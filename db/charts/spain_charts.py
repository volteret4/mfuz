# spain_csv.py - Script para extraer charts españoles
# Funciones adicionales para extraer datos de Wikipedia sobre charts españoles
# Basado en el formato del script uk_csv.py existente

import os
import re
import csv
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from time import sleep
import sqlite3
from pathlib import Path
import sys

# Añadir la ruta del directorio padre para importar base_module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from base_module import PROJECT_ROOT
except ImportError:
    # Fallback si no se puede importar
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Importar funciones comunes del script UK (asumiendo que están en el mismo directorio)
from db.charts.uk_csv import (descargar_pagina, limpiar_texto, obtener_genero_cancion,
                     get_db_connection, find_artist_id, find_song_id, CONFIG, DB_PATH, 
                     OUTPUT_DIR, BASE_URL, HEADERS)

# URLs específicas para España
SPAIN_URLS = {
    "number_ones_by_year": "/wiki/List_of_number-one_singles_of_{year}_(Spain)",
    "number_ones_albums_by_year": "/wiki/List_of_number-one_albums_of_{year}_(Spain)",
    "number_ones_historic": "/wiki/List_of_Spanish_number-one_hits_of_{year}",
    "main_list": "/wiki/List_of_number-one_hits_(Spain)"
}


def init_config(config=None):
    """Inicializa la configuración del script español"""
    global CONFIG, DB_PATH
    
    if config:
        CONFIG = config
        DB_PATH = Path(config.get('db_path', 'music_database.db'))
        print(f"Spain Charts - Configuración inicializada desde db_creator")
        print(f"Spain Charts - Base de datos: {DB_PATH}")
        print(f"Spain Charts - Géneros habilitados: {config.get('generos', False)}")
        
        # IMPORTANTE: También actualizar las variables globales de uk_csv
        import db.charts.uk_csv as uk_csv
        uk_csv.CONFIG = config
        uk_csv.DB_PATH = DB_PATH
        
        # Actualizar configuraciones de API específicas si existen
        if 'discogs_token' in config:
            uk_csv.DISCOGS_TOKEN = config['discogs_token']
        if 'musicbrainz_user_agent' in config:
            uk_csv.MUSICBRAINZ_USER_AGENT = config['musicbrainz_user_agent']
        if 'rate_limit' in config:
            uk_csv.DISCOGS_REQUEST_DELAY = config['rate_limit']
            
        print("Spain Charts - Variables de uk_csv actualizadas correctamente")
    else:
        # Configuración por defecto si no se proporciona
        DB_PATH = Path(PROJECT_ROOT, "music_database.db") if 'PROJECT_ROOT' in globals() else Path("music_database.db")
        CONFIG = {}

def verificar_configuracion():
    """Verifica que la configuración esté correcta"""
    if DB_PATH is None:
        raise ValueError("DB_PATH no está configurado. Ejecuta init_config() primero.")
    
    if not CONFIG:
        print("Advertencia: CONFIG está vacío")
    
    print(f"Spain Charts - Verificación: DB_PATH = {DB_PATH}")
    print(f"Spain Charts - Verificación: CONFIG keys = {list(CONFIG.keys()) if CONFIG else 'None'}")
    
    # Verificar que uk_csv también tenga la configuración
    from db.charts.uk_csv import DB_PATH as uk_db_path, CONFIG as uk_config
    print(f"Spain Charts - Verificación: uk_csv.DB_PATH = {uk_db_path}")
    print(f"Spain Charts - Verificación: uk_csv.CONFIG keys = {list(uk_config.keys()) if uk_config else 'None'}")


