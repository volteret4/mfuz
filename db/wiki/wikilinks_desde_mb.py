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
import time
import traceback

sqlite3.register_adapter(datetime.datetime, lambda dt: dt.isoformat())

# MusicBrainz API constants
MUSICBRAINZ_API_BASE = "https://musicbrainz.org/ws/2"
MUSICBRAINZ_USER_AGENT = "MusicLibraryWikipediaUpdater/1.0 (your-email@example.com)"
MUSICBRAINZ_RATE_LIMIT = 1.0  # seconds between requests

# Definición de colores para el log
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_PURPLE = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"


def init_database(db_path):
    """Inicializa la base de datos añadiendo las columnas necesarias si no existen"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Función auxiliar para verificar y añadir columnas
    def check_and_add_columns(table_name):
        # Comprobar si la tabla existe
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            print(f"{COLOR_YELLOW}La tabla '{table_name}' no existe en la base de datos{COLOR_RESET}")
            return False
            
        # Comprobar si las columnas existen
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        columns_to_add = []
        if 'wikipedia_url' not in column_names:
            columns_to_add.append('wikipedia_url TEXT')
        if 'wikipedia_content' not in column_names:
            columns_to_add.append('wikipedia_content TEXT')
        if 'wikipedia_updated' not in column_names:
            columns_to_add.append('wikipedia_updated TIMESTAMP')
            
        # Añadir columnas faltantes
        for column_def in columns_to_add:
            column_name = column_def.split()[0]
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
            print(f"{COLOR_GREEN}Columna '{column_name}' añadida a la tabla '{table_name}'{COLOR_RESET}")
        
        return True
    
    # Verificar y añadir columnas para artists, albums y labels
    check_and_add_columns('artists')
    check_and_add_columns('albums')
    check_and_add_columns('labels')
    
    # Actualizamos la base de datos
    conn.commit()
    conn.close()

def ensure_dir_exists(file_path):
    """Ensure that the directory for the given file path exists"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def construct_log_path(log_file):
    """Construct a proper log file path using PROJECT_ROOT"""
    # If log_file is already an absolute path, return it as is
    if os.path.isabs(log_file):
        return log_file
    
    # Otherwise, construct the path using PROJECT_ROOT
    from base_module import PROJECT_ROOT
    log_path = os.path.join(PROJECT_ROOT, log_file)
    
    # Ensure the directory exists
    ensure_dir_exists(log_path)
    return log_path


def load_log_file(log_file):
    """Carga el archivo de registro o crea uno nuevo si no existe"""
    try:
        log_path = construct_log_path(log_file)
        
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print(f"{COLOR_YELLOW}Error al cargar el archivo de registro. Creando uno nuevo.{COLOR_RESET}")
                    return {"last_artist_id": 0, "last_album_id": 0, "last_label_id": 0}
        else:
            return {"last_artist_id": 0, "last_album_id": 0, "last_label_id": 0}
    except Exception as e:
        print(f"{COLOR_RED}Error loading log file: {e}{COLOR_RESET}")
        return {"last_artist_id": 0, "last_album_id": 0, "last_label_id": 0}


def save_log_file(log_file, data):
    """Guarda el estado actual en el archivo de registro"""
    try:
        log_path = construct_log_path(log_file)
        
        with open(log_path, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"{COLOR_RED}Error saving log file: {e}{COLOR_RESET}")



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
    
    # Inicializar stats con los datos básicos
    stats = {
        "total_artists": total_artists,
        "artists_with_wiki": artists_with_wiki,
        "artists_with_content": artists_with_content,
        "artists_missing_wiki": total_artists - artists_with_wiki,
        "total_albums": total_albums,
        "albums_with_wiki": albums_with_wiki,
        "albums_with_content": albums_with_content,
        "albums_missing_wiki": total_albums - albums_with_wiki
    }
    
    # Verificar si existe la tabla de sellos y añadir esas estadísticas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='labels'")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM labels")
        total_labels = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM labels WHERE wikipedia_url IS NOT NULL AND wikipedia_url != ''")
        labels_with_wiki = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM labels WHERE wikipedia_content IS NOT NULL AND wikipedia_content != ''")
        labels_with_content = cursor.fetchone()[0]
        
        stats.update({
            "total_labels": total_labels,
            "labels_with_wiki": labels_with_wiki,
            "labels_with_content": labels_with_content,
            "labels_missing_wiki": total_labels - labels_with_wiki
        })
    
    conn.close()
    
    return stats


