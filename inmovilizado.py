from datetime import datetime
from calendar import monthrange
import pandas as pd

from db_context import get_connection

def inicializar_tabla_inmovilizado():
    conexion = get_connection()
    cursor = conexion.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inmovilizado (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        fecha_compra TEXT NOT NULL,
        fecha_inicio_amortizacion TEXT NOT NULL,
        coste REAL NOT NULL,
        valor_residual REAL NOT NULL DEFAULT 0,
        vida_util_anios REAL NOT NULL,
        porcentaje_amortizacion REAL NOT NULL,
        cuenta_inmovilizado TEXT NOT NULL,
        cuenta_amort_acumulada TEXT NOT NULL,
        cuenta_gasto_amortizacion TEXT NOT NULL,
        amortizacion_acumulada REAL NOT NULL DEFAULT 0,
        activo INTEGER NOT NULL DEFAULT 1,
        observaciones TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS amortizaciones_generadas (
        id SERIAL PRIMARY KEY,
        bien_id INTEGER NOT NULL,
        ejercicio INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        fecha_asiento TEXT NOT NULL,
        asiento_id INTEGER,
        importe REAL NOT NULL,
        UNIQUE(bien_id, ejercicio, mes),
        FOREIGN KEY (bien_id) REFERENCES inmovilizado(id)
    )
    """)

    migraciones = [
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS porcentaje_amortizacion REAL NOT NULL DEFAULT 0",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS amortizacion_acumulada REAL NOT NULL DEFAULT 0",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS activo INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS observaciones TEXT",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS codigo_maquina TEXT",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS categoria TEXT",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS ubicacion TEXT",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS estado_operativo TEXT NOT NULL DEFAULT 'disponible'",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS valor_mercado REAL NOT NULL DEFAULT 0",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS tarifa_dia REAL NOT NULL DEFAULT 0",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS fecha_inicio_amortizacion TEXT",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS valor_residual REAL NOT NULL DEFAULT 0",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS vida_util_anios REAL NOT NULL DEFAULT 1",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS cuenta_inmovilizado TEXT NOT NULL DEFAULT '213 Maquinaria'",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS cuenta_amort_acumulada TEXT NOT NULL DEFAULT '2813 Amortizacion acumulada maquinaria'",
        "ALTER TABLE inmovilizado ADD COLUMN IF NOT EXISTS cuenta_gasto_amortizacion TEXT NOT NULL DEFAULT '681 Amortizacion del inmovilizado material'",
        """
        UPDATE inmovilizado
        SET fecha_inicio_amortizacion = COALESCE(fecha_inicio_amortizacion, fecha_compra)
        WHERE fecha_inicio_amortizacion IS NULL
        """,
        """
        UPDATE inmovilizado
        SET porcentaje_amortizacion = ROUND((100 / NULLIF(vida_util_anios, 0))::numeric, 2)
        WHERE porcentaje_amortizacion = 0 AND vida_util_anios > 0
        """,
    ]

    for sql in migraciones:
        cursor.execute(sql)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alquileres_maquinaria (
        id SERIAL PRIMARY KEY,
        bien_id INTEGER NOT NULL REFERENCES inmovilizado(id),
        cliente TEXT,
        obra TEXT,
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT,
        dias INTEGER NOT NULL DEFAULT 0,
        importe REAL NOT NULL DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'abierto',
        observaciones TEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS costes_maquinaria (
        id SERIAL PRIMARY KEY,
        bien_id INTEGER NOT NULL REFERENCES inmovilizado(id),
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL,
        importe REAL NOT NULL DEFAULT 0,
        proveedor TEXT,
        observaciones TEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conexion.commit()
    conexion.close()


def validar_fecha(fecha_texto: str):
    try:
        datetime.strptime(fecha_texto, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def ultimo_dia_mes(ejercicio: int, mes: int) -> str:
    dia = monthrange(ejercicio, mes)[1]
    return f"{ejercicio}-{mes:02d}-{dia:02d}"


def meses_entre(fecha_inicio: str, fecha_fin: str) -> int:
    inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    return (fin.year - inicio.year) * 12 + (fin.month - inicio.month)


def calcular_base_amortizable(coste: float, valor_residual: float) -> float:
    return round(float(coste) - float(valor_residual), 2)


def calcular_amortizacion_anual(coste: float, vida_util_anios: float, valor_residual: float = 0) -> float:
    base = calcular_base_amortizable(coste, valor_residual)
    if vida_util_anios <= 0:
        raise ValueError("La vida util debe ser mayor que 0.")
    return round(base / float(vida_util_anios), 2)


def calcular_amortizacion_mensual(coste: float, vida_util_anios: float, valor_residual: float = 0) -> float:
    return round(calcular_amortizacion_anual(coste, vida_util_anios, valor_residual) / 12, 2)


def alta_inmovilizado(
    nombre,
    fecha_compra,
    coste,
    vida_util_anios,
    fecha_inicio_amortizacion=None,
    valor_residual=0,
    cuenta_inmovilizado="213 Maquinaria",
    cuenta_amort_acumulada="2813 Amortizacion acumulada de maquinaria",
    cuenta_gasto_amortizacion="681 Amortizacion del inmovilizado material",
    observaciones=""
):
    inicializar_tabla_inmovilizado()

    if not nombre or not str(nombre).strip():
        raise ValueError("El nombre del bien es obligatorio.")

    if not validar_fecha(fecha_compra):
        raise ValueError("La fecha de compra debe tener formato YYYY-MM-DD.")

    if fecha_inicio_amortizacion is None:
        fecha_inicio_amortizacion = fecha_compra

    if not validar_fecha(fecha_inicio_amortizacion):
        raise ValueError("La fecha de inicio de amortizacion debe tener formato YYYY-MM-DD.")

    coste = float(coste)
    vida_util_anios = float(vida_util_anios)
    valor_residual = float(valor_residual)

    if coste <= 0:
        raise ValueError("El coste debe ser mayor que 0.")
    if vida_util_anios <= 0:
        raise ValueError("La vida util debe ser mayor que 0.")
    if valor_residual < 0:
        raise ValueError("El valor residual no puede ser negativo.")
    if valor_residual >= coste:
        raise ValueError("El valor residual debe ser menor que el coste.")

    porcentaje_amortizacion = round(100 / vida_util_anios, 2)

    conexion = get_connection()
    cursor = conexion.cursor()

    cursor.execute("""
    INSERT INTO inmovilizado (
        nombre,
        fecha_compra,
        fecha_inicio_amortizacion,
        coste,
        valor_residual,
        vida_util_anios,
        porcentaje_amortizacion,
        cuenta_inmovilizado,
        cuenta_amort_acumulada,
        cuenta_gasto_amortizacion,
        amortizacion_acumulada,
        activo,
        observaciones
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 1, %s)
    RETURNING id
    """, (
        nombre.strip(),
        fecha_compra,
        fecha_inicio_amortizacion,
        coste,
        valor_residual,
        vida_util_anios,
        porcentaje_amortizacion,
        cuenta_inmovilizado,
        cuenta_amort_acumulada,
        cuenta_gasto_amortizacion,
        observaciones
    ))

    bien_id = cursor.fetchone()[0]
    conexion.commit()
    conexion.close()

    return bien_id


def ver_inmovilizado(solo_activos=False):
    inicializar_tabla_inmovilizado()

    conexion = get_connection()
    query = """
    SELECT
        id,
        nombre,
        fecha_compra,
        fecha_inicio_amortizacion,
        coste,
        valor_residual,
        vida_util_anios,
        porcentaje_amortizacion,
        amortizacion_acumulada,
        codigo_maquina,
        categoria,
        ubicacion,
        estado_operativo,
        valor_mercado,
        tarifa_dia,
        ROUND(((coste - valor_residual) - amortizacion_acumulada)::numeric, 2) AS pendiente_amortizar,
        ROUND((coste - amortizacion_acumulada)::numeric, 2) AS valor_neto_contable,
        cuenta_inmovilizado,
        cuenta_amort_acumulada,
        cuenta_gasto_amortizacion,
        activo,
        observaciones
    FROM inmovilizado
    """
    if solo_activos:
        query += " WHERE activo = 1 "
    query += " ORDER BY id DESC "

    df = pd.read_sql_query(query, conexion)
    conexion.close()

    return df


def obtener_bien(bien_id):
    inicializar_tabla_inmovilizado()

    conexion = get_connection()
    cursor = conexion.cursor()

    cursor.execute("""
    SELECT
        id,
        nombre,
        fecha_compra,
        fecha_inicio_amortizacion,
        coste,
        valor_residual,
        vida_util_anios,
        porcentaje_amortizacion,
        cuenta_inmovilizado,
        cuenta_amort_acumulada,
        cuenta_gasto_amortizacion,
        amortizacion_acumulada,
        activo,
        observaciones
    FROM inmovilizado
    WHERE id = %s
    """, (bien_id,))

    fila = cursor.fetchone()
    conexion.close()

    if not fila:
        return None

    columnas = [
        "id", "nombre", "fecha_compra", "fecha_inicio_amortizacion", "coste",
        "valor_residual", "vida_util_anios", "porcentaje_amortizacion",
        "cuenta_inmovilizado", "cuenta_amort_acumulada", "cuenta_gasto_amortizacion",
        "amortizacion_acumulada", "activo", "observaciones"
    ]
    return dict(zip(columnas, fila))


def baja_inmovilizado(bien_id):
    inicializar_tabla_inmovilizado()
    conexion = get_connection()
    cursor = conexion.cursor()

    cursor.execute("""
    UPDATE inmovilizado
    SET activo = 0
    WHERE id = %s
    """, (bien_id,))

    conexion.commit()
    afectados = cursor.rowcount
    conexion.close()

    return afectados > 0


def ya_generada_amortizacion(bien_id, ejercicio, mes):
    conexion = get_connection()
    cursor = conexion.cursor()

    cursor.execute("""
    SELECT id
    FROM amortizaciones_generadas
    WHERE bien_id = %s AND ejercicio = %s AND mes = %s
    """, (bien_id, ejercicio, mes))

    existe = cursor.fetchone() is not None
    conexion.close()
    return existe


def calcular_importe_amortizacion_mes(bien_id, ejercicio, mes):
    bien = obtener_bien(bien_id)
    if not bien:
        raise ValueError("El bien no existe.")

    if int(bien["activo"]) != 1:
        return 0.0

    fecha_inicio = bien["fecha_inicio_amortizacion"]
    fecha_objetivo = ultimo_dia_mes(ejercicio, mes)

    if fecha_objetivo < fecha_inicio:
        return 0.0

    base_amortizable = calcular_base_amortizable(bien["coste"], bien["valor_residual"])
    pendiente = round(base_amortizable - float(bien["amortizacion_acumulada"]), 2)

    if pendiente <= 0:
        return 0.0

    cuota_mensual = calcular_amortizacion_mensual(
        bien["coste"],
        bien["vida_util_anios"],
        bien["valor_residual"]
    )

    return round(min(cuota_mensual, pendiente), 2)


def generar_asiento_amortizacion(bien_id, ejercicio, mes, fecha_asiento=None):
    inicializar_tabla_inmovilizado()

    if mes < 1 or mes > 12:
        raise ValueError("El mes debe estar entre 1 y 12.")

    if fecha_asiento is None:
        fecha_asiento = ultimo_dia_mes(ejercicio, mes)

    if not validar_fecha(fecha_asiento):
        raise ValueError("La fecha del asiento debe tener formato YYYY-MM-DD.")

    if ya_generada_amortizacion(bien_id, ejercicio, mes):
        raise ValueError(f"Ya existe amortizacion generada para {ejercicio}-{mes:02d}.")

    bien = obtener_bien(bien_id)
    if not bien:
        raise ValueError("El bien no existe.")

    importe = calcular_importe_amortizacion_mes(bien_id, ejercicio, mes)
    if importe <= 0:
        raise ValueError("No corresponde generar amortizacion para ese periodo o ya esta totalmente amortizado.")

    conexion = get_connection()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
        INSERT INTO asientos (fecha, concepto, tipo_operacion)
        VALUES (%s, %s, %s)
        RETURNING id
        """, (
            fecha_asiento,
            f"Amortizacion {ejercicio}-{mes:02d} - {bien['nombre']}",
            "amortizacion"
        ))
        asiento_id = cursor.fetchone()[0]

        cursor.execute("""
        INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
        VALUES (%s, %s, %s, %s)
        """, (
            asiento_id,
            bien["cuenta_gasto_amortizacion"],
            "debe",
            importe
        ))

        cursor.execute("""
        INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
        VALUES (%s, %s, %s, %s)
        """, (
            asiento_id,
            bien["cuenta_amort_acumulada"],
            "haber",
            importe
        ))

        cursor.execute("""
        UPDATE inmovilizado
        SET amortizacion_acumulada = ROUND((amortizacion_acumulada + %s)::numeric, 2)
        WHERE id = %s
        """, (importe, bien_id))

        cursor.execute("""
        INSERT INTO amortizaciones_generadas (
            bien_id, ejercicio, mes, fecha_asiento, asiento_id, importe
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """, (bien_id, ejercicio, mes, fecha_asiento, asiento_id, importe))

        conexion.commit()
        return asiento_id

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()


