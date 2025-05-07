#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
import sqlite3
import traceback
from pathlib import Path
from urllib.parse import quote_plus

# Intentar importar módulos específicos de servicios musicales con manejo de errores
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

try:
    import musicbrainzngs
    MUSICBRAINZ_AVAILABLE = True
except ImportError:
    MUSICBRAINZ_AVAILABLE = False

try:
    import pylast
    PYLAST_AVAILABLE = True
except ImportError:
    PYLAST_AVAILABLE = False

try:
    import discogs_client
    DISCOGS_AVAILABLE = True
except ImportError:
    DISCOGS_AVAILABLE = False


class ArtistImageDownloader:
    """
    Clase para descargar imágenes de artistas desde varias plataformas musicales.
    Soporta: Discogs, Last.fm, Spotify y MusicBrainz.
    """
    
    def __init__(self, db_path=None):
        self.db_path = db_path
        
        # Configuración de carpeta para guardar imágenes
        self.images_folder = os.path.join(os.path.expanduser("~"), ".cache", "music_app", "artist_images")
        os.makedirs(self.images_folder, exist_ok=True)
        
        # Clientes API para cada servicio
        self.spotify_client = None
        self.lastfm_client = None
        self.discogs_client = None
        self.musicbrainz_client_setup = False
        
        # Estadísticas
        self.stats = {
            'total': 0,
            'processed': 0,
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'sources': {
                'spotify': 0,
                'lastfm': 0,
                'discogs': 0,
                'musicbrainz': 0,
                'none': 0
            }
        }
    
    def log(self, message):
        """Envía mensajes de registro a la consola"""
        print(f"[ArtistImageDownloader] {message}")
    
    def connect_db(self):
        """Establece conexión con la base de datos"""
        if not self.db_path:
            raise ValueError("Database path not specified")
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Para acceder a las columnas por nombre
            return conn
        except Exception as e:
            self.log(f"Error connecting to database: {str(e)}")
            return None
    
    def setup_clients(self, spotify_config=None, lastfm_config=None, discogs_config=None, 
                     musicbrainz_config=None):
        """Configura los clientes API para cada servicio"""
        # Configurar Spotify
        if spotify_config and SPOTIPY_AVAILABLE:
            try:
                client_id = spotify_config.get('client_id')
                client_secret = spotify_config.get('client_secret')
                cache_path = spotify_config.get('cache_path')
                
                if not cache_path:
                    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "music_app", "spotify")
                    os.makedirs(cache_dir, exist_ok=True)
                    cache_path = os.path.join(cache_dir, "spotify_token.txt")
                
                if client_id and client_secret:
                    auth_manager = SpotifyOAuth(
                        client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=spotify_config.get('redirect_uri', 'http://localhost:8888/callback'),
                        scope="",
                        cache_path=cache_path,
                        open_browser=False
                    )
                    
                    # Si hay un token en cache válido, usarlo
                    token_info = auth_manager.get_cached_token()
                    if token_info and not auth_manager.is_token_expired(token_info):
                        self.spotify_client = spotipy.Spotify(auth=token_info['access_token'])
                        self.log("Autenticación Spotify completada usando token en caché")
                    else:
                        # Usar credenciales de cliente para acceso básico
                        self.spotify_client = spotipy.Spotify(
                            client_credentials_manager=spotipy.oauth2.SpotifyClientCredentials(
                                client_id=client_id,
                                client_secret=client_secret
                            )
                        )
                        self.log("Autenticación Spotify completada usando credenciales de cliente")
            except Exception as e:
                self.log(f"Error configurando cliente Spotify: {str(e)}")

        # Configurar Last.fm
        if lastfm_config and PYLAST_AVAILABLE:
            try:
                api_key = lastfm_config.get('api_key')
                api_secret = lastfm_config.get('api_secret')
                
                if api_key and api_secret:
                    self.lastfm_client = pylast.LastFMNetwork(
                        api_key=api_key,
                        api_secret=api_secret
                    )
                    self.log("Cliente Last.fm configurado correctamente")
            except Exception as e:
                self.log(f"Error configurando cliente Last.fm: {str(e)}")
        
        # Configurar Discogs
        if discogs_config and DISCOGS_AVAILABLE:
            try:
                token = discogs_config.get('token')
                user_agent = discogs_config.get('user_agent', 'MusicAppArtistImageDownloader/1.0')
                
                if token:
                    self.discogs_client = discogs_client.Client(user_agent, token=token)
                    self.log("Cliente Discogs configurado correctamente")
            except Exception as e:
                self.log(f"Error configurando cliente Discogs: {str(e)}")
        
        # Configurar MusicBrainz
        if musicbrainz_config and MUSICBRAINZ_AVAILABLE:
            try:
                app_name = musicbrainz_config.get('app_name', 'MusicAppImageDownloader')
                version = musicbrainz_config.get('version', '1.0')
                contact = musicbrainz_config.get('contact', 'user@example.com')
                
                musicbrainzngs.set_useragent(app_name, version, contact)
                self.musicbrainz_client_setup = True
                self.log("Cliente MusicBrainz configurado correctamente")
            except Exception as e:
                self.log(f"Error configurando cliente MusicBrainz: {str(e)}")
    
    def get_image_filename(self, artist_id, service_name):
        """Genera nombre de archivo para una imagen basado en el ID del artista y el servicio"""
        return os.path.join(self.images_folder, f"artist_{artist_id}_{service_name}.jpg")
    
    def download_image(self, url, output_path):
        """Descarga una imagen desde una URL y la guarda en disco"""
        try:
            if not url:
                return False
            
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code != 200:
                return False
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
        except Exception as e:
            self.log(f"Error downloading image: {str(e)}")
            return False
    
    def search_spotify_artist_image(self, artist_name, artist_id):
        """Busca imagen de artista en Spotify"""
        if not self.spotify_client:
            return None
        
        try:
            # Buscar artista por nombre
            results = self.spotify_client.search(q=f'artist:"{artist_name}"', type='artist', limit=5)
            
            if results and 'artists' in results and 'items' in results['artists'] and results['artists']['items']:
                # Iterar sobre los resultados para encontrar la mejor coincidencia
                for artist in results['artists']['items']:
                    if artist['name'].lower() == artist_name.lower() and artist['images']:
                        # Ordenar imágenes por tamaño (de mayor a menor)
                        images = sorted(artist['images'], key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
                        
                        if images:
                            img_url = images[0]['url']
                            output_path = self.get_image_filename(artist_id, 'spotify')
                            
                            if self.download_image(img_url, output_path):
                                self.update_artist_image_path(artist_id, output_path, 'spotify')
                                self.stats['sources']['spotify'] += 1
                                return output_path
            
            # Si llegamos aquí, no encontramos la imagen
            return None
        except Exception as e:
            self.log(f"Error buscando imagen en Spotify para {artist_name}: {str(e)}")
            return None
    
    def search_lastfm_artist_image(self, artist_name, artist_id):
        """Busca imagen de artista en Last.fm"""
        if not self.lastfm_client:
            return None
        
        try:
            artist = self.lastfm_client.get_artist(artist_name)
            img_url = artist.get_cover_image(size=pylast.SIZE_MEGA)
            
            if img_url and img_url != "":
                output_path = self.get_image_filename(artist_id, 'lastfm')
                
                if self.download_image(img_url, output_path):
                    self.update_artist_image_path(artist_id, output_path, 'lastfm')
                    self.stats['sources']['lastfm'] += 1
                    return output_path
            
            return None
        except Exception as e:
            self.log(f"Error buscando imagen en Last.fm para {artist_name}: {str(e)}")
            return None
    
    def search_discogs_artist_image(self, artist_name, artist_id):
        """Busca imagen de artista en Discogs"""
        if not self.discogs_client:
            return None
        
        try:
            # Buscar artista en Discogs
            results = self.discogs_client.search(artist_name, type='artist')
            
            if results:
                for result in results:
                    # Verificar que es un artista y tiene imágenes
                    if hasattr(result, 'images') and result.images:
                        # Buscar imagen primaria o la primera disponible
                        primary_image = None
                        for img in result.images:
                            if img.get('type') == 'primary':
                                primary_image = img.get('uri')
                                break
                        
                        # Si no hay primaria, usar la primera imagen
                        if not primary_image and result.images:
                            primary_image = result.images[0].get('uri')
                        
                        if primary_image:
                            output_path = self.get_image_filename(artist_id, 'discogs')
                            
                            if self.download_image(primary_image, output_path):
                                self.update_artist_image_path(artist_id, output_path, 'discogs')
                                self.stats['sources']['discogs'] += 1
                                return output_path
                        
                        # Solo procesamos el primer resultado que tenga imágenes
                        break
            
            return None
        except Exception as e:
            self.log(f"Error buscando imagen en Discogs para {artist_name}: {str(e)}")
            return None
    
    def search_musicbrainz_artist_image(self, artist_name, artist_id, mbid=None):
        """Busca imagen de artista en MusicBrainz/Cover Art Archive"""
        if not self.musicbrainz_client_setup:
            return None
        
        try:
            # Si tenemos MBID, usarlo directamente
            if mbid:
                try:
                    artist_info = musicbrainzngs.get_artist_by_id(mbid, includes=['url-rels'])
                    if 'artist' in artist_info:
                        relations = artist_info['artist'].get('url-relation-list', [])
                        
                        # Buscar relación con imagen, generalmente en servicios externos
                        for relation in relations:
                            if relation.get('type') == 'image':
                                img_url = relation.get('target')
                                
                                if img_url:
                                    output_path = self.get_image_filename(artist_id, 'musicbrainz')
                                    
                                    if self.download_image(img_url, output_path):
                                        self.update_artist_image_path(artist_id, output_path, 'musicbrainz')
                                        self.stats['sources']['musicbrainz'] += 1
                                        return output_path
                except Exception as e:
                    self.log(f"Error obteniendo artista por MBID: {str(e)}")
            
            # Si no tenemos MBID o falló la búsqueda directa, buscar por nombre
            results = musicbrainzngs.search_artists(artist=artist_name)
            
            if 'artist-list' in results and results['artist-list']:
                # Tomar el primer resultado (asumiendo es el más relevante)
                first_artist = results['artist-list'][0]
                found_mbid = first_artist.get('id')
                
                if found_mbid:
                    # Actualizar el MBID en la base de datos si no lo teníamos
                    if not mbid:
                        self.update_artist_mbid(artist_id, found_mbid)
                    
                    # Intentar obtener imagen
                    artist_info = musicbrainzngs.get_artist_by_id(found_mbid, includes=['url-rels'])
                    if 'artist' in artist_info:
                        relations = artist_info['artist'].get('url-relation-list', [])
                        
                        for relation in relations:
                            if relation.get('type') == 'image':
                                img_url = relation.get('target')
                                
                                if img_url:
                                    output_path = self.get_image_filename(artist_id, 'musicbrainz')
                                    
                                    if self.download_image(img_url, output_path):
                                        self.update_artist_image_path(artist_id, output_path, 'musicbrainz')
                                        self.stats['sources']['musicbrainz'] += 1
                                        return output_path
            
            return None
        except Exception as e:
            self.log(f"Error buscando imagen en MusicBrainz para {artist_name}: {str(e)}")
            return None
    
    def update_artist_image_path(self, artist_id, image_path, source):
        """Actualiza la ruta de imagen del artista en la base de datos"""
        try:
            conn = self.connect_db()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Revisar si ya existe una entrada en artists_networks
            cursor.execute("SELECT id FROM artists_networks WHERE artist_id = ?", (artist_id,))
            result = cursor.fetchone()
            
            if result:
                # Actualizar entrada existente
                if source == 'spotify':
                    cursor.execute("UPDATE artists_networks SET spotify = ? WHERE artist_id = ?", 
                                  (image_path, artist_id))
                elif source == 'lastfm':
                    cursor.execute("UPDATE artists_networks SET lastfm = ? WHERE artist_id = ?", 
                                  (image_path, artist_id))
                elif source == 'discogs':
                    cursor.execute("UPDATE artists_networks SET discogs_url = ? WHERE artist_id = ?", 
                                  (image_path, artist_id))
                elif source == 'musicbrainz':
                    cursor.execute("UPDATE artists_networks SET musicbrainz_url = ? WHERE artist_id = ?", 
                                  (image_path, artist_id))
            else:
                # Crear nueva entrada
                if source == 'spotify':
                    cursor.execute("INSERT INTO artists_networks (artist_id, spotify) VALUES (?, ?)", 
                                  (artist_id, image_path))
                elif source == 'lastfm':
                    cursor.execute("INSERT INTO artists_networks (artist_id, lastfm) VALUES (?, ?)", 
                                  (artist_id, image_path))
                elif source == 'discogs':
                    cursor.execute("INSERT INTO artists_networks (artist_id, discogs_url) VALUES (?, ?)", 
                                  (artist_id, image_path))
                elif source == 'musicbrainz':
                    cursor.execute("INSERT INTO artists_networks (artist_id, musicbrainz_url) VALUES (?, ?)", 
                                  (artist_id, image_path))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.log(f"Error actualizando ruta de imagen: {str(e)}")
            if conn:
                conn.close()
            return False
    
    def update_artist_mbid(self, artist_id, mbid):
        """Actualiza el MBID de un artista en la base de datos"""
        try:
            conn = self.connect_db()
            if not conn:
                return False
            
            cursor = conn.cursor()
            cursor.execute("UPDATE artists SET mbid = ? WHERE id = ?", (mbid, artist_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.log(f"Error actualizando MBID: {str(e)}")
            if conn:
                conn.close()
            return False
    
    def get_artists_without_images(self):
        """Obtiene lista de artistas que no tienen imágenes asociadas"""
        try:
            conn = self.connect_db()
            if not conn:
                return []
            
            cursor = conn.cursor()
            # Buscar artistas que no tienen entrada en artists_networks o tienen entradas vacías
            query = """
                SELECT a.id, a.name, a.mbid
                FROM artists a
                LEFT JOIN artists_networks an ON a.id = an.artist_id
                WHERE an.artist_id IS NULL
                   OR (an.spotify IS NULL AND an.lastfm IS NULL AND an.discogs_url IS NULL AND an.musicbrainz_url IS NULL)
            """
            
            cursor.execute(query)
            artists = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return artists
        except Exception as e:
            self.log(f"Error obteniendo artistas sin imágenes: {str(e)}")
            if conn:
                conn.close()
            return []
    
    def get_all_artists(self):
        """Obtiene todos los artistas de la base de datos"""
        try:
            conn = self.connect_db()
            if not conn:
                return []
            
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, mbid FROM artists")
            artists = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return artists
        except Exception as e:
            self.log(f"Error obteniendo todos los artistas: {str(e)}")
            if conn:
                conn.close()
            return []
    
    def start_download(self, missing_only=True, limit=None):
        """Inicia el proceso de descarga de imágenes de artistas"""
        # Obtener lista de artistas
        if missing_only:
            artists = self.get_artists_without_images()
            self.log(f"Encontrados {len(artists)} artistas sin imágenes")
        else:
            artists = self.get_all_artists()
            self.log(f"Procesando todos los {len(artists)} artistas")
        
        # Aplicar límite si se especifica
        if limit and limit > 0:
            artists = artists[:limit]
            self.log(f"Limitando a {limit} artistas")
        
        # Actualizar estadísticas
        self.stats['total'] = len(artists)
        self.stats['processed'] = 0
        self.stats['downloaded'] = 0
        self.stats['skipped'] = 0
        self.stats['failed'] = 0
        self.stats['sources'] = {'spotify': 0, 'lastfm': 0, 'discogs': 0, 'musicbrainz': 0, 'none': 0}
        
        # Procesar cada artista
        for i, artist in enumerate(artists):
            # Actualizar progreso
            self.stats['processed'] = i + 1
            progress_percent = int((i + 1) / len(artists) * 100)
            self.log(f"Progreso: {progress_percent}% ({i + 1}/{len(artists)})")
            
            artist_id = artist['id']
            artist_name = artist['name']
            mbid = artist.get('mbid')
            
            self.log(f"Procesando artista: {artist_name}")
            
            # Intentar descargar imagen de cada servicio en orden
            image_path = None
            
            # 1. Spotify
            if self.spotify_client:
                image_path = self.search_spotify_artist_image(artist_name, artist_id)
                if image_path:
                    self.log(f"Imagen de Spotify descargada para: {artist_name}")
                    self.stats['downloaded'] += 1
                    continue
            
            # 2. Last.fm
            if not image_path and self.lastfm_client:
                image_path = self.search_lastfm_artist_image(artist_name, artist_id)
                if image_path:
                    self.log(f"Imagen de Last.fm descargada para: {artist_name}")
                    self.stats['downloaded'] += 1
                    continue
            
            # 3. Discogs
            if not image_path and self.discogs_client:
                image_path = self.search_discogs_artist_image(artist_name, artist_id)
                if image_path:
                    self.log(f"Imagen de Discogs descargada para: {artist_name}")
                    self.stats['downloaded'] += 1
                    continue
            
            # 4. MusicBrainz
            if not image_path and self.musicbrainz_client_setup:
                image_path = self.search_musicbrainz_artist_image(artist_name, artist_id, mbid)
                if image_path:
                    self.log(f"Imagen de MusicBrainz descargada para: {artist_name}")
                    self.stats['downloaded'] += 1
                    continue
            
            # No se encontró imagen en ningún servicio
            if not image_path:
                self.log(f"No se encontró imagen para: {artist_name}")
                self.stats['failed'] += 1
                self.stats['sources']['none'] += 1
            
            # Pausa para evitar sobrecargar las APIs
            time.sleep(0.5)
        
        # Mostrar resultados
        self.log(f"\nProceso completado. Descargadas: {self.stats['downloaded']}, "
                f"Fallidas: {self.stats['failed']}, Total: {self.stats['total']}")
        self.log(f"Fuentes: Spotify: {self.stats['sources']['spotify']}, "
                f"Last.fm: {self.stats['sources']['lastfm']}, "
                f"Discogs: {self.stats['sources']['discogs']}, "
                f"MusicBrainz: {self.stats['sources']['musicbrainz']}, "
                f"Ninguna: {self.stats['sources']['none']}")
        
        return self.stats


def main(config):
    """
    Función principal compatible con db_creator.py
    Recibe un diccionario de configuración y ejecuta el proceso.
    """
    # Extraer configuración
    db_path = config.get('db_path')
    
    if not db_path:
        print("Error: No se especificó ruta de base de datos (db_path)")
        return 1
    
    # Configuración de clientes API
    spotify_config = {
        'client_id': config.get('spotify_client_id'),
        'client_secret': config.get('spotify_client_secret'),
        'cache_path': config.get('spotify_cache_path')
    }
    
    lastfm_config = {
        'api_key': config.get('lastfm_api_key'),
        'api_secret': config.get('lastfm_api_secret')
    }
    
    discogs_config = {
        'token': config.get('discogs_token'),
        'user_agent': config.get('discogs_user_agent', 'MusicAppArtistImageDownloader/1.0')
    }
    
    musicbrainz_config = {
        'app_name': config.get('musicbrainz_app_name', 'MusicAppImageDownloader'),
        'version': config.get('musicbrainz_version', '1.0'),
        'contact': config.get('musicbrainz_contact', 'user@example.com')
    }
    
    # Crear el directorio de imágenes personalizado si se especifica
    images_folder = config.get('images_folder')
    
    # Crear instancia del descargador
    downloader = ArtistImageDownloader(db_path=db_path)
    
    # Configurar directorio de imágenes personalizado si se proporciona
    if images_folder:
        downloader.images_folder = images_folder
        os.makedirs(images_folder, exist_ok=True)
        print(f"Directorio de imágenes configurado en: {images_folder}")
    
    # Configurar clientes API
    downloader.setup_clients(
        spotify_config=spotify_config if spotify_config.get('client_id') else None,
        lastfm_config=lastfm_config if lastfm_config.get('api_key') else None,
        discogs_config=discogs_config if discogs_config.get('token') else None,
        musicbrainz_config=musicbrainz_config
    )
    
    # Iniciar descarga
    stats = downloader.start_download(
        missing_only=config.get('missing_only', True),
        limit=config.get('limit')
    )
    
    # Guardar estadísticas en un archivo JSON si se especifica
    stats_file = config.get('stats_file')
    if stats_file:
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            print(f"Estadísticas guardadas en: {stats_file}")
        except Exception as e:
            print(f"Error guardando estadísticas: {str(e)}")
    
    return 0


# Para uso desde línea de comandos
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Descargar imágenes de artistas desde varias plataformas musicales')
    parser.add_argument('--db', required=True, help='Ruta al archivo de base de datos SQLite')
    parser.add_argument('--spotify-client-id', help='Spotify Client ID')
    parser.add_argument('--spotify-secret', help='Spotify Client Secret')
    parser.add_argument('--lastfm-api-key', help='Last.fm API Key')
    parser.add_argument('--lastfm-secret', help='Last.fm API Secret')
    parser.add_argument('--discogs-token', help='Discogs API Token')
    parser.add_argument('--limit', type=int, help='Límite de artistas a procesar')
    parser.add_argument('--all', action='store_true', help='Procesar todos los artistas, no solo los que faltan')
    parser.add_argument('--images-folder', help='Directorio donde se guardarán las imágenes')
    
    args = parser.parse_args()
    
    # Crear configuración a partir de los argumentos
    config = {
        'db_path': args.db,
        'spotify_client_id': args.spotify_client_id,
        'spotify_client_secret': args.spotify_client_secret,
        'lastfm_api_key': args.lastfm_api_key,
        'lastfm_api_secret': args.lastfm_secret,
        'discogs_token': args.discogs_token,
        'limit': args.limit,
        'missing_only': not args.all,
        'images_folder': args.images_folder
    }
    
    main(config)