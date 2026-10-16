#!/usr/bin/env python
#
# Script Name: blogs_playlist_generator.py
# Description: Genera playlists a partir de blogs en FreshRSS, extrayendo URLs de YouTube, Bandcamp, etc.
# Author: volteret4 (adaptado)
#
# Notes:
#   Dependencies:  - python3, PyQt6
#                  - yt-dlp
#                  - servidor freshrss y categoria blog creada en el.
#

import logging
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import re
import requests
from typing import List, Dict
from urllib.parse import quote
import subprocess
import sys
import argparse
import traceback
import json
from concurrent.futures import ThreadPoolExecutor

# Configuración de logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30
# Peticiones simultáneas a los blogs y procesos yt-dlp en paralelo
FETCH_WORKERS = 8
TITLE_WORKERS = 6
# Fichero (en el directorio de salida) con los posts ya procesados
PROCESSED_FILE = '.posts_procesados.json'

# Sesión compartida para las páginas de los blogs (keep-alive)
web_session = requests.Session()
web_session.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) FreshRSS-Script/1.0'

def clean_youtube_url(url):
    """Limpia y normaliza URLs de YouTube"""
    # Recortar cualquier texto adicional al final de la URL
    url = url.split('"')[0].split("'")[0].split('>')[0].split('<')[0]
    
    # Eliminar parámetros innecesarios y obtener solo el ID de video
    if 'youtube.com/watch' in url:
        video_id = re.search(r'v=([^&]+)', url)
        if video_id:
            return f'https://youtube.com/watch?v={video_id.group(1)}'
    elif 'youtu.be/' in url:
        video_id = url.split('/')[-1].split('?')[0]
        return f'https://youtube.com/watch?v={video_id}'
    elif 'youtube.com/embed/' in url:
        video_id = url.split('/')[-1].split('?')[0]
        return f'https://youtube.com/watch?v={video_id}'
    return url

def extract_bandcamp_id(url):
    """Extrae y normaliza URLs de Bandcamp"""
    # Limpiar cualquier texto HTML adicional
    url = url.split('"')[0].split("'")[0].split('>')[0].split('<')[0]
    
    # Asegurarse de que la URL es completa
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url.lstrip('/')
    
    return url

def extract_music_urls(url):
    """
    Extrae las URLs de música (Bandcamp, SoundCloud, YouTube) del contenido HTML de la URL dada.
    Devuelve None si la página no se pudo descargar (para reintentarlo en la próxima ejecución).
    """
    try:
        response = web_session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        content = response.text
        music_urls = set()
        
        # Patrones para buscar URLs de música
        music_patterns = [
            # Bandcamp
            r'(https?://[a-zA-Z0-9-]+\.bandcamp\.com/[^\s"\'<>]+)',
            # SoundCloud
            r'(https?://(?:www\.)?soundcloud\.com/[^\s"\'<>]+)',
            # YouTube (varios formatos)
            r'(https?://(?:www\.)?youtube\.com/embed/[^\s"\'<>]+)',
            r'(https?://(?:www\.)?youtube\.com/watch\?[^\s"\'<>]+)',
            r'(https?://(?:www\.)?youtu\.be/[^\s"\'<>]+)'
        ]
        
        for pattern in music_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Limpiar la URL para eliminar cualquier texto HTML
                # Detectar y cortar en el primer carácter que no debería ser parte de la URL
                extracted_url = match.split('"')[0].split("'")[0].split('>')[0].split('<')[0]
                
                # Normalizar según el tipo de URL
                if 'bandcamp.com' in extracted_url:
                    if extracted_url.startswith('//'):
                        extracted_url = 'https:' + extracted_url
                    extracted_url = extract_bandcamp_id(extracted_url)
                else:
                    extracted_url = clean_youtube_url(extracted_url)
                
                # Solo agregar si la URL parece válida
                if extracted_url and ('youtube.com' in extracted_url or 'youtu.be' in extracted_url or 
                                     'bandcamp.com' in extracted_url or 'soundcloud.com' in extracted_url):
                    music_urls.add(extracted_url)
        
        logger.debug(f"Extraídas {len(music_urls)} URLs de música de {url}")
        return list(music_urls)
    except Exception as e:
        logger.error(f"Error al extraer URLs de {url}: {e}")
        return None


