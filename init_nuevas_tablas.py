from db_context import get_connection


def inicializar_nuevas_tablas():
    conn = get_connection()
    cursor = conn.cursor()

    sentencias = [
        """
        CREATE TABLE IF NOT EXISTS scoring_clientes (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL,
            puntuacion INTEGER NOT NULL,
            color TEXT NOT NULL,
            motivo TEXT,
            fecha_revision TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS modelos_fiscales (
            id SERIAL PRIMARY KEY,
            modelo TEXT NOT NULL,
            periodo TEXT NOT NULL,
            fecha_presentacion TEXT,
            fecha_limite TEXT,
            estado TEXT,
            observaciones TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS movimientos_bancarios (
            id SERIAL PRIMARY KEY,
            fecha TEXT NOT NULL,
            concepto TEXT NOT NULL,
            importe REAL NOT NULL,
            saldo REAL,
            conciliado INTEGER DEFAULT 0,
            referencia TEXT,
            observaciones TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS alertas (
            id SERIAL PRIMARY KEY,
            tipo TEXT NOT NULL,
            prioridad TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            fecha_alerta TEXT NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            referencia_tabla TEXT,
            referencia_id INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS presentaciones_fiscales (
            id SERIAL PRIMARY KEY,
            modelo TEXT,
            periodo TEXT,
            fecha_presentacion TEXT,
            resultado TEXT,
            observaciones TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS reglas_empresa (
            id SERIAL PRIMARY KEY,
            clave TEXT NOT NULL,
            valor TEXT NOT NULL
        )
        """,
    ]

    for sentencia in sentencias:
        cursor.execute(sentencia)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    inicializar_nuevas_tablas()
    print("Nuevas tablas creadas correctamente")
