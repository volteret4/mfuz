#!/usr/bin/env python3
"""
Script para medir el tiempo de ejecución individual de cada script del config_database_creator.json
"""

import json
import subprocess
import time
import sys
import os
import hashlib
from pathlib import Path
import argparse
import sqlite3 
from collections import defaultdict



def get_filesystem_snapshot(project_root='.', excluded_dirs=None, excluded_extensions=None):
    """
    Crear un snapshot del estado actual del sistema de archivos del proyecto
    
    Args:
        project_root: Ruta raíz del proyecto
        excluded_dirs: Lista de directorios a excluir (ej: ['.git', '__pycache__', '.venv'])
        excluded_extensions: Lista de extensiones a excluir (ej: ['.pyc', '.log'])
    """
    if excluded_dirs is None:
        excluded_dirs = {'.git', '__pycache__', '.venv', 'venv', '.pytest_cache', 
                        'node_modules', '.mypy_cache', '.tox', 'dist', 'build'}
    
    if excluded_extensions is None:
        excluded_extensions = {'.pyc', '.pyo', '.pyd', '__pycache__'}
    
    snapshot = {
        'files': {},
        'directories': set(),
        'total_files': 0,
        'total_size': 0,
        'project_root': str(Path(project_root).resolve())
    }
    
    project_path = Path(project_root).resolve()
    
    try:
        for root, dirs, files in os.walk(project_path):
            # Filtrar directorios excluidos
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
            current_path = Path(root)
            relative_path = current_path.relative_to(project_path)
            
            # Añadir directorio al snapshot
            snapshot['directories'].add(str(relative_path))
            
            for file in files:
                file_path = current_path / file
                relative_file_path = file_path.relative_to(project_path)
                
                # Filtrar archivos por extensión
                if file_path.suffix.lower() in excluded_extensions:
                    continue
                
                try:
                    stat_info = file_path.stat()
                    
                    # Calcular hash del archivo para detectar cambios de contenido
                    file_hash = None
                    if stat_info.st_size < 10 * 1024 * 1024:  # Solo hash para archivos < 10MB
                        try:
                            with open(file_path, 'rb') as f:
                                file_hash = hashlib.md5(f.read()).hexdigest()
                        except (PermissionError, OSError):
                            file_hash = None
                    
                    snapshot['files'][str(relative_file_path)] = {
                        'size': stat_info.st_size,
                        'mtime': stat_info.st_mtime,
                        'hash': file_hash,
                        'extension': file_path.suffix.lower()
                    }
                    
                    snapshot['total_files'] += 1
                    snapshot['total_size'] += stat_info.st_size
                    
                except (PermissionError, OSError, FileNotFoundError):
                    # Archivo no accesible, saltarlo
                    continue
    
    except Exception as e:
        print(f"⚠️  Error creando snapshot del sistema de archivos: {e}")
        return None
    
    snapshot['directories'] = sorted(list(snapshot['directories']))
    print(f"✓ Snapshot FS creado: {snapshot['total_files']} archivos, {format_file_size(snapshot['total_size'])}")
    
    return snapshot


def compare_filesystem_snapshots(before_snapshot, after_snapshot):
    """
    Comparar dos snapshots del sistema de archivos y detectar cambios
    """
    if not before_snapshot or not after_snapshot:
        return None
    
    changes = {
        'new_files': [],
        'deleted_files': [],
        'modified_files': [],
        'new_directories': [],
        'deleted_directories': [],
        'size_changes': {
            'before': before_snapshot['total_size'],
            'after': after_snapshot['total_size'],
            'difference': after_snapshot['total_size'] - before_snapshot['total_size']
        },
        'file_count_change': after_snapshot['total_files'] - before_snapshot['total_files']
    }
    
    before_files = set(before_snapshot['files'].keys())
    after_files = set(after_snapshot['files'].keys())
    before_dirs = set(before_snapshot['directories'])
    after_dirs = set(after_snapshot['directories'])
    
    # Detectar archivos nuevos y eliminados
    changes['new_files'] = sorted(list(after_files - before_files))
    changes['deleted_files'] = sorted(list(before_files - after_files))
    
    # Detectar directorios nuevos y eliminados
    changes['new_directories'] = sorted(list(after_dirs - before_dirs))
    changes['deleted_directories'] = sorted(list(before_dirs - after_dirs))
    
    # Detectar archivos modificados
    common_files = before_files.intersection(after_files)
    for file_path in common_files:
        before_file = before_snapshot['files'][file_path]
        after_file = after_snapshot['files'][file_path]
        
        # Comparar por hash si está disponible, sino por mtime y size
        if before_file['hash'] and after_file['hash']:
            if before_file['hash'] != after_file['hash']:
                changes['modified_files'].append({
                    'path': file_path,
                    'change_type': 'content',
                    'size_before': before_file['size'],
                    'size_after': after_file['size'],
                    'size_diff': after_file['size'] - before_file['size']
                })
        else:
            # Fallback: comparar por timestamp y tamaño
            if (before_file['mtime'] != after_file['mtime'] or 
                before_file['size'] != after_file['size']):
                changes['modified_files'].append({
                    'path': file_path,
                    'change_type': 'timestamp_or_size',
                    'size_before': before_file['size'],
                    'size_after': after_file['size'],
                    'size_diff': after_file['size'] - before_file['size']
                })
    
    return changes


