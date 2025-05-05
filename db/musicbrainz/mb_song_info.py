import sqlite3
import time
import datetime
import musicbrainzngs as mb
from musicbrainzngs.musicbrainz import WebServiceError
import json
import os
import sys

# Configuración de MusicBrainz
mb.set_useragent("TuAppMusicaNombre", "0.1", "mailto:tuemail@example.com")

# Variables globales
force_update = False
DB_PATH = None
INTERACTIVE_MODE = False
CONFIG = {}

def connect_to_db():
    """Conecta a la base de datos SQLite"""
    if not DB_PATH:
        raise ValueError("DB_PATH no está definido")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_songs_to_update():
    """Obtiene las canciones que necesitan actualización de MusicBrainz"""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    if force_update:
        # Si force_update es True, actualizar todas las canciones
        cursor.execute("""
            SELECT s.id, s.title, s.artist, s.album_artist, s.album, s.mbid
            FROM songs s
            LEFT JOIN song_links sl ON s.id = sl.song_id
        """)
    else:
        # Si force_update es False, solo obtener canciones sin información de MusicBrainz
        cursor.execute("""
            SELECT s.id, s.title, s.artist, s.album_artist, s.album, s.mbid
            FROM songs s
            LEFT JOIN song_links sl ON s.id = sl.song_id
            WHERE (sl.musicbrainz_url IS NULL OR sl.musicbrainz_recording_id IS NULL)
        """)
    
    songs = cursor.fetchall()
    conn.close()
    return songs

def search_musicbrainz_by_mbid(mbid):
    """Busca información en MusicBrainz usando el MBID"""
    if not mbid:
        return None
    
    try:
        # Intentar obtener la grabación por MBID con includes válidos
        result = mb.get_recording_by_id(mbid, includes=["artists", "releases", "artist-credits"])
        return result
    except WebServiceError as e:
        print(f"Error de API de MusicBrainz con MBID {mbid}: {str(e)}")
        return None
    except Exception as e:
        print(f"Error al buscar por MBID {mbid}: {str(e)}")
        return None

def search_musicbrainz_by_metadata(title, artist, album=None):
    """Busca información en MusicBrainz usando metadatos"""
    query = f'recording:"{title}" AND artist:"{artist}"'
    if album:
        query += f' AND release:"{album}"'
    
    try:
        # Buscar grabaciones que coincidan con la consulta
        result = mb.search_recordings(query=query, limit=5)
        if 'recording-list' in result and result['recording-list']:
            # Obtener el MBID de la primera coincidencia
            recording_id = result['recording-list'][0]['id']
            # Obtener información completa
            try:
                return mb.get_recording_by_id(recording_id, includes=["artists", "releases", "artist-credits"])
            except WebServiceError as e:
                print(f"Error al obtener detalles para {recording_id}: {str(e)}")
                return None
        return None
    except Exception as e:
        print(f"Error al buscar {title} - {artist}: {str(e)}")
        return None

def extract_mb_data(recording_data):
    """Extrae datos relevantes de la respuesta de MusicBrainz"""
    if not recording_data or 'recording' not in recording_data:
        return {}
    
    recording = recording_data['recording']
    
    data = {
        'musicbrainz_recording_id': recording.get('id', ''),
        'musicbrainz_url': f"https://musicbrainz.org/recording/{recording.get('id', '')}",
        'musicbrainz_artist_id': '',
        'musicbrainz_album_artist_id': '',
        'musicbrainz_release_group_id': ''
    }
    
    # Extraer ID del artista principal
    if 'artist-credit' in recording and recording['artist-credit']:
        for artist_credit in recording['artist-credit']:
            if isinstance(artist_credit, dict) and 'artist' in artist_credit:
                data['musicbrainz_artist_id'] = artist_credit['artist'].get('id', '')
                break
    
    # Extraer ID del grupo de lanzamiento (álbum)
    if 'release-list' in recording and recording['release-list']:
        for release in recording['release-list']:
            # Obtener release-group ID si está disponible
            if 'release-group' in release and isinstance(release['release-group'], dict):
                data['musicbrainz_release_group_id'] = release['release-group'].get('id', '')
            
            # Extraer ID del artista del álbum
            if 'artist-credit' in release and release['artist-credit']:
                for artist_credit in release['artist-credit']:
                    if isinstance(artist_credit, dict) and 'artist' in artist_credit:
                        data['musicbrainz_album_artist_id'] = artist_credit['artist'].get('id', '')
                        break
            
            # Si encontramos un grupo de lanzamiento, podemos terminar
            if data['musicbrainz_release_group_id']:
                break
    
    return data

