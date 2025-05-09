# modules/submodules/shared/spotify_service.py
import os
import json
import time
import base64
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote
from threading import Timer
import http.server
import socketserver
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re


from base_module import PROJECT_ROOT



class SpotifyAuthHandler(http.server.SimpleHTTPRequestHandler):
    """Manejador de autorización para Spotify callback"""
    
    def __init__(self, *args, auth_code_callback=None, **kwargs):
        self.auth_code_callback = auth_code_callback
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Procesar solicitud GET con código de autorización"""
        query = urllib.parse.urlparse(self.path).query
        query_components = dict(qc.split("=") for qc in query.split("&") if "=" in qc)
        
        if "code" in query_components:
            auth_code = query_components["code"]
            self.auth_code_callback(auth_code)
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            success_html = """
            <html>
            <head><title>Autorización Spotify Completada</title></head>
            <body>
                <h1>Autorización Completada</h1>
                <p>Puedes cerrar esta ventana y volver a la aplicación.</p>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            error_html = """
            <html>
            <head><title>Error de Autorización</title></head>
            <body>
                <h1>Error de Autorización</h1>
                <p>No se recibió código de autorización. Por favor, intenta nuevamente.</p>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())
        
        self.server.server_close()
        return


class SpotifyService:
    """Servicio unificado para interactuar con la API de Spotify"""
    
    def __init__(self, client_id, client_secret, redirect_uri, cache_dir, cache_duration=24, spotify_client=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = "https://api.spotify.com/v1"
        self.auth_url = "https://accounts.spotify.com/api/token"
        self.authorize_url = "https://accounts.spotify.com/authorize"
        
        self.cache_dir = Path(cache_dir)
        self.cache_duration = cache_duration
        self.access_token = None
        self.token_expiry = None
        
        # Variable para capturar errores
        self.last_error = None
        
        # Variables Spotipy
        self.sp = spotify_client
        self.sp_oauth = None
        self.authenticated = False
        
        # Validar credenciales
        if not self.client_id or not self.client_secret:
            self.last_error = "Credenciales Spotify incompletas"
            return
        
        # Crear directorio de caché si no existe
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.last_error = f"Error creando directorio de caché: {str(e)}"
            return
        
        # Intentar cargar token guardado
        self._load_saved_token()
    
    def setup(self):
        """Configurar y autenticar con Spotify"""
        try:
            # Verificar si ya tenemos un error de inicialización
            if self.last_error:
                print(f"Error previo en inicialización: {self.last_error}")
                return False
            
            # Definir scope para permisos de Spotify
            scope = "playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative user-follow-read user-read-email"
            
            # Crear instancia OAuth
            self.sp_oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=scope,
                open_browser=False,
                cache_path=str(self.cache_dir / "spotify_token.txt")
            )
            
            # Obtener token
            token_info = self._get_token_or_authenticate()
            
            if token_info:
                # Crear cliente Spotify con el token
                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                
                # Obtener información del usuario
                try:
                    user_info = self.sp.current_user()
                    self.spotify_user_id = user_info['id']
                    print(f"Authenticated as user: {self.spotify_user_id}")
                    self.authenticated = True
                    return True
                except Exception as e:
                    self.last_error = f"Error obteniendo info de usuario: {str(e)}"
                    print(self.last_error)
                    return False
            else:
                self.last_error = "No se pudo obtener token de autenticación"
                return False
            
        except ImportError as e:
            self.last_error = f"Error importando spotipy: {str(e)}. ¿Está instalado?"
            print(self.last_error)
            return False
        except Exception as e:
            self.last_error = f"Error configurando Spotify: {str(e)}"
            print(self.last_error)
            return False
    
    def _load_saved_token(self):
        """Cargar token guardado si existe y es válido"""
        token_file = self.cache_dir / "spotify_token.json" or PROJECT_ROOT / ".cache" / "spotify_token.txt"
        
        if token_file.exists():
            try:
                with open(token_file, "r") as f:
                    token_data = json.load(f)
                
                expiry_time = datetime.fromisoformat(token_data.get("expiry", ""))
                
                if datetime.now() < expiry_time - timedelta(minutes=5):
                    self.access_token = token_data.get("access_token")
                    self.token_expiry = expiry_time
                    return True
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error cargando token guardado: {e}")
        
        return False
    
    def _save_token(self):
        """Guardar token actual en caché"""
        if not self.access_token or not self.token_expiry:
            return
        
        token_file = self.cache_dir / "spotify_token.json"
        
        try:
            token_data = {
                "access_token": self.access_token,
                "expiry": self.token_expiry.isoformat()
            }
            
            with open(token_file, "w") as f:
                json.dump(token_data, f)
        except Exception as e:
            print(f"Error guardando token: {e}")
    
 
    
    def _get_token_or_authenticate(self):
        """Obtener token válido o iniciar autenticación"""
        try:
            # Verificar token en caché
            cached_token = self.sp_oauth.get_cached_token()
            if cached_token and not self.sp_oauth.is_token_expired(cached_token):
                return cached_token
            elif cached_token:
                try:
                    new_token = self.sp_oauth.refresh_access_token(cached_token['refresh_token'])
                    return new_token
                except Exception as e:
                    print(f"Token refresh failed: {str(e)}")
            
            # Si no hay token válido, realizar nueva autenticación
            print("Iniciando autenticación de Spotify...")
            return self._perform_new_authentication()
        except Exception as e:
            print(f"Error en get_token_or_authenticate: {str(e)}")
            return None
    
    def _perform_new_authentication(self):
        """Realizar autenticación desde cero"""
        auth_url = self.sp_oauth.get_authorize_url()
        
        # Para interactuar con el usuario, podría usar PyQt dialogs aquí
        print(f"Por favor, visita: {auth_url}")
        redirect_url = input("Ingresa la URL de redirección: ")
        
        if redirect_url:
            try:
                if '%3A' in redirect_url or '%2F' in redirect_url:
                    redirect_url = unquote(redirect_url)
                
                code = None
                if redirect_url.startswith('http'):
                    code = self.sp_oauth.parse_response_code(redirect_url)
                elif 'code=' in redirect_url:
                    code = redirect_url.split('code=')[1].split('&')[0]
                else:
                    code = redirect_url
                
                if code:
                    token_info = self.sp_oauth.get_access_token(code)
                    return token_info
            except Exception as e:
                print(f"Error en autenticación: {str(e)}")
        
        return None
    
    def get_client_credentials(self):
        """Obtener token usando Client Credentials Flow"""
        if self.access_token and datetime.now() < self.token_expiry:
            return self.access_token
        
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(self.auth_url, headers=headers, data=data)
            response.raise_for_status()
            
            token_info = response.json()
            self.access_token = token_info.get("access_token")
            
            expires_in = token_info.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            self._save_token()
            
            return self.access_token
        except requests.exceptions.RequestException as e:
            print(f"Error obteniendo token: {e}")
            return None
    
    def search_artist(self, name):
        """Buscar un artista por nombre"""
        cache_file = self._get_cache_file_path(f"artist_{name}")
        cached_data = self._load_from_cache(cache_file)
        
        if cached_data:
            return cached_data
        
        token = self.get_client_credentials()
        if not token:
            return None
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        params = {
            "q": name,
            "type": "artist",
            "limit": 1
        }
        
        try:
            response = requests.get(f"{self.base_url}/search", headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            artists = data.get("artists", {}).get("items", [])
            
            if artists:
                artist_data = artists[0]
                self._save_to_cache(cache_file, artist_data)
                return artist_data
            
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error buscando artista: {e}")
            return None
    
    def get_artist_concerts_from_db_or_search(self, artist_name, db_path):
        """Obtener información de conciertos para un artista"""
        import sqlite3
        
        # Verificar caché primero
        cache_file = self._get_cache_file_path(f"spotify_concerts_{artist_name}")
        cached_data = self._load_from_cache(cache_file)
        
        if cached_data:
            return cached_data, f"Se encontraron {len(cached_data)} conciertos para {artist_name} (caché)"
        
        # Buscar en BD
        artist_url = None
        try:
            db_conn = sqlite3.connect(db_path)
            cursor = db_conn.cursor()
            cursor.execute("SELECT spotify_url FROM artists WHERE name = ?", (artist_name,))
            result = cursor.fetchone()
            
            if result and result[0]:
                artist_url = result[0]
            else:
                artist_url = self.search_artist_url(artist_name)
                if result:
                    cursor.execute("UPDATE artists SET spotify_url = ? WHERE name = ?", (artist_url, artist_name))
                    db_conn.commit()
        except Exception as e:
            print(f"Error accessing database: {e}")
            artist_url = self.search_artist_url(artist_name)
        finally:
            if 'db_conn' in locals():
                db_conn.close()
        
        if not artist_url:
            return [], f"No se encontró URL de Spotify para {artist_name}"
        
        # Scrapear conciertos
        return self.scrape_artist_concerts(artist_url, artist_name)
    
    def search_artist_url(self, artist_name):
        """Buscar URL del artista en Spotify"""
        artist_data = self.search_artist(artist_name)
        if artist_data and 'external_urls' in artist_data:
            return artist_data['external_urls'].get('spotify', '')
        return ''
    
    def scrape_artist_concerts(self, artist_url, artist_name):
        """Scrapear conciertos de un artista usando Selenium con mejor extracción de datos"""
        match = re.search(r'/artist/([^/]+)', artist_url)
        if not match:
            return [], "URL de artista inválida"
        
        artist_id = match.group(1)
        concerts_url = f"https://open.spotify.com/artist/{artist_id}/concerts"
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # Prevenir detección de automatización
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        
        # Agregar argumentos adicionales para mejor rendimiento
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.get(concerts_url)
            
            # Aumentar tiempo de espera para asegurar carga completa
            wait = WebDriverWait(driver, 10)
            
            # Intentar diferentes selectores para asegurar que encontramos los conciertos
            concert_selectors = [
                '[data-testid="concert-row"]',
                'a[href*="/concert/"]',
                'div[role="row"]',
                '.encore-text-body-medium' # Un selector de respaldo general
            ]
            
            for selector in concert_selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    print(f"Selector encontrado: {selector}")
                    concert_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if concert_elements and len(concert_elements) > 0:
                        break
                except Exception as e:
                    print(f"Selector {selector} no encontrado: {e}")
                    concert_elements = []
            
            if not concert_elements:
                return [], f"No se encontraron conciertos para {artist_name}"
            
            # Pausa para asegurar que todo esté cargado
            time.sleep(2)
            
            concerts = []
            
            for element in concert_elements:
                try:
                    # Extraer enlace completo del concierto para obtener más detalles
                    concert_link = element.get_attribute('href')
                    if not concert_link:
                        links = element.find_elements(By.TAG_NAME, 'a')
                        for link in links:
                            href = link.get_attribute('href')
                            if href and '/concert/' in href:
                                concert_link = href
                                break
                    
                    # Datos básicos del concierto
                    date_element = element.find_element(By.TAG_NAME, 'time')
                    date = date_element.get_attribute('datetime') if date_element else ""
                    
                    # Diferentes intentos para obtener datos
                    try:
                        day = self._find_element_safely(element, '.encore-text-body-medium-bold')
                    except:
                        day = self._find_element_safely(element, '[data-encore-type="text"][class*="bold"]')
                    
                    try:
                        month = self._find_element_safely(element, '.encore-text-body-small')
                    except:
                        month = ""
                    
                    try:
                        city = self._find_element_safely(element, '.encore-text-body-medium')
                    except:
                        city = self._find_element_safely(element, '[data-encore-type="text"]')
                    
                    try:
                        venue = self._find_element_safely(element, '[data-testid="event-venue"]')
                    except:
                        venue = ""
                    
                    # Obtener horario con múltiples intentos
                    time_str = ""
                    time_selectors = [
                        '.G8sU0RZZT\\*ZhaEv7B26V .encore-text-body-medium',
                        '[data-encore-type="text"][class*="encore-text-body-medium"]',
                        '.encore-text-body-medium:last-child',
                        'span.encore-text-body-medium'
                    ]
                    
                    for selector in time_selectors:
                        try:
                            time_str = element.find_element(By.CSS_SELECTOR, selector).text
                            if time_str:
                                break
                        except:
                            continue
                    
                    # Crear objeto básico del concierto
                    concert = {
                        'artist': artist_name,
                        'name': f"{venue} Concert" if venue else "Concert",
                        'venue': venue,
                        'city': city,
                        'date': date[:10] if date else '',
                        'time': time_str,
                        'image': '',
                        'url': concert_link,
                        'source': 'Spotify'
                    }
                    
                    # Si tenemos un enlace a un concierto específico, obtener más detalles
                    if concert_link and '/concert/' in concert_link:
                        try:
                            # Abrir la página del concierto en una nueva pestaña para obtener más detalles
                            driver.execute_script("window.open(arguments[0]);", concert_link)
                            # Cambiar a la nueva pestaña
                            driver.switch_to.window(driver.window_handles[1])
                            
                            # Esperar que cargue la página
                            time.sleep(3)
                            
                            # Obtener detalles adicionales
                            venue_details = self._extract_concert_details(driver)
                            
                            # Cerrar la pestaña y volver a la original
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                            
                            # Fusionar los detalles obtenidos con el objeto del concierto
                            if venue_details:
                                concert.update(venue_details)
                        except Exception as e:
                            print(f"Error obteniendo detalles del concierto: {e}")
                    
                    concerts.append(concert)
                    
                except Exception as e:
                    print(f"Error procesando elemento de concierto: {e}")
                    continue
            
            # Actualizar caché
            cache_file = self._get_cache_file_path(f"spotify_concerts_{artist_name}")
            self._save_to_cache(cache_file, concerts)
            
            return concerts, f"Se encontraron {len(concerts)} conciertos para {artist_name} (scraping)"
            
        except Exception as e:
            return [], f"Error en scraping: {str(e)}"
        finally:
            driver.quit()

    def _find_element_safely(self, element, selector):
        """Método auxiliar para encontrar elementos de manera segura"""
        try:
            result = element.find_element(By.CSS_SELECTOR, selector)
            return result.text.strip() if result else ""
        except:
            return ""

    def _extract_concert_details(self, driver):
        """Extrae detalles adicionales de la página de un concierto específico"""
        try:
            venue_details = {}
            
            # Intentar múltiples selectores para obtener la dirección del venue
            address_selectors = [
                "#main > div > div.ZQftYELq0aOsg6tPbVbV > div.jEMA2gVoLgPQqAFrPhFw > div > div.main-view-container__scroll-node > div:nth-child(1) > div > main > section > div.gKtc3TdowDTXBaVESi1D > div.VvL91cIRcCi1hJh0K845 > div.LdW0YNvo_Y77hgqhL4zY > a > h2:nth-child(1)",
                "a[href*='maps'] h2",
                "h2",
                ".main-view-container h2:first-of-type"
            ]
            
            for selector in address_selectors:
                try:
                    address_element = driver.find_element(By.CSS_SELECTOR, selector)
                    if address_element and address_element.text:
                        venue_details['address'] = address_element.text.strip()
                        break
                except:
                    continue
            
            # Intentar obtener ubicación precisa
            try:
                location_link = driver.find_element(By.CSS_SELECTOR, "a[href*='maps']")
                if location_link:
                    map_url = location_link.get_attribute('href')
                    venue_details['map_url'] = map_url
                    
                    # Extraer coordenadas de Google Maps URL si están disponibles
                    coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', map_url)
                    if coords_match:
                        venue_details['latitude'] = coords_match.group(1)
                        venue_details['longitude'] = coords_match.group(2)
            except:
                pass
            
            # Intentar obtener precios si están disponibles
            try:
                price_element = driver.find_element(By.CSS_SELECTOR, "[data-testid='ticket-price']")
                if price_element:
                    venue_details['price'] = price_element.text.strip()
            except:
                pass
            
            # Intentar obtener estado (sold out, etc.)
            try:
                status_element = driver.find_element(By.CSS_SELECTOR, "[data-testid='ticket-status']")
                if status_element:
                    venue_details['status'] = status_element.text.strip()
            except:
                pass
            
            # Intentar obtener información adicional (descripción)
            try:
                description_element = driver.find_element(By.CSS_SELECTOR, ".concert-description")
                if description_element:
                    venue_details['description'] = description_element.text.strip()
            except:
                pass
            
            # Obtener enlace a tickets (específicamente con los selectores proporcionados)
            ticket_selectors = [
                "#main > div > div.ZQftYELq0aOsg6tPbVbV > div.jEMA2gVoLgPQqAFrPhFw > div > div.main-view-container__scroll-node.ZjfaJlGQZ42nCWjD3FDm > div:nth-child(1) > div > main > section > div.gKtc3TdowDTXBaVESi1D > div.VvL91cIRcCi1hJh0K845 > div.LdW0YNvo_Y77hgqhL4zY > div.cTkykhjfHxkEGKbxSxXw > a",
                "div.LdW0YNvo_Y77hgqhL4zY > div.cTkykhjfHxkEGKbxSxXw > a",
                "p.encore-text-body-medium-bold.encore-internal-color-text-positive",
                "p.encore-text-body-medium-bold",
                "a[href*='ticket']"
            ]
            
            for selector in ticket_selectors:
                try:
                    ticket_element = driver.find_element(By.CSS_SELECTOR, selector)
                    if ticket_element:
                        # Verificar si es el elemento en sí o si contiene el texto "tickets" o similar
                        element_text = ticket_element.text.lower()
                        if 'ticket' in element_text or 'comprar' in element_text or 'buy' in element_text:
                            ticket_url = ticket_element.get_attribute('href')
                            if ticket_url:
                                # Guardar el enlace original por si acaso
                                venue_details['ticket_url_original'] = ticket_url
                                
                                # Procesar el enlace para extraer la URL de destino real
                                processed_url = self._extract_destination_url(ticket_url)
                                if processed_url:
                                    venue_details['ticket_url'] = processed_url
                                
                                # También guardar el texto del botón/enlace
                                venue_details['ticket_text'] = element_text
                                break
                except:
                    continue
            
            # Si no se encontró con los selectores específicos, intentar una búsqueda más general
            if 'ticket_url' not in venue_details:
                try:
                    # Buscar todos los enlaces en la página
                    all_links = driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        href = link.get_attribute('href')
                        if href and ('ticket' in href.lower() or 'buy' in href.lower() or 'comprar' in href.lower()):
                            # Guardar el enlace original
                            venue_details['ticket_url_original'] = href
                            
                            # Procesar el enlace
                            processed_url = self._extract_destination_url(href)
                            if processed_url:
                                venue_details['ticket_url'] = processed_url
                            
                            try:
                                venue_details['ticket_text'] = link.text
                            except:
                                pass
                            break
                except:
                    pass



            return venue_details
        
        except Exception as e:
            print(f"Error extrayendo detalles del concierto: {e}")
            return {}
    

    def _extract_destination_url(self, url):
        """
        Extrae la URL de destino real desde un enlace de redireccionamiento
        
        Args:
            url (str): URL original que puede contener un parámetro de destino
            
        Returns:
            str: URL de destino extraída o URL original si no se puede extraer
        """
        try:
            # Verificar si es un enlace de redirección con parámetro 'destination'
            if 'destination=' in url:
                # Encontrar la posición del parámetro 'destination='
                dest_pos = url.find('destination=')
                if dest_pos > -1:
                    # Extraer todo lo que viene después de 'destination='
                    dest_value = url[dest_pos + 12:]  # 12 es la longitud de 'destination='
                    
                    # Si hay otros parámetros después, cortar en el primer '&'
                    amp_pos = dest_value.find('&')
                    if amp_pos > -1:
                        dest_value = dest_value[:amp_pos]
                    
                    # Decodificar la URL (puede estar codificada varias veces)
                    from urllib.parse import unquote
                    dest_url = unquote(dest_value)
                    
                    # A veces, la URL puede estar codificada múltiples veces
                    while '%' in dest_url:
                        new_dest_url = unquote(dest_url)
                        if new_dest_url == dest_url:  # Si ya no cambia, salir del bucle
                            break
                        dest_url = new_dest_url
                    
                    return dest_url
            
            # Si no se puede extraer el destino, devolver la URL original
            return url
        except Exception as e:
            print(f"Error procesando URL de destino: {e}")
            return url

    def _get_cache_file_path(self, cache_key):
        """Generar ruta al archivo de caché"""
        safe_key = "".join(x for x in cache_key if x.isalnum() or x in " _-").rstrip()
        safe_key = safe_key.replace(" ", "_").lower()
        return self.cache_dir / f"spotify_{safe_key}.json"
    
    def _load_from_cache(self, cache_file):
        """Cargar datos de caché si existen y son válidos"""
        if not cache_file.exists():
            return None
        
        try:
            file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            cache_age = datetime.now() - file_time
            
            if cache_age > timedelta(hours=self.cache_duration):
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if isinstance(data, dict) and 'timestamp' in data:
                    cache_time = datetime.fromisoformat(data['timestamp'])
                    if (datetime.now() - cache_time) > timedelta(hours=self.cache_duration):
                        return None
                    return data.get('data', data)
                else:
                    return data
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error leyendo caché: {e}")
            return None
    
    def _save_to_cache(self, cache_file, data):
        """Guardar resultados en caché"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Error guardando caché: {e}")
    
    def clear_cache(self, pattern=None):
        """Limpiar caché"""
        if pattern:
            for file in self.cache_dir.glob(f"spotify_{pattern}*.json"):
                file.unlink()
        else:
            for file in self.cache_dir.glob("spotify_*.json"):
                file.unlink()


# Agregar este nuevo método a la clase SpotifyService en spotify.py

    def get_artist_albums(self, artist_id, limit=10):
        """
        Obtener los álbumes de un artista desde Spotify
        
        Args:
            artist_id (str): ID del artista en Spotify
            limit (int): Límite de álbumes a obtener
            
        Returns:
            dict: Datos de los álbumes o None si hay error
        """
        token = self.get_client_credentials()
        if not token:
            return None
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        params = {
            "limit": limit,
            "include_groups": "album,single"
        }
        
        try:
            url = f"{self.base_url}/artists/{artist_id}/albums"
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error obteniendo álbumes: {e}")
            return None