import os
import random
import glob
import datetime
import tempfile
import base64
import json
import textwrap

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_DISPONIBLE = True
except ImportError:
    px = None
    go = None
    PLOTLY_DISPONIBLE = False

import pandas as pd
import streamlit as st
import re

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

from login_view import logout
from auth_empresas import inicializar_master
from db_context import set_active_db_path, get_connection
from init_db import inicializar_bd_empresa

from importador_excel import (
    leer_excel,
    clasificar_dataframe_movimientos,
    importar_asientos_desde_excel,
    importar_documento_facturas,
    importar_linea_corregida,
    deshacer_ultima_importacion,
    inferir_opciones_importacion,
    borrar_asientos_importados_excel,
    obtener_incidencias_importacion,
    marcar_incidencia_revisada,
    borrar_incidencia_importacion,
    importar_pagos_proveedor_desde_excel,
    limpiar_historico_importaciones,
)
try:
    from importador_excel import importar_movimientos_desde_excel
except ImportError:
    def importar_movimientos_desde_excel(*args, **kwargs):
        return "error: la función importar_movimientos_desde_excel no está disponible en el archivo cargado"

from control_contable import validar_sistema_completo
from contabilidad import borrar_asiento, reset_contabilidad

from informes import (
    balance_comprobacion,
    libro_mayor,
    cuenta_resultados,
    balance_situacion
)

from operaciones_inteligentes import procesar_operacion_texto

from inmovilizado import (
    alta_inmovilizado,
    ver_inmovilizado,
    generar_amortizaciones_mes,
    historial_amortizaciones
)

from conciliacion_bancaria import (
    inicializar_tablas_conciliacion,
    movimientos_pendientes,
    facturas_pendientes,
    sugerencias_ia,
    aplicar_conciliacion,
    resumen_conciliacion,
    historial_conciliaciones,
    auto_conciliar_por_ia
)

from migrar_bd import migrar_bd_empresa

from terceros import (
    listar_terceros,
    obtener_tercero,
    crear_tercero,
    actualizar_tercero,
    borrar_tercero,
    metricas_tercero,
)

from tesoreria import registrar_desde_vencimiento

from contabilidad import aplicar_correccion_incidencia

from contabilidad import (
    aplicar_correccion_incidencia,
    crear_asiento_fianza_recibida,
    crear_asiento_fianza_devuelta
)

from clientes import recalcular_y_guardar_scoring

from facturacion import (
    generar_siguiente_numero_factura_venta,
    calcular_totales_factura_venta,
    registrar_factura,
    registrar_cobro_factura
)

# =========================================================
# ESTILO / DISEÑO
# =========================================================

def obtener_imagen_canarias_local():
    patrones = [
        "assets/canarias/*.jpg",
        "assets/canarias/*.jpeg",
        "assets/canarias/*.png",
        "assets/canarias/*.webp"
    ]

    imagenes = []
    for patron in patrones:
        imagenes.extend(glob.glob(patron))

    if not imagenes:
        return None

    return random.choice(imagenes)


