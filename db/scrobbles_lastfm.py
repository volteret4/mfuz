#!/usr/bin/env python3
import sqlite3
import requests
import json
import argparse
import json
import datetime
import time
import os
from pathlib import Path
import musicbrainzngs

INTERACTIVE_MODE = False  # This will be set by db_creator.py
FORCE_UPDATE = True  # This will be set by db_creator.py

# Variable global para el caché (inicializar en setup_musicbrainz)
mb_cache = None
lastfm_cache = None



def update_artists_metadata(conn, lastfm_api_key, limit=50):
    """
    Actualiza la información de bio, tags y artistas similares para artistas que no tienen estos datos
    
    Args:
        conn: Conexión a la base de datos
        lastfm_api_key: API key de Last.fm
        limit: Número máximo de artistas a actualizar por ejecución
    """
    cursor = conn.cursor()
    
    # Verificar si existen las columnas necesarias
    cursor.execute("PRAGMA table_info(artists)")
    columns = [column[1] for column in cursor.fetchall()]
    
    query_parts = []
    if "bio" in columns:
        query_parts.append("bio IS NULL OR bio = ''")
    if "tags" in columns:
        query_parts.append("tags IS NULL OR tags = ''")
    if "similar_artists" in columns:
        query_parts.append("similar_artists IS NULL OR similar_artists = ''")
    
    if not query_parts:
        print("No hay columnas de metadatos para actualizar")
        return 0
    
    query = f"""
        SELECT id, name, mbid 
        FROM artists 
        WHERE {' OR '.join(query_parts)}
        LIMIT ?
    """
    
    cursor.execute(query, (limit,))
    artists_to_update = cursor.fetchall()
    
    if not artists_to_update:
        print("No hay artistas que necesiten actualización de metadatos")
        return 0
    
    print(f"Actualizando metadatos para {len(artists_to_update)} artistas")
    
    updated_count = 0
    for artist_id, artist_name, mbid in artists_to_update:
        print(f"Actualizando metadatos para {artist_name}")
        
        # Obtener información completa desde Last.fm
        artist_info = get_artist_info(artist_name, mbid, lastfm_api_key)
        
        if not artist_info:
            print(f"No se pudo obtener información para {artist_name}")
            continue
        
        # Preparar actualizaciones
        updates = []
        params = []
        
        # Bio
        if "bio" in columns and 'bio' in artist_info and 'content' in artist_info['bio']:
            bio = artist_info['bio']['content']
            if bio:
                updates.append("bio = ?")
                params.append(bio)
        
        # Tags
        if "tags" in columns and 'tags' in artist_info and 'tag' in artist_info['tags']:
            tag_list = artist_info['tags']['tag']
            tags = []
            if isinstance(tag_list, list):
                tags = [tag['name'] for tag in tag_list]
            else:
                tags = [tag_list['name']]
            
            tags_str = ','.join(tags)
            if tags_str:
                updates.append("tags = ?")
                params.append(tags_str)
        
        # Similar artists
        if "similar_artists" in columns and 'similar' in artist_info and 'artist' in artist_info['similar']:
            similar_list = artist_info['similar']['artist']
            similar_artists = []
            if isinstance(similar_list, list):
                similar_artists = [{'name': a['name'], 'url': a.get('url', '')} for a in similar_list]
            else:
                similar_artists = [{'name': similar_list['name'], 'url': similar_list.get('url', '')}]
            
            similar_json = json.dumps(similar_artists)
            updates.append("similar_artists = ?")
            params.append(similar_json)
        
        # URL de Last.fm
        if "lastfm_url" in columns and 'url' in artist_info:
            updates.append("lastfm_url = ?")
            params.append(artist_info['url'])
        elif "website" in columns and 'url' in artist_info:
            updates.append("website = ?")
            params.append(artist_info['url'])
        
        # Ejecutar actualización
        if updates:
            query = f"UPDATE artists SET {', '.join(updates)} WHERE id = ?"
            params.append(artist_id)
            
            try:
                cursor.execute(query, params)
                updated_count += 1
            except sqlite3.Error as e:
                print(f"Error al actualizar metadatos para {artist_name}: {e}")
    
    conn.commit()
    print(f"Actualizados metadatos para {updated_count} artistas")
    return updated_count



def setup_cache(cache_directory=None):
    """Configura el sistema de caché unificado con mejor manejo de errores"""
    global mb_cache, lastfm_cache
    
    # Inicializar caché (en memoria por defecto)
    if mb_cache is None:
        try:
            mb_cache = APICache(name="MusicBrainz", cache_duration=30)  # Mayor duración para MusicBrainz
        except Exception as e:
            print(f"Error inicializando caché MusicBrainz: {e}")
            mb_cache = APICache(name="MusicBrainz")  # Fallback con configuración por defecto
    
    if lastfm_cache is None:
        try:
            lastfm_cache = APICache(name="LastFM", cache_duration=7)  # 7 días para Last.fm
        except Exception as e:
            print(f"Error inicializando caché LastFM: {e}")
            lastfm_cache = APICache(name="LastFM")  # Fallback con configuración por defecto
    
    # Si se proporciona un directorio de caché, configurar persistencia
    if cache_directory:
        try:
            os.makedirs(cache_directory, exist_ok=True)
            
            mb_cache_file = os.path.join(cache_directory, "musicbrainz_cache.json")
            lastfm_cache_file = os.path.join(cache_directory, "lastfm_cache.json")
            
            print(f"Configurando caché en: {cache_directory}")
            print(f"Archivo de caché MusicBrainz: {mb_cache_file}")
            print(f"Archivo de caché Last.fm: {lastfm_cache_file}")
            
            # Crear nuevas instancias con archivos de caché
            try:
                mb_cache = APICache(name="MusicBrainz", cache_file=mb_cache_file, cache_duration=30)
                lastfm_cache = APICache(name="LastFM", cache_file=lastfm_cache_file, cache_duration=7)
                
                print(f"Caché configurada en: {cache_directory}")
                print(f"Entradas en caché MusicBrainz: {len(mb_cache.cache)}")
                print(f"Entradas en caché LastFM: {len(lastfm_cache.cache)}")
            except Exception as e:
                print(f"Error configurando caché con archivos: {e}")
                print("Usando caché en memoria en su lugar")
                
                # Si falla la carga desde archivos, reinicializar con cachés en memoria
                mb_cache = APICache(name="MusicBrainz", cache_duration=30)
                lastfm_cache = APICache(name="LastFM", cache_duration=7)
        except Exception as e:
            print(f"Error configurando caché persistente: {e}")
            print("Usando caché en memoria")
    else:
        print("Caché configurada en memoria (no persistente)")
    
    # Validar objetos de caché
    if not isinstance(mb_cache.cache, dict):
        print(f"Advertencia: Caché MusicBrainz es inválida. Reinicializando.")
        mb_cache.cache = {}
    
    if not isinstance(lastfm_cache.cache, dict):
        print(f"Advertencia: Caché LastFM es inválida. Reinicializando.")
        lastfm_cache.cache = {}

def get_artist_info(artist_name, mbid, lastfm_api_key):
    """
    Obtiene información detallada de un artista desde Last.fm, con mejor manejo de errores
    
    Args:
        artist_name: Nombre del artista
        mbid: MBID del artista (opcional)
        lastfm_api_key: API key de Last.fm
        
    Returns:
        Diccionario con información del artista o None si no se encuentra
    """
    global lastfm_cache
    
    # Validación mejorada de parámetros
    if not artist_name or not isinstance(artist_name, str):
        print(f"Error: Nombre de artista inválido: {repr(artist_name)}")
        return None
    
    if not lastfm_api_key or not isinstance(lastfm_api_key, str):
        print(f"Error: API key de Last.fm inválida")
        return None
    
    # Normalizar el nombre del artista (eliminar espacios extras, etc.)
    artist_name = artist_name.strip()
    
    # Crear clave de caché
    cache_key = {
        'method': 'artist.getInfo',
        'artist': artist_name,
    }
    if mbid:
        cache_key['mbid'] = mbid
    
    # Verificar en caché primero
    if lastfm_cache:
        cached_result = lastfm_cache.get(cache_key)
        if cached_result:
            print(f"Usando datos en caché para artista Last.fm: {artist_name}")
            return cached_result.get('artist')
    
    # Función para manejar reintentos
    def try_request(attempt=0, retry_count=2):
        try:
            # Construir parámetros de consulta
            params = {
                'method': 'artist.getInfo',
                'artist': artist_name,
                'api_key': lastfm_api_key,
                'format': 'json',
                'autocorrect': 1  # Activar corrección automática
            }
            
            if mbid:
                params['mbid'] = mbid
            
            print(f"Consultando Last.fm para artista: {artist_name} (intento {attempt+1}/{retry_count+1})")
            response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"Error HTTP en Last.fm: {response.status_code} - {response.reason}")
                if attempt < retry_count:
                    return try_request(attempt + 1)
                return None
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                print(f"Error al parsear respuesta JSON: {response.text[:200]}...")
                if attempt < retry_count:
                    return try_request(attempt + 1)
                return None
            
            # Verificar si hay error en la respuesta
            if 'error' in data:
                error_code = data.get('error', 0)
                error_msg = data.get('message', 'Error desconocido')
                print(f"Error de Last.fm [{error_code}]: {error_msg}")
                
                # Si el error es por artista no encontrado, intentar con nombre alternativo
                if error_code == 6 and attempt < retry_count:  # Artist not found
                    # Intentar buscar por nombre sin caracteres especiales
                    import unicodedata
                    import re
                    
                    # Normalizar eliminando acentos y caracteres especiales
                    normalized_name = unicodedata.normalize('NFKD', artist_name)
                    normalized_name = re.sub(r'[^\w\s]', '', normalized_name)
                    
                    if normalized_name != artist_name:
                        print(f"Reintentando con nombre normalizado: {normalized_name}")
                        params['artist'] = normalized_name
                        return try_request(attempt + 1)
                
                return None
            
            # Guardar en caché y devolver resultado
            if 'artist' in data:
                if lastfm_cache:
                    lastfm_cache.put(cache_key, data)
                return data['artist']
            
            print(f"Respuesta de Last.fm sin información de artista para {artist_name}")
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión a Last.fm: {e}")
            if attempt < retry_count:
                return try_request(attempt + 1)
            return None
    
    # Intentar obtener datos
    return try_request()



def create_optimized_indices(conn, lastfm_username=None):
    """
    Crea índices optimizados para consultas frecuentes, con soporte para tablas específicas de usuario
    
    Args:
        conn: Conexión a la base de datos
        lastfm_username: Nombre de usuario de Last.fm opcional para crear índices para tablas específicas
    
    Returns:
        Número de índices creados
    """
    cursor = conn.cursor()
    indices_created = 0
    
    # Índices básicos para todas las tablas
    basic_indices = [
        # Búsquedas de artistas (case-insensitive)
        "CREATE INDEX IF NOT EXISTS idx_artists_name_lower ON artists(lower(name))",
        "CREATE INDEX IF NOT EXISTS idx_albums_name_lower ON albums(lower(name))",
        "CREATE INDEX IF NOT EXISTS idx_songs_title_lower ON songs(lower(title))",
        
        # Búsquedas por MusicBrainz ID
        "CREATE INDEX IF NOT EXISTS idx_artists_mbid ON artists(mbid)",
        "CREATE INDEX IF NOT EXISTS idx_albums_mbid ON albums(mbid)",
        "CREATE INDEX IF NOT EXISTS idx_songs_mbid ON songs(mbid)",
        
        # Relaciones
        "CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums(artist_id)",
        "CREATE INDEX IF NOT EXISTS idx_songs_album_id ON songs(album_id)",
        "CREATE INDEX IF NOT EXISTS idx_songs_artist_name ON songs(artist)",
        
        # Búsquedas combinadas
        "CREATE INDEX IF NOT EXISTS idx_songs_artist_album ON songs(artist, album)",
        "CREATE INDEX IF NOT EXISTS idx_albums_artist_name ON albums(artist_id, lower(name))",
        
        # Para song_links
        "CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)",
        "CREATE INDEX IF NOT EXISTS idx_song_links_lastfm ON song_links(lastfm_url)",
        
        # Para géneros (útil para descubrimiento musical)
        "CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre)",
        "CREATE INDEX IF NOT EXISTS idx_artists_tags ON artists(tags)",
        
        # Para análisis por tiempo
        "CREATE INDEX IF NOT EXISTS idx_songs_added_timestamp ON songs(added_timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_songs_added_year_month ON songs(added_year, added_month)",
        "CREATE INDEX IF NOT EXISTS idx_songs_added_week ON songs(added_week)",
        
        # Para búsqueda de recién añadidos
        "CREATE INDEX IF NOT EXISTS idx_artists_origen ON artists(origen)",
        "CREATE INDEX IF NOT EXISTS idx_albums_origen ON albums(origen)",
        "CREATE INDEX IF NOT EXISTS idx_songs_origen ON songs(origen)",
        
        # Para MusicBrainz
        "CREATE INDEX IF NOT EXISTS idx_albums_musicbrainz_albumid ON albums(musicbrainz_albumid)",
        "CREATE INDEX IF NOT EXISTS idx_songs_musicbrainz_recordingid ON songs(musicbrainz_recordingid)",
    ]
    
    # Índices específicos de usuario si se proporciona nombre de usuario
    user_indices = []
    if lastfm_username:
        scrobbles_table = f"scrobbles_{lastfm_username}"
        
        user_indices = [
            # Para scrobbles
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_song_id ON {scrobbles_table}(song_id)",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_album_id ON {scrobbles_table}(album_id)",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_id ON {scrobbles_table}(artist_id)",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_timestamp ON {scrobbles_table}(timestamp)",
            
            # Para estadísticas
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_timestamp ON {scrobbles_table}(artist_id, timestamp)",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_album_timestamp ON {scrobbles_table}(album_id, timestamp)",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_date ON {scrobbles_table}(DATE(scrobble_date))",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_day_hour ON {scrobbles_table}(strftime('%w', scrobble_date), strftime('%H', scrobble_date))",
            
            # Búsquedas texto en scrobbles
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_track_name_lower ON {scrobbles_table}(lower(track_name))",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_name_lower ON {scrobbles_table}(lower(artist_name))",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_album_name_lower ON {scrobbles_table}(lower(album_name))",
            
            # Para análisis por año, mes, semana y día
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_year ON {scrobbles_table}(strftime('%Y', scrobble_date))",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_year_month ON {scrobbles_table}(strftime('%Y-%m', scrobble_date))",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_year_week ON {scrobbles_table}(strftime('%Y-%W', scrobble_date))",
            f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_year_day ON {scrobbles_table}(strftime('%Y-%j', scrobble_date))",
        ]
    
    # Lista combinada de índices
    all_indices = basic_indices + user_indices
    
    # Crear cada índice
    for index_sql in all_indices:
        try:
            cursor.execute(index_sql)
            indices_created += 1
            print(f"Índice creado: {index_sql}")
        except sqlite3.OperationalError as e:
            print(f"Error al crear índice: {e}")
    
    # Índices FTS para búsqueda de texto completo
    try:
        # Verificar si necesitamos crear índices FTS
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_fts'")
        if not cursor.fetchone():
            # Crear tabla FTS5 para búsqueda de texto completo
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS song_fts USING fts5(
                    id,
                    title,
                    artist,
                    album,
                    genre,
                    content=songs
                )
            """)
            
            # Poblar tabla FTS con datos existentes
            cursor.execute("""
                INSERT INTO song_fts(id, title, artist, album, genre)
                SELECT id, title, artist, album, genre FROM songs
            """)
            
            indices_created += 1
            print("Índice FTS5 creado para búsqueda de texto completo en canciones")
    except sqlite3.OperationalError as e:
        print(f"Error al crear índice FTS: {e} (SQLite puede no soportar FTS5)")
    
    # Trigger para mantener actualizado el índice FTS
    try:
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS songs_ai AFTER INSERT ON songs BEGIN
                INSERT INTO song_fts(id, title, artist, album, genre) 
                VALUES (new.id, new.title, new.artist, new.album, new.genre);
            END;
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS songs_au AFTER UPDATE ON songs BEGIN
                DELETE FROM song_fts WHERE id = old.id;
                INSERT INTO song_fts(id, title, artist, album, genre) 
                VALUES (new.id, new.title, new.artist, new.album, new.genre);
            END;
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS songs_ad AFTER DELETE ON songs BEGIN
                DELETE FROM song_fts WHERE id = old.id;
            END;
        """)
        
        indices_created += 3
        print("Triggers creados para mantener actualizado el índice FTS")
    except sqlite3.OperationalError as e:
        print(f"Error al crear triggers para FTS: {e}")
    
    # Commit para guardar cambios
    conn.commit()
    
    return indices_created


