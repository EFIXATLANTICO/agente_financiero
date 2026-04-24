from datetime import datetime
from db_context import get_connection
from contabilidad import crear_asiento, agregar_linea_asiento
from config_empresa import CONFIG_EMPRESA
import datetime


# =========================
# TERCEROS
# =========================

def crear_cliente(nombre, nif="", direccion="", email="", telefono=""):
    conn = get_connection()
    cursor = conn.cursor()

    nombre = (nombre or "").strip()
    nif = (nif or "").strip()
    direccion = (direccion or "").strip()
    email = (email or "").strip()
    telefono = (telefono or "").strip()

    if not nombre:
        raise ValueError("El nombre del cliente es obligatorio")

    cursor.execute("""
    INSERT INTO clientes (nombre, nif, direccion, email, telefono)
    VALUES (?, ?, ?, ?, ?)
    """, (nombre, nif, direccion, email, telefono))

    conn.commit()
    cliente_id = cursor.lastrowid
    conn.close()

    return {
        "ok": True,
        "id": cliente_id,
        "nombre": nombre,
        "nif": nif,
        "direccion": direccion,
        "email": email,
        "telefono": telefono
    }


def crear_proveedor(nombre, nif="", direccion="", email="", telefono=""):
    conn = get_connection()
    cursor = conn.cursor()

    nombre = (nombre or "").strip()
    nif = (nif or "").strip()
    direccion = (direccion or "").strip()
    email = (email or "").strip()
    telefono = (telefono or "").strip()

    if not nombre:
        raise ValueError("El nombre del proveedor es obligatorio")

    cursor.execute("""
    INSERT INTO proveedores (nombre, nif, direccion, email, telefono)
    VALUES (?, ?, ?, ?, ?)
    """, (nombre, nif, direccion, email, telefono))

    conn.commit()
    proveedor_id = cursor.lastrowid
    conn.close()

    return {
        "ok": True,
        "id": proveedor_id,
        "nombre": nombre,
        "nif": nif,
        "direccion": direccion,
        "email": email,
        "telefono": telefono
    }


def obtener_clientes():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nombre, nif, direccion, email, telefono
    FROM clientes
    ORDER BY nombre
    """)

    filas = cursor.fetchall()
    conn.close()

    return filas


def obtener_proveedores():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nombre, nif, direccion, email, telefono
    FROM proveedores
    ORDER BY nombre
    """)

    filas = cursor.fetchall()
    conn.close()

    return filas


def ver_clientes():
    resultados = obtener_clientes()

    print("\nCLIENTES\n")
    for fila in resultados:
        print(fila)


def ver_proveedores():
    resultados = obtener_proveedores()

    print("\nPROVEEDORES\n")
    for fila in resultados:
        print(fila)


# =========================
# FACTURACIÓN
# =========================

