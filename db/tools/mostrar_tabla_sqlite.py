import sqlite3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.db_connection import apply_pragmas
import sys

db_path = sys.argv[1]
conn = sqlite3.connect(db_path)
apply_pragmas(conn)
cursor = conn.cursor()

# Obtener todas las tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tablas = cursor.fetchall()

for tabla in tablas:
    print(f"\nEstructura de la tabla: {tabla[0]}")
    cursor.execute(f"PRAGMA table_info({tabla[0]})")
    columnas = cursor.fetchall()
    for columna in columnas:
        print(columna)  # (ID, Nombre, Tipo, ¿Puede ser NULL?, Valor por defecto, Clave primaria)

conn.close()