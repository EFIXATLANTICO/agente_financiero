import re
from db_context import get_connection


def extraer_texto_pdf_simple(pdf_path):
    import PyPDF2

    texto_total = ""

    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            texto = page.extract_text() or ""
            texto_total += "\n" + texto

    return texto_total


def limpiar_numero_es(texto):
    texto = texto.replace(".", "").replace(",", ".").strip()
    return float(texto)


def detectar_importe_linea(texto, etiqueta):
    for linea in texto.splitlines():
        if etiqueta.lower() in linea.lower():
            numeros = re.findall(r"-?\d[\d\.]*,\d{2}", linea)
            if numeros:
                return limpiar_numero_es(numeros[-1])
    return 0.0


def leer_balance_situacion_pdf(pdf_path):
    texto = extraer_texto_pdf_simple(pdf_path)

    print("----- TEXTO PDF -----")
    print(texto)
    print("---------------------")

    datos = {
        # ACTIVO
        "inmovilizado_intangible": detectar_importe_linea(texto, "Inmovilizado intangible"),
        "inmovilizado_material": detectar_importe_linea(texto, "Inmovilizado material"),
        "inversiones_financieras_lp": detectar_importe_linea(texto, "Inversiones financieras a largo plazo"),
        "existencias": detectar_importe_linea(texto, "Existencias"),
        "clientes": detectar_importe_linea(texto, "Clientes ventas y prestación de servicios"),
        "otros_deudores": detectar_importe_linea(texto, "Otros deudores"),
        "inversiones_financieras_cp": detectar_importe_linea(texto, "Inversiones financieras a corto plazo"),
        "efectivo": detectar_importe_linea(texto, "Efectivo y otros activos líquidos"),

        # PATRIMONIO NETO
        "capital": detectar_importe_linea(texto, "Capital"),
        "reservas": detectar_importe_linea(texto, "Reservas"),
        "resultados_anteriores": detectar_importe_linea(texto, "Resultados de ejercicios anteriores"),
        "resultado_ejercicio": detectar_importe_linea(texto, "Resultado del ejercicio"),
        "subvenciones": detectar_importe_linea(texto, "Subvenciones"),

        # PASIVO
        "deuda_leasing_lp": detectar_importe_linea(texto, "arrendamiento financiero"),
        "otras_deudas_lp": detectar_importe_linea(texto, "Otras deudas a largo plazo"),
        "deudas_credito_cp": detectar_importe_linea(texto, "Deudas con entidades de credito"),
        "otras_deudas_cp": detectar_importe_linea(texto, "Otras deudas a corto plazo"),
        "proveedores": detectar_importe_linea(texto, "Proveedores"),
        "otros_acreedores": detectar_importe_linea(texto, "Otros acreedores"),
    }

    return datos

    datos = {
        # ACTIVO
        "inmovilizado_intangible": detectar_importe_linea(texto, "I. Inmovilizado intangible"),
        "inmovilizado_material": detectar_importe_linea(texto, "II. Inmovilizado material"),
        "inversiones_financieras_lp": detectar_importe_linea(texto, "V. Inversiones financieras a largo plazo"),
        "existencias": detectar_importe_linea(texto, "II. Existencias"),
        "clientes": detectar_importe_linea(texto, "1. Clientes ventas y prestación de servicios"),
        "otros_deudores": detectar_importe_linea(texto, "3. Otros deudores"),
        "inversiones_financieras_cp": detectar_importe_linea(texto, "V. Inversiones financieras a corto plazo"),
        "efectivo": detectar_importe_linea(texto, "Efectivo y otros activos líquidos"),

        # PATRIMONIO NETO
        "capital": detectar_importe_linea(texto, "1. Capital escriturado"),
        "reservas": detectar_importe_linea(texto, "2. Otras Reservas"),
        "resultados_anteriores": detectar_importe_linea(texto, "V. Resultados de ejercicios anteriores"),
        "resultado_ejercicio": detectar_importe_linea(texto, "VII. Resultado del ejercicio"),
        "subvenciones": detectar_importe_linea(texto, "A-3) Subvenciones, donaciones y legados recibidos"),

        # PASIVO
        "deuda_leasing_lp": detectar_importe_linea(texto, "2. Acreedores por arrendamiento financiero"),
        "otras_deudas_lp": detectar_importe_linea(texto, "3. Otras deudas a largo plazo"),
        "deudas_credito_cp": detectar_importe_linea(texto, "1. Deudas con entidades de credito"),
        "otras_deudas_cp": detectar_importe_linea(texto, "3. Otras deudas a corto plazo"),
        "proveedores": detectar_importe_linea(texto, "b) Proveedores a corto plazo"),
        "otros_acreedores": detectar_importe_linea(texto, "2. Otros acreedores"),
    }

    # Totales por si quieres revisar
    datos["total_activo"] = detectar_importe_linea(texto, "T O T A L A C T I V O")
    datos["total_pn_pasivo"] = detectar_importe_linea(texto, "T O T A L PATRIMONIO NETO Y PASIVO")

    return datos