def format_filesystem_changes_report(script_name, fs_changes, execution_time):
    """
    Formatear un reporte legible de cambios en el sistema de archivos
    """
    if not fs_changes:
        return f"\n{script_name}: Sin cambios detectados en el sistema de archivos"
    
    # Verificar si hay cambios significativos
    has_changes = (fs_changes['new_files'] or fs_changes['deleted_files'] or 
                   fs_changes['modified_files'] or fs_changes['new_directories'] or 
                   fs_changes['deleted_directories'])
    
    if not has_changes:
        return f"\n{script_name}: Sin cambios detectados en el sistema de archivos"
    
    report = f"\n{'='*60}\n"
    report += f"CAMBIOS EN SISTEMA DE ARCHIVOS - {script_name} ({format_time(execution_time)})\n"
    report += f"{'='*60}\n"
    
    # Nuevas directorios
    if fs_changes['new_directories']:
        report += f"📁 NUEVOS DIRECTORIOS ({len(fs_changes['new_directories'])}):\n"
        for directory in fs_changes['new_directories']:
            report += f"  + {directory}/\n"
        report += "\n"
    
    # Directorios eliminados
    if fs_changes['deleted_directories']:
        report += f"🗑️  DIRECTORIOS ELIMINADOS ({len(fs_changes['deleted_directories'])}):\n"
        for directory in fs_changes['deleted_directories']:
            report += f"  - {directory}/\n"
        report += "\n"
    
    # Archivos nuevos
    if fs_changes['new_files']:
        report += f"📄 ARCHIVOS NUEVOS ({len(fs_changes['new_files'])}):\n"
        # Agrupar por extensión para mejor visualización
        files_by_ext = defaultdict(list)
        for file_path in fs_changes['new_files']:
            ext = Path(file_path).suffix.lower() or '(sin extensión)'
            files_by_ext[ext].append(file_path)
        
        for ext, files in sorted(files_by_ext.items()):
            report += f"  {ext} ({len(files)}):\n"
            for file_path in files[:5]:  # Mostrar máximo 5 archivos por extensión
                report += f"    + {file_path}\n"
            if len(files) > 5:
                report += f"    ... y {len(files) - 5} más\n"
        report += "\n"
    
    # Archivos eliminados
    if fs_changes['deleted_files']:
        report += f"🗑️  ARCHIVOS ELIMINADOS ({len(fs_changes['deleted_files'])}):\n"
        for file_path in fs_changes['deleted_files'][:10]:  # Mostrar máximo 10
            report += f"  - {file_path}\n"
        if len(fs_changes['deleted_files']) > 10:
            report += f"  ... y {len(fs_changes['deleted_files']) - 10} más\n"
        report += "\n"
    
    # Archivos modificados
    if fs_changes['modified_files']:
        report += f"✏️  ARCHIVOS MODIFICADOS ({len(fs_changes['modified_files'])}):\n"
        # Ordenar por cambio de tamaño para mostrar los más significativos primero
        sorted_modified = sorted(fs_changes['modified_files'], 
                               key=lambda x: abs(x.get('size_diff', 0)), reverse=True)
        
        for file_info in sorted_modified[:10]:  # Mostrar máximo 10
            path = file_info['path']
            size_diff = file_info.get('size_diff', 0)
            
            if size_diff != 0:
                size_change = f" ({'+' if size_diff > 0 else ''}{format_file_size(abs(size_diff))})"
            else:
                size_change = ""
                
            report += f"  ~ {path}{size_change}\n"
        
        if len(fs_changes['modified_files']) > 10:
            report += f"  ... y {len(fs_changes['modified_files']) - 10} más\n"
        report += "\n"
    
    # Resumen de cambios
    file_count_change = fs_changes['file_count_change']
    if file_count_change != 0:
        symbol = "+" if file_count_change > 0 else ""
        report += f"📊 TOTAL ARCHIVOS: {symbol}{file_count_change}\n"
    
    # Cambio de tamaño total
    size_change = fs_changes['size_changes']['difference']
    if size_change != 0:
        symbol = "+" if size_change > 0 else ""
        report += f"💾 TAMAÑO TOTAL: {symbol}{format_file_size(abs(size_change))}\n"
    
    return report