def imagen_a_base64(ruta_imagen):
    if not ruta_imagen or not os.path.exists(ruta_imagen):
        return None

    with open(ruta_imagen, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def obtener_logo_efix():
    rutas_posibles = [
        "assets/logo_efix.png",
        "assets/logo_efix.jpg",
        "assets/logo_efix.jpeg",
        "assets/logo_efix.webp"
    ]

    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            return ruta

    return None


def mostrar_logo_efix(width=220, centrado=False):
    ruta_logo = obtener_logo_efix()
    if not ruta_logo:
        return

    if centrado:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(ruta_logo, width=width)
    else:
        st.image(ruta_logo, width=width)

def aplicar_estilo(modo="app"):
    st.markdown("""
    <style>

        html, body, [class*="css"] {
            font-family: "Segoe UI", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 8% 12%, rgba(56, 189, 248, 0.12), transparent 18%),
                radial-gradient(circle at 92% 10%, rgba(59, 130, 246, 0.10), transparent 18%),
                radial-gradient(circle at 50% 100%, rgba(99, 102, 241, 0.08), transparent 22%),
                linear-gradient(180deg, #f8fbff 0%, #eef5fb 52%, #edf4fb 100%);
            color: #132238;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 8% 12%, rgba(56, 189, 248, 0.12), transparent 18%),
                radial-gradient(circle at 92% 10%, rgba(59, 130, 246, 0.10), transparent 18%),
                radial-gradient(circle at 50% 100%, rgba(99, 102, 241, 0.08), transparent 22%),
                linear-gradient(180deg, #f8fbff 0%, #eef5fb 52%, #edf4fb 100%);
        }

        [data-testid="stHeader"] {
            background: transparent;
            height: 0 !important;
        }

        [data-testid="stToolbar"] {
            display: none !important;
        }

        #MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
            display: none !important;
        }

        .main > div {
            padding-top: 0.2rem;
        }

        .block-container {
            max-width: 96%;
            padding-top: 1.4rem;
            padding-bottom: 2rem;
        }

        section[data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(255,255,255,0.72) 0%, rgba(243,248,255,0.90) 100%);
            backdrop-filter: blur(24px);
            border-right: 1px solid rgba(59, 130, 246, 0.08);
            min-width: 280px !important;
            max-width: 280px !important;
            box-shadow: 10px 0 35px rgba(15, 23, 42, 0.04);
        }

        section[data-testid="stSidebar"] > div {
            background: transparent;
            padding-top: 1rem;
        }

        section[data-testid="stSidebar"] * {
            color: #17304d !important;
        }

        .hero-shell {
            background: rgba(255,255,255,0.60);
            border: 1px solid rgba(255,255,255,0.55);
            backdrop-filter: blur(16px);
            border-radius: 30px;
            padding: 1.2rem;
            box-shadow:
                0 22px 44px rgba(15, 23, 42, 0.07),
                inset 0 1px 0 rgba(255,255,255,0.55);
            margin-bottom: 1.2rem;
        }

        .hero-box {
            background:
                radial-gradient(circle at top left, rgba(56,189,248,0.18), transparent 25%),
                linear-gradient(135deg, #0f172a 0%, #1d4ed8 58%, #0ea5e9 100%);
            padding: 1.8rem 1.9rem;
            border-radius: 26px;
            color: white;
            box-shadow: 0 22px 48px rgba(37, 99, 235, 0.22);
        }

        .hero-title {
            font-size: 2.2rem;
            font-weight: 900;
            margin-bottom: 0.35rem;
            letter-spacing: -0.04em;
            line-height: 1.02;
        }

        .hero-text {
            font-size: 1.08rem;
            opacity: 0.96;
            line-height: 1.55;
        }

        .section-title {
            color: #0f172a;
            font-size: 1.58rem;
            font-weight: 900;
            margin-bottom: 0.85rem;
            letter-spacing: -0.03em;
        }

        .block-chip {
            display: inline-block;
            background: linear-gradient(135deg, rgba(219, 234, 254, 0.96) 0%, rgba(224, 242, 254, 0.96) 100%);
            color: #1d4ed8;
            border-radius: 999px;
            padding: 0.38rem 0.90rem;
            font-size: 0.92rem;
            font-weight: 800;
            margin-bottom: 0.90rem;
            box-shadow: 0 10px 20px rgba(37,99,235,0.08);
        }

        .small-muted {
            color: #52657e;
            font-size: 1rem;
        }

        .soft-card {
            background: rgba(255,255,255,0.78);
            border: 1px solid rgba(255,255,255,0.55);
            backdrop-filter: blur(14px);
            border-radius: 24px;
            padding: 1.15rem;
            box-shadow:
                0 18px 38px rgba(15, 23, 42, 0.05),
                inset 0 1px 0 rgba(255,255,255,0.55);
        }

        .feature-card {
            background: rgba(255,255,255,0.84);
            border: 1px solid rgba(255,255,255,0.58);
            backdrop-filter: blur(16px);
            border-radius: 24px;
            padding: 1.25rem;
            box-shadow:
                0 18px 40px rgba(15, 23, 42, 0.05),
                inset 0 1px 0 rgba(255,255,255,0.55);
            min-height: 165px;
        }

        .feature-icon {
            width: 48px;
            height: 48px;
            border-radius: 16px;
            background: linear-gradient(135deg, #dbeafe 0%, #e0f2fe 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            margin-bottom: 0.95rem;
            box-shadow: 0 10px 18px rgba(59,130,246,0.10);
        }

        .feature-title {
            font-size: 1.12rem;
            font-weight: 900;
            color: #0f172a;
            margin-bottom: 0.35rem;
        }

        .feature-text {
            font-size: 0.98rem;
            color: #52657e;
            line-height: 1.55;
        }

        label, .stSelectbox label, .stTextInput label, .stNumberInput label, .stDateInput label, .stTextArea label {
            font-size: 1rem !important;
            font-weight: 800 !important;
            color: #32455d !important;
        }

        .stMarkdown p, .stText, .stCaption {
            font-size: 1rem !important;
        }

        div[data-testid="stMetric"] {
            background:
                linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(247,250,252,0.94) 100%);
            border: 1px solid rgba(59,130,246,0.08);
            border-radius: 22px;
            padding: 1rem;
            box-shadow:
                0 18px 34px rgba(15, 23, 42, 0.05),
                inset 0 1px 0 rgba(255,255,255,0.70);
        }

        div[data-testid="stMetricLabel"] {
            font-size: 1rem !important;
            font-weight: 800 !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.78rem !important;
            font-weight: 900 !important;
            color: #0f172a !important;
            letter-spacing: -0.03em;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.60rem;
            margin-bottom: 0.8rem;
        }

        .stTabs [data-baseweb="tab"] {
            background: rgba(255,255,255,0.90);
            border: 1px solid rgba(59,130,246,0.08);
            border-radius: 18px;
            padding: 0.68rem 1.05rem;
            font-size: 1rem;
            font-weight: 800;
            color: #334155;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.03);
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #dbeafe 0%, #e0f2fe 100%) !important;
            color: #1d4ed8 !important;
        }

        .stButton > button {
            border-radius: 18px;
            border: 1px solid rgba(59, 130, 246, 0.12);
            background:
                linear-gradient(135deg, #ffffff 0%, #f0f7ff 55%, #e0f2fe 100%);
            color: #0f172a;
            font-size: 1rem;
            font-weight: 800;
            padding: 0.68rem 1rem;
            box-shadow:
                0 12px 28px rgba(15, 23, 42, 0.06),
                inset 0 1px 0 rgba(255,255,255,0.75);
        }

        .stButton > button:hover {
            border-color: rgba(37, 99, 235, 0.22);
            color: #1d4ed8;
            transform: translateY(-1px);
            box-shadow: 0 18px 32px rgba(37, 99, 235, 0.10);
        }

        div[data-testid="stDataFrame"] {
            background: rgba(255,255,255,0.90);
            border-radius: 20px;
            padding: 0.35rem;
            box-shadow:
                0 18px 36px rgba(15, 23, 42, 0.05),
                inset 0 1px 0 rgba(255,255,255,0.65);
            border: 1px solid rgba(59,130,246,0.06);
        }

        .sidebar-card {
            background:
                linear-gradient(180deg, rgba(255,255,255,0.78) 0%, rgba(255,255,255,0.64) 100%);
            border-radius: 24px;
            padding: 1rem;
            border: 1px solid rgba(59, 130, 246, 0.08);
            box-shadow:
                0 16px 30px rgba(15, 23, 42, 0.05),
                inset 0 1px 0 rgba(255,255,255,0.70);
            margin-bottom: 1rem;
            backdrop-filter: blur(12px);
        }

        .chart-shell {
            background: linear-gradient(180deg, rgba(255,255,255,0.94) 0%, rgba(248,250,252,0.92) 100%);
            border: 1px solid rgba(59,130,246,0.08);
            border-radius: 26px;
            padding: 1.1rem 1.1rem 0.8rem 1.1rem;
            box-shadow:
                0 20px 40px rgba(15, 23, 42, 0.05),
                inset 0 1px 0 rgba(255,255,255,0.72);
            margin-top: 0.8rem;
            margin-bottom: 1.1rem;
        }

        .chart-title {
            font-size: 1.15rem;
            font-weight: 900;
            color: #0f172a;
            margin-bottom: 0.2rem;
            letter-spacing: -0.02em;
        }

        .chart-subtitle {
            font-size: 0.94rem;
            color: #64748b;
            margin-bottom: 0.85rem;
        }

        .status-card {
            background: linear-gradient(135deg, rgba(255,255,255,0.97) 0%, rgba(241,245,249,0.95) 100%);
            border: 1px solid rgba(148,163,184,0.14);
            border-radius: 22px;
            padding: 1rem;
            box-shadow: 0 10px 24px rgba(15,23,42,0.05);
            min-height: 132px;
        }

        .status-card-title {
            font-size: 0.88rem;
            font-weight: 800;
            color: #64748b;
            margin-bottom: 0.35rem;
        }

        .status-card-value {
            font-size: 2rem;
            font-weight: 900;
            color: #0f172a;
            letter-spacing: -0.03em;
            margin-bottom: 0.22rem;
        }

        .status-card-text {
            font-size: 0.92rem;
            color: #64748b;
            line-height: 1.45;
        }

        .status-card-pendiente {
            border-top: 4px solid #f59e0b;
        }

        .status-card-pagada {
            border-top: 4px solid #10b981;
        }

        .status-card-vencida {
            border-top: 4px solid #ef4444;
        }

    </style>
    """, unsafe_allow_html=True)

def mostrar_hero():
    empresa = st.session_state.get("empresa_activa", {})
    usuario = st.session_state.get("usuario", {})

    ruta_logo = obtener_logo_efix()
    logo_html = ""

    if ruta_logo:
        logo_base64 = imagen_a_base64(ruta_logo)
        if logo_base64:
            logo_html = (
                '<div style="display:flex; justify-content:flex-start; margin-bottom:1.2rem;">'
                f'<img src="data:image/png;base64,{logo_base64}" '
                'style="max-width:240px; max-height:82px; object-fit:contain;">'
                '</div>'
            )

    hero_html = (
        '<div style="'
        'position:relative;'
        'overflow:hidden;'
        'border-radius:34px;'
        'padding:2rem;'
        'margin-top:0.4rem;'
        'margin-bottom:1.6rem;'
        'background:radial-gradient(circle at top right, rgba(56,189,248,0.18), transparent 26%),'
        'linear-gradient(135deg, #0f172a 0%, #1d4ed8 58%, #0ea5e9 100%);'
        'box-shadow:0 24px 60px rgba(37,99,235,0.18);'
        '">'
            '<div style="'
            'position:absolute;'
            'inset:0;'
            'background:linear-gradient(120deg, rgba(255,255,255,0.05), transparent 40%),'
            'radial-gradient(circle at bottom left, rgba(255,255,255,0.08), transparent 28%);'
            'pointer-events:none;'
            '"></div>'

            '<div style="position:relative; z-index:2;">'
                f'{logo_html}'

                '<div style="'
                'display:inline-block;'
                'padding:0.42rem 0.85rem;'
                'border-radius:999px;'
                'background:rgba(255,255,255,0.12);'
                'color:#e0f2fe;'
                'font-size:0.92rem;'
                'font-weight:800;'
                'margin-bottom:1rem;'
                '">'
                    'Plataforma financiera inteligente'
                '</div>'

                '<div style="'
                'font-size:2.5rem;'
                'font-weight:900;'
                'color:white;'
                'line-height:1.02;'
                'letter-spacing:-0.05em;'
                'margin-bottom:0.7rem;'
                'max-width:760px;'
                '">'
                    'El cerebro financiero de tu empresa'
                '</div>'

                '<div style="'
                'font-size:1.06rem;'
                'color:rgba(255,255,255,0.88);'
                'line-height:1.7;'
                'max-width:760px;'
                'margin-bottom:1.35rem;'
                '">'
                    'Gestiona importaciones, incidencias, fianzas, tesorería y control financiero '
                    'desde una interfaz mucho más limpia, moderna y agradable de usar.'
                '</div>'

                '<div style="display:flex; flex-wrap:wrap; gap:12px;">'
                    '<div style="'
                    'background:rgba(255,255,255,0.12);'
                    'border:1px solid rgba(255,255,255,0.14);'
                    'border-radius:18px;'
                    'padding:0.85rem 1rem;'
                    'color:white;'
                    'min-width:220px;'
                    '">'
                        '<div style="font-size:0.82rem; opacity:0.72;">Usuario activo</div>'
                        f'<div style="font-size:1rem; font-weight:800;">{usuario.get("username", "")}</div>'
                    '</div>'

                    '<div style="'
                    'background:rgba(255,255,255,0.12);'
                    'border:1px solid rgba(255,255,255,0.14);'
                    'border-radius:18px;'
                    'padding:0.85rem 1rem;'
                    'color:white;'
                    'min-width:240px;'
                    '">'
                        '<div style="font-size:0.82rem; opacity:0.72;">Empresa activa</div>'
                        f'<div style="font-size:1rem; font-weight:800;">{empresa.get("nombre", "")}</div>'
                    '</div>'
                '</div>'
            '</div>'
        '</div>'
    )

    st.markdown(hero_html, unsafe_allow_html=True)

def generar_email_recordatorio_cobro(nombre_cliente, factura_id, importe, fecha_factura):
    asunto = f"Recordatorio de pago - Factura {factura_id}"

    cuerpo = (
        f"Estimado/a {nombre_cliente},\n\n"
        f"Le escribimos para recordarle que la factura {factura_id}, emitida con fecha {fecha_factura}, "
        f"por importe de {importe:.2f} €, figura actualmente como pendiente de cobro.\n\n"
        f"Le agradeceríamos que revisara el estado del pago y, en caso de estar ya realizado, "
        f"nos lo indicara para actualizar nuestro registro.\n\n"
        f"Quedamos a su disposición para cualquier aclaración.\n\n"
        f"Un saludo,\nAdministración"
    )

    return asunto, cuerpo


def generar_email_envio_factura(nombre_cliente, factura_id, importe, fecha_factura):
    asunto = f"Envío de factura {factura_id}"

    cuerpo = (
        f"Estimado/a {nombre_cliente},\n\n"
        f"Le remitimos la factura {factura_id}, de fecha {fecha_factura}, "
        f"por importe de {importe:.2f} €.\n\n"
        f"Quedamos a su disposición para cualquier consulta.\n\n"
        f"Un saludo,\nAdministración"
    )

    return asunto, cuerpo


def generar_email_proveedor(nombre_proveedor, factura_id, importe, fecha_factura):
    asunto = f"Revisión de factura proveedor {factura_id}"

    cuerpo = (
        f"Estimado/a {nombre_proveedor},\n\n"
        f"Estamos revisando la factura {factura_id}, con fecha {fecha_factura}, "
        f"por importe de {importe:.2f} €.\n\n"
        f"Le agradeceríamos confirmación del estado o cualquier aclaración adicional.\n\n"
        f"Un saludo,\nAdministración"
    )

    return asunto, cuerpo


def acciones_sugeridas_pyme():
    acciones = []

    try:
        df_cobros = facturas_pendientes()
        if not df_cobros.empty:
            df_ventas = df_cobros[df_cobros["tipo"] == "venta"].copy()
            for _, row in df_ventas.iterrows():
                acciones.append({
                    "Tipo": "Cobro pendiente",
                    "Prioridad": "Media",
                    "Referencia": f"Factura {row['id']}",
                    "Tercero": row["nombre_tercero"],
                    "Acción sugerida": "Revisar cobro o enviar recordatorio",
                    "Detalle": f"{row['total']:.2f} € | {row['fecha_emision']}"
                })

            df_compras = df_cobros[df_cobros["tipo"] == "compra"].copy()
            for _, row in df_compras.iterrows():
                acciones.append({
                    "Tipo": "Pago pendiente",
                    "Prioridad": "Media",
                    "Referencia": f"Factura {row['id']}",
                    "Tercero": row["nombre_tercero"],
                    "Acción sugerida": "Revisar pago a proveedor",
                    "Detalle": f"{row['total']:.2f} € | {row['fecha_emision']}"
                })
    except Exception:
        pass

    try:
        df_banco = movimientos_pendientes()
        for _, row in df_banco.iterrows():
            acciones.append({
                "Tipo": "Banco pendiente",
                "Prioridad": "Alta",
                "Referencia": f"Movimiento {row['id']}",
                "Tercero": "-",
                "Acción sugerida": "Conciliar movimiento",
                "Detalle": f"{row['fecha']} | {row['concepto']} | {row['importe']:.2f} €"
            })
    except Exception:
        pass

    if not acciones:
        return pd.DataFrame(columns=["Tipo", "Prioridad", "Referencia", "Tercero", "Acción sugerida", "Detalle"])

    return pd.DataFrame(acciones)

def _normalizar_texto_conciliacion(texto):
    import re

    txt = str(texto or "").lower().strip()
    txt = txt.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    txt = re.sub(r"[^a-z0-9\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _tokens_relevantes_conciliacion(texto):
    stopwords = {
        "de", "del", "la", "las", "el", "los", "por", "para", "con", "sin", "una", "uno",
        "un", "y", "o", "en", "al", "se", "su", "sus", "a", "e", "transferencia", "traspaso",
        "pago", "cobro", "factura", "recibo", "banco", "ingreso"
    }

    txt = _normalizar_texto_conciliacion(texto)
    tokens = [t for t in txt.split() if len(t) >= 3 and t not in stopwords]
    return set(tokens)


def _score_similitud_conciliacion(concepto_movimiento, nombre_tercero, concepto_factura):
    tokens_mov = _tokens_relevantes_conciliacion(concepto_movimiento)
    tokens_ter = _tokens_relevantes_conciliacion(nombre_tercero)
    tokens_fac = _tokens_relevantes_conciliacion(concepto_factura)

    score = 0

    # Coincidencias del tercero dentro del movimiento
    score += 4 * len(tokens_mov.intersection(tokens_ter))

    # Coincidencias entre concepto del movimiento y concepto de factura
    score += 2 * len(tokens_mov.intersection(tokens_fac))

    # Bonus si el nombre del tercero aparece más o menos directo
    nombre_simple = _normalizar_texto_conciliacion(nombre_tercero)
    mov_simple = _normalizar_texto_conciliacion(concepto_movimiento)

    if nombre_simple and nombre_simple in mov_simple:
        score += 8

    return score
def _preseleccionar_facturas(df, importe_movimiento):
    df = df.copy()

    # Solo candidatas con score > 0
    df_validas = df[df["score_similitud"] > 0].copy()

    if df_validas.empty:
        return [], {}

    df_validas = df_validas.sort_values(by="score_similitud", ascending=False)

    restante = float(importe_movimiento)

    seleccionadas_ids = []
    importes = {}

    for _, row in df_validas.iterrows():
        factura_id = int(row["id"])
        total_factura = float(row["total"])

        if restante <= 0:
            break

        aplicar = min(total_factura, restante)

        if aplicar > 0:
            seleccionadas_ids.append(factura_id)
            importes[factura_id] = aplicar
            restante -= aplicar

    return seleccionadas_ids, importes

# =========================================================
# PANTALLAS DE BLOQUES
# =========================================================

def pantalla_panel_control():
    st.markdown('<div class="block-chip">Visión general</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Panel de control</div>', unsafe_allow_html=True)
    st.caption("Un resumen más visual, claro y moderno del estado de tu sistema.")

    try:
        resumen = resumen_conciliacion()
    except Exception:
        resumen = {
            "movimientos_pendientes": 0,
            "facturas_pendientes": 0,
            "conciliaciones_realizadas": 0
        }

    try:
        df_control = validar_sistema_completo()
        inicializar_incidencias_control_revisadas()

        if df_control.empty:
            df_control_activo = df_control.copy()
        else:
            revisadas_global = []

            for _, row in df_control.iterrows():
                asiento_id_tmp = row.get("asiento_id")
                tipo_tmp = row.get("tipo")
                detalle_tmp = row.get("detalle")

                if pd.isna(asiento_id_tmp):
                    revisadas_global.append(False)
                else:
                    revisadas_global.append(
                        incidencia_control_ya_revisada(
                            int(asiento_id_tmp),
                            str(tipo_tmp),
                            str(detalle_tmp)
                        )
                    )

            if len(revisadas_global) == len(df_control):
                df_control_activo = df_control[[not x for x in revisadas_global]].copy()
            else:
                df_control_activo = df_control.copy()

        incidencias = 0 if df_control_activo.empty else len(df_control_activo)

    except Exception:
        incidencias = 0
        df_control = pd.DataFrame()
        df_control_activo = pd.DataFrame()

    try:
        df_inmo = ver_inmovilizado()
        total_bienes = 0 if df_inmo.empty else len(df_inmo)
    except Exception:
        total_bienes = 0

    estado = "Correcto"
    if incidencias > 0 or resumen["movimientos_pendientes"] > 0:
        estado = "Revisar"

    st.markdown("""
        <style>
        .kpi-card {
            background: rgba(255,255,255,0.82);
            border: 1px solid rgba(59,130,246,0.08);
            border-radius: 24px;
            padding: 1.15rem;
            box-shadow: 0 18px 34px rgba(15,23,42,0.05);
            backdrop-filter: blur(12px);
            min-height: 145px;
        }
        .kpi-label {
            font-size: 0.92rem;
            color: #5b6b80;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .kpi-value {
            font-size: 2rem;
            font-weight: 900;
            color: #0f172a;
            letter-spacing: -0.04em;
            margin-bottom: 0.35rem;
        }
        .kpi-meta {
            font-size: 0.94rem;
            color: #64748b;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Estado general</div>
                <div class="kpi-value">{estado}</div>
                <div class="kpi-meta">Situación global del sistema</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Incidencias</div>
                <div class="kpi-value">{incidencias}</div>
                <div class="kpi-meta">Control contable e inconsistencias</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Banco pendiente</div>
                <div class="kpi-value">{resumen["movimientos_pendientes"]}</div>
                <div class="kpi-meta">Movimientos por conciliar</div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Facturas pendientes</div>
                <div class="kpi-value">{resumen["facturas_pendientes"]}</div>
                <div class="kpi-meta">Cobros o pagos sin cerrar</div>
            </div>
        """, unsafe_allow_html=True)

    col5, col6 = st.columns(2)

    with col5:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Conciliaciones</div>
                <div class="kpi-value">{resumen["conciliaciones_realizadas"]}</div>
                <div class="kpi-meta">Procesos conciliados correctamente</div>
            </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Bienes inmovilizado</div>
                <div class="kpi-value">{total_bienes}</div>
                <div class="kpi-meta">Elementos registrados en la base</div>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("Comprobar sistema"):
            try:
                df_revision = validar_sistema_completo()

                if df_revision.empty:
                    st.success("No se detectaron incidencias contables.")
                else:
                    st.warning(f"Se detectaron {len(df_revision)} incidencias contables.")
                    st.dataframe(df_revision, use_container_width=True)
            except Exception as e:
                st.error(str(e))

    with col_b:
        if st.button("Auto-conciliar banco"):
            try:
                resultado = auto_conciliar_por_ia(score_minimo=0.85)
                if resultado.empty:
                    st.info("No hubo conciliaciones automáticas.")
                else:
                    st.success("Conciliación ejecutada.")
                    st.dataframe(resultado, use_container_width=True)
            except Exception as e:
                st.error(str(e))

    tab1, tab2 = st.tabs(["Incidencias", "Banco pendiente"])

    with tab1:
        if df_control_activo.empty:
            st.success("No hay incidencias.")
        else:
            st.dataframe(df_control_activo, use_container_width=True)

    with tab2:
        try:
            df_mov = movimientos_pendientes()
            if df_mov.empty:
                st.success("No hay movimientos pendientes.")
            else:
                st.dataframe(df_mov, use_container_width=True)
        except Exception as e:
            st.error(str(e))

def obtener_trimestre_desde_fecha(fecha_txt):
    fecha_txt = str(fecha_txt or "").strip()

    if not fecha_txt:
        return None

    try:
        fecha = datetime.datetime.strptime(fecha_txt, "%Y-%m-%d")
    except Exception:
        return None

    mes = fecha.month

    if 1 <= mes <= 3:
        return 1
    elif 4 <= mes <= 6:
        return 2
    elif 7 <= mes <= 9:
        return 3
    else:
        return 4


def obtener_info_liquidacion_igic(trimestre, year):
    if trimestre == 1:
        return {
            "label": f"1T {year}",
            "periodo": "Enero - Marzo",
            "presentacion": f"1-15 abril {year}",
            "pago": f"20 abril {year}",
            "modelo_url": "https://www3.gobiernodecanarias.org/tributos/atc/w/modelo-420",
            "sede_url": "https://sede.gobiernodecanarias.org/sede/tramites/4015",
            "calendario_url": "https://www3.gobiernodecanarias.org/tributos/atc/2026-/-plazos-de-presentaci%C3%B3n-telem%C3%A1tica-con-domiciliaci%C3%B3n-bancaria"
        }

    elif trimestre == 2:
        return {
            "label": f"2T {year}",
            "periodo": "Abril - Junio",
            "presentacion": f"1-15 julio {year}",
            "pago": f"20 julio {year}",
            "modelo_url": "https://www3.gobiernodecanarias.org/tributos/atc/w/modelo-420",
            "sede_url": "https://sede.gobiernodecanarias.org/sede/tramites/4015",
            "calendario_url": "https://www3.gobiernodecanarias.org/tributos/atc/2026-/-plazos-de-presentaci%C3%B3n-telem%C3%A1tica-con-domiciliaci%C3%B3n-bancaria"
        }

    elif trimestre == 3:
        return {
            "label": f"3T {year}",
            "periodo": "Julio - Septiembre",
            "presentacion": f"1-15 octubre {year}",
            "pago": f"20 octubre {year}",
            "modelo_url": "https://www3.gobiernodecanarias.org/tributos/atc/w/modelo-420",
            "sede_url": "https://sede.gobiernodecanarias.org/sede/tramites/4015",
            "calendario_url": "https://www3.gobiernodecanarias.org/tributos/atc/2026-/-plazos-de-presentaci%C3%B3n-telem%C3%A1tica-con-domiciliaci%C3%B3n-bancaria"
        }

    elif trimestre == 4:
        return {
            "label": f"4T {year}",
            "periodo": "Octubre - Diciembre",
            "presentacion": f"1-25 enero {year + 1}",
            "pago": f"31 enero {year + 1}",
            "modelo_url": "https://www3.gobiernodecanarias.org/tributos/atc/w/modelo-420",
            "sede_url": "https://sede.gobiernodecanarias.org/sede/tramites/4015",
            "calendario_url": "https://www3.gobiernodecanarias.org/tributos/atc/2026-/-plazos-de-presentaci%C3%B3n-telem%C3%A1tica-con-domiciliaci%C3%B3n-bancaria"
        }

    return {
        "label": f"{trimestre}T {year}",
        "periodo": "",
        "presentacion": "",
        "pago": "",
        "modelo_url": "https://www3.gobiernodecanarias.org/tributos/atc/w/modelo-420",
        "sede_url": "https://sede.gobiernodecanarias.org/sede/tramites/4015",
        "calendario_url": "https://www3.gobiernodecanarias.org/tributos/atc/2026-/-plazos-de-presentaci%C3%B3n-telem%C3%A1tica-con-domiciliaci%C3%B3n-bancaria"
    }


def calcular_resumen_igic_por_trimestres(cursor, year=None):
    if year is None:
        year = datetime.datetime.today().year

    cursor.execute("""
        SELECT a.id, a.fecha, l.cuenta, l.movimiento, l.importe
        FROM lineas_asiento l
        INNER JOIN asientos a
            ON a.id = l.asiento_id
        WHERE substr(a.fecha, 1, 4) = %s
        ORDER BY a.fecha ASC, a.id ASC
    """, (str(year),))

    lineas = cursor.fetchall()

    resumen = {
        1: {"repercutido": 0.0, "soportado": 0.0},
        2: {"repercutido": 0.0, "soportado": 0.0},
        3: {"repercutido": 0.0, "soportado": 0.0},
        4: {"repercutido": 0.0, "soportado": 0.0},
    }

    for _asiento_id, fecha, cuenta, movimiento, importe in lineas:
        trimestre = obtener_trimestre_desde_fecha(fecha)

        if trimestre is None:
            continue

        cuenta = str(cuenta or "").strip()
        movimiento = str(movimiento or "").strip().lower()
        importe = float(importe or 0)

        if cuenta.startswith("477"):
            if movimiento == "haber":
                resumen[trimestre]["repercutido"] += importe
            else:
                resumen[trimestre]["repercutido"] -= importe

        if cuenta.startswith("472"):
            if movimiento == "debe":
                resumen[trimestre]["soportado"] += importe
            else:
                resumen[trimestre]["soportado"] -= importe

    for trimestre in resumen:
        resumen[trimestre]["repercutido"] = round(resumen[trimestre]["repercutido"], 2)
        resumen[trimestre]["soportado"] = round(resumen[trimestre]["soportado"], 2)
        resumen[trimestre]["resultado"] = round(
            resumen[trimestre]["repercutido"] - resumen[trimestre]["soportado"],
            2
        )

    return resumen

def pintar_resumen_anual_igic(resumen_igic_trimestres, year_actual):
    total_repercutido = round(sum(v["repercutido"] for v in resumen_igic_trimestres.values()), 2)
    total_soportado = round(sum(v["soportado"] for v in resumen_igic_trimestres.values()), 2)
    total_resultado = round(sum(v["resultado"] for v in resumen_igic_trimestres.values()), 2)

    st.caption("Resumen fiscal del ejercicio")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Repercutido", f"{total_repercutido:,.2f} €")

    with col2:
        st.metric("Soportado", f"{total_soportado:,.2f} €")

    with col3:
        etiqueta = "A ingresar" if total_resultado > 0 else "A compensar" if total_resultado < 0 else "Equilibrado"
        st.metric("Resultado", f"{total_resultado:,.2f} €", etiqueta)

def pintar_card_trimestre_igic(info, datos):
    repercutido = round(float(datos.get("repercutido", 0.0)), 2)
    soportado = round(float(datos.get("soportado", 0.0)), 2)
    resultado = round(float(datos.get("resultado", 0.0)), 2)

    if resultado > 0:
        estado = "A ingresar"
        caja_estado = st.error
    elif resultado < 0:
        estado = "A compensar"
        caja_estado = st.success
    else:
        estado = "Equilibrado"
        caja_estado = st.info

    with st.container(border=True):
        st.markdown(f"### {info['label']}")
        st.caption(info["periodo"])

        caja_estado(f"Estado del trimestre: **{estado}**")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Repercutido", f"{repercutido:,.2f} €")

        with col2:
            st.metric("Soportado", f"{soportado:,.2f} €")

        with col3:
            st.metric("Resultado", f"{resultado:,.2f} €")

        st.markdown("#### Liquidación")
        st.write(f"**Presentación:** {info['presentacion']}")
        st.write(f"**Pago límite:** {info['pago']}")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.link_button("Modelo 420", info["modelo_url"], use_container_width=True)

        with c2:
            st.link_button("Presentación", info["sede_url"], use_container_width=True)

        with c3:
            st.link_button("Calendario ATC", info["calendario_url"], use_container_width=True)

def pantalla_resumen_financiero(cursor):
    st.markdown('<div class="block-chip">Indicadores</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Resumen financiero</div>', unsafe_allow_html=True)

    conexion_resumen = get_connection()
    cursor_resumen = conexion_resumen.cursor()

    try:
        cursor_resumen.execute("""
        SELECT cuenta, movimiento, importe
        FROM lineas_asiento
        """)
        lineas = cursor_resumen.fetchall()

        year_actual = datetime.datetime.today().year
        resumen_igic_trimestres = calcular_resumen_igic_por_trimestres(cursor_resumen, year_actual)
    finally:
        conexion_resumen.close()

    ventas = 0
    compras = 0
    igic_repercutido = 0
    igic_soportado = 0
    bancos = 0
    clientes = 0
    proveedores = 0

    for cuenta, movimiento, importe in lineas:
        cuenta = str(cuenta).strip()
        importe = float(importe)

        if cuenta.startswith("7"):
            ventas += importe if movimiento == "haber" else -importe

        if cuenta.startswith("6"):
            compras += importe if movimiento == "debe" else -importe

        if cuenta.startswith("477"):
            igic_repercutido += importe if movimiento == "haber" else -importe

        if cuenta.startswith("472"):
            igic_soportado += importe if movimiento == "debe" else -importe

        if cuenta.startswith("572"):
            bancos += importe if movimiento == "debe" else -importe

        if cuenta.startswith("43"):
            clientes += importe if movimiento == "debe" else -importe

        if cuenta.startswith("40"):
            proveedores += importe if movimiento == "haber" else -importe

    beneficio = ventas - compras
    igic_pagar = igic_repercutido - igic_soportado

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ventas totales", f"{ventas:.2f} €")
        st.metric("IGIC repercutido", f"{igic_repercutido:.2f} €")
    with col2:
        st.metric("Compras totales", f"{compras:.2f} €")
        st.metric("IGIC soportado", f"{igic_soportado:.2f} €")
    with col3:
        st.metric("Beneficio bruto", f"{beneficio:.2f} €")
        st.metric("IGIC a pagar", f"{igic_pagar:.2f} €")
    

    filas_igic = []

    for trimestre in [1, 2, 3, 4]:
        info = obtener_info_liquidacion_igic(trimestre, year_actual)
        datos = resumen_igic_trimestres[trimestre]

        filas_igic.append({
            "Trimestre": info["label"],
            "Periodo": info["periodo"],
            "IGIC repercutido": datos["repercutido"],
            "IGIC soportado": datos["soportado"],
            "Resultado": datos["resultado"],
            "Presentación": info["presentacion"],
            "Pago límite": info["pago"],
        })

    # =========================
    # IGIC ANUAL
    # =========================
    st.subheader("IGIC anual")

    pintar_resumen_anual_igic(resumen_igic_trimestres, year_actual)

    st.divider()

    # =========================
    # IGIC POR TRIMESTRES
    # =========================
    st.subheader("IGIC por trimestres")

    col1, col2 = st.columns(2)

    for i, trimestre in enumerate([1, 2, 3, 4]):
        info = obtener_info_liquidacion_igic(trimestre, year_actual)
        datos = resumen_igic_trimestres[trimestre]

        if i % 2 == 0:
            with col1:
                pintar_card_trimestre_igic(info, datos)
        else:
            with col2:
                pintar_card_trimestre_igic(info, datos)

    for trimestre in [1, 2, 3, 4]:
        info = obtener_info_liquidacion_igic(trimestre, year_actual)
        datos = resumen_igic_trimestres[trimestre]

        with st.expander(f"{info['label']} | Liquidación IGIC"):
            st.write(f"**Periodo:** {info['periodo']}")
            st.write(f"**IGIC repercutido:** {datos['repercutido']:.2f} €")
            st.write(f"**IGIC soportado:** {datos['soportado']:.2f} €")
            st.write(f"**Resultado:** {datos['resultado']:.2f} €")
            st.write(f"**Presentación:** {info['presentacion']}")
            st.write(f"**Pago límite:** {info['pago']}")

            st.markdown(f"[Modelo 420 - ATC]({info['modelo_url']})")
            st.markdown(f"[Sede electrónica - presentación]({info['sede_url']})")
            st.markdown(f"[Calendario oficial ATC]({info['calendario_url']})")

    st.subheader("Tesorería")
    st.metric("Saldo en bancos", f"{bancos:.2f} €")

    c4, c5 = st.columns(2)
    with c4:
        st.metric("Saldo clientes", f"{clientes:.2f} €")
    with c5:
        st.metric("Saldo proveedores", f"{proveedores:.2f} €")

    ventas_chart = 0.0
    compras_chart = 0.0
    bancos_chart = 0.0
    clientes_chart = 0.0
    proveedores_chart = 0.0

    try:
        cursor.execute("""
            SELECT cuenta, movimiento, importe
            FROM lineas_asiento
            ORDER BY id
        """)
        lineas_chart = cursor.fetchall()

        for cuenta, movimiento, importe in lineas_chart:
            cuenta = str(cuenta or "").strip()
            movimiento = str(movimiento or "").strip().lower()
            importe = float(importe or 0)

            if cuenta.startswith("7"):
                ventas_chart += importe if movimiento == "haber" else -importe
            elif cuenta.startswith("6"):
                compras_chart += importe if movimiento == "debe" else -importe
            elif cuenta.startswith("572"):
                bancos_chart += importe if movimiento == "debe" else -importe
            elif cuenta.startswith("43"):
                clientes_chart += importe if movimiento == "debe" else -importe
            elif cuenta.startswith("40"):
                proveedores_chart += importe if movimiento == "haber" else -importe

    except Exception as e:
        st.warning(f"No se pudo calcular el gráfico desde lineas_asiento: {e}")

    df_resumen_real = pd.DataFrame({
        "Categoría": [
            "Ventas (7)",
            "Compras (6)",
            "Bancos (572)",
            "Clientes (43)",
            "Proveedores (40)"
        ],
        "Importe": [
            ventas_chart,
            compras_chart,
            bancos_chart,
            clientes_chart,
            proveedores_chart
        ]
    })

    st.markdown("""
        <div class="chart-shell">
            <div class="chart-title">Visión general por cuentas reales</div>
            <div class="chart-subtitle">
                Distribución visual de ventas, compras, bancos, clientes y proveedores sobre contabilidad real.
            </div>
        </div>
    """, unsafe_allow_html=True)

    if PLOTLY_DISPONIBLE:
        fig_bar = px.bar(
            df_resumen_real,
            x="Categoría",
            y="Importe",
            text="Importe"
        )

        fig_bar.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            marker_line_width=0
        )

        fig_bar.update_layout(
            height=440,
            plot_bgcolor="rgba(255,255,255,0.00)",
            paper_bgcolor="rgba(255,255,255,0)",
            margin=dict(l=20, r=20, t=10, b=20),
            xaxis_title="",
            yaxis_title="Importe (€)",
            yaxis=dict(
                gridcolor="rgba(148,163,184,0.20)",
                zerolinecolor="rgba(148,163,184,0.25)"
            ),
            xaxis=dict(
                tickfont=dict(size=12)
            ),
            showlegend=False
        )

        st.plotly_chart(
            fig_bar,
            use_container_width=True,
            key="grafico_cuentas_reales"
        )
    else:
        st.bar_chart(
            df_resumen_real.set_index("Categoría"),
            use_container_width=True
        )

    pendientes = 0
    pagadas = 0
    vencidas = 0

    try:
        cursor.execute("SELECT estado, fecha_vencimiento FROM facturas")
        filas_fact = cursor.fetchall()

        for estado, fecha_vencimiento in filas_fact:
            estado_vis, _badge = estado_factura_visual(estado, fecha_vencimiento)
            if estado_vis == "Pendiente":
                pendientes += 1
            elif estado_vis == "Pagada":
                pagadas += 1
            elif estado_vis == "Vencida":
                vencidas += 1
    except Exception:
        pass

    total_facturas_estado = pendientes + pagadas + vencidas

    st.markdown("""
        <div class="chart-shell">
            <div class="chart-title">Estado global de facturas</div>
            <div class="chart-subtitle">
                Vista rápida del estado documental de la cartera de facturas.
            </div>
        </div>
    """, unsafe_allow_html=True)

    c_estado_1, c_estado_2, c_estado_3 = st.columns(3)

    with c_estado_1:
        st.markdown(f"""
            <div class="status-card status-card-pendiente">
                <div class="status-card-title">Pendientes</div>
                <div class="status-card-value">{pendientes}</div>
                <div class="status-card-text">Facturas todavía abiertas o por completar.</div>
            </div>
        """, unsafe_allow_html=True)

    with c_estado_2:
        st.markdown(f"""
            <div class="status-card status-card-pagada">
                <div class="status-card-title">Pagadas</div>
                <div class="status-card-value">{pagadas}</div>
                <div class="status-card-text">Facturas cerradas correctamente en el sistema.</div>
            </div>
        """, unsafe_allow_html=True)

    with c_estado_3:
        st.markdown(f"""
            <div class="status-card status-card-vencida">
                <div class="status-card-title">Vencidas</div>
                <div class="status-card-value">{vencidas}</div>
                <div class="status-card-text">Facturas que requieren atención o revisión prioritaria.</div>
            </div>
        """, unsafe_allow_html=True)

    df_estado = pd.DataFrame({
        "Estado": ["Pendientes", "Pagadas", "Vencidas"],
        "Cantidad": [pendientes, pagadas, vencidas]
    })

    if total_facturas_estado > 0:
        if PLOTLY_DISPONIBLE:
            col_g1, col_g2 = st.columns([1.15, 0.85])

            with col_g1:
                fig_estado_bar = px.bar(
                    df_estado,
                    x="Cantidad",
                    y="Estado",
                    orientation="h",
                    text="Cantidad"
                )

                fig_estado_bar.update_traces(
                    textposition="outside",
                    marker_line_width=0
                )

                fig_estado_bar.update_layout(
                    height=340,
                    plot_bgcolor="rgba(255,255,255,0.00)",
                    paper_bgcolor="rgba(255,255,255,0)",
                    margin=dict(l=20, r=20, t=10, b=10),
                    xaxis_title="Cantidad",
                    yaxis_title="",
                    showlegend=False
                )

                st.plotly_chart(
                    fig_estado_bar,
                    use_container_width=True,
                    key="grafico_estado_facturas_bar"
                )

            with col_g2:
                fig_estado_donut = px.pie(
                    df_estado,
                    names="Estado",
                    values="Cantidad",
                    hole=0.65
                )

                fig_estado_donut.update_traces(
                    textinfo="percent+label"
                )

                fig_estado_donut.update_layout(
                    height=340,
                    plot_bgcolor="rgba(255,255,255,0.00)",
                    paper_bgcolor="rgba(255,255,255,0)",
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=False,
                    annotations=[
                        dict(
                            text=f"{total_facturas_estado}<br>facturas",
                            x=0.5,
                            y=0.5,
                            font_size=18,
                            showarrow=False
                        )
                    ]
                )

                st.plotly_chart(
                    fig_estado_donut,
                    use_container_width=True,
                    key="grafico_estado_facturas_donut"
                )
        else:
            st.bar_chart(
                df_estado.set_index("Estado"),
                use_container_width=True
            )
    else:
        st.info("No hay facturas suficientes para representar el estado global.")


def normalizar_texto_fianza(texto):
    texto = str(texto or "").strip().lower()
    texto = texto.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return texto


def extraer_importes_desde_texto_fianza(texto):
    import re

    texto_original = str(texto or "").strip()
    texto = normalizar_texto_fianza(texto_original)

    candidatos_prioritarios = []
    candidatos_generales = []

    patrones_contexto = [
        r'fianza\s*(?:de)?\s*(\d+(?:[.,]\d{1,2})?)',
        r'deposito\s*(?:de)?\s*(\d+(?:[.,]\d{1,2})?)',
        r'garantia\s*(?:de)?\s*(\d+(?:[.,]\d{1,2})?)',
        r'(\d+(?:[.,]\d{1,2})?)\s*€?\s*(?:de\s*)?fianza',
        r'(\d+(?:[.,]\d{1,2})?)\s*€?\s*(?:de\s*)?deposito',
        r'(\d+(?:[.,]\d{1,2})?)\s*€?\s*(?:de\s*)?garantia',
    ]

    for patron in patrones_contexto:
        encontrados = re.findall(patron, texto)
        for item in encontrados:
            try:
                valor = round(float(str(item).replace(",", ".")), 2)
                if 0 < valor < 100000 and valor not in candidatos_prioritarios:
                    candidatos_prioritarios.append(valor)
            except Exception:
                pass

    encontrados_generales = re.findall(r'(\d+(?:[.,]\d{1,2})?)', texto)
    for item in encontrados_generales:
        try:
            valor = round(float(str(item).replace(",", ".")), 2)
            if 0 < valor < 100000 and valor not in candidatos_generales:
                candidatos_generales.append(valor)
        except Exception:
            pass

    return {
        "prioritarios": candidatos_prioritarios,
        "generales": candidatos_generales
    }


def obtener_sentido_tesoreria_asiento(cursor, asiento_id):
    cursor.execute("""
        SELECT cuenta, movimiento, importe
        FROM lineas_asiento
        WHERE asiento_id = %s
    """, (asiento_id,))

    lineas = cursor.fetchall()

    entrada = 0.0
    salida = 0.0
    cuenta_detectada = "570 Caja"

    for cuenta, movimiento, importe in lineas:
        cuenta_txt = str(cuenta or "").strip()
        movimiento_txt = str(movimiento or "").strip().lower()
        importe = float(importe or 0)

        if cuenta_txt.startswith("57"):
            cuenta_detectada = cuenta_txt

            if movimiento_txt == "debe":
                entrada += importe
            elif movimiento_txt == "haber":
                salida += importe

    if entrada > salida:
        return {
            "sentido": "entrada",
            "importe_tesoreria": round(entrada, 2),
            "cuenta_tesoreria": cuenta_detectada
        }

    if salida > entrada:
        return {
            "sentido": "salida",
            "importe_tesoreria": round(salida, 2),
            "cuenta_tesoreria": cuenta_detectada
        }

    return {
        "sentido": "neutro",
        "importe_tesoreria": 0.0,
        "cuenta_tesoreria": cuenta_detectada
    }


def analizar_asiento_fianza(cursor, asiento_id, fecha, concepto):
    from contabilidad import buscar_fianza_recibida_candidata_para_devolucion

    texto = normalizar_texto_fianza(concepto)
    importes_texto = extraer_importes_desde_texto_fianza(texto)
    tesoreria = obtener_sentido_tesoreria_asiento(cursor, asiento_id)

    palabras_fianza = ["fianza", "deposito", "garantia", "garantía", "depósito"]
    palabras_devolucion = ["devol", "reintegro", "refund", "reembolso", "cancelacion", "cancelación"]

    score_fianza = 0
    score_devolucion = 0
    motivos = []

    if any(p in texto for p in palabras_fianza):
        score_fianza += 50
        motivos.append("El concepto contiene términos típicos de fianza")

    if any(p in texto for p in palabras_devolucion):
        score_devolucion += 40
        motivos.append("El concepto contiene términos de devolución o reintegro")

    if tesoreria["sentido"] == "entrada":
        score_fianza += 25
        motivos.append("El asiento refleja entrada de tesorería")

    if tesoreria["sentido"] == "salida":
        score_devolucion += 25
        motivos.append("El asiento refleja salida de tesorería")

    importe_sugerido = 0.0

    if importes_texto["prioritarios"]:
        importe_sugerido = float(importes_texto["prioritarios"][0])
        motivos.append("Se ha detectado un importe junto a términos de fianza/deposito/garantia")
    elif importes_texto["generales"]:
        importe_sugerido = float(importes_texto["generales"][0])
        motivos.append("Se ha detectado un importe numérico en el concepto")
    else:
        importe_sugerido = float(tesoreria["importe_tesoreria"] or 0)
        motivos.append("Se usa el importe detectado en tesorería al no encontrar importe claro en el concepto")

    if score_fianza == 0 and score_devolucion == 0:
        return {
            "es_fianza": False,
            "tipo": "no_fianza",
            "confianza": "baja",
            "score": 0,
            "importe_sugerido": 0.0,
            "cuenta_tesoreria": tesoreria["cuenta_tesoreria"],
            "motivos": [],
            "fianza_origen": None
        }

    fianza_origen = None

    if score_devolucion >= score_fianza:
        fianza_origen = buscar_fianza_recibida_candidata_para_devolucion(
            cursor,
            importe_objetivo=importe_sugerido if importe_sugerido > 0 else None,
            texto_referencia=texto
        )

        if fianza_origen:
            score_devolucion += 35
            motivos.append(
                f"Se ha encontrado una fianza recibida candidata con saldo pendiente {fianza_origen['saldo_pendiente']:.2f} €"
            )

        tipo = "fianza_devuelta"
        score_final = score_devolucion
    else:
        tipo = "fianza_recibida"
        score_final = score_fianza

    confianza = "baja"
    if score_final >= 90:
        confianza = "alta"
    elif score_final >= 60:
        confianza = "media"

    return {
        "es_fianza": True,
        "tipo": tipo,
        "confianza": confianza,
        "score": score_final,
        "importe_sugerido": round(float(importe_sugerido or 0), 2),
        "cuenta_tesoreria": tesoreria["cuenta_tesoreria"] if tesoreria["cuenta_tesoreria"].startswith("57") else "570 Caja",
        "motivos": motivos,
        "fianza_origen": fianza_origen
    }

def detectar_posible_fianza_desde_concepto(concepto):
    import re

    texto = str(concepto or "").lower()

    if "fianza" not in texto:
        return {"detectada": False, "importe": 0.0}

    match = re.search(r'fianza\s*(\d+[.,]?\d*)', texto)

    if match:
        try:
            importe = float(match.group(1).replace(",", "."))
            return {"detectada": True, "importe": importe}
        except Exception:
            pass

    numeros = re.findall(r'(\d+[.,]?\d*)', texto)

    valores_validos = []
    for n in numeros:
        try:
            val = float(n.replace(",", "."))
            if val < 10000:
                valores_validos.append(val)
        except Exception:
            pass

    if valores_validos:
        return {
            "detectada": True,
            "importe": max(valores_validos)
        }

    return {"detectada": True, "importe": 0.0}

def detectar_devolucion_fianza_desde_concepto(concepto):
    import re

    texto = str(concepto or "").strip().lower()

    if not texto:
        return {"detectada": False, "importe": 0.0}

    palabras_clave = [
        "devolucion fianza",
        "devolución fianza",
        "devolver fianza",
        "se devuelve fianza",
        "devolvemos fianza",
        "devolucion de fianza",
        "devolución de fianza"
    ]

    if not ("fianza" in texto and ("devol" in texto or "refund" in texto)):
        return {"detectada": False, "importe": 0.0}

    candidatos = re.findall(r'(\d+[.,]?\d*)', texto)
    if not candidatos:
        return {"detectada": True, "importe": 0.0}

    valores = []
    for c in candidatos:
        try:
            valores.append(float(c.replace(",", ".")))
        except Exception:
            pass

    if not valores:
        return {"detectada": True, "importe": 0.0}

    return {
        "detectada": True,
        "importe": max(valores)
    }

def extraer_asiento_origen_desde_concepto_fianza(concepto):
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

def existe_fianza_asociada(asiento_id, concepto_origen):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, concepto
            FROM asientos
            WHERE tipo_operacion = 'fianza_recibida'
            ORDER BY id DESC
        """)
        filas = cursor.fetchall()

        for asiento_fianza_id, concepto_existente in filas:
            origen_detectado = extraer_asiento_origen_desde_concepto_fianza(concepto_existente)
            if origen_detectado == int(asiento_id):
                return int(asiento_fianza_id)

        concepto_fianza = f"Fianza asociada a asiento {asiento_id} - {concepto_origen}"

        cursor.execute("""
            SELECT id
            FROM asientos
            WHERE tipo_operacion = 'fianza_recibida'
              AND concepto = %s
            LIMIT 1
        """, (concepto_fianza,))

        fila = cursor.fetchone()
        return fila[0] if fila else None

    finally:
        conn.close()

def existe_devolucion_fianza_asociada(asiento_id, concepto_origen):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, concepto
            FROM asientos
            WHERE tipo_operacion = 'fianza_devuelta'
            ORDER BY id DESC
        """)
        filas = cursor.fetchall()

        for asiento_dev_id, concepto_existente in filas:
            origen_detectado = extraer_asiento_origen_desde_concepto_fianza(concepto_existente)
            if origen_detectado == int(asiento_id):
                return int(asiento_dev_id)

        concepto_dev = f"Devolución de fianza origen"

        cursor.execute("""
            SELECT id
            FROM asientos
            WHERE tipo_operacion = 'fianza_devuelta'
              AND concepto LIKE %s
            LIMIT 1
        """, (f"%asiento origen {asiento_id} - %",))

        fila = cursor.fetchone()
        return fila[0] if fila else None

    finally:
        conn.close()

