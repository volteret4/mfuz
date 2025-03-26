import sqlite3
import argparse
import json
import os
import webbrowser
import datetime
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
import subprocess

sqlite3.register_adapter(datetime.datetime, lambda dt: dt.isoformat())

def init_database(db_path):
    """Inicializa la base de datos añadiendo las columnas necesarias si no existen"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Comprobamos si las columnas existen en la tabla artists
    cursor.execute("PRAGMA table_info(artists)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'wikipedia_url' not in column_names:
        cursor.execute("ALTER TABLE artists ADD COLUMN wikipedia_url TEXT")
        print("Columna 'wikipedia_url' añadida a la tabla 'artists'")
    
    if 'wikipedia_content' not in column_names:
        cursor.execute("ALTER TABLE artists ADD COLUMN wikipedia_content TEXT")
        print("Columna 'wikipedia_content' añadida a la tabla 'artists'")
    
    if 'wikipedia_updated' not in column_names:
        cursor.execute("ALTER TABLE artists ADD COLUMN wikipedia_updated TIMESTAMP")
        print("Columna 'wikipedia_updated' añadida a la tabla 'artists'")
    
    # Comprobamos si las columnas existen en la tabla albums
    cursor.execute("PRAGMA table_info(albums)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'wikipedia_url' not in column_names:
        cursor.execute("ALTER TABLE albums ADD COLUMN wikipedia_url TEXT")
        print("Columna 'wikipedia_url' añadida a la tabla 'albums'")
    
    if 'wikipedia_content' not in column_names:
        cursor.execute("ALTER TABLE albums ADD COLUMN wikipedia_content TEXT")
        print("Columna 'wikipedia_content' añadida a la tabla 'albums'")
    
    if 'wikipedia_updated' not in column_names:
        cursor.execute("ALTER TABLE albums ADD COLUMN wikipedia_updated TIMESTAMP")
        print("Columna 'wikipedia_updated' añadida a la tabla 'albums'")
    
    # Actualizamos la base de datos
    conn.commit()
    conn.close()

def load_log_file(log_file):
    """Carga el archivo de registro o crea uno nuevo si no existe"""
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Error al cargar el archivo de registro. Creando uno nuevo.")
                return {"last_artist_id": 0, "last_album_id": 0}
    else:
        return {"last_artist_id": 0, "last_album_id": 0}

def save_log_file(log_file, data):
    """Guarda el estado actual en el archivo de registro"""
    with open(log_file, 'w') as f:
        json.dump(data, f)

def get_database_stats(db_path):
    """Obtiene estadísticas sobre enlaces existentes y faltantes"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Artistas
    cursor.execute("SELECT COUNT(*) FROM artists")
    total_artists = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM artists WHERE wikipedia_url IS NOT NULL AND wikipedia_url != ''")
    artists_with_wiki = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM artists WHERE wikipedia_content IS NOT NULL AND wikipedia_content != ''")
    artists_with_content = cursor.fetchone()[0]
    
    # Álbumes
    cursor.execute("SELECT COUNT(*) FROM albums")
    total_albums = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM albums WHERE wikipedia_url IS NOT NULL AND wikipedia_url != ''")
    albums_with_wiki = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM albums WHERE wikipedia_content IS NOT NULL AND wikipedia_content != ''")
    albums_with_content = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_artists": total_artists,
        "artists_with_wiki": artists_with_wiki,
        "artists_with_content": artists_with_content,
        "artists_missing_wiki": total_artists - artists_with_wiki,
        "total_albums": total_albums,
        "albums_with_wiki": albums_with_wiki,
        "albums_with_content": albums_with_content,
        "albums_missing_wiki": total_albums - albums_with_wiki
    }

def extract_wikipedia_url_from_musicbrainz(mb_url):
    """Intenta extraer un enlace a Wikipedia desde MusicBrainz"""
    if not mb_url:
        return None
    
    # Obtener el ID de MusicBrainz
    mb_id = mb_url.split('/')[-1]
    
    # Consultar la API de MusicBrainz para obtener relaciones
    try:
        if 'artist' in mb_url:
            endpoint = f"https://musicbrainz.org/ws/2/artist/{mb_id}?inc=url-rels&fmt=json"
        else:
            endpoint = f"https://musicbrainz.org/ws/2/release/{mb_id}?inc=url-rels&fmt=json"
        
        response = requests.get(endpoint, headers={"User-Agent": "MusicLibraryWikipediaUpdater/1.0"})
        
        if response.status_code == 200:
            data = response.json()
            
            # Buscar relación con Wikipedia
            if 'relations' in data:
                for relation in data['relations']:
                    if relation['type'] == 'wikipedia' and 'url' in relation:
                        return relation['url']['resource']
        
        return None
    except Exception as e:
        print(f"Error al consultar MusicBrainz: {e}")
        return None

