import datetime
import re
import unicodedata

from db_context import get_connection, obtener_empresa_id_activa
from config_empresa import CONFIG_EMPRESA


CUENTAS = {
    "bancos": CONFIG_EMPRESA.get("cuenta_bancos", "572 Bancos"),
    "caja": CONFIG_EMPRESA.get("cuenta_caja", "570 Caja"),
    "clientes": CONFIG_EMPRESA.get("cuenta_clientes", "430 Clientes"),
    "proveedores": CONFIG_EMPRESA.get("cuenta_proveedores", "400 Proveedores"),
    "igic_soportado": CONFIG_EMPRESA.get("cuenta_igic_soportado", "472 Hacienda Publica IGIC soportado"),
    "igic_repercutido": CONFIG_EMPRESA.get("cuenta_igic_repercutido", "477 Hacienda Publica IGIC repercutido"),
    "ventas": CONFIG_EMPRESA.get("cuenta_ingreso_venta", "700 Ventas de mercaderias"),
    "servicios": CONFIG_EMPRESA.get("cuenta_ingreso_servicio", "705 Prestaciones de servicios"),
    "compras": CONFIG_EMPRESA.get("cuenta_compra_mercaderia", "600 Compras de mercaderias"),
}


ESCENARIOS_DEMO_60 = [
    "Venta de mercaderias mixta contado/credito",
    "Compra de materias primas a credito",
    "Compra de maquinaria con pago parcial y financiacion",
    "Venta de servicios cobrada por transferencia",
    "Nominas con retenciones",
    "Pago de seguros sociales",
    "Compra de mobiliario al contado",
    "Venta con letra a 90 dias",
    "Pago de alquiler con impuesto",
    "Seguro anual pagado",
    "Suministros pendientes",
    "Cobro de cliente anterior",
    "Pago a proveedor anterior",
    "Devolucion a proveedor",
    "Devolucion de cliente",
    "Amortizacion de maquinaria",
    "Amortizacion de mobiliario",
    "Prestamo bancario recibido",
    "Pago de intereses",
    "Cuota de prestamo",
    "Compra de existencias al contado",
    "Regularizacion de existencias finales",
    "Publicidad con tarjeta",
    "Venta de vehiculo",
    "Compra de software",
    "Servicios profesionales con retencion",
    "Liquidacion trimestral de impuesto indirecto",
    "Impuesto sobre beneficios",
    "Constitucion con aportacion dineraria",
    "Aportacion no dineraria de vehiculo",
    "Compra con descuento comercial",
    "Rappel sobre compras",
    "Rappel sobre ventas",
    "Anticipo de cliente",
    "Anticipo a proveedor",
    "Reclasificacion de deuda a corto plazo",
    "Deterioro de existencias",
    "Reversion deterioro existencias",
    "Provision insolvencias clientes",
    "Cliente incobrable",
    "Compra intracomunitaria",
    "Venta intracomunitaria",
    "Importacion con aranceles",
    "Exportacion",
    "Transporte de mercancias",
    "Confirming anticipado con comision",
    "Descuento de efectos comerciales",
    "Multa administrativa",
    "Donacion realizada",
    "Subvencion oficial recibida",
    "Imputacion de subvencion",
    "Intereses por descubierto",
    "Comision bancaria",
    "Compra de acciones",
    "Venta de acciones",
    "Cobro de dividendos",
    "Periodificacion de ingresos",
    "Periodificacion de gastos",
    "Regularizacion ingresos y gastos",
    "Cierre contable",
]


