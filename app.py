import streamlit as st
from login_view import pantalla_login, pantalla_selector_empresa
from app_visual import mostrar_app
from auth_empresas import existe_algun_usuario
from bootstrap_sistema import bootstrap_inicial

# ----------------------------
# CONFIGURACIÓN APP
# ----------------------------
st.set_page_config(
    page_title="EFIX ATLÁNTICO",
    page_icon="📘",
    layout="wide"
)

# ----------------------------
# FUNCIÓN PRINCIPAL
# ----------------------------
def main():

    # ----------------------------
    # BOOTSTRAP INICIAL
    # ----------------------------
    if not existe_algun_usuario():
        bootstrap_inicial()

    # ----------------------------
    # LOGIN
    # ----------------------------
    if "usuario" not in st.session_state:
        pantalla_login()
        return

    # ----------------------------
    # SELECCIÓN EMPRESA
    # ----------------------------
    if "empresa_activa" not in st.session_state:
        pantalla_selector_empresa()
        return

    # ----------------------------
    # APP PRINCIPAL
    # ----------------------------
    mostrar_app()


# ----------------------------
# ENTRYPOINT
# ----------------------------
if __name__ == "__main__":
    main()