import os
import sys
import sqlite3
import requests
import json
import time
from datetime import datetime
import re



# PROJECT_ROOT será proporcionado por db_creator.py
# No necesitamos importar BaseModule

def create_table(conn):
    """Crea la tabla artists_setlistfm si no existe"""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS artists_setlistfm (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artist_id INTEGER NOT NULL,
        artist_name TEXT NOT NULL,
        setlist_id TEXT NOT NULL UNIQUE,
        eventDate TEXT,
        artist_url TEXT,
        venue_id TEXT,
        venue_name TEXT,
        city_name TEXT,
        city_state TEXT,
        coords TEXT,
        country_name TEXT,
        country_code TEXT,
        url TEXT,
        tour TEXT,
        sets TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()

def create_places_table(conn):
    """Crea la tabla places_setlistfm si no existe"""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS places_setlistfm (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venue_id TEXT NOT NULL UNIQUE,
        venue_name TEXT,
        city_name TEXT,
        city_state TEXT,
        coords TEXT,
        country_name TEXT,
        country_code TEXT,
        artists_num INTEGER,
        conciertos_num INTEGER,
        artists_names TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()

def get_artists(conn):
    """Obtiene todos los artistas de la base de datos con sus MBIDs"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, mbid FROM artists")
    return cursor.fetchall()

def fetch_setlists_by_mbid(mbid, api_key, page=1, year=0):
    """Obtiene los setlists de un artista por MBID de la API de setlist.fm"""
    url = f"https://api.setlist.fm/rest/1.0/search/setlists"
    headers = {
        'Accept': 'application/json',
        'x-api-key': api_key
    }
    params = {
        'artistMbid': mbid,
        'p': page
    }
    
    # Añadir el filtro de año si se ha especificado
    if year > 0:
        params['year'] = year
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 404:
        return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
    
    if response.status_code == 429:  # Too Many Requests
        print(f"Rate limit alcanzado para MBID {mbid}, esperando 60 segundos...")
        time.sleep(60)
        return fetch_setlists_by_mbid(mbid, api_key, page, year)
    
    if response.status_code != 200:
        print(f"Error al obtener setlists para MBID {mbid}: {response.status_code}")
        print(response.text)
        return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
    
    return response.json()

def fetch_setlists_by_name(artist_name, api_key, page=1, year=0):
    """Obtiene los setlists de un artista por nombre de la API de setlist.fm"""
    url = f"https://api.setlist.fm/rest/1.0/search/setlists"
    headers = {
        'Accept': 'application/json',
        'x-api-key': api_key
    }
    params = {
        'artistName': artist_name,
        'p': page
    }
    
    # Añadir el filtro de año si se ha especificado
    if year > 0:
        params['year'] = year
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 404:
        return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
    
    if response.status_code == 429:  # Too Many Requests
        print(f"Rate limit alcanzado para {artist_name}, esperando 60 segundos...")
        time.sleep(5)
        return fetch_setlists_by_name(artist_name, api_key, page, year)
    
    if response.status_code != 200:
        print(f"Error al obtener setlists para {artist_name}: {response.status_code}")
        print(response.text)
        return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
    
    return response.json()

def save_setlists(conn, artist_id, artist_name, setlists):
    """Guarda los setlists en la base de datos"""
    cursor = conn.cursor()
    
    for setlist in setlists:
        # Extraer los valores que necesitamos
        setlist_id = setlist.get('id', '')
        eventDate = setlist.get('eventDate', '')
        
        artist_data = setlist.get('artist', {})
        artist_url = artist_data.get('url', '')
        
        venue_data = setlist.get('venue', {})
        venue_id = venue_data.get('id', '')
        venue_name = venue_data.get('name', '')
        
        city_data = venue_data.get('city', {})
        city_name = city_data.get('name', '')
        city_state = city_data.get('state', '')
        
        coords_data = city_data.get('coords', {})
        coords = f"{coords_data.get('lat', '')},{coords_data.get('long', '')}" if coords_data else ''
        
        country_data = city_data.get('country', {})
        country_name = country_data.get('name', '')
        country_code = country_data.get('code', '')
        
        url = setlist.get('url', '')
        tour_data = setlist.get('tour', {})
        tour = tour_data.get('name', '') if tour_data else ''
        
        sets_data = setlist.get('sets', {})
        sets_json = json.dumps(sets_data) if sets_data else '{}'
        
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO artists_setlistfm
            (artist_id, artist_name, setlist_id, eventDate, artist_url, venue_id, venue_name, 
            city_name, city_state, coords, country_name, country_code, url, tour, sets, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                artist_id, artist_name, setlist_id, eventDate, artist_url, venue_id, venue_name,
                city_name, city_state, coords, country_name, country_code, url, tour, sets_json, 
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        except Exception as e:
            print(f"Error al guardar setlist {setlist_id} para {artist_name}: {e}")
    
    conn.commit()

def process_artist(conn, artist_id, artist_name, artist_mbid, api_key, force_update=False, interactive=False, year=0):
    """Procesa los setlists de un artista, primero por MBID y luego por nombre si es necesario"""
    cursor = conn.cursor()
    
    # Verificar si ya tenemos setlists de este artista (si estamos filtrando por año, no omitir)
    if year == 0:
        cursor.execute("SELECT COUNT(*) FROM artists_setlistfm WHERE artist_id = ?", (artist_id,))
        count = cursor.fetchone()[0]
        
        if count > 0 and not force_update:
            if interactive:
                update = input(f"Ya existen {count} setlists para {artist_name}. ¿Actualizar? (s/n): ")
                if update.lower() != 's':
                    print(f"Omitiendo {artist_name}...")
                    return
            else:
                print(f"Omitiendo {artist_name} (ya tiene {count} setlists)...")
                return
    
    # Si estamos filtrando por año, mostrar mensaje apropiado
    if year > 0:
        print(f"Procesando setlists para {artist_name} del año {year}...")
    else:
        print(f"Procesando setlists para {artist_name}...")
    
    # Estrategia 1: Buscar por MBID primero
    found_by_mbid = False
    if artist_mbid:
        print(f"  Intentando búsqueda por MBID: {artist_mbid}")
        page = 1
        total_setlists = 0
        
        while True:
            print(f"  Página {page} (MBID)...")
            response = fetch_setlists_by_mbid(artist_mbid, api_key, page, year)
            
            setlists = response.get('setlist', [])
            if not setlists:
                break
            
            save_setlists(conn, artist_id, artist_name, setlists)
            found_by_mbid = True
            
            total_setlists += len(setlists)
            
            # Verificar si hay más páginas
            total = response.get('total', 0)
            items_per_page = response.get('itemsPerPage', 20)
            total_pages = (total + items_per_page - 1) // items_per_page
            
            if page >= total_pages:
                break
            
            page += 1
            # Respetar los límites de la API
            time.sleep(1)
        
        if found_by_mbid:
            if year > 0:
                print(f"Guardados {total_setlists} setlists para {artist_name} del año {year} mediante MBID")
            else:
                print(f"Guardados {total_setlists} setlists para {artist_name} mediante MBID")
    
    # Estrategia 2: Si no hay MBID o no se encontraron resultados, buscar por nombre
    if not artist_mbid or not found_by_mbid:
        if not artist_mbid:
            print(f"  No hay MBID disponible para {artist_name}, buscando por nombre")
        else:
            print(f"  No se encontraron resultados por MBID para {artist_name}, buscando por nombre")
        
        page = 1
        total_setlists = 0
        
        while True:
            print(f"  Página {page} (nombre)...")
            response = fetch_setlists_by_name(artist_name, api_key, page, year)
            
            setlists = response.get('setlist', [])
            if not setlists:
                break
            
            save_setlists(conn, artist_id, artist_name, setlists)
            
            total_setlists += len(setlists)
            
            # Verificar si hay más páginas
            total = response.get('total', 0)
            items_per_page = response.get('itemsPerPage', 20)
            total_pages = (total + items_per_page - 1) // items_per_page
            
            if page >= total_pages:
                break
            
            page += 1
            # Respetar los límites de la API
            time.sleep(1)
        
        if year > 0:
            print(f"Guardados {total_setlists} setlists para {artist_name} del año {year} mediante nombre")
        else:
            print(f"Guardados {total_setlists} setlists para {artist_name} mediante nombre")

def process_places(conn, force_update=False):
    """Procesa los lugares de conciertos a partir de los setlists"""
    print("\n=== Procesando lugares de conciertos ===")
    
    # Crear la tabla de lugares si no existe
    create_places_table(conn)
    
    cursor = conn.cursor()
    
    # Obtener todos los venues únicos con sus datos
    cursor.execute('''
    SELECT DISTINCT venue_id, venue_name, city_name, city_state, coords, country_name, country_code
    FROM artists_setlistfm
    WHERE venue_id IS NOT NULL AND venue_id != ''
    ''')
    
    venues = cursor.fetchall()
    print(f"Encontrados {len(venues)} lugares únicos")
    
    # Para cada venue, calcular estadísticas
    for venue in venues:
        venue_id, venue_name, city_name, city_state, coords, country_name, country_code = venue
        
        # Verificar si ya existe el lugar en la tabla places_setlistfm
        cursor.execute("SELECT id FROM places_setlistfm WHERE venue_id = ?", (venue_id,))
        exists = cursor.fetchone()
        
        if exists and not force_update:
            print(f"  Omitiendo lugar: {venue_name} (ya existe)")
            continue
        
        print(f"  Procesando lugar: {venue_name}")
        
        # Obtener todos los artistas distintos que han tocado en este venue
        cursor.execute('''
        SELECT DISTINCT artist_id, artist_name
        FROM artists_setlistfm
        WHERE venue_id = ?
        ''', (venue_id,))
        
        artists = cursor.fetchall()
        artists_num = len(artists)
        artists_names = ', '.join([artist[1] for artist in artists])
        
        # Obtener el número total de conciertos en este venue
        cursor.execute('''
        SELECT COUNT(*)
        FROM artists_setlistfm
        WHERE venue_id = ?
        ''', (venue_id,))
        
        conciertos_num = cursor.fetchone()[0]
        
        # Insertar o actualizar la información del lugar
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO places_setlistfm
            (venue_id, venue_name, city_name, city_state, coords, country_name, country_code,
            artists_num, conciertos_num, artists_names, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                venue_id, venue_name, city_name, city_state, coords, country_name, country_code,
                artists_num, conciertos_num, artists_names, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            print(f"    Guardado: {artists_num} artistas, {conciertos_num} conciertos")
        except Exception as e:
            print(f"    Error al guardar lugar {venue_id}: {e}")
    
    conn.commit()
    print("Proceso de lugares completado")


def add_setlistfm_id_column(conn):
    """Añade la columna setlistfm_id a la tabla artists si no existe"""
    cursor = conn.cursor()
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(artists)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'setlistfm_id' not in columns:
            cursor.execute("ALTER TABLE artists ADD COLUMN setlistfm_id TEXT")
            conn.commit()
            print("Columna setlistfm_id añadida a la tabla artists")
    except Exception as e:
        print(f"Error al añadir columna setlistfm_id: {e}")

def get_setlistfm_id_by_mbid(mbid, api_key):
    """Obtiene el setlistfm_id de un artista usando su MBID"""
    url = f"https://api.setlist.fm/rest/1.0/search/artists"
    headers = {
        'Accept': 'application/json',
        'x-api-key': api_key
    }
    params = {
        'artistMbid': mbid,
        'p': 1,
        'sort': 'sortName'
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 404:
        return None
    
    if response.status_code == 429:  # Too Many Requests
        print(f"Rate limit alcanzado para MBID {mbid}, esperando 60 segundos...")
        time.sleep(60)
        return get_setlistfm_id_by_mbid(mbid, api_key)
    
    if response.status_code != 200:
        print(f"Error al obtener setlistfm_id para MBID {mbid}: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    artists = data.get('artist', [])
    
    if artists and len(artists) > 0:
        artist_url = artists[0].get('url')
        if artist_url:
            # Extraer el ID de la URL
            # https://www.setlist.fm/setlists/the-beatles-23d6a88b.html
            match = re.search(r'-([0-9a-f]+)\.html$', artist_url)
            if match:
                return match.group(1)
    
    return None

def update_setlistfm_ids(conn, api_key, force_update=False):
    """Actualiza los setlistfm_id para todos los artistas con MBID"""
    print("\n=== Actualizando IDs de setlist.fm ===")
    
    # Añadir columna si no existe
    add_setlistfm_id_column(conn)
    
    cursor = conn.cursor()
    
    # Obtener artistas con MBID pero sin setlistfm_id o si force_update es True
    if force_update:
        cursor.execute("SELECT id, name, mbid FROM artists WHERE mbid IS NOT NULL")
    else:
        cursor.execute("SELECT id, name, mbid FROM artists WHERE mbid IS NOT NULL AND (setlistfm_id IS NULL OR setlistfm_id = '')")
    
    artists = cursor.fetchall()
    total_artists = len(artists)
    print(f"Encontrados {total_artists} artistas para actualizar")
    
    updated = 0
    for i, (artist_id, artist_name, mbid) in enumerate(artists, 1):
        print(f"Procesando {artist_name} ({i}/{total_artists})")
        
        setlistfm_id = get_setlistfm_id_by_mbid(mbid, api_key)
        
        if setlistfm_id:
            try:
                cursor.execute("UPDATE artists SET setlistfm_id = ? WHERE id = ?", (setlistfm_id, artist_id))
                conn.commit()
                updated += 1
                print(f"  Actualizado: {artist_name} - ID: {setlistfm_id}")
            except Exception as e:
                print(f"  Error al actualizar {artist_name}: {e}")
        else:
            print(f"  No se encontró ID de setlist.fm para {artist_name}")
        
        # Respetar límites de la API
        time.sleep(1)
    
    print(f"Actualizaciones completadas: {updated} de {total_artists} artistas")



def main(config=None):
    """Función principal"""
    if config is None:
        config = {}
    
    # Obtener la API key de setlist.fm
    api_key = config.get('setlistfm_apikey', os.environ.get('SETLISTFM_APIKEY'))
    if not api_key:
        print("Error: No se ha proporcionado la API key de setlist.fm")
        print("Puedes proporcionarla en el archivo de configuración como 'setlistfm_apikey'")
        print("o como variable de entorno SETLISTFM_APIKEY")
        return 1
    
    # Obtener la ruta de la base de datos
    db_path = config.get('db_path')
    if not db_path:
        print("Error: No se ha proporcionado la ruta de la base de datos")
        return 1
    
    # Configurar el modo interactivo
    interactive = config.get('interactive', False)
    
    # Configurar la actualización forzada
    force_update = config.get('force_update', False)
    
    # Configurar límite de artistas (para pruebas)
    limit = config.get('limit', 0)
    
    # Artistas específicos a procesar
    artist_names = config.get('artist_names', [])
    artist_ids = config.get('artist_ids', [])
    
    # Año específico para filtrar setlists
    year = int(config.get('year', 0))
    
    # Verificar si se debe procesar lugares
    process_places_flag = config.get('process_places', False)
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    
    try:
        # Crear la tabla si no existe
        create_table(conn)
        
        # Obtener todos los artistas con sus MBIDs
        artists = get_artists(conn)
        
        if limit > 0:
            artists = artists[:limit]
        
        if artist_names:
            artists = [a for a in artists if a[1] in artist_names]
        
        if artist_ids:
            artists = [a for a in artists if a[0] in artist_ids]
        
        # Mostrar mensaje sobre el filtro de año
        if year > 0:
            print(f"Filtrando setlists solo para el año {year}")
        
        for artist_id, artist_name, artist_mbid in artists:
            process_artist(conn, artist_id, artist_name, artist_mbid, api_key, force_update, interactive, year)
        
        # Procesar lugares si se ha especificado
        if process_places_flag:
            process_places(conn, force_update)
        
        
        # Actualizar setlistfm_ids si se ha especificado
        update_setlistfm_ids(conn, api_key, force_update)
    
    finally:
        conn.close()
    
    print("Proceso completado")
    return 0

if __name__ == "__main__":
    # Este bloque solo se ejecutará si el script se llama directamente
    # y no a través de db_creator.py
    print("Este script está diseñado para ser ejecutado a través de db_creator.py")
    sys.exit(1)