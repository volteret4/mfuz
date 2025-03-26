from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLineEdit, QListWidget, QComboBox, QMessageBox,
                            QListWidgetItem, QSplitter, QLabel, QGroupBox,
                            QInputDialog, QDialog, QTextEdit, QListView)
from PyQt6.QtCore import Qt
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Dict, List
import webbrowser
import os
from pathlib import Path
import traceback
import json
import threading
import http.server
import socketserver
import urllib.parse
import time
import logging
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule, THEMES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class SpotifyPlaylistManager(BaseModule):
    def __init__(self, client_id: str, client_secret: str, cache_path: str = None, force_update: str = False, parent=None, theme='Tokyo Night', **kwargs):
        super().__init__(parent, theme)        
        if cache_path is None:
            cache_path = str(Path.home() / ".cache" / "spotify_token.txt")
        if not client_id or not client_secret:
            raise ValueError("Client ID y Client Secret son obligatorios")
        # Definir rutas de cache
        self.cache_dir = Path.home() / ".cache" / "spotify_manager"
        self.playlists_cache = self.cache_dir / "playlists.json"
        self.tracks_cache_dir = self.cache_dir / "tracks"
        
        # Crear directorios si no existen
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.tracks_cache_dir.mkdir(exist_ok=True)
        
        self.setup_spotify(client_id, client_secret, cache_path)
        self.playlists = {}
        self.temp_playlist_tracks = []

        self.available_themes = kwargs.pop('temas', [])
        self.selected_theme = kwargs.pop('tema_seleccionado', theme)
        
        #self.init_ui()
        self.load_playlists()


    def apply_theme(self, theme_name=None):
        super().apply_theme(theme_name)

    def setup_spotify(self, client_id: str, client_secret: str, cache_path: str):
        """Configurar cliente de Spotify con manejo de token mejorado"""
        try:
            print("Setting up Spotify client...")
            
            # Ensure cache directory exists
            project_root = Path(__file__).parent.parent
            token_cache_path = project_root / ".content" / "cache" / "token"
            token_cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"Using token cache path: {token_cache_path}")
            
            scope = "playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative"
            
            # Create a new OAuth instance
            self.sp_oauth = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri='http://localhost:8998',
                scope=scope,
                open_browser=False,
                cache_path=str(token_cache_path)
            )
            
            # Try to get a valid token or initiate authentication
            token_info = self.get_token_or_authenticate()
            
            # Create Spotify client with the token
            print("Creating Spotify client with token")
            self.sp = spotipy.Spotify(auth=token_info['access_token'])
            
            print("Getting current user info")
            user_info = self.sp.current_user()
            self.user_id = user_info['id']
            print(f"Authenticated as user: {self.user_id}")
            
        except Exception as e:
            print(f"Spotify setup error: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error de autenticación con Spotify: {str(e)}")
            raise

    def get_token_or_authenticate(self):
        """Obtener token válido o iniciar autenticación"""
        try:
            # Check if we have a valid cached token
            token_info = None
            try:
                cached_token = self.sp_oauth.get_cached_token()
                if cached_token and not self.sp_oauth.is_token_expired(cached_token):
                    print("Using valid cached token")
                    return cached_token
                elif cached_token:
                    print("Cached token is expired, trying to refresh")
                    try:
                        new_token = self.sp_oauth.refresh_access_token(cached_token['refresh_token'])
                        print("Token refreshed successfully")
                        return new_token
                    except Exception as e:
                        print(f"Token refresh failed: {str(e)}")
                        # If refresh fails, we'll continue to new authentication
                else:
                    print("No valid cached token found")
            except Exception as e:
                print(f"Error checking cached token: {str(e)}")
                # Continue to new authentication
            
            # If we get here, we need to authenticate from scratch
            print("Starting new authentication flow")
            return self.perform_new_authentication()
        except Exception as e:
            print(f"Error in get_token_or_authenticate: {str(e)}")
            traceback.print_exc()
            raise

    def perform_new_authentication(self):
        """Realizar autenticación nueva desde cero"""
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
        
        # No abrimos el navegador automáticamente
        # webbrowser.open(auth_url)  # Comentado para evitar apertura automática
        
        # Usar QInputDialog en lugar de QDialog personalizado
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
            # Handle URL-encoded URLs
            if '%3A' in redirect_url or '%2F' in redirect_url:
                redirect_url = urllib.parse.unquote(redirect_url)
            
            print(f"Processing redirect URL: {redirect_url[:30]}...")
            
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
            
            print(f"Extracted code: {code[:5]}...")
            
            # Get token with the code
            token_info = self.sp_oauth.get_access_token(code)
            
            if not token_info or 'access_token' not in token_info:
                raise Exception("No se pudo obtener el token de acceso")
            
            print("Authentication successful")
            return token_info
            
        except Exception as e:
            print(f"Error processing authentication: {str(e)}")
            traceback.print_exc()
            
            # Show error and offer retry
            retry = QMessageBox.question(
                self,
                "Error de autenticación",
                f"Ocurrió un error: {str(e)}\n\n¿Desea intentar nuevamente?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if retry == QMessageBox.StandardButton.Yes:
                return self.perform_new_authentication()
            else:
                raise Exception("Autenticación fallida")

    def refresh_token(self):
        """Renovar token si es necesario"""
        try:
            token_info = self.sp_oauth.get_cached_token()
            if token_info and self.sp_oauth.is_token_expired(token_info):
                print("Refreshing expired token")
                token_info = self.sp_oauth.refresh_access_token(token_info['refresh_token'])
                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                return True
            return False
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")
            traceback.print_exc()
            
            # If refresh fails, try getting a new token
            try:
                print("Attempting new authentication after refresh failure")
                token_info = self.perform_new_authentication()
                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                return True
            except Exception as e2:
                print(f"New authentication also failed: {str(e2)}")
                QMessageBox.critical(self, "Error", f"Error renovando token: {str(e)}")
                return False

    def api_call_with_retry(self, func, *args, **kwargs):
        """Ejecutar llamada API con reintento si el token expira"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"API call failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    if "token" in str(e).lower():
                        print("Token error detected, refreshing...")
                        if self.refresh_token():
                            print("Token refreshed, retrying...")
                            continue
                        else:
                            print("Token refresh failed")
                    else:
                        print("Non-token error")
                
                # Last attempt failed or it's not a token error
                raise

    def start_temporary_server(self):
        """Iniciar servidor HTTP temporal para capturar el token de redirección"""
        
        # Definir manejador de solicitudes
        class TokenRequestHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Override to reduce console spam
                if args[0] == '200':
                    print("Received callback request")
                else:
                    print(f"Server: {format % args}")
            
            def do_GET(self):
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    # Capture full URL with the code
                    full_url = f"http://localhost:8998{self.path}"
                    
                    # Decode URL if it's encoded
                    if '%3A' in full_url or '%2F' in full_url:
                        full_url = urllib.parse.unquote(full_url)
                    
                    print(f"Callback URL: {full_url}")
                    
                    if 'code=' in self.path:
                        print("Code parameter found in URL")
                        self.server.spotify_manager._callback_token = full_url
                        response = """
                        <html>
                        <head>
                            <title>Autorización Completada</title>
                            <style>
                                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                                h1 { color: #1DB954; }
                            </style>
                        </head>
                        <body>
                            <h1>Autorización completada correctamente</h1>
                            <p>Puedes cerrar esta ventana y volver a la aplicación.</p>
                            <p>La aplicación continuará automáticamente.</p>
                        </body>
                        </html>
                        """
                    else:
                        print(f"No code parameter in callback URL: {self.path}")
                        response = """
                        <html>
                        <head>
                            <title>Error de Autorización</title>
                            <style>
                                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                                h1 { color: #FF0000; }
                            </style>
                        </head>
                        <body>
                            <h1>Error en el proceso de autorización</h1>
                            <p>No se recibió el código de autorización.</p>
                            <p>Por favor, regrese a la aplicación e intente nuevamente.</p>
                        </body>
                        </html>
                        """
                        
                    self.wfile.write(response.encode('utf-8'))
                except Exception as e:
                    print(f"Error handling request: {str(e)}")
                    try:
                        error_response = f"""
                        <html><body><h1>Error</h1><p>{str(e)}</p></body></html>
                        """.encode('utf-8')
                        self.wfile.write(error_response)
                    except:
                        pass
        
        # Configuración del servidor
        try:
            # Allow port reuse to avoid "address already in use" errors
            socketserver.TCPServer.allow_reuse_address = True
            httpd = socketserver.TCPServer(("localhost", 8998), TokenRequestHandler)
            httpd.timeout = 1  # Short timeout for faster shutdown
            httpd.spotify_manager = self
            
            print("Starting temporary server on http://localhost:8998")
            
            # Start in separate thread
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            return server_thread, httpd
        except Exception as e:
            print(f"Error starting temporary server: {str(e)}")
            print("Continuing with manual fallback only")
            return None, None




    def init_ui(self):
        """Initialize the user interface"""
        # Verificar si los widgets ya existen
        if hasattr(self, 'playlist_list'):
            print("La UI ya está inicializada, saltando init_ui()")
            return
        
        layout = self.layout()
        if not layout:
            layout = QVBoxLayout()
            self.setLayout(layout)
        
        # Playlists section
        print("Creando playlist_list")
        self.playlist_list = QListWidget(self)
        self.playlist_list.setMinimumHeight(200)
        layout.addWidget(self.playlist_list)
        
        # Search section
        search_container = QWidget(self)
        search_container.setStyleSheet("""
            QWidget::tab-bar {
                alignment: center;
            }
            QWidget::tab {
                border-radius: 10px;
                padding: 5px;
                margin: 5px;
            }
            QWidget::tab:selected {
                background: #dcdcdc;
                border: 2px solid #a0a0a0;
            }
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_input = QLineEdit(search_container)
        self.search_input.setPlaceholderText("Buscar canción o artista...")
        self.search_button = QPushButton("Buscar", search_container)
        
        self.search_button.clicked.connect(self.search_tracks)
        self.search_input.returnPressed.connect(self.search_tracks)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addWidget(search_container)
        
        # Splitter para dividir resultados y creador de playlists
        self.results_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.results_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: transparent;
                width: 1px;
            }
        """)
        
        # Search results (panel izquierdo)
        search_results_group = QGroupBox("Resultados de búsqueda")
        search_results_group.setStyleSheet("""
            QGroupBox {
                border: none;
                background-color: transparent;
                padding: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)
        search_results_layout = QVBoxLayout(search_results_group)
        
        self.search_results = QListWidget()
        self.search_results.setMinimumHeight(200)
        self.search_results.setResizeMode(QListView.ResizeMode.Adjust)
        self.search_results.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.search_results.setWordWrap(True)
        self.search_results.setUniformItemSizes(False)  # Permitir alturas diferentes

        search_results_layout.addWidget(self.search_results)
        
        self.results_splitter.addWidget(search_results_group)
        
        # Creador de playlists (panel derecho)
        playlist_creator_group = QGroupBox("Creador de playlists")
        playlist_creator_group.setStyleSheet("""
            QGroupBox {
                border: none;
                background-color: transparent;
                padding: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)
        playlist_creator_layout = QVBoxLayout(playlist_creator_group)
        
        self.playlist_creator = QListWidget()
        self.playlist_creator.setMinimumHeight(200)
        self.playlist_creator.setResizeMode(QListView.ResizeMode.Adjust)
        self.playlist_creator.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.playlist_creator.setWordWrap(True)
        self.playlist_creator.setUniformItemSizes(False)
        playlist_creator_layout.addWidget(self.playlist_creator)
        
        # Botones para gestionar creador de playlists
        playlist_buttons_container = QWidget()
        playlist_buttons_container.setStyleSheet("""
            QWidget {
                background-color: {theme['bg']};
                color: {theme['fg']};
                font-family: {self.font_family};
                font-size: {self.font_size};
                border: none
            }
        """)
            
        playlist_buttons_layout = QHBoxLayout(playlist_buttons_container)
        
        self.save_playlist_button = QPushButton("Guardar playlist")
        self.save_playlist_button.clicked.connect(self.save_temp_playlist)
        self.clear_playlist_button = QPushButton("Limpiar")
        self.clear_playlist_button.clicked.connect(self.clear_temp_playlist)
        
        playlist_buttons_layout.addWidget(self.save_playlist_button)
        playlist_buttons_layout.addWidget(self.clear_playlist_button)
        
        playlist_creator_layout.addWidget(playlist_buttons_container)
        
        self.results_splitter.addWidget(playlist_creator_group)
        
        # Agregar splitter al layout principal
        layout.addWidget(self.results_splitter)
        
        # New playlist section
        playlist_container = QWidget(self)
        playlist_container.setStyleSheet("""
            QWidget::tab-bar {
                alignment: center;
            }
            QWidget::tab {
                border-radius: 10px;
                padding: 5px;
                margin: 5px;
            }
            QWidget::tab:selected {
                background: transparent;
                border: none;
            }
        """)
        new_playlist_layout = QHBoxLayout(playlist_container)
        new_playlist_layout.setContentsMargins(0, 0, 0, 0)
        
        self.new_playlist_input = QLineEdit(playlist_container)
        self.new_playlist_input.setPlaceholderText("Nueva playlist...")
        self.new_playlist_button = QPushButton("Crear Playlist", playlist_container)
        
        self.new_playlist_button.clicked.connect(self.create_playlist)
        self.new_playlist_input.returnPressed.connect(self.create_playlist)
        
        new_playlist_layout.addWidget(self.new_playlist_input)
        new_playlist_layout.addWidget(self.new_playlist_button)
        layout.addWidget(playlist_container)
        
        # Playlist selector
        selector_container = QWidget(self)
        selector_container.setStyleSheet("""
            QWidget::tab-bar {
                alignment: center;
            }
            QWidget::tab {
                border-radius: 10px;
                padding: 5px;
                margin: 5px;
            }
            QWidget::tab:selected {
                background: #dcdcdc;
                border: 2px solid #a0a0a0;
            }
        """)
        add_to_playlist_layout = QHBoxLayout(selector_container)
        add_to_playlist_layout.setContentsMargins(0, 0, 0, 0)
        
        self.playlist_selector = QComboBox(selector_container)
        self.add_song_button = QPushButton("Añadir canción seleccionada a Playlist", selector_container)
        self.add_song_button.clicked.connect(self.add_selected_song)
        
        add_to_playlist_layout.addWidget(self.playlist_selector)
        add_to_playlist_layout.addWidget(self.add_song_button)
        layout.addWidget(selector_container)


    def load_playlists(self, force_update: str = False):
        """Load user playlists from cache or Spotify"""
        print("Comenzando carga de playlists...")
        
        try:
            if not force_update and self.playlists_cache.exists():
                with open(self.playlists_cache, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    self.update_playlist_ui(cached_data['items'])
                    print("Playlists cargadas desde cache")
                    return

            results = self.api_call_with_retry(self.sp.current_user_playlists)
            
            # Guardar en cache
            with open(self.playlists_cache, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            self.update_playlist_ui(results['items'])
            
        except Exception as e:
            print(f"Error cargando playlists: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Error cargando playlists: {str(e)}")

    def update_playlist_ui(self, playlists_data):
        """Update UI with playlist data"""
        self.playlist_list.clear()
        self.playlist_selector.clear()
        self.playlists.clear()
        
        for playlist in playlists_data:
            self.playlists[playlist['name']] = playlist['id']
            
            item_widget = QWidget(self.playlist_list)
            # Aplicar estilo al widget para que sea invisible/sin bordes
            item_widget.setStyleSheet("""
                QWidget {
                    border: none;
                    background-color: transparent;
                    padding: 2px
                }
            """)

            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(3, 5, 3, 5)
            
            playlist_button = QPushButton(playlist['name'], item_widget)
            playlist_button.setFixedHeight(30)
            playlist_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    border: none;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
            """)
            
            # Modificar el handler del botón de playlist para mostrar contenido
            def create_show_handler(pid=playlist['id'], pname=playlist['name']):
                return lambda: self.show_playlist_content(pid, pname)
            
            playlist_button.clicked.connect(create_show_handler())
            
            play_button = QPushButton("▶", item_widget)
            play_button.setFixedWidth(30)
            play_button.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 255, 0, 0.2);
                }
            """)
            
            playlist_url = playlist['external_urls']['spotify']
            def create_play_handler(url=playlist_url):
                return lambda: self.play_spotify_entity(url)
            
            play_button.clicked.connect(create_play_handler())
            
            delete_button = QPushButton("✖", item_widget)
            delete_button.setFixedWidth(30)
            delete_button.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 0, 0, 0.2);
                }
            """)
            
            def create_delete_handler(pid=playlist['id']):
                return lambda: self.delete_playlist(pid)
            
            delete_button.clicked.connect(create_delete_handler())
            
            item_layout.addWidget(playlist_button, stretch=1)
            item_layout.addWidget(play_button)
            item_layout.addWidget(delete_button)
            
            item = QListWidgetItem(self.playlist_list)
            item.setSizeHint(item_widget.sizeHint())
            self.playlist_list.addItem(item)
            self.playlist_list.setItemWidget(item, item_widget)
            
            self.playlist_selector.addItem(playlist['name'])


    def show_playlist_content(self, playlist_id: str, playlist_name: str, force_update: str = False):
        """Show playlist tracks in search results area"""
        print(f"Mostrando contenido de playlist: {playlist_name}")
        
        cache_file = self.tracks_cache_dir / f"{playlist_id}.json"
        
        try:
            tracks_data = None
            if not force_update and cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    tracks_data = json.load(f)
                print("Tracks cargados desde cache")
            else:
                # Obtener tracks de Spotify
                results = self.api_call_with_retry(self.sp.playlist_items, playlist_id)
                tracks_data = []
                
                for item in results['items']:
                    if item['track']:
                        track_info = {
                            'id': item['track']['id'],
                            'name': item['track']['name'],
                            'artists': [artist['name'] for artist in item['track']['artists']],
                            'url': item['track']['external_urls']['spotify']
                        }
                        tracks_data.append(track_info)
                
                # Guardar en cache
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(tracks_data, f, ensure_ascii=False, indent=2)
            
            # Actualizar UI
            self.search_results.clear()
            
            for track in tracks_data:
                artist_names = ", ".join(track['artists'])
                display_text = f"{track['name']} - {artist_names}"
                
                item_widget = QWidget()
                item_widget.setStyleSheet("""
                    QWidget {
                        border: none;
                        background-color: transparent;
                        padding: 2px
                    }
                    QWidget:hover {
                        background-color: rgba(255, 255, 255, 0.1);
                    }
                """)
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(5, 5, 5, 5)
                
                track_label = QLabel(display_text)
                track_label.setWordWrap(True)
                
                play_button = QPushButton("▶")
                play_button.setFixedWidth(30)
                play_button.setStyleSheet("""
                    QPushButton {
                        border: none;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: rgba(0, 255, 0, 0.2);
                    }
                """)
                
                def create_play_handler(url=track['url']):
                    return lambda: self.play_spotify_entity(url)
                play_button.clicked.connect(create_play_handler())
                
                add_button = QPushButton("+")
                add_button.setFixedWidth(30)
                add_button.setStyleSheet("""
                    QPushButton {
                        border: none;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: rgba(0, 0, 255, 0.2);
                    }
                """)
                
                def create_add_handler(track_id=track['id'], display=display_text, track_url=track['url']):
                    return lambda: self.add_to_temp_playlist(track_id, display, track_url)
                add_button.clicked.connect(create_add_handler())
                
                item_layout.addWidget(track_label, stretch=1)
                item_layout.addWidget(play_button)
                item_layout.addWidget(add_button)
                
                item = QListWidgetItem(self.search_results)
                item.setData(Qt.ItemDataRole.UserRole, track['id'])
                item.setSizeHint(item_widget.sizeHint())
                self.search_results.addItem(item)
                self.search_results.setItemWidget(item, item_widget)
                
            print(f"Mostrados {len(tracks_data)} tracks")
            
        except Exception as e:
            print(f"Error mostrando contenido de playlist: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Error mostrando contenido de playlist: {str(e)}")



    def open_spotify_url(self, url):
        """Open URL using xdg-open"""
        try:
            import subprocess
            subprocess.Popen(['xdg-open', url])
        except Exception as e:
            print(f"Error abriendo URL: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error abriendo URL: {str(e)}")


    def play_spotify_entity(self, url):
        """Play Spotify entity using the web player or app"""
        try:
            self.open_spotify_url(url)
        except Exception as e:
            print(f"Error reproduciendo: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error reproduciendo: {str(e)}")


    def search_tracks(self):
        """Search for tracks on Spotify"""
        print("Iniciando búsqueda...")
        query = self.search_input.text()
        query = query.strip()
        print(f"Término de búsqueda: '{query}'")
        
        if not query:
            print("Búsqueda vacía, retornando")
            return
            
        try:
            print(f"Realizando búsqueda en Spotify para: {query}")
            results = self.api_call_with_retry(self.sp.search, q=query, type='track', limit=10)
            
            if not results or 'tracks' not in results:
                print("No se encontraron resultados")
                return
                
            self.search_results.clear()
            print(f"Encontrados {len(results['tracks']['items'])} resultados")
            
            for track in results['tracks']['items']:
                artist_names = ", ".join(artist['name'] for artist in track['artists'])
                display_text = f"{track['name']} - {artist_names}"
                
                # Crear widget para contener track y botones
                item_widget = QWidget()
                item_widget.setStyleSheet("""
                    QPushButton {
                        border: none;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: rgba(0, 255, 0, 0.2);
                    }
                """)
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(5, 5, 5, 5)
                
                # Etiqueta con información de la canción
                track_label = QLabel(display_text)
                track_label.setWordWrap(True)
                
                # Botón de reproducir
                play_button = QPushButton("▶")
                play_button.setFixedWidth(30)
                play_button.setStyleSheet("""
                    QPushButton {
                        border: none;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: rgba(0, 255, 0, 0.2);
                    }
                """)
                
                track_url = track['external_urls']['spotify']
                def create_play_handler(url=track_url):
                    return lambda: self.play_spotify_entity(url)
                play_button.clicked.connect(create_play_handler())
                
                # Botón de añadir al creador de playlists
                add_button = QPushButton("+")
                add_button.setFixedWidth(30)
                add_button.setStyleSheet("""
                    QPushButton {
                        border: none;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: rgba(0, 0, 255, 0.2);
                    }
                """)
                
                # Crear función de cierre con track_id y display_text
                def create_add_handler(track_id=track['id'], display=display_text, track_url=track_url):
                    return lambda: self.add_to_temp_playlist(track_id, display, track_url)
                add_button.clicked.connect(create_add_handler())
                
                item_layout.addWidget(track_label, stretch=1)
                item_layout.addWidget(play_button)
                item_layout.addWidget(add_button)
                
                # Agregar widget a lista
                item = QListWidgetItem(self.search_results)
                item.setData(Qt.ItemDataRole.UserRole, track['id'])
                item.setSizeHint(item_widget.sizeHint())
                self.search_results.addItem(item)
                self.search_results.setItemWidget(item, item_widget)
                
                print(f"Añadido: {display_text}")
                
        except Exception as e:
            print(f"Error en búsqueda: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error en la búsqueda: {str(e)}")


    def add_to_temp_playlist(self, track_id, display_text, track_url):
        """Añadir canción al creador de playlists temporal"""
        print(f"Añadiendo a playlist temporal: {display_text}")
        
        # Guardar información de la canción
        track_info = {
            'id': track_id,
            'display': display_text,
            'url': track_url
        }
        self.temp_playlist_tracks.append(track_info)
        
        # Crear widget para la canción en el creador
        item_widget = QWidget()
        item_widget.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 0, 0.2);
            }
        """)
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 5, 5, 5)
        
        # Etiqueta con información de la canción
        track_label = QLabel(display_text)
        track_label.setWordWrap(True)
        
        # Botón de reproducir
        play_button = QPushButton("▶")
        play_button.setFixedWidth(30)
        play_button.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 0, 0.2);
            }
        """)
        
        def create_play_handler(url=track_url):
            return lambda: self.play_spotify_entity(url)
        play_button.clicked.connect(create_play_handler())
        
        # Botón de eliminar
        remove_button = QPushButton("✖")
        remove_button.setFixedWidth(30)
        remove_button.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.2);
            }
        """)
        
        # Creamos un índice para la posición actual de esta canción
        current_index = len(self.temp_playlist_tracks) - 1
        
        def create_remove_handler(index=current_index):
            return lambda: self.remove_from_temp_playlist(index)
        remove_button.clicked.connect(create_remove_handler())
        
        item_layout.addWidget(track_label, stretch=1)
        item_layout.addWidget(play_button)
        item_layout.addWidget(remove_button)
        
        # Agregar widget a lista
        item = QListWidgetItem(self.playlist_creator)
        item.setSizeHint(item_widget.sizeHint())
        self.playlist_creator.addItem(item)
        self.playlist_creator.setItemWidget(item, item_widget)


    def remove_from_temp_playlist(self, index):
        """Eliminar canción del creador de playlists temporal"""
        if 0 <= index < len(self.temp_playlist_tracks):
            # Eliminar del listado visual
            self.playlist_creator.takeItem(index)
            
            # Eliminar de la lista de tracks
            removed = self.temp_playlist_tracks.pop(index)
            print(f"Eliminada canción: {removed['display']}")
            
            # Actualizar índices para los botones de eliminar
            self.refresh_temp_playlist_view()
            
    
    def refresh_temp_playlist_view(self):
        """Recrea la vista del creador de playlists para actualizar índices"""
        self.playlist_creator.clear()
        
        for i, track in enumerate(self.temp_playlist_tracks):
            # Crear widget para la canción
            item_widget = QWidget()
            item_widget.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 255, 0, 0.2);
                }
            """)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 5, 5, 5)
            
            # Etiqueta con información de la canción
            track_label = QLabel(track['display'])
            track_label.setWordWrap(True)
            
            # Botón de reproducir
            play_button = QPushButton("▶")
            play_button.setFixedWidth(30)
            play_button.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 255, 0, 0.2);
                }
            """)
            
            def create_play_handler(url=track['url']):
                return lambda: self.play_spotify_entity(url)
            play_button.clicked.connect(create_play_handler())
            
            # Botón de eliminar
            remove_button = QPushButton("✖")
            remove_button.setFixedWidth(30)
            remove_button.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 0, 0, 0.2);
                }
            """)
            
            def create_remove_handler(index=i):
                return lambda: self.remove_from_temp_playlist(index)
            remove_button.clicked.connect(create_remove_handler())
            
            item_layout.addWidget(track_label, stretch=1)
            item_layout.addWidget(play_button)
            item_layout.addWidget(remove_button)
            
            # Agregar widget a lista
            item = QListWidgetItem(self.playlist_creator)
            item.setSizeHint(item_widget.sizeHint())
            self.playlist_creator.addItem(item)
            self.playlist_creator.setItemWidget(item, item_widget)
    
    
    def clear_temp_playlist(self):
        """Limpiar el creador de playlists temporal"""
        self.temp_playlist_tracks = []
        self.playlist_creator.clear()


    def save_temp_playlist(self):
        """Guardar las canciones del creador de playlists a una playlist existente"""
        if not self.temp_playlist_tracks:
            QMessageBox.warning(self, "Error", "No hay canciones para guardar")
            return
            
        playlist_name = self.playlist_selector.currentText()
        if not playlist_name:
            QMessageBox.warning(self, "Error", "Por favor selecciona una playlist")
            return
            
        playlist_id = self.playlists.get(playlist_name)
        if not playlist_id:
            QMessageBox.warning(self, "Error", "Playlist no encontrada")
            return
        
        try:
            # Extraer IDs de las canciones
            track_uris = [f"spotify:track:{track['id']}" for track in self.temp_playlist_tracks]
            
            # Añadir canciones a la playlist
            self.sp.playlist_add_items(playlist_id, track_uris)
            
            QMessageBox.information(self, "Éxito", f"{len(track_uris)} canciones añadidas a {playlist_name}")
            
            # Limpiar después de guardar
            self.clear_temp_playlist()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error guardando canciones: {str(e)}")


    def create_playlist(self):
        """Create a new Spotify playlist"""
        print("Botón crear playlist clickeado")
        name = self.new_playlist_input.text().strip()
        print(f"Intentando crear playlist con nombre: [{name}]")
        if not name:
            QMessageBox.warning(self, "Error", "Por favor introduce un nombre para la playlist")
            return
            
        try:
            self.sp.user_playlist_create(
                user=self.user_id,
                name=name,
                public=False,
                description="Creada desde Playlist Manager"
            )
            
            self.new_playlist_input.clear()
            self.load_playlists()
            QMessageBox.information(self, "Éxito", "Playlist creada correctamente")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creando playlist: {str(e)}")


    def delete_playlist(self, playlist_id: str):
        """Delete a Spotify playlist and its cache"""
        try:
            self.sp.current_user_unfollow_playlist(playlist_id)
            
            # Eliminar cache de tracks
            cache_file = self.tracks_cache_dir / f"{playlist_id}.json"
            if cache_file.exists():
                cache_file.unlink()
            
            # Recargar playlists con force_update
            self.load_playlists(force_update=True)
            
            QMessageBox.information(self, "Éxito", "Playlist eliminada correctamente")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error eliminando playlist: {str(e)}")


    def add_selected_song(self):
        """Add selected song from search results to chosen playlist"""
        selected_items = self.search_results.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Error", "Por favor selecciona una canción")
            return
            
        track_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        playlist_name = self.playlist_selector.currentText()
        playlist_id = self.playlists.get(playlist_name)
        
        if not playlist_id:
            QMessageBox.warning(self, "Error", "Por favor selecciona una playlist")
            return
            
        try:
            self.sp.playlist_add_items(playlist_id, [f"spotify:track:{track_id}"])
            QMessageBox.information(self, "Éxito", "Canción añadida correctamente")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error añadiendo canción: {str(e)}")


    # Nuevos métodos para integración con otros módulos
    def add_track_to_creator(self, spotify_uri=None, search_query=None):
        """
        Método para que otros módulos puedan añadir canciones al creador de playlists:
        - Si se proporciona spotify_uri, se añade directamente
        - Si se proporciona search_query, se realiza una búsqueda y se muestran resultados
        """
        if spotify_uri:
            try:
                # Extraer el ID de la canción del URI
                track_id = spotify_uri.split(':')[-1]
                
                # Obtener información de la canción
                track_info = self.api_call_with_retry(self.sp.track, track_id)
                
                artist_names = ", ".join(artist['name'] for artist in track_info['artists'])
                display_text = f"{track_info['name']} - {artist_names}"
                
                # Añadir al creador de playlists
                self.add_to_temp_playlist(track_id, display_text, track_info['external_urls']['spotify'])
                
                return True
                
            except Exception as e:
                print(f"Error añadiendo canción al creador: {str(e)}")
                return False
                
        elif search_query:
            # Realizar búsqueda y mostrar resultados
            self.search_input.setText(search_query)
            self.search_tracks()
            return True
            
        return False

    # Métodos para integración con otros módulos
    def add_track_by_url(self, spotify_url):
        """
        Añade una canción directamente al creador de playlist usando una URL de Spotify
        Args:
            spotify_url (str): URL de Spotify a una canción (ej: https://open.spotify.com/track/...)
        Returns:
            bool: True si se añadió correctamente, False en caso contrario
        """
        try:
            # Extraer el ID de la canción de la URL
            if 'spotify.com/track/' in spotify_url:
                track_id = spotify_url.split('track/')[1].split('?')[0]
                
                # Obtener información de la canción
                track_info = self.api_call_with_retry(self.sp.track, track_id)
                
                # Formato para mostrar
                artist_names = ", ".join(artist['name'] for artist in track_info['artists'])
                display_text = f"{track_info['name']} - {artist_names}"
                
                # Añadir al creador de playlists
                self.add_to_temp_playlist(track_id, display_text, track_info['external_urls']['spotify'])
                
                return True
            else:
                print(f"URL no válida: {spotify_url}")
                return False
        except Exception as e:
            print(f"Error añadiendo canción por URL: {str(e)}")
            return False

    def search_track_by_query(self, query):
        """
        Busca una canción por texto y muestra los resultados en el panel de búsqueda
        Args:
            query (str): Texto a buscar (artista+canción)
        Returns:
            bool: True si la búsqueda se realizó correctamente
        """
        try:
            # Establecer el texto en el campo de búsqueda
            self.search_input.setText(query)
            # Ejecutar la búsqueda
            self.search_tracks()
            return True
        except Exception as e:
            print(f"Error buscando canción: {str(e)}")
            return False