def generar_amortizaciones_mes(ejercicio, mes, solo_activos=True):
    inicializar_tabla_inmovilizado()

    df = ver_inmovilizado(solo_activos=solo_activos)
    resultados = []

    for _, fila in df.iterrows():
        bien_id = int(fila["id"])
        try:
            asiento_id = generar_asiento_amortizacion(bien_id, ejercicio, mes)
            resultados.append({
                "bien_id": bien_id,
                "nombre": fila["nombre"],
                "estado": "generado",
                "asiento_id": asiento_id
            })
        except Exception as e:
            resultados.append({
                "bien_id": bien_id,
                "nombre": fila["nombre"],
                "estado": "omitido",
                "detalle": str(e)
            })

    return pd.DataFrame(resultados)


def historial_amortizaciones(bien_id=None):
    inicializar_tabla_inmovilizado()
    conexion = get_connection()

    query = """
    SELECT
        ag.id,
        ag.bien_id,
        i.nombre,
        ag.ejercicio,
        ag.mes,
        ag.fecha_asiento,
        ag.asiento_id,
        ag.importe
    FROM amortizaciones_generadas ag
    INNER JOIN inmovilizado i ON i.id = ag.bien_id
    """
    params = []

    if bien_id is not None:
        query += " WHERE ag.bien_id = %s "
        params.append(bien_id)

    query += " ORDER BY ag.ejercicio DESC, ag.mes DESC, ag.id DESC "

    df = pd.read_sql_query(query, conexion, params=params)
    conexion.close()
    return df


