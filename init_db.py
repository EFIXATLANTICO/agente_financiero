from db_context import get_connection


def inicializar_bd_empresa():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        concepto TEXT NOT NULL,
        tipo_operacion TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lineas_asiento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asiento_id INTEGER NOT NULL,
        cuenta TEXT NOT NULL,
        movimiento TEXT NOT NULL CHECK(movimiento IN ('debe', 'haber')),
        importe REAL NOT NULL DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        nif TEXT,
        direccion TEXT,
        email TEXT,
        telefono TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        nif TEXT,
        direccion TEXT,
        email TEXT,
        telefono TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS facturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER,
        tipo TEXT NOT NULL,
        serie TEXT,
        numero_factura TEXT,
        tercero_id INTEGER,
        nombre_tercero TEXT NOT NULL,
        nif_tercero TEXT,
        fecha_emision TEXT NOT NULL,
        fecha_operacion TEXT,
        fecha_vencimiento TEXT,
        concepto TEXT,
        base_imponible REAL NOT NULL DEFAULT 0,
        tipo_impuesto TEXT DEFAULT 'IGIC',
        impuesto_pct REAL NOT NULL DEFAULT 0,
        cuota_impuesto REAL NOT NULL DEFAULT 0,
        total REAL NOT NULL DEFAULT 0,
        moneda TEXT DEFAULT 'EUR',
        estado TEXT DEFAULT 'pendiente',
        forma_pago TEXT,
        observaciones TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS importaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL,
        nombre_archivo TEXT,
        hash_archivo TEXT,
        fecha_importacion TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asientos_importacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        importacion_id INTEGER NOT NULL,
        asiento_id INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER,
        tipo_operacion TEXT,
        fecha_operacion TEXT,
        concepto TEXT,
        nombre_tercero TEXT,
        numero_factura TEXT,
        forma_pago TEXT,
        base_imponible REAL DEFAULT 0,
        impuesto_pct REAL DEFAULT 0,
        cuota_impuesto REAL DEFAULT 0,
        total REAL DEFAULT 0,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operaciones_asientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operacion_id INTEGER NOT NULL,
        asiento_id INTEGER NOT NULL,
        UNIQUE(operacion_id, asiento_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS validaciones_contables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER,
        fecha TEXT,
        origen TEXT,
        referencia_id INTEGER,
        estado TEXT,
        mensaje TEXT,
        detalle TEXT,
        bloqueante INTEGER DEFAULT 0,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vencimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factura_id INTEGER,
        fecha_vencimiento TEXT,
        importe REAL DEFAULT 0,
        estado TEXT DEFAULT 'pendiente',
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS movimientos_banco (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        concepto TEXT,
        importe REAL NOT NULL,
        estado_conciliacion TEXT DEFAULT 'pendiente',
        revisado INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS conciliaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movimiento_id INTEGER NOT NULL,
        factura_id INTEGER NOT NULL,
        importe_aplicado REAL NOT NULL,
        fecha_conciliacion TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inmovilizado (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        fecha_compra TEXT,
        fecha_inicio_amortizacion TEXT,
        coste REAL DEFAULT 0,
        valor_residual REAL DEFAULT 0,
        vida_util_anios REAL DEFAULT 0,
        cuenta_inmovilizado TEXT,
        cuenta_amort_acumulada TEXT,
        cuenta_gasto_amortizacion TEXT,
        observaciones TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS amortizaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inmovilizado_id INTEGER NOT NULL,
        ejercicio INTEGER,
        mes INTEGER,
        importe REAL DEFAULT 0,
        asiento_id INTEGER,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # MIGRACIONES SUAVES (no rompe BDs existentes)
    try:
        cur.execute("ALTER TABLE facturas ADD COLUMN forma_pago TEXT")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE facturas ADD COLUMN observaciones TEXT")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE movimientos_banco ADD COLUMN revisado INTEGER DEFAULT 0")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE vencimientos ADD COLUMN importe REAL DEFAULT 0")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE vencimientos ADD COLUMN estado TEXT DEFAULT 'pendiente'")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE vencimientos ADD COLUMN creado_en TEXT DEFAULT CURRENT_TIMESTAMP")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE vencimientos ADD COLUMN importe_pendiente REAL DEFAULT 0")
    except Exception:
        pass
    cur.execute("""
    CREATE TABLE IF NOT EXISTS incidencias_importacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        importacion_id INTEGER,
        tipo_importacion TEXT,
        fila_excel INTEGER,
        fecha TEXT,
        concepto TEXT,
        detalle_error TEXT,
        estado TEXT DEFAULT 'pendiente',
        datos_json TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

