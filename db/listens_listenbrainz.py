#!/usr/bin/env python3
import sqlite3
import requests
import json
import argparse
import datetime
import time
import os
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description='Obtener listens de ListenBrainz y añadirlos a la base de datos')
    parser.add_argument('--config',  help='Archivo de configuración')
    parser.add_argument('--user', type=str,  help='Usuario de ListenBrainz')
    parser.add_argument('--token', type=str,  help='Token de autenticación de ListenBrainz')
    parser.add_argument('--db-path', type=str,  help='Ruta al archivo de base de datos SQLite')
    parser.add_argument('--force-update', default=False, help='Forzar actualización completa')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar todos los listens en formato JSON (opcional)')
    parser.add_argument('--max-items', type=int, default=1000, help='Número máximo de listens a obtener por llamada (opcional)')
    parser.add_argument('--limit-process', type=int, help='Número máximo de listens a procesar (opcional)')
    parser.add_argument('--reprocess-existing', default=False, help='Reprocesar listens existentes con los métodos de coincidencia seleccionados')

    # Nuevas opciones para las mejoras de coincidencia
    parser.add_argument('--normalize-strings', default=False, help='Usar normalización de strings para mejorar coincidencias')
    parser.add_argument('--enhanced-matching', default=False, help='Crear y usar tablas normalizadas para buscar coincidencias')
    parser.add_argument('--mbid-matching', default=False, help='Intentar coincidencia por MusicBrainz IDs')
    parser.add_argument('--fuzzy-matching', default=False, help='Usar coincidencia difusa para encontrar canciones')
    parser.add_argument('--analyze-mismatches', default=False, help='Analizar razones de discrepancias')
    parser.add_argument('--use-all-matching', default=False, help='Utilizar todas las técnicas de coincidencia mejoradas')
    
    return parser.parse_args()

def setup_database(conn):
    """Configura la base de datos con las tablas necesarias para listens de ListenBrainz"""
    cursor = conn.cursor()
    
    # Verificar si la tabla de listens existe, si no, crearla
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listens (
        id INTEGER PRIMARY KEY,
        track_name TEXT NOT NULL,
        album_name TEXT,
        artist_name TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        listen_date TIMESTAMP NOT NULL,
        listenbrainz_url TEXT,
        song_id INTEGER,
        album_id INTEGER,
        artist_id INTEGER,
        FOREIGN KEY (song_id) REFERENCES songs(id),
        FOREIGN KEY (album_id) REFERENCES albums(id),
        FOREIGN KEY (artist_id) REFERENCES artists(id)
    )
    """)
    
    # Crear índices para búsquedas eficientes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listens_timestamp ON listens(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listens_artist ON listens(artist_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listens_song_id ON listens(song_id)")
    
    # Crear tabla para configuración de ListenBrainz
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listenbrainz_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        username TEXT,
        last_timestamp INTEGER,
        last_updated TIMESTAMP
    )
    """)
    
    conn.commit()
def get_existing_items(conn):
    """Obtiene los artistas, álbumes y canciones existentes en la base de datos"""
    cursor = conn.cursor()
    
    # Obtener artistas existentes
    cursor.execute("SELECT id, name FROM artists")
    artists_rows = cursor.fetchall()
    artists = {row[1].lower(): row[0] for row in artists_rows}
    
    # Obtener álbumes existentes
    # Usando solo el nombre del álbum y el nombre del artista
    cursor.execute("""
        SELECT a.name, ar.name as artist_name
        FROM albums a 
        LEFT JOIN artists ar ON a.name = ar.name
    """)
    albums_rows = cursor.fetchall()
    albums = {(row[0].lower(), row[1].lower() if row[1] else ''): (None, None) for row in albums_rows}
    
    # Obtener canciones existentes
    # Usando solo nombres de canción, artista y álbum
    cursor.execute("""
        SELECT title, artist, album
        FROM songs
    """)
    songs_rows = cursor.fetchall()
    songs = {
        (row[0].lower(), row[1].lower() if row[1] else '', row[2].lower() if row[2] else None): None 
        for row in songs_rows
    }
    
    return artists, albums, songs

def get_last_timestamp(conn):
    """Obtiene el timestamp del último listen procesado desde la tabla de configuración"""
    cursor = conn.cursor()
    cursor.execute("SELECT last_timestamp FROM listenbrainz_config WHERE id = 1")
    result = cursor.fetchone()
    
    if result:
        return result[0]
    return 0