def verificar_base_datos():
    """Verifica que la base de datos existe y tiene las tablas necesarias"""
    try:
        print(f"Verificando base de datos en: {DB_PATH}")
        
        if not DB_PATH.exists():
            print(f"ERROR: El archivo de base de datos no existe: {DB_PATH}")
            return False
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que existe la tabla artists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artists'")
        if not cursor.fetchone():
            print(f"ERROR: La tabla 'artists' no existe en {DB_PATH}")
            conn.close()
            return False
            
        # Verificar que existe la tabla songs
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='songs'")
        if not cursor.fetchone():
            print(f"ERROR: La tabla 'songs' no existe en {DB_PATH}")
            conn.close()
            return False
            
        print(f"Base de datos verificada correctamente: {DB_PATH}")
        
        # Mostrar algunas estadísticas para confirmar
        cursor.execute("SELECT COUNT(*) FROM artists")
        artists_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM songs")
        songs_count = cursor.fetchone()[0]
        
        print(f"Tabla 'artists': {artists_count} registros")
        print(f"Tabla 'songs': {songs_count} registros")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error verificando base de datos: {e}")
        return False


def obtener_url_spain(tipo, anio=None):
    """
    Obtiene la URL de Wikipedia para los charts españoles según el tipo y año.
    Incluye fallback para años con formatos de URL diferentes.
    
    Args:
        tipo (str): Tipo de datos ('singles', 'albums')
        anio (int, optional): Año específico
        
    Returns:
        tuple: (url_principal, url_fallback) o (None, None) si no es válida
    """
    if tipo == "singles" and anio:
        # Para años más recientes (desde ~1990), usar el formato moderno
        if anio >= 1990:
            url_principal = urljoin(BASE_URL, SPAIN_URLS["number_ones_by_year"].format(year=anio))
            return url_principal, None
        else:
            # Para años históricos (1959-1989), usar el formato histórico con fallback
            url_principal = urljoin(BASE_URL, SPAIN_URLS["number_ones_historic"].format(year=anio))
            # URL de fallback con "(Spain)" al final
            url_fallback = urljoin(BASE_URL, f"/wiki/List_of_number-one_singles_of_{anio}_(Spain)")
            return url_principal, url_fallback
    
    elif tipo == "albums" and anio:
        # Solo para años recientes hay listas de álbumes
        if anio >= 1995:
            url_principal = urljoin(BASE_URL, SPAIN_URLS["number_ones_albums_by_year"].format(year=anio))
            return url_principal, None
        else:
            print(f"No hay datos de álbumes disponibles para el año {anio}")
            return None, None
    
    elif tipo == "main_list":
        url_principal = urljoin(BASE_URL, SPAIN_URLS["main_list"])
        return url_principal, None
    
    print(f"Combinación no válida: tipo={tipo}, anio={anio}")
    return None, None

def descargar_pagina_con_fallback(url_principal, url_fallback=None):
    """
    Descarga una página web con fallback a URL alternativa si falla la principal.
    
    Args:
        url_principal (str): URL principal a intentar
        url_fallback (str, optional): URL alternativa si falla la principal
        
    Returns:
        BeautifulSoup: Objeto BeautifulSoup con el contenido de la página
    """
    # Intentar con URL principal primero
    print(f"Intentando URL principal: {url_principal}")
    soup = descargar_pagina(url_principal)
    
    if soup:
        print("✓ URL principal funcionó correctamente")
        return soup
    
    # Si falla y hay URL de fallback, intentar con ella
    if url_fallback:
        print(f"✗ URL principal falló, intentando fallback: {url_fallback}")
        soup = descargar_pagina(url_fallback)
        
        if soup:
            print("✓ URL de fallback funcionó correctamente")
            return soup
        else:
            print("✗ Ambas URLs fallaron")
    else:
        print("✗ URL principal falló y no hay fallback disponible")
    
    return None