def generar_numero_factura(serie="F"):
    conn = get_connection()
    cursor = conn.cursor()

    anio = datetime.now().year

    cursor.execute("""
    SELECT COUNT(*)
    FROM facturas
    WHERE serie = ?
    """, (serie,))

    total = cursor.fetchone()[0] + 1
    conn.close()

    return f"{serie}-{anio}-{str(total).zfill(4)}"


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
    moneda="EUR"
):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        tipo = (tipo or "").strip().lower()
        base_imponible = float(base_imponible)
        impuesto_pct = float(impuesto_pct)

        cuota_impuesto = round(base_imponible * impuesto_pct / 100, 2)
        total = round(base_imponible + cuota_impuesto, 2)

        tercero_id = None

        if tipo == "venta":
            cursor.execute("SELECT id FROM clientes WHERE nombre = ?", (nombre_tercero,))
            fila = cursor.fetchone()

            if fila:
                tercero_id = fila[0]
            else:
                cursor.execute(
                    """
                    INSERT INTO clientes (nombre, nif, direccion, email, telefono)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (nombre_tercero, nif_tercero or "", "", "", "")
                )
                tercero_id = cursor.lastrowid

        elif tipo == "compra":
            cursor.execute("SELECT id FROM proveedores WHERE nombre = ?", (nombre_tercero,))
            fila = cursor.fetchone()

            if fila:
                tercero_id = fila[0]
            else:
                cursor.execute(
                    """
                    INSERT INTO proveedores (nombre, nif, direccion, email, telefono)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (nombre_tercero, nif_tercero or "", "", "", "")
                )
                tercero_id = cursor.lastrowid
        else:
            raise ValueError("El tipo de factura debe ser 'compra' o 'venta'")

        estado = "pendiente"

        cursor.execute(
            """
            INSERT INTO facturas (
                tipo,
                serie,
                numero_factura,
                tercero_id,
                nombre_tercero,
                nif_tercero,
                fecha_emision,
                fecha_operacion,
                fecha_vencimiento,
                concepto,
                base_imponible,
                tipo_impuesto,
                impuesto_pct,
                cuota_impuesto,
                total,
                moneda,
                estado,
                forma_pago,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                base_imponible,
                "IGIC",
                impuesto_pct,
                cuota_impuesto,
                total,
                moneda,
                estado,
                forma_pago,
                observaciones,
            )
        )

        factura_id = cursor.lastrowid

        if tipo == "compra":
            cuenta_gasto = CONFIG_EMPRESA["cuenta_compra_mercaderia"]
            cuenta_impuesto = CONFIG_EMPRESA["cuenta_igic_soportado"]
            cuenta_contrapartida = CONFIG_EMPRESA["cuenta_proveedores"]

            lineas = [
                (cuenta_gasto, "debe", base_imponible),
                (cuenta_impuesto, "debe", cuota_impuesto),
                (cuenta_contrapartida, "haber", total),
            ]

            tipo_asiento = "factura_compra"

        else:
            if "alquiler" in (concepto or "").lower():
                cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_alquiler"]
            elif "servicio" in (concepto or "").lower():
                cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_servicio"]
            else:
                cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_venta"]

            cuenta_impuesto = CONFIG_EMPRESA["cuenta_igic_repercutido"]

            cuenta_contrapartida = CONFIG_EMPRESA["cuenta_clientes"]

            lineas = [
                (cuenta_contrapartida, "debe", total),
                (cuenta_ingreso, "haber", base_imponible),
                (cuenta_impuesto, "haber", cuota_impuesto),
            ]

            tipo_asiento = "factura_venta"

        cursor.execute(
            """
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (?, ?, ?)
            """,
            (fecha_operacion, concepto, tipo_asiento)
        )
        asiento_id = cursor.lastrowid

        for cuenta, movimiento, importe in lineas:
            cursor.execute(
                """
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (?, ?, ?, ?)
                """,
                (asiento_id, cuenta, movimiento, float(importe))
            )

        try:
            cursor.execute(
                """
                INSERT INTO operaciones_asientos (operacion_id, asiento_id)
                VALUES (?, ?)
                """,
                (factura_id, asiento_id)
            )
        except Exception:
            pass

        conn.commit()

        return {
            "ok": True,
            "factura_id": factura_id,
            "asiento_id": asiento_id,
            "tipo": tipo,
            "base_imponible": base_imponible,
            "impuesto_pct": impuesto_pct,
            "cuota_impuesto": cuota_impuesto,
            "total": total,
        }

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

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
    observaciones=""
):
    conn = get_connection()
    cursor = conn.cursor()

    base = float(base)
    igic_porcentaje = float(igic_porcentaje)
    igic = round(base * igic_porcentaje / 100, 2)
    total = round(base + igic, 2)

    if not numero_factura:
        numero_factura = generar_numero_factura(serie)

    if not fecha_operacion:
        fecha_operacion = fecha

    cursor.execute("""
    INSERT INTO facturas (
        empresa_id,
        tipo,
        serie,
        numero_factura,
        tercero_id,
        nombre_tercero,
        nif_tercero,
        fecha_emision,
        fecha_operacion,
        fecha_vencimiento,
        concepto,
        base_imponible,
        tipo_impuesto,
        impuesto_pct,
        cuota_impuesto,
        total,
        moneda,
        estado,
        forma_pago,
        observaciones
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        None,
        "venta",
        serie,
        numero_factura,
        cliente_id,
        nombre_cliente,
        nif_cliente,
        fecha,
        fecha_operacion,
        fecha_vencimiento,
        concepto,
        base,
        "IGIC",
        igic_porcentaje,
        igic,
        total,
        "EUR",
        "pendiente",
        forma_pago,
        observaciones
    ))

    conn.commit()
    factura_id = cursor.lastrowid
    conn.close()

    asiento_id = crear_asiento(fecha, concepto, "venta")
    agregar_linea_asiento(asiento_id, "430 Clientes", "debe", total)
    agregar_linea_asiento(asiento_id, "700 Ventas", "haber", base)
    agregar_linea_asiento(asiento_id, "477 IGIC repercutido", "haber", igic)

    return {
        "ok": True,
        "factura_id": factura_id,
        "asiento_id": asiento_id,
        "tipo": "venta",
        "numero_factura": numero_factura,
        "base": base,
        "igic_pct": igic_porcentaje,
        "igic": igic,
        "total": total,
        "estado": "pendiente"
    }


