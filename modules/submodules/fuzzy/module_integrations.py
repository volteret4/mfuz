# Modifica module_integrations.py

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QMessageBox, QApplication
import sqlite3
import os

class ModuleIntegrator:
    """Class to handle integration between music_fuzzy module and other application modules"""
    
    def __init__(self, parent):
        """
        Initialize the integrator with a reference to the parent module
        
        Args:
            parent: The parent module (music_fuzzy instance)
        """
        self.parent = parent
        self.setup_buttons()
    
    def setup_buttons(self):
        """Connect integration buttons to their handlers"""
        # Find and connect the conciertos_button
        conciertos_button = self.parent.findChild(QPushButton, "conciertos_button")
        if conciertos_button:
            try:
                conciertos_button.clicked.disconnect()  # Prevent duplicate connections
            except:
                pass
            conciertos_button.clicked.connect(self.handle_conciertos_button)
            print("Conciertos button connected")
        
        # Find and connect the url_playlists_button
        url_playlists_button = self.parent.findChild(QPushButton, "url_playlists_button")
        if url_playlists_button:
            try:
                url_playlists_button.clicked.disconnect()
            except:
                pass
            url_playlists_button.clicked.connect(self.handle_url_playlists_button)
            print("URL Playlists button connected")
        else:
            print("WARNING: URL Playlists button not found")
        
        # Find and connect the spotify_button
        spotify_button = self.parent.findChild(QPushButton, "spotify_button")
        if spotify_button:
            try:
                spotify_button.clicked.disconnect()
            except Exception as e:
                print(f"Disconnecting spotify_button: {e}")
                pass
            spotify_button.clicked.connect(self.handle_spotify_button)
            print("Spotify button connected")
        else:
            print("WARNING: Spotify button not found")
            # Try to find by searching all buttons
            for button in self.parent.findChildren(QPushButton):
                print(f"Found button: {button.objectName()}")
                if button.toolTip() == "Spotify" or "spotify" in button.objectName().lower():
                    try:
                        button.clicked.disconnect()
                    except:
                        pass
                    button.clicked.connect(self.handle_spotify_button)
                    print(f"Connected Spotify button via name/tooltip: {button.objectName()}")
        
        # Find and connect the muspy_button
        muspy_button = self.parent.findChild(QPushButton, "muspy_button")
        if muspy_button:
            try:
                muspy_button.clicked.disconnect()
            except:
                pass
            muspy_button.clicked.connect(self.handle_muspy_button)
            print("Muspy button connected")
        else:
            print("WARNING: Muspy button not found")
            # Try to find by alternative methods
            for button in self.parent.findChildren(QPushButton):
                if button.toolTip() == "Muspy" or "muspy" in button.objectName().lower():
                    try:
                        button.clicked.disconnect()
                    except:
                        pass
                    button.clicked.connect(self.handle_muspy_button)
                    print(f"Connected Muspy button via name/tooltip: {button.objectName()}")
    
    def handle_spotify_button(self):
        """
        Handle click on spotify_button - add selected songs with Spotify URLs to URL Playlist module
        """
        print("Spotify button clicked!")
        QApplication.processEvents()  # Procesar eventos pendientes
        
        # Get selected items with Spotify URLs
        selected_items = self._get_selected_items_with_spotify_urls()
        
        if not selected_items or not selected_items['songs']:
            QMessageBox.information(
                self.parent, 
                "Información", 
                "No hay canciones con URLs de Spotify seleccionadas para añadir"
            )
            return
        
        # Switch to URL Playlist module
        url_playlist_tab_name = self._find_url_playlist_tab_name()
        if not url_playlist_tab_name:
            QMessageBox.warning(
                self.parent, 
                "Advertencia", 
                "No se encontró el módulo de URL Playlist"
            )
            return
        
        # Get the tab_manager and switch to URL Playlist tab
        if hasattr(self.parent, 'tab_manager') and self.parent.tab_manager:
            # Add songs to URL Playlist
            success = self.parent.tab_manager.switch_to_tab(
                url_playlist_tab_name,
                'add_spotify_songs_to_queue',  # Method to call in URL Playlist module
                selected_items['songs']  # Pass songs as argument
            )
            
            if success:
                num_songs = len(selected_items['songs'])
                QMessageBox.information(
                    self.parent, 
                    "Éxito", 
                    f"Se han añadido {num_songs} canciones con URLs de Spotify a la playlist"
                )
            else:
                QMessageBox.warning(
                    self.parent, 
                    "Error", 
                    "No se pudieron añadir las canciones a la playlist"
                )
        else:
            print("Cannot access tab manager")
    
    def _get_selected_items_with_spotify_urls(self):
        """
        Get the currently selected items and collect all songs that have Spotify URLs
        from the database, including processing child items.
        
        Returns:
            dict: Dictionary with 'songs', 'albums', and 'artists' keys
        """
        result = {
            'songs': [],
            'albums': [],
            'artists': []
        }
        
        if not hasattr(self.parent, 'results_tree_widget'):
            print("results_tree_widget not found")
            return result
            
        # Make sure we have access to the database
        if not hasattr(self.parent, 'db_path') or not self.parent.db_path:
            print("Database path not available")
            return result
            
        db_path = self.parent.db_path
        if not os.path.exists(db_path):
            print(f"Database not found at: {db_path}")
            return result
        
        # Get selected items
        selected_items = self.parent.results_tree_widget.selectedItems()
        if not selected_items:
            print("No items selected")
            return result
        
        # Connect to database
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            print(f"Connected to database: {db_path}")
            
            processed_song_ids = set()  # Track already processed songs to avoid duplicates
            
            # Process each selected item
            for item in selected_items:
                self._process_item_for_spotify_urls(item, result, cursor, processed_song_ids)
            
            conn.close()
        except Exception as e:
            print(f"Database error: {e}")
            import traceback
            traceback.print_exc()
        
        # Log the results
        print(f"Found {len(result['songs'])} songs with Spotify URLs")
        print(f"Found {len(result['albums'])} albums with Spotify URLs")
        print(f"Found {len(result['artists'])} artists with Spotify URLs")
        
        return result

    def _process_item_for_spotify_urls(self, item, result, cursor, processed_song_ids):
        """Helper method to process an item and its children recursively for Spotify URLs"""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data or not isinstance(item_data, dict):
            return
                
        item_type = item_data.get('type')
        print(f"Processing item for Spotify URLs: type={item_type}")
        
        # Process the current item based on its type
        if item_type == 'song' or item_type == 'track':
            song_id = item_data.get('id')
            if song_id and song_id not in processed_song_ids:
                processed_song_ids.add(song_id)
                self._add_song_with_spotify_url(song_id, item_data, result, cursor)
        
        elif item_type == 'album':
            album_id = item_data.get('id')
            album_name = item_data.get('name', '')
            
            if album_id:
                # Add album if it has Spotify URL
                self._add_album_with_spotify_url(album_id, item_data, result, cursor)
                
                # Process child songs from the tree view
                for i in range(item.childCount()):
                    child_item = item.child(i)
                    self._process_item_for_spotify_urls(child_item, result, cursor, processed_song_ids)
                
                # Also lookup songs from database
                if album_name:
                    self._add_songs_by_album_name(album_name, result, cursor, processed_song_ids)
        
        elif item_type == 'artist':
            artist_id = item_data.get('id')
            artist_name = item_data.get('name', '')
            
            if artist_id:
                # Add artist if it has Spotify URL
                self._add_artist_with_spotify_url(artist_id, item_data, result, cursor)
                
                # Process all child albums and their songs from the tree view
                for i in range(item.childCount()):
                    album_item = item.child(i)
                    self._process_item_for_spotify_urls(album_item, result, cursor, processed_song_ids)
                
                # Also lookup songs from database
                if artist_name:
                    self._add_songs_by_artist_name(artist_name, result, cursor, processed_song_ids)

    def _add_song_with_spotify_url(self, song_id, item_data, result, cursor):
        """Add a song with Spotify URL to the result"""
        # Get Spotify URL from song_links table
        cursor.execute("""
            SELECT s.id, s.title, s.artist, s.album, sl.spotify_url, sl.spotify_id 
            FROM songs s
            LEFT JOIN song_links sl ON s.id = sl.song_id
            WHERE s.id = ? AND sl.spotify_url IS NOT NULL
        """, (song_id,))
        song_result = cursor.fetchone()
        
        if song_result:
            spotify_url = song_result['spotify_url']
            print(f"Found Spotify URL for song {song_id}: {spotify_url}")
            
            # Create a copy of song data with the Spotify URL
            song_data = dict(item_data)
            song_data['spotify_url'] = spotify_url
            song_data['url'] = spotify_url  # Standard field for compatibility
            song_data['source'] = 'spotify'
            song_data['title'] = song_result['title']
            song_data['artist'] = song_result['artist']
            song_data['album'] = song_result['album']
            
            result['songs'].append(song_data)

    def _add_album_with_spotify_url(self, album_id, item_data, result, cursor):
        """Add an album with Spotify URL to the result"""
        # Check if album has Spotify URL
        cursor.execute("""
            SELECT a.id, a.name, ar.name as artist_name, a.spotify_url, a.spotify_id
            FROM albums a
            JOIN artists ar ON a.artist_id = ar.id
            WHERE a.id = ? AND a.spotify_url IS NOT NULL
        """, (album_id,))
        album_result = cursor.fetchone()
        
        if album_result:
            spotify_url = album_result['spotify_url']
            print(f"Found Spotify URL for album {album_id}: {spotify_url}")
            
            # Add album data
            album_data = dict(item_data)
            album_data['spotify_url'] = spotify_url
            album_data['url'] = spotify_url
            album_data['source'] = 'spotify'
            album_data['name'] = album_result['name']
            album_data['artist'] = album_result['artist_name']
            
            result['albums'].append(album_data)

    def _add_songs_by_album_name(self, album_name, result, cursor, processed_song_ids):
        """Add all songs from an album that have Spotify URLs"""
        cursor.execute("""
            SELECT s.id, s.title, s.artist, s.album, sl.spotify_url, sl.spotify_id
            FROM songs s
            LEFT JOIN song_links sl ON s.id = sl.song_id
            WHERE s.album = ? AND sl.spotify_url IS NOT NULL
        """, (album_name,))
        
        songs = cursor.fetchall()
        for song in songs:
            if song['id'] not in processed_song_ids:
                processed_song_ids.add(song['id'])
                song_data = {
                    'id': song['id'],
                    'title': song['title'],
                    'artist': song['artist'],
                    'album': song['album'],
                    'spotify_url': song['spotify_url'],
                    'url': song['spotify_url'],
                    'source': 'spotify',
                    'type': 'track'
                }
                result['songs'].append(song_data)
                print(f"Added song with Spotify URL: {song['title']}")

    def _add_artist_with_spotify_url(self, artist_id, item_data, result, cursor):
        """Add an artist with Spotify URL to the result"""
        # Check if artist has Spotify URL in artists_networks
        cursor.execute("""
            SELECT a.id, a.name, an.spotify as spotify_url
            FROM artists a
            LEFT JOIN artists_networks an ON a.id = an.artist_id
            WHERE a.id = ? AND an.spotify IS NOT NULL
        """, (artist_id,))
        artist_result = cursor.fetchone()
        
        if not artist_result:
            # Try to find Spotify URL in artists table
            cursor.execute("""
                SELECT id, name, spotify_url
                FROM artists
                WHERE id = ? AND spotify_url IS NOT NULL
            """, (artist_id,))
            artist_result = cursor.fetchone()
        
        if artist_result:
            spotify_url = artist_result['spotify_url']
            print(f"Found Spotify URL for artist {artist_id}: {spotify_url}")
            
            # Add artist data
            artist_data = dict(item_data)
            artist_data['spotify_url'] = spotify_url
            artist_data['url'] = spotify_url
            artist_data['source'] = 'spotify'
            artist_data['name'] = artist_result['name']
            
            result['artists'].append(artist_data)

    def _add_songs_by_artist_name(self, artist_name, result, cursor, processed_song_ids):
        """Add all songs from an artist that have Spotify URLs"""
        # Get all album names for this artist
        cursor.execute("""
            SELECT DISTINCT album FROM songs WHERE artist = ?
        """, (artist_name,))
        album_names = [row['album'] for row in cursor.fetchall() if row['album']]
        
        for album_name in album_names:
            # Get all songs for this album and artist that have Spotify URLs
            cursor.execute("""
                SELECT s.id, s.title, s.artist, s.album, sl.spotify_url, sl.spotify_id
                FROM songs s
                LEFT JOIN song_links sl ON s.id = sl.song_id
                WHERE s.album = ? AND s.artist = ? AND sl.spotify_url IS NOT NULL
            """, (album_name, artist_name))
            
            songs = cursor.fetchall()
            for song in songs:
                if song['id'] not in processed_song_ids:
                    processed_song_ids.add(song['id'])
                    song_data = {
                        'id': song['id'],
                        'title': song['title'],
                        'artist': song['artist'],
                        'album': song['album'],
                        'spotify_url': song['spotify_url'],
                        'url': song['spotify_url'],
                        'source': 'spotify',
                        'type': 'track'
                    }
                    result['songs'].append(song_data)
                    print(f"Added song with Spotify URL: {song['title']}")
    
    def handle_conciertos_button(self):
        """Handle click on conciertos button - search for concerts for the selected artist"""
        # Get the selected artist from the tree widget
        artist_name = self._get_selected_artist()
        if not artist_name:
            print("No artist selected")
            return
            
        print(f"Searching concerts for artist: {artist_name}")
        
        # Use the tab_manager to switch to the conciertos module
        if hasattr(self.parent, 'tab_manager') and self.parent.tab_manager:
            # Switch to the conciertos tab and call the search method
            self.parent.tab_manager.switch_to_tab(
                'Conciertos', 
                'search_concerts_for_artist',  # Method name in the conciertos module
                artist_name,                  # First argument: artist name
                None                          # Second argument: country_code (use default)
            )
        else:
            print("Cannot access tab manager")
    
    def handle_url_playlists_button(self):
        """
        Handle click on url_playlists_button - add selected songs to the URL Playlist module
        """
        # Get selected items with songs
        result = self._get_selected_items_with_songs()
        
        if not result or not result.get('songs'):
            QMessageBox.information(
                self.parent, 
                "Información", 
                "No hay canciones con rutas locales seleccionadas."
            )
            return
        
        # Switch to URL Playlist module
        url_playlist_tab_name = self._find_url_playlist_tab_name()
        if not url_playlist_tab_name:
            QMessageBox.warning(
                self.parent, 
                "Advertencia", 
                "No se encontró el módulo de URL Playlist"
            )
            return
        
        # Get the tab_manager and switch to URL Playlist tab
        if hasattr(self.parent, 'tab_manager') and self.parent.tab_manager:
            # Add songs to URL Playlist
            success = self.parent.tab_manager.switch_to_tab(
                url_playlist_tab_name,
                'add_songs_to_queue',  # Method to call in URL Playlist module
                result['songs']  # Pass songs as argument
            )
            
            if success:
                num_songs = len(result['songs'])
                QMessageBox.information(
                    self.parent, 
                    "Éxito", 
                    f"Se han añadido {num_songs} canciones a la playlist"
                )
            else:
                QMessageBox.warning(
                    self.parent, 
                    "Error", 
                    "No se pudieron añadir las canciones a la playlist"
                )
        else:
            print("Cannot access tab manager")
    
    def _find_url_playlist_tab_name(self):
        """
        Find the exact name of the URL Playlist tab
        
        Returns:
            str: Tab name or None if not found
        """
        if not hasattr(self.parent, 'tab_manager') or not self.parent.tab_manager:
            return None
            
        # Try different possible names for the URL Playlist tab
        possible_names = ['URL Playlist', 'Url Playlists', 'URL Player']
        
        for name in possible_names:
            if name in self.parent.tab_manager.tabs:
                return name
                
        return None
    
    def _get_selected_items_with_songs(self):
        """
        Get the currently selected items and collect all songs with file_path
        
        Returns:
            dict: Dictionary with 'songs' key containing all songs to add
        """
        result = {
            'songs': [],
            'albums': [],
            'artists': []
        }
        
        if not hasattr(self.parent, 'results_tree_widget'):
            print("results_tree_widget not found")
            return result
                
        # Get selected items
        selected_items = self.parent.results_tree_widget.selectedItems()
        if not selected_items:
            print("No items selected")
            return result
        
        # Add debug logs
        print(f"Selected {len(selected_items)} items")
        
        # Track processed song IDs to avoid duplicates
        processed_song_ids = set()
        
        # Process each selected item
        for item in selected_items:
            self._process_item_for_local_songs(item, result, processed_song_ids)
        
        # Final count
        print(f"Total songs with file_path: {len(result['songs'])}")
        
        return result

    def _collect_songs_recursive(self, item, songs_list, processed_song_ids):
        """
        Recursively collect all songs with file_path from an item and its children
        
        Args:
            item: The QTreeWidgetItem to process
            songs_list: List to store songs
            processed_song_ids: Set of already processed song IDs
            
        Returns:
            bool: True if any songs were added, False otherwise
        """
        added_songs = False
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data or not isinstance(item_data, dict):
            return False
        
        item_type = item_data.get('type')
        
        # Debug output for this item
        print(f"Processing {item_type}: {item.text(0)}")
        
        # If it's a song, check if it has a file_path
        if item_type == 'song' or item_type == 'track':
            song_id = item_data.get('id')
            
            # Skip if already processed
            if song_id and song_id in processed_song_ids:
                return False
            
            # Check for file_path
            if 'file_path' in item_data and item_data['file_path']:
                songs_list.append(item_data)
                print(f"Added song: {item_data.get('title')} - {item_data.get('file_path')}")
                
                # Mark as processed
                if song_id:
                    processed_song_ids.add(song_id)
                    
                added_songs = True
            else:
                print(f"Song {item_data.get('title')} has no file_path")
        
        # For albums and artists, process all children
        elif item_type == 'album' or item_type == 'artist':
            # Process all children
            for i in range(item.childCount()):
                child_item = item.child(i)
                if self._collect_songs_recursive(child_item, songs_list, processed_song_ids):
                    added_songs = True
        
        return added_songs

    def _process_item_for_local_songs(self, item, result, processed_song_ids):
        """
        Process tree item recursively, collecting all songs with file_path
        
        Args:
            item: The QTreeWidgetItem to process
            result: Dictionary to store results
            processed_song_ids: Set of already processed song IDs to avoid duplicates
        """
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data or not isinstance(item_data, dict):
            return
        
        item_type = item_data.get('type')
        
        # Add the current item to the appropriate list
        if item_type == 'artist':
            print(f"Processing artist: {item_data.get('name', 'Unknown')}")
            
            # Buscar canciones directamente en la base de datos para el artista
            if hasattr(self.parent, 'db_manager') and self.parent.db_manager:
                artist_id = item_data.get('id')
                if artist_id:
                    # Obtener todos los álbumes del artista
                    albums = self.parent.db_manager.get_artist_albums(artist_id)
                    if albums:
                        print(f"Found {len(albums)} albums for artist ID {artist_id}")
                        for album in albums:
                            album_id = album.get('id')
                            if album_id:
                                # Obtener canciones del álbum
                                songs = self.parent.db_manager.get_album_songs(album_id)
                                if songs:
                                    print(f"Found {len(songs)} songs for album ID {album_id}")
                                    for song in songs:
                                        song_id = song.get('id')
                                        if song_id and song_id not in processed_song_ids:
                                            if 'file_path' in song and song['file_path']:
                                                result['songs'].append(song)
                                                processed_song_ids.add(song_id)
                                                print(f"Added song: {song.get('title')} - {song.get('file_path')}")
            
            # Process all child albums in the tree
            for i in range(item.childCount()):
                album_item = item.child(i)
                self._process_item_for_local_songs(album_item, result, processed_song_ids)
        
        elif item_type == 'album':
            print(f"Processing album: {item_data.get('title', item_data.get('name', 'Unknown'))}")
            
            # Buscar canciones directamente en la base de datos para el álbum
            if hasattr(self.parent, 'db_manager') and self.parent.db_manager:
                album_id = item_data.get('id')
                if album_id:
                    songs = self.parent.db_manager.get_album_songs(album_id)
                    if songs:
                        print(f"Found {len(songs)} songs for album ID {album_id}")
                        for song in songs:
                            song_id = song.get('id')
                            if song_id and song_id not in processed_song_ids:
                                if 'file_path' in song and song['file_path']:
                                    result['songs'].append(song)
                                    processed_song_ids.add(song_id)
                                    print(f"Added song: {song.get('title')} - {song.get('file_path')}")
            
            # Process all child songs in the tree
            for i in range(item.childCount()):
                song_item = item.child(i)
                self._process_item_for_local_songs(song_item, result, processed_song_ids)
        
        elif item_type == 'song' or item_type == 'track':
            song_id = item_data.get('id')
            
            # Check if we have already processed this song
            if song_id and song_id in processed_song_ids:
                return
            
            # Check if the song has a file_path
            if 'file_path' in item_data and item_data['file_path']:
                # Add song to results
                result['songs'].append(item_data)
                print(f"Added song with file_path: {item_data.get('title', 'Unknown')} - {item_data.get('file_path', '').split('/')[-1]}")
                
                # Mark as processed
                if song_id:
                    processed_song_ids.add(song_id)
            else:
                print(f"Song {item_data.get('title', 'Unknown')} has no file_path in item_data")
                
                # Intentar obtener el file_path desde la base de datos
                if hasattr(self.parent, 'db_manager') and self.parent.db_manager and song_id:
                    song_details = self.parent.db_manager.get_song_details(song_id)
                    if song_details and 'file_path' in song_details and song_details['file_path']:
                        # Usar los detalles completos de la canción
                        result['songs'].append(song_details)
                        processed_song_ids.add(song_id)
                        print(f"Added song from DB: {song_details.get('title')} - {song_details.get('file_path')}")
    
    def _add_child_songs(self, parent_item, songs_list):
        """
        Add all child songs from a parent item to the songs list
        
        Args:
            parent_item: The parent QTreeWidgetItem
            songs_list: List to add songs to
        """
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            child_data = child_item.data(0, Qt.ItemDataRole.UserRole)
            
            if child_data and isinstance(child_data, dict):
                item_type = child_data.get('type')
                
                if (item_type == 'song' or item_type == 'track') and 'file_path' in child_data and child_data['file_path']:
                    songs_list.append(child_data)
    
    def _get_selected_artist(self):
        """
        Get the artist name from the currently selected item in the tree
        
        Returns:
            str: Artist name or None if no valid selection
        """
        if not hasattr(self.parent, 'results_tree_widget'):
            return None
            
        # Get selected items
        selected_items = self.parent.results_tree_widget.selectedItems()
        if not selected_items:
            return None
            
        selected_item = selected_items[0]
        item_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data or not isinstance(item_data, dict):
            return None
            
        item_type = item_data.get('type')
        
        if item_type == 'artist':
            # If artist is selected, get artist name directly
            return selected_item.text(0)
        elif item_type == 'album':
            # If album is selected, get the parent artist
            parent_item = selected_item.parent()
            if parent_item:
                return parent_item.text(0)
        elif item_type == 'song':
            # If song is selected, get artist from parent's parent or from the item data
            album_item = selected_item.parent()
            if album_item:
                artist_item = album_item.parent()
                if artist_item:
                    return artist_item.text(0)
            
            # Fallback to song's artist if available in item_data
            if 'artist' in item_data:
                return item_data['artist']
                
        return None


