
import hashlib
from datetime import datetime, date

import numpy as np
import pandas as pd

from db_context import get_connection
from conciliacion_bancaria import registrar_movimiento_banco

import json

def guardar_incidencia_importacion(
    importacion_id,
    tipo_importacion,
    fila_excel,
    fecha,
    concepto,
    detalle_error,
    datos=None,
    conn=None,
    cursor=None
):
    import json

    conn_local = conn is None or cursor is None

    if conn_local:
        conn = get_connection()
        cursor = conn.cursor()

    try:
        datos_serializables = _hacer_json_serializable(datos or {})
        fecha = _hacer_json_serializable(fecha)
        concepto = _hacer_json_serializable(concepto)
        detalle_error = _hacer_json_serializable(detalle_error)

        cursor.execute("""
            SELECT id
            FROM incidencias_importacion
            WHERE importacion_id = %s
              AND tipo_importacion = %s
              AND fila_excel = %s
              AND COALESCE(fecha, '') = COALESCE(%s, '')
              AND COALESCE(concepto, '') = COALESCE(%s, '')
              AND COALESCE(detalle_error, '') = COALESCE(%s, '')
            LIMIT 1
        """, (
            importacion_id,
            tipo_importacion,
            fila_excel,
            fecha,
            concepto,
            detalle_error
        ))

        existente = cursor.fetchone()
        if existente:
            if conn_local:
                conn.commit()
            return

        cursor.execute("""
            INSERT INTO incidencias_importacion (
                importacion_id,
                tipo_importacion,
                fila_excel,
                fecha,
                concepto,
                detalle_error,
                estado,
                datos_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            importacion_id,
            tipo_importacion,
            fila_excel,
            fecha,
            concepto,
            detalle_error,
            "pendiente",
            json.dumps(datos_serializables, ensure_ascii=False)
        ))

        if conn_local:
            conn.commit()

    finally:
        if conn_local:
            conn.close()

def _hacer_json_serializable(valor):
    if isinstance(valor, dict):
        return {str(k): _hacer_json_serializable(v) for k, v in valor.items()}

    if isinstance(valor, list):
        return [_hacer_json_serializable(v) for v in valor]

    if isinstance(valor, tuple):
        return [_hacer_json_serializable(v) for v in valor]

    if isinstance(valor, set):
        return [_hacer_json_serializable(v) for v in valor]

    if isinstance(valor, pd.Timestamp):
        return valor.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(valor, (datetime, date)):
        return valor.isoformat()

    if isinstance(valor, np.integer):
        return int(valor)

    if isinstance(valor, np.floating):
        return float(valor)

    if isinstance(valor, np.bool_):
        return bool(valor)

    if pd.isna(valor):
        return None

    return valor

def obtener_incidencias_importacion(estado=None, tipo_importacion=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT id, importacion_id, tipo_importacion, fila_excel, fecha, concepto, detalle_error, estado, datos_json, creado_en
    FROM incidencias_importacion
    WHERE 1=1
    """
    params = []

    if estado and estado != "todas":
        query += " AND estado = %s"
        params.append(estado)

    if tipo_importacion and tipo_importacion != "todos":
        query += " AND tipo_importacion = %s"
        params.append(tipo_importacion)

    query += " ORDER BY id DESC"

    cursor.execute(query, params)
    filas = cursor.fetchall()
    conn.close()

    return pd.DataFrame(filas, columns=[
        "ID", "Importación ID", "Tipo", "Fila Excel", "Fecha",
        "Concepto", "Detalle error", "Estado", "Datos JSON", "Creado en"
    ])


def marcar_incidencia_revisada(incidencia_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE incidencias_importacion
    SET estado = 'revisada'
    WHERE id = %s
    """, (incidencia_id,))

    conn.commit()
    conn.close()

    return "ok"


def cambiar_estado_incidencia_importacion(incidencia_id, estado):
    estado = (estado or "").strip().lower()
    if estado not in ("pendiente", "revisada"):
        return {"ok": False, "mensaje": "Estado de incidencia no valido"}

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        UPDATE incidencias_importacion
        SET estado = %s
        WHERE id = %s
        """, (estado, incidencia_id))

        conn.commit()
        return {"ok": True, "mensaje": f"Incidencia marcada como {estado}"}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}
    finally:
        conn.close()


def borrar_incidencia_importacion(incidencia_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM incidencias_importacion WHERE id = %s", (incidencia_id,))
    conn.commit()
    conn.close()

    return "ok"


# =========================
# UTILIDADES
# =========================

def _normalizar_nombre_columna(col):
    import unicodedata

    col = str(col).strip().lower()
    col = unicodedata.normalize("NFD", col)
    col = "".join(c for c in col if unicodedata.category(c) != "Mn")
    col = col.replace("€", "eur")
    col = col.replace("(", "").replace(")", "")
    col = col.replace(".", "")
    col = " ".join(col.split())
    return col

def normalizar_columnas(df):
    nuevas = {}
    for c in df.columns:
        nuevas[c] = _normalizar_nombre_columna(c)
    return df.rename(columns=nuevas)
import re
import unicodedata


def normalizar_texto_tercero(texto):
    texto = str(texto or "").strip().upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto)
    return texto