def extract_wikipedia_url_from_musicbrainz(mb_url, user_agent=None):
    """
    Intenta extraer un enlace a Wikipedia desde MusicBrainz con depuración detallada
    y manejo mejorado de relaciones URL
    """
    if not mb_url:
        print(f"  {COLOR_YELLOW}No se proporcionó URL de MusicBrainz{COLOR_RESET}")
        return None
    
    print(f"  {COLOR_BLUE}Analizando URL de MusicBrainz: {mb_url}{COLOR_RESET}")
    
    # Verificar y procesar URL
    mb_id = None
    entity_type = None
    
    try:
        # Detectar tipo de entidad y extraer ID correctamente
        if '/artist/' in mb_url:
            entity_type = 'artist'
            mb_id = mb_url.split('/artist/')[-1].split('/')[0].split('?')[0]
        elif '/release/' in mb_url:
            entity_type = 'release'
            mb_id = mb_url.split('/release/')[-1].split('/')[0].split('?')[0]
        elif '/label/' in mb_url:
            entity_type = 'label'
            mb_id = mb_url.split('/label/')[-1].split('/')[0].split('?')[0]
        elif '/recording/' in mb_url:
            entity_type = 'recording'
            mb_id = mb_url.split('/recording/')[-1].split('/')[0].split('?')[0]
        else:
            # Si la URL no tiene un formato reconocido, intentar extraer ID genéricamente
            mb_parts = mb_url.strip('/').split('/')
            mb_id = mb_parts[-1].split('?')[0] if mb_parts else None
            
            # Inferir tipo basado en la URL
            if 'artist' in mb_url.lower():
                entity_type = 'artist'
            elif 'release' in mb_url.lower():
                entity_type = 'release'
            elif 'label' in mb_url.lower():
                entity_type = 'label'
            elif 'recording' in mb_url.lower():
                entity_type = 'recording'
            else:
                entity_type = 'artist'  # Tipo por defecto
        
        if not mb_id:
            print(f"  {COLOR_RED}No se pudo extraer ID de MusicBrainz de la URL: {mb_url}{COLOR_RESET}")
            return None
            
        print(f"  {COLOR_BLUE}ID de MusicBrainz extraído: {mb_id}, Tipo: {entity_type}{COLOR_RESET}")
        
        # Preparar endpoint y parámetros para la API de MusicBrainz
        endpoint = f"https://musicbrainz.org/ws/2/{entity_type}/{mb_id}"
        params = {
            "inc": "url-rels",
            "fmt": "json"
        }
        
        headers = {
            "User-Agent": user_agent or "MusicLibraryWikipediaUpdater/1.0 (your-email@example.com)",
            "Accept": "application/json"
        }
        
        print(f"  {COLOR_BLUE}Consultando API de MusicBrainz: {endpoint}{COLOR_RESET}")
        
        import requests
        import time
        import json
        
        response = requests.get(endpoint, params=params, headers=headers, timeout=30)
        
        # Respetar límites de tasa
        time.sleep(1)
        
        if response.status_code != 200:
            print(f"  {COLOR_RED}Error en API de MusicBrainz: Código {response.status_code}{COLOR_RESET}")
            if response.text:
                print(f"  {COLOR_YELLOW}Respuesta: {response.text[:200]}...{COLOR_RESET}")
            return None
            
        # Procesar la respuesta
        data = response.json()
        
        # Depuración: guardar respuesta a archivo para análisis
        with open(f'mb_response_{entity_type}_{mb_id}.json', 'w') as f:
            json.dump(data, f, indent=2)
            print(f"  {COLOR_BLUE}Respuesta guardada en mb_response_{entity_type}_{mb_id}.json{COLOR_RESET}")
        
        # Verificar que la respuesta contiene relaciones
        if 'relations' not in data:
            print(f"  {COLOR_YELLOW}No se encontraron relaciones en la respuesta. Campos disponibles: {list(data.keys())}{COLOR_RESET}")
            return None
            
        # Buscar enlaces a Wikipedia, Wikimedia o Wikidata en las relaciones
        print(f"  {COLOR_BLUE}Encontradas {len(data['relations'])} relaciones{COLOR_RESET}")
        
        # Primero, buscar relaciones directas a Wikipedia
        for relation in data['relations']:
            relation_type = relation.get('type', '')
            
            if 'url' in relation and 'resource' in relation['url']:
                url = relation['url']['resource']
                
                if relation_type == 'wikipedia':
                    print(f"  {COLOR_GREEN}Encontrado enlace directo a Wikipedia: {url}{COLOR_RESET}")
                    return url
                    
                # También buscar en URL que contengan 'wikipedia'
                if 'wikipedia.org' in url:
                    print(f"  {COLOR_GREEN}Encontrado enlace a Wikipedia en relación '{relation_type}': {url}{COLOR_RESET}")
                    return url
        
        # Buscar relaciones a Wikidata o Wikimedia Commons
        wikidata_url = None
        
        for relation in data['relations']:
            relation_type = relation.get('type', '')
            
            if 'url' in relation and 'resource' in relation['url']:
                url = relation['url']['resource']
                
                # Capturar URL de Wikidata para uso posterior
                if relation_type == 'wikidata' or 'wikidata.org' in url:
                    print(f"  {COLOR_BLUE}Encontrado enlace a Wikidata: {url}{COLOR_RESET}")
                    wikidata_url = url
        
        # Si encontramos Wikidata, intentar conseguir enlace a Wikipedia
        if wikidata_url:
            wikipedia_url = extract_wikipedia_from_wikidata(wikidata_url)
            if wikipedia_url:
                print(f"  {COLOR_GREEN}Encontrado enlace a Wikipedia desde Wikidata: {wikipedia_url}{COLOR_RESET}")
                return wikipedia_url
        
        print(f"  {COLOR_YELLOW}No se encontró enlace a Wikipedia en MusicBrainz para {entity_type} {mb_id}{COLOR_RESET}")
        return None
        
    except Exception as e:
        import traceback
        print(f"  {COLOR_RED}Error procesando MusicBrainz: {str(e)}{COLOR_RESET}")
        traceback.print_exc()
        return None


def extract_wikipedia_from_wikidata(wikidata_url):
    """Obtiene un enlace a Wikipedia desde una entidad de Wikidata"""
    if not wikidata_url:
        return None
        
    try:
        # Extraer el ID de entidad de Wikidata (Q12345)
        entity_id = None
        if 'entity/' in wikidata_url:
            entity_id = wikidata_url.split('entity/')[-1].split('/')[0]
        else:
            # Intentar extraer directamente
            entity_parts = wikidata_url.strip('/').split('/')
            entity_id = entity_parts[-1] if entity_parts else None
            
        if not entity_id or not entity_id.startswith('Q'):
            print(f"  {COLOR_YELLOW}ID de Wikidata no válido: {entity_id}{COLOR_RESET}")
            return None
            
        print(f"  {COLOR_BLUE}Consultando Wikidata para entidad: {entity_id}{COLOR_RESET}")
        
        # Consultar a la API de Wikidata
        import requests
        
        endpoint = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbgetentities",
            "ids": entity_id,
            "format": "json",
            "props": "sitelinks"
        }
        
        response = requests.get(endpoint, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"  {COLOR_RED}Error en API de Wikidata: {response.status_code}{COLOR_RESET}")
            return None
            
        data = response.json()
        
        # Verificar si tenemos sitelinks en la respuesta
        if 'entities' in data and entity_id in data['entities'] and 'sitelinks' in data['entities'][entity_id]:
            sitelinks = data['entities'][entity_id]['sitelinks']
            
            # Intentar obtener enlace de Wikipedia en español primero
            if 'eswiki' in sitelinks:
                title = sitelinks['eswiki']['title']
                es_url = f"https://es.wikipedia.org/wiki/{title.replace(' ', '_')}"
                print(f"  {COLOR_GREEN}Enlace encontrado a Wikipedia en español: {es_url}{COLOR_RESET}")
                return es_url
                
            # Si no hay en español, intentar con inglés
            if 'enwiki' in sitelinks:
                title = sitelinks['enwiki']['title']
                en_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                print(f"  {COLOR_GREEN}Enlace encontrado a Wikipedia en inglés: {en_url}{COLOR_RESET}")
                return en_url
                
            # Intentar con cualquier otra Wikipedia
            for site, data in sitelinks.items():
                if site.endswith('wiki') and not site.endswith(('wikiquote', 'wikibooks', 'wikinews', 'wikiversity', 'wikivoyage')):
                    lang = site.replace('wiki', '')
                    title = data['title']
                    wiki_url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    print(f"  {COLOR_GREEN}Enlace encontrado a Wikipedia en {lang}: {wiki_url}{COLOR_RESET}")
                    return wiki_url
                    
        print(f"  {COLOR_YELLOW}No se encontraron enlaces a Wikipedia en Wikidata para {entity_id}{COLOR_RESET}")
        return None
        
    except Exception as e:
        print(f"  {COLOR_RED}Error procesando Wikidata: {str(e)}{COLOR_RESET}")
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
               s.replay_gain_track_gain, s.replay_gain_album_gain,
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
    if song_dict.get('has_lyrics'):
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



