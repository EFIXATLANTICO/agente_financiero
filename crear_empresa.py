from auth_empresas import crear_empresa, vincular_usuario_empresa
from db_context import set_active_db_path
from init_db import inicializar_bd_empresa


def crear_nueva_empresa(
    usuario_id,
    nombre,
    nif="",
    email="",
    activar_bd=True,
    inicializar_bd=True,
    rol_en_empresa="admin"
):
    """
    Crea una nueva empresa, la vincula al usuario y opcionalmente:
    - activa su base de datos
    - inicializa las tablas de empresa

    Devuelve un diccionario con toda la informacion relevante.
    """

    if not usuario_id:
        raise ValueError("usuario_id es obligatorio")

    nombre = (nombre or "").strip()
    nif = (nif or "").strip()
    email = (email or "").strip()

    if not nombre:
        raise ValueError("El nombre de la empresa es obligatorio")

    empresa_id, db_path = crear_empresa(nombre, nif, email)

    vincular_usuario_empresa(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        rol_en_empresa=rol_en_empresa
    )

    if activar_bd:
        set_active_db_path(db_path)

    if inicializar_bd:
        inicializar_bd_empresa()

    return {
        "ok": True,
        "empresa_id": empresa_id,
        "db_path": db_path,
        "nombre": nombre,
        "nif": nif,
        "email": email,
        "usuario_id": usuario_id,
        "rol_en_empresa": rol_en_empresa
    }


def crear_empresa_para_usuario(usuario_id, nombre, nif="", email=""):
    """
    Alias semantico mas expresivo para usar desde vistas o flujos de alta.
    """
    return crear_nueva_empresa(
        usuario_id=usuario_id,
        nombre=nombre,
        nif=nif,
        email=email,
        activar_bd=True,
        inicializar_bd=True,
        rol_en_empresa="admin"
    )