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
    
    # Obtener artistas existentes
    cursor.execute("SELECT id, name FROM artists")
    artists_rows = cursor.fetchall()
    artists = {row[1].lower(): row[0] for row in artists_rows}
    
    # Obtener álbumes existentes
    cursor.execute("""
        SELECT a.id, a.name, ar.name, a.artist_id
        FROM albums a 
        JOIN artists ar ON a.artist_id = ar.id
    """)
    albums_rows = cursor.fetchall()
    albums = {(row[1].lower(), row[2].lower()): (row[0], row[3]) for row in albums_rows}
    
    # Obtener canciones existentes
    cursor.execute("""
        SELECT s.id, s.title, s.artist, s.album
        FROM songs s
    """)
    songs_rows = cursor.fetchall()
    songs = {(row[1].lower(), row[2].lower(), row[3].lower() if row[3] else None): row[0] 
             for row in songs_rows}
    
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
        print(f"\nArtista: {artist_name}")
        print(f"MBID: {mbid}")
        print(f"URL: {url}")
        print(f"Tags: {tags_str}")
        print(f"Bio: {bio[:100]}..." if len(bio) > 100 else f"Bio: {bio}")
        
        respuesta = input("¿Añadir este artista a la base de datos? (s/n): ").lower()
        if respuesta != 's':
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
        print(f"\nÁlbum: {album_name}")
        print(f"MBID: {mbid}")
        print(f"URL: {url}")
        print(f"Año: {year}")
        print(f"Total pistas: {total_tracks}")
        
        respuesta = input("¿Añadir este álbum a la base de datos? (s/n): ").lower()
        if respuesta != 's':
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
        print(f"\nCanción: {track_name}")
        print(f"MBID: {mbid}")
        print(f"Duración: {duration} segundos")
        print(f"Álbum: {album_name}")
        print(f"Artista: {artist_name}")
        print(f"Género: {genre}")
        
        respuesta = input("¿Añadir esta canción a la base de datos? (s/n): ").lower()
        if respuesta != 's':
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

def get_lastfm_scrobbles(lastfm_username, lastfm_api_key, from_timestamp=0, limit=200):
    """Obtiene los scrobbles de Last.fm para un usuario desde un timestamp específico"""
    all_tracks = []
    page = 1
    total_pages = 1
    
    while page <= total_pages:
        params = {
            'method': 'user.getrecenttracks',
            'user': lastfm_username,
            'api_key': lastfm_api_key,
            'format': 'json',
            'limit': limit,
            'page': page,
            'from': from_timestamp
        }
        
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        if response.status_code != 200:
            print(f"Error al obtener scrobbles: {response.status_code}")
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
        
        print(f"Obtenida página {page} de {total_pages} ({len(filtered_tracks)} tracks)")
        
        page += 1
        # Pequeña pausa para no saturar la API
        time.sleep(0.25)
    
    return all_tracks

