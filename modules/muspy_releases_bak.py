import sys
import os
import json
from pathlib import Path
import subprocess
import requests
import logging
import datetime
from PyQt6 import uic
try:
    from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
                                QLabel, QLineEdit, QMessageBox, QApplication, QFileDialog, QTableWidget, 
                                QTableWidgetItem, QHeaderView, QDialog, QCheckBox, QScrollArea, QDialogButtonBox,
                                QMenu, QInputDialog, QTreeWidget, QTreeWidgetItem, QProgressDialog, QSizePolicy,
                                QStackedWidget, QSpinBox, QComboBox, QAbstractItemView)
    from PyQt6.QtCore import pyqtSignal, Qt, QPoint, QObject, QThread, QSize, QEvent
    from PyQt6.QtGui import QColor, QTextDocument, QAction, QCursor, QTextCursor, QIcon, QShortcut, QKeySequence
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("PyQt6 not available. UI functionality will be limited.")

# Set up a basic logger before any imports that might use it
logger = logging.getLogger("MuspyArtistModule")

# Configure path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule, THEMES, PROJECT_ROOT        # BaseModule
from tools.musicbrainz_login import MusicBrainzAuthManager      # Musicbrainz
from tools.bluesky_manager import BlueskyManager                # Bluesky


# Try to import specific modules that might not be available
try:
    from spotipy.oauth2 import SpotifyOAuth
    from tools.spotify_login import SpotifyAuthManager
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False
    logger.warning("Spotipy/Spotify modules not available. Spotify features will be disabled.")

try:
    from tools.lastfm_login import LastFMAuthManager
    LASTFM_AVAILABLE = True
except ImportError:
    LASTFM_AVAILABLE = False
    logger.warning("LastFM module not available. LastFM features will be disabled.")



# CLASES AUXILIARES

# Filter PyQt logs
class PyQtFilter(logging.Filter):
    def filter(self, record):
        # Filter PyQt messages
        if record.name.startswith('PyQt6'):
            return False
        return True

# Apply the filter to the global logger
logging.getLogger().addFilter(PyQtFilter())

# Try to set up better logging if available
try:
    from loggin_helper import setup_module_logger
    logger = setup_module_logger(
        module_name="MuspyArtistModule",
        log_level="INFO",
        log_types=["ERROR", "INFO", "WARNING", "UI"]
    )
except ImportError:
    # Fallback to standard logging if specialized logger isn't available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MuspyArtistModule")



        

# LA MANDANGA

