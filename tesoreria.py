from db_context import get_connection
from config_empresa import CONFIG_EMPRESA
from conciliacion_bancaria import registrar_movimiento_banco


# =========================
# COBROS Y PAGOS
# =========================

def registrar_cobro_o_pago(factura_id, fecha, forma_pago="transferencia", importe=None, observaciones=""):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, tipo, nombre_tercero, concepto, total, estado
            FROM facturas
            WHERE id = ?
            """,
            (factura_id,)
        )
        fila = cursor.fetchone()

        if not fila:
            return {"ok": False, "mensaje": "Factura no encontrada"}

        factura_id_db, tipo, nombre_tercero, concepto, total_factura, estado_actual = fila

        total_factura = float(total_factura or 0)

        if importe is None:
            importe = total_factura

        importe = float(importe)

        if importe <= 0:
            return {"ok": False, "mensaje": "El importe debe ser mayor que cero"}

        if importe > total_factura:
            return {"ok": False, "mensaje": "El importe no puede superar el total de la factura"}

        if tipo == "venta":
            if forma_pago == "contado":
                cuenta_tesoreria = CONFIG_EMPRESA["cuenta_caja"]
            else:
                cuenta_tesoreria = CONFIG_EMPRESA["cuenta_bancos"]

            cuenta_contrapartida = CONFIG_EMPRESA["cuenta_clientes"]
            tipo_asiento = "cobro"
            nuevo_estado = "cobrada" if round(importe, 2) == round(total_factura, 2) else "cobro_parcial"

            lineas = [
                (cuenta_tesoreria, "debe", importe),
                (cuenta_contrapartida, "haber", importe),
            ]

        elif tipo == "compra":
            if forma_pago == "contado":
                cuenta_tesoreria = CONFIG_EMPRESA["cuenta_caja"]
            else:
                cuenta_tesoreria = CONFIG_EMPRESA["cuenta_bancos"]

            cuenta_contrapartida = CONFIG_EMPRESA["cuenta_proveedores"]
            tipo_asiento = "pago"
            nuevo_estado = "pagada" if round(importe, 2) == round(total_factura, 2) else "pago_parcial"

            lineas = [
                (cuenta_contrapartida, "debe", importe),
                (cuenta_tesoreria, "haber", importe),
            ]

        else:
            return {"ok": False, "mensaje": "Tipo de factura no válido"}

        concepto_asiento = f"{tipo_asiento.upper()} factura {factura_id_db} - {nombre_tercero}"

        cursor.execute(
            """
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (?, ?, ?)
            """,
            (fecha, concepto_asiento, tipo_asiento)
        )
        asiento_id = cursor.lastrowid

        for cuenta, movimiento, importe_linea in lineas:
            cursor.execute(
                """
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (?, ?, ?, ?)
                """,
                (asiento_id, cuenta, movimiento, float(importe_linea))
            )
        if cuenta_tesoreria == CONFIG_EMPRESA["cuenta_bancos"]:
            importe_banco = importe if tipo == "venta" else -importe

            try:
                registrar_movimiento_banco(
                    fecha=fecha,
                    concepto=concepto_asiento,
                    importe=importe_banco,
                    referencia=f"factura_{factura_id_db}"
                )
            except TypeError:
                registrar_movimiento_banco(
                    fecha,
                    concepto_asiento,
                    importe_banco
                )
            except Exception:
                pass

        cursor.execute(
            """
            UPDATE facturas
            SET estado = ?, forma_pago = ?, observaciones = ?
            WHERE id = ?
            """,
            (nuevo_estado, forma_pago, observaciones, factura_id_db)
        )

        conn.commit()

        return {
            "ok": True,
            "factura_id": factura_id_db,
            "asiento_id": asiento_id,
            "tipo": tipo,
            "estado_anterior": estado_actual,
            "estado_nuevo": nuevo_estado,
            "importe": importe,
            "forma_pago": forma_pago,
            "concepto": concepto,
        }

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

    finally:
        conn.close()


def registrar_desde_vencimiento(vencimiento_id, fecha, forma_pago="transferencia", importe=None, observaciones=""):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, factura_id, tipo, estado, importe, importe_pendiente
            FROM vencimientos
            WHERE id = ?
            """,
            (vencimiento_id,)
        )
        fila = cursor.fetchone()

        if not fila:
            return {"ok": False, "mensaje": "Vencimiento no encontrado"}

        id_venc, factura_id, tipo_venc, estado_venc, importe_total, importe_pendiente = fila

        if str(estado_venc).strip().lower() not in ["pendiente", "vencido", "cobro_parcial", "pago_parcial"]:
            return {"ok": False, "mensaje": f"El vencimiento no está pendiente: {estado_venc}"}

        importe_total = float(importe_total or 0)
        importe_pendiente = float(importe_pendiente or importe_total)

        if importe is None:
            importe = importe_pendiente

        importe = float(importe)

        if importe <= 0:
            return {"ok": False, "mensaje": "El importe debe ser mayor que cero"}

        if importe > importe_pendiente:
            return {"ok": False, "mensaje": "El importe no puede superar el pendiente del vencimiento"}

        if tipo_venc == "cobro":
            cuenta_tesoreria = CONFIG_EMPRESA["cuenta_bancos"] if forma_pago != "contado" else CONFIG_EMPRESA["cuenta_caja"]
            cuenta_contrapartida = CONFIG_EMPRESA["cuenta_clientes"]
            concepto = f"COBRO vencimiento {id_venc}"

            lineas = [
                (cuenta_tesoreria, "debe", importe),
                (cuenta_contrapartida, "haber", importe),
            ]

        else:  # pago
            cuenta_tesoreria = CONFIG_EMPRESA["cuenta_bancos"] if forma_pago != "contado" else CONFIG_EMPRESA["cuenta_caja"]
            cuenta_contrapartida = CONFIG_EMPRESA["cuenta_proveedores"]
            concepto = f"PAGO vencimiento {id_venc}"

            lineas = [
                (cuenta_contrapartida, "debe", importe),
                (cuenta_tesoreria, "haber", importe),
            ]

        cursor.execute(
            """
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (?, ?, ?)
            """,
            (fecha, concepto, tipo_venc)
        )
        asiento_id = cursor.lastrowid

        if cuenta_tesoreria == CONFIG_EMPRESA["cuenta_bancos"]:
            importe_banco = importe if tipo_venc == "cobro" else -importe

            try:
                registrar_movimiento_banco(
                    fecha=fecha,
                    concepto=concepto,
                    importe=importe_banco,
                    referencia=f"vencimiento_{id_venc}"
                )
            except TypeError:
                registrar_movimiento_banco(
                    fecha,
                    concepto,
                    importe_banco
                )
            except Exception:
                pass

        nuevo_pendiente = round(importe_pendiente - importe, 2)

        if nuevo_pendiente <= 0:
            nuevo_estado = "cobrado" if tipo_venc == "cobro" else "pagado"
            nuevo_pendiente = 0.0
        else:
            nuevo_estado = "cobro_parcial" if tipo_venc == "cobro" else "pago_parcial"

        cursor.execute(
            """
            UPDATE vencimientos
            SET estado = ?, importe_pendiente = ?
            WHERE id = ?
            """,
            (nuevo_estado, nuevo_pendiente, id_venc)
        )

        conn.commit()

        return {
            "ok": True,
            "mensaje": f"Vencimiento {id_venc} registrado correctamente",
            "vencimiento_id": id_venc,
            "asiento_id": asiento_id,
            "factura_id": factura_id,
            "estado_nuevo": nuevo_estado,
            "importe_registrado": importe,
            "importe_pendiente": nuevo_pendiente,
        }

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

    finally:
        conn.close()

# =========================
# CONSULTAS
# =========================

def obtener_facturas_pendientes():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            tipo,
            nombre_tercero,
            fecha_emision,
            total,
            estado,
            concepto
        FROM facturas
        WHERE estado IN ('pendiente', 'cobro_parcial', 'pago_parcial')
        ORDER BY id
        """
    )

    resultados = cursor.fetchall()
    conn.close()

    return resultados


def ver_facturas_pendientes():
    resultados = obtener_facturas_pendientes()

    print("\nFACTURAS PENDIENTES\n")
    for fila in resultados:
        print(fila)