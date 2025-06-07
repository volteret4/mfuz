#!/usr/bin/env python
#
# Nombre:: db_musica_spotify.py
# Descripción: Lee artistas seguidos por un usuario de Spotify, extrae sus álbumes y canciones, y las guarda en una base de datos.
# Basado en: db_musica_path.py
#
# Notes: Este script complementa db_musica_path.py y puede ejecutarse de forma independiente o después de él.
#        Extrae datos de Spotify e ignora artistas ya existentes en la base de datos con origen 'local'.
#
#   Dependencias:   - python3, sqlite3, spotipy
#                   - Credenciales de API de Spotify

import os
import sys
import json
import logging
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
import time
import re

# Añadir el path del proyecto al sys.path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import PROJECT_ROOT, BaseModule

# Intentar importar spotipy
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False
    print("Error: El módulo 'spotipy' no está instalado. Ejecútalo con: pip install spotipy")
    sys.exit(1)


class MusicSpotifyManager:
    def __init__(self, db_path: str, spotify_client_id: str = None, spotify_client_secret: str = None, 
                 spotify_redirect_uri: str = "http://localhost:8888/callback",
                 spotify_cache_path: str = None, force_update: bool = False, 
                 skip_existing_artists: bool = True, user_id: str = None):
        """
        Inicializa el gestor de música desde Spotify.
        
        Args:
            db_path: Ruta al archivo de la base de datos SQLite
            spotify_client_id: ID de cliente de Spotify
            spotify_client_secret: Secreto de cliente de Spotify
            spotify_redirect_uri: URI de redirección para autenticación de Spotify
            spotify_cache_path: Ruta para almacenar el token de Spotify
            force_update: Si es True, fuerza la actualización de los datos existentes
            skip_existing_artists: Si es True, omite artistas que ya existen en la base de datos con origen 'local'
            user_id: ID de usuario de Spotify (opcional, si no se proporciona se obtiene del usuario autenticado)
        """
        super().__init__()
        
        self.db_path = Path(db_path).resolve()
        self.spotify_client_id = spotify_client_id
        self.spotify_client_secret = spotify_client_secret
        self.spotify_redirect_uri = spotify_redirect_uri
        self.spotify_cache_path = spotify_cache_path or str(PROJECT_ROOT / ".content" / "cache" / ".spotify_token.json")
        self.force_update = force_update
        self.skip_existing_artists = skip_existing_artists
        self.user_id = user_id
        
        # Configuración de logging
        self.logger = self._setup_logger()
        
        # Tratar de obtener credenciales de Spotify si no se proporcionaron
        if not self.spotify_client_id or not self.spotify_client_secret:
            self._load_spotify_credentials()
        
        # Inicializar el cliente de Spotify
        self.spotify = self._init_spotify()
        
        # Verificar si el cliente de Spotify está inicializado correctamente
        if not self.spotify:
            self.logger.error("No se pudo inicializar el cliente de Spotify. Revisa las credenciales y la conexión.")
            sys.exit(1)
        
        # Obtener el ID de usuario de Spotify si no se proporcionó
        if not self.user_id:
            self.user_id = self._get_spotify_user_id()
        
        # Inicializar la base de datos
        self.init_database()

    def _setup_logger(self):
        """Configura y devuelve un logger."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Crear manejador para la consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Establecer el formato
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Añadir el manejador al logger
        logger.addHandler(console_handler)
        
        # Crear directorio para logs si no existe
        log_dir = PROJECT_ROOT / ".content" / "logs" / "db"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Crear manejador para archivo
        file_handler = logging.FileHandler(log_dir / "db_musica_spotify.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Añadir el manejador al logger
        logger.addHandler(file_handler)
        
        return logger

    def _load_spotify_credentials(self):
        """Carga las credenciales de Spotify desde un archivo de configuración o variables de entorno."""
        try:
            # Intentar cargar desde archivo de configuración
            config_path = PROJECT_ROOT / "config" / "config.yml"
            if os.path.exists(config_path):
                try:
                    import yaml
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                    
                    spotify_config = config.get('spotify', {})
                    if spotify_config:
                        self.spotify_client_id = spotify_config.get('client_id')
                        self.spotify_client_secret = spotify_config.get('client_secret')
                        self.spotify_redirect_uri = spotify_config.get('redirect_uri', self.spotify_redirect_uri)
                except Exception as e:
                    self.logger.warning(f"Error al cargar configuración YAML: {e}")
            
            # Si todavía no tenemos credenciales, intentar con variables de entorno
            if not self.spotify_client_id:
                self.spotify_client_id = os.environ.get('SPOTIFY_CLIENT_ID')
            if not self.spotify_client_secret:
                self.spotify_client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
            if not self.spotify_redirect_uri or self.spotify_redirect_uri == "http://localhost:8888/callback":
                env_redirect_uri = os.environ.get('SPOTIFY_REDIRECT_URI')
                if env_redirect_uri:
                    self.spotify_redirect_uri = env_redirect_uri
            
            # Alternativamente, intentar usar spotify_login.py si está disponible
            try:
                from spotify_login import SpotifyAuthManager
                auth_manager = SpotifyAuthManager(project_root=str(PROJECT_ROOT))
                sp_client = auth_manager.get_client()
                if sp_client:
                    self.spotify = sp_client
                    self.logger.info("Cliente de Spotify obtenido con éxito usando SpotifyAuthManager")
                    return
            except ImportError:
                pass
            
            if not self.spotify_client_id or not self.spotify_client_secret:
                self.logger.warning("No se encontraron credenciales de Spotify. Configuración incompleta.")
                
        except Exception as e:
            self.logger.error(f"Error al cargar credenciales de Spotify: {str(e)}")
            import traceback
            self.logger.error(f"Detalles del error: {traceback.format_exc()}")

    def _init_spotify(self):
        """
        Inicializa y devuelve el cliente de la API de Spotify.
        
        Returns:
            spotipy.Spotify o None: Instancia del cliente de Spotify o None si falla la inicialización
        """
        # Si ya tenemos un cliente inicializado (posiblemente de SpotifyAuthManager)
        if hasattr(self, 'spotify') and self.spotify:
            return self.spotify
        
        # Verificar credenciales
        if not self.spotify_client_id or not self.spotify_client_secret:
            self.logger.error("No se proporcionaron credenciales de Spotify")
            return None
        
        try:
            # Crear objeto de autenticación
            scope = "user-follow-read user-library-read"
            sp_oauth = SpotifyOAuth(
                client_id=self.spotify_client_id,
                client_secret=self.spotify_client_secret,
                redirect_uri=self.spotify_redirect_uri,
                scope=scope,
                cache_path=self.spotify_cache_path,
                open_browser=True
            )
            
            # Obtener token (esto podría abrir el navegador para la autenticación si es necesario)
            token_info = sp_oauth.get_cached_token()
            
            if not token_info:
                auth_url = sp_oauth.get_authorize_url()
                self.logger.info(f"Visita esta URL para autorizar la aplicación: {auth_url}")
                response = input("Introduce la URL de redirección completa:")
                code = sp_oauth.parse_response_code(response)
                token_info = sp_oauth.get_access_token(code)
            
            # Crear cliente de Spotify
            spotify = spotipy.Spotify(auth=token_info['access_token'])
            
            # Verificar que el cliente funciona con una consulta simple
            spotify.current_user()
            
            return spotify
        
        except Exception as e:
            self.logger.error(f"Error al inicializar el cliente de Spotify: {str(e)}")
            return None

    def _get_spotify_user_id(self):
        """
        Obtiene el ID del usuario de Spotify autenticado.
        
        Returns:
            str: ID del usuario de Spotify
        """
        try:
            user_info = self.spotify.current_user()
            user_id = user_info['id']
            self.logger.info(f"Usuario de Spotify autenticado: {user_info['display_name']} (ID: {user_id})")
            return user_id
        except Exception as e:
            self.logger.error(f"Error al obtener el ID de usuario de Spotify: {str(e)}")
            sys.exit(1)

    def init_database(self):
        """Inicializa la base de datos si no existe o actualiza el esquema si es necesario."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Crear todas las tablas necesarias primero
        self._create_tables(c)
        
        # Luego verificar y actualizar esquema
        self._verify_schema(c)
        
        conn.commit()
        conn.close()

    def _create_tables(self, cursor):
        """Crea las tablas necesarias en la base de datos."""
        
        # Tabla artists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY,
                name TEXT,
                bio TEXT,
                tags TEXT,
                similar_artists TEXT,
                last_updated TIMESTAMP,
                origin TEXT,
                formed_year INTEGER,
                total_albums INTEGER,
                spotify_url TEXT,
                youtube_url TEXT,
                musicbrainz_url TEXT,
                discogs_url TEXT,
                rateyourmusic_url TEXT,
                links_updated TIMESTAMP,
                wikipedia_url TEXT,
                wikipedia_content TEXT,
                wikipedia_updated TIMESTAMP,
                mbid TEXT,
                bandcamp_url TEXT,
                member_of TEXT,
                aliases TEXT,
                lastfm_url TEXT,
                origen TEXT DEFAULT 'spotify',
                website TEXT,
                added_timestamp TIMESTAMP,
                added_day INTEGER,
                added_week INTEGER,
                added_month INTEGER,
                added_year INTEGER,
                img TEXT,
                img_urls TEXT,
                img_paths TEXT,
                jaangle_ready BOOLEAN DEFAULT 1,
                spotify_popularity INTEGER
            )
        ''')
        
        # Tabla albums
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY,
                artist_id INTEGER,
                name TEXT,
                year TEXT,
                label TEXT,
                genre TEXT,
                total_tracks INTEGER,
                album_art_path TEXT,
                last_updated TIMESTAMP,
                spotify_url TEXT,
                spotify_id TEXT,
                youtube_url TEXT,
                musicbrainz_url TEXT,
                discogs_url TEXT,
                rateyourmusic_url TEXT,
                links_updated TIMESTAMP,
                wikipedia_url TEXT,
                wikipedia_content TEXT,
                wikipedia_updated TIMESTAMP,
                mbid TEXT,
                folder_path TEXT,
                bitrate_range TEXT,
                bandcamp_url TEXT,
                producers TEXT,
                engineers TEXT,
                mastering_engineers TEXT,
                credits TEXT,
                lastfm_url TEXT,
                origen TEXT DEFAULT 'spotify',
                added_timestamp TIMESTAMP,
                added_day INTEGER,
                added_week INTEGER,
                added_month INTEGER,
                added_year INTEGER,
                album_art_urls TEXT,
                musicbrainz_albumid TEXT,
                musicbrainz_albumartistid TEXT,
                musicbrainz_releasegroupid TEXT,
                catalognumber TEXT,
                media TEXT,
                discnumber TEXT,
                releasecountry TEXT,
                originalyear INTEGER,
                FOREIGN KEY(artist_id) REFERENCES artists(id)
            )
        ''')
        
        # Tabla songs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY,
                file_path TEXT,
                title TEXT,
                track_number INTEGER,
                artist TEXT,
                album_artist TEXT,
                album TEXT,
                date TEXT,
                genre TEXT,
                label TEXT,
                mbid TEXT,
                bitrate INTEGER,
                bit_depth INTEGER,
                sample_rate INTEGER,
                last_modified TIMESTAMP,
                added_timestamp TIMESTAMP,
                added_week INTEGER,
                added_month INTEGER,
                added_year INTEGER,
                duration REAL,
                lyrics_id INTEGER,
                replay_gain_track_gain REAL,
                replay_gain_track_peak REAL,
                replay_gain_album_gain REAL,
                replay_gain_album_peak REAL,
                album_art_path_denorm TEXT,
                has_lyrics INTEGER DEFAULT 0,
                origen TEXT DEFAULT 'spotify',
                reproducciones INTEGER DEFAULT 1,
                fecha_reproducciones TEXT,
                scrobbles_ids TEXT,
                added_day INTEGER,
                musicbrainz_artistid TEXT,
                musicbrainz_recordingid TEXT,
                musicbrainz_albumartistid TEXT,
                musicbrainz_releasegroupid TEXT
            )
        ''')
        
        # Tabla genres
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY,
                name TEXT,
                description TEXT,
                related_genres TEXT,
                origin_year INTEGER,
                origen TEXT
            )
        ''')
        
        # Tabla lyrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lyrics (
                id INTEGER PRIMARY KEY,
                track_id INTEGER,
                lyrics TEXT,
                source TEXT DEFAULT 'Genius',
                last_updated TIMESTAMP,
                FOREIGN KEY(track_id) REFERENCES songs(id)
            )
        ''')
                
        # Tabla song_links
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS song_links (
                id INTEGER PRIMARY KEY,
                song_id INTEGER,
                spotify_url TEXT,
                spotify_id TEXT,
                lastfm_url TEXT,
                links_updated TIMESTAMP,
                youtube_url TEXT,
                musicbrainz_url TEXT,
                musicbrainz_recording_id TEXT,
                bandcamp_url TEXT,
                soundcloud_url TEXT,
                boomkat_url TEXT,
                preview_url TEXT,
                listenbrainz_preview_url TEXT,
                FOREIGN KEY(song_id) REFERENCES songs(id)
            )
        ''')
        
        # Tablas FTS (Full Text Search) - solo si no existen
        try:
            cursor.execute('CREATE VIRTUAL TABLE IF NOT EXISTS songs_fts USING fts5(title, artist, album, genre, content=songs, content_rowid=id)')
            cursor.execute('CREATE VIRTUAL TABLE IF NOT EXISTS lyrics_fts USING fts5(lyrics, content=lyrics, content_rowid=id)')
            cursor.execute('CREATE VIRTUAL TABLE IF NOT EXISTS song_fts USING fts5(id, title, artist, album, genre)')
            cursor.execute('CREATE VIRTUAL TABLE IF NOT EXISTS artist_fts USING fts5(id, name, bio, tags)')
            cursor.execute('CREATE VIRTUAL TABLE IF NOT EXISTS album_fts USING fts5(id, name, genre)')
        except Exception as e:
            # Las tablas FTS pueden fallar si ya existen, esto es normal
            pass
        
        # Crear índices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums(artist_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lyrics_track_id ON lyrics(track_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name)")



    def _verify_schema(self, cursor):
        """Verifica que el esquema de la base de datos es correcto y lo actualiza si es necesario."""
        
        # Verificar si las tablas existen primero
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {table[0] for table in cursor.fetchall()}
        
        # Si no existen las tablas principales, salir (ya se crearon en _create_tables)
        required_tables = {'artists', 'albums', 'songs', 'genres', 'lyrics', 'song_links'}
        if not required_tables.issubset(existing_tables):
            self.logger.info("Tablas principales creadas correctamente")
            return
        
        # Verificar origen en tabla artists
        cursor.execute("PRAGMA table_info(artists)")
        artist_columns = {col[1] for col in cursor.fetchall()}
        
        if 'origen' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN origen TEXT DEFAULT 'spotify'")
        if 'spotify_popularity' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN spotify_popularity INTEGER")
        if 'added_timestamp' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN added_timestamp TIMESTAMP")
        if 'added_day' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN added_day INTEGER")
        if 'added_week' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN added_week INTEGER")
        if 'added_month' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN added_month INTEGER")
        if 'added_year' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN added_year INTEGER")
        if 'website' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN website TEXT")
        if 'img' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN img TEXT")
        if 'img_urls' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN img_urls TEXT")
        if 'img_paths' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN img_paths TEXT")
        if 'jaangle_ready' not in artist_columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN jaangle_ready BOOLEAN DEFAULT 1")
        
        # Verificar origen en tabla albums
        cursor.execute("PRAGMA table_info(albums)")
        album_columns = {col[1] for col in cursor.fetchall()}
        
        if 'origen' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN origen TEXT DEFAULT 'spotify'")
        if 'added_timestamp' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN added_timestamp TIMESTAMP")
        if 'added_day' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN added_day INTEGER")
        if 'added_week' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN added_week INTEGER")
        if 'added_month' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN added_month INTEGER")
        if 'added_year' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN added_year INTEGER")
        if 'album_art_urls' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN album_art_urls TEXT")
        if 'musicbrainz_albumid' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN musicbrainz_albumid TEXT")
        if 'musicbrainz_albumartistid' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN musicbrainz_albumartistid TEXT")
        if 'musicbrainz_releasegroupid' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN musicbrainz_releasegroupid TEXT")
        if 'catalognumber' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN catalognumber TEXT")
        if 'media' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN media TEXT")
        if 'discnumber' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN discnumber TEXT")
        if 'releasecountry' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN releasecountry TEXT")
        if 'originalyear' not in album_columns:
            cursor.execute("ALTER TABLE albums ADD COLUMN originalyear INTEGER")
        
        # Verificar origen en tabla songs
        cursor.execute("PRAGMA table_info(songs)")
        song_columns = {col[1] for col in cursor.fetchall()}

        if 'origen' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN origen TEXT DEFAULT 'spotify'")
        if 'added_timestamp' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN added_timestamp TIMESTAMP")
        if 'added_day' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN added_day INTEGER")
        if 'added_week' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN added_week INTEGER")
        if 'added_month' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN added_month INTEGER")
        if 'added_year' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN added_year INTEGER")
        if 'reproducciones' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN reproducciones INTEGER DEFAULT 1")
        if 'fecha_reproducciones' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN fecha_reproducciones TEXT")
        if 'scrobbles_ids' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN scrobbles_ids TEXT")
        if 'musicbrainz_artistid' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN musicbrainz_artistid TEXT")
        if 'musicbrainz_recordingid' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN musicbrainz_recordingid TEXT")
        if 'musicbrainz_albumartistid' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN musicbrainz_albumartistid TEXT")
        if 'musicbrainz_releasegroupid' not in song_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN musicbrainz_releasegroupid TEXT")
        
        # Verificar origen en tabla genres
        cursor.execute("PRAGMA table_info(genres)")
        genre_columns = {col[1] for col in cursor.fetchall()}
        
        if 'origen' not in genre_columns:
            cursor.execute("ALTER TABLE genres ADD COLUMN origen TEXT")
        
        # Verificar song_links
        cursor.execute("PRAGMA table_info(song_links)")
        song_link_columns = {col[1] for col in cursor.fetchall()}
        
        if 'preview_url' not in song_link_columns:
            cursor.execute("ALTER TABLE song_links ADD COLUMN preview_url TEXT")
        if 'listenbrainz_preview_url' not in song_link_columns:
            cursor.execute("ALTER TABLE song_links ADD COLUMN listenbrainz_preview_url TEXT")
    def get_followed_artists(self):
        """
        Obtiene la lista de artistas seguidos por el usuario en Spotify.
        
        Returns:
            List[Dict]: Lista de diccionarios con información de los artistas
        """
        artists = []
        after = None
        
        while True:
            results = self.spotify.current_user_followed_artists(limit=50, after=after)
            items = results['artists']['items']
            
            if not items:
                break
                
            artists.extend(items)
            after = items[-1]['id']
            
            # Si el último after coincide con el anterior, hemos terminado
            if len(artists) >= results['artists']['total']:
                break
                
            time.sleep(0.5)  # Para no sobrecargar la API
        
        self.logger.info(f"Se encontraron {len(artists)} artistas seguidos en Spotify")
        return artists

    def get_saved_albums(self):
        """
        Obtiene la lista de álbumes guardados por el usuario en Spotify.
        
        Returns:
            List[Dict]: Lista de diccionarios con información de los álbumes
        """
        albums = []
        offset = 0
        limit = 50
        
        while True:
            results = self.spotify.current_user_saved_albums(limit=limit, offset=offset)
            items = results['items']
            
            if not items:
                break
                
            albums.extend(items)
            offset += limit
            
            if offset >= results['total']:
                break
                
            time.sleep(0.5)  # Para no sobrecargar la API
        
        self.logger.info(f"Se encontraron {len(albums)} álbumes guardados en Spotify")
        return albums

    def get_artist_albums(self, artist_id: str):
        """
        Obtiene todos los álbumes de un artista.
        
        Args:
            artist_id: ID de Spotify del artista
            
        Returns:
            List[Dict]: Lista de diccionarios con información de los álbumes
        """
        albums = []
        offset = 0
        limit = 50
        
        while True:
            try:
                results = self.spotify.artist_albums(
                    artist_id, 
                    album_type='album,single,compilation', 
                    limit=limit, 
                    offset=offset
                )
                
                items = results['items']
                if not items:
                    break
                    
                albums.extend(items)
                offset += limit
                
                if offset >= results['total']:
                    break
                    
                time.sleep(0.5)  # Para no sobrecargar la API
                
            except Exception as e:
                self.logger.error(f"Error al obtener álbumes para el artista {artist_id}: {str(e)}")
                break
        
        return albums

    def get_album_tracks(self, album_id: str):
        """
        Obtiene todas las pistas de un álbum.
        
        Args:
            album_id: ID de Spotify del álbum
            
        Returns:
            List[Dict]: Lista de diccionarios con información de las pistas
        """
        tracks = []
        offset = 0
        limit = 50
        
        while True:
            try:
                results = self.spotify.album_tracks(album_id, limit=limit, offset=offset)
                items = results['items']
                
                if not items:
                    break
                    
                tracks.extend(items)
                offset += limit
                
                if offset >= results['total']:
                    break
                    
                time.sleep(0.5)  # Para no sobrecargar la API
                
            except Exception as e:
                self.logger.error(f"Error al obtener pistas para el álbum {album_id}: {str(e)}")
                break
        
        return tracks

    def get_albums_from_saved_tracks(self):
        """
        Obtiene todos los álbumes de las pistas guardadas por el usuario.
        
        Returns:
            Set[str]: Conjunto de IDs de álbumes únicos
        """
        album_ids = set()
        offset = 0
        limit = 50
        
        while True:
            try:
                results = self.spotify.current_user_saved_tracks(limit=limit, offset=offset)
                items = results['items']
                
                if not items:
                    break
                
                # Extraer los IDs de álbumes
                for item in items:
                    if 'track' in item and 'album' in item['track'] and 'id' in item['track']['album']:
                        album_ids.add(item['track']['album']['id'])
                
                offset += limit
                
                if offset >= results['total']:
                    break
                    
                time.sleep(0.5)  # Para no sobrecargar la API
                
            except Exception as e:
                self.logger.error(f"Error al obtener pistas guardadas: {str(e)}")
                break
        
        self.logger.info(f"Se encontraron {len(album_ids)} álbumes únicos en las pistas guardadas")
        return album_ids

    def insert_artist(self, artist_data: Dict):
        """
        Inserta o actualiza un artista en la base de datos.
        
        Args:
            artist_data: Diccionario con datos del artista desde Spotify
            
        Returns:
            int: ID del artista en la base de datos o None si hay error
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Verificar si el artista ya existe y su origen
            cursor.execute("SELECT id, origen FROM artists WHERE name = ?", (artist_data['name'],))
            existing_artist = cursor.fetchone()
            
            # Si el artista ya existe y su origen es 'local' y estamos omitiendo artistas existentes
            if existing_artist and existing_artist[1] == 'local' and self.skip_existing_artists:
                self.logger.info(f"Omitiendo artista '{artist_data['name']}' ya que existe con origen 'local'")
                return existing_artist[0]
            
            # Preparar campos
            current_time = datetime.now()
            
            # Extraer géneros si están disponibles
            genres = ', '.join(artist_data.get('genres', [])) if artist_data.get('genres') else None
            
            # Obtener popularidad como un tag
            popularity = artist_data.get('popularity', 0)
            spotify_popularity = popularity
            
            # Si es una actualización
            if existing_artist:
                artist_id = existing_artist[0]
                
                # Solo actualizar si se fuerza la actualización o si el origen no es 'local'
                if self.force_update or existing_artist[1] != 'local':
                    cursor.execute('''
                        UPDATE artists SET 
                        spotify_url = ?, 
                        spotify_popularity = ?, 
                        last_updated = ?,
                        origen = ?
                        WHERE id = ?
                    ''', (
                        artist_data.get('external_urls', {}).get('spotify'),
                        spotify_popularity,
                        current_time,
                        f"spotify_{self.user_id}",
                        artist_id
                    ))
                    
                    self.logger.info(f"Actualizado artista '{artist_data['name']}' en la base de datos")
            else:
                # Insertar nuevo artista
                cursor.execute('''
                    INSERT INTO artists (
                        name, spotify_popularity, last_updated, spotify_url, origen,
                        added_timestamp, added_day, added_week, added_month, added_year
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    artist_data['name'],
                    spotify_popularity,
                    current_time,
                    artist_data.get('external_urls', {}).get('spotify'),
                    f"spotify_{self.user_id}",
                    current_time,
                    current_time.day,
                    int(current_time.strftime('%V')),
                    current_time.month,
                    current_time.year
                ))
                
                artist_id = cursor.lastrowid
                self.logger.info(f"Insertado nuevo artista '{artist_data['name']}' en la base de datos")
            
            # Insertar géneros en la tabla genres con origen
            if artist_data.get('genres'):
                origen_spotify = f"spotify_{self.user_id}"
                for genre in artist_data['genres']:
                    # Siempre insertar el género como nuevo registro con origen spotify
                    # No verificar duplicados por nombre, permitir múltiples entradas del mismo género con diferentes orígenes
                    cursor.execute('''
                        INSERT INTO genres (name, origen) VALUES (?, ?)
                    ''', (genre, origen_spotify))
            
            conn.commit()
            return artist_id
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error al insertar artista {artist_data.get('name', 'desconocido')}: {str(e)}")
            return None
        finally:
            conn.close()



    def insert_album(self, album_data: Dict, artist_id: int):
        """
        Inserta o actualiza un álbum en la base de datos.
        
        Args:
            album_data: Diccionario con datos del álbum desde Spotify
            artist_id: ID del artista en la base de datos
            
        Returns:
            int: ID del álbum en la base de datos
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Extraer año de la fecha de lanzamiento
            release_date = album_data.get('release_date', '')
            year = release_date[:4] if release_date else None
            
            # Obtener información del álbum para encontrar etiqueta discográfica
            album_id = album_data.get('id')
            label = None
            
            if album_id:
                try:
                    album_info = self.spotify.album(album_id)
                    if 'label' in album_info:
                        label = album_info['label']
                    time.sleep(0.2)  # Para no sobrecargar la API
                except Exception as e:
                    self.logger.warning(f"No se pudo obtener información completa del álbum {album_id}: {str(e)}")
            
            # Obtener géneros
            genres = ', '.join(album_data.get('genres', [])) if 'genres' in album_data else None
            
            # Verificar si el álbum ya existe
            cursor.execute("SELECT id, origen FROM albums WHERE artist_id = ? AND name = ?", (artist_id, album_data['name']))
            existing_album = cursor.fetchone()
            
            current_time = datetime.now()
            
            # URL de la imagen del álbum
            album_art_url = None
            if album_data.get('images') and len(album_data['images']) > 0:
                album_art_url = album_data['images'][0]['url']
            
            # Si el álbum ya existe
            if existing_album:
                album_id_db = existing_album[0]
                
                # Solo actualizar si se fuerza la actualización o si el origen no es 'local'
                if self.force_update or existing_album[1] != 'local':
                    cursor.execute('''
                        UPDATE albums SET 
                        year = ?, 
                        label = ?, 
                        genre = ?,
                        total_tracks = ?,
                        spotify_url = ?,
                        spotify_id = ?,
                        album_art_path = ?,
                        last_updated = ?,
                        origen = ?
                        WHERE id = ?
                    ''', (
                        year,
                        label,
                        genres,
                        album_data.get('total_tracks'),
                        album_data.get('external_urls', {}).get('spotify'),
                        album_data.get('id'),
                        album_art_url,
                        current_time,
                        f"spotify_{self.user_id}",
                        album_id_db
                    ))
                    
                    self.logger.info(f"Actualizado álbum '{album_data['name']}' en la base de datos")
            else:
                # Insertar nuevo álbum
                cursor.execute('''
                    INSERT INTO albums (
                        artist_id, name, year, label, genre, total_tracks,
                        spotify_url, spotify_id, album_art_path, last_updated, origen,
                        added_timestamp, added_day, added_week, added_month, added_year
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    artist_id,
                    album_data['name'],
                    year,
                    label,
                    genres,
                    album_data.get('total_tracks'),
                    album_data.get('external_urls', {}).get('spotify'),
                    album_data.get('id'),
                    album_art_url,
                    current_time,
                    f"spotify_{self.user_id}",
                    current_time,
                    current_time.day,
                    int(current_time.strftime('%V')),
                    current_time.month,
                    current_time.year
                ))
                
                album_id_db = cursor.lastrowid
                self.logger.info(f"Insertado nuevo álbum '{album_data['name']}' en la base de datos")
            
            conn.commit()
            return album_id_db
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error al insertar álbum {album_data.get('name', 'desconocido')}: {str(e)}")
            return None
        finally:
            conn.close()





               
    def run(self):
        """
        Ejecuta el proceso completo de extracción y actualización de la base de datos.
        
        Returns:
            Dict: Estadísticas del procesamiento
        """
        start_time = datetime.now()
        self.logger.info(f"Iniciando proceso en {start_time}")
        
        # Estadísticas
        stats = {
            "artists_followed": 0,
            "albums_from_artists": 0,
            "tracks_from_artists": 0,
            "albums_saved": 0,
            "tracks_from_saved_albums": 0,
            "albums_from_saved_tracks": 0,
            "tracks_from_saved_tracks_albums": 0
        }
        
        # 1. Procesar artistas seguidos
        self.logger.info("1. Procesando artistas seguidos...")
        followed_stats = self.process_followed_artists()
        stats["artists_followed"] = followed_stats["artists"]
        stats["albums_from_artists"] = followed_stats["albums"]
        stats["tracks_from_artists"] = followed_stats["tracks"]
        
        # 2. Procesar álbumes guardados
        self.logger.info("2. Procesando álbumes guardados...")
        saved_albums_stats = self.process_saved_albums()
        stats["albums_saved"] = saved_albums_stats["albums"]
        stats["tracks_from_saved_albums"] = saved_albums_stats["tracks"]
        
        # 3. Procesar álbumes de pistas guardadas
        self.logger.info("3. Procesando álbumes de pistas guardadas...")
        saved_tracks_albums_stats = self.process_saved_tracks_albums()
        stats["albums_from_saved_tracks"] = saved_tracks_albums_stats["albums"]
        stats["tracks_from_saved_tracks_albums"] = saved_tracks_albums_stats["tracks"]
        
        # Resumen
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60.0  # en minutos
        
        self.logger.info(f"""
        ==========================================
        RESUMEN DE EJECUCIÓN - DB_MUSICA_SPOTIFY
        ==========================================
        Tiempo de ejecución: {duration:.2f} minutos
        
        Artistas seguidos procesados: {stats['artists_followed']}
        Álbumes de artistas procesados: {stats['albums_from_artists']}
        Pistas de artistas procesadas: {stats['tracks_from_artists']}
        
        Álbumes guardados procesados: {stats['albums_saved']}
        Pistas de álbumes guardados procesadas: {stats['tracks_from_saved_albums']}
        
        Álbumes de pistas guardadas procesados: {stats['albums_from_saved_tracks']}
        Pistas de esos álbumes procesadas: {stats['tracks_from_saved_tracks_albums']}
        
        Total de pistas procesadas: {stats['tracks_from_artists'] + stats['tracks_from_saved_albums'] + stats['tracks_from_saved_tracks_albums']}
        ==========================================
        """)
        
        return stats
        
    def insert_track(self, track_data: Dict, album_name: str, album_artist: str):
        """
        Inserta o actualiza una pista en la base de datos.
        
        Args:
            track_data: Diccionario con datos de la pista desde Spotify
            album_name: Nombre del álbum al que pertenece la pista
            album_artist: Nombre del artista principal del álbum
            
        Returns:
            int: ID de la pista en la base de datos o None si ocurre un error
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Extraer artista principal de la pista
            artist_name = track_data['artists'][0]['name'] if track_data.get('artists') else album_artist
            
            # Verificar si la pista ya existe
            cursor.execute('''
                SELECT s.id, s.origen, sl.id 
                FROM songs s 
                LEFT JOIN song_links sl ON s.id = sl.song_id
                WHERE s.title = ? AND s.artist = ? AND s.album = ?
            ''', (track_data['name'], artist_name, album_name))
            
            existing_track = cursor.fetchone()
            
            current_time = datetime.now()
            
            # Obtener duración de la pista en segundos
            duration = track_data.get('duration_ms', 0) / 1000.0 if track_data.get('duration_ms') else None
            
            # Si la pista ya existe
            if existing_track:
                track_id = existing_track[0]
                song_link_id = existing_track[2]
                
                # Solo actualizar si se fuerza la actualización o si el origen no es 'local'
                if self.force_update or existing_track[1] != 'local':
                    cursor.execute('''
                        UPDATE songs SET 
                        track_number = ?, 
                        album_artist = ?,
                        duration = ?,
                        origen = ?,
                        last_modified = ?
                        WHERE id = ?
                    ''', (
                        track_data.get('track_number'),
                        album_artist,
                        duration,
                        f"spotify_{self.user_id}",
                        current_time,
                        track_id
                    ))
                    
                    # Actualizar o insertar enlaces
                    spotify_url = track_data.get('external_urls', {}).get('spotify')
                    spotify_id = track_data.get('id')
                    
                    if song_link_id:
                        cursor.execute('''
                            UPDATE song_links SET 
                            spotify_url = ?, 
                            spotify_id = ?,
                            links_updated = ?
                            WHERE id = ?
                        ''', (
                            spotify_url,
                            spotify_id,
                            current_time,
                            song_link_id
                        ))
                    else:
                        cursor.execute('''
                            INSERT INTO song_links (
                                song_id, spotify_url, spotify_id, links_updated
                            ) VALUES (?, ?, ?, ?)
                        ''', (
                            track_id,
                            spotify_url,
                            spotify_id,
                            current_time
                        ))
                    
                    self.logger.info(f"Actualizada pista '{track_data['name']}' en la base de datos")
            else:
                # Insertar nueva pista
                cursor.execute('''
                    INSERT INTO songs (
                        title, track_number, artist, album_artist, album,
                        duration, added_timestamp, added_day, added_week, added_month, added_year,
                        last_modified, origen
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    track_data['name'],
                    track_data.get('track_number'),
                    artist_name,
                    album_artist,
                    album_name,
                    duration,
                    current_time,
                    current_time.day,
                    int(current_time.strftime('%V')),
                    current_time.month,
                    current_time.year,
                    current_time,
                    f"spotify_{self.user_id}"
                ))
                
                track_id = cursor.lastrowid
                
                # Insertar enlaces
                spotify_url = track_data.get('external_urls', {}).get('spotify')
                spotify_id = track_data.get('id')
                
                cursor.execute('''
                    INSERT INTO song_links (
                        song_id, spotify_url, spotify_id, links_updated
                    ) VALUES (?, ?, ?, ?)
                ''', (
                    track_id,
                    spotify_url,
                    spotify_id,
                    current_time
                ))
                
                self.logger.info(f"Insertada nueva pista '{track_data['name']}' en la base de datos")
            
            conn.commit()
            return track_id
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error al insertar pista {track_data.get('name', 'desconocido')}: {str(e)}")
            return None
        finally:
            conn.close()


      
    def process_artist(self, artist_data: Dict):
        """
        Procesa un artista, sus álbumes y pistas e inserta/actualiza en la base de datos.
        
        Args:
            artist_data: Datos del artista desde Spotify
            
        Returns:
            Tuple[int, int, int]: Número de álbumes y pistas procesadas
        """
        try:
            # Insertar o actualizar artista
            artist_id = self.insert_artist(artist_data)
            
            if not artist_id:
                return 0, 0
                
            # Si el artista ya existía con origen 'local' y estamos omitiendo artistas existentes, saltar
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT origen FROM artists WHERE id = ?", (artist_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] == 'local' and self.skip_existing_artists:
                return 0, 0
                
            # Obtener álbumes del artista
            albums = self.get_artist_albums(artist_data['id'])
            
            processed_albums = 0
            processed_tracks = 0
            
            for album in albums:
                try:
                    album_id_db = self.insert_album(album, artist_id)
                    
                    if album_id_db:
                        processed_albums += 1
                        
                        # Procesar pistas del álbum
                        album_tracks = self.process_album_tracks(album['id'], album_id_db, album, artist_data['name'])
                        processed_tracks += album_tracks
                        
                except Exception as e:
                    self.logger.error(f"Error al procesar álbum {album.get('name', 'desconocido')}: {str(e)}")
                    continue
                    
            return processed_albums, processed_tracks
                
        except Exception as e:
            self.logger.error(f"Error al procesar artista {artist_data.get('name', 'desconocido')}: {str(e)}")
            return 0, 0
    
    def process_followed_artists(self):
        """
        Procesa todos los artistas seguidos por el usuario en Spotify.
        
        Returns:
            Dict: Estadísticas del procesamiento
        """
        artists = self.get_followed_artists()
        
        if not artists:
            self.logger.warning("No se encontraron artistas seguidos en Spotify")
            return {"artists": 0, "albums": 0, "tracks": 0}
            
        total_artists = len(artists)
        total_albums = 0
        total_tracks = 0
        
        for i, artist in enumerate(artists, 1):
            self.logger.info(f"Procesando artista {i}/{total_artists}: {artist['name']}")
            
            albums, tracks = self.process_artist(artist)
            total_albums += albums
            total_tracks += tracks
            
            # Pausa para no sobrecargar la API
            time.sleep(0.5)
            
        stats = {
            "artists": total_artists,
            "albums": total_albums,
            "tracks": total_tracks
        }
        
        self.logger.info(f"Estadísticas finales: {stats}")
        return stats
    
    def process_saved_albums(self):
        """
        Procesa todos los álbumes guardados por el usuario en Spotify.
        
        Returns:
            Dict: Estadísticas del procesamiento
        """
        saved_albums = self.get_saved_albums()
        
        if not saved_albums:
            self.logger.warning("No se encontraron álbumes guardados en Spotify")
            return {"albums": 0, "tracks": 0}
            
        total_albums = 0
        total_tracks = 0
        
        for i, item in enumerate(saved_albums, 1):
            album = item['album']
            album_artist = album['artists'][0]['name'] if album.get('artists') else "Desconocido"
            
            self.logger.info(f"Procesando álbum guardado {i}/{len(saved_albums)}: {album['name']} de {album_artist}")
            
            try:
                # Obtener o insertar el artista primero
                artist_data = self.spotify.artist(album['artists'][0]['id']) if album.get('artists') else None
                
                if artist_data:
                    artist_id = self.insert_artist(artist_data)
                    
                    if artist_id:
                        # Insertar o actualizar el álbum
                        album_id_db = self.insert_album(album, artist_id)
                        
                        if album_id_db:
                            total_albums += 1
                            
                            # Procesar pistas del álbum
                            album_tracks = self.process_album_tracks(album['id'], album_id_db, album, album_artist)
                            total_tracks += album_tracks
                
            except Exception as e:
                self.logger.error(f"Error al procesar álbum guardado {album.get('name', 'desconocido')}: {str(e)}")
                continue
                
            # Pausa para no sobrecargar la API
            time.sleep(0.5)
            
        stats = {
            "albums": total_albums,
            "tracks": total_tracks
        }
        
        self.logger.info(f"Estadísticas de álbumes guardados: {stats}")
        return stats
    
    def process_saved_tracks_albums(self):
        """
        Procesa los álbumes de las pistas guardadas por el usuario en Spotify.
        
        Returns:
            Dict: Estadísticas del procesamiento
        """
        album_ids = self.get_albums_from_saved_tracks()
        
        if not album_ids:
            self.logger.warning("No se encontraron álbumes en las pistas guardadas")
            return {"albums": 0, "tracks": 0}
            
        total_albums = 0
        total_tracks = 0
        
        for i, album_id in enumerate(album_ids, 1):
            self.logger.info(f"Procesando álbum de pistas guardadas {i}/{len(album_ids)}")
            
            try:
                # Obtener datos del álbum
                album = self.spotify.album(album_id)
                album_artist = album['artists'][0]['name'] if album.get('artists') else "Desconocido"
                
                # Obtener o insertar el artista primero
                artist_data = self.spotify.artist(album['artists'][0]['id']) if album.get('artists') else None
                
                if artist_data:
                    artist_id = self.insert_artist(artist_data)
                    
                    if artist_id:
                        # Insertar o actualizar el álbum
                        album_id_db = self.insert_album(album, artist_id)
                        
                        if album_id_db:
                            total_albums += 1
                            
                            # Procesar pistas del álbum
                            album_tracks = self.process_album_tracks(album['id'], album_id_db, album, album_artist)
                            total_tracks += album_tracks
                
            except Exception as e:
                self.logger.error(f"Error al procesar álbum de pistas guardadas {album_id}: {str(e)}")
                continue
                
            # Pausa para no sobrecargar la API
            time.sleep(0.5)
            
        stats = {
            "albums": total_albums,
            "tracks": total_tracks
        }
        
        self.logger.info(f"Estadísticas de álbumes de pistas guardadas: {stats}")
        return stats


    def process_album_tracks(self, album_id_spotify: str, album_id_db: int, album_data: Dict, artist_name: str):
        """
        Procesa las pistas de un álbum e inserta/actualiza en la base de datos.
        
        Args:
            album_id_spotify: ID de Spotify del álbum
            album_id_db: ID del álbum en la base de datos
            album_data: Datos del álbum
            artist_name: Nombre del artista principal
            
        Returns:
            int: Número de pistas procesadas
        """
        # Obtener las pistas del álbum
        tracks = self.get_album_tracks(album_id_spotify)
        
        if not tracks:
            self.logger.warning(f"No se encontraron pistas para el álbum {album_data['name']}")
            return 0
            
        processed_tracks = 0
        
        for track in tracks:
            try:
                track_id = self.insert_track(track, album_data['name'], artist_name)
                if track_id:
                    processed_tracks += 1
            except Exception as e:
                self.logger.error(f"Error al procesar pista {track.get('name', 'desconocida')}: {str(e)}")
                continue
                
        return processed_tracks


