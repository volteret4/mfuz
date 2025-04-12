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

INTERACTIVE_MODE = True  # This will be set by db_creator.py
FORCE_UPDATE = True  # This will be set by db_creator.py

# Variable global para el caché (inicializar en setup_musicbrainz)
mb_cache = None
lastfm_cache = None

def handle_force_update(db_path):
    """
    Función crítica: Se ejecuta al principio del módulo para asegurar que force_update funcione
    """
    global FORCE_UPDATE
    if not FORCE_UPDATE or not db_path:
        return
        
    print("\n" + "!"*80)
    print("MODO FORCE_UPDATE ACTIVADO: Eliminando todos los scrobbles existentes")
    print("!"*80 + "\n")
    
    try:
        # Conectar directamente a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si existe la tabla
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scrobbles'")
        if cursor.fetchone():
            # Eliminar datos
            cursor.execute("DELETE FROM scrobbles")
            # Restablecer el timestamp
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lastfm_config'")
            if cursor.fetchone():
                cursor.execute("UPDATE lastfm_config SET last_timestamp = 0 WHERE id = 1")
            
            conn.commit()
            print(f"Base de datos limpiada exitosamente: {db_path}")
            print(f"Se han eliminado todos los scrobbles. Se realizará una actualización completa.\n")
        else:
            print(f"La tabla 'scrobbles' no existe aún en la base de datos: {db_path}")
        
        conn.close()
    except Exception as e:
        print(f"Error al intentar limpiar la base de datos: {e}")

def find_best_match(name, candidates, threshold=0.8):
    """
    Encuentra la mejor coincidencia para 'name' entre los candidatos.
    Totalmente insensible a mayúsculas/minúsculas.
    
    Args:
        name: Nombre a buscar
        candidates: Lista de nombres candidatos o diccionario donde las claves son nombres
        threshold: Umbral mínimo de coincidencia (0-1)
    
    Returns:
        Tupla (mejor_coincidencia, puntuación) o (None, 0) si no hay coincidencias
    """
    import difflib
    
    if not candidates or not name:
        return None, 0
    
    # Normalizar nombre para comparación (todo a minúsculas)
    name_lower = name.lower().strip()
    
    # Si candidates es un diccionario, extraemos las claves (nombres)
    if isinstance(candidates, dict):
        candidate_items = list(candidates.items())
        candidate_names = [k for k, v in candidate_items]
    else:
        candidate_names = candidates
        candidate_items = [(c, c) for c in candidates]
    
    # Primero buscar coincidencias exactas (ignorando mayúsculas/minúsculas)
    for i, cname in enumerate(candidate_names):
        if cname.lower().strip() == name_lower:
            return candidate_items[i][1], 1.0  # Coincidencia perfecta
    
    # Si no hay coincidencia exacta, calcular puntuaciones de similitud
    scores = []
    for i, cname in enumerate(candidate_names):
        # Usar minúsculas para la comparación
        ratio = difflib.SequenceMatcher(None, name_lower, cname.lower().strip()).ratio()
        scores.append((candidate_items[i][1], ratio))
    
    # Encontrar la mejor coincidencia
    if not scores:
        return None, 0
        
    best_match = max(scores, key=lambda x: x[1])
    
    # Devolver sólo si supera el umbral
    if best_match[1] >= threshold:
        return best_match
    
    return None, 0



