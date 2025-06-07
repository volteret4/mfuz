#!/usr/bin/env python3
"""
Script para medir el tiempo de ejecución individual de cada script del config_database_creator.json
"""

import json
import subprocess
import time
import sys
from pathlib import Path
import argparse
import sqlite3 
from collections import defaultdict


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


def run_single_script(script_name, original_config, temp_config_path, db_path):
    """Ejecutar un script individual y medir su tiempo y cambios en BD"""
    # Crear configuración temporal con solo este script
    temp_config = original_config.copy()
    temp_config['scripts_order'] = [script_name]
    
    # Guardar configuración temporal
    save_config_temp(temp_config, temp_config_path)
    
    print(f"\n{'='*60}")
    print(f"Ejecutando: {script_name}")
    print(f"{'='*60}")
    
    # Crear snapshot ANTES de ejecutar
    print("Creando snapshot de BD antes de ejecutar...")
    before_snapshot = get_db_snapshot(db_path)
    
    # Ejecutar el comando y medir tiempo
    start_time = time.time()
    
    try:
        result = subprocess.run([
            'python', 'db_creator.py', 
            '--config', temp_config_path
        ], capture_output=True, text=True)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Crear snapshot DESPUÉS de ejecutar
        print("Creando snapshot de BD después de ejecutar...")
        after_snapshot = get_db_snapshot(db_path)
        
        # Analizar cambios
        changes = compare_snapshots(before_snapshot, after_snapshot)
        
        success = result.returncode == 0
        
        return {
            'script': script_name,
            'execution_time': execution_time,
            'success': success,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode,
            'db_changes': changes,
            'before_snapshot': before_snapshot,
            'after_snapshot': after_snapshot
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
            'before_snapshot': before_snapshot,
            'after_snapshot': None
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
            
        result = run_single_script(script, config_data, args.temp_config, db_path)
        results.append(result)
        
        # Mostrar resultado inmediato
        status = "✓ ÉXITO" if result['success'] else "✗ ERROR"
        print(f"Resultado: {status} - Tiempo: {format_time(result['execution_time'])}")
        
        # Mostrar cambios inmediatamente
        if result['db_changes']:
            print(format_changes_report(script, result['db_changes'], result['execution_time']))
        
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
    
    print(f"\n📋 Reporte detallado guardado en: {args.output}")
    print(f"📋 Reporte de cambios en BD guardado en: {args.db_changes_report}")

if __name__ == "__main__":
    main()