def fetch_title(url):
    """Obtiene el título de un vídeo/canción con yt-dlp, o None si falla"""
    try:
        result = subprocess.run(
            ['yt-dlp', '--get-title', '--no-warnings', '--no-playlist', url],
            capture_output=True,
            text=True,
            timeout=30  # Timeout para evitar cuelgues
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
        logger.debug(f"yt-dlp no devolvió título para {url}: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        logger.debug(f"Timeout al extraer título de {url}")
    except Exception as e:
        logger.debug(f"Error extrayendo título de {url}: {str(e)}")
    return None


def fetch_titles(urls):
    """Obtiene los títulos de varias URLs en paralelo, manteniendo el orden"""
    with ThreadPoolExecutor(max_workers=TITLE_WORKERS) as executor:
        titles = list(executor.map(fetch_title, urls))
    return [title or f"Sin título ({i+1})" for i, title in enumerate(titles)]


def read_playlist(playlist_path: Path):
    """Lee una playlist .m3u y su .txt de títulos; devuelve [(url, título)]"""
    if not playlist_path.exists():
        return []
    with open(playlist_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    titles = []
    txt_path = playlist_path.with_suffix('.txt')
    if txt_path.exists():
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            titles = [line.rstrip('\n') for line in f]
    return [(url, titles[i] if i < len(titles) else f"Sin título ({i+1})") for i, url in enumerate(urls)]

class FreshRSSReader:
    def __init__(self, base_url: str, username: str, api_password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_password = api_password
        self.api_endpoint = f"{self.base_url}/api/greader.php"
        self.auth_token = None
        # Sesión reutilizable (keep-alive, evita un handshake TLS por petición)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'FreshRSS-Script/1.0'
        
    def login(self) -> bool:
        """Inicia sesión en la API de FreshRSS"""
        endpoint = f"{self.api_endpoint}/accounts/ClientLogin"
        params = {
            'Email': self.username,
            'Passwd': self.api_password
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            for line in response.text.splitlines():
                if line.startswith('Auth='):
                    self.auth_token = line.replace('Auth=', '').strip()
                    self.session.headers['Authorization'] = f'GoogleLogin auth={self.auth_token}'
                    logger.info(f"Token obtenido correctamente")
                    return True
            
            logger.error("No se encontró el token de autenticación")
            return False
        except Exception as e:
            logger.error(f"Error en login: {str(e)}")
            return False

    def get_unread_posts(self, stream_id: str = 'user/-/label/Blogs') -> List[Dict[str, str]]:
        """Obtiene los posts no leídos de un stream (por defecto toda la categoría 'Blogs')
        con una sola consulta paginada, en lugar de una petición por feed"""
        endpoint = f"{self.api_endpoint}/reader/api/0/stream/contents/{quote(stream_id)}"
        params = {
            'output': 'json',
            'n': 1000,
            'xt': 'user/-/state/com.google/read'
        }
        
        posts = []
        try:
            while True:
                response = self.session.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get('items', []):
                    url = None
                    if 'canonical' in item and item['canonical']:
                        url = item['canonical'][0]['href']
                    elif 'alternate' in item and item['alternate']:
                        url = item['alternate'][0]['href']
                    
                    if url:
                        published_date = datetime.fromtimestamp(item.get('published', 0))
                        posts.append({
                            'url': url,
                            'date': published_date,
                            'title': item.get('title', 'Sin título'),
                            'month_key': published_date.strftime('%Y-%m'),
                            'feed_title': item.get('origin', {}).get('title', 'Unknown Feed')
                        })
                
                # Paginar solo si el servidor indica que hay más resultados
                continuation = data.get('continuation')
                if not continuation:
                    break
                params['c'] = continuation
                    
            return posts
        except Exception as e:
            logger.error(f"Error obteniendo posts de {stream_id}: {str(e)}")
            raise

class PlaylistManagerRSS:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_path = self.output_dir / PROCESSED_FILE
        self.processed_posts = self._load_processed()
        
    def _load_processed(self) -> set:
        """Carga las URLs de posts ya procesados en ejecuciones anteriores"""
        try:
            with open(self.processed_path, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except FileNotFoundError:
            return set()
        except Exception as e:
            logger.error(f"Error cargando {self.processed_path}: {e}")
            return set()
    
    def _save_processed(self):
        """Guarda las URLs de posts procesados"""
        tmp_path = self.processed_path.with_suffix('.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(sorted(self.processed_posts), f, indent=0)
        tmp_path.replace(self.processed_path)
    
    def filter_new_posts(self, posts: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Descarta los posts cuyas páginas ya se analizaron en ejecuciones anteriores"""
        return [post for post in posts if post['url'] not in self.processed_posts]
        
    def create_m3u_playlist(self, urls: List[str], feed_dir: Path, filename: str):
        """Crea (o amplía) un archivo .m3u con las URLs proporcionadas y su .txt de títulos"""
        # Asegurarse de que existe el directorio del feed
        feed_dir.mkdir(parents=True, exist_ok=True)
        
        playlist_path = feed_dir / f"{filename}.m3u"
        
        # Conservar las entradas existentes y sus títulos ya extraídos
        entries = read_playlist(playlist_path)
        known = {url for url, _ in entries}
        new_urls = [url for url in urls if url not in known]
        if not new_urls:
            logger.debug(f"Sin URLs nuevas para {playlist_path}")
            return None
        
        logger.info(f"Extrayendo {len(new_urls)} títulos para: {playlist_path}")
        entries += zip(new_urls, fetch_titles(new_urls))
        
        with open(playlist_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for url, _ in entries:
                f.write(f"{url}\n")
        with open(playlist_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
            for _, title in entries:
                f.write(f"{title}\n")
                
        logger.info(f"Playlist creada: {playlist_path}")
        return playlist_path
    
    def extract_titles_for_playlist(self, playlist_path: Path):
        """Extrae los títulos de los vídeos/canciones usando yt-dlp"""
        logger.info(f"Extrayendo títulos para: {playlist_path}")
        
        try:
            # Leer URLs del playlist
            with open(playlist_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            titles = fetch_titles(urls)

            # Escribir títulos en un archivo .txt
            txt_path = playlist_path.with_suffix('.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                for title in titles:
                    f.write(f"{title}\n")

            logger.info(f"Archivo de títulos creado: {txt_path}")
            
        except Exception as e:
            logger.error(f"Error durante la extracción de títulos: {str(e)}")
        
    def process_posts(self, posts: List[Dict[str, str]]):
        """Procesa los posts y crea playlists organizadas por feed y mes"""
        # Descargar las páginas de los posts en paralelo
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
            results = list(executor.map(extract_music_urls, [post['url'] for post in posts]))
        
        # Organizar URLs de música por feed y luego por mes
        urls_by_feed_and_month = defaultdict(lambda: defaultdict(list))
        
        for post, music_urls in zip(posts, results):
            if music_urls is None:
                continue  # Error de descarga: se reintentará en la próxima ejecución
            month_urls = urls_by_feed_and_month[post['feed_title']][post['month_key']]
            month_urls.extend(url for url in music_urls if url not in month_urls)
        
        created_playlists = []
        
        # Procesar cada feed
        for feed_title, months in urls_by_feed_and_month.items():
            # Crear un nombre seguro para el directorio del feed
            safe_feed_name = re.sub(r'[^\w\-_]', '_', feed_title)
            feed_dir = self.output_dir / safe_feed_name
            
            # Procesar cada mes del feed
            for month_key, month_urls in months.items():
                if month_urls:
                    playlist_path = self.create_m3u_playlist(month_urls, feed_dir, month_key)
                    if playlist_path:
                        created_playlists.append(str(playlist_path))
        
        # Marcar como procesados los posts descargados correctamente
        self.processed_posts.update(post['url'] for post, music_urls in zip(posts, results) if music_urls is not None)
        self._save_processed()
        
        return created_playlists

    def process_local_playlists(self, local_playlists_dir: str):
        """Procesa playlists locales existentes y genera archivos de títulos"""
        if not local_playlists_dir:
            logger.info("No se proporcionó directorio de playlists locales, saltando...")
            return []

        local_dir = Path(local_playlists_dir)
        if not local_dir.exists():
            logger.warning(f"El directorio de playlists locales no existe: {local_dir}")
            return []
            
        logger.info(f"Procesando playlists locales en: {local_dir}")
        
        # Encontrar todos los archivos .m3u en el directorio y subdirectorios
        m3u_files = list(local_dir.glob('**/*.m3u'))
        logger.info(f"Encontradas {len(m3u_files)} playlists locales")
        
        processed_files = []
        for m3u_file in m3u_files:
            # Comprobar si ya existe un archivo .txt correspondiente
            txt_file = m3u_file.with_suffix('.txt')
            
            # Si el archivo .txt no existe o está vacío, procesarlo
            if not txt_file.exists() or txt_file.stat().st_size == 0:
                logger.info(f"Procesando playlist local: {m3u_file}")
                self.extract_titles_for_playlist(m3u_file)
                processed_files.append(str(m3u_file))
            else:
                logger.info(f"Saltando playlist ya procesada: {m3u_file}")
                
        return processed_files

def main():
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Genera playlists de música desde feeds de blogs en FreshRSS')
    parser.add_argument('--url', required=True, help='URL de FreshRSS')
    parser.add_argument('--username', required=True, help='Nombre de usuario de FreshRSS')
    parser.add_argument('--auth-token', required=True, help='Token de API de FreshRSS')
    parser.add_argument('--output-dir', required=True, help='Directorio para guardar las playlists')
    parser.add_argument('--playlists-locales', help='Directorio con playlists locales existentes para procesar', default='')
    
    args = parser.parse_args()
    
    try:
        # Iniciar proceso
        print(f"Generando playlists desde {args.url}")
        print(f"Guardando en: {args.output_dir}")
        
        # Inicializar objetos
        reader = FreshRSSReader(args.url, args.username, args.auth_token)
        playlist_manager_rss = PlaylistManagerRSS(args.output_dir)
        
        # Login
        if not reader.login():
            print("Error en la autenticación")
            return 1
            
        # Obtener posts no leídos de la categoría Blogs (una sola consulta paginada)
        print("Obteniendo posts de blogs...")
        all_posts = reader.get_unread_posts()
        new_posts = playlist_manager_rss.filter_new_posts(all_posts)
        print(f"Encontrados {len(all_posts)} posts no leídos, {len(new_posts)} sin procesar")
        
        posts_by_feed = defaultdict(int)
        for post in new_posts:
            posts_by_feed[post['feed_title']] += 1
        for feed_title, count in posts_by_feed.items():
            print(f"Procesando feed: {feed_title}")
            print(f"  Obtenidos {count} posts nuevos")
                
        # Crear playlists
        print("Creando playlists...")
        created_playlists = playlist_manager_rss.process_posts(new_posts)
        
        # Procesar playlists locales si se proporcionó un directorio
        if args.playlists_locales:
            print(f"Procesando playlists locales en: {args.playlists_locales}")
            processed_local = playlist_manager_rss.process_local_playlists(args.playlists_locales)
            print(f"Playlists locales procesadas: {len(processed_local)}")
        
        # Mostrar resultados
        print(f"Proceso completado. Posts totales procesados: {len(new_posts)}")
        print(f"Playlists creadas: {len(created_playlists)}")
        for playlist in created_playlists:
            print(f"  - {playlist}")
            
        return 0
        
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())