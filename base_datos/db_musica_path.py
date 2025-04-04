
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

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
import pylast
import sqlite3
from datetime import datetime, timedelta
import argparse


class MusicLibraryManager:
    def __init__(self, root_path: str, db_path: str, lastfm_api_key: str):
        self.root_path = Path(root_path).resolve()
        self.db_path = Path(db_path).resolve()
        self.supported_formats = ('.mp3', '.flac', '.m4a')
        
        # Logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # LastFM initialization
        self.network = pylast.LastFMNetwork(
            api_key=lastfm_api_key,
        )
        
        # Initialize database
        self.init_database()

    def init_database(self, create_indices=False):
        """Initialize SQLite database with comprehensive tables and optionally create indices."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check for existing tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [table[0] for table in c.fetchall()]
        
        # Songs table
        if 'songs' not in existing_tables:
            c.execute('''
                CREATE TABLE IF NOT EXISTS songs (
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
                    has_lyrics INTEGER DEFAULT 0
                )
            ''')
        else:
            # Check existing columns in songs table
            c.execute("PRAGMA table_info(songs)")
            columns = {col[1] for col in c.fetchall()}
            
            # Add new columns if they don't exist
            new_columns = {
                'added_timestamp': 'TIMESTAMP',
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
                'has_lyrics': 'INTEGER DEFAULT 0'
            }
            
            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    c.execute(f"ALTER TABLE songs ADD COLUMN {col_name} {col_type}")
        
        # Artists table
        if 'artists' not in existing_tables:
            c.execute('''
                CREATE TABLE IF NOT EXISTS artists (
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
                    mbid TEXT
                )
            ''')
        else:
            # Check existing columns in artists table
            c.execute("PRAGMA table_info(artists)")
            artist_columns = {col[1] for col in c.fetchall()}
            
            # Add new columns if they don't exist
            new_artist_columns = {
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
                'member_of': 'TEXT'
            }
            
            for col_name, col_type in new_artist_columns.items():
                if col_name not in artist_columns:
                    c.execute(f"ALTER TABLE artists ADD COLUMN {col_name} {col_type}")
        
        # Albums table
        if 'albums' not in existing_tables:
            c.execute('''
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
                    FOREIGN KEY(artist_id) REFERENCES artists(id),
                    UNIQUE(artist_id, name)
                )
            ''')
        else:
            # Check existing columns in albums table
            c.execute("PRAGMA table_info(albums)")
            album_columns = {col[1] for col in c.fetchall()}
            
            # Add new columns if they don't exist
            new_album_columns = {
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
                'credits': 'JSON'
            }
            
            for col_name, col_type in new_album_columns.items():
                if col_name not in album_columns:
                    c.execute(f"ALTER TABLE albums ADD COLUMN {col_name} {col_type}")
        
        
        # Genres table
        if 'genres' not in existing_tables:
            c.execute('''
                CREATE TABLE IF NOT EXISTS genres (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    description TEXT,
                    related_genres TEXT,
                    origin_year INTEGER
                )
            ''')
        
        # Lyrics table
        if 'lyrics' not in existing_tables:
            c.execute('''
                CREATE TABLE IF NOT EXISTS lyrics (
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
                    FOREIGN KEY(song_id) REFERENCES songs(id)
                )
            ''')
        else:
            # Check existing columns in song_links table
            c.execute("PRAGMA table_info(song_links)")
            song_links_columns = {col[1] for col in c.fetchall()}
            
            # Add new columns if they don't exist
            new_song_links_columns = {
                'spotify_url': 'TEXT',
                'spotify_id': 'TEXT',
                'lastfm_url': 'TEXT',
                'links_updated': 'TIMESTAMP',
                'youtube_url': 'TEXT',
                'musicbrainz_url': 'TEXT',
                'musicbrainz_recording_id': 'TEXT'
            }
            
            for col_name, col_type in new_song_links_columns.items():
                if col_name not in song_links_columns:
                    c.execute(f"ALTER TABLE song_links ADD COLUMN {col_name} {col_type}")
        
        # Create FTS tables if they don't exist
        if 'songs_fts' not in existing_tables:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS songs_fts USING fts5(
                    title, artist, album, genre,
                    content=songs, content_rowid=id
                )
            ''')
        
        if 'lyrics_fts' not in existing_tables:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS lyrics_fts USING fts5(
                    lyrics,
                    content=lyrics, content_rowid=id
                )
            ''')
        
        if 'song_fts' not in existing_tables:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS song_fts USING fts5(
                    id, title, artist, album, genre
                )
            ''')
        
        if 'artist_fts' not in existing_tables:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS artist_fts USING fts5(
                    id, name, bio, tags
                )
            ''')
        
        if 'album_fts' not in existing_tables:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS album_fts USING fts5(
                    id, name, genre
                )
            ''')
        
        # Create indices if requested
        if create_indices:
            c.execute("CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums(artist_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_lyrics_track_id ON lyrics(track_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)")
        
        conn.commit()
        conn.close()
        

    def create_indices(self):
        """Crea índices optimizados para mejorar el rendimiento de consultas."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            self.logger.info("Creando índices para optimizar la base de datos...")
            
            # 1. Índices para búsquedas generales
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
            
            # 2. Índices para búsquedas case-insensitive
            indices_case_insensitive = [
                "CREATE INDEX IF NOT EXISTS idx_songs_title_lower ON songs(LOWER(title))",
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_lower ON songs(LOWER(artist))",
                "CREATE INDEX IF NOT EXISTS idx_songs_album_lower ON songs(LOWER(album))",
                "CREATE INDEX IF NOT EXISTS idx_artists_name_lower ON artists(LOWER(name))",
                "CREATE INDEX IF NOT EXISTS idx_albums_name_lower ON albums(LOWER(name))",
                "CREATE INDEX IF NOT EXISTS idx_albums_label_lower ON albums(LOWER(label))",
                "CREATE INDEX IF NOT EXISTS idx_albums_genre_lower ON albums(LOWER(genre))"
            ]
            
            # 3. Índices compuestos para consultas específicas
            indices_compuestos = [
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_album ON songs(artist, album)",
                "CREATE INDEX IF NOT EXISTS idx_songs_album_title ON songs(album, title)",
                "CREATE INDEX IF NOT EXISTS idx_songs_album_track ON songs(album, track_number)",
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_title ON songs(artist, title)",
                "CREATE INDEX IF NOT EXISTS idx_songs_date_added ON songs(added_year, added_month, added_week)"
            ]
            
            # 4. Índices para JOINs específicos
            indices_joins = [
                "CREATE INDEX IF NOT EXISTS idx_songs_id ON songs(id)",
                "CREATE INDEX IF NOT EXISTS idx_lyrics_track_id ON lyrics(track_id)",
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_album_join ON songs(artist, album)"
            ]
            
            # 5. Índices para la consulta de búsqueda principal
            indices_busqueda = [
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_album_track ON songs(artist, album, track_number)"
            ]
            
            # 6. Índices para URLs y servicios externos
            indices_urls = [
                "CREATE INDEX IF NOT EXISTS idx_song_links_urls ON song_links(song_id, spotify_url, youtube_url, spotify_id, lastfm_url)"
            ]
            
            # Crear todos los índices
            indices_totales = indices_generales + indices_case_insensitive + indices_compuestos + indices_joins + indices_busqueda + indices_urls
            
            for index_query in indices_totales:
                try:
                    c.execute(index_query)
                    conn.commit()
                except sqlite3.OperationalError as e:
                    # Algunos índices pueden fallar si la columna no existe todavía
                    self.logger.warning(f"Índice no creado: {e}")

            # 7. Enable foreign keys without trying to alter existing tables
            try:
                c.execute("PRAGMA foreign_keys = ON")
                self.logger.info("Foreign keys enabled for future operations")
            except sqlite3.OperationalError as e:
                self.logger.warning(f"Could not enable foreign keys: {e}")
            
            # # 7. Restricciones de clave foránea (si no existen ya)
            # try:
            #     c.execute("PRAGMA foreign_keys = ON")
                
            #     # Verificar si ya existen las restricciones antes de añadirlas
            #     c.execute("PRAGMA foreign_key_list(songs)")
            #     if not c.fetchall():
            #         c.execute("ALTER TABLE songs ADD CONSTRAINT fk_songs_lyrics FOREIGN KEY (lyrics_id) REFERENCES lyrics(id)")
                
            #     c.execute("PRAGMA foreign_key_list(lyrics)")
            #     if not c.fetchall():
            #         c.execute("ALTER TABLE lyrics ADD CONSTRAINT fk_lyrics_songs FOREIGN KEY (track_id) REFERENCES songs(id)")
                
            #     c.execute("PRAGMA foreign_key_list(albums)")
            #     if not c.fetchall():
            #         c.execute("ALTER TABLE albums ADD CONSTRAINT fk_albums_artists FOREIGN KEY (artist_id) REFERENCES artists(id)")
                
            #     c.execute("PRAGMA foreign_key_list(song_links)")
            #     if not c.fetchall():
            #         c.execute("ALTER TABLE song_links ADD CONSTRAINT fk_song_links_songs FOREIGN KEY (song_id) REFERENCES songs(id)")
            
            except sqlite3.OperationalError as e:
                self.logger.warning(f"No se pudieron crear restricciones de clave foránea: {e}")
                
            # 8. Intentar crear tablas FTS (Full-Text Search) si están soportadas
            try:
                c.execute("DROP TABLE IF EXISTS songs_fts")
                c.execute("CREATE VIRTUAL TABLE songs_fts USING fts5(title, artist, album, genre, content=songs)")
                
                c.execute("DROP TABLE IF EXISTS lyrics_fts")
                c.execute("CREATE VIRTUAL TABLE lyrics_fts USING fts5(lyrics, content=lyrics)")
                
                self.logger.info("Tablas de búsqueda de texto completo creadas exitosamente")
            except sqlite3.OperationalError as e:
                self.logger.warning(f"No se pudieron crear tablas FTS: {e}")
            
            # 9. Actualizar estadísticas del optimizador
            c.execute("ANALYZE")
            
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
        """Extract comprehensive audio metadata including correctly calculated bitrate."""
        try:
            audio = None
            audio_tech = None
            track_number = '0'
            
            # Handle different audio formats
            if file_path.suffix.lower() == '.mp3':
                audio = EasyID3(file_path)
                audio_tech = mutagen.File(file_path)
                track_number = audio.get('tracknumber', ['0'])[0].split('/')[0]
                
                # Get ID3 tags for replay gain (MP3)
                raw_audio = mutagen.File(file_path)
                
            elif file_path.suffix.lower() == '.flac':
                audio = FLAC(file_path)
                audio_tech = audio
                track_number = str(audio.get('tracknumber', ['0'])[0]).split('/')[0]
                
                # FLAC has direct access to replay gain
                raw_audio = audio
                
            elif file_path.suffix.lower() == '.m4a':
                audio = mutagen.File(file_path)
                audio_tech = audio
                track_number = audio.get('trkn', [[0, 0]])[0][0]
                
                # For M4A, tags are directly accessible
                raw_audio = audio
                
            if not audio or not audio_tech:
                return None

            current_time = datetime.now()
            
            metadata = {
                'file_path': str(file_path),
                'title': audio.get('title', ['Untitled'])[0],
                'track_number': int(track_number) if track_number and str(track_number).isdigit() else 0,
                'artist': audio.get('artist', ['Unknown Artist'])[0],
                'album_artist': audio.get('albumartist', [None])[0] or audio.get('album artist', [None])[0] or audio.get('artist', ['Unknown Artist'])[0],
                'album': audio.get('album', ['Unknown Album'])[0],
                'date': audio.get('date', [''])[0] or audio.get('year', [''])[0],
                'genre': audio.get('genre', ['Unknown'])[0],
                'label': audio.get('organization', [None])[0] or audio.get('label', [None])[0] or '',
                'mbid': audio.get('musicbrainz_trackid', [''])[0],
                'date_created': datetime.fromtimestamp(os.path.getctime(file_path)),
                'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)),
                'added_timestamp': current_time,
                'added_week': int(current_time.strftime('%V')),  # ISO week number
                'added_month': current_time.month,
                'added_year': current_time.year,
                'folder_path': str(file_path.parent)  # Add folder path for album grouping
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
            # For FLAC files
            if file_path.suffix.lower() == '.flac':
                metadata['replay_gain_track_gain'] = self._extract_float_tag(raw_audio, 'replaygain_track_gain')
                metadata['replay_gain_track_peak'] = self._extract_float_tag(raw_audio, 'replaygain_track_peak')
                metadata['replay_gain_album_gain'] = self._extract_float_tag(raw_audio, 'replaygain_album_gain')
                metadata['replay_gain_album_peak'] = self._extract_float_tag(raw_audio, 'replaygain_album_peak')
            
            # For MP3 files - different tag formats exist, try multiple variants
            elif file_path.suffix.lower() == '.mp3':
                # Try to find replay gain info in raw ID3 tags
                metadata['replay_gain_track_gain'] = self._extract_mp3_replay_gain(raw_audio, 'TXXX:REPLAYGAIN_TRACK_GAIN', 'TXXX:replaygain_track_gain')
                metadata['replay_gain_track_peak'] = self._extract_mp3_replay_gain(raw_audio, 'TXXX:REPLAYGAIN_TRACK_PEAK', 'TXXX:replaygain_track_peak')
                metadata['replay_gain_album_gain'] = self._extract_mp3_replay_gain(raw_audio, 'TXXX:REPLAYGAIN_ALBUM_GAIN', 'TXXX:replaygain_album_gain')
                metadata['replay_gain_album_peak'] = self._extract_mp3_replay_gain(raw_audio, 'TXXX:REPLAYGAIN_ALBUM_PEAK', 'TXXX:replaygain_album_peak')
                
            # For M4A files
            elif file_path.suffix.lower() == '.m4a':
                # M4A usually has replay gain in ----:com.apple.iTunes:replaygain_track_gain format
                for tag in raw_audio:
                    if 'replaygain_track_gain' in tag.lower():
                        metadata['replay_gain_track_gain'] = self._parse_replay_gain_value(str(raw_audio[tag][0]))
                    if 'replaygain_track_peak' in tag.lower():
                        metadata['replay_gain_track_peak'] = self._parse_replay_gain_value(str(raw_audio[tag][0]))
                    if 'replaygain_album_gain' in tag.lower():
                        metadata['replay_gain_album_gain'] = self._parse_replay_gain_value(str(raw_audio[tag][0]))
                    if 'replaygain_album_peak' in tag.lower():
                        metadata['replay_gain_album_peak'] = self._parse_replay_gain_value(str(raw_audio[tag][0]))



            return metadata

        except Exception as e:
            self.logger.error(f"Metadata extraction error for {file_path}: {str(e)}")
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
        
        error_log_path = PROJECT_ROOT / '.content' / 'log' / 'db' / 'db_musica_path_error.log'
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
                            

                        if force_update or not db_last_modified or last_modified > db_last_modified:
                            metadata = self.get_audio_metadata(file_path)
                            
                            if metadata:
                                # Preserve original added_timestamp if it exists
                                if original_added_timestamp:
                                    metadata['added_timestamp'] = original_added_timestamp
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
                                        added_timestamp, added_week, added_month, added_year,
                                        replay_gain_track_gain, replay_gain_track_peak, 
                                        replay_gain_album_gain, replay_gain_album_peak)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        metadata['file_path'], metadata['title'], metadata['track_number'], 
                                        metadata['artist'], consistent_album_artist, folder_metadata['album'], 
                                        folder_metadata['year'], folder_metadata['genre'], folder_metadata['label'], 
                                        metadata['mbid'], metadata.get('bitrate'), metadata.get('bit_depth'),
                                        metadata.get('sample_rate'), metadata['last_modified'], 
                                        metadata.get('duration'), metadata['added_timestamp'],
                                        metadata['added_week'], metadata['added_month'], metadata['added_year'],
                                        metadata.get('replay_gain_track_gain'), metadata.get('replay_gain_track_peak'),
                                        metadata.get('replay_gain_album_gain'), metadata.get('replay_gain_album_peak')
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
                                        added_timestamp, added_week, added_month, added_year,
                                        replay_gain_track_gain, replay_gain_track_peak, 
                                        replay_gain_album_gain, replay_gain_album_peak)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        metadata['file_path'], metadata['title'], metadata['track_number'], 
                                        metadata['artist'], metadata['album_artist'], metadata['album'], 
                                        metadata['date'], metadata['genre'], metadata['label'], 
                                        metadata['mbid'], metadata.get('bitrate'), metadata.get('bit_depth'),
                                        metadata.get('sample_rate'), metadata['last_modified'], 
                                        metadata.get('duration'), metadata['added_timestamp'],
                                        metadata['added_week'], metadata['added_month'], metadata['added_year'],
                                        metadata.get('replay_gain_track_gain'), metadata.get('replay_gain_track_peak'),
                                        metadata.get('replay_gain_album_gain'), metadata.get('replay_gain_album_peak')
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
                        
                        conn.commit()
                    
                    except Exception as file_error:
                        error_files += 1
                        error_logger.error(f"File processing error {abs_path}: {str(file_error)}")
        
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
        # Primero obtener el ID de la canción
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
        
        cursor.execute("SELECT last_updated FROM artists WHERE name = ?", (artist_name,))
        existing_artist = cursor.fetchone()
        
        # Only update if no existing record or older than 30 days
        if not existing_artist:
            cursor.execute('''
                INSERT INTO artists 
                (name, last_updated)
                VALUES (?, ?)
            ''', (artist_name, datetime.now()))
        elif existing_artist and (datetime.now() - self._parse_db_datetime(existing_artist[0])) > timedelta(days=30):
            lastfm_info = self.get_lastfm_artist_info(artist_name)
            
            if lastfm_info:
                cursor.execute('''
                    UPDATE artists 
                    SET bio = ?, tags = ?, similar_artists = ?, last_updated = ?
                    WHERE name = ?
                ''', (
                    lastfm_info['bio'], lastfm_info['tags'], 
                    lastfm_info['similar_artists'], lastfm_info['last_updated'],
                    artist_name
                ))



    def _update_album_info(self, cursor, metadata):
        """Update album information using folder-based consistency and calculate bitrate range."""
        # Skip if invalid data
        if not metadata['artist'] or not metadata['album']:
            return
            
        # Clean up artist name (just in case)
        artist_name = metadata['artist'].split('feat.')[0].split('with')[0].split('&')[0].strip()
        
        # First check if artist exists
        cursor.execute("SELECT id FROM artists WHERE name = ?", (artist_name,))
        artist_result = cursor.fetchone()
        
        if not artist_result:
            # If artist doesn't exist, create it
            cursor.execute('''
                INSERT INTO artists (name, last_updated)
                VALUES (?, ?)
            ''', (artist_name, datetime.now()))
            cursor.execute("SELECT id FROM artists WHERE name = ?", (artist_name,))
            artist_result = cursor.fetchone()
            
        artist_id = artist_result[0]
        
        # Check if this album already exists for this artist
        cursor.execute('''
            SELECT id, last_updated 
            FROM albums 
            WHERE artist_id = ? AND name = ?
        ''', (artist_id, metadata['album']))
        
        existing_album = cursor.fetchone()
        
        # Calculate bitrate range for the album
        cursor.execute('''
            SELECT MIN(bitrate), MAX(bitrate)
            FROM songs
            WHERE album = ? AND artist = ?
        ''', (metadata['album'], artist_name))
        
        bitrate_range = cursor.fetchone()
        min_bitrate = bitrate_range[0] if bitrate_range and bitrate_range[0] is not None else 0
        max_bitrate = bitrate_range[1] if bitrate_range and bitrate_range[1] is not None else 0
        
        # If we have new song data, update the range with current song bitrate
        if 'bitrate' in metadata and metadata['bitrate']:
            if metadata['bitrate'] < min_bitrate or min_bitrate == 0:
                min_bitrate = metadata['bitrate']
            if metadata['bitrate'] > max_bitrate:
                max_bitrate = metadata['bitrate']
        
        bitrate_range_str = f"{min_bitrate}-{max_bitrate}" if min_bitrate != max_bitrate else str(min_bitrate)
        
        # Insert or update based on existence and last updated time
        if not existing_album:
            cursor.execute('''
                INSERT INTO albums 
                (artist_id, name, year, label, genre, last_updated, bitrate_range, folder_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                artist_id, metadata['album'], 
                metadata['date'], metadata['label'], 
                metadata['genre'], datetime.now(),
                bitrate_range_str, metadata.get('folder_path', '')
            ))
        elif (datetime.now() - self._parse_db_datetime(existing_album[1])) > timedelta(days=30):
            cursor.execute('''
                UPDATE albums
                SET year = ?, label = ?, genre = ?, last_updated = ?, bitrate_range = ?, folder_path = ?
                WHERE id = ?
            ''', (
                metadata['date'], metadata['label'], 
                metadata['genre'], datetime.now(),
                bitrate_range_str, metadata.get('folder_path', ''),
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

    def get_lastfm_artist_info(self, artist_name: str) -> Optional[Dict]:
        """Retrieve comprehensive LastFM artist information."""
        try:
            artist = self.network.get_artist(artist_name)
            
            return {
                'name': artist_name,
                'bio': artist.get_bio_summary(),
                'tags': json.dumps([tag.item.name for tag in artist.get_top_tags()]),
                'similar_artists': json.dumps([similar.item.name for similar in artist.get_similar()]),
                'last_updated': datetime.now(),
                'origin': None,  # LastFM doesn't directly provide this
                'formed_year': None  # LastFM doesn't directly provide this
            }
        except Exception as e:
            self.logger.error(f"LastFM artist info error for {artist_name}: {str(e)}")
            return {
                'name': artist_name,
                'bio': '',
                'tags': json.dumps([]),
                'similar_artists': json.dumps([]),
                'last_updated': datetime.now(),
                'origin': None,
                'formed_year': None
            }
    
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
        parser = argparse.ArgumentParser(description='enlaces_artista_album')
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
    lastfm_api_key = config.get('lastfm_api_key')
    print(f"db_path: {db_path}")
    print(f"Ruta de la base de datos (después de Path().resolve()): {Path(db_path).resolve()}")
    print(f"¿La ruta existe? {os.path.exists(db_path)}")
    print(f"¿Tienes permisos? {os.access(db_path, os.R_OK | os.W_OK) if os.path.exists(db_path) else 'N/A'}")

    if not all([db_path, root_path, lastfm_api_key]):
        missing = []
        if not db_path: missing.append('db_path')
        if not root_path: missing.append('root_path')
        if not lastfm_api_key: missing.append('lastfm_api_key')
        print(f"Error: Faltan claves necesarias en la configuración: {', '.join(missing)}")
        return 1
        
    manager = MusicLibraryManager(root_path, db_path, lastfm_api_key)


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