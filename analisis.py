import sqlite3

conexion = sqlite3.connect("database/contabilidad.db")
cursor = conexion.cursor()


def resumen_empresa():

    print("\nRESUMEN FINANCIERO\n")

    # ventas
    cursor.execute("""
    SELECT SUM(importe)
    FROM lineas_asiento
    WHERE cuenta = '700 Ventas'
    """)
    ventas = cursor.fetchone()[0] or 0

    # compras
    cursor.execute("""
    SELECT SUM(importe)
    FROM lineas_asiento
    WHERE cuenta = '600 Compras'
    """)
    compras = cursor.fetchone()[0] or 0

    # IGIC soportado
    cursor.execute("""
    SELECT SUM(importe)
    FROM lineas_asiento
    WHERE cuenta = '472 IGIC soportado'
    """)
    igic_soportado = cursor.fetchone()[0] or 0

    # IGIC repercutido
    cursor.execute("""
    SELECT SUM(importe)
    FROM lineas_asiento
    WHERE cuenta = '477 IGIC repercutido'
    """)
    igic_repercutido = cursor.fetchone()[0] or 0

    # banco
    cursor.execute("""
    SELECT
        SUM(CASE WHEN movimiento = 'debe' THEN importe ELSE -importe END)
    FROM lineas_asiento
    WHERE cuenta = '572 Bancos'
    """)
    banco = cursor.fetchone()[0] or 0

    print("Ventas totales:", ventas)
    print("Compras totales:", compras)
    print("IGIC soportado:", igic_soportado)
    print("IGIC repercutido:", igic_repercutido)
    print("IGIC a pagar:", igic_repercutido - igic_soportado)
    print("Saldo bancos:", banco)