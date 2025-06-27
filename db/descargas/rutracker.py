#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
import requests
import time
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

# Agregar el directorio padre al path para importar BaseModule
sys.path.append(str(Path(__file__).parent.parent))
from base_module import BaseModule, PROJECT_ROOT

class RuTrackerModule:
    def __init__(self, config=None):
        self.config = config or {}
        self.session = requests.Session()
        self.setup_logging()
        self.authenticated = False
        
        # Configuración por defecto
        self.rutracker_url = self.config.get('rutracker_url', 'https://rutracker.org')
        self.username = self.config.get('rutracker_username', '')
        self.password = self.config.get('rutracker_password', '')
        
        # Configuración para Jackett (alternativa)
        self.use_jackett = self.config.get('use_jackett', False)
        self.jackett_url = self.config.get('jackett_url', '')
        self.jackett_api_key = self.config.get('jackett_api_key', '')
        self.jackett_indexer = self.config.get('jackett_indexer', 'rutracker')
       
        self.rate_limit = self.config.get('rate_limit', 3.0)
        self.force_update = self.config.get('force_update', False)
        self.limit = self.config.get('limit', 0)
        self.db_path = self.config.get('db_path', '')
        
        self.last_request_time = 0
        
        # Configurar headers para evitar detección
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Configurar timeouts y reintentos
        self.session.timeout = (30, 60)  # connect timeout, read timeout
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 5)
        
        # Configurar proxy si está disponible
        proxy_config = self.config.get('proxy', {})
        if proxy_config:
            proxies = {}
            if proxy_config.get('http'):
                proxies['http'] = proxy_config['http']
            if proxy_config.get('https'):
                proxies['https'] = proxy_config['https']
            if proxies:
                self.session.proxies.update(proxies)
                self.logger.info(f"Proxy configurado: {proxies}")
        
        # Configurar SSL si está disponible
        if self.config.get('verify_ssl', True) is False:
            self.session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
    def setup_logging(self):
        """Configura el logging"""
        log_level = self.config.get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def rate_limit_request(self):
        """Implementa el rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()

    def check_site_availability(self):
        """Verifica si RuTracker está disponible"""
        test_urls = [
            f"{self.rutracker_url}",
            f"{self.rutracker_url}/forum/",
            "https://rutracker.org",
            "http://rutracker.org"
        ]
        
        for url in test_urls:
            try:
                self.logger.info(f"Verificando disponibilidad de {url}")
                response = self.make_request(url)
                if response.status_code == 200:
                    self.rutracker_url = url.rstrip('/')
                    self.logger.info(f"Sitio disponible en: {self.rutracker_url}")
                    return True
            except Exception as e:
                self.logger.debug(f"URL {url} no disponible: {e}")
                continue
        
        self.logger.error("RuTracker no está disponible en ninguna URL")
        return False

    def authenticate(self):
        """Autentica con RuTracker usando credenciales"""
        if not self.username or not self.password:
            self.logger.error("No se proporcionaron credenciales de autenticación")
            return False
        
        # Verificar disponibilidad del sitio primero
        if not self.check_site_availability():
            return False
            
        try:
            # Primero obtener la página principal para obtener el formulario de login
            main_page_url = f"{self.rutracker_url}/forum/index.php"
            self.logger.info(f"Obteniendo página principal: {main_page_url}")
            
            main_page = self.make_request(main_page_url)
            
            # Parsear la página para encontrar el formulario de login
            soup = BeautifulSoup(main_page.content, 'html.parser')
            
            # Buscar el formulario de login
            login_form = soup.find('form', {'action': True})
            if not login_form:
                # Intentar buscar por atributos específicos
                login_form = soup.find('form') or soup.find('div', {'id': 'loginForm'})
            
            if login_form:
                action = login_form.get('action', '')
                if action.startswith('/'):
                    login_url = f"{self.rutracker_url}{action}"
                elif action:
                    login_url = f"{self.rutracker_url}/forum/{action}"
                else:
                    login_url = f"{self.rutracker_url}/forum/login.php"
            else:
                # URLs comunes para login en RuTracker
                possible_urls = [
                    f"{self.rutracker_url}/forum/login.php",
                    f"{self.rutracker_url}/login.php",
                    f"{self.rutracker_url}/forum/index.php"
                ]
                login_url = possible_urls[0]
            
            self.logger.info(f"Intentando autenticación en: {login_url}")
            
            # Datos de login (formatos comunes en RuTracker)
            login_data_variants = [
                {
                    'login_username': self.username,
                    'login_password': self.password,
                    'login': 'Вход'
                },
                {
                    'username': self.username,
                    'password': self.password,
                    'login': 'Войти'
                },
                {
                    'login_username': self.username,
                    'login_password': self.password,
                    'submit': 'Войти'
                }
            ]
            
            # Intentar diferentes variantes de datos de login
            for i, login_data in enumerate(login_data_variants):
                try:
                    self.logger.info(f"Intento de login {i+1}/{len(login_data_variants)}")
                    response = self.make_request(login_url, method='POST', data=login_data)
                    
                    # Verificar si el login fue exitoso
                    success_indicators = [
                        'Вы зашли как',
                        'profile.php',
                        'logout.php',
                        'viewtopic.php',
                        self.username.lower() in response.text.lower()
                    ]
                    
                    if any(indicator in response.text for indicator in success_indicators):
                        self.logger.info("Autenticación exitosa con RuTracker")
                        self.authenticated = True
                        return True
                        
                except Exception as e:
                    self.logger.warning(f"Intento de login {i+1} falló: {e}")
                    continue
            
            # Si llegamos aquí, ninguna variante funcionó
            self.logger.error("Error en la autenticación - todas las variantes fallaron")
            
            # Intentar método alternativo: buscar directamente en la página principal
            if self.username.lower() in main_page.text.lower():
                self.logger.info("Posiblemente ya autenticado (usuario encontrado en página)")
                self.authenticated = True
                return True
                
            return False
                
        except Exception as e:
            self.logger.error(f"Error al autenticar: {e}")
            return False

    def make_request(self, url, method='GET', **kwargs):
        """Hace una petición HTTP con reintentos y manejo de errores"""
        for attempt in range(self.max_retries):
            try:
                self.rate_limit_request()
                
                if method.upper() == 'GET':
                    response = self.session.get(url, timeout=(30, 60), **kwargs)
                else:
                    response = self.session.post(url, timeout=(30, 60), **kwargs)
                
                # Verificar códigos de estado problemáticos
                if response.status_code == 504:
                    raise requests.exceptions.Timeout("Gateway Timeout")
                elif response.status_code == 503:
                    raise requests.exceptions.ConnectionError("Service Unavailable")
                elif response.status_code == 429:
                    raise requests.exceptions.ConnectionError("Too Many Requests")
                
                response.raise_for_status()
                return response
                
            except (requests.exceptions.Timeout, 
                    requests.exceptions.ConnectionError,
                    requests.exceptions.HTTPError) as e:
                
                self.logger.warning(f"Intento {attempt + 1}/{self.max_retries} falló para {url}: {e}")
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Backoff exponencial
                    self.logger.info(f"Esperando {wait_time} segundos antes del siguiente intento...")
                    time.sleep(wait_time)
                else:
                    raise e
            except Exception as e:
                self.logger.error(f"Error inesperado en petición a {url}: {e}")
                raise e

    def search_artist_albums_via_jackett(self, artist_name, max_results=50):
        """Busca álbumes usando Jackett como intermediario para RuTracker"""
        if not self.jackett_url or not self.jackett_api_key:
            self.logger.error("Configuración de Jackett faltante")
            return []
        
        self.logger.info(f"Buscando {artist_name} vía Jackett")
        
        # URL de Jackett para búsqueda en RuTracker
        url = f"{self.jackett_url}/api/v2.0/indexers/{self.jackett_indexer}/results/torznab"
        
        params = {
            "apikey": self.jackett_api_key,
            "t": "music",
            "cat": "3000",  # Categoría de música
            "q": artist_name.replace(" ", "+"),
            "limit": max_results
        }
        
        try:
            response = self.make_request(url, params=params)
            return self.parse_jackett_response(response.text, artist_name)
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda vía Jackett: {e}")
            return []

    def parse_jackett_response(self, xml_response, artist_name):
        """Parsea la respuesta XML de Jackett"""
        import xml.etree.ElementTree as ET
        
        results = []
        
        try:
            root = ET.fromstring(xml_response)
            namespace = {"torznab": "http://torznab.com/schemas/2015/feed"}
            
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                pubdate_elem = item.find("pubDate")
                
                if title_elem is None or link_elem is None:
                    continue
                
                title = title_elem.text
                download_url = link_elem.text
                pub_date = pubdate_elem.text if pubdate_elem is not None else ""
                
                # Obtener atributos específicos de torznab
                size = 0
                seeders = 0
                leechers = 0
                
                for attr in item.findall(".//torznab:attr", namespace):
                    attr_name = attr.get("name")
                    attr_value = attr.get("value")
                    
                    if attr_name == "size" and attr_value:
                        size = int(attr_value)
                    elif attr_name == "seeders" and attr_value:
                        seeders = int(attr_value)
                    elif attr_name == "leechers" and attr_value:
                        leechers = int(attr_value)
                
                # Verificar si coincide con el artista
                if self.title_matches_artist(title, artist_name):
                    # Extraer ID del torrent si es posible
                    torrent_id = self.extract_torrent_id_from_url(download_url)
                    
                    # Parsear información del título
                    album_info = self.parse_title_info(title)
                    
                    result = {
                        'torrent_id': torrent_id or f"jackett_{len(results)}",
                        'title': title,
                        'album_name': album_info.get('album', ''),
                        'artist_name': album_info.get('artist', artist_name),
                        'year': album_info.get('year', 0),
                        'format': album_info.get('format', ''),
                        'quality': album_info.get('quality', ''),
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'post_url': download_url,
                        'download_url': download_url,
                        'pub_date': pub_date
                    }
                    
                    results.append(result)
            
            return results
            
        except ET.ParseError as e:
            self.logger.error(f"Error parseando XML de Jackett: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error procesando respuesta de Jackett: {e}")
            return []

    def extract_torrent_id_from_url(self, url):
        """Extrae ID del torrent de una URL de Jackett"""
        import re
        # Buscar patrones comunes en URLs de torrents
        patterns = [
            r'(?:t=|torrent=|id=)(\d+)',
            r'/(\d+)\.torrent',
            r'hash=([a-fA-F0-9]{40})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    def search_artist_albums(self, artist_name, max_pages=3):
        """Busca álbumes de un artista en RuTracker (directo o vía Jackett)"""
        
        # Si está configurado para usar Jackett, usarlo directamente
        if self.use_jackett:
            self.logger.info(f"Usando Jackett para buscar {artist_name}")
            return self.search_artist_albums_via_jackett(artist_name)
        
        # Intentar primero la búsqueda directa
        if not self.authenticated:
            if not self.authenticate():
                self.logger.warning("Fallo autenticación directa, intentando vía Jackett si está configurado")
                if self.jackett_url and self.jackett_api_key:
                    self.logger.info("Fallback a Jackett")
                    return self.search_artist_albums_via_jackett(artist_name)
                return []

        results = []
        search_query = artist_name
        
        # Categorías de música en RuTracker (ajustar según necesidad)
        music_categories = [
            '2321',  # Lossless
            '2320',  # MP3
            '2327',  # Alternative/Indie
            '2328',  # Electronic
            '2329'   # Rock
        ]
        
        for page in range(max_pages):
            # URLs posibles para búsqueda
            search_urls = [
                f"{self.rutracker_url}/forum/tracker.php",
                f"{self.rutracker_url}/forum/viewforum.php",
                f"{self.rutracker_url}/forum/search.php"
            ]
            
            page_results = []
            
            for search_url in search_urls:
                params = {
                    'nm': search_query,
                    'start': page * 50,  # RuTracker usa 50 resultados por página
                    'f': ','.join(music_categories)  # Categorías de música
                }
                
                try:
                    response = self.make_request(search_url, params=params)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_results = self.parse_search_results(soup, artist_name)
                    
                    if page_results:
                        self.logger.debug(f"URL {search_url} - Página {page+1}: {len(page_results)} resultados")
                        break  # Si encontramos resultados, no probar otras URLs
                        
                except Exception as e:
                    self.logger.debug(f"Error en {search_url}: {e}")
                    continue
            
            if page_results:
                results.extend(page_results)
            else:
                # Si no hay resultados en esta página, parar
                break
        
        self.logger.info(f"Total de torrents encontrados para {artist_name}: {len(results)}")
        return results

    def parse_search_results(self, soup, artist_name):
        """Parsea los resultados de búsqueda de RuTracker"""
        results = []
        
        # Buscar diferentes tipos de tablas de resultados
        possible_tables = [
            soup.find('table', {'id': 'tor-tbl'}),
            soup.find('table', {'class': 'forumline'}),
            soup.find('table', class_=lambda x: x and 'tracker' in x),
            soup.find('table')  # Fallback a cualquier tabla
        ]
        
        results_table = None
        for table in possible_tables:
            if table and table.find_all('tr'):
                results_table = table
                break
        
        if not results_table:
            self.logger.debug("No se encontró tabla de resultados")
            return results
        
        rows = results_table.find_all('tr')
        if len(rows) <= 1:  # Solo header o vacío
            return results
            
        # Saltar header(s)
        data_rows = rows[1:] if len(rows) > 1 else rows
        
        for row in data_rows:
            try:
                result = self.parse_torrent_row(row, artist_name)
                if result:
                    results.append(result)
            except Exception as e:
                self.logger.debug(f"Error parseando fila: {e}")
                continue
        
        return results

    def parse_torrent_row(self, row, artist_name):
        """Parsea una fila individual de torrent"""
        cells = row.find_all('td')
        if len(cells) < 3:  # Mínimo necesario
            return None
        
        try:
            # Buscar el enlace del título en diferentes posiciones
            title_link = None
            title_cell = None
            
            # Buscar en diferentes celdas
            for i, cell in enumerate(cells):
                link = cell.find('a', href=True)
                if link and ('viewtopic.php' in link.get('href', '') or 't=' in link.get('href', '')):
                    title_link = link
                    title_cell = cell
                    break
            
            if not title_link:
                return None
            
            torrent_id = self.extract_torrent_id(title_link.get('href', ''))
            if not torrent_id:
                return None
            
            title = title_link.get_text(strip=True)
            
            # Verificar si el título contiene el nombre del artista
            if not self.title_matches_artist(title, artist_name):
                return None
            
            # Extraer información adicional de las celdas
            size_bytes = 0
            seeders = 0
            leechers = 0
            
            # Buscar size, seeders, leechers en las celdas
            for cell in cells:
                cell_text = cell.get_text(strip=True)
                
                # Intentar identificar tamaño
                if any(unit in cell_text.upper() for unit in ['MB', 'GB', 'TB', 'KB']):
                    size_bytes = self.parse_size(cell_text)
                
                # Intentar identificar seeders/leechers (números)
                if cell_text.isdigit():
                    num = int(cell_text)
                    if num > 0:
                        if seeders == 0:
                            seeders = num
                        elif leechers == 0:
                            leechers = num
            
            # Parsear título para extraer información del álbum
            album_info = self.parse_title_info(title)
            
            post_url = urljoin(self.rutracker_url, title_link.get('href'))
            download_url = f"{self.rutracker_url}/forum/dl.php?t={torrent_id}"
            
            return {
                'torrent_id': torrent_id,
                'title': title,
                'album_name': album_info.get('album', ''),
                'artist_name': album_info.get('artist', artist_name),
                'year': album_info.get('year', 0),
                'format': album_info.get('format', ''),
                'quality': album_info.get('quality', ''),
                'size': size_bytes,
                'seeders': seeders,
                'leechers': leechers,
                'post_url': post_url,
                'download_url': download_url
            }
            
        except Exception as e:
            self.logger.debug(f"Error parseando torrent: {e}")
            return None

    def extract_torrent_id(self, href):
        """Extrae el ID del torrent de la URL"""
        if not href:
            return None
        
        match = re.search(r't=(\d+)', href)
        return match.group(1) if match else None

    def title_matches_artist(self, title, artist_name):
        """Verifica si el título del torrent corresponde al artista buscado"""
        title_lower = title.lower()
        artist_lower = artist_name.lower()
        
        # Búsqueda simple por contención
        return artist_lower in title_lower

    def parse_size(self, size_text):
        """Convierte el texto de tamaño a bytes"""
        if not size_text:
            return 0
        
        # Remover espacios y convertir a mayúsculas
        size_text = size_text.strip().upper()
        
        # Buscar número y unidad
        match = re.match(r'([\d.,]+)\s*([KMGT]?B)', size_text)
        if not match:
            return 0
        
        number_str = match.group(1).replace(',', '.')
        unit = match.group(2)
        
        try:
            number = float(number_str)
        except ValueError:
            return 0
        
        # Convertir a bytes
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4
        }
        
        return int(number * multipliers.get(unit, 1))

    def parse_title_info(self, title):
        """Extrae información del álbum desde el título del torrent"""
        info = {
            'artist': '',
            'album': '',
            'year': 0,
            'format': '',
            'quality': ''
        }
        
        # Patrones comunes en RuTracker
        # Formato típico: "Artist - Album (Year) [Format/Quality]"
        
        # Extraer año
        year_match = re.search(r'\((\d{4})\)', title)
        if year_match:
            info['year'] = int(year_match.group(1))
        
        # Extraer formato y calidad
        format_match = re.search(r'\[([^\]]+)\]', title)
        if format_match:
            format_info = format_match.group(1)
            info['format'] = format_info
            
            # Identificar calidad específica
            if 'FLAC' in format_info.upper():
                info['quality'] = 'FLAC'
            elif 'MP3' in format_info.upper():
                info['quality'] = 'MP3'
            elif 'APE' in format_info.upper():
                info['quality'] = 'APE'
        
        # Extraer artista y álbum (antes del año)
        title_clean = re.sub(r'\s*\(\d{4}\).*', '', title)
        if ' - ' in title_clean:
            parts = title_clean.split(' - ', 1)
            info['artist'] = parts[0].strip()
            info['album'] = parts[1].strip()
        else:
            info['album'] = title_clean.strip()
        
        return info

    def find_album_and_mb_discography_id(self, conn, artist_id, album_name, year=None):
        """Busca el album_id y mb_discography_id correspondientes en la base de datos solo por nombre"""
        if not album_name:
            return None, None
        
        # Buscar primero en musicbrainz_discography por coincidencia exacta
        query = """
        SELECT md.id, md.album_id 
        FROM musicbrainz_discography md
        WHERE md.artist_id = ? AND LOWER(md.title) = LOWER(?)
        """
        cursor = conn.execute(query, (artist_id, album_name))
        result = cursor.fetchone()
        
        if result:
            mb_discography_id, album_id = result
            return album_id, mb_discography_id
        
        # Buscar por coincidencia aproximada (contiene el nombre)
        query = """
        SELECT md.id, md.album_id 
        FROM musicbrainz_discography md
        WHERE md.artist_id = ? AND LOWER(md.title) LIKE LOWER(?)
        ORDER BY LENGTH(md.title) ASC
        LIMIT 1
        """
        cursor = conn.execute(query, (artist_id, f'%{album_name}%'))
        result = cursor.fetchone()
        
        if result:
            mb_discography_id, album_id = result
            return album_id, mb_discography_id
        
        # Buscar coincidencia inversa (el nombre del torrent contiene el título del álbum)
        query = """
        SELECT md.id, md.album_id 
        FROM musicbrainz_discography md
        WHERE md.artist_id = ? AND LOWER(?) LIKE LOWER('%' || md.title || '%')
        ORDER BY LENGTH(md.title) DESC
        LIMIT 1
        """
        cursor = conn.execute(query, (artist_id, album_name))
        result = cursor.fetchone()
        
        if result:
            mb_discography_id, album_id = result
            return album_id, mb_discography_id
        
        # Si no se encuentra en musicbrainz_discography, buscar solo en albums
        album_id = self.find_album_id_fallback(conn, artist_id, album_name)
        return album_id, None

    def find_album_id_fallback(self, conn, artist_id, album_name):
        """Busca el album_id en la tabla albums como fallback solo por nombre"""
        if not album_name:
            return None
        
        # Buscar por nombre exacto
        query = """
        SELECT id FROM albums 
        WHERE artist_id = ? AND LOWER(name) = LOWER(?)
        """
        cursor = conn.execute(query, (artist_id, album_name))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Buscar por nombre similar (contiene)
        query = """
        SELECT id FROM albums 
        WHERE artist_id = ? AND LOWER(name) LIKE LOWER(?)
        ORDER BY LENGTH(name) ASC
        LIMIT 1
        """
        cursor = conn.execute(query, (artist_id, f'%{album_name}%'))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Buscar coincidencia inversa
        query = """
        SELECT id FROM albums 
        WHERE artist_id = ? AND LOWER(?) LIKE LOWER('%' || name || '%')
        ORDER BY LENGTH(name) DESC
        LIMIT 1
        """
        cursor = conn.execute(query, (artist_id, album_name))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        return None

    
    def get_artists_to_search(self):
        """Obtiene artistas para buscar según el modo de operación"""
        if self.config.get('update_mode', False):
            # Modo actualización: buscar artistas que ya tienen torrents para verificar disponibilidad
            query = """
            SELECT DISTINCT 
                a.id as artist_id,
                a.name as artist_name,
                COUNT(rt.id) as torrent_count,
                MAX(rt.last_checked) as last_checked
            FROM artists a
            JOIN rutracker_torrents rt ON a.id = rt.artist_id
            WHERE (rt.last_checked IS NULL OR rt.last_checked < datetime('now', '-7 days'))
                OR (rt.is_available = 0 AND rt.last_checked < datetime('now', '-3 days'))
            GROUP BY a.id, a.name
            ORDER BY last_checked ASC NULLS FIRST, torrent_count DESC
            """
            
            with self.get_db_connection() as conn:
                cursor = conn.execute(query)
                results = cursor.fetchall()
        else:
            # Modo inicial: buscar artistas según configuración
            if self.force_update:
                # Si force_update es True, procesar TODOS los artistas
                query = """
                SELECT DISTINCT 
                    a.id as artist_id,
                    a.name as artist_name,
                    COUNT(md.id) as album_count
                FROM artists a
                JOIN musicbrainz_discography md ON a.id = md.artist_id
                WHERE a.name IS NOT NULL AND a.name != ''
                GROUP BY a.id, a.name
                ORDER BY album_count DESC, a.name
                """
                
                with self.get_db_connection() as conn:
                    cursor = conn.execute(query)
                    results = cursor.fetchall()
            else:
                # Solo artistas SIN torrents registrados (comportamiento por defecto)
                query = """
                SELECT DISTINCT 
                    a.id as artist_id,
                    a.name as artist_name,
                    COUNT(md.id) as album_count
                FROM artists a
                JOIN musicbrainz_discography md ON a.id = md.artist_id
                LEFT JOIN rutracker_torrents rt ON a.id = rt.artist_id
                WHERE rt.id IS NULL 
                    AND a.name IS NOT NULL
                    AND a.name != ''
                GROUP BY a.id, a.name
                ORDER BY album_count DESC, a.name
                """
                
                with self.get_db_connection() as conn:
                    cursor = conn.execute(query)
                    results = cursor.fetchall()
        
        mode_text = "actualización" if self.config.get('update_mode', False) else ("búsqueda completa (todos los artistas)" if self.force_update else "búsqueda inicial (solo artistas sin torrents)")
        self.logger.info(f"Encontrados {len(results)} artistas para {mode_text}")
        return results


    


    def get_db_connection(self):
        """Obtener conexión a la base de datos"""
        try:
            # Buscar la base de datos en varias ubicaciones posibles
            db_paths = [
                self.db_path,
                Path(PROJECT_ROOT) / "db" / "sqlite" / "musica.sqlite",
                Path(PROJECT_ROOT) / ".content" / "database" / "musica.sqlite",
                Path(PROJECT_ROOT) / "music.db"
            ]
            
            for db_path in db_paths:
                if os.path.exists(str(db_path)):
                    return sqlite3.connect(str(db_path))
            
            print(f"Base de datos no encontrada en ninguna ubicación")
            return None
        except Exception as e:
            print(f"Error conectando a la base de datos: {str(e)}")
            return None

    
    def save_torrent_data(self, artist_id, artist_name, torrent_results):
        """Guarda los datos de torrents encontrados con gestión de duplicados mejorada"""
        if not torrent_results:
            return 0
            
        saved_count = 0
        updated_count = 0
        
        with self.get_db_connection() as conn:
            for torrent in torrent_results:
                # Verificar si el torrent ya existe PARA ESTE ARTISTA específico
                check_sql = """
                SELECT id, is_available, artist_id 
                FROM rutracker_torrents 
                WHERE torrent_id = ? AND artist_id = ?
                """
                cursor = conn.execute(check_sql, (torrent['torrent_id'], artist_id))
                existing = cursor.fetchone()
                
                # Buscar album_id y mb_discography_id solo por nombre
                album_id, mb_discography_id = self.find_album_and_mb_discography_id(
                    conn, artist_id, torrent['album_name']
                )
                
                if existing:
                    # Actualizar torrent existente SOLO para este artista
                    existing_id, was_available, existing_artist_id = existing
                    update_sql = """
                    UPDATE rutracker_torrents SET
                        album_id = ?, mb_discography_id = ?, album_name = ?,
                        torrent_title = ?, post_url = ?, download_url = ?,
                        format = ?, quality = ?, size = ?, seeders = ?, 
                        leechers = ?, year = ?, is_available = 1,
                        last_checked = CURRENT_TIMESTAMP, last_updated = CURRENT_TIMESTAMP,
                        times_unavailable = 0
                    WHERE id = ?
                    """
                    
                    values = (
                        album_id, mb_discography_id, torrent['album_name'],
                        torrent['title'], torrent['post_url'], torrent['download_url'],
                        torrent['format'], torrent['quality'], torrent['size'],
                        torrent['seeders'], torrent['leechers'], torrent['year'],
                        existing_id
                    )
                    
                    conn.execute(update_sql, values)
                    updated_count += 1
                    
                    if not was_available:
                        self.logger.info(f"Torrent restaurado: {torrent['torrent_id']} - {artist_name}")
                    else:
                        self.logger.debug(f"Torrent actualizado: {torrent['torrent_id']} - {artist_name}")
                else:
                    # Verificar si el mismo torrent_id existe para OTRO artista
                    check_other_sql = """
                    SELECT id, artist_name 
                    FROM rutracker_torrents 
                    WHERE torrent_id = ? AND artist_id != ?
                    """
                    cursor = conn.execute(check_other_sql, (torrent['torrent_id'], artist_id))
                    other_artist = cursor.fetchone()
                    
                    if other_artist:
                        # El torrent existe para otro artista, crear entrada duplicada con sufijo
                        new_torrent_id = f"{torrent['torrent_id']}_{artist_id}"
                        self.logger.debug(f"Torrent {torrent['torrent_id']} ya existe para {other_artist[1]}, creando entrada para {artist_name} con ID {new_torrent_id}")
                        torrent_id_to_use = new_torrent_id
                    else:
                        torrent_id_to_use = torrent['torrent_id']
                    
                    # Insertar nuevo torrent
                    insert_sql = """
                    INSERT INTO rutracker_torrents (
                        artist_id, album_id, mb_discography_id, artist_name, album_name,
                        torrent_title, torrent_id, post_url, download_url,
                        format, quality, size, seeders, leechers, year,
                        is_available, last_checked, last_updated, first_found,
                        times_unavailable
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)
                    """
                    
                    values = (
                        artist_id, album_id, mb_discography_id, artist_name, torrent['album_name'],
                        torrent['title'], torrent_id_to_use, 
                        torrent['post_url'], torrent['download_url'],
                        torrent['format'], torrent['quality'], torrent['size'],
                        torrent['seeders'], torrent['leechers'], torrent['year']
                    )
                    
                    try:
                        conn.execute(insert_sql, values)
                        saved_count += 1
                        if mb_discography_id:
                            self.logger.debug(f"Nuevo torrent guardado con MB ID {mb_discography_id}: {torrent_id_to_use} - {artist_name} - {torrent['album_name']}")
                        else:
                            self.logger.debug(f"Nuevo torrent guardado sin MB match: {torrent_id_to_use} - {artist_name} - {torrent['album_name']}")
                    except sqlite3.Error as e:
                        self.logger.error(f"Error al guardar torrent {torrent_id_to_use}: {e}")
                            
            conn.commit()
                    
        if saved_count > 0 or updated_count > 0:
            self.logger.info(f"Guardados: {saved_count} nuevos, {updated_count} actualizados para {artist_name}")
        
        return saved_count + updated_count

    def verify_torrent_availability(self, torrent_data):
        """Verifica si un torrent específico sigue disponible - mejorado para evitar conflicts"""
        torrent_id = torrent_data.get('torrent_id')
        post_url = torrent_data.get('post_url')
        
        if not post_url:
            return False
        
        try:
            response = self.make_request(post_url)
            
            # Verificar si la página existe y no está eliminada
            unavailable_indicators = [
                'тема удалена',
                'topic deleted',
                'не найдена',
                'not found',
                '404',
                'topic does not exist'
            ]
            
            content_lower = response.text.lower()
            if any(indicator in content_lower for indicator in unavailable_indicators):
                return False
            
            # Si llegamos aquí y el response es 200, probablemente está disponible
            return response.status_code == 200
                
        except Exception as e:
            self.logger.debug(f"Error verificando disponibilidad del torrent {torrent_id}: {e}")
            return False

    def update_torrent_availability(self):
        """Actualiza el estado de disponibilidad de torrents existentes - mejorado para preservar todos los artistas"""
        query = """
        SELECT id, torrent_id, post_url, artist_name, torrent_title, artist_id
        FROM rutracker_torrents
        WHERE last_checked < datetime('now', '-7 days')
            OR (is_available = 0 AND last_checked < datetime('now', '-3 days'))
        ORDER BY last_checked ASC NULLS FIRST
        LIMIT ?
        """
        
        check_limit = self.config.get('availability_check_limit', 100)
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(query, (check_limit,))
            torrents_to_check = cursor.fetchall()
        
        if not torrents_to_check:
            self.logger.info("No hay torrents que necesiten verificación de disponibilidad")
            return
        
        self.logger.info(f"Verificando disponibilidad de {len(torrents_to_check)} torrents")
        
        available_count = 0
        unavailable_count = 0
        
        for row_id, torrent_id, post_url, artist_name, title, artist_id in torrents_to_check:
            torrent_data = {'torrent_id': torrent_id, 'post_url': post_url}
            is_available = self.verify_torrent_availability(torrent_data)
            
            # Actualizar usando el ID único de la fila, no solo el torrent_id
            update_sql = """
            UPDATE rutracker_torrents 
            SET is_available = ?, 
                last_checked = CURRENT_TIMESTAMP,
                times_unavailable = CASE 
                    WHEN ? = 0 THEN times_unavailable + 1 
                    ELSE 0 
                END
            WHERE id = ?
            """
            
            with self.get_db_connection() as conn:
                conn.execute(update_sql, (is_available, is_available, row_id))
                conn.commit()
            
            if is_available:
                available_count += 1
                self.logger.debug(f"✓ {artist_name} - {title[:50]}...")
            else:
                unavailable_count += 1
                self.logger.debug(f"✗ {artist_name} - {title[:50]}...")
        
        self.logger.info(f"Verificación completada: {available_count} disponibles, {unavailable_count} no disponibles")

    def create_rutracker_torrents_table(self):
        """Crea la tabla para almacenar información de torrents de RuTracker - mejorada para manejar duplicados"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS rutracker_torrents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER,
            album_id INTEGER,
            mb_discography_id INTEGER,
            artist_name TEXT,
            album_name TEXT,
            torrent_title TEXT,
            torrent_id TEXT,
            post_url TEXT,
            download_url TEXT,
            format TEXT,
            quality TEXT,
            size INTEGER,
            seeders INTEGER,
            leechers INTEGER,
            year INTEGER,
            is_available BOOLEAN DEFAULT 1,
            last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            first_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            times_unavailable INTEGER DEFAULT 0,
            FOREIGN KEY (artist_id) REFERENCES artists (id),
            FOREIGN KEY (album_id) REFERENCES albums (id),
            FOREIGN KEY (mb_discography_id) REFERENCES musicbrainz_discography (id),
            UNIQUE(torrent_id, artist_id)
        )
        """
        
        # Verificar si la tabla ya existe y necesita modificaciones
        with self.get_db_connection() as conn:
            # Verificar si la tabla existe
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rutracker_torrents'")
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # Verificar la estructura actual
                cursor = conn.execute("PRAGMA table_info(rutracker_torrents)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Verificar si necesita la columna mb_discography_id
                if 'mb_discography_id' not in columns:
                    conn.execute("ALTER TABLE rutracker_torrents ADD COLUMN mb_discography_id INTEGER")
                    self.logger.info("Columna mb_discography_id agregada a rutracker_torrents")
                
                # Verificar constraint UNIQUE actual
                cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='rutracker_torrents'")
                table_sql = cursor.fetchone()[0]
                
                if 'UNIQUE(torrent_id, artist_id)' not in table_sql and 'UNIQUE(torrent_id)' in table_sql:
                    # Necesitamos recrear la tabla para cambiar el constraint
                    self.logger.info("Recreando tabla para cambiar constraint UNIQUE...")
                    
                    # Crear tabla temporal con nueva estructura
                    conn.execute("""
                    CREATE TABLE rutracker_torrents_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        artist_id INTEGER,
                        album_id INTEGER,
                        mb_discography_id INTEGER,
                        artist_name TEXT,
                        album_name TEXT,
                        torrent_title TEXT,
                        torrent_id TEXT,
                        post_url TEXT,
                        download_url TEXT,
                        format TEXT,
                        quality TEXT,
                        size INTEGER,
                        seeders INTEGER,
                        leechers INTEGER,
                        year INTEGER,
                        is_available BOOLEAN DEFAULT 1,
                        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        first_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        times_unavailable INTEGER DEFAULT 0,
                        FOREIGN KEY (artist_id) REFERENCES artists (id),
                        FOREIGN KEY (album_id) REFERENCES albums (id),
                        FOREIGN KEY (mb_discography_id) REFERENCES musicbrainz_discography (id),
                        UNIQUE(torrent_id, artist_id)
                    )
                    """)
                    
                    # Copiar datos existentes
                    conn.execute("""
                    INSERT INTO rutracker_torrents_new 
                    SELECT * FROM rutracker_torrents
                    """)
                    
                    # Reemplazar tabla
                    conn.execute("DROP TABLE rutracker_torrents")
                    conn.execute("ALTER TABLE rutracker_torrents_new RENAME TO rutracker_torrents")
                    
                    self.logger.info("Tabla recreada con constraint UNIQUE(torrent_id, artist_id)")
            else:
                # Crear tabla nueva
                conn.execute(create_table_sql)
                self.logger.info("Tabla rutracker_torrents creada con constraint UNIQUE(torrent_id, artist_id)")
            
            # Crear índices para mejorar performance
            create_indices_sql = [
                "CREATE INDEX IF NOT EXISTS idx_rutracker_artist_id ON rutracker_torrents(artist_id)",
                "CREATE INDEX IF NOT EXISTS idx_rutracker_album_id ON rutracker_torrents(album_id)",
                "CREATE INDEX IF NOT EXISTS idx_rutracker_mb_discography_id ON rutracker_torrents(mb_discography_id)",
                "CREATE INDEX IF NOT EXISTS idx_rutracker_torrent_id ON rutracker_torrents(torrent_id)",
                "CREATE INDEX IF NOT EXISTS idx_rutracker_available ON rutracker_torrents(is_available)",
                "CREATE INDEX IF NOT EXISTS idx_rutracker_last_checked ON rutracker_torrents(last_checked)",
                "CREATE INDEX IF NOT EXISTS idx_rutracker_artist_torrent ON rutracker_torrents(artist_id, torrent_id)"
            ]
            
            for index_sql in create_indices_sql:
                conn.execute(index_sql)
            
            conn.commit()
            self.logger.info("Tabla rutracker_torrents verificada con índices optimizados")

    def get_statistics(self):
        """Obtiene estadísticas detalladas de la tabla rutracker_torrents - mejoradas para múltiples artistas"""
        with self.get_db_connection() as conn:
            stats_query = """
            SELECT 
                COUNT(*) as total_torrents,
                COUNT(CASE WHEN is_available = 1 THEN 1 END) as available_torrents,
                COUNT(CASE WHEN is_available = 0 THEN 1 END) as unavailable_torrents,
                COUNT(DISTINCT artist_id) as unique_artists,
                COUNT(DISTINCT album_id) as unique_albums,
                COUNT(DISTINCT mb_discography_id) as unique_mb_discography,
                COUNT(CASE WHEN mb_discography_id IS NOT NULL THEN 1 END) as torrents_with_mb_match,
                AVG(CASE WHEN is_available = 1 THEN seeders END) as avg_seeders_available,
                COUNT(CASE WHEN quality LIKE '%FLAC%' AND is_available = 1 THEN 1 END) as flac_available,
                COUNT(CASE WHEN quality LIKE '%MP3%' AND is_available = 1 THEN 1 END) as mp3_available,
                MIN(first_found) as oldest_torrent,
                MAX(last_updated) as newest_torrent,
                COUNT(DISTINCT torrent_id) as unique_torrent_ids,
                COUNT(*) - COUNT(DISTINCT torrent_id) as duplicate_torrent_ids
            FROM rutracker_torrents
            """
            cursor = conn.execute(stats_query)
            stats = cursor.fetchone()
            
            # Top artistas con más torrents
            top_artists_query = """
            SELECT artist_name, COUNT(*) as torrent_count, 
                COUNT(CASE WHEN is_available = 1 THEN 1 END) as available_count
            FROM rutracker_torrents 
            GROUP BY artist_id, artist_name
            ORDER BY torrent_count DESC
            LIMIT 10
            """
            cursor = conn.execute(top_artists_query)
            top_artists = cursor.fetchall()
            
            # Estadísticas por formato
            format_query = """
            SELECT quality, COUNT(*) as count, AVG(seeders) as avg_seeders,
                COUNT(DISTINCT artist_id) as artists_count
            FROM rutracker_torrents 
            WHERE is_available = 1 AND quality IS NOT NULL
            GROUP BY quality
            ORDER BY count DESC
            """
            cursor = conn.execute(format_query)
            format_stats = cursor.fetchall()
            
        self.logger.info("=== Estadísticas de RuTracker Torrents ===")
        self.logger.info(f"Total de torrents: {stats[0]}")
        self.logger.info(f"Torrents únicos (por ID): {stats[12]}")
        self.logger.info(f"Torrents duplicados (mismo ID, diferentes artistas): {stats[13]}")
        self.logger.info(f"Torrents disponibles: {stats[1]}")
        self.logger.info(f"Torrents no disponibles: {stats[2]}")
        self.logger.info(f"Artistas únicos: {stats[3]}")
        self.logger.info(f"Álbumes únicos: {stats[4]}")
        self.logger.info(f"Registros MB únicos: {stats[5]}")
        self.logger.info(f"Torrents con coincidencia MB: {stats[6]} ({(stats[6]/stats[0]*100):.1f}%)" if stats[0] > 0 else "Torrents con coincidencia MB: 0")
        self.logger.info(f"Promedio de seeders (disponibles): {stats[7]:.2f}" if stats[7] else "Promedio de seeders: 0")
        self.logger.info(f"Torrents FLAC disponibles: {stats[8]}")
        self.logger.info(f"Torrents MP3 disponibles: {stats[9]}")
        self.logger.info(f"Torrent más antiguo: {stats[10]}")
        self.logger.info(f"Última actualización: {stats[11]}")
        
        if top_artists:
            self.logger.info("\n=== Top 10 artistas con más torrents ===")
            for artist_name, total, available in top_artists:
                self.logger.info(f"{artist_name}: {total} torrents ({available} disponibles)")
        
        if format_stats:
            self.logger.info("\n=== Distribución por formato (disponibles) ===")
            for quality, count, avg_seeders, artists_count in format_stats[:10]:
                self.logger.info(f"{quality}: {count} torrents de {artists_count} artistas (avg seeders: {avg_seeders:.1f})")


    def cleanup_old_unavailable_torrents(self):
        """Elimina torrents que han estado no disponibles durante mucho tiempo"""
        max_unavailable_days = self.config.get('max_unavailable_days', 30)
        max_unavailable_times = self.config.get('max_unavailable_times', 5)
        
        cleanup_sql = """
        DELETE FROM rutracker_torrents 
        WHERE is_available = 0 
            AND (
                last_checked < datetime('now', '-{} days')
                OR times_unavailable >= ?
            )
        """.format(max_unavailable_days)
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(cleanup_sql, (max_unavailable_times,))
            deleted_count = cursor.rowcount
            conn.commit()
        
        if deleted_count > 0:
            self.logger.info(f"Eliminados {deleted_count} torrents obsoletos")


    def find_album_id(self, conn, artist_id, album_name, year):
        """Busca el album_id correspondiente en la base de datos"""
        if not album_name:
            return None
        
        # Buscar por nombre exacto
        query = """
        SELECT id FROM albums 
        WHERE artist_id = ? AND LOWER(name) = LOWER(?)
        """
        cursor = conn.execute(query, (artist_id, album_name))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Buscar por nombre similar y año
        if year > 0:
            query = """
            SELECT id FROM albums 
            WHERE artist_id = ? AND LOWER(name) LIKE LOWER(?) AND (year = ? OR year LIKE ?)
            """
            cursor = conn.execute(query, (artist_id, f'%{album_name}%', str(year), f'%{year}%'))
            result = cursor.fetchone()
            
            if result:
                return result[0]
        
        return None

    def process_artists(self):
        """Procesa artistas para buscar sus torrents en RuTracker"""
        # Determinar modo de operación
        update_mode = self.config.get('update_mode', False)
        
        if update_mode:
            self.logger.info("Modo actualización: verificando torrents existentes y buscando nuevos")
            # Primero verificar disponibilidad de torrents existentes
            self.update_torrent_availability()
            # Limpiar torrents obsoletos
            self.cleanup_old_unavailable_torrents()
        
        artists = self.get_artists_to_search()
        
        if not artists:
            self.logger.info("No hay artistas para procesar")
            return
            
        # Aplicar límite si está configurado
        if self.limit > 0:
            artists = artists[:self.limit]
            self.logger.info(f"Limitando procesamiento a {self.limit} artistas")
            
        total_found = 0
        processed = 0
        
        for artist_data in artists:
            if update_mode:
                artist_id, artist_name, torrent_count, last_checked = artist_data
                self.logger.info(f"Actualizando artista: {artist_name} ({torrent_count} torrents, último check: {last_checked})")
            else:
                artist_id, artist_name, album_count = artist_data
                self.logger.info(f"Procesando artista: {artist_name} ({album_count} álbumes en DB)")
            
            # Buscar torrents del artista en RuTracker
            torrent_results = self.search_artist_albums(artist_name)
            
            if torrent_results:
                saved = self.save_torrent_data(artist_id, artist_name, torrent_results)
                total_found += saved
                self.logger.info(f"Procesado {artist_name}: {len(torrent_results)} torrents encontrados, {saved} procesados")
            else:
                self.logger.info(f"No se encontraron torrents para {artist_name}")
            
            processed += 1
            
            if processed % 10 == 0:
                self.logger.info(f"Progreso: {processed}/{len(artists)} artistas procesados, {total_found} torrents procesados")
                    
        self.logger.info(f"Proceso completado: {processed} artistas procesados, {total_found} torrents procesados en total")

 

    def configure_update_mode(self):
        """Configura el módulo para modo actualización si ya existen datos"""
        with self.get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM rutracker_torrents")
            existing_count = cursor.fetchone()[0]
            
            # Contar artistas con torrents vs artistas totales
            cursor = conn.execute("""
                SELECT 
                    COUNT(DISTINCT rt.artist_id) as artists_with_torrents,
                    (SELECT COUNT(*) FROM artists WHERE name IS NOT NULL AND name != '') as total_artists
                FROM rutracker_torrents rt
            """)
            artists_with_torrents, total_artists = cursor.fetchone()
        
        # Si force_update está activo, NUNCA usar modo actualización
        if self.force_update:
            self.config['update_mode'] = False
            self.logger.info(f"FORCE_UPDATE activo: Procesando TODOS los {total_artists} artistas (modo búsqueda completa)")
            return
        
        # Si force_initial_mode está activo, forzar modo inicial
        if self.config.get('force_initial_mode', False):
            self.config['update_mode'] = False
            remaining_artists = total_artists - artists_with_torrents
            self.logger.info(f"FORCE_INITIAL_MODE activo: Procesando {remaining_artists} artistas restantes de {total_artists} totales")
            return
        
        # Determinar modo automáticamente
        if existing_count > 0:
            self.config['update_mode'] = True
            self.logger.info(f"Detectados {existing_count} torrents existentes para {artists_with_torrents}/{total_artists} artistas. Activando modo actualización.")
        else:
            self.config['update_mode'] = False
            self.logger.info(f"No hay torrents existentes. Activando modo búsqueda inicial para {total_artists} artistas.")


    def get_progress_summary(self):
        """Obtiene un resumen del progreso actual"""
        with self.get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(DISTINCT a.id) as total_artists,
                    COUNT(DISTINCT rt.artist_id) as artists_with_torrents,
                    COUNT(rt.id) as total_torrents,
                    COUNT(CASE WHEN rt.is_available = 1 THEN 1 END) as available_torrents
                FROM artists a
                LEFT JOIN rutracker_torrents rt ON a.id = rt.artist_id
                WHERE a.name IS NOT NULL AND a.name != ''
            """)
            total_artists, artists_with_torrents, total_torrents, available_torrents = cursor.fetchone()
        
        if total_artists > 0:
            percentage = (artists_with_torrents / total_artists) * 100
            self.logger.info(f"Progreso general: {artists_with_torrents}/{total_artists} artistas procesados ({percentage:.1f}%)")
            self.logger.info(f"Total de torrents: {total_torrents} ({available_torrents} disponibles)")
        
        return {
            'total_artists': total_artists,
            'artists_with_torrents': artists_with_torrents,
            'total_torrents': total_torrents,
            'available_torrents': available_torrents,
            'percentage_complete': percentage if total_artists > 0 else 0
        }


