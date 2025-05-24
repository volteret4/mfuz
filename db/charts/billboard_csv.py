#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Billboard Charts Scraper

Este script extrae datos de las listas de Billboard desde Wikipedia 
y genera archivos CSV con esa información.

El script puede extraer diferentes tipos de datos:
- Billboard Year-End Hot 100 (1958-presente)
- Billboard Year-End top singles (1950-1957)
- Billboard Hot 100 top-ten singles por año
- Hot Country Albums number ones por año
- Top Country Albums number ones por año

Uso:
    python billboard_scraper.py [opciones]

Opciones:
    --type TYPE     Tipo de datos a extraer (yearend, hot100, country)
    --year YEAR     Año específico a extraer (1950-2024)
    --all           Extraer todos los datos disponibles

Ejemplos:
    python billboard_scraper.py --type yearend --year 1975
    python billboard_scraper.py --type hot100 --year 1971
    python billboard_scraper.py --type country --year 2005
    python billboard_scraper.py --all

Autor: Claude
Fecha: Mayo 2025
"""

import os
import re
import csv
import time
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import urllib.parse
from time import sleep
import threading
import time as time_module
import sqlite3
from pathlib import Path
import sys

# Añadir esta línea después de las importaciones existentes
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from base_module import PROJECT_ROOT

# Configuración para APIs
DISCOGS_TOKEN = "MJXLYUGuqwXHVONuYZxVWFSXvFmxpdLqauTRcCsP"  # Opcional: añade tu token de Discogs para más requests
MUSICBRAINZ_USER_AGENT = "BillboardScraper/1.0 (frodobolson@disroot.org)"  # Cambia por tu email
ultimo_request_discogs = 0
ultimo_request_musicbrainz = 0
lock_discogs = threading.Lock()
lock_musicbrainz = threading.Lock()

# Cache para evitar consultas repetidas
cache_generos = {}


# Aumentar delays si sigues teniendo problemas
if DISCOGS_TOKEN:
    DISCOGS_REQUEST_DELAY = 3.5  # Con token puedes ir más rápido
else:
    DISCOGS_REQUEST_DELAY = 6.0

MUSICBRAINZ_REQUEST_DELAY = 1.0

# Configuración
BASE_URL = "https://en.wikipedia.org"
OUTPUT_DIR = "billboard_data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# URLs específicas para Billboard
BILLBOARD_URLS = {
    # Year-End singles (1950-1957: top 30, 1958+: Hot 100)
    "yearend_early": "/wiki/Billboard_year-end_top_30_singles_of_{year}",  # 1950-1957
    "yearend_hot100": "/wiki/Billboard_Year-End_Hot_100_singles_of_{year}",  # 1958+
    
    # Hot 100 top-ten por año
    "hot100_topten": "/wiki/List_of_Billboard_Hot_100_top-ten_singles_in_{year}",
    
    # Country Albums
    "country_albums_old": "/wiki/List_of_Hot_Country_Albums_number_ones_of_{year}",  # años anteriores
    "country_albums_new": "/wiki/List_of_Top_Country_Albums_number_ones_of_{year}",  # años recientes
}
# Añadir estas variables globales después de las existentes
CONFIG = {}
DB_PATH = None

def init_config(config=None):
    """Inicializa la configuración del script"""
    global CONFIG, DB_PATH, DISCOGS_TOKEN, MUSICBRAINZ_USER_AGENT, DISCOGS_REQUEST_DELAY
    if config:
        CONFIG = config
        DB_PATH = Path(config.get('db_path', 'music_database.db'))
        
        # Actualizar configuraciones de API desde config
        if 'discogs_token' in config:
            DISCOGS_TOKEN = config['discogs_token']
        if 'musicbrainz_user_agent' in config:
            MUSICBRAINZ_USER_AGENT = config['musicbrainz_user_agent']
        if 'rate_limit' in config:
            DISCOGS_REQUEST_DELAY = config['rate_limit']
        
        print(f"Configuración inicializada desde db_creator")
        print(f"Base de datos: {DB_PATH}")
        print(f"Géneros habilitados: {config.get('generos', False)}")
    else:
        # Configuración por defecto si no se proporciona
        DB_PATH = Path(PROJECT_ROOT, "music_database.db") if 'PROJECT_ROOT' in globals() else Path("music_database.db")

def configurar_argumentos():
    """Configura los argumentos de línea de comandos - VERSIÓN ADAPTADA"""
    # Si se ejecuta desde db_creator, usar configuración en lugar de argumentos
    if CONFIG:
        # Crear args simulados basados en la configuración
        class ConfigArgs:
            def __init__(self, config):
                self.type = config.get('type', 'all')
                self.year = config.get('year')
                self.all = config.get('type') == 'all' or config.get('all', False)
                self.generos = config.get('generos', False)
        
        return ConfigArgs(CONFIG)
    
    # Solo parsear argumentos si se ejecuta directamente
    parser = argparse.ArgumentParser(description="Billboard Charts Scraper")
    parser.add_argument("--type", choices=["yearend", "hot100", "country"],
                        help="Tipo de datos a extraer")
    parser.add_argument("--year", type=int, choices=range(1950, 2025),
                        help="Año específico a extraer")
    parser.add_argument("--all", action="store_true",
                        help="Extraer todos los datos disponibles")
    parser.add_argument("--generos", action="store_true",
                        help="Incluir información de géneros musicales")
    return parser.parse_args()

def obtener_url_billboard(tipo, anio):
    """
    Obtiene la URL de Wikipedia para Billboard según el tipo y año.
    
    Args:
        tipo (str): Tipo de datos a extraer
        anio (int): Año específico
        
    Returns:
        str: URL completa
    """
    if tipo == "yearend":
        if anio <= 1957:
            return urljoin(BASE_URL, BILLBOARD_URLS["yearend_early"].format(year=anio))
        else:
            return urljoin(BASE_URL, BILLBOARD_URLS["yearend_hot100"].format(year=anio))
    
    elif tipo == "hot100":
        return urljoin(BASE_URL, BILLBOARD_URLS["hot100_topten"].format(year=anio))
    
    elif tipo == "country":
        # Intentar primero con el formato más reciente, luego el antiguo
        if anio >= 2000:
            return urljoin(BASE_URL, BILLBOARD_URLS["country_albums_new"].format(year=anio))
        else:
            return urljoin(BASE_URL, BILLBOARD_URLS["country_albums_old"].format(year=anio))
    
    return None

def limpiar_texto(texto):
    """
    Versión mejorada de limpieza de texto.
    """
    if not texto:
        return texto
    
    # Eliminar referencias de Wikipedia [1], [2], etc.
    texto = re.sub(r'\[\d+\]', '', texto)
    texto = re.sub(r'\[[\w\s]*\]', '', texto)
    
    # Eliminar símbolos especiales comunes
    texto = re.sub(r'[♦♠♣♥★☆†‡•]', '', texto)
    
    # Limpiar comillas múltiples
    texto = re.sub(r'"{2,}', '"', texto)
    texto = re.sub(r'^"(.*)"$', r'\1', texto)
    
    # Limpiar espacios
    texto = re.sub(r'\s+', ' ', texto)
    texto = texto.strip()
    
    # Eliminar texto entre paréntesis al final (como fechas de lanzamiento)
    texto = re.sub(r'\s*\([^)]*\)$', '', texto)
    
    return texto

def verificar_url_existe(url):
    """
    Verifica si una URL existe antes de intentar descargarla.
    """
    try:
        response = requests.head(url, headers=HEADERS, timeout=10)
        return response.status_code == 200
    except:
        return False

def descargar_pagina(url):
    """
    Descarga una página web y devuelve su contenido HTML.
    
    Args:
        url (str): URL de la página a descargar
        
    Returns:
        BeautifulSoup: Objeto BeautifulSoup con el contenido de la página
    """
    try:
        print(f"Descargando {url}")
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"Error al descargar {url}: {e}")
        return None

def extraer_yearend_singles(soup, anio):
    """
    Extrae los datos de Billboard Year-End singles.
    Versión mejorada que maneja diferentes estructuras de tabla.
    """
    singles = []
    
    # Buscar todas las tablas posibles
    tablas = soup.find_all('table', class_=['wikitable', 'sortable', 'plainrowheaders'])
    
    if not tablas:
        # Buscar tablas sin clase específica
        tablas = soup.find_all('table')
    
    if not tablas:
        print(f"No se encontraron tablas en la página del año {anio}")
        return singles
    
    # Analizar cada tabla para encontrar la correcta
    tabla_principal = None
    for tabla in tablas:
        # Verificar si tiene suficientes filas
        filas = tabla.find_all('tr')
        if len(filas) < 10:  # Debe tener al menos 10 canciones
            continue
            
        # Verificar estructura de encabezados
        encabezados = tabla.find_all('th')
        if encabezados:
            textos_encabezados = [th.get_text().strip().lower() for th in encabezados]
            # Buscar indicadores de que es la tabla correcta
            indicadores = ['no.', 'position', 'rank', 'title', 'song', 'artist', 'performer']
            if any(indicador in ' '.join(textos_encabezados) for indicador in indicadores):
                tabla_principal = tabla
                break
        
        # Si no hay encabezados claros, verificar contenido de las primeras filas
        filas_muestra = filas[1:4]  # Revisar las primeras 3 filas de datos
        tiene_numeros = False
        tiene_texto = False
        
        for fila in filas_muestra:
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) >= 2:
                primera_celda = limpiar_texto(celdas[0].get_text())
                if re.match(r'^\d+$', primera_celda) and int(primera_celda) <= 100:
                    tiene_numeros = True
                if len(celdas) >= 2 and celdas[1].get_text().strip():
                    tiene_texto = True
        
        if tiene_numeros and tiene_texto:
            tabla_principal = tabla
            break
    
    if not tabla_principal:
        print(f"No se encontró una tabla válida en la página del año {anio}")
        # Debug: mostrar las primeras líneas de la página
        print("Primeras 500 caracteres de la página:")
        print(soup.get_text()[:500])
        return singles
    
    # Extraer filas de la tabla
    filas = tabla_principal.find_all('tr')
    
    # Determinar la estructura de la tabla analizando los encabezados
    encabezados = tabla_principal.find_all('th')
    indices_columnas = {'posicion': 0, 'titulo': 1, 'artista': 2}
    
    if encabezados:
        for i, th in enumerate(encabezados):
            texto = th.get_text().strip().lower()
            if 'title' in texto or 'song' in texto:
                indices_columnas['titulo'] = i
            elif 'artist' in texto or 'performer' in texto:
                indices_columnas['artista'] = i
            elif 'no.' in texto or 'position' in texto or 'rank' in texto:
                indices_columnas['posicion'] = i
    
    # Procesar filas de datos
    for i, fila in enumerate(filas):
        celdas = fila.find_all(['td', 'th'])
        
        # Saltar filas de encabezados
        if len(celdas) < 2 or all(celda.name == 'th' for celda in celdas):
            continue
        
        try:
            posicion = None
            titulo = None
            artista = None
            
            # Extraer datos según la estructura identificada
            if len(celdas) > indices_columnas['posicion']:
                pos_texto = limpiar_texto(celdas[indices_columnas['posicion']].get_text())
                if re.match(r'^\d+$', pos_texto):
                    posicion = int(pos_texto)
            
            if len(celdas) > indices_columnas['titulo']:
                titulo = limpiar_texto(celdas[indices_columnas['titulo']].get_text())
            
            if len(celdas) > indices_columnas['artista']:
                artista = limpiar_texto(celdas[indices_columnas['artista']].get_text())
            
            # Validar que tenemos datos mínimos
            if titulo and len(titulo) > 1 and artista and len(artista) > 1:
                singles.append({
                    'año': anio,
                    'posición': posicion if posicion else len(singles) + 1,
                    'título': titulo,
                    'artista': artista
                })
            
        except Exception as e:
            print(f"Error al procesar fila {i} del año {anio}: {e}")
            continue
    
    print(f"Extraídas {len(singles)} canciones del año {anio}")
    return singles

def extraer_hot100_topten(soup, anio):
    """
    Extrae los datos de Billboard Hot 100 top-ten singles.
    Versión mejorada que maneja diferentes estructuras de página.
    """
    singles = []
    
    # Las páginas de Hot 100 top-ten a menudo tienen múltiples tablas por mes
    # Primero intentamos encontrar todas las tablas posibles
    tablas = soup.find_all('table', class_=['wikitable', 'sortable', 'plainrowheaders'])
    
    if not tablas:
        tablas = soup.find_all('table')
    
    if not tablas:
        print(f"No se encontraron tablas en la página del año {anio}")
        return singles
    
    print(f"Encontradas {len(tablas)} tablas en la página")
    
    # Estas páginas suelen tener una tabla por mes o una tabla principal
    tablas_validas = []
    
    for i, tabla in enumerate(tablas):
        filas = tabla.find_all('tr')
        if len(filas) < 3:  # Muy pocas filas
            continue
            
        # Verificar si parece una tabla de singles
        encabezados = tabla.find_all('th')
        es_tabla_singles = False
        
        if encabezados:
            textos_enc = ' '.join([th.get_text().strip().lower() for th in encabezados])
            # Indicadores típicos de tablas de Hot 100 top-ten
            indicadores = ['single', 'song', 'title', 'artist', 'peak', 'position', 'chart', 'date', 'entry']
            if any(ind in textos_enc for ind in indicadores):
                es_tabla_singles = True
        
        # Si no hay encabezados claros, verificar contenido
        if not es_tabla_singles:
            filas_muestra = filas[1:4]
            for fila in filas_muestra:
                celdas = fila.find_all(['td', 'th'])
                if len(celdas) >= 3:
                    # Buscar patrones típicos: fecha, título con enlace, artista
                    tiene_enlace = any(celda.find('a') for celda in celdas)
                    tiene_fecha = any(re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b', 
                                               celda.get_text().lower()) for celda in celdas)
                    if tiene_enlace and (tiene_fecha or len(celdas) >= 4):
                        es_tabla_singles = True
                        break
        
        if es_tabla_singles:
            tablas_validas.append((i, tabla))
            print(f"Tabla {i+1} identificada como válida")
    
    if not tablas_validas:
        print(f"No se encontraron tablas válidas para el año {anio}")
        return singles
    
    # Procesar todas las tablas válidas
    for tabla_idx, tabla in tablas_validas:
        print(f"Procesando tabla {tabla_idx + 1}...")
        singles_tabla = extraer_singles_de_tabla_hot100(tabla, anio)
        singles.extend(singles_tabla)
    
    # Eliminar duplicados basados en título y artista
    singles_unicos = []
    vistos = set()
    
    for single in singles:
        clave = (single['título'].lower(), single['artista'].lower())
        if clave not in vistos:
            vistos.add(clave)
            singles_unicos.append(single)
    
    print(f"Extraídos {len(singles_unicos)} singles únicos del año {anio}")
    return singles_unicos


def extraer_singles_de_tabla_hot100(tabla, anio):
    """
    Extrae singles de una tabla específica de Hot 100 top-ten.
    """
    singles = []
    filas = tabla.find_all('tr')
    
    # Analizar estructura de encabezados
    encabezados = tabla.find_all('th')
    estructura = analizar_estructura_hot100(encabezados)
    
    for fila in filas[1:]:  # Saltar encabezados
        celdas = fila.find_all(['td', 'th'])
        
        if len(celdas) < 2:
            continue
        
        try:
            single_data = extraer_datos_fila_hot100(celdas, estructura, anio)
            if single_data:
                singles.append(single_data)
        except Exception as e:
            continue
    
    return singles


def analizar_estructura_hot100(encabezados):
    """
    Analiza los encabezados para determinar la estructura de la tabla.
    """
    estructura = {
        'fecha': None,
        'titulo': None,
        'artista': None,
        'pico': None,
        'semanas': None
    }
    
    if not encabezados:
        # Estructura por defecto si no hay encabezados
        return {
            'fecha': 0,
            'titulo': 1,
            'artista': 2,
            'pico': 3,
            'semanas': 4
        }
    
    for i, th in enumerate(encabezados):
        texto = th.get_text().strip().lower()
        
        if any(palabra in texto for palabra in ['date', 'week', 'chart']):
            estructura['fecha'] = i
        elif any(palabra in texto for palabra in ['single', 'song', 'title']):
            estructura['titulo'] = i
        elif 'artist' in texto or 'performer' in texto:
            estructura['artista'] = i
        elif 'peak' in texto or 'position' in texto:
            estructura['pico'] = i
        elif 'weeks' in texto or 'wks' in texto:
            estructura['semanas'] = i
    
    return estructura

def extraer_datos_fila_hot100(celdas, estructura, anio):
    """
    Extrae los datos de una fila específica de la tabla Hot 100.
    """
    if len(celdas) < 2:
        return None
    
    fecha = None
    titulo = None
    artista = None
    posicion_pico = None
    semanas = None
    
    # Extraer datos según la estructura identificada
    try:
        if estructura['fecha'] is not None and len(celdas) > estructura['fecha']:
            fecha = limpiar_texto(celdas[estructura['fecha']].get_text())
        
        if estructura['titulo'] is not None and len(celdas) > estructura['titulo']:
            titulo = limpiar_texto(celdas[estructura['titulo']].get_text())
        
        if estructura['artista'] is not None and len(celdas) > estructura['artista']:
            artista = limpiar_texto(celdas[estructura['artista']].get_text())
        
        if estructura['pico'] is not None and len(celdas) > estructura['pico']:
            pico_texto = limpiar_texto(celdas[estructura['pico']].get_text())
            if re.match(r'^\d+$', pico_texto):
                posicion_pico = int(pico_texto)
        
        if estructura['semanas'] is not None and len(celdas) > estructura['semanas']:
            sem_texto = limpiar_texto(celdas[estructura['semanas']].get_text())
            if re.match(r'^\d+$', sem_texto):
                semanas = int(sem_texto)
    
    except (IndexError, ValueError):
        pass
    
    # Si la estructura no funcionó, intentar heurísticas
    if not titulo or not artista:
        titulo, artista = buscar_titulo_artista_heuristico(celdas)
    
    # Buscar fecha si no se encontró
    if not fecha:
        for celda in celdas:
            texto = celda.get_text().strip()
            if re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d+', texto.lower()):
                fecha = limpiar_texto(texto)
                break
    
    # Validar que tenemos datos mínimos
    if titulo and len(titulo) > 1 and artista and len(artista) > 1:
        return {
            'año': anio,
            'título': titulo,
            'artista': artista,
            'posición_pico': posicion_pico if posicion_pico else 'N/A',
            'fecha_entrada': fecha if fecha else 'N/A',
            'semanas_chart': semanas if semanas else 'N/A'
        }
    
    return None

def buscar_titulo_artista_heuristico(celdas):
    """
    Usa heurísticas para encontrar título y artista cuando la estructura no es clara.
    """
    titulo = None
    artista = None
    
    # Primera estrategia: buscar enlaces (típicamente indican título o artista)
    celdas_con_enlaces = []
    for i, celda in enumerate(celdas):
        if celda.find('a'):
            celdas_con_enlaces.append((i, limpiar_texto(celda.get_text())))
    
    if len(celdas_con_enlaces) >= 2:
        # Asumir que el primer enlace es el título, el segundo el artista
        titulo = celdas_con_enlaces[0][1]
        artista = celdas_con_enlaces[1][1]
    elif len(celdas_con_enlaces) == 1:
        # Solo un enlace, probablemente el título
        titulo = celdas_con_enlaces[0][1]
        # Buscar artista en celdas adyacentes
        idx_titulo = celdas_con_enlaces[0][0]
        if idx_titulo + 1 < len(celdas):
            artista = limpiar_texto(celdas[idx_titulo + 1].get_text())
        elif idx_titulo - 1 >= 0:
            artista = limpiar_texto(celdas[idx_titulo - 1].get_text())
    
    # Si no hay enlaces, usar posiciones típicas
    if not titulo and len(celdas) > 1:
        # Saltar primera columna si parece ser fecha
        start_idx = 1 if re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)', 
                                  celdas[0].get_text().lower()) else 0
        
        if start_idx < len(celdas):
            titulo = limpiar_texto(celdas[start_idx].get_text())
        if start_idx + 1 < len(celdas):
            artista = limpiar_texto(celdas[start_idx + 1].get_text())
    
    return titulo, artista

def procesar_hot100_topten(anio):
    """
    Versión mejorada que maneja múltiples formatos de URL para Hot 100 top-ten.
    """
    urls_posibles = [
        f"https://en.wikipedia.org/wiki/List_of_Billboard_Hot_100_top-ten_singles_in_{anio}",
        f"https://en.wikipedia.org/wiki/List_of_Billboard_Hot_100_top_10_singles_in_{anio}",
        f"https://en.wikipedia.org/wiki/Billboard_Hot_100_top-ten_singles_of_{anio}",
        f"https://en.wikipedia.org/wiki/List_of_Hot_100_number-one_singles_of_{anio}_(U.S.)"
    ]
    
    soup = None
    url_exitosa = None
    
    for url in urls_posibles:
        print(f"Intentando URL: {url}")
        if verificar_url_existe(url):
            soup = descargar_pagina(url)
            if soup:
                url_exitosa = url
                break
        time.sleep(0.5)
    
    if not soup:
        print(f"No se pudo acceder a ninguna URL válida para Hot 100 top-ten del año {anio}")
        return
    
    print(f"Usando URL: {url_exitosa}")
    singles = extraer_hot100_topten(soup, anio)
    
    if singles:
        archivo = os.path.join(OUTPUT_DIR, "hot100", f"billboard_hot100_topten_{anio}.csv")
        guardar_csv_billboard(singles, archivo, "hot100")
    else:
        print(f"No se pudieron extraer datos de Hot 100 top-ten para el año {anio}")

def extraer_country_albums(soup, anio):
    """
    Extrae los datos de Country Albums number ones.
    
    Args:
        soup (BeautifulSoup): Objeto BeautifulSoup con el contenido de la página
        anio (int): Año a extraer
        
    Returns:
        list: Lista de diccionarios con los datos de los álbumes
    """
    albums = []
    
    # Buscar las tablas principales
    tablas = soup.find_all('table', class_='wikitable')
    
    if not tablas:
        print(f"No se encontraron tablas en la página del año {anio}")
        return albums
    
    # Buscar tabla con columnas típicas de álbumes country
    tabla_principal = None
    for tabla in tablas:
        encabezados = tabla.find_all('th')
        if encabezados and len(encabezados) >= 3:
            textos = [th.get_text().strip().lower() for th in encabezados]
            if ('album' in textos or 'title' in textos) and 'artist' in textos and ('date' in textos or 'week' in textos):
                tabla_principal = tabla
                break
    
    if not tabla_principal:
        print(f"No se encontró la tabla principal en la página del año {anio}")
        return albums
    
    # Extraer filas de la tabla
    filas = tabla_principal.find_all('tr')
    
    for fila in filas[1:]:
        celdas = fila.find_all(['td', 'th'])
        
        if len(celdas) < 3:
            continue
        
        try:
            fecha = None
            album = None
            artista = None
            semanas = None
            
            # Identificar columnas por contenido
            for i, celda in enumerate(celdas):
                texto = limpiar_texto(celda.get_text())
                
                # Primera columna suele ser fecha
                if i == 0 and (re.match(r'\w+ \d+', texto) or re.match(r'\d+/\d+', texto)):
                    fecha = texto
                # Columnas con enlaces suelen ser álbum/artista
                elif celda.find('a') and not album:
                    album = texto
                elif celda.find('a') and album and not artista:
                    artista = texto
                # Columna con número puede ser semanas en #1
                elif re.match(r'^\d+$', texto) and not semanas:
                    semanas = int(texto)
            
            # Si no hay enlaces, usar posiciones fijas
            if not fecha and len(celdas) > 0:
                fecha = limpiar_texto(celdas[0].get_text())
            if not album and len(celdas) > 1:
                album = limpiar_texto(celdas[1].get_text())
            if not artista and len(celdas) > 2:
                artista = limpiar_texto(celdas[2].get_text())
            if not semanas and len(celdas) > 3:
                sem_texto = limpiar_texto(celdas[3].get_text())
                if re.match(r'^\d+$', sem_texto):
                    semanas = int(sem_texto)
            
            if album and artista:
                albums.append({
                    'año': anio,
                    'fecha': fecha if fecha else 'N/A',
                    'álbum': album,
                    'artista': artista,
                    'semanas_en_1': semanas if semanas else 'N/A'
                })
        except Exception as e:
            print(f"Error al extraer datos de una fila: {e}")
            continue
    
    return albums

def guardar_csv_billboard(datos, archivo, tipo):
    """
    Versión actualizada que maneja todos los campos nuevos.
    """
    if not datos:
        print(f"No hay datos para guardar en {archivo}")
        return
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    
    # Determinar los encabezados según el tipo de datos
    if tipo == "yearend":
        encabezados = ['año', 'posición', 'título', 'artista']
    elif tipo == "hot100":
        encabezados = ['año', 'título', 'artista', 'posición_pico', 'fecha_entrada', 'semanas_chart']
    elif tipo == "country":
        encabezados = ['año', 'fecha', 'álbum', 'artista', 'semanas_en_1', 'posición']
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

def procesar_yearend_singles(anio):
    """
    Versión mejorada que verifica múltiples formatos de URL.
    """
    # Lista de posibles formatos de URL para el año
    urls_posibles = []
    
    if anio <= 1957:
        urls_posibles.extend([
            f"https://en.wikipedia.org/wiki/Billboard_year-end_top_30_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/Billboard_year-end_top_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/List_of_Billboard_number-one_singles_of_{anio}"
        ])
    else:
        urls_posibles.extend([
            f"https://en.wikipedia.org/wiki/Billboard_Year-End_Hot_100_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/Billboard_year-end_Hot_100_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/List_of_Billboard_Hot_100_number-one_singles_of_{anio}"
        ])
    
    soup = None
    url_exitosa = None
    
    # Probar cada URL hasta encontrar una que funcione
    for url in urls_posibles:
        print(f"Intentando URL: {url}")
        if verificar_url_existe(url):
            soup = descargar_pagina(url)
            if soup:
                url_exitosa = url
                break
        time.sleep(0.5)  # Pequeña pausa entre intentos
    
    if not soup:
        print(f"No se pudo acceder a ninguna URL válida para el año {anio}")
        return
    
    print(f"Usando URL: {url_exitosa}")
    singles = extraer_yearend_singles(soup, anio)
    
    if singles:
        tipo_archivo = "yearend_top30" if anio <= 1957 else "yearend_hot100"
        archivo = os.path.join(OUTPUT_DIR, "yearend", f"billboard_{tipo_archivo}_{anio}.csv")
        guardar_csv_billboard(singles, archivo, "yearend")
    else:
        print(f"No se pudieron extraer datos para el año {anio}")



def procesar_country_albums(anio):
    """
    Versión mejorada que prueba múltiples formatos de URL para Country Albums.
    """
    urls_posibles = [
        f"https://en.wikipedia.org/wiki/List_of_Hot_Country_Albums_number_ones_of_{anio}",
        f"https://en.wikipedia.org/wiki/List_of_Top_Country_Albums_number_ones_of_{anio}",
        f"https://en.wikipedia.org/wiki/List_of_Billboard_Hot_Country_Albums_number_ones_of_{anio}",
        f"https://en.wikipedia.org/wiki/List_of_Billboard_Top_Country_Albums_number_ones_of_{anio}",
        f"https://en.wikipedia.org/wiki/List_of_number-one_country_albums_of_{anio}_(U.S.)",
        f"https://en.wikipedia.org/wiki/Billboard_Top_Country_Albums_number_ones_of_{anio}"
    ]
    
    soup = None
    url_exitosa = None
    
    for url in urls_posibles:
        print(f"Intentando URL: {url}")
        try:
            response = requests.head(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                soup = descargar_pagina(url)
                if soup:
                    url_exitosa = url
                    break
            elif response.status_code == 404:
                print(f"URL no encontrada (404): {url}")
        except Exception as e:
            print(f"Error verificando URL {url}: {e}")
        
        time.sleep(0.5)
    
    if not soup:
        print(f"No se pudo acceder a ninguna URL válida para Country Albums del año {anio}")
        return
    
    print(f"Usando URL exitosa: {url_exitosa}")
    albums = extraer_country_albums_mejorado(soup, anio)
    
    if albums:
        archivo = os.path.join(OUTPUT_DIR, "country", f"billboard_country_albums_{anio}.csv")
        guardar_csv_billboard(albums, archivo, "country")
    else:
        print(f"No se pudieron extraer datos de Country Albums para el año {anio}")

def extraer_country_albums_mejorado(soup, anio):
    """
    Versión mejorada para extraer datos de Country Albums con mejor detección de tablas.
    """
    albums = []
    
    print(f"Analizando página de Country Albums para el año {anio}...")
    
    # Buscar todas las posibles tablas
    todas_las_tablas = soup.find_all('table')
    tablas_candidatas = []
    
    print(f"Encontradas {len(todas_las_tablas)} tablas en total")
    
    # Filtrar tablas que podrían contener datos de álbumes
    for i, tabla in enumerate(todas_las_tablas):
        filas = tabla.find_all('tr')
        if len(filas) < 3:  # Muy pocas filas
            continue
        
        # Verificar si tiene estructura de tabla de datos
        primera_fila = filas[0] if filas else None
        if not primera_fila:
            continue
            
        # Contar celdas en las primeras filas
        celdas_primera = len(primera_fila.find_all(['th', 'td']))
        if celdas_primera < 3:  # Necesitamos al menos 3 columnas
            continue
        
        # Buscar indicadores de contenido de álbumes
        texto_tabla = tabla.get_text().lower()
        indicadores_album = ['album', 'artist', 'date', 'week', 'chart', 'number', 'position']
        indicadores_encontrados = sum(1 for ind in indicadores_album if ind in texto_tabla)
        
        if indicadores_encontrados >= 2:  # Al menos 2 indicadores
            tablas_candidatas.append((i, tabla, indicadores_encontrados))
            print(f"Tabla {i+1}: {indicadores_encontrados} indicadores encontrados")
    
    # Ordenar por número de indicadores (más indicadores = más probable)
    tablas_candidatas.sort(key=lambda x: x[2], reverse=True)
    
    if not tablas_candidatas:
        print("No se encontraron tablas candidatas válidas")
        return albums
    
    # Procesar las tablas más prometedoras
    for tabla_idx, tabla, score in tablas_candidatas[:3]:  # Probar las 3 mejores
        print(f"Procesando tabla {tabla_idx + 1} (score: {score})...")
        albums_tabla = extraer_albums_de_tabla_country(tabla, anio)
        if albums_tabla:
            albums.extend(albums_tabla)
            print(f"Extraídos {len(albums_tabla)} álbumes de la tabla {tabla_idx + 1}")
        
        # Si ya tenemos buenos resultados, no necesitamos más tablas
        if len(albums) > 10:
            break
    
    # Eliminar duplicados
    albums_unicos = eliminar_duplicados_albums(albums)
    print(f"Total de álbumes únicos extraídos: {len(albums_unicos)}")
    
    return albums_unicos

def extraer_albums_de_tabla_country(tabla, anio):
    """
    Extrae álbumes de una tabla específica de Country Albums.
    """
    albums = []
    filas = tabla.find_all('tr')
    
    if len(filas) <= 1:
        return albums
    
    # Analizar encabezados para entender la estructura
    primera_fila = filas[0]
    encabezados = primera_fila.find_all(['th', 'td'])
    estructura = analizar_estructura_country(encabezados)
    
    print(f"Estructura detectada: {estructura}")
    
    # Procesar filas de datos
    for i, fila in enumerate(filas[1:], 1):
        celdas = fila.find_all(['td', 'th'])
        
        if len(celdas) < 2:
            continue
        
        try:
            album_data = extraer_datos_fila_country(celdas, estructura, anio)
            if album_data:
                albums.append(album_data)
        except Exception as e:
            print(f"Error procesando fila {i}: {e}")
            continue
    
    return albums

def analizar_estructura_country(encabezados):
    """
    Analiza los encabezados para determinar la estructura de la tabla de Country Albums.
    """
    estructura = {
        'fecha': None,
        'album': None,
        'artista': None,
        'semanas': None,
        'posicion': None
    }
    
    if not encabezados:
        return {
            'fecha': 0,
            'album': 1,
            'artista': 2,
            'semanas': 3
        }
    
    for i, th in enumerate(encabezados):
        texto = th.get_text().strip().lower()
        
        # Patrones para diferentes tipos de columnas
        if any(palabra in texto for palabra in ['date', 'week ending', 'chart date']):
            estructura['fecha'] = i
        elif any(palabra in texto for palabra in ['album', 'title']):
            estructura['album'] = i
        elif any(palabra in texto for palabra in ['artist', 'performer']):
            estructura['artista'] = i
        elif any(palabra in texto for palabra in ['weeks', 'wks', 'week']):
            estructura['semanas'] = i
        elif any(palabra in texto for palabra in ['position', 'peak', 'no.', '#']):
            estructura['posicion'] = i
    
    return estructura

def extraer_datos_fila_country(celdas, estructura, anio):
    """
    Extrae los datos de una fila específica de la tabla de Country Albums.
    """
    if len(celdas) < 2:
        return None
    
    fecha = None
    album = None
    artista = None
    semanas = None
    posicion = None
    
    try:
        # Extraer datos según la estructura identificada
        if estructura.get('fecha') is not None and len(celdas) > estructura['fecha']:
            fecha = limpiar_texto(celdas[estructura['fecha']].get_text())
        
        if estructura.get('album') is not None and len(celdas) > estructura['album']:
            album = limpiar_texto(celdas[estructura['album']].get_text())
        
        if estructura.get('artista') is not None and len(celdas) > estructura['artista']:
            artista = limpiar_texto(celdas[estructura['artista']].get_text())
        
        if estructura.get('semanas') is not None and len(celdas) > estructura['semanas']:
            sem_texto = limpiar_texto(celdas[estructura['semanas']].get_text())
            if re.match(r'^\d+$', sem_texto):
                semanas = int(sem_texto)
        
        if estructura.get('posicion') is not None and len(celdas) > estructura['posicion']:
            pos_texto = limpiar_texto(celdas[estructura['posicion']].get_text())
            if re.match(r'^\d+$', pos_texto):
                posicion = int(pos_texto)
    
    except (IndexError, ValueError):
        pass
    
    # Si la estructura automática falló, usar heurísticas
    if not album or not artista:
        album, artista = buscar_album_artista_heuristico(celdas)
    
    # Buscar fecha si no se encontró
    if not fecha:
        for celda in celdas:
            texto = celda.get_text().strip()
            # Buscar patrones de fecha
            if re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d+', texto.lower()):
                fecha = limpiar_texto(texto)
                break
            elif re.search(r'\d{1,2}/\d{1,2}', texto):
                fecha = limpiar_texto(texto)
                break
    
    # Validar que tenemos datos mínimos
    if album and len(album) > 1 and artista and len(artista) > 1:
        return {
            'año': anio,
            'fecha': fecha if fecha else 'N/A',
            'álbum': album,
            'artista': artista,
            'semanas_en_1': semanas if semanas else 'N/A',
            'posición': posicion if posicion else 'N/A'
        }
    
    return None

def buscar_album_artista_heuristico(celdas):
    """
    Usa heurísticas para encontrar álbum y artista cuando la estructura no es clara.
    """
    album = None
    artista = None
    
    # Estrategia 1: buscar enlaces (típicamente indican álbum o artista)
    celdas_con_enlaces = []
    for i, celda in enumerate(celdas):
        if celda.find('a'):
            texto = limpiar_texto(celda.get_text())
            if len(texto) > 1:  # Evitar enlaces vacíos
                celdas_con_enlaces.append((i, texto))
    
    if len(celdas_con_enlaces) >= 2:
        # Asumir que el primer enlace es el álbum, el segundo el artista
        album = celdas_con_enlaces[0][1]
        artista = celdas_con_enlaces[1][1]
    elif len(celdas_con_enlaces) == 1:
        # Solo un enlace, determinar si es álbum o artista
        texto_enlace = celdas_con_enlaces[0][1]
        idx_enlace = celdas_con_enlaces[0][0]
        
        # Si hay comillas, probablemente es un álbum
        if '"' in texto_enlace or "'" in texto_enlace:
            album = texto_enlace
            # Buscar artista en celdas adyacentes
            for adj_idx in [idx_enlace + 1, idx_enlace - 1]:
                if 0 <= adj_idx < len(celdas):
                    candidato = limpiar_texto(celdas[adj_idx].get_text())
                    if len(candidato) > 1 and not re.match(r'^\d+$', candidato):
                        artista = candidato
                        break
        else:
            artista = texto_enlace
            # Buscar álbum en celdas adyacentes
            for adj_idx in [idx_enlace + 1, idx_enlace - 1]:
                if 0 <= adj_idx < len(celdas):
                    candidato = limpiar_texto(celdas[adj_idx].get_text())
                    if len(candidato) > 1 and not re.match(r'^\d+$', candidato):
                        album = candidato
                        break
    
    # Estrategia 2: si no hay enlaces, usar posiciones y características del texto
    if not album or not artista:
        textos_validos = []
        for i, celda in enumerate(celdas):
            texto = limpiar_texto(celda.get_text())
            # Filtrar fechas, números y textos muy cortos
            if (len(texto) > 1 and 
                not re.match(r'^\d+$', texto) and
                not re.search(r'^\d{1,2}/\d{1,2}', texto) and
                not re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)', texto.lower())):
                textos_validos.append(texto)
        
        if len(textos_validos) >= 2:
            # El primero suele ser álbum, el segundo artista
            if not album:
                album = textos_validos[0]
            if not artista:
                artista = textos_validos[1]
        elif len(textos_validos) == 1:
            if not album and not artista:
                # Determinar si es más probable que sea álbum o artista
                texto = textos_validos[0]
                if '"' in texto or "'" in texto or 'the ' in texto.lower():
                    album = texto
                else:
                    artista = texto
    
    return album, artista

def eliminar_duplicados_albums(albums):
    """
    Elimina álbumes duplicados basándose en álbum y artista.
    """
    vistos = set()
    albums_unicos = []
    
    for album in albums:
        clave = (album['álbum'].lower(), album['artista'].lower())
        if clave not in vistos:
            vistos.add(clave)
            albums_unicos.append(album)
    
    return albums_unicos

# GENEROS




def obtener_genero_cancion(titulo, artista, es_album=False):
    """
    Versión mejorada con mejor manejo de errores y rate limiting.
    """
    # Crear clave de cache
    cache_key = f"{artista.lower()}|{titulo.lower()}|{es_album}"
    
    if cache_key in cache_generos:
        return cache_generos[cache_key]
    
    print(f"\n=== Buscando género para: {artista} - {titulo} ===")
    
    genero = None
    
    # Intentar primero con Discogs
    try:
        print("Intentando con Discogs...")
        genero = buscar_genero_discogs(titulo, artista, es_album)
        if genero and genero != 'N/A':
            print(f"✓ Género encontrado en Discogs: {genero}")
            cache_generos[cache_key] = genero
            return genero
        else:
            print("✗ No se encontró género en Discogs")
    except Exception as e:
        print(f"✗ Error consultando Discogs: {e}")
    
    # Pausa adicional entre servicios
    sleep(1)
    
    # Si Discogs no funciona, intentar con MusicBrainz
    try:
        print("Intentando con MusicBrainz...")
        genero = buscar_genero_musicbrainz(titulo, artista, es_album)
        if genero and genero != 'N/A':
            print(f"✓ Género encontrado en MusicBrainz: {genero}")
            cache_generos[cache_key] = genero
            return genero
        else:
            print("✗ No se encontró género en MusicBrainz")
    except Exception as e:
        print(f"✗ Error consultando MusicBrainz: {e}")
    
    # Pausa adicional antes de buscar por artista
    sleep(1)
    
    # Si no encontramos el género de la canción/álbum, buscar por artista
    try:
        print("Intentando buscar género del artista...")
        genero = buscar_genero_artista(artista)
        if genero and genero != 'N/A':
            print(f"✓ Género del artista encontrado: {genero}")
            cache_generos[cache_key] = genero
            return genero
        else:
            print("✗ No se encontró género del artista")
    except Exception as e:
        print(f"✗ Error buscando género del artista: {e}")
    
    # Si todo falla
    print("✗ No se pudo encontrar género")
    cache_generos[cache_key] = 'N/A'
    return 'N/A'

def sleep_rate_limit_discogs():
    """Aplica rate limiting para Discogs"""
    global ultimo_request_discogs
    with lock_discogs:
        tiempo_actual = time_module.time()
        tiempo_transcurrido = tiempo_actual - ultimo_request_discogs
        if tiempo_transcurrido < DISCOGS_REQUEST_DELAY:
            sleep_tiempo = DISCOGS_REQUEST_DELAY - tiempo_transcurrido
            print(f"Rate limiting Discogs: esperando {sleep_tiempo:.1f}s")
            sleep(sleep_tiempo)
        ultimo_request_discogs = time_module.time()

def sleep_rate_limit_musicbrainz():
    """Aplica rate limiting para MusicBrainz"""
    global ultimo_request_musicbrainz
    with lock_musicbrainz:
        tiempo_actual = time_module.time()
        tiempo_transcurrido = tiempo_actual - ultimo_request_musicbrainz
        if tiempo_transcurrido < MUSICBRAINZ_REQUEST_DELAY:
            sleep_tiempo = MUSICBRAINZ_REQUEST_DELAY - tiempo_transcurrido
            sleep(sleep_tiempo)
        ultimo_request_musicbrainz = time_module.time()

def buscar_genero_discogs(titulo, artista, es_album=False):
    """
    Busca género en Discogs con rate limiting mejorado.
    """
    try:
        sleep_rate_limit_discogs()  # Rate limiting ANTES del request
        
        # Preparar la consulta
        query = f"{artista} {titulo}"
        query_encoded = urllib.parse.quote(query)
        
        # Configurar headers
        headers = {
            'User-Agent': 'BillboardScraper/1.0'
        }
        
        if DISCOGS_TOKEN:
            headers['Authorization'] = f'Discogs token={DISCOGS_TOKEN}'
        
        # URL de búsqueda
        tipo = 'release' if es_album else 'master'
        url = f"https://api.discogs.com/database/search?q={query_encoded}&type={tipo}&per_page=5"
        
        print(f"Consultando Discogs: {query}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('results'):
            for resultado in data['results'][:3]:  # Revisar los primeros 3 resultados
                # Verificar que el artista coincida aproximadamente
                if coincide_artista(artista, resultado.get('title', '')):
                    generos = resultado.get('genre', [])
                    if generos:
                        print(f"Género encontrado en Discogs: {generos}")
                        return procesar_generos(generos)
        
        return 'N/A'
        
    except requests.exceptions.RequestException as e:
        if '429' in str(e) or 'rate limit' in str(e).lower():
            print(f"Rate limit en Discogs, esperando 5 segundos...")
            sleep(5)
        print(f"Error en Discogs: {e}")
        return 'N/A'
    except Exception as e:
        print(f"Error general en Discogs: {e}")
        return 'N/A'

def buscar_genero_musicbrainz(titulo, artista, es_album=False):
    """
    Busca género en MusicBrainz con rate limiting mejorado.
    """
    try:
        sleep_rate_limit_musicbrainz()  # Rate limiting ANTES del request
        
        headers = {
            'User-Agent': MUSICBRAINZ_USER_AGENT
        }
        
        # Preparar consulta
        query_parts = []
        if es_album:
            query_parts.append(f'release:"{titulo}"')
        else:
            query_parts.append(f'recording:"{titulo}"')
        
        query_parts.append(f'artist:"{artista}"')
        query = ' AND '.join(query_parts)
        query_encoded = urllib.parse.quote(query)
        
        # URL de búsqueda
        if es_album:
            url = f"https://musicbrainz.org/ws/2/release?query={query_encoded}&fmt=json&limit=5"
        else:
            url = f"https://musicbrainz.org/ws/2/recording?query={query_encoded}&fmt=json&limit=5"
        
        print(f"Consultando MusicBrainz: {titulo} - {artista}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Buscar en los resultados
        resultados_key = 'releases' if es_album else 'recordings'
        if data.get(resultados_key):
            for resultado in data[resultados_key][:3]:
                # Verificar coincidencia de artista
                artistas_mb = []
                if 'artist-credit' in resultado:
                    artistas_mb = [ac.get('name', '') for ac in resultado['artist-credit'] if isinstance(ac, dict)]
                
                if any(coincide_artista(artista, a) for a in artistas_mb):
                    # Obtener detalles adicionales si es necesario
                    generos = extraer_generos_musicbrainz(resultado)
                    if generos:
                        print(f"Género encontrado en MusicBrainz: {generos}")
                        return procesar_generos(generos)
        
        return 'N/A'
        
    except requests.exceptions.RequestException as e:
        if '503' in str(e) or 'rate limit' in str(e).lower():
            print(f"Rate limit en MusicBrainz, esperando 3 segundos...")
            sleep(3)
        print(f"Error en MusicBrainz: {e}")
        return 'N/A'
    except Exception as e:
        print(f"Error general en MusicBrainz: {e}")
        return 'N/A'
def buscar_genero_artista(artista):
    """
    Busca el género principal del artista cuando no se encuentra para la canción específica.
    """
    cache_key = f"artist|{artista.lower()}"
    
    if cache_key in cache_generos:
        return cache_generos[cache_key]
    
    print(f"Buscando género del artista: {artista}")
    
    # Intentar con Discogs primero
    try:
        genero = buscar_artista_discogs(artista)
        if genero and genero != 'N/A':
            cache_generos[cache_key] = genero
            return genero
    except Exception as e:
        print(f"Error buscando artista en Discogs: {e}")
    
    # Intentar con MusicBrainz
    try:
        genero = buscar_artista_musicbrainz(artista)
        if genero and genero != 'N/A':
            cache_generos[cache_key] = genero
            return genero
    except Exception as e:
        print(f"Error buscando artista en MusicBrainz: {e}")
    
    cache_generos[cache_key] = 'N/A'
    return 'N/A'


def buscar_artista_discogs(artista):
    """
    Busca información del artista en Discogs con rate limiting.
    """
    try:
        sleep_rate_limit_discogs()  # Rate limiting ANTES del request
        
        query_encoded = urllib.parse.quote(artista)
        headers = {
            'User-Agent': 'BillboardScraper/1.0'
        }
        
        if DISCOGS_TOKEN:
            headers['Authorization'] = f'Discogs token={DISCOGS_TOKEN}'
        
        url = f"https://api.discogs.com/database/search?q={query_encoded}&type=artist&per_page=3"
        
        print(f"Buscando artista en Discogs: {artista}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('results'):
            for resultado in data['results']:
                if coincide_artista(artista, resultado.get('title', '')):
                    # Obtener detalles del artista
                    if 'id' in resultado:
                        return obtener_detalles_artista_discogs(resultado['id'])
        
        return 'N/A'
        
    except requests.exceptions.RequestException as e:
        if '429' in str(e) or 'rate limit' in str(e).lower():
            print(f"Rate limit buscando artista en Discogs, esperando 5 segundos...")
            sleep(5)
        print(f"Error buscando artista en Discogs: {e}")
        return 'N/A'
    except Exception as e:
        print(f"Error general buscando artista en Discogs: {e}")
        return 'N/A'

def obtener_detalles_artista_discogs(artist_id):
    """
    Obtiene detalles completos del artista desde Discogs con rate limiting.
    """
    try:
        sleep_rate_limit_discogs()  # Rate limiting ANTES del request
        
        headers = {
            'User-Agent': 'BillboardScraper/1.0'
        }
        
        if DISCOGS_TOKEN:
            headers['Authorization'] = f'Discogs token={DISCOGS_TOKEN}'
        
        url = f"https://api.discogs.com/artists/{artist_id}"
        
        print(f"Obteniendo detalles del artista (ID: {artist_id})")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Buscar géneros en el perfil del artista
        generos = []
        if 'profile' in data:
            profile = data['profile'].lower()
            generos_conocidos = [
                'rock', 'pop', 'country', 'jazz', 'blues', 'hip hop', 'rap', 'r&b', 'soul',
                'funk', 'disco', 'electronic', 'house', 'techno', 'reggae', 'folk', 'punk',
                'metal', 'classical', 'gospel', 'bluegrass', 'indie', 'alternative'
            ]
            
            for genero in generos_conocidos:
                if genero in profile:
                    generos.append(genero.title())
        
        if generos:
            print(f"Géneros del artista encontrados: {generos}")
            return procesar_generos(generos)
        
        return 'N/A'
        
    except requests.exceptions.RequestException as e:
        if '429' in str(e) or 'rate limit' in str(e).lower():
            print(f"Rate limit obteniendo detalles en Discogs, esperando 5 segundos...")
            sleep(5)
        print(f"Error obteniendo detalles del artista: {e}")
        return 'N/A'
    except Exception as e:
        print(f"Error general obteniendo detalles del artista: {e}")
        return 'N/A'

def buscar_artista_musicbrainz(artista):
    """
    Busca información del artista en MusicBrainz con rate limiting.
    """
    try:
        sleep_rate_limit_musicbrainz()  # Rate limiting ANTES del request
        
        headers = {
            'User-Agent': MUSICBRAINZ_USER_AGENT
        }
        
        query_encoded = urllib.parse.quote(f'artist:"{artista}"')
        url = f"https://musicbrainz.org/ws/2/artist?query={query_encoded}&fmt=json&limit=3"
        
        print(f"Buscando artista en MusicBrainz: {artista}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('artists'):
            for artista_mb in data['artists']:
                if coincide_artista(artista, artista_mb.get('name', '')):
                    # MusicBrainz usa tags para géneros
                    if 'tags' in artista_mb:
                        tags = [tag['name'] for tag in artista_mb['tags'] if tag.get('count', 0) > 0]
                        if tags:
                            print(f"Tags del artista encontrados: {tags}")
                            return procesar_generos(tags)
        
        return 'N/A'
        
    except requests.exceptions.RequestException as e:
        if '503' in str(e) or 'rate limit' in str(e).lower():
            print(f"Rate limit buscando artista en MusicBrainz, esperando 3 segundos...")
            sleep(3)
        print(f"Error buscando artista en MusicBrainz: {e}")
        return 'N/A'
    except Exception as e:
        print(f"Error general buscando artista en MusicBrainz: {e}")
        return 'N/A'

def coincide_artista(artista_original, artista_resultado):
    """
    Verifica si dos nombres de artista coinciden aproximadamente.
    """
    # Limpiar y normalizar nombres
    def limpiar_nombre(nombre):
        # Remover artículos comunes y limpiar
        nombre = re.sub(r'\bthe\b|\band\b|\&', '', nombre.lower())
        nombre = re.sub(r'[^\w\s]', '', nombre)
        return nombre.strip()
    
    orig_limpio = limpiar_nombre(artista_original)
    result_limpio = limpiar_nombre(artista_resultado)
    
    # Verificar coincidencias
    if orig_limpio == result_limpio:
        return True
    
    # Verificar si uno contiene al otro
    if orig_limpio in result_limpio or result_limpio in orig_limpio:
        return True
    
    # Verificar coincidencia de palabras principales
    palabras_orig = set(orig_limpio.split())
    palabras_result = set(result_limpio.split())
    
    if len(palabras_orig) > 0 and len(palabras_result) > 0:
        coincidencias = len(palabras_orig.intersection(palabras_result))
        total_palabras = min(len(palabras_orig), len(palabras_result))
        
        # Si coincide más del 60% de las palabras
        if coincidencias / total_palabras > 0.6:
            return True
    
    return False

def procesar_generos(generos_raw):
    """
    Procesa y normaliza la lista de géneros obtenida de las APIs.
    """
    if not generos_raw:
        return 'N/A'
    
    # Mapeo de géneros para normalizar
    mapeo_generos = {
        'rock and roll': 'Rock',
        'r&b': 'R&B',
        'rhythm and blues': 'R&B',
        'hip hop': 'Hip Hop',
        'hip-hop': 'Hip Hop',
        'rap': 'Hip Hop',
        'country music': 'Country',
        'pop music': 'Pop',
        'electronic music': 'Electronic',
        'dance music': 'Dance',
        'folk music': 'Folk',
        'classical music': 'Classical',
        'jazz music': 'Jazz',
        'blues music': 'Blues',
        'gospel music': 'Gospel',
        'soul music': 'Soul',
        'funk music': 'Funk',
        'reggae music': 'Reggae',
        'punk rock': 'Punk',
        'heavy metal': 'Metal',
        'hard rock': 'Rock',
        'soft rock': 'Rock',
        'indie rock': 'Indie Rock',
        'alternative rock': 'Alternative'
    }
    
    # Procesar géneros
    generos_procesados = []
    
    for genero in generos_raw:
        if isinstance(genero, str):
            genero_lower = genero.lower().strip()
            
            # Buscar en el mapeo
            genero_normalizado = mapeo_generos.get(genero_lower, genero.title())
            
            # Filtrar géneros demasiado específicos o no musicales
            if len(genero_normalizado) > 2 and genero_normalizado not in generos_procesados:
                generos_procesados.append(genero_normalizado)
    
    if generos_procesados:
        # Devolver los primeros 2 géneros más relevantes
        return ', '.join(generos_procesados[:2])
    
    return 'N/A'

def extraer_generos_musicbrainz(resultado):
    """
    Extrae géneros de un resultado de MusicBrainz.
    """
    generos = []
    
    # Buscar en tags
    if 'tags' in resultado:
        for tag in resultado['tags']:
            if tag.get('count', 0) > 0:
                generos.append(tag['name'])
    
    # Buscar en release-groups si es un recording
    if 'releases' in resultado:
        for release in resultado['releases'][:2]:  # Solo los primeros 2
            if 'tags' in release:
                for tag in release['tags']:
                    if tag.get('count', 0) > 0:
                        generos.append(tag['name'])
    
    return generos

def guardar_csv_billboard_con_genero(datos, archivo, tipo):
    """
    Versión actualizada que incluye la columna de género.
    """
    if not datos:
        print(f"No hay datos para guardar en {archivo}")
        return
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    
    # Determinar los encabezados según el tipo de datos
    if tipo == "yearend":
        encabezados = ['año', 'posición', 'título', 'artista', 'género']
    elif tipo == "hot100":
        encabezados = ['año', 'título', 'artista', 'posición_pico', 'fecha_entrada', 'semanas_chart', 'género']
    elif tipo == "country":
        encabezados = ['año', 'fecha', 'álbum', 'artista', 'semanas_en_1', 'posición', 'género']
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

def procesar_yearend_singles_con_genero(anio):
    """
    Versión que incluye búsqueda de géneros para Year-End singles.
    """
    urls_posibles = []
    
    if anio <= 1957:
        urls_posibles.extend([
            f"https://en.wikipedia.org/wiki/Billboard_year-end_top_30_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/Billboard_year-end_top_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/List_of_Billboard_number-one_singles_of_{anio}"
        ])
    else:
        urls_posibles.extend([
            f"https://en.wikipedia.org/wiki/Billboard_Year-End_Hot_100_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/Billboard_year-end_Hot_100_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/List_of_Billboard_Hot_100_number-one_singles_of_{anio}"
        ])
    
    soup = None
    url_exitosa = None
    
    for url in urls_posibles:
        print(f"Intentando URL: {url}")
        if verificar_url_existe(url):
            soup = descargar_pagina(url)
            if soup:
                url_exitosa = url
                break
        time.sleep(1)
    
    if not soup:
        print(f"No se pudo acceder a ninguna URL válida para el año {anio}")
        return
    
    print(f"Usando URL: {url_exitosa}")
    singles = extraer_yearend_singles(soup, anio)
    

    if singles:
        # Añadir géneros a cada single
        print(f"\n=== Obteniendo géneros para {len(singles)} singles del año {anio} ===")
        total_singles = len(singles)
        
        for i, single in enumerate(singles):
            print(f"\n--- Procesando {i+1}/{total_singles} ---")
            print(f"Canción: {single['título']} - {single['artista']}")
            
            genero = obtener_genero_cancion(single['título'], single['artista'], es_album=False)
            single['género'] = genero
            
            # Pausa progresiva: más larga cada 5 canciones
            if (i + 1) % 5 == 0:
                print(f"Pausa después de {i+1} canciones...")
                sleep(3)
            elif (i + 1) % 10 == 0:
                print(f"Pausa larga después de {i+1} canciones...")
                sleep(5)
            else:
                sleep(1)  # Pausa mínima entre canciones
        
        tipo_archivo = "yearend_top30" if anio <= 1957 else "yearend_hot100"
        archivo = os.path.join(OUTPUT_DIR, "yearend", f"billboard_{tipo_archivo}_{anio}.csv")
        guardar_csv_billboard_con_genero(singles, archivo, "yearend")
    else:
        print(f"No se pudieron extraer datos para el año {anio}")


# Funciones de base de datos

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    if DB_PATH is None:
        raise ValueError("Base de datos no configurada. Ejecuta init_config() primero.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_billboard_charts_tables():
    """Crea las tablas para almacenar los datos de Billboard Charts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla para Billboard Year-End singles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS billboard_yearend_singles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            año INTEGER NOT NULL,
            posición INTEGER,
            título TEXT NOT NULL,
            artista TEXT NOT NULL,
            género TEXT,
            artist_id INTEGER,
            song_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    ''')
    
    # Tabla para Billboard Hot 100 top-ten
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS billboard_hot100_topten (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            año INTEGER NOT NULL,
            título TEXT NOT NULL,
            artista TEXT NOT NULL,
            posición_pico INTEGER,
            fecha_entrada TEXT,
            semanas_chart INTEGER,
            género TEXT,
            artist_id INTEGER,
            song_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    ''')
    
    # Tabla para Billboard Country Albums
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS billboard_country_albums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            año INTEGER NOT NULL,
            fecha TEXT,
            álbum TEXT NOT NULL,
            artista TEXT NOT NULL,
            semanas_en_1 INTEGER,
            posición INTEGER,
            género TEXT,
            artist_id INTEGER,
            album_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (album_id) REFERENCES albums(id)
        )
    ''')
    
    # Índices para mejorar rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_billboard_yearend_artist ON billboard_yearend_singles(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_billboard_yearend_year ON billboard_yearend_singles(año)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_billboard_hot100_artist ON billboard_hot100_topten(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_billboard_hot100_year ON billboard_hot100_topten(año)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_billboard_country_artist ON billboard_country_albums(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_billboard_country_year ON billboard_country_albums(año)')
    
    conn.commit()
    conn.close()
    print("Tablas de Billboard Charts creadas correctamente")

def find_artist_id(artist_name):
    """Busca el artist_id en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Búsqueda exacta primero
    cursor.execute("SELECT id FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name,))
    result = cursor.fetchone()
    
    if result:
        conn.close()
        return result[0]
    
    # Búsqueda por similitud (contiene)
    cursor.execute("SELECT id FROM artists WHERE LOWER(name) LIKE LOWER(?)", (f"%{artist_name}%",))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def find_song_id(title, artist_name):
    """Busca el song_id en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Búsqueda exacta
    cursor.execute("""
        SELECT id FROM songs 
        WHERE LOWER(title) = LOWER(?) AND LOWER(artist) = LOWER(?)
    """, (title, artist_name))
    result = cursor.fetchone()
    
    if result:
        conn.close()
        return result[0]
    
    # Búsqueda por similitud
    cursor.execute("""
        SELECT id FROM songs 
        WHERE LOWER(title) LIKE LOWER(?) AND LOWER(artist) LIKE LOWER(?)
    """, (f"%{title}%", f"%{artist_name}%"))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def find_album_id(album_name, artist_name):
    """Busca el album_id en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Búsqueda exacta
    cursor.execute("""
        SELECT id FROM albums 
        WHERE LOWER(name) = LOWER(?) AND artist_id IN (
            SELECT id FROM artists WHERE LOWER(name) = LOWER(?)
        )
    """, (album_name, artist_name))
    result = cursor.fetchone()
    
    if result:
        conn.close()
        return result[0]
    
    # Búsqueda por similitud
    cursor.execute("""
        SELECT id FROM albums 
        WHERE LOWER(name) LIKE LOWER(?) AND artist_id IN (
            SELECT id FROM artists WHERE LOWER(name) LIKE LOWER(?)
        )
    """, (f"%{album_name}%", f"%{artist_name}%"))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def insert_yearend_singles_to_db(singles_data):
    """Inserta datos de Year-End singles en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for single in singles_data:
        # Buscar IDs relacionados
        artist_id = find_artist_id(single['artista'])
        song_id = find_song_id(single['título'], single['artista'])
        
        # Verificar si ya existe este registro
        cursor.execute("""
            SELECT id FROM billboard_yearend_singles 
            WHERE año = ? AND título = ? AND artista = ?
        """, (single['año'], single['título'], single['artista']))
        
        if not cursor.fetchone():  # Si no existe, insertar
            cursor.execute("""
                INSERT INTO billboard_yearend_singles 
                (año, posición, título, artista, género, artist_id, song_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                single['año'],
                single.get('posición'),
                single['título'],
                single['artista'],
                single.get('género', 'N/A'),
                artist_id,
                song_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} Year-End singles en la base de datos")
    return inserted_count

def insert_hot100_topten_to_db(singles_data):
    """Inserta datos de Hot 100 top-ten en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for single in singles_data:
        # Buscar IDs relacionados
        artist_id = find_artist_id(single['artista'])
        song_id = find_song_id(single['título'], single['artista'])
        
        # Verificar si ya existe este registro
        cursor.execute("""
            SELECT id FROM billboard_hot100_topten 
            WHERE año = ? AND título = ? AND artista = ?
        """, (single['año'], single['título'], single['artista']))
        
        if not cursor.fetchone():  # Si no existe, insertar
            cursor.execute("""
                INSERT INTO billboard_hot100_topten 
                (año, título, artista, posición_pico, fecha_entrada, semanas_chart, género, artist_id, song_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                single['año'],
                single['título'],
                single['artista'],
                single.get('posición_pico'),
                single.get('fecha_entrada'),
                single.get('semanas_chart'),
                single.get('género', 'N/A'),
                artist_id,
                song_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} Hot 100 top-ten singles en la base de datos")
    return inserted_count

def insert_country_albums_to_db(albums_data):
    """Inserta datos de Country Albums en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for album in albums_data:
        # Buscar IDs relacionados
        artist_id = find_artist_id(album['artista'])
        album_id = find_album_id(album['álbum'], album['artista'])
        
        # Verificar si ya existe este registro
        cursor.execute("""
            SELECT id FROM billboard_country_albums 
            WHERE año = ? AND álbum = ? AND artista = ?
        """, (album['año'], album['álbum'], album['artista']))
        
        if not cursor.fetchone():  # Si no existe, insertar
            cursor.execute("""
                INSERT INTO billboard_country_albums 
                (año, fecha, álbum, artista, semanas_en_1, posición, género, artist_id, album_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                album['año'],
                album.get('fecha'),
                album['álbum'],
                album['artista'],
                album.get('semanas_en_1'),
                album.get('posición'),
                album.get('género', 'N/A'),
                artist_id,
                album_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} Country Albums en la base de datos")
    return inserted_count


# Funciones de procesamiento adaptadas para base de datos

def procesar_yearend_singles_db(anio):
    """Procesa Year-End singles y los guarda en BD sin géneros"""
    urls_posibles = []
    
    if anio <= 1957:
        urls_posibles.extend([
            f"https://en.wikipedia.org/wiki/Billboard_year-end_top_30_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/Billboard_year-end_top_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/List_of_Billboard_number-one_singles_of_{anio}"
        ])
    else:
        urls_posibles.extend([
            f"https://en.wikipedia.org/wiki/Billboard_Year-End_Hot_100_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/Billboard_year-end_Hot_100_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/List_of_Billboard_Hot_100_number-one_singles_of_{anio}"
        ])
    
    soup = None
    url_exitosa = None
    
    for url in urls_posibles:
        print(f"Intentando URL: {url}")
        if verificar_url_existe(url):
            soup = descargar_pagina(url)
            if soup:
                url_exitosa = url
                break
        time.sleep(1)
    
    if not soup:
        print(f"No se pudo acceder a ninguna URL válida para el año {anio}")
        return
    
    print(f"Usando URL: {url_exitosa}")
    singles = extraer_yearend_singles(soup, anio)
    
    if singles:
        # Guardar en base de datos
        insert_yearend_singles_to_db(singles)
        
        # Mantener funcionalidad CSV como respaldo
        tipo_archivo = "yearend_top30" if anio <= 1957 else "yearend_hot100"
        archivo = os.path.join(OUTPUT_DIR, "yearend", f"billboard_{tipo_archivo}_{anio}.csv")
        guardar_csv_billboard(singles, archivo, "yearend")

def procesar_yearend_singles_con_genero_db(anio):
    """Procesa Year-End singles con géneros y los guarda en BD"""
    # Código igual que procesar_yearend_singles_con_genero pero llamando a insert_yearend_singles_to_db
    urls_posibles = []
    
    if anio <= 1957:
        urls_posibles.extend([
            f"https://en.wikipedia.org/wiki/Billboard_year-end_top_30_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/Billboard_year-end_top_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/List_of_Billboard_number-one_singles_of_{anio}"
        ])
    else:
        urls_posibles.extend([
            f"https://en.wikipedia.org/wiki/Billboard_Year-End_Hot_100_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/Billboard_year-end_Hot_100_singles_of_{anio}",
            f"https://en.wikipedia.org/wiki/List_of_Billboard_Hot_100_number-one_singles_of_{anio}"
        ])
    
    soup = None
    url_exitosa = None
    
    for url in urls_posibles:
        print(f"Intentando URL: {url}")
        if verificar_url_existe(url):
            soup = descargar_pagina(url)
            if soup:
                url_exitosa = url
                break
        time.sleep(1)
    
    if not soup:
        print(f"No se pudo acceder a ninguna URL válida para el año {anio}")
        return
    
    print(f"Usando URL: {url_exitosa}")
    singles = extraer_yearend_singles(soup, anio)
    
    if singles:
        # Añadir géneros a cada single
        print(f"\n=== Obteniendo géneros para {len(singles)} singles del año {anio} ===")
        total_singles = len(singles)
        
        for i, single in enumerate(singles):
            print(f"\n--- Procesando {i+1}/{total_singles} ---")
            print(f"Canción: {single['título']} - {single['artista']}")
            
            genero = obtener_genero_cancion(single['título'], single['artista'], es_album=False)
            single['género'] = genero
            
            # Pausa progresiva: más larga cada 5 canciones
            if (i + 1) % 5 == 0:
                print(f"Pausa después de {i+1} canciones...")
                sleep(3)
            elif (i + 1) % 10 == 0:
                print(f"Pausa larga después de {i+1} canciones...")
                sleep(5)
            else:
                sleep(1)  # Pausa mínima entre canciones
        
        # Guardar en base de datos
        insert_yearend_singles_to_db(singles)
        
        # Mantener funcionalidad CSV como respaldo
        tipo_archivo = "yearend_top30" if anio <= 1957 else "yearend_hot100"
        archivo = os.path.join(OUTPUT_DIR, "yearend", f"billboard_{tipo_archivo}_{anio}.csv")
        guardar_csv_billboard_con_genero(singles, archivo, "yearend")


def main(config=None):
    """Función principal del script con soporte para géneros y base de datos"""
    # Inicializar configuración si se proporciona
    if config:
        init_config(config)
        print(f"Usando base de datos: {DB_PATH}")
    
    args = configurar_argumentos()
    
    # Crear tablas de base de datos
    create_billboard_charts_tables()
    
    # Crear directorios de salida (mantenidos para respaldo CSV)
    os.makedirs(os.path.join(OUTPUT_DIR, "yearend"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "hot100"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "country"), exist_ok=True)
    
    # Determinar si usar funciones con géneros o sin géneros
    usar_generos = args.generos
    
    if args.all:
        # Extraer todos los datos disponibles
        if usar_generos:
            print("Extrayendo todos los datos de Billboard disponibles CON información de géneros...")
        else:
            print("Extrayendo todos los datos de Billboard disponibles SIN información de géneros...")
        
        # Year-End singles (1950-2024)
        for anio in range(1950, 2025):
            if usar_generos:
                procesar_yearend_singles_con_genero_db(anio)
            else:
                procesar_yearend_singles_db(anio)
            time.sleep(2)  # Pausa más larga para APIs externas
        
        # Aquí puedes añadir hot100 y country cuando crees las funciones correspondientes
        
    else:
        # Extraer datos específicos según los argumentos
        if args.type and args.year:
            if args.type == "yearend":
                if usar_generos:
                    procesar_yearend_singles_con_genero_db(args.year)
                else:
                    procesar_yearend_singles_db(args.year)
            elif args.type == "hot100":
                # Crear función similar para hot100
                print("Hot100 aún no implementado para base de datos")
            elif args.type == "country":
                # Crear función similar para country
                print("Country aún no implementado para base de datos")
        else:
            print("Debe especificar tanto --type como --year, o usar --all")
            print("Use --help para obtener ayuda.")
if __name__ == "__main__":
    main()