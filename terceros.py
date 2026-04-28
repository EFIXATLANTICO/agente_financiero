import pandas as pd
from db_context import get_connection


TABLAS_VALIDAS = {
    "cliente": "clientes",
    "proveedor": "proveedores",
}


def _tabla_tipo(tipo):
    tipo = (tipo or "").strip().lower()
    if tipo not in TABLAS_VALIDAS:
        raise ValueError("Tipo de tercero no valido")
    return TABLAS_VALIDAS[tipo]


def listar_terceros(tipo):
    tabla = _tabla_tipo(tipo)
    conn = get_connection()

    try:
        df = pd.read_sql_query(
            f"""
            SELECT id, nombre, nif, direccion, email, telefono
            FROM {tabla}
            ORDER BY nombre
            """,
            conn,
        )
        return df
    finally:
        conn.close()


def obtener_tercero(tipo, tercero_id):
    tabla = _tabla_tipo(tipo)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            SELECT id, nombre, nif, direccion, email, telefono
            FROM {tabla}
            WHERE id = %s
            """,
            (tercero_id,),
        )
        fila = cursor.fetchone()
        if not fila:
            return None

        return {
            "id": fila[0],
            "nombre": fila[1],
            "nif": fila[2] or "",
            "direccion": fila[3] or "",
            "email": fila[4] or "",
            "telefono": fila[5] or "",
        }
    finally:
        conn.close()


def crear_tercero(tipo, nombre, nif="", direccion="", email="", telefono=""):
    tabla = _tabla_tipo(tipo)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        nombre = (nombre or "").strip()
        if not nombre:
            return {"ok": False, "mensaje": "El nombre es obligatorio"}

        cursor.execute(
            f"""
            SELECT id
            FROM {tabla}
            WHERE UPPER(TRIM(nombre)) = UPPER(TRIM(%s))
            """,
            (nombre,),
        )
        if cursor.fetchone():
            return {"ok": False, "mensaje": f"Ya existe un {tipo} con ese nombre"}

        cursor.execute(
            f"""
            INSERT INTO {tabla} (nombre, nif, direccion, email, telefono)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (nombre, nif or "", direccion or "", email or "", telefono or ""),
        )

        tercero_id = cursor.fetchone()[0]
        conn.commit()
        return {"ok": True, "id": tercero_id, "mensaje": f"{tipo.capitalize()} creado correctamente"}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

    finally:
        conn.close()


def actualizar_tercero(tipo, tercero_id, nombre, nif="", direccion="", email="", telefono=""):
    tabla = _tabla_tipo(tipo)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        nombre = (nombre or "").strip()
        if not nombre:
            return {"ok": False, "mensaje": "El nombre es obligatorio"}

        cursor.execute(
            f"""
            SELECT id
            FROM {tabla}
            WHERE id = %s
            """,
            (tercero_id,),
        )
        if not cursor.fetchone():
            return {"ok": False, "mensaje": f"{tipo.capitalize()} no encontrado"}

        cursor.execute(
            f"""
            SELECT id
            FROM {tabla}
            WHERE UPPER(TRIM(nombre)) = UPPER(TRIM(%s))
              AND id <> %s
            """,
            (nombre, tercero_id),
        )
        if cursor.fetchone():
            return {"ok": False, "mensaje": f"Ya existe otro {tipo} con ese nombre"}

        cursor.execute(
            f"""
            UPDATE {tabla}
            SET nombre = %s, nif = %s, direccion = %s, email = %s, telefono = %s
            WHERE id = %s
            """,
            (nombre, nif or "", direccion or "", email or "", telefono or "", tercero_id),
        )

        conn.commit()
        return {"ok": True, "mensaje": f"{tipo.capitalize()} actualizado correctamente"}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

    finally:
        conn.close()


