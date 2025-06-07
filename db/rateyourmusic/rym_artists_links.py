#!/usr/bin/env python3
"""
Script para buscar URLs de RateYourMusic para artistas usando SearXNG
Compatible con db_creator.py
"""

import requests
import sqlite3
import time
import re
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variables globales que serán configuradas por db_creator
CONFIG = {}

class RateYourMusicSearcher:
    def __init__(self, db_path, searxng_url, delay=5.0, max_retries=3):
        """
        Inicializa el buscador de RateYourMusic
        
        Args:
            db_path: Ruta a la base de datos SQLite
            searxng_url: URL base de la instancia SearXNG (ej: "http://localhost:8080")
            delay: Retraso entre búsquedas en segundos (aumentado por defecto)
            max_retries: Máximo número de reintentos para rate limiting
        """
        self.db_path = Path(db_path)
        self.create_rym_artists_table()
        self.searxng_url = searxng_url.rstrip('/')
        self.delay = delay
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Estadísticas
        self.stats = {
            'total_artists': 0,
            'already_have_rym': 0,
            'searches_performed': 0,
            'urls_found': 0,
            'urls_updated': 0,
            'errors': 0,
            'rate_limits': 0
        }


    def create_rym_artists_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Eliminar la tabla si existe y crearla de nuevo
        cursor.execute("DROP TABLE IF EXISTS rym_artists")
        
        cursor.execute("""
            CREATE TABLE rym_artists (
                id INTEGER PRIMARY KEY,
                artist_id INTEGER,
                artist_name TEXT NOT NULL,
                rym_url TEXT,
                found_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP,
                status TEXT DEFAULT 'found',
                album_count INTEGER DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                avg_rating REAL DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()

    def get_artists_without_rym_url(self, limit=None):
        """Obtiene artistas que no tienen URL de RateYourMusic"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT id, name 
        FROM artists 
        WHERE (rateyourmusic_url IS NULL OR rateyourmusic_url = '')
        AND name IS NOT NULL 
        AND name != ''
        ORDER BY id
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        cursor.execute(query)
        artists = cursor.fetchall()
        conn.close()
        
        return artists


    def get_artists_with_rym_url_missing_entry(self):
        """Obtiene artistas que tienen URL de RateYourMusic pero no entrada en rym_artists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT a.id, a.name, a.rateyourmusic_url
        FROM artists a
        LEFT JOIN rym_artists ra ON a.id = ra.artist_id
        WHERE a.rateyourmusic_url IS NOT NULL 
        AND a.rateyourmusic_url != ''
        AND ra.artist_id IS NULL
        ORDER BY a.id
        """
        
        cursor.execute(query)
        artists = cursor.fetchall()
        conn.close()
        
        return artists

    def create_rym_entry_for_existing_url(self, artist_id, artist_name, rym_url):
        """Crea entrada en rym_artists para un artista que ya tiene URL"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insertar en rym_artists
            cursor.execute(
                """
                INSERT INTO rym_artists (artist_id, artist_name, rym_url, found_date, status)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'found')
                """,
                (artist_id, artist_name, rym_url)
            )

            conn.commit()
            conn.close()
            
            logger.debug(f"Creada entrada en rym_artists para artista {artist_id}: {rym_url}")
            
        except sqlite3.Error as e:
            logger.error(f"Error creando entrada en rym_artists para artista {artist_id}: {e}")
            self.stats['errors'] += 1


    def search_artist_on_rym(self, artist_name):
        """
        Busca un artista en RateYourMusic usando SearXNG con mejor debugging y manejo de errores
        
        Returns:
            str or None: URL de RateYourMusic si se encuentra, None si no
        """
        max_retries = self.max_retries
        base_wait_time = 2
        
        for attempt in range(max_retries):
            try:
                # Construir query de búsqueda para RateYourMusic
                search_query = f"site:rateyourmusic.com {artist_name}"
                
                # Parámetros para SearXNG - cambiar a HTML para evitar problemas
                params = {
                    'q': search_query,
                    'format': 'html',  # Cambiar a HTML por defecto
                    'categories': 'general',
                    'engines': 'google,bing,duckduckgo'  # Especificar motores
                }
                
                # Headers más completos para evitar bloqueos
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                # Realizar búsqueda
                search_url = f"{self.searxng_url}/search"
                logger.debug(f"Buscando: {artist_name} (intento {attempt + 1}/{max_retries})")
                logger.debug(f"URL: {search_url}")
                logger.debug(f"Query: {search_query}")
                
                response = self.session.get(search_url, params=params, headers=headers, timeout=15)
                
                # Debug de la respuesta
                logger.debug(f"Status code: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                # Manejar rate limiting
                if response.status_code == 429:
                    wait_time = base_wait_time * (2 ** attempt)
                    logger.warning(f"Rate limit alcanzado para '{artist_name}'. Esperando {wait_time} segundos...")
                    self.stats['rate_limits'] += 1
                    time.sleep(wait_time)
                    continue
                
                # Manejar 403 Forbidden
                if response.status_code == 403:
                    logger.warning(f"Acceso prohibido (403) para '{artist_name}'. Probablemente bloqueado por headers.")
                    # Intentar con diferentes headers o sin parámetros específicos
                    simple_params = {'q': search_query}
                    simple_headers = {'User-Agent': 'Mozilla/5.0 (compatible; SearchBot/1.0)'}
                    
                    response = self.session.get(search_url, params=simple_params, headers=simple_headers, timeout=15)
                    logger.debug(f"Intento simplificado - Status code: {response.status_code}")
                    
                    if response.status_code != 200:
                        logger.warning(f"Sigue fallando después del intento simplificado para '{artist_name}'")
                        continue
                
                if response.status_code != 200:
                    logger.warning(f"Status code no exitoso: {response.status_code} para '{artist_name}'")
                    logger.debug(f"Response content: {response.text[:500]}...")
                    continue  # Cambiar return por continue para intentar de nuevo
                
                # Siempre parsear como HTML ya que cambiamos el formato
                rym_urls = self._parse_html_results(response.text, artist_name)
                
                if rym_urls:
                    logger.info(f"✓ Encontrado para '{artist_name}': {rym_urls}")
                    return rym_urls
                else:
                    logger.debug(f"✗ No encontrado para '{artist_name}' en intento {attempt + 1}")
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    wait_time = base_wait_time * (2 ** attempt)
                    logger.warning(f"Rate limit HTTP error para '{artist_name}'. Esperando {wait_time} segundos...")
                    self.stats['rate_limits'] += 1
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Error HTTP en la búsqueda para '{artist_name}': {e}")
                    self.stats['errors'] += 1
                    continue  # Continuar con el siguiente intento
            except requests.exceptions.RequestException as e:
                logger.error(f"Error en la búsqueda para '{artist_name}': {e}")
                self.stats['errors'] += 1
                if attempt < max_retries - 1:
                    time.sleep(base_wait_time)
                    continue
            except Exception as e:
                logger.error(f"Error inesperado buscando '{artist_name}': {e}")
                self.stats['errors'] += 1
                continue
        
        # Si llegamos aquí, agotamos todos los intentos
        logger.error(f"Máximo de intentos agotado para '{artist_name}'")
        self.stats['errors'] += 1
        return None

    def _parse_html_results(self, html_content, artist_name):
        """Parsea resultados HTML y extrae URLs de RateYourMusic"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Múltiples selectores para diferentes versiones de SearXNG
            result_selectors = [
                'article.result',
                'div.result',
                '.result',
                'article',
                'div[class*="result"]',
                'h3 a',  # Enlaces directos en títulos
                'a[href*="rateyourmusic.com"]'  # Enlaces directos a RYM
            ]
            
            rym_urls = []
            
            # Primero buscar enlaces directos a RateYourMusic
            direct_links = soup.find_all('a', href=True)
            for link in direct_links:
                url = link.get('href', '')
                if self.is_valid_rym_artist_url(url):
                    title_text = link.get_text() or ''
                    # Buscar texto del contexto (div padre, etc.)
                    parent_text = ''
                    parent = link.find_parent()
                    if parent:
                        parent_text = parent.get_text()
                    
                    combined_text = f"{title_text} {parent_text}"
                    
                    if self.artist_name_matches(artist_name, url, combined_text):
                        rym_urls.append(url)
                        logger.debug(f"URL directa válida encontrada: {url}")
            
            # Si no encontramos enlaces directos, buscar en resultados estructurados
            if not rym_urls:
                for selector in result_selectors:
                    results = soup.select(selector)
                    if not results:
                        continue
                        
                    logger.debug(f"Usando selector '{selector}', encontrados {len(results)} resultados")
                    
                    for result in results:
                        # Buscar enlaces en el resultado
                        links = result.find_all('a', href=True)
                        for link in links:
                            url = link.get('href', '')
                            text = result.get_text()
                            
                            logger.debug(f"Examinando URL: {url}")
                            
                            if self.is_valid_rym_artist_url(url):
                                if self.artist_name_matches(artist_name, url, text):
                                    rym_urls.append(url)
                                    logger.debug(f"URL válida encontrada en HTML: {url}")
                    
                    # Si encontramos URLs, no necesitamos probar otros selectores
                    if rym_urls:
                        break
            
            if rym_urls:
                best_url = self.select_best_rym_url(rym_urls, artist_name)
                logger.info(f"✓ Encontrado en HTML para '{artist_name}': {best_url}")
                return best_url
            else:
                logger.debug(f"No se encontraron URLs válidas en HTML para '{artist_name}'")
                return None
                
        except Exception as e:
            logger.error(f"Error parseando HTML para '{artist_name}': {e}")
            return None



    def is_valid_rym_artist_url(self, url):
        """Verifica si una URL es válida de RateYourMusic para artistas"""
        if not url or not isinstance(url, str):
            return False
            
        # Limpiar URL
        url = url.strip()
        
        # Debe ser de rateyourmusic.com
        if 'rateyourmusic.com' not in url.lower():
            return False
            
        # Patrones válidos para páginas de artistas
        artist_patterns = [
            r'rateyourmusic\.com/artist/',
            r'rateyourmusic\.com/artist\.php',
            r'rateyourmusic\.com/music/artist/',
        ]
        
        for pattern in artist_patterns:
            if re.search(pattern, url.lower()):
                return True
        
        # Excluir URLs que definitivamente NO son de artistas
        exclude_patterns = [
            r'/release/',
            r'/album/',
            r'/ep/',
            r'/single/',
            r'/chart/',
            r'/list/',
            r'/review/',
            r'/board/',
            r'/user/',
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, url.lower()):
                return False
                
        return False




    def artist_name_matches(self, search_name, url, result_text):
        """
        Verifica si el resultado corresponde al artista buscado con mejor lógica
        """
        search_name_clean = self.clean_artist_name(search_name)
        result_text_clean = self.clean_artist_name(result_text)
        url_clean = self.clean_artist_name(url)
        
        logger.debug(f"Comparando: '{search_name_clean}' vs '{result_text_clean[:100]}...'")
        
        # Verificación exacta (case insensitive)
        if search_name_clean.lower() in result_text_clean.lower():
            logger.debug("Match exacto en texto")
            return True
            
        # Verificación en URL
        if search_name_clean.lower() in url_clean.lower():
            logger.debug("Match exacto en URL")
            return True
        
        # Verificación por palabras (más flexible)
        search_words = set(word.lower() for word in search_name_clean.split() if len(word) > 2)
        result_words = set(word.lower() for word in result_text_clean.split())
        
        if search_words:
            matches = search_words.intersection(result_words)
            match_ratio = len(matches) / len(search_words)
            logger.debug(f"Match ratio: {match_ratio:.2f} ({matches})")
            
            # Relajar el criterio: 50% de las palabras deben coincidir
            if match_ratio >= 0.5:
                logger.debug("Match por palabras clave")
                return True
        
        return False

    def clean_artist_name(self, name):
        """Limpia el nombre del artista para comparación"""
        if not name:
            return ""
            
        # Remover caracteres especiales y normalizar
        cleaned = re.sub(r'[^\w\s]', ' ', str(name))
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def select_best_rym_url(self, urls, artist_name):
        """Selecciona la mejor URL de RateYourMusic de una lista"""
        if not urls:
            return None
            
        if len(urls) == 1:
            return urls[0]
            
        # Preferir URLs más simples (menos parámetros)
        urls_sorted = sorted(urls, key=lambda x: len(x))
        
        # Preferir URLs que contengan el nombre del artista
        artist_clean = self.clean_artist_name(artist_name).lower()
        for url in urls_sorted:
            if artist_clean in url.lower():
                return url
                
        return urls_sorted[0]

    def update_artist_rym_url(self, artist_id, rym_url):
        """Actualiza la URL de RateYourMusic en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Actualizar tabla artists
            cursor.execute(
                "UPDATE artists SET rateyourmusic_url = ? WHERE id = ?",
                (rym_url, artist_id)
            )
            
            # Obtener nombre del artista
            cursor.execute("SELECT name FROM artists WHERE id = ?", (artist_id,))
            result = cursor.fetchone()
            artist_name = result[0] if result else "Unknown"
            
            # Insertar en rym_artists
            cursor.execute(
                """
                INSERT INTO rym_artists (artist_id, artist_name, rym_url, found_date, status)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'found')
                """,
                (artist_id, artist_name, rym_url)
            )

            conn.commit()
            conn.close()
            
            self.stats['urls_updated'] += 1
            logger.debug(f"Actualizado artista {artist_id} con URL: {rym_url}")
            
        except sqlite3.Error as e:
            logger.error(f"Error actualizando base de datos para artista {artist_id}: {e}")
            self.stats['errors'] += 1

    def get_statistics(self):
        """Obtiene estadísticas del proceso"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM artists")
        self.stats['total_artists'] = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM artists WHERE rateyourmusic_url IS NOT NULL AND rateyourmusic_url != ''"
        )
        self.stats['already_have_rym'] = cursor.fetchone()[0]
        
        conn.close()

    def run_search(self, limit=None, skip_existing=True):
        """
        Ejecuta la búsqueda de URLs de RateYourMusic
        
        Args:
            limit: Límite de artistas a procesar (None para todos)
            skip_existing: Si saltar artistas que ya tienen URL
        """
        logger.info("=== Iniciando búsqueda de URLs de RateYourMusic ===")
        logger.info(f"Límite configurado: {limit}")
        logger.info(f"Skip existing: {skip_existing}")
        
        # Obtener estadísticas iniciales
        self.get_statistics()
        
        # NUEVO: Primero procesar artistas que ya tienen URL pero no entrada en rym_artists
        existing_artists = self.get_artists_with_rym_url_missing_entry()
        if existing_artists:
            logger.info(f"Encontrados {len(existing_artists)} artistas con URL existente sin entrada en rym_artists")
            for artist_id, artist_name, rym_url in existing_artists:
                logger.info(f"Creando entrada para: {artist_name}")
                self.create_rym_entry_for_existing_url(artist_id, artist_name, rym_url)
                self.stats['urls_found'] += 1
        
        # Obtener artistas sin URL de RYM
        artists = self.get_artists_without_rym_url(limit)
        
        if not artists:
            logger.info("No hay artistas sin URL de RateYourMusic para procesar")
            if existing_artists:
                logger.info("✅ Se procesaron entradas existentes correctamente")
            return
            
        logger.info(f"Procesando {len(artists)} artistas sin URL...")
        logger.info(f"Retraso entre búsquedas: {self.delay} segundos")
        logger.info(f"URL de SearXNG: {self.searxng_url}")
        
        for i, (artist_id, artist_name) in enumerate(artists, 1):
            try:
                logger.info(f"[{i}/{len(artists)}] Procesando: {artist_name}")
                
                # Buscar URL de RateYourMusic
                rym_url = self.search_artist_on_rym(artist_name)
                self.stats['searches_performed'] += 1
                
                if rym_url:
                    # Actualizar base de datos
                    self.update_artist_rym_url(artist_id, rym_url)
                    self.stats['urls_found'] += 1
                
                # Pausa entre búsquedas
                if i < len(artists):  # No pausar después del último
                    time.sleep(self.delay)
                    
            except KeyboardInterrupt:
                logger.info("\n⚠️ Proceso interrumpido por el usuario")
                break
            except Exception as e:
                logger.error(f"Error procesando artista {artist_name}: {e}")
                self.stats['errors'] += 1
                continue
        
        # Mostrar estadísticas finales
        self.show_final_stats()

    def show_final_stats(self):
        """Muestra estadísticas finales del proceso"""
        logger.info("\n=== Estadísticas Finales ===")
        logger.info(f"Total de artistas en BD: {self.stats['total_artists']}")
        logger.info(f"Ya tenían URL de RYM: {self.stats['already_have_rym']}")
        logger.info(f"Búsquedas realizadas: {self.stats['searches_performed']}")
        logger.info(f"URLs encontradas: {self.stats['urls_found']}")
        logger.info(f"URLs actualizadas en BD: {self.stats['urls_updated']}")
        logger.info(f"Rate limits encontrados: {self.stats['rate_limits']}")
        logger.info(f"Errores: {self.stats['errors']}")
        
        if self.stats['searches_performed'] > 0:
            success_rate = (self.stats['urls_found'] / self.stats['searches_performed']) * 100
            logger.info(f"Tasa de éxito: {success_rate:.1f}%")




