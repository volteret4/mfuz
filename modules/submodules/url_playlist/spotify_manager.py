import os
import json
import time
import base64
import requests
import traceback
from urllib.parse import unquote
from pathlib import Path

from PyQt6.QtCore import Qt, QMetaObject
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QLineEdit, QDialog, QApplication

# Asegurarse de que PROJECT_ROOT está disponible
try:
    from base_module import PROJECT_ROOT
except ImportError:
    import os
    PROJECT_ROOT = os.path.abspath(Path(os.path.dirname(__file__), "..", ".."))

# Intentar importar spotipy, con manejo de errores
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

def setup_spotify(self, client_id=None, client_secret=None, cache_path=None, redirect_uri=None):
    """Configure Spotify client with improved token management"""
    if not SPOTIPY_AVAILABLE:
        self.log("Error: spotipy module not found. Please install it with 'pip install spotipy'")
        return False
        
    try:
        # Si ya tienes los valores de tus credenciales, úsalos
        if not client_id:
            client_id = os.environ.get('SPOTIFY_CLIENT_ID') or self.spotify_client_id
        
        if not client_secret:
            client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET') or self.spotify_client_secret
            
        if not client_id or not client_secret:
            self.log("Spotify client ID and secret are required for Spotify functionality")
            return False

        if not redirect_uri:
            redirect_uri = os.environ.get('SPOTIFY_REDIRECT_URI') or self.spotify_redirect_uri

        if hasattr(self, 'playlist_spotify_comboBox'):
            self.playlist_spotify_comboBox.blockSignals(True)

        self.log("Setting up Spotify client...")
        
        # Ensure cache directory exists - usa la ruta que prefieras
        if not cache_path:
            cache_dir = Path(os.path.expanduser("~"), ".cache", "music_app", "spotify")
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = Path(cache_dir, "spotify_token.txt")
            
        self.log(f"Using token cache path: {cache_path}")
        
        # Define scope for Spotify permissions
        scope = "playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative"
        
        # Create a new OAuth instance
        try:
            self.sp_oauth = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scope,
                open_browser=False,
                cache_path=cache_path
            )
            
            # Intenta obtener el token usando tu método existente primero
            token_info = None
            if hasattr(self, '_load_api_credentials_from_env'):
                self._load_api_credentials_from_env()  # Tu método existente
                
                # Si después de cargar las credenciales tenemos un token, úsalo
                if hasattr(self, 'spotify_token') and self.spotify_token:
                    token_info = {'access_token': self.spotify_token}
            
            # Si no tenemos token, usar el nuevo método
            if not token_info:
                token_info = get_token_or_authenticate(self)
            
            # Create Spotify client with the token
            self.log("Creating Spotify client with token")
            self.sp = spotipy.Spotify(auth=token_info['access_token'])
            
            self.log("Getting current user info")
            user_info = self.sp.current_user()
            self.spotify_user_id = user_info['id']
            self.log(f"Authenticated as user: {self.spotify_user_id}")

            # Resultado exitoso, ahora activamos las señales
            if hasattr(self, 'playlist_spotify_comboBox'):
                self.playlist_spotify_comboBox.blockSignals(False)
            
            # Flag that Spotify is authenticated
            self.spotify_authenticated = True
            return True
            
        except Exception as e:
            self.log(f"Spotify setup error: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            self.log(f"Error de autenticación con Spotify: {str(e)}")
            return False
            
    except Exception as e:
        self.log(f"Error setting up Spotify: {str(e)}")
        return False

def get_token_or_authenticate(self):
    """Get valid token or initiate authentication"""
    try:
        # Si ya tienes un token desde tu método existente, úsalo
        if hasattr(self, 'spotify_token') and self.spotify_token:
            return {'access_token': self.spotify_token}
            
        # Check if we have a valid cached token
        token_info = None
        try:
            cached_token = self.sp_oauth.get_cached_token()
            if cached_token and not self.sp_oauth.is_token_expired(cached_token):
                self.log("Using valid cached token")
                return cached_token
            elif cached_token:
                self.log("Cached token is expired, trying to refresh")
                try:
                    new_token = self.sp_oauth.refresh_access_token(cached_token['refresh_token'])
                    self.log("Token refreshed successfully")
                    return new_token
                except Exception as e:
                    self.log(f"Token refresh failed: {str(e)}")
                    # If refresh fails, we'll continue to new authentication
            else:
                self.log("No valid cached token found")
        except Exception as e:
            self.log(f"Error checking cached token: {str(e)}")
            # Continue to new authentication
        
        # If we get here, we need to authenticate from scratch
        self.log("Starting new authentication flow")
        return perform_new_authentication(self)
    except Exception as e:
        self.log(f"Error in get_token_or_authenticate: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        raise

def perform_new_authentication(self):
    """Perform new authentication from scratch"""
    # Check if we're in the main thread
    from PyQt6.QtCore import QThread
    
    if QThread.currentThread() != QApplication.instance().thread():
        # We're not in the main thread, so we need to use a different approach
        self.log("Authentication required from a background thread, switching to main thread")
        
        # Para PyQt6 necesitamos otro enfoque en lugar de invokeMethod con función
        # Usamos una solución alternativa con QTimer
        from PyQt6.QtCore import QTimer, QEventLoop
        
        result = [None]  # Use a list to store the result
        loop = QEventLoop()
        
        # Define a function to run in the main thread
        def run_auth_in_main_thread():
            try:
                result[0] = _perform_auth_in_main_thread(self)
            except Exception as e:
                self.log(f"Error in main thread authentication: {str(e)}")
                import traceback
                self.log(traceback.format_exc())
                result[0] = None
            finally:
                loop.quit()  # Exit the event loop when done
        
        # Use QTimer to execute in the main thread
        QTimer.singleShot(0, run_auth_in_main_thread)
        
        # Wait for the function to complete
        loop.exec()
        
        return result[0]
    else:
        # We're already in the main thread
        return _perform_auth_in_main_thread(self)

def _perform_auth_in_main_thread(self):
    """Perform authentication in the main thread"""
    # Get the authorization URL
    auth_url = self.sp_oauth.get_authorize_url()
    
    # Show instructions dialog with the URL
    msg_box = QMessageBox(self)
    msg_box.setWindowTitle("Autorización de Spotify")
    msg_box.setText(
        "Para usar las funciones de Spotify, necesita autorizar esta aplicación.\n\n"
        "1. Copie el siguiente enlace y ábralo manualmente en su navegador:\n\n"
        f"{auth_url}\n\n"
        "2. Inicie sesión en Spotify si se le solicita.\n"
        "3. Haga clic en 'Agree' para autorizar la aplicación.\n"
        "4. Será redirigido a una página. Copie la URL completa de esa página."
    )
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
    msg_box.button(QMessageBox.StandardButton.Ok).setText("Continuar")
    
    if msg_box.exec() == QMessageBox.StandardButton.Cancel:
        raise Exception("Autorización cancelada por el usuario")
    
    # Use QInputDialog for the redirect URL
    redirect_url, ok = QInputDialog.getText(
        self,
        "Ingrese URL de redirección",
        "Después de autorizar en Spotify, copie la URL completa de la página a la que fue redirigido:",
        QLineEdit.EchoMode.Normal,
        ""
    )
    
    if not ok or not redirect_url:
        raise Exception("Autorización cancelada por el usuario")
    
    # Process the URL to get the authorization code
    try:
        import urllib.parse
        
        # Handle URL-encoded URLs
        if '%3A' in redirect_url or '%2F' in redirect_url:
            redirect_url = unquote(redirect_url)
        
        self.log(f"Processing redirect URL: {redirect_url[:30]}...")
        
        # Extract the code from the URL
        code = None
        if redirect_url.startswith('http'):
            code = self.sp_oauth.parse_response_code(redirect_url)
        elif 'code=' in redirect_url:
            code = redirect_url.split('code=')[1].split('&')[0]
        else:
            code = redirect_url
        
        if not code or code == redirect_url:
            raise Exception("No se pudo extraer el código de autorización")
        
        self.log(f"Extracted code: {code[:5]}...")
        
        # Get token with the code
        token_info = self.sp_oauth.get_access_token(code)
        
        if not token_info or 'access_token' not in token_info:
            raise Exception("No se pudo obtener el token de acceso")
        
        self.log("Authentication successful")
        return token_info
        
    except Exception as e:
        self.log(f"Error processing authentication: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        
        # Show error and offer retry
        retry = QMessageBox.question(
            self,
            "Error de autenticación",
            f"Ocurrió un error: {str(e)}\n\n¿Desea intentar nuevamente?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if retry == QMessageBox.StandardButton.Yes:
            return _perform_auth_in_main_thread(self)
        else:
            raise Exception("Autenticación fallida")

def get_spotify_token(self):
    """Get or refresh Spotify API token"""
    if not hasattr(self, 'spotify_enabled') or not self.spotify_enabled:
        return None
    
    token = None
    token_expired = True
    
    # Try to read existing token
    if hasattr(self, 'spotify_token_path') and os.path.exists(self.spotify_token_path):
        try:
            with open(self.spotify_token_path, 'r') as f:
                token_data = json.load(f)
                token = token_data.get('access_token')
                expires_at = token_data.get('expires_at', 0)
                
                # Check if token is still valid (with 60 second margin)
                if expires_at > time.time() + 60:
                    token_expired = False
        except Exception as e:
            self.log(f"Error reading Spotify token: {e}")
    
    # Refresh token if needed
    if token_expired:
        token = _refresh_spotify_token(self)
    
    return token

def _refresh_spotify_token(self):
    """Refresh Spotify API token and save it to disk"""
    if not self.spotify_client_id or not self.spotify_client_secret:
        return None
        
    try:
        # Use requests to get a new token
        auth_url = 'https://accounts.spotify.com/api/token'
        auth_header = base64.b64encode(f"{self.spotify_client_id}:{self.spotify_client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {'grant_type': 'client_credentials'}
        
        response = requests.post(auth_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Add expires_at timestamp
            token_data['expires_at'] = time.time() + token_data['expires_in']
            
            # Save token to file
            with open(self.spotify_token_path, 'w') as f:
                json.dump(token_data, f)
                
            self.log("Spotify token refreshed successfully")
            return token_data['access_token']
        else:
            self.log(f"Error refreshing Spotify token: {response.status_code} {response.text}")
            return None
            
    except Exception as e:
        self.log(f"Exception refreshing Spotify token: {e}")
        return None

def refresh_token(self):
    """Refresh token if necessary"""
    if not SPOTIPY_AVAILABLE:
        return False

    try:
        token_info = self.sp_oauth.get_cached_token()
        if token_info and self.sp_oauth.is_token_expired(token_info):
            self.log("Refreshing expired token")
            token_info = self.sp_oauth.refresh_access_token(token_info['refresh_token'])
            self.sp = spotipy.Spotify(auth=token_info['access_token'])
            return True
        return False
    except Exception as e:
        self.log(f"Error refreshing token: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        
        # If refresh fails, try getting a new token
        try:
            self.log("Attempting new authentication after refresh failure")
            token_info = perform_new_authentication(self)
            self.sp = spotipy.Spotify(auth=token_info['access_token'])
            return True
        except Exception as e2:
            self.log(f"New authentication also failed: {str(e2)}")
            self.log(f"Error renovando token: {str(e)}")
            return False

def api_call_with_retry(self, func, *args, **kwargs):
    """Execute API call with retry if token expires"""
    if not SPOTIPY_AVAILABLE:
        self.log("Error: spotipy module not found")
        return None

    max_retries = 2
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.log(f"API call failed (attempt {attempt+1}/{max_retries}): {str(e)}")
            
            if attempt < max_retries - 1:
                if "token" in str(e).lower():
                    self.log("Token error detected, refreshing...")
                    if refresh_token(self):
                        self.log("Token refreshed, retrying...")
                        continue
                    else:
                        self.log("Token refresh failed")
                else:
                    self.log("Non-token error")
            
            # Last attempt failed or it's not a token error
            raise

def create_spotify_playlist(self, name, public=False, description=None):
    """Create a new Spotify playlist"""
    if not SPOTIPY_AVAILABLE:
        self.log("Error: spotipy module not found")
        return False

    if not name:
        self.log("Nombre de playlist vacío, no se creó")
        return False
        
    if not hasattr(self, 'sp') or not self.sp:
        self.log("Spotify client not initialized")
        return False
    
    try:
        # Crear la playlist
        result = api_call_with_retry(
            self,
            self.sp.user_playlist_create,
            user=self.spotify_user_id,
            name=name,
            public=public,
            description=description or "Created from Music App"
        )
        
        playlist_id = result['id']
        self.log(f"Playlist '{name}' creada correctamente")
        
        # Reload playlists to update UI
        load_spotify_playlists(self, force_update=True)
        
        # Seleccionar la nueva playlist
        if hasattr(self, 'playlist_spotify_comboBox'):
            index = self.playlist_spotify_comboBox.findText(name)
            if index >= 0:
                self.playlist_spotify_comboBox.setCurrentIndex(index)
        
        return True
    
    except Exception as e:
        self.log(f"Error creando playlist: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        
        QMessageBox.warning(self, "Error", f"Error creando playlist: {str(e)}")
        
        return False

def add_tracks_to_spotify_playlist(self, playlist_id, playlist_name):
    """Add tracks from the current queue to a Spotify playlist"""
    if not SPOTIPY_AVAILABLE:
        self.log("Error: spotipy module not found")
        return False

    try:
        # Show a progress dialog
        from PyQt6.QtWidgets import QProgressDialog
        
        progress_dialog = QProgressDialog("Añadiendo canciones a Spotify...", "Cancelar", 0, self.listWidget.count(), self)
        progress_dialog.setWindowTitle("Guardando Playlist")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Get Spotify URIs for all tracks in the queue
        track_uris = []
        not_found = []
        skipped = 0
        
        for i in range(self.listWidget.count()):
            # Update progress
            progress_dialog.setValue(i)
            if progress_dialog.wasCanceled():
                self.log("Operación cancelada por el usuario")
                return
            
            # Get item data
            item = self.listWidget.item(i)
            if not item:
                continue
                
            # Get track data
            track_data = {}
            if i < len(self.current_playlist):
                track_data = self.current_playlist[i]
            else:
                # Extract from item text
                text = item.text()
                title = text
                artist = ""
                if " - " in text:
                    parts = text.split(" - ", 1)
                    artist = parts[0]
                    title = parts[1]
                track_data = {'title': title, 'artist': artist, 'url': item.data(Qt.ItemDataRole.UserRole)}
            
            track_uri = None
            
            # Check if this is already a Spotify track with ID
            entry_data = track_data.get('entry_data', {})
            if isinstance(entry_data, dict) and entry_data.get('source') == 'spotify' and entry_data.get('spotify_id'):
                track_uri = f"spotify:track:{entry_data['spotify_id']}"
            # Check if URL is a Spotify URL with track ID
            elif 'url' in track_data and 'spotify.com/track/' in track_data['url']:
                track_id = track_data['url'].split('spotify.com/track/')[1].split('?')[0]
                track_uri = f"spotify:track:{track_id}"
            else:
                # Try to search for the track on Spotify
                search_query = f"{track_data.get('title', '')} artist:{track_data.get('artist', '')}" 
                track_uri = self.search_spotify_track_uri(search_query)
            
            if track_uri:
                track_uris.append(track_uri)
            else:
                not_found.append(track_data.get('title', f"Track {i+1}"))
                skipped += 1
        
        progress_dialog.setValue(self.listWidget.count())
        
        # Add tracks to the playlist (in batches of 100 if needed)
        if track_uris:
            batch_size = 100
            for i in range(0, len(track_uris), batch_size):
                batch = track_uris[i:i+batch_size]
                api_call_with_retry(self, self.sp.playlist_add_items, playlist_id, batch)
        
        # Show results
        if skipped > 0:
            QMessageBox.information(
                self, 
                "Playlist guardada", 
                f"Playlist '{playlist_name}' actualizada con {len(track_uris)} canciones.\n"
                f"No se encontraron {skipped} canciones en Spotify."
            )
        else:
            QMessageBox.information(
                self, 
                "Playlist guardada", 
                f"Playlist '{playlist_name}' actualizada con {len(track_uris)} canciones."
            )
        
        self.log(f"Playlist '{playlist_name}' actualizada con {len(track_uris)} canciones")
        if skipped > 0:
            self.log(f"No se encontraron {skipped} canciones en Spotify: {', '.join(not_found[:5])}" + 
                ("..." if len(not_found) > 5 else ""))
        
        return True
    except Exception as e:
        self.log(f"Error añadiendo canciones a la playlist: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        QMessageBox.warning(self, "Error", f"Error añadiendo canciones a la playlist: {str(e)}")
        return False

def load_spotify_playlists(self, force_update=False):
    """Load user Spotify playlists from cache or Spotify"""
    if not hasattr(self, 'sp') or not self.sp:
        self.log("Spotify client not initialized")
        return False
        
    try:
        cache_path = Path(os.path.expanduser("~"), ".cache", "music_app", "spotify", "playlists.json")
        
        if not force_update and os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                update_spotify_playlists_ui(self, cached_data['items'])
                self.log("Spotify playlists loaded from cache")
                return True

        results = api_call_with_retry(self, self.sp.current_user_playlists)
        
        # Save to cache
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        update_spotify_playlists_ui(self, results['items'])
        return True
        
    except Exception as e:
        self.log(f"Error loading Spotify playlists: {str(e)}")
        self.log(f"Traceback: {traceback.format_exc()}")
        return False

def update_spotify_playlists_ui(self, playlists_data):
    """Update UI with Spotify playlist data"""
    # Verificar que el combobox existe antes de usarlo
    if not hasattr(self, 'playlist_spotify_comboBox') or not self.playlist_spotify_comboBox:
        self.log("Error: No se encontró el combobox de playlists de Spotify")
        return
        
    # Guardar la selección actual si existe
    current_text = self.playlist_spotify_comboBox.currentText() if self.playlist_spotify_comboBox.count() > 0 else ""
    
    # Bloquear señales durante la actualización
    self.playlist_spotify_comboBox.blockSignals(True)
    
    # Limpiar y repoblar el combobox
    self.playlist_spotify_comboBox.clear()
    
    # Añadir placeholder como primera opción
    self.playlist_spotify_comboBox.addItem(QIcon(":/services/spotify"), "Playlists Spotify")
    
    # Añadir la opción de "Nueva Playlist" después del placeholder
    self.playlist_spotify_comboBox.addItem(QIcon(":/services/spotify"), "Nueva Playlist Spotify")
    
    # Almacenar playlists
    self.spotify_playlists = {}
    
    # Añadir las playlists al combobox
    for playlist in playlists_data:
        playlist_name = playlist['name']
        playlist_id = playlist['id']
        
        # Guardar la playlist
        self.spotify_playlists[playlist_name] = playlist
        
        # Añadir al combobox
        self.playlist_spotify_comboBox.addItem(QIcon(":/services/spotify"), playlist_name)
    
    # Restaurar la selección anterior si es posible
    if current_text and current_text != "Playlists Spotify" and current_text != "Nueva Playlist Spotify":
        index = self.playlist_spotify_comboBox.findText(current_text)
        if index >= 0:
            self.playlist_spotify_comboBox.setCurrentIndex(index)
        else:
            self.playlist_spotify_comboBox.setCurrentIndex(0)  # Seleccionar placeholder
    else:
        self.playlist_spotify_comboBox.setCurrentIndex(0)  # Seleccionar placeholder
    
    # Desbloquear señales
    self.playlist_spotify_comboBox.blockSignals(False)
    
    # Forzar actualización visual
    self.playlist_spotify_comboBox.update()
    
    self.log(f"Cargadas {len(playlists_data)} playlists de Spotify")