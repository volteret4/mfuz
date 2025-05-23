#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script que combina funcionalidades de portadas_artistas.py y fotos_artistas.py
para descargar imágenes de artistas y guardar URLs en la base de datos.
"""

import os
import sys
import json
import time
import sqlite3
import logging
import requests
import hashlib
import traceback
from pathlib import Path
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Optional, Union, Any
import urllib3
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from base_module import PROJECT_ROOT


# Añade estas importaciones al principio del archivo
import io
from PIL import Image
import numpy as np
import cv2
from functools import lru_cache

# Añade esta función para calcular un hash perceptual de las imágenes
@lru_cache(maxsize=100)
def calculate_phash(image_path):
    """
    Calcula un hash perceptual de una imagen para detectar duplicados visuales
    independientemente del formato, tamaño o pequeñas variaciones.
    """
    try:
        # Abrir la imagen y convertirla a escala de grises
        img = Image.open(image_path).convert('L')
        # Redimensionar a un tamaño pequeño (32x32)
        img = img.resize((32, 32), Image.LANCZOS)
        
        # Convertir a array de NumPy
        img_array = np.array(img)
        
        # Aplicar DCT (Transformada de Coseno Discreta)
        dct = cv2.dct(np.float32(img_array))
        
        # Recortar a 8x8 para quedarnos con las frecuencias más bajas
        dct_low = dct[:8, :8]
        
        # Calcular el valor medio (excluyendo la primera componente DC)
        avg = (dct_low.sum() - dct_low[0, 0]) / 63
        
        # Generar hash binario
        diff = dct_low > avg
        
        # Convertir el array booleano a un valor entero
        hash_value = 0
        for i, row in enumerate(diff.flatten()):
            if row:
                hash_value |= 1 << i
        
        return hash_value
    except Exception as e:
        logger.error(f"Error al calcular hash perceptual: {e}")
        # Devolver un valor que no coincidirá con ningún otro
        return None

# Función para calcular la similitud entre dos hashes
def hamming_distance(hash1, hash2):
    """Calcula la distancia de Hamming entre dos hashes perceptuales"""
    if hash1 is None or hash2 is None:
        return float('inf')  # Distancia infinita si algún hash es None
    
    # XOR para encontrar bits diferentes
    xor = hash1 ^ hash2
    # Contar bits diferentes
    distance = bin(xor).count('1')
    return distance

# Versión alternativa basada en histogramas si no está disponible OpenCV
def calculate_histogram_similarity(image_path1, image_path2):
    """
    Calcula la similitud entre dos imágenes usando histogramas.
    Útil como alternativa si no está disponible OpenCV.
    """
    try:
        img1 = Image.open(image_path1).convert('RGB').resize((64, 64))
        img2 = Image.open(image_path2).convert('RGB').resize((64, 64))
        
        hist1 = img1.histogram()
        hist2 = img2.histogram()
        
        # Calcular la diferencia cuadrática entre histogramas
        rms = sum((a-b)**2 for a, b in zip(hist1, hist2)) / len(hist1)
        return rms
    except Exception as e:
        logger.error(f"Error al calcular similitud de histogramas: {e}")
        return float('inf')  # Valor alto para que no coincida

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('artistas_imagenes')

# Constantes para las APIs
MUSICBRAINZ_API_BASE = "https://musicbrainz.org/ws/2"
MUSICBRAINZ_COVER_ART = "https://coverartarchive.org"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
USER_AGENT = "MusicArtworkDownloader/1.0 (https://github.com/yourusername/music-art-downloader)"

# Tiempo de espera entre solicitudes para respetar las limitaciones de las APIs
MB_RATE_LIMIT = 1.0  # 1 segundo entre solicitudes para MusicBrainz
SPOTIFY_RATE_LIMIT = 0.2  # 0.2 segundos entre solicitudes para Spotify



# Primero, añade las constantes para las APIs adicionales
DISCOGS_API_BASE = "https://api.discogs.com"
LASTFM_API_BASE = "https://ws.audioscrobbler.com/2.0"

# Añade estas clases después de la clase SpotifyAPI

class DiscogsAPI:
    def __init__(self, token=None):
        self.token = token
        self.last_request_time = 0
    
    def _rate_limit(self) -> None:
        """Implementa el límite de tasa para las solicitudes a Discogs"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < 1.0:  # Máximo 60 solicitudes por minuto
            time.sleep(1.0 - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
        """Realiza una solicitud a la API de Discogs"""
        self._rate_limit()
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json'
        }
        
        if self.token:
            headers['Authorization'] = f"Discogs token={self.token}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error en la solicitud a Discogs: {e}")
            return None
    
    def search_artist(self, name: str) -> Optional[Dict[str, Any]]:
        """Busca un artista por nombre"""
        query = quote_plus(name)
        url = f"{DISCOGS_API_BASE}/database/search?q={query}&type=artist&per_page=1"
        data = self._make_request(url)
        
        if data and 'results' in data and data['results']:
            return data['results'][0]
        return None
    
    def get_artist_images(self, artist_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extrae las URL de las imágenes de un artista"""
        images = []
        
        # Imagen principal de resultados de búsqueda
        if 'cover_image' in artist_data and artist_data['cover_image']:
            images.append({
                'url': artist_data['cover_image'],
                'type': 'artist',
                'source': 'discogs'
            })
        
        # Si hay un ID de artista, obtenemos más detalles
        if 'id' in artist_data:
            artist_id = artist_data['id']
            url = f"{DISCOGS_API_BASE}/artists/{artist_id}"
            details = self._make_request(url)
            
            if details and 'images' in details:
                for img in details['images']:
                    if img.get('uri'):
                        images.append({
                            'url': img['uri'],
                            'type': 'artist',
                            'source': 'discogs',
                            'width': img.get('width'),
                            'height': img.get('height')
                        })
        
        return images


class LastfmAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.last_request_time = 0
    
    def _rate_limit(self) -> None:
        """Implementa el límite de tasa para las solicitudes a Last.fm"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < 0.25:  # Máximo 5 solicitudes por segundo
            time.sleep(0.25 - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def _make_request(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Realiza una solicitud a la API de Last.fm con mejor manejo de errores"""
        self._rate_limit()
        
        if not self.api_key:
            logger.warning("No se proporcionó API key de Last.fm")
            return None
        
        params['api_key'] = self.api_key
        params['format'] = 'json'
        
        # Configurar sesión con reintentos
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        try:
            # Intentar con verificación SSL
            response = session.get(LASTFM_API_BASE, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError:
            # Si falla por SSL, intentar sin verificación
            logger.warning("Error SSL en solicitud a Last.fm. Reintentando sin verificación SSL.")
            try:
                response = session.get(LASTFM_API_BASE, params=params, timeout=10, verify=False)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                logger.error(f"Error en solicitud a Last.fm sin SSL: {e}")
                return None
        except requests.RequestException as e:
            logger.error(f"Error en solicitud a Last.fm: {e}")
            return None
    
    def get_artist_images(self, artist_name: str) -> List[Dict[str, str]]:
        """Obtiene las URL de las imágenes de un artista con URLs alternativas"""
        data = self.get_artist_info(artist_name)
        images = []
        
        if data and 'artist' in data:
            # Intentar obtener imágenes de la respuesta API
            if 'image' in data['artist']:
                for img in data['artist']['image']:
                    if img['#text'] and img['#text'] != '':
                        # Comprobar si es una URL de imagen por defecto
                        if '2a96cbd8b46e442fc41c2b86b821562f' in img['#text']:
                            continue  # Omitir imágenes por defecto
                        
                        # Usar CDN alternativo si es de lastfm.freetls.fastly.net
                        url = img['#text']
                        if 'lastfm.freetls.fastly.net' in url:
                            # Intentar obtener una URL alternativa
                            url = url.replace('lastfm.freetls.fastly.net', 'lastfm-img2.akamaized.net')
                        
                        images.append({
                            'url': url,
                            'type': 'artist',
                            'source': 'lastfm',
                            'size': img['size']
                        })
            
            # Intentar obtener URL de la wiki si existe
            if 'url' in data['artist']:
                artist_url = data['artist']['url']
                artist_mbid = data['artist'].get('mbid', '')
                
                # Si tenemos un MBID, podemos construir una URL de imagen alternativa
                if artist_mbid:
                    alt_image_url = f"https://www.last.fm/music/{artist_name.replace(' ', '+')}/+images"
                    images.append({
                        'url': alt_image_url,
                        'type': 'artist',
                        'source': 'lastfm_page',
                        'is_page': True  # Indicar que es una página, no una imagen directa
                    })
        
        return images
    
    def get_artist_info(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un artista por su nombre"""
        params = {
            'method': 'artist.getinfo',
            'artist': artist_name
        }
        
        return self._make_request(params)
    



def get_file_hash(file_path):
    """Calcula el hash MD5 de un archivo"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class MusicBrainzAPI:
    def __init__(self):
        self.last_request_time = 0
    
    def _rate_limit(self) -> None:
        """Implementa el límite de tasa para las solicitudes a MusicBrainz"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < MB_RATE_LIMIT:
            time.sleep(MB_RATE_LIMIT - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
        """Realiza una solicitud a la API de MusicBrainz"""
        self._rate_limit()
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error en la solicitud a MusicBrainz: {e}")
            return None
    
    def get_artist_images(self, mbid: str) -> List[Dict[str, str]]:
        """Obtiene las URL de las imágenes de un artista por su MBID"""
        url = f"{MUSICBRAINZ_API_BASE}/artist/{mbid}?inc=url-rels&fmt=json"
        data = self._make_request(url)
        
        if not data:
            return []
        
        # Buscar relaciones de URL que puedan contener imágenes
        image_urls = []
        if 'relations' in data:
            for relation in data['relations']:
                if relation['type'] == 'image' and 'url' in relation:
                    image_urls.append({
                        'url': relation['url']['resource'],
                        'type': 'artist'
                    })
        
        return image_urls


class SpotifyAPI:
    def __init__(self, spotify_client_id: str = "", spotify_client_secret: str = ""):
        self.client_id = spotify_client_id
        self.client_secret = spotify_client_secret
        self.access_token = None
        self.token_expiry = 0
        self.last_request_time = 0
    
    def _rate_limit(self) -> None:
        """Implementa el límite de tasa para las solicitudes a Spotify"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < SPOTIFY_RATE_LIMIT:
            time.sleep(SPOTIFY_RATE_LIMIT - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def _get_token(self) -> bool:
        """Obtiene un token de acceso para la API de Spotify"""
        if self.access_token and time.time() < self.token_expiry:
            return True
        
        if not self.client_id or not self.client_secret:
            logger.warning("No se proporcionaron credenciales de Spotify")
            return False
        
        auth_url = "https://accounts.spotify.com/api/token"
        auth_response = requests.post(auth_url, {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        })
        
        if auth_response.status_code != 200:
            logger.error(f"Error al obtener token de Spotify: {auth_response.text}")
            return False
        
        auth_data = auth_response.json()
        self.access_token = auth_data['access_token']
        self.token_expiry = time.time() + auth_data['expires_in'] - 60  # Restar 60 segundos por seguridad
        return True
    
    def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
        """Realiza una solicitud a la API de Spotify"""
        if not self._get_token():
            return None
        
        self._rate_limit()
        
        headers = {
            'Authorization': f"Bearer {self.access_token}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error en la solicitud a Spotify: {e}")
            return None
    
    def search_artist(self, name: str) -> Optional[Dict[str, Any]]:
        """Busca un artista por nombre"""
        query = f"artist:{quote_plus(name)}"
        url = f"{SPOTIFY_API_BASE}/search?q={query}&type=artist&limit=1"
        data = self._make_request(url)
        
        if data and 'artists' in data and 'items' in data['artists'] and data['artists']['items']:
            return data['artists']['items'][0]
        return None
    
    def get_artist_images(self, artist_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extrae las URL de las imágenes de un artista"""
        if 'images' not in artist_data:
            return []
        
        return [{'url': img['url'], 'type': 'artist', 'width': img['width'], 'height': img['height']} 
                for img in artist_data['images']]
    
    def get_artist_by_id(self, spotify_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un artista por su ID de Spotify"""
        url = f"{SPOTIFY_API_BASE}/artists/{spotify_id}"
        return self._make_request(url)


class ArtistasImagenes:
    def __init__(self, db_path=None, force_update=False, project_root=None, images_folder=None, albums_folder=None):
        self.db_path = db_path
        self.project_root = PROJECT_ROOT
        self.force_update = force_update  # Nueva opción para forzar actualización
        

        # Configuración de carpetas para guardar imágenes
        if images_folder == None and albums_folder == None:
            if self.project_root:
                self.images_folder = os.path.join(self.project_root, ".content", "artistas_img")
                if not os.path.exists(self.images_folder):
                    os.makedirs(self.images_folder)
                self.albums_folder = os.path.join(self.project_root, ".content", "albums_img")
                if not os.path.exists(self.albums_folder):
                    os.makedirs(self.albums_folder)

            else:
                self.images_folder = os.path.join(os.path.expanduser("~"), ".cache", "music_app", "artistas_img")
                self.albums_folder = os.path.join(os.path.expanduser("~"), ".cache", "music_app", "albums_img")
        else:
            self.images_folder = images_folder
            self.albums_folder = albums_folder
            
        os.makedirs(self.images_folder, exist_ok=True)
        os.makedirs(self.albums_folder, exist_ok=True)
        
        # APIs para artistas
        self.spotify = SpotifyAPI()
        self.musicbrainz = MusicBrainzAPI()
        self.discogs = DiscogsAPI()
        self.lastfm = LastfmAPI()
        
        # APIs para álbumes
        self.spotify_album = None
        self.musicbrainz_album = None
        self.discogs_album = None
        self.lastfm_album = None
        
        # Conexión a la base de datos
        self.conn = None
        self.cursor = None
        
        # Estadísticas
        self.stats = {
            'total_artists': 0,
            'processed_artists': 0,
            'artists_downloaded': 0,
            'artists_urls_saved': 0,
            'artists_failed': 0,
            'total_albums': 0,
            'processed_albums': 0,
            'albums_downloaded': 0,
            'albums_urls_saved': 0,
            'albums_failed': 0,
            'sources': {
                'spotify': 0,
                'musicbrainz': 0,
                'discogs': 0,
                'lastfm': 0,
                'none': 0
            }
        }
    


    def setup_apis(self, spotify_client_id="", spotify_client_secret="", 
                  discogs_token="", lastfm_api_key=""):
        """Configura todas las APIs"""
        # Configurar APIs de artistas
        self.spotify = SpotifyAPI(spotify_client_id, spotify_client_secret)
        self.discogs = DiscogsAPI(discogs_token)
        self.lastfm = LastfmAPI(lastfm_api_key)
        
        # Configurar APIs de álbumes
        self.spotify_album = SpotifyAlbumAPI(spotify_client_id, spotify_client_secret)
        self.musicbrainz_album = MusicBrainzAlbumAPI()
        self.discogs_album = DiscogsAlbumAPI(discogs_token)
        self.lastfm_album = LastfmAlbumAPI(lastfm_api_key)
        
        logger.info("APIs configuradas")

    def get_discogs_images(self, artist_name):
        """Obtiene imágenes de artista desde Discogs"""
        images = []
        
        artist_data = self.discogs.search_artist(artist_name)
        if artist_data:
            images = self.discogs.get_artist_images(artist_data)
        
        return images

    def get_lastfm_images(self, artist_name):
        """Obtiene imágenes de artista desde Last.fm"""
        return self.lastfm.get_artist_images(artist_name)



    def connect_db(self):
        """Conecta a la base de datos"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"Conectado a la base de datos: {self.db_path}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al conectar a la base de datos: {e}")
            return False
    
    def disconnect_db(self):
        """Desconecta de la base de datos"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
            logger.info("Desconectado de la base de datos")
    
    def setup_spotify(self, client_id, client_secret):
        """Configura el cliente de Spotify"""
        self.spotify = SpotifyAPI(client_id, client_secret)
        logger.info("Cliente de Spotify configurado")
    
    
    def get_artists(self):
        """Obtiene todos los artistas de la base de datos con sus datos de imágenes"""
        try:
            self.cursor.execute("""
                SELECT a.id, a.name, a.mbid, a.img, a.img_paths, a.img_urls, n.spotify as spotify_url
                FROM artists a
                LEFT JOIN artists_networks n ON a.id = n.artist_id
            """)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error al obtener artistas: {e}")
            return []
    
    def get_artist_image_path(self, artist_name, index=1):
        """Determina la ruta donde se guardará la imagen del artista"""
        # Sanitizar el nombre del artista para usarlo como carpeta
        safe_name = "".join(c for c in artist_name if c.isalnum() or c in " ").strip()
        safe_name = safe_name.replace(" ", "_")
        
        artist_dir = os.path.join(self.images_folder, safe_name)
        os.makedirs(artist_dir, exist_ok=True)
        
        return os.path.join(artist_dir, f"image_{index}.jpg")
    
    def download_image(self, url, output_path):
        """Descarga una imagen desde una URL y la guarda en disco con manejo mejorado de errores"""
        try:
            if not url:
                return False
            
            # Configurar sesión con reintentos y manejo de certificados SSL
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # Verificar si es una URL de Last.fm que está fallando con SSL
            verify_ssl = True
            if 'lastfm.freetls.fastly.net' in url:
                verify_ssl = False
                logger.warning(f"Deshabilitando verificación SSL para URL de Last.fm: {url}")
            
            # Añadir referenciador y User-Agent para evitar 403 Forbidden
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.google.com/'
            }
            
            response = session.get(url, stream=True, timeout=15, headers=headers, verify=verify_ssl)
            
            # Si la respuesta tiene código 403, intentamos con otro User-Agent
            if response.status_code == 403:
                logger.info(f"Reintentando con User-Agent alternativo: {url}")
                headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15'
                response = session.get(url, stream=True, timeout=15, headers=headers, verify=verify_ssl)
            
            if response.status_code != 200:
                logger.warning(f"Error al descargar imagen: {response.status_code} - URL: {url}")
                return False
            
            # Verificar que realmente es una imagen
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"El contenido no es una imagen. Content-Type: {content_type} - URL: {url}")
                return False
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verificar tamaño mínimo para asegurar que la imagen es válida
            if os.path.getsize(output_path) < 1000:  # menos de 1KB, probablemente no sea una imagen válida
                logger.warning(f"La imagen descargada es demasiado pequeña: {os.path.getsize(output_path)} bytes - URL: {url}")
                os.remove(output_path)  # Eliminar archivo pequeño
                return False
            
            logger.info(f"Imagen descargada: {output_path}")
            return True
        except requests.exceptions.SSLError as e:
            logger.error(f"Error SSL al descargar imagen: {str(e)} - URL: {url}")
            # Intentar sin verificación SSL si ese fue el problema
            try:
                if 'certificate verify failed' in str(e):
                    logger.info(f"Reintentando sin verificación SSL: {url}")
                    response = requests.get(url, stream=True, timeout=15, headers=headers, verify=False)
                    if response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        logger.info(f"Imagen descargada (sin SSL): {output_path}")
                        return True
            except Exception as retry_err:
                logger.error(f"Error en segundo intento: {str(retry_err)} - URL: {url}")
            return False
        except Exception as e:
            logger.error(f"Error descargando imagen: {str(e)} - URL: {url}")
            return False
    
    def get_spotify_images(self, artist_name, artist_id, spotify_url=None):
        """Obtiene imágenes de artista desde Spotify"""
        images = []
        artist_data = None
        
        # Si tenemos URL de Spotify, extraer el ID
        if spotify_url:
            try:
                spotify_id = spotify_url.split('/')[-1]
                artist_data = self.spotify.get_artist_by_id(spotify_id)
            except Exception as e:
                logger.debug(f"Error al obtener artista de Spotify por URL: {e}")
        
        # Si no tenemos URL o falló, buscar por nombre
        if not artist_data:
            artist_data = self.spotify.search_artist(artist_name)
        
        if artist_data:
            images = self.spotify.get_artist_images(artist_data)
            
        return images
    
    def get_musicbrainz_images(self, artist_name, mbid=None):
        """Obtiene imágenes de artista desde MusicBrainz"""
        images = []
        
        if mbid:
            images = self.musicbrainz.get_artist_images(mbid)
        
        return images
    
    def update_artist_image(self, artist_id, image_paths, img_urls=None):
        """Actualiza las imágenes del artista en la base de datos"""
        try:
            if image_paths:
                # Actualizar la columna img con la primera imagen (para compatibilidad)
                self.cursor.execute("UPDATE artists SET img = ? WHERE id = ?", 
                                (image_paths[0], artist_id))
                
                # Guardar todas las rutas en la columna img_paths
                img_paths_json = json.dumps(image_paths)
                self.cursor.execute("UPDATE artists SET img_paths = ? WHERE id = ?", 
                                (img_paths_json, artist_id))
            
            # Si tenemos URLs de imágenes, actualizarlas en img_urls
            if img_urls:
                # Convertir a formato JSON
                img_urls_json = json.dumps(img_urls)
                self.cursor.execute("UPDATE artists SET img_urls = ? WHERE id = ?", 
                                (img_urls_json, artist_id))
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al actualizar imagen de artista: {e}")
            return False
    
    def process_artist(self, artist, descargar_img=True, guardar_url=True):
        """Procesa un artista para descargar imágenes y/o guardar URLs"""
        artist_id = artist['id']
        artist_name = artist['name']
        mbid = artist.get('mbid')
        spotify_url = artist.get('spotify_url')
        
        # Verificar si ya tiene datos y omitir si no se requiere actualización forzada
        existing_img = artist.get('img')
        existing_paths = artist.get('img_paths')
        existing_urls = artist.get('img_urls')
        
        # Si no se requiere actualización forzada y ya tiene datos, omitir
        if not self.force_update:
            # Si descargar_img=True y ya tiene imgs, omitir
            if descargar_img and existing_img and (existing_paths or os.path.exists(existing_img)):
                logger.info(f"Artista {artist_name} ya tiene imágenes descargadas. Omitiendo.")
                return True
            
            # Si guardar_url=True y ya tiene URLs, omitir
            if guardar_url and existing_urls:
                logger.info(f"Artista {artist_name} ya tiene URLs guardadas. Omitiendo.")
                return True
        
        logger.info(f"Procesando artista: {artist_name}")
        
        # Obtener imágenes de todas las fuentes
        spotify_images = self.get_spotify_images(artist_name, artist_id, spotify_url)
        mb_images = self.get_musicbrainz_images(artist_name, mbid)
        discogs_images = self.get_discogs_images(artist_name)
        lastfm_images = self.get_lastfm_images(artist_name)
        
        # Combinar todas las imágenes
        all_images = spotify_images + mb_images + discogs_images + lastfm_images
        
        if not all_images:
            logger.warning(f"No se encontraron imágenes para {artist_name}")
            self.stats['sources']['none'] = self.stats['sources'].get('none', 0) + 1
            self.stats['artists_failed'] += 1
            return False
        
        # Registrar las fuentes
        for img in all_images:
            source = img.get('source', 'unknown')
            self.stats['sources'][source] = self.stats['sources'].get(source, 0) + 1
        
        # Si solo necesitamos guardar URLs
        if guardar_url and not descargar_img:
            # Eliminar URLs duplicadas
            img_urls = []
            url_set = set()
            
            for img in all_images:
                if img['url'] not in url_set:
                    url_set.add(img['url'])
                    img_urls.append(img)
            
            if self.update_artist_image(artist_id, None, img_urls):
                logger.info(f"URLs de imágenes guardadas para {artist_name}")
                self.stats['artists_urls_saved'] += 1
                return True
        
        # Si necesitamos descargar imágenes
        if descargar_img:
            # Ordenar por tamaño si hay información de dimensiones
            def image_sort_key(img):
                if 'width' in img and 'height' in img:
                    return img['width'] * img['height']
                elif 'size' in img:
                    sizes = {'small': 1, 'medium': 2, 'large': 3, 'extralarge': 4, 'mega': 5}
                    return sizes.get(img['size'], 0)
                return 0
            
            all_images.sort(key=image_sort_key, reverse=True)
            
            # Preparar directorio para el artista
            safe_name = "".join(c for c in artist_name if c.isalnum() or c in " ").strip()
            safe_name = safe_name.replace(" ", "_")
            artist_dir = os.path.join(self.images_folder, safe_name)
            os.makedirs(artist_dir, exist_ok=True)
            
            # Carpeta temporal para verificar duplicados
            temp_dir = os.path.join(artist_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Descargar imágenes a carpeta temporal
            downloaded_temp_paths = []
            
            # Primera pasada: descargar todas las imágenes a carpeta temporal
            max_attempts = min(15, len(all_images))  # Intentar con más imágenes disponibles
            
            for i, img in enumerate(all_images[:max_attempts]):
                temp_path = os.path.join(temp_dir, f"temp_{i+1}.jpg")
                
                if self.download_image(img['url'], temp_path):
                    # Verificar que la imagen es válida
                    try:
                        with Image.open(temp_path) as im:
                            width, height = im.size
                            # Descartar imágenes muy pequeñas
                            if width < 50 or height < 50:
                                logger.warning(f"Imagen demasiado pequeña descartada: {width}x{height}")
                                os.remove(temp_path)
                                continue
                        
                        downloaded_temp_paths.append((temp_path, img))
                    except Exception as e:
                        logger.warning(f"No es una imagen válida: {e}")
                        try:
                            os.remove(temp_path)
                        except:
                            pass
            
            # Segunda pasada: detectar duplicados visuales
            unique_images = []
            phashes = []
            
            # Intentar usar hash perceptual primero
            try:
                import cv2  # Verificar que OpenCV está disponible
                
                for i, (temp_path, img) in enumerate(downloaded_temp_paths):
                    phash = calculate_phash(temp_path)
                    
                    # Si no pudimos calcular el hash, continuar con la siguiente
                    if phash is None:
                        continue
                    
                    # Verificar si es un duplicado visual
                    is_duplicate = False
                    for j, existing_hash in enumerate(phashes):
                        # Umbral para considerar imágenes similares (ajustable)
                        if hamming_distance(phash, existing_hash) < 10:  # Umbral bajo = más estricto
                            is_duplicate = True
                            logger.info(f"Imagen {i+1} es duplicado visual de imagen {j+1}")
                            
                            # Verificar cuál tiene mejor calidad (tamaño de archivo)
                            current_size = os.path.getsize(temp_path)
                            existing_size = os.path.getsize(unique_images[j][0])
                            
                            if current_size > existing_size * 1.2:  # 20% más grande
                                # Reemplazar la existente con esta de mejor calidad
                                logger.info(f"Reemplazando imagen {j+1} con versión de mayor calidad")
                                unique_images[j] = (temp_path, img)
                            break
                    
                    if not is_duplicate:
                        phashes.append(phash)
                        unique_images.append((temp_path, img))
                        
                        # Limitamos a 5 imágenes únicas
                        if len(unique_images) >= 5:
                            break
                            
            except (ImportError, NameError):
                logger.warning("OpenCV no disponible, usando comparación de histogramas")
                
                # Si OpenCV no está disponible, usar comparación de histogramas
                for temp_path, img in downloaded_temp_paths:
                    is_duplicate = False
                    
                    for existing_path, _ in unique_images:
                        similarity = calculate_histogram_similarity(temp_path, existing_path)
                        # Umbral para considerar duplicados (menor = más similar)
                        if similarity < 5000:  # Ajustar según resultados
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        unique_images.append((temp_path, img))
                        
                        # Limitamos a 5 imágenes únicas
                        if len(unique_images) >= 5:
                            break
            
            # Tercera pasada: mover archivos únicos a su ubicación final
            downloaded_paths = []
            saved_img_info = []
            
            for i, (temp_path, img) in enumerate(unique_images):
                source = img.get('source', 'unknown')
                final_path = os.path.join(artist_dir, f"image_{i+1}_{source}.jpg")
                
                try:
                    # Copiar archivo de la carpeta temporal a la ubicación final
                    import shutil
                    shutil.copy2(temp_path, final_path)
                    downloaded_paths.append(final_path)
                    
                    # Guardar información de la imagen
                    img_info = {
                        'url': img['url'], 
                        'path': final_path,
                        'source': source
                    }
                    saved_img_info.append(img_info)
                except Exception as e:
                    logger.error(f"Error al mover imagen: {e}")
            
            # Limpieza: eliminar carpeta temporal
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Error al eliminar directorio temporal: {e}")
            
            if downloaded_paths:
                # Actualizar la base de datos con todas las rutas y las URLs
                if self.update_artist_image(artist_id, downloaded_paths, saved_img_info if guardar_url else None):
                    logger.info(f"Imágenes y URLs actualizadas para {artist_name}. Imágenes únicas: {len(downloaded_paths)}")
                    self.stats['artists_downloaded'] += 1
                    return True
            
        logger.warning(f"No se pudo procesar completamente {artist_name}")
        self.stats['artists_failed'] += 1
        return False
    
    def run(self, descargar_img_artistas=True, guardar_url_artistas=True, 
            descargar_img_albums=False, guardar_url_albums=False):
        """Ejecuta el proceso para artistas y/o álbumes"""
        if not self.connect_db():
            return self.stats
        
        try:
            # Verificar y crear columnas si es necesario
            if not self.ensure_columns_exist():
                logger.error("No se pudo verificar/crear la estructura de la base de datos")
                return self.stats
            
            # Procesar artistas si se solicita
            if descargar_img_artistas or guardar_url_artistas:
                artists = self.get_artists()
                self.stats['total_artists'] = len(artists)
                
                logger.info(f"Procesando {len(artists)} artistas...")
                
                for i, artist in enumerate(artists):
                    self.stats['processed_artists'] = i + 1
                    
                    # Mostrar progreso
                    if i % 10 == 0 or i == len(artists) - 1:
                        progress = (i + 1) / len(artists) * 100
                        logger.info(f"Progreso artistas: {progress:.1f}% ({i+1}/{len(artists)})")
                    
                    if not self.process_artist(artist, descargar_img_artistas, guardar_url_artistas):
                        logger.debug(f"No se pudo procesar el artista {artist['name']}")
                    
                    # Pequeña pausa para no sobrecargar la base de datos y APIs
                    time.sleep(0.1)
            
            # Procesar álbumes si se solicita
            if descargar_img_albums or guardar_url_albums:
                albums = self.get_albums()
                self.stats['total_albums'] = len(albums)
                
                logger.info(f"Procesando {len(albums)} álbumes...")
                
                for i, album in enumerate(albums):
                    self.stats['processed_albums'] = i + 1
                    
                    # Mostrar progreso
                    if i % 10 == 0 or i == len(albums) - 1:
                        progress = (i + 1) / len(albums) * 100
                        logger.info(f"Progreso álbumes: {progress:.1f}% ({i+1}/{len(albums)})")
                    
                    if not self.process_album(album, descargar_img_albums, guardar_url_albums):
                        logger.debug(f"No se pudo procesar el álbum {album['name']}")
                    
                    # Pequeña pausa para no sobrecargar la base de datos y APIs
                    time.sleep(0.1)
            
            logger.info("Proceso completado.")
            logger.info(f"Resultados artistas: {self.stats['artists_downloaded']} imágenes descargadas, " +
                        f"{self.stats['artists_urls_saved']} URL guardadas, " +
                        f"{self.stats['artists_failed']} fallidos.")
            logger.info(f"Resultados álbumes: {self.stats['albums_downloaded']} carátulas descargadas, " +
                        f"{self.stats['albums_urls_saved']} URL guardadas, " +
                        f"{self.stats['albums_failed']} fallidos.")
            
        except Exception as e:
            logger.error(f"Error durante la ejecución: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.disconnect_db()
        
        return self.stats


    def get_album_image_path(self, artist_name, album_name, index=1):
        """Determina la ruta donde se guardará la imagen del álbum"""
        # Sanitizar nombres para usarlos como carpeta
        safe_artist = "".join(c for c in artist_name if c.isalnum() or c in " ").strip()
        safe_artist = safe_artist.replace(" ", "_")
        
        safe_album = "".join(c for c in album_name if c.isalnum() or c in " ").strip()
        safe_album = safe_album.replace(" ", "_")
        
        album_dir = os.path.join(self.albums_folder, f"{safe_artist}_-_{safe_album}")
        os.makedirs(album_dir, exist_ok=True)
        
        return os.path.join(album_dir, f"cover_{index}.jpg")



    def get_albums(self):
        """Obtiene todos los álbumes de la base de datos con sus datos de imágenes"""
        try:
            self.cursor.execute("""
                SELECT a.id, a.name, a.album_art_path, a.album_art_urls, a.mbid, 
                    art.name as artist_name 
                FROM albums a
                JOIN artists art ON a.artist_id = art.id
            """)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error al obtener álbumes: {e}")
            return []
    
    def update_album_cover(self, album_id, image_path, img_urls=None):
        """Actualiza la carátula del álbum en la base de datos"""
        try:
            # Actualizar la columna album_art_path en la tabla albums
            self.cursor.execute("UPDATE albums SET album_art_path = ? WHERE id = ?", 
                            (image_path, album_id))
            
            # Si tenemos URLs de imágenes, actualizarlas en album_art_urls
            if img_urls:
                # Convertir a formato JSON
                img_urls_json = json.dumps(img_urls)
                self.cursor.execute("UPDATE albums SET album_art_urls = ? WHERE id = ?", 
                                (img_urls_json, album_id))
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al actualizar carátula de álbum: {e}")
            return False
    
    def get_album_covers(self, artist_name, album_name, album_mbid=None):
        """Obtiene carátulas de un álbum desde todas las fuentes"""
        spotify_images = self.spotify_album.get_album_cover(artist_name, album_name, album_mbid)
        mb_images = self.musicbrainz_album.get_album_cover(artist_name, album_name, album_mbid)
        discogs_images = self.discogs_album.get_album_cover(artist_name, album_name, album_mbid)
        lastfm_images = self.lastfm_album.get_album_cover(artist_name, album_name, album_mbid)
        
        return spotify_images + mb_images + discogs_images + lastfm_images
    
    def process_album(self, album, descargar_img=True, guardar_url=True):
        """Procesa un álbum para descargar carátula y/o guardar URLs"""
        album_id = album['id']
        album_name = album['name']
        artist_name = album['artist_name']
        mbid = album.get('mbid')
        existing_cover = album.get('album_art_path')
        
        # Verificar si ya tiene datos y omitir si no se requiere actualización forzada
        existing_cover = album.get('album_art_path')
        existing_urls = album.get('album_art_urls')
        
        # Si no se requiere actualización forzada y ya tiene datos, omitir
        if not self.force_update:
            # Si descargar_img=True y ya tiene carátula, omitir
            if descargar_img and existing_cover and os.path.exists(existing_cover):
                logger.info(f"Álbum {album_name} ya tiene carátula. Omitiendo.")
                return True
            
            # Si guardar_url=True y ya tiene URLs, omitir
            if guardar_url and existing_urls:
                logger.info(f"Álbum {album_name} ya tiene URLs guardadas. Omitiendo.")
                return True
        
        logger.info(f"Procesando álbum: {album_name} de {artist_name}")
        
        # Si ya existe una carátula y no queremos sobrescribir
        if existing_cover and os.path.exists(existing_cover) and not descargar_img:
            logger.info(f"El álbum ya tiene carátula: {existing_cover}")
            return True
        
        # Obtener imágenes de todas las fuentes
        all_images = self.get_album_covers(artist_name, album_name, mbid)
        
        if not all_images:
            logger.warning(f"No se encontraron carátulas para {album_name} de {artist_name}")
            self.stats['sources']['none'] = self.stats['sources'].get('none', 0) + 1
            self.stats['albums_failed'] += 1
            return False
        
        # Registrar las fuentes
        for img in all_images:
            source = img.get('source', 'unknown')
            self.stats['sources'][source] = self.stats['sources'].get(source, 0) + 1
        
        # Si solo necesitamos guardar URLs
        if guardar_url and not descargar_img:
            # Eliminar URLs duplicadas
            img_urls = []
            url_set = set()
            
            for img in all_images:
                if img['url'] not in url_set:
                    url_set.add(img['url'])
                    img_urls.append(img)
            
            if self.update_album_cover(album_id, existing_cover, img_urls):
                logger.info(f"URLs de carátulas guardadas para {album_name}")
                self.stats['albums_urls_saved'] += 1
                return True
        
        # Si necesitamos descargar imágenes
        if descargar_img:
            # Priorizar imágenes frontales y ordenar por tamaño
            def image_sort_key(img):
                score = 0
                
                # Priorizar imágenes marcadas como frontales
                if img.get('front', False):
                    score += 1000
                
                # Añadir puntuación basada en dimensiones
                if 'width' in img and 'height' in img:
                    score += img['width'] * img['height']
                elif 'size' in img:
                    sizes = {'small': 1, 'medium': 2, 'large': 3, 'extralarge': 4, 'mega': 5}
                    score += sizes.get(img['size'], 0) * 100
                
                # Priorizar fuentes más confiables
                source_priority = {'spotify': 3, 'musicbrainz': 2, 'discogs': 1, 'lastfm': 0}
                score += source_priority.get(img.get('source', ''), 0) * 10
                
                return score
            
            all_images.sort(key=image_sort_key, reverse=True)
            
            # Preparar directorio para el álbum
            temp_dir = os.path.join(self.albums_folder, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Intentar descargar las mejores imágenes
            downloaded_path = None
            saved_img_info = None
            
            for i, img in enumerate(all_images[:5]):  # Intentar con las 5 mejores
                if downloaded_path:
                    break  # Ya hemos encontrado una buena imagen
                
                temp_path = os.path.join(temp_dir, f"temp_album_{i+1}.jpg")
                
                if self.download_image(img['url'], temp_path):
                    # Verificar calidad mínima
                    try:
                        with Image.open(temp_path) as im:
                            width, height = im.size
                            if width < 300 or height < 300:
                                logger.warning(f"Imagen demasiado pequeña: {width}x{height}")
                                continue
                        
                        # Encontramos una buena imagen!
                        final_path = self.get_album_image_path(artist_name, album_name)
                        
                        # Copiar archivo final
                        import shutil
                        shutil.copy2(temp_path, final_path)
                        
                        downloaded_path = final_path
                        saved_img_info = [{
                            'url': img['url'],
                            'path': final_path,
                            'source': img.get('source', 'unknown')
                        }]
                        
                        logger.info(f"Carátula descargada para {album_name}: {final_path}")
                    except Exception as e:
                        logger.warning(f"Error procesando imagen: {e}")
            
            # Limpieza de archivos temporales
            try:
                import shutil
                for file in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, file))
            except Exception as e:
                logger.warning(f"Error al limpiar archivos temporales: {e}")
            
            # Actualizar base de datos
            if downloaded_path:
                if self.update_album_cover(album_id, downloaded_path, saved_img_info if guardar_url else None):
                    logger.info(f"Carátula y URLs actualizadas para {album_name}")
                    self.stats['albums_downloaded'] += 1
                    return True
                
            # Si no pudimos descargar pero queremos guardar URLs
            elif guardar_url:
                img_urls = []
                url_set = set()
                
                for img in all_images:
                    if img['url'] not in url_set:
                        url_set.add(img['url'])
                        img_urls.append(img)
                
                if self.update_album_cover(album_id, existing_cover, img_urls):
                    logger.info(f"No se descargó carátula pero se guardaron URLs para {album_name}")
                    self.stats['albums_urls_saved'] += 1
                    return True
        
        logger.warning(f"No se pudo procesar completamente el álbum {album_name}")
        self.stats['albums_failed'] += 1
        return False


    def ensure_columns_exist(self):
        """Verifica que las columnas necesarias existan en las tablas"""
        try:
            # Verificar las columnas existentes en la tabla artists
            self.cursor.execute("PRAGMA table_info(artists)")
            artist_columns = [col[1] for col in self.cursor.fetchall()]
            
            # Verificar y añadir columnas para artistas
            if 'img' not in artist_columns:
                logger.info("Creando columna 'img' en la tabla artists")
                self.cursor.execute("ALTER TABLE artists ADD COLUMN img TEXT")
            
            if 'img_urls' not in artist_columns:
                logger.info("Creando columna 'img_urls' en la tabla artists")
                self.cursor.execute("ALTER TABLE artists ADD COLUMN img_urls TEXT")
            
            if 'img_paths' not in artist_columns:
                logger.info("Creando columna 'img_paths' en la tabla artists")
                self.cursor.execute("ALTER TABLE artists ADD COLUMN img_paths TEXT")
            
            # Verificar las columnas existentes en la tabla albums
            self.cursor.execute("PRAGMA table_info(albums)")
            album_columns = [col[1] for col in self.cursor.fetchall()]
            
            # Verificar y añadir columnas para álbumes
            if 'album_art_urls' not in album_columns:
                logger.info("Creando columna 'album_art_urls' en la tabla albums")
                self.cursor.execute("ALTER TABLE albums ADD COLUMN album_art_urls TEXT")
                
            self.conn.commit()
            logger.info("Estructura de la base de datos verificada y actualizada")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al verificar/crear columnas: {e}")
            return False

    def is_valid_image_url(url):
        """Verifica si una URL parece ser una imagen válida"""
        # Verificar extensión
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff']
        if any(url.lower().endswith(ext) for ext in image_extensions):
            return True
        
        # Verificar patrones comunes de URLs de imagen
        image_patterns = [
            '/images/', 'image', 'picture', 'photo', 'avatar', 'cover', 
            'albumart', 'artwork', '/img/', '.img.', 'media'
        ]
        
        if any(pattern in url.lower() for pattern in image_patterns):
            return True
        
        return False

# Añadir nuevas APIs para obtener carátulas de álbumes

class AlbumArtAPI:
    """Clase base para descarga de carátulas de álbumes"""
    def get_album_cover(self, artist_name, album_name, album_mbid=None):
        raise NotImplementedError("Esta clase base debe ser implementada por subclases")


class SpotifyAlbumAPI(SpotifyAPI):
    """Extensión de SpotifyAPI para búsqueda específica de carátulas de álbumes"""
    
    def search_album(self, artist_name: str, album_name: str) -> Optional[Dict[str, Any]]:
        """Busca un álbum específico por artista y nombre"""
        query = f"album:{quote_plus(album_name)} artist:{quote_plus(artist_name)}"
        url = f"{SPOTIFY_API_BASE}/search?q={query}&type=album&limit=5"
        data = self._make_request(url)
        
        if data and 'albums' in data and 'items' in data['albums'] and data['albums']['items']:
            # Intentar encontrar la mejor coincidencia
            albums = data['albums']['items']
            
            # Normalizar nombres para comparar
            album_name_norm = album_name.lower().strip()
            artist_name_norm = artist_name.lower().strip()
            
            for album in albums:
                album_match = album['name'].lower().strip() == album_name_norm
                
                # Verificar si el artista coincide
                artist_match = False
                if 'artists' in album and album['artists']:
                    for artist in album['artists']:
                        if artist['name'].lower().strip() == artist_name_norm:
                            artist_match = True
                            break
                
                if album_match and artist_match:
                    return album
            
            # Si no encontramos coincidencia exacta, devolver el primero
            return albums[0]
            
        return None
    
    def get_album_cover(self, artist_name: str, album_name: str, album_mbid=None) -> List[Dict[str, str]]:
        """Obtiene las URL de las imágenes de un álbum"""
        album_data = self.search_album(artist_name, album_name)
        images = []
        
        if album_data and 'images' in album_data:
            for img in album_data['images']:
                images.append({
                    'url': img['url'],
                    'type': 'album',
                    'width': img.get('width'),
                    'height': img.get('height'),
                    'source': 'spotify'
                })
        
        return images


class MusicBrainzAlbumAPI(MusicBrainzAPI):
    """Extensión de MusicBrainzAPI para búsqueda específica de carátulas de álbumes"""
    
    def search_album(self, artist_name: str, album_name: str) -> Optional[str]:
        """Busca un álbum en MusicBrainz y devuelve su MBID"""
        query = f'release:"{album_name}" AND artist:"{artist_name}"'
        url = f"{MUSICBRAINZ_API_BASE}/release?query={quote_plus(query)}&limit=5&fmt=json"
        data = self._make_request(url)
        
        if data and 'releases' in data and data['releases']:
            return data['releases'][0]['id']
        return None
    
    def get_album_cover(self, artist_name: str, album_name: str, album_mbid=None) -> List[Dict[str, str]]:
        """Obtiene las URL de las imágenes de un álbum"""
        images = []
        
        # Si nos proporcionan un MBID, lo usamos directamente
        if not album_mbid:
            album_mbid = self.search_album(artist_name, album_name)
        
        if album_mbid:
            url = f"{MUSICBRAINZ_COVER_ART}/release/{album_mbid}"
            
            try:
                response = requests.get(url, headers={'Accept': 'application/json'})
                if response.status_code == 200:
                    data = response.json()
                    if 'images' in data:
                        for img in data['images']:
                            if img.get('front', False):  # Priorizar imágenes frontales
                                images.append({
                                    'url': img.get('image', ''),
                                    'type': 'album',
                                    'source': 'musicbrainz',
                                    'front': True
                                })
                            else:
                                images.append({
                                    'url': img.get('image', ''),
                                    'type': 'album',
                                    'source': 'musicbrainz',
                                    'front': False
                                })
            except requests.RequestException as e:
                logger.error(f"Error al obtener carátula de MusicBrainz: {e}")
        
        return images


class DiscogsAlbumAPI(DiscogsAPI):
    """Extensión de DiscogsAPI para búsqueda específica de carátulas de álbumes"""
    
    def search_album(self, artist_name: str, album_name: str) -> Optional[Dict[str, Any]]:
        """Busca un álbum específico en Discogs"""
        query = f"{album_name} {artist_name}"
        url = f"{DISCOGS_API_BASE}/database/search?q={quote_plus(query)}&type=release&per_page=5"
        data = self._make_request(url)
        
        if data and 'results' in data and data['results']:
            # Filtrar por coincidencia de artista y título
            for result in data['results']:
                if 'title' in result and artist_name.lower() in result['title'].lower() and album_name.lower() in result['title'].lower():
                    return result
            
            # Si no hay coincidencia específica, devolver el primero
            return data['results'][0]
        
        return None
    
    def get_album_cover(self, artist_name: str, album_name: str, album_mbid=None) -> List[Dict[str, str]]:
        """Obtiene las URL de las imágenes de un álbum"""
        album_data = self.search_album(artist_name, album_name)
        images = []
        
        if album_data:
            # Imagen de la búsqueda
            if 'cover_image' in album_data and album_data['cover_image']:
                images.append({
                    'url': album_data['cover_image'],
                    'type': 'album',
                    'source': 'discogs'
                })
            
            # Intentar obtener más imágenes del lanzamiento
            if 'id' in album_data:
                release_id = album_data['id']
                url = f"{DISCOGS_API_BASE}/releases/{release_id}"
                release_data = self._make_request(url)
                
                if release_data and 'images' in release_data:
                    for img in release_data['images']:
                        if img.get('uri'):
                            is_primary = img.get('type', '') == 'primary'
                            images.append({
                                'url': img['uri'],
                                'type': 'album',
                                'source': 'discogs',
                                'front': is_primary,
                                'width': img.get('width'),
                                'height': img.get('height')
                            })
        
        return images


class LastfmAlbumAPI(LastfmAPI):
    """Extensión de LastfmAPI para búsqueda específica de carátulas de álbumes"""
    
    def get_album_info(self, artist_name: str, album_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un álbum en Last.fm"""
        params = {
            'method': 'album.getinfo',
            'artist': artist_name,
            'album': album_name
        }
        
        return self._make_request(params)
    
    def get_album_cover(self, artist_name: str, album_name: str, album_mbid=None) -> List[Dict[str, str]]:
        """Obtiene las URL de las imágenes de un álbum"""
        data = self.get_album_info(artist_name, album_name)
        images = []
        
        if data and 'album' in data and 'image' in data['album']:
            for img in data['album']['image']:
                if img['#text'] and img['#text'] != '':
                    # Comprobar si es una imagen por defecto
                    if '2a96cbd8b46e442fc41c2b86b821562f' in img['#text']:
                        continue  # Omitir imágenes por defecto
                    
                    # Usar CDN alternativo si es de lastfm.freetls.fastly.net
                    url = img['#text']
                    if 'lastfm.freetls.fastly.net' in url:
                        url = url.replace('lastfm.freetls.fastly.net', 'lastfm-img2.akamaized.net')
                    
                    images.append({
                        'url': url,
                        'type': 'album',
                        'source': 'lastfm',
                        'size': img['size']
                    })
        
        return images



def main(config=None):
    """
    Función principal que puede ser invocada directamente por db_creator.py
    """
    if not config:
        logger.error("No se proporcionó configuración")
        return 1
    
    # Verificar dependencias opcionales
    try:
        import cv2
        logger.info("OpenCV disponible para detección avanzada de duplicados")
    except ImportError:
        logger.warning("OpenCV no disponible. Se usará detección básica de duplicados.")
    
    try:
        from PIL import Image
        logger.info("PIL disponible para procesamiento de imágenes")
    except ImportError:
        logger.error("PIL no disponible. Es necesario para procesar imágenes.")
        return 1
    
    # Extraer configuración
    db_path = config.get('db_path')
    project_root = config.get('project_root')
    
    if not db_path:
        logger.error("No se especificó ruta de base de datos (db_path)")
        return 1
    
    # Opciones para artistas
    descargar_img_artistas = config.get('descargar_img_artistas', True)
    guardar_url_artistas = config.get('guardar_url_artistas', True)
    
    # Opciones para álbumes
    descargar_img_albums = config.get('descargar_img_albums', False)
    guardar_url_albums = config.get('guardar_url_albums', False)
    
    # Opción para forzar actualización
    force_update = config.get('force_update', False)
    
    # Manejo de valores booleanos en forma de string
    if isinstance(descargar_img_artistas, str):
        descargar_img_artistas = descargar_img_artistas.lower() == 'true'
    if isinstance(guardar_url_artistas, str):
        guardar_url_artistas = guardar_url_artistas.lower() == 'true'
    if isinstance(descargar_img_albums, str):
        descargar_img_albums = descargar_img_albums.lower() == 'true'
    if isinstance(guardar_url_albums, str):
        guardar_url_albums = guardar_url_albums.lower() == 'true'
    if isinstance(force_update, str):
        force_update = force_update.lower() == 'true'
    
    # Configuración de APIs
    spotify_client_id = config.get('spotify_client_id', '')
    spotify_client_secret = config.get('spotify_client_secret', '')
    discogs_token = config.get('discogs_token', '')
    lastfm_api_key = config.get('lastfm_api_key', '')
    
    # Iniciar el proceso
    gestor = ArtistasImagenes(db_path, project_root, force_update)
    gestor.setup_apis(
        spotify_client_id=spotify_client_id,
        spotify_client_secret=spotify_client_secret,
        discogs_token=discogs_token,
        lastfm_api_key=lastfm_api_key
    )
    
    stats = gestor.run(
        descargar_img_artistas=descargar_img_artistas,
        guardar_url_artistas=guardar_url_artistas,
        descargar_img_albums=descargar_img_albums,
        guardar_url_albums=guardar_url_albums
    )
    
    # Si se solicita archivo de estadísticas
    stats_file = config.get('stats_file')
    if stats_file:
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logger.error(f"Error al guardar estadísticas: {e}")
    
    return 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Descargar imágenes de artistas y álbumes y guardar URLs')
    parser.add_argument('--db_path', required=True, help='Ruta a la base de datos')
    parser.add_argument('--project_root', help='Ruta raíz del proyecto')
    
    # Opciones para artistas (como valores string, no store_true)
    parser.add_argument('--descargar_img_artistas', choices=['true', 'false'], default='true', 
                        help='Descargar imágenes de artistas (true/false)')
    parser.add_argument('--guardar_url_artistas', choices=['true', 'false'], default='true', 
                        help='Guardar URLs de imágenes de artistas en la base de datos (true/false)')
    
    # Opciones para álbumes
    parser.add_argument('--descargar_img_albums', choices=['true', 'false'], default='false', 
                        help='Descargar carátulas de álbumes (true/false)')
    parser.add_argument('--guardar_url_albums', choices=['true', 'false'], default='false', 
                        help='Guardar URLs de carátulas de álbumes en la base de datos (true/false)')
    
    # Opción para forzar actualización
    parser.add_argument('--force_update', choices=['true', 'false'], default='false',
                       help='Forzar actualización incluso si ya existen datos (true/false)')
    
    # Configuración de APIs
    parser.add_argument('--spotify_client_id', help='ID de cliente de Spotify')
    parser.add_argument('--spotify_client_secret', help='Secret de cliente de Spotify')
    parser.add_argument('--discogs_token', help='Token de acceso para Discogs API')
    parser.add_argument('--lastfm_api_key', help='API key para Last.fm')
    
    # Archivo de estadísticas
    parser.add_argument('--stats_file', help='Ruta para guardar archivo de estadísticas JSON')
    
    args = parser.parse_args()
    
    # Crear configuración
    config = {
        'db_path': args.db_path,
        'project_root': args.project_root,
        'descargar_img_artistas': args.descargar_img_artistas,
        'guardar_url_artistas': args.guardar_url_artistas,
        'descargar_img_albums': args.descargar_img_albums,
        'guardar_url_albums': args.guardar_url_albums,
        'force_update': args.force_update,
        'spotify_client_id': args.spotify_client_id,
        'spotify_client_secret': args.spotify_client_secret,
        'discogs_token': args.discogs_token,
        'lastfm_api_key': args.lastfm_api_key,
        'stats_file': args.stats_file
    }
    
    sys.exit(main(config))