import requests
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import base64
import webbrowser
import urllib.parse
from threading import Timer
import http.server
import socketserver

class SpotifyAuthHandler(http.server.SimpleHTTPRequestHandler):
    """Handler para recibir el código de autorización de Spotify"""
    
    def __init__(self, request, client_address, server, auth_code_callback):
        self.auth_code_callback = auth_code_callback
        super().__init__(request, client_address, server)
    
    def do_GET(self):
        """Procesar solicitud GET con código de autorización"""
        query = urllib.parse.urlparse(self.path).query
        query_components = dict(qc.split("=") for qc in query.split("&") if "=" in qc)
        
        if "code" in query_components:
            # Obtener código de autorización y llamar al callback
            auth_code = query_components["code"]
            self.auth_code_callback(auth_code)
            
            # Enviar página de éxito
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
            # Si no hay código, enviar error
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
        
        # Señalar al servidor que debe cerrarse después de esta solicitud
        self.server.server_close()
        return

class SpotifyService:
    """Servicio para interactuar con la API de Spotify con soporte de caché"""
    
    def __init__(self, client_id, client_secret, redirect_uri, cache_dir, cache_duration=24):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = "https://api.spotify.com/v1"
        self.auth_url = "https://accounts.spotify.com/api/token"
        self.authorize_url = "https://accounts.spotify.com/authorize"
        
        self.cache_dir = Path(cache_dir)
        self.cache_duration = cache_duration  # horas
        self.access_token = None
        self.token_expiry = None
        
        # Crear directorio de caché si no existe
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Intentar cargar token guardado
        self._load_saved_token()
    
    def _load_saved_token(self):
        """Cargar token guardado si existe y es válido"""
        token_file = self.cache_dir / "spotify_token.json"
        
        if token_file.exists():
            try:
                with open(token_file, "r") as f:
                    token_data = json.load(f)
                
                expiry_time = datetime.fromisoformat(token_data.get("expiry", ""))
                
                # Verificar si el token aún es válido (menos 5 minutos para margen)
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
    
    def get_client_credentials(self):
        """Obtener token usando Client Credentials Flow (sin usuario)"""
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
            
            # Establecer tiempo de expiración (normalmente 1 hora)
            expires_in = token_info.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            # Guardar token
            self._save_token()
            
            return self.access_token
        except requests.exceptions.RequestException as e:
            print(f"Error obteniendo token: {e}")
            return None
    
    def authorize_user_flow(self, callback_function=None):
        """Iniciar flujo de autorización de usuario (Authorization Code Flow)"""
        # Generar URL de autorización
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "user-follow-read user-read-email"  # Scopes necesarios
        }
        
        auth_url = f"{self.authorize_url}?{urllib.parse.urlencode(params)}"
        
        # Abrir navegador para autorización
        webbrowser.open(auth_url)
        
        # Iniciar servidor local para recibir la redirección
        redirect_port = int(self.redirect_uri.split(":")[-1]) if "localhost" in self.redirect_uri else 8000
        
        def create_handler(*args, **kwargs):
            return SpotifyAuthHandler(*args, **kwargs, auth_code_callback=self._handle_auth_code)
        
        self.auth_code = None
        self.auth_callback = callback_function
        
        # Iniciar servidor en un hilo separado
        httpd = socketserver.TCPServer(("", redirect_port), create_handler)
        server_thread = Timer(0.1, httpd.handle_request)
        server_thread.daemon = True
        server_thread.start()
        
        return True
    
    def _handle_auth_code(self, auth_code):
        """Procesar código de autorización y obtener token"""
        self.auth_code = auth_code
        
        # Intercambiar código por token
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(self.auth_url, headers=headers, data=data)
            response.raise_for_status()
            
            token_info = response.json()
            self.access_token = token_info.get("access_token")
            self.refresh_token = token_info.get("refresh_token")
            
            # Establecer tiempo de expiración
            expires_in = token_info.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            # Guardar token
            token_file = self.cache_dir / "spotify_user_token.json"
            
            token_data = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expiry": self.token_expiry.isoformat()
            }
            
            with open(token_file, "w") as f:
                json.dump(token_data, f)
            
            # Llamar al callback si existe
            if self.auth_callback:
                self.auth_callback(True)
                
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error obteniendo token de usuario: {e}")
            
            # Llamar al callback con error
            if self.auth_callback:
                self.auth_callback(False)
                
            return False
    
    def search_artist(self, name):
        """Buscar un artista por nombre"""
        # Verificar caché primero
        cache_file = self._get_cache_file_path(f"artist_{name}")
        cached_data = self._load_from_cache(cache_file)
        
        if cached_data:
            return cached_data
        
        # Obtener token
        token = self.get_client_credentials()
        if not token:
            return None
        
        # Realizar búsqueda
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
            
            if not artists:
                return None
            
            artist_data = artists[0]
            
            # Guardar en caché
            self._save_to_cache(cache_file, artist_data)
            
            return artist_data
        except requests.exceptions.RequestException as e:
            print(f"Error buscando artista: {e}")
            return None
    
    def get_artist_concerts(self, artist_name, country_code=None):
        """
        Buscar conciertos de un artista usando la API de Spotify
        
        Args:
            artist_name (str): Nombre del artista
            country_code (str, optional): Código de país para filtrar
            
        Returns:
            list: Lista de conciertos encontrados
        """
        # Verificar caché primero
        cache_key = f"concerts_{artist_name}"
        if country_code:
            cache_key += f"_{country_code}"
            
        cache_file = self._get_cache_file_path(cache_key)
        cached_data = self._load_from_cache(cache_file)
        
        if cached_data:
            return cached_data, f"Se encontraron {len(cached_data)} conciertos para {artist_name} (caché)"
        
        # Buscar artista primero
        artist_data = self.search_artist(artist_name)
        if not artist_data:
            return [], f"No se encontró el artista {artist_name} en Spotify"
        
        artist_id = artist_data.get("id")
        
        # Obtener token
        token = self.get_client_credentials()
        if not token:
            return [], "Error de autenticación con Spotify"
        
        # Consultar información del artista para ver si tiene conciertos próximos
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        try:
            # Spotify no proporciona directamente una API para conciertos
            # Pero podemos extraer enlaces externos que podrían tener info
            response = requests.get(f"{self.base_url}/artists/{artist_id}", headers=headers)
            response.raise_for_status()
            
            artist_details = response.json()
            external_urls = artist_details.get("external_urls", {})
            
            # Verificar si hay enlaces a páginas con tours
            concerts = []
            
            # Extraer información de conciertos (esto generalmente requerirá scraping)
            # En este ejemplo, se devuelve info básica
            concert = {
                'artist': artist_name,
                'name': f"Tour {datetime.now().year}",
                'venue': 'Varias localizaciones',
                'city': 'Consultar enlaces',
                'date': datetime.now().strftime("%Y-%m-%d"),
                'time': '',
                'image': artist_details.get("images", [{}])[0].get("url", "") if artist_details.get("images") else '',
                'url': external_urls.get("spotify", "")
            }
            
            concerts.append(concert)
            
            # Guardar en caché
            self._save_to_cache(cache_file, concerts)
            
            return concerts, f"Se encontró información de tour para {artist_name}"
        except requests.exceptions.RequestException as e:
            return [], f"Error en la solicitud: {str(e)}"
    
    def get_user_followed_artists(self):
        """Obtener lista de artistas que sigue el usuario"""
        # Verificar si tenemos token de usuario
        user_token_file = self.cache_dir / "spotify_user_token.json"
        
        if not user_token_file.exists():
            # Iniciar flujo de autorización
            return None, "Es necesario autorizar el acceso a tu cuenta de Spotify"
        
        try:
            with open(user_token_file, "r") as f:
                token_data = json.load(f)
            
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expiry = datetime.fromisoformat(token_data.get("expiry", ""))
            
            # Verificar si el token ha expirado
            if datetime.now() >= expiry:
                # Refrescar token
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
                
                response = requests.post(self.auth_url, headers=headers, data=data)
                response.raise_for_status()
                
                new_token_info = response.json()
                access_token = new_token_info.get("access_token")
                
                # Actualizar refresh_token si se proporciona uno nuevo
                if "refresh_token" in new_token_info:
                    refresh_token = new_token_info.get("refresh_token")
                
                # Actualizar tiempo de expiración
                expires_in = new_token_info.get("expires_in", 3600)
                expiry = datetime.now() + timedelta(seconds=expires_in)
                
                # Guardar token actualizado
                token_data = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expiry": expiry.isoformat()
                }
                
                with open(user_token_file, "w") as f:
                    json.dump(token_data, f)
            
            # Consultar artistas seguidos
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            all_artists = []
            next_url = f"{self.base_url}/me/following?type=artist&limit=50"
            
            while next_url:
                response = requests.get(next_url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                artists = data.get("artists", {})
                
                all_artists.extend(artists.get("items", []))
                
                # Verificar si hay más páginas
                next_url = artists.get("next")
            
            # Extraer nombres de artistas
            artist_names = [artist.get("name") for artist in all_artists]
            
            return artist_names, f"Se encontraron {len(artist_names)} artistas seguidos en Spotify"
        except requests.exceptions.RequestException as e:
            return None, f"Error obteniendo artistas seguidos: {str(e)}"
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return None, f"Error procesando token: {str(e)}"
    
    def _get_cache_file_path(self, cache_key):
        """Generar ruta al archivo de caché"""
        # Normalizar clave para archivo
        safe_key = "".join(x for x in cache_key if x.isalnum() or x in " _-").rstrip()
        safe_key = safe_key.replace(" ", "_").lower()
        
        return self.cache_dir / f"spotify_{safe_key}.json"
    
    def _load_from_cache(self, cache_file):
        """Cargar datos de caché si existen y son válidos"""
        if not cache_file.exists():
            return None
        
        try:
            # Verificar si el archivo es reciente
            file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            cache_age = datetime.now() - file_time
            
            if cache_age > timedelta(hours=self.cache_duration):
                # Caché expirado
                return None
            
            # Cargar datos
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Verificar timestamp del caché
                if isinstance(data, dict) and 'timestamp' in data:
                    cache_time = datetime.fromisoformat(data['timestamp'])
                    if (datetime.now() - cache_time) > timedelta(hours=self.cache_duration):
                        return None
                    
                    # Devolver solo los datos (no el timestamp)
                    return data.get('data', data)
                else:
                    # Formato sin timestamp
                    return data
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error leyendo caché: {e}")
            return None
    
    def _save_to_cache(self, cache_file, data):
        """Guardar resultados en caché"""
        try:
            # Guardar con timestamp
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Error guardando caché: {e}")
    
    def clear_cache(self, pattern=None):
        """
        Limpiar caché
        
        Args:
            pattern (str, optional): Patrón para filtrar archivos de caché a limpiar
        """
        if pattern:
            for file in self.cache_dir.glob(f"spotify_{pattern}*.json"):
                file.unlink()
        else:
            for file in self.cache_dir.glob("spotify_*.json"):
                file.unlink()