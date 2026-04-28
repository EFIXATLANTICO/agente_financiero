import re
import datetime
from db_context import get_connection,obtener_empresa_id_activa
from config_empresa import CONFIG_EMPRESA
from contabilidad import crear_asiento_completo
from motor_operaciones import (
    construir_evento_contable,
    extraer_nombre_tercero_inteligente,
    detectar_pago_mixto,
)
from clasificador_operaciones import clasificar_operacion
from motor_catalogo import generar_lineas_desde_catalogo
from contabilidad import registrar_pago_parcial_compra
from operaciones_avanzadas import registrar_operacion_avanzada

# =========================
# UTILIDADES BASE
# =========================

def _texto_normalizado(texto):
    return (texto or "").strip().lower()


def _a_float(valor, default=0.0):
    try:
        if valor is None:
            return float(default)
        if isinstance(valor, (int, float)):
            return float(valor)
        texto = str(valor).strip().replace(".", "").replace(",", ".")
        return float(texto)
    except Exception:
        return float(default)


# =========================
# EXTRACCION Y DETECCION
# =========================

def extraer_importe(texto):
    """
    Extrae el importe principal de la operacion evitando confundirlo con:
    - porcentajes de IGIC/IVA
    - plazos tipo '45 dias'
    - numeros accesorios
    Prioriza importes expresados con 'por', 'por valor de', 'importe', 'total'.
    """
    texto_original = texto or ""
    t = _texto_normalizado(texto_original)

    # 1) Prioridad maxima: patrones explicitos de importe
    patrones_importe = [
        r"\bpor\s+valor\s+de\s+(\d+(:[.,]\d+))",
        r"\bpor\s+(\d+(:[.,]\d+))\s*(:euros|)",
        r"\bimporte\s+de\s+(\d+(:[.,]\d+))",
        r"\btotal\s+de\s+(\d+(:[.,]\d+))",
    ]

    for patron in patrones_importe:
        m = re.search(patron, t, flags=re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", "."))

    # 2) Si no hay patron explicito, filtrar numeros problematicos
    candidatos = []

    for match in re.finditer(r"\d+(:[.,]\d+)", texto_original):
        valor_txt = match.group(0)
        inicio, fin = match.span()

        contexto_previo = t[max(0, inicio - 20):inicio]
        contexto_posterior = t[fin:min(len(t), fin + 20)]

        es_porcentaje_fiscal = (
            "igic" in contexto_previo
            or "iva" in contexto_previo
            or "%" in contexto_posterior
        )

        es_plazo = (
            "dia" in contexto_posterior
            or "dias" in contexto_posterior
            or "dias" in contexto_posterior
            or "dia" in contexto_posterior
        )

        if es_porcentaje_fiscal or es_plazo:
            continue

        candidatos.append(valor_txt)

    if not candidatos:
        numeros = re.findall(r"\d+(:[.,]\d+)", texto_original)
        if not numeros:
            return None
        candidatos = numeros

    # 3) Mejor quedarse con el mayor candidato que con el ultimo:
    # normalmente el importe sera mayor que dias (45), IGIC (7), etc.
    valores = []
    for c in candidatos:
        try:
            valores.append(float(c.replace(",", ".")))
        except Exception:
            pass

    if not valores:
        return None

    return max(valores)

def detectar_forma_pago(texto):
    t = _texto_normalizado(texto)

    if "contado" in t or "al contado" in t or "efectivo" in t or "caja" in t:
        return "contado"

    if "transferencia" in t or "banco" in t or "transfer" in t:
        return "transferencia"

    if "pagare" in t or "pagare" in t:
        return "pagare"

    if "confirming" in t:
        return "confirming"

    if "credito" in t or "credito" in t or "aplazado" in t:
        return "credito"

    return "credito"


def detectar_tipo_operacion(texto):
    t = _texto_normalizado(texto)

    patrones_compra = [
        "compra", "compramos", "adquirimos",
        "factura proveedor", "recibimos factura",
        "pago de alquiler", "factura de",
    ]

    patrones_venta = [
        "venta", "vendemos",
        "factura cliente", "emitimos factura",
        "cobro", "ingreso",
        "servicio", "prestacion",
        "alquiler cobrado",
    ]

    patrones_financiacion = [
        "prestamo", "prestamo",
        "amortizacion", "amortizacion",
        "principal", "intereses",
        "anticipo", "fianza",
    ]

    if any(p in t for p in patrones_compra):
        return "compra"

    if any(p in t for p in patrones_venta):
        return "venta"

    if any(p in t for p in patrones_financiacion):
        return "financiacion"

    return "desconocido"

def detectar_tipo_ingreso(texto):
    t = _texto_normalizado(texto)

    if "alquiler" in t or "arrendamiento" in t or "renting" in t:
        return "alquiler"

    if any(p in t for p in ["servicio", "mantenimiento", "asesoria", "asesoria"]):
        return "servicio"

    if any(p in t for p in ["venta", "mercader", "producto", "maquina", "maquina", "maquinaria"]):
        return "venta"

    if CONFIG_EMPRESA.get("actividad_principal") == "alquiler de maquinaria":
        return "alquiler"

    return "venta"


def detectar_tipo_avanzado(texto):
    t = _texto_normalizado(texto)

    if any(p in t for p in [
        "aportacion socio", "aportacion socio", "aportacion de socios", "aportacion de socios"
    ]):
        return "aportacion_socios"

    if any(p in t for p in [
        "ampliacion capital", "ampliacion capital", "ampliacion de capital", "ampliacion de capital"
    ]):
        return "ampliacion_capital"

    if any(p in t for p in [
        "prestamo socio", "prestamo socio", "prestamo de socio", "prestamo de socio"
    ]):
        return "prestamo_socio"

    if any(p in t for p in [
        "prestamo banco", "prestamo banco", "prestamo bancario", "prestamo bancario"
    ]):
        return "prestamo_bancario"

    if "intereses" in t:
        return "intereses"

    if "comision" in t or "comision" in t:
        return "gasto_bancario"

    return None


def extraer_tercero(texto):
    return extraer_nombre_tercero_inteligente(texto)


def extraer_igic(texto, igic_defecto=7.0):
    t = _texto_normalizado(texto)
    m = re.search(r"(:igic|iva)\s+(\d+(:[.,]\d+))", t)
    if m:
        return float(m.group(1).replace(",", "."))
    return float(igic_defecto)


# =========================
# TERCEROS
# =========================

def buscar_o_crear_tercero(nombre, tipo):
    conn = get_connection()
    cursor = conn.cursor()

    nombre = (nombre or "Tercero no identificado").strip()

    try:
        if tipo == "compra":
            cursor.execute(
                """
                SELECT id
                FROM proveedores
                WHERE UPPER(TRIM(nombre)) = UPPER(TRIM(%s))
                LIMIT 1
                """,
                (nombre,),
            )
            fila = cursor.fetchone()
            if fila:
                return fila[0], "proveedor"

            cursor.execute(
                """
                INSERT INTO proveedores (nombre, nif, direccion, email, telefono)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (nombre, "", "", "", ""),
            )
            tercero_id = cursor.fetchone()[0]
            conn.commit()
            return tercero_id, "proveedor"

        if tipo == "venta":
            cursor.execute(
                """
                SELECT id
                FROM clientes
                WHERE UPPER(TRIM(nombre)) = UPPER(TRIM(%s))
                LIMIT 1
                """,
                (nombre,),
            )
            fila = cursor.fetchone()
            if fila:
                return fila[0], "cliente"

            cursor.execute(
                """
                INSERT INTO clientes (nombre, nif, direccion, email, telefono)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (nombre, "", "", "", ""),
            )
            tercero_id = cursor.fetchone()[0]
            conn.commit()
            return tercero_id, "cliente"

        return None, None
    finally:
        conn.close()


def obtener_cuenta_pago(forma_pago):
    if forma_pago == "contado":
        return CONFIG_EMPRESA["cuenta_caja"]

    if forma_pago == "transferencia":
        return CONFIG_EMPRESA["cuenta_bancos"]

    if forma_pago == "pagare":
        return CONFIG_EMPRESA["cuenta_efectos_pagar"]

    if forma_pago == "confirming":
        return CONFIG_EMPRESA["cuenta_proveedores"]

    return CONFIG_EMPRESA["cuenta_proveedores"]


# =========================
# VALIDACIONES
# =========================

def validar_partida_doble(lineas):
    debe = round(sum(float(l[2]) for l in lineas if l[1] == "debe"), 2)
    haber = round(sum(float(l[2]) for l in lineas if l[1] == "haber"), 2)

    return {"debe": debe, "haber": haber, "cuadra": debe == haber}


def detectar_errores_lineas(lineas):
    errores = []

    for cuenta, movimiento, importe in lineas:
        if not cuenta:
            errores.append("Hay una cuenta vacia")
        if movimiento not in ["debe", "haber"]:
            errores.append(f"Movimiento invalido en {cuenta}")
        if importe is None:
            errores.append(f"Importe vacio en {cuenta}")
            continue

        try:
            if float(importe) <= 0:
                errores.append(f"Importe invalido en {cuenta}")
        except Exception:
            errores.append(f"Importe no numerico en {cuenta}")

    return errores


def registrar_validacion_contable(fecha, origen, estado, mensaje, detalle=""):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO validaciones_contables (
                empresa_id, fecha, origen, referencia_id, estado, mensaje, detalle, bloqueante
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                None,
                fecha,
                origen,
                None,
                estado,
                mensaje,
                detalle,
                1 if estado == "rojo" else 0,
            ),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


# =========================
# REGISTRO EN BD
# =========================



def registrar_asiento_compuesto(fecha, concepto, lineas, tipo_operacion):
    validacion = validar_partida_doble(lineas)
    errores = detectar_errores_lineas(lineas)

    if errores:
        registrar_validacion_contable(
            fecha=fecha,
            origen="operacion_inteligente",
            estado="rojo",
            mensaje="Errores en lineas del asiento",
            detalle=" | ".join(errores),
        )
        return {"ok": False, "mensaje": "Errores en las lineas del asiento", "errores": errores}

    if not validacion["cuadra"]:
        registrar_validacion_contable(
            fecha=fecha,
            origen="operacion_inteligente",
            estado="rojo",
            mensaje="El asiento no cuadra",
            detalle=f"Debe={validacion['debe']} Haber={validacion['haber']}",
        )
        return {"ok": False, "mensaje": "El asiento no cuadra (error contable)", "validacion": validacion}

    try:
        asiento_id = crear_asiento_completo(
            fecha=fecha,
            concepto=concepto,
            tipo_operacion=tipo_operacion,
            lineas=lineas,
        )
    except Exception as e:
        registrar_validacion_contable(
            fecha=fecha,
            origen="operacion_inteligente",
            estado="rojo",
            mensaje="Error al registrar asiento",
            detalle=str(e),
        )
        return {"ok": False, "mensaje": f"Error al registrar asiento: {e}"}

    registrar_validacion_contable(
        fecha=fecha,
        origen="operacion_inteligente",
        estado="verde",
        mensaje="Asiento registrado correctamente",
        detalle=f"Asiento ID {asiento_id}",
    )

    return {"ok": True, "asiento_id": asiento_id, "validacion": validacion}

def registrar_operacion_bd(datos, cursor=None):
    cierre_local = False
    conn = None

    if cursor is None:
        conn = get_connection()
        cursor = conn.cursor()
        cierre_local = True

    cursor.execute(
        """
        INSERT INTO operaciones (
            empresa_id,
            tipo_operacion,
            fecha_operacion,
            concepto,
            nombre_tercero,
            numero_factura,
            forma_pago,
            base_imponible,
            impuesto_pct,
            cuota_impuesto,
            total
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            int(datos.get("empresa_id", 1)),
            datos.get("tipo_operacion"),
            datos.get("fecha_operacion"),
            datos.get("concepto"),
            datos.get("nombre_tercero"),
            datos.get("numero_factura"),
            datos.get("forma_pago"),
            _a_float(datos.get("base_imponible", 0)),
            _a_float(datos.get("impuesto_pct", 0)),
            _a_float(datos.get("cuota_impuesto", 0)),
            _a_float(datos.get("total", 0)),
        ),
    )

    operacion_id = cursor.fetchone()[0]

    if cierre_local:
        conn.commit()
        conn.close()

    return operacion_id


def _registrar_operacion_y_asiento(fecha, concepto, lineas, tipo_operacion_asiento, datos_operacion):
    validacion = validar_partida_doble(lineas)
    errores = detectar_errores_lineas(lineas)

    if errores:
        registrar_validacion_contable(
            fecha=fecha,
            origen="operacion_inteligente",
            estado="rojo",
            mensaje="Errores en lineas del asiento",
            detalle=" | ".join(errores),
        )
        return {"ok": False, "mensaje": "Errores en las lineas del asiento", "errores": errores}

    if not validacion["cuadra"]:
        registrar_validacion_contable(
            fecha=fecha,
            origen="operacion_inteligente",
            estado="rojo",
            mensaje="El asiento no cuadra",
            detalle=f"Debe={validacion['debe']} Haber={validacion['haber']}",
        )
        return {"ok": False, "mensaje": "El asiento no cuadra (error contable)", "validacion": validacion}

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (fecha, concepto, tipo_operacion_asiento),
        )
        asiento_id = cursor.fetchone()[0]

        for cuenta, movimiento, importe in lineas:
            movimiento = (movimiento or "").strip().lower()

            if movimiento not in ("debe", "haber"):
                raise ValueError("El movimiento debe ser 'debe' o 'haber'")

            cursor.execute(
                """
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (%s, %s, %s, %s)
                """,
                (asiento_id, cuenta, movimiento, float(importe)),
            )

        operacion_id = registrar_operacion_bd(datos_operacion, cursor=cursor)

        cursor.execute(
            """
            INSERT INTO operaciones_asientos (operacion_id, asiento_id)
            VALUES (%s, %s)
            """,
            (operacion_id, asiento_id),
           )

        conn.commit()

    except Exception as e:
        conn.rollback()
        registrar_validacion_contable(
            fecha=fecha,
            origen="operacion_inteligente",
            estado="rojo",
            mensaje="Error al registrar operacion completa",
            detalle=str(e),
        )
        return {"ok": False, "mensaje": f"Error al registrar operacion: {e}"}

    finally:
        conn.close()

    registrar_validacion_contable(
        fecha=fecha,
        origen="operacion_inteligente",
        estado="verde",
        mensaje="Operacion y asiento registrados correctamente",
        detalle=f"Asiento ID {asiento_id} | Operacion ID {operacion_id}",
    )

    return {
        "ok": True,
        "asiento_id": asiento_id,
        "operacion_id": operacion_id,
        "validacion": validacion,
    }


def detectar_numero_plazos(texto):
    texto = (texto or "").lower()

    match = re.search(r"(\d+)\s*(plazos|pagos|cuotas)", texto)
    if match:
        return int(match.group(1))

    if "fraccionado" in texto:
        return 2

    return 1


def registrar_vencimiento_operacion(
    empresa_id,
    operacion_id,
    fecha_vencimiento,
    importe,
    tipo,
    nombre_tercero
):
    if not operacion_id or not fecha_vencimiento:
        return {"ok": False, "mensaje": "Faltan datos para crear el vencimiento"}

    conn = get_connection()
    cursor = conn.cursor()

    try:
        importe = float(importe or 0)

        cursor.execute(
            """
            INSERT INTO vencimientos (
                empresa_id,
                factura_id,
                fecha_vencimiento,
                importe,
                importe_pendiente,
                estado,
                tipo,
                nombre_tercero
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                empresa_id,
                operacion_id,
                fecha_vencimiento,
                importe,
                importe,
                "pendiente",
                tipo,
                nombre_tercero
            ),
        )

        conn.commit()
        return {"ok": True}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

    finally:
        conn.close()

def registrar_vencimientos_multiples(
    empresa_id,
    operacion_id,
    fecha_operacion,
    fecha_vencimiento_base,
    importe_total,
    tipo,
    nombre_tercero,
    numero_plazos
):
    if not fecha_operacion:
        return {"ok": False, "mensaje": "Falta fecha de operacion"}

    if not fecha_vencimiento_base:
        return {"ok": False, "mensaje": "Falta fecha de vencimiento base"}

    try:
        numero_plazos = int(numero_plazos or 1)
    except Exception:
        numero_plazos = 1

    if numero_plazos <= 1:
        return registrar_vencimiento_operacion(
            empresa_id=empresa_id,
            operacion_id=operacion_id,
            fecha_vencimiento=fecha_vencimiento_base,
            importe=importe_total,
            tipo=tipo,
            nombre_tercero=nombre_tercero,
        )

    try:
        fecha_op = datetime.datetime.strptime(str(fecha_operacion), "%Y-%m-%d").date()
        fecha_base = datetime.datetime.strptime(str(fecha_vencimiento_base), "%Y-%m-%d").date()
    except Exception:
        return {"ok": False, "mensaje": "Formato de fecha invalido para generar plazos"}

    diferencia_dias = (fecha_base - fecha_op).days
    if diferencia_dias <= 0:
        diferencia_dias = 30

    importe_total = float(importe_total or 0)
    importe_por_plazo = round(importe_total / numero_plazos, 2)

    for i in range(numero_plazos):
        dias_plazo = diferencia_dias * (i + 1)
        fecha_venc_i = str(fecha_op + datetime.timedelta(days=dias_plazo))

        if i == numero_plazos - 1:
            importe_i = round(importe_total - (importe_por_plazo * (numero_plazos - 1)), 2)
        else:
            importe_i = importe_por_plazo

        resultado = registrar_vencimiento_operacion(
            empresa_id=empresa_id,
            operacion_id=operacion_id,
            fecha_vencimiento=fecha_venc_i,
            importe=importe_i,
            tipo=tipo,
            nombre_tercero=nombre_tercero,
        )

        if not resultado["ok"]:
            return resultado

    return {"ok": True}

def calcular_pago_operacion(total, pago_total=True, anticipo=0):
    if pago_total:
        return total, 0
    pendiente = round(total - anticipo, 2)
    return anticipo, pendiente
def existe_operacion_parecida_reciente(fecha, concepto, total, tipo_operacion):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM operaciones
            WHERE fecha_operacion = %s
              AND concepto = %s
              AND ROUND(COALESCE(total, 0)::numeric, 2) = ROUND(%s::numeric, 2)
              AND tipo_operacion = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (fecha, concepto, float(total), tipo_operacion),
        )
        fila = cursor.fetchone()
        return fila is not None
    finally:
        conn.close()

# =========================
# PROCESAMIENTO PRINCIPAL
# =========================

def procesar_operacion_texto(texto, fecha, igic_defecto=7.0):
    resultado_avanzado = registrar_operacion_avanzada(texto, fecha, igic_defecto)
    if resultado_avanzado is not None:
        return resultado_avanzado

    empresa_id = obtener_empresa_id_activa()

    clasificacion = clasificar_operacion(texto)
    if clasificacion:
        tipo_catalogo = clasificacion["clave"]
        definicion = clasificacion["definicion"]
    else:
        tipo_catalogo = None
        definicion = None

    tipo = detectar_tipo_operacion(texto)
    tipo_avanzado = detectar_tipo_avanzado(texto)

    texto_tipo = _texto_normalizado(texto)

    fuerza_venta = any(
        patron in texto_tipo
        for patron in [
            "venta",
            "vendemos",
            "vendo",
            "factura cliente",
            "emitimos factura",
            "cobra",
            "cobro",
            "cobrado",
            "ingreso",
        ]
    )

    fuerza_compra = any(
        patron in texto_tipo
        for patron in [
            "compra",
            "compramos",
            "compro",
            "adquirimos",
            "factura proveedor",
            "recibimos factura",
            "pago proveedor",
        ]
    )

    if fuerza_venta:
        tipo = "venta"
    elif fuerza_compra:
        tipo = "compra"
    elif clasificacion:
        tipo_catalogo_regla = (definicion.get("reglas", {}).get("tipo") or "").lower()
        if tipo_catalogo_regla in ["compra", "venta", "financiacion"]:
            tipo = tipo_catalogo_regla

    if tipo == "desconocido":
        return {"ok": False, "mensaje": "No se pudo detectar el tipo de operacion"}

    importe_base = extraer_importe(texto)
    if importe_base is None:
        return {"ok": False, "mensaje": "No se pudo detectar el importe"}

    if tipo_avanzado == "aportacion_socios":
        importe = extraer_importe(texto)
        if importe is None:
            return {"ok": False, "mensaje": "No se pudo detectar el importe"}
        lineas = [
            (CONFIG_EMPRESA["cuenta_bancos"], "debe", importe),
            ("118 Aportaciones de socios", "haber", importe),
        ]

        resultado_asiento = registrar_asiento_compuesto(
            fecha=fecha,
            concepto=texto,
            lineas=lineas,
            tipo_operacion="aportacion_socios",
        )

        if not resultado_asiento["ok"]:
            return resultado_asiento

        return {
            "ok": True,
            "tipo": "aportacion_socios",
            "asiento_id": resultado_asiento["asiento_id"],
            "importe": importe,
            "lineas": lineas,
        }

    if tipo_avanzado == "ampliacion_capital":
        importe = extraer_importe(texto)
        if importe is None:
            return {"ok": False, "mensaje": "No se pudo detectar el importe"}

        lineas = [
            (CONFIG_EMPRESA["cuenta_bancos"], "debe", importe),
            ("100 Capital social", "haber", importe),
        ]

        resultado_asiento = registrar_asiento_compuesto(
            fecha=fecha,
            concepto=texto,
            lineas=lineas,
            tipo_operacion="ampliacion_capital",
        )

        if not resultado_asiento["ok"]:
            return resultado_asiento

        return {
            "ok": True,
            "tipo": "ampliacion_capital",
            "asiento_id": resultado_asiento["asiento_id"],
            "importe": importe,
            "lineas": lineas,
        }

    if tipo_avanzado == "prestamo_socio":
        importe = extraer_importe(texto)
        if importe is None:
            return {"ok": False, "mensaje": "No se pudo detectar el importe"}

        lineas = [
            (CONFIG_EMPRESA["cuenta_bancos"], "debe", importe),
            ("551 Cuenta con socios", "haber", importe),
        ]

        resultado_asiento = registrar_asiento_compuesto(
            fecha=fecha,
            concepto=texto,
            lineas=lineas,
            tipo_operacion="prestamo_socio",
        )

        if not resultado_asiento["ok"]:
            return resultado_asiento

        return {
            "ok": True,
            "tipo": "prestamo_socio",
            "asiento_id": resultado_asiento["asiento_id"],
            "importe": importe,
            "lineas": lineas,
        }

    if tipo_avanzado == "gasto_bancario":
        importe = extraer_importe(texto)
        if importe is None:
            return {"ok": False, "mensaje": "No se pudo detectar el importe"}

        lineas = [
            ("626 Servicios bancarios", "debe", importe),
            (CONFIG_EMPRESA["cuenta_bancos"], "haber", importe),
        ]

        resultado_asiento = registrar_asiento_compuesto(
            fecha=fecha,
            concepto=texto,
            lineas=lineas,
            tipo_operacion="gasto_bancario",
        )

        if not resultado_asiento["ok"]:
            return resultado_asiento

        return {
            "ok": True,
            "tipo": "gasto_bancario",
            "asiento_id": resultado_asiento["asiento_id"],
            "importe": importe,
            "lineas": lineas,
        }
    if clasificacion and "financiacion" in tipo_catalogo:
        tipo = "financiacion"

    if tipo == "desconocido":
        return {"ok": False, "mensaje": "No se pudo detectar el tipo de operacion"}

    importe_base = extraer_importe(texto)
    if importe_base is None:
        return {"ok": False, "mensaje": "No se pudo detectar el importe"}

    tercero = extraer_tercero(texto)
    igic_pct = extraer_igic(texto, igic_defecto)
    if definicion:
        subtipo = (definicion.get("reglas", {}).get("subtipo") or "").lower()
        if subtipo in [
            "anticipo_proveedor",
            "anticipo_cliente",
            "fianza_entregada",
            "fianza_recibida",
            "prestamo_recibido",
            "devolucion_prestamo",
            "intereses",
        ]:
            igic_pct = 0.0

    evento = construir_evento_contable(
        texto=texto,
        fecha_operacion=fecha,
        importe=importe_base,
        igic_pct=igic_pct,
    )

    contexto_catalogo = {
        "forma_pago": evento["forma_pago"],
        "base": importe_base,
        "impuesto": round(importe_base * igic_pct / 100, 2),
        "total": round(importe_base + (importe_base * igic_pct / 100), 2),
        "cuenta_activo": (definicion or {}).get("reglas", {}).get("cuenta_activo"),
        "cuenta_gasto": (definicion or {}).get("reglas", {}).get("cuenta_gasto"),
        "cuenta_base": (definicion or {}).get("reglas", {}).get("cuenta_base"),
        "cuenta_pasivo": (definicion or {}).get("reglas", {}).get("cuenta_pasivo"),
    }

    forma_pago = evento["forma_pago"]

    igic = round(importe_base * igic_pct / 100, 2)
    total = round(importe_base + igic, 2)

    reparto_pago = detectar_pago_mixto(texto, total)

    texto_pago_mixto = _texto_normalizado(texto)

    if not reparto_pago.get("es_mixto"):
        if (
            "mitad" in texto_pago_mixto
            and (
                "resto" in texto_pago_mixto
                or "otra mitad" in texto_pago_mixto
                or "otro 50" in texto_pago_mixto
            )
        ):
            importe_contado = round(total / 2, 2)
            importe_credito = round(total - importe_contado, 2)

            reparto_pago["es_mixto"] = True
            reparto_pago["importe_contado"] = importe_contado
            reparto_pago["importe_credito"] = importe_credito

    tercero_id, tipo_tercero = buscar_o_crear_tercero(tercero, tipo)
    if tipo == "financiacion":
        if definicion:
            lineas = generar_lineas_desde_catalogo(definicion, contexto_catalogo)
        else:
            return {"ok": False, "mensaje": "No se pudo resolver la operacion financiera"}

        resultado = _registrar_operacion_y_asiento(
            fecha=fecha,
            concepto=texto,
            lineas=lineas,
            tipo_operacion_asiento="operacion_inteligente_financiacion",
            datos_operacion={
                "empresa_id": empresa_id,
                "tipo_operacion": "financiacion",
                "fecha_operacion": fecha,
                "concepto": texto,
                "nombre_tercero": tercero,
                "numero_factura": None,
                "forma_pago": forma_pago,
                "base_imponible": importe_base,
                "impuesto_pct": 0,
                "cuota_impuesto": 0,
                "total": importe_base,
            },
        )

        if not resultado["ok"]:
            return resultado

        return {
            "ok": True,
            "operacion_id": resultado["operacion_id"],
            "asiento_id": resultado["asiento_id"],
            "tipo": tipo,
            "tercero": tercero,
            "tercero_id": tercero_id,
            "tipo_tercero": tipo_tercero,
            "forma_pago": forma_pago,
            "base": importe_base,
            "igic_pct": 0,
            "igic": 0,
            "total": importe_base,
            "lineas": lineas,
            "evento": evento,
        }

    if tipo == "compra":
        if existe_operacion_parecida_reciente(fecha, texto, total, "compra"):
            return {"ok": False, "mensaje": "Ya existe una operacion muy similar registrada. Revisa antes de duplicar."}

        if reparto_pago["es_mixto"]:
            importe_contado = round(float(reparto_pago.get("importe_contado") or 0), 2)
            importe_credito = round(float(reparto_pago.get("importe_credito") or 0), 2)

            if definicion:
                cuenta_compra = (
                    contexto_catalogo.get("cuenta_activo")
                    or CONFIG_EMPRESA["cuenta_compra_mercaderia"]
                )
            else:
                cuenta_compra = CONFIG_EMPRESA["cuenta_compra_mercaderia"]

            lineas = [
                (cuenta_compra, "debe", importe_base),
                (CONFIG_EMPRESA["cuenta_igic_soportado"], "debe", igic),
                (CONFIG_EMPRESA["cuenta_proveedores"], "haber", total),
            ]
        else:
            if definicion:
                lineas = generar_lineas_desde_catalogo(definicion, contexto_catalogo)
            else:
                cuenta_haber = obtener_cuenta_pago(forma_pago)

                lineas = [
                    (CONFIG_EMPRESA["cuenta_compra_mercaderia"], "debe", importe_base),
                    (CONFIG_EMPRESA["cuenta_igic_soportado"], "debe", igic),
                    (cuenta_haber, "haber", total),
                ]

        resultado = _registrar_operacion_y_asiento(
            fecha=fecha,
            concepto=texto,
            lineas=lineas,
            tipo_operacion_asiento="operacion_inteligente_compra",
            datos_operacion={
                "empresa_id": empresa_id,
                "tipo_operacion": "compra",
                "fecha_operacion": fecha,
                "concepto": texto,
                "nombre_tercero": tercero,
                "numero_factura": None,
                "forma_pago": forma_pago,
                "base_imponible": importe_base,
                "impuesto_pct": igic_pct,
                "cuota_impuesto": igic,
                "total": total,
            },
        )

        if not resultado["ok"]:
            return resultado

        resultado_pago_parcial = None

        if reparto_pago["es_mixto"] and round(float(reparto_pago.get("importe_contado") or 0), 2) > 0:
            texto_pago = _texto_normalizado(texto)

            cuenta_pago = (
                CONFIG_EMPRESA["cuenta_caja"]
                if "efectivo" in texto_pago or "caja" in texto_pago
                else CONFIG_EMPRESA["cuenta_bancos"]
            )

            resultado_pago_parcial = registrar_pago_parcial_compra(
                fecha=fecha,
                importe=round(float(reparto_pago.get("importe_contado") or 0), 2),
                concepto=f"Pago parcial proveedor - {texto}",
                cuenta_tesoreria=cuenta_pago
            )

            resultado["pago_parcial"] = resultado_pago_parcial


        if evento.get("genera_vencimiento"):
            nombre_proveedor = tercero

            if not nombre_proveedor or nombre_proveedor == "Tercero no identificado":
                match = re.search(r"a\s+(.+)\s+por", texto.lower())
                if match:
                    nombre_proveedor = match.group(1).strip().upper()
                else:
                    nombre_proveedor = "PROVEEDOR DESCONOCIDO"

            numero_plazos = detectar_numero_plazos(texto)

            if reparto_pago["es_mixto"]:
                importe_vencimiento = float(reparto_pago["importe_credito"] or 0)
            else:
                importe_vencimiento = float(total)

            if importe_vencimiento <= 0:
                resultado_vencimiento = {"ok": True}
            else:
                resultado_vencimiento = registrar_vencimientos_multiples(
                    empresa_id=empresa_id,
                    operacion_id=resultado["operacion_id"],
                    fecha_operacion=fecha,
                    fecha_vencimiento_base=evento.get("fecha_vencimiento"),
                    importe_total=importe_vencimiento,
                    tipo="pago",
                    nombre_tercero=nombre_proveedor,
                    numero_plazos=numero_plazos,
                )

            if not resultado_vencimiento["ok"]:
                return {
                    "ok": False,
                    "mensaje": f"Operacion registrada, pero fallo el vencimiento: {resultado_vencimiento['mensaje']}"
                }

        return {
            "ok": True,
            "operacion_id": resultado["operacion_id"],
            "asiento_id": resultado["asiento_id"],
            "tipo": tipo,
            "tercero": tercero,
            "tercero_id": tercero_id,
            "tipo_tercero": tipo_tercero,
            "forma_pago": forma_pago,
            "base": importe_base,
            "igic_pct": igic_pct,
            "igic": igic,
            "total": total,
            "lineas": lineas,
            "evento": evento,
            "pago_parcial": resultado_pago_parcial,
            "importe_pagado_hoy": round(float(reparto_pago.get("importe_contado") or 0), 2) if reparto_pago["es_mixto"] else 0.0,
            "importe_pendiente": round(float(reparto_pago.get("importe_credito") or total), 2) if reparto_pago["es_mixto"] else total,
        }
    if tipo == "venta":
        if existe_operacion_parecida_reciente(fecha, texto, total, "venta"):
            return {"ok": False, "mensaje": "Ya existe una operacion muy similar registrada. Revisa antes de duplicar."}

        subtipo_ingreso = detectar_tipo_ingreso(texto)
        if subtipo_ingreso == "alquiler":
            cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_alquiler"]
        elif subtipo_ingreso == "servicio":
            cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_servicio"]
        else:
            cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_venta"]

        if definicion:
            subfamilia = definicion.get("subtipo")

            if subfamilia == "servicios":
                cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_servicio"]
            elif subfamilia == "alquileres":
                cuenta_ingreso = CONFIG_EMPRESA["cuenta_ingreso_alquiler"]

        if reparto_pago["es_mixto"]:
            texto_pago = _texto_normalizado(texto)

            cuenta_cobro_inmediato = (
                CONFIG_EMPRESA["cuenta_caja"]
                if "efectivo" in texto_pago or "caja" in texto_pago
                else CONFIG_EMPRESA["cuenta_bancos"]
            )

            importe_contado = round(float(reparto_pago.get("importe_contado") or 0), 2)
            importe_credito = round(float(reparto_pago.get("importe_credito") or 0), 2)

            lineas = [
                (cuenta_cobro_inmediato, "debe", importe_contado),
                (CONFIG_EMPRESA["cuenta_clientes"], "debe", importe_credito),
                (cuenta_ingreso, "haber", importe_base),
                (CONFIG_EMPRESA["cuenta_igic_repercutido"], "haber", igic),
            ]

        else:
            texto_pago = _texto_normalizado(texto)

            if (
                "cobrado" in texto_pago
                or "cobra" in texto_pago
                or "cobro" in texto_pago
                or "al contado" in texto_pago
                or "contado" in texto_pago
                or forma_pago in ["contado", "transferencia"]
            ):
                cuenta_debe = (
                    CONFIG_EMPRESA["cuenta_caja"]
                    if "efectivo" in texto_pago or "caja" in texto_pago
                    else CONFIG_EMPRESA["cuenta_bancos"]
                )
            else:
                cuenta_debe = CONFIG_EMPRESA["cuenta_clientes"]

            lineas = [
                (cuenta_debe, "debe", total),
                (cuenta_ingreso, "haber", importe_base),
                (CONFIG_EMPRESA["cuenta_igic_repercutido"], "haber", igic),
            ]

        resultado = _registrar_operacion_y_asiento(
            fecha=fecha,
            concepto=texto,
            lineas=lineas,
            tipo_operacion_asiento="operacion_inteligente_venta",
            datos_operacion={
                "empresa_id": empresa_id,
                "tipo_operacion": "venta",
                "fecha_operacion": fecha,
                "concepto": texto,
                "nombre_tercero": tercero,
                "numero_factura": None,
                "forma_pago": forma_pago,
                "base_imponible": importe_base,
                "impuesto_pct": igic_pct,
                "cuota_impuesto": igic,
                "total": total,
            },
        )

        if not resultado["ok"]:
            return resultado

        if evento.get("genera_vencimiento"):
            nombre_cliente = tercero

            if not nombre_cliente or nombre_cliente == "Tercero no identificado":
                match = re.search(r"a\s+(.+)\s+por", texto.lower())
                if match:
                    nombre_cliente = match.group(1).strip().upper()
                else:
                    nombre_cliente = "CLIENTE DESCONOCIDO"

            numero_plazos = detectar_numero_plazos(texto)
            if reparto_pago["es_mixto"]:
                importe_vencimiento = float(reparto_pago["importe_credito"] or 0)
            else:
                importe_vencimiento = float(total)

            if importe_vencimiento <= 0:
                resultado_vencimiento = {"ok": True}
            else:
                resultado_vencimiento = registrar_vencimientos_multiples(
                    empresa_id=empresa_id,
                    operacion_id=resultado["operacion_id"],
                    fecha_operacion=fecha,
                    fecha_vencimiento_base=evento.get("fecha_vencimiento"),
                    importe_total=importe_vencimiento,
                    tipo="cobro",
                    nombre_tercero=nombre_cliente,
                    numero_plazos=numero_plazos,
                )

            if not resultado_vencimiento["ok"]:
                return {
                    "ok": False,
                    "mensaje": f"Operacion registrada, pero fallo el vencimiento: {resultado_vencimiento['mensaje']}"
                }

        return {
            "ok": True,
            "operacion_id": resultado["operacion_id"],
            "asiento_id": resultado["asiento_id"],
            "tipo": tipo,
            "tercero": tercero,
            "tercero_id": tercero_id,
            "tipo_tercero": tipo_tercero,
            "forma_pago": forma_pago,
            "base": importe_base,
            "igic_pct": igic_pct,
            "igic": igic,
            "total": total,
            "lineas": lineas,
            "evento": evento,
        }

    return {"ok": False, "mensaje": "Tipo no soportado todavia"}
