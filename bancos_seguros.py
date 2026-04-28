from datetime import date, datetime

import pandas as pd

from db_context import get_connection


def _hoy():
    return date.today().isoformat()


def inicializar_bancos_seguros():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entidades_financieras (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL UNIQUE,
        tipo TEXT DEFAULT 'banco',
        contacto TEXT,
        telefono TEXT,
        email TEXT,
        observaciones TEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saldos_entidades (
        id SERIAL PRIMARY KEY,
        entidad_id INTEGER REFERENCES entidades_financieras(id),
        producto TEXT,
        iban TEXT,
        saldo REAL NOT NULL DEFAULT 0,
        fecha_saldo TEXT NOT NULL,
        observaciones TEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos_financieros (
        id SERIAL PRIMARY KEY,
        entidad_id INTEGER REFERENCES entidades_financieras(id),
        tipo_producto TEXT NOT NULL,
        nombre TEXT NOT NULL,
        importe_concedido REAL NOT NULL DEFAULT 0,
        importe_dispuesto REAL NOT NULL DEFAULT 0,
        tipo_interes REAL NOT NULL DEFAULT 0,
        fecha_inicio TEXT,
        fecha_vencimiento TEXT,
        cuota REAL NOT NULL DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'vigente',
        observaciones TEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seguros_empresa (
        id SERIAL PRIMARY KEY,
        entidad_id INTEGER REFERENCES entidades_financieras(id),
        compania TEXT,
        ramo TEXT NOT NULL,
        poliza TEXT,
        bien_asegurado TEXT,
        prima_anual REAL NOT NULL DEFAULT 0,
        fecha_inicio TEXT,
        fecha_vencimiento TEXT,
        estado TEXT NOT NULL DEFAULT 'vigente',
        observaciones TEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

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

    migraciones_movimientos = [
        "ALTER TABLE movimientos_banco ADD COLUMN IF NOT EXISTS fecha TEXT",
        "ALTER TABLE movimientos_banco ADD COLUMN IF NOT EXISTS concepto TEXT",
        "ALTER TABLE movimientos_banco ADD COLUMN IF NOT EXISTS importe REAL",
        "ALTER TABLE movimientos_banco ADD COLUMN IF NOT EXISTS sentido TEXT",
        "ALTER TABLE movimientos_banco ADD COLUMN IF NOT EXISTS saldo REAL",
        "ALTER TABLE movimientos_banco ADD COLUMN IF NOT EXISTS referencia TEXT",
        "ALTER TABLE movimientos_banco ADD COLUMN IF NOT EXISTS estado_conciliacion TEXT DEFAULT 'pendiente'",
        "ALTER TABLE movimientos_banco ADD COLUMN IF NOT EXISTS revisado INTEGER DEFAULT 0",
        """
        UPDATE movimientos_banco
        SET sentido = CASE WHEN importe < 0 THEN 'pago' ELSE 'ingreso' END
        WHERE sentido IS NULL
        """,
        """
        UPDATE movimientos_banco
        SET estado_conciliacion = 'pendiente'
        WHERE estado_conciliacion IS NULL
        """,
        """
        UPDATE movimientos_banco
        SET revisado = 0
        WHERE revisado IS NULL
        """,
    ]

    for sql in migraciones_movimientos:
        cursor.execute(sql)

    conn.commit()
    conn.close()


def listar_entidades():
    inicializar_bancos_seguros()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT id, nombre, tipo, contacto, telefono, email, observaciones
        FROM entidades_financieras
        ORDER BY nombre
    """, conn)
    conn.close()
    return df


def crear_entidad(nombre, tipo="banco", contacto="", telefono="", email="", observaciones=""):
    inicializar_bancos_seguros()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO entidades_financieras (nombre, tipo, contacto, telefono, email, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (nombre) DO UPDATE
        SET tipo = EXCLUDED.tipo,
            contacto = EXCLUDED.contacto,
            telefono = EXCLUDED.telefono,
            email = EXCLUDED.email,
            observaciones = EXCLUDED.observaciones
        RETURNING id
    """, (nombre.strip(), tipo, contacto, telefono, email, observaciones))
    entidad_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return entidad_id


def opciones_entidades():
    df = listar_entidades()
    if df.empty:
        return {}
    return {f"{row['nombre']} ({row['tipo']})": int(row["id"]) for _, row in df.iterrows()}


def registrar_saldo(entidad_id, producto, iban, saldo, fecha_saldo=None, observaciones=""):
    inicializar_bancos_seguros()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO saldos_entidades (entidad_id, producto, iban, saldo, fecha_saldo, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (entidad_id, producto, iban, float(saldo or 0), fecha_saldo or _hoy(), observaciones))
    saldo_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return saldo_id


def listar_saldos():
    inicializar_bancos_seguros()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            s.id,
            e.nombre AS entidad,
            s.producto,
            s.iban,
            s.saldo,
            s.fecha_saldo,
            s.observaciones
        FROM saldos_entidades s
        LEFT JOIN entidades_financieras e ON e.id = s.entidad_id
        ORDER BY s.fecha_saldo DESC, s.id DESC
    """, conn)
    conn.close()
    return df


def registrar_producto_financiero(
    entidad_id,
    tipo_producto,
    nombre,
    importe_concedido=0,
    importe_dispuesto=0,
    tipo_interes=0,
    fecha_inicio=None,
    fecha_vencimiento=None,
    cuota=0,
    estado="vigente",
    observaciones="",
):
    inicializar_bancos_seguros()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO productos_financieros (
            entidad_id, tipo_producto, nombre, importe_concedido, importe_dispuesto,
            tipo_interes, fecha_inicio, fecha_vencimiento, cuota, estado, observaciones
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        entidad_id, tipo_producto, nombre, float(importe_concedido or 0),
        float(importe_dispuesto or 0), float(tipo_interes or 0), fecha_inicio,
        fecha_vencimiento, float(cuota or 0), estado, observaciones
    ))
    producto_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return producto_id


def listar_productos_financieros():
    inicializar_bancos_seguros()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            p.id,
            e.nombre AS entidad,
            p.tipo_producto,
            p.nombre,
            p.importe_concedido,
            p.importe_dispuesto,
            ROUND((p.importe_concedido - p.importe_dispuesto)::numeric, 2) AS disponible,
            p.tipo_interes,
            p.fecha_inicio,
            p.fecha_vencimiento,
            p.cuota,
            p.estado,
            p.observaciones
        FROM productos_financieros p
        LEFT JOIN entidades_financieras e ON e.id = p.entidad_id
        ORDER BY p.estado, p.fecha_vencimiento NULLS LAST, p.id DESC
    """, conn)
    conn.close()
    return df


def registrar_seguro(
    entidad_id,
    compania,
    ramo,
    poliza="",
    bien_asegurado="",
    prima_anual=0,
    fecha_inicio=None,
    fecha_vencimiento=None,
    estado="vigente",
    observaciones="",
):
    inicializar_bancos_seguros()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO seguros_empresa (
            entidad_id, compania, ramo, poliza, bien_asegurado, prima_anual,
            fecha_inicio, fecha_vencimiento, estado, observaciones
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        entidad_id, compania, ramo, poliza, bien_asegurado, float(prima_anual or 0),
        fecha_inicio, fecha_vencimiento, estado, observaciones
    ))
    seguro_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return seguro_id


def listar_seguros():
    inicializar_bancos_seguros()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            s.id,
            COALESCE(e.nombre, s.compania) AS entidad_o_compania,
            s.ramo,
            s.poliza,
            s.bien_asegurado,
            s.prima_anual,
            s.fecha_inicio,
            s.fecha_vencimiento,
            s.estado,
            s.observaciones
        FROM seguros_empresa s
        LEFT JOIN entidades_financieras e ON e.id = s.entidad_id
        ORDER BY s.estado, s.fecha_vencimiento NULLS LAST, s.id DESC
    """, conn)
    conn.close()
    return df


def listar_movimientos_bancarios(limit=500):
    inicializar_bancos_seguros()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT id, fecha, concepto, importe, sentido, saldo, referencia, estado_conciliacion, revisado
        FROM movimientos_banco
        ORDER BY fecha DESC NULLS LAST, id DESC
        LIMIT %s
    """, conn, params=(int(limit),))
    conn.close()
    return df
