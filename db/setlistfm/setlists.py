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
    
    # Crear tabla para tracking de búsquedas vacías
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS artists_setlistfm_searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artist_id INTEGER NOT NULL UNIQUE,
        artist_name TEXT NOT NULL,
        last_search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        found_setlists INTEGER DEFAULT 0,
        search_method TEXT
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



def is_date_after(setlist_date, from_date):
    """Compara si la fecha del setlist es posterior a from_date"""
    if not setlist_date or not from_date:
        return True
    
    try:
        # Convertir ambas fechas a formato comparable (YYYY-MM-DD)
        def parse_date(date_str):
            if '-' in date_str:
                parts = date_str.split('-')
                if len(parts) == 3:
                    if len(parts[0]) == 4:  # YYYY-MM-DD
                        return date_str
                    elif len(parts[2]) == 4:  # DD-MM-YYYY
                        return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            return date_str
        
        setlist_normalized = parse_date(setlist_date)
        from_normalized = parse_date(from_date)
        
        return setlist_normalized > from_normalized
    except:
        return True  # En caso de error, incluir el setlist


def filter_setlists_by_date(setlists, from_date):
    """Filtra setlists que sean posteriores a from_date"""
    if not from_date:
        return setlists
    
    filtered = []
    for setlist in setlists:
        event_date = setlist.get('eventDate', '')
        if is_date_after(event_date, from_date):
            filtered.append(setlist)
    
    return filtered



def get_latest_setlist_date(conn, artist_id):
    """Obtiene la fecha del setlist más reciente para un artista"""
    cursor = conn.cursor()
    cursor.execute('''
    SELECT MAX(eventDate) 
    FROM artists_setlistfm 
    WHERE artist_id = ? AND eventDate IS NOT NULL AND eventDate != ''
    ''', (artist_id,))
    
    result = cursor.fetchone()
    if result and result[0]:
        # Convertir la fecha al formato correcto antes de devolverla
        raw_date = result[0]
        # Si la fecha está en formato DD-MM-YYYY, devolverla tal como está
        if '-' in raw_date and len(raw_date.split('-')) == 3:
            parts = raw_date.split('-')
            if len(parts[2]) == 4:  # DD-MM-YYYY
                return raw_date
            elif len(parts[0]) == 4:  # YYYY-MM-DD, convertir
                year, month, day = parts
                return f"{day.zfill(2)}-{month.zfill(2)}-{year}"
        return raw_date
    return None


def fetch_setlists_by_mbid(mbid, api_key, page=1, year=0, from_date=None, retry_count=0):
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
    
    # NO usar filtro de fecha - la API de setlist.fm no soporta rangos de fechas
    # El filtrado se hará después al procesar los resultados
    if from_date:
        print(f"    Filtrando setlists posteriores a: {from_date} (filtrado local)")
    
    try:
        response = requests.get(url, headers=headers, params=params)
    except requests.RequestException as e:
        print(f"Error de conexión para MBID {mbid}: {e}")
        return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
    
    if response.status_code == 404:
        return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
    
    if response.status_code == 429:  # Too Many Requests
        if retry_count >= 2:
            print(f"Rate limit alcanzado para MBID {mbid} después de 2 intentos, saltando al siguiente artista...")
            return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
        
        print(f"Rate limit alcanzado para MBID {mbid}, esperando 60 segundos... (intento {retry_count + 1}/2)")
        time.sleep(60)
        return fetch_setlists_by_mbid(mbid, api_key, page, year, from_date, retry_count + 1)
    
    if response.status_code != 200:
        print(f"Error al obtener setlists para MBID {mbid}: {response.status_code}")
        print(response.text)
        return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
    
    return response.json()


