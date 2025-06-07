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

def load_config(config_path):
    """Cargar configuración desde archivo JSON"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config_temp(config_data, temp_path):
    """Guardar configuración temporal con un solo script"""
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

def run_single_script(script_name, original_config, temp_config_path):
    """Ejecutar un script individual y medir su tiempo"""
    # Crear configuración temporal con solo este script
    temp_config = original_config.copy()
    temp_config['scripts_order'] = [script_name]
    
    # Guardar configuración temporal
    save_config_temp(temp_config, temp_config_path)
    
    print(f"\n{'='*60}")
    print(f"Ejecutando: {script_name}")
    print(f"{'='*60}")
    
    # Ejecutar el comando y medir tiempo
    start_time = time.time()
    
    try:
        result = subprocess.run([
            'python', 'db_creator.py', 
            '--config', temp_config_path
        ], capture_output=True, text=True, timeout=3600)  # timeout de 1 hora
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        success = result.returncode == 0
        
        return {
            'script': script_name,
            'execution_time': execution_time,
            'success': success,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        end_time = time.time()
        execution_time = end_time - start_time
        return {
            'script': script_name,
            'execution_time': execution_time,
            'success': False,
            'stdout': '',
            'stderr': 'TIMEOUT: Ejecución excedió 1 hora',
            'returncode': -1
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
            'returncode': -2
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
    
    args = parser.parse_args()
    
    # Verificar que existe el archivo de configuración
    if not Path(args.config).exists():
        print(f"Error: No se encuentra el archivo {args.config}")
        sys.exit(1)
    
    # Cargar configuración
    print(f"Cargando configuración desde: {args.config}")
    config_data = load_config(args.config)
    
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
            
        result = run_single_script(script, config_data, args.temp_config)
        results.append(result)
        
        # Mostrar resultado inmediato
        status = "✓ ÉXITO" if result['success'] else "✗ ERROR"
        print(f"Resultado: {status} - Tiempo: {format_time(result['execution_time'])}")
        
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
    
    # Guardar reporte detallado
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write("REPORTE DETALLADO DE TIEMPOS DE EJECUCIÓN\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Configuración: {args.config}\n")
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
    
    print(f"\n📋 Reporte detallado guardado en: {args.output}")

if __name__ == "__main__":
    main()