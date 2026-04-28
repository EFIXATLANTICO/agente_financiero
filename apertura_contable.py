import sqlite3
import pandas as pd


def crear_asiento_apertura(df, fecha="2024-01-01", concepto="Asiento de apertura"):

    conexion = sqlite3.connect("database/contabilidad.db")
    cursor = conexion.cursor()

    # crear asiento
    cursor.execute("""
        INSERT INTO asientos (fecha, concepto, tipo_operacion)
        VALUES (, , )
    """, (fecha, concepto, "apertura"))

    asiento_id = cursor.lastrowid

    for _, row in df.iterrows():

        cuenta = str(row["Cuenta"])
        saldo = float(row["Saldo"])

        if saldo > 0:

            cursor.execute("""
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (, , 'debe', )
            """, (asiento_id, cuenta, abs(saldo)))

        else:

            cursor.execute("""
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (, , 'haber', )
            """, (asiento_id, cuenta, abs(saldo)))

    conexion.commit()
    conexion.close()

    return asiento_id