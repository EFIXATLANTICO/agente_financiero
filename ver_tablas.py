import sqlite3

conn = sqlite3.connect("database/empresas/empresa_1.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tablas = cursor.fetchall()

print("TABLAS DE EMPRESA:")
for t in tablas:
    print(t[0])

conn.close()