def save_last_timestamp(conn, timestamp, username):
    """Guarda el timestamp del último listen procesado en la tabla de configuración"""
    cursor = conn.cursor()
    
    # Intentar actualizar primero
    cursor.execute("""
        UPDATE listenbrainz_config 
        SET last_timestamp = ?, username = ?, last_updated = datetime('now')
        WHERE id = 1
    """, (timestamp, username))
    
    # Si no se actualizó ninguna fila, insertar
    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO listenbrainz_config (id, username, last_timestamp, last_updated)
            VALUES (1, ?, ?, datetime('now'))
        """, (username, timestamp))
    
    conn.commit()



def get_listenbrainz_listens(username, token, from_timestamp=0, max_items=1000, limit_total=None):
    """
    Obtiene los listens de ListenBrainz para un usuario desde un timestamp específico,
    gestionando correctamente la paginación.
    
    Args:
        username: Nombre de usuario de ListenBrainz
        token: Token de autorización
        from_timestamp: Timestamp desde el que empezar a obtener listens
        max_items: Máximo número de items por solicitud (por defecto 1000)
        limit_total: Límite total de listens a obtener (None para no límite)
    
    Returns:
        Lista de listens obtenidos
    """
    all_listens = []
    print(f"Obteniendo listens para el usuario: {username}")
    
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Token {token}'
    }
    
    base_url = 'https://api.listenbrainz.org/1/user/'
    
    # Convertir from_timestamp a entero si no lo es ya
    try:
        from_timestamp = int(from_timestamp)
    except (ValueError, TypeError):
        from_timestamp = 0
    
    # Determinar dirección de la paginación y punto de inicio
    if from_timestamp > 0:
        # Paginación hacia adelante desde un timestamp específico
        direction = "forward"
        current_ts = from_timestamp
        params_key = 'min_ts'  # Para paginación hacia adelante, usamos min_ts
    else:
        # Paginación hacia atrás desde el presente
        direction = "backward"
        current_ts = None
        params_key = 'max_ts'  # Para paginación hacia atrás, usamos max_ts
    
    endpoint = f'{username}/listens'
    url = f"{base_url}{endpoint}"
    
    # Función para extraer de forma segura el timestamp de un listen
    def safe_get_timestamp(listen):
        try:
            ts = listen.get('listened_at', 0)
            return int(ts) if ts is not None else 0
        except (ValueError, TypeError):
            return 0
    
    # Función para obtener listens con manejo de errores
    def fetch_listens(params):
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                print(f"Error al obtener listens: {response.status_code}")
                print(f"Detalles: {response.text}")
                return None
            return response.json()
        except Exception as e:
            print(f"Excepción al obtener listens: {e}")
            return None
    
    # Bucle de paginación
    more_results = True
    page = 1
    
    while more_results:
        # Construir parámetros para la solicitud
        params = {'count': max_items}
        
        # Añadir parámetro de timestamp para la paginación
        if direction == "forward" and current_ts:
            params['min_ts'] = current_ts
        elif direction == "backward" and current_ts:
            params['max_ts'] = current_ts
        
        # Primera página sin timestamp en backward
        if direction == "backward" and page == 1:
            # No añadir max_ts para la primera página en backward
            pass
        
        print(f"Obteniendo página {page} de listens con params: {params}")
        
        # Realizar solicitud
        data = fetch_listens(params)
        
        # Verificar respuesta
        if not data or 'payload' not in data or 'listens' not in data['payload']:
            print(f"No se encontraron más listens en la página {page}")
            more_results = False
            continue
        
        # Procesar listens recibidos
        listens = data['payload']['listens']
        if not listens:
            print(f"Página {page} vacía, finalizando paginación")
            more_results = False
            continue
        
        # Añadir a la lista general
        all_listens.extend(listens)
        print(f"Página {page}: Obtenidos {len(listens)} listens (total acumulado: {len(all_listens)})")
        
        # Comprobar si hemos alcanzado el límite total
        if limit_total and len(all_listens) >= limit_total:
            print(f"Alcanzado límite total de {limit_total} listens")
            more_results = False
            continue
        
        # Actualizar timestamp para la siguiente página
        if direction == "forward":
            # Para paginación forward, usar el timestamp más reciente + 1
            timestamps = [safe_get_timestamp(listen) for listen in listens]
            if timestamps:
                current_ts = max(timestamps) + 1
            else:
                more_results = False
        else:  # backward
            # Para paginación backward, usar el timestamp más antiguo - 1
            timestamps = [safe_get_timestamp(listen) for listen in listens]
            if timestamps:
                current_ts = min(timestamps) - 1
            else:
                more_results = False
        
        # Esperar un poco para no sobrecargar la API
        time.sleep(0.5)
        page += 1
        
        # Verificar si hay más resultados según la API
        if 'payload' in data and 'count' in data['payload'] and data['payload']['count'] < max_items:
            print(f"La API indica que no hay más resultados (recibidos {data['payload']['count']} < {max_items} solicitados)")
            more_results = False
    
    # Ordenar listens por timestamp antes de devolverlos
    all_listens.sort(key=lambda x: safe_get_timestamp(x))
    
    # Aplicar límite total si es necesario
    if limit_total and len(all_listens) > limit_total:
        all_listens = all_listens[:limit_total]
        print(f"Listens limitados a {limit_total} según parámetro limit_total")
    
    return all_listens
    
def process_listens(conn, listens, existing_artists, existing_albums, existing_songs, 
                    normalize_strings=False, use_mbid=False, use_fuzzy=False, limit=None):
    """
    Procesa los listens y actualiza la base de datos utilizando diferentes estrategias de coincidencia
    
    Args:
        conn: Conexión a la base de datos SQLite
        listens: Lista de objetos listen de ListenBrainz
        existing_artists: Diccionario de artistas existentes (nombre -> id)
        existing_albums: Diccionario de álbumes existentes ((nombre, artista) -> (id, artist_id))
        existing_songs: Diccionario de canciones existentes ((título, artista, álbum) -> id)
        normalize_strings: Si se debe normalizar las cadenas para mejorar coincidencias
        use_mbid: Si se debe intentar coincidencia por MusicBrainz IDs
        use_fuzzy: Si se debe usar coincidencia difusa
        limit: Número máximo de listens a procesar
        
    Returns:
        Tupla con (procesados, enlazados, no enlazados, timestamp más reciente)
    """
    cursor = conn.cursor()
    processed_count = 0
    linked_count = 0
    unlinked_count = 0
    newest_timestamp = 0
    
    # Para depuración
    failed_matches = []
    
    # Aplicar límite si se especificó
    if limit and len(listens) > limit:
        listens = listens[:limit]
        print(f"Procesando solo {limit} listens de {len(listens)} obtenidos")
    
    # Verificar si la columna additional_data existe, si no, crearla
    cursor.execute("PRAGMA table_info(listens)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'additional_data' not in columns:
        cursor.execute("ALTER TABLE listens ADD COLUMN additional_data TEXT")
        conn.commit()
    
    for listen in listens:
        # En ListenBrainz, la estructura es diferente a Last.fm
        track_metadata = listen.get('track_metadata', {})
        
        # Extraer información de track_metadata
        artist_name = track_metadata.get('artist_name', '')
        track_name = track_metadata.get('track_name', '')
        
        # Extraer información del álbum (si existe)
        additional_info = track_metadata.get('additional_info', {})
        album_name = additional_info.get('release_name', '')
        
        # Si no hay album_name en additional_info, intentar buscarlo en otros lugares
        if not album_name and 'release_name' in track_metadata:
            album_name = track_metadata.get('release_name', '')
        
        # En ListenBrainz, el timestamp está en seconds desde epoch
        try:
            timestamp = int(listen.get('listened_at', 0))
        except (ValueError, TypeError):
            timestamp = 0
        listen_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        # Construir URL de ListenBrainz para el listen
        listenbrainz_url = f"https://listenbrainz.org/user/{listen.get('user_name', '')}"
        
        # Actualizar el timestamp más reciente
        newest_timestamp = max(newest_timestamp, timestamp)
        
        # Verificar si el listen ya existe en la base de datos para evitar duplicados
        cursor.execute("SELECT id FROM listens WHERE timestamp = ? AND artist_name = ? AND track_name = ?", 
                      (timestamp, artist_name, track_name))
        existing = cursor.fetchone()
        if existing:
            # Si ya existe pero queremos actualizar sus metadatos
            store_track_metadata(conn, existing[0], listen)
            continue  # El listen ya existe, continuamos con el siguiente
        
        # Inicializar IDs
        song_id = None
        artist_id = None
        album_id = None
        
        # Estrategias de coincidencia en orden de prioridad:
        
        # 1. Intentar coincidencia por MusicBrainz IDs si está habilitado
        if use_mbid:
            song_id = find_song_by_mbid(conn, listen)
        
        # 2. Intentar coincidencia difusa si está habilitada y no se encontró por MBID
        if not song_id and use_fuzzy:
            # Si se debe normalizar strings, aplicar normalización
            if normalize_strings:
                norm_track = normalize_string(track_name)
                norm_artist = normalize_string(artist_name)
                norm_album = normalize_string(album_name) if album_name else None
                
                song_id = fuzzy_match_song(conn, norm_track, norm_artist, norm_album)
            else:
                song_id = fuzzy_match_song(conn, track_name, artist_name, album_name)
        
        # 3. Si no se encontró con métodos avanzados, intentar coincidencia exacta
        if not song_id:
            # 3.1 Intentar coincidencia exacta por nombre de artista
            if artist_name:
                artist_name_key = artist_name.lower()
                if normalize_strings:
                    artist_name_key = normalize_string(artist_name)
                artist_id = existing_artists.get(artist_name_key)
            
            # 3.2 Intentar coincidencia de álbum
            if album_name and artist_name:
                album_key = (album_name.lower(), artist_name.lower())
                if normalize_strings:
                    album_key = (normalize_string(album_name), normalize_string(artist_name))
                if album_key in existing_albums:
                    album_id, _ = existing_albums.get(album_key)
            
            # 3.3 Intentar coincidencia exacta por título, artista y álbum
            if track_name and artist_name:
                # Con álbum si está disponible
                if album_name:
                    song_key = (track_name.lower(), artist_name.lower(), album_name.lower())
                    if normalize_strings:
                        song_key = (normalize_string(track_name), normalize_string(artist_name), normalize_string(album_name))
                    if song_key in existing_songs:
                        song_id = existing_songs.get(song_key)
                
                # Sin álbum si no se encontró o no está disponible
                if not song_id:
                    song_key = (track_name.lower(), artist_name.lower(), None)
                    if normalize_strings:
                        song_key = (normalize_string(track_name), normalize_string(artist_name), None)
                    if song_key in existing_songs:
                        song_id = existing_songs.get(song_key)
            
            # 3.4 Buscar en la base de datos directamente con LIKE para ser más flexible
            if not song_id and track_name and artist_name:
                # Normalizar nombres para búsqueda
                track_search = track_name.replace("'", "''").lower()
                artist_search = artist_name.replace("'", "''").lower()
                
                if normalize_strings:
                    track_search = normalize_string(track_search)
                    artist_search = normalize_string(artist_search)
                
                cursor.execute("""
                    SELECT id FROM songs 
                    WHERE LOWER(title) LIKE ? AND LOWER(artist) LIKE ?
                    LIMIT 1
                """, (f"%{track_search}%", f"%{artist_search}%"))
                
                result = cursor.fetchone()
                if result:
                    song_id = result[0]
        
        # Si encontramos la canción, usar su información de texto
        if song_id:
            cursor.execute("""
                SELECT title, artist, album FROM songs 
                WHERE id = ?
            """, (song_id,))
            result = cursor.fetchone()
            if result:
                # Usar la información de texto para búsquedas adicionales
                existing_artist_name = result[1]
                existing_album_name = result[2]
                
                # Intentar obtener artist_id basado en el nombre del artista
                if existing_artist_name:
                    artist_name_key = existing_artist_name.lower()
                    if normalize_strings:
                        artist_name_key = normalize_string(existing_artist_name)
                    artist_id = existing_artists.get(artist_name_key)
                
                # Intentar obtener album_id basado en nombre de álbum y artista
                if existing_album_name and existing_artist_name:
                    album_key = (existing_album_name.lower(), existing_artist_name.lower())
                    if normalize_strings:
                        album_key = (normalize_string(existing_album_name), normalize_string(existing_artist_name))
                    if album_key in existing_albums:
                        album_id, _ = existing_albums.get(album_key)
        
        # Recoger información para depuración si no se encontró coincidencia
        if not song_id and processed_count < 50:  # Limitar para no llenar la memoria
            failed_matches.append({
                'track': track_name,
                'artist': artist_name,
                'album': album_name
            })
        
        # Insertar el listen en la tabla
        cursor.execute("""
            INSERT INTO listens 
            (track_name, album_name, artist_name, timestamp, listen_date, listenbrainz_url, song_id, album_id, artist_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (track_name, album_name, artist_name, timestamp, listen_date, listenbrainz_url, song_id, album_id, artist_id))
        
        listen_id = cursor.lastrowid
        
        # Almacenar metadatos completos del track
        store_track_metadata(conn, listen_id, listen)
        
        processed_count += 1
        
        # Contabilizar si se pudo enlazar con la base de datos
        if song_id:
            linked_count += 1
            
            # Actualizar song_links si el song_id existe
            cursor.execute("""
                UPDATE song_links 
                SET links_updated = datetime('now')
                WHERE song_id = ?
            """, (song_id,))
        else:
            unlinked_count += 1
    
    conn.commit()
    
    # Imprimir ejemplos de coincidencias fallidas para depuración
    if failed_matches:
        print("\nEjemplos de coincidencias fallidas:")
        for i, match in enumerate(failed_matches[:10]):  # Mostrar máximo 10 ejemplos
            print(f"{i+1}. Canción: '{match['track']}' - Artista: '{match['artist']}' - Álbum: '{match['album']}'")
    
    return processed_count, linked_count, unlinked_count, newest_timestamp

