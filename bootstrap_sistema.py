from auth_empresas import (
    crear_usuario,
    crear_empresa,
    vincular_usuario_empresa
)
from db_context import set_active_db_path
from init_db import inicializar_bd_empresa


def bootstrap_inicial():
    print("Inicializando sistema...")

    # Crear usuario admin
    user_id = crear_usuario(
        username="admin",
        password="admin123",
        nombre="Administrador"
    )

    # Crear empresa demo
    empresa_id, db_path = crear_empresa(
        nombre="Empresa Demo",
        nif="",
        email=""
    )

    # Vincular usuario con empresa
    vincular_usuario_empresa(user_id, empresa_id)

    # Activar BD de empresa
    set_active_db_path(db_path)

    # Inicializar tablas
    inicializar_bd_empresa()

    print("Sistema inicializado correctamente")