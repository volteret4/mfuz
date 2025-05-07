"""
Script para obtener enlaces de YouTube para canciones a partir de:
1. Álbumes que ya tienen URLs de Discogs
2. Buscar directamente en Last.fm para canciones individuales

Este script se enfoca principalmente en encontrar videos de YouTube para canciones
y actualizar la tabla song_links en la base de datos.
"""

import os
import sys
import time
import sqlite3
import requests
import logging
import json
import re
from base_module import PROJECT_ROOT
from urllib.parse import quote_plus

# Importación condicional de BeautifulSoup para evitar errores si no está instalado
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

class DiscogsLinksModule:
    """
    Módulo para obtener enlaces de Discogs (incluidos videos) para artistas, álbumes y canciones
    y guardarlos en la base de datos.
    """
    
    def __init__(self, config=None):
        # Inicialización básica
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Configuración
        self.db_path = self.config.get('db_path')
        self.discogs_token = self.config.get('discogs_token')
        self.lastfm_api_key = self.config.get('lastfm_api_key')
        self.rate_limit = float(self.config.get('rate_limit', 1.0))
        self.user_agent = self.config.get('user_agent', 'MusicDB/1.0')
        self.missing_only = self.config.get('missing_only', True)
        self.cache_file = self.config.get('cache_file', os.path.join(PROJECT_ROOT, '.content/cache/discogs_links_cache.json'))
        self.force_update = self.config.get('force_update', False)
        self.batch_size = int(self.config.get('batch_size', 100))
        self.max_retries = int(self.config.get('max_retries', 3))
        
        # Opciones de fuentes
        self.use_discogs = self.config.get('use_discogs', True)
        self.use_lastfm = self.config.get('use_lastfm', True)
        
        # Tipos de entidades para procesar
        self.entity_types = self.config.get('entity_types', ['songs', 'albums', 'artists'])
        
        # Verificar dependencias
        if self.use_lastfm and not HAS_BS4:
            self.logger.warning("BeautifulSoup no está instalado. La funcionalidad de Last.fm será limitada.")
            
        # Verificar configuración crucial
        if not self.db_path or not os.path.exists(self.db_path):
            self.logger.error(f"No se encontró la base de datos en {self.db_path}")
            
        # Inicializar caché
        self.cache = self.load_cache()
        
    def setup_logging(self):
        """Configurar el logging"""
        try:
            log_file = self.config.get('log_file', os.path.join(PROJECT_ROOT, '.content/logs/discogs_links.log'))
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # Configurar logger
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
            self.logger.info("=== Iniciando DiscogsLinksModule ===")
            self.logger.info(f"Ruta de la base de datos: {self.db_path}")
            for key, value in self.config.items():
                if key not in ['lastfm_api_key', 'discogs_token']:  # No logear claves API
                    self.logger.debug(f"Config: {key} = {value}")
        except Exception as e:
            print(f"Error al configurar logging: {e}")  # Fallback si no podemos configurar el logger
            # Intentar configurar un logger básico
            logging.basicConfig(level=logging.INFO)
    
    def load_cache(self):
        """Cargar caché de búsquedas anteriores"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error al cargar el archivo de caché: {e}")
                return {}
        return {}
    
    def save_cache(self):
        """Guardar caché de búsquedas"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error al guardar el archivo de caché: {e}")
    
    def api_request(self, url, headers=None, retries=0, service="API"):
        """Realizar una petición a cualquier API con manejo de rate limit y errores"""
        if headers is None:
            headers = {'User-Agent': self.user_agent}
        
        try:
            time.sleep(self.rate_limit)  # Respetar rate limit
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                if 'application/json' in response.headers.get('Content-Type', ''):
                    return response.json()
                return response.text
            elif response.status_code == 429 and retries < self.max_retries:
                # Too Many Requests - esperar y reintentar
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"Rate limit alcanzado en {service}. Esperando {retry_after} segundos...")
                time.sleep(retry_after)
                return self.api_request(url, headers, retries + 1, service)
            else:
                self.logger.error(f"Error en petición a {service}: {response.status_code} - {response.text[:200]}...")
                return None
        except Exception as e:
            self.logger.error(f"Error al realizar petición a {service}: {e}")
            if retries < self.max_retries:
                time.sleep(5 * (retries + 1))  # Backoff exponencial
                return self.api_request(url, headers, retries + 1, service)
            return None
    
    def discogs_request(self, url, retries=0):
        """Realizar una petición a la API de Discogs"""
        headers = {
            'User-Agent': self.user_agent,
            'Authorization': f'Discogs token={self.discogs_token}'
        }
        return self.api_request(url, headers, retries, "Discogs")
    
    def get_youtube_from_lastfm_page(self, lastfm_url):
        """Extraer ID de YouTube de una página de Last.fm"""
        # Verificar si BeautifulSoup está disponible
        if not HAS_BS4:
            self.logger.warning("BeautifulSoup no está instalado. No se puede extraer YouTube ID de Last.fm")
            return None
            
        try:
            response = self.api_request(lastfm_url, service="Last.fm page")
            if not response:
                return None
                
            soup = BeautifulSoup(response, 'html.parser')
            
            # Buscar elementos con atributo data-youtube-id o data-youtube-url
            youtube_elements = soup.select('[data-youtube-id], [data-youtube-url]')
            
            for element in youtube_elements:
                # Preferir data-youtube-url si está disponible
                if element.has_attr('data-youtube-url'):
                    return element['data-youtube-url']
                elif element.has_attr('data-youtube-id'):
                    youtube_id = element['data-youtube-id']
                    return f"https://www.youtube.com/watch?v={youtube_id}"
                    
            # Método alternativo: buscar enlaces a YouTube en la página
            youtube_links = soup.select('a[href*="youtube.com/watch"], a[href*="youtu.be/"]')
            if youtube_links:
                return youtube_links[0]['href']
                
            return None
        except Exception as e:
            self.logger.error(f"Error al extraer ID de YouTube de Last.fm: {e}")
            return None
            
    def search_lastfm_track(self, title, artist):
        """Buscar una canción en Last.fm y extraer el enlace de YouTube"""
        # Si no tenemos BeautifulSoup o falta API key, regresar directamente
        if not HAS_BS4 or not self.lastfm_api_key:
            if not self.lastfm_api_key:
                self.logger.warning("No se ha configurado la API key de Last.fm")
            return None
            
        search_key = f"lastfm|{artist}|{title}"
        
        # Verificar caché
        if search_key in self.cache and not self.force_update:
            return self.cache[search_key]
            
        # Buscar la canción en Last.fm
        url = f"https://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={self.lastfm_api_key}&artist={quote_plus(artist)}&track={quote_plus(title)}&format=json"
        result = self.api_request(url, service="Last.fm API")
        
        if not result or isinstance(result, str):
            self.cache[search_key] = None
            return None
            
        # Verificar si hay un error en el resultado
        if isinstance(result, dict) and 'error' in result:
            self.logger.warning(f"Error en Last.fm API: {result.get('message', 'Desconocido')}")
            self.cache[search_key] = None
            return None
            
        try:
            track_url = result['track']['url']
            lastfm_url = track_url
            
            # Crear resultado base
            result_data = {
                'lastfm_url': lastfm_url
            }
            
            # Intentar obtener el enlace de YouTube desde la página de Last.fm
            youtube_url = self.get_youtube_from_lastfm_page(lastfm_url)
            if youtube_url:
                result_data['youtube_url'] = youtube_url
                
            # Guardar en caché
            self.cache[search_key] = result_data
            return result_data
            
        except (KeyError, TypeError) as e:
            self.logger.error(f"Error procesando resultado de Last.fm: {e}")
            self.cache[search_key] = None
            return None
            
    def search_discogs_release(self, title, artist, album=None):
        """Buscar un lanzamiento en Discogs"""
        search_key = f"discogs|{title}|{artist}|{album or ''}"
        
        # Verificar caché para no repetir búsquedas
        if search_key in self.cache and not self.force_update:
            return self.cache[search_key]
        
        query = f"{title} {artist}"
        if album:
            query += f" {album}"
        
        url = f"https://api.discogs.com/database/search?q={quote_plus(query)}&type=release&token={self.discogs_token}"
        result = self.discogs_request(url)
        
        if result and 'results' in result and len(result['results']) > 0:
            # Guardar el primer resultado en caché
            release_id = result['results'][0].get('id')
            release_url = f"https://www.discogs.com/release/{release_id}"
            self.cache[search_key] = {
                'discogs_url': release_url,
                'release_id': release_id
            }
            
            # Obtener detalles del lanzamiento, incluyendo videos
            release_data_url = f"https://api.discogs.com/releases/{release_id}?token={self.discogs_token}"
            release_data = self.discogs_request(release_data_url)
            
            if release_data and 'videos' in release_data and len(release_data['videos']) > 0:
                # Guardar las URLs de los videos
                self.cache[search_key]['videos'] = [video['uri'] for video in release_data['videos']]
                # Guardar el primer video como youtube_url
                for video in release_data['videos']:
                    if 'youtube.com' in video['uri'] or 'youtu.be' in video['uri']:
                        self.cache[search_key]['youtube_url'] = video['uri']
                        break
            
            return self.cache[search_key]
        else:
            # Guardar búsqueda fallida en caché para no repetir
            self.cache[search_key] = None
            return None
            
    def search_links(self, title, artist, album=None):
        """Buscar enlaces usando múltiples fuentes"""
        result = {}
        
        # Buscar en Discogs primero si está habilitado
        if self.use_discogs and self.discogs_token:
            try:
                discogs_result = self.search_discogs_release(title, artist, album)
                if discogs_result:
                    # Solo guardar youtube_url ya que discogs_url no existe en song_links
                    if 'youtube_url' in discogs_result:
                        result['youtube_url'] = discogs_result['youtube_url']
            except Exception as e:
                self.logger.error(f"Error al buscar en Discogs: {e}")
        
        # Si no encontramos un enlace de YouTube en Discogs, intentar con Last.fm
        if self.use_lastfm and ('youtube_url' not in result or not result['youtube_url']):
            try:
                lastfm_result = self.search_lastfm_track(title, artist)
                if lastfm_result:
                    # Actualizar solo campos que no tenemos ya
                    for key, value in lastfm_result.items():
                        if key in ['youtube_url', 'lastfm_url'] and (key not in result or not result[key]):
                            result[key] = value
            except Exception as e:
                self.logger.error(f"Error al buscar en Last.fm: {e}")
                
        return result if result else None
    
    def get_songs_to_process(self):
        """Obtener canciones para procesar"""
        if 'songs' not in self.entity_types:
            return []
            
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Modificamos la consulta para buscar canciones sin enlaces de YouTube
            query = """
                SELECT s.id, s.title, s.artist, s.album 
                FROM songs s
                LEFT JOIN song_links sl ON s.id = sl.song_id
            """
            
            if self.missing_only:
                query += " WHERE sl.youtube_url IS NULL OR sl.youtube_url = ''"
                
            query += f" LIMIT {self.batch_size}"
            
            self.logger.debug(f"Query para obtener canciones: {query}")
            cursor.execute(query)
            songs = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return songs
        except Exception as e:
            self.logger.error(f"Error al obtener canciones: {e}")
            return []
    
    def get_albums_with_discogs_url(self):
        """Obtener álbumes que ya tienen URL de Discogs"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT a.id, a.name as album_name, ar.name as artist_name, a.discogs_url, a.year
                FROM albums a
                JOIN artists ar ON a.artist_id = ar.id
                WHERE a.discogs_url IS NOT NULL AND a.discogs_url != ''
                LIMIT ?
            """
            
            cursor.execute(query, (self.batch_size,))
            albums = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return albums
        except Exception as e:
            self.logger.error(f"Error al obtener álbumes con Discogs URL: {e}")
            return []
            
    def get_songs_from_album(self, album_id):
        """Obtener todas las canciones de un álbum"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Primero, obtenemos el nombre del álbum
            cursor.execute("SELECT name FROM albums WHERE id = ?", (album_id,))
            album_row = cursor.fetchone()
            
            if not album_row:
                self.logger.warning(f"No se encontró el álbum con ID {album_id}")
                conn.close()
                return []
                
            album_name = album_row['name']
            
            # Ahora buscamos canciones con ese nombre de álbum
            query = """
                SELECT s.id, s.title, s.artist, s.track_number
                FROM songs s
                WHERE s.album = ?
                ORDER BY s.track_number, s.title
            """
            
            cursor.execute(query, (album_name,))
            songs = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return songs
        except Exception as e:
            self.logger.error(f"Error al obtener canciones del álbum {album_id}: {e}")
            return []
            
    def get_release_id_from_url(self, discogs_url):
        """Extrae el ID de release de una URL de Discogs"""
        try:
            # Patrones comunes de URLs de Discogs
            patterns = [
                r'release/(\d+)',
                r'releases/(\d+)',
                r'master/(\d+)',
                r'masters/(\d+)',
                r'/(\d+)-'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, discogs_url)
                if match:
                    return match.group(1)
            
            return None
        except Exception as e:
            self.logger.error(f"Error al extraer release ID de {discogs_url}: {e}")
            return None
            
    def get_release_details(self, release_id):
        """Obtener detalles de un release de Discogs, incluyendo videos"""
        if not release_id:
            return None
            
        cache_key = f"release_{release_id}"
        if cache_key in self.cache and not self.force_update:
            return self.cache[cache_key]
            
        url = f"https://api.discogs.com/releases/{release_id}"
        if self.discogs_token:
            url += f"?token={self.discogs_token}"
            
        response = self.discogs_request(url)
        
        if response and 'videos' in response:
            # Guardar en caché
            self.cache[cache_key] = response
            return response
            
        return None
        
    def match_songs_to_videos(self, songs, videos):
        """Emparejar canciones con videos basándose en el título"""
        song_video_mapping = {}
        
        for song in songs:
            song_title = song['title'].lower()
            best_match = None
            best_score = 0
            
            for video in videos:
                video_title = video.get('title', '').lower()
                
                # Buscar coincidencia exacta primero
                if song_title in video_title or video_title in song_title:
                    score = len(song_title) / max(len(song_title), len(video_title))
                    if score > best_score:
                        best_score = score
                        best_match = video
                
                # Si no hay coincidencia exacta, intentar con palabras clave
                elif best_score < 0.7:  # Umbral para considerar coincidencias parciales
                    song_words = set(song_title.split())
                    video_words = set(video_title.split())
                    common_words = song_words.intersection(video_words)
                    
                    if common_words:
                        score = len(common_words) / max(len(song_words), len(video_words))
                        if score > best_score:
                            best_score = score
                            best_match = video
            
            # Solo considerar coincidencias con un score mínimo
            if best_score > 0.5:
                song_video_mapping[song['id']] = {
                    'video': best_match,
                    'score': best_score
                }
        
        return song_video_mapping
        
    def process_album_videos(self):
        """Procesar videos de álbumes que ya tienen URL de Discogs"""
        albums = self.get_albums_with_discogs_url()
        self.logger.info(f"Procesando videos para {len(albums)} álbumes con URL de Discogs")
        
        for i, album in enumerate(albums):
            self.logger.info(f"[{i+1}/{len(albums)}] Procesando álbum: {album['artist_name']} - {album['album_name']}")
            
            # Obtener el ID del release de Discogs
            release_id = self.get_release_id_from_url(album['discogs_url'])
            if not release_id:
                self.logger.warning(f"  No se pudo extraer el ID de release de {album['discogs_url']}")
                continue
                
            # Obtener detalles del release, incluyendo videos
            release_details = self.get_release_details(release_id)
            if not release_details or 'videos' not in release_details or not release_details['videos']:
                self.logger.info(f"  No se encontraron videos para este álbum en Discogs")
                continue
                
            # Filtrar solo videos de YouTube
            youtube_videos = [
                video for video in release_details['videos'] 
                if 'youtube.com' in video.get('uri', '') or 'youtu.be' in video.get('uri', '')
            ]
            
            if not youtube_videos:
                self.logger.info(f"  No se encontraron videos de YouTube para este álbum")
                continue
                
            self.logger.info(f"  Encontrados {len(youtube_videos)} videos de YouTube")
            
            # Obtener todas las canciones del álbum
            songs = self.get_songs_from_album(album['id'])
            if not songs:
                self.logger.warning(f"  No se encontraron canciones para este álbum")
                continue
                
            self.logger.info(f"  Encontradas {len(songs)} canciones en el álbum")
            
            # Emparejar canciones con videos
            song_video_mapping = self.match_songs_to_videos(songs, youtube_videos)
            
            # Actualizar enlaces en la base de datos
            for song_id, match_info in song_video_mapping.items():
                video = match_info['video']
                score = match_info['score']
                
                song_title = next((s['title'] for s in songs if s['id'] == song_id), "Desconocido")
                self.logger.info(f"  Emparejado: '{song_title}' con '{video.get('title', 'Sin título')}' (Score: {score:.2f})")
                
                # Actualizar en song_links
                self.update_song_links(song_id, {
                    'youtube_url': video.get('uri')
                })
            
            # Guardar caché periódicamente
            if (i + 1) % 5 == 0:
                self.save_cache()
    
    def update_song_links(self, song_id, data):
        """Actualizar links de canciones en la base de datos"""
        if not data:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verificar si ya existe un registro para esta canción
        cursor.execute("SELECT 1 FROM song_links WHERE song_id = ?", (song_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Actualizar registro existente
            update_fields = []
            params = []
            
            # Usar las columnas que existen en la tabla song_links
            for field, data_field in [
                ("youtube_url", "youtube_url"),
                ("lastfm_url", "lastfm_url")
            ]:
                if data_field in data and data[data_field]:
                    update_fields.append(f"{field} = ?")
                    params.append(data[data_field])
                
            if update_fields:
                params.append(song_id)
                query = f"UPDATE song_links SET {', '.join(update_fields)} WHERE song_id = ?"
                cursor.execute(query, params)
        else:
            # Crear nuevo registro
            fields = ["song_id"]
            values = [song_id]
            placeholders = ["?"]
            
            # Usar las columnas que existen en la tabla song_links
            for field, data_field in [
                ("youtube_url", "youtube_url"),
                ("lastfm_url", "lastfm_url")
            ]:
                if data_field in data and data[data_field]:
                    fields.append(field)
                    values.append(data[data_field])
                    placeholders.append("?")
                
            if len(fields) > 1:  # Al menos un campo además de song_id
                query = f"INSERT INTO song_links ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(query, values)
        
        conn.commit()
        conn.close()
    
    def update_album(self, album_id, data):
        """Actualizar información de álbum en la base de datos"""
        if not data:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        update_fields = []
        params = []
        
        # Mapeo de campos de data a campos de la tabla
        field_mapping = {
            "discogs_url": "discogs_url",
            "youtube_url": "youtube_url",
            "lastfm_url": "lastfm_url"
        }
        
        for db_field, data_field in field_mapping.items():
            if data_field in data and data[data_field]:
                update_fields.append(f"{db_field} = ?")
                params.append(data[data_field])
            
        if update_fields:
            params.append(album_id)
            query = f"UPDATE albums SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
        
        conn.commit()
        conn.close()
    
    def update_artist(self, artist_id, data):
        """Actualizar información de artista en la base de datos"""
        if not data:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        update_fields = []
        params = []
        
        # Mapeo de campos de data a campos de la tabla
        field_mapping = {
            "discogs_url": "discogs_url",
            "lastfm_url": "lastfm_url"
        }
        
        for db_field, data_field in field_mapping.items():
            if data_field in data and data[data_field]:
                update_fields.append(f"{db_field} = ?")
                params.append(data[data_field])
            
        if update_fields:
            params.append(artist_id)
            query = f"UPDATE artists SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
        
        conn.commit()
        conn.close()
    
    def process_songs(self):
        """Procesar canciones y actualizar enlaces"""
        songs = self.get_songs_to_process()
        self.logger.info(f"Procesando {len(songs)} canciones")
        
        for i, song in enumerate(songs):
            self.logger.info(f"[{i+1}/{len(songs)}] Procesando canción: {song['artist']} - {song['title']}")
            
            # Buscar información de la canción en las diferentes fuentes
            links_data = self.search_links(song['title'], song['artist'], song['album'])
            
            # Si no se encontró información, registrarlo
            if not links_data:
                self.logger.info(f"  No se encontraron enlaces para: {song['artist']} - {song['title']}")
            else:
                # Registrar el tipo de enlaces encontrados
                found_links = [key for key in links_data.keys() if key.endswith('_url')]
                if found_links:
                    self.logger.info(f"  Enlaces encontrados: {', '.join(found_links)}")
            
            # Actualizar los enlaces en la base de datos
            self.update_song_links(song['id'], links_data)
            
            # Guardar caché periódicamente
            if (i + 1) % 10 == 0:
                self.save_cache()
    
    def process_albums(self):
        """Procesar álbumes y actualizar enlaces"""
        albums = self.get_albums_to_process()
        self.logger.info(f"Procesando {len(albums)} álbumes")
        
        for i, album in enumerate(albums):
            self.logger.info(f"[{i+1}/{len(albums)}] Procesando álbum: {album['artist']} - {album['title']}")
            
            # Buscar información del álbum
            links_data = self.search_links(album['title'], album['artist'])
            
            # Actualizar la información en la base de datos
            self.update_album(album['id'], links_data)
            
            # Guardar caché periódicamente
            if (i + 1) % 10 == 0:
                self.save_cache()
    
    def process_artists(self):
        """Procesar artistas y actualizar enlaces"""
        artists = self.get_artists_to_process()
        self.logger.info(f"Procesando {len(artists)} artistas")
        
        for i, artist in enumerate(artists):
            self.logger.info(f"[{i+1}/{len(artists)}] Procesando artista: {artist['title']}")
            
            # Para artistas, buscamos usando solo el nombre del artista
            links_data = self.search_links("", artist['title'])
            
            # Actualizar la información en la base de datos
            self.update_artist(artist['id'], links_data)
            
            # Guardar caché periódicamente
            if (i + 1) % 10 == 0:
                self.save_cache()
    
    def run(self):
        """Ejecutar el módulo completo"""
        self.logger.info("=== Iniciando proceso de obtención de enlaces ===")
        
        try:
            # Verificar si la base de datos existe y es accesible
            if not os.path.exists(self.db_path):
                self.logger.error(f"La base de datos no existe en {self.db_path}")
                return
                
            # Verificar las tablas necesarias
            self.logger.info("Verificando estructura de la base de datos...")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Comprobar la tabla song_links
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_links'")
            if not cursor.fetchone():
                self.logger.error("La tabla song_links no existe en la base de datos")
                conn.close()
                return
                
            conn.close()
            
            # Procesamiento principal: videos de álbumes de Discogs
            self.logger.info("Procesando videos de álbumes desde Discogs...")
            self.process_album_videos()
            
            # Procesar cada tipo de entidad según configuración
            if 'songs' in self.entity_types:
                self.logger.info("Buscando enlaces para canciones individuales...")
                self.process_songs()
            
            # Guardar caché final
            self.save_cache()
            
        except Exception as e:
            self.logger.error(f"Error durante la ejecución: {e}", exc_info=True)
        
        self.logger.info("=== Proceso completado ===\n")


def main(config=None):
    """Función principal para ejecutar el módulo"""
    try:
        # Asegurar que tenemos una configuración
        if config is None:
            config = {}
        
        # Instanciar y ejecutar el módulo
        module = DiscogsLinksModule(config)
        module.run()
    except Exception as e:
        logging.error(f"Error al ejecutar discogs_links: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    # Para pruebas directas
    sys.exit(main())