# Lo encontramos por cohones
def normalize_string(text):
    """Normaliza un string para mejorar las coincidencias"""
    if not text:
        return ""
    
    # Convertir a minúsculas
    text = text.lower()
    
    # Eliminar caracteres especiales y espacios extras
    import re
    text = re.sub(r'[^\w\s]', ' ', text)  # Reemplazar caracteres especiales con espacios
    text = re.sub(r'\s+', ' ', text).strip()  # Normalizar espacios
    
    # Eliminar palabras comunes que pueden variar entre fuentes
    words_to_remove = ['feat', 'ft', 'featuring', 'prod', 'remix', 'remaster', 'remastered']
    for word in words_to_remove:
        text = re.sub(r'\b' + word + r'\b', '', text)
    
    return text.strip()


def enhance_matching(conn, existing_artists, existing_albums, existing_songs):
    """Crea tablas de búsqueda normalizadas para mejorar las coincidencias"""
    cursor = conn.cursor()
    
    # Crear tablas temporales para búsqueda normalizada
    cursor.execute("DROP TABLE IF EXISTS normalized_songs")
    cursor.execute("""
        CREATE TABLE normalized_songs (
            song_id INTEGER PRIMARY KEY,
            normalized_title TEXT,
            normalized_artist TEXT,
            normalized_album TEXT
        )
    """)
    
    # Llenar la tabla normalizada de canciones
    cursor.execute("""
        SELECT id, title, artist, album FROM songs
    """)
    songs = cursor.fetchall()
    
    for song in songs:
        song_id, title, artist, album = song
        cursor.execute("""
            INSERT INTO normalized_songs 
            (song_id, normalized_title, normalized_artist, normalized_album)
            VALUES (?, ?, ?, ?)
        """, (song_id, normalize_string(title), normalize_string(artist), normalize_string(album)))
    
    # Crear índices para búsqueda rápida
    cursor.execute("CREATE INDEX idx_norm_title ON normalized_songs(normalized_title)")
    cursor.execute("CREATE INDEX idx_norm_artist ON normalized_songs(normalized_artist)")
    
    conn.commit()
    print("Tablas de normalización creadas para mejorar las coincidencias")
    
    return conn


