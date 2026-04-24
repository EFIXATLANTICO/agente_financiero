import sqlite3

conn = sqlite3.connect("database/empresas/empresa_1.db")
cursor = conn.cursor()

# =========================
# TABLA OPERACIONES
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS operaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    tipo_operacion TEXT NOT NULL,
    fecha_operacion TEXT NOT NULL,
    departamento TEXT,
    concepto TEXT NOT NULL,
    tercero_id INTEGER,
    nombre_tercero TEXT,
    numero_factura TEXT,
    forma_pago TEXT,
    pago_tipo TEXT DEFAULT 'total',
    porcentaje_anticipo REAL DEFAULT 0,
    importe_anticipo REAL DEFAULT 0,
    importe_pendiente REAL DEFAULT 0,
    base_imponible REAL DEFAULT 0,
    tipo_impuesto TEXT DEFAULT 'IGIC',
    impuesto_pct REAL DEFAULT 0,
    cuota_impuesto REAL DEFAULT 0,
    total REAL DEFAULT 0,
    estado TEXT DEFAULT 'registrada',
    observaciones TEXT,
    creado_en TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# =========================
# TABLA FACTURAS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS facturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    serie TEXT,
    numero_factura TEXT NOT NULL,
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
    estado TEXT NOT NULL DEFAULT 'pendiente',
    forma_pago TEXT,
    observaciones TEXT,
    creado_en TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# =========================
# TABLA VENCIMIENTOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS vencimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    factura_id INTEGER,
    tipo TEXT NOT NULL,
    tercero_id INTEGER,
    nombre_tercero TEXT NOT NULL,
    fecha_emision TEXT,
    fecha_vencimiento TEXT NOT NULL,
    importe_total REAL NOT NULL DEFAULT 0,
    importe_cobrado_pagado REAL NOT NULL DEFAULT 0,
    importe_pendiente REAL NOT NULL DEFAULT 0,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    forma_pago TEXT,
    numero_efecto TEXT,
    observaciones TEXT,
    creado_en TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# =========================
# TABLA VALIDACIONES CONTABLES
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS validaciones_contables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    origen TEXT NOT NULL,
    referencia_id INTEGER,
    estado TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    detalle TEXT,
    bloqueante INTEGER NOT NULL DEFAULT 0,
    creado_en TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# =========================
# TABLA OPERACIONES_ASIENTOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS operaciones_asientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    operacion_id INTEGER NOT NULL,
    asiento_id INTEGER NOT NULL,
    creado_en TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Nuevas tablas creadas correctamente")

CREATE TABLE IF NOT EXISTS scoring_clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    puntuacion INTEGER NOT NULL,
    color TEXT NOT NULL,
    motivo TEXT,
    fecha_revision TEXT NOT NULL
)
CREATE TABLE IF NOT EXISTS vencimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER,
    tipo TEXT,
    tercero TEXT,
    fecha_vencimiento TEXT,
    importe_total REAL,
    importe_pendiente REAL,
    estado TEXT
)
CREATE TABLE IF NOT EXISTS modelos_fiscales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modelo TEXT NOT NULL,
    periodo TEXT NOT NULL,
    fecha_presentacion TEXT,
    fecha_limite TEXT,
    estado TEXT,
    observaciones TEXT
)
CREATE TABLE IF NOT EXISTS modelos_fiscales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modelo TEXT NOT NULL,
    periodo TEXT NOT NULL,
    fecha_presentacion TEXT,
    fecha_limite TEXT,
    estado TEXT,
    observaciones TEXT
)
CREATE TABLE IF NOT EXISTS movimientos_bancarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    concepto TEXT NOT NULL,
    importe REAL NOT NULL,
    saldo REAL,
    conciliado INTEGER DEFAULT 0,
    referencia TEXT,
    observaciones TEXT
)
CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    prioridad TEXT NOT NULL,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    fecha_alerta TEXT NOT NULL,
    estado TEXT DEFAULT 'pendiente',
    referencia_tabla TEXT,
    referencia_id INTEGER
)
CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    prioridad TEXT NOT NULL,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    fecha_alerta TEXT NOT NULL,
    estado TEXT DEFAULT 'pendiente',
    referencia_tabla TEXT,
    referencia_id INTEGER
)
CREATE TABLE IF NOT EXISTS presentaciones_fiscales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modelo TEXT,
    periodo TEXT,
    fecha_presentacion TEXT,
    resultado TEXT,
    observaciones TEXT
)
CREATE TABLE IF NOT EXISTS reglas_empresa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clave TEXT NOT NULL,
    valor TEXT NOT NULL
)