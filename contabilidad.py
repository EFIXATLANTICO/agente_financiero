from db_context import get_connection
import re


# =========================
# FUNCIONES BASE CONTABLES
# =========================

def crear_asiento(fecha, concepto, tipo_operacion):
    """
    Crea un asiento contable y devuelve su ID.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO asientos (fecha, concepto, tipo_operacion)
    VALUES (?, ?, ?)
    """, (fecha, concepto, tipo_operacion))

    conn.commit()
    asiento_id = cursor.lastrowid
    conn.close()

    return asiento_id


def agregar_linea_asiento(asiento_id, cuenta, movimiento, importe):
    """
    Agrega una línea a un asiento existente.
    """
    movimiento = (movimiento or "").strip().lower()
    if movimiento not in ("debe", "haber"):
        raise ValueError("El movimiento debe ser 'debe' o 'haber'")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
    VALUES (?, ?, ?, ?)
    """, (asiento_id, cuenta, movimiento, float(importe)))

    conn.commit()
    conn.close()


def obtener_lineas_asiento(asiento_id):
    """
    Devuelve las líneas de un asiento.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT cuenta, movimiento, importe
    FROM lineas_asiento
    WHERE asiento_id = ?
    ORDER BY id
    """, (asiento_id,))

    lineas = cursor.fetchall()
    conn.close()

    return lineas


def obtener_libro_diario(tipo_operacion=None, limite=None):
    """
    Devuelve el libro diario en formato lista de diccionarios.
    Cada asiento incluye sus líneas.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if tipo_operacion and tipo_operacion != "Todos":
        cursor.execute("""
        SELECT id, fecha, concepto, tipo_operacion
        FROM asientos
        WHERE tipo_operacion = ?
        ORDER BY id ASC
        """, (tipo_operacion,))
    else:
        cursor.execute("""
        SELECT id, fecha, concepto, tipo_operacion
        FROM asientos
        ORDER BY id ASC
        """)

    asientos = cursor.fetchall()

    if limite:
        asientos = asientos[-int(limite):]

    resultado = []

    for asiento_id, fecha, concepto, tipo_op in asientos:
        cursor.execute("""
        SELECT cuenta, movimiento, importe
        FROM lineas_asiento
        WHERE asiento_id = ?
        ORDER BY id
        """, (asiento_id,))
        lineas = cursor.fetchall()

        resultado.append({
            "id": asiento_id,
            "fecha": fecha,
            "concepto": concepto,
            "tipo_operacion": tipo_op,
            "lineas": [
                {
                    "cuenta": cuenta,
                    "movimiento": movimiento,
                    "importe": float(importe)
                }
                for cuenta, movimiento, importe in lineas
            ]
        })

    conn.close()
    return resultado


def ver_libro_diario():
    """
    Mantiene compatibilidad con tu versión anterior:
    imprime el diario por consola.
    """
    asientos = obtener_libro_diario()

    print("\nLIBRO DIARIO\n")

    for asiento in asientos:
        print(f"ASIENTO {asiento['id']}")
        print(f"Fecha: {asiento['fecha']}")
        print(f"Concepto: {asiento['concepto']}")
        print(f"Tipo: {asiento['tipo_operacion']}")

        for linea in asiento["lineas"]:
            print(
                f"  {linea['movimiento'].upper()} | "
                f"{linea['cuenta']} | {linea['importe']}"
            )

        print("-------------------------")