def cuadro_amortizacion(bien_id):
    bien = obtener_bien(bien_id)
    if not bien:
        raise ValueError("El bien no existe.")

    base_amortizable = calcular_base_amortizable(bien["coste"], bien["valor_residual"])
    cuota_mensual = calcular_amortizacion_mensual(
        bien["coste"],
        bien["vida_util_anios"],
        bien["valor_residual"]
    )

    fecha_inicio = datetime.strptime(bien["fecha_inicio_amortizacion"], "%Y-%m-%d").date()
    total_meses = int(round(float(bien["vida_util_anios"]) * 12, 0))

    filas = []
    acumulada = 0.0

    for i in range(total_meses):
        year = fecha_inicio.year + ((fecha_inicio.month - 1 + i) // 12)
        month = ((fecha_inicio.month - 1 + i) % 12) + 1

        pendiente_antes = round(base_amortizable - acumulada, 2)
        cuota = min(cuota_mensual, pendiente_antes)
        acumulada = round(acumulada + cuota, 2)
        pendiente_despues = round(base_amortizable - acumulada, 2)

        filas.append({
            "Periodo": f"{year}-{month:02d}",
            "Cuota": round(cuota, 2),
            "Amortizacion acumulada": acumulada,
            "Pendiente amortizar": pendiente_despues
        })

        if pendiente_despues <= 0:
            break

    return pd.DataFrame(filas)


def actualizar_datos_maquinaria(
    bien_id,
    codigo_maquina="",
    categoria="",
    ubicacion="",
    estado_operativo="disponible",
    valor_mercado=0,
    tarifa_dia=0,
    observaciones=None,
):
    inicializar_tabla_inmovilizado()
    conn = get_connection()
    cursor = conn.cursor()

    if observaciones is None:
        cursor.execute("""
            UPDATE inmovilizado
            SET codigo_maquina = %s,
                categoria = %s,
                ubicacion = %s,
                estado_operativo = %s,
                valor_mercado = %s,
                tarifa_dia = %s
            WHERE id = %s
        """, (
            codigo_maquina, categoria, ubicacion, estado_operativo,
            float(valor_mercado or 0), float(tarifa_dia or 0), bien_id
        ))
    else:
        cursor.execute("""
            UPDATE inmovilizado
            SET codigo_maquina = %s,
                categoria = %s,
                ubicacion = %s,
                estado_operativo = %s,
                valor_mercado = %s,
                tarifa_dia = %s,
                observaciones = %s
            WHERE id = %s
        """, (
            codigo_maquina, categoria, ubicacion, estado_operativo,
            float(valor_mercado or 0), float(tarifa_dia or 0), observaciones, bien_id
        ))

    conn.commit()
    afectados = cursor.rowcount
    conn.close()
    return afectados > 0


def registrar_alquiler_maquinaria(
    bien_id,
    cliente,
    obra,
    fecha_inicio,
    fecha_fin=None,
    dias=0,
    importe=0,
    estado="abierto",
    observaciones="",
):
    inicializar_tabla_inmovilizado()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alquileres_maquinaria (
            bien_id, cliente, obra, fecha_inicio, fecha_fin, dias, importe, estado, observaciones
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        bien_id, cliente, obra, fecha_inicio, fecha_fin, int(dias or 0),
        float(importe or 0), estado, observaciones
    ))
    alquiler_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return alquiler_id