def buscar_o_crear_tercero_importacion(tipo_tercero, nombre):
    conn = get_connection()
    cursor = conn.cursor()

    nombre = str(nombre or "").strip()
    nombre_norm = normalizar_texto_tercero(nombre)

    if not nombre_norm:
        conn.close()
        return None

    tabla = "clientes" if tipo_tercero == "cliente" else "proveedores"

    try:
        cursor.execute(f"SELECT id, nombre FROM {tabla}")
        filas = cursor.fetchall()

        for tercero_id, nombre_existente in filas:
            if normalizar_texto_tercero(nombre_existente) == nombre_norm:
                conn.close()
                return tercero_id

        cursor.execute(
            f"""
            INSERT INTO {tabla} (nombre, nif, direccion, email, telefono)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nombre.strip(), "", "", "", "")
        )
        conn.commit()
        tercero_id = cursor.lastrowid
        conn.close()
        return tercero_id

    except Exception as e:
        print(f"ERROR crear tercero {tabla} | nombre={nombre} | error={e}")
        conn.close()
        return None

def sugerir_tipo_importacion(df):
    columnas = set(df.columns)

    tiene_fecha = "fecha" in columnas
    tiene_total = any(c in columnas for c in ["total", "importe", "base imponible"])
    tiene_tercero = any(c in columnas for c in [
        "cliente", "proveedor", "razon social", "nombre", "empresa", "tercero"
    ])
    tiene_cuentas = "cuenta debe" in columnas or "cuenta haber" in columnas

    if tiene_cuentas:
        return "asientos"

    if tiene_fecha and "concepto" in columnas and "importe" in columnas and not tiene_tercero:
        return "movimientos"

    if tiene_fecha and tiene_total and tiene_tercero:
        return "facturas"

    return "desconocido"


def sugerir_mapeo_columnas(df):
    columnas = list(df.columns)

    def buscar(*opciones):
        for opcion in opciones:
            if opcion in columnas:
                return opcion
        return None

    mapeo = {
        "fecha": buscar("fecha", "fecha factura", "fecha emision", "fecha emisión"),
        "tercero": buscar("razon social", "razón social", "nombre", "empresa", "tercero", "cliente", "proveedor"),
        "numero_factura": buscar("codigo", "código", "factura", "numero factura", "n factura"),
        "concepto": buscar("concepto", "observaciones", "descripcion", "descripción"),
        "total": buscar("total", "importe"),
        "base": buscar("base imponible", "base"),
        "impuesto_pct": buscar("igic", "iva", "impuesto %", "tipo impuesto"),
        "cuota_impuesto": buscar("cuota impuesto", "impuesto", "igic cuota", "iva cuota"),
        "forma_pago": buscar("forma pago", "forma de pago", "metodo pago", "método pago", "pago"),
        "dias_vencimiento": buscar("vencimientos", "vencimiento", "dias", "días", "plazo"),
        "fecha_vencimiento": buscar("fecha vencimiento"),
    }

    return mapeo
def inferir_tipo_tercero(df, mapeo):
    col_tercero = mapeo.get("tercero")
    if not col_tercero or col_tercero not in df.columns:
        return "cliente"

    columnas = set(df.columns)

    if "proveedor" in columnas:
        return "proveedor"

    texto_columnas = " ".join(columnas).lower()

    if "cliente" in texto_columnas or "razon social" in texto_columnas:
        return "cliente"

    return "cliente"

def inferir_opciones_importacion(df, mapeo):
    tipo_tercero = inferir_tipo_tercero(df, mapeo)

    return {
        "tipo_tercero": tipo_tercero,
        "igic_por_defecto": 7.0,
        "crear_terceros": True,
        "crear_vencimientos": True,
        "generar_asientos": True,
    }


def detectar_tipo_excel(df):
    columnas = {_normalizar_nombre_columna(c) for c in df.columns}

    # DEBUG (MUY IMPORTANTE)
    print("COLUMNAS DETECTADAS:", columnas)

    # --- ASIENTOS ---
    columnas_asientos = {
        "fecha",
        "cuenta debe",
        "debe eur",
        "cuenta haber",
        "haber eur",
        "concepto"
    }

    # --- MOVIMIENTOS ---
    columnas_movimientos = {
        "fecha",
        "concepto",
        "importe"
    }

    # --- FACTURAS (flexible) ---
    tiene_fecha = "fecha" in columnas
    tiene_total = "total" in columnas or "importe" in columnas
    tiene_cliente = (
        "cliente" in columnas
        or "razon social" in columnas
        or "nombre" in columnas
    )
    tiene_pago = any("pago" in c for c in columnas)
    tiene_vencimiento = any("venc" in c for c in columnas)

    if columnas_asientos.issubset(columnas):
        return "asientos"

    if columnas_movimientos.issubset(columnas):
        return "movimientos"

    # 👇 DETECCIÓN INTELIGENTE
    if tiene_fecha and tiene_total and tiene_cliente:
        return "facturas"
    # --- PAGOS PROVEEDOR / CARTERA DE PAGOS ---
    columnas_pagos_base = {
        "factura/venc",
        "identificador",
        "proveedor",
        "razon",
        "importe",
        "fec fact",
        "fec vcto",
        "forma de pago",
        "estado"
    }

    if columnas_pagos_base.issubset(columnas) and ("fp" in columnas or "f p" in columnas):
        return "pagos_proveedor"

    return "desconocido"

def leer_excel(archivo):
    df = pd.read_excel(archivo)
    df = normalizar_columnas(df)

    tipo = detectar_tipo_excel(df)
    mapeo = sugerir_mapeo_columnas(df)

    return tipo, df, mapeo

def calcular_hash_archivo(archivo_bytes):
    return hashlib.md5(archivo_bytes).hexdigest()


def _es_vacio(valor):
    if valor is None:
        return True
    try:
        return pd.isna(valor)
    except Exception:
        return False


def _texto_limpio(valor, default=""):
    if _es_vacio(valor):
        return default
    texto = str(valor).strip()
    if texto.lower() in {"nan", "nat", "none"}:
        return default
    return texto


def _normalizar_fecha_importacion(valor):
    if _es_vacio(valor):
        raise ValueError("Fecha vacía")

    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d")

    try:
        ts = pd.to_datetime(valor, errors="raise", dayfirst=True)
        if pd.isna(ts):
            raise ValueError
        return ts.strftime("%Y-%m-%d")
    except Exception:
        texto = _texto_limpio(valor)
        if not texto:
            raise ValueError("Fecha vacía")
        raise ValueError(f"Fecha no válida: {texto}")


def _parsear_importe(valor):
    if _es_vacio(valor):
        raise ValueError("Importe vacío")

    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return round(float(valor), 2)

    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none"}:
        raise ValueError("Importe vacío")

    negativo = False
    if texto.startswith("(") and texto.endswith(")"):
        negativo = True
        texto = texto[1:-1].strip()

    texto = texto.replace("€", "").replace("EUR", "").replace("eur", "")
    texto = texto.replace(" ", "")

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        importe = float(texto)
    except Exception as e:
        raise ValueError(f"Importe no numérico: {valor}") from e

    if negativo:
        importe *= -1

    return round(importe, 2)


def _extraer_lineas_desde_fila(row):
    lineas = []

    cuenta_debe = _texto_limpio(row.get("cuenta debe"))
    importe_debe_raw = row.get("debe eur")

    if cuenta_debe and not _es_vacio(importe_debe_raw):
        importe_debe = _parsear_importe(importe_debe_raw)

        if importe_debe > 0:
            lineas.append((cuenta_debe, "debe", importe_debe))
        elif importe_debe < 0:
            lineas.append((cuenta_debe, "haber", abs(importe_debe)))

    cuenta_haber = _texto_limpio(row.get("cuenta haber"))
    importe_haber_raw = row.get("haber eur")

    if cuenta_haber and not _es_vacio(importe_haber_raw):
        importe_haber = _parsear_importe(importe_haber_raw)

        if importe_haber > 0:
            lineas.append((cuenta_haber, "haber", importe_haber))
        elif importe_haber < 0:
            lineas.append((cuenta_haber, "debe", abs(importe_haber)))

    if not lineas:
        raise ValueError("Fila sin líneas contables válidas")

    return lineas


def _insertar_movimiento_banco_en_cursor(cursor, fecha, concepto, importe, saldo=None, referencia=None):
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_banco (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            concepto TEXT,
            importe REAL,
            sentido TEXT,
            saldo REAL,
            referencia TEXT,
            estado_conciliacion TEXT DEFAULT 'pendiente',
            revisado INTEGER DEFAULT 0
        )
        """)
    except Exception:
        pass

    sentido = "ingreso" if float(importe) > 0 else "pago"
    cursor.execute("""
    INSERT INTO movimientos_banco (
        fecha, concepto, importe, sentido, saldo, referencia
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        fecha,
        concepto,
        abs(float(importe)),
        sentido,
        saldo,
        referencia
    ))


# =========================
# IMPORTACIONES
# =========================

def registrar_importacion(tipo, nombre_archivo, hash_archivo):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id
    FROM importaciones
    WHERE hash_archivo = %s
    ORDER BY id DESC
    LIMIT 1
    """, (hash_archivo,))
    existente = cursor.fetchone()

    if existente:
        importacion_id_existente = existente[0]

        cursor.execute("""
        SELECT COUNT(*)
        FROM asientos_importacion
        WHERE importacion_id = %s
        """, (importacion_id_existente,))
        total_asientos = cursor.fetchone()[0]

        # Si ya tiene asientos vinculados, sí es duplicado real
        if total_asientos > 0:
            conn.close()
            return None, "duplicado"

        # Si no tiene asientos, era una importación fallida/incompleta:
        # la borramos y permitimos reintentar
        cursor.execute("DELETE FROM importaciones WHERE id = %s", (importacion_id_existente,))
        conn.commit()

    cursor.execute("""
    INSERT INTO importaciones (tipo, nombre_archivo, hash_archivo, fecha_importacion)
    VALUES (%s, %s, %s, %s)
    RETURNING id
    """, (
        tipo,
        nombre_archivo,
        hash_archivo,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    importacion_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    return importacion_id, "ok"


# =========================
# CLASIFICACIÓN DE MOVIMIENTOS
# =========================

def clasificar_movimiento(concepto, importe):
    concepto_norm = str(concepto).strip().lower()
    importe = float(importe)

    if "amazon" in concepto_norm or "papeleria" in concepto_norm or "papelería" in concepto_norm:
        return "compra", "600 Compras"

    if "comision" in concepto_norm or "comisión" in concepto_norm or "gasto bancario" in concepto_norm:
        return "gasto_bancario", "626 Servicios bancarios"

    if "seguro" in concepto_norm:
        return "gasto", "625 Prima de seguros"

    if "alquiler" in concepto_norm or "renting" in concepto_norm:
        return "gasto", "621 Arrendamientos y cánones"

    if "nomina" in concepto_norm or "nómina" in concepto_norm:
        return "gasto", "640 Sueldos y salarios"

    if "hacienda" in concepto_norm or "aeat" in concepto_norm:
        return "gasto", "475 Hacienda Pública acreedora"

    if "cliente" in concepto_norm or "cobro" in concepto_norm or importe > 0:
        return "ingreso", "700 Ventas"

    if importe < 0:
        return "gasto", "629 Otros servicios"

    return "desconocido", "999 Cuenta pendiente de clasificar"


def clasificar_dataframe_movimientos(df):
    df = df.copy()

    tipos = []
    cuentas = []

    for _, row in df.iterrows():
        concepto = str(row["concepto"]).strip()
        importe = float(row["importe"])

        tipo, cuenta = clasificar_movimiento(concepto, importe)

        tipos.append(tipo)
        cuentas.append(cuenta)

    df["tipo_detectado"] = tipos
    df["cuenta_sugerida"] = cuentas

    return df


# =========================
# VALIDACIÓN DE ASIENTOS
# =========================

def validar_asiento_compuesto(lineas):
    if len(lineas) < 2:
        return False, "El asiento tiene menos de 2 líneas"

    total_debe = 0.0
    total_haber = 0.0

    for cuenta, movimiento, importe in lineas:
        cuenta = _texto_limpio(cuenta)
        if not cuenta:
            return False, "Hay una línea sin cuenta"

        try:
            importe = _parsear_importe(importe)
        except Exception as e:
            return False, str(e)

        if importe < 0:
            return False, "Hay una línea con importe negativo"

        movimiento = _texto_limpio(movimiento).lower()
        if movimiento == "debe":
            total_debe += importe
        elif movimiento == "haber":
            total_haber += importe
        else:
            return False, "Movimiento no válido"

    if round(total_debe, 2) != round(total_haber, 2):
        return False, f"Asiento descuadrado: debe {round(total_debe, 2)} / haber {round(total_haber, 2)}"

    return True, "OK"


# =========================
# IMPORTAR ASIENTOS
# =========================
# IMPORTAR ASIENTOS
# =========================

def importar_asientos_desde_excel(df, nombre_archivo, archivo_bytes):
    hash_archivo = calcular_hash_archivo(archivo_bytes)
    importacion_id, estado = registrar_importacion("asientos", nombre_archivo, hash_archivo)

    if estado == "duplicado":
        return {"ok": False, "estado": "duplicado"}

    columnas_requeridas = [
        "fecha",
        "cuenta debe",
        "debe eur",
        "cuenta haber",
        "haber eur",
        "concepto"
    ]

    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        return {"ok": False, "estado": "error_columnas", "detalle": faltantes}

    conn = get_connection()
    cursor = conn.cursor()
    importados = 0
    errores = []

    def registrar_error(fila_excel, fecha, concepto, mensaje, datos=None):
        error_dict = {
            "fila_excel": fila_excel,
            "fecha": fecha,
            "concepto": concepto,
            "error": mensaje,
        }
        errores.append(error_dict)
        guardar_incidencia_importacion(
            importacion_id=importacion_id,
            tipo_importacion="asientos",
            fila_excel=fila_excel,
            fecha=fecha,
            concepto=concepto,
            detalle_error=mensaje,
            datos=datos or error_dict,
            conn=conn,
            cursor=cursor,
        )

    def guardar_asiento_compuesto(fecha, concepto, lineas):
        nonlocal importados
        valido, mensaje = validar_asiento_compuesto(lineas)
        if not valido:
            return False, mensaje

        cursor.execute("""
        INSERT INTO asientos (fecha, concepto, tipo_operacion)
        VALUES (?, ?, ?)
        """, (fecha, concepto, "importado_excel"))
        asiento_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO asientos_importacion (importacion_id, asiento_id)
        VALUES (?, ?)
        """, (importacion_id, asiento_id))

        for cuenta, movimiento, importe in lineas:
            cursor.execute("""
            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
            VALUES (?, ?, ?, ?)
            """, (asiento_id, cuenta, movimiento, float(_parsear_importe(importe))))

        importados += 1
        return True, "OK"

    try:
        df = df.copy()
        if df.empty:
            return {"ok": False, "estado": "sin_lineas"}

        df["_fila_excel"] = range(2, len(df) + 2)
        df["fecha"] = df["fecha"].replace(r"^\s*$", pd.NA, regex=True).ffill()
        df["concepto"] = df["concepto"].replace(r"^\s*$", pd.NA, regex=True).ffill()

        lineas_actuales = []
        filas_actuales = []
        fecha_actual = None
        concepto_actual = None

        def cerrar_bloque():
            nonlocal lineas_actuales, filas_actuales, fecha_actual, concepto_actual
            if not lineas_actuales:
                return
            fila_ref = filas_actuales[0] if filas_actuales else None
            ok, mensaje = guardar_asiento_compuesto(fecha_actual, concepto_actual, lineas_actuales)
            if not ok:
                registrar_error(
                    fila_ref,
                    fecha_actual,
                    concepto_actual,
                    mensaje,
                    {
                        "filas_excel": filas_actuales,
                        "lineas": lineas_actuales,
                        "fecha": fecha_actual,
                        "concepto": concepto_actual,
                    },
                )
            lineas_actuales = []
            filas_actuales = []
            fecha_actual = None
            concepto_actual = None

        for _, row in df.iterrows():
            fila_excel = int(row["_fila_excel"])
            tiene_debe = _texto_limpio(row.get("cuenta debe")) or not _es_vacio(row.get("debe eur"))
            tiene_haber = _texto_limpio(row.get("cuenta haber")) or not _es_vacio(row.get("haber eur"))
            if not (tiene_debe or tiene_haber):
                continue

            try:
                fecha = _normalizar_fecha_importacion(row.get("fecha"))
                concepto = _texto_limpio(row.get("concepto"), default="Importación Excel")
            except Exception as e:
                registrar_error(fila_excel, _texto_limpio(row.get("fecha")), _texto_limpio(row.get("concepto")), str(e), dict(row))
                continue

            if fecha_actual is None:
                fecha_actual = fecha
                concepto_actual = concepto
            elif fecha != fecha_actual:
                cerrar_bloque()
                fecha_actual = fecha
                concepto_actual = concepto

            try:
                nuevas_lineas = _extraer_lineas_desde_fila(row)
                lineas_actuales.extend(nuevas_lineas)
                filas_actuales.append(fila_excel)

                valido_tmp, _ = validar_asiento_compuesto(lineas_actuales)
                if valido_tmp:
                    cerrar_bloque()

            except Exception as e:
                registrar_error(fila_excel, fecha, concepto, str(e), dict(row))

        cerrar_bloque()

        if importados == 0 and errores:
            conn.commit()
            return {
                "ok": False,
                "estado": "sin_asientos_validos",
                "importados": 0,
                "errores": errores,
                "num_errores": len(errores),
            }

        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM asientos")
        total_asientos_bd = cursor.fetchone()[0]

        return {
            "ok": True,
            "estado": "ok_parcial" if errores else "ok",
            "importados": importados,
            "errores": errores,
            "num_errores": len(errores),
            "total_asientos_bd": total_asientos_bd,
            "importacion_id": importacion_id,
        }

    except Exception as e:
        import traceback
        conn.rollback()
        detalle = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(detalle)
        return {"ok": False, "estado": "error", "detalle": detalle}

    finally:
        conn.close()

# =========================
# IMPORTAR MOVIMIENTOS BANCARIOS
# =========================
# IMPORTAR MOVIMIENTOS BANCARIOS
# =========================

def importar_movimientos_desde_excel(df, nombre_archivo, archivo_bytes):
    hash_archivo = calcular_hash_archivo(archivo_bytes)
    importacion_id, estado = registrar_importacion("movimientos", nombre_archivo, hash_archivo)

    if estado == "duplicado":
        return "duplicado"

    columnas_requeridas = ["fecha", "concepto", "importe"]
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        return f"error_columnas: faltan {', '.join(faltantes)}"

    conn = get_connection()
    cursor = conn.cursor()
    errores = []
    importados = 0

    try:
        df = df.copy()

        if "tipo_detectado" not in df.columns or "cuenta_sugerida" not in df.columns:
            df = clasificar_dataframe_movimientos(df)

        for idx, row in df.iterrows():
            fila_excel = int(idx) + 2
            try:
                fecha = _normalizar_fecha_importacion(row.get("fecha"))
                concepto = _texto_limpio(row.get("concepto"), default="Movimiento bancario")
                importe = _parsear_importe(row.get("importe"))
                tipo = _texto_limpio(row.get("tipo_detectado"), default="desconocido")
                cuenta = _texto_limpio(row.get("cuenta_sugerida"), default="999 Cuenta pendiente de clasificar")

                _insertar_movimiento_banco_en_cursor(
                    cursor,
                    fecha=fecha,
                    concepto=concepto,
                    importe=importe,
                    saldo=row.get("saldo"),
                    referencia=row.get("referencia"),
                )

                cursor.execute("""
                INSERT INTO asientos (fecha, concepto, tipo_operacion)
                VALUES (?, ?, ?)
                """, (fecha, concepto, "movimiento_excel"))

                asiento_id = cursor.lastrowid

                cursor.execute("""
                INSERT INTO asientos_importacion (importacion_id, asiento_id)
                VALUES (?, ?)
                """, (importacion_id, asiento_id))

                if tipo == "ingreso":
                    lineas = [
                        ("572 Bancos", "debe", abs(importe)),
                        (cuenta, "haber", abs(importe))
                    ]
                elif tipo in ["gasto", "compra", "gasto_bancario"]:
                    lineas = [
                        (cuenta, "debe", abs(importe)),
                        ("572 Bancos", "haber", abs(importe))
                    ]
                else:
                    lineas = [
                        ("999 Cuenta pendiente de clasificar", "debe", abs(importe)),
                        ("572 Bancos", "haber", abs(importe))
                    ]

                valido, mensaje = validar_asiento_compuesto(lineas)
                if not valido:
                    raise ValueError(mensaje)

                for cuenta_linea, movimiento, importe_linea in lineas:
                    cursor.execute("""
                    INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                    VALUES (?, ?, ?, ?)
                    """, (asiento_id, cuenta_linea, movimiento, float(importe_linea)))

                importados += 1

            except Exception as e:
                errores.append({
                    "fila_excel": fila_excel,
                    "fecha": _texto_limpio(row.get("fecha")),
                    "concepto": _texto_limpio(row.get("concepto")),
                    "error": str(e),
                })
                guardar_incidencia_importacion(
                    importacion_id=importacion_id,
                    tipo_importacion="movimientos",
                    fila_excel=fila_excel,
                    fecha=_texto_limpio(row.get("fecha")),
                    concepto=_texto_limpio(row.get("concepto")),
                    detalle_error=str(e),
                    datos={k: (None if _es_vacio(v) else str(v)) for k, v in row.to_dict().items()},
                    conn=conn,
                    cursor=cursor,
                )

        conn.commit()
        if errores and importados == 0:
            return f"error: no se pudo importar ninguna fila. Errores: {len(errores)}"
        return "ok"

    except Exception as e:
        conn.rollback()
        return f"error: {e}"

    finally:
        conn.close()

def importar_pagos_proveedor_desde_excel(df, nombre_archivo, archivo_bytes):
    hash_archivo = calcular_hash_archivo(archivo_bytes)
    importacion_id, estado = registrar_importacion("pagos_proveedor", nombre_archivo, hash_archivo)

    if estado == "duplicado":
        return {"ok": False, "estado": "duplicado"}

    conn = get_connection()
    cursor = conn.cursor()

    importadas = 0
    errores = []

    def registrar_error(fila_excel, fecha, concepto, mensaje, datos=None):
        error_dict = {
            "fila_excel": fila_excel,
            "fecha": fecha,
            "concepto": concepto,
            "error": mensaje,
        }
        errores.append(error_dict)
        guardar_incidencia_importacion(
            importacion_id=importacion_id,
            tipo_importacion="pagos_proveedor",
            fila_excel=fila_excel,
            fecha=fecha,
            concepto=concepto,
            detalle_error=mensaje,
            datos=datos or error_dict,
            conn=conn,
            cursor=cursor,
        )

    try:
        columnas_requeridas = [
            "factura/venc",
            "identificador",
            "proveedor",
            "razon",
            "importe",
            "fec fact",
            "fec vcto",
            "forma de pago",
            "estado",
        ]

        faltantes = [c for c in columnas_requeridas if c not in df.columns]
        if faltantes:
            return {"ok": False, "estado": "error_columnas", "detalle": faltantes}

        if "fp" not in df.columns and "f p" not in df.columns:
            return {"ok": False, "estado": "error_columnas", "detalle": ["fp"]}

        for idx, row in df.iterrows():
            fila_excel = int(idx) + 2

            try:
                referencia = str(row.get("factura/venc", "") or "").strip()
                identificador = str(row.get("identificador", "") or "").strip()
                proveedor_codigo = str(row.get("proveedor", "") or "").strip()
                razon = str(row.get("razon", "") or "").strip()
                forma_pago = str(row.get("forma de pago", "") or "").strip()
                estado_pago = str(row.get("estado", "") or "").strip().lower()

                importe = _parsear_importe(row.get("importe"))

                if importe == 0:
                    raise ValueError("El importe es cero")

                fecha_fact = pd.to_datetime(row.get("fec fact"), errors="coerce")
                fecha_vcto = pd.to_datetime(row.get("fec vcto"), errors="coerce")

                if not razon:
                    raise ValueError("La razón del proveedor está vacía")

                cursor.execute("""
                    SELECT id
                    FROM proveedores
                    WHERE UPPER(TRIM(nombre)) = UPPER(TRIM(?))
                    LIMIT 1
                """, (razon,))
                fila_proveedor = cursor.fetchone()

                if fila_proveedor:
                    proveedor_id = int(fila_proveedor[0])
                else:
                    cursor.execute("""
                        INSERT INTO proveedores (nombre, nif, direccion, email, telefono)
                        VALUES (?, '', '', '', '')
                    """, (razon,))
                    proveedor_id = cursor.lastrowid

                fecha_emision_txt = fecha_fact.strftime("%Y-%m-%d") if pd.notna(fecha_fact) else None
                fecha_venc_txt = fecha_vcto.strftime("%Y-%m-%d") if pd.notna(fecha_vcto) else None

                numero_factura = referencia if referencia else identificador
                concepto = f"Pago proveedor {razon} | Ref {numero_factura}"

                estado_factura = "pendiente"
                if estado_pago in ["pagado", "pagada"]:
                    estado_factura = "pagada"

                igic_pct = 7.0
                total_factura = float(abs(importe))
                base_imponible = round(total_factura / (1 + igic_pct / 100), 2)
                cuota_igic = round(total_factura - base_imponible, 2)

                cursor.execute("""
                    INSERT INTO facturas (
                        tipo,
                        numero_factura,
                        tercero_id,
                        fecha_emision,
                        fecha_vencimiento,
                        concepto,
                        base_imponible,
                        cuota_impuesto,
                        total,
                        estado,
                        forma_pago,
                        observaciones
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "compra",
                    numero_factura,
                    proveedor_id,
                    fecha_emision_txt,
                    fecha_venc_txt,
                    concepto,
                    float(base_imponible),
                    float(cuota_igic),
                    float(total_factura),
                    estado_factura,
                    forma_pago,
                    f"Proveedor: {razon} | Identificador: {identificador} | Código proveedor: {proveedor_codigo} | IGIC aplicado: {igic_pct}%"
                ))
                factura_id = cursor.lastrowid

                fecha_asiento = fecha_emision_txt or fecha_venc_txt or datetime.now().strftime("%Y-%m-%d")

                cursor.execute("""
                    INSERT INTO asientos (fecha, concepto, tipo_operacion)
                    VALUES (?, ?, ?)
                """, (
                    fecha_asiento,
                    concepto,
                    "factura_importada_excel"
                ))
                asiento_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO asientos_importacion (importacion_id, asiento_id)
                    VALUES (?, ?)
                """, (importacion_id, asiento_id))

                if importe >= 0:
                    lineas = [
                        ("600 Compras", "debe", float(base_imponible)),
                        ("472 Hacienda Pública, IGIC soportado", "debe", float(cuota_igic)),
                        ("400 Proveedores", "haber", float(total_factura)),
                    ]
                else:
                    lineas = [
                        ("400 Proveedores", "debe", float(total_factura)),
                        ("609 Rappels por compras", "haber", float(base_imponible)),
                        ("472 Hacienda Pública, IGIC soportado", "haber", float(cuota_igic)),
                    ]

                for cuenta_linea, movimiento, importe_linea in lineas:
                    cursor.execute("""
                        INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                        VALUES (?, ?, ?, ?)
                    """, (
                        asiento_id,
                        cuenta_linea,
                        movimiento,
                        float(importe_linea)
                    ))

                if fecha_venc_txt:
                    estado_venc = "vencido" if estado_pago in ["vencido", "vencida"] else "pendiente"
                    importe_pendiente = 0.0 if estado_factura == "pagada" else float(abs(importe))

                    cursor.execute("""
                        INSERT INTO vencimientos (
                            factura_id,
                            fecha_vencimiento,
                            importe,
                            importe_pendiente,
                            estado,
                            tipo,
                            nombre_tercero
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        factura_id,
                        fecha_venc_txt,
                        float(abs(importe)),
                        float(importe_pendiente),
                        estado_venc,
                        "pago",
                        razon
                    ))

                importadas += 1

            except Exception as e:
                registrar_error(
                    fila_excel=fila_excel,
                    fecha=str(row.get("fec fact", "") or ""),
                    concepto=str(row.get("factura/venc", "") or ""),
                    mensaje=str(e),
                    datos={
                        "referencia": str(row.get("factura/venc", "") or "").strip(),
                        "identificador": str(row.get("identificador", "") or "").strip(),
                        "proveedor": str(row.get("razon", "") or "").strip(),
                    }
                )

        conn.commit()

        return {
            "ok": True,
            "estado": "ok",
            "importadas": importadas,
            "errores": errores,
            "num_errores": len(errores),
        }

    except Exception as e:
        conn.rollback()
        return {"ok": False, "estado": "error", "detalle": str(e)}

    finally:
        conn.close()

