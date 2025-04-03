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
from urllib.parse import urlparse
import traceback
import re

# Importamos aclarar_contenido.py para usar su función
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))
import aclarar_contenido


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
        respuesta = requests.get(url_album, headers=headers)
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
                
                # Verificar si el enlace está vivo
                url_completa = url if url.startswith('http') else f"http://www.anydecentmusic.com{url}"
                
                try:
                    # Configurar para seguir redirecciones pero guardar la URL final
                    resp = requests.head(
                        url_completa, 
                        headers=headers, 
                        allow_redirects=True, 
                        timeout=10
                    )
                    
                    # Determinar el estado del enlace
                    if resp.status_code == 200:
                        estado = "Activo"
                        # Verificar si hubo redirección
                        if resp.url != url_completa:
                            estado = f"Redirigido a: {resp.url}"
                            url_completa = resp.url  # Actualizar URL a la redirección
                        
                        enlaces_validos.append({
                            'numero': idx,
                            'texto': texto,
                            'url': url_completa,
                            'estado': estado
                        })
                    elif resp.status_code in [404, 403]:
                        estado = f"Error {resp.status_code} - No disponible"
                        # No registramos estos errores comunes
                    else:
                        estado = f"Error HTTP: {resp.status_code}"
                        enlaces_error.append({
                            'numero': idx,
                            'texto': texto,
                            'url': url_completa,
                            'estado': estado,
                            'codigo': resp.status_code
                        })
                        
                except requests.exceptions.RequestException as e:
                    estado = f"Error al verificar: {str(e)}"
                    enlaces_error.append({
                        'numero': idx,
                        'texto': texto,
                        'url': url_completa,
                        'estado': estado,
                        'excepcion': str(e)
                    })
                
                print(f"Enlace {idx}: {texto} - {url_completa} -> {estado}")
    
    print(f"Total de enlaces: {total_enlaces}")
    print(f"Total de enlaces 'Read Review': {total_read_review}")
    print(f"Enlaces válidos encontrados: {len(enlaces_validos)}")
    print(f"Enlaces con errores no estándar: {len(enlaces_error)}")
    
    return enlaces_validos, enlaces_error

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
        conn.row_factory = sqlite3.Row  # Para acceder a las columnas por nombre
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

def obtener_ultimo_album_procesado(cursor):
    """
    Obtiene el ID del último álbum procesado para permitir reanudar el proceso
    
    Args:
        cursor: Cursor de la base de datos
        
    Returns:
        int: ID del último álbum procesado o 0 si no hay ninguno
    """
    try:
        cursor.execute("""
            SELECT MAX(entity_id) as last_id 
            FROM feeds 
            WHERE entity_type = 'album' AND feed_name LIKE '%anydecentmusic%'
        """)
        result = cursor.fetchone()
        return result['last_id'] if result and result['last_id'] is not None else 0
    except sqlite3.Error as e:
        print(f"Error al obtener último álbum procesado: {e}")
        return 0

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
        
        conn.commit()
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
        raw_content = aclarar_contenido.get_full_content(url, service_type)
        
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

