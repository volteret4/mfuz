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
                                QStackedWidget, QSpinBox, QComboBox)
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
from base_module import BaseModule, THEMES, PROJECT_ROOT

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

# Musicbrainz
from tools.musicbrainz_login import MusicBrainzAuthManager

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


class NumericTableWidgetItem(QTableWidgetItem):
    """A QTableWidgetItem that sorts numerically"""
    
    def __lt__(self, other):
        try:
            # Convert both items to numbers for comparison
            return float(self.text().replace(',', '')) < float(other.text().replace(',', ''))
        except (ValueError, TypeError):
            # Fall back to default string comparison if numeric conversion fails
            return super().__lt__(other)


class ProgressWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    status_update = pyqtSignal(str)
    
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            result = self.function(
                progress_callback=self.progress.emit, 
                status_callback=self.status_update.emit,
                *self.args, 
                **self.kwargs
            )
            self.finished.emit(result)
        except Exception as e:
            self.status_update.emit(f"Error: {str(e)}")
            self.finished.emit([])


class AuthWorker(QObject):
    finished = pyqtSignal(bool)
    
    def __init__(self, auth_manager, username, password):
        super().__init__()
        self.auth_manager = auth_manager
        self.username = username
        self.password = password
    
    def authenticate(self):
        success = False
        try:
            # Actualizar credenciales
            self.auth_manager.username = self.username
            self.auth_manager.password = self.password
            
            # Intentar autenticar
            success = self.auth_manager.authenticate()
        except Exception as e:
            print(f"Error en autenticación en segundo plano: {e}")
        
        # Emitir señal cuando termine
        self.finished.emit(success)