def _cuenta_compra_por_proveedor(razon, referencia="", forma_pago=""):
    texto = f"{razon or ''} {referencia or ''} {forma_pago or ''}".lower()

    if any(p in texto for p in ["orange", "telefonica", "vodafone", "internet", "fibra", "energia", "energy", "eni", "electric"]):
        return "628 Suministros"
    if any(p in texto for p in ["fred olsen", "trans", "transporte", "seur", "dhl", "correos", "mensaj"]):
        return "624 Transportes"
    if any(p in texto for p in ["asesor", "abogado", "gestor", "consultor"]):
        return "623 Servicios de profesionales independientes"
    if any(p in texto for p in ["seguro", "asegur"]):
        return "625 Primas de seguros"
    if any(p in texto for p in ["publicidad", "marketing", "google", "meta", "facebook"]):
        return "627 Publicidad, propaganda y relaciones publicas"
    if any(p in texto for p in ["maquinaria", "maquina", "tecnomaq"]):
        return "213 Maquinaria"
    if any(p in texto for p in ["mueble", "mobiliario"]):
        return "216 Mobiliario"
    if any(p in texto for p in ["software", "informatica", "licencia"]):
        return "206 Aplicaciones informaticas"
    if any(p in texto for p in ["mercadona", "comercial", "suministros industriales", "material"]):
        return "600 Compras de mercaderias"

    return "629 Otros servicios"


