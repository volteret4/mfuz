
#!/usr/bin/env python
#
# Script Name: portadas_y_artistas.py
# Description: Descarga desde musicbrainz portadas y fotos de los artistas leyendo un config.json
# Author: volteret4
# Repository: https://github.com/volteret4/
# Notes:
#   Dependencies:  - python3, 
#

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Music Artwork Downloader

Este script descarga portadas de álbumes y fotos de artistas desde MusicBrainz o Spotify
utilizando los MBIDs almacenados en la base de datos.
"""

import os
import sys
import sqlite3
import argparse
import logging
import json
import time
import requests
from pathlib import Path
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Optional, Union, Any
import hashlib

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('artwork_downloader')

# Constantes para las APIs
MUSICBRAINZ_API_BASE = "https://musicbrainz.org/ws/2"
MUSICBRAINZ_COVER_ART = "https://coverartarchive.org"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
USER_AGENT = "MusicArtworkDownloader/1.0 (https://github.com/yourusername/music-art-downloader)"

# Tiempo de espera entre solicitudes para respetar las limitaciones de las APIs
MB_RATE_LIMIT = 1.0  # 1 segundo entre solicitudes para MusicBrainz
SPOTIFY_RATE_LIMIT = 0.2  # 0.2 segundos entre solicitudes para Spotify



def get_file_hash(file_path):
    """Calcula el hash MD5 de un archivo"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Clase para manejar la configuración
class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), 'config.json')
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde un archivo JSON"""
        default_config = {
            "database_path": os.path.expanduser("~/music.db"),
            "artist_images_path": os.path.expanduser("~/Music/Artists"),
            "album_images_default_path": None,  # Si es None, se usará la ruta del álbum
            "spotify_client_id": "",
            "spotify_client_secret": "",
            "max_artist_images": 3,
            "preferred_source": "musicbrainz",  # o "spotify"
            "image_size": "large",  # "small", "medium", "large"
            "file_format": "jpg"
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # Actualizar la configuración predeterminada con los valores del usuario
                    default_config.update(user_config)
            except Exception as e:
                logger.error(f"Error al cargar la configuración: {e}")
        else:
            # Guardar la configuración predeterminada si no existe
            self._save_config(default_config)
            
        return default_config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Guarda la configuración en un archivo JSON"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.error(f"Error al guardar la configuración: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor de la configuración"""
        return self.config.get(key, default)
    
    def update(self, key: str, value: Any) -> None:
        """Actualiza un valor en la configuración"""
        self.config[key] = value
        self._save_config(self.config)