class FloatingNavigationButtons(QObject):
    """
    Class to manage floating navigation buttons for a stacked widget.
    The buttons appear when mouse hovers over the left/right edge of the widget.
    """
    def __init__(self, stacked_widget, parent=None):
        super().__init__(parent)
        self.stacked_widget = stacked_widget
        self.parent_widget = parent if parent else stacked_widget.parent()
        
        # Create buttons
        self.prev_button = QPushButton(self.parent_widget)
        self.next_button = QPushButton(self.parent_widget)
        
        # Configure buttons
        self.setup_buttons()
        
        # Set up event filter for mouse tracking
        self.stacked_widget.setMouseTracking(True)
        self.stacked_widget.installEventFilter(self)
        
        # Hide buttons initially
        self.prev_button.hide()
        self.next_button.hide()
        
        # Connect signals
        self.connect_signals()
        
        # Track active areas
        self.left_active = False
        self.right_active = False
        
    def setup_buttons(self):
        """Set up button appearance and positioning"""
        # Set fixed size
        button_size = 40
        self.prev_button.setFixedSize(button_size, button_size)
        self.next_button.setFixedSize(button_size, button_size)
        
        # Set icons - use predefined icons from theme if available
        self.prev_button.setText("←")  # Fallback to text
        self.next_button.setText("→")  # Fallback to text
        
        try:
            self.prev_button.setIcon(QIcon.fromTheme("go-previous"))
            self.next_button.setIcon(QIcon.fromTheme("go-next"))
            # Set icon size
            icon_size = int(button_size * 0.7)
            self.prev_button.setIconSize(QSize(icon_size, icon_size))
            self.next_button.setIconSize(QSize(icon_size, icon_size))
        except:
            # Fallback to text if icons not available
            pass
        
        # Set style
        button_style = """
            QPushButton {
                background-color: rgba(66, 133, 244, 0.8);
                border-radius: 20px;
                color: white;
                border: none;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(82, 148, 255, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(58, 118, 216, 0.9);
            }
        """
        self.prev_button.setStyleSheet(button_style)
        self.next_button.setStyleSheet(button_style)
        
        # Add drop shadow effect for better visibility
        try:
            from PyQt6.QtWidgets import QGraphicsDropShadowEffect
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setColor(QColor(0, 0, 0, 160))
            shadow.setOffset(0, 0)
            self.prev_button.setGraphicsEffect(shadow)
            
            shadow2 = QGraphicsDropShadowEffect()
            shadow2.setBlurRadius(10)
            shadow2.setColor(QColor(0, 0, 0, 160))
            shadow2.setOffset(0, 0)
            self.next_button.setGraphicsEffect(shadow2)
        except:
            # Skip shadow effect if not available
            pass
        
        # Position the buttons
        self.update_button_positions()
        
    def update_button_positions(self):
        """Update the position of navigation buttons based on stacked widget size"""
        if not self.stacked_widget:
            return
            
        # Get the size of the stacked widget
        widget_rect = self.stacked_widget.rect()
        widget_height = widget_rect.height()
        
        # Position buttons vertically centered, on the edges
        y_position = (widget_height - self.prev_button.height()) // 2
        
        # Position the previous button on the left edge
        self.prev_button.move(10, y_position)
        
        # Position the next button on the right edge
        self.next_button.move(
            self.stacked_widget.width() - self.next_button.width() - 10, 
            y_position
        )
        
    def connect_signals(self):
        """Connect button signals to navigation functions"""
        self.prev_button.clicked.connect(self.go_to_previous_page)
        self.next_button.clicked.connect(self.go_to_next_page)
        
        # Connect to parent resize for repositioning
        if self.parent_widget:
            self.parent_widget.resizeEvent = self.handle_parent_resize
        
    def handle_parent_resize(self, event):
        """Handle parent resize event to update button positions"""
        self.update_button_positions()
        
        # Call original resize event if it exists
        original_resize = getattr(self.parent_widget.__class__, "resizeEvent", None)
        if original_resize and original_resize != self.handle_parent_resize:
            original_resize(self.parent_widget, event)
    
    def go_to_previous_page(self):
        """Navigate to the previous page in the stacked widget"""
        current_index = self.stacked_widget.currentIndex()
        if current_index > 0:
            self.stacked_widget.setCurrentIndex(current_index - 1)
        else:
            # Wrap around to the last page
            self.stacked_widget.setCurrentIndex(self.stacked_widget.count() - 1)
            
    def go_to_next_page(self):
        """Navigate to the next page in the stacked widget"""
        current_index = self.stacked_widget.currentIndex()
        if current_index < self.stacked_widget.count() - 1:
            self.stacked_widget.setCurrentIndex(current_index + 1)
        else:
            # Wrap around to the first page
            self.stacked_widget.setCurrentIndex(0)
    
    def eventFilter(self, obj, event):
        """Filter events to detect mouse hover on edges"""
        if obj == self.stacked_widget:
            if event.type() == QEvent.Type.Enter:
                # Mouse entered widget, show buttons if near edges
                # Fix: QEnterEvent uses position() not pos()
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                self.check_mouse_position(pos)
                
            elif event.type() == QEvent.Type.Leave:
                # Mouse left widget, hide buttons
                self.prev_button.hide()
                self.next_button.hide()
                self.left_active = False
                self.right_active = False
                
            elif event.type() == QEvent.Type.MouseMove:
                # Mouse moved inside widget, check position
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                self.check_mouse_position(pos)
        
        # Let the event continue to be processed
        return super().eventFilter(obj, event)
    
    def check_mouse_position(self, pos):
        """Check if mouse is near left or right edge and show appropriate button"""
        # Define edge sensitivity (px from edge)
        edge_sensitivity = 50
        
        # Check left edge
        if pos.x() <= edge_sensitivity:
            if not self.left_active:
                self.prev_button.show()
                self.left_active = True
        else:
            if self.left_active:
                self.prev_button.hide()
                self.left_active = False
        
        # Check right edge
        if pos.x() >= (self.stacked_widget.width() - edge_sensitivity):
            if not self.right_active:
                self.next_button.show()
                self.right_active = True
        else:
            if self.right_active:
                self.next_button.hide()
                self.right_active = False


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
    def init_ui(self):
        """Initialize the user interface for Muspy artist management"""
        # Lista de widgets requeridos
        required_widgets = [
            'artist_input', 'search_button', 
            'load_artists_button', 'sync_artists_button', 
            'get_releases_button', 'get_new_releases_button', 'get_my_releases_button',
            'stackedWidget', 'tabla_musicbrainz_collection'  # Added the table to required widgets
        ]
        
        # Intentar cargar desde archivo UI
        ui_file_path = os.path.join(PROJECT_ROOT, "ui", "muspy_releases_module.ui")
        
        if os.path.exists(ui_file_path):
            try:
                # Cargar el archivo UI
                uic.loadUi(ui_file_path, self)
                
                # Log UI loading success
                self.logger.info(f"UI loaded from {ui_file_path}")
                
                # Debug: List all widgets to identify what's available
                self.logger.debug("Listing all widgets after UI load:")
                for widget in self.findChildren(QWidget):
                    self.logger.debug(f"  - {widget.objectName()} : {type(widget).__name__}")
                
                # Look specifically for stacked widget pages
                if hasattr(self, 'stackedWidget'):
                    self.logger.debug(f"StackedWidget has {self.stackedWidget.count()} pages:")
                    for i in range(self.stackedWidget.count()):
                        page = self.stackedWidget.widget(i)
                        self.logger.debug(f"  - Page {i} objectName: {page.objectName()}")
                        # Check for the table in each page
                        table = page.findChild(QTableWidget, "tabla_musicbrainz_collection")
                        if table:
                            self.logger.debug(f"    Found tabla_musicbrainz_collection in page {i}")
                
                # Verificar que se han cargado los widgets principales
                missing_widgets = []
                for widget_name in required_widgets:
                    if not hasattr(self, widget_name) or getattr(self, widget_name) is None:
                        widget = self.findChild(QWidget, widget_name)
                        if widget:
                            setattr(self, widget_name, widget)
                            self.logger.debug(f"Found and set widget: {widget_name}")
                        else:
                            missing_widgets.append(widget_name)
                            self.logger.warning(f"Widget not found: {widget_name}")
                
                if missing_widgets:
                    self.logger.error(f"Widgets not found in UI: {', '.join(missing_widgets)}")
                    raise AttributeError(f"Widgets not found in UI: {', '.join(missing_widgets)}")
                
                # Do NOT replace the stacked widget pages if they're already there
                # Instead, augment them if needed
                self._setup_stacked_widget(respect_existing=True)
                
                # Add floating navigation to stacked widget
                self.floating_nav = FloatingNavigationButtons(self.stackedWidget, self)
                
                # Set initial welcome text
                self.results_text.setHtml("""
                <!DOCTYPE HTML>
                <html><head><style>
                body { text-align: center; margin-top: 20px; }
                h2 { color: #7aa2f7; }
                ul { text-align: left; max-width: 600px; margin: 0 auto; }
                li { margin-bottom: 10px; }
                </style></head><body>
                <h2>Muspy Artist Module</h2>
                <p>Welcome to the Muspy Artist Module. This tool lets you:</p>
                <ul>
                    <li>Follow artists on Muspy to track upcoming releases</li>
                    <li>View upcoming releases from your favorite artists</li>
                    <li>Sync with Last.fm to follow your most played artists</li>
                    <li>Search for specific artist releases</li>
                </ul>
                <p>Use the buttons at the bottom to get started.</p>
                </body></html>
                """)
                
                # Make sure we start with the text page visible
                self.stackedWidget.setCurrentIndex(0)
                

                self.setup_table_context_menus()
                
                # Connect signals
                self._connect_signals()
                
                # Intentar autenticación silenciosa con MusicBrainz al iniciar
                if hasattr(self, 'musicbrainz_username') and self.musicbrainz_username and hasattr(self, 'musicbrainz_password') and self.musicbrainz_password:
                    self.logger.info("Intentando autenticación automática con MusicBrainz...")
                    self._start_background_auth()
                   
                
                print(f"UI MuspyArtistModule cargada desde {ui_file_path}")
            except Exception as e:
                print(f"Error cargando UI MuspyArtistModule desde archivo: {e}")
                import traceback
                print(traceback.format_exc())
                self._fallback_init_ui()
        else:
            print(f"Archivo UI MuspyArtistModule no encontrado: {ui_file_path}, usando creación manual")
            self._fallback_init_ui()


    def _setup_stacked_widget(self, respect_existing=True):
        """Set up the stacked widget references without creating new pages"""
        # Check if stacked widget exists
        if not hasattr(self, 'stackedWidget'):
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Log what's in the stacked widget for debugging
        self.logger.info(f"StackedWidget has {self.stackedWidget.count()} pages")
        for i in range(self.stackedWidget.count()):
            page = self.stackedWidget.widget(i)
            self.logger.info(f"Page {i}: {page.objectName()}")
            
            # If we find the musicbrainz_collection_page, check for the table
            if page.objectName() == "musicbrainz_collection_page":
                table = page.findChild(QTableWidget, "tabla_musicbrainz_collection")
                if table:
                    self.logger.info("Found tabla_musicbrainz_collection in musicbrainz_collection_page")
                else:
                    self.logger.warning("tabla_musicbrainz_collection NOT found in musicbrainz_collection_page")
        
        # We're NOT creating any new pages - all should be defined in the UI file


    def display_lastfm_artists_in_stacked_widget(self, artists):
        """
        Display Last.fm artists in the artists page of the stacked widget
        
        Args:
            artists (list): List of artist dictionaries from Last.fm
        """
        # Find the stacked widget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            # Fallback if stacked widget not found
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the artists page
        artists_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "artists_page":
                artists_page = widget
                break
        
        if not artists_page:
            self.logger.error("Artists page not found in stacked widget")
            return
        
        # Get the table widget and count label
        table = artists_page.findChild(QTableWidget, "artists_table")
        count_label = artists_page.findChild(QLabel, "artists_count_label")
        
        if not table:
            self.logger.error("Artists table not found in artists page")
            return
        
        # Update count label
        if count_label:
            count_label.setText(f"Showing {len(artists)} top artists for {self.lastfm_username}")
        
        # Configure table to include new columns - make sure we have 5 columns now
        table.setColumnCount(5)  # Update column count to include listeners and URL
        table.setHorizontalHeaderLabels(["Artist", "Playcount", "Listeners", "URL", "Actions"])
        
        # Configure table
        table.setRowCount(len(artists))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill table with artist data
        for i, artist in enumerate(artists):
            artist_name = artist.get('name', '')
            playcount = str(artist.get('playcount', 'N/A'))
            listeners = str(artist.get('listeners', 'N/A'))
            url = artist.get('url', '')
            
            # Artist name
            name_item = QTableWidgetItem(artist_name)
            table.setItem(i, 0, name_item)
            
            # Playcount - with numeric sorting capability
            playcount_item = NumericTableWidgetItem(playcount)
            playcount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 1, playcount_item)
            
            # Listeners - with numeric sorting capability
            listeners_item = NumericTableWidgetItem(listeners)
            listeners_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 2, listeners_item)
            
            # URL - add the Last.fm URL
            url_item = QTableWidgetItem(url)
            table.setItem(i, 3, url_item)
            
            # Actions - create a widget with buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)
            
            # Add "Follow" button
            follow_button = QPushButton("Follow")
            follow_button.setProperty("artist_name", artist_name)
            follow_button.setMaximumWidth(80)
            follow_button.clicked.connect(lambda checked, a=artist_name: self.add_lastfm_artist_to_muspy(a))
            actions_layout.addWidget(follow_button)
            
            # Store URL and MBID in the item data for context menu use
            if url:
                name_item.setData(Qt.ItemDataRole.UserRole, {'url': url, 'mbid': artist.get('mbid', '')})
            
            table.setCellWidget(i, 4, actions_widget)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
        
        # Resize columns to fit content
        table.resizeColumnsToContents()
        
        
        # Configure context menu for the table
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_unified_context_menu)
        
        # Switch to the artists page
        stack_widget.setCurrentWidget(artists_page)

    def display_loved_tracks_in_stacked_widget(self, loved_tracks):
        """
        Display loved tracks in the loved tracks page of the stacked widget
        
        Args:
            loved_tracks (list): List of loved track objects from Last.fm or cached dictionaries
        """
        # Find the stacked widget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the loved tracks page
        loved_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "loved_tracks_page":
                loved_page = widget
                break
        
        if not loved_page:
            self.logger.error("Loved tracks page not found in stacked widget")
            return
        
        # Get the table and count label
        table = loved_page.findChild(QTableWidget, "loved_tracks_table")
        count_label = loved_page.findChild(QLabel, "loved_count_label")
        
        if not table:
            self.logger.error("Loved tracks table not found in loved tracks page")
            return
        
        # Update count label
        if count_label:
            count_label.setText(f"Showing {len(loved_tracks)} loved tracks for {self.lastfm_username}")
        
        # Configure table
        table.setRowCount(len(loved_tracks))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table with data
        for i, loved_track in enumerate(loved_tracks):
            # Check if this is a pylast object or dictionary from cache
            if hasattr(loved_track, 'track'):
                # Extract data from pylast objects
                track = loved_track.track
                artist_name = track.artist.name
                track_name = track.title
                
                # Get album if available
                album_name = ""
                try:
                    album = track.get_album()
                    if album:
                        album_name = album.title
                except:
                    pass
                    
                # Get date if available
                date_text = ""
                if hasattr(loved_track, "date") and loved_track.date:
                    try:
                        import datetime
                        date_obj = datetime.datetime.fromtimestamp(int(loved_track.date))
                        date_text = date_obj.strftime("%Y-%m-%d")
                    except:
                        date_text = str(loved_track.date)
            else:
                # This is a dictionary from cache
                artist_name = loved_track.get('artist', '')
                track_name = loved_track.get('title', '')
                album_name = loved_track.get('album', '')
                
                # Format date
                date_value = loved_track.get('date')
                date_text = ""
                if date_value:
                    try:
                        import datetime
                        date_obj = datetime.datetime.fromtimestamp(int(date_value))
                        date_text = date_obj.strftime("%Y-%m-%d")
                    except:
                        date_text = str(date_value)
            
            # Set artist name column
            artist_item = QTableWidgetItem(artist_name)
            table.setItem(i, 0, artist_item)
            
            # Set track name column
            track_item = QTableWidgetItem(track_name)
            table.setItem(i, 1, track_item)
            
            # Set album column
            album_item = QTableWidgetItem(album_name)
            table.setItem(i, 2, album_item)
            
            # Date column
            date_item = QTableWidgetItem(date_text)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 3, date_item)
            
            # Actions column with buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)
            
            # Follow artist button
            follow_button = QPushButton("Follow Artist")
            follow_button.setMaximumWidth(90)
            follow_button.setProperty("artist_name", artist_name)
            follow_button.clicked.connect(lambda checked, a=artist_name: self.add_lastfm_artist_to_muspy(a))
            actions_layout.addWidget(follow_button)
            
            table.setCellWidget(i, 4, actions_widget)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
        
        # Switch to the loved tracks page
        stack_widget.setCurrentWidget(loved_page)



    def _fallback_init_ui(self):
        """Método de respaldo para crear la UI manualmente si el archivo UI falla."""
        # Main vertical layout
        main_layout = QVBoxLayout(self)

        # Top section with search
        top_layout = QHBoxLayout()
        
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Introduce el nombre de un artista para buscar discos anunciados")
        top_layout.addWidget(self.artist_input)

        self.search_button = QPushButton("Voy a tener suerte")
        top_layout.addWidget(self.search_button)

        main_layout.addLayout(top_layout)

        # Results area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.append("""
            \n\n\n\n
            Leer db: Mostrará una selección con los artistas a escoger para sincronizar con muspy
            Sincronizar artistas: Añadirá los artistas faltantes a Muspy
            Sincronizar Lastfm: Sincronizará artistas seguidos en lastfm en Muspy
            Mis Próximos discos: Buscará lanzamientos anunciados de tus artistas seguidos
            Discos ausentes: Comprobará qué discos de los artistas seleccionados no existe en tu base de datos
            Obtener todo: Obtiene TODO lo anunciado, serán decenas de miles...
            \n\n\n\n
            """)
        main_layout.addWidget(self.results_text)

        # Bottom buttons layout
        bottom_layout = QHBoxLayout()
        
        self.load_artists_button = QPushButton("Leer db")
        bottom_layout.addWidget(self.load_artists_button)

        self.sync_artists_button = QPushButton("Sincronizar Artistas")
        bottom_layout.addWidget(self.sync_artists_button)

        self.sync_lastfm_button = QPushButton("Sync Lastfm")
        bottom_layout.addWidget(self.sync_lastfm_button)
        
        self.get_releases_button = QPushButton("Mis próximos discos")
        bottom_layout.addWidget(self.get_releases_button)
        
        self.get_new_releases_button = QPushButton("Discos ausentes")
        bottom_layout.addWidget(self.get_new_releases_button)
        
        self.get_my_releases_button = QPushButton("Obtener todo...")
        bottom_layout.addWidget(self.get_my_releases_button)

        main_layout.addLayout(bottom_layout)
        
        # Conectar señales
        self._connect_signals()


    def toggle_debug_logging(self):
        """Toggle debug logging on/off"""
        self.enable_logging = not self.enable_logging
        
        # Simply update the log level of the existing loggers
        if self.enable_logging:
            self.logger.setLevel(logging.DEBUG)
            logging.getLogger().setLevel(logging.DEBUG)
            self.results_text.append("Debug logging enabled")
        else:
            self.logger.setLevel(logging.INFO)
            logging.getLogger().setLevel(logging.INFO)
            self.results_text.append("Debug logging disabled")


    def previous_page(self):
        """Navigate to the previous page in the stacked widget"""
        if hasattr(self, 'stackedWidget') and self.stackedWidget.count() > 0:
            current = self.stackedWidget.currentIndex()
            if current > 0:
                self.stackedWidget.setCurrentIndex(current - 1)
            else:
                # Wrap around to the last page
                self.stackedWidget.setCurrentIndex(self.stackedWidget.count() - 1)

    def next_page(self):
        """Navigate to the next page in the stacked widget"""
        if hasattr(self, 'stackedWidget') and self.stackedWidget.count() > 0:
            current = self.stackedWidget.currentIndex()
            if current < self.stackedWidget.count() - 1:
                self.stackedWidget.setCurrentIndex(current + 1)
            else:
                # Wrap around to the first page
                self.stackedWidget.setCurrentIndex(0)



    def _connect_signals(self):
        """Connect signals from widgets to their respective slots."""
        # Connect search functions
        self.search_button.clicked.connect(self.search_and_get_releases)
        self.artist_input.returnPressed.connect(self.search_and_get_releases)
        
        # Connect menu buttons
        self.load_artists_button.clicked.connect(self.show_load_menu)
        self.sync_artists_button.clicked.connect(self.show_sync_menu)
        
        # Connect Last.fm button if enabled
        if hasattr(self, 'sync_lastfm_button'):
            if self.lastfm_enabled:
                self.sync_lastfm_button.clicked.connect(self.show_lastfm_options_menu)
                self.sync_lastfm_button.setVisible(True)
            else:
                self.sync_lastfm_button.setVisible(False)
        
        # Connect other action buttons
        self.get_releases_button.clicked.connect(self.get_muspy_releases)
        self.get_new_releases_button.clicked.connect(lambda: self.get_new_releases(PROJECT_ROOT))
        self.get_my_releases_button.clicked.connect(self.get_all_my_releases)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Add keyboard shortcuts for stacked widget navigation
        prev_shortcut = QShortcut(QKeySequence("Alt+Left"), self)
        prev_shortcut.activated.connect(self.previous_page)
        
        next_shortcut = QShortcut(QKeySequence("Alt+Right"), self)
        next_shortcut.activated.connect(self.next_page)

        # Connect MusicBrainz button if found
        if hasattr(self, 'get_releases_musicbrainz'):
            self.get_releases_musicbrainz.clicked.connect(self.show_musicbrainz_collection_menu)

        # Connect Spotify button if enabled
        if hasattr(self, 'get_releases_spotify_button'):
            if self.spotify_enabled:
                self.get_releases_spotify_button.clicked.connect(self.show_spotify_menu)
                self.get_releases_spotify_button.setVisible(True)
            else:
                self.get_releases_spotify_button.setVisible(False)

    def show_lastfm_options_menu(self):
        """
        Display a menu with Last.fm options when the Last.fm button is clicked
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "Last.fm credentials not configured")
            return
        
        # Create menu
        menu = QMenu(self)
        
        # Add menu options
        top_artists_action = QAction("Show Top Artists...", self)
        loved_tracks_action = QAction("Show Loved Tracks", self)
        refresh_cache_action = QAction("Refresh Cached Data", self)
        
        # Connect actions
        top_artists_action.triggered.connect(self.show_lastfm_top_artists_dialog)
        loved_tracks_action.triggered.connect(self.show_lastfm_loved_tracks)
        refresh_cache_action.triggered.connect(self.clear_lastfm_cache)
        
        # Add actions to menu
        menu.addAction(top_artists_action)
        menu.addAction(loved_tracks_action)
        menu.addSeparator()
        menu.addAction(refresh_cache_action)
        
        # Get the button position
        pos = self.sync_lastfm_button.mapToGlobal(QPoint(0, self.sync_lastfm_button.height()))
        
        # Show menu
        menu.exec(pos)


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
            QMessageBox.warning(self, "Error", "Last.fm is not configured in settings")
            return
        
        # Create a cache key that includes the period and count
        cache_key = f"top_artists_{period}_{count}"
        
        # Try to get from cache first if allowed
        if use_cached:
            cached_data = self.cache_manager(cache_key)
            if cached_data:
                self.display_lastfm_artists_in_stacked_widget(cached_data)
                return
        
        # Create progress dialog
        progress = QProgressDialog("Fetching artists from Last.fm...", "Cancel", 0, 100, self)
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
                QMessageBox.warning(self, "Error", "No artists found on Last.fm account")
                progress.close()
                return
            
            # Log what we found
            self.logger.info(f"Found {len(artists)} artists on Last.fm")
            
            # Cache the results
            self.cache_manager(cache_key, artists)
            
            # Update progress
            progress.setValue(80)
            QApplication.processEvents()
            
            # Display artists in stacked widget table
            self.display_lastfm_artists_in_stacked_widget(artists)
            
            # Final progress
            progress.setValue(100)
            
        except Exception as e:
            error_msg = f"Error fetching artists from Last.fm: {e}"
            QMessageBox.warning(self, "Error", error_msg)
            self.logger.error(error_msg, exc_info=True)
        finally:
            progress.close()


    def _display_lastfm_artists_table(self, artists):
        """
        Display Last.fm artists in a table
        
        Args:
            artists (list): List of artist dictionaries from Last.fm
        """
        # Hide the results text if visible
        if hasattr(self, 'results_text') and self.results_text.isVisible():
            self.results_text.hide()
        
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
        
        # Make the table sortable
        table.setSortingEnabled(True)
        
        # Store reference for later access
        self.artists_table = table
        
        return table



    def update_status_text(self, text):
        """Update the status text in the results area"""
        self.results_text.append(text)
        QApplication.processEvents()  # Keep UI responsive



    def _display_top_artists_results(self, top_artists):
        """
        Display the results of top artists fetching
        
        Args:
            top_artists (list): List of top artists data
        """
        if not top_artists:
            self.results_text.append("No artists found or retrieval failed.")
            return
        
        # Display artists in a formatted way
        self.results_text.clear()
        self.results_text.append(f"Top {len(top_artists)} artists for {self.lastfm_username}:\n")
        
        # Create a context menu for the results text
        self.results_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_text.customContextMenuRequested.connect(self.show_artist_context_menu)
        
        # Store top artists for context menu use
        self.top_artists_list = top_artists
        
        # Display each artist with playcount
        for i, artist in enumerate(top_artists):
            artist_name = artist['name']
            playcount = artist.get('playcount', 'N/A')
            
            # Format line with index for easier selection
            artist_line = f"{i+1}. {artist_name} (Playcount: {playcount})"
            self.results_text.append(artist_line)
            
            # Add a special hidden marker for context menu to identify this line as an artist
            # This uses HTML with a hidden span that won't be visible to users
            hidden_marker = f'<span style="display:none" class="artist" data-index="{i}"></span>'
            cursor = self.results_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.results_text.setTextCursor(cursor)
            self.results_text.textCursor().insertHtml(hidden_marker)
            
        self.results_text.append("\nRight-click on an artist to see options.")

    def show_lastfm_custom_top_artists(self):
        """
        Show a dialog to let the user input a custom number of artists to display
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "Last.fm username not configured")
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


    def show_lastfm_top_artists_dialog(self):
        """
        Show a dialog to select period and number of top artists to display
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "Last.fm is not configured in settings")
            return
        
        # Create the dialog
        dialog = QDialog(self)
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

    def show_artist_context_menu(self, position):
        """
        Show context menu for artists in the results text
        """
        # Get the cursor at the clicked position
        cursor = self.results_text.cursorForPosition(position)
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
                menu.exec(self.results_text.mapToGlobal(position))

    def add_lastfm_artist_to_muspy(self, artist_name):
        """
        Add a Last.fm artist to Muspy - revisada para asegurar la correcta autenticación
        
        Args:
            artist_name (str): Name of the artist to add
        """
        if not self.muspy_username or not self.muspy_api_key:
            QMessageBox.warning(self, "Error", "Muspy configuration not available")
            return
        
        # Comprobar y obtener ID de Muspy si no está establecido
        if not self.muspy_id:
            self.get_muspy_id()
            if not self.muspy_id:
                QMessageBox.warning(self, "Error", "Could not get Muspy ID. Please check your credentials.")
                return

        # Mostrar progreso mientras buscamos MBID
        progress = QProgressDialog("Searching for artist...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Adding Artist")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(20)
        progress.show()
        QApplication.processEvents()
                
        # First get the MBID for the artist
        mbid = self.get_mbid_artist_searched(artist_name)
        progress.setValue(50)
        QApplication.processEvents()
        
        if mbid:
            # Try to add the artist to Muspy
            progress.setLabelText(f"Adding {artist_name} to Muspy...")
            progress.setValue(70)
            QApplication.processEvents()
            
            success = self.add_artist_to_muspy(mbid, artist_name)
            
            progress.setValue(100)
            
            if success:
                QMessageBox.information(self, "Success", f"Successfully added {artist_name} to Muspy")
            else:
                # Depuración adicional para identificar el problema
                self.logger.error(f"Failed to add {artist_name} to Muspy. ID: {self.muspy_id}, MBID: {mbid}")
                QMessageBox.warning(self, "Error", f"Failed to add {artist_name} to Muspy. Check logs for details.")
        else:
            progress.close()
            QMessageBox.warning(self, "Error", f"Could not find MusicBrainz ID for {artist_name}")

    def follow_lastfm_artist_on_spotify(self, artist_name):
        """
        Follow a Last.fm artist on Spotify
        
        Args:
            artist_name (str): Name of the artist to follow
        """
        if not self.spotify_enabled:
            QMessageBox.warning(self, "Error", "Spotify configuration not available")
            return
            
        try:
            # Get the Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                self.results_text.append("Failed to get Spotify client. Please check authentication.")
                return
                
            # Try to follow the artist
            result = self.follow_artist_on_spotify(artist_name, spotify_client)
            
            if result == 1:
                QMessageBox.information(self, "Success", f"Successfully followed {artist_name} on Spotify")
            elif result == 0:
                QMessageBox.information(self, "Already Following", f"You are already following {artist_name} on Spotify")
            else:
                QMessageBox.warning(self, "Error", f"Failed to follow {artist_name} on Spotify")
                
        except Exception as e:
            error_msg = f"Error following artist on Spotify: {e}"
            self.results_text.append(error_msg)
            self.logger.error(error_msg, exc_info=True)

    def show_artist_info(self, artist_name):
        """
        Show detailed information about an artist
        
        Args:
            artist_name (str): Name of the artist
        """
        try:
            # Clear results
            self.results_text.clear()
            self.results_text.show()
            self.results_text.append(f"Fetching information for {artist_name}...\n")
            QApplication.processEvents()
            
            # Get Last.fm info
            if hasattr(self, 'lastfm_auth') and self.lastfm_auth:
                network = self.lastfm_auth.get_network()
                if network:
                    try:
                        artist = network.get_artist(artist_name)
                        
                        # Display basic info
                        self.results_text.append(f"🎵 {artist_name}")
                        
                        # Get listener and playcount info
                        if hasattr(artist, 'get_listener_count'):
                            self.results_text.append(f"Listeners: {artist.get_listener_count():,}")
                        if hasattr(artist, 'get_playcount'):
                            self.results_text.append(f"Total Playcount: {artist.get_playcount():,}")
                        
                        # Get bio if available
                        bio = None
                        if hasattr(artist, 'get_bio_summary'):
                            bio = artist.get_bio_summary(language='en')
                        
                        if bio:
                            # Strip HTML tags for cleaner display
                            import re
                            bio_text = re.sub(r'<[^>]+>', '', bio)
                            self.results_text.append("\nBio:")
                            self.results_text.append(bio_text)
                        
                        # Get top tracks
                        if hasattr(artist, 'get_top_tracks'):
                            top_tracks = artist.get_top_tracks(limit=5)
                            if top_tracks:
                                self.results_text.append("\nTop Tracks:")
                                for i, track in enumerate(top_tracks, 1):
                                    self.results_text.append(f"{i}. {track.item.title}")
                        
                        # Get similar artists
                        if hasattr(artist, 'get_similar'):
                            similar = artist.get_similar(limit=5)
                            if similar:
                                self.results_text.append("\nSimilar Artists:")
                                for i, similar_artist in enumerate(similar, 1):
                                    self.results_text.append(f"{i}. {similar_artist.item.name}")
                    except Exception as e:
                        self.results_text.append(f"Error getting Last.fm info: {e}")
            
            # Get local database info
            self.results_text.append("\nLooking for local info...")
            
            # Use consultar_items_db to check if we have this artist in our database
            if self.query_db_script_path and self.db_path:
                try:
                    import subprocess
                    
                    # Build command
                    cmd = f"python {self.query_db_script_path} --db {self.db_path} --artist \"{artist_name}\" --artist-info"
                    
                    # Run command
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0 and result.stdout:
                        try:
                            artist_info = json.loads(result.stdout)
                            
                            # Display database info
                            if 'links' in artist_info:
                                self.results_text.append("\nOnline Links:")
                                for service, url in artist_info['links'].items():
                                    self.results_text.append(f"- {service.capitalize()}: {url}")
                            
                            if 'albums' in artist_info:
                                self.results_text.append(f"\nAlbums in Database: {len(artist_info['albums'])}")
                                for album in artist_info['albums']:
                                    year = f" ({album['year']})" if album.get('year') else ""
                                    self.results_text.append(f"- {album['name']}{year}")
                        except json.JSONDecodeError:
                            self.results_text.append("Error parsing database info")
                    else:
                        self.results_text.append("Artist not found in local database")
                except Exception as e:
                    self.results_text.append(f"Error querying local database: {e}")
            else:
                self.results_text.append("Database query not available. Check configuration.")
        
        except Exception as e:
            error_msg = f"Error fetching artist info: {e}"
            self.results_text.append(error_msg)
            self.logger.error(error_msg, exc_info=True)


    def show_lastfm_loved_tracks(self, limit=50, use_cached=True):
        """
        Show user's loved tracks from Last.fm with caching support
        
        Args:
            limit (int): Maximum number of tracks to display
            use_cached (bool): Whether to use cached data when available
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "Last.fm username not configured")
            return

        # Try to get from cache first if allowed
        cache_key = f"loved_tracks_{limit}"
        if use_cached:
            cached_data = self.cache_manager(cache_key)
            if cached_data:
                self.display_loved_tracks_in_stacked_widget(cached_data)
                return

        # Create progress dialog
        progress = QProgressDialog("Fetching loved tracks from Last.fm...", "Cancel", 0, 100, self)
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
                QMessageBox.warning(self, "Error", "No loved tracks found on Last.fm account")
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
            self.cache_manager(cache_key, serializable_tracks)
            
            # Store for later use
            self.loved_tracks_list = loved_tracks
            
            # Update progress
            progress.setValue(80)
            
            # Display in stacked widget
            self.display_loved_tracks_in_stacked_widget(loved_tracks)
            
            # Final progress
            progress.setValue(100)
            
        except Exception as e:
            error_msg = f"Error fetching loved tracks from Last.fm: {e}"
            QMessageBox.warning(self, "Error", error_msg)
            self.logger.error(error_msg, exc_info=True)
        finally:
            progress.close()




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
            self.results_text.hide()


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

   

    def show_track_context_menu(self, position):
        """
        Show context menu for tracks in the results text
        """
        # Get the cursor at the clicked position
        cursor = self.results_text.cursorForPosition(position)
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
                menu.exec(self.results_text.mapToGlobal(position))

    def unlove_lastfm_track(self, index):
        """
        Remove a track from Last.fm loved tracks
        
        Args:
            index (int): Index of the track in the loved_tracks_list
        """
        if not hasattr(self, 'loved_tracks_list') or index >= len(self.loved_tracks_list):
            QMessageBox.warning(self, "Error", "Track information not available")
            return
            
        if not self.lastfm_auth.is_authenticated():
            # Need to authenticate for write operations
            reply = QMessageBox.question(
                self,
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
                        QMessageBox.warning(self, "Authentication Failed", "Could not authenticate with Last.fm")
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
                self,
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
                    QMessageBox.information(self, "Success", "Track removed from loved tracks")
                    
                    # Refresh the list
                    self.show_lastfm_loved_tracks()
                else:
                    QMessageBox.warning(self, "Error", "Could not connect to Last.fm")
        except Exception as e:
            error_msg = f"Error removing track from loved tracks: {e}"
            QMessageBox.warning(self, "Error", error_msg)
            self.logger.error(error_msg, exc_info=True)

    def search_track(self, artist_name, track_name):
        """
        Search for a track in local database and online services
        
        Args:
            artist_name (str): Name of the artist
            track_name (str): Name of the track
        """
        # Clear results
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append(f"Searching for '{track_name}' by {artist_name}...\n")
        QApplication.processEvents()
        
        # Check local database
        if self.query_db_script_path and self.db_path:
            try:
                import subprocess
                
                # Build command
                cmd = f"python {self.query_db_script_path} --db {self.db_path} --song \"{track_name}\" --artist \"{artist_name}\" --song-info"
                
                # Run command
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout:
                    try:
                        song_info = json.loads(result.stdout)
                        
                        if song_info:
                            self.results_text.append("Found in local database:")
                            self.results_text.append(f"Title: {song_info.get('title', 'Unknown')}")
                            self.results_text.append(f"Artist: {song_info.get('artist', 'Unknown')}")
                            self.results_text.append(f"Album: {song_info.get('album', 'Unknown')}")
                            
                            if 'file_path' in song_info:
                                self.results_text.append(f"Path: {song_info['file_path']}")
                            
                            if 'links' in song_info:
                                self.results_text.append("\nOnline Links:")
                                for service, url in song_info['links'].items():
                                    self.results_text.append(f"- {service.capitalize()}: {url}")
                        else:
                            self.results_text.append("Track not found in local database")
                    except json.JSONDecodeError:
                        self.results_text.append("Error parsing database info")
                else:
                    self.results_text.append("Track not found in local database")
            except Exception as e:
                self.results_text.append(f"Error querying local database: {e}")
        else:
            self.results_text.append("Database query not available. Check configuration.")
        
        # Try to get Last.fm info
        if hasattr(self, 'lastfm_auth') and self.lastfm_auth:
            try:
                self.results_text.append("\nLooking up on Last.fm...")
                
                network = self.lastfm_auth.get_network()
                if network:
                    track = network.get_track(artist_name, track_name)
                    
                    if track:
                        self.results_text.append(f"Last.fm page: {track.get_url()}")
                        
                        # Try to get additional info
                        try:
                            track_info = track.get_info()
                            if track_info:
                                if 'playcount' in track_info:
                                    self.results_text.append(f"Playcount: {track_info['playcount']}")
                                if 'userplaycount' in track_info:
                                    self.results_text.append(f"Your playcount: {track_info['userplaycount']}")
                        except:
                            pass
            except Exception as e:
                self.results_text.append(f"Error getting Last.fm info: {e}")




    def show_lastfm_sync_menu(self):
        """
        Display a menu with Last.fm sync options when sync_lastfm_button is clicked
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "Last.fm credentials not configured")
            return
        
        menu = QMenu(self)
        
        # Add menu options for different top artist counts
        top10_action = QAction("Sync Top 10 Last.fm Artists", self)
        top50_action = QAction("Sync Top 50 Last.fm Artists", self)
        top100_action = QAction("Sync Top 100 Last.fm Artists", self)
        custom_action = QAction("Sync Custom Number of Artists...", self)
        
        # Connect actions to their respective functions
        top10_action.triggered.connect(lambda: self.sync_top_artists_from_lastfm(10))
        top50_action.triggered.connect(lambda: self.sync_top_artists_from_lastfm(50))
        top100_action.triggered.connect(lambda: self.sync_top_artists_from_lastfm(100))
        custom_action.triggered.connect(self.sync_lastfm_custom_count)
        
        # Add actions to menu
        menu.addAction(top10_action)
        menu.addAction(top50_action)
        menu.addAction(top100_action)
        menu.addSeparator()
        menu.addAction(custom_action)
        
        # Show menu at button position
        menu.exec(self.sync_lastfm_button.mapToGlobal(QPoint(0, self.sync_lastfm_button.height())))




    def show_load_menu(self):
        """
        Display a menu with load options when load_artists_button is clicked
        """
        # Create menu
        menu = QMenu(self)
        
        # Add menu actions
        artists_action = QAction("Seleccionar artistas", self)
        albums_action = QAction("Seleccionar albums", self)
        
        # Connect actions to their respective functions
        artists_action.triggered.connect(self.load_artists_from_file)
        albums_action.triggered.connect(self.load_albums_from_file)
        
        # Add actions to menu
        menu.addAction(artists_action)
        menu.addAction(albums_action)
        
        # Get the button position
        pos = self.load_artists_button.mapToGlobal(QPoint(0, self.load_artists_button.height()))
        
        # Show menu
        menu.exec(pos)


    def show_context_menu(self, position):
        """Show context menu with additional options"""
        context_menu = QMenu(self)
        
        # Add API credential check action
        check_credentials_action = QAction("Check API Credentials", self)
        check_credentials_action.triggered.connect(self.check_api_credentials)
        context_menu.addAction(check_credentials_action)
        
        # Add dependency check action
        check_dependencies_action = QAction("Check Dependencies", self)
        check_dependencies_action.triggered.connect(self.check_install_dependencies)
        context_menu.addAction(check_dependencies_action)
        
        # Add LastFM authentication action
        if self.lastfm_enabled:
            lastfm_auth_action = QAction("Manage LastFM Authentication", self)
            lastfm_auth_action.triggered.connect(self.manage_lastfm_auth)
            context_menu.addAction(lastfm_auth_action)
        
        # Add separator
        context_menu.addSeparator()
        
        # Add debug actions
        if self.enable_logging:
            toggle_debug_action = QAction("Disable Debug Logging", self)
        else:
            toggle_debug_action = QAction("Enable Debug Logging", self)
        
        toggle_debug_action.triggered.connect(self.toggle_debug_logging)
        context_menu.addAction(toggle_debug_action)
        
        # Show the menu
        context_menu.exec(self.mapToGlobal(position))



    def sync_top_artists_from_lastfm(self, count=50, period="overall"):
        """
        Synchronize top Last.fm artists with Muspy
        
        Args:
            count (int): Number of top artists to sync
            period (str): Period to fetch top artists for (7day, 1month, 3month, 6month, 12month, overall)
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "Last.fm username not configured")
            return

        if not self.muspy_id:
            # Try to get the Muspy ID if it's not set
            self.get_muspy_id()
            if not self.muspy_id:
                QMessageBox.warning(self, "Error", "Could not get Muspy ID. Please check your credentials.")
                return

        # Clear the results area and make sure it's visible
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append(f"Starting Last.fm synchronization for user {self.lastfm_username}...\n")
        self.results_text.append(f"Syncing top {count} artists from Last.fm to Muspy using period: {period}\n")
        QApplication.processEvents()  # Force UI update
        
        # Create progress dialog
        progress = QProgressDialog("Syncing artists with Muspy...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Syncing with Muspy")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        
        try:
            # First try direct API import
            import_url = f"{self.base_url}/import/{self.muspy_id}"
            auth = (self.muspy_username, self.muspy_api_key)
            
            import_data = {
                'type': 'lastfm',
                'username': self.lastfm_username,
                'count': count,
                'period': period
            }
            
            self.results_text.append("Sending request to Muspy API...")
            progress.setValue(20)
            QApplication.processEvents()  # Force UI update
            
            # Use POST for the import endpoint
            response = requests.post(import_url, auth=auth, json=import_data)
            
            if response.status_code in [200, 201]:
                success_msg = f"Successfully synchronized top {count} artists from Last.fm account {self.lastfm_username}"
                self.results_text.append(success_msg)
                progress.setValue(100)
                
                # Show success message
                QMessageBox.information(self, "Synchronization Complete", success_msg)
                return
            else:
                # If direct API fails, try alternative method
                self.results_text.append(f"Direct API import failed with status {response.status_code}. Trying alternative method...")
                progress.setValue(30)
                QApplication.processEvents()  # Force UI update
                
                # Use the alternative method - first get the top artists
                import pylast
                network = pylast.LastFMNetwork(
                    api_key=self.lastfm_api_key,
                    api_secret=self.lastfm_api_secret
                )
                
                if not network:
                    self.results_text.append("Could not connect to LastFM. Please check your credentials.")
                    progress.setValue(100)
                    return
                
                progress.setValue(40)
                self.results_text.append(f"Fetching top {count} artists from LastFM...")
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
                    self.results_text.append("No artists found on LastFM account.")
                    progress.setValue(100)
                    return
                
                self.results_text.append(f"Found {len(top_artists)} artists on LastFM.")
                progress.setValue(50)
                QApplication.processEvents()  # Force UI update
                
                # Search for MBIDs and add to Muspy
                successful_adds = 0
                failed_adds = 0
                mbid_not_found = 0
                
                # Process each artist
                for i, artist in enumerate(top_artists):
                    if progress.wasCanceled():
                        self.results_text.append("Operation canceled.")
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
                        self.results_text.append(f"Searching MBID for {artist_name}...")
                        mbid = self.get_mbid_artist_searched(artist_name)
                    
                    if mbid:
                        # Add artist to Muspy
                        self.results_text.append(f"Adding {artist_name} to Muspy...")
                        result = self.add_artist_to_muspy_silent(mbid, artist_name)
                        if result == 1:
                            successful_adds += 1
                            self.results_text.append(f"Successfully added {artist_name} to Muspy")
                        elif result == 0:
                            # Already exists
                            successful_adds += 1
                            self.results_text.append(f"{artist_name} already exists in Muspy")
                        else:
                            failed_adds += 1
                            self.results_text.append(f"Failed to add {artist_name} to Muspy")
                    else:
                        mbid_not_found += 1
                        self.results_text.append(f"Could not find MBID for {artist_name}")
                    
                    # Check if we should continue
                    if i % 5 == 0:
                        self.results_text.append(f"Processed: {i+1}/{len(top_artists)}, Added: {successful_adds}, Failed: {failed_adds}, No MBID: {mbid_not_found}")
                        QApplication.processEvents()  # Force UI update
                
                # Final progress
                progress.setValue(100)
                
                # Summary message
                summary_msg = f"Sync complete: Added {successful_adds}, Failed {failed_adds}, No MBID {mbid_not_found}"
                self.results_text.append(summary_msg)
                
                # Show a message box with results
                QMessageBox.information(self, "Synchronization Complete", summary_msg)
        except Exception as e:
            error_msg = f"Error syncing with Muspy API: {e}"
            self.results_text.append(error_msg)
            self.logger.error(error_msg, exc_info=True)
            
            # Show error message
            QMessageBox.warning(self, "Error", f"Error during synchronization: {str(e)}")
        finally:
            progress.close()
                


    def _sync_artists_with_progress(self, progress_callback, status_callback, count):
        """
        Background worker function to sync artists with progress updates
        
        Args:
            progress_callback: Function to call for progress updates
            status_callback: Function to call for status text updates
            count: Number of artists to sync
            
        Returns:
            dict: Sync results summary
        """
        try:
            # First try direct API import
            import_url = f"{self.base_url}/import/{self.muspy_id}"
            auth = (self.muspy_username, self.muspy_api_key)
            
            import_data = {
                'type': 'lastfm',
                'username': self.lastfm_username,
                'count': count,
                'period': 'overall'
            }
            
            status_callback("Sending request to Muspy API...")
            progress_callback(20)
            
            # Use POST for the import endpoint
            response = requests.post(import_url, auth=auth, json=import_data)
            
            if response.status_code in [200, 201]:
                status_callback(f"Successfully synchronized top {count} artists from Last.fm account {self.lastfm_username}")
                progress_callback(100)
                return {
                    'success': True,
                    'message': f"Successfully synchronized top {count} artists from Last.fm",
                    'api_method': 'direct'
                }
            else:
                # If direct API fails, try using our LastFM manager as fallback
                status_callback("Direct API import failed. Trying alternative method...")
                progress_callback(30)
                
                # Use the alternative method
                result = self.sync_top_artists_from_lastfm(
                    progress_callback=lambda p: progress_callback(30 + int(p * 0.7)),  # Scale to 30-100%
                    status_callback=status_callback,
                    count=count
                )
                
                return result
        except Exception as e:
            error_msg = f"Error syncing with Muspy API: {e}"
            status_callback(error_msg)
            self.logger.error(error_msg, exc_info=True)
            
            # Try alternative method
            status_callback("Trying alternative synchronization method...")
            progress_callback(30)
            
            # Use the alternative method
            result = self.sync_top_artists_from_lastfm(
                progress_callback=lambda p: progress_callback(30 + int(p * 0.7)),  # Scale to 30-100%
                status_callback=status_callback,
                count=count
            )
            
            return result

    def sync_spotify_selected_artists(self):
        """
        Synchronize selected artists from the JSON file with Spotify
        """
        # Check if Spotify is enabled
        if not self.spotify_enabled:
            QMessageBox.warning(self, "Error", "Spotify credentials not configured")
            return
        
        # Path to the JSON file
        json_path = os.path.join(PROJECT_ROOT, ".content", "cache", "artists_selected.json")
        
        # Check if file exists
        if not os.path.exists(json_path):
            QMessageBox.warning(self, "Error", "No selected artists file found. Please load artists first.")
            return
        
        # Load artists from JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
                
            if not artists_data:
                QMessageBox.warning(self, "Error", "No artists found in the selection file.")
                return
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading selected artists: {str(e)}")
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
                QMessageBox.warning(self, "Error", "Could not authenticate with Spotify. Please check your credentials.")
                return
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error initializing Spotify: {str(e)}")
            return
        
        # Create progress dialog
        progress = QProgressDialog("Syncing artists with Spotify...", "Cancel", 0, len(artists_data), self)
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
                    
        QMessageBox.information(self, "Spotify Synchronization Complete", summary_msg)
    def _display_sync_results(self, result):
        """
        Display the results of the synchronization
        
        Args:
            result (dict or list): Sync results summary
        """
        # Handle case where result is a list (from certain API calls)
        if isinstance(result, list):
            self.results_text.clear()
            self.results_text.append("Synchronization completed!\n")
            
            # Basic stats for list results
            self.results_text.append(f"Processed {len(result)} items")
            
            # Show success message
            QMessageBox.information(self, "Synchronization Complete", 
                                f"Synchronization completed successfully with {len(result)} items processed.")
            return
            
        # Continue with original dictionary-based handling
        if result and result.get('success'):
            self.results_text.clear()
            self.results_text.append("Synchronization completed successfully!\n")
            self.results_text.append(result.get('message', ""))
            
            # Show additional details if available
            if 'stats' in result:
                stats = result['stats']
                self.results_text.append(f"\nSummary:")
                self.results_text.append(f"Total artists processed: {stats.get('total', 0)}")
                self.results_text.append(f"Successfully added: {stats.get('success', 0)}")
                self.results_text.append(f"Not found (no MBID): {stats.get('no_mbid', 0)}")
                self.results_text.append(f"Failed to add: {stats.get('failed', 0)}")
            
            self.results_text.append("\nYou can now view your upcoming releases using the 'Mis próximos discos' button")
            
            # Show success message
            QMessageBox.information(self, "Synchronization Complete", result.get('message', "Synchronization successful"))
        elif result:  # Result exists but no success flag
            self.results_text.append("\nSynchronization status unclear.")
            self.results_text.append(result.get('message', "Unknown status"))
        else:
            self.results_text.append("\nSynchronization failed or returned no data.")

  

    def sync_lastfm_custom_count(self):
        """
        Show a dialog to let the user input a custom number of artists to sync
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "Last.fm username not configured")
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

    def check_install_dependencies(self):
        """Check and optionally install missing dependencies"""
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append("Checking dependencies...")
        QApplication.processEvents()
        
        missing_deps = []
        
        # Check for required packages
        try:
            import requests
            self.results_text.append("✓ requests package installed")
        except ImportError:
            missing_deps.append("requests")
            self.results_text.append("✗ requests package missing")
        
        try:
            import spotipy
            self.results_text.append("✓ spotipy package installed")
        except ImportError:
            missing_deps.append("spotipy")
            self.results_text.append("✗ spotipy package missing")
        
        try:
            import pylast
            self.results_text.append("✓ pylast package installed")
        except ImportError:
            missing_deps.append("pylast")
            self.results_text.append("✗ pylast package missing")
        
        # Offer to install missing dependencies
        if missing_deps:
            self.results_text.append("\nMissing dependencies found. Would you like to install them?")
            
            # Create a message box to ask for installation
            reply = QMessageBox.question(
                self, 
                "Install Dependencies", 
                f"The following dependencies are missing:\n- {', '.join(missing_deps)}\n\nWould you like to install them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.results_text.append("\nInstalling dependencies...")
                QApplication.processEvents()
                
                # Create a string of all dependencies to install
                deps_str = " ".join(missing_deps)
                
                try:
                    import subprocess
                    result = subprocess.run(
                        f"pip install {deps_str}", 
                        shell=True, 
                        capture_output=True, 
                        text=True
                    )
                    
                    if result.returncode == 0:
                        self.results_text.append("✓ Dependencies installed successfully!")
                        self.results_text.append("\nPlease restart the application to use the new dependencies.")
                    else:
                        self.results_text.append(f"✗ Error installing dependencies: {result.stderr}")
                except Exception as e:
                    self.results_text.append(f"✗ Error running pip: {e}")
            else:
                self.results_text.append("\nDependency installation skipped.")
        else:
            self.results_text.append("\n✓ All required dependencies are installed!")


    def check_api_credentials(self):
        """
        Check and display the status of API credentials for debugging
        """
        self.show_text_page()
        self.results_text.clear()
        
        self.results_text.append("API Credentials Status:\n")
        
        # Check Muspy credentials
        self.results_text.append("Muspy Credentials:")
        if self.muspy_username and self.muspy_api_key:
            self.results_text.append(f"  Username: {self.muspy_username}")
            self.results_text.append(f"  API Key: {'*' * len(self.muspy_api_key) if self.muspy_api_key else 'Not configured'}")
            self.results_text.append(f"  Muspy ID: {self.muspy_id or 'Not detected'}")
            self.results_text.append("  Status: Configured")
        else:
            self.results_text.append("  Status: Not fully configured")
        
        # Check Spotify credentials
        self.results_text.append("\nSpotify Credentials:")
        if self.spotify_client_id and self.spotify_client_secret:
            self.results_text.append(f"  Client ID: {self.spotify_client_id[:5]}...{self.spotify_client_id[-5:] if len(self.spotify_client_id) > 10 else ''}")
            self.results_text.append(f"  Client Secret: {'*' * 10}")
            self.results_text.append("  Status: Configured")
            
            # Test authentication if credentials are available
            if hasattr(self, 'spotify_auth') and self.spotify_auth:
                is_auth = self.spotify_auth.is_authenticated()
                self.results_text.append(f"  Authentication: {'Successful' if is_auth else 'Failed or not attempted'}")
        else:
            self.results_text.append("  Status: Not fully configured")
        
        # Check Last.fm credentials
        self.results_text.append("\nLast.fm Credentials:")
        if self.lastfm_api_key and self.lastfm_username:
            self.results_text.append(f"  API Key: {self.lastfm_api_key[:5]}...{self.lastfm_api_key[-5:] if len(self.lastfm_api_key) > 10 else ''}")
            self.results_text.append(f"  Username: {self.lastfm_username}")
            self.results_text.append("  Status: Configured")
            
            # Test authentication if LastFM auth manager exists
            if hasattr(self, 'lastfm_auth'):
                is_auth = self.lastfm_auth.is_authenticated()
                self.results_text.append(f"  Authentication: {'Successful' if is_auth else 'Not authenticated for write operations'}")
        else:
            self.results_text.append("  Status: Not fully configured")
        
        self.results_text.append("\nTo test connections, use the sync menu options.")
    
    
    
    def get_muspy_id(self):
        """
        Returns the Muspy ID, using the one from config and only fetching if not available
        
        Returns:
            str: ID de usuario de Muspy
        """
        # If we already have an ID, use it
        if self.muspy_id:
            self.logger.debug(f"Using existing Muspy ID: {self.muspy_id}")
            return self.muspy_id
            
        # If not available and we have credentials, try to fetch it once
        if not self.muspy_id and self.muspy_username and self.muspy_api_key:
            try:
                self.logger.info("No Muspy ID in config, attempting to fetch from API")
                # Using the /user endpoint to get user info
                url = f"{self.base_url}/user"
                auth = (self.muspy_username, self.muspy_api_key)
                
                response = requests.get(url, auth=auth)
                
                if response.status_code == 200:
                    # Try to parse user_id from response
                    user_data = response.json()
                    if 'userid' in user_data:
                        self.muspy_id = user_data['userid']
                        self.logger.info(f"Muspy ID obtained: {self.muspy_id}")
                        return self.muspy_id
                    else:
                        self.logger.error(f"No 'userid' in response JSON: {user_data}")
                else:
                    self.logger.error(f"Error calling Muspy API: {response.status_code} - {response.text}")
            except Exception as e:
                self.logger.error(f"Error getting Muspy ID: {e}", exc_info=True)
        
        # If we still don't have an ID, log the error
        if not self.muspy_id:
            self.logger.error("No valid Muspy ID available. Please set it in configuration.")
        
        return self.muspy_id

    def load_artists_from_file(self):
        """
        Executes a script to load artists from the database,
        shows a dialog with checkboxes for selecting artists and
        saves the selected ones to a JSON file
        """
        try:
            # Ensure we have PROJECT_ROOT
            self.results_text.append(f"PROJECT_ROOT: {PROJECT_ROOT}")

            # Ensure db_path is absolute
            if not os.path.isabs(self.db_path):
                full_db_path = os.path.join(PROJECT_ROOT, self.db_path)
            else:
                full_db_path = self.db_path
            
            # Print debug info
            self.results_text.append(f"Using database path: {full_db_path}")
            self.results_text.append(f"Database exists: {os.path.exists(full_db_path)}")

            # Build path to the script
            script_path = os.path.join(PROJECT_ROOT, "base_datos", "tools", "consultar_items_db.py")
            
            # Check if script exists
            if not os.path.exists(script_path):
                self.results_text.append(f"Error: Script not found at {script_path}")
                return
                
            # Execute the query script for artists
            self.results_text.clear()
            self.results_text.append("Executing query for artists in the database...")
            QApplication.processEvents()  # Update UI
            
            cmd = f"python {script_path} --db {full_db_path} --buscar artistas"
            self.results_text.append(f"Running command: {cmd}")
            QApplication.processEvents()
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.results_text.append(f"Error executing script: {result.stderr}")
                return
                
            # Load results as JSON
            try:
                artists_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                self.results_text.append(f"Error processing script output: {e}")
                self.results_text.append(f"Script output: {result.stdout[:500]}...")
                return
            
            # Check if there are artists
            if not artists_data:
                self.results_text.append("No artists found in the database.")
                return
            
            # Ensure cache directory exists
            cache_dir = os.path.join(PROJECT_ROOT, ".content", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Load existing artists if file already exists
            json_path = os.path.join(cache_dir, "artists_selected.json")
            existing_artists = []
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = f.read()
                        if data:  # Only try to load if not empty
                            existing_artists = json.loads(data)
                        else:
                            self.results_text.append("Existing artists file is empty, using empty list")
                except Exception as e:
                    self.results_text.append(f"Error loading existing artists: {e}")
            
            # Create a list of existing artist names
            existing_names = set()
            if existing_artists:
                existing_names = {artist.get("nombre", "") for artist in existing_artists if isinstance(artist, dict) and "nombre" in artist}
            
            # Create the dialog using the UI file
            dialog = QDialog(self)
            ui_file_path = os.path.join(PROJECT_ROOT, "ui", "muspy_artist_selection_dialog.ui")
            
            if os.path.exists(ui_file_path):
                try:
                    # Load the UI file
                    uic.loadUi(ui_file_path, dialog)
                    
                    # Explicitly connect dialog buttons
                    if hasattr(dialog, 'buttonBox'):
                        dialog.buttonBox.accepted.connect(dialog.accept)
                        dialog.buttonBox.rejected.connect(dialog.reject)
                        self.results_text.append("Dialog buttonBox connections established")
                    else:
                        self.results_text.append("Warning: buttonBox not found in dialog")
                    
                    # Update the label with artist count
                    dialog.info_label.setText(f"Selecciona los artistas que deseas guardar ({len(artists_data)} encontrados)")
                    
                    # Remove example checkboxes from scroll_layout
                    for i in reversed(range(dialog.scroll_layout.count())):
                        widget = dialog.scroll_layout.itemAt(i).widget()
                        if widget is not None:
                            widget.deleteLater()
                    
                    # Create checkboxes for each artist
                    checkboxes = []
                    for artist in artists_data:
                        artist_name = artist.get('nombre', '')
                        artist_mbid = artist.get('mbid', '')
                        
                        checkbox = QCheckBox(f"{artist_name} ({artist_mbid})")
                        checkbox.setChecked(artist_name in existing_names)  # Pre-select if already exists
                        checkbox.setProperty("artist_data", artist)  # Store artist data in checkbox
                        checkboxes.append(checkbox)
                        dialog.scroll_layout.addWidget(checkbox)
                    
                    # Connect signals
                    dialog.search_input.textChanged.connect(lambda text: self.filter_artists(text, checkboxes))
                    dialog.select_all_button.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes if not cb.isHidden()])
                    dialog.deselect_all_button.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes])
                    
                except Exception as e:
                    self.results_text.append(f"Error loading UI for artist selection: {e}")
                    return
            else:
                self.results_text.append(f"UI file not found: {ui_file_path}")
                return
                
            # Show the dialog
            result = dialog.exec()
            self.results_text.append(f"Dialog execution result: {result}")
            self.results_text.append(f"QDialog.DialogCode.Accepted value: {QDialog.DialogCode.Accepted}")
            
            if result == QDialog.DialogCode.Accepted:
                self.results_text.append("Dialog accepted, processing selection...")
            else:
                self.results_text.append("Operation canceled by user.")
                return
            
            # Collect selected artists
            selected_artists = []
            
            # Get selected artists from checkboxes
            for checkbox in checkboxes:
                if checkbox.isChecked():
                    artist_data = checkbox.property("artist_data")
                    if artist_data:
                        selected_artists.append(artist_data)
            
            self.results_text.append(f"Number of selected artists: {len(selected_artists)}")
            if selected_artists:
                self.results_text.append(f"First selected artist: {str(selected_artists[0])}")
            
            # Save selected artists to JSON
            try:
                # Ensure the directory exists
                cache_dir = os.path.join(PROJECT_ROOT, ".content", "cache")
                os.makedirs(cache_dir, exist_ok=True)
                json_path = os.path.join(cache_dir, "artists_selected.json")
                
                self.results_text.append(f"Trying to save to: {json_path}")
                self.results_text.append(f"Directory exists: {os.path.exists(os.path.dirname(json_path))}")
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(selected_artists, f, ensure_ascii=False, indent=2)
                
                # Verify file was created
                if os.path.exists(json_path):
                    file_size = os.path.getsize(json_path)
                    self.results_text.append(f"File created successfully. Size: {file_size} bytes")
                else:
                    self.results_text.append("File not created despite no errors")
                
                # Update artists in the instance
                self.artists = [artist["nombre"] for artist in selected_artists]
                
                self.results_text.append(f"Saved {len(selected_artists)} artists to {json_path}")
                
                # Show popup with results
                QMessageBox.information(
                    self, 
                    "Artists Saved", 
                    f"Saved {len(selected_artists)} artists for synchronization.\n"
                    f"You can synchronize them with Muspy, Last.fm or Spotify using the sync button."
                )
            except Exception as e:
                self.results_text.append(f"Error saving artists: {e}")
                self.logger.error(f"Error saving artists file: {e}", exc_info=True)
        
        except Exception as e:
            self.results_text.append(f"Error: {str(e)}")
            logger.error(f"Error in load_artists_from_file: {e}", exc_info=True)

    def filter_artists(self, search_text, checkboxes):
        """
        Filter artists in the dialog by search text
        
        Args:
            search_text (str): Text to search for
            checkboxes (list): List of artist checkboxes
        """
        search_text = search_text.lower()
        for checkbox in checkboxes:
            artist_data = checkbox.property("artist_data")
            
            # Show/hide based on artist name match
            if isinstance(artist_data, dict) and "nombre" in artist_data:
                artist_name = artist_data["nombre"].lower()
                visible = search_text in artist_name
                checkbox.setVisible(visible)
            else:
                # Fallback to checkbox text if artist_data not available
                checkbox_text = checkbox.text().lower()
                visible = search_text in checkbox_text
                checkbox.setVisible(visible)


    def load_albums_from_file(self):
        """
        Executes a script to load albums from the database,
        shows a dialog with a tree view for selecting albums and
        saves the selected ones to a JSON file
        """
        try:
            # Ensure we have PROJECT_ROOT
            self.results_text.append(f"PROJECT_ROOT: {PROJECT_ROOT}")

            # Ensure db_path is absolute
            if not os.path.isabs(self.db_path):
                full_db_path = os.path.join(PROJECT_ROOT, self.db_path)
            else:
                full_db_path = self.db_path
            
            # Print debug info
            self.results_text.append(f"Using database path: {full_db_path}")
            self.results_text.append(f"Database exists: {os.path.exists(full_db_path)}")

            # Build path to the script
            script_path = os.path.join(PROJECT_ROOT, "base_datos", "tools", "consultar_items_db.py")
            
            # Check if script exists
            if not os.path.exists(script_path):
                self.results_text.append(f"Error: Script not found at {script_path}")
                return
                
            # Execute the query script
            self.results_text.clear()
            self.results_text.append("Executing album query in the database...")
            QApplication.processEvents()  # Update UI
            
            cmd = f"python {script_path} --db {full_db_path} --buscar albums"
            self.results_text.append(f"Running command: {cmd}")
            QApplication.processEvents()
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.results_text.append(f"Error executing script: {result.stderr}")
                return
                
            # Load results as JSON
            try:
                albums_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                self.results_text.append(f"Error processing script output: {e}")
                self.results_text.append(f"Script output: {result.stdout[:500]}...")
                return
            
            # Check if there are albums
            if not albums_data:
                self.results_text.append("No albums found in the database.")
                return
            
            # Ensure cache directory exists
            cache_dir = os.path.join(PROJECT_ROOT, ".content", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Load existing albums if file already exists
            json_path = os.path.join(cache_dir, "albums_selected.json")
            existing_albums = []
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = f.read()
                        if data:  # Only try to load if not empty
                            existing_albums = json.loads(data)
                        else:
                            self.results_text.append("Existing albums file is empty, using empty list")
                except Exception as e:
                    self.results_text.append(f"Error loading existing albums: {e}")
            
            # Create a set of existing album MBIDs for checking
            existing_mbids = set()
            if existing_albums:
                existing_mbids = {album.get("mbid", "") for album in existing_albums if isinstance(album, dict) and "mbid" in album}
            
            # Create the dialog using the UI file
            dialog = QDialog(self)
            ui_file_path = os.path.join(PROJECT_ROOT, "ui", "muspy_artist_selection_dialog.ui")
            
            if os.path.exists(ui_file_path):
                try:
                    # Load the UI file
                    uic.loadUi(ui_file_path, dialog)
                    if hasattr(dialog, 'buttonBox'):
                        # Conecta las señales a los slots de QDialog
                        dialog.buttonBox.accepted.connect(dialog.accept)
                        dialog.buttonBox.rejected.connect(dialog.reject)
                        self.logger.debug("Dialog buttonBox signals connected for albums")


                    # Update the label with album count
                    dialog.info_label.setText(f"Selecciona los álbumes que deseas guardar ({len(albums_data)} encontrados)")
                    
                    # Remove example checkboxes from scroll_layout
                    for i in reversed(range(dialog.scroll_layout.count())):
                        widget = dialog.scroll_layout.itemAt(i).widget()
                        if widget is not None:
                            widget.deleteLater()
                    
                    # Create the tree widget to replace checkboxes
                    tree = QTreeWidget()
                    tree.setColumnCount(4)
                    tree.setHeaderLabels(["Artista", "Álbum", "Año", "MBID"])
                    tree.setAlternatingRowColors(True)
                    tree.setSortingEnabled(True)
                    
                    # Add the tree to the scroll layout
                    dialog.scroll_layout.addWidget(tree)
                    
                    # Organize albums by artist
                    artists = {}
                    for album in albums_data:
                        # Get correct album properties from the JSON data
                        artist_name = album.get("artista", "Unknown Artist")
                        album_name = album.get("album", "Unknown Album")
                        album_mbid = album.get("mbid", "")
                        
                        # Add to artist dictionary
                        if artist_name not in artists:
                            artists[artist_name] = []
                        
                        artists[artist_name].append(album)
                    
                    # Create checkboxes for each album, organized by artist
                    checkboxes = []
                    
                    # Populate tree with albums grouped by artist
                    for artist_name, artist_albums in artists.items():
                        # Create artist parent item
                        artist_item = QTreeWidgetItem(tree)
                        artist_item.setText(0, "")
                        artist_item.setText(1, artist_name)
                        artist_item.setExpanded(True)
                        
                        # Set bold font for artist
                        font = artist_item.font(1)
                        font.setBold(True)
                        artist_item.setFont(1, font)
                        
                        # Add each album as a child item
                        for album in artist_albums:
                            album_item = QTreeWidgetItem()
                            
                            # Create a checkbox for the album
                            checkbox = QCheckBox()
                            checkbox.setText(f"{album.get('album', 'Unknown Album')}")
                            checkbox.setChecked(album.get("mbid", "") in existing_mbids)
                            checkbox.setProperty("album_data", album)
                            checkboxes.append(checkbox)
                            
                            # Add album data to tree item
                            album_item = QTreeWidgetItem(artist_item)
                            album_item.setText(0, artist_name)
                            album_item.setText(1, album.get("album", "Unknown Album"))
                            album_item.setText(2, album.get("year", ""))
                            album_item.setText(3, album.get("mbid", ""))
                            
                            # Store checkbox in first column
                            tree.setItemWidget(album_item, 1, checkbox)
                            
                            # Store original album data in the item
                            album_item.setData(0, Qt.ItemDataRole.UserRole, album)
                    
                    # Resize columns to content
                    for i in range(4):
                        tree.resizeColumnToContents(i)
                    
                    # Connect signals
                    dialog.search_input.textChanged.connect(lambda text: self.filter_albums_tree(text, tree, checkboxes))
                    dialog.select_all_button.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes if not cb.isHidden()])
                    dialog.deselect_all_button.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes])
                    
                    # Store references for access from other functions
                    dialog.tree = tree
                    dialog.checkboxes = checkboxes
                    
                except Exception as e:
                    self.results_text.append(f"Error loading UI for album selection: {e}")
                    return
            else:
                self.results_text.append(f"UI file not found: {ui_file_path}")
                return
                
            # Show the dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.results_text.append("Dialog accepted, processing selection...")
            else:
                self.results_text.append("Operation canceled by user.")
                return
            
            # Collect selected albums
            selected_albums = []
            
            # Get selected albums from checkboxes
            for checkbox in checkboxes:
                if checkbox.isChecked():
                    album_data = checkbox.property("album_data")
                    if album_data:
                        selected_albums.append(album_data)
            
            # Save selected albums to JSON
            try:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(json_path), exist_ok=True)
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(selected_albums, f, ensure_ascii=False, indent=2)
                
                self.results_text.append(f"Saved {len(selected_albums)} albums to {json_path}")
                
                # Show popup with results
                QMessageBox.information(
                    self, 
                    "Albums Saved", 
                    f"Saved {len(selected_albums)} albums for synchronization.\n"
                    f"You can synchronize them with Muspy, Last.fm or Spotify using the sync button."
                )
            except Exception as e:
                self.results_text.append(f"Error saving albums: {e}")
        
        except Exception as e:
            self.results_text.append(f"Error: {str(e)}")
            logger.error(f"Error in load_albums_from_file: {e}", exc_info=True)

    def filter_albums_tree(self, search_text, tree, checkboxes=None):
        """
        Filter albums in the tree view by search text
        """
        search_text = search_text.lower()
        
        # Process all top-level items (artists)
        for i in range(tree.topLevelItemCount()):
            artist_item = tree.topLevelItem(i)
            visible_children = 0
            
            # El nombre del artista ahora está en la columna 0
            artist_name = artist_item.text(0).lower()
            
            # Check each album under this artist
            for j in range(artist_item.childCount()):
                album_item = artist_item.child(j)
                
                # El nombre del álbum ahora está en la columna 1
                album_name = album_item.text(1).lower()
                
                # Show/hide based on search
                if search_text in album_name or search_text in artist_name:
                    album_item.setHidden(False)
                    if checkboxes:
                        # Necesitas ajustar dónde buscas el checkbox si estás usando setItemWidget
                        checkbox = tree.itemWidget(album_item, 1)  # Ahora en columna 1
                        if checkbox in checkboxes:
                            checkbox.setHidden(False)
                    visible_children += 1
                else:
                    album_item.setHidden(True)
                    if checkboxes:
                        checkbox = tree.itemWidget(album_item, 1)  # Ahora en columna 1
                        if checkbox in checkboxes:
                            checkbox.setHidden(True)
            
            # Show/hide artist based on whether any children are visible
            artist_item.setHidden(visible_children == 0)
            
            # If search text matches artist name, show all albums
            if search_text in artist_name:
                artist_item.setHidden(False)
                for j in range(artist_item.childCount()):
                    album_item = artist_item.child(j)
                    album_item.setHidden(False)
                    if checkboxes:
                        checkbox = tree.itemWidget(album_item, 1)  # Ahora en columna 1
                        if checkbox in checkboxes:
                            checkbox.setHidden(False)


    def filter_albums(self, search_text, checkboxes):
        """
        Filtra los álbumes en el diálogo según el texto de búsqueda.
        
        Args:
            search_text (str): Texto de búsqueda
            checkboxes (list): Lista de checkboxes de álbumes
        """
        search_text = search_text.lower()
        for checkbox in checkboxes:
            album_data = checkbox.property("album_data")
            
            # Buscar tanto en el nombre del artista como en el del álbum
            artist_name = album_data.get("artista", "").lower()
            album_name = album_data.get("nombre", "").lower()
            
            visible = search_text in artist_name or search_text in album_name
            checkbox.setVisible(visible)


    def get_albums_with_mbids(self, artist_name=None):
        """
        Get albums and their MBIDs from the local database using consultar_items_db
        
        Args:
            artist_name (str, optional): Filter by artist name
            
        Returns:
            list: Albums with their MBIDs and metadata
        """
        try:
            # Determine database path
            if not os.path.isabs(self.db_path):
                full_db_path = os.path.join(PROJECT_ROOT, self.db_path)
            else:
                full_db_path = self.db_path
                
            # Ensure script path is available
            if not self.query_db_script_path or not os.path.exists(self.query_db_script_path):
                script_path = os.path.join(PROJECT_ROOT, "base_datos", "tools", "consultar_items_db.py")
            else:
                script_path = self.query_db_script_path
                
            # Build command
            if artist_name:
                cmd = f"python {script_path} --db {full_db_path} --artist \"{artist_name}\" --album-info"
            else:
                cmd = f"python {script_path} --db {full_db_path} --ultimos --limite 500"
                
            self.logger.info(f"Running command: {cmd}")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Error executing script: {result.stderr}")
                return []
                
            # Parse JSON result
            albums_data = json.loads(result.stdout)
            
            # Log results for debugging
            self.logger.debug(f"Found {len(albums_data)} albums")
            if albums_data and len(albums_data) > 0:
                self.logger.debug(f"Sample album data: {albums_data[0]}")
                
            return albums_data
            
        except Exception as e:
            self.logger.error(f"Error getting albums with MBIDs: {e}", exc_info=True)
            return []


    def display_releases_tree(self, releases, group_by_artist=True):
        """
        Display releases in a tree view grouped by artist
        
        Args:
            releases (list): List of release dictionaries
            group_by_artist (bool): Whether to group by artist or not
        """
        # Clear any existing table/tree widget
        for i in reversed(range(self.layout().count())): 
            item = self.layout().itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None and (isinstance(widget, QTreeWidget) or 
                                        isinstance(widget, QTableWidget) or 
                                        (hasattr(self, 'add_follow_button') and widget == self.add_follow_button)):
                    self.layout().removeItem(item)
                    widget.deleteLater()
        
        # Create new tree widget with specific object name
        tree = QTreeWidget()
        tree.setObjectName("releases_tree")
        tree.setHeaderLabels(["Artist/Release", "Type", "Date", "Details"])
        tree.setColumnCount(4)
        tree.setAlternatingRowColors(True)
        tree.setSortingEnabled(True)
        
        # Set the size policy to make it fill available space
        tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tree.setMinimumHeight(400)  # Set minimum height to ensure visibility
        
        # Organize releases by artist if requested
        if group_by_artist:
            artists = {}
            for release in releases:
                artist_name = release.get('artist', {}).get('name', 'Unknown Artist')
                if artist_name not in artists:
                    artists[artist_name] = []
                artists[artist_name].append(release)
                
            # Create tree items
            for artist_name, artist_releases in artists.items():
                # Create parent item for artist
                artist_item = QTreeWidgetItem(tree)
                artist_item.setText(0, artist_name)
                artist_item.setText(1, "")
                artist_item.setExpanded(True)  # Expand by default
                
                # Add child items for each release
                for release in artist_releases:
                    release_item = QTreeWidgetItem(artist_item)
                    release_item.setText(0, release.get('title', 'Unknown'))
                    release_item.setText(1, release.get('type', 'Unknown').title())
                    release_item.setText(2, release.get('date', 'No date'))
                    
                    # Format details
                    details = []
                    if release.get('format'):
                        details.append(f"Format: {release.get('format')}")
                    if release.get('tracks'):
                        details.append(f"Tracks: {release.get('tracks')}")
                    release_item.setText(3, "; ".join(details) if details else "")
                    
                    # Store release data for later reference
                    release_item.setData(0, Qt.ItemDataRole.UserRole, release)
                    
                    # Color by date
                    try:
                        release_date = datetime.datetime.strptime(release.get('date', '9999-99-99'), "%Y-%m-%d").date()
                        today = datetime.date.today()
                        one_month = today + datetime.timedelta(days=30)
                        
                        if release_date <= today + datetime.timedelta(days=7):
                            # Coming very soon - red background
                            for col in range(4):
                                release_item.setBackground(col, QColor(31, 60, 28))
                        elif release_date <= one_month:
                            # Coming in a month - yellow background
                            for col in range(4):
                                release_item.setBackground(col, QColor(60, 28, 31))
                    except ValueError:
                        # Invalid date format, don't color
                        pass
        else:
            # Simple flat list
            for release in releases:
                release_item = QTreeWidgetItem(tree)
                artist_name = release.get('artist', {}).get('name', 'Unknown Artist')
                release_item.setText(0, f"{artist_name} - {release.get('title', 'Unknown')}")
                release_item.setText(1, release.get('type', 'Unknown').title())
                release_item.setText(2, release.get('date', 'No date'))
                
                # Format details
                details = []
                if release.get('format'):
                    details.append(f"Format: {release.get('format')}")
                if release.get('tracks'):
                    details.append(f"Tracks: {release.get('tracks')}")
                release_item.setText(3, "; ".join(details) if details else "")
                
                # Store release data
                release_item.setData(0, Qt.ItemDataRole.UserRole, release)
        
        # Resize columns to content
        for i in range(4):
            tree.resizeColumnToContents(i)
        
        # Connect signals
        tree.itemDoubleClicked.connect(self.on_release_double_clicked)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.show_release_context_menu)
        
        # Hide the text edit and add the tree to the layout at a specific position
        self.results_text.hide()
        
        # If we have a stacked widget, use it
        stacked_widget = self.findChild(QStackedWidget, "stackedWidget")
        if stacked_widget:
            # Find the releases page by name or add the tree to it
            releases_page = None
            for i in range(stacked_widget.count()):
                page = stacked_widget.widget(i)
                if page.objectName() == "releases_page":
                    releases_page = page
                    break
                    
            if releases_page:
                # Clear the existing layout
                if releases_page.layout():
                    while releases_page.layout().count():
                        item = releases_page.layout().takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()
                else:
                    # Create a layout if it doesn't exist
                    page_layout = QVBoxLayout(releases_page)
                    
                # Add the tree to the page
                releases_page.layout().addWidget(tree)
                
                # Switch to the releases page
                stacked_widget.setCurrentWidget(releases_page)
            else:
                # If no specific page found, add to main layout
                self.layout().insertWidget(self.layout().count() - 1, tree)
        else:
            # No stacked widget, add to main layout
            self.layout().insertWidget(self.layout().count() - 1, tree)
        
        # Store reference to tree widget
        self.tree_widget = tree
        
        return tree

        
    def show_release_context_menu(self, position):
        """Show context menu for releases in tree view"""
        if not hasattr(self, 'tree_widget'):
            return
            
        # Get the item at position
        item = self.tree_widget.itemAt(position)
        if not item:
            return
            
        # Create context menu
        menu = QMenu(self)
        
        # Check if this is a release item (has parent) or an artist item
        if item.parent():
            # This is a release item
            release_data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if release_data:
                # Add actions for release
                open_muspy_action = QAction("View on Muspy", self)
                open_muspy_action.triggered.connect(lambda: self.open_muspy_release(release_data))
                menu.addAction(open_muspy_action)
                
                # Check if MusicBrainz ID is available
                if 'mbid' in release_data:
                    open_mb_action = QAction("View on MusicBrainz", self)
                    open_mb_action.triggered.connect(lambda: self.open_musicbrainz_release(release_data))
                    menu.addAction(open_mb_action)
        else:
            # This is an artist item
            artist_name = item.text(0)
            
            follow_action = QAction(f"Follow {artist_name} on Muspy", self)
            follow_action.triggered.connect(lambda: self.follow_artist_from_tree(artist_name))
            menu.addAction(follow_action)
            
            # Add more artist actions as needed
        
        # Show the menu
        menu.exec(self.tree_widget.mapToGlobal(position))

    def open_muspy_release(self, release_data):
        """Open a release on Muspy website"""
        if 'mbid' in release_data:
            url = f"https://muspy.com/release/{release_data['mbid']}"
            import webbrowser
            webbrowser.open(url)

    def open_musicbrainz_release(self, release_data):
        """Open a release on MusicBrainz website"""
        if 'mbid' in release_data:
            url = f"https://musicbrainz.org/release/{release_data['mbid']}"
            import webbrowser
            webbrowser.open(url)

    def follow_artist_from_tree(self, artist_name):
        """Follow an artist from the tree view"""
        # First get the MBID
        mbid = self.get_mbid_artist_searched(artist_name)
        
        if mbid:
            # Store current artist
            self.current_artist = {"name": artist_name, "mbid": mbid}
            
            # Follow the artist
            success = self.add_artist_to_muspy(mbid, artist_name)
            
            if success:
                QMessageBox.information(self, "Success", f"Now following {artist_name} on Muspy")
            else:
                QMessageBox.warning(self, "Error", f"Could not follow {artist_name} on Muspy")
        else:
            QMessageBox.warning(self, "Error", f"Could not find MBID for {artist_name}")

    def on_release_double_clicked(self, item, column):
        """Handle double-click on a tree item"""
        # Check if this is a release item
        if item.parent():
            # This is a release, get its data
            release_data = item.data(0, Qt.ItemDataRole.UserRole)
            if release_data and 'mbid' in release_data:
                self.open_musicbrainz_release(release_data)



    def _fallback_artist_selection_dialog(self, dialog, artists_data, existing_names):
        """
        Método de respaldo para crear el diálogo de selección de artistas manualmente
        si el archivo UI no se encuentra.
        
        Args:
            dialog (QDialog): Diálogo a configurar
            artists_data (list): Lista de datos de artistas
            existing_names (set): Conjunto de nombres de artistas existentes
        """
        dialog.setWindowTitle("Seleccionar Artistas")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(600)
        
        # Layout principal
        layout = QVBoxLayout(dialog)
        
        # Etiqueta informativa
        info_label = QLabel(f"Selecciona los artistas que deseas guardar ({len(artists_data)} encontrados)")
        layout.addWidget(info_label)
        
        # Campo de búsqueda
        search_layout = QHBoxLayout()
        search_label = QLabel("Buscar:")
        search_input = QLineEdit()
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_input)
        layout.addLayout(search_layout)
        
        # Área de scroll con checkboxes
        scroll_area = QWidget()
        scroll_layout = QVBoxLayout(scroll_area)
        
        # Lista para almacenar los checkboxes
        checkboxes = []
        
        # Crear un checkbox para cada artista
        for artist in artists_data:
            checkbox = QCheckBox(f"{artist['nombre']} ({artist['mbid']})")
            checkbox.setChecked(artist['nombre'] in existing_names)  # Pre-seleccionar si ya existe
            checkbox.setProperty("artist_data", artist)  # Almacenar datos del artista en el checkbox
            checkboxes.append(checkbox)
            scroll_layout.addWidget(checkbox)
        
        # Crear área de desplazamiento
        scroll_widget = QScrollArea()
        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(scroll_area)
        layout.addWidget(scroll_widget)
        
        # Botones de selección
        button_layout = QHBoxLayout()
        select_all_button = QPushButton("Seleccionar Todos")
        deselect_all_button = QPushButton("Deseleccionar Todos")
        button_layout.addWidget(select_all_button)
        button_layout.addWidget(deselect_all_button)
        layout.addLayout(button_layout)
        
        # Botones de aceptar/cancelar
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)
        
        # Guardamos referencias para acceder a ellos desde otras funciones
        dialog.scroll_layout = scroll_layout
        dialog.search_input = search_input
        dialog.select_all_button = select_all_button
        dialog.deselect_all_button = deselect_all_button
        dialog.buttons = buttons
        
        # Conectar señales
        search_input.textChanged.connect(lambda text: self.filter_artists(text, checkboxes))
        select_all_button.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes if cb.isVisible()])
        deselect_all_button.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes if cb.isVisible()])
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)



    def search_and_get_releases(self):
        """Search for artist releases without adding to Muspy - revisada para cambiar a la página correcta"""
        artist_name = self.artist_input.text().strip()
        if not artist_name:
            QMessageBox.warning(self, "Error", "Please enter an artist name")
            return

        # Ensure we start with text page visible for status updates
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Searching for releases by {artist_name}...")
        QApplication.processEvents()

        # Get MBID for the artist
        mbid = self.get_mbid_artist_searched(artist_name)
        
        if not mbid:
            QMessageBox.warning(self, "Error", f"Could not find MusicBrainz ID for {artist_name}")
            return
        
        # Store the current artist for possible addition later
        self.current_artist = {"name": artist_name, "mbid": mbid}
        
        # Get releases for the artist
        self.get_artist_releases(mbid, artist_name)

    def search_album_mbid(self):
        """
        Search for album MBID from the database
        Shows a dialog with album search results and allows selection
        """
        # Get search term
        search_term, ok = QInputDialog.getText(
            self, "Search Album", "Enter album name to search:"
        )
        
        if not ok or not search_term.strip():
            return
            
        # Show searching indicator
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append(f"Searching for album: {search_term}...")
        QApplication.processEvents()
        
        try:
            # Use consultar_items_db to search
            if not os.path.isabs(self.db_path):
                full_db_path = os.path.join(PROJECT_ROOT, self.db_path)
            else:
                full_db_path = self.db_path
                
            # Build the command - search for albums
            script_path = os.path.join(PROJECT_ROOT, "base_datos", "tools", "consultar_items_db.py")
            cmd = f"python {script_path} --db {full_db_path} --buscar albums --limite 100"
            
            # Run the command
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.results_text.append(f"Error searching albums: {result.stderr}")
                return
                
            # Parse the results
            albums = json.loads(result.stdout)
            
            # Filter by search term
            search_term = search_term.lower()
            matching_albums = []
            
            for album in albums:
                album_name = album.get('album', '').lower()
                artist_name = album.get('artista', '').lower()
                
                if search_term in album_name or search_term in artist_name:
                    matching_albums.append(album)
            
            if not matching_albums:
                self.results_text.append("No matching albums found.")
                return
                
            # Create a dialog to display results
            dialog = QDialog(self)
            dialog.setWindowTitle("Album Search Results")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(400)
            
            # Layout
            layout = QVBoxLayout(dialog)
            
            # Tree widget for results
            tree = QTreeWidget()
            tree.setHeaderLabels(["Album", "Artist", "MBID"])
            tree.setColumnCount(3)
            tree.setAlternatingRowColors(True)
            
            # Add albums to tree
            for album in matching_albums:
                item = QTreeWidgetItem(tree)
                item.setText(0, album.get('album', 'Unknown'))
                item.setText(1, album.get('artista', 'Unknown'))
                item.setText(2, album.get('mbid', 'None'))
                
                # Store album data
                item.setData(0, Qt.ItemDataRole.UserRole, album)
            
            # Resize columns
            for i in range(3):
                tree.resizeColumnToContents(i)
                
            layout.addWidget(tree)
            
            # Buttons
            button_layout = QHBoxLayout()
            select_button = QPushButton("Get Releases")
            cancel_button = QPushButton("Cancel")
            
            button_layout.addWidget(select_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            # Connect signals
            select_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            # Store tree in dialog
            dialog.tree = tree
            
            # Show dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get selected album
                selected_items = tree.selectedItems()
                if selected_items:
                    selected_album = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
                    album_mbid = selected_album.get('mbid')
                    
                    if album_mbid:
                        # Get releases using the album MBID
                        self.get_releases_by_album_mbid(album_mbid, selected_album.get('album'), selected_album.get('artista'))
                    else:
                        QMessageBox.warning(self, "Error", "Selected album does not have a MusicBrainz ID.")
        
        except Exception as e:
            self.results_text.append(f"Error searching albums: {str(e)}")
            self.logger.error(f"Error in search_album_mbid: {e}", exc_info=True)



    def get_releases_by_album_mbid(self, album_mbid, album_name=None, artist_name=None):
        """
        Get releases for an album by its MusicBrainz ID
        
        Args:
            album_mbid (str): MusicBrainz ID of the album
            album_name (str, optional): Name of the album for display
            artist_name (str, optional): Name of the artist for display
        """
        if not self.muspy_username or not self.muspy_api_key:
            QMessageBox.warning(self, "Error", "Muspy configuration not available")
            return

        try:
            # Clear results and show status
            self.results_text.clear()
            self.results_text.show()
            self.results_text.append(f"Getting releases for album: {album_name or album_mbid}...")
            QApplication.processEvents()
            
            # API query
            url = f"{self.base_url}/releases"
            params = {"since": album_mbid}
            auth = (self.muspy_username, self.muspy_api_key)
            
            response = requests.get(url, auth=auth, params=params)
            
            if response.status_code == 200:
                all_releases = response.json()
                
                # Filter for future releases
                today = datetime.date.today().strftime("%Y-%m-%d")
                future_releases = [release for release in all_releases if release.get('date', '0000-00-00') >= today]
                
                if not future_releases:
                    self.results_text.append(f"No future releases found for {album_name or 'this album'}")
                    if all_releases:
                        self.results_text.append(f"Found {len(all_releases)} past releases.")
                        
                        # Ask if user wants to see past releases
                        reply = QMessageBox.question(
                            self, 
                            "Show Past Releases", 
                            f"No future releases found, but there are {len(all_releases)} past releases. Do you want to see them?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        
                        if reply == QMessageBox.StandardButton.Yes:
                            # Show past releases in tree view
                            self.display_releases_tree(all_releases)
                    return
                
                # Display releases in tree view
                self.display_releases_tree(future_releases)
                
                # If we have artist information, store it for possible follow action
                if artist_name:
                    # Get artist MBID
                    artist_mbid = self.get_mbid_artist_searched(artist_name)
                    if artist_mbid:
                        self.current_artist = {"name": artist_name, "mbid": artist_mbid}
                        
                        # Add a button to follow this artist
                        self.add_follow_button = QPushButton(f"Follow {artist_name} on Muspy")
                        self.add_follow_button.clicked.connect(self.follow_current_artist)
                        self.layout().insertWidget(self.layout().count() - 1, self.add_follow_button)
            else:
                self.results_text.append(f"Error retrieving releases: {response.status_code} - {response.text}")
        
        except Exception as e:
            self.results_text.append(f"Connection error with Muspy: {e}")
            self.logger.error(f"Error getting releases by album MBID: {e}", exc_info=True)

    def get_artist_releases(self, mbid, artist_name=None):
        """
        Get future releases for a specific artist by MBID - adaptado para usar muspy_results
        
        Args:
            mbid (str): MusicBrainz ID of the artist
            artist_name (str, optional): Name of the artist for display
        """
        if not self.muspy_username or not self.muspy_api_key:
            QMessageBox.warning(self, "Error", "Muspy configuration not available")
            return

        try:
            # Asegurarnos de mostrar la página de texto para actualizaciones
            self.show_text_page()
            self.results_text.append(f"Getting releases for {artist_name or 'artist'}...")
            QApplication.processEvents()
            
            url = f"{self.base_url}/releases"
            params = {"mbid": mbid}
            auth = (self.muspy_username, self.muspy_api_key)
            
            response = requests.get(url, auth=auth, params=params)
            
            if response.status_code == 200:
                all_releases = response.json()
                
                # Filter for future releases
                today = datetime.date.today().strftime("%Y-%m-%d")
                future_releases = [release for release in all_releases if release.get('date', '0000-00-00') >= today]
                
                if not future_releases:
                    self.results_text.append(f"No future releases found for {artist_name or 'Unknown'}")
                    return
                
                # Log releases for debugging
                self.logger.info(f"Received {len(future_releases)} future releases out of {len(all_releases)} total")
                if future_releases:
                    self.logger.info(f"Sample release data: {future_releases[0]}")
                
                # Usar la página muspy_results
                self.display_releases_in_muspy_results_page(future_releases, artist_name)
                
                # Add a button to follow this artist
                self.add_follow_button_to_results_page(artist_name)
            else:
                self.results_text.append(f"Error retrieving releases: {response.status_code} - {response.text}")
        
        except Exception as e:
            self.results_text.append(f"Connection error with Muspy: {e}")
            self.logger.error(f"Error getting releases: {e}")

    def follow_current_artist(self):
        """Follow the currently displayed artist"""
        # Check if we have a current artist
        if not hasattr(self, 'current_artist') or not self.current_artist:
            self.logger.error("No current artist to follow")
            QMessageBox.warning(self, "Error", "No artist currently selected")
            return
        
        # Log the attempt
        self.logger.info(f"Attempting to follow artist: {self.current_artist.get('name')}, MBID: {self.current_artist.get('mbid')}")
        
        # No need to get the Muspy ID, we should already have it from config
        if not self.muspy_id:
            self.logger.error("Muspy ID not available")
            QMessageBox.warning(self, "Error", "Muspy ID not available. Please check your configuration.")
            return
        
        # Follow the artist
        success = self.add_artist_to_muspy(self.current_artist.get("mbid"), self.current_artist.get("name"))
        
        # Update UI based on result
        if success:
            # Find and update the appropriate button
            stack_widget = self.findChild(QStackedWidget, "stackedWidget")
            if stack_widget:
                current_page = stack_widget.currentWidget()
                if current_page and current_page.objectName() == "muspy_results_widget":
                    follow_button = current_page.findChild(QPushButton, "follow_artist_button")
                    if follow_button:
                        follow_button.setText(f"Siguiendo a {self.current_artist.get('name')} en Muspy")
                        follow_button.setEnabled(False)
                        self.logger.debug("Updated follow button in results widget")
            
            # Also update any standalone button
            if hasattr(self, 'add_follow_button'):
                self.add_follow_button.setText(f"Siguiendo a {self.current_artist.get('name')} en Muspy")
                self.add_follow_button.setEnabled(False)
                self.logger.debug("Updated standalone follow button")
            
            QMessageBox.information(self, "Success", f"Now following {self.current_artist.get('name')} on Muspy")

    def get_new_releases(self, PROJECT_ROOT):
        """
        Retrieve new releases using the Muspy API endpoint
        Gets a list of album MBIDs from a local script and checks for new releases since each album
        Displays new releases in the stacked widget
        """
        if not os.path.isabs(self.db_path):
            full_db_path = os.path.join(PROJECT_ROOT, self.db_path)
        else:
            full_db_path = self.db_path
        
        script_path = os.path.join(PROJECT_ROOT, "base_datos", "tools", "consultar_items_db.py")
        
        # Define the operation to run with progress monitoring
        def fetch_new_releases(update_progress):
            update_progress(0, 1, "Ejecutando consulta a la base de datos...", indeterminate=True)
            
            try:
                # Execute the script to get albums
                cmd = f"python {script_path} --db {full_db_path} --ultimos --limite 500"
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return {
                        "success": False, 
                        "error": f"Error ejecutando el script: {result.stderr}"
                    }
                
                # Parse album data
                try:
                    albums = json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "Error al parsear la respuesta del script"
                    }
                
                if not albums:
                    return {
                        "success": False,
                        "error": "No se encontraron álbumes en la base de datos"
                    }
                
                update_progress(1, len(albums) + 1, f"Procesando {len(albums)} álbumes...")
                
                # Lista para almacenar todos los nuevos lanzamientos
                all_new_releases = []
                
                # Consultar a muspy por cada MBID
                for i, album in enumerate(albums):
                    mbid = album.get('mbid')
                    if not mbid:
                        continue
                    
                    update_progress(i + 1, len(albums) + 1, f"Consultando álbum {i+1}/{len(albums)}: {album.get('album', 'Desconocido')}")
                    
                    # Construir la URL con el parámetro 'since'
                    url = f"{self.base_url}/releases"
                    params = {'since': mbid}
                    auth = (self.muspy_username, self.muspy_api_key)
                    
                    response = requests.get(url, params=params, auth=auth)
                    
                    if response.status_code == 200:
                        releases = response.json()
                        # Filtrar lanzamientos futuros
                        today = datetime.date.today().strftime("%Y-%m-%d")
                        future_releases = [release for release in releases if release.get('date', '0000-00-00') >= today]
                        
                        # Agregar a la lista de todos los lanzamientos
                        all_new_releases.extend(future_releases)
                
                # Eliminar duplicados (si el mismo lanzamiento aparece para varios álbumes)
                unique_releases = []
                seen_ids = set()
                for release in all_new_releases:
                    if release.get('mbid') not in seen_ids:
                        seen_ids.add(release.get('mbid'))
                        unique_releases.append(release)
                
                # Ordenar por fecha
                unique_releases.sort(key=lambda x: x.get('date', '0000-00-00'))
                
                update_progress(len(albums) + 1, len(albums) + 1, "Procesamiento completado")
                
                return {
                    "success": True,
                    "releases": unique_releases
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error al obtener nuevos lanzamientos: {str(e)}"
                }
        
        # Run the operation with progress dialog
        result = self.show_progress_operation(
            fetch_new_releases,
            title="Buscando Nuevos Lanzamientos",
            label_format="{status}"
        )
        
        if result:
            if result.get("success"):
                releases = result.get("releases", [])
                
                if not releases:
                    QMessageBox.information(self, "No New Releases", "No new releases available")
                    return
                
                # Show releases in stacked widget
                self.display_releases_in_stacked_widget(releases)
            else:
                error_msg = result.get("error", "Unknown error")
                QMessageBox.warning(self, "Error", error_msg)

    def sync_artists_with_muspy(self):
        """Synchronize artists from JSON file with Muspy using progress bar"""
        # Ruta al archivo JSON
        json_path = os.path.join(PROJECT_ROOT, ".content", "cache", "artists_selected.json")
        
        # Verificar si el archivo existe
        if not os.path.exists(json_path):
            error_msg = "El archivo artists_selected.json no existe."
            self.results_text.append(error_msg)
            QMessageBox.warning(self, "Error", error_msg)
            return
        
        # Leer el archivo JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
        except Exception as e:
            error_msg = f"Error al leer el archivo JSON: {e}"
            self.results_text.append(error_msg)
            QMessageBox.warning(self, "Error", error_msg)
            return
        
        # Verificar si hay artistas en el JSON
        if not artists_data:
            error_msg = "No hay artistas en el archivo JSON."
            self.results_text.append(error_msg)
            QMessageBox.warning(self, "Error", error_msg)
            return
        
        # Función para procesar los artistas con progreso
        def process_artists(update_progress, artists_data):
            total_artists = len(artists_data)
            
            # Variables para llevar el conteo
            results = {
                "successful_adds": 0,
                "failed_adds": 0,
                "duplicates": 0
            }
            
            # Actualizar inicialmente
            update_progress(0, total_artists, "Preparando sincronización...")
            
            # Procesar artistas
            for i, artist_data in enumerate(artists_data):
                # Comprobar si se canceló
                if not update_progress(i, total_artists, f"Procesando {artist_data.get('nombre', 'Desconocido')}"):
                    return {**results, "canceled": True}
                
                try:
                    # Obtener el nombre y MBID directamente del JSON
                    artist_name = artist_data.get("nombre", "")
                    mbid = artist_data.get("mbid", "")
                    
                    # Intentar añadir el artista con el MBID proporcionado
                    if mbid:
                        response = self.add_artist_to_muspy_silent(mbid, artist_name)
                        if response == 1:
                            results["successful_adds"] += 1
                        elif response == 0:
                            results["duplicates"] += 1
                        else:
                            results["failed_adds"] += 1
                    else:
                        self.logger.error(f"MBID no válido para el artista {artist_name}")
                        results["failed_adds"] += 1
                
                except Exception as e:
                    self.logger.error(f"Error al sincronizar artista {artist_name if 'artist_name' in locals() else 'desconocido'}: {e}")
                    results["failed_adds"] += 1
                    
            # Actualizar con el resultado final
            update_progress(total_artists, total_artists, "Sincronización completada")
            return results
        
        # Ejecutar con el diálogo de progreso
        results = self.show_progress_operation(
            process_artists, 
            operation_args={"artists_data": artists_data},
            title="Sincronizando Artistas",
            label_format="Artista {current} de {total} - {status}",
            finish_message=None  # Personalizar luego
        )
        
        # Comprobar si fue cancelado
        if results and results.get("canceled"):
            self.results_text.append("Sincronización cancelada por el usuario.")
            return
        
        # Mostrar el resumen final solo si no se canceló
        if results:
            # Construir mensaje de resultados
            finish_message = (
                f"Sincronización completada\n\n"
                f"Total artistas procesados: {len(artists_data)}\n"
                f"Añadidos correctamente: {results['successful_adds']}\n"
                f"Duplicados (ya existían): {results['duplicates']}\n"
                f"Fallos: {results['failed_adds']}"
            )
            
            # Mostrar en la interfaz
            self.results_text.clear()
            self.results_text.append(finish_message)
            
            # Mostrar popup con resultados
            QMessageBox.information(
                self, 
                "Sincronización Completa", 
                finish_message.replace("\n\n", "\n")
            )

  

    def get_mbid_artist_searched(self, artist_name):
        """
        Retrieve the MusicBrainz ID for a given artist
        
        Args:
            artist_name (str): Name of the artist to search
        
        Returns:
            str or None: MusicBrainz ID of the artist
        """
        if artist_name is None:
            return None
        
        try:
            # First attempt: query existing database
            if self.query_db_script_path:
                # Add full absolute paths
                full_db_path = os.path.expanduser(self.db_path) if self.db_path else None
                full_script_path = os.path.expanduser(self.query_db_script_path)
                
                # Log the search
                self.results_text.append(f"Searching for MBID for {artist_name}...")
                logger.debug(f"Script Path: {full_script_path}")
                logger.debug(f"DB Path: {full_db_path}")
                logger.debug(f"Artist: {artist_name}")

                # Try to find the artist in the database
                mbid_result = subprocess.run(
                    ['python', full_script_path, "--db", full_db_path, "--artist", artist_name, "--mbid"], 
                    capture_output=True, 
                    text=True
                )
                
                # Check if the output contains an error message
                if mbid_result.returncode == 0 and mbid_result.stdout.strip():
                    # Clean the result
                    mbid = mbid_result.stdout.strip().strip('"\'')
                    # Verify that the MBID looks valid (should be a UUID)
                    if len(mbid) == 36 and mbid.count('-') == 4:
                        logger.debug(f"MBID found in database: {mbid}")
                        return mbid
                
                # If we didn't find the MBID in the database, try searching MusicBrainz directly
                self.results_text.append(f"Searching MusicBrainz for {artist_name}...")
                QApplication.processEvents()
                
                # Use the MusicBrainz API directly
                try:
                    import requests
                    url = "https://musicbrainz.org/ws/2/artist/"
                    params = {
                        "query": f"artist:{artist_name}",
                        "fmt": "json"
                    }
                    headers = {
                        "User-Agent": "MuspyReleasesModule/1.0"
                    }
                    
                    response = requests.get(url, params=params, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "artists" in data and data["artists"]:
                            # Get the first artist result
                            artist = data["artists"][0]
                            mbid = artist.get("id")
                            
                            if mbid and len(mbid) == 36 and mbid.count('-') == 4:
                                self.results_text.append(f"MBID found on MusicBrainz: {mbid}")
                                return mbid
                except Exception as e:
                    logger.error(f"Error searching MusicBrainz API: {e}")
            
            self.results_text.append(f"Could not find MBID for {artist_name}")
            return None
        
        except Exception as e:
            self.results_text.append(f"Error searching for MBID: {e}")
            logger.error(f"Error getting MBID for {artist_name}: {e}", exc_info=True)
            return None
 
    def add_artist_to_muspy_silent(self, mbid, artist_name=None):
        """
        Add artist to Muspy without showing dialog boxes
        
        Args:
            mbid (str): MusicBrainz ID of the artist
            artist_name (str, optional): Name of the artist for logging
        
        Returns:
            int: 1 for success, 0 for already exists, -1 for error
        """
        if not self.muspy_username or not self.muspy_api_key or not self.muspy_id:
            return -1

        try:
            # Use the same URL format as the working curl command
            url = f"https://muspy.com/api/1/artists/{self.muspy_id}/{mbid}"
            auth = (self.muspy_username, self.muspy_password)
            
            # Check if artist already exists first
            check_response = requests.get(url, auth=auth)
            
            # If status code is 200, artist already exists
            if check_response.status_code == 200:
                return 0  # Already exists
            
            # Otherwise, add the artist
            response = requests.put(url, auth=auth)
            
            if response.status_code in [200, 201]:
                return 1  # Success
            else:
                self.logger.error(f"Error adding artist {artist_name or mbid} to Muspy: {response.status_code} - {response.text}")
                return -1  # Error
        except Exception as e:
            self.logger.error(f"Error adding artist {artist_name or mbid} to Muspy: {e}")
            return -1  # Error



    def add_artist_to_muspy(self, mbid=None, artist_name=None):
        """
        Add/Follow an artist to Muspy using their MBID - fixed to match working curl pattern
        
        Args:
            mbid (str, optional): MusicBrainz ID of the artist
            artist_name (str, optional): Name of the artist for logging
        
        Returns:
            bool: True if artist was successfully added, False otherwise
        """
        if not self.muspy_username or not self.muspy_api_key:
            self.logger.error("Muspy credentials not configured")
            return False

        if not mbid:
            self.logger.error(f"No MBID provided for {artist_name or 'Unknown'}")
            return False

        # Ensure muspy_id is available
        if not self.muspy_id:
            self.get_muspy_id()
            if not self.muspy_id:
                self.logger.error("Could not get Muspy ID")
                return False

        try:
            # Use exactly the same URL format as in the working curl command
            url = f"https://muspy.com/api/1/artists/{self.muspy_id}/{mbid}"
            
            # Use the same authentication method
            auth = (self.muspy_username, self.muspy_password)
            
            # Use a PUT request with no body, exactly like the curl command
            response = requests.put(url, auth=auth)
            
            # Log detailed information for debugging
            self.logger.debug(f"PUT request to {url}")
            self.logger.debug(f"Using auth: {self.muspy_username}:***")
            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response text: {response.text}")
            
            if response.status_code in [200, 201]:
                self.logger.info(f"Successfully added {artist_name or mbid} to Muspy")
                return True
            else:
                self.logger.error(f"Error adding artist to Muspy: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Exception adding artist to Muspy: {e}", exc_info=True)
            return False

    def sync_lastfm_muspy(self):
        """Synchronize Last.fm artists with Muspy"""
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "Last.fm username not configured")
            return

        if not self.muspy_id:
            # Try to get the Muspy ID if it's not set
            self.get_muspy_id()
            if not self.muspy_id:
                QMessageBox.warning(self, "Error", "Could not get Muspy ID. Please check your credentials.")
                return

        # Clear the results area and make sure it's visible
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append(f"Starting Last.fm synchronization for user {self.lastfm_username}...\n")
        QApplication.processEvents()  # Update UI

        try:
            # First try direct API import
            import_url = f"{self.base_url}/import/{self.muspy_id}"
            auth = (self.muspy_username, self.muspy_api_key)
            
            import_data = {
                'type': 'lastfm',
                'username': self.lastfm_username,
                'count': 50,  # Import more artists
                'period': 'overall'
            }
            
            self.results_text.append("Sending request to Muspy API...")
            QApplication.processEvents()
            
            # Use POST for the import endpoint
            response = requests.post(import_url, auth=auth, json=import_data)
            
            if response.status_code in [200, 201]:
                self.results_text.append(f"Successfully synchronized artists from Last.fm account {self.lastfm_username}")
                self.results_text.append("You can now view your upcoming releases using the 'Mis próximos discos' button")
                return True
            else:
                # If direct API fails, try using our LastFM manager as fallback
                self.results_text.append("Direct API import failed. Trying alternative method...")
                return self.sync_top_artists_from_lastfm()
        except Exception as e:
            error_msg = f"Error syncing with Muspy API: {e}"
            self.results_text.append(error_msg)
            self.logger.error(error_msg, exc_info=True)
            
            # Try alternative method
            self.results_text.append("Trying alternative synchronization method...")
            return self.sync_top_artists_from_lastfm()


    def unfollow_artist_from_muspy(self, mbid, artist_name=None):
        """
        Unfollow an artist from Muspy using the DELETE API endpoint
        
        Args:
            mbid (str): MusicBrainz ID of the artist to unfollow
            artist_name (str, optional): Artist name for display purposes
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.muspy_username or not self.muspy_api_key or not self.muspy_id:
            self.logger.error("Muspy credentials not configured")
            return False

        try:
            # Use the DELETE endpoint as specified in the API docs
            url = f"{self.base_url}/artists/{self.muspy_id}/{mbid}"
            auth = (self.muspy_username, self.muspy_api_key)
            
            # Make the DELETE request
            response = requests.delete(url, auth=auth)
            
            # Log response details for debugging
            self.logger.debug(f"DELETE request to {url}")
            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response text: {response.text}")
            
            if response.status_code in [200, 204]:
                artist_display = artist_name or mbid
                self.logger.info(f"Successfully unfollowed {artist_display} from Muspy")
                return True
            else:
                self.logger.error(f"Error unfollowing artist from Muspy: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Exception unfollowing artist from Muspy: {e}", exc_info=True)
            return False

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



    def get_muspy_releases(self, use_cached=True):
        """
        Retrieve future releases from Muspy for the current user with caching support
        
        Args:
            use_cached (bool): Whether to use cached data when available
        """
        if not self.muspy_username or not self.muspy_api_key:
            QMessageBox.warning(self, "Error", "Muspy configuration not available")
            return

        if not self.muspy_id:
            # Try to get the Muspy ID if it's not set
            self.get_muspy_id()
            if not self.muspy_id:
                QMessageBox.warning(self, "Error", "Could not get Muspy ID. Please check your credentials.")
                return

        # Try to get from cache first if allowed
        cache_key = f"muspy_releases_{self.muspy_id}"
        if use_cached:
            cached_data = self.cache_manager(cache_key, expiry_hours=12)  # Shorter expiry for releases
            if cached_data:
                future_releases = cached_data.get("future_releases", [])
                if future_releases:
                    self.display_releases_in_stacked_widget(future_releases)
                    return
                elif cached_data.get("all_releases"):
                    QMessageBox.information(self, "No Future Releases", 
                        f"No se encontraron próximos lanzamientos en Muspy.\n" +
                        f"(Total de lanzamientos pasados: {len(cached_data.get('all_releases', []))})")
                    return

        # Función de operación con progreso
        def fetch_releases(update_progress):
            update_progress(0, 1, "Conectando con Muspy API...", indeterminate=True)
            
            try:
                # Use proper endpoint with the user ID
                url = f"{self.base_url}/releases/{self.muspy_id}"
                auth = (self.muspy_username, self.muspy_api_key)
                
                response = requests.get(url, auth=auth)
                
                if response.status_code == 200:
                    # Procesando datos
                    update_progress(1, 2, "Procesando resultados...", indeterminate=True)
                    
                    all_releases = response.json()
                    
                    # Filter for future releases
                    today = datetime.date.today().strftime("%Y-%m-%d")
                    future_releases = [release for release in all_releases if release.get('date', '0000-00-00') >= today]
                    
                    # Cache the results
                    cache_data = {
                        "all_releases": all_releases,
                        "future_releases": future_releases
                    }
                    self.cache_manager(cache_key, cache_data, expiry_hours=12)
                    
                    # Actualizar progreso y terminar
                    update_progress(2, 2, "Generando visualización...")
                    
                    return {
                        "success": True,
                        "all_releases": all_releases,
                        "future_releases": future_releases
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Error retrieving releases: {response.status_code} - {response.text}"
                    }
            
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Connection error with Muspy: {e}"
                }
        
        # Ejecutar con diálogo de progreso
        result = self.show_progress_operation(
            fetch_releases,
            title="Obteniendo Próximos Lanzamientos",
            label_format="{status}"
        )
        
        # Procesar resultados
        if result:
            if result.get("success"):
                future_releases = result.get("future_releases", [])
                all_releases = result.get("all_releases", [])
                
                if not future_releases:
                    QMessageBox.information(self, "No Future Releases", 
                        f"No se encontraron próximos lanzamientos en Muspy.\n" +
                        f"(Total de lanzamientos: {len(all_releases)})")
                    return
                
                # Display releases properly using stacked widget
                self.display_releases_in_stacked_widget(future_releases)
            else:
                error_msg = result.get("error", "Unknown error")
                QMessageBox.warning(self, "Error", error_msg)
   
    def display_releases_in_stacked_widget(self, releases):
        """
        Display releases in the proper page of the stacked widget
        
        Args:
            releases (list): List of release dictionaries
        """
        # Find the stacked widget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            # Fallback if stacked widget not found
            self.logger.error("Stacked widget not found in UI")
            self.display_releases_table(releases)
            return
        
        # Find the releases table page
        releases_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "releases_page":
                releases_page = widget
                break
        
        if not releases_page:
            # Fallback if page not found
            self.logger.error("Releases page not found in stacked widget")
            self.display_releases_table(releases)
            return
        
        # Get the table widget from the releases page
        table = releases_page.findChild(QTableWidget, "releases_table")
        if not table:
            self.logger.error("Releases table not found in releases page")
            return
        
        # Get count label
        count_label = releases_page.findChild(QLabel, "count_label")
        if count_label:
            count_label.setText(f"Showing {len(releases)} upcoming releases")
        
        # Configure table
        table.setRowCount(len(releases))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table
        self._fill_releases_table(table, releases)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
        
        # Switch to the releases page - this will fully hide the text page
        stack_widget.setCurrentWidget(releases_page)

    
    
    
    def show_text_page(self, html_content=None):
        """
        Switch to the text page and optionally update its content
        
        Args:
            html_content (str, optional): HTML content to display
        """
        # Find the stacked widget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            # Asegurarnos de que results_text es visible como fallback
            if hasattr(self, 'results_text'):
                self.results_text.show()
            return
        
        # Find the text page
        text_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "text_page":
                text_page = widget
                break
        
        if not text_page:
            self.logger.error("text_page not found in stacked widget")
            # Asegurarnos de que results_text es visible como fallback
            if hasattr(self, 'results_text'):
                self.results_text.show()
            return
        
        # Update content if provided
        if html_content and hasattr(self, 'results_text'):
            self.results_text.setHtml(html_content)
        
        # Switch to text page
        stack_widget.setCurrentWidget(text_page)
        
        # Asegurarnos de que results_text es visible dentro de text_page
        if hasattr(self, 'results_text'):
            self.results_text.setVisible(True)
   

    def display_releases_in_muspy_results_page(self, releases, artist_name=None):
        """
        Muestra los lanzamientos en la página específica de resultados de Muspy
        
        Args:
            releases (list): Lista de lanzamientos
            artist_name (str, optional): Nombre del artista para el título
        """
        # Find the stacked widget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            # Fallback a la función original si no encontramos el widget
            self.display_releases_table(releases)
            return
        
        # Find the muspy_results page - CHANGED TO MATCH UI OBJECT NAME
        results_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "muspy_results_widget":  # Updated object name
                results_page = widget
                break
        
        if not results_page:
            self.logger.error("muspy_results_widget page not found in stacked widget")
            # Log more details for debugging
            self.logger.error(f"Available pages in stackedWidget ({stack_widget.count()}):")
            for i in range(stack_widget.count()):
                widget = stack_widget.widget(i)
                self.logger.error(f"  - Page {i}: {widget.objectName()}")            
            
            # Fallback a la función original si no encontramos la página
            self.display_releases_table(releases)
            return
        
        # Get the table widget and count label from the results page
        table = results_page.findChild(QTableWidget, "tableWidget_muspy_results")
        count_label = results_page.findChild(QLabel, "label_result_count")
        
        if not table:
            self.logger.error("tableWidget_muspy_results not found in results page")
            return
        
        # Update count label if exists
        if count_label:
            count_label.setText(f"Showing {len(releases)} upcoming releases for {artist_name or 'artist'}")
        
        # Configure table
        table.setRowCount(len(releases))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table
        self._fill_releases_table(table, releases)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
        
        # Switch to the results page
        stack_widget.setCurrentWidget(results_page)


    def add_follow_button_to_results_page(self, artist_name):
        """
        Añade un botón para seguir al artista actual en la página de resultados
        
        Args:
            artist_name (str): Nombre del artista
        """
        # Find the muspy_results page
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("stackedWidget not found")
            return
        
        results_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "muspy_results_widget":
                results_page = widget
                break
        
        if not results_page:
            self.logger.error("muspy_results_widget page not found")
            return
        
        # Buscar un botón existente o crear uno nuevo
        follow_button = results_page.findChild(QPushButton, "follow_artist_button")
        
        if not follow_button:
            self.logger.info("Creating new follow button")
            # Si no existe, buscar un layout donde añadirlo
            layout = None
            
            # Look for the button container
            button_container = results_page.findChild(QWidget, "button_container")
            if button_container:
                for child in button_container.children():
                    if isinstance(child, QVBoxLayout) or isinstance(child, QHBoxLayout):
                        layout = child
                        break
            
            # If no specific container found, look for any layout
            if not layout:
                for child in results_page.children():
                    if isinstance(child, QVBoxLayout) or isinstance(child, QHBoxLayout):
                        layout = child
                        break
            
            if layout:
                # Crear el botón
                follow_button = QPushButton(f"Seguir a {artist_name} en Muspy")
                follow_button.setObjectName("follow_artist_button")
                layout.addWidget(follow_button)
            else:
                self.logger.error("No suitable layout found in muspy_results page for follow button")
                return
        else:
            # Si ya existe, actualizar el texto
            self.logger.info(f"Updating existing follow button for {artist_name}")
            follow_button.setText(f"Seguir a {artist_name} en Muspy")
        
        # Check if this artist is already being followed
        if hasattr(self, 'current_artist') and self.current_artist and self.current_artist.get('name') == artist_name:
            # Check with the API if we're already following this artist
            if self.muspy_id and self.current_artist.get('mbid'):
                url = f"{self.base_url}/artists/{self.muspy_id}/{self.current_artist['mbid']}"
                auth = (self.muspy_username, self.muspy_api_key)
                
                try:
                    response = requests.get(url, auth=auth)
                    if response.status_code == 200:
                        # We're already following this artist
                        follow_button.setText(f"Ya sigues a {artist_name} en Muspy")
                        follow_button.setEnabled(False)
                        return
                except:
                    # If check fails, assume we're not following
                    pass
        
        # Conectar el botón a la acción
        # Disconnect any previous connections to avoid multiple triggers
        try:
            follow_button.clicked.disconnect()
        except:
            pass
        
        follow_button.clicked.connect(self.follow_current_artist)
        follow_button.setEnabled(True)



    def get_all_my_releases(self):
        """
        Retrieve all releases for the user's artists using the user ID with progress bar
        """
        if not self.muspy_api_key:
            QMessageBox.warning(self, "Error", "Muspy ID not available. Please check your configuration.")
            return

        # Función de operación con progreso
        def fetch_all_releases(update_progress):
            # Valores iniciales
            all_releases = []
            offset = 0
            limit = 100  # Maximum allowed by API
            total_found = 0  # Lo actualizaremos después del primer lote
            more_releases = True
            batch_num = 1
            
            # Iniciar progreso indeterminado hasta que sepamos cuántos hay
            update_progress(0, 1, "Conectando con Muspy API...", indeterminate=True)
            
            try:
                while more_releases:
                    # Actualizar status
                    batch_status = f"Obteniendo lote {batch_num} (registros {offset+1}-{offset+limit})..."
                    
                    if total_found > 0:
                        # Ya conocemos el total aproximado
                        update_progress(len(all_releases), total_found, batch_status)
                    else:
                        # Todavía en modo indeterminado
                        update_progress(0, 1, batch_status, indeterminate=True)
                    
                    # Create URL with user ID, offset, and limit
                    url = f"{self.base_url}/releases/{self.muspy_id}"
                    params = {
                        "offset": offset,
                        "limit": limit
                    }
                    
                    # Make the request
                    response = requests.get(url, params=params)
                    
                    if response.status_code == 200:
                        batch_releases = response.json()
                        
                        if not batch_releases:
                            # No more releases to fetch
                            more_releases = False
                        else:
                            # Add to our collection and update offset
                            all_releases.extend(batch_releases)
                            offset += limit
                            batch_num += 1
                            
                            # Estimate total if we don't have it yet
                            if total_found == 0 and len(batch_releases) == limit:
                                # Si el primer lote está lleno, estimamos que podría haber
                                # al menos 5 veces ese tamaño (sobreestimación)
                                total_found = limit * 5
                            elif total_found == 0:
                                # Si el primer lote no está lleno, ya tenemos todos
                                total_found = len(batch_releases)
                            
                            # If we got fewer than the limit, we've reached the end
                            if len(batch_releases) < limit:
                                more_releases = False
                                # Update exact total
                                total_found = len(all_releases)
                    else:
                        return {
                            "success": False,
                            "error": f"Error retrieving releases: {response.status_code} - {response.text}"
                        }
                
                # Estamos procesando los resultados
                update_progress(1, 2, "Procesando resultados...", indeterminate=True)
                
                # Filter for future releases
                today = datetime.date.today().strftime("%Y-%m-%d")
                future_releases = [release for release in all_releases if release.get('date', '0000-00-00') >= today]
                
                # Sort releases by date
                future_releases.sort(key=lambda x: x.get('date', '9999-99-99'))
                
                # Completar la operación
                update_progress(2, 2, "Completado")
                
                return {
                    "success": True,
                    "all_releases": all_releases,
                    "future_releases": future_releases
                }
                
            except Exception as e:
                self.logger.error(f"Error getting all releases: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"Error obteniendo lanzamientos: {str(e)}"
                }
        
        # Ejecutar con el diálogo de progreso
        result = self.show_progress_operation(
            fetch_all_releases,
            title="Obteniendo Todos los Lanzamientos",
            label_format="{status}"
        )
        
        # Procesar resultados
        if result:
            if result.get("success"):
                all_releases = result.get("all_releases", [])
                future_releases = result.get("future_releases", [])
                
                # Mostrar resultados en la interfaz
                self.results_text.clear()
                self.results_text.append(f"Procesamiento completo. Encontrados {len(future_releases)} lanzamientos futuros de un total de {len(all_releases)} lanzamientos.")
                
                if not future_releases:
                    self.results_text.append("No se encontraron lanzamientos futuros para tus artistas.")
                    return
                
                # Display releases in table
                self.display_releases_table(future_releases)
            else:
                error_msg = result.get("error", "Error desconocido")
                self.results_text.append(f"Error: {error_msg}")
                QMessageBox.warning(self, "Error", error_msg)



 
    def display_releases_table(self, releases):
        """
        Display releases in a table that takes up all available space
        
        Args:
            releases (list): List of release dictionaries
        """
        # Hide the results text if visible
        if hasattr(self, 'results_text') and self.results_text.isVisible():
            self.results_text.hide()
        
        # Remove any existing table widget if present
        for i in reversed(range(self.layout().count())):
            item = self.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QTableWidget):
                item.widget().deleteLater()
        
        # Create the table widget
        table = QTableWidget(self)
        table.setObjectName("releases_table")
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Artist", "Release Title", "Type", "Date", "Disambiguation"])
        
        # Make the table expand to fill all available space
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table.setMinimumHeight(400)  # Ensure reasonable minimum height
        
        # Configure table headers
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Artist
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Type
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Date
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Disambiguation
        
        # Set row count
        table.setRowCount(len(releases))
        
        # Fill the table with data
        self._fill_releases_table(table, releases)
        
        # Insert the table into the layout in the correct position
        # This should be after the search area and before the button area
        main_layout = self.layout()
        
        # Create a count label for the number of releases
        count_label = QLabel(f"Showing {len(releases)} upcoming releases")
        count_label.setObjectName("count_label")
        
        # Use consistent positioning - insert widgets before the last item (button row)
        insert_position = main_layout.count() - 1
        main_layout.insertWidget(insert_position, count_label)
        main_layout.insertWidget(insert_position + 1, table)
        
        # Add styling to make the table fit the aesthetic
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
        
        # Make the table sortable after data is loaded
        table.setSortingEnabled(True)
        
        # Store reference for later access
        self.releases_table = table
        
        return table

    def _fallback_display_releases_table(self, releases):
        """
        Método de respaldo para mostrar la tabla de lanzamientos si no se encuentra el archivo UI
        
        Args:
            releases (list): Lista de lanzamientos
        """
        # Create the table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(['Artist', 'Release Title', 'Type', 'Date', 'Disambiguation'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Add a label showing how many releases we're displaying
        count_label = QLabel(f"Showing {len(releases)} upcoming releases")
        self.layout().insertWidget(self.layout().count() - 1, count_label)
        
        # Configure number of rows
        table.setRowCount(len(releases))
        
        # Fill the table
        self._fill_releases_table(table, releases)
        
        # If we have a current artist, add a follow button
        if hasattr(self, 'current_artist') and self.current_artist:
            self.add_follow_button = QPushButton(f"Seguir a {self.current_artist['name']} en Muspy")
            self.add_follow_button.clicked.connect(self.follow_current_artist)
            self.layout().insertWidget(self.layout().count() - 1, self.add_follow_button)
        
        # Resize rows to content
        table.resizeRowsToContents()
        
        # Make the table sortable
        table.setSortingEnabled(True)
        table.sortItems(3, Qt.SortOrder.AscendingOrder)

        
        # Hide the text edit and add the table to the layout
        self.results_text.hide()
        # Insert the table just above the bottom buttons
        self.layout().insertWidget(self.layout().count() - 1, table)
        return table


    def _fill_releases_table(self, table, releases):
        """
        Rellena una tabla existente con los datos de lanzamientos
        
        Args:
            table (QTableWidget): Tabla a rellenar
            releases (list): Lista de lanzamientos
        """
        # Fill the table
        for row, release in enumerate(releases):
            artist = release.get('artist', {})
            
            # Create items for each column
            artist_name_item = QTableWidgetItem(artist.get('name', 'Unknown'))
            if artist.get('disambiguation'):
                artist_name_item.setToolTip(artist.get('disambiguation'))
            table.setItem(row, 0, artist_name_item)
            
            # Title with proper casing and full information
            title_item = QTableWidgetItem(release.get('title', 'Untitled'))
            if release.get('comments'):
                title_item.setToolTip(release.get('comments'))
            table.setItem(row, 1, title_item)
            
            # Release type (Album, EP, etc.)
            type_item = QTableWidgetItem(release.get('type', 'Unknown').title())
            table.setItem(row, 2, type_item)
            
            # Date with color highlighting for upcoming releases
            date_str = release.get('date', 'No date')
            date_item = QTableWidgetItem(date_str)
            
            # Highlight dates that are within the next month  
            try:
                release_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                today = datetime.date.today()
                one_month = today + datetime.timedelta(days=30)
                
                if release_date <= today + datetime.timedelta(days=7):
                    # Coming very soon - red
                    date_item.setBackground(QColor(31, 60, 28))
                elif release_date <= one_month:
                    # Coming in a month - yellow
                    date_item.setBackground(QColor(60, 28, 31))
            except ValueError:
                # If date parsing fails, don't color
                pass
                
            table.setItem(row, 3, date_item)
            
            # Additional details
            details = []
            if release.get('format'):
                details.append(f"Format: {release.get('format')}")
            if release.get('tracks'):
                details.append(f"Tracks: {release.get('tracks')}")
            if release.get('country'):
                details.append(f"Country: {release.get('country')}")
            if artist.get('disambiguation'):
                details.append(artist.get('disambiguation'))

            details_item = QTableWidgetItem("; ".join(details) if details else "")
            table.setItem(row, 4, details_item)

# Menú sincronización
    def show_sync_menu(self):
        """
        Display a menu with sync options when sync_artists_button is clicked
        """
        # Create menu
        menu = QMenu(self)
        
        # Add menu actions
        muspy_action = QAction("Sincronizar artistas con Muspy", self)
        lastfm_action = QAction("Sincronizar Last.fm con Muspy", self)
        spotify_action = QAction("Sincronizar con Spotify", self)
        
        # Connect actions to their respective functions
        muspy_action.triggered.connect(self.sync_artists_with_muspy)
        lastfm_action.triggered.connect(self.show_lastfm_sync_dialog)
        spotify_action.triggered.connect(self.sync_spotify_selected_artists)
        
        # Add actions to menu
        menu.addAction(muspy_action)
        menu.addAction(lastfm_action)
        menu.addAction(spotify_action)
        
        # Get the button position
        pos = self.sync_artists_button.mapToGlobal(QPoint(0, self.sync_artists_button.height()))
        
        # Show menu
        menu.exec(pos)

 
    def show_lastfm_sync_dialog(self):
        """
        Shows a dialog with options to sync Last.fm artists with Muspy
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "Last.fm credentials not configured")
            return
            
        # Create the dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Last.fm Sync Options")
        dialog.setMinimumWidth(350)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Create widgets for number of artists
        artist_layout = QHBoxLayout()
        artist_label = QLabel("Number of top artists:")
        artist_spinbox = QSpinBox()
        artist_spinbox.setRange(1, 100000)
        artist_spinbox.setValue(50)  # Default value
        artist_spinbox.setSingleStep(10)
        artist_layout.addWidget(artist_label)
        artist_layout.addWidget(artist_spinbox)
        layout.addLayout(artist_layout)
        
        # Create widgets for time period
        period_layout = QHBoxLayout()
        period_label = QLabel("Time period (days):")
        period_combo = QComboBox()
        period_combo.addItem("7 days", "7day")
        period_combo.addItem("30 days", "1month")
        period_combo.addItem("90 days", "3month")
        period_combo.addItem("180 days", "6month")
        period_combo.addItem("365 days", "12month")
        period_combo.addItem("All time", "overall")
        period_combo.setCurrentIndex(5)  # Default to "All time"
        period_layout.addWidget(period_label)
        period_layout.addWidget(period_combo)
        layout.addLayout(period_layout)
        
        # Add information text
        info_label = QLabel("This will add your most played Last.fm artists to Muspy for release tracking.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Create buttons
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("Cancel")
        sync_button = QPushButton("Sync Artists")
        sync_button.setDefault(True)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(sync_button)
        layout.addLayout(button_layout)
        
        # Connect buttons
        cancel_button.clicked.connect(dialog.reject)
        sync_button.clicked.connect(dialog.accept)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get values from dialog
            count = artist_spinbox.value()
            period = period_combo.currentData()
            
            # Call function to sync with these parameters
            self.sync_top_artists_from_lastfm(count, period)


    def sync_lastfm_artists(self):
        """
        Synchronize selected artists with Last.fm (love tracks by these artists)
        """
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "Last.fm credentials not configured")
            return

        # Clear the results area and make sure it's visible
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append(f"Starting Last.fm synchronization...\n")
        QApplication.processEvents()  # Update UI

        try:
            # Get the selected artists from the JSON file
            json_path = os.path.join(PROJECT_ROOT, ".content", "cache", "artists_selected.json")
            if not os.path.exists(json_path):
                self.results_text.append("No selected artists found. Please load artists first.")
                return
                
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
                
            if not artists_data:
                self.results_text.append("No artists found in the selection file.")
                return
                
            total_artists = len(artists_data)
            self.results_text.append(f"Found {total_artists} artists to synchronize with Last.fm.")
            QApplication.processEvents()
            
            # Get LastFM network
            network = self.lastfm_auth.get_network()
            if not network:
                self.results_text.append("Could not connect to LastFM. Please check your credentials.")
                return
                
            # Check if we're authenticated for write operations
            if not self.lastfm_auth.is_authenticated():
                if QT_AVAILABLE:
                    reply = QMessageBox.question(
                        self, 
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
                                self.results_text.append("Authentication failed. Cannot follow artists.")
                                return
                        else:
                            self.results_text.append("Authentication canceled. Will only retrieve artist info.")
                    else:
                        self.results_text.append("Authentication declined. Will only retrieve artist info.")
                else:
                    self.results_text.append("Authentication required but not available without UI. Will only retrieve artist info.")
            
            successful_syncs = 0
            failed_syncs = 0
            info_only = 0
            
            # Process artists
            for i, artist_data in enumerate(artists_data):
                artist_name = artist_data.get('nombre', '')
                
                # Update progress
                if (i + 1) % 5 == 0 or i == total_artists - 1:
                    progress = int((i + 1) / total_artists * 50)
                    self.results_text.clear()
                    self.results_text.append(f"Syncing with Last.fm... {i + 1}/{total_artists}\n")
                    self.results_text.append(f"Progress: [" + "#" * progress + "-" * (50 - progress) + "]\n")
                    self.results_text.append(f"Success: {successful_syncs}, Info only: {info_only}, Failed: {failed_syncs}\n")
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
                            logger.info(f"Found artist {artist_name} on Last.fm")
                            info_only += 1
                        except Exception as e:
                            logger.error(f"Error getting info for {artist_name}: {e}")
                            failed_syncs += 1
                            
                except Exception as e:
                    failed_syncs += 1
                    logger.error(f"Error syncing {artist_name} with Last.fm: {e}")
            
            # Show final summary
            self.results_text.clear()
            self.results_text.append(f"Last.fm synchronization completed\n")
            self.results_text.append(f"Total artists processed: {total_artists}\n")
            
            if self.lastfm_auth.is_authenticated():
                self.results_text.append(f"Successfully followed: {successful_syncs}\n")
            else:
                self.results_text.append(f"Artists found (info only): {info_only}\n")
                
            self.results_text.append(f"Failed: {failed_syncs}\n")
            
            # Show a message box with results
            QMessageBox.information(
                self,
                "Last.fm Synchronization Complete",
                f"Processed {total_artists} artists with Last.fm.\n" +
                (f"Successfully followed: {successful_syncs}\n" if self.lastfm_auth.is_authenticated() else f"Artists found (info only): {info_only}\n") +
                f"Failed: {failed_syncs}"
            )
            
        except Exception as e:
            error_msg = f"Error in Last.fm synchronization: {e}"
            self.results_text.append(error_msg)
            logger.error(error_msg, exc_info=True)
 
    def sync_spotify(self):
        """
        Synchronize selected artists from JSON to Spotify (follow them on Spotify)
        """
        # Check if Spotify credentials are configured
        if not self.spotify_enabled:
            self.results_text.clear()
            self.results_text.show()
            self.results_text.append("Spotify credentials not configured. Please check your settings.")
            return
        
        # Clear the results area
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append("Starting Spotify synchronization...\n")
        QApplication.processEvents()
        
        # Get an authenticated Spotify client
        try:
            self.results_text.append("Authenticating with Spotify...")
            QApplication.processEvents()
            
            # Get the Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                self.results_text.append("Failed to get Spotify client. Please check authentication.")
                return
                
            # Get user info to confirm authentication
            user_info = spotify_client.current_user()
            if user_info and 'id' in user_info:
                self.results_text.append(f"Successfully authenticated as {user_info.get('display_name', user_info['id'])}")
            else:
                self.results_text.append("Authentication succeeded but user info couldn't be retrieved.")
                return
            
            # Get the selected artists from JSON
            json_path = os.path.join(PROJECT_ROOT, ".content", "cache", "artists_selected.json")
            if not os.path.exists(json_path):
                self.results_text.append("No selected artists found. Please load artists first.")
                return
                
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
                
            if not artists_data:
                self.results_text.append("No artists found in the selection file.")
                return
                
            total_artists = len(artists_data)
            self.results_text.append(f"Found {total_artists} artists to synchronize with Spotify.")
            QApplication.processEvents()
            
            # Create a progress bar dialog
            from PyQt6.QtWidgets import QProgressDialog
            progress = QProgressDialog("Syncing artists with Spotify...", "Cancel", 0, total_artists, self)
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
                    self.results_text.append("Synchronization canceled by user.")
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
                    logger.error(f"Error following artist {artist_name} on Spotify: {e}")
            
            # Complete the progress
            progress.setValue(total_artists)
            
            # Show summary in results text
            self.results_text.clear()
            self.results_text.append(f"Spotify synchronization completed\n")
            self.results_text.append(f"Total artists processed: {total_artists}")
            self.results_text.append(f"Successfully followed: {successful_follows}")
            self.results_text.append(f"Already following: {already_following}")
            self.results_text.append(f"Not found on Spotify: {artists_not_found}")
            self.results_text.append(f"Failed: {failed_follows}")
            
            # Show the detailed log in a dialog
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton
            log_dialog = QDialog(self)
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
                self,
                "Spotify Synchronization Complete",
                f"Successfully followed {successful_follows} artists on Spotify.\n"
                f"Already following: {already_following}\n"
                f"Artists not found: {artists_not_found}\n"
                f"Failed: {failed_follows}"
            )
                
        except Exception as e:
            error_msg = f"Error during Spotify synchronization: {e}"
            self.results_text.append(error_msg)
            logger.error(error_msg, exc_info=True)
   
    def authenticate_spotify(self):
        """
        Authenticate with Spotify using OAuth
        """
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
            
            # Setup cache path
            cache_path = os.path.join(PROJECT_ROOT, ".content", "cache", ".spotify_cache")
            
                    
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
                self.results_text.append("Authentication canceled")
                return False
            
            # Exchange the code for a token
            code = sp_oauth.parse_response_code(redirect_url)
            token_info = sp_oauth.get_access_token(code)
            
            # Create Spotify client
            spotify_client= spotipy.Spotify(auth=token_info['access_token'])
            
            # Test with a simple API call
            user_info = spotify_client.current_user()
            if user_info and 'id' in user_info:
                self.results_text.append(f"Successfully authenticated as {user_info['display_name']}")
                return True
            else:
                self.results_text.append("Authentication failed")
                return False
            
        except Exception as e:
            logger.error(f"Spotify authentication error: {e}")
            self.results_text.append(f"Error authenticating with Spotify: {e}")
            return False

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
                    logger.error("Could not get authenticated Spotify client")
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
                    logger.info(f"Already following {artist_name} on Spotify")
                    return 0  # Already following
                
                # Follow the artist
                spotify_client.user_follow_artists([artist_id])
                logger.info(f"Successfully followed {artist_name} on Spotify")
                return 1  # Success
                
            else:
                logger.warning(f"Artist '{artist_name}' not found on Spotify")
                return -1  # Error/Not found
                
        except Exception as e:
            logger.error(f"Error following artist on Spotify: {e}")
            return -1  # Error




    def manage_lastfm_auth(self):
        """Manage LastFM authentication settings"""
        if not self.lastfm_enabled:
            QMessageBox.warning(self, "Error", "LastFM credentials not configured")
            return
            
        # Check current status
        is_authenticated = False
        user_info = None
        
        if hasattr(self, 'lastfm_auth'):
            is_authenticated = self.lastfm_auth.is_authenticated()
            user_info = self.lastfm_auth.get_user_info()
        
        # Create management menu
        auth_menu = QMenu(self)
        
        # Show status
        status_action = QAction(f"Status: {'Authenticated' if is_authenticated else 'Not Authenticated'}", self)
        status_action.setEnabled(False)
        auth_menu.addAction(status_action)
        
        # Show user info if available
        if user_info:
            user_info_action = QAction(f"User: {user_info.get('name')} (Playcount: {user_info.get('playcount', 'N/A')})", self)
            user_info_action.setEnabled(False)
            auth_menu.addAction(user_info_action)
        
        auth_menu.addSeparator()
        
        # Authentication actions
        authenticate_action = QAction("Authenticate with LastFM", self)
        authenticate_action.triggered.connect(self._authenticate_lastfm)
        auth_menu.addAction(authenticate_action)
        
        if is_authenticated:
            clear_action = QAction("Clear Authentication", self)
            clear_action.triggered.connect(self._clear_lastfm_auth)
            auth_menu.addAction(clear_action)
        
        auth_menu.addSeparator()
        
        # Test actions for authenticated users
        if is_authenticated:
            test_action = QAction("Test LastFM Connection", self)
            test_action.triggered.connect(self._test_lastfm_connection)
            auth_menu.addAction(test_action)
        
        # Show menu
        auth_menu.exec(QCursor.pos())

    def _authenticate_lastfm(self):
        """Authenticate with LastFM by getting password from user"""
        if not hasattr(self, 'lastfm_auth') or not self.lastfm_username:
            QMessageBox.warning(self, "Error", "LastFM configuration not available")
            return
        
        # Prompt for password
        password, ok = QInputDialog.getText(
            self,
            "LastFM Authentication",
            f"Enter password for LastFM user {self.lastfm_username}:",
            QLineEdit.EchoMode.Password
        )
        
        if not ok or not password:
            self.results_text.append("Authentication canceled.")
            return
        
        # Update password in auth manager
        self.lastfm_auth.password = password
        
        # Try to authenticate
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append("Authenticating with LastFM...")
        QApplication.processEvents()
        
        if self.lastfm_auth.authenticate():
            self.results_text.append("Authentication successful!")
            user_info = self.lastfm_auth.get_user_info()
            if user_info:
                self.results_text.append(f"Logged in as: {user_info.get('name')}")
                self.results_text.append(f"Playcount: {user_info.get('playcount', 'N/A')}")
        else:
            self.results_text.append("Authentication failed. Please check your username and password.")

    def _clear_lastfm_auth(self):
        """Clear LastFM authentication data"""
        if hasattr(self, 'lastfm_auth'):
            self.lastfm_auth.clear_session()
            self.results_text.clear()
            self.results_text.show()
            self.results_text.append("LastFM authentication data cleared.")
            QMessageBox.information(self, "Authentication Cleared", "LastFM authentication data has been cleared.")

    def _test_lastfm_connection(self):
        """Test the LastFM connection with a simple API call"""
        if not hasattr(self, 'lastfm_auth'):
            QMessageBox.warning(self, "Error", "LastFM configuration not available")
            return
        
        self.results_text.clear()
        self.results_text.show()
        self.results_text.append("Testing LastFM connection...")
        QApplication.processEvents()
        
        # Get user info
        user_info = self.lastfm_auth.get_user_info()
        if user_info:
            self.results_text.append("Connection successful!")
            self.results_text.append(f"User: {user_info.get('name')}")
            self.results_text.append(f"Playcount: {user_info.get('playcount', 'N/A')}")
            self.results_text.append(f"URL: {user_info.get('url', 'N/A')}")
            
            # Try to get top artists if we're authenticated
            if self.lastfm_auth.is_authenticated():
                self.results_text.append("\nFetching top artists...")
                QApplication.processEvents()
                
                top_artists = self.lastfm_auth.get_top_artists(limit=5)
                if top_artists:
                    self.results_text.append("\nTop 5 Artists:")
                    for artist in top_artists:
                        self.results_text.append(f"• {artist['name']} (Playcount: {artist['playcount']})")
                else:
                    self.results_text.append("Could not retrieve top artists.")
        else:
            self.results_text.append("Connection failed. Please check your LastFM credentials.")

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


    def load_module_settings(self, module_args):
        """Load module-specific settings from args dictionary"""
        try:
            # Load API credentials
            if 'spotify_client_id' in module_args:
                self.spotify_client_id = module_args['spotify_client_id']
            if 'spotify_client_secret' in module_args:
                self.spotify_client_secret = module_args['spotify_client_secret']
            if 'lastfm_api_key' in module_args:
                self.lastfm_api_key = module_args['lastfm_api_key']
            if 'lastfm_username' in module_args:
                self.lastfm_username = module_args['lastfm_username']
                
            # Update Spotify/LastFM enabled flags based on credentials
            self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
            self.lastfm_enabled = bool(self.lastfm_api_key and self.lastfm_username)
            
            logger.info("Module settings loaded successfully")
        except Exception as e:
            logger.error(f"Error loading module settings: {e}")

    def initialize_default_values(self):
        """Initialize default values for settings when configuration can't be loaded"""
        logger.info("Initializing default values for settings")
        
        # Default API credentials (empty)
        self.spotify_client_id = None
        self.spotify_client_secret = None
        self.lastfm_api_key = None
        self.lastfm_username = None
        
        # Default flags
        self.spotify_enabled = False
        self.lastfm_enabled = False


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

    def get_spotify_client(self):
        """Get an authenticated Spotify client on demand"""
        if hasattr(self, 'spotify_auth'):
            return self.spotify_auth.get_client()
        return None


    def show_progress_operation(self, operation_function, operation_args=None, title="Operación en progreso", 
                            label_format="{current}/{total} - {status}", 
                            cancel_button_text="Cancelar", 
                            finish_message=None):
        """
        Ejecuta una operación con una barra de progreso, permitiendo cancelación.
        
        Args:
            operation_function (callable): Función a ejecutar que debe aceptar un objeto QProgressDialog
                                        como su primer argumento
            operation_args (dict, optional): Argumentos para pasar a la función de operación
            title (str): Título de la ventana de progreso
            label_format (str): Formato del texto de progreso, con placeholders {current}, {total}, {status}
            cancel_button_text (str): Texto del botón cancelar
            finish_message (str, optional): Mensaje a mostrar cuando la operación termina con éxito
                                        (None para no mostrar ningún mensaje)
        
        Returns:
            Any: El valor devuelto por la función de operación
        """
        from PyQt6.QtWidgets import QProgressDialog, QApplication
        from PyQt6.QtCore import Qt
        
        # Crear el diálogo de progreso
        progress = QProgressDialog(self)
        progress.setWindowTitle(title)
        progress.setCancelButtonText(cancel_button_text)
        progress.setMinimumDuration(0)  # Mostrar inmediatamente
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Configuramos la progress bar para que permita rastreo indeterminado si es necesario
        progress.setMinimum(0)
        progress.setMaximum(100)  # Se puede cambiar desde la operación
        progress.setValue(0)
        
        # Configurar el status label inicial
        initial_status = label_format.format(current=0, total=0, status="Iniciando...")
        progress.setLabelText(initial_status)
        
        # Crear una función de actualización que la operación pueda utilizar
        def update_progress(current, total, status="Procesando...", indeterminate=False):
            if progress.wasCanceled():
                return False
            
            if indeterminate:
                # Modo indeterminado: 0 indica progreso indeterminado en Qt
                progress.setMinimum(0)
                progress.setMaximum(0)
            else:
                # Modo normal con porcentaje
                progress.setMinimum(0)
                progress.setMaximum(total)
                progress.setValue(current)
                
            # Actualizar el texto
            progress_text = label_format.format(current=current, total=total, status=status)
            progress.setLabelText(progress_text)
            
            # Procesar eventos para mantener la UI responsiva
            QApplication.processEvents()
            return True
        
        # Preparar argumentos
        if operation_args is None:
            operation_args = {}
        
        # Ejecutar la operación con la función de progreso
        try:
            result = operation_function(update_progress, **operation_args)
            
            # Mostrar mensaje de finalización si se proporciona
            if finish_message and not progress.wasCanceled():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Operación completa", finish_message)
                
            return result
        except Exception as e:
            # Capturar cualquier excepción para no dejar el diálogo colgado
            from PyQt6.QtWidgets import QMessageBox
            self.logger.error(f"Error en la operación: {e}", exc_info=True)
            
            # Solo mostrar error si no fue cancelado
            if not progress.wasCanceled():
                QMessageBox.critical(self, "Error", f"Se produjo un error durante la operación: {str(e)}")
            
            return None
        finally:
            # Asegurarse de que el diálogo se cierre
            progress.close()

    

    def cache_manager(self, cache_type, data=None, force_refresh=False, expiry_hours=24):
        """
        Manages caching for different types of data (top_artists, loved_tracks, releases)
        
        Args:
            cache_type (str): Type of cache ('top_artists', 'loved_tracks', 'releases')
            data (dict, optional): Data to cache. If None, retrieves cache.
            force_refresh (bool): Whether to ignore cache and force refresh
            expiry_hours (int): Hours after which cache expires (default 24)
            
        Returns:
            dict or None: Cached data if available and not expired, None otherwise
        """
        import json
        import os
        import time
        
        # Ensure cache directory exists
        cache_dir = os.path.join(PROJECT_ROOT, ".content", "cache", "muspy_module")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Define cache file path
        cache_file = os.path.join(cache_dir, f"{cache_type}_cache.json")
        
        # If we're storing data
        if data is not None:
            cache_data = {
                "timestamp": time.time(),
                "data": data
            }
            
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                self.logger.debug(f"Cached {cache_type} data successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error caching {cache_type} data: {e}")
                return False
        
        # If we're retrieving data
        else:
            # If force refresh, don't use cache
            if force_refresh:
                return None
                
            # Check if cache file exists
            if not os.path.exists(cache_file):
                return None
                
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                # Check if cache is expired
                timestamp = cache_data.get("timestamp", 0)
                expiry_time = timestamp + (expiry_hours * 3600)  # Convert hours to seconds
                
                if time.time() > expiry_time:
                    self.logger.debug(f"{cache_type} cache expired")
                    return None
                    
                # Cache is valid
                self.logger.debug(f"Using cached {cache_type} data")
                return cache_data.get("data")
                
            except Exception as e:
                self.logger.error(f"Error loading {cache_type} cache: {e}")
                return None

    def clear_lastfm_cache(self):
        """
        Clear the LastFM cache files
        """
        import os
        import glob
        
        cache_dir = os.path.join(PROJECT_ROOT, ".content", "cache", "muspy_module")
        
        if not os.path.exists(cache_dir):
            return
        
        try:
            # Find all LastFM cache files
            lastfm_cache_files = glob.glob(os.path.join(cache_dir, "top_artists_*.json"))
            lastfm_cache_files.extend(glob.glob(os.path.join(cache_dir, "loved_tracks_*.json")))
            
            for cache_file in lastfm_cache_files:
                try:
                    os.remove(cache_file)
                    self.logger.debug(f"Removed cache file: {cache_file}")
                except Exception as e:
                    self.logger.error(f"Error removing cache file {cache_file}: {e}")
            
            QMessageBox.information(self, "Cache Cleared", f"Cleared {len(lastfm_cache_files)} LastFM cache files")
        except Exception as e:
            self.logger.error(f"Error clearing LastFM cache: {e}")
            QMessageBox.warning(self, "Error", f"Error clearing cache: {e}")

    def debug_stacked_widget_hierarchy(self):
        """Debug the stacked widget hierarchy to troubleshoot issues"""
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
            
        self.logger.info(f"Found stackedWidget with {stack_widget.count()} pages")
        
        # Log details about each page
        for i in range(stack_widget.count()):
            page = stack_widget.widget(i)
            self.logger.info(f"Page {i} - objectName: {page.objectName()}")
            
            # Log children of the page
            for child in page.children():
                if hasattr(child, 'objectName'):
                    self.logger.info(f"  Child: {child.objectName()} - Type: {type(child).__name__}")


