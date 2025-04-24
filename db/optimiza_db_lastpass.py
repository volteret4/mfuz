#!/usr/bin/env python
#
# Script Name: optimiza_db_lastpass.py
# Description: Optimiza la base de datos, crea índices, tablas normalizadas y vistas
# Author: volteret4
# Repository: https://github.com/volteret4/
# License:
# Notes:
#   Dependencies:  - python3, sqlite3
#
# CONSEJOS DE USO:
# - Para búsquedas de texto rápidas, usa las tablas virtuales '_fts':
#     SELECT * FROM songs WHERE id IN (SELECT id FROM song_fts WHERE song_fts MATCH 'palabra_clave')

# - Utiliza las vistas 'view_song_details' y 'view_album_stats' para consultas comunes

# - Aprovecha las columnas desnormalizadas para consultas más rápidas:
#     - album_year
#     - artist_origin
#     - album_art_path_denorm
#     - has_lyrics


import sqlite3
import os
import time
import logging
import shutil
import argparse
import json
import re

class QueryOptimizer:
    def __init__(self, db_path, backup=True):
        self.db_path = db_path
        self.backup = backup
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        logger = logging.getLogger('QueryOptimizer')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def backup_database(self):
        """Crea una copia de seguridad de la base de datos."""
        if self.backup:
            backup_path = f"{self.db_path}_backup_{int(time.time())}"
            self.logger.info(f"Creando copia de seguridad en: {backup_path}")
            shutil.copy2(self.db_path, backup_path)
            return backup_path
        return None
    
    def optimize_for_reading(self):
        """Aplica optimizaciones específicas para maximizar la velocidad de consulta."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            self.logger.info("Aplicando optimizaciones para velocidad máxima de consulta...")
            
            # Configuraciones de rendimiento orientadas a lectura
            pragmas = [
                "PRAGMA journal_mode = WAL",         # Write-Ahead Logging mejora lecturas concurrentes
                "PRAGMA synchronous = NORMAL",        # Equilibrio entre rendimiento y seguridad
                "PRAGMA cache_size = -32000",         # Usar ~32MB de caché para consultas (valor negativo para KB)
                "PRAGMA temp_store = MEMORY",         # Almacenar tablas temporales en memoria
                "PRAGMA mmap_size = 30000000000",     # Usar memory-mapped I/O para lectura más rápida (30GB máximo)
                "PRAGMA page_size = 32768",           # Páginas más grandes (32KB) mejor para lecturas secuenciales
                "PRAGMA foreign_keys = OFF",          # Deshabilitar verificación de claves foráneas para rendimiento
                "PRAGMA automatic_index = ON"         # Permitir índices automáticos para consultas complejas
            ]
            
            for pragma in pragmas:
                c.execute(pragma)
                
            # Verificar configuraciones aplicadas
            c.execute("PRAGMA journal_mode")
            journal_mode = c.fetchone()[0]
            self.logger.info(f"Modo de journal establecido a: {journal_mode}")
            
            c.execute("PRAGMA page_size")
            page_size = c.fetchone()[0]
            self.logger.info(f"Tamaño de página establecido a: {page_size} bytes")
            
            c.execute("PRAGMA cache_size")
            cache_size = c.fetchone()[0]
            self.logger.info(f"Tamaño de caché establecido a: {cache_size * -1 / 1024} MB")
            
            # Ejecutar ANALYZE para optimizar el planificador de consultas
            c.execute("ANALYZE")
            
            self.logger.info("Optimizaciones de lectura aplicadas correctamente")
        
        except Exception as e:
            self.logger.error(f"Error al optimizar la base de datos: {str(e)}")
        
        finally:
            conn.close()
    
    def create_advanced_indices(self):
        """Crea índices avanzados optimizados para consultas comunes en una biblioteca musical."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            self.logger.info("Creando índices avanzados para consultas...")
            
            # Identificar consultas potencialmente frecuentes y crear índices específicos
            indexes = [
                # Índices básicos
                "CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_albums_name ON albums(name COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name COLLATE NOCASE)",
                
                # Índices para búsquedas parciales (usando LIKE)
                "CREATE INDEX IF NOT EXISTS idx_songs_title_pattern ON songs(title COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_pattern ON songs(artist COLLATE NOCASE)",
                
                # Índices compuestos para búsquedas comunes combinadas
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_album ON songs(artist, album)",
                "CREATE INDEX IF NOT EXISTS idx_songs_album_title ON songs(album, title)",
                "CREATE INDEX IF NOT EXISTS idx_albums_artist_id_year ON albums(artist_id, year)",
                
                # Índices para ordenamiento
                "CREATE INDEX IF NOT EXISTS idx_songs_added_timestamp ON songs(added_timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_songs_duration ON songs(duration)",
                
                # Índices para juntar tablas eficientemente
                "CREATE INDEX IF NOT EXISTS idx_songs_lyrics_id ON songs(lyrics_id)",
                "CREATE INDEX IF NOT EXISTS idx_lyrics_track_id ON lyrics(track_id)",
                "CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)",
                "CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums(artist_id)",
                
                # Índices para filtros de tiempo/fecha
                "CREATE INDEX IF NOT EXISTS idx_songs_added_year_month ON songs(added_year, added_month)",
                
                # Índices para estadísticas y agregaciones
                "CREATE INDEX IF NOT EXISTS idx_songs_bitrate ON songs(bitrate)",
                "CREATE INDEX IF NOT EXISTS idx_songs_bit_depth ON songs(bit_depth)",
                "CREATE INDEX IF NOT EXISTS idx_songs_sample_rate ON songs(sample_rate)",
                
                # Índices para metadatos de streaming
                "CREATE INDEX IF NOT EXISTS idx_albums_spotify_id ON albums(spotify_id)",
                "CREATE INDEX IF NOT EXISTS idx_song_links_spotify_id ON song_links(spotify_id)",
                
                # NUEVOS ÍNDICES ADICIONALES
                "CREATE INDEX IF NOT EXISTS idx_artists_origin ON artists(origin)",
                "CREATE INDEX IF NOT EXISTS idx_albums_label ON albums(label)",
                "CREATE INDEX IF NOT EXISTS idx_albums_year ON albums(year)",
                "CREATE INDEX IF NOT EXISTS idx_feeds_entity_type_id ON feeds(entity_type, entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_scrobbles_artist_name ON scrobbles(artist_name)",
                "CREATE INDEX IF NOT EXISTS idx_listens_artist_name ON listens(artist_name)",
                "CREATE INDEX IF NOT EXISTS idx_scrobbles_album_name ON scrobbles(album_name)",
                "CREATE INDEX IF NOT EXISTS idx_listens_album_name ON listens(album_name)",
                "CREATE INDEX IF NOT EXISTS idx_scrobbles_song_id ON scrobbles(song_id)",
                "CREATE INDEX IF NOT EXISTS idx_listens_song_id ON listens(song_id)",
                "CREATE INDEX IF NOT EXISTS idx_label_release_relationships_label_id ON label_release_relationships(label_id)",
                "CREATE INDEX IF NOT EXISTS idx_label_release_relationships_album_id ON label_release_relationships(album_id)"
            ]
            
            # Crear vistas materializadas para consultas frecuentes
            materializations = [
                # Vista para información completa de canciones
                """
                CREATE VIEW IF NOT EXISTS view_song_details AS
                SELECT 
                    s.id, s.title, s.artist, s.album_artist, s.album, s.duration, s.genre, 
                    s.date, s.track_number, s.file_path, s.bitrate, s.bit_depth, s.sample_rate,
                    a.id as album_id, a.year as album_year, a.album_art_path,
                    ar.id as artist_id, ar.bio as artist_bio, ar.origin as artist_origin,
                    l.lyrics,
                    sl.spotify_url, sl.youtube_url
                FROM songs s
                LEFT JOIN albums a ON s.album = a.name
                LEFT JOIN artists ar ON s.artist = ar.name
                LEFT JOIN lyrics l ON s.lyrics_id = l.id
                LEFT JOIN song_links sl ON s.id = sl.song_id
                """,
                
                # Vista para estadísticas de álbumes
                """
                CREATE VIEW IF NOT EXISTS view_album_stats AS
                SELECT 
                    a.id, a.name, a.artist_id, ar.name as artist_name, a.year, a.genre, a.label,
                    COUNT(s.id) as actual_track_count,
                    a.total_tracks as reported_track_count,
                    SUM(s.duration) as total_duration,
                    AVG(s.bitrate) as avg_bitrate,
                    MAX(s.bit_depth) as max_bit_depth,
                    MAX(s.sample_rate) as max_sample_rate
                FROM albums a
                LEFT JOIN artists ar ON a.artist_id = ar.id
                LEFT JOIN songs s ON s.album = a.name AND s.artist = ar.name
                GROUP BY a.id
                """,
                
                # NUEVAS VISTAS ADICIONALES
                
                # Vista para estadísticas de artistas
                """
                CREATE VIEW IF NOT EXISTS view_artist_stats AS
                SELECT 
                    ar.id, ar.name, ar.origin, 
                    COUNT(DISTINCT a.id) as album_count,
                    COUNT(DISTINCT s.id) as song_count,
                    COUNT(DISTINCT l.id) as lyric_count,
                    COUNT(DISTINCT f.id) as feed_count,
                    (SELECT COUNT(*) FROM scrobbles sc WHERE sc.artist_name = ar.name) as scrobble_count,
                    (SELECT COUNT(*) FROM listens ls WHERE ls.artist_name = ar.name) as listen_count,
                    GROUP_CONCAT(DISTINCT s.genre) as genres
                FROM artists ar
                LEFT JOIN albums a ON a.artist_id = ar.id
                LEFT JOIN songs s ON s.artist = ar.name
                LEFT JOIN lyrics l ON s.lyrics_id = l.id
                LEFT JOIN feeds f ON f.entity_id = ar.id AND f.entity_type = 'artist'
                GROUP BY ar.id
                """,
                
                # Vista para estadísticas de sellos discográficos
                """
                CREATE VIEW IF NOT EXISTS view_label_stats AS
                SELECT 
                    a.label,
                    COUNT(DISTINCT a.id) as album_count,
                    COUNT(DISTINCT a.artist_id) as artist_count,
                    COUNT(DISTINCT s.id) as song_count,
                    MIN(a.year) as first_year,
                    MAX(a.year) as last_year,
                    GROUP_CONCAT(DISTINCT s.genre) as genres,
                    (
                        SELECT COUNT(*) 
                        FROM feeds f 
                        JOIN albums a2 ON f.entity_id = a2.id AND f.entity_type = 'album'
                        WHERE a2.label = a.label
                    ) as feed_count
                FROM albums a
                LEFT JOIN songs s ON s.album = a.name
                WHERE a.label IS NOT NULL AND a.label != ''
                GROUP BY a.label
                """,
                
                # Vista para estadísticas de países
                """
                CREATE VIEW IF NOT EXISTS view_country_stats AS
                SELECT 
                    ar.origin as country,
                    COUNT(DISTINCT ar.id) as artist_count,
                    COUNT(DISTINCT a.id) as album_count,
                    COUNT(DISTINCT s.id) as song_count,
                    COUNT(DISTINCT s.genre) as genre_count,
                    MIN(a.year) as first_year,
                    MAX(a.year) as last_year,
                    (
                        SELECT COUNT(*) 
                        FROM scrobbles sc 
                        JOIN artists ar2 ON sc.artist_name = ar2.name
                        WHERE ar2.origin = ar.origin
                    ) as scrobble_count
                FROM artists ar
                LEFT JOIN albums a ON a.artist_id = ar.id
                LEFT JOIN songs s ON s.artist = ar.name
                WHERE ar.origin IS NOT NULL AND ar.origin != ''
                GROUP BY ar.origin
                """,
                
                # Vista para estadísticas de escuchas por artista
                """
                CREATE VIEW IF NOT EXISTS view_artist_listens AS
                SELECT 
                    ar.id, ar.name, ar.origin,
                    COUNT(DISTINCT sc.id) as scrobble_count,
                    COUNT(DISTINCT ls.id) as listen_count,
                    (SELECT COUNT(DISTINCT date(sc2.scrobble_date)) FROM scrobbles sc2 WHERE sc2.artist_name = ar.name) as days_listened,
                    (SELECT MAX(sc3.scrobble_date) FROM scrobbles sc3 WHERE sc3.artist_name = ar.name) as last_listen_date
                FROM artists ar
                LEFT JOIN scrobbles sc ON sc.artist_name = ar.name
                LEFT JOIN listens ls ON ls.artist_name = ar.name
                GROUP BY ar.id
                """
            ]
            
            # Crear los índices
            for index in indexes:
                try:
                    c.execute(index)
                    self.logger.info(f"Índice creado: {index}")
                except sqlite3.Error as e:
                    self.logger.warning(f"No se pudo crear el índice: {str(e)}")
            
            # Crear vistas
            for view in materializations:
                try:
                    c.execute(view)
                    self.logger.info(f"Vista creada correctamente")
                except sqlite3.Error as e:
                    self.logger.warning(f"No se pudo crear la vista: {str(e)}")
            
            conn.commit()
            self.logger.info("Índices y vistas creados con éxito")
        
        except Exception as e:
            self.logger.error(f"Error al crear índices avanzados: {str(e)}")
        
        finally:
            conn.close()
    
    def add_denormalized_columns(self):
        """
        Añade columnas desnormalizadas para mejorar el rendimiento de consulta.
        La desnormalización es una técnica que sacrifica espacio para mejorar la velocidad de lectura.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            self.logger.info("Añadiendo columnas desnormalizadas para mejorar rendimiento de consulta...")
            
            # Verificar si las columnas ya existen en la tabla songs
            c.execute("PRAGMA table_info(songs)")
            columns = [info[1] for info in c.fetchall()]
            
            # Columnas a añadir si no existen
            columns_to_add = []
            if "album_year" not in columns:
                columns_to_add.append("album_year TEXT")
            if "artist_origin" not in columns:
                columns_to_add.append("artist_origin TEXT")
            if "album_art_path_denorm" not in columns:
                columns_to_add.append("album_art_path_denorm TEXT")
            if "has_lyrics" not in columns:
                columns_to_add.append("has_lyrics INTEGER DEFAULT 0")
            # Nuevas columnas desnormalizadas
            if "album_label" not in columns:
                columns_to_add.append("album_label TEXT")
            if "decade" not in columns:
                columns_to_add.append("decade INTEGER")
            
            # Añadir columnas a la tabla songs
            if columns_to_add:
                for column_def in columns_to_add:
                    column_name = column_def.split()[0]
                    self.logger.info(f"Añadiendo columna {column_name} a la tabla songs")
                    c.execute(f"ALTER TABLE songs ADD COLUMN {column_def}")
                
                conn.commit()
                self.logger.info("Columnas añadidas correctamente")
            else:
                self.logger.info("Las columnas desnormalizadas ya existen")
            
            # Actualizar valores desnormalizados
            self.logger.info("Actualizando valores desnormalizados...")
            
            # Actualizar album_year desde la tabla albums
            c.execute("""
            UPDATE songs
            SET album_year = (
                SELECT year FROM albums WHERE name = songs.album
            )
            WHERE album_year IS NULL
            """)
            
            # Actualizar artist_origin desde la tabla artists
            c.execute("""
            UPDATE songs
            SET artist_origin = (
                SELECT origin FROM artists WHERE name = songs.artist
            )
            WHERE artist_origin IS NULL
            """)
            
            # Actualizar album_art_path_denorm desde la tabla albums
            c.execute("""
            UPDATE songs
            SET album_art_path_denorm = (
                SELECT album_art_path FROM albums WHERE name = songs.album
            )
            WHERE album_art_path_denorm IS NULL
            """)
            
            # Actualizar has_lyrics basado en lyrics_id
            c.execute("""
            UPDATE songs
            SET has_lyrics = CASE WHEN lyrics_id IS NOT NULL THEN 1 ELSE 0 END
            """)
            
            # Actualizar album_label
            c.execute("""
            UPDATE songs
            SET album_label = (
                SELECT label FROM albums WHERE name = songs.album
            )
            WHERE album_label IS NULL
            """)
            
            # Actualizar década basada en album_year
            c.execute("""
            UPDATE songs
            SET decade = (
                CASE 
                    WHEN album_year IS NULL THEN NULL
                    WHEN CAST(album_year AS INTEGER) > 1900 THEN (CAST(album_year AS INTEGER) / 10) * 10
                    ELSE NULL
                END
            )
            WHERE decade IS NULL
            """)
            
            conn.commit()
            self.logger.info("Valores desnormalizados actualizados correctamente")
            
            # Crear índices para las nuevas columnas
            new_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_songs_album_year ON songs(album_year)",
                "CREATE INDEX IF NOT EXISTS idx_songs_artist_origin ON songs(artist_origin)",
                "CREATE INDEX IF NOT EXISTS idx_songs_has_lyrics ON songs(has_lyrics)",
                "CREATE INDEX IF NOT EXISTS idx_songs_album_label ON songs(album_label)",
                "CREATE INDEX IF NOT EXISTS idx_songs_decade ON songs(decade)"
            ]
            
            for index in new_indexes:
                c.execute(index)
            
            conn.commit()
            self.logger.info("Índices para columnas desnormalizadas creados con éxito")
        
        except Exception as e:
            self.logger.error(f"Error al añadir columnas desnormalizadas: {str(e)}")
        
        finally:
            conn.close()
    
    def create_full_text_search(self):
        """
        Crea índices de búsqueda de texto completo para consultas de búsqueda rápidas.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            self.logger.info("Configurando búsqueda de texto completo...")
            
            # Habilitar la extensión FTS5
            c.execute("PRAGMA foreign_keys = OFF")
            
            # Crear tabla virtual para la búsqueda de canciones
            c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS song_fts USING fts5(
                id, title, artist, album, genre, 
                content='songs', content_rowid='id',
                tokenize='unicode61'
            )
            """)
            
            # Llenar la tabla FTS con datos existentes
            c.execute("""
            INSERT OR IGNORE INTO song_fts(rowid, title, artist, album, genre)
            SELECT id, title, artist, album, genre FROM songs
            """)
            
            # Crear disparadores para mantener el índice FTS actualizado
            triggers = [
                # Disparador para INSERT
                """
                CREATE TRIGGER IF NOT EXISTS songs_ai AFTER INSERT ON songs BEGIN
                  INSERT INTO song_fts(rowid, title, artist, album, genre)
                  VALUES (new.id, new.title, new.artist, new.album, new.genre);
                END;
                """,
                
                # Disparador para DELETE
                """
                CREATE TRIGGER IF NOT EXISTS songs_ad AFTER DELETE ON songs BEGIN
                  INSERT INTO song_fts(song_fts, rowid, title, artist, album, genre)
                  VALUES ('delete', old.id, old.title, old.artist, old.album, old.genre);
                END;
                """,
                
                # Disparador para UPDATE
                """
                CREATE TRIGGER IF NOT EXISTS songs_au AFTER UPDATE ON songs BEGIN
                  INSERT INTO song_fts(song_fts, rowid, title, artist, album, genre)
                  VALUES ('delete', old.id, old.title, old.artist, old.album, old.genre);
                  INSERT INTO song_fts(rowid, title, artist, album, genre)
                  VALUES (new.id, new.title, new.artist, new.album, new.genre);
                END;
                """
            ]
            
            for trigger in triggers:
                c.execute(trigger)
            
            # También crear FTS para artists
            c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS artist_fts USING fts5(
                id, name, bio, tags,
                content='artists', content_rowid='id',
                tokenize='unicode61'
            )
            """)
            
            c.execute("""
            INSERT OR IGNORE INTO artist_fts(rowid, name, bio, tags)
            SELECT id, name, bio, tags FROM artists
            """)
            
            # Y para albums
            c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS album_fts USING fts5(
                id, name, genre,
                content='albums', content_rowid='id',
                tokenize='unicode61'
            )
            """)
            
            c.execute("""
            INSERT OR IGNORE INTO album_fts(rowid, name, genre)
            SELECT id, name, genre FROM albums
            """)
            
            # Nuevo: FTS para lyrics
            c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS lyrics_fts USING fts5(
                id, track_id, lyrics,
                content='lyrics', content_rowid='id',
                tokenize='unicode61'
            )
            """)
            
            c.execute("""
            INSERT OR IGNORE INTO lyrics_fts(rowid, track_id, lyrics)
            SELECT id, track_id, lyrics FROM lyrics
            """)
            
            conn.commit()
            self.logger.info("Búsqueda de texto completo configurada correctamente")
        
        except Exception as e:
            self.logger.error(f"Error al configurar búsqueda de texto completo: {str(e)}")
        
        finally:
            conn.close()
    
    def create_normalized_tables(self):
        """
        Crea tablas normalizadas para mejorar la estructura de la base de datos
        y facilitar las consultas complejas.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            self.logger.info("Creando tablas normalizadas...")
            
            # Tabla de géneros normalizada
            c.execute("""
            CREATE TABLE IF NOT EXISTS genres_normalized (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
            """)
            
            # Tabla de relación para artistas y géneros
            c.execute("""
            CREATE TABLE IF NOT EXISTS artist_genres (
                id INTEGER PRIMARY KEY,
                artist_id INTEGER,
                genre_id INTEGER,
                FOREIGN KEY (artist_id) REFERENCES artists(id),
                FOREIGN KEY (genre_id) REFERENCES genres_normalized(id)
            )
            """)
            
            # Tabla de países normalizada
            c.execute("""
            CREATE TABLE IF NOT EXISTS countries (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                code TEXT
            )
            """)
            
            # Añadir columna country_id a la tabla artists si no existe
            c.execute("PRAGMA table_info(artists)")
            artist_columns = [info[1] for info in c.fetchall()]
            
            if "country_id" not in artist_columns:
                c.execute("ALTER TABLE artists ADD COLUMN country_id INTEGER REFERENCES countries(id)")
            
            # Tabla de décadas para agilizar consultas temporales
            c.execute("""
            CREATE TABLE IF NOT EXISTS decades (
                id INTEGER PRIMARY KEY,
                decade INTEGER UNIQUE NOT NULL,
                description TEXT
            )
            """)
            
            # Añadir columna decade_id a la tabla albums si no existe
            c.execute("PRAGMA table_info(albums)")
            album_columns = [info[1] for info in c.fetchall()]
            
            if "decade_id" not in album_columns:
                c.execute("ALTER TABLE albums ADD COLUMN decade_id INTEGER REFERENCES decades(id)")
            
            # Crear índices para las nuevas tablas
            c.execute("CREATE INDEX IF NOT EXISTS idx_artist_genres_artist_id ON artist_genres(artist_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_artist_genres_genre_id ON artist_genres(genre_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_artists_country_id ON artists(country_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_albums_decade_id ON albums(decade_id)")
            
            conn.commit()
            self.logger.info("Tablas normalizadas creadas con éxito")
            
            # Poblar las tablas normalizadas con datos existentes
            self.populate_normalized_tables(conn)
            
        except Exception as e:
            self.logger.error(f"Error al crear tablas normalizadas: {str(e)}")
        
        finally:
            conn.close()
    
    def populate_normalized_tables(self, conn):
        """
        Rellena las tablas normalizadas con datos existentes.
        """
        c = conn.cursor()
        
        try:
            self.logger.info("Poblando tablas normalizadas con datos existentes...")
            
            # Poblar tabla de géneros
            c.execute("""
            INSERT OR IGNORE INTO genres_normalized (name)
            SELECT DISTINCT genre FROM songs WHERE genre IS NOT NULL AND genre != ''
            UNION
            SELECT DISTINCT genre FROM albums WHERE genre IS NOT NULL AND genre != ''
            """)
            
            # Poblar tabla de países
            c.execute("""
            INSERT OR IGNORE INTO countries (name)
            SELECT DISTINCT origin FROM artists WHERE origin IS NOT NULL AND origin != ''
            """)
            
            # Actualizar country_id en artists
            c.execute("""
            UPDATE artists
            SET country_id = (SELECT id FROM countries WHERE name = artists.origin)
            WHERE origin IS NOT NULL AND origin != '' AND country_id IS NULL
            """)
            
            # Poblar tabla de décadas
            c.execute("""
            INSERT OR IGNORE INTO decades (decade, description)
            SELECT 
                CAST(SUBSTR(year, 1, 3) || '0' AS INTEGER) as decade,
                CAST(SUBSTR(year, 1, 3) || '0s' AS TEXT) as description
            FROM albums
            WHERE 
                year IS NOT NULL 
                AND year != '' 
                AND CAST(year AS INTEGER) > 1900
            GROUP BY decade
            """)
            
            # Actualizar decade_id en albums
            c.execute("""
            UPDATE albums
            SET decade_id = (
                SELECT id FROM decades 
                WHERE decade = CAST(SUBSTR(albums.year, 1, 3) || '0' AS INTEGER)
            )
            WHERE 
                year IS NOT NULL 
                AND year != '' 
                AND CAST(year AS INTEGER) > 1900
                AND decade_id IS NULL
            """)
            
            # Procesar tags de artistas y poblar artist_genres
            c.execute("SELECT id, tags FROM artists WHERE tags IS NOT NULL AND tags != ''")
            
            for artist_id, tags in c.fetchall():
                # Procesar tags
                genres = self._parse_tags(tags)
                
                for genre in genres:
                    if genre:
                        # Obtener o crear género normalizado
                        c.execute("SELECT id FROM genres_normalized WHERE name = ?", (genre,))
                        result = c.fetchone()
                        if result:
                            genre_id = result[0]
                        else:
                            c.execute("INSERT INTO genres_normalized (name) VALUES (?)", (genre,))
                            genre_id = c.lastrowid
                        
                        # Crear relación
                        c.execute("""
                        INSERT OR IGNORE INTO artist_genres (artist_id, genre_id)
                        VALUES (?, ?)
                        """, (artist_id, genre_id))
            
            conn.commit()
            self.logger.info("Tablas normalizadas pobladas con éxito")
            
        except Exception as e:
            self.logger.error(f"Error al poblar tablas normalizadas: {str(e)}")
    
    def _parse_tags(self, tags):
        """
        Parse tags string into a list of genres.
        Handles various formats: comma-separated, JSON arrays, etc.
        """
        if not tags:
            return []
        
        # First, try to parse as JSON
        if tags.startswith('[') and tags.endswith(']'):
            try:
                import json
                return json.loads(tags)
            except:
                pass
        
        # Try different separators
        if ',' in tags:
            return [tag.strip() for tag in tags.split(',') if tag.strip()]
        elif ';' in tags:
            return [tag.strip() for tag in tags.split(';') if tag.strip()]
        elif '|' in tags:
            return [tag.strip() for tag in tags.split('|') if tag.strip()]
        
        # If no separator is found, treat as a single tag
        return [tags.strip()] if tags.strip() else []
    
    def create_useful_triggers(self):
        """
        Crea triggers útiles para mantener la integridad y actualizar 
        automáticamente columnas desnormalizadas.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            self.logger.info("Creando triggers útiles...")
            
            # Trigger para actualizar has_lyrics cuando se inserta o elimina una letra
            triggers = [
                # Cuando se añade una nueva letra
                """
                CREATE TRIGGER IF NOT EXISTS lyrics_after_insert
                AFTER INSERT ON lyrics
                BEGIN
                    UPDATE songs SET has_lyrics = 1 WHERE id = NEW.track_id;
                END;
                """,
                
                # Cuando se elimina una letra
                """
                CREATE TRIGGER IF NOT EXISTS lyrics_after_delete
                AFTER DELETE ON lyrics
                BEGIN
                    UPDATE songs SET has_lyrics = 0 WHERE id = OLD.track_id;
                END;
                """,
                
                # Cuando se actualiza un álbum, actualizar album_year en canciones
                """
                CREATE TRIGGER IF NOT EXISTS albums_after_update_year
                AFTER UPDATE OF year ON albums
                BEGIN
                    UPDATE songs SET album_year = NEW.year WHERE album = NEW.name;
                END;
                """,
                
                # Cuando se actualiza un artista, actualizar artist_origin en canciones
                """
                CREATE TRIGGER IF NOT EXISTS artists_after_update_origin
                AFTER UPDATE OF origin ON artists
                BEGIN
                    UPDATE songs SET artist_origin = NEW.origin WHERE artist = NEW.name;
                END;
                """,
                
                # Cuando se actualiza la ruta de portada de álbum
                """
                CREATE TRIGGER IF NOT EXISTS albums_after_update_art
                AFTER UPDATE OF album_art_path ON albums
                BEGIN
                    UPDATE songs SET album_art_path_denorm = NEW.album_art_path WHERE album = NEW.name;
                END;
                """,
                
                # Cuando se actualiza el sello discográfico
                """
                CREATE TRIGGER IF NOT EXISTS albums_after_update_label
                AFTER UPDATE OF label ON albums
                BEGIN
                    UPDATE songs SET album_label = NEW.label WHERE album = NEW.name;
                END;
                """,
                
                # Actualizar década cuando cambia el año del álbum
                """
                CREATE TRIGGER IF NOT EXISTS albums_after_update_year_decade
                AFTER UPDATE OF year ON albums
                BEGIN
                    UPDATE albums 
                    SET decade_id = (
                        SELECT id FROM decades 
                        WHERE decade = CAST(SUBSTR(NEW.year, 1, 3) || '0' AS INTEGER)
                    )
                    WHERE id = NEW.id AND NEW.year IS NOT NULL AND NEW.year != '';
                    
                    UPDATE songs 
                    SET decade = CAST(SUBSTR(NEW.year, 1, 3) || '0' AS INTEGER)
                    WHERE album = NEW.name;
                END;
                """
            ]
            
            for trigger in triggers:
                try:
                    c.execute(trigger)
                    self.logger.info(f"Trigger creado correctamente")
                except sqlite3.Error as e:
                    self.logger.warning(f"No se pudo crear el trigger: {str(e)}")
            
            conn.commit()
            self.logger.info("Triggers creados con éxito")
            
        except Exception as e:
            self.logger.error(f"Error al crear triggers: {str(e)}")
        
        finally:
            conn.close()
    
    def run_query_optimization(self):
        """Ejecuta todo el proceso de optimización para consultas."""
        backup_path = self.backup_database()
        
        try:
            self.logger.info("Iniciando proceso de optimización para CONSULTAS...")
            
            # Paso 1: Configuraciones de SQLite para lectura
            self.optimize_for_reading()
            
            # Paso 2: Crear tablas normalizadas
            self.create_normalized_tables()
            
            # Paso 3: Crear índices avanzados
            self.create_advanced_indices()
            
            # Paso 4: Añadir columnas desnormalizadas
            self.add_denormalized_columns()
            
            # Paso 5: Configurar búsqueda de texto completo
            self.create_full_text_search()
            
            # Paso 6: Crear triggers útiles
            self.create_useful_triggers()
            
            # Compactar y analizar la base de datos
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("VACUUM")
            c.execute("ANALYZE")
            conn.close()
            
            self.logger.info("¡Proceso de optimización para CONSULTAS completado con éxito!")
            self.logger.info("""
            CONSEJOS DE USO:
            - Para búsquedas de texto rápidas, usa las tablas virtuales '_fts': 
              SELECT * FROM songs WHERE id IN (SELECT id FROM song_fts WHERE song_fts MATCH 'palabra_clave')
              
            - Utiliza las vistas 'view_song_details', 'view_album_stats', 'view_artist_stats', 
              'view_label_stats' y 'view_country_stats' para consultas comunes
              
            - Aprovecha las columnas desnormalizadas para consultas más rápidas:
              - album_year
              - artist_origin
              - album_art_path_denorm
              - has_lyrics
              - album_label
              - decade
            
            - Tablas normalizadas:
              - genres_normalized: Para consultas relacionadas con géneros
              - countries: Normaliza países para estadísticas
              - decades: Facilita consultas por década
              
            - Búsqueda avanzada:
              - song_fts: Búsqueda de texto completo en canciones
              - artist_fts: Búsqueda de texto completo en artistas
              - album_fts: Búsqueda de texto completo en álbumes
              - lyrics_fts: Búsqueda de texto completo en letras
            """)
            
            return True
        except Exception as e:
            self.logger.error(f"Error durante la optimización: {str(e)}")
            
            if backup_path:
                self.logger.info(f"Restaurando base de datos desde la copia de seguridad: {backup_path}")
                shutil.copy2(backup_path, self.db_path)
            
            return False


def main():
    parser = argparse.ArgumentParser(description='Optimizador de consultas para base de datos de música')
    parser.add_argument('--db_path', required=False, help='Ruta al archivo de base de datos SQLite')
    parser.add_argument('--config', required=False, help='Archivo de configuración JSON')
    parser.add_argument('--no-backup', action='store_true', help='No crear copia de seguridad antes de optimizar')
    args = parser.parse_args()
    
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config_data = json.load(f)
                
            # Combinar configuraciones
            config.update(config_data.get("common", {}))
            config.update(config_data.get("optimiza_db_lastpass", {}))
        except Exception as e:
            print(f"Error al cargar el archivo de configuración: {e}")
    
    db_path = args.db_path or config.get('db_path')
    
    if not db_path:
        db_path = input("Ingresa la ruta completa a tu base de datos SQLite: ")
    
    if os.path.exists(db_path):
        optimizer = QueryOptimizer(db_path, backup=not args.no_backup)
        optimizer.run_query_optimization()
    else:
        print(f"El archivo {db_path} no existe.")


if __name__ == "__main__":
    main()