def importar_pagos_proveedor_desde_excel(df, nombre_archivo, archivo_bytes):
    from db_context import obtener_empresa_id_activa

    hash_archivo = calcular_hash_archivo(archivo_bytes)
    importacion_id, estado = registrar_importacion("pagos_proveedor", nombre_archivo, hash_archivo)

    if estado == "duplicado":
        return {"ok": False, "estado": "duplicado"}

    empresa_id = obtener_empresa_id_activa()
    conn = get_connection()
    cursor = conn.cursor()
    _asegurar_columnas_importacion_facturas(cursor)

    importadas = 0
    errores = []

    def registrar_error(fila_excel, fecha, concepto, mensaje, datos=None):
        error_dict = {
            "fila_excel": fila_excel,
            "fecha": fecha,
            "numero_factura": concepto,
            "tercero": (datos or {}).get("proveedor", ""),
            "error": mensaje,
        }
        errores.append(error_dict)
        guardar_incidencia_importacion(
            importacion_id=importacion_id,
            tipo_importacion="pagos_proveedor",
            fila_excel=fila_excel,
            fecha=fecha,
            concepto=concepto,
            detalle_error=mensaje,
            datos=datos or error_dict,
            conn=conn,
            cursor=cursor,
        )

    try:
        columnas_requeridas = [
            "factura/venc",
            "identificador",
            "proveedor",
            "razon",
            "importe",
            "fec fact",
            "fec vcto",
            "forma de pago",
            "estado",
        ]

        faltantes = [c for c in columnas_requeridas if c not in df.columns]
        if faltantes:
            return {"ok": False, "estado": "error_columnas", "detalle": faltantes}

        for idx, row in df.iterrows():
            fila_excel = int(idx) + 2

            try:
                cursor.execute("SAVEPOINT fila_importacion")

                referencia = _texto_limpio(row.get("factura/venc"))
                identificador = _texto_limpio(row.get("identificador"))
                proveedor_codigo = _texto_limpio(row.get("proveedor"))
                razon = _texto_limpio(row.get("razon"))
                forma_pago = _texto_limpio(row.get("forma de pago"), "credito").lower()
                estado_pago = _texto_limpio(row.get("estado")).lower()

                importe = round(_parsear_importe_excel(row.get("importe")), 2)
                if importe == 0:
                    raise ValueError("El importe es cero")

                fecha_fact = pd.to_datetime(row.get("fec fact"), errors="coerce", dayfirst=True)
                fecha_vcto = pd.to_datetime(row.get("fec vcto"), errors="coerce", dayfirst=True)

                if not razon:
                    raise ValueError("La razon del proveedor esta vacia")

                cursor.execute(
                    """
                    SELECT id
                    FROM proveedores
                    WHERE UPPER(TRIM(nombre)) = UPPER(TRIM(%s))
                    LIMIT 1
                    """,
                    (razon,),
                )
                fila_proveedor = cursor.fetchone()

                if fila_proveedor:
                    proveedor_id = int(fila_proveedor[0])
                else:
                    cursor.execute(
                        """
                        INSERT INTO proveedores (nombre, nif, direccion, email, telefono)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (razon, "", "", "", ""),
                    )
                    proveedor_id = cursor.fetchone()[0]

                fecha_venc_txt = fecha_vcto.strftime("%Y-%m-%d") if pd.notna(fecha_vcto) else None
                fecha_emision_txt = fecha_fact.strftime("%Y-%m-%d") if pd.notna(fecha_fact) else fecha_venc_txt
                if not fecha_emision_txt:
                    raise ValueError("Falta fecha de factura y fecha de vencimiento")
                numero_factura = referencia or identificador
                concepto = f"Factura proveedor {razon} | Ref {numero_factura}"
                estado_factura = "pagada" if estado_pago in ["pagado", "pagada", "cobrado", "cobrada"] else "pendiente"

                igic_pct = 7.0
                total_factura = float(abs(importe))
                base_imponible = round(total_factura / (1 + igic_pct / 100), 2)
                cuota_igic = round(total_factura - base_imponible, 2)
                es_abono = importe < 0
                tipo_factura = "abono_compra" if es_abono else "compra"
                cuenta_gasto = _cuenta_compra_por_proveedor(razon, referencia, forma_pago)

                cursor.execute(
                    """
                    INSERT INTO facturas (
                        empresa_id, tipo, serie, numero_factura, tercero_id,
                        nombre_tercero, fecha_emision, fecha_operacion,
                        fecha_vencimiento, concepto, base_imponible,
                        tipo_impuesto, impuesto_pct, cuota_impuesto, total,
                        estado, forma_pago, observaciones
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        empresa_id,
                        tipo_factura,
                        "PROV",
                        numero_factura,
                        proveedor_id,
                        razon,
                        fecha_emision_txt,
                        fecha_emision_txt,
                        fecha_venc_txt,
                        concepto,
                        float(base_imponible),
                        "IGIC",
                        float(igic_pct),
                        float(cuota_igic),
                        float(total_factura),
                        "abono" if es_abono else estado_factura,
                        forma_pago,
                        f"Importado de Seralven | Proveedor codigo: {proveedor_codigo} | Identificador: {identificador} | Cuenta sugerida: {cuenta_gasto}",
                    ),
                )
                factura_id = cursor.fetchone()[0]

                fecha_asiento = fecha_emision_txt or fecha_venc_txt or datetime.now().strftime("%Y-%m-%d")
                cursor.execute(
                    """
                    INSERT INTO asientos (fecha, concepto, tipo_operacion)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (fecha_asiento, concepto, "abono_importado_excel" if es_abono else "factura_importada_excel"),
                )
                asiento_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO asientos_importacion (importacion_id, asiento_id)
                    VALUES (%s, %s)
                    """,
                    (importacion_id, asiento_id),
                )

                if es_abono:
                    lineas = [
                        ("400 Proveedores", "debe", float(total_factura)),
                        ("608 Devoluciones de compras y operaciones similares", "haber", float(base_imponible)),
                        ("472 Hacienda Publica, IGIC soportado", "haber", float(cuota_igic)),
                    ]
                else:
                    lineas = [
                        (cuenta_gasto, "debe", float(base_imponible)),
                        ("472 Hacienda Publica, IGIC soportado", "debe", float(cuota_igic)),
                        ("400 Proveedores", "haber", float(total_factura)),
                    ]

                for cuenta_linea, movimiento, importe_linea in lineas:
                    if round(float(importe_linea or 0), 2) == 0:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (asiento_id, cuenta_linea, movimiento, float(importe_linea)),
                    )

                if fecha_venc_txt and not es_abono:
                    estado_venc = "vencido" if estado_pago in ["vencido", "vencida"] else "pendiente"
                    importe_pendiente = 0.0 if estado_factura == "pagada" else float(total_factura)
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
                            factura_id,
                            fecha_venc_txt,
                            float(total_factura),
                            float(importe_pendiente),
                            estado_venc,
                            "pago",
                            razon,
                        ),
                    )

                importadas += 1
                cursor.execute("RELEASE SAVEPOINT fila_importacion")

            except Exception as e:
                try:
                    cursor.execute("ROLLBACK TO SAVEPOINT fila_importacion")
                    cursor.execute("RELEASE SAVEPOINT fila_importacion")
                except Exception:
                    conn.rollback()

                registrar_error(
                    fila_excel=fila_excel,
                    fecha=str(row.get("fec fact", "") or ""),
                    concepto=str(row.get("factura/venc", "") or ""),
                    mensaje=str(e),
                    datos={
                        "referencia": _texto_limpio(row.get("factura/venc")),
                        "identificador": _texto_limpio(row.get("identificador")),
                        "proveedor": _texto_limpio(row.get("razon")),
                    },
                )

        conn.commit()
        return {
            "ok": True,
            "estado": "ok",
            "importadas": importadas,
            "errores": errores,
            "num_errores": len(errores),
        }

    except Exception as e:
        conn.rollback()
        return {"ok": False, "estado": "error", "detalle": str(e)}

    finally:
        conn.close()


