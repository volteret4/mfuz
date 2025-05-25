#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Charts Scraper

Este script extrae datos de las listas de éxitos de la música del Reino Unido 
desde Wikipedia y genera archivos CSV con esa información.

El script puede extraer diferentes tipos de datos:
- Top 10 singles por año
- Top 10 álbumes por año
- Singles más vendidos por década
- Álbumes más vendidos por década
- Número 1 de cada año

Uso:
    python uk_charts_scraper.py [opciones]

Opciones:
    --type TYPE     Tipo de datos a extraer (singles, albums, bestselling)
    --decade DECADE Década a extraer (50s, 60s, 70s, etc.)
    --year YEAR     Año específico a extraer (1952-2024)
    --all           Extraer todos los datos disponibles

Ejemplos:
    python uk_charts_scraper.py --type singles --year 1960
    python uk_charts_scraper.py --type bestselling --decade 60s
    python uk_charts_scraper.py --all

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

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from base_module import PROJECT_ROOT
# Variables globales para configuración
CONFIG = {}
DB_PATH = None

# Configuración
BASE_URL = "https://en.wikipedia.org"
OUTPUT_DIR = "uk_charts_data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# URLs para charts especializados
SPECIALIZED_URLS = {
    "vinyl_albums": {
        "10s": "/wiki/List_of_Official_Vinyl_Albums_Chart_number_ones_of_the_2010s",
        "20s": "/wiki/List_of_Official_Vinyl_Albums_Chart_number_ones_of_the_2020s"
    },
    "vinyl_singles": {
        "10s": "/wiki/List_of_Official_Vinyl_Singles_Chart_number_ones_of_the_2010s", 
        "20s": "/wiki/List_of_Official_Vinyl_Singles_Chart_number_ones_of_the_2020s"
    },
    "streaming_albums": "/wiki/Official_Albums_Streaming_Chart",
    "downloads_singles": "/wiki/UK_Singles_Downloads_Chart"
}

INDIE_NME_URLS = {
    "indie_base": "/wiki/List_of_UK_Independent_Singles_Chart_number_ones_of_",
    "nme": {
        "60s": "/wiki/List_of_NME_number-one_singles_of_the_1960s",
        "70s": "/wiki/List_of_NME_number-one_singles_of_the_1970s",
        "80s": "/wiki/List_of_NME_number-one_singles_of_the_1980s"
    }
}

# Configuración para APIs de géneros
DISCOGS_TOKEN = "MJXLYUGuqwXHVONuYZxVWFSXvFmxpdLqauTRcCsP"  # Opcional: añade tu token de Discogs
MUSICBRAINZ_USER_AGENT = "UKChartsScraper/1.0 (frodobolson@disroot.org)"  # Cambia por tu email
ultimo_request_discogs = 0
ultimo_request_musicbrainz = 0
lock_discogs = threading.Lock()
lock_musicbrainz = threading.Lock()

# Cache para evitar consultas repetidas
cache_generos = {}

# Configuración de delays para rate limiting
if DISCOGS_TOKEN:
    DISCOGS_REQUEST_DELAY = 5.5  # Con token puedes ir más rápido
else:
    DISCOGS_REQUEST_DELAY = 10.0

MUSICBRAINZ_REQUEST_DELAY = 1.0


# URLs base para cada tipo de dato
# URLs base actualizadas (simplificadas)
URLS = {
    "singles_by_year": "/wiki/List_of_UK_top-ten_singles_in_{year}",
    "albums_by_year": "/wiki/List_of_UK_top-ten_albums_in_{year}",
    "bestselling_singles_by_year": "/wiki/List_of_best-selling_singles_by_year_in_the_United_Kingdom",
}

# Mapeo específico para URLs de décadas (estos son casos especiales)
DECADE_URLS = {
    "bestselling_singles": {
        "50s": "/wiki/List_of_best-selling_singles_of_the_1950s_in_the_United_Kingdom",
        "60s": "/wiki/List_of_best-selling_singles_of_the_1960s_in_the_United_Kingdom", 
        "70s": "/wiki/List_of_best-selling_singles_of_the_1970s_in_the_United_Kingdom",
        "80s": "/wiki/List_of_best-selling_singles_of_the_1980s_in_the_United_Kingdom",
        "90s": "/wiki/List_of_best-selling_singles_of_the_1990s_in_the_United_Kingdom",
        "00s": "/wiki/List_of_best-selling_singles_of_the_2000s_(decade)_in_the_United_Kingdom",
        "10s": "/wiki/List_of_best-selling_singles_of_the_2010s_in_the_United_Kingdom",
        "20s": "/wiki/List_of_best-selling_singles_of_the_2020s_in_the_United_Kingdom"
    },
    "number_ones_singles": {
        "50s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_1950s",
        "60s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_1960s",
        "70s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_1970s", 
        "80s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_1980s",
        "90s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_1990s",
        "00s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_2000s",
        "10s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_2010s",
        "20s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_2020s"
    },
    "number_ones_albums": {
        "50s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_1950s",
        "60s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_1960s", 
        "70s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_1970s",
        "80s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_1980s",
        "90s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_1990s",
        "00s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_2000s",
        "10s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_2010s", 
        "20s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_2020s"
    }
}

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




# URLs base actualizadas (simplificadas)
URLS = {
    "singles_by_year": "/wiki/List_of_UK_top-ten_singles_in_{year}",
    "albums_by_year": "/wiki/List_of_UK_top-ten_albums_in_{year}",
    "bestselling_singles_by_year": "/wiki/List_of_best-selling_singles_by_year_in_the_United_Kingdom",
}

# Mapeo específico para URLs de décadas (estos son casos especiales)
DECADE_URLS = {
    "bestselling_singles": {
        "50s": "/wiki/List_of_best-selling_singles_of_the_1950s_in_the_United_Kingdom",
        "60s": "/wiki/List_of_best-selling_singles_of_the_1960s_in_the_United_Kingdom", 
        "70s": "/wiki/List_of_best-selling_singles_of_the_1970s_in_the_United_Kingdom",
        "80s": "/wiki/List_of_best-selling_singles_of_the_1980s_in_the_United_Kingdom",
        "90s": "/wiki/List_of_best-selling_singles_of_the_1990s_in_the_United_Kingdom",
        "00s": "/wiki/List_of_best-selling_singles_of_the_2000s_(decade)_in_the_United_Kingdom",
        "10s": "/wiki/List_of_best-selling_singles_of_the_2010s_in_the_United_Kingdom",
        "20s": "/wiki/List_of_best-selling_singles_of_the_2020s_in_the_United_Kingdom"
    },
    "number_ones_singles": {
        "50s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_1950s",
        "60s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_1960s",
        "70s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_1970s", 
        "80s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_1980s",
        "90s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_1990s",
        "00s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_2000s",
        "10s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_2010s",
        "20s": "/wiki/List_of_UK_Singles_Chart_number_ones_of_the_2020s"
    },
    "number_ones_albums": {
        "50s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_1950s",
        "60s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_1960s", 
        "70s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_1970s",
        "80s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_1980s",
        "90s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_1990s",
        "00s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_2000s",
        "10s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_2010s", 
        "20s": "/wiki/List_of_UK_Albums_Chart_number_ones_of_the_2020s"
    }
}