def obtener_facturas():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        tipo,
        serie,
        numero_factura,
        tercero_id,
        nombre_tercero,
        nif_tercero,
        fecha_emision,
        fecha_operacion,
        fecha_vencimiento,
        concepto,
        base_imponible,
        tipo_impuesto,
        impuesto_pct,
        cuota_impuesto,
        total,
        moneda,
        estado,
        forma_pago,
        observaciones,
        creado_en
    FROM facturas
    ORDER BY id DESC
    """)

    filas = cursor.fetchall()
    conn.close()

    return filas


def ver_facturas():
    resultados = obtener_facturas()

    print("\nFACTURAS\n")
    for fila in resultados:
        print(fila)

def generar_siguiente_numero_factura_venta():
    conn = get_connection()
    cursor = conn.cursor()

    year_actual = datetime.datetime.today().year
    prefijo = f"FV-{year_actual}-"

    cursor.execute("""
        SELECT numero_factura
        FROM facturas
        WHERE numero_factura LIKE ?
        ORDER BY id DESC
        LIMIT 1
    """, (f"{prefijo}%",))

    fila = cursor.fetchone()
    conn.close()

    if not fila or not fila[0]:
        return f"{prefijo}0001"

    ultimo_numero = str(fila[0]).strip()

    try:
        secuencia = int(ultimo_numero.split("-")[-1])
        nueva_secuencia = secuencia + 1
    except Exception:
        nueva_secuencia = 1

    return f"{prefijo}{nueva_secuencia:04d}"


def calcular_totales_factura_venta(base_imponible, tipo_impuesto):
    base_imponible = float(base_imponible or 0)
    tipo_impuesto = float(tipo_impuesto or 0)

    cuota_impuesto = round(base_imponible * (tipo_impuesto / 100), 2)
    total = round(base_imponible + cuota_impuesto, 2)

    return {
        "base_imponible": round(base_imponible, 2),
        "tipo_impuesto": round(tipo_impuesto, 2),
        "cuota_impuesto": cuota_impuesto,
        "total": total
    }


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
    observaciones=""
):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        totales = calcular_totales_factura_venta(base_imponible, tipo_impuesto)

        cursor.execute("""
            INSERT INTO facturas (
                tipo,
                proveedor,
                numero_factura,
                fecha,
                fecha_emision,
                fecha_vencimiento,
                concepto,
                descripcion,
                base_imponible,
                cuota_iva,
                iva,
                impuesto,
                total,
                importe_total,
                estado,
                forma_pago,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "venta",
            nombre_cliente,
            numero_factura,
            fecha_emision,
            fecha_emision,
            fecha_vencimiento,
            concepto,
            concepto,
            totales["base_imponible"],
            totales["cuota_impuesto"],
            totales["cuota_impuesto"],
            totales["cuota_impuesto"],
            totales["total"],
            totales["total"],
            "pendiente",
            forma_pago,
            observaciones
        ))

        factura_id = cursor.lastrowid

        concepto_asiento = f"Factura emitida {numero_factura} - {nombre_cliente}"

        cursor.execute("""
            INSERT INTO asientos (
                fecha,
                concepto,
                tipo_operacion,
                total,
                estado
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            fecha_emision,
            concepto_asiento,
            "venta",
            totales["total"],
            "validado"
        ))

        asiento_id = cursor.lastrowid

        # Debe: cliente
        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe, concepto)
            VALUES (?, ?, ?, ?, ?)
        """, (
            asiento_id,
            "430",
            "debe",
            totales["total"],
            f"Cliente {nombre_cliente}"
        ))

        # Haber: ventas
        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe, concepto)
            VALUES (?, ?, ?, ?, ?)
        """, (
            asiento_id,
            "700",
            "haber",
            totales["base_imponible"],
            concepto
        ))

        # Haber: impuesto repercutido
        if totales["cuota_impuesto"] > 0:
            cursor.execute("""
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe, concepto)
                VALUES (?, ?, ?, ?, ?)
            """, (
                asiento_id,
                "477",
                "haber",
                totales["cuota_impuesto"],
                f"Impuesto factura {numero_factura}"
            ))

        conn.commit()

        return {
            "ok": True,
            "factura_id": factura_id,
            "asiento_id": asiento_id,
            "numero_factura": numero_factura,
            "total": totales["total"]
        }

    except Exception as e:
        conn.rollback()
        return {
            "ok": False,
            "error": str(e)
        }

    finally:
        conn.close()

def marcar_factura_como_cobrada_y_registrar_cobro(factura_id, forma_pago="transferencia", fecha_cobro=None):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if not fecha_cobro:
            fecha_cobro = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT
                id,
                nombre_tercero,
                numero_factura,
                total
            FROM facturas
            WHERE id = ?
            LIMIT 1
        """, (int(factura_id),))

        factura = cursor.fetchone()

        if not factura:
            return {"ok": False, "mensaje": "No se encontró la factura."}

        factura_id_db, nombre_tercero, numero_factura, total = factura
        total = float(total or 0)

        if forma_pago == "efectivo":
            cuenta_tesoreria = CONFIG_EMPRESA["cuenta_caja"]
        else:
            cuenta_tesoreria = CONFIG_EMPRESA["cuenta_bancos"]

        cursor.execute("""
            UPDATE facturas
            SET estado = 'pagada'
            WHERE id = ?
        """, (int(factura_id_db),))

        concepto_asiento = f"Cobro factura {numero_factura} - {nombre_tercero}"

        cursor.execute("""
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (?, ?, ?)
        """, (
            fecha_cobro,
            concepto_asiento,
            "cobro_factura"
        ))
        asiento_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (?, ?, ?, ?)
        """, (
            asiento_id,
            cuenta_tesoreria,
            "debe",
            total
        ))

        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (?, ?, ?, ?)
        """, (
            asiento_id,
            CONFIG_EMPRESA["cuenta_clientes"],
            "haber",
            total
        ))

        try:
            cursor.execute("""
                UPDATE vencimientos
                SET estado = 'pagado'
                WHERE factura_id = ?
            """, (int(factura_id_db),))
        except Exception:
            pass

        conn.commit()

        return {
            "ok": True,
            "mensaje": f"Factura {numero_factura} marcada como cobrada",
            "asiento_id": asiento_id
        }

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

    finally:
        conn.close()