def find_song_by_mbid(conn, listen):
    """Intenta encontrar una canción por su MusicBrainz ID"""
    cursor = conn.cursor()
    
    # Extraer MBIDs del listen si están disponibles
    additional_info = listen.get('track_metadata', {}).get('additional_info', {})
    
    recording_mbid = additional_info.get('recording_mbid')
    release_mbid = additional_info.get('release_mbid')
    artist_mbids = additional_info.get('artist_mbids', [])
    
    song_id = None
    
    # Buscar por recording_mbid (más específico)
    if recording_mbid:
        cursor.execute("SELECT id FROM songs WHERE mbid = ?", (recording_mbid,))
        result = cursor.fetchone()
        if result:
            return result[0]
        
        # También buscar en song_links
        cursor.execute("SELECT song_id FROM song_links WHERE musicbrainz_recording_id = ?", (recording_mbid,))
        result = cursor.fetchone()
        if result:
            return result[0]
    
    # Buscar por combinación de artist_mbid y release_mbid
    if artist_mbids and release_mbid:
        for artist_mbid in artist_mbids:
            cursor.execute("""
                SELECT s.id
                FROM songs s
                JOIN albums a ON s.album = a.name
                JOIN artists ar ON s.artist = ar.name
                WHERE ar.mbid = ? AND a.mbid = ?
            """, (artist_mbid, release_mbid))
            result = cursor.fetchone()
            if result:
                return result[0]
    
    return None


def fuzzy_match_song(conn, track_name, artist_name, album_name=None):
    """Usa coincidencia difusa para encontrar canciones similares"""
    cursor = conn.cursor()
    
    # Normalizar los términos de búsqueda
    normalized_track = normalize_string(track_name)
    normalized_artist = normalize_string(artist_name)
    normalized_album = normalize_string(album_name) if album_name else None
    
    # Estrategia 1: Buscar en la tabla normalizada (más rápido)
    if normalized_album:
        cursor.execute("""
            SELECT song_id FROM normalized_songs
            WHERE normalized_title = ? AND normalized_artist = ? AND normalized_album = ?
            LIMIT 1
        """, (normalized_track, normalized_artist, normalized_album))
        result = cursor.fetchone()
        if result:
            return result[0]
    
    # Estrategia 2: Solo por título y artista
    cursor.execute("""
        SELECT song_id FROM normalized_songs
        WHERE normalized_title = ? AND normalized_artist = ?
        LIMIT 1
    """, (normalized_track, normalized_artist))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Estrategia 3: Usar LIKE para coincidencia parcial
    track_search = f"%{normalized_track}%"
    artist_search = f"%{normalized_artist}%"
    
    cursor.execute("""
        SELECT song_id FROM normalized_songs
        WHERE normalized_title LIKE ? AND normalized_artist LIKE ?
        LIMIT 1
    """, (track_search, artist_search))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Estrategia 4: Solo buscar por artista exacto y título parcial
    cursor.execute("""
        SELECT song_id FROM normalized_songs
        WHERE normalized_artist = ? AND normalized_title LIKE ?
        LIMIT 1
    """, (normalized_artist, track_search))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    return None