def inicializar_revision_fianzas():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS revision_fianzas (
            id SERIAL PRIMARY KEY,
            asiento_origen_id INTEGER UNIQUE,
            estado TEXT,
            comentario TEXT,
            creado_en TEXT
        )
    """)

    conn.commit()
    conn.close()


def obtener_estado_revision_fianza(asiento_origen_id):
    inicializar_revision_fianzas()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT estado, comentario
        FROM revision_fianzas
        WHERE asiento_origen_id = %s
        LIMIT 1
    """, (asiento_origen_id,))

    fila = cursor.fetchone()
    conn.close()

    if not fila:
        return None, ""

    return fila[0], fila[1] or ""


def guardar_estado_revision_fianza(asiento_origen_id, estado, comentario=""):
    inicializar_revision_fianzas()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO revision_fianzas (asiento_origen_id, estado, comentario, creado_en)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT(asiento_origen_id)
        DO UPDATE SET
            estado = excluded.estado,
            comentario = excluded.comentario
    """, (asiento_origen_id, estado, comentario))

    conn.commit()
    conn.close()

def borrar_estado_revision_fianza(asiento_origen_id):
    inicializar_revision_fianzas()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM revision_fianzas
        WHERE asiento_origen_id = %s
    """, (asiento_origen_id,))

    conn.commit()
    conn.close()

def puede_crearse_operacion_fianza(fila):
    confianza = str(fila.get("Confianza", "")).strip().lower()
    tipo_sugerido = str(fila.get("Tipo sugerido", "")).strip()
    fianza_origen = fila.get("Fianza origen")

    if confianza == "baja":
        return {
            "ok": False,
            "motivo": "Confianza baja. Revisión manual obligatoria."
        }

    if tipo_sugerido == "Devolución de fianza" and pd.isna(fianza_origen):
        return {
            "ok": False,
            "motivo": "No se ha encontrado fianza origen para la devolución."
        }

    return {
        "ok": True,
        "motivo": ""
    }

def pantalla_fianzas_detectadas(cursor):
    st.markdown('<div class="section-title">Fianzas detectadas</div>', unsafe_allow_html=True)
    st.caption("Revisa, ajusta importes, marca varias y crea operaciones de fianza con detección inteligente, sin duplicados.")

    col_reset_1, col_reset_2 = st.columns([1, 3])

    with col_reset_1:
        if st.button("🧹 Limpiar selección", key="reset_estado_fianzas"):
            st.session_state["fianzas_marcadas_manualmente"] = {}
            st.session_state["fianzas_edicion_manual"] = {}
            st.success("Selección y edición manual limpiadas.")
            st.rerun()

    # =========================
    # FILTROS
    # =========================
    col_f1, col_f2 = st.columns([2, 1])

    with col_f1:
        texto_busqueda = st.text_input(
            "Buscar en concepto",
            value="",
            placeholder="Ej: fianza, depósito, cliente, alquiler, devolución...",
            key="fianzas_texto_busqueda"
        ).strip().lower()

    with col_f2:
        solo_pendientes = st.checkbox(
            "Mostrar solo pendientes de crear",
            value=True,
            key="fianzas_solo_pendientes"
        )

    # =========================
    # CARGA DE ASIENTOS ORIGEN
    # =========================
    cursor.execute("""
        SELECT id, fecha, concepto, tipo_operacion
        FROM asientos
        WHERE tipo_operacion IN ('factura_importada_excel', 'importado_excel', 'correccion_incidencia')
        ORDER BY id DESC
    """)
    asientos = cursor.fetchall()

    registros = []

    for asiento_id, fecha, concepto, tipo_operacion in asientos:
        concepto_txt = str(concepto or "").strip()

        if texto_busqueda and texto_busqueda not in concepto_txt.lower():
            continue

        analisis = analizar_asiento_fianza(cursor, asiento_id, fecha, concepto_txt)

        if not analisis["es_fianza"]:
            continue

        estado_revision, comentario_revision = obtener_estado_revision_fianza(asiento_id)

        if estado_revision == "descartada":
            continue

        asiento_fianza_existente = None
        asiento_devolucion_existente = None

        if analisis["tipo"] == "fianza_recibida":
            asiento_fianza_existente = existe_fianza_asociada(asiento_id, concepto_txt)
            ya_creada = asiento_fianza_existente is not None
        else:
            asiento_devolucion_existente = existe_devolucion_fianza_asociada(asiento_id, concepto_txt)
            ya_creada = asiento_devolucion_existente is not None

        if solo_pendientes and ya_creada:
            continue

        fianza_origen = analisis.get("fianza_origen")
        fianza_origen_id = int(fianza_origen["asiento_id"]) if fianza_origen else None
        saldo_pendiente = float(fianza_origen["saldo_pendiente"]) if fianza_origen else 0.0

        registros.append({
            "Seleccionar": False,
            "Asiento origen": int(asiento_id),
            "Fecha": str(fecha),
            "Concepto": concepto_txt,
            "Tipo sugerido": "Fianza recibida" if analisis["tipo"] == "fianza_recibida" else "Devolución de fianza",
            "Confianza": analisis["confianza"].capitalize(),
            "Importe sugerido": float(analisis["importe_sugerido"]),
            "Importe fianza": float(analisis["importe_sugerido"]),
            "Cuenta tesorería": analisis["cuenta_tesoreria"],
            "Ya creada": "Sí" if ya_creada else "No",
            "Asiento fianza": int(asiento_fianza_existente) if asiento_fianza_existente else None,
            "Asiento devolución": int(asiento_devolucion_existente) if asiento_devolucion_existente else None,
            "Fianza origen": fianza_origen_id,
            "Saldo pendiente origen": saldo_pendiente,
            "Motivos": " | ".join(analisis["motivos"])
        })

    if not registros:
        st.success("No hay operaciones de fianza detectadas para mostrar.")
        return

    df_fianzas = pd.DataFrame(registros)

    # =========================
    # ESTADO EN SESIÓN
    # =========================
    if "fianzas_marcadas_manualmente" not in st.session_state:
        st.session_state["fianzas_marcadas_manualmente"] = {}

    if "fianzas_edicion_manual" not in st.session_state:
        st.session_state["fianzas_edicion_manual"] = {}

    # aplicar edición manual persistida
    for idx, row in df_fianzas.iterrows():
        asiento_origen = int(row["Asiento origen"])

        if asiento_origen in st.session_state["fianzas_edicion_manual"]:
            ed = st.session_state["fianzas_edicion_manual"][asiento_origen]

            if "Importe fianza" in ed:
                df_fianzas.at[idx, "Importe fianza"] = float(ed["Importe fianza"])

            if "Cuenta tesorería" in ed:
                df_fianzas.at[idx, "Cuenta tesorería"] = str(ed["Cuenta tesorería"])

        df_fianzas.at[idx, "Seleccionar"] = st.session_state["fianzas_marcadas_manualmente"].get(
            asiento_origen,
            False
        )

    # =========================
    # BOTONES DE ACCIÓN RÁPIDA
    # =========================
    col_b1, col_b2, col_b3 = st.columns([1, 1, 2])

    with col_b1:
        if st.button("Marcar todas visibles", key="marcar_todas_fianzas"):
            for _, row in df_fianzas.iterrows():
                st.session_state["fianzas_marcadas_manualmente"][int(row["Asiento origen"])] = True
            st.rerun()

    with col_b2:
        if st.button("Desmarcar todas visibles", key="desmarcar_todas_fianzas"):
            for _, row in df_fianzas.iterrows():
                st.session_state["fianzas_marcadas_manualmente"][int(row["Asiento origen"])] = False
            st.rerun()

    with col_b3:
        st.write(f"**Total detectadas:** {len(df_fianzas)}")

    # =========================
    # TABLA EDITABLE
    # =========================
    df_editado = st.data_editor(
        df_fianzas,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn("Seleccionar"),
            "Asiento origen": st.column_config.NumberColumn("Asiento origen", disabled=True),
            "Fecha": st.column_config.TextColumn("Fecha", disabled=True),
            "Concepto": st.column_config.TextColumn("Concepto", disabled=True, width="large"),
            "Tipo sugerido": st.column_config.TextColumn("Tipo sugerido", disabled=True),
            "Confianza": st.column_config.TextColumn("Confianza", disabled=True),
            "Importe sugerido": st.column_config.NumberColumn("Importe sugerido", format="%.2f", disabled=True),
            "Importe fianza": st.column_config.NumberColumn("Importe fianza", format="%.2f", min_value=0.0),
            "Cuenta tesorería": st.column_config.SelectboxColumn(
                "Cuenta tesorería",
                options=["570 Caja", "572 Bancos"]
            ),
            "Ya creada": st.column_config.TextColumn("Ya creada", disabled=True),
            "Asiento fianza": st.column_config.NumberColumn("Asiento fianza", disabled=True),
            "Asiento devolución": st.column_config.NumberColumn("Asiento devolución", disabled=True),
            "Fianza origen": st.column_config.NumberColumn("Fianza origen", disabled=True),
            "Saldo pendiente origen": st.column_config.NumberColumn("Saldo pendiente origen", format="%.2f", disabled=True),
            "Motivos": st.column_config.TextColumn("Motivos", disabled=True, width="large"),
        },
        key="editor_fianzas_detectadas"
    )

    # persistir marcado y edición
    for _, row in df_editado.iterrows():
        asiento_origen = int(row["Asiento origen"])

        st.session_state["fianzas_marcadas_manualmente"][asiento_origen] = bool(row["Seleccionar"])
        st.session_state["fianzas_edicion_manual"][asiento_origen] = {
            "Importe fianza": float(row["Importe fianza"] or 0),
            "Cuenta tesorería": str(row["Cuenta tesorería"])
        }

    seleccionadas = df_editado[df_editado["Seleccionar"] == True].copy()

    # =========================
    # MÉTRICAS
    # =========================
    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        st.metric("Seleccionadas", len(seleccionadas))

    with col_m2:
        pendientes = df_editado[df_editado["Ya creada"] == "No"]
        st.metric("Pendientes visibles", len(pendientes))

    with col_m3:
        st.metric("Total visibles", len(df_editado))

    st.divider()

    # =========================
    # EDITOR INDIVIDUAL FINO
    # =========================
    st.markdown("### Editar una operación concreta")
    st.caption("Usa esta zona para revisar bien el tipo, el importe y la cuenta antes de crear la operación.")

    opciones_asiento = {
        f"Asiento {int(row['Asiento origen'])} | {row['Fecha']} | {str(row['Concepto'])[:90]}": int(row["Asiento origen"])
        for _, row in df_editado.iterrows()
    }

    asiento_edicion = st.selectbox(
        "Selecciona un asiento",
        list(opciones_asiento.keys()),
        key="selector_edicion_fianza"
    )

    asiento_edicion_id = opciones_asiento[asiento_edicion]
    fila_edicion = df_editado[df_editado["Asiento origen"] == asiento_edicion_id].iloc[0]

    concepto_edicion = str(fila_edicion["Concepto"])
    fecha_edicion = str(fila_edicion["Fecha"])
    tipo_sugerido_edicion = str(fila_edicion["Tipo sugerido"])
    confianza_edicion = str(fila_edicion["Confianza"])
    importe_sugerido_edicion = float(fila_edicion["Importe sugerido"])
    importe_actual_edicion = float(fila_edicion["Importe fianza"])
    cuenta_actual_edicion = str(fila_edicion["Cuenta tesorería"])
    ya_creada_edicion = str(fila_edicion["Ya creada"]) == "Sí"
    asiento_fianza_edicion = fila_edicion["Asiento fianza"]
    asiento_devolucion_edicion = fila_edicion["Asiento devolución"]
    fianza_origen_edicion = fila_edicion["Fianza origen"]
    saldo_pendiente_origen_edicion = float(fila_edicion["Saldo pendiente origen"] or 0)
    motivos_edicion = str(fila_edicion["Motivos"])

    st.write(f"**Asiento origen:** {asiento_edicion_id}")
    st.write(f"**Fecha:** {fecha_edicion}")
    st.write(f"**Concepto:** {concepto_edicion}")
    st.write(f"**Tipo sugerido:** {tipo_sugerido_edicion}")
    st.write(f"**Confianza:** {confianza_edicion}")
    if confianza_edicion.lower() == "alta":
        st.success("Detección sólida.")
    elif confianza_edicion.lower() == "media":
        st.info("Detección razonable. Conviene revisar antes de crear.")
    else:
        st.warning("Detección débil. No se permitirá creación automática.")
    st.write(f"**Importe sugerido detectado:** {importe_sugerido_edicion:.2f} €")

    if pd.notna(fianza_origen_edicion):
        st.write(f"**Fianza origen encontrada:** {int(fianza_origen_edicion)}")
        st.write(f"**Saldo pendiente origen:** {saldo_pendiente_origen_edicion:.2f} €")

    if motivos_edicion:
        st.info(motivos_edicion)

    col_e1, col_e2 = st.columns(2)

    with col_e1:
        nuevo_importe = st.number_input(
            "Importe de operación",
            min_value=0.0,
            step=0.01,
            value=float(importe_actual_edicion),
            key=f"editar_importe_fianza_{asiento_edicion_id}"
        )

    with col_e2:
        nueva_cuenta = st.selectbox(
            "Cuenta tesorería",
            ["570 Caja", "572 Bancos"],
            index=0 if cuenta_actual_edicion == "570 Caja" else 1,
            key=f"editar_cuenta_fianza_{asiento_edicion_id}"
        )

    col_e3, col_e4, col_e5, col_e6 = st.columns(4)

    with col_e3:
        if st.button("Guardar edición", key=f"guardar_edicion_fianza_{asiento_edicion_id}"):
            st.session_state["fianzas_edicion_manual"][int(asiento_edicion_id)] = {
                "Importe fianza": float(nuevo_importe),
                "Cuenta tesorería": nueva_cuenta
            }
            st.success("Edición guardada.")
            st.rerun()

    with col_e4:
        if st.button("Marcar esta fila", key=f"marcar_fila_fianza_{asiento_edicion_id}"):
            st.session_state["fianzas_marcadas_manualmente"][int(asiento_edicion_id)] = True
            st.success("Fila marcada.")
            st.rerun()

    with col_e5:
        estado_revision_actual, _ = obtener_estado_revision_fianza(asiento_edicion_id)

        if estado_revision_actual == "descartada":
            if st.button("Reactivar sugerencia", key=f"reactivar_fianza_{asiento_edicion_id}"):
                borrar_estado_revision_fianza(asiento_edicion_id)
                st.success("La sugerencia vuelve a estar activa.")
                st.rerun()
        else:
            if st.button("No es una fianza", key=f"descartar_fianza_{asiento_edicion_id}"):
                guardar_estado_revision_fianza(
                    asiento_origen_id=asiento_edicion_id,
                    estado="descartada",
                    comentario="Marcada manualmente como no fianza"
                )
                st.success("Marcada como no fianza. Ya no volverá a salir en pendientes.")
                st.rerun()

    with col_e6:
        validacion_creacion = puede_crearse_operacion_fianza(fila_edicion)

        if ya_creada_edicion:
            if tipo_sugerido_edicion == "Fianza recibida":
                st.info(f"Ya creada (asiento {asiento_fianza_edicion})")
            else:
                st.info(f"Ya creada (asiento {asiento_devolucion_edicion})")
        else:
            if not validacion_creacion["ok"]:
                st.warning(validacion_creacion["motivo"])
            else:
                if st.button("Crear solo esta operación", key=f"crear_una_fianza_{asiento_edicion_id}"):
                    if tipo_sugerido_edicion == "Fianza recibida":
                        resultado_fianza = crear_asiento_fianza_recibida(
                            fecha=fecha_edicion,
                            concepto=f"Fianza asociada a asiento {asiento_edicion_id} - {concepto_edicion}",
                            importe=float(nuevo_importe),
                            cuenta_tesoreria=nueva_cuenta,
                            asiento_origen_id=asiento_edicion_id
                        )
                    else:
                        resultado_fianza = crear_asiento_fianza_devuelta(
                            fecha=fecha_edicion,
                            concepto=f"Devolución de fianza origen {int(fianza_origen_edicion)} - asiento origen {asiento_edicion_id} - {concepto_edicion}",
                            importe=float(nuevo_importe),
                            cuenta_tesoreria=nueva_cuenta,
                            asiento_origen_id=asiento_edicion_id,
                            asiento_fianza_recibida_id=int(fianza_origen_edicion) if pd.notna(fianza_origen_edicion) else None
                        )

                    if resultado_fianza["ok"]:
                        guardar_estado_revision_fianza(
                            asiento_origen_id=asiento_edicion_id,
                            estado="creada",
                            comentario=f"Operación creada: {resultado_fianza['asiento_id']}"
                        )
                        st.success(
                            f"Operación creada correctamente (ID: {resultado_fianza['asiento_id']})"
                        )
                        st.rerun()
                    else:
                        if resultado_fianza.get("duplicado"):
                            guardar_estado_revision_fianza(
                                asiento_origen_id=asiento_edicion_id,
                                estado="creada",
                                comentario=resultado_fianza["error"]
                            )
                            st.warning(resultado_fianza["error"])
                            st.rerun()
                        else:
                            st.error(f"Error al crear la operación: {resultado_fianza['error']}")

    st.divider()

    # =========================
    # CREACIÓN MASIVA
    # =========================
    st.markdown("### Creación masiva")
    st.caption("Crea todas las filas seleccionadas respetando importes, tipo sugerido y cuenta de tesorería.")

    if seleccionadas.empty:
        st.info("Marca una o varias filas para crear las operaciones.")
        return

    if st.button("Crear operaciones seleccionadas", key="crear_fianzas_masivas"):
        creados = []
        duplicados = []
        errores = []

        for _, row in seleccionadas.iterrows():
            asiento_id = int(row["Asiento origen"])
            fecha = str(row["Fecha"])
            concepto = str(row["Concepto"])
            tipo_sugerido = str(row["Tipo sugerido"])
            importe_fianza = float(row["Importe fianza"] or 0)
            cuenta_tesoreria = str(row["Cuenta tesorería"])
            fianza_origen = row["Fianza origen"]

            validacion_creacion = puede_crearse_operacion_fianza(row)

            if not validacion_creacion["ok"]:
                errores.append({
                    "Asiento origen": asiento_id,
                    "Tipo": tipo_sugerido,
                    "Detalle": validacion_creacion["motivo"]
                })
                continue

            if tipo_sugerido == "Fianza recibida":
                resultado_fianza = crear_asiento_fianza_recibida(
                    fecha=fecha,
                    concepto=f"Fianza asociada a asiento {asiento_id} - {concepto}",
                    importe=importe_fianza,
                    cuenta_tesoreria=cuenta_tesoreria,
                    asiento_origen_id=asiento_id
                )
            else:
                resultado_fianza = crear_asiento_fianza_devuelta(
                    fecha=fecha,
                    concepto=f"Devolución de fianza origen {int(fianza_origen)} - asiento origen {asiento_id} - {concepto}",
                    importe=importe_fianza,
                    cuenta_tesoreria=cuenta_tesoreria,
                    asiento_origen_id=asiento_id,
                    asiento_fianza_recibida_id=int(fianza_origen) if pd.notna(fianza_origen) else None
                )

            if resultado_fianza["ok"]:
                guardar_estado_revision_fianza(
                    asiento_origen_id=asiento_id,
                    estado="creada",
                    comentario=f"Operación creada: {resultado_fianza['asiento_id']}"
                )

                creados.append({
                    "Asiento origen": asiento_id,
                    "Tipo": tipo_sugerido,
                    "Asiento creado": resultado_fianza["asiento_id"],
                    "Importe": importe_fianza
                })
            else:
                if resultado_fianza.get("duplicado"):
                    guardar_estado_revision_fianza(
                        asiento_origen_id=asiento_id,
                        estado="creada",
                        comentario=resultado_fianza["error"]
                    )

                    duplicados.append({
                        "Asiento origen": asiento_id,
                        "Tipo": tipo_sugerido,
                        "Detalle": resultado_fianza["error"]
                    })
                else:
                    errores.append({
                        "Asiento origen": asiento_id,
                        "Tipo": tipo_sugerido,
                        "Detalle": resultado_fianza["error"]
                    })

        if creados:
            st.success(f"Se han creado {len(creados)} operaciones.")
            st.dataframe(pd.DataFrame(creados), use_container_width=True)

        if duplicados:
            st.warning(f"{len(duplicados)} ya existían y no se duplicaron.")
            st.dataframe(pd.DataFrame(duplicados), use_container_width=True)

        if errores:
            st.error(f"Hubo {len(errores)} errores al crear operaciones.")
            st.dataframe(pd.DataFrame(errores), use_container_width=True)

        if creados:
            st.rerun()

