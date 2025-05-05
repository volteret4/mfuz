import os
import sys
import json
import time
import sqlite3
import datetime
import requests
from pathlib import Path

def crear_tabla_scrobbles(conn, lastfm_user):
    """
    Crea la tabla para almacenar los scrobbles del usuario si no existe.
    
    Args:
        conn: Conexión a la base de datos SQLite
        lastfm_user: Nombre de usuario de Last.fm para personalizar la tabla
    """
    cursor = conn.cursor()
    
    # Nombre de la tabla personalizada para este usuario
    tabla_scrobbles = f"scrobbles_{lastfm_user}"
    
    # Crear tabla si no existe
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {tabla_scrobbles} (
        id INTEGER PRIMARY KEY,
        artist_name TEXT NOT NULL,
        artist_mbid TEXT,
        name TEXT NOT NULL,
        album_name TEXT,
        album_mbid TEXT,
        timestamp INTEGER NOT NULL,
        fecha_scrobble TIMESTAMP NOT NULL,
        lastfm_url TEXT,
        fecha_adicion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reproducciones INTEGER DEFAULT 1,
        fecha_reproducciones TEXT
    )
    """)
    
    # Crear tabla de configuración si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lastfm_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        lastfm_username TEXT,
        last_timestamp INTEGER,
        last_updated TIMESTAMP
    )
    """)
    
    # Crear índices para búsquedas eficientes
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{tabla_scrobbles}_artist ON {tabla_scrobbles}(artist_name)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{tabla_scrobbles}_name ON {tabla_scrobbles}(name)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{tabla_scrobbles}_album ON {tabla_scrobbles}(album_name)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{tabla_scrobbles}_timestamp ON {tabla_scrobbles}(timestamp)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{tabla_scrobbles}_fecha ON {tabla_scrobbles}(fecha_scrobble)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{tabla_scrobbles}_artist_name ON {tabla_scrobbles}(artist_name, name)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{tabla_scrobbles}_artist_album_name ON {tabla_scrobbles}(artist_name, album_name, name)")
    
    conn.commit()
    print(f"Tabla {tabla_scrobbles} creada o verificada correctamente.")

