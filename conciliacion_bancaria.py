import sqlite3
from datetime import datetime
from difflib import SequenceMatcher

import pandas as pd

from db_context import get_connection

def inicializar_tablas_conciliacion():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimientos_banco (
        id SERIAL PRIMARY KEY,
        fecha TEXT,
        concepto TEXT,
        importe REAL,
        sentido TEXT,
        saldo REAL,
        referencia TEXT,
        estado_conciliacion TEXT DEFAULT 'pendiente',
revisado INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conciliaciones (
        id SERIAL PRIMARY KEY,
        movimiento_banco_id INTEGER,
        fecha TEXT,
        score_ia REAL,
        estado TEXT,
        observaciones TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conciliacion_detalle (
        id SERIAL PRIMARY KEY,
        conciliacion_id INTEGER,
        factura_id INTEGER,
        importe_aplicado REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conciliacion_snapshot (
        id SERIAL PRIMARY KEY,
        asiento_id INTEGER,
        lineas_json TEXT
    )
    """)

    conn.commit()
    conn.close()


def registrar_movimiento_banco(fecha, concepto, importe, saldo=None, referencia=None):
    inicializar_tablas_conciliacion()

    conn = get_connection()
    cursor = conn.cursor()

    sentido = "ingreso" if float(importe) > 0 else "pago"

    cursor.execute("""
    INSERT INTO movimientos_banco (
        fecha,
        concepto,
        importe,
        sentido,
        saldo,
        referencia
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        fecha,
        concepto,
        abs(float(importe)),
        sentido,
        saldo,
        referencia
    ))

    conn.commit()
    conn.close()


def movimientos_pendientes():
    inicializar_tablas_conciliacion()

    conn = get_connection()
    df = pd.read_sql_query("""
    SELECT *
    FROM movimientos_banco
    WHERE estado_conciliacion = 'pendiente'
    ORDER BY fecha, id
    """, conn)
    conn.close()
    return df


def facturas_pendientes():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT *
        FROM facturas
        WHERE estado IN ('pendiente', 'cobro_parcial', 'pago_parcial')
        ORDER BY fecha_emision, id
    """, conn)
    conn.close()
    return df


def similitud(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()


def score_match(mov, fac):
    score = 0.0

    if abs(float(mov["importe"]) - float(fac["total"])) < 0.01:
        score += 0.50
    elif abs(float(mov["importe"]) - float(fac["total"])) <= 5:
        score += 0.25

    score += similitud(mov["concepto"], fac["nombre_tercero"]) * 0.40
    score += similitud(mov["concepto"], fac.get("concepto", "")) * 0.10

    dias = abs(
        (pd.to_datetime(mov["fecha"]) - pd.to_datetime(fac["fecha_emision"])).days
    )

    if dias <= 3:
        score += 0.20
    elif dias <= 10:
        score += 0.10

    if mov["sentido"] == "ingreso" and fac["tipo"] == "venta":
        score += 0.10
    elif mov["sentido"] == "pago" and fac["tipo"] == "compra":
        score += 0.10
    import re

    # detectar número de factura en el concepto
    numeros_mov = re.findall(r'\d+', str(mov["concepto"]))
    numeros_fac = re.findall(r'\d+', str(fac.get("numero", "")))

    if numeros_mov and numeros_fac:
        if any(n in numeros_mov for n in numeros_fac):
            score += 0.30

    return round(score, 4)


def sugerencias_ia(score_minimo=0.60):
    movs = movimientos_pendientes()
    facs = facturas_pendientes()

    resultados = []

    if movs.empty or facs.empty:
        return pd.DataFrame()

    for _, m in movs.iterrows():
        for _, f in facs.iterrows():
            s = score_match(m, f)

            if s >= score_minimo:
                resultados.append({
                    "movimiento_id": int(m["id"]),
                    "factura_id": int(f["id"]),
                    "score": s,
                    "importe_mov": float(m["importe"]),
                    "importe_fac": float(f["total"]),
                    "concepto_mov": m["concepto"],
                    "tercero": f["nombre_tercero"],
                    "tipo_factura": f["tipo"],
                    "fecha_mov": m["fecha"],
                    "fecha_factura": f["fecha_emision"],
                    "explicacion": f"Score {s} → importe + texto + fecha"
                })

    df = pd.DataFrame(resultados)

    if df.empty:
        return df

    df = df.sort_values(
        ["movimiento_id", "score"],
        ascending=[True, False]
    )

    # quedarse solo con la mejor sugerencia por movimiento
    df = df.groupby("movimiento_id").head(1)

    return df.reset_index(drop=True)

def aplicar_conciliacion(movimiento_id, facturas_importes):
    inicializar_tablas_conciliacion()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, sentido, estado_conciliacion, importe
    FROM movimientos_banco
    WHERE id = ?
    """, (movimiento_id,))
    mov = cursor.fetchone()

    if not mov:
        conn.close()
        raise ValueError("Movimiento bancario no encontrado")

    _, sentido, estado_conciliacion, importe_mov = mov

    if estado_conciliacion == "conciliado":
        conn.close()
        raise ValueError("Ese movimiento ya está conciliado")

    total_aplicar = sum(float(i[1]) for i in facturas_importes)

    if total_aplicar > float(importe_mov) + 0.01:
        conn.close()
        raise ValueError("El importe aplicado supera el movimiento bancario")

    cursor.execute("""
    INSERT INTO conciliaciones
    (movimiento_banco_id, fecha, score_ia, estado, observaciones)
    VALUES (?, ?, ?, ?, ?)
    """, (
        movimiento_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        None,
        "conciliado",
        ""
    ))

    conciliacion_id = cursor.lastrowid

    for factura_id, importe in facturas_importes:
        cursor.execute("""
        SELECT tipo, estado, total
        FROM facturas
        WHERE id = ?
        """, (factura_id,))
        fila = cursor.fetchone()

        if not fila:
            conn.rollback()
            conn.close()
            raise ValueError(f"Factura {factura_id} no encontrada")

        tipo_factura, estado_factura, total_factura = fila

        if estado_factura not in ["pendiente", "cobro_parcial", "pago_parcial"]:
            conn.rollback()
            conn.close()
            raise ValueError(f"La factura {factura_id} no está pendiente ni parcial")

        if sentido == "ingreso" and tipo_factura != "venta":
            conn.rollback()
            conn.close()
            raise ValueError("Un ingreso bancario debe conciliarse con una factura de venta")

        if sentido == "pago" and tipo_factura != "compra":
            conn.rollback()
            conn.close()
            raise ValueError("Un pago bancario debe conciliarse con una factura de compra")

        if float(importe) < 0:
            conn.rollback()
            conn.close()
            raise ValueError("El importe aplicado no puede ser negativo")

        cursor.execute("""
        SELECT COALESCE(SUM(importe_aplicado), 0)
        FROM conciliacion_detalle
        WHERE factura_id = ?
        """, (factura_id,))
        ya_aplicado = float(cursor.fetchone()[0] or 0)

        pendiente_factura = max(0.0, float(total_factura) - ya_aplicado)

        importe_aplicado = pendiente_factura if float(importe) == 0 else float(importe)

        if importe_aplicado <= 0:
            conn.rollback()
            conn.close()
            raise ValueError(f"El importe aplicado a la factura {factura_id} debe ser mayor que cero")

        if importe_aplicado > pendiente_factura + 0.01:
            conn.rollback()
            conn.close()
            raise ValueError(
                f"El importe aplicado a la factura {factura_id} supera su pendiente real ({pendiente_factura:.2f} €)"
            )

        cursor.execute("""
        INSERT INTO conciliacion_detalle
        (conciliacion_id, factura_id, importe_aplicado)
        VALUES (?, ?, ?)
        """, (
            conciliacion_id,
            factura_id,
            importe_aplicado
        ))

        total_aplicado = ya_aplicado + importe_aplicado

        if float(total_aplicado) >= float(total_factura):
            nuevo_estado = "cobrada" if tipo_factura == "venta" else "pagada"
        else:
            nuevo_estado = "cobro_parcial" if tipo_factura == "venta" else "pago_parcial"

        cursor.execute("""
        UPDATE facturas
        SET estado = ?
        WHERE id = ?
        """, (nuevo_estado, factura_id))

    cursor.execute("""
    UPDATE movimientos_banco
    SET estado_conciliacion = 'conciliado',
        revisado = 1
    WHERE id = ?
    """, (movimiento_id,))

    conn.commit()
    conn.close()

def resumen_conciliacion():
    inicializar_tablas_conciliacion()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM movimientos_banco
    WHERE estado_conciliacion = 'pendiente'
    """)
    movs = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM facturas
    WHERE estado IN ('pendiente', 'cobro_parcial', 'pago_parcial')
    """)
    facts = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM conciliaciones
    """)
    conc = cursor.fetchone()[0]

    conn.close()

    return {
        "movimientos_pendientes": movs,
        "facturas_pendientes": facts,
        "conciliaciones_realizadas": conc
    }


def historial_conciliaciones():
    inicializar_tablas_conciliacion()

    conn = get_connection()
    df = pd.read_sql_query("""
    SELECT *
    FROM conciliaciones
    ORDER BY id DESC
    """, conn)
    conn.close()
    return df


def auto_conciliar_por_ia(score_minimo=0.85):
    df = sugerencias_ia(score_minimo=score_minimo)

    if df.empty:
        return pd.DataFrame()

    # seguridad extra: solo scores altos
    df = df[df["score"] >= score_minimo]

    resultados = []
    movimientos_usados = set()
    facturas_usadas = set()

    for _, row in df.iterrows():
        movimiento_id = int(row["movimiento_id"])
        factura_id = int(row["factura_id"])

        if movimiento_id in movimientos_usados:
            continue

        if factura_id in facturas_usadas:
            continue

        try:
            aplicar_conciliacion(
                movimiento_id=movimiento_id,
                facturas_importes=[(factura_id, float(row["importe_fac"]))]
            )

            resultados.append({
                "movimiento_id": movimiento_id,
                "factura_id": factura_id,
                "score": row["score"],
                "estado": "conciliado"
            })

            movimientos_usados.add(movimiento_id)
            facturas_usadas.add(factura_id)

        except Exception as e:
            resultados.append({
                "movimiento_id": movimiento_id,
                "factura_id": factura_id,
                "score": row["score"],
                "estado": f"error: {str(e)}"
            })

    return pd.DataFrame(resultados)