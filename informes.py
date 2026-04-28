import pandas as pd
from db_context import get_connection
from pgc import obtener_cuenta_pgc, normalizar_cuenta

import re


def obtener_grupo_cuenta(cuenta):
    cuenta = str(cuenta or "").strip()

    match = re.match(r"^(\d{3})", cuenta)
    if match:
        return match.group(1)

    match = re.search(r"(\d{3})", cuenta)
    if match:
        return match.group(1)

    return cuenta


def nombre_grupo_cuenta(grupo):
    mapa = {
        # Grupo 1
        "100": "100 Capital social",
        "112": "112 Reserva legal",
        "113": "113 Reservas voluntarias",
        "118": "118 Aportaciones de socios o propietarios",
        "129": "129 Resultado del ejercicio",
        "170": "170 Deudas a largo plazo con entidades de credito",
        "173": "173 Proveedores de inmovilizado a largo plazo",
        "180": "180 Fianzas recibidas a largo plazo",

        # Grupo 2
        "200": "200 Investigacion",
        "203": "203 Propiedad industrial",
        "206": "206 Aplicaciones informaticas",
        "210": "210 Terrenos y bienes naturales",
        "211": "211 Construcciones",
        "212": "212 Instalaciones tecnicas",
        "213": "213 Maquinaria",
        "214": "214 Utillaje",
        "215": "215 Otras instalaciones",
        "216": "216 Mobiliario",
        "217": "217 Equipos para procesos de informacion",
        "218": "218 Elementos de transporte",
        "219": "219 Otro inmovilizado material",
        "260": "260 Fianzas constituidas a largo plazo",

        # Grupo 3
        "300": "300 Mercaderias",
        "310": "310 Materias primas",
        "320": "320 Elementos y conjuntos incorporables",

        # Grupo 4
        "400": "400 Proveedores",
        "401": "401 Proveedores, efectos comerciales a pagar",
        "407": "407 Anticipos a proveedores",
        "410": "410 Acreedores por prestaciones de servicios",
        "430": "430 Clientes",
        "431": "431 Clientes, efectos comerciales a cobrar",
        "438": "438 Anticipos de clientes",
        "440": "440 Deudores",
        "460": "460 Anticipos de remuneraciones",
        "465": "465 Remuneraciones pendientes de pago",
        "470": "470 Hacienda Publica, deudora por diversos conceptos",
        "472": "472 Hacienda Publica, IGIC soportado",
        "475": "475 Hacienda Publica, acreedora por conceptos fiscales",
        "476": "476 Organismos de la Seguridad Social, acreedores",
        "477": "477 Hacienda Publica, IGIC repercutido",

        # Grupo 5
        "520": "520 Deudas a corto plazo con entidades de credito",
        "523": "523 Proveedores de inmovilizado a corto plazo",
        "551": "551 Cuenta corriente con socios y administradores",
        "555": "555 Partidas pendientes de aplicacion",
        "570": "570 Caja",
        "572": "572 Bancos e instituciones de credito c/c vista, euros",

        # Grupo 6
        "600": "600 Compras de mercaderias",
        "601": "601 Compras de materias primas",
        "606": "606 Descuentos sobre compras por pronto pago",
        "607": "607 Trabajos realizados por otras empresas",
        "621": "621 Arrendamientos y canones",
        "622": "622 Reparaciones y conservacion",
        "623": "623 Servicios de profesionales independientes",
        "624": "624 Transportes",
        "625": "625 Primas de seguros",
        "626": "626 Servicios bancarios y similares",
        "627": "627 Publicidad, propaganda y relaciones publicas",
        "628": "628 Suministros",
        "629": "629 Otros servicios",
        "631": "631 Otros tributos",
        "640": "640 Sueldos y salarios",
        "642": "642 Seguridad Social a cargo de la empresa",
        "649": "649 Otros gastos sociales",
        "662": "662 Intereses de deudas",
        "669": "669 Otros gastos financieros",
        "678": "678 Gastos excepcionales",

        # Grupo 7
        "700": "700 Ventas de mercaderias",
        "705": "705 Prestaciones de servicios",
        "706": "706 Descuentos sobre ventas por pronto pago",
        "708": "708 Devoluciones de ventas y operaciones similares",
        "752": "752 Ingresos por arrendamientos",
        "759": "759 Ingresos por servicios diversos",
        "769": "769 Otros ingresos financieros",
        "778": "778 Ingresos excepcionales",
    }
    return mapa.get(grupo, grupo)

COLUMNAS_BALANCE = ["Cuenta", "Nombre", "Debe", "Haber", "Saldo"]
COLUMNAS_MAYOR = ["Fecha", "Concepto", "Cuenta", "Movimiento", "Importe", "Saldo acumulado"]
COLUMNAS_PYG_DETALLE = ["Cuenta", "Nombre", "Tipo", "Importe"]
COLUMNAS_BALANCE_DETALLE = ["Cuenta", "Nombre", "Bloque PGC", "Importe"]
COLUMNAS_BALANCE_RESUMEN = ["Masa patrimonial", "Importe"]


