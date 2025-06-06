
#!/usr/bin/env python
#
# Nombre:: db_musica_path.py
# Descripción: Lee una ruta, extrae información de canciones y las guarda en una base de datos.
# Autor: volteret4
# Repositorio: https://github.com/volteret4/
# Notes: Es el primero de una colección de scripts para gestionar una base de datos de canciones:
#
#                   - db_musica_path.py: Lee una ruta, extrae información de canciones y las guarda en una base de datos.
#                   - enlaces_artista_album.py: Lee la base de datos  y busca enlaces a servicios externos para arista y album(Spotify, Lastfm, YouTube, MusicBrainz, Discogs, RateYourMusic).
#                   - enlaces_canciones_spotify_lastfm.py: Lee la base de datos  y busca enlaces a servicios externos para canciones(Spotify, Lastfm, Bandcamp, YouTube, MusicBrainz, Discogs, RateYourMusic).
#                   - letras_genius_db_musica.py: Lee la base de datos creada por db_musica.py y busca las letras de las canciones en Genius,añadiéndolas a la base de datos.
#                   - wikilinks_desde_mb.py: Lee la base de datos creada por db_musica.py y busca info de wikipedia para base de datos de la biblioteca de musica y añade los confirmados.
#                   - scrobbles_lastfm.py: Lee las base de datos y obtiene los scrobbles de lastfm. Guarda también el último scrobble.
#                   - scrobbles_listenbrainz: Idem que el anterior, pero con listenbrainz
#                   - optimiza_db_lastpass.py: Lee la base de datos y optimiza el esquema para mejorar el rendimiento
#
#   Dependencias:   - python3, mutagen, pylast, sqlite3
#                   - carpeta con musica en flac, m4a, mp3
#   Ha tardado 43 minutos para una carpeta en NFS con 84 GB, 600 carpetas con 

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
import sqlite3
from datetime import datetime, timedelta
import argparse

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import PROJECT_ROOT