def main(config=None):
    """Función principal del script"""
    try:
        module = RuTrackerModule(config)
        
        # Determinar el método de acceso
        if module.use_jackett:
            print("Modo Jackett configurado")
            if not module.jackett_url or not module.jackett_api_key:
                print("Error: Faltan credenciales de Jackett")
                print("Configura 'jackett_url' y 'jackett_api_key'")
                return 1
        else:
            print("Modo directo configurado")
            # Verificar credenciales para acceso directo
            if not module.username or not module.password:
                print("Error: Se requieren credenciales de RuTracker para acceso directo")
                print("Configura 'rutracker_username' y 'rutracker_password'")
                print("O configura 'use_jackett: true' con credenciales de Jackett")
                return 1
            
            # Verificar disponibilidad del sitio antes de continuar
            print("Verificando disponibilidad de RuTracker...")
            if not module.check_site_availability():
                print("Error: RuTracker no está disponible actualmente")
                print("Posibles causas:")
                print("- El sitio está bloqueado en tu región")
                print("- Problemas temporales del servidor")
                print("- Necesitas usar VPN o proxy")
                
                # Ofrecer fallback a Jackett si está configurado
                if module.jackett_url and module.jackett_api_key:
                    print("\nIntentando usar Jackett como alternativa...")
                    module.use_jackett = True
                else:
                    print("\nConsideraciones:")
                    print("1. Configura un proxy en la configuración")
                    print("2. Usa Jackett como intermediario")
                    print("3. Usa VPN")
                    return 1
            
        # Crear tabla si no existe
        module.create_rutracker_torrents_table()
        
        # Mostrar progreso inicial
        print("\n=== Estado inicial ===")
        module.get_progress_summary()
        
        # Configurar modo de operación automáticamente
        module.configure_update_mode()
        
        # Procesar artistas
        module.process_artists()
        
        # Mostrar progreso final
        print("\n=== Estado final ===")
        module.get_progress_summary()
        
        # Mostrar estadísticas
        module.get_statistics()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario")
        return 1
    except Exception as e:
        print(f"Error en el proceso: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Busca torrents en RuTracker')
    parser.add_argument('--config', type=str, help='Archivo de configuración JSON')
    parser.add_argument('--username', type=str, help='Usuario de RuTracker')
    parser.add_argument('--password', type=str, help='Contraseña de RuTracker')
    parser.add_argument('--jackett-url', type=str, help='URL de Jackett')
    parser.add_argument('--jackett-api-key', type=str, help='API Key de Jackett')
    parser.add_argument('--use-jackett', action='store_true', help='Usar Jackett en lugar de acceso directo')
    parser.add_argument('--limit', type=int, default=0, help='Límite de artistas a procesar')
    parser.add_argument('--force-update', action='store_true', help='Forzar actualización de existentes')
    parser.add_argument('--proxy-http', type=str, help='Proxy HTTP (ej: socks5://127.0.0.1:1080)')
    parser.add_argument('--proxy-https', type=str, help='Proxy HTTPS (ej: socks5://127.0.0.1:1080)')
    
    args = parser.parse_args()
    
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Sobrescribir con argumentos de línea de comandos
    if args.username:
        config['rutracker_username'] = args.username
    if args.password:
        config['rutracker_password'] = args.password
    if args.jackett_url:
        config['jackett_url'] = args.jackett_url
    if args.jackett_api_key:
        config['jackett_api_key'] = args.jackett_api_key
    if args.use_jackett:
        config['use_jackett'] = True
    if args.limit:
        config['limit'] = args.limit
    if args.force_update:
        config['force_update'] = True
    
    # Configurar proxy si se proporciona
    if args.proxy_http or args.proxy_https:
        config['proxy'] = {}
        if args.proxy_http:
            config['proxy']['http'] = args.proxy_http
        if args.proxy_https:
            config['proxy']['https'] = args.proxy_https
        
    sys.exit(main(config))