# Musicbrainz
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
                    date_text = release.get('date', '')
                    if not isinstance(date_text, str):
                        date_text = ""
                    date_item = QTableWidgetItem(date_text)
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

    def follow_artist_from_name(self, artist_name):
        """Follow artist by searching for their MBID first"""
        # First get the MBID
        mbid = self.get_mbid_artist_searched(artist_name)
        
        if mbid:
            # Store current artist
            self.current_artist = {"name": artist_name, "mbid": mbid}
            
            # Follow the artist
            success = self.add_artist_to_muspy(mbid, artist_name)
            
            if success:
                QMessageBox.information(self, "Success", f"Now following {artist_name} on Muspy")
            else:
                QMessageBox.warning(self, "Error", f"Could not follow {artist_name} on Muspy")
        else:
            QMessageBox.warning(self, "Error", f"Could not find MBID for {artist_name}")

    def open_musicbrainz_artist(self, artist_mbid):
        """Open MusicBrainz artist page in browser"""
        if not artist_mbid:
            return
            
        url = f"https://musicbrainz.org/artist/{artist_mbid}"
        
        import webbrowser
        webbrowser.open(url)

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

    def show_spotify_menu(self):
        """
        Display a menu with Spotify options when get_releases_spotify button is clicked
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self, "Error", "Spotify credentials not configured")
            return
        
        # Create menu
        menu = QMenu(self)
        
        # Add menu actions
        show_artists_action = QAction("Mostrar artistas seguidos", self)
        show_releases_action = QAction("Nuevos álbumes de artistas seguidos", self)
        
        # Connect actions to their respective functions
        show_artists_action.triggered.connect(self.show_spotify_followed_artists)
        show_releases_action.triggered.connect(self.show_spotify_new_releases)
        
        # Add actions to menu
        menu.addAction(show_artists_action)
        menu.addAction(show_releases_action)
        
        # Add separator and cache management option
        menu.addSeparator()
        clear_cache_action = QAction("Limpiar caché de Spotify", self)
        clear_cache_action.triggered.connect(self.clear_spotify_cache)
        menu.addAction(clear_cache_action)
        
        # Get the button position
        pos = self.get_releases_spotify_button.mapToGlobal(QPoint(0, self.get_releases_spotify_button.height()))
        
        # Show menu
        menu.exec(pos)

    def show_spotify_followed_artists(self):
        """
        Show a list of artists the user follows on Spotify with caching
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self, "Error", "Spotify credentials not configured")
            return
        
        # Make sure we're showing the text page during loading
        self.show_text_page()
        self.results_text.clear()
        
        # Try to get from cache first
        cache_key = "followed_artists"
        cached_data = self.spotify_cache_manager(cache_key, expiry_hours=24)
        if cached_data:
            self.results_text.append("Showing cached followed artists data...")
            self.display_spotify_artists_in_stacked_widget(cached_data)
            return
        
        self.results_text.append("Retrieving artists you follow on Spotify...")
        QApplication.processEvents()
        
        # Get Spotify client
        spotify_client = self.spotify_auth.get_client()
        if not spotify_client:
            self.results_text.append("Failed to get Spotify client. Please check authentication.")
            return
        
        # Function to fetch artists with progress dialog
        def fetch_spotify_artists(update_progress):
            try:
                update_progress(0, 100, "Connecting to Spotify API...")
                
                all_artists = []
                offset = 0
                limit = 50  # Spotify's maximum
                total = 1  # Will be updated after first request
                
                # Paginate through all followed artists
                while offset < total:
                    # Update progress
                    progress_percent = min(100, int((offset / max(1, total)) * 100))
                    update_progress(progress_percent, 100, f"Fetching artists ({offset}/{total})...")
                    
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
                update_progress(95, 100, "Processing artist data...")
                
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
                self.spotify_cache_manager(cache_key, processed_artists)
                
                update_progress(100, 100, "Complete!")
                
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
        result = self.show_progress_operation(
            fetch_spotify_artists,
            title="Loading Spotify Artists",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            artists = result.get("artists", [])
            
            if not artists:
                self.results_text.append("You don't follow any artists on Spotify.")
                return
            
            # Display artists in the stack widget table
            self.display_spotify_artists_in_stacked_widget(artists)
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.results_text.append(f"Error: {error_msg}")
            QMessageBox.warning(self, "Error", f"Could not load Spotify artists: {error_msg}")

    def show_spotify_new_releases(self):
        """
        Show new releases from artists the user follows on Spotify with caching
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self, "Error", "Spotify credentials not configured")
            return
        
        # Make sure we're showing the text page during loading
        self.show_text_page()
        self.results_text.clear()
        
        # Try to get from cache first
        cache_key = "new_releases"
        cached_data = self.spotify_cache_manager(cache_key, expiry_hours=12)  # Shorter expiry for releases
        if cached_data:
            self.results_text.append("Showing cached new releases data...")
            self.display_spotify_releases_in_stacked_widget(cached_data)
            return
        
        self.results_text.append("Retrieving new releases from artists you follow on Spotify...")
        QApplication.processEvents()
        
        # Get Spotify client
        spotify_client = self.spotify_auth.get_client()
        if not spotify_client:
            self.results_text.append("Failed to get Spotify client. Please check authentication.")
            return
        
        # Function to fetch new releases with progress dialog
        def fetch_spotify_releases(update_progress):
            try:
                update_progress(0, 100, "Connecting to Spotify API...")
                
                # First get all artists the user follows
                update_progress(10, 100, "Getting artists you follow...")
                
                followed_artists = []
                offset = 0
                limit = 50  # Spotify's maximum
                total = 1  # Will be updated after first request
                
                # Paginate through all followed artists
                while offset < total:
                    # Fetch current page of artists
                    results = spotify_client.current_user_followed_artists(limit=limit, after=None if offset == 0 else followed_artists[-1]['id'])
                    
                    if 'artists' in results and 'items' in results['artists']:
                        # Get artists from this page
                        artists_page = results['artists']['items']
                        followed_artists.extend(artists_page)
                        
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
                
                # We have all followed artists, now get their recent releases
                update_progress(30, 100, f"Found {len(followed_artists)} artists. Getting their recent releases...")
                
                all_releases = []
                artist_count = len(followed_artists)
                
                # Only process a reasonable number of artists to avoid rate limits
                max_artists_to_process = min(artist_count, 50)
                artists_to_process = followed_artists[:max_artists_to_process]
                
                for i, artist in enumerate(artists_to_process):
                    artist_id = artist['id']
                    artist_name = artist['name']
                    
                    progress = 30 + int((i / max_artists_to_process) * 60)
                    update_progress(progress, 100, f"Getting releases for {artist_name} ({i+1}/{max_artists_to_process})...")
                    
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
                        # Continue with next artist
                        continue
                
                # Process releases data
                update_progress(95, 100, "Processing release data...")
                
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
                self.spotify_cache_manager(cache_key, processed_releases)
                
                update_progress(100, 100, "Complete!")
                
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
        result = self.show_progress_operation(
            fetch_spotify_releases,
            title="Loading Spotify Releases",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            releases = result.get("releases", [])
            
            if not releases:
                self.results_text.append("No new releases found from artists you follow on Spotify.")
                return
            
            # Display releases in the stack widget table
            self.display_spotify_releases_in_stacked_widget(releases)
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.results_text.append(f"Error: {error_msg}")
            QMessageBox.warning(self, "Error", f"Could not load Spotify releases: {error_msg}")



    def display_spotify_artists_in_stacked_widget(self, artists):
        """
        Display Spotify artists in the stacked widget
        
        Args:
            artists (list): List of artist dictionaries
        """
        # Find the stacked widget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the spotify_artists_page (assuming it exists in the UI)
        spotify_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "spotify_artists_page":
                spotify_page = widget
                break
        
        if not spotify_page:
            self.logger.error("spotify_artists_page not found in stacked widget")
            # Fallback to text display
            self._display_spotify_artists_as_text(artists)
            return
        
        # Get the table from the page
        table = spotify_page.findChild(QTableWidget, "spotify_artists_table")
        if not table:
            self.logger.error("spotify_artists_table not found in spotify_artists_page")
            # Fallback to text display
            self._display_spotify_artists_as_text(artists)
            return
        
        # Get the count label
        count_label = spotify_page.findChild(QLabel, "spotify_artists_count_label")
        if count_label:
            count_label.setText(f"Showing {len(artists)} artists you follow on Spotify")
        
        # Configure table
        table.setRowCount(len(artists))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table with data
        for i, artist in enumerate(artists):
            # Name column
            name_item = QTableWidgetItem(artist.get('name', 'Unknown'))
            table.setItem(i, 0, name_item)
            
            # Genres column
            genres_item = QTableWidgetItem(artist.get('genres', ''))
            table.setItem(i, 1, genres_item)
            
            # Followers column - Usar NumericTableWidgetItem
            followers = artist.get('followers', 0)
            followers_item = NumericTableWidgetItem(f"{followers:,}" if followers else "0")
            followers_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 2, followers_item)
            
            # Popularity column - Usar NumericTableWidgetItem
            popularity = artist.get('popularity', 0)
            popularity_item = NumericTableWidgetItem(str(popularity))
            popularity_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 3, popularity_item)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
        
        # Configure context menu for the table
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_spotify_artist_context_menu)
        
        # Switch to the Spotify artists page
        stack_widget.setCurrentWidget(spotify_page)

    def display_spotify_releases_in_stacked_widget(self, releases):
        """
        Display Spotify releases in the stacked widget
        
        Args:
            releases (list): List of release dictionaries
        """
        # Find the stacked widget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the spotify_releases_page (assuming it exists in the UI)
        spotify_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "spotify_releases_page":
                spotify_page = widget
                break
        
        if not spotify_page:
            self.logger.error("spotify_releases_page not found in stacked widget")
            # Fallback to text display
            self._display_spotify_releases_as_text(releases)
            return
        
        # Get the table from the page
        table = spotify_page.findChild(QTableWidget, "spotify_releases_table")
        if not table:
            self.logger.error("spotify_releases_table not found in spotify_releases_page")
            # Fallback to text display
            self._display_spotify_releases_as_text(releases)
            return
        
        # Get the count label
        count_label = spotify_page.findChild(QLabel, "spotify_releases_count_label")
        if count_label:
            count_label.setText(f"Showing {len(releases)} new releases from artists you follow on Spotify")
        
        # Configure table
        table.setRowCount(len(releases))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table with data
        for i, release in enumerate(releases):
            # Artist column
            artist_item = QTableWidgetItem(release.get('artist', 'Unknown'))
            table.setItem(i, 0, artist_item)
            
            # Title column
            title_item = QTableWidgetItem(release.get('title', 'Unknown'))
            table.setItem(i, 1, title_item)
            
            # Type column
            type_item = QTableWidgetItem(release.get('type', ''))
            table.setItem(i, 2, type_item)
            
            # Date column
            date_item = QTableWidgetItem(release.get('date', ''))
            table.setItem(i, 3, date_item)
            
            # Tracks column - Usar NumericTableWidgetItem
            tracks_item = NumericTableWidgetItem(str(release.get('total_tracks', 0)))
            tracks_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 4, tracks_item)
            
            # Store the Spotify IDs for context menu actions
            for col in range(table.columnCount()):
                if table.item(i, col):
                    # Store both release ID and artist ID
                    item_data = {
                        'release_id': release.get('id', ''),
                        'artist_id': release.get('artist_id', '')
                    }
                    table.item(i, col).setData(Qt.ItemDataRole.UserRole, item_data)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
        
        # Configure context menu for the table
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_spotify_release_context_menu)
        
        # Switch to the Spotify releases page
        stack_widget.setCurrentWidget(spotify_page)


    def _display_spotify_artists_as_text(self, artists):
        """
        Display Spotify artists as text in the results area
        
        Args:
            artists (list): List of artist dictionaries
        """
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"You follow {len(artists)} artists on Spotify")
        self.results_text.append("-" * 50)
        
        # Sort by name
        sorted_artists = sorted(artists, key=lambda x: x.get('name', '').lower())
        
        for i, artist in enumerate(sorted_artists):
            name = artist.get('name', 'Unknown')
            followers = artist.get('followers', 0)
            genres = artist.get('genres', '')
            popularity = artist.get('popularity', 0)
            
            self.results_text.append(f"{i+1}. {name}")
            self.results_text.append(f"   Followers: {followers:,}")
            if genres:
                self.results_text.append(f"   Genres: {genres}")
            self.results_text.append(f"   Popularity: {popularity}/100")
            self.results_text.append("")
        
        self.results_text.append("-" * 50)

    def _display_spotify_releases_as_text(self, releases):
        """
        Display Spotify releases as text in the results area
        
        Args:
            releases (list): List of release dictionaries
        """
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Found {len(releases)} new releases from artists you follow")
        self.results_text.append("-" * 50)
        
        for i, release in enumerate(releases):
            artist = release.get('artist', 'Unknown')
            title = release.get('title', 'Unknown')
            release_type = release.get('type', '')
            date = release.get('date', '')
            tracks = release.get('total_tracks', 0)
            
            self.results_text.append(f"{i+1}. {artist} - {title}")
            self.results_text.append(f"   Type: {release_type}")
            self.results_text.append(f"   Released: {date}")
            self.results_text.append(f"   Tracks: {tracks}")
            self.results_text.append("")
        
        self.results_text.append("-" * 50)


    def show_spotify_artist_context_menu(self, position):
        """
        Show context menu for Spotify artists in the table
        
        Args:
            position (QPoint): Position where the context menu was requested
        """
        table = self.sender()
        if not table:
            return
        
        item = table.itemAt(position)
        if not item:
            return
        
        # Get the artist ID from the item
        artist_id = item.data(Qt.ItemDataRole.UserRole)
        if not artist_id:
            return
        
        # Get the artist name from the row
        row = item.row()
        artist_name = table.item(row, 0).text() if table.item(row, 0) else "Unknown"
        
        # Create the context menu
        menu = QMenu(self)
        
        # Add actions
        view_spotify_action = QAction(f"View '{artist_name}' on Spotify", self)
        view_spotify_action.triggered.connect(lambda: self.open_spotify_artist(artist_id))
        menu.addAction(view_spotify_action)
        
        # Add action to follow on Muspy
        follow_muspy_action = QAction(f"Follow '{artist_name}' on Muspy", self)
        follow_muspy_action.triggered.connect(lambda: self.follow_spotify_artist_on_muspy(artist_id, artist_name))
        menu.addAction(follow_muspy_action)
        
        # Add action to get artist's albums
        get_albums_action = QAction(f"Get '{artist_name}' releases", self)
        get_albums_action.triggered.connect(lambda: self.get_spotify_artist_albums(artist_id, artist_name))
        menu.addAction(get_albums_action)
        
        # Show the menu
        menu.exec(table.mapToGlobal(position))

    def show_spotify_release_context_menu(self, position):
        """
        Show context menu for Spotify releases in the table
        
        Args:
            position (QPoint): Position where the context menu was requested
        """
        table = self.sender()
        if not table:
            return
        
        item = table.itemAt(position)
        if not item:
            return
        
        # Get the release and artist IDs from the item
        item_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(item_data, dict):
            return
        
        release_id = item_data.get('release_id', '')
        artist_id = item_data.get('artist_id', '')
        
        if not release_id:
            return
        
        # Get the release title and artist name from the row
        row = item.row()
        artist_name = table.item(row, 0).text() if table.item(row, 0) else "Unknown"
        release_title = table.item(row, 1).text() if table.item(row, 1) else "Unknown"
        
        # Create the context menu
        menu = QMenu(self)
        
        # Add actions
        view_release_action = QAction(f"View '{release_title}' on Spotify", self)
        view_release_action.triggered.connect(lambda: self.open_spotify_album(release_id))
        menu.addAction(view_release_action)
        
        if artist_id:
            view_artist_action = QAction(f"View artist '{artist_name}' on Spotify", self)
            view_artist_action.triggered.connect(lambda: self.open_spotify_artist(artist_id))
            menu.addAction(view_artist_action)
            
            # Add action to follow artist on Muspy
            follow_muspy_action = QAction(f"Follow '{artist_name}' on Muspy", self)
            follow_muspy_action.triggered.connect(lambda: self.follow_spotify_artist_on_muspy(artist_id, artist_name))
            menu.addAction(follow_muspy_action)
        
        # Show the menu
        menu.exec(table.mapToGlobal(position))

    def open_spotify_artist(self, artist_id):
        """Open Spotify artist page in browser"""
        if not artist_id:
            return
            
        url = f"https://open.spotify.com/artist/{artist_id}"
        
        import webbrowser
        webbrowser.open(url)

    def open_spotify_album(self, album_id):
        """Open Spotify album page in browser"""
        if not album_id:
            return
            
        url = f"https://open.spotify.com/album/{album_id}"
        
        import webbrowser
        webbrowser.open(url)

    def follow_spotify_artist_on_muspy(self, artist_id, artist_name):
        """
        Follow a Spotify artist on Muspy by first finding their MBID
        
        Args:
            artist_id (str): Spotify ID of the artist
            artist_name (str): Name of the artist
        """
        # First get the MBID by searching for the artist name
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Searching for MusicBrainz ID for {artist_name}...")
        QApplication.processEvents()
        
        mbid = self.get_mbid_artist_searched(artist_name)
        
        if mbid:
            # Store current artist
            self.current_artist = {"name": artist_name, "mbid": mbid}
            
            # Follow the artist
            success = self.add_artist_to_muspy(mbid, artist_name)
            
            if success:
                self.results_text.append(f"Successfully added {artist_name} to Muspy")
                QMessageBox.information(self, "Success", f"Now following {artist_name} on Muspy")
            else:
                self.results_text.append(f"Failed to add {artist_name} to Muspy")
                QMessageBox.warning(self, "Error", f"Could not follow {artist_name} on Muspy")
        else:
            self.results_text.append(f"Could not find MusicBrainz ID for {artist_name}")
            QMessageBox.warning(self, "Error", f"Could not find MusicBrainz ID for {artist_name}")

    def get_spotify_artist_albums(self, artist_id, artist_name):
        """
        Get and display all albums for a Spotify artist
        
        Args:
            artist_id (str): Spotify ID of the artist
            artist_name (str): Name of the artist
        """
        # Make sure we're showing the text page during loading
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Retrieving albums for {artist_name}...")
        QApplication.processEvents()
        
        # Get Spotify client
        spotify_client = self.spotify_auth.get_client()
        if not spotify_client:
            self.results_text.append("Failed to get Spotify client. Please check authentication.")
            return
        
        # Function to fetch albums with progress dialog
        def fetch_artist_albums(update_progress):
            try:
                update_progress(0, 100, "Connecting to Spotify API...")
                
                all_albums = []
                album_types = ['album', 'single', 'compilation']
                
                for i, album_type in enumerate(album_types):
                    progress = i * 30
                    update_progress(progress, 100, f"Fetching {album_type}s...")
                    
                    offset = 0
                    limit = 50  # Spotify's maximum
                    total = 1  # Will be updated after first request
                    
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
                            # Get albums from this page
                            albums_page = results['items']
                            
                            # Add albums to our list
                            for album in albums_page:
                                # Add album type for filtering
                                album['fetch_type'] = album_type
                                all_albums.append(album)
                            
                            # Update total count
                            total = results['total']
                            
                            # If we got fewer than requested, we're done
                            if len(albums_page) < limit:
                                break
                                
                            # Update offset
                            offset += len(albums_page)
                        else:
                            # No more results or error
                            break
                
                # Process albums data
                update_progress(95, 100, "Processing album data...")
                
                # Remove duplicates (sometimes the same album appears in different categories)
                unique_albums = {}
                for album in all_albums:
                    album_id = album.get('id')
                    if album_id and album_id not in unique_albums:
                        unique_albums[album_id] = album
                
                # Convert to list and sort by release date (newest first)
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
                
                update_progress(100, 100, "Complete!")
                
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
        result = self.show_progress_operation(
            fetch_artist_albums,
            title=f"Loading Albums for {artist_name}",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            albums = result.get("albums", [])
            
            if not albums:
                self.results_text.append(f"No albums found for {artist_name}.")
                return
            
            # Display albums in the stack widget table
            self.display_spotify_artist_albums_in_stacked_widget(albums, artist_name)
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.results_text.append(f"Error: {error_msg}")
            QMessageBox.warning(self, "Error", f"Could not load albums: {error_msg}")

    def display_spotify_artist_albums_in_stacked_widget(self, albums, artist_name):
        """
        Display albums for a specific Spotify artist in the stacked widget
        
        Args:
            albums (list): List of album dictionaries
            artist_name (str): Name of the artist
        """
        # Find the stacked widget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the spotify_releases_page (we'll reuse it for albums)
        spotify_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "spotify_releases_page":
                spotify_page = widget
                break
        
        if not spotify_page:
            self.logger.error("spotify_releases_page not found in stacked widget")
            # Fallback to text display
            self._display_spotify_artist_albums_as_text(albums, artist_name)
            return
        
        # Get the table from the page
        table = spotify_page.findChild(QTableWidget, "spotify_releases_table")
        if not table:
            self.logger.error("spotify_releases_table not found in spotify_releases_page")
            # Fallback to text display
            self._display_spotify_artist_albums_as_text(albums, artist_name)
            return
        
        # Get the count label
        count_label = spotify_page.findChild(QLabel, "spotify_releases_count_label")
        if count_label:
            count_label.setText(f"Showing {len(albums)} albums for {artist_name}")
        
        # Configure table
        table.setRowCount(len(albums))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table with data
        for i, album in enumerate(albums):
            # Artist column
            artist_item = QTableWidgetItem(artist_name)
            table.setItem(i, 0, artist_item)
            
            # Title column
            title_item = QTableWidgetItem(album.get('title', 'Unknown'))
            table.setItem(i, 1, title_item)
            
            # Type column
            type_item = QTableWidgetItem(album.get('type', ''))
            table.setItem(i, 2, type_item)
            
            # Date column
            date_item = QTableWidgetItem(album.get('date', ''))
            table.setItem(i, 3, date_item)
            
            # Tracks column - Usar NumericTableWidgetItem
            tracks_item = NumericTableWidgetItem(str(release.get('total_tracks', 0)))
            tracks_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 4, tracks_item)
            
            # Store the Spotify IDs for context menu actions
            for col in range(table.columnCount()):
                if table.item(i, col):
                    # Store both album ID and artist ID
                    item_data = {
                        'release_id': album.get('id', ''),
                        'artist_id': album.get('artist_id', '')
                    }
                    table.item(i, col).setData(Qt.ItemDataRole.UserRole, item_data)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
        
        # Configure context menu for the table
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_spotify_release_context_menu)
        
        # Switch to the Spotify releases page
        stack_widget.setCurrentWidget(spotify_page)

    def _display_spotify_artist_albums_as_text(self, albums, artist_name):
        """
        Display albums for a specific Spotify artist as text in the results area
        
        Args:
            albums (list): List of album dictionaries
            artist_name (str): Name of the artist
        """
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Found {len(albums)} albums for {artist_name}")
        self.results_text.append("-" * 50)
        
        # Group by type
        albums_by_type = {}
        for album in albums:
            album_type = album.get('type', 'Unknown').title()
            if album_type not in albums_by_type:
                albums_by_type[album_type] = []
            albums_by_type[album_type].append(album)
        
        # Display by type
        for album_type, type_albums in albums_by_type.items():
            self.results_text.append(f"\n{album_type}s ({len(type_albums)}):")
            self.results_text.append("-" * 30)
            
            # Sort by date (newest first)
            sorted_albums = sorted(type_albums, key=lambda x: x.get('date', '0000-00-00'), reverse=True)
            
            for i, album in enumerate(sorted_albums):
                title = album.get('title', 'Unknown')
                date = album.get('date', '')
                tracks = album.get('total_tracks', 0)
                
                self.results_text.append(f"{i+1}. {title}")
                if date:
                    self.results_text.append(f"   Released: {date}")
                self.results_text.append(f"   Tracks: {tracks}")
                self.results_text.append("")
        
        self.results_text.append("-" * 50)

    def spotify_cache_manager(self, cache_key, data=None, force_refresh=False, expiry_hours=24):
        """
        Manages caching for Spotify data
        
        Args:
            cache_key (str): Unique key for the cache entry
            data (dict, optional): Data to cache. If None, retrieves cache.
            force_refresh (bool): Whether to ignore cache and force refresh
            expiry_hours (int): Hours after which cache expires (default 24)
                
        Returns:
            dict or None: Cached data if available and not expired, None otherwise
        """
        import json
        import os
        import time
        
        # Ensure cache directory exists
        cache_dir = os.path.join(PROJECT_ROOT, ".content", "cache", "muspy", "spotify")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Define cache file path
        cache_file = os.path.join(cache_dir, f"{cache_key}_cache.json")
        
        # If we're storing data
        if data is not None:
            cache_data = {
                "timestamp": time.time(),
                "data": data
            }
            
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                self.logger.debug(f"Cached Spotify {cache_key} data successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error caching Spotify {cache_key} data: {e}")
                return False
        
        # If we're retrieving data
        else:
            # If force refresh, don't use cache
            if force_refresh:
                return None
                    
            # Check if cache file exists
            if not os.path.exists(cache_file):
                return None
                    
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                        
                # Check if cache is expired
                timestamp = cache_data.get("timestamp", 0)
                expiry_time = timestamp + (expiry_hours * 3600)  # Convert hours to seconds
                    
                if time.time() > expiry_time:
                    self.logger.debug(f"Spotify {cache_key} cache expired")
                    return None
                        
                # Cache is valid
                self.logger.debug(f"Using cached Spotify {cache_key} data")
                return cache_data.get("data")
                    
            except Exception as e:
                self.logger.error(f"Error loading Spotify {cache_key} cache: {e}")
                return None

    def clear_spotify_cache(self):
        """
        Clear all Spotify cache files
        """
        import os
        import glob
        
        # Ensure cache directory exists
        cache_dir = os.path.join(PROJECT_ROOT, ".content", "cache", "muspy", "spotify")
        
        if not os.path.exists(cache_dir):
            QMessageBox.information(self, "Cache", "No hay archivos de caché para limpiar.")
            return
        
        try:
            # Find all Spotify cache files
            cache_files = glob.glob(os.path.join(cache_dir, "*_cache.json"))
            
            if not cache_files:
                QMessageBox.information(self, "Cache", "No hay archivos de caché para limpiar.")
                return
            
            # Delete each cache file
            count = 0
            for cache_file in cache_files:
                try:
                    os.remove(cache_file)
                    count += 1
                except Exception as e:
                    self.logger.error(f"Error removing cache file {cache_file}: {e}")
            
            QMessageBox.information(self, "Cache limpiada", f"Se han eliminado {count} archivos de caché de Spotify.")
        except Exception as e:
            self.logger.error(f"Error clearing Spotify cache: {e}")
            QMessageBox.warning(self, "Error", f"Error al limpiar la caché: {e}")


# MENU CONTEXTUAL TABLAS:

    def show_unified_context_menu(self, position):
        """
        Unified context menu handler for all tables in the application
        
        Args:
            position (QPoint): Position where the context menu was requested
        """
        # Get the sender table widget
        table = self.sender()
        if not table:
            return
            
        # Get the item at the position
        item = table.itemAt(position)
        if not item:
            return
            
        # Get the table name
        table_name = table.objectName()
        
        # Get the row of the item
        row = item.row()
        
        # Extract information based on table type
        info = self._extract_item_info(table, row, table_name)
        if not info:
            return
            
        # Create the context menu
        menu = QMenu(self)
        
        # Add actions based on available information
        self._build_context_menu(menu, info, table_name)
        
        # Show the menu
        menu.exec(table.mapToGlobal(position))

    def _extract_item_info(self, table, row, table_name):
        """
        Extract item information based on the table type
        
        Args:
            table (QTableWidget): The table widget
            row (int): Row index of the selected item
            table_name (str): Name of the table widget
            
        Returns:
            dict: Dictionary with extracted information or None if extraction failed
        """
        info = {
            'artist_name': None,
            'artist_mbid': None,
            'release_title': None,
            'release_mbid': None,
            'spotify_artist_id': None,
            'spotify_release_id': None
        }
        
        try:
            # MusicBrainz collection table
            if table_name == "tabla_musicbrainz_collection":
                # Artist name is in column 0
                if table.item(row, 0):
                    info['artist_name'] = table.item(row, 0).text()
                
                # Artist MBID is in column 1
                if table.columnCount() > 1 and table.item(row, 1):
                    info['artist_mbid'] = table.item(row, 1).text()
                    
                # Release title is in column 2
                if table.columnCount() > 2 and table.item(row, 2):
                    info['release_title'] = table.item(row, 2).text()
                    
                # Release MBID might be stored in the item data
                if table.item(row, 0):
                    info['release_mbid'] = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                    
            # Spotify artists table
            elif table_name == "spotify_artists_table":
                # Artist name is in column 0
                if table.item(row, 0):
                    info['artist_name'] = table.item(row, 0).text()
                    
                # Spotify artist ID might be stored in the item data
                if table.item(row, 0):
                    info['spotify_artist_id'] = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                    
            # Artists table
            elif table_name == "tableWidget_artists":
                # Artist name is in column 0
                if table.item(row, 0):
                    info['artist_name'] = table.item(row, 0).text()
                    
                # Artist MBID might be in column 1 or in the item data
                if table.columnCount() > 1 and table.item(row, 1):
                    mbid_col = table.item(row, 1).text()
                    if len(mbid_col) == 36 and mbid_col.count('-') == 4:
                        info['artist_mbid'] = mbid_col
                
                # Try to get MBID from data if not found in columns
                if not info['artist_mbid'] and table.item(row, 0):
                    data = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                    if isinstance(data, dict) and 'mbid' in data:
                        info['artist_mbid'] = data['mbid']
                    
            # Songs table
            elif table_name == "tableWidget_songs":
                # Artist name is usually in column 0 or 1
                for col in [0, 1]:
                    if col < table.columnCount() and table.item(row, col):
                        text = table.item(row, col).text()
                        if text and not any(char.isdigit() for char in text):
                            info['artist_name'] = text
                            break
                
                # Try to get data from item
                if table.item(row, 0):
                    data = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                    if isinstance(data, dict):
                        if 'artist_mbid' in data:
                            info['artist_mbid'] = data['artist_mbid']
                        elif 'mbid' in data:
                            info['artist_mbid'] = data['mbid']
                        
            # Releases table
            elif table_name == "tableWidget_releases" or table_name == "tableWidget_muspy_results":
                # Artist name is in column 0
                if table.item(row, 0):
                    info['artist_name'] = table.item(row, 0).text()
                    
                # Release title is in column 1
                if table.columnCount() > 1 and table.item(row, 1):
                    info['release_title'] = table.item(row, 1).text()
                    
                # Try to get MBID from data
                if table.item(row, 0):
                    data = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                    if isinstance(data, dict):
                        if 'artist_mbid' in data:
                            info['artist_mbid'] = data['artist_mbid']
                        elif 'mbid' in data:
                            info['artist_mbid'] = data['mbid']
                        
                        if 'release_mbid' in data:
                            info['release_mbid'] = data['release_mbid']
                    
            # For any other table, try some common patterns
            else:
                # Try to find artist name in first 2 columns
                for col in range(min(2, table.columnCount())):
                    if table.item(row, col):
                        info['artist_name'] = table.item(row, col).text()
                        break
                
                # Try to get data from item
                if table.item(row, 0):
                    data = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                    if isinstance(data, dict):
                        if 'artist_mbid' in data:
                            info['artist_mbid'] = data['artist_mbid']
                        elif 'mbid' in data:
                            info['artist_mbid'] = data['mbid']
                        
                        if 'artist_name' in data:
                            info['artist_name'] = data['artist_name']
            
            return info
        
        except Exception as e:
            self.logger.error(f"Error extracting item info: {e}", exc_info=True)
            return None


    def _build_context_menu(self, menu, info, table_name):
        """
        Build context menu based on available information
        
        Args:
            menu (QMenu): The menu to populate
            info (dict): Dictionary with extracted information
            table_name (str): Name of the table widget
        """
        artist_name = info.get('artist_name')
        artist_mbid = info.get('artist_mbid')
        release_title = info.get('release_title')
        release_mbid = info.get('release_mbid')
        spotify_artist_id = info.get('spotify_artist_id')
        
        # Add artist-related actions if we have an artist name
        if artist_name:
            # Muspy follow/unfollow actions
            if self.muspy_username and self.muspy_api_key:
                if artist_mbid:
                    # Follow using MBID (more reliable)
                    follow_muspy_action = QAction(f"Follow '{artist_name}' on Muspy", self)
                    follow_muspy_action.triggered.connect(lambda: self.add_artist_to_muspy(artist_mbid, artist_name))
                    menu.addAction(follow_muspy_action)
                    
                    # Add unfollow option too
                    unfollow_muspy_action = QAction(f"Unfollow '{artist_name}' from Muspy", self)
                    unfollow_muspy_action.triggered.connect(lambda: self.unfollow_artist_from_muspy_with_confirm(artist_mbid, artist_name))
                    menu.addAction(unfollow_muspy_action)
                else:
                    # Search for MBID first
                    follow_muspy_action = QAction(f"Follow '{artist_name}' on Muspy (search by name)", self)
                    follow_muspy_action.triggered.connect(lambda: self.follow_artist_from_name(artist_name))
                    menu.addAction(follow_muspy_action)
            
            # Spotify follow/unfollow actions
            if self.spotify_enabled:
                if spotify_artist_id:
                    # Follow using Spotify ID
                    follow_spotify_action = QAction(f"Follow '{artist_name}' on Spotify", self)
                    follow_spotify_action.triggered.connect(lambda: self.follow_artist_on_spotify_by_id(spotify_artist_id))
                    menu.addAction(follow_spotify_action)
                    
                    # Add unfollow option
                    unfollow_spotify_action = QAction(f"Unfollow '{artist_name}' from Spotify", self)
                    unfollow_spotify_action.triggered.connect(lambda: self.unfollow_artist_from_spotify_with_confirm(spotify_artist_id, artist_name))
                    menu.addAction(unfollow_spotify_action)
                else:
                    # Search by name
                    follow_spotify_action = QAction(f"Follow '{artist_name}' on Spotify (search by name)", self)
                    follow_spotify_action.triggered.connect(lambda: self.follow_artist_on_spotify_by_name(artist_name))
                    menu.addAction(follow_spotify_action)
            
            # View artist info (MusicBrainz, Spotify, etc.)
            menu.addSeparator()
            
            # MusicBrainz actions
            if artist_mbid:
                view_mb_action = QAction(f"View '{artist_name}' on MusicBrainz", self)
                view_mb_action.triggered.connect(lambda: self.open_musicbrainz_artist(artist_mbid))
                menu.addAction(view_mb_action)
            
            # Spotify actions
            if spotify_artist_id:
                view_spotify_action = QAction(f"View '{artist_name}' on Spotify", self)
                view_spotify_action.triggered.connect(lambda: self.open_spotify_artist(spotify_artist_id))
                menu.addAction(view_spotify_action)
            elif self.spotify_enabled:
                # Search on Spotify
                search_spotify_action = QAction(f"Search '{artist_name}' on Spotify", self)
                search_spotify_action.triggered.connect(lambda: self.search_and_open_spotify_artist(artist_name))
                menu.addAction(search_spotify_action)
            
            # Add Last.fm actions if applicable
            if self.lastfm_enabled and artist_name:
                view_lastfm_action = QAction(f"View '{artist_name}' on Last.fm", self)
                view_lastfm_action.triggered.connect(lambda: self.open_lastfm_artist(artist_name))
                menu.addAction(view_lastfm_action)
        
        # Add release-related actions if we have a release title
        if release_title:
            if menu.actions():  # If we already have actions, add a separator
                menu.addSeparator()
            
            # Add to MusicBrainz collection if we have a release MBID
            if release_mbid and hasattr(self, 'musicbrainz_auth') and self.musicbrainz_enabled:
                # Get collections list if we haven't done so yet
                if not hasattr(self, '_mb_collections') or not self._mb_collections:
                    self._mb_collections = self.fetch_all_musicbrainz_collections()
                
                if hasattr(self, '_mb_collections') and self._mb_collections:
                    # Create a submenu for collections
                    collections_menu = QMenu("Add to Collection", self)
                    
                    for collection in self._mb_collections:
                        collection_name = collection.get('name', 'Unnamed Collection')
                        collection_id = collection.get('id')
                        
                        if collection_id:
                            collection_action = QAction(collection_name, self)
                            collection_action.triggered.connect(
                                lambda checked, cid=collection_id, cname=collection_name, rmbid=release_mbid: 
                                self.add_release_to_collection(cid, cname, rmbid)
                            )
                            collections_menu.addAction(collection_action)
                    
                    menu.addMenu(collections_menu)
            
            # View release info
            if release_mbid:
                view_release_mb_action = QAction(f"View '{release_title}' on MusicBrainz", self)
                view_release_mb_action.triggered.connect(lambda: self.open_musicbrainz_release(release_mbid))
                menu.addAction(view_release_mb_action)


    def unfollow_artist_from_muspy_with_confirm(self, mbid, artist_name):
        """Show confirmation dialog before unfollowing an artist from Muspy"""
        reply = QMessageBox.question(
            self,
            "Confirm Unfollow",
            f"Are you sure you want to unfollow '{artist_name}' from Muspy?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.unfollow_artist_from_muspy(mbid, artist_name)
            
            if success:
                QMessageBox.information(self, "Success", f"Successfully unfollowed {artist_name} from Muspy")
            else:
                QMessageBox.warning(self, "Error", f"Failed to unfollow {artist_name} from Muspy")

    def unfollow_artist_from_spotify_with_confirm(self, artist_id, artist_name):
        """Show confirmation dialog before unfollowing an artist from Spotify"""
        reply = QMessageBox.question(
            self,
            "Confirm Unfollow",
            f"Are you sure you want to unfollow '{artist_name}' from Spotify?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.unfollow_artist_from_spotify(artist_id, artist_name)
            
            if success:
                QMessageBox.information(self, "Success", f"Successfully unfollowed {artist_name} from Spotify")
            else:
                QMessageBox.warning(self, "Error", f"Failed to unfollow {artist_name} from Spotify or not currently following")

    def open_lastfm_artist(self, artist_name):
        """Open Last.fm artist page in browser"""
        if not artist_name:
            return
            
        # URL encode the artist name for the URL
        import urllib.parse
        encoded_name = urllib.parse.quote(artist_name)
        
        url = f"https://www.last.fm/music/{encoded_name}"
        
        import webbrowser
        webbrowser.open(url)


    def follow_artist_on_spotify_by_id(self, artist_id):
        """
        Follow an artist on Spotify using their Spotify ID
        
        Args:
            artist_id (str): Spotify ID of the artist
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self, "Error", "Spotify authentication required")
            return
            
        try:
            # Get Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                QMessageBox.warning(self, "Error", "Failed to get Spotify client")
                return
                
            # Check if already following
            is_following = spotify_client.current_user_following_artists([artist_id])
            if is_following and is_following[0]:
                QMessageBox.information(self, "Already Following", "You are already following this artist on Spotify")
                return
                
            # Follow the artist
            spotify_client.user_follow_artists([artist_id])
            QMessageBox.information(self, "Success", "Successfully followed artist on Spotify")
            
        except Exception as e:
            self.logger.error(f"Error following artist on Spotify: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to follow artist on Spotify: {e}")

    def follow_artist_on_spotify_by_name(self, artist_name):
        """
        Search for an artist on Spotify by name and follow them
        
        Args:
            artist_name (str): Name of the artist
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self, "Error", "Spotify authentication required")
            return
            
        try:
            # Get Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                QMessageBox.warning(self, "Error", "Failed to get Spotify client")
                return
                
            # Search for the artist
            results = spotify_client.search(q=f'artist:"{artist_name}"', type='artist', limit=1)
            
            if not results or not results.get('artists') or not results['artists'].get('items'):
                QMessageBox.warning(self, "Not Found", f"Could not find artist '{artist_name}' on Spotify")
                return
                
            # Get the artist ID
            artist = results['artists']['items'][0]
            artist_id = artist['id']
            
            # Check if already following
            is_following = spotify_client.current_user_following_artists([artist_id])
            if is_following and is_following[0]:
                QMessageBox.information(self, "Already Following", f"You are already following {artist['name']} on Spotify")
                return
                
            # Follow the artist
            spotify_client.user_follow_artists([artist_id])
            QMessageBox.information(self, "Success", f"Successfully followed {artist['name']} on Spotify")
            
        except Exception as e:
            self.logger.error(f"Error following artist on Spotify: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to follow artist on Spotify: {e}")

    def search_and_open_spotify_artist(self, artist_name):
        """
        Search for an artist on Spotify by name and open their page
        
        Args:
            artist_name (str): Name of the artist
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self, "Error", "Spotify authentication required")
            return
            
        try:
            # Get Spotify client
            spotify_client = self.spotify_auth.get_client()
            if not spotify_client:
                QMessageBox.warning(self, "Error", "Failed to get Spotify client")
                return
                
            # Search for the artist
            results = spotify_client.search(q=f'artist:"{artist_name}"', type='artist', limit=1)
            
            if not results or not results.get('artists') or not results['artists'].get('items'):
                QMessageBox.warning(self, "Not Found", f"Could not find artist '{artist_name}' on Spotify")
                return
                
            # Get the artist ID
            artist = results['artists']['items'][0]
            artist_id = artist['id']
            
            # Open the artist page
            self.open_spotify_artist(artist_id)
            
        except Exception as e:
            self.logger.error(f"Error searching artist on Spotify: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to search for artist on Spotify: {e}")

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


    def setup_table_context_menus(self):
        """
        Set up context menus for all tables in the application
        """
        # List of table object names to configure
        table_names = [
            "tabla_musicbrainz_collection",
            "spotify_artists_table",
            "artists_table",
            "loved_songs_table",
            "releases_table",
            "tableWidget_muspy_results"
        ]
        
        # Find and configure each table
        for table_name in table_names:
            table = self.findChild(QTableWidget, table_name)
            if table:
                # Set context menu policy
                table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                
                # Connect signal to unified handler
                table.customContextMenuRequested.disconnect() if table.receivers(table.customContextMenuRequested) > 0 else None
                table.customContextMenuRequested.connect(self.show_unified_context_menu)
                
                self.logger.debug(f"Set up context menu for table: {table_name}")


   

  



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