# =========================
# MANTENIMIENTO
# =========================
# MANTENIMIENTO
# =========================

def deshacer_ultima_importacion():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, tipo
    FROM importaciones
    ORDER BY id DESC
    LIMIT 1
    """)
    ultima = cursor.fetchone()

    if not ultima:
        conn.close()
        return "sin_importaciones"

    importacion_id, tipo_importacion = ultima

    cursor.execute("""
    SELECT asiento_id
    FROM asientos_importacion
    WHERE importacion_id = ?
    """, (importacion_id,))
    asientos = cursor.fetchall()

    for fila in asientos:
        asiento_id = fila[0]
        cursor.execute("DELETE FROM lineas_asiento WHERE asiento_id = ?", (asiento_id,))
        cursor.execute("DELETE FROM asientos WHERE id = ?", (asiento_id,))

    cursor.execute("DELETE FROM asientos_importacion WHERE importacion_id = ?", (importacion_id,))
    cursor.execute("DELETE FROM importaciones WHERE id = ?", (importacion_id,))

    conn.commit()
    conn.close()

    return "ok"


def borrar_asientos_importados_excel():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id
    FROM asientos
    WHERE tipo_operacion = 'importado_excel'
    """)

    asientos = cursor.fetchall()

    if not asientos:
        conn.close()
        return "sin_asientos"

    for fila in asientos:
        asiento_id = fila[0]
        cursor.execute("DELETE FROM lineas_asiento WHERE asiento_id = ?", (asiento_id,))
        cursor.execute("DELETE FROM asientos_importacion WHERE asiento_id = ?", (asiento_id,))
        cursor.execute("DELETE FROM asientos WHERE id = ?", (asiento_id,))

    conn.commit()
    conn.close()

    return "ok"

