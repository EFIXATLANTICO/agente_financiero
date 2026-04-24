import os
import sqlite3

MASTER_DB_PATH = "database/master.db"


def ensure_dirs():
    os.makedirs("database", exist_ok=True)
    os.makedirs("database/empresas", exist_ok=True)


def get_master_connection():
    ensure_dirs()
    return sqlite3.connect(MASTER_DB_PATH)


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
    """
    Intenta obtener el ID de la empresa activa a partir de la ruta
    de la base de datos seleccionada.
    """
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
            WHERE db_path = ?
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
    ensure_dirs()
    path = get_db_path()

    if not os.path.exists(path):
        raise RuntimeError(
            f"La base de datos no existe: {path}. "
            "Debes inicializarla antes de usarla."
        )

    return sqlite3.connect(path)

def get_current_db_info():
    path = os.environ.get("ACTIVE_DB_PATH")
    return {
        "db_activa": path,
        "existe": os.path.exists(path) if path else False
    }