def process_scrobbles(conn, tracks, existing_artists, existing_albums, existing_songs, lastfm_api_key, interactive=False):
    """Procesa los scrobbles y actualiza la base de datos con los nuevos scrobbles"""
    cursor = conn.cursor()
    processed_count = 0
    linked_count = 0
    unlinked_count = 0
    newest_timestamp = 0
    
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
    
    for track_idx, track in enumerate(tracks):
        print(f"\nProcesando scrobble {track_idx+1}/{len(tracks)}")
        artist_name = track['artist']['#text']
        album_name = track['album']['#text'] if track['album']['#text'] else None
        track_name = track['name']
        timestamp = int(track['date']['uts'])
        scrobble_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        lastfm_url = track['url']
        
        print(f"Artista: {artist_name}, Álbum: {album_name}, Canción: {track_name}")
        
        # Actualizar el timestamp más reciente
        newest_timestamp = max(newest_timestamp, timestamp)
        
        # Verificar si el scrobble ya existe en la base de datos para evitar duplicados
        cursor.execute("SELECT id FROM scrobbles WHERE timestamp = ? AND artist_name = ? AND track_name = ?", 
                      (timestamp, artist_name, track_name))
        if cursor.fetchone():
            print(f"Scrobble duplicado, saltando")
            continue  # El scrobble ya existe, continuamos con el siguiente
        
        # Buscar IDs existentes en la base de datos
        artist_id = existing_artists.get(artist_name.lower())
        if artist_id:
            print(f"Artista encontrado en la base de datos: ID {artist_id}")
        
        album_id = None
        song_id = None
        
        # Si el artista no existe, comprobar si ya lo hemos procesado o necesitamos añadirlo
        if not artist_id and artist_name.lower() in new_artists:
            artist_id = new_artists[artist_name.lower()]
            print(f"Artista encontrado en nuevos artistas procesados: ID {artist_id}")
        elif not artist_id:
            print(f"Intentando obtener información para nuevo artista: {artist_name}")
            new_artists_attempts += 1
            # Obtener información del artista desde Last.fm
            artist_mbid = track['artist'].get('mbid', '')
            artist_info = get_artist_info(artist_name, artist_mbid, lastfm_api_key)
            
            if artist_info:
                print(f"Información de artista obtenida correctamente, intentando añadir a la base de datos")
                artist_id = add_artist_to_db(conn, artist_info, interactive)
                if artist_id:
                    print(f"Artista añadido correctamente: ID {artist_id}")
                    new_artists[artist_name.lower()] = artist_id
                    existing_artists[artist_name.lower()] = artist_id
                    new_artists_success += 1
                else:
                    print(f"Error al añadir el artista a la base de datos")
                    errors['db_errors'] += 1
            else:
                print(f"No se pudo obtener información para el artista {artist_name}")
                errors['artist_not_found'] += 1
        
        # Si hay un álbum y artista, buscar o añadir el álbum
        if album_name and artist_id:
            album_key = (album_name.lower(), artist_name.lower())
            
            # Buscar en álbumes existentes
            if album_key in existing_albums:
                album_id, _ = existing_albums.get(album_key)
                print(f"Álbum encontrado en la base de datos: ID {album_id}")
            elif album_key in new_albums:
                album_id = new_albums[album_key]
                print(f"Álbum encontrado en nuevos álbumes procesados: ID {album_id}")
            else:
                print(f"Intentando obtener información para nuevo álbum: {album_name}")
                new_albums_attempts += 1
                # Obtener información del álbum desde Last.fm
                album_mbid = track['album'].get('mbid', '')
                album_info = get_album_info(album_name, artist_name, album_mbid, lastfm_api_key)
                
                if album_info:
                    print(f"Información de álbum obtenida correctamente, intentando añadir a la base de datos")
                    album_id = add_album_to_db(conn, album_info, artist_id, interactive)
                    if album_id:
                        print(f"Álbum añadido correctamente: ID {album_id}")
                        new_albums[album_key] = album_id
                        existing_albums[album_key] = (album_id, artist_id)
                        new_albums_success += 1
                    else:
                        print(f"Error al añadir el álbum a la base de datos")
                        errors['db_errors'] += 1
                else:
                    print(f"No se pudo obtener información para el álbum {album_name}")
                    errors['album_not_found'] += 1
        
        # Buscar o añadir la canción
        song_key = (track_name.lower(), artist_name.lower(), album_name.lower() if album_name else None)
        
        if song_key in existing_songs:
            song_id = existing_songs.get(song_key)
            print(f"Canción encontrada en la base de datos: ID {song_id}")
        elif song_key in new_songs:
            song_id = new_songs[song_key]
            print(f"Canción encontrada en nuevas canciones procesadas: ID {song_id}")
        elif artist_id:  # Solo añadir canciones si tenemos el artista
            print(f"Intentando obtener información para nueva canción: {track_name}")
            new_songs_attempts += 1
            track_mbid = track.get('mbid', '')
            track_info = get_track_info(track_name, artist_name, track_mbid, lastfm_api_key)
            
            if track_info:
                print(f"Información de canción obtenida correctamente, intentando añadir a la base de datos")
                song_id = add_song_to_db(conn, track_info, album_id, artist_id, interactive)
                if song_id:
                    print(f"Canción añadida correctamente: ID {song_id}")
                    new_songs[song_key] = song_id
                    existing_songs[song_key] = song_id
                    new_songs_success += 1
                else:
                    print(f"Error al añadir la canción a la base de datos")
                    errors['db_errors'] += 1
            else:
                print(f"No se pudo obtener información para la canción {track_name}")
                errors['song_not_found'] += 1
        
        try:
            # Insertar el scrobble en la tabla
            cursor.execute("""
                INSERT INTO scrobbles 
                (track_name, album_name, artist_name, timestamp, scrobble_date, lastfm_url, song_id, album_id, artist_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (track_name, album_name, artist_name, timestamp, scrobble_date, lastfm_url, song_id, album_id, artist_id))
            
            processed_count += 1
            
            # Contabilizar si se pudo enlazar con la base de datos
            if song_id:
                linked_count += 1
                print(f"Scrobble enlazado correctamente con song_id: {song_id}")
                
                # Actualizar song_links si el song_id existe
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO song_links (song_id, lastfm_url, links_updated)
                        VALUES (?, ?, datetime('now'))
                    """, (song_id, lastfm_url))
                except sqlite3.Error as e:
                    # Es posible que la tabla song_links no exista, no es crítico
                    print(f"Nota: No se pudo actualizar song_links: {e}")
            else:
                unlinked_count += 1
                print(f"Scrobble guardado pero sin enlazar a una canción")
            
            # Actualizar información de artista si existe en la base de datos
            if artist_id and 'url' in track['artist']:
                cursor.execute("""
                    UPDATE artists 
                    SET lastfm_url = COALESCE(lastfm_url, ?)
                    WHERE id = ?
                """, (track['artist']['url'], artist_id))
                
            # Actualizar información de álbum si existe en la base de datos
            if album_id and 'url' in track['album']:
                cursor.execute("""
                    UPDATE albums
                    SET lastfm_url = COALESCE(lastfm_url, ?)
                    WHERE id = ?
                """, (track['album']['url'], album_id))
        
        except sqlite3.Error as e:
            print(f"Error al insertar scrobble en la base de datos: {e}")
            errors['db_errors'] += 1
    
    conn.commit()
    
    # Resumen detallado
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
    
    return processed_count, linked_count, unlinked_count, newest_timestamp

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
    def __init__(self, db_path, lastfm_user, lastfm_api_key):
        self.db_path = db_path
        self.lastfm_user = lastfm_user
        self.lastfm_api_key = lastfm_api_key
        self.conn = None
        self.existing_artists = {}
        self.existing_albums = {}
        self.existing_songs = {}
        
    def connect(self):
        """Conecta a la base de datos y carga los elementos existentes"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            setup_database(self.conn)
            self.existing_artists, self.existing_albums, self.existing_songs = get_existing_items(self.conn)
        return self.conn
        
    def disconnect(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_new_scrobbles(self, force_update=False):
        """Obtiene los nuevos scrobbles desde el último timestamp"""
        self.connect()
        from_timestamp = 0 if force_update else get_last_timestamp(self.conn)
        tracks = get_lastfm_scrobbles(self.lastfm_user, self.lastfm_api_key, from_timestamp)
        return tracks, from_timestamp
    
    def process_scrobbles_batch(self, tracks, interactive=False, callback=None):
        """Procesa un lote de scrobbles con posible interfaz gráfica"""
        self.connect()
        
        # Si se proporciona un callback, lo usamos para la interacción en lugar del modo interactivo estándar
        if callback:
            # Definimos reemplazos para las funciones interactivas
            def wrapped_add_artist(conn, artist_info, _):
                return callback('artist', artist_info)
                
            def wrapped_add_album(conn, album_info, artist_id, _):
                return callback('album', album_info, artist_id)
                
            def wrapped_add_song(conn, track_info, album_id, artist_id, _):
                return callback('song', track_info, album_id, artist_id)
                
            # Guardamos temporalmente las funciones originales
            original_add_artist = globals()['add_artist_to_db']
            original_add_album = globals()['add_album_to_db']
            original_add_song = globals()['add_song_to_db']
            
            # Reemplazamos con nuestras versiones
            globals()['add_artist_to_db'] = wrapped_add_artist
            globals()['add_album_to_db'] = wrapped_add_album
            globals()['add_song_to_db'] = wrapped_add_song
            
            try:
                # Procesar con las funciones modificadas
                result = process_scrobbles(
                    self.conn, tracks, self.existing_artists, self.existing_albums, 
                    self.existing_songs, self.lastfm_api_key, False
                )
            finally:
                # Restaurar las funciones originales
                globals()['add_artist_to_db'] = original_add_artist
                globals()['add_album_to_db'] = original_add_album
                globals()['add_song_to_db'] = original_add_song
        else:
            # Procesar normalmente
            result = process_scrobbles(
                self.conn, tracks, self.existing_artists, self.existing_albums, 
                self.existing_songs, self.lastfm_api_key, interactive
            )
            
        # Actualizar el timestamp
        processed, linked, unlinked, newest_timestamp = result
        if newest_timestamp > 0:
            save_last_timestamp(self.conn, newest_timestamp, self.lastfm_user)
            
        return result
    
    def update_scrobbles(self, force_update=False, interactive=False, callback=None):
        """Actualiza los scrobbles desde Last.fm y los procesa"""
        tracks, from_timestamp = self.get_new_scrobbles(force_update)
        if tracks:
            return self.process_scrobbles_batch(tracks, interactive, callback)
        return 0, 0, 0, 0
    
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
    
    match_percentage = (matched_scrobbles / total_scrobbles * 100) if total_scrobbles > 0 else 0
    
    stats = {
        'total_scrobbles': total_scrobbles,
        'matched_scrobbles': matched_scrobbles,
        'match_percentage': match_percentage,
        'total_artists': total_artists,
        'total_albums': total_albums,
        'total_songs': total_songs
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
                'tags': ','.join([tag['name'] for tag in artist_info.get('tags', {}).get('tag', [])]) if 'tags' in artist_info else '',
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

    def get_top_artists(self, limit=10):
        """Obtiene los artistas más escuchados según los scrobbles"""
        self.connect()
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT artist_name, COUNT(*) as count
            FROM scrobbles
            GROUP BY artist_name
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        return cursor.fetchall()

    def get_top_albums(self, limit=10):
        """Obtiene los álbumes más escuchados según los scrobbles"""
        self.connect()
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT album_name, artist_name, COUNT(*) as count
            FROM scrobbles
            WHERE album_name IS NOT NULL AND album_name != ''
            GROUP BY album_name, artist_name
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        return cursor.fetchall()

    def get_top_songs(self, limit=10):
        """Obtiene las canciones más escuchadas según los scrobbles"""
        self.connect()
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT track_name, artist_name, COUNT(*) as count
            FROM scrobbles
            GROUP BY track_name, artist_name
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        return cursor.fetchall()

    def get_recent_scrobbles(self, limit=20):
        """Obtiene los scrobbles más recientes"""
        self.connect()
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT track_name, album_name, artist_name, scrobble_date, lastfm_url
            FROM scrobbles
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        return cursor.fetchall()

def main(config=None):
    # Cargar configuración
    parser = argparse.ArgumentParser(description='enlaces_artista_album')
    parser.add_argument('--config', help='Archivo de configuración')
    parser.add_argument('--lastfm_user', type=str, help='Usuario de Last.fm')
    parser.add_argument('--lastfm-api-key', type=str, help='API key de Last.fm')
    parser.add_argument('--db-path', type=str, help='Ruta al archivo de base de datos SQLite')
    parser.add_argument('--force-update', action='store_true', help='Forzar actualización completa')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar todos los scrobbles en formato JSON (opcional)')
    parser.add_argument('--interactive', action='store_true', help='Modo interactivo para añadir nuevos elementos')
            
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

    output_json = args.output_json or config.get("output_json", ".content/cache/scrobbles_lastfm.json")
    force_update = args.force_update or config.get('force_update', False)
    interactive = args.interactive or config.get('interactive', False)


    # Verificar API key
    if not check_api_key(lastfm_api_key):
        print("ERROR: La API key de Last.fm no es válida o hay problemas con el servicio.")
        print("Revisa tu API key y asegúrate de que el servicio de Last.fm esté disponible.")
        return 0, 0, 0, 0



    # En la función main, antes de empezar el procesamiento normal:
    print("\n=== PRUEBA DE API DE LAST.FM ===")
    print("Realizando prueba directa de las API de Last.fm...")
    test_artist = "The Beatles"  # Un artista que seguramente existe
    test_album = "Abbey Road"
    test_track = "Come Together"

    print(f"\nPrueba de artist.getInfo para '{test_artist}'")
    test_artist_info = get_artist_info(test_artist, None, lastfm_api_key)
    print(f"Resultado: {'Éxito' if test_artist_info else 'Fallo'}")

    print(f"\nPrueba de album.getInfo para '{test_album}' de '{test_artist}'")
    test_album_info = get_album_info(test_album, test_artist, None, lastfm_api_key)
    print(f"Resultado: {'Éxito' if test_album_info else 'Fallo'}")

    print(f"\nPrueba de track.getInfo para '{test_track}' de '{test_artist}'")
    test_track_info = get_track_info(test_track, test_artist, None, lastfm_api_key)
    print(f"Resultado: {'Éxito' if test_track_info else 'Fallo'}")

    if not (test_artist_info and test_album_info and test_track_info):
        print("\nALERTA: Al menos una de las pruebas ha fallado.")
        print("Esto puede indicar problemas con la API key, conexión a Internet, o el servicio de Last.fm.")
        if not interactive:
            print("Continuando de todos modos, pero es posible que el procesamiento no funcione correctamente.")
        else:
            continuar = input("¿Deseas continuar de todos modos? (s/n): ").lower()
            if continuar != 's':
                return 0, 0, 0, 0

    print("\n=== FIN DE PRUEBA DE API ===\n")

    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    
    try:
        # Configurar la base de datos
        setup_database(conn)
        
        # Obtener elementos existentes
        existing_artists, existing_albums, existing_songs = get_existing_items(conn)
        print(f"Elementos existentes: {len(existing_artists)} artistas, {len(existing_albums)} álbumes, {len(existing_songs)} canciones")
        
        # Obtener el último timestamp procesado
        if force_update == True:
            from_timestamp = 0
            print("Obteniendo todos los scrobbles (esto puede tardar)")
        else:
            from_timestamp = get_last_timestamp(conn)
            print(f"Obteniendo scrobbles desde {datetime.datetime.fromtimestamp(from_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")

        
        # Obtener scrobbles
        tracks = get_lastfm_scrobbles(lastfm_user, lastfm_api_key, from_timestamp)
        print(f"Obtenidos {len(tracks)} scrobbles")
        
        # Guardar todos los scrobbles en JSON si se especificó
        if output_json and tracks:
            if not os.path.exists(output_json):
                open(output_json, 'w').close()
            with open(output_json, 'w') as f:
                json.dump(tracks, f, indent=2)
            print(f"Guardados todos los scrobbles en {output_json}")
        
        # Procesar scrobbles
        if tracks:
            processed, linked, unlinked, newest_timestamp = process_scrobbles(
                conn, tracks, existing_artists, existing_albums, existing_songs, 
                lastfm_api_key, interactive
            )
            print(f"Procesados {processed} scrobbles: {linked} enlazados, {unlinked} no enlazados")
            
            # Guardar el timestamp más reciente para la próxima ejecución
            if newest_timestamp > 0:
                save_last_timestamp(conn, newest_timestamp, lastfm_user)
                print(f"Guardado último timestamp: {datetime.datetime.fromtimestamp(newest_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("No se encontraron nuevos scrobbles para procesar")
        
        # Mostrar estadísticas generales
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scrobbles")
        total_scrobbles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM scrobbles WHERE song_id IS NOT NULL")
        matched_scrobbles = cursor.fetchone()[0]
        
        print(f"Estadísticas generales: {total_scrobbles} scrobbles totales, {matched_scrobbles} enlazados con canciones ({matched_scrobbles/total_scrobbles*100:.1f}% de coincidencia)")
    
    finally:
        conn.close()
        
    return processed, linked, unlinked, newest_timestamp if 'processed' in locals() else (0, 0, 0, 0)



if __name__ == "__main__":
    main()