def get_project_root_from_config(config_data):
    """
    Intentar determinar la ruta raíz del proyecto desde la configuración
    """
    # Buscar pistas en la configuración sobre la ubicación del proyecto
    db_path = config_data.get('common', {}).get('db_path', '')
    
    if db_path:
        # Usar el directorio padre de la base de datos como aproximación
        db_parent = Path(db_path).parent
        return str(db_parent) if db_parent != Path('.') else '.'
    
    # Fallback: usar directorio actual
    return '.'

def format_file_size(size_bytes):
    """Formatear tamaño de archivo en formato legible"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    if i == 0:
        return f"{int(size)} {size_names[i]}"
    else:
        return f"{size:.2f} {size_names[i]}"

def load_config(config_path):
    """Cargar configuración desde archivo JSON"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config_temp(config_data, temp_path):
    """Guardar configuración temporal con un solo script"""
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)


def run_single_script(script_name, original_config, temp_config_path, db_path, project_root='.'):
    """Ejecutar un script individual y medir su tiempo, cambios en BD y sistema de archivos"""
    # Crear configuración temporal con solo este script
    temp_config = original_config.copy()
    temp_config['scripts_order'] = [script_name]
    
    # Guardar configuración temporal
    save_config_temp(temp_config, temp_config_path)
    
    print(f"\n{'='*60}")
    print(f"Ejecutando: {script_name}")
    print(f"{'='*60}")
    
    # Crear snapshots ANTES de ejecutar
    print("Creando snapshot de BD antes de ejecutar...")
    before_db_snapshot = get_db_snapshot(db_path)
    
    print("Creando snapshot del sistema de archivos antes de ejecutar...")
    before_fs_snapshot = get_filesystem_snapshot(project_root)
    
    # Ejecutar el comando y medir tiempo
    start_time = time.time()
    
    try:
        result = subprocess.run([
            'python', 'db_creator.py', 
            '--config', temp_config_path
        ], capture_output=True, text=True)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Crear snapshots DESPUÉS de ejecutar
        print("Creando snapshot de BD después de ejecutar...")
        after_db_snapshot = get_db_snapshot(db_path)
        
        print("Creando snapshot del sistema de archivos después de ejecutar...")
        after_fs_snapshot = get_filesystem_snapshot(project_root)
        
        # Analizar cambios
        db_changes = compare_snapshots(before_db_snapshot, after_db_snapshot)
        fs_changes = compare_filesystem_snapshots(before_fs_snapshot, after_fs_snapshot)
        
        success = result.returncode == 0
        
        return {
            'script': script_name,
            'execution_time': execution_time,
            'success': success,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode,
            'db_changes': db_changes,
            'fs_changes': fs_changes,
            'before_db_snapshot': before_db_snapshot,
            'after_db_snapshot': after_db_snapshot,
            'before_fs_snapshot': before_fs_snapshot,
            'after_fs_snapshot': after_fs_snapshot
        }
        
    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        return {
            'script': script_name,
            'execution_time': execution_time,
            'success': False,
            'stdout': '',
            'stderr': f'ERROR: {str(e)}',
            'returncode': -2,
            'db_changes': None,
            'fs_changes': None,
            'before_db_snapshot': before_db_snapshot,
            'after_db_snapshot': None,
            'before_fs_snapshot': before_fs_snapshot,
            'after_fs_snapshot': None
        }

