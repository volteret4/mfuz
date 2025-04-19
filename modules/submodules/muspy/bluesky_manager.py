# submodules/bluesky/bluesky_manager.py
import os
import json
import requests
import logging
from PyQt6.QtWidgets import (QMessageBox, QInputDialog, QLineEdit, QDialog,
                          QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                          QDialogButtonBox, QComboBox, QProgressDialog,
                          QApplication, QMenu)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from base_module import PROJECT_ROOT

class BlueskyManager:
    def __init__(self, parent, project_root, bluesky_username=None, ui_callback=None, spotify_manager=None, lastfm_manager=None, musicbrainz_manager=None):
        self.parent = parent
        self.project_root = project_root
        self.bluesky_username = bluesky_username
        self.logger = logging.getLogger(__name__)
        self.bluesky_manager = None
        self.ui_callback = ui_callback
        self.spotify_manager = spotify_manager
        self.lastfm_manager = lastfm_manager
        self.musicbrainz_manager = musicbrainz_manager
        
    def _init_bluesky_manager(self):
        """
        Initialize the Bluesky manager if not already initialized
        """
        if not hasattr(self, 'bluesky_manager'):
            from tools.bluesky_manager import BlueskyManager
            self.bluesky_manager = BlueskyManager(
                parent=self.parent, 
                project_root=self.project_root,
                username=self.bluesky_username
            )
            
        return self.bluesky_manager



    def configure_bluesky_username(self):
        """
        Show dialog to configure Bluesky username
        """
        # Get current username or empty string
        current_username = self.bluesky_username or ""
        
        # Show input dialog
        username, ok = QInputDialog.getText(
            self,
            "Configurar Bluesky",
            "Introduzca su nombre de usuario de Bluesky:",
            QLineEdit.EchoMode.Normal,
            current_username
        )
        
        if ok and username:
            # Normalize the username
            username = username.strip().lower()
            
            # Remove .bsky.social if present (will be added when needed)
            if username.endswith('.bsky.social'):
                username = username.replace('.bsky.social', '')
            
            # Save the username
            self.bluesky_username = username
            
            # Reinitialize Bluesky manager if it exists
            if hasattr(self, 'bluesky_manager'):
                self.username = username
            
            QMessageBox.information(self, "Bluesky Configurado", 
                                f"Usuario de Bluesky configurado como: {username}")



    def search_spotify_artists_on_bluesky(self):
        """
        Search for Spotify followed artists on Bluesky
        """
        # Check if Spotify is enabled
        if not self.spotify_manager.ensure_spotify_auth():
            QMessageBox.warning(self, "Error", "Spotify no está configurado o la autenticación falló")
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
            self.display_bluesky_artists_in_table(artists)
        else:
            error_msg = result.get("message", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")


    def search_db_artists_on_bluesky(self):
        """
        Search for database artists on Bluesky
        """
        # Initialize Bluesky manager
        self._init_bluesky_manager()
        
        # Make sure we're showing the text page during loading
        self.parent.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append("Buscando artistas de la base de datos en Bluesky...")
        QApplication.processEvents()
        
        # Path to the artists JSON file
        json_path = os.path.join(PROJECT_ROOT, ".content", "cache", "artists_selected.json")
        
        # Check if file exists
        if not os.path.exists(json_path):
            QMessageBox.warning(self, "Error", "No hay artistas seleccionados. Por favor, carga artistas primero.")
            return
        
        # Load artists from JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
                
            if not artists_data:
                QMessageBox.warning(self, "Error", "No hay artistas en el archivo seleccionado.")
                return
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar artistas: {str(e)}")
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
            self.display_bluesky_artists_in_table(artists)
        else:
            error_msg = result.get("message", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")


    def show_lastfm_bluesky_dialog(self):
        """
        Show dialog to select period and number of top artists from LastFM to search on Bluesky
        """
        if not self.lastfm_manager.lastfm_enabled:
            QMessageBox.warning(self, "Error", "LastFM no está configurado")
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Buscar Top Artistas de LastFM en Bluesky")
        dialog.setMinimumWidth(350)
        
        # Create layout
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
        count_spin.setRange(5, 200)
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
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get selected values
            period = period_combo.currentData()
            count = count_spin.value()
            
            # Search for LastFM artists on Bluesky
            self.search_lastfm_artists_on_bluesky(period, count)


    def search_lastfm_artists_on_bluesky(self, period, count):
        """
        Search for LastFM top artists on Bluesky
        
        Args:
            period (str): Period for LastFM top artists
            count (int): Number of artists to fetch
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "LastFM no está configurado")
            return
        
        # Initialize Bluesky manager
        self._init_bluesky_manager()
        
        # Make sure we're showing the text page during loading
        self.parent.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Obteniendo top {count} artistas de LastFM para el período {period}...")
        QApplication.processEvents()
        
        # Define function for progress dialog
        def search_lastfm_artists_on_bluesky(update_progress):
            try:
                # First get top artists from LastFM
                update_progress(0, 100, "Obteniendo top artistas de LastFM...")
                
                top_artists = self.get_lastfm_top_artists_direct(count, period)
                
                if not top_artists:
                    return {"success": False, "message": "No se pudieron obtener artistas de LastFM"}
                
                # Now search for each artist on Bluesky
                found_artists = []
                total_artists = len(top_artists)
                
                update_progress(20, 100, f"Buscando {total_artists} artistas en Bluesky...")
                
                for i, artist in enumerate(top_artists):
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
                            'lastfm_playcount': artist.get('playcount', 0)
                        }
                        
                        found_artists.append(artist_entry)
                
                update_progress(100, 100, "Búsqueda completada")
                
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
            search_lastfm_artists_on_bluesky,
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
            self.display_bluesky_artists_in_table(artists)
        else:
            error_msg = result.get("message", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")


    def search_mb_collection_on_bluesky(self):
        """
        Search for MusicBrainz collection artists on Bluesky
        """
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_manager.musicbrainz_enabled:
            QMessageBox.warning(self, "Error", "MusicBrainz no está configurado o la autenticación falló")
            return
        
        # Check if authenticated
        is_auth = self.musicbrainz_auth.is_authenticated()
        
        if not is_auth:
            # Prompt for login if not authenticated
            reply = QMessageBox.question(
                self, 
                "Autenticación Requerida", 
                "Necesita iniciar sesión en MusicBrainz para acceder a sus colecciones. ¿Iniciar sesión ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if not self.authenticate_musicbrainz_silently():
                    QMessageBox.warning(self, "Error", "Falló la autenticación. Por favor, intente de nuevo.")
                    return
            else:
                return
        
        # Get collections list if we haven't done so yet
        if not hasattr(self, '_mb_collections') or not self._mb_collections:
            self._mb_collections = self.fetch_all_musicbrainz_collections()
        
        if not self._mb_collections:
            QMessageBox.warning(self, "Error", "No se encontraron colecciones de MusicBrainz")
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
            self.display_bluesky_artists_in_table(artists)
        else:
            error_msg = result.get("message", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")




    def handle_bluesky_artist_selection(self, table):
        """
        Handle selection of a Bluesky artist in the table
        
        Args:
            table (QTableWidget): Table with selected artist
        """
        # Get the selected row
        selected_rows = table.selectedIndexes()
        if not selected_rows:
            return
        
        # Get the row of the first selected item
        row = selected_rows[0].row()
        
        # Get artist data from the first column
        item = table.item(row, 0)
        if not item:
            return
        
        artist_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(artist_data, dict):
            return
        
        # Find sidebar elements in the bluesky_page
        bluesky_page = None
        for i in range(self.stackedWidget.count()):
            widget = self.stackedWidget.widget(i)
            if widget.objectName() == "bluesky_page":
                bluesky_page = widget
                break
        
        if not bluesky_page:
            return
        
        image_label = bluesky_page.findChild(QLabel, "bluesky_selected_artist_foto")
        messages_text = bluesky_page.findChild(QTextEdit, "bluesky_selected_artist_mensajes")
        sidebar_panel = bluesky_page.findChild(QWidget, "bluesky_selected_artist_panel")
        
        # Make sure panel is visible
        if sidebar_panel:
            sidebar_panel.setVisible(True)
        
        # Update image if available
        if image_label:
            # Try to get the avatar URL from profile
            avatar_url = None
            if 'profile' in artist_data and isinstance(artist_data['profile'], dict):
                avatar = artist_data['profile'].get('avatar')
                if avatar:
                    avatar_url = avatar
            
            if avatar_url:
                # Download and display the image
                self.load_image_for_label(image_label, avatar_url)
            else:
                # Clear image if no avatar available
                image_label.clear()
                image_label.setText("No image available")
        
        # Update messages panel
        if messages_text:
            messages_text.clear()
            posts = artist_data.get('posts', [])
            
            if posts:
                messages_text.setHtml("<h3>Recent Posts</h3>")
                
                for i, post in enumerate(posts):
                    text = post.get('text', '')
                    created_at = post.get('created_at', '')
                    
                    # Format date if available
                    date_str = ""
                    if created_at:
                        try:
                            # Convert ISO 8601 format to readable date
                            from datetime import datetime
                            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                        except:
                            date_str = created_at
                    
                    # Add formatted post to text edit
                    messages_text.append(f"<p><b>{date_str}</b></p>")
                    messages_text.append(f"<p>{text}</p>")
                    
                    # Add separator between posts
                    if i < len(posts) - 1:
                        messages_text.append("<hr>")
            else:
                messages_text.setPlainText("No recent posts available")



    def load_image_for_label(self, label, url):
        """
        Load an image from URL and display it in a QLabel
        
        Args:
            label (QLabel): Label to display the image in
            url (str): URL of the image to load
        """
        try:
            # Import Qt modules
            from PyQt6.QtCore import QByteArray, QBuffer
            from PyQt6.QtGui import QPixmap, QImage
            
            # Create request
            response = requests.get(url)
            
            if response.status_code == 200:
                # Load image data into QPixmap
                img_data = QByteArray(response.content)
                buffer = QBuffer(img_data)
                buffer.open(QBuffer.OpenModeFlag.ReadOnly)
                
                # Load image
                image = QImage()
                image.load(buffer, "")
                
                # Create pixmap and scale to fit label while maintaining aspect ratio
                pixmap = QPixmap.fromImage(image)
                label_size = label.size()
                scaled_pixmap = pixmap.scaled(
                    label_size.width(), label_size.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Set pixmap to label
                label.setPixmap(scaled_pixmap)
            else:
                label.clear()
                label.setText(f"Failed to load image: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error loading image from {url}: {e}")
            label.clear()
            label.setText("Error loading image")


    def show_bluesky_context_menu(self, position):
        """
        Show context menu for Bluesky artists in the table
        
        Args:
            position (QPoint): Position where the context menu was requested
        """
        table = self.sender()
        if not table:
            return
        
        item = table.itemAt(position)
        if not item:
            return
        
        # Get the artist data from the item
        artist_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(artist_data, dict):
            return
        
        name = artist_data.get('name', '')
        handle = artist_data.get('handle', '')
        did = artist_data.get('did', '')
        url = artist_data.get('url', '')
        
        if not handle or not url:
            return
        
        # Create context menu
        menu = QMenu(self)
        
        # Add actions
        open_profile_action = QAction(f"Abrir perfil de {name} en Bluesky", self)
        open_profile_action.triggered.connect(lambda: self.open_url(url))
        menu.addAction(open_profile_action)
        
        # Add follow action if we have a DID and username
        if did and self.bluesky_username:
            follow_action = QAction(f"Seguir a {name} en Bluesky", self)
            follow_action.triggered.connect(lambda: self.follow_artist_on_bluesky(did, name))
            menu.addAction(follow_action)
        
        copy_url_action = QAction("Copiar URL", self)
        copy_url_action.triggered.connect(lambda: self.copy_to_clipboard(url))
        menu.addAction(copy_url_action)
        
        copy_handle_action = QAction("Copiar handle", self)
        copy_handle_action.triggered.connect(lambda: self.copy_to_clipboard(handle))
        menu.addAction(copy_handle_action)
        
        # If we have artist name, add related actions
        if name:
            menu.addSeparator()
            
            # Add Muspy actions if configured
            if hasattr(self, 'muspy_username') and self.muspy_username:
                follow_muspy_action = QAction(f"Seguir a {name} en Muspy", self)
                follow_muspy_action.triggered.connect(lambda: self.follow_artist_from_name(name))
                menu.addAction(follow_muspy_action)
            
            # Add Spotify actions if enabled
            if self.spotify_enabled:
                follow_spotify_action = QAction(f"Seguir a {name} en Spotify", self)
                follow_spotify_action.triggered.connect(lambda: self.follow_artist_on_spotify_by_name(name))
                menu.addAction(follow_spotify_action)
        
        # Show menu
        menu.exec(table.mapToGlobal(position))


    def follow_artist_on_bluesky(self, did, name):
        """
        Follow an artist on Bluesky
        
        Args:
            did (str): DID of the artist
            name (str): Name of the artist for display
        """
        if not did or not self.bluesky_username:
            QMessageBox.warning(self, "Error", "Bluesky no está configurado correctamente")
            return
        
        # Initialize Bluesky manager if needed
        bluesky_manager = self._init_bluesky_manager()
        
        try:
            # Follow the artist
            success = follow_user(did)
            
            if success:
                QMessageBox.information(self, "Éxito", f"Ahora sigues a {name} en Bluesky")
            else:
                QMessageBox.warning(self, "Error", f"No se pudo seguir a {name} en Bluesky. Comprueba tus credenciales.")
        except Exception as e:
            self.logger.error(f"Error following artist on Bluesky: {e}")
            QMessageBox.warning(self, "Error", f"Error al seguir al artista: {str(e)}")



    def open_url(self, url):
        """
        Open a URL in the default browser
        
        Args:
            url (str): URL to open
        """
        import webbrowser
        webbrowser.open(url)

    def copy_to_clipboard(self, text):
        """
        Copy text to clipboard
        
        Args:
            text (str): Text to copy
        """
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)    