def _parsear_dias_vencimiento(valor):
    texto = str(valor or "").strip().upper()
    texto = texto.replace(" ", "")

    if texto.endswith("D"):
        try:
            return int(texto.replace("D", "").strip())
        except Exception:
            return 0

    return 0


def _es_formato_seralven(df):
    columnas = set(df.columns)
    requeridas = {"codigo", "fecha", "razon social", "total", "forma pago", "vencimientos"}
    return requeridas.issubset(columnas)


def _asegurar_columnas_importacion_facturas(cursor):
    migraciones = [
        "ALTER TABLE vencimientos ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        "ALTER TABLE vencimientos ADD COLUMN IF NOT EXISTS importe_pendiente REAL DEFAULT 0",
        "ALTER TABLE vencimientos ADD COLUMN IF NOT EXISTS tipo TEXT",
        "ALTER TABLE vencimientos ADD COLUMN IF NOT EXISTS nombre_tercero TEXT",
        "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS forma_pago TEXT",
        "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS observaciones TEXT",
    ]

    for sql in migraciones:
        cursor.execute(sql)


def _numero_seralven(valor):
    texto = _texto_limpio(valor)
    if texto.endswith(".0"):
        texto = texto[:-2]
    if texto.isdigit() and len(texto) < 5:
        return texto.zfill(5)
    return texto


def importar_facturas_seralven(df, nombre_archivo, archivo_bytes, opciones):
    from db_context import obtener_empresa_id_activa

    hash_archivo = calcular_hash_archivo(archivo_bytes)
    importacion_id, estado = registrar_importacion("facturas_seralven", nombre_archivo, hash_archivo)

    if estado == "duplicado":
        return {"ok": False, "estado": "duplicado"}

    empresa_id = obtener_empresa_id_activa()
    igic_pct = float(opciones.get("igic_por_defecto", 7.0) or 7.0)

    conn = get_connection()
    cursor = conn.cursor()
    _asegurar_columnas_importacion_facturas(cursor)

    importadas = 0
    errores = []

    def registrar_error(fila_excel, fecha, concepto, mensaje, datos=None):
        error_dict = {
            "fila_excel": fila_excel,
            "fecha": fecha,
            "numero_factura": concepto,
            "error": mensaje,
        }
        errores.append(error_dict)
        guardar_incidencia_importacion(
            importacion_id=importacion_id,
            tipo_importacion="facturas_seralven",
            fila_excel=fila_excel,
            fecha=fecha,
            concepto=concepto,
            detalle_error=mensaje,
            datos=datos or error_dict,
            conn=conn,
            cursor=cursor,
        )

    try:
        for idx, row in df.iterrows():
            fila_excel = int(idx) + 2
            numero_factura = _numero_seralven(row.get("codigo"))
            try:
                fecha = pd.to_datetime(row.get("fecha"), errors="coerce", dayfirst=True)
                if pd.isna(fecha):
                    raise ValueError("Fecha invalida")

                tercero = _texto_limpio(row.get("razon social"))
                if not tercero:
                    raise ValueError("Cliente vacio")

                total = round(_parsear_importe_excel(row.get("total")), 2)
                if total == 0:
                    raise ValueError("Importe cero: revisar manualmente")

                es_abono = total < 0
                total_abs = abs(total)
                base = round(total_abs / (1 + igic_pct / 100), 2)
                cuota = round(total_abs - base, 2)
                fecha_txt = fecha.strftime("%Y-%m-%d")
                forma_pago = _texto_limpio(row.get("forma pago"), "credito").lower()
                dias_vto = _parsear_dias_vencimiento(row.get("vencimientos"))
                fecha_vto = fecha + pd.Timedelta(days=dias_vto) if dias_vto > 0 else None
                concepto = _texto_limpio(row.get("observaciones"), f"Factura {numero_factura} - {tercero}")

                cursor.execute(
                    """
                    SELECT id
                    FROM clientes
                    WHERE UPPER(TRIM(nombre)) = UPPER(TRIM(%s))
                    LIMIT 1
                    """,
                    (tercero,),
                )
                fila_cliente = cursor.fetchone()

                if fila_cliente:
                    tercero_id = int(fila_cliente[0])
                else:
                    cursor.execute(
                        """
                        INSERT INTO clientes (nombre, nif, direccion, email, telefono)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            tercero,
                            "",
                            _texto_limpio(row.get("direccion")),
                            "",
                            "",
                        ),
                    )
                    tercero_id = cursor.fetchone()[0]

                estado_factura = "abono" if es_abono else "pendiente" if dias_vto > 0 else "pagada"
                fecha_vto_txt = fecha_vto.strftime("%Y-%m-%d") if fecha_vto is not None else None
                tipo_factura = "abono_venta" if es_abono else "venta"

                cursor.execute(
                    """
                    INSERT INTO facturas (
                        empresa_id,
                        tipo,
                        serie,
                        numero_factura,
                        tercero_id,
                        nombre_tercero,
                        fecha_emision,
                        fecha_operacion,
                        fecha_vencimiento,
                        concepto,
                        base_imponible,
                        tipo_impuesto,
                        impuesto_pct,
                        cuota_impuesto,
                        total,
                        estado,
                        forma_pago,
                        observaciones
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        empresa_id,
                        tipo_factura,
                        "SER",
                        numero_factura,
                        tercero_id,
                        tercero,
                        fecha_txt,
                        fecha_txt,
                        fecha_vto_txt,
                        concepto,
                        base,
                        "IGIC",
                        igic_pct,
                        cuota,
                        total_abs,
                        estado_factura,
                        forma_pago,
                        f"Importado de Seralven | {'Abono/rectificativa' if es_abono else 'Factura de venta'} | Cliente codigo: {_texto_limpio(row.get('cliente'))} | Empresa: {_texto_limpio(row.get('empresa'))}",
                    ),
                )
                factura_id = cursor.fetchone()[0]

                cuenta_cobro = "430 Clientes" if dias_vto > 0 else _cuenta_contrapartida_por_forma_pago("cliente", forma_pago)
                tipo_asiento = "abono_importado_excel" if es_abono else "factura_importada_excel"
                concepto_asiento = f"{'Abono' if es_abono else 'Factura venta'} {numero_factura} - {tercero}"
                cursor.execute(
                    """
                    INSERT INTO asientos (fecha, concepto, tipo_operacion)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (fecha_txt, concepto_asiento, tipo_asiento),
                )
                asiento_id = cursor.fetchone()[0]

                if es_abono:
                    lineas_contables = [
                        ("708 Devoluciones de ventas y operaciones similares", "debe", base),
                        ("477 Hacienda Publica, IGIC repercutido", "debe", cuota),
                        (cuenta_cobro, "haber", total_abs),
                    ]
                else:
                    lineas_contables = [
                        (cuenta_cobro, "debe", total_abs),
                        ("700 Ventas de mercaderias", "haber", base),
                        ("477 Hacienda Publica, IGIC repercutido", "haber", cuota),
                    ]

                for cuenta, movimiento, importe_linea in lineas_contables:
                    if importe_linea:
                        cursor.execute(
                            """
                            INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (asiento_id, cuenta, movimiento, float(importe_linea)),
                        )

                cursor.execute(
                    """
                    INSERT INTO asientos_importacion (importacion_id, asiento_id)
                    VALUES (%s, %s)
                    """,
                    (importacion_id, asiento_id),
                )

                if fecha_vto_txt and not es_abono:
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
                            factura_id,
                            fecha_vto_txt,
                            total_abs,
                            total_abs,
                            "pendiente",
                            "cobro",
                            tercero,
                        ),
                    )

                importadas += 1

            except Exception as e:
                registrar_error(
                    fila_excel=fila_excel,
                    fecha=str(row.get("fecha", "") or ""),
                    concepto=numero_factura,
                    mensaje=str(e),
                    datos={
                        "codigo": numero_factura,
                        "cliente": _texto_limpio(row.get("razon social")),
                        "total": _hacer_json_serializable(row.get("total")),
                    },
                )

        conn.commit()
        return {
            "ok": True,
            "estado": "ok",
            "importadas": importadas,
            "errores": errores,
            "num_errores": len(errores),
        }

    except Exception as e:
        conn.rollback()
        return {"ok": False, "estado": "error", "detalle": str(e)}

    finally:
        conn.close()