def pantalla_devoluciones_fianza(cursor):
    st.info("Pantalla antigua de devoluciones desactivada temporalmente.")
    return

def pantalla_libro_diario(cursor):
    st.markdown('<div class="section-title">Libro diario</div>', unsafe_allow_html=True)

    # =========================
    # FILTROS
    # =========================
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        filtro_tipo = st.selectbox(
            "Filtrar por tipo de operación",
            [
                "Todos",
                "compra",
                "venta",
                "cobro",
                "pago",
                "importado_excel",
                "movimiento_excel",
                "factura_importada_excel",
                "correccion_incidencia",
                "fianza_recibida",
                "fianza_devuelta"
            ],
            key="libro_filtro_tipo"
        )

    with col_f2:
        texto_busqueda = st.text_input(
            "Buscar en concepto",
            value="",
            placeholder="Ej: fianza, factura, cliente, alquiler...",
            key="libro_texto_busqueda"
        ).strip().lower()

    with col_f3:
        limite = st.number_input(
            "Número máximo de asientos a mostrar",
            min_value=50,
            max_value=100000,
            value=500,
            step=50,
            key="libro_limite"
        )

    col_f4, col_f5, col_f6 = st.columns(3)

    with col_f4:
        fecha_desde = st.text_input(
            "Fecha desde (YYYY-MM-DD)",
            value="",
            key="libro_fecha_desde"
        ).strip()

    with col_f5:
        fecha_hasta = st.text_input(
            "Fecha hasta (YYYY-MM-DD)",
            value="",
            key="libro_fecha_hasta"
        ).strip()

    with col_f6:
        st.empty()

    col_f7, col_f8 = st.columns(2)

    with col_f7:
        importe_minimo = st.number_input(
            "Importe mínimo del asiento",
            min_value=0.0,
            step=1.0,
            value=0.0,
            key="libro_importe_minimo"
        )

    with col_f8:
        solo_con_error_textual = st.checkbox(
            "Solo conceptos con palabras clave",
            value=False,
            key="libro_solo_keywords"
        )

    # =========================
    # CARGA DE ASIENTOS
    # =========================
    if filtro_tipo == "Todos":
        cursor.execute("""
            SELECT id, fecha, concepto, tipo_operacion
            FROM asientos
            ORDER BY id ASC
        """)
    else:
        cursor.execute("""
            SELECT id, fecha, concepto, tipo_operacion
            FROM asientos
            WHERE tipo_operacion = %s
            ORDER BY id ASC
        """, (filtro_tipo,))

    asientos = cursor.fetchall()

    if not asientos:
        st.warning("No hay asientos para mostrar.")
        return

    # =========================
    # FILTRADO EN PYTHON
    # =========================
    asientos_filtrados = []

    palabras_clave = ["fianza", "deposito", "depósito", "garantia", "garantía"]

    for asiento in asientos:
        asiento_id, fecha, concepto, tipo_operacion = asiento
        concepto_txt = str(concepto or "").strip()
        concepto_lower = concepto_txt.lower()

        # filtro texto
        if texto_busqueda and texto_busqueda not in concepto_lower:
            continue

        # filtro fechas
        if fecha_desde and str(fecha) < fecha_desde:
            continue
        if fecha_hasta and str(fecha) > fecha_hasta:
            continue

        mostrar_aviso_fianza = False
        asiento_fianza_existente = None
        importe_fianza_sugerido = 0.0


        # filtro solo conceptos con keywords
        if solo_con_error_textual and not any(p in concepto_lower for p in palabras_clave):
            continue

        # calcular importe total del asiento
        cursor.execute("""
            SELECT SUM(importe)
            FROM lineas_asiento
            WHERE asiento_id = %s
              AND movimiento = %s
        """, (asiento_id, "debe"))
        total_debe = cursor.fetchone()[0] or 0.0

        if float(total_debe) < float(importe_minimo):
            continue

        asientos_filtrados.append((
            asiento_id,
            fecha,
            concepto_txt,
            tipo_operacion,
            float(total_debe)
        ))

    if not asientos_filtrados:
        st.info("No hay asientos que cumplan los filtros.")
        return

    # limitar
    asientos_filtrados = asientos_filtrados[-limite:]

    # resumen
    total_resultados = len(asientos_filtrados)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Asientos filtrados", total_resultados)
    with c2:
        st.metric("Límite aplicado", limite)

    # vista tabla resumen
    st.divider()

    # =========================
    # DETALLE DE ASIENTOS
    # =========================
    for numero_visible, asiento in enumerate(asientos_filtrados, start=1):
        (
            asiento_id,
            fecha,
            concepto,
            tipo_operacion,
            total_debe
        ) = asiento

        etiqueta_fianza = ""

        with st.expander(
            f"Asiento {numero_visible} | ID {asiento_id} | {fecha} | {concepto[:80]}{etiqueta_fianza}",
            expanded=False
        ):
            cursor.execute("""
                SELECT cuenta, movimiento, importe
                FROM lineas_asiento
                WHERE asiento_id = %s
            """, (asiento_id,))
            lineas = cursor.fetchall()

            df_lineas = pd.DataFrame(
                lineas,
                columns=["Cuenta", "Movimiento", "Importe"]
            )

            st.write(f"**Concepto:** {concepto}")
            st.write(f"**Tipo:** {tipo_operacion}")
            st.write(f"**Importe total del asiento (debe):** {total_debe:.2f} €")
            st.dataframe(df_lineas, use_container_width=True)

            analisis_fianza = analizar_asiento_fianza(cursor, asiento_id, fecha, concepto)
            es_asiento_ya_fianza = tipo_operacion in ("fianza_recibida", "fianza_devuelta")

            if mostrar_aviso_fianza and not es_asiento_ya_fianza:
                st.warning(
                    f"Posible fianza detectada en el concepto. "
                    f"Importe sugerido: {analisis_fianza['importe_sugerido']:.2f} €"
                )

                col_fianza_1, col_fianza_2, col_fianza_3 = st.columns(3)

                with col_fianza_1:
                    importe_fianza = st.number_input(
                        "Importe fianza",
                        min_value=0.0,
                        step=0.01,
                        value=float(analisis_fianza["importe_sugerido"]),
                        key=f"importe_fianza_{asiento_id}"
                    )

                with col_fianza_2:
                    cuenta_tesoreria = st.selectbox(
                        "Cuenta tesorería",
                        ["570 Caja", "572 Bancos"],
                        index=0,
                        key=f"cuenta_tesoreria_fianza_{asiento_id}"
                    )

                with col_fianza_3:
                    st.write("")
                    st.write("")

                if st.button("Crear asiento de fianza", key=f"fianza_{asiento_id}"):
                    resultado_fianza = crear_asiento_fianza_recibida(
                        fecha=fecha,
                        concepto=f"Fianza asociada a asiento {asiento_id} - {concepto}",
                        importe=importe_fianza,
                        cuenta_tesoreria=cuenta_tesoreria,
                        asiento_origen_id=asiento_id
                    )

                    if resultado_fianza["ok"]:
                        st.success(
                            f"Asiento de fianza creado correctamente (ID: {resultado_fianza['asiento_id']})"
                        )
                        st.rerun()
                    else:
                        if resultado_fianza.get("duplicado"):
                            st.warning(resultado_fianza["error"])
                        else:
                            st.error(
                                f"Error al crear asiento de fianza: {resultado_fianza['error']}"
                            )
            elif asiento_fianza_existente is not None:
                st.success(
                    f"La fianza ya fue creada anteriormente (ID asiento: {asiento_fianza_existente})"
                )

def pantalla_balance_comprobacion():
    st.markdown('<div class="section-title">Balance de comprobación</div>', unsafe_allow_html=True)

    df_balance = balance_comprobacion()
    st.dataframe(df_balance, use_container_width=True)

    total_debe = df_balance["Debe"].sum()
    total_haber = df_balance["Haber"].sum()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Debe", f"{total_debe:.2f} €")
    with col2:
        st.metric("Total Haber", f"{total_haber:.2f} €")

    if round(total_debe, 2) == round(total_haber, 2):
        st.success("El balance de comprobación cuadra")
    else:
        st.error("El balance de comprobación NO cuadra")


def pantalla_libro_mayor():
    st.markdown('<div class="section-title">Libro mayor</div>', unsafe_allow_html=True)
    cuenta = st.text_input("Filtrar por cuenta (opcional)")
    df_mayor = libro_mayor(cuenta.strip()) if cuenta.strip() else libro_mayor()
    st.dataframe(df_mayor, use_container_width=True)


def pantalla_cuenta_resultados():
    st.markdown('<div class="section-title">Cuenta de pérdidas y ganancias</div>', unsafe_allow_html=True)
    resumen, detalle = cuenta_resultados()
    st.subheader("Resumen")
    st.dataframe(resumen, use_container_width=True)
    st.subheader("Detalle")
    st.dataframe(detalle, use_container_width=True)


def pantalla_balance_situacion():
    st.markdown('<div class="section-title">Balance de situación</div>', unsafe_allow_html=True)

    resumen, activo_no_corriente, activo_corriente, patrimonio_neto, pasivo_no_corriente, pasivo_corriente = balance_situacion()

    st.subheader("Resumen")
    st.dataframe(resumen, use_container_width=True)

    st.subheader("Activo")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Activo no corriente**")
        st.dataframe(activo_no_corriente, use_container_width=True)

    with col2:
        st.markdown("**Activo corriente**")
        st.dataframe(activo_corriente, use_container_width=True)

    st.subheader("Patrimonio neto y Pasivo")
    col3, col4, col5 = st.columns(3)

    with col3:
        st.markdown("**Patrimonio neto**")
        st.dataframe(patrimonio_neto, use_container_width=True)

    with col4:
        st.markdown("**Pasivo no corriente**")
        st.dataframe(pasivo_no_corriente, use_container_width=True)

    with col5:
        st.markdown("**Pasivo corriente**")
        st.dataframe(pasivo_corriente, use_container_width=True)

def inicializar_incidencias_control_revisadas():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidencias_control_revisadas (
            id SERIAL PRIMARY KEY,
            asiento_id INTEGER,
            tipo_incidencia TEXT,
            detalle TEXT,
            revisada_en TEXT
        )
    """)

    conn.commit()
    conn.close()


def incidencia_control_ya_revisada(asiento_id, tipo_incidencia, detalle):
    inicializar_incidencias_control_revisadas()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM incidencias_control_revisadas
        WHERE asiento_id = %s
          AND tipo_incidencia = %s
          AND detalle = %s
        LIMIT 1
    """, (int(asiento_id), str(tipo_incidencia), str(detalle)))

    fila = cursor.fetchone()
    conn.close()

    return fila is not None


def marcar_incidencia_control_revisada(asiento_id, tipo_incidencia, detalle):
    inicializar_incidencias_control_revisadas()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO incidencias_control_revisadas (
            asiento_id,
            tipo_incidencia,
            detalle,
            revisada_en
        )
        VALUES (%s, %s, %s, %s)
    """, (
        int(asiento_id),
        str(tipo_incidencia),
        str(detalle),
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return {"ok": True}


def quitar_incidencia_control_revisada(asiento_id, tipo_incidencia, detalle):
    inicializar_incidencias_control_revisadas()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM incidencias_control_revisadas
        WHERE asiento_id = %s
          AND tipo_incidencia = %s
          AND detalle = %s
    """, (
        int(asiento_id),
        str(tipo_incidencia),
        str(detalle)
    ))

    conn.commit()
    conn.close()

    return {"ok": True}

def actualizar_asiento_y_lineas(asiento_id, nueva_fecha, nuevo_concepto, lineas_editadas):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE asientos
            SET fecha = %s, concepto = %s
            WHERE id = %s
        """, (
            str(nueva_fecha),
            str(nuevo_concepto),
            int(asiento_id)
        ))

        cursor.execute("""
            DELETE FROM lineas_asiento
            WHERE asiento_id = %s
        """, (int(asiento_id),))

        for linea in lineas_editadas:
            cuenta = str(linea.get("Cuenta") or "").strip()
            movimiento = str(linea.get("Movimiento") or "").strip().lower()
            importe = float(linea.get("Importe") or 0)

            if not cuenta:
                continue

            if movimiento not in ("debe", "haber"):
                continue

            if importe <= 0:
                continue

            cursor.execute("""
                INSERT INTO lineas_asiento (asiento_id, cuenta, movimiento, importe)
                VALUES (%s, %s, %s, %s)
            """, (
                int(asiento_id),
                cuenta,
                movimiento,
                importe
            ))

        conn.commit()

        return {
            "ok": True,
            "mensaje": f"Asiento {asiento_id} actualizado correctamente"
        }

    except Exception as e:
        conn.rollback()
        return {
            "ok": False,
            "mensaje": str(e)
        }

    finally:
        conn.close()

def pantalla_control_contable():
    st.markdown('<div class="section-title">Control contable</div>', unsafe_allow_html=True)

    df_control = validar_sistema_completo()
    inicializar_incidencias_control_revisadas()

    if df_control.empty:
        st.success("No se detectaron incidencias contables")
    else:
        revisadas_global = []

        for _, row in df_control.iterrows():
            asiento_id_tmp = row.get("asiento_id")
            tipo_tmp = row.get("tipo")
            detalle_tmp = row.get("detalle")

            if pd.isna(asiento_id_tmp):
                revisadas_global.append(False)
            else:
                revisadas_global.append(
                    incidencia_control_ya_revisada(
                        int(asiento_id_tmp),
                        str(tipo_tmp),
                        str(detalle_tmp)
                    )
                )

        if len(revisadas_global) == len(df_control):
            df_control_activo = df_control[[not x for x in revisadas_global]].copy()
        else:
            df_control_activo = df_control.copy()

        total = len(df_control_activo)
        altas = len(df_control_activo[df_control_activo["gravedad"] == "alta"])
        medias = len(df_control_activo[df_control_activo["gravedad"] == "media"])
        bajas = len(df_control_activo[df_control_activo["gravedad"] == "baja"])

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Total incidencias", total)
        with c2:
            st.metric("Gravedad alta", altas)
        with c3:
            st.metric("Gravedad media", medias)
        with c4:
            st.metric("Gravedad baja", bajas)

        st.markdown("### Filtros")

        f1, f2, f3 = st.columns(3)

        with f1:
            filtro_gravedad = st.selectbox(
                "Filtrar por gravedad",
                ["Todas", "alta", "media", "baja"],
                key="control_contable_filtro_gravedad"
            )

        with f2:
            filtro_texto = st.text_input(
                "Buscar en tipo / concepto / detalle",
                value="",
                key="control_contable_filtro_texto"
            ).strip().lower()

        with f3:
            mostrar_revisadas = st.checkbox(
                "Mostrar revisadas",
                value=False,
                key="control_contable_mostrar_revisadas"
            )

        df_mostrar = df_control_activo.copy()

        if filtro_gravedad != "Todas":
            df_mostrar = df_mostrar[df_mostrar["gravedad"] == filtro_gravedad].copy()

        if filtro_texto:
            mask = (
                df_mostrar["tipo"].astype(str).str.lower().str.contains(filtro_texto, na=False) |
                df_mostrar["concepto"].astype(str).str.lower().str.contains(filtro_texto, na=False) |
                df_mostrar["detalle"].astype(str).str.lower().str.contains(filtro_texto, na=False)
            )
            df_mostrar = df_mostrar[mask].copy()
        revisadas_mask = []

        for _, row in df_mostrar.iterrows():
            asiento_id_tmp = row.get("asiento_id")
            tipo_tmp = row.get("tipo")
            detalle_tmp = row.get("detalle")

            if pd.isna(asiento_id_tmp):
                revisadas_mask.append(False)
            else:
                revisadas_mask.append(
                    incidencia_control_ya_revisada(
                        int(asiento_id_tmp),
                        str(tipo_tmp),
                        str(detalle_tmp)
                    )
                )

        if len(revisadas_mask) == len(df_mostrar):
            if not mostrar_revisadas:
                df_mostrar = df_mostrar[[not x for x in revisadas_mask]].copy()
            else:
                df_mostrar = df_mostrar.copy()
                df_mostrar["revisada"] = revisadas_mask

        if df_mostrar.empty:
            st.info("No hay incidencias con los filtros seleccionados.")
        else:
            st.warning(f"Se detectaron {len(df_mostrar)} incidencias")

            if "revisada" in df_mostrar.columns:
                df_mostrar["revisada"] = df_mostrar["revisada"].apply(lambda x: "sí" if x else "no")

            st.dataframe(df_mostrar, use_container_width=True)
            st.markdown("### Revisar incidencia concreta")

            incidencias_con_asiento = df_mostrar[df_mostrar["asiento_id"].notna()].copy()

            if incidencias_con_asiento.empty:
                st.info("Las incidencias filtradas no están asociadas a un asiento concreto.")
            else:
                opciones_incidencia = {}

                for idx, row in incidencias_con_asiento.iterrows():
                    asiento_id = int(row["asiento_id"])
                    fecha_txt = str(row["fecha"] or "")
                    tipo_txt = str(row["tipo"] or "")
                    concepto_txt = str(row["concepto"] or "")
                    etiqueta = f"Asiento {asiento_id} | {fecha_txt} | {tipo_txt} | {concepto_txt[:80]}"
                    opciones_incidencia[etiqueta] = asiento_id

                seleccion_incidencia = st.selectbox(
                    "Selecciona una incidencia para revisar su asiento",
                    list(opciones_incidencia.keys()),
                    key="control_contable_selector_incidencia"
                )

                asiento_id_sel = opciones_incidencia[seleccion_incidencia]

                fila_incidencia = incidencias_con_asiento[incidencias_con_asiento["asiento_id"] == asiento_id_sel].iloc[0]

                st.write(f"**Tipo de incidencia:** {fila_incidencia['tipo']}")
                st.write(f"**Gravedad:** {fila_incidencia['gravedad']}")
                st.write(f"**Detalle:** {fila_incidencia['detalle']}")
                st.info(sugerir_accion_incidencia(fila_incidencia["tipo"]))

                cursor = get_connection().cursor()
                try:
                    cursor.execute("""
                        SELECT id, fecha, concepto, tipo_operacion
                        FROM asientos
                        WHERE id = %s
                        LIMIT 1
                    """, (asiento_id_sel,))
                    asiento = cursor.fetchone()

                    if asiento:
                        asiento_id_db, fecha_db, concepto_db, tipo_db = asiento

                        st.markdown("#### Detalle del asiento")
                        st.write(f"**ID:** {asiento_id_db}")
                        st.write(f"**Fecha:** {fecha_db}")
                        st.write(f"**Concepto:** {concepto_db}")
                        st.write(f"**Tipo operación:** {tipo_db}")

                        cursor.execute("""
                            SELECT cuenta, movimiento, importe
                            FROM lineas_asiento
                            WHERE asiento_id = %s
                        """, (asiento_id_sel,))
                        lineas = cursor.fetchall()

                        if lineas:
                            df_lineas = pd.DataFrame(lineas, columns=["Cuenta", "Movimiento", "Importe"])
                            st.dataframe(df_lineas, use_container_width=True)

                            total_debe = df_lineas[df_lineas["Movimiento"] == "debe"]["Importe"].astype(float).sum()
                            total_haber = df_lineas[df_lineas["Movimiento"] == "haber"]["Importe"].astype(float).sum()

                            c_det1, c_det2, c_det3 = st.columns(3)

                            with c_det1:
                                st.metric("Debe", f"{total_debe:.2f} €")

                            with c_det2:
                                st.metric("Haber", f"{total_haber:.2f} €")

                            with c_det3:
                                st.metric("Diferencia", f"{(total_debe - total_haber):.2f} €")
                            st.markdown("#### Edición manual del asiento")

                            with st.expander("Editar asiento y líneas", expanded=False):
                                nueva_fecha = st.text_input(
                                    "Fecha del asiento",
                                    value=str(fecha_db),
                                    key=f"editar_fecha_asiento_{asiento_id_sel}"
                                )

                                nuevo_concepto = st.text_input(
                                    "Concepto del asiento",
                                    value=str(concepto_db),
                                    key=f"editar_concepto_asiento_{asiento_id_sel}"
                                )

                                df_lineas_edit = df_lineas.copy()

                                opciones_movimiento = ["debe", "haber"]
                                df_lineas_edit["Movimiento"] = df_lineas_edit["Movimiento"].astype(str).str.lower()

                                df_lineas_resultado = st.data_editor(
                                    df_lineas_edit,
                                    use_container_width=True,
                                    num_rows="dynamic",
                                    key=f"editor_lineas_asiento_{asiento_id_sel}",
                                    column_config={
                                        "Cuenta": st.column_config.TextColumn("Cuenta"),
                                        "Movimiento": st.column_config.SelectboxColumn(
                                            "Movimiento",
                                            options=opciones_movimiento
                                        ),
                                        "Importe": st.column_config.NumberColumn(
                                            "Importe",
                                            min_value=0.0,
                                            step=0.01,
                                            format="%.2f"
                                        )
                                    }
                                )

                                ed1, ed2 = st.columns(2)

                                with ed1:
                                    if st.button("Guardar cambios del asiento", key=f"guardar_cambios_asiento_{asiento_id_sel}"):
                                        lineas_editadas = df_lineas_resultado.to_dict(orient="records")

                                        resultado_actualizacion = actualizar_asiento_y_lineas(
                                            asiento_id=asiento_id_sel,
                                            nueva_fecha=nueva_fecha,
                                            nuevo_concepto=nuevo_concepto,
                                            lineas_editadas=lineas_editadas
                                        )

                                        if resultado_actualizacion["ok"]:
                                            st.success(resultado_actualizacion["mensaje"])
                                            st.rerun()
                                        else:
                                            st.error(resultado_actualizacion["mensaje"])

                                with ed2:
                                    if st.button("Guardar y revalidar", key=f"guardar_revalidar_asiento_{asiento_id_sel}"):
                                        lineas_editadas = df_lineas_resultado.to_dict(orient="records")

                                        resultado_actualizacion = actualizar_asiento_y_lineas(
                                            asiento_id=asiento_id_sel,
                                            nueva_fecha=nueva_fecha,
                                            nuevo_concepto=nuevo_concepto,
                                            lineas_editadas=lineas_editadas
                                        )

                                        if resultado_actualizacion["ok"]:
                                            st.success("Asiento actualizado y sistema revalidado.")
                                            st.rerun()
                                        else:
                                            st.error(resultado_actualizacion["mensaje"])

                            st.markdown("#### Acciones sobre este asiento")

                            ac1, ac2, ac3, ac4 = st.columns(4)

                            with ac1:
                                if st.button("Revalidar sistema", key=f"revalidar_inc_{asiento_id_sel}"):
                                    st.success("Validación relanzada.")
                                    st.rerun()
                            with ac2:
                                if st.button("Aceptar incidencia", key=f"aceptar_incidencia_{asiento_id_sel}"):
                                    resultado_revision = marcar_incidencia_control_revisada(
                                        asiento_id_sel,
                                        fila_incidencia["tipo"],
                                        fila_incidencia["detalle"]
                                    )

                                    if resultado_revision.get("ok"):
                                        st.success("Incidencia marcada como revisada. Ya no aparecerá en el listado.")
                                        st.rerun()
                                    else:
                                        st.error("No se pudo marcar la incidencia como revisada.")

                            with ac3:
                                clave_confirmacion = f"confirmar_borrar_desde_control_{asiento_id_sel}"

                                if clave_confirmacion not in st.session_state:
                                    st.session_state[clave_confirmacion] = False

                                if not st.session_state[clave_confirmacion]:
                                    if st.button("Borrar este asiento", key=f"borrar_desde_control_{asiento_id_sel}"):
                                        st.session_state[clave_confirmacion] = True
                                else:
                                    st.warning(f"Vas a borrar el asiento {asiento_id_sel}. Esta acción no se puede deshacer.")
                            with ac4:
                                if st.button("Quitar revisada", key=f"quitar_revision_inc_{asiento_id_sel}"):
                                    resultado_quitar_revision = quitar_incidencia_control_revisada(
                                        asiento_id_sel,
                                        fila_incidencia["tipo"],
                                        fila_incidencia["detalle"]
                                    )

                                    if resultado_quitar_revision.get("ok"):
                                        st.success("La incidencia vuelve a quedar activa.")
                                        st.rerun()
                                    else:
                                        st.error("No se pudo reactivar la incidencia.")

                                    bc1, bc2 = st.columns(2)

                                    with bc1:
                                        if st.button("Sí, borrar asiento", key=f"confirmar_borrar_desde_control_si_{asiento_id_sel}"):
                                            resultado_borrado = borrar_asiento(asiento_id_sel)
                                            st.session_state[clave_confirmacion] = False

                                            if resultado_borrado["ok"]:
                                                st.success(resultado_borrado["mensaje"])
                                                st.rerun()
                                            else:
                                                st.error(resultado_borrado["mensaje"])

                                    with bc2:
                                        if st.button("Cancelar borrado", key=f"confirmar_borrar_desde_control_no_{asiento_id_sel}"):
                                            st.session_state[clave_confirmacion] = False

                            st.caption("Consejo: si el asiento está descuadrado o tiene importe absurdo, revisa primero el origen antes de borrarlo.")

                        else:
                            st.warning("Este asiento no tiene líneas contables.")
                finally:
                    cursor.connection.close()

    st.subheader("Mantenimiento")
    st.markdown("### Borrar asiento concreto")

    asiento_id_borrar = st.number_input(
        "ID del asiento a borrar",
        min_value=1,
        step=1,
        key="asiento_id_borrar"
    )

    if "confirmar_borrado_asiento" not in st.session_state:
        st.session_state["confirmar_borrado_asiento"] = False

    if not st.session_state["confirmar_borrado_asiento"]:
        if st.button("Borrar asiento seleccionado", key="boton_borrar_asiento"):
            st.session_state["confirmar_borrado_asiento"] = True
    else:
        st.warning(f"Vas a borrar el asiento ID {asiento_id_borrar}. Esta acción no se puede deshacer.")

        col_b1, col_b2 = st.columns(2)

        with col_b1:
            if st.button("Sí, borrar asiento", key="confirmar_borrar_asiento_si"):
                resultado_borrado = borrar_asiento(asiento_id_borrar)
                st.session_state["confirmar_borrado_asiento"] = False

                if resultado_borrado["ok"]:
                    st.success(resultado_borrado["mensaje"])
                    st.rerun()
                else:
                    st.error(resultado_borrado["mensaje"])

        with col_b2:
            if st.button("Cancelar borrado", key="confirmar_borrar_asiento_no"):
                st.session_state["confirmar_borrado_asiento"] = False

    if "confirmar_reset_contable" not in st.session_state:
        st.session_state["confirmar_reset_contable"] = False

    if not st.session_state["confirmar_reset_contable"]:
        if st.button("Resetear contabilidad", key="boton_reset_contabilidad"):
            st.session_state["confirmar_reset_contable"] = True
    else:
        st.warning("¿Seguro que quieres borrar toda la contabilidad?")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Sí, resetear todo", key="confirmar_reset_contable_si"):
                resultado = reset_contabilidad()
                st.session_state["confirmar_reset_contable"] = False

                if isinstance(resultado, dict):
                    if resultado.get("ok"):
                        st.success("Contabilidad reseteada correctamente")
                    else:
                        st.error(
                            f"Reset incompleto | asientos={resultado.get('asientos')} | "
                            f"lineas={resultado.get('lineas')} | errores={resultado.get('errores')}"
                        )
                    st.rerun()
                else:
                    if resultado == "ok":
                        st.success("Contabilidad reseteada correctamente")
                        st.rerun()
                    else:
                        st.error(f"No se pudo resetear la contabilidad: {resultado}")

        with col2:
            if st.button("Cancelar", key="confirmar_reset_contable_no"):
                st.session_state["confirmar_reset_contable"] = False

def sugerir_accion_incidencia(tipo_incidencia):
    tipo = str(tipo_incidencia or "").strip().lower()

    mapa = {
        "asiento_sin_lineas": "Revisar el origen del asiento. No tiene líneas contables y normalmente debe eliminarse o reconstruirse.",
        "asiento_descuadrado": "Revisar las líneas del asiento y corregir importes o movimientos hasta que Debe y Haber cuadren.",
        "importe_absurdo": "Revisar el concepto y el importe detectado. Puede haberse tomado un teléfono, DNI o referencia como importe.",
        "cliente_saldo_acreedor": "Revisar cobros, abonos o facturas del cliente. Un cliente con saldo acreedor suele indicar una imputación anómala.",
        "proveedor_saldo_deudor": "Revisar pagos, anticipos o facturas del proveedor. Un proveedor con saldo deudor puede estar mal contabilizado.",
        "caja_negativa": "Revisar pagos en efectivo y faltantes de registro. La caja no debería quedar en negativo.",
        "bancos_negativos": "Revisar movimientos bancarios, pagos duplicados o conciliaciones incorrectas.",
        "devolucion_sin_fianza_previa": "Comprobar si falta crear la fianza original o si la devolución se ha contabilizado sobre un asiento incorrecto.",
        "fianza_abierta": "Comprobar si la fianza sigue vigente o si falta registrar su devolución.",
    }

    return mapa.get(
        tipo,
        "Revisar manualmente esta incidencia y validar el asiento asociado."
    )


def pantalla_apertura_pdf():
    from apertura_pdf import procesar_balance_pdf_a_apertura, registrar_balance_pdf_como_apertura

    st.markdown('<div class="section-title">Asiento de apertura desde PDF</div>', unsafe_allow_html=True)

    pdf_file = st.file_uploader("Sube el balance en PDF", type=["pdf"])
    fecha_apertura = st.date_input("Fecha de apertura")

    if pdf_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_file.read())
            ruta_pdf = tmp.name

        if st.button("Analizar balance"):
            resultado = procesar_balance_pdf_a_apertura(
                ruta_pdf,
                str(fecha_apertura)
            )

            st.subheader("Validación")
            st.write(resultado["validacion"])

            st.subheader("Líneas del asiento")
            for linea in resultado["lineas"]:
                st.write(linea)

            st.session_state["apertura_pdf_resultado"] = resultado
            st.session_state["apertura_pdf_ruta"] = ruta_pdf

    if "apertura_pdf_resultado" in st.session_state:
        resultado_pdf = st.session_state["apertura_pdf_resultado"]

        if st.button("Registrar asiento de apertura"):
            resultado_registro = registrar_balance_pdf_como_apertura(
                st.session_state["apertura_pdf_ruta"],
                str(fecha_apertura)
            )

            if resultado_registro["ok"]:
                st.success(f"Asiento creado correctamente. ID: {resultado_registro['asiento_id']}")
            else:
                st.error("El asiento no cuadra, revisa los datos")

        if "detalle" in resultado_pdf:
            st.subheader("Validación ampliada")
            st.write(resultado_pdf["detalle"]["validacion"])

            st.subheader("Líneas generadas")
            for linea in resultado_pdf["detalle"]["lineas"]:
                st.write(linea)

            st.subheader("Datos detectados del balance")
            st.write(resultado_pdf["detalle"]["datos_balance"])

def formatear_importe_seguro(valor):
    try:
        return f"{float(valor or 0):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00 €"


def estado_factura_visual(estado, fecha_vencimiento=None):
    estado_txt = str(estado or "").strip().lower()

    if estado_txt in ("abono", "rectificativa", "abonada"):
        return "Abono", "badge-pagada"

    if estado_txt in ("pagada", "cobrada", "cobrado"):
        return "Pagada", "badge-pagada"

    if fecha_vencimiento:
        try:
            if isinstance(fecha_vencimiento, str):
                fecha_v = datetime.strptime(fecha_vencimiento[:10], "%Y-%m-%d").date()
            else:
                fecha_v = fecha_vencimiento

            if fecha_v < datetime.today().date():
                return "Vencida", "badge-vencida"
        except:
            pass

    return "Pendiente", "badge-pendiente"


def convertir_fila_factura_a_dict(cursor, fila):
    columnas = [desc[0] for desc in cursor.description]
    return dict(zip(columnas, fila))


def obtener_facturas_dict(cursor):
    cursor.execute("SELECT * FROM facturas ORDER BY id DESC")
    filas = cursor.fetchall()

    columnas = [desc[0] for desc in cursor.description]
    return [dict(zip(columnas, fila)) for fila in filas]


def generar_html_ficha_factura(factura):
    numero = factura.get("numero_factura") or factura.get("numero") or f"Factura #{factura.get('id', '')}"
    tercero = (
        factura.get("nombre_tercero")
        or factura.get("cliente")
        or factura.get("proveedor")
        or factura.get("tercero")
        or "No informado"
    )
    fecha = factura.get("fecha") or factura.get("fecha_emision") or ""
    vencimiento = factura.get("fecha_vencimiento") or factura.get("vencimiento") or ""
    concepto = factura.get("concepto") or factura.get("descripcion") or ""
    estado = factura.get("estado") or "pendiente"
    tipo = factura.get("tipo") or factura.get("tipo_factura") or "compra"
    base = factura.get("base_imponible") or factura.get("base") or 0
    cuota = factura.get("cuota_impuesto") or factura.get("cuota_iva") or factura.get("iva") or factura.get("impuesto") or 0
    total = factura.get("total") or factura.get("importe_total") or factura.get("importe") or 0
    forma_pago = factura.get("forma_pago") or factura.get("metodo_pago") or ""
    referencia = factura.get("referencia") or ""
    moneda = factura.get("moneda") or "EUR"

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Factura {numero}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f4f7fb;
                margin: 0;
                padding: 30px;
                color: #172033;
            }}
            .sheet {{
                background: white;
                max-width: 980px;
                margin: 0 auto;
                border-radius: 18px;
                padding: 32px;
                box-shadow: 0 12px 30px rgba(0,0,0,0.08);
            }}
            .header {{
                background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 65%, #38bdf8 100%);
                color: white;
                border-radius: 18px;
                padding: 22px 24px;
                margin-bottom: 24px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .header p {{
                margin: 8px 0 0 0;
                color: rgba(255,255,255,0.85);
            }}
            .grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
                margin-bottom: 20px;
            }}
            .box {{
                background: #f8fafc;
                border: 1px solid #dbe3ee;
                border-radius: 14px;
                padding: 16px;
            }}
            .label {{
                font-size: 12px;
                font-weight: 700;
                color: #64748b;
                text-transform: uppercase;
                margin-bottom: 6px;
            }}
            .value {{
                font-size: 16px;
                font-weight: 700;
                color: #172033;
            }}
            .table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            .table th, .table td {{
                border: 1px solid #dbe3ee;
                padding: 12px;
                text-align: left;
            }}
            .table th {{
                background: #eff6ff;
            }}
            .footer {{
                margin-top: 24px;
                font-size: 13px;
                color: #64748b;
            }}
        </style>
    </head>
    <body>
        <div class="sheet">
            <div class="header">
                <h1>{'Abono / rectificativa' if str(tipo).lower() in ('abono_venta', 'venta_rectificativa') else 'Factura emitida' if str(tipo).lower() == 'venta' else 'Ficha factura proveedor'}</h1>
                <p>{numero}</p>
            </div>

            <div class="grid">
                <div class="box">
                    <div class="label">Tercero</div>
                    <div class="value">{tercero}</div>
                </div>
                <div class="box">
                    <div class="label">Estado</div>
                    <div class="value">{estado}</div>
                </div>
                <div class="box">
                    <div class="label">Fecha</div>
                    <div class="value">{fecha}</div>
                </div>
                <div class="box">
                    <div class="label">Vencimiento</div>
                    <div class="value">{vencimiento}</div>
                </div>
                <div class="box">
                    <div class="label">Forma de pago</div>
                    <div class="value">{forma_pago}</div>
                </div>
                <div class="box">
                    <div class="label">Referencia</div>
                    <div class="value">{referencia}</div>
                </div>
            </div>

            <div class="box">
                <div class="label">Concepto</div>
                <div class="value">{concepto}</div>
            </div>

            <table class="table">
                <thead>
                    <tr>
                        <th>Base</th>
                        <th>Impuesto</th>
                        <th>Total</th>
                        <th>Moneda</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{formatear_importe_seguro(base)}</td>
                        <td>{formatear_importe_seguro(cuota)}</td>
                        <td><strong>{formatear_importe_seguro(total)}</strong></td>
                        <td>{moneda}</td>
                    </tr>
                </tbody>
            </table>

            <div class="footer">
                Documento generado desde la aplicación.
            </div>
        </div>
    </body>
    </html>
    """
    return html