def lookup_artist_in_database(conn, artist_name, mbid=None, threshold=0.85):
    """
    Lookup artist using database information with fuzzy matching
    Returns (artist_id, artist_info) or (None, None) if not found
    """
    cursor = conn.cursor()
    
    # Try exact name match first
    cursor.execute("SELECT id, mbid, name, origen FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name,))
    result = cursor.fetchone()
    
    # If no match by name but we have MBID, try by MBID
    if not result and mbid:
        cursor.execute("SELECT id, mbid, name, origen FROM artists WHERE mbid = ?", (mbid,))
        result = cursor.fetchone()
    
    # If still no match and threshold < 1.0, try fuzzy matching
    if not result and threshold < 1.0:
        # Get all artists for fuzzy matching
        cursor.execute("SELECT id, mbid, name, origen FROM artists")
        all_artists = cursor.fetchall()
        
        # Build dictionary of names to full records
        artist_dict = {row[2]: row for row in all_artists}
        
        # Find best match
        best_match, score = find_best_match(artist_name, artist_dict.keys(), threshold)
        
        if best_match:
            print(f"Encontrado artista por coincidencia aproximada: '{best_match}' (score: {score:.2f})")
            result = artist_dict[best_match]
    
    if result:
        return result[0], {
            'id': result[0],
            'mbid': result[1],
            'name': result[2],
            'origen': result[3]
        }
    
    return None, None

def lookup_album_in_database(conn, album_name, artist_id=None, artist_name=None, mbid=None, threshold=0.85):
    """
    Lookup album using database information with fuzzy matching
    Prioritizes search by artist_id if available
    Returns (album_id, album_info) or (None, None) if not found
    """
    cursor = conn.cursor()
    
    # Initial query construction for exact match
    query = "SELECT a.id, a.mbid, a.name, a.artist_id, ar.name, a.origen FROM albums a JOIN artists ar ON a.artist_id = ar.id WHERE "
    conditions = []
    params = []
    
    # Base condition on album name
    conditions.append("LOWER(a.name) = LOWER(?)")
    params.append(album_name)
    
    # If we have artist_id, prioritize it
    if artist_id:
        conditions.append("a.artist_id = ?")
        params.append(artist_id)
    # Otherwise use artist name if available
    elif artist_name:
        conditions.append("LOWER(ar.name) = LOWER(?)")
        params.append(artist_name)
    
    # Execute with available conditions
    cursor.execute(query + " AND ".join(conditions), params)
    result = cursor.fetchone()
    
    # If no match by name/artist but we have MBID, try by MBID
    if not result and mbid:
        cursor.execute("SELECT a.id, a.mbid, a.name, a.artist_id, ar.name, a.origen FROM albums a JOIN artists ar ON a.artist_id = ar.id WHERE a.mbid = ?", (mbid,))
        result = cursor.fetchone()
    
    # If still no match and threshold < 1.0, try fuzzy matching
    if not result and threshold < 1.0:
        # Get all albums for the artist if we have artist_id
        if artist_id:
            cursor.execute("SELECT a.id, a.mbid, a.name, a.artist_id, ar.name, a.origen FROM albums a JOIN artists ar ON a.artist_id = ar.id WHERE a.artist_id = ?", (artist_id,))
            artist_albums = cursor.fetchall()
            
            # Build dictionary of album names to full records
            album_dict = {row[2]: row for row in artist_albums}
            
            # Find best match among this artist's albums
            best_match, score = find_best_match(album_name, album_dict.keys(), threshold)
            
            if best_match:
                print(f"Encontrado álbum por coincidencia aproximada: '{best_match}' (score: {score:.2f})")
                result = album_dict[best_match]
        
        # If we still don't have a match but have artist_name, try all albums
        elif artist_name and not result:
            # Get all albums
            cursor.execute("SELECT a.id, a.mbid, a.name, a.artist_id, ar.name, a.origen FROM albums a JOIN artists ar ON a.artist_id = ar.id")
            all_albums = cursor.fetchall()
            
            # Create composite keys with artist and album name
            album_dict = {f"{row[4]} - {row[2]}": row for row in all_albums}
            
            # Find best match with combined artist-album key
            best_match, score = find_best_match(f"{artist_name} - {album_name}", album_dict.keys(), threshold)
            
            if best_match:
                print(f"Encontrado álbum por coincidencia aproximada: '{best_match}' (score: {score:.2f})")
                result = album_dict[best_match]
    
    if result:
        return result[0], {
            'id': result[0],
            'mbid': result[1],
            'name': result[2],
            'artist_id': result[3],
            'artist_name': result[4],
            'origen': result[5]
        }
    
    return None, None



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




def lookup_song_in_database(conn, track_name, artist_id=None, artist_name=None, album_id=None, album_name=None, mbid=None, lastfm_url=None, threshold=0.85):
    """
    Lookup song using database information with fuzzy matching
    Prioritizes search by existing IDs when available
    Returns (song_id, song_info) or (None, None) if not found
    """
    # If we have a Last.fm URL, try to find by that first
    if lastfm_url:
        song_id, song_info = lookup_song_by_lastfm_url(conn, lastfm_url)
        if song_id:
            return song_id, song_info
    cursor = conn.cursor()
    
    # Primero intentar una búsqueda exacta pero case-insensitive
    query = "SELECT id, mbid, title, artist, album, origen FROM songs WHERE "
    conditions = ["LOWER(title) = LOWER(?)"]
    params = [track_name]
    
    # Añadir condición de artista si disponible
    if artist_name:
        conditions.append("LOWER(artist) = LOWER(?)")
        params.append(artist_name)
    
    # Añadir condición de álbum si disponible
    if album_name:
        conditions.append("LOWER(album) = LOWER(?)")
        params.append(album_name)
    
    # Ejecutar consulta
    cursor.execute(query + " AND ".join(conditions), params)
    result = cursor.fetchone()
    
    # Si no hay resultado, intentar búsqueda más flexible sin importar mayúsculas/minúsculas
    if not result:
        # Obtener todas las canciones para búsqueda más flexible
        additional_cond = ""
        additional_params = []
    
        if artist_name:
            additional_cond = " WHERE LOWER(artist) = LOWER(?)"
            additional_params = [artist_name]
        
        cursor.execute(f"SELECT id, mbid, title, artist, album, origen FROM songs{additional_cond}", additional_params)
        all_songs = cursor.fetchall()
        
        # Comparar manualmente para total insensibilidad a case
        for song in all_songs:
            song_title = song[2]
            
            # Comparación insensible a mayúsculas/minúsculas
            if song_title.lower() == track_name.lower():
                # Si tenemos artista, verificar también
                if artist_name:
                    song_artist = song[3]
                    if song_artist.lower() == artist_name.lower():
                        result = song
                        print(f"Encontrada canción por coincidencia insensible a mayúsculas: '{song_title}' por '{song_artist}'")
                        break
                else:
                    result = song
                    print(f"Encontrada canción por coincidencia insensible a mayúsculas: '{song_title}'")
                    break
    
    if result:
        return result[0], {
            'id': result[0],
            'mbid': result[1],
            'title': result[2],
            'artist': result[3],
            'album': result[4],
            'origen': result[5]
        }
    
    return None, None



def get_or_update_artist(conn, artist_name, mbid, lastfm_api_key, interactive=False):
    """Busca un artista por nombre y lo actualiza con datos de MusicBrainz si es necesario"""
    cursor = conn.cursor()
    
    # Buscar primero por nombre en la base de datos
    cursor.execute("SELECT id, mbid, origen FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name,))
    existing_artist = cursor.fetchone()
    
    if existing_artist:
        artist_id, existing_mbid, origen = existing_artist
        print(f"Artista encontrado en base de datos por nombre: {artist_name} (ID: {artist_id})")
        
        # Si tenemos un nuevo MBID y el existente es diferente o no existe, actualizar
        if mbid and (not existing_mbid or existing_mbid != mbid):
            print(f"Actualizando MBID para artista {artist_name}: {mbid}")
            cursor.execute("UPDATE artists SET mbid = ? WHERE id = ?", (mbid, artist_id))
            conn.commit()
            
            # Opcionalmente obtener más datos de MusicBrainz
            if 'online' not in origen:
                artist_info = get_artist_info(artist_name, mbid, lastfm_api_key)
                if artist_info:
                    update_artist_in_db(conn, artist_id, artist_info)
        
        return artist_id
    
    # Si no existe, obtener info y crear nuevo
    print(f"Artista no encontrado, obteniendo información para: {artist_name}")
    artist_info = get_artist_info(artist_name, mbid, lastfm_api_key)
    
    if artist_info:
        return add_artist_to_db(conn, artist_info, interactive)
    
    # Si no se puede obtener info, crear con datos mínimos
    if interactive:
        print("\n" + "="*60)
        print(f"NO SE PUDO OBTENER INFORMACIÓN PARA EL ARTISTA:")
        print("="*60)
        print(f"Nombre: {artist_name}")
        print(f"MBID: {mbid}")
        print("-"*60)
        respuesta = input("¿Añadir este artista con datos mínimos? (s/n): ").lower()
        if respuesta != 's':
            return None
    
    try:
        cursor.execute("""
            INSERT INTO artists (name, mbid, origen)
            VALUES (?, ?, 'manual')
            RETURNING id
        """, (artist_name, mbid))
        
        artist_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Artista añadido con datos mínimos, ID: {artist_id}")
        return artist_id
    except sqlite3.Error as e:
        print(f"Error al añadir el artista {artist_name}: {e}")
        return None

def get_or_update_artist(conn, artist_name, mbid, interactive=False):
    """
    Busca un artista siguiendo la lógica prioritaria:
    1. Primero en base de datos
    2. Luego en MusicBrainz
    3. Solo como último recurso, Last.fm
    """
    print(f"\n=== Procesando artista: {artist_name} ===")
    
    # 1. Buscar en la base de datos
    artist_id, artist_db_info = lookup_artist_in_database(conn, artist_name, mbid)
    
    if artist_id:
        print(f"Artista encontrado en base de datos: {artist_name} (ID: {artist_id})")
        
        # Si tenemos un nuevo MBID y el existente es diferente o no existe, actualizar
        if mbid and (not artist_db_info['mbid'] or artist_db_info['mbid'] != mbid):
            cursor = conn.cursor()
            print(f"Actualizando MBID para artista {artist_name}: {mbid}")
            cursor.execute("UPDATE artists SET mbid = ? WHERE id = ?", (mbid, artist_id))
            conn.commit()
        
        return artist_id
    
    # 2. Si no está en la base de datos, buscar en MusicBrainz
    print(f"Artista no encontrado en base de datos, buscando en MusicBrainz: {artist_name}")
    
    mb_artist = None
    if mbid:
        # Si tenemos MBID, buscar directamente por él
        mb_artist = get_artist_from_musicbrainz(mbid)
        if mb_artist:
            print(f"Artista encontrado en MusicBrainz por MBID: {mb_artist.get('name', artist_name)}")
    
    # Si no tenemos MBID o no se encontró por MBID, buscar por nombre
    if not mb_artist:
        mb_artist = get_artist_from_musicbrainz_by_name(artist_name)
        if mb_artist:
            print(f"Artista encontrado en MusicBrainz por nombre: {mb_artist.get('name', artist_name)}")
            mbid = mb_artist.get('id', '')
    
    # 3. Si se encontró información en MusicBrainz, guardar en la base de datos
    if mb_artist:
        cursor = conn.cursor()
        
        # Extraer tags si existen
        tags = []
        if 'tag-list' in mb_artist:
            tags = [tag['name'] for tag in mb_artist.get('tag-list', [])]
        tags_str = ','.join(tags)
        
        # Extraer URLs oficiales
        url = ''
        if 'url-relation-list' in mb_artist:
            for url_rel in mb_artist['url-relation-list']:
                if url_rel.get('type') == 'official homepage':
                    url = url_rel.get('target', '')
                    break
        
        # Mostrar información en modo interactivo
        if interactive:
            print("\n" + "="*60)
            print(f"INFORMACIÓN DEL ARTISTA A AÑADIR (desde MusicBrainz):")
            print("="*60)
            print(f"Nombre: {mb_artist.get('name', artist_name)}")
            print(f"MBID: {mbid}")
            print(f"URL: {url}")
            print(f"Tags: {tags_str}")
            print(f"Origen: musicbrainz")
            print("-"*60)
            
            respuesta = input("\n¿Añadir este artista a la base de datos? (s/n): ").lower()
            if respuesta != 's':
                print("Operación cancelada por el usuario.")
                return None
        
        try:
            cursor.execute("""
                INSERT INTO artists (name, mbid, tags, lastfm_url, origen)
                VALUES (?, ?, ?, ?, 'musicbrainz')
                RETURNING id
            """, (
                mb_artist.get('name', artist_name), 
                mbid, 
                tags_str, 
                url
            ))
            
            artist_id = cursor.fetchone()[0]
            conn.commit()
            print(f"Artista añadido con ID: {artist_id} (origen: MusicBrainz)")
            return artist_id
        except sqlite3.Error as e:
            print(f"Error al añadir el artista {artist_name} desde MusicBrainz: {e}")
    
    # 4. Si todo lo anterior falla, preguntar al usuario
    if interactive:
        print("\n" + "="*60)
        print(f"NO SE PUDO OBTENER INFORMACIÓN PARA EL ARTISTA:")
        print("="*60)
        print(f"Nombre: {artist_name}")
        print(f"MBID: {mbid}")
        print("-"*60)
        respuesta = input("¿Añadir este artista con datos mínimos? (s/n): ").lower()
        if respuesta != 's':
            return None
    
    # 5. Añadir con datos mínimos
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO artists (name, mbid, origen)
            VALUES (?, ?, 'manual')
            RETURNING id
        """, (artist_name, mbid))
        
        artist_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Artista añadido con datos mínimos, ID: {artist_id}")
        return artist_id
    except sqlite3.Error as e:
        print(f"Error al añadir el artista {artist_name}: {e}")
        return None



def get_or_update_album(conn, album_name, artist_name, artist_id, mbid, interactive=False):
    """
    Busca un álbum siguiendo la lógica prioritaria:
    1. Primero en base de datos
    2. Luego en MusicBrainz
    3. Solo como último recurso, datos mínimos
    """
    print(f"\n=== Procesando álbum: {album_name} de {artist_name} ===")
    
    # 1. Buscar en la base de datos
    album_id, album_db_info = lookup_album_in_database(conn, album_name, artist_id, artist_name, mbid)
    
    if album_id:
        print(f"Álbum encontrado en base de datos: {album_name} (ID: {album_id})")
        
        # Si el artista es diferente del que tenemos en nuestro scrobble, analizar
        if album_db_info['artist_id'] != artist_id and artist_id is not None:
            print(f"Nota: El álbum está asociado a otro artista en la base de datos: {album_db_info['artist_name']}")
            # No modificaremos esto automáticamente, pero registramos la discrepancia
        
        # Si tenemos un nuevo MBID y el existente es diferente o no existe, actualizar
        if mbid and (not album_db_info['mbid'] or album_db_info['mbid'] != mbid):
            cursor = conn.cursor()
            print(f"Actualizando MBID para álbum {album_name}: {mbid}")
            cursor.execute("UPDATE albums SET mbid = ? WHERE id = ?", (mbid, album_id))
            conn.commit()
        
        return album_id
    
    # 2. Si no está en la base de datos, buscar en MusicBrainz
    print(f"Álbum no encontrado en base de datos, buscando en MusicBrainz: {album_name}")
    
    mb_album = None
    if mbid:
        # Si tenemos MBID, buscar directamente por él
        mb_album = get_album_from_musicbrainz(mbid)
        if mb_album:
            print(f"Álbum encontrado en MusicBrainz por MBID: {mb_album.get('title', album_name)}")
    
    # Si no tenemos MBID o no se encontró por MBID, buscar por nombre y artista
    if not mb_album:
        mb_album = get_album_from_musicbrainz_by_name(album_name, artist_name)
        if mb_album:
            print(f"Álbum encontrado en MusicBrainz por nombre: {mb_album.get('title', album_name)}")
            mbid = mb_album.get('id', '')
    
    # 3. Si se encontró información en MusicBrainz, guardar en la base de datos
    if mb_album:
        # Extraer año si existe
        year = None
        if 'date' in mb_album:
            try:
                year_str = mb_album['date']
                if year_str and len(year_str) >= 4:
                    year = int(year_str[:4])
            except (ValueError, TypeError):
                pass
        
        # Número de pistas
        total_tracks = 0
        if 'medium-list' in mb_album:
            for medium in mb_album['medium-list']:
                if 'track-count' in medium:
                    total_tracks += int(medium['track-count'])
        
        # Mostrar información en modo interactivo
        if interactive:
            print("\n" + "="*60)
            print(f"INFORMACIÓN DEL ÁLBUM A AÑADIR (desde MusicBrainz):")
            print("="*60)
            print(f"Nombre: {mb_album.get('title', album_name)}")
            print(f"Artista: {artist_name} (ID: {artist_id})")
            print(f"MBID: {mbid}")
            print(f"Año: {year}")
            print(f"Total pistas: {total_tracks}")
            print(f"Origen: musicbrainz")
            print("-"*60)
            
            respuesta = input("\n¿Añadir este álbum a la base de datos? (s/n): ").lower()
            if respuesta != 's':
                print("Operación cancelada por el usuario.")
                return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO albums (artist_id, name, year, mbid, total_tracks, origen)
                VALUES (?, ?, ?, ?, ?, 'musicbrainz')
                RETURNING id
            """, (
                artist_id, 
                mb_album.get('title', album_name), 
                year, 
                mbid, 
                total_tracks
            ))
            
            album_id = cursor.fetchone()[0]
            conn.commit()
            print(f"Álbum añadido con ID: {album_id} (origen: MusicBrainz)")
            return album_id
        except sqlite3.Error as e:
            print(f"Error al añadir el álbum {album_name} desde MusicBrainz: {e}")
    
    # 4. Si todo lo anterior falla, preguntar al usuario
    if interactive:
        print("\n" + "="*60)
        print(f"NO SE PUDO OBTENER INFORMACIÓN PARA EL ÁLBUM:")
        print("="*60)
        print(f"Nombre: {album_name}")
        print(f"Artista: {artist_name} (ID: {artist_id})")
        print(f"MBID: {mbid}")
        print("-"*60)
        respuesta = input("¿Añadir este álbum con datos mínimos? (s/n): ").lower()
        if respuesta != 's':
            return None
    
    # 5. Añadir con datos mínimos
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO albums (name, artist_id, mbid, origen)
            VALUES (?, ?, ?, 'manual')
            RETURNING id
        """, (album_name, artist_id, mbid))
        
        album_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Álbum añadido con datos mínimos, ID: {album_id}")
        return album_id
    except sqlite3.Error as e:
        print(f"Error al añadir el álbum {album_name}: {e}")
        return None



def get_or_update_song(conn, track_name, artist_name, album_name, artist_id, album_id, mbid, interactive=False):
    """
    Busca una canción siguiendo la lógica prioritaria:
    1. Primero en base de datos
    2. Luego en MusicBrainz
    3. Solo como último recurso, datos mínimos
    """
    print(f"\n=== Procesando canción: {track_name} de {artist_name} ===")
    
    # 1. Buscar en la base de datos
    song_id, song_db_info = lookup_song_in_database(conn, track_name, artist_id, artist_name, album_id, album_name, mbid)
    
    if song_id:
        print(f"Canción encontrada en base de datos: {track_name} (ID: {song_id})")
        
        # Si tenemos un nuevo MBID y el existente es diferente o no existe, actualizar
        if mbid and (not song_db_info['mbid'] or song_db_info['mbid'] != mbid):
            cursor = conn.cursor()
            print(f"Actualizando MBID para canción {track_name}: {mbid}")
            cursor.execute("UPDATE songs SET mbid = ? WHERE id = ?", (mbid, song_id))
            
            # Si tenemos un álbum, actualizar también ese dato si está vacío
            if album_name and album_id and (not song_db_info['album'] or song_db_info['album'] == ''):
                cursor.execute("UPDATE songs SET album = ?, album_id = ? WHERE id = ?", 
                               (album_name, album_id, song_id))
            
            conn.commit()
        
        return song_id
    
    # 2. Si no está en la base de datos, buscar en MusicBrainz
    print(f"Canción no encontrada en base de datos, buscando en MusicBrainz: {track_name}")
    
    mb_track = None
    if mbid:
        # Si tenemos MBID, buscar directamente por él
        mb_track = get_track_from_musicbrainz(mbid)
        if mb_track:
            print(f"Canción encontrada en MusicBrainz por MBID: {mb_track.get('title', track_name)}")
    
    # Si no tenemos MBID o no se encontró por MBID, buscar por nombre, artista y álbum
    if not mb_track:
        mb_track = get_track_from_musicbrainz_by_name(track_name, artist_name, album_name)
        if mb_track:
            print(f"Canción encontrada en MusicBrainz por nombre: {mb_track.get('title', track_name)}")
            mbid = mb_track.get('id', '')
    
    # 3. Si se encontró información en MusicBrainz, guardar en la base de datos
    if mb_track:
        # Extraer duración si existe
        duration = None
        if 'length' in mb_track:
            try:
                duration = int(mb_track['length']) // 1000  # ms a segundos
            except (ValueError, TypeError):
                pass
        
        # Géneros/tags
        genre = ''
        if 'tag-list' in mb_track and mb_track['tag-list']:
            genre = mb_track['tag-list'][0]['name']
        
        # Fecha actual para campos de tiempo
        now = datetime.datetime.now()
        added_timestamp = int(time.time())
        added_week = now.isocalendar()[1]
        added_month = now.month
        added_year = now.year
        
        # Mostrar información en modo interactivo
        if interactive:
            print("\n" + "="*60)
            print(f"INFORMACIÓN DE LA CANCIÓN A AÑADIR (desde MusicBrainz):")
            print("="*60)
            print(f"Título: {mb_track.get('title', track_name)}")
            print(f"Artista: {artist_name} (ID: {artist_id})")
            print(f"Álbum: {album_name} (ID: {album_id})")
            print(f"MBID: {mbid}")
            print(f"Duración: {duration} segundos")
            print(f"Género: {genre}")
            print(f"Origen: musicbrainz")
            print("-"*60)
            
            respuesta = input("\n¿Añadir esta canción a la base de datos? (s/n): ").lower()
            if respuesta != 's':
                print("Operación cancelada por el usuario.")
                return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO songs 
                (title, mbid, added_timestamp, added_week, added_month, added_year, 
                 duration, album, album_artist, artist, genre, origen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'musicbrainz')
                RETURNING id
            """, (
                mb_track.get('title', track_name), 
                mbid, 
                added_timestamp, 
                added_week, 
                added_month, 
                added_year,
                duration, 
                album_name, 
                artist_name, 
                artist_name, 
                genre
            ))
            
            song_id = cursor.fetchone()[0]
            conn.commit()
            print(f"Canción añadida con ID: {song_id} (origen: MusicBrainz)")
            return song_id
        except sqlite3.Error as e:
            print(f"Error al añadir la canción {track_name} desde MusicBrainz: {e}")
    
    # 4. Si todo lo anterior falla, preguntar al usuario
    if interactive:
        print("\n" + "="*60)
        print(f"NO SE PUDO OBTENER INFORMACIÓN PARA LA CANCIÓN:")
        print("="*60)
        print(f"Título: {track_name}")
        print(f"Artista: {artist_name} (ID: {artist_id})")
        print(f"Álbum: {album_name if album_name else 'N/A'} (ID: {album_id if album_id else 'N/A'})")
        print(f"MBID: {mbid}")
        print("-"*60)
        respuesta = input("¿Añadir esta canción con datos mínimos? (s/n): ").lower()
        if respuesta != 's':
            return None
    
    # 5. Añadir con datos mínimos
    now = datetime.datetime.now()
    added_timestamp = int(time.time())
    added_week = now.isocalendar()[1]
    added_month = now.month
    added_year = now.year
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO songs 
            (title, artist, album, album_artist, mbid, added_timestamp, added_week, added_month, added_year, origen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual')
            RETURNING id
        """, (track_name, artist_name, album_name, artist_name, mbid, added_timestamp, added_week, added_month, added_year))
        
        song_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Canción añadida con datos mínimos, ID: {song_id}")
        return song_id
    except sqlite3.Error as e:
        print(f"Error al añadir la canción {track_name}: {e}")
        return None


def setup_musicbrainz(cache_directory=None):
    """Configura el cliente de MusicBrainz y el sistema de caché"""
    global mb_cache, lastfm_cache
    
    # Configurar cliente de MusicBrainz
    musicbrainzngs.set_useragent(
        "TuAppMusical", 
        "1.0", 
        "tu_email@example.com"
    )
    
    # Inicializar caché (en memoria por defecto)
    if mb_cache is None:
        mb_cache = MusicBrainzCache()
    
    if lastfm_cache is None:
        lastfm_cache = LastFMCache()
    
    # Si se proporciona un directorio de caché, configurar persistencia
    if cache_directory:
        try:
            os.makedirs(cache_directory, exist_ok=True)
            
            mb_cache_file = os.path.join(cache_directory, "musicbrainz_cache.json")
            lastfm_cache_file = os.path.join(cache_directory, "lastfm_cache.json")
            
            mb_cache = MusicBrainzCache(mb_cache_file)
            lastfm_cache = LastFMCache(lastfm_cache_file)
            
            print(f"Caché configurado en: {cache_directory}")
        except Exception as e:
            print(f"Error al configurar caché persistente: {e}")
            print("Usando caché en memoria")
    else:
        print("Caché configurado en memoria (no persistente)")

def get_artist_from_musicbrainz(mbid):
    """
    Obtiene información de un artista desde MusicBrainz usando su MBID, usando caché
    """
    global mb_cache
    
    if not mbid:
        return None
    
    # Verificar en caché primero
    if mb_cache:
        cached_result = mb_cache.get("artist", mbid)
        if cached_result:
            print(f"Usando datos en caché para artista con MBID {mbid}")
            return cached_result
    
    try:
        print(f"Consultando MusicBrainz para artista con MBID {mbid}")
        artist_data = musicbrainzngs.get_artist_by_id(mbid, includes=["tags", "url-rels"])
        result = artist_data.get("artist")
        
        # Guardar en caché
        if mb_cache and result:
            mb_cache.put("artist", result, mbid)
            
        return result
    except musicbrainzngs.WebServiceError as e:
        print(f"Error al consultar MusicBrainz para artista con MBID {mbid}: {e}")
        return None

def get_artist_from_musicbrainz_by_name(artist_name):
    """
    Búsqueda en MusicBrainz por nombre del artista, usando caché
    """
    global mb_cache
    
    if not artist_name:
        return None
    
    # Simply use artist_name directly, don't try to reference album_name
    artist_name = str(artist_name) if artist_name else ""

    # Verificar en caché primero
    search_params = {"artist": artist_name, "limit": 1}
    if mb_cache:
        cached_result = mb_cache.get("artist-search", None, search_params)
        if cached_result:
            print(f"Usando datos en caché para búsqueda de artista '{artist_name}'")
            return cached_result
    
    try:
        print(f"Consultando MusicBrainz para búsqueda de artista '{artist_name}'")
        result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        
        # Extraer primer resultado si existe
        if result and 'artist-list' in result and result['artist-list']:
            first_result = result['artist-list'][0]
            
            # Guardar en caché
            if mb_cache:
                mb_cache.put("artist-search", first_result, None, search_params)
                
            return first_result
        return None
    except musicbrainzngs.WebServiceError as e:
        print(f"Error al buscar artista en MusicBrainz por nombre '{artist_name}': {e}")
        return None

def get_album_from_musicbrainz(mbid):
    """Obtiene información de un álbum desde MusicBrainz usando su MBID, usando caché"""
    global mb_cache
    
    if not mbid:
        return None
    
    # Verificar en caché primero
    if mb_cache:
        cached_result = mb_cache.get("release", mbid)
        if cached_result:
            print(f"Usando datos en caché para álbum con MBID {mbid}")
            return cached_result
    
    try:
        print(f"Consultando MusicBrainz para álbum con MBID {mbid}")
        release_data = musicbrainzngs.get_release_by_id(
            mbid, 
            includes=["artists", "recordings", "release-groups", "url-rels"]
        )
        result = release_data.get("release")
        
        # Guardar en caché
        if mb_cache and result:
            mb_cache.put("release", result, mbid)
            
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
        cached_result = mb_cache.get("release-search", None, query)
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
                                    mb_cache.put("release-search", release, None, query)
                                return release
            
            # Si no hay coincidencia exacta, usar el primer resultado
            first_result = result['release-list'][0]
            
            # Guardar en caché
            if mb_cache:
                mb_cache.put("release-search", first_result, None, query)
                
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
        cached_result = mb_cache.get("recording", mbid)
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
            mb_cache.put("recording", result, mbid)
            
        return result
    except musicbrainzngs.WebServiceError as e:
        print(f"Error al consultar MusicBrainz para canción con MBID {mbid}: {e}")
        return None

def get_track_from_musicbrainz_by_name(track_name, artist_name=None, album_name=None):
    """Búsqueda en MusicBrainz por nombre de la canción y opcionalmente artista/álbum, usando caché"""
    global mb_cache
    
    if not track_name:
        return None
    
    # Proper string conversion to avoid errors
    track_name = str(track_name) if track_name else ""
    artist_name = str(artist_name) if artist_name else ""
    album_name = str(album_name) if album_name else ""
    
    # Construir parámetros de búsqueda
    query = {'recording': track_name, 'limit': 5}
    if artist_name:
        query['artist'] = artist_name
        
    # Verificar en caché primero
    if mb_cache:
        cached_result = mb_cache.get("recording-search", None, query)
        if cached_result:
            print(f"Usando datos en caché para búsqueda de canción '{track_name}'")
            return cached_result
    
    try:
        print(f"Consultando MusicBrainz para búsqueda de canción '{track_name}'")
        result = musicbrainzngs.search_recordings(**query)
        
        if result and 'recording-list' in result and result['recording-list']:
            recordings = result['recording-list']
            
            # Si tenemos artista y álbum, intentar encontrar coincidencia exacta
            if artist_name and album_name:
                for recording in recordings:
                    if 'artist-credit' in recording and 'release-list' in recording:
                        # Verificar coincidencia de artista
                        artist_match = False
                        for credit in recording['artist-credit']:
                            if 'artist' in credit and 'name' in credit['artist'] and credit['artist']['name'].lower() == artist_name.lower():
                                artist_match = True
                                break
                        
                        # Si el artista coincide, verificar álbum
                        if artist_match and 'release-list' in recording:
                            for release in recording['release-list']:
                                if release['title'].lower() == album_name.lower():
                                    # Guardar en caché
                                    if mb_cache:
                                        mb_cache.put("recording-search", recording, None, query)
                                    return recording
            
            # Si sólo tenemos artista, buscar mejor coincidencia por artista
            elif artist_name:
                for recording in recordings:
                    if 'artist-credit' in recording:
                        for credit in recording['artist-credit']:
                            if 'artist' in credit and 'name' in credit['artist'] and credit['artist']['name'].lower() == artist_name.lower():
                                # Guardar en caché
                                if mb_cache:
                                    mb_cache.put("recording-search", recording, None, query)
                                return recording
            
            # Si no hay coincidencia exacta, usar el primer resultado
            first_result = recordings[0]
            
            # Guardar en caché
            if mb_cache:
                mb_cache.put("recording-search", first_result, None, query)
                
            return first_result
        return None
    except musicbrainzngs.WebServiceError as e:
        print(f"Error al buscar canción en MusicBrainz por nombre '{track_name}': {e}")
        return None

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
     # Add indexes for Last.fm URLs
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_artists_lastfm_url ON artists(lastfm_url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_lastfm_url ON albums(lastfm_url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_song_links_lastfm_url ON song_links(lastfm_url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)")

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
    

    # Crear tabla song_links si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS song_links (
        id INTEGER PRIMARY KEY,
        song_id INTEGER,
        lastfm_url TEXT,
        FOREIGN KEY (song_id) REFERENCES songs(id)
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
    """Obtiene información detallada de un artista desde Last.fm, usando caché"""
    global lastfm_cache
    
    # Construir parámetros de consulta
    params = {
        'method': 'artist.getInfo',
        'artist': artist_name,
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    if mbid:
        params['mbid'] = mbid
    
    # Verificar en caché primero
    if lastfm_cache:
        cached_result = lastfm_cache.get('artist.getInfo', params)
        if cached_result:
            print(f"Usando datos en caché para artista Last.fm: {artist_name}")
            return cached_result.get('artist')
    
    print(f"Consultando información para artista: {artist_name} (MBID: {mbid})")
    
    try:
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
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
            return None
        
        print(f"Información obtenida correctamente para artista: {artist_name}")
        
        # Guardar en caché
        if lastfm_cache:
            lastfm_cache.put('artist.getInfo', params, data)
            
        return data['artist']
    
    except Exception as e:
        print(f"Error al consultar artista {artist_name}: {e}")
        return None

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
        cached_result = lastfm_cache.get('album.getInfo', params)
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
            lastfm_cache.put('album.getInfo', params, data)
            
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
        cached_result = lastfm_cache.get('track.getInfo', cache_params)
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
            lastfm_cache.put('track.getInfo', params, data)
            
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
    """Añade un nuevo artista a la base de datos con prioridad para datos de MusicBrainz"""
    cursor = conn.cursor()
    
    artist_name = artist_info.get('name', '')
    mbid = artist_info.get('mbid', '')
    url = artist_info.get('url', '')
    
    # Intentar obtener datos de MusicBrainz si hay MBID
    mb_artist = None
    if mbid:
        mb_artist = get_artist_from_musicbrainz(mbid)
    
    # Usar nombre de MusicBrainz si está disponible
    if mb_artist and 'name' in mb_artist:
        artist_name = mb_artist.get('name', artist_name)
        print(f"Usando nombre de MusicBrainz: {artist_name}")
    
    # Extraer tags
    tags = []
    if 'tags' in artist_info and 'tag' in artist_info['tags']:
        tag_list = artist_info['tags']['tag']
        if isinstance(tag_list, list):
            tags = [tag['name'] for tag in tag_list]
        else:
            tags = [tag_list['name']]
    
    # Intentar añadir tags de MusicBrainz
    if mb_artist and 'tag-list' in mb_artist:
        mb_tags = [tag['name'] for tag in mb_artist.get('tag-list', [])]
        tags.extend(mb_tags)
        tags = list(set(tags))  # Eliminar duplicados
    
    tags_str = ','.join(tags)
    
    # Extraer bio
    bio = ''
    if 'bio' in artist_info and 'content' in artist_info['bio']:
        bio = artist_info['bio']['content']
    
    # Añadir URLs de MusicBrainz
    if mb_artist and 'url-relation-list' in mb_artist:
        for url_rel in mb_artist['url-relation-list']:
            if url_rel.get('type') == 'official homepage':
                mb_url = url_rel.get('target')
                if mb_url:
                    print(f"Añadiendo URL oficial de MusicBrainz: {mb_url}")
                    # No sobreescribimos LastFM URL, guardamos en una nueva columna o campo
    
    if interactive:
        # Código existente para modo interactivo con adición de info de origen de datos
        print("\n" + "="*60)
        print(f"INFORMACIÓN DEL ARTISTA A AÑADIR:")
        print("="*60)
        print(f"Nombre: {artist_name}")
        print(f"MBID: {mbid}")
        print(f"URL: {url}")
        print(f"Tags: {tags_str}")
        print("Bio: " + bio[:150] + "..." if len(bio) > 150 else f"Bio: {bio}")
        print(f"Origen de datos: {'MusicBrainz+LastFM' if mb_artist else 'LastFM'}")
        print("-"*60)
        print("Columnas a insertar en la tabla 'artists':")
        print("-"*60)
        print(f"name = '{artist_name}'")
        print(f"mbid = '{mbid}'")
        print(f"tags = '{tags_str}'")
        print(f"bio = '{bio[:50]}...'")
        print(f"lastfm_url = '{url}'")
        print(f"origen = '{'musicbrainz+online' if mb_artist else 'online'}'")
        print("="*60)
        
        respuesta = input("\n¿Añadir este artista a la base de datos? (s/n): ").lower()
        if respuesta != 's':
            print("Operación cancelada por el usuario.")
            return None
    
    try:
        cursor.execute("""
            INSERT INTO artists (name, mbid, tags, bio, lastfm_url, origen)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
        """, (
            artist_name, 
            mbid, 
            tags_str, 
            bio, 
            url, 
            'musicbrainz+online' if mb_artist else 'online'
        ))
        
        artist_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Artista añadido con ID: {artist_id}")
        return artist_id
    except sqlite3.Error as e:
        print(f"Error al añadir el artista {artist_name}: {e}")
        return None

def add_album_to_db(conn, album_info, artist_id, interactive=False):
    """Añade un nuevo álbum a la base de datos con prioridad para datos de MusicBrainz"""
    cursor = conn.cursor()
    
    album_name = album_info.get('name', '')
    mbid = album_info.get('mbid', '')
    url = album_info.get('url', '')
    
    # Intentar obtener datos de MusicBrainz si hay MBID
    mb_album = None
    if mbid:
        mb_album = get_album_from_musicbrainz(mbid)
    
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
    
    # Intentar obtener año de MusicBrainz
    if mb_album and 'date' in mb_album:
        try:
            mb_date = mb_album['date']
            if mb_date and (len(mb_date) >= 4):
                mb_year = int(mb_date[:4])
                if mb_year > 0:
                    year = mb_year
                    print(f"Usando año de MusicBrainz: {year}")
        except (ValueError, TypeError):
            pass
    
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
        print(f"Total pistas: {total_tracks}")
        print(f"Origen de datos: {'MusicBrainz+LastFM' if mb_album else 'LastFM'}")
        print("-"*60)
        print("Columnas a insertar en la tabla 'albums':")
        print("-"*60)
        print(f"artist_id = {artist_id}")
        print(f"name = '{album_name}'")
        print(f"year = {year}")
        print(f"lastfm_url = '{url}'")
        print(f"mbid = '{mbid}'")
        print(f"total_tracks = {total_tracks}")
        print(f"origen = '{'musicbrainz+online' if mb_album else 'online'}'")
        print("="*60)
        
        respuesta = input("\n¿Añadir este álbum a la base de datos? (s/n): ").lower()
        if respuesta != 's':
            print("Operación cancelada por el usuario.")
            return None
    
    try:
        cursor.execute("""
            INSERT INTO albums (artist_id, name, year, lastfm_url, mbid, total_tracks, origen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """, (
            artist_id, 
            album_name, 
            year, 
            url, 
            mbid, 
            total_tracks, 
            'musicbrainz+online' if mb_album else 'online'
        ))
        
        album_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Álbum añadido con ID: {album_id}")
        return album_id
    except sqlite3.Error as e:
        print(f"Error al añadir el álbum {album_name}: {e}")
        return None



def add_song_to_db(conn, track_info, album_id, artist_id, interactive=False):
    """Añade una nueva canción a la base de datos con prioridad para datos de MusicBrainz"""
    cursor = conn.cursor()
    
    track_name = track_info.get('name', '')
    mbid = track_info.get('mbid', '')
    
    # Intentar obtener datos de MusicBrainz si hay MBID
    mb_track = None
    if mbid:
        mb_track = get_track_from_musicbrainz(mbid)
    
    # Usar nombre de MusicBrainz si está disponible
    if mb_track and 'title' in mb_track:
        track_name = mb_track.get('title', track_name)
        print(f"Usando nombre de MusicBrainz: {track_name}")
    
    # Obtener duración
    duration = None
    if 'duration' in track_info:
        try:
            duration = int(track_info['duration']) // 1000  # Convertir de ms a segundos
        except (ValueError, TypeError):
            pass
    
    # Intentar obtener duración de MusicBrainz
    if mb_track and 'length' in mb_track:
        try:
            # MusicBrainz almacena duración en milisegundos
            mb_duration = int(mb_track['length']) // 1000
            if mb_duration > 0:
                duration = mb_duration
                print(f"Usando duración de MusicBrainz: {duration} segundos")
        except (ValueError, TypeError):
            pass
    
    # Obtener información del álbum y artista
    album_name = ''
    artist_name = ''
    
    if 'album' in track_info and 'title' in track_info['album']:
        album_name = track_info['album']['title']
    
    if 'artist' in track_info and 'name' in track_info['artist']:
        artist_name = track_info['artist']['name']
    
    # Intentar obtener artista de MusicBrainz
    if mb_track and 'artist-credit' in mb_track and mb_track['artist-credit']:
        mb_artist_name = mb_track['artist-credit'][0].get('artist', {}).get('name')
        if mb_artist_name:
            artist_name = mb_artist_name
            print(f"Usando artista de MusicBrainz: {artist_name}")
    
    # Géneros (tags)
    genre = ''
    if 'toptags' in track_info and 'tag' in track_info['toptags']:
        tags = track_info['toptags']['tag']
        if isinstance(tags, list) and tags:
            genre = tags[0]['name']
        elif isinstance(tags, dict):
            genre = tags.get('name', '')
    
    # Intentar obtener géneros de MusicBrainz
    if mb_track and 'tag-list' in mb_track and mb_track['tag-list']:
        mb_genres = [tag['name'] for tag in mb_track['tag-list']]
        if mb_genres:
            genre = mb_genres[0]  # Usar el primer género
            print(f"Usando género de MusicBrainz: {genre}")
    
    # Fecha actual para campos de tiempo
    now = datetime.datetime.now()
    added_timestamp = int(time.time())
    added_week = now.isocalendar()[1]
    added_month = now.month
    added_year = now.year
    
    # Obtener nombres reales de álbum y artista para mostrarlos en modo interactivo
    album_real_name = None
    artist_real_name = None
    
    if interactive:
        try:
            if artist_id:
                cursor.execute("SELECT name FROM artists WHERE id = ?", (artist_id,))
                result = cursor.fetchone()
                if result:
                    artist_real_name = result[0]
            
            if album_id:
                cursor.execute("SELECT name FROM albums WHERE id = ?", (album_id,))
                result = cursor.fetchone()
                if result:
                    album_real_name = result[0]
        except sqlite3.Error as e:
            print(f"Error al obtener información de referencias: {e}")
    
    if interactive:
        print("\n" + "="*60)
        print(f"INFORMACIÓN DE LA CANCIÓN A AÑADIR:")
        print("="*60)
        print(f"Título: {track_name}")
        print(f"Artista: {artist_real_name or artist_name} (ID: {artist_id})")
        print(f"Álbum: {album_real_name or album_name} (ID: {album_id})")
        print(f"MBID: {mbid}")
        print(f"Duración: {duration} segundos")
        print(f"Género: {genre}")
        print(f"Origen de datos: {'MusicBrainz+LastFM' if mb_track else 'LastFM'}")
        print("-"*60)
        print("Columnas a insertar en la tabla 'songs':")
        print("-"*60)
        print(f"title = '{track_name}'")
        print(f"mbid = '{mbid}'")
        print(f"added_timestamp = {added_timestamp}")
        print(f"added_week = {added_week}")
        print(f"added_month = {added_month}")
        print(f"added_year = {added_year}")
        print(f"duration = {duration}")
        print(f"album = '{album_name}'")
        print(f"album_artist = '{artist_name}'")
        print(f"artist = '{artist_name}'")
        print(f"genre = '{genre}'")
        print(f"origen = '{'musicbrainz+online' if mb_track else 'online'}'")
        print("="*60)
        
        respuesta = input("\n¿Añadir esta canción a la base de datos? (s/n): ").lower()
        if respuesta != 's':
            print("Operación cancelada por el usuario.")
            return None
    
    try:
        cursor.execute("""
            INSERT INTO songs 
            (title, mbid, added_timestamp, added_week, added_month, added_year, 
             duration, album, album_artist, artist, genre, origen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """, (
            track_name, 
            mbid, 
            added_timestamp, 
            added_week, 
            added_month, 
            added_year,
            duration, 
            album_name, 
            artist_name, 
            artist_name, 
            genre, 
            'musicbrainz+online' if mb_track else 'online'
        ))
        
        song_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Canción añadida con ID: {song_id}")
        return song_id
    except sqlite3.Error as e:
        print(f"Error al añadir la canción {track_name}: {e}")
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
                cached_data = lastfm_cache.get('user.getrecenttracks', params)
        
        if cached_data:
            print(f"Usando datos en caché para página {page} de scrobbles")
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
                    lastfm_cache.put('user.getrecenttracks', params, data)
                
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

def search_related_elements(conn, scrobble_info):
    """
    Busca elementos relacionados en la base de datos cuando hay coincidencias parciales
    
    Args:
        conn: Conexión a la base de datos
        scrobble_info: Diccionario con información del scrobble
        
    Returns:
        Diccionario con elementos relacionados
    """
    cursor = conn.cursor()
    results = {
        'related_songs': [],
        'related_albums': [],
        'related_artists': []
    }
    
    artist_name = scrobble_info['artist_name']
    album_name = scrobble_info['album_name']
    track_name = scrobble_info['track_name']
    
    # Si coincide artista y álbum pero no canción, buscar todas las canciones de ese álbum
    if scrobble_info['artist_match'] and scrobble_info['album_match'] and not scrobble_info['song_match']:
        cursor.execute("""
            SELECT s.id, s.title, s.lastfm_url 
            FROM songs s
            JOIN artists a ON LOWER(s.artist) = LOWER(a.name)
            JOIN albums al ON LOWER(s.album) = LOWER(al.name) AND al.artist_id = a.id
            WHERE LOWER(a.name) = LOWER(?) AND LOWER(al.name) = LOWER(?)
            ORDER BY s.title
        """, (artist_name, album_name))
        
        results['related_songs'] = cursor.fetchall()
    
    # Si coincide artista y canción pero no álbum, buscar álbumes que contengan esa canción
    if scrobble_info['artist_match'] and scrobble_info['song_match'] and not scrobble_info['album_match'] and album_name:
        cursor.execute("""
            SELECT al.id, al.name, al.lastfm_url
            FROM albums al
            JOIN artists a ON al.artist_id = a.id
            JOIN songs s ON LOWER(s.album) = LOWER(al.name) AND LOWER(s.artist) = LOWER(a.name)
            WHERE LOWER(a.name) = LOWER(?) AND LOWER(s.title) = LOWER(?)
            ORDER BY al.name
        """, (artist_name, track_name))
        
        results['related_albums'] = cursor.fetchall()
    
    # Si coincide álbum y canción pero no artista, buscar artistas relacionados
    if scrobble_info['album_match'] and scrobble_info['song_match'] and not scrobble_info['artist_match']:
        cursor.execute("""
            SELECT a.id, a.name, a.lastfm_url
            FROM artists a
            JOIN albums al ON al.artist_id = a.id
            JOIN songs s ON LOWER(s.album) = LOWER(al.name) AND LOWER(s.artist) = LOWER(a.name)
            WHERE LOWER(s.title) = LOWER(?) AND LOWER(al.name) = LOWER(?)
            ORDER BY a.name
        """, (track_name, album_name))
        
        results['related_artists'] = cursor.fetchall()
    
    return results

def display_scrobble_info(scrobble_info, db_info, related_elements=None):
    """
    Muestra información detallada de un scrobble con coincidencias en la base de datos
    """
    artist_name = scrobble_info['artist_name']
    album_name = scrobble_info['album_name']
    track_name = scrobble_info['track_name']
    scrobble_date = scrobble_info['scrobble_date']
    lastfm_url = scrobble_info['lastfm_url']
    
    print("\n" + "="*80)
    print(f"INFORMACIÓN DEL SCROBBLE")
    print("="*80)
    
    # Información de la canción
    print(f"Canción: {track_name}")
    if db_info['song_id']:
        print(f"  ID en base de datos: {db_info['song_id']}")
        if db_info['song_lastfm_url']:
            print(f"  Last.fm URL (DB): {db_info['song_lastfm_url']}")
    print(f"  Last.fm URL (scrobble): {lastfm_url}")
    
    # Información del artista
    print(f"Artista: {artist_name}")
    if db_info['artist_id']:
        print(f"  ID en base de datos: {db_info['artist_id']}")
        if db_info['artist_lastfm_url']:
            print(f"  Last.fm URL (DB): {db_info['artist_lastfm_url']}")
    
    # Información del álbum
    if album_name:
        print(f"Álbum: {album_name}")
        if db_info['album_id']:
            print(f"  ID en base de datos: {db_info['album_id']}")
            if db_info['album_lastfm_url']:
                print(f"  Last.fm URL (DB): {db_info['album_lastfm_url']}")
    
    # Fecha del scrobble
    print(f"Fecha: {scrobble_date}")
    
    # Mostrar elementos relacionados si hay coincidencias parciales
    if related_elements:
        print("\n" + "-"*80)
        print("ELEMENTOS RELACIONADOS EN BASE DE DATOS")
        print("-"*80)
        
        # Mostrar canciones relacionadas
        if related_elements['related_songs']:
            print("\nCanciones en este álbum:")
            for idx, (song_id, song_title, song_url) in enumerate(related_elements['related_songs']):
                print(f"  [{idx+1}] {song_title} (ID: {song_id})")
                if song_url:
                    print(f"      URL: {song_url}")
        
        # Mostrar álbumes relacionados
        if related_elements['related_albums']:
            print("\nÁlbumes con esta canción:")
            for idx, (album_id, album_name, album_url) in enumerate(related_elements['related_albums']):
                print(f"  [{idx+1}] {album_name} (ID: {album_id})")
                if album_url:
                    print(f"      URL: {album_url}")
        
        # Mostrar artistas relacionados
        if related_elements['related_artists']:
            print("\nArtistas con esta canción/álbum:")
            for idx, (artist_id, artist_name, artist_url) in enumerate(related_elements['related_artists']):
                print(f"  [{idx+1}] {artist_name} (ID: {artist_id})")
                if artist_url:
                    print(f"      URL: {artist_url}")
    
    print("-"*80)

def process_scrobbles(conn, tracks, existing_artists, existing_albums, existing_songs, lastfm_api_key, interactive=False, callback=None):
    """Procesa los scrobbles y actualiza la base de datos con los nuevos scrobbles,
    priorizando datos de la base de datos y MusicBrainz"""
    cursor = conn.cursor()
    processed_count = 0
    linked_count = 0
    unlinked_count = 0
    newest_timestamp = 0
    
    # Variables para estadísticas
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
    
    # Clasificar scrobbles
    matched_scrobbles = []
    new_scrobbles = []
    partial_matches = []
    
    print("\nAnalizando scrobbles para clasificación...")
    for track_idx, track in enumerate(tracks):
        # Extraer información básica
        artist_name = track['artist']['#text']
        album_name = track['album']['#text'] if track['album']['#text'] else None
        track_name = track['name']
        
        # Verificar coincidencias en base de datos
        artist_match = False
        album_match = False
        song_match = False
        
        # Buscar artista
        artist_info = existing_artists.get(artist_name.lower())
        if artist_info:
            artist_match = True
        
        # Buscar álbum si hay artista
        if artist_match and album_name:
            album_key = (album_name.lower(), artist_name.lower())
            album_info = existing_albums.get(album_key)
            if album_info:
                album_match = True
        
        # Buscar canción
        song_key = (track_name.lower(), artist_name.lower(), album_name.lower() if album_name else None)
        song_info = existing_songs.get(song_key)
        if song_info:
            song_match = True
        
        # Clasificar el scrobble
        track_info = {
            'track': track,
            'index': track_idx,
            'artist_match': artist_match,
            'album_match': album_match,
            'song_match': song_match
        }
        
        if song_match:
            matched_scrobbles.append(track_info)
        elif not artist_match and not album_match:
            new_scrobbles.append(track_info)
        else:
            partial_matches.append(track_info)
    
    # Mostrar resumen de la clasificación
    print("\n" + "="*80)
    print("RESUMEN DE SCROBBLES A PROCESAR")
    print("="*80)
    print(f"Total de scrobbles: {len(tracks)}")
    print(f"Scrobbles con coincidencia completa (canción): {len(matched_scrobbles)}")
    print(f"Scrobbles con coincidencia parcial (artista o álbum): {len(partial_matches)}")
    print(f"Scrobbles sin coincidencias en base de datos: {len(new_scrobbles)}")
    print("="*80)
    
    if interactive:
        print("\nElija por dónde empezar el procesamiento:")
        print("1. Scrobbles con coincidencia completa")
        print("2. Scrobbles con coincidencia parcial")
        print("3. Scrobbles sin coincidencias")
        print("4. Todos en orden original")
        
        choice = input("\nIngrese su elección (1-4): ").strip()
        
        if choice == '1':
            process_order = matched_scrobbles + partial_matches + new_scrobbles
            print(f"\nProcesando primero {len(matched_scrobbles)} scrobbles con coincidencia completa...")
        elif choice == '2':
            process_order = partial_matches + new_scrobbles + matched_scrobbles
            print(f"\nProcesando primero {len(partial_matches)} scrobbles con coincidencia parcial...")
        elif choice == '3':
            process_order = new_scrobbles + partial_matches + matched_scrobbles
            print(f"\nProcesando primero {len(new_scrobbles)} scrobbles sin coincidencias...")
        else:
            # Usar el orden original
            process_order = [{'track': track, 'index': idx} for idx, track in enumerate(tracks)]
            print(f"\nProcesando todos los {len(tracks)} scrobbles en orden original...")
    else:
        # Modo no interactivo, usar orden original
        process_order = [{'track': track, 'index': idx} for idx, track in enumerate(tracks)]
    
    # Indicador de modo automático
    auto_mode = not interactive
    
    # Procesar cada scrobble
    for idx, scrobble_info in enumerate(process_order):
        track = scrobble_info['track']
        
        # Extraer información del track
        artist_name = track['artist']['#text']
        album_name = track['album']['#text'] if track['album']['#text'] else None
        track_name = track['name']
        timestamp = int(track['date']['uts'])
        scrobble_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        lastfm_url = track['url']
        
        artist_mbid = track['artist'].get('mbid', '')
        
        # Actualizar el timestamp más reciente
        newest_timestamp = max(newest_timestamp, timestamp)
        
        # Verificar si el scrobble ya existe
        cursor.execute("SELECT id FROM scrobbles WHERE timestamp = ? AND artist_name = ? AND track_name = ?", 
                     (timestamp, artist_name, track_name))
        if cursor.fetchone():
            if not auto_mode:
                print(f"Scrobble duplicado, saltando: {track_name} - {artist_name}")
            continue
        
        # Obtener información de coincidencias para mostrar
        artist_id = None
        album_id = None
        song_id = None
        artist_lastfm_url = None
        album_lastfm_url = None
        song_lastfm_url = None
        
        # Información del artista
        artist_info = existing_artists.get(artist_name.lower())
        if artist_info:
            if isinstance(artist_info, dict):
                artist_id = artist_info['id']
                # Obtener URL si está disponible
                cursor.execute("SELECT lastfm_url FROM artists WHERE id = ?", (artist_id,))
                result = cursor.fetchone()
                if result:
                    artist_lastfm_url = result[0]
            else:
                artist_id = artist_info
        
        # Información del álbum
        if album_name:
            album_key = (album_name.lower(), artist_name.lower())
            album_info = existing_albums.get(album_key)
            if album_info:
                if isinstance(album_info, dict):
                    album_id = album_info['id']
                elif isinstance(album_info, tuple):
                    album_id = album_info[0]
                else:
                    album_id = album_info
                
                # Obtener URL si está disponible
                cursor.execute("SELECT lastfm_url FROM albums WHERE id = ?", (album_id,))
                result = cursor.fetchone()
                if result:
                    album_lastfm_url = result[0]
        
        # Información de la canción
        song_key = (track_name.lower(), artist_name.lower(), album_name.lower() if album_name else None)
        song_info = existing_songs.get(song_key)
        if song_info:
            if isinstance(song_info, dict):
                song_id = song_info['id']
            else:
                song_id = song_info
                
            # Obtener URL si está disponible
            cursor.execute("""
                SELECT sl.lastfm_url 
                FROM song_links sl 
                WHERE sl.song_id = ? 
            """, (song_id,))
            result = cursor.fetchone()
            if result:
                song_lastfm_url = result[0]
        
        # Determinar coincidencias para este scrobble específico
        artist_match = artist_id is not None
        album_match = album_id is not None
        song_match = song_id is not None
        
        # Preparar información para mostrar
        scrobble_display_info = {
            'artist_name': artist_name,
            'album_name': album_name,
            'track_name': track_name,
            'scrobble_date': scrobble_date,
            'lastfm_url': lastfm_url,
            'artist_match': artist_match,
            'album_match': album_match,
            'song_match': song_match
        }
        
        db_display_info = {
            'artist_id': artist_id,
            'album_id': album_id,
            'song_id': song_id,
            'artist_lastfm_url': artist_lastfm_url,
            'album_lastfm_url': album_lastfm_url,
            'song_lastfm_url': song_lastfm_url
        }
        
        # En modo interactivo, mostrar información y preguntar si procesar
        process_this_scrobble = True
        
        if interactive and not auto_mode:
            # Buscar elementos relacionados si hay coincidencias parciales
            related_elements = None
            if (artist_match and album_match and not song_match) or \
               (artist_match and song_match and not album_match) or \
               (album_match and song_match and not artist_match):
                related_elements = search_related_elements(conn, scrobble_display_info)
            
            # Mostrar información detallada del scrobble
            display_scrobble_info(scrobble_display_info, db_display_info, related_elements)
            
            # Si hay elementos relacionados, permitir seleccionar
            selected_song_id = song_id
            selected_album_id = album_id
            selected_artist_id = artist_id
            
            if related_elements:
                # Preguntar por canciones relacionadas
                if related_elements['related_songs'] and not song_match:
                    print("\nSeleccione una canción de la lista (0 para ninguna):")
                    choice = input("Número de canción: ").strip()
                    try:
                        choice_idx = int(choice) - 1
                        if choice_idx >= 0 and choice_idx < len(related_elements['related_songs']):
                            selected_song_id = related_elements['related_songs'][choice_idx][0]
                            print(f"Canción seleccionada con ID: {selected_song_id}")
                    except ValueError:
                        pass
                
                # Preguntar por álbumes relacionados
                if related_elements['related_albums'] and not album_match:
                    print("\nSeleccione un álbum de la lista (0 para ninguno):")
                    choice = input("Número de álbum: ").strip()
                    try:
                        choice_idx = int(choice) - 1
                        if choice_idx >= 0 and choice_idx < len(related_elements['related_albums']):
                            selected_album_id = related_elements['related_albums'][choice_idx][0]
                            print(f"Álbum seleccionado con ID: {selected_album_id}")
                    except ValueError:
                        pass
                
                # Preguntar por artistas relacionados
                if related_elements['related_artists'] and not artist_match:
                    print("\nSeleccione un artista de la lista (0 para ninguno):")
                    choice = input("Número de artista: ").strip()
                    try:
                        choice_idx = int(choice) - 1
                        if choice_idx >= 0 and choice_idx < len(related_elements['related_artists']):
                            selected_artist_id = related_elements['related_artists'][choice_idx][0]
                            print(f"Artista seleccionado con ID: {selected_artist_id}")
                    except ValueError:
                        pass
            
            # Preguntar si procesar este scrobble
            respuesta = input("\n¿Procesar este scrobble? (s/n/q para salir/a para modo automático): ").lower()
            if respuesta == 'q':
                print("Interrumpiendo procesamiento por solicitud del usuario.")
                break
            elif respuesta == 'a':
                auto_mode = True
                print("Cambiando a modo automático para el resto del procesamiento.")
            elif respuesta != 's':
                print("Saltando este scrobble.")
                process_this_scrobble = False
            
            # Actualizar IDs con las selecciones del usuario
            if process_this_scrobble:
                artist_id = selected_artist_id
                album_id = selected_album_id
                song_id = selected_song_id
        
        # Si no se va a procesar, continuar con el siguiente
        if not process_this_scrobble:
            continue
        
        # Si no tenemos artista en la base de datos, intentar encontrarlo o crearlo
        if artist_id is None:
            new_artists_attempts += 1
            artist_id = get_or_update_artist(conn, artist_name, artist_mbid, interactive and not auto_mode)
            
            if artist_id:
                new_artists[artist_name.lower()] = artist_id
                existing_artists[artist_name.lower()] = {'id': artist_id, 'origen': 'musicbrainz'}
                new_artists_success += 1
            else:
                errors['artist_not_found'] += 1
        
        # Si no tenemos álbum en la base de datos, intentar encontrarlo o crearlo
        if album_name and artist_id and album_id is None:
            album_mbid = track['album'].get('mbid', '')
            new_albums_attempts += 1
            album_id = get_or_update_album(conn, album_name, artist_name, artist_id, album_mbid, interactive and not auto_mode)
            
            if album_id:
                album_key = (album_name.lower(), artist_name.lower())
                new_albums[album_key] = album_id
                existing_albums[album_key] = {'id': album_id, 'artist_id': artist_id, 'origen': 'musicbrainz'}
                new_albums_success += 1
            else:
                errors['album_not_found'] += 1
        
        # Si no tenemos canción en la base de datos, intentar encontrarla o crearla
        if artist_id and song_id is None:
            track_mbid = track.get('mbid', '')
            new_songs_attempts += 1
            song_id = get_or_update_song(conn, track_name, artist_name, album_name, artist_id, album_id, track_mbid, interactive and not auto_mode)
            
            if song_id:
                song_key = (track_name.lower(), artist_name.lower(), album_name.lower() if album_name else None)
                new_songs[song_key] = song_id
                existing_songs[song_key] = {'id': song_id, 'origen': 'musicbrainz'}
                new_songs_success += 1
            else:
                errors['song_not_found'] += 1
        
        # Insertar el scrobble
        try:
            cursor.execute("""
                INSERT INTO scrobbles 
                (track_name, album_name, artist_name, timestamp, scrobble_date, lastfm_url, song_id, album_id, artist_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (track_name, album_name, artist_name, timestamp, scrobble_date, lastfm_url, song_id, album_id, artist_id))
            
            processed_count += 1
            
            # Contabilizar si se pudo enlazar con la base de datos
            if song_id:
                linked_count += 1
                if not auto_mode:
                    print(f"Scrobble enlazado correctamente con song_id: {song_id}")
            else:
                unlinked_count += 1
                if not auto_mode:
                    print(f"Scrobble guardado pero sin enlazar a una canción")
                    
            # Commit periódico para guardar avances
            if processed_count % 10 == 0:
                conn.commit()
                if not auto_mode:
                    print(f"Progreso guardado: {processed_count} scrobbles procesados hasta ahora.")
        
        except sqlite3.Error as e:
            print(f"Error al insertar scrobble en la base de datos: {e}")
            errors['db_errors'] += 1
        
        # Cada 10 scrobbles, preguntar si continuar o cambiar a modo automático
        if interactive and not auto_mode and (idx + 1) % 10 == 0:
            continue_processing, switch_to_auto = ask_to_continue()
            if not continue_processing:
                print("Procesamiento interrumpido por el usuario.")
                break
            if switch_to_auto:
                auto_mode = True
                print("Cambiando a modo automático para el resto del procesamiento.")
    
    # Commit final para asegurar que todo quede guardado
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


def search_related_elements(conn, scrobble_info):
    """
    Busca elementos relacionados en la base de datos cuando hay coincidencias parciales
    
    Args:
        conn: Conexión a la base de datos
        scrobble_info: Diccionario con información del scrobble
        
    Returns:
        Diccionario con elementos relacionados
    """
    cursor = conn.cursor()
    results = {
        'related_songs': [],
        'related_albums': [],
        'related_artists': []
    }
    
    artist_name = scrobble_info['artist_name']
    album_name = scrobble_info['album_name']
    track_name = scrobble_info['track_name']
    
    # Si coincide artista y álbum pero no canción, buscar todas las canciones de ese álbum
    if scrobble_info['artist_match'] and scrobble_info['album_match'] and not scrobble_info['song_match']:
        cursor.execute("""
            SELECT s.id, s.title, s.lastfm_url 
            FROM songs s
            JOIN artists a ON LOWER(s.artist) = LOWER(a.name)
            JOIN albums al ON LOWER(s.album) = LOWER(al.name) AND al.artist_id = a.id
            WHERE LOWER(a.name) = LOWER(?) AND LOWER(al.name) = LOWER(?)
            ORDER BY s.title
        """, (artist_name, album_name))
        
        results['related_songs'] = cursor.fetchall()
    
    # Si coincide artista y canción pero no álbum, buscar álbumes que contengan esa canción
    if scrobble_info['artist_match'] and scrobble_info['song_match'] and not scrobble_info['album_match'] and album_name:
        cursor.execute("""
            SELECT al.id, al.name, al.lastfm_url
            FROM albums al
            JOIN artists a ON al.artist_id = a.id
            JOIN songs s ON LOWER(s.album) = LOWER(al.name) AND LOWER(s.artist) = LOWER(a.name)
            WHERE LOWER(a.name) = LOWER(?) AND LOWER(s.title) = LOWER(?)
            ORDER BY al.name
        """, (artist_name, track_name))
        
        results['related_albums'] = cursor.fetchall()
    
    # Si coincide álbum y canción pero no artista, buscar artistas relacionados
    if scrobble_info['album_match'] and scrobble_info['song_match'] and not scrobble_info['artist_match']:
        cursor.execute("""
            SELECT a.id, a.name, a.lastfm_url
            FROM artists a
            JOIN albums al ON al.artist_id = a.id
            JOIN songs s ON LOWER(s.album) = LOWER(al.name) AND LOWER(s.artist) = LOWER(a.name)
            WHERE LOWER(s.title) = LOWER(?) AND LOWER(al.name) = LOWER(?)
            ORDER BY a.name
        """, (track_name, album_name))
        
        results['related_artists'] = cursor.fetchall()
    
    return results

def display_scrobble_info(scrobble_info, db_info, related_elements=None):
    """
    Muestra información detallada de un scrobble con coincidencias en la base de datos
    """
    artist_name = scrobble_info['artist_name']
    album_name = scrobble_info['album_name']
    track_name = scrobble_info['track_name']
    scrobble_date = scrobble_info['scrobble_date']
    lastfm_url = scrobble_info['lastfm_url']
    
    print("\n" + "="*80)
    print(f"INFORMACIÓN DEL SCROBBLE")
    print("="*80)
    
    # Información de la canción
    print(f"Canción: {track_name}")
    if db_info['song_id']:
        print(f"  ID en base de datos: {db_info['song_id']}")
        if db_info['song_lastfm_url']:
            print(f"  Last.fm URL (DB): {db_info['song_lastfm_url']}")
    print(f"  Last.fm URL (scrobble): {lastfm_url}")
    
    # Información del artista
    print(f"Artista: {artist_name}")
    if db_info['artist_id']:
        print(f"  ID en base de datos: {db_info['artist_id']}")
        if db_info['artist_lastfm_url']:
            print(f"  Last.fm URL (DB): {db_info['artist_lastfm_url']}")
    
    # Información del álbum
    if album_name:
        print(f"Álbum: {album_name}")
        if db_info['album_id']:
            print(f"  ID en base de datos: {db_info['album_id']}")
            if db_info['album_lastfm_url']:
                print(f"  Last.fm URL (DB): {db_info['album_lastfm_url']}")
    
    # Fecha del scrobble
    print(f"Fecha: {scrobble_date}")
    
    # Mostrar elementos relacionados si hay coincidencias parciales
    if related_elements:
        print("\n" + "-"*80)
        print("ELEMENTOS RELACIONADOS EN BASE DE DATOS")
        print("-"*80)
        
        # Mostrar canciones relacionadas
        if related_elements['related_songs']:
            print("\nCanciones en este álbum:")
            for idx, (song_id, song_title, song_url) in enumerate(related_elements['related_songs']):
                print(f"  [{idx+1}] {song_title} (ID: {song_id})")
                if song_url:
                    print(f"      URL: {song_url}")
        
        # Mostrar álbumes relacionados
        if related_elements['related_albums']:
            print("\nÁlbumes con esta canción:")
            for idx, (album_id, album_name, album_url) in enumerate(related_elements['related_albums']):
                print(f"  [{idx+1}] {album_name} (ID: {album_id})")
                if album_url:
                    print(f"      URL: {album_url}")
        
        # Mostrar artistas relacionados
        if related_elements['related_artists']:
            print("\nArtistas con esta canción/álbum:")
            for idx, (artist_id, artist_name, artist_url) in enumerate(related_elements['related_artists']):
                print(f"  [{idx+1}] {artist_name} (ID: {artist_id})")
                if artist_url:
                    print(f"      URL: {artist_url}")
    
    print("-"*80)


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
        cached_result = lastfm_cache.get('album.getInfo', params)
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
            lastfm_cache.put('album.getInfo', params, data)
        
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



def update_song_links_from_albums(conn, lastfm_api_key, limit=50, progress_callback=None):
    """
    Busca álbumes con URL de Last.fm pero sin enlaces para sus canciones
    y actualiza la tabla song_links con los enlaces de Last.fm
    
    Args:
        conn: Conexión a la base de datos
        lastfm_api_key: API key de Last.fm
        limit: Límite de álbumes a procesar por ejecución
        progress_callback: Función para reportar progreso
    
    Returns:
        Tuple (álbumes procesados, canciones encontradas, canciones actualizadas)
    """
    cursor = conn.cursor()
    
    # Asegurar que la tabla song_links existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS song_links (
        id INTEGER PRIMARY KEY,
        song_id INTEGER,
        lastfm_url TEXT,
        FOREIGN KEY (song_id) REFERENCES songs(id)
    )
    """)
    
    # Crear índice para búsquedas eficientes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)")
    
    # Buscar álbumes con URL de Last.fm
    cursor.execute("""
    SELECT a.id, a.name, a.artist_id, ar.name as artist_name, a.lastfm_url
    FROM albums a
    JOIN artists ar ON a.artist_id = ar.id
    WHERE a.lastfm_url IS NOT NULL AND a.lastfm_url != ''
    ORDER BY a.id
    LIMIT ?
    """, (limit,))
    
    albums = cursor.fetchall()
    albums_processed = 0
    total_songs_found = 0
    songs_updated = 0
    
    for i, (album_id, album_name, artist_id, artist_name, lastfm_url) in enumerate(albums):
        if progress_callback:
            progress_callback(f"Procesando álbum {i+1}/{len(albums)}: {album_name}", 
                             (i / len(albums) * 100) if albums else 0)
        else:
            print(f"\nProcesando álbum {i+1}/{len(albums)}: {album_name} de {artist_name}")
        
        # Obtener canciones del álbum desde Last.fm
        tracks = get_tracks_from_lastfm_album(lastfm_url, lastfm_api_key)
        total_songs_found += len(tracks)
        
        if not tracks:
            print(f"  No se encontraron canciones para el álbum '{album_name}'")
            continue
        
        print(f"  Encontradas {len(tracks)} canciones para el álbum '{album_name}'")
        
        # Para cada canción, verificar si existe en la base de datos y actualizar el enlace
        for track in tracks:
            # Buscar la canción en la base de datos
            cursor.execute("""
            SELECT id FROM songs
            WHERE LOWER(title) = LOWER(?) AND LOWER(artist) = LOWER(?) AND LOWER(album) = LOWER(?)
            """, (track['name'], track['artist'], track['album']))
            
            song_result = cursor.fetchone()
            if not song_result:
                # Si no encontramos coincidencia exacta, intentar solo por título y artista
                cursor.execute("""
                SELECT id FROM songs
                WHERE LOWER(title) = LOWER(?) AND LOWER(artist) = LOWER(?)
                """, (track['name'], track['artist']))
                song_result = cursor.fetchone()
            
            if song_result:
                song_id = song_result[0]
                
                # Verificar si ya existe un enlace para esta canción
                cursor.execute("""
                SELECT id FROM song_links
                WHERE song_id = ? 
                """, (song_id,))
                
                if cursor.fetchone():
                    # Actualizar el enlace existente
                    cursor.execute("""
                    UPDATE song_links SET lastfm_url = ?
                    WHERE song_id = ? 
                    """, (track['lastfm_url'], song_id))
                else:
                    # Crear un nuevo enlace
                    cursor.execute("""
                    INSERT INTO song_links (song_id, lastfm_url)
                    VALUES (?, 'lastfm', ?)
                    """, (song_id, track['lastfm_url']))
                
                songs_updated += 1
        
        albums_processed += 1
    
    conn.commit()
    
    if progress_callback:
        progress_callback(f"Completado. {albums_processed} álbumes procesados, {songs_updated} canciones actualizadas", 100)
    else:
        print(f"\nCompletado. {albums_processed} álbumes procesados, {total_songs_found} canciones encontradas, {songs_updated} canciones actualizadas")
    
    return albums_processed, total_songs_found, songs_updated


def lookup_song_by_lastfm_url(conn, lastfm_url):
    """
    Busca una canción en la base de datos por su URL de Last.fm
    
    Args:
        conn: Conexión a la base de datos
        lastfm_url: URL de Last.fm para la canción
    
    Returns:
        (song_id, song_info) o (None, None) si no se encuentra
    """
    if not lastfm_url:
        return None, None
    
    cursor = conn.cursor()
    
    # Primero buscar en song_links
    cursor.execute("""
    SELECT sl.song_id, s.title, s.artist, s.album, s.mbid, s.origen
    FROM song_links sl
    JOIN songs s ON sl.song_id = s.id
    WHERE sl.lastfm_url = ? 
    """, (lastfm_url,))
    
    result = cursor.fetchone()
    if result:
        return result[0], {
            'id': result[0],
            'title': result[1],
            'artist': result[2],
            'album': result[3],
            'mbid': result[4],
            'origen': result[5]
        }
    
    return None, None

def lookup_album_by_lastfm_url(conn, lastfm_url):
    """
    Busca un álbum en la base de datos por su URL de Last.fm
    """
    if not lastfm_url:
        return None, None
    
    cursor = conn.cursor()
    
    # Verificar primero si la columna lastfm_url existe en la tabla albums
    cursor.execute("PRAGMA table_info(albums)")
    columns = cursor.fetchall()
    if not any(col[1] == 'lastfm_url' for col in columns):
        print("La tabla albums no tiene la columna 'lastfm_url'")
        return None, None
    
    # Ahora realizar la búsqueda
    cursor.execute("""
    SELECT a.id, a.mbid, a.name, a.artist_id, ar.name, a.origen
    FROM albums a
    JOIN artists ar ON a.artist_id = ar.id
    WHERE a.lastfm_url = ?
    """, (lastfm_url,))
    
    result = cursor.fetchone()
    if result:
        return result[0], {
            'id': result[0],
            'mbid': result[1],
            'name': result[2],
            'artist_id': result[3],
            'artist_name': result[4],
            'origen': result[5]
        }
    
    return None, None

def lookup_artist_by_lastfm_url(conn, lastfm_url):
    """
    Busca un artista en la base de datos por su URL de Last.fm
    
    Args:
        conn: Conexión a la base de datos
        lastfm_url: URL de Last.fm para el artista
    
    Returns:
        (artist_id, artist_info) o (None, None) si no se encuentra
    """
    if not lastfm_url:
        return None, None
    
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, mbid, name, origen
    FROM artists
    WHERE lastfm_url = ?
    """, (lastfm_url,))
    
    result = cursor.fetchone()
    if result:
        return result[0], {
            'id': result[0],
            'mbid': result[1],
            'name': result[2],
            'origen': "online"
        }
    
    return None, None



class LastFMScrobbler:
    def __init__(self, db_path, lastfm_user, lastfm_api_key, progress_callback=None, cache_dir=None):
        self.db_path = db_path
        self.lastfm_user = lastfm_user
        self.lastfm_api_key = lastfm_api_key
        self.conn = None
        self.existing_artists = {}
        self.existing_albums = {}
        self.existing_songs = {}
        self.progress_callback = progress_callback
        self._interactive_mode = False
        self._cache_dir = None  # Inicializar a None
        
        # Establecer cache_dir a través del setter
        if cache_dir:
            self.cache_dir = cache_dir
        
    @property
    def cache_dir(self):
        return self._cache_dir
        
    @cache_dir.setter
    def cache_dir(self, value):
        self._cache_dir = value
        if value:
            # Asegurarse de que setup_musicbrainz está accesible
            global setup_musicbrainz
            if 'setup_musicbrainz' in globals():
                setup_musicbrainz(value)
            else:
                print("ADVERTENCIA: setup_musicbrainz no está definido globalmente")
        
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
    
    def get_new_scrobbles(self, force_update=False, filter_duplicates=True):
            """Obtiene los nuevos scrobbles desde el último timestamp"""
            self.connect()
            from_timestamp = 0 if force_update else get_last_timestamp(self.conn)
            
            if from_timestamp > 0:
                date_str = datetime.datetime.fromtimestamp(from_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                self._update_progress(f"Obteniendo scrobbles desde {date_str}", 15)
            else:
                self._update_progress("Obteniendo todos los scrobbles (esto puede tardar)", 15)
                
            tracks = get_lastfm_scrobbles(self.lastfm_user, self.lastfm_api_key, from_timestamp, 
                                        progress_callback=self.progress_callback,
                                        filter_duplicates=filter_duplicates)
            
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
    
  
    def update_scrobbles(self, force_update=False, interactive=None, callback=None, use_mbid_lookups=True, filter_duplicates=True):
            """Actualiza los scrobbles desde Last.fm y los procesa"""
            if interactive is None:
                interactive = self.interactive_mode
            
            # Si force_update, primero limpiar la base de datos
            if force_update:
                if not self.force_update_database(interactive):
                    self._update_progress("Operación cancelada por el usuario", 0)
                    return 0, 0, 0, 0
            
            # Ahora obtener los nuevos scrobbles (desde cero si force_update era True)
            tracks, from_timestamp = self.get_new_scrobbles(force_update, filter_duplicates)
            if tracks:
                if use_mbid_lookups:
                    self._update_progress("Usando búsquedas por nombre y actualización con MBIDs", 35)
                return self.process_scrobbles_batch(tracks, interactive, callback)
            return 0, 0, 0, 0
    
    def merge_duplicates_by_mbid(conn):
        """Fusiona elementos duplicados identificados por MBID"""
        cursor = conn.cursor()
        
        # 1. Fusionar artistas con el mismo MBID
        print("Buscando artistas duplicados por MBID...")
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
            primary_id = int(ids[0])  # Usar el primer ID como principal
            
            print(f"Encontrados {count} artistas duplicados con MBID {mbid}. Fusionando en ID {primary_id}...")
            
            # Actualizar referencias en álbumes
            for other_id in ids[1:]:
                cursor.execute("UPDATE albums SET artist_id = ? WHERE artist_id = ?", (primary_id, other_id))
                
            # Actualizar referencias en scrobbles
            for other_id in ids[1:]:
                cursor.execute("UPDATE scrobbles SET artist_id = ? WHERE artist_id = ?", (primary_id, other_id))
            
            # Eliminar artistas duplicados
            for other_id in ids[1:]:
                try:
                    cursor.execute("DELETE FROM artists WHERE id = ?", (other_id,))
                except sqlite3.Error as e:
                    print(f"Error al eliminar artista duplicado {other_id}: {e}")
        
        # 2. Fusionar álbumes con el mismo MBID
        print("Buscando álbumes duplicados por MBID...")
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
            primary_id = int(ids[0])  # Usar el primer ID como principal
            
            print(f"Encontrados {count} álbumes duplicados con MBID {mbid}. Fusionando en ID {primary_id}...")
            
            # Actualizar referencias en scrobbles
            for other_id in ids[1:]:
                cursor.execute("UPDATE scrobbles SET album_id = ? WHERE album_id = ?", (primary_id, other_id))
            
            # Eliminar álbumes duplicados
            for other_id in ids[1:]:
                try:
                    cursor.execute("DELETE FROM albums WHERE id = ?", (other_id,))
                except sqlite3.Error as e:
                    print(f"Error al eliminar álbum duplicado {other_id}: {e}")
        
        # 3. Fusionar canciones con el mismo MBID
        print("Buscando canciones duplicadas por MBID...")
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
            primary_id = int(ids[0])  # Usar el primer ID como principal
            
            print(f"Encontradas {count} canciones duplicadas con MBID {mbid}. Fusionando en ID {primary_id}...")
            
            # Actualizar referencias en scrobbles
            for other_id in ids[1:]:
                cursor.execute("UPDATE scrobbles SET song_id = ? WHERE song_id = ?", (primary_id, other_id))
            
            # Eliminar canciones duplicadas
            for other_id in ids[1:]:
                try:
                    cursor.execute("DELETE FROM songs WHERE id = ?", (other_id,))
                except sqlite3.Error as e:
                    print(f"Error al eliminar canción duplicada {other_id}: {e}")
        
        conn.commit()
        
        return len(duplicated_artists), len(duplicated_albums), len(duplicated_songs)


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
       
        # Fusionar duplicados por MBID
        print("\nBuscando y fusionando elementos duplicados por MBID...")
        artists_merged, albums_merged, songs_merged = merge_duplicates_by_mbid(self.conn)
        
        print(f"Elementos fusionados: {artists_merged} artistas, {albums_merged} álbumes, {songs_merged} canciones")
        
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
                    'origen': 'online'
                }
            return None
        
        return {
            'id': result[0],
            'name': result[1],
            'mbid': result[2],
            'tags': result[3],
            'bio': result[4],
            'lastfm_url': result[5],
            'origen': "online"
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
                    'origen': 'online',
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
            'origen': "online",
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


    def force_update_database(self, interactive=None):
        """Elimina todos los scrobbles existentes para hacer una actualización completa."""
        if interactive is None:
            interactive = self.interactive_mode
            
        confirm = True
        if interactive:
            print("\n¡ATENCIÓN! Esta operación eliminará TODOS los scrobbles de la base de datos.")
            response = input("¿Está seguro de que desea eliminar TODOS los scrobbles existentes? (s/n): ").lower()
            confirm = response == 's'
            
        if confirm:
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM scrobbles")
            cursor.execute("UPDATE lastfm_config SET last_timestamp = 0 WHERE id = 1")
            self.conn.commit()
            self._update_progress("TODOS los scrobbles han sido eliminados. Se realizará una actualización completa.", 10)
            return True
        
        return False
class MusicBrainzCache:
    """
    Caché para consultas a la API de MusicBrainz.
    Almacena resultados para evitar peticiones repetidas.
    """
    
    def __init__(self, cache_file=None, cache_duration=30):
        """
        Inicializa el caché de MusicBrainz.
        
        Args:
            cache_file: Ruta al archivo para persistir el caché
            cache_duration: Duración del caché en días
        """
        self.cache = {}
        self.cache = CaseInsensitiveDict()  # Usar diccionario case-insensitive
        self.cache_file = cache_file
        self.cache_duration = cache_duration  # en días
        
        if cache_file and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    loaded_cache = json.load(f)
                    
                    # Filtrar entradas expiradas
                    now = time.time()
                    for key, entry in loaded_cache.items():
                        if 'timestamp' in entry:
                            age_days = (now - entry['timestamp']) / (60 * 60 * 24)
                            if age_days <= self.cache_duration:
                                self.cache[key] = entry
                        else:
                            # Si no tiene timestamp, asumimos que es reciente
                            self.cache[key] = entry
                            
                print(f"MusicBrainzCache: Cargadas {len(self.cache)} entradas válidas de {len(loaded_cache)} totales")
            except Exception as e:
                print(f"Error al cargar archivo de caché de MusicBrainz: {e}")
                # Iniciar con caché vacío si hay error
                self.cache = {}
    
    def get(self, query_type, query_id=None, query_params=None):
        """
        Obtiene un resultado desde el caché si está disponible y no ha expirado.
        
        Args:
            query_type: Tipo de consulta (artist, release, recording, etc)
            query_id: ID para búsquedas directas
            query_params: Parámetros para búsquedas por parámetros
            
        Returns:
            Datos en caché o None si no existe o expiró
        """
        cache_key = self._make_key(query_type, query_id, query_params)
        entry = self.cache.get(cache_key)
        
        if not entry:
            return None
            
        # Verificar expiración
        if 'timestamp' in entry:
            age_days = (time.time() - entry['timestamp']) / (60 * 60 * 24)
            if age_days > self.cache_duration:
                # Expirado, eliminar y retornar None
                del self.cache[cache_key]
                return None
        
        return entry.get('data')
    
    def put(self, query_type, result, query_id=None, query_params=None):
        """
        Almacena un resultado en el caché.
        
        Args:
            query_type: Tipo de consulta
            result: Resultado a almacenar
            query_id: ID para búsquedas directas
            query_params: Parámetros para búsquedas por parámetros
        """
        cache_key = self._make_key(query_type, query_id, query_params)
        
        # Almacenar con timestamp para expiración
        self.cache[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }
        
        # Guardar en archivo si está configurado
        self._save_cache()
    
    def clear(self, save=True):
        """Limpia todo el caché"""
        self.cache = {}
        if save and self.cache_file:
            self._save_cache()
    
    def _save_cache(self):
        """Guarda el caché a disco si hay archivo configurado"""
        if not self.cache_file:
            return
            
        try:
            # Crear directorio si no existe
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
                
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar archivo de caché de MusicBrainz: {e}")
    
    def _make_key(self, query_type, query_id=None, query_params=None):
        """
        Crea una clave única para el caché a partir de los parámetros.
        
        Args:
            query_type: Tipo de consulta (artist, release, recording)
            query_id: ID para búsquedas directas
            query_params: Parámetros para búsquedas por nombre, etc.
            
        Returns:
            String único que identifica la consulta
        """
        if query_id:
            return f"{query_type}:id:{query_id}"
        elif query_params:
            # Convertir params a representación estable
            if isinstance(query_params, dict):
                # Ordenar keys para consistencia
                param_str = json.dumps(query_params, sort_keys=True)
            else:
                param_str = str(query_params)
            
            # Usar hash para claves muy largas
            if len(param_str) > 200:
                import hashlib
                param_hash = hashlib.md5(param_str.encode('utf-8')).hexdigest()
                return f"{query_type}:params:{param_hash}"
            else:
                return f"{query_type}:params:{param_str}"
        
        return f"{query_type}:generic"


class LastFMCache:
    """
    Caché para consultas a la API de Last.fm.
    Similar al caché de MusicBrainz pero adaptado a las particularidades de Last.fm.
    """
    
    def __init__(self, cache_file=None, cache_duration=7):
        """
        Inicializa el caché de Last.fm.
        
        Args:
            cache_file: Ruta al archivo para persistir el caché
            cache_duration: Duración del caché en días (más corto que MusicBrainz)
        """
        self.cache = {}
        self.cache = CaseInsensitiveDict()  # Usar diccionario case-insensitive
        self.cache_file = cache_file
        self.cache_duration = cache_duration  # en días
        
        if cache_file and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    loaded_cache = json.load(f)
                    
                    # Filtrar entradas expiradas
                    now = time.time()
                    for key, entry in loaded_cache.items():
                        if 'timestamp' in entry:
                            age_days = (now - entry['timestamp']) / (60 * 60 * 24)
                            if age_days <= self.cache_duration:
                                self.cache[key] = entry
                        else:
                            # Si no tiene timestamp, asumimos que es reciente
                            self.cache[key] = entry
                            
                print(f"LastFMCache: Cargadas {len(self.cache)} entradas válidas de {len(loaded_cache)} totales")
            except Exception as e:
                print(f"Error al cargar archivo de caché de Last.fm: {e}")
                # Iniciar con caché vacío si hay error
                self.cache = {}
    
    def get(self, method, params):
        """
        Obtiene un resultado desde el caché si está disponible y no ha expirado.
        
        Args:
            method: Método de la API (artist.getInfo, album.getInfo, etc)
            params: Diccionario con parámetros de la consulta
            
        Returns:
            Datos en caché o None si no existe o expiró
        """
        # Para Last.fm, ignoramos api_key en la clave de caché
        filtered_params = {k: v for k, v in params.items() if k != 'api_key'}
        cache_key = self._make_key(method, filtered_params)
        
        entry = self.cache.get(cache_key)
        
        if not entry:
            return None
            
        # Verificar expiración
        if 'timestamp' in entry:
            age_days = (time.time() - entry['timestamp']) / (60 * 60 * 24)
            if age_days > self.cache_duration:
                # Expirado, eliminar y retornar None
                del self.cache[cache_key]
                return None
        
        return entry.get('data')
    
    def put(self, method, params, result):
        """
        Almacena un resultado en el caché.
        
        Args:
            method: Método de la API
            params: Parámetros de la consulta
            result: Resultado a almacenar
        """
        # Ignorar api_key en la clave de caché
        filtered_params = {k: v for k, v in params.items() if k != 'api_key'}
        cache_key = self._make_key(method, filtered_params)
        
        # No almacenar respuestas de error
        if isinstance(result, dict) and 'error' in result:
            return
        
        # Almacenar con timestamp para expiración
        self.cache[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }
        
        # Guardar en archivo si está configurado
        self._save_cache()
    
    def clear(self, save=True):
        """Limpia todo el caché"""
        self.cache = {}
        if save and self.cache_file:
            self._save_cache()
    
    def _save_cache(self):
        """Guarda el caché a disco si hay archivo configurado"""
        if not self.cache_file:
            return
            
        try:
            # Crear directorio si no existe
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
                
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar archivo de caché de Last.fm: {e}")
    
    def _make_key(self, method, params):
        """
        Crea una clave única para el caché a partir de los parámetros.
        
        Args:
            method: Método de la API
            params: Diccionario con parámetros
            
        Returns:
            String único que identifica la consulta
        """
        # Convertir params a representación estable
        param_str = json.dumps(params, sort_keys=True)
        
        # Usar hash para claves muy largas
        if len(param_str) > 200:
            import hashlib
            param_hash = hashlib.md5(param_str.encode('utf-8')).hexdigest()
            return f"{method}:{param_hash}"
        else:
            return f"{method}:{param_str}"


class CaseInsensitiveDict(dict):
    """Diccionario con claves insensibles a mayúsculas/minúsculas"""
    
    def __init__(self, *args, **kwargs):
        super(CaseInsensitiveDict, self).__init__(*args, **kwargs)
        self._convert_keys()
    
    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower() if isinstance(key, str) else key)
    
    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower() if isinstance(key, str) else key, value)
    
    def __delitem__(self, key):
        return super(CaseInsensitiveDict, self).__delitem__(key.lower() if isinstance(key, str) else key)
    
    def __contains__(self, key):
        return super(CaseInsensitiveDict, self).__contains__(key.lower() if isinstance(key, str) else key)
    
    def get(self, key, default=None):
        return super(CaseInsensitiveDict, self).get(key.lower() if isinstance(key, str) else key, default)
    
    def _convert_keys(self):
        for key in list(self.keys()):
            if isinstance(key, str):
                value = super(CaseInsensitiveDict, self).pop(key)
                self[key.lower()] = value


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
    parser.add_argument('--cache-dir', type=str, help='Directorio para archivos de caché')
            
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
    
    # Directorio de caché - Asegúrate de que este valor se defina
    cache_dir = args.cache_dir or config.get('cache_dir', '.content/cache/api_cache')
    
    # Check for force_update in multiple places
    global FORCE_UPDATE
    force_update = args.force_update or config.get('force_update', False) or FORCE_UPDATE
    interactive = args.interactive or config.get('interactive', False) or INTERACTIVE_MODE

    print(f"Modo force_update: {force_update}")
    print(f"Modo interactive: {interactive}")
    
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
    scrobbler.cache_dir = cache_dir  # Asignar cache_dir al scrobbler
    
    # Aplicar force_update si es necesario
    if force_update:
        handle_force_update(db_path)
    
    # Obtener y procesar scrobbles
    return scrobbler.update_scrobbles(force_update=force_update)

if __name__ != "__main__" and FORCE_UPDATE:
    # We are being imported as a module, try to find db_path from globals
    try:
        db_path = None
        if 'CONFIG' in globals():
            db_path = CONFIG.get('db_path')
        if not db_path and 'filtered_config' in globals():
            db_path = filtered_config.get('db_path')
        
        if db_path:
            print(f"Módulo importado con FORCE_UPDATE=True, limpiando base de datos: {db_path}")
            handle_force_update(db_path)
    except Exception as e:
        print(f"Error al intentar manejar force_update al importar el módulo: {e}")