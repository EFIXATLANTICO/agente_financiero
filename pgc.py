import pandas as pd

PGC_PATH = "pgc_cuentas.csv"


def cargar_pgc():
    df = pd.read_csv(PGC_PATH, dtype=str, sep=";")
    df = df.fillna("")

    columnas_obligatorias = ["codigo", "nombre", "informe", "tipo"]
    for col in columnas_obligatorias:
        if col not in df.columns:
            df[col] = ""

    return df


def normalizar_cuenta(cuenta):
    cuenta = str(cuenta).strip()

    if "." in cuenta:
        cuenta = cuenta.split(".")[0]

    cuenta = cuenta.replace(" ", "")
    return cuenta


def obtener_cuenta_pgc(cuenta):
    cuenta = normalizar_cuenta(cuenta)
    df = cargar_pgc()

    exactas = df[df["codigo"] == cuenta]
    if not exactas.empty:
        row = exactas.iloc[0].to_dict()
        return row["codigo"], row

    mejor = None
    mejor_longitud = -1

    for _, row in df.iterrows():
        codigo = str(row["codigo"]).strip()
        if codigo and cuenta.startswith(codigo) and len(codigo) > mejor_longitud:
            mejor = row.to_dict()
            mejor_longitud = len(codigo)

    if mejor:
        return mejor["codigo"], mejor

    return None, None