def main():
    """Main function to run the Muspy Artist Management Module"""
    app = QApplication(sys.argv)
    
    # Parse command-line arguments
    muspy_username = None
    muspy_api_key = None
    artists_file = None
    query_db_script_path = None
    #search_mbid_script_path = None
    db_path = None
    for arg in sys.argv[1:]:
        if arg.startswith('--muspy-username='):
            muspy_username = arg.split('=')[1]
        elif arg.startswith('--muspy-api-key='):
            muspy_api_key = arg.split('=')[1]
        elif arg.startswith('--artists-file='):
            artists_file = arg.split('=')[1]
        elif arg.startswith('--query-db-script-path='):
            query_db_script_path = arg.split('=')[1]
        # elif arg.startswith('--search-mbid-script-path='):
        #     search_mbid_script_path = arg.split('=')[1]
        elif arg.startswith('--lastfm-username='):
            lastfm_username = arg.split('=')[1]
        elif arg.startswith('--db-path='):
            db_path = arg.split('=')[1]

    # Create module instance
    module = MuspyArtistModule(
        muspy_username=muspy_username, 
        muspy_api_key=muspy_api_key,
        artists_file=artists_file,
        query_db_script_path=query_db_script_path,
        #search_mbid_script_path=search_mbid_script_path,
        lastfm_username=lastfm_username,
        db_path=db_path
    )
    module.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