def create_basic_artist(conn, artist_name, mbid=None, lastfm_user="usuario"):
    """
    Crea un artista con información básica cuando no se puede obtener de Last.fm
    
    Args:
        conn: Conexión a la base de datos
        artist_name: Nombre del artista
        mbid: MBID opcional
        lastfm_user: Usuario de Last.fm para el origen
        
    Returns:
        ID del artista creado o None si falla
    """
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO artists (name, mbid, origen)
            VALUES (?, ?, ?)
            RETURNING id
        """, (artist_name, mbid, f"scrobbles_{lastfm_user}"))
        
        artist_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Artista básico creado: {artist_name} (ID: {artist_id})")
        return artist_id
    except sqlite3.Error as e:
        print(f"Error al crear artista básico {artist_name}: {e}")
        return None


def handle_force_update(db_path, lastfm_username):
    """
    Función crítica: Se ejecuta al principio del módulo para asegurar que force_update funcione
    
    Args:
        db_path: Ruta al archivo de base de datos
        lastfm_username: Nombre de usuario de Last.fm para personalizar la tabla
    """
    global FORCE_UPDATE
    if not FORCE_UPDATE or not db_path or not lastfm_username:
        return
        
    print("\n" + "!"*80)
    print(f"MODO FORCE_UPDATE ACTIVADO: Eliminando todos los scrobbles existentes para {lastfm_username}")
    print("!"*80 + "\n")
    
    try:
        # Conectar directamente a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Nombre de la tabla de scrobbles personalizada
        scrobbles_table = f"scrobbles_{lastfm_username}"
        
        # Verificar si existe la tabla
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{scrobbles_table}'")
        if cursor.fetchone():
            # Eliminar datos
            cursor.execute(f"DELETE FROM {scrobbles_table}")
            # Restablecer el timestamp
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lastfm_config'")
            if cursor.fetchone():
                cursor.execute("UPDATE lastfm_config SET last_timestamp = 0 WHERE id = 1")
            
            conn.commit()
            print(f"Base de datos limpiada exitosamente: {db_path}")
            print(f"Se han eliminado todos los scrobbles de {lastfm_username}. Se realizará una actualización completa.\n")
        else:
            print(f"La tabla '{scrobbles_table}' no existe aún en la base de datos: {db_path}")
        
        conn.close()
    except Exception as e:
        print(f"Error al intentar limpiar la base de datos: {e}")









def filter_duplicate_scrobbles(tracks):
    """
    Filtra scrobbles duplicados de Last.fm basándose en la misma canción y artista
    Prioriza mantener el scrobble más reciente
    
    Args:
        tracks: Lista de scrobbles obtenidos de Last.fm
        
    Returns:
        Lista filtrada sin duplicados
    """
    if not tracks:
        return []
    
    # Usaremos un diccionario para mantener solo el scrobble más reciente
    # para cada combinación única de artista+canción
    unique_tracks = {}
    
    # Ordenar por timestamp descendente (más recientes primero)
    sorted_tracks = sorted(tracks, key=lambda x: int(x['date']['uts']), reverse=True)
    
    for track in sorted_tracks:
        # Crear una clave única para esta canción+artista
        key = (track['artist']['#text'].lower(), track['name'].lower())
        
        # Solo guardar si es la primera vez que vemos esta combinación
        # (que será la más reciente debido al orden)
        if key not in unique_tracks:
            unique_tracks[key] = track
    
    # Convertir el diccionario de nuevo a lista
    filtered_tracks = list(unique_tracks.values())
    
    # Re-ordenar por timestamp ascendente para procesamiento cronológico
    filtered_tracks.sort(key=lambda x: int(x['date']['uts']))
    
    print(f"Filtrados {len(tracks) - len(filtered_tracks)} scrobbles duplicados")
    print(f"Total de scrobbles únicos: {len(filtered_tracks)}")
    
    return filtered_tracks





def update_album_details_from_musicbrainz(conn, album_id, mbid=None):
    """
    Actualiza los detalles del álbum con información completa de MusicBrainz
    
    Args:
        conn: Conexión a la base de datos
        album_id: ID del álbum a actualizar
        mbid: MusicBrainz ID opcional, si ya se conoce
    
    Returns:
        True si se actualizó correctamente, False en caso contrario
    """
    cursor = conn.cursor()
    
    # Primero obtener información básica del álbum
    cursor.execute("""
        SELECT a.name, a.mbid, ar.name 
        FROM albums a
        JOIN artists ar ON a.artist_id = ar.id
        WHERE a.id = ?
    """, (album_id,))
    
    result = cursor.fetchone()
    if not result:
        print(f"No se encontró álbum con ID {album_id}")
        return False
    
    album_name, album_mbid, artist_name = result
    mbid_to_use = mbid if mbid else album_mbid
    
    if not mbid_to_use:
        print(f"No hay MBID disponible para el álbum {album_name}")
        # Intentar buscar por nombre
        mb_album = get_album_from_musicbrainz_by_name(album_name, artist_name)
        if mb_album:
            mbid_to_use = mb_album.get('id')
            print(f"Se encontró MBID por nombre: {mbid_to_use}")
        else:
            print(f"No se pudo encontrar MBID para el álbum {album_name} de {artist_name}")
            return False
    
    # Obtener información detallada del álbum desde MusicBrainz
    mb_album = get_album_from_musicbrainz(mbid_to_use)
    if not mb_album:
        print(f"No se pudo obtener información de MusicBrainz para el álbum {album_name} (MBID: {mbid_to_use})")
        return False
    
    # Verificar columnas disponibles
    cursor.execute("PRAGMA table_info(albums)")
    available_columns = [column[1] for column in cursor.fetchall()]
    
    # Extraer todos los datos relevantes
    updates = []
    params = []
    
    # Actualizar MBID por si acaso
    updates.append("mbid = ?")
    params.append(mbid_to_use)
    
    # Actualizar MusicBrainz IDs
    if "musicbrainz_albumid" in available_columns:
        updates.append("musicbrainz_albumid = ?")
        params.append(mbid_to_use)
    
    # URL de MusicBrainz
    if "musicbrainz_url" in available_columns:
        musicbrainz_url = f"https://musicbrainz.org/release/{mbid_to_use}"
        updates.append("musicbrainz_url = ?")
        params.append(musicbrainz_url)
    
    # Número de catálogo
    if "catalognumber" in available_columns and 'label-info-list' in mb_album and mb_album['label-info-list']:
        for label_info in mb_album['label-info-list']:
            if 'catalog-number' in label_info:
                updates.append("catalognumber = ?")
                params.append(label_info['catalog-number'])
                break
    
    # Sello discográfico
    if "label" in available_columns and 'label-info-list' in mb_album and mb_album['label-info-list']:
        for label_info in mb_album['label-info-list']:
            if 'label' in label_info and 'name' in label_info['label']:
                updates.append("label = ?")
                params.append(label_info['label']['name'])
                break
    
    # Información del artista del álbum
    if "musicbrainz_albumartistid" in available_columns and 'artist-credit' in mb_album and mb_album['artist-credit']:
        for credit in mb_album['artist-credit']:
            if 'artist' in credit and 'id' in credit['artist']:
                updates.append("musicbrainz_albumartistid = ?")
                params.append(credit['artist']['id'])
                break
    
    # Release Group ID
    if "musicbrainz_releasegroupid" in available_columns and 'release-group' in mb_album and 'id' in mb_album['release-group']:
        updates.append("musicbrainz_releasegroupid = ?")
        params.append(mb_album['release-group']['id'])
    
    # Género
    if "genre" in available_columns and 'tag-list' in mb_album:
        tags = [tag['name'] for tag in mb_album['tag-list']] if 'tag-list' in mb_album else []
        genre = ','.join(tags[:3]) if tags else ''
        if genre:
            updates.append("genre = ?")
            params.append(genre)
    
    # Media y formato
    if "media" in available_columns and 'medium-list' in mb_album and mb_album['medium-list']:
        media_types = []
        for medium in mb_album['medium-list']:
            if 'format' in medium:
                media_types.append(medium['format'])
        
        if media_types:
            updates.append("media = ?")
            params.append(','.join(media_types))
        
        # Tomar el primer disco como referencia para discnumber
        if "discnumber" in available_columns and 'position' in mb_album['medium-list'][0]:
            updates.append("discnumber = ?")
            params.append(str(mb_album['medium-list'][0]['position']))
    
    # País de lanzamiento
    if "releasecountry" in available_columns and 'country' in mb_album:
        updates.append("releasecountry = ?")
        params.append(mb_album['country'])
    
    # Año original
    if "originalyear" in available_columns and 'release-group' in mb_album and 'first-release-date' in mb_album['release-group']:
        first_release = mb_album['release-group']['first-release-date']
        if first_release and len(first_release) >= 4:
            try:
                originalyear = int(first_release[:4])
                updates.append("originalyear = ?")
                params.append(originalyear)
                
                # Actualizar year si está vacío
                if "year" in available_columns:
                    cursor.execute("SELECT year FROM albums WHERE id = ?", (album_id,))
                    current_year = cursor.fetchone()[0]
                    if not current_year:
                        updates.append("year = ?")
                        params.append(originalyear)
            except ValueError:
                pass
    
    # Número total de pistas
    if "total_tracks" in available_columns and 'medium-list' in mb_album:
        total_tracks = 0
        for medium in mb_album['medium-list']:
            if 'track-count' in medium:
                total_tracks += int(medium['track-count'])
        
        if total_tracks > 0:
            updates.append("total_tracks = ?")
            params.append(total_tracks)
    
    # Ejecutar actualización
    if updates:
        query = f"UPDATE albums SET {', '.join(updates)} WHERE id = ?"
        params.append(album_id)
        
        try:
            cursor.execute(query, params)
            conn.commit()
            print(f"Álbum {album_name} actualizado con éxito con datos de MusicBrainz")
            return True
        except sqlite3.Error as e:
            print(f"Error al actualizar álbum {album_name}: {e}")
    
    return False



def get_or_update_artist(conn, artist_name, mbid, lastfm_api_key, interactive=False):
    """
    Función mejorada para obtener artista por nombre o MBID con mejor prevención de duplicados
    Primero busca en la base de datos, luego en Last.fm/MusicBrainz, y solo crea nuevo si es necesario
    
    Args:
        conn: Conexión a la base de datos
        artist_name: Nombre del artista
        mbid: MBID del artista (opcional)
        lastfm_api_key: API key de Last.fm
        interactive: Si está en modo interactivo
        
    Returns:
        ID del artista o None si no se puede obtener
    """
    print(f"\n=== Procesando artista: {artist_name} ===")
    
    # Primero intentar obtener el nombre correcto y MBID desde Last.fm
    corrected_name, corrected_mbid = get_artist_correction(artist_name, lastfm_api_key)
    
    # Usar los valores corregidos
    artist_name_to_use = corrected_name
    mbid_to_use = corrected_mbid if corrected_mbid else mbid
    
    # 1. Primero intentar encontrar en la base de datos con búsqueda mejorada
    artist_id, artist_db_info = lookup_artist_in_database(conn, artist_name_to_use, mbid_to_use, threshold=0.90)
    
    if artist_id:
        print(f"Artista encontrado en base de datos: {artist_name_to_use} (ID: {artist_id})")
        cursor = conn.cursor()
        
        # Si tenemos un nuevo MBID y el existente es diferente o no existe, actualizar
        if mbid_to_use and (not artist_db_info['mbid'] or artist_db_info['mbid'] != mbid_to_use):
            # Verificar si otro artista ya tiene este MBID para evitar duplicados
            cursor.execute("SELECT id, name FROM artists WHERE mbid = ? AND id != ?", (mbid_to_use, artist_id))
            existing_with_mbid = cursor.fetchone()
            
            if existing_with_mbid:
                print(f"ADVERTENCIA: Artista '{existing_with_mbid[1]}' (ID: {existing_with_mbid[0]}) ya tiene MBID {mbid_to_use}")
                print(f"Esto sugiere un posible duplicado entre '{artist_name}' y '{existing_with_mbid[1]}'")
                
                if interactive:
                    # Dejar que el usuario decida cómo manejar esto
                    print("\n" + "="*60)
                    print("MBID DUPLICADO DETECTADO")
                    print("="*60)
                    print(f"Artista 1: {artist_name} (ID: {artist_id})")
                    print(f"Artista 2: {existing_with_mbid[1]} (ID: {existing_with_mbid[0]})")
                    print(f"Ambos comparten MBID: {mbid_to_use}")
                    print("-"*60)
                    choice = input("¿Cómo proceder? (1: Mantener ambos, 2: Unir al primero, 3: Unir al segundo): ")
                    
                    if choice == "2":
                        # Unir al primero (artista actual)
                        cursor.execute("UPDATE albums SET artist_id = ? WHERE artist_id = ?", 
                                     (artist_id, existing_with_mbid[0]))
                        cursor.execute("UPDATE scrobbles SET artist_id = ? WHERE artist_id = ?", 
                                     (artist_id, existing_with_mbid[0]))
                        cursor.execute("DELETE FROM artists WHERE id = ?", (existing_with_mbid[0],))
                        conn.commit()
                        print(f"Artista '{existing_with_mbid[1]}' unido a '{artist_name}'")
                    elif choice == "3":
                        # Unir al segundo (artista existente)
                        cursor.execute("UPDATE albums SET artist_id = ? WHERE artist_id = ?", 
                                     (existing_with_mbid[0], artist_id))
                        cursor.execute("UPDATE scrobbles SET artist_id = ? WHERE artist_id = ?", 
                                     (existing_with_mbid[0], artist_id))
                        cursor.execute("DELETE FROM artists WHERE id = ?", (artist_id,))
                        conn.commit()
                        print(f"Artista '{artist_name}' unido a '{existing_with_mbid[1]}'")
                        return existing_with_mbid[0]  # Devolver el ID del artista al que unimos
                    # Opción 1 o predeterminada: mantener ambos, solo actualizar el MBID del actual
            
            # Actualizar MBID si no unimos o elegimos mantener ambos
            print(f"Actualizando MBID para artista {artist_name_to_use}: {mbid_to_use}")
            cursor.execute("UPDATE artists SET mbid = ? WHERE id = ?", (mbid_to_use, artist_id))
            conn.commit()

        # Verificar si el origen es "manual" y actualizar la información del artista
        if artist_db_info['origen'] == 'manual':
            print(f"Artista {artist_name_to_use} tiene origen 'manual', actualizando información...")
            # Obtener información completa desde Last.fm
            artist_info = get_artist_info(artist_name_to_use, mbid_to_use, lastfm_api_key)
            
            if artist_info:
                update_artist_in_db(conn, artist_id, artist_info)
        
        return artist_id
    
    # 2. Si no está en la base de datos, buscar en Last.fm y MusicBrainz
    print(f"Artista no encontrado en base de datos, buscando en Last.fm: {artist_name_to_use}")
    
    # Obtener información completa desde Last.fm
    artist_info = get_artist_info(artist_name_to_use, mbid_to_use, lastfm_api_key)
    
    if not artist_info:
        print(f"No se pudo obtener información de Last.fm para {artist_name_to_use}")
        
        # Intentar con MusicBrainz si tenemos MBID
        mb_artist = None
        if mbid_to_use:
            mb_artist = get_artist_from_musicbrainz(mbid_to_use)
            if mb_artist:
                print(f"Artista encontrado en MusicBrainz por MBID: {mb_artist.get('name', artist_name_to_use)}")
                
                # Verificar de nuevo la base de datos con el nombre oficial de MusicBrainz
                if 'name' in mb_artist and mb_artist['name'] != artist_name_to_use:
                    mb_artist_name = mb_artist['name']
                    artist_id, artist_db_info = lookup_artist_in_database(conn, mb_artist_name, mbid_to_use, threshold=0.95)
                    
                    if artist_id:
                        print(f"Artista encontrado en base de datos usando nombre de MusicBrainz: {mb_artist_name} (ID: {artist_id})")
                        return artist_id
    
    # 3. Si encontramos información, guardar en la base de datos
    if artist_info:
        cursor = conn.cursor()
        
        # Extraer tags si existen
        tags = []
        if 'tags' in artist_info and 'tag' in artist_info['tags']:
            tag_list = artist_info['tags']['tag']
            if isinstance(tag_list, list):
                tags = [tag['name'] for tag in tag_list]
            else:
                tags = [tag_list['name']]
        tags_str = ','.join(tags)
        
        # Extraer bio
        bio = ''
        if 'bio' in artist_info and 'content' in artist_info['bio']:
            bio = artist_info['bio']['content']
        
        # URL de Last.fm
        url = artist_info.get('url', '')
        
        # MBID final
        final_mbid = artist_info.get('mbid', mbid_to_use)
        
        # Verificación final para artista existente por MBID
        if final_mbid:
            cursor.execute("SELECT id, name FROM artists WHERE mbid = ?", (final_mbid,))
            existing = cursor.fetchone()
            if existing:
                print(f"Encontrado artista con mismo MBID ya en base de datos: {existing[1]} (ID: {existing[0]})")
                return existing[0]
        
        # Mostrar información en modo interactivo
        if interactive:
            print("\n" + "="*60)
            print(f"INFORMACIÓN DEL ARTISTA A AÑADIR (de Last.fm):")
            print("="*60)
            print(f"Nombre: {artist_info.get('name', artist_name_to_use)}")
            print(f"MBID: {final_mbid}")
            print(f"URL: {url}")
            print(f"Tags: {tags_str}")
            print(f"Bio: {bio[:150]}..." if len(bio) > 150 else f"Bio: {bio}")
            print(f"Origen: lastfm")
            print("-"*60)
            
            response = input("\n¿Añadir este artista a la base de datos? (s/n): ").lower()
            if response != 's':
                print("Operación cancelada por usuario.")
                return None
        
        try:
            # Encontrar el nombre más preciso a usar
            artist_name_to_save = artist_info.get('name', artist_name_to_use)
            
            # Verificar una vez más por nombre
            cursor.execute("SELECT id FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name_to_save,))
            existing_by_name = cursor.fetchone()
            if existing_by_name:
                print(f"Encontrado artista con mismo nombre: {artist_name_to_save} (ID: {existing_by_name[0]})")
                
                # Actualizar el MBID si es necesario
                if final_mbid:
                    cursor.execute("UPDATE artists SET mbid = ? WHERE id = ?", (final_mbid, existing_by_name[0]))
                    conn.commit()
                
                return existing_by_name[0]
            
            # Insertar nuevo artista
            cursor.execute("""
                INSERT INTO artists (name, mbid, tags, bio, lastfm_url, origen)
                VALUES (?, ?, ?, ?, ?, 'lastfm')
                RETURNING id
            """, (
                artist_name_to_save, 
                final_mbid, 
                tags_str, 
                bio, 
                url
            ))
            
            artist_id = cursor.fetchone()[0]
            conn.commit()
            print(f"Artista añadido con ID: {artist_id} (origen: lastfm)")
            return artist_id
        except sqlite3.Error as e:
            print(f"Error al añadir artista {artist_name_to_use} desde Last.fm: {e}")
    
    # 4. Si hay error con Last.fm y MusicBrainz, preguntar al usuario
    if interactive:
        print("\n" + "="*60)
        print(f"NO SE PUDO OBTENER INFORMACIÓN PARA EL ARTISTA:")
        print("="*60)
        print(f"Nombre: {artist_name_to_use}")
        print(f"MBID: {mbid_to_use}")
        print("-"*60)
        response = input("¿Añadir este artista con datos mínimos (origen manual)? (s/n): ").lower()
        if response != 's':
            return None
    
    # 5. Añadir con datos mínimos y origen manual como último recurso
    try:
        cursor = conn.cursor()
        
        # Verificación final por nombre
        cursor.execute("SELECT id FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name_to_use,))
        existing_by_name = cursor.fetchone()
        if existing_by_name:
            print(f"Encontrado artista con mismo nombre: {artist_name_to_use} (ID: {existing_by_name[0]})")
            return existing_by_name[0]
        
        cursor.execute("""
            INSERT INTO artists (name, mbid, origen)
            VALUES (?, ?, 'manual')
            RETURNING id
        """, (artist_name_to_use, mbid_to_use))
        
        artist_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Artista añadido con datos mínimos, ID: {artist_id} (origen: manual)")
        return artist_id
    except sqlite3.Error as e:
        print(f"Error al añadir artista {artist_name_to_use}: {e}")
        return None

def limpiar_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')


def lookup_artist_in_database(conn, artist_name, mbid=None, threshold=0.9):
    """
    Búsqueda mejorada de artistas en la base de datos utilizando múltiples criterios
    para evitar duplicados.
    
    Args:
        conn: Conexión a la base de datos
        artist_name: Nombre del artista a buscar
        mbid: MBID del artista (opcional)
        threshold: Umbral para coincidencias de texto parciales (entre 0 y 1)
        
    Returns:
        Tupla (artist_id, info_artista) o (None, None) si no se encuentra
    """
    cursor = conn.cursor()
    artist_id = None
    artist_info = None
    
    # Normalizar strings
    artist_name = artist_name.strip() if artist_name else ""
    
    # 1. Buscar por MBID si está disponible (el método más preciso)
    if mbid:
        cursor.execute("SELECT id, name, mbid, origen FROM artists WHERE mbid = ?", (mbid,))
        result = cursor.fetchone()
        if result:
            artist_id = result[0]
            artist_info = {
                'id': result[0],
                'name': result[1],
                'mbid': result[2],
                'origen': result[3]
            }
            return artist_id, artist_info
    
    # 2. Buscar por nombre exacto
    if artist_name:
        cursor.execute("SELECT id, name, mbid, origen FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name,))
        result = cursor.fetchone()
        if result:
            artist_id = result[0]
            artist_info = {
                'id': result[0],
                'name': result[1],
                'mbid': result[2],
                'origen': result[3]
            }
            return artist_id, artist_info
    
    # 3. Buscar por coincidencia aproximada de nombre
    if artist_name and threshold < 1.0:
        cursor.execute("SELECT id, name, mbid, origen FROM artists")
        artists = cursor.fetchall()
        
        # Buscar la mejor coincidencia usando similitud
        best_match = None
        best_score = threshold  # Umbral mínimo
        
        import difflib
        for artist in artists:
            score = difflib.SequenceMatcher(None, artist_name.lower(), artist[1].lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = artist
        
        if best_match:
            artist_id = best_match[0]
            artist_info = {
                'id': best_match[0],
                'name': best_match[1],
                'mbid': best_match[2],
                'origen': best_match[3]
            }
            print(f"Coincidencia aproximada para artista: '{artist_name}' -> '{best_match[1]}' (similitud: {best_score:.2f})")
            return artist_id, artist_info
    
    # Si llegamos aquí, no se encontró el artista
    return None, None



def lookup_album_in_database(conn, album_name, artist_id, artist_name=None, mbid=None, threshold=0.9):
    """
    Búsqueda mejorada de álbumes en la base de datos utilizando múltiples criterios
    para evitar duplicados.
    
    Args:
        conn: Conexión a la base de datos
        album_name: Nombre del álbum a buscar
        artist_id: ID del artista
        artist_name: Nombre del artista (opcional)
        mbid: MBID del álbum (opcional)
        threshold: Umbral para coincidencias de texto parciales (entre 0 y 1)
        
    Returns:
        Tupla (album_id, info_album) o (None, None) si no se encuentra
    """
    cursor = conn.cursor()
    album_id = None
    album_info = None
    
    # Normalizar strings
    album_name = album_name.strip() if album_name else ""
    artist_name = artist_name.strip() if artist_name else ""
    
    # 1. Buscar por MBID si está disponible (el método más preciso)
    if mbid:
        cursor.execute("SELECT id, name, artist_id, mbid, origen FROM albums WHERE mbid = ?", (mbid,))
        result = cursor.fetchone()
        if result:
            album_id = result[0]
            album_info = {
                'id': result[0],
                'name': result[1],
                'artist_id': result[2],
                'mbid': result[3],
                'origen': result[4]
            }
            
            # Verificar si corresponde al mismo artista
            if album_info['artist_id'] != artist_id and artist_id is not None:
                print(f"Advertencia: Álbum con MBID {mbid} encontrado para otro artista (ID: {album_info['artist_id']})")
            
            return album_id, album_info
    
    # 2. Buscar por nombre exacto y artista_id
    if album_name and artist_id:
        cursor.execute("""
            SELECT id, name, artist_id, mbid, origen
            FROM albums 
            WHERE artist_id = ? AND LOWER(name) = LOWER(?)
        """, (artist_id, album_name))
        
        result = cursor.fetchone()
        if result:
            album_id = result[0]
            album_info = {
                'id': result[0],
                'name': result[1],
                'artist_id': result[2],
                'mbid': result[3],
                'origen': result[4]
            }
            return album_id, album_info
    
    # 3. Buscar por coincidencia aproximada de nombre
    if album_name and artist_id and threshold < 1.0:
        # Obtener todos los álbumes de este artista
        cursor.execute("""
            SELECT id, name, artist_id, mbid, origen
            FROM albums 
            WHERE artist_id = ?
        """, (artist_id,))
        
        albums = cursor.fetchall()
        
        # Buscar la mejor coincidencia usando similitud
        best_match = None
        best_score = threshold  # Umbral mínimo
        
        import difflib
        for album in albums:
            score = difflib.SequenceMatcher(None, album_name.lower(), album[1].lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = album
        
        if best_match:
            album_id = best_match[0]
            album_info = {
                'id': best_match[0],
                'name': best_match[1],
                'artist_id': best_match[2],
                'mbid': best_match[3],
                'origen': best_match[4]
            }
            print(f"Coincidencia aproximada para álbum: '{album_name}' -> '{best_match[1]}' (similitud: {best_score:.2f})")
            return album_id, album_info
    
    # Si llegamos aquí, no se encontró el álbum
    return None, None


def get_or_update_album(conn, album_name, artist_name, artist_id, mbid, lastfm_api_key, interactive=False):
    """
    Función mejorada para obtener/crear álbum asegurándose de que se añade correctamente
    """
    print(f"\n=== Procesando álbum: {album_name} de {artist_name} (MBID: {mbid}) ===")
    
    if not album_name or not artist_id:
        print("Nombre de álbum o ID de artista no proporcionados, omitiendo")
        return None
    
    cursor = conn.cursor()
    
    # Primero intentar encontrar por MBID si está disponible (más preciso)
    if mbid:
        cursor.execute("SELECT id, name FROM albums WHERE mbid = ?", (mbid,))
        result = cursor.fetchone()
        if result:
            print(f"Álbum encontrado por MBID: {result[1]} (ID: {result[0]})")
            return result[0]
    
    # Buscar por nombre y artista_id
    cursor.execute("""
        SELECT id, name, mbid FROM albums 
        WHERE artist_id = ? AND LOWER(name) = LOWER(?)
    """, (artist_id, album_name))
    
    result = cursor.fetchone()
    if result:
        album_id, db_album_name, db_mbid = result
        print(f"Álbum encontrado en base de datos: {db_album_name} (ID: {album_id})")
        
        # Si tenemos un nuevo MBID y el existente es diferente o no existe, actualizar
        if mbid and (not db_mbid or db_mbid != mbid):
            print(f"Actualizando MBID para álbum {db_album_name}: {mbid}")
            cursor.execute("UPDATE albums SET mbid = ? WHERE id = ?", (mbid, album_id))
            conn.commit()
        
        return album_id
    
    # Si no está en la base de datos, buscar información y crearlo
    print(f"Álbum no encontrado en base de datos. Buscando información para: {album_name}")
    
    # Obtener información del álbum
    album_info = get_album_info(album_name, artist_name, mbid, lastfm_api_key)
    
    # Si no se puede obtener de Last.fm y tenemos MBID, intentar con MusicBrainz
    if not album_info and mbid:
        print(f"Intentando obtener información de MusicBrainz para MBID: {mbid}")
        mb_album = get_album_from_musicbrainz(mbid)
        if mb_album:
            print(f"Información obtenida de MusicBrainz: {mb_album.get('title', album_name)}")
            
            # Crear entrada en la base de datos con datos de MusicBrainz
            try:
                cursor.execute("""
                    INSERT INTO albums (artist_id, name, mbid, origen, year)
                    VALUES (?, ?, ?, 'musicbrainz', ?)
                    RETURNING id
                """, (
                    artist_id,
                    mb_album.get('title', album_name),
                    mbid,
                    mb_album.get('first-release-date', '')[:4] if 'first-release-date' in mb_album else None
                ))
                
                album_id = cursor.fetchone()[0]
                conn.commit()
                print(f"Álbum añadido desde MusicBrainz con ID: {album_id}")
                
                # Actualizar con detalles adicionales
                update_album_details_from_musicbrainz(conn, album_id, mbid)
                
                return album_id
            except sqlite3.Error as e:
                print(f"Error al añadir álbum desde MusicBrainz: {e}")
    
    # Si tenemos información de Last.fm, crear con esos datos
    if album_info:
        # Extraer año
        year = None
        if 'releasedate' in album_info:
            try:
                release_date = album_info['releasedate'].strip()
                if release_date:
                    year = datetime.datetime.strptime(release_date, '%d %b %Y, %H:%M').year
            except (ValueError, AttributeError):
                pass
        
        # Extraer MBID (podría venir en la respuesta si no lo teníamos antes)
        album_mbid = album_info.get('mbid', mbid)
        
        try:
            cursor.execute("""
                INSERT INTO albums (artist_id, name, year, lastfm_url, mbid, origen)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
            """, (
                artist_id,
                album_info.get('name', album_name),
                year,
                album_info.get('url', ''),
                album_mbid,
                'lastfm'
            ))
            
            album_id = cursor.fetchone()[0]
            conn.commit()
            print(f"Álbum añadido desde Last.fm con ID: {album_id}")
            
            # Si tenemos MBID, actualizar con datos de MusicBrainz
            if album_mbid:
                update_album_details_from_musicbrainz(conn, album_id, album_mbid)
            
            return album_id
        except sqlite3.Error as e:
            print(f"Error al añadir álbum desde Last.fm: {e}")
    
    # Si no hay información disponible, crear con datos mínimos
    print(f"No se pudo obtener información para álbum '{album_name}'. Creando con datos mínimos.")
    try:
        cursor.execute("""
            INSERT INTO albums (artist_id, name, mbid, origen)
            VALUES (?, ?, ?, ?)
            RETURNING id
        """, (artist_id, album_name, mbid, 'manual'))
        
        album_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Álbum añadido con datos mínimos, ID: {album_id}")
        return album_id
    except sqlite3.Error as e:
        print(f"Error al añadir álbum con datos mínimos: {e}")
        return None

def setup_musicbrainz(cache_directory=None):
    """Configura el cliente de MusicBrainz y el sistema de caché"""
    # Configurar cliente de MusicBrainz
    musicbrainzngs.set_useragent(
        "TuAppMusical", 
        "1.0", 
        "tu_email@example.com"
    )
    
    # Inicializar caché unificado
    setup_cache(cache_directory)


def get_artist_from_musicbrainz(mbid):
    """
    Obtiene información extendida de un artista desde MusicBrainz usando su MBID, usando caché
    """
    global mb_cache
    
    if not mbid:
        return None
    
    # Verificar en caché primero
    if mb_cache:
        cached_result = mb_cache.get({"type": "artist", "id": mbid})
        if cached_result:
            print(f"Usando datos en caché para artista con MBID {mbid}")
            return cached_result
    
    try:
        print(f"Consultando MusicBrainz para artista con MBID {mbid}")
        # Incluir más información relevante
        artist_data = musicbrainzngs.get_artist_by_id(
            mbid, 
            includes=["tags", "url-rels", "aliases", "annotation"]
        )
        result = artist_data.get("artist")
        
        # Guardar en caché
        if mb_cache and result:
            mb_cache.put({"type": "artist", "id": mbid}, result)
            
        return result
    except musicbrainzngs.WebServiceError as e:
        print(f"Error al consultar MusicBrainz para artista con MBID {mbid}: {e}")
        return None



def get_album_from_musicbrainz(mbid):
    """Obtiene información extendida de un álbum desde MusicBrainz usando su MBID, usando caché"""
    global mb_cache
    
    if not mbid:
        return None
    
    # Verificar en caché primero
    if mb_cache:
        cached_result = mb_cache.get({"type": "release", "id": mbid})
        if cached_result:
            print(f"Usando datos en caché para álbum con MBID {mbid}")
            return cached_result
    
    try:
        print(f"Consultando MusicBrainz para álbum con MBID {mbid}")
        # Incluir más información relevante
        release_data = musicbrainzngs.get_release_by_id(
            mbid, 
            includes=["artists", "recordings", "release-groups", "url-rels", 
                     "labels", "media", "discids", "annotation"]
        )
        result = release_data.get("release")
        
        # Guardar en caché
        if mb_cache and result:
            mb_cache.put({"type": "release", "id": mbid}, result)
            
        return result
    except musicbrainzngs.WebServiceError as e:
        print(f"Error al consultar MusicBrainz para álbum con MBID {mbid}: {e}")
        return None

def get_album_from_musicbrainz_by_name(album_name, artist_name=None):
    """Búsqueda en MusicBrainz por nombre del álbum y opcionalmente artista, usando caché"""
    global mb_cache
    
    if not album_name:
        return None
    
    # Proper string conversion to avoid errors
    album_name = str(album_name) if album_name else ""
    artist_name = str(artist_name) if artist_name else ""
    
    # Construir parámetros de búsqueda
    query = {'release': album_name, 'limit': 5}
    if artist_name:
        query['artist'] = artist_name
        
    # Verificar en caché primero
    if mb_cache:
        cached_result = mb_cache.get({"type": "release-search", "id": query})
        if cached_result:
            print(f"Usando datos en caché para búsqueda de álbum '{album_name}'")
            return cached_result
    
    try:
        print(f"Consultando MusicBrainz para búsqueda de álbum '{album_name}'")
        result = musicbrainzngs.search_releases(**query)
        
        if result and 'release-list' in result and result['release-list']:
            # Si múltiples resultados y tenemos artista, priorizar coincidencias exactas
            if artist_name and len(result['release-list']) > 1:
                for release in result['release-list']:
                    if 'artist-credit' in release:
                        for credit in release['artist-credit']:
                            if 'artist' in credit and 'name' in credit['artist'] and credit['artist']['name'].lower() == artist_name.lower():
                                # Guardar en caché
                                if mb_cache:
                                    mb_cache.put({"type": "release-search", "id": release}, result)
                                return release
            
            # Si no hay coincidencia exacta, usar el primer resultado
            first_result = result['release-list'][0]
            
            # Guardar en caché
            if mb_cache:
                mb_cache.put({"type": "release-search", "id": first_result}, result)
                
            return first_result
        return None
    except musicbrainzngs.WebServiceError as e:
        print(f"Error al buscar álbum en MusicBrainz por nombre '{album_name}': {e}")
        return None

def get_track_from_musicbrainz(mbid):
    """Obtiene información de una canción desde MusicBrainz usando su MBID, usando caché"""
    global mb_cache
    
    if not mbid:
        return None
    
    # Verificar en caché primero
    if mb_cache:
        cached_result = mb_cache.get({"type": "recording", "id": mbid})
        if cached_result:
            print(f"Usando datos en caché para canción con MBID {mbid}")
            return cached_result
    
    try:
        print(f"Consultando MusicBrainz para canción con MBID {mbid}")
        recording_data = musicbrainzngs.get_recording_by_id(
            mbid, 
            includes=["artists", "releases", "tags", "url-rels"]
        )
        result = recording_data.get("recording")
        
        # Guardar en caché
        if mb_cache and result:
            mb_cache.put({"type": "recording", "id": mbid}, result)
            
        return result
    except musicbrainzngs.WebServiceError as e:
        print(f"Error al consultar MusicBrainz para canción con MBID {mbid}: {e}")
        return None

# def get_track_from_musicbrainz_by_name(track_name, artist_name=None, album_name=None):
#     """Búsqueda en MusicBrainz por nombre de la canción y opcionalmente artista/álbum, usando caché"""
#     global mb_cache
    
#     if not track_name:
#         return None
    
#     # Proper string conversion to avoid errors
#     track_name = str(track_name) if track_name else ""
#     artist_name = str(artist_name) if artist_name else ""
#     album_name = str(album_name) if album_name else ""
    
#     # Construir parámetros de búsqueda
#     query = {'recording': track_name, 'limit': 5}
#     if artist_name:
#         query['artist'] = artist_name
        
#     # Verificar en caché primero
#     if mb_cache:
#         cached_result = mb_cache.get({"type": "recording-search", "id": query})
#         if cached_result:
#             print(f"Usando datos en caché para búsqueda de canción '{track_name}'")
#             return cached_result
    
#     try:
#         print(f"Consultando MusicBrainz para búsqueda de canción '{track_name}'")
#         result = musicbrainzngs.search_recordings(**query)
        
#         if result and 'recording-list' in result and result['recording-list']:
#             recordings = result['recording-list']
            
#             # Si tenemos artista y álbum, intentar encontrar coincidencia exacta
#             if artist_name and album_name:
#                 for recording in recordings:
#                     if 'artist-credit' in recording and 'release-list' in recording:
#                         # Verificar coincidencia de artista
#                         artist_match = False
#                         for credit in recording['artist-credit']:
#                             if 'artist' in credit and 'name' in credit['artist'] and credit['artist']['name'].lower() == artist_name.lower():
#                                 artist_match = True
#                                 break
                        
#                         # Si el artista coincide, verificar álbum
#                         if artist_match and 'release-list' in recording:
#                             for release in recording['release-list']:
#                                 if release['title'].lower() == album_name.lower():
#                                     # Guardar en caché
#                                     if mb_cache:
#                                         mb_cache.put({"type": "recording-search", "id": recording}, result)
#                                     return recording
            
#             # Si sólo tenemos artista, buscar mejor coincidencia por artista
#             elif artist_name:
#                 for recording in recordings:
#                     if 'artist-credit' in recording:
#                         for credit in recording['artist-credit']:
#                             if 'artist' in credit and 'name' in credit['artist'] and credit['artist']['name'].lower() == artist_name.lower():
#                                 # Guardar en caché
#                                 if mb_cache:
#                                     mb_cache.put({"type": "recording-search", "id": recording}, result)
#                                 return recording
            
#             # Si no hay coincidencia exacta, usar el primer resultado
#             first_result = recordings[0]
            
#             # Guardar en caché
#             if mb_cache:
#                 mb_cache.put({"type": "recording-search", "id": first_result}, result)
                
#             return first_result
#         return None
#     except musicbrainzngs.WebServiceError as e:
#         print(f"Error al buscar canción en MusicBrainz por nombre '{track_name}': {e}")
#         return None

def setup_database(conn, lastfm_username):
    """Sets up the database with the necessary tables and columns for scrobbles
    
    Args:
        conn: Database connection
        lastfm_username: Last.fm username to personalize the table
    """
    cursor = conn.cursor()
    
    # Name of the personalized scrobbles table for this user
    scrobbles_table = f"scrobbles_{lastfm_username}"
    songs_table = f"songs_{lastfm_username}"
    #scrobbled_songs_table = f"scrobbled_songs_{lastfm_username}"
    
    # Create scrobbles table for this specific user if it doesn't exist
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {scrobbles_table} (
        id INTEGER PRIMARY KEY,
        track_name TEXT NOT NULL,
        album_name TEXT,
        artist_name TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        scrobble_date TIMESTAMP NOT NULL,
        lastfm_url TEXT,
        song_id INTEGER,
        album_id INTEGER,
        artist_id INTEGER,
        FOREIGN KEY (song_id) REFERENCES songs(id),
        FOREIGN KEY (album_id) REFERENCES albums(id),
        FOREIGN KEY (artist_id) REFERENCES artists(id)
    )
    """)
    
    # Create songs table for this user if it doesn't exist
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {songs_table} (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        mbid TEXT,
        added_timestamp INTEGER,
        added_week INTEGER,
        added_month INTEGER,
        added_year INTEGER,
        duration INTEGER,
        album TEXT,
        album_artist TEXT,
        date TEXT,
        genre TEXT,
        artist TEXT NOT NULL,
        origen TEXT,
        scrobble_id INTEGER,
        data_source TEXT,
        musicbrainz_artistid TEXT,
        musicbrainz_recordingid TEXT,
        musicbrainz_albumartistid TEXT,
        musicbrainz_releasegroupid TEXT
    )
    """)
    
    # # Create scrobbled_songs table for this user if it doesn't exist
    # cursor.execute(f"""
    # CREATE TABLE IF NOT EXISTS {scrobbled_songs_table} (
    #     id INTEGER PRIMARY KEY,
    #     title TEXT NOT NULL,
    #     artist_name TEXT NOT NULL,
    #     artist_id INTEGER,
    #     album_name TEXT,
    #     album_id INTEGER,
    #     song_id INTEGER,
    #     lastfm_url TEXT,
    #     scrobble_timestamps TEXT,
    #     mbid TEXT,
    #     FOREIGN KEY (song_id) REFERENCES songs(id),
    #     FOREIGN KEY (album_id) REFERENCES albums(id),
    #     FOREIGN KEY (artist_id) REFERENCES artists(id)
    # )
    # """)
    
    # Create table for configuration
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lastfm_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        lastfm_username TEXT,
        last_timestamp INTEGER,
        last_updated TIMESTAMP
    )
    """)
    
    # Create artists table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS artists (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        mbid TEXT,
        tags TEXT,
        bio TEXT,
        lastfm_url TEXT,
        origen TEXT,
        website TEXT,
        similar_artists TEXT
    )
    """)
    
    # Create albums table if it doesn't exist - with all the required fields
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS albums (
        id INTEGER PRIMARY KEY,
        artist_id INTEGER,
        name TEXT NOT NULL,
        year INTEGER,
        lastfm_url TEXT,
        mbid TEXT,
        total_tracks INTEGER,
        origen TEXT,
        musicbrainz_albumid TEXT,
        musicbrainz_albumartistid TEXT,
        musicbrainz_releasegroupid TEXT,
        musicbrainz_url TEXT,
        catalognumber TEXT,
        media TEXT,
        discnumber TEXT,
        releasecountry TEXT,
        originalyear INTEGER,
        label TEXT,
        genre TEXT,
        scrobble_id INTEGER,
        data_source TEXT,
        FOREIGN KEY (artist_id) REFERENCES artists(id)
    )
    """)
    
    # Create song_links table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS song_links (
        id INTEGER PRIMARY KEY,
        song_id INTEGER,
        lastfm_url TEXT,
        spotify_url TEXT,
        spotify_id TEXT,
        youtube_url TEXT,
        musicbrainz_url TEXT,
        musicbrainz_recording_id TEXT,
        bandcamp_url TEXT,
        soundcloud_url TEXT,
        FOREIGN KEY (song_id) REFERENCES songs(id)
    )
    """)
    
    # Function to check and add columns if they don't exist
    def add_column_if_not_exists(table, column, type):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [info[1] for info in cursor.fetchall()]
        if column not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type}")
            print(f"Added column '{column}' to '{table}' table")
    
    # Add missing columns to artists
    add_column_if_not_exists('artists', 'origen', 'TEXT')
    add_column_if_not_exists('artists', 'website', 'TEXT')
    add_column_if_not_exists('artists', 'similar_artists', 'TEXT')
    add_column_if_not_exists('artists', 'scrobble_id', 'INTEGER')
    add_column_if_not_exists('artists', 'data_source', 'TEXT')
    
    # Add missing columns to albums
    add_column_if_not_exists('albums', 'origen', 'TEXT')
    add_column_if_not_exists('albums', 'scrobble_id', 'INTEGER')
    add_column_if_not_exists('albums', 'data_source', 'TEXT')
    add_column_if_not_exists('albums', 'lastfm_url', 'TEXT')
    add_column_if_not_exists('albums', 'musicbrainz_albumid', 'TEXT')
    add_column_if_not_exists('albums', 'musicbrainz_albumartistid', 'TEXT')
    add_column_if_not_exists('albums', 'musicbrainz_releasegroupid', 'TEXT')
    add_column_if_not_exists('albums', 'musicbrainz_url', 'TEXT')
    add_column_if_not_exists('albums', 'catalognumber', 'TEXT')
    add_column_if_not_exists('albums', 'media', 'TEXT')
    add_column_if_not_exists('albums', 'discnumber', 'TEXT')
    add_column_if_not_exists('albums', 'releasecountry', 'TEXT')
    add_column_if_not_exists('albums', 'originalyear', 'INTEGER')
    add_column_if_not_exists('albums', 'label', 'TEXT')
    add_column_if_not_exists('albums', 'genre', 'TEXT')
    
    # Add missing columns to songs
    add_column_if_not_exists('songs', 'origen', 'TEXT')
    add_column_if_not_exists('songs', 'scrobble_id', 'INTEGER')
    add_column_if_not_exists('songs', 'data_source', 'TEXT')
    
    # Create indices for efficient queries
    create_optimized_indices(conn, lastfm_username)
    
    conn.commit()
    print(f"Database setup completed for user {lastfm_username}")
    
    return True

