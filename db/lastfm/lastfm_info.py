#!/usr/bin/env python3
import os
import sys
import json
import time
import sqlite3
import requests
import argparse
from pathlib import Path

# Reutilizaremos la clase de caché del script anterior
class CacheJSON:
    """
    Clase para manejar la caché de peticiones a Last.fm mediante archivos JSON.
    """
    def __init__(self, cache_dir=None, duracion_cache=30):  # Mayor duración para metadatos
        """
        Inicializa la caché.
        
        Args:
            cache_dir: Directorio para almacenar los archivos de caché
            duracion_cache: Duración en días de la validez de la caché
        """
        self.cache = {}
        self.cache_file = None
        self.duracion_cache = duracion_cache  # en días
        
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            self.cache_file = os.path.join(cache_dir, "lastfm_metadata_cache.json")
            self.cargar_cache()
    
    def cargar_cache(self):
        """Carga la caché desde el archivo si existe."""
        if not self.cache_file or not os.path.exists(self.cache_file):
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                try:
                    self.cache = json.load(f)
                    # Filtrar entradas caducadas
                    ahora = time.time()
                    self.cache = {
                        k: v for k, v in self.cache.items()
                        if 'timestamp' in v and 
                        (ahora - v['timestamp']) / (60 * 60 * 24) <= self.duracion_cache
                    }
                    print(f"Caché cargada con {len(self.cache)} entradas válidas")
                except json.JSONDecodeError:
                    print("Error al decodificar el archivo de caché. Usando caché vacía.")
                    self.cache = {}
        except Exception as e:
            print(f"Error al cargar la caché: {e}")
            self.cache = {}
    
    def guardar_cache(self):
        """Guarda la caché en el archivo."""
        if not self.cache_file:
            return
        
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar la caché: {e}")
    
    def obtener(self, clave):
        """
        Obtiene un valor de la caché si existe y no ha caducado.
        
        Args:
            clave: Clave única para identificar la entrada
            
        Returns:
            Datos almacenados o None si no existe o ha caducado
        """
        clave_str = self._normalizar_clave(clave)
        entrada = self.cache.get(clave_str)
        
        if not entrada:
            return None
            
        # Verificar si ha caducado
        if 'timestamp' in entrada:
            edad_dias = (time.time() - entrada['timestamp']) / (60 * 60 * 24)
            if edad_dias > self.duracion_cache:
                # Eliminar entrada caducada
                del self.cache[clave_str]
                return None
        
        return entrada.get('datos')
    
    def almacenar(self, clave, datos):
        """
        Almacena datos en la caché.
        
        Args:
            clave: Clave única para identificar la entrada
            datos: Datos a almacenar
        """
        if datos is None:
            return
            
        clave_str = self._normalizar_clave(clave)
        
        # Almacenar con timestamp para verificar caducidad
        self.cache[clave_str] = {
            'datos': datos,
            'timestamp': time.time()
        }
        
        # Guardar en archivo
        self.guardar_cache()
    
    def _normalizar_clave(self, clave):
        """
        Convierte una clave en una cadena JSON ordenada.
        
        Args:
            clave: Clave a normalizar (diccionario, lista, etc.)
            
        Returns:
            Cadena JSON que representa la clave
        """
        if isinstance(clave, dict):
            # Filtrar claves irrelevantes como api_key
            filtrado = {k.lower(): v for k, v in clave.items() 
                     if k.lower() not in ('api_key', 'format')}
            return json.dumps(filtrado, sort_keys=True)
        else:
            return str(clave)

# Instancia global de caché
cache_lastfm = None

def setup_cache(cache_dir=None):
    """
    Configura la caché global.
    
    Args:
        cache_dir: Directorio para los archivos de caché
    """
    global cache_lastfm
    cache_lastfm = CacheJSON(cache_dir)
    return cache_lastfm

