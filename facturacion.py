import datetime

from config_empresa import CONFIG_EMPRESA
from contabilidad import crear_asiento, agregar_linea_asiento
from db_context import get_connection


def _fetchone_dict(cursor, fila):
    if not fila:
        return None
    columnas = [desc[0] for desc in cursor.description]
    return dict(zip(columnas, fila))


def _normalizar_tipo(tipo):
    tipo = (tipo or "").strip().lower()
    if tipo not in ("venta", "compra"):
        raise ValueError("El tipo de factura debe ser 'compra' o 'venta'")
    return tipo


def _tabla_tercero(tipo):
    return "clientes" if tipo == "venta" else "proveedores"


def _buscar_o_crear_tercero(cursor, tipo, nombre, nif=""):
    tabla = _tabla_tercero(tipo)
    nombre = (nombre or "").strip()
    nif = (nif or "").strip()

    if not nombre:
        raise ValueError("El nombre del tercero es obligatorio")

    cursor.execute(f"SELECT id FROM {tabla} WHERE nombre = %s LIMIT 1", (nombre,))
    fila = cursor.fetchone()
    if fila:
        return fila[0]

    cursor.execute(
        f"""
        INSERT INTO {tabla} (nombre, nif, direccion, email, telefono)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (nombre, nif, "", "", ""),
    )
    return cursor.fetchone()[0]


def crear_cliente(nombre, nif="", direccion="", email="", telefono=""):
    return _crear_tercero("clientes", nombre, nif, direccion, email, telefono)


def crear_proveedor(nombre, nif="", direccion="", email="", telefono=""):
    return _crear_tercero("proveedores", nombre, nif, direccion, email, telefono)


def _crear_tercero(tabla, nombre, nif="", direccion="", email="", telefono=""):
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre es obligatorio")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            INSERT INTO {tabla} (nombre, nif, direccion, email, telefono)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                nombre,
                (nif or "").strip(),
                (direccion or "").strip(),
                (email or "").strip(),
                (telefono or "").strip(),
            ),
        )
        tercero_id = cursor.fetchone()[0]
        conn.commit()
        return {"ok": True, "id": tercero_id, "nombre": nombre}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_clientes():
    return _obtener_terceros("clientes")


def obtener_proveedores():
    return _obtener_terceros("proveedores")


def _obtener_terceros(tabla):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id, nombre, nif, direccion, email, telefono FROM {tabla} ORDER BY nombre")
    filas = cursor.fetchall()
    conn.close()
    return filas


def ver_clientes():
    for fila in obtener_clientes():
        print(fila)


def ver_proveedores():
    for fila in obtener_proveedores():
        print(fila)


def generar_numero_factura(serie="F"):
    conn = get_connection()
    cursor = conn.cursor()
    anio = datetime.datetime.now().year
    cursor.execute("SELECT COUNT(*) FROM facturas WHERE serie = %s", (serie,))
    total = int(cursor.fetchone()[0] or 0) + 1
    conn.close()
    return f"{serie}-{anio}-{total:04d}"


def generar_siguiente_numero_factura_venta():
    conn = get_connection()
    cursor = conn.cursor()
    year_actual = datetime.datetime.today().year
    prefijo = f"FV-{year_actual}-"

    cursor.execute(
        """
        SELECT numero_factura
        FROM facturas
        WHERE numero_factura LIKE %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (f"{prefijo}%",),
    )
    fila = cursor.fetchone()
    conn.close()

    if not fila or not fila[0]:
        return f"{prefijo}0001"

    try:
        secuencia = int(str(fila[0]).split("-")[-1]) + 1
    except Exception:
        secuencia = 1
    return f"{prefijo}{secuencia:04d}"


def calcular_totales_factura_venta(base_imponible, tipo_impuesto):
    base_imponible = round(float(base_imponible or 0), 2)
    tipo_impuesto = round(float(tipo_impuesto or 0), 2)
    cuota_impuesto = round(base_imponible * tipo_impuesto / 100, 2)
    return {
        "base_imponible": base_imponible,
        "tipo_impuesto": tipo_impuesto,
        "cuota_impuesto": cuota_impuesto,
        "total": round(base_imponible + cuota_impuesto, 2),
    }