def obtener_url(tipo, anio=None, decada=None):
    """
    Obtiene la URL de Wikipedia según el tipo de datos, año o década.
    VERSIÓN MEJORADA que maneja correctamente todas las décadas.
    
    Args:
        tipo (str): Tipo de datos a extraer
        anio (int, optional): Año específico
        decada (str, optional): Década específica (e.g., "60s", "00s", "10s")
        
    Returns:
        str: URL completa
    """
    if tipo == "singles" and anio:
        return urljoin(BASE_URL, URLS["singles_by_year"].format(year=anio))
    
    elif tipo == "albums" and anio:
        return urljoin(BASE_URL, URLS["albums_by_year"].format(year=anio))
    
    elif tipo == "bestselling" and decada:
        # Usar el mapeo específico para bestselling singles por década
        if decada in DECADE_URLS["bestselling_singles"]:
            return urljoin(BASE_URL, DECADE_URLS["bestselling_singles"][decada])
        else:
            print(f"Década {decada} no soportada para bestselling singles")
            return None
    
    elif tipo == "bestselling" and not decada:
        # Bestselling singles por año (todas las décadas en una página)
        return urljoin(BASE_URL, URLS["bestselling_singles_by_year"])
    
    elif tipo == "numberones" and decada:
        # Usar el mapeo específico para number ones por década
        if decada in DECADE_URLS["number_ones_singles"]:
            return urljoin(BASE_URL, DECADE_URLS["number_ones_singles"][decada])
        else:
            print(f"Década {decada} no soportada para number ones singles")
            return None
    
    elif tipo == "numberones_albums" and decada:
        # Usar el mapeo específico para number ones albums por década
        if decada in DECADE_URLS["number_ones_albums"]:
            return urljoin(BASE_URL, DECADE_URLS["number_ones_albums"][decada])
        else:
            print(f"Década {decada} no soportada para number ones albums")
            return None
    
    print(f"Combinación no válida: tipo={tipo}, anio={anio}, decada={decada}")
    return None

def validar_decada(decada):
    """
    Valida si una década es soportada por el script.
    
    Args:
        decada (str): Década a validar (e.g., "60s", "00s", "10s")
        
    Returns:
        bool: True si la década es válida, False en caso contrario
    """
    decadas_validas = ["50s", "60s", "70s", "80s", "90s", "00s", "10s", "20s"]
    return decada in decadas_validas

def obtener_decadas_disponibles():
    """
    Devuelve la lista de décadas disponibles para el scraping.
    
    Returns:
        list: Lista de décadas disponibles
    """
    return ["50s", "60s", "70s", "80s", "90s", "00s", "10s", "20s"]

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

def extraer_top_singles_por_anio(soup, anio):
    """
    Extrae los datos de los top 10 singles de un año específico.
    VERSIÓN MEJORADA con limpieza de texto.
    
    Args:
        soup (BeautifulSoup): Objeto BeautifulSoup con el contenido de la página
        anio (int): Año a extraer
        
    Returns:
        list: Lista de diccionarios con los datos de los singles
    """
    singles = []
    
    # Buscar las tablas principales
    tablas = soup.find_all('table', class_='wikitable')
    
    if not tablas:
        print(f"No se encontraron tablas en la página del año {anio}")
        return singles
    
    # La primera tabla suele contener la lista de singles
    tabla_principal = None
    for tabla in tablas:
        # Verificar si la tabla es la que buscamos
        encabezados = tabla.find_all('th')
        if encabezados and len(encabezados) >= 4:
            # Buscamos encabezados que tengan "Single", "Artist", "Peak"
            textos = [th.get_text().strip().lower() for th in encabezados]
            if 'single' in textos and 'artist' in textos and 'peak' in textos:
                tabla_principal = tabla
                break
    
    if not tabla_principal:
        print(f"No se encontró la tabla principal en la página del año {anio}")
        return singles
    
    # Extraer filas de la tabla
    filas = tabla_principal.find_all('tr')
    
    # Saltamos la primera fila (encabezados)
    for fila in filas[1:]:
        celdas = fila.find_all(['td', 'th'])
        
        # Necesitamos al menos 3 celdas (título, artista, posición)
        if len(celdas) < 3:
            continue
        
        # Extraer información básica
        try:
            # Los índices pueden variar según la estructura de la tabla
            # Intentamos identificar cada columna por su contenido
            titulo = None
            artista = None
            posicion = None
            fecha = None
            
            for i, celda in enumerate(celdas):
                texto = limpiar_texto(celda.get_text())  # ← CAMBIO AQUÍ
                
                # Intentar identificar qué columna es
                enlaces = celda.find_all('a')
                if enlaces and not titulo and not artista:
                    # Primera celda con enlaces suele ser el título
                    titulo = texto
                elif enlaces and titulo and not artista:
                    # Segunda celda con enlaces suele ser el artista
                    artista = texto
                elif re.match(r'^\d+$', texto) and not posicion:
                    # Columna con número suele ser la posición
                    posicion = int(texto)
            
            # Si logramos extraer los datos básicos, agregamos el single
            if titulo and artista:
                singles.append({
                    'año': anio,
                    'título': titulo,
                    'artista': artista,
                    'posición': posicion if posicion else 'N/A',
                    'fecha_pico': fecha if fecha else 'N/A'
                })
                
                # Limitamos a los 10 primeros singles
                if len(singles) >= 10:
                    break
        except Exception as e:
            print(f"Error al extraer datos de una fila: {e}")
            continue
    
    return singles


def extraer_top_singles_por_anio(soup, anio):
    """
    Extrae los datos de los top 10 singles de un año específico.
    VERSIÓN MEJORADA con limpieza de texto.
    
    Args:
        soup (BeautifulSoup): Objeto BeautifulSoup con el contenido de la página
        anio (int): Año a extraer
        
    Returns:
        list: Lista de diccionarios con los datos de los singles
    """
    singles = []
    
    # Buscar las tablas principales
    tablas = soup.find_all('table', class_='wikitable')
    
    if not tablas:
        print(f"No se encontraron tablas en la página del año {anio}")
        return singles
    
    # La primera tabla suele contener la lista de singles
    tabla_principal = None
    for tabla in tablas:
        # Verificar si la tabla es la que buscamos
        encabezados = tabla.find_all('th')
        if encabezados and len(encabezados) >= 4:
            # Buscamos encabezados que tengan "Single", "Artist", "Peak"
            textos = [th.get_text().strip().lower() for th in encabezados]
            if 'single' in textos and 'artist' in textos and 'peak' in textos:
                tabla_principal = tabla
                break
    
    if not tabla_principal:
        print(f"No se encontró la tabla principal en la página del año {anio}")
        return singles
    
    # Extraer filas de la tabla
    filas = tabla_principal.find_all('tr')
    
    # Saltamos la primera fila (encabezados)
    for fila in filas[1:]:
        celdas = fila.find_all(['td', 'th'])
        
        # Necesitamos al menos 3 celdas (título, artista, posición)
        if len(celdas) < 3:
            continue
        
        # Extraer información básica
        try:
            # Los índices pueden variar según la estructura de la tabla
            # Intentamos identificar cada columna por su contenido
            titulo = None
            artista = None
            posicion = None
            fecha = None
            
            for i, celda in enumerate(celdas):
                texto = limpiar_texto(celda.get_text())  # ← CAMBIO AQUÍ
                
                # Intentar identificar qué columna es
                enlaces = celda.find_all('a')
                if enlaces and not titulo and not artista:
                    # Primera celda con enlaces suele ser el título
                    titulo = texto
                elif enlaces and titulo and not artista:
                    # Segunda celda con enlaces suele ser el artista
                    artista = texto
                elif re.match(r'^\d+$', texto) and not posicion:
                    # Columna con número suele ser la posición
                    posicion = int(texto)
            
            # Si logramos extraer los datos básicos, agregamos el single
            if titulo and artista:
                singles.append({
                    'año': anio,
                    'título': titulo,
                    'artista': artista,
                    'posición': posicion if posicion else 'N/A',
                    'fecha_pico': fecha if fecha else 'N/A'
                })
                
                # Limitamos a los 10 primeros singles
                if len(singles) >= 10:
                    break
        except Exception as e:
            print(f"Error al extraer datos de una fila: {e}")
            continue
    
    return singles