def pantalla_facturas(cursor):
    st.markdown("""
        <div class="subnav-shell">
            <div class="subnav-title">Facturación</div>
        </div>
    """, unsafe_allow_html=True)

    facturas = obtener_facturas_dict(cursor)

    if not facturas:
        st.info("No hay facturas registradas.")
        return

    total_facturas = len(facturas)
    total_importe = sum(
        float(f.get("total") or f.get("importe_total") or f.get("importe") or 0)
        for f in facturas
    )

    pendientes = 0
    pagadas = 0
    vencidas = 0
    compras = 0
    ventas = 0

    for f in facturas:
        tipo_tmp = str(f.get("tipo") or f.get("tipo_factura") or "").strip().lower()
        if tipo_tmp == "compra":
            compras += 1
        elif tipo_tmp == "venta":
            ventas += 1
        elif tipo_tmp in ("abono_venta", "venta_rectificativa"):
            ventas += 1

        estado_visual, _badge = estado_factura_visual(
            f.get("estado"),
            f.get("fecha_vencimiento") or f.get("vencimiento")
        )

        if estado_visual == "Pendiente":
            pendientes += 1
        elif estado_visual == "Pagada":
            pagadas += 1
        elif estado_visual == "Vencida":
            vencidas += 1

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total facturas</div>
                <div class="metric-value">{total_facturas}</div>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Pendientes</div>
                <div class="metric-value">{pendientes}</div>
            </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Pagadas</div>
                <div class="metric-value">{pagadas}</div>
            </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Compras / Ventas</div>
                <div class="metric-value">{compras} / {ventas}</div>
            </div>
        """, unsafe_allow_html=True)

    with c5:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Importe total</div>
                <div class="metric-value">{formatear_importe_seguro(total_importe)}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="panel-card">', unsafe_allow_html=True)

    col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 2, 1])

    with col_f1:
        filtro_tipo = st.selectbox(
            "Tipo",
            ["Todos", "compra", "venta", "abono_venta"],
            key="facturas_filtro_tipo"
        )

    with col_f2:
        filtro_estado = st.selectbox(
            "Estado",
            ["Todos", "Pendiente", "Pagada", "Vencida", "Abono"],
            key="facturas_filtro_estado"
        )

    with col_f3:
        filtro_texto = st.text_input(
            "Buscar por número, tercero, concepto o referencia",
            key="facturas_filtro_texto"
        )

    with col_f4:
        ordenar_por = st.selectbox(
            "Orden",
            ["Más recientes", "Más antiguas", "Mayor importe", "Menor importe"],
            key="facturas_orden_visual"
        )

    st.markdown('</div>', unsafe_allow_html=True)

    facturas_filtradas = []

    for factura in facturas:
        tipo = str(factura.get("tipo") or factura.get("tipo_factura") or "").strip().lower()
        numero = str(factura.get("numero_factura") or factura.get("numero") or "")
        tercero = str(factura.get("cliente") or factura.get("proveedor") or factura.get("tercero") or "")
        concepto = str(factura.get("concepto") or factura.get("descripcion") or "")
        referencia = str(factura.get("referencia") or "")
        estado_visual, badge_class = estado_factura_visual(
            factura.get("estado"),
            factura.get("fecha_vencimiento") or factura.get("vencimiento")
        )

        if filtro_tipo != "Todos" and tipo != filtro_tipo:
            continue

        if filtro_estado != "Todos" and estado_visual != filtro_estado:
            continue

        if filtro_texto:
            texto = filtro_texto.lower().strip()
            bloque_busqueda = f"{numero} {tercero} {concepto} {referencia}".lower()
            if texto not in bloque_busqueda:
                continue

        factura["_estado_visual"] = estado_visual
        factura["_badge_class"] = badge_class
        factura["_importe_visual"] = float(
            factura.get("total") or factura.get("importe_total") or factura.get("importe") or 0
        )

        facturas_filtradas.append(factura)

    if not facturas_filtradas:
        st.warning("No hay facturas que coincidan con los filtros.")
        return

    if ordenar_por == "Más recientes":
        facturas_filtradas.sort(
            key=lambda x: str(x.get("fecha") or x.get("fecha_emision") or ""),
            reverse=True
        )
    elif ordenar_por == "Más antiguas":
        facturas_filtradas.sort(
            key=lambda x: str(x.get("fecha") or x.get("fecha_emision") or ""),
            reverse=False
        )
    elif ordenar_por == "Mayor importe":
        facturas_filtradas.sort(
            key=lambda x: float(x.get("_importe_visual") or 0),
            reverse=True
        )
    elif ordenar_por == "Menor importe":
        facturas_filtradas.sort(
            key=lambda x: float(x.get("_importe_visual") or 0),
            reverse=False
        )

    df_grid = pd.DataFrame([
        {
            "ID": f.get("id"),
            "Número": f.get("numero_factura") or f.get("numero") or f"Factura #{f.get('id')}",
            "Tipo": str(f.get("tipo") or f.get("tipo_factura") or "").strip().lower(),
            "Tercero": f.get("nombre_tercero") or f.get("cliente") or f.get("proveedor") or f.get("tercero") or "Sin tercero",
            "Fecha": f.get("fecha") or f.get("fecha_emision") or "",
            "Vencimiento": f.get("fecha_vencimiento") or f.get("vencimiento") or "",
            "Estado": f.get("_estado_visual"),
            "Importe_num": float(f.get("_importe_visual") or 0),
            "Importe": formatear_importe_seguro(f.get("_importe_visual")),
            "Referencia": f.get("referencia") or "",
            "Concepto": f.get("concepto") or f.get("descripcion") or "",
        }
        for f in facturas_filtradas
    ])

    st.markdown("### Listado filtrado")

    gb = GridOptionsBuilder.from_dataframe(df_grid)

    gb.configure_default_column(
        sortable=True,
        filter=True,
        resizable=True
    )

    gb.configure_selection(
        selection_mode="single",
        use_checkbox=False
    )

    gb.configure_column("ID", width=90)
    gb.configure_column("Número", width=180)
    gb.configure_column("Tipo", width=110)
    gb.configure_column("Tercero", width=220)
    gb.configure_column("Fecha", width=120)
    gb.configure_column("Vencimiento", width=130)
    gb.configure_column("Estado", width=120)
    gb.configure_column("Importe_num", hide=True)
    gb.configure_column("Importe", width=130)
    gb.configure_column("Referencia", width=160, hide=True)
    gb.configure_column("Concepto", width=280, hide=True)

    gb.configure_pagination(
        enabled=True,
        paginationAutoPageSize=False,
        paginationPageSize=12
    )

    grid_options = gb.build()

    respuesta_grid = AgGrid(
        df_grid,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=False,
        enable_enterprise_modules=False,
        height=360,
        theme="streamlit",
        key="grid_facturas_principal"
    )

    fila_seleccionada = None

    if respuesta_grid and "selected_rows" in respuesta_grid:
        seleccionadas = respuesta_grid["selected_rows"]

        if seleccionadas is not None:
            if isinstance(seleccionadas, pd.DataFrame):
                if not seleccionadas.empty:
                    fila_seleccionada = seleccionadas.iloc[0].to_dict()

            elif isinstance(seleccionadas, list):
                if len(seleccionadas) > 0:
                    primera = seleccionadas[0]

                    if isinstance(primera, dict):
                        fila_seleccionada = primera
                    elif isinstance(primera, pd.Series):
                        fila_seleccionada = primera.to_dict()

            elif isinstance(seleccionadas, dict):
                fila_seleccionada = seleccionadas

    if fila_seleccionada:
        factura_id_sel = fila_seleccionada.get("ID")
        for f in facturas_filtradas:
            if str(f.get("id")) == str(factura_id_sel):
                st.session_state["factura_seleccionada_id"] = f.get("id")
                break

    factura = None
    factura_id_guardada = st.session_state.get("factura_seleccionada_id")

    if factura_id_guardada is not None:
        for f in facturas_filtradas:
            if str(f.get("id")) == str(factura_id_guardada):
                factura = f
                break

    if factura is None and facturas_filtradas:
        factura = facturas_filtradas[0]
        st.session_state["factura_seleccionada_id"] = factura.get("id")

    if factura is None:
        st.info("Selecciona una factura en la tabla para ver su ficha.")
        return

    numero = factura.get("numero_factura") or factura.get("numero") or f"Factura #{factura.get('id')}"
    tercero = (
    factura.get("nombre_tercero")
    or factura.get("cliente")
    or factura.get("proveedor")
    or factura.get("tercero")
    or "No informado"
)
    fecha = factura.get("fecha") or factura.get("fecha_emision") or ""
    vencimiento = factura.get("fecha_vencimiento") or factura.get("vencimiento") or ""
    concepto = factura.get("concepto") or factura.get("descripcion") or ""
    estado_visual = factura.get("_estado_visual")
    badge_class = factura.get("_badge_class")
    total = factura.get("_importe_visual")
    tipo = str(factura.get("tipo") or factura.get("tipo_factura") or "compra").strip().lower()
    referencia = factura.get("referencia") or ""
    forma_pago = factura.get("forma_pago") or factura.get("metodo_pago") or ""
    base = factura.get("base_imponible") or factura.get("base") or 0
    impuesto = factura.get("cuota_impuesto") or factura.get("cuota_iva") or factura.get("iva") or factura.get("impuesto") or 0
    origen = factura.get("origen") or factura.get("origen_documento") or factura.get("canal_origen") or ""

    etiqueta_tipo = "Factura de compra" if tipo == "compra" else "Abono / rectificativa" if tipo in ("abono_venta", "venta_rectificativa") else "Factura de venta" if tipo == "venta" else "Factura"

    st.markdown("### Detalle de factura seleccionada")

    col_a, col_b = st.columns([1.05, 0.95])

    with col_a:
        st.markdown(f"""
            <div class="factura-mini-card">
                <div class="titulo">{numero}</div>
                <div class="sub"><strong>Tipo:</strong> {etiqueta_tipo}</div>
                <div class="sub"><strong>Tercero:</strong> {tercero}</div>
                <div class="sub"><strong>Fecha:</strong> {fecha}</div>
                <div class="sub"><strong>Vencimiento:</strong> {vencimiento}</div>
                <div class="sub"><strong>Referencia:</strong> {referencia if referencia else "Sin referencia"}</div>
                <div class="sub"><strong>Forma de pago:</strong> {forma_pago if forma_pago else "No informada"}</div>
                <div class="sub"><strong>Base:</strong> {formatear_importe_seguro(base)}</div>
                <div class="sub"><strong>Impuesto:</strong> {formatear_importe_seguro(impuesto)}</div>
                <div class="sub"><strong>Total:</strong> {formatear_importe_seguro(total)}</div>
                <div class="sub"><strong>Origen:</strong> {origen if origen else "No informado"}</div>
                <div class="sub"><strong>Concepto:</strong> {concepto}</div>
                <div class="badge-estado {badge_class}">{estado_visual}</div>
            </div>
        """, unsafe_allow_html=True)
        estado_actual_tmp = str(estado_visual or "").strip().lower()

        if estado_actual_tmp in ("pendiente", "vencida"):
            st.markdown("#### Registrar cobro")

            cc1, cc2, cc3 = st.columns(3)

            with cc1:
                fecha_cobro = st.date_input(
                    "Fecha cobro",
                    value=datetime.datetime.today().date(),
                    key=f"fecha_cobro_factura_{factura.get('id')}"
                )

            with cc2:
                forma_cobro = st.selectbox(
                    "Medio de cobro",
                    ["transferencia", "efectivo"],
                    key=f"forma_cobro_factura_{factura.get('id')}"
                )

            with cc3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Registrar cobro", key=f"registrar_cobro_factura_{factura.get('id')}"):
                    resultado_cobro = registrar_cobro_factura(
                        factura_id=factura.get("id"),
                        fecha_cobro=str(fecha_cobro),
                        forma_cobro=forma_cobro
                    )

                    if resultado_cobro.get("ok"):
                        st.success(
                            f"{resultado_cobro.get('mensaje')} "
                            f"Asiento de cobro ID {resultado_cobro.get('asiento_id')}"
                        )
                        st.rerun()
                    else:
                        st.error(resultado_cobro.get("mensaje"))
        else:
            st.success("Esta factura ya está cobrada/pagada.")

    with col_b:
        html_factura = generar_html_ficha_factura(factura)

        st.download_button(
            "Descargar ficha imprimible (.html)",
            data=html_factura,
            file_name=f"factura_{factura.get('id', 'sin_id')}.html",
            mime="text/html",
            key=f"descargar_factura_{factura.get('id')}"
        )

        with st.expander("Vista previa imprimible", expanded=True):
            st.components.v1.html(html_factura, height=720, scrolling=True)

def pantalla_nueva_factura_venta(cursor):
    st.markdown("""
        <div class="subnav-shell">
            <div class="subnav-title">Nueva factura de venta</div>
        </div>
    """, unsafe_allow_html=True)

    numero_sugerido = generar_siguiente_numero_factura_venta()

    with st.form("form_nueva_factura_venta", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            nombre_cliente = st.text_input("Cliente", key="fv_nombre_cliente")
            fecha_emision = st.date_input("Fecha emisión", key="fv_fecha_emision")
            concepto = st.text_area("Concepto", key="fv_concepto")

        with col2:
            numero_factura = st.text_input("Número factura", value=numero_sugerido, key="fv_numero_factura")
            fecha_vencimiento = st.date_input("Fecha vencimiento", key="fv_fecha_vencimiento")
            forma_pago = st.selectbox(
                "Forma de pago",
                ["TRANSFERENCIA", "EFECTIVO", "TARJETA", "BIZUM", "DOMICILIACIÓN", "OTRO"],
                key="fv_forma_pago"
            )

        col3, col4, col5 = st.columns(3)

        with col3:
            base_imponible = st.number_input(
                "Base imponible",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                key="fv_base_imponible"
            )

        with col4:
            tipo_impuesto = st.number_input(
                "Tipo impuesto (%)",
                min_value=0.0,
                step=0.1,
                format="%.1f",
                value=7.0,
                key="fv_tipo_impuesto"
            )

        with col5:
            observaciones = st.text_input("Observaciones", key="fv_observaciones")

        totales = calcular_totales_factura_venta(base_imponible, tipo_impuesto)

        st.markdown("### Resumen")
        r1, r2, r3 = st.columns(3)

        with r1:
            st.metric("Base", formatear_importe_seguro(totales["base_imponible"]))

        with r2:
            st.metric("Impuesto", formatear_importe_seguro(totales["cuota_impuesto"]))

        with r3:
            st.metric("Total", formatear_importe_seguro(totales["total"]))

        b1, b2 = st.columns(2)

        with b1:
            guardar = st.form_submit_button("Guardar factura de venta")

        with b2:
            guardar_y_cobrar = st.form_submit_button("Guardar y registrar cobro")

    if guardar or guardar_y_cobrar:
        if not str(nombre_cliente).strip():
            st.error("Debes indicar el cliente.")
            return

        if not str(concepto).strip():
            st.error("Debes indicar el concepto.")
            return

        resultado = registrar_factura(
            tipo="venta",
            nombre_tercero=nombre_cliente.strip(),
            nif_tercero="",
            fecha_emision=str(fecha_emision),
            fecha_operacion=str(fecha_emision),
            concepto=concepto.strip(),
            base_imponible=base_imponible,
            impuesto_pct=tipo_impuesto,
            forma_pago=forma_pago.lower(),
            numero_factura=str(numero_factura).strip(),
            serie="FV",
            fecha_vencimiento=str(fecha_vencimiento),
            observaciones=observaciones.strip(),
            moneda="EUR"
        )
        if resultado.get("ok"):
            if guardar_y_cobrar:
                st.success(
                    f"Factura creada y cobrada correctamente. "
                    f"Factura ID {resultado['factura_id']} | "
                    f"Asiento factura ID {resultado['asiento_id']} | "
                    f"Total {resultado['total']:.2f} €"
                )
            else:
                st.success(
                    f"Factura creada correctamente. "
                    f"Factura ID {resultado['factura_id']} | "
                    f"Asiento ID {resultado['asiento_id']} | "
                    f"Total {resultado['total']:.2f} €"
                )

            st.session_state["factura_seleccionada_id"] = resultado["factura_id"]
            estado_factura_visual_tmp = "pendiente"

            if guardar_y_cobrar:
                resultado_cobro = marcar_factura_como_cobrada_y_registrar_cobro(
                    factura_id=resultado["factura_id"],
                    forma_pago=forma_pago.lower(),
                    fecha_cobro=str(fecha_emision)
                )

                if resultado_cobro.get("ok"):
                    st.success(
                        f"Cobro registrado correctamente. "
                        f"Asiento de cobro ID {resultado_cobro['asiento_id']}"
                    )
                    estado_factura_visual_tmp = "pagada"
                else:
                    st.error(f"La factura se creó, pero no se pudo registrar el cobro: {resultado_cobro.get('mensaje')}")

            st.session_state["ultima_factura_venta_creada"] = {
                "id": resultado["factura_id"],
                "tipo": "venta",
                "numero_factura": str(numero_factura).strip(),
                "numero": str(numero_factura).strip(),
                "nombre_tercero": nombre_cliente.strip(),
                "fecha": str(fecha_emision),
                "fecha_emision": str(fecha_emision),
                "fecha_vencimiento": str(fecha_vencimiento),
                "vencimiento": str(fecha_vencimiento),
                "concepto": concepto.strip(),
                "descripcion": concepto.strip(),
                "base_imponible": totales["base_imponible"],
                "base": totales["base_imponible"],
                "cuota_impuesto": totales["cuota_impuesto"],
                "cuota_iva": totales["cuota_impuesto"],
                "iva": totales["cuota_impuesto"],
                "impuesto": totales["cuota_impuesto"],
                "total": totales["total"],
                "importe_total": totales["total"],
                "estado": estado_factura_visual_tmp,
                "forma_pago": forma_pago,
                "observaciones": observaciones.strip(),
                "moneda": "EUR"
            }

        else:
            st.error(f"No se pudo crear la factura: {resultado.get('mensaje')}")
    factura_reciente = st.session_state.get("ultima_factura_venta_creada")

    if factura_reciente:
        st.markdown("### Factura lista para entregar")

        html_factura = generar_html_ficha_factura(factura_reciente)

        html_factura_imprimible = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Factura {factura_reciente.get('numero_factura', '')}</title>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: #f4f7fb;
                    font-family: Arial, sans-serif;
                }}

                .topbar {{
                    position: sticky;
                    top: 0;
                    z-index: 1000;
                    background: white;
                    border-bottom: 1px solid #dbe3ee;
                    padding: 12px 18px;
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                }}

                .btn-print {{
                    background: linear-gradient(135deg, #0f172a 0%, #2563eb 100%);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 10px 16px;
                    font-size: 14px;
                    font-weight: 700;
                    cursor: pointer;
                }}

                .btn-print:hover {{
                    opacity: 0.92;
                }}

                .contenido {{
                    padding: 0;
                    margin: 0;
                }}

                @media print {{
                    .topbar {{
                        display: none !important;
                    }}

                    body {{
                        background: white !important;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="topbar">
                <button class="btn-print" onclick="window.print()">Imprimir factura</button>
            </div>
            <div class="contenido">
                {html_factura}
            </div>
        </body>
        </html>
        """

        col_p1, col_p2 = st.columns([0.28, 0.72])

        with col_p1:
            st.download_button(
                "Descargar factura (.html)",
                data=html_factura_imprimible,
                file_name=f"factura_{factura_reciente.get('numero_factura', 'sin_numero')}.html",
                mime="text/html",
                key="descargar_ultima_factura_venta"
            )

            if st.button("Quitar vista previa", key="quitar_vista_previa_factura_venta"):
                st.session_state.pop("ultima_factura_venta_creada", None)
                st.rerun()

        with col_p2:
            st.components.v1.html(
                html_factura_imprimible,
                height=900,
                scrolling=True
            )

