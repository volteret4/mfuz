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

def process_scrobbles(conn, tracks, existing_artists, existing_albums, existing_songs):
    """Procesa los scrobbles y actualiza la base de datos con los nuevos scrobbles"""
    cursor = conn.cursor()
    processed_count = 0
    linked_count = 0
    unlinked_count = 0
    newest_timestamp = 0
    
    # Verificar si hay scrobbles duplicados
    cursor.execute("SELECT timestamp FROM scrobbles ORDER BY timestamp DESC LIMIT 1")
    last_db_timestamp = cursor.fetchone()
    last_db_timestamp = last_db_timestamp[0] if last_db_timestamp else 0
    
    for track in tracks:
        artist_name = track['artist']['#text']
        album_name = track['album']['#text'] if track['album']['#text'] else None
        track_name = track['name']
        timestamp = int(track['date']['uts'])
        scrobble_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        lastfm_url = track['url']
        
        # Actualizar el timestamp más reciente
        newest_timestamp = max(newest_timestamp, timestamp)
        
        # Verificar si el scrobble ya existe en la base de datos para evitar duplicados
        cursor.execute("SELECT id FROM scrobbles WHERE timestamp = ? AND artist_name = ? AND track_name = ?", 
                      (timestamp, artist_name, track_name))
        if cursor.fetchone():
            continue  # El scrobble ya existe, continuamos con el siguiente
        
        # Buscar IDs existentes en la base de datos
        artist_id = existing_artists.get(artist_name.lower())
        album_id = None
        song_id = None
        
        if album_name and (album_name.lower(), artist_name.lower()) in existing_albums:
            album_id, _ = existing_albums.get((album_name.lower(), artist_name.lower()))
        
        song_key = (track_name.lower(), artist_name.lower(), album_name.lower() if album_name else None)
        if song_key in existing_songs:
            song_id = existing_songs.get(song_key)
        
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
            
            # Actualizar song_links si el song_id existe
            cursor.execute("""
                INSERT OR REPLACE INTO song_links (song_id, lastfm_url, links_updated)
                VALUES (?, ?, datetime('now'))
            """, (song_id, lastfm_url))
        else:
            unlinked_count += 1
        
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
    
    conn.commit()
    return processed_count, linked_count, unlinked_count, newest_timestamp

# def load_config(config_file):
#     """Load configuration from a JSON file"""
#     with open(config_file, 'r') as f:
#         config = json.load(f)
    
#     # Validate required keys
#     required_keys = ['db_path', 'lastfm_user', 'lastfm_api_key']
#     for key in required_keys:
#         if key not in config:
#             raise ValueError(f"Missing required configuration key: {key}")
    
#     return config

def main(config=None):
    # Cargar configuración
    parser = argparse.ArgumentParser(description='enlaces_artista_album')
    parser.add_argument('--config', help='Archivo de configuración')
    parser.add_argument('--lastfm_user', type=str, help='Usuario de Last.fm')
    parser.add_argument('--lastfm-api-key', type=str, help='API key de Last.fm')
    parser.add_argument('--db-path', type=str, help='Ruta al archivo de base de datos SQLite')
    parser.add_argument('--force-update', default=False, help='Forzar actualización completa')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar todos los scrobbles en formato JSON (opcional)')
            
    args = parser.parse_args()
        
    
    with open(args.config, 'r') as f:
        config_data = json.load(f)
        
    # Combinar configuraciones
    config = {}
    config.update(config_data.get("common", {}))
    config.update(config_data.get("scrobbles_lastfm", {}))

    
    db_path = args.db_path or config['db_path']
    if not db_path: 
        print("Añade db_path al json o usa --db-path")

    lastfm_user = args.lastfm_user or config['lastfm_user']
    if not lastfm_user: 
        print("Añade lastfm_user al json o usa --lastfm-user especificando tu usuario en lastfm")

    lastfm_api_key = args.lastfm_api_key or config['lastfm_api_key']
    if not lastfm_api_key:
        print("Añade lastfm_api_key al json o usa --lastfm-api-key especificando tu api key en lastfm")

    output_json = config.get("output_json", ".content/cache/scrobbles_lastfm.json")

    force_update = args.force_update or config['force_update']



    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    
    try:
        # Configurar la base de datos
        setup_database(conn)
        
        # Obtener elementos existentes
        existing_artists, existing_albums, existing_songs = get_existing_items(conn)
        print(f"Elementos existentes: {len(existing_artists)} artistas, {len(existing_albums)} álbumes, {len(existing_songs)} canciones")
        
        # Obtener el último timestamp procesado
        #from_timestamp = 0 if force_update else get_last_timestamp(conn)
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
                conn, tracks, existing_artists, existing_albums, existing_songs
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

if __name__ == "__main__":
    main()