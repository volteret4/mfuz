# submodules/lastfm/lastfm_manager.py
import sys
import os
import json
import requests
import logging
import time
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QMessageBox, QInputDialog, QLineEdit, QProgressDialog, QApplication, QDialog,
                            QHBoxLayout, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                            QDialogButtonBox, QSpinBox, QComboBox, QLabel, QCheckBox, QMenu)
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtGui import QAction, QCursor
#from modules.submodules.muspy import cache_manager
from modules.submodules.muspy.progress_utils import AuthWorker

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import PROJECT_ROOT

class LastFMManager:
    def __init__(self, 
                parent, 
                project_root, 
                lastfm_api_key=None, 
                lastfm_api_secret=None, 
                lastfm_username=None, 
                ui_callback=None, 
                muspy_id=None, 
                muspy_username=None,
                muspy_manager=None,
                display_manager=None,
                progress_utils=None,
                cache_manager=None,
                musicbrainz_manager=None
                ):

        self.parent = parent
        self.project_root = PROJECT_ROOT
        self.lastfm_api_key = lastfm_api_key
        self.lastfm_api_secret = lastfm_api_secret
        self.lastfm_username = lastfm_username
        #self.logger = logging.getLogger(__name__)
        self.logger = self.parent.logger
        self.lastfm_auth = None
        self.lastfm_enabled = bool(self.lastfm_api_key and self.lastfm_username)
        self.muspy_id = muspy_id
        self.muspy_username = muspy_username
        self.ui_callback = ui_callback or UICallback(None)  # Usar un callback vacío si no se proporciona uno
        self.base_url = "https://muspy.com/api/1"
        self.muspy_manager = muspy_manager
        self.display_manager = display_manager
        self.cache_manager = cache_manager
        self.progress_utils = progress_utils
        self.musicbrainz_manager = musicbrainz_manager

        # Initialize LastFM auth if enabled
        if self.lastfm_enabled:
            try:
                from tools.lastfm_login import LastFMAuthManager
                
                self.logger.info(f"Initializing LastFM auth with: api_key={self.lastfm_api_key}, username={self.lastfm_username}")
                
                self.lastfm_auth = LastFMAuthManager(
                    api_key=self.lastfm_api_key,
                    api_secret=self.lastfm_api_secret,
                    username=self.lastfm_username,
                    parent_widget=self.parent,
                    project_root=self.project_root
                )
                self.logger.info(f"LastFM auth manager initialized for user: {self.lastfm_username}")
            except Exception as e:
                self.logger.error(f"Error initializing LastFM auth manager: {e}", exc_info=True)
                self.lastfm_enabled = False
    


    def get_lastfm_top_artists_direct(self, count=50, period="overall"):
        """
        Get top artists directly from Last.fm API to ensure we get all data fields
        
        Args:
            count (int): Number of top artists to fetch
            period (str): Time period (overall, 7day, 1month, 3month, 6month, 12month)
            
        Returns:
            list: List of artist dictionaries or empty list on error
        """
        if not self.lastfm_api_key or not self.lastfm_username:
            self.logger.error("Last.fm API key or username not configured")
            return []
        
        try:
            # Build API URL
            url = "http://ws.audioscrobbler.com/2.0/"
            params = {
                "method": "user.gettopartists",
                "user": self.lastfm_username,
                "api_key": self.lastfm_api_key,
                "format": "json",
                "limit": count,
                "period": period
            }
            
            # Make the request
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Add debug output to inspect the structure
                self.logger.debug(f"Last.fm API response structure: {json.dumps(data, indent=2)[:500]}...")
                
                if "topartists" in data and "artist" in data["topartists"]:
                    artists = data["topartists"]["artist"]
                    
                    # Process artists
                    result = []
                    for artist in artists:
                        # Extraer datos básicos
                        artist_dict = {
                            "name": artist.get("name", ""),
                            "playcount": int(artist.get("playcount", 0)),
                            "mbid": artist.get("mbid", ""),
                            "url": artist.get("url", "")
                        }
                        
                        # Intentar obtener listeners
                        listeners = artist.get("listeners")
                        if not listeners:
                            # Si no está disponible, intenta hacer una llamada extra para cada artista
                            try:
                                # Solo para los primeros X artistas para no sobrecargar la API
                                if len(result) < 20:  # Limitar a 20 artistas para no hacer demasiadas llamadas
                                    artist_info_params = {
                                        "method": "artist.getInfo",
                                        "artist": artist_dict["name"],
                                        "api_key": self.lastfm_api_key,
                                        "format": "json"
                                    }
                                    artist_info_response = requests.get(url, params=artist_info_params)
                                    if artist_info_response.status_code == 200:
                                        artist_info = artist_info_response.json()
                                        if "artist" in artist_info and "stats" in artist_info["artist"]:
                                            listeners = artist_info["artist"]["stats"].get("listeners", "0")
                            except Exception as e:
                                self.logger.debug(f"Error getting listeners for {artist_dict['name']}: {e}")
                        
                        # Añadir listeners al diccionario
                        artist_dict["listeners"] = int(listeners) if listeners else 0
                        
                        result.append(artist_dict)
                    
                    return result
        
        except Exception as e:
            self.logger.error(f"Error fetching top artists from Last.fm: {e}", exc_info=True)
            return []




    def show_lastfm_top_artists(self, count=50, period="overall", use_cached=True):
        """
        Show top Last.fm artists in the designated widget with caching support
        
        Args:
            count (int): Number of top artists to display
            period (str): Time period for artists (overall, 7day, 1month, 3month, 6month, 12month)
            use_cached (bool): Whether to use cached data when available
        """
        # Check if Last.fm is enabled
        if not self.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "Last.fm is not configured in settings")
            return
        
        # Create a cache key that includes the period and count
        cache_key = f"top_artists_{period}_{count}"
        
        # Try to get from cache first if allowed
        if use_cached:
            cached_data = self.cache_manager.cache_manager(cache_key)
            if cached_data:
                self.display_manager.display_lastfm_artists_in_stacked_widget(cached_data)
                return
        
        # Create progress dialog
        progress = QProgressDialog("Fetching artists from Last.fm...", "Cancel", 0, 100, self.parent)
        progress.setWindowTitle("Loading Artists")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        try:
            # Update progress
            progress.setValue(20)
            QApplication.processEvents()
            
            # Get artists using direct API call
            artists = self.get_lastfm_top_artists_direct(count, period)
            
            # Update progress
            progress.setValue(60)
            QApplication.processEvents()
            
            if not artists:
                QMessageBox.warning(self.parent, "Error", "No artists found on Last.fm account")
                progress.close()
                return
            
            # Log what we found
            self.logger.info(f"Found {len(artists)} artists on Last.fm")
            
            # Cache the results
            self.cache_manager.cache_manager(cache_key, artists)
            
            # Update progress
            progress.setValue(80)
            QApplication.processEvents()
            
            # Display artists in stacked widget table
            self.display_manager.display_lastfm_artists_in_stacked_widget(artists)
            
            # Final progress
            progress.setValue(100)
            
        except Exception as e:
            error_msg = f"Error fetching artists from Last.fm: {e}"
            QMessageBox.warning(self.parent, "Error", error_msg)
            self.logger.error(error_msg, exc_info=True)
        finally:
            progress.close()


    def show_lastfm_top_artists_dialog(self):
        """
        Show a dialog to select period and number of top artists to display
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "Last.fm is not configured in settings")
            return
        
        # Create the dialog
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Last.fm Top Artists Options")
        dialog.setMinimumWidth(300)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Period selection
        period_layout = QHBoxLayout()
        period_label = QLabel("Time period:")
        period_combo = QComboBox()
        period_combo.addItem("7 days", "7day")
        period_combo.addItem("1 month", "1month")
        period_combo.addItem("3 months", "3month")
        period_combo.addItem("6 months", "6month")
        period_combo.addItem("12 months", "12month")
        period_combo.addItem("All time", "overall")
        period_combo.setCurrentIndex(5)  # Default to "All time"
        period_layout.addWidget(period_label)
        period_layout.addWidget(period_combo)
        layout.addLayout(period_layout)
        
        # Artist count
        count_layout = QHBoxLayout()
        count_label = QLabel("Number of artists:")
        count_spin = QSpinBox()
        count_spin.setRange(5, 1000)
        count_spin.setValue(50)
        count_spin.setSingleStep(5)
        count_layout.addWidget(count_label)
        count_layout.addWidget(count_spin)
        layout.addLayout(count_layout)
        
        # Cache option
        cache_check = QCheckBox("Use cached data if available")
        cache_check.setChecked(True)
        layout.addWidget(cache_check)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            period = period_combo.currentData()
            count = count_spin.value()
            use_cached = cache_check.isChecked()
            
            # Call function with selected parameters
            self.show_lastfm_top_artists(count=count, period=period, use_cached=use_cached)



    def show_lastfm_loved_tracks(self, limit=50, use_cached=True):
        """
        Show user's loved tracks from Last.fm with caching support
        
        Args:
            limit (int): Maximum number of tracks to display
            use_cached (bool): Whether to use cached data when available
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "Last.fm username not configured")
            return

        # Try to get from cache first if allowed
        cache_key = f"loved_tracks_{limit}"
        if use_cached:
            cached_data = self.cache_manager.cache_manager(cache_key)
            if cached_data:
                self.display_manager.display_loved_tracks_in_stacked_widget(cached_data)
                return

        # Create progress dialog
        progress = QProgressDialog("Fetching loved tracks from Last.fm...", "Cancel", 0, 100, self.parent)
        progress.setWindowTitle("Loading Loved Tracks")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        
        try:
            # Get LastFM network - using direct pylast approach for reliability
            import pylast
            network = pylast.LastFMNetwork(
                api_key=self.lastfm_api_key,
                api_secret=self.lastfm_api_secret
            )
            
            # Update progress
            progress.setValue(20)
            QApplication.processEvents()
            
            # Get user object directly
            user = network.get_user(self.lastfm_username)
            
            # Update progress
            progress.setValue(40)
            QApplication.processEvents()
            
            # Get loved tracks directly with pylast
            self.logger.info(f"Fetching up to {limit} loved tracks for user {self.lastfm_username}")
            loved_tracks = user.get_loved_tracks(limit=limit)
            
            # Update progress
            progress.setValue(60)
            QApplication.processEvents()
            
            if not loved_tracks:
                QMessageBox.warning(self.parent, "Error", "No loved tracks found on Last.fm account")
                progress.close()
                return
            
            # Convert pylast objects to serializable format for caching
            serializable_tracks = []
            for track in loved_tracks:
                track_dict = {
                    'artist': track.track.artist.name,
                    'title': track.track.title,
                    'url': track.track.get_url(),
                    'date': track.date if hasattr(track, 'date') else None,
                }
                
                # Try to get album info if available
                try:
                    album = track.track.get_album()
                    if album:
                        track_dict['album'] = album.title
                except:
                    track_dict['album'] = ""
                    
                serializable_tracks.append(track_dict)
            
            # Cache the results
            self.cache_manager.cache_manager(cache_key, serializable_tracks)
            
            # Store for later use
            self.loved_tracks_list = loved_tracks
            
            # Update progress
            progress.setValue(80)
            
            # Display in stacked widget
            self.display_manager.display_loved_tracks_in_stacked_widget(loved_tracks)
            
            # Final progress
            progress.setValue(100)
            
        except Exception as e:
            error_msg = f"Error fetching loved tracks from Last.fm: {e}"
            QMessageBox.warning(self.parent, "Error", error_msg)
            self.logger.error(error_msg, exc_info=True)
        finally:
            progress.close()


    def sync_top_artists_from_lastfm(self, count=50, period="overall"):
        """
        Synchronize top Last.fm artists with Muspy
        
        Args:
            count (int): Number of top artists to sync
            period (str): Period to fetch top artists for (7day, 1month, 3month, 6month, 12month, overall)
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "Last.fm username not configured")
            return

        if not self.muspy_id:
            # Try to get the Muspy ID if it's not set
            self.get_muspy_id()
            if not self.muspy_id:
                QMessageBox.warning(self.parent, "Error", "Could not get Muspy ID. Please check your credentials.")
                return

        # Clear the results area and make sure it's visible
        self.ui_callback.clear()
        self.ui_callback.show()
        self.ui_callback.append(f"Starting Last.fm synchronization for user {self.lastfm_username}...\n")
        self.ui_callback.append(f"Syncing top {count} artists from Last.fm to Muspy using period: {period}\n")
        QApplication.processEvents()  # Force UI update
        
        # Create progress dialog
        progress = QProgressDialog("Syncing artists with Muspy...", "Cancel", 0, 100, self.parent)
        progress.setWindowTitle("Syncing with Muspy")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        
        try:
            # First try direct API import
            import_url = f"{self.base_url}/import/{self.muspy_id}"
            auth = (self.muspy_username, self.muspy_id)
            
            import_data = {
                'type': 'lastfm',
                'username': self.lastfm_username,
                'count': count,
                'period': period
            }
            
            self.ui_callback.append("Sending request to Muspy API...")
            progress.setValue(20)
            QApplication.processEvents()  # Force UI update
            
            # Use POST for the import endpoint
            response = requests.post(import_url, auth=auth, json=import_data)
            
            if response.status_code in [200, 201]:
                success_msg = f"Successfully synchronized top {count} artists from Last.fm account {self.lastfm_username}"
                self.ui_callback.append(success_msg)
                progress.setValue(100)
                
                # Show success message
                QMessageBox.information(self.parent, "Synchronization Complete", success_msg)
                return
            else:
                # If direct API fails, try alternative method
                self.ui_callback.append(f"Direct API import failed with status {response.status_code}. Trying alternative method...")
                progress.setValue(30)
                QApplication.processEvents()  # Force UI update
                
                # Use the alternative method - first get the top artists
                import pylast
                network = pylast.LastFMNetwork(
                    api_key=self.lastfm_api_key,
                    api_secret=self.lastfm_api_secret
                )
                
                if not network:
                    self.ui_callback.append("Could not connect to LastFM. Please check your credentials.")
                    progress.setValue(100)
                    return
                
                progress.setValue(40)
                self.ui_callback.append(f"Fetching top {count} artists from LastFM...")
                QApplication.processEvents()  # Force UI update
                
                # Convert period to pylast format if needed
                pylast_period = period
                if period == "7day":
                    pylast_period = pylast.PERIOD_7DAYS
                elif period == "1month":
                    pylast_period = pylast.PERIOD_1MONTH
                elif period == "3month":
                    pylast_period = pylast.PERIOD_3MONTHS
                elif period == "6month":
                    pylast_period = pylast.PERIOD_6MONTHS
                elif period == "12month":
                    pylast_period = pylast.PERIOD_12MONTHS
                else:
                    pylast_period = pylast.PERIOD_OVERALL
                
                # Get the user and top artists
                user = network.get_user(self.lastfm_username)
                top_artists = user.get_top_artists(limit=count, period=pylast_period)
                
                if not top_artists:
                    self.ui_callback.append("No artists found on LastFM account.")
                    progress.setValue(100)
                    return
                
                self.ui_callback.append(f"Found {len(top_artists)} artists on LastFM.")
                progress.setValue(50)
                QApplication.processEvents()  # Force UI update
                
                # Search for MBIDs and add to Muspy
                successful_adds = 0
                failed_adds = 0
                mbid_not_found = 0
                
                # Process each artist
                for i, artist in enumerate(top_artists):
                    if progress.wasCanceled():
                        self.ui_callback.append("Operation canceled.")
                        break
                    
                    artist_name = artist.item.name
                    progress_value = 50 + int((i / len(top_artists)) * 40)  # Scale to 50-90%
                    progress.setValue(progress_value)
                    progress.setLabelText(f"Processing {artist_name} ({i+1}/{len(top_artists)})")
                    QApplication.processEvents()  # Force UI update
                    
                    # Try to use MBID from LastFM if available
                    mbid = artist.item.get_mbid() if hasattr(artist.item, 'get_mbid') else None
                    
                    # If no MBID, search for it
                    if not mbid:
                        self.ui_callback.append(f"Searching MBID for {artist_name}...")
                        mbid = self.muspy_manager.get_mbid_artist_searched(artist_name)
                    
                    if mbid:
                        # Add artist to Muspy
                        self.ui_callback.append(f"Adding {artist_name} with mbid {mbid} to Muspy...")
                        result = self.muspy_manager.add_artist_to_muspy_silent(mbid, artist_name)
                        if result == 1:
                            successful_adds += 1
                            self.ui_callback.append(f"Successfully added {artist_name} to Muspy")
                        elif result == 0:
                            # Already exists
                            successful_adds += 1
                            self.ui_callback.append(f"{artist_name} already exists in Muspy")
                        else:
                            failed_adds += 1
                            self.ui_callback.append(f"Failed to add {artist_name} to Muspy")
                    else:
                        mbid_not_found += 1
                        self.ui_callback.append(f"Could not find MBID for {artist_name}")
                    
                    # Check if we should continue
                    if i % 5 == 0:
                        self.ui_callback.append(f"Processed: {i+1}/{len(top_artists)}, Added: {successful_adds}, Failed: {failed_adds}, No MBID: {mbid_not_found}")
                        QApplication.processEvents()  # Force UI update
                
                # Final progress
                progress.setValue(100)
                
                # Summary message
                summary_msg = f"Sync complete: Added {successful_adds}, Failed {failed_adds}, No MBID {mbid_not_found}"
                self.ui_callback.append(summary_msg)
                
                # Show a message box with results
                QMessageBox.information(self.parent, "Synchronization Complete", summary_msg)
        except Exception as e:
            error_msg = f"Error syncing with Muspy API: {e}"
            self.ui_callback.append(error_msg)
            self.logger.error(error_msg, exc_info=True)
            
            # Show error message
            QMessageBox.warning(self.parent, "Error", f"Error during synchronization: {str(e)}")
        finally:
            progress.close()
                


    def add_lastfm_artist_to_muspy(self, artist_name):
        """
        Add a Last.fm artist to Muspy - revisada para asegurar la correcta autenticación
        
        Args:
            artist_name (str): Name of the artist to add
        """
        if not self.muspy_username or not self.muspy_id:
            QMessageBox.warning(self.parent, "Error", "Muspy configuration not available")
            return
        
        # Comprobar y obtener ID de Muspy si no está establecido
        if not self.muspy_id:
            self.get_muspy_id()
            if not self.muspy_id:
                QMessageBox.warning(self.parent, "Error", "Could not get Muspy ID. Please check your credentials.")
                return

        # Mostrar progreso mientras buscamos MBID
        progress = QProgressDialog("Searching for artist...", "Cancel", 0, 100, self.parent)
        progress.setWindowTitle("Adding Artist")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(20)
        progress.show()
        QApplication.processEvents()
                
        # First get the MBID for the artist
        mbid = self.muspy_manager.get_mbid_artist_searched(artist_name)
        progress.setValue(50)
        QApplication.processEvents()
        
        if mbid:
            # Try to add the artist to Muspy
            progress.setLabelText(f"Adding {artist_name} to Muspy...")
            progress.setValue(70)
            QApplication.processEvents()
            
            success = self.muspy_manager.add_artist_to_muspy(mbid, artist_name)
            
            progress.setValue(100)
            
            if success:
                QMessageBox.information(self.parent, "Success", f"Successfully added {artist_name} to Muspy")
            else:
                # Depuración adicional para identificar el problema
                self.logger.error(f"Failed to add {artist_name} to Muspy. ID: {self.muspy_id}, MBID: {mbid}")
                QMessageBox.warning(self.parent, "Error", f"Failed to add {artist_name} to Muspy. Check logs for details.")
        else:
            progress.close()
            QMessageBox.warning(self.parent, "Error", f"Could not find MusicBrainz ID for {artist_name}")




    def show_artist_info(self, artist_name):
        """
        Show detailed information about an artist
        
        Args:
            artist_name (str): Name of the artist
        """
        try:
            # Clear results
            self.ui_callback.clear()
            self.ui_callback.show()
            self.ui_callback.append(f"Fetching information for {artist_name}...\n")
            QApplication.processEvents()
            
            # Get Last.fm info
            if hasattr(self, 'lastfm_auth') and self.lastfm_auth:
                network = self.lastfm_auth.get_network()
                if network:
                    try:
                        artist = network.get_artist(artist_name)
                        
                        # Display basic info
                        self.ui_callback.append(f"🎵 {artist_name}")
                        
                        # Get listener and playcount info
                        if hasattr(artist, 'get_listener_count'):
                            self.ui_callback.append(f"Listeners: {artist.get_listener_count():,}")
                        if hasattr(artist, 'get_playcount'):
                            self.ui_callback.append(f"Total Playcount: {artist.get_playcount():,}")
                        
                        # Get bio if available
                        bio = None
                        if hasattr(artist, 'get_bio_summary'):
                            bio = artist.get_bio_summary(language='en')
                        
                        if bio:
                            # Strip HTML tags for cleaner display
                            import re
                            bio_text = re.sub(r'<[^>]+>', '', bio)
                            self.ui_callback.append("\nBio:")
                            self.ui_callback.append(bio_text)
                        
                        # Get top tracks
                        if hasattr(artist, 'get_top_tracks'):
                            top_tracks = artist.get_top_tracks(limit=5)
                            if top_tracks:
                                self.ui_callback.append("\nTop Tracks:")
                                for i, track in enumerate(top_tracks, 1):
                                    self.ui_callback.append(f"{i}. {track.item.title}")
                        
                        # Get similar artists
                        if hasattr(artist, 'get_similar'):
                            similar = artist.get_similar(limit=5)
                            if similar:
                                self.ui_callback.append("\nSimilar Artists:")
                                for i, similar_artist in enumerate(similar, 1):
                                    self.ui_callback.append(f"{i}. {similar_artist.item.name}")
                    except Exception as e:
                        self.ui_callback.append(f"Error getting Last.fm info: {e}")
            
            # Get local database info
            self.ui_callback.append("\nLooking for local info...")
            
            # Use consultar_items_db to check if we have this artist in our database
            if self.parent.query_db_script_path and self.parent.db_path:
                try:
                    import subprocess
                    
                    # Build command
                    cmd = f"python {self.parent.query_db_script_path} --db {self.parent.db_path} --artist \"{artist_name}\" --artist-info"
                    
                    # Run command
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0 and result.stdout:
                        try:
                            artist_info = json.loads(result.stdout)
                            
                            # Display database info
                            if 'links' in artist_info:
                                self.ui_callback.append("\nOnline Links:")
                                for service, url in artist_info['links'].items():
                                    self.ui_callback.append(f"- {service.capitalize()}: {url}")
                            
                            if 'albums' in artist_info:
                                self.ui_callback.append(f"\nAlbums in Database: {len(artist_info['albums'])}")
                                for album in artist_info['albums']:
                                    year = f" ({album['year']})" if album.get('year') else ""
                                    self.ui_callback.append(f"- {album['name']}{year}")
                        except json.JSONDecodeError:
                            self.ui_callback.append("Error parsing database info")
                    else:
                        self.ui_callback.append("Artist not found in local database")
                except Exception as e:
                    self.ui_callback.append(f"Error querying local database: {e}")
            else:
                self.ui_callback.append("Database query not available. Check configuration.")
        
        except Exception as e:
            error_msg = f"Error fetching artist info: {e}"
            self.ui_callback.append(error_msg)
            self.logger.error(error_msg, exc_info=True)


    def _start_background_auth(self):
        """Start MusicBrainz authentication in a background thread"""
        if not hasattr(self, 'lastfm_auth') or not self.lastfm_enabled:
            return
            
        # Create a QThread
        self.auth_thread = QThread()
        
        # Create the worker
        self.auth_worker = AuthWorker(
            self.lastfm_auth, 
            self.lastfm_username, 
            self.lastfm_api_key
        )
        
        # Move worker to thread
        self.auth_worker.moveToThread(self.auth_thread)
        
        # Connect signals
        self.auth_thread.started.connect(self.auth_worker.authenticate)
        self.auth_worker.finished.connect(self.auth_thread.quit)
        self.auth_worker.finished.connect(self.musicbrainz_manager.handle_background_auth_result)
        
        # Clean up connections
        self.auth_thread.finished.connect(self.auth_worker.deleteLater)
        self.auth_thread.finished.connect(self.auth_thread.deleteLater)
        
        # Start the thread
        self.auth_thread.start()




    def manage_lastfm_auth(self):
        """Manage LastFM authentication settings"""
        if not self.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "LastFM credentials not configured")
            return
            
        # Check current status
        is_authenticated = False
        user_info = None
        
        if hasattr(self, 'lastfm_auth'):
            is_authenticated = self.lastfm_auth.is_authenticated()
            user_info = self.lastfm_auth.get_user_info()
        
        # Create management menu
        auth_menu = QMenu(self.parent)
        
        # Show status
        status_action = QAction(f"Status: {'Authenticated' if is_authenticated else 'Not Authenticated'}", self.parent)
        status_action.setEnabled(False)
        auth_menu.addAction(status_action)
        
        # Show user info if available
        if user_info:
            user_info_action = QAction(f"User: {user_info.get('name')} (Playcount: {user_info.get('playcount', 'N/A')})", self.parent)
            user_info_action.setEnabled(False)
            auth_menu.addAction(user_info_action)
        
        auth_menu.addSeparator()
        
        # Authentication actions
        authenticate_action = QAction("Authenticate with LastFM", self.parent)
        authenticate_action.triggered.connect(self._authenticate_lastfm)
        auth_menu.addAction(authenticate_action)
        
        if is_authenticated:
            clear_action = QAction("Clear Authentication", self.parent)
            clear_action.triggered.connect(self._clear_lastfm_auth)
            auth_menu.addAction(clear_action)
        
        auth_menu.addSeparator()
        
        # Test actions for authenticated users
        if is_authenticated:
            test_action = QAction("Test LastFM Connection", self.parent)
            test_action.triggered.connect(self._test_lastfm_connection)
            auth_menu.addAction(test_action)
        
        # Show menu
        auth_menu.exec(QCursor.pos())

    def _authenticate_lastfm(self):
        """Authenticate with LastFM by getting password from user"""
        if not hasattr(self, 'lastfm_auth') or not self.lastfm_username:
            QMessageBox.warning(self.parent, "Error", "LastFM configuration not available")
            return
        
        # Prompt for password
        password, ok = QInputDialog.getText(
            self.parent,
            "LastFM Authentication",
            f"Enter password for LastFM user {self.lastfm_username}:",
            QLineEdit.EchoMode.Password
        )
        
        if not ok or not password:
            self.ui_callback.append("Authentication canceled.")
            return
        
        # Update password in auth manager
        self.lastfm_auth.password = password
        
        # Try to authenticate
        self.ui_callback.clear()
        self.ui_callback.show()
        self.ui_callback.append("Authenticating with LastFM...")
        QApplication.processEvents()
        
        if self.lastfm_auth.authenticate():
            self.ui_callback.append("Authentication successful!")
            user_info = self.lastfm_auth.get_user_info()
            if user_info:
                self.ui_callback.append(f"Logged in as: {user_info.get('name')}")
                self.ui_callback.append(f"Playcount: {user_info.get('playcount', 'N/A')}")
        else:
            self.ui_callback.append("Authentication failed. Please check your username and password.")



    def _clear_lastfm_auth(self):
        """Clear LastFM authentication data"""
        if hasattr(self, 'lastfm_auth'):
            self.lastfm_auth.clear_session()
            self.ui_callback.clear()
            self.ui_callback.show()
            self.ui_callback.append("LastFM authentication data cleared.")
            QMessageBox.information(self.parent, "Authentication Cleared", "LastFM authentication data has been cleared.")


    def _test_lastfm_connection(self):
        """Test the LastFM connection with a simple API call"""
        if not hasattr(self, 'lastfm_auth'):
            QMessageBox.warning(self.parent, "Error", "LastFM configuration not available")
            return
        
        self.ui_callback.clear()
        self.ui_callback.show()
        self.ui_callback.append("Testing LastFM connection...")
        QApplication.processEvents()
        
        # Get user info
        user_info = self.lastfm_auth.get_user_info()
        if user_info:
            self.ui_callback.append("Connection successful!")
            self.ui_callback.append(f"User: {user_info.get('name')}")
            self.ui_callback.append(f"Playcount: {user_info.get('playcount', 'N/A')}")
            self.ui_callback.append(f"URL: {user_info.get('url', 'N/A')}")
            
            # Try to get top artists if we're authenticated
            if self.lastfm_auth.is_authenticated():
                self.ui_callback.append("\nFetching top artists...")
                QApplication.processEvents()
                
                top_artists = self.lastfm_auth.get_top_artists(limit=5)
                if top_artists:
                    self.ui_callback.append("\nTop 5 Artists:")
                    for artist in top_artists:
                        self.ui_callback.append(f"• {artist['name']} (Playcount: {artist['playcount']})")
                else:
                    self.ui_callback.append("Could not retrieve top artists.")
        else:
            self.ui_callback.append("Connection failed. Please check your LastFM credentials.")




    def sync_lastfm_artists(self):
        """
        Synchronize selected artists with Last.fm (love tracks by these artists)
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "Last.fm credentials not configured")
            return

        # Clear the results area and make sure it's visible
        self.ui_callback.clear()
        self.ui_callback.show()
        self.ui_callback.append(f"Starting Last.fm synchronization...\n")
        QApplication.processEvents()  # Update UI

        try:
            # Get the selected artists from the JSON file
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
            self.ui_callback.append(f"Found {total_artists} artists to synchronize with Last.fm.")
            QApplication.processEvents()
            
            # Get LastFM network
            network = self.lastfm_auth.get_network()
            if not network:
                self.ui_callback.append("Could not connect to LastFM. Please check your credentials.")
                return
                
            # Check if we're authenticated for write operations
            if not self.lastfm_auth.is_authenticated():
                if QT_AVAILABLE:
                    reply = QMessageBox.question(
                        self.parent, 
                        "LastFM Authentication Required",
                        "Following artists requires LastFM authentication. Do you want to provide your password to authenticate?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        # Prompt for password
                        password, ok = QInputDialog.getText(
                            self,
                            "LastFM Password",
                            f"Enter LastFM password for {self.lastfm_username}:",
                            QLineEdit.EchoMode.Password
                        )
                        
                        if ok and password:
                            # Update the auth manager with the password and try to authenticate
                            self.lastfm_auth.password = password
                            if not self.lastfm_auth.authenticate():
                                self.ui_callback.append("Authentication failed. Cannot follow artists.")
                                return
                        else:
                            self.ui_callback.append("Authentication canceled. Will only retrieve artist info.")
                    else:
                        self.ui_callback.append("Authentication declined. Will only retrieve artist info.")
                else:
                    self.ui_callback.append("Authentication required but not available without UI. Will only retrieve artist info.")
            
            successful_syncs = 0
            failed_syncs = 0
            info_only = 0
            
            # Process artists
            for i, artist_data in enumerate(artists_data):
                artist_name = artist_data.get('nombre', '')
                
                # Update progress
                if (i + 1) % 5 == 0 or i == total_artists - 1:
                    progress = int((i + 1) / total_artists * 50)
                    self.ui_callback.clear()
                    self.ui_callback.append(f"Syncing with Last.fm... {i + 1}/{total_artists}\n")
                    self.ui_callback.append(f"Progress: [" + "#" * progress + "-" * (50 - progress) + "]\n")
                    self.ui_callback.append(f"Success: {successful_syncs}, Info only: {info_only}, Failed: {failed_syncs}\n")
                    QApplication.processEvents()
                
                try:
                    # If authenticated, try to follow the artist
                    if self.lastfm_auth.is_authenticated():
                        if self.lastfm_auth.follow_artist(artist_name):
                            successful_syncs += 1
                        else:
                            failed_syncs += 1
                    else:
                        # Just get artist info if not authenticated
                        try:
                            artist = network.get_artist(artist_name)
                            # Just logging that we found the artist
                            self.logger.info(f"Found artist {artist_name} on Last.fm")
                            info_only += 1
                        except Exception as e:
                            self.logger.error(f"Error getting info for {artist_name}: {e}")
                            failed_syncs += 1
                            
                except Exception as e:
                    failed_syncs += 1
                    self.logger.error(f"Error syncing {artist_name} with Last.fm: {e}")
            
            # Show final summary
            self.ui_callback.clear()
            self.ui_callback.append(f"Last.fm synchronization completed\n")
            self.ui_callback.append(f"Total artists processed: {total_artists}\n")
            
            if self.lastfm_auth.is_authenticated():
                self.ui_callback.append(f"Successfully followed: {successful_syncs}\n")
            else:
                self.ui_callback.append(f"Artists found (info only): {info_only}\n")
                
            self.ui_callback.append(f"Failed: {failed_syncs}\n")
            
            # Show a message box with results
            QMessageBox.information(
                self.parent,
                "Last.fm Synchronization Complete",
                f"Processed {total_artists} artists with Last.fm.\n" +
                (f"Successfully followed: {successful_syncs}\n" if self.lastfm_auth.is_authenticated() else f"Artists found (info only): {info_only}\n") +
                f"Failed: {failed_syncs}"
            )
            
        except Exception as e:
            error_msg = f"Error in Last.fm synchronization: {e}"
            self.ui_callback.append(error_msg)
            self.logger.error(error_msg, exc_info=True)
 
    def unlove_lastfm_track(self, index):
        """
        Remove a track from Last.fm loved tracks
        
        Args:
            index (int): Index of the track in the loved_tracks_list
        """
        if not hasattr(self, 'loved_tracks_list') or index >= len(self.loved_tracks_list):
            QMessageBox.warning(self.parent, "Error", "Track information not available")
            return
            
        if not self.lastfm_auth.is_authenticated():
            # Need to authenticate for write operations
            reply = QMessageBox.question(
                self.parent,
                "Authentication Required",
                "To remove a track from your loved tracks, you need to authenticate with Last.fm. Proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Prompt for password
                password, ok = QInputDialog.getText(
                    self,
                    "Last.fm Password",
                    f"Enter password for {self.lastfm_username}:",
                    QLineEdit.EchoMode.Password
                )
                
                if ok and password:
                    # Try to authenticate
                    self.lastfm_auth.password = password
                    if not self.lastfm_auth.authenticate():
                        QMessageBox.warning(self.parent, "Authentication Failed", "Could not authenticate with Last.fm")
                        return
                else:
                    return  # Canceled
            else:
                return  # Declined authentication
        
        # Now we should be authenticated
        try:
            # Get the track from our list
            loved_track = self.loved_tracks_list[index]
            track = loved_track.track
            
            # Confirm with user
            reply = QMessageBox.question(
                self.parent,
                "Confirm Unlove",
                f"Remove '{track.title}' by {track.artist.name} from your loved tracks?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Try to unlove the track
                network = self.lastfm_auth.get_network()
                if network:
                    track.unlove()
                    
                    # Show success message
                    QMessageBox.information(self.parent, "Success", "Track removed from loved tracks")
                    
                    # Refresh the list
                    self.show_lastfm_loved_tracks()
                else:
                    QMessageBox.warning(self.parent, "Error", "Could not connect to Last.fm")
        except Exception as e:
            error_msg = f"Error removing track from loved tracks: {e}"
            QMessageBox.warning(self.parent, "Error", error_msg)
            self.logger.error(error_msg, exc_info=True)



    def show_track_context_menu(self, position):
        """
        Show context menu for tracks in the results text
        """
        # Get the cursor at the clicked position
        cursor = self.ui_callback.cursor_for_position(position)
        if not cursor:
            return
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        
        # Get the line text
        line_text = cursor.selectedText()
        
        # Check if this is a track line (starts with a number followed by a dot)
        import re
        if re.match(r'^\d+\.', line_text):
            # Extract track info from the line
            match = re.search(r'^\d+\.\s+(.+?)\s+-\s+(.+)$', line_text)
            if match:
                artist_name = match.group(1)
                track_name = match.group(2)
                
                # Get the index
                index_match = re.search(r'^(\d+)', line_text)
                track_index = int(index_match.group(1)) - 1 if index_match else -1
                
                # Create context menu
                menu = QMenu(self)
                
                # Add options
                unlove_action = QAction(f"Remove from Loved Tracks", self)
                search_action = QAction(f"Search for '{track_name}'", self)
                add_artist_muspy_action = QAction(f"Add {artist_name} to Muspy", self)
                
                # Connect actions
                if track_index >= 0 and hasattr(self, 'loved_tracks_list') and track_index < len(self.loved_tracks_list):
                    unlove_action.triggered.connect(lambda: self.unlove_lastfm_track(track_index))
                search_action.triggered.connect(lambda: self.search_track(artist_name, track_name))
                add_artist_muspy_action.triggered.connect(lambda: self.add_lastfm_artist_to_muspy(artist_name))
                
                # Add actions to menu
                menu.addAction(unlove_action)
                menu.addSeparator()
                menu.addAction(search_action)
                menu.addAction(add_artist_muspy_action)
                
                # Show menu
                menu.exec(self.ui_callback.map_to_global(position))



    def _display_loved_tracks_in_table(self, loved_tracks):
        """
        Display loved tracks in the stacked widget table
        
        Args:
            loved_tracks (list): List of loved tracks from Last.fm
        """
        # Find the stackedWidget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Could not find stackedWidget")
            return
        
        # Find the loved tracks page (assuming it's the third page index 2)
        loved_page = None
        for i in range(stack_widget.count()):
            page = stack_widget.widget(i)
            if page.objectName() == "loved_tracks_page":
                loved_page = page
                break
        
        if not loved_page:
            self.logger.error("Could not find loved_tracks_page in stackedWidget")
            return
        
        # Find the table in the loved tracks page
        table = loved_page.findChild(QTableWidget, "loved_tracks_table")
        if not table:
            self.logger.error("Could not find loved_tracks_table in loved_tracks_page")
            return
        
        # Find the count label
        count_label = loved_page.findChild(QLabel, "count_label")
        if count_label:
            count_label.setText(f"Showing {len(loved_tracks)} loved tracks for {self.lastfm_username}")
        
        # Clear and set up the table
        table.setRowCount(0)  # Clear existing rows
        table.setRowCount(len(loved_tracks))  # Set new row count
        
        # Fill the table with data
        for i, loved_track in enumerate(loved_tracks):
            # Extract data from pylast objects
            track = loved_track.track
            artist_name = track.artist.name
            track_name = track.title
            
            # Set artist name column
            artist_item = QTableWidgetItem(artist_name)
            table.setItem(i, 0, artist_item)
            
            # Set track name column
            track_item = QTableWidgetItem(track_name)
            table.setItem(i, 1, track_item)
            
            # Set album column (might be empty)
            album_name = ""
            try:
                album = track.get_album()
                if album:
                    album_name = album.title
            except:
                pass
            album_item = QTableWidgetItem(album_name)
            table.setItem(i, 2, album_item)
            
            # Date column (if available)
            date_text = ""
            if hasattr(loved_track, "date") and loved_track.date:
                try:
                    import datetime
                    date_obj = datetime.datetime.fromtimestamp(int(loved_track.date))
                    date_text = date_obj.strftime("%Y-%m-%d")
                except:
                    date_text = str(loved_track.date)
            
            date_item = QTableWidgetItem(date_text)
            table.setItem(i, 3, date_item)
            
            # Actions column with buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            follow_button = QPushButton("Follow Artist")
            follow_button.setFixedWidth(100)
            follow_button.clicked.connect(lambda checked, a=artist_name: self.add_lastfm_artist_to_muspy(a))
            
            actions_layout.addWidget(follow_button)
            table.setCellWidget(i, 4, actions_widget)
        
        # Make sure the columns resize properly
        table.resizeColumnsToContents()
        
        # Switch to the loved tracks page in the stacked widget
        stack_widget.setCurrentWidget(loved_page)
        
        # Hide the results text and show the stacked widget
        if hasattr(self, 'results_text'):
            self.ui_callback.hide()



    def follow_lastfm_artist_on_spotify(self, artist_name):
        """
        Follow a Last.fm artist on Spotify
        
        Args:
            artist_name (str): Name of the artist to follow
        """
        if not self.spotify_enabled:
            QMessageBox.warning(self.parent, "Error", "Spotify configuration not available")
            return
            
        try:
            # Get the Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                self.ui_callback.append("Failed to get Spotify client. Please check authentication.")
                return
                
            # Try to follow the artist
            result = self.follow_artist_on_spotify(artist_name, spotify_client)
            
            if result == 1:
                QMessageBox.information(self.parent, "Success", f"Successfully followed {artist_name} on Spotify")
            elif result == 0:
                QMessageBox.information(self.parent, "Already Following", f"You are already following {artist_name} on Spotify")
            else:
                QMessageBox.warning(self.parent, "Error", f"Failed to follow {artist_name} on Spotify")
                
        except Exception as e:
            error_msg = f"Error following artist on Spotify: {e}"
            self.ui_callback.append(error_msg)
            self.logger.error(error_msg, exc_info=True)


    def show_artist_context_menu(self, position):
        """
        Show context menu for artists in the results text
        """
        # Get the cursor at the clicked position
        cursor = self.ui_callback.cursor_for_position(position)
        if not cursor:
            return
        
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        
        # Get the line text
        line_text = cursor.selectedText()
        
        # Check if this is an artist line (starts with a number followed by a dot)
        import re
        if re.match(r'^\d+\.', line_text):
            # Extract artist name from the line
            match = re.search(r'^\d+\.\s+(.+?)\s+\(Playcount', line_text)
            if match:
                artist_name = match.group(1)
                
                # Create context menu
                menu = QMenu(self)
                
                # Add options
                add_muspy_action = QAction(f"Add {artist_name} to Muspy", self)
                add_spotify_action = QAction(f"Follow {artist_name} on Spotify", self)
                show_info_action = QAction(f"Show info for {artist_name}", self)
                
                # Connect actions
                add_muspy_action.triggered.connect(lambda: self.add_lastfm_artist_to_muspy(artist_name))
                add_spotify_action.triggered.connect(lambda: self.follow_lastfm_artist_on_spotify(artist_name))
                show_info_action.triggered.connect(lambda: self.show_artist_info(artist_name))
                
                # Add actions to menu
                menu.addAction(add_muspy_action)
                menu.addAction(add_spotify_action)
                menu.addSeparator()
                menu.addAction(show_info_action)
                
                # Show menu
                menu.exec(self.ui_callback.map_to_global(position))



    def show_lastfm_custom_top_artists(self):
        """
        Show a dialog to let the user input a custom number of artists to display
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "Last.fm username not configured")
            return
            
        # Create the input dialog
        from PyQt6.QtWidgets import QInputDialog
        
        count, ok = QInputDialog.getInt(
            self,
            "Last.fm Top Artists",
            "Enter number of top artists to display:",
            value=50,
            min=1,
            max=1000,
            step=10
        )
        
        if ok:
            # User clicked OK, proceed with displaying artists
            self.show_lastfm_top_artists(count)




    def _display_top_artists_results(self, top_artists):
        """
        Display the results of top artists fetching
        
        Args:
            top_artists (list): List of top artists data
        """
        if not top_artists:
            self.ui_callback.append("No artists found or retrieval failed.")
            return
        
        # Display artists in a formatted way
        self.ui_callback.clear()
        self.ui_callback.append(f"Top {len(top_artists)} artists for {self.lastfm_username}:\n")
        
        # Create a context menu for the results text
        self.ui_callback.set_context_menu_policy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui_callback.connect_context_menu(self.show_artist_context_menu)
        
        # Store top artists for context menu use
        self.top_artists_list = top_artists
        
        # Display each artist with playcount
        for i, artist in enumerate(top_artists):
            artist_name = artist['name']
            playcount = artist.get('playcount', 'N/A')
            
            # Format line with index for easier selection
            artist_line = f"{i+1}. {artist_name} (Playcount: {playcount})"
            self.ui_callback.append(artist_line)
            
            # Add a special hidden marker for context menu to identify this line as an artist
            # This uses HTML with a hidden span that won't be visible to users
            hidden_marker = f'<span style="display:none" class="artist" data-index="{i}"></span>'
            cursor = self.ui_callback.get_text_cursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.ui_callback.set_text_cursor(cursor)
            self.ui_callback.insert_html(hidden_marker)

        self.ui_callback.append("\nRight-click on an artist to see options.")




    def _display_lastfm_artists_table(self, artists):
        """
        Display Last.fm artists in a table
        
        Args:
            artists (list): List of artist dictionaries from Last.fm
        """
        # Hide the results text if visible
        if hasattr(self, 'results_text') and self.results_text.isVisible():
            self.ui_callback.hide()
        
        # Remove any existing table widget if present
        for i in reversed(range(self.layout().count())):
            item = self.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QTableWidget):
                item.widget().deleteLater()
        
        # Create the table widget
        table = QTableWidget(self)
        table.setObjectName("artists_table")
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Artist", "Playcount", "Actions"])
        
        # Make the table expand to fill all available space
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table.setMinimumHeight(400)  # Ensure reasonable minimum height
        
        # Configure table headers
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Artist
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Playcount
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        # Set row count
        table.setRowCount(len(artists))
        
        # Fill table with artist data
        for i, artist in enumerate(artists):
            artist_name = artist['name']
            playcount = str(artist.get('playcount', 'N/A'))
            
            # Artist name
            name_item = QTableWidgetItem(artist_name)
            table.setItem(i, 0, name_item)
            
            # Playcount
            playcount_item = QTableWidgetItem(playcount)
            table.setItem(i, 1, playcount_item)
            
            # Actions - create a widget with buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            # Add "Follow" button
            follow_button = QPushButton("Follow")
            follow_button.setProperty("artist_name", artist_name)
            follow_button.clicked.connect(lambda checked, a=artist_name: self.add_lastfm_artist_to_muspy(a))
            actions_layout.addWidget(follow_button)
            
            table.setCellWidget(i, 2, actions_widget)
        
        # Create a count label for the number of artists
        count_label = QLabel(f"Showing {len(artists)} top artists for {self.lastfm_username}")
        count_label.setObjectName("count_label")
        
        # Insert into layout - position before the bottom buttons
        main_layout = self.layout()
        insert_position = main_layout.count() - 1
        main_layout.insertWidget(insert_position, count_label)
        main_layout.insertWidget(insert_position + 1, table)
        
        # Add styling to match the releases table
        table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
            }
            QHeaderView::section {
                background-color: #24283b;
                color: #a9b1d6;
                border: none;
                padding: 6px;
            }
            QTableWidget::item {
                border: none;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #364A82;
            }
        """)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
    
        # Resize columns to fit content
        table.resizeColumnsToContents()
        
        # Store reference for later access
        self.artists_table = table
        
        return table



    def sync_lastfm_muspy(self):
        """Synchronize Last.fm artists with Muspy"""
        if not self.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "Last.fm username not configured")
            return

        if not self.muspy_id:
            # Try to get the Muspy ID if it's not set
            self.get_muspy_id()
            if not self.muspy_id:
                QMessageBox.warning(self.parent, "Error", "Could not get Muspy ID. Please check your credentials.")
                return

        # Clear the results area and make sure it's visible
        self.ui_callback.clear()
        self.ui_callback.show()
        self.ui_callback.append(f"Starting Last.fm synchronization for user {self.lastfm_username}...\n")
        QApplication.processEvents()  # Update UI

        try:
            # First try direct API import
            import_url = f"{self.base_url}/import/{self.muspy_id}"
            auth = (self.muspy_username, self.muspy_id)
            
            import_data = {
                'type': 'lastfm',
                'username': self.lastfm_username,
                'count': 50,  # Import more artists
                'period': 'overall'
            }
            
            self.ui_callback.append("Sending request to Muspy API...")
            QApplication.processEvents()
            
            # Use POST for the import endpoint
            response = requests.post(import_url, auth=auth, json=import_data)
            
            if response.status_code in [200, 201]:
                self.ui_callback.append(f"Successfully synchronized artists from Last.fm account {self.lastfm_username}")
                self.ui_callback.append("You can now view your upcoming releases using the 'Mis próximos discos' button")
                return True
            else:
                # If direct API fails, try using our LastFM manager as fallback
                self.ui_callback.append("Direct API import failed. Trying alternative method...")
                return self.sync_top_artists_from_lastfm()
        except Exception as e:
            error_msg = f"Error syncing with Muspy API: {e}"
            self.ui_callback.append(error_msg)
            self.logger.error(error_msg, exc_info=True)
            
            # Try alternative method
            self.ui_callback.append("Trying alternative synchronization method...")
            return self.sync_top_artists_from_lastfm()



    def sync_lastfm_custom_count(self):
        """
        Show a dialog to let the user input a custom number of artists to sync
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "Last.fm username not configured")
            return
            
        # Create the input dialog
        from PyQt6.QtWidgets import QInputDialog
        
        count, ok = QInputDialog.getInt(
            self,
            "Sync Last.fm Artists",
            "Enter number of top artists to sync:",
            value=50,
            min=1,
            max=1000,
            step=10
        )
        
        if ok:
            # User clicked OK, proceed with the sync
            self.sync_top_artists_from_lastfm(count)

    
    def load_lastfm_settings(self, kwargs):
        """Load Last.fm settings from configuration"""
        try:
            # Initialize with default values
            self.lastfm_api_key = None
            self.lastfm_api_secret = None
            self.lastfm_username = None
            
            # First try direct parameters that could be passed to the constructor
            if 'lastfm_api_key' in kwargs and kwargs['lastfm_api_key']:
                self.lastfm_api_key = kwargs['lastfm_api_key']
                    
            if 'lastfm_username' in kwargs and kwargs['lastfm_username']:
                self.lastfm_username = kwargs['lastfm_username']
                    
            # Then try lastfm section
            lastfm_section = kwargs.get('lastfm', {})
            if lastfm_section:
                if not self.lastfm_api_key and 'api_key' in lastfm_section:
                    self.lastfm_api_key = lastfm_section['api_key']
                        
                if not self.lastfm_api_secret and 'api_secret' in lastfm_section:
                    self.lastfm_api_secret = lastfm_section['api_secret']
                        
                if not self.lastfm_username and 'username' in lastfm_section:
                    self.lastfm_username = lastfm_section['username']
                
            # Finally try from global_theme_config
            global_config = kwargs.get('global_theme_config', {})
            if global_config:
                if not self.lastfm_api_key and 'lastfm_api_key' in global_config:
                    self.lastfm_api_key = global_config['lastfm_api_key']
                        
                if not self.lastfm_api_secret and 'lastfm_api_secret' in global_config:
                    self.lastfm_api_secret = global_config['lastfm_api_secret']
                        
                if not self.lastfm_username and 'lastfm_username' in global_config:
                    self.lastfm_username = global_config['lastfm_username']
                
            # Determine if Last.fm is enabled - SOLO basándonos en username como pediste
            self.lastfm_enabled = bool(self.lastfm_username and self.lastfm_api_key)
                
            # Log the configuration
            if self.lastfm_enabled:
                print(f"LastFM configurado para el usuario: {self.lastfm_username}")
            else:
                missing = []
                if not self.lastfm_api_key:
                    missing.append("API key")
                if not self.lastfm_username:
                    missing.append("username")
                print(f"LastFM no está completamente configurado - falta: {', '.join(missing)}")
                    
        except Exception as e:
            print(f"Error cargando configuración de LastFM: {e}")
            self.lastfm_enabled = False