def extraer_number_ones_spain_moderno(soup, anio):
    """
    Extrae los datos de número 1 españoles para años modernos (1990+).
    Estructura: Week | Issue date | Top Streaming/Sales | Most Airplay
    
    Args:
        soup (BeautifulSoup): Contenido HTML de la página
        anio (int): Año a extraer
        
    Returns:
        list: Lista de diccionarios con los datos
    """
    singles = []
    
    # Buscar las tablas principales
    tablas = soup.find_all('table', class_='wikitable')
    
    if not tablas:
        print(f"No se encontraron tablas en la página del año {anio}")
        return singles
    
    # La primera tabla suele contener los datos principales
    tabla_principal = tablas[0]
    
    # Extraer filas de la tabla
    filas = tabla_principal.find_all('tr')
    
    # Saltamos la primera fila (encabezados)
    for fila in filas[1:]:
        celdas = fila.find_all(['td', 'th'])
        
        # Necesitamos al menos 4 celdas para el formato moderno
        if len(celdas) < 4:
            continue
        
        try:
            # Estructura típica: Week | Issue date | Artist - Song | Artist - Song (radio)
            semana = limpiar_texto(celdas[0].get_text())
            fecha = limpiar_texto(celdas[1].get_text())
            
            # Extraer información de streaming/sales (columna 2)
            streaming_cell = celdas[2]
            streaming_text = limpiar_texto(streaming_cell.get_text())
            
            # Separar artista y canción del formato "Artist - Song" o "Artist Song"
            titulo_streaming, artista_streaming = separar_artista_titulo(streaming_text)
            
            # Extraer información de radio (columna 3) si existe
            titulo_radio = 'N/A'
            artista_radio = 'N/A'
            
            if len(celdas) > 3:
                radio_cell = celdas[3]
                radio_text = limpiar_texto(radio_cell.get_text())
                if radio_text and radio_text != 'N/A':
                    titulo_radio, artista_radio = separar_artista_titulo(radio_text)
            
            # Agregar entrada para streaming/sales
            if titulo_streaming and artista_streaming:
                singles.append({
                    'año': anio,
                    'semana': semana,
                    'fecha': fecha,
                    'título': titulo_streaming,
                    'artista': artista_streaming,
                    'tipo_chart': 'Streaming/Sales',
                    'posición': 1  # Siempre número 1
                })
            
            # Agregar entrada para radio si es diferente
            if (titulo_radio and artista_radio and 
                titulo_radio != 'N/A' and 
                (titulo_radio != titulo_streaming or artista_radio != artista_streaming)):
                singles.append({
                    'año': anio,
                    'semana': semana,
                    'fecha': fecha,
                    'título': titulo_radio,
                    'artista': artista_radio,
                    'tipo_chart': 'Radio',
                    'posición': 1
                })
                
        except Exception as e:
            print(f"Error al extraer datos de una fila: {e}")
            continue
    
    return singles

def extraer_number_ones_spain_historico(soup, anio):
    """
    Extrae los datos de número 1 españoles para años históricos (1959-1989).
    Estructura más simple: Issue Date | Song | Artist
    
    Args:
        soup (BeautifulSoup): Contenido HTML de la página
        anio (int): Año a extraer
        
    Returns:
        list: Lista de diccionarios con los datos
    """
    singles = []
    
    # Buscar las tablas principales
    tablas = soup.find_all('table', class_='wikitable')
    
    if not tablas:
        print(f"No se encontraron tablas en la página del año {anio}")
        return singles
    
    # La primera tabla suele contener los datos
    tabla_principal = tablas[0]
    
    # Extraer filas de la tabla
    filas = tabla_principal.find_all('tr')
    
    # Saltamos la primera fila (encabezados)
    for fila in filas[1:]:
        celdas = fila.find_all(['td', 'th'])
        
        # Necesitamos al menos 3 celdas: Issue Date | Song | Artist
        if len(celdas) < 3:
            continue
        
        try:
            fecha = limpiar_texto(celdas[0].get_text())
            titulo = limpiar_texto(celdas[1].get_text())
            artista = limpiar_texto(celdas[2].get_text())
            
            # Solo agregar si hay título y artista válidos
            if titulo and artista and titulo != '' and artista != '':
                singles.append({
                    'año': anio,
                    'semana': 'N/A',
                    'fecha': fecha,
                    'título': titulo,
                    'artista': artista,
                    'tipo_chart': 'Singles',
                    'posición': 1
                })
                
        except Exception as e:
            print(f"Error al extraer datos de una fila: {e}")
            continue
    
    return singles

