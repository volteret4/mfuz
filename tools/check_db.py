#!/usr/bin/env python3
"""
Script de diagnóstico para problemas de acceso a base de datos SQLite
"""

import os
import sqlite3
import sys
import stat
from pathlib import Path
import pwd
import grp

def check_database_path(db_path):
    """Verificar el path de la base de datos y diagnosticar problemas"""
    print("=" * 60)
    print("DIAGNÓSTICO DE BASE DE DATOS SQLITE")
    print("=" * 60)

    # 1. Verificar que el path no esté vacío
    if not db_path:
        print("❌ ERROR: db_path está vacío o es None")
        return False

    print(f"📁 Path de la base de datos: {db_path}")

    # 2. Verificar si es un path absoluto
    if not os.path.isabs(db_path):
        print(f"⚠️  ADVERTENCIA: El path no es absoluto")
        abs_path = os.path.abspath(db_path)
        print(f"📁 Path absoluto: {abs_path}")
        db_path = abs_path

    # 3. Verificar si el archivo existe
    exists = os.path.exists(db_path)
    print(f"📄 Archivo existe: {'✅ Sí' if exists else '❌ No'}")

    if not exists:
        print("❌ ERROR: El archivo de base de datos no existe")
        # Verificar si el directorio padre existe
        parent_dir = os.path.dirname(db_path)
        if os.path.exists(parent_dir):
            print(f"📁 El directorio padre existe: {parent_dir}")
        else:
            print(f"❌ ERROR: El directorio padre no existe: {parent_dir}")
            return False

    # 4. Verificar permisos del archivo (si existe)
    if exists:
        try:
            file_stat = os.stat(db_path)
            print(f"👤 Propietario: {pwd.getpwuid(file_stat.st_uid).pw_name}")
            print(f"👥 Grupo: {grp.getgrgid(file_stat.st_gid).gr_name}")
            print(f"🔐 Permisos: {oct(file_stat.st_mode)[-3:]}")

            # Verificar si el archivo es legible
            readable = os.access(db_path, os.R_OK)
            writable = os.access(db_path, os.W_OK)
            print(f"📖 Legible: {'✅ Sí' if readable else '❌ No'}")
            print(f"✏️  Escribible: {'✅ Sí' if writable else '❌ No'}")

        except Exception as e:
            print(f"❌ ERROR obteniendo información del archivo: {e}")

    # 5. Verificar permisos del directorio padre
    parent_dir = os.path.dirname(db_path)
    if os.path.exists(parent_dir):
        try:
            dir_stat = os.stat(parent_dir)
            print(f"\n📁 DIRECTORIO PADRE: {parent_dir}")
            print(f"👤 Propietario: {pwd.getpwuid(dir_stat.st_uid).pw_name}")
            print(f"👥 Grupo: {grp.getgrgid(dir_stat.st_gid).gr_name}")
            print(f"🔐 Permisos: {oct(dir_stat.st_mode)[-3:]}")

            # SQLite necesita poder escribir en el directorio para crear archivos temporales
            dir_writable = os.access(parent_dir, os.W_OK)
            print(f"✏️  Directorio escribible: {'✅ Sí' if dir_writable else '❌ No'}")

            if not dir_writable:
                print("❌ ERROR CRÍTICO: SQLite necesita permisos de escritura en el directorio padre")
                print("   para crear archivos de journal y lock. Esto es obligatorio.")

        except Exception as e:
            print(f"❌ ERROR obteniendo información del directorio: {e}")

    # 6. Verificar usuario actual
    current_user = os.getenv('USER') or os.getenv('USERNAME')
    print(f"\n👤 Usuario actual: {current_user}")
    print(f"🆔 UID actual: {os.getuid()}")
    print(f"🆔 GID actual: {os.getgid()}")

    # 7. Intentar conectar a la base de datos
    print(f"\n🔌 PROBANDO CONEXIÓN A LA BASE DE DATOS...")
    try:
        conn = sqlite3.connect(db_path)
        print("✅ Conexión exitosa")

        # Probar una consulta simple
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📊 Tablas encontradas: {len(tables)}")
        for table in tables[:5]:  # Mostrar primeras 5 tablas
            print(f"   - {table[0]}")
        if len(tables) > 5:
            print(f"   ... y {len(tables) - 5} más")

        conn.close()
        print("✅ Conexión cerrada correctamente")
        return True

    except sqlite3.OperationalError as e:
        print(f"❌ ERROR DE CONEXIÓN: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR INESPERADO: {e}")
        return False

def fix_permissions(db_path):
    """Sugerir comandos para arreglar permisos"""
    print("\n" + "=" * 60)
    print("COMANDOS SUGERIDOS PARA ARREGLAR PERMISOS")
    print("=" * 60)

    parent_dir = os.path.dirname(db_path)
    current_user = os.getenv('USER')

    print("# Hacer al usuario actual propietario de la base de datos:")
    print(f"sudo chown {current_user}:{current_user} {db_path}")

    print("\n# Dar permisos de lectura/escritura al archivo:")
    print(f"chmod 664 {db_path}")

    print("\n# Asegurar que el directorio tenga permisos de escritura:")
    print(f"chmod 755 {parent_dir}")

    print("\n# Si el directorio no existe, crearlo:")
    print(f"mkdir -p {parent_dir}")

def main():
    """Función principal para diagnosticar la base de datos"""
    if len(sys.argv) != 2:
        print("Uso: python sqlite_diagnosis.py <path_to_database>")
        print("Ejemplo: python sqlite_diagnosis.py /ruta/a/tu/base_de_datos.db")
        sys.exit(1)

    db_path = sys.argv[1]

    # Realizar diagnóstico
    success = check_database_path(db_path)

    if not success:
        fix_permissions(db_path)
        print("\n❌ DIAGNÓSTICO FALLIDO - Revisa los errores arriba")
        sys.exit(1)
    else:
        print("\n✅ DIAGNÓSTICO EXITOSO - La base de datos debería funcionar")

if __name__ == "__main__":
    main()
