import os
import glob
import random
import base64

import psycopg2
import streamlit as st

from auth_empresas import autenticar, empresas_de_usuario
from db_context import set_active_db_path, clear_active_db_path


def _obtener_imagen_canarias_login():
    imagenes = []
    for patron in (
        "assets/canarias/*.jpg",
        "assets/canarias/*.jpeg",
        "assets/canarias/*.png",
        "assets/canarias/*.webp",
    ):
        imagenes.extend(glob.glob(patron))

    return random.choice(imagenes) if imagenes else None


def _imagen_a_base64_login(ruta_imagen):
    if not ruta_imagen or not os.path.exists(ruta_imagen):
        return None

    with open(ruta_imagen, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _obtener_logo_efix():
    for ruta in (
        "assets/logo_efix.png",
        "assets/logo_efix.jpg",
        "assets/logo_efix.jpeg",
        "assets/logo_efix.webp",
    ):
        if os.path.exists(ruta):
            return ruta
    return None


def mostrar_logo_login_efix():
    ruta_logo = _obtener_logo_efix()
    if not ruta_logo:
        return

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(ruta_logo, width=420)
        st.caption("Acceso a tu entorno contable")


def aplicar_estilo_login():
    if "fondo_login_canarias" not in st.session_state:
        st.session_state["fondo_login_canarias"] = _obtener_imagen_canarias_login()

    ruta_fondo = st.session_state.get("fondo_login_canarias")
    fondo_base64 = _imagen_a_base64_login(ruta_fondo)

    fondo_css = """
        background:
            radial-gradient(circle at 20% 20%, rgba(56, 189, 248, 0.18), transparent 24%),
            radial-gradient(circle at 80% 18%, rgba(37, 99, 235, 0.20), transparent 22%),
            linear-gradient(135deg, rgba(15, 23, 42, 0.78), rgba(15, 23, 42, 0.88));
        background-color: #0f172a;
    """

    if fondo_base64:
        fondo_css = f"""
            background:
                linear-gradient(rgba(8, 15, 32, 0.48), rgba(15, 23, 42, 0.68)),
                url("data:image/jpeg;base64,{fondo_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        """

    st.markdown(f"""
    <style>
        .stApp, [data-testid="stAppViewContainer"] {{
            {fondo_css}
        }}

        [data-testid="stHeader"] {{
            background: transparent !important;
            height: 0 !important;
        }}

        [data-testid="stToolbar"],
        #MainMenu,
        footer,
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}

        .block-container {{
            max-width: 1050px;
            padding-top: 2rem !important;
            padding-bottom: 2rem;
        }}

        .login-shell {{
            max-width: 560px;
            margin: 1.2rem auto 0 auto;
            background: linear-gradient(180deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0.10) 100%);
            border: 1px solid rgba(255,255,255,0.16);
            border-radius: 30px;
            padding: 2.2rem 2.1rem 1.7rem 2.1rem;
            backdrop-filter: blur(20px);
            box-shadow: 0 24px 80px rgba(2, 6, 23, 0.38);
            position: relative;
            overflow: hidden;
        }}

        .login-title {{
            position: relative;
            z-index: 2;
            font-size: 2.1rem;
            font-weight: 900;
            color: #ffffff;
            text-align: center;
            margin-bottom: 0.35rem;
        }}

        .login-subtitle,
        .login-mini,
        .login-trust {{
            position: relative;
            z-index: 2;
            color: rgba(255,255,255,0.86);
            text-align: center;
        }}

        .login-subtitle {{
            font-size: 1rem;
            margin-bottom: 1.5rem;
            line-height: 1.5;
        }}

        .login-mini {{
            font-size: 0.95rem;
            margin-top: 1rem;
        }}

        .login-trust {{
            font-size: 0.84rem;
            margin-top: 0.8rem;
            line-height: 1.45;
        }}

        label, .stTextInput label {{
            color: #e2e8f0 !important;
            font-weight: 700 !important;
        }}

        .stTextInput input {{
            background: rgba(255,255,255,0.94) !important;
            border-radius: 16px !important;
            border: 1px solid rgba(255,255,255,0.22) !important;
            color: #0f172a !important;
        }}

        .stButton > button {{
            width: 100%;
            border-radius: 16px;
            border: 1px solid rgba(125, 211, 252, 0.18);
            background: linear-gradient(135deg, #38bdf8 0%, #2563eb 55%, #1d4ed8 100%);
            color: white;
            font-size: 1rem;
            font-weight: 900;
            padding: 0.78rem 1rem;
        }}
    </style>
    """, unsafe_allow_html=True)


def pantalla_login():
    aplicar_estilo_login()

    st.markdown('<div class="login-shell">', unsafe_allow_html=True)
    mostrar_logo_login_efix()
    st.markdown('<div class="login-mini">Acceso privado para usuarios autorizados</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Bienvenido a eFix</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="login-subtitle">Controla facturas, bancos, IGIC y resultados desde un panel financiero claro.</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("login_error"):
        st.error(st.session_state["login_error"])
        detalle_error = st.session_state.get("login_error_detalle")
        if detalle_error:
            with st.expander("Detalle tecnico de conexion"):
                st.code(detalle_error)

    with st.form("form_login_efix", clear_on_submit=False):
        usuario = st.text_input("Usuario", autocomplete="username")
        password = st.text_input("Contrasena", type="password", autocomplete="current-password")
        enviar_login = st.form_submit_button("Entrar")

    if enviar_login:
        st.session_state.pop("login_error", None)
        st.session_state.pop("login_error_detalle", None)

        usuario_limpio = (usuario or "").strip().lower()
        password_limpio = (password or "").strip()

        if not usuario_limpio or not password_limpio:
            st.warning("Introduce usuario y contrasena para acceder.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        try:
            with st.spinner("Verificando acceso..."):
                user = autenticar(usuario_limpio, password_limpio)
        except psycopg2.OperationalError as e:
            st.session_state["login_error"] = (
                "La base de datos no responde ahora mismo. Espera unos segundos y vuelve a pulsar Entrar."
            )
            st.session_state["login_error_detalle"] = str(e)
            st.rerun()
        except Exception as e:
            st.session_state["login_error"] = "No se pudo verificar el acceso. Revisa la conexion o los secretos de Supabase."
            st.session_state["login_error_detalle"] = str(e)
            st.rerun()

        if not user:
            st.error("Usuario o contrasena incorrectos")
            st.markdown('<div class="login-mini">Revisa tus credenciales e intentalo de nuevo.</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            return

        st.session_state["usuario"] = user
        st.session_state["login_ts"] = __import__("time").time()
        st.rerun()

    st.markdown(
        '<div class="login-trust">Tus datos permanecen en un entorno privado de trabajo. Si no tienes acceso, contacta con el administrador.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def pantalla_selector_empresa():
    aplicar_estilo_login()

    usuario = st.session_state.get("usuario")
    if not usuario or "id" not in usuario:
        st.error("No hay usuario autenticado.")
        st.stop()

    filas = empresas_de_usuario(usuario["id"])

    if not filas:
        st.warning("No tienes empresas asignadas.")
        st.stop()

    if len(filas) == 1:
        empresa = filas[0]
        st.session_state["empresa_activa"] = empresa
        set_active_db_path(empresa["db_path"])
        st.rerun()

    opciones = {empresa["nombre"]: empresa for empresa in filas}

    st.markdown('<div class="login-shell">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Selecciona empresa</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="login-subtitle">Elige el entorno sobre el que quieres trabajar.</div>',
        unsafe_allow_html=True,
    )

    seleccion = st.selectbox("Empresa", list(opciones.keys()), label_visibility="collapsed")

    if st.button("Continuar"):
        empresa = opciones[seleccion]
        st.session_state["empresa_activa"] = empresa
        set_active_db_path(empresa["db_path"])
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def logout():
    for key in ("usuario", "empresas_usuario", "empresa_activa", "login_ts"):
        st.session_state.pop(key, None)
    clear_active_db_path()
    st.rerun()