class MusicLibraryManager:
    def __init__(self, root_path: str, db_path: str):
        self.root_path = Path(root_path).resolve()
        self.db_path = Path(db_path).resolve()
        self.supported_formats = ('.mp3', '.flac', '.m4a')
        
        # Logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Crear el directorio padre de la base de datos si no existe
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database - asegúrate de que esto se ejecute
        self.init_database()
        
        # Verifica que las tablas necesarias existan
        self._verify_tables_exist()






    def init_database(self, create_indices=False):
        """Initialize SQLite database with comprehensive tables and optionally create indices."""
        
        # Crear el directorio si no existe
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Verificar si el archivo de base de datos existe
        db_exists = self.db_path.exists()
        
        if not db_exists:
            self.logger.info(f"Creando nueva base de datos en: {self.db_path}")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Habilitar claves foráneas
        c.execute("PRAGMA foreign_keys = ON")
        
        # Check for existing tables solo si la DB ya existía
        existing_tables = []
        if db_exists:
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [table[0] for table in c.fetchall()]
        
        # Songs table - crear siempre si no existe
        if 'songs' not in existing_tables:
            self.logger.info("Creando tabla 'songs'...")
            c.execute('''
                CREATE TABLE songs (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT UNIQUE,
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
                    added_day INTEGER,
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
                    origen TEXT DEFAULT 'local',
                    musicbrainz_artistid TEXT,
                    musicbrainz_recordingid TEXT,
                    musicbrainz_albumartistid TEXT,
                    musicbrainz_releasegroupid TEXT
                )
            ''')
        else:
            # Verificar y añadir columnas faltantes
            self._add_missing_columns_to_songs(c)
        
        # Artists table - crear siempre si no existe
        if 'artists' not in existing_tables:
            self.logger.info("Creando tabla 'artists'...")
            c.execute('''
                CREATE TABLE artists (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
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
                    added_timestamp TIMESTAMP,
                    added_day INTEGER,
                    added_week INTEGER,
                    added_month INTEGER,
                    added_year INTEGER,
                    origen TEXT DEFAULT 'local',
                    aliases TEXT,
                    member_of TEXT
                )
            ''')
        else:
            # Verificar y añadir columnas faltantes
            self._add_missing_columns_to_artists(c)
        
        # Albums table - crear siempre si no existe
        if 'albums' not in existing_tables:
            self.logger.info("Creando tabla 'albums'...")
            c.execute('''
                CREATE TABLE albums (
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
                    added_timestamp TIMESTAMP,
                    added_day INTEGER,
                    added_week INTEGER,
                    added_month INTEGER,
                    added_year INTEGER,
                    origen TEXT DEFAULT 'local',
                    musicbrainz_albumid TEXT,
                    musicbrainz_albumartistid TEXT,
                    musicbrainz_releasegroupid TEXT,
                    catalognumber TEXT,
                    media TEXT,
                    discnumber TEXT,
                    releasecountry TEXT,
                    originalyear INTEGER,
                    producers TEXT,
                    engineers TEXT,
                    mastering_engineers TEXT,
                    credits TEXT,
                    FOREIGN KEY(artist_id) REFERENCES artists(id),
                    UNIQUE(artist_id, name)
                )
            ''')
        else:
            # Verificar y añadir columnas faltantes
            self._add_missing_columns_to_albums(c)
            
        # Genres table
        if 'genres' not in existing_tables:
            self.logger.info("Creando tabla 'genres'...")
            c.execute('''
                CREATE TABLE genres (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    description TEXT,
                    related_genres TEXT,
                    origin_year INTEGER
                )
            ''')
        
        # Lyrics table
        if 'lyrics' not in existing_tables:
            self.logger.info("Creando tabla 'lyrics'...")
            c.execute('''
                CREATE TABLE lyrics (
                    id INTEGER PRIMARY KEY,
                    track_id INTEGER,
                    lyrics TEXT,
                    source TEXT DEFAULT 'Genius',
                    last_updated TIMESTAMP,
                    FOREIGN KEY(track_id) REFERENCES songs(id)
                )
            ''')
            
        # Song Links table
        if 'song_links' not in existing_tables:
            self.logger.info("Creando tabla 'song_links'...")
            c.execute('''
                CREATE TABLE song_links (
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
                    FOREIGN KEY(song_id) REFERENCES songs(id)
                )
            ''')
        else:
            # Verificar y añadir columnas faltantes
            self._add_missing_columns_to_song_links(c)
        
        # Create FTS tables if they don't exist
        self._create_fts_tables(c, existing_tables)
        
        # Create indices if requested or if it's a new database
        if create_indices or not db_exists:
            self._create_basic_indices(c)
        
        conn.commit()
        conn.close()
        
        if not db_exists:
            self.logger.info("Base de datos creada exitosamente")

    def _add_missing_columns_to_songs(self, cursor):
        """Añadir columnas faltantes a la tabla songs"""
        cursor.execute("PRAGMA table_info(songs)")
        columns = {col[1] for col in cursor.fetchall()}
        
        # Lista de todas las columnas que deberían existir
        required_columns = {
            'added_timestamp': 'TIMESTAMP',
            'added_day': 'INTEGER',
            'added_week': 'INTEGER', 
            'added_month': 'INTEGER',
            'added_year': 'INTEGER',
            'duration': 'REAL',
            'lyrics_id': 'INTEGER',
            'replay_gain_track_gain': 'REAL',
            'replay_gain_track_peak': 'REAL',
            'replay_gain_album_gain': 'REAL',
            'replay_gain_album_peak': 'REAL',
            'album_art_path_denorm': 'TEXT',
            'has_lyrics': 'INTEGER DEFAULT 0',
            'origen': 'TEXT DEFAULT "local"',
            'musicbrainz_artistid': 'TEXT',
            'musicbrainz_recordingid': 'TEXT',
            'musicbrainz_albumartistid': 'TEXT',
            'musicbrainz_releasegroupid': 'TEXT'
        }
        
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE songs ADD COLUMN {col_name} {col_type}")
                    self.logger.info(f"Añadida columna '{col_name}' a tabla songs")
                except sqlite3.OperationalError as e:
                    self.logger.warning(f"No se pudo añadir columna {col_name}: {e}")

    def _add_missing_columns_to_artists(self, cursor):
        """Añadir columnas faltantes a la tabla artists"""
        cursor.execute("PRAGMA table_info(artists)")
        columns = {col[1] for col in cursor.fetchall()}
        
        required_columns = {
            'spotify_url': 'TEXT',
            'youtube_url': 'TEXT',
            'musicbrainz_url': 'TEXT',
            'discogs_url': 'TEXT',
            'rateyourmusic_url': 'TEXT',
            'links_updated': 'TIMESTAMP',
            'wikipedia_url': 'TEXT',
            'wikipedia_content': 'TEXT',
            'wikipedia_updated': 'TIMESTAMP',
            'mbid': 'TEXT',
            'aliases': 'TEXT',
            'member_of': 'TEXT',
            'added_timestamp': 'TIMESTAMP',
            'added_day': 'INTEGER',
            'added_week': 'INTEGER',
            'added_month': 'INTEGER',
            'added_year': 'INTEGER',
            'origen': 'TEXT DEFAULT "local"'
        }
        
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE artists ADD COLUMN {col_name} {col_type}")
                    self.logger.info(f"Añadida columna '{col_name}' a tabla artists")
                except sqlite3.OperationalError as e:
                    self.logger.warning(f"No se pudo añadir columna {col_name}: {e}")

    def _add_missing_columns_to_albums(self, cursor):
        """Añadir columnas faltantes a la tabla albums"""
        cursor.execute("PRAGMA table_info(albums)")
        columns = {col[1] for col in cursor.fetchall()}
        
        required_columns = {
            'spotify_url': 'TEXT',
            'spotify_id': 'TEXT',
            'youtube_url': 'TEXT',
            'musicbrainz_url': 'TEXT',
            'discogs_url': 'TEXT',
            'rateyourmusic_url': 'TEXT',
            'links_updated': 'TIMESTAMP',
            'wikipedia_url': 'TEXT',
            'wikipedia_content': 'TEXT',
            'wikipedia_updated': 'TIMESTAMP',
            'mbid': 'TEXT',
            'folder_path': 'TEXT',
            'bitrate_range': 'TEXT',
            'producers': 'TEXT',
            'engineers': 'TEXT',
            'mastering_engineers': 'TEXT',
            'credits': 'TEXT',
            'added_timestamp': 'TIMESTAMP',
            'added_day': 'INTEGER',
            'added_week': 'INTEGER',
            'added_month': 'INTEGER',
            'added_year': 'INTEGER',
            'origen': 'TEXT DEFAULT "local"',
            'musicbrainz_albumid': 'TEXT',
            'musicbrainz_albumartistid': 'TEXT',
            'musicbrainz_releasegroupid': 'TEXT',
            'catalognumber': 'TEXT',
            'media': 'TEXT',
            'discnumber': 'TEXT',
            'releasecountry': 'TEXT',
            'originalyear': 'INTEGER'
        }
        
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE albums ADD COLUMN {col_name} {col_type}")
                    self.logger.info(f"Añadida columna '{col_name}' a tabla albums")
                except sqlite3.OperationalError as e:
                    self.logger.warning(f"No se pudo añadir columna {col_name}: {e}")

    def _add_missing_columns_to_song_links(self, cursor):
        """Añadir columnas faltantes a la tabla song_links"""
        cursor.execute("PRAGMA table_info(song_links)")
        columns = {col[1] for col in cursor.fetchall()}
        
        required_columns = {
            'spotify_url': 'TEXT',
            'spotify_id': 'TEXT',
            'lastfm_url': 'TEXT',
            'links_updated': 'TIMESTAMP',
            'youtube_url': 'TEXT',
            'musicbrainz_url': 'TEXT',
            'musicbrainz_recording_id': 'TEXT',
            'bandcamp_url': 'TEXT',
            'soundcloud_url': 'TEXT',
            'boomkat_url': 'TEXT'
        }
        
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE song_links ADD COLUMN {col_name} {col_type}")
                    self.logger.info(f"Añadida columna '{col_name}' a tabla song_links")
                except sqlite3.OperationalError as e:
                    self.logger.warning(f"No se pudo añadir columna {col_name}: {e}")

    def _create_fts_tables(self, cursor, existing_tables):
        """Crear tablas FTS si no existen"""
        if 'songs_fts' not in existing_tables:
            cursor.execute('''
                CREATE VIRTUAL TABLE songs_fts USING fts5(
                    title, artist, album, genre,
                    content=songs, content_rowid=id
                )
            ''')
        
        if 'lyrics_fts' not in existing_tables:
            cursor.execute('''
                CREATE VIRTUAL TABLE lyrics_fts USING fts5(
                    lyrics,
                    content=lyrics, content_rowid=id
                )
            ''')
        
        if 'song_fts' not in existing_tables:
            cursor.execute('''
                CREATE VIRTUAL TABLE song_fts USING fts5(
                    id, title, artist, album, genre
                )
            ''')
        
        if 'artist_fts' not in existing_tables:
            cursor.execute('''
                CREATE VIRTUAL TABLE artist_fts USING fts5(
                    id, name, bio, tags
                )
            ''')
        
        if 'album_fts' not in existing_tables:
            cursor.execute('''
                CREATE VIRTUAL TABLE album_fts USING fts5(
                    id, name, genre
                )
            ''')

    def _create_basic_indices(self, cursor):
        """Crear índices básicos necesarios"""
        basic_indices = [
            "CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist)",
            "CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album)",
            "CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre)",
            "CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums(artist_id)",
            "CREATE INDEX IF NOT EXISTS idx_lyrics_track_id ON lyrics(track_id)",
            "CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)",
            "CREATE INDEX IF NOT EXISTS idx_songs_file_path ON songs(file_path)",
            "CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name)",
            "CREATE INDEX IF NOT EXISTS idx_albums_name ON albums(name)"
        ]
        
        for index_query in basic_indices:
            try:
                cursor.execute(index_query)
            except sqlite3.OperationalError as e:
                self.logger.warning(f"No se pudo crear índice: {e}")

    def _verify_tables_exist(self):
        """Verifica que todas las tablas necesarias existen, y las crea si no."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        required_tables = ['songs', 'artists', 'albums', 'genres', 'lyrics', 'song_links']
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [table[0] for table in c.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            self.logger.warning(f"Tablas faltantes detectadas: {missing_tables}. Reinicializando base de datos.")
            conn.close()
            self.init_database(create_indices=True)
        else:
            conn.close()
            self.logger.info("Todas las tablas necesarias están presentes")
            

    def create_indices(self):
        """Crea índices optimizados para mejorar el rendimiento de consultas."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            self.logger.info("Creando índices para optimizar la base de datos...")
            
            # 1. Índices para campos MusicBrainz en songs
            indices_musicbrainz_songs = [
                "CREATE INDEX IF NOT EXISTS idx_songs_mbid ON songs(mbid)",
                "CREATE INDEX IF NOT EXISTS idx_songs_musicbrainz_artistid ON songs(musicbrainz_artistid)",
                "CREATE INDEX IF NOT EXISTS idx_songs_musicbrainz_recordingid ON songs(musicbrainz_recordingid)",
                "CREATE INDEX IF NOT EXISTS idx_songs_musicbrainz_albumartistid ON songs(musicbrainz_albumartistid)",
                "CREATE INDEX IF NOT EXISTS idx_songs_musicbrainz_releasegroupid ON songs(musicbrainz_releasegroupid)"
            ]
            
            # 2. Índices para campos MusicBrainz en albums
            indices_musicbrainz_albums = [
                "CREATE INDEX IF NOT EXISTS idx_albums_mbid ON albums(mbid)",
                "CREATE INDEX IF NOT EXISTS idx_albums_musicbrainz_albumid ON albums(musicbrainz_albumid)",
                "CREATE INDEX IF NOT EXISTS idx_albums_musicbrainz_albumartistid ON albums(musicbrainz_albumartistid)",
                "CREATE INDEX IF NOT EXISTS idx_albums_musicbrainz_releasegroupid ON albums(musicbrainz_releasegroupid)",
                "CREATE INDEX IF NOT EXISTS idx_albums_catalognumber ON albums(catalognumber)",
                "CREATE INDEX IF NOT EXISTS idx_albums_originalyear ON albums(originalyear)",
                "CREATE INDEX IF NOT EXISTS idx_albums_releasecountry ON albums(releasecountry)"
            ]
            
            # 3. Índices para campos MusicBrainz en artists
            indices_musicbrainz_artists = [
                "CREATE INDEX IF NOT EXISTS idx_artists_mbid ON artists(mbid)"
            ]
            
            # 4. Índices compuestos para búsquedas comunes con campos MusicBrainz
            indices_compuestos_musicbrainz = [
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_mb_id ON songs(artist, musicbrainz_artistid)",
                "CREATE INDEX IF NOT EXISTS idx_albums_artist_mb_id ON albums(name, musicbrainz_albumid)",
                "CREATE INDEX IF NOT EXISTS idx_albums_year_country ON albums(year, releasecountry)"
            ]
            
            # Añadir a los índices existentes
            indices_generales = [
                "CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title)",
                "CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist)",
                "CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album)",
                "CREATE INDEX IF NOT EXISTS idx_songs_album_artist ON songs(album_artist)",
                "CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre)",
                "CREATE INDEX IF NOT EXISTS idx_songs_added_timestamp ON songs(added_timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_songs_track_number ON songs(track_number)",
                "CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name)",
                "CREATE INDEX IF NOT EXISTS idx_albums_name ON albums(name)",
                "CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums(artist_id)",
                "CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)",
                "CREATE INDEX IF NOT EXISTS idx_albums_year ON albums(year)"
            ]
            
            indices_case_insensitive = [
                "CREATE INDEX IF NOT EXISTS idx_songs_title_lower ON songs(LOWER(title))",
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_lower ON songs(LOWER(artist))",
                "CREATE INDEX IF NOT EXISTS idx_songs_album_lower ON songs(LOWER(album))",
                "CREATE INDEX IF NOT EXISTS idx_artists_name_lower ON artists(LOWER(name))",
                "CREATE INDEX IF NOT EXISTS idx_albums_name_lower ON albums(LOWER(name))",
                "CREATE INDEX IF NOT EXISTS idx_albums_label_lower ON albums(LOWER(label))",
                "CREATE INDEX IF NOT EXISTS idx_albums_genre_lower ON albums(LOWER(genre))"
            ]
            
            indices_compuestos = [
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_album ON songs(artist, album)",
                "CREATE INDEX IF NOT EXISTS idx_songs_album_title ON songs(album, title)",
                "CREATE INDEX IF NOT EXISTS idx_songs_album_track ON songs(album, track_number)",
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_title ON songs(artist, title)",
                "CREATE INDEX IF NOT EXISTS idx_songs_date_added ON songs(added_year, added_month, added_week)"
            ]
            
            # Crear todos los índices combinados
            indices_totales = (
                indices_generales + 
                indices_case_insensitive + 
                indices_compuestos + 
                indices_musicbrainz_songs + 
                indices_musicbrainz_albums + 
                indices_musicbrainz_artists + 
                indices_compuestos_musicbrainz
            )
            
            for index_query in indices_totales:
                try:
                    c.execute(index_query)
                    conn.commit()
                except sqlite3.OperationalError as e:
                    self.logger.warning(f"Índice no creado: {e}")

            # Enable foreign keys
            try:
                c.execute("PRAGMA foreign_keys = ON")
                self.logger.info("Foreign keys enabled for future operations")
            except sqlite3.OperationalError as e:
                self.logger.warning(f"Could not enable foreign keys: {e}")
                
            self.logger.info("Creación de índices completada")
        
        except Exception as e:
            self.logger.error(f"Error al crear índices: {str(e)}")
        
        finally:
            conn.close()


    def optimize_database(self):
        """Aplica configuraciones de rendimiento a la base de datos SQLite."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            self.logger.info("Aplicando optimizaciones a la base de datos...")
            
            # Configuraciones de rendimiento
            pragmas = [
                "PRAGMA journal_mode = WAL",  # Write-Ahead Logging para mejor concurrencia
                "PRAGMA synchronous = NORMAL", # Balance entre rendimiento y seguridad
                "PRAGMA cache_size = -8000",   # Usar aproximadamente 8MB de caché (valor negativo para KB)
                "PRAGMA temp_store = MEMORY",  # Almacenar tablas temporales en memoria
                "PRAGMA foreign_keys = ON"     # Habilitar claves foráneas
            ]
            
            for pragma in pragmas:
                c.execute(pragma)
                
            # Verificar que se aplicó el modo WAL
            c.execute("PRAGMA journal_mode")
            journal_mode = c.fetchone()[0]
            self.logger.info(f"Modo de journal establecido a: {journal_mode}")
            
            # Ejecutar VACUUM para compactar la base de datos
            c.execute("VACUUM")
            
            self.logger.info("Optimizaciones de la base de datos aplicadas correctamente")
        
        except Exception as e:
            self.logger.error(f"Error al optimizar la base de datos: {str(e)}")
        
        finally:
            conn.close()



    def update_schema_with_musicbrainz_metadata(self):
        """Actualiza el esquema para incluir nuevos metadatos de MusicBrainz."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Nuevas columnas para la tabla songs
        new_songs_columns = {
            'musicbrainz_artistid': 'TEXT',
            'musicbrainz_recordingid': 'TEXT',
            'musicbrainz_albumartistid': 'TEXT',
            'musicbrainz_releasegroupid': 'TEXT'
        }
        
        # Verificar y añadir columnas en la tabla songs
        c.execute("PRAGMA table_info(songs)")
        existing_song_columns = {col[1] for col in c.fetchall()}
        for col_name, col_type in new_songs_columns.items():
            if col_name not in existing_song_columns:
                c.execute(f"ALTER TABLE songs ADD COLUMN {col_name} {col_type}")
        
        # Nuevas columnas para la tabla albums
        new_albums_columns = {
            'musicbrainz_albumid': 'TEXT',
            'musicbrainz_albumartistid': 'TEXT',
            'musicbrainz_releasegroupid': 'TEXT',
            'catalognumber': 'TEXT',
            'media': 'TEXT',
            'discnumber': 'TEXT',
            'releasecountry': 'TEXT',
            'originalyear': 'INTEGER'
        }
        
        # Verificar y añadir columnas en la tabla albums
        c.execute("PRAGMA table_info(albums)")
        existing_album_columns = {col[1] for col in c.fetchall()}
        for col_name, col_type in new_albums_columns.items():
            if col_name not in existing_album_columns:
                c.execute(f"ALTER TABLE albums ADD COLUMN {col_name} {col_type}")
        
        conn.commit()
        conn.close()
        self.logger.info("Esquema actualizado con columnas para metadatos de MusicBrainz")


    def update_schema(self):
        """Actualiza el esquema de la base de datos con todas las tablas e índices."""
        # Primero inicializar la base de datos (tablas)
        self.init_database()
        
        # Luego aplicar optimizaciones
        self.optimize_database()
        
        # Finalmente crear índices
        self.create_indices()
        
        self.logger.info("Actualización de esquema completada")


    def quick_scan_library(self):
        """
        Realiza un escaneo rápido para identificar álbumes ausentes y
        actualizar la base de datos de manera eficiente.
        """
        start_time = datetime.now()
        self.logger.info("Iniciando escaneo rápido de la biblioteca...")
        
        # Encontrar álbumes ausentes
        missing_album_ids = self.find_missing_albums()
        
        if missing_album_ids:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            try:
                # Marcar los álbumes como eliminados o eliminarlos
                # Opción 1: Eliminar los álbumes ausentes
                for album_id in missing_album_ids:
                    # También puedes eliminar las canciones relacionadas
                    c.execute("SELECT id FROM songs WHERE album IN (SELECT name FROM albums WHERE id = ?)", (album_id,))
                    song_ids = [row[0] for row in c.fetchall()]
                    
                    for song_id in song_ids:
                        c.execute("DELETE FROM song_links WHERE song_id = ?", (song_id,))
                        c.execute("DELETE FROM lyrics WHERE track_id = ?", (song_id,))
                    
                    c.execute("DELETE FROM songs WHERE album IN (SELECT name FROM albums WHERE id = ?)", (album_id,))
                    c.execute("DELETE FROM albums WHERE id = ?", (album_id,))
                
                # Opción 2: Alternativamente, puedes marcarlos como eliminados sin eliminarlos
                # c.execute("UPDATE albums SET is_deleted = 1 WHERE id IN ({})".format(','.join('?' * len(missing_album_ids))), missing_album_ids)
                
                conn.commit()
                self.logger.info(f"Se han eliminado {len(missing_album_ids)} álbumes ausentes de la base de datos")
                
            except Exception as e:
                self.logger.error(f"Error al actualizar álbumes ausentes: {str(e)}")
            
            finally:
                conn.close()
        
        # Posiblemente escanear solo las carpetas nuevas
        # Esta sería una mejora futura para solo procesar carpetas que no están en la DB
        
        self.logger.info(f"Escaneo rápido completado en {(datetime.now() - start_time).total_seconds():.2f} segundos")


    def get_audio_metadata(self, file_path: Path) -> Optional[Dict]:
        """Extract comprehensive audio metadata including MusicBrainz IDs and additional fields."""
        try:
            audio = None
            audio_tech = None
            
            # Handle different audio formats
            if file_path.suffix.lower() == '.mp3':
                audio = mutagen.File(file_path, easy=True)
                audio_tech = mutagen.File(file_path)
                
            elif file_path.suffix.lower() == '.flac':
                audio = mutagen.flac.FLAC(file_path)
                audio_tech = audio
                
            elif file_path.suffix.lower() == '.m4a':
                audio = mutagen.File(file_path)
                audio_tech = audio
            
            if not audio or not audio_tech:
                return None

            # Extraer track_number y manejarlo correctamente según el formato
            track_number = '0'
            if file_path.suffix.lower() == '.mp3':
                if 'tracknumber' in audio:
                    track_number = audio['tracknumber'][0].split('/')[0]
            elif file_path.suffix.lower() == '.flac':
                if 'tracknumber' in audio:
                    track_number = str(audio.get('tracknumber', ['0'])[0]).split('/')[0]
            elif file_path.suffix.lower() == '.m4a':
                if 'trkn' in audio:
                    track_number = str(audio.get('trkn', [[0, 0]])[0][0])

            current_time = datetime.now()
            
            # Metadata básica
            metadata = {
                'file_path': str(file_path),
                'title': self._get_tag_value(audio, 'title', 'Untitled'),
                'track_number': int(track_number) if track_number and str(track_number).isdigit() else 0,
                'artist': self._get_tag_value(audio, 'artist', 'Unknown Artist'),
                'album_artist': self._get_tag_value(audio, 'albumartist', None) or 
                            self._get_tag_value(audio, 'album artist', None) or 
                            self._get_tag_value(audio, 'artist', 'Unknown Artist'),
                'album': self._get_tag_value(audio, 'album', 'Unknown Album'),
                'date': self._get_tag_value(audio, 'date', '') or self._get_tag_value(audio, 'year', ''),
                'genre': self._get_tag_value(audio, 'genre', 'Unknown'),
                'label': self._get_tag_value(audio, 'organization', None) or 
                        self._get_tag_value(audio, 'label', ''),
                'mbid': self._get_tag_value(audio, 'musicbrainz_trackid', ''),
                'date_created': datetime.fromtimestamp(os.path.getctime(file_path)),
                'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)),
                'added_timestamp': current_time,
                'added_day': current_time.day,
                'added_week': int(current_time.strftime('%V')),
                'added_month': current_time.month,
                'added_year': current_time.year,
                'folder_path': str(file_path.parent),
                'origen': 'local',
                
                # Nuevos metadatos de MusicBrainz
                'musicbrainz_artistid': self._get_tag_value(audio, 'musicbrainz_artistid', ''),
                'musicbrainz_recordingid': self._get_tag_value(audio, 'musicbrainz_recordingid', ''),
                'musicbrainz_albumid': self._get_tag_value(audio, 'musicbrainz_albumid', ''),
                'musicbrainz_albumartistid': self._get_tag_value(audio, 'musicbrainz_albumartistid', ''),
                'musicbrainz_releasegroupid': self._get_tag_value(audio, 'musicbrainz_releasegroupid', ''),
                'catalognumber': self._get_tag_value(audio, 'catalognumber', ''),
                'media': self._get_tag_value(audio, 'media', ''),
                'discnumber': self._get_tag_value(audio, 'discnumber', ''),
                'releasecountry': self._get_tag_value(audio, 'releasecountry', ''),
                'originalyear': self._extract_year(self._get_tag_value(audio, 'originalyear', ''))
            }

            # Technical information - correctly calculate bitrate
            if hasattr(audio_tech, 'info'):
                # Calculate bitrate correctly based on format
                if file_path.suffix.lower() == '.flac':
                    # For FLAC: Calculate from file size and duration
                    file_size_bits = os.path.getsize(file_path) * 8
                    duration_seconds = audio_tech.info.length
                    if duration_seconds > 0:
                        bitrate = int(file_size_bits / duration_seconds / 1000)  # Convert to kbps
                    else:
                        bitrate = 0
                else:
                    # For MP3/M4A: Use the reported bitrate
                    bitrate = getattr(audio_tech.info, 'bitrate', 0) // 1000  # Convert to kbps
                
                metadata['bitrate'] = bitrate
                metadata['sample_rate'] = getattr(audio_tech.info, 'sample_rate', 0)
                metadata['bit_depth'] = getattr(audio_tech.info, 'bits_per_sample', 0)
                metadata['duration'] = getattr(audio_tech.info, 'length', 0)
            
            # Extract ReplayGain information based on file format
            metadata['replay_gain_track_gain'] = self._extract_float_tag(audio, 'replaygain_track_gain')
            metadata['replay_gain_track_peak'] = self._extract_float_tag(audio, 'replaygain_track_peak')
            metadata['replay_gain_album_gain'] = self._extract_float_tag(audio, 'replaygain_album_gain')
            metadata['replay_gain_album_peak'] = self._extract_float_tag(audio, 'replaygain_album_peak')

            return metadata

        except Exception as e:
            self.logger.error(f"Metadata extraction error for {file_path}: {str(e)}")
            return None

    def _get_tag_value(self, audio, tag_name, default_value=''):
        """Obtiene el valor de una etiqueta de forma segura para diferentes formatos de audio."""
        if tag_name in audio:
            value = audio[tag_name]
            if isinstance(value, list) and value:
                return value[0]
            return value
        return default_value

    def _extract_year(self, year_str):
        """Extraer año como entero desde una cadena de texto."""
        if not year_str:
            return None
        
        # Intentar extraer el año como entero
        try:
            # Buscar un patrón de 4 dígitos que represente un año
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', str(year_str))
            if year_match:
                return int(year_match.group(0))
            
            # Si no tiene formato de año, probar a convertir directamente
            return int(year_str)
        except (ValueError, TypeError):
            return None


    def find_album_folders(self):
        """
        Encuentra todas las carpetas que contienen archivos FLAC u otros formatos soportados.
        
        Returns:
            set: Conjunto de rutas de carpetas que contienen archivos de audio soportados
        """
        album_folders = set()
        
        self.logger.info("Buscando carpetas con archivos de audio...")
        start_time = datetime.now()
        
        for extension in self.supported_formats:
            for file_path in self.root_path.rglob(f'*{extension}'):
                album_folders.add(str(file_path.parent.resolve()))
        
        self.logger.info(f"Se encontraron {len(album_folders)} carpetas en {(datetime.now() - start_time).total_seconds():.2f} segundos")
        return album_folders

    def find_missing_albums(self):
        """
        Identifica álbumes que ya no existen en el sistema de archivos.
        
        Returns:
            list: Lista de IDs de álbumes que ya no existen
        """
        # Obtener todas las carpetas con archivos de audio
        album_folders = self.find_album_folders()
        
        # Método 1: Comparación directa con la base de datos (consulta por consulta)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        missing_album_ids = []
        
        try:
            # Opción 1: Para bases de datos pequeñas, verificar directamente
            c.execute("SELECT id, folder_path FROM albums WHERE folder_path IS NOT NULL")
            db_albums = c.fetchall()
            
            if len(db_albums) < 5000:  # Un límite arbitrario para bases de datos pequeñas
                for album_id, folder_path in db_albums:
                    if folder_path and folder_path not in album_folders:
                        missing_album_ids.append(album_id)
            else:
                # Opción 2: Para bases de datos grandes, usar un enfoque de conjunto
                # Guardar todos los IDs y paths en un diccionario para búsqueda rápida
                album_dict = {folder_path: album_id for album_id, folder_path in db_albums if folder_path}
                
                # Encontrar las rutas que no existen en album_folders
                missing_paths = set(album_dict.keys()) - album_folders
                
                # Obtener los IDs correspondientes
                missing_album_ids = [album_dict[path] for path in missing_paths]
            
            self.logger.info(f"Se encontraron {len(missing_album_ids)} álbumes ausentes en la biblioteca")
            
        except Exception as e:
            self.logger.error(f"Error al buscar álbumes ausentes: {str(e)}")
        
        finally:
            conn.close()
        
        return missing_album_ids


    def update_album_artwork_and_paths(self):
        """
        Actualiza la tabla 'albums' con información sobre:
        - folder_path: La ruta de la carpeta que contiene las canciones del álbum
        - album_art_path: La ruta de la imagen de portada (cover, folder, album)
        - total_tracks: El número total de canciones del álbum
        También actualiza la tabla 'songs' con:
        - album_art_path_denorm: La ruta de la imagen de portada del álbum
        """
        # Conectar a la base de datos
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            # Primero, obtener todos los álbumes en la base de datos
            c.execute("SELECT id, name FROM albums")
            albums = c.fetchall()
            
            self.logger.info(f"Actualizando información de rutas, portadas y conteo de canciones para {len(albums)} álbumes...")
            start_time = datetime.now()
            
            albums_updated = 0
            artwork_found = 0
            
            for album_id, album_name in albums:
                # Obtener las rutas de carpetas y contar canciones para este álbum desde la tabla songs
                c.execute("""
                    SELECT file_path FROM songs 
                    WHERE album = ?
                """, (album_name,))
                
                results = c.fetchall()
                track_count = len(results)
                
                # Extraer las rutas de carpetas únicas
                folder_paths = set()
                for row in results:
                    if row[0]:
                        # Obtener la carpeta padre del archivo
                        folder_path = str(Path(row[0]).parent)
                        folder_paths.add(folder_path)
                
                if not folder_paths:
                    continue
                    
                # Actualizar los folder_paths y total_tracks en la tabla albums
                folder_paths_str = ";".join(folder_paths)
                c.execute("UPDATE albums SET folder_path = ?, total_tracks = ? WHERE id = ?", 
                        (folder_paths_str, track_count, album_id))
                albums_updated += 1
                
                # Buscar imágenes de portada en las carpetas
                album_art_path = None
                for folder_path in folder_paths:
                    # Buscar archivos de imagen con nombres comunes para portadas
                    potential_covers = []
                    folder = Path(folder_path)
                    
                    # Buscar archivos de imagen con nombres comunes para portadas
                    for cover_name in ['cover', 'folder', 'album', 'front']:
                        for ext in ['.jpg', '.jpeg', '.png']:
                            # Buscar exacto
                            exact_match = folder / f"{cover_name}{ext}"
                            if exact_match.exists():
                                potential_covers.append(str(exact_match))
                            
                            # Buscar con mayúsculas
                            upper_match = folder / f"{cover_name.capitalize()}{ext}"
                            if upper_match.exists():
                                potential_covers.append(str(upper_match))
                    
                    # Si encontramos portadas, usar la primera
                    if potential_covers:
                        album_art_path = potential_covers[0]
                        break
                
                # Actualizar album_art_path en la tabla albums
                if album_art_path:
                    c.execute("UPDATE albums SET album_art_path = ? WHERE id = ?", 
                            (album_art_path, album_id))
                    artwork_found += 1
                    
                    # Actualizar el campo album_art_path_denorm en la tabla songs
                    c.execute("""
                        UPDATE songs 
                        SET album_art_path_denorm = ? 
                        WHERE album = ?
                    """, (album_art_path, album_name))
                
            # Guardar los cambios
            conn.commit()
            self.logger.info(f"Actualización completada: {albums_updated} álbumes actualizados, {artwork_found} con portadas encontradas, en {(datetime.now() - start_time).total_seconds():.2f} segundos")
                
        except Exception as e:
            self.logger.error(f"Error al actualizar rutas y portadas de álbumes: {str(e)}")
            conn.rollback()
        
        finally:
            conn.close()

    def _extract_float_tag(self, audio, tag_name):
        """Extract a float value from an audio tag, handling different formats."""
        if tag_name in audio:
            try:
                # Extract the numerical part and convert to float
                value = str(audio[tag_name][0])
                return self._parse_replay_gain_value(value)
            except (IndexError, ValueError, TypeError):
                return None
        return None

    def _extract_mp3_replay_gain(self, audio, *tag_names):
        """Try multiple possible tag names for MP3 replay gain."""
        for tag_name in tag_names:
            if tag_name in audio:
                try:
                    value = str(audio[tag_name].text[0])
                    return self._parse_replay_gain_value(value)
                except (IndexError, ValueError, AttributeError, TypeError):
                    continue
        return None

    def _parse_replay_gain_value(self, value_str):
        """Parse replay gain value from string, handling different formats."""
        try:
            # Strip 'dB' suffix and any whitespace
            value_str = value_str.replace('dB', '').strip()
            # Convert to float
            return float(value_str)
        except (ValueError, TypeError):
            return None

    def update_album_bitrates(self):

        """
        Actualiza los rangos de bitrate para todos los álbumes en la base de datos.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            self.logger.info("Actualizando rangos de bitrate para álbumes...")
            
            # Obtener todos los álbumes
            c.execute("SELECT id, artist_id, name FROM albums")
            albums = c.fetchall()
            
            updated_count = 0
            
            for album_id, artist_id, album_name in albums:
                # Obtener el artista asociado
                c.execute("SELECT name FROM artists WHERE id = ?", (artist_id,))
                artist_result = c.fetchone()
                
                if artist_result:
                    artist_name = artist_result[0]
                    
                    # Calcular el rango de bitrate para el álbum
                    c.execute('''
                        SELECT MIN(bitrate), MAX(bitrate), COUNT(*)
                        FROM songs
                        WHERE album = ? AND artist = ?
                    ''', (album_name, artist_name))
                    
                    bitrate_range = c.fetchone()
                    
                    if bitrate_range and bitrate_range[2] > 0:  # Asegurarse de que hay canciones
                        min_bitrate = bitrate_range[0] if bitrate_range[0] is not None else 0
                        max_bitrate = bitrate_range[1] if bitrate_range[1] is not None else 0
                        
                        # Formatear el rango de bitrate
                        bitrate_range_str = f"{min_bitrate}-{max_bitrate}" if min_bitrate != max_bitrate else str(min_bitrate)
                        
                        # Actualizar el álbum con el rango de bitrate
                        c.execute('''
                            UPDATE albums
                            SET bitrate_range = ?
                            WHERE id = ?
                        ''', (bitrate_range_str, album_id))
                        
                        updated_count += 1
                        
                        if updated_count % 100 == 0:
                            conn.commit()
                            self.logger.info(f"Actualizados {updated_count} álbumes")
            
            conn.commit()
            self.logger.info(f"Actualización de rangos de bitrate completada. Actualizados {updated_count} álbumes.")
        
        except Exception as e:
            self.logger.error(f"Error al actualizar rangos de bitrate: {str(e)}")
        
        finally:
            conn.close()


    def scan_library(self, force_update=False):
        """Comprehensive library scanning with selective updates."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        error_log_path = PROJECT_ROOT / '.content' / 'logs' / 'db' / 'db_musica_path_error.log'
        if not error_log_path.exists():
            error_log_path.parent.mkdir(parents=True, exist_ok=True)
            with error_log_path.open('w', encoding='utf-8') as f:
                f.write('')
        error_logger = logging.getLogger('error_log')
        error_logger.setLevel(logging.ERROR)
        error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
        error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        error_handler.setFormatter(error_formatter)
        error_logger.addHandler(error_handler)
        
        processed_files = 0
        error_files = 0
        
        # Dictionary to store folder metadata for album consistency
        folder_albums = {}
        
        try:
            # Verificar si la tabla song_links existe y crearla si no
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_links'")
            if not c.fetchone():
                c.execute('''
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
                        FOREIGN KEY(song_id) REFERENCES songs(id)
                    )
                ''')
                conn.commit()
            
            # First pass: gather folder information to establish consistent album metadata
            for file_path in self.root_path.rglob('*'):
                if file_path.suffix.lower() in self.supported_formats:
                    try:
                        metadata = self.get_audio_metadata(file_path)
                        if metadata:
                            folder_path = metadata['folder_path']
                            if folder_path not in folder_albums:
                                # Use album artist if available, otherwise use primary artist
                                primary_artist = metadata['album_artist'] or metadata['artist'].split('feat.')[0].split('with')[0].split('&')[0].strip()
                                
                                folder_albums[folder_path] = {
                                    'album': metadata['album'],
                                    'primary_artist': primary_artist,
                                    'year': metadata['date'],
                                    'genre': metadata['genre'],
                                    'label': metadata['label']
                                }
                    except Exception as e:
                        error_logger.error(f"First pass error for {file_path}: {str(e)}")
            
            # Second pass: process files with consistent album metadata
            for file_path in self.root_path.rglob('*'):
                if file_path.suffix.lower() in self.supported_formats:
                    abs_path = str(file_path.absolute())
                    
                    try:
                        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        # Check if file needs processing
                        c.execute("SELECT last_modified, added_timestamp FROM songs WHERE file_path = ?", (abs_path,))
                        existing_record = c.fetchone()
                        
                        # Convert database date to datetime
                        if existing_record:
                            try:
                                db_last_modified = datetime.strptime(existing_record[0], '%Y-%m-%d %H:%M:%S.%f')
                                original_added_timestamp = datetime.strptime(existing_record[1], '%Y-%m-%d %H:%M:%S.%f') if existing_record[1] else None
                            except ValueError:
                                # Try without the fraction of seconds
                                try:
                                    db_last_modified = datetime.strptime(existing_record[0], '%Y-%m-%d %H:%M:%S')
                                    original_added_timestamp = datetime.strptime(existing_record[1], '%Y-%m-%d %H:%M:%S') if existing_record[1] else None
                                except:
                                    db_last_modified = None
                                    original_added_timestamp = None
                        else:
                            db_last_modified = None
                            original_added_timestamp = None
                            

                        if force_update == True or not db_last_modified or last_modified > db_last_modified:
                            metadata = self.get_audio_metadata(file_path)
                            
                            if metadata:
                                # Preserve original added_timestamp if it exists
                                if original_added_timestamp:
                                    metadata['added_timestamp'] = original_added_timestamp
                                    metadata['added_day'] = original_added_timestamp.day
                                    metadata['added_week'] = int(original_added_timestamp.strftime('%V'))
                                    metadata['added_month'] = original_added_timestamp.month
                                    metadata['added_year'] = original_added_timestamp.year
                                
                                # Use folder-based consistent album metadata
                                folder_path = metadata['folder_path']
                                if folder_path in folder_albums:
                                    folder_metadata = folder_albums[folder_path]
                                    consistent_album_artist = folder_metadata['primary_artist']
                                    
                                    # Insert or update song with consistent album metadata
                                    c.execute('''
                                        INSERT OR REPLACE INTO songs 
                                        (file_path, title, track_number, artist, album_artist, 
                                        album, date, genre, label, mbid, bitrate, 
                                        bit_depth, sample_rate, last_modified, duration,
                                        added_timestamp, added_day, added_week, added_month, added_year,
                                        replay_gain_track_gain, replay_gain_track_peak, 
                                        replay_gain_album_gain, replay_gain_album_peak, origen,
                                        musicbrainz_artistid, musicbrainz_recordingid, 
                                        musicbrainz_albumartistid, musicbrainz_releasegroupid)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        metadata['file_path'], metadata['title'], metadata['track_number'], 
                                        metadata['artist'], consistent_album_artist, folder_metadata['album'], 
                                        folder_metadata['year'], folder_metadata['genre'], folder_metadata['label'], 
                                        metadata['mbid'], metadata.get('bitrate'), metadata.get('bit_depth'),
                                        metadata.get('sample_rate'), metadata['last_modified'], 
                                        metadata.get('duration'), metadata['added_timestamp'],
                                        metadata.get('added_day'), metadata['added_week'], 
                                        metadata['added_month'], metadata['added_year'],
                                        metadata.get('replay_gain_track_gain'), metadata.get('replay_gain_track_peak'),
                                        metadata.get('replay_gain_album_gain'), metadata.get('replay_gain_album_peak'),
                                        'local',
                                        metadata.get('musicbrainz_artistid', ''),
                                        metadata.get('musicbrainz_recordingid', ''),
                                        metadata.get('musicbrainz_albumartistid', ''),
                                        metadata.get('musicbrainz_releasegroupid', '')
                                    ))
                                    
                                    # Asegurarse de que la canción también tenga entrada en song_links
                                    self._ensure_song_links_entry(c, metadata['file_path'])
                                    
                                    processed_files += 1
                                    
                                    # Update/insert artist information (using album artist for album relationship)
                                    self._update_artist_info(c, consistent_album_artist)
                                    
                                    # Update/insert album information using consistent album metadata
                                    self._update_album_info(c, {
                                        'artist': consistent_album_artist,
                                        'album': folder_metadata['album'],
                                        'date': folder_metadata['year'],
                                        'label': folder_metadata['label'],
                                        'genre': folder_metadata['genre']
                                    })
                                    
                                    # Update/insert genre information
                                    self._update_genre_info(c, folder_metadata['genre'])
                                else:
                                    # Fallback to original metadata if folder info not available
                                    c.execute('''
                                        INSERT OR REPLACE INTO songs 
                                        (file_path, title, track_number, artist, album_artist, 
                                        album, date, genre, label, mbid, bitrate, 
                                        bit_depth, sample_rate, last_modified, duration,
                                        added_timestamp, added_day, added_week, added_month, added_year,
                                        replay_gain_track_gain, replay_gain_track_peak, 
                                        replay_gain_album_gain, replay_gain_album_peak, origen)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        metadata['file_path'], metadata['title'], metadata['track_number'], 
                                        metadata['artist'], metadata['album_artist'], metadata['album'], 
                                        metadata['date'], metadata['genre'], metadata['label'], 
                                        metadata['mbid'], metadata.get('bitrate'), metadata.get('bit_depth'),
                                        metadata.get('sample_rate'), metadata['last_modified'], 
                                        metadata.get('duration'), metadata['added_timestamp'],
                                        metadata.get('added_day'), metadata['added_week'], 
                                        metadata['added_month'], metadata['added_year'],
                                        metadata.get('replay_gain_track_gain'), metadata.get('replay_gain_track_peak'),
                                        metadata.get('replay_gain_album_gain'), metadata.get('replay_gain_album_peak'),
                                        'local'
                                    ))
                                    
                                    # Asegurarse de que la canción también tenga entrada en song_links
                                    self._ensure_song_links_entry(c, metadata['file_path'])
                                    
                                    processed_files += 1
                                    
                                    # Update remaining tables
                                    self._update_artist_info(c, metadata['album_artist'] or metadata['artist'])
                                    self._update_album_info(c, metadata)
                                    self._update_genre_info(c, metadata['genre'])
                            
                            else:
                                error_files += 1
                                error_logger.error(f"Metadata extraction failed: {abs_path}")
                        
                        # Hacemos commit más frecuentemente para evitar perder trabajo
                        if processed_files % 10 == 0:
                            conn.commit()
                    
                    except Exception as file_error:
                        error_files += 1
                        error_logger.error(f"File processing error {abs_path}: {str(file_error)}")
            
            # Commit final para asegurar que todos los cambios se guarden
            conn.commit()
        
        except Exception as scan_error:
            self.logger.error(f"Library scan error: {str(scan_error)}")
        
        finally:
            conn.close()
            error_logger.removeHandler(error_handler)
            error_handler.close()
            
            self.logger.info("Library scan completed")
            self.logger.info(f"Files processed: {processed_files}")
            self.logger.info(f"Files with errors: {error_files}")


    def _ensure_song_links_entry(self, cursor, file_path):
        """Asegurarse de que existe una entrada en song_links para esta canción"""
        # Primero, verificar si la tabla song_links existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_links'")
        if not cursor.fetchone():
            # Si la tabla no existe, crearla
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
                    FOREIGN KEY(song_id) REFERENCES songs(id)
                )
            ''')
        
        # Ahora obtener el ID de la canción
        cursor.execute("SELECT id FROM songs WHERE file_path = ?", (file_path,))
        result = cursor.fetchone()
        if result:
            song_id = result[0]
            
            # Verificar si ya existe una entrada en song_links
            cursor.execute("SELECT id FROM song_links WHERE song_id = ?", (song_id,))
            if not cursor.fetchone():
                # Si no existe, crear una entrada vacía
                cursor.execute('''
                    INSERT INTO song_links 
                    (song_id, links_updated)
                    VALUES (?, ?)
                ''', (song_id, datetime.now()))

    def _update_artist_info(self, cursor, artist_name):
        """Update artist information selectively."""
        # Skip if artist name is None
        if not artist_name:
            return

        # Clean up artist name to remove featuring parts
        artist_name = artist_name.split('feat.')[0].split('with')[0].split('&')[0].strip()
        
        cursor.execute("SELECT id FROM artists WHERE name = ?", (artist_name,))
        existing_artist = cursor.fetchone()
        
        current_time = datetime.now()
        
        # Simplemente insertar el artista si no existe
        if not existing_artist:
            cursor.execute('''
                INSERT INTO artists 
                (name, last_updated, added_timestamp, added_day, added_week, added_month, added_year, origen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                artist_name, current_time, current_time, 
                current_time.day, int(current_time.strftime('%V')), 
                current_time.month, current_time.year, 'local'
            ))




    def _update_album_info(self, cursor, metadata):
        """Update album information with all MusicBrainz and additional metadata."""
        # Omitir si no hay datos válidos
        if not metadata['artist'] or not metadata['album']:
            return
            
        # Limpiar nombre de artista 
        artist_name = metadata['artist'].split('feat.')[0].split('with')[0].split('&')[0].strip()
        
        # Verificar si existe el artista
        cursor.execute("SELECT id FROM artists WHERE name = ?", (artist_name,))
        artist_result = cursor.fetchone()
        
        current_time = datetime.now()
        
        if not artist_result:
            # Crear el artista si no existe
            cursor.execute('''
                INSERT INTO artists (
                    name, last_updated, added_timestamp, added_day, added_week, 
                    added_month, added_year, origen, mbid
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                artist_name, current_time, current_time, 
                current_time.day, int(current_time.strftime('%V')), 
                current_time.month, current_time.year, 'local',
                metadata.get('musicbrainz_albumartistid', '')
            ))
            cursor.execute("SELECT id FROM artists WHERE name = ?", (artist_name,))
            artist_result = cursor.fetchone()
                
        artist_id = artist_result[0]
        
        # Verificar si existe este álbum para este artista
        cursor.execute('''
            SELECT id, last_updated 
            FROM albums 
            WHERE artist_id = ? AND name = ?
        ''', (artist_id, metadata['album']))
        
        existing_album = cursor.fetchone()
        
        # Calcular el rango de bitrate
        cursor.execute('''
            SELECT MIN(bitrate), MAX(bitrate)
            FROM songs
            WHERE album = ? AND artist = ?
        ''', (metadata['album'], artist_name))
        
        bitrate_range = cursor.fetchone()
        min_bitrate = bitrate_range[0] if bitrate_range and bitrate_range[0] is not None else 0
        max_bitrate = bitrate_range[1] if bitrate_range and bitrate_range[1] is not None else 0
        
        if 'bitrate' in metadata and metadata['bitrate']:
            if metadata['bitrate'] < min_bitrate or min_bitrate == 0:
                min_bitrate = metadata['bitrate']
            if metadata['bitrate'] > max_bitrate:
                max_bitrate = metadata['bitrate']
        
        bitrate_range_str = f"{min_bitrate}-{max_bitrate}" if min_bitrate != max_bitrate else str(min_bitrate)
        
        # Insertar o actualizar el álbum
        if not existing_album:
            cursor.execute('''
                INSERT INTO albums (
                    artist_id, name, year, label, genre, last_updated, bitrate_range, folder_path, 
                    added_timestamp, added_day, added_week, added_month, added_year, origen,
                    musicbrainz_albumid, musicbrainz_albumartistid, musicbrainz_releasegroupid,
                    catalognumber, media, discnumber, releasecountry, originalyear, mbid
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                artist_id, metadata['album'], metadata['date'], metadata['label'], metadata['genre'],
                current_time, bitrate_range_str, metadata.get('folder_path', ''),
                current_time, current_time.day, int(current_time.strftime('%V')),
                current_time.month, current_time.year, 'local',
                metadata.get('musicbrainz_albumid', ''),
                metadata.get('musicbrainz_albumartistid', ''),
                metadata.get('musicbrainz_releasegroupid', ''),
                metadata.get('catalognumber', ''),
                metadata.get('media', ''),
                metadata.get('discnumber', ''),
                metadata.get('releasecountry', ''),
                metadata.get('originalyear'),
                metadata.get('musicbrainz_albumid', '')  # Usamos musicbrainz_albumid como mbid
            ))
        elif (datetime.now() - self._parse_db_datetime(existing_album[1])) > timedelta(days=30):
            cursor.execute('''
                UPDATE albums
                SET year = ?, label = ?, genre = ?, last_updated = ?, bitrate_range = ?, folder_path = ?,
                    musicbrainz_albumid = COALESCE(musicbrainz_albumid, ?),
                    musicbrainz_albumartistid = COALESCE(musicbrainz_albumartistid, ?),
                    musicbrainz_releasegroupid = COALESCE(musicbrainz_releasegroupid, ?),
                    catalognumber = COALESCE(catalognumber, ?),
                    media = COALESCE(media, ?),
                    discnumber = COALESCE(discnumber, ?),
                    releasecountry = COALESCE(releasecountry, ?),
                    originalyear = COALESCE(originalyear, ?),
                    mbid = COALESCE(mbid, ?)
                WHERE id = ?
            ''', (
                metadata['date'], metadata['label'], metadata['genre'], current_time,
                bitrate_range_str, metadata.get('folder_path', ''),
                metadata.get('musicbrainz_albumid', ''),
                metadata.get('musicbrainz_albumartistid', ''),
                metadata.get('musicbrainz_releasegroupid', ''),
                metadata.get('catalognumber', ''),
                metadata.get('media', ''),
                metadata.get('discnumber', ''),
                metadata.get('releasecountry', ''),
                metadata.get('originalyear'),
                metadata.get('musicbrainz_albumid', ''),
                existing_album[0]
            ))

    def _update_genre_info(self, cursor, genre_name):
        """Update genre information if not exists."""
        if not genre_name or genre_name == 'Unknown':
            return
            
        cursor.execute("SELECT * FROM genres WHERE name = ?", (genre_name,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO genres (name) VALUES (?)
            ''', (genre_name,))

    # def get_lastfm_artist_info(self, artist_name: str) -> Optional[Dict]:
    #     """Retrieve comprehensive LastFM artist information."""
    #     try:
    #         artist = self.network.get_artist(artist_name)
            
    #         return {
    #             'name': artist_name,
    #             'bio': artist.get_bio_summary(),
    #             'tags': json.dumps([tag.item.name for tag in artist.get_top_tags()]),
    #             'similar_artists': json.dumps([similar.item.name for similar in artist.get_similar()]),
    #             'last_updated': datetime.now(),
    #             'origin': None,  # LastFM doesn't directly provide this
    #             'formed_year': None  # LastFM doesn't directly provide this
    #         }
    #     except Exception as e:
    #         self.logger.error(f"LastFM artist info error for {artist_name}: {str(e)}")
    #         return {
    #             'name': artist_name,
    #             'bio': '',
    #             'tags': json.dumps([]),
    #             'similar_artists': json.dumps([]),
    #             'last_updated': datetime.now(),
    #             'origin': None,
    #             'formed_year': None
    #         }
    
    def _parse_db_datetime(self, datetime_str):
        """Safely parse datetime strings from database."""
        if not datetime_str:
            return datetime.now() - timedelta(days=365)  # Default to a year ago
            
        try:
            return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return datetime.now() - timedelta(days=365)  # Default to a year ago

    def update_replay_gain_only(self):
        """One-time update to extract replay gain for all files in the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Get all files in the database
            c.execute("SELECT file_path FROM songs")
            files = c.fetchall()
            
            updated_count = 0
            for file_path_tuple in files:
                file_path = file_path_tuple[0]
                path_obj = Path(file_path)
                
                if path_obj.exists() and path_obj.is_file():
                    try:
                        # Just extract the replay gain data
                        audio = None
                        if path_obj.suffix.lower() == '.flac':
                            audio = FLAC(path_obj)
                        elif path_obj.suffix.lower() == '.mp3':
                            audio = mutagen.File(path_obj)
                        elif path_obj.suffix.lower() == '.m4a':
                            audio = mutagen.File(path_obj)
                        
                        if audio:
                            # Extract replay gain using the methods you implemented
                            replay_gains = {
                                'replay_gain_track_gain': self._extract_float_tag(audio, 'replaygain_track_gain'),
                                'replay_gain_track_peak': self._extract_float_tag(audio, 'replaygain_track_peak'),
                                'replay_gain_album_gain': self._extract_float_tag(audio, 'replaygain_album_gain'),
                                'replay_gain_album_peak': self._extract_float_tag(audio, 'replaygain_album_peak')
                            }
                            
                            # Update the database with just the replay gain data
                            c.execute("""
                                UPDATE songs 
                                SET replay_gain_track_gain = ?,
                                    replay_gain_track_peak = ?,
                                    replay_gain_album_gain = ?,
                                    replay_gain_album_peak = ?
                                WHERE file_path = ?
                            """, (
                                replay_gains['replay_gain_track_gain'],
                                replay_gains['replay_gain_track_peak'],
                                replay_gains['replay_gain_album_gain'],
                                replay_gains['replay_gain_album_peak'],
                                file_path
                            ))
                            updated_count += 1
                            
                            if updated_count % 100 == 0:
                                conn.commit()
                                self.logger.info(f"Updated replay gain for {updated_count} files")
                                
                    except Exception as e:
                        self.logger.error(f"Error updating replay gain for {file_path}: {str(e)}")
            
            conn.commit()
            self.logger.info(f"Replay gain update completed. Updated {updated_count} files.")
        
        except Exception as e:
            self.logger.error(f"Replay gain update error: {str(e)}")
        
        finally:
            conn.close()



def main(config=None):
    if config is None:
        parser = argparse.ArgumentParser(description='db_musica_path')
        parser.add_argument('--config', required=True, help='Archivo de configuración')
        args = parser.parse_args()
        
        with open(args.config, 'r') as f:
            config_data = json.load(f)
            
        # Combinar configuraciones
        config = {}
        config.update(config_data.get("common", {}))
        config.update(config_data.get("db_musica_path", {}))

    # Verificamos que todas las claves necesarias existan
    db_path = config.get('db_path')
    root_path = config.get('root_path')
    
    print(f"db_path: {db_path}")
    print(f"Ruta de la base de datos (después de Path().resolve()): {Path(db_path).resolve()}")
    print(f"¿La ruta existe? {os.path.exists(db_path)}")
    print(f"¿Tienes permisos? {os.access(db_path, os.R_OK | os.W_OK) if os.path.exists(db_path) else 'N/A'}")

    if not all([db_path, root_path]):
        missing = []
        if not db_path: missing.append('db_path')
        if not root_path: missing.append('root_path')
        print(f"Error: Faltan claves necesarias en la configuración: {', '.join(missing)}")
        return 1
        
    manager = MusicLibraryManager(root_path, db_path)

    # Asegurar que el esquema esté actualizado con los nuevos campos
    manager.update_schema_with_musicbrainz_metadata()

    if config.get('update_schema', False):
        manager.update_schema()

    
    if config.get('optimize', False):
        manager.optimize_database()
        manager.create_indices()
        
    if config.get('update_replay_gain', False):
        manager.update_replay_gain_only()
    
    if config.get('quick_scan', False):
        manager.quick_scan_library()
        
    if config.get('update_bitrates', False):
        manager.update_album_bitrates()
    
    # Escanear la biblioteca siempre como último paso
    if not config.get('update_replay_gain', False) and not config.get('optimize', False) and not config.get('update_schema', False) and not config.get('quick_scan', False) and not config.get('update_bitrates', False):
        manager.scan_library(force_update=config.get('force_update', False))
        manager.update_album_artwork_and_paths()

if __name__ == "__main__":
    main()