def crear_asiento_completo(fecha, concepto, tipo_operacion, lineas):
    """
    Crea un asiento completo con todas sus líneas en una sola transacción.
    Si falla cualquier línea, no se guarda nada.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO asientos (fecha, concepto, tipo_operacion)
        VALUES (?, ?, ?)
        """, (fecha, concepto, tipo_operacion))

        asiento_id = cursor.lastrowid

        for cuenta, movimiento, importe in lineas:
            movimiento = (movimiento or "").strip().lower()

            if movimiento not in ("debe", "haber"):
                raise ValueError("El movimiento debe ser 'debe' o 'haber'")

            cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (?, ?, ?, ?)
            """, (asiento_id, cuenta, movimiento, float(importe)))

        conn.commit()
        return asiento_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =========================
# OPERACIONES CONTABLES
# =========================

def registrar_compra_con_igic(fecha, base, igic_porcentaje, concepto):
    """
    Registra una compra con IGIC:
    600 Compras
    472 IGIC soportado
    400 Proveedores
    """
    base = float(base)
    igic_porcentaje = float(igic_porcentaje)

    igic = round(base * igic_porcentaje / 100, 2)
    total = round(base + igic, 2)

    asiento_id = crear_asiento(fecha, concepto, "compra")

    agregar_linea_asiento(asiento_id, "600 Compras", "debe", base)
    agregar_linea_asiento(asiento_id, "472 IGIC soportado", "debe", igic)
    agregar_linea_asiento(asiento_id, "400 Proveedores", "haber", total)

    return {
        "ok": True,
        "asiento_id": asiento_id,
        "tipo": "compra",
        "base": base,
        "igic_pct": igic_porcentaje,
        "igic": igic,
        "total": total
    }


def registrar_venta_con_igic(fecha, base, igic_porcentaje, concepto):
    """
    Registra una venta con IGIC:
    430 Clientes
    700 Ventas
    477 IGIC repercutido
    """
    base = float(base)
    igic_porcentaje = float(igic_porcentaje)

    igic = round(base * igic_porcentaje / 100, 2)
    total = round(base + igic, 2)

    asiento_id = crear_asiento(fecha, concepto, "venta")

    agregar_linea_asiento(asiento_id, "430 Clientes", "debe", total)
    agregar_linea_asiento(asiento_id, "700 Ventas", "haber", base)
    agregar_linea_asiento(asiento_id, "477 IGIC repercutido", "haber", igic)

    return {
        "ok": True,
        "asiento_id": asiento_id,
        "tipo": "venta",
        "base": base,
        "igic_pct": igic_porcentaje,
        "igic": igic,
        "total": total
    }


# =========================
# LIBRO MAYOR
# =========================

def obtener_mayor(cuenta):
    """
    Devuelve el mayor de una cuenta con saldo acumulado.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT a.fecha, a.concepto, l.movimiento, l.importe
    FROM lineas_asiento l
    JOIN asientos a ON l.asiento_id = a.id
    WHERE l.cuenta = ?
    ORDER BY a.fecha, l.id
    """, (cuenta,))

    movimientos = cursor.fetchall()
    conn.close()

    saldo = 0.0
    resultado = []

    for fecha, concepto, movimiento, importe in movimientos:
        importe = float(importe)

        if movimiento == "debe":
            saldo += importe
        else:
            saldo -= importe

        resultado.append({
            "fecha": fecha,
            "concepto": concepto,
            "movimiento": movimiento,
            "importe": importe,
            "saldo": round(saldo, 2)
        })

    return resultado


def ver_mayor(cuenta):
    """
    Mantiene compatibilidad con tu versión anterior:
    imprime el mayor por consola.
    """
    movimientos = obtener_mayor(cuenta)

    print(f"\nMAYOR DE LA CUENTA {cuenta}\n")

    for mov in movimientos:
        print(
            f"{mov['fecha']} | "
            f"{mov['concepto']} | "
            f"{mov['movimiento'].upper()} | "
            f"{mov['importe']} | "
            f"SALDO: {mov['saldo']}"
        )

def borrar_asiento(asiento_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM operaciones_asientos WHERE asiento_id = %s", (asiento_id,))
        cursor.execute("DELETE FROM asientos_importacion WHERE asiento_id = %s", (asiento_id,))
        cursor.execute("DELETE FROM lineas_asiento WHERE asiento_id = %s", (asiento_id,))
        cursor.execute("DELETE FROM asientos WHERE id = %s", (asiento_id,))

        conn.commit()

        return {"ok": True, "mensaje": f"Asiento {asiento_id} borrado correctamente"}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

    finally:
        conn.close()
# =========================
# UTILIDADES DE RESET
# =========================

def reset_contabilidad():
    """
    Borra toda la contabilidad y datos operativos básicos de la empresa activa.
    Devuelve un resumen verificando que asientos y líneas hayan quedado a cero.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        def tabla_existe(nombre_tabla):
            cursor.execute("SELECT to_regclass(%s)", (nombre_tabla,))
            return cursor.fetchone()[0] is not None

        tablas_a_borrar = [
            "operaciones_asientos",
            "asientos_importacion",
            "lineas_asiento",
            "incidencias_importacion",
            "vencimientos",
            "facturas",
            "importaciones",
            "operaciones",
            "validaciones_contables",
            "movimientos_bancarios",
            "movimientos_banco",
            "conciliaciones",
            "amortizaciones",
            "inmovilizado",
            "asientos",
            "clientes",
            "proveedores"
        ]

        errores = []

        for tabla in tablas_a_borrar:
            try:
                if tabla_existe(tabla):
                    cursor.execute(f"DELETE FROM {tabla}")
            except Exception as e:
                errores.append(f"{tabla}: {e}")
                conn.rollback()

        conn.commit()

        total_asientos = 0
        total_lineas = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM asientos")
            total_asientos = int(cursor.fetchone()[0])
        except Exception as e:
            errores.append(f"conteo_asientos: {e}")

        try:
            cursor.execute("SELECT COUNT(*) FROM lineas_asiento")
            total_lineas = int(cursor.fetchone()[0])
        except Exception as e:
            errores.append(f"conteo_lineas: {e}")

        return {
            "ok": total_asientos == 0 and total_lineas == 0 and len(errores) == 0,
            "asientos": total_asientos,
            "lineas": total_lineas,
            "errores": errores,
        }

    except Exception as e:
        conn.rollback()
        return {
            "ok": False,
            "asientos": None,
            "lineas": None,
            "errores": [str(e)],
        }

    finally:
        conn.close()