def main(config=None):
    """
    Función principal para ejecutar el script.
    
    Args:
        config: Diccionario de configuración (opcional)
        
    Returns:
        int: Código de salida
    """
    # Si no se proporcionó configuración, parsear argumentos de línea de comandos
    if config is None:
        parser = argparse.ArgumentParser(description='Crear base de datos de música desde Spotify')
        parser.add_argument('--db-path', help='Ruta a la base de datos SQLite')
        parser.add_argument('--spotify-client-id', help='ID de cliente de Spotify')
        parser.add_argument('--spotify-client-secret', help='Secreto de cliente de Spotify')
        parser.add_argument('--spotify-redirect-uri', help='URI de redirección para autenticación de Spotify')
        parser.add_argument('--spotify-cache-path', help='Ruta para almacenar el token de Spotify')
        parser.add_argument('--force-update', action='store_true', 
                          help='Forzar actualización de datos existentes')
        parser.add_argument('--no-skip-existing', action='store_true', 
                          help='No omitir artistas existentes con origen "local"')
        parser.add_argument('--user-id', help='ID de usuario de Spotify (opcional)')
        parser.add_argument('--config', help='Archivo de configuración JSON')
        args = parser.parse_args()
        
        # Si se proporcionó un archivo de configuración, cargarlo
        if args.config:
            try:
                with open(args.config, 'r') as f:
                    file_config = json.load(f)
                    
                # Combinar configuraciones
                config = {}
                # Primero cargar configuración global si existe
                config.update(file_config.get('common', {}))
                # Luego cargar configuración específica de este script
                config.update(file_config.get('db_musica_spotify', {}))
                
            except Exception as e:
                print(f"Error al cargar archivo de configuración: {e}")
                return 1
        else:
            # Usar argumentos de línea de comandos
            config = vars(args)
    
    # Comprobar que tenemos la ruta de la base de datos
    if 'db_path' not in config or not config['db_path']:
        print("Error: No se especificó la ruta de la base de datos")
        return 1
    
    # Inicializar el gestor
    manager = MusicSpotifyManager(
        db_path=config['db_path'],
        spotify_client_id=config.get('spotify_client_id'),
        spotify_client_secret=config.get('spotify_client_secret'),
        spotify_redirect_uri=config.get('spotify_redirect_uri'),
        spotify_cache_path=config.get('spotify_cache_path'),
        force_update=config.get('force_update', False),
        skip_existing_artists=not config.get('no_skip_existing', False),
        user_id=config.get('user_id')
    )
    
    # Verificar que el cliente de Spotify se inicializó correctamente
    if not hasattr(manager, 'spotify') or manager.spotify is None:
        print("Error: No se pudo inicializar el cliente de Spotify. Revisa las credenciales y la conexión.")
        return 1
    
    # Ejecutar el proceso
    try:
        manager.run()
        return 0
    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())