def obtener_con_reintentos(url, params, max_reintentos=3, tiempo_espera=1, timeout=10):
    """
    Realiza una petición HTTP con reintentos en caso de error.
    
    Args:
        url: URL a consultar
        params: Parámetros para la petición
        max_reintentos: Número máximo de reintentos
        tiempo_espera: Tiempo base de espera entre reintentos
        timeout: Tiempo máximo de espera para la petición
        
    Returns:
        Respuesta HTTP o None si fallan todos los intentos
    """
    for intento in range(max_reintentos):
        try:
            respuesta = requests.get(url, params=params, timeout=timeout)
            
            # Si hay límite de tasa, esperar y reintentar
            if respuesta.status_code == 429:  # Rate limit
                tiempo_espera_recomendado = int(respuesta.headers.get('Retry-After', tiempo_espera * 2))
                print(f"Límite de tasa alcanzado. Esperando {tiempo_espera_recomendado} segundos...")
                time.sleep(tiempo_espera_recomendado)
                continue
            
            return respuesta
            
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            print(f"Error en intento {intento+1}/{max_reintentos}: {e}")
            if intento < max_reintentos - 1:
                # Backoff exponencial
                tiempo_espera_actual = tiempo_espera * (2 ** intento)
                print(f"Reintentando en {tiempo_espera_actual} segundos...")
                time.sleep(tiempo_espera_actual)
    
    return None

