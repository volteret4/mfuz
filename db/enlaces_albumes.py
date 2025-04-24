import os
import sys
import argparse
import sqlite3
import time
import json
import requests
from urllib.parse import quote_plus
from datetime import datetime
from base_module import PROJECT_ROOT
import requests
from bs4 import BeautifulSoup
import re
import random
from playwright.sync_api import sync_playwright


class AlbumLinksManager():
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.db_path = config.get('db_path')
        self.missing_only = config.get('missing_only', False)
        self.user_agent = config.get('user_agent', 'MusicLibraryManager/1.0')
        self.delay_between_requests = config.get('delay_between_requests', 1)
        
        # Asegurarse de que tenemos una base de datos válida
        if not self.db_path or not os.path.exists(self.db_path):
            raise ValueError(f"Ruta de base de datos inválida: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
    def setup_table(self):
        """Crear la tabla album_links si no existe"""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS album_links (
            id INTEGER PRIMARY KEY,
            album_id INTEGER NOT NULL,
            boomkat_url TEXT,
            soundcloud_url TEXT,
            allmusic_url TEXT,
            last_updated TIMESTAMP,
            FOREIGN KEY (album_id) REFERENCES albums(id)
        )
        ''')
        
        # Crear índice para búsquedas rápidas
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_album_links_album_id ON album_links(album_id)')
        
        # Asegurarse de que todos los álbumes tienen una entrada en album_links
        self.cursor.execute('''
        INSERT OR IGNORE INTO album_links (album_id, last_updated)
        SELECT id, NULL FROM albums WHERE id NOT IN (SELECT album_id FROM album_links)
        ''')
        
        self.conn.commit()
        print("Tabla album_links configurada correctamente")
    
    def get_albums_to_process(self):
        """Obtener lista de álbumes para procesar basado en el flag missing_only"""
        if self.missing_only:
            # Solo obtener álbumes con enlaces faltantes
            self.cursor.execute('''
            SELECT a.id, a.name, art.name as artist_name, a.mbid, art.mbid as artist_mbid 
            FROM albums a 
            JOIN artists art ON a.artist_id = art.id
            LEFT JOIN album_links al ON a.id = al.album_id
            WHERE al.boomkat_url IS NULL OR al.soundcloud_url IS NULL OR al.allmusic_url IS NULL
            ORDER BY a.id
            ''')
        else:
            # Obtener todos los álbumes
            self.cursor.execute('''
            SELECT a.id, a.name, art.name as artist_name, a.mbid, art.mbid as artist_mbid 
            FROM albums a 
            JOIN artists art ON a.artist_id = art.id
            ORDER BY a.id
            ''')
        
        return self.cursor.fetchall()
        
    def search_boomkat_url(self, artist_name, album_name):
        """
        Busca URL de Boomkat para un álbum específico usando Playwright con un
        contenedor Chrome Browserless.
        
        Args:
            artist_name (str): Nombre del artista
            album_name (str): Nombre del álbum
                
        Returns:
            str: URL de Boomkat para el álbum o None si no se encuentra
        """
        
        # Configuración actualizada para browserless - Cambiando de ws a wss y añadiendo token
        BROWSERLESS_URL = "http://192.168.1.133:3000?token=toketaso"
        
        # También preparamos una URL HTTP alternativa en caso de que necesitemos cambiar de protocolo
        BROWSERLESS_HTTP_URL = "http://192.168.1.133:3000"
        
        # Lista de User-Agents para rotar
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        ]
        
        # Primero intentamos buscar solo por el artista para obtener resultados más amplios
        artist_search = quote_plus(artist_name)
        
        # URL base de búsqueda de Boomkat
        search_url = f"https://boomkat.com/search?q={artist_search}"
        
        user_agent = random.choice(user_agents)
        
        print(f"Buscando en Boomkat por artista: {artist_name}")
        
        # Configurar reintentos
        max_retries = 3
        retry_delay = 2
        best_match = None
        
        try:
            with sync_playwright() as p:
                for attempt in range(max_retries):
                    browser = None
                    context = None
                    page = None
                    
                    try:
                        print(f"Intento {attempt+1}: Conectando a browserless en {BROWSERLESS_URL}")
                        
                        # Probar diferentes métodos de conexión
                        try:
                            # Intento 1: Conexión directa con browserless via WebSocket
                            browser = p.chromium.connect_over_cdp(BROWSERLESS_URL, timeout=30000)
                            print("Conexión correcta con browserless via WebSocket")
                        except Exception as connect_err:
                            print(f"Error al conectar con browserless via WebSocket: {str(connect_err)}")
                            
                            try:
                                # Intento 2: Probar conexión HTTP en lugar de WebSocket
                                print(f"Intentando conexión HTTP en lugar de WebSocket: {BROWSERLESS_HTTP_URL}")
                                browser = p.chromium.connect_over_cdp(BROWSERLESS_HTTP_URL, timeout=30000)
                                print("Conexión correcta con browserless via HTTP")
                            except Exception as http_err:
                                print(f"Error al conectar con browserless via HTTP: {str(http_err)}")
                                
                                # Intento 3: Usar chromium local en modo headless
                                print("Intentando lanzar navegador local en su lugar...")
                                browser = p.chromium.launch(
                                    headless=True,
                                    args=["--disable-web-security", "--no-sandbox"]
                                )
                                print("Navegador local lanzado como alternativa")
                        
                        # Crear contexto con el user-agent aleatorio
                        context = browser.new_context(
                            user_agent=user_agent,
                            viewport={"width": 1280, "height": 800},
                            locale="en-US",
                            timezone_id="America/New_York",
                            bypass_csp=True,
                            extra_http_headers={
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                                "Accept-Language": "en-US,en;q=0.5",
                                "Upgrade-Insecure-Requests": "1",
                                "Cache-Control": "max-age=0",
                                "DNT": "1"
                            }
                        )
                        
                        # Crear una nueva página
                        page = context.new_page()
                        
                        # Resto del código permanece igual...
                        # ... (código para navegar, buscar y procesar resultados)
                        
                        # Primero visitar la página principal para obtener cookies
                        print("Visitando la página principal de Boomkat primero...")
                        
                        # Usar un wait_until más flexible y aumentar el timeout
                        try:
                            page.goto('https://boomkat.com/', wait_until="domcontentloaded", timeout=30000)
                        except Exception as nav_err:
                            print(f"Advertencia en navegación inicial: {str(nav_err)}")
                            # Continuamos incluso si hay timeout
                        
                        # Añadir un retraso aleatorio para simular comportamiento humano
                        time.sleep(random.uniform(1.0, 2.0))
                        
                        # Ir a la página de búsqueda
                        print(f"Navegando a la URL de búsqueda: {search_url}")
                        try:
                            response = page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                            if not response:
                                print("Respuesta nula en la navegación a la búsqueda")
                                continue
                                
                            if not response.ok:
                                print(f"Error en la respuesta de Boomkat: {response.status}")
                                if attempt < max_retries - 1:
                                    wait_time = retry_delay * (2 ** attempt)
                                    print(f"Esperando {wait_time} segundos antes de reintentar...")
                                    time.sleep(wait_time)
                                    continue
                                else:
                                    print("Se agotaron los reintentos")
                                    break
                        except Exception as search_err:
                            print(f"Error en la navegación a la búsqueda: {str(search_err)}")
                            # Intentamos continuar de todos modos
                        
                        # Capturar una captura de pantalla para ver qué está pasando
                        screenshot_path = f'boomkat_debug_{attempt}.png'
                        page.screenshot(path=screenshot_path)
                        print(f"Captura de pantalla guardada en: {screenshot_path}")
                        
                        # El resto del código permanece igual...
                        # Esperar a que los resultados se carguen
                        found_selector = False
                        for selector in ['div.product', 'div.listing2__product', 'div.product-list-item']:
                            try:
                                page.wait_for_selector(selector, timeout=5000)
                                found_selector = True
                                print(f"Encontrado selector: {selector}")
                                break
                            except Exception as e:
                                print(f"No se encontró el selector: {selector} - Error: {str(e)}")
                        
                        if not found_selector:
                            print("No se encontraron resultados con ningún selector conocido")
                            # Guardar captura de pantalla para depuración
                            screenshot_path = f'boomkat_no_results_{attempt}.png'
                            page.screenshot(path=screenshot_path)
                            print(f"Captura de pantalla guardada en: {screenshot_path}")
                            
                            # Guardar el HTML para depuración
                            content = page.content()
                            html_path = f'boomkat_response_{attempt}.html'
                            with open(html_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            print(f"HTML guardado en: {html_path}")
                            
                            if attempt >= max_retries - 1:
                                print("Se agotaron los reintentos, no se encontraron resultados")
                                break
                            continue
                        
                        products = []
                        for selector in ['div.product', 'div.listing2__product div.product', 'div.product-list-item']:
                            products = page.query_selector_all(selector)
                            if products and len(products) > 0:
                                print(f"Encontrados {len(products)} elementos con selector: {selector}")
                                break
                        
                        if not products or len(products) == 0:
                            print("No se encontraron productos en la página")
                            continue
                        
                        # Normalizar los nombres para comparación
                        artist_normalized = self._normalize_for_comparison(artist_name)
                        album_normalized = self._normalize_for_comparison(album_name)
                        
                        best_score = 0
                        
                        # Analizar los primeros 10 resultados (o menos si hay menos)
                        max_items = min(10, len(products))
                        for i in range(max_items):
                            try:
                                product = products[i]
                                
                                # Extraer información del producto usando la API síncrona de Playwright
                                product_data = product.evaluate('''(element) => {
                                    const artistEl = element.querySelector('strong') || element.querySelector('.artist');
                                    const albumEl = element.querySelector('.album-title') || element.querySelector('.title');
                                    const linkEl = element.querySelector('a[href*="/albums/"]') || 
                                                element.querySelector('a[href*="/releases/"]') || 
                                                element.closest('a');
                                    
                                    let artist = artistEl ? artistEl.textContent.trim() : '';
                                    let album = albumEl ? albumEl.textContent.trim() : '';
                                    
                                    // Si no encontramos artista/álbum específicamente, intentar extraer del texto completo
                                    if (!artist || !album) {
                                        const fullText = element.textContent.trim();
                                        const parts = fullText.split(/\\s+[\\-–—]\\s+/, 2);
                                        if (parts.length === 2) {
                                            artist = artist || parts[0].trim();
                                            album = album || parts[1].trim();
                                        }
                                    }
                                    
                                    const href = linkEl ? linkEl.getAttribute('href') : null;
                                    
                                    return {
                                        artist: artist,
                                        album: album,
                                        url: href
                                    };
                                }''')
                                
                                if not product_data.get('artist') or not product_data.get('album') or not product_data.get('url'):
                                    print(f"Datos incompletos para el producto {i+1}")
                                    continue
                                
                                item_artist = product_data['artist']
                                item_title = product_data['album']
                                item_url = product_data['url']
                                
                                print(f"\nProducto {i+1}:")
                                print(f"Artista: '{item_artist}', Álbum: '{item_title}'")
                                
                                # Normalizar para comparación
                                item_artist_normalized = self._normalize_for_comparison(item_artist)
                                item_title_normalized = self._normalize_for_comparison(item_title)
                                
                                # Calcular puntuación de coincidencia
                                artist_score = self._similarity_score(artist_normalized, item_artist_normalized)
                                title_score = self._similarity_score(album_normalized, item_title_normalized)
                                
                                print(f"Puntuación - Artista: {artist_score:.2f}, Título: {title_score:.2f}")
                                
                                # Ponderación: artista más importante que título
                                total_score = (artist_score * 0.6) + (title_score * 0.4)
                                
                                # Si el artista coincide bien pero el título no tanto, seguir considerándolo
                                if artist_score > 0.85:
                                    total_score = max(total_score, 0.7)
                                
                                # Si es un buen match, guardar el enlace
                                if total_score > best_score and total_score > 0.6:
                                    best_score = total_score
                                    
                                    # Obtener la URL completa
                                    product_url = item_url
                                    if not product_url.startswith('http'):
                                        product_url = 'https://boomkat.com' + product_url
                                    best_match = product_url
                                    print(f"Nuevo mejor match: {best_score:.2f}: {best_match}")
                                
                            except Exception as e:
                                print(f"Error al procesar elemento {i+1}: {str(e)}")
                                continue
                        
                        # Si encontramos un match aceptable, terminar el bucle
                        if best_match and best_score > 0.6:
                            print(f"Encontrado en Boomkat con puntuación {best_score:.2f}: {best_match}")
                            break
                        
                        # Si no encontramos un match pero es el último intento, volver a intentar con la búsqueda completa
                        if attempt == max_retries - 1 and not best_match:
                            # Intentar una búsqueda más específica
                            full_search = quote_plus(f"{artist_name} {album_name}")
                            full_search_url = f"https://boomkat.com/search?q={full_search}"
                            print(f"Último intento con búsqueda completa: {full_search_url}")
                            
                            try:
                                page.goto(full_search_url, wait_until="domcontentloaded", timeout=30000)
                                time.sleep(2)  # Dar tiempo para que cargue
                            except Exception as final_err:
                                print(f"Error en la búsqueda final: {str(final_err)}")
                                # Continuamos de todos modos
                            
                    except Exception as e:
                        print(f"Error detallado en intento {attempt+1}: {type(e).__name__}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            print(f"Esperando {wait_time} segundos antes de reintentar...")
                            time.sleep(wait_time)
                        else:
                            print("Se agotaron los reintentos")
                    finally:
                        # Cerrar recursos de forma segura
                        try:
                            if page:
                                page.close()
                            if context:
                                context.close()
                            if browser:
                                browser.close()
                        except Exception as e:
                            print(f"Error al cerrar recursos: {str(e)}")
                        
                        # Añadir un retraso para evitar ser bloqueado
                        time.sleep(random.uniform(1.5, 3.0))
        except Exception as outer_e:
            print(f"Error externo en Playwright: {str(outer_e)}")
            import traceback
            traceback.print_exc()
        
        return best_match

    def _normalize_for_comparison(self, text):
        """
        Normaliza texto para comparación eliminando caracteres especiales,
        convirtiendo a minúsculas y quitando palabras comunes.
        """
        if not text:
            return ""
            
        # Convertir a minúsculas
        text = text.lower()
        
        # Eliminar caracteres especiales y sustituir por espacios
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Eliminar dígitos aislados
        text = re.sub(r'\b\d+\b', '', text)
        
        # Eliminar palabras comunes en títulos de álbumes y ediciones
        common_words = ['reissue', 'remastered', 'deluxe', 'edition', 'vinyl', 'cd', 
                        'limited', 'special', 'expanded', 'anniversary', 'the', 'ep',
                        'feat', 'featuring', 'lp', 'original', 'soundtrack', 'ost',
                        'version', 'mix', 'remix', 'digital', 'download']
                        
        for word in common_words:
            text = re.sub(r'\b' + word + r'\b', '', text)
        
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def _similarity_score(self, str1, str2):
        """
        Calcula una puntuación de similitud entre dos cadenas
        usando una combinación de métodos para mayor precisión.
        
        Returns:
            float: Puntuación entre 0 (nada similar) y 1 (idéntico)
        """
        from difflib import SequenceMatcher
        import re
        
        if not str1 or not str2:
            return 0
        
        # Convertir a minúscula para comparación
        str1 = str1.lower()
        str2 = str2.lower()
        
        # Puntuación con SequenceMatcher
        sequence_score = SequenceMatcher(None, str1, str2).ratio()
        
        # Verificar si alguna es una subcadena de la otra (para manejar casos donde un título
        # es una versión recortada del otro)
        substring_match = 0
        if str1 in str2 or str2 in str1:
            min_len = min(len(str1), len(str2))
            max_len = max(len(str1), len(str2))
            substring_match = min_len / max_len
        
        # Comparar palabras individuales (para casos donde el orden es diferente)
        words1 = set(re.findall(r'\b\w+\b', str1))
        words2 = set(re.findall(r'\b\w+\b', str2))
        
        if not words1 or not words2:
            word_match = 0
        else:
            common_words = words1.intersection(words2)
            all_words = words1.union(words2)
            word_match = len(common_words) / len(all_words) if all_words else 0
        
        # Combinar las puntuaciones (puedes ajustar estos pesos)
        final_score = (sequence_score * 0.5) + (substring_match * 0.3) + (word_match * 0.2)
        
        return final_score

    
    def search_allmusic_url(self, artist_name, album_name, mbid=None):
        """
        Busca URL de AllMusic para un álbum específico usando web scraping.
        
        Args:
            artist_name (str): Nombre del artista
            album_name (str): Nombre del álbum
            mbid (str, optional): MusicBrainz ID del álbum
                
        Returns:
            str: URL de AllMusic para el álbum o None si no se encuentra
        """
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import quote_plus
        import time
        import re
        
        # Normalizar nombres para búsqueda
        search_term = f"{artist_name} {album_name}".strip()
        encoded_search = quote_plus(search_term)
        
        # URL base de búsqueda de AllMusic
        search_url = f"https://www.allmusic.com/search/albums/{encoded_search}"
        
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.allmusic.com/',
        }
        
        try:
            print(f"Buscando en AllMusic: {search_term}")
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"Error en la respuesta de AllMusic: {response.status_code}")
                return None
                
            # Parsear la página de resultados
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # AllMusic muestra resultados en una lista de elementos
            result_items = soup.select('.album')
            
            if not result_items:
                print(f"No se encontraron resultados en AllMusic para: {search_term}")
                return None
                
            # Normalizar los nombres para comparación
            artist_normalized = self._normalize_for_comparison(artist_name)
            album_normalized = self._normalize_for_comparison(album_name)
            
            best_match = None
            best_score = 0
            
            for item in result_items:
                # Extraer título y artista del elemento
                title_elem = item.select_one('.title')
                artist_elem = item.select_one('.performer')
                
                if not title_elem or not artist_elem:
                    continue
                    
                item_title = title_elem.get_text().strip()
                item_artist = artist_elem.get_text().strip()
                
                # Normalizar para comparación
                item_title_normalized = self._normalize_for_comparison(item_title)
                item_artist_normalized = self._normalize_for_comparison(item_artist)
                
                # Calcular puntuación de coincidencia
                # Coincidencia exacta de artista es más importante
                artist_score = self._similarity_score(artist_normalized, item_artist_normalized)
                title_score = self._similarity_score(album_normalized, item_title_normalized)
                
                # Ponderación: artista más importante que título
                total_score = (artist_score * 0.6) + (title_score * 0.4)
                
                # Si es un buen match, guardar el enlace
                if total_score > best_score and total_score > 0.7:  # Umbral de aceptación
                    best_score = total_score
                    
                    # Extraer el enlace al álbum
                    link_elem = title_elem.find('a')
                    if link_elem and 'href' in link_elem.attrs:
                        album_url = link_elem['href']
                        if not album_url.startswith('http'):
                            album_url = 'https://www.allmusic.com' + album_url
                        best_match = album_url
            
            # Añadir un retraso para evitar ser bloqueado
            time.sleep(self.delay_between_requests)
            
            if best_match:
                print(f"Encontrado en AllMusic con puntuación {best_score:.2f}: {best_match}")
                return best_match
            else:
                print(f"No se encontró un match aceptable en AllMusic para: {search_term}")
                return None
                
        except Exception as e:
            print(f"Error al buscar en AllMusic: {str(e)}")
            return None


    def search_soundcloud_url(self, artist_name, album_name):
        """
        Busca URL de SoundCloud para un álbum específico usando web scraping.
        
        Args:
            artist_name (str): Nombre del artista
            album_name (str): Nombre del álbum
                
        Returns:
            str: URL de SoundCloud para el álbum o None si no se encuentra
        """
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import quote_plus
        import time
        import re
        
        # Normalizar nombres para búsqueda
        search_term = f"{artist_name} {album_name}".strip()
        encoded_search = quote_plus(search_term)
        
        # URL base de búsqueda de SoundCloud (la búsqueda por sets para encontrar álbumes/playlists)
        search_url = f"https://soundcloud.com/search/sets?q={encoded_search}"
        
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://soundcloud.com/',
        }
        
        try:
            print(f"Buscando en SoundCloud: {search_term}")
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"Error en la respuesta de SoundCloud: {response.status_code}")
                return None
                
            # Parsear la página de resultados
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # SoundCloud muestra resultados en elementos con clases específicas
            # El selector puede necesitar ajustes dependiendo de la estructura HTML actual
            result_items = soup.select('.searchItem__searchResultsList .searchItem')
            
            if not result_items:
                print(f"No se encontraron resultados en SoundCloud para: {search_term}")
                return None
                
            # Normalizar los nombres para comparación
            artist_normalized = self._normalize_for_comparison(artist_name)
            album_normalized = self._normalize_for_comparison(album_name)
            
            best_match = None
            best_score = 0
            
            for item in result_items:
                # Extraer título y artista del elemento
                title_elem = item.select_one('.soundTitle__title')
                artist_elem = item.select_one('.soundTitle__username')
                
                if not title_elem or not artist_elem:
                    continue
                    
                item_title = title_elem.get_text().strip()
                item_artist = artist_elem.get_text().strip()
                
                # Normalizar para comparación
                item_title_normalized = self._normalize_for_comparison(item_title)
                item_artist_normalized = self._normalize_for_comparison(item_artist)
                
                # Calcular puntuación de coincidencia
                artist_score = self._similarity_score(artist_normalized, item_artist_normalized)
                title_score = self._similarity_score(album_normalized, item_title_normalized)
                
                # Ponderación: artista más importante que título
                total_score = (artist_score * 0.6) + (title_score * 0.4)
                
                # Si es un buen match, guardar el enlace
                if total_score > best_score and total_score > 0.65:  # Umbral de aceptación (ligeramente menor)
                    best_score = total_score
                    
                    # Extraer el enlace al set/playlist
                    link_elem = title_elem.find('a')
                    if link_elem and 'href' in link_elem.attrs:
                        set_url = link_elem['href']
                        if not set_url.startswith('http'):
                            set_url = 'https://soundcloud.com' + set_url
                        best_match = set_url
            
            # Añadir un retraso para evitar ser bloqueado
            time.sleep(self.delay_between_requests)
            
            if best_match:
                print(f"Encontrado en SoundCloud con puntuación {best_score:.2f}: {best_match}")
                return best_match
            else:
                print(f"No se encontró un match aceptable en SoundCloud para: {search_term}")
                return None
                
        except Exception as e:
            print(f"Error al buscar en SoundCloud: {str(e)}")
            return None
    
    def update_album_links(self, album_id, boomkat_url=None, soundcloud_url=None, allmusic_url=None):
        """Actualizar enlaces para un álbum específico"""
        # Primero, verificar si el álbum ya tiene una entrada en album_links
        self.cursor.execute("SELECT * FROM album_links WHERE album_id = ?", (album_id,))
        existing_record = self.cursor.fetchone()
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if existing_record:
            # Preparar actualización solo para los campos proporcionados
            update_fields = []
            update_values = []
            
            if boomkat_url is not None:
                update_fields.append("boomkat_url = ?")
                update_values.append(boomkat_url)
            
            if soundcloud_url is not None:
                update_fields.append("soundcloud_url = ?")
                update_values.append(soundcloud_url)
            
            if allmusic_url is not None:
                update_fields.append("allmusic_url = ?")
                update_values.append(allmusic_url)
            
            if update_fields:  # Solo actualizar si hay campos para actualizar
                update_fields.append("last_updated = ?")
                update_values.append(current_time)
                
                query = f"UPDATE album_links SET {', '.join(update_fields)} WHERE album_id = ?"
                update_values.append(album_id)
                
                self.cursor.execute(query, update_values)
        else:
            # Insertar un nuevo registro
            self.cursor.execute('''
            INSERT INTO album_links (album_id, boomkat_url, soundcloud_url, allmusic_url, last_updated)
            VALUES (?, ?, ?, ?, ?)
            ''', (album_id, boomkat_url, soundcloud_url, allmusic_url, current_time))
        
        self.conn.commit()
    
    def process_all_albums(self):
        """Procesar todos los álbumes y actualizar sus enlaces"""
        albums = self.get_albums_to_process()
        total_albums = len(albums)
        
        print(f"Procesando {total_albums} álbumes...")
        
        for i, album in enumerate(albums, 1):
            album_id = album['id']
            album_name = album['name']
            artist_name = album['artist_name']
            mbid = album['mbid']
            
            print(f"[{i}/{total_albums}] Procesando álbum: {artist_name} - {album_name}")
            
            # Buscar enlaces
            boomkat_url = self.search_boomkat_url(artist_name, album_name)
            soundcloud_url = self.search_soundcloud_url(artist_name, album_name)
            allmusic_url = self.search_allmusic_url(artist_name, album_name, mbid)
            
            # Actualizar enlaces en la base de datos
            self.update_album_links(album_id, boomkat_url, soundcloud_url, allmusic_url)
            
            # Mostrar progreso
            if i % 10 == 0 or i == total_albums:
                print(f"Progreso: {i}/{total_albums} ({i/total_albums*100:.1f}%)")
    
    def close(self):
        """Cerrar la conexión a la base de datos"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            print("Conexión a la base de datos cerrada")

def main(config=None):
    """Función principal que será llamada por el script padre"""
    if config is None:
        # Si se ejecuta directamente, parsear argumentos
        parser = argparse.ArgumentParser(description='Gestionar enlaces de álbumes')
        parser.add_argument('--db-path', required=True, help='Ruta a la base de datos SQLite')
        parser.add_argument('--missing-only', action='store_true', help='Solo procesar álbumes con enlaces faltantes')
        parser.add_argument('--delay', type=float, default=1.0, help='Retraso entre solicitudes (segundos)')
        args = parser.parse_args()
        
        # Combinar configuraciones
        config = {}
        config.update(config_data.get("common", {}))
        config.update(config_data.get("enlaces_albumes", {}))
    
    try:
        # Inicializar y ejecutar el gestor de enlaces
        manager = AlbumLinksManager(config)
        manager.setup_table()
        manager.process_all_albums()
    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        return 1
    finally:
        if 'manager' in locals():
            manager.close()
    
    print("Proceso completado exitosamente")
    return 0

if __name__ == "__main__":
    sys.exit(main())