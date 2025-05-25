#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Independent and NME Charts Scraper

Este script extrae datos de las listas independientes y de NME de música del Reino Unido 
desde Wikipedia.

Tipos de datos soportados:
- UK Independent Singles Chart (número 1 por año desde 1980)
- NME Chart (número 1 por década desde 1970s-1980s)

El script puede procesar múltiples años y décadas de forma automática
y guardar los datos tanto en CSV como en base de datos SQLite.

Autor: Claude
Fecha: Mayo 2025
"""

import os
import re
import csv
import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
import sys
import time
from time import sleep

# Importar del script base
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from base_module import PROJECT_ROOT

# Variables globales para configuración
CONFIG = {}
DB_PATH = None

# Configuración
BASE_URL = "https://en.wikipedia.org"
OUTPUT_DIR = "uk_indie_nme_charts_data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# URLs para UK Independent Charts (por año)
UK_INDIE_URLS = {
    # 1980s
    "80s": "/wiki/Lists_of_UK_Independent_Singles_Chart_number_ones_of_the_1980s",
    # Años individuales (ejemplos principales)
    "1999": "/wiki/List_of_UK_Independent_Singles_Chart_number_ones_of_1999",
    "2000": "/wiki/List_of_UK_Independent_Singles_Chart_number_ones_of_2000", 
    "2001": "/wiki/List_of_UK_Independent_Singles_Chart_number_ones_of_2001",
    "2002": "/wiki/List_of_UK_Independent_Singles_Chart_number_ones_of_2002",
    "2007": "/wiki/List_of_UK_Independent_Singles_Chart_number_ones_of_2007"
}

# URLs para NME Charts (por década)
NME_URLS = {
    "70s": "/wiki/List_of_NME_number-one_singles_of_the_1970s",
    "80s": "/wiki/List_of_NME_number-one_singles_of_the_1980s",
    "60s": "/wiki/List_of_NME_number-one_singles_of_the_1960s"
}

# Años disponibles para UK Independent Charts
INDIE_YEARS_AVAILABLE = list(range(1980, 2026))  # 1980-2025
NME_DECADES_AVAILABLE = ["60s", "70s", "80s"]

def init_config(config=None):
    """Inicializa la configuración del script"""
    global CONFIG, DB_PATH
    if config:
        CONFIG = config
        DB_PATH = Path(config.get('db_path', 'music_database.db'))
        print(f"Configuración inicializada desde db_creator")
        print(f"Base de datos: {DB_PATH}")
        print(f"Géneros habilitados: {config.get('generos', False)}")
    else:
        DB_PATH = Path(PROJECT_ROOT, "music_database.db") if 'PROJECT_ROOT' in globals() else Path("music_database.db")

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    if DB_PATH is None:
        raise ValueError("Base de datos no configurada. Ejecuta init_config() primero.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_indie_nme_charts_tables():
    """Crea las tablas para almacenar los datos de charts independientes y NME"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla para UK Independent Singles Chart
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uk_indie_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            año INTEGER NOT NULL,
            fecha_chart TEXT,
            artista TEXT NOT NULL,
            single TEXT NOT NULL,
            sello_discográfico TEXT,
            semanas_numero_uno INTEGER,
            posicion_main_chart INTEGER,
            notas TEXT,
            género TEXT,
            artist_id INTEGER,
            song_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    ''')
    
    # Tabla para NME Charts  
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nme_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            década TEXT NOT NULL,
            año INTEGER,
            fecha_chart TEXT,
            artista TEXT NOT NULL,
            single TEXT NOT NULL,
            semanas_numero_uno INTEGER,
            notas TEXT,
            diferencias_chart_oficial TEXT,
            género TEXT,
            artist_id INTEGER,
            song_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    ''')
    
    # Índices para mejorar rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_indie_artist ON uk_indie_charts(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_indie_year ON uk_indie_charts(año)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nme_artist ON nme_charts(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nme_decade ON nme_charts(década)')
    
    conn.commit()
    conn.close()
    print("Tablas de UK Independent y NME Charts creadas correctamente")

def descargar_pagina(url):
    """Descarga una página web y devuelve su contenido HTML"""
    try:
        print(f"Descargando {url}")
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"Error al descargar {url}: {e}")
        return None

