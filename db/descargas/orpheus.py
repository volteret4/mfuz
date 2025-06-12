#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
import requests
import time
import json
import logging
from datetime import datetime
from pathlib import Path

# Agregar el directorio padre al path para importar BaseModule
sys.path.append(str(Path(__file__).parent.parent))
from base_module import BaseModule, PROJECT_ROOT

class OrpheusTorrentsModule:
    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}
        self.session = requests.Session()
        self.setup_logging()
        self.authenticated = False
        
        # Configuración por defecto
        self.db_path = self.config.get('db_path', '')
        self.orpheus_url = self.config.get('orpheus_url', 'https://orpheus.network')
        self.username = self.config.get('orpheus_username', '')
        self.password = self.config.get('orpheus_password', '')
        self.api_token = self.config.get('orpheus_api_token', '')
        self.rate_limit = self.config.get('rate_limit', 2.1)  # Respetando el límite de 5 req/10s
        self.force_update = self.config.get('force_update', False)
        self.limit = self.config.get('limit', 0)  # 0 = sin límite
        
        self.last_request_time = 0
        
    def setup_logging(self):
        """Configura el logging"""
        log_level = self.config.get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def authenticate(self):
        """Autentica con Orpheus Network usando token API o credenciales"""
        if self.api_token:
            # Usar token API
            self.session.headers.update({
                'Authorization': f'token {self.api_token}',
                'User-Agent': 'MusicDatabase/1.0 (orpheus torrent collector)'
            })
            self.logger.info("Usando autenticación por token API")
        elif self.username and self.password:
            # Usar login con usuario/contraseña
            login_url = f"{self.orpheus_url}/login.php"
            login_data = {
                'username': self.username,
                'password': self.password
            }
            
            try:
                response = self.session.post(login_url, data=login_data)
                if response.status_code == 200 and 'index.php' in response.url:
                    self.logger.info("Autenticación exitosa con usuario/contraseña")
                else:
                    raise Exception("Error en la autenticación")
            except Exception as e:
                self.logger.error(f"Error al autenticar: {e}")
                return False
        else:
            self.logger.error("No se proporcionaron credenciales de autenticación")
            return False
            
        self.authenticated = True
        return True

    def rate_limit_request(self):
        """Implementa el rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()

    

    def search_artist_discography(self, artist_name):
        """Busca la discografía completa de un artista en Orpheus"""
        if not self.authenticated:
            if not self.authenticate():
                return None

        self.rate_limit_request()
        
        # Buscar por artista para obtener toda su discografía
        search_url = f"{self.orpheus_url}/ajax.php"
        params = {
            'action': 'artist',
            'artistname': artist_name
        }
        
        try:
            response = self.session.get(search_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'success':
                return data.get('response', {})
            else:
                # Si no funciona la búsqueda por artista, intentar búsqueda general
                return self.search_artist_general(artist_name)
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error en la petición para artista {artist_name}: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Error al decodificar JSON para artista {artist_name}: {e}")
            return None
    def search_artist_torrents(self, artist_name):
        """Busca todos los torrents disponibles para un artista en Orpheus"""
        if not self.authenticated:
            if not self.authenticate():
                return None

        self.rate_limit_request()
        
        search_url = f"{self.orpheus_url}/ajax.php"
        params = {
            'action': 'browse',
            'searchstr': artist_name
        }
        
        try:
            response = self.session.get(search_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'success':
                return data.get('response', {})
            else:
                self.logger.warning(f"Búsqueda sin resultados para artista: {artist_name}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error en la petición para {artist_name}: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Error al decodificar JSON para {artist_name}: {e}")
            return None


    def get_artists_to_search(self):
        """Obtiene artistas únicos de musicbrainz_discography para buscar"""
        query = """
        SELECT DISTINCT 
            md.artist_id,
            a.name as artist_name
        FROM musicbrainz_discography md
        JOIN artists a ON md.artist_id = a.id
        LEFT JOIN orpheus_torrents ot ON md.artist_id = ot.artist_id
        WHERE (ot.id IS NULL OR ?) 
            AND a.name IS NOT NULL
            AND a.name NOT IN ('various artists', 'varios artistas', 'v.a.', 'compilation')
        ORDER BY a.name
        """
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(query, (self.force_update,))
            results = cursor.fetchall()
            
        self.logger.info(f"Encontrados {len(results)} artistas para buscar")
        return results


    def get_artist_albums_from_db(self, artist_id):
        """Obtiene todos los álbumes de un artista desde musicbrainz_discography"""
        query = """
        SELECT 
            md.album_id,
            md.title as album_name,
            md.mbid,
            md.first_release_date,
            md.release_type
        FROM musicbrainz_discography md
        WHERE md.artist_id = ?
            AND md.title IS NOT NULL
            AND md.title != ''
        ORDER BY md.first_release_date, md.title
        """
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(query, (artist_id,))
            return cursor.fetchall()
    def normalize_album_name(self, album_name):
        """Normaliza nombres de álbumes para mejor matching"""
        import re
        if not album_name:
            return ""
        
        # Convertir a minúsculas
        normalized = album_name.lower().strip()
        
        # Remover caracteres especiales y espacios extra
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remover palabras comunes que pueden diferir
        common_words = ['the', 'a', 'an', 'remaster', 'remastered', 'deluxe', 'edition', 'ep', 'lp']
        words = normalized.split()
        words = [w for w in words if w not in common_words]
        
        return ' '.join(words)

    def match_albums(self, orpheus_albums, db_albums):
        """Hace matching entre álbumes de Orpheus y la base de datos local"""
        matches = []
        
        # Crear diccionarios normalizados para matching
        db_normalized = {}
        for album in db_albums:
            album_id, album_name, mbid, release_date, release_type = album
            normalized_name = self.normalize_album_name(album_name)
            if normalized_name:
                db_normalized[normalized_name] = album
        
        # Buscar matches en Orpheus
        for orpheus_album in orpheus_albums:
            group_info = orpheus_album.get('group', {})
            orpheus_name = group_info.get('groupName', '')
            orpheus_year = group_info.get('groupYear', 0)
            
            normalized_orpheus = self.normalize_album_name(orpheus_name)
            
            if normalized_orpheus in db_normalized:
                db_album = db_normalized[normalized_orpheus]
                matches.append({
                    'orpheus_data': orpheus_album,
                    'db_data': db_album,
                    'match_confidence': 'exact'
                })
            else:
                # Búsqueda fuzzy para matches parciales
                best_match = self.find_fuzzy_match(normalized_orpheus, db_normalized)
                if best_match:
                    matches.append({
                        'orpheus_data': orpheus_album,
                        'db_data': best_match,
                        'match_confidence': 'fuzzy'
                    })
        
        return matches

    def find_fuzzy_match(self, target, candidates, threshold=0.8):
        """Encuentra el mejor match usando similitud de strings"""
        from difflib import SequenceMatcher
        
        best_match = None
        best_score = 0
        
        for candidate_name, candidate_data in candidates.items():
            score = SequenceMatcher(None, target, candidate_name).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate_data
        
        return best_match


    def create_orpheus_torrents_table(self):
        """Crea la tabla para almacenar información de torrents de Orpheus"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS orpheus_torrents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER,
            album_id INTEGER,
            musicbrainz_discography_id INTEGER,
            artist_name TEXT,
            album_name TEXT,
            torrent_name TEXT,
            torrent_id INTEGER,
            group_id INTEGER,
            post_url TEXT,
            torrent_url TEXT,
            media TEXT,
            format TEXT,
            encoding TEXT,
            size INTEGER,
            seeders INTEGER,
            leechers INTEGER,
            snatched INTEGER,
            year INTEGER,
            record_label TEXT,
            catalogue_number TEXT,
            scene BOOLEAN,
            has_log BOOLEAN,
            has_cue BOOLEAN,
            log_score INTEGER,
            freeTorrent BOOLEAN,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists (id),
            FOREIGN KEY (album_id) REFERENCES albums (id),
            FOREIGN KEY (musicbrainz_discography_id) REFERENCES musicbrainz_discography (id),
            UNIQUE(torrent_id)
        )
        """
        
        with self.get_db_connection() as conn:
            conn.execute(create_table_sql)
            conn.commit()
            self.logger.info("Tabla orpheus_torrents creada/verificada")



    def get_db_connection(self):
        """
        Obtener conexión a la base de datos
        
        Returns:
            Connection: Objeto de conexión SQLite o None si hay error
        """
        try:
            # Buscar la base de datos en varias ubicaciones posibles
            db_paths = [
                self.db_path,
                Path(PROJECT_ROOT) / "db" / "sqlite" / "musica.sqlite",
                Path(PROJECT_ROOT) / ".content" / "database" / "musica.sqlite",
                Path(PROJECT_ROOT) / "music.db"
            ]
            
            for db_path in db_paths:
                if os.path.exists(str(db_path)):
                    return sqlite3.connect(str(db_path))
            
            print(f"Base de datos no encontrada en ninguna ubicación")
            return None
        except Exception as e:
            print(f"Error conectando a la base de datos: {str(e)}")
            return None

 
    def calculate_tokens_needed(self, size_bytes):
        """Calcula el número de tokens necesarios basado en el tamaño del archivo"""
        if not size_bytes or size_bytes == 0:
            return 1  # Mínimo 1 token
        
        # 1 token por cada 512MB (536870912 bytes)
        token_size = 512 * 1024 * 1024  # 512MB en bytes
        tokens_needed = max(1, (size_bytes + token_size - 1) // token_size)  # Redondeo hacia arriba
        return tokens_needed

    def build_torrent_download_url(self, torrent_id, size_bytes=0):
        """Construye la URL de descarga del torrent con tokens si es necesario"""
        base_url = f"{self.orpheus_url}/torrents.php?action=download&id={torrent_id}"
        
        if self.api_token:
            base_url += f"&api_token={self.api_token}"
            
            # Calcular tokens necesarios
            tokens_needed = self.calculate_tokens_needed(size_bytes)
            if tokens_needed > 0:
                base_url += f"&usetoken={tokens_needed}"
        
        return base_url

    def find_matching_albums(self, artist_id, orpheus_album_name, orpheus_year):
        """Encuentra álbumes coincidentes en musicbrainz_discography y albums"""
        import re
        
        def normalize_title(title):
            """Normaliza título para comparación"""
            if not title:
                return ""
            # Convertir a minúsculas, quitar acentos y caracteres especiales
            normalized = re.sub(r'[^\w\s]', '', title.lower())
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            return normalized
        
        orpheus_normalized = normalize_title(orpheus_album_name)
        
        with self.get_db_connection() as conn:
            # Buscar en musicbrainz_discography con diferentes niveles de coincidencia
            mb_query = """
            SELECT id, album_id, title, first_release_date
            FROM musicbrainz_discography 
            WHERE artist_id = ?
            ORDER BY 
                CASE 
                    WHEN LOWER(title) = LOWER(?) THEN 1
                    WHEN LOWER(title) LIKE LOWER(?) THEN 2
                    ELSE 3
                END,
                ABS(CAST(SUBSTR(first_release_date, 1, 4) AS INTEGER) - ?) ASC
            """
            
            cursor = conn.execute(mb_query, (
                artist_id, 
                orpheus_album_name, 
                f"%{orpheus_album_name}%",
                orpheus_year or 0
            ))
            mb_results = cursor.fetchall()
            
            # Buscar en albums también
            album_query = """
            SELECT id, name, year
            FROM albums 
            WHERE artist_id = ?
            ORDER BY 
                CASE 
                    WHEN LOWER(name) = LOWER(?) THEN 1
                    WHEN LOWER(name) LIKE LOWER(?) THEN 2
                    ELSE 3
                END,
                ABS(COALESCE(CAST(year AS INTEGER), 0) - ?) ASC
            """
            
            cursor = conn.execute(album_query, (
                artist_id, 
                orpheus_album_name, 
                f"%{orpheus_album_name}%",
                orpheus_year or 0
            ))
            album_results = cursor.fetchall()
            
        # Encontrar la mejor coincidencia
        mb_discography_id = None
        album_id = None
        
        # Buscar en musicbrainz_discography
        for mb_id, mb_album_id, mb_title, mb_date in mb_results:
            mb_normalized = normalize_title(mb_title)
            
            # Coincidencia exacta
            if mb_normalized == orpheus_normalized:
                mb_discography_id = mb_id
                if mb_album_id:
                    album_id = mb_album_id
                break
            
            # Coincidencia parcial con umbral de similitud
            if (orpheus_normalized in mb_normalized or 
                mb_normalized in orpheus_normalized):
                # Verificar que la similitud sea razonable
                similarity = len(set(orpheus_normalized.split()) & set(mb_normalized.split()))
                if similarity >= 1:  # Al menos una palabra en común
                    mb_discography_id = mb_id
                    if mb_album_id:
                        album_id = mb_album_id
                    break
        
        # Si no encontramos album_id desde musicbrainz_discography, buscar en albums directamente
        if not album_id:
            for alb_id, alb_name, alb_year in album_results:
                alb_normalized = normalize_title(alb_name)
                
                if alb_normalized == orpheus_normalized:
                    album_id = alb_id
                    break
                    
                if (orpheus_normalized in alb_normalized or 
                    alb_normalized in orpheus_normalized):
                    similarity = len(set(orpheus_normalized.split()) & set(alb_normalized.split()))
                    if similarity >= 1:
                        album_id = alb_id
                        break
            
        return mb_discography_id, album_id   


    def save_torrent_data(self, artist_id, artist_name, search_results):
        """Guarda los datos de torrents encontrados para un artista"""
        if not search_results or 'results' not in search_results:
            return 0
            
        saved_count = 0
        
        with self.get_db_connection() as conn:
            for result in search_results['results']:
                # En la API de Gazelle, la estructura puede variar
                # Intentar obtener group_id de diferentes ubicaciones
                group_id = None
                group_info = {}
                
                if 'groupId' in result:
                    group_id = result['groupId']
                    group_info = result
                elif 'group' in result:
                    group_info = result['group']
                    group_id = group_info.get('groupId') or group_info.get('id')
                
                if not group_id:
                    self.logger.warning(f"No se pudo obtener group_id para resultado: {result.keys()}")
                    continue
                
                # Información del grupo/álbum
                group_name = group_info.get('groupName', '') or group_info.get('name', '')
                group_year = group_info.get('groupYear', 0) or group_info.get('year', 0)
                record_label = group_info.get('recordLabel', '') or group_info.get('label', '')
                catalogue_number = group_info.get('catalogueNumber', '') or group_info.get('catNumber', '')
                
                # Buscar coincidencias en nuestras tablas
                mb_discography_id, album_id = self.find_matching_albums(
                    artist_id, group_name, group_year
                )
                
                # Los torrents pueden estar en 'torrents' o directamente en el resultado
                torrents_list = []
                if 'torrents' in result:
                    torrents_list = result['torrents']
                elif 'torrent' in result:
                    torrents_list = [result['torrent']]
                else:
                    # Si no hay lista de torrents, tratar el resultado como un torrent individual
                    torrents_list = [result]
                
                # Procesar cada torrent en el grupo
                for torrent in torrents_list:
                    torrent_id = torrent.get('torrentId') or torrent.get('id')
                    
                    if not torrent_id:
                        self.logger.warning(f"No se pudo obtener torrent_id para: {torrent.keys()}")
                        continue
                        
                    # Verificar si ya existe este torrent
                    cursor = conn.execute(
                        "SELECT id FROM orpheus_torrents WHERE torrent_id = ?", 
                        (torrent_id,)
                    )
                    if cursor.fetchone() and not self.force_update:
                        continue
                        
                    # URL del post y del torrent
                    post_url = f"{self.orpheus_url}/torrents.php?id={group_id}"
                    torrent_url = f"{self.orpheus_url}/torrents.php?action=download&id={torrent_id}"
                    
                    # Nombre del torrent
                    format_str = torrent.get('format', '') or torrent.get('encoding', '')
                    encoding_str = torrent.get('encoding', '') or torrent.get('bitrate', '')
                    torrent_name = f"{artist_name} - {group_name} ({group_year}) [{format_str} {encoding_str}]".strip()
                    
                    insert_sql = """
                    INSERT OR REPLACE INTO orpheus_torrents (
                        artist_id, album_id, musicbrainz_discography_id,
                        artist_name, album_name, torrent_name, 
                        torrent_id, group_id, post_url, torrent_url,
                        media, format, encoding, size,
                        seeders, leechers, snatched,
                        year, record_label, catalogue_number,
                        scene, has_log, has_cue, log_score, freeTorrent,
                        last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    values = (
                        artist_id, album_id, mb_discography_id,
                        artist_name, group_name, torrent_name,
                        torrent_id, group_id, post_url, torrent_url,
                        torrent.get('media', ''),
                        torrent.get('format', ''),
                        torrent.get('encoding', ''),
                        torrent.get('size', 0),
                        torrent.get('seeders', 0),
                        torrent.get('leechers', 0),
                        torrent.get('snatched', 0),
                        group_year,
                        record_label,
                        catalogue_number,
                        torrent.get('scene', False),
                        torrent.get('hasLog', False),
                        torrent.get('hasCue', False),
                        torrent.get('logScore', 0),
                        torrent.get('freeTorrent', False),
                        datetime.now()
                    )
                    
                    try:
                        conn.execute(insert_sql, values)
                        saved_count += 1
                        
                        self.logger.debug(f"Guardado torrent {torrent_id} para {group_name} (group_id: {group_id})")
                        
                        if mb_discography_id:
                            self.logger.debug(f"Mapeado torrent {torrent_id} con musicbrainz_discography.id={mb_discography_id}")
                        if album_id:
                            self.logger.debug(f"Mapeado torrent {torrent_id} con albums.id={album_id}")
                            
                    except sqlite3.Error as e:
                        self.logger.error(f"Error al guardar torrent {torrent_id}: {e}")
                        
            conn.commit()
            
        return saved_count

    def process_artists(self):
        """Procesa todos los artistas y busca sus torrents disponibles"""
        artists = self.get_artists_to_search()
        
        if not artists:
            self.logger.info("No hay artistas para procesar")
            return
            
        # Aplicar límite si está configurado
        if self.limit > 0:
            artists = artists[:self.limit]
            self.logger.info(f"Limitando búsqueda a {self.limit} artistas")
            
        total_found = 0
        processed = 0
        
        for artist in artists:
            artist_id, artist_name = artist
            
            self.logger.info(f"Buscando torrents para: {artist_name}")
            
            search_results = self.search_artist_torrents(artist_name)
            
            if search_results:
                saved = self.save_torrent_data(artist_id, artist_name, search_results)
                total_found += saved
                if saved > 0:
                    self.logger.info(f"Encontrados {saved} torrents para {artist_name}")
                else:
                    self.logger.info(f"Sin torrents nuevos para {artist_name}")
            else:
                self.logger.info(f"Sin resultados en Orpheus para {artist_name}")
            
            processed += 1
            
            if processed % 10 == 0:
                self.logger.info(f"Progreso: {processed}/{len(artists)} artistas procesados, {total_found} torrents encontrados")
                
        self.logger.info(f"Proceso completado: {processed} artistas procesados, {total_found} torrents encontrados en total")


    def process_albums(self):
        """Procesa artistas completos en lugar de álbumes individuales"""
        artists = self.get_artists_to_search()
        
        if not artists:
            self.logger.info("No hay artistas para procesar")
            return
            
        # Aplicar límite si está configurado
        if self.limit > 0:
            artists = artists[:self.limit]
            self.logger.info(f"Limitando búsqueda a {self.limit} artistas")
            
        total_found = 0
        processed = 0
        
        for artist_data in artists:
            artist_id, artist_name, album_count = artist_data
            
            self.logger.info(f"Procesando artista: {artist_name} ({album_count} álbumes en DB)")
            
            # Obtener discografía completa del artista en Orpheus
            orpheus_results = self.search_artist_discography(artist_name)
            
            if not orpheus_results or 'results' not in orpheus_results:
                self.logger.warning(f"No se encontró discografía para {artist_name}")
                processed += 1
                continue
            
            # Obtener álbumes del artista desde la base de datos
            db_albums = self.get_artist_albums_from_db(artist_id)
            
            if not db_albums:
                self.logger.warning(f"No hay álbumes en DB para {artist_name}")
                processed += 1
                continue
            
            # Hacer matching entre Orpheus y DB
            matches = self.match_albums(orpheus_results['results'], db_albums)
            
            if matches:
                saved = self.save_matched_torrents(artist_id, artist_name, matches)
                total_found += saved
                self.logger.info(f"Procesado {artist_name}: {len(matches)} matches, {saved} torrents guardados")
            else:
                self.logger.info(f"No se encontraron matches para {artist_name}")
            
            processed += 1
            
            if processed % 10 == 0:
                self.logger.info(f"Progreso: {processed}/{len(artists)} artistas procesados, {total_found} torrents encontrados")
                
        self.logger.info(f"Proceso completado: {processed} artistas procesados, {total_found} torrents encontrados en total")

    def get_statistics(self):
        """Obtiene estadísticas de la tabla orpheus_torrents"""
        with self.get_db_connection() as conn:
            stats_query = """
            SELECT 
                COUNT(*) as total_torrents,
                COUNT(DISTINCT artist_id) as unique_artists,
                COUNT(DISTINCT album_id) as unique_albums,
                COUNT(DISTINCT group_id) as unique_groups,
                COUNT(DISTINCT musicbrainz_discography_id) as mapped_mb_albums,
                AVG(seeders) as avg_seeders,
                COUNT(CASE WHEN freeTorrent = 1 THEN 1 END) as free_torrents,
                COUNT(CASE WHEN album_id IS NOT NULL THEN 1 END) as with_local_album,
                COUNT(CASE WHEN musicbrainz_discography_id IS NOT NULL THEN 1 END) as with_mb_mapping
            FROM orpheus_torrents
            """
            cursor = conn.execute(stats_query)
            stats = cursor.fetchone()
            
        self.logger.info("=== Estadísticas de Orpheus Torrents ===")
        self.logger.info(f"Total de torrents: {stats[0]}")
        self.logger.info(f"Artistas únicos: {stats[1]}")
        self.logger.info(f"Álbumes únicos: {stats[2]}")
        self.logger.info(f"Grupos únicos: {stats[3]}")
        self.logger.info(f"Álbumes mapeados con MusicBrainz: {stats[4]}")
        self.logger.info(f"Promedio de seeders: {stats[5]:.2f}")
        self.logger.info(f"Torrents gratuitos: {stats[6]}")
        self.logger.info(f"Con álbum local: {stats[7]}")
        self.logger.info(f"Con mapeo MusicBrainz: {stats[8]}")

def main(config=None):
    """Función principal del script"""
    try:
        module = OrpheusTorrentsModule(config)
        
        # Verificar credenciales
        if not module.api_token and not (module.username and module.password):
            print("Error: Se requieren credenciales de Orpheus Network")
            print("Configura 'orpheus_api_token' o 'orpheus_username' y 'orpheus_password'")
            return 1
            
        # Crear tabla si no existe
        module.create_orpheus_torrents_table()
        
        # Procesar artistas
        module.process_artists()
        
        # Mostrar estadísticas
        module.get_statistics()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario")
        return 1
    except Exception as e:
        print(f"Error en el proceso: {e}")
        return 1

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Busca torrents en Orpheus Network')
    parser.add_argument('--config', type=str, help='Archivo de configuración JSON')
    parser.add_argument('--username', type=str, help='Usuario de Orpheus')
    parser.add_argument('--password', type=str, help='Contraseña de Orpheus')
    parser.add_argument('--api-token', type=str, help='Token API de Orpheus')
    parser.add_argument('--limit', type=int, default=0, help='Límite de artistas a procesar')
    parser.add_argument('--force-update', action='store_true', help='Forzar actualización de existentes')
    
    args = parser.parse_args()
    
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Sobrescribir con argumentos de línea de comandos
    if args.username:
        config['orpheus_username'] = args.username
    if args.password:
        config['orpheus_password'] = args.password
    if args.api_token:
        config['orpheus_api_token'] = args.api_token
    if args.limit:
        config['limit'] = args.limit
    if args.force_update:
        config['force_update'] = True
        
    sys.exit(main(config))