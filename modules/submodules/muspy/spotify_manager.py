# submodules/spotify/spotify_manager.py
import os
import json
import requests
import logging
from PyQt6.QtWidgets import (QMessageBox, QApplication, QProgressDialog, 
                            QMenu, QSpinBox, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                            QCheckBox, QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pathlib import Path

from base_module import PROJECT_ROOT
#from modules.submodules.muspy import cache_manager

class SpotifyManager:
    def __init__(self,
                 parent,
                 project_root,
                 spotify_client_id=None,
                 spotify_client_secret=None, 
                 spotify_redirect_uri=None, 
                 ui_callback=None, 
                 progress_utils=None,
                 display_manager=None,
                 cache_manager=None,
                 muspy_manager=None,
                 utils=None
  
                 ):
        self.parent = parent
        self.project_root = project_root
        self.spotify_client_id = spotify_client_id
        self.spotify_client_secret = spotify_client_secret
        self.spotify_redirect_uri = spotify_redirect_uri
        self.logger = logging.getLogger(__name__)
        #self.logger = self.parent.logger
        self.spotify_auth = None
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        self.ui_callback = ui_callback or UICallback(None)
        self.progress_utils = progress_utils
        self.display_manager = display_manager
        self.cache_manager = cache_manager
        self.utils = utils
        self.muspy_manager = muspy_manager

        # Initialize Spotify auth manager if credentials are available
        if self.spotify_enabled:
            try:
                from tools.spotify_login import SpotifyAuthManager
                self.spotify_auth = SpotifyAuthManager(
                    client_id=self.spotify_client_id,
                    client_secret=self.spotify_client_secret,
                    redirect_uri=self.spotify_redirect_uri,
                    parent_widget=parent,
                    project_root=self.project_root
                )
                self.logger.info(f"Spotify auth manager initialized")
            except Exception as e:
                self.logger.error(f"Error initializing Spotify auth manager: {e}", exc_info=True)
                self.spotify_enabled = False
                
    def ensure_spotify_auth(self):
        """
        Ensure Spotify authentication is available
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        if not self.spotify_enabled:
            return False
            
        if not hasattr(self, 'spotify_auth'):
            return False
            
        # Check if we have a valid client
        try:
            spotify_client = self.spotify_auth.get_client()
            if spotify_client:
                return True
        except:
            pass
            
        # Try to authenticate
        try:
            return self.spotify_auth.authenticate()
        except:
            return False
            
    def get_spotify_client(self):
        """Get an authenticated Spotify client on demand"""
        if hasattr(self, 'spotify_auth'):
            return self.spotify_auth.get_client()
        return None


    def show_spotify_menu(self):
        """
        Display a menu with Spotify options when get_releases_spotify_button is clicked
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify credentials not configured")
            return
        
        # Create menu
        menu = QMenu(self.parent)
        
        # Add menu actions
        show_artists_action = QAction("Mostrar artistas seguidos", self)
        show_releases_action = QAction("Nuevos álbumes de artistas seguidos", self)
        show_saved_tracks_action = QAction("Canciones Guardadas", self)
        show_top_items_action = QAction("Top Items", self)
        
        # Connect actions to their respective functions
        show_artists_action.triggered.connect(self.show_spotify_followed_artists)
        show_releases_action.triggered.connect(self.show_spotify_new_releases)
        show_saved_tracks_action.triggered.connect(self.show_spotify_saved_tracks)
        show_top_items_action.triggered.connect(self.show_spotify_top_items_dialog)
        
        # Add actions to menu
        menu.addAction(show_artists_action)
        menu.addAction(show_releases_action)
        menu.addAction(show_saved_tracks_action)
        menu.addAction(show_top_items_action)
        
        # Add separator and cache management option
        menu.addSeparator()
        clear_cache_action = QAction("Limpiar caché de Spotify", self)
        clear_cache_action.triggered.connect(self.clear_spotify_cache)
        menu.addAction(clear_cache_action)
        
        # Get the button position
        pos = self.get_releases_spotify_button.mapToGlobal(QPoint(0, self.get_releases_spotify_button.height()))
        
        # Show menu
        menu.exec(pos)



    def follow_artist_on_spotify(self, artist_name, spotify_client=None):
        """
        Follow an artist on Spotify
        
        Args:
            artist_name (str): Name of the artist to follow
            spotify_client (spotipy.Spotify, optional): An authenticated Spotify client
            
        Returns:
            int: 1 for success, 0 for already following, -1 for error
        """
        try:
            # If no client provided, get one from our auth manager
            if spotify_client is None:
                spotify_client = self.spotify_auth.get_client()
                if not spotify_client:
                    self.logger.error("Could not get authenticated Spotify client")
                    return -1
            
            # Search for the artist on Spotify
            results = spotify_client.search(q=f'artist:"{artist_name}"', type='artist', limit=1)
            
            # Check if we found a match
            if results and 'artists' in results and 'items' in results['artists'] and results['artists']['items']:
                artist = results['artists']['items'][0]
                artist_id = artist['id']
                
                # Check if already following
                is_following = spotify_client.current_user_following_artists([artist_id])
                if is_following and is_following[0]:
                    self.logger.info(f"Already following {artist_name} on Spotify")
                    return 0  # Already following
                
                # Follow the artist
                spotify_client.user_follow_artists([artist_id])
                self.logger.info(f"Successfully followed {artist_name} on Spotify")
                return 1  # Success
                
            else:
                self.logger.warning(f"Artist '{artist_name}' not found on Spotify")
                return -1  # Error/Not found
                
        except Exception as e:
            self.logger.error(f"Error following artist on Spotify: {e}")
            return -1  # Error





    def follow_artist_on_spotify_by_id(self, artist_id):
        """
        Follow an artist on Spotify using their Spotify ID
        
        Args:
            artist_id (str): Spotify ID of the artist
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify authentication required")
            return
            
        try:
            # Get Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                QMessageBox.warning(self.parent, "Error", "Failed to get Spotify client")
                return
                
            # Check if already following
            is_following = spotify_client.current_user_following_artists([artist_id])
            if is_following and is_following[0]:
                QMessageBox.information(self.parent, "Already Following", "You are already following this artist on Spotify")
                return
                
            # Follow the artist
            spotify_client.user_follow_artists([artist_id])
            QMessageBox.information(self.parent, "Success", "Successfully followed artist on Spotify")
            
        except Exception as e:
            self.logger.error(f"Error following artist on Spotify: {e}", exc_info=True)
            QMessageBox.warning(self.parent, "Error", f"Failed to follow artist on Spotify: {e}")


  
    def authenticate_spotify(self):
        """
        Authenticate with Spotify using OAuth
        """
        try:

            
            # Setup cache path
            cache_path = Path(PROJECT_ROOT, ".content", "cache", ".spotify_cache")
            # Set up the OAuth object
            sp_oauth = SpotifyOAuth(
                client_id=self.spotify_client_id,
                client_secret=self.spotify_client_secret,
                redirect_uri=self.spotify_redirect_uri,
                scope="user-follow-modify user-follow-read",
                cache_path=cache_path
            )
            
            # Get the authorization URL
            auth_url = sp_oauth.get_authorize_url()
            
            # Open the URL in the default browser
            import webbrowser
            webbrowser.open(auth_url)
            
            # Show a dialog to get the redirect URL
            from PyQt6.QtWidgets import QInputDialog
            redirect_url, ok = QInputDialog.getText(
                self, 
                "Spotify Authentication", 
                "Please login to Spotify in your browser and paste the URL you were redirected to:"
            )
            
            if not ok or not redirect_url:
                self.ui_callback.append("Authentication canceled")
                return False
            
            # Exchange the code for a token
            code = sp_oauth.parse_response_code(redirect_url)
            token_info = sp_oauth.get_access_token(code)
            
            # Create Spotify client
            spotify_client= spotipy.Spotify(auth=token_info['access_token'])
            
            # Test with a simple API call
            user_info = spotify_client.current_user()
            if user_info and 'id' in user_info:
                self.ui_callback.append(f"Successfully authenticated as {user_info['display_name']}")
                return True
            else:
                self.ui_callback.append("Authentication failed")
                return False
            
        except Exception as e:
            self.logger.error(f"Spotify authentication error: {e}")
            self.ui_callback.append(f"Error authenticating with Spotify: {e}")
            return False

    def show_spotify_followed_artists(self):
        """
        Show a list of artists the user follows on Spotify with caching
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify credentials not configured")
            return
        
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        
        # Try to get from cache first
        cache_key = "followed_artists"
        cached_data = self.cache_manager.spotify_cache_manager(cache_key, expiry_hours=24)
        if cached_data:
            self.ui_callback.append("Showing cached followed artists data...")
            self.display_manager.display_spotify_artists_in_stacked_widget(cached_data)
            return
        
        self.ui_callback.append("Retrieving artists you follow on Spotify...")
        QApplication.processEvents()
        
        # Get Spotify client
        spotify_client = self.spotify_auth.get_client()
        if not spotify_client:
            self.ui_callback.append("Failed to get Spotify client. Please check authentication.")
            return
        
        # Function to fetch artists with progress dialog
        def fetch_spotify_artists(update_progress, *args, **kwargs):
            try:
                # Usar el patrón: update_progress(current, total, message)
                if not update_progress(0, 100, "Connecting to Spotify API..."):
                    return {"success": False, "error": "Canceled"}
                
                all_artists = []
                offset = 0
                limit = 50
                total = 1
                
                while offset < total:
                    if total > 1:
                        progress_percent = min(95, int((offset / max(1, total)) * 95))
                        if not update_progress(progress_percent, 100, f"Fetching artists ({offset}/{total})..."):
                            return {"success": False, "error": "Canceled"}
                    else:
                        if not update_progress(10, 100, "Fetching artists..."):
                            return {"success": False, "error": "Canceled"}
                    
                    # Fetch current page of artists
                    results = spotify_client.current_user_followed_artists(limit=limit, after=None if offset == 0 else all_artists[-1]['id'])
                    
                    if 'artists' in results and 'items' in results['artists']:
                        # Get artists from this page
                        artists_page = results['artists']['items']
                        all_artists.extend(artists_page)
                        
                        # Update total count
                        total = results['artists']['total']
                        
                        # If we got fewer than requested, we're done
                        if len(artists_page) < limit:
                            break
                            
                        # Update offset
                        offset += len(artists_page)
                    else:
                        # No more results or error
                        break
                
                # Process artists data
                if not update_progress(95, 100, "Processing artist data..."):
                    return {"success": False, "error": "Canceled"}
                
                processed_artists = []
                for artist in all_artists:
                    processed_artists.append({
                        'name': artist.get('name', 'Unknown'),
                        'id': artist.get('id', ''),
                        'popularity': artist.get('popularity', 0),
                        'followers': artist.get('followers', {}).get('total', 0) if 'followers' in artist else 0,
                        'genres': ', '.join(artist.get('genres', [])),
                        'image_url': artist.get('images', [{}])[0].get('url', '') if artist.get('images') else ''
                    })
                
                # Cache the processed artists
                self.cache_manager.spotify_cache_manager(cache_key, processed_artists)
                
                update_progress(100, 100, "Complete!")
                
                if not update_progress(100, 100, "Complete!"):
                    return {"success": False, "error": "Canceled"}
                
                return {
                    "success": True,
                    "artists": processed_artists,
                    "total": len(processed_artists)
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching Spotify artists: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Execute with progress dialog
        result = self.parent.show_progress_operation(
            fetch_spotify_artists,
            title="Loading Spotify Artists",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            artists = result.get("artists", [])
            
            if not artists:
                self.ui_callback.append("You don't follow any artists on Spotify.")
                return
            
            # Display artists in the stack widget table
            self.display_manager.display_spotify_artists_in_stacked_widget(artists)
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", f"Could not load Spotify artists: {error_msg}")


    def show_spotify_new_releases(self):
        """
        Show new releases from artists the user follows on Spotify with caching
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify credentials not configured")
            return
        
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        
        # Try to get from cache first
        cache_key = "new_releases"
        cached_data = self.cache_manager.spotify_cache_manager(cache_key, expiry_hours=12)  # Shorter expiry for releases
        if cached_data:
            self.ui_callback.append("Showing cached new releases data...")
            self.display_manager.display_spotify_releases_in_stacked_widget(cached_data)
            return
        
        self.ui_callback.append("Retrieving new releases from artists you follow on Spotify...")
        QApplication.processEvents()
        
        # Get Spotify client
        spotify_client = self.spotify_auth.get_client()
        if not spotify_client:
            self.ui_callback.append("Failed to get Spotify client. Please check authentication.")
            return
        
        # Function to fetch new releases with progress dialog
        def fetch_spotify_releases(update_progress, *args, **kwargs):
            try:
                if not update_progress(0, 100, "Connecting to Spotify API..."):
                    return {"success": False, "error": "Canceled"}
                
                # First get all artists the user follows
                if not update_progress(10, 100, "Getting artists you follow..."):
                    return {"success": False, "error": "Canceled"}
                
                followed_artists = []
                offset = 0
                limit = 50
                total = 1
                
                # Paginate through all followed artists
                while offset < total:
                    results = spotify_client.current_user_followed_artists(limit=limit, after=None if offset == 0 else followed_artists[-1]['id'])
                    
                    if 'artists' in results and 'items' in results['artists']:
                        artists_page = results['artists']['items']
                        followed_artists.extend(artists_page)
                        total = results['artists']['total']
                        
                        if len(artists_page) < limit:
                            break
                            
                        offset += len(artists_page)
                    else:
                        break
                
                # We have all followed artists, now get their recent releases
                if not update_progress(30, 100, f"Found {len(followed_artists)} artists. Getting their recent releases..."):
                    return {"success": False, "error": "Canceled"}
                
                all_releases = []
                artist_count = len(followed_artists)
                
                # Only process a reasonable number of artists to avoid rate limits
                max_artists_to_process = min(artist_count, 50)
                artists_to_process = followed_artists[:max_artists_to_process]
                
                for i, artist in enumerate(artists_to_process):
                    artist_id = artist['id']
                    artist_name = artist['name']
                    
                    progress = 30 + int((i / max_artists_to_process) * 60)
                    if not update_progress(progress, 100, f"Getting releases for {artist_name} ({i+1}/{max_artists_to_process})..."):
                        return {"success": False, "error": "Canceled"}
                    
                    # Get albums for this artist
                    try:
                        # Get all album types: album, single, appears_on, compilation
                        for album_type in ['album', 'single']:
                            albums = spotify_client.artist_albums(artist_id, album_type=album_type, limit=10)
                            
                            if 'items' in albums:
                                # Filter for recent releases (last 3 months)
                                import datetime
                                three_months_ago = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
                                
                                for album in albums['items']:
                                    release_date = album.get('release_date', '0000-00-00')
                                    
                                    # Only include recent releases
                                    if release_date >= three_months_ago:
                                        # Add artist info to album
                                        album['artist_name'] = artist_name
                                        album['artist_id'] = artist_id
                                        all_releases.append(album)
                    except Exception as e:
                        self.logger.error(f"Error getting albums for {artist_name}: {e}")
                        continue
                
                # Process releases data
                if not update_progress(95, 100, "Processing release data..."):
                    return {"success": False, "error": "Canceled"}
                
                # Sort by release date (newest first)
                all_releases.sort(key=lambda x: x.get('release_date', '0000-00-00'), reverse=True)
                
                # Format for display
                processed_releases = []
                for release in all_releases:
                    processed_releases.append({
                        'artist': release.get('artist_name', 'Unknown'),
                        'artist_id': release.get('artist_id', ''),
                        'title': release.get('name', 'Unknown'),
                        'id': release.get('id', ''),
                        'type': release.get('album_type', '').title(),
                        'date': release.get('release_date', ''),
                        'total_tracks': release.get('total_tracks', 0),
                        'image_url': release.get('images', [{}])[0].get('url', '') if release.get('images') else ''
                    })
                
                # Cache the processed releases
                self.cache_manager.spotify_cache_manager(cache_key, processed_releases)
                
                if not update_progress(100, 100, "Complete!"):
                    return {"success": False, "error": "Canceled"}
                
                return {
                    "success": True,
                    "releases": processed_releases,
                    "total": len(processed_releases)
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching Spotify releases: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Execute with progress dialog
        result = self.parent.show_progress_operation(
            fetch_spotify_releases,
            title="Loading Spotify Releases",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            releases = result.get("releases", [])
            
            if not releases:
                self.ui_callback.append("No new releases found from artists you follow on Spotify.")
                return
            
            # Display releases in the stack widget table
            self.display_manager.display_spotify_releases_in_stacked_widget(releases)
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", f"Could not load Spotify releases: {error_msg}")



    def show_spotify_saved_tracks(self):
        """
        Show the user's saved tracks on Spotify with caching
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify credentials not configured")
            return
        
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        
        # Try to get from cache first
        cache_key = "saved_tracks"
        cached_data = self.cache_manager.spotify_cache_manager(cache_key, expiry_hours=6)  # Short expiry as saved tracks change frequently
        if cached_data:
            self.ui_callback.append("Showing cached saved tracks data...")
            self.display_manager.display_spotify_saved_tracks_in_stacked_widget(cached_data)
            return
        
        self.ui_callback.append("Retrieving your saved tracks from Spotify...")
        QApplication.processEvents()
        
        # Get Spotify client
        spotify_client = self.spotify_auth.get_client()
        if not spotify_client:
            self.ui_callback.append("Failed to get Spotify client. Please check authentication.")
            return
        
        # Function to fetch saved tracks with progress dialog
        def fetch_spotify_saved_tracks(update_progress, *args, **kwargs):
            try:
                if not update_progress(0, 100, "Connecting to Spotify API..."):
                    return {"success": False, "error": "Canceled"}
                
                all_tracks = []
                offset = 0
                limit = 50
                total = 1
                
                while offset < total:
                    if total > 1:
                        progress_percent = min(95, int((offset / max(1, total)) * 95))
                        if not update_progress(progress_percent, 100, f"Fetching tracks ({offset}/{total})..."):
                            return {"success": False, "error": "Canceled"}
                    else:
                        if not update_progress(10, 100, "Fetching tracks..."):
                            return {"success": False, "error": "Canceled"}
                    
                    # Fetch current page of tracks
                    results = spotify_client.current_user_saved_tracks(limit=limit, offset=offset)
                    
                    if 'items' in results:
                        # Get tracks from this page
                        tracks_page = results['items']
                        
                        # Process each track item
                        for item in tracks_page:
                            track = item.get('track', {})
                            added_at = item.get('added_at', '')
                            
                            # Get album info
                            album = track.get('album', {})
                            album_name = album.get('name', 'Unknown Album')
                            
                            # Get artists info (there might be multiple)
                            artists = track.get('artists', [])
                            artist_names = [artist.get('name', 'Unknown Artist') for artist in artists]
                            artist_name = ', '.join(artist_names)
                            
                            # Create processed track object
                            processed_track = {
                                'id': track.get('id', ''),
                                'name': track.get('name', 'Unknown Track'),
                                'artist': artist_name,
                                'album': album_name,
                                'duration_ms': track.get('duration_ms', 0),
                                'popularity': track.get('popularity', 0),
                                'added_at': added_at,
                                'uri': track.get('uri', ''),
                                'external_urls': track.get('external_urls', {})
                            }
                            
                            all_tracks.append(processed_track)
                        
                        # Update total count
                        total = results['total']
                        
                        # If we got fewer than requested, we're done
                        if len(tracks_page) < limit:
                            break
                            
                        # Update offset for next page
                        offset += len(tracks_page)
                    else:
                        # No more results or error
                        break
                
                if not update_progress(98, 100, "Processing track data..."):
                    return {"success": False, "error": "Canceled"}
                
                # Cache the processed tracks
                self.cache_manager.spotify_cache_manager(cache_key, all_tracks)
                
                if not update_progress(100, 100, "Complete!"):
                    return {"success": False, "error": "Canceled"}
                
                return {
                    "success": True,
                    "tracks": all_tracks,
                    "total": len(all_tracks)
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching Spotify saved tracks: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Execute with progress dialog
        result = self.parent.show_progress_operation(
            fetch_spotify_saved_tracks,
            title="Loading Spotify Saved Tracks",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            tracks = result.get("tracks", [])
            
            if not tracks:
                self.ui_callback.append("You don't have any saved tracks on Spotify.")
                return
            
            # Display tracks in the stack widget table
            self.display_manager.display_spotify_saved_tracks_in_stacked_widget(tracks)
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", f"Could not load Spotify saved tracks: {error_msg}")





    def show_spotify_top_items_dialog(self):
        """
        Show dialog to select parameters for fetching user's top items from Spotify
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify credentials not configured")
            return
        
        # Create dialog
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Spotify Top Items Options")
        dialog.setMinimumWidth(350)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("Item Type:")
        type_combo = QComboBox()
        type_combo.addItem("Artists", "artists")
        type_combo.addItem("Tracks", "tracks")
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_combo)
        layout.addLayout(type_layout)
        
        # Time range selection
        time_layout = QHBoxLayout()
        time_label = QLabel("Time Range:")
        time_combo = QComboBox()
        time_combo.addItem("Last 4 Weeks", "short_term")
        time_combo.addItem("Last 6 Months", "medium_term")
        time_combo.addItem("All Time", "long_term")
        time_layout.addWidget(time_label)
        time_layout.addWidget(time_combo)
        layout.addLayout(time_layout)
        
        # Limit selection
        limit_layout = QHBoxLayout()
        limit_label = QLabel("Number of Items:")
        limit_spin = QSpinBox()
        limit_spin.setRange(1, 50)
        limit_spin.setValue(20)
        limit_layout.addWidget(limit_label)
        limit_layout.addWidget(limit_spin)
        layout.addLayout(limit_layout)
        
        # Cache checkbox
        cache_check = QCheckBox("Use cached data if available")
        cache_check.setChecked(True)
        layout.addWidget(cache_check)
        
        # Create buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get values
            item_type = type_combo.currentData()
            time_range = time_combo.currentData()
            limit = limit_spin.value()
            use_cache = cache_check.isChecked()
            
            # Call function with selected parameters
            self.fetch_spotify_top_items(item_type, time_range, limit, use_cache)




  

    def fetch_spotify_top_items(self, item_type, time_range, limit, use_cache=True):
        """
        Fetch and display user's top items from Spotify
        
        Args:
            item_type (str): Type of items to fetch ('artists' or 'tracks')
            time_range (str): Time range ('short_term', 'medium_term', or 'long_term')
            limit (int): Number of items to fetch
            use_cache (bool): Whether to use cached data when available
        """
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        
        # Try to get from cache first
        cache_key = f"top_{item_type}_{time_range}_{limit}"
        if use_cache:
            cached_data = self.cache_manager.spotify_cache_manager(cache_key, expiry_hours=24)
            if cached_data:
                self.ui_callback.append(f"Showing cached top {item_type} data...")
                self.display_manager.display_spotify_top_items_in_stacked_widget(cached_data, item_type)
                return
        
        self.ui_callback.append(f"Retrieving your top {item_type} from Spotify...")
        QApplication.processEvents()
        
        # Get Spotify client
        spotify_client = self.spotify_auth.get_client()
        if not spotify_client:
            self.ui_callback.append("Failed to get Spotify client. Please check authentication.")
            return
        
        # Function to fetch top items with progress dialog
        def fetch_top_items(update_progress, *args, **kwargs):
            try:
                if not update_progress(0, 100, "Connecting to Spotify API..."):
                    return {"success": False, "error": "Canceled"}
                
                if not update_progress(30, 100, f"Fetching top {item_type}..."):
                    return {"success": False, "error": "Canceled"}
                
                if item_type == "artists":
                    results = spotify_client.current_user_top_artists(
                        limit=limit,
                        offset=0,
                        time_range=time_range
                    )
                    items = results.get("items", [])
                    
                    # Process artists
                    if not update_progress(70, 100, f"Processing {item_type} data..."):
                        return {"success": False, "error": "Canceled"}
                    processed_items = []
                    
                    for artist in items:
                        processed_items.append({
                            'id': artist.get('id', ''),
                            'name': artist.get('name', 'Unknown'),
                            'popularity': artist.get('popularity', 0),
                            'followers': artist.get('followers', {}).get('total', 0) if 'followers' in artist else 0,
                            'genres': ', '.join(artist.get('genres', [])),
                            'image_url': artist.get('images', [{}])[0].get('url', '') if artist.get('images') else '',
                            'type': 'artist'
                        })
                
                elif item_type == "tracks":
                    results = spotify_client.current_user_top_tracks(
                        limit=limit,
                        offset=0,
                        time_range=time_range
                    )
                    items = results.get("items", [])
                    
                    # Process tracks
                    update_progress(70, "Processing track data...")
                    processed_items = []
                    
                    for track in items:
                        # Get album info
                        album = track.get('album', {})
                        album_name = album.get('name', 'Unknown Album')
                        
                        # Get artists info
                        artists = track.get('artists', [])
                        artist_names = [artist.get('name', 'Unknown Artist') for artist in artists]
                        artist_name = ', '.join(artist_names)
                        
                        processed_items.append({
                            'id': track.get('id', ''),
                            'name': track.get('name', 'Unknown'),
                            'artist': artist_name,
                            'album': album_name,
                            'duration_ms': track.get('duration_ms', 0),
                            'popularity': track.get('popularity', 0),
                            'uri': track.get('uri', ''),
                            'type': 'track'
                        })
                
                # Cache the processed items
                self.cache_manager.spotify_cache_manager(cache_key, processed_items)
                
                if not update_progress(100, 100, "Complete!"):
                    return {"success": False, "error": "Canceled"}
                
                return {
                    "success": True,
                    "items": processed_items,
                    "type": item_type,
                    "total": len(processed_items)
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching Spotify top {item_type}: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Execute with progress dialog
        result = self.parent.show_progress_operation(
            fetch_top_items,
            title=f"Loading Spotify Top {item_type.title()}",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            items = result.get("items", [])
            
            if not items:
                self.ui_callback.append(f"No top {item_type} found for your Spotify account.")
                return
            
            # Display items in the stack widget table
            self.display_manager.display_spotify_top_items_in_stacked_widget(items, item_type)
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", f"Could not load Spotify top {item_type}: {error_msg}")



    def follow_artist_on_spotify_by_name(self, artist_name):
        """
        Search for an artist on Spotify by name and follow them
        
        Args:
            artist_name (str): Name of the artist
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify authentication required")
            return
            
        try:
            # Get Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                QMessageBox.warning(self.parent, "Error", "Failed to get Spotify client")
                return
                
            # Search for the artist
            results = spotify_client.search(q=f'artist:"{artist_name}"', type='artist', limit=1)
            
            if not results or not results.get('artists') or not results['artists'].get('items'):
                QMessageBox.warning(self.parent, "Not Found", f"Could not find artist '{artist_name}' on Spotify")
                return
                
            # Get the artist ID
            artist = results['artists']['items'][0]
            artist_id = artist['id']
            
            # Check if already following
            is_following = spotify_client.current_user_following_artists([artist_id])
            if is_following and is_following[0]:
                QMessageBox.information(self.parent, "Already Following", f"You are already following {artist['name']} on Spotify")
                return
                
            # Follow the artist
            spotify_client.user_follow_artists([artist_id])
            QMessageBox.information(self.parent, "Success", f"Successfully followed {artist['name']} on Spotify")
            
        except Exception as e:
            self.logger.error(f"Error following artist on Spotify: {e}", exc_info=True)
            QMessageBox.warning(self.parent, "Error", f"Failed to follow artist on Spotify: {e}")





    def search_and_open_spotify_artist(self, artist_name):
        """
        Search for an artist on Spotify by name and open their page
        
        Args:
            artist_name (str): Name of the artist
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify authentication required")
            return
            
        try:
            # Get Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                QMessageBox.warning(self.parent, "Error", "Failed to get Spotify client")
                return
                
            # Search for the artist
            results = spotify_client.search(q=f'artist:"{artist_name}"', type='artist', limit=1)
            
            if not results or not results.get('artists') or not results['artists'].get('items'):
                QMessageBox.warning(self.parent, "Not Found", f"Could not find artist '{artist_name}' on Spotify")
                return
                
            # Get the artist ID
            artist = results['artists']['items'][0]
            artist_id = artist['id']
            
            # Open the artist page
            self.utils.open_spotify_artist(artist_id)
            
        except Exception as e:
            self.logger.error(f"Error searching artist on Spotify: {e}", exc_info=True)
            QMessageBox.warning(self.parent, "Error", f"Failed to search for artist on Spotify: {e}")





  

    def remove_track_from_spotify_saved(self, track_id, track_name):
        """
        Remove a track from Spotify saved tracks
        
        Args:
            track_id (str): Spotify ID of the track
            track_name (str): Name of the track for display
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify authentication required")
            return
        
        # Confirm with the user
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove '{track_name}' from your saved tracks?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Get Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                QMessageBox.warning(self.parent, "Error", "Failed to get Spotify client")
                return
            
            # Remove the track
            spotify_client.current_user_saved_tracks_delete([track_id])
            
            # Show success message
            QMessageBox.information(self.parent, "Success", f"Removed '{track_name}' from your saved tracks")
            
            # Ask if user wants to refresh the list
            refresh_reply = QMessageBox.question(
                self.parent,
                "Refresh List",
                "Do you want to refresh your saved tracks list?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if refresh_reply == QMessageBox.StandardButton.Yes:
                # Refresh the saved tracks display
                self.show_spotify_saved_tracks()
            
        except Exception as e:
            self.logger.error(f"Error removing track from saved tracks: {e}", exc_info=True)
            QMessageBox.warning(self.parent, "Error", f"Failed to remove track: {e}")



    def sync_spotify_selected_artists(self):
        """
        Synchronize selected artists from the JSON file with Spotify
        """
        # Check if Spotify is enabled
        if not self.spotify_enabled:
            QMessageBox.warning(self.parent, "Error", "Spotify credentials not configured")
            return
        
        # Path to the JSON file
        json_path = Path(PROJECT_ROOT, ".content", "cache", "artists_selected.json")
        
        # Check if file exists
        if not os.path.exists(json_path):
            QMessageBox.warning(self.parent, "Error", "No selected artists file found. Please load artists first.")
            return
        
        # Load artists from JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
                
            if not artists_data:
                QMessageBox.warning(self.parent, "Error", "No artists found in the selection file.")
                return
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", f"Error loading selected artists: {str(e)}")
            return
        
        # Get Spotify client
        try:
            # Initialize SpotifyAuthManager if needed
            if not hasattr(self, 'spotify_auth'):
                from tools.spotify_login import SpotifyAuthManager
                self.spotify_auth = SpotifyAuthManager(
                    client_id=self.spotify_client_id,
                    client_secret=self.spotify_client_secret,
                    redirect_uri=self.spotify_redirect_uri,
                    parent_widget=self,
                    project_root=PROJECT_ROOT
                )
            
            # Get authenticated client
            spotify_client = self.spotify_auth.get_client()
            
            if not spotify_client:
                QMessageBox.warning(self.parent, "Error", "Could not authenticate with Spotify. Please check your credentials.")
                return
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", f"Error initializing Spotify: {str(e)}")
            return
        
        # Create progress dialog
        progress = QProgressDialog("Syncing artists with Spotify...", "Cancel", 0, len(artists_data), self.parent)
        progress.setWindowTitle("Spotify Synchronization")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        # Counters for results
        successful_follows = 0
        already_following = 0
        failed_follows = 0
        artists_not_found = 0
        
        # Process each artist
        for i, artist_data in enumerate(artists_data):
            # Check if user canceled
            if progress.wasCanceled():
                break
            
            # Get artist name
            artist_name = artist_data.get("nombre", "")
            if not artist_name:
                failed_follows += 1
                continue
            
            # Update progress
            progress.setValue(i)
            progress.setLabelText(f"Processing {artist_name} ({i+1}/{len(artists_data)})")
            QApplication.processEvents()
            
            # Search for artist on Spotify
            try:
                results = spotify_client.search(q=f'artist:"{artist_name}"', type='artist', limit=1)
                
                if results and 'artists' in results and 'items' in results['artists'] and results['artists']['items']:
                    artist = results['artists']['items'][0]
                    artist_id = artist['id']
                    
                    # Check if already following
                    is_following = spotify_client.current_user_following_artists([artist_id])
                    if is_following and is_following[0]:
                        already_following += 1
                    else:
                        # Follow the artist
                        spotify_client.user_follow_artists([artist_id])
                        successful_follows += 1
                else:
                    artists_not_found += 1
            except Exception as e:
                self.logger.error(f"Error following {artist_name} on Spotify: {e}")
                failed_follows += 1
        
        # Complete the progress
        progress.setValue(len(artists_data))
        
        # Show summary
        summary_msg = f"Spotify synchronization completed:\n\n" \
                    f"Successfully followed: {successful_follows}\n" \
                    f"Already following: {already_following}\n" \
                    f"Not found on Spotify: {artists_not_found}\n" \
                    f"Failed: {failed_follows}"
                    
        QMessageBox.information(self.parent, "Spotify Synchronization Complete", summary_msg)



    def _display_spotify_artist_albums_as_text(self, albums, artist_name):
        """
        Display albums for a specific Spotify artist as text in the results area
        
        Args:
            albums (list): List of album dictionaries
            artist_name (str): Name of the artist
        """
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Found {len(albums)} albums for {artist_name}")
        self.ui_callback.append("-" * 50)
        
        # Group by type
        albums_by_type = {}
        for album in albums:
            album_type = album.get('type', 'Unknown').title()
            if album_type not in albums_by_type:
                albums_by_type[album_type] = []
            albums_by_type[album_type].append(album)
        
        # Display by type
        for album_type, type_albums in albums_by_type.items():
            self.ui_callback.append(f"\n{album_type}s ({len(type_albums)}):")
            self.ui_callback.append("-" * 30)
            
            # Sort by date (newest first)
            sorted_albums = sorted(type_albums, key=lambda x: x.get('date', '0000-00-00'), reverse=True)
            
            for i, album in enumerate(sorted_albums):
                title = album.get('title', 'Unknown')
                date = album.get('date', '')
                tracks = album.get('total_tracks', 0)
                
                self.ui_callback.append(f"{i+1}. {title}")
                if date:
                    self.ui_callback.append(f"   Released: {date}")
                self.ui_callback.append(f"   Tracks: {tracks}")
                self.ui_callback.append("")
        
        self.ui_callback.append("-" * 50)





    def get_spotify_artist_albums(self, artist_id, artist_name):
        """
        Get and display all albums for a Spotify artist
        
        Args:
            artist_id (str): Spotify ID of the artist
            artist_name (str): Name of the artist
        """
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Retrieving albums for {artist_name}...")
        QApplication.processEvents()
        
        # Get Spotify client
        spotify_client = self.spotify_auth.get_client()
        if not spotify_client:
            self.ui_callback.append("Failed to get Spotify client. Please check authentication.")
            return
        
        # Function to fetch albums with progress dialog
        def fetch_artist_albums(update_progress, *args, **kwargs):
            try:
                if not update_progress(0, 100, "Connecting to Spotify API..."):
                    return {"success": False, "error": "Canceled"}
                
                all_albums = []
                album_types = ['album', 'single', 'compilation']
                
                for i, album_type in enumerate(album_types):
                    progress = i * 30
                    if not update_progress(progress, 100, f"Fetching {album_type}s..."):
                        return {"success": False, "error": "Canceled"}
                    
                    offset = 0
                    limit = 50
                    total = 1
                    
                    # Paginate through all albums of this type
                    while offset < total:
                        # Fetch current page of albums
                        results = spotify_client.artist_albums(
                            artist_id, 
                            album_type=album_type,
                            limit=limit,
                            offset=offset
                        )
                        
                        if 'items' in results:
                            albums_page = results['items']
                            
                            # Add albums to our list
                            for album in albums_page:
                                album['fetch_type'] = album_type
                                all_albums.append(album)
                            
                            total = results['total']
                            
                            if len(albums_page) < limit:
                                break
                                
                            offset += len(albums_page)
                        else:
                            break
                
                # Process albums data
                if not update_progress(95, 100, "Processing album data..."):
                    return {"success": False, "error": "Canceled"}
                
                # Remove duplicates and process
                unique_albums = {}
                for album in all_albums:
                    album_id = album.get('id')
                    if album_id and album_id not in unique_albums:
                        unique_albums[album_id] = album
                
                processed_albums = list(unique_albums.values())
                processed_albums.sort(key=lambda x: x.get('release_date', '0000-00-00'), reverse=True)
                
                # Format for display
                display_albums = []
                for album in processed_albums:
                    display_albums.append({
                        'artist': artist_name,
                        'artist_id': artist_id,
                        'title': album.get('name', 'Unknown'),
                        'id': album.get('id', ''),
                        'type': album.get('album_type', '').title(),
                        'fetch_type': album.get('fetch_type', ''),
                        'date': album.get('release_date', ''),
                        'total_tracks': album.get('total_tracks', 0),
                        'image_url': album.get('images', [{}])[0].get('url', '') if album.get('images') else ''
                    })
                
                if not update_progress(100, 100, "Complete!"):
                    return {"success": False, "error": "Canceled"}
                
                return {
                    "success": True,
                    "albums": display_albums,
                    "total": len(display_albums)
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching artist albums: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Execute with progress dialog
        result = self.parent.show_progress_operation(
            fetch_artist_albums,
            title=f"Loading Albums for {artist_name}",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            albums = result.get("albums", [])
            
            if not albums:
                self.ui_callback.append(f"No albums found for {artist_name}.")
                return
            
            # Display albums in the stack widget table
            self.display_manager.display_spotify_artist_albums_in_stacked_widget(albums, artist_name)
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", f"Could not load albums: {error_msg}")

   
    def follow_spotify_artist_on_muspy(self, artist_id, artist_name):
        """
        Follow a Spotify artist on Muspy by first finding their MBID
        
        Args:
            artist_id (str): Spotify ID of the artist
            artist_name (str): Name of the artist
        """
        # First get the MBID by searching for the artist name
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Searching for MusicBrainz ID for {artist_name}...")
        QApplication.processEvents()
        
        mbid = self.get_mbid_artist_searched(artist_name)
        
        if mbid:
            # Store current artist
            self.current_artist = {"name": artist_name, "mbid": mbid}
            
            # Follow the artist
            success = self.add_artist_to_muspy(mbid, artist_name)
            
            if success:
                self.ui_callback.append(f"Successfully added {artist_name} to Muspy")
                QMessageBox.information(self.parent, "Success", f"Now following {artist_name} on Muspy")
            else:
                self.ui_callback.append(f"Failed to add {artist_name} to Muspy")
                QMessageBox.warning(self.parent, "Error", f"Could not follow {artist_name} on Muspy")
        else:
            self.ui_callback.append(f"Could not find MusicBrainz ID for {artist_name}")
            QMessageBox.warning(self.parent, "Error", f"Could not find MusicBrainz ID for {artist_name}")



 







    def show_spotify_artist_context_menu(self, position):
        """
        Show context menu for Spotify artists in the table
        
        Args:
            position (QPoint): Position where the context menu was requested
        """
        table = self.parent.sender()
        if not table:
            return
        
        item = table.itemAt(position)
        if not item:
            return
        
        # Get the artist data from the item
        item_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(item_data, dict):
            return
        
        # Extract the ID and name directly (don't pass the whole dictionary)
        artist_id = item_data.get('spotify_artist_id', '')
        artist_name = item_data.get('artist_name', '')
        
        if not artist_id or not artist_name:
            return
        
        # Create the context menu
        menu = QMenu(self.parent)
        
        # Add actions
        view_spotify_action = QAction(f"View '{artist_name}' on Spotify", self.parent)
        # Corregido - Pasamos solo el ID, no el diccionario completo
        view_spotify_action.triggered.connect(lambda: self.utils.open_spotify_artist(artist_id))
        menu.addAction(view_spotify_action)
        
        # Igual para el resto de acciones que usan el ID del artista
        follow_spotify_action = QAction(f"Follow '{artist_name}' on Spotify", self.parent)
        follow_spotify_action.triggered.connect(lambda: self.follow_artist_on_spotify_by_id(artist_id))
        menu.addAction(follow_spotify_action)
        
        add_to_muspy_action = QAction(f"Follow '{artist_name}' on Muspy", self.parent)
        add_to_muspy_action.triggered.connect(lambda: self.muspy_manager.follow_artist_from_name(artist_name))
        menu.addAction(add_to_muspy_action)
        
        # Show the menu
        menu.exec(table.mapToGlobal(position))

  
   


    def setup_spotify(self):
        # Initialize Spotify auth manager with credentials
        self.spotify_auth = SpotifyAuthManager(
            client_id=self.spotify_client_id,
            client_secret=self.spotify_client_secret,
            parent_widget=self
        )
        
        # Try to authenticate
        if self.spotify_auth.is_authenticated() or self.spotify_auth.authenticate():
            self.spotify_authenticated = True
            user_info = self.spotify_auth.get_user_info()
            if user_info:
                self.spotify_user_id = user_info['id']
                print(f"Authenticated with Spotify as: {user_info.get('display_name')}")
        else:
            self.spotify_authenticated = False
            print("Failed to authenticate with Spotify")


    def sync_spotify(self):
        """
        Synchronize selected artists from JSON to Spotify (follow them on Spotify)
        """
        # Check if Spotify credentials are configured
        if not self.spotify_enabled:
            self.ui_callback.clear()
            self.ui_callback.show()
            self.ui_callback.append("Spotify credentials not configured. Please check your settings.")
            return
        
        # Clear the results area
        self.ui_callback.clear()
        self.ui_callback.show()
        self.ui_callback.append("Starting Spotify synchronization...\n")
        QApplication.processEvents()
        
        # Get an authenticated Spotify client
        try:
            self.ui_callback.append("Authenticating with Spotify...")
            QApplication.processEvents()
            
            # Get the Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                self.ui_callback.append("Failed to get Spotify client. Please check authentication.")
                return
                
            # Get user info to confirm authentication
            user_info = spotify_client.current_user()
            if user_info and 'id' in user_info:
                self.ui_callback.append(f"Successfully authenticated as {user_info.get('display_name', user_info['id'])}")
            else:
                self.ui_callback.append("Authentication succeeded but user info couldn't be retrieved.")
                return
            
            # Get the selected artists from JSON
            json_path = Path(PROJECT_ROOT, ".content", "cache", "artists_selected.json")
            if not os.path.exists(json_path):
                self.ui_callback.append("No selected artists found. Please load artists first.")
                return
                
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
                
            if not artists_data:
                self.ui_callback.append("No artists found in the selection file.")
                return
                
            total_artists = len(artists_data)
            self.ui_callback.append(f"Found {total_artists} artists to synchronize with Spotify.")
            QApplication.processEvents()
            
            # Create a progress bar dialog
            from PyQt6.QtWidgets import QProgressDialog
            progress = QProgressDialog("Syncing artists with Spotify...", "Cancel", 0, total_artists, self.parent)
            progress.setWindowTitle("Spotify Synchronization")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)  # Show immediately
            progress.setValue(0)
            
            # Counters for results
            successful_follows = 0
            already_following = 0
            artists_not_found = 0
            failed_follows = 0
            
            # Create a text widget to log the results
            log_text = QTextEdit()
            log_text.setReadOnly(True)
            log_text.append("Spotify Synchronization Log:\n")
            
            # Process each artist
            for i, artist_data in enumerate(artists_data):
                # Check if user canceled
                if progress.wasCanceled():
                    self.ui_callback.append("Synchronization canceled by user.")
                    break
                    
                # Handle None values in artist_data
                if artist_data is None:
                    log_text.append(f"Skipping artist at index {i} - data is None")
                    failed_follows += 1
                    continue
                    
                # Make sure artist_data is a dictionary
                if not isinstance(artist_data, dict):
                    log_text.append(f"Skipping artist at index {i} - data is not a dictionary: {type(artist_data)}")
                    failed_follows += 1
                    continue
                    
                artist_name = artist_data.get("nombre", "")
                if not artist_name:
                    log_text.append(f"Skipping artist with no name")
                    failed_follows += 1
                    continue
                    
                # Update progress
                progress.setValue(i)
                progress.setLabelText(f"Processing {artist_name} ({i+1}/{total_artists})")
                QApplication.processEvents()
                
                # Search for the artist on Spotify
                try:
                    results = spotify_client.search(q=f'artist:"{artist_name}"', type='artist', limit=1)
                    
                    if results and 'artists' in results and 'items' in results['artists'] and results['artists']['items']:
                        artist = results['artists']['items'][0]
                        artist_id = artist['id']
                        
                        # Check if already following
                        is_following = spotify_client.current_user_following_artists([artist_id])
                        if is_following and is_following[0]:
                            log_text.append(f"✓ Already following {artist_name} on Spotify")
                            already_following += 1
                        else:
                            # Follow the artist
                            spotify_client.user_follow_artists([artist_id])
                            log_text.append(f"✓ Successfully followed {artist_name} on Spotify")
                            successful_follows += 1
                    else:
                        log_text.append(f"✗ Artist not found: {artist_name}")
                        artists_not_found += 1
                except Exception as e:
                    log_text.append(f"✗ Error following {artist_name}: {str(e)}")
                    failed_follows += 1
                    self.logger.error(f"Error following artist {artist_name} on Spotify: {e}")
            
            # Complete the progress
            progress.setValue(total_artists)
            
            # Show summary in results text
            self.ui_callback.clear()
            self.ui_callback.append(f"Spotify synchronization completed\n")
            self.ui_callback.append(f"Total artists processed: {total_artists}")
            self.ui_callback.append(f"Successfully followed: {successful_follows}")
            self.ui_callback.append(f"Already following: {already_following}")
            self.ui_callback.append(f"Not found on Spotify: {artists_not_found}")
            self.ui_callback.append(f"Failed: {failed_follows}")
            
            # Show the detailed log in a dialog
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton
            log_dialog = QDialog(self.parent)
            log_dialog.setWindowTitle("Spotify Sync Results")
            log_dialog.setMinimumSize(600, 400)
            
            layout = QVBoxLayout(log_dialog)
            layout.addWidget(log_text)
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(log_dialog.accept)
            layout.addWidget(close_button)
            
            log_dialog.exec()
            
            # Show a message box with results
            QMessageBox.information(
                self.parent,
                "Spotify Synchronization Complete",
                f"Successfully followed {successful_follows} artists on Spotify.\n"
                f"Already following: {already_following}\n"
                f"Artists not found: {artists_not_found}\n"
                f"Failed: {failed_follows}"
            )
                
        except Exception as e:
            error_msg = f"Error during Spotify synchronization: {e}"
            self.ui_callback.append(error_msg)
            self.logger.error(error_msg, exc_info=True)




    def unfollow_artist_from_spotify(self, artist_id, artist_name=None):
        """
        Unfollow an artist from Spotify
        
        Args:
            artist_id (str): Spotify ID of the artist to unfollow
            artist_name (str, optional): Artist name for display purposes
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.ensure_spotify_auth():
            self.logger.error("Spotify authentication required")
            return False
        
        try:
            # Get Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                self.logger.error("Failed to get Spotify client")
                return False
            
            # Check if actually following this artist before trying to unfollow
            is_following = spotify_client.current_user_following_artists([artist_id])
            if not is_following or not is_following[0]:
                artist_display = artist_name or artist_id
                self.logger.info(f"Not following {artist_display} on Spotify")
                return False
            
            # Unfollow the artist
            spotify_client.user_unfollow_artists([artist_id])
            
            artist_display = artist_name or artist_id
            self.logger.info(f"Successfully unfollowed {artist_display} from Spotify")
            return True
        except Exception as e:
            self.logger.error(f"Error unfollowing artist from Spotify: {e}", exc_info=True)
            return False