def fetch_setlists_by_name(artist_name, api_key, page=1, year=0, from_date=None, retry_count=0):
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
    
    # NO usar filtro de fecha - la API de setlist.fm no soporta rangos de fechas
    # El filtrado se hará después al procesar los resultados
    if from_date:
        print(f"    Filtrando setlists posteriores a: {from_date} (filtrado local)")
    
    try:
        response = requests.get(url, headers=headers, params=params)
    except requests.RequestException as e:
        print(f"Error de conexión para {artist_name}: {e}")
        return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
    
    if response.status_code == 404:
        return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
    
    if response.status_code == 429:  # Too Many Requests
        if retry_count >= 2:
            print(f"Rate limit alcanzado para {artist_name} después de 2 intentos, saltando al siguiente artista...")
            return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
            
        print(f"Rate limit alcanzado para {artist_name}, esperando 5 segundos... (intento {retry_count + 1}/2)")
        time.sleep(5)
        return fetch_setlists_by_name(artist_name, api_key, page, year, from_date, retry_count + 1)
    
    if response.status_code != 200:
        print(f"Error al obtener setlists para {artist_name}: {response.status_code}")
        print(response.text)
        return {"setlist": [], "total": 0, "page": 1, "itemsPerPage": 20}
    
    return response.json()