def update_artists_wikipedia(db_path, log_file, user_agent=None, modo='manual', force_update=False):
    """Actualiza los enlaces y contenido de Wikipedia para artistas"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Cargar el registro
    log_data = load_log_file(log_file)
    last_id = 0 if force_update else log_data.get("last_artist_id", 0)
    
    # Obtener artistas sin enlaces a Wikipedia o todos si force_update está activado
    if force_update:
        cursor.execute("""
            SELECT id, name, musicbrainz_url
            FROM artists
            WHERE id > ?
            ORDER BY id
        """, (last_id,))
        print(f"{COLOR_CYAN}Modo force-update activado. Procesando todos los artistas...{COLOR_RESET}")
    else:
        cursor.execute("""
            SELECT id, name, musicbrainz_url
            FROM artists
            WHERE id > ? AND (wikipedia_url IS NULL OR wikipedia_url = '')
            ORDER BY id
        """, (last_id,))
    
    artists = cursor.fetchall()
    total = len(artists)
    
    if total == 0:
        print(f"{COLOR_YELLOW}No hay artistas pendientes de actualizar enlaces a Wikipedia.{COLOR_RESET}")
        return
    
    print(f"{COLOR_CYAN}Procesando {total} artistas...{COLOR_RESET}")
    print(f"{COLOR_CYAN}Modo: {modo}{COLOR_RESET}")
    
    for i, (artist_id, artist_name, mb_url) in enumerate(artists):
        clear()
        print(f"\n{COLOR_BOLD}[{i+1}/{total}] Procesando artista: {artist_name}{COLOR_RESET}")
        
        # Mostrar álbumes del artista
        albums = get_artist_albums(db_path, artist_id)
        if albums:
            print(f"  {COLOR_CYAN}Álbumes:{COLOR_RESET}")
            for album_name, album_year, album_label in albums:
                label_info = f" - {album_label}" if album_label else ""
                print(f"   - {album_name} ({album_year}){label_info}")
        else:
            print(f"  {COLOR_YELLOW}No hay álbumes registrados para este artista.{COLOR_RESET}")
        
        # Intentar obtener el enlace desde MusicBrainz
        wiki_url = None
        from_musicbrainz = False
        if mb_url:
            print(f"  {COLOR_BLUE}Buscando enlace en MusicBrainz: {mb_url}{COLOR_RESET}")
            wiki_url = extract_wikipedia_url_from_musicbrainz(mb_url, user_agent)
            
            if wiki_url:
                print(f"  {COLOR_GREEN}Enlace encontrado en MusicBrainz: {wiki_url}{COLOR_RESET}")
                from_musicbrainz = True
        
        # En modo super-auto, saltar si no se encontró enlace en MusicBrainz
        if modo == 'super-auto' and not wiki_url:
            print(f"  {COLOR_YELLOW}No se encontró enlace en MusicBrainz. Saltando en modo super-auto.{COLOR_RESET}")
            continue
        
        # Procesar enlaces de MusicBrainz según el modo
        if wiki_url and from_musicbrainz:
            # En modo auto y super-auto, añadir automáticamente
            if modo in ['auto', 'super-auto']:
                print(f"  {COLOR_GREEN}Añadiendo automáticamente enlace de MusicBrainz: {wiki_url}{COLOR_RESET}")
                print("  Obteniendo contenido de Wikipedia...")
                content = get_wikipedia_content(wiki_url)
                
                if content:
                    print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                else:
                    print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
            
            # En modo manual, pedir confirmación
            elif modo == 'manual':
                # Abrir el navegador para verificación
                try:
                    subprocess.Popen(["xdg-open", wiki_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    print(f"  {COLOR_RED}No se pudo abrir el navegador: {e}{COLOR_RESET}")
                    print(f"  URL: {wiki_url}")
                
                # Pedir confirmación
                user_input = input(f"  Confirmar URL para '{artist_name}' [Enter para confirmar '{wiki_url}', URL nueva, o 'n' para dejar vacío]: ")
                
                if user_input.lower() == 'n':
                    wiki_url = ""
                    content = None
                elif user_input.strip():
                    wiki_url = user_input.strip()
                    
                    # Si se modificó la URL, preguntar si desea añadirla a MusicBrainz
                    # if mb_url and wiki_url:
                    #     contribute = input(f"  ¿Desea añadir esta URL a MusicBrainz? (y/n): ")
                    #     if contribute.lower() == 'y':
                    #         add_wikipedia_link_to_musicbrainz(mb_url, wiki_url, user_agent, mb_username, mb_password)
                
                # Obtener contenido si hay URL
                if wiki_url:
                    print("  Obteniendo contenido de Wikipedia...")
                    content = get_wikipedia_content(wiki_url)
                    if content:
                        print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                    else:
                        print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
        
        # Si no se encontró enlace en MusicBrainz o estamos en modo manual/auto, buscar en Wikipedia
        elif not wiki_url and modo != 'super-auto':
            print(f"  {COLOR_BLUE}Buscando en Wikipedia...{COLOR_RESET}")
            wiki_url = search_wikipedia(artist_name)
            
            if wiki_url:
                print(f"  {COLOR_GREEN}Enlace encontrado en Wikipedia: {wiki_url}{COLOR_RESET}")
                
                # Abrir navegador para verificación
                try:
                    subprocess.Popen(["xdg-open", wiki_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    print(f"  {COLOR_RED}No se pudo abrir el navegador: {e}{COLOR_RESET}")
                    print(f"  URL: {wiki_url}")
                
                # Pedir confirmación
                user_input = input(f"  Confirmar URL para '{artist_name}' [Enter para confirmar '{wiki_url}', URL nueva, o 'n' para dejar vacío]: ")
                
                if user_input.lower() == 'n':
                    wiki_url = ""
                elif user_input.strip():
                    wiki_url = user_input.strip()
                
                # Si se confirmó o modificó la URL, preguntar si desea añadirla a MusicBrainz
                if mb_url and wiki_url:
                    contribute = input(f"  ¿Desea añadir esta URL a MusicBrainz? (y/n): ")
                    if contribute.lower() == 'y':
                        add_wikipedia_link_to_musicbrainz(mb_url, wiki_url, user_agent, mb_username, mb_password)
                
                # Obtener contenido si hay URL
                if wiki_url:
                    print("  Obteniendo contenido de Wikipedia...")
                    content = get_wikipedia_content(wiki_url)
                    if content:
                        print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                    else:
                        print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
            else:
                print(f"  {COLOR_YELLOW}No se encontró enlace en Wikipedia.{COLOR_RESET}")
                
                # Permitir entrada manual
                print(f"{COLOR_CYAN} Artista: {artist_name} {COLOR_RESET}")
                user_input = input(f"  Introduzca URL manualmente o Enter para dejar vacío: ")
                if user_input.strip():
                    wiki_url = user_input.strip()
                    
                    # Si se proporcionó una URL manualmente, preguntar si desea añadirla a MusicBrainz
                    if mb_url:
                        contribute = input(f"  ¿Desea añadir esta URL a MusicBrainz? (y/n): ")
                        if contribute.lower() == 'y':
                            add_wikipedia_link_to_musicbrainz(mb_url, wiki_url, user_agent, mb_username, mb_password)
                    
                    # Obtener contenido
                    print("  Obteniendo contenido de Wikipedia...")
                    content = get_wikipedia_content(wiki_url)
                    if content:
                        print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                    else:
                        print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
                else:
                    wiki_url = ""
                    content = None
        
        # Actualizar la base de datos con URL y contenido
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
        
        # Actualizar el archivo de registro
        log_data["last_artist_id"] = artist_id
        save_log_file(log_file, log_data)
        
        # Preguntar si desea continuar después de cada 10 artistas (excepto en modo super-auto)
        if modo != 'super-auto' and (i + 1) % 10 == 0 and i < total - 1:
            if input(f"\n¿Desea continuar con la actualización? [{COLOR_GREEN}S{COLOR_RESET}/n]: ").lower() == 'n':
                break
    
    conn.close()
    print(f"\n{COLOR_GREEN}Actualización de artistas completada.{COLOR_RESET}")

# ALBUMS
def update_albums_wikipedia(db_path, log_file, user_agent=None, modo='manual', mb_username=None, mb_password=None, force_update=False):
    """Actualiza los enlaces y contenido de Wikipedia para álbumes"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Cargar el registro
    log_data = load_log_file(log_file)
    last_id = 0 if force_update else log_data.get("last_album_id", 0)
    
    # Obtener álbumes sin enlaces a Wikipedia o todos si force_update está activado
    if force_update:
        cursor.execute("""
            SELECT albums.id, albums.name, artists.name, albums.musicbrainz_url, albums.label, albums.year
            FROM albums
            JOIN artists ON albums.artist_id = artists.id
            WHERE albums.id > ?
            ORDER BY albums.id
        """, (last_id,))
        print(f"{COLOR_CYAN}Modo force-update activado. Procesando todos los álbumes...{COLOR_RESET}")
    else:
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
        print(f"{COLOR_YELLOW}No hay álbumes pendientes de actualizar enlaces a Wikipedia.{COLOR_RESET}")
        return
    
    print(f"{COLOR_CYAN}Procesando {total} álbumes...{COLOR_RESET}")
    
    for i, (album_id, album_name, artist_name, mb_url, album_label, album_year) in enumerate(albums):
        search_query = f"{artist_name} {album_name}"
        label_info = f" - Sello: {album_label}" if album_label else ""
        year_info = f" ({album_year})" if album_year else ""
        
        clear()
        print(f"\n{COLOR_BOLD}[{i+1}/{total}] Procesando álbum: {album_name}{year_info}{COLOR_RESET}")
        print(f"  {COLOR_CYAN}Artista: {artist_name}{COLOR_RESET}")
        if album_label:
            print(f"  {COLOR_CYAN}Sello: {album_label}{COLOR_RESET}")
        
        # Primero intentamos obtener el enlace desde MusicBrainz
        wiki_url = None
        from_musicbrainz = False
        if mb_url:
            print(f"  {COLOR_BLUE}Buscando enlace en MusicBrainz: {mb_url}{COLOR_RESET}")
            wiki_url = extract_wikipedia_url_from_musicbrainz(mb_url, user_agent)
            
            if wiki_url:
                print(f"  {COLOR_GREEN}Enlace encontrado en MusicBrainz: {wiki_url}{COLOR_RESET}")
                from_musicbrainz = True
        
        # Si no encontramos el enlace en MusicBrainz y estamos en modo super-auto, saltar este álbum
        if not wiki_url and modo == 'super-auto':
            print(f"  {COLOR_YELLOW}No se encontró enlace en MusicBrainz y estamos en modo super-auto. Saltando...{COLOR_RESET}")
            # Actualizamos el archivo de registro
            log_data["last_album_id"] = album_id
            save_log_file(log_file, log_data)
            continue
        
        # Si no encontramos el enlace en MusicBrainz, buscamos en Wikipedia
        if not wiki_url and modo != 'super-auto':
            print(f"  {COLOR_BLUE}Buscando en Wikipedia...{COLOR_RESET}")
            wiki_url = search_wikipedia(search_query)
            
            if wiki_url:
                print(f"  {COLOR_GREEN}Enlace encontrado en Wikipedia: {wiki_url}{COLOR_RESET}")
            else:
                print(f"  {COLOR_YELLOW}No se encontró enlace en Wikipedia.{COLOR_RESET}")
                print(f"  {COLOR_CYAN}Álbum: {album_name} - Artista: {artist_name}{COLOR_RESET}")
                
                if modo == 'manual':
                    user_input = input(f"  Introduzca URL manualmente o Enter para dejar vacío: ")
                    if user_input.strip():
                        wiki_url = user_input.strip()
                        
                        # Si se proporciona una URL manualmente, obtenemos el contenido
                        print("  Obteniendo contenido de Wikipedia...")
                        content = get_wikipedia_content(wiki_url)
                        if content:
                            print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                        else:
                            print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
                    else:
                        wiki_url = ""
                        content = None
                else:  # modo auto normal
                    wiki_url = ""
                    content = None
        
        # Si tenemos una URL, procesamos diferente según la fuente
        content = None
        if wiki_url and from_musicbrainz:
            # Si proviene de MusicBrainz, añadimos automáticamente
            print(f"  {COLOR_GREEN}Añadiendo automáticamente enlace de MusicBrainz: {wiki_url}{COLOR_RESET}")
            print("  Obteniendo contenido de Wikipedia...")
            content = get_wikipedia_content(wiki_url)
            
            if content:
                # No mostramos extracto, sólo confirmación
                print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
            else:
                print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
            
            if modo == 'manual':
                # Abrimos el navegador para que el usuario pueda verificar
                try:
                    subprocess.Popen(["xdg-open", wiki_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    print(f"  {COLOR_RED}No se pudo abrir el navegador: {e}{COLOR_RESET}")
                    print(f"  URL: {wiki_url}")
            
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
                        print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                    else:
                        print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
            elif modo == 'auto' or modo == 'super-auto':
                print(f"  {COLOR_GREEN}URL añadida automáticamente en modo {modo}{COLOR_RESET}")
                # En modos automáticos, se añade directamente sin confirmación
        
        # Si viene de búsqueda en Wikipedia y no estamos en modo super-auto, mostramos para confirmación
        elif wiki_url and modo != 'super-auto':
            if modo == 'manual':
                try:
                    subprocess.Popen(["xdg-open", wiki_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    print(f"  {COLOR_RED}No se pudo abrir el navegador: {e}{COLOR_RESET}")
                    print(f"  URL: {wiki_url}")
                    
                print(f"  {COLOR_CYAN}Álbum: {album_name} - Artista: {artist_name}{COLOR_RESET}")
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
                    print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                else:
                    print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
        
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
        
        # Preguntamos si desea continuar después de cada 10 álbumes en modo manual
        if modo == 'manual' and (i + 1) % 10 == 0 and i < total - 1:
            if input(f"\n¿Desea continuar con la actualización? [{COLOR_GREEN}S{COLOR_RESET}/n]: ").lower() == 'n':
                break
    
    conn.close()
    print(f"\n{COLOR_GREEN}Actualización de álbumes completada.{COLOR_RESET}")

def update_content_only(db_path, entity_type, user_agent=None, modo='manual'):
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
        entity_name = 'artistas'
        
        # Para cada artista, conseguimos también sus álbumes
        entities_with_info = []
        for entity_id, entity_name, wiki_url in entities:
            albums = get_artist_albums(db_path, entity_id)
            entities_with_info.append((entity_id, entity_name, wiki_url, albums))
        
    elif entity_type == 'albums':
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
        entity_name = 'álbumes'
    
    elif entity_type == 'labels':
        cursor.execute("""
            SELECT id, name, wikipedia_url, country, founded_year
            FROM labels
            WHERE wikipedia_url IS NOT NULL AND wikipedia_url != '' 
            AND (wikipedia_content IS NULL OR wikipedia_content = '')
            ORDER BY id
        """)
        
        entities_with_info = cursor.fetchall()
        table_name = 'labels'
        entity_name = 'sellos'
    
    else:
        print(f"{COLOR_RED}Tipo de entidad no válido: {entity_type}{COLOR_RESET}")
        conn.close()
        return
    
    total = len(entities_with_info)
    
    if total == 0:
        print(f"{COLOR_YELLOW}No hay {entity_name} con URL pero sin contenido.{COLOR_RESET}")
        return
    
    print(f"{COLOR_CYAN}Procesando {total} {entity_name} para obtener contenido de Wikipedia...{COLOR_RESET}")
    
    if entity_type == 'artists':
        for i, (entity_id, entity_name, wiki_url, albums) in enumerate(entities_with_info):
            print(f"\n{COLOR_BOLD}[{i+1}/{total}] Obteniendo contenido para: {entity_name}{COLOR_RESET}")
            print(f"  URL: {wiki_url}")
            
            # Mostrar álbumes del artista
            if albums:
                print(f"  {COLOR_CYAN}Álbumes:{COLOR_RESET}")
                for album_name, album_year, album_label in albums:
                    label_info = f" - {album_label}" if album_label else ""
                    print(f"   - {album_name} ({album_year}){label_info}")
            else:
                print(f"  {COLOR_YELLOW}No hay álbumes registrados para este artista.{COLOR_RESET}")
            
            # Obtener contenido
            print(f"  {COLOR_BLUE}Obteniendo contenido...{COLOR_RESET}")
            content = get_wikipedia_content(wiki_url)
            
            if content:
                print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                
                # Actualizar la base de datos
                now = datetime.datetime.now()
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET wikipedia_content = ?, wikipedia_updated = ?
                    WHERE id = ?
                """, (content, now, entity_id))
                
                conn.commit()
            else:
                print(f"  {COLOR_RED}No se pudo obtener el contenido.{COLOR_RESET}")

                # Preguntamos si desea continuar después de cada 20 entidades
            if (i + 1) % 20 == 0 and i < total - 1:
                if input(f"\n¿Desea continuar con la actualización de contenido? [{COLOR_GREEN}S{COLOR_RESET}/n]: ").lower() == 'n':
                    break


    elif entity_type == 'albums':
        for i, (entity_id, entity_name, wiki_url, album_label, album_year, artist_name) in enumerate(entities_with_info):
            label_info = f" - Sello: {album_label}" if album_label else ""
            year_info = f" ({album_year})" if album_year else ""
            
            print(f"\n{COLOR_BOLD}[{i+1}/{total}] Obteniendo contenido para: {entity_name}{year_info} de {artist_name}{label_info}{COLOR_RESET}")
            print(f"  URL: {wiki_url}")
            
            # Obtener contenido
            print(f"  {COLOR_BLUE}Obteniendo contenido...{COLOR_RESET}")
            content = get_wikipedia_content(wiki_url)
            
            if content:
                print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                
                # Actualizar la base de datos
                now = datetime.datetime.now()
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET wikipedia_content = ?, wikipedia_updated = ?
                    WHERE id = ?
                """, (content, now, entity_id))
                
                conn.commit()
            else:
                print(f"  {COLOR_RED}No se pudo obtener el contenido.{COLOR_RESET}")

                # Preguntamos si desea continuar después de cada 20 entidades
            if (i + 1) % 20 == 0 and i < total - 1:
                if input(f"\n¿Desea continuar con la actualización de contenido? [{COLOR_GREEN}S{COLOR_RESET}/n]: ").lower() == 'n':
                    break
                
    elif entity_type == 'labels':
        for i, (entity_id, entity_name, wiki_url, country, founded_year) in enumerate(entities_with_info):
            country_info = f" - País: {country}" if country else ""
            year_info = f" - Fundado: {founded_year}" if founded_year else ""
            
            print(f"\n{COLOR_BOLD}[{i+1}/{total}] Obteniendo contenido para: {entity_name}{country_info}{year_info}{COLOR_RESET}")
            print(f"  URL: {wiki_url}")
            
            # Obtener contenido
            print(f"  {COLOR_BLUE}Obteniendo contenido...{COLOR_RESET}")
            content = get_wikipedia_content(wiki_url)
            
            if content:
                print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                
                # Actualizar la base de datos
                now = datetime.datetime.now()
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET wikipedia_content = ?, wikipedia_updated = ?
                    WHERE id = ?
                """, (content, now, entity_id))
                
                conn.commit()
            else:
                print(f"  {COLOR_RED}No se pudo obtener el contenido.{COLOR_RESET}")
    
            # Preguntamos si desea continuar después de cada 20 entidades
            if (i + 1) % 20 == 0 and i < total - 1:
                if input(f"\n¿Desea continuar con la actualización de contenido? [{COLOR_GREEN}S{COLOR_RESET}/n]: ").lower() == 'n':
                    break
        
    conn.close()
    print(f"\n{COLOR_GREEN}Actualización de contenido para {entity_name} completada.{COLOR_RESET}")



# SELLOS
def get_label_info(db_path, label_id):
    """Obtiene información básica sobre un sello"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name, country, founded_year, mbid
        FROM labels
        WHERE id = ?
    """, (label_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "name": result[0],
            "country": result[1],
            "founded_year": result[2],
            "mbid": result[3]
        }
    return None

def update_labels_wikipedia(db_path, log_file, user_agent=None, modo='manual', force_update=False):
    """Actualiza los enlaces y contenido de Wikipedia para sellos"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Cargar el registro
    log_data = load_log_file(log_file)
    last_id = 0 if force_update else log_data.get("last_label_id", 0)
    
    # Obtener sellos sin enlaces a Wikipedia o todos si force_update está activado
    if force_update:
        cursor.execute("""
            SELECT id, name, mbid
            FROM labels
            WHERE id > ?
            ORDER BY id
        """, (last_id,))
        print(f"{COLOR_CYAN}Modo force-update activado. Procesando todos los sellos...{COLOR_RESET}")
    else:
        cursor.execute("""
            SELECT id, name, mbid
            FROM labels
            WHERE id > ? AND (wikipedia_url IS NULL OR wikipedia_url = '')
            ORDER BY id
        """, (last_id,))
    
    labels = cursor.fetchall()
    total = len(labels)
    
    if total == 0:
        print(f"{COLOR_YELLOW}No hay sellos pendientes de actualizar enlaces a Wikipedia.{COLOR_RESET}")
        return
    
    print(f"{COLOR_CYAN}Procesando {total} sellos...{COLOR_RESET}")
    
    for i, (label_id, label_name, mb_url) in enumerate(labels):
        clear()
        print(f"\n{COLOR_BOLD}[{i+1}/{total}] Procesando sello: {label_name}{COLOR_RESET}")
        
        # Obtener información adicional del sello
        label_info = get_label_info(db_path, label_id)
        if label_info:
            country_info = f" - País: {label_info['country']}" if label_info.get('country') else ""
            year_info = f" - Fundado: {label_info['founded_year']}" if label_info.get('founded_year') else ""
            print(f"  {country_info}{year_info}")
        
        # Primero intentamos obtener el enlace desde MusicBrainz
        wiki_url = None
        from_musicbrainz = False
        if mb_url:
            print(f"  {COLOR_BLUE}Buscando enlace en MusicBrainz: {mb_url}{COLOR_RESET}")
            wiki_url = extract_wikipedia_url_from_musicbrainz(mb_url, user_agent)
            
            if wiki_url:
                print(f"  {COLOR_GREEN}Enlace encontrado en MusicBrainz: {wiki_url}{COLOR_RESET}")
                from_musicbrainz = True
        
        # Si no encontramos el enlace en MusicBrainz y estamos en modo super-auto, saltar este sello
        if not wiki_url and modo == 'super-auto':
            print(f"  {COLOR_YELLOW}No se encontró enlace en MusicBrainz y estamos en modo super-auto. Saltando...{COLOR_RESET}")
            # Actualizamos el archivo de registro
            log_data["last_label_id"] = label_id
            save_log_file(log_file, log_data)
            continue
        
        # Si no encontramos el enlace en MusicBrainz, buscamos en Wikipedia
        if not wiki_url and modo != 'super-auto':
            print(f"  {COLOR_BLUE}Buscando en Wikipedia...{COLOR_RESET}")
            wiki_url = search_wikipedia(label_name)
            
            if wiki_url:
                print(f"  {COLOR_GREEN}Enlace encontrado en Wikipedia: {wiki_url}{COLOR_RESET}")
            else:
                print(f"  {COLOR_YELLOW}No se encontró enlace en Wikipedia.{COLOR_RESET}")
        
        # Si tenemos una URL, procesamos diferente según la fuente
        content = None
        if wiki_url:
            # Si proviene de MusicBrainz, añadimos automáticamente
            if from_musicbrainz:
                print(f"  {COLOR_GREEN}Añadiendo automáticamente enlace de MusicBrainz: {wiki_url}{COLOR_RESET}")
                print("  Obteniendo contenido de Wikipedia...")
                content = get_wikipedia_content(wiki_url)
                
                if content:
                    # No mostramos extracto, sólo confirmación
                    print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                else:
                    print(f"  {COLOR_RED}No se pudo obtener el contenido.{COLOR_RESET}")
                
                if modo == 'manual':
                    # Abrimos el navegador para que el usuario pueda verificar
                    try:
                        subprocess.Popen(["xdg-open", wiki_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception as e:
                        print(f"  {COLOR_RED}No se pudo abrir el navegador: {e}{COLOR_RESET}")
                        print(f"  URL: {wiki_url}")
                
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
                            print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                        else:
                            print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
                elif modo == 'auto' or modo == 'super-auto':
                    print(f"  {COLOR_GREEN}URL añadida automáticamente en modo {modo}{COLOR_RESET}")

            # Si viene de búsqueda en Wikipedia y no estamos en modo super-auto, mostramos para confirmación
            elif modo != 'super-auto':
                if modo == 'manual':
                    try:
                        subprocess.Popen(["xdg-open", wiki_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception as e:
                        print(f"  {COLOR_RED}No se pudo abrir el navegador: {e}{COLOR_RESET}")
                        print(f"  URL: {wiki_url}")
                        
                    user_input = input(f"  Confirmar URL para '{label_name}' [Enter para confirmar '{wiki_url}', URL nueva, o 'n' para dejar vacío]: ")
                    
                    if user_input.lower() == 'n':
                        wiki_url = ""
                    elif user_input.strip():
                        wiki_url = user_input.strip()
                    
                # Si tenemos una URL final, obtenemos el contenido
                if wiki_url:
                    print("  Obteniendo contenido de Wikipedia...")
                    content = get_wikipedia_content(wiki_url)
                    if content:
                        print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                    else:
                        print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
        else:
            if modo == 'manual':
                print(f"{COLOR_CYAN}Sello: {label_name} {COLOR_RESET}")
                user_input = input(f"  Introduzca URL manualmente o Enter para dejar vacío: ")
                if user_input.strip():
                    wiki_url = user_input.strip()
                    
                    # Si se proporciona una URL manualmente, obtenemos el contenido
                    print("  Obteniendo contenido de Wikipedia...")
                    content = get_wikipedia_content(wiki_url)
                    if content:
                        print(f"  {COLOR_GREEN}Contenido obtenido ({len(content)} caracteres){COLOR_RESET}")
                    else:
                        print(f"  {COLOR_YELLOW}No se pudo obtener el contenido.{COLOR_RESET}")
                else:
                    wiki_url = ""
            else:
                wiki_url = ""
                
        # Actualizamos la base de datos con URL y contenido
        now = datetime.datetime.now()
        if wiki_url:
            cursor.execute("""
                UPDATE labels
                SET wikipedia_url = ?, wikipedia_content = ?, wikipedia_updated = ?
                WHERE id = ?
            """, (wiki_url, content or "", now, label_id))
        else:
            cursor.execute("""
                UPDATE labels
                SET wikipedia_url = ?, wikipedia_content = ?, wikipedia_updated = ?
                WHERE id = ?
            """, ("", "", now, label_id))
        
        conn.commit()
        
        # Actualizamos el archivo de registro
        log_data["last_label_id"] = label_id
        save_log_file(log_file, log_data)
        
        # Preguntamos si desea continuar después de cada 10 sellos en modo manual
        if modo == 'manual' and (i + 1) % 10 == 0 and i < total - 1:
            if input(f"\n¿Desea continuar con la actualización? [{COLOR_GREEN}S{COLOR_RESET}/n]: ").lower() == 'n':
                break
    
    conn.close()
    print(f"\n{COLOR_GREEN}Actualización de sellos completada.{COLOR_RESET}")

# Añadir enlace elegido a musicbrainz. ¡Ole tu!
# Add this function to contribute Wikipedia links back to MusicBrainz
def add_wikipedia_link_to_musicbrainz(mb_url, wiki_url, user_agent=None, mb_username=None, mb_password=None):
    """
    Adds a Wikipedia URL link to a MusicBrainz entity using the MusicBrainz API.
    Requires authentication with MusicBrainz.
    
    Args:
        mb_url (str): MusicBrainz URL of the entity
        wiki_url (str): Wikipedia URL to add
        user_agent (str, optional): User agent string
    
    Returns:
        bool: Success status
    """
    if not mb_url or not wiki_url:
        print(f"  {COLOR_RED}Error: Missing MusicBrainz URL or Wikipedia URL{COLOR_RESET}")
        return False
    
    # Parse the MusicBrainz URL to get entity type and ID
    entity_type = None
    mb_id = None
    
    if '/artist/' in mb_url:
        entity_type = 'artist'
        mb_id = mb_url.split('/artist/')[-1].split('/')[0].split('?')[0]
    elif '/release/' in mb_url:
        entity_type = 'release'
        mb_id = mb_url.split('/release/')[-1].split('/')[0].split('?')[0]
    elif '/label/' in mb_url:
        entity_type = 'label'
        mb_id = mb_url.split('/label/')[-1].split('/')[0].split('?')[0]
    else:
        print(f"  {COLOR_RED}Unsupported MusicBrainz entity type in URL: {mb_url}{COLOR_RESET}")
        return False
    
    # Check if credentials are available
    #mb_username = os.environ.get('MUSICBRAINZ_USERNAME')
    #mb_password = os.environ.get('MUSICBRAINZ_PASSWORD')
    print(f"mb_username {mb_username}")
    print(f"mb_password {mb_password}")


    if not mb_username or not mb_password:
        print(f"  {COLOR_YELLOW}MusicBrainz credentials not found in environment variables.{COLOR_RESET}")
        
        # Ask for credentials if not available
        use_creds = input(f"  Do you want to provide MusicBrainz credentials now? (y/n): ")
        if use_creds.lower() != 'y':
            print(f"  {COLOR_YELLOW}Skipping MusicBrainz contribution.{COLOR_RESET}")
            return False
        
        mb_username = input("  Enter your MusicBrainz username: ")
        mb_password = input("  Enter your MusicBrainz password: ")
    
    # Prepare the API endpoint
    endpoint = f"{MUSICBRAINZ_API_BASE}/{entity_type}/{mb_id}/url-rels"
    
    headers = {
        "User-Agent": user_agent or MUSICBRAINZ_USER_AGENT,
        "Content-Type": "application/json"
    }
    
    # Prepare the data for the URL relationship
    data = {
        "target": wiki_url,
        "type": "wikipedia",
        "editNote": "Added Wikipedia link"
    }
    
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        
        print(f"  {COLOR_BLUE}Adding Wikipedia link to MusicBrainz...{COLOR_RESET}")
        
        # POST request to add the URL relationship
        response = requests.post(
            endpoint, 
            json=data, 
            headers=headers,
            auth=HTTPBasicAuth(mb_username, mb_password),
            timeout=30
        )
        
        # Respect rate limits
        time.sleep(MUSICBRAINZ_RATE_LIMIT)
        
        if response.status_code in [201, 200]:
            print(f"  {COLOR_GREEN}Successfully added Wikipedia link to MusicBrainz!{COLOR_RESET}")
            return True
        else:
            print(f"  {COLOR_RED}Failed to add link to MusicBrainz: HTTP {response.status_code}{COLOR_RESET}")
            print(f"  {COLOR_YELLOW}Response: {response.text[:200]}...{COLOR_RESET}")
            return False
            
    except Exception as e:
        print(f"  {COLOR_RED}Error adding link to MusicBrainz: {str(e)}{COLOR_RESET}")
        traceback.print_exc()
        return False




def clear():
    # Para sistemas UNIX (Linux/Mac)
    if os.name == 'posix':
        os.system('clear')
    # Para sistemas Windows
    elif os.name == 'nt':
        os.system('cls')

def main(config=None):
    """
    Main function that can be called either directly or from db_creator
    
    Args:
        config (dict, optional): Configuration dictionary when called from db_creator
    """
    print(f"{COLOR_BOLD}Iniciando wikilinks_desde_mb...{COLOR_RESET}")
    
    # If called directly (not from db_creator)
    if config is None:
        # Configurar argumentos de línea de comandos
        parser = argparse.ArgumentParser(description='Actualizar enlaces y contenido de Wikipedia en la base de datos de música')
        parser.add_argument('--config', help='Archivo de configuración JSON')
        parser.add_argument('--log-file', help='Archivo de registro para seguimiento del progreso')
        parser.add_argument('--db-path', help='Ruta a la base de datos SQLite')
        parser.add_argument('--type', help='Tipo de entidad a actualizar (artists, albums, artists_content, albums_content, labels, labels_content)')
        parser.add_argument('--user-agent', help='User-Agent para las peticiones a MusicBrainz')
        parser.add_argument('--modo', help='Tipo de lanzamiento, auto o manual')
        parser.add_argument('--force-update', action='store_true', help='Forzar actualización de todos los elementos, incluso los que ya tienen enlaces')
        
        args = parser.parse_args()
        
        try:
            # Cargar configuración
            config_file = args.config
            if not config_file:
                print(f"{COLOR_RED}Error: Debe especificar un archivo de configuración{COLOR_RESET}")
                return
                
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Combinar configuraciones
            config = {}
            config.update(config_data.get("common", {}))
            config.update(config_data.get("wikilinks_desde_mb", {}))
    
            # Command line arguments override config file
            if args.log_file:
                config['log_file'] = args.log_file
            if args.db_path:
                config['db_path'] = args.db_path
            if args.type:
                config['type'] = args.type
            if args.user_agent:
                config['user_agent'] = args.user_agent
            if args.modo:
                config['modo'] = args.modo
            if args.force_update:
                config['force_update'] = True
        except Exception as e:
            print(f"{COLOR_RED}Error loading configuration: {e}{COLOR_RESET}")
            return
    
    # Dump the configuration for debugging
    print(f"{COLOR_CYAN}Configuración recibida:{COLOR_RESET}")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # Extract necessary parameters with fallbacks
    db_path = config.get('db_path')
    if not db_path:
        print(f"{COLOR_RED}Error: Database path not specified{COLOR_RESET}")
        return
    
    if not os.path.exists(db_path):
        print(f"{COLOR_RED}Error: Database file {db_path} doesn't exist{COLOR_RESET}")
        return
        
    log_file = config.get('log_file', 'wikilinks.log')
    user_agent = config.get('user_agent', "MusicLibraryWikipediaUpdater/1.0 (your-email@example.com)")
    force_update = config.get('force_update', False)
    
    # Try to get update_type from 'type', 'update_type', or 'wikilinks_desde_mb.type'
    update_type = None
    for key in ['type', 'update_type']:
        if key in config and config[key]:
            update_type = config[key]
            break
    
    # Also check in nested structure
    if not update_type and 'wikilinks_desde_mb' in config and isinstance(config['wikilinks_desde_mb'], dict):
        for key in ['type', 'update_type']:
            if key in config['wikilinks_desde_mb'] and config['wikilinks_desde_mb'][key]:
                update_type = config['wikilinks_desde_mb'][key]
                break

    if not update_type:
        print(f"{COLOR_RED}Error: Must specify update type (artists, albums, artists_content, albums_content, labels, labels_content){COLOR_RESET}")
        print(f"{COLOR_YELLOW}Please add 'type' or 'update_type' to your JSON configuration in the wikilinks_desde_mb section{COLOR_RESET}")
        return

    modo = config.get('modo')

    print(f"{COLOR_CYAN}Update type: {update_type}{COLOR_RESET}")
    print(f"{COLOR_CYAN}Database path: {db_path}{COLOR_RESET}")
    print(f"{COLOR_CYAN}Log file: {log_file}{COLOR_RESET}")
    print(f"{COLOR_CYAN}User-Agent: {user_agent}{COLOR_RESET}")
    print(f"{COLOR_CYAN}Force update: {force_update}{COLOR_RESET}")

    # Inicializar la base de datos
    init_database(db_path)
    
    # Mostrar estadísticas iniciales
    stats = get_database_stats(db_path)
    print(f"\n{COLOR_BOLD}=== Estadísticas de Enlaces y Contenido ==={COLOR_RESET}")
    print(f"{COLOR_CYAN}Artistas: {stats['artists_with_wiki']}/{stats['total_artists']} enlaces ({stats['artists_missing_wiki']} faltan){COLOR_RESET}")
    print(f"{COLOR_CYAN}Artistas: {stats['artists_with_content']}/{stats['total_artists']} con contenido{COLOR_RESET}")
    print(f"{COLOR_CYAN}Álbumes: {stats['albums_with_wiki']}/{stats['total_albums']} enlaces ({stats['albums_missing_wiki']} faltan){COLOR_RESET}")
    print(f"{COLOR_CYAN}Álbumes: {stats['albums_with_content']}/{stats['total_albums']} con contenido{COLOR_RESET}")
    
    # Mostrar estadísticas de sellos si están disponibles
    if 'labels_with_wiki' in stats:
        print(f"{COLOR_CYAN}Sellos: {stats['labels_with_wiki']}/{stats['total_labels']} enlaces ({stats['labels_missing_wiki']} faltan){COLOR_RESET}")
        print(f"{COLOR_CYAN}Sellos: {stats['labels_with_content']}/{stats['total_labels']} con contenido{COLOR_RESET}")
    
    print(f"{COLOR_BOLD}=========================================={COLOR_RESET}\n")
    
    # Ejecutar la actualización según el tipo
    if update_type == 'artists':
        update_artists_wikipedia(db_path, log_file, user_agent, modo, force_update)
    elif update_type == 'albums':
        update_albums_wikipedia(db_path, log_file, user_agent, modo, force_update)
    elif update_type == 'artists_content':
        update_content_only(db_path, 'artists', user_agent, modo)
    elif update_type == 'albums_content':
        update_content_only(db_path, 'albums', user_agent, modo)
    elif update_type == 'labels':
        update_labels_wikipedia(db_path, log_file, user_agent, modo, force_update)
    elif update_type == 'labels_content':
        update_content_only(db_path, 'labels', user_agent, modo)
    else:
        print(f"{COLOR_RED}Error: Unknown update type: {update_type}{COLOR_RESET}")
        return
    
    # Mostrar estadísticas finales
    stats = get_database_stats(db_path)
    print(f"\n{COLOR_BOLD}=== Estadísticas Finales ==={COLOR_RESET}")
    print(f"{COLOR_CYAN}Artistas: {stats['artists_with_wiki']}/{stats['total_artists']} enlaces ({stats['artists_missing_wiki']} faltan){COLOR_RESET}")
    print(f"{COLOR_CYAN}Artistas: {stats['artists_with_content']}/{stats['total_artists']} con contenido{COLOR_RESET}")
    print(f"{COLOR_CYAN}Álbumes: {stats['albums_with_wiki']}/{stats['total_albums']} enlaces ({stats['albums_missing_wiki']} faltan){COLOR_RESET}")
    print(f"{COLOR_CYAN}Álbumes: {stats['albums_with_content']}/{stats['total_albums']} con contenido{COLOR_RESET}")
    
    # Mostrar estadísticas de sellos si están disponibles
    if 'labels_with_wiki' in stats:
        print(f"{COLOR_CYAN}Sellos: {stats['labels_with_wiki']}/{stats['total_labels']} enlaces ({stats['labels_missing_wiki']} faltan){COLOR_RESET}")
        print(f"{COLOR_CYAN}Sellos: {stats['labels_with_content']}/{stats['total_labels']} con contenido{COLOR_RESET}")
    
    print(f"{COLOR_BOLD}============================{COLOR_RESET}\n")

if __name__ == "__main__":
    main()