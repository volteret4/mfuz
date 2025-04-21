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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_module import PROJECT_ROOT
from tools.discogs_login import DiscogsClient

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
        #super().__init__(config)
        self.logger = logging.getLogger("redes_sociales_artistas")
        self.config = config or {}
        
        # Configuración por defecto
        self.default_config = {
            'rate_limit': 1.0,
            'max_retries': 3,
            'batch_size': 50,
            'force_update': False,
            'missing_only': True,
            'concurrent_workers': 1
        }
        
        # Combinar con la configuración proporcionada
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
        
        # Inicializar cliente de Discogs
        self.discogs_token = self.config.get('discogs_token')
        if not self.discogs_token:
            self.logger.error("No se ha proporcionado un token de Discogs")
        
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
            'residentadvisor.net': 'resident_advisor'
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
                enlaces TEXT,
                last_updated TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            )
            ''')
            
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
    
    def get_artists_to_process(self):
        """
        Obtiene la lista de artistas para procesar.
        
        Returns:
            list: Lista de IDs de artistas para procesar.
        """
        if not self.connect_db():
            return []
        
        try:
            if self.config.get('missing_only', True):
                # Obtener artistas que no están en la tabla artists_networks
                query = '''
                SELECT a.id, a.name, a.discogs_url 
                FROM artists a
                LEFT JOIN artists_networks an ON a.id = an.artist_id
                WHERE an.id IS NULL
                ORDER BY a.id
                LIMIT ?
                '''
                self.cursor.execute(query, (self.config.get('batch_size', 50),))
            else:
                # Obtener todos los artistas
                query = '''
                SELECT a.id, a.name, a.discogs_url 
                FROM artists a
                ORDER BY a.id
                LIMIT ?
                '''
                self.cursor.execute(query, (self.config.get('batch_size', 50),))
            
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error al obtener artistas: {str(e)}")
            return []
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
                    headers={'User-Agent': 'MusicDatabaseApp/1.0'}
                )
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error al obtener página de Discogs ({attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(rate_limit * 2)  # Aumentar el tiempo de espera en caso de error
        
        return None
    
    def search_discogs_artist(self, artist_name):
        """
        Busca un artista en Discogs a través de la API.
        
        Args:
            artist_name (str): Nombre del artista a buscar.
            
        Returns:
            str: URL de Discogs del artista, o None si no se encontró.
        """
        artist_result = self.discogs_client.search_artist(artist_name)
        if artist_result:
            return artist_result.get('resource_url')
        return None
    
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
        
        if not discogs_url:
            # Buscar en Discogs API
            discogs_url = self.search_discogs_artist(artist_name)
            if not discogs_url:
                self.logger.warning(f"No se encontró el artista '{artist_name}' en Discogs")
                
                # Guardar un registro vacío para no volver a procesar
                if self.config.get('missing_only', True):
                    if not self.connect_db():
                        return {"success": False, "artist_id": artist_id}
                    
                    try:
                        self.cursor.execute('''
                        INSERT INTO artists_networks 
                        (artist_id, last_updated) 
                        VALUES (?, ?)
                        ''', (artist_id, datetime.now(),))
                        self.conn.commit()
                    except sqlite3.Error as e:
                        self.logger.error(f"Error al guardar registro vacío: {str(e)}")
                        self.conn.rollback()
                    finally:
                        self.close_db()
                
                return {"success": False, "artist_id": artist_id}
        
        # Obtener la página HTML
        html_content = self.get_discogs_page(discogs_url)
        if not html_content:
            self.logger.warning(f"No se pudo obtener la página de Discogs para '{artist_name}'")
            return {"success": False, "artist_id": artist_id}
        
        # Extraer las redes sociales
        networks = self.extract_social_networks(html_content, artist_name)
        
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
                resident_advisor = ?, rateyourmusic = ?, enlaces = ?, last_updated = ?
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
                    networks['rateyourmusic'],
                    networks['enlaces'], datetime.now(), artist_id
                )
            else:
                # Insertar nuevo registro
                query = '''
                INSERT INTO artists_networks 
                (artist_id, allmusic, bandcamp, boomkat, facebook, twitter, mastodon, bluesky,
                instagram, spotify, lastfm, wikipedia, juno, soundcloud,
                youtube, imdb, progarchives, setlist_fm, who_sampled, vimeo,
                genius, myspace, tumblr, resident_advisor, rateyourmusic, enlaces, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    networks['rateyourmusic'],
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
    
    def run(self):
        """
        Ejecuta el procesamiento de redes sociales de artistas.
        """
        self.logger.info("Iniciando procesamiento de redes sociales")
        
        # Configurar la base de datos
        if not self.setup_database():
            self.logger.error("Error al configurar la base de datos. Abortando.")
            return False
        
        # Obtener artistas para procesar
        artists = self.get_artists_to_process()
        if not artists:
            self.logger.info("No hay artistas para procesar.")
            return True
        
        self.logger.info(f"Se procesarán {len(artists)} artistas")
        
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