def get_existing_items(conn):
    """Obtiene los artistas, álbumes y canciones existentes en la base de datos"""
    cursor = conn.cursor()
    
    # Obtener artistas existentes (incluyendo origen)
    cursor.execute("SELECT id, name, origen FROM artists")
    artists_rows = cursor.fetchall()
    artists = {row[1].lower(): {'id': row[0], 'origen': row[2]} for row in artists_rows}
    
    # Obtener álbumes existentes (incluyendo origen)
    cursor.execute("""
        SELECT a.id, a.name, ar.name, a.artist_id, a.origen
        FROM albums a 
        JOIN artists ar ON a.artist_id = ar.id
    """)
    albums_rows = cursor.fetchall()
    albums = {(row[1].lower(), row[2].lower()): {'id': row[0], 'artist_id': row[3], 'origen': row[4]} for row in albums_rows}
    
    # Obtener canciones existentes (incluyendo origen)
    cursor.execute("""
        SELECT s.id, s.title, s.artist, s.album, s.origen
        FROM songs s
    """)
    songs_rows = cursor.fetchall()
    songs = {(row[1].lower(), row[2].lower(), row[3].lower() if row[3] else None): 
             {'id': row[0], 'origen': row[4]} for row in songs_rows}
    
    return artists, albums, songs