def _cuenta_contrapartida_por_forma_pago(tipo_tercero, forma_pago):
    forma_pago = str(forma_pago or "").strip().lower()

    if tipo_tercero == "cliente":
        if forma_pago in ["contado", "efectivo", "caja"]:
            return "570 Caja"
        if forma_pago in ["transferencia", "banco"]:
            return "572 Bancos"
        return "430 Clientes"

    else:
        if forma_pago in ["contado", "efectivo", "caja"]:
            return "570 Caja"
        if forma_pago in ["transferencia", "banco"]:
            return "572 Bancos"
        return "400 Proveedores"

def _parsear_importe_excel(valor):
    if pd.isna(valor):
        return 0.0

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()

    if not texto:
        return 0.0

    texto = texto.replace("€", "").replace("EUR", "").replace("eur", "").strip()

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", "")

    return float(texto)

def importar_documento_facturas(df, nombre_archivo, archivo_bytes, mapeo, opciones):
    from db_context import obtener_empresa_id_activa
    from contabilidad import crear_asiento_completo
    from operaciones_inteligentes import registrar_operacion_bd

    if _es_formato_seralven(df):
        return importar_facturas_seralven(df, nombre_archivo, archivo_bytes, opciones)

    hash_archivo = calcular_hash_archivo(archivo_bytes)
    importacion_id, estado = registrar_importacion("facturas", nombre_archivo, hash_archivo)

    if estado == "duplicado":
        return {"ok": False, "estado": "duplicado"}

    empresa_id = obtener_empresa_id_activa()
    conn = get_connection()
    cursor = conn.cursor()

    importadas = 0
    errores = []

    tipo_tercero = opciones.get("tipo_tercero", "cliente")
    igic_por_defecto = float(opciones.get("igic_por_defecto", 7.0) or 0)
    crear_terceros = bool(opciones.get("crear_terceros", True))
    crear_vencimientos = bool(opciones.get("crear_vencimientos", True))
    generar_asientos = bool(opciones.get("generar_asientos", True))

    col_fecha = mapeo.get("fecha")
    col_tercero = mapeo.get("tercero")
    col_numero = mapeo.get("numero_factura")
    col_concepto = mapeo.get("concepto")
    col_total = mapeo.get("total")
    col_base = mapeo.get("base")
    col_impuesto_pct = mapeo.get("impuesto_pct")
    col_cuota = mapeo.get("cuota_impuesto")
    col_forma_pago = mapeo.get("forma_pago")
    col_dias_vto = mapeo.get("dias_vencimiento")
    col_fecha_vto = mapeo.get("fecha_vencimiento")

    obligatorias = {
        "fecha": col_fecha,
        "tercero": col_tercero,
        "total": col_total,
    }

    faltantes = [k for k, v in obligatorias.items() if not v]
    if faltantes:
        conn.close()
        return {"ok": False, "estado": "mapeo_incompleto", "detalle": faltantes}

    try:
        df = df.copy()

        for idx, row in df.iterrows():
            try:
                fecha = pd.to_datetime(row.get(col_fecha), errors="coerce")
                tercero = str(row.get(col_tercero, "") or "").strip()
                numero_factura = str(row.get(col_numero, "") or "").strip() if col_numero else ""
                concepto = str(row.get(col_concepto, "") or "").strip() if col_concepto else ""
                forma_pago = str(row.get(col_forma_pago, "") or "").strip().lower() if col_forma_pago else "credito"

                if pd.isna(fecha):
                    raise ValueError("Fecha inválida")
                if not tercero:
                    raise ValueError("Tercero vacío")

                total = round(_parsear_importe_excel(row.get(col_total, 0)), 2)
                if total <= 0:
                    raise ValueError("Total inválido")

                if col_base and pd.notna(row.get(col_base)):
                    base = round(_parsear_importe_excel(row.get(col_base, 0)), 2)
                else:
                    base = round(total / (1 + igic_por_defecto / 100), 2) if igic_por_defecto > 0 else round(total, 2)

                if col_cuota and pd.notna(row.get(col_cuota)):
                    cuota = round(_parsear_importe_excel(row.get(col_cuota, 0)), 2)
                else:
                    cuota = round(total - base, 2)

                if col_impuesto_pct and pd.notna(row.get(col_impuesto_pct)):
                    impuesto_pct = round(_parsear_importe_excel(row.get(col_impuesto_pct, 0)), 2)
                else:
                    impuesto_pct = igic_por_defecto

                if round(base + cuota, 2) != round(total, 2):
                    cuota = round(total - base, 2)

                fecha_txt = fecha.strftime("%Y-%m-%d")

                if crear_terceros:
                    tercero_id = buscar_o_crear_tercero_importacion(tipo_tercero, tercero)
                    if tercero_id is None:
                        raise ValueError(f"No se pudo crear o recuperar el {tipo_tercero}: {tercero}")

                operacion_id = None
                asiento_id = None

                if generar_asientos:

                    # Determinar si es crédito o contado
                    es_credito = False

                    if col_dias_vto:
                        dias = _parsear_dias_vencimiento(row.get(col_dias_vto))
                        if dias > 0:
                            es_credito = True

                    if col_fecha_vto and pd.notna(row.get(col_fecha_vto)):
                        es_credito = True

                    if tipo_tercero == "cliente":
                        # Decisión contable ventas
                        if es_credito:
                            cuenta_contrapartida = "430 Clientes"
                        else:
                            if forma_pago in ["contado", "efectivo", "caja"]:
                                cuenta_contrapartida = "570 Caja"
                            elif forma_pago in ["transferencia", "banco"]:
                                cuenta_contrapartida = "572 Bancos"
                            else:
                                cuenta_contrapartida = "430 Clientes"

                        lineas = [
                            (cuenta_contrapartida, "debe", total),
                            ("700 Ventas de mercaderías", "haber", base),
                        ]
                        if cuota != 0:
                            lineas.append(("477 Hacienda Pública, IGIC repercutido", "haber", cuota))

                        asiento_id = crear_asiento_completo(
                            fecha=fecha_txt,
                            concepto=concepto or f"Factura importada {numero_factura} - {tercero}",
                            tipo_operacion="factura_importada_excel",
                            lineas=lineas,
                        )

                        datos_operacion = {
                            "empresa_id": empresa_id,
                            "tipo_operacion": "venta",
                            "fecha_operacion": fecha_txt,
                            "concepto": concepto or f"Factura importada {numero_factura}",
                            "nombre_tercero": tercero,
                            "numero_factura": numero_factura,
                            "forma_pago": forma_pago,
                            "base_imponible": base,
                            "impuesto_pct": impuesto_pct,
                            "cuota_impuesto": cuota,
                            "total": total,
                        }
                        operacion_id = registrar_operacion_bd(datos_operacion, cursor=cursor)

                    else:
                        # Decisión contable compras
                        if es_credito:
                            cuenta_contrapartida = "400 Proveedores"
                        else:
                            if forma_pago in ["contado", "efectivo", "caja"]:
                                cuenta_contrapartida = "570 Caja"
                            elif forma_pago in ["transferencia", "banco"]:
                                cuenta_contrapartida = "572 Bancos"
                            else:
                                cuenta_contrapartida = "400 Proveedores"

                        lineas = [("600 Compras de mercaderías", "debe", base)]
                        if cuota != 0:
                            lineas.append(("472 Hacienda Pública, IGIC soportado", "debe", cuota))
                        lineas.append((cuenta_contrapartida, "haber", total))

                        asiento_id = crear_asiento_completo(
                            fecha=fecha_txt,
                            concepto=concepto or f"Factura importada {numero_factura} - {tercero}",
                            tipo_operacion="factura_importada_excel",
                            lineas=lineas,
                        )

                        datos_operacion = {
                            "empresa_id": empresa_id,
                            "tipo_operacion": "compra",
                            "fecha_operacion": fecha_txt,
                            "concepto": concepto or f"Factura importada {numero_factura}",
                            "nombre_tercero": tercero,
                            "numero_factura": numero_factura,
                            "forma_pago": forma_pago,
                            "base_imponible": base,
                            "impuesto_pct": impuesto_pct,
                            "cuota_impuesto": cuota,
                            "total": total,
                        }
                        operacion_id = registrar_operacion_bd(datos_operacion, cursor=cursor)

                    if asiento_id:
                        cursor.execute(
                            """
                            INSERT INTO asientos_importacion (importacion_id, asiento_id)
                            VALUES (?, ?)
                            """,
                            (importacion_id, asiento_id),
                        )

                if crear_vencimientos and operacion_id:
                    fecha_vencimiento = None
                    if col_fecha_vto and pd.notna(row.get(col_fecha_vto)):
                        fecha_vencimiento = pd.to_datetime(row.get(col_fecha_vto), errors="coerce")
                    elif col_dias_vto:
                        dias = _parsear_dias_vencimiento(row.get(col_dias_vto))
                        if dias > 0:
                            fecha_vencimiento = fecha + pd.Timedelta(days=dias)

                    if fecha_vencimiento is not None and not pd.isna(fecha_vencimiento):
                        tipo_vto = "cobro" if tipo_tercero == "cliente" else "pago"
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
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                empresa_id,
                                operacion_id,
                                fecha_vencimiento.strftime("%Y-%m-%d"),
                                total,
                                total,
                                "pendiente",
                                tipo_vto,
                                tercero,
                            ),
                        )

                importadas += 1
                conn.commit()

            except Exception as e:
                mensaje = str(e)

                error_dict = {
                    "fila_excel": int(idx) + 2,
                    "tercero": str(row.get(col_tercero, "") or "").strip() if col_tercero else "",
                    "numero_factura": str(row.get(col_numero, "") or "").strip() if col_numero else "",
                    "error": mensaje,
                }

                errores.append(error_dict)

                guardar_incidencia_importacion(
                    importacion_id=importacion_id,
                    tipo_importacion="facturas",
                    fila_excel=int(idx) + 2,
                    fecha=fecha.strftime("%Y-%m-%d") if pd.notna(fecha) else None,
                    concepto=concepto if 'concepto' in locals() else "",
                    detalle_error=mensaje,
                    datos={
                        "fila_excel": int(idx) + 2,
                        "tercero": str(row.get(col_tercero, "") or "").strip() if col_tercero else "",
                        "numero_factura": str(row.get(col_numero, "") or "").strip() if col_numero else "",
                    }
                )

        conn.commit()
        return {
            "ok": True,
            "estado": "ok",
            "importadas": importadas,
            "errores": errores,
            "num_errores": len(errores),
        }

    except Exception as e:
        conn.rollback()
        return {"ok": False, "estado": "error", "detalle": str(e)}

    finally:
        conn.close()