def crear_tablas_enlaces(conn):
    """
    Crea las tablas necesarias para almacenar los enlaces a Last.fm si no existen.
    
    Args:
        conn: Conexión a la base de datos SQLite
    """
    cursor = conn.cursor()
    
    # Tabla de redes sociales para artistas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS artists_networks (
        id INTEGER PRIMARY KEY,
        artist_id INTEGER UNIQUE,
        artist_name TEXT,
        allmusic TEXT,
        bandcamp TEXT,
        boomkat TEXT,
        facebook TEXT,
        twitter TEXT,
        mastodon TEXT,
        bluesky TEXT,
        instagram TEXT,
        spotify TEXT,
        lastfm TEXT,
        wikipedia TEXT,
        juno TEXT,
        soundcloud TEXT,
        youtube TEXT,
        imdb TEXT,
        progarchives TEXT,
        setlist_fm TEXT,
        who_sampled TEXT,
        vimeo TEXT,
        genius TEXT,
        myspace TEXT,
        tumblr TEXT,
        resident_advisor TEXT,
        rateyourmusic TEXT,
        enlaces TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (artist_id) REFERENCES artists(id)
    )
    """)
    
    # Tabla de enlaces para álbumes - CORREGIDO
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='album_links'")
        if not cursor.fetchone():
            print("Creando tabla album_links...")
            cursor.execute("""
            CREATE TABLE album_links (
                id INTEGER PRIMARY KEY,
                album_id INTEGER UNIQUE,
                album_name TEXT,
                artist_name TEXT,
                lastfm_url TEXT,
                spotify_url TEXT,
                spotify_id TEXT,
                youtube_url TEXT,
                musicbrainz_url TEXT,
                discogs_url TEXT,
                bandcamp_url TEXT,
                apple_music_url TEXT,
                rateyourmusic_url TEXT,
                links_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (album_id) REFERENCES albums(id)
            )
            """)
            print("Tabla album_links creada correctamente")
    except sqlite3.Error as e:
        print(f"Error al crear tabla album_links: {e}")
    
    # Asegurar que song_links existe y tiene la columna lastfm_url
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_links'")
        if not cursor.fetchone():
            # Si no existe, crear la tabla song_links
            print("Creando tabla song_links...")
            cursor.execute("""
            CREATE TABLE song_links (
                id INTEGER PRIMARY KEY,
                song_id INTEGER UNIQUE,
                lastfm_url TEXT,
                spotify_url TEXT,
                spotify_id TEXT,
                youtube_url TEXT,
                musicbrainz_url TEXT,
                musicbrainz_recording_id TEXT,
                bandcamp_url TEXT,
                soundcloud_url TEXT,
                links_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (song_id) REFERENCES songs(id)
            )
            """)
            print("Tabla song_links creada correctamente")
        else:
            # Verificar si lastfm_url existe en song_links
            cursor.execute("PRAGMA table_info(song_links)")
            columnas = [columna[1] for columna in cursor.fetchall()]
            
            if 'lastfm_url' not in columnas:
                print("Añadiendo columna lastfm_url a song_links...")
                cursor.execute("ALTER TABLE song_links ADD COLUMN lastfm_url TEXT")
                print("Columna lastfm_url añadida a song_links")
                
            if 'links_updated' not in columnas:
                print("Añadiendo columna links_updated a song_links...")
                cursor.execute("ALTER TABLE song_links ADD COLUMN links_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print("Columna links_updated añadida a song_links")
    except sqlite3.Error as e:
        print(f"Error al gestionar tabla song_links: {e}")
    
    # Crear índices para búsquedas eficientes
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_artists_networks_artist_id ON artists_networks(artist_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_album_links_album_id ON album_links(album_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_artists_networks_lastfm ON artists_networks(lastfm)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_album_links_lastfm ON album_links(lastfm_url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_song_links_lastfm ON song_links(lastfm_url)")
        print("Índices creados o verificados correctamente")
    except sqlite3.Error as e:
        print(f"Error al crear índices: {e}")
    
    conn.commit()
    print("Configuración de tablas e índices completada")

def obtener_info_artista(artist_name, mbid, lastfm_api_key):
    """
    Obtiene información detallada de un artista desde Last.fm.
    
    Args:
        artist_name: Nombre del artista
        mbid: ID de MusicBrainz (opcional)
        lastfm_api_key: API key de Last.fm
        
    Returns:
        Diccionario con la información del artista o None si no se encuentra
    """
    global cache_lastfm
    
    # Validación de parámetros
    if not artist_name or not isinstance(artist_name, str):
        print(f"Error: Nombre de artista inválido: {repr(artist_name)}")
        return None
    
    if not lastfm_api_key or not isinstance(lastfm_api_key, str):
        print(f"Error: API key de Last.fm inválida")
        return None
    
    # Normalizar el nombre del artista
    artist_name = artist_name.strip()
    
    # Crear clave de caché
    cache_key = {
        'method': 'artist.getInfo',
        'artist': artist_name,
    }
    if mbid:
        cache_key['mbid'] = mbid
    
    # Verificar en caché primero
    if cache_lastfm:
        cached_result = cache_lastfm.obtener(cache_key)
        if cached_result:
            print(f"Usando datos en caché para artista Last.fm: {artist_name}")
            return cached_result.get('artist')
    
    # Construir parámetros de consulta
    params = {
        'method': 'artist.getInfo',
        'artist': artist_name,
        'api_key': lastfm_api_key,
        'format': 'json',
        'autocorrect': 1  # Activar corrección automática
    }
    
    if mbid:
        params['mbid'] = mbid
    
    print(f"Consultando Last.fm para artista: {artist_name}")
    
    try:
        response = obtener_con_reintentos('http://ws.audioscrobbler.com/2.0/', params)
        
        if not response or response.status_code != 200:
            print(f"Error al obtener información para {artist_name}: {response.status_code if response else 'Sin respuesta'}")
            return None
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"Error al parsear respuesta JSON para {artist_name}")
            return None
        
        # Verificar si hay error en la respuesta
        if 'error' in data:
            print(f"Error de Last.fm para {artist_name}: {data.get('message', 'Error desconocido')}")
            return None
        
        # Verificar si hay información de artista
        if 'artist' not in data:
            print(f"No se encontró información para el artista {artist_name}")
            return None
        
        # Guardar en caché y devolver resultado
        if cache_lastfm:
            cache_lastfm.almacenar(cache_key, data)
        
        return data['artist']
        
    except Exception as e:
        print(f"Error al consultar información para {artist_name}: {e}")
        return None

def obtener_info_album(album_name, artist_name, mbid, lastfm_api_key):
    """
    Obtiene información detallada de un álbum desde Last.fm.
    
    Args:
        album_name: Nombre del álbum
        artist_name: Nombre del artista
        mbid: ID de MusicBrainz (opcional)
        lastfm_api_key: API key de Last.fm
        
    Returns:
        Diccionario con la información del álbum o None si no se encuentra
    """
    global cache_lastfm
    
    # Validación de parámetros
    if not album_name or not artist_name:
        print(f"Error: Se requiere nombre de álbum y artista")
        return None
    
    # Normalizar nombres
    album_name = album_name.strip()
    artist_name = artist_name.strip()
    
    # Crear clave de caché
    cache_key = {
        'method': 'album.getInfo',
        'album': album_name,
        'artist': artist_name
    }
    if mbid:
        cache_key['mbid'] = mbid
    
    # Verificar en caché primero
    if cache_lastfm:
        cached_result = cache_lastfm.obtener(cache_key)
        if cached_result:
            print(f"Usando datos en caché para álbum Last.fm: {album_name}")
            return cached_result.get('album')
    
    # Construir parámetros de consulta
    params = {
        'method': 'album.getInfo',
        'album': album_name,
        'artist': artist_name,
        'api_key': lastfm_api_key,
        'format': 'json',
        'autocorrect': 1
    }
    
    if mbid:
        params['mbid'] = mbid
    
    print(f"Consultando Last.fm para álbum: {album_name} de {artist_name}")
    
    try:
        response = obtener_con_reintentos('http://ws.audioscrobbler.com/2.0/', params)
        
        if not response or response.status_code != 200:
            print(f"Error al obtener información para álbum {album_name}: {response.status_code if response else 'Sin respuesta'}")
            return None
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"Error al parsear respuesta JSON para álbum {album_name}")
            return None
        
        # Verificar si hay error en la respuesta
        if 'error' in data:
            print(f"Error de Last.fm para álbum {album_name}: {data.get('message', 'Error desconocido')}")
            return None
        
        # Verificar si hay información de álbum
        if 'album' not in data:
            print(f"No se encontró información para el álbum {album_name}")
            return None
        
        # Guardar en caché y devolver resultado
        if cache_lastfm:
            cache_lastfm.almacenar(cache_key, data)
        
        return data['album']
        
    except Exception as e:
        print(f"Error al consultar información para álbum {album_name}: {e}")
        return None

def obtener_info_cancion(track_name, artist_name, mbid, lastfm_api_key):
    """
    Obtiene información detallada de una canción desde Last.fm.
    
    Args:
        track_name: Nombre de la canción
        artist_name: Nombre del artista
        mbid: ID de MusicBrainz (opcional)
        lastfm_api_key: API key de Last.fm
        
    Returns:
        Diccionario con la información de la canción o None si no se encuentra
    """
    global cache_lastfm
    
    # Validación de parámetros
    if not track_name or not artist_name:
        print(f"Error: Se requiere nombre de canción y artista")
        return None
    
    # Normalizar nombres
    track_name = track_name.strip()
    artist_name = artist_name.strip()
    
    # Crear clave de caché
    cache_key = {
        'method': 'track.getInfo',
        'track': track_name,
        'artist': artist_name
    }
    if mbid:
        cache_key['mbid'] = mbid
    
    # Verificar en caché primero
    if cache_lastfm:
        cached_result = cache_lastfm.obtener(cache_key)
        if cached_result:
            print(f"Usando datos en caché para canción Last.fm: {track_name}")
            return cached_result.get('track')
    
    # Construir parámetros de consulta
    params = {
        'method': 'track.getInfo',
        'track': track_name,
        'artist': artist_name,
        'api_key': lastfm_api_key,
        'format': 'json',
        'autocorrect': 1
    }
    
    if mbid:
        params['mbid'] = mbid
    
    print(f"Consultando Last.fm para canción: {track_name} de {artist_name}")
    
    try:
        response = obtener_con_reintentos('http://ws.audioscrobbler.com/2.0/', params)
        
        if not response or response.status_code != 200:
            print(f"Error al obtener información para canción {track_name}: {response.status_code if response else 'Sin respuesta'}")
            return None
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"Error al parsear respuesta JSON para canción {track_name}")
            return None
        
        # Verificar si hay error en la respuesta
        if 'error' in data:
            print(f"Error de Last.fm para canción {track_name}: {data.get('message', 'Error desconocido')}")
            return None
        
        # Verificar si hay información de canción
        if 'track' not in data:
            print(f"No se encontró información para la canción {track_name}")
            return None
        
        # Guardar en caché y devolver resultado
        if cache_lastfm:
            cache_lastfm.almacenar(cache_key, data)
        
        return data['track']
        
    except Exception as e:
        print(f"Error al consultar información para canción {track_name}: {e}")
        return None

def actualizar_info_artistas(conn, lastfm_api_key, limite=50):
    """
    Actualiza la información SOLO para los artistas que les faltan datos en Last.fm.
    
    Args:
        conn: Conexión a la base de datos
        lastfm_api_key: API key de Last.fm
        limite: Número máximo de artistas a actualizar por ejecución
        
    Returns:
        Número de artistas actualizados
    """
    cursor = conn.cursor()
    
    # Verificar estructura de la tabla artists
    cursor.execute("PRAGMA table_info(artists)")
    columnas_artists = {columna[1]: columna[0] for columna in cursor.fetchall()}
    
    # Verificar si existen las columnas necesarias
    columnas_requeridas = ["bio", "tags", "similar_artists", "lastfm_url"]
    columnas_faltantes = [col for col in columnas_requeridas if col not in columnas_artists]
    
    if columnas_faltantes:
        for columna in columnas_faltantes:
            try:
                cursor.execute(f"ALTER TABLE artists ADD COLUMN {columna} TEXT")
                print(f"Añadida columna {columna} a la tabla artists")
            except sqlite3.Error as e:
                print(f"Error al añadir columna {columna}: {e}")
    
    # Obtener SOLO artistas que les falte información
    query = """
    SELECT id, name, mbid 
    FROM artists 
    WHERE bio IS NULL OR bio = '' OR tags IS NULL OR tags = '' OR 
          similar_artists IS NULL OR similar_artists = '' OR 
          lastfm_url IS NULL OR lastfm_url = ''
    LIMIT ?
    """
    
    cursor.execute(query, (limite,))
    artistas_a_actualizar = cursor.fetchall()
    
    if not artistas_a_actualizar:
        print("No hay artistas que necesiten actualización de Last.fm")
        return 0
    
    print(f"Actualizando información para {len(artistas_a_actualizar)} artistas que les falta datos")
    
    actualizados = 0
    
    for artista_id, artista_nombre, mbid in artistas_a_actualizar:
        # Verificar qué campos faltan específicamente para este artista
        cursor.execute("""
        SELECT bio, tags, similar_artists, lastfm_url
        FROM artists
        WHERE id = ?
        """, (artista_id,))
        
        datos_actuales = cursor.fetchone()
        if not datos_actuales:
            print(f"Error: No se pudo obtener información actual para el artista ID {artista_id}")
            continue
            
        bio_actual, tags_actuales, similar_actuales, lastfm_url_actual = datos_actuales
        
        # Solo actualizar si falta algún campo
        campos_faltantes = []
        if not bio_actual:
            campos_faltantes.append("bio")
        if not tags_actuales:
            campos_faltantes.append("tags")
        if not similar_actuales:
            campos_faltantes.append("similar_artists")
        if not lastfm_url_actual:
            campos_faltantes.append("lastfm_url")
            
        if not campos_faltantes:
            # Si no falta ningún campo, saltamos este artista
            continue
            
        print(f"Actualizando {artista_nombre} (ID: {artista_id}) - Campos faltantes: {', '.join(campos_faltantes)}")
        
        # Obtener información de Last.fm
        info_artista = obtener_info_artista(artista_nombre, mbid, lastfm_api_key)
        
        if not info_artista:
            print(f"No se pudo obtener información para {artista_nombre}")
            continue
        
        # Preparar actualizaciones - SOLO para campos faltantes
        updates = []
        params = []
        
        # Bio
        if 'bio' in campos_faltantes and 'bio' in info_artista and 'content' in info_artista['bio']:
            bio = info_artista['bio']['content'].strip()
            if bio:
                updates.append("bio = ?")
                params.append(bio)
        
        # Tags
        if 'tags' in campos_faltantes and 'tags' in info_artista and 'tag' in info_artista['tags']:
            tag_list = info_artista['tags']['tag']
            tags = []
            if isinstance(tag_list, list):
                tags = [tag['name'] for tag in tag_list]
            else:
                tags = [tag_list['name']]
            
            tags_str = ','.join(tags)
            if tags_str:
                updates.append("tags = ?")
                params.append(tags_str)
        
        # Similar artists
        if 'similar_artists' in campos_faltantes and 'similar' in info_artista and 'artist' in info_artista['similar']:
            similar_list = info_artista['similar']['artist']
            similar_artists = []
            if isinstance(similar_list, list):
                similar_artists = [{'name': a['name'], 'url': a.get('url', '')} for a in similar_list]
            else:
                similar_artists = [{'name': similar_list['name'], 'url': similar_list.get('url', '')}]
            
            similar_json = json.dumps(similar_artists)
            updates.append("similar_artists = ?")
            params.append(similar_json)
        
        # URL de Last.fm
        if 'lastfm_url' in campos_faltantes and 'url' in info_artista:
            updates.append("lastfm_url = ?")
            params.append(info_artista['url'])
        
        # Actualizar MBID si no lo teníamos
        if not mbid and 'mbid' in info_artista and info_artista['mbid']:
            updates.append("mbid = ?")
            params.append(info_artista['mbid'])
        
        # Ejecutar actualización si hay cambios
        if updates:
            query = f"UPDATE artists SET {', '.join(updates)} WHERE id = ?"
            params.append(artista_id)
            
            try:
                cursor.execute(query, params)
                actualizados += 1
            except sqlite3.Error as e:
                print(f"Error al actualizar artista {artista_nombre}: {e}")
        
        # Actualizar también la tabla artists_networks SOLO si falta
        if 'url' in info_artista:
            try:
                # Verificar si ya existe entrada con lastfm
                cursor.execute("""
                SELECT id FROM artists_networks 
                WHERE artist_id = ? AND (lastfm IS NULL OR lastfm = '')
                """, (artista_id,))
                
                red_sin_lastfm = cursor.fetchone()
                
                if red_sin_lastfm:
                    # Actualizar si existe pero le falta lastfm
                    cursor.execute("""
                    UPDATE artists_networks 
                    SET lastfm = ?, artist_name = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE artist_id = ?
                    """, (info_artista['url'], artista_nombre, artista_id))
                    print(f"Actualizada red social Last.fm para {artista_nombre}")
                else:
                    # Verificar si existe entrada
                    cursor.execute("SELECT id FROM artists_networks WHERE artist_id = ?", (artista_id,))
                    red_existente = cursor.fetchone()
                    
                    if not red_existente:
                        # Insertar solo si no existe
                        cursor.execute("""
                        INSERT INTO artists_networks (artist_id, artist_name, lastfm, last_updated)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        """, (artista_id, artista_nombre, info_artista['url']))
                        print(f"Creada entrada de red social Last.fm para {artista_nombre}")
            except sqlite3.Error as e:
                print(f"Error al actualizar red social para {artista_nombre}: {e}")
    
    conn.commit()
    print(f"Actualizados {actualizados} artistas con información de Last.fm")
    return actualizados

def actualizar_enlaces_albumes(conn, lastfm_api_key, limite=50):
    """
    Actualiza los enlaces a Last.fm SOLO para los álbumes que no tienen enlace.
    
    Args:
        conn: Conexión a la base de datos
        lastfm_api_key: API key de Last.fm
        limite: Número máximo de álbumes a actualizar por ejecución
        
    Returns:
        Número de álbumes actualizados
    """
    cursor = conn.cursor()
    
    # Verificar que la tabla existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='album_links'")
    if not cursor.fetchone():
        print("Tabla album_links no encontrada. Creándola...")
        crear_tablas_enlaces(conn)
    
    # Obtener SOLO álbumes sin enlaces a Last.fm
    query = """
    SELECT a.id, a.name, ar.name 
    FROM albums a
    JOIN artists ar ON a.artist_id = ar.id
    LEFT JOIN album_links al ON a.id = al.album_id
    WHERE al.id IS NULL OR al.lastfm_url IS NULL OR al.lastfm_url = ''
    LIMIT ?
    """
    
    try:
        cursor.execute(query, (limite,))
        albumes_a_actualizar = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error al consultar álbumes a actualizar: {e}")
        return 0
    
    if not albumes_a_actualizar:
        print("No hay álbumes que necesiten enlaces a Last.fm")
        return 0
    
    print(f"Actualizando enlaces para {len(albumes_a_actualizar)} álbumes que les falta el enlace")
    
    actualizados = 0
    
    for album_id, album_nombre, artista_nombre in albumes_a_actualizar:
        print(f"Actualizando enlace para {album_nombre} de {artista_nombre} (ID: {album_id})")
        
        # Obtener información de Last.fm
        info_album = obtener_info_album(album_nombre, artista_nombre, None, lastfm_api_key)
        
        if not info_album:
            print(f"No se pudo obtener información para {album_nombre}")
            continue
        
        # Procesar la URL de Last.fm
        lastfm_url = info_album.get('url', '')
        
        if not lastfm_url:
            print(f"No se encontró URL de Last.fm para {album_nombre}")
            continue
        
        try:
            # Verificar si ya existe entrada
            cursor.execute("SELECT id, lastfm_url FROM album_links WHERE album_id = ?", (album_id,))
            enlace_existente = cursor.fetchone()
            
            if enlace_existente:
                # Solo actualizar si el enlace está vacío
                if not enlace_existente[1]:
                    cursor.execute("""
                    UPDATE album_links 
                    SET lastfm_url = ?, album_name = ?, artist_name = ?, links_updated = CURRENT_TIMESTAMP
                    WHERE album_id = ?
                    """, (lastfm_url, album_nombre, artista_nombre, album_id))
                    actualizados += 1
                    print(f"Actualizado enlace Last.fm para {album_nombre}")
            else:
                # Insertar si no existe
                cursor.execute("""
                INSERT INTO album_links (album_id, album_name, artist_name, lastfm_url, links_updated)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (album_id, album_nombre, artista_nombre, lastfm_url))
                actualizados += 1
                print(f"Creado enlace Last.fm para {album_nombre}")
            
        except sqlite3.Error as e:
            print(f"Error al actualizar enlace para {album_nombre}: {e}")
    
    conn.commit()
    print(f"Actualizados enlaces Last.fm para {actualizados} álbumes")
    return actualizados