def format_time(seconds):
    """Formatear tiempo en formato legible"""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.2f}s"

def extract_all_scripts(config_data):
    """Extraer todos los posibles scripts del config (excluyendo 'common')"""
    scripts = []
    for key in config_data.keys():
        if key not in ['scripts_order', 'common'] and isinstance(config_data[key], dict):
            scripts.append(key)
    return scripts

# estadisticas

def get_db_snapshot(db_path):
    """Crear un snapshot del estado actual de la base de datos"""
    # Verificar si la base de datos existe
    db_file = Path(db_path)
    
    if not db_file.exists():
        print(f"✓ Base de datos {db_path} no existe, creando snapshot vacío")
        return {
            'tables': {},
            'total_rows': 0,
            'db_exists': False,
            'file_size': 0
        }
    
    # Verificar si tenemos permisos para leer el archivo
    if not db_file.is_file():
        print(f"✗ Error: {db_path} existe pero no es un archivo válido")
        return {
            'tables': {},
            'total_rows': 0,
            'db_exists': False,
            'file_size': 0
        }
    
    try:
        # Obtener tamaño del archivo
        file_size = db_file.stat().st_size
        print(f"✓ Archivo encontrado: {format_file_size(file_size)}")
        
        # Intentar conectar a la BD
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar que es una BD SQLite válida
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        
        snapshot = {
            'tables': {},
            'total_rows': 0,
            'db_exists': True,
            'file_size': file_size
        }
        
        # Obtener lista de tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"✓ Encontradas {len(tables)} tablas")
        
        for table in tables:
            try:
                # Obtener estructura de la tabla (columnas)
                cursor.execute(f"PRAGMA table_info({table})")
                columns = {}
                for col_info in cursor.fetchall():
                    col_id, col_name, col_type, not_null, default_val, pk = col_info
                    columns[col_name] = {
                        'type': col_type,
                        'not_null': not_null,
                        'default': default_val,
                        'primary_key': pk
                    }
                
                # Obtener número de filas
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                row_count = cursor.fetchone()[0]
                
                snapshot['tables'][table] = {
                    'columns': columns,
                    'row_count': row_count
                }
                snapshot['total_rows'] += row_count
                
            except Exception as table_error:
                print(f"⚠️  Error procesando tabla {table}: {table_error}")
                # Continuar con las demás tablas
                continue
        
        conn.close()
        print(f"✓ Snapshot completado: {len(snapshot['tables'])} tablas, {snapshot['total_rows']:,} filas")
        return snapshot
        
    except sqlite3.DatabaseError as db_error:
        print(f"✗ Error de BD SQLite: {db_error}")
        return {
            'tables': {},
            'total_rows': 0,
            'db_exists': False,
            'file_size': 0
        }
    except PermissionError:
        print(f"✗ Error de permisos: no se puede acceder a {db_path}")
        return {
            'tables': {},
            'total_rows': 0,
            'db_exists': False,
            'file_size': 0
        }
    except Exception as e:
        print(f"✗ Error inesperado al crear snapshot de {db_path}: {e}")
        return {
            'tables': {},
            'total_rows': 0,
            'db_exists': False,
            'file_size': 0
        }



