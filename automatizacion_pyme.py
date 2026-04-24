import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "database/contabilidad.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def acciones_sugeridas():
    conn = get_connection()
    acciones = []

    # Facturas de venta pendientes
    try:
        df_ventas = pd.read_sql_query("""
        SELECT id, tipo, nombre_tercero, fecha, total, estado, concepto
        FROM facturas
        WHERE tipo = 'venta' AND estado = 'pendiente'
        ORDER BY fecha
        """, conn)

        hoy = datetime.today().date()

        for _, row in df_ventas.iterrows():
            try:
                fecha_factura = pd.to_datetime(row["fecha"]).date()
                dias = (hoy - fecha_factura).days
            except Exception:
                dias = 0

            if dias >= 30:
                acciones.append({
                    "Tipo": "Cobro vencido",
                    "Prioridad": "Alta",
                    "Referencia": f"Factura {row['id']}",
                    "Tercero": row["nombre_tercero"],
                    "Acción sugerida": "Enviar recordatorio de cobro",
                    "Detalle": f"{dias} días desde la factura. Importe: {row['total']:.2f} €"
                })
            elif dias >= 7:
                acciones.append({
                    "Tipo": "Seguimiento cobro",
                    "Prioridad": "Media",
                    "Referencia": f"Factura {row['id']}",
                    "Tercero": row["nombre_tercero"],
                    "Acción sugerida": "Revisar cobro pendiente",
                    "Detalle": f"{dias} días desde la factura. Importe: {row['total']:.2f} €"
                })
    except Exception:
        pass

    # Compras pendientes
    try:
        df_compras = pd.read_sql_query("""
        SELECT id, tipo, nombre_tercero, fecha, total, estado, concepto
        FROM facturas
        WHERE tipo = 'compra' AND estado = 'pendiente'
        ORDER BY fecha
        """, conn)

        for _, row in df_compras.iterrows():
            acciones.append({
                "Tipo": "Pago pendiente",
                "Prioridad": "Media",
                "Referencia": f"Factura {row['id']}",
                "Tercero": row["nombre_tercero"],
                "Acción sugerida": "Revisar pago a proveedor",
                "Detalle": f"Importe pendiente: {row['total']:.2f} €"
            })
    except Exception:
        pass

    # Movimientos bancarios pendientes
    try:
        df_banco = pd.read_sql_query("""
        SELECT id, fecha, concepto, importe, estado_conciliacion
        FROM movimientos_banco
        WHERE estado_conciliacion = 'pendiente'
        ORDER BY fecha
        """, conn)

        for _, row in df_banco.iterrows():
            acciones.append({
                "Tipo": "Banco pendiente",
                "Prioridad": "Alta",
                "Referencia": f"Movimiento {row['id']}",
                "Tercero": "-",
                "Acción sugerida": "Conciliar movimiento bancario",
                "Detalle": f"{row['fecha']} | {row['concepto']} | {row['importe']:.2f} €"
            })
    except Exception:
        pass

    conn.close()

    if not acciones:
        return pd.DataFrame(columns=["Tipo", "Prioridad", "Referencia", "Tercero", "Acción sugerida", "Detalle"])

    return pd.DataFrame(acciones)


def facturas_pendientes_cobro():
    conn = get_connection()
    try:
        df = pd.read_sql_query("""
        SELECT id, nombre_tercero, fecha, total, estado, concepto
        FROM facturas
        WHERE tipo = 'venta' AND estado = 'pendiente'
        ORDER BY fecha
        """, conn)
    finally:
        conn.close()
    return df


def facturas_pendientes_pago():
    conn = get_connection()
    try:
        df = pd.read_sql_query("""
        SELECT id, nombre_tercero, fecha, total, estado, concepto
        FROM facturas
        WHERE tipo = 'compra' AND estado = 'pendiente'
        ORDER BY fecha
        """, conn)
    finally:
        conn.close()
    return df


def generar_email_recordatorio_cobro(nombre_cliente, factura_id, importe, fecha_factura):
    asunto = f"Recordatorio de pago - Factura {factura_id}"
    cuerpo = f"""Estimado/a {nombre_cliente},

Le escribimos para recordarle que la factura {factura_id}, emitida con fecha {fecha_factura}, por importe de {importe:.2f} €, figura actualmente como pendiente de cobro.

Le agradeceríamos que revisara el estado del pago y, en caso de estar ya realizado, nos lo indicara para actualizar nuestro registro.

Quedamos a su disposición para cualquier aclaración.

Un saludo,
Administración
"""
    return asunto, cuerpo


def generar_email_envio_factura(nombre_cliente, factura_id, importe, fecha_factura):
    asunto = f"Envío de factura {factura_id}"
    cuerpo = f"""Estimado/a {nombre_cliente},

Le remitimos la factura {factura_id}, de fecha {fecha_factura}, por importe de {importe:.2f} €.

Quedamos a su disposición para cualquier consulta.

Un saludo,
Administración
"""
    return asunto, cuerpo


def generar_email_proveedor(nombre_proveedor, factura_id, importe, fecha_factura):
    asunto = f"Revisión de factura de proveedor {factura_id}"
    cuerpo = f"""Estimado/a {nombre_proveedor},

Estamos revisando la factura {factura_id}, con fecha {fecha_factura}, por importe de {importe:.2f} €.

Le agradeceríamos confirmación del estado o cualquier aclaración adicional que considere necesaria.

Un saludo,
Administración
"""
    return asunto, cuerpo