def normalizar(texto):
    texto = (texto or "").lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.replace("€", " euros")
    texto = re.sub(r"[^\w\s.,%+-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def contiene(texto, *palabras):
    t = normalizar(texto)
    return all(normalizar(p) in t for p in palabras)


def cualquiera(texto, palabras):
    t = normalizar(texto)
    return any(normalizar(p) in t for p in palabras)


def _numero(txt):
    txt = str(txt or "").strip()
    if "," in txt and "." in txt:
        txt = txt.replace(".", "").replace(",", ".")
    elif re.match(r"^\d{1,3}(?:\.\d{3})+$", txt):
        txt = txt.replace(".", "")
    else:
        txt = txt.replace(",", ".")
    return float(txt)


def extraer_importes(texto):
    t = normalizar(texto)
    valores = []
    for m in re.finditer(r"(?<!\w)(\d+(?:[.,]\d+)?)(?!\w)", t):
        valor = _numero(m.group(1))
        post = t[m.end():m.end() + 20]
        if "%" in post or re.search(r"\b(dia|dias|ano|anos|año|años)\b", post):
            continue
        valores.append(valor)
    return valores


def importe_principal(texto):
    importes = extraer_importes(texto)
    if not importes:
        return None
    return max(importes)


def extraer_porcentaje(texto, defecto=None):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", normalizar(texto))
    if not m:
        return defecto
    return _numero(m.group(1))


def extraer_plazo_dias(texto, defecto=30):
    m = re.search(r"(\d+)\s*dias", normalizar(texto))
    if not m:
        return defecto
    return int(m.group(1))


def fecha_mas_dias(fecha, dias):
    try:
        base = datetime.datetime.strptime(str(fecha), "%Y-%m-%d").date()
    except Exception:
        base = datetime.date.today()
    return str(base + datetime.timedelta(days=int(dias or 0)))


def detectar_tercero(texto):
    original = texto or ""
    patrones = [
        r"\ba\s+([A-Z0-9ÑÁÉÍÓÚÜ.,&\-\s]+?)\s+por\b",
        r"\bde\s+([A-Z0-9ÑÁÉÍÓÚÜ.,&\-\s]+?)\s+por\b",
        r"\ba\s+([A-Z0-9ÑÁÉÍÓÚÜ.,&\-\s]+?)\s+mediante\b",
        r"\bcliente\s+([A-Z0-9ÑÁÉÍÓÚÜ.,&\-\s]+?)\s+por\b",
        r"\bproveedor\s+([A-Z0-9ÑÁÉÍÓÚÜ.,&\-\s]+?)\s+por\b",
    ]
    for patron in patrones:
        m = re.search(patron, original, flags=re.IGNORECASE)
        if m:
            nombre = re.sub(r"\s+", " ", m.group(1)).strip(" .,-")
            basura = [
                "MATERIAS PRIMAS A", "MERCADERIAS A", "PRODUCTOS TERMINADOS A",
                "SERVICIOS DE CONSULTORIA A", "MAQUINARIA A", "MOBILIARIO DE OFICINA A",
            ]
            for item in basura:
                nombre = nombre.upper().replace(item, "").strip()
            return nombre.upper() or "TERCERO NO IDENTIFICADO"
    return "TERCERO NO IDENTIFICADO"


def con_igic(texto, base, igic_defecto):
    t = normalizar(texto)
    if any(p in t for p in ["sin iva", "sin igic", "exenta", "intracomunitaria", "exportacion"]):
        pct = 0.0
    else:
        m = re.search(r"(?:iva|igic)\s*(?:del\s*)?(\d+(?:[.,]\d+)?)", t)
        pct = _numero(m.group(1)) if m else float(igic_defecto or 0)
    cuota = round(float(base) * pct / 100, 2)
    return pct, cuota, round(float(base) + cuota, 2)


def add(lineas, cuenta, movimiento, importe):
    importe = round(float(importe or 0), 2)
    if abs(importe) > 0.004:
        lineas.append((cuenta, movimiento, importe))


def cuadrar(lineas):
    debe = round(sum(i for _, m, i in lineas if m == "debe"), 2)
    haber = round(sum(i for _, m, i in lineas if m == "haber"), 2)
    return debe, haber, round(debe - haber, 2)


def validar_lineas(lineas):
    errores = []
    for cuenta, mov, importe in lineas:
        if not cuenta:
            errores.append("Cuenta vacia")
        if mov not in ("debe", "haber"):
            errores.append(f"Movimiento invalido: {mov}")
        if round(float(importe or 0), 2) <= 0:
            errores.append(f"Importe no positivo en {cuenta}")
    debe, haber, diferencia = cuadrar(lineas)
    if abs(diferencia) > 0.01:
        errores.append(f"Asiento descuadrado: debe {debe} / haber {haber}")
    return errores


def resolver_operacion_avanzada(texto, fecha, igic_defecto=7.0):
    t = normalizar(texto)
    base = importe_principal(texto)
    if base is None and not cualquiera(t, ["regularizacion de ingresos", "cierre contable"]):
        return None

    tercero = detectar_tercero(texto)
    lineas = []
    vencimientos = []
    advertencias = []
    tipo = "operacion_inteligente_avanzada"
    forma_pago = "bancos" if cualquiera(t, ["transferencia", "domiciliacion", "tarjeta", "banco", "cheque"]) else "credito"
    base_imponible = float(base or 0)
    impuesto_pct = 0.0
    cuota = 0.0
    total = base_imponible

    def impuesto():
        nonlocal impuesto_pct, cuota, total
        impuesto_pct, cuota, total = con_igic(texto, base_imponible, igic_defecto)

    def venc(tipo_vto, importe, dias=None):
        if dias is None:
            dias = extraer_plazo_dias(texto, 30)
        vencimientos.append({
            "fecha_vencimiento": fecha_mas_dias(fecha, dias),
            "importe": round(float(importe), 2),
            "tipo": tipo_vto,
            "nombre_tercero": tercero,
        })

    # Ventas y compras frecuentes.
    if contiene(t, "venta", "mercaderias") or contiene(t, "venta", "productos terminados"):
        impuesto()
        tipo = "venta"
        cuenta_ingreso = CUENTAS["ventas"]
        pct = extraer_porcentaje(texto, None)
        if pct and "contado" in t and "resto" in t:
            contado = round(total * pct / 100, 2)
            credito = round(total - contado, 2)
            add(lineas, CUENTAS["caja"], "debe", contado)
            add(lineas, CUENTAS["clientes"], "debe", credito)
            venc("cobro", credito, extraer_plazo_dias(texto, 45))
        elif "letra" in t:
            add(lineas, "431 Clientes, efectos comerciales a cobrar", "debe", total)
            venc("cobro", total, extraer_plazo_dias(texto, 90))
        elif cualquiera(t, ["contado", "transferencia inmediata"]):
            add(lineas, CUENTAS["bancos"] if "transferencia" in t else CUENTAS["caja"], "debe", total)
        else:
            add(lineas, CUENTAS["clientes"], "debe", total)
            if "credito" in t:
                venc("cobro", total)
        add(lineas, cuenta_ingreso, "haber", base_imponible)
        add(lineas, CUENTAS["igic_repercutido"], "haber", cuota)

    elif contiene(t, "servicios de consultoria") or contiene(t, "servicios", "consultoria"):
        impuesto()
        tipo = "venta"
        add(lineas, CUENTAS["bancos"], "debe", total)
        add(lineas, CUENTAS["servicios"], "haber", base_imponible)
        add(lineas, CUENTAS["igic_repercutido"], "haber", cuota)

    elif contiene(t, "venta", "vehiculo"):
        impuesto()
        tipo = "venta_inmovilizado"
        add(lineas, CUENTAS["caja"] if "contado" in t else CUENTAS["bancos"], "debe", total)
        add(lineas, "218 Elementos de transporte", "haber", base_imponible)
        add(lineas, CUENTAS["igic_repercutido"], "haber", cuota)
        advertencias.append("Venta de inmovilizado simplificada: falta coste historico y amortizacion acumulada para calcular resultado real.")

    elif contiene(t, "compra", "materias primas"):
        impuesto()
        tipo = "compra"
        add(lineas, "601 Compras de materias primas", "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, CUENTAS["proveedores"], "haber", total)
        venc("pago", total, extraer_plazo_dias(texto, 30))

    elif contiene(t, "compra", "mercaderias") or contiene(t, "compra", "existencias"):
        descuento = 0.0
        m = re.search(r"descuento comercial del (\d+(?:[.,]\d+)?)", t)
        if m:
            descuento = round(base_imponible * _numero(m.group(1)) / 100, 2)
            base_imponible = round(base_imponible - descuento, 2)
        impuesto()
        tipo = "compra"
        add(lineas, CUENTAS["compras"], "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, CUENTAS["caja"] if "contado" in t else CUENTAS["proveedores"], "haber", total)

    elif contiene(t, "adquisicion", "maquinaria") or contiene(t, "compra", "maquinaria"):
        impuesto()
        tipo = "compra_inmovilizado"
        pct = extraer_porcentaje(texto, 0) or 0
        contado = round(total * pct / 100, 2) if pct else (total if "contado" in t else 0)
        financiado = round(total - contado, 2)
        add(lineas, "213 Maquinaria", "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, CUENTAS["bancos"] if "transferencia" in t else CUENTAS["caja"], "haber", contado)
        add(lineas, "173 Proveedores de inmovilizado a largo plazo", "haber", financiado)

    elif contiene(t, "mobiliario"):
        impuesto()
        tipo = "compra_inmovilizado"
        add(lineas, "216 Mobiliario", "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, CUENTAS["caja"] if "contado" in t else CUENTAS["bancos"], "haber", total)

    elif contiene(t, "software"):
        impuesto()
        tipo = "compra_inmovilizado"
        add(lineas, "206 Aplicaciones informaticas", "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, CUENTAS["bancos"], "haber", total)

    # Gastos, impuestos y tesoreria.
    elif contiene(t, "alquiler"):
        impuesto()
        tipo = "gasto"
        add(lineas, "621 Arrendamientos y canones", "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, CUENTAS["bancos"], "haber", total)
    elif contiene(t, "seguro anual") or contiene(t, "contratacion de seguro"):
        tipo = "gasto"
        add(lineas, "625 Primas de seguros", "debe", base_imponible)
        add(lineas, CUENTAS["caja"], "haber", base_imponible)
    elif cualquiera(t, ["suministros electricos", "electricos", "electricidad"]):
        impuesto()
        tipo = "gasto"
        add(lineas, "628 Suministros", "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, CUENTAS["proveedores"], "haber", total)
        venc("pago", total)
    elif contiene(t, "publicidad"):
        impuesto()
        tipo = "gasto"
        add(lineas, "627 Publicidad, propaganda y relaciones publicas", "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, CUENTAS["bancos"], "haber", total)
    elif contiene(t, "transporte"):
        impuesto()
        tipo = "gasto"
        add(lineas, "624 Transportes", "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, CUENTAS["bancos"], "haber", total)
    elif contiene(t, "servicios profesionales") or contiene(t, "asesoria"):
        impuesto()
        tipo = "gasto"
        retencion = round(base_imponible * 0.15, 2)
        add(lineas, "623 Servicios de profesionales independientes", "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, "4751 Hacienda Publica, acreedora por retenciones", "haber", retencion)
        add(lineas, CUENTAS["bancos"], "haber", round(total - retencion, 2))
        advertencias.append("Retencion IRPF aplicada por defecto al 15%.")
    elif contiene(t, "multa"):
        tipo = "gasto"
        add(lineas, "678 Gastos excepcionales", "debe", base_imponible)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)
    elif contiene(t, "donacion"):
        tipo = "gasto"
        add(lineas, "678 Gastos excepcionales", "debe", base_imponible)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)
    elif contiene(t, "comision bancaria") or contiene(t, "mantenimiento de cuenta"):
        tipo = "gasto_bancario"
        add(lineas, "626 Servicios bancarios y similares", "debe", base_imponible)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)
    elif contiene(t, "intereses por descubierto") or contiene(t, "intereses del prestamo") or contiene(t, "pago de intereses"):
        tipo = "gasto_financiero"
        add(lineas, "662 Intereses de deudas", "debe", base_imponible)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)

    # Cobros, pagos y financiacion.
    elif contiene(t, "cobro de cliente"):
        tipo = "cobro"
        add(lineas, CUENTAS["bancos"], "debe", base_imponible)
        add(lineas, CUENTAS["clientes"], "haber", base_imponible)
    elif contiene(t, "pago a proveedor"):
        tipo = "pago"
        add(lineas, CUENTAS["proveedores"], "debe", base_imponible)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)
    elif contiene(t, "prestamo bancario") or contiene(t, "concesion de un prestamo"):
        tipo = "financiacion"
        add(lineas, CUENTAS["bancos"], "debe", base_imponible)
        add(lineas, "170 Deudas a largo plazo con entidades de credito", "haber", base_imponible)
    elif contiene(t, "cuota de prestamo"):
        tipo = "financiacion"
        intereses = 400.0 if "intereses" in t else 0.0
        capital = round(base_imponible - intereses, 2)
        if capital <= 0:
            capital = base_imponible
            intereses = 0.0
            advertencias.append("No se ha separado capital/intereses porque falta detalle.")
        add(lineas, "170 Deudas a largo plazo con entidades de credito", "debe", capital)
        add(lineas, "662 Intereses de deudas", "debe", intereses)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)

    # Devoluciones, rappels y anticipos.
    elif contiene(t, "devolucion de mercaderias a proveedor") or contiene(t, "devolucion a proveedor"):
        impuesto()
        tipo = "abono_compra"
        add(lineas, CUENTAS["proveedores"], "debe", total)
        add(lineas, "608 Devoluciones de compras y operaciones similares", "haber", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "haber", cuota)
    elif contiene(t, "devolucion de cliente"):
        impuesto()
        tipo = "abono_venta"
        add(lineas, "708 Devoluciones de ventas y operaciones similares", "debe", base_imponible)
        add(lineas, CUENTAS["igic_repercutido"], "debe", cuota)
        add(lineas, CUENTAS["clientes"], "haber", total)
    elif contiene(t, "rappel sobre compras"):
        impuesto()
        tipo = "rappel_compra"
        add(lineas, CUENTAS["proveedores"], "debe", total)
        add(lineas, "609 Rappels por compras", "haber", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "haber", cuota)
    elif contiene(t, "rappel sobre ventas"):
        impuesto()
        tipo = "rappel_venta"
        add(lineas, "709 Rappels sobre ventas", "debe", base_imponible)
        add(lineas, CUENTAS["igic_repercutido"], "debe", cuota)
        add(lineas, CUENTAS["clientes"], "haber", total)
    elif contiene(t, "anticipo recibido de cliente"):
        impuesto()
        tipo = "anticipo_cliente"
        add(lineas, CUENTAS["bancos"], "debe", total)
        add(lineas, "438 Anticipos de clientes", "haber", base_imponible)
        add(lineas, CUENTAS["igic_repercutido"], "haber", cuota)
    elif contiene(t, "anticipo entregado a proveedor"):
        impuesto()
        tipo = "anticipo_proveedor"
        add(lineas, "407 Anticipos a proveedores", "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", cuota)
        add(lineas, CUENTAS["bancos"], "haber", total)

    # Inmovilizado, existencias y deterioros.
    elif contiene(t, "amortizacion anual de maquinaria") or contiene(t, "amortizacion de maquinaria"):
        tipo = "amortizacion"
        add(lineas, "681 Amortizacion del inmovilizado material", "debe", base_imponible)
        add(lineas, "2813 Amortizacion acumulada de maquinaria", "haber", base_imponible)
    elif contiene(t, "amortizacion del mobiliario"):
        tipo = "amortizacion"
        add(lineas, "681 Amortizacion del inmovilizado material", "debe", base_imponible)
        add(lineas, "2816 Amortizacion acumulada de mobiliario", "haber", base_imponible)
    elif contiene(t, "regularizacion de existencias finales"):
        tipo = "regularizacion_existencias"
        add(lineas, "300 Mercaderias", "debe", base_imponible)
        add(lineas, "610 Variacion de existencias de mercaderias", "haber", base_imponible)
        advertencias.append("Regularizacion simplificada: no se ha dado de baja existencia inicial.")
    elif contiene(t, "deterioro de valor de existencias"):
        tipo = "deterioro"
        add(lineas, "693 Perdidas por deterioro de existencias", "debe", base_imponible)
        add(lineas, "390 Deterioro de valor de mercaderias", "haber", base_imponible)
    elif contiene(t, "reversion de deterioro"):
        tipo = "reversion_deterioro"
        add(lineas, "390 Deterioro de valor de mercaderias", "debe", base_imponible)
        add(lineas, "793 Reversion del deterioro de existencias", "haber", base_imponible)
    elif contiene(t, "provision por insolvencias"):
        tipo = "deterioro_clientes"
        add(lineas, "694 Perdidas por deterioro de creditos comerciales", "debe", base_imponible)
        add(lineas, "490 Deterioro de valor de creditos por operaciones comerciales", "haber", base_imponible)
    elif contiene(t, "fallido de cliente"):
        tipo = "cliente_incobrable"
        add(lineas, "650 Perdidas de creditos comerciales incobrables", "debe", base_imponible)
        add(lineas, CUENTAS["clientes"], "haber", base_imponible)

    # Operaciones exteriores.
    elif contiene(t, "compra intracomunitaria"):
        tipo = "compra_intracomunitaria"
        iva = round(base_imponible * float(igic_defecto or 0) / 100, 2)
        add(lineas, CUENTAS["compras"], "debe", base_imponible)
        add(lineas, CUENTAS["igic_soportado"], "debe", iva)
        add(lineas, CUENTAS["igic_repercutido"], "haber", iva)
        add(lineas, CUENTAS["proveedores"], "haber", base_imponible)
    elif contiene(t, "venta intracomunitaria") or contiene(t, "exportacion"):
        tipo = "venta_exenta"
        add(lineas, CUENTAS["clientes"], "debe", base_imponible)
        add(lineas, CUENTAS["ventas"], "haber", base_imponible)
    elif contiene(t, "importacion de mercancias"):
        tipo = "importacion"
        arancel = 300.0 if "aranceles" in t else 0.0
        add(lineas, CUENTAS["compras"], "debe", round(base_imponible + arancel, 2))
        add(lineas, CUENTAS["bancos"], "haber", round(base_imponible + arancel, 2))

    # Patrimonio, subvenciones, inversiones y periodificaciones.
    elif contiene(t, "constitucion de la empresa"):
        tipo = "capital"
        add(lineas, CUENTAS["bancos"], "debe", base_imponible)
        add(lineas, "100 Capital social", "haber", base_imponible)
    elif contiene(t, "aportacion no dineraria"):
        tipo = "capital"
        add(lineas, "218 Elementos de transporte", "debe", base_imponible)
        add(lineas, "100 Capital social", "haber", base_imponible)
    elif contiene(t, "reclasificacion de deuda"):
        tipo = "reclasificacion_deuda"
        add(lineas, "170 Deudas a largo plazo con entidades de credito", "debe", base_imponible)
        add(lineas, "520 Deudas a corto plazo con entidades de credito", "haber", base_imponible)
    elif contiene(t, "subvencion oficial"):
        tipo = "subvencion"
        add(lineas, CUENTAS["bancos"], "debe", base_imponible)
        add(lineas, "130 Subvenciones oficiales de capital", "haber", base_imponible)
    elif contiene(t, "imputacion a resultados de subvencion"):
        tipo = "subvencion"
        add(lineas, "130 Subvenciones oficiales de capital", "debe", base_imponible)
        add(lineas, "746 Subvenciones transferidas al resultado", "haber", base_imponible)
    elif contiene(t, "compra de acciones"):
        tipo = "inversion_financiera"
        add(lineas, "250 Inversiones financieras a largo plazo en instrumentos de patrimonio", "debe", base_imponible)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)
    elif contiene(t, "venta de acciones"):
        tipo = "inversion_financiera"
        add(lineas, CUENTAS["bancos"], "debe", base_imponible)
        add(lineas, "250 Inversiones financieras a largo plazo en instrumentos de patrimonio", "haber", 5000.0)
        add(lineas, "766 Beneficios en participaciones y valores", "haber", round(base_imponible - 5000.0, 2))
        advertencias.append("Coste de acciones asumido en 5.000 EUR por el enunciado anterior.")
    elif contiene(t, "cobro de dividendos"):
        tipo = "ingreso_financiero"
        add(lineas, CUENTAS["bancos"], "debe", base_imponible)
        add(lineas, "760 Ingresos de participaciones en instrumentos de patrimonio", "haber", base_imponible)
    elif contiene(t, "periodificacion de ingresos"):
        tipo = "periodificacion"
        add(lineas, "485 Ingresos anticipados", "debe", base_imponible)
        add(lineas, "705 Prestaciones de servicios", "haber", base_imponible)
    elif contiene(t, "periodificacion de gastos"):
        tipo = "periodificacion"
        add(lineas, "480 Gastos anticipados", "debe", base_imponible)
        add(lineas, "629 Otros servicios", "haber", base_imponible)
    elif contiene(t, "liquidacion trimestral"):
        tipo = "liquidacion_impuesto"
        add(lineas, "4750 Hacienda Publica, acreedora por IVA/IGIC", "debe", base_imponible)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)
    elif contiene(t, "impuesto sobre beneficios"):
        tipo = "impuesto_sociedades"
        add(lineas, "630 Impuesto sobre beneficios", "debe", base_imponible)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)
    elif contiene(t, "confirming anticipado"):
        tipo = "financiacion_cobro"
        add(lineas, CUENTAS["bancos"], "debe", base_imponible)
        add(lineas, "626 Servicios bancarios y similares", "debe", 150.0)
        add(lineas, CUENTAS["clientes"], "haber", round(base_imponible + 150.0, 2))
        advertencias.append("Se interpreta el importe como efectivo recibido neto; comision 150 EUR.")
    elif contiene(t, "descuento de efectos"):
        tipo = "financiacion_cobro"
        gastos = 80.0
        add(lineas, CUENTAS["bancos"], "debe", round(base_imponible - gastos, 2))
        add(lineas, "665 Intereses por descuento de efectos", "debe", gastos)
        add(lineas, "431 Clientes, efectos comerciales a cobrar", "haber", base_imponible)
    elif contiene(t, "nominas") or contiene(t, "nomina"):
        tipo = "nomina"
        add(lineas, "640 Sueldos y salarios", "debe", base_imponible)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)
        advertencias.append("Nomina simplificada: faltan bruto, IRPF, Seguridad Social trabajador y empresa.")
    elif contiene(t, "seguros sociales"):
        tipo = "seguridad_social"
        add(lineas, "476 Organismos de la Seguridad Social acreedores", "debe", base_imponible)
        add(lineas, CUENTAS["bancos"], "haber", base_imponible)
    elif contiene(t, "regularizacion de ingresos y gastos") or contiene(t, "cierre contable"):
        return {
            "ok": False,
            "mensaje": "Esta operacion necesita saldos reales de todas las cuentas para generarse sin inventar datos.",
            "tipo": "cierre_contable",
            "requiere_saldos": True,
        }
    else:
        return None

    errores = validar_lineas(lineas)
    if errores:
        return {"ok": False, "mensaje": "No se pudo construir un asiento fiable", "errores": errores, "lineas": lineas}

    return {
        "ok": True,
        "tipo": tipo,
        "fecha": fecha,
        "concepto": texto,
        "tercero": tercero,
        "forma_pago": forma_pago,
        "base": round(base_imponible, 2),
        "impuesto_pct": impuesto_pct,
        "cuota_impuesto": cuota,
        "total": total,
        "lineas": lineas,
        "vencimientos": vencimientos,
        "advertencias": advertencias,
    }


def existe_operacion_avanzada(fecha, concepto, total, tipo):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id
            FROM operaciones
            WHERE fecha_operacion = %s
              AND concepto = %s
              AND ROUND(total::numeric, 2) = ROUND(%s::numeric, 2)
              AND tipo_operacion = %s
            LIMIT 1
            """,
            (fecha, concepto, float(total or 0), tipo),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def registrar_operacion_avanzada(texto, fecha, igic_defecto=7.0):
    resuelta = resolver_operacion_avanzada(texto, fecha, igic_defecto)
    if not resuelta:
        return None
    if not resuelta.get("ok"):
        return resuelta

    empresa_id = obtener_empresa_id_activa()
    if existe_operacion_avanzada(fecha, texto, resuelta["total"], resuelta["tipo"]):
        return {"ok": False, "mensaje": "Ya existe una operacion muy similar registrada. Revisa antes de duplicar."}

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO asientos (fecha, concepto, tipo_operacion)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (fecha, texto, resuelta["tipo"]),
        )
        asiento_id = cursor.fetchone()[0]

        for cuenta, movimiento, importe in resuelta["lineas"]:
            cursor.execute(
                """
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (%s, %s, %s, %s)
                """,
                (asiento_id, cuenta, movimiento, float(importe)),
            )

        cursor.execute(
            """
            INSERT INTO operaciones (
                empresa_id, tipo_operacion, fecha_operacion, concepto,
                nombre_tercero, numero_factura, forma_pago,
                base_imponible, impuesto_pct, cuota_impuesto, total
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                empresa_id,
                resuelta["tipo"],
                fecha,
                texto,
                resuelta["tercero"],
                None,
                resuelta["forma_pago"],
                resuelta["base"],
                resuelta["impuesto_pct"],
                resuelta["cuota_impuesto"],
                resuelta["total"],
            ),
        )
        operacion_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO operaciones_asientos (operacion_id, asiento_id, empresa_id)
            VALUES (%s, %s, %s)
            """,
            (operacion_id, asiento_id, empresa_id),
        )

        for vencimiento in resuelta.get("vencimientos", []):
            cursor.execute(
                """
                INSERT INTO vencimientos (
                    empresa_id, factura_id, fecha_vencimiento, importe,
                    importe_pendiente, estado, tipo, nombre_tercero
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    empresa_id,
                    operacion_id,
                    vencimiento["fecha_vencimiento"],
                    vencimiento["importe"],
                    vencimiento["importe"],
                    "pendiente",
                    vencimiento["tipo"],
                    vencimiento["nombre_tercero"],
                ),
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": f"Error al registrar operacion avanzada: {e}"}
    finally:
        conn.close()

    return {
        "ok": True,
        "tipo": resuelta["tipo"],
        "operacion_id": operacion_id,
        "asiento_id": asiento_id,
        "tercero": resuelta["tercero"],
        "forma_pago": resuelta["forma_pago"],
        "base": resuelta["base"],
        "igic_pct": resuelta["impuesto_pct"],
        "igic": resuelta["cuota_impuesto"],
        "total": resuelta["total"],
        "lineas": resuelta["lineas"],
        "vencimientos": resuelta.get("vencimientos", []),
        "advertencias": resuelta.get("advertencias", []),
        "motor": "operaciones_avanzadas_60",
    }