def aplicar_correccion_incidencia(incidencia_id, propuesta):
    from db_context import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    try:
        fecha = str(propuesta.get("fecha", "")).strip()
        concepto = str(propuesta.get("concepto", "")).strip()
        cuenta_debe = str(propuesta.get("cuenta_debe", "")).strip()
        cuenta_haber = str(propuesta.get("cuenta_haber", "")).strip()
        debe = float(propuesta.get("debe", 0) or 0)
        haber = float(propuesta.get("haber", 0) or 0)

        if not fecha:
            return {"ok": False, "error": "La fecha es obligatoria"}

        if not concepto:
            return {"ok": False, "error": "El concepto es obligatorio"}

        if not cuenta_debe or not cuenta_haber:
            return {"ok": False, "error": "Faltan cuentas contables"}

        if debe <= 0 or haber <= 0:
            return {"ok": False, "error": "Los importes deben ser mayores que cero"}

        if round(debe, 2) != round(haber, 2):
            return {"ok": False, "error": "El asiento no está cuadrado"}

        cursor.execute("""
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (?, ?, ?)
        """, (fecha, concepto, "correccion_incidencia"))

        asiento_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (?, ?, ?, ?)
        """, (asiento_id, cuenta_debe, "debe", round(debe, 2)))

        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (?, ?, ?, ?)
        """, (asiento_id, cuenta_haber, "haber", round(haber, 2)))

        cursor.execute("""
            UPDATE incidencias_importacion
            SET estado = 'revisada'
            WHERE id = ?
        """, (incidencia_id,))

        conn.commit()

        return {"ok": True, "asiento_id": asiento_id}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()