def registrar_factura(
    tipo,
    nombre_tercero,
    nif_tercero,
    fecha_emision,
    fecha_operacion,
    concepto,
    base_imponible,
    impuesto_pct,
    forma_pago="credito",
    numero_factura=None,
    serie="A",
    fecha_vencimiento=None,
    observaciones="",
    moneda="EUR",
):
    tipo = _normalizar_tipo(tipo)
    totales = calcular_totales_factura_venta(base_imponible, impuesto_pct)
    fecha_operacion = str(fecha_operacion or fecha_emision)
    fecha_emision = str(fecha_emision)
    fecha_vencimiento = str(fecha_vencimiento or fecha_emision)
    numero_factura = numero_factura or generar_numero_factura(serie)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        tercero_id = _buscar_o_crear_tercero(cursor, tipo, nombre_tercero, nif_tercero)

        cursor.execute(
            """
            INSERT INTO facturas (
                tipo, serie, numero_factura, tercero_id, nombre_tercero, nif_tercero,
                fecha_emision, fecha_operacion, fecha_vencimiento, concepto,
                base_imponible, tipo_impuesto, impuesto_pct, cuota_impuesto, total,
                moneda, estado, forma_pago, observaciones
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                tipo,
                serie,
                numero_factura,
                tercero_id,
                nombre_tercero,
                nif_tercero or "",
                fecha_emision,
                fecha_operacion,
                fecha_vencimiento,
                concepto,
                totales["base_imponible"],
                "IGIC",
                totales["tipo_impuesto"],
                totales["cuota_impuesto"],
                totales["total"],
                moneda,
                "pendiente",
                forma_pago,
                observaciones,
            ),
        )
        factura_id = cursor.fetchone()[0]

        if tipo == "compra":
            lineas = [
                (CONFIG_EMPRESA["cuenta_compra_mercaderia"], "debe", totales["base_imponible"]),
                (CONFIG_EMPRESA["cuenta_igic_soportado"], "debe", totales["cuota_impuesto"]),
                (CONFIG_EMPRESA["cuenta_proveedores"], "haber", totales["total"]),
            ]
            tipo_asiento = "factura_compra"
        else:
            concepto_lower = (concepto or "").lower()
            if "alquiler" in concepto_lower:
                cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_alquiler"]
            elif "servicio" in concepto_lower:
                cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_servicio"]
            else:
                cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_venta"]

            lineas = [
                (CONFIG_EMPRESA["cuenta_clientes"], "debe", totales["total"]),
                (cuenta_ingreso, "haber", totales["base_imponible"]),
                (CONFIG_EMPRESA["cuenta_igic_repercutido"], "haber", totales["cuota_impuesto"]),
            ]
            tipo_asiento = "factura_venta"

        cursor.execute(
            """
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (fecha_operacion, concepto, tipo_asiento),
        )
        asiento_id = cursor.fetchone()[0]

        for cuenta, movimiento, importe in lineas:
            cursor.execute(
                """
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (%s, %s, %s, %s)
                """,
                (asiento_id, cuenta, movimiento, float(importe)),
            )

        cursor.execute(
            """
            INSERT INTO operaciones_asientos (operacion_id, asiento_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (factura_id, asiento_id),
        )

        conn.commit()
        return {
            "ok": True,
            "factura_id": factura_id,
            "asiento_id": asiento_id,
            "tipo": tipo,
            "numero_factura": numero_factura,
            **totales,
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e), "error": str(e)}
    finally:
        conn.close()


def registrar_factura_venta(
    fecha,
    cliente_id,
    nombre_cliente,
    base,
    igic_porcentaje,
    concepto,
    nif_cliente="",
    serie="F",
    numero_factura=None,
    fecha_operacion=None,
    fecha_vencimiento=None,
    forma_pago="",
    observaciones="",
):
    return registrar_factura(
        tipo="venta",
        nombre_tercero=nombre_cliente,
        nif_tercero=nif_cliente,
        fecha_emision=fecha,
        fecha_operacion=fecha_operacion or fecha,
        concepto=concepto,
        base_imponible=base,
        impuesto_pct=igic_porcentaje,
        forma_pago=forma_pago,
        numero_factura=numero_factura,
        serie=serie,
        fecha_vencimiento=fecha_vencimiento,
        observaciones=observaciones,
    )


def registrar_factura_compra(
    fecha,
    proveedor_id,
    nombre_proveedor,
    base,
    igic_porcentaje,
    concepto,
    nif_proveedor="",
    serie="FC",
    numero_factura=None,
    fecha_operacion=None,
    fecha_vencimiento=None,
    forma_pago="",
    observaciones="",
):
    return registrar_factura(
        tipo="compra",
        nombre_tercero=nombre_proveedor,
        nif_tercero=nif_proveedor,
        fecha_emision=fecha,
        fecha_operacion=fecha_operacion or fecha,
        concepto=concepto,
        base_imponible=base,
        impuesto_pct=igic_porcentaje,
        forma_pago=forma_pago,
        numero_factura=numero_factura,
        serie=serie,
        fecha_vencimiento=fecha_vencimiento,
        observaciones=observaciones,
    )


def obtener_facturas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, tipo, serie, numero_factura, tercero_id, nombre_tercero, nif_tercero,
               fecha_emision, fecha_operacion, fecha_vencimiento, concepto, base_imponible,
               tipo_impuesto, impuesto_pct, cuota_impuesto, total, moneda, estado,
               forma_pago, observaciones, creado_en
        FROM facturas
        ORDER BY id DESC
        """
    )
    filas = cursor.fetchall()
    conn.close()
    return filas