# MUSPY

    def handle_muspy_button(self):
        """
        Maneja el clic en muspy_button - envía el artista seleccionado al módulo muspy_releases
        """
        print("Muspy button clicked!")
        QApplication.processEvents()  # Procesar eventos pendientes
        
        # Obtener el elemento seleccionado
        if not hasattr(self.parent, 'results_tree_widget'):
            print("results_tree_widget not found")
            return
            
        selected_items = self.parent.results_tree_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(
                self.parent, 
                "Información", 
                "No hay artista seleccionado para buscar"
            )
            return
            
        selected_item = selected_items[0]
        item_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            print("No se encontraron datos del elemento para el elemento seleccionado")
            return
            
        item_type = item_data.get('type')
        
        # Determinar el nombre del artista según el tipo de elemento
        artist_name = None
        if item_type == 'artist':
            # Corregido: Primero intentar obtener del item_data, luego del texto del ítem
            artist_name = item_data.get('name')
            if not artist_name and hasattr(selected_item, 'text'):
                artist_name = selected_item.text(0)
        elif item_type == 'album':
            # Puede ser del álbum o del padre artista
            if 'artist' in item_data:
                artist_name = item_data.get('artist')
            else:
                parent_item = selected_item.parent()
                if parent_item:
                    artist_name = parent_item.text(0)
        elif item_type == 'song':
            # Puede venir del elemento canción o de su jerarquía
            if 'artist' in item_data:
                artist_name = item_data.get('artist')
            else:
                # Buscar en la jerarquía: canción -> álbum -> artista
                album_item = selected_item.parent()
                if album_item:
                    artist_item = album_item.parent()
                    if artist_item:
                        artist_name = artist_item.text(0)
        
        # Si aún no encontramos el nombre del artista, intentamos otras alternativas
        if not artist_name:
            # Intentar obtener del texto del ítem seleccionado
            try:
                artist_name = selected_item.text(0)
            except:
                pass
            
            # Si todavía no tenemos nombre, intentar buscar por otras propiedades del item_data
            if not artist_name and isinstance(item_data, dict):
                # Buscar en cualquier campo que pueda contener el nombre del artista
                for field in ['artist', 'artist_name', 'nombre', 'nombre_artista']:
                    if field in item_data and item_data[field]:
                        artist_name = item_data[field]
                        break
        
        if not artist_name:
            QMessageBox.warning(
                self.parent, 
                "Error", 
                "No se pudo determinar el nombre del artista"
            )
            return
        
        print(f"Artista seleccionado: {artist_name}")
        
        # Buscar el módulo muspy_releases
        muspy_tab_name = None
        for tab_name in self.parent.tab_manager.tabs.keys():
            if "muspy" in tab_name.lower():
                muspy_tab_name = tab_name
                break
        
        if not muspy_tab_name:
            QMessageBox.warning(
                self.parent, 
                "Error", 
                "No se encontró el módulo Muspy Releases"
            )
            return
        
        # Cambiar a la pestaña muspy y establecer el texto del artista
        if hasattr(self.parent, 'tab_manager') and self.parent.tab_manager:
            # Cambiar a la pestaña
            success = self.parent.tab_manager.switch_to_tab(
                muspy_tab_name,
                None  # No llamamos a un método del módulo directamente
            )
            
            if success:
                # Acceder al módulo después de cambiar a la pestaña
                muspy_module = self.parent.tab_manager.tabs.get(muspy_tab_name)
                if muspy_module and hasattr(muspy_module, 'artist_input'):
                    muspy_module.artist_input.setText(artist_name)
                    # Opcionalmente, disparar la búsqueda
                    if hasattr(muspy_module, 'search_button') and muspy_module.search_button:
                        muspy_module.search_button.click()
                else:
                    QMessageBox.warning(
                        self.parent, 
                        "Error", 
                        "El módulo Muspy no tiene un campo de entrada de artista"
                    )
            else:
                QMessageBox.warning(
                    self.parent, 
                    "Error", 
                    "No se pudo cambiar al módulo Muspy"
                )