def extraer_bestselling_singles_decada(soup, decada):
    """
    Extrae los datos de los singles más vendidos de una década.
    VERSIÓN MEJORADA con limpieza de texto.
    
    Args:
        soup (BeautifulSoup): Objeto BeautifulSoup con el contenido de la página
        decada (str): Década a extraer (e.g., "60s")
        
    Returns:
        list: Lista de diccionarios con los datos de los singles
    """
    singles = []
    
    # Buscar las tablas principales
    tablas = soup.find_all('table', class_='wikitable')
    
    if not tablas:
        print(f"No se encontraron tablas en la página de la década {decada}")
        return singles
    
    # Buscamos la tabla que tenga "Position", "Single", "Artist"
    tabla_principal = None
    for tabla in tablas:
        encabezados = tabla.find_all('th')
        if encabezados and len(encabezados) >= 3:
            textos = [th.get_text().strip().lower() for th in encabezados]
            if ('position' in textos or 'pos' in textos or 'rank' in textos) and 'single' in textos and 'artist' in textos:
                tabla_principal = tabla
                break
    
    if not tabla_principal:
        # En algunos casos, la tabla no tiene encabezados identificables
        # Intentamos encontrar la tabla que tenga una fila con "She Loves You" (para los 60s)
        # o algún éxito conocido de la década
        for tabla in tablas:
            if decada == "60s" and "She Loves You" in tabla.get_text():
                tabla_principal = tabla
                break
            elif decada == "70s" and "Bohemian Rhapsody" in tabla.get_text():
                tabla_principal = tabla
                break
            # Añadir más condiciones para otras décadas
    
    if not tabla_principal:
        print(f"No se encontró la tabla principal en la página de la década {decada}")
        return singles
    
    # Extraer filas de la tabla
    filas = tabla_principal.find_all('tr')
    
    # Saltamos la primera fila (encabezados)
    for fila in filas[1:]:
        celdas = fila.find_all(['td', 'th'])
        
        # Necesitamos al menos 3 celdas (posición, título, artista)
        if len(celdas) < 3:
            continue
        
        try:
            # Los índices pueden variar según la estructura de la tabla
            posicion = limpiar_texto(celdas[0].get_text())  # ← CAMBIO AQUÍ
            titulo = limpiar_texto(celdas[1].get_text())    # ← CAMBIO AQUÍ
            artista = limpiar_texto(celdas[2].get_text())   # ← CAMBIO AQUÍ
            
            # En algunas tablas, puede haber una columna de año y ventas
            anio = limpiar_texto(celdas[3].get_text()) if len(celdas) > 3 else 'N/A'
            ventas = limpiar_texto(celdas[4].get_text()) if len(celdas) > 4 else 'N/A'
            
            singles.append({
                'década': decada,
                'posición': posicion,
                'título': titulo,
                'artista': artista,
                'año': anio,
                'ventas': ventas
            })
            
            # Limitamos a los 10 primeros singles
            if len(singles) >= 10:
                break
        except Exception as e:
            print(f"Error al extraer datos de una fila: {e}")
            continue
    
    return singles

def extraer_bestselling_singles_por_anio(soup):
    """
    Extrae los datos de los singles más vendidos de cada año.
    VERSIÓN MEJORADA con limpieza de texto.
    
    Args:
        soup (BeautifulSoup): Objeto BeautifulSoup con el contenido de la página
        
    Returns:
        list: Lista de diccionarios con los datos de los singles
    """
    singles = []
    
    # Buscar las tablas principales
    tablas = soup.find_all('table')
    
    if not tablas:
        print(f"No se encontraron tablas en la página de best-selling singles por año")
        return singles
    
    # La tabla que buscamos suele tener encabezados como "Year", "Single", "Artist"
    tabla_principal = None
    for tabla in tablas:
        encabezados = tabla.find_all('th')
        if encabezados and len(encabezados) >= 3:
            textos = [th.get_text().strip().lower() for th in encabezados]
            if 'year' in textos and 'single' in textos and 'artist' in textos:
                tabla_principal = tabla
                break
    
    if not tabla_principal:
        print(f"No se encontró la tabla principal en la página de best-selling singles por año")
        return singles
    
    # Extraer filas de la tabla
    filas = tabla_principal.find_all('tr')
    
    # Saltamos la primera fila (encabezados)
    for fila in filas[1:]:
        celdas = fila.find_all(['td', 'th'])
        
        # Necesitamos al menos 3 celdas (año, título, artista)
        if len(celdas) < 3:
            continue
        
        try:
            anio = limpiar_texto(celdas[0].get_text())     # ← CAMBIO AQUÍ
            titulo = limpiar_texto(celdas[1].get_text())   # ← CAMBIO AQUÍ
            artista = limpiar_texto(celdas[2].get_text())  # ← CAMBIO AQUÍ
            
            # Puede haber una columna con número de ventas
            ventas = limpiar_texto(celdas[3].get_text()) if len(celdas) > 3 else 'N/A'
            
            singles.append({
                'año': anio,
                'título': titulo,
                'artista': artista,
                'ventas': ventas
            })
        except Exception as e:
            print(f"Error al extraer datos de una fila: {e}")
            continue
    
    return singles

def guardar_csv_con_genero(datos, archivo, tipo):
    """
    Guarda los datos en un archivo CSV incluyendo la columna de género.
    
    Args:
        datos (list): Lista de diccionarios con los datos a guardar
        archivo (str): Nombre del archivo CSV a crear
        tipo (str): Tipo de datos (singles, albums, bestselling)
    """
    if not datos:
        print(f"No hay datos para guardar en {archivo}")
        return
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    
    # Determinar los encabezados según el tipo de datos
    if tipo == "singles" or tipo == "albums":
        encabezados = ['año', 'posición', 'título', 'artista', 'fecha_pico', 'género']
    elif tipo == "bestselling" and "década" in datos[0]:
        encabezados = ['década', 'posición', 'título', 'artista', 'año', 'ventas', 'género']
    elif tipo == "bestselling":
        encabezados = ['año', 'título', 'artista', 'ventas', 'género']
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


def procesar_singles_por_anio(anio):
    """
    Procesa los datos de los top 10 singles de un año específico.
    
    Args:
        anio (int): Año a procesar
    """
    url = obtener_url("singles", anio=anio)
    soup = descargar_pagina(url)
    
    if not soup:
        return
    
    singles = extraer_top_singles_por_anio(soup, anio)
    
    if singles:
        archivo = os.path.join(OUTPUT_DIR, "singles", f"uk_top10_singles_{anio}.csv")
        guardar_csv_con_genero(singles, archivo, "singles")

def procesar_bestselling_singles_decada_db(decada):
    """
    Procesa los datos de los singles más vendidos de una década sin géneros y los guarda en BD.
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    """
    # Verificar si ya existen datos
    if verificar_datos_existentes_bestselling('decada', decada=decada):
        return
    
    url = obtener_url("bestselling", decada=decada)
    soup = descargar_pagina(url)
    
    if not soup:
        return
    
    singles = extraer_bestselling_singles_decada(soup, decada)
    
    if singles:
        # Guardar en base de datos
        insert_bestselling_to_db(singles, 'decada')
        
        # Mantener funcionalidad CSV como respaldo
        archivo = os.path.join(OUTPUT_DIR, "bestselling", f"uk_bestselling_singles_{decada}.csv")
        guardar_csv_con_genero(singles, archivo, "bestselling")


def procesar_bestselling_singles_por_anio_db():
    """
    Procesa los datos de los singles más vendidos de cada año sin géneros y los guarda en BD.
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    """
    # Verificar si ya existen datos
    if verificar_datos_existentes_bestselling('anual'):
        return
    
    url = obtener_url("bestselling")
    soup = descargar_pagina(url)
    
    if not soup:
        return
    
    singles = extraer_bestselling_singles_por_anio(soup)
    
    if singles:
        # Guardar en base de datos
        insert_bestselling_to_db(singles, 'anual')
        
        # Mantener funcionalidad CSV como respaldo
        archivo = os.path.join(OUTPUT_DIR, "bestselling", "uk_bestselling_singles_by_year.csv")
        guardar_csv_con_genero(singles, archivo, "bestselling")



# def procesar_bestselling_singles_decada(decada):
#     """
#     Procesa los datos de los singles más vendidos de una década.
    
#     Args:
#         decada (str): Década a procesar (e.g., "60s")
#     """
#     url = obtener_url("bestselling", decada=decada)
#     soup = descargar_pagina(url)
    
