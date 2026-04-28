import hashlib
from db_context import ensure_dirs, get_master_connection

MASTER_DB = "database/master.db"
_MASTER_INICIALIZADO = False


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def inicializar_master():
    global _MASTER_INICIALIZADO
    if _MASTER_INICIALIZADO:
        return

    ensure_dirs()
    conn = get_master_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nombre TEXT,
        email TEXT,
        rol TEXT DEFAULT 'admin',
        activo INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        nif TEXT,
        email TEXT,
        db_path TEXT NOT NULL,
        activa INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER NOT NULL,
        empresa_id INTEGER NOT NULL,
        rol_en_empresa TEXT DEFAULT 'admin',
        UNIQUE(usuario_id, empresa_id)
    )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_empresas (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            rol_en_empresa TEXT DEFAULT 'admin',
            activo INTEGER DEFAULT 1,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    _MASTER_INICIALIZADO = True



def crear_usuario(username, password, nombre="", email="", rol="admin"):
    inicializar_master()
    conn = get_master_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO usuarios (username, password_hash, nombre, email, rol, activo)
    VALUES (%s, %s, %s, %s, %s, 1)
    """, (username, hash_password(password), nombre, email, rol))

    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def crear_empresa(nombre, nif="", email=""):
    inicializar_master()
    conn = get_master_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO empresas (nombre, nif, email, db_path, activa)
    VALUES (%s, %s, %s, '', 1)
    """, (nombre, nif, email))

    empresa_id = cur.lastrowid
    db_path = f"database/empresas/empresa_{empresa_id}.db"

    cur.execute("""
    UPDATE empresas
    SET db_path = %s
    WHERE id = %s
    """, (db_path, empresa_id))

    conn.commit()
    conn.close()

    return empresa_id, db_path


def vincular_usuario_empresa(usuario_id, empresa_id, rol_en_empresa="admin"):
    inicializar_master()
    conn = get_master_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO usuarios_empresas (usuario_id, empresa_id, rol_en_empresa)
    VALUES (%s, %s, %s)
    """, (usuario_id, empresa_id, rol_en_empresa))

    conn.commit()
    conn.close()


def autenticar(username, password):
    inicializar_master()
    conn = get_master_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT id, username, nombre, email, rol, activo
    FROM usuarios
    WHERE username = %s AND password_hash = %s
    """, (username, hash_password(password)))

    fila = cur.fetchone()
    conn.close()

    if not fila or int(fila[5]) != 1:
        return None

    return {
        "id": fila[0],
        "username": fila[1],
        "nombre": fila[2],
        "email": fila[3],
        "rol": fila[4],
    }


def empresas_de_usuario(usuario_id):
    inicializar_master()
    conn = get_master_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT e.id, e.nombre, e.db_path, ue.rol_en_empresa
    FROM empresas e
    INNER JOIN usuarios_empresas ue ON e.id = ue.empresa_id
    WHERE ue.usuario_id = %s AND e.activa = 1
    ORDER BY e.nombre
    """, (usuario_id,))

    filas = cur.fetchall()
    conn.close()

    return [
        {
            "id": f[0],
            "nombre": f[1],
            "db_path": f[2],
            "rol_en_empresa": f[3],
        }
        for f in filas
    ]


def existe_algun_usuario():
    inicializar_master()
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM usuarios")
    total = cur.fetchone()[0]
    conn.close()
    return total > 0