def generar_lineas_asiento_apertura(datos):
    """
    Genera las líneas del asiento de apertura.
    Regla:
    - activo positivo -> debe
    - patrimonio neto y pasivo -> haber
    - efectivo negativo -> se reclasifica a deuda bancaria CP en haber
    """
    lineas = []

    # ACTIVO -> DEBE
    if datos["inmovilizado_intangible"] > 0:
        lineas.append(("200 Inmovilizado intangible", "debe", datos["inmovilizado_intangible"]))

    if datos["inmovilizado_material"] > 0:
        lineas.append(("213 Inmovilizado material", "debe", datos["inmovilizado_material"]))

    if datos["inversiones_financieras_lp"] > 0:
        lineas.append(("250 Inversiones financieras a largo plazo", "debe", datos["inversiones_financieras_lp"]))

    if datos["existencias"] > 0:
        lineas.append(("300 Existencias", "debe", datos["existencias"]))

    if datos["clientes"] > 0:
        lineas.append(("430 Clientes", "debe", datos["clientes"]))

    if datos["otros_deudores"] > 0:
        lineas.append(("440 Deudores varios", "debe", datos["otros_deudores"]))

    if datos["inversiones_financieras_cp"] > 0:
        lineas.append(("540 Inversiones financieras a corto plazo", "debe", datos["inversiones_financieras_cp"]))

    # Efectivo: si es positivo va a debe; si es negativo se reclasifica a haber
    if datos["efectivo"] > 0:
        lineas.append(("572 Bancos", "debe", datos["efectivo"]))

    # PATRIMONIO NETO + PASIVO -> HABER
    if datos["capital"] > 0:
        lineas.append(("100 Capital social", "haber", datos["capital"]))

    if datos["reservas"] > 0:
        lineas.append(("113 Reservas voluntarias", "haber", datos["reservas"]))

    if datos["resultados_anteriores"] > 0:
        lineas.append(("120 Remanente", "haber", datos["resultados_anteriores"]))

    if datos["resultado_ejercicio"] > 0:
        lineas.append(("129 Resultado del ejercicio", "haber", datos["resultado_ejercicio"]))

    if datos["subvenciones"] > 0:
        lineas.append(("130 Subvenciones oficiales de capital", "haber", datos["subvenciones"]))

    if datos["deuda_leasing_lp"] > 0:
        lineas.append(("174 Acreedores por arrendamiento financiero a largo plazo", "haber", datos["deuda_leasing_lp"]))

    if datos["otras_deudas_lp"] > 0:
        lineas.append(("171 Deudas a largo plazo", "haber", datos["otras_deudas_lp"]))

    if datos["deudas_credito_cp"] > 0:
        lineas.append(("520 Deudas a corto plazo con entidades de crédito", "haber", datos["deudas_credito_cp"]))

    if datos["otras_deudas_cp"] > 0:
        lineas.append(("521 Otras deudas a corto plazo", "haber", datos["otras_deudas_cp"]))

    if datos["proveedores"] > 0:
        lineas.append(("400 Proveedores", "haber", datos["proveedores"]))

    if datos["otros_acreedores"] > 0:
        lineas.append(("410 Acreedores varios", "haber", datos["otros_acreedores"]))

    # Si bancos viene negativo, lo tratamos como deuda bancaria CP
    if datos["efectivo"] < 0:
        lineas.append(("520 Deudas a corto plazo con entidades de crédito", "haber", abs(datos["efectivo"])))

    return lineas


def validar_asiento(lineas):
    debe = round(sum(importe for _, mov, importe in lineas if mov == "debe"), 2)
    haber = round(sum(importe for _, mov, importe in lineas if mov == "haber"), 2)

    return {
        "debe": debe,
        "haber": haber,
        "cuadra": debe == haber
    }


def registrar_asiento_apertura(fecha, concepto, lineas):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO asientos (fecha, concepto, tipo_operacion)
        VALUES (?, ?, ?)
    """, (fecha, concepto, "asiento_apertura"))

    asiento_id = cursor.lastrowid

    for cuenta, movimiento, importe in lineas:
        cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (?, ?, ?, ?)
        """, (asiento_id, cuenta, movimiento, float(importe)))

    conn.commit()
    conn.close()

    return asiento_id


def procesar_balance_pdf_a_apertura(pdf_path, fecha_apertura):
    datos = leer_balance_situacion_pdf(pdf_path)
    lineas = generar_lineas_asiento_apertura(datos)
    validacion = validar_asiento(lineas)

    return {
        "datos_balance": datos,
        "lineas": lineas,
        "validacion": validacion,
        "fecha_apertura": fecha_apertura
    }


def registrar_balance_pdf_como_apertura(pdf_path, fecha_apertura):
    resultado = procesar_balance_pdf_a_apertura(pdf_path, fecha_apertura)

    if not resultado["validacion"]["cuadra"]:
        return {
            "ok": False,
            "mensaje": "El asiento de apertura no cuadra",
            "detalle": resultado
        }

    asiento_id = registrar_asiento_apertura(
        fecha=fecha_apertura,
        concepto="Asiento de apertura generado desde PDF",
        lineas=resultado["lineas"]
    )

    return {
        "ok": True,
        "asiento_id": asiento_id,
        "lineas": resultado["lineas"],
        "validacion": resultado["validacion"],
        "datos_balance": resultado["datos_balance"]
    }