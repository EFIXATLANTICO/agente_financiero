import os
import sqlite3
import psycopg2
import streamlit as st


def ensure_dirs():
    pass


def get_master_connection():
    ultimo_error = None
    destinos = [
        {
            "host": st.secrets["SUPABASE_HOST"],
            "port": st.secrets["SUPABASE_PORT"],
        }
    ]

    if "SUPABASE_DIRECT_HOST" in st.secrets:
        destinos.append({
            "host": st.secrets["SUPABASE_DIRECT_HOST"],
            "port": st.secrets.get("SUPABASE_DIRECT_PORT", 5432),
        })

    for destino in destinos:
        try:
            return psycopg2.connect(
                host=destino["host"],
                port=destino["port"],
                database=st.secrets["SUPABASE_DB"],
                user=st.secrets["SUPABASE_USER"],
                password=st.secrets["SUPABASE_PASSWORD"],
                sslmode="require",
                connect_timeout=4,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=3,
                application_name="efix_atlantico",
            )
        except psycopg2.OperationalError as e:
            ultimo_error = e

    raise ultimo_error


def get_db_path():
    ensure_dirs()
    path = os.environ.get("ACTIVE_DB_PATH")
    if not path:
        raise RuntimeError(
            "No hay base de datos de empresa activa. "
            "Debes seleccionar una empresa antes de operar."
        )
    return path


def obtener_empresa_id_activa():
    path = get_db_path()
    nombre_archivo = os.path.basename(path)
    nombre_sin_ext = os.path.splitext(nombre_archivo)[0]

    if nombre_sin_ext.startswith("empresa_"):
        try:
            return int(nombre_sin_ext.replace("empresa_", ""))
        except Exception:
            pass

    conn = get_master_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM empresas
            WHERE db_path = %s
            LIMIT 1
            """,
            (path,),
        )
        fila = cursor.fetchone()
        if fila:
            return int(fila[0])
    finally:
        conn.close()

    raise RuntimeError(
        f"No se pudo determinar el ID de la empresa activa para la BD: {path}"
    )


def set_active_db_path(path: str):
    ensure_dirs()
    if not path:
        raise ValueError("La ruta de la base de datos no puede estar vacía.")
    os.environ["ACTIVE_DB_PATH"] = path


def clear_active_db_path():
    os.environ.pop("ACTIVE_DB_PATH", None)


def get_connection():
    return get_master_connection()


def get_current_db_info():
    path = os.environ.get("ACTIVE_DB_PATH")
    return {
        "db_activa": path,
        "existe": os.path.exists(path) if path else False
    }