def serializar_dataframe(df):
    df_copy = df.copy()

    for col in df_copy.columns:
        if str(df_copy[col].dtype).startswith("datetime"):
            df_copy[col] = df_copy[col].astype(str)

    return df_copy

def limpiar_historico_importaciones():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM incidencias_importacion")
        cursor.execute("DELETE FROM asientos_importacion")
        cursor.execute("DELETE FROM importaciones")

        conn.commit()
        return {"ok": True, "mensaje": "Histórico de importaciones eliminado correctamente"}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "mensaje": str(e)}

    finally:
        conn.close()

def importar_linea_corregida(df, fila_excel, tercero, numero_factura, total, tipo="factura"):
    from db_context import obtener_empresa_id_activa
    from contabilidad import crear_asiento_completo
    from operaciones_inteligentes import registrar_operacion_bd

    conn = get_connection()
    cursor = conn.cursor()

    try:
        empresa_id = obtener_empresa_id_activa()

        fila_excel = int(fila_excel)
        idx_df = fila_excel - 2

        if idx_df < 0 or idx_df >= len(df):
            raise ValueError(f"No se encontró la fila Excel {fila_excel} en el documento cargado")

        row = df.iloc[idx_df]

        fecha_raw = row.get("fecha")
        fecha = pd.to_datetime(fecha_raw, errors="coerce")
        if pd.isna(fecha):
            raise ValueError("La fecha de la fila no es válida")

        fecha_txt = fecha.strftime("%Y-%m-%d")

        forma_pago = str(row.get("forma pago", "") or row.get("forma_pago", "") or "credito").strip().lower()
        concepto = str(row.get("observaciones", "") or row.get("concepto", "") or f"Factura {numero_factura}").strip()

        total = round(float(total), 2)

        if total == 0:
            raise ValueError("El total no puede ser 0")

        igic_pct = 7.0
        total_abs = abs(total)
        base = round(total_abs / (1 + igic_pct / 100), 2)
        cuota = round(total_abs - base, 2)

        tercero_id = buscar_o_crear_tercero_importacion("cliente", tercero)
        if tercero_id is None:
            raise ValueError(f"No se pudo crear o recuperar el cliente: {tercero}")

        es_abono = total < 0

        if es_abono:
            lineas = [
                ("708 Devoluciones de ventas y operaciones similares", "debe", base),
                ("477 Hacienda Pública, IGIC repercutido", "debe", cuota),
                ("430 Clientes", "haber", total_abs),
            ]
            tipo_operacion = "abono_importado_excel"
            concepto_asiento = concepto or f"Abono importado {numero_factura} - {tercero}"
            tipo_bd = "venta_rectificativa"
        else:
            cuenta_contrapartida = "430 Clientes"
            if forma_pago in ["contado", "efectivo", "caja"]:
                cuenta_contrapartida = "570 Caja"
            elif forma_pago in ["transferencia", "banco"]:
                cuenta_contrapartida = "572 Bancos"

            lineas = [
                (cuenta_contrapartida, "debe", total_abs),
                ("700 Ventas de mercaderías", "haber", base),
                ("477 Hacienda Pública, IGIC repercutido", "haber", cuota),
            ]
            tipo_operacion = "factura_importada_excel"
            concepto_asiento = concepto or f"Factura importada {numero_factura} - {tercero}"
            tipo_bd = "venta"

        asiento_id = crear_asiento_completo(
            fecha=fecha_txt,
            concepto=concepto_asiento,
            tipo_operacion=tipo_operacion,
            lineas=lineas,
        )

        datos_operacion = {
            "empresa_id": empresa_id,
            "tipo_operacion": tipo_bd,
            "fecha_operacion": fecha_txt,
            "concepto": concepto_asiento,
            "nombre_tercero": tercero,
            "numero_factura": numero_factura,
            "forma_pago": forma_pago,
            "base_imponible": base,
            "impuesto_pct": igic_pct,
            "cuota_impuesto": cuota,
            "total": total_abs,
        }

        registrar_operacion_bd(datos_operacion, cursor=cursor)
        conn.commit()

        return {"ok": True, "asiento_id": asiento_id}

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()
