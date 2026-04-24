from db_context import get_connection


def columna_existe(cursor, tabla, columna):
    cursor.execute(f"PRAGMA table_info({tabla})")
    columnas = cursor.fetchall()
    nombres = [c[1] for c in columnas]
    return columna in nombres


def agregar_columna_si_falta(cursor, tabla, columna, definicion_sql):
    if not columna_existe(cursor, tabla, columna):
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion_sql}")


def migrar_bd_empresa():
    conn = get_connection()
    cursor = conn.cursor()

    # CLIENTES
    agregar_columna_si_falta(cursor, "clientes", "email", "TEXT")
    agregar_columna_si_falta(cursor, "clientes", "telefono", "TEXT")

    # PROVEEDORES
    agregar_columna_si_falta(cursor, "proveedores", "email", "TEXT")
    agregar_columna_si_falta(cursor, "proveedores", "telefono", "TEXT")

    # FACTURAS (por si alguna BD antigua va atrasada)
    agregar_columna_si_falta(cursor, "facturas", "serie", "TEXT")
    agregar_columna_si_falta(cursor, "facturas", "numero_factura", "TEXT")
    agregar_columna_si_falta(cursor, "facturas", "tercero_id", "INTEGER")
    agregar_columna_si_falta(cursor, "facturas", "nif_tercero", "TEXT")
    agregar_columna_si_falta(cursor, "facturas", "fecha_emision", "TEXT")
    agregar_columna_si_falta(cursor, "facturas", "fecha_operacion", "TEXT")
    agregar_columna_si_falta(cursor, "facturas", "fecha_vencimiento", "TEXT")
    agregar_columna_si_falta(cursor, "facturas", "base_imponible", "REAL DEFAULT 0")
    agregar_columna_si_falta(cursor, "facturas", "tipo_impuesto", "TEXT DEFAULT 'IGIC'")
    agregar_columna_si_falta(cursor, "facturas", "impuesto_pct", "REAL DEFAULT 0")
    agregar_columna_si_falta(cursor, "facturas", "cuota_impuesto", "REAL DEFAULT 0")
    agregar_columna_si_falta(cursor, "facturas", "moneda", "TEXT DEFAULT 'EUR'")
    agregar_columna_si_falta(cursor, "facturas", "forma_pago", "TEXT")
    agregar_columna_si_falta(cursor, "facturas", "observaciones", "TEXT")
    agregar_columna_si_falta(cursor, "facturas", "creado_en", "TEXT")

    conn.commit()
    conn.close()

    return "ok"