def registrar_cobro_factura(factura_id, fecha_cobro=None, forma_cobro="transferencia"):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if not fecha_cobro:
            fecha_cobro = datetime.datetime.now().strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT id, numero_factura, nombre_tercero, total, estado
            FROM facturas
            WHERE id = ?
            LIMIT 1
        """, (int(factura_id),))

        fila = cursor.fetchone()

        if not fila:
            return {"ok": False, "mensaje": "No se encontró la factura."}

        factura_id_db, numero_factura, nombre_tercero, total, estado_actual = fila
        total = float(total or 0)

        if str(estado_actual).strip().lower() in ("pagada", "cobrada", "cobrado"):
            return {"ok": False, "mensaje": "La factura ya está cobrada/pagada."}

        forma_cobro = str(forma_cobro or "").strip().lower()

        if forma_cobro == "efectivo":
            cuenta_tesoreria = CONFIG_EMPRESA["cuenta_caja"]
        else:
            cuenta_tesoreria = CONFIG_EMPRESA["cuenta_bancos"]

        cursor.execute("""
            UPDATE facturas
            SET estado = 'pagada'
            WHERE id = ?
        """, (int(factura_id_db),))

        concepto_asiento = f"Cobro factura {numero_factura} - {nombre_tercero}"

        cursor.execute("""
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (?, ?, ?)
        """, (
            str(fecha_cobro),
            concepto_asiento,
            "cobro_factura"
        ))
        asiento_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (?, ?, ?, ?)
        """, (
            asiento_id,
            cuenta_tesoreria,
            "debe",
            total
        ))

        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (?, ?, ?, ?)
        """, (
            asiento_id,
            CONFIG_EMPRESA["cuenta_clientes"],
            "haber",
            total
        ))

        try:
            cursor.execute("""
                UPDATE vencimientos
                SET estado = 'pagado'
                WHERE factura_id = ?
            """, (int(factura_id_db),))
        except Exception:
            pass

        conn.commit()

        return {
            "ok": True,
            "mensaje": f"Factura {numero_factura} cobrada correctamente.",
            "asiento_id": asiento_id
        }

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

    finally:
        conn.close()