def pantalla_clientes(cursor):
    st.markdown('<div class="section-title">Clientes</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["Listado", "Alta", "Editar / Borrar", "Ficha"])

    with tab1:
        df = listar_terceros("cliente")
        if df.empty:
            st.info("No hay clientes registrados.")
        else:
            st.dataframe(df, use_container_width=True)

    with tab2:
        nombre = st.text_input("Nombre cliente", key="alta_cliente_nombre")
        nif = st.text_input("NIF", key="alta_cliente_nif")
        direccion = st.text_input("Dirección", key="alta_cliente_direccion")
        email = st.text_input("Email", key="alta_cliente_email")
        telefono = st.text_input("Teléfono", key="alta_cliente_telefono")

        if st.button("Crear cliente", key="crear_cliente_btn"):
            resultado = crear_tercero(
                "cliente",
                nombre=nombre,
                nif=nif,
                direccion=direccion,
                email=email,
                telefono=telefono,
            )
            if resultado["ok"]:
                st.success(resultado["mensaje"])
                st.rerun()
            else:
                st.error(resultado["mensaje"])

    with tab3:
        df = listar_terceros("cliente")
        if df.empty:
            st.info("No hay clientes para editar o borrar.")
        else:
            opciones = {f"{row['id']} - {row['nombre']}": int(row["id"]) for _, row in df.iterrows()}
            seleccion = st.selectbox("Selecciona cliente", list(opciones.keys()), key="editar_cliente_select")
            cliente_id = opciones[seleccion]

            tercero = obtener_tercero("cliente", cliente_id)

            nombre = st.text_input("Nombre", value=tercero["nombre"], key="edit_cliente_nombre")
            nif = st.text_input("NIF", value=tercero["nif"], key="edit_cliente_nif")
            direccion = st.text_input("Dirección", value=tercero["direccion"], key="edit_cliente_direccion")
            email = st.text_input("Email", value=tercero["email"], key="edit_cliente_email")
            telefono = st.text_input("Teléfono", value=tercero["telefono"], key="edit_cliente_telefono")

            c1, c2 = st.columns(2)

            with c1:
                if st.button("Guardar cambios", key="guardar_cliente_btn"):
                    resultado = actualizar_tercero(
                        "cliente",
                        tercero_id=cliente_id,
                        nombre=nombre,
                        nif=nif,
                        direccion=direccion,
                        email=email,
                        telefono=telefono,
                    )
                    if resultado["ok"]:
                        st.success(resultado["mensaje"])
                        st.rerun()
                    else:
                        st.error(resultado["mensaje"])

            with c2:
                if "confirmar_borrar_cliente" not in st.session_state:
                    st.session_state["confirmar_borrar_cliente"] = False

                if not st.session_state["confirmar_borrar_cliente"]:
                    if st.button("Borrar cliente", key="borrar_cliente_btn"):
                        st.session_state["confirmar_borrar_cliente"] = True
                else:
                    st.warning(f"Vas a borrar el cliente ID {cliente_id}.")
                    cc1, cc2 = st.columns(2)

                    with cc1:
                        if st.button("Sí, borrar", key="confirmar_borrar_cliente_si"):
                            resultado = borrar_tercero("cliente", cliente_id)
                            st.session_state["confirmar_borrar_cliente"] = False
                            if resultado["ok"]:
                                st.success(resultado["mensaje"])
                                st.rerun()
                            else:
                                st.error(resultado["mensaje"])

                    with cc2:
                        if st.button("Cancelar", key="confirmar_borrar_cliente_no"):
                            st.session_state["confirmar_borrar_cliente"] = False

    with tab4:
        df = listar_terceros("cliente")
        if df.empty:
            st.info("No hay clientes para consultar.")
        else:
            opciones = {f"{row['id']} - {row['nombre']}": int(row["id"]) for _, row in df.iterrows()}
            seleccion = st.selectbox("Selecciona cliente para ver ficha", list(opciones.keys()), key="ficha_cliente_select")
            cliente_id = opciones[seleccion]

            ficha = metricas_tercero("cliente", cliente_id)

            if ficha:
                tercero = ficha["tercero"]

                st.write(f"**Nombre:** {tercero['nombre']}")
                st.write(f"**NIF:** {tercero['nif']}")
                st.write(f"**Dirección:** {tercero['direccion']}")
                st.write(f"**Email:** {tercero['email']}")
                st.write(f"**Teléfono:** {tercero['telefono']}")
                st.markdown("### Scoring del cliente")

                if st.button("Recalcular scoring", key=f"recalcular_scoring_cliente_{cliente_id}"):
                    resultado_scoring = recalcular_y_guardar_scoring(cliente_id)
                    st.session_state[f"scoring_cliente_{cliente_id}"] = resultado_scoring

                if f"scoring_cliente_{cliente_id}" in st.session_state:
                    resultado_scoring = st.session_state[f"scoring_cliente_{cliente_id}"]

                    color = str(resultado_scoring["color"]).lower()
                    decision = str(resultado_scoring["decision"]).lower()

                    if color == "verde":
                        icono = "🟢"
                        titulo_estado = "Cliente sano"
                    elif color == "amarillo":
                        icono = "🟡"
                        titulo_estado = "Cliente con atención"
                    else:
                        icono = "🔴"
                        titulo_estado = "Cliente de riesgo"

                    if decision == "trabajar":
                        decision_txt = "Trabajar"
                    elif decision == "trabajar_con_limites":
                        decision_txt = "Trabajar con límites"
                    else:
                        decision_txt = "Revisar o bloquear"

                    if color == "verde":
                        st.success(f"{icono} {titulo_estado}")
                    elif color == "amarillo":
                        st.warning(f"{icono} {titulo_estado}")
                    else:
                        st.error(f"{icono} {titulo_estado}")

                    st.write(f"**Decisión recomendada:** {decision_txt}")
                    st.info(resultado_scoring["motivo"])

                    col_sc1, col_sc2, col_sc3 = st.columns(3)

                    with col_sc1:
                        st.metric("Scoring", resultado_scoring["puntuacion"])

                    with col_sc2:
                        st.metric("Semáforo", resultado_scoring["color"].capitalize())

                    with col_sc3:
                        st.metric("Decisión", decision_txt)

                    col_sc4, col_sc5, col_sc6 = st.columns(3)

                    with col_sc4:
                        st.metric("Facturas pendientes", resultado_scoring["pendientes"])

                    with col_sc5:
                        st.metric("Saldo pendiente", f"{resultado_scoring['saldo_pendiente']:.2f} €")

                    with col_sc6:
                        st.metric("Días de deuda", resultado_scoring["dias_deuda"])

                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Facturas", ficha["total_facturas"])
                with col2:
                    st.metric("Operaciones", ficha["total_operaciones"])
                with col3:
                    st.metric("Volumen total", f"{ficha['volumen_total']:.2f} €")
                with col4:
                    st.metric("Cobrado", f"{ficha['volumen_cerrado']:.2f} €")
                with col5:
                    st.metric("Pendiente", f"{ficha['saldo_pendiente']:.2f} €")

                st.write(f"**Forma de pago habitual:** {ficha['forma_pago_habitual'] or '-'}")

                st.subheader("Últimas facturas")
                st.dataframe(ficha["facturas"], use_container_width=True)
                st.subheader("Últimas operaciones")
                st.dataframe(ficha["operaciones"], use_container_width=True)

def pantalla_proveedores(cursor):
    st.markdown('<div class="section-title">Proveedores</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["Listado", "Alta", "Editar / Borrar", "Ficha"])

    with tab1:
        df = listar_terceros("proveedor")
        if df.empty:
            st.info("No hay proveedores registrados.")
        else:
            st.dataframe(df, use_container_width=True)

    with tab2:
        nombre = st.text_input("Nombre proveedor", key="alta_proveedor_nombre")
        nif = st.text_input("NIF", key="alta_proveedor_nif")
        direccion = st.text_input("Dirección", key="alta_proveedor_direccion")
        email = st.text_input("Email", key="alta_proveedor_email")
        telefono = st.text_input("Teléfono", key="alta_proveedor_telefono")

        if st.button("Crear proveedor", key="crear_proveedor_btn"):
            resultado = crear_tercero(
                "proveedor",
                nombre=nombre,
                nif=nif,
                direccion=direccion,
                email=email,
                telefono=telefono,
            )
            if resultado["ok"]:
                st.success(resultado["mensaje"])
                st.rerun()
            else:
                st.error(resultado["mensaje"])

    with tab3:
        df = listar_terceros("proveedor")
        if df.empty:
            st.info("No hay proveedores para editar o borrar.")
        else:
            opciones = {f"{row['id']} - {row['nombre']}": int(row["id"]) for _, row in df.iterrows()}
            seleccion = st.selectbox("Selecciona proveedor", list(opciones.keys()), key="editar_proveedor_select")
            proveedor_id = opciones[seleccion]

            tercero = obtener_tercero("proveedor", proveedor_id)

            nombre = st.text_input("Nombre", value=tercero["nombre"], key="edit_proveedor_nombre")
            nif = st.text_input("NIF", value=tercero["nif"], key="edit_proveedor_nif")
            direccion = st.text_input("Dirección", value=tercero["direccion"], key="edit_proveedor_direccion")
            email = st.text_input("Email", value=tercero["email"], key="edit_proveedor_email")
            telefono = st.text_input("Teléfono", value=tercero["telefono"], key="edit_proveedor_telefono")

            c1, c2 = st.columns(2)

            with c1:
                if st.button("Guardar cambios", key="guardar_proveedor_btn"):
                    resultado = actualizar_tercero(
                        "proveedor",
                        tercero_id=proveedor_id,
                        nombre=nombre,
                        nif=nif,
                        direccion=direccion,
                        email=email,
                        telefono=telefono,
                    )
                    if resultado["ok"]:
                        st.success(resultado["mensaje"])
                        st.rerun()
                    else:
                        st.error(resultado["mensaje"])

            with c2:
                if "confirmar_borrar_proveedor" not in st.session_state:
                    st.session_state["confirmar_borrar_proveedor"] = False

                if not st.session_state["confirmar_borrar_proveedor"]:
                    if st.button("Borrar proveedor", key="borrar_proveedor_btn"):
                        st.session_state["confirmar_borrar_proveedor"] = True
                else:
                    st.warning(f"Vas a borrar el proveedor ID {proveedor_id}.")

                    cc1, cc2 = st.columns(2)

                    with cc1:
                        if st.button("Sí, borrar", key="confirmar_borrar_proveedor_si"):
                            resultado = borrar_tercero("proveedor", proveedor_id)
                            st.session_state["confirmar_borrar_proveedor"] = False
                            if resultado["ok"]:
                                st.success(resultado["mensaje"])
                                st.rerun()
                            else:
                                st.error(resultado["mensaje"])

                    with cc2:
                        if st.button("Cancelar", key="confirmar_borrar_proveedor_no"):
                            st.session_state["confirmar_borrar_proveedor"] = False

    with tab4:
        df = listar_terceros("proveedor")
        if df.empty:
            st.info("No hay proveedores para consultar.")
        else:
            opciones = {f"{row['id']} - {row['nombre']}": int(row["id"]) for _, row in df.iterrows()}
            seleccion = st.selectbox("Selecciona proveedor para ver ficha", list(opciones.keys()), key="ficha_proveedor_select")
            proveedor_id = opciones[seleccion]

            ficha = metricas_tercero("proveedor", proveedor_id)

            if ficha:
                tercero = ficha["tercero"]

                st.write(f"**Nombre:** {tercero['nombre']}")
                st.write(f"**NIF:** {tercero['nif']}")
                st.write(f"**Dirección:** {tercero['direccion']}")
                st.write(f"**Email:** {tercero['email']}")
                st.write(f"**Teléfono:** {tercero['telefono']}")

                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Facturas", ficha["total_facturas"])
                with col2:
                    st.metric("Operaciones", ficha["total_operaciones"])
                with col3:
                    st.metric("Volumen total", f"{ficha['volumen_total']:.2f} €")
                with col4:
                    st.metric("Pagado", f"{ficha['volumen_cerrado']:.2f} €")
                with col5:
                    st.metric("Pendiente", f"{ficha['saldo_pendiente']:.2f} €")

                st.write(f"**Forma de pago habitual:** {ficha['forma_pago_habitual'] or '-'}")

                st.subheader("Últimas facturas")
                st.dataframe(ficha["facturas"], use_container_width=True)
                st.subheader("Últimas operaciones")
                st.dataframe(ficha["operaciones"], use_container_width=True)

def pantalla_importar_excel():
    st.markdown('<div class="section-title">Importar Excel</div>', unsafe_allow_html=True)

    archivo = st.file_uploader("Subir archivo Excel", type=["xlsx"])

    if archivo is not None:
        st.session_state["archivo_excel"] = archivo
        tipo_excel, df, mapeo_sugerido = leer_excel(archivo)

        if tipo_excel == "movimientos":
            st.success("Excel detectado como MOVIMIENTOS")
            df = clasificar_dataframe_movimientos(df)
            st.subheader("Vista previa de movimientos clasificados")
            st.dataframe(df, use_container_width=True)

            if "confirmar_importacion_movimientos" not in st.session_state:
                st.session_state.confirmar_importacion_movimientos = False

            if st.button("Importar movimientos a la contabilidad"):
                st.session_state.confirmar_importacion_movimientos = True

            if st.session_state.confirmar_importacion_movimientos:
                st.warning("¿Estás seguro de que quieres convertir estos movimientos en asientos contables?")
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Sí, importar movimientos"):
                        archivo_bytes = st.session_state["archivo_excel"].getvalue()
                        resultado = importar_movimientos_desde_excel(
                            df,
                            st.session_state["archivo_excel"].name,
                            archivo_bytes
                        )

                        if resultado == "duplicado":
                            st.warning("Este archivo ya fue importado anteriormente")
                        else:
                            st.success("Movimientos importados correctamente a la contabilidad")

                        st.session_state.confirmar_importacion_movimientos = False

                with col2:
                    if st.button("Cancelar importación movimientos"):
                        st.session_state.confirmar_importacion_movimientos = False

        elif tipo_excel == "asientos":
            st.success("Excel detectado como ASIENTOS")
            st.subheader("Vista previa de asientos")
            st.dataframe(df, use_container_width=True)

            if "confirmar_importacion" not in st.session_state:
                st.session_state.confirmar_importacion = False

            if st.button("Importar asientos a la contabilidad"):
                st.session_state.confirmar_importacion = True

            if st.session_state.confirmar_importacion:
                st.warning("¿Estás seguro de que quieres importar este Excel a la contabilidad?")
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Sí, importar"):
                        archivo_bytes = st.session_state["archivo_excel"].getvalue()
                        resultado = importar_asientos_desde_excel(
                            df,
                            st.session_state["archivo_excel"].name,
                            archivo_bytes
                        )

                        if isinstance(resultado, dict) and resultado.get("estado") == "duplicado":
                            st.warning("Este archivo ya fue importado anteriormente")
                        elif isinstance(resultado, dict) and resultado.get("estado") == "error_columnas":
                            faltantes = resultado.get("detalle", [])
                            st.error(f"Faltan columnas obligatorias: {', '.join(faltantes)}")
                        elif isinstance(resultado, dict) and resultado.get("estado") == "sin_lineas":
                            st.error("El Excel no contiene líneas válidas para formar asientos")
                        elif isinstance(resultado, dict) and not resultado.get("ok", False):

                            st.error("Error al importar asientos")

                            st.write("Resultado completo:")
                            st.json(resultado)

                            if "detalle" in resultado:
                                st.code(resultado["detalle"], language="python")
                        else:
                            st.success(
                                f"Asientos importados correctamente: {resultado.get('importados', 0)} | "
                                f"Asientos totales en BD: {resultado.get('total_asientos_bd', 'N/D')}"
                        )
                            if resultado.get("num_errores", 0) > 0:
                                st.warning(f"Errores detectados: {resultado['num_errores']}")
                                st.dataframe(pd.DataFrame(resultado["errores"]), use_container_width=True)

                        st.session_state.confirmar_importacion = False

                with col2:
                    if st.button("Cancelar"):
                        st.session_state.confirmar_importacion = False

        elif tipo_excel == "facturas":
            st.success("Excel detectado como FACTURAS")
            st.subheader("Vista previa de facturas")
            st.dataframe(df, use_container_width=True)

            opciones_auto = inferir_opciones_importacion(df, mapeo_sugerido)

            st.info(
                f"Importación automática preparada. "
                f"Tipo de tercero detectado: {opciones_auto['tipo_tercero']}. "
                f"Se crearán terceros, asientos y vencimientos si procede."
            )

            if "confirmar_importacion_facturas" not in st.session_state:
                st.session_state.confirmar_importacion_facturas = False

            if st.button("Importar automáticamente"):
                st.session_state.confirmar_importacion_facturas = True

            if st.session_state.confirmar_importacion_facturas:
                st.warning("¿Estás seguro de que quieres importar este documento?")

                c1, c2 = st.columns(2)

                with c1:
                    if st.button("Sí, importar facturas"):
                        archivo_bytes = st.session_state["archivo_excel"].getvalue()

                        resultado = importar_documento_facturas(
                            df,
                            st.session_state["archivo_excel"].name,
                            archivo_bytes,
                            mapeo_sugerido,
                            opciones_auto
                        )

                        st.session_state["ultimo_resultado_importacion_facturas"] = resultado
                        st.session_state.confirmar_importacion_facturas = False

                        if isinstance(resultado, dict) and resultado.get("estado") == "duplicado":
                            st.warning("Este archivo ya fue importado anteriormente")

                        elif isinstance(resultado, dict) and not resultado.get("ok", False):
                            st.error(resultado.get("detalle", str(resultado)))

                        else:
                            st.success(
                                f"Facturas importadas: {resultado.get('importadas', 0)}. "
                                f"Los asientos creados quedan registrados con tipo 'factura_importada_excel'."
                            )
                            st.rerun()

                with c2:
                    if st.button("Cancelar importación facturas"):
                        st.session_state.confirmar_importacion_facturas = False

            resultado_facturas = st.session_state.get("ultimo_resultado_importacion_facturas")

            if isinstance(resultado_facturas, dict) and resultado_facturas.get("ok", False):
                if resultado_facturas.get("num_errores", 0) > 0:
                    st.warning(f"Errores detectados: {resultado_facturas['num_errores']}")

                    df_errores = pd.DataFrame(resultado_facturas["errores"])

                    for i, row in df_errores.iterrows():
                        col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])

                        with col1:
                            st.write(row.get("fila_excel"))

                        with col2:
                            st.write(row.get("tercero"))

                        with col3:
                            st.write(row.get("numero_factura"))

                        with col4:
                            st.write(row.get("error"))

                        with col5:
                            if st.button("🔧", key=f"editar_error_factura_{i}"):
                                st.session_state["error_en_edicion_factura"] = dict(row)
                                st.rerun()

            if "error_en_edicion_factura" in st.session_state:

                error = st.session_state["error_en_edicion_factura"]

                st.divider()

                with st.container():
                    st.markdown("### 🛠️ Resolución de incidencia")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Fila Excel", error.get("fila_excel"))

                    with col2:
                        st.metric("Tercero", error.get("tercero"))

                    with col3:
                        st.metric("Factura", error.get("numero_factura"))

                    with col4:
                        st.metric("Error", error.get("error"))

                    st.divider()

                    accion = st.radio(
                        "¿Qué quieres hacer con esta incidencia?",
                        [
                            "Corregir total",
                            "Importar como abono",
                            "Dejar pendiente",
                            "Cancelar"
                        ],
                        key="accion_error_factura"
                    )

                    st.divider()

                    if accion == "Corregir total":

                        nuevo_total = st.number_input(
                            "Total corregido",
                            value=0.0,
                            step=0.01,
                            key="edit_total_factura"
                        )

                        if st.button("✅ Reintentar con total corregido", key="btn_reintentar_total_factura"):

                            try:
                                importar_linea_corregida(
                                    df=df,
                                    fila_excel=error.get("fila_excel"),
                                    tercero=error.get("tercero"),
                                    numero_factura=error.get("numero_factura"),
                                    total=-abs(total_abono)
                                )

                                st.success("Factura corregida e importada")

                                del st.session_state["error_en_edicion_factura"]
                                st.rerun()

                            except Exception as e:
                                st.error(f"Error: {e}")

                    elif accion == "Importar como abono":

                        st.info("Se importará como factura rectificativa o abono")

                        fila_excel_error = int(error.get("fila_excel"))
                        idx_df_error = fila_excel_error - 2

                        total_detectado_abono = 0.0
                        if 0 <= idx_df_error < len(df):
                            valor_excel = df.iloc[idx_df_error].get("total", 0)
                            try:
                                total_detectado_abono = round(abs(float(valor_excel)), 2)
                            except Exception:
                                total_detectado_abono = 0.0

                        total_abono = st.number_input(
                            "Importe del abono",
                            value=float(total_detectado_abono),
                            step=0.01,
                            key="edit_total_abono_factura"
                        )
                        if st.button("↩️ Importar como abono", key="btn_importar_abono_factura"):

                            try:
                                importar_linea_corregida(
                                    df=df,
                                    fila_excel=error.get("fila_excel"),
                                    tercero=error.get("tercero"),
                                    numero_factura=error.get("numero_factura"),
                                    total=-abs(total_abono)
                                )

                                st.success("Importado como abono")

                                del st.session_state["error_en_edicion_factura"]
                                st.rerun()

                            except Exception as e:
                                st.error(f"Error: {e}")

                    elif accion == "Dejar pendiente":

                        comentario = st.text_area(
                            "Comentario (opcional)",
                            key="comentario_pendiente_factura"
                        )

                        if st.button("🕒 Guardar para revisar después", key="btn_guardar_pendiente_factura"):
                            st.info("Incidencia dejada pendiente para revisión manual.")
                            del st.session_state["error_en_edicion_factura"]
                            st.rerun()

                    elif accion == "Cancelar":

                        if st.button("❌ Cancelar corrección", key="btn_cancelar_factura"):
                            del st.session_state["error_en_edicion_factura"]
                            st.rerun()

        elif tipo_excel == "pagos_proveedor":
            st.success("Excel detectado como PAGOS A PROVEEDORES / VENCIMIENTOS DE PAGO")
            st.subheader("Vista previa de pagos a proveedores")
            st.dataframe(df, use_container_width=True)

            if "confirmar_importacion_pagos_proveedor" not in st.session_state:
                st.session_state["confirmar_importacion_pagos_proveedor"] = False

            if st.button("Importar pagos a proveedores", key="btn_importar_pagos_proveedor"):
                st.session_state["confirmar_importacion_pagos_proveedor"] = True

            if st.session_state["confirmar_importacion_pagos_proveedor"]:
                st.warning("¿Estás seguro de que quieres importar este documento de pagos a proveedores?")

                c1, c2 = st.columns(2)

                with c1:
                    if st.button("Sí, importar pagos a proveedores", key="btn_confirmar_importar_pagos_proveedor"):
                        archivo_bytes = st.session_state["archivo_excel"].getvalue()

                        resultado = importar_pagos_proveedor_desde_excel(
                            df,
                            st.session_state["archivo_excel"].name,
                            archivo_bytes
                        )

                        st.session_state["confirmar_importacion_pagos_proveedor"] = False

                        if isinstance(resultado, dict) and resultado.get("estado") == "duplicado":
                            st.warning("Este archivo ya fue importado anteriormente")
                        elif isinstance(resultado, dict) and resultado.get("estado") == "error_columnas":
                            faltantes = resultado.get("detalle", [])
                            st.error(f"Faltan columnas obligatorias: {', '.join(faltantes)}")
                        elif isinstance(resultado, dict) and not resultado.get("ok", False):
                            st.error(resultado.get("detalle", str(resultado)))
        else:
            importadas = int(resultado.get("importadas", 0))
            num_errores = int(resultado.get("num_errores", 0))

            st.success(f"Pagos a proveedores importados: {importadas}")

            if num_errores > 0:
                st.warning(f"Errores detectados: {num_errores}")

                df_errores = pd.DataFrame(resultado["errores"])

                for i, row in df_errores.iterrows():
                    col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])

                    with col1:
                        st.write(row.get("fila_excel"))

                    with col2:
                        st.write(row.get("tercero"))

                    with col3:
                        st.write(row.get("numero_factura"))

                    with col4:
                        st.write(row.get("error"))

                    with col5:
                        if st.button("🔧", key=f"editar_error_{i}"):
                            st.session_state["error_en_edicion"] = dict(row)
                            st.rerun()

            if "error_en_edicion" in st.session_state:

                error = st.session_state["error_en_edicion"]

                st.divider()
                st.subheader("🛠️ Corregir incidencia")

                fila = error.get("fila_excel")

                nuevo_tercero = st.text_input(
                    "Tercero",
                    value=error.get("tercero", ""),
                    key="edit_tercero"
                )

                nuevo_numero = st.text_input(
                    "Número factura",
                    value=error.get("numero_factura", ""),
                    key="edit_numero"
                )

                nuevo_total = st.number_input(
                    "Total corregido",
                    value=0.0,
                    step=0.01,
                    key="edit_total"
                )

                col_a, col_b = st.columns(2)

                with col_a:
                    if st.button("✅ Reintentar importación"):

                        try:
                            resultado_reintento = importar_linea_corregida(
                                df=df,
                                fila_excel=fila,
                                tercero=nuevo_tercero,
                                numero_factura=nuevo_numero,
                                total=nuevo_total
                            )

                            st.success("Importado correctamente")

                            del st.session_state["error_en_edicion"]
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error: {e}")

                with col_b:
                    if st.button("❌ Cancelar"):
                        del st.session_state["error_en_edicion"]
                        st.rerun()

                with c2:
                    if st.button("Cancelar importación pagos a proveedores", key="btn_cancelar_importar_pagos_proveedor"):
                        st.session_state["confirmar_importacion_pagos_proveedor"] = False

            st.divider()
            st.markdown("### Mantenimiento importaciones")

            if st.button("🧹 Limpiar histórico de importaciones", key="btn_limpiar_historico_importaciones"):
                resultado_limpieza = limpiar_historico_importaciones()

                if resultado_limpieza.get("ok"):
                    st.success(resultado_limpieza.get("mensaje", "Histórico limpiado correctamente"))
                    st.rerun()
                else:
                    st.error(resultado_limpieza.get("mensaje", "No se pudo limpiar el histórico"))