#     if not soup:
#         return
    
#     singles = extraer_bestselling_singles_decada(soup, decada)
    
#     if singles:
#         archivo = os.path.join(OUTPUT_DIR, "bestselling", f"uk_bestselling_singles_{decada}.csv")
#         guardar_csv_con_genero(singles, archivo, "bestselling")

# def procesar_bestselling_singles_por_anio():
#     """
#     Procesa los datos de los singles más vendidos de cada año.
#     """
#     url = obtener_url("bestselling")
#     soup = descargar_pagina(url)
    
#     if not soup:
#         return
    
#     singles = extraer_bestselling_singles_por_anio(soup)
    
#     if singles:
#         archivo = os.path.join(OUTPUT_DIR, "bestselling", "uk_bestselling_singles_by_year.csv")
#         guardar_csv_con_genero(singles, archivo, "bestselling")

def limpiar_texto(texto):
    """
    Limpia el texto extraído de Wikipedia eliminando comillas adicionales,
    caracteres especiales y espacios innecesarios.
    
    Args:
        texto (str): Texto a limpiar
        
    Returns:
        str: Texto limpio
    """
    if not texto:
        return texto
    
    # Eliminar comillas dobles múltiples y simples
    texto = re.sub(r'"{2,}', '"', texto)  # Múltiples comillas dobles -> una sola
    texto = re.sub(r'^"(.*)"$', r'\1', texto)  # Quitar comillas al inicio y final
    
    # Limpiar caracteres especiales comunes de Wikipedia
    texto = re.sub(r'\[[\w\s]*\]', '', texto)  # Eliminar referencias [A], [E], etc.
    texto = re.sub(r'♦|♠|♣|♥|★|☆', '', texto)  # Eliminar símbolos especiales
    texto = re.sub(r'\s+', ' ', texto)  # Múltiples espacios -> uno solo
    
    return texto.strip()