def borrar_tercero(tipo, tercero_id):
    tabla = _tabla_tipo(tipo)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            SELECT nombre
            FROM {tabla}
            WHERE id = %s
            """,
            (tercero_id,),
        )
        fila = cursor.fetchone()
        if not fila:
            return {"ok": False, "mensaje": f"{tipo.capitalize()} no encontrado"}

        nombre = fila[0]

        if tipo == "cliente":
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM facturas
                WHERE tipo = 'venta' AND tercero_id = %s
                """,
                (tercero_id,),
            )
        else:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM facturas
                WHERE tipo = 'compra' AND tercero_id = %s
                """,
                (tercero_id,),
            )

        total_facturas = cursor.fetchone()[0]

        if total_facturas > 0:
            return {
                "ok": False,
                "mensaje": f"No se puede borrar porque {nombre} tiene facturas asociadas ({total_facturas})"
            }

        cursor.execute(
            f"""
            DELETE FROM {tabla}
            WHERE id = %s
            """,
            (tercero_id,),
        )

        conn.commit()
        return {"ok": True, "mensaje": f"{tipo.capitalize()} borrado correctamente"}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

    finally:
        conn.close()


def metricas_tercero(tipo, tercero_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        tercero = obtener_tercero(tipo, tercero_id)
        if not tercero:
            return None

        nombre_tercero = (tercero["nombre"] or "").strip()

        if tipo == "cliente":
            tipo_factura = "venta"
            estado_final = "cobrada"
            tipo_operacion = "venta"
        else:
            tipo_factura = "compra"
            estado_final = "pagada"
            tipo_operacion = "compra"

        # METRICAS DESDE FACTURAS
        cursor.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(total), 0),
                COALESCE(SUM(CASE WHEN estado = %s THEN total ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN estado IN ('pendiente', 'cobro_parcial', 'pago_parcial') THEN total ELSE 0 END), 0)
            FROM facturas
            WHERE tipo = %s AND tercero_id = %s
            """,
            (estado_final, tipo_factura, tercero_id),
        )
        total_facturas, volumen_facturas, volumen_cerrado, saldo_pendiente = cursor.fetchone()

        # METRICAS DESDE OPERACIONES INTELIGENTES
        cursor.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(total), 0)
            FROM operaciones
            WHERE tipo_operacion = %s
              AND UPPER(TRIM(nombre_tercero)) = UPPER(TRIM(%s))
            """,
            (tipo_operacion, nombre_tercero),
        )
        total_operaciones, volumen_operaciones = cursor.fetchone()

        # FORMA DE PAGO HABITUAL (facturas primero, si no, operaciones)
        cursor.execute(
            """
            SELECT forma_pago, COUNT(*) as n
            FROM facturas
            WHERE tipo = %s AND tercero_id = %s AND forma_pago IS NOT NULL AND TRIM(forma_pago) <> ''
            GROUP BY forma_pago
            ORDER BY n DESC, forma_pago
            LIMIT 1
            """,
            (tipo_factura, tercero_id),
        )
        fila_pago = cursor.fetchone()

        if fila_pago:
            forma_pago_habitual = fila_pago[0]
        else:
            cursor.execute(
                """
                SELECT forma_pago, COUNT(*) as n
                FROM operaciones
                WHERE tipo_operacion = %s
                  AND UPPER(TRIM(nombre_tercero)) = UPPER(TRIM(%s))
                  AND forma_pago IS NOT NULL AND TRIM(forma_pago) <> ''
                GROUP BY forma_pago
                ORDER BY n DESC, forma_pago
                LIMIT 1
                """,
                (tipo_operacion, nombre_tercero),
            )
            fila_pago_op = cursor.fetchone()
            forma_pago_habitual = fila_pago_op[0] if fila_pago_op else ""

        # ULTIMAS FACTURAS
        cursor.execute(
            """
            SELECT id, fecha_emision, concepto, total, estado, forma_pago
            FROM facturas
            WHERE tipo = %s AND tercero_id = %s
            ORDER BY fecha_emision DESC, id DESC
            LIMIT 20
            """,
            (tipo_factura, tercero_id),
        )
        facturas = cursor.fetchall()

        df_facturas = pd.DataFrame(
            facturas,
            columns=["ID", "Fecha", "Concepto", "Total", "Estado", "Forma pago"]
        ) if facturas else pd.DataFrame(columns=["ID", "Fecha", "Concepto", "Total", "Estado", "Forma pago"])

        # ULTIMAS OPERACIONES
        cursor.execute(
            """
            SELECT id, fecha_operacion, concepto, total, forma_pago
            FROM operaciones
            WHERE tipo_operacion = %s
              AND UPPER(TRIM(nombre_tercero)) = UPPER(TRIM(%s))
            ORDER BY fecha_operacion DESC, id DESC
            LIMIT 20
            """,
            (tipo_operacion, nombre_tercero),
        )
        operaciones = cursor.fetchall()

        df_operaciones = pd.DataFrame(
            operaciones,
            columns=["ID", "Fecha", "Concepto", "Total", "Forma pago"]
        ) if operaciones else pd.DataFrame(columns=["ID", "Fecha", "Concepto", "Total", "Forma pago"])

        return {
            "tercero": tercero,
            "total_facturas": int(total_facturas or 0),
            "total_operaciones": int(total_operaciones or 0),
            "volumen_total": float((volumen_facturas or 0) + (volumen_operaciones or 0)),
            "volumen_facturas": float(volumen_facturas or 0),
            "volumen_operaciones": float(volumen_operaciones or 0),
            "volumen_cerrado": float(volumen_cerrado or 0),
            "saldo_pendiente": float(saldo_pendiente or 0),
            "forma_pago_habitual": forma_pago_habitual or "",
            "facturas": df_facturas,
            "operaciones": df_operaciones,
        }

    finally:
        conn.close()