def compare_snapshots(before_snapshot, after_snapshot):
    """Comparar dos snapshots y detectar cambios"""
    if not before_snapshot or not after_snapshot:
        return None
    
    # Caso especial: BD no existía antes pero sí después (primera creación)
    if not before_snapshot.get('db_exists', True) and after_snapshot.get('db_exists', True):
        return {
            'database_created': True,
            'new_tables': list(after_snapshot['tables'].keys()),
            'new_columns': {},
            'modified_columns': {},
            'row_changes': {table: {'before': 0, 'after': data['row_count'], 'difference': data['row_count']} 
                          for table, data in after_snapshot['tables'].items()},
            'total_row_change': after_snapshot['total_rows'],
            'file_size_change': {
                'before': 0,
                'after': after_snapshot['file_size'],
                'difference': after_snapshot['file_size']
            }
        }
    
    # Caso especial: BD existía antes pero no después (¿eliminada?)
    if before_snapshot.get('db_exists', True) and not after_snapshot.get('db_exists', True):
        return {
            'database_deleted': True,
            'new_tables': [],
            'new_columns': {},
            'modified_columns': {},
            'row_changes': {},
            'total_row_change': -before_snapshot['total_rows'],
            'file_size_change': {
                'before': before_snapshot['file_size'],
                'after': 0,
                'difference': -before_snapshot['file_size']
            }
        }
    
    # Caso normal: comparación entre dos BD existentes
    changes = {
        'new_tables': [],
        'new_columns': defaultdict(list),
        'modified_columns': defaultdict(list),
        'row_changes': {},
        'total_row_change': after_snapshot['total_rows'] - before_snapshot['total_rows'],
        'file_size_change': {
            'before': before_snapshot['file_size'],
            'after': after_snapshot['file_size'],
            'difference': after_snapshot['file_size'] - before_snapshot['file_size']
        }
    }
    
    # Detectar nuevas tablas
    before_tables = set(before_snapshot['tables'].keys())
    after_tables = set(after_snapshot['tables'].keys())
    changes['new_tables'] = list(after_tables - before_tables)
    
    # Analizar tablas existentes
    for table in before_tables.intersection(after_tables):
        before_table = before_snapshot['tables'][table]
        after_table = after_snapshot['tables'][table]
        
        # Detectar nuevas columnas
        before_cols = set(before_table['columns'].keys())
        after_cols = set(after_table['columns'].keys())
        new_cols = after_cols - before_cols
        if new_cols:
            changes['new_columns'][table] = list(new_cols)
        
        # Detectar columnas modificadas
        for col in before_cols.intersection(after_cols):
            before_col = before_table['columns'][col]
            after_col = after_table['columns'][col]
            if before_col != after_col:
                changes['modified_columns'][table].append({
                    'column': col,
                    'before': before_col,
                    'after': after_col
                })
        
        # Detectar cambios en número de filas
        row_diff = after_table['row_count'] - before_table['row_count']
        if row_diff != 0:
            changes['row_changes'][table] = {
                'before': before_table['row_count'],
                'after': after_table['row_count'],
                'difference': row_diff
            }
    
    return changes

def format_changes_report(script_name, changes, execution_time):
    """Formatear un reporte de cambios legible"""
    if not changes:
        return f"\n{script_name}: Sin cambios detectados en la BD"
    
    report = f"\n{'='*60}\n"
    report += f"CAMBIOS EN BD - {script_name} ({format_time(execution_time)})\n"
    report += f"{'='*60}\n"
    
    # Caso especial: creación de base de datos
    if changes.get('database_created'):
        report += f"🆕 BASE DE DATOS CREADA\n"
        report += f"📋 TABLAS INICIALES ({len(changes['new_tables'])}):\n"
        for table in changes['new_tables']:
            report += f"  + {table}\n"
        report += f"📈 TOTAL FILAS INICIALES: +{changes['total_row_change']:,} filas\n"
        report += f"💾 TAMAÑO INICIAL: {format_file_size(changes['file_size_change']['after'])}\n"
        return report
    
    # Caso especial: eliminación de base de datos
    if changes.get('database_deleted'):
        report += f"🗑️  BASE DE DATOS ELIMINADA\n"
        report += f"💾 TAMAÑO PERDIDO: {format_file_size(changes['file_size_change']['before'])}\n"
        return report
    
    # Nuevas tablas
    if changes['new_tables']:
        report += f"📋 NUEVAS TABLAS ({len(changes['new_tables'])}):\n"
        for table in changes['new_tables']:
            report += f"  + {table}\n"
        report += "\n"
    
    # Nuevas columnas
    if changes['new_columns']:
        report += f"📝 NUEVAS COLUMNAS:\n"
        for table, columns in changes['new_columns'].items():
            report += f"  {table}: {', '.join(columns)}\n"
        report += "\n"
    
    # Columnas modificadas
    if changes['modified_columns']:
        report += f"🔧 COLUMNAS MODIFICADAS:\n"
        for table, modifications in changes['modified_columns'].items():
            report += f"  {table}:\n"
            for mod in modifications:
                report += f"    - {mod['column']}: {mod['before']} → {mod['after']}\n"
        report += "\n"
    
    # Cambios en filas
    if changes['row_changes']:
        report += f"📊 CAMBIOS EN FILAS:\n"
        # Ordenar por diferencia absoluta (mayor impacto primero)
        sorted_changes = sorted(changes['row_changes'].items(), 
                              key=lambda x: abs(x[1]['difference']), reverse=True)
        
        for table, row_data in sorted_changes:
            diff = row_data['difference']
            symbol = "+" if diff > 0 else ""
            report += f"  {table}: {row_data['before']} → {row_data['after']} ({symbol}{diff:,})\n"
        report += "\n"
    
    # Resumen total
    total_change = changes['total_row_change']
    if total_change != 0:
        symbol = "+" if total_change > 0 else ""
        report += f"📈 TOTAL FILAS: {symbol}{total_change:,} filas\n"
    
    # Cambio de tamaño de archivo
    size_change = changes.get('file_size_change', {})
    if size_change and size_change['difference'] != 0:
        before_size = format_file_size(size_change['before'])
        after_size = format_file_size(size_change['after'])
        diff_size = size_change['difference']
        symbol = "+" if diff_size > 0 else ""
        diff_formatted = format_file_size(abs(diff_size))
        report += f"💾 TAMAÑO BD: {before_size} → {after_size} ({symbol}{diff_formatted})\n"
    
    return report




