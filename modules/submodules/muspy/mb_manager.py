# submodules/musicbrainz/mb_manager.py
import os
import json
import requests
import logging
from PyQt6.QtWidgets import (QMessageBox, QInputDialog, QLineEdit, QDialog,
                          QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                          QDialogButtonBox, QComboBox, QProgressDialog)
from PyQt6.QtCore import Qt, QThread

class MusicBrainzManager:
    def __init__(self, parent, project_root, musicbrainz_username=None, musicbrainz_password=None):
        self.parent = parent
        self.project_root = project_root
        self.musicbrainz_username = musicbrainz_username
        self.musicbrainz_password = musicbrainz_password
        self.logger = logging.getLogger(__name__)
        self.musicbrainz_auth = None
        self.musicbrainz_enabled = bool(self.musicbrainz_username)
        self._mb_collections = None
        
        # Initialize MusicBrainz auth manager
        if self.musicbrainz_enabled:
            try:
                from tools.musicbrainz_login import MusicBrainzAuthManager
                self.musicbrainz_auth = MusicBrainzAuthManager(
                    username=self.musicbrainz_username,
                    password=self.musicbrainz_password,
                    parent_widget=parent,
                    project_root=project_root
                )
                self.logger.info(f"MusicBrainz auth manager initialized for user: {self.musicbrainz_username}")
            except Exception as e:
                self.logger.error(f"Error initializing MusicBrainz auth manager: {e}", exc_info=True)
                self.musicbrainz_enabled = False



    def show_musicbrainz_collection_menu(self):
        """Display a menu with MusicBrainz collection options"""
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_enabled:
            QMessageBox.warning(self, "Error", "MusicBrainz credentials not configured")
            return
        
        # Check if authenticated
        is_auth = self.musicbrainz_auth.is_authenticated()
        
        if not is_auth:
            # Prompt for login if not authenticated
            self.authenticate_musicbrainz_silently()
            # Recheck authentication status after login attempt
            is_auth = hasattr(self, 'musicbrainz_auth') and self.musicbrainz_auth.is_authenticated()
        
        # Create menu
        menu = QMenu(self)
        
        if not is_auth:
            # Add login action if still not authenticated
            login_action = QAction("Login to MusicBrainz...", self)
            login_action.triggered.connect(self.authenticate_musicbrainz_silently)
            menu.addAction(login_action)
        else:
            # We're authenticated, fetch collections
            # Use cached collections if available
            collections = []
            if hasattr(self, '_mb_collections') and self._mb_collections:
                collections = self._mb_collections
            else:
                # Try API method first
                if hasattr(self.musicbrainz_auth, 'get_collections_by_api'):
                    collections = self.musicbrainz_auth.get_collections_by_api()
                
                # Fallback to HTML parsing if API method failed or doesn't exist
                if not collections and hasattr(self.musicbrainz_auth, 'get_user_collections'):
                    collections = self.musicbrainz_auth.get_user_collections()
                
                # Cache collections for later use
                self._mb_collections = collections
            
            # Add "Show Collections" submenu
            collections_menu = QMenu("Show Collection", self)
            
            if collections:
                for collection in collections:
                    collection_name = collection.get('name', 'Unnamed Collection')
                    collection_id = collection.get('id')
                    collection_count = collection.get('entity_count', 0)
                    
                    if collection_id:
                        collection_action = QAction(f"{collection_name} ({collection_count} releases)", self)
                        collection_action.setProperty("collection_id", collection_id)
                        collection_action.triggered.connect(lambda checked, cid=collection_id, cname=collection_name: 
                                                        self.show_musicbrainz_collection(cid, cname))
                        collections_menu.addAction(collection_action)
            else:
                no_collections_action = QAction("No collections found", self)
                no_collections_action.setEnabled(False)
                collections_menu.addAction(no_collections_action)
                
                # Add refresh action
                refresh_action = QAction("Refresh Collections", self)
                refresh_action.triggered.connect(self.fetch_all_musicbrainz_collections)
                collections_menu.addAction(refresh_action)
                
            menu.addMenu(collections_menu)
            
            # Add "Add Albums to Collection" submenu
            add_menu = QMenu("Add Albums to Collection", self)
            
            # First check if we have the albums_selected.json file
            albums_json_path = os.path.join(PROJECT_ROOT, ".content", "cache", "albums_selected.json")
            
            if not os.path.exists(albums_json_path):
                no_albums_action = QAction("No albums selected (load albums first)", self)
                no_albums_action.setEnabled(False)
                add_menu.addAction(no_albums_action)
            else:
                # Try to load and count the albums
                try:
                    with open(albums_json_path, 'r', encoding='utf-8') as f:
                        selected_albums = json.load(f)
                        album_count = len(selected_albums)
                    
                    # We have albums, populate the collections
                    if collections:
                        for collection in collections:
                            collection_name = collection.get('name', 'Unnamed Collection')
                            collection_id = collection.get('id')
                            
                            if collection_id:
                                add_action = QAction(f"Add {album_count} albums to: {collection_name}", self)
                                add_action.setProperty("collection_id", collection_id)
                                add_action.triggered.connect(lambda checked, cid=collection_id, cname=collection_name: 
                                                        self.add_selected_albums_to_collection(cid, cname))
                                add_menu.addAction(add_action)
                    else:
                        no_collections_action = QAction("No collections found", self)
                        no_collections_action.setEnabled(False)
                        add_menu.addAction(no_collections_action)
                except Exception as e:
                    error_action = QAction(f"Error reading albums: {str(e)}", self)
                    error_action.setEnabled(False)
                    add_menu.addAction(error_action)
            
            menu.addMenu(add_menu)
            
            # Add "Create New Collection" action
            create_action = QAction("Create New Collection...", self)
            create_action.triggered.connect(self.create_new_collection)
            menu.addAction(create_action)
            
            # Add separator and logout option
            menu.addSeparator()
            logout_action = QAction("Logout from MusicBrainz", self)
            logout_action.triggered.connect(self.logout_musicbrainz)
            menu.addAction(logout_action)
        
        # Show the menu at the button position
        if hasattr(self, 'get_releases_musicbrainz'):
            pos = self.get_releases_musicbrainz.mapToGlobal(QPoint(0, self.get_releases_musicbrainz.height()))
            menu.exec(pos)

    def create_new_collection(self):
        """
        Create a new MusicBrainz collection
        """
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_auth.is_authenticated():
            QMessageBox.warning(self, "Error", "Not authenticated with MusicBrainz")
            return
        
        # Prompt for collection name
        collection_name, ok = QInputDialog.getText(
            self,
            "Create Collection",
            "Enter name for new collection:",
            QLineEdit.EchoMode.Normal
        )
        
        if not ok or not collection_name.strip():
            return
        
        # Prompt for collection type
        collection_types = ["release", "artist", "label", "recording", "work"]
        collection_type, ok = QInputDialog.getItem(
            self,
            "Collection Type",
            "Select collection type:",
            collection_types,
            0,  # Default to "release"
            False  # Not editable
        )
        
        if not ok:
            return
        
        # Show progress dialog
        progress = QProgressDialog("Creating collection...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Creating Collection")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(20)
        
        try:
            # Call MusicBrainz API to create collection
            url = "https://musicbrainz.org/ws/2/collection"
            headers = {
                "User-Agent": "MuspyReleasesModule/1.0",
                "Content-Type": "application/json"
            }
            
            data = {
                "name": collection_name,
                "entity_type": collection_type,
                "editor": self.musicbrainz_username
            }
            
            progress.setValue(50)
            QApplication.processEvents()
            
            response = self.musicbrainz_auth.session.post(url, json=data, headers=headers)
            
            progress.setValue(80)
            
            if response.status_code in [200, 201]:
                # Success
                collection_id = None
                try:
                    result_data = response.json()
                    collection_id = result_data.get("id")
                except:
                    pass
                    
                progress.setValue(100)
                
                success_msg = f"Collection '{collection_name}' created successfully"
                if collection_id:
                    success_msg += f"\nCollection ID: {collection_id}"
                    
                QMessageBox.information(self, "Success", success_msg)
                
                # Update collections - just fetch them again
                self.fetch_all_musicbrainz_collections()
            else:
                error_msg = f"Error creating collection: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg += f"\n{error_data['error']}"
                except:
                    error_msg += f"\n{response.text}"
                    
                QMessageBox.warning(self, "Error", error_msg)
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error creating collection: {str(e)}")
        
        finally:
            progress.close()

    def authenticate_musicbrainz_silently(self):
        """
        Intenta autenticar con MusicBrainz usando las credenciales almacenadas
        sin mostrar diálogos de UI
        
        Returns:
            bool: True si se logró autenticar, False en caso contrario
        """
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_username or not self.musicbrainz_password:
            self.logger.debug("No auth manager or credentials available for silent auth")
            return False
        
        try:
            # Log authentication attempt for debugging
            self.logger.info(f"Attempting silent authentication for user: {self.musicbrainz_username}")
            
            # Explicitly configure the session with the credentials
            self.musicbrainz_auth.username = self.musicbrainz_username
            self.musicbrainz_auth.password = self.musicbrainz_password
            
            # Clear and rebuild the session to ensure fresh state
            self.musicbrainz_auth.session = requests.Session()
            self.musicbrainz_auth.session.headers.update({
                "User-Agent": "MuspyReleasesModule/1.0"
            })
            
            # Iniciar autenticación
            result = self.musicbrainz_auth.authenticate(silent=True)
            
            if result:
                self.logger.info("Silent authentication successful")
                return True
            else:
                self.logger.warning("Silent authentication failed")
                return False
        
        except Exception as e:
            self.logger.error(f"Error in silent authentication: {e}", exc_info=True)
            return False



    def authenticate_musicbrainz_dialog(self):
        """
        Authenticate with MusicBrainz by getting username/password from user
        
        Returns:
            bool: Whether authentication was successful
        """
        if not hasattr(self, 'musicbrainz_auth'):
            QMessageBox.warning(self, "Error", "MusicBrainz configuration not available")
            return False
        
        # If we already have a username, use it as default
        default_username = self.musicbrainz_username or ""
        
        # Output debug information to help diagnose the issue
        self.logger.debug(f"MusicBrainz auth attempt with username: {default_username}")
        self.logger.debug(f"Password exists: {bool(self.musicbrainz_password)}")
        
        # Prompt for username if not already set
        if not default_username:
            username, ok = QInputDialog.getText(
                self,
                "MusicBrainz Authentication",
                "Enter your MusicBrainz username:",
                QLineEdit.EchoMode.Normal,
                default_username
            )
            
            if not ok or not username:
                self.results_text.append("Authentication canceled.")
                return False
            
            self.musicbrainz_username = username
            self.musicbrainz_auth.username = username
        
        # Use existing password if available, otherwise prompt
        if not self.musicbrainz_password:
            password, ok = QInputDialog.getText(
                self,
                "MusicBrainz Authentication",
                f"Enter password for MusicBrainz user {self.musicbrainz_username}:",
                QLineEdit.EchoMode.Password
            )
            
            if not ok or not password:
                self.results_text.append("Authentication canceled.")
                return False
                
            self.musicbrainz_password = password
        
        # Update password in auth manager
        self.musicbrainz_auth.password = self.musicbrainz_password
        
        # Try to authenticate
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append("Authenticating with MusicBrainz...")
        QApplication.processEvents()
        
        # More detailed logging
        self.logger.debug("Attempting to authenticate with MusicBrainz...")
        
        if self.musicbrainz_auth.authenticate():
            self.results_text.append("Authentication successful!")
            self.musicbrainz_enabled = True
            
            # Show success message
            QMessageBox.information(self, "Success", "Successfully logged in to MusicBrainz")
            return True
        else:
            error_msg = "Authentication failed. Please check your username and password."
            self.results_text.append(error_msg)
            QMessageBox.warning(self, "Authentication Failed", error_msg)
            
            # Clear password on failure
            self.musicbrainz_password = None
            return False

    def logout_musicbrainz(self):
        """
        Log out from MusicBrainz by clearing session
        """
        if hasattr(self, 'musicbrainz_auth'):
            self.musicbrainz_auth.clear_session()
            self.results_text.clear()
            self.results_text.show()
            self.results_text.append("MusicBrainz authentication data cleared.")
            QMessageBox.information(self, "Authentication Cleared", "MusicBrainz authentication data has been cleared.")


  

    def fetch_all_musicbrainz_collections(self):
        """
        Fetch all MusicBrainz collections with enhanced debugging
        """
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_auth.is_authenticated():
            QMessageBox.warning(self, "Error", "Not authenticated with MusicBrainz")
            return
        
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append(f"Fetching collections for {self.musicbrainz_username}...")
        QApplication.processEvents()
        
        try:
            # Try to get collections using HTML parsing
            html_collections = self.musicbrainz_auth.get_user_collections()
            self.results_text.append(f"Found {len(html_collections)} collections via HTML parsing")
            
            # Try to get collections using API if the method exists
            api_collections = []
            if hasattr(self.musicbrainz_auth, 'get_collections_by_api'):
                api_collections = self.musicbrainz_auth.get_collections_by_api()
                self.results_text.append(f"Found {len(api_collections)} collections via API")
            else:
                self.results_text.append("API method not available - update MusicBrainzAuthManager class")
            
            # Combine both approaches, removing duplicates
            all_collections = []
            added_ids = set()
            
            for collection in html_collections + api_collections:
                coll_id = collection.get('id')
                if coll_id and coll_id not in added_ids:
                    all_collections.append(collection)
                    added_ids.add(coll_id)
            
            # Lookup each collection by ID directly
            direct_collections = []
            for coll_id in added_ids:
                try:
                    url = f"https://musicbrainz.org/collection/{coll_id}"
                    response = self.musicbrainz_auth.session.get(url)
                    
                    if response.status_code == 200:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(response.text, 'html.parser')
                        title = soup.title.text.strip() if soup.title else "Unknown Collection"
                        
                        # Extract name from title (usually in format "Collection "Name" - MusicBrainz")
                        import re
                        name_match = re.search(r'Collection "(.*?)"', title)
                        coll_name = name_match.group(1) if name_match else title
                        
                        direct_collections.append({
                            'id': coll_id,
                            'name': coll_name,
                            'count': 0  # Count unknown
                        })
                except Exception as e:
                    self.logger.error(f"Error looking up collection {coll_id}: {e}")
            
            # Check which collections we've found with various methods
            if direct_collections:
                self.results_text.append(f"Found {len(direct_collections)} collections via direct lookup:")
                for coll in direct_collections:
                    self.results_text.append(f"• {coll['name']} (ID: {coll['id']})")
            
            if all_collections:
                self.results_text.append(f"Found {len(all_collections)} unique collections in total:")
                for coll in all_collections:
                    self.results_text.append(f"• {coll['name']} (ID: {coll['id']})")
            else:
                self.results_text.append("No collections found with any method.")
                
            return all_collections
            
        except Exception as e:
            error_msg = f"Error fetching collections: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.results_text.append(error_msg)
            return []



    def _select_musicbrainz_collection(self):
        """
        Show dialog to select a MusicBrainz collection
        
        Returns:
            dict or None: Selected collection dict or None if canceled
        """
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Seleccionar Colección de MusicBrainz")
        dialog.setMinimumWidth(400)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Collection selection
        collections_combo = QComboBox()
        
        # Add collections to combo box
        if hasattr(self, '_mb_collections') and self._mb_collections:
            for collection in self._mb_collections:
                name = collection.get('name', 'Colección sin nombre')
                count = collection.get('entity_count', 0)
                collections_combo.addItem(f"{name} ({count} elementos)", collection)
        else:
            collections_combo.addItem("No hay colecciones disponibles")
            collections_combo.setEnabled(False)
        
        layout.addWidget(QLabel("Seleccione una colección:"))
        layout.addWidget(collections_combo)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get selected collection
            return collections_combo.currentData()
        else:
            return None




    def show_musicbrainz_collection(self, collection_id, collection_name):
        """
        Show the contents of a MusicBrainz collection in the table
        
        Args:
            collection_id (str): ID of the collection to display
            collection_name (str): Name of the collection for display
        """
        # Make sure we're showing the text page during loading
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Loading collection: {collection_name}...")
        self.results_text.append("Please wait while data is being retrieved...")
        QApplication.processEvents()
        
        # Verificar autenticación una sola vez en esta sesión
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_auth.is_authenticated():
            # Si no hay autenticación explícita previa, informar y salir
            self.results_text.append("Not authenticated with MusicBrainz. Please log in first.")
            QApplication.processEvents()
            
            # Ofrecer opción de iniciar sesión
            reply = QMessageBox.question(
                self, 
                "Authentication Required", 
                "You need to be logged in to MusicBrainz to view collections. Log in now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if not self.authenticate_musicbrainz_silently():
                    QMessageBox.warning(self, "Error", "Authentication failed. Please try again.")
                    return
            else:
                return
        
        # Create function to fetch collection data with progress bar
        def fetch_collection_data(update_progress):
            update_progress(0, 3, "Connecting to MusicBrainz...", indeterminate=True)
            
            try:
                # Mostrar progreso mientras trabajamos
                update_progress(1, 3, "Retrieving collection data...", indeterminate=True)
                
                # Usar nuestra función de paginación mejorada
                result = self.fetch_collection_data_with_pagination(
                    collection_id, 
                    page_size=100,  # ajusta según sea necesario
                    max_pages=50    # ajusta según sea necesario
                )
                
                if result.get("success"):
                    releases = result.get("releases", [])
                    update_progress(2, 3, f"Processing {len(releases)} releases...")
                    
                    # Más procesamiento si es necesario
                    update_progress(3, 3, "Data processed successfully")
                    
                    return {
                        "success": True,
                        "releases": releases
                    }
                else:
                    return result  # Devolver error
            
            except Exception as e:
                self.logger.error(f"Error fetching collection: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"Error fetching collection: {str(e)}"
                }
        
        # Execute with progress dialog
        result = self.show_progress_operation(
            fetch_collection_data,
            title=f"Loading Collection: {collection_name}",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            releases = result.get("releases", [])
            
            if not releases:
                # Keep showing text instead of empty table
                self.show_text_page()
                self.results_text.append(f"The collection '{collection_name}' is empty.")
                QMessageBox.information(self, "Empty Collection", f"The collection '{collection_name}' is empty.")
                return
            
            # Show all processing text before attempting to switch to table view
            self.show_text_page()
            self.results_text.append(f"Successfully retrieved {len(releases)} releases.")
            self.results_text.append("Preparing table display...")
            QApplication.processEvents()
            
            # Display releases in the table
            self.display_musicbrainz_collection_table(releases, collection_name)
        else:
            # Keep showing text for error case
            self.show_text_page()
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.results_text.append(f"Error: {error_msg}")
            QMessageBox.warning(self, "Error", f"Could not load collection: {error_msg}")



    def get_collection_contents(self, collection_id, entity_type="release"):
        """
        Get the contents of a MusicBrainz collection using the API with proper pagination
        
        Args:
            collection_id (str): ID of the collection
            entity_type (str): Type of entity in the collection (release, artist, etc.)
                
        Returns:
            list: List of entities in the collection
        """
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_auth.is_authenticated():
            self.logger.error("Not authenticated with MusicBrainz")
            return []
        
        try:
            # Use the MusicBrainz API to get collection contents
            url = f"https://musicbrainz.org/ws/2/{entity_type}"
            
            headers = {
                "User-Agent": "MuspyReleasesModule/1.0"
            }
            
            entities = []
            offset = 0
            page_size = 100  # MusicBrainz API default limit
            more_pages = True
            
            # Update text display
            if hasattr(self, 'results_text'):
                self.results_text.append(f"Fetching collection data (page size: {page_size})...")
                QApplication.processEvents()
            
            # Paginate through results
            while more_pages:
                params = {
                    "collection": collection_id,
                    "fmt": "json",
                    "limit": page_size,
                    "offset": offset,
                    "inc": "artist-credits"  # Add inc parameter to get artist data
                }
                
                # Update text display for pagination
                if hasattr(self, 'results_text'):
                    self.results_text.append(f"Fetching page at offset {offset}...")
                    QApplication.processEvents()
                
                response = self.musicbrainz_auth.session.get(url, params=params, headers=headers)
                
                if response.status_code != 200:
                    self.logger.error(f"Error getting collection contents: {response.status_code} - {response.text}")
                    break
                    
                data = response.json()
                
                # Different entity types have different response structures
                items = []
                total_count = 0
                
                if entity_type == "release":
                    items = data.get("releases", [])
                    total_count = data.get("release-count", 0)
                elif entity_type == "artist":
                    items = data.get("artists", [])
                    total_count = data.get("artist-count", 0)
                else:
                    # Default fallback
                    items = data.get(f"{entity_type}s", [])
                    total_count = data.get(f"{entity_type}-count", data.get("count", 0))
                
                # Update text display for progress
                if hasattr(self, 'results_text'):
                    self.results_text.append(f"Retrieved {len(items)} items (total expected: {total_count})")
                    QApplication.processEvents()
                
                self.logger.info(f"Got {len(items)} items at offset {offset} of {total_count} total")
                entities.extend(items)
                
                # Check if we need to fetch more pages
                offset += len(items)
                
                # If we got fewer items than requested, or we've reached the total, we're done
                if len(items) < page_size or offset >= total_count:
                    more_pages = False
                    self.logger.info(f"Finished pagination with {len(entities)} total items")
                
                # Safeguard against infinite loops
                if len(items) == 0:
                    break
            
            return entities
                
        except Exception as e:
            self.logger.error(f"Error getting collection contents: {e}", exc_info=True)
            return []





    def fetch_collection_data_with_pagination(self, collection_id, page_size=100, max_pages=50):
        """
        Fetch collection data with robust pagination support
        
        Args:
            collection_id (str): ID of the collection
            page_size (int): Number of items per page
            max_pages (int): Maximum number of pages to fetch
            
        Returns:
            dict: Result with success flag and releases data
        """
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_auth.is_authenticated():
            return {"success": False, "error": "Not authenticated with MusicBrainz"}
        
        try:
            self.results_text.append(f"Fetching collection data with pagination (page size: {page_size}, max pages: {max_pages})...")
            QApplication.processEvents()
            
            # API URL para colecciones
            base_url = f"https://musicbrainz.org/ws/2/release"
            headers = {"User-Agent": "MuspyReleasesModule/1.0"}
            
            all_releases = []
            offset = 0
            page = 1
            continue_pagination = True
            
            while continue_pagination and page <= max_pages:
                # Construir parámetros para esta página
                params = {
                    "collection": collection_id,
                    "limit": page_size,
                    "offset": offset,
                    "fmt": "json",
                    "inc": "artist-credits"  # Incluir datos de artistas
                }
                
                # Actualizar status
                self.results_text.append(f"Fetching page {page} (offset: {offset})...")
                QApplication.processEvents()
                
                # Hacer la petición
                response = self.musicbrainz_auth.session.get(base_url, params=params, headers=headers)
                
                if response.status_code != 200:
                    self.logger.error(f"API error on page {page}: {response.status_code} - {response.text}")
                    self.results_text.append(f"Error fetching page {page}: {response.status_code}")
                    break
                
                # Procesar los datos
                try:
                    data = response.json()
                    
                    # Extraer releases y metadata
                    releases = data.get("releases", [])
                    total_count = data.get("release-count", -1)
                    
                    # Actualizar status
                    self.results_text.append(f"Retrieved {len(releases)} releases on page {page} (total: {total_count if total_count >= 0 else 'unknown'})")
                    QApplication.processEvents()
                    
                    # Procesar cada release
                    page_releases = []
                    for release in releases:
                        # Extraer datos básicos con manejo seguro (prevenir KeyErrors)
                        processed_release = {
                            'mbid': release.get('id', ''),
                            'title': release.get('title', 'Unknown Title'),
                            'artist': "",
                            'artist_mbid': "",
                            'type': "",
                            'date': release.get('date', ''),
                            'status': release.get('status', ''),
                            'country': release.get('country', '')
                        }
                        
                        # Extraer tipo del grupo de release (si existe)
                        release_group = release.get('release-group', {})
                        if isinstance(release_group, dict):
                            processed_release['type'] = release_group.get('primary-type', '')
                        
                        # Procesar información de artistas
                        artist_credits = release.get('artist-credit', [])
                        
                        if artist_credits:
                            artist_names = []
                            artist_mbids = []
                            
                            for credit in artist_credits:
                                if isinstance(credit, dict):
                                    if 'artist' in credit and isinstance(credit['artist'], dict):
                                        artist_info = credit['artist']
                                        artist_names.append(artist_info.get('name', ''))
                                        if 'id' in artist_info:
                                            artist_mbids.append(artist_info['id'])
                                    elif 'name' in credit:
                                        artist_names.append(credit['name'])
                                elif isinstance(credit, str):
                                    artist_names.append(credit)
                            
                            processed_release['artist'] = " ".join(filter(None, artist_names))
                            if artist_mbids:
                                processed_release['artist_mbid'] = artist_mbids[0]
                        
                        page_releases.append(processed_release)
                    
                    # Añadir los releases de esta página al total
                    all_releases.extend(page_releases)
                    
                    # Verificar si hay más páginas
                    # 1. Si no obtuvimos resultados o menos de los solicitados
                    if len(releases) < page_size:
                        self.results_text.append(f"Fetched less than {page_size} items, pagination complete.")
                        continue_pagination = False
                    
                    # 2. Si sabemos el total y ya lo alcanzamos o superamos
                    elif total_count >= 0 and offset + len(releases) >= total_count:
                        self.results_text.append(f"Reached end of collection ({total_count} items).")
                        continue_pagination = False
                    
                    # 3. Si alcanzamos el número máximo de páginas
                    elif page >= max_pages:
                        self.results_text.append(f"Reached max pages limit ({max_pages}).")
                        continue_pagination = False
                    
                    # Preparar para la siguiente página
                    page += 1
                    offset += len(releases)
                
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON response on page {page}")
                    self.results_text.append(f"Error processing page {page}: invalid response format")
                    continue_pagination = False
                    
            # Resumen final
            self.results_text.append(f"Pagination complete: retrieved {len(all_releases)} releases from {page-1} pages")
            QApplication.processEvents()
            
            return {
                "success": True,
                "releases": all_releases
            }
            
        except Exception as e:
            self.logger.error(f"Error in pagination: {e}", exc_info=True)
            self.results_text.append(f"Error retrieving data: {str(e)}")
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }






    def display_musicbrainz_collection_table(self, releases, collection_name):
        """
        Display MusicBrainz collection releases in the tabla_musicbrainz_collection table
        
        Args:
            releases (list): List of processed release dictionaries
            collection_name (str): Name of the collection for display
        """
        # First make sure we have the text displayed while we work
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Collection: {collection_name}")
        self.results_text.append(f"Found {len(releases)} releases")
        self.results_text.append("Preparing display...")
        QApplication.processEvents()
        
        # Find the stacked widget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Could not find stackedWidget")
            # Continue with text display only
            self._show_releases_as_text(releases, collection_name)
            return
        
        # Find the MusicBrainz collection page
        mb_page_index = -1
        for i in range(stack_widget.count()):
            page = stack_widget.widget(i)
            if page.objectName() == "musicbrainz_collection_page":
                mb_page_index = i
                self.logger.info(f"Found musicbrainz_collection_page at index {i}")
                break
        
        if mb_page_index < 0:
            self.logger.error("Could not find musicbrainz_collection_page in stackedWidget")
            # Continue with text display only
            self._show_releases_as_text(releases, collection_name)
            return
        
        # Get the page widget
        mb_page = stack_widget.widget(mb_page_index)
        
        # Find the table within the page
        table = mb_page.findChild(QTableWidget, "tabla_musicbrainz_collection")
        if not table:
            self.logger.error("Could not find tabla_musicbrainz_collection in musicbrainz_collection_page")
            
            # Look for ANY table in the page
            tables = mb_page.findChildren(QTableWidget)
            self.logger.debug(f"Found {len(tables)} tables in the page:")
            for t in tables:
                self.logger.debug(f"  - Table: {t.objectName()}")
                
                # Use the first table found as a fallback
                if not table and isinstance(t, QTableWidget):
                    table = t
                    self.logger.warning(f"Using fallback table: {t.objectName()}")
            
            if not table:
                # No table found at all, continue with text display
                self._show_releases_as_text(releases, collection_name)
                return
        
        # Find the label for collection info
        collection_label = mb_page.findChild(QLabel, "label_musicbrainz_collection")
        if collection_label:
            collection_label.setText(f"Collection: {collection_name} ({len(releases)} releases)")
        
        # Setup the table
        try:
            # Ensure table has enough columns - ADDING ARTIST MBID COLUMN
            if table.columnCount() < 7:
                table.setColumnCount(7)
                table.setHorizontalHeaderLabels(["Artist", "Artist MBID", "Release Title", "Type", "Date", "Status", "Country"])
            
            # Set row count
            table.setRowCount(len(releases))
            table.setSortingEnabled(False)  # Disable sorting while updating
            
            # Fill the table
            for row, release in enumerate(releases):
                try:
                    # Artist - con manejo de errores
                    artist_text = release.get('artist', '')
                    if not artist_text or not isinstance(artist_text, str):
                        artist_text = "Unknown Artist"
                    artist_item = QTableWidgetItem(artist_text)
                    table.setItem(row, 0, artist_item)
                    
                    # Artist MBID - con manejo de errores
                    artist_mbid = release.get('artist_mbid', '')
                    if not isinstance(artist_mbid, str):
                        artist_mbid = ""
                    artist_mbid_item = QTableWidgetItem(artist_mbid)
                    table.setItem(row, 1, artist_mbid_item)
                    
                    # Title - con manejo de errores
                    title_text = release.get('title', '')
                    if not title_text or not isinstance(title_text, str):
                        title_text = "Untitled Release"
                    title_item = QTableWidgetItem(title_text)
                    table.setItem(row, 2, title_item)
                    
                    # Type - con manejo de errores
                    type_text = release.get('type', '')
                    if not isinstance(type_text, str):
                        type_text = ""
                    type_item = QTableWidgetItem(type_text.title())
                    table.setItem(row, 3, type_item)
                    
                    # Date - con manejo de errores
                    date_str = release.get('date', 'No date')
                    if not isinstance(date_text, str):
                        date_text = ""
                    date_item = DateTableWidgetItem(date_str) 
                    table.setItem(row, 4, date_item)
                    
                    # Status - con manejo de errores
                    status_text = release.get('status', '')
                    if not isinstance(status_text, str):
                        status_text = ""
                    status_item = QTableWidgetItem(status_text.title())
                    table.setItem(row, 5, status_item)
                    
                    # Country - con manejo de errores
                    country_text = release.get('country', '')
                    if not isinstance(country_text, str):
                        country_text = ""
                    country_item = QTableWidgetItem(country_text)
                    table.setItem(row, 6, country_item)
                    
                    # Store MBID for context menu actions
                    release_mbid = release.get('mbid', '')
                    if isinstance(release_mbid, str):
                        for col in range(7):
                            if table.item(row, col):
                                table.item(row, col).setData(Qt.ItemDataRole.UserRole, release_mbid)
                
                except Exception as e:
                    self.logger.error(f"Error adding row {row}: {e}", exc_info=True)
                    # Intentar continuar con la siguiente fila
                    continue
            
            # Re-enable sorting
            table.setSortingEnabled(True)
        
            # Resize columns to fit content
            table.resizeColumnsToContents()
            
            # Configure context menu for the table if not already configured
            if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
                table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                table.customContextMenuRequested.connect(self.show_musicbrainz_table_context_menu)
            
            # Switch to the MusicBrainz collection page
            stack_widget.setCurrentIndex(mb_page_index)
            self.logger.info(f"Successfully displayed {len(releases)} releases in the MusicBrainz collection table")
        
        except Exception as e:
            self.logger.error(f"Error displaying collection in table: {e}", exc_info=True)
            # Fall back to text display
            self._show_releases_as_text(releases, collection_name)


    def _show_releases_as_text(self, releases, collection_name, limit=100):
        """
        Muestra lanzamientos como texto en el visor de resultados
        
        Args:
            releases (list): Lista de diccionarios con información de lanzamientos
            collection_name (str): Nombre de la colección
            limit (int): Número máximo de lanzamientos a mostrar
        """
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Collection: {collection_name}")
        self.results_text.append(f"Found {len(releases)} releases")
        self.results_text.append("-" * 50)
        QApplication.processEvents()
        
        # Mostrar solo hasta el límite
        for i, release in enumerate(releases[:limit]):
            try:
                # Extraer datos con manejo seguro
                artist = release.get('artist', 'Unknown Artist')
                if not isinstance(artist, str):
                    artist = "Unknown Artist"
                    
                title = release.get('title', 'Untitled Release')
                if not isinstance(title, str):
                    title = "Untitled Release"
                    
                date = release.get('date', '')
                if not isinstance(date, str):
                    date = ""
                    
                artist_mbid = release.get('artist_mbid', '')
                if not isinstance(artist_mbid, str):
                    artist_mbid = ""
                    
                # Formatear línea
                line = f"{i+1}. {artist}"
                if artist_mbid:
                    line += f" (MBID: {artist_mbid})"
                line += f" - {title}"
                if date:
                    line += f" ({date})"
                    
                self.results_text.append(line)
            except Exception as e:
                self.logger.error(f"Error displaying release {i}: {e}")
                self.results_text.append(f"{i+1}. [Error displaying release]")
        
        # Si hay más releases que el límite
        if len(releases) > limit:
            self.results_text.append(f"... and {len(releases)-limit} more releases.")
        
        self.results_text.append("-" * 50)
        self.results_text.append("Switch to the table view for a better display experience (if available).")




    def add_release_to_collection(self, collection_id, collection_name, release_mbid):
        """
        Add a single release to a MusicBrainz collection
        
        Args:
            collection_id (str): ID of the collection
            collection_name (str): Name of the collection
            release_mbid (str): MusicBrainz ID of the release
        """
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_auth.is_authenticated():
            QMessageBox.warning(self, "Error", "Not authenticated with MusicBrainz")
            return
            
        try:
            # Call MusicBrainz API to add the release
            url = f"https://musicbrainz.org/ws/2/collection/{collection_id}/releases/{release_mbid}"
            headers = {
                "User-Agent": "MuspyReleasesModule/1.0"
            }
            
            response = self.musicbrainz_auth.session.put(url, headers=headers)
            
            if response.status_code in [200, 201]:
                QMessageBox.information(self, "Success", f"Successfully added release to collection '{collection_name}'")
            else:
                error_msg = f"Error adding release to collection: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg += f"\n{error_data['error']}"
                except:
                    error_msg += f"\n{response.text}"
                    
                QMessageBox.warning(self, "Error", error_msg)
                
        except Exception as e:
            self.logger.error(f"Error adding release to collection: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to add release to collection: {e}")


    def add_selected_albums_to_collection(self, collection_id, collection_name):
        """
        Add albums from albums_selected.json to a MusicBrainz collection with improved authentication
        
        Args:
            collection_id (str): ID of the collection to add albums to
            collection_name (str): Name of the collection for display
        """
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_auth.is_authenticated():
            # Attempt to authenticate first
            self.logger.info("Not authenticated with MusicBrainz, attempting authentication...")
            if not self.authenticate_musicbrainz_silently():
                QMessageBox.warning(self, "Error", "MusicBrainz authentication required to add albums to collections")
                return
        
        # Path to the JSON file
        json_path = os.path.join(PROJECT_ROOT, ".content", "cache", "albums_selected.json")
        
        # Check if file exists
        if not os.path.exists(json_path):
            QMessageBox.warning(self, "Error", "No selected albums file found. Please load albums first.")
            return
        
        # Load albums from JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                albums_data = json.load(f)
                
            if not albums_data:
                QMessageBox.warning(self, "Error", "No albums found in the selection file.")
                return
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading selected albums: {str(e)}")
            return
        
        # Function to add albums with progress dialog
        def add_albums_to_collection(update_progress):
            # Prepare list of MBIDs
            album_mbids = []
            valid_albums = []
            
            update_progress(0, 3, "Preparing album data...", indeterminate=True)
            
            # Extract MBIDs from albums data
            for album in albums_data:
                mbid = album.get('mbid')
                if mbid and len(mbid) == 36 and mbid.count('-') == 4:
                    album_mbids.append(mbid)
                    valid_albums.append(album)
            
            if not album_mbids:
                return {
                    "success": False,
                    "error": "No valid MusicBrainz IDs found in selected albums"
                }
            
            update_progress(1, 3, f"Adding {len(album_mbids)} albums to collection...", indeterminate=True)
            
            # Log authentication status for debugging
            self.logger.info(f"MusicBrainz auth status before adding albums: {self.musicbrainz_auth.is_authenticated()}")
            
            # Re-authenticate to ensure fresh session
            self.musicbrainz_auth.authenticate(silent=True)
            
            # Process in smaller batches to avoid overwhelming the API
            batch_size = 20  # MusicBrainz recommends smaller batches
            total_batches = (len(album_mbids) + batch_size - 1) // batch_size
            
            success_count = 0
            failed_batches = []
            
            for batch_idx in range(total_batches):
                batch_start = batch_idx * batch_size
                batch_end = min(batch_start + batch_size, len(album_mbids))
                current_batch = album_mbids[batch_start:batch_end]
                
                # Calculate progress as integer (0-100 range)
                progress_value = int(1 + (batch_idx / total_batches) * 100)
                update_progress(progress_value, 100, 
                            f"Processing batch {batch_idx+1}/{total_batches} ({batch_end}/{len(album_mbids)} albums)...", 
                            indeterminate=False)
                
                try:
                    # Join MBIDs with semicolons as per API spec
                    mbids_param = ";".join(current_batch)
                    
                    # Construct URL for this batch
                    url = f"https://musicbrainz.org/ws/2/collection/{collection_id}/releases/{mbids_param}"
                    
                    # Add necessary headers
                    headers = {
                        "User-Agent": "MuspyReleasesModule/1.0",
                        "Content-Type": "application/json"
                    }
                    
                    # Make the request with all cookies from the session
                    response = self.musicbrainz_auth.session.put(url, headers=headers)
                    
                    if response.status_code in [200, 201]:
                        success_count += len(current_batch)
                        self.logger.info(f"Successfully added batch {batch_idx+1} to collection")
                    else:
                        failed_batches.append(batch_idx + 1)
                        self.logger.error(f"Failed to add batch {batch_idx+1}: {response.status_code} - {response.text}")
                except Exception as e:
                    failed_batches.append(batch_idx + 1)
                    self.logger.error(f"Error processing batch {batch_idx+1}: {str(e)}")
            
            update_progress(3, 3, "Finalizing...", indeterminate=True)
            
            return {
                "success": success_count > 0,
                "total": len(album_mbids),
                "success_count": success_count,
                "failed_batches": failed_batches
            }
        
        # Execute with progress dialog
        result = self.show_progress_operation(
            add_albums_to_collection,
            title=f"Adding to Collection: {collection_name}",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            success_count = result.get("success_count", 0)
            total = result.get("total", 0)
            failed_batches = result.get("failed_batches", [])
            
            if failed_batches:
                message = (f"Added {success_count} of {total} albums to collection '{collection_name}'.\n\n"
                        f"Some batches failed: {', '.join(map(str, failed_batches))}.\n"
                        "This might be due to permission issues or some albums already being in the collection.")
                QMessageBox.warning(self, "Partial Success", message)
            else:
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Successfully added {success_count} albums to collection '{collection_name}'"
                )
            
            # Offer to show the collection
            reply = QMessageBox.question(
                self,
                "View Collection",
                f"Would you like to view the updated collection '{collection_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.show_musicbrainz_collection(collection_id, collection_name)
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            QMessageBox.warning(self, "Error", f"Could not add albums to collection: {error_msg}")

    


    def show_musicbrainz_table_context_menu(self, position):
        """
        Show context menu for items in the MusicBrainz collection table
        
        Args:
            position (QPoint): Position where the context menu was requested
        """
        table = self.sender()
        if not table:
            return
        
        item = table.itemAt(position)
        if not item:
            return
        
        # Get the release MBID from the item
        release_mbid = item.data(Qt.ItemDataRole.UserRole)
        
        # Get the full row data
        row = item.row()
        artist = table.item(row, 0).text() if table.item(row, 0) else "Unknown"
        artist_mbid = table.item(row, 1).text() if table.columnCount() > 1 and table.item(row, 1) else ""
        title = table.item(row, 2).text() if table.columnCount() > 2 and table.item(row, 2) else "Unknown"
        
        # Create the context menu
        menu = QMenu(self)
        
        # Add actions
        view_release_action = QAction(f"View '{title}' on MusicBrainz", self)
        view_release_action.triggered.connect(lambda: self.open_musicbrainz_release(release_mbid))
        menu.addAction(view_release_action)
        
        if artist_mbid:
            view_artist_action = QAction(f"View artist '{artist}' on MusicBrainz", self)
            view_artist_action.triggered.connect(lambda: self.open_musicbrainz_artist(artist_mbid))
            menu.addAction(view_artist_action)
        
        menu.addSeparator()
        
        if artist_mbid:
            follow_artist_mbid_action = QAction(f"Follow '{artist}' on Muspy (using MBID)", self)
            follow_artist_mbid_action.triggered.connect(lambda: self.add_artist_to_muspy(artist_mbid, artist))
            menu.addAction(follow_artist_mbid_action)
        
        follow_action = QAction(f"Follow '{artist}' on Muspy (search by name)", self)
        follow_action.triggered.connect(lambda: self.follow_artist_from_name(artist))
        menu.addAction(follow_action)
        
        # Show the menu
        menu.exec(table.mapToGlobal(position))



    def _start_background_auth(self):
        """Start MusicBrainz authentication in a background thread"""
        if not hasattr(self, 'musicbrainz_auth') or not self.musicbrainz_enabled:
            return
            
        # Create a QThread
        self.auth_thread = QThread()
        
        # Create the worker
        self.auth_worker = AuthWorker(
            self.musicbrainz_auth, 
            self.musicbrainz_username, 
            self.musicbrainz_password
        )
        
        # Move worker to thread
        self.auth_worker.moveToThread(self.auth_thread)
        
        # Connect signals
        self.auth_thread.started.connect(self.auth_worker.authenticate)
        self.auth_worker.finished.connect(self.auth_thread.quit)
        self.auth_worker.finished.connect(self.handle_background_auth_result)
        
        # Clean up connections
        self.auth_thread.finished.connect(self.auth_worker.deleteLater)
        self.auth_thread.finished.connect(self.auth_thread.deleteLater)
        
        # Start the thread
        self.auth_thread.start()

    def handle_background_auth_result(self, success):
        """Handle the result of background authentication"""
        if success:
            self.logger.info("Background MusicBrainz authentication successful")
            # Pre-fetch collections to make menu faster later
            if hasattr(self, 'musicbrainz_auth') and self.musicbrainz_auth.is_authenticated():
                try:
                    # Fetch collections in a non-blocking way (just store for later use)
                    if hasattr(self.musicbrainz_auth, 'get_collections_by_api'):
                        self._mb_collections = self.musicbrainz_auth.get_collections_by_api()
                    elif hasattr(self.musicbrainz_auth, 'get_user_collections'):
                        self._mb_collections = self.musicbrainz_auth.get_user_collections()
                except Exception as e:
                    self.logger.error(f"Error pre-fetching collections: {e}")
        else:
            self.logger.warning("Background MusicBrainz authentication failed")



    def open_musicbrainz_artist(self, artist_mbid):
        """Open MusicBrainz artist page in browser"""
        if not artist_mbid:
            return
            
        url = f"https://musicbrainz.org/artist/{artist_mbid}"
        
        import webbrowser
        webbrowser.open(url)

     