def pantalla_ver_importaciones(cursor):
    st.markdown('<div class="section-title">Importaciones registradas</div>', unsafe_allow_html=True)

    cursor.execute("SELECT * FROM importaciones ORDER BY id DESC")
    importaciones = cursor.fetchall()

    if importaciones:
        try:
            df = pd.DataFrame(
                importaciones,
                columns=["ID", "Tipo", "Nombre archivo", "Hash archivo", "Fecha importacion"][:len(importaciones[0])]
            )
        except Exception:
            df = pd.DataFrame(importaciones)

        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No hay importaciones registradas")

    st.subheader("Mantenimiento")

    if st.button("Borrar asientos importados_excel no registrados"):
        resultado = borrar_asientos_importados_excel()
        if resultado == "ok":
            st.success("Asientos importados_excel borrados correctamente")
        else:
            st.warning("No hay asientos importados_excel para borrar")


def pantalla_conciliacion_bancaria():
    st.markdown('<div class="section-title">Conciliación bancaria con IA</div>', unsafe_allow_html=True)

    resumen = resumen_conciliacion()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Movimientos pendientes", resumen["movimientos_pendientes"])
    with col2:
        st.metric("Facturas pendientes", resumen["facturas_pendientes"])
    with col3:
        st.metric("Conciliaciones realizadas", resumen["conciliaciones_realizadas"])

    tab1, tab2, tab3, tab4 = st.tabs([
        "Movimientos bancarios",
        "Facturas pendientes",
        "Sugerencias IA",
        "Historial"
    ])

    with tab1:
        df = movimientos_pendientes()
        if df.empty:
            st.info("No hay movimientos bancarios pendientes")
        else:
            st.dataframe(df, use_container_width=True)

    with tab2:
        df = facturas_pendientes()
        if df.empty:
            st.info("No hay facturas pendientes")
        else:
            st.dataframe(df, use_container_width=True)

    with tab3:
        df = sugerencias_ia()
        if df.empty:
            st.info("No hay sugerencias disponibles")
        else:
            st.dataframe(df, use_container_width=True)

        st.subheader("Auto-conciliación")
        umbral = st.slider("Score mínimo", 0.50, 0.99, 0.85, 0.01)

        if st.button("Ejecutar auto-conciliación IA"):
            resultado = auto_conciliar_por_ia(score_minimo=umbral)
            if resultado.empty:
                st.info("No hubo conciliaciones automáticas")
            else:
                st.dataframe(resultado, use_container_width=True)

        st.subheader("Conciliación manual avanzada")

        df_mov = movimientos_pendientes()
        df_fac = facturas_pendientes()

        if df_mov.empty:
            st.info("No hay movimientos bancarios pendientes para conciliar.")
        elif df_fac.empty:
            st.info("No hay facturas pendientes para conciliar.")
        else:
            opciones_mov = {
                f"{int(row['id'])} | {row['fecha']} | {row['sentido']} | {float(row['importe']):.2f} € | {str(row['concepto'])[:80]}": int(row["id"])
                for _, row in df_mov.iterrows()
            }

            seleccion_mov = st.selectbox(
                "Selecciona movimiento bancario",
                list(opciones_mov.keys()),
                key="conciliacion_manual_movimiento_select"
            )

            movimiento_id = opciones_mov[seleccion_mov]
            fila_mov = df_mov[df_mov["id"] == movimiento_id].iloc[0]

            importe_movimiento = float(fila_mov["importe"])
            sentido_movimiento = str(fila_mov["sentido"]).strip().lower()

            st.write(f"**Importe movimiento:** {importe_movimiento:.2f} €")
            st.write(f"**Sentido:** {sentido_movimiento}")
            st.write(f"**Concepto:** {fila_mov['concepto']}")

            if sentido_movimiento == "ingreso":
                df_fac_filtrado = df_fac[df_fac["tipo"] == "venta"].copy()
                seleccion_auto_ids, importes_auto = _preseleccionar_facturas(
                    df_fac_filtrado,
                    importe_movimiento
                )
            else:
                df_fac_filtrado = df_fac[df_fac["tipo"] == "compra"].copy()

            if df_fac_filtrado.empty:
                st.warning("No hay facturas compatibles con el sentido del movimiento.")
            else:
                concepto_movimiento_txt = str(fila_mov["concepto"] or "")

                df_fac_filtrado["score_similitud"] = df_fac_filtrado.apply(
                    lambda row: _score_similitud_conciliacion(
                        concepto_movimiento=concepto_movimiento_txt,
                        nombre_tercero=row.get("nombre_tercero", ""),
                        concepto_factura=row.get("concepto", "")
                    ),
                    axis=1
                )

                # Ordenamos por score y, en empate, por fecha más reciente
                if "fecha_emision" in df_fac_filtrado.columns:
                    try:
                        df_fac_filtrado["fecha_emision_sort"] = pd.to_datetime(
                            df_fac_filtrado["fecha_emision"],
                            errors="coerce"
                        )
                    except Exception:
                        df_fac_filtrado["fecha_emision_sort"] = pd.NaT
                else:
                    df_fac_filtrado["fecha_emision_sort"] = pd.NaT

                df_fac_filtrado = df_fac_filtrado.sort_values(
                    by=["score_similitud", "fecha_emision_sort", "total"],
                    ascending=[False, False, False]
                ).copy()

                st.caption("Las facturas se muestran priorizadas por similitud con el concepto del movimiento bancario.")

                seleccion_auto_ids, importes_auto = _preseleccionar_facturas(
                    df_fac_filtrado,
                    importe_movimiento
                )

                registros = []
                for _, row in df_fac_filtrado.iterrows():
                    factura_id = int(row["id"])

                    seleccionada_auto = factura_id in seleccion_auto_ids
                    importe_auto = importes_auto.get(factura_id, float(row["total"]))

                    registros.append({
                        "Seleccionar": seleccionada_auto,
                        "Factura ID": factura_id,
                        "Score": int(row["score_similitud"]),
                        "Tipo": str(row["tipo"]),
                        "Tercero": str(row["nombre_tercero"]),
                        "Fecha": str(row["fecha_emision"]),
                        "Concepto": str(row["concepto"]),
                        "Total factura": float(row["total"]),
                        "Estado": str(row["estado"]),
                        "Importe a aplicar": float(importe_auto),
                    })

                df_editor = pd.DataFrame(registros)

                df_editado = st.data_editor(
                    df_editor,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="fixed",
                    column_config={
                        "Seleccionar": st.column_config.CheckboxColumn("Seleccionar"),
                        "Factura ID": st.column_config.NumberColumn("Factura ID", disabled=True),
                        "Score": st.column_config.NumberColumn("Score", disabled=True),
                        "Tipo": st.column_config.TextColumn("Tipo", disabled=True),
                        "Tercero": st.column_config.TextColumn("Tercero", disabled=True),
                        "Fecha": st.column_config.TextColumn("Fecha", disabled=True),
                        "Concepto": st.column_config.TextColumn("Concepto", disabled=True, width="large"),
                        "Total factura": st.column_config.NumberColumn("Total factura", format="%.2f", disabled=True),
                        "Estado": st.column_config.TextColumn("Estado", disabled=True),
                        "Importe a aplicar": st.column_config.NumberColumn("Importe a aplicar", format="%.2f", min_value=0.0),
                    },
                    key="editor_conciliacion_manual_multiple"
                )

                seleccionadas = df_editado[df_editado["Seleccionar"] == True].copy()

                total_aplicado = float(seleccionadas["Importe a aplicar"].fillna(0).astype(float).sum()) if not seleccionadas.empty else 0.0
                diferencia = round(importe_movimiento - total_aplicado, 2)

                c_man1, c_man2, c_man3 = st.columns(3)

                with c_man1:
                    st.metric("Importe movimiento", f"{importe_movimiento:.2f} €")

                with c_man2:
                    st.metric("Total aplicado", f"{total_aplicado:.2f} €")

                with c_man3:
                    st.metric("Diferencia", f"{diferencia:.2f} €")
                if abs(diferencia) < 0.01:
                    st.success("La propuesta automática cuadra exactamente con el movimiento.")
                elif diferencia > 0:
                    st.warning(f"Quedan {diferencia:.2f} € sin aplicar.")
                else:
                    st.error(f"Se está aplicando {abs(diferencia):.2f} € de más.")

                if seleccionadas.empty:
                    st.info("Marca una o varias facturas para aplicar la conciliación.")
                else:
                    facturas_importes = [
                        (int(row["Factura ID"]), float(row["Importe a aplicar"]))
                        for _, row in seleccionadas.iterrows()
                    ]

                    if total_aplicado > importe_movimiento + 0.01:
                        st.error("El total aplicado supera el importe del movimiento bancario.")
                    else:
                        col_acc1, col_acc2 = st.columns(2)

                        with col_acc1:
                            if st.button("Aplicar conciliación manual avanzada", key="btn_conciliacion_manual_multiple"):
                                try:
                                    aplicar_conciliacion(
                                        movimiento_id=movimiento_id,
                                        facturas_importes=facturas_importes
                                    )
                                    st.success("Conciliación aplicada correctamente")
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))

                        with col_acc2:
                            if st.button("Auto-conciliar este movimiento", key="btn_auto_conciliar_movimiento_actual"):
                                try:
                                    aplicar_conciliacion(
                                        movimiento_id=movimiento_id,
                                        facturas_importes=facturas_importes
                                    )
                                    st.success("Auto-conciliación aplicada correctamente")
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))

                        with col_acc2:
                            if st.button("Auto-conciliar este movimiento", key="btn_auto_conciliar_movimiento_actual"):
                                try:
                                    aplicar_conciliacion(
                                        movimiento_id=movimiento_id,
                                        facturas_importes=facturas_importes
                                    )
                                    st.success("Auto-conciliación aplicada correctamente")
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))

                        with col_acc2:
                            if st.button("Auto-conciliar este movimiento", key="btn_auto_conciliar_movimiento_actual"):
                                try:
                                    aplicar_conciliacion(
                                        movimiento_id=movimiento_id,
                                        facturas_importes=facturas_importes
                                    )
                                    st.success("Auto-conciliación aplicada correctamente")
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))
    with tab4:
        df = historial_conciliaciones()
        if df.empty:
            st.info("No hay conciliaciones registradas")
        else:
            st.dataframe(df, use_container_width=True)


def pantalla_automatizacion_pyme():
    st.markdown('<div class="section-title">Automatización PYME</div>', unsafe_allow_html=True)

    df_acciones = acciones_sugeridas_pyme()
    st.subheader("Bandeja de acciones sugeridas")

    if df_acciones.empty:
        st.success("No hay acciones pendientes.")
    else:
        st.dataframe(df_acciones, use_container_width=True)

    tab1, tab2, tab3 = st.tabs([
        "Cobros pendientes",
        "Pagos pendientes",
        "Generador de correos"
    ])

    with tab1:
        try:
            df = facturas_pendientes()
            df = df[df["tipo"] == "venta"].copy()
            if df.empty:
                st.info("No hay facturas pendientes de cobro.")
            else:
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(str(e))

    with tab2:
        try:
            df = facturas_pendientes()
            df = df[df["tipo"] == "compra"].copy()
            if df.empty:
                st.info("No hay facturas pendientes de pago.")
            else:
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(str(e))

    with tab3:
        tipo_correo = st.selectbox(
            "Tipo de correo",
            ["Recordatorio de cobro", "Envío de factura", "Correo a proveedor"]
        )

        nombre = st.text_input("Nombre del destinatario")
        factura_id = st.text_input("Factura / referencia")
        importe = st.number_input("Importe", min_value=0.0, step=1.0)
        fecha = st.text_input("Fecha", value=str(datetime.date.today()))

        if st.button("Generar borrador de correo"):
            if tipo_correo == "Recordatorio de cobro":
                asunto, cuerpo = generar_email_recordatorio_cobro(nombre, factura_id, importe, fecha)
            elif tipo_correo == "Envío de factura":
                asunto, cuerpo = generar_email_envio_factura(nombre, factura_id, importe, fecha)
            else:
                asunto, cuerpo = generar_email_proveedor(nombre, factura_id, importe, fecha)

            st.write("**Asunto:**")
            st.code(asunto)

            st.write("**Cuerpo:**")
            st.text_area("Borrador", value=cuerpo, height=250)



def pantalla_registrar_operacion():
    st.markdown('<div class="section-title">Registrar operación inteligente</div>', unsafe_allow_html=True)

    texto = st.text_area(
        "Describe la operación",
        placeholder="Ejemplo: Compra de mercadería a Paquito Perez SL al contado por 100 euros"
    )
    fecha = st.text_input("Fecha (YYYY-MM-DD)", value=str(datetime.date.today()))
    igic_defecto = st.number_input(
        "IGIC por defecto (%)",
        min_value=0.0,
        max_value=25.0,
        value=7.0,
        step=0.5
    )

    if "confirmar_operacion_inteligente" not in st.session_state:
        st.session_state["confirmar_operacion_inteligente"] = False

    if not st.session_state["confirmar_operacion_inteligente"]:
        if st.button("Procesar operación", key="boton_procesar_operacion"):
            if texto and fecha:
                st.session_state["confirmar_operacion_inteligente"] = True
            else:
                st.warning("Debes introducir texto y fecha.")
    else:
        st.warning("Confirma la operación antes de registrarla.")

        st.write(f"**Texto:** {texto}")
        st.write(f"**Fecha:** {fecha}")
        st.write(f"**IGIC por defecto:** {igic_defecto:.2f}%")

        col_conf_1, col_conf_2 = st.columns(2)

        with col_conf_1:
            if st.button("Sí, registrar operación", key="confirmar_operacion_inteligente_si"):
                resultado = procesar_operacion_texto(texto, fecha, igic_defecto)
                st.session_state["confirmar_operacion_inteligente"] = False

                if resultado["ok"]:
                    asiento_id = resultado.get("asiento_id")

                    if asiento_id is not None:
                        st.success(f"Asiento creado correctamente. ID: {asiento_id}")
                    else:
                        st.success("Operación registrada correctamente")

                    df_control = validar_sistema_completo()

                    if not df_control.empty:
                        st.warning("⚠️ Se detectaron incidencias contables tras registrar la operación")
                        st.dataframe(df_control, use_container_width=True)
                    else:
                        st.success("Validación contable correcta: no se detectaron incidencias")

                    st.subheader("Resumen detectado")
                    st.write(f"**Tipo:** {resultado.get('tipo', '-')}")
                    st.write(f"**Tercero:** {resultado.get('tercero', '-')}")
                    st.write(f"**Forma de pago:** {resultado.get('forma_pago', '-')}")

                    evento = resultado.get("evento", {})
                    if evento:
                        st.write(f"**Familia detectada:** {evento.get('familia', '-')}")
                        st.write(f"**Plazo (días):** {evento.get('plazo_dias', 0)}")
                        st.write(f"**Genera vencimiento:** {'Sí' if evento.get('genera_vencimiento') else 'No'}")
                        st.write(f"**Fecha vencimiento:** {evento.get('fecha_vencimiento') or '-'}")
                        st.write(f"**Periodificable:** {'Sí' if evento.get('periodificable') else 'No'}")

                    if "base" in resultado:
                        st.write(f"**Base:** {resultado['base']:.2f} €")

                    if "igic_pct" in resultado and "igic" in resultado:
                        st.write(f"**IGIC ({resultado['igic_pct']:.2f}%):** {resultado['igic']:.2f} €")

                    if "total" in resultado:
                        st.write(f"**Total:** {resultado['total']:.2f} €")

                    if "importe" in resultado:
                        st.write(f"**Importe:** {resultado['importe']:.2f} €")

                    if resultado.get("advertencias"):
                        for aviso in resultado["advertencias"]:
                            st.warning(aviso)

                    if resultado.get("vencimientos"):
                        df_vencimientos = pd.DataFrame(resultado["vencimientos"])
                        st.subheader("Vencimientos generados")
                        st.dataframe(df_vencimientos, use_container_width=True)

                    df_lineas = pd.DataFrame(
                        resultado["lineas"],
                        columns=["Cuenta", "Movimiento", "Importe"]
                    )
                    st.subheader("Asiento generado")
                    st.dataframe(df_lineas, use_container_width=True)
                else:
                    st.error(resultado["mensaje"])

        with col_conf_2:
            if st.button("Cancelar", key="confirmar_operacion_inteligente_no"):
                st.session_state["confirmar_operacion_inteligente"] = False
                st.info("Operación cancelada")


def pantalla_operaciones(cursor):
    st.markdown('<div class="section-title">Operaciones registradas</div>', unsafe_allow_html=True)

    try:
        cursor.execute("SELECT * FROM operaciones ORDER BY id DESC")
        ops = cursor.fetchall()

        try:
            df = pd.DataFrame(
                ops,
                columns=[
                    "ID", "Empresa ID", "Tipo operación", "Fecha operación", "Concepto",
                    "Nombre tercero", "Número factura", "Forma pago", "Base imponible",
                    "Impuesto %", "Cuota impuesto", "Total", "Creado en"
                ][:len(ops[0])] if ops else [
                    "ID", "Empresa ID", "Tipo operación", "Fecha operación", "Concepto",
                    "Nombre tercero", "Número factura", "Forma pago", "Base imponible",
                    "Impuesto %", "Cuota impuesto", "Total", "Creado en"
                ]
            )
        except Exception:
            df = pd.DataFrame(ops)

        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"No se pudieron cargar las operaciones: {e}")