def get_last_timestamp(conn, lastfm_username):
    """
    Obtiene el timestamp del último scrobble procesado desde la tabla de configuración
    
    Args:
        conn: Conexión a la base de datos
        lastfm_username: Nombre de usuario de Last.fm
    """
    cursor = conn.cursor()
    cursor.execute("SELECT last_timestamp FROM lastfm_config WHERE id = 1 AND lastfm_username = ?", (lastfm_username,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    return 0




def save_last_timestamp(conn, timestamp, lastfm_username):
    """
    Guarda el timestamp del último scrobble procesado en la tabla de configuración
    
    Args:
        conn: Conexión a la base de datos
        timestamp: Timestamp a guardar
        lastfm_username: Nombre de usuario de Last.fm
    """
    cursor = conn.cursor()
    
    # Intentar actualizar primero
    cursor.execute("""
        UPDATE lastfm_config 
        SET last_timestamp = ?, lastfm_username = ?, last_updated = datetime('now')
        WHERE id = 1 AND lastfm_username = ?
    """, (timestamp, lastfm_username, lastfm_username))
    
    # Si no se actualizó ninguna fila, intentar actualizar sin filtrar por nombre de usuario
    if cursor.rowcount == 0:
        cursor.execute("""
            UPDATE lastfm_config 
            SET last_timestamp = ?, lastfm_username = ?, last_updated = datetime('now')
            WHERE id = 1
        """, (timestamp, lastfm_username))
    
    # Si aún no se actualizó ninguna fila, insertar
    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO lastfm_config (id, lastfm_username, last_timestamp, last_updated)
            VALUES (1, ?, ?, datetime('now'))
        """, (lastfm_username, timestamp))
    
    conn.commit()


# LASTFM INFO



def get_album_info(album_name, artist_name, mbid, lastfm_api_key):
    """Obtiene información detallada de un álbum desde Last.fm, usando caché"""
    global lastfm_cache
    
    # Construir parámetros de consulta
    params = {
        'method': 'album.getInfo',
        'album': album_name,
        'artist': artist_name,
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    if mbid:
        params['mbid'] = mbid
    
    # Verificar en caché primero
    if lastfm_cache:
        cached_result = lastfm_cache.get(params)
        if cached_result:
            print(f"Usando datos en caché para álbum Last.fm: {album_name}")
            return cached_result.get('album')
    
    print(f"Consultando información para álbum: {album_name} de {artist_name} (MBID: {mbid})")
    
    try:
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        if response.status_code != 200:
            print(f"Error al obtener información del álbum {album_name}: {response.status_code}")
            print(f"Respuesta de error: {response.text[:200]}...")
            return None
        
        data = response.json()
        
        # Verificar si hay un mensaje de error en la respuesta JSON
        if 'error' in data:
            print(f"Error de la API de Last.fm: {data['message']} (código {data['error']})")
            return None
            
        if 'album' not in data:
            print(f"No se encontró información para el álbum {album_name}")
            return None
        
        print(f"Información obtenida correctamente para álbum: {album_name}")
        
        # Guardar en caché
        if lastfm_cache:
            lastfm_cache.put(params, data)
            
        return data['album']
    
    except Exception as e:
        print(f"Error al consultar álbum {album_name}: {e}")
        return None

def get_track_info(track_name, artist_name, mbid, lastfm_api_key):
    """Obtiene información detallada de una canción desde Last.fm, usando caché"""
    global lastfm_cache
    
    # Construir parámetros de consulta (todo a minúsculas para caché)
    params = {
        'method': 'track.getInfo',
        'track': track_name,
        'artist': artist_name,
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    # Crear clave de caché insensible a mayúsculas/minúsculas
    cache_params = {
        'method': 'track.getInfo',
        'track': track_name.lower() if track_name else "",
        'artist': artist_name.lower() if artist_name else "",
    }
    
    if mbid:
        params['mbid'] = mbid
        cache_params['mbid'] = mbid
    
    # Verificar en caché primero
    if lastfm_cache:
        cached_result = lastfm_cache.get(params)
        if cached_result:
            print(f"Usando datos en caché para canción Last.fm: {track_name}")
            return cached_result.get('track')
    
    print(f"Consultando información para canción: {track_name} de {artist_name} (MBID: {mbid})")
    
    try:
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        if response.status_code != 200:
            print(f"Error al obtener información de la canción {track_name}: {response.status_code}")
            print(f"Respuesta de error: {response.text[:200]}...")
            return None
        
        data = response.json()
        
        # Verificar si hay un mensaje de error en la respuesta JSON
        if 'error' in data:
            print(f"Error de la API de Last.fm: {data['message']} (código {data['error']})")
            return None
            
        if 'track' not in data:
            print(f"No se encontró información para la canción {track_name}")
            return None
        
        print(f"Información obtenida correctamente para canción: {track_name}")
        
        # Guardar en caché
        if lastfm_cache:
            lastfm_cache.put(params, data)
            
        return data['track']
    
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión al consultar canción {track_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error al decodificar respuesta JSON para canción {track_name}: {e}")
        print(f"Respuesta recibida: {response.text[:200]}...")
        return None
    except Exception as e:
        print(f"Error inesperado al consultar canción {track_name}: {e}")
        return None


# Modificar las funciones de añadir artistas, álbumes y canciones para incluir el ID del scrobble y el origen de datos
def add_artist_to_db(conn, artist_info, lastfm_username, scrobble_id=None, interactive=False):
    """
    Añade un nuevo artista a la base de datos con metadatos extendidos
    
    Args:
        conn: Conexión a la base de datos
        artist_info: Información del artista
        lastfm_username: Nombre de usuario de Last.fm para el origen de datos
        scrobble_id: ID del scrobble de donde proviene la información
        interactive: Si está activo el modo interactivo
    """
    cursor = conn.cursor()
    
    artist_name = artist_info.get('name', '')
    mbid = artist_info.get('mbid', '')
    url = artist_info.get('url', '')
    
    # Extraer bio
    bio = ''
    if 'bio' in artist_info and 'content' in artist_info['bio']:
        bio = artist_info['bio']['content']
    
    # Extraer tags
    tags = []
    if 'tags' in artist_info and 'tag' in artist_info['tags']:
        tag_list = artist_info['tags']['tag']
        if isinstance(tag_list, list):
            tags = [tag['name'] for tag in tag_list]
        else:
            tags = [tag_list['name']]
    tags_str = ','.join(tags)
    
    # Extraer artistas similares
    similar_artists = []
    if 'similar' in artist_info and 'artist' in artist_info['similar']:
        similar_list = artist_info['similar']['artist']
        if isinstance(similar_list, list):
            similar_artists = [{'name': a['name'], 'url': a.get('url', '')} for a in similar_list]
        else:
            similar_artists = [{'name': similar_list['name'], 'url': similar_list.get('url', '')}]
    similar_json = json.dumps(similar_artists) if similar_artists else ''
    
    # Origen personalizado para este usuario
    origen = f"scrobbles_{lastfm_username}"
    
    if interactive:
        print("\n" + "="*60)
        print(f"INFORMACIÓN DEL ARTISTA A AÑADIR:")
        print("="*60)
        print(f"Nombre: {artist_name}")
        print(f"MBID: {mbid}")
        print(f"URL: {url}")
        print(f"Tags: {tags_str}")
        print(f"Bio: {bio[:150]}..." if len(bio) > 150 else f"Bio: {bio}")
        print(f"Artistas similares: {len(similar_artists)}")
        print(f"Origen: {origen}")
        if scrobble_id:
            print(f"Scrobble ID: {scrobble_id}")
        print("-"*60)
        
        respuesta = input("\n¿Añadir este artista a la base de datos? (s/n): ").lower()
        if respuesta != 's':
            print("Operación cancelada por el usuario.")
            return None
    
    # Comprobar si la tabla tiene la columna lastfm_url
    cursor.execute("PRAGMA table_info(artists)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "lastfm_url" in columns:
        insert_sql = """
            INSERT INTO artists (
                name, mbid, tags, bio, lastfm_url, origen, similar_artists
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """
        params = (
            artist_name, 
            mbid, 
            tags_str, 
            bio, 
            url, 
            origen,
            similar_json
        )
    else:
        # Si no existe la columna lastfm_url, usar una versión alternativa
        print("Advertencia: La tabla 'artists' no tiene la columna 'lastfm_url'. Usando versión alternativa.")
        
        # Verificar si existe la columna website para usar en su lugar
        if "website" in columns:
            insert_sql = """
                INSERT INTO artists (
                    name, mbid, tags, bio, website, origen, similar_artists
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            """
            params = (
                artist_name, 
                mbid, 
                tags_str, 
                bio, 
                url, 
                origen,
                similar_json
            )
        else:
            # Si no hay columna lastfm_url ni website, omitir ese campo
            insert_sql = """
                INSERT INTO artists (
                    name, mbid, tags, bio, origen, similar_artists
                )
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
            """
            params = (
                artist_name, 
                mbid, 
                tags_str, 
                bio, 
                origen,
                similar_json
            )
    
    # Comprobar si existe la columna similar_artists
    if "similar_artists" not in columns:
        # Modificar la consulta para no incluir similar_artists
        insert_sql = insert_sql.replace(", similar_artists", "")
        params = params[:-1]  # Quitar el último parámetro (similar_json)
    
    try:
        cursor.execute(insert_sql, params)
        artist_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Artista añadido con ID: {artist_id}")
        return artist_id
    except sqlite3.Error as e:
        print(f"Error al añadir el artista {artist_name}: {e}")
        # Intentar imprimir información adicional sobre el error
        print(f"Columnas disponibles: {', '.join(columns)}")
        print(f"SQL: {insert_sql}")
        return None

def add_album_to_db(conn, album_info, artist_id, lastfm_username, scrobble_id=None, interactive=False):
    """
    Añade un nuevo álbum a la base de datos con metadatos extendidos de MusicBrainz,
    verificando primero si el álbum ya existe para evitar duplicados.
    
    Args:
        conn: Conexión a la base de datos
        album_info: Información del álbum
        artist_id: ID del artista
        lastfm_username: Nombre de usuario de Last.fm para el origen de datos
        scrobble_id: ID del scrobble de donde proviene la información
        interactive: Si está activo el modo interactivo
    """
    cursor = conn.cursor()
    
    album_name = album_info.get('name', '')
    mbid = album_info.get('mbid', '')
    url = album_info.get('url', '')
    
    # Verificar si el álbum ya existe
    cursor.execute("""
        SELECT id FROM albums 
        WHERE artist_id = ? AND (LOWER(name) = LOWER(?) OR mbid = ?)
    """, (artist_id, album_name, mbid if mbid else ''))
    
    existing_album = cursor.fetchone()
    if existing_album:
        print(f"Álbum '{album_name}' ya existe con ID {existing_album[0]}")
        return existing_album[0]
    
    # Verificar columnas disponibles en la tabla albums
    cursor.execute("PRAGMA table_info(albums)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Intentar obtener datos de MusicBrainz si hay MBID
    mb_album = None
    data_source = 'lastfm'  # Por defecto, Last.fm
    
    # Metadatos adicionales MusicBrainz - inicialización
    musicbrainz_albumid = ''
    musicbrainz_albumartistid = ''
    musicbrainz_releasegroupid = ''
    catalognumber = ''
    media = ''
    discnumber = ''
    releasecountry = ''
    originalyear = None
    label = ''
    genre = ''
    musicbrainz_url = ''
    
    if mbid:
        mb_album = get_album_from_musicbrainz(mbid)
        if mb_album:
            data_source = 'musicbrainz+lastfm'  # Si encontramos datos en MusicBrainz
            
            # Metadatos de MusicBrainz
            musicbrainz_albumid = mb_album.get('id', '')
            
            # URL de MusicBrainz
            musicbrainz_url = f"https://musicbrainz.org/release/{musicbrainz_albumid}" if musicbrainz_albumid else ''
            
            # Obtener albumartistid y releasegroupid
            if 'artist-credit' in mb_album and mb_album['artist-credit']:
                for credit in mb_album['artist-credit']:
                    if 'artist' in credit and 'id' in credit['artist']:
                        musicbrainz_albumartistid = credit['artist']['id']
                        break
            
            if 'release-group' in mb_album and 'id' in mb_album['release-group']:
                musicbrainz_releasegroupid = mb_album['release-group']['id']
            
            # Obtener catalognumber y label
            if 'label-info-list' in mb_album:
                for label_info in mb_album['label-info-list']:
                    if 'catalog-number' in label_info:
                        catalognumber = label_info['catalog-number']
                    
                    if 'label' in label_info and 'name' in label_info['label']:
                        label = label_info['label']['name']
                        break
            
            # Obtener media y discnumber
            if 'medium-list' in mb_album and mb_album['medium-list']:
                media_types = []
                for medium in mb_album['medium-list']:
                    if 'format' in medium:
                        media_types.append(medium['format'])
                media = ','.join(media_types)
                
                # Tomamos el primer disco como referencia para discnumber
                if 'position' in mb_album['medium-list'][0]:
                    discnumber = str(mb_album['medium-list'][0]['position'])
            
            # Obtener país de lanzamiento
            if 'country' in mb_album:
                releasecountry = mb_album['country']
            
            # Intentar obtener el año original
            if 'release-group' in mb_album and 'first-release-date' in mb_album['release-group']:
                first_release = mb_album['release-group']['first-release-date']
                if first_release and len(first_release) >= 4:
                    try:
                        originalyear = int(first_release[:4])
                    except ValueError:
                        pass
            
            # Obtener género si está disponible
            if 'tag-list' in mb_album:
                tags = [tag['name'] for tag in mb_album['tag-list']] if 'tag-list' in mb_album else []
                genre = ','.join(tags[:3]) if tags else ''
    
    # Usar nombre de MusicBrainz si está disponible
    if mb_album and 'title' in mb_album:
        album_name = mb_album.get('title', album_name)
        print(f"Usando nombre de MusicBrainz: {album_name}")
    
    # Extraer año
    year = None
    if 'releasedate' in album_info:
        try:
            release_date = album_info['releasedate'].strip()
            if release_date:
                year = datetime.datetime.strptime(release_date, '%d %b %Y, %H:%M').year
        except (ValueError, AttributeError):
            pass
    
    # Usar año original de MusicBrainz para el campo year si está disponible
    if originalyear and not year:
        year = originalyear
    
    # Número de pistas
    total_tracks = 0
    if 'tracks' in album_info and 'track' in album_info['tracks']:
        tracks = album_info['tracks']['track']
        if isinstance(tracks, list):
            total_tracks = len(tracks)
        else:
            total_tracks = 1
    
    # Intentar obtener número de pistas de MusicBrainz
    if mb_album and 'medium-list' in mb_album:
        mb_total_tracks = 0
        for medium in mb_album['medium-list']:
            if 'track-count' in medium:
                mb_total_tracks += int(medium['track-count'])
        
        if mb_total_tracks > 0:
            total_tracks = mb_total_tracks
            print(f"Usando total de pistas de MusicBrainz: {total_tracks}")
    
    # Origen personalizado para este usuario
    origen = f"scrobbles_{lastfm_username}"
    
    # Obtener el nombre del artista para mostrarlo en modo interactivo
    artist_name = ""
    if interactive:
        try:
            cursor.execute("SELECT name FROM artists WHERE id = ?", (artist_id,))
            result = cursor.fetchone()
            if result:
                artist_name = result[0]
        except sqlite3.Error as e:
            print(f"Error al obtener el nombre del artista: {e}")
    
    if interactive:
        print("\n" + "="*60)
        print(f"INFORMACIÓN DEL ÁLBUM A AÑADIR:")
        print("="*60)
        print(f"Nombre: {album_name}")
        print(f"Artista: {artist_name} (ID: {artist_id})")
        print(f"MBID: {mbid}")
        print(f"URL: {url}")
        print(f"Año: {year}")
        print(f"Año original: {originalyear}")
        print(f"Total pistas: {total_tracks}")
        print(f"MusicBrainz Album ID: {musicbrainz_albumid}")
        print(f"MusicBrainz Album Artist ID: {musicbrainz_albumartistid}")
        print(f"MusicBrainz Release Group ID: {musicbrainz_releasegroupid}")
        print(f"MusicBrainz URL: {musicbrainz_url}")
        print(f"Número de catálogo: {catalognumber}")
        print(f"Medio: {media}")
        print(f"Número de disco: {discnumber}")
        print(f"País de lanzamiento: {releasecountry}")
        print(f"Sello: {label}")
        print(f"Género: {genre}")
        print(f"Origen de datos: {origen}")
        print(f"Data source: {data_source}")
        if scrobble_id:
            print(f"Scrobble ID: {scrobble_id}")
        print("-"*60)
        
        respuesta = input("\n¿Añadir este álbum a la base de datos? (s/n): ").lower()
        if respuesta != 's':
            print("Operación cancelada por el usuario.")
            return None
    
    # Construir la consulta SQL dinámicamente en función de las columnas disponibles
    insert_columns = ["artist_id", "name", "mbid", "origen"]
    insert_values = [artist_id, album_name, mbid, origen]
    
    # Añadir campos opcionales si existen en la tabla
    if "year" in columns and year:
        insert_columns.append("year")
        insert_values.append(year)
    
    if "lastfm_url" in columns and url:
        insert_columns.append("lastfm_url")
        insert_values.append(url)
    
    if "total_tracks" in columns and total_tracks:
        insert_columns.append("total_tracks")
        insert_values.append(total_tracks)
    
    if "scrobble_id" in columns and scrobble_id:
        insert_columns.append("scrobble_id")
        insert_values.append(scrobble_id)
    
    if "data_source" in columns:
        insert_columns.append("data_source")
        insert_values.append(data_source)
    
    # Campos de MusicBrainz
    if "musicbrainz_albumid" in columns and musicbrainz_albumid:
        insert_columns.append("musicbrainz_albumid")
        insert_values.append(musicbrainz_albumid)
    
    if "musicbrainz_albumartistid" in columns and musicbrainz_albumartistid:
        insert_columns.append("musicbrainz_albumartistid")
        insert_values.append(musicbrainz_albumartistid)
    
    if "musicbrainz_releasegroupid" in columns and musicbrainz_releasegroupid:
        insert_columns.append("musicbrainz_releasegroupid")
        insert_values.append(musicbrainz_releasegroupid)
    
    if "musicbrainz_url" in columns and musicbrainz_url:
        insert_columns.append("musicbrainz_url")
        insert_values.append(musicbrainz_url)
    
    if "catalognumber" in columns and catalognumber:
        insert_columns.append("catalognumber")
        insert_values.append(catalognumber)
    
    if "media" in columns and media:
        insert_columns.append("media")
        insert_values.append(media)
    
    if "discnumber" in columns and discnumber:
        insert_columns.append("discnumber")
        insert_values.append(discnumber)
    
    if "releasecountry" in columns and releasecountry:
        insert_columns.append("releasecountry")
        insert_values.append(releasecountry)
    
    if "originalyear" in columns and originalyear:
        insert_columns.append("originalyear")
        insert_values.append(originalyear)
    
    if "label" in columns and label:
        insert_columns.append("label")
        insert_values.append(label)
    
    if "genre" in columns and genre:
        insert_columns.append("genre")
        insert_values.append(genre)
    
    try:
        # Construir la consulta SQL con las columnas dinámicas
        placeholders = ", ".join(["?"] * len(insert_values))
        columns_str = ", ".join(insert_columns)
        
        query = f"""
            INSERT INTO albums ({columns_str})
            VALUES ({placeholders})
            RETURNING id
        """
        
        cursor.execute(query, insert_values)
        album_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Álbum añadido con ID: {album_id}")
        return album_id
    except sqlite3.Error as e:
        print(f"Error al añadir el álbum {album_name}: {e}")
        print(f"Consulta: {query}")
        print(f"Valores: {insert_values}")
        print(f"Columnas disponibles: {columns}")
        return None


        
def add_song_to_db(conn, track_info, album_id, artist_id, lastfm_username, scrobble_id=None, interactive=False):
    """
    Añade una nueva canción a la base de datos con metadatos extendidos,
    usando la tabla songs general, no una tabla personalizada por usuario
    
    Args:
        conn: Conexión a la base de datos
        track_info: Información de la canción
        album_id: ID del álbum
        artist_id: ID del artista
        lastfm_username: Nombre de usuario de Last.fm para el origen de datos
        scrobble_id: ID del scrobble de donde proviene la información
        interactive: Si está activo el modo interactivo
    """
    cursor = conn.cursor()
    
    track_name = track_info.get('name', '')
    mbid = track_info.get('mbid', '')
    lastfm_url = track_info.get('url', '')
    
    # Obtener información adicional
    duration = None
    if 'duration' in track_info:
        try:
            duration = int(track_info['duration']) // 1000  # Convertir de ms a segundos
        except (ValueError, TypeError):
            pass
    
    # Obtener nombre del artista y álbum
    artist_name = ''
    album_name = ''
    
    # Obtener nombre del artista
    if artist_id:
        try:
            cursor.execute("SELECT name FROM artists WHERE id = ?", (artist_id,))
            result = cursor.fetchone()
            if result:
                artist_name = result[0]
        except sqlite3.Error:
            pass
    
    # Si no se encontró nombre del artista, usar el de track_info
    if not artist_name and 'artist' in track_info:
        if isinstance(track_info['artist'], dict):
            artist_name = track_info['artist'].get('name', '')
        else:
            artist_name = track_info['artist']
    
    # Obtener nombre del álbum
    if album_id:
        try:
            cursor.execute("SELECT name FROM albums WHERE id = ?", (album_id,))
            result = cursor.fetchone()
            if result:
                album_name = result[0]
        except sqlite3.Error:
            pass
    
    # Si no se encontró nombre del álbum, usar el de track_info
    if not album_name and 'album' in track_info:
        if isinstance(track_info['album'], dict):
            album_name = track_info['album'].get('title', '')
        else:
            album_name = track_info['album']
    
    # Obtener género
    genre = ''
    if 'toptags' in track_info and 'tag' in track_info['toptags']:
        tags = track_info['toptags']['tag']
        if isinstance(tags, list) and tags:
            genre = tags[0]['name']
        elif isinstance(tags, dict):
            genre = tags.get('name', '')
    
    # MusicBrainz Recording ID
    musicbrainz_recordingid = ''
    if 'mbid' in track_info:
        musicbrainz_recordingid = track_info['mbid']
    
    # Timestamp actual
    added_timestamp = int(time.time())
    
    # Información de fecha para estadísticas
    now = datetime.datetime.now()
    added_week = now.isocalendar()[1]
    added_month = now.month
    added_year = now.year
    
    # Mostrar información en modo interactivo
    if interactive:
        print("\n" + "="*60)
        print(f"INFORMACIÓN DE LA CANCIÓN A AÑADIR:")
        print("="*60)
        print(f"Título: {track_name}")
        print(f"Artista: {artist_name} (ID: {artist_id})")
        print(f"Álbum: {album_name} (ID: {album_id})")
        print(f"MBID: {mbid}")
        print(f"Duración: {duration} segundos")
        print(f"Género: {genre}")
        print(f"MusicBrainz Recording ID: {musicbrainz_recordingid}")
        print(f"URL Last.fm: {lastfm_url}")
        print("-"*60)
        
        respuesta = input("\n¿Añadir esta canción a la base de datos? (s/n): ").lower()
        if respuesta != 's':
            print("Operación cancelada por el usuario.")
            return None
    
    try:
        # Verificar si la canción ya existe
        cursor.execute("""
            SELECT id FROM songs 
            WHERE LOWER(title) = LOWER(?) AND LOWER(artist) = LOWER(?)
            AND (LOWER(album) = LOWER(?) OR (album IS NULL AND ? IS NULL))
        """, (track_name, artist_name, album_name, album_name))
        
        existing_song = cursor.fetchone()
        if existing_song:
            song_id = existing_song[0]
            print(f"Canción ya existe con ID: {song_id}")
            
            # Actualizar información si tenemos más datos
            cursor.execute("""
                UPDATE songs 
                SET mbid = COALESCE(mbid, ?),
                    duration = COALESCE(duration, ?),
                    genre = COALESCE(genre, ?),
                    musicbrainz_recordingid = COALESCE(musicbrainz_recordingid, ?)
                WHERE id = ?
            """, (mbid, duration, genre, musicbrainz_recordingid, song_id))
            
            conn.commit()
            return song_id
        
        # Insertar nueva canción
        cursor.execute("""
            INSERT INTO songs (
                title, artist, album, album_artist, mbid, duration, genre,
                added_timestamp, added_week, added_month, added_year,
                origen, musicbrainz_recordingid
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """, (
            track_name,
            artist_name,
            album_name,
            artist_name,  # album_artist = artist
            mbid,
            duration,
            genre,
            added_timestamp,
            added_week,
            added_month,
            added_year,
            f"scrobbles_{lastfm_username}",
            musicbrainz_recordingid
        ))
        
        song_id = cursor.fetchone()[0]
        
        # Crear enlaces adicionales
        if lastfm_url:
            try:
                cursor.execute("""
                    INSERT INTO song_links (song_id, lastfm_url)
                    VALUES (?, ?)
                """, (song_id, lastfm_url))
            except sqlite3.Error as e:
                print(f"Error al crear enlace de canción: {e}")
        
        conn.commit()
        print(f"Canción añadida con ID: {song_id}")
        return song_id
        
    except sqlite3.Error as e:
        print(f"Error al añadir canción {track_name}: {e}")
        return None
        
# SCROBBLES
def get_lastfm_scrobbles(lastfm_username, lastfm_api_key, from_timestamp=0, limit=200, progress_callback=None, filter_duplicates=True):
    """
    Obtiene los scrobbles de Last.fm para un usuario desde un timestamp específico.
    Implementa caché para páginas ya consultadas.
    
    Args:
        lastfm_username: Nombre de usuario de Last.fm
        lastfm_api_key: API key de Last.fm
        from_timestamp: Timestamp desde el que obtener scrobbles
        limit: Número máximo de scrobbles por página
        progress_callback: Función para reportar progreso (mensaje, porcentaje)
    """
    global lastfm_cache
    
    all_tracks = []
    page = 1
    total_pages = 1
    
    # Verificar si hay caché disponible
    if lastfm_cache is not None:
        print(f"Usando caché Last.fm con {len(lastfm_cache.cache)} entradas")
    else:
        print("No hay caché Last.fm disponible")
    
    while page <= total_pages:
        # Actualizar progreso
        if progress_callback:
            progress = (page / total_pages * 15) if total_pages > 1 else 5
            progress_callback(f"Obteniendo página {page} de {total_pages}", progress)
        else:
            print(f"Obteniendo página {page} de {total_pages}")
        
        params = {
            'method': 'user.getrecenttracks',
            'user': lastfm_username,
            'api_key': lastfm_api_key,
            'format': 'json',
            'limit': limit,
            'page': page,
            'from': from_timestamp
        }
        
        # Verificar caché para esta página específica
        cached_data = None
        if lastfm_cache:
            # No cacheamos scrobbles más recientes (última página si empezamos desde la 1)
            if not (from_timestamp == 0 and page == 1):
                cache_key = {
                    'method': 'user.getrecenttracks',
                    'user': lastfm_username,
                    'page': page,
                    'from': from_timestamp,
                    'limit': limit
                }
                cached_data = lastfm_cache.get(cache_key)
                if cached_data:
                    print(f"Usando datos en caché para página {page} de scrobbles")
        
        if cached_data:
            data = cached_data
        else:
            try:
                response = get_with_retry('http://ws.audioscrobbler.com/2.0/', params)
                
                if not response or response.status_code != 200:
                    error_msg = f"Error al obtener scrobbles: {response.status_code if response else 'Sin respuesta'}"
                    if progress_callback:
                        progress_callback(error_msg, 0)
                    else:
                        print(error_msg)
                        
                    if page > 1:  # Si hemos obtenido algunas páginas, devolvemos lo que tenemos
                        break
                    else:
                        return []
                
                data = response.json()
                
                # Guardar en caché todas las páginas excepto la primera si empezamos desde 0
                # (porque la primera página contiene los scrobbles más recientes que cambian)
                if lastfm_cache and not (from_timestamp == 0 and page == 1):
                    cache_key = {
                        'method': 'user.getrecenttracks',
                        'user': lastfm_username,
                        'page': page,
                        'from': from_timestamp,
                        'limit': limit
                    }
                    lastfm_cache.put(cache_key, data)
                    print(f"Guardando en caché Last.fm página {page}")
                
            except Exception as e:
                error_msg = f"Error al procesar página {page}: {str(e)}"
                if progress_callback:
                    progress_callback(error_msg, 0)
                else:
                    print(error_msg)
                
                if page > 1:  # Si hemos obtenido algunas páginas, devolvemos lo que tenemos
                    break
                else:
                    return []
        
        # Comprobar si hay tracks
        if 'recenttracks' not in data or 'track' not in data['recenttracks']:
            break
        
        # Actualizar total_pages
        total_pages = int(data['recenttracks']['@attr']['totalPages'])
        
        # Añadir tracks a la lista
        tracks = data['recenttracks']['track']
        if not isinstance(tracks, list):
            tracks = [tracks]
        
        # Filtrar tracks que están siendo escuchados actualmente (no tienen date)
        filtered_tracks = [track for track in tracks if 'date' in track]
        all_tracks.extend(filtered_tracks)
        
        # Reportar progreso
        if progress_callback:
            progress = (page / total_pages * 15) if total_pages > 1 else 15
            progress_callback(f"Obtenida página {page} de {total_pages} ({len(filtered_tracks)} tracks)", progress)
        else:
            print(f"Obtenida página {page} de {total_pages} ({len(filtered_tracks)} tracks)")
        
        page += 1
        # Pequeña pausa para no saturar la API
        time.sleep(0.25)
    
    # Informar del total obtenido
    if progress_callback:
        progress_callback(f"Obtenidos {len(all_tracks)} scrobbles en total", 30)
    else:
        print(f"Obtenidos {len(all_tracks)} scrobbles en total")
        
    # At the end of the function, right before returning all_tracks:
    if filter_duplicates and all_tracks:
        if progress_callback:
            progress_callback("Filtrando scrobbles duplicados...", 95)
        else:
            print("Filtrando scrobbles duplicados...")
        
        filtered_tracks = filter_duplicate_scrobbles(all_tracks)
        
        if progress_callback:
            progress_callback(f"Obtenidos {len(filtered_tracks)} scrobbles únicos", 100)
        else:
            print(f"Obtenidos {len(filtered_tracks)} scrobbles únicos")
            
        return filtered_tracks
    
    # Only return the original all_tracks if filter_duplicates is False
    return all_tracks


def get_with_retry(url, params, max_retries=3, retry_delay=1, timeout=10):
    """Realiza una petición HTTP con reintentos en caso de error
    
    Args:
        url: URL a consultar
        params: Parámetros para la petición
        max_retries: Número máximo de reintentos
        retry_delay: Tiempo base de espera entre reintentos (se incrementará exponencialmente)
        timeout: Tiempo máximo de espera para la petición
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            
            # Si hay límite de tasa, esperar y reintentar
            if response.status_code == 429:  # Rate limit
                wait_time = int(response.headers.get('Retry-After', retry_delay * 2))
                print(f"Rate limit alcanzado. Esperando {wait_time} segundos...")
                time.sleep(wait_time)
                continue
            
            return response
            
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            print(f"Error en intento {attempt+1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                # Backoff exponencial
                sleep_time = retry_delay * (2 ** attempt)
                print(f"Reintentando en {sleep_time} segundos...")
                time.sleep(sleep_time)
    
    return None

def update_artist_in_db(conn, artist_id, artist_info):
    """
    Actualiza información de un artista existente desde Last.fm sin modificar 'origen'
    
    Args:
        conn: Conexión a la base de datos
        artist_id: ID del artista a actualizar
        artist_info: Información del artista obtenida desde Last.fm
        
    Returns:
        True si se actualizó correctamente, False en caso contrario
    """
    # Verificar si este artista es de solo lectura (origen 'local')
    if is_read_only(conn, 'artists', artist_id):
        print(f"Artista con ID {artist_id} es de origen 'local', no se actualizará")
        return False
    
    cursor = conn.cursor()
    
    # Extraer datos del artista
    mbid = artist_info.get('mbid', '')
    url = artist_info.get('url', '')
    
    # Extraer tags
    tags = []
    if 'tags' in artist_info and 'tag' in artist_info['tags']:
        tag_list = artist_info['tags']['tag']
        if isinstance(tag_list, list):
            tags = [tag['name'] for tag in tag_list]
        else:
            tags = [tag_list['name']]
    tags_str = ','.join(tags)
    
    # Extraer bio
    bio = ''
    if 'bio' in artist_info and 'content' in artist_info['bio']:
        bio = artist_info['bio']['content']
    
    # Extraer artistas similares
    similar_artists = []
    if 'similar' in artist_info and 'artist' in artist_info['similar']:
        similar_list = artist_info['similar']['artist']
        if isinstance(similar_list, list):
            similar_artists = [{'name': a['name'], 'url': a.get('url', '')} for a in similar_list]
        else:
            similar_artists = [{'name': similar_list['name'], 'url': similar_list.get('url', '')}]
    similar_json = json.dumps(similar_artists) if similar_artists else ''
    
    # Verificar qué columnas están disponibles
    cursor.execute("PRAGMA table_info(artists)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Preparar actualizaciones - nunca modificar 'origen'
    updates = []
    params = []
    
    # Solo actualizar campos si tienen datos
    if mbid:
        updates.append("mbid = COALESCE(mbid, ?)")
        params.append(mbid)
    
    if tags_str:
        updates.append("tags = COALESCE(tags, ?)")
        params.append(tags_str)
    
    if bio:
        updates.append("bio = COALESCE(bio, ?)")
        params.append(bio)
    
    if url and 'lastfm_url' in columns:
        updates.append("lastfm_url = COALESCE(lastfm_url, ?)")
        params.append(url)
    
    if similar_json and 'similar_artists' in columns:
        updates.append("similar_artists = COALESCE(similar_artists, ?)")
        params.append(similar_json)
    
    # Agregar timestamp si no existe
    now = int(time.time())
    if 'added_timestamp' in columns:
        updates.append("added_timestamp = COALESCE(added_timestamp, ?)")
        params.append(now)
    
    if updates:
        try:
            query = f"UPDATE artists SET {', '.join(updates)} WHERE id = ?"
            params.append(artist_id)
            cursor.execute(query, params)
            conn.commit()
            print(f"Artista {artist_id} actualizado correctamente (metadatos)")
            return True
        except sqlite3.Error as e:
            print(f"Error al actualizar artista {artist_id}: {e}")
    
    return False


def update_album_in_db(conn, album_id, album_info):
    """Actualiza información de un álbum existente desde Last.fm y MusicBrainz"""
    # Check if this album is read-only first
    if is_read_only(conn, 'albums', album_id):
        print(f"Álbum con ID {album_id} es de origen 'local', no se actualizará")
        return False

    cursor = conn.cursor()
    
    album_name = album_info.get('name', '')
    mbid = album_info.get('mbid', '')
    url = album_info.get('url', '')
    
    # Intentar obtener datos adicionales de MusicBrainz
    mb_album = None
    if mbid:
        mb_album = get_album_from_musicbrainz(mbid)
    
    # Recopilar actualizaciones
    updates = []
    params = []
    
    # Metadatos básicos
    if mbid:
        updates.append("mbid = COALESCE(mbid, ?)")
        params.append(mbid)
    
    # Extraer año
    year = None
    if 'releasedate' in album_info:
        try:
            release_date = album_info['releasedate'].strip()
            if release_date:
                year = datetime.datetime.strptime(release_date, '%d %b %Y, %H:%M').year
                updates.append("year = COALESCE(year, ?)")
                params.append(year)
        except (ValueError, AttributeError):
            pass
    
    if url:
        updates.append("lastfm_url = COALESCE(lastfm_url, ?)")
        params.append(url)
    
    # Número de pistas
    total_tracks = 0
    if 'tracks' in album_info and 'track' in album_info['tracks']:
        tracks = album_info['tracks']['track']
        if isinstance(tracks, list):
            total_tracks = len(tracks)
        else:
            total_tracks = 1
        
        updates.append("total_tracks = COALESCE(total_tracks, ?)")
        params.append(total_tracks)
    
    # Siempre actualizar origen a 'scrobbles' para marcar que ha sido verificado
    updates.append("origen = 'scrobbles'")
    
    # Campos adicionales de MusicBrainz
    if mb_album:
        # Album ID
        if 'id' in mb_album:
            updates.append("musicbrainz_albumid = COALESCE(musicbrainz_albumid, ?)")
            params.append(mb_album['id'])
        
        # Album Artist ID
        if 'artist-credit' in mb_album and mb_album['artist-credit']:
            for credit in mb_album['artist-credit']:
                if 'artist' in credit and 'id' in credit['artist']:
                    updates.append("musicbrainz_albumartistid = COALESCE(musicbrainz_albumartistid, ?)")
                    params.append(credit['artist']['id'])
                    break
        
        # Release Group ID
        if 'release-group' in mb_album and 'id' in mb_album['release-group']:
            updates.append("musicbrainz_releasegroupid = COALESCE(musicbrainz_releasegroupid, ?)")
            params.append(mb_album['release-group']['id'])
        
        # Catalog Number
        if 'label-info-list' in mb_album:
            for label_info in mb_album['label-info-list']:
                if 'catalog-number' in label_info:
                    updates.append("catalognumber = COALESCE(catalognumber, ?)")
                    params.append(label_info['catalog-number'])
                    break
        
        # Media Type and Disc Number
        if 'medium-list' in mb_album and mb_album['medium-list']:
            media_types = []
            for medium in mb_album['medium-list']:
                if 'format' in medium:
                    media_types.append(medium['format'])
            
            if media_types:
                updates.append("media = COALESCE(media, ?)")
                params.append(','.join(media_types))
            
            # First disc position as discnumber
            if 'position' in mb_album['medium-list'][0]:
                updates.append("discnumber = COALESCE(discnumber, ?)")
                params.append(str(mb_album['medium-list'][0]['position']))
        
        # Country of release
        if 'country' in mb_album:
            updates.append("releasecountry = COALESCE(releasecountry, ?)")
            params.append(mb_album['country'])
        
        # Original Year
        if 'release-group' in mb_album and 'first-release-date' in mb_album['release-group']:
            first_release = mb_album['release-group']['first-release-date']
            if first_release and len(first_release) >= 4:
                try:
                    originalyear = int(first_release[:4])
                    updates.append("originalyear = COALESCE(originalyear, ?)")
                    params.append(originalyear)
                except ValueError:
                    pass
    
    if updates:
        sql = f"UPDATE albums SET {', '.join(updates)} WHERE id = ?"
        params.append(album_id)
        
        try:
            cursor.execute(sql, params)
            conn.commit()
            print(f"Álbum con ID {album_id} actualizado correctamente")
            return True
        except sqlite3.Error as e:
            print(f"Error al actualizar el álbum ID {album_id}: {e}")
    
    return False

def update_song_in_db(conn, song_id, track_info):
    """Actualiza información de una canción existente desde Last.fm y MusicBrainz"""
    # Check if this song is read-only first
    if is_read_only(conn, 'songs', song_id):
        print(f"Canción con ID {song_id} es de origen 'local', no se actualizará")
        return False

    cursor = conn.cursor()
    
    track_name = track_info.get('name', '')
    mbid = track_info.get('mbid', '')
    
    # Intentar obtener datos adicionales de MusicBrainz
    mb_track = None
    if mbid:
        mb_track = get_track_from_musicbrainz(mbid)
    
    # Recopilar actualizaciones
    updates = []
    params = []
    
    # Metadatos básicos
    if mbid:
        updates.append("mbid = COALESCE(mbid, ?)")
        params.append(mbid)
    
    # Duración
    if 'duration' in track_info:
        try:
            duration = int(track_info['duration']) // 1000  # Convertir de ms a segundos
            updates.append("duration = COALESCE(duration, ?)")
            params.append(duration)
        except (ValueError, TypeError):
            pass
    
    # Género
    if 'toptags' in track_info and 'tag' in track_info['toptags']:
        tags = track_info['toptags']['tag']
        genre = ''
        if isinstance(tags, list) and tags:
            genre = tags[0]['name']
        elif isinstance(tags, dict):
            genre = tags.get('name', '')
        
        if genre:
            updates.append("genre = COALESCE(genre, ?)")
            params.append(genre)
    
    # Campos adicionales de MusicBrainz
    if mb_track:
        # Recording ID
        if 'id' in mb_track:
            updates.append("musicbrainz_recordingid = COALESCE(musicbrainz_recordingid, ?)")
            params.append(mb_track['id'])
        
        # Artist ID
        if 'artist-credit' in mb_track and mb_track['artist-credit']:
            for credit in mb_track['artist-credit']:
                if 'artist' in credit and 'id' in credit['artist']:
                    updates.append("musicbrainz_artistid = COALESCE(musicbrainz_artistid, ?)")
                    params.append(credit['artist']['id'])
                    break
        
        # Album & Release Group Info
        if 'release-list' in mb_track and mb_track['release-list'] and mb_track['release-list']:
            for release in mb_track['release-list']:
                # Obtener album artist ID
                if 'artist-credit' in release:
                    for credit in release['artist-credit']:
                        if 'artist' in credit and 'id' in credit['artist']:
                            updates.append("musicbrainz_albumartistid = COALESCE(musicbrainz_albumartistid, ?)")
                            params.append(credit['artist']['id'])
                            break
                
                # Obtener release group ID
                if 'release-group' in release and 'id' in release['release-group']:
                    updates.append("musicbrainz_releasegroupid = COALESCE(musicbrainz_releasegroupid, ?)")
                    params.append(release['release-group']['id'])
                    break
    
    # Siempre actualizar origen a 'scrobbles' para marcar que ha sido verificado
    updates.append("origen = 'scrobbles'")
    
    if updates:
        sql = f"UPDATE songs SET {', '.join(updates)} WHERE id = ?"
        params.append(song_id)
        
        try:
            cursor.execute(sql, params)
            conn.commit()
            print(f"Canción con ID {song_id} actualizada correctamente")
            return True
        except sqlite3.Error as e:
            print(f"Error al actualizar la canción ID {song_id}: {e}")
    
    return False

def ask_to_continue():
    """Pregunta al usuario si desea continuar procesando"""
    while True:
        resp = input("\n¿Continuar procesando? (s/n/a para automático): ").lower()
        if resp == 's':
            return True, False
        elif resp == 'n':
            return False, False
        elif resp == 'a':
            return True, True
    return False, False






def agrupar_scrobbles_por_artista_album(tracks):
    """
    Agrupa scrobbles por artista y álbum para procesarlos de manera más eficiente
    y evitar insertar duplicados.
    
    Args:
        tracks: Lista de scrobbles obtenidos de Last.fm
        
    Returns:
        Un diccionario agrupado con la siguiente estructura:
        {
            'artista1': {
                'info': {track info del artista},
                'albums': {
                    'album1': {
                        'info': {track info del álbum},
                        'tracks': [lista de tracks de este álbum]
                    },
                    'album2': {...}
                }
            },
            'artista2': {...}
        }
    """
    agrupado = {}
    
    print(f"Agrupando {len(tracks)} scrobbles por artista y álbum...")
    
    for track in tracks:
        artist_name = track['artist']['#text']
        album_name = track['album']['#text'] if track['album']['#text'] else None
        
        # Asegurarse de que el artista está en el diccionario
        if artist_name not in agrupado:
            agrupado[artist_name] = {
                'info': track,  # Guardamos un track para tener la info del artista
                'albums': {}
            }
        
        # Si el álbum existe y no está en el diccionario del artista, añadirlo
        if album_name:
            if album_name not in agrupado[artist_name]['albums']:
                agrupado[artist_name]['albums'][album_name] = {
                    'info': track,  # Guardamos un track para tener la info del álbum
                    'tracks': []
                }
            
            # Añadir el track a la lista de tracks del álbum
            agrupado[artist_name]['albums'][album_name]['tracks'].append(track)
        else:
            # Si no hay álbum, crear una categoría especial para singles/desconocidos
            singles_key = "Singles o sin álbum"
            if singles_key not in agrupado[artist_name]['albums']:
                agrupado[artist_name]['albums'][singles_key] = {
                    'info': None,
                    'tracks': []
                }
            agrupado[artist_name]['albums'][singles_key]['tracks'].append(track)
    
    # Contar estadísticas para información
    total_artists = len(agrupado)
    total_albums = sum(len(artist_data['albums']) for artist_data in agrupado.values())
    
    print(f"Agrupación completada: {total_artists} artistas, {total_albums} álbumes")
    
    return agrupado


def is_read_only(conn, table, record_id):
    """
    Determina si un registro debe tratarse como de solo lectura
    
    Args:
        conn: Conexión a la base de datos
        table: Nombre de la tabla a verificar ('artists', 'albums', o 'songs')
        record_id: ID del registro a verificar
    
    Returns:
        True SOLO si origen es exactamente 'local', False en cualquier otro caso
    """
    cursor = conn.cursor()
    cursor.execute(f"SELECT origen FROM {table} WHERE id = ?", (record_id,))
    result = cursor.fetchone()
    
    if not result:
        return False  # El registro no existe
    
    origen = result[0]
    # Solo es read-only si origen es exactamente 'local'
    return origen == 'canttouchit'

def get_tracks_from_lastfm_album(album_lastfm_url, lastfm_api_key):
    """
    Extrae información de canciones desde la URL de un álbum en Last.fm
    
    Args:
        album_lastfm_url: URL del álbum en Last.fm
        lastfm_api_key: API key de Last.fm
    
    Returns:
        Lista de diccionarios con información de las canciones
    """
    if not album_lastfm_url or not lastfm_api_key:
        return []
    
    # Intentar extraer el artista y el álbum desde la URL
    # Formato típico: https://www.last.fm/music/Artist+Name/Album+Name
    try:
        parts = album_lastfm_url.strip('/').split('/')
        if len(parts) >= 5 and parts[3] == 'music':
            artist_name = parts[4].replace('+', ' ')
            album_name = parts[5].replace('+', ' ') if len(parts) > 5 else None
        else:
            # Si no podemos extraer de la URL, no podemos continuar
            return []
    except Exception as e:
        print(f"Error al parsear URL de álbum '{album_lastfm_url}': {e}")
        return []
    
    # Construir parámetros para la API de Last.fm
    params = {
        'method': 'album.getInfo',
        'artist': artist_name,
        'album': album_name,
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    # Verificar en caché primero (podemos reutilizar el caché existente)
    global lastfm_cache
    if lastfm_cache:
        cached_result = lastfm_cache.get(params)
        if cached_result and 'album' in cached_result and 'tracks' in cached_result['album']:
            print(f"Usando datos en caché para álbum Last.fm: {album_name}")
            return _extract_tracks_from_album_info(cached_result['album'])
    
    try:
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        if response.status_code != 200:
            print(f"Error al obtener información del álbum {album_name}: {response.status_code}")
            return []
        
        data = response.json()
        
        # Verificar si hay error en la respuesta
        if 'error' in data:
            print(f"Error de Last.fm: {data['message']}")
            return []
            
        if 'album' not in data:
            print(f"No se encontró información para el álbum {album_name}")
            return []
        
        # Guardar en caché
        if lastfm_cache:
            lastfm_cache.put(params, data)        
        # Extraer y devolver la información de las canciones
        return _extract_tracks_from_album_info(data['album'])
    
    except Exception as e:
        print(f"Error al consultar información del álbum {album_name}: {e}")
        return []

def _extract_tracks_from_album_info(album_info):
    """
    Extrae la información de las canciones de un álbum
    desde la respuesta de Last.fm
    """
    tracks = []
    
    # Verificar que el álbum tenga canciones
    if 'tracks' not in album_info or 'track' not in album_info['tracks']:
        return tracks
    
    # Last.fm puede devolver un único track o una lista
    track_data = album_info['tracks']['track']
    
    # Si es un solo track, convertirlo a lista
    if not isinstance(track_data, list):
        track_data = [track_data]
    
    # Extraer información relevante de cada canción
    for track in track_data:
        tracks.append({
            'name': track.get('name', ''),
            'artist': album_info.get('artist', ''),
            'album': album_info.get('name', ''),
            'lastfm_url': track.get('url', ''),
            'duration': track.get('duration', 0),
            'mbid': track.get('mbid', '')
        })
    
    return tracks




def check_api_key(lastfm_api_key):
    """Comprueba si la API key de Last.fm es válida"""
    print("Verificando API key de Last.fm...")
    params = {
        'method': 'auth.getSession',
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    try:
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        # Una API key incorrecta debería devolver un error 403 o un mensaje de error en JSON
        if response.status_code == 403:
            print("API key inválida: Error 403 Forbidden")
            return False
        
        data = response.json()
        if 'error' in data and data['error'] == 10:
            print("API key inválida: Error de autenticación")
            return False
        
        # Si llegamos aquí, la key parece válida aunque el método específico requiera más parámetros
        print("API key parece válida")
        return True
        
    except Exception as e:
        print(f"Error al verificar API key: {e}")
        return False


            
class LastFMScrobbler:
    """Class to manage Last.fm scrobbles in the database"""
    
    def __init__(self, db_path, lastfm_user, lastfm_api_key, progress_callback=None, cache_dir=None, add_items=True):
        """
        Initializes the Last.fm scrobbler
        
        Args:
            db_path: Path to the SQLite database file
            lastfm_user: Last.fm username
            lastfm_api_key: Last.fm API key
            progress_callback: Optional callback function for progress updates
            cache_dir: Optional directory for cache files
            add_items: Whether to add artists, albums, and songs
        """
        self.db_path = db_path
        self.lastfm_user = lastfm_user
        self.lastfm_api_key = lastfm_api_key
        self.conn = None
        self.existing_artists = {}
        self.existing_albums = {}
        self.existing_songs = {}
        self.progress_callback = progress_callback
        self._interactive_mode = False
        self._cache_dir = None  # Initialize to None
        self._add_items = add_items  # Flag to determine whether to add artists, albums, and songs
        
        # Set cache_dir through the setter
        if cache_dir:
            self.cache_dir = cache_dir
        
    @property
    def cache_dir(self):
        return self._cache_dir
        
    @cache_dir.setter
    def cache_dir(self, value):
        self._cache_dir = value
        if value:
            # Make sure setup_musicbrainz is accessible
            global setup_musicbrainz
            if 'setup_musicbrainz' in globals():
                setup_musicbrainz(value)
            else:
                print("WARNING: setup_musicbrainz is not defined globally")
        
    @property
    def interactive_mode(self):
        return self._interactive_mode
        
    @interactive_mode.setter
    def interactive_mode(self, value):
        self._interactive_mode = value
        global INTERACTIVE_MODE
        INTERACTIVE_MODE = value
    
    @property
    def add_items(self):
        return self._add_items
    
    @add_items.setter
    def add_items(self, value):
        self._add_items = value
    
    def _update_progress(self, message, percentage=None, extra_data=None):
        """Updates progress through the callback if available"""
        if self.progress_callback:
            if extra_data:
                self.progress_callback(message, percentage, extra_data)
            else:
                self.progress_callback(message, percentage)
        else:
            print(message)
    
    def connect(self):
        """Connects to the database and loads existing elements"""
        if self.conn is None:
            self._update_progress("Connecting to database...", 0)
            self.conn = sqlite3.connect(self.db_path)
            # Ensure the necessary tables exist for this user
            setup_database(self.conn, self.lastfm_user)
            
            # Ensure that all necessary columns exist
            self.ensure_columns_exist()
            
            self._update_progress("Loading existing elements...", 5)
            self.existing_artists, self.existing_albums, self.existing_songs = get_existing_items(self.conn)
            self._update_progress(f"Loaded {len(self.existing_artists)} artists, {len(self.existing_albums)} albums, {len(self.existing_songs)} songs", 10)
        return self.conn
    
    def ensure_columns_exist(self):
        """Ensures that all necessary columns exist in the tables"""
        cursor = self.conn.cursor()
        
        # Check columns in artists table
        cursor.execute("PRAGMA table_info(artists)")
        artist_columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns to artists
        if "lastfm_url" not in artist_columns:
            try:
                cursor.execute("ALTER TABLE artists ADD COLUMN lastfm_url TEXT")
                print("Added column 'lastfm_url' to 'artists' table")
            except sqlite3.Error as e:
                print(f"Error adding column lastfm_url: {e}")
        
        if "similar_artists" not in artist_columns:
            try:
                cursor.execute("ALTER TABLE artists ADD COLUMN similar_artists TEXT")
                print("Added column 'similar_artists' to 'artists' table")
            except sqlite3.Error as e:
                print(f"Error adding column similar_artists: {e}")
        
        # Check columns in albums table
        cursor.execute("PRAGMA table_info(albums)")
        album_columns = [column[1] for column in cursor.fetchall()]
        
        # Add musicbrainz_albumid column if it doesn't exist
        if "musicbrainz_albumid" not in album_columns:
            try:
                cursor.execute("ALTER TABLE albums ADD COLUMN musicbrainz_albumid TEXT")
                print("Added column 'musicbrainz_albumid' to 'albums' table")
            except sqlite3.Error as e:
                print(f"Error adding column musicbrainz_albumid: {e}")
        
        # Check user-specific songs table
        songs_table = f"songs_{self.lastfm_user}"
        
        # Check if songs table for this user exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{songs_table}'")
        if cursor.fetchone() is None:
            # Create the table if it doesn't exist
            self._update_progress(f"Creating songs table for user {self.lastfm_user}...", 5)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {songs_table} (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                mbid TEXT,
                added_timestamp INTEGER,
                added_week INTEGER,
                added_month INTEGER,
                added_year INTEGER,
                duration INTEGER,
                album TEXT,
                album_artist TEXT,
                date TEXT,
                genre TEXT,
                artist TEXT NOT NULL,
                origen TEXT,
                scrobble_id INTEGER,
                data_source TEXT,
                musicbrainz_artistid TEXT,
                musicbrainz_recordingid TEXT,
                musicbrainz_albumartistid TEXT,
                musicbrainz_releasegroupid TEXT
            )
            """)
            print(f"Created songs table for user {self.lastfm_user}")
        
        self.conn.commit()
        
    def disconnect(self):
        """Closes the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self._update_progress("Database connection closed", 100)
    
    def get_new_scrobbles(self, force_update=False, filter_duplicates=True):
        """Gets new scrobbles from the last timestamp"""
        self.connect()
        from_timestamp = 0 if force_update else get_last_timestamp(self.conn, self.lastfm_user)
        
        if from_timestamp > 0:
            date_str = datetime.datetime.fromtimestamp(from_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            self._update_progress(f"Getting scrobbles since {date_str}", 15)
        else:
            self._update_progress("Getting all scrobbles (this may take a while)", 15)
                
        tracks = get_lastfm_scrobbles(self.lastfm_user, self.lastfm_api_key, from_timestamp, 
                                    progress_callback=self.progress_callback,
                                    filter_duplicates=filter_duplicates)
        
        self._update_progress(f"Retrieved {len(tracks)} scrobbles", 30)
        return tracks, from_timestamp
    
    def process_scrobbles_batch(self, tracks, interactive=None, callback=None):
        """Processes a batch of scrobbles with possible GUI interface"""
        self.connect()
        
        if interactive is None:
            interactive = self.interactive_mode
                
        # If there are few tracks, report
        if len(tracks) == 0:
            self._update_progress("No new scrobbles to process", 100)
            return 0, 0, 0, 0
                
        self._update_progress(f"Processing {len(tracks)} scrobbles...", 40)
        
        # Add this line to ensure albums are created first
        album_ids = self.ensure_albums_from_scrobbles(tracks)
        
        # Use the provided callback or the object's own
        process_callback = callback if callback else self.progress_callback
        
        # Make sure to use the current value of add_items
        result = self._process_scrobbles(
            self.conn, tracks, self.existing_artists, self.existing_albums, 
            self.existing_songs, self.lastfm_api_key, interactive, process_callback, 
            add_items=self._add_items
        )
        
        # Update the timestamp
        processed, linked, unlinked, newest_timestamp = result
        if newest_timestamp > 0:
            save_last_timestamp(self.conn, newest_timestamp, self.lastfm_user)
            date_str = datetime.datetime.fromtimestamp(newest_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            self._update_progress(f"Saved last timestamp: {date_str}", 95)
                
        match_percent = (linked / processed * 100) if processed > 0 else 0
        self._update_progress(f"Processing complete. {processed} scrobbles processed, {linked} linked ({match_percent:.1f}%)", 100)
                
        return result

    def _process_scrobbles(self, conn, tracks, existing_artists, existing_albums, existing_songs, 
                        lastfm_api_key, interactive=False, callback=None, add_items=True):
        """
        Procesa scrobbles con mejor estructuración y asegura la adición de álbumes correctamente
        
        Args:
            conn: Conexión a la base de datos
            tracks: Lista de tracks obtenidos de Last.fm
            existing_artists: Diccionario de artistas existentes
            existing_albums: Diccionario de álbumes existentes
            existing_songs: Diccionario de canciones existentes
            lastfm_api_key: API key de Last.fm
            interactive: Si se debe pedir confirmación al usuario
            callback: Función de callback para actualizar progreso
            add_items: Si se deben añadir artistas/álbumes/canciones no existentes
                
        Returns:
            Tupla (procesados, enlazados, no_enlazados, timestamp_más_reciente)
        """
        cursor = conn.cursor()
        scrobbles_table = f"scrobbles_{self.lastfm_user}"
        processed_count = 0
        linked_count = 0
        unlinked_count = 0
        newest_timestamp = 0
        
        # Verificar si hay scrobbles
        if not tracks:
            print("No hay scrobbles para procesar")
            return 0, 0, 0, 0
        
        # Definir actualización de progreso
        def update_progress(message, percent):
            if callback:
                callback(message, percent)
            else:
                print(message)
        
        # Primera fase: verificar scrobbles duplicados
        update_progress("Verificando duplicados...", 5)
        unique_tracks = []
        duplicates = 0
        
        for track in tracks:
            # Extraer información básica
            artist_name = track['artist']['#text']
            album_name = track['album']['#text'] if 'album' in track and '#text' in track['album'] else None
            track_name = track['name']
            timestamp = int(track['date']['uts'])
            
            # Actualizar el timestamp más reciente
            newest_timestamp = max(newest_timestamp, timestamp)
            
            # Verificar si el scrobble ya existe
            cursor.execute(f"SELECT id FROM {scrobbles_table} WHERE timestamp = ? AND artist_name = ? AND track_name = ?", 
                        (timestamp, artist_name, track_name))
            if cursor.fetchone():
                duplicates += 1
                continue
            
            unique_tracks.append(track)
        
        update_progress(f"Encontrados {len(unique_tracks)} scrobbles únicos, {duplicates} duplicados", 10)
        
        # Segunda fase: procesar scrobbles
        total_tracks = len(unique_tracks)
        
        # Crear tablas temporales para procesamiento en lotes
        cursor.execute("CREATE TEMPORARY TABLE IF NOT EXISTS temp_artists (name TEXT, mbid TEXT)")
        cursor.execute("CREATE TEMPORARY TABLE IF NOT EXISTS temp_albums (name TEXT, artist TEXT, mbid TEXT)")
        cursor.execute("CREATE TEMPORARY TABLE IF NOT EXISTS temp_songs (title TEXT, artist TEXT, album TEXT, mbid TEXT)")
        
        # Poblar tablas temporales
        artist_set = set()
        album_set = set()
        song_set = set()
        
        for track in unique_tracks:
            artist_name = track['artist']['#text']
            artist_mbid = track['artist'].get('mbid', '')
            album_name = track['album']['#text'] if 'album' in track and '#text' in track['album'] else None
            album_mbid = track['album'].get('mbid', '') if 'album' in track else None
            track_name = track['name']
            track_mbid = track.get('mbid', '')
            
            # Añadir a conjuntos para eliminar duplicados
            artist_set.add((artist_name, artist_mbid))
            
            if album_name:
                album_set.add((album_name, artist_name, album_mbid))
            
            song_set.add((track_name, artist_name, album_name, track_mbid))
        
        # Actualizar tablas temporales (solo si add_items es True)
        if add_items:
            update_progress("Identificando elementos a crear...", 15)
            
            # Insertar artistas
            for artist_name, artist_mbid in artist_set:
                # Verificar si ya existe
                if artist_name.lower() not in existing_artists:
                    cursor.execute("INSERT INTO temp_artists VALUES (?, ?)", (artist_name, artist_mbid))
            
            # Insertar álbumes
            for album_name, artist_name, album_mbid in album_set:
                # Verificar si ya existe
                album_key = (album_name.lower(), artist_name.lower())
                if album_key not in existing_albums:
                    cursor.execute("INSERT INTO temp_albums VALUES (?, ?, ?)", (album_name, artist_name, album_mbid))
            
            # Insertar canciones
            for track_name, artist_name, album_name, track_mbid in song_set:
                # Verificar si ya existe
                song_key = (track_name.lower(), artist_name.lower(), album_name.lower() if album_name else None)
                if song_key not in existing_songs:
                    cursor.execute("INSERT INTO temp_songs VALUES (?, ?, ?, ?)", (track_name, artist_name, album_name, track_mbid))
            
            # Crear artistas faltantes
            cursor.execute("SELECT COUNT(*) FROM temp_artists")
            artists_to_create = cursor.fetchone()[0]
            
            if artists_to_create > 0:
                update_progress(f"Creando {artists_to_create} artistas...", 20)
                
                cursor.execute("SELECT name, mbid FROM temp_artists")
                artists_data = cursor.fetchall()
                
                for i, (artist_name, artist_mbid) in enumerate(artists_data):
                    progress = 20 + (i / artists_to_create * 10)
                    update_progress(f"Creando artista {i+1}/{artists_to_create}: {artist_name}", progress)
                    
                    # Obtener información y crear artista
                    try:
                        # Usar la función mejorada
                        artist_info = get_artist_info(artist_name, artist_mbid, lastfm_api_key)
                        
                        if not artist_info:
                            # Si no se pudo obtener info completa, crear uno básico
                            artist_id = create_basic_artist(conn, artist_name, artist_mbid, self.lastfm_user)
                        else:
                            # Añadir artista con información completa
                            artist_id = add_artist_to_db(conn, artist_info, self.lastfm_user)
                        
                        if artist_id:
                            existing_artists[artist_name.lower()] = {'id': artist_id, 'origen': f'scrobbles_{self.lastfm_user}'}
                    except Exception as e:
                        print(f"Error al crear artista {artist_name}: {e}")
            
            # Crear álbumes faltantes
            cursor.execute("""
                SELECT a.name, a.artist, a.mbid, ar.id
                FROM temp_albums a
                JOIN artists ar ON LOWER(a.artist) = LOWER(ar.name)
            """)
            albums_data = cursor.fetchall()
            albums_to_create = len(albums_data)
            
            if albums_to_create > 0:
                update_progress(f"Creando {albums_to_create} álbumes...", 30)
                
                for i, (album_name, artist_name, album_mbid, artist_id) in enumerate(albums_data):
                    progress = 30 + (i / albums_to_create * 10)
                    update_progress(f"Creando álbum {i+1}/{albums_to_create}: {album_name}", progress)
                    
                    try:
                        # Get album information
                        album_info = get_album_info(album_name, artist_name, album_mbid, lastfm_api_key)
                        
                        if album_info:
                            album_id = add_album_to_db(conn, album_info, artist_id, self.lastfm_user)
                        else:
                            # Create basic album if no info is available
                            cursor.execute("""
                                INSERT INTO albums (artist_id, name, mbid, origen)
                                VALUES (?, ?, ?, ?)
                                RETURNING id
                            """, (artist_id, album_name, album_mbid, f"scrobbles_{self.lastfm_user}"))
                            
                            album_id = cursor.fetchone()[0]
                            conn.commit()
                        
                        if album_id:
                            album_key = (album_name.lower(), artist_name.lower())
                            existing_albums[album_key] = {'id': album_id, 'artist_id': artist_id, 'origen': f"scrobbles_{self.lastfm_user}"}
                    except Exception as e:
                        print(f"Error al crear álbum {album_name}: {e}")
            
            # Crear canciones faltantes
            cursor.execute("""
                SELECT s.title, s.artist, s.album, s.mbid, ar.id, al.id
                FROM temp_songs s
                LEFT JOIN artists ar ON LOWER(s.artist) = LOWER(ar.name)
                LEFT JOIN albums al ON LOWER(s.album) = LOWER(al.name) AND al.artist_id = ar.id
                WHERE ar.id IS NOT NULL
            """)
            songs_data = cursor.fetchall()
            songs_to_create = len(songs_data)
            
            if songs_to_create > 0:
                update_progress(f"Creando {songs_to_create} canciones...", 40)
                
                for i, (title, artist_name, album_name, track_mbid, artist_id, album_id) in enumerate(songs_data):
                    progress = 40 + (i / songs_to_create * 10)
                    update_progress(f"Creando canción {i+1}/{songs_to_create}: {title}", progress)
                    
                    try:
                        # Obtener información de la canción
                        track_info = get_track_info(title, artist_name, track_mbid, lastfm_api_key)
                        
                        if track_info:
                            # Pasa el valor self.lastfm_user explícitamente como lastfm_username
                            song_id = add_song_to_db(conn, track_info, album_id, artist_id, self.lastfm_user)
                        else:
                            # Crear canción básica
                            now = datetime.datetime.now()
                            added_timestamp = int(time.time())
                            added_week = now.isocalendar()[1]
                            added_month = now.month
                            added_year = now.year
                            
                            # Crear la tabla songs estándar, no la personalizada
                            cursor.execute("""
                                INSERT INTO songs 
                                (title, artist, album, album_artist, mbid, added_timestamp, added_week, 
                                added_month, added_year, origen)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                RETURNING id
                            """, (
                                title, 
                                artist_name, 
                                album_name, 
                                artist_name, 
                                track_mbid, 
                                added_timestamp, 
                                added_week, 
                                added_month, 
                                added_year, 
                                f"scrobbles_{self.lastfm_user}"
                            ))
                            
                            song_id = cursor.fetchone()[0]
                            conn.commit()
                        
                        if song_id:
                            song_key = (title.lower(), artist_name.lower(), album_name.lower() if album_name else None)
                            existing_songs[song_key] = {'id': song_id}
                    except Exception as e:
                        print(f"Error al crear canción {title}: {e}")
        
        # Tercera fase: crear scrobbles
        update_progress("Insertando scrobbles en la base de datos...", 70)
        
        # Procesar scrobbles en lotes
        batch_size = 100
        batches = [unique_tracks[i:i+batch_size] for i in range(0, len(unique_tracks), batch_size)]
        
        for batch_idx, batch in enumerate(batches):
            progress = 70 + (batch_idx / len(batches) * 30)
            update_progress(f"Procesando lote {batch_idx+1}/{len(batches)}", progress)
            
            # Preparar valores para inserción en lote
            values = []
            for track in batch:
                artist_name = track['artist']['#text']
                album_name = track['album']['#text'] if 'album' in track and '#text' in track['album'] else None
                track_name = track['name']
                timestamp = int(track['date']['uts'])
                scrobble_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                lastfm_url = track['url']
                
                # Buscar IDs relacionados
                artist_id = None
                album_id = None
                song_id = None
                
                # Buscar artista
                artist_info = existing_artists.get(artist_name.lower())
                if artist_info:
                    if isinstance(artist_info, dict):
                        artist_id = artist_info['id']
                    else:
                        artist_id = artist_info
                
                # Buscar álbum si hay artista y album_name existe
                if album_name and artist_id:
                    album_key = (album_name.lower(), artist_name.lower())
                    album_info = existing_albums.get(album_key)
                    if album_info:
                        if isinstance(album_info, dict):
                            album_id = album_info['id']
                        elif isinstance(album_info, tuple):
                            album_id = album_info[0]
                        else:
                            album_id = album_info
                
                # Buscar canción
                song_key = (track_name.lower(), artist_name.lower(), album_name.lower() if album_name else None)
                song_info = existing_songs.get(song_key)
                if song_info:
                    if isinstance(song_info, dict):
                        song_id = song_info['id']
                    else:
                        song_id = song_info
                
                values.append((
                    track_name,
                    album_name,
                    artist_name,
                    timestamp,
                    scrobble_date,
                    lastfm_url,
                    song_id,
                    album_id,
                    artist_id
                ))
            
            # Insertar en lote
            placeholders = []
            flat_values = []
            
            for item in values:
                placeholders.append('(?, ?, ?, ?, ?, ?, ?, ?, ?)')
                flat_values.extend(item)
            
            sql = f"""
                INSERT INTO {scrobbles_table} 
                (track_name, album_name, artist_name, timestamp, scrobble_date, lastfm_url, song_id, album_id, artist_id)
                VALUES {', '.join(placeholders)}
            """
            
            try:
                cursor.execute(sql, flat_values)
                
                # Actualizar contadores
                processed_count += len(batch)
                for _, _, _, _, _, _, song_id, _, _ in values:
                    if song_id:
                        linked_count += 1
                    else:
                        unlinked_count += 1
                        
            except sqlite3.Error as e:
                print(f"Error al insertar lote de scrobbles: {e}")
            
            # Commit cada lote para no perder progreso
            conn.commit()
        
        # Limpiar tablas temporales
        cursor.execute("DROP TABLE IF EXISTS temp_artists")
        cursor.execute("DROP TABLE IF EXISTS temp_albums")
        cursor.execute("DROP TABLE IF EXISTS temp_songs")
        
        update_progress(f"Proceso completado. {processed_count} scrobbles procesados, {linked_count} enlazados", 100)
        
        return processed_count, linked_count, unlinked_count, newest_timestamp

    def update_artists_metadata(self, limit=50):
        """
        Updates metadata information for artists that don't have it
        
        Args:
            limit: Maximum number of artists to update per execution
            
        Returns:
            Number of updated artists
        """
        # Call the global function but pass self.lastfm_api_key explicitly
        return update_artists_metadata(self.conn, self.lastfm_api_key, limit)

    def ensure_albums_from_scrobbles(self, tracks):
        """
        Ensures that all albums mentioned in scrobbles are added to the database.
        
        Args:
            tracks: List of tracks from Last.fm scrobbles
            
        Returns:
            Dictionary of created/found album IDs
        """
        self.connect()
        cursor = self.conn.cursor()
        album_ids = {}
        
        # Group tracks by artist and album
        albums_to_process = {}
        for track in tracks:
            artist_name = track['artist']['#text']
            album_name = track['album']['#text'] if 'album' in track and '#text' in track['album'] else None
            album_mbid = track['album'].get('mbid', '') if 'album' in track else None
            
            if album_name and artist_name:
                key = (album_name.lower(), artist_name.lower())
                if key not in albums_to_process:
                    albums_to_process[key] = {
                        'name': album_name,
                        'artist': artist_name,
                        'mbid': album_mbid
                    }
        
        # Process each unique album
        total_albums = len(albums_to_process)
        self._update_progress(f"Processing {total_albums} unique albums...", 25)
        
        for i, ((album_name_lower, artist_name_lower), album_data) in enumerate(albums_to_process.items()):
            album_name = album_data['name']
            artist_name = album_data['artist']
            album_mbid = album_data['mbid']
            
            progress = 25 + (i / max(1, total_albums) * 10)
            self._update_progress(f"Processing album {i+1}/{total_albums}: {album_name}", progress)
            
            # Find artist ID
            cursor.execute("SELECT id FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name,))
            artist_result = cursor.fetchone()
            
            if artist_result:
                artist_id = artist_result[0]
                
                # Check if album exists
                cursor.execute("""
                    SELECT id FROM albums 
                    WHERE artist_id = ? AND LOWER(name) = LOWER(?)
                """, (artist_id, album_name))
                
                album_result = cursor.fetchone()
                
                if album_result:
                    # Album exists
                    album_id = album_result[0]
                    album_ids[(album_name_lower, artist_name_lower)] = album_id
                else:
                    # Create new album
                    try:
                        # Get album info
                        album_info = get_album_info(album_name, artist_name, album_mbid, self.lastfm_api_key)
                        
                        if album_info:
                            album_id = add_album_to_db(conn, album_info, artist_id, self.lastfm_user)
                        else:
                            # Create basic album
                            cursor.execute("""
                                INSERT INTO albums (artist_id, name, mbid, origen)
                                VALUES (?, ?, ?, ?)
                                RETURNING id
                            """, (artist_id, album_name, album_mbid, f"scrobbles_{self.lastfm_user}"))
                            
                            album_id = cursor.fetchone()[0]
                            self.conn.commit()
                        
                        if album_id:
                            album_ids[(album_name_lower, artist_name_lower)] = album_id
                            print(f"Album created: {album_name} (ID: {album_id})")
                    except Exception as e:
                        print(f"Error creating album {album_name}: {e}")
        
        return album_ids


    def update_scrobbles(self, force_update=False, interactive=None, callback=None, filter_duplicates=True):
        """Updates scrobbles from Last.fm and processes them"""
        if interactive is None:
            interactive = self.interactive_mode
        
        # If force_update, first clean the database
        if force_update:
            handle_force_update(self.db_path, self.lastfm_user)
        
        # Now get the new scrobbles (from zero if force_update was True)
        tracks, from_timestamp = self.get_new_scrobbles(force_update, filter_duplicates)
        
        if not tracks:
            self._update_progress("No new scrobbles to process", 100)
            return 0, 0, 0, 0
        
        # Process the scrobbles
        results = self.process_scrobbles_batch(tracks, interactive, callback)
        
        # Update MusicBrainz information for albums
        self._update_progress("Updating detailed album information from MusicBrainz...", 96)
        cursor = self.conn.cursor()
        
        # Look for albums that need updates of specific fields
        cursor.execute("""
            SELECT id, name, mbid 
            FROM albums 
            WHERE musicbrainz_albumid IS NULL OR catalognumber IS NULL
            LIMIT 50
        """)
        
        albums_to_update = cursor.fetchall()
        albums_updated = 0
        
        for album_id, album_name, album_mbid in albums_to_update:
            if update_album_details_from_musicbrainz(self.conn, album_id, album_mbid):
                albums_updated += 1
        
        if albums_updated > 0:
            self._update_progress(f"Updated details for {albums_updated} albums with MusicBrainz data", 98)
        
        # Update artist information (bios, tags, similar artists)
        self._update_progress("Updating artist details...", 99)
        artists_updated = self.update_artists_with_lastfm_info()
        
        self._update_progress(f"Processing completed. {results[0]} scrobbles processed, {results[1]} linked, "
                            f"{albums_updated} albums updated, {artists_updated} artists updated", 100)
        
        # Update artist metadata after processing scrobbles
        if self._add_items:
            self._update_progress("Updating artist metadata...", 97)
            updated_artists = self.update_artists_metadata(20)  # Limit to 20 per session
            self._update_progress(f"Updated metadata for {updated_artists} artists", 98)

        return results




    def update_artists_with_lastfm_info(self, limit=20):
        """
        Updates detailed artist information from Last.fm (bio, tags, similar)
        
        Args:
            limit: Maximum number of artists to update per execution
            
        Returns:
            Number of updated artists
        """
        cursor = self.conn.cursor()
        
        # Look for artists without bio or tags
        cursor.execute("""
            SELECT id, name, mbid
            FROM artists
            WHERE bio IS NULL OR tags IS NULL OR bio = '' OR tags = ''
            LIMIT ?
        """, (limit,))
        
        artists_to_update = cursor.fetchall()
        artists_updated = 0
        
        for artist_id, artist_name, artist_mbid in artists_to_update:
            # Get complete information from Last.fm
            artist_info = get_artist_info(artist_name, artist_mbid, self.lastfm_api_key)
            
            if not artist_info:
                print(f"Couldn't get Last.fm information for {artist_name}")
                continue
            
            # Prepare updates
            updates = []
            params = []
            
            # Bio
            if 'bio' in artist_info and 'content' in artist_info['bio'] and artist_info['bio']['content']:
                bio = artist_info['bio']['content']
                if bio and bio.strip():
                    updates.append("bio = ?")
                    params.append(bio)
            
            # Tags
            if 'tags' in artist_info and 'tag' in artist_info['tags']:
                tag_list = artist_info['tags']['tag']
                tags = []
                
                if isinstance(tag_list, list):
                    tags = [tag['name'] for tag in tag_list]
                else:
                    tags = [tag_list['name']]
                    
                tags_str = ','.join(tags)
                if tags_str:
                    updates.append("tags = ?")
                    params.append(tags_str)
            
            # Similar artists - save as JSON
            if 'similar' in artist_info and 'artist' in artist_info['similar']:
                similar_artists = artist_info['similar']['artist']
                if similar_artists:
                    # Extract only relevant information
                    similar_data = []
                    
                    if isinstance(similar_artists, list):
                        for artist in similar_artists:
                            similar_data.append({
                                'name': artist.get('name', ''),
                                'url': artist.get('url', ''),
                                'mbid': artist.get('mbid', '')
                            })
                    else:
                        similar_data.append({
                            'name': similar_artists.get('name', ''),
                            'url': similar_artists.get('url', ''),
                            'mbid': similar_artists.get('mbid', '')
                        })
                    
                    updates.append("similar_artists = ?")
                    params.append(json.dumps(similar_data))
            
            # Last.fm URL
            if 'url' in artist_info:
                updates.append("lastfm_url = COALESCE(lastfm_url, ?)")
                params.append(artist_info['url'])
            
            # Update
            if updates:
                query = f"UPDATE artists SET {', '.join(updates)} WHERE id = ?"
                params.append(artist_id)
                
                try:
                    cursor.execute(query, params)
                    artists_updated += 1
                except sqlite3.Error as e:
                    print(f"Error updating artist {artist_name}: {e}")
        
        self.conn.commit()
        return artists_updated

    def create_indices(self):
        """Creates optimized indices to improve query performance."""
        self.connect()
        # Call the global function passing the username
        return create_optimized_indices(self.conn, self.lastfm_user)

    def merge_duplicates_by_mbid(self, conn):
        """Merges elements duplicated by MBID"""
        cursor = conn.cursor()

        # 1. Merge artists with the same MBID
        print("Looking for duplicate artists by MBID...")
        cursor.execute("""
            SELECT mbid, GROUP_CONCAT(id) as ids, COUNT(*) as count
            FROM artists
            WHERE mbid IS NOT NULL AND mbid != ''
            GROUP BY mbid
            HAVING count > 1
        """)

        duplicated_artists = cursor.fetchall()

        for mbid, ids_str, count in duplicated_artists:
            ids = ids_str.split(',')
            primary_id = int(ids[0])  # Use first ID as primary
            
            print(f"Found {count} duplicate artists with MBID {mbid}. Merging into ID {primary_id}...")
            
            # Update references in albums
            for other_id in ids[1:]:
                cursor.execute("UPDATE albums SET artist_id = ? WHERE artist_id = ?", (primary_id, other_id))
                
            # Update references in scrobbles
            for other_id in ids[1:]:
                cursor.execute("UPDATE scrobbles SET artist_id = ? WHERE artist_id = ?", (primary_id, other_id))
            
            # Delete duplicate artists
            for other_id in ids[1:]:
                try:
                    cursor.execute("DELETE FROM artists WHERE id = ?", (other_id,))
                except sqlite3.Error as e:
                    print(f"Error deleting duplicate artist {other_id}: {e}")

        # 2. Merge albums with the same MBID
        print("Looking for duplicate albums by MBID...")
        cursor.execute("""
            SELECT mbid, GROUP_CONCAT(id) as ids, COUNT(*) as count
            FROM albums
            WHERE mbid IS NOT NULL AND mbid != ''
            GROUP BY mbid
            HAVING count > 1
        """)

        duplicated_albums = cursor.fetchall()

        for mbid, ids_str, count in duplicated_albums:
            ids = ids_str.split(',')
            primary_id = int(ids[0])  # Use first ID as primary
            
            print(f"Found {count} duplicate albums with MBID {mbid}. Merging into ID {primary_id}...")
            
            # Update references in scrobbles
            for other_id in ids[1:]:
                cursor.execute("UPDATE scrobbles SET album_id = ? WHERE album_id = ?", (primary_id, other_id))
            
            # Delete duplicate albums
            for other_id in ids[1:]:
                try:
                    cursor.execute("DELETE FROM albums WHERE id = ?", (other_id,))
                except sqlite3.Error as e:
                    print(f"Error deleting duplicate album {other_id}: {e}")

        # 3. Merge songs with the same MBID
        print("Looking for duplicate songs by MBID...")
        cursor.execute("""
            SELECT mbid, GROUP_CONCAT(id) as ids, COUNT(*) as count
            FROM songs
            WHERE mbid IS NOT NULL AND mbid != ''
            GROUP BY mbid
            HAVING count > 1
        """)

        duplicated_songs = cursor.fetchall()

        for mbid, ids_str, count in duplicated_songs:
            ids = ids_str.split(',')
            primary_id = int(ids[0])  # Use first ID as primary
            
            print(f"Found {count} duplicate songs with MBID {mbid}. Merging into ID {primary_id}...")
            
            # Update references in scrobbles
            for other_id in ids[1:]:
                cursor.execute("UPDATE scrobbles SET song_id = ? WHERE song_id = ?", (primary_id, other_id))
            
            # Delete duplicate songs
            for other_id in ids[1:]:
                try:
                    cursor.execute("DELETE FROM songs WHERE id = ?", (other_id,))
                except sqlite3.Error as e:
                    print(f"Error deleting duplicate song {other_id}: {e}")

        conn.commit()

        return len(duplicated_artists), len(duplicated_albums), len(duplicated_songs)


    def update_database_with_online_info(self, specific_data=None):
        """Actualiza la información de artistas, álbumes y canciones existentes con datos de Last.fm,
        respetando los registros con origen 'local'
        
        Args:
            specific_data: Diccionario con claves 'artists', 'albums', 'songs' para actualizar solo ciertos elementos
        """
        self.connect()
        cursor = self.conn.cursor()
        
        total_updates = 0
        successful_updates = 0
        
        # Actualizar artistas que NO tengan origen 'local'
        update_artists = specific_data is None or 'artists' in specific_data
        
        if update_artists:
            self._update_progress("Verificando artistas para actualizar...", 5)
            cursor.execute("SELECT id, name, origen FROM artists WHERE origen != 'local' OR origen IS NULL")
            artists_to_update = cursor.fetchall()
            
            self._update_progress(f"Encontrados {len(artists_to_update)} artistas actualizables", 10)
            
            for i, (artist_id, artist_name, origen) in enumerate(artists_to_update):
                progress = 10 + (i / len(artists_to_update) * 30) if artists_to_update else 40
                self._update_progress(f"Evaluando artista {i+1}/{len(artists_to_update)}: {artist_name} (origen: {origen or 'NULL'})", progress)
                
                # Preguntar al usuario si estamos en modo interactivo
                if self.interactive_mode:
                    continue_update = input(f"¿Actualizar información para artista '{artist_name}'? (s/n): ").lower() == 's'
                    if not continue_update:
                        print(f"Saltando actualización para artista {artist_name}")
                        continue
                
                total_updates += 1
                artist_info = get_artist_info(artist_name, None, self.lastfm_api_key)
                if artist_info:
                    if update_artist_in_db(self.conn, artist_id, artist_info):
                        successful_updates += 1
        
        # Actualizar álbumes sin origen 'scrobbles'
        update_albums = specific_data is None or 'albums' in specific_data
        
        if update_albums:
            self._update_progress("Verificando álbumes para actualizar...", 40)
            cursor.execute("""
                SELECT a.id, a.name, ar.name FROM albums a 
                JOIN artists ar ON a.artist_id = ar.id
                WHERE a.origen IS NULL OR a.origen != 'scrobbles'
            """)
            albums_to_update = cursor.fetchall()
            
            self._update_progress(f"Encontrados {len(albums_to_update)} álbumes para actualizar", 45)
            
            for i, (album_id, album_name, artist_name) in enumerate(albums_to_update):
                progress = 45 + (i / len(albums_to_update) * 30) if albums_to_update else 75
                self._update_progress(f"Actualizando álbum {i+1}/{len(albums_to_update)}: {album_name} de {artist_name}", progress)
                
                total_updates += 1
                album_info = get_album_info(album_name, artist_name, None, self.lastfm_api_key)
                if album_info:
                    if update_album_in_db(self.conn, album_id, album_info):
                        successful_updates += 1
        
        # Actualizar canciones sin origen 'scrobbles'
        update_songs = specific_data is None or 'songs' in specific_data
        
        if update_songs:
            self._update_progress("Verificando canciones para actualizar...", 75)
            cursor.execute("SELECT id, title, artist FROM songs WHERE origen IS NULL OR origen != 'scrobbles'")
            songs_to_update = cursor.fetchall()
            
            self._update_progress(f"Encontradas {len(songs_to_update)} canciones para actualizar", 80)
            
            for i, (song_id, song_name, artist_name) in enumerate(songs_to_update):
                progress = 80 + (i / len(songs_to_update) * 20) if songs_to_update else 100
                self._update_progress(f"Actualizando canción {i+1}/{len(songs_to_update)}: {song_name} de {artist_name}", progress)
                
                total_updates += 1
                track_info = get_track_info(song_name, artist_name, None, self.lastfm_api_key)
                if track_info:
                    if update_song_in_db(self.conn, song_id, track_info):
                        successful_updates += 1
        
        self._update_progress(f"Actualización completada. {successful_updates} de {total_updates} elementos actualizados correctamente", 100)
    
        # Fusionar duplicados por MBID
        print("\nBuscando y fusionando elementos duplicados por MBID...")
        artists_merged, albums_merged, songs_merged = merge_duplicates_by_mbid(self, self.conn)
        
        print(f"Elementos fusionados: {artists_merged} artistas, {albums_merged} álbumes, {songs_merged} canciones")
        
        return successful_updates, total_updates

    def verify_database_integrity(self):
        """Verifies database integrity and fixes common issues"""
        self.connect()
        cursor = self.conn.cursor()
        corrections = 0
        
        self._update_progress("Verifying database integrity...", 5)
        
        # Check for scrobbles without artist_id but with existing artist
        self._update_progress("Checking artist links in scrobbles...", 10)
        
        # Use the correct table name for this user
        scrobbles_table = f"scrobbles_{self.lastfm_user}"
        
        cursor.execute(f"""
            SELECT s.id, s.artist_name, a.id 
            FROM {scrobbles_table} s
            JOIN artists a ON LOWER(s.artist_name) = LOWER(a.name)
            WHERE s.artist_id IS NULL
        """)
        
        artist_links = cursor.fetchall()
        if artist_links:
            self._update_progress(f"Fixing {len(artist_links)} artist links", 20)
            for scrobble_id, artist_name, artist_id in artist_links:
                cursor.execute(f"UPDATE {scrobbles_table} SET artist_id = ? WHERE id = ?", (artist_id, scrobble_id))
                corrections += 1
        
        # Check for scrobbles without album_id but with existing album
        self._update_progress("Checking album links in scrobbles...", 40)
        cursor.execute(f"""
            SELECT s.id, s.album_name, s.artist_name, a.id 
            FROM {scrobbles_table} s
            JOIN albums a ON LOWER(s.album_name) = LOWER(a.name)
            JOIN artists ar ON a.artist_id = ar.id AND LOWER(s.artist_name) = LOWER(ar.name)
            WHERE s.album_id IS NULL AND s.album_name IS NOT NULL AND s.album_name != ''
        """)
        
        album_links = cursor.fetchall()
        if album_links:
            self._update_progress(f"Fixing {len(album_links)} album links", 60)
            for scrobble_id, album_name, artist_name, album_id in album_links:
                cursor.execute(f"UPDATE {scrobbles_table} SET album_id = ? WHERE id = ?", (album_id, scrobble_id))
                corrections += 1
        
        # Check for scrobbles without song_id but with existing song
        self._update_progress("Checking song links in scrobbles...", 80)
        
        # Look in both global and user-specific song tables
        songs_table = f"songs_{self.lastfm_user}"
        
        # First try the user-specific table
        cursor.execute(f"""
            SELECT s.id, s.track_name, s.artist_name, sg.id 
            FROM {scrobbles_table} s
            JOIN {songs_table} sg ON LOWER(s.track_name) = LOWER(sg.title) AND LOWER(s.artist_name) = LOWER(sg.artist)
            WHERE s.song_id IS NULL
        """)
        
        song_links = cursor.fetchall()
        
        # Then try the global songs table
        cursor.execute(f"""
            SELECT s.id, s.track_name, s.artist_name, sg.id 
            FROM {scrobbles_table} s
            JOIN songs sg ON LOWER(s.track_name) = LOWER(sg.title) AND LOWER(s.artist_name) = LOWER(sg.artist)
            WHERE s.song_id IS NULL
        """)
        
        song_links_global = cursor.fetchall()
        song_links.extend(song_links_global)
        
        if song_links:
            self._update_progress(f"Fixing {len(song_links)} song links", 90)
            for scrobble_id, track_name, artist_name, song_id in song_links:
                cursor.execute(f"UPDATE {scrobbles_table} SET song_id = ? WHERE id = ?", (song_id, scrobble_id))
                corrections += 1
        
        self.conn.commit()
        self._update_progress(f"Verification completed. Made {corrections} corrections", 100)
        return corrections


    def export_scrobbles_to_json(self, file_path, limit=None):
        """Exporta scrobbles a un archivo JSON
        
        Args:
            file_path: Ruta del archivo a guardar
            limit: Número máximo de scrobbles a exportar o None para todos
        """
        self.connect()
        cursor = self.conn.cursor()
        scrobbles_table = f"scrobbles_{self.lastfm_user}"
        
        # Verificar si existe la tabla
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{scrobbles_table}'")
        if not cursor.fetchone():
            print(f"No hay datos para el usuario {self.lastfm_user}")
            return 0
        
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        cursor.execute(f"""
            SELECT id, track_name, album_name, artist_name, timestamp, scrobble_date, lastfm_url,
                    song_id, album_id, artist_id
            FROM {scrobbles_table}
            ORDER BY timestamp DESC
            {limit_clause}
        """)
        
        scrobbles = []
        for row in cursor.fetchall():
            scrobble = {
                'id': row[0],
                'track_name': row[1],
                'album_name': row[2],
                'artist_name': row[3],
                'timestamp': row[4],
                'scrobble_date': row[5],
                'lastfm_url': row[6],
                'song_id': row[7],
                'album_id': row[8],
                'artist_id': row[9]
            }
            scrobbles.append(scrobble)
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Guardar a archivo JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                'user': self.lastfm_user,
                'export_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'count': len(scrobbles),
                'scrobbles': scrobbles
            }, f, indent=2, ensure_ascii=False)
        
        return len(scrobbles)


   
    def force_update_database(self, interactive=None):
        """Deletes all existing scrobbles to perform a full update."""
        if interactive is None:
            interactive = self.interactive_mode
            
        confirm = True
        if interactive:
            print("\nWARNING! This operation will delete ALL scrobbles from the database.")
            response = input(f"Are you sure you want to delete ALL scrobbles for user {self.lastfm_user}? (y/n): ").lower()
            confirm = response == 'y'
            
        if confirm:
            self.connect()
            cursor = self.conn.cursor()
            scrobbles_table = f"scrobbles_{self.lastfm_user}"
            
            # Check if the table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{scrobbles_table}'")
            if cursor.fetchone():
                cursor.execute(f"DELETE FROM {scrobbles_table}")
                cursor.execute("UPDATE lastfm_config SET last_timestamp = 0 WHERE id = 1 AND lastfm_username = ?", (self.lastfm_user,))
                self.conn.commit()
                self._update_progress(f"ALL scrobbles for user {self.lastfm_user} have been deleted. A full update will be performed.", 10)
                return True
            else:
                self._update_progress(f"The table '{scrobbles_table}' doesn't exist yet. Nothing to delete.", 10)
                return True
        
        return False




    def create_indices(self):
        """Crea índices optimizados para mejorar el rendimiento de consultas."""
        self.connect()
        cursor = self.conn.cursor()
        scrobbles_table = f"scrobbles_{self.lastfm_user}"
        
        # Verificar si existe la tabla
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{scrobbles_table}'")
        if not cursor.fetchone():
            print(f"No hay datos para el usuario {self.lastfm_user}. No se crearán índices.")
            return 0

        try:
            self._update_progress("Creando índices para optimizar la base de datos...", 5)
            
            # Índices para la tabla de scrobbles de este usuario
            indices_scrobbles = [
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_name ON {scrobbles_table}(artist_name)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_album_name ON {scrobbles_table}(album_name)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_track_name ON {scrobbles_table}(track_name)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_timestamp ON {scrobbles_table}(timestamp)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_song_id ON {scrobbles_table}(song_id)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_id ON {scrobbles_table}(artist_id)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_album_id ON {scrobbles_table}(album_id)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_album ON {scrobbles_table}(artist_name, album_name)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_track ON {scrobbles_table}(artist_name, track_name)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_album_track ON {scrobbles_table}(album_name, track_name)",
                # Índice para búsquedas por fecha - útil para estadísticas por periodo
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_date ON {scrobbles_table}(date(scrobble_date))",
                # Índice para búsquedas por hora del día
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_hour ON {scrobbles_table}(strftime('%H', scrobble_date))",
                # Índice para búsquedas por día de la semana
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_weekday ON {scrobbles_table}(strftime('%w', scrobble_date))"
            ]
            
            # Crear índices para la tabla de scrobbles
            indices_creados = 0
            for index_query in indices_scrobbles:
                try:
                    cursor.execute(index_query)
                    indices_creados += 1
                    
                    # Commit después de cada índice para no bloquear la base de datos por mucho tiempo
                    self.conn.commit()
                    
                    self._update_progress(f"Creando índice {indices_creados}/{len(indices_scrobbles)}...", 
                                         5 + (indices_creados / len(indices_scrobbles) * 90))
                except sqlite3.OperationalError as e:
                    print(f"Error al crear índice: {e}")
            
            self._update_progress(f"Índices creados correctamente: {indices_creados}", 100)
            return indices_creados
            
        except Exception as e:
            print(f"Error al crear índices: {e}")
            return 0


    def get_artist_correction(artist_name, lastfm_api_key):
        """
        Uses the Last.fm artist.getCorrection API to get the correct
        artist name and MBID.
        
        Args:
            artist_name: Artist name to correct
            lastfm_api_key: Last.fm API key
            
        Returns:
            Tuple (corrected_name, mbid) or (artist_name, None) if no correction
        """
        if not artist_name or not lastfm_api_key:
            return artist_name, None
        
        # Check cache first
        global lastfm_cache
        if lastfm_cache:
            try:
                cache_params = {
                    'method': 'artist.getCorrection',
                    'artist': artist_name
                }
                cached_result = lastfm_cache.get(cache_params)
                if cached_result:
                    print(f"Using cached data for artist correction: {artist_name}")
                    return process_correction_response(cached_result, artist_name)
            except Exception as e:
                print(f"Error using cache for artist correction: {e}")
        
        # Try to use pylast if available
        try:
            import pylast
            network = pylast.LastFMNetwork(api_key=lastfm_api_key)
            artist = network.get_artist(artist_name)
            
            try:
                # Try to get corrections
                corrections = artist.get_correction()
                if corrections:
                    corrected_artist = corrections[0]
                    corrected_name = corrected_artist.get_name()
                    mbid = corrected_artist.get_mbid()
                    
                    print(f"Correction found: '{artist_name}' -> '{corrected_name}' (MBID: {mbid})")
                    
                    # Save to cache
                    if lastfm_cache:
                        try:
                            response_data = {
                                'corrections': {'correction': [{'artist': {'name': corrected_name, 'mbid': mbid}}]}
                            }
                            lastfm_cache.put(cache_params, response_data)
                        except Exception as e:
                            print(f"Error saving correction to cache: {e}")
                    
                    return corrected_name, mbid
            except pylast.WSError:
                # If there's an error, try the alternative method
                pass
        except ImportError:
            # pylast is not available
            pass
        
        # Alternative method using requests directly
        try:
            params = {
                'method': 'artist.getCorrection',
                'artist': artist_name,
                'api_key': lastfm_api_key,
                'format': 'json'
            }
            
            response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Save to cache
                if lastfm_cache:
                    try:
                        lastfm_cache.put(params, data)
                    except Exception as e:
                        print(f"Error saving to cache: {e}")
                
                return process_correction_response(data, artist_name)
        except Exception as e:
            print(f"Error looking for correction for artist '{artist_name}': {e}")
        
        # If no correction is found or there's an error, return the original name
        return artist_name, None

    def process_correction_response(data, original_name):
        """
        Processes the artist.getCorrection response
        
        Args:
            data: JSON response from the API
            original_name: Original artist name
            
        Returns:
            Tuple (corrected_name, mbid)
        """
        try:
            if 'corrections' in data and 'correction' in data['corrections']:
                corrections = data['corrections']['correction']
                
                # Can be a list or a single item
                if isinstance(corrections, list):
                    correction = corrections[0]
                else:
                    correction = corrections
                
                if 'artist' in correction:
                    artist_data = correction['artist']
                    corrected_name = artist_data.get('name', original_name)
                    mbid = artist_data.get('mbid')
                    
                    # Only report if there's a difference
                    if corrected_name.lower() != original_name.lower() or mbid:
                        print(f"Correction found: '{original_name}' -> '{corrected_name}' (MBID: {mbid})")
                    
                    return corrected_name, mbid
        except Exception as e:
            print(f"Error processing correction for '{original_name}': {e}")
        
        return original_name, None
# Fixed APICache class to handle the "argument of type 'int' is not iterable" error

class APICache:
    """
    Generic cache for API queries (Last.fm, MusicBrainz, etc.)
    """
    
    def __init__(self, name="generic", cache_file=None, cache_duration=7):
        """
        Initializes the cache.
        
        Args:
            name: Cache name (for logs)
            cache_file: Path to file to persist the cache
            cache_duration: Cache duration in days
        """
        self.name = name
        self.cache = {}
        self.cache_file = cache_file
        self.cache_duration = cache_duration  # in days
        
        if cache_file and os.path.exists(cache_file):
            try:
                # Read the file with robust error handling
                with open(cache_file, 'r', encoding='utf-8') as f:
                    try:
                        loaded_cache = json.load(f)
                        print(f"Loading cache from file: {cache_file}")
                        
                        # Verify the loaded cache is a dictionary
                        if not isinstance(loaded_cache, dict):
                            print(f"Warning: Cache file contains invalid data type: {type(loaded_cache)}. Using empty cache.")
                            loaded_cache = {}
                            
                    except json.JSONDecodeError as je:
                        print(f"Error decoding cache file ({cache_file}): {je}")
                        print("Trying to recover partial data...")
                        
                        # Attempt to recover partial data
                        f.seek(0)  # Go back to start of file
                        loaded_cache = self._recover_partial_json(f)
                        
                        # If we couldn't recover anything, start with empty cache
                        if not loaded_cache:
                            print("Couldn't recover any data. Using empty cache.")
                            loaded_cache = {}
                        else:
                            print(f"Recovered {len(loaded_cache)} partial cache entries.")
                    
                    # Filter expired entries
                    now = time.time()
                    valid_entries = 0
                    
                    # Create a new cache to avoid modifying during iteration
                    filtered_cache = {}
                    
                    # Process each key-value pair
                    for key, entry in loaded_cache.items():
                        # Skip invalid entries
                        if not isinstance(entry, dict):
                            print(f"Skipping invalid cache entry for key {key}: {type(entry)}")
                            continue
                            
                        # Check expiration
                        if 'timestamp' in entry:
                            age_days = (now - entry['timestamp']) / (60 * 60 * 24)
                            if age_days <= self.cache_duration:
                                filtered_cache[key] = entry
                                valid_entries += 1
                        else:
                            # If no timestamp, assume it's recent
                            filtered_cache[key] = entry
                            valid_entries += 1
                    
                    # Assign the filtered cache            
                    self.cache = filtered_cache
                    print(f"{self.name}Cache: Loaded {valid_entries} valid entries out of {len(loaded_cache)} total")
            except Exception as e:
                print(f"Error loading cache file for {self.name}: {e}")
                print("Using empty cache")
                self.cache = {}
    
    def get(self, key_parts):
        """
        Gets a result from the cache if available and not expired.
        
        Args:
            key_parts: Elements to form the cache key (list, tuple or dictionary)
            
        Returns:
            Cached data or None if it doesn't exist or expired
        """
        try:
            cache_key = self._make_key(key_parts)
            entry = self.cache.get(cache_key)
            
            if not entry:
                return None
                
            # Check expiration
            if 'timestamp' in entry:
                age_days = (time.time() - entry['timestamp']) / (60 * 60 * 24)
                if age_days > self.cache_duration:
                    # Expired, delete and return None
                    del self.cache[cache_key]
                    return None
            
            return entry.get('data')
        except Exception as e:
            # If anything goes wrong, just return None and log the error
            print(f"Error retrieving from cache: {e}")
            return None
    
    def put(self, key_parts, result):
        """
        Stores a result in the cache.
        
        Args:
            key_parts: Elements to form the cache key
            result: Result to store
        """
        try:
            # Don't store None results or error responses
            if result is None or (isinstance(result, dict) and 'error' in result):
                return
                
            cache_key = self._make_key(key_parts)
            
            # Store with timestamp for expiration
            self.cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
            
            # Save to file if configured
            self._save_cache()
        except Exception as e:
            # If caching fails, just log the error and continue
            print(f"Error storing in cache: {e}")
    
    def clear(self, save=True):
        """Clears the entire cache"""
        self.cache = {}
        if save and self.cache_file:
            self._save_cache()
    
    def _save_cache(self):
        """Saves the cache to disk if a file is configured"""
        if not self.cache_file:
            return
            
        try:
            # Create directory if it doesn't exist
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
                
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache file for {self.name}: {e}")
    
    def _make_key(self, key_parts):
        """
        Creates a unique key for the cache from the provided elements.
        
        Args:
            key_parts: Elements to form the key (list, tuple, dictionary, etc.)
            
        Returns:
            Unique string that identifies the query
        """
        try:
            # If it's a dictionary, normalize and sort
            if isinstance(key_parts, dict):
                # Filter irrelevant keys like api_keys
                filtered = {k.lower(): v for k, v in key_parts.items() 
                        if k.lower() not in ('api_key', 'format')}
                key_str = json.dumps(filtered, sort_keys=True)
            elif isinstance(key_parts, (list, tuple)):
                # Convert elements to strings and join
                key_str = ":".join(str(k).lower() for k in key_parts if k)
            else:
                key_str = str(key_parts).lower()
            
            # Use hash for very long keys
            if len(key_str) > 200:
                import hashlib
                key_hash = hashlib.md5(key_str.encode('utf-8')).hexdigest()
                return key_hash
            
            return key_str
        except Exception as e:
            # If key generation fails, use a fallback mechanism
            print(f"Error creating cache key: {e}")
            import hashlib
            # Create a simple hash of the string representation
            return hashlib.md5(str(key_parts).encode('utf-8')).hexdigest()

    def _recover_partial_json(self, file_obj):
        """
        Attempts to recover partial JSON data from a corrupted file.
        
        Args:
            file_obj: Open file object
            
        Returns:
            Dictionary with data that could be recovered
        """
        try:
            # Read all content
            content = file_obj.read()
            
            # Look for complete JSON key-value pairs
            import re
            recovered_data = {}
            
            # Pattern to find "key": value pairs
            pattern = r'"([^"]+)"\s*:\s*(\{[^{}]*\}|\[[^\[\]]*\]|"[^"]*"|null|true|false|\d+(?:\.\d+)?)'
            matches = re.findall(pattern, content)
            
            for key, value in matches:
                try:
                    # Try to parse it as valid JSON
                    parsed_value = json.loads(value)
                    recovered_data[key] = parsed_value
                except json.JSONDecodeError:
                    # If it fails, skip this pair
                    continue
            
            return recovered_data
        except Exception as e:
            print(f"Error trying to recover partial data: {e}")
            return {}



 

def main(config=None):
    # Cargar configuración
    parser = argparse.ArgumentParser(description='Lastfm Scrobbles')
    parser.add_argument('--config', help='Archivo de configuración')
    parser.add_argument('--lastfm_user', type=str, help='Usuario de Last.fm')
    parser.add_argument('--lastfm-api-key', type=str, help='API key de Last.fm')
    parser.add_argument('--db-path', type=str, help='Ruta al archivo de base de datos SQLite')
    parser.add_argument('--force-update', type=str, choices=['true', 'false'], help='Forzar actualización completa')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar todos los scrobbles en formato JSON (opcional)')
    parser.add_argument('--interactive', type=str, choices=['true', 'false'], help='Modo interactivo para añadir nuevos elementos')
    parser.add_argument('--cache-dir', type=str, help='Directorio para archivos de caché')
    parser.add_argument('--add-items', type=str, choices=['true', 'false'], help='Añadir artistas, álbumes y canciones a la base de datos')
    parser.add_argument('--create-indices', type=str, choices=['true', 'false'], help='Crear índices optimizados para la base de datos')
            
    args = parser.parse_args()
    
    if args.config:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
            
        # Combinar configuraciones
        config = {}
        config.update(config_data.get("common", {}))
        config.update(config_data.get("lastfm_escuchas", {}))
    elif config is None:
        config = {}
    
    db_path = args.db_path or config.get('db_path')
    if not db_path: 
        print("Añade db_path al json o usa --db-path")
        return

    lastfm_user = args.lastfm_user or config.get('lastfm_user')
    if not lastfm_user: 
        print("Añade lastfm_user al json o usa --lastfm-user especificando tu usuario en lastfm")
        return

    lastfm_api_key = args.lastfm_api_key or config.get('lastfm_api_key')
    if not lastfm_api_key:
        print("Añade lastfm_api_key al json o usa --lastfm-api-key especificando tu api key en lastfm")
        return

    output_json = args.output_json or config.get("output_json")
    
    # Directorio de caché
    cache_dir = args.cache_dir or config.get('cache_dir', '.content/cache/api_cache')
    
    # Forzar impresión del directorio de caché
    print(f"Directorio de caché configurado: {cache_dir}")
    
    # Configurar caché ANTES de otras operaciones
    setup_cache(cache_dir)

    # Comprobar si añadir elementos - convertir a bool correctamente
    add_items_str = args.add_items or config.get('add_items', 'true')
    # Convertir string a bool
    add_items = add_items_str.lower() in ('true', 't', 'yes', 'y', '1') if isinstance(add_items_str, str) else bool(add_items_str)
    
    # Check for force_update in multiple places - convertir a bool correctamente
    global FORCE_UPDATE
    force_update_arg = args.force_update or config.get('force_update', 'false')
    # Convertir string a bool
    force_update = force_update_arg.lower() in ('true', 't', 'yes', 'y', '1') if isinstance(force_update_arg, str) else bool(force_update_arg)
    # Actualizar la variable global
    FORCE_UPDATE = force_update
    
    # Modo interactivo - convertir a bool correctamente
    interactive_str = args.interactive or config.get('interactive', 'false')
    # Convertir string a bool
    interactive = interactive_str.lower() in ('true', 't', 'yes', 'y', '1') if isinstance(interactive_str, str) else bool(interactive_str)
    # Actualizar la variable global
    global INTERACTIVE_MODE
    INTERACTIVE_MODE = interactive
    
    # Crear índices - convertir a bool correctamente
    create_indices_str = args.create_indices or config.get('create_indices', 'false')
    # Convertir string a bool
    create_indices = create_indices_str.lower() in ('true', 't', 'yes', 'y', '1') if isinstance(create_indices_str, str) else bool(create_indices_str)

    print(f"Modo force_update: {force_update}")
    print(f"Modo interactive: {interactive}")
    print(f"Añadir artistas/álbumes/canciones: {add_items}")
    
    # Configurar MusicBrainz y caché
    setup_musicbrainz(cache_dir)
    
    # Verificar API key
    if not check_api_key(lastfm_api_key):
        print("ERROR: La API key de Last.fm no es válida o hay problemas con el servicio.")
        print("Revisa tu API key y asegúrate de que el servicio de Last.fm esté disponible.")
        return 0, 0, 0, 0

    # Instanciar LastFMScrobbler
    scrobbler = LastFMScrobbler(db_path, lastfm_user, lastfm_api_key)
    scrobbler.interactive_mode = interactive
    scrobbler.cache_dir = cache_dir
    # Asignar explícitamente el valor de add_items
    scrobbler.add_items = add_items
    
    # Aplicar force_update si es necesario
    if force_update:
        handle_force_update(db_path, lastfm_user)
    
    # Crear índices si se solicita
    if create_indices:
        indices_creados = scrobbler.create_indices()
        print(f"Se crearon {indices_creados} índices optimizados")
        return indices_creados, 0, 0, 0
    
    # Obtener y procesar scrobbles
    result = scrobbler.update_scrobbles(force_update=force_update)
    
    # Exportar a JSON si se solicita
    if output_json:
        exported = scrobbler.export_scrobbles_to_json(output_json)
        print(f"Se exportaron {exported} scrobbles a {output_json}")
    
    return result


if __name__ == "__main__":
    main()