def update_song_links(song_id, mb_data):
    """Actualiza la información de MusicBrainz en la tabla song_links"""
    if not mb_data:
        return
    
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Verificar si ya existe una entrada para esta canción
    cursor.execute("SELECT id FROM song_links WHERE song_id = ?", (song_id,))
    row = cursor.fetchone()
    
    if row:
        # Actualizar entrada existente
        query = """
            UPDATE song_links SET 
            musicbrainz_url = ?,
            musicbrainz_recording_id = ?,
            links_updated = CURRENT_TIMESTAMP
            WHERE song_id = ?
        """
        cursor.execute(query, (
            mb_data.get('musicbrainz_url', ''),
            mb_data.get('musicbrainz_recording_id', ''),
            song_id
        ))
    else:
        # Crear nueva entrada
        query = """
            INSERT INTO song_links (
                song_id, musicbrainz_url, musicbrainz_recording_id, links_updated
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """
        cursor.execute(query, (
            song_id,
            mb_data.get('musicbrainz_url', ''),
            mb_data.get('musicbrainz_recording_id', '')
        ))
    
    conn.commit()
    
    # Actualizar la tabla songs con IDs de MusicBrainz
    query = """
        UPDATE songs SET 
        mbid = ?,
        musicbrainz_artistid = ?,
        musicbrainz_albumartistid = ?,
        musicbrainz_releasegroupid = ?
        WHERE id = ?
    """
    cursor.execute(query, (
        mb_data.get('musicbrainz_recording_id', ''),
        mb_data.get('musicbrainz_artist_id', ''),
        mb_data.get('musicbrainz_album_artist_id', ''),
        mb_data.get('musicbrainz_release_group_id', ''),
        song_id
    ))
    
    conn.commit()
    conn.close()

def process_songs():
    """Procesa todas las canciones y actualiza la información de MusicBrainz"""
    songs = get_songs_to_update()
    total = len(songs)
    
    print(f"Se procesarán {total} canciones")
    
    for i, song in enumerate(songs):
        if i > 0 and i % 10 == 0:
            print(f"Procesadas {i}/{total} canciones")
        
        # Verificación y limpieza de datos
        title = song['title'] if song['title'] else ""
        artist = song['artist'] if song['artist'] else ""
        album = song['album'] if song['album'] else ""
        mbid = song['mbid'] if song['mbid'] else ""
        
        # Primero intentar buscar por MBID
        mb_result = None
        if mbid:
            mb_result = search_musicbrainz_by_mbid(mbid)
        
        # Si no hay MBID o la búsqueda por MBID falla, buscar por metadatos
        if not mb_result and title and artist:
            mb_result = search_musicbrainz_by_metadata(title, artist, album)
        
        # Extraer datos relevantes
        if mb_result:
            mb_data = extract_mb_data(mb_result)
            update_song_links(song['id'], mb_data)
        
        # Esperar 1 segundo para no sobrecargar la API de MusicBrainz
        time.sleep(1)
    
    print(f"Procesamiento completado. {total} canciones actualizadas.")

def main(config=None):
    """Función principal del script"""
    global force_update, DB_PATH, CONFIG
    
    if config:
        CONFIG = config
        # Establecer la ruta de la base de datos
        DB_PATH = config.get('db_path')
        if not DB_PATH:
            print("Error: No se especificó la ruta de la base de datos (db_path)")
            return
        
        # Establecer force_update
        force_update = config.get('force_update', False)
    
    print(f"Iniciando actualización de MusicBrainz. Force update: {force_update}")
    
    # Validar la conexión a la base de datos
    try:
        conn = connect_to_db()
        conn.close()
        print("Conexión a la base de datos exitosa")
    except Exception as e:
        print(f"Error al conectar a la base de datos: {str(e)}")
        return
    
    # Iniciar el procesamiento
    process_songs()

# Si se ejecuta directamente, establecer configuración predeterminada para pruebas
if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        with open(config_file, 'r') as f:
            config = json.load(f)
        main(config)
    else:
        # Configuración de prueba
        test_config = {
            'db_path': './music.db',
            'force_update': False
        }
        main(test_config)