def _df_vacio(columnas):
    return pd.DataFrame(columns=columnas)


def _obtener_info_cuenta(cuenta):
    cuenta_normalizada = normalizar_cuenta(cuenta)
    _, info = obtener_cuenta_pgc(cuenta_normalizada)
    return cuenta_normalizada, info


def _clasificar_saldo_para_balance(tipo, saldo):
    saldo = float(saldo or 0)

    if tipo in ["activo_no_corriente", "activo_corriente"]:
        return round(saldo, 2)

    if tipo in ["patrimonio_neto", "pasivo_no_corriente", "pasivo_corriente"]:
        return round(abs(saldo), 2)

    return round(saldo, 2)


def balance_comprobacion():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT cuenta, movimiento, importe
        FROM lineas_asiento
        ORDER BY cuenta
        """
    )

    resultados = cursor.fetchall()
    conn.close()

    if not resultados:
        return _df_vacio(COLUMNAS_BALANCE)

    acumulado = {}

    for cuenta, movimiento, importe in resultados:
        grupo = obtener_grupo_cuenta(cuenta)
        nombre = nombre_grupo_cuenta(grupo)

        if grupo not in acumulado:
            acumulado[grupo] = {
                "Cuenta": grupo,
                "Nombre": nombre,
                "Debe": 0.0,
                "Haber": 0.0,
            }

        importe = float(importe or 0)

        if movimiento == "debe":
            acumulado[grupo]["Debe"] += importe
        elif movimiento == "haber":
            acumulado[grupo]["Haber"] += importe

    datos = []
    for grupo, valores in acumulado.items():
        debe = round(valores["Debe"], 2)
        haber = round(valores["Haber"], 2)
        saldo = round(debe - haber, 2)

        datos.append([
            valores["Cuenta"],
            valores["Nombre"],
            debe,
            haber,
            saldo,
        ])

    df = pd.DataFrame(datos, columns=COLUMNAS_BALANCE)
    df = df.sort_values(by=["Cuenta"], kind="stable").reset_index(drop=True)
    return df

def libro_mayor(cuenta_buscada=None):
    conn = get_connection()
    cursor = conn.cursor()

    if cuenta_buscada:
        cuenta_buscada = normalizar_cuenta(str(cuenta_buscada).strip())
        cursor.execute(
            """
            SELECT
                a.fecha,
                a.concepto,
                l.cuenta,
                l.movimiento,
                l.importe
            FROM lineas_asiento l
            JOIN asientos a ON l.asiento_id = a.id
            WHERE l.cuenta = 
            ORDER BY a.fecha, a.id, l.id
            """,
            (cuenta_buscada,),
        )
    else:
        cursor.execute(
            """
            SELECT
                a.fecha,
                a.concepto,
                l.cuenta,
                l.movimiento,
                l.importe
            FROM lineas_asiento l
            JOIN asientos a ON l.asiento_id = a.id
            ORDER BY l.cuenta, a.fecha, a.id, l.id
            """
        )

    resultados = cursor.fetchall()
    conn.close()

    if not resultados:
        return _df_vacio(COLUMNAS_MAYOR)

    datos = []
    saldo = 0.0
    cuenta_actual = None

    for fecha, concepto, cuenta, movimiento, importe in resultados:
        cuenta = normalizar_cuenta(str(cuenta))
        importe = float(importe or 0)

        if cuenta_buscada is None and cuenta_actual != cuenta:
            saldo = 0.0
            cuenta_actual = cuenta

        if movimiento == "debe":
            saldo += importe
        else:
            saldo -= importe

        datos.append([
            fecha,
            concepto,
            cuenta,
            movimiento,
            round(importe, 2),
            round(saldo, 2),
        ])

    return pd.DataFrame(datos, columns=COLUMNAS_MAYOR)


def cuenta_resultados():
    df = balance_comprobacion()
    if df.empty:
        resumen = pd.DataFrame(
            [
                ["Importe neto cifra de negocios y otros ingresos", 0.0],
                ["Gastos de explotacion", 0.0],
                ["Resultado del ejercicio", 0.0],
            ],
            columns=["Concepto PGC", "Importe"],
        )
        return resumen, _df_vacio(COLUMNAS_PYG_DETALLE)

    datos = []
    total_ingresos = 0.0
    total_gastos = 0.0

    for _, row in df.iterrows():
        cuenta = normalizar_cuenta(row["Cuenta"])
        _, info = obtener_cuenta_pgc(cuenta)

        if not info or info.get("informe") != "pyg":
            continue

        nombre = info["nombre"]
        tipo = info.get("tipo")

        if tipo == "ingreso_explotacion":
            importe = float(row["Haber"]) - float(row["Debe"])
            total_ingresos += importe
            datos.append([cuenta, nombre, "Ingreso", round(importe, 2)])

        elif tipo == "gasto_explotacion":
            importe = float(row["Debe"]) - float(row["Haber"])
            total_gastos += importe
            datos.append([cuenta, nombre, "Gasto", round(importe, 2)])

    detalle = pd.DataFrame(datos, columns=COLUMNAS_PYG_DETALLE)
    if not detalle.empty:
        detalle = detalle[detalle["Importe"] != 0].reset_index(drop=True)

    resultado = round(total_ingresos - total_gastos, 2)

    resumen = pd.DataFrame(
        [
            ["Importe neto cifra de negocios y otros ingresos", round(total_ingresos, 2)],
            ["Gastos de explotacion", round(total_gastos, 2)],
            ["Resultado del ejercicio", resultado],
        ],
        columns=["Concepto PGC", "Importe"],
    )

    return resumen, detalle


def balance_situacion():
    df = balance_comprobacion()

    if df.empty:
        resumen = pd.DataFrame(
            [
                ["Activo no corriente", 0.0],
                ["Activo corriente", 0.0],
                ["TOTAL ACTIVO", 0.0],
                ["Patrimonio neto", 0.0],
                ["Pasivo no corriente", 0.0],
                ["Pasivo corriente", 0.0],
                ["TOTAL PN Y PASIVO", 0.0],
                ["DIFERENCIA", 0.0],
                ["CUADRA", "SI"],
            ],
            columns=COLUMNAS_BALANCE_RESUMEN,
        )
        vacio = _df_vacio(COLUMNAS_BALANCE_DETALLE)
        return resumen, vacio.copy(), vacio.copy(), vacio.copy(), vacio.copy(), vacio.copy()

    datos = []
    total_activo_no_corriente = 0.0
    total_activo_corriente = 0.0
    total_patrimonio_neto = 0.0
    total_pasivo_no_corriente = 0.0
    total_pasivo_corriente = 0.0

    for _, row in df.iterrows():
        cuenta = normalizar_cuenta(row["Cuenta"])
        _, info = obtener_cuenta_pgc(cuenta)

        if not info or info.get("informe") != "balance":
            continue

        nombre = info["nombre"]
        tipo = info.get("tipo")
        saldo = float(row["Saldo"])
        importe = _clasificar_saldo_para_balance(tipo, saldo)

        if tipo == "activo_no_corriente":
            total_activo_no_corriente += importe
            datos.append([cuenta, nombre, "Activo no corriente", round(importe, 2)])

        elif tipo == "activo_corriente":
            total_activo_corriente += importe
            datos.append([cuenta, nombre, "Activo corriente", round(importe, 2)])

        elif tipo == "patrimonio_neto":
            total_patrimonio_neto += importe
            datos.append([cuenta, nombre, "Patrimonio neto", round(importe, 2)])

        elif tipo == "pasivo_no_corriente":
            total_pasivo_no_corriente += importe
            datos.append([cuenta, nombre, "Pasivo no corriente", round(importe, 2)])

        elif tipo == "pasivo_corriente":
            total_pasivo_corriente += importe
            datos.append([cuenta, nombre, "Pasivo corriente", round(importe, 2)])

    detalle = pd.DataFrame(datos, columns=COLUMNAS_BALANCE_DETALLE)

    if not detalle.empty:
        detalle = detalle[detalle["Importe"] != 0].reset_index(drop=True)

    if detalle.empty:
        detalle = _df_vacio(COLUMNAS_BALANCE_DETALLE)

    total_activo = round(total_activo_no_corriente + total_activo_corriente, 2)
    total_pn_pasivo = round(total_patrimonio_neto + total_pasivo_no_corriente + total_pasivo_corriente, 2)
    diferencia = round(total_activo - total_pn_pasivo, 2)

    cuadra = "SI" if round(diferencia, 2) == 0 else "NO"

    resumen = pd.DataFrame(
        [
            ["Activo no corriente", round(total_activo_no_corriente, 2)],
            ["Activo corriente", round(total_activo_corriente, 2)],
            ["TOTAL ACTIVO", total_activo],
            ["Patrimonio neto", round(total_patrimonio_neto, 2)],
            ["Pasivo no corriente", round(total_pasivo_no_corriente, 2)],
            ["Pasivo corriente", round(total_pasivo_corriente, 2)],
            ["TOTAL PN Y PASIVO", total_pn_pasivo],
            ["DIFERENCIA", diferencia],
            ["CUADRA", cuadra],
        ],
        columns=COLUMNAS_BALANCE_RESUMEN,
    )

    activo_no_corriente = detalle[detalle["Bloque PGC"] == "Activo no corriente"].copy().reset_index(drop=True)
    activo_corriente = detalle[detalle["Bloque PGC"] == "Activo corriente"].copy().reset_index(drop=True)
    patrimonio_neto = detalle[detalle["Bloque PGC"] == "Patrimonio neto"].copy().reset_index(drop=True)
    pasivo_no_corriente = detalle[detalle["Bloque PGC"] == "Pasivo no corriente"].copy().reset_index(drop=True)
    pasivo_corriente = detalle[detalle["Bloque PGC"] == "Pasivo corriente"].copy().reset_index(drop=True)

    return (
        resumen,
        activo_no_corriente,
        activo_corriente,
        patrimonio_neto,
        pasivo_no_corriente,
        pasivo_corriente,
    )