def obtener_ultimo_timestamp(conn, lastfm_user):
    """
    Obtiene el timestamp del último scrobble procesado.
    
    Args:
        conn: Conexión a la base de datos
        lastfm_user: Nombre de usuario de Last.fm
        
    Returns:
        Timestamp del último scrobble o 0 si no hay registros
    """
    cursor = conn.cursor()
    
    # Intentar obtener de la tabla de configuración
    cursor.execute("""
    SELECT last_timestamp FROM lastfm_config 
    WHERE id = 1 AND lastfm_username = ?
    """, (lastfm_user,))
    
    resultado = cursor.fetchone()
    if resultado:
        ultimo_timestamp = resultado[0]
        fecha = datetime.datetime.fromtimestamp(ultimo_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Último scrobble procesado: {fecha} (timestamp: {ultimo_timestamp})")
        return ultimo_timestamp
    
    # Si no hay entrada en la configuración, crear una con timestamp 0
    cursor.execute("""
    INSERT OR IGNORE INTO lastfm_config (id, lastfm_username, last_timestamp, last_updated)
    VALUES (1, ?, 0, CURRENT_TIMESTAMP)
    """, (lastfm_user,))
    
    conn.commit()
    print("No hay registros previos. Se comenzará desde el inicio.")
    return 0

def guardar_ultimo_timestamp(conn, timestamp, lastfm_user):
    """
    Guarda el timestamp del último scrobble procesado.
    
    Args:
        conn: Conexión a la base de datos
        timestamp: Timestamp a guardar
        lastfm_user: Nombre de usuario de Last.fm
    """
    cursor = conn.cursor()
    
    # Añadir margen de error (restar 1 hora) para asegurar la captura de todos los scrobbles
    # Esto ayuda con posibles diferencias de tiempo entre Last.fm y la aplicación
    timestamp_ajustado = timestamp - 3600  # Restar 1 hora en segundos
    
    cursor.execute("""
    UPDATE lastfm_config 
    SET last_timestamp = ?, lastfm_username = ?, last_updated = CURRENT_TIMESTAMP
    WHERE id = 1
    """, (timestamp_ajustado, lastfm_user))
    
    conn.commit()
    fecha = datetime.datetime.fromtimestamp(timestamp_ajustado).strftime('%Y-%m-%d %H:%M:%S')
    print(f"Timestamp actualizado: {fecha} ({timestamp_ajustado}) - ajustado una hora atrás para evitar pérdidas")



class CacheJSON:
    """
    Clase para manejar la caché de peticiones a Last.fm mediante archivos JSON.
    """
    def __init__(self, cache_dir=None, duracion_cache=7):
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
            self.cache_file = os.path.join(cache_dir, "lastfm_cache.json")
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

def obtener_scrobbles_lastfm(lastfm_username, lastfm_api_key, desde_timestamp=0, limite=200):
    """
    Obtiene todos los scrobbles de Last.fm para un usuario.
    
    Args:
        lastfm_username: Nombre de usuario de Last.fm
        lastfm_api_key: API key de Last.fm
        desde_timestamp: Timestamp desde el que obtener scrobbles
        limite: Número máximo de scrobbles por página
        
    Returns:
        Lista de scrobbles obtenidos
    """
    global cache_lastfm
    
    todos_scrobbles = []
    pagina = 1
    total_paginas = 1
    
    # Mensaje inicial
    if desde_timestamp > 0:
        fecha = datetime.datetime.fromtimestamp(desde_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Obteniendo scrobbles desde {fecha}")
    else:
        print("Obteniendo todos los scrobbles (esto puede tardar bastante)")
    
    while pagina <= total_paginas:
        print(f"Obteniendo página {pagina} de {total_paginas}...")
        
        params = {
            'method': 'user.getrecenttracks',
            'user': lastfm_username,
            'api_key': lastfm_api_key,
            'format': 'json',
            'limit': limite,
            'page': pagina,
            'from': desde_timestamp
        }
        
        # Verificar en caché primero
        datos_cache = None
        if cache_lastfm:
            # Nunca cachear la primera página para siempre obtener los más recientes
            if pagina != 1:
                clave_cache = {
                    'method': 'user.getrecenttracks',
                    'user': lastfm_username,
                    'page': pagina,
                    'from': desde_timestamp,
                    'limit': limite
                }
                datos_cache = cache_lastfm.obtener(clave_cache)
                if datos_cache:
                    print(f"Usando datos en caché para página {pagina}")
        
        if datos_cache:
            datos = datos_cache
        else:
            try:
                respuesta = obtener_con_reintentos('http://ws.audioscrobbler.com/2.0/', params)
                
                if not respuesta or respuesta.status_code != 200:
                    error_msg = f"Error al obtener scrobbles: {respuesta.status_code if respuesta else 'Sin respuesta'}"
                    print(error_msg)
                    
                    if pagina > 1:  # Si hemos obtenido algunas páginas, devolvemos lo que tenemos
                        break
                    else:
                        return []
                
                datos = respuesta.json()
                
                # Guardar en caché todas las páginas excepto la primera
                # para asegurar que siempre obtenemos los scrobbles más recientes
                if cache_lastfm and pagina != 1:
                    clave_cache = {
                        'method': 'user.getrecenttracks',
                        'user': lastfm_username,
                        'page': pagina,
                        'from': desde_timestamp,
                        'limit': limite
                    }
                    cache_lastfm.almacenar(clave_cache, datos)
                    print(f"Guardando en caché página {pagina}")
                
            except Exception as e:
                print(f"Error al procesar página {pagina}: {str(e)}")
                
                if pagina > 1:  # Si hemos obtenido algunas páginas, devolvemos lo que tenemos
                    break
                else:
                    return []
        
        # Comprobar si hay tracks
        if 'recenttracks' not in datos or 'track' not in datos['recenttracks']:
            break
        
        # Actualizar total_paginas
        total_paginas = int(datos['recenttracks']['@attr']['totalPages'])
        
        # Añadir tracks a la lista
        tracks = datos['recenttracks']['track']
        if not isinstance(tracks, list):
            tracks = [tracks]
        
        # Filtrar tracks que están siendo escuchados actualmente (no tienen date)
        filtrados = [track for track in tracks if 'date' in track]
        todos_scrobbles.extend(filtrados)
        
        # Reportar progreso
        print(f"Obtenidos {len(filtrados)} scrobbles en página {pagina}")
        
        pagina += 1
        # Pequeña pausa para no saturar la API
        time.sleep(0.25)
    
    print(f"Obtenidos {len(todos_scrobbles)} scrobbles en total")
    return todos_scrobbles



def procesar_scrobbles(scrobbles):
    """
    Procesa y deduplica scrobbles basándose en la misma canción y artista.
    Los scrobbles se agrupan por artista+canción, manteniendo todas las fechas.
    
    Args:
        scrobbles: Lista de scrobbles obtenidos de Last.fm
        
    Returns:
        Lista de scrobbles procesados y agrupados
    """
    if not scrobbles:
        return []
    
    print("Procesando y agrupando scrobbles...")
    
    # Usar un diccionario para agrupar scrobbles por artista+canción
    scrobbles_agrupados = {}
    
    for scrobble in scrobbles:
        # Extraer información básica
        artist_name = scrobble['artist']['#text']
        artist_mbid = scrobble.get('artist', {}).get('mbid', '')
        track_name = scrobble['name']
        album_name = scrobble['album']['#text'] if 'album' in scrobble and '#text' in scrobble['album'] else ''
        album_mbid = scrobble.get('album', {}).get('mbid', '')
        timestamp = int(scrobble['date']['uts'])
        fecha = scrobble['date']['#text']
        lastfm_url = scrobble.get('url', '')
        
        # Clave única para esta combinación artista+canción
        clave = (artist_name.lower(), track_name.lower())
        
        # Si es la primera vez que vemos esta combinación, crear entrada
        if clave not in scrobbles_agrupados:
            scrobbles_agrupados[clave] = {
                'artist_name': artist_name,
                'artist_mbid': artist_mbid,
                'name': track_name,
                'album_name': album_name,
                'album_mbid': album_mbid,
                'timestamp': timestamp,  # Usamos el timestamp más reciente
                'fecha_scrobble': fecha,
                'lastfm_url': lastfm_url,
                'reproducciones': 1,
                'fecha_reproducciones': [fecha]
            }
        else:
            # Si ya existe, actualizar la entrada
            entrada = scrobbles_agrupados[clave]
            entrada['reproducciones'] += 1
            entrada['fecha_reproducciones'].append(fecha)
            
            # Actualizar timestamp si este es más reciente
            if timestamp > entrada['timestamp']:
                entrada['timestamp'] = timestamp
                entrada['fecha_scrobble'] = fecha
            
            # Completar campos que podrían faltar
            if not entrada['artist_mbid'] and artist_mbid:
                entrada['artist_mbid'] = artist_mbid
            
            if not entrada['album_name'] and album_name:
                entrada['album_name'] = album_name
                
            if not entrada['album_mbid'] and album_mbid:
                entrada['album_mbid'] = album_mbid
                
            if not entrada['lastfm_url'] and lastfm_url:
                entrada['lastfm_url'] = lastfm_url
    
    # Convertir valores de diccionario a lista
    scrobbles_procesados = list(scrobbles_agrupados.values())
    
    # Convertir listas de fechas a cadenas JSON
    for scrobble in scrobbles_procesados:
        scrobble['fecha_reproducciones'] = json.dumps(scrobble['fecha_reproducciones'])
    
    print(f"Procesamiento completado: {len(scrobbles)} scrobbles agrupados en {len(scrobbles_procesados)} entradas únicas")
    return scrobbles_procesados

def guardar_scrobbles_en_db(conn, scrobbles, lastfm_user):
    """
    Guarda los scrobbles en la base de datos, actualizando las entradas existentes.
    
    Args:
        conn: Conexión a la base de datos
        scrobbles: Lista de scrobbles procesados
        lastfm_user: Nombre de usuario de Last.fm
        
    Returns:
        Número de scrobbles guardados (nuevos + actualizados)
    """
    if not scrobbles:
        return 0
    
    cursor = conn.cursor()
    tabla_scrobbles = f"scrobbles_{lastfm_user}"
    nuevos = 0
    actualizados = 0
    
    print(f"Guardando {len(scrobbles)} scrobbles en la base de datos...")
    
    for scrobble in scrobbles:
        # Verificar si ya existe este scrobble (mismo artista y canción)
        cursor.execute(f"""
        SELECT id, reproducciones, fecha_reproducciones 
        FROM {tabla_scrobbles} 
        WHERE LOWER(artist_name) = LOWER(?) AND LOWER(name) = LOWER(?)
        """, (scrobble['artist_name'], scrobble['name']))
        
        resultado = cursor.fetchone()
        
        if resultado:
            # Actualizar scrobble existente
            id_existente, reproducciones_existentes, fechas_existentes = resultado
            
            # Combinar fechas de reproducción
            fechas_actuales = json.loads(fechas_existentes) if fechas_existentes else []
            nuevas_fechas = json.loads(scrobble['fecha_reproducciones'])
            todas_fechas = list(set(fechas_actuales + nuevas_fechas))
            
            # Actualizar con la información más completa
            cursor.execute(f"""
            UPDATE {tabla_scrobbles}
            SET artist_mbid = COALESCE(artist_mbid, ?),
                album_name = COALESCE(album_name, ?),
                album_mbid = COALESCE(album_mbid, ?),
                lastfm_url = COALESCE(lastfm_url, ?),
                reproducciones = ?,
                fecha_reproducciones = ?
            WHERE id = ?
            """, (
                scrobble['artist_mbid'],
                scrobble['album_name'],
                scrobble['album_mbid'],
                scrobble['lastfm_url'],
                len(todas_fechas),
                json.dumps(todas_fechas),
                id_existente
            ))
            
            actualizados += 1
        else:
            # Insertar nuevo scrobble
            cursor.execute(f"""
            INSERT INTO {tabla_scrobbles} (
                artist_name, artist_mbid, name, album_name, album_mbid, 
                timestamp, fecha_scrobble, lastfm_url, reproducciones, fecha_reproducciones
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scrobble['artist_name'],
                scrobble['artist_mbid'],
                scrobble['name'],
                scrobble['album_name'],
                scrobble['album_mbid'],
                scrobble['timestamp'],
                scrobble['fecha_scrobble'],
                scrobble['lastfm_url'],
                scrobble['reproducciones'],
                scrobble['fecha_reproducciones']
            ))
            
            nuevos += 1
    
    conn.commit()
    print(f"Guardados en base de datos: {nuevos} nuevos, {actualizados} actualizados")
    return nuevos + actualizados

def guardar_scrobbles_json(scrobbles, ruta_json, lastfm_user):
    """
    Guarda los scrobbles en un archivo JSON.
    
    Args:
        scrobbles: Lista de scrobbles procesados
        ruta_json: Ruta del archivo JSON a guardar
        lastfm_user: Nombre de usuario de Last.fm
    """
    # Asegurar que el directorio exista
    directorio = os.path.dirname(os.path.abspath(ruta_json))
    os.makedirs(directorio, exist_ok=True)
    
    # Preparar datos para guardar
    datos = {
        'usuario': lastfm_user,
        'fecha_exportacion': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_scrobbles': len(scrobbles),
        'scrobbles': scrobbles
    }
    
    # Guardar en JSON
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    
    print(f"Guardados {len(scrobbles)} scrobbles en {ruta_json}")

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

def obtener_scrobbles_lastfm(lastfm_username, lastfm_api_key, desde_timestamp=0, limite=200):
    """
    Obtiene todos los scrobbles de Last.fm para un usuario.
    
    Args:
        lastfm_username: Nombre de usuario de Last.fm
        lastfm_api_key: API key de Last.fm
        desde_timestamp: Timestamp desde el que obtener scrobbles
        limite: Número máximo de scrobbles por página
        
    Returns:
        Lista de scrobbles obtenidos
    """
    global cache_lastfm
    
    todos_scrobbles = []
    pagina = 1
    total_paginas = 1
    
    # Mensaje inicial
    if desde_timestamp > 0:
        fecha = datetime.datetime.fromtimestamp(desde_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Obteniendo scrobbles desde {fecha}")
    else:
        print("Obteniendo todos los scrobbles (esto puede tardar bastante)")
    
    while pagina <= total_paginas:
        print(f"Obteniendo página {pagina} de {total_paginas}...")
        
        params = {
            'method': 'user.getrecenttracks',
            'user': lastfm_username,
            'api_key': lastfm_api_key,
            'format': 'json',
            'limit': limite,
            'page': pagina,
            'from': desde_timestamp
        }
        
        # Verificar en caché primero
        datos_cache = None
        if cache_lastfm:
            # Nunca cachear la primera página para siempre obtener los más recientes
            if pagina != 1:
                clave_cache = {
                    'method': 'user.getrecenttracks',
                    'user': lastfm_username,
                    'page': pagina,
                    'from': desde_timestamp,
                    'limit': limite
                }
                datos_cache = cache_lastfm.obtener(clave_cache)
                if datos_cache:
                    print(f"Usando datos en caché para página {pagina}")
        
        if datos_cache:
            datos = datos_cache
        else:
            try:
                respuesta = obtener_con_reintentos('http://ws.audioscrobbler.com/2.0/', params)
                
                if not respuesta or respuesta.status_code != 200:
                    error_msg = f"Error al obtener scrobbles: {respuesta.status_code if respuesta else 'Sin respuesta'}"
                    print(error_msg)
                    
                    if pagina > 1:  # Si hemos obtenido algunas páginas, devolvemos lo que tenemos
                        break
                    else:
                        return []
                
                datos = respuesta.json()
                
                # Guardar en caché todas las páginas excepto la primera
                # para asegurar que siempre obtenemos los scrobbles más recientes
                if cache_lastfm and pagina != 1:
                    clave_cache = {
                        'method': 'user.getrecenttracks',
                        'user': lastfm_username,
                        'page': pagina,
                        'from': desde_timestamp,
                        'limit': limite
                    }
                    cache_lastfm.almacenar(clave_cache, datos)
                    print(f"Guardando en caché página {pagina}")
                
            except Exception as e:
                print(f"Error al procesar página {pagina}: {str(e)}")
                
                if pagina > 1:  # Si hemos obtenido algunas páginas, devolvemos lo que tenemos
                    break
                else:
                    return []
        
        # Comprobar si hay tracks
        if 'recenttracks' not in datos or 'track' not in datos['recenttracks']:
            break
        
        # Actualizar total_paginas
        total_paginas = int(datos['recenttracks']['@attr']['totalPages'])
        
        # Añadir tracks a la lista
        tracks = datos['recenttracks']['track']
        if not isinstance(tracks, list):
            tracks = [tracks]
        
        # Filtrar tracks que están siendo escuchados actualmente (no tienen date)
        filtrados = [track for track in tracks if 'date' in track]
        todos_scrobbles.extend(filtrados)
        
        # Reportar progreso
        print(f"Obtenidos {len(filtrados)} scrobbles en página {pagina}")
        
        pagina += 1
        # Pequeña pausa para no saturar la API
        time.sleep(0.25)
    
    print(f"Obtenidos {len(todos_scrobbles)} scrobbles en total")
    return todos_scrobbles


def guardar_ultimo_timestamp(conn, timestamp, lastfm_user):
    """
    Guarda el timestamp del último scrobble procesado.
    
    Args:
        conn: Conexión a la base de datos
        timestamp: Timestamp a guardar
        lastfm_user: Nombre de usuario de Last.fm
    """
    cursor = conn.cursor()
    
    # Añadir margen de error (restar 1 hora) para asegurar la captura de todos los scrobbles
    # Esto ayuda con posibles diferencias de tiempo entre Last.fm y la aplicación
    timestamp_ajustado = timestamp - 3600  # Restar 1 hora en segundos
    
    cursor.execute("""
    UPDATE lastfm_config 
    SET last_timestamp = ?, lastfm_username = ?, last_updated = CURRENT_TIMESTAMP
    WHERE id = 1
    """, (timestamp_ajustado, lastfm_user))
    
    conn.commit()
    fecha = datetime.datetime.fromtimestamp(timestamp_ajustado).strftime('%Y-%m-%d %H:%M:%S')
    print(f"Timestamp actualizado: {fecha} ({timestamp_ajustado}) - ajustado una hora atrás para evitar pérdidas")


def main(config):
    """
    Función principal para obtener y guardar scrobbles de Last.fm.
    
    Args:
        config: Diccionario con configuración
        
    Returns:
        Tuple: (scrobbles_totales, scrobbles_unicos, scrobbles_guardados)
    """
    lastfm_user = config.get('lastfm_user')
    lastfm_api_key = config.get('lastfm_api_key')
    db_path = config.get('db_path')
    output_json = config.get('output_json')
    cache_dir = config.get('cache_dir', '.content/cache/lastfm')
    
    # Validar configuración
    if not all([lastfm_user, lastfm_api_key, db_path]):
        print("Error: Se requieren lastfm_user, lastfm_api_key y db_path en la configuración")
        return 0, 0, 0
    
    # Establecer caché
    setup_cache(cache_dir)
    
    # Verificar API key
    if not verificar_api_key(lastfm_api_key):
        print("ERROR: La API key de Last.fm no es válida o hay problemas con el servicio")
        return 0, 0, 0
    
    print(f"Procesando scrobbles para el usuario: {lastfm_user}")
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    
    # Crear tabla para scrobbles
    crear_tabla_scrobbles(conn, lastfm_user)
    
    # Obtener último timestamp procesado
    ultimo_timestamp = obtener_ultimo_timestamp(conn, lastfm_user)
    
    # Forzar actualización completa si se especifica
    if config.get('force_update', False):
        print("Modo force_update activado: Se ignorará el último timestamp")
        ultimo_timestamp = 0
    
    # Realizar una comprobación inicial para ver si hay nuevos scrobbles
    print("Comprobando si hay nuevos scrobbles...")
    params = {
        'method': 'user.getrecenttracks',
        'user': lastfm_user,
        'api_key': lastfm_api_key,
        'format': 'json',
        'limit': 1,
        'page': 1
    }
    
    try:
        respuesta = obtener_con_reintentos('http://ws.audioscrobbler.com/2.0/', params)
        if respuesta and respuesta.status_code == 200:
            datos = respuesta.json()
            if 'recenttracks' in datos and 'track' in datos['recenttracks']:
                tracks = datos['recenttracks']['track']
                if not isinstance(tracks, list):
                    tracks = [tracks]
                
                # Filtrar tracks que están siendo escuchados actualmente
                tracks = [track for track in tracks if 'date' in track]
                
                if tracks:
                    ultimo_track_timestamp = int(tracks[0]['date']['uts'])
                    if ultimo_track_timestamp > ultimo_timestamp:
                        print(f"Se encontraron nuevos scrobbles desde el último procesado")
                    else:
                        print("No hay nuevos scrobbles desde la última actualización")
                        if not config.get('force_update', False):
                            conn.close()
                            return 0, 0, 0
    except Exception as e:
        print(f"Error al comprobar nuevos scrobbles: {e}")
    
    # Obtener scrobbles de Last.fm
    todos_scrobbles = obtener_scrobbles_lastfm(lastfm_user, lastfm_api_key, ultimo_timestamp)
    
    if not todos_scrobbles:
        print("No se encontraron nuevos scrobbles para procesar")
        conn.close()
        return 0, 0, 0
    
    # Procesar scrobbles para agrupar y deduplicar
    scrobbles_procesados = procesar_scrobbles(todos_scrobbles)
    
    # Guardar en la base de datos
    guardados = guardar_scrobbles_en_db(conn, scrobbles_procesados, lastfm_user)
    
    # Actualizar el último timestamp procesado
    if scrobbles_procesados:
        ultimo_ts = max(scrobble['timestamp'] for scrobble in scrobbles_procesados)
        guardar_ultimo_timestamp(conn, ultimo_ts, lastfm_user)
    
    # Guardar en JSON si se especificó
    if output_json:
        guardar_scrobbles_json(scrobbles_procesados, output_json, lastfm_user)
    
    conn.close()
    
    return len(todos_scrobbles), len(scrobbles_procesados), guardados


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Obtiene y guarda scrobbles de Last.fm')
    parser.add_argument('--lastfm_user', required=True, help='Usuario de Last.fm')
    parser.add_argument('--lastfm_api_key', required=True, help='API key de Last.fm')
    parser.add_argument('--db_path', required=True, help='Ruta al archivo de base de datos SQLite')
    parser.add_argument('--output_json', help='Ruta para guardar scrobbles en formato JSON (opcional)')
    parser.add_argument('--cache_dir', default='.content/cache/lastfm', help='Directorio para archivos de caché')
    parser.add_argument('--force_update', action='store_true', help='Forzar actualización completa')
    
    args = parser.parse_args()
    
    config = vars(args)
    main(config)