def search_wikipedia(query):
    """Busca en la API de Wikipedia y devuelve el primer resultado"""
    try:
        encoded_query = quote(query)
        url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={encoded_query}&limit=1&namespace=0&format=json"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if len(data) > 3 and len(data[3]) > 0:
                return data[3][0]  # Primera URL
        
        # Intentar en español si no hay resultados
        url = f"https://es.wikipedia.org/w/api.php?action=opensearch&search={encoded_query}&limit=1&namespace=0&format=json"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if len(data) > 3 and len(data[3]) > 0:
                return data[3][0]  # Primera URL
        
        return None
    except Exception as e:
        print(f"Error al buscar en Wikipedia: {e}")
        return None

def get_wikipedia_content(url):
    """Obtiene el contenido principal de una página de Wikipedia preservando los saltos de línea"""
    if not url:
        return None
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer el contenido principal
            main_content = soup.find('div', {'id': 'mw-content-text'})
            
            if main_content:
                # Eliminar elementos no deseados
                for div in main_content.find_all(['div', 'table'], {'class': ['navbox', 'infobox', 'toc', 'metadata', 'tmbox', 'ambox']}):
                    div.decompose()
                
                # Extraer los párrafos principales preservando los saltos de línea
                paragraphs = main_content.find_all('p')
                
                # Preservamos la estructura original conservando los párrafos vacíos
                content = ""
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text:  # Solo añadimos párrafos con contenido
                        content += text + "\n\n"
                
                return content.strip()
            
        return None
    except Exception as e:
        print(f"Error al obtener contenido de Wikipedia: {e}")
        return None
def get_song_details(conn, song_id):
    """Obtiene los detalles completos de una canción incluyendo letras y enlaces externos"""
    cursor = conn.cursor()
    
    # Consulta principal para obtener datos de la canción
    cursor.execute("""
        SELECT s.id, s.title, s.artist, s.album, s.genre, s.date, s.album_year, 
               s.track_number, s.duration, s.file_path, s.bitrate, s.has_lyrics,
               s.replay_gain, s.replay_gain_track_gain, s.replay_gain_album_gain,
               s.artist_origin, s.album_art_path_denorm
        FROM songs s
        WHERE s.id = ?
    """, (song_id,))
    
    song = cursor.fetchone()
    
    if not song:
        return None
    
    # Convertimos a diccionario para facilitar agregar datos adicionales
    column_names = [description[0] for description in cursor.description]
    song_dict = dict(zip(column_names, song))
    
    # Obtener letras si las hay
    if song_dict['has_lyrics']:
        cursor.execute("""
            SELECT lyrics, source, last_updated
            FROM lyrics
            WHERE track_id = ?
        """, (song_id,))
        
        lyrics_data = cursor.fetchone()
        if lyrics_data:
            song_dict['lyrics_text'] = lyrics_data[0]
            song_dict['lyrics_source'] = lyrics_data[1]
            song_dict['lyrics_updated'] = lyrics_data[2]
    
    # Obtener enlaces externos
    cursor.execute("""
        SELECT spotify_url, spotify_id, youtube_url, lastfm_url, 
               musicbrainz_url, musicbrainz_recording_id
        FROM song_links
        WHERE song_id = ?
    """, (song_id,))
    
    links = cursor.fetchone()
    if links:
        column_names = [description[0] for description in cursor.description]
        links_dict = dict(zip(column_names, links))
        song_dict.update(links_dict)
    
    # Obtener información del artista incluyendo datos de Wikipedia
    cursor.execute("""
        SELECT id, bio, tags, origin, formed_year, wikipedia_url, 
               wikipedia_updated
        FROM artists
        WHERE name = ?
    """, (song_dict['artist'],))
    
    artist_data = cursor.fetchone()
    if artist_data:
        column_names = [description[0] for description in cursor.description]
        artist_dict = dict(zip(column_names, artist_data))
        
        # Solo añadimos un extracto del contenido de Wikipedia si existe
        if artist_dict.get('wikipedia_url'):
            cursor.execute("""
                SELECT wikipedia_content
                FROM artists
                WHERE id = ?
            """, (artist_dict['id'],))
            
            wiki_content = cursor.fetchone()
            if wiki_content and wiki_content[0]:
                # Limitamos a 500 caracteres para el extracto
                artist_dict['wikipedia_extract'] = wiki_content[0][:500] + '...' if len(wiki_content[0]) > 500 else wiki_content[0]
        
        # Añadimos los datos del artista bajo una clave separada
        song_dict['artist_info'] = artist_dict
    
    # Obtener información del álbum incluyendo datos de Wikipedia
    cursor.execute("""
        SELECT id, year, label, genre, total_tracks, album_art_path, 
               wikipedia_url, wikipedia_updated
        FROM albums
        WHERE name = ? AND artist_id = (
            SELECT id FROM artists WHERE name = ?
        )
    """, (song_dict['album'], song_dict['artist']))
    
    album_data = cursor.fetchone()
    if album_data:
        column_names = [description[0] for description in cursor.description]
        album_dict = dict(zip(column_names, album_data))
        
        # Solo añadimos un extracto del contenido de Wikipedia si existe
        if album_dict.get('wikipedia_url'):
            cursor.execute("""
                SELECT wikipedia_content
                FROM albums
                WHERE id = ?
            """, (album_dict['id'],))
            
            wiki_content = cursor.fetchone()
            if wiki_content and wiki_content[0]:
                # Limitamos a 500 caracteres para el extracto
                album_dict['wikipedia_extract'] = wiki_content[0][:500] + '...' if len(wiki_content[0]) > 500 else wiki_content[0]
        
        # Añadimos los datos del álbum bajo una clave separada
        song_dict['album_info'] = album_dict
    
    return song_dict

    