def registrar_coste_maquinaria(bien_id, fecha, tipo, importe, proveedor="", observaciones=""):
    inicializar_tabla_inmovilizado()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO costes_maquinaria (bien_id, fecha, tipo, importe, proveedor, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (bien_id, fecha, tipo, float(importe or 0), proveedor, observaciones))
    coste_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return coste_id


def listar_rotacion_maquinaria(fecha_desde=None, fecha_hasta=None):
    inicializar_tabla_inmovilizado()
    conn = get_connection()

    params = []
    filtro_alquiler = ""
    filtro_coste = ""
    if fecha_desde:
        filtro_alquiler += " AND a.fecha_inicio >= %s"
        filtro_coste += " AND c.fecha >= %s"
        params.append(fecha_desde)
    if fecha_hasta:
        filtro_alquiler += " AND COALESCE(a.fecha_fin, a.fecha_inicio) <= %s"
        filtro_coste += " AND c.fecha <= %s"
        params.append(fecha_hasta)

    params_costes = list(params)
    df = pd.read_sql_query(f"""
        WITH alquileres AS (
            SELECT
                a.bien_id,
                COUNT(*) AS alquileres,
                COALESCE(SUM(a.dias), 0) AS dias_alquilados,
                COALESCE(SUM(a.importe), 0) AS ingresos
            FROM alquileres_maquinaria a
            WHERE 1=1 {filtro_alquiler}
            GROUP BY a.bien_id
        ),
        costes AS (
            SELECT
                c.bien_id,
                COALESCE(SUM(c.importe), 0) AS costes
            FROM costes_maquinaria c
            WHERE 1=1 {filtro_coste}
            GROUP BY c.bien_id
        )
        SELECT
            i.id,
            i.nombre,
            i.codigo_maquina,
            i.categoria,
            i.ubicacion,
            i.estado_operativo,
            i.coste,
            i.valor_mercado,
            i.tarifa_dia,
            COALESCE(a.alquileres, 0) AS alquileres,
            COALESCE(a.dias_alquilados, 0) AS dias_alquilados,
            COALESCE(a.ingresos, 0) AS ingresos,
            COALESCE(c.costes, 0) AS costes,
            ROUND((COALESCE(a.ingresos, 0) - COALESCE(c.costes, 0))::numeric, 2) AS margen
        FROM inmovilizado i
        LEFT JOIN alquileres a ON a.bien_id = i.id
        LEFT JOIN costes c ON c.bien_id = i.id
        WHERE i.activo = 1
        ORDER BY ingresos DESC, i.nombre
    """, conn, params=params + params_costes)

    conn.close()
    return df


def listar_alquileres_maquinaria(limit=500):
    inicializar_tabla_inmovilizado()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT a.id, i.nombre AS maquina, a.cliente, a.obra, a.fecha_inicio, a.fecha_fin,
               a.dias, a.importe, a.estado, a.observaciones
        FROM alquileres_maquinaria a
        LEFT JOIN inmovilizado i ON i.id = a.bien_id
        ORDER BY a.fecha_inicio DESC, a.id DESC
        LIMIT %s
    """, conn, params=(int(limit),))
    conn.close()
    return df


def listar_costes_maquinaria(limit=500):
    inicializar_tabla_inmovilizado()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT c.id, i.nombre AS maquina, c.fecha, c.tipo, c.importe, c.proveedor, c.observaciones
        FROM costes_maquinaria c
        LEFT JOIN inmovilizado i ON i.id = c.bien_id
        ORDER BY c.fecha DESC, c.id DESC
        LIMIT %s
    """, conn, params=(int(limit),))
    conn.close()
    return df
