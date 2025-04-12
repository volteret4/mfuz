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

INTERACTIVE_MODE = False  # This will be set by db_creator.py


def setup_database(conn):
    """Configura la base de datos con las tablas necesarias para scrobbles"""
    cursor = conn.cursor()
    
    # Crear tabla de scrobbles si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scrobbles (
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
    
    # Crear índice para búsquedas eficientes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scrobbles_timestamp ON scrobbles(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scrobbles_artist ON scrobbles(artist_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scrobbles_song_id ON scrobbles(song_id)")
    
    # Crear tabla para configuración
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lastfm_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        lastfm_username TEXT,
        last_timestamp INTEGER,
        last_updated TIMESTAMP
    )
    """)
    
    # Crear tabla de artistas si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS artists (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        mbid TEXT,
        tags TEXT,
        bio TEXT,
        lastfm_url TEXT,
        origen TEXT
    )
    """)
    
    # Crear tabla de álbumes si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS albums (
        id INTEGER PRIMARY KEY,
        artist_id INTEGER,
        name TEXT NOT NULL,
        year INTEGER,
        lastfm_url TEXT,
        mbid TEXT,
        total_tracks INTEGER,
        FOREIGN KEY (artist_id) REFERENCES artists(id)
    )
    """)
    
    # Crear tabla de canciones si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS songs (
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
        artist TEXT NOT NULL
    )
    """)
    
    # Función para comprobar si una columna existe en una tabla
    def column_exists(table, column):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [info[1] for info in cursor.fetchall()]
        return column in columns
    
    # Añadir columna 'origen' a la tabla artists si no existe
    if not column_exists('artists', 'origen'):
        cursor.execute("ALTER TABLE artists ADD COLUMN origen TEXT")
    
    # Añadir columna 'origen' a la tabla albums si no existe
    if not column_exists('albums', 'origen'):
        cursor.execute("ALTER TABLE albums ADD COLUMN origen TEXT")
    
    # Añadir columna 'origen' a la tabla songs si no existe
    if not column_exists('songs', 'origen'):
        cursor.execute("ALTER TABLE songs ADD COLUMN origen TEXT")
    
    conn.commit()

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

def get_last_timestamp(conn):
    """Obtiene el timestamp del último scrobble procesado desde la tabla de configuración"""
    cursor = conn.cursor()
    cursor.execute("SELECT last_timestamp FROM lastfm_config WHERE id = 1")
    result = cursor.fetchone()
    
    if result:
        return result[0]
    return 0