def process_artist(conn, artist_id, artist_name, artist_mbid, api_key, force_update=False, interactive=False, year=0, new_only=False):
    """Procesa los setlists de un artista, primero por MBID y luego por nombre si es necesario"""
    cursor = conn.cursor()
    
    # Verificar si debemos omitir este artista por búsqueda reciente sin resultados
    if should_skip_artist(conn, artist_id, force_update, year, new_only):
        return
    
    # Obtener la fecha del último setlist para buscar solo nuevos
    from_date = None
    if not force_update and year == 0:
        latest_date = get_latest_setlist_date(conn, artist_id)
        if latest_date:
            from_date = latest_date  # Ya viene en formato correcto
            print(f"  Buscando setlists desde: {latest_date}")
    
    # Verificar si ya tenemos setlists de este artista (si estamos filtrando por año, no omitir)
    if year == 0 and not new_only:
        cursor.execute("SELECT COUNT(*) FROM artists_setlistfm WHERE artist_id = ?", (artist_id,))
        count = cursor.fetchone()[0]
        
        if count > 0 and not force_update:
            if interactive:
                update = input(f"Ya existen {count} setlists para {artist_name}. ¿Actualizar? (s/n): ")
                if update.lower() != 's':
                    print(f"Omitiendo {artist_name}...")
                    return
            else:
                print(f"Buscando setlists nuevos para {artist_name} (tiene {count} setlists)...")
    
    # Si estamos filtrando por año, mostrar mensaje apropiado
    if year > 0:
        print(f"Procesando setlists para {artist_name} del año {year}...")
    else:
        print(f"Procesando setlists para {artist_name}...")
    
    total_setlists_found = 0
    search_method = ""
    
    # Estrategia 1: Buscar por MBID primero
    found_by_mbid = False
    if artist_mbid:
        print(f"  Intentando búsqueda por MBID: {artist_mbid}")
        page = 1
        setlists_by_mbid = 0
        
        while True:
            print(f"  Página {page} (MBID)...")
            response = fetch_setlists_by_mbid(artist_mbid, api_key, page, year, from_date)
            
            setlists = response.get('setlist', [])
            if not setlists:
                break
            
            # Filtrar por fecha localmente si es necesario
            if from_date:
                setlists = filter_setlists_by_date(setlists, from_date)
                if setlists:
                    print(f"    Después del filtro de fecha: {len(setlists)} setlists")
            
            # Filtrar setlists que ya existen en la base de datos
            new_setlists = []
            for setlist in setlists:
                setlist_id = setlist.get('id', '')
                cursor.execute("SELECT id FROM artists_setlistfm WHERE setlist_id = ?", (setlist_id,))
                if not cursor.fetchone():
                    new_setlists.append(setlist)
            
            if new_setlists:
                save_setlists(conn, artist_id, artist_name, new_setlists)
                found_by_mbid = True
                
                setlists_by_mbid += len(new_setlists)
                total_setlists_found += len(new_setlists)
                print(f"    Guardados {len(new_setlists)} setlists nuevos de {len(setlists)} encontrados")
            else:
                print(f"    No hay setlists nuevos en esta página")
            
            # Si estamos filtrando por fecha y no hay resultados nuevos, podemos parar
            # ya que los setlists vienen ordenados por fecha (más recientes primero)
            if from_date and not new_setlists and len(setlists) > 0:
                print(f"    No hay setlists más recientes, terminando búsqueda")
                break
            
            # Verificar si hay más páginas
            total = response.get('total', 0)
            items_per_page = response.get('itemsPerPage', 20)
            total_pages = (total + items_per_page - 1) // items_per_page
            
            if page >= total_pages:
                break
            
            page += 1
            # Respetar los límites de la API (máximo 2 llamadas por segundo)
            time.sleep(0.5)
        
        if found_by_mbid:
            search_method = "MBID"
            if year > 0:
                print(f"Guardados {setlists_by_mbid} setlists nuevos para {artist_name} del año {year} mediante MBID")
            else:
                print(f"Guardados {setlists_by_mbid} setlists nuevos para {artist_name} mediante MBID")
    
    # Estrategia 2: Si no hay MBID o no se encontraron resultados, buscar por nombre
    if not artist_mbid or not found_by_mbid:
        if not artist_mbid:
            print(f"  No hay MBID disponible para {artist_name}, buscando por nombre")
        else:
            print(f"  No se encontraron resultados por MBID para {artist_name}, buscando por nombre")
        
        page = 1
        setlists_by_name = 0
        
        while True:
            print(f"  Página {page} (nombre)...")
            response = fetch_setlists_by_name(artist_name, api_key, page, year, from_date)
            
            setlists = response.get('setlist', [])
            if not setlists:
                break
            
            # Filtrar por fecha localmente si es necesario
            if from_date:
                setlists = filter_setlists_by_date(setlists, from_date)
                if setlists:
                    print(f"    Después del filtro de fecha: {len(setlists)} setlists")
            
            # Filtrar setlists que ya existen en la base de datos
            new_setlists = []
            for setlist in setlists:
                setlist_id = setlist.get('id', '')
                cursor.execute("SELECT id FROM artists_setlistfm WHERE setlist_id = ?", (setlist_id,))
                if not cursor.fetchone():
                    new_setlists.append(setlist)
            
            if new_setlists:
                save_setlists(conn, artist_id, artist_name, new_setlists)
                
                setlists_by_name += len(new_setlists)
                total_setlists_found += len(new_setlists)
                print(f"    Guardados {len(new_setlists)} setlists nuevos de {len(setlists)} encontrados")
            else:
                print(f"    No hay setlists nuevos en esta página")
            
            # Si estamos filtrando por fecha y no hay resultados nuevos, podemos parar
            if from_date and not new_setlists and len(setlists) > 0:
                print(f"    No hay setlists más recientes, terminando búsqueda")
                break
            
            # Verificar si hay más páginas
            total = response.get('total', 0)
            items_per_page = response.get('itemsPerPage', 20)
            total_pages = (total + items_per_page - 1) // items_per_page
            
            if page >= total_pages:
                break
            
            page += 1
            # Respetar los límites de la API (máximo 2 llamadas por segundo)
            # Respetar los límites de la API (máximo 2 llamadas por segundo)
            time.sleep(0.5)
        
        if setlists_by_name > 0:
            if search_method:
                search_method += " + nombre"
            else:
                search_method = "nombre"
            
            if year > 0:
                print(f"Guardados {setlists_by_name} setlists nuevos para {artist_name} del año {year} mediante nombre")
            else:
                print(f"Guardados {setlists_by_name} setlists nuevos para {artist_name} mediante nombre")
    
    # Si no se especificó método de búsqueda, usar el apropiado
    if not search_method:
        search_method = "MBID" if artist_mbid else "nombre"
    
    # Actualizar tracking de búsqueda
    update_search_tracking(conn, artist_id, artist_name, total_setlists_found, search_method)
    
    if total_setlists_found == 0:
        print(f"  No se encontraron setlists nuevos para {artist_name}")# Respetar los límites de la API (máximo 2 llamadas por segundo)
        time.sleep(0.5)
        
        if setlists_by_name > 0:
            if search_method:
                search_method += " + nombre"
            else:
                search_method = "nombre"
            
            if year > 0:
                print(f"Guardados {setlists_by_name} setlists nuevos para {artist_name} del año {year} mediante nombre")
            else:
                print(f"Guardados {setlists_by_name} setlists nuevos para {artist_name} mediante nombre")
    
    # Si no se especificó método de búsqueda, usar el apropiado
    if not search_method:
        search_method = "MBID" if artist_mbid else "nombre"
    
    # Actualizar tracking de búsqueda
    update_search_tracking(conn, artist_id, artist_name, total_setlists_found, search_method)
    
    if total_setlists_found == 0:
        print(f"  No se encontraron setlists nuevos para {artist_name}")


    




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



