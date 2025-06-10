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
import undetected_chromedriver as uc

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
    
    def __init__(self, client_id, client_secret, redirect_uri, cache_dir, cache_duration=24, spotify_client=None, chrome_headless=True):
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
        
        # Nueva configuración para Chrome
        self.chrome_headless = chrome_headless
        
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
    
    def _create_chrome_driver(self):
        """Crear driver de Chrome con opciones que funcionan"""
        try:
            options = uc.ChromeOptions()
            
            if self.chrome_headless:
                options.add_argument('--headless=new')
                print("Chrome ejecutándose en modo headless")
            else:
                print("Chrome ejecutándose en modo visible")
            
            # Opciones básicas que funcionan
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--no-first-run')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            options.add_argument('--window-size=1920,1080')
            
            if not self.chrome_headless:
                options.add_argument('--start-maximized')
            
            # COMENTAR estas líneas que causan problemas
            #options.add_experimental_option('excludeSwitches', ['enable-logging'])
            #options.add_experimental_option('useAutomationExtension', False)
            
            print("Creando driver de Chrome...")
            driver = uc.Chrome(options=options, version_main=None)
            
            driver.set_page_load_timeout(90)
            driver.implicitly_wait(15)
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✅ Driver de Chrome creado exitosamente")
            return driver
            
        except Exception as e:
            print(f"❌ Error creando driver de Chrome: {e}")
            raise



    def _wait_for_page_load(self, driver, timeout=30):
        """Esperar carga de página de manera simple y robusta"""
        try:
            print("⏳ Esperando carga de página...")
            
            # Esperar a que el estado de la página sea 'complete'
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            print("✅ Página base cargada")
            
            # Esperar un poco más para contenido dinámico
            time.sleep(5)
            
            # Verificar si hay elementos básicos de Spotify
            try:
                wait = WebDriverWait(driver, 10)
                # Buscar cualquier elemento que indique que es una página de Spotify
                wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'encore') or contains(@data-testid, 'spotify') or contains(text(), 'Spotify')]")))
                print("✅ Elementos de Spotify detectados")
            except:
                print("⚠️ Elementos específicos de Spotify no detectados, pero continuando...")
            
            return True
            
        except Exception as e:
            print(f"⚠️ Timeout esperando carga de página: {e}")
            print("Continuando de todas formas...")
            return False

    def _handle_spotify_cookie_banner(self, driver):
        """Manejar banner de cookies de Spotify automáticamente"""
        try:
            # Selectores comunes para el banner de cookies
            cookie_selectors = [
                "#onetrust-accept-btn-handler",
                "[id*='accept']",
                "[data-testid*='accept']",
                "button[id*='cookie']",
                ".accept-cookies",
                "[aria-label*='Accept']"
            ]
            
            for selector in cookie_selectors:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    element.click()
                    print(f"Banner de cookies cerrado usando selector: {selector}")
                    time.sleep(1)
                    return True
                except:
                    continue
            
            print("No se encontró banner de cookies o ya fue cerrado")
            return False
            
        except Exception as e:
            print(f"Error manejando banner de cookies: {e}")
            return False

    def _scroll_to_load_content(self, driver):
        """Hacer scroll para cargar contenido dinámico"""
        try:
            # Obtener altura inicial
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            scroll_attempts = 0
            max_scrolls = 3  # Limitar scrolls para no sobrecargar
            
            while scroll_attempts < max_scrolls:
                # Scroll hacia abajo
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Esperar a que cargue contenido
                time.sleep(2)
                
                # Calcular nueva altura
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    break
                    
                last_height = new_height
                scroll_attempts += 1
            
            # Volver al inicio
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            print(f"Completados {scroll_attempts} scrolls para cargar contenido")
            
        except Exception as e:
            print(f"Error haciendo scroll: {e}")



    def _simple_element_finder(self, driver, artist_name):
        """Buscador de elementos simplificado y debug"""
        try:
            print(f"🔍 Buscando conciertos para {artist_name}...")
            
            # Primero, verificar que la página se haya cargado correctamente
            current_url = driver.current_url
            print(f"📍 URL actual: {current_url}")
            
            # Verificar si estamos en la página correcta
            if "/concerts" not in current_url:
                print("⚠️ No estamos en la página de conciertos")
                return []
            
            # Obtener título de la página
            page_title = driver.title
            print(f"📄 Título de página: {page_title}")
            
            # Buscar elementos de manera muy simple
            print("🔍 Buscando elementos...")
            
            # 1. Buscar enlaces que contengan "/concert/"
            concert_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/concert/')]")
            print(f"🔗 Enlaces de conciertos encontrados: {len(concert_links)}")
            
            # 2. Buscar elementos que contengan fechas
            date_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '2025') or contains(text(), '2024')]")
            print(f"📅 Elementos con fechas encontrados: {len(date_elements)}")
            
            # 3. Buscar elementos que contengan nombres de venues
            venue_keywords = ['Arena', 'Stadium', 'Hall', 'Centre', 'Center', 'Theatre', 'Theater', 'Palau', 'Dome']
            venue_elements = []
            for keyword in venue_keywords:
                elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                venue_elements.extend(elements)
            print(f"🏟️ Elementos con venues encontrados: {len(venue_elements)}")
            
            # 4. Si no hay elementos específicos, analizar el contenido de la página
            if not concert_links and not date_elements and not venue_elements:
                print("❌ No se encontraron elementos específicos")
                print("📝 Analizando contenido de página...")
                
                # Obtener todo el texto de la página
                page_text = driver.find_element(By.TAG_NAME, "body").text
                print(f"📄 Longitud del texto de página: {len(page_text)} caracteres")
                
                # Mostrar las primeras líneas del texto
                lines = page_text.split('\n')[:20]
                print("📋 Primeras líneas de la página:")
                for i, line in enumerate(lines):
                    if line.strip():
                        print(f"   {i+1}: {line.strip()[:100]}")
                
                # Buscar patrones en el texto
                if artist_name.lower() in page_text.lower():
                    print(f"✅ Nombre del artista '{artist_name}' encontrado en la página")
                else:
                    print(f"❌ Nombre del artista '{artist_name}' NO encontrado en la página")
                
                # Buscar indicaciones de "no concerts"
                no_concert_phrases = ['no upcoming', 'no events', 'no concerts', 'no shows']
                for phrase in no_concert_phrases:
                    if phrase in page_text.lower():
                        print(f"ℹ️ Frase encontrada: '{phrase}' - puede que no haya conciertos")
            
            # Combinar todos los elementos encontrados
            all_elements = []
            all_elements.extend(concert_links)
            all_elements.extend(date_elements)
            all_elements.extend(venue_elements)
            
            # Eliminar duplicados
            unique_elements = list(set(all_elements))
            
            print(f"✅ Total de elementos únicos encontrados: {len(unique_elements)}")
            return unique_elements
            
        except Exception as e:
            print(f"❌ Error en búsqueda simple: {e}")
            return []



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
        """Método principal actualizado - usar el método integrado"""
        return self.scrape_artist_concerts_integrated(artist_url, artist_name)


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

    def _handle_captcha_detection(self, driver):
        """
        Detectar y manejar captchas automáticamente
        
        Args:
            driver: Instancia del WebDriver
            
        Returns:
            bool: True si se detectó captcha, False si no
        """
        captcha_selectors = [
            '[data-testid="captcha"]',
            'iframe[src*="recaptcha"]',
            '.captcha-container',
            '#captcha',
            '[id*="captcha"]',
            '[class*="captcha"]',
            'iframe[src*="hcaptcha"]'
        ]
        
        has_captcha = False
        
        for selector in captcha_selectors:
            try:
                captcha_element = driver.find_element(By.CSS_SELECTOR, selector)
                if captcha_element.is_displayed():
                    print(f"Captcha detectado con selector: {selector}")
                    has_captcha = True
                    break
            except:
                continue
        
        # También verificar por texto indicativo de captcha
        try:
            page_text = driver.page_source.lower()
            captcha_indicators = ['captcha', 'robot', 'verify', 'human']
            
            for indicator in captcha_indicators:
                if indicator in page_text and ('verify' in page_text or 'human' in page_text):
                    print(f"Posible captcha detectado por texto: {indicator}")
                    has_captcha = True
                    break
        except:
            pass
        
        return has_captcha

    def _extract_concert_link(self, element):
        """Extraer enlace del concierto de un elemento"""
        try:
            # Buscar enlace directo
            concert_link = element.get_attribute('href')
            if concert_link and '/concert/' in concert_link:
                return concert_link
            
            # Buscar en elementos hijos
            links = element.find_elements(By.TAG_NAME, 'a')
            for link in links:
                href = link.get_attribute('href')
                if href and '/concert/' in href:
                    return href
            
            # Buscar por selectores específicos
            link_selectors = [
                'a[href*="/concert/"]',
                '[data-testid*="concert"] a',
                '.concert-link',
                '[role="link"]'
            ]
            
            for selector in link_selectors:
                try:
                    link_element = element.find_element(By.CSS_SELECTOR, selector)
                    href = link_element.get_attribute('href')
                    if href and '/concert/' in href:
                        return href
                except:
                    continue
            
            return None
        except Exception as e:
            print(f"Error extrayendo enlace: {e}")
            return None

    def _extract_basic_concert_info(self, element, artist_name):
        """Extraer información básica del concierto desde un elemento"""
        concert_data = {
            'artist': artist_name,
            'name': 'Concert',
            'venue': '',
            'city': '',
            'date': '',
            'time': '',
            'image': '',
            'url': '',
            'source': 'Spotify'
        }
        
        try:
            # Buscar fecha usando múltiples estrategias
            date_selectors = [
                'time',
                '[datetime]',
                '.date',
                '[data-testid*="date"]',
                '.encore-text-body-medium-bold'
            ]
            
            for selector in date_selectors:
                try:
                    date_element = element.find_element(By.CSS_SELECTOR, selector)
                    
                    # Intentar obtener datetime attribute
                    datetime_value = date_element.get_attribute('datetime')
                    if datetime_value:
                        concert_data['date'] = datetime_value[:10] if len(datetime_value) >= 10 else datetime_value
                        break
                    
                    # Si no hay datetime, usar el texto
                    date_text = date_element.text.strip()
                    if date_text and any(char.isdigit() for char in date_text):
                        concert_data['date'] = self._parse_date_text(date_text)
                        break
                except:
                    continue
            
            # Buscar lugar/venue
            venue_selectors = [
                '[data-testid="event-venue"]',
                '.venue',
                '.location',
                '.encore-text-body-medium:not(.encore-text-body-medium-bold)',
                'h3', 'h4'
            ]
            
            for selector in venue_selectors:
                try:
                    venue_element = element.find_element(By.CSS_SELECTOR, selector)
                    venue_text = venue_element.text.strip()
                    if venue_text and len(venue_text) > 1:
                        concert_data['venue'] = venue_text
                        break
                except:
                    continue
            
            # Buscar ciudad
            city_selectors = [
                '.city',
                '.location-city',
                '[data-testid*="city"]',
                '.encore-text-body-small'
            ]
            
            for selector in city_selectors:
                try:
                    city_element = element.find_element(By.CSS_SELECTOR, selector)
                    city_text = city_element.text.strip()
                    if city_text and len(city_text) > 1:
                        concert_data['city'] = city_text
                        break
                except:
                    continue
            
            # Si no encontramos ciudad específica, intentar extraer de venue o de todos los textos
            if not concert_data['city']:
                all_texts = element.find_elements(By.CSS_SELECTOR, '*')
                for text_element in all_texts:
                    text = text_element.text.strip()
                    # Buscar patrones de ciudad (texto que no sea fecha ni número)
                    if text and len(text) > 2 and not text.isdigit() and ',' in text:
                        concert_data['city'] = text.split(',')[-1].strip()
                        break
            
            # Buscar hora
            time_selectors = [
                '.time',
                '[data-testid*="time"]',
                '.encore-text-body-small'
            ]
            
            for selector in time_selectors:
                try:
                    time_element = element.find_element(By.CSS_SELECTOR, selector)
                    time_text = time_element.text.strip()
                    if ':' in time_text:
                        concert_data['time'] = time_text
                        break
                except:
                    continue
            
            # Actualizar nombre del concierto
            if concert_data['venue']:
                concert_data['name'] = f"{artist_name} at {concert_data['venue']}"
            
        except Exception as e:
            print(f"Error extrayendo información básica: {e}")
        
        return concert_data

    def _parse_date_text(self, date_text):
        """Convertir texto de fecha a formato ISO"""
        try:
            import re
            from datetime import datetime
            
            # Buscar patrones de fecha comunes
            patterns = [
                r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',  # "15 Dec 2024"
                r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',  # "Dec 15, 2024"
                r'(\d{4})-(\d{1,2})-(\d{1,2})',  # "2024-12-15"
                r'(\d{1,2})/(\d{1,2})/(\d{4})'   # "15/12/2024"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, date_text)
                if match:
                    try:
                        if pattern == patterns[0]:  # "15 Dec 2024"
                            day, month, year = match.groups()
                            date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
                        elif pattern == patterns[1]:  # "Dec 15, 2024"
                            month, day, year = match.groups()
                            date_obj = datetime.strptime(f"{month} {day} {year}", "%b %d %Y")
                        elif pattern == patterns[2]:  # "2024-12-15"
                            year, month, day = match.groups()
                            date_obj = datetime(int(year), int(month), int(day))
                        elif pattern == patterns[3]:  # "15/12/2024"
                            day, month, year = match.groups()
                            date_obj = datetime(int(year), int(month), int(day))
                        
                        return date_obj.strftime("%Y-%m-%d")
                    except:
                        continue
            
            return date_text  # Devolver texto original si no se puede parsear
        except:
            return date_text

    def _get_concert_details_safe(self, driver, concert_link):
        """Obtener detalles del concierto de manera segura"""
        try:
            # Abrir en nueva pestaña
            driver.execute_script("window.open(arguments[0]);", concert_link)
            driver.switch_to.window(driver.window_handles[1])
            
            # Esperar carga
            time.sleep(3)
            
            # Extraer detalles
            details = self._extract_concert_details(driver)
            
            # Cerrar pestaña y volver
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            
            return details
        except Exception as e:
            print(f"Error obteniendo detalles del concierto: {e}")
            try:
                # Asegurar que volvemos a la pestaña original
                if len(driver.window_handles) > 1:
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except:
                pass
            return {}

    def _wait_for_user_captcha_resolution(self, driver, max_wait_time=60):
        """Esperar resolución automática del captcha sin interacción del usuario"""
        print(f"Esperando resolución automática del captcha...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            if not self._handle_captcha_detection(driver):
                print("Captcha resuelto o página cargada correctamente")
                return True
            
            time.sleep(2)  # Verificar cada 2 segundos
        
        print("Tiempo de espera agotado - continuando con el scraping")
        return False



    def _convert_css_to_xpath(self, css_selector, artist_name):
        """Convertir selectores CSS con pseudo-clases a XPath"""
        if ':has-text' in css_selector:
            if 'Santana' in css_selector:
                return f"//div[contains(text(), '{artist_name}')]"
            elif 'venue' in css_selector:
                return "//div[contains(@class, 'encore-text') and (contains(text(), 'Arena') or contains(text(), 'Stadium') or contains(text(), 'Hall'))]"
        elif ':contains' in css_selector:
            if '2025' in css_selector:
                return "//*[contains(@class, 'text') and (contains(text(), '2025') or contains(text(), '2024'))]"
        
        return css_selector

    def _find_concerts_by_text_content(self, driver, artist_name):
        """Buscar conciertos por contenido de texto como método de fallback"""
        try:
            # Buscar todos los elementos que contengan fechas futuras
            date_patterns = ['2025', '2024', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            potential_elements = []
            
            for pattern in date_patterns:
                xpath = f"//*[contains(text(), '{pattern}')]"
                elements = driver.find_elements(By.XPATH, xpath)
                potential_elements.extend(elements)
            
            # Filtrar elementos que probablemente sean conciertos
            concert_elements = []
            venue_keywords = ['Arena', 'Stadium', 'Hall', 'Center', 'Theatre', 'Theater', 
                            'Palau', 'Auditorium', 'Dome', 'Coliseum']
            
            for element in potential_elements:
                try:
                    # Buscar en el elemento padre y hermanos
                    parent = element.find_element(By.XPATH, '..')
                    parent_text = parent.text.lower()
                    
                    # Si contiene palabras clave de venues, es probable que sea un concierto
                    if any(keyword.lower() in parent_text for keyword in venue_keywords):
                        if parent not in concert_elements:
                            concert_elements.append(parent)
                            
                except:
                    continue
            
            print(f"Encontrados {len(concert_elements)} elementos potenciales por contenido de texto")
            return concert_elements
            
        except Exception as e:
            print(f"Error buscando por texto: {e}")
            return []

    def _extract_concert_info_robust(self, element, artist_name):
        """Extraer información de concierto de manera robusta"""
        concert_data = {
            'artist': artist_name,
            'name': 'Concert',
            'venue': '',
            'city': '',
            'date': '',
            'time': '',
            'image': '',
            'url': '',
            'source': 'Spotify'
        }
        
        try:
            # Obtener todo el texto del elemento para análisis
            element_text = element.text.strip()
            
            # Buscar venue (palabras que terminen en keywords comunes)
            venue_keywords = ['Arena', 'Stadium', 'Hall', 'Center', 'Centre', 'Theatre', 
                            'Theater', 'Palau', 'Auditorium', 'Dome', 'Coliseum', 'Palace']
            
            for keyword in venue_keywords:
                if keyword in element_text:
                    # Encontrar la línea que contiene el venue
                    lines = element_text.split('\n')
                    for line in lines:
                        if keyword in line:
                            concert_data['venue'] = line.strip()
                            break
                    break
            
            # Buscar fechas usando expresiones regulares
            import re
            date_patterns = [
                r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(2024|2025)',
                r'(2024|2025)-(\d{1,2})-(\d{1,2})',
                r'(\d{1,2})/(\d{1,2})/(2024|2025)'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, element_text, re.IGNORECASE)
                if match:
                    concert_data['date'] = match.group(0)
                    break
            
            # Buscar ciudad (generalmente líneas con comas)
            lines = element_text.split('\n')
            for line in lines:
                if ',' in line and len(line.split(',')) >= 2:
                    # La ciudad suele estar después de la coma
                    parts = line.split(',')
                    if len(parts) >= 2:
                        concert_data['city'] = parts[-1].strip()
                        break
            
            # Buscar URL del concierto
            try:
                links = element.find_elements(By.TAG_NAME, 'a')
                for link in links:
                    href = link.get_attribute('href')
                    if href and '/concert/' in href:
                        concert_data['url'] = href
                        break
            except:
                pass
            
            # Mejorar el nombre del concierto
            if concert_data['venue']:
                concert_data['name'] = f"{artist_name} at {concert_data['venue']}"
            
            return concert_data
            
        except Exception as e:
            print(f"Error extrayendo información robusta: {e}")
            return concert_data

    def _analyze_page_structure(self, driver):
        """Analizar estructura de página para depuración"""
        try:
            print("\n=== ANÁLISIS DE ESTRUCTURA DE PÁGINA ===")
            
            # Buscar elementos con data-testid
            testid_elements = driver.find_elements(By.XPATH, "//*[@data-testid]")
            print(f"Elementos con data-testid: {len(testid_elements)}")
            
            testids = set()
            for elem in testid_elements[:10]:  # Limitar a 10 para no saturar
                testid = elem.get_attribute('data-testid')
                if testid:
                    testids.add(testid)
            
            print(f"Data-testids encontrados: {sorted(testids)}")
            
            # Buscar elementos con clases encore
            encore_elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'encore')]")
            print(f"Elementos con clase 'encore': {len(encore_elements)}")
            
            # Buscar enlaces
            links = driver.find_elements(By.TAG_NAME, 'a')
            concert_links = [link.get_attribute('href') for link in links 
                            if link.get_attribute('href') and '/concert/' in link.get_attribute('href')]
            print(f"Enlaces de conciertos encontrados: {len(concert_links)}")
            
            # Buscar elementos con fechas
            date_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '2025') or contains(text(), '2024')]")
            print(f"Elementos con fechas: {len(date_elements)}")
            
            print("=== FIN ANÁLISIS ===\n")
            
        except Exception as e:
            print(f"Error analizando estructura: {e}")


    def scrape_artist_concerts_integrated(self, artist_url, artist_name):
        """Scraper que analiza el contenido real de Spotify"""
        match = re.search(r'/artist/([^/]+)', artist_url)
        if not match:
            return [], "URL de artista inválida"
        
        artist_id = match.group(1)
        concerts_url = f"https://open.spotify.com/artist/{artist_id}/concerts"
        
        print(f"🎵 Iniciando scraping REAL para: {artist_name}")
        print(f"🔗 URL objetivo: {concerts_url}")
        
        driver = None
        try:
            driver = self._create_chrome_driver()
            driver.get(concerts_url)
            time.sleep(10)  # Espera para carga completa
            
            current_url = driver.current_url
            page_title = driver.title
            
            print(f"📍 URL actual: {current_url}")
            print(f"📄 Título: {page_title}")
            
            # Verificar que estamos en la página correcta
            if "/concerts" not in current_url:
                return [], f"La URL no lleva a una página de conciertos: {current_url}"
            
            # Analizar el contenido real de la página
            print("🔍 Analizando contenido real de la página...")
            
            # Obtener todo el texto
            body_text = driver.find_element(By.TAG_NAME, "body").text
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            
            print(f"📄 Líneas de texto encontradas: {len(lines)}")
            
            # Buscar patrones de conciertos en el texto
            concerts = []
            concert_info = {}
            
            # Analizar línea por línea buscando patrones
            for i, line in enumerate(lines):
                print(f"Línea {i+1}: {line}")
                
                # Buscar venues (lugares con palabras clave)
                venue_keywords = ['Arena', 'Stadium', 'Hall', 'Centre', 'Center', 'Theatre', 'Theater', 
                                'Palau', 'Dome', 'Coliseum', 'Palace', 'Auditorium']
                
                for keyword in venue_keywords:
                    if keyword in line:
                        print(f"  🏟️ VENUE encontrado: {line}")
                        concert_info = {'venue': line, 'line_number': i+1}
                        
                        # Buscar información adicional en líneas cercanas
                        context_lines = lines[max(0, i-2):min(len(lines), i+3)]
                        print(f"  📋 Contexto: {context_lines}")
                        
                        # Buscar fechas en el contexto
                        for context_line in context_lines:
                            # Buscar años
                            if any(year in context_line for year in ['2024', '2025']):
                                concert_info['date_line'] = context_line
                                print(f"  📅 FECHA encontrada: {context_line}")
                            
                            # Buscar ciudades (líneas con comas)
                            if ',' in context_line and context_line != line:
                                concert_info['city_line'] = context_line
                                print(f"  🌆 CIUDAD encontrada: {context_line}")
                        
                        # Crear concierto si tenemos venue
                        if concert_info.get('venue'):
                            concert = {
                                'artist': artist_name,
                                'name': f"{artist_name} Concert",
                                'venue': concert_info['venue'],
                                'city': concert_info.get('city_line', '').split(',')[-1].strip() if concert_info.get('city_line') else '',
                                'date': concert_info.get('date_line', ''),
                                'time': '',
                                'image': '',
                                'url': current_url,
                                'source': 'Spotify'
                            }
                            concerts.append(concert)
                            print(f"  ✅ CONCIERTO CREADO: {concert}")
                        
                        concert_info = {}  # Reset para el siguiente
            
            # Si no encontramos venues por keywords, buscar otros patrones
            if not concerts:
                print("🔍 No se encontraron venues con keywords. Buscando otros patrones...")
                
                # Buscar patrones de fecha primero
                date_lines = []
                for i, line in enumerate(lines):
                    if any(year in line for year in ['2024', '2025']) or \
                    any(month in line.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                                            'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                        date_lines.append((i, line))
                        print(f"  📅 Línea con fecha: {line}")
                
                # Para cada línea con fecha, buscar venues cerca
                for date_i, date_line in date_lines:
                    context_start = max(0, date_i - 3)
                    context_end = min(len(lines), date_i + 4)
                    context = lines[context_start:context_end]
                    
                    print(f"  🔍 Analizando contexto de fecha '{date_line}':")
                    for ctx_line in context:
                        print(f"    - {ctx_line}")
                        
                        # Buscar líneas que podrían ser venues (más de 10 caracteres, sin ser obvios elementos de UI)
                        ui_keywords = ['saltar', 'contenido', 'premium', 'descargar', 'registr', 'sesión', 
                                    'biblioteca', 'lista', 'playlist', 'album', 'artist', 'song']
                        
                        if (len(ctx_line) > 10 and 
                            not any(ui_word in ctx_line.lower() for ui_word in ui_keywords) and
                            ctx_line != date_line):
                            
                            print(f"    🏟️ POSIBLE VENUE: {ctx_line}")
                            
                            concert = {
                                'artist': artist_name,
                                'name': f"{artist_name} Concert",
                                'venue': ctx_line,
                                'city': '',
                                'date': date_line,
                                'time': '',
                                'image': '',
                                'url': current_url,
                                'source': 'Spotify'
                            }
                            concerts.append(concert)
            
            # Verificar si hay mensaje de "no concerts"
            no_concert_indicators = ['no upcoming', 'no events', 'no concerts', 'no shows', 
                                'This artist has no upcoming events']
            
            for indicator in no_concert_indicators:
                if indicator.lower() in body_text.lower():
                    print(f"ℹ️ Mensaje encontrado: '{indicator}' - No hay conciertos programados")
                    return [], f"No hay conciertos programados para {artist_name}"
            
            # Debug: Guardar archivos
            if not self.chrome_headless:
                try:
                    screenshot_path = self.cache_dir / f"real_debug_{artist_name.replace(' ', '_')}.png"
                    driver.save_screenshot(str(screenshot_path))
                    print(f"📸 Screenshot: {screenshot_path}")
                    
                    html_path = self.cache_dir / f"real_page_{artist_name.replace(' ', '_')}.html"
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    print(f"💾 HTML: {html_path}")
                    
                    # Guardar análisis de texto
                    analysis_path = self.cache_dir / f"text_analysis_{artist_name.replace(' ', '_')}.txt"
                    with open(analysis_path, 'w', encoding='utf-8') as f:
                        f.write(f"ANÁLISIS DE TEXTO PARA: {artist_name}\n")
                        f.write(f"URL: {current_url}\n")
                        f.write(f"Título: {page_title}\n\n")
                        f.write("TODAS LAS LÍNEAS:\n")
                        for i, line in enumerate(lines):
                            f.write(f"{i+1:3d}: {line}\n")
                    print(f"📝 Análisis: {analysis_path}")
                    
                except Exception as e:
                    print(f"❌ Error guardando debug: {e}")
            
            # Guardar en caché si hay resultados
            if concerts:
                try:
                    cache_file = self._get_cache_file_path(f"spotify_concerts_{artist_name}")
                    self._save_to_cache(cache_file, concerts)
                except Exception as e:
                    print(f"⚠️ Error guardando caché: {e}")
            
            result_msg = f"Encontrados {len(concerts)} conciertos reales para {artist_name}"
            print(f"🎉 {result_msg}")
            
            return concerts, result_msg
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return [], f"Error en scraping: {str(e)}"
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _find_concert_elements_comprehensive(self, driver, artist_name):
        """Búsqueda comprehensiva de elementos de conciertos"""
        concert_elements = []
        
        # Estrategia 1: Selectores específicos de conciertos
        specific_selectors = [
            '[data-testid*="concert"]',
            '[data-testid*="event"]',
            '[data-testid*="show"]',
            'a[href*="/concert/"]',
            '[aria-label*="concert"]'
        ]
        
        for selector in specific_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✅ Encontrados {len(elements)} elementos con selector específico: {selector}")
                    concert_elements.extend(elements)
            except Exception as e:
                print(f"❌ Error con selector {selector}: {e}")
        
        if concert_elements:
            return list(set(concert_elements))  # Eliminar duplicados
        
        # Estrategia 2: Buscar por contenido de texto
        print("🔍 Estrategia 2: Búsqueda por contenido de texto...")
        text_elements = self._find_by_text_patterns(driver, artist_name)
        if text_elements:
            concert_elements.extend(text_elements)
        
        if concert_elements:
            return list(set(concert_elements))
        
        # Estrategia 3: Buscar por estructura de página
        print("🔍 Estrategia 3: Análisis de estructura...")
        structural_elements = self._find_by_page_structure(driver)
        if structural_elements:
            concert_elements.extend(structural_elements)
        
        return list(set(concert_elements))

    def _find_by_text_patterns(self, driver, artist_name):
        """Buscar elementos por patrones de texto"""
        elements = []
        
        # Patrones de texto que indican conciertos
        patterns = [
            # Fechas
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}',
            r'\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
            r'\b(2024|2025)\b',
            # Venues
            r'\b(Arena|Stadium|Hall|Centre|Center|Theatre|Theater|Palau|Dome)\b',
            # Ciudades comunes
            r'\b(London|Paris|Madrid|Barcelona|Berlin|Amsterdam|Rome)\b'
        ]
        
        for pattern in patterns:
            try:
                xpath = f"//*[re:match(text(), '{pattern}', 'i')]"
                # Como XPath no soporta regex por defecto, usar un enfoque diferente
                xpath_simple = f"//*[contains(text(), '2025') or contains(text(), '2024') or contains(text(), 'Arena') or contains(text(), 'Stadium')]"
                
                pattern_elements = driver.find_elements(By.XPATH, xpath_simple)
                
                for elem in pattern_elements:
                    # Buscar el contenedor padre que podría ser un elemento de concierto
                    try:
                        parent = elem.find_element(By.XPATH, '../..')  # Subir 2 niveles
                        if parent not in elements:
                            elements.append(parent)
                    except:
                        if elem not in elements:
                            elements.append(elem)
                            
            except Exception as e:
                print(f"Error buscando patrón {pattern}: {e}")
        
        print(f"Encontrados {len(elements)} elementos por patrones de texto")
        return elements

    def _find_by_page_structure(self, driver):
        """Buscar elementos por estructura de página"""
        elements = []
        
        try:
            # Buscar contenedores que podrían contener conciertos
            container_selectors = [
                '[role="grid"]',
                '[role="list"]',
                '.grid',
                '.list',
                '[data-encore-id="container"]',
                '[class*="container"]',
                '[class*="grid"]'
            ]
            
            for selector in container_selectors:
                try:
                    containers = driver.find_elements(By.CSS_SELECTOR, selector)
                    for container in containers:
                        # Buscar elementos hijos que podrían ser conciertos
                        children = container.find_elements(By.XPATH, './*')
                        
                        # Filtrar elementos que tengan contenido relevante
                        for child in children:
                            text = child.text.strip()
                            if len(text) > 10 and ('2024' in text or '2025' in text or 
                                                any(venue in text for venue in ['Arena', 'Stadium', 'Hall', 'Centre'])):
                                elements.append(child)
                                
                except Exception as e:
                    print(f"Error con contenedor {selector}: {e}")
        
        except Exception as e:
            print(f"Error buscando por estructura: {e}")
        
        print(f"Encontrados {len(elements)} elementos por estructura")
        return elements

    def _process_concert_elements(self, elements, artist_name, driver):
        """Procesar elementos encontrados para extraer información de conciertos"""
        concerts = []
        
        for i, element in enumerate(elements):
            try:
                print(f"📝 Procesando elemento {i+1}/{len(elements)}...")
                
                # Extraer información básica
                concert_data = self._extract_concert_info_robust(element, artist_name)
                
                # Intentar obtener información adicional si hay enlace
                if concert_data.get('url'):
                    additional_info = self._get_additional_concert_info(driver, concert_data['url'])
                    if additional_info:
                        concert_data.update(additional_info)
                
                concerts.append(concert_data)
                
            except Exception as e:
                print(f"❌ Error procesando elemento {i+1}: {e}")
                continue
        
        return concerts

    def _validate_concerts(self, concerts):
        """Validar y limpiar lista de conciertos"""
        valid_concerts = []
        
        for concert in concerts:
            # Criterios de validación
            if (concert.get('venue') and len(concert['venue']) > 2 and
                (concert.get('date') or concert.get('city'))):
                
                # Limpiar datos
                concert['venue'] = concert['venue'].strip()
                concert['city'] = concert.get('city', '').strip()
                concert['date'] = concert.get('date', '').strip()
                
                # Evitar duplicados
                if not any(v.get('venue') == concert['venue'] and 
                        v.get('date') == concert['date'] for v in valid_concerts):
                    valid_concerts.append(concert)
        
        return valid_concerts

    def _debug_page_comprehensive(self, driver, artist_name):
        """Debug comprehensivo de la página"""
        try:
            print("\n🔍 === DEBUG COMPREHENSIVO ===")
            
            # Screenshot
            screenshot_path = self.cache_dir / f"debug_comprehensive_{artist_name.replace(' ', '_')}.png"
            driver.save_screenshot(str(screenshot_path))
            print(f"📸 Screenshot: {screenshot_path}")
            
            # Guardar HTML
            html_path = self.cache_dir / f"debug_page_{artist_name.replace(' ', '_')}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"💾 HTML guardado: {html_path}")
            
            # Análisis de elementos
            self._analyze_page_structure(driver)
            
            print("=== FIN DEBUG ===\n")
            
        except Exception as e:
            print(f"Error en debug: {e}")

    def _debug_error_state(self, driver, artist_name, error):
        """Debug específico para estados de error"""
        try:
            timestamp = int(time.time())
            screenshot_path = self.cache_dir / f"error_{timestamp}_{artist_name.replace(' ', '_')}.png"
            driver.save_screenshot(str(screenshot_path))
            print(f"📸 Error screenshot: {screenshot_path}")
            
            # Logs del navegador
            try:
                logs = driver.get_log('browser')
                if logs:
                    log_path = self.cache_dir / f"browser_logs_{timestamp}.txt"
                    with open(log_path, 'w') as f:
                        for log in logs:
                            f.write(f"{log['level']}: {log['message']}\n")
                    print(f"📝 Browser logs: {log_path}")
            except:
                print("⚠️ No se pudieron obtener logs del navegador")
            
        except Exception as e:
            print(f"Error en debug de error: {e}")