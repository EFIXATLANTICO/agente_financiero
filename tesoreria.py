from db_context import get_connection, obtener_empresa_id_activa
from config_empresa import CONFIG_EMPRESA
from conciliacion_bancaria import registrar_movimiento_banco




# =========================
# VENCIMIENTOS
# =========================

def _fecha_date(valor):
    import datetime

    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    try:
        return datetime.datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _estado_operable(estado):
    return str(estado or "").strip().lower() in ["pendiente", "vencido", "cobro_parcial", "pago_parcial"]


def _filtrar_vencimientos(filas, filtro="todos", tercero=None, hoy=None):
    import datetime

    hoy = hoy or datetime.date.today()
    filtro = str(filtro or "todos").strip().lower()
    tercero = str(tercero or "").strip().upper()
    resultado = []

    for fila in filas:
        fila = dict(fila)
        estado = str(fila.get("estado") or "").strip().lower()
        fecha = _fecha_date(fila.get("fecha_vencimiento"))
        operable = _estado_operable(estado)

        incluir = True
        if filtro == "pendientes":
            incluir = operable
        elif filtro == "vencidos":
            incluir = operable and fecha is not None and fecha < hoy
        elif filtro == "proximos":
            incluir = operable and fecha is not None and hoy <= fecha <= hoy + datetime.timedelta(days=7)

        if incluir and tercero:
            incluir = str(fila.get("nombre_tercero") or "").strip().upper() == tercero

        if incluir:
            resultado.append(fila)

    return resultado


def listar_vencimientos(filtro="todos", tercero=None, hoy=None):
    empresa_id = obtener_empresa_id_activa()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                empresa_id,
                factura_id,
                nombre_tercero,
                tipo,
                fecha_vencimiento,
                importe,
                COALESCE(importe_pendiente, importe, 0) AS importe_pendiente,
                estado,
                creado_en
            FROM vencimientos
            WHERE empresa_id = %s OR empresa_id IS NULL
            ORDER BY fecha_vencimiento ASC, id DESC
            """,
            (empresa_id,),
        )
        columnas = [desc[0] for desc in cursor.description]
        filas = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
        return _filtrar_vencimientos(filas, filtro=filtro, tercero=tercero, hoy=hoy)
    finally:
        conn.close()


def _actualizar_factura_desde_vencimiento(cursor, factura_id, tipo_venc, nuevo_estado_venc, forma_pago, observaciones):
    if not factura_id:
        return

    cursor.execute("SELECT id, tipo FROM facturas WHERE id = %s LIMIT 1", (int(factura_id),))
    factura = cursor.fetchone()
    if not factura:
        return

    cursor.execute(
        """
        SELECT COALESCE(SUM(COALESCE(importe_pendiente, importe, 0)), 0)
        FROM vencimientos
        WHERE factura_id = %s
          AND estado IN ('pendiente', 'vencido', 'cobro_parcial', 'pago_parcial')
        """,
        (int(factura_id),),
    )
    pendiente_total = float(cursor.fetchone()[0] or 0)

    tipo_factura = str(factura[1] or "").strip().lower()
    if pendiente_total <= 0:
        estado_factura = "cobrada" if tipo_factura == "venta" or tipo_venc == "cobro" else "pagada"
    else:
        estado_factura = "cobro_parcial" if tipo_factura == "venta" or tipo_venc == "cobro" else "pago_parcial"

    cursor.execute(
        """
        UPDATE facturas
        SET estado = %s, forma_pago = %s, observaciones = %s
        WHERE id = %s
        """,
        (estado_factura, forma_pago, observaciones, int(factura_id)),
    )

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
            WHERE id = %s
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
            return {"ok": False, "mensaje": "Tipo de factura no valido"}

        concepto_asiento = f"{tipo_asiento.upper()} factura {factura_id_db} - {nombre_tercero}"

        cursor.execute(
            """
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (fecha, concepto_asiento, tipo_asiento)
        )
        asiento_id = cursor.fetchone()[0]

        for cuenta, movimiento, importe_linea in lineas:
            cursor.execute(
                """
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (%s, %s, %s, %s)
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
            SET estado = %s, forma_pago = %s, observaciones = %s
            WHERE id = %s
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
            WHERE id = %s
            """,
            (vencimiento_id,)
        )
        fila = cursor.fetchone()

        if not fila:
            return {"ok": False, "mensaje": "Vencimiento no encontrado"}

        id_venc, factura_id, tipo_venc, estado_venc, importe_total, importe_pendiente = fila

        if str(estado_venc).strip().lower() not in ["pendiente", "vencido", "cobro_parcial", "pago_parcial"]:
            return {"ok": False, "mensaje": f"El vencimiento no esta pendiente: {estado_venc}"}

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
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (fecha, concepto, tipo_venc)
        )
        asiento_id = cursor.fetchone()[0]

        for cuenta, movimiento, importe_linea in lineas:
            cursor.execute(
                """
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (%s, %s, %s, %s)
                """,
                (asiento_id, cuenta, movimiento, float(importe_linea))
            )

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
            SET estado = %s, importe_pendiente = %s, forma_pago = %s
            WHERE id = %s
            """,
            (nuevo_estado, nuevo_pendiente, forma_pago, id_venc)
        )

        _actualizar_factura_desde_vencimiento(cursor, factura_id, tipo_venc, nuevo_estado, forma_pago, observaciones)

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


def cobrar_factura_venta(factura_id, fecha_cobro=None, forma_pago="transferencia"):
    from facturacion import registrar_cobro_factura

    return registrar_cobro_factura(factura_id, fecha_cobro, forma_pago)


def pagar_factura_compra(factura_id, fecha_pago=None, forma_pago="transferencia"):
    from facturacion import pagar_factura_compra as _pagar_factura_compra

    return _pagar_factura_compra(factura_id, fecha_pago, forma_pago)


def ver_facturas_pendientes():
    resultados = obtener_facturas_pendientes()

    print("\nFACTURAS PENDIENTES\n")
    for fila in resultados:
        print(fila)