# DEBUG
    def test_searxng_connection(self):
        """Prueba la conexión con SearXNG con debugging mejorado"""
        try:
            test_url = f"{self.searxng_url}/search"
            params = {
                'q': 'test rateyourmusic',
                'format': 'html',
                'categories': 'general'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            logger.info(f"Probando conexión con SearXNG: {self.searxng_url}")
            response = self.session.get(test_url, params=params, headers=headers, timeout=10)
            
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Headers de respuesta: {dict(list(response.headers.items())[:5])}")  # Primeros 5 headers
            
            if response.status_code == 200:
                # Verificar si hay contenido útil
                content_preview = response.text[:500]
                logger.info(f"✓ SearXNG responde correctamente. Preview: {content_preview[:100]}...")
                
                # Buscar indicadores de que SearXNG está funcionando
                if 'searx' in response.text.lower() or 'results' in response.text.lower():
                    logger.info("✓ Parece ser una respuesta válida de SearXNG")
                    return True
                else:
                    logger.warning("⚠️ La respuesta no parece ser de SearXNG")
                    return False
            elif response.status_code == 403:
                logger.error("✗ Error 403: Acceso prohibido. Posible problema de configuración o bloqueo.")
                logger.error("Sugerencias:")
                logger.error("1. Verificar que SearXNG permite búsquedas externas")
                logger.error("2. Revisar configuración de rate limiting")
                logger.error("3. Verificar que el puerto 8485 esté correcto")
                return False
            else:
                logger.error(f"✗ SearXNG error: {response.status_code}")
                logger.error(f"Response: {response.text[:200]}...")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error conectando con SearXNG: {e}")
            return False

    def test_single_search(self, artist_name="radiohead"):
        """Prueba una búsqueda individual para debugging"""
        logger.info(f"=== Prueba de búsqueda para: {artist_name} ===")
        
        # Probar conexión primero
        if not self.test_searxng_connection():
            return None
        
        # Realizar búsqueda de prueba
        result = self.search_artist_on_rym(artist_name)
        
        if result:
            logger.info(f"✓ Prueba exitosa: {result}")
        else:
            logger.warning(f"✗ No se encontró resultado para {artist_name}")
        
        return result
            
        # Limpiar URL
        url = url.strip()
        
        # Debe ser de rateyourmusic.com
        if 'rateyourmusic.com' not in url.lower():
            return False
            
        # Patrones válidos para páginas de artistas
        artist_patterns = [
            r'rateyourmusic\.com/artist/',
            r'rateyourmusic\.com/artist\.php',
            r'rateyourmusic\.com/music/artist/',
        ]
        
        for pattern in artist_patterns:
            if re.search(pattern, url.lower()):
                return True
        
        # Excluir URLs que definitivamente NO son de artistas
        exclude_patterns = [
            r'/release/',
            r'/album/',
            r'/ep/',
            r'/single/',
            r'/chart/',
            r'/list/',
            r'/review/',
            r'/board/',
            r'/user/',
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, url.lower()):
                return False
                
        return False


def main(config=None):
    """Función principal compatible con db_creator.py"""
    
    # Si no se pasa configuración como parámetro, usar la global CONFIG
    if config is None:
        global CONFIG
        config = CONFIG if CONFIG else {}
    
    # Configuración por defecto
    default_config = {
        'db_path': 'data/music.db',
        'searxng_url': 'https://searx.tiekoetter.com',
        'delay': 5.0,
        'max_retries': 3,
        'limit': None,
        'skip_existing': True,
        'log_level': 'INFO'
    }
    
    # Combinar configuración (config tiene prioridad sobre defaults)
    if config is None:
        final_config = default_config
        logger.info(f"Configuración predeterminada (editar json para personalizar): {final_config}")
    else:
        final_config = config
        logger.info(f"Configuración recibida: {config}")
    
    
    # Debug: mostrar configuración recibida
    
    # Configurar logging
    log_level = getattr(logging, final_config.get('log_level', 'INFO').upper())
    logging.getLogger().setLevel(log_level)
    
    try:
        # Validar configuración
        db_path = Path(final_config['db_path'])
        if not db_path.exists():
            logger.error(f"Base de datos no encontrada: {db_path}")
            return 1
            
        searxng_url = final_config['searxng_url']
        if not searxng_url:
            logger.error("URL de SearXNG no configurada")
            return 1
        
        # Crear instancia del buscador
        searcher = RateYourMusicSearcher(
            db_path=db_path,
            searxng_url=searxng_url,
            delay=final_config['delay'],
            max_retries=final_config.get('max_retries', 3)
        )
        
        # Ejecutar búsqueda
        searcher.run_search(
            limit=final_config.get('limit'),
            skip_existing=final_config.get('skip_existing', True)
        )
        
        logger.info("✅ Proceso completado exitosamente")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error en el proceso: {e}")
        return 1