def get_artist_albums(db_path, artist_id):
    """Obtiene los álbumes asociados a un artista"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name, year, label 
        FROM albums 
        WHERE artist_id = ? 
        ORDER BY year
    """, (artist_id,))
    
    albums = cursor.fetchall()
    conn.close()
    
    return albums

def update_artists_wikipedia(db_path, log_file):
    """Actualiza los enlaces y contenido de Wikipedia para artistas"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Cargar el registro
    log_data = load_log_file(log_file)
    last_id = log_data.get("last_artist_id", 0)
    
    # Obtener artistas sin enlaces a Wikipedia
    cursor.execute("""
        SELECT id, name, musicbrainz_url
        FROM artists
        WHERE id > ? AND (wikipedia_url IS NULL OR wikipedia_url = '')
        ORDER BY id
    """, (last_id,))
    
    artists = cursor.fetchall()
    total = len(artists)
    
    if total == 0:
        print("No hay artistas pendientes de actualizar enlaces a Wikipedia.")
        return
    
    print(f"Procesando {total} artistas sin enlaces a Wikipedia...")
    
    for i, (artist_id, artist_name, mb_url) in enumerate(artists):
        print(f"\n[{i+1}/{total}] Procesando artista: {artist_name}")
        
        # Mostrar álbumes del artista
        albums = get_artist_albums(db_path, artist_id)
        if albums:
            print("  Álbumes:")
            for album_name, album_year, album_label in albums:
                label_info = f" - {album_label}" if album_label else ""
                print(f"   - {album_name} ({album_year}){label_info}")
        else:
            print("  No hay álbumes registrados para este artista.")
        
        # Primero intentamos obtener el enlace desde MusicBrainz
        wiki_url = None
        from_musicbrainz = False
        if mb_url:
            print(f"  Buscando enlace en MusicBrainz...")
            wiki_url = extract_wikipedia_url_from_musicbrainz(mb_url)
            
            if wiki_url:
                print(f"  Enlace encontrado en MusicBrainz: {wiki_url}")
                from_musicbrainz = True
        
        # Si no encontramos el enlace en MusicBrainz, buscamos en Wikipedia
        if not wiki_url:
            print(f"  Buscando en Wikipedia...")
            wiki_url = search_wikipedia(artist_name)
            
            if wiki_url:
                print(f"  Enlace encontrado en Wikipedia: {wiki_url}")
            else:
                print("  No se encontró enlace en Wikipedia.")
        
        # Si tenemos una URL, procesamos diferente según la fuente
        content = None
        if wiki_url:
            # Si proviene de MusicBrainz, añadimos automáticamente
            if from_musicbrainz:
                print(f"  Añadiendo automáticamente enlace de MusicBrainz: {wiki_url}")
                print("  Obteniendo contenido de Wikipedia...")
                content = get_wikipedia_content(wiki_url)
                
                if content:
                    content_preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"  Contenido obtenido: {content_preview}")
                else:
                    print("  No se pudo obtener el contenido.")
                
                # Abrimos el navegador para que el usuario pueda verificar
                subprocess.Popen(["xdg-open", wiki_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Damos opción a rechazar o modificar el enlace automático
                user_input = input(f"  URL de MusicBrainz añadida automáticamente. ¿Desea modificar o rechazar? [Enter para aceptar, nueva URL o 'n' para rechazar]: ")
                
                if user_input.lower() == 'n':
                    wiki_url = ""
                    content = None
                elif user_input.strip():
                    wiki_url = user_input.strip()
                    print("  Obteniendo contenido de la nueva URL...")
                    content = get_wikipedia_content(wiki_url)
                    if content:
                        content_preview = content[:100] + "..." if len(content) > 100 else content
                        print(f"  Contenido obtenido: {content_preview}")
                    else:
                        print("  No se pudo obtener el contenido.")
            
            # Si viene de búsqueda en Wikipedia, mostramos para confirmación
            else:
                subprocess.Popen(["xdg-open", wiki_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                user_input = input(f"  Confirmar URL para '{artist_name}' [Enter para confirmar '{wiki_url}', URL nueva, o 'n' para dejar vacío]: ")
                
                if user_input.lower() == 'n':
                    wiki_url = ""
                elif user_input.strip():
                    wiki_url = user_input.strip()
                    
                # Si tenemos una URL final, obtenemos el contenido
                if wiki_url:
                    print("  Obteniendo contenido de Wikipedia...")
                    content = get_wikipedia_content(wiki_url)
                    if content:
                        content_preview = content[:100] + "..." if len(content) > 100 else content
                        print(f"  Contenido obtenido: {content_preview}")
                    else:
                        print("  No se pudo obtener el contenido.")
        else:
            user_input = input(f"  No se encontró URL para '{artist_name}'. Introduzca URL manualmente o Enter para dejar vacío: ")
            if user_input.strip():
                wiki_url = user_input.strip()
                
                # Si se proporciona una URL manualmente, obtenemos el contenido
                print("  Obteniendo contenido de Wikipedia...")
                content = get_wikipedia_content(wiki_url)
                if content:
                    content_preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"  Contenido obtenido: {content_preview}")
                else:
                    print("  No se pudo obtener el contenido.")
            else:
                wiki_url = ""
        
        # Actualizamos la base de datos con URL y contenido
        now = datetime.datetime.now()
        if wiki_url:
            cursor.execute("""
                UPDATE artists
                SET wikipedia_url = ?, wikipedia_content = ?, wikipedia_updated = ?, links_updated = ?
                WHERE id = ?
            """, (wiki_url, content or "", now, now, artist_id))
        else:
            cursor.execute("""
                UPDATE artists
                SET wikipedia_url = ?, wikipedia_content = ?, wikipedia_updated = ?, links_updated = ?
                WHERE id = ?
            """, ("", "", now, now, artist_id))
        
        conn.commit()
        
        # Actualizamos el archivo de registro
        log_data["last_artist_id"] = artist_id
        save_log_file(log_file, log_data)
        
        # Preguntamos si desea continuar después de cada 10 artistas
        if (i + 1) % 10 == 0 and i < total - 1:
            if input("\n¿Desea continuar con la actualización? [S/n]: ").lower() == 'n':
                break
    
    conn.close()
    print("\nActualización de artistas completada.")

def update_albums_wikipedia(db_path, log_file):
    """Actualiza los enlaces y contenido de Wikipedia para álbumes"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Cargar el registro
    log_data = load_log_file(log_file)
    last_id = log_data.get("last_album_id", 0)
    
    # Obtener álbumes sin enlaces a Wikipedia
    cursor.execute("""
        SELECT albums.id, albums.name, artists.name, albums.musicbrainz_url, albums.label, albums.year
        FROM albums
        JOIN artists ON albums.artist_id = artists.id
        WHERE albums.id > ? AND (albums.wikipedia_url IS NULL OR albums.wikipedia_url = '')
        ORDER BY albums.id
    """, (last_id,))
    
    albums = cursor.fetchall()
    total = len(albums)
    
    if total == 0:
        print("No hay álbumes pendientes de actualizar enlaces a Wikipedia.")
        return
    
    print(f"Procesando {total} álbumes sin enlaces a Wikipedia...")
    
    for i, (album_id, album_name, artist_name, mb_url, album_label, album_year) in enumerate(albums):
        search_query = f"{artist_name} {album_name}"
        label_info = f" - Sello: {album_label}" if album_label else ""
        year_info = f" ({album_year})" if album_year else ""
        
        print(f"\n[{i+1}/{total}] Procesando álbum: {album_name}{year_info} de {artist_name}{label_info}")
        
        # Primero intentamos obtener el enlace desde MusicBrainz
        wiki_url = None
        from_musicbrainz = False
        if mb_url:
            print(f"  Buscando enlace en MusicBrainz...")
            wiki_url = extract_wikipedia_url_from_musicbrainz(mb_url)
            
            if wiki_url:
                print(f"  Enlace encontrado en MusicBrainz: {wiki_url}")
                from_musicbrainz = True
        
        # Si no encontramos el enlace en MusicBrainz, buscamos en Wikipedia
        if not wiki_url:
            print(f"  Buscando en Wikipedia...")
            wiki_url = search_wikipedia(search_query)
            
            if wiki_url:
                print(f"  Enlace encontrado en Wikipedia: {wiki_url}")
            else:
                print("  No se encontró enlace en Wikipedia.")
        
        # Si tenemos una URL, procesamos diferente según la fuente
        content = None
        if wiki_url:
            # Si proviene de MusicBrainz, añadimos automáticamente
            if from_musicbrainz:
                print(f"  Añadiendo automáticamente enlace de MusicBrainz: {wiki_url}")
                print("  Obteniendo contenido de Wikipedia...")
                content = get_wikipedia_content(wiki_url)
                
                if content:
                    content_preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"  Contenido obtenido: {content_preview}")
                else:
                    print("  No se pudo obtener el contenido.")
                
                # Abrimos el navegador para que el usuario pueda verificar
                subprocess.Popen(["xdg-open", wiki_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Damos opción a rechazar o modificar el enlace automático
                user_input = input(f"  URL de MusicBrainz añadida automáticamente. ¿Desea modificar o rechazar? [Enter para aceptar, nueva URL o 'n' para rechazar]: ")
                
                if user_input.lower() == 'n':
                    wiki_url = ""
                    content = None
                elif user_input.strip():
                    wiki_url = user_input.strip()
                    print("  Obteniendo contenido de la nueva URL...")
                    content = get_wikipedia_content(wiki_url)
                    if content:
                        content_preview = content[:100] + "..." if len(content) > 100 else content
                        print(f"  Contenido obtenido: {content_preview}")
                    else:
                        print("  No se pudo obtener el contenido.")
            
            # Si viene de búsqueda en Wikipedia, mostramos para confirmación
            else:
                subprocess.Popen(["xdg-open", wiki_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                user_input = input(f"  Confirmar URL para '{album_name}' [Enter para confirmar '{wiki_url}', URL nueva, o 'n' para dejar vacío]: ")
                
                if user_input.lower() == 'n':
                    wiki_url = ""
                elif user_input.strip():
                    wiki_url = user_input.strip()
                    
                # Si tenemos una URL final, obtenemos el contenido
                if wiki_url:
                    print("  Obteniendo contenido de Wikipedia...")
                    content = get_wikipedia_content(wiki_url)
                    if content:
                        content_preview = content[:100] + "..." if len(content) > 100 else content
                        print(f"  Contenido obtenido: {content_preview}")
                    else:
                        print("  No se pudo obtener el contenido.")
        else:
            user_input = input(f"  No se encontró URL para '{album_name}'. Introduzca URL manualmente o Enter para dejar vacío: ")
            if user_input.strip():
                wiki_url = user_input.strip()
                
                # Si se proporciona una URL manualmente, obtenemos el contenido
                print("  Obteniendo contenido de Wikipedia...")
                content = get_wikipedia_content(wiki_url)
                if content:
                    content_preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"  Contenido obtenido: {content_preview}")
                else:
                    print("  No se pudo obtener el contenido.")
            else:
                wiki_url = ""
        
        # Actualizamos la base de datos con URL y contenido
        now = datetime.datetime.now()
        if wiki_url:
            cursor.execute("""
                UPDATE albums
                SET wikipedia_url = ?, wikipedia_content = ?, wikipedia_updated = ?, links_updated = ?
                WHERE id = ?
            """, (wiki_url, content or "", now, now, album_id))
        else:
            cursor.execute("""
                UPDATE albums
                SET wikipedia_url = ?, wikipedia_content = ?, wikipedia_updated = ?, links_updated = ?
                WHERE id = ?
            """, ("", "", now, now, album_id))
        
        conn.commit()
        
        # Actualizamos el archivo de registro
        log_data["last_album_id"] = album_id
        save_log_file(log_file, log_data)
        
        # Preguntamos si desea continuar después de cada 10 álbumes
        if (i + 1) % 10 == 0 and i < total - 1:
            if input("\n¿Desea continuar con la actualización? [S/n]: ").lower() == 'n':
                break
    
    conn.close()
    print("\nActualización de álbumes completada.")

def update_content_only(db_path, entity_type):
    """Actualiza solo el contenido para entidades que ya tienen URL de Wikipedia pero no contenido"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if entity_type == 'artists':
        # Obtener artistas con URL pero sin contenido
        cursor.execute("""
            SELECT id, name, wikipedia_url
            FROM artists
            WHERE wikipedia_url IS NOT NULL AND wikipedia_url != '' 
            AND (wikipedia_content IS NULL OR wikipedia_content = '')
            ORDER BY id
        """)
        
        entities = cursor.fetchall()
        table_name = 'artists'
        
        # Para cada artista, conseguimos también sus álbumes
        entities_with_info = []
        for entity_id, entity_name, wiki_url in entities:
            albums = get_artist_albums(db_path, entity_id)
            entities_with_info.append((entity_id, entity_name, wiki_url, albums))
        
    else:  # albums
        cursor.execute("""
            SELECT albums.id, albums.name, albums.wikipedia_url, albums.label, albums.year, artists.name
            FROM albums
            JOIN artists ON albums.artist_id = artists.id
            WHERE albums.wikipedia_url IS NOT NULL AND albums.wikipedia_url != '' 
            AND (albums.wikipedia_content IS NULL OR albums.wikipedia_content = '')
            ORDER BY albums.id
        """)
        
        entities_with_info = cursor.fetchall()
        table_name = 'albums'
    
    total = len(entities_with_info)
    
    if total == 0:
        print(f"No hay {entity_type} con URL pero sin contenido.")
        return
    
    print(f"Procesando {total} {entity_type} para obtener contenido de Wikipedia...")
    
    if entity_type == 'artists':
        for i, (entity_id, entity_name, wiki_url, albums) in enumerate(entities_with_info):
            print(f"\n[{i+1}/{total}] Obteniendo contenido para: {entity_name}")
            print(f"  URL: {wiki_url}")
            
            # Mostrar álbumes del artista
            if albums:
                print("  Álbumes:")
                for album_name, album_year, album_label in albums:
                    label_info = f" - {album_label}" if album_label else ""
                    print(f"   - {album_name} ({album_year}){label_info}")
            else:
                print("  No hay álbumes registrados para este artista.")
            
            # Obtener contenido
            print("  Obteniendo contenido...")
            content = get_wikipedia_content(wiki_url)
            
            if content:
                content_preview = content[:100] + "..." if len(content) > 100 else content
                print(f"  Contenido obtenido: {content_preview}")
                
                # Actualizar la base de datos
                now = datetime.datetime.now()
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET wikipedia_content = ?, wikipedia_updated = ?
                    WHERE id = ?
                """, (content, now, entity_id))
                
                conn.commit()
            else:
                print("  No se pudo obtener el contenido.")
    else:  # albums
        for i, (entity_id, entity_name, wiki_url, album_label, album_year, artist_name) in enumerate(entities_with_info):
            label_info = f" - Sello: {album_label}" if album_label else ""
            year_info = f" ({album_year})" if album_year else ""
            
            print(f"\n[{i+1}/{total}] Obteniendo contenido para: {entity_name}{year_info} de {artist_name}{label_info}")
            print(f"  URL: {wiki_url}")
            
            # Obtener contenido
            print("  Obteniendo contenido...")
            content = get_wikipedia_content(wiki_url)
            
            if content:
                content_preview = content[:100] + "..." if len(content) > 100 else content
                print(f"  Contenido obtenido: {content_preview}")
                
                # Actualizar la base de datos
                now = datetime.datetime.now()
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET wikipedia_content = ?, wikipedia_updated = ?
                    WHERE id = ?
                """, (content, now, entity_id))
                
                conn.commit()
            else:
                print("  No se pudo obtener el contenido.")
        
            # Preguntamos si desea continuar después de cada 20 entidades
            if (i + 1) % 20 == 0 and i < total - 1:
                if input("\n¿Desea continuar con la actualización de contenido? [S/n]: ").lower() == 'n':
                    break
    
    conn.close()
    print(f"\nActualización de contenido para {entity_type} completada.")


def load_config(config_file):
    """Load configuration from a JSON file"""
    with open(config_file, 'r') as f:
        return json.load(f)

def main():
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Actualizar enlaces y contenido de Wikipedia en la base de datos de música')
    parser.add_argument('--config', required=True, help='Archivo de configuración JSON')
    parser.add_argument('--log-file', help='Archivo de registro para seguimiento del progreso')
    parser.add_argument('--db-path', help='Ruta a la base de datos SQLite')
    parser.add_argument('type', choices=['artists', 'albums', 'artists_content', 'albums_content'], 
                        help='Tipo de entidad a actualizar (artists, albums, artists_content, albums_content)')
    
    args = parser.parse_args()
    
    # Cargar configuración
    config = load_config(args.config)

    
    db_path = args.db_path or config.get('db_path')
    if not db_path:
        print("Debes añadir un db-path como argumento o en la configuracion")
    
    log_file = args.log_file or config.get('log_file', 'db_wiki_update.log')
    
    update_type = args.type or config.get('type', None)
    if not update_type:
        print("Error: Debe especificar tipo de actualización. --type o en config_db_creator.json")


    # Inicializar la base de datos
    init_database(db_path)
    
    # Mostrar estadísticas iniciales
    stats = get_database_stats(db_path)
    print("\n=== Estadísticas de Enlaces y Contenido ===")
    print(f"Artistas: {stats['artists_with_wiki']}/{stats['total_artists']} enlaces ({stats['artists_missing_wiki']} faltan)")
    print(f"Artistas: {stats['artists_with_content']}/{stats['total_artists']} con contenido")
    print(f"Álbumes: {stats['albums_with_wiki']}/{stats['total_albums']} enlaces ({stats['albums_missing_wiki']} faltan)")
    print(f"Álbumes: {stats['albums_with_content']}/{stats['total_albums']} con contenido")
    print("==========================================\n")
    
    # Ejecutar la actualización según el tipo
    if update_type == 'artists':
        update_artists_wikipedia(db_path, log_file)
    elif update_type == 'albums':
        update_albums_wikipedia(db_path, log_file)
    elif update_type == 'artists_content':
        update_content_only(db_path, 'artists')
    elif update_type == 'albums_content':
        update_content_only(db_path, 'albums')
    
    # Mostrar estadísticas finales
    stats = get_database_stats(db_path)
    print("\n=== Estadísticas Finales ===")
    print(f"Artistas: {stats['artists_with_wiki']}/{stats['total_artists']} enlaces ({stats['artists_missing_wiki']} faltan)")
    print(f"Artistas: {stats['artists_with_content']}/{stats['total_artists']} con contenido")
    print(f"Álbumes: {stats['albums_with_wiki']}/{stats['total_albums']} enlaces ({stats['albums_missing_wiki']} faltan)")
    print(f"Álbumes: {stats['albums_with_content']}/{stats['total_albums']} con contenido")
    print("============================\n")

if __name__ == "__main__":
    main()