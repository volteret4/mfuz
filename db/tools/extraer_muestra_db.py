#!/usr/bin/env python3
"""
Script para extraer muestras de 3 elementos de cada tabla de la base de datos musical
Uso: python script.py [json|csv] [ruta_base_datos.db]
"""

import sqlite3
import json
import csv
import sys
import os
from typing import Dict, List, Any

def get_sample_data(db_path: str, limit: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extrae una muestra de datos de cada tabla principal de la base de datos
    """
    
    # Tablas principales a muestrear (excluyendo FTS y tablas auxiliares)
    main_tables = [
        'songs', 'artists', 'albums', 'genres', 'lyrics', 'song_links',
        'scrobbles', 'labels', 'listens', 'feeds', 'discogs_discography',
        'uk_charts_singles', 'billboard_yearend_singles'
    ]
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Para obtener diccionarios en lugar de tuplas
    
    sample_data = {}
    
    for table in main_tables:
        try:
            cursor = conn.execute(f"SELECT * FROM {table} LIMIT {limit}")
            rows = cursor.fetchall()
            
            # Convertir Row objects a diccionarios
            sample_data[table] = [dict(row) for row in rows]
            
            print(f"✓ Extraídos {len(rows)} registros de {table}")
            
        except sqlite3.Error as e:
            print(f"⚠️  Error al consultar tabla {table}: {e}")
            sample_data[table] = []
    
    conn.close()
    return sample_data

def export_to_json(data: Dict[str, List[Dict[str, Any]]], output_file: str):
    """Exporta los datos a formato JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"✓ Datos exportados a {output_file}")

def export_to_csv(data: Dict[str, List[Dict[str, Any]]], output_dir: str):
    """Exporta los datos a múltiples archivos CSV (uno por tabla)"""
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for table_name, records in data.items():
        if not records:  # Skip empty tables
            continue
            
        csv_file = os.path.join(output_dir, f"{table_name}_sample.csv")
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if records:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
                print(f"✓ Tabla {table_name} exportada a {csv_file}")

def show_summary(data: Dict[str, List[Dict[str, Any]]]):
    """Muestra un resumen de los datos extraídos"""
    print("\n" + "="*50)
    print("RESUMEN DE DATOS EXTRAÍDOS")
    print("="*50)
    
    total_records = 0
    for table_name, records in data.items():
        count = len(records)
        total_records += count
        status = "✓" if count > 0 else "✗"
        print(f"{status} {table_name:<25} {count:>3} registros")
    
    print("-"*50)
    print(f"Total de registros extraídos: {total_records}")

def main():
    if len(sys.argv) < 2:
        print("Uso: python script.py [json|csv] [ruta_base_datos.db]")
        print("Ejemplos:")
        print("  python script.py json mi_musica.db")
        print("  python script.py csv mi_musica.db")
        sys.exit(1)
    
    output_format = sys.argv[1].lower()
    db_path = sys.argv[2] if len(sys.argv) > 2 else "music_database.db"
    
    if output_format not in ['json', 'csv']:
        print("❌ Formato debe ser 'json' o 'csv'")
        sys.exit(1)
    
    if not os.path.exists(db_path):
        print(f"❌ No se encontró la base de datos: {db_path}")
        sys.exit(1)
    
    print(f"🎵 Extrayendo muestras de {db_path}...")
    print(f"📊 Formato de salida: {output_format.upper()}")
    print("-"*50)
    
    # Extraer datos
    sample_data = get_sample_data(db_path)
    
    # Mostrar resumen
    show_summary(sample_data)
    
    # Exportar según el formato solicitado
    if output_format == 'json':
        output_file = f"music_sample_{os.path.basename(db_path).split('.')[0]}.json"
        export_to_json(sample_data, output_file)
    else:  # csv
        output_dir = f"music_samples_{os.path.basename(db_path).split('.')[0]}"
        export_to_csv(sample_data, output_dir)
    
    print(f"\n🎉 ¡Proceso completado exitosamente!")

if __name__ == "__main__":
    main()