def should_skip_artist(conn, artist_id, force_update=False, year=0, new_only=False):
    """Determina si se debe omitir un artista basado en búsquedas recientes sin resultados"""
    if force_update or year > 0:
        return False
    
    cursor = conn.cursor()
    
    # Si es modo new_only, verificar si el artista necesita actualización
    if new_only:
        cursor.execute('''
        SELECT last_search_date
        FROM artists_setlistfm_searches 
        WHERE artist_id = ? 
        AND datetime(last_search_date) > datetime('now', '-30 days')
        ''', (artist_id,))
        
        result = cursor.fetchone()
        if result:
            print(f"  Omitiendo artista (actualizado recientemente: {result[0]})")
            return True
    
    # Verificar si se buscó recientemente sin encontrar nada
    cursor.execute('''
    SELECT last_search_date, found_setlists 
    FROM artists_setlistfm_searches 
    WHERE artist_id = ? AND found_setlists = 0
    AND datetime(last_search_date) > datetime('now', '-30 days')
    ''', (artist_id,))
    
    result = cursor.fetchone()
    if result:
        last_search, found = result
        print(f"  Omitiendo artista (búsqueda reciente sin resultados: {last_search})")
        return True
    
    return False

def update_search_tracking(conn, artist_id, artist_name, found_setlists, search_method):
    """Actualiza el tracking de búsquedas para un artista"""
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT OR REPLACE INTO artists_setlistfm_searches
        (artist_id, artist_name, last_search_date, found_setlists, search_method)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            artist_id, artist_name, 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            found_setlists, search_method
        ))
        conn.commit()
    except Exception as e:
        print(f"Error al actualizar tracking de búsqueda para {artist_name}: {e}")

def update_setlistfm_ids_before_search(conn, api_key, force_update=False):
    """Actualiza los setlistfm_id ANTES de buscar setlists"""
    print("\n=== Actualizando IDs de setlist.fm ANTES de buscar setlists ===")
    
    # Añadir columna si no existe
    add_setlistfm_id_column(conn)
    
    cursor = conn.cursor()
    
    # Obtener artistas con MBID pero sin setlistfm_id
    if force_update:
        cursor.execute("SELECT id, name, mbid FROM artists WHERE mbid IS NOT NULL")
    else:
        cursor.execute("SELECT id, name, mbid FROM artists WHERE mbid IS NOT NULL AND (setlistfm_id IS NULL OR setlistfm_id = '')")
    
    artists = cursor.fetchall()
    total_artists = len(artists)
    
    if total_artists == 0:
        print("No hay artistas que necesiten actualización de setlistfm_id")
        return
    
    print(f"Actualizando setlistfm_id para {total_artists} artistas...")
    
    updated = 0
    for i, (artist_id, artist_name, mbid) in enumerate(artists, 1):
        print(f"  Obteniendo ID para {artist_name} ({i}/{total_artists})")
        
        setlistfm_id = get_setlistfm_id_by_mbid(mbid, api_key)
        
        if setlistfm_id:
            try:
                cursor.execute("UPDATE artists SET setlistfm_id = ? WHERE id = ?", (setlistfm_id, artist_id))
                conn.commit()
                updated += 1
                print(f"    ✓ ID actualizado: {setlistfm_id}")
            except Exception as e:
                print(f"    ✗ Error al actualizar: {e}")
        else:
            print(f"    - No se encontró ID de setlist.fm")
        
        # Respetar límites de la API
        time.sleep(0.5)
    
    print(f"Actualizaciones de IDs completadas: {updated} de {total_artists} artistas")


