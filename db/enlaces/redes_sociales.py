#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import sqlite3
import time
import json
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Importar módulos base
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tools.discogs_login import DiscogsClient
from base_module import PROJECT_ROOT
print(PROJECT_ROOT)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class RedesSocialesArtistas:
    """
    Módulo para obtener y almacenar las redes sociales de los artistas desde Discogs.
    """
    
    def __init__(self, config=None):
        """
        Inicializa el módulo de redes sociales de artistas.
        
        Args:
            config (dict, optional): Configuración del módulo.
        """
        self.logger = logging.getLogger("redes_sociales_artistas")
        self.config = config or {}
        
        # Configuración por defecto
        self.default_config = {
            'rate_limit': 1.0,
            'max_retries': 3,
            'batch_size': 50,
            'force_update': False,
            'missing_only': True,
            'concurrent_workers': 1,
            'user_agent': 'MusicDatabaseApp/1.0'
        }
        
        # Combinar con la configuración proporcionada
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
        
        # Mostrar configuración
        self.logger.info(f"Configuración: {self.config}")
        
        # Inicializar cliente de Discogs
        self.discogs_token = self.config.get('discogs_token')
        if not self.discogs_token:
            self.logger.warning("No se ha proporcionado un token de Discogs. Algunas funcionalidades pueden estar limitadas.")
        
        self.discogs_client = DiscogsClient(
            token=self.discogs_token,
            rate_limit=self.config.get('rate_limit', 1.0),
            user_agent=self.config.get('user_agent', 'MusicDatabaseApp/1.0')
        )
        
        # Conectar a la base de datos
        self.db_path = self.config.get('db_path')
        if not self.db_path:
            self.logger.error("No se ha proporcionado la ruta de la base de datos")
        
        self.conn = None
        self.cursor = None
        
        # Lista de redes sociales conocidas
        self.known_networks = {
            'AllMusic.com': 'allmusic',
            'allmusic.com': 'allmusic',
            'bandcamp.com': 'bandcamp',
            'boomkat.com': 'boomkat',
            'facebook.com': 'facebook',
            'twitter.com': 'twitter',
            'x.com': 'twitter',
            'mastodon.social': 'mastodon',
            'masto.ai': 'mastodon',
            'mastodon.': 'mastodon',
            'bsky.app': 'bluesky',
            'bluesky.social': 'bluesky',
            'instagram.com': 'instagram',
            'spotify.com': 'spotify',
            'open.spotify.com': 'spotify',
            'last.fm': 'lastfm',
            'www.last.fm': 'lastfm',
            'wikipedia.org': 'wikipedia',
            'juno.co.uk': 'juno',
            'soundcloud.com': 'soundcloud',
            'youtube.com': 'youtube',
            'youtu.be': 'youtube',
            'imdb.com': 'imdb',
            'ProgArchives.com': 'progarchives',
            'progarchives.com': 'progarchives',
            'setlist.fm': 'setlist.fm',
            'whosampled.com': 'who_sampled',
            'vimeo.com': 'vimeo',
            'genius.com': 'genius',
            'myspace.com': 'myspace',
            'tumblr.com': 'tumblr',
            'ra.co': 'resident_advisor',
            'rateyourmusic.com': 'rateyourmusic',
            'RateYourMusic.com': 'rateyourmusic',
            'residentadvisor.net': 'resident_advisor',
            'discogs.com': 'discogs'
        }

    
    def connect_db(self):
        """
        Establece la conexión a la base de datos.
        """
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error al conectar a la base de datos: {str(e)}")
            return False
    
    def close_db(self):
        """
        Cierra la conexión a la base de datos.
        """
        if self.conn:
            self.conn.close()
    
    def setup_database(self):
        """
        Configura la base de datos, creando la tabla si no existe.
        """
        if not self.connect_db():
            return False
        
        try:
            # Crear tabla de redes sociales si no existe
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS artists_networks (
                id INTEGER PRIMARY KEY,
                artist_id INTEGER NOT NULL,
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
                discogs TEXT,
                discogs_http TEXT,
                enlaces TEXT,
                last_updated TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            )
            ''')
            
            # Verificar si las columnas 'discogs' y 'discogs_http' ya existen
            self.cursor.execute("PRAGMA table_info(artists_networks)")
            columns = [col[1] for col in self.cursor.fetchall()]
            
            # Si la columna 'discogs' no existe, añadirla
            if 'discogs' not in columns:
                self.logger.info("Añadiendo columna 'discogs' a la tabla artists_networks")
                self.cursor.execute("ALTER TABLE artists_networks ADD COLUMN discogs TEXT")
            
            # Si la columna 'discogs_http' no existe, añadirla
            if 'discogs_http' not in columns:
                self.logger.info("Añadiendo columna 'discogs_http' a la tabla artists_networks")
                self.cursor.execute("ALTER TABLE artists_networks ADD COLUMN discogs_http TEXT")
            
            # Crear índice para búsquedas más rápidas
            self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_artists_networks_artist_id
            ON artists_networks (artist_id)
            ''')
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error al configurar la base de datos: {str(e)}")
            self.conn.rollback()
            return False
        finally:
            self.close_db()


            
    
    
    def extract_social_networks(self, html_content, artist_name):
        """
        Extrae enlaces a redes sociales del HTML de la página de Discogs.
        
        Args:
            html_content (str): Contenido HTML de la página.
            artist_name (str): Nombre del artista para búsquedas alternativas.
            
        Returns:
            dict: Diccionario con las redes sociales encontradas.
        """
        networks = {
            'allmusic': None,
            'bandcamp': None,
            'boomkat': None,
            'facebook': None,
            'twitter': None,
            'mastodon': None,
            'bluesky': None,
            'instagram': None,
            'spotify': None,
            'lastfm': None,
            'wikipedia': None,
            'juno': None,
            'soundcloud': None,
            'youtube': None,
            'imdb': None,
            'progarchives': None,
            'setlist_fm': None,
            'who_sampled': None,
            'vimeo': None,
            'genius': None,
            'myspace': None,
            'tumblr': None,
            'resident_advisor': None,
            'rateyourmusic': None,
            'enlaces': []
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Buscar los enlaces en la tabla con la información del artista
            links = soup.select("table.table_c5ftk tbody tr td a.link_wXY7O")
            
            for link in links:
                url = link.get('href')
                if not url:
                    continue
                
                # Extraer el dominio
                parsed_url = urlparse(url)
                domain = parsed_url.netloc or parsed_url.path
                
                # Remover www. si existe
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                # Clasificar según el dominio
                matched = False
                for key, network in self.known_networks.items():
                    if key in domain:
                        networks[network] = url
                        matched = True
                        break
                
                if not matched:
                    networks['enlaces'].append(url)
            
            # Convertir la lista de enlaces a JSON
            if networks['enlaces']:
                networks['enlaces'] = json.dumps(networks['enlaces'])
            else:
                networks['enlaces'] = None
                
            return networks
        except Exception as e:
            self.logger.error(f"Error al extraer redes sociales para {artist_name}: {str(e)}")
            return networks
    
    def get_discogs_page(self, artist_url):
        """
        Obtiene el contenido HTML de la página de Discogs del artista.
        
        Args:
            artist_url (str): URL de Discogs del artista.
            
        Returns:
            str: Contenido HTML de la página.
        """
        if not artist_url:
            return None
        
        max_retries = self.config.get('max_retries', 3)
        rate_limit = self.config.get('rate_limit', 1.0)
        
        for attempt in range(max_retries):
            try:
                # Asegurar el rate limit
                time.sleep(rate_limit)
                
                response = requests.get(
                    artist_url,
                    headers={
                        'User-Agent': self.config.get('user_agent', 'MusicDatabaseApp/1.0'),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    },
                    timeout=30,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 404:
                    self.logger.warning(f"Página no encontrada (404): {artist_url}")
                    return None
                elif response.status_code == 429:
                    self.logger.warning(f"Rate limit excedido (429), esperando más tiempo...")
                    time.sleep(rate_limit * 5)  # Esperar más tiempo en caso de rate limit
                    continue
                else:
                    self.logger.warning(f"Error HTTP {response.status_code} para URL: {artist_url}")
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout al obtener página ({attempt + 1}/{max_retries}): {artist_url}")
                time.sleep(rate_limit * 2)
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error al obtener página de Discogs ({attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(rate_limit * 2)
        
        return None
    
    def search_discogs_artist(self, artist_name):
        """
        Busca un artista en Discogs a través de la API.
        
        Args:
            artist_name (str): Nombre del artista a buscar.
            
        Returns:
            tuple: (URL de API de Discogs, URL HTTP de Discogs) o (None, None) si no se encontró.
        """
        artist_result = self.discogs_client.search_artist(artist_name)
        if artist_result:
            api_url = artist_result.get('resource_url')
            discogs_http_url = None
            
            try:
                # Esperar para respetar el rate limit
                time.sleep(self.config.get('rate_limit', 1.0))
                
                response = requests.get(
                    api_url,
                    headers={
                        'User-Agent': self.config.get('user_agent', 'MusicDatabaseApp/1.0'),
                        'Authorization': f'Discogs token={self.discogs_token}' if self.discogs_token else None
                    },
                    timeout=30
                )
                
                # Verificar el status code antes de intentar parsear JSON
                if response.status_code == 200:
                    try:
                        artist_data = response.json()
                        if 'uri' in artist_data:
                            discogs_http_url = artist_data['uri']
                        else:
                            # Construir la URL HTTP a partir de la URL de la API
                            artist_id = api_url.split('/')[-1]
                            normalized_name = re.sub(r'[^\w\s-]', '', artist_name).replace(' ', '-')
                            discogs_http_url = f"https://www.discogs.com/artist/{artist_id}-{normalized_name}"
                    except ValueError as json_error:
                        self.logger.warning(f"Error al parsear JSON de Discogs para {artist_name}: {json_error}")
                        self.logger.debug(f"Respuesta recibida: {response.text[:200]}")
                        # Construir la URL HTTP de forma alternativa
                        artist_id = api_url.split('/')[-1]
                        normalized_name = re.sub(r'[^\w\s-]', '', artist_name).replace(' ', '-')
                        discogs_http_url = f"https://www.discogs.com/artist/{artist_id}-{normalized_name}"
                else:
                    self.logger.warning(f"Error HTTP {response.status_code} al obtener datos de Discogs para {artist_name}")
                    # Construir la URL HTTP de forma alternativa
                    artist_id = api_url.split('/')[-1]
                    normalized_name = re.sub(r'[^\w\s-]', '', artist_name).replace(' ', '-')
                    discogs_http_url = f"https://www.discogs.com/artist/{artist_id}-{normalized_name}"
            
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Error de conexión al obtener datos de Discogs para {artist_name}: {str(e)}")
                # Construir la URL HTTP de forma alternativa
                artist_id = api_url.split('/')[-1]
                normalized_name = re.sub(r'[^\w\s-]', '', artist_name).replace(' ', '-')
                discogs_http_url = f"https://www.discogs.com/artist/{artist_id}-{normalized_name}"
            
            return api_url, discogs_http_url
        
        return None, None
    
    def process_artist(self, artist):
        """
        Procesa un artista, obteniendo sus redes sociales.
        
        Args:
            artist (sqlite3.Row): Fila con la información del artista.
            
        Returns:
            dict: Resultado del procesamiento.
        """
        artist_id = artist['id']
        artist_name = artist['name']
        
        # Verificar si existe la columna discogs_url antes de intentar acceder
        discogs_url = None
        if 'discogs_url' in artist.keys():
            discogs_url = artist['discogs_url']
        
        self.logger.info(f"Procesando artista: {artist_name} (ID: {artist_id})")
        
        
        # Variables para ambas URLs de Discogs
        discogs_api_url = None
        discogs_http_url = None
        
        if not discogs_url:
            # Buscar en Discogs API - ahora devuelve ambas URLs
            discogs_api_url, discogs_http_url = self.search_discogs_artist(artist_name)
            discogs_url = discogs_api_url  # Para mantener compatibilidad con el resto del código
            
            if not discogs_api_url:
                self.logger.warning(f"No se encontró el artista '{artist_name}' en Discogs")
                
                # Guardar un registro vacío para no volver a procesar
                if not self.connect_db():
                    return {"success": False, "artist_id": artist_id, "message": "Error de conexión"}
                
                try:
                    # Verificar si ya existe
                    self.cursor.execute('SELECT id FROM artists_networks WHERE artist_id = ?', (artist_id,))
                    existing = self.cursor.fetchone()
                    
                    if existing:
                        # Ya existe, actualizar timestamp
                        self.cursor.execute('''
                        UPDATE artists_networks SET last_updated = ? WHERE artist_id = ?
                        ''', (datetime.now(), artist_id))
                    else:
                        # Insertar nuevo registro vacío
                        self.cursor.execute('''
                        INSERT INTO artists_networks 
                        (artist_id, last_updated) 
                        VALUES (?, ?)
                        ''', (artist_id, datetime.now()))
                        
                    self.conn.commit()
                    self.logger.info(f"Guardado registro vacío para '{artist_name}'")
                except sqlite3.Error as e:
                    self.logger.error(f"Error al guardar registro vacío: {str(e)}")
                    self.conn.rollback()
                finally:
                    self.close_db()
                
                return {"success": False, "artist_id": artist_id, "message": "No encontrado en Discogs"}
        else:
            # Si ya tenemos la URL de la API, intentar obtener la URL HTTP
            try:
                discogs_api_url = discogs_url
                # Esperar para respetar el rate limit
                time.sleep(self.config.get('rate_limit', 1.0))
                
                response = requests.get(
                    discogs_api_url,
                    headers={'User-Agent': self.config.get('user_agent', 'MusicDatabaseApp/1.0')}
                )
                response.raise_for_status()
                
                artist_data = response.json()
                if 'uri' in artist_data:
                    discogs_http_url = artist_data['uri']
                else:
                    # Construir la URL HTTP a partir de la URL de la API
                    artist_id = discogs_api_url.split('/')[-1]
                    normalized_name = artist_name.replace(' ', '-')
                    discogs_http_url = f"https://www.discogs.com/artist/{artist_id}-{normalized_name}"
            
            except Exception as e:
                self.logger.warning(f"Error al obtener la URI HTTP de Discogs para {artist_name}: {str(e)}")
        
        # Obtener la página HTML
        html_content = self.get_discogs_page(discogs_http_url or discogs_api_url)
        if not html_content:
            self.logger.warning(f"No se pudo obtener la página de Discogs para '{artist_name}'")
            return {"success": False, "artist_id": artist_id}
        
        # Extraer las redes sociales
        networks = self.extract_social_networks(html_content, artist_name)
        
        # Añadir las URLs de Discogs a las redes sociales
        networks['discogs'] = discogs_api_url
        networks['discogs_http'] = discogs_http_url
        
        # Guardar en la base de datos
        if not self.connect_db():
            return {"success": False, "artist_id": artist_id}
        
        try:
            # Comprobar si ya existe un registro
            self.cursor.execute('SELECT id FROM artists_networks WHERE artist_id = ?', (artist_id,))
            existing = self.cursor.fetchone()
            
            if existing:
                # Actualizar registro existente
                query = '''
                UPDATE artists_networks SET 
                allmusic = ?, bandcamp = ?, boomkat = ?, facebook = ?, twitter = ?, mastodon = ?, bluesky = ?,
                instagram = ?, spotify = ?, lastfm = ?, wikipedia = ?, juno = ?,
                soundcloud = ?, youtube = ?, imdb = ?, progarchives = ?, setlist_fm = ?,
                who_sampled = ?, vimeo = ?, genius = ?, myspace = ?, tumblr = ?,
                resident_advisor = ?, rateyourmusic = ?, discogs = ?, discogs_http = ?, enlaces = ?, last_updated = ?
                WHERE artist_id = ?
                '''
                params = (
                    networks['allmusic'], networks['bandcamp'], networks['boomkat'],
                    networks['facebook'], networks['twitter'],
                    networks['mastodon'], networks['bluesky'], networks['instagram'],
                    networks['spotify'], networks['lastfm'], networks['wikipedia'],
                    networks['juno'], networks['soundcloud'], networks['youtube'],
                    networks['imdb'], networks['progarchives'], networks['setlist_fm'],
                    networks['who_sampled'], networks['vimeo'], networks['genius'],
                    networks['myspace'], networks['tumblr'], networks['resident_advisor'],
                    networks['rateyourmusic'], networks['discogs'], networks['discogs_http'],
                    networks['enlaces'], datetime.now(), artist_id
                )
            else:
                # Insertar nuevo registro
                query = '''
                INSERT INTO artists_networks 
                (artist_id, allmusic, bandcamp, boomkat, facebook, twitter, mastodon, bluesky,
                instagram, spotify, lastfm, wikipedia, juno, soundcloud,
                youtube, imdb, progarchives, setlist_fm, who_sampled, vimeo,
                genius, myspace, tumblr, resident_advisor, rateyourmusic, discogs, discogs_http, enlaces, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                params = (
                    artist_id, networks['allmusic'], networks['bandcamp'], networks['boomkat'],
                    networks['facebook'], networks['twitter'],
                    networks['mastodon'], networks['bluesky'], networks['instagram'],
                    networks['spotify'], networks['lastfm'], networks['wikipedia'],
                    networks['juno'], networks['soundcloud'], networks['youtube'],
                    networks['imdb'], networks['progarchives'], networks['setlist_fm'],
                    networks['who_sampled'], networks['vimeo'], networks['genius'],
                    networks['myspace'], networks['tumblr'], networks['resident_advisor'],
                    networks['rateyourmusic'], networks['discogs'], networks['discogs_http'],
                    networks['enlaces'], datetime.now()
                )
            
            self.cursor.execute(query, params)
            self.conn.commit()
            self.logger.info(f"Redes sociales guardadas para '{artist_name}'")
            return {"success": True, "artist_id": artist_id}
        except sqlite3.Error as e:
            self.logger.error(f"Error al guardar redes sociales para '{artist_name}': {str(e)}")
            self.conn.rollback()
            return {"success": False, "artist_id": artist_id}
        finally:
            self.close_db()
    
   


  

    def debug_dates(self):
        """
        Función de diagnóstico para entender el formato de fechas en la base de datos.
        """
        if not self.connect_db():
            return
        
        try:
            # Obtener algunas fechas de ejemplo
            self.cursor.execute("""
                SELECT artist_id, last_updated, 
                    typeof(last_updated) as tipo,
                    length(last_updated) as longitud
                FROM artists_networks 
                WHERE last_updated IS NOT NULL 
                LIMIT 10
            """)
            samples = self.cursor.fetchall()
            
            print("=== DIAGNÓSTICO DE FECHAS ===")
            for sample in samples:
                print(f"Artist ID: {sample[0]}")
                print(f"  Fecha original: '{sample[1]}'")
                print(f"  Tipo: {sample[2]}")
                print(f"  Longitud: {sample[3]}")
                print()
            
            # Probar diferentes métodos de comparación
            print("=== PRUEBAS DE COMPARACIÓN ===")
            
            # Método 1: Comparación directa de strings
            self.cursor.execute("""
                SELECT COUNT(*) FROM artists_networks 
                WHERE last_updated > '2025-05-20'
            """)
            count1 = self.cursor.fetchone()[0]
            print(f"Comparación string directa (> '2025-05-20'): {count1}")
            
            # Método 2: Usando datetime() con substr
            self.cursor.execute("""
                SELECT COUNT(*) FROM artists_networks 
                WHERE datetime(substr(last_updated, 1, 19)) > datetime('now', '-5 days')
            """)
            count2 = self.cursor.fetchone()[0]
            print(f"Con datetime(substr()): {count2}")
            
            # Método 3: Usando date() para comparar solo fechas
            self.cursor.execute("""
                SELECT COUNT(*) FROM artists_networks 
                WHERE date(last_updated) > date('now', '-5 days')
            """)
            count3 = self.cursor.fetchone()[0]
            print(f"Con date(): {count3}")
            
            # Método 4: Comparación manual con substr
            self.cursor.execute("""
                SELECT COUNT(*) FROM artists_networks 
                WHERE substr(last_updated, 1, 10) > date('now', '-5 days')
            """)
            count4 = self.cursor.fetchone()[0]
            print(f"Con substr() manual: {count4}")
            
            # Mostrar la fecha actual de SQLite
            self.cursor.execute("SELECT datetime('now'), date('now')")
            now = self.cursor.fetchone()
            print(f"Fecha actual SQLite: {now[0]} / {now[1]}")
            
        except sqlite3.Error as e:
            print(f"Error en diagnóstico: {e}")
        finally:
            self.close_db()


    def debug_dates_extended(self):
        """
        Función de diagnóstico extendida para entender la distribución de fechas.
        """
        if not self.connect_db():
            return
        
        try:
            print("=== DIAGNÓSTICO EXTENDIDO DE FECHAS ===")
            
            # Mostrar distribución por períodos
            periods = [
                ("Últimas 24 horas", "'-1 days'"),
                ("Últimos 7 días", "'-7 days'"),
                ("Últimos 30 días", "'-30 days'"),
                ("Últimos 60 días", "'-60 days'"),
                ("Últimos 90 días", "'-90 days'"),
                ("Últimos 120 días", "'-120 days'")
            ]
            
            for period_name, period_sql in periods:
                self.cursor.execute(f"""
                    SELECT COUNT(*) FROM artists_networks 
                    WHERE date(last_updated) > date('now', {period_sql})
                """)
                count = self.cursor.fetchone()[0]
                print(f"{period_name}: {count} artistas")
            
            # Mostrar algunos ejemplos específicos de fechas antiguas
            print("\n=== FECHAS MÁS ANTIGUAS ===")
            self.cursor.execute("""
                SELECT artist_id, last_updated
                FROM artists_networks 
                WHERE last_updated IS NOT NULL
                ORDER BY last_updated ASC
                LIMIT 10
            """)
            oldest = self.cursor.fetchall()
            for record in oldest:
                print(f"Artist {record[0]}: {record[1]}")
            
            # Mostrar algunos ejemplos específicos de fechas recientes
            print("\n=== FECHAS MÁS RECIENTES ===")
            self.cursor.execute("""
                SELECT artist_id, last_updated
                FROM artists_networks 
                WHERE last_updated IS NOT NULL
                ORDER BY last_updated DESC
                LIMIT 10
            """)
            newest = self.cursor.fetchall()
            for record in newest:
                print(f"Artist {record[0]}: {record[1]}")
            
            # Verificar si hay artistas sin MBID con fechas antiguas
            print("\n=== ARTISTAS SIN MBID CON FECHAS ANTIGUAS ===")
            self.cursor.execute("""
                SELECT COUNT(*) FROM artists a
                JOIN artists_networks an ON a.id = an.artist_id
                WHERE (a.mbid IS NULL OR a.mbid = '')
                AND date(an.last_updated) < date('now', '-90 days')
            """)
            no_mbid_old = self.cursor.fetchone()[0]
            print(f"Artistas sin MBID actualizados hace >90 días: {no_mbid_old}")
            
            # Verificar si hay artistas con MBID con fechas antiguas
            print("\n=== ARTISTAS CON MBID CON FECHAS ANTIGUAS ===")
            self.cursor.execute("""
                SELECT COUNT(*) FROM artists a
                JOIN artists_networks an ON a.id = an.artist_id
                WHERE (a.mbid IS NOT NULL AND a.mbid != '')
                AND date(an.last_updated) < date('now', '-60 days')
            """)
            mbid_old = self.cursor.fetchone()[0]
            print(f"Artistas con MBID actualizados hace >60 días: {mbid_old}")
            
            # Mostrar algunos ejemplos concretos que deberían procesarse
            if mbid_old > 0:
                print("\n=== EJEMPLOS DE ARTISTAS CON MBID ANTIGUOS ===")
                self.cursor.execute("""
                    SELECT a.id, a.name, an.last_updated
                    FROM artists a
                    JOIN artists_networks an ON a.id = an.artist_id
                    WHERE (a.mbid IS NOT NULL AND a.mbid != '')
                    AND date(an.last_updated) < date('now', '-60 days')
                    ORDER BY an.last_updated ASC
                    LIMIT 5
                """)
                examples = self.cursor.fetchall()
                for record in examples:
                    print(f"  Artist {record[0]} ({record[1]}): {record[2]}")
            
            if no_mbid_old > 0:
                print("\n=== EJEMPLOS DE ARTISTAS SIN MBID ANTIGUOS ===")
                self.cursor.execute("""
                    SELECT a.id, a.name, an.last_updated
                    FROM artists a
                    JOIN artists_networks an ON a.id = an.artist_id
                    WHERE (a.mbid IS NULL OR a.mbid = '')
                    AND date(an.last_updated) < date('now', '-90 days')
                    ORDER BY an.last_updated ASC
                    LIMIT 5
                """)
                examples = self.cursor.fetchall()
                for record in examples:
                    print(f"  Artist {record[0]} ({record[1]}): {record[2]}")
                    
        except sqlite3.Error as e:
            print(f"Error en diagnóstico extendido: {e}")
        finally:
            self.close_db()


    def get_artists_to_process(self):
        """
        Obtiene la lista de artistas para procesar, priorizando aquellos con MBID.
        VERSIÓN CON LOGGING MEJORADO para debugging.
        """
        if not self.connect_db():
            return []
        
        try:
            # Primero, comprobar si hay artistas en la base de datos
            self.cursor.execute("SELECT COUNT(*) FROM artists")
            artist_count = self.cursor.fetchone()[0]
            self.logger.info(f"Total de artistas en la base de datos: {artist_count}")
            
            # Contar artistas con MBID
            self.cursor.execute("SELECT COUNT(*) FROM artists WHERE mbid IS NOT NULL AND mbid != ''")
            mbid_count = self.cursor.fetchone()[0]
            self.logger.info(f"Artistas con MBID: {mbid_count}")
            
            if artist_count == 0:
                self.logger.warning("No hay artistas en la base de datos")
                return []
            
            # Verificar si la tabla artists_networks existe
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artists_networks'")
            if not self.cursor.fetchone():
                # La tabla no existe, procesaremos artistas priorizando los que tienen MBID
                self.logger.info("La tabla artists_networks no existe, priorizando artistas con MBID")
                query = '''
                SELECT a.id, a.name, a.discogs_url 
                FROM artists a
                ORDER BY CASE 
                    WHEN a.mbid IS NOT NULL AND a.mbid != '' THEN 1 
                    ELSE 2 
                END, a.id
                LIMIT ?
                '''
                self.cursor.execute(query, (self.config.get('batch_size', 50),))
                result = self.cursor.fetchall()
                return result
            
            # Verificar cuántos artistas ya tienen redes sociales
            self.cursor.execute("SELECT COUNT(*) FROM artists_networks")
            networks_count = self.cursor.fetchone()[0]
            self.logger.info(f"Artistas con registros en artists_networks: {networks_count}")
            
            # Verificar cuántos fueron actualizados recientemente
            self.cursor.execute("""
                SELECT COUNT(*) FROM artists_networks 
                WHERE date(last_updated) > date('now', '-7 days')
            """)
            recent_count = self.cursor.fetchone()[0]
            self.logger.info(f"Artistas actualizados en los últimos 7 días: {recent_count}")
            
            if self.config.get('force_update', False):
                # Modo force_update: procesar todos los artistas, priorizando MBID
                self.logger.info("Modo force_update activado: procesando todos los artistas")
                query = '''
                SELECT a.id, a.name, a.discogs_url 
                FROM artists a
                ORDER BY CASE 
                    WHEN a.mbid IS NOT NULL AND a.mbid != '' THEN 1 
                    ELSE 2 
                END, a.id
                LIMIT ?
                '''
                self.cursor.execute(query, (self.config.get('batch_size', 50),))
                result = self.cursor.fetchall()
                self.logger.info(f"Seleccionados {len(result)} artistas para force_update")
                return result
            
            elif self.config.get('missing_only', True):
                # Modo missing_only MUY ESTRICTO con priorización por MBID
                
                # Primero: artistas con MBID que no tienen registro
                query_mbid_no_record = '''
                SELECT a.id, a.name, a.discogs_url 
                FROM artists a
                WHERE (a.mbid IS NOT NULL AND a.mbid != '')
                AND a.id NOT IN (SELECT DISTINCT artist_id FROM artists_networks WHERE artist_id IS NOT NULL)
                ORDER BY a.id
                LIMIT ?
                '''
                
                self.cursor.execute(query_mbid_no_record, (self.config.get('batch_size', 50),))
                result = self.cursor.fetchall()
                
                if len(result) > 0:
                    self.logger.info(f"Encontrados {len(result)} artistas CON MBID sin registro en artists_networks")
                    return result
                
                # Segundo: artistas SIN MBID pero sin registro
                query_no_mbid_no_record = '''
                SELECT a.id, a.name, a.discogs_url 
                FROM artists a
                WHERE (a.mbid IS NULL OR a.mbid = '')
                AND a.id NOT IN (SELECT DISTINCT artist_id FROM artists_networks WHERE artist_id IS NOT NULL)
                ORDER BY a.id
                LIMIT ?
                '''
                
                self.cursor.execute(query_no_mbid_no_record, (min(self.config.get('batch_size', 50) // 2, 25),))
                result = self.cursor.fetchall()
                
                if len(result) > 0:
                    self.logger.info(f"Encontrados {len(result)} artistas SIN MBID sin registro en artists_networks")
                    return result
                
                # Tercero: artistas con MBID muy desactualizados (>60 días) - CON LOGGING DETALLADO
                query_mbid_old = '''
                SELECT a.id, a.name, a.discogs_url 
                FROM artists a
                JOIN artists_networks an ON a.id = an.artist_id
                WHERE (a.mbid IS NOT NULL AND a.mbid != '')
                AND (an.last_updated IS NULL OR date(an.last_updated) < date('now', '-60 days'))
                ORDER BY COALESCE(an.last_updated, '1970-01-01')
                LIMIT ?
                '''
                
                # Primero contar cuántos hay
                count_query = '''
                SELECT COUNT(*) FROM artists a
                JOIN artists_networks an ON a.id = an.artist_id
                WHERE (a.mbid IS NOT NULL AND a.mbid != '')
                AND (an.last_updated IS NULL OR date(an.last_updated) < date('now', '-60 days'))
                '''
                self.cursor.execute(count_query)
                count_available = self.cursor.fetchone()[0]
                self.logger.info(f"Artistas con MBID desactualizados (>60 días) disponibles: {count_available}")
                
                self.cursor.execute(query_mbid_old, (self.config.get('batch_size', 50),))
                result = self.cursor.fetchall()
                
                if len(result) > 0:
                    self.logger.info(f"Seleccionados {len(result)} artistas con MBID desactualizados (>60 días)")
                    # Mostrar algunos ejemplos
                    for i, artist in enumerate(result[:3]):
                        self.logger.info(f"  Ejemplo {i+1}: Artist {artist[0]} - {artist[1]}")
                    return result
                
                # Cuarto: otros artistas desactualizados pero sin MBID - CON LOGGING DETALLADO
                count_query_no_mbid = '''
                SELECT COUNT(*) FROM artists a
                JOIN artists_networks an ON a.id = an.artist_id
                WHERE (a.mbid IS NULL OR a.mbid = '')
                AND (an.last_updated IS NULL OR date(an.last_updated) < date('now', '-90 days'))
                '''
                self.cursor.execute(count_query_no_mbid)
                count_available_no_mbid = self.cursor.fetchone()[0]
                self.logger.info(f"Artistas sin MBID desactualizados (>90 días) disponibles: {count_available_no_mbid}")
                
                query_no_mbid_old = '''
                SELECT a.id, a.name, a.discogs_url 
                FROM artists a
                JOIN artists_networks an ON a.id = an.artist_id
                WHERE (a.mbid IS NULL OR a.mbid = '')
                AND (an.last_updated IS NULL OR date(an.last_updated) < date('now', '-90 days'))
                ORDER BY COALESCE(an.last_updated, '1970-01-01')
                LIMIT ?
                '''
                
                self.cursor.execute(query_no_mbid_old, (min(self.config.get('batch_size', 50) // 4, 10),))
                result = self.cursor.fetchall()
                
                self.logger.info(f"Seleccionados {len(result)} artistas sin MBID muy desactualizados (>90 días)")
                # Mostrar algunos ejemplos
                for i, artist in enumerate(result[:3]):
                    self.logger.info(f"  Ejemplo {i+1}: Artist {artist[0]} - {artist[1]}")
                return result
            else:
                # Modo normal: seleccionar artistas al azar, priorizando MBID
                query = '''
                SELECT a.id, a.name, a.discogs_url 
                FROM artists a
                ORDER BY CASE 
                    WHEN a.mbid IS NOT NULL AND a.mbid != '' THEN 1 
                    ELSE 2 
                END, RANDOM()
                LIMIT ?
                '''
                self.cursor.execute(query, (self.config.get('batch_size', 50),))
                result = self.cursor.fetchall()
                return result
                
        except sqlite3.Error as e:
            self.logger.error(f"Error al obtener artistas: {str(e)}")
            self.conn.rollback()
            return []
        finally:
            self.close_db()




    def run(self):
        """
        Ejecuta el procesamiento de redes sociales de artistas.
        VERSIÓN CORREGIDA con mejor manejo de fechas.
        """
        self.logger.info(f"Iniciando procesamiento de redes sociales con configuración:")
        self.logger.info(f"  force_update: {self.config.get('force_update', False)}")
        self.logger.info(f"  missing_only: {self.config.get('missing_only', True)}")
        self.logger.info(f"  batch_size: {self.config.get('batch_size', 50)}")
        
        # Verificar la configuración
        if not self.db_path:
            self.logger.error("Error: No se ha especificado la ruta de la base de datos (db_path)")
            return False
        
        # OPCIONAL: Ejecutar diagnóstico de fechas si hay problemas
        self.debug_dates_extended()
        
        # Configurar la base de datos
        if not self.setup_database():
            self.logger.error("Error al configurar la base de datos. Abortando.")
            return False
        
        # Obtener artistas para procesar
        artists = self.get_artists_to_process()
        if not artists:
            self.logger.info("No hay artistas para procesar según los criterios configurados.")
            
            # Verificar si hay artistas en la base de datos
            if not self.connect_db():
                return False
            
            try:
                self.cursor.execute("SELECT COUNT(*) FROM artists")
                artist_count = self.cursor.fetchone()[0]
                
                if artist_count == 0:
                    self.logger.warning("No hay artistas en la base de datos. Debe ejecutar primero los scripts que importan artistas.")
                else:
                    self.logger.info(f"Total de artistas en la base de datos: {artist_count}")
                    
                    # Verificar diferentes categorías de artistas - MÉTODO MÁS ROBUSTO
                    # 1. Sin registro en artists_networks
                    self.cursor.execute('''
                        SELECT COUNT(*) FROM artists a
                        WHERE a.id NOT IN (SELECT DISTINCT artist_id FROM artists_networks WHERE artist_id IS NOT NULL)
                    ''')
                    no_record_count = self.cursor.fetchone()[0]
                    
                    # 2. Con MBID pero sin registro
                    self.cursor.execute('''
                        SELECT COUNT(*) FROM artists a
                        WHERE (a.mbid IS NOT NULL AND a.mbid != '')
                        AND a.id NOT IN (SELECT DISTINCT artist_id FROM artists_networks WHERE artist_id IS NOT NULL)
                    ''')
                    mbid_no_record_count = self.cursor.fetchone()[0]
                    
                    # 3. Desactualizados (>60 días) - MÉTODO MÁS ROBUSTO
                    self.cursor.execute('''
                        SELECT COUNT(*) FROM artists a
                        JOIN artists_networks an ON a.id = an.artist_id
                        WHERE an.last_updated IS NULL 
                        OR date(an.last_updated) < date('now', '-60 days')
                    ''')
                    old_count = self.cursor.fetchone()[0]
                    
                    # 4. Actualizados recientemente (últimos 7 días) - MÉTODO MÁS ROBUSTO
                    self.cursor.execute('''
                        SELECT COUNT(*) FROM artists_networks 
                        WHERE date(last_updated) > date('now', '-7 days')
                    ''')
                    recent_count = self.cursor.fetchone()[0]
                    
                    self.logger.info(f"Resumen de estado de artistas:")
                    self.logger.info(f"  - Sin registro en artists_networks: {no_record_count}")
                    self.logger.info(f"  - Con MBID pero sin registro: {mbid_no_record_count}")
                    self.logger.info(f"  - Desactualizados (>60 días): {old_count}")
                    self.logger.info(f"  - Actualizados recientemente (<7 días): {recent_count}")
                    
                    if no_record_count == 0 and old_count == 0:
                        self.logger.info("No hay artistas que necesiten actualización según missing_only=true.")
                        self.logger.info("Todos los artistas tienen registro y están relativamente actualizados.")
                        self.logger.info("Para forzar actualización de todos los artistas, use force_update=true.")
                    else:
                        self.logger.info("Hay artistas que deberían procesarse, pero se aplicaron filtros estrictos.")
                        self.logger.info("Considere:")
                        self.logger.info("  - Aumentar batch_size si es muy pequeño")
                        self.logger.info("  - Usar force_update=true para procesar artistas recientes")
                        self.logger.info("  - Verificar los logs de debug para más detalles")
                        
            except sqlite3.Error as e:
                self.logger.error(f"Error al verificar artistas: {str(e)}")
            finally:
                self.close_db()
            
            return True
        
        self.logger.info(f"Se procesarán {len(artists)} artistas")
        
        # NUEVA VERIFICACIÓN: Filtrar artistas que necesitan actualización
        if not self.config.get('force_update', False):
            filtered_artists = []
            skipped_count = 0
            
            for artist in artists:
                artist_id = artist[0]  # El ID es el primer elemento de la tupla
                artist_name = artist[1]  # El nombre es el segundo elemento
                
                if self.should_skip_artist(artist_id):
                    skipped_count += 1
                    self.logger.debug(f"SALTANDO artista '{artist_name}' (ID: {artist_id}) - actualizado recientemente")
                else:
                    filtered_artists.append(artist)
            
            if skipped_count > 0:
                self.logger.info(f"Se saltaron {skipped_count} artistas por estar actualizados recientemente")
            
            artists = filtered_artists
            
            if not artists:
                self.logger.info("No hay artistas que necesiten actualización después del filtrado")
                return True
        
        self.logger.info(f"Procesando {len(artists)} artistas después del filtrado")
        
        # Procesar artistas
        if self.config.get('concurrent_workers', 1) > 1:
            # Procesamiento en paralelo
            with ThreadPoolExecutor(max_workers=self.config.get('concurrent_workers')) as executor:
                results = list(executor.map(self.process_artist, artists))
        else:
            # Procesamiento secuencial
            results = [self.process_artist(artist) for artist in artists]
        
        # Resumen de resultados
        successful = sum(1 for r in results if r.get('success', False))
        failed = len(results) - successful
        
        self.logger.info(f"Procesamiento completado: {successful} exitosos, {failed} fallidos")
        return True


    def should_skip_artist(self, artist_id):
        """
        Verifica si debemos saltar este artista (para usar en el bucle principal).
        
        Args:
            artist_id (int): ID del artista a verificar
            
        Returns:
            bool: True si debemos saltar el artista, False si debemos procesarlo
        """
        if self.config.get('force_update', False):
            return False  # Si force_update está activo, nunca saltar
        
        return not self.needs_update(artist_id)

    def needs_update(self, artist_id):
        """
        Verifica si un artista necesita actualización basado en la configuración.
        VERSIÓN CORREGIDA con mejor manejo de fechas.
        """
        if not self.connect_db():
            return True
        
        try:
            # Obtener información del registro de redes sociales - MÉTODO MÁS ROBUSTO
            self.cursor.execute('''
            SELECT *, 
                CASE 
                    WHEN last_updated IS NULL THEN 'nunca'
                    WHEN date(last_updated) > date('now', '-1 days') THEN 'hoy'
                    WHEN date(last_updated) > date('now', '-7 days') THEN 'esta_semana'
                    WHEN date(last_updated) > date('now', '-30 days') THEN 'este_mes'
                    ELSE 'antiguo'
                END as update_status
            FROM artists_networks 
            WHERE artist_id = ?
            ''', (artist_id,))
            record = self.cursor.fetchone()
            
            if not record:
                self.logger.debug(f"Artista {artist_id}: SIN registro - necesita actualización")
                return True  # No existe registro, necesita actualización
            
            if self.config.get('force_update', False):
                self.logger.debug(f"Artista {artist_id}: force_update activado")
                return True  # force_update activado
            
            update_status = record['update_status']
            
            # Si fue actualizado hoy, NO procesar (a menos que force_update esté activo)
            if update_status == 'hoy':
                self.logger.debug(f"Artista {artist_id}: actualizado HOY - SALTANDO")
                return False
                
            # Si fue actualizado esta semana, solo procesar si está muy incompleto
            if update_status == 'esta_semana':
                important_fields = ['facebook', 'twitter', 'instagram', 'spotify', 'youtube', 'bandcamp']
                empty_count = sum(1 for field in important_fields 
                                if record[field] is None or record[field] == '')
                
                if empty_count >= 5:  # Muy incompleto
                    self.logger.debug(f"Artista {artist_id}: actualizado esta semana pero MUY incompleto ({empty_count}/6 campos vacíos)")
                    return True
                else:
                    self.logger.debug(f"Artista {artist_id}: actualizado esta semana y relativamente completo - SALTANDO")
                    return False
            
            # Si fue actualizado este mes, solo procesar si está completamente vacío
            if update_status == 'este_mes':
                important_fields = ['facebook', 'twitter', 'instagram', 'spotify', 'youtube', 'bandcamp']
                empty_count = sum(1 for field in important_fields 
                                if record[field] is None or record[field] == '')
                
                if empty_count == 6:  # Completamente vacío
                    self.logger.debug(f"Artista {artist_id}: actualizado este mes pero COMPLETAMENTE vacío")
                    return True
                else:
                    self.logger.debug(f"Artista {artist_id}: actualizado este mes y tiene algunos datos - SALTANDO")
                    return False
            
            # Si es antiguo (>30 días) o nunca actualizado, procesar
            if update_status in ['antiguo', 'nunca']:
                self.logger.debug(f"Artista {artist_id}: {update_status} - necesita actualización")
                return True
            
            return False  # Por defecto, no actualizar
            
        except sqlite3.Error as e:
            self.logger.error(f"Error al verificar necesidad de actualización: {str(e)}")
            return True  # En caso de error, mejor actualizar
        finally:
            self.close_db()



def main(config=None):
    """
    Función principal para ejecutar el módulo.
    
    Args:
        config (dict, optional): Configuración del módulo.
    """
    module = RedesSocialesArtistas(config)
    return module.run()

if __name__ == "__main__":
    # Si se ejecuta directamente, utilizar configuración por defecto
    main()