def actualizar_enlaces_canciones(conn, lastfm_api_key, limite=50):
    """
    Actualiza los enlaces a Last.fm SOLO para las canciones que no tienen enlace.
    
    Args:
        conn: Conexión a la base de datos
        lastfm_api_key: API key de Last.fm
        limite: Número máximo de canciones a actualizar por ejecución
        
    Returns:
        Número de canciones actualizadas
    """
    cursor = conn.cursor()
    
    # Verificar que la tabla existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_links'")
    if not cursor.fetchone():
        print("Tabla song_links no encontrada. Creándola...")
        crear_tablas_enlaces(conn)
    
    # Obtener SOLO canciones sin enlaces a Last.fm
    query = """
    SELECT s.id, s.title, s.artist
    FROM songs s
    LEFT JOIN song_links sl ON s.id = sl.song_id
    WHERE sl.id IS NULL OR sl.lastfm_url IS NULL OR sl.lastfm_url = ''
    LIMIT ?
    """
    
    cursor.execute(query, (limite,))
    canciones_a_actualizar = cursor.fetchall()
    
    if not canciones_a_actualizar:
        print("No hay canciones que necesiten enlaces a Last.fm")
        return 0
    
    print(f"Actualizando enlaces para {len(canciones_a_actualizar)} canciones que les falta el enlace")
    
    actualizados = 0
    
    for cancion_id, cancion_titulo, artista_nombre in canciones_a_actualizar:
        print(f"Actualizando enlace para {cancion_titulo} de {artista_nombre} (ID: {cancion_id})")
        
        # Obtener información de Last.fm
        info_cancion = obtener_info_cancion(cancion_titulo, artista_nombre, None, lastfm_api_key)
        
        if not info_cancion:
            print(f"No se pudo obtener información para {cancion_titulo}")
            continue
        
        # Procesar la URL de Last.fm
        lastfm_url = info_cancion.get('url', '')
        
        if not lastfm_url:
            print(f"No se encontró URL de Last.fm para {cancion_titulo}")
            continue
        
        try:
            # Verificar si ya existe entrada
            cursor.execute("SELECT id, lastfm_url FROM song_links WHERE song_id = ?", (cancion_id,))
            enlace_existente = cursor.fetchone()
            
            if enlace_existente:
                # Solo actualizar si el enlace está vacío
                if not enlace_existente[1]:
                    cursor.execute("""
                    UPDATE song_links 
                    SET lastfm_url = ?, links_updated = CURRENT_TIMESTAMP
                    WHERE song_id = ?
                    """, (lastfm_url, cancion_id))
                    actualizados += 1
                    print(f"Actualizado enlace Last.fm para {cancion_titulo}")
            else:
                # Insertar si no existe
                cursor.execute("""
                INSERT INTO song_links (song_id, lastfm_url, links_updated)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (cancion_id, lastfm_url))
                actualizados += 1
                print(f"Creado enlace Last.fm para {cancion_titulo}")
            
        except sqlite3.Error as e:
            print(f"Error al actualizar enlace para {cancion_titulo}: {e}")
    
    conn.commit()
    print(f"Actualizados enlaces Last.fm para {actualizados} canciones")
    return actualizados

def main(config):
    """
    Función principal para actualizar información y enlaces de Last.fm.
    
    Args:
        config: Diccionario con configuración
        
    Returns:
        Dict: Resultados de las actualizaciones
    """
    lastfm_api_key = config.get('lastfm_api_key')
    db_path = config.get('db_path')
    cache_dir = config.get('cache_dir', '.content/cache/lastfm')
    limite_artistas = config.get('limite_artistas', 50)
    limite_albumes = config.get('limite_albumes', 50)
    limite_canciones = config.get('limite_canciones', 50)
    
    # Validar configuración
    if not all([lastfm_api_key, db_path]):
        print("Error: Se requieren lastfm_api_key y db_path en la configuración")
        return {'error': 'Configuración incompleta'}
    
    # Establecer caché
    setup_cache(cache_dir)
    
    print("Iniciando actualización de información y enlaces de Last.fm")
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    
    # Crear tablas si no existen
    crear_tablas_enlaces(conn)
    
    resultados = {}
    
    # Actualizar información de artistas
    print("\n=== Actualizando información de artistas ===")
    artistas_actualizados = actualizar_info_artistas(conn, lastfm_api_key, limite_artistas)
    resultados['artistas_actualizados'] = artistas_actualizados
    
    # Actualizar enlaces a álbumes
    print("\n=== Actualizando enlaces de álbumes ===")
    albumes_actualizados = actualizar_enlaces_albumes(conn, lastfm_api_key, limite_albumes)
    resultados['albumes_actualizados'] = albumes_actualizados
    
    # Actualizar enlaces a canciones
    print("\n=== Actualizando enlaces de canciones ===")
    canciones_actualizadas = actualizar_enlaces_canciones(conn, lastfm_api_key, limite_canciones)
    resultados['canciones_actualizadas'] = canciones_actualizadas
    
    # Cerrar conexión
    conn.close()
    
    print("\n=== Resumen de actualizaciones ===")
    print(f"Artistas actualizados: {artistas_actualizados}")
    print(f"Álbumes actualizados: {albumes_actualizados}")
    print(f"Canciones actualizadas: {canciones_actualizadas}")
    
    return resultados

def verificar_api_key(lastfm_api_key):
    """
    Verifica si la API key de Last.fm es válida.
    
    Args:
        lastfm_api_key: API key a verificar
        
    Returns:
        True si parece válida, False si hay error
    """
    print("Verificando API key de Last.fm...")
    params = {
        'method': 'auth.getSession',
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    try:
        respuesta = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        # Una API key incorrecta debería devolver un error 403 o un mensaje de error en JSON
        if respuesta.status_code == 403:
            print("API key inválida: Error 403 Forbidden")
            return False
        
        datos = respuesta.json()
        if 'error' in datos and datos['error'] == 10:
            print("API key inválida: Error de autenticación")
            return False
        
        # Si llegamos aquí, la key parece válida aunque el método específico requiera más parámetros
        print("API key parece válida")
        return True
        
    except Exception as e:
        print(f"Error al verificar API key: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Actualiza información y enlaces de Last.fm')
    parser.add_argument('--lastfm_api_key', required=True, help='API key de Last.fm')
    parser.add_argument('--db_path', required=True, help='Ruta al archivo de base de datos SQLite')
    parser.add_argument('--cache_dir', default='.content/cache/lastfm', help='Directorio para archivos de caché')
    parser.add_argument('--limite_artistas', type=int, default=999999, help='Número máximo de artistas a actualizar')
    parser.add_argument('--limite_albumes', type=int, default=999999, help='Número máximo de álbumes a actualizar')
    parser.add_argument('--limite_canciones', type=int, default=999999, help='Número máximo de canciones a actualizar')
    
    args = parser.parse_args()
    
    if not verificar_api_key(args.lastfm_api_key):
        print("ERROR: La API key de Last.fm no es válida o hay problemas con el servicio")
        sys.exit(1)
    
    config = vars(args)
    main(config)