def ver_facturas():
    for fila in obtener_facturas():
        print(fila)


def crear_factura_venta(
    cliente_id=None,
    nombre_cliente="",
    numero_factura="",
    fecha_emision="",
    fecha_vencimiento="",
    concepto="",
    base_imponible=0.0,
    tipo_impuesto=7.0,
    forma_pago="",
    observaciones="",
):
    return registrar_factura(
        tipo="venta",
        nombre_tercero=nombre_cliente,
        nif_tercero="",
        fecha_emision=fecha_emision,
        fecha_operacion=fecha_emision,
        concepto=concepto,
        base_imponible=base_imponible,
        impuesto_pct=tipo_impuesto,
        forma_pago=forma_pago,
        numero_factura=numero_factura,
        serie="FV",
        fecha_vencimiento=fecha_vencimiento,
        observaciones=observaciones,
    )


def _registrar_movimiento_factura(factura_id, fecha, forma_pago, tipo_movimiento):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, tipo, numero_factura, nombre_tercero, total, estado
            FROM facturas
            WHERE id = %s
            LIMIT 1
            """,
            (int(factura_id),),
        )
        fila = cursor.fetchone()
        if not fila:
            return {"ok": False, "mensaje": "No se encontro la factura."}

        factura_id_db, tipo, numero_factura, nombre_tercero, total, estado_actual = fila
        total = float(total or 0)
        es_venta = tipo == "venta"
        cuenta_tesoreria = CONFIG_EMPRESA["cuenta_caja"] if forma_pago == "efectivo" else CONFIG_EMPRESA["cuenta_bancos"]
        cuenta_tercero = CONFIG_EMPRESA["cuenta_clientes"] if es_venta else CONFIG_EMPRESA["cuenta_proveedores"]

        nuevo_estado = "pagada" if not es_venta else "cobrada"
        concepto_asiento = f"{'Cobro' if es_venta else 'Pago'} factura {numero_factura} - {nombre_tercero}"

        cursor.execute(
            "UPDATE facturas SET estado = %s, forma_pago = %s WHERE id = %s",
            (nuevo_estado, forma_pago, int(factura_id_db)),
        )

        cursor.execute(
            """
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (str(fecha), concepto_asiento, tipo_movimiento),
        )
        asiento_id = cursor.fetchone()[0]

        lineas = (
            [(cuenta_tesoreria, "debe", total), (cuenta_tercero, "haber", total)]
            if es_venta
            else [(cuenta_tercero, "debe", total), (cuenta_tesoreria, "haber", total)]
        )

        for cuenta, movimiento, importe in lineas:
            cursor.execute(
                """
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (%s, %s, %s, %s)
                """,
                (asiento_id, cuenta, movimiento, importe),
            )

        cursor.execute("UPDATE vencimientos SET estado = 'pagado' WHERE factura_id = %s", (int(factura_id_db),))
        conn.commit()
        return {"ok": True, "mensaje": "Movimiento registrado correctamente.", "asiento_id": asiento_id}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}
    finally:
        conn.close()


def marcar_factura_como_cobrada_y_registrar_cobro(factura_id, forma_pago="transferencia", fecha_cobro=None):
    fecha_cobro = fecha_cobro or datetime.datetime.now().strftime("%Y-%m-%d")
    return _registrar_movimiento_factura(factura_id, fecha_cobro, forma_pago, "cobro_factura")


def registrar_cobro_factura(factura_id, fecha_cobro=None, forma_cobro="transferencia"):
    fecha_cobro = fecha_cobro or datetime.datetime.now().strftime("%Y-%m-%d")
    return _registrar_movimiento_factura(factura_id, fecha_cobro, forma_cobro, "cobro_factura")


def cobrar_factura_venta(factura_id, fecha_cobro=None, forma_cobro="transferencia"):
    return registrar_cobro_factura(factura_id, fecha_cobro, forma_cobro)


def pagar_factura_compra(factura_id, fecha_pago=None, forma_pago="transferencia"):
    fecha_pago = fecha_pago or datetime.datetime.now().strftime("%Y-%m-%d")
    return _registrar_movimiento_factura(factura_id, fecha_pago, forma_pago, "pago_factura")