def separar_artista_titulo(texto_combinado):
    """
    Separa el artista y título de un texto combinado.
    Formatos comunes: "Artist - Title", "Artist Title", "Title by Artist"
    
    Args:
        texto_combinado (str): Texto que contiene artista y título
        
    Returns:
        tuple: (titulo, artista)
    """
    if not texto_combinado or texto_combinado.strip() == '':
        return 'N/A', 'N/A'
    
    texto = texto_combinado.strip()
    
    # Formato: "Artist - Title"
    if ' - ' in texto:
        partes = texto.split(' - ', 1)
        if len(partes) == 2:
            return partes[1].strip(), partes[0].strip()
    
    # Formato: "Title by Artist"
    if ' by ' in texto:
        partes = texto.split(' by ', 1)
        if len(partes) == 2:
            return partes[0].strip(), partes[1].strip()
    
    # Formato: "Artist: Title"
    if ': ' in texto:
        partes = texto.split(': ', 1)
        if len(partes) == 2:
            return partes[1].strip(), partes[0].strip()
    
    # Si no se puede separar, asumir que todo es el título
    return texto, 'N/A'

def procesar_singles_spain_anio_db(anio):
    """
    Procesa los datos de número 1 de España para un año específico y los guarda en BD.
    """
    # Verificar si ya existen datos
    if verificar_datos_existentes_spain_singles(anio):
        return
        
    # Obtener URLs (principal y fallback)
    urls = obtener_url_spain("singles", anio=anio)
    if urls[0] is None:  # Si no hay URL principal
        return
    
    url_principal, url_fallback = urls
    
    # Intentar descargar con fallback
    soup = descargar_pagina_con_fallback(url_principal, url_fallback)
    if not soup:
        print(f"No se pudo descargar ninguna página para el año {anio}")
        return
    
    # Usar extractor apropiado según el año
    if anio >= 1990:
        singles = extraer_number_ones_spain_moderno(soup, anio)
    else:
        singles = extraer_number_ones_spain_historico(soup, anio)
    
    if singles:
        # Guardar en base de datos
        insert_spain_singles_to_db(singles)
        
        # Guardar CSV como respaldo
        archivo = os.path.join(OUTPUT_DIR, "spain", f"spain_number_ones_{anio}.csv")
        guardar_csv_spain(singles, archivo, "singles")
        
        print(f"Procesados {len(singles)} singles de España para el año {anio}")
    else:
        print(f"No se encontraron datos para España en el año {anio}")

def procesar_singles_spain_anio_con_genero_db(anio):
    """
    Procesa los datos de número 1 de España para un año específico con géneros y los guarda en BD.
    """
    # Verificar si ya existen datos
    if verificar_datos_existentes_spain_singles(anio):
        return
        
    # Obtener URLs (principal y fallback)
    urls = obtener_url_spain("singles", anio=anio)
    if urls[0] is None:  # Si no hay URL principal
        return
    
    url_principal, url_fallback = urls
    
    # Intentar descargar con fallback
    soup = descargar_pagina_con_fallback(url_principal, url_fallback)
    if not soup:
        print(f"No se pudo descargar ninguna página para el año {anio}")
        return
    
    # Usar extractor apropiado según el año
    if anio >= 1990:
        singles = extraer_number_ones_spain_moderno(soup, anio)
    else:
        singles = extraer_number_ones_spain_historico(soup, anio)
    
    if singles:
        # Añadir géneros a cada single
        print(f"\n=== Obteniendo géneros para {len(singles)} singles españoles del año {anio} ===")
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
                sleep(1.5)
        
        # Guardar en base de datos
        insert_spain_singles_to_db(singles)
        
        # Guardar CSV como respaldo
        archivo = os.path.join(OUTPUT_DIR, "spain", f"spain_number_ones_{anio}_con_generos.csv")
        guardar_csv_spain(singles, archivo, "singles")
        
        print(f"Procesados {len(singles)} singles de España para el año {anio}")
    else:
        print(f"No se encontraron datos para España en el año {anio}")

def create_spain_charts_tables():
    """Crea las tablas para almacenar los datos de charts españoles"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla para singles número 1 de España
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spain_charts_singles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            año INTEGER NOT NULL,
            semana TEXT,
            fecha TEXT,
            título TEXT NOT NULL,
            artista TEXT NOT NULL,
            tipo_chart TEXT NOT NULL CHECK(tipo_chart IN ('Streaming/Sales', 'Radio', 'Singles')),
            posición INTEGER DEFAULT 1,
            género TEXT,
            artist_id INTEGER,
            song_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    ''')
    
    # Tabla para álbumes número 1 de España (para años posteriores)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spain_charts_albums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            año INTEGER NOT NULL,
            semana TEXT,
            fecha TEXT,
            título TEXT NOT NULL,
            artista TEXT NOT NULL,
            posición INTEGER DEFAULT 1,
            género TEXT,
            artist_id INTEGER,
            album_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (album_id) REFERENCES albums(id)
        )
    ''')
    
    # Índices para mejorar rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spain_singles_artist ON spain_charts_singles(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spain_singles_year ON spain_charts_singles(año)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spain_singles_tipo ON spain_charts_singles(tipo_chart)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spain_albums_artist ON spain_charts_albums(artista)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spain_albums_year ON spain_charts_albums(año)')
    
    conn.commit()
    conn.close()
    print("Tablas de charts españoles creadas correctamente")

def insert_spain_singles_to_db(singles_data):
    """Inserta datos de singles españoles en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for single in singles_data:
        # Buscar IDs relacionados
        artist_id = find_artist_id(single['artista'])
        song_id = find_song_id(single['título'], single['artista'])
        
        # Verificar si ya existe este registro
        cursor.execute("""
            SELECT id FROM spain_charts_singles 
            WHERE año = ? AND título = ? AND artista = ? AND tipo_chart = ? AND 
                  COALESCE(semana, '') = COALESCE(?, '') AND COALESCE(fecha, '') = COALESCE(?, '')
        """, (single['año'], single['título'], single['artista'], single['tipo_chart'], 
              single.get('semana'), single.get('fecha')))
        
        if not cursor.fetchone():  # Si no existe, insertar
            cursor.execute("""
                INSERT INTO spain_charts_singles 
                (año, semana, fecha, título, artista, tipo_chart, posición, género, artist_id, song_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                single['año'],
                single.get('semana'),
                single.get('fecha'),
                single['título'],
                single['artista'],
                single['tipo_chart'],
                single.get('posición', 1),
                single.get('género', 'N/A'),
                artist_id,
                song_id
            ))
            inserted_count += 1
    
    conn.commit()
    conn.close()
    print(f"Insertados {inserted_count} singles españoles en la base de datos")
    return inserted_count

def guardar_csv_spain(datos, archivo, tipo):
    """
    Guarda los datos españoles en un archivo CSV.
    
    Args:
        datos (list): Lista de diccionarios con los datos a guardar
        archivo (str): Nombre del archivo CSV a crear
        tipo (str): Tipo de datos (singles, albums)
    """
    if not datos:
        print(f"No hay datos para guardar en {archivo}")
        return
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    
    # Determinar los encabezados según el tipo de datos
    if tipo == "singles":
        encabezados = ['año', 'semana', 'fecha', 'título', 'artista', 'tipo_chart', 'posición', 'género']
    elif tipo == "albums":
        encabezados = ['año', 'semana', 'fecha', 'título', 'artista', 'posición', 'género']
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
        
        print(f"Datos españoles guardados correctamente en {archivo} ({len(datos)} registros)")
    except Exception as e:
        print(f"Error al guardar el archivo CSV {archivo}: {e}")

def obtener_años_disponibles_spain():
    """
    Devuelve la lista de años disponibles para los charts españoles.
    
    Returns:
        list: Lista de años disponibles (1959-2024)
    """
    return list(range(1959, 2025))

def verificar_datos_existentes_spain_singles(anio):
    """
    Verifica si ya existen datos de singles españoles para un año específico
    
    Args:
        anio (int): Año a verificar
        
    Returns:
        bool: True si ya existen datos, False si no
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM spain_charts_singles WHERE año = ?", (anio,))
    count = cursor.fetchone()[0]
    
    conn.close()
    
    if count > 0:
        print(f"Ya existen {count} registros de singles españoles para el año {anio}. Saltando...")
        return True
    return False


def main(config=None):
    """
    Función principal requerida por db_creator.py
    """
    print("=== INICIANDO SPAIN_CHARTS ===")
    
    # PRIMERO: Inicializar configuración
    if config:
        print(f"Configuración recibida: {type(config)}")
        print(f"db_path en config: {config.get('db_path', 'NO ENCONTRADO')}")
        init_config(config)
    else:
        print("ERROR: No se recibió configuración")
        init_config()  # Usar configuración por defecto
    
    # SEGUNDO: Verificar configuración
    try:
        verificar_configuracion()
    except ValueError as e:
        print(f"ERROR de configuración: {e}")
        return
    
    # TERCERO: Verificar base de datos
    if not verificar_base_datos():
        print("ERROR: Abortando ejecución por problemas con la base de datos")
        return
    
    # CUARTO: Ejecutar main_spain
    print("Delegando a main_spain...")
    main_spain(config)

def main_spain(config=None):
    """Función principal del script español con soporte para géneros y base de datos"""
    
    print(f"=== MAIN_SPAIN INICIADO ===")
    print(f"DB_PATH actual: {DB_PATH}")
    print(f"CONFIG actual: {CONFIG}")
    
    # Crear tablas de base de datos específicas de España
    create_spain_charts_tables()
    
    # Crear directorios de salida
    os.makedirs(os.path.join(OUTPUT_DIR, "spain"), exist_ok=True)
    
    # Determinar si usar funciones con géneros
    usar_generos = config.get('generos', False) if config else False
    print(f"Usar géneros: {usar_generos}")
    
    # Extraer datos según configuración
    if config and config.get('type') == 'all':
        # Extraer todos los años disponibles
        if usar_generos:
            print("Extrayendo todos los datos españoles CON información de géneros...")
        else:
            print("Extrayendo todos los datos españoles SIN información de géneros...")
        
        años_a_procesar = obtener_años_disponibles_spain()
        print(f"Procesando {len(años_a_procesar)} años: {años_a_procesar[:5]}...{años_a_procesar[-5:]}")
        
        for anio in años_a_procesar:
            print(f"\n--- Procesando año {anio} ---")
            if usar_generos:
                procesar_singles_spain_anio_con_genero_db(anio)
            else:
                procesar_singles_spain_anio_db(anio)
            time.sleep(config.get('rate_limit', 1.5))  # Pausa configurable
            
    elif config and config.get('year'):
        # Extraer año específico
        anio = config.get('year')
        print(f"Procesando año específico: {anio}")
        if usar_generos:
            procesar_singles_spain_anio_con_genero_db(anio)
        else:
            procesar_singles_spain_anio_db(anio)
    else:
        print("Configuración no válida para charts españoles")
        print("Usa 'type': 'all' para extraer todos los años")
        print("O especifica 'year': XXXX para un año específico")