def main():
    parser = argparse.ArgumentParser(description='Medir tiempo de ejecución de scripts individuales')
    parser.add_argument('--config', default='config/config_database_creator.json',
                       help='Ruta al archivo de configuración')
    parser.add_argument('--scripts', nargs='*', 
                       help='Scripts específicos a probar (si no se especifica, prueba todos)')
    parser.add_argument('--output', default='execution_times_report.txt',
                       help='Archivo de salida para el reporte')
    parser.add_argument('--temp-config', default='temp_config_test.json',
                       help='Archivo temporal para configuración')
    parser.add_argument('--db-changes-report', default='db_changes_report.txt',
                       help='Archivo de salida para el reporte de cambios en BD')
    parser.add_argument('--fs-changes-report', default='filesystem_changes_report.txt',
                   help='Archivo de salida para el reporte de cambios en sistema de archivos')
    parser.add_argument('--project-root', default='.',
                   help='Ruta raíz del proyecto para monitorear cambios de archivos')
    args = parser.parse_args()
    
    # Verificar que existe el archivo de configuración
    if not Path(args.config).exists():
        print(f"Error: No se encuentra el archivo {args.config}")
        sys.exit(1)
    
    # Cargar configuración
    print(f"Cargando configuración desde: {args.config}")
    config_data = load_config(args.config)
    
    # Obtener ruta de la base de datos
    db_path = config_data.get('common', {}).get('db_path')
    if not db_path:
        print("Error: No se encontró 'db_path' en la configuración")
        sys.exit(1)
    
    print(f"Base de datos: {db_path}")
    
    # Mostrar tamaño inicial de la BD si existe
    if Path(db_path).exists():
        initial_size = Path(db_path).stat().st_size
        print(f"Tamaño inicial de BD: {format_file_size(initial_size)}")
    else:
        print("Base de datos no existe - será creada durante el proceso")
    



    # Obtener lista de scripts a probar
    if args.scripts:
        scripts_to_test = args.scripts
    else:
        scripts_to_test = extract_all_scripts(config_data)
    
    print(f"Scripts a probar: {len(scripts_to_test)}")
    for script in scripts_to_test:
        print(f"  - {script}")
    
    # Ejecutar pruebas
    results = []
    total_start_time = time.time()
    
    for i, script in enumerate(scripts_to_test, 1):
        print(f"\n[{i}/{len(scripts_to_test)}] Probando: {script}")
        
        if script not in config_data:
            print(f"ADVERTENCIA: Script '{script}' no encontrado en configuración")
            continue
            
        result = run_single_script(script, config_data, args.temp_config, db_path, args.project_root)
        results.append(result)
        
        # Mostrar resultado inmediato
        status = "✓ ÉXITO" if result['success'] else "✗ ERROR"
        print(f"Resultado: {status} - Tiempo: {format_time(result['execution_time'])}")
        
        # Mostrar cambios inmediatamente
        if result['db_changes']:
            print(format_changes_report(script, result['db_changes'], result['execution_time']))

        # Mostrar cambios de sistema de archivos inmediatamente
        if result['fs_changes']:
            print(format_filesystem_changes_report(script, result['fs_changes'], result['execution_time']))
        
        if not result['success'] and result['stderr']:
            print(f"Error: {result['stderr'][:200]}...")
    
    total_end_time = time.time()
    total_execution_time = total_end_time - total_start_time
    
    # Limpiar archivo temporal
    temp_config_path = Path(args.temp_config)
    if temp_config_path.exists():
        temp_config_path.unlink()
    
    # Generar reporte
    print(f"\n{'='*80}")
    print("REPORTE FINAL DE TIEMPOS DE EJECUCIÓN")
    print(f"{'='*80}")
    
    # Ordenar por tiempo de ejecución
    results.sort(key=lambda x: x['execution_time'], reverse=True)
    
    successful_results = [r for r in results if r['success']]
    failed_results = [r for r in results if not r['success']]
    
    # Mostrar resultados exitosos
    if successful_results:
        print(f"\n📊 SCRIPTS EXITOSOS ({len(successful_results)}):")
        print("-" * 80)
        for result in successful_results:
            print(f"{result['script']:<40} {format_time(result['execution_time']):>15}")
    
    # Mostrar scripts fallidos
    if failed_results:
        print(f"\n❌ SCRIPTS FALLIDOS ({len(failed_results)}):")
        print("-" * 80)
        for result in failed_results:
            print(f"{result['script']:<40} {format_time(result['execution_time']):>15} - {result['stderr'][:30]}...")
    
    print(f"\n⏱️  TIEMPO TOTAL DE PRUEBAS: {format_time(total_execution_time)}")
    
    # Mostrar tamaño final de la BD
    if Path(db_path).exists():
        final_size = Path(db_path).stat().st_size
        print(f"💾 TAMAÑO FINAL DE BD: {format_file_size(final_size)}")
    else:
        print("💾 Base de datos no existe al final del proceso")
    
    # Guardar reporte detallado
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write("REPORTE DETALLADO DE TIEMPOS DE EJECUCIÓN\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Configuración: {args.config}\n")
        f.write(f"Base de datos: {db_path}\n")

        f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Proyecto: {args.project_root}\n\n")
        f.write(f"Total de scripts probados: {len(results)}\n")
        f.write(f"Scripts exitosos: {len(successful_results)}\n")
        f.write(f"Scripts fallidos: {len(failed_results)}\n")
        f.write(f"Tiempo total: {format_time(total_execution_time)}\n\n")
        
        f.write("RESULTADOS DETALLADOS:\n")
        f.write("-" * 80 + "\n")
        
        for result in results:
            f.write(f"\nScript: {result['script']}\n")
            f.write(f"Tiempo: {format_time(result['execution_time'])}\n")
            f.write(f"Éxito: {'Sí' if result['success'] else 'No'}\n")
            f.write(f"Código de retorno: {result['returncode']}\n")
            if result['fs_changes']:
                f.write(format_filesystem_changes_report(result['script'], result['fs_changes'], result['execution_time']))
                f.write("\n")

            if result['stderr']:
                f.write(f"Error:\n{result['stderr']}\n")
                
            if result['stdout']:
                f.write(f"Salida:\n{result['stdout'][:500]}...\n")
            
            f.write("-" * 40 + "\n")
    
    # Guardar reporte de cambios en BD
    with open(args.db_changes_report, 'w', encoding='utf-8') as f:
        f.write("REPORTE DE CAMBIOS EN BASE DE DATOS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Base de datos: {db_path}\n\n")
        for result in results:
            if result['db_changes']:
                f.write(format_changes_report(result['script'], result['db_changes'], result['execution_time']))
                f.write("\n")
        f.write("REPORTE DE CAMBIOS EN SISTEMA DE ARCHIVOS\n")
        f.write("=" * 80 + "\n\n")        
        for result in results:
            if result['fs_changes']:
                f.write(format_filesystem_changes_report(result['script'], result['fs_changes'], result['execution_time']))
                f.write("\n")

        print(f"📋 Reporte de cambios en FS guardado en: {args.fs_changes_report}")
    print(f"\n📋 Reporte detallado guardado en: {args.output}")
    print(f"📋 Reporte de cambios en BD guardado en: {args.db_changes_report}")

if __name__ == "__main__":
    main()