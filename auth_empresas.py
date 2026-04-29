import hashlib
import secrets
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sesiones_usuario (
            id SERIAL PRIMARY KEY,
            token_hash TEXT UNIQUE NOT NULL,
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expira_en TIMESTAMP NOT NULL,
            ultimo_uso TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def _hash_token(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def crear_sesion_usuario(usuario_id, empresa_id=None, horas=8):
    inicializar_master()
    token = secrets.token_urlsafe(32)
    conn = get_master_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM sesiones_usuario
        WHERE expira_en < CURRENT_TIMESTAMP
    """)

    cur.execute("""
        INSERT INTO sesiones_usuario (token_hash, usuario_id, empresa_id, expira_en)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP + (%s * INTERVAL '1 hour'))
    """, (_hash_token(token), usuario_id, empresa_id, int(horas)))

    conn.commit()
    conn.close()
    return token


def actualizar_empresa_sesion(token, empresa_id):
    if not token or not empresa_id:
        return

    inicializar_master()
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE sesiones_usuario
        SET empresa_id = %s, ultimo_uso = CURRENT_TIMESTAMP
        WHERE token_hash = %s AND expira_en > CURRENT_TIMESTAMP
    """, (empresa_id, _hash_token(token)))
    conn.commit()
    conn.close()


def obtener_sesion_usuario(token):
    if not token:
        return None

    inicializar_master()
    conn = get_master_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            u.id, u.username, u.nombre, u.email, u.rol, u.activo,
            e.id, e.nombre, e.db_path,
            ue.rol_en_empresa
        FROM sesiones_usuario s
        INNER JOIN usuarios u ON u.id = s.usuario_id
        LEFT JOIN empresas e ON e.id = s.empresa_id AND e.activa = 1
        LEFT JOIN usuarios_empresas ue ON ue.usuario_id = u.id AND ue.empresa_id = e.id
        WHERE s.token_hash = %s
          AND s.expira_en > CURRENT_TIMESTAMP
        LIMIT 1
    """, (_hash_token(token),))

    fila = cur.fetchone()

    if fila:
        cur.execute("""
            UPDATE sesiones_usuario
            SET ultimo_uso = CURRENT_TIMESTAMP
            WHERE token_hash = %s
        """, (_hash_token(token),))
        conn.commit()

    conn.close()

    if not fila or int(fila[5]) != 1:
        return None

    sesion = {
        "usuario": {
            "id": fila[0],
            "username": fila[1],
            "nombre": fila[2],
            "email": fila[3],
            "rol": fila[4],
        },
        "empresa": None,
    }

    if fila[6]:
        sesion["empresa"] = {
            "id": fila[6],
            "nombre": fila[7],
            "db_path": fila[8],
            "rol_en_empresa": fila[9],
        }

    return sesion


def cerrar_sesion_token(token):
    if not token:
        return

    inicializar_master()
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sesiones_usuario WHERE token_hash = %s", (_hash_token(token),))
    conn.commit()
    conn.close()