def pantalla_vencimientos(cursor):
    st.markdown('<div class="section-title">Vencimientos</div>', unsafe_allow_html=True)

    try:
        cursor.execute("""
        SELECT
            id,
            empresa_id,
            factura_id,
            nombre_tercero,
            tipo,
            fecha_vencimiento,
            importe,
            importe_pendiente,
            estado,
            creado_en
        FROM vencimientos
        ORDER BY fecha_vencimiento ASC, id DESC
        """)
        vencimientos = cursor.fetchall()
    except Exception as e:
        st.error(str(e))
        return

    if not vencimientos:
        st.info("No hay vencimientos registrados.")
        return

    df = pd.DataFrame(
        vencimientos,
        columns=[
            "ID",
            "Empresa ID",
            "Referencia",
            "Nombre tercero",
            "Tipo",
            "Fecha vencimiento",
            "Importe",
            "Importe pendiente",
            "Estado",
            "Creado en"
        ]
)

    df["Fecha vencimiento"] = pd.to_datetime(df["Fecha vencimiento"], errors="coerce")
    hoy = pd.Timestamp.today().normalize()

    pendientes = df[df["Estado"].isin(["pendiente", "vencido", "cobro_parcial", "pago_parcial"])].copy()
    vencidos = pendientes[pendientes["Fecha vencimiento"] < hoy].copy()
    proximos = pendientes[
        (pendientes["Fecha vencimiento"] >= hoy) &
        (pendientes["Fecha vencimiento"] <= hoy + pd.Timedelta(days=7))
    ].copy()

    if "filtro_vencimientos" not in st.session_state:
        st.session_state["filtro_vencimientos"] = "todos"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Pendientes", len(pendientes))
        if st.button("Ver pendientes", key="btn_ver_pendientes"):
            st.session_state["filtro_vencimientos"] = "pendientes"

    with c2:
        st.metric("Vencidos", len(vencidos))
        if st.button("Ver vencidos", key="btn_ver_vencidos"):
            st.session_state["filtro_vencimientos"] = "vencidos"

    with c3:
        st.metric("Próximos 7 días", len(proximos))
        if st.button("Ver próximos 7 días", key="btn_ver_proximos"):
            st.session_state["filtro_vencimientos"] = "proximos"

    with c4:
        st.metric("Todos", len(df))
        if st.button("Ver todos", key="btn_ver_todos_vencimientos"):
            st.session_state["filtro_vencimientos"] = "todos"

    filtro = st.session_state["filtro_vencimientos"]

    if filtro == "pendientes":
        df_mostrar = pendientes.copy()
        st.subheader("Listado de vencimientos pendientes")
    elif filtro == "vencidos":
        df_mostrar = vencidos.copy()
        st.subheader("Listado de vencimientos vencidos")
    elif filtro == "proximos":
        df_mostrar = proximos.copy()
        st.subheader("Listado de vencimientos próximos 7 días")
    else:
        df_mostrar = df.copy()
        st.subheader("Listado completo de vencimientos")

    if df_mostrar.empty:
        st.info("No hay registros para este filtro.")
        return

    empresas = sorted(
        [x for x in df_mostrar["Nombre tercero"].dropna().astype(str).unique().tolist() if x.strip()]
    )

    empresa_seleccionada = st.selectbox(
        "Filtrar por empresa / tercero",
        ["Todas"] + empresas,
        key="filtro_empresa_vencimientos"
    )

    if empresa_seleccionada != "Todas":
        df_mostrar = df_mostrar[
            df_mostrar["Nombre tercero"].astype(str).str.upper() == empresa_seleccionada.upper()
        ].copy()

    if df_mostrar.empty:
        st.info("No hay vencimientos para la empresa seleccionada.")
        return

    total_importe = df_mostrar["Importe"].fillna(0).astype(float).sum()
    st.write(f"**Total importe listado:** {total_importe:,.2f} €")

    df_mostrar = df_mostrar.sort_values(
        by=["Fecha vencimiento", "Nombre tercero", "ID"],
        ascending=[True, True, False]
    ).reset_index(drop=True)

    st.dataframe(df_mostrar, use_container_width=True)

    st.markdown("### Registrar pago / cobro desde vencimiento")

    opciones = {
        f"{row['ID']} | {row['Nombre tercero']} | {row['Tipo']} | {row['Importe']:.2f} € | {row['Estado']}": int(row["ID"])
        for _, row in df_mostrar.iterrows()
        if str(row["Estado"]).strip().lower() in ["pendiente", "vencido", "cobro_parcial", "pago_parcial"]
    }

    if not opciones:
        st.info("No hay vencimientos operables en el listado actual.")
        return

    seleccion = st.selectbox(
        "Selecciona vencimiento",
        list(opciones.keys()),
        key="select_vencimiento_operar"
    )

    vencimiento_id = opciones[seleccion]

    fila_vencimiento = df_mostrar[df_mostrar["ID"] == vencimiento_id].iloc[0]
    importe_pendiente_actual = float(fila_vencimiento["Importe pendiente"])

    fecha_pago = st.text_input(
        "Fecha de pago / cobro (YYYY-MM-DD)",
        value=str(datetime.date.today()),
        key="fecha_operar_vencimiento"
    )

    importe_operar = st.number_input(
        "Importe a registrar",
        min_value=0.01,
        step=0.01,
        value=importe_pendiente_actual,
        key="importe_operar_vencimiento"
    )
    forma_pago = st.selectbox(
        "Forma de pago",
        ["transferencia", "contado"],
        key="forma_pago_vencimiento"
    )
    observaciones = st.text_input("Observaciones", value="", key="obs_vencimiento")

    if "confirmar_operacion_vencimiento" not in st.session_state:
        st.session_state["confirmar_operacion_vencimiento"] = False

    if not st.session_state["confirmar_operacion_vencimiento"]:
        if st.button("Registrar pago / cobro", key="btn_registrar_desde_vencimiento"):
            st.session_state["confirmar_operacion_vencimiento"] = True
    else:
        st.warning("Confirma el registro de pago / cobro del vencimiento seleccionado.")

        cc1, cc2 = st.columns(2)

        with cc1:
            if st.button("Sí, registrar", key="btn_confirmar_registrar_vencimiento_si"):
                resultado = registrar_desde_vencimiento(
                    vencimiento_id=vencimiento_id,
                    fecha=fecha_pago,
                    forma_pago=forma_pago,
                    importe=importe_operar,
                    observaciones=observaciones,
                )
                st.session_state["confirmar_operacion_vencimiento"] = False

                if resultado["ok"]:
                    st.success(resultado["mensaje"])
                    st.rerun()
                else:
                    st.error(resultado["mensaje"])

        with cc2:
            if st.button("Cancelar", key="btn_confirmar_registrar_vencimiento_no"):
                st.session_state["confirmar_operacion_vencimiento"] = False

def pantalla_inmovilizado():
    st.markdown('<div class="section-title">Gestión de inmovilizado</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Listado de bienes",
        "Alta de bien",
        "Generar amortización",
        "Historial"
    ])

    with tab1:
        df = ver_inmovilizado()
        if df.empty:
            st.info("No hay bienes registrados.")
        else:
            st.dataframe(df, use_container_width=True)

    with tab2:
        nombre = st.text_input("Nombre del bien")
        fecha_compra = st.date_input("Fecha de compra", datetime.date.today())
        fecha_inicio = st.date_input("Inicio de amortización", datetime.date.today())
        coste = st.number_input("Coste", min_value=0.0, step=100.0)
        valor_residual = st.number_input("Valor residual", min_value=0.0, step=100.0)
        vida_util = st.number_input("Vida útil (años)", min_value=1.0, step=1.0)

        cuenta_inmovilizado = st.text_input("Cuenta inmovilizado", "213 Maquinaria")
        cuenta_amort_acum = st.text_input(
            "Cuenta amortización acumulada",
            "2813 Amortización acumulada maquinaria"
        )
        cuenta_gasto = st.text_input(
            "Cuenta gasto amortización",
            "681 Amortización del inmovilizado material"
        )

        observaciones = st.text_area("Observaciones")

        if st.button("Crear bien"):
            try:
                bien_id = alta_inmovilizado(
                    nombre=nombre,
                    fecha_compra=str(fecha_compra),
                    fecha_inicio_amortizacion=str(fecha_inicio),
                    coste=coste,
                    valor_residual=valor_residual,
                    vida_util_anios=vida_util,
                    cuenta_inmovilizado=cuenta_inmovilizado,
                    cuenta_amort_acumulada=cuenta_amort_acum,
                    cuenta_gasto_amortizacion=cuenta_gasto,
                    observaciones=observaciones
                )
                st.success(f"Bien creado correctamente (ID {bien_id})")
            except Exception as e:
                st.error(str(e))

    with tab3:
        ejercicio = st.number_input(
            "Ejercicio",
            min_value=2000,
            max_value=2100,
            value=datetime.date.today().year
        )
        mes = st.selectbox("Mes", list(range(1, 13)))

        if st.button("Generar amortización para todos los bienes"):
            try:
                df = generar_amortizaciones_mes(ejercicio, mes)
                st.success("Proceso terminado")
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(str(e))

    with tab4:
        df = historial_amortizaciones()
        if df.empty:
            st.info("No hay amortizaciones generadas.")
        else:
            st.dataframe(df, use_container_width=True)


# =========================================================
# NAVEGACIÓN POR BLOQUES
# =========================================================

def mostrar_bloque_inicio(cursor):
    st.markdown("## 🏠 Panel principal")

    # 1. Mantienes TODO lo que ya tenías
    pantalla_panel_control()

    st.divider()

    # 2. Añadimos una capa más profesional encima/sobre el resumen
    st.markdown("## 📊 Resumen financiero ejecutivo")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Mantienes tu resumen actual completo
        pantalla_resumen_financiero(cursor)

    with col2:
        st.markdown("""
        ### 🤖 Asistente IA
        Tu sistema permite automatizar:
        - Asientos contables
        - Facturas
        - Clientes y proveedores
        - Balances
        - Importación desde Excel
        - Operaciones inteligentes
        """)

        st.markdown("""
        ### ✅ Acciones recomendadas
        - Revisar incidencias
        - Conciliar bancos
        - Ver facturas pendientes
        - Generar informe mensual
        """)

    st.divider()

    # 3. Aquí puedes dejar cualquier bloque extra que ya tuvieras debajo
    # Por ejemplo:
    # mostrar_modulos_destacados()
    # mostrar_alertas()
    # mostrar_ultimas_operaciones()

def mostrar_bloque_contabilidad(cursor):
    st.markdown('<div class="block-chip">Contabilidad</div>', unsafe_allow_html=True)
    seccion = st.radio(
        "Subbloque",
        [
            "Libro diario",
            "Balance de comprobación",
            "Libro mayor",
            "Cuenta de resultados",
            "Balance de situación",
            "Control contable",
            "Asiento de apertura"
        ],
        horizontal=True
    )

    if seccion == "Libro diario":
        pantalla_libro_diario(cursor)
    elif seccion == "Balance de comprobación":
        pantalla_balance_comprobacion()
    elif seccion == "Libro mayor":
        pantalla_libro_mayor()
    elif seccion == "Cuenta de resultados":
        pantalla_cuenta_resultados()
    elif seccion == "Balance de situación":
        pantalla_balance_situacion()
    elif seccion == "Control contable":
        pantalla_control_contable()
    elif seccion == "Asiento de apertura":
        pantalla_apertura_pdf()
    elif opcion == "Clientes":
        from clientes import pantalla_clientes
        pantalla_clientes()


def mostrar_bloque_facturacion(cursor):
    st.markdown('<div class="block-chip">Facturación</div>', unsafe_allow_html=True)

    seccion = st.radio(
        "Subbloque",
        ["Facturas", "Nueva factura venta", "Clientes", "Proveedores", "Vencimientos"],
        horizontal=True
    )

    if seccion == "Facturas":
        pantalla_facturas(cursor)
    elif seccion == "Nueva factura venta":
        pantalla_nueva_factura_venta(cursor)
    elif seccion == "Clientes":
        pantalla_clientes(cursor)
    elif seccion == "Proveedores":
        pantalla_proveedores(cursor)
    elif seccion == "Vencimientos":
        pantalla_vencimientos(cursor)


def mostrar_bloque_operaciones(cursor):
    st.markdown('<div class="block-chip">Operaciones e importación</div>', unsafe_allow_html=True)
    seccion = st.radio(
        "Subbloque",
        [
            "Registrar operación",
            "Operaciones",
            "Importar Excel",
            "Ver importaciones",
            "Incidencias importación",
            "Fianzas detectadas"
        ],
        horizontal=True
    )

    if seccion == "Registrar operación":
        pantalla_registrar_operacion()
    elif seccion == "Operaciones":
        pantalla_operaciones(cursor)
    elif seccion == "Importar Excel":
        pantalla_importar_excel()
    elif seccion == "Ver importaciones":
        pantalla_ver_importaciones(cursor)
    elif seccion == "Incidencias importación":
        pantalla_incidencias_importacion()
    elif seccion == "Fianzas detectadas":
        pantalla_fianzas_detectadas(cursor)


def mostrar_bloque_tesoreria():
    st.markdown('<div class="block-chip">Tesorería y automatización</div>', unsafe_allow_html=True)
    seccion = st.radio(
        "Subbloque",
        ["Conciliación bancaria IA", "Automatización PYME"],
        horizontal=True
    )

    if seccion == "Conciliación bancaria IA":
        pantalla_conciliacion_bancaria()
    elif seccion == "Automatización PYME":
        pantalla_automatizacion_pyme()


def mostrar_bloque_inmovilizado():
    st.markdown('<div class="block-chip">Activos</div>', unsafe_allow_html=True)
    pantalla_inmovilizado()


# =========================================================
# APP PRINCIPAL
# =========================================================

def mostrar_app():
    if "usuario" not in st.session_state or "empresa_activa" not in st.session_state:
      st.error("Sesión no iniciada correctamente")
      st.stop()
    usuario = st.session_state["usuario"]
    empresa_activa = st.session_state["empresa_activa"]

    with st.sidebar:
        mostrar_logo_efix(width=150, centrado=True)
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("### Navegación")
        bloque = st.radio(
            "Ir a",
            [
                "Inicio",
                "Contabilidad",
                "Facturación",
                "Operaciones",
                "Tesorería",
                "Inmovilizado"
            ],
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("#### Sesión")
        st.caption(f"Usuario: {usuario.get('username', '')}")
        st.caption(f"Empresa: {empresa_activa.get('nombre', '')}")

        if bloque == "Inicio":
            if st.button("Cambiar fondo inicio", use_container_width=True):
                st.session_state["fondo_inicio_canarias"] = obtener_imagen_canarias_local()
                st.rerun()

        if st.button("Cerrar sesión", use_container_width=True):
            logout()

        st.markdown('</div>', unsafe_allow_html=True)

    aplicar_estilo("app")

    inicializar_master()
    set_active_db_path(empresa_activa["db_path"])
    inicializar_bd_empresa()
    migrar_bd_empresa()
    inicializar_tablas_conciliacion()

    # mostrar_cabecera_efix()

    if bloque == "Inicio":
        mostrar_hero()

    conexion = get_connection()
    cursor = conexion.cursor()

    try:

        if bloque == "Inicio":
            mostrar_bloque_inicio(cursor)
        elif bloque == "Contabilidad":
            mostrar_bloque_contabilidad(cursor)
        elif bloque == "Facturación":
            mostrar_bloque_facturacion(cursor)
        elif bloque == "Operaciones":
            mostrar_bloque_operaciones(cursor)
        elif bloque == "Tesorería":
            mostrar_bloque_tesoreria()
        elif bloque == "Inmovilizado":
            mostrar_bloque_inmovilizado()
    finally:
        conexion.close()

def mostrar_cabecera_efix():
    empresa = st.session_state.get("empresa_activa", {})
    usuario = st.session_state.get("usuario", {})

    ruta_logo = obtener_logo_efix()
    logo_html = ""

    if ruta_logo:
        logo_base64 = imagen_a_base64(ruta_logo)
        if logo_base64:
            logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="height:82px;">'

    st.markdown(
        f"""
        <div style="
            width:100%;
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            text-align:center;
            margin-top:0.4rem;
            margin-bottom:1.4rem;
        ">

            {logo_html}

            <div style="
                text-align:center;
                font-size:1.12rem;
                color:#4b5f7a;
                margin-top:0.1rem;
                margin-bottom:0.9rem;
                font-weight:500;
                letter-spacing:0.01em;
                line-height:1.45;
                width:100%;
            ">
                Inteligencia financiera para decidir mejor, trabajar con orden y crecer con control.
            </div>

            <div style="
                font-size:0.96rem;
                color:#64748b;
                margin-bottom:0.2rem;
                text-align:center;
                width:100%;
            ">
                👤 {usuario.get('username', '')} &nbsp;&nbsp;|&nbsp;&nbsp; 🏢 {empresa.get('nombre', '')}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

def _parsear_datos_json_incidencia(valor):
    if pd.isna(valor) or not str(valor).strip():
        return {}
    try:
        return json.loads(valor)
    except Exception:
        return {"raw": str(valor)}


def _sugerencia_basica_incidencia(detalle_error, datos):
    detalle = str(detalle_error or "").lower()

    if "debe no puede ser negativo" in detalle:
        return "Sugerencia: mover el importe al HABER en positivo."

    if "haber no puede ser negativo" in detalle:
        return "Sugerencia: mover el importe al DEBE en positivo."

    if "fecha no válida" in detalle or "fecha vacía" in detalle:
        return "Sugerencia: corregir la fecha al formato YYYY-MM-DD."

    if "asiento descuadrado" in detalle:
        return "Sugerencia: revisar el conjunto de líneas del asiento y comprobar debe/haber."

    if "importe vacío" in detalle:
        return "Sugerencia: completar el importe faltante."

    if "importe no numérico" in detalle:
        return "Sugerencia: limpiar símbolos o texto y dejar solo número."

    if "fila sin líneas contables válidas" in detalle:
        return "Sugerencia: revisar cuentas e importes de la fila original."

    return "Sugerencia: revisar manualmente los datos originales y validar la corrección antes de aplicar."

def pantalla_incidencias_importacion():
    st.markdown('<div class="section-title">Revisión de incidencias de importación</div>', unsafe_allow_html=True)
    st.caption("Corrige solo lo necesario, valida el asiento y deja preparada la resolución.")
    col_acc_1, col_acc_2 = st.columns([1, 3])

    with col_acc_1:
        if st.button("🧹 Vaciar incidencias", key="vaciar_incidencias_importacion"):
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM incidencias_importacion")
                conn.commit()
                st.success("Bandeja de incidencias vaciada.")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"No se pudieron borrar las incidencias: {e}")
            finally:
                conn.close()

    
    f_estado, f_tipo = st.columns(2)

    with f_estado:
        estado = st.selectbox(
            "Estado",
            ["todas", "pendiente", "revisada"],
            index=1,
            key="inc_estado"
        )

    with f_tipo:
        tipo = st.selectbox(
            "Tipo de importación",
            ["todos", "asientos", "movimientos", "facturas", "pagos_proveedor"],
            index=0,
            key="inc_tipo_importacion"
        )

    estado_filtro = None if estado == "todas" else estado
    tipo_filtro = None if tipo == "todos" else tipo

    df = obtener_incidencias_importacion(
        estado=estado_filtro,
        tipo_importacion=tipo_filtro
    )

    if df.empty:
        st.success("No hay incidencias registradas.")
        return

    st.markdown("### Bandeja de incidencias")
    st.dataframe(df[["ID", "Tipo", "Fila Excel", "Fecha", "Concepto", "Detalle error", "Estado"]], use_container_width=True)

    opciones = {
        f"ID {row['ID']} | {row['Tipo']} | fila {row['Fila Excel']} | {row['Concepto']}": int(row["ID"])
        for _, row in df.iterrows()
    }

    seleccion = st.selectbox("Selecciona una incidencia para revisarla", list(opciones.keys()), key="inc_select")
    incidencia_id = opciones[seleccion]

    fila = df[df["ID"] == incidencia_id].iloc[0]
    datos = _parsear_datos_json_incidencia(fila["Datos JSON"])
    sugerencia = _sugerencia_basica_incidencia(fila["Detalle error"], datos)

    st.divider()

    # =========================
    # BLOQUE 1 - RESUMEN
    # =========================
    st.markdown("## 1) Resumen de la incidencia")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("ID incidencia", int(fila["ID"]))
    with c2:
        st.metric("Tipo", str(fila["Tipo"]))
    with c3:
        st.metric("Fila Excel", int(fila["Fila Excel"]) if pd.notna(fila["Fila Excel"]) else 0)
    with c4:
        st.metric("Estado", str(fila["Estado"]))

    # =========================
    # BLOQUE 2 - QUÉ HA PASADO
    # =========================
    st.markdown("## 2) Qué ha pasado")

    st.error(f"Error detectado: {fila['Detalle error']}")
    st.info(sugerencia)

    # =========================
    # BLOQUE 3 - DATOS ORIGINALES
    # =========================
    st.markdown("## 3) Datos originales detectados")

    fecha_original = str(datos.get("fecha") or fila["Fecha"] or "")
    concepto_original = str(datos.get("concepto") or fila["Concepto"] or "")
    cuenta_debe_original = str(datos.get("cuenta debe") or "")
    cuenta_haber_original = str(datos.get("cuenta haber") or "")

    try:
        debe_original = float(datos.get("debe eur") or 0)
    except Exception:
        debe_original = 0.0

    try:
        haber_original = float(datos.get("haber eur") or 0)
    except Exception:
        haber_original = 0.0

    o1, o2, o3 = st.columns(3)
    with o1:
        st.text_input("Fecha original", value=fecha_original, disabled=True, key=f"orig_fecha_{incidencia_id}")
        st.text_input("Cuenta debe original", value=cuenta_debe_original, disabled=True, key=f"orig_cdebe_{incidencia_id}")
    with o2:
        st.text_input("Concepto original", value=concepto_original, disabled=True, key=f"orig_concepto_{incidencia_id}")
        st.number_input("Debe original", value=float(abs(debe_original)), step=0.01, disabled=True, key=f"orig_debe_{incidencia_id}")
    with o3:
        st.text_input("Cuenta haber original", value=cuenta_haber_original, disabled=True, key=f"orig_chaber_{incidencia_id}")
        st.number_input("Haber original", value=float(abs(haber_original)), step=0.01, disabled=True, key=f"orig_haber_{incidencia_id}")

    with st.expander("Ver datos técnicos originales"):
        st.json(datos)

    # =========================
    # BLOQUE 4 - CORRECCIÓN
    # =========================
    st.markdown("## 4) Corrección propuesta")

    fecha_corregida = st.text_input("Fecha corregida", value=fecha_original, key=f"corr_fecha_{incidencia_id}")
    concepto_corregido = st.text_input("Concepto corregido", value=concepto_original, key=f"corr_concepto_{incidencia_id}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Lado debe")
        cuenta_debe = st.text_input("Cuenta debe", value=cuenta_debe_original, key=f"corr_cuenta_debe_{incidencia_id}")
        debe = st.number_input("Importe debe", min_value=0.0, step=0.01, value=float(abs(debe_original)), key=f"corr_debe_{incidencia_id}")

    with col2:
        st.markdown("### Lado haber")
        cuenta_haber = st.text_input("Cuenta haber", value=cuenta_haber_original, key=f"corr_cuenta_haber_{incidencia_id}")
        haber = st.number_input("Importe haber", min_value=0.0, step=0.01, value=float(abs(haber_original)), key=f"corr_haber_{incidencia_id}")

    st.markdown("## 5) Validación rápida")

    diferencia = round(float(debe) - float(haber), 2)

    v1, v2, v3 = st.columns(3)
    with v1:
        st.metric("Debe", f"{debe:.2f} €")
    with v2:
        st.metric("Haber", f"{haber:.2f} €")
    with v3:
        st.metric("Diferencia", f"{diferencia:.2f} €")

    if diferencia == 0 and cuenta_debe.strip() and cuenta_haber.strip():
        st.success("La corrección propuesta está cuadrada y lista para aplicarse.")
    else:
        st.warning("La corrección todavía no está lista. Revisa cuentas e importes hasta que la diferencia sea 0,00 €.")

    propuesta = {
        "fecha": fecha_corregida,
        "concepto": concepto_corregido,
        "cuenta_debe": cuenta_debe,
        "debe": debe,
        "cuenta_haber": cuenta_haber,
        "haber": haber,
    }

    with st.expander("Ver propuesta estructurada"):
        st.json(propuesta)

    # =========================
    # BLOQUE 5 - ACCIONES
    # =========================
    st.markdown("## 6) Acciones")

    a1, a2, a3 = st.columns(3)

    with a1:
        if st.button("Marcar como revisada", key=f"rev_{incidencia_id}"):
            try:
                resultado_revision = marcar_incidencia_revisada(incidencia_id)

                if isinstance(resultado_revision, dict):
                    if resultado_revision.get("ok", True):
                        st.success("Incidencia marcada como revisada.")
                        st.rerun()
                    else:
                        st.error(resultado_revision.get("mensaje", "No se pudo marcar como revisada."))
                else:
                    st.success("Incidencia marcada como revisada.")
                    st.rerun()

            except Exception as e:
                st.error(f"No se pudo marcar como revisada: {e}")

    with a2:
        if st.button(
            "Aplicar corrección y volcar a contabilidad",
            key=f"aplicar_corr_{incidencia_id}"
        ):
            try:
                resultado = aplicar_correccion_incidencia(incidencia_id, propuesta)

                if resultado.get("ok"):
                    try:
                        borrar_incidencia_revisada(incidencia_id)
                    except Exception:
                        pass

                    st.success(
                        f"Asiento generado correctamente (ID: {resultado['asiento_id']}). "
                        f"La incidencia ha quedado marcada como revisada."
                    )
                    st.rerun()
                else:
                    st.error(f"Error: {resultado.get('error', 'No se pudo aplicar la corrección.')}")

            except Exception as e:
                st.error(f"No se pudo aplicar la corrección: {e}")

    with a3:
        if st.button("Borrar incidencia", key=f"del_{incidencia_id}"):
            try:
                resultado_borrado = borrar_incidencia_importacion(incidencia_id)

                if isinstance(resultado_borrado, dict):
                    if resultado_borrado.get("ok", True):
                        st.success("Incidencia borrada.")
                        st.rerun()
                    else:
                        st.error(resultado_borrado.get("mensaje", "No se pudo borrar la incidencia."))
                else:
                    st.success("Incidencia borrada.")
                    st.rerun()

            except Exception as e:
                st.error(f"No se pudo borrar la incidencia: {e}")

def borrar_estado_revision_fianza(asiento_origen_id):
    inicializar_revision_fianzas()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM revision_fianzas
        WHERE asiento_origen_id = %s
    """, (asiento_origen_id,))

    conn.commit()
    conn.close()