def inicializar_relaciones_fianzas():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relaciones_fianzas (
            id SERIAL PRIMARY KEY,
            asiento_fianza_recibida_id INTEGER NOT NULL,
            asiento_fianza_devuelta_id INTEGER NOT NULL UNIQUE,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def extraer_asiento_origen_desde_concepto(concepto):
    texto = str(concepto or "")

    patrones = [
        r"asiento\s+origen\s+(\d+)",
        r"asiento\s+(\d+)"
    ]

    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def obtener_fianza_devuelta_existente(cursor, asiento_origen_id=None, concepto=None):
    if asiento_origen_id is not None:
        cursor.execute("""
            SELECT id, concepto
            FROM asientos
            WHERE tipo_operacion = 'fianza_devuelta'
            ORDER BY id DESC
        """)
        filas = cursor.fetchall()

        for asiento_id, concepto_existente in filas:
            origen_detectado = extraer_asiento_origen_desde_concepto(concepto_existente)
            if origen_detectado == int(asiento_origen_id):
                return int(asiento_id)

    if concepto:
        cursor.execute("""
            SELECT id
            FROM asientos
            WHERE tipo_operacion = 'fianza_devuelta'
              AND concepto = %s
            LIMIT 1
        """, (concepto,))

        fila = cursor.fetchone()
        if fila:
            return fila[0]

    return None

def obtener_fianza_recibida_existente(cursor, asiento_origen_id=None, concepto=None):
    if asiento_origen_id is not None:
        cursor.execute("""
            SELECT id, concepto
            FROM asientos
            WHERE tipo_operacion = 'fianza_recibida'
            ORDER BY id DESC
        """)
        filas = cursor.fetchall()

        for asiento_id, concepto_existente in filas:
            origen_detectado = extraer_asiento_origen_desde_concepto(concepto_existente)
            if origen_detectado == int(asiento_origen_id):
                return int(asiento_id)

        cursor.execute("""
            SELECT id
            FROM asientos
            WHERE tipo_operacion = 'fianza_recibida'
              AND concepto LIKE %s
            LIMIT 1
        """, (f"Fianza asociada a asiento {asiento_origen_id} - %",))

        fila = cursor.fetchone()
        if fila:
            return fila[0]

    if concepto:
        cursor.execute("""
            SELECT id
            FROM asientos
            WHERE tipo_operacion = 'fianza_recibida'
              AND concepto = %s
            LIMIT 1
        """, (concepto,))

        fila = cursor.fetchone()
        if fila:
            return fila[0]

    return None

def obtener_importe_asiento_por_cuenta(cursor, asiento_id, cuenta_prefijo, movimiento=None):
    if movimiento:
        cursor.execute("""
            SELECT COALESCE(SUM(importe), 0)
            FROM lineas_asiento
            WHERE asiento_id = %s
              AND cuenta LIKE %s
              AND movimiento = %s
        """, (asiento_id, f"{cuenta_prefijo}%", movimiento))
    else:
        cursor.execute("""
            SELECT COALESCE(SUM(importe), 0)
            FROM lineas_asiento
            WHERE asiento_id = %s
              AND cuenta LIKE %s
        """, (asiento_id, f"{cuenta_prefijo}%"))

    fila = cursor.fetchone()
    return round(float(fila[0] or 0), 2)


def obtener_saldo_fianza_recibida(cursor, asiento_fianza_id):
    inicializar_relaciones_fianzas()

    recibido = obtener_importe_asiento_por_cuenta(
        cursor,
        asiento_fianza_id,
        "560",
        movimiento="haber"
    )

    cursor.execute("""
        SELECT asiento_fianza_devuelta_id
        FROM relaciones_fianzas
        WHERE asiento_fianza_recibida_id = %s
    """, (asiento_fianza_id,))

    devoluciones = cursor.fetchall()

    total_devuelto = 0.0

    for fila in devoluciones:
        asiento_dev_id = int(fila[0])
        total_devuelto += obtener_importe_asiento_por_cuenta(
            cursor,
            asiento_dev_id,
            "560",
            movimiento="debe"
        )

    return {
        "recibido": round(recibido, 2),
        "devuelto": round(total_devuelto, 2),
        "pendiente": round(recibido - total_devuelto, 2)
    }


def buscar_fianza_recibida_candidata_para_devolucion(cursor, importe_objetivo=None, texto_referencia=""):
    texto_referencia = str(texto_referencia or "").strip().lower()

    cursor.execute("""
        SELECT id, fecha, concepto
        FROM asientos
        WHERE tipo_operacion = 'fianza_recibida'
        ORDER BY fecha DESC, id DESC
    """)

    candidatos = []
    filas = cursor.fetchall()

    for asiento_id, fecha, concepto in filas:
        saldo = obtener_saldo_fianza_recibida(cursor, int(asiento_id))

        if saldo["pendiente"] <= 0:
            continue

        score = 0
        concepto_txt = str(concepto or "").lower()

        if importe_objetivo is not None:
            diferencia = abs(float(saldo["pendiente"]) - float(importe_objetivo))
            if diferencia < 0.01:
                score += 100
            elif diferencia <= 5:
                score += 50
            elif diferencia <= 20:
                score += 20

        palabras_clave = ["cliente", "hector", "reserva", "alquiler", "fianza", "deposito", "depósito", "garantia", "garantía"]
        for palabra in palabras_clave:
            if palabra in texto_referencia and palabra in concepto_txt:
                score += 10

        if "asociada a asiento" in concepto_txt:
            score += 5

        candidatos.append({
            "asiento_id": int(asiento_id),
            "fecha": str(fecha),
            "concepto": str(concepto or ""),
            "score": score,
            "saldo_pendiente": float(saldo["pendiente"]),
            "importe_recibido": float(saldo["recibido"]),
            "importe_devuelto": float(saldo["devuelto"])
        })

    if not candidatos:
        return None

    candidatos = sorted(
        candidatos,
        key=lambda x: (x["score"], x["fecha"], x["asiento_id"]),
        reverse=True
    )

    return candidatos[0]

def crear_asiento_fianza_recibida(fecha, concepto, importe, cuenta_tesoreria="570 Caja", asiento_origen_id=None):
    from db_context import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    try:
        fecha = str(fecha or "").strip()
        concepto = str(concepto or "").strip()
        importe = float(importe or 0)

        if not fecha:
            return {"ok": False, "error": "La fecha es obligatoria"}

        if importe <= 0:
            return {"ok": False, "error": "El importe de la fianza debe ser mayor que cero"}

        existente_id = obtener_fianza_recibida_existente(
            cursor,
            asiento_origen_id=asiento_origen_id,
            concepto=concepto
        )

        if existente_id:
            return {
                "ok": False,
                "duplicado": True,
                "error": f"La fianza ya fue creada anteriormente (ID asiento: {existente_id})"
            }

        cursor.execute("""
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (
            fecha,
            concepto or "Fianza recibida",
            "fianza_recibida"
        ))

        asiento_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (%s, %s, %s, %s)
        """, (
            asiento_id,
            cuenta_tesoreria,
            "debe",
            round(importe, 2)
        ))

        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (%s, %s, %s, %s)
        """, (
            asiento_id,
            "560 Fianzas recibidas",
            "haber",
            round(importe, 2)
        ))

        conn.commit()

        return {"ok": True, "asiento_id": asiento_id}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()

def crear_asiento_fianza_devuelta(
    fecha,
    concepto,
    importe,
    cuenta_tesoreria="570 Caja",
    asiento_origen_id=None,
    asiento_fianza_recibida_id=None
):
    from db_context import get_connection

    if float(importe) <= 0:
        return {"ok": False, "error": "El importe debe ser mayor que cero"}

    conn = get_connection()
    cursor = conn.cursor()

    try:
        inicializar_relaciones_fianzas()

        fecha = str(fecha or "").strip()
        concepto = str(concepto or "").strip()
        importe = round(float(importe or 0), 2)

        if not fecha:
            return {"ok": False, "error": "La fecha es obligatoria"}

        existente_id = obtener_fianza_devuelta_existente(
            cursor,
            asiento_origen_id=asiento_origen_id,
            concepto=concepto
        )

        if existente_id:
            return {
                "ok": False,
                "duplicado": True,
                "error": f"Ya existe una devolución de fianza para este asiento (ID {existente_id})"
            }

        if asiento_fianza_recibida_id is None:
            return {
                "ok": False,
                "error": "No se ha indicado la fianza recibida origen"
            }

        saldo = obtener_saldo_fianza_recibida(cursor, int(asiento_fianza_recibida_id))

        if saldo["pendiente"] <= 0:
            return {
                "ok": False,
                "error": f"La fianza origen ya está completamente devuelta (ID {asiento_fianza_recibida_id})"
            }

        if importe - saldo["pendiente"] > 0.01:
            return {
                "ok": False,
                "error": (
                    f"El importe a devolver ({importe:.2f} €) supera el saldo pendiente "
                    f"de la fianza origen ({saldo['pendiente']:.2f} €)"
                )
            }

        cursor.execute("""
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (fecha, concepto, "fianza_devuelta"))

        asiento_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (%s, %s, %s, %s)
        """, (asiento_id, "560 Fianzas recibidas", "debe", float(importe)))

        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (%s, %s, %s, %s)
        """, (asiento_id, cuenta_tesoreria, "haber", float(importe)))

        cursor.execute("""
            INSERT INTO relaciones_fianzas (
                asiento_fianza_recibida_id,
                asiento_fianza_devuelta_id
            )
            VALUES (%s, %s)
        """, (int(asiento_fianza_recibida_id), int(asiento_id)))

        conn.commit()

        return {"ok": True, "asiento_id": asiento_id}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()

def registrar_pago_parcial_compra(
    fecha,
    importe,
    concepto="Pago parcial compra",
    cuenta_tesoreria="570 Caja"
):
    """
    Registra un pago parcial de una compra ya contabilizada contra proveedores.

    Debe:
        400 Proveedores

    Haber:
        570 Caja / 572 Bancos
    """
    importe = round(float(importe or 0), 2)

    if importe <= 0:
        return {
            "ok": False,
            "error": "El importe del pago parcial debe ser mayor que cero."
        }

    asiento_id = crear_asiento(
        fecha,
        concepto,
        "pago_parcial_compra"
    )

    agregar_linea_asiento(
        asiento_id,
        "400 Proveedores",
        "debe",
        importe
    )

    agregar_linea_asiento(
        asiento_id,
        cuenta_tesoreria,
        "haber",
        importe
    )

    return {
        "ok": True,
        "asiento_id": asiento_id,
        "importe": importe
    }