# Clase para manejar la base de datos
class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        


    def connect(self) -> None:
        """Conecta a la base de datos"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"Conectado a la base de datos: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Error al conectar a la base de datos: {e}")
            sys.exit(1)
    
    def disconnect(self) -> None:
        """Desconecta de la base de datos"""
        if self.conn:
            self.conn.close()
            logger.info("Desconectado de la base de datos")
    
    def get_albums_without_artwork(self) -> List[Dict[str, Any]]:
        """Obtiene los álbumes que no tienen portada"""
        try:
            query = """
            SELECT a.id, a.name, a.mbid, a.artist_id, a.folder_path, a.album_art_path,
                   a.spotify_url, a.spotify_id, a.musicbrainz_url,
                   ar.name as artist_name, ar.mbid as artist_mbid
            FROM albums a
            LEFT JOIN artists ar ON a.artist_id = ar.id
            WHERE a.album_art_path IS NULL OR a.album_art_path = ''
               OR NOT EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='albums' AND sql LIKE '%album_art_path%')
               OR NOT EXISTS (SELECT 1 FROM pragma_table_info('albums') WHERE name='album_art_path')
            """
            self.cursor.execute(query)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error al obtener álbumes sin portada: {e}")
            return []
    
    def get_albums_with_mbid(self) -> List[Dict[str, Any]]:
        """Obtiene los álbumes que tienen MBID"""
        try:
            query = """
            SELECT a.id, a.name, a.mbid, a.artist_id, a.folder_path, a.album_art_path,
                   a.spotify_url, a.spotify_id, a.musicbrainz_url,
                   ar.name as artist_name, ar.mbid as artist_mbid
            FROM albums a
            LEFT JOIN artists ar ON a.artist_id = ar.id
            WHERE a.mbid IS NOT NULL AND a.mbid != ''
            """
            self.cursor.execute(query)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error al obtener álbumes con MBID: {e}")
            return []
    
    def get_all_albums(self) -> List[Dict[str, Any]]:
        """Obtiene todos los álbumes"""
        try:
            query = """
            SELECT a.id, a.name, a.mbid, a.artist_id, a.folder_path, a.album_art_path,
                   a.spotify_url, a.spotify_id, a.musicbrainz_url,
                   ar.name as artist_name, ar.mbid as artist_mbid
            FROM albums a
            LEFT JOIN artists ar ON a.artist_id = ar.id
            """
            self.cursor.execute(query)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error al obtener todos los álbumes: {e}")
            return []
    
    def get_artists_without_images(self) -> List[Dict[str, Any]]:
        """Obtiene los artistas que no tienen imágenes"""
        try:
            # En este caso, asumimos que no hay un campo específico para imágenes de artistas en la BD,
            # por lo que obtenemos todos los artistas y luego verificaremos si existen imágenes localmente
            query = """
            SELECT id, name, mbid, spotify_url, musicbrainz_url
            FROM artists
            WHERE mbid IS NOT NULL AND mbid != ''
            """
            self.cursor.execute(query)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error al obtener artistas sin imágenes: {e}")
            return []
    
    def update_album_artwork_path(self, album_id: int, path: str) -> bool:
        """Actualiza la ruta de la portada de un álbum en la base de datos"""
        try:
            query = "UPDATE albums SET album_art_path = ? WHERE id = ?"
            self.cursor.execute(query, (path, album_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al actualizar la ruta de la portada: {e}")
            return False

# Clase para manejar la API de MusicBrainz
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
    
    def get_album_artwork(self, mbid: str) -> List[Dict[str, str]]:
        """Obtiene las URL de las portadas de un álbum por su MBID"""
        url = f"{MUSICBRAINZ_COVER_ART}/release-group/{mbid}"
        
        try:
            response = requests.get(f"{url}", headers={'User-Agent': USER_AGENT})
            if response.status_code == 404:
                # Intentamos con el endpoint de release en lugar de release-group
                response = requests.get(f"{MUSICBRAINZ_COVER_ART}/release/{mbid}", 
                                        headers={'User-Agent': USER_AGENT})
            
            if response.status_code == 200:
                data = response.json()
                if 'images' in data:
                    return [{'url': img['image'], 'type': img.get('types', ['front'])[0]} 
                            for img in data['images']]
            return []
        except requests.RequestException as e:
            logger.error(f"Error al obtener portada de MusicBrainz: {e}")
            return []
    
    def get_artist_images(self, mbid: str) -> List[Dict[str, str]]:
        """Obtiene las URL de las imágenes de un artista por su MBID"""
        # MusicBrainz no proporciona imágenes de artistas directamente,
        # pero podemos usar el servicio de MusicBrainz para obtener el ID de Wikidata y luego
        # consultar las imágenes allí, o utilizar el ID para consultar en otras APIs
        
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
        
        # Si no encontramos imágenes, podríamos intentar con Wikidata
        if not image_urls and 'relations' in data:
            wikidata_url = None
            for relation in data['relations']:
                if relation['type'] == 'wikidata' and 'url' in relation:
                    wikidata_url = relation['url']['resource']
                    break
            
            if wikidata_url:
                # Extrae el ID de Wikidata
                wikidata_id = wikidata_url.split('/')[-1]
                # Podríamos implementar una consulta a la API de Wikidata aquí
        
        return image_urls

# Clase para manejar la API de Spotify
class SpotifyAPI:
    def __init__(self, spotify_client_id: str, spotify_client_secret: str):
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
    
    def get_album_by_id(self, spotify_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un álbum por su ID de Spotify"""
        url = f"{SPOTIFY_API_BASE}/albums/{spotify_id}"
        return self._make_request(url)
    
    def search_album(self, name: str, artist: str) -> Optional[Dict[str, Any]]:
        """Busca un álbum por nombre y artista"""
        query = f"album:{quote_plus(name)} artist:{quote_plus(artist)}"
        url = f"{SPOTIFY_API_BASE}/search?q={query}&type=album&limit=1"
        data = self._make_request(url)
        
        if data and 'albums' in data and 'items' in data['albums'] and data['albums']['items']:
            return data['albums']['items'][0]
        return None
    
    def get_album_artwork(self, album_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extrae las URL de las portadas de un álbum"""
        if 'images' not in album_data:
            return []
        
        return [{'url': img['url'], 'type': 'front', 'width': img['width'], 'height': img['height']} 
                for img in album_data['images']]
    
    def get_artist_by_id(self, spotify_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un artista por su ID de Spotify"""
        url = f"{SPOTIFY_API_BASE}/artists/{spotify_id}"
        return self._make_request(url)
    
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
    
    def get_related_artists(self, spotify_id: str) -> List[Dict[str, Any]]:
        """Obtiene artistas relacionados para obtener más imágenes"""
        url = f"{SPOTIFY_API_BASE}/artists/{spotify_id}/related-artists"
        data = self._make_request(url)
        
        if data and 'artists' in data:
            return data['artists']
        return []

# Clase principal del downloader
class ArtworkDownloader:
    def __init__(self, config_path: Optional[str] = None):
        self.config = Config(config_path)
        self.db = Database(self.config.get('database_path'))
        
        spotify_config = self.config.get('spotify', {})
        self.spotify = SpotifyAPI(
            spotify_config.get('client_id', ''),
            spotify_config.get('client_secret', '')
        )
        
        self.musicbrainz = MusicBrainzAPI()
        self.db.connect()
    
    def download_file(self, url: str, destination: str) -> bool:
        """Descarga un archivo desde una URL a una ruta de destino"""
        try:
            # Asegurarse de que el directorio existe
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            # Descargar el archivo
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Archivo descargado: {destination}")
            return True
        except Exception as e:
            logger.error(f"Error al descargar {url}: {e}")
            return False
    
    def get_album_artwork_path(self, album: Dict[str, Any]) -> str:
        """Determina la ruta donde se guardará la portada del álbum"""
        # Si hay una ruta específica configurada para las portadas de álbumes
        album_images_path = self.config.get('album_images_default_path')
        
        if album_images_path:
            # Usar la ruta configurada
            directory = os.path.join(album_images_path, f"{album['artist_name']} - {album['name']}")
            Path(directory).mkdir(parents=True, exist_ok=True)
            return os.path.join(directory, f"cover.{self.config.get('file_format', 'jpg')}")
        else:
            # Usar la ruta del álbum si está disponible
            if album['folder_path'] and os.path.exists(album['folder_path']):
                return os.path.join(album['folder_path'], f"cover.{self.config.get('file_format', 'jpg')}")
            else:
                # Fallback a la ruta de música predeterminada
                directory = os.path.expanduser(f"~/Music/Albums/{album['artist_name']} - {album['name']}")
                Path(directory).mkdir(parents=True, exist_ok=True)
                return os.path.join(directory, f"cover.{self.config.get('file_format', 'jpg')}")
    
    def get_artist_image_path(self, artist: Dict[str, Any], index: int = 0) -> str:
        """Determina la ruta donde se guardarán las imágenes del artista"""
        artist_images_path = self.config.get('artist_images_path')
        directory = os.path.join(artist_images_path, artist['name'])
        Path(directory).mkdir(parents=True, exist_ok=True)
        return os.path.join(directory, f"image_{index + 1}.{self.config.get('file_format', 'jpg')}")
    
    def process_album(self, album: Dict[str, Any]) -> bool:
        """Procesa un álbum para descargar su portada"""
        # Verificar si ya existe la portada
        artwork_path = self.get_album_artwork_path(album)
        if os.path.exists(artwork_path):
            logger.info(f"La portada ya existe para '{album['name']}': {artwork_path}")
            # Actualizar la base de datos si la ruta es diferente
            if album['album_art_path'] != artwork_path:
                self.db.update_album_artwork_path(album['id'], artwork_path)
                logger.info(f"Actualizada ruta en la base de datos para '{album['name']}'")
            return True
        
        logger.info(f"Buscando portada para '{album['name']}' de '{album['artist_name']}'")
        
        artwork_urls = []
        preferred_source = self.config.get('preferred_source', 'musicbrainz')
        
        # Estrategias de búsqueda en orden de preferencia
        search_strategies = []
        
        # Configurar el orden de las estrategias según la fuente preferida
        if preferred_source == 'musicbrainz':
            search_strategies = [
                self._get_artwork_from_musicbrainz_mbid,
                self._get_artwork_from_spotify_id,
                self._get_artwork_from_spotify_search,
                self._get_artwork_fallback
            ]
        else:  # spotify
            search_strategies = [
                self._get_artwork_from_spotify_id,
                self._get_artwork_from_spotify_search,
                self._get_artwork_from_musicbrainz_mbid,
                self._get_artwork_fallback
            ]
        
        # Intentar cada estrategia hasta encontrar imágenes
        for strategy in search_strategies:
            artwork_urls = strategy(album)
            if artwork_urls:
                break
        
        # Descargar la mejor imagen encontrada
        if artwork_urls:
            # Ordenar por tipo, priorizando 'front'
            artwork_urls.sort(key=lambda x: 0 if x.get('type') == 'front' else 1)
            
            for artwork in artwork_urls:
                logger.info(f"Descargando portada de tipo '{artwork.get('type', 'unknown')}' para '{album['name']}'")
                if self.download_file(artwork['url'], artwork_path):
                    # Actualizar la base de datos con la nueva ruta
                    self.db.update_album_artwork_path(album['id'], artwork_path)
                    logger.info(f"Portada descargada correctamente: {artwork_path}")
                    return True
                else:
                    logger.warning(f"Error al descargar la portada de {artwork['url']}")
        
        logger.warning(f"No se pudo encontrar portada para '{album['name']}'")
        return False
    
    def _get_artwork_from_musicbrainz_mbid(self, album: Dict[str, Any]) -> List[Dict[str, str]]:
        """Obtiene la portada de un álbum usando su MBID en MusicBrainz"""
        if album['mbid']:
            logger.debug(f"Buscando portada en MusicBrainz para MBID: {album['mbid']}")
            return self.musicbrainz.get_album_artwork(album['mbid'])
        return []
    
    def _get_artwork_from_spotify_id(self, album: Dict[str, Any]) -> List[Dict[str, str]]:
        """Obtiene la portada de un álbum usando su ID de Spotify"""
        if album['spotify_id']:
            logger.debug(f"Buscando portada en Spotify para ID: {album['spotify_id']}")
            album_data = self.spotify.get_album_by_id(album['spotify_id'])
            if album_data:
                return self.spotify.get_album_artwork(album_data)
        return []
    
    def _get_artwork_from_spotify_search(self, album: Dict[str, Any]) -> List[Dict[str, str]]:
        """Busca la portada de un álbum en Spotify por nombre y artista"""
        logger.debug(f"Buscando portada en Spotify para: {album['name']} - {album['artist_name']}")
        album_data = self.spotify.search_album(album['name'], album['artist_name'])
        if album_data:
            return self.spotify.get_album_artwork(album_data)
        return []
    
    def _get_artwork_fallback(self, album: Dict[str, Any]) -> List[Dict[str, str]]:
        """Estrategia de último recurso para encontrar una portada"""
        logger.debug(f"Intentando estrategias alternativas para: {album['name']}")
        
        # Intentar con variaciones del nombre del álbum (por ejemplo, sin caracteres especiales)
        import re
        clean_album_name = re.sub(r'[^\w\s]', '', album['name'])
        clean_artist_name = re.sub(r'[^\w\s]', '', album['artist_name'])
        
        if clean_album_name != album['name'] or clean_artist_name != album['artist_name']:
            album_data = self.spotify.search_album(clean_album_name, clean_artist_name)
            if album_data:
                return self.spotify.get_album_artwork(album_data)
        
        # Si tenemos el artista_id, buscar álbumes de ese artista
        if 'artist_id' in album and album['artist_id']:
            # Aquí podríamos implementar una búsqueda más exhaustiva
            pass
        
        return []
    

    def get_file_hash(file_path):
        """Calcula el hash MD5 de un archivo"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def process_artist(self, artist: Dict[str, Any]) -> bool:
        """Procesa un artista para descargar sus imágenes, evitando duplicados"""
        # Verificar si ya existen las imágenes
        base_path = os.path.join(self.config.get('artist_images_path'), artist['name'])
        max_images = self.config.get('max_artist_images', 3)
        
        # Crear el directorio si no existe
        os.makedirs(base_path, exist_ok=True)
        
        # Comprobar imágenes existentes
        if os.path.exists(base_path):
            existing_images = [f for f in os.listdir(base_path) 
                            if f.startswith('image_') and 
                            f.endswith(f".{self.config.get('file_format', 'jpg')}")]
            
            if len(existing_images) >= max_images:
                # Verificar si hay duplicados entre las imágenes existentes
                image_hashes = []
                duplicate_found = False
                
                for img_file in existing_images:
                    img_path = os.path.join(base_path, img_file)
                    img_hash = get_file_hash(img_path)
                    
                    if img_hash in image_hashes:
                        logger.warning(f"Se detectó imagen duplicada para '{artist['name']}': {img_file}")
                        os.remove(img_path)
                        duplicate_found = True
                    else:
                        image_hashes.append(img_hash)
                
                if not duplicate_found and len(existing_images) >= max_images:
                    logger.info(f"Ya existen {len(existing_images)} imágenes únicas para '{artist['name']}'")
                    return True
                
                # Actualizar la lista de imágenes existentes después de eliminar duplicados
                existing_images = [f for f in os.listdir(base_path) 
                                if f.startswith('image_') and 
                                f.endswith(f".{self.config.get('file_format', 'jpg')}")]
        
        logger.info(f"Buscando imágenes para el artista '{artist['name']}'")
        
        # Colección para almacenar todas las URLs de imágenes encontradas
        all_image_urls = []
        used_urls = set()  # Para evitar URLs duplicadas
        
        # 1. Buscar imágenes en MusicBrainz si tenemos MBID
        if artist['mbid']:
            logger.debug(f"Buscando imágenes en MusicBrainz para MBID: {artist['mbid']}")
            mb_images = self.musicbrainz.get_artist_images(artist['mbid'])
            
            for img in mb_images:
                if img['url'] not in used_urls:
                    all_image_urls.append(img)
                    used_urls.add(img['url'])
            
            logger.debug(f"Encontradas {len(mb_images)} imágenes en MusicBrainz, {len(all_image_urls)} únicas")
        
        # 2. Buscar imágenes en Spotify por ID o por búsqueda
        spotify_artist = None
        
        # 2.1 Intentar con la URL de Spotify si está disponible
        if artist.get('spotify_url'):
            try:
                spotify_id = artist['spotify_url'].split('/')[-1]
                logger.debug(f"Buscando imágenes en Spotify para ID: {spotify_id}")
                spotify_artist = self.spotify.get_artist_by_id(spotify_id)
            except Exception as e:
                logger.debug(f"Error al obtener artista de Spotify usando URL: {str(e)}")
        
        # 2.2 Si no tenemos URL o falló, buscar por nombre
        if not spotify_artist:
            logger.debug(f"Buscando imágenes en Spotify para artista: {artist['name']}")
            spotify_artist = self.spotify.search_artist(artist['name'])
        
        # 2.3 Extraer imágenes de Spotify si encontramos el artista
        if spotify_artist:
            spotify_images = self.spotify.get_artist_images(spotify_artist)
            
            for img in spotify_images:
                if img['url'] not in used_urls:
                    all_image_urls.append(img)
                    used_urls.add(img['url'])
            
            logger.debug(f"Encontradas {len(spotify_images)} imágenes en Spotify, {len(all_image_urls)} únicas")
            
            # 3. Si necesitamos más imágenes, intentar con artistas relacionados
            if len(all_image_urls) < max_images * 2 and 'id' in spotify_artist:  # Obtener el doble para tener más opciones
                logger.debug(f"Buscando imágenes de artistas relacionados para: {artist['name']}")
                related_artists = self.spotify.get_related_artists(spotify_artist['id'])
                
                for related in related_artists[:10]:  # Ampliar a 10 artistas relacionados para tener más variedad
                    related_images = self.spotify.get_artist_images(related)
                    
                    # Añadir información sobre el artista relacionado
                    for img in related_images[:2]:  # Tomar hasta 2 imágenes de cada artista relacionado
                        if img['url'] not in used_urls:
                            img['related_artist_name'] = related.get('name', 'Unknown')
                            all_image_urls.append(img)
                            used_urls.add(img['url'])
                    
                    if len(all_image_urls) >= max_images * 3:  # Obtener más extras para seleccionar las mejores
                        break
        
        # 4. Último recurso: buscar imágenes alternativas
        if len(all_image_urls) < max_images:
            logger.warning(f"No se encontraron suficientes imágenes únicas para '{artist['name']}'")
            # Aquí podrías implementar búsquedas adicionales
        
        # Ordenar por calidad/relevancia
        def image_sort_key(img):
            # Prioridad: imágenes oficiales del artista > imágenes de artistas relacionados
            priority = 1 if 'related_artist_name' in img else 0
            
            # Si hay información de dimensiones, priorizar imágenes grandes pero no demasiado
            if 'width' in img and 'height' in img:
                size = img['width'] * img['height']
                # Normalizar a un valor entre 0 y 1 (asumiendo tamaños entre 100x100 y 2000x2000)
                size_score = min(1.0, max(0.0, (size - 10000) / 4000000))
                return (priority, -size_score)  # Ordenar primero por prioridad, luego por tamaño (grande mejor)
            
            return (priority, 0)
        
        all_image_urls.sort(key=image_sort_key)
        
        # Descargar las imágenes necesarias
        success = False
        downloaded_count = 0
        image_hashes = []
        
        # Primero, obtener hashes de las imágenes existentes
        for img_file in [f for f in os.listdir(base_path) 
                        if f.startswith('image_') and 
                        f.endswith(f".{self.config.get('file_format', 'jpg')}")]:
            img_path = os.path.join(base_path, img_file)
            image_hashes.append(get_file_hash(img_path))
        
        # Obtener el número inicial de imágenes
        initial_images_count = len(image_hashes)
        
        # Intentar descargar imágenes hasta tener el número requerido de imágenes únicas
        for image in all_image_urls:
            # Si ya tenemos suficientes imágenes únicas, salir
            if len(image_hashes) >= max_images:
                break
                
            # Calcular el siguiente índice para nombramiento
            next_index = len([f for f in os.listdir(base_path) 
                            if f.startswith('image_') and 
                            f.endswith(f".{self.config.get('file_format', 'jpg')}")])
            
            # Información adicional para el log
            source_info = ""
            if 'related_artist_name' in image:
                source_info = f" (del artista relacionado: {image['related_artist_name']})"
            
            image_path = self.get_artist_image_path(artist, next_index)
            
            logger.info(f"Descargando imagen {next_index + 1} para '{artist['name']}'{source_info}")
            
            if self.download_file(image['url'], image_path):
                # Verificar si la imagen es un duplicado por hash
                img_hash = get_file_hash(image_path)
                
                if img_hash in image_hashes:
                    logger.info(f"Imagen duplicada detectada por hash, eliminando: {image_path}")
                    os.remove(image_path)
                else:
                    # No es duplicado, guardarla
                    image_hashes.append(img_hash)
                    downloaded_count += 1
                    success = True
                    logger.info(f"Imagen única descargada: {image_path}")
            else:
                logger.warning(f"Error al descargar imagen de {image['url']}")
        
        # Renombrar las imágenes para que tengan una secuencia continua (1, 2, 3...)
        # Solo si hemos descargado nuevas imágenes o eliminado duplicados
        if downloaded_count > 0 or len(image_hashes) != initial_images_count:
            all_images = sorted([f for f in os.listdir(base_path) 
                            if f.startswith('image_') and 
                            f.endswith(f".{self.config.get('file_format', 'jpg')}")],
                            key=lambda x: int(x.split('_')[1].split('.')[0]))
            
            # Renombrar temporalmente para evitar conflictos
            for i, img_file in enumerate(all_images):
                old_path = os.path.join(base_path, img_file)
                temp_path = os.path.join(base_path, f"temp_{i+1}.{self.config.get('file_format', 'jpg')}")
                os.rename(old_path, temp_path)
            
            # Renombrar a los nombres finales
            for i in range(len(all_images)):
                temp_path = os.path.join(base_path, f"temp_{i+1}.{self.config.get('file_format', 'jpg')}")
                new_path = os.path.join(base_path, f"image_{i+1}.{self.config.get('file_format', 'jpg')}")
                os.rename(temp_path, new_path)
        
        if downloaded_count > 0:
            logger.info(f"Se han descargado {downloaded_count} imágenes únicas para '{artist['name']}'")
        elif not all_image_urls:
            logger.warning(f"No se encontraron imágenes para '{artist['name']}'")
        else:
            logger.warning(f"No se pudieron descargar imágenes únicas para '{artist['name']}'")
        
        return success
    
    def download_album_artworks(self) -> int:
        """Descarga las portadas de álbumes que no tienen una"""
        albums = self.db.get_all_albums()
        logger.info(f"Procesando {len(albums)} álbumes")
        
        count = 0
        for album in albums:
            if self.process_album(album):
                count += 1
        
        logger.info(f"Se descargaron {count} portadas de álbumes")
        return count
    
    def download_artist_images(self) -> int:
        """Descarga imágenes de artistas"""
        artists = self.db.get_artists_without_images()
        logger.info(f"Procesando {len(artists)} artistas")
        
        count = 0
        for artist in artists:
            if self.process_artist(artist):
                count += 1
        
        logger.info(f"Se descargaron imágenes para {count} artistas")
        return count
    
    def run(self, download_albums: bool = False, download_artists: bool = False) -> None:
        """Ejecuta el proceso de descarga según los parámetros"""
        if not download_albums and not download_artists:
            logger.error("Debe especificar al menos una opción: álbumes o artistas")
            return
        
        start_time = time.time()
        album_count = 0
        artist_count = 0
        
        try:
            logger.info("Iniciando proceso de descarga de imágenes...")
            
            if download_albums:
                logger.info("=== Descargando portadas de álbumes ===")
                album_count = self.download_album_artworks()
            
            if download_artists:
                logger.info("=== Descargando fotos de artistas ===")
                artist_count = self.download_artist_images()
            
            # Mostrar resumen
            elapsed_time = time.time() - start_time
            logger.info("\n=== Resumen de operaciones ===")
            logger.info(f"Tiempo total: {elapsed_time:.2f} segundos")
            
            if download_albums:
                logger.info(f"Portadas de álbumes procesadas: {album_count}")
            
            if download_artists:
                logger.info(f"Artistas con imágenes procesadas: {artist_count}")
            
            logger.info("Proceso completado con éxito.")
            
        except KeyboardInterrupt:
            logger.info("\nOperación interrumpida por el usuario.")
        except Exception as e:
            logger.error(f"Error durante la ejecución: {e}")
        finally:
            self.db.disconnect()

def main(config=None):
    """
    Función principal que puede ser invocada directamente por db_creator.py
    
    Args:
        config: Diccionario de configuración pasado por db_creator.py
    """
    # Si config ya viene proporcionado por db_creator.py, usarlo
    if config is not None:
        logger.info("Usando configuración proporcionada por db_creator.py")
    else:
        # Ejecución independiente, usar argparse
        parser = argparse.ArgumentParser(description='Descarga portadas de álbumes y fotos de artistas')
        parser.add_argument('--config', help='Ruta al archivo de configuración')
        parser.add_argument('--albums', action='store_true', help='Descargar portadas de álbumes')
        parser.add_argument('--artists', action='store_true', help='Descargar fotos de artistas')
        parser.add_argument('--artist-path', help='Ruta donde guardar las fotos de artistas')
        parser.add_argument('--album-path', help='Ruta donde guardar las portadas de álbumes (si no se especifica, se usará la ruta del álbum)')
        parser.add_argument('--max-artist-images', type=int, help='Número máximo de imágenes a descargar por artista')
        parser.add_argument('--source', choices=['musicbrainz', 'spotify'], help='Fuente de las imágenes')
        parser.add_argument('--verbose', '-v', action='store_true', help='Mostrar mensajes detallados')
        
        args = parser.parse_args()
        
        # Si se especifica un archivo de configuración, cargarlo
        if args.config:
            try:
                with open(args.config, 'r') as f:
                    config_data = json.load(f)
                
                # Crear el diccionario de configuración
                config = {}
                # Incluir ajustes comunes
                config.update(config_data.get("common", {}))
                # Incluir ajustes específicos del script
                config.update(config_data.get("portadas_artistas", {}))
                
                # Sobreescribir con argumentos de línea de comandos si se proporcionaron
                if args.albums:
                    config['download_albums'] = args.albums
                if args.artists:
                    config['download_artists'] = args.artists
                if args.artist_path:
                    config['artist_path'] = args.artist_path
                if args.album_path:
                    config['album_path'] = args.album_path
                if args.max_artist_images:
                    config['max_artist_images'] = args.max_artist_images
                if args.source:
                    config['source'] = args.source
                if args.verbose:
                    config['verbose'] = args.verbose
            except Exception as e:
                logger.error(f"Error al cargar el archivo de configuración: {e}")
                return 1
        else:
            # Si no hay archivo de configuración, usar solo los argumentos
            config = {
                'download_albums': args.albums,
                'download_artists': args.artists,
                'artist_path': args.artist_path,
                'album_path': args.album_path,
                'max_artist_images': args.max_artist_images,
                'source': args.source,
                'verbose': args.verbose
            }
    
    # Configurar nivel de logging
    if config.get('verbose', False):
        logger.setLevel(logging.DEBUG)
    
    # Inicializar el downloader
    try:
        # Extraer los valores necesarios para la inicialización
        config_path = config.get('config_path')
        downloader = ArtworkDownloader(config_path)
        
        # Actualizar la configuración del downloader
        if 'db_path' in config:
            downloader.config.update('database_path', config['db_path'])
        
        if config.get('artist_path'):
            downloader.config.update('artist_images_path', os.path.abspath(config['artist_path']))
        
        if config.get('album_path'):
            downloader.config.update('album_images_default_path', os.path.abspath(config['album_path']))
        
        if config.get('max_artist_images'):
            downloader.config.update('max_artist_images', config['max_artist_images'])
        
        if config.get('source'):
            downloader.config.update('preferred_source', config['source'])
        
        # Configurar Spotify si hay credenciales
        if 'spotify_client_id' in config and 'spotify_client_secret' in config:
            spotify_config = {
                'client_id': config['spotify_client_id'],
                'client_secret': config['spotify_client_secret']
            }
            downloader.config.update('spotify', spotify_config)
        
        # Determinar qué descargar
        download_albums = config.get('download_albums', False)
        download_artists = config.get('download_artists', True)  # Por defecto, descargar artistas
        
        # Ejecutar el downloader
        downloader.run(download_albums=download_albums, download_artists=download_artists)
        
        return 0
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())