def improve_process_listens(conn, listens, existing_artists, existing_albums, existing_songs, limit=None):
    """Versión mejorada de process_listens con mejor coincidencia"""
    # Primero, crear tablas normalizadas para búsqueda mejorada
    conn = enhance_matching(conn, existing_artists, existing_albums, existing_songs)
    cursor = conn.cursor()
    
    # Aplicar límite si se especificó
    if limit and len(listens) > limit:
        listens = listens[:limit]
        print(f"Procesando solo {limit} listens de {len(listens)} obtenidos")
    
    processed_count = 0
    linked_count = 0
    unlinked_count = 0
    newest_timestamp = 0
    
    # Verificar si la columna additional_data existe, si no, crearla
    cursor.execute("PRAGMA table_info(listens)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'additional_data' not in columns:
        cursor.execute("ALTER TABLE listens ADD COLUMN additional_data TEXT")
        conn.commit()
    
    for listen in listens:
        track_metadata = listen.get('track_metadata', {})
        artist_name = track_metadata.get('artist_name', '')
        track_name = track_metadata.get('track_name', '')
        additional_info = track_metadata.get('additional_info', {})
        album_name = additional_info.get('release_name', '')
        
        if not album_name and 'release_name' in track_metadata:
            album_name = track_metadata.get('release_name', '')
        
        try:
            timestamp = int(listen.get('listened_at', 0))
            listen_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            listenbrainz_url = f"https://listenbrainz.org/user/{listen.get('user_name', '')}"
        
            newest_timestamp = max(newest_timestamp, timestamp)
            
            # Verificar duplicados
            cursor.execute("SELECT id FROM listens WHERE timestamp = ? AND artist_name = ? AND track_name = ?", 
                          (timestamp, artist_name, track_name))
            existing = cursor.fetchone()
            if existing:
                # Si ya existe pero queremos reprocesarlo con nuevos métodos, actualizamos los metadatos
                store_track_metadata(conn, existing[0], listen)
                continue
            
            # Estrategias de coincidencia mejoradas
            song_id = None
            artist_id = None
            album_id = None
            
            # 1. Intentar coincidencia por MusicBrainz IDs
            song_id = find_song_by_mbid(conn, listen)
            
            if not song_id:
                # 2. Intentar coincidencia difusa si no hay MBID
                song_id = fuzzy_match_song(conn, track_name, artist_name, album_name)
            
            # Si encontramos la canción, obtener los IDs del artista y álbum
            if song_id:
                cursor.execute("SELECT artist, album FROM songs WHERE id = ?", (song_id,))
                result = cursor.fetchone()
                if result:
                    artist_id, album_id = result
            else:
                # Si no se encontró la canción, intentar buscar el artista y álbum por separado
                if artist_name:
                    artist_id = existing_artists.get(artist_name.lower())
                
                if album_name and artist_name:
                    album_key = (album_name.lower(), artist_name.lower())
                    if album_key in existing_albums:
                        album_id, artist_id = existing_albums.get(album_key)
            
            # Insertar el listen en la tabla
            cursor.execute("""
                INSERT INTO listens 
                (track_name, album_name, artist_name, timestamp, listen_date, listenbrainz_url, song_id, album_id, artist_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (track_name, album_name, artist_name, timestamp, listen_date, listenbrainz_url, song_id, album_id, artist_id))
            
            listen_id = cursor.lastrowid
            
            # Almacenar metadatos completos del track
            store_track_metadata(conn, listen_id, listen)
            
            processed_count += 1
            
            if song_id:
                linked_count += 1
                # Actualizar song_links si el song_id existe
                cursor.execute("""
                    UPDATE song_links 
                    SET links_updated = datetime('now')
                    WHERE song_id = ?
                """, (song_id,))
            else:
                unlinked_count += 1
        
        except (ValueError, TypeError):
            # Manejar errores de timestamp
            continue
    
    conn.commit()
    
    return processed_count, linked_count, unlinked_count, newest_timestamp

def analyze_mismatch_reasons(conn):
    """Analiza las razones de las discrepancias para ayudar a mejorar las coincidencias"""
    cursor = conn.cursor()
    
    print("\n=== ANÁLISIS DE DISCREPANCIAS ===")
    
    # 1. Muestreo de canciones sin coincidencia
    cursor.execute("""
        SELECT track_name, artist_name, album_name
        FROM listens
        WHERE song_id IS NULL
        LIMIT 20
    """)
    unmatched = cursor.fetchall()
    
    print(f"\n1. Muestra de canciones sin coincidencia ({len(unmatched)} ejemplos):")
    for track, artist, album in unmatched:
        print(f"   - '{track}' por '{artist}'" + (f" del álbum '{album}'" if album else ""))
    
    # 2. Verificar posibles coincidencias con normalización
    mismatches = []
    for track, artist, album in unmatched[:10]:  # Limitar a 10 para no hacer demasiadas consultas
        norm_track = normalize_string(track)
        norm_artist = normalize_string(artist)
        
        cursor.execute("""
            SELECT title, artist, album FROM songs
            WHERE LOWER(title) LIKE ? AND LOWER(artist) LIKE ?
            LIMIT 3
        """, (f"%{norm_track}%", f"%{norm_artist}%"))
        
        potential_matches = cursor.fetchall()
        if potential_matches:
            mismatches.append({
                'listen': (track, artist, album),
                'potential_matches': potential_matches
            })
    
    if mismatches:
        print("\n2. Posibles coincidencias que se están perdiendo:")
        for mismatch in mismatches:
            listen = mismatch['listen']
            print(f"   Listen: '{listen[0]}' por '{listen[1]}'")
            print(f"   Posibles coincidencias en la biblioteca:")
            for match in mismatch['potential_matches']:
                print(f"     - '{match[0]}' por '{match[1]}'" + (f" del álbum '{match[2]}'" if match[2] else ""))
            print()
    
    # 3. Estadísticas sobre los listen sin coincidencia
    cursor.execute("""
        SELECT COUNT(*) FROM listens WHERE song_id IS NULL AND album_name IS NULL
    """)
    no_album_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM listens WHERE song_id IS NULL
    """)
    total_unmatched = cursor.fetchone()[0]
    
    print(f"\n3. Estadísticas de listens sin coincidencia:")
    print(f"   - Total sin coincidencia: {total_unmatched}")
    print(f"   - Sin información de álbum: {no_album_count} ({no_album_count/total_unmatched*100:.1f}% del total sin coincidencia)")
    
    return True

def custom_process_listens(conn, listens, existing_artists, existing_albums, existing_songs, use_mbid=False, use_fuzzy=False, limit=None):
    """Procesa los listens utilizando las técnicas de coincidencia seleccionadas"""
    cursor = conn.cursor()
    processed_count = 0
    linked_count = 0
    unlinked_count = 0
    newest_timestamp = 0
    
    # Aplicar límite si se especificó
    if limit and len(listens) > limit:
        listens = listens[:limit]
        print(f"Procesando solo {limit} listens de {len(listens)} obtenidos")
    
    # Verificar si la columna additional_data existe, si no, crearla
    cursor.execute("PRAGMA table_info(listens)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'additional_data' not in columns:
        cursor.execute("ALTER TABLE listens ADD COLUMN additional_data TEXT")
        conn.commit()
    
    for listen in listens:
        track_metadata = listen.get('track_metadata', {})
        artist_name = track_metadata.get('artist_name', '')
        track_name = track_metadata.get('track_name', '')
        additional_info = track_metadata.get('additional_info', {})
        album_name = additional_info.get('release_name', '')
        
        if not album_name and 'release_name' in track_metadata:
            album_name = track_metadata.get('release_name', '')
        
        try:
            timestamp = int(listen.get('listened_at', 0))
            listen_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            listenbrainz_url = f"https://listenbrainz.org/user/{listen.get('user_name', '')}"
        
            newest_timestamp = max(newest_timestamp, timestamp)
            
            # Verificar duplicados
            cursor.execute("SELECT id FROM listens WHERE timestamp = ? AND artist_name = ? AND track_name = ?", 
                        (timestamp, artist_name, track_name))
            existing = cursor.fetchone()
            if existing:
                # Si ya existe pero queremos reprocesarlo con nuevos métodos, actualizamos los metadatos
                store_track_metadata(conn, existing[0], listen)
                continue
            
            # Inicializar IDs
            song_id = None
            artist_id = None
            album_id = None
            
            # Aplicar estrategias de coincidencia según los parámetros
            if use_mbid:
                # Intentar coincidencia por MusicBrainz IDs
                song_id = find_song_by_mbid(conn, listen)
            
            if not song_id and use_fuzzy:
                # Intentar coincidencia difusa
                song_id = fuzzy_match_song(conn, track_name, artist_name, album_name)
            
            # Si no se encontró con las técnicas avanzadas, intentar con la estrategia estándar
            if not song_id:
                # Buscar IDs existentes con estrategias estándar
                if artist_name:
                    artist_id = existing_artists.get(artist_name.lower())
                
                if album_name and artist_name:
                    album_key = (album_name.lower(), artist_name.lower())
                    if album_key in existing_albums:
                        album_id, artist_id = existing_albums.get(album_key)
                
                # Intentar buscar la canción con estrategias estándar
                if track_name and artist_name:
                    song_key = (track_name.lower(), artist_name.lower(), album_name.lower() if album_name else None)
                    if song_key in existing_songs:
                        song_id = existing_songs.get(song_key)
                    else:
                        # Intentar sin álbum
                        song_key = (track_name.lower(), artist_name.lower(), None)
                        if song_key in existing_songs:
                            song_id = existing_songs.get(song_key)
            
            # Si se encontró la canción, obtener los IDs de artista y álbum
            if song_id and (not artist_id or not album_id):
                cursor.execute("""
                    SELECT artist_id, album_id FROM songs 
                    WHERE id = ?
                """, (song_id,))
                result = cursor.fetchone()
                if result:
                    if not artist_id:
                        artist_id = result[0]
                    if not album_id:
                        album_id = result[1]
            
            # Si no se encontró artist_id, buscar en la tabla de artistas
            if not artist_id and artist_name:
                cursor.execute("""
                    SELECT id FROM artists 
                    WHERE lower(name) = lower(?)
                """, (artist_name,))
                artist_result = cursor.fetchone()
                if artist_result:
                    artist_id = artist_result[0]
            
            # Insertar el listen en la tabla
            cursor.execute("""
                INSERT INTO listens 
                (track_name, album_name, artist_name, timestamp, listen_date, listenbrainz_url, song_id, album_id, artist_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (track_name, album_name, artist_name, timestamp, listen_date, listenbrainz_url, song_id, album_id, artist_id))
            
            listen_id = cursor.lastrowid
            
            # Almacenar metadatos completos del track
            store_track_metadata(conn, listen_id, listen)
            
            processed_count += 1
            
            if song_id:
                linked_count += 1
                # Actualizar song_links si el song_id existe
                cursor.execute("""
                    UPDATE song_links 
                    SET links_updated = datetime('now')
                    WHERE song_id = ?
                """, (song_id,))
            else:
                unlinked_count += 1
        
        except (ValueError, TypeError):
            # Manejar errores de timestamp
            continue
    
    conn.commit()
    
    return processed_count, linked_count, unlinked_count, newest_timestamp


def store_track_metadata(conn, listen_id, listen):
    """Almacena los metadatos completos del track en formato JSON"""
    cursor = conn.cursor()
    
    if 'track_metadata' in listen:
        import json
        metadata_json = json.dumps(listen['track_metadata'])
        
        cursor.execute("""
            UPDATE listens
            SET additional_data = json_set(COALESCE(additional_data, '{}'), '$.track_metadata', json(?))
            WHERE id = ?
        """, (metadata_json, listen_id))
        
        return cursor.rowcount > 0
    
    return False

def reprocess_existing_listens(conn, existing_artists, existing_albums, existing_songs, use_mbid=False, use_fuzzy=False, limit=None):
    """Reprocesa los listens existentes utilizando las técnicas de coincidencia seleccionadas"""
    cursor = conn.cursor()
    
    # Verificar si la columna additional_data existe, si no, crearla
    cursor.execute("PRAGMA table_info(listens)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'additional_data' not in columns:
        cursor.execute("ALTER TABLE listens ADD COLUMN additional_data TEXT")
        conn.commit()
        print("Añadida columna additional_data a la tabla listens")
    
    # Ahora obtener los listens sin depender de la columna additional_data primero
    if limit:
        cursor.execute("""
            SELECT id, track_name, album_name, artist_name, timestamp, listen_date, listenbrainz_url
            FROM listens
            ORDER BY id
            LIMIT ?
        """, (limit,))
    else:
        cursor.execute("""
            SELECT id, track_name, album_name, artist_name, timestamp, listen_date, listenbrainz_url
            FROM listens
        """)
    
    rows = cursor.fetchall()
    total = len(rows)
    updated = 0
    
    print(f"Reprocesando {total} listens existentes...")
    
    for i, row in enumerate(rows):
        if i % 100 == 0 and i > 0:
            print(f"Procesados {i}/{total} listens...")
        
        listen_id, track_name, album_name, artist_name, timestamp, listen_date, listenbrainz_url = row
        
        # Inicializar IDs
        song_id = None
        artist_id = None
        album_id = None
        
        # Crear un objeto similar a un listen para usar con find_song_by_mbid
        listen_obj = {
            'track_metadata': {
                'artist_name': artist_name,
                'track_name': track_name,
                'additional_info': {
                    'release_name': album_name
                }
            }
        }
        
        # Intentar obtener metadata adicional si existe
        cursor.execute("SELECT additional_data FROM listens WHERE id = ?", (listen_id,))
        additional_data_row = cursor.fetchone()
        if additional_data_row and additional_data_row[0]:
            try:
                import json
                metadata = json.loads(additional_data_row[0])
                if 'track_metadata' in metadata:
                    listen_obj['track_metadata'] = metadata['track_metadata']
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Aplicar estrategias de coincidencia según los parámetros
        if use_mbid:
            song_id = find_song_by_mbid(conn, listen_obj)
        
        if not song_id and use_fuzzy:
            song_id = fuzzy_match_song(conn, track_name, artist_name, album_name)
        
        # Si no se encontró con las técnicas avanzadas, intentar con la estrategia estándar
        if not song_id:
            if artist_name:
                artist_id = existing_artists.get(artist_name.lower())
            
            if album_name and artist_name:
                album_key = (album_name.lower(), artist_name.lower())
                if album_key in existing_albums:
                    album_id, artist_id = existing_albums.get(album_key)
            
            if track_name and artist_name:
                song_key = (track_name.lower(), artist_name.lower(), album_name.lower() if album_name else None)
                if song_key in existing_songs:
                    song_id = existing_songs.get(song_key)
                else:
                    song_key = (track_name.lower(), artist_name.lower(), None)
                    if song_key in existing_songs:
                        song_id = existing_songs.get(song_key)
        
        # Si se encontró la canción, buscar información relacionada en la tabla songs
        if song_id:
            # Buscar información relacionada con la canción en la estructura existente
            cursor.execute("""
                SELECT artist, album FROM songs 
                WHERE id = ?
            """, (song_id,))
            result = cursor.fetchone()
            if result:
                artist_name_db, album_name_db = result
                
                # Ahora buscar los IDs correspondientes
                if artist_name_db:
                    artist_id = existing_artists.get(artist_name_db.lower())
                
                if album_name_db and artist_name_db:
                    album_key = (album_name_db.lower(), artist_name_db.lower())
                    if album_key in existing_albums:
                        album_id, _ = existing_albums.get(album_key)
        
        # Actualizar el listen solo si hay cambios
        cursor.execute("""
            UPDATE listens 
            SET song_id = ?, album_id = ?, artist_id = ?
            WHERE id = ?
        """, (song_id, album_id, artist_id, listen_id))
        
        if cursor.rowcount > 0:
            updated += 1
        
        # Actualizar song_links si el song_id existe
        if song_id:
            cursor.execute("""
                UPDATE song_links 
                SET links_updated = datetime('now')
                WHERE song_id = ?
            """, (song_id,))
    
    conn.commit()
    print(f"Reprocesamiento completado. Actualizados {updated} de {total} listens.")
    
    return updated


def debug_listens_timestamps(listens):
    """
    Detailed debugging for ListenBrainz listen timestamps
    
    Args:
        listens (list): List of listen records
    """
    print("Timestamp Debugging")
    print("-" * 40)
    
    if not listens:
        print("No listens to analyze")
        return
    
    # Analyze timestamp information
    timestamp_types = {}
    timestamp_values = []
    problematic_listens = []
    
    for i, listen in enumerate(listens, 1):
        timestamp = listen.get('listened_at')
        
        # Track type distribution
        type_name = type(timestamp).__name__
        timestamp_types[type_name] = timestamp_types.get(type_name, 0) + 1
        
        # Try converting to integer
        try:
            int_timestamp = int(timestamp)
            timestamp_values.append(int_timestamp)
        except (ValueError, TypeError) as e:
            problematic_listens.append({
                'index': i,
                'timestamp': timestamp,
                'type': type(timestamp).__name__,
                'error': str(e)
            })
    
    # Print summary
    print("\nTimestamp Type Distribution:")
    for type_name, count in timestamp_types.items():
        print(f"  {type_name}: {count} listens")
    
    print("\nTimestamp Value Range:")
    if timestamp_values:
        print(f"  Min: {min(timestamp_values)}")
        print(f"  Max: {max(timestamp_values)}")
        print(f"  Total valid timestamps: {len(timestamp_values)}")
    
    print("\nProblematic Listens:")
    for listen in problematic_listens[:10]:  # Show first 10
        print(f"  Listen {listen['index']}: "
              f"timestamp={listen['timestamp']}, "
              f"type={listen['type']}, "
              f"error={listen['error']}")
    
    return problematic_listens

def safe_convert_timestamps(listens):
    """
    Safely convert ListenBrainz listen timestamps to integers
    
    Args:
        listens (list): List of listen records
    
    Returns:
        list: Updated listens with converted timestamps
    """
    converted_listens = []
    
    for listen in listens:
        try:
            # Try multiple conversion strategies
            timestamp = listen.get('listened_at')
            
            # Strategy 1: Direct integer conversion
            if isinstance(timestamp, int):
                converted_listen = listen.copy()
                converted_listen['listened_at'] = timestamp
                converted_listens.append(converted_listen)
                continue
            
            # Strategy 2: String to integer
            if isinstance(timestamp, str):
                int_timestamp = int(float(timestamp))
                converted_listen = listen.copy()
                converted_listen['listened_at'] = int_timestamp
                converted_listens.append(converted_listen)
                continue
            
            # Strategy 3: Extract timestamp from nested structures
            if isinstance(timestamp, dict):
                for key in ['timestamp', 'listened_at', 'time']:
                    if key in timestamp:
                        int_timestamp = int(float(timestamp[key]))
                        converted_listen = listen.copy()
                        converted_listen['listened_at'] = int_timestamp
                        converted_listens.append(converted_listen)
                        break
            
            # If no conversion worked, skip this listen
            print(f"Could not convert timestamp: {timestamp}")
        
        except (ValueError, TypeError) as e:
            print(f"Timestamp conversion error: {e}")
    
    return converted_listens



def main():
    args = parse_args()
    
    
    with open(args.config, 'r') as f:
        config_data = json.load(f)
    
    config = {}
    config.update(config_data.get("common", {}))
    config.update(config_data.get("scrobbles_listenbrainz", {}))

    db_path = args.db_path or config['db_path']
    if not db_path: 
        print("Añade db_path al json o usa --db-path")

    user = args.user or config['user']
    token = args.token or config['token']
    output_json = args.output_json or config['output_json']
    max_items = args.max_items or config['max_items']
    limit_process = args.limit_process or config['limit_process']
    
    
    
    force_update = args.force_update or config['force_update']
    reprocess_existing = args.reprocess_existing or config['reprocess_existing']
    normalize_strings = args.normalize_strings or config['normalize_strings']
    mbid_matching = args.mbid_matching or config['mbid_matching']
    fuzzy_matching = args.fuzzy_matching or config['fuzzy_matching']
    use_all_matching = args.use_all_matching or config['use_all_matching']
    analyze_mismatches = args.analyze_mismatches or config['analyze_mismatches']
    
    enhanced_matching = args.enhanced_matching or config['enhanced_matching']
    


    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    
    try:
        # Configurar la base de datos
        setup_database(conn)
        
        # Obtener elementos existentes
        existing_artists, existing_albums, existing_songs = get_existing_items(conn)
        print(f"Elementos existentes: {len(existing_artists)} artistas, {len(existing_albums)} álbumes, {len(existing_songs)} canciones")
        
     
        # Crear tablas normalizadas si se solicita
        if enhanced_matching == True or use_all_matching:
            print("Creando tablas normalizadas para mejorar búsquedas")
            conn = enhance_matching(conn, existing_artists, existing_albums, existing_songs)
        
        # Reprocesar listens existentes si se solicita
        if reprocess_existing == True:
            print("Reprocesando listens existentes...")
            updated = reprocess_existing_listens(
                conn, 
                existing_artists, 
                existing_albums, 
                existing_songs,
                use_mbid=mbid_matching or use_all_matching,
                use_fuzzy=fuzzy_matching or use_all_matching,
                limit=limit_process
            )
            print(f"Reprocesamiento completado: {updated} listens actualizados")
        
        # Obtener el último timestamp procesado
        if force_update == True:
            from_timestamp = 0
            print("Obteniendo todos los listens (esto puede tardar)")
        else:
            from_timestamp = get_last_timestamp(conn)
            print(f"Obteniendo listens desde {datetime.datetime.fromtimestamp(from_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")



        # Obtener listens de ListenBrainz
        listens = get_listenbrainz_listens(user, token, from_timestamp, max_items, limit_process)
        print(f"Obtenidos {len(listens)} listens")
        debug_listens_timestamps(listens)
        listens = safe_convert_timestamps(listens)


        # Guardar todos los listens en JSON si se especificó
        if output_json and listens:
            with open(output_json, 'w') as f:
                json.dump(listens, f, indent=2)
            print(f"Guardados todos los listens en {output_json}")
        
        # Procesar listens según las opciones seleccionadas
        if listens:
            if use_all_matching:
                # Usar el proceso mejorado con todas las técnicas
                processed, linked, unlinked, newest_timestamp = improve_process_listens(
                    conn, listens, existing_artists, existing_albums, existing_songs, limit_process
                )
            else:
                # Determinar qué funciones usar basado en los argumentos
                if mbid_matching == True or fuzzy_matching == True:
                    # Función personalizada según las opciones seleccionadas
                    processed, linked, unlinked, newest_timestamp = custom_process_listens(
                        conn, listens, existing_artists, existing_albums, existing_songs,
                        use_mbid=mbid_matching, use_fuzzy=fuzzy_matching,
                        limit=limit_process
                    )
                else:
                    # Usar el proceso estándar con opciones de normalización si se especificó
                    processed, linked, unlinked, newest_timestamp = process_listens(
                        conn, listens, existing_artists, existing_albums, existing_songs,
                        normalize_strings=normalize_strings,
                        use_mbid=mbid_matching,
                        use_fuzzy=fuzzy_matching,
                        limit=limit_process
                    )
            
            print(f"Procesados {processed} listens: {linked} enlazados, {unlinked} no enlazados")
            
            # Guardar el timestamp más reciente para la próxima ejecución
            if newest_timestamp > 0:
                save_last_timestamp(conn, newest_timestamp, user)
                print(f"Guardado último timestamp: {datetime.datetime.fromtimestamp(newest_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("No se encontraron nuevos listens para procesar")
        
        # Analizar discrepancias si se solicita
        if analyze_mismatches == True:
            analyze_mismatch_reasons(conn)
        
        # Mostrar estadísticas generales
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM listens")
        total_listens = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM listens WHERE song_id IS NOT NULL")
        matched_listens = cursor.fetchone()[0]
        
        match_percentage = 0 if total_listens == 0 else (matched_listens / total_listens * 100)
        print(f"Estadísticas generales: {total_listens} listens totales, {matched_listens} enlazados con canciones ({match_percentage:.1f}% de coincidencia)")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()