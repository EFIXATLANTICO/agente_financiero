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
        asiento_id INTEGER,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("ALTER TABLE nominas ADD COLUMN IF NOT EXISTS asiento_id INTEGER")
    cursor.execute("ALTER TABLE impuestos_laborales ADD COLUMN IF NOT EXISTS asiento_id INTEGER")

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
               n.estado, n.observaciones, n.asiento_id
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
               , asiento_id
        FROM impuestos_laborales
        ORDER BY estado, fecha_vencimiento NULLS LAST, id DESC
    """, conn)
    conn.close()
    return df


def contabilizar_nomina(nomina_id, fecha_asiento=None, pagar_en_mismo_asiento=True, cuenta_pago="572 Bancos"):
    from contabilidad import crear_asiento_completo

    inicializar_laboral()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.id, t.nombre, n.periodo, n.fecha_pago, n.salario_bruto, n.irpf,
               n.seguridad_social_trabajador, n.seguridad_social_empresa,
               n.salario_neto, n.asiento_id
        FROM nominas n
        LEFT JOIN trabajadores t ON t.id = n.trabajador_id
        WHERE n.id = %s
    """, (nomina_id,))
    fila = cursor.fetchone()
    conn.close()

    if not fila:
        return {"ok": False, "mensaje": "Nomina no encontrada"}

    _, trabajador, periodo, fecha_pago, bruto, irpf, ss_trab, ss_emp, neto, asiento_id = fila
    if asiento_id:
        return {"ok": False, "mensaje": f"Esta nomina ya esta contabilizada en el asiento {asiento_id}"}

    bruto = float(bruto or 0)
    irpf = float(irpf or 0)
    ss_trab = float(ss_trab or 0)
    ss_emp = float(ss_emp or 0)
    neto = float(neto or 0)

    if bruto <= 0:
        return {"ok": False, "mensaje": "El salario bruto debe ser mayor que cero"}

    fecha_asiento = fecha_asiento or fecha_pago
    concepto = f"Nomina {periodo} - {trabajador or 'trabajador'}"
    lineas = [
        ("640 Sueldos y salarios", "debe", bruto),
    ]

    if ss_emp > 0:
        lineas.append(("642 Seguridad Social a cargo de la empresa", "debe", ss_emp))
    if irpf > 0:
        lineas.append(("4751 Hacienda acreedora por retenciones", "haber", irpf))
    if ss_trab + ss_emp > 0:
        lineas.append(("476 Organismos Seguridad Social acreedores", "haber", ss_trab + ss_emp))
    if neto > 0:
        lineas.append(("465 Remuneraciones pendientes de pago", "haber", neto))

    if pagar_en_mismo_asiento and neto > 0:
        lineas.append(("465 Remuneraciones pendientes de pago", "debe", neto))
        lineas.append((cuenta_pago, "haber", neto))

    asiento_id_nuevo = crear_asiento_completo(fecha_asiento, concepto, "nomina", lineas)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE nominas
        SET asiento_id = %s, estado = %s
        WHERE id = %s
    """, (asiento_id_nuevo, "pagada" if pagar_en_mismo_asiento else "contabilizada", nomina_id))
    conn.commit()
    conn.close()

    return {"ok": True, "mensaje": f"Nomina contabilizada en asiento {asiento_id_nuevo}", "asiento_id": asiento_id_nuevo}


def contabilizar_pago_impuesto_laboral(impuesto_id, fecha_pago=None, cuenta_pago="572 Bancos"):
    from contabilidad import crear_asiento_completo

    inicializar_laboral()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, periodo, tipo, importe, fecha_pago, asiento_id
        FROM impuestos_laborales
        WHERE id = %s
    """, (impuesto_id,))
    fila = cursor.fetchone()
    conn.close()

    if not fila:
        return {"ok": False, "mensaje": "Impuesto laboral no encontrado"}

    impuesto_id, periodo, tipo, importe, fecha_pago_bd, asiento_id = fila
    if asiento_id:
        return {"ok": False, "mensaje": f"Este impuesto ya esta contabilizado en el asiento {asiento_id}"}

    importe = float(importe or 0)
    if importe <= 0:
        return {"ok": False, "mensaje": "El importe debe ser mayor que cero"}

    tipo_normalizado = str(tipo or "").lower()
    cuenta_debe = "476 Organismos Seguridad Social acreedores"
    if "irpf" in tipo_normalizado or "111" in tipo_normalizado or "retencion" in tipo_normalizado:
        cuenta_debe = "4751 Hacienda acreedora por retenciones"

    fecha_asiento = fecha_pago or fecha_pago_bd
    concepto = f"Pago {tipo} {periodo}"
    lineas = [
        (cuenta_debe, "debe", importe),
        (cuenta_pago, "haber", importe),
    ]
    asiento_id_nuevo = crear_asiento_completo(fecha_asiento, concepto, "pago_impuesto_laboral", lineas)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE impuestos_laborales
        SET asiento_id = %s, estado = 'pagado', fecha_pago = %s
        WHERE id = %s
    """, (asiento_id_nuevo, fecha_asiento, impuesto_id))
    conn.commit()
    conn.close()

    return {"ok": True, "mensaje": f"Impuesto laboral contabilizado en asiento {asiento_id_nuevo}", "asiento_id": asiento_id_nuevo}