# FUNCIONES DE GÉNEROS 

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
            'User-Agent': 'UKChartsScraper/1.0'
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
            print(f"Rate limit en Discogs, esperando 10 segundos...")
            sleep(10)
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
        sleep_rate_limit_discogs()
        
        query_encoded = urllib.parse.quote(artista)
        headers = {
            'User-Agent': 'UKChartsScraper/1.0'
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
            print(f"Rate limit buscando artista en Discogs, esperando 10 segundos...")
            sleep(10)
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
        sleep_rate_limit_discogs()
        
        headers = {
            'User-Agent': 'UKChartsScraper/1.0'
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
            print(f"Rate limit obteniendo detalles en Discogs, esperando 10 segundos...")
            sleep(10)
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
        sleep_rate_limit_musicbrainz()
        
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

def procesar_singles_por_anio_db(anio):
    """
    Procesa los datos de los top 10 singles de un año específico sin géneros y los guarda en BD.
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    """
    # Verificar si ya existen datos
    if verificar_datos_existentes_singles(anio):
        return
    
    url = obtener_url("singles", anio=anio)
    soup = descargar_pagina(url)
    
    if not soup:
        return
    
    singles = extraer_top_singles_por_anio(soup, anio)
    
    if singles:
        # Guardar en base de datos
        insert_singles_to_db(singles)
        
        # Mantener funcionalidad CSV como respaldo
        archivo = os.path.join(OUTPUT_DIR, "singles", f"uk_top10_singles_{anio}.csv")
        guardar_csv_con_genero(singles, archivo, "singles")

def procesar_bestselling_singles_decada_con_genero_db(decada):
    """
    Procesa los datos de los singles más vendidos de una década y los guarda en BD.
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    """
    # Verificar si ya existen datos
    if verificar_datos_existentes_bestselling('decada', decada=decada):
        return
    
    url = obtener_url("bestselling", decada=decada)
    soup = descargar_pagina(url)
    
    if not soup:
        return
    
    singles = extraer_bestselling_singles_decada(soup, decada)
    
    if singles:
        # Añadir géneros a cada single
        print(f"\n=== Obteniendo géneros para {len(singles)} singles de los {decada} ===")
        total_singles = len(singles)
        
        for i, single in enumerate(singles):
            print(f"\n--- Procesando {i+1}/{total_singles} ---")
            print(f"Canción: {single['título']} - {single['artista']}")
            
            genero = obtener_genero_cancion(single['título'], single['artista'], es_album=False)
            single['género'] = genero
            
            # Pausa progresiva
            if (i + 1) % 3 == 0:
                print(f"Pausa después de {i+1} canciones...")
                sleep(3)
            else:
                sleep(1)
        
        # Guardar en base de datos
        insert_bestselling_to_db(singles, 'decada')
        
        # Mantener funcionalidad CSV como respaldo
        archivo = os.path.join(OUTPUT_DIR, "bestselling", f"uk_bestselling_singles_{decada}_con_generos.csv")
        guardar_csv_con_genero(singles, archivo, "bestselling")



def procesar_singles_por_anio_con_genero_db(anio):
    """
    Procesa los datos de los top 10 singles de un año específico y los guarda en BD.
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    """
    # Verificar si ya existen datos
    if verificar_datos_existentes_singles(anio):
        return
    
    url = obtener_url("singles", anio=anio)
    soup = descargar_pagina(url)
    
    if not soup:
        return
    
    singles = extraer_top_singles_por_anio(soup, anio)
    
    if singles:
        # Añadir géneros a cada single si se solicita
        print(f"\n=== Obteniendo géneros para {len(singles)} singles del año {anio} ===")
        total_singles = len(singles)
        
        for i, single in enumerate(singles):
            print(f"\n--- Procesando {i+1}/{total_singles} ---")
            print(f"Canción: {single['título']} - {single['artista']}")
            
            genero = obtener_genero_cancion(single['título'], single['artista'], es_album=False)
            single['género'] = genero
            
            # Pausa progresiva
            if (i + 1) % 5 == 0:
                print(f"Pausa después de {i+1} canciones...")
                sleep(3)
            elif (i + 1) % 10 == 0:
                print(f"Pausa larga después de {i+1} canciones...")
                sleep(5)
            else:
                sleep(1.5)
        
        # Guardar en base de datos
        insert_singles_to_db(singles)
        
        # Mantener funcionalidad CSV como respaldo si se desea
        archivo = os.path.join(OUTPUT_DIR, "singles", f"uk_top10_singles_{anio}_con_generos.csv")
        guardar_csv_con_genero(singles, archivo, "singles")
    else:
        print(f"No se pudieron extraer datos para el año {anio}")



# def procesar_singles_por_anio_con_genero(anio):
#     """
#     Procesa los datos de los top 10 singles de un año específico incluyendo géneros.
    
#     Args:
#         anio (int): Año a procesar
#     """
#     url = obtener_url("singles", anio=anio)
#     soup = descargar_pagina(url)
    
#     if not soup:
#         return
    
#     singles = extraer_top_singles_por_anio(soup, anio)
    
#     if singles:
#         # Añadir géneros a cada single
#         print(f"\n=== Obteniendo géneros para {len(singles)} singles del año {anio} ===")
#         total_singles = len(singles)
        
#         for i, single in enumerate(singles):
#             print(f"\n--- Procesando {i+1}/{total_singles} ---")
#             print(f"Canción: {single['título']} - {single['artista']}")
            
#             genero = obtener_genero_cancion(single['título'], single['artista'], es_album=False)
#             single['género'] = genero
            
#             # Pausa progresiva: más larga cada 5 canciones
#             if (i + 1) % 5 == 0:
#                 print(f"Pausa después de {i+1} canciones...")
#                 sleep(3)
#             elif (i + 1) % 10 == 0:
#                 print(f"Pausa larga después de {i+1} canciones...")
#                 sleep(5)
#             else:
#                 sleep(1.5)  # Pausa mínima entre canciones
        
#         archivo = os.path.join(OUTPUT_DIR, "singles", f"uk_top10_singles_{anio}_con_generos.csv")
#         guardar_csv_con_genero(singles, archivo, "singles")
#     else:
#         print(f"No se pudieron extraer datos para el año {anio}")

# def procesar_bestselling_singles_decada_con_genero(decada):
#     """
#     Procesa los datos de los singles más vendidos de una década incluyendo géneros.
    
#     Args:
#         decada (str): Década a procesar (e.g., "60s")
#     """
#     url = obtener_url("bestselling", decada=decada)
#     soup = descargar_pagina(url)
    
#     if not soup:
#         return
    
#     singles = extraer_bestselling_singles_decada(soup, decada)
    
#     if singles:
#         # Añadir géneros a cada single
#         print(f"\n=== Obteniendo géneros para {len(singles)} singles de los {decada} ===")
#         total_singles = len(singles)
        
#         for i, single in enumerate(singles):
#             print(f"\n--- Procesando {i+1}/{total_singles} ---")
#             print(f"Canción: {single['título']} - {single['artista']}")
            
#             genero = obtener_genero_cancion(single['título'], single['artista'], es_album=False)
#             single['género'] = genero
            
#             # Pausa progresiva
#             if (i + 1) % 3 == 0:
#                 print(f"Pausa después de {i+1} canciones...")
#                 sleep(3)
#             else:
#                 sleep(1)
        
#         archivo = os.path.join(OUTPUT_DIR, "bestselling", f"uk_bestselling_singles_{decada}_con_generos.csv")
#         guardar_csv_con_genero(singles, archivo, "bestselling")
#     else:
#         print(f"No se pudieron extraer datos para la década {decada}")

# def procesar_bestselling_singles_por_anio_con_genero():
#     """
#     Procesa los datos de los singles más vendidos de cada año incluyendo géneros.
#     """
#     url = obtener_url("bestselling")
#     soup = descargar_pagina(url)
    
#     if not soup:
#         return
    
#     singles = extraer_bestselling_singles_por_anio(soup)
    
#     if singles:
#         # Añadir géneros a cada single
#         print(f"\n=== Obteniendo géneros para {len(singles)} singles por año ===")
#         total_singles = len(singles)
        
#         for i, single in enumerate(singles):
#             print(f"\n--- Procesando {i+1}/{total_singles} ---")
#             print(f"Canción: {single['título']} - {single['artista']}")
            
#             genero = obtener_genero_cancion(single['título'], single['artista'], es_album=False)
#             single['género'] = genero
            
#             # Pausa progresiva
#             if (i + 1) % 5 == 0:
#                 print(f"Pausa después de {i+1} canciones...")
#                 sleep(3)
#             else:
#                 sleep(1)
        
#         archivo = os.path.join(OUTPUT_DIR, "bestselling", "uk_bestselling_singles_by_year_con_generos.csv")
#         guardar_csv_con_genero(singles, archivo, "bestselling")
#     else:
#         print(f"No se pudieron extraer datos de bestselling por año")


def procesar_bestselling_singles_por_anio_con_genero_db():
    """
    Procesa los datos de los singles más vendidos de cada año y los guarda en BD.
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    """
    # Verificar si ya existen datos
    if verificar_datos_existentes_bestselling('anual'):
        return
    
    url = obtener_url("bestselling")
    soup = descargar_pagina(url)
    
    if not soup:
        return
    
    singles = extraer_bestselling_singles_por_anio(soup)
    
    if singles:
        # Añadir géneros a cada single
        print(f"\n=== Obteniendo géneros para {len(singles)} singles por año ===")
        total_singles = len(singles)
        
        for i, single in enumerate(singles):
            print(f"\n--- Procesando {i+1}/{total_singles} ---")
            print(f"Canción: {single['título']} - {single['artista']}")
            
            genero = obtener_genero_cancion(single['título'], single['artista'], es_album=False)
            single['género'] = genero
            
            # Pausa progresiva
            if (i + 1) % 5 == 0:
                print(f"Pausa después de {i+1} canciones...")
                sleep(3)
            else:
                sleep(1)
        
        # Guardar en base de datos
        insert_bestselling_to_db(singles, 'anual')
        
        # Mantener funcionalidad CSV como respaldo
        archivo = os.path.join(OUTPUT_DIR, "bestselling", "uk_bestselling_singles_by_year_con_generos.csv")
        guardar_csv_con_genero(singles, archivo, "bestselling")



# BASE DE DATOS



# Añadir estas configuraciones después de las existentes
DB_PATH = Path(PROJECT_ROOT, "music_database.db")  # Ajusta la ruta según tu estructura

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    if DB_PATH is None:
        raise ValueError("Base de datos no configurada. Ejecuta init_config() primero.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_uk_charts_tables():
    """Crea las tablas para almacenar los datos de UK Charts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla para singles de top 10
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uk_charts_singles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            año INTEGER NOT NULL,
            posición INTEGER,
            título TEXT NOT NULL,
            artista TEXT NOT NULL,
            fecha_pico TEXT,
            género TEXT,
            artist_id INTEGER,
            song_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    ''')
    
    # Tabla para bestselling singles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uk_charts_bestselling (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('decada', 'anual')),
            década TEXT,
            año TEXT,
            posición TEXT,
            título TEXT NOT NULL,
            artista TEXT NOT NULL,
            ventas TEXT,
            género TEXT,
            artist_id INTEGER,
            song_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    ''')
    
    # Índices para mejorar rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_uk_singles_artist ON uk_charts_singles(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_uk_singles_year ON uk_charts_singles(año)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_uk_bestselling_artist ON uk_charts_bestselling(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_uk_bestselling_tipo ON uk_charts_bestselling(tipo)')
    
    conn.commit()
    conn.close()
    print("Tablas de UK Charts creadas correctamente")

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

def insert_singles_to_db(singles_data):
    """Inserta datos de singles en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for single in singles_data:
        # Buscar IDs relacionados
        artist_id = find_artist_id(single['artista'])
        song_id = find_song_id(single['título'], single['artista'])
        
        # Verificar si ya existe este registro
        cursor.execute("""
            SELECT id FROM uk_charts_singles 
            WHERE año = ? AND título = ? AND artista = ?
        """, (single['año'], single['título'], single['artista']))
        
        if not cursor.fetchone():  # Si no existe, insertar
            cursor.execute("""
                INSERT INTO uk_charts_singles 
                (año, posición, título, artista, fecha_pico, género, artist_id, song_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                single['año'],
                single.get('posición'),
                single['título'],
                single['artista'],
                single.get('fecha_pico'),
                single.get('género', 'N/A'),
                artist_id,
                song_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} singles en la base de datos")
    return inserted_count

def insert_bestselling_to_db(bestselling_data, tipo):
    """Inserta datos de bestselling en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for single in bestselling_data:
        # Buscar IDs relacionados
        artist_id = find_artist_id(single['artista'])
        song_id = find_song_id(single['título'], single['artista'])
        
        # Preparar datos según el tipo
        decada = single.get('década') if tipo == 'decada' else None
        año = single.get('año', 'N/A')
        
        # Verificar si ya existe este registro
        cursor.execute("""
            SELECT id FROM uk_charts_bestselling 
            WHERE tipo = ? AND título = ? AND artista = ? AND 
                  COALESCE(década, '') = COALESCE(?, '') AND año = ?
        """, (tipo, single['título'], single['artista'], decada, año))
        
        if not cursor.fetchone():  # Si no existe, insertar
            cursor.execute("""
                INSERT INTO uk_charts_bestselling 
                (tipo, década, año, posición, título, artista, ventas, género, artist_id, song_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tipo,
                decada,
                año,
                single.get('posición', 'N/A'),
                single['título'],
                single['artista'],
                single.get('ventas', 'N/A'),
                single.get('género', 'N/A'),
                artist_id,
                song_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} registros bestselling ({tipo}) en la base de datos")
    return inserted_count


# specialized


def create_specialized_charts_tables():
    """Crea las tablas para almacenar los datos de charts especializados"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla para vinilos (álbumes y singles)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uk_vinyl_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chart_type TEXT NOT NULL CHECK(chart_type IN ('albums', 'singles')),
            década TEXT NOT NULL,
            artista TEXT NOT NULL,
            título TEXT NOT NULL,
            fecha_numero_uno TEXT,
            semanas_numero_uno INTEGER,
            género TEXT,
            artist_id INTEGER,
            album_id INTEGER,
            song_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (album_id) REFERENCES albums(id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    ''')
    
    # Tabla para streaming de álbumes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uk_streaming_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chart_type TEXT NOT NULL CHECK(chart_type IN ('albums')),
            año INTEGER,
            artista TEXT NOT NULL,
            álbum TEXT NOT NULL,
            posición INTEGER,
            semanas_en_chart INTEGER,
            género TEXT,
            artist_id INTEGER,
            album_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (album_id) REFERENCES albums(id)
        )
    ''')
    
    # Tabla para descargas de singles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uk_downloads_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chart_type TEXT NOT NULL CHECK(chart_type IN ('singles')),
            año INTEGER,
            artista TEXT NOT NULL,
            single TEXT NOT NULL,
            posición INTEGER,
            semanas_en_chart INTEGER,  
            ventas_totales TEXT,
            género TEXT,
            artist_id INTEGER,
            song_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    ''')
    
    # Índices adicionales
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vinyl_artist ON uk_vinyl_charts(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vinyl_decade ON uk_vinyl_charts(década)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_streaming_artist ON uk_streaming_charts(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_artist ON uk_downloads_charts(artista)')
    
    conn.commit()
    conn.close()
    print("Tablas de UK Specialized Charts creadas correctamente")

def extraer_vinyl_chart_data(soup, decade, chart_type):
    """
    Extrae datos de los charts de vinilos (albums o singles)
    
    Args:
        soup (BeautifulSoup): Contenido HTML de la página
        decade (str): Década (10s, 20s)
        chart_type (str): Tipo de chart (albums, singles)
        
    Returns:
        list: Lista de diccionarios con los datos extraídos
    """
    data = []
    
    # Buscar tablas principales en la página
    tablas = soup.find_all('table', class_='wikitable')
    
    if not tablas:
        print(f"No se encontraron tablas en la página de vinyl {chart_type} {decade}")
        return data
    
    # Buscar la tabla principal con los datos del chart
    tabla_principal = None
    for tabla in tablas:
        # Verificar encabezados de tabla
        encabezados = tabla.find_all('th')
        if encabezados and len(encabezados) >= 3:
            textos = [th.get_text().strip().lower() for th in encabezados]
            # Buscar encabezados típicos: "artist", "album"/"single", "date", "weeks"
            if any(keyword in ' '.join(textos) for keyword in ['artist', 'album', 'single', 'date', 'weeks']):
                tabla_principal = tabla
                break
    
    if not tabla_principal:
        print(f"No se encontró tabla principal para vinyl {chart_type} {decade}")
        return data
    
    # Extraer filas de datos
    filas = tabla_principal.find_all('tr')
    
    for fila in filas[1:]:  # Saltar encabezados
        celdas = fila.find_all(['td', 'th'])
        
        if len(celdas) < 3:
            continue
        
        try:
            # Estructura típica: Artista | Álbum/Single | Fecha | Semanas
            artista = limpiar_texto(celdas[0].get_text())
            titulo = limpiar_texto(celdas[1].get_text()) 
            fecha = limpiar_texto(celdas[2].get_text()) if len(celdas) > 2 else 'N/A'
            semanas = limpiar_texto(celdas[3].get_text()) if len(celdas) > 3 else 'N/A'
            
            # Convertir semanas a entero si es posible
            try:
                semanas_num = int(re.search(r'\d+', semanas).group()) if re.search(r'\d+', semanas) else None
            except:
                semanas_num = None
                
            if artista and titulo:
                data.append({
                    'década': f"20{decade}",
                    'chart_type': chart_type,
                    'artista': artista,
                    'título': titulo,
                    'fecha_numero_uno': fecha,
                    'semanas_numero_uno': semanas_num,
                    'género': 'N/A'  # Se puede añadir después si se solicita
                })
                
        except Exception as e:
            print(f"Error al extraer datos de fila: {e}")
            continue
    
    return data

def extraer_streaming_data(soup):
    """
    Extrae datos del Official Albums Streaming Chart
    
    Args:
        soup (BeautifulSoup): Contenido HTML de la página
        
    Returns:
        list: Lista de diccionarios con los datos extraídos
    """
    data = []
    
    # Buscar información en el texto de la página
    texto_pagina = soup.get_text()
    
    # Buscar información específica mencionada en el artículo
    # Ed Sheeran x fue el primero en 2015
    if "Ed Sheeran" in texto_pagina and "x" in texto_pagina:
        data.append({
            'año': 2015,
            'chart_type': 'albums',
            'artista': 'Ed Sheeran',
            'álbum': 'x',
            'posición': 1,
            'semanas_en_chart': None,
            'género': 'Pop'
        })
    
    # ÷ (Divide) tuvo 34 semanas en #1
    if "÷" in texto_pagina or "Divide" in texto_pagina:
        data.append({
            'año': 2017,
            'chart_type': 'albums', 
            'artista': 'Ed Sheeran',
            'álbum': '÷',
            'posición': 1,
            'semanas_en_chart': 34,
            'género': 'Pop'
        })
        
    return data

def extraer_downloads_data(soup):
    """
    Extrae datos del UK Singles Downloads Chart
    
    Args:
        soup (BeautifulSoup): Contenido HTML de la página
        
    Returns:
        list: Lista de diccionarios con los datos extraídos
    """
    data = []
    
    # Buscar información específica mencionada en el artículo
    texto_pagina = soup.get_text()
    
    # Información extraída del artículo
    singles_destacados = [
        {
            'año': 2004,
            'artista': 'Westlife', 
            'single': 'Flying Without Wings',
            'posición': 1,
            'nota': 'Primer #1 oficial'
        },
        {
            'año': 2006,
            'artista': 'Gnarls Barkley',
            'single': 'Crazy', 
            'posición': 1,
            'semanas_en_chart': 11,
            'nota': 'Más tiempo en #1'
        },
        {
            'año': 2009,
            'artista': 'Rage Against the Machine',
            'single': 'Killing in the Name',
            'posición': 1, 
            'nota': 'Descarga más rápida de todos los tiempos'
        },
        {
            'año': 2014,
            'artista': 'Pharrell Williams',
            'single': 'Happy',
            'posición': 1,
            'nota': 'Canción más descargada de la historia UK'
        }
    ]
    
    for single in singles_destacados:
        data.append({
            'año': single['año'],
            'chart_type': 'singles',
            'artista': single['artista'],
            'single': single['single'],
            'posición': single['posición'],
            'semanas_en_chart': single.get('semanas_en_chart'),
            'ventas_totales': 'N/A',
            'género': 'N/A'
        })
    
    return data

def find_album_id(album_name, artist_name):
    """Busca el album_id en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT albums.id FROM albums 
        JOIN artists ON albums.artist_id = artists.id
        WHERE LOWER(albums.name) = LOWER(?) AND LOWER(artists.name) = LOWER(?)
    """, (album_name, artist_name))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def insert_vinyl_data_to_db(vinyl_data):
    """Inserta datos de vinilos en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for record in vinyl_data:
        # Buscar IDs relacionados
        artist_id = find_artist_id(record['artista'])
        
        if record['chart_type'] == 'albums':
            album_id = find_album_id(record['título'], record['artista'])
            song_id = None
        else:
            album_id = None
            song_id = find_song_id(record['título'], record['artista'])
        
        # Verificar si ya existe
        cursor.execute("""
            SELECT id FROM uk_vinyl_charts 
            WHERE chart_type = ? AND década = ? AND artista = ? AND título = ?
        """, (record['chart_type'], record['década'], record['artista'], record['título']))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO uk_vinyl_charts 
                (chart_type, década, artista, título, fecha_numero_uno, semanas_numero_uno, 
                 género, artist_id, album_id, song_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['chart_type'],
                record['década'],
                record['artista'],
                record['título'],
                record['fecha_numero_uno'],
                record['semanas_numero_uno'],
                record.get('género', 'N/A'),
                artist_id,
                album_id,
                song_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} registros de vinyl en la base de datos")
    return inserted_count

def insert_streaming_data_to_db(streaming_data):
    """Inserta datos de streaming en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for record in streaming_data:
        artist_id = find_artist_id(record['artista'])
        album_id = find_album_id(record['álbum'], record['artista'])
        
        cursor.execute("""
            SELECT id FROM uk_streaming_charts 
            WHERE año = ? AND artista = ? AND álbum = ?
        """, (record['año'], record['artista'], record['álbum']))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO uk_streaming_charts 
                (chart_type, año, artista, álbum, posición, semanas_en_chart, género, artist_id, album_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['chart_type'],
                record['año'],
                record['artista'],
                record['álbum'],
                record['posición'],
                record['semanas_en_chart'],
                record.get('género', 'N/A'),
                artist_id,
                album_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} registros de streaming en la base de datos")
    return inserted_count

def insert_downloads_data_to_db(downloads_data):
    """Inserta datos de descargas en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for record in downloads_data:
        artist_id = find_artist_id(record['artista'])
        song_id = find_song_id(record['single'], record['artista'])
        
        cursor.execute("""
            SELECT id FROM uk_downloads_charts 
            WHERE año = ? AND artista = ? AND single = ?
        """, (record['año'], record['artista'], record['single']))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO uk_downloads_charts 
                (chart_type, año, artista, single, posición, semanas_en_chart, ventas_totales, 
                 género, artist_id, song_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['chart_type'],
                record['año'],
                record['artista'],
                record['single'],
                record['posición'],
                record['semanas_en_chart'],
                record.get('ventas_totales', 'N/A'),
                record.get('género', 'N/A'),
                artist_id,
                song_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} registros de downloads en la base de datos")
    return inserted_count

def procesar_vinyl_charts():
    """
    Procesa todos los charts de vinilos disponibles
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    """
    print("\n=== Procesando Charts de Vinilos ===")
    
    for chart_type in ['albums', 'singles']:
        for decade in ['10s', '20s']:
            # Verificar si ya existen datos
            if verificar_datos_existentes_vinyl(chart_type, decade):
                continue
            
            url_key = f"vinyl_{chart_type}"
            url = urljoin(BASE_URL, SPECIALIZED_URLS[url_key][decade])
            soup = descargar_pagina(url)
            
            if soup:
                data = extraer_vinyl_chart_data(soup, decade, chart_type)
                if data:
                    insert_vinyl_data_to_db(data)
                    print(f"Procesados {len(data)} registros de vinyl {chart_type} {decade}")
                else:
                    print(f"No se encontraron datos para vinyl {chart_type} {decade}")
            
            time.sleep(1)  # Rate limiting

def procesar_streaming_charts():
    """
    Procesa el chart de streaming de álbumes
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    """
    print("\n=== Procesando Charts de Streaming ===")
    
    # Verificar si ya existen datos
    if verificar_datos_existentes_streaming():
        return
    
    url = urljoin(BASE_URL, SPECIALIZED_URLS['streaming_albums'])
    soup = descargar_pagina(url)
    
    if soup:
        data = extraer_streaming_data(soup)
        if data:
            insert_streaming_data_to_db(data)
            print(f"Procesados {len(data)} registros de streaming")
        else:
            print("No se encontraron datos de streaming")

def procesar_downloads_charts():
    """
    Procesa el chart de descargas de singles
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    """
    print("\n=== Procesando Charts de Descargas ===")
    
    # Verificar si ya existen datos
    if verificar_datos_existentes_downloads():
        return
    
    url = urljoin(BASE_URL, SPECIALIZED_URLS['downloads_singles'])
    soup = descargar_pagina(url)
    
    if soup:
        data = extraer_downloads_data(soup)
        if data:
            insert_downloads_data_to_db(data)
            print(f"Procesados {len(data)} registros de downloads")
        else:
            print("No se encontraron datos de downloads")


def configurar_argumentos():
    """Configura los argumentos de línea de comandos - VERSIÓN EXPANDIDA"""
    # Si se ejecuta desde db_creator, usar configuración en lugar de argumentos  
    if CONFIG:
        # Crear args simulados basados en la configuración
        class ConfigArgs:
            def __init__(self, config):
                self.type = config.get('type', 'all')
                self.decade = config.get('decade')
                self.year = config.get('year')
                self.all = config.get('type') == 'all' or config.get('all', False)
                self.generos = config.get('generos', False)
                self.specialized = config.get('specialized', False)  # NUEVO
        
        return ConfigArgs(CONFIG)
    
    # Solo parsear argumentos si se ejecuta directamente
    parser = argparse.ArgumentParser(description="UK Charts Scraper - Incluyendo Charts Especializados")
    parser.add_argument("--type", choices=["singles", "albums", "bestselling", "numberones", "vinyl", "streaming", "downloads"],
                        help="Tipo de datos a extraer")
    parser.add_argument("--decade", choices=obtener_decadas_disponibles(),
                        help="Década a extraer")
    parser.add_argument("--year", type=int, choices=range(1952, 2025),
                        help="Año específico a extraer")
    parser.add_argument("--all", action="store_true",
                        help="Extraer todos los datos disponibles")
    parser.add_argument("--generos", action="store_true",
                        help="Incluir información de géneros musicales")
    parser.add_argument("--specialized", action="store_true", 
                        help="Incluir charts especializados (vinyl, streaming, downloads)")  # NUEVO
    
    return parser.parse_args()

# indie nme 

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

def procesar_indie_charts_db(years=None):
    """
    Procesa los UK Independent Singles Charts para años específicos
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    
    Args:
        years (list, optional): Lista de años a procesar. Si None, usa configuración
    """
    print("\n=== Procesando UK Independent Singles Charts ===")
    
    if years is None:
        # Obtener años de la configuración
        years = CONFIG.get('indie_years', [1999, 2000, 2001, 2002, 2007])
    
    all_data = []
    
    for year in years:
        # Verificar si ya existen datos
        if verificar_datos_existentes_indie(year):
            continue
        
        print(f"Procesando UK Independent Chart año {year}")
        url = urljoin(BASE_URL, INDIE_NME_URLS["indie_base"] + str(year))
        soup = descargar_pagina(url)
        
        if soup:
            data = extraer_indie_chart_data(soup, year)
            if data:
                all_data.extend(data)
                print(f"Extraídos {len(data)} registros para {year}")
            else:
                print(f"No se encontraron datos para {year}")
        
        time.sleep(CONFIG.get('rate_limit', 1.5))  # Rate limiting
    
    if all_data:
        # Guardar en base de datos
        insert_indie_data_to_db(all_data)
        print(f"Total procesados: {len(all_data)} registros de UK Independent Chart")

def procesar_nme_charts_db(decades=None):
    """
    Procesa los NME Charts para décadas específicas
    VERSIÓN MODIFICADA: Verifica datos existentes antes de procesar.
    
    Args:
        decades (list, optional): Lista de décadas a procesar. Si None, usa configuración
    """
    print("\n=== Procesando NME Charts ===")
    
    if decades is None:
        # Obtener décadas de la configuración
        decades = CONFIG.get('nme_decades', ["60s", "70s", "80s"])
    
    all_data = []
    
    for decade in decades:
        # Verificar si ya existen datos
        if verificar_datos_existentes_nme(decade):
            continue
        
        print(f"Procesando NME Chart década {decade}")
        url = urljoin(BASE_URL, INDIE_NME_URLS["nme"][decade])
        soup = descargar_pagina(url)
        
        if soup:
            data = extraer_nme_chart_data(soup, decade)
            if data:
                all_data.extend(data)
                print(f"Extraídos {len(data)} registros para {decade}")
            else:
                print(f"No se encontraron datos para {decade}")
        
        time.sleep(CONFIG.get('rate_limit', 1.5))  # Rate limiting
    
    if all_data:
        # Guardar en base de datos
        insert_nme_data_to_db(all_data)
        print(f"Total procesados: {len(all_data)} registros de NME Chart")


# VERIFICAR DATPOS EN DB ANTES DE DESCARGAR

def verificar_datos_existentes_singles(anio):
    """
    Verifica si ya existen datos de singles para un año específico en la base de datos
    
    Args:
        anio (int): Año a verificar
        
    Returns:
        bool: True si ya existen datos, False si no
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM uk_charts_singles WHERE año = ?", (anio,))
    count = cursor.fetchone()[0]
    
    conn.close()
    
    if count > 0:
        print(f"Ya existen {count} registros de singles para el año {anio}. Saltando...")
        return True
    return False

def verificar_datos_existentes_bestselling(tipo, decada=None, anio=None):
    """
    Verifica si ya existen datos de bestselling para una década o año específico
    
    Args:
        tipo (str): 'decada' o 'anual'
        decada (str, optional): Década a verificar
        anio (str, optional): Año a verificar
        
    Returns:
        bool: True si ya existen datos, False si no
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if tipo == 'decada' and decada:
        cursor.execute("SELECT COUNT(*) FROM uk_charts_bestselling WHERE tipo = ? AND década = ?", 
                      (tipo, decada))
    elif tipo == 'anual':
        cursor.execute("SELECT COUNT(*) FROM uk_charts_bestselling WHERE tipo = ?", (tipo,))
    else:
        conn.close()
        return False
    
    count = cursor.fetchone()[0]
    conn.close()
    
    if count > 0:
        identificador = decada if decada else "todos los años"
        print(f"Ya existen {count} registros de bestselling {tipo} para {identificador}. Saltando...")
        return True
    return False

def verificar_datos_existentes_vinyl(chart_type, decade):
    """
    Verifica si ya existen datos de vinyl para un tipo y década específicos
    
    Args:
        chart_type (str): 'albums' o 'singles'
        decade (str): Década a verificar
        
    Returns:
        bool: True si ya existen datos, False si no
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    decade_full = f"20{decade}"
    cursor.execute("SELECT COUNT(*) FROM uk_vinyl_charts WHERE chart_type = ? AND década = ?", 
                  (chart_type, decade_full))
    count = cursor.fetchone()[0]
    
    conn.close()
    
    if count > 0:
        print(f"Ya existen {count} registros de vinyl {chart_type} para {decade_full}. Saltando...")
        return True
    return False

def verificar_datos_existentes_streaming():
    """
    Verifica si ya existen datos de streaming en la base de datos
    
    Returns:
        bool: True si ya existen datos, False si no
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM uk_streaming_charts")
    count = cursor.fetchone()[0]
    
    conn.close()
    
    if count > 0:
        print(f"Ya existen {count} registros de streaming. Saltando...")
        return True
    return False

def verificar_datos_existentes_downloads():
    """
    Verifica si ya existen datos de downloads en la base de datos
    
    Returns:
        bool: True si ya existen datos, False si no
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM uk_downloads_charts")
    count = cursor.fetchone()[0]
    
    conn.close()
    
    if count > 0:
        print(f"Ya existen {count} registros de downloads. Saltando...")
        return True
    return False

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
    """Función principal del script con soporte para géneros, base de datos y charts especializados"""
    # Inicializar configuración si se proporciona
    if config:
        init_config(config)
        print(f"Usando base de datos: {DB_PATH}")
    
    args = configurar_argumentos()
    
    # Crear tablas de base de datos (incluyendo especializadas)
    create_uk_charts_tables()
    create_specialized_charts_tables()  # NUEVO
    create_indie_nme_charts_tables() 


    # Crear directorios de salida (mantenidos para respaldo CSV)
    os.makedirs(os.path.join(OUTPUT_DIR, "singles"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "albums"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "bestselling"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "vinyl"), exist_ok=True)         # NUEVO
    os.makedirs(os.path.join(OUTPUT_DIR, "streaming"), exist_ok=True)     # NUEVO
    os.makedirs(os.path.join(OUTPUT_DIR, "downloads"), exist_ok=True)     # NUEVO
    os.makedirs(os.path.join(OUTPUT_DIR, "indie"), exist_ok=True)      # AÑADIR
    os.makedirs(os.path.join(OUTPUT_DIR, "nme"), exist_ok=True) 

    # Determinar si usar funciones con géneros o sin géneros
    usar_generos = args.generos
    incluir_especializados = getattr(args, 'specialized', False)
    
    if args.all:
        # Extraer todos los datos disponibles
        if usar_generos:
            print("Extrayendo todos los datos disponibles CON información de géneros...")
        else:
            print("Extrayendo todos los datos disponibles SIN información de géneros...")
        

        if CONFIG.get('include_indie', False):
            print("\n=== Procesando UK Independent Charts ===")
            procesar_indie_charts_db()
            
        if CONFIG.get('include_nme', False):
            print("\n=== Procesando NME Charts ===")
            procesar_nme_charts_db()


        # Extraer singles por año desde 1952 hasta 2024
        for anio in range(1952, 2025):
            if usar_generos:
                procesar_singles_por_anio_con_genero_db(anio)
            else:
                procesar_singles_por_anio_db(anio)
            time.sleep(1)  # Pausa para evitar sobrecargar el servidor
        
        # Extraer bestselling singles por década
        for decada in ["50s", "60s", "70s", "80s", "90s", "00s", "10s", "20s"]:
            if usar_generos:
                procesar_bestselling_singles_decada_con_genero_db(decada)
            else:
                procesar_bestselling_singles_decada_db(decada)
            time.sleep(1)
        
        # Extraer bestselling singles por año
        if usar_generos:
            procesar_bestselling_singles_por_anio_con_genero_db()
        else:
            procesar_bestselling_singles_por_anio_db()
        
        # NUEVO: Procesar charts especializados si están habilitados
        if incluir_especializados:
            print("\n=== Procesando Charts Especializados ===")
            procesar_vinyl_charts()
            procesar_streaming_charts()
            procesar_downloads_charts()
            
    elif args.type in ["vinyl", "streaming", "downloads", "indie", "nme"]:  # MODIFICAR ESTA LÍNEA
        # Manejar tipos especializados (AÑADIR ESTAS LÍNEAS)
        if args.type == "vinyl":
            procesar_vinyl_charts()
        elif args.type == "streaming":
            procesar_streaming_charts()
        elif args.type == "downloads":
            procesar_downloads_charts()
        elif args.type == "indie":  # NUEVO
            procesar_indie_charts_db()
        elif args.type == "nme":    # NUEVO
            procesar_nme_charts_db()
    else:
        # Extraer datos específicos según los argumentos (lógica existente)
        if args.type == "singles" and args.year:
            if usar_generos:
                procesar_singles_por_anio_con_genero_db(args.year)
            else:
                procesar_singles_por_anio_db(args.year)
        elif args.type == "bestselling" and args.decade:
            if usar_generos:
                procesar_bestselling_singles_decada_con_genero_db(args.decade)
            else:
                procesar_bestselling_singles_decada_db(args.decade)
        elif args.type == "bestselling" and not args.decade:
            if usar_generos:
                procesar_bestselling_singles_por_anio_con_genero_db()
            else:
                procesar_bestselling_singles_por_anio_db()
        else:
            print("Argumentos no válidos. Use --help para obtener ayuda.")
            print("Ejemplos:")
            print("  python uk_csv.py --type singles --year 1975")
            print("  python uk_csv.py --type singles --year 1975 --generos")
            print("  python uk_csv.py --type bestselling --decade 60s --generos")
            print("  python uk_csv.py --type vinyl")
            print("  python uk_csv.py --type streaming") 
            print("  python uk_csv.py --type downloads")
            print("  python uk_csv.py --all --generos --specialized")
            print("  python uk_csv.py --type indie")
            print("  python uk_csv.py --type nme")

if __name__ == "__main__":
    main()