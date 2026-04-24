import sqlite3

conn = sqlite3.connect("database/master.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM usuarios")
usuarios = cursor.fetchall()

print("USUARIOS EN LA BASE DE DATOS:")
for u in usuarios:
    print(u)

conn.close()