class MuspyArtistModule(BaseModule):
    def __init__(self, 
            muspy_username=None, 
            muspy_api_key=None,
            muspy_password=None,
            muspy_id=None,
            artists_file=None,
            query_db_script_path=None,
            search_mbid_script_path=None,
            lastfm_username=None,
            lastfm_api_key=None,
            lastfm_api_secret=None,
            spotify_client_id=None,
            spotify_client_secret=None,
            spotify_redirect_uri=None,
            musicbrainz_username=None,
            musicbrainz_password=None,
            bluesky_username=None,
            parent=None, 
            db_path='music_database.db',
            theme='Tokyo Night', 
            *args, **kwargs):
        """
        Initialize the Muspy Artist Management Module
        """
        # Logging configuration
        self.module_name = self.__class__.__name__
        self.log_config = kwargs.get('logging', {})
        self.log_level = self.log_config.get('log_level', 'INFO')
        self.enable_logging = self.log_config.get('debug_enabled', False)
        self.log_types = self.log_config.get('log_types', ['ERROR', 'INFO'])
        
        # Basic properties
        self.muspy_username = muspy_username
        self.muspy_password = muspy_password
        self.muspy_api_key = muspy_api_key
        self.muspy_id = muspy_id
        self.base_url = "https://muspy.com/api/1"
        self.artists_file = artists_file
        self.query_db_script_path = query_db_script_path
        self.db_path = db_path
        self.spotify_redirect_uri = spotify_redirect_uri
        self.follow_artist_auth_method = "tuple"  # Default authentication method (can be "tuple", "basic", or "manual")    
        # Initialize credentials
        self.spotify_client_id = spotify_client_id
        self.spotify_client_secret = spotify_client_secret
        self.lastfm_api_key = lastfm_api_key
        self.lastfm_api_secret = lastfm_api_secret
        self.lastfm_username = lastfm_username
        
        self.bluesky_username = bluesky_username
        
        # Set up a basic logger early so it's available before super().__init__()
        self.logger = logging.getLogger(self.module_name)

        # Initialize MusicBrainz credentials from all possible sources
        self.musicbrainz_username = kwargs.get('musicbrainz_username')
        self.musicbrainz_password = kwargs.get('musicbrainz_password')

        # Check global theme config for credentials if not already set
        global_config = kwargs.get('global_theme_config', {})
        if global_config:
            if not self.musicbrainz_username and 'musicbrainz_username' in global_config:
                self.musicbrainz_username = global_config['musicbrainz_username']
            if not self.musicbrainz_password and 'musicbrainz_password' in global_config:
                self.musicbrainz_password = global_config['musicbrainz_password']

        self.musicbrainz_enabled = bool(self.musicbrainz_username)

        # Debug log for troubleshooting
        if self.musicbrainz_username:
            self.logger.info(f"MusicBrainz username configured: {self.musicbrainz_username}")
            self.logger.info(f"MusicBrainz password configured: {bool(self.musicbrainz_password)}")
        else:
            self.logger.warning("MusicBrainz username not configured")

        # Initialize MusicBrainz auth manager
        if self.musicbrainz_enabled:
            try:
                from tools.musicbrainz_login import MusicBrainzAuthManager
                self.musicbrainz_auth = MusicBrainzAuthManager(
                    username=self.musicbrainz_username,
                    password=self.musicbrainz_password,
                    parent_widget=self,
                    project_root=PROJECT_ROOT
                )
                self.logger.info(f"MusicBrainz auth manager initialized for user: {self.musicbrainz_username}")
            except Exception as e:
                self.logger.error(f"Error initializing MusicBrainz auth manager: {e}", exc_info=True)
                self.musicbrainz_enabled = False

        # IMPORTANTE: Inicializar lastfm_enabled y spotify_enabled ANTES de llamar a super().__init__()
        # Determinar si Last.fm está habilitado (ahora basado en username como solicitaste)
        self.lastfm_enabled = bool(self.lastfm_username and self.lastfm_api_key)
        
        # Determinar si Spotify está habilitado
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        
        # Initialize Spotify auth manager if credentials are available
        if self.spotify_enabled:
            try:
                self.spotify_auth = SpotifyAuthManager(
                    client_id=self.spotify_client_id,
                    client_secret=self.spotify_client_secret,
                    redirect_uri=self.spotify_redirect_uri,
                    parent_widget=self,
                    project_root=PROJECT_ROOT
                )
                self.logger.info(f"Spotify auth manager initialized")
            except Exception as e:
                self.logger.error(f"Error initializing Spotify auth manager: {e}", exc_info=True)
                self.spotify_enabled = False



        # Theme configuration
        self.available_themes = kwargs.pop('temas', [])
        self.selected_theme = kwargs.pop('tema_seleccionado', theme)
        

        
        # Debug print to see what's coming in from config
        print(f"DEBUG - Last.fm config: api_key={lastfm_api_key}, username={lastfm_username}, enabled={self.lastfm_enabled}")
        
        # Call super init now that we've set up the required attributes
        super().__init__(parent, theme, **kwargs)
        
        # Set up logger
        if self.enable_logging:
            try:
                from loggin_helper import setup_module_logger
                self.logger = setup_module_logger(
                    module_name=self.module_name,
                    log_level=self.log_level,
                    log_types=self.log_types
                )
            except ImportError:
                self.logger = logger
        else:
            self.logger = logger
        
        # Initialize the Last.fm auth if enabled
        if self.lastfm_enabled:
            try:
                from tools.lastfm_login import LastFMAuthManager
                
                self.logger.info(f"Initializing LastFM auth with: api_key={self.lastfm_api_key}, username={self.lastfm_username}")
                
                self.lastfm_auth = LastFMAuthManager(
                    api_key=self.lastfm_api_key,
                    api_secret=self.lastfm_api_secret,
                    username=self.lastfm_username,
                    parent_widget=self,
                    project_root=PROJECT_ROOT
                )
                self.logger.info(f"LastFM auth manager initialized for user: {self.lastfm_username}")
            except Exception as e:
                self.logger.error(f"Error initializing LastFM auth manager: {e}", exc_info=True)
                self.lastfm_enabled = False
        

   # Actualización del método init_ui en la clase MuspyArtistModule
   


    # def previous_page(self):
    #     """Navigate to the previous page in the stacked widget"""
    #     if hasattr(self, 'stackedWidget') and self.stackedWidget.count() > 0:
    #         current = self.stackedWidget.currentIndex()
    #         if current > 0:
    #             self.stackedWidget.setCurrentIndex(current - 1)
    #         else:
    #             # Wrap around to the last page
    #             self.stackedWidget.setCurrentIndex(self.stackedWidget.count() - 1)

    # def next_page(self):
    #     """Navigate to the next page in the stacked widget"""
    #     if hasattr(self, 'stackedWidget') and self.stackedWidget.count() > 0:
    #         current = self.stackedWidget.currentIndex()
    #         if current < self.stackedWidget.count() - 1:
    #             self.stackedWidget.setCurrentIndex(current + 1)
    #         else:
    #             # Wrap around to the first page
    #             self.stackedWidget.setCurrentIndex(0)






    # def _display_loved_tracks_table(self, loved_tracks):
    #     """
    #     Display loved tracks in a table
        
    #     Args:
    #         loved_tracks (list): List of loved track objects from Last.fm
    #     """
    #     # Look for the stacked widget
    #     stack_widget = self.findChild(QStackedWidget, "stackedWidget")
    #     if stack_widget is None:
    #         # Fallback to old display method
    #         self.results_text.clear()
    #         self.results_text.show()
    #         self.results_text.append(f"Found {len(loved_tracks)} loved tracks for {self.lastfm_username}")
    #         for i, track in enumerate(loved_tracks):
    #             self.results_text.append(f"{i+1}. {track.track.artist.name} - {track.track.title}")
    #         return
            
    #     # Find the loved tracks page in the stacked widget
    #     loved_tracks_page = None
    #     for i in range(stack_widget.count()):
    #         page = stack_widget.widget(i)
    #         if page.objectName() == "loved_tracks_page":
    #             loved_tracks_page = page
    #             break
                
    #     if loved_tracks_page is None:
    #         # Fallback to old display
    #         self.results_text.append("Loved tracks page not found in stacked widget")
    #         return
        
    #     # Get the table from the page
    #     table = loved_tracks_page.findChild(QTableWidget, "loved_tracks_table")
    #     if table is None:
    #         self.results_text.append("Loved tracks table not found in page")
    #         return
            
    #     # Get count label
    #     count_label = loved_tracks_page.findChild(QLabel, "count_label")
    #     if count_label:
    #         count_label.setText(f"Showing {len(loved_tracks)} loved tracks for {self.lastfm_username}")
        
    #     # Configure table
    #     table.setSortingEnabled(False)  # Disable sorting while updating
    #     table.setRowCount(len(loved_tracks))
        
    #     # Fill table
    #     for i, track in enumerate(loved_tracks):
    #         # Artist
    #         artist_name = track.track.artist.name
    #         artist_item = QTableWidgetItem(artist_name)
    #         table.setItem(i, 0, artist_item)
            
    #         # Track name
    #         track_name = track.track.title
    #         track_item = QTableWidgetItem(track_name)
    #         table.setItem(i, 1, track_item)
            
    #         # Album - may not be available in all cases
    #         album_name = ""
    #         try:
    #             album_name = track.track.get_album().title if track.track.get_album() else ""
    #         except:
    #             pass
    #         album_item = QTableWidgetItem(album_name)
    #         table.setItem(i, 2, album_item)
            
    #         # Date loved - may need conversion
    #         date_str = ""
    #         if hasattr(track, 'date'):
    #             try:
    #                 # Convert timestamp to readable format
    #                 import datetime
    #                 date_obj = datetime.datetime.fromtimestamp(int(track.date))
    #                 date_str = date_obj.strftime('%Y-%m-%d %H:%M')
    #             except:
    #                 date_str = str(track.date)
    #         date_item = QTableWidgetItem(date_str)
    #         table.setItem(i, 3, date_item)
            
    #         # Actions - using a button
    #         actions_widget = QWidget()
    #         actions_layout = QHBoxLayout(actions_widget)
    #         actions_layout.setContentsMargins(2, 2, 2, 2)
            
    #         # Unlove button
    #         unlove_button = QPushButton("Unlove")
    #         unlove_button.setProperty("track_index", i)
    #         unlove_button.clicked.connect(lambda checked, idx=i: self.unlove_track_from_table(idx))
    #         actions_layout.addWidget(unlove_button)
            
    #         # Follow artist button
    #         follow_button = QPushButton("Follow Artist")
    #         follow_button.setProperty("artist_name", artist_name)
    #         follow_button.clicked.connect(lambda checked, a=artist_name: self.add_lastfm_artist_to_muspy(a))
    #         actions_layout.addWidget(follow_button)
            
    #         table.setCellWidget(i, 4, actions_widget)
        
    #     # Re-enable sorting
    #     table.setSortingEnabled(True)
        
    #     # Switch to the loved tracks page
    #     stack_widget.setCurrentWidget(loved_tracks_page)
        
    #     # Hide results text if visible
    #     if hasattr(self, 'results_text') and self.results_text.isVisible():
    #         self.results_text.hide()

    # def unlove_track_from_table(self, track_index):
    #     """
    #     Unlove a track directly from the table
        
    #     Args:
    #         track_index (int): Index of the track in the loved_tracks_list
    #     """
    #     if not hasattr(self, 'loved_tracks_list') or track_index >= len(self.loved_tracks_list):
    #         QMessageBox.warning(self, "Error", "Track information not available")
    #         return
        
    #     loved_track = self.loved_tracks_list[track_index]
    #     track = loved_track.track
        
    #     # Confirm with user
    #     reply = QMessageBox.question(
    #         self,
    #         "Confirm Unlove",
    #         f"Remove '{track.title}' by {track.artist.name} from your loved tracks?",
    #         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    #     )
        
    #     if reply == QMessageBox.StandardButton.Yes:
    #         try:
    #             # Check if authentication is needed
    #             if not self.lastfm_auth.is_authenticated():
    #                 # Need to authenticate for write operations
    #                 auth_reply = QMessageBox.question(
    #                     self,
    #                     "Authentication Required",
    #                     "To remove a track from your loved tracks, you need to authenticate with Last.fm. Proceed?",
    #                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    #                 )
                    
    #                 if auth_reply == QMessageBox.StandardButton.Yes:
    #                     # Prompt for password
    #                     password, ok = QInputDialog.getText(
    #                         self,
    #                         "Last.fm Password",
    #                         f"Enter password for {self.lastfm_username}:",
    #                         QLineEdit.EchoMode.Password
    #                     )
                        
    #                     if ok and password:
    #                         # Try to authenticate
    #                         self.lastfm_auth.password = password
    #                         if not self.lastfm_auth.authenticate():
    #                             QMessageBox.warning(self, "Authentication Failed", "Could not authenticate with Last.fm")
    #                             return
    #                     else:
    #                         return  # Canceled
    #                 else:
    #                     return  # Declined authentication
                
    #             # Get the authenticated network
    #             network = self.lastfm_auth.get_network()
    #             if not network:
    #                 QMessageBox.warning(self, "Error", "Could not connect to Last.fm")
    #                 return
                    
    #             # Unlove the track
    #             track.unlove()
                
    #             # Show success message
    #             QMessageBox.information(self, "Success", "Track removed from loved tracks")
                
    #             # Refresh the list
    #             self.show_lastfm_loved_tracks()
                
    #         except Exception as e:
    #             error_msg = f"Error removing track from loved tracks: {e}"
    #             QMessageBox.warning(self, "Error", error_msg)
    #             self.logger.error(error_msg, exc_info=True)

   



    
    # def get_muspy_id(self):
    #     """
    #     Returns the Muspy ID, using the one from config and only fetching if not available
        
    #     Returns:
    #         str: ID de usuario de Muspy
    #     """
    #     # If we already have an ID, use it
    #     if self.muspy_id:
    #         self.logger.debug(f"Using existing Muspy ID: {self.muspy_id}")
    #         return self.muspy_id
            
    #     # If not available and we have credentials, try to fetch it once
    #     if not self.muspy_id and self.muspy_username and self.muspy_api_key:
    #         try:
    #             self.logger.info("No Muspy ID in config, attempting to fetch from API")
    #             # Using the /user endpoint to get user info
    #             url = f"{self.base_url}/user"
    #             auth = (self.muspy_username, self.muspy_api_key)
                
    #             response = requests.get(url, auth=auth)
                
    #             if response.status_code == 200:
    #                 # Try to parse user_id from response
    #                 user_data = response.json()
    #                 if 'userid' in user_data:
    #                     self.muspy_id = user_data['userid']
    #                     self.logger.info(f"Muspy ID obtained: {self.muspy_id}")
    #                     return self.muspy_id
    #                 else:
    #                     self.logger.error(f"No 'userid' in response JSON: {user_data}")
    #             else:
    #                 self.logger.error(f"Error calling Muspy API: {response.status_code} - {response.text}")
    #         except Exception as e:
    #             self.logger.error(f"Error getting Muspy ID: {e}", exc_info=True)
        
    #     # If we still don't have an ID, log the error
    #     if not self.muspy_id:
    #         self.logger.error("No valid Muspy ID available. Please set it in configuration.")
        
    #     return self.muspy_id

  


# Menú sincronización
    
  

# Musicbrainz
   


# MENU CONTEXTUAL TABLAS:




  




  
