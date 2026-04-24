from config_empresa import CONFIG_EMPRESA


def resolver_cuenta_catalogo(codigo_cuenta, contexto):
    if codigo_cuenta == "cuenta_compra_mercaderia":
        return CONFIG_EMPRESA["cuenta_compra_mercaderia"]

    if codigo_cuenta == "cuenta_igic_soportado":
        return CONFIG_EMPRESA["cuenta_igic_soportado"]

    if codigo_cuenta == "cuenta_igic_repercutido":
        return CONFIG_EMPRESA["cuenta_igic_repercutido"]

    if codigo_cuenta == "cuenta_proveedores":
        return CONFIG_EMPRESA["cuenta_proveedores"]

    if codigo_cuenta == "cuenta_clientes":
        return CONFIG_EMPRESA["cuenta_clientes"]

    if codigo_cuenta == "cuenta_ingreso_venta":
        return CONFIG_EMPRESA["cuenta_ingreso_venta"]

    if codigo_cuenta == "cuenta_ingreso_servicio":
        return CONFIG_EMPRESA["cuenta_ingreso_servicio"]

    if codigo_cuenta == "cuenta_ingreso_alquiler":
        return CONFIG_EMPRESA["cuenta_ingreso_alquiler"]

    if codigo_cuenta == "cuenta_bancos":
        return CONFIG_EMPRESA["cuenta_bancos"]

    if codigo_cuenta == "cuenta_caja":
        return CONFIG_EMPRESA["cuenta_caja"]

    if codigo_cuenta == "cuenta_bancos_o_caja":
        forma_pago = (contexto.get("forma_pago") or "").lower()
        if forma_pago == "contado":
            return CONFIG_EMPRESA["cuenta_caja"]
        return CONFIG_EMPRESA["cuenta_bancos"]

    if codigo_cuenta == "cuenta_proveedores_o_bancos":
        forma_pago = (contexto.get("forma_pago") or "").lower()
        if forma_pago == "contado":
            return CONFIG_EMPRESA["cuenta_caja"]
        if forma_pago == "transferencia":
            return CONFIG_EMPRESA["cuenta_bancos"]
        return CONFIG_EMPRESA["cuenta_proveedores"]

    if codigo_cuenta == "cuenta_clientes_o_bancos":
        forma_pago = (contexto.get("forma_pago") or "").lower()
        if forma_pago == "contado":
            return CONFIG_EMPRESA["cuenta_caja"]
        if forma_pago == "transferencia":
            return CONFIG_EMPRESA["cuenta_bancos"]
        return CONFIG_EMPRESA["cuenta_clientes"]

    if codigo_cuenta == "cuenta_inmovilizado":
        return contexto.get("cuenta_activo", "217 Equipos para procesos de información")

    if codigo_cuenta == "cuenta_gasto":
        return contexto.get("cuenta_gasto", "629 Otros servicios")

    if codigo_cuenta == "cuenta_personalizada_base":
        return contexto.get("cuenta_base", "629 Otros servicios")

    if codigo_cuenta == "cuenta_pasivo":
        return contexto.get("cuenta_pasivo", "170 Deudas a largo plazo con entidades de crédito")

    return codigo_cuenta

    if codigo_cuenta == "cuenta_anticipo_proveedor":
        return "407 Anticipos a proveedores"

    if codigo_cuenta == "cuenta_anticipo_cliente":
        return "438 Anticipos de clientes"

    if codigo_cuenta == "cuenta_fianza_constituida":
        return "260 Fianzas constituidas a largo plazo"

    if codigo_cuenta == "cuenta_fianza_recibida":
        return "180 Fianzas recibidas a largo plazo"

    if codigo_cuenta == "cuenta_prestamo_lp":
        return "170 Deudas a largo plazo con entidades de crédito"

    if codigo_cuenta == "cuenta_intereses_deudas":
        return "662 Intereses de deudas"



def resolver_formula_importe(formula, contexto):
    if formula == "base":
        return float(contexto.get("base", 0) or 0)

    if formula == "impuesto":
        return float(contexto.get("impuesto", 0) or 0)

    if formula == "total":
        return float(contexto.get("total", 0) or 0)

    if formula == "saldo":
        return float(contexto.get("saldo", 0) or 0)

    return 0.0


def generar_lineas_desde_catalogo(definicion, contexto):
    if not definicion:
        return []

    plantilla = definicion.get("plantilla", {})
    lineas_plantilla = plantilla.get("lineas", [])

    lineas = []

    for linea in lineas_plantilla:
        lado = linea.get("lado")
        cuenta_raw = linea.get("cuenta")
        formula = linea.get("formula")

        cuenta = resolver_cuenta_catalogo(cuenta_raw, contexto)
        importe = resolver_formula_importe(formula, contexto)

        if round(float(importe or 0), 2) == 0:
            continue

        lineas.append((cuenta, lado, float(importe)))

    return lineas