def limpiar_texto(texto):
    """Limpia el texto extraído eliminando caracteres especiales y espacios innecesarios"""
    if not texto:
        return texto
    
    # Eliminar comillas dobles múltiples y referencias
    texto = re.sub(r'"{2,}', '"', texto)
    texto = re.sub(r'^"(.*)"$', r'\1', texto)
    texto = re.sub(r'\[[\w\s]*\]', '', texto)
    texto = re.sub(r'♦|♠|♣|♥|★|☆', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    
    return texto.strip()

def generar_url_indie_chart(year):
    """
    Genera la URL para un año específico del UK Independent Singles Chart
    
    Args:
        year (int): Año a consultar
        
    Returns:
        str: URL completa
    """
    return f"/wiki/List_of_UK_Independent_Singles_Chart_number_ones_of_{year}"

def extraer_indie_chart_data(soup, year):
    """
    Extrae datos del UK Independent Singles Chart para un año específico
    
    Args:
        soup (BeautifulSoup): Contenido HTML de la página
        year (int): Año del chart
        
    Returns:
        list: Lista de diccionarios con los datos extraídos
    """
    data = []
    
    # Buscar tablas principales en la página
    tablas = soup.find_all('table', class_='wikitable')
    
    if not tablas:
        print(f"No se encontraron tablas en la página indie {year}")
        return data
    
    # Buscar la tabla principal con los datos del chart
    tabla_principal = None
    for tabla in tablas:
        # Verificar encabezados de tabla
        encabezados = tabla.find_all('th')
        if encabezados and len(encabezados) >= 2:
            textos = [th.get_text().strip().lower() for th in encabezados]
            # Buscar encabezados típicos del indie chart
            if any(keyword in ' '.join(textos) for keyword in ['date', 'single', 'artist', 'weeks']):
                tabla_principal = tabla
                break
    
    if not tabla_principal:
        print(f"No se encontró tabla principal para indie {year}")
        return data
    
    # Extraer filas de datos
    filas = tabla_principal.find_all('tr')
    
    for fila in filas[1:]:  # Saltar encabezados
        celdas = fila.find_all(['td', 'th'])
        
        if len(celdas) < 2:
            continue
        
        try:
            # Estructura típica: Fecha | Single | Artista | [Sello] | [Semanas] | [Posición main chart]
            fecha = limpiar_texto(celdas[0].get_text()) if len(celdas) > 0 else 'N/A'
            single = limpiar_texto(celdas[1].get_text()) if len(celdas) > 1 else 'N/A'
            artista = limpiar_texto(celdas[2].get_text()) if len(celdas) > 2 else 'N/A'
            sello = limpiar_texto(celdas[3].get_text()) if len(celdas) > 3 else 'N/A'
            semanas = limpiar_texto(celdas[4].get_text()) if len(celdas) > 4 else 'N/A'
            pos_main = limpiar_texto(celdas[5].get_text()) if len(celdas) > 5 else 'N/A'
            
            # Convertir valores numéricos
            try:
                semanas_num = int(re.search(r'\d+', semanas).group()) if re.search(r'\d+', semanas) else None
            except:
                semanas_num = None
                
            try:
                pos_main_num = int(re.search(r'\d+', pos_main).group()) if re.search(r'\d+', pos_main) else None
            except:
                pos_main_num = None
                
            if artista and single and artista != 'N/A' and single != 'N/A':
                data.append({
                    'año': year,
                    'fecha_chart': fecha,
                    'artista': artista,
                    'single': single,
                    'sello_discográfico': sello,
                    'semanas_numero_uno': semanas_num,
                    'posicion_main_chart': pos_main_num,
                    'notas': 'N/A',
                    'género': 'N/A'  # Se puede añadir después si se solicita
                })
                
        except Exception as e:
            print(f"Error al extraer datos de fila indie: {e}")
            continue
    
    return data

def extraer_nme_chart_data(soup, decade):
    """
    Extrae datos del NME Chart para una década específica
    
    Args:
        soup (BeautifulSoup): Contenido HTML de la página
        decade (str): Década del chart (60s, 70s, 80s)
        
    Returns:
        list: Lista de diccionarios con los datos extraídos
    """
    data = []
    
    # Buscar tablas principales en la página
    tablas = soup.find_all('table', class_='wikitable')
    
    if not tablas:
        print(f"No se encontraron tablas en la página NME {decade}")
        return data
    
    # Buscar la tabla principal con los datos del chart
    tabla_principal = None
    for tabla in tablas:
        # Verificar encabezados de tabla
        encabezados = tabla.find_all('th')
        if encabezados and len(encabezados) >= 3:
            textos = [th.get_text().strip().lower() for th in encabezados]
            # Buscar encabezados típicos del NME chart
            if any(keyword in ' '.join(textos) for keyword in ['single', 'artist', 'date', 'weeks']):
                tabla_principal = tabla
                break
    
    if not tabla_principal:
        print(f"No se encontró tabla principal para NME {decade}")
        return data
    
    # Extraer filas de datos
    filas = tabla_principal.find_all('tr')
    
    for fila in filas[1:]:  # Saltar encabezados
        celdas = fila.find_all(['td', 'th'])
        
        if len(celdas) < 3:
            continue
        
        try:
            # Estructura típica: Single | Artista | Fecha(s) | Semanas
            single = limpiar_texto(celdas[0].get_text())
            artista = limpiar_texto(celdas[1].get_text())
            fecha = limpiar_texto(celdas[2].get_text())
            semanas = limpiar_texto(celdas[3].get_text()) if len(celdas) > 3 else '1'
            
            # Extraer año de la fecha si es posible
            year_match = re.search(r'19\d{2}', fecha)
            year = int(year_match.group()) if year_match else None
            
            # Convertir semanas a entero si es posible
            try:
                semanas_num = int(re.search(r'\d+', semanas).group()) if re.search(r'\d+', semanas) else 1
            except:
                semanas_num = 1
                
            if artista and single:
                data.append({
                    'década': f"19{decade}",
                    'año': year,
                    'fecha_chart': fecha,
                    'artista': artista,
                    'single': single,
                    'semanas_numero_uno': semanas_num,
                    'notas': 'Chart independiente NME',
                    'diferencias_chart_oficial': 'N/A',  # Se puede añadir manualmente
                    'género': 'N/A'  # Se puede añadir después si se solicita
                })
                
        except Exception as e:
            print(f"Error al extraer datos de fila NME: {e}")
            continue
    
    return data

def find_artist_id(artist_name):
    """Busca el artist_id en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name,))
    result = cursor.fetchone()
    
    if result:
        conn.close()
        return result[0]
    
    cursor.execute("SELECT id FROM artists WHERE LOWER(name) LIKE LOWER(?)", (f"%{artist_name}%",))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def find_song_id(title, artist_name):
    """Busca el song_id en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM songs 
        WHERE LOWER(title) = LOWER(?) AND LOWER(artist) = LOWER(?)
    """, (title, artist_name))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def insert_indie_data_to_db(indie_data):
    """Inserta datos de UK Independent Chart en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for record in indie_data:
        # Buscar IDs relacionados
        artist_id = find_artist_id(record['artista'])
        song_id = find_song_id(record['single'], record['artista'])
        
        # Verificar si ya existe
        cursor.execute("""
            SELECT id FROM uk_indie_charts 
            WHERE año = ? AND artista = ? AND single = ?
        """, (record['año'], record['artista'], record['single']))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO uk_indie_charts 
                (año, fecha_chart, artista, single, sello_discográfico, semanas_numero_uno, 
                 posicion_main_chart, notas, género, artist_id, song_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['año'],
                record['fecha_chart'],
                record['artista'],
                record['single'],
                record['sello_discográfico'],
                record['semanas_numero_uno'],
                record['posicion_main_chart'],
                record['notas'],
                record.get('género', 'N/A'),
                artist_id,
                song_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} registros de UK Independent Chart en la base de datos")
    return inserted_count

def insert_nme_data_to_db(nme_data):
    """Inserta datos de NME Chart en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for record in nme_data:
        # Buscar IDs relacionados
        artist_id = find_artist_id(record['artista'])
        song_id = find_song_id(record['single'], record['artista'])
        
        # Verificar si ya existe
        cursor.execute("""
            SELECT id FROM nme_charts 
            WHERE década = ? AND artista = ? AND single = ?
        """, (record['década'], record['artista'], record['single']))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO nme_charts 
                (década, año, fecha_chart, artista, single, semanas_numero_uno, 
                 notas, diferencias_chart_oficial, género, artist_id, song_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['década'],
                record['año'],
                record['fecha_chart'],
                record['artista'],  
                record['single'],
                record['semanas_numero_uno'],
                record['notas'],
                record['diferencias_chart_oficial'],
                record.get('género', 'N/A'),
                artist_id,
                song_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} registros de NME Chart en la base de datos")
    return inserted_count

def guardar_csv(datos, archivo, tipo):
    """Guarda los datos en un archivo CSV"""
    if not datos:
        print(f"No hay datos para guardar en {archivo}")
        return
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    
    # Determinar los encabezados según el tipo de datos
    if tipo == "indie":
        encabezados = ['año', 'fecha_chart', 'artista', 'single', 'sello_discográfico', 
                      'semanas_numero_uno', 'posicion_main_chart', 'notas', 'género']
    elif tipo == "nme":
        encabezados = ['década', 'año', 'fecha_chart', 'artista', 'single', 
                      'semanas_numero_uno', 'notas', 'diferencias_chart_oficial', 'género']
    else:
        encabezados = list(datos[0].keys())
    
    try:
        with open(archivo, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=encabezados)
            writer.writeheader()
            for fila in datos:
                # Filtrar columnas que no están en los encabezados
                fila_filtrada = {k: v for k, v in fila.items() if k in encabezados}
                writer.writerow(fila_filtrada)
        
        print(f"Datos guardados correctamente en {archivo} ({len(datos)} registros)")
    except Exception as e:
        print(f"Error al guardar el archivo CSV {archivo}: {e}")

def procesar_indie_charts(years=None):
    """
    Procesa los UK Independent Singles Charts para años específicos o todos
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    
    Args:
        years (list, optional): Lista de años a procesar. Si None, procesa años principales
    """
    print("\n=== Procesando UK Independent Singles Charts ===")
    
    if years is None:
        # Procesar años principales conocidos
        years = [1999, 2000, 2001, 2002, 2007]
    
    all_data = []
    
    for year in years:
        # Verificar si ya existen datos
        if verificar_datos_existentes_indie(year):
            continue
        
        print(f"Procesando año {year}")
        url = urljoin(BASE_URL, generar_url_indie_chart(year))
        soup = descargar_pagina(url)
        
        if soup:
            data = extraer_indie_chart_data(soup, year)
            if data:
                all_data.extend(data)
                print(f"Extraídos {len(data)} registros para {year}")
            else:
                print(f"No se encontraron datos para {year}")
        
        time.sleep(1)  # Rate limiting
    
    if all_data:
        # Guardar en base de datos
        insert_indie_data_to_db(all_data)
        
        # Guardar CSV como respaldo
        archivo_csv = os.path.join(OUTPUT_DIR, "indie", "uk_indie_charts_all.csv")
        guardar_csv(all_data, archivo_csv, "indie")
        
        print(f"Total procesados: {len(all_data)} registros de UK Independent Chart")

def procesar_nme_charts(decades=None):
    """
    Procesa los NME Charts para décadas específicas o todas
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    
    Args:
        decades (list, optional): Lista de décadas a procesar. Si None, procesa todas disponibles
    """
    print("\n=== Procesando NME Charts ===")
    
    if decades is None:
        decades = NME_DECADES_AVAILABLE
    
    all_data = []
    
    for decade in decades:
        # Verificar si ya existen datos
        if verificar_datos_existentes_nme(decade):
            continue
        
        print(f"Procesando década {decade}")
        url = urljoin(BASE_URL, NME_URLS[decade])
        soup = descargar_pagina(url)
        
        if soup:
            data = extraer_nme_chart_data(soup, decade)
            if data:
                all_data.extend(data)
                print(f"Extraídos {len(data)} registros para {decade}")
            else:
                print(f"No se encontraron datos para {decade}")
        
        time.sleep(1)  # Rate limiting
    
    if all_data:
        # Guardar en base de datos
        insert_nme_data_to_db(all_data)
        
        # Guardar CSV como respaldo
        archivo_csv = os.path.join(OUTPUT_DIR, "nme", "nme_charts_all.csv")
        guardar_csv(all_data, archivo_csv, "nme")
        
        print(f"Total procesados: {len(all_data)} registros de NME Chart")

        
def verificar_datos_existentes_indie(year):
    """
    Verifica si ya existen datos de indie chart para un año específico
    
    Args:
        year (int): Año a verificar
        
    Returns:
        bool: True si ya existen datos, False si no
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM uk_indie_charts WHERE año = ?", (year,))
    count = cursor.fetchone()[0]
    
    conn.close()
    
    if count > 0:
        print(f"Ya existen {count} registros de indie chart para {year}. Saltando...")
        return True
    return False

def verificar_datos_existentes_nme(decade):
    """
    Verifica si ya existen datos de NME chart para una década específica
    
    Args:
        decade (str): Década a verificar (60s, 70s, 80s)
        
    Returns:
        bool: True si ya existen datos, False si no
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    decade_full = f"19{decade}"
    cursor.execute("SELECT COUNT(*) FROM nme_charts WHERE década = ?", (decade_full,))
    count = cursor.fetchone()[0]
    
    conn.close()
    
    if count > 0:
        print(f"Ya existen {count} registros de NME chart para {decade_full}. Saltando...")
        return True
    return False


def main(config=None):
    """Función principal del script"""
    # Inicializar configuración si se proporciona
    if config:
        init_config(config)
        print(f"Usando base de datos: {DB_PATH}")
    
    # Crear tablas de base de datos
    create_indie_nme_charts_tables()
    
    # Crear directorios de salida (para respaldo CSV)
    os.makedirs(os.path.join(OUTPUT_DIR, "indie"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "nme"), exist_ok=True)
    
    print("Iniciando extracción de UK Independent y NME Charts...")
    
    # Procesar UK Independent Charts (años principales)
    procesar_indie_charts()
    
    # Procesar NME Charts (todas las décadas disponibles)
    procesar_nme_charts()
    
    print("\n=== Extracción completada ===")
    print(f"Datos guardados en la base de datos: {DB_PATH}")
    print(f"CSVs de respaldo guardados en: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()