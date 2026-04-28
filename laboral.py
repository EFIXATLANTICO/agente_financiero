import pandas as pd

from db_context import get_connection


def inicializar_laboral():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trabajadores (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        nif TEXT,
        puesto TEXT,
        tipo_contrato TEXT,
        fecha_alta TEXT,
        fecha_baja TEXT,
        salario_bruto_anual REAL NOT NULL DEFAULT 0,
        irpf_porcentaje REAL NOT NULL DEFAULT 0,
        seguridad_social_trabajador REAL NOT NULL DEFAULT 0,
        seguridad_social_empresa REAL NOT NULL DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'activo',
        observaciones TEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nominas (
        id SERIAL PRIMARY KEY,
        trabajador_id INTEGER REFERENCES trabajadores(id),
        periodo TEXT NOT NULL,
        fecha_pago TEXT,
        salario_bruto REAL NOT NULL DEFAULT 0,
        irpf REAL NOT NULL DEFAULT 0,
        seguridad_social_trabajador REAL NOT NULL DEFAULT 0,
        seguridad_social_empresa REAL NOT NULL DEFAULT 0,
        salario_neto REAL NOT NULL DEFAULT 0,
        coste_empresa REAL NOT NULL DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'pendiente',
        observaciones TEXT,
        asiento_id INTEGER,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS impuestos_laborales (
        id SERIAL PRIMARY KEY,
        periodo TEXT NOT NULL,
        tipo TEXT NOT NULL,
        importe REAL NOT NULL DEFAULT 0,
        fecha_vencimiento TEXT,
        fecha_pago TEXT,
        estado TEXT NOT NULL DEFAULT 'pendiente',
        observaciones TEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def listar_trabajadores(solo_activos=False):
    inicializar_laboral()
    conn = get_connection()
    query = """
        SELECT id, nombre, nif, puesto, tipo_contrato, fecha_alta, fecha_baja,
               salario_bruto_anual, irpf_porcentaje, seguridad_social_trabajador,
               seguridad_social_empresa, estado, observaciones
        FROM trabajadores
    """
    if solo_activos:
        query += " WHERE estado = 'activo'"
    query += " ORDER BY estado, nombre"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def crear_trabajador(
    nombre,
    nif="",
    puesto="",
    tipo_contrato="indefinido",
    fecha_alta=None,
    fecha_baja=None,
    salario_bruto_anual=0,
    irpf_porcentaje=0,
    seguridad_social_trabajador=0,
    seguridad_social_empresa=0,
    estado="activo",
    observaciones="",
):
    inicializar_laboral()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trabajadores (
            nombre, nif, puesto, tipo_contrato, fecha_alta, fecha_baja,
            salario_bruto_anual, irpf_porcentaje, seguridad_social_trabajador,
            seguridad_social_empresa, estado, observaciones
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        nombre.strip(), nif, puesto, tipo_contrato, fecha_alta, fecha_baja,
        float(salario_bruto_anual or 0), float(irpf_porcentaje or 0),
        float(seguridad_social_trabajador or 0), float(seguridad_social_empresa or 0),
        estado, observaciones
    ))
    trabajador_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return trabajador_id


def opciones_trabajadores():
    df = listar_trabajadores(solo_activos=True)
    if df.empty:
        return {}
    return {f"{row['nombre']} ({row['nif'] or 'sin NIF'})": int(row["id"]) for _, row in df.iterrows()}


def registrar_nomina(
    trabajador_id,
    periodo,
    fecha_pago=None,
    salario_bruto=0,
    irpf=0,
    seguridad_social_trabajador=0,
    seguridad_social_empresa=0,
    estado="pendiente",
    observaciones="",
):
    salario_bruto = float(salario_bruto or 0)
    irpf = float(irpf or 0)
    ss_trab = float(seguridad_social_trabajador or 0)
    ss_emp = float(seguridad_social_empresa or 0)
    salario_neto = round(salario_bruto - irpf - ss_trab, 2)
    coste_empresa = round(salario_bruto + ss_emp, 2)

    inicializar_laboral()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO nominas (
            trabajador_id, periodo, fecha_pago, salario_bruto, irpf,
            seguridad_social_trabajador, seguridad_social_empresa,
            salario_neto, coste_empresa, estado, observaciones
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        trabajador_id, periodo, fecha_pago, salario_bruto, irpf, ss_trab, ss_emp,
        salario_neto, coste_empresa, estado, observaciones
    ))
    nomina_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return nomina_id


def listar_nominas():
    inicializar_laboral()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT n.id, t.nombre AS trabajador, n.periodo, n.fecha_pago,
               n.salario_bruto, n.irpf, n.seguridad_social_trabajador,
               n.seguridad_social_empresa, n.salario_neto, n.coste_empresa,
               n.estado, n.observaciones
        FROM nominas n
        LEFT JOIN trabajadores t ON t.id = n.trabajador_id
        ORDER BY n.periodo DESC, n.id DESC
    """, conn)
    conn.close()
    return df


def registrar_impuesto_laboral(periodo, tipo, importe, fecha_vencimiento=None, fecha_pago=None, estado="pendiente", observaciones=""):
    inicializar_laboral()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO impuestos_laborales (
            periodo, tipo, importe, fecha_vencimiento, fecha_pago, estado, observaciones
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        periodo, tipo, float(importe or 0), fecha_vencimiento, fecha_pago, estado, observaciones
    ))
    impuesto_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return impuesto_id


def listar_impuestos_laborales():
    inicializar_laboral()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT id, periodo, tipo, importe, fecha_vencimiento, fecha_pago, estado, observaciones
        FROM impuestos_laborales
        ORDER BY estado, fecha_vencimiento NULLS LAST, id DESC
    """, conn)
    conn.close()
    return df
