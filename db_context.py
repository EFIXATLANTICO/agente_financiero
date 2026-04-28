import os
import sqlite3
import psycopg2
import streamlit as st


def ensure_dirs():
    pass


def _secret_text(key, default=None):
    if key in st.secrets:
        return str(st.secrets[key]).strip()
    return default


def _secret_int(key, default):
    try:
        return int(str(st.secrets.get(key, default)).strip())
    except Exception:
        return default


def _add_destino(destinos, host, port, user):
    host = str(host or "").strip()
    port = int(port or 5432)
    user = str(user or "").strip()

    if not host or not user:
        return

    clave = (host, port, user)
    if clave not in {(d["host"], d["port"], d["user"]) for d in destinos}:
        destinos.append({"host": host, "port": port, "user": user})


def get_master_connection():
    ultimo_error = None
    errores = []
    destinos = []

    host_pooler = _secret_text("SUPABASE_HOST")
    port_pooler = _secret_int("SUPABASE_PORT", 6543)
    user_pooler = _secret_text("SUPABASE_USER")

    if host_pooler and "pooler.supabase.com" in host_pooler:
        port_pooler = 5432

    _add_destino(destinos, host_pooler, port_pooler, user_pooler)

    if "SUPABASE_DIRECT_HOST" in st.secrets:
        _add_destino(
            destinos,
            _secret_text("SUPABASE_DIRECT_HOST"),
            _secret_int("SUPABASE_DIRECT_PORT", 5432),
            _secret_text("SUPABASE_DIRECT_USER", "postgres"),
        )

    for destino in destinos:
        try:
            return psycopg2.connect(
                host=destino["host"],
                port=destino["port"],
                database=st.secrets["SUPABASE_DB"],
                user=destino["user"],
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
            errores.append(
                f"{destino['host']}:{destino['port']} usuario={destino['user']} "
                f"(SUPABASE_PORT leido={port_pooler}) -> {str(e).strip()}"
            )

    if errores:
        raise psycopg2.OperationalError(
            "No se pudo conectar a Supabase con ninguna ruta:\n\n" + "\n\n".join(errores)
        )

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