def save_last_timestamp(conn, timestamp, lastfm_username):
    """Guarda el timestamp del último scrobble procesado en la tabla de configuración"""
    cursor = conn.cursor()
    
    # Intentar actualizar primero
    cursor.execute("""
        UPDATE lastfm_config 
        SET last_timestamp = ?, lastfm_username = ?, last_updated = datetime('now')
        WHERE id = 1
    """, (timestamp, lastfm_username))
    
    # Si no se actualizó ninguna fila, insertar
    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO lastfm_config (id, lastfm_username, last_timestamp, last_updated)
            VALUES (1, ?, ?, datetime('now'))
        """, (lastfm_username, timestamp))
    
    conn.commit()

# LASTFM INFO

def get_artist_info(artist_name, mbid, lastfm_api_key):
    """Obtiene información detallada de un artista desde Last.fm"""
    params = {
        'method': 'artist.getInfo',
        'artist': artist_name,
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    if mbid:
        params['mbid'] = mbid
    
    print(f"Consultando información para artista: {artist_name} (MBID: {mbid})")
    print(f"URL de consulta: http://ws.audioscrobbler.com/2.0/ con params: {params}")
    
    try:
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        print(f"Código de respuesta: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error al obtener información del artista {artist_name}: {response.status_code}")
            print(f"Respuesta de error: {response.text[:200]}...")
            return None
        
        data = response.json()
        
        # Verificar si hay un mensaje de error en la respuesta JSON
        if 'error' in data:
            print(f"Error de la API de Last.fm: {data['message']} (código {data['error']})")
            return None
            
        if 'artist' not in data:
            print(f"No se encontró información para el artista {artist_name}")
            print(f"Respuesta completa: {data}")
            return None
        
        print(f"Información obtenida correctamente para artista: {artist_name}")
        return data['artist']
    
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión al consultar artista {artist_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error al decodificar respuesta JSON para artista {artist_name}: {e}")
        print(f"Respuesta recibida: {response.text[:200]}...")
        return None
    except Exception as e:
        print(f"Error inesperado al consultar artista {artist_name}: {e}")
        return None

def get_album_info(album_name, artist_name, mbid, lastfm_api_key):
    """Obtiene información detallada de un álbum desde Last.fm"""
    params = {
        'method': 'album.getInfo',
        'album': album_name,
        'artist': artist_name,
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    if mbid:
        params['mbid'] = mbid
    
    print(f"Consultando información para álbum: {album_name} de {artist_name} (MBID: {mbid})")
    print(f"URL de consulta: http://ws.audioscrobbler.com/2.0/ con params: {params}")
    
    try:
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        print(f"Código de respuesta: {response.status_code}")
        
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
            print(f"Respuesta completa: {data}")
            return None
        
        print(f"Información obtenida correctamente para álbum: {album_name}")
        return data['album']
    
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión al consultar álbum {album_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error al decodificar respuesta JSON para álbum {album_name}: {e}")
        print(f"Respuesta recibida: {response.text[:200]}...")
        return None
    except Exception as e:
        print(f"Error inesperado al consultar álbum {album_name}: {e}")
        return None

def get_track_info(track_name, artist_name, mbid, lastfm_api_key):
    """Obtiene información detallada de una canción desde Last.fm"""
    params = {
        'method': 'track.getInfo',
        'track': track_name,
        'artist': artist_name,
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    if mbid:
        params['mbid'] = mbid
    
    print(f"Consultando información para canción: {track_name} de {artist_name} (MBID: {mbid})")
    print(f"URL de consulta: http://ws.audioscrobbler.com/2.0/ con params: {params}")
    
    try:
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        print(f"Código de respuesta: {response.status_code}")
        
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
            print(f"Respuesta completa: {data}")
            return None
        
        print(f"Información obtenida correctamente para canción: {track_name}")
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

def add_artist_to_db(conn, artist_info, interactive=False):
    """Añade un nuevo artista a la base de datos"""
    cursor = conn.cursor()
    
    artist_name = artist_info.get('name', '')
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
    
    if interactive:
        print(f"\n===== NUEVO ARTISTA =====")
        print(f"Artista: {artist_name}")
        print(f"MBID: {mbid}")
        print(f"URL: {url}")
        print(f"Tags: {tags_str}")
        print(f"Bio: {bio[:100]}..." if len(bio) > 100 else f"Bio: {bio}")
        
        respuesta = input("\n¿Añadir este artista a la base de datos? (s/n): ").lower()
        if respuesta != 's':
            print("Artista no añadido por decisión del usuario.")
            return None
    
    try:
        cursor.execute("""
            INSERT INTO artists (name, mbid, tags, bio, lastfm_url, origen)
            VALUES (?, ?, ?, ?, ?, 'online')
            RETURNING id
        """, (artist_name, mbid, tags_str, bio, url))
        
        artist_id = cursor.fetchone()[0]
        conn.commit()
        return artist_id
    except sqlite3.Error as e:
        print(f"Error al añadir el artista {artist_name}: {e}")
        return None
def add_album_to_db(conn, album_info, artist_id, interactive=False):
    """Añade un nuevo álbum a la base de datos"""
    cursor = conn.cursor()
    
    album_name = album_info.get('name', '')
    mbid = album_info.get('mbid', '')
    url = album_info.get('url', '')
    
    # Extraer año
    year = None
    if 'releasedate' in album_info:
        try:
            release_date = album_info['releasedate'].strip()
            if release_date:
                year = datetime.datetime.strptime(release_date, '%d %b %Y, %H:%M').year
        except (ValueError, AttributeError):
            pass
    
    # Número de pistas
    total_tracks = 0
    if 'tracks' in album_info and 'track' in album_info['tracks']:
        tracks = album_info['tracks']['track']
        if isinstance(tracks, list):
            total_tracks = len(tracks)
        else:
            total_tracks = 1
    
    if interactive:
        print(f"\n===== NUEVO ÁLBUM =====")
        print(f"Álbum: {album_name}")
        print(f"MBID: {mbid}")
        print(f"URL: {url}")
        print(f"Año: {year}")
        print(f"Total pistas: {total_tracks}")
        
        respuesta = input("\n¿Añadir este álbum a la base de datos? (s/n): ").lower()
        if respuesta != 's':
            print("Álbum no añadido por decisión del usuario.")
            return None
    
    try:
        cursor.execute("""
            INSERT INTO albums (artist_id, name, year, lastfm_url, mbid, total_tracks, origen)
            VALUES (?, ?, ?, ?, ?, ?, 'online')
            RETURNING id
        """, (artist_id, album_name, year, url, mbid, total_tracks))
        
        album_id = cursor.fetchone()[0]
        conn.commit()
        return album_id
    except sqlite3.Error as e:
        print(f"Error al añadir el álbum {album_name}: {e}")
        return None

def add_song_to_db(conn, track_info, album_id, artist_id, interactive=False):
    """Añade una nueva canción a la base de datos"""
    cursor = conn.cursor()
    
    track_name = track_info.get('name', '')
    mbid = track_info.get('mbid', '')
    
    # Obtener duración
    duration = None
    if 'duration' in track_info:
        try:
            duration = int(track_info['duration']) // 1000  # Convertir de ms a segundos
        except (ValueError, TypeError):
            pass
    
    # Obtener información del álbum y artista
    album_name = ''
    artist_name = ''
    
    if 'album' in track_info and 'title' in track_info['album']:
        album_name = track_info['album']['title']
    
    if 'artist' in track_info and 'name' in track_info['artist']:
        artist_name = track_info['artist']['name']
    
    # Géneros (tags)
    genre = ''
    if 'toptags' in track_info and 'tag' in track_info['toptags']:
        tags = track_info['toptags']['tag']
        if isinstance(tags, list) and tags:
            genre = tags[0]['name']
        elif isinstance(tags, dict):
            genre = tags.get('name', '')
    
    # Fecha actual para campos de tiempo
    now = datetime.datetime.now()
    added_timestamp = int(time.time())
    added_week = now.isocalendar()[1]
    added_month = now.month
    added_year = now.year
    
    if interactive:
        print(f"\n===== NUEVA CANCIÓN =====")
        print(f"Canción: {track_name}")
        print(f"MBID: {mbid}")
        print(f"Duración: {duration} segundos")
        print(f"Álbum: {album_name}")
        print(f"Artista: {artist_name}")
        print(f"Género: {genre}")
        
        respuesta = input("\n¿Añadir esta canción a la base de datos? (s/n): ").lower()
        if respuesta != 's':
            print("Canción no añadida por decisión del usuario.")
            return None
    
    try:
        cursor.execute("""
            INSERT INTO songs 
            (title, mbid, added_timestamp, added_week, added_month, added_year, 
             duration, album, album_artist, artist, genre, origen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'online')
            RETURNING id
        """, (track_name, mbid, added_timestamp, added_week, added_month, added_year,
              duration, album_name, artist_name, artist_name, genre))
        
        song_id = cursor.fetchone()[0]
        conn.commit()
        return song_id
    except sqlite3.Error as e:
        print(f"Error al añadir la canción {track_name}: {e}")
        return None

# SCROBBLES
def get_lastfm_scrobbles(lastfm_username, lastfm_api_key, from_timestamp=0, limit=200, progress_callback=None):
    """Obtiene los scrobbles de Last.fm para un usuario desde un timestamp específico
    
    Args:
        lastfm_username: Nombre de usuario de Last.fm
        lastfm_api_key: API key de Last.fm
        from_timestamp: Timestamp desde el que obtener scrobbles
        limit: Número máximo de scrobbles por página
        progress_callback: Función para reportar progreso (mensaje, porcentaje)
    """
    all_tracks = []
    page = 1
    total_pages = 1
    
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
    
    # Informar del total obtenido
    if progress_callback:
        progress_callback(f"Obtenidos {len(all_tracks)} scrobbles en total", 30)
    else:
        print(f"Obtenidos {len(all_tracks)} scrobbles en total")
        
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
    """Actualiza información de un artista existente desde Last.fm"""
    cursor = conn.cursor()
    
    artist_name = artist_info.get('name', '')
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
    
    try:
        # Actualizar solo campos que estén presentes y no sean nulos
        updates = []
        params = []
        
        if mbid:
            updates.append("mbid = COALESCE(mbid, ?)")
            params.append(mbid)
        
        if tags_str:
            updates.append("tags = COALESCE(tags, ?)")
            params.append(tags_str)
        
        if bio:
            updates.append("bio = COALESCE(bio, ?)")
            params.append(bio)
        
        if url:
            updates.append("lastfm_url = COALESCE(lastfm_url, ?)")
            params.append(url)
        
        # Siempre actualizar origen a 'online' para marcar que ha sido verificado
        updates.append("origen = 'online'")
        
        if updates:
            sql = f"UPDATE artists SET {', '.join(updates)} WHERE id = ?"
            params.append(artist_id)
            cursor.execute(sql, params)
            conn.commit()
            print(f"Artista con ID {artist_id} actualizado correctamente")
            return True
    except sqlite3.Error as e:
        print(f"Error al actualizar el artista ID {artist_id}: {e}")
    
    return False

def update_album_in_db(conn, album_id, album_info):
    """Actualiza información de un álbum existente desde Last.fm"""
    cursor = conn.cursor()
    
    album_name = album_info.get('name', '')
    mbid = album_info.get('mbid', '')
    url = album_info.get('url', '')
    
    # Extraer año
    year = None
    if 'releasedate' in album_info:
        try:
            release_date = album_info['releasedate'].strip()
            if release_date:
                year = datetime.datetime.strptime(release_date, '%d %b %Y, %H:%M').year
        except (ValueError, AttributeError):
            pass
    
    # Número de pistas
    total_tracks = 0
    if 'tracks' in album_info and 'track' in album_info['tracks']:
        tracks = album_info['tracks']['track']
        if isinstance(tracks, list):
            total_tracks = len(tracks)
        else:
            total_tracks = 1
    
    try:
        # Actualizar solo campos que estén presentes y no sean nulos
        updates = []
        params = []
        
        if mbid:
            updates.append("mbid = COALESCE(mbid, ?)")
            params.append(mbid)
        
        if year:
            updates.append("year = COALESCE(year, ?)")
            params.append(year)
        
        if url:
            updates.append("lastfm_url = COALESCE(lastfm_url, ?)")
            params.append(url)
        
        if total_tracks > 0:
            updates.append("total_tracks = COALESCE(total_tracks, ?)")
            params.append(total_tracks)
        
        # Siempre actualizar origen a 'online' para marcar que ha sido verificado
        updates.append("origen = 'online'")
        
        if updates:
            sql = f"UPDATE albums SET {', '.join(updates)} WHERE id = ?"
            params.append(album_id)
            cursor.execute(sql, params)
            conn.commit()
            print(f"Álbum con ID {album_id} actualizado correctamente")
            return True
    except sqlite3.Error as e:
        print(f"Error al actualizar el álbum ID {album_id}: {e}")
    
    return False

def update_song_in_db(conn, song_id, track_info):
    """Actualiza información de una canción existente desde Last.fm"""
    cursor = conn.cursor()
    
    track_name = track_info.get('name', '')
    mbid = track_info.get('mbid', '')
    
    # Obtener duración
    duration = None
    if 'duration' in track_info:
        try:
            duration = int(track_info['duration']) // 1000  # Convertir de ms a segundos
        except (ValueError, TypeError):
            pass
    
    # Géneros (tags)
    genre = ''
    if 'toptags' in track_info and 'tag' in track_info['toptags']:
        tags = track_info['toptags']['tag']
        if isinstance(tags, list) and tags:
            genre = tags[0]['name']
        elif isinstance(tags, dict):
            genre = tags.get('name', '')
    
    try:
        # Actualizar solo campos que estén presentes y no sean nulos
        updates = []
        params = []
        
        if mbid:
            updates.append("mbid = COALESCE(mbid, ?)")
            params.append(mbid)
        
        if duration:
            updates.append("duration = COALESCE(duration, ?)")
            params.append(duration)
        
        if genre:
            updates.append("genre = COALESCE(genre, ?)")
            params.append(genre)
        
        # Siempre actualizar origen a 'online' para marcar que ha sido verificado
        updates.append("origen = 'online'")
        
        if updates:
            sql = f"UPDATE songs SET {', '.join(updates)} WHERE id = ?"
            params.append(song_id)
            cursor.execute(sql, params)
            conn.commit()
            print(f"Canción con ID {song_id} actualizada correctamente")
            return True
    except sqlite3.Error as e:
        print(f"Error al actualizar la canción ID {song_id}: {e}")
    
    return False



def process_scrobbles(conn, tracks, existing_artists, existing_albums, existing_songs, lastfm_api_key, interactive=False):
    """Procesa los scrobbles y actualiza la base de datos con los nuevos scrobbles"""
    cursor = conn.cursor()
    processed_count = 0
    linked_count = 0
    unlinked_count = 0
    newest_timestamp = 0
    
    print(f"Modo interactivo: {'ACTIVADO' if interactive else 'DESACTIVADO'}")
    print(f"Total de tracks a procesar: {len(tracks)}")
    
    new_artists_attempts = 0
    new_artists_success = 0
    new_albums_attempts = 0
    new_albums_success = 0
    new_songs_attempts = 0
    new_songs_success = 0
    
    new_artists = {}  # Para almacenar artistas nuevos y evitar consultas repetidas
    new_albums = {}   # Para almacenar álbumes nuevos y evitar consultas repetidas
    new_songs = {}    # Para almacenar canciones nuevas y evitar consultas repetidas
    
    # Verificar si hay scrobbles duplicados
    cursor.execute("SELECT timestamp FROM scrobbles ORDER BY timestamp DESC LIMIT 1")
    last_db_timestamp = cursor.fetchone()
    last_db_timestamp = last_db_timestamp[0] if last_db_timestamp else 0
    
    # Información de los errores encontrados
    errors = {
        'artist_not_found': 0,
        'album_not_found': 0,
        'song_not_found': 0,
        'api_errors': 0,
        'db_errors': 0
    }
    
    # Preparar lotes para inserción
    scrobbles_batch = []
    batch_size = 100
    
    for track_idx, track in enumerate(tracks):
        # Actualizar progreso
        if progress_callback and (track_idx % 10 == 0 or track_idx == len(tracks) - 1):
            progress_callback(f"Procesando scrobble {track_idx+1}/{len(tracks)}", 
                             (track_idx + 1) / len(tracks) * 100)
        
        if progress_callback is None:
            print(f"\nProcesando scrobble {track_idx+1}/{len(tracks)}")
            
        artist_name = track['artist']['#text']
        album_name = track['album']['#text'] if track['album']['#text'] else None
        track_name = track['name']
        timestamp = int(track['date']['uts'])
        scrobble_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        lastfm_url = track['url']
        
        if progress_callback is None:
            print(f"Artista: {artist_name}, Álbum: {album_name}, Canción: {track_name}")
        
        # Actualizar el timestamp más reciente
        newest_timestamp = max(newest_timestamp, timestamp)
        
        # Verificar si el scrobble ya existe en la base de datos para evitar duplicados
        cursor.execute("SELECT id FROM scrobbles WHERE timestamp = ? AND artist_name = ? AND track_name = ?", 
                      (timestamp, artist_name, track_name))
        if cursor.fetchone():
            if progress_callback is None:
                print(f"Scrobble duplicado, saltando")
            continue  # El scrobble ya existe, continuamos con el siguiente
        
        # Buscar IDs existentes en la base de datos
        artist_info = existing_artists.get(artist_name.lower())
        artist_id = artist_info['id'] if artist_info else None
        
        if artist_id:
            if progress_callback is None:
                print(f"Artista encontrado en la base de datos: ID {artist_id}")
            
            # Si el origen no es 'online', actualizar información
            if artist_info.get('origen') != 'online':
                if progress_callback is None:
                    print(f"Artista con origen '{artist_info.get('origen')}', actualizando información")
                artist_mbid = track['artist'].get('mbid', '')
                last_artist_info = get_artist_info(artist_name, artist_mbid, lastfm_api_key)
                if last_artist_info:
                    update_artist_in_db(conn, artist_id, last_artist_info)
        
        album_id = None
        song_id = None
        
        # Si el artista no existe, comprobar si ya lo hemos procesado o necesitamos añadirlo
        if not artist_id and artist_name.lower() in new_artists:
            artist_id = new_artists[artist_name.lower()]
            if progress_callback is None:
                print(f"Artista encontrado en nuevos artistas procesados: ID {artist_id}")
        elif not artist_id:
            if progress_callback is None:
                print(f"Intentando obtener información para nuevo artista: {artist_name}")
            new_artists_attempts += 1
            # Obtener información del artista desde Last.fm
            artist_mbid = track['artist'].get('mbid', '')
            artist_info = get_artist_info(artist_name, artist_mbid, lastfm_api_key)
            
            if artist_info:
                if progress_callback is None:
                    print(f"Información de artista obtenida correctamente, intentando añadir a la base de datos")
                artist_id = add_artist_to_db(conn, artist_info, interactive)
                if artist_id:
                    if progress_callback is None:
                        print(f"Artista añadido correctamente: ID {artist_id}")
                    new_artists[artist_name.lower()] = artist_id
                    if existing_artists is not None:  # Importante: Verificar que no sea None
                        existing_artists[artist_name.lower()] = {'id': artist_id, 'origen': 'online'}
                    new_artists_success += 1
                else:
                    if progress_callback is None:
                        print(f"Error al añadir el artista a la base de datos")
                    errors['db_errors'] += 1
            else:
                if progress_callback is None:
                    print(f"No se pudo obtener información para el artista {artist_name}")
                errors['artist_not_found'] += 1
        
        # Si hay un álbum y artista, buscar o añadir el álbum
        if album_name and artist_id:
            album_key = (album_name.lower(), artist_name.lower())
            
            # Buscar en álbumes existentes
            album_info = existing_albums.get(album_key)
            if album_info:
                album_id = album_info['id']
                if progress_callback is None:
                    print(f"Álbum encontrado en la base de datos: ID {album_id}")
                
                # Si el origen no es 'online', actualizar información
                if album_info.get('origen') != 'online':
                    if progress_callback is None:
                        print(f"Álbum con origen '{album_info.get('origen')}', actualizando información")
                    album_mbid = track['album'].get('mbid', '')
                    last_album_info = get_album_info(album_name, artist_name, album_mbid, lastfm_api_key)
                    if last_album_info:
                        update_album_in_db(conn, album_id, last_album_info)
                
            elif album_key in new_albums:
                album_id = new_albums[album_key]
                if progress_callback is None:
                    print(f"Álbum encontrado en nuevos álbumes procesados: ID {album_id}")
            else:
                if progress_callback is None:
                    print(f"Intentando obtener información para nuevo álbum: {album_name}")
                new_albums_attempts += 1
                # Obtener información del álbum desde Last.fm
                album_mbid = track['album'].get('mbid', '')
                album_info = get_album_info(album_name, artist_name, album_mbid, lastfm_api_key)
                
                if album_info:
                    if progress_callback is None:
                        print(f"Información de álbum obtenida correctamente, intentando añadir a la base de datos")
                    album_id = add_album_to_db(conn, album_info, artist_id, interactive)
                    if album_id:
                        if progress_callback is None:
                            print(f"Álbum añadido correctamente: ID {album_id}")
                        new_albums[album_key] = album_id
                        if existing_albums is not None:  # Importante: Verificar que no sea None
                            existing_albums[album_key] = {'id': album_id, 'artist_id': artist_id, 'origen': 'online'}
                        new_albums_success += 1
                    else:
                        if progress_callback is None:
                            print(f"Error al añadir el álbum a la base de datos")
                        errors['db_errors'] += 1
                else:
                    if progress_callback is None:
                        print(f"No se pudo obtener información para el álbum {album_name}")
                    errors['album_not_found'] += 1
        
        # Buscar o añadir la canción
        song_key = (track_name.lower(), artist_name.lower(), album_name.lower() if album_name else None)
        
        song_info = existing_songs.get(song_key)
        if song_info:
            song_id = song_info['id']
            if progress_callback is None:
                print(f"Canción encontrada en la base de datos: ID {song_id}")
            
            # Si el origen no es 'online', actualizar información
            if song_info.get('origen') != 'online':
                if progress_callback is None:
                    print(f"Canción con origen '{song_info.get('origen')}', actualizando información")
                track_mbid = track.get('mbid', '')
                last_track_info = get_track_info(track_name, artist_name, track_mbid, lastfm_api_key)
                if last_track_info:
                    update_song_in_db(conn, song_id, last_track_info)
            
        elif song_key in new_songs:
            song_id = new_songs[song_key]
            if progress_callback is None:
                print(f"Canción encontrada en nuevas canciones procesadas: ID {song_id}")
        elif artist_id:  # Solo añadir canciones si tenemos el artista
            if progress_callback is None:
                print(f"Intentando obtener información para nueva canción: {track_name}")
            new_songs_attempts += 1
            track_mbid = track.get('mbid', '')
            track_info = get_track_info(track_name, artist_name, track_mbid, lastfm_api_key)
            
            if track_info:
                if progress_callback is None:
                    print(f"Información de canción obtenida correctamente, intentando añadir a la base de datos")
                song_id = add_song_to_db(conn, track_info, album_id, artist_id, interactive)
                if song_id:
                    if progress_callback is None:
                        print(f"Canción añadida correctamente: ID {song_id}")
                    new_songs[song_key] = song_id
                    if existing_songs is not None:  # Importante: Verificar que no sea None
                        existing_songs[song_key] = {'id': song_id, 'origen': 'online'}
                    new_songs_success += 1
                else:
                    if progress_callback is None:
                        print(f"Error al añadir la canción a la base de datos")
                    errors['db_errors'] += 1
            else:
                if progress_callback is None:
                    print(f"No se pudo obtener información para la canción {track_name}")
                errors['song_not_found'] += 1
        
        try:
            # Preparar el scrobble para inserción por lotes
            scrobbles_batch.append({
                'track_name': track_name,
                'album_name': album_name,
                'artist_name': artist_name,
                'timestamp': timestamp,
                'scrobble_date': scrobble_date,
                'lastfm_url': lastfm_url,
                'song_id': song_id,
                'album_id': album_id,
                'artist_id': artist_id
            })
            
            # Si alcanzamos el tamaño del lote, insertar
            if len(scrobbles_batch) >= batch_size:
                insert_scrobbles_batch(conn, scrobbles_batch)
                
                # Contar resultados
                for scrobble in scrobbles_batch:
                    processed_count += 1
                    if scrobble['song_id']:
                        linked_count += 1
                    else:
                        unlinked_count += 1
                        
                scrobbles_batch = []
            
        except Exception as e:
            if progress_callback is None:
                print(f"Error al preparar scrobble para inserción: {e}")
            errors['db_errors'] += 1
    
    # Insertar los scrobbles restantes del lote
    if scrobbles_batch:
        try:
            insert_scrobbles_batch(conn, scrobbles_batch)
            
            # Contar resultados
            for scrobble in scrobbles_batch:
                processed_count += 1
                if scrobble['song_id']:
                    linked_count += 1
                else:
                    unlinked_count += 1
                    
        except Exception as e:
            if progress_callback is None:
                print(f"Error al insertar lote final de scrobbles: {e}")
            errors['db_errors'] += 1
    
    conn.commit()
    
    # Resumen detallado
    if progress_callback is None:
        print("\n=== RESUMEN DE PROCESAMIENTO ===")
        print(f"Scrobbles procesados: {processed_count}")
        print(f"Scrobbles enlazados: {linked_count}")
        print(f"Scrobbles no enlazados: {unlinked_count}")
        print(f"Intentos de nuevos artistas: {new_artists_attempts}")
        print(f"Nuevos artistas añadidos: {new_artists_success}")
        print(f"Intentos de nuevos álbumes: {new_albums_attempts}")
        print(f"Nuevos álbumes añadidos: {new_albums_success}")
        print(f"Intentos de nuevas canciones: {new_songs_attempts}")
        print(f"Nuevas canciones añadidas: {new_songs_success}")
        print("\nErrores encontrados:")
        print(f"Artistas no encontrados: {errors['artist_not_found']}")
        print(f"Álbumes no encontrados: {errors['album_not_found']}")
        print(f"Canciones no encontradas: {errors['song_not_found']}")
        print(f"Errores de API: {errors['api_errors']}")
        print(f"Errores de base de datos: {errors['db_errors']}")
    
    # Si hay callback, enviar resumen al final
    if progress_callback:
        summary = {
            'processed': processed_count,
            'linked': linked_count,
            'unlinked': unlinked_count,
            'new_artists': new_artists_success,
            'new_albums': new_albums_success,
            'new_songs': new_songs_success,
            'errors': errors
        }
        progress_callback("Procesamiento completo", 100, summary)
    
    return processed_count, linked_count, unlinked_count, newest_timestamp


def insert_scrobbles_batch(conn, scrobbles, batch_size=100):
    """Inserta múltiples scrobbles en la base de datos usando operaciones por lotes"""
    cursor = conn.cursor()
    
    # Preparar los datos para inserción
    values = []
    for scrobble in scrobbles:
        values.append((
            scrobble['track_name'],
            scrobble['album_name'],
            scrobble['artist_name'],
            scrobble['timestamp'],
            scrobble['scrobble_date'],
            scrobble['lastfm_url'],
            scrobble['song_id'],
            scrobble['album_id'],
            scrobble['artist_id']
        ))
    
    # Insertar en lotes
    for i in range(0, len(values), batch_size):
        batch = values[i:i+batch_size]
        
        # Construir la consulta SQL con múltiples valores
        placeholders = []
        flat_values = []
        
        for item in batch:
            placeholders.append('(?, ?, ?, ?, ?, ?, ?, ?, ?)')
            flat_values.extend(item)
        
        sql = f"""
            INSERT INTO scrobbles 
            (track_name, album_name, artist_name, timestamp, scrobble_date, lastfm_url, song_id, album_id, artist_id)
            VALUES {', '.join(placeholders)}
        """
        
        cursor.execute(sql, flat_values)
    
    conn.commit()


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
    def __init__(self, db_path, lastfm_user, lastfm_api_key, progress_callback=None):
        self.db_path = db_path
        self.lastfm_user = lastfm_user
        self.lastfm_api_key = lastfm_api_key
        self.conn = None
        self.existing_artists = {}
        self.existing_albums = {}
        self.existing_songs = {}
        self.progress_callback = progress_callback
        self._interactive_mode = False
        
    @property
    def interactive_mode(self):
        return self._interactive_mode
        
    @interactive_mode.setter
    def interactive_mode(self, value):
        self._interactive_mode = value
        global INTERACTIVE_MODE
        INTERACTIVE_MODE = value
        
    def _update_progress(self, message, percentage=None, extra_data=None):
        """Actualiza el progreso a través del callback si está disponible"""
        if self.progress_callback:
            if extra_data:
                self.progress_callback(message, percentage, extra_data)
            else:
                self.progress_callback(message, percentage)
        else:
            print(message)
    
    def connect(self):
        """Conecta a la base de datos y carga los elementos existentes"""
        if self.conn is None:
            self._update_progress("Conectando a la base de datos...", 0)
            self.conn = sqlite3.connect(self.db_path)
            setup_database(self.conn)
            self._update_progress("Cargando elementos existentes...", 5)
            self.existing_artists, self.existing_albums, self.existing_songs = get_existing_items(self.conn)
            self._update_progress(f"Cargados {len(self.existing_artists)} artistas, {len(self.existing_albums)} álbumes, {len(self.existing_songs)} canciones", 10)
        return self.conn
        
    def disconnect(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self._update_progress("Conexión a la base de datos cerrada", 100)
    
    def get_new_scrobbles(self, force_update=False):
        """Obtiene los nuevos scrobbles desde el último timestamp"""
        self.connect()
        from_timestamp = 0 if force_update else get_last_timestamp(self.conn)
        
        if from_timestamp > 0:
            date_str = datetime.datetime.fromtimestamp(from_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            self._update_progress(f"Obteniendo scrobbles desde {date_str}", 15)
        else:
            self._update_progress("Obteniendo todos los scrobbles (esto puede tardar)", 15)
            
        tracks = get_lastfm_scrobbles(self.lastfm_user, self.lastfm_api_key, from_timestamp, 
                                      progress_callback=self.progress_callback)
        
        self._update_progress(f"Obtenidos {len(tracks)} scrobbles", 30)
        return tracks, from_timestamp
    
    def process_scrobbles_batch(self, tracks, interactive=None, callback=None):
        """Procesa un lote de scrobbles con posible interfaz gráfica"""
        self.connect()
        
        if interactive is None:
            interactive = self.interactive_mode
            
        # Si hay pocos tracks, informar
        if len(tracks) == 0:
            self._update_progress("No hay nuevos scrobbles para procesar", 100)
            return 0, 0, 0, 0
            
        self._update_progress(f"Procesando {len(tracks)} scrobbles...", 40)
        
        # Usar el callback proporcionado o el propio del objeto
        process_callback = callback if callback else self.progress_callback
        
        # Procesar los scrobbles
        result = process_scrobbles(
            self.conn, tracks, self.existing_artists, self.existing_albums, 
            self.existing_songs, self.lastfm_api_key, interactive, process_callback
        )
        
        # Actualizar el timestamp
        processed, linked, unlinked, newest_timestamp = result
        if newest_timestamp > 0:
            save_last_timestamp(self.conn, newest_timestamp, self.lastfm_user)
            date_str = datetime.datetime.fromtimestamp(newest_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            self._update_progress(f"Guardado último timestamp: {date_str}", 95)
            
        match_percent = (linked / processed * 100) if processed > 0 else 0
        self._update_progress(f"Procesamiento completo. {processed} scrobbles procesados, {linked} enlazados ({match_percent:.1f}%)", 100)
            
        return result
    
    def update_scrobbles(self, force_update=False, interactive=None, callback=None):
        """Actualiza los scrobbles desde Last.fm y los procesa"""
        if interactive is None:
            interactive = self.interactive_mode
            
        tracks, from_timestamp = self.get_new_scrobbles(force_update)
        if tracks:
            return self.process_scrobbles_batch(tracks, interactive, callback)
        return 0, 0, 0, 0
    
    def update_database_with_online_info(self, specific_data=None):
        """Actualiza la información de artistas, álbumes y canciones existentes con datos de Last.fm
        
        Args:
            specific_data: Diccionario con claves 'artists', 'albums', 'songs' para actualizar solo ciertos elementos
        """
        self.connect()
        cursor = self.conn.cursor()
        
        total_updates = 0
        successful_updates = 0
        
        # Actualizar artistas sin origen 'online'
        update_artists = specific_data is None or 'artists' in specific_data
        
        if update_artists:
            self._update_progress("Verificando artistas para actualizar...", 5)
            cursor.execute("SELECT id, name FROM artists WHERE origen IS NULL OR origen != 'online'")
            artists_to_update = cursor.fetchall()
            
            self._update_progress(f"Encontrados {len(artists_to_update)} artistas para actualizar", 10)
            
            for i, (artist_id, artist_name) in enumerate(artists_to_update):
                progress = 10 + (i / len(artists_to_update) * 30) if artists_to_update else 40
                self._update_progress(f"Actualizando artista {i+1}/{len(artists_to_update)}: {artist_name}", progress)
                
                total_updates += 1
                artist_info = get_artist_info(artist_name, None, self.lastfm_api_key)
                if artist_info:
                    if update_artist_in_db(self.conn, artist_id, artist_info):
                        successful_updates += 1
        
        # Actualizar álbumes sin origen 'online'
        update_albums = specific_data is None or 'albums' in specific_data
        
        if update_albums:
            self._update_progress("Verificando álbumes para actualizar...", 40)
            cursor.execute("""
                SELECT a.id, a.name, ar.name FROM albums a 
                JOIN artists ar ON a.artist_id = ar.id
                WHERE a.origen IS NULL OR a.origen != 'online'
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
        
        # Actualizar canciones sin origen 'online'
        update_songs = specific_data is None or 'songs' in specific_data
        
        if update_songs:
            self._update_progress("Verificando canciones para actualizar...", 75)
            cursor.execute("SELECT id, title, artist FROM songs WHERE origen IS NULL OR origen != 'online'")
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
        return successful_updates, total_updates
    
    def verify_database_integrity(self):
        """Verifica la integridad de la base de datos y corrige problemas comunes"""
        self.connect()
        cursor = self.conn.cursor()
        corrections = 0
        
        self._update_progress("Verificando integridad de la base de datos...", 5)
        
        # Verificar scrobbles sin artista_id pero con artista existente
        self._update_progress("Verificando enlaces de artistas en scrobbles...", 10)
        cursor.execute("""
            SELECT s.id, s.artist_name, a.id 
            FROM scrobbles s
            JOIN artists a ON LOWER(s.artist_name) = LOWER(a.name)
            WHERE s.artist_id IS NULL
        """)
        
        artist_links = cursor.fetchall()
        if artist_links:
            self._update_progress(f"Corrigiendo {len(artist_links)} enlaces de artistas", 20)
            for scrobble_id, artist_name, artist_id in artist_links:
                cursor.execute("UPDATE scrobbles SET artist_id = ? WHERE id = ?", (artist_id, scrobble_id))
                corrections += 1
        
        # Verificar scrobbles sin album_id pero con álbum existente
        self._update_progress("Verificando enlaces de álbumes en scrobbles...", 40)
        cursor.execute("""
            SELECT s.id, s.album_name, s.artist_name, a.id 
            FROM scrobbles s
            JOIN albums a ON LOWER(s.album_name) = LOWER(a.name)
            JOIN artists ar ON a.artist_id = ar.id AND LOWER(s.artist_name) = LOWER(ar.name)
            WHERE s.album_id IS NULL AND s.album_name IS NOT NULL AND s.album_name != ''
        """)
        
        album_links = cursor.fetchall()
        if album_links:
            self._update_progress(f"Corrigiendo {len(album_links)} enlaces de álbumes", 60)
            for scrobble_id, album_name, artist_name, album_id in album_links:
                cursor.execute("UPDATE scrobbles SET album_id = ? WHERE id = ?", (album_id, scrobble_id))
                corrections += 1
        
        # Verificar scrobbles sin song_id pero con canción existente
        self._update_progress("Verificando enlaces de canciones en scrobbles...", 80)
        cursor.execute("""
            SELECT s.id, s.track_name, s.artist_name, sg.id 
            FROM scrobbles s
            JOIN songs sg ON LOWER(s.track_name) = LOWER(sg.title) AND LOWER(s.artist_name) = LOWER(sg.artist)
            WHERE s.song_id IS NULL
        """)
        
        song_links = cursor.fetchall()
        if song_links:
            self._update_progress(f"Corrigiendo {len(song_links)} enlaces de canciones", 90)
            for scrobble_id, track_name, artist_name, song_id in song_links:
                cursor.execute("UPDATE scrobbles SET song_id = ? WHERE id = ?", (song_id, scrobble_id))
                corrections += 1
        
        self.conn.commit()
        self._update_progress(f"Verificación completada. Se realizaron {corrections} correcciones", 100)
        return corrections
        
    def get_statistics(self):
        """Obtiene estadísticas generales de scrobbles"""
        self.connect()
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM scrobbles")
        total_scrobbles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM scrobbles WHERE song_id IS NOT NULL")
        matched_scrobbles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM artists")
        total_artists = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM albums")
        total_albums = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM songs")
        total_songs = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM scrobbles")
        min_timestamp, max_timestamp = cursor.fetchone()
        
        match_percentage = (matched_scrobbles / total_scrobbles * 100) if total_scrobbles > 0 else 0
        
        # Calcular periodo de tiempo
        if min_timestamp and max_timestamp:
            min_date = datetime.datetime.fromtimestamp(min_timestamp)
            max_date = datetime.datetime.fromtimestamp(max_timestamp)
            
            # Calcula la diferencia en días
            date_diff = (max_date - min_date).days
            years = date_diff // 365
            months = (date_diff % 365) // 30
            days = (date_diff % 365) % 30
            
            time_period = {
                'start_date': min_date.strftime('%Y-%m-%d'),
                'end_date': max_date.strftime('%Y-%m-%d'),
                'days': date_diff,
                'years': years,
                'months': months,
                'days_remainder': days
            }
        else:
            time_period = {
                'start_date': None,
                'end_date': None,
                'days': 0,
                'years': 0,
                'months': 0,
                'days_remainder': 0
            }
        
        # Estadísticas de scrobbles por periodo
        scrobbles_per_day = total_scrobbles / time_period['days'] if time_period['days'] > 0 else 0
        
        # Top artistas
        cursor.execute("""
            SELECT artist_name, COUNT(*) as count
            FROM scrobbles
            GROUP BY artist_name
            ORDER BY count DESC
            LIMIT 5
        """)
        top_artists = cursor.fetchall()
        
        # Top álbumes
        cursor.execute("""
            SELECT album_name, artist_name, COUNT(*) as count
            FROM scrobbles
            WHERE album_name IS NOT NULL AND album_name != ''
            GROUP BY album_name, artist_name
            ORDER BY count DESC
            LIMIT 5
        """)
        top_albums = cursor.fetchall()
        
        # Top canciones
        cursor.execute("""
            SELECT track_name, artist_name, COUNT(*) as count
            FROM scrobbles
            GROUP BY track_name, artist_name
            ORDER BY count DESC
            LIMIT 5
        """)
        top_songs = cursor.fetchall()
        
        stats = {
            'total_scrobbles': total_scrobbles,
            'matched_scrobbles': matched_scrobbles,
            'match_percentage': match_percentage,
            'total_artists': total_artists,
            'total_albums': total_albums,
            'total_songs': total_songs,
            'time_period': time_period,
            'scrobbles_per_day': scrobbles_per_day,
            'top_artists': top_artists,
            'top_albums': top_albums,
            'top_songs': top_songs
        }
        
        return stats

    def get_artist_info_by_name(self, artist_name):
        """Obtiene información detallada de un artista por su nombre"""
        self.connect()
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id, name, mbid, tags, bio, lastfm_url, origen
            FROM artists
            WHERE LOWER(name) = LOWER(?)
        """, (artist_name,))
        
        result = cursor.fetchone()
        if not result:
            # Si no existe, intentar obtenerlo de Last.fm
            artist_info = get_artist_info(artist_name, None, self.lastfm_api_key)
            if artist_info:
                return {
                    'id': None,
                    'name': artist_info.get('name', ''),
                    'mbid': artist_info.get('mbid', ''),
                    'tags': ','.join([tag['name'] for tag in artist_info.get('tags', {}).get('tag', [])]) if 'tags' in artist_info and 'tag' in artist_info['tags'] else '',
                    'bio': artist_info.get('bio', {}).get('content', '') if 'bio' in artist_info else '',
                    'lastfm_url': artist_info.get('url', ''),
                    'origen': 'online (no guardado)'
                }
            return None
        
        return {
            'id': result[0],
            'name': result[1],
            'mbid': result[2],
            'tags': result[3],
            'bio': result[4],
            'lastfm_url': result[5],
            'origen': result[6]
        }

    def get_album_info_by_name(self, album_name, artist_name):
        """Obtiene información detallada de un álbum por su nombre y artista"""
        self.connect()
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT a.id, a.name, a.year, a.lastfm_url, a.mbid, a.total_tracks, a.origen, a.artist_id, ar.name
            FROM albums a
            JOIN artists ar ON a.artist_id = ar.id
            WHERE LOWER(a.name) = LOWER(?) AND LOWER(ar.name) = LOWER(?)
        """, (album_name, artist_name))
        
        result = cursor.fetchone()
        if not result:
            # Si no existe, intentar obtenerlo de Last.fm
            album_info = get_album_info(album_name, artist_name, None, self.lastfm_api_key)
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
                
                # Número de pistas
                total_tracks = 0
                if 'tracks' in album_info and 'track' in album_info['tracks']:
                    tracks = album_info['tracks']['track']
                    if isinstance(tracks, list):
                        total_tracks = len(tracks)
                    else:
                        total_tracks = 1
                        
                return {
                    'id': None,
                    'name': album_info.get('name', ''),
                    'year': year,
                    'lastfm_url': album_info.get('url', ''),
                    'mbid': album_info.get('mbid', ''),
                    'total_tracks': total_tracks,
                    'origen': 'online (no guardado)',
                    'artist_id': None,
                    'artist_name': artist_name
                }
            return None
        
        return {
            'id': result[0],
            'name': result[1],
            'year': result[2],
            'lastfm_url': result[3],
            'mbid': result[4],
            'total_tracks': result[5],
            'origen': result[6],
            'artist_id': result[7],
            'artist_name': result[8]
        }

    def get_song_info_by_name(self, track_name, artist_name):
        """Obtiene información detallada de una canción por su nombre y artista"""
        self.connect()
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id, title, mbid, duration, album, album_artist, date, genre, artist, origen
            FROM songs
            WHERE LOWER(title) = LOWER(?) AND LOWER(artist) = LOWER(?)
        """, (track_name, artist_name))
        
        result = cursor.fetchone()
        if not result:
            # Si no existe, intentar obtenerlo de Last.fm
            track_info = get_track_info(track_name, artist_name, None, self.lastfm_api_key)
            if track_info:
                # Obtener duración
                duration = None
                if 'duration' in track_info:
                    try:
                        duration = int(track_info['duration']) // 1000  # Convertir de ms a segundos
                    except (ValueError, TypeError):
                        pass
                
                # Géneros (tags)
                genre = ''
                if 'toptags' in track_info and 'tag' in track_info['toptags']:
                    tags = track_info['toptags']['tag']
                    if isinstance(tags, list) and tags:
                        genre = tags[0]['name']
                    elif isinstance(tags, dict):
                        genre = tags.get('name', '')
                        
                return {
                    'id': None,
                    'title': track_info.get('name', ''),
                    'mbid': track_info.get('mbid', ''),
                    'duration': duration,
                    'album': track_info.get('album', {}).get('title', '') if 'album' in track_info else '',
                    'album_artist': artist_name,
                    'date': None,
                    'genre': genre,
                    'artist': artist_name,
                    'origen': 'online (no guardado)'
                }
            return None
        
        return {
            'id': result[0],
            'title': result[1],
            'mbid': result[2],
            'duration': result[3],
            'album': result[4],
            'album_artist': result[5],
            'date': result[6],
            'genre': result[7],
            'artist': result[8],
            'origen': result[9]
        }

    def get_top_artists(self, limit=10, period=None):
        """Obtiene los artistas más escuchados según los scrobbles
        
        Args:
            limit: Número máximo de resultados
            period: Periodo de tiempo en días o None para todo el tiempo
        """
        self.connect()
        cursor = self.conn.cursor()
        
        if period:
            # Calcular timestamp para filtrar por periodo
            from_timestamp = int(time.time()) - (period * 86400)
            
            cursor.execute("""
                SELECT artist_name, COUNT(*) as count
                FROM scrobbles
                WHERE timestamp >= ?
                GROUP BY artist_name
                ORDER BY count DESC
                LIMIT ?
            """, (from_timestamp, limit))
        else:
            cursor.execute("""
                SELECT artist_name, COUNT(*) as count
                FROM scrobbles
                GROUP BY artist_name
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))
        
        return cursor.fetchall()

    def get_top_albums(self, limit=10, period=None):
        """Obtiene los álbumes más escuchados según los scrobbles
        
        Args:
            limit: Número máximo de resultados
            period: Periodo de tiempo en días o None para todo el tiempo
        """
        self.connect()
        cursor = self.conn.cursor()
        
        if period:
            # Calcular timestamp para filtrar por periodo
            from_timestamp = int(time.time()) - (period * 86400)
            
            cursor.execute("""
                SELECT album_name, artist_name, COUNT(*) as count
                FROM scrobbles
                WHERE album_name IS NOT NULL AND album_name != '' AND timestamp >= ?
                GROUP BY album_name, artist_name
                ORDER BY count DESC
                LIMIT ?
            """, (from_timestamp, limit))
        else:
            cursor.execute("""
                SELECT album_name, artist_name, COUNT(*) as count
                FROM scrobbles
                WHERE album_name IS NOT NULL AND album_name != ''
                GROUP BY album_name, artist_name
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))
        
        return cursor.fetchall()

    def get_top_songs(self, limit=10, period=None):
        """Obtiene las canciones más escuchadas según los scrobbles
        
        Args:
            limit: Número máximo de resultados
            period: Periodo de tiempo en días o None para todo el tiempo
        """
        self.connect()
        cursor = self.conn.cursor()
        
        if period:
            # Calcular timestamp para filtrar por periodo
            from_timestamp = int(time.time()) - (period * 86400)
            
            cursor.execute("""
                SELECT track_name, artist_name, COUNT(*) as count
                FROM scrobbles
                WHERE timestamp >= ?
                GROUP BY track_name, artist_name
                ORDER BY count DESC
                LIMIT ?
            """, (from_timestamp, limit))
        else:
            cursor.execute("""
                SELECT track_name, artist_name, COUNT(*) as count
                FROM scrobbles
                GROUP BY track_name, artist_name
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))
        
        return cursor.fetchall()

    def get_recent_scrobbles(self, limit=20, artist_filter=None, album_filter=None):
        """Obtiene los scrobbles más recientes
        
        Args:
            limit: Número máximo de resultados
            artist_filter: Filtrar por artista específico
            album_filter: Filtrar por álbum específico
        """
        self.connect()
        cursor = self.conn.cursor()
        
        query = """
            SELECT track_name, album_name, artist_name, scrobble_date, lastfm_url
            FROM scrobbles
        """
        
        conditions = []
        params = []
        
        if artist_filter:
            conditions.append("LOWER(artist_name) = LOWER(?)")
            params.append(artist_filter)
        
        if album_filter:
            conditions.append("LOWER(album_name) = LOWER(?)")
            params.append(album_filter)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        return cursor.fetchall()

    def search_scrobbles(self, query, limit=50):
        """Busca scrobbles por texto en artista, álbum o canción
        
        Args:
            query: Texto a buscar
            limit: Número máximo de resultados
        """
        self.connect()
        cursor = self.conn.cursor()
        
        search_term = f"%{query}%"
        
        cursor.execute("""
            SELECT track_name, album_name, artist_name, scrobble_date, lastfm_url
            FROM scrobbles
            WHERE 
                LOWER(track_name) LIKE LOWER(?) OR 
                LOWER(album_name) LIKE LOWER(?) OR 
                LOWER(artist_name) LIKE LOWER(?)
            ORDER BY timestamp DESC
            LIMIT ?
        """, (search_term, search_term, search_term, limit))
        
        return cursor.fetchall()

    def get_listening_history(self, interval='daily', limit=30):
        """Obtiene la historia de escucha en intervalos
        
        Args:
            interval: 'daily', 'weekly', 'monthly' o 'yearly'
            limit: Número máximo de intervalos a devolver
        """
        self.connect()
        cursor = self.conn.cursor()
        
        if interval == 'daily':
            date_format = '%Y-%m-%d'
            interval_sql = "strftime('%Y-%m-%d', datetime(timestamp, 'unixepoch'))"
        elif interval == 'weekly':
            date_format = '%Y-%W'
            interval_sql = "strftime('%Y-%W', datetime(timestamp, 'unixepoch'))"
        elif interval == 'monthly':
            date_format = '%Y-%m'
            interval_sql = "strftime('%Y-%m', datetime(timestamp, 'unixepoch'))"
        elif interval == 'yearly':
            date_format = '%Y'
            interval_sql = "strftime('%Y', datetime(timestamp, 'unixepoch'))"
        else:
            # Por defecto, daily
            date_format = '%Y-%m-%d'
            interval_sql = "strftime('%Y-%m-%d', datetime(timestamp, 'unixepoch'))"
        
        cursor.execute(f"""
            SELECT {interval_sql} as period, COUNT(*) as count
            FROM scrobbles
            GROUP BY period
            ORDER BY period DESC
            LIMIT ?
        """, (limit,))
        
        return cursor.fetchall()

    def get_scrobbles_by_period(self, start_date=None, end_date=None, limit=1000):
        """Obtiene scrobbles en un rango de fechas
        
        Args:
            start_date: Fecha inicial (YYYY-MM-DD) o None para sin límite inferior
            end_date: Fecha final (YYYY-MM-DD) o None para sin límite superior
            limit: Número máximo de resultados
        """
        self.connect()
        cursor = self.conn.cursor()
        
        query = """
            SELECT track_name, album_name, artist_name, scrobble_date, lastfm_url
            FROM scrobbles
        """
        
        conditions = []
        params = []
        
        if start_date:
            # Convertir fecha a timestamp Unix
            try:
                start_timestamp = int(datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp())
                conditions.append("timestamp >= ?")
                params.append(start_timestamp)
            except ValueError:
                pass
        
        if end_date:
            # Convertir fecha a timestamp Unix para el final del día
            try:
                end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
                end_timestamp = int(end_date_obj.timestamp())
                conditions.append("timestamp <= ?")
                params.append(end_timestamp)
            except ValueError:
                pass
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        return cursor.fetchall()

    def export_scrobbles_to_json(self, file_path, limit=None, include_linked_info=False):
        """Exporta scrobbles a un archivo JSON
        
        Args:
            file_path: Ruta del archivo a guardar
            limit: Número máximo de scrobbles a exportar o None para todos
            include_linked_info: Incluir información detallada de artistas, álbumes y canciones
        """
        self.connect()
        cursor = self.conn.cursor()
        
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        cursor.execute(f"""
            SELECT id, track_name, album_name, artist_name, timestamp, scrobble_date, lastfm_url,
                    song_id, album_id, artist_id
            FROM scrobbles
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
            
            # Opcionalmente añadir información detallada
            if include_linked_info:
                if scrobble['artist_id']:
                    cursor.execute("SELECT name, mbid, tags, lastfm_url FROM artists WHERE id = ?", (scrobble['artist_id'],))
                    artist_info = cursor.fetchone()
                    if artist_info:
                        scrobble['artist_info'] = {
                            'name': artist_info[0],
                            'mbid': artist_info[1],
                            'tags': artist_info[2],
                            'lastfm_url': artist_info[3]
                        }
                
                if scrobble['album_id']:
                    cursor.execute("SELECT name, year, lastfm_url, mbid, total_tracks FROM albums WHERE id = ?", (scrobble['album_id'],))
                    album_info = cursor.fetchone()
                    if album_info:
                        scrobble['album_info'] = {
                            'name': album_info[0],
                            'year': album_info[1],
                            'lastfm_url': album_info[2],
                            'mbid': album_info[3],
                            'total_tracks': album_info[4]
                        }
                
                if scrobble['song_id']:
                    cursor.execute("SELECT title, mbid, duration, genre FROM songs WHERE id = ?", (scrobble['song_id'],))
                    song_info = cursor.fetchone()
                    if song_info:
                        scrobble['song_info'] = {
                            'title': song_info[0],
                            'mbid': song_info[1],
                            'duration': song_info[2],
                            'genre': song_info[3]
                        }
            
            scrobbles.append(scrobble)
        
        # Guardar a archivo JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'scrobbles': scrobbles}, f, indent=2, ensure_ascii=False)
        
        return len(scrobbles)

def main(config=None):
    # Cargar configuración
    parser = argparse.ArgumentParser(description='enlaces_artista_album')
    parser.add_argument('--config', help='Archivo de configuración')
    parser.add_argument('--lastfm_user', type=str, help='Usuario de Last.fm')
    parser.add_argument('--lastfm-api-key', type=str, help='API key de Last.fm')
    parser.add_argument('--db-path', type=str, help='Ruta al archivo de base de datos SQLite')
    parser.add_argument('--force-update', action='store_true', help='Forzar actualización completa')
    parser.add_argument('--verify-db', action='store_true', help='Verificar y corregir integridad de la base de datos')
    parser.add_argument('--update-metadata', action='store_true', help='Actualizar metadatos desde Last.fm')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar todos los scrobbles en formato JSON (opcional)')
    parser.add_argument('--interactive', action='store_true', help='Modo interactivo para añadir nuevos elementos')
    parser.add_argument('--export-json', type=str, help='Exportar scrobbles a archivo JSON')
    parser.add_argument('--export-limit', type=int, help='Límite de scrobbles a exportar')
    parser.add_argument('--include-details', action='store_true', help='Incluir detalles en exportación')
            
    args = parser.parse_args()
    
    if args.config:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
            
        # Combinar configuraciones
        config = {}
        config.update(config_data.get("common", {}))
        config.update(config_data.get("scrobbles_lastfm", {}))
    elif config is None:
        config = {}
    
    # Establecer variable global de modo interactivo
    global INTERACTIVE_MODE
    INTERACTIVE_MODE = args.interactive or config.get('interactive', False)
    
    db_path = args.db_path or config.get('db_path')
    if not db_path: 
        print("Añade db_path al json o usa --db-path")
        return 0, 0, 0, 0

    lastfm_user = args.lastfm_user or config.get('lastfm_user')
    if not lastfm_user: 
        print("Añade lastfm_user al json o usa --lastfm-user especificando tu usuario en lastfm")
        return 0, 0, 0, 0

    lastfm_api_key = args.lastfm_api_key or config.get('lastfm_api_key')
    if not lastfm_api_key:
        print("Añade lastfm_api_key al json o usa --lastfm-api-key especificando tu api key en lastfm")
        return 0, 0, 0, 0

    output_json = args.output_json or config.get("output_json", ".content/cache/scrobbles_lastfm.json")
    force_update = args.force_update or config.get('force_update', False)
    verify_db = args.verify_db or config.get('verify_db', False)
    update_metadata = args.update_metadata or config.get('update_metadata', False)
    interactive = args.interactive or config.get('interactive', False)

    # Verificar API key
    if not check_api_key(lastfm_api_key):
        print("ERROR: La API key de Last.fm no es válida o hay problemas con el servicio.")
        print("Revisa tu API key y asegúrate de que el servicio de Last.fm esté disponible.")
        return 0, 0, 0, 0

    # Crear la instancia del scrobbler
    scrobbler = LastFMScrobbler(db_path, lastfm_user, lastfm_api_key)
    scrobbler.interactive_mode = INTERACTIVE_MODE

    # Realizar las operaciones solicitadas
    if args.export_json:
        print(f"Exportando scrobbles a {args.export_json}...")
        export_limit = args.export_limit if args.export_limit else None
        count = scrobbler.export_scrobbles_to_json(
            args.export_json, 
            limit=export_limit,
            include_linked_info=args.include_details
        )
        print(f"Exportados {count} scrobbles a {args.export_json}")
        return 0, 0, 0, 0

    if verify_db:
        print("Verificando integridad de la base de datos...")
        corrections = scrobbler.verify_database_integrity()
        print(f"Verificación completada: {corrections} correcciones realizadas")

    if update_metadata:
        print("Actualizando metadatos desde Last.fm...")
        success, total = scrobbler.update_database_with_online_info()
        print(f"Actualización de metadatos completada: {success} de {total} elementos actualizados")

    # Actualizar scrobbles
    processed = 0
    linked = 0
    unlinked = 0
    newest_timestamp = 0

    if force_update:
        print("Modo force-update activado: obteniendo todos los scrobbles")
        
    try:
        # Esta es la línea clave - usar la clase LastFMScrobbler
        processed, linked, unlinked, newest_timestamp = scrobbler.update_scrobbles(force_update, interactive)
        
        # Si se solicitó guardar a JSON
        if output_json and processed > 0:
            # Asegurarse de que el directorio existe
            output_dir = os.path.dirname(output_json)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # Guardar los últimos scrobbles obtenidos
            print(f"Guardando scrobbles en {output_json}")
            limit = 1000  # Limitar a 1000 scrobbles por defecto
            scrobbler.export_scrobbles_to_json(output_json, limit=limit)
            print(f"Guardados hasta {limit} scrobbles recientes en {output_json}")
            
    finally:
        # Mostrar estadísticas generales
        stats = scrobbler.get_statistics()
        
        print("\n=== ESTADÍSTICAS GENERALES ===")
        print(f"Total scrobbles: {stats['total_scrobbles']}")
        print(f"Scrobbles enlazados: {stats['matched_scrobbles']} ({stats['match_percentage']:.1f}%)")
        print(f"Total artistas: {stats['total_artists']}")
        print(f"Total álbumes: {stats['total_albums']}")
        print(f"Total canciones: {stats['total_songs']}")
        
        if stats['time_period']['days'] > 0:
            time_str = ""
            if stats['time_period']['years'] > 0:
                time_str += f"{stats['time_period']['years']} años, "
            if stats['time_period']['months'] > 0:
                time_str += f"{stats['time_period']['months']} meses, "
            time_str += f"{stats['time_period']['days_remainder']} días"
            
            print(f"Periodo cubierto: {time_str} ({stats['time_period']['start_date']} a {stats['time_period']['end_date']})")
            print(f"Promedio: {stats['scrobbles_per_day']:.1f} scrobbles por día")
        
        # Desconectar
        scrobbler.disconnect()
        
    return processed, linked, unlinked, newest_timestamp

if __name__ == "__main__":
    main()