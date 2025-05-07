# submodules/bluesky/bluesky_manager.py
import os
import json
import requests
import logging
import datetime
from PyQt6 import uic
from pathlib import Path
from PyQt6.QtWidgets import (QMessageBox, QInputDialog, QLineEdit, QDialog,
                          QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                          QDialogButtonBox, QComboBox, QProgressDialog,
                          QApplication, QMenu, QSpinBox, QCheckBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from base_module import PROJECT_ROOT

class BlueskyManager:
    def __init__(self, 
                    parent, 
                    project_root, 
                    bluesky_username=None,
                    bluesky_password=None, 
                    ui_callback=None, 
                    spotify_manager=None, 
                    lastfm_manager=None, 
                    musicbrainz_manager=None,
                    display_manager=None,
                    utils=None
                    ):
        self.parent = parent
        self.project_root = project_root
        self.bluesky_username = bluesky_username
        self.bluesky_password = bluesky_password
        self.logger = logging.getLogger(__name__)
        self.bluesky_manager = None
        self.ui_callback = ui_callback
        self.spotify_manager = spotify_manager
        self.lastfm_manager = lastfm_manager
        self.musicbrainz_manager = musicbrainz_manager
        self.display_manager = display_manager
        self.utils = utils
        self._auth_token = None
        self._auth_refresh_token = None

    def _init_bluesky_manager(self):
        """
        Initialize the Bluesky manager if not already initialized
        """
        # Verificamos si tenemos un usuario de Bluesky configurado
        if not self.bluesky_username:
            self.logger.warning("No hay usuario de Bluesky configurado")
            return False

        self.logger.info(f"Inicializando manejador para usuario de Bluesky: {self.bluesky_username}")
            
        return True


    def configure_bluesky_username(self):
        """
        Show dialog to configure Bluesky username and password
        """
        # Create dialog
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Configurar Bluesky")
        dialog.setMinimumWidth(400)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Username field
        username_layout = QHBoxLayout()
        username_label = QLabel("Nombre de usuario:")
        username_input = QLineEdit()
        if self.bluesky_username:
            username_input.setText(self.bluesky_username)
        username_layout.addWidget(username_label)
        username_layout.addWidget(username_input)
        layout.addLayout(username_layout)
        
        # Password field
        password_layout = QHBoxLayout()
        password_label = QLabel("Contraseña de App:")
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        if self.bluesky_password:
            password_input.setText(self.bluesky_password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(password_input)
        layout.addLayout(password_layout)
        
        # Help text with more detailed instructions
        help_label = QLabel(
            "<b>Instrucciones:</b><br>"
            "1. Para el nombre de usuario, puedes usar:<br>"
            "   - Solo tu nombre (ej: usuario)<br>"
            "   - Tu nombre completo (ej: usuario.bsky.social)<br>"
            "   - Con @ (ej: @usuario)<br>"
            "2. Para la contraseña, debes usar una 'App Password':<br>"
            "   - Ve a Configuración > App Passwords en Bluesky<br>"
            "   - Crea una nueva contraseña para esta aplicación<br>"
            "   - Copia y pega la contraseña aquí<br>"
            "3. <b>NO</b> uses tu contraseña normal de Bluesky"
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        
        # Error label (initially hidden)
        error_label = QLabel("")
        error_label.setStyleSheet("color: red;")
        error_label.setWordWrap(True)
        error_label.setVisible(False)
        layout.addWidget(error_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        test_button = QPushButton("Probar Conexión")
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(test_button)
        button_layout.addWidget(button_box)
        layout.addLayout(button_layout)
        
        # Function to test connection
        def test_connection():
            username = username_input.text().strip()
            password = password_input.text().strip()
            
            if not username or not password:
                error_label.setText("El nombre de usuario y la contraseña son obligatorios")
                error_label.setVisible(True)
                return
            
            # Normalize username format
            if not '@' in username and not '.' in username:
                username = f"{username}.bsky.social"
            elif not '.' in username and username.startswith('@'):
                username = f"{username[1:]}.bsky.social"
            
            # Test authentication
            url = "https://bsky.social/xrpc/com.atproto.server.createSession"
            payload = {
                "identifier": username,
                "password": password
            }
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "MuspyModule/1.0",
                "Accept": "application/json"
            }
            
            try:
                error_label.setText("Probando conexión...")
                error_label.setVisible(True)
                QApplication.processEvents()
                
                response = requests.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    error_label.setStyleSheet("color: green;")
                    error_label.setText("¡Conexión exitosa! Credenciales verificadas.")
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('message', 'Error desconocido')
                        error_label.setText(f"Error: {error_msg}")
                    except:
                        error_label.setText(f"Error: Código {response.status_code}")
                    error_label.setStyleSheet("color: red;")
            except Exception as e:
                error_label.setText(f"Error de conexión: {str(e)}")
                error_label.setStyleSheet("color: red;")
        
        # Connect signals
        test_button.clicked.connect(test_connection)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get values
            username = username_input.text().strip()
            password = password_input.text().strip()
            
            if not username or not password:
                QMessageBox.warning(self.parent, "Error", "El nombre de usuario y la contraseña son obligatorios")
                return False
            
            # Normalize the username
            if not '@' in username and not '.' in username:
                username = f"{username}.bsky.social"
            elif not '.' in username and username.startswith('@'):
                username = f"{username[1:]}.bsky.social"
            
            # Save the credentials
            self.bluesky_username = username
            self.bluesky_password = password
            
            # Clear existing auth token
            self._auth_token = None
            
            QMessageBox.information(self.parent, "Bluesky Configurado", 
                f"Usuario de Bluesky configurado como: {username}")
            
            return True
        
        return False


    def authenticate_bluesky(self):
        """
        Authenticate with Bluesky and get access token
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        if not self.bluesky_username or not self.bluesky_password:
            self.logger.warning("Faltan credenciales de Bluesky")
            return False
        
        try:
            # Construct auth URL
            url = "https://bsky.social/xrpc/com.atproto.server.createSession"
            
            # Ensure the username has the correct format
            # If it doesn't include .bsky.social and it doesn't have an @ prefix, add it
            identifier = self.bluesky_username
            if not '@' in identifier and not '.' in identifier:
                identifier = f"{identifier}.bsky.social"
            elif not '.' in identifier and identifier.startswith('@'):
                identifier = f"{identifier[1:]}.bsky.social"
            
            self.logger.debug(f"Attempting Bluesky authentication with identifier: {identifier}")
            
            # Prepare payload
            payload = {
                "identifier": identifier,
                "password": self.bluesky_password
            }
            
            # Set headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "MuspyModule/1.0",
                "Accept": "application/json"
            }
            
            # Make request
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self._auth_token = data.get("accessJwt")
                self._auth_refresh_token = data.get("refreshJwt")
                self.logger.info("Autenticación con Bluesky exitosa")
                return True
            else:
                # Log detailed error information
                error_message = f"Error de autenticación con Bluesky: {response.status_code}"
                try:
                    error_data = response.json()
                    error_message += f" - {error_data.get('message', response.text)}"
                    self.logger.error(error_message)
                    # Show error to user
                    if hasattr(self, 'parent') and self.parent:
                        QMessageBox.warning(self.parent, "Error de Autenticación", 
                                        f"No se pudo autenticar: {error_data.get('message', 'Error desconocido')}")
                except:
                    self.logger.error(f"{error_message} - {response.text}")
                    if hasattr(self, 'parent') and self.parent:
                        QMessageBox.warning(self.parent, "Error de Autenticación", 
                                        f"No se pudo autenticar. Código: {response.status_code}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error en autenticación con Bluesky: {e}", exc_info=True)
            if hasattr(self, 'parent') and self.parent:
                QMessageBox.warning(self.parent, "Error de Conexión", 
                                f"Error conectando con Bluesky: {str(e)}")
            return False

    def get_auth_headers(self):
        """
        Get authentication headers for Bluesky API requests
        
        Returns:
            dict: Headers with authentication token if available
        """
        headers = {
            "User-Agent": "MuspyModule/1.0",
            "Accept": "application/json"
        }
        
        # Add auth token if available
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        
        return headers



    def search_spotify_artists_on_bluesky(self):
        """
        Search for Spotify followed artists on Bluesky
        """
        # Check if Spotify is enabled
        if not self.spotify_manager.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify no está configurado o la autenticación falló")
            return
        
        # Initialize Bluesky manager
        self._init_bluesky_manager()
        
        # Make sure we're showing the text page during loading
        self.parent.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append("Obteniendo artistas seguidos en Spotify...")
        QApplication.processEvents()
        
        # Get Spotify client
        spotify_client = self.spotify_manager.spotify_auth.get_client()
        if not spotify_client:
            self.ui_callback.append("Error al obtener cliente Spotify. Verifique su autenticación.")
            return
        
        # Define function for progress dialog
        def search_spotify_artists_on_bluesky(update_progress):
            try:
                # Get followed artists from Spotify
                update_progress(0, 100, "Obteniendo artistas seguidos en Spotify...")
                
                all_artists = []
                offset = 0
                limit = 50  # Spotify's maximum limit
                total = 1  # Will be updated after first request
                
                # Paginate through results
                while offset < total:
                    # Fetch current page of artists
                    results = spotify_client.current_user_followed_artists(limit=limit, after=None if offset == 0 else all_artists[-1]['id'])
                    
                    if 'artists' in results and 'items' in results['artists']:
                        # Get artists from this page
                        artists_page = results['artists']['items']
                        all_artists.extend(artists_page)
                        
                        # Update total count
                        total = results['artists']['total']
                        
                        # If we got fewer items than requested, we're done
                        if len(artists_page) < limit:
                            break
                            
                        # Update offset
                        offset += len(artists_page)
                    else:
                        # No more results or error
                        break
                
                # Now search for each artist on Bluesky
                found_artists = []
                total_artists = len(all_artists)
                
                update_progress(20, 100, f"Buscando {total_artists} artistas en Bluesky...")
                
                for i, artist in enumerate(all_artists):
                    artist_name = artist.get('name', '')
                    
                    # Update progress (scale from 20-95%)
                    progress_value = 20 + int((i / total_artists) * 75)
                    update_progress(progress_value, 100, f"Buscando {artist_name} ({i+1}/{total_artists})...")
                    
                    # Check if user canceled
                    if not update_progress(progress_value, 100, f"Buscando {artist_name} ({i+1}/{total_artists})..."):
                        return {"success": False, "message": "Búsqueda cancelada por el usuario"}
                    
                    # Search for artist on Bluesky
                    user_info = self.check_bluesky_user(artist_name)
                    
                    if user_info:
                        # Get profile and recent posts
                        profile = self.get_user_profile(user_info['did'])
                        posts = self.get_recent_posts(user_info['did'])
                        
                        # Create artist entry
                        artist_entry = {
                            'name': artist_name,
                            'handle': user_info['handle'],
                            'did': user_info['did'],
                            'profile': profile,
                            'posts': posts
                        }
                        
                        found_artists.append(artist_entry)
                
                update_progress(100, 100, "Búsqueda completada")
                
                return {
                    "success": True,
                    "artists": found_artists,
                    "total_searched": total_artists
                }
                
            except Exception as e:
                self.logger.error(f"Error searching Spotify artists on Bluesky: {e}", exc_info=True)
                return {"success": False, "message": f"Error: {str(e)}"}
        
        # Execute with progress dialog
        result = self.parent.show_progress_operation(
            search_spotify_artists_on_bluesky,
            title="Buscando Artistas de Spotify en Bluesky",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            artists = result.get("artists", [])
            total_searched = result.get("total_searched", 0)
            
            if not artists:
                self.ui_callback.append(f"No se encontró ninguno de los {total_searched} artistas de Spotify en Bluesky.")
                return
            
            # Display artists in the stacked widget table
            self.display_manager.display_bluesky_artists_in_table(artists)
        else:
            error_msg = result.get("message", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")


    def search_db_artists_on_bluesky(self):
        """
        Search for database artists on Bluesky
        """
        # Initialize Bluesky manager
        self._init_bluesky_manager()
        
        # Ensure we have credentials
        if not self.bluesky_username:
            if not self.configure_bluesky_username():
                return
        
        # Try authentication if needed
        if not self._auth_token and not self.authenticate_bluesky():
            self.ui_callback.append("Error de autenticación con Bluesky. Verifique sus credenciales.")
            return
        
        # Make sure we're showing the text page during loading
        self.parent.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append("Buscando artistas de la base de datos en Bluesky...")
        QApplication.processEvents()
        
        # Path to the artists JSON file
        json_path = Path(PROJECT_ROOT, ".content", "cache", "artists_selected.json")
        
        # Check if file exists
        if not os.path.exists(json_path):
            QMessageBox.warning(self.parent, "Error", "No hay artistas seleccionados. Por favor, carga artistas primero.")
            return
        
        # Load artists from JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
                
            if not artists_data:
                QMessageBox.warning(self.parent, "Error", "No hay artistas en el archivo seleccionado.")
                return
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", f"Error al cargar artistas: {str(e)}")
            return
        
        # Define function for progress dialog
        def search_artists_on_bluesky(update_progress):
            found_artists = []
            total_artists = len(artists_data)
            
            for i, artist in enumerate(artists_data):
                # Get artist name
                artist_name = artist.get('nombre', '')
                if not artist_name:
                    continue
                    
                # Update progress
                progress_value = int((i / total_artists) * 100)
                update_progress(progress_value, 100, f"Buscando {artist_name} ({i+1}/{total_artists})...")
                
                # Check if user canceled
                if not update_progress(progress_value, 100, f"Buscando {artist_name} ({i+1}/{total_artists})..."):
                    return {"success": False, "message": "Búsqueda cancelada por el usuario"}
                
                # Search for artist on Bluesky
                user_info = self.check_bluesky_user(artist_name)
                
                if user_info:
                    # Get profile and recent posts
                    profile = self.get_user_profile(user_info['did'])
                    posts = self.get_recent_posts(user_info['did'])
                    
                    # Create artist entry
                    artist_entry = {
                        'name': artist_name,
                        'handle': user_info['handle'],
                        'did': user_info['did'],
                        'profile': profile,
                        'posts': posts
                    }
                    
                    found_artists.append(artist_entry)
            
            return {
                "success": True,
                "artists": found_artists,
                "total_searched": total_artists
            }
        
        # Execute with progress dialog
        result = self.parent.show_progress_operation(
            search_artists_on_bluesky,
            title="Buscando en Bluesky",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            artists = result.get("artists", [])
            
            if not artists:
                self.ui_callback.append("No se encontró ningún artista en Bluesky.")
                return
            
            # Display artists in the stacked widget table
            self.display_manager.display_bluesky_artists_in_table(artists)
        else:
            error_msg = result.get("message", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")


    def show_lastfm_bluesky_dialog(self):
        """
        Show dialog to select period and number of top artists from LastFM to search on Bluesky
        """
        if not self.lastfm_manager.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "LastFM no está configurado")
            return
        
        # Intentar cargar desde archivo UI primero
        ui_file_path = Path(self.project_root, "ui", "muspy", "lastfm_bluesky_dialog.ui")
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Buscar Top Artistas de LastFM en Bluesky")
        
        # Cargar UI si existe, sino crear manualmente
        if os.path.exists(ui_file_path):
            try:
                uic.loadUi(ui_file_path, dialog)
                # Asegurar las conexiones de botones
                dialog.buttonBox.accepted.connect(dialog.accept)
                dialog.buttonBox.rejected.connect(dialog.reject)
            except Exception as e:
                self.logger.error(f"Error loading UI: {e}")
                self._create_fallback_lastfm_dialog(dialog)
        else:
            self._create_fallback_lastfm_dialog(dialog)
        
        # Usar open() en vez de exec() para no bloquear
        if not hasattr(self, '_dialog_ref'):
            self._dialog_ref = []
        self._dialog_ref.append(dialog)
        
        # Conectar señal para procesar la selección
        dialog.accepted.connect(lambda: self._process_lastfm_dialog_selection(dialog))
        
        # Mostrar de forma no bloqueante
        dialog.open()

    def _process_lastfm_dialog_selection(self, dialog):
        """Procesa la selección del diálogo de LastFM Bluesky"""
        # Obtener los valores seleccionados
        period = dialog.period_combo.currentData()
        count = dialog.count_spin.value()
        
        # Buscar artistas de LastFM en Bluesky
        self.search_lastfm_artists_on_bluesky(period, count)
        
        # Limpiar referencia
        if hasattr(self, '_dialog_ref') and dialog in self._dialog_ref:
            self._dialog_ref.remove(dialog)

    def _create_fallback_lastfm_dialog(self, dialog):
        """Crea un diálogo de fallback si no se puede cargar el UI"""
        dialog.setMinimumWidth(350)
        
        # Crear layout
        layout = QVBoxLayout(dialog)
        
        # Period selection
        period_layout = QHBoxLayout()
        period_label = QLabel("Período de tiempo:")
        period_combo = QComboBox()
        period_combo.addItem("7 días", "7day")
        period_combo.addItem("1 mes", "1month")
        period_combo.addItem("3 meses", "3month")
        period_combo.addItem("6 meses", "6month")
        period_combo.addItem("12 meses", "12month")
        period_combo.addItem("Todo el tiempo", "overall")
        period_combo.setCurrentIndex(5)  # Default to "Todo el tiempo"
        period_layout.addWidget(period_label)
        period_layout.addWidget(period_combo)
        layout.addLayout(period_layout)
        
        # Count selection
        count_layout = QHBoxLayout()
        count_label = QLabel("Número de artistas:")
        count_spin = QSpinBox()
        count_spin.setRange(5, 5000)
        count_spin.setValue(50)
        count_spin.setSingleStep(5)
        count_layout.addWidget(count_label)
        count_layout.addWidget(count_spin)
        layout.addLayout(count_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Guardar referencias para acceder después
        dialog.period_combo = period_combo
        dialog.count_spin = count_spin
        dialog.buttonBox = button_box

    def search_lastfm_artists_on_bluesky(self, period, count):
        """
        Search for LastFM top artists on Bluesky
        
        Args:
            period (str): Period for LastFM top artists
            count (int): Number of artists to fetch
        """
        if not self.lastfm_manager.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "LastFM no está configurado")
            return
        
        # Initialize Bluesky manager
        self._init_bluesky_manager()
        
        # Make sure we're showing the text page during loading
        self.parent.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Obteniendo top {count} artistas de LastFM para el período {period}...")
        QApplication.processEvents()
        
        # Define function for progress dialog
        def search_lastfm_artists_on_bluesky_worker(progress_callback, status_callback, **kwargs):
            try:
                # First get top artists from LastFM
                progress_callback(0)
                status_callback("Obteniendo top artistas de LastFM...")
                
                top_artists = self.lastfm_manager.get_lastfm_top_artists_direct(count, period)
                
                if not top_artists:
                    return {"success": False, "message": "No se pudieron obtener artistas de LastFM"}
                
                # Now search for each artist on Bluesky
                found_artists = []
                total_artists = len(top_artists)
                
                progress_callback(20)
                status_callback(f"Buscando {total_artists} artistas en Bluesky...")
                
                for i, artist in enumerate(top_artists):
                    artist_name = artist.get('name', '')
                    
                    # Update progress (scale from 20-95%)
                    progress_value = 20 + int((i / total_artists) * 75)
                    progress_callback(progress_value)
                    status_callback(f"Buscando {artist_name} ({i+1}/{total_artists})...")
                    
                    # Search for artist on Bluesky
                    user_info = self.check_bluesky_user(artist_name)
                    
                    if user_info:
                        # Get profile and recent posts
                        profile = self.get_user_profile(user_info['did'])
                        posts = self.get_recent_posts(user_info['did'])
                        
                        # Create artist entry
                        artist_entry = {
                            'name': artist_name,
                            'handle': user_info['handle'],
                            'did': user_info['did'],
                            'profile': profile,
                            'posts': posts,
                            'lastfm_playcount': artist.get('playcount', 0)
                        }
                        
                        found_artists.append(artist_entry)
                
                progress_callback(100)
                status_callback("Búsqueda completada")
                
                return {
                    "success": True,
                    "artists": found_artists,
                    "total_searched": total_artists
                }
                
            except Exception as e:
                self.logger.error(f"Error searching LastFM artists on Bluesky: {e}", exc_info=True)
                return {"success": False, "message": f"Error: {str(e)}"}
        
        # Execute with progress dialog
        result = self.parent.show_progress_operation(
            search_lastfm_artists_on_bluesky_worker,
            title="Buscando Artistas de LastFM en Bluesky",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            artists = result.get("artists", [])
            total_searched = result.get("total_searched", 0)
            
            if not artists:
                self.ui_callback.append(f"No se encontró ninguno de los {total_searched} artistas de LastFM en Bluesky.")
                return
            
            # Display artists in the stacked widget table
            self.display_manager.display_bluesky_artists_in_table(artists)
        else:
            error_msg = result.get("message", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")

    def search_mb_collection_on_bluesky(self):
        """
        Search for MusicBrainz collection artists on Bluesky
        """
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_manager.musicbrainz_enabled:
            QMessageBox.warning(self.parent, "Error", "MusicBrainz no está configurado o la autenticación falló")
            return
        
        # Check if authenticated
        is_auth = self.musicbrainz_auth.is_authenticated()
        
        if not is_auth:
            # Prompt for login if not authenticated
            reply = QMessageBox.question(
                self.parent, 
                "Autenticación Requerida", 
                "Necesita iniciar sesión en MusicBrainz para acceder a sus colecciones. ¿Iniciar sesión ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if not self.authenticate_musicbrainz_silently():
                    QMessageBox.warning(self.parent, "Error", "Falló la autenticación. Por favor, intente de nuevo.")
                    return
            else:
                return
        
        # Get collections list if we haven't done so yet
        if not hasattr(self, '_mb_collections') or not self._mb_collections:
            self._mb_collections = self.fetch_all_musicbrainz_collections()
        
        if not self._mb_collections:
            QMessageBox.warning(self.parent, "Error", "No se encontraron colecciones de MusicBrainz")
            return
        
        # Show collection selection dialog
        collection = self._select_musicbrainz_collection()
        
        if not collection:
            return  # User canceled
        
        # Initialize Bluesky manager
        self._init_bluesky_manager()
        
        # Make sure we're showing the text page during loading
        self.parent.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Obteniendo artistas de la colección '{collection['name']}'...")
        QApplication.processEvents()
        
        # Define function for progress dialog
        def search_mb_collection_on_bluesky(update_progress):
            try:
                # First get artists from the collection
                update_progress(0, 100, "Obteniendo artistas de la colección...")
                
                # Get collection contents
                collection_data = self.get_collection_contents(collection['id'], 'artist')
                if not collection_data:
                    return {"success": False, "message": "No se pudieron obtener los artistas de la colección"}
                
                # Extract artists from collection
                artists = []
                for item in collection_data:
                    if 'name' in item:
                        artists.append({
                            'name': item['name'],
                            'mbid': item.get('id', '')
                        })
                
                if not artists:
                    return {"success": False, "message": "No se encontraron artistas en la colección"}
                
                # Now search for each artist on Bluesky
                found_artists = []
                total_artists = len(artists)
                
                update_progress(20, 100, f"Buscando {total_artists} artistas en Bluesky...")
                
                for i, artist in enumerate(artists):
                    artist_name = artist.get('name', '')
                    
                    # Update progress (scale from 20-95%)
                    progress_value = 20 + int((i / total_artists) * 75)
                    update_progress(progress_value, 100, f"Buscando {artist_name} ({i+1}/{total_artists})...")
                    
                    # Check if user canceled
                    if not update_progress(progress_value, 100, f"Buscando {artist_name} ({i+1}/{total_artists})..."):
                        return {"success": False, "message": "Búsqueda cancelada por el usuario"}
                    
                    # Search for artist on Bluesky
                    user_info = self.check_bluesky_user(artist_name)
                    
                    if user_info:
                        # Get profile and recent posts
                        profile = self.get_user_profile(user_info['did'])
                        posts = self.get_recent_posts(user_info['did'])
                        
                        # Create artist entry
                        artist_entry = {
                            'name': artist_name,
                            'handle': user_info['handle'],
                            'did': user_info['did'],
                            'profile': profile,
                            'posts': posts,
                            'mbid': artist.get('mbid', '')
                        }
                        
                        found_artists.append(artist_entry)
                
                update_progress(100, 100, "Búsqueda completada")
                
                return {
                    "success": True,
                    "artists": found_artists,
                    "total_searched": total_artists
                }
                
            except Exception as e:
                self.logger.error(f"Error searching MB collection on Bluesky: {e}", exc_info=True)
                return {"success": False, "message": f"Error: {str(e)}"}
        
        # Execute with progress dialog
        result = self.parent.show_progress_operation(
            search_mb_collection_on_bluesky,
            title=f"Buscando Artistas de '{collection['name']}' en Bluesky",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            artists = result.get("artists", [])
            total_searched = result.get("total_searched", 0)
            
            if not artists:
                self.ui_callback.append(f"No se encontró ninguno de los {total_searched} artistas de MusicBrainz en Bluesky.")
                return
            
            # Display artists in the stacked widget table
            self.display_manager.display_bluesky_artists_in_table(artists)
        else:
            error_msg = result.get("message", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")


    def follow_artist_on_bluesky(self, did, name, show_messages=True):
        """
        Follow an artist on Bluesky
        
        Args:
            did (str): DID of the artist
            name (str): Name of the artist for display
            show_messages (bool): Whether to show success/error messages
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not did or not self.bluesky_username:
            if show_messages:
                QMessageBox.warning(self.parent, "Error", "Bluesky no está configurado correctamente")
            return False
        
        # Ensure we're authenticated
        if not self._auth_token and not self.authenticate_bluesky():
            if show_messages and not self.configure_bluesky_username():
                return False
            if not self.authenticate_bluesky():
                if show_messages:
                    QMessageBox.warning(self.parent, "Error", "No se pudo autenticar con Bluesky. Verifique sus credenciales.")
                return False
        
        try:
            # Correct API URL for creating records (including follows)
            url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
            
            # Get our own DID from auth session
            if not hasattr(self, '_user_did') or not self._user_did:
                # We need to get our own DID from the session data
                session_url = "https://bsky.social/xrpc/com.atproto.server.getSession"
                session_response = requests.get(session_url, headers=self.get_auth_headers())
                
                if session_response.status_code == 200:
                    session_data = session_response.json()
                    self._user_did = session_data.get('did')
                else:
                    if show_messages:
                        QMessageBox.warning(self.parent, "Error", f"No se pudo obtener información de sesión: {session_response.status_code}")
                    return False
            
            # Prepare payload according to API specification
            payload = {
                "repo": self._user_did,
                "collection": "app.bsky.graph.follow",
                "record": {
                    "subject": did,
                    "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
                }
            }
            
            # Make the request with auth headers
            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json"
            
            self.logger.debug(f"Follow request payload: {payload}")
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                if show_messages:
                    QMessageBox.information(self.parent, "Éxito", f"Ahora sigues a {name} en Bluesky")
                return True
            elif response.status_code == 401:
                # Token expired, try to re-authenticate
                if self.authenticate_bluesky():
                    # Retry the request recursively
                    return self.follow_artist_on_bluesky(did, name, show_messages)
                else:
                    if show_messages:
                        QMessageBox.warning(self.parent, "Error", "Error de autenticación con Bluesky. Verifique sus credenciales.")
                    return False
            else:
                error_message = f"No se pudo seguir a {name} en Bluesky: {response.status_code}"
                try:
                    error_data = response.json()
                    error_message += f" - {error_data.get('message', '')}"
                except:
                    pass
                    
                self.logger.error(f"Follow error: {error_message}")
                self.logger.error(f"Response content: {response.text}")
                if show_messages:
                    QMessageBox.warning(self.parent, "Error", error_message)
                return False
        
        except Exception as e:
            self.logger.error(f"Error following artist on Bluesky: {e}")
            if show_messages:
                QMessageBox.warning(self.parent, "Error", f"Error al seguir al artista: {str(e)}")
            return False

    def follow_selected_bluesky_artists(self, table):
        """
        Follow multiple artists selected via checkboxes in the Bluesky table
        
        Args:
            table (QTableWidget): The table containing artist checkboxes
        """
        if not self.bluesky_username:
            QMessageBox.warning(self.parent, "Error", "Bluesky no está configurado correctamente")
            return
        
        # Ensure we're authenticated
        if not self._auth_token and not self.authenticate_bluesky():
            if not self.configure_bluesky_username():
                return
            if not self.authenticate_bluesky():
                QMessageBox.warning(self.parent, "Error", "No se pudo autenticar con Bluesky. Verifique sus credenciales.")
                return
                
        # Recolectar artistas seleccionados
        artists_to_follow = []
        
        for row in range(table.rowCount()):
            # Obtener el widget de la columna checkbox (primera columna)
            checkbox_widget = table.cellWidget(row, 0)
            if not checkbox_widget:
                continue
                
            # Buscar el checkbox dentro del widget
            checkbox = None
            for child in checkbox_widget.children():
                if isinstance(child, QCheckBox):
                    checkbox = child
                    break
                    
            if checkbox and checkbox.isChecked():
                # Obtener datos del artista desde el checkbox
                artist_data = checkbox.property("artist_data")
                if artist_data and 'did' in artist_data and artist_data['did']:
                    artists_to_follow.append(artist_data)
        
        if not artists_to_follow:
            QMessageBox.warning(self.parent, "Aviso", "No hay artistas seleccionados para seguir")
            return
            
        # Preguntar confirmación
        reply = QMessageBox.question(
            self.parent,
            "Confirmar seguimiento masivo",
            f"¿Estás seguro de que quieres seguir a {len(artists_to_follow)} artistas en Bluesky?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        # Crear diálogo de progreso
        progress = QProgressDialog("Siguiendo artistas en Bluesky...", "Cancelar", 0, len(artists_to_follow), self.parent)
        progress.setWindowTitle("Seguimiento masivo")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Seguir a cada artista
        success_count = 0
        fail_count = 0
        
        for i, artist in enumerate(artists_to_follow):
            # Actualizar progreso
            progress.setValue(i)
            progress.setLabelText(f"Siguiendo a {artist['name']} ({i+1}/{len(artists_to_follow)})...")
            QApplication.processEvents()
            
            # Verificar si se canceló
            if progress.wasCanceled():
                break
                
            # Seguir al artista
            if self.follow_artist_on_bluesky(artist['did'], artist['name'], show_messages=False):
                success_count += 1
            else:
                fail_count += 1
                
        # Cerrar diálogo de progreso
        progress.setValue(len(artists_to_follow))
        
        # Mostrar resultados
        result_message = f"Proceso completado:\n" \
                        f"- Artistas seguidos con éxito: {success_count}\n" \
                        f"- Errores: {fail_count}"
        
        QMessageBox.information(self.parent, "Resultado del seguimiento masivo", result_message)

    def check_bluesky_user(self, artist_name):
        """
        Check if an artist exists on Bluesky by name
        
        Args:
            artist_name (str): Name of the artist to check
            
        Returns:
            dict or None: User info if found, None otherwise
        """
        if not self.bluesky_username:
            self.logger.error("No Bluesky username configured")
            return None
        
        # Ensure we're authenticated
        if not self._auth_token and not self.authenticate_bluesky():
            if not self.configure_bluesky_username():
                return None
            if not self.authenticate_bluesky():
                return None
        
        try:
            # Normalize the artist name for search
            search_name = artist_name.strip().lower()
            
            # Construct search URL
            url = "https://bsky.social/xrpc/app.bsky.actor.searchActors"
            params = {
                "q": search_name,
                "limit": 5  # Limit to top results
            }
            
            # Make the request with auth headers
            headers = self.get_auth_headers()
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                actors = data.get("actors", [])
                
                # Look for exact or close matches
                for actor in actors:
                    actor_name = actor.get("displayName", "").lower()
                    handle = actor.get("handle", "")
                    did = actor.get("did", "")
                    
                    # Check if this is a good match
                    if (search_name in actor_name or 
                        search_name.replace(" ", "") in actor_name.replace(" ", "") or
                        search_name in handle.lower()):
                        
                        # Create URL for profile
                        profile_url = f"https://bsky.app/profile/{handle}"
                        
                        return {
                            "handle": handle,
                            "did": did,
                            "name": actor.get("displayName", artist_name),
                            "url": profile_url
                        }
                
                return None
            elif response.status_code == 401:
                # Token expired, try to re-authenticate
                self.logger.warning("Token expirado, reintentando autenticación")
                if self.authenticate_bluesky():
                    # Retry the request recursively
                    return self.check_bluesky_user(artist_name)
                else:
                    return None
            else:
                self.logger.error(f"Error searching Bluesky for {artist_name}: {response.status_code}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error checking Bluesky for {artist_name}: {e}")
            return None

       
    def get_user_profile(self, did):
        """
        Get the profile of a Bluesky user by DID
        
        Args:
            did (str): Decentralized ID of the user
            
        Returns:
            dict or None: Profile info if found, None otherwise
        """
        if not did:
            return None
        
        # Ensure we're authenticated
        if not self._auth_token and not self.authenticate_bluesky():
            return None
        
        try:
            # Construct API URL
            url = "https://bsky.social/xrpc/app.bsky.actor.getProfile"
            params = {"actor": did}
            
            # Make the request with auth headers
            headers = self.get_auth_headers()
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token expired, try to re-authenticate
                if self.authenticate_bluesky():
                    # Retry the request recursively
                    return self.get_user_profile(did)
                else:
                    return None
            else:
                self.logger.error(f"Error fetching profile for {did}: {response.status_code}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error getting user profile: {e}")
            return None

    def get_recent_posts(self, did, limit=5):
        """
        Get recent posts from a Bluesky user
        
        Args:
            did (str): Decentralized ID of the user
            limit (int): Maximum number of posts to retrieve
            
        Returns:
            list: List of recent posts or empty list on error
        """
        if not did:
            return []
        
        # Ensure we're authenticated
        if not self._auth_token and not self.authenticate_bluesky():
            return []
        
        try:
            # Construct API URL
            url = "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed"
            params = {
                "actor": did,
                "limit": limit
            }
            
            # Make the request with auth headers
            headers = self.get_auth_headers()
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                # Extract feed items
                for feed_item in data.get("feed", []):
                    post = feed_item.get("post", {})
                    post_record = post.get("record", {})
                    
                    if post_record:
                        posts.append({
                            "text": post_record.get("text", ""),
                            "created_at": post_record.get("createdAt", "")
                        })
                
                return posts
            elif response.status_code == 401:
                # Token expired, try to re-authenticate
                if self.authenticate_bluesky():
                    # Retry the request recursively
                    return self.get_recent_posts(did, limit)
                else:
                    return []
            else:
                self.logger.error(f"Error fetching posts for {did}: {response.status_code}")
                return []
        
        except Exception as e:
            self.logger.error(f"Error getting recent posts: {e}")
            return []