def buscar_album_en_db(conn, cursor, album_id, album_name, artist_name, content_service, archivo_errores=None):
    """
    Busca reseñas para un álbum específico y las guarda en la base de datos
    
    Args:
        conn: Conexión a la base de datos
        cursor: Cursor de la base de datos
        album_id (int): ID del álbum en la base de datos
        album_name (str): Nombre del álbum
        artist_name (str): Nombre del artista
        content_service (str): Servicio a usar para extraer contenido
        archivo_errores (str, optional): Ruta al archivo donde guardar errores
        
    Returns:
        int: Número de reseñas encontradas y guardadas
    """
    # Construir la URL de búsqueda (podemos buscar por el nombre del álbum)
    termino_busqueda = artist_name
    url_busqueda = f"http://www.anydecentmusic.com/search-results.aspx?search={urllib.parse.quote(termino_busqueda)}"
    
    print(f"\nBuscando: {termino_busqueda}")
    print(f"Álbum objetivo: {album_name}")
    print(f"URL de búsqueda: {url_busqueda}")
    
    # Realizar la petición HTTP
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        respuesta = requests.get(url_busqueda, headers=headers, timeout=15)
        respuesta.raise_for_status()  # Verificar si hay errores en la respuesta
    except requests.exceptions.RequestException as e:
        print(f"Error al realizar la petición: {e}")
        return 0
    
    # Parsear el HTML con BeautifulSoup
    soup = BeautifulSoup(respuesta.text, 'html.parser')
    
    # Buscar todos los resultados de la lista
    resultados = soup.select('form > div > div > div > ul > li > div')
    
    if not resultados:
        print("No se encontraron resultados para la búsqueda.")
        return 0
    
    print(f"Se encontraron {len(resultados)} resultados generales.")
    
    # Variables para seguimiento
    album_encontrado = False
    enlaces_guardados = 0
    
    # Verificar cada resultado para encontrar coincidencias de artista y álbum
    for idx, resultado in enumerate(resultados, 1):
        # Intentar obtener el nombre del artista y álbum
        artista_elemento = resultado.select_one('a:nth-of-type(2) > h2')
        album_elemento = resultado.select_one('a:nth-of-type(3) > h3')
        
        if artista_elemento and album_elemento:
            nombre_artista = artista_elemento.text.strip()
            nombre_album = album_elemento.text.strip()
            
            print(f"Resultado {idx}: {nombre_artista} - {nombre_album}")
            
            # Verificar si coincide con lo que estamos buscando
            # Usamos .lower() para hacer la comparación sin distinguir mayúsculas/minúsculas
            if (artist_name.lower() in nombre_artista.lower() and 
                album_name.lower() in nombre_album.lower()):
                print(f"¡Coincidencia encontrada! Artista: {nombre_artista}, Álbum: {nombre_album}")
                album_encontrado = True
                
                # Obtener la URL del álbum
                album_url_elemento = resultado.select_one('a:nth-of-type(3)')
                if album_url_elemento and album_url_elemento.has_attr('href'):
                    album_url = album_url_elemento['href']
                    album_url_completa = f"http://www.anydecentmusic.com/{album_url}"
                    print(f"URL del álbum: {album_url_completa}")
                    
                    # Obtener enlaces de reseñas y posibles errores
                    enlaces_validos, enlaces_error = extraer_enlaces_album(album_url_completa)
                    
                    # Guardar errores si hay archivo configurado
                    if archivo_errores and enlaces_error:
                        guardar_errores_enlace(archivo_errores, nombre_artista, nombre_album, enlaces_error)
                    
                    if enlaces_validos:
                        print(f"Se encontraron {len(enlaces_validos)} enlaces de reseñas válidos.")
                        
                        # Procesar cada enlace válido
                        for enlace in enlaces_validos:
                            url = enlace['url']
                            estado = enlace['estado']
                            
                            print(f"Procesando enlace: {url}")
                            
                            # Extraer dominio para feed_name
                            feed_name = extraer_dominio(url)
                            
                            # Intentar obtener el título de la página
                            post_title = obtener_titulo_pagina(url)
                            
                            # Extraer contenido
                            contenido = extraer_contenido_con_aclarar(url, content_service)
                            
                            # Si hay contenido, guardar en la base de datos
                            if contenido:
                                # Fecha actual como fecha de post si no está disponible
                                post_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                # Guardar en la tabla feeds
                                guardado = guardar_feed(
                                    conn, cursor, 'album', album_id, feed_name, 
                                    post_title, url, post_date, contenido
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
def procesar_albums(db_path, content_service, archivo_errores=None, inicio_id=0, lote=50, pausa=2):
    """
    Procesa todos los álbumes de la base de datos en busca de reseñas
    
    Args:
        db_path (str): Ruta al archivo de la base de datos
        content_service (str): Servicio a usar para extraer contenido
        archivo_errores (str, optional): Ruta al archivo donde guardar errores
        inicio_id (int): ID del álbum desde el cual comenzar (para reanudar)
        lote (int): Número de álbumes a procesar por lote
        pausa (int): Segundos de pausa entre búsquedas
        
    Returns:
        tuple: (Albums procesados, reseñas encontradas)
    """
    conn, cursor = conectar_db(db_path)
    
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
        print(f"\n--- Procesando lote {i//lote + 1} ({len(lote_actual)} álbumes) ---")
        
        for album in lote_actual:
            print(f"\nProcesando álbum ID {album['id']}: {album['artist']} - {album['name']}")
            
            # Buscar reseñas para este álbum
            resenas = buscar_album_en_db(
                conn, cursor, album['id'], album['name'], album['artist'], 
                content_service, archivo_errores
            )
            
            # Actualizar estadísticas
            albums_procesados += 1
            resenas_totales += resenas
            
            # Pausa para evitar sobrecargar el servidor
            if albums_procesados < len(albums_a_procesar):
                print(f"Esperando {pausa} segundos antes de la próxima búsqueda...")
                time.sleep(pausa)
        
        # Resumen del lote
        print(f"\n--- Completado lote {i//lote + 1}: {albums_procesados} álbumes procesados, {resenas_totales} reseñas encontradas ---")
    
    # Cerrar conexión
    conn.close()
    
    return albums_procesados, resenas_totales

def main(config=None):
    """
    Función principal que puede ser llamada directamente o desde db_creator
    
    Args:
        config (dict, optional): Diccionario de configuración cuando se llama desde db_creator
    """
    print("Iniciando recolección de reseñas de álbumes...")
    
    # Si se llama directamente (no desde db_creator)
    if config is None:
        parser = argparse.ArgumentParser(description='Buscar reseñas de álbumes en AnyDecentMusic')
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
    
    # Extraer parámetros de configuración con valores predeterminados
    db_path = config.get('db_path')
    if not db_path:
        print("Error: No se especificó la ruta de la base de datos")
        return
    
    content_service = config.get('content_service', 'five_filters')
    inicio_id = config.get('inicio_id', 0)
    tamano_lote = config.get('tamano_lote', 50)
    pausa_entre_busquedas = config.get('pausa', 2)
    archivo_errores = config.get('archivo_errores')
    
    print(f"Configuración:")
    print(f"  Base de datos: {db_path}")
    print(f"  Servicio de contenido: {content_service}")
    print(f"  ID inicial: {inicio_id}")
    print(f"  Tamaño de lote: {tamano_lote}")
    print(f"  Pausa entre búsquedas: {pausa_entre_busquedas} segundos")
    if archivo_errores:
        print(f"  Archivo de errores: {archivo_errores}")
    
    # Verificar existencia de la base de datos
    if not os.path.exists(db_path):
        print(f"Error: La base de datos {db_path} no existe")
        return
    
    # Iniciar procesamiento
    try:
        albums_procesados, resenas_encontradas = procesar_albums(
            db_path, content_service, archivo_errores, inicio_id, tamano_lote, pausa_entre_busquedas
        )
        
        print(f"\n=== Resumen final ===")
        print(f"Álbumes procesados: {albums_procesados}")
        print(f"Reseñas encontradas y guardadas: {resenas_encontradas}")
        print(f"============================")
    except Exception as e:
        print(f"Error durante el procesamiento: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()