def convert_date_format(date_str):
    """Convierte fecha de formato DD-MM-YYYY a DD-MM-YYYY para la API"""
    if not date_str:
        return None
    
    try:
        # Si la fecha está en formato ISO (YYYY-MM-DD), convertir a DD-MM-YYYY
        if '-' in date_str and len(date_str.split('-')[0]) == 4:
            year, month, day = date_str.split('-')
            return f"{day.zfill(2)}-{month.zfill(2)}-{year}"
        # Si la fecha ya está en formato DD-MM-YYYY, verificar y corregir formato
        elif '-' in date_str and len(date_str.split('-')) == 3:
            parts = date_str.split('-')
            # Verificar si es DD-MM-YYYY
            if len(parts[2]) == 4:
                day, month, year = parts
                return f"{day.zfill(2)}-{month.zfill(2)}-{year}"
            # Si es MM-DD-YYYY, convertir
            elif len(parts[0]) == 2 and len(parts[1]) == 2:
                day, month, year = parts
                return f"{day.zfill(2)}-{month.zfill(2)}-{year}"
        
        # Asumir que ya está en formato correcto
        return date_str
    except Exception as e:
        print(f"Error al convertir fecha {date_str}: {e}")
        return None










def get_artists_for_new_mode(conn):
    """Obtiene artistas que necesitan actualización (last_updated > 30 días)"""
    cursor = conn.cursor()
    cursor.execute('''
    SELECT DISTINCT a.id, a.name, a.mbid
    FROM artists a
    LEFT JOIN artists_setlistfm_searches s ON a.id = s.artist_id
    WHERE s.last_search_date IS NULL 
       OR datetime(s.last_search_date) <= datetime('now', '-30 days')
    ORDER BY a.name
    ''')
    return cursor.fetchall()



            
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

def get_setlistfm_id_by_mbid(mbid, api_key, retry_count=0):
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
        if retry_count >= 2:
            print(f"Rate limit alcanzado para MBID {mbid} después de 2 intentos, saltando al siguiente artista...")
            return None
            
        print(f"Rate limit alcanzado para MBID {mbid}, esperando 10 segundos... (intento {retry_count + 1}/2)")
        time.sleep(10)
        return get_setlistfm_id_by_mbid(mbid, api_key, retry_count + 1)
    
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
        
        # Respetar límites de la API (máximo 2 llamadas por segundo)
        time.sleep(0.5)  # Esperar 0.5 segundos para no exceder 2 llamadas por segundo
    
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
    
    # Verificar si solo se deben actualizar los IDs de setlist.fm
    setlistfm_id_only = config.get('setlistfm_id', False)
    
    # NUEVO: Verificar si se deben actualizar IDs antes de buscar
    update_ids = config.get('update_ids', False)
    
    # NUEVO: Modo new_only para actualizar solo artistas antiguos
    new_only = config.get('new', False)
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    
    try:
        if setlistfm_id_only:
            print("Modo: Solo actualización de IDs de setlist.fm")
            # Crear la tabla si no existe (por si acaso)
            create_table(conn)
            # Obtener todos los artistas con sus MBIDs
            artists = get_artists(conn)
            
            if limit > 0:
                artists = artists[:limit]
            
            if artist_names:
                artists = [a for a in artists if a[1] in artist_names]
            
            if artist_ids:
                artists = [a for a in artists if a[0] in artist_ids]
                
            # Actualizar setlistfm_ids
            update_setlistfm_ids(conn, api_key, force_update)
        else:
            # Crear la tabla si no existe
            create_table(conn)
            
            # NUEVO: Actualizar IDs de setlist.fm antes de buscar si se especifica
            if update_ids:
                update_setlistfm_ids_before_search(conn, api_key, force_update)
            
            # Obtener artistas según el modo
            if new_only:
                print("Modo: Solo artistas no actualizados en los últimos 30 días")
                artists = get_artists_for_new_mode(conn)
            else:
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
            
            print(f"Procesando {len(artists)} artistas...")
            
            for artist_id, artist_name, artist_mbid in artists:
                process_artist(conn, artist_id, artist_name, artist_mbid, api_key, force_update, interactive, year, new_only)
            
            # Procesar lugares si se ha especificado
            if process_places_flag:
                process_places(conn, force_update)
    
    finally:
        conn.close()
    
    print("Proceso completado")
    return 0

if __name__ == "__main__":
    # Este bloque solo se ejecutará si el script se llama directamente
    # y no a través de db_creator.py
    print("Este script está diseñado para ser ejecutado a través de db_creator.py")
    sys.exit(1)