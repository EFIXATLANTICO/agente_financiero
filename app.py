import streamlit as st
from login_view import pantalla_login, pantalla_selector_empresa
from app_visual import mostrar_app
from auth_empresas import existe_algun_usuario
from bootstrap_sistema import bootstrap_inicial

from db_context import get_master_connection

def crear_datos_demo():
    conn = get_master_connection()
    cur = conn.cursor()

    # 1. Crear empresa
    cur.execute("""
        INSERT INTO empresas (nombre, db_path, activa)
        VALUES (%s, %s, 1)
        ON CONFLICT DO NOTHING
    """, ("Empresa Demo", "empresa_demo"))

    # 2. Obtener usuario admin
    cur.execute("""
        SELECT id FROM usuarios WHERE username = %s
    """, ("admin",))
    usuario = cur.fetchone()

    if usuario:
        usuario_id = usuario[0]

        # 3. Obtener empresa
        cur.execute("""
            SELECT id FROM empresas WHERE nombre = %s
        """, ("Empresa Demo",))
        empresa = cur.fetchone()

        if empresa:
            empresa_id = empresa[0]

            # 4. Asignar empresa al usuario
            cur.execute("""
                INSERT INTO usuarios_empresas (usuario_id, empresa_id, rol_en_empresa, activo)
                VALUES (%s, %s, %s, 1)
                ON CONFLICT DO NOTHING
            """, (usuario_id, empresa_id, "admin"))

    conn.commit()
    conn.close()

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

    crear_datos_demo()

# ----------------------------
# ENTRYPOINT
# ----------------------------
if __name__ == "__main__":
    main()