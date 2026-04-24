import sqlite3

conn = sqlite3.connect("database/master.db")
cursor = conn.cursor()

print("=== USUARIOS ===")
cursor.execute("SELECT * FROM usuarios")
for row in cursor.fetchall():
    print(row)

print("\n=== EMPRESAS ===")
cursor.execute("SELECT * FROM empresas")
for row in cursor.fetchall():
    print(row)

print("\n=== USUARIO_EMPRESAS ===")
cursor.execute("SELECT * FROM usuario_empresas")
for row in cursor.fetchall():
    print(row)

conn.close()