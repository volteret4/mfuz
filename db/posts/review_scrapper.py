#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import sys
import urllib.parse
import os
import sqlite3
import time
import json
import argparse
import datetime
from urllib.parse import urlparse, quote_plus
import traceback
import re
import random
from concurrent.futures import ThreadPoolExecutor, as_completed


# Importamos aclarar_contenido.py para usar su función
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))
import tools.aclarar_contenido

# Shared base utilities
_DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _DB_DIR not in sys.path:
    sys.path.insert(0, _DB_DIR)
from base.api_cache import APICache
from base.db_connection import apply_pragmas

# URL de la instancia SearXNG selfhosteada (sin barra final)
SEARXNG_URL = "http://localhost:8485"

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
_session = requests.Session()
_session.headers.update(_HEADERS)
_cache = APICache(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.cache', 'review_cache.sqlite'))


def verificar_y_crear_tablas(conn, cursor):
    """
    Verifica y crea todas las tablas necesarias si no existen

    Args:
        conn: Conexión a la base de datos
        cursor: Cursor de la base de datos

    Returns:
        bool: True si todo se creó correctamente
    """
    try:
        # Crear tabla feeds básica si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                feed_name TEXT NOT NULL,
                post_title TEXT NOT NULL,
                post_url TEXT NOT NULL,
                post_date TIMESTAMP,
                content TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ Tabla feeds verificada/creada")

        # Crear columna origen si no existe
        crear_columna_origen_si_no_existe(cursor)

        # Crear tabla album_metacritic si no existe
        crear_tabla_metacritic(cursor)

        # Crear tabla album_aoty si no existe
        crear_tabla_aoty(cursor)

        # Crear tabla de historial de búsquedas si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS album_search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                album_id INTEGER NOT NULL,
                origen_fuente TEXT NOT NULL,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(album_id, origen_fuente)
            )
        """)
        print("✓ Tabla album_search_history verificada/creada")

        # Commit de todas las creaciones
        conn.commit()
        print("✓ Todas las tablas verificadas/creadas exitosamente")
        return True

    except sqlite3.Error as e:
        print(f"Error al verificar/crear tablas: {e}")
        conn.rollback()
        return False



def buscar_album_en_db(conn, cursor, album_id, album_name, artist_name, content_service, archivo_errores=None):
    """
    Busca un álbum en AnyDecentMusic y guarda las reseñas encontradas
    """
    # Resto de la función original...
    termino_busqueda = artist_name
    url_busqueda = f"http://www.anydecentmusic.com/search-results.aspx?search={urllib.parse.quote(termino_busqueda)}"

    print(f"Buscando álbum: {album_name}")
    print(f"Artista: {artist_name}")
    print(f"URL de búsqueda: {url_busqueda}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        respuesta = _session.get(url_busqueda, headers=headers)
        respuesta.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al realizar la petición: {e}")
        return 0

    soup = BeautifulSoup(respuesta.text, 'html.parser')
    resultados = soup.select('form > div > div > div > ul > li > div')

    if not resultados:
        print("No se encontraron resultados para la búsqueda.")
        return 0

    print(f"Se encontraron {len(resultados)} resultados.")

    album_encontrado = False
    enlaces_guardados = 0

    for idx, resultado in enumerate(resultados, 1):
        artista_elemento = resultado.select_one('a:nth-of-type(2) > h2')
        album_elemento = resultado.select_one('a:nth-of-type(3) > h3')

        if artista_elemento and album_elemento:
            nombre_artista = artista_elemento.text.strip()
            nombre_album = album_elemento.text.strip()

            print(f"Resultado {idx}: {nombre_artista} - {nombre_album}")

            if (artist_name.lower() in nombre_artista.lower() and
                album_name.lower() in nombre_album.lower()):
                print(f"¡Coincidencia encontrada! Artista: {nombre_artista}, Álbum: {nombre_album}")
                album_encontrado = True

                album_url_elemento = resultado.select_one('a:nth-of-type(3)')
                if album_url_elemento and album_url_elemento.has_attr('href'):
                    album_url = album_url_elemento['href']
                    album_url_completa = f"http://www.anydecentmusic.com/{album_url}"
                    print(f"URL del álbum: {album_url_completa}")

                    enlaces_validos, enlaces_error = extraer_enlaces_album(album_url_completa)

                    if archivo_errores and enlaces_error:
                        guardar_errores_enlace(archivo_errores, nombre_artista, nombre_album, enlaces_error)

                    if enlaces_validos:
                        print(f"Se encontraron {len(enlaces_validos)} enlaces de reseñas.")

                        for enlace in enlaces_validos:
                            url = enlace['url']
                            estado = enlace['estado']

                            print(f"Procesando enlace: {url}")

                            feed_name = extraer_dominio(url)
                            post_title = obtener_titulo_pagina(url)
                            contenido = extraer_contenido_con_aclarar(url, content_service)

                            if contenido:
                                post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                guardado = guardar_feed(conn, cursor, 'album', album_id, feed_name,
                                                      post_title, url, post_date, contenido)

                                if guardado:
                                    enlaces_guardados += 1
                                    print(f"Reseña guardada: {feed_name} - {post_title}")
                            else:
                                print(f"No se pudo extraer contenido de {url}")
                    else:
                        print("No se encontraron enlaces de reseñas válidos.")

    if not album_encontrado:
        print(f"No se encontró el álbum '{album_name}' para el artista '{artist_name}'.")

    return enlaces_guardados



def extraer_enlaces_album(url_album):
    """
    Accede a la página del álbum y extrae todos los enlaces "Read Review".
    Verifica también si los enlaces están activos, retornan 404 o redireccionan.
    También registra errores no estándar (diferentes de 404 o 403).

    Args:
        url_album (str): URL de la página del álbum

    Returns:
        tuple: (enlaces_validos, enlaces_error) donde ambos son listas de enlaces
    """
    print(f"Accediendo a la página del álbum: {url_album}")

    # Realizar la petición HTTP
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        respuesta = _session.get(url_album, headers=headers)
        respuesta.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a la página del álbum: {e}")
        return [], []

    # Parsear el HTML
    soup = BeautifulSoup(respuesta.text, 'html.parser')

    # Buscar todos los elementos de la lista que contienen los enlaces
    elementos_lista = soup.select('form > div > div > div > ol > li')

    enlaces_validos = []
    enlaces_error = []
    total_enlaces = 0
    total_read_review = 0
    to_check = []  # (idx, texto, url_completa, url_original)

    for idx, elemento in enumerate(elementos_lista, 1):
        # Buscar el enlace dentro de cada elemento de la lista
        enlace_elemento = elemento.select_one('p > a')
        if enlace_elemento and enlace_elemento.has_attr('href'):
            total_enlaces += 1
            url = enlace_elemento['href']
            texto = enlace_elemento.text.strip()

            # Solo procesar los enlaces "Read Review"
            if "Read Review" in texto:
                total_read_review += 1

                # CORRECCIÓN: Verificar y construir la URL completa correctamente
                if url.startswith('http://') or url.startswith('https://'):
                    url_completa = url
                elif url.startswith('/'):
                    url_completa = f"http://www.anydecentmusic.com{url}"
                else:
                    # Si no tiene protocolo ni empieza con /, agregar el prefijo completo
                    url_completa = f"http://www.anydecentmusic.com/{url}"

                # VALIDACIÓN ADICIONAL: Verificar que la URL sea válida antes de hacer la petición
                try:
                    parsed_url = urllib.parse.urlparse(url_completa)
                    if not parsed_url.scheme or not parsed_url.netloc:
                        print(f"URL inválida detectada: {url_completa}")
                        estado = "URL inválida"
                        enlaces_error.append({
                            'numero': idx,
                            'texto': texto,
                            'url': url_completa,
                            'estado': estado,
                            'url_original': url
                        })
                        continue
                except Exception as url_parse_error:
                    print(f"Error al parsear URL: {url_completa} - {url_parse_error}")
                    estado = f"Error de parsing URL: {str(url_parse_error)}"
                    enlaces_error.append({
                        'numero': idx,
                        'texto': texto,
                        'url': url_completa,
                        'estado': estado,
                        'url_original': url
                    })
                    continue

                to_check.append((idx, texto, url_completa, url))

    # Parallel HEAD checks for all format-valid URLs
    def _head_check(item):
        i, txt, url_c, url_orig = item
        try:
            resp = _session.head(url_c, allow_redirects=True, timeout=10)
            return i, txt, url_c, url_orig, resp.status_code, resp.url, None
        except requests.exceptions.RequestException as e:
            return i, txt, url_c, url_orig, None, url_c, str(e)

    with ThreadPoolExecutor(max_workers=8) as executor:
        for future in as_completed(executor.submit(_head_check, item) for item in to_check):
            idx, texto, url_completa, url_orig, status_code, final_url, error = future.result()
            if error is not None:
                estado = f"Error al verificar: {error}"
                enlaces_error.append({'numero': idx, 'texto': texto, 'url': url_completa,
                                      'estado': estado, 'excepcion': error, 'url_original': url_orig})
            elif status_code == 200:
                if final_url != url_completa:
                    estado = f"Redirigido a: {final_url}"
                    url_completa = final_url
                else:
                    estado = "Activo"
                enlaces_validos.append({'numero': idx, 'texto': texto, 'url': url_completa,
                                        'estado': estado, 'url_original': url_orig})
            elif status_code in [404, 403]:
                estado = f"Error {status_code} - No disponible"
            else:
                estado = f"Error HTTP: {status_code}"
                enlaces_error.append({'numero': idx, 'texto': texto, 'url': url_completa,
                                      'estado': estado, 'codigo': status_code, 'url_original': url_orig})
            print(f"Enlace {idx}: {texto} - {url_completa} -> {estado}")

    print(f"Total de enlaces: {total_enlaces}")
    print(f"Total de enlaces 'Read Review': {total_read_review}")
    print(f"Enlaces válidos encontrados: {len(enlaces_validos)}")
    print(f"Enlaces con errores no estándar: {len(enlaces_error)}")

    return enlaces_validos, enlaces_error


# También añadir esta función de utilidad para limpiar URLs problemáticas
def limpiar_url(url):
    """
    Limpia y valida una URL antes de usarla

    Args:
        url (str): URL a limpiar

    Returns:
        str or None: URL limpia y válida, o None si no es válida
    """
    try:
        # Decodificar URL encoding si es necesario
        url_decoded = urllib.parse.unquote(url)

        # Validar que no tenga caracteres extraños
        parsed = urllib.parse.urlparse(url_decoded)

        # Verificar que tenga esquema y netloc válidos
        if not parsed.scheme:
            return None
        if not parsed.netloc:
            return None

        # Reconstruir la URL limpia
        url_limpia = urllib.parse.urlunparse(parsed)

        return url_limpia
    except Exception as e:
        print(f"Error limpiando URL {url}: {e}")
        return None

def guardar_errores_enlace(archivo_errores, artista, album, enlaces_error):
    """
    Guarda los enlaces con errores no estándar en un archivo

    Args:
        archivo_errores (str): Ruta al archivo donde guardar los errores
        artista (str): Nombre del artista
        album (str): Nombre del álbum
        enlaces_error (list): Lista de enlaces con errores

    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    if not enlaces_error:
        return True

    try:
        # Crear el directorio si no existe
        directorio = os.path.dirname(archivo_errores)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)

        # Abrir en modo append para no sobrescribir errores anteriores
        with open(archivo_errores, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"Artista: {artista}\n")
            f.write(f"Álbum: {album}\n")
            f.write(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*50}\n\n")

            for enlace in enlaces_error:
                f.write(f"URL: {enlace['url']}\n")
                f.write(f"Texto: {enlace['texto']}\n")
                f.write(f"Estado: {enlace['estado']}\n")

                # Añadir detalles adicionales si están disponibles
                if 'codigo' in enlace:
                    f.write(f"Código HTTP: {enlace['codigo']}\n")
                if 'excepcion' in enlace:
                    f.write(f"Excepción: {enlace['excepcion']}\n")

                f.write("\n")

        print(f"Errores guardados en {archivo_errores}")
        return True
    except Exception as e:
        print(f"Error al guardar errores en archivo: {e}")
        return False


def conectar_db(db_path):
    """
    Establece conexión con la base de datos SQLite

    Args:
        db_path (str): Ruta al archivo de la base de datos

    Returns:
        tuple: Conexión y cursor a la base de datos
    """
    try:
        conn = sqlite3.connect(db_path)
        apply_pragmas(conn)
        conn.row_factory = sqlite3.Row  # Para acceder a las columnas por nombre
        apply_pragmas(conn)
        cursor = conn.cursor()
        return conn, cursor
    except sqlite3.Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        sys.exit(1)

def obtener_albums(cursor):
    """
    Obtiene todos los álbumes de la base de datos

    Args:
        cursor: Cursor de la base de datos

    Returns:
        list: Lista de diccionarios con información de los álbumes
    """
    try:
        # Consulta para obtener álbumes con artista principal
        cursor.execute("""
            SELECT albums.id, albums.name, artists.name as artist_name
            FROM albums
            JOIN artists ON albums.artist_id = artists.id
            ORDER BY albums.id
        """)

        albums = []
        for row in cursor.fetchall():
            albums.append({
                'id': row['id'],
                'name': row['name'],
                'artist': row['artist_name']
            })

        print(f"Se encontraron {len(albums)} álbumes en la base de datos")
        return albums
    except sqlite3.Error as e:
        print(f"Error al obtener álbumes: {e}")
        return []



def extraer_dominio(url):
    """
    Extrae el nombre del dominio de una URL

    Args:
        url (str): URL completa

    Returns:
        str: Nombre del dominio (ej: 'pitchfork.com')
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        # Eliminar 'www.' si existe
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception as e:
        print(f"Error al extraer dominio de {url}: {e}")
        return "unknown_domain"

def obtener_titulo_pagina(url):
    """
    Intenta obtener el título de una página web

    Args:
        url (str): URL de la página

    Returns:
        str: Título de la página o una cadena predeterminada
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')

        if title_tag and title_tag.text:
            # Limpiar el título eliminando saltos de línea y espacios excesivos
            title = re.sub(r'\s+', ' ', title_tag.text).strip()
            return title

        # Si no hay título, extraer el dominio y crear un título genérico
        domain = extraer_dominio(url)
        return f"Review on {domain}"
    except Exception as e:
        print(f"Error al obtener título de {url}: {e}")
        domain = extraer_dominio(url)
        return f"Review on {domain}"

def guardar_feed(conn, cursor, entity_type, entity_id, feed_name, post_title, post_url, post_date, content):
    """
    Guarda la información de una reseña en la tabla feeds

    Args:
        conn: Conexión a la base de datos
        cursor: Cursor de la base de datos
        entity_type (str): Tipo de entidad ('album')
        entity_id (int): ID de la entidad
        feed_name (str): Nombre del feed (dominio)
        post_title (str): Título del post
        post_url (str): URL del post
        post_date (str): Fecha del post (o None)
        content (str): Contenido del post

    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    try:
        # Verificar si ya existe una entrada para esta URL
        cursor.execute("""
            SELECT id FROM feeds
            WHERE entity_type = ? AND entity_id = ? AND post_url = ?
        """, (entity_type, entity_id, post_url))

        existing = cursor.fetchone()

        # Si existe, actualizar
        if existing:
            cursor.execute("""
                UPDATE feeds
                SET feed_name = ?, post_title = ?, post_date = ?, content = ?, added_date = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (feed_name, post_title, post_date, content, existing['id']))
            print(f"Actualizada reseña existente para {post_url}")
        else:
            # Si no existe, insertar nuevo
            cursor.execute("""
                INSERT INTO feeds (entity_type, entity_id, feed_name, post_title, post_url, post_date, content, added_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (entity_type, entity_id, feed_name, post_title, post_url, post_date, content))
            print(f"Insertada nueva reseña para {post_url}")

        return True
    except sqlite3.Error as e:
        print(f"Error al guardar en base de datos: {e}")
        conn.rollback()
        return False

def extraer_contenido_con_aclarar(url, service_type):
    """
    Extrae el contenido de una URL usando aclarar_contenido.py

    Args:
        url (str): URL de la página
        service_type (str): Tipo de servicio a usar ('five_filters', 'mercury', 'readability')

    Returns:
        str: Contenido extraído o None si hubo un error
    """
    try:
        raw_content = tools.aclarar_contenido.get_full_content(url, service_type)

        # Procesar según el tipo de servicio
        if service_type in ['mercury', 'readability']:
            # Estos servicios devuelven JSON
            if isinstance(raw_content, dict):
                if service_type == 'mercury' and 'content' in raw_content:
                    # Convertir HTML a texto plano básico
                    soup = BeautifulSoup(raw_content['content'], 'html.parser')
                    return soup.get_text(separator='\n\n')
                elif service_type == 'readability' and 'content' in raw_content:
                    soup = BeautifulSoup(raw_content['content'], 'html.parser')
                    return soup.get_text(separator='\n\n')

            # Falló la conversión o estructura inesperada
            print(f"Estructura inesperada en la respuesta de {service_type}")
            return None
        else:
            # Five Filters devuelve texto
            return raw_content
    except Exception as e:
        print(f"Error al extraer contenido con aclarar_contenido.py: {e}")
        traceback.print_exc()
        return None





# METACRITIC

# Función para crear la tabla album_metacritic
def crear_tabla_metacritic(cursor):
    """
    Crea la tabla album_metacritic si no existe
    """
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS album_metacritic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                album_id INTEGER NOT NULL,
                metascore INTEGER,
                num_critics INTEGER DEFAULT 0,
                positive_reviews INTEGER DEFAULT 0,
                mixed_reviews INTEGER DEFAULT 0,
                negative_reviews INTEGER DEFAULT 0,
                metacritic_url TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (album_id) REFERENCES albums(id),
                UNIQUE(album_id)
            )
        """)
        print("Tabla album_metacritic creada o verificada")
        return True
    except sqlite3.Error as e:
        print(f"Error al crear tabla album_metacritic: {e}")
        return False




def guardar_datos_metacritic(conn, cursor, album_id, datos_metacritic):
    """
    Guarda los datos de Metacritic en la base de datos

    Args:
        conn: Conexión a la base de datos
        cursor: Cursor de la base de datos
        album_id (int): ID del álbum
        datos_metacritic (dict): Datos extraídos de Metacritic

    Returns:
        bool: True si se guardó correctamente
    """
    try:
        # Verificar si ya existe
        cursor.execute("SELECT id FROM album_metacritic WHERE album_id = ?", (album_id,))
        existing = cursor.fetchone()

        if existing:
            # Actualizar
            cursor.execute("""
                UPDATE album_metacritic
                SET metascore = ?, num_critics = ?, positive_reviews = ?,
                    mixed_reviews = ?, negative_reviews = ?, metacritic_url = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE album_id = ?
            """, (
                datos_metacritic['metascore'],
                datos_metacritic['num_critics'],
                datos_metacritic['positive_reviews'],
                datos_metacritic['mixed_reviews'],
                datos_metacritic['negative_reviews'],
                datos_metacritic['metacritic_url'],
                album_id
            ))
            print(f"Datos de Metacritic actualizados para álbum ID {album_id}")
        else:
            # Insertar nuevo
            cursor.execute("""
                INSERT INTO album_metacritic
                (album_id, metascore, num_critics, positive_reviews, mixed_reviews, negative_reviews, metacritic_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                album_id,
                datos_metacritic['metascore'],
                datos_metacritic['num_critics'],
                datos_metacritic['positive_reviews'],
                datos_metacritic['mixed_reviews'],
                datos_metacritic['negative_reviews'],
                datos_metacritic['metacritic_url']
            ))
            print(f"Datos de Metacritic insertados para álbum ID {album_id}")

        return True

    except sqlite3.Error as e:
        print(f"Error guardando datos de Metacritic: {e}")
        conn.rollback()
        return False



def limpiar_nombre_para_url(nombre):
    """
    Limpia un nombre de artista o álbum para usarlo en URLs de Metacritic

    Args:
        nombre (str): Nombre a limpiar

    Returns:
        str: Nombre limpio para URL
    """
    # Convertir a minúsculas
    nombre = nombre.lower()

    # Reemplazar caracteres especiales y espacios
    nombre = re.sub(r'[^\w\s-]', '', nombre)  # Eliminar caracteres especiales excepto guiones y espacios
    nombre = re.sub(r'\s+', '-', nombre)       # Reemplazar espacios con guiones
    nombre = re.sub(r'-+', '-', nombre)        # Eliminar guiones múltiples
    nombre = nombre.strip('-')                 # Eliminar guiones al inicio y final

    return nombre

def construir_url_metacritic_directa(artist_name, album_name):
    """
    Construye la URL directa de Metacritic basada en el patrón conocido

    Args:
        artist_name (str): Nombre del artista
        album_name (str): Nombre del álbum

    Returns:
        str: URL directa de Metacritic
    """
    artist_clean = limpiar_nombre_para_url(artist_name)
    album_clean = limpiar_nombre_para_url(album_name)

    # Patrón de Metacritic: /music/[album-name]/[artist-name]
    url = f"https://www.metacritic.com/music/{album_clean}/{artist_clean}"

    return url

def verificar_url_metacritic(url):
    """
    Versión mejorada de verificación que es más tolerante

    Args:
        url (str): URL a verificar

    Returns:
        bool: True si la URL existe y es válida
    """
    try:
        response = _session.head(url, timeout=15, allow_redirects=True)

        # Aceptar tanto 200 como algunos otros códigos válidos
        if response.status_code in [200, 301, 302]:
            # Verificar que la URL final siga siendo de Metacritic
            if 'metacritic.com' in response.url and '/music/' in response.url:
                return True

        return False
    except:
        return False

def buscar_album_metacritic_mejorado(artist_name, album_name):
    """
    Versión mejorada con múltiples métodos y anti-detección
    """
    print(f"Buscando en Metacritic: {artist_name} - {album_name}")

    # Método 1: URL directa (más rápido, sin scraping)
    print("Probando URL directa primero...")
    url_directa = construir_url_metacritic_directa(artist_name, album_name)
    if verificar_url_metacritic(url_directa):
        print(f"✓ Encontrado en URL directa: {url_directa}")
        return url_directa

    # Delay aleatorio antes de scraping
    delay = random.uniform(2, 5)
    print(f"Esperando {delay:.1f} segundos...")
    time.sleep(delay)

    # Método 2: DuckDuckGo con anti-detección
    print("Probando con DuckDuckGo...")
    metacritic_url = buscar_metacritic_con_duckduckgo(artist_name, album_name)
    if metacritic_url:
        return metacritic_url

    # Método 3: Google como fallback
    # print("Probando con Google como fallback...")
    # metacritic_url = buscar_metacritic_con_google_scraping(artist_name, album_name)
    # if metacritic_url:
    #     return metacritic_url

    # Método 4: Variaciones de URL directa
    print("Probando variaciones de URL directa...")
    variaciones_album = generar_variaciones_nombre(album_name)[:2]
    variaciones_artista = generar_variaciones_nombre(artist_name)[:2]

    for album_var in variaciones_album:
        for artist_var in variaciones_artista:
            url_directa = construir_url_metacritic_directa(artist_var, album_var)

            # Delay pequeño entre intentos
            time.sleep(random.uniform(0.5, 1.5))

            if verificar_url_metacritic(url_directa):
                print(f"✓ Encontrado en variación directa: {url_directa}")
                return url_directa

    print(f"✗ No se encontró el álbum en Metacritic")
    return None
def procesar_albums(db_path, content_service, archivo_errores=None, inicio_id=0, lote=50, pausa=2):
    """
    Procesa múltiples álbumes para buscar sus reseñas
    """
    conn, cursor = conectar_db(db_path)

    # Verificar y crear todas las tablas necesarias al inicio
    if not verificar_y_crear_tablas(conn, cursor):
        print("❌ Error al verificar/crear tablas. Abortando.")
        conn.close()
        return 0, 0

    # Obtener todos los álbumes
    todos_albums = obtener_albums(cursor)

    # Filtrar álbumes para comenzar desde inicio_id
    albums_a_procesar = [a for a in todos_albums if a['id'] >= inicio_id]

    print(f"Se procesarán {len(albums_a_procesar)} álbumes, comenzando desde ID {inicio_id}")

    # Estadísticas
    albums_procesados = 0
    resenas_totales = 0

    # Procesar por lotes
    for i in range(0, len(albums_a_procesar), lote):
        lote_actual = albums_a_procesar[i:i+lote]
        print(f"\n=== Procesando lote {i//lote + 1} ({len(lote_actual)} álbumes) ===")

        for album in lote_actual:
            print(f"\nProcesando álbum ID {album['id']}: {album['artist']} - {album['name']}")

            # Buscar reseñas para este álbum
            resenas = buscar_album_en_db(conn, cursor, album['id'], album['name'],
                                       album['artist'], content_service, archivo_errores)

            # Actualizar estadísticas
            albums_procesados += 1
            resenas_totales += resenas

            # Pausa para evitar sobrecargar el servidor
            if albums_procesados < len(albums_a_procesar):
                print(f"Esperando {pausa} segundos antes de la próxima búsqueda...")
                time.sleep(pausa)

        # Resumen del lote
        print(f"\n--- Resumen lote {i//lote + 1} ---")
        print(f"Álbumes procesados: {albums_procesados}")
        print(f"Reseñas encontradas: {resenas_totales}")

    # Cerrar conexión
    conn.close()

    return albums_procesados, resenas_totales

# Añadir estas opciones a tu configuración
def procesar_albums_con_anti_deteccion(db_path, content_service, config):
    """
    Versión mejorada del procesador con anti-detección
    """
    # Nuevas configuraciones
    use_proxy = config.get('use_proxy', False)
    proxy_list = config.get('proxy_list', [])
    max_intentos_por_sesion = config.get('max_intentos_por_sesion', 20)
    pausa_entre_sesiones = config.get('pausa_entre_sesiones', 300)  # 5 minutos

    intentos_sesion = 0
    intentos_fallidos = 0

    for album in albums_a_procesar:
        # Verificar límite de intentos por sesión
        if intentos_sesion >= max_intentos_por_sesion:
            print(f"\n⏸️ Límite de sesión alcanzado. Pausando {pausa_entre_sesiones/60:.1f} minutos...")
            time.sleep(pausa_entre_sesiones)
            intentos_sesion = 0
            intentos_fallidos = 0

        # Procesar álbum con manejo de errores
        try:
            resultado = buscar_album_metacritic_mejorado(
                album['artist'],
                album['name']
            )

            if resultado:
                intentos_fallidos = 0  # Reset en éxito
            else:
                intentos_fallidos += 1
                manejar_rate_limiting(intentos_fallidos)

            intentos_sesion += 1

        except Exception as e:
            print(f"Error procesando álbum: {e}")
            intentos_fallidos += 1
            manejar_rate_limiting(intentos_fallidos)


def manejar_rate_limiting(intentos_fallidos):
    """
    Implementa backoff exponencial para rate limiting

    Args:
        intentos_fallidos (int): Número de intentos fallidos consecutivos
    """
    if intentos_fallidos > 0:
        # Backoff exponencial con jitter
        base_delay = min(2 ** intentos_fallidos, 60)  # Máximo 60 segundos
        jitter = random.uniform(0, base_delay * 0.3)
        total_delay = base_delay + jitter

        print(f"⏳ Rate limiting: esperando {total_delay:.1f} segundos (intento {intentos_fallidos})...")
        time.sleep(total_delay)


def buscar_album_metacritic_fallback(artist_name, album_name):
    """
    Búsqueda de fallback usando el buscador de Metacritic

    Args:
        artist_name (str): Nombre del artista
        album_name (str): Nombre del álbum

    Returns:
        str or None: URL del álbum en Metacritic si se encuentra
    """
    query = f"{artist_name} {album_name}".strip()
    search_url = f"https://www.metacritic.com/search/music/{quote_plus(query)}/results"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Buscando con el buscador de Metacritic: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Buscar enlaces de resultados de música
        result_links = soup.find_all('a', href=True)

        for link in result_links:
            href = link['href']
            if '/music/' in href and href.count('/') >= 3:  # Formato /music/album/artist
                # Construir URL completa si es relativa
                if href.startswith('/'):
                    result_url = f"https://www.metacritic.com{href}"
                else:
                    result_url = href

                # Verificar que no sea una página de artista
                if not result_url.endswith('/critic-reviews/') and '/artist/' not in result_url:
                    print(f"Encontrado resultado de búsqueda: {result_url}")

                    # Verificar que la URL sea válida
                    if verificar_url_metacritic(result_url):
                        return result_url

        print(f"No se encontró '{album_name}' de '{artist_name}' en el buscador de Metacritic")
        return None

    except Exception as e:
        print(f"Error en búsqueda de fallback en Metacritic: {e}")
        return None

def extraer_datos_metacritic_mejorado(metacritic_url):
    """
    Versión mejorada para extraer datos de Metacritic con mejor detección de elementos

    Args:
        metacritic_url (str): URL de la página del álbum en Metacritic

    Returns:
        dict: Diccionario con los datos extraídos o None si hay error
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Extrayendo datos de: {metacritic_url}")
        response = requests.get(metacritic_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        datos = {
            'metascore': None,
            'num_critics': 0,
            'positive_reviews': 0,
            'mixed_reviews': 0,
            'negative_reviews': 0,
            'metacritic_url': metacritic_url
        }

        # Extraer Metascore - múltiples selectores posibles
        metascore_selectors = [
            'div.metascore_w',
            'span.metascore_w',
            '.c-siteReviewScore_background-critic_medium',
            '.c-siteReviewScore_background-critic_large',
            '.metascore_w'
        ]

        metascore_elem = None
        for selector in metascore_selectors:
            metascore_elem = soup.select_one(selector)
            if metascore_elem:
                break

        if metascore_elem:
            try:
                metascore_text = metascore_elem.get_text().strip()
                datos['metascore'] = int(re.search(r'\d+', metascore_text).group())
                print(f"Metascore encontrado: {datos['metascore']}")
            except (ValueError, AttributeError):
                print("No se pudo extraer el Metascore del elemento encontrado")

        # Buscar información de críticos y distribución
        page_text = soup.get_text()

        # Buscar "Based on X Critic Reviews" o "X Critic Reviews"
        critics_patterns = [
            r'Based on (\d+) Critic Review',
            r'(\d+) Critic Review',
            r'(\d+) critic review'
        ]

        for pattern in critics_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                datos['num_critics'] = int(match.group(1))
                print(f"Número de críticos: {datos['num_critics']}")
                break

        # Buscar distribución de reseñas
        # Patrones para buscar distribución
        positive_patterns = [
            r'(\d+)\s+Positive',
            r'Positive[:\s]+(\d+)',
            r'(\d+)\s+positive'
        ]

        mixed_patterns = [
            r'(\d+)\s+Mixed',
            r'Mixed[:\s]+(\d+)',
            r'(\d+)\s+mixed'
        ]

        negative_patterns = [
            r'(\d+)\s+Negative',
            r'Negative[:\s]+(\d+)',
            r'(\d+)\s+negative'
        ]

        # Buscar distribución con patrones
        for pattern in positive_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                datos['positive_reviews'] = int(match.group(1))
                break

        for pattern in mixed_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                datos['mixed_reviews'] = int(match.group(1))
                break

        for pattern in negative_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                datos['negative_reviews'] = int(match.group(1))
                break

        print(f"Datos extraídos: Metascore={datos['metascore']}, Critics={datos['num_critics']}, Positive={datos['positive_reviews']}, Mixed={datos['mixed_reviews']}, Negative={datos['negative_reviews']}")

        return datos

    except Exception as e:
        print(f"Error extrayendo datos de Metacritic: {e}")
        return None

# Actualizar la función principal para usar las versiones mejoradas
def buscar_album_en_db_con_metacritic_mejorado(conn, cursor, album_id, album_name, artist_name, content_service, include_metacritic=True, archivo_errores=None):
    """
    Versión mejorada con mejor búsqueda en Metacritic
    """
    enlaces_guardados = 0

    # Búsqueda original en AnyDecentMusic
    enlaces_guardados += buscar_album_en_db(conn, cursor, album_id, album_name, artist_name, content_service, archivo_errores)

    # Nueva búsqueda en Metacritic
    if include_metacritic:
        print(f"\n--- Buscando en Metacritic: {artist_name} - {album_name} ---")

        # Usar la función mejorada de búsqueda
        metacritic_url = buscar_album_metacritic_mejorado(artist_name, album_name)

        if metacritic_url:
            # Extraer datos de Metacritic con la función mejorada
            datos_metacritic = extraer_datos_metacritic_mejorado(metacritic_url)

            if datos_metacritic:
                # Guardar en la tabla album_metacritic
                if guardar_datos_metacritic(conn, cursor, album_id, datos_metacritic):
                    print(f"✓ Datos de Metacritic guardados para {artist_name} - {album_name}")

                # También guardar la página como una reseña en feeds si tiene contenido útil
                if datos_metacritic['metascore'] is not None:
                    post_title = f"Metacritic Reviews - {artist_name} - {album_name} (Score: {datos_metacritic['metascore']})"
                    content = f"Metacritic Score: {datos_metacritic['metascore']}/100\n"
                    content += f"Based on {datos_metacritic['num_critics']} critic reviews\n"
                    content += f"Positive: {datos_metacritic['positive_reviews']}, "
                    content += f"Mixed: {datos_metacritic['mixed_reviews']}, "
                    content += f"Negative: {datos_metacritic['negative_reviews']}"

                    post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    if guardar_feed(conn, cursor, 'album', album_id, 'metacritic.com',
                                  post_title, metacritic_url, post_date, content):
                        enlaces_guardados += 1
                        print(f"✓ Reseña de Metacritic guardada en feeds")
            else:
                print("No se pudieron extraer datos de la página de Metacritic")
        else:
            print(f"✗ No se encontró el álbum en Metacritic")

    return enlaces_guardados

# Actualizar la función procesar_albums_con_metacritic para usar la versión mejorada
def procesar_albums_con_metacritic_mejorado(db_path, content_service, include_metacritic=True, archivo_errores=None, inicio_id=0, lote=50, pausa=2):
    """
    Versión mejorada de procesar_albums que incluye mejor búsqueda en Metacritic
    """
    conn, cursor = conectar_db(db_path)

    # Crear tabla de Metacritic si no existe
    if include_metacritic:
        crear_tabla_metacritic(cursor)
        conn.commit()

    # Obtener todos los álbumes
    todos_albums = obtener_albums(cursor)

    # Filtrar álbumes para comenzar desde inicio_id
    albums_a_procesar = [a for a in todos_albums if a['id'] >= inicio_id]

    print(f"Se procesarán {len(albums_a_procesar)} álbumes, comenzando desde ID {inicio_id}")
    if include_metacritic:
        print("✓ Incluye búsqueda MEJORADA en Metacritic")

    # Estadísticas
    albums_procesados = 0
    resenas_totales = 0
    metacritic_encontrados = 0

    # Procesar por lotes
    for i in range(0, len(albums_a_procesar), lote):
        lote_actual = albums_a_procesar[i:i+lote]
        print(f"\n{'='*60}")
        print(f"PROCESANDO LOTE {i//lote + 1} ({len(lote_actual)} álbumes)")
        print(f"{'='*60}")

        for album in lote_actual:
            print(f"\n🎵 Procesando álbum ID {album['id']}: {album['artist']} - {album['name']}")

            # Buscar reseñas para este álbum (incluyendo Metacritic mejorado)
            resenas = buscar_album_en_db_con_metacritic_mejorado(
                conn, cursor, album['id'], album['name'], album['artist'],
                content_service, include_metacritic, archivo_errores
            )

            # Verificar si se encontró en Metacritic
            if include_metacritic:
                cursor.execute("SELECT metascore FROM album_metacritic WHERE album_id = ?", (album['id'],))
                if cursor.fetchone():
                    metacritic_encontrados += 1

            # Actualizar estadísticas
            albums_procesados += 1
            resenas_totales += resenas

            # Pausa para evitar sobrecargar el servidor
            if albums_procesados < len(albums_a_procesar):
                print(f"⏳ Esperando {pausa} segundos antes de la próxima búsqueda...")
                time.sleep(pausa)

        # Resumen del lote
        print(f"\n--- RESUMEN LOTE {i//lote + 1} ---")
        print(f"✓ Álbumes procesados: {albums_procesados}")
        print(f"✓ Reseñas encontradas: {resenas_totales}")
        if include_metacritic:
            print(f"✓ Encontrados en Metacritic: {metacritic_encontrados}")
        print(f"{'='*40}")

    # Cerrar conexión
    conn.close()

    return albums_procesados, resenas_totales, metacritic_encontrados

def extraer_enlaces_reviews_metacritic(metacritic_url):
    """
    Extrae todos los enlaces a reseñas individuales de una página de Metacritic

    Args:
        metacritic_url (str): URL de la página del álbum en Metacritic

    Returns:
        tuple: (enlaces_validos, enlaces_error) donde ambos son listas de enlaces
    """
    print(f"Extrayendo enlaces de reseñas de Metacritic: {metacritic_url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(metacritic_url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a Metacritic: {e}")
        return [], []

    soup = BeautifulSoup(response.text, 'html.parser')

    enlaces_validos = []
    enlaces_error = []

    # Buscar reseñas de críticos - múltiples selectores posibles
    review_selectors = [
        # Selectores modernos de Metacritic
        '.c-siteReview',
        '.review.critic_review',
        '.critic_reviews .review',
        # Selectores clásicos
        '.critic_review',
        '.review_wrap',
        '.review_section .review'
    ]

    reviews_found = []
    for selector in review_selectors:
        reviews_found = soup.select(selector)
        if reviews_found:
            print(f"Encontradas {len(reviews_found)} reseñas usando selector: {selector}")
            break

    if not reviews_found:
        print("No se encontraron reseñas en la página")
        return [], []

    for idx, review in enumerate(reviews_found, 1):
        try:
            # Buscar enlace externo a la reseña original
            link_selectors = [
                'a.c-siteReview_externalLink',
                'a[href*="http"]:not([href*="metacritic.com"])',  # Enlaces externos
                '.review_critic a[href*="http"]',
                '.source a',
                'a.external_link',
                'a[target="_blank"]'
            ]

            enlace_review = None
            for link_selector in link_selectors:
                enlace_review = review.select_one(link_selector)
                if enlace_review and enlace_review.has_attr('href'):
                    break

            if not enlace_review or not enlace_review.has_attr('href'):
                continue

            url_review = enlace_review['href']

            # Verificar que sea una URL externa válida
            if not url_review.startswith('http'):
                continue
            if 'metacritic.com' in url_review:
                continue

            # Obtener información de la publicación
            publication_selectors = [
                '.c-siteReview_source',
                '.review_critic .source',
                '.source',
                '.critic .source',
                '.review_publication'
            ]

            publication_elem = None
            for pub_selector in publication_selectors:
                publication_elem = review.select_one(pub_selector)
                if publication_elem:
                    break

            publication_name = publication_elem.text.strip() if publication_elem else extraer_dominio(url_review)

            # Obtener puntuación si está disponible
            score_selectors = [
                '.c-siteReview_score',
                '.metascore_w',
                '.review_grade',
                '.score'
            ]

            score_elem = None
            for score_selector in score_selectors:
                score_elem = review.select_one(score_selector)
                if score_elem:
                    break

            score = score_elem.text.strip() if score_elem else None

            print(f"Encontrada reseña {idx}: {publication_name} - {url_review}")

            # Verificar si el enlace está activo
            success, resp_or_error, final_url = validar_y_hacer_peticion(url_review, headers)

            if success and resp_or_error.status_code == 200:
                estado = "Activo"
                if final_url != url_review:
                    estado = f"Redirigido a: {final_url}"
                    url_review = final_url

                enlaces_validos.append({
                    'numero': idx,
                    'publication': publication_name,
                    'url': url_review,
                    'estado': estado,
                    'score': score
                })
            elif success and resp_or_error.status_code in [404, 403]:
                # Enlaces muertos, no los registramos como error
                print(f"Enlace muerto (HTTP {resp_or_error.status_code}): {url_review}")
            else:
                error_msg = resp_or_error if not success else f"HTTP {resp_or_error.status_code}"
                enlaces_error.append({
                    'numero': idx,
                    'publication': publication_name,
                    'url': url_review,
                    'estado': error_msg,
                    'score': score
                })

        except Exception as e:
            print(f"Error procesando reseña {idx}: {e}")
            continue

    print(f"Total de enlaces válidos encontrados: {len(enlaces_validos)}")
    print(f"Total de enlaces con errores: {len(enlaces_error)}")

    return enlaces_validos, enlaces_error




def procesar_reviews_metacritic_mejorado(conn, cursor, album_id, metacritic_url, content_service):
    """
    Versión mejorada que procesa reseñas de Metacritic con filtrado de URLs
    """
    enlaces_validos, enlaces_error = extraer_enlaces_reviews_metacritic(metacritic_url)

    # Filtrar enlaces válidos para reseñas
    enlaces_validos = filtrar_enlaces_validos_para_reviews(enlaces_validos)

    if enlaces_error:
        print(f"Se encontraron {len(enlaces_error)} enlaces con errores en Metacritic")

    reviews_guardadas = 0

    for enlace in enlaces_validos:
        url = enlace['url']
        publication = enlace['publication']
        score = enlace.get('score')

        print(f"Procesando reseña de {publication}: {url}")

        try:
            # Usar la nueva función de extracción específica por sitio
            contenido = extraer_contenido_segun_sitio(url, content_service)

            if contenido:
                # Crear título para la reseña
                post_title = f"{publication} Review"
                if score:
                    post_title += f" (Score: {score})"

                # Fecha actual
                post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Guardar en la tabla feeds
                feed_name = extraer_dominio(url)

                guardado = guardar_feed(
                    conn, cursor, 'album', album_id, feed_name,
                    post_title, url, post_date, contenido
                )

                if guardado:
                    reviews_guardadas += 1
                    print(f"✓ Reseña guardada: {publication} - {post_title}")
                else:
                    print(f"✗ Error guardando reseña de {publication}")
            else:
                print(f"✗ No se pudo extraer contenido de {publication}: {url}")

        except Exception as e:
            print(f"✗ Error procesando reseña de {publication}: {e}")
            continue

    print(f"Total de reseñas guardadas desde Metacritic: {reviews_guardadas}")
    return reviews_guardadas




def buscar_album_en_db_con_metacritic_completo_mejorado(conn, cursor, album_id, album_name, artist_name, content_service, include_metacritic=True, archivo_errores=None):
    """
    Versión mejorada completa que extrae tanto datos de Metacritic como todas sus reseñas individuales con filtrado
    """
    enlaces_guardados = 0

    # Búsqueda mejorada en AnyDecentMusic
    try:
        enlaces_guardados += buscar_album_en_db_mejorado(conn, cursor, album_id, album_name, artist_name, content_service, archivo_errores)
    except Exception as e:
        print(f"Error en búsqueda AnyDecentMusic: {e}")

    # Nueva búsqueda completa en Metacritic
    if include_metacritic:
        print(f"\n{'='*60}")
        print(f"🎯 PROCESANDO METACRITIC: {artist_name} - {album_name}")
        print(f"{'='*60}")

        metacritic_url = buscar_album_metacritic_mejorado(artist_name, album_name)

        if metacritic_url:
            print(f"✓ Álbum encontrado en Metacritic: {metacritic_url}")

            # 1. Extraer y guardar datos básicos de Metacritic
            datos_metacritic = extraer_datos_metacritic_mejorado(metacritic_url)

            if datos_metacritic:
                if guardar_datos_metacritic(conn, cursor, album_id, datos_metacritic):
                    print(f"✓ Datos básicos de Metacritic guardados")

                # Guardar resumen como entrada en feeds
                if datos_metacritic['metascore'] is not None:
                    post_title = f"Metacritic Summary - {artist_name} - {album_name} (Score: {datos_metacritic['metascore']})"
                    content = f"Metacritic Score: {datos_metacritic['metascore']}/100\n"
                    content += f"Based on {datos_metacritic['num_critics']} critic reviews\n"
                    content += f"Distribution:\n"
                    content += f"  Positive (75-100): {datos_metacritic['positive_reviews']} reviews\n"
                    content += f"  Mixed (50-74): {datos_metacritic['mixed_reviews']} reviews\n"
                    content += f"  Negative (0-49): {datos_metacritic['negative_reviews']} reviews"

                    post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    if guardar_feed(conn, cursor, 'album', album_id, 'metacritic.com',
                                  post_title, metacritic_url, post_date, content):
                        enlaces_guardados += 1

            # 2. Procesar todas las reseñas individuales de Metacritic con filtrado mejorado
            print(f"\n🔍 Buscando reseñas individuales en Metacritic...")
            reviews_procesadas = procesar_reviews_metacritic_mejorado(conn, cursor, album_id, metacritic_url, content_service)
            enlaces_guardados += reviews_procesadas

            if reviews_procesadas > 0:
                print(f"✓ {reviews_procesadas} reseñas individuales procesadas desde Metacritic")
            else:
                print(f"⚠️  No se encontraron reseñas individuales en Metacritic")

        else:
            print(f"✗ No se encontró el álbum en Metacritic")

    return enlaces_guardados


def validar_y_hacer_peticion(url, headers, timeout=10):
    """
    Valida una URL y hace una petición HEAD de forma segura

    Args:
        url (str): URL a verificar
        headers (dict): Headers HTTP
        timeout (int): Timeout en segundos

    Returns:
        tuple: (success, response_or_error_message, final_url)
    """
    try:
        # Validar URL primero
        url_limpia = limpiar_url(url)
        if not url_limpia:
            return False, "URL inválida", url

        # Hacer la petición
        resp = requests.head(
            url_limpia,
            headers=headers,
            allow_redirects=True,
            timeout=timeout
        )

        return True, resp, resp.url

    except requests.exceptions.ConnectionError as e:
        return False, f"Error de conexión: {str(e)}", url
    except requests.exceptions.Timeout:
        return False, "Timeout de conexión", url
    except requests.exceptions.RequestException as e:
        return False, f"Error de petición: {str(e)}", url
    except Exception as e:
        return False, f"Error inesperado: {str(e)}", url

# AOTY

# FUNCIONES PARA ALBUM OF THE YEAR (AOTY)
# Agregar estas funciones a tu review_scrapper.py

def limpiar_nombre_para_aoty(nombre):
    """
    Limpia un nombre de artista o álbum para busqueda en AOTY

    Args:
        nombre (str): Nombre a limpiar

    Returns:
        str: Nombre limpio para búsqueda
    """
    # Convertir a minúsculas
    nombre = nombre.lower()

    # Reemplazar caracteres especiales
    nombre = re.sub(r'[^\w\s-]', ' ', nombre)  # Reemplazar especiales con espacios
    nombre = re.sub(r'\s+', ' ', nombre)       # Normalizar espacios
    nombre = nombre.strip()                    # Eliminar espacios al inicio/final

    return nombre


def verificar_url_aoty(url):
    """
    Verifica si una URL de AOTY existe y es válida

    Args:
        url (str): URL a verificar

    Returns:
        bool: True si la URL existe y es válida
    """
    try:
        response = _session.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except:
        return False

def extraer_datos_aoty(aoty_url):
    """
    Extrae los datos básicos de puntuación de una página de AOTY

    Args:
        aoty_url (str): URL de la página del álbum en AOTY

    Returns:
        dict: Diccionario con los datos extraídos o None si hay error
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Extrayendo datos de AOTY: {aoty_url}")
        response = requests.get(aoty_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        datos = {
            'user_score': None,
            'critic_score': None,
            'num_user_ratings': 0,
            'num_critic_ratings': 0,
            'aoty_url': aoty_url
        }

        # Extraer puntuación de usuarios
        user_score_selectors = [
            '.userScore',
            '.albumUserScore',
            'div[class*="userScore"]',
            'span[class*="userScore"]'
        ]

        for selector in user_score_selectors:
            user_score_elem = soup.select_one(selector)
            if user_score_elem:
                try:
                    score_text = user_score_elem.get_text().strip()
                    # Extraer número del texto (puede estar en formato "82" o "8.2/10")
                    score_match = re.search(r'(\d+(?:\.\d+)?)', score_text)
                    if score_match:
                        score = float(score_match.group(1))
                        # Convertir a escala 0-100 si es necesario
                        if score <= 10:
                            score = score * 10
                        datos['user_score'] = int(score)
                        print(f"User Score encontrado: {datos['user_score']}")
                        break
                except (ValueError, AttributeError):
                    continue

        # Extraer puntuación de críticos
        critic_score_selectors = [
            '.criticScore',
            '.albumCriticScore',
            'div[class*="criticScore"]',
            'span[class*="criticScore"]'
        ]

        for selector in critic_score_selectors:
            critic_score_elem = soup.select_one(selector)
            if critic_score_elem:
                try:
                    score_text = critic_score_elem.get_text().strip()
                    score_match = re.search(r'(\d+(?:\.\d+)?)', score_text)
                    if score_match:
                        score = float(score_match.group(1))
                        if score <= 10:
                            score = score * 10
                        datos['critic_score'] = int(score)
                        print(f"Critic Score encontrado: {datos['critic_score']}")
                        break
                except (ValueError, AttributeError):
                    continue

        # Extraer número de ratings
        page_text = soup.get_text()

        # Buscar número de user ratings
        user_ratings_patterns = [
            r'(\d+)\s+user\s+rating',
            r'(\d+)\s+rating',
            r'based\s+on\s+(\d+)\s+rating'
        ]

        for pattern in user_ratings_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                datos['num_user_ratings'] = int(match.group(1))
                print(f"Número de user ratings: {datos['num_user_ratings']}")
                break

        # Buscar número de critic ratings
        critic_ratings_patterns = [
            r'(\d+)\s+critic\s+review',
            r'(\d+)\s+review'
        ]

        for pattern in critic_ratings_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                datos['num_critic_ratings'] = int(match.group(1))
                print(f"Número de critic ratings: {datos['num_critic_ratings']}")
                break

        print(f"Datos extraídos de AOTY: User={datos['user_score']}, Critic={datos['critic_score']}, User Ratings={datos['num_user_ratings']}, Critic Ratings={datos['num_critic_ratings']}")

        return datos

    except Exception as e:
        print(f"Error extrayendo datos de AOTY: {e}")
        return None

def extraer_enlaces_reviews_aoty(aoty_url):
    """
    Extrae todos los enlaces a reseñas externas de una página de AOTY

    Args:
        aoty_url (str): URL de la página del álbum en AOTY

    Returns:
        tuple: (enlaces_validos, enlaces_error) donde ambos son listas de enlaces
    """
    print(f"Extrayendo enlaces de reseñas de AOTY: {aoty_url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(aoty_url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a AOTY: {e}")
        return [], []

    soup = BeautifulSoup(response.text, 'html.parser')

    enlaces_validos = []
    enlaces_error = []

    # Buscar sección de críticas/reseñas
    review_selectors = [
        '.criticReview',
        '.reviewEntry',
        '.criticEntry',
        'div[class*="review"]',
        'div[class*="critic"]'
    ]

    reviews_found = []
    for selector in review_selectors:
        reviews_found = soup.select(selector)
        if reviews_found:
            print(f"Encontradas {len(reviews_found)} reseñas usando selector: {selector}")
            break

    # Si no encontramos con selectores específicos, buscar enlaces externos
    if not reviews_found:
        # Buscar enlaces que parezcan ser de reseñas externas
        external_links = soup.find_all('a', href=True)
        potential_reviews = []

        for link in external_links:
            href = link['href']
            # Filtrar enlaces que parezcan reseñas externas
            if (href.startswith('http') and
                not any(domain in href for domain in ['albumoftheyear.org', 'facebook.com', 'twitter.com', 'instagram.com']) and
                any(keyword in href.lower() for keyword in ['review', 'music', 'album', 'pitchfork', 'rolling', 'guardian', 'nme'])):
                potential_reviews.append(link)

        reviews_found = potential_reviews[:10]  # Limitar a 10 resultados
        print(f"Encontrados {len(reviews_found)} enlaces externos potenciales")

    if not reviews_found:
        print("No se encontraron reseñas en la página de AOTY")
        return [], []

    for idx, review in enumerate(reviews_found, 1):
        try:
            # Si es un enlace directo
            if review.name == 'a' and review.has_attr('href'):
                url_review = review['href']
                publication_name = review.get_text().strip() or extraer_dominio(url_review)
            else:
                # Buscar enlace dentro del elemento de reseña
                link_elem = review.find('a', href=True)
                if not link_elem:
                    continue

                url_review = link_elem['href']

                # Buscar nombre de la publicación
                publication_elem = review.find(class_=re.compile(r'publication|source|site'))
                if not publication_elem:
                    publication_elem = review.find('span')

                publication_name = publication_elem.get_text().strip() if publication_elem else extraer_dominio(url_review)

            # Verificar que sea una URL externa válida
            if not url_review.startswith('http'):
                if url_review.startswith('//'):
                    url_review = 'https:' + url_review
                elif url_review.startswith('/'):
                    continue  # Enlace interno, saltarlo
                else:
                    url_review = 'https://' + url_review

            # Excluir enlaces internos de AOTY
            if 'albumoftheyear.org' in url_review:
                continue

            print(f"Encontrada reseña {idx}: {publication_name} - {url_review}")

            # Verificar si el enlace está activo
            success, resp_or_error, final_url = validar_y_hacer_peticion(url_review, headers)

            if success and resp_or_error.status_code == 200:
                estado = "Activo"
                if final_url != url_review:
                    estado = f"Redirigido a: {final_url}"
                    url_review = final_url

                enlaces_validos.append({
                    'numero': idx,
                    'publication': publication_name,
                    'url': url_review,
                    'estado': estado
                })
            elif success and resp_or_error.status_code in [404, 403]:
                # Enlaces muertos, no los registramos como error
                print(f"Enlace muerto (HTTP {resp_or_error.status_code}): {url_review}")
            else:
                error_msg = resp_or_error if not success else f"HTTP {resp_or_error.status_code}"
                enlaces_error.append({
                    'numero': idx,
                    'publication': publication_name,
                    'url': url_review,
                    'estado': error_msg
                })

        except Exception as e:
            print(f"Error procesando reseña {idx}: {e}")
            continue

    print(f"Total de enlaces válidos encontrados en AOTY: {len(enlaces_validos)}")
    print(f"Total de enlaces con errores en AOTY: {len(enlaces_error)}")

    return enlaces_validos, enlaces_error

def crear_tabla_aoty(cursor):
    """
    Crea la tabla album_aoty si no existe
    """
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS album_aoty (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                album_id INTEGER NOT NULL,
                user_score INTEGER,
                critic_score INTEGER,
                num_user_ratings INTEGER DEFAULT 0,
                num_critic_ratings INTEGER DEFAULT 0,
                aoty_url TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (album_id) REFERENCES albums(id),
                UNIQUE(album_id)
            )
        """)
        print("Tabla album_aoty creada o verificada")
        return True
    except sqlite3.Error as e:
        print(f"Error al crear tabla album_aoty: {e}")
        return False

def guardar_datos_aoty(conn, cursor, album_id, datos_aoty):
    """
    Guarda los datos de AOTY en la base de datos

    Args:
        conn: Conexión a la base de datos
        cursor: Cursor de la base de datos
        album_id (int): ID del álbum
        datos_aoty (dict): Datos extraídos de AOTY

    Returns:
        bool: True si se guardó correctamente
    """
    try:
        # Verificar si ya existe
        cursor.execute("SELECT id FROM album_aoty WHERE album_id = ?", (album_id,))
        existing = cursor.fetchone()

        if existing:
            # Actualizar
            cursor.execute("""
                UPDATE album_aoty
                SET user_score = ?, critic_score = ?, num_user_ratings = ?,
                    num_critic_ratings = ?, aoty_url = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE album_id = ?
            """, (
                datos_aoty['user_score'],
                datos_aoty['critic_score'],
                datos_aoty['num_user_ratings'],
                datos_aoty['num_critic_ratings'],
                datos_aoty['aoty_url'],
                album_id
            ))
            print(f"Datos de AOTY actualizados para álbum ID {album_id}")
        else:
            # Insertar nuevo
            cursor.execute("""
                INSERT INTO album_aoty
                (album_id, user_score, critic_score, num_user_ratings, num_critic_ratings, aoty_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                album_id,
                datos_aoty['user_score'],
                datos_aoty['critic_score'],
                datos_aoty['num_user_ratings'],
                datos_aoty['num_critic_ratings'],
                datos_aoty['aoty_url']
            ))
            print(f"Datos de AOTY insertados para álbum ID {album_id}")

        return True

    except sqlite3.Error as e:
        print(f"Error guardando datos de AOTY: {e}")
        conn.rollback()
        return False



def procesar_reviews_aoty_mejorado(conn, cursor, album_id, aoty_url, content_service):
    """
    Versión mejorada que procesa reseñas de AOTY con filtrado de URLs
    """
    enlaces_validos, enlaces_error = extraer_enlaces_reviews_aoty(aoty_url)

    # Filtrar enlaces válidos para reseñas
    enlaces_validos = filtrar_enlaces_validos_para_reviews(enlaces_validos)

    if enlaces_error:
        print(f"Se encontraron {len(enlaces_error)} enlaces con errores en AOTY")

    reviews_guardadas = 0

    for enlace in enlaces_validos:
        url = enlace['url']
        publication = enlace['publication']

        print(f"Procesando reseña de {publication}: {url}")

        try:
            # Usar la nueva función de extracción específica por sitio
            contenido = extraer_contenido_segun_sitio(url, content_service)

            if contenido:
                # Crear título para la reseña
                post_title = f"{publication} Review (via AOTY)"

                # Fecha actual
                post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Guardar en la tabla feeds
                feed_name = extraer_dominio(url)

                guardado = guardar_feed(
                    conn, cursor, 'album', album_id, feed_name,
                    post_title, url, post_date, contenido
                )

                if guardado:
                    reviews_guardadas += 1
                    print(f"✓ Reseña guardada: {publication} - {post_title}")
                else:
                    print(f"✗ Error guardando reseña de {publication}")
            else:
                print(f"✗ No se pudo extraer contenido de {publication}: {url}")

        except Exception as e:
            print(f"✗ Error procesando reseña de {publication}: {e}")
            continue

    print(f"Total de reseñas guardadas desde AOTY: {reviews_guardadas}")
    return reviews_guardadas




def buscar_album_en_db_completo_mejorado(conn, cursor, album_id, album_name, artist_name, content_service,
                               include_metacritic=True, include_aoty=True, archivo_errores=None,
                               google_api_key=None, google_cx=None):
    """
    Versión mejorada completa con filtrado de URLs de streaming
    """
    enlaces_guardados = 0

    # 1. Búsqueda mejorada en AnyDecentMusic
    try:
        print(f"\n🌍 Buscando en AnyDecentMusic...")
        enlaces_guardados += buscar_album_en_db_mejorado(conn, cursor, album_id, album_name, artist_name, content_service, archivo_errores)
    except Exception as e:
        print(f"Error en búsqueda AnyDecentMusic: {e}")

    # 2. Búsqueda completa en Metacritic
    if include_metacritic:
        print(f"\n🎯 Buscando en Metacritic...")
        try:
            metacritic_url = buscar_album_metacritic_mejorado(artist_name, album_name)

            if metacritic_url:
                print(f"✓ Álbum encontrado en Metacritic: {metacritic_url}")

                # Extraer y guardar datos básicos de Metacritic
                datos_metacritic = extraer_datos_metacritic_mejorado(metacritic_url)

                if datos_metacritic:
                    if guardar_datos_metacritic(conn, cursor, album_id, datos_metacritic):
                        print(f"✓ Datos básicos de Metacritic guardados")

                    # Guardar resumen como entrada en feeds
                    if datos_metacritic['metascore'] is not None:
                        post_title = f"Metacritic Summary - {artist_name} - {album_name} (Score: {datos_metacritic['metascore']})"
                        content = f"Metacritic Score: {datos_metacritic['metascore']}/100\n"
                        content += f"Based on {datos_metacritic['num_critics']} critic reviews\n"
                        content += f"Distribution: +{datos_metacritic['positive_reviews']} ±{datos_metacritic['mixed_reviews']} -{datos_metacritic['negative_reviews']}"

                        post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        if guardar_feed(conn, cursor, 'album', album_id, 'metacritic.com',
                                      post_title, metacritic_url, post_date, content):
                            enlaces_guardados += 1

                # Procesar reseñas individuales de Metacritic con filtrado mejorado
                print(f"🔍 Buscando reseñas individuales en Metacritic...")
                reviews_procesadas = procesar_reviews_metacritic_mejorado(conn, cursor, album_id, metacritic_url, content_service)
                enlaces_guardados += reviews_procesadas

                if reviews_procesadas > 0:
                    print(f"✓ {reviews_procesadas} reseñas individuales procesadas desde Metacritic")
                else:
                    print(f"⚠️  No se encontraron reseñas individuales en Metacritic")
            else:
                print(f"✗ No se encontró el álbum en Metacritic")
        except Exception as e:
            print(f"Error en búsqueda Metacritic: {e}")

    # 3. Búsqueda completa en Album of the Year (AOTY)
    if include_aoty:
        print(f"\n🏆 Buscando en Album of the Year...")
        try:
            aoty_url = buscar_album_aoty(artist_name, album_name, google_api_key, google_cx)

            if aoty_url:
                print(f"✓ Álbum encontrado en AOTY: {aoty_url}")

                # Extraer y guardar datos básicos de AOTY
                datos_aoty = extraer_datos_aoty(aoty_url)

                if datos_aoty:
                    if guardar_datos_aoty(conn, cursor, album_id, datos_aoty):
                        print(f"✓ Datos básicos de AOTY guardados")
                        print(f"   User Score: {datos_aoty['user_score']}")
                        print(f"   Critic Score: {datos_aoty['critic_score']}")

                    # Guardar resumen como entrada en feeds
                    if datos_aoty['user_score'] is not None or datos_aoty['critic_score'] is not None:
                        scores_text = []
                        if datos_aoty['user_score']:
                            scores_text.append(f"User: {datos_aoty['user_score']}")
                        if datos_aoty['critic_score']:
                            scores_text.append(f"Critic: {datos_aoty['critic_score']}")

                        post_title = f"AOTY Summary - {artist_name} - {album_name} ({'/'.join(scores_text)})"
                        content = f"Album of the Year Scores:\n"
                        if datos_aoty['user_score']:
                            content += f"User Score: {datos_aoty['user_score']}/100 (based on {datos_aoty['num_user_ratings']} ratings)\n"
                        if datos_aoty['critic_score']:
                            content += f"Critic Score: {datos_aoty['critic_score']}/100 (based on {datos_aoty['num_critic_ratings']} reviews)\n"

                        post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        if guardar_feed(conn, cursor, 'album', album_id, 'albumoftheyear.org',
                                      post_title, aoty_url, post_date, content):
                            enlaces_guardados += 1

                # Procesar reseñas individuales de AOTY con filtrado mejorado
                print(f"🔍 Buscando reseñas individuales en AOTY...")
                reviews_procesadas = procesar_reviews_aoty_mejorado(conn, cursor, album_id, aoty_url, content_service)
                enlaces_guardados += reviews_procesadas

                if reviews_procesadas > 0:
                    print(f"✓ {reviews_procesadas} reseñas individuales procesadas desde AOTY")
                else:
                    print(f"⚠️  No se encontraron reseñas individuales en AOTY")
            else:
                print(f"✗ No se encontró el álbum en Album of the Year")
        except Exception as e:
            print(f"Error en búsqueda AOTY: {e}")

    return enlaces_guardados




def buscar_album_aoty_con_google(artist_name, album_name, google_api_key=None, google_cx=None):
    """
    Busca un álbum en Album of the Year usando Google Search como método principal

    Args:
        artist_name (str): Nombre del artista
        album_name (str): Nombre del álbum
        google_api_key (str): API key de Google (opcional)
        google_cx (str): Custom Search Engine ID (opcional)

    Returns:
        str or None: URL del álbum en AOTY si se encuentra
    """
    print(f"Buscando en Album of the Year: {artist_name} - {album_name}")

    # Método 1: Búsqueda con Google Custom Search (si está disponible)
    if google_api_key and google_cx:
        try:
            aoty_url = buscar_aoty_con_google_api(artist_name, album_name, google_api_key, google_cx)
            if aoty_url:
                return aoty_url
        except Exception as e:
            print(f"Error con Google API, probando método directo: {e}")

    # Método 2: Búsqueda directa simulando Google
    try:
        aoty_url = buscar_aoty_simulando_google(artist_name, album_name)
        if aoty_url:
            return aoty_url
    except Exception as e:
        print(f"Error con búsqueda simulada de Google: {e}")

    # Método 3: Búsqueda original en AOTY (fallback)
    try:
        return buscar_album_aoty_original(artist_name, album_name)
    except Exception as e:
        print(f"Error con búsqueda original AOTY: {e}")
        return None

def buscar_aoty_con_google_api(artist_name, album_name, api_key, cx):
    """
    Busca usando la API oficial de Google Custom Search
    """
    import requests

    query = f'site:albumoftheyear.org "{artist_name}" "{album_name}"'
    url = "https://www.googleapis.com/customsearch/v1"

    params = {
        'key': api_key,
        'cx': cx,
        'q': query,
        'num': 5
    }

    print(f"Buscando con Google API: {query}")

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    if 'items' in data:
        for item in data['items']:
            url = item['link']
            if '/album/' in url and 'albumoftheyear.org' in url:
                if verificar_url_aoty(url):
                    print(f"✓ Encontrado con Google API: {url}")
                    return url

    return None

def buscar_aoty_simulando_google(artist_name, album_name):
    """
    Busca simulando una búsqueda de Google con site:albumoftheyear.org
    """
    import requests
    from urllib.parse import quote_plus

    # Diferentes variaciones de la consulta
    queries = [
        f'site:albumoftheyear.org "{artist_name}" "{album_name}"',
        f'site:albumoftheyear.org {artist_name} {album_name}',
        f'site:albumoftheyear.org "{album_name}" {artist_name}',
        f'site:albumoftheyear.org {album_name}'
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    for query in queries:
        try:
            print(f"Probando consulta Google: {query}")

            # Usar DuckDuckGo como alternativa más confiable
            search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"

            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar enlaces en los resultados
            links = soup.find_all('a', href=True)

            for link in links:
                href = link['href']

                # Limpiar URL de DuckDuckGo (suelen estar en formato /l/?uddg=...)
                if '/l/?uddg=' in href:
                    import urllib.parse
                    try:
                        href = urllib.parse.unquote(href.split('uddg=')[1].split('&')[0])
                    except:
                        continue

                if 'albumoftheyear.org' in href and '/album/' in href:
                    # Limpiar URL
                    if href.startswith('http'):
                        clean_url = href.split('&')[0]  # Eliminar parámetros adicionales

                        if verificar_url_aoty(clean_url):
                            print(f"✓ Encontrado con DuckDuckGo: {clean_url}")
                            return clean_url

            # Pequeña pausa entre consultas
            import time
            time.sleep(1)

        except Exception as e:
            print(f"Error en consulta '{query}': {e}")
            continue

    return None

def buscar_album_aoty_original(artist_name, album_name):
    """
    Versión original de búsqueda directa en AOTY (como fallback)
    """
    print(f"Usando búsqueda directa en AOTY como último recurso...")

    # Limpiar nombres para la búsqueda
    artist_clean = limpiar_nombre_para_aoty(artist_name)
    album_clean = limpiar_nombre_para_aoty(album_name)

    # Crear query de búsqueda
    query = f"{artist_clean} {album_clean}".strip()
    search_url = f"https://www.albumoftheyear.org/search/albums/?q={quote_plus(query)}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        print(f"URL de búsqueda directa: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Intentar múltiples selectores para encontrar resultados
        selectors_to_try = [
            'div.albumBlock a[href*="/album/"]',
            'a[href*="/album/"]',
            '.searchResult a',
            '.albumEntry a',
            'div.album a',
            '.result a'
        ]

        album_links = []
        for selector in selectors_to_try:
            links = soup.select(selector)
            if links:
                album_links = links
                print(f"Encontrados {len(links)} enlaces con selector: {selector}")
                break

        # Si aún no encontramos nada, buscar todos los enlaces que contengan /album/
        if not album_links:
            all_links = soup.find_all('a', href=True)
            album_links = [link for link in all_links if '/album/' in link.get('href', '')]
            print(f"Encontrados {len(album_links)} enlaces de álbum mediante búsqueda general")

        # Verificar cada resultado
        for link in album_links[:5]:  # Solo verificar los primeros 5
            href = link['href']

            if href.startswith('/'):
                result_url = f"https://www.albumoftheyear.org{href}"
            else:
                result_url = href

            if verificar_url_aoty(result_url):
                print(f"✓ Primer resultado válido en búsqueda directa: {result_url}")
                return result_url

        return None

    except Exception as e:
        print(f"Error en búsqueda directa AOTY: {e}")
        return None

# Actualizar la función principal para usar la nueva búsqueda
def buscar_album_aoty(artist_name, album_name, google_api_key=None, google_cx=None):
    """
    Función principal actualizada que usa los métodos mejorados
    """
    return buscar_album_aoty_mejorado_v2(artist_name, album_name, google_api_key, google_cx)




def es_url_valida_para_reviews(url):
    """
    Verifica si una URL es válida para extraer reseñas (evita URLs de streaming)

    Args:
        url (str): URL a verificar

    Returns:
        bool: True si es válida para reseñas, False si debe ser evitada
    """
    urls_a_evitar = [
        'music.apple.com',
        'open.spotify.com',
        'spotify.com/album',
        'spotify.com/artist',
        'music.amazon.com',
        'tidal.com',
        'deezer.com',
        'youtube.com/playlist',
        'youtube.com/channel',
        'bandcamp.com/track',  # Solo evitar tracks individuales, no álbumes
        'soundcloud.com/sets'  # Solo evitar sets, no tracks individuales
    ]

    url_lower = url.lower()

    for url_evitar in urls_a_evitar:
        if url_evitar in url_lower:
            print(f"⚠️  URL evitada (streaming/no-review): {url}")
            return False

    return True

def extraer_contenido_segun_sitio(url, content_service):
    """
    Extrae contenido específico según el sitio web

    Args:
        url (str): URL de la página
        content_service (str): Servicio base para extraer contenido

    Returns:
        str: Contenido extraído o None si hubo un error
    """
    try:
        # Verificar si es una URL que debemos evitar
        if not es_url_valida_para_reviews(url):
            return None

        domain = extraer_dominio(url)
        print(f"Extrayendo contenido de {domain}: {url}")

        # Extracciones específicas por sitio
        if 'allmusic.com' in domain:
            return extraer_contenido_allmusic(url)
        elif 'sputnikmusic.com' in domain:
            return extraer_contenido_sputnikmusic(url)
        elif 'pitchfork.com' in domain:
            return extraer_contenido_pitchfork(url)
        elif 'rollingstone.com' in domain:
            return extraer_contenido_rollingstone(url)
        elif 'nme.com' in domain:
            return extraer_contenido_nme(url)
        else:
            # Para otros sitios, usar el método general
            return extraer_contenido_con_aclarar(url, content_service)

    except Exception as e:
        print(f"Error extrayendo contenido específico de {url}: {e}")
        # Fallback al método general
        return extraer_contenido_con_aclarar(url, content_service)

def extraer_contenido_allmusic(url):
    """
    Extrae específicamente las reseñas de AllMusic

    Args:
        url (str): URL de AllMusic

    Returns:
        str: Contenido de la reseña o None
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Selectores específicos para reseñas de AllMusic
        review_selectors = [
            'div.review',
            'section.review',
            'div.editorial-review',
            'div[class*="review"]',
            'div.content .text',
            'section[class*="editorial"]',
            '.review-content',
            'div.album-review'
        ]

        review_content = None

        for selector in review_selectors:
            review_element = soup.select_one(selector)
            if review_element:
                # Limpiar el contenido
                # Remover elementos no deseados
                for unwanted in review_element.find_all(['script', 'style', 'nav', 'aside']):
                    unwanted.decompose()

                review_text = review_element.get_text(separator='\n\n').strip()

                # Verificar que tenga contenido sustancial (más de 100 caracteres)
                if len(review_text) > 100:
                    review_content = review_text
                    print(f"✓ Reseña extraída de AllMusic usando selector: {selector}")
                    break

        # Si no encontramos reseña específica, buscar párrafos largos
        if not review_content:
            paragraphs = soup.find_all('p')
            long_paragraphs = []

            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 150:  # Párrafos largos que probablemente sean reseña
                    long_paragraphs.append(text)

            if long_paragraphs:
                # Tomar los párrafos más largos (probablemente la reseña)
                review_content = '\n\n'.join(long_paragraphs[:3])
                print(f"✓ Reseña extraída de AllMusic usando párrafos largos")

        if review_content and len(review_content) > 50:
            return f"AllMusic Review:\n\n{review_content}"
        else:
            print("⚠️  No se encontró contenido de reseña específico en AllMusic")
            return None

    except Exception as e:
        print(f"Error extrayendo contenido de AllMusic: {e}")
        return None

def extraer_contenido_sputnikmusic(url):
    """
    Extrae específicamente las reseñas de SputnikMusic

    Args:
        url (str): URL de SputnikMusic

    Returns:
        str: Contenido de la reseña o None
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Selectores específicos para reseñas de SputnikMusic
        review_selectors = [
            'div#review_text',
            'div.review_text',
            'div.reviewcontent',
            'div[class*="review"]',
            '#reviewbody',
            '.review-body',
            'div.main_review'
        ]

        review_content = None

        for selector in review_selectors:
            review_element = soup.select_one(selector)
            if review_element:
                # Limpiar el contenido
                for unwanted in review_element.find_all(['script', 'style', 'nav', 'aside', 'div.comments']):
                    unwanted.decompose()

                review_text = review_element.get_text(separator='\n\n').strip()

                # Verificar que tenga contenido sustancial
                if len(review_text) > 200:
                    review_content = review_text
                    print(f"✓ Reseña extraída de SputnikMusic usando selector: {selector}")
                    break

        # Método alternativo: buscar el texto principal de la reseña
        if not review_content:
            # SputnikMusic suele tener la reseña en divs específicos
            main_content = soup.find('div', {'id': 'main'}) or soup.find('div', {'class': 'main'})

            if main_content:
                # Buscar párrafos largos dentro del contenido principal
                paragraphs = main_content.find_all('p')
                review_paragraphs = []

                for p in paragraphs:
                    text = p.get_text().strip()
                    if len(text) > 100:
                        review_paragraphs.append(text)

                if review_paragraphs:
                    review_content = '\n\n'.join(review_paragraphs)
                    print(f"✓ Reseña extraída de SputnikMusic usando párrafos del contenido principal")

        if review_content and len(review_content) > 100:
            return f"SputnikMusic Review:\n\n{review_content}"
        else:
            print("⚠️  No se encontró contenido de reseña específico en SputnikMusic")
            return None

    except Exception as e:
        print(f"Error extrayendo contenido de SputnikMusic: {e}")
        return None

def extraer_contenido_pitchfork(url):
    """
    Extrae específicamente las reseñas de Pitchfork

    Args:
        url (str): URL de Pitchfork

    Returns:
        str: Contenido de la reseña o None
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Selectores específicos para Pitchfork
        review_selectors = [
            'div.contents',
            'div.review-content',
            'div[class*="ReviewContent"]',
            'div[class*="review-text"]',
            'article div p',
            '.body-text',
            '.review-detail__text'
        ]

        review_content = None

        for selector in review_selectors:
            elements = soup.select(selector)
            if elements:
                # Para Pitchfork, concatenar varios párrafos
                review_paragraphs = []
                for elem in elements:
                    text = elem.get_text().strip()
                    if len(text) > 50:
                        review_paragraphs.append(text)

                if review_paragraphs:
                    review_content = '\n\n'.join(review_paragraphs[:10])  # Limitar a 10 párrafos
                    print(f"✓ Reseña extraída de Pitchfork usando selector: {selector}")
                    break

        if review_content and len(review_content) > 200:
            return f"Pitchfork Review:\n\n{review_content}"
        else:
            print("⚠️  No se encontró contenido de reseña específico en Pitchfork")
            return None

    except Exception as e:
        print(f"Error extrayendo contenido de Pitchfork: {e}")
        return None

def extraer_contenido_rollingstone(url):
    """
    Extrae específicamente las reseñas de Rolling Stone
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Selectores para Rolling Stone
        review_selectors = [
            'div.entry-content',
            'div.article-content',
            'div[class*="content"]',
            'article div p'
        ]

        for selector in review_selectors:
            elements = soup.select(selector)
            if elements:
                review_paragraphs = []
                for elem in elements:
                    text = elem.get_text().strip()
                    if len(text) > 50:
                        review_paragraphs.append(text)

                if review_paragraphs:
                    review_content = '\n\n'.join(review_paragraphs[:8])
                    print(f"✓ Reseña extraída de Rolling Stone")
                    return f"Rolling Stone Review:\n\n{review_content}"

        return None

    except Exception as e:
        print(f"Error extrayendo contenido de Rolling Stone: {e}")
        return None

def extraer_contenido_nme(url):
    """
    Extrae específicamente las reseñas de NME
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Selectores para NME
        review_selectors = [
            'div.ArticleBody',
            'div.entry-content',
            'div[class*="article-body"]',
            'article div p'
        ]

        for selector in review_selectors:
            elements = soup.select(selector)
            if elements:
                review_paragraphs = []
                for elem in elements:
                    text = elem.get_text().strip()
                    if len(text) > 50:
                        review_paragraphs.append(text)

                if review_paragraphs:
                    review_content = '\n\n'.join(review_paragraphs[:8])
                    print(f"✓ Reseña extraída de NME")
                    return f"NME Review:\n\n{review_content}"

        return None

    except Exception as e:
        print(f"Error extrayendo contenido de NME: {e}")
        return None





def filtrar_enlaces_validos_para_reviews(enlaces_validos):
    """
    Filtra una lista de enlaces válidos eliminando URLs de streaming

    Args:
        enlaces_validos (list): Lista de diccionarios con enlaces

    Returns:
        list: Lista filtrada de enlaces válidos para reseñas
    """
    enlaces_filtrados = []

    for enlace in enlaces_validos:
        url = enlace.get('url', '')

        if es_url_valida_para_reviews(url):
            enlaces_filtrados.append(enlace)
        else:
            print(f"🚫 Enlace filtrado: {enlace.get('publication', 'Unknown')} - {url}")

    print(f"📊 Enlaces después del filtrado: {len(enlaces_filtrados)}/{len(enlaces_validos)}")
    return enlaces_filtrados



def crear_columna_origen_si_no_existe(cursor):
    """
    Añade la columna 'origen' a la tabla feeds si no existe

    Args:
        cursor: Cursor de la base de datos

    Returns:
        bool: True si se creó o ya existía, False si hubo error
    """
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(feeds)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'origen' not in columns:
            print("Añadiendo columna 'origen' a la tabla feeds...")
            cursor.execute("ALTER TABLE feeds ADD COLUMN origen TEXT")
            print("✓ Columna 'origen' añadida exitosamente")
        else:
            print("✓ Columna 'origen' ya existe en la tabla feeds")

        return True
    except sqlite3.Error as e:
        print(f"Error al crear columna origen: {e}")
        return False

def crear_columna_origen_si_no_existe(cursor):
    """
    Añade la columna 'origen' a la tabla feeds si no existe

    Args:
        cursor: Cursor de la base de datos

    Returns:
        bool: True si se creó o ya existía, False si hubo error
    """
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(feeds)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'origen' not in columns:
            print("Añadiendo columna 'origen' a la tabla feeds...")
            cursor.execute("ALTER TABLE feeds ADD COLUMN origen TEXT")
            print("✓ Columna 'origen' añadida exitosamente")
        else:
            print("✓ Columna 'origen' ya existe en la tabla feeds")

        return True
    except sqlite3.Error as e:
        print(f"Error al crear columna origen: {e}")
        return False

MESES_ENTRE_BUSQUEDAS = 6


def registrar_busqueda(conn, cursor, album_id, origen_fuente):
    """
    Registra o actualiza el timestamp de la última búsqueda de un álbum para una fuente.
    """
    try:
        cursor.execute("""
            INSERT INTO album_search_history (album_id, origen_fuente, searched_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(album_id, origen_fuente) DO UPDATE SET searched_at = CURRENT_TIMESTAMP
        """, (album_id, origen_fuente))
    except sqlite3.Error as e:
        print(f"Error registrando búsqueda: {e}")


def verificar_album_ya_procesado(cursor, album_id, origen_fuente):
    """
    Verifica si un álbum fue buscado por una fuente hace menos de MESES_ENTRE_BUSQUEDAS meses.
    Devuelve True (saltar) si se buscó recientemente, False si hay que volver a buscar.
    """
    try:
        cursor.execute("""
            SELECT searched_at FROM album_search_history
            WHERE album_id = ? AND origen_fuente = ?
        """, (album_id, origen_fuente))

        row = cursor.fetchone()
        if not row:
            print(f"   ✓ Álbum ID {album_id} nunca buscado en {origen_fuente}")
            return False

        searched_at = datetime.datetime.fromisoformat(row['searched_at'])
        cutoff = datetime.datetime.now() - datetime.timedelta(days=30 * MESES_ENTRE_BUSQUEDAS)

        if searched_at > cutoff:
            meses = (datetime.datetime.now() - searched_at).days // 30
            print(f"   ⏭️  Álbum ID {album_id} buscado en {origen_fuente} hace {meses} meses — saltando")
            return True
        else:
            print(f"   🔄 Álbum ID {album_id}: búsqueda en {origen_fuente} caducada, volviendo a buscar")
            return False

    except sqlite3.Error as e:
        print(f"Error verificando historial de búsqueda: {e}")
        return False


def guardar_feed_con_origen(conn, cursor, entity_type, entity_id, feed_name, post_title, post_url, post_date, content, origen):
    """
    Versión mejorada de guardar_feed que incluye la columna origen

    Args:
        conn: Conexión a la base de datos
        cursor: Cursor de la base de datos
        entity_type (str): Tipo de entidad ('album')
        entity_id (int): ID de la entidad
        feed_name (str): Nombre del feed (dominio)
        post_title (str): Título del post
        post_url (str): URL del post
        post_date (str): Fecha del post (o None)
        content (str): Contenido del post
        origen (str): Origen de la reseña (review_metacritic, review_aoty, review_anydecentmusic)

    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    try:
        # Verificar si ya existe una entrada para esta URL
        cursor.execute("""
            SELECT id FROM feeds
            WHERE entity_type = ? AND entity_id = ? AND post_url = ?
        """, (entity_type, entity_id, post_url))

        existing = cursor.fetchone()

        # Si existe, actualizar
        if existing:
            cursor.execute("""
                UPDATE feeds
                SET feed_name = ?, post_title = ?, post_date = ?, content = ?, origen = ?, added_date = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (feed_name, post_title, post_date, content, origen, existing['id']))
            print(f"Actualizada reseña existente para {post_url} (origen: {origen})")
        else:
            # Si no existe, insertar nuevo
            cursor.execute("""
                INSERT INTO feeds (entity_type, entity_id, feed_name, post_title, post_url, post_date, content, origen, added_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (entity_type, entity_id, feed_name, post_title, post_url, post_date, content, origen))
            print(f"Insertada nueva reseña para {post_url} (origen: {origen})")

        return True
    except sqlite3.Error as e:
        print(f"Error al guardar en base de datos: {e}")
        conn.rollback()
        return False

# FUNCIONES MEJORADAS CON force_update Y origen

def buscar_album_en_db_mejorado_con_force_update(conn, cursor, album_id, album_name, artist_name, content_service,
                                                force_update=False, archivo_errores=None):
    """
    Versión mejorada de búsqueda en AnyDecentMusic con soporte para force_update y origen
    """
    origen = "review_anydecentmusic"

    # Verificar si ya fue procesado y force_update está desactivado
    if not force_update and verificar_album_ya_procesado(cursor, album_id, origen):
        print(f"   ⏭️  Saltando álbum ID {album_id} - ya procesado por AnyDecentMusic")
        return 0

    # Construir la URL de búsqueda
    termino_busqueda = artist_name
    url_busqueda = f"http://www.anydecentmusic.com/search-results.aspx?search={urllib.parse.quote(termino_busqueda)}"

    print(f"\n🌍 Buscando en AnyDecentMusic: {termino_busqueda}")
    print(f"Álbum objetivo: {album_name}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        respuesta = requests.get(url_busqueda, headers=headers, timeout=15)
        respuesta.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al realizar la petición: {e}")
        return 0

    soup = BeautifulSoup(respuesta.text, 'html.parser')
    resultados = soup.select('form > div > div > div > ul > li > div')

    if not resultados:
        print("No se encontraron resultados para la búsqueda.")
        return 0

    print(f"Se encontraron {len(resultados)} resultados generales.")

    album_encontrado = False
    enlaces_guardados = 0

    # Verificar cada resultado para encontrar coincidencias
    for idx, resultado in enumerate(resultados, 1):
        artista_elemento = resultado.select_one('a:nth-of-type(2) > h2')
        album_elemento = resultado.select_one('a:nth-of-type(3) > h3')

        if artista_elemento and album_elemento:
            nombre_artista = artista_elemento.text.strip()
            nombre_album = album_elemento.text.strip()

            print(f"Resultado {idx}: {nombre_artista} - {nombre_album}")

            if (artist_name.lower() in nombre_artista.lower() and
                album_name.lower() in nombre_album.lower()):
                print(f"¡Coincidencia encontrada! Artista: {nombre_artista}, Álbum: {nombre_album}")
                album_encontrado = True

                album_url_elemento = resultado.select_one('a:nth-of-type(3)')
                if album_url_elemento and album_url_elemento.has_attr('href'):
                    album_url = album_url_elemento['href']
                    album_url_completa = f"http://www.anydecentmusic.com/{album_url}"
                    print(f"URL del álbum: {album_url_completa}")

                    enlaces_validos, enlaces_error = extraer_enlaces_album(album_url_completa)

                    # Filtrar enlaces válidos para reseñas
                    enlaces_validos = filtrar_enlaces_validos_para_reviews(enlaces_validos)

                    if archivo_errores and enlaces_error:
                        guardar_errores_enlace(archivo_errores, nombre_artista, nombre_album, enlaces_error)

                    if enlaces_validos:
                        print(f"Se encontraron {len(enlaces_validos)} enlaces de reseñas válidos.")

                        for enlace in enlaces_validos:
                            url = enlace['url']
                            estado = enlace['estado']

                            print(f"Procesando enlace: {url}")

                            feed_name = extraer_dominio(url)
                            post_title = obtener_titulo_pagina(url)

                            # Usar extracción específica por sitio
                            contenido = extraer_contenido_segun_sitio(url, content_service)

                            if contenido:
                                post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                                # Usar la nueva función con origen
                                guardado = guardar_feed_con_origen(
                                    conn, cursor, 'album', album_id, feed_name,
                                    post_title, url, post_date, contenido, origen
                                )

                                if guardado:
                                    enlaces_guardados += 1
                                    print(f"Reseña guardada: {feed_name} - {post_title}")
                            else:
                                print(f"No se pudo extraer contenido de {url}")
                    else:
                        print("No se encontraron enlaces de reseñas válidos.")

    if not album_encontrado:
        print(f"No se encontró el álbum '{album_name}' para el artista '{artist_name}'.")

    return enlaces_guardados

def procesar_reviews_metacritic_mejorado_con_force_update(conn, cursor, album_id, metacritic_url, content_service, force_update=False):
    """
    Versión mejorada que procesa reseñas de Metacritic con force_update y origen
    """
    origen = "review_metacritic"

    # Verificar si ya fue procesado y force_update está desactivado
    if not force_update and verificar_album_ya_procesado(cursor, album_id, origen):
        print(f"   ⏭️  Saltando reseñas de Metacritic para álbum ID {album_id} - ya procesado")
        return 0

    enlaces_validos, enlaces_error = extraer_enlaces_reviews_metacritic(metacritic_url)

    # Filtrar enlaces válidos para reseñas
    enlaces_validos = filtrar_enlaces_validos_para_reviews(enlaces_validos)

    if enlaces_error:
        print(f"Se encontraron {len(enlaces_error)} enlaces con errores en Metacritic")

    reviews_guardadas = 0

    for enlace in enlaces_validos:
        url = enlace['url']
        publication = enlace['publication']
        score = enlace.get('score')

        print(f"Procesando reseña de {publication}: {url}")

        try:
            # Usar la nueva función de extracción específica por sitio
            contenido = extraer_contenido_segun_sitio(url, content_service)

            if contenido:
                # Crear título para la reseña
                post_title = f"{publication} Review"
                if score:
                    post_title += f" (Score: {score})"

                # Fecha actual
                post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Guardar en la tabla feeds con origen
                feed_name = extraer_dominio(url)

                guardado = guardar_feed_con_origen(
                    conn, cursor, 'album', album_id, feed_name,
                    post_title, url, post_date, contenido, origen
                )

                if guardado:
                    reviews_guardadas += 1
                    print(f"✓ Reseña guardada: {publication} - {post_title}")
                else:
                    print(f"✗ Error guardando reseña de {publication}")
            else:
                print(f"✗ No se pudo extraer contenido de {publication}: {url}")

        except Exception as e:
            print(f"✗ Error procesando reseña de {publication}: {e}")
            continue

    print(f"Total de reseñas guardadas desde Metacritic: {reviews_guardadas}")
    return reviews_guardadas

def procesar_reviews_aoty_mejorado_con_force_update(conn, cursor, album_id, aoty_url, content_service, force_update=False):
    """
    Versión mejorada que procesa reseñas de AOTY con force_update y origen
    """
    origen = "review_aoty"

    # Verificar si ya fue procesado y force_update está desactivado
    if not force_update and verificar_album_ya_procesado(cursor, album_id, origen):
        print(f"   ⏭️  Saltando reseñas de AOTY para álbum ID {album_id} - ya procesado")
        return 0

    enlaces_validos, enlaces_error = extraer_enlaces_reviews_aoty(aoty_url)

    # Filtrar enlaces válidos para reseñas
    enlaces_validos = filtrar_enlaces_validos_para_reviews(enlaces_validos)

    if enlaces_error:
        print(f"Se encontraron {len(enlaces_error)} enlaces con errores en AOTY")

    reviews_guardadas = 0

    for enlace in enlaces_validos:
        url = enlace['url']
        publication = enlace['publication']

        print(f"Procesando reseña de {publication}: {url}")

        try:
            # Usar la nueva función de extracción específica por sitio
            contenido = extraer_contenido_segun_sitio(url, content_service)

            if contenido:
                # Crear título para la reseña
                post_title = f"{publication} Review (via AOTY)"

                # Fecha actual
                post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Guardar en la tabla feeds con origen
                feed_name = extraer_dominio(url)

                guardado = guardar_feed_con_origen(
                    conn, cursor, 'album', album_id, feed_name,
                    post_title, url, post_date, contenido, origen
                )

                if guardado:
                    reviews_guardadas += 1
                    print(f"✓ Reseña guardada: {publication} - {post_title}")
                else:
                    print(f"✗ Error guardando reseña de {publication}")
            else:
                print(f"✗ No se pudo extraer contenido de {publication}: {url}")

        except Exception as e:
            print(f"✗ Error procesando reseña de {publication}: {e}")
            continue

    print(f"Total de reseñas guardadas desde AOTY: {reviews_guardadas}")
    return reviews_guardadas

def buscar_album_en_db_completo_con_force_update(conn, cursor, album_id, album_name, artist_name, content_service,
                                               include_metacritic=True, include_aoty=True,
                                               force_update=False, archivo_errores=None,
                                               google_api_key=None, google_cx=None):
    """
    Versión completa con force_update y origen para todas las fuentes
    """
    enlaces_guardados = 0

    print(f"\n{'='*60}")
    print(f"🎵 PROCESANDO ÁLBUM (force_update={force_update})")
    print(f"   🎤 {artist_name} - 💿 {album_name}")
    print(f"{'='*60}")

    # 1. Búsqueda mejorada en AnyDecentMusic
    if force_update or not verificar_album_ya_procesado(cursor, album_id, 'review_anydecentmusic'):
        try:
            print(f"\n🌍 Procesando AnyDecentMusic...")
            enlaces_guardados += buscar_album_en_db_mejorado_con_force_update(
                conn, cursor, album_id, album_name, artist_name, content_service,
                force_update, archivo_errores
            )
            registrar_busqueda(conn, cursor, album_id, 'review_anydecentmusic')
        except Exception as e:
            print(f"Error en búsqueda AnyDecentMusic: {e}")
    else:
        print(f"\n🌍 AnyDecentMusic: búsqueda reciente, saltando")

    # 2. Búsqueda completa en Metacritic
    if include_metacritic and (force_update or not verificar_album_ya_procesado(cursor, album_id, 'review_metacritic')):
        print(f"\n🎯 Procesando Metacritic...")
        try:
            # Verificar si ya fue procesado por Metacritic (datos básicos)
            if not force_update:
                cursor.execute("SELECT metascore, metacritic_url FROM album_metacritic WHERE album_id = ?", (album_id,))
                existing_metacritic = cursor.fetchone()
                if existing_metacritic:
                    print(f"   ⏭️  Saltando datos de Metacritic para álbum ID {album_id} - ya procesado")
                    # Reutilizamos la URL guardada para procesar reseñas individuales si aún no se han procesado
                    existing_url = existing_metacritic['metacritic_url']
                    if existing_url:
                        reviews_procesadas = procesar_reviews_metacritic_mejorado_con_force_update(
                            conn, cursor, album_id, existing_url, content_service, force_update
                        )
                        enlaces_guardados += reviews_procesadas
                else:
                    # Solo buscar y guardar datos básicos si no existen
                    metacritic_url = buscar_album_metacritic_mejorado(artist_name, album_name)

                    if metacritic_url:
                        print(f"✓ Álbum encontrado en Metacritic: {metacritic_url}")

                        # Extraer y guardar datos básicos de Metacritic
                        datos_metacritic = extraer_datos_metacritic_mejorado(metacritic_url)

                        if datos_metacritic:
                            if guardar_datos_metacritic(conn, cursor, album_id, datos_metacritic):
                                print(f"✓ Datos básicos de Metacritic guardados")

                            # Guardar resumen como entrada en feeds con origen
                            if datos_metacritic['metascore'] is not None:
                                post_title = f"Metacritic Summary - {artist_name} - {album_name} (Score: {datos_metacritic['metascore']})"
                                content = f"Metacritic Score: {datos_metacritic['metascore']}/100\n"
                                content += f"Based on {datos_metacritic['num_critics']} critic reviews\n"
                                content += f"Distribution: +{datos_metacritic['positive_reviews']} ±{datos_metacritic['mixed_reviews']} -{datos_metacritic['negative_reviews']}"

                                post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                                if guardar_feed_con_origen(conn, cursor, 'album', album_id, 'metacritic.com',
                                                      post_title, metacritic_url, post_date, content, 'review_metacritic'):
                                    enlaces_guardados += 1

                        # Procesar reseñas individuales de Metacritic con force_update
                        print(f"🔍 Buscando reseñas individuales en Metacritic...")
                        reviews_procesadas = procesar_reviews_metacritic_mejorado_con_force_update(
                            conn, cursor, album_id, metacritic_url, content_service, force_update
                        )
                        enlaces_guardados += reviews_procesadas
                    else:
                        print(f"✗ No se encontró el álbum en Metacritic")
            else:
                # Si force_update=True, procesar todo nuevamente
                metacritic_url = buscar_album_metacritic_mejorado(artist_name, album_name)

                if metacritic_url:
                    print(f"✓ Álbum encontrado en Metacritic: {metacritic_url}")

                    # Extraer y guardar datos básicos de Metacritic
                    datos_metacritic = extraer_datos_metacritic_mejorado(metacritic_url)

                    if datos_metacritic:
                        if guardar_datos_metacritic(conn, cursor, album_id, datos_metacritic):
                            print(f"✓ Datos básicos de Metacritic guardados")

                        # Guardar resumen como entrada en feeds con origen
                        if datos_metacritic['metascore'] is not None:
                            post_title = f"Metacritic Summary - {artist_name} - {album_name} (Score: {datos_metacritic['metascore']})"
                            content = f"Metacritic Score: {datos_metacritic['metascore']}/100\n"
                            content += f"Based on {datos_metacritic['num_critics']} critic reviews\n"
                            content += f"Distribution: +{datos_metacritic['positive_reviews']} ±{datos_metacritic['mixed_reviews']} -{datos_metacritic['negative_reviews']}"

                            post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                            if guardar_feed_con_origen(conn, cursor, 'album', album_id, 'metacritic.com',
                                                  post_title, metacritic_url, post_date, content, 'review_metacritic'):
                                enlaces_guardados += 1

                    # Procesar reseñas individuales de Metacritic
                    print(f"🔍 Buscando reseñas individuales en Metacritic...")
                    reviews_procesadas = procesar_reviews_metacritic_mejorado_con_force_update(
                        conn, cursor, album_id, metacritic_url, content_service, force_update
                    )
                    enlaces_guardados += reviews_procesadas
                else:
                    print(f"✗ No se encontró el álbum en Metacritic")

        except Exception as e:
            print(f"Error en búsqueda Metacritic: {e}")
        else:
            registrar_busqueda(conn, cursor, album_id, 'review_metacritic')
    elif include_metacritic:
        print(f"\n🎯 Metacritic: búsqueda reciente, saltando")

    # 3. Búsqueda completa en Album of the Year (AOTY)
    if include_aoty and (force_update or not verificar_album_ya_procesado(cursor, album_id, 'review_aoty')):
        print(f"\n🏆 Procesando Album of the Year...")
        try:
            if not force_update:
                cursor.execute("SELECT user_score, aoty_url FROM album_aoty WHERE album_id = ?", (album_id,))
                existing_aoty = cursor.fetchone()
                if existing_aoty:
                    print(f"   ⏭️  Saltando datos de AOTY para álbum ID {album_id} - ya procesado")
                    # Reutilizamos la URL guardada para procesar reseñas individuales si aún no se han procesado
                    existing_url = existing_aoty['aoty_url']
                    if existing_url:
                        reviews_procesadas = procesar_reviews_aoty_mejorado_con_force_update(
                            conn, cursor, album_id, existing_url, content_service, force_update
                        )
                        enlaces_guardados += reviews_procesadas
                else:

                    # Solo buscar y guardar datos básicos si no existen
                    aoty_url = buscar_album_aoty(artist_name, album_name, google_api_key, google_cx)

                    if aoty_url:
                        print(f"✓ Álbum encontrado en AOTY: {aoty_url}")

                        # Extraer y guardar datos básicos de AOTY
                        datos_aoty = extraer_datos_aoty(aoty_url)

                        if datos_aoty:
                            if guardar_datos_aoty(conn, cursor, album_id, datos_aoty):
                                print(f"✓ Datos básicos de AOTY guardados")

                            # Guardar resumen como entrada en feeds con origen
                            if datos_aoty['user_score'] is not None or datos_aoty['critic_score'] is not None:
                                scores_text = []
                                if datos_aoty['user_score']:
                                    scores_text.append(f"User: {datos_aoty['user_score']}")
                                if datos_aoty['critic_score']:
                                    scores_text.append(f"Critic: {datos_aoty['critic_score']}")

                                post_title = f"AOTY Summary - {artist_name} - {album_name} ({'/'.join(scores_text)})"
                                content = f"Album of the Year Scores:\n"
                                if datos_aoty['user_score']:
                                    content += f"User Score: {datos_aoty['user_score']}/100 (based on {datos_aoty['num_user_ratings']} ratings)\n"
                                if datos_aoty['critic_score']:
                                    content += f"Critic Score: {datos_aoty['critic_score']}/100 (based on {datos_aoty['num_critic_ratings']} reviews)\n"

                                post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                                if guardar_feed_con_origen(conn, cursor, 'album', album_id, 'albumoftheyear.org',
                                                      post_title, aoty_url, post_date, content, 'review_aoty'):
                                    enlaces_guardados += 1

                        # Procesar reseñas individuales de AOTY con force_update
                        print(f"🔍 Buscando reseñas individuales en AOTY...")
                        reviews_procesadas = procesar_reviews_aoty_mejorado_con_force_update(
                            conn, cursor, album_id, aoty_url, content_service, force_update
                        )
                        enlaces_guardados += reviews_procesadas
                    else:
                        print(f"✗ No se encontró el álbum en Album of the Year")
            else:
                # Si force_update=True, procesar todo nuevamente
                aoty_url = buscar_album_aoty(artist_name, album_name, google_api_key, google_cx)

                if aoty_url:
                    print(f"✓ Álbum encontrado en AOTY: {aoty_url}")

                    # Extraer y guardar datos básicos de AOTY
                    datos_aoty = extraer_datos_aoty(aoty_url)

                    if datos_aoty:
                        if guardar_datos_aoty(conn, cursor, album_id, datos_aoty):
                            print(f"✓ Datos básicos de AOTY guardados")

                        # Guardar resumen como entrada en feeds con origen
                        if datos_aoty['user_score'] is not None or datos_aoty['critic_score'] is not None:
                            scores_text = []
                            if datos_aoty['user_score']:
                                scores_text.append(f"User: {datos_aoty['user_score']}")
                            if datos_aoty['critic_score']:
                                scores_text.append(f"Critic: {datos_aoty['critic_score']}")

                            post_title = f"AOTY Summary - {artist_name} - {album_name} ({'/'.join(scores_text)})"
                            content = f"Album of the Year Scores:\n"
                            if datos_aoty['user_score']:
                                content += f"User Score: {datos_aoty['user_score']}/100 (based on {datos_aoty['num_user_ratings']} ratings)\n"
                            if datos_aoty['critic_score']:
                                content += f"Critic Score: {datos_aoty['critic_score']}/100 (based on {datos_aoty['num_critic_ratings']} reviews)\n"

                            post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                            if guardar_feed_con_origen(conn, cursor, 'album', album_id, 'albumoftheyear.org',
                                                  post_title, aoty_url, post_date, content, 'review_aoty'):
                                enlaces_guardados += 1

                    # Procesar reseñas individuales de AOTY
                    print(f"🔍 Buscando reseñas individuales en AOTY...")
                    reviews_procesadas = procesar_reviews_aoty_mejorado_con_force_update(
                        conn, cursor, album_id, aoty_url, content_service, force_update
                    )
                    enlaces_guardados += reviews_procesadas
                else:
                    print(f"✗ No se encontró el álbum en Album of the Year")

        except Exception as e:
            print(f"Error en búsqueda AOTY: {e}")
        else:
            registrar_busqueda(conn, cursor, album_id, 'review_aoty')
    elif include_aoty:
        print(f"\n🏆 Album of the Year: búsqueda reciente, saltando")

    return enlaces_guardados

def procesar_albums_con_force_update_y_origen(db_path, content_service, include_metacritic=True,
                                            include_aoty=True, archive_errores=None,
                                            inicio_id=0, lote=50, pausa=2,
                                            force_update=False,
                                            google_api_key=None, google_cx=None):
    """
    Función principal con soporte completo para force_update y columna origen
    """
    conn, cursor = conectar_db(db_path)

    # Crear columna origen si no existe
    crear_columna_origen_si_no_existe(cursor)
    conn.commit()

    # Crear tablas si no existen
    if include_metacritic:
        crear_tabla_metacritic(cursor)
    if include_aoty:
        crear_tabla_aoty(cursor)
    conn.commit()

    # Obtener todos los álbumes
    todos_albums = obtener_albums(cursor)
    albums_a_procesar = [a for a in todos_albums if a['id'] >= inicio_id]

    print(f"\n{'='*80}")
    print(f"🚀 PROCESAMIENTO CON force_update Y COLUMNA origen")
    print(f"{'='*80}")
    print(f"📊 Álbumes a procesar: {len(albums_a_procesar)} (desde ID {inicio_id})")
    print(f"🔄 Force update: {'ACTIVADO' if force_update else 'DESACTIVADO'}")

    if force_update:
        print(f"   → Se procesarán TODOS los álbumes nuevamente")
    else:
        print(f"   → Se saltarán álbumes ya procesados por cada fuente")

    fuentes_activas = ["AnyDecentMusic"]
    if include_metacritic:
        fuentes_activas.append("Metacritic")
    if include_aoty:
        fuentes_activas.append("Album of the Year")

    print(f"📄 Fuentes activas: {', '.join(fuentes_activas)}")
    print(f"⚙️  Servicio de contenido: {content_service}")
    print(f"🏷️  Columna origen: ACTIVADA (review_anydecentmusic, review_metacritic, review_aoty)")
    print(f"{'='*80}")

    # Estadísticas
    albums_procesados = 0
    resenas_totales = 0
    albums_saltados = 0
    metacritic_encontrados = 0
    aoty_encontrados = 0
    anydecentmusic_encontrados = 0

    # Procesar por lotes
    for i in range(0, len(albums_a_procesar), lote):
        lote_actual = albums_a_procesar[i:i+lote]
        print(f"\n{'='*60}")
        print(f"📦 PROCESANDO LOTE {i//lote + 1}/{(len(albums_a_procesar)-1)//lote + 1} ({len(lote_actual)} álbumes)")
        print(f"{'='*60}")

        for album in lote_actual:
            print(f"\n🎵 ÁLBUM {albums_procesados + 1}/{len(albums_a_procesar)} - ID {album['id']}")
            print(f"   🎤 {album['artist']} - 💿 {album['name']}")

            # Verificar si el álbum debe ser saltado completamente
            album_saltado = False
            if not force_update:
                # Verificar si ya fue procesado por TODAS las fuentes activas
                fuentes_procesadas = 0

                if verificar_album_ya_procesado(cursor, album['id'], 'review_anydecentmusic'):
                    fuentes_procesadas += 1

                if include_metacritic and verificar_album_ya_procesado(cursor, album['id'], 'review_metacritic'):
                    fuentes_procesadas += 1

                if include_aoty and verificar_album_ya_procesado(cursor, album['id'], 'review_aoty'):
                    fuentes_procesadas += 1

                total_fuentes = 1 + (1 if include_metacritic else 0) + (1 if include_aoty else 0)

                if fuentes_procesadas == total_fuentes:
                    print(f"   ⏭️  ÁLBUM COMPLETAMENTE PROCESADO - Saltando")
                    albums_saltados += 1
                    album_saltado = True

            if not album_saltado:
                # Buscar reseñas para este álbum con force_update
                resenas = buscar_album_en_db_completo_con_force_update(
                    conn, cursor, album['id'], album['name'], album['artist'],
                    content_service, include_metacritic, include_aoty,
                    force_update, archive_errores, google_api_key, google_cx
                )

                # Actualizar estadísticas
                resenas_totales += resenas
                print(f"   📈 Reseñas encontradas para este álbum: {resenas}")

            # Verificar fuentes encontradas para estadísticas
            if include_metacritic:
                cursor.execute("SELECT metascore FROM album_metacritic WHERE album_id = ?", (album['id'],))
                if cursor.fetchone():
                    metacritic_encontrados += 1

            if include_aoty:
                cursor.execute("SELECT user_score FROM album_aoty WHERE album_id = ?", (album['id'],))
                if cursor.fetchone():
                    aoty_encontrados += 1

            # Contar reseñas de AnyDecentMusic
            cursor.execute("""
                SELECT COUNT(*) as count FROM feeds
                WHERE entity_type = 'album' AND entity_id = ?
                AND origen = 'review_anydecentmusic'
            """, (album['id'],))
            if cursor.fetchone()['count'] > 0:
                anydecentmusic_encontrados += 1

            conn.commit()
            albums_procesados += 1

            # Pausa para evitar sobrecargar los servidores
            if albums_procesados < len(albums_a_procesar):
                print(f"   ⏳ Esperando {pausa} segundos...")
                time.sleep(pausa)

        # Resumen del lote
        print(f"\n{'='*40}")
        print(f"📊 RESUMEN LOTE {i//lote + 1}")
        print(f"{'='*40}")
        print(f"✅ Álbumes procesados: {albums_procesados}/{len(albums_a_procesar)}")
        print(f"⏭️  Álbumes saltados: {albums_saltados}")
        print(f"📄 Reseñas totales: {resenas_totales}")
        print(f"🌍 Encontrados en AnyDecentMusic: {anydecentmusic_encontrados}")
        if include_metacritic:
            print(f"🎯 Encontrados en Metacritic: {metacritic_encontrados}")
        if include_aoty:
            print(f"🏆 Encontrados en Album of the Year: {aoty_encontrados}")
        print(f"{'='*40}")

    # Cerrar conexión
    conn.close()

    return albums_procesados, resenas_totales, albums_saltados, metacritic_encontrados, aoty_encontrados, anydecentmusic_encontrados


def generar_variaciones_nombre(nombre):
    """
    Versión corregida que genera variaciones únicas de un nombre para búsqueda

    Args:
        nombre (str): Nombre original

    Returns:
        list: Lista de variaciones únicas ordenadas por relevancia
    """
    variaciones = []  # Usar lista para mantener orden de relevancia
    variaciones_set = set()  # Set para evitar duplicados

    nombre_lower = nombre.strip().lower()

    # 1. Original (más relevante)
    if nombre_lower not in variaciones_set:
        variaciones.append(nombre_lower)
        variaciones_set.add(nombre_lower)

    # 2. Sin artículos al inicio (muy relevante)
    sin_articulos = re.sub(r'^(the|a|an)\s+', '', nombre, flags=re.IGNORECASE).strip().lower()
    if sin_articulos and sin_articulos not in variaciones_set:
        variaciones.append(sin_articulos)
        variaciones_set.add(sin_articulos)

    # 3. Sin paréntesis (relevante)
    sin_parentesis = re.sub(r'\s*\([^)]*\)', '', nombre).strip().lower()
    if sin_parentesis and sin_parentesis not in variaciones_set:
        variaciones.append(sin_parentesis)
        variaciones_set.add(sin_parentesis)

    # 4. Sin "featuring", "feat.", "ft." (relevante)
    sin_featuring = re.sub(r'\s+(featuring|feat\.?|ft\.?)\s+.*$', '', nombre, flags=re.IGNORECASE).strip().lower()
    if sin_featuring and sin_featuring not in variaciones_set:
        variaciones.append(sin_featuring)
        variaciones_set.add(sin_featuring)

    # 5. Sin corchetes (menos relevante)
    sin_corchetes = re.sub(r'\s*\[[^\]]*\]', '', nombre).strip().lower()
    if sin_corchetes and sin_corchetes not in variaciones_set:
        variaciones.append(sin_corchetes)
        variaciones_set.add(sin_corchetes)

    # Limitar a máximo 4 variaciones para evitar demasiadas combinaciones
    return variaciones[:4]

def buscar_album_metacritic_mejorado_v2(artist_name, album_name):
    """
    Versión mejorada que evita repeticiones y usa DuckDuckGo como método principal

    Args:
        artist_name (str): Nombre del artista
        album_name (str): Nombre del álbum

    Returns:
        str or None: URL del álbum en Metacritic si se encuentra
    """
    print(f"Buscando en Metacritic: {artist_name} - {album_name}")

    # Método 1: Búsqueda con DuckDuckGo (más efectivo)
    metacritic_url = buscar_metacritic_con_duckduckgo(artist_name, album_name)
    if metacritic_url:
        return metacritic_url

    # Método 2: URLs directas con variaciones (sin repeticiones)
    print("Probando URLs directas con variaciones...")

    # Generar variaciones únicas
    variaciones_album = generar_variaciones_nombre(album_name)
    variaciones_artista = generar_variaciones_nombre(artist_name)

    print(f"Variaciones de álbum ({len(variaciones_album)}): {variaciones_album}")
    print(f"Variaciones de artista ({len(variaciones_artista)}): {variaciones_artista}")

    # Probar combinaciones únicas (máximo 6 intentos)
    combinaciones_probadas = set()
    intentos = 0
    max_intentos = 6

    for album_var in variaciones_album:
        for artist_var in variaciones_artista:
            if intentos >= max_intentos:
                break

            # Crear clave única para evitar repeticiones
            clave_combinacion = f"{album_var}|{artist_var}"
            if clave_combinacion in combinaciones_probadas:
                continue

            combinaciones_probadas.add(clave_combinacion)
            intentos += 1

            url_directa = construir_url_metacritic_directa(artist_var, album_var)
            print(f"Intento {intentos}: {url_directa}")

            if verificar_url_metacritic(url_directa):
                print(f"✓ Encontrado en URL directa: {url_directa}")
                return url_directa

        if intentos >= max_intentos:
            break

    # Método 3: Fallback con buscador interno de Metacritic
    print("Probando buscador interno de Metacritic como último recurso...")
    return buscar_album_metacritic_fallback(artist_name, album_name)


def generar_variaciones_nombre(nombre):
    """
    Versión corregida que genera variaciones únicas de un nombre para búsqueda

    Args:
        nombre (str): Nombre original

    Returns:
        list: Lista de variaciones únicas ordenadas por relevancia
    """
    variaciones = []  # Usar lista para mantener orden de relevancia
    variaciones_set = set()  # Set para evitar duplicados

    nombre_lower = nombre.strip().lower()

    # 1. Original (más relevante)
    if nombre_lower not in variaciones_set:
        variaciones.append(nombre_lower)
        variaciones_set.add(nombre_lower)

    # 2. Sin artículos al inicio (muy relevante)
    sin_articulos = re.sub(r'^(the|a|an)\s+', '', nombre, flags=re.IGNORECASE).strip().lower()
    if sin_articulos and sin_articulos not in variaciones_set:
        variaciones.append(sin_articulos)
        variaciones_set.add(sin_articulos)

    # 3. Sin paréntesis (relevante)
    sin_parentesis = re.sub(r'\s*\([^)]*\)', '', nombre).strip().lower()
    if sin_parentesis and sin_parentesis not in variaciones_set:
        variaciones.append(sin_parentesis)
        variaciones_set.add(sin_parentesis)

    # 4. Sin "featuring", "feat.", "ft." (relevante)
    sin_featuring = re.sub(r'\s+(featuring|feat\.?|ft\.?)\s+.*$', '', nombre, flags=re.IGNORECASE).strip().lower()
    if sin_featuring and sin_featuring not in variaciones_set:
        variaciones.append(sin_featuring)
        variaciones_set.add(sin_featuring)

    # 5. Sin corchetes (menos relevante)
    sin_corchetes = re.sub(r'\s*\[[^\]]*\]', '', nombre).strip().lower()
    if sin_corchetes and sin_corchetes not in variaciones_set:
        variaciones.append(sin_corchetes)
        variaciones_set.add(sin_corchetes)

    # Limitar a máximo 4 variaciones para evitar demasiadas combinaciones
    return variaciones[:4]



def buscar_metacritic_con_duckduckgo(artist_name, album_name):
    """
    Busca en Metacritic usando SearXNG (instancia selfhosteada)
    """
    from urllib.parse import quote_plus
    import time
    import random

    _ck = ('metacritic_url', artist_name.lower(), album_name.lower())
    _cached = _cache.get(_ck, service='metacritic')
    if _cached is not None:
        url = _cached.get('url')
        print(f"{'✓' if url else '⏭'} Metacritic URL desde caché: {url or 'no encontrado'}")
        return url

    # Queries limitadas
    queries = [
        f'site:metacritic.com "{artist_name}" "{album_name}" music',
        f'site:metacritic.com {artist_name} {album_name} album'
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
    }

    for i, query in enumerate(queries, 1):
        try:
            print(f"Búsqueda SearXNG {i}/{len(queries)} (Metacritic): {query}")

            search_url = f"{SEARXNG_URL}/search"
            params = {
                'q': query,
                'format': 'json',
                'engines': 'google,bing,duckduckgo',
            }

            response = _session.get(search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            for result in results:
                href = result.get('url', '')

                if 'metacritic.com' in href and '/music/' in href and href.startswith('http'):
                    clean_url = href.split('?')[0].split('#')[0]
                    print(f"Candidato encontrado: {clean_url}")

                    if verificar_url_metacritic(clean_url):
                        print(f"✓ Encontrado con SearXNG: {clean_url}")
                        _cache.set(_ck, service='metacritic', value={'url': clean_url})
                        return clean_url

            # Pequeña pausa entre queries
            if i < len(queries):
                time.sleep(1)

        except Exception as e:
            print(f"Error en búsqueda SearXNG (Metacritic) '{query}': {e}")
            continue

    _cache.set(_ck, service='metacritic', value={'url': None})
    return None

def buscar_metacritic_con_google_scraping(artist_name, album_name):
    """
    Busca usando Google Search (scraping) como alternativa a DuckDuckGo
    """
    from urllib.parse import quote_plus
    import time
    import random

    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]

    query = f'site:metacritic.com "{artist_name}" "{album_name}" music album'

    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        # Usar google.com/search
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"

        print(f"Buscando con Google: {query}")

        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()

        # Verificar si hay captcha
        if 'captcha' in response.text.lower() or '/sorry/' in response.url:
            print("⚠️ Google detectó tráfico inusual")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Buscar enlaces en los resultados
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Extraer URL real de Google
            if '/url?q=' in href:
                try:
                    import urllib.parse
                    real_url = urllib.parse.unquote(href.split('/url?q=')[1].split('&')[0])

                    if 'metacritic.com' in real_url and '/music/' in real_url:
                        print(f"Candidato encontrado: {real_url}")

                        # Delay antes de verificar
                        time.sleep(random.uniform(1, 2))

                        if verificar_url_metacritic(real_url):
                            print(f"✓ Encontrado con Google: {real_url}")
                            return real_url
                except:
                    continue

        return None

    except Exception as e:
        print(f"Error en búsqueda Google: {e}")
        return None



def buscar_album_aoty_mejorado_v2(artist_name, album_name, google_api_key=None, google_cx=None):
    """
    Versión mejorada que usa DuckDuckGo como método principal para AOTY

    Args:
        artist_name (str): Nombre del artista
        album_name (str): Nombre del álbum
        google_api_key (str): API key de Google (opcional)
        google_cx (str): Custom Search Engine ID (opcional)

    Returns:
        str or None: URL del álbum en AOTY si se encuentra
    """
    print(f"Buscando en Album of the Year: {artist_name} - {album_name}")

    # Método 1: DuckDuckGo (más efectivo que Google API)
    print("Usando DuckDuckGo como método principal...")
    aoty_url = buscar_aoty_con_duckduckgo_v2(artist_name, album_name)
    if aoty_url:
        return aoty_url

    # Método 2: Google API (si está disponible)
    if google_api_key and google_cx:
        try:
            print("Probando con Google API...")
            aoty_url = buscar_aoty_con_google_api(artist_name, album_name, google_api_key, google_cx)
            if aoty_url:
                return aoty_url
        except Exception as e:
            print(f"Error con Google API: {e}")

    # Método 3: Búsqueda directa en AOTY (fallback)
    print("Usando búsqueda directa como último recurso...")
    return buscar_album_aoty_directo_mejorado(artist_name, album_name)

def buscar_aoty_con_duckduckgo_v2(artist_name, album_name):
    """
    Búsqueda en AOTY usando SearXNG (instancia selfhosteada)

    Args:
        artist_name (str): Nombre del artista
        album_name (str): Nombre del álbum

    Returns:
        str or None: URL del álbum en AOTY si se encuentra
    """
    from urllib.parse import quote_plus
    import time

    _ck = ('aoty_url', artist_name.lower(), album_name.lower())
    _cached = _cache.get(_ck, service='youtube')  # reuse youtube TTL (7d)
    if _cached is not None:
        url = _cached.get('url')
        print(f"{'✓' if url else '⏭'} AOTY URL desde caché: {url or 'no encontrado'}")
        return url

    # Generar variaciones limitadas para búsqueda más efectiva
    variaciones_album = generar_variaciones_nombre(album_name)[:2]
    variaciones_artista = generar_variaciones_nombre(artist_name)[:2]

    # Queries específicas para AOTY
    queries = []
    for album_var in variaciones_album:
        for artist_var in variaciones_artista:
            queries.append(f'site:albumoftheyear.org "{artist_var}" "{album_var}"')

    queries.extend([
        f'site:albumoftheyear.org {artist_name} {album_name} album',
    ])
    queries = queries[:5]

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
    }

    for i, query in enumerate(queries, 1):
        try:
            print(f"Búsqueda SearXNG {i}/{len(queries)} (AOTY): {query}")

            search_url = f"{SEARXNG_URL}/search"
            params = {
                'q': query,
                'format': 'json',
                'engines': 'google,bing,duckduckgo',
            }

            response = _session.get(search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            for result in results:
                href = result.get('url', '')

                if ('albumoftheyear.org' in href and
                        '/album/' in href and
                        href.startswith('http')):
                    clean_url = href.split('?')[0].split('#')[0]
                    print(f"Candidato AOTY encontrado: {clean_url}")

                    if verificar_url_aoty_mejorado(clean_url):
                        print(f"✓ Encontrado AOTY con SearXNG: {clean_url}")
                        _cache.set(_ck, service='youtube', value={'url': clean_url})
                        return clean_url

            if i < len(queries):
                time.sleep(1)

        except Exception as e:
            print(f"Error en búsqueda SearXNG (AOTY) '{query}': {e}")
            continue

    print("No se encontró resultado válido en AOTY con SearXNG")
    _cache.set(_ck, service='youtube', value={'url': None})
    return None

def buscar_album_aoty_directo_mejorado(artist_name, album_name):
    """
    Versión mejorada de búsqueda directa en AOTY con mejor manejo de errores

    Args:
        artist_name (str): Nombre del artista
        album_name (str): Nombre del álbum

    Returns:
        str or None: URL del álbum en AOTY si se encuentra
    """
    from urllib.parse import quote_plus

    print(f"Búsqueda directa en AOTY...")

    # Usar solo las mejores variaciones para evitar spam
    variaciones_album = generar_variaciones_nombre(album_name)[:2]
    variaciones_artista = generar_variaciones_nombre(artist_name)[:2]

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    # Probar diferentes queries de búsqueda
    search_queries = []

    for album_var in variaciones_album:
        for artist_var in variaciones_artista:
            query = f"{artist_var} {album_var}".strip()
            if query not in search_queries:
                search_queries.append(query)

    # Limitar a 4 queries máximo
    search_queries = search_queries[:4]

    for i, query in enumerate(search_queries, 1):
        try:
            search_url = f"https://www.albumoftheyear.org/search/albums/?q={quote_plus(query)}"
            print(f"Búsqueda directa AOTY {i}/{len(search_queries)}: {search_url}")

            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Múltiples selectores para encontrar enlaces de álbumes
            selectors_to_try = [
                'div.albumBlock a[href*="/album/"]',
                'a[href*="/album/"]',
                '.searchResult a[href*="/album/"]',
                '.albumEntry a[href*="/album/"]'
            ]

            album_links = []
            for selector in selectors_to_try:
                links = soup.select(selector)
                if links:
                    album_links = links[:5]  # Solo los primeros 5
                    print(f"Encontrados {len(links)} enlaces con selector: {selector}")
                    break

            # Verificar cada resultado
            for link in album_links:
                href = link.get('href', '')

                if href.startswith('/'):
                    result_url = f"https://www.albumoftheyear.org{href}"
                else:
                    result_url = href

                if verificar_url_aoty_mejorado(result_url):
                    print(f"✓ Primer resultado válido en búsqueda directa AOTY: {result_url}")
                    return result_url

            # Pausa entre queries
            if i < len(search_queries):
                time.sleep(1)

        except Exception as e:
            print(f"Error en búsqueda directa AOTY query '{query}': {e}")
            continue

    return None


def verificar_url_aoty_mejorado(url):
    """
    Versión mejorada de verificación para AOTY

    Args:
        url (str): URL a verificar

    Returns:
        bool: True si la URL existe y es válida
    """
    try:
        response = _session.head(url, timeout=10, allow_redirects=True)

        # Aceptar varios códigos de estado válidos
        if response.status_code in [200, 301, 302]:
            # Verificar que la URL final siga siendo de AOTY
            if 'albumoftheyear.org' in response.url:
                return True

        return False
    except Exception as e:
        print(f"Error verificando URL AOTY {url}: {e}")
        return False




def main(config=None):
    """
    Función principal con verificación y creación automática de tablas
    """
    print("🎵 Iniciando recolección COMPLETA de reseñas de álbumes...")

    # Si se llama directamente (no desde db_creator)
    if config is None:
        parser = argparse.ArgumentParser(description='Buscar reseñas de álbumes (versión completa)')
        parser.add_argument('--config', required=True, help='Archivo de configuración JSON')
        args = parser.parse_args()

        # Cargar configuración desde archivo
        try:
            with open(args.config, 'r') as f:
                config_data = json.load(f)

            # Combinar configuraciones
            config = {}
            config.update(config_data.get("common", {}))
            config.update(config_data.get("review_scrapper", {}))
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
            sys.exit(1)

    # Extraer parámetros de configuración
    db_path = config.get('db_path')
    if not db_path:
        print("Error: No se especificó la ruta de la base de datos")
        return

    content_service = config.get('content_service', 'five_filters')
    inicio_id = config.get('inicio_id', 0)
    tamano_lote = config.get('tamano_lote', 50)
    pausa_entre_busquedas = config.get('pausa', 2)
    archivo_errores = config.get('archivo_errores')
    include_metacritic = config.get('include_metacritic', True)
    include_aoty = config.get('include_aoty', True)
    force_update = config.get('force_update', False)
    google_api_key = config.get('google_api_key')
    google_cx = config.get('google_cx')

    print(f"📋 Configuración COMPLETA:")
    print(f"  📁 Base de datos: {db_path}")
    print(f"  🔧 Servicio de contenido: {content_service}")
    print(f"  🔢 ID inicial: {inicio_id}")
    print(f"  📦 Tamaño de lote: {tamano_lote}")
    print(f"  ⏱️  Pausa entre búsquedas: {pausa_entre_busquedas} segundos")
    print(f"  🎯 Incluir Metacritic: {include_metacritic}")
    print(f"  🏆 Incluir Album of the Year: {include_aoty}")
    print(f"  🔄 Force update: {'ACTIVADO' if force_update else 'DESACTIVADO'}")

    # Verificar existencia de la base de datos
    if not os.path.exists(db_path):
        print(f"❌ Error: La base de datos {db_path} no existe")
        return

    # Verificar y crear tablas antes de procesar
    conn, cursor = conectar_db(db_path)
    if not verificar_y_crear_tablas(conn, cursor):
        print("❌ Error al verificar/crear tablas. Abortando.")
        conn.close()
        return
    conn.close()

    print("✅ Tablas verificadas/creadas correctamente")

    # Iniciar procesamiento completo
    try:
        albums_procesados, resenas_encontradas, albums_saltados, metacritic_encontrados, aoty_encontrados, anydecentmusic_encontrados = procesar_albums_con_force_update_y_origen(
            db_path, content_service, include_metacritic, include_aoty, archivo_errores,
            inicio_id, tamano_lote, pausa_entre_busquedas, force_update,
            google_api_key, google_cx
        )

        print(f"\n{'='*80}")
        print(f"🎉 RESUMEN FINAL COMPLETO")
        print(f"{'='*80}")
        print(f"📊 Álbumes procesados: {albums_procesados}")
        print(f"⏭️  Álbumes saltados: {albums_saltados}")
        print(f"📄 Reseñas encontradas: {resenas_encontradas}")
        print(f"🌍 AnyDecentMusic: {anydecentmusic_encontrados}")
        if include_metacritic:
            print(f"🎯 Metacritic: {metacritic_encontrados}")
        if include_aoty:
            print(f"🏆 Album of the Year: {aoty_encontrados}")
        print(f"{'='*80}")

    except Exception as e:
        print(f"❌ Error durante el procesamiento: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
