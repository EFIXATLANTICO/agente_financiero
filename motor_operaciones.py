import re
import datetime
from config_empresa import CONFIG_EMPRESA


PALABRAS_BASURA_TERCERO = [
    "a credito a",
    "a credito a",
    "credito a",
    "credito a",
    "a contado a",
    "al contado a",
    "contado a",
    "a proveedor",
    "de proveedor",
    "a cliente",
    "de cliente",
    "cliente",
    "proveedor",
    "con igic",
    "con iva",
    "por valor de",
    "por valor",
    "por",
    "valor de",
]


def normalizar_texto_operacion(texto):
    return (texto or "").strip().lower()


def limpiar_nombre_tercero(nombre):
    nombre = (nombre or "").strip()

    if not nombre:
        return "Tercero no identificado"

    nombre_limpio = nombre.lower().strip()

    for basura in PALABRAS_BASURA_TERCERO:
        patron = r"^" + re.escape(basura) + r"\s+"
        nombre_limpio = re.sub(patron, "", nombre_limpio, flags=re.IGNORECASE)

    nombre_limpio = re.sub(r"\s+", " ", nombre_limpio).strip(" ,.-")

    if not nombre_limpio:
        return "Tercero no identificado"

    return nombre_limpio.upper()


def extraer_nombre_tercero_inteligente(texto):
    texto = texto or ""

    patrones = [
        r"\ba\s+(:cr[ee]dito\s+a\s+)([A-Za-zAEIOUaeiouNn0-9\s\.\-&]+)(=\s+por\s+valor\s+de|\s+por\s+\d|\s+con\s+igic|\s+con\s+iva|\s+al\s+contado|\s+a\s+\d+\s*d[ii]as|\s*$)",
        r"\bde\s+([A-Za-zAEIOUaeiouNn0-9\s\.\-&]+)(=\s+por\s+valor\s+de|\s+por\s+\d|\s+con\s+igic|\s+con\s+iva|\s+al\s+contado|\s+a\s+\d+\s*d[ii]as|\s*$)",
        r"\bcliente\s+([A-Za-zAEIOUaeiouNn0-9\s\.\-&]+)(=\s+por\s+valor\s+de|\s+por\s+\d|\s+con\s+igic|\s+con\s+iva|\s*$)",
        r"\bproveedor\s+([A-Za-zAEIOUaeiouNn0-9\s\.\-&]+)(=\s+por\s+valor\s+de|\s+por\s+\d|\s+con\s+igic|\s+con\s+iva|\s*$)",
    ]

    for patron in patrones:
        m = re.search(patron, texto, flags=re.IGNORECASE)
        if m:
            candidato = m.group(1).strip()
            candidato = limpiar_nombre_tercero(candidato)
            if candidato and candidato != "TERCERO NO IDENTIFICADO":
                return candidato

    return "Tercero no identificado"


def detectar_familia_operacion(texto):
    t = normalizar_texto_operacion(texto)

    if any(p in t for p in ["compra", "compramos", "adquirimos", "factura proveedor"]):
        return "compra"

    if any(p in t for p in ["venta", "vendemos", "factura cliente", "emitimos factura"]):
        return "venta"

    if any(p in t for p in ["cobro", "cobramos", "nos pagan", "cobrado"]):
        return "cobro"

    if any(p in t for p in ["pago", "pagamos", "abonamos", "pagado"]):
        return "pago"

    if any(p in t for p in ["aportacion socio", "aportacion socio", "aportacion de socios", "aportacion de socios"]):
        return "aportacion_socios"

    if any(p in t for p in ["ampliacion capital", "ampliacion capital", "ampliacion de capital", "ampliacion de capital"]):
        return "ampliacion_capital"

    if any(p in t for p in ["prestamo banco", "prestamo banco", "prestamo bancario", "prestamo bancario"]):
        return "prestamo_bancario"

    if any(p in t for p in ["prestamo socio", "prestamo socio", "prestamo de socio", "prestamo de socio"]):
        return "prestamo_socio"

    if any(p in t for p in ["comision bancaria", "comision bancaria", "comision", "comision"]):
        return "gasto_bancario"

    if any(p in t for p in ["nomina", "nomina"]):
        return "nomina"

    if any(p in t for p in ["seguro", "periodificacion", "periodificacion", "gasto anticipado", "ingreso anticipado"]):
        return "periodificacion"

    if any(p in t for p in ["inmovilizado", "maquinaria", "vehiculo", "vehiculo", "ordenador", "mobiliario"]):
        return "inmovilizado"

    return "desconocido"


def detectar_forma_pago_avanzada(texto):
    t = normalizar_texto_operacion(texto)

    if "al contado" in t or "contado" in t or "efectivo" in t or "caja" in t:
        return "contado"

    if "transferencia" in t or "banco" in t or "transfer" in t:
        return "transferencia"

    if "pagare" in t or "pagare" in t:
        return "pagare"

    if "confirming" in t:
        return "confirming"

    if "credito" in t or "credito" in t or "aplazado" in t:
        return "credito"

    if re.search(r"\b\d+\s*d[ii]as\b", t):
        return "credito"

    return "credito"


def detectar_plazo_dias(texto):
    t = normalizar_texto_operacion(texto)
    m = re.search(r"\b(\d+)\s*d[ii]as\b", t)
    if m:
        return int(m.group(1))
    return 0
def extraer_fecha_vencimiento(texto):
    t = normalizar_texto_operacion(texto)
    m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", t)
    if not m:
        return None

    fecha_txt = m.group(1)
    try:
        dia, mes, anio = fecha_txt.split("/")
        fecha = datetime.date(int(anio), int(mes), int(dia))
        return str(fecha)
    except Exception:
        return None


def calcular_fecha_vencimiento(fecha_operacion, plazo_dias):
    if not fecha_operacion:
        return None

    try:
        fecha_base = datetime.datetime.strptime(str(fecha_operacion), "%Y-%m-%d").date()
    except Exception:
        return None

    try:
        plazo = int(plazo_dias or 0)
    except Exception:
        plazo = 0

    if plazo <= 0:
        plazo = 30

    return str(fecha_base + datetime.timedelta(days=plazo))
def detectar_pago_mixto(texto, total):
    t = normalizar_texto_operacion(texto)
    total = float(total or 0)

    contado = 0.0
    credito = 0.0

    # Caso 1: mitad / la mitad / otra mitad
    patrones_mitad = [
        "mitad al contado",
        "la mitad al contado",
        "paga la mitad al contado",
        "paga la mitad hoy al contado",
        "mitad hoy al contado",
        "la mitad hoy al contado",
        "la otra mitad a",
        "resto a",
        "resto a credito",
        "resto a credito",
    ]

    if (
        ("mitad" in t and "contado" in t and ("resto" in t or "otra mitad" in t or "a 30 dias" in t or "a 45 dias" in t or "a 60 dias" in t or "a 90 dias" in t))
        or all(p in t for p in ["mitad", "contado", "resto"])
    ):
        contado = round(total / 2, 2)
        credito = round(total - contado, 2)
        return {
            "es_mixto": True,
            "importe_contado": contado,
            "importe_credito": credito,
        }

    # Caso 2: porcentaje al contado + resto aplazado
    m_pct = re.search(r"(\d+(:[.,]\d+))\s*%\s+(:hoy\s+)al\s+contado", t)
    if m_pct and ("resto a" in t or "resto a credito" in t or "resto a credito" in t or "otra parte a" in t):
        pct = float(m_pct.group(1).replace(",", "."))
        contado = round(total * pct / 100, 2)
        credito = round(total - contado, 2)
        return {
            "es_mixto": True,
            "importe_contado": contado,
            "importe_credito": credito,
        }

    # Caso 3: importe exacto al contado y resto aplazado
    m_importe = re.search(r"(:paga|abon[a-z]*|entrega)\s+(\d+(:[.,]\d+))\s*(:euros|)\s+(:hoy\s+)al\s+contado", t)
    if m_importe and ("resto a" in t or "resto a credito" in t or "resto a credito" in t):
        contado = float(m_importe.group(1).replace(",", "."))
        credito = round(total - contado, 2)

        if contado > 0 and credito > 0:
            return {
                "es_mixto": True,
                "importe_contado": contado,
                "importe_credito": credito,
            }

    return {
        "es_mixto": False,
        "importe_contado": 0.0,
        "importe_credito": total,
    }

def detectar_periodificacion(texto):
    t = normalizar_texto_operacion(texto)

    if any(p in t for p in ["periodificacion", "periodificacion", "gasto anticipado", "ingreso anticipado"]):
        return True

    if "anual" in t and "pagado por adelantado" in t:
        return True

    return False


def detectar_subtipo_ingreso(texto):
    t = normalizar_texto_operacion(texto)

    if "alquiler" in t or "arrendamiento" in t or "renting" in t:
        return "alquiler"

    if any(p in t for p in ["servicio", "mantenimiento", "asesoria", "asesoria"]):
        return "servicio"

    if any(p in t for p in ["mercader", "producto", "venta"]):
        return "venta"

    if CONFIG_EMPRESA.get("actividad_principal") == "alquiler de maquinaria":
        return "alquiler"

    return "venta"


def construir_evento_contable(texto, fecha_operacion=None, importe=None, igic_pct=None):
    familia = detectar_familia_operacion(texto)
    tercero = extraer_nombre_tercero_inteligente(texto)
    forma_pago = detectar_forma_pago_avanzada(texto)
    plazo_dias = detectar_plazo_dias(texto)
    periodificable = detectar_periodificacion(texto)
    subtipo_ingreso = detectar_subtipo_ingreso(texto)
    fecha_vencimiento_explicita = extraer_fecha_vencimiento(texto)

    genera_vencimiento = familia in ["compra", "venta"] and (plazo_dias > 0 or forma_pago == "credito")

    if fecha_vencimiento_explicita:
        fecha_vencimiento = fecha_vencimiento_explicita
    elif genera_vencimiento:
        fecha_vencimiento = calcular_fecha_vencimiento(fecha_operacion, plazo_dias)
    else:
        fecha_vencimiento = None

    return {
        "texto_original": texto,
        "familia": familia,
        "tercero_nombre": tercero,
        "forma_pago": forma_pago,
        "plazo_dias": plazo_dias,
        "fecha_vencimiento": fecha_vencimiento,
        "periodificable": periodificable,
        "subtipo_ingreso": subtipo_ingreso,
        "importe_detectado": importe,
        "igic_pct_detectado": igic_pct,
        "genera_vencimiento": genera_vencimiento,
        "requiere_tercero": familia in ["compra", "venta", "cobro", "pago"],
    }