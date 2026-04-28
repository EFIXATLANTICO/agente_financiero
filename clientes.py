def guardar_scoring_cliente(cliente_id, puntuacion, color, motivo, fecha_revision):
    from db_context import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scoring_clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                puntuacion REAL,
                color TEXT,
                motivo TEXT,
                fecha_revision TEXT
            )
        """)

        cursor.execute("""
            INSERT INTO scoring_clientes (cliente_id, puntuacion, color, motivo, fecha_revision)
            VALUES (, , , , )
        """, (cliente_id, puntuacion, color, motivo, fecha_revision))

        conn.commit()
    finally:
        conn.close()


def calcular_scoring_cliente(cliente_id):
    from db_context import get_connection
    import datetime

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Volumen total facturado al cliente
        cursor.execute("""
            SELECT COALESCE(SUM(total), 0)
            FROM facturas
            WHERE tercero_id = 
              AND tipo = 'venta'
        """, (cliente_id,))
        total_facturado = float(cursor.fetchone()[0] or 0)

        # 2. Numero de facturas pendientes o parciales
        cursor.execute("""
            SELECT COUNT(*)
            FROM facturas
            WHERE tercero_id = 
              AND tipo = 'venta'
              AND estado IN ('pendiente', 'cobro_parcial')
        """, (cliente_id,))
        pendientes = int(cursor.fetchone()[0] or 0)

        # 3. Saldo pendiente
        cursor.execute("""
            SELECT COALESCE(SUM(total), 0)
            FROM facturas
            WHERE tercero_id = 
              AND tipo = 'venta'
              AND estado IN ('pendiente', 'cobro_parcial')
        """, (cliente_id,))
        saldo_pendiente = float(cursor.fetchone()[0] or 0)

        # 4. Antiguedad maxima de deuda
        cursor.execute("""
            SELECT MAX(julianday('now') - julianday(fecha_emision))
            FROM facturas
            WHERE tercero_id = 
              AND tipo = 'venta'
              AND estado IN ('pendiente', 'cobro_parcial')
        """, (cliente_id,))
        dias_deuda = float(cursor.fetchone()[0] or 0)

    finally:
        conn.close()

    puntuacion = 100
    motivos = []

    if pendientes >= 5:
        puntuacion -= 25
        motivos.append("Muchas facturas pendientes")

    if saldo_pendiente > 3000:
        puntuacion -= 20
        motivos.append("Saldo pendiente elevado")

    if dias_deuda > 90:
        puntuacion -= 35
        motivos.append("Deuda antigua (+90 dias)")
    elif dias_deuda > 45:
        puntuacion -= 15
        motivos.append("Deuda media (+45 dias)")

    if total_facturado < 1000:
        puntuacion -= 10
        motivos.append("Historico de negocio bajo")

    puntuacion = max(0, min(100, puntuacion))

    if puntuacion >= 70:
        color = "verde"
        decision = "trabajar"
    elif puntuacion >= 40:
        color = "amarillo"
        decision = "trabajar_con_limites"
    else:
        color = "rojo"
        decision = "revisar_o_bloquear"

    return {
        "puntuacion": puntuacion,
        "color": color,
        "motivo": " | ".join(motivos) if motivos else "Cliente sin incidencias relevantes",
        "fecha_revision": datetime.date.today().isoformat(),
        "decision": decision,
        "saldo_pendiente": saldo_pendiente,
        "dias_deuda": round(dias_deuda, 0),
        "total_facturado": total_facturado,
        "pendientes": pendientes,
    }


def recalcular_y_guardar_scoring(cliente_id):
    datos = calcular_scoring_cliente(cliente_id)

    guardar_scoring_cliente(
        cliente_id,
        datos["puntuacion"],
        datos["color"],
        datos["motivo"],
        datos["fecha_revision"]
    )

    return datos


