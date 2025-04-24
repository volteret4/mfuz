# muspy_releases_module.py
import sys
import os
import json
import logging
import datetime
from pathlib import Path
import subprocess
import requests
from PyQt6 import uic
from modules.submodules.muspy import progress_utils, cache_manager, spotify_manager
try:
    from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
                                QLabel, QLineEdit, QMessageBox, QApplication, QFileDialog, QTableWidget, 
                                QTableWidgetItem, QHeaderView, QDialog, QCheckBox, QScrollArea, QDialogButtonBox,
                                QMenu, QInputDialog, QTreeWidget, QTreeWidgetItem, QProgressDialog, QSizePolicy,
                                QStackedWidget, QSpinBox, QComboBox, QAbstractItemView, QMenu)
    from PyQt6.QtCore import pyqtSignal, Qt, QPoint, QObject, QThread, QSize, QEvent
    from PyQt6.QtGui import QColor, QTextDocument, QAction, QCursor, QTextCursor, QIcon, QShortcut, QKeySequence
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("PyQt6 not available. UI functionality will be limited.")

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule, THEMES, PROJECT_ROOT
import resources_rc

# Importar los submodulos
from modules.submodules.muspy.table_widgets import NumericTableWidgetItem, DateTableWidgetItem
from modules.submodules.muspy.progress_utils import ProgressWorker, AuthWorker, FloatingNavigationButtons
from modules.submodules.muspy.cache_manager import CacheManager
from modules.submodules.muspy.display_utils import DisplayManager
from modules.submodules.muspy.muspy_manager import MuspyAuthManager
from modules.submodules.muspy.lastfm_manager import LastFMManager
from modules.submodules.muspy.spotify_manager import SpotifyManager
from modules.submodules.muspy.mb_manager import MusicBrainzManager
from modules.submodules.muspy.bluesky_manager import BlueskyManager

from modules.submodules.muspy.utils import MuspyUtils
from modules.submodules.muspy.twitter_manager import TwitterManager


# Intentar importar módulos específicos que podrían no estar disponibles
try:
    from spotipy.oauth2 import SpotifyOAuth
    from tools.spotify_login import SpotifyAuthManager
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False
    logger = logging.getLogger("MuspyArtistModule")
    logger.warning("Spotipy/Spotify modules not available. Spotify features will be disabled.")

try:
    from tools.lastfm_login import LastFMAuthManager
    LASTFM_AVAILABLE = True
except ImportError:
    LASTFM_AVAILABLE = False
    logger = logging.getLogger("MuspyArtistModule")
    logger.warning("LastFM module not available. LastFM features will be disabled.")

# Filtro para logs de PyQt
class PyQtFilter(logging.Filter):
    def filter(self, record):
        # Filter PyQt messages
        if record.name.startswith('PyQt6'):
            return False
        return True

# Aplicar el filtro al logger global
logging.getLogger().addFilter(PyQtFilter())

# Configurar un logger básico
logger = logging.getLogger("MuspyArtistModule")

# Intentar configurar un logger mejor si está disponible
try:
    from loggin_helper import setup_module_logger
    logger = setup_module_logger(
        module_name="MuspyArtistModule",
        log_level="INFO",
        log_types=["ERROR", "INFO", "WARNING", "UI"]
    )
except ImportError:
    # Fallback al logging estándar
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MuspyArtistModule")


class UICallback:
    def __init__(self, text_widget, **args):
        self.text_widget = text_widget
        
    def clear(self):
        """Limpia el contenido del widget de texto"""
        if self.text_widget:
            self.text_widget.clear()
            
    def append(self, text):
        """Añade texto al widget"""
        if self.text_widget:
            self.text_widget.append(text)
            
    def show(self):
        """Muestra el widget de texto"""
        if self.text_widget:
            self.text_widget.show()
            
    def hide(self):
        """Oculta el widget de texto"""
        if self.text_widget:
            self.text_widget.hide()

    def set_html(self, html_content):
        """Establece contenido HTML"""
        if self.text_widget:
            self.text_widget.setHtml(html_content)
            
    # Métodos para manejo de cursores
    def cursor_for_position(self, position):
        """Obtiene el cursor para una posición dada"""
        if self.text_widget:
            return self.text_widget.cursorForPosition(position)
        return None
        
    def get_text_cursor(self):
        """Obtiene el cursor de texto actual"""
        if self.text_widget:
            return self.text_widget.textCursor()
        return None
        
    def set_text_cursor(self, cursor):
        """Establece el cursor de texto"""
        if self.text_widget and cursor:
            self.text_widget.setTextCursor(cursor)
            
    def insert_html(self, html):
        """Inserta HTML en la posición actual del cursor"""
        if self.text_widget:
            cursor = self.text_widget.textCursor()
            cursor.insertHtml(html)
            
    # Métodos para menús contextuales
    def set_context_menu_policy(self, policy):
        """Establece la política de menú contextual"""
        if self.text_widget:
            self.text_widget.setContextMenuPolicy(policy)
            
    def connect_context_menu(self, callback):
        """Conecta la señal de menú contextual a un callback"""
        if self.text_widget:
            self.text_widget.customContextMenuRequested.connect(callback)
            
    def map_to_global(self, position):
        """Mapea una posición local a coordenadas globales"""
        if self.text_widget:
            return self.text_widget.mapToGlobal(position)
        return position

    def add_artist_to_muspy_silent(self, mbid, artist_name):
        return self.add_artist_to_muspy_silent(mbid, artist_name)


class TwitterAuthWorker(QThread):
    """Worker para autenticación de Twitter en segundo plano"""
    auth_completed = pyqtSignal(bool)
    
    def __init__(self, twitter_auth=None):
        """
        Inicializa el worker de autenticación
        
        Args:
            twitter_auth: Gestor de autenticación de Twitter
        """
        super().__init__()
        self.twitter_auth = twitter_auth
        
    def run(self):
        """Ejecuta la autenticación en segundo plano"""
        if not self.twitter_auth:
            self.auth_completed.emit(False)
            return
            
        try:
            result = self.twitter_auth.authenticate(silent=True)
            self.auth_completed.emit(result)
        except Exception as e:
            self.logger.error(f"Error en worker de autenticación Twitter: {e}", exc_info=True)
            self.auth_completed.emit(False)


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
            bluesky_password=None,
            twitter_username=None,
            twitter_client_id=None,
            twitter_client_secret=None,
            twitter_redirect_uri=None,
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

        # Muspy
        self.muspy_username = muspy_username
        self.muspy_password = muspy_password
        self.muspy_api_key = muspy_api_key
        self.muspy_id = muspy_id
        self.muspy_base_url = "https://muspy.com/api/1"
        self.artists_file = artists_file
        
        # Rutas
        self.query_db_script_path = query_db_script_path
        self.db_path = db_path
        
        # Bluesky
        self.bluesky_username = bluesky_username
        self.bluesky_password = bluesky_password

        # Twitter
        self.twitter_username = twitter_username
        self.twitter_client_id = twitter_client_id
        self.twitter_client_secret = twitter_client_secret
        self.twitter_redirect_uri = twitter_redirect_uri
        

        
        # Inicializar managers
        self.cache_manager = CacheManager(PROJECT_ROOT)
        
        # Set up a basic logger early so it's available before super().__init__()
        self.logger = logging.getLogger(self.module_name)
        
        # Initialize MusicBrainz credentials & manager
        self.musicbrainz_username = kwargs.get('musicbrainz_username', musicbrainz_username)
        self.musicbrainz_password = kwargs.get('musicbrainz_password', musicbrainz_password)
        self.musicbrainz_enabled = bool(self.musicbrainz_username and self.musicbrainz_password)
        
        # Check global theme config for credentials for mb if not already set
        global_config = kwargs.get('global_theme_config', {})
        if global_config:
            if not self.musicbrainz_username and 'musicbrainz_username' in global_config:
                self.musicbrainz_username = global_config['musicbrainz_username']
            if not self.musicbrainz_password and 'musicbrainz_password' in global_config:
                self.musicbrainz_password = global_config['musicbrainz_password']
        
        # Twitter credentials
        global_config = kwargs.get('global_theme_config', {})
        if global_config:
            if not self.twitter_client_id and 'twitter_client_id' in global_config:
                self.twitter_client_id = global_config['twitter_client_id']
            if not self.twitter_client_secret and 'twitter_client_secret' in global_config:
                self.twitter_client_secret = global_config['twitter_client_secret']
            if not self.twitter_redirect_uri and 'twitter_redirect_uri' in global_config:
                self.twitter_redirect_uri = global_config.get('twitter_redirect_uri', "http://localhost:8080/callback")
        
        # Actualizar estado de habilitación de Twitter
        self.twitter_enabled = bool(self.twitter_client_id and self.twitter_client_secret)
        self.logger.info(f"Twitter enabled: {self.twitter_enabled}")
        if self.twitter_enabled:
            self.logger.info(f"Twitter client ID: {self.twitter_client_id[:5]}... (truncated)")

        # Initialize LastFM credentials & manager
        self.lastfm_api_key = lastfm_api_key
        self.lastfm_api_secret = lastfm_api_secret
        self.lastfm_username = lastfm_username
        self.lastfm_enabled = bool(self.lastfm_username and self.lastfm_api_key)
        
        # Initialize Spotify credentials & manager 
        self.spotify_client_id = spotify_client_id
        self.spotify_client_secret = spotify_client_secret
        self.spotify_redirect_uri = spotify_redirect_uri
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        
        # Theme configuration
        self.available_themes = kwargs.pop('temas', [])
        self.selected_theme = kwargs.pop('tema_seleccionado', theme)
        
        # Call super init now that we've set up the required attributes
        super().__init__(parent, theme, **kwargs)
        
        # Set up better logger if enabled
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
            
        self.utils = MuspyUtils(self)            
        self.ui_callback = UICallback(self.results_text)
        self.ui_callback.append(f"MusicBrainz Username: {self.musicbrainz_username}")

        self.progress_utils = FloatingNavigationButtons(self)
        # Initialize managers (AFTER super init)
        self.display_manager = DisplayManager(
            self,
            utils=self.utils,
            )
        self.muspy_manager = MuspyAuthManager(
            parent=self,
            project_root=PROJECT_ROOT,
            muspy_username=self.muspy_username,
            muspy_api_key=self.muspy_api_key,
            muspy_password=self.muspy_password,
            muspy_id=self.muspy_id,
            ui_callback=self.ui_callback,
            display_manager=self.display_manager,
            spotify_client_id=self.spotify_client_id,
            spotify_client_secret=self.spotify_client_secret,
            spotify_redirect_uri=self.spotify_redirect_uri,
            lastfm_api_key=self.lastfm_api_key,
            lastfm_api_secret=self.lastfm_api_secret,
            lastfm_username=self.lastfm_username,
            musicbrainz_username=self.musicbrainz_username,
            musicbrainz_password=self.musicbrainz_password
        )
        
        self.musicbrainz_manager = MusicBrainzManager(
            parent=self,
            project_root=PROJECT_ROOT,
            musicbrainz_username=self.musicbrainz_username,
            musicbrainz_password=self.musicbrainz_password,
            display_manager=self.display_manager,
            ui_callback=self.ui_callback,
            progress_utils=self.progress_utils
        )
        
        self.lastfm_manager = LastFMManager(
            parent=self,
            project_root=PROJECT_ROOT,
            lastfm_api_key=self.lastfm_api_key,
            lastfm_api_secret=self.lastfm_api_secret,
            lastfm_username=self.lastfm_username,
            muspy_id=self.muspy_id,
            ui_callback=self.ui_callback,
            muspy_manager=self.muspy_manager,
            cache_manager=self.cache_manager,
            display_manager=self.display_manager,
            progress_utils=self.progress_utils,
            musicbrainz_manager=self.musicbrainz_manager
        )
        
        self.spotify_manager = SpotifyManager(
            parent=self,
            project_root=PROJECT_ROOT,
            spotify_client_id=self.spotify_client_id,
            spotify_client_secret=self.spotify_client_secret,
            spotify_redirect_uri=self.spotify_redirect_uri,
            ui_callback = self.ui_callback,
            progress_utils=self.progress_utils,
            display_manager=self.display_manager,
            cache_manager=self.cache_manager,
            muspy_manager=self.muspy_manager,
            utils=self.utils
        )
        
        self.bluesky_manager = BlueskyManager(
            parent=self,
            project_root=PROJECT_ROOT,
            bluesky_username=self.bluesky_username,
            bluesky_password=self.bluesky_password,
            ui_callback=self.ui_callback,
            spotify_manager = self.spotify_manager,
            lastfm_manager = self.lastfm_manager,
            musicbrainz_manager = self.musicbrainz_manager,
            display_manager=self.display_manager,
            utils=self.utils
        )
        self.twitter_manager = TwitterManager(
            parent=self,
            project_root=PROJECT_ROOT,
            twitter_client_id=self.twitter_client_id,
            twitter_client_secret=self.twitter_client_secret,
            twitter_redirect_uri=self.twitter_redirect_uri,
            ui_callback=self.ui_callback,
            spotify_manager=self.spotify_manager,
            lastfm_manager=self.lastfm_manager,
            musicbrainz_manager=self.musicbrainz_manager,
            utils=self.utils,
            display_manager=self.display_manager,
            cache_manager=self.cache_manager,
            muspy_manager=self.muspy_manager
        )

        self.display_manager.set_muspy_manager(self.muspy_manager)
        self.display_manager.set_spotify_manager(self.spotify_manager)
        self.display_manager.set_lastfm_manager(self.lastfm_manager)
        self.display_manager.set_bluesky_manager(self.bluesky_manager)

        if hasattr(self, 'stackedWidget'):
            # Asegúrate de crear solo una instancia, almacenada en un atributo
            self.floating_nav = FloatingNavigationButtons(self.stackedWidget, self)

    def _start_background_twitter_auth(self):
        """Inicia la autenticación de Twitter en segundo plano"""
        if not self.twitter_auth:
            self.logger.warning("No se puede iniciar la autenticación sin twitter_auth inicializado")
            return
            
        try:
            # Crear e iniciar worker de autenticación
            from PyQt6.QtCore import QThread, pyqtSignal
            
            class TwitterAuthWorker(QThread):
                """Worker para autenticación de Twitter en segundo plano"""
                auth_completed = pyqtSignal(bool)
                
                def __init__(self, twitter_auth=None, logger=None):
                    super().__init__()
                    self.twitter_auth = twitter_auth
                    self.logger = logger
                    
                def run(self):
                    if not self.twitter_auth:
                        self.auth_completed.emit(False)
                        return
                        
                    try:
                        result = self.twitter_auth.authenticate(silent=True)
                        self.auth_completed.emit(result)
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error en worker de autenticación Twitter: {e}", exc_info=True)
                        self.auth_completed.emit(False)
            
            # Crear y conectar worker
            self.twitter_auth_worker = TwitterAuthWorker(self.twitter_auth, self.logger)
            self.twitter_auth_worker.auth_completed.connect(self._on_twitter_auth_completed)
            self.twitter_auth_worker.start()
            self.logger.info("Iniciada autenticación en segundo plano de Twitter")
        except Exception as e:
            self.logger.error(f"Error iniciando autenticación en segundo plano de Twitter: {e}", exc_info=True)

    def _on_twitter_auth_completed(self, success):
        """Maneja la finalización de la autenticación de Twitter"""
        if success:
            self.logger.info("Autenticación de Twitter completada con éxito")
        else:
            self.logger.warning("Autenticación de Twitter no completada")



    def init_ui(self):
        """Initialize the user interface for Muspy artist management"""
        # Lista de widgets requeridos
        required_widgets = [
            'artist_input', 'search_button', 
            'load_artists_button', 'sync_artists_button', 
            'get_releases_button', 'get_new_releases_button', 'networks_artists_button',
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
                #self.floating_nav = FloatingNavigationButtons(self.stackedWidget, self)
                
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
                if self.musicbrainz_enabled:
                    self.logger.info("Iniciando autenticación automática con MusicBrainz...")
                    # Crear un QTimer para iniciar la autenticación después de que la interfaz esté lista
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(1000, self._start_background_auth)

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
        
        self.networks_artists_button = QPushButton("Obtener todo...")
        bottom_layout.addWidget(self.networks_artists_button)

        main_layout.addLayout(bottom_layout)
        
        # Conectar señales
        self._connect_signals()


# Métodos de navegación y UI:
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
        self.get_new_releases_button.clicked.connect(lambda: self.get_new_releases(PROJECT_ROOT))
        self.networks_artists_button.clicked.connect(self.show_networks_menu)

        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Add keyboard shortcuts for stacked widget navigation
        prev_shortcut = QShortcut(QKeySequence("Alt+Left"), self)
        prev_shortcut.activated.connect(self.go_to_previous_page)  # Cambiado de previous_page a go_to_previous_page
        
        next_shortcut = QShortcut(QKeySequence("Alt+Right"), self)
        next_shortcut.activated.connect(self.go_to_next_page)  # Cambiado de next_page a go_to_next_page

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

        self.get_releases_button.clicked.connect(self.show_releases_menu)

        # Solo crear si no existe ya
        if hasattr(self, 'stackedWidget') and not hasattr(self, 'floating_nav'):
            self.floating_nav = FloatingNavigationButtons(self.stackedWidget, self)




    def go_to_previous_page(self):
        """Navigate to the previous page in the stacked widget"""
        if hasattr(self, 'stackedWidget'):  # Cambiado de stacked_widget a stackedWidget
            current_index = self.stackedWidget.currentIndex()  # Cambiado de stacked_widget a stackedWidget
            if current_index > 0:
                self.stackedWidget.setCurrentIndex(current_index - 1)  # Cambiado de stacked_widget a stackedWidget
            else:
                # Wrap around to the last page
                self.stackedWidget.setCurrentIndex(self.stackedWidget.count() - 1)  # Cambiado de stacked_widget a stackedWidget
                
    def go_to_next_page(self):
        """Navigate to the next page in the stacked widget"""
        if hasattr(self, 'stackedWidget'):  # Cambiado de stacked_widget a stackedWidget
            current_index = self.stackedWidget.currentIndex()  # Cambiado de stacked_widget a stackedWidget
            if current_index < self.stackedWidget.count() - 1:  # Cambiado de stacked_widget a stackedWidget
                self.stackedWidget.setCurrentIndex(current_index + 1)  # Cambiado de stacked_widget a stackedWidget
            else:
                # Wrap around to the first page
                self.stackedWidget.setCurrentIndex(0)  # Cambiado de stacked_widget a stackedWidget


# Manejadores de menús y contextuales:


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






    def show_sync_menu(self):
        """
        Display a menu with sync options when sync_artists_button is clicked
        """
        # Create menu
        menu = QMenu(self)
        
        # Add menu actions
        muspy_action = QAction("Sincronizar base de datos con Muspy", self)
        spotify_action = QAction("Sincronizar base de datos con Spotify", self)
        lastfm_action = QAction("Sincronizar Last.fm con Muspy", self)
        
        # Connect actions to their respective functions
        muspy_action.triggered.connect(self.sync_artists_with_muspy)
        lastfm_action.triggered.connect(self.show_lastfm_sync_dialog)
        spotify_action.triggered.connect(self.sync_spotify_selected_artists)
        
        # Add actions to menu
        menu.addAction(muspy_action)
        menu.addAction(spotify_action)
        menu.addAction(lastfm_action)
        
        # Get the button position
        pos = self.sync_artists_button.mapToGlobal(QPoint(0, self.sync_artists_button.height()))
        
        # Show menu
        menu.exec(pos)





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
        top_artists_action = QAction("Artistas más escuchados", self)
        loved_tracks_action = QAction("Canciones Favoritas", self)
        refresh_cache_action = QAction("Limpiar caché LastFM", self)
        
        # Connect actions
        top_artists_action.triggered.connect(self.lastfm_manager.show_lastfm_top_artists_dialog)
        loved_tracks_action.triggered.connect(self.lastfm_manager.show_lastfm_loved_tracks)
        refresh_cache_action.triggered.connect(self.cache_manager.clear_lastfm_cache)
        
        # Add actions to menu
        menu.addAction(top_artists_action)
        menu.addAction(loved_tracks_action)
        menu.addSeparator()
        menu.addAction(refresh_cache_action)
        
        # Get the button position
        pos = self.sync_lastfm_button.mapToGlobal(QPoint(0, self.sync_lastfm_button.height()))
        
        # Show menu
        menu.exec(pos)



    def show_releases_menu(self):
        """
        Display a menu with release options when get_releases_button is clicked
        """
        # Create menu
        menu = QMenu(self)
        
        # Add menu actions
        my_releases_action = QAction("Mis Próximos Discos", self)
        all_releases_action = QAction("Obtener Todos los Lanzamientos...", self)
        
        # Connect actions to their respective functions
        my_releases_action.triggered.connect(self.get_muspy_releases)
        all_releases_action.triggered.connect(self.show_get_all_releases_dialog)
        
        # Add actions to menu
        menu.addAction(my_releases_action)
        menu.addAction(all_releases_action)
        
        # Get the button position
        pos = self.get_releases_button.mapToGlobal(QPoint(0, self.get_releases_button.height()))
        
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


    def show_twitter_config_info(self):
        """
        Muestra información sobre cómo configurar Twitter
        """
        QMessageBox.information(
            self,
            "Configurar Twitter",
            "Para habilitar la integración con Twitter, necesitas configurar las siguientes variables:\n\n"
            "- twitter_client_id: ID de cliente de la API de Twitter\n"
            "- twitter_client_secret: Secret de cliente de la API de Twitter\n"
            "- twitter_redirect_uri: URI de redirección (opcional)\n\n"
            "Puedes configurar estas variables en el archivo de configuración."
        )





    def show_networks_menu(self):
        """
        Muestra un menú con opciones de integración de redes sociales
        """
        # Crear menú
        menu = QMenu(self)
        
        # Añadir funcionalidad original
        original_action = QAction("Obtener todos los lanzamientos", self)
        original_action.triggered.connect(self.get_all_my_releases)
        menu.addAction(original_action)
        
        menu.addSeparator()
        
        # Opciones de menú para Twitter
        if self.twitter_enabled:
            twitter_menu = QMenu("Twitter / X", self)
            
            # Submenú para sincronización de artistas con Twitter
            sync_twitter_menu = QMenu("Sincronizar artistas con Twitter", self)
            
            # Opciones de sincronización
            spotify_twitter_action = QAction("Sincronizar artistas de Spotify", self)
            spotify_twitter_action.triggered.connect(self.twitter_manager.sync_spotify_artists_with_twitter)
            sync_twitter_menu.addAction(spotify_twitter_action)
            
            # Modificación aquí para usar nuestra nueva función selección-sincronización
            db_twitter_action = QAction("Seleccionar y sincronizar artistas de base de datos", self)
            db_twitter_action.triggered.connect(lambda: self.twitter_manager.show_artist_selection_for_twitter())
            sync_twitter_menu.addAction(db_twitter_action)
            
            mb_twitter_action = QAction("Sincronizar artistas de MusicBrainz", self)
            mb_twitter_action.triggered.connect(self.twitter_manager.sync_mb_artists_with_twitter)
            sync_twitter_menu.addAction(mb_twitter_action)
            
            lastfm_twitter_action = QAction("Sincronizar artistas de LastFM", self)
            lastfm_twitter_action.triggered.connect(self.twitter_manager.show_lastfm_twitter_dialog)
            sync_twitter_menu.addAction(lastfm_twitter_action)
            
            # Añadir submenú de sincronización a menú de Twitter
            twitter_menu.addMenu(sync_twitter_menu)
            
            # Otras opciones de Twitter
            twitter_users_action = QAction("Mostrar usuarios seguidos", self)
            twitter_users_action.triggered.connect(self.twitter_manager.show_twitter_followed_users)
            twitter_menu.addAction(twitter_users_action)
            
            twitter_search_action = QAction("Buscar usuarios", self)
            twitter_search_action.triggered.connect(self.twitter_manager.show_twitter_search_dialog)
            twitter_menu.addAction(twitter_search_action)
            
            twitter_tweets_action = QAction("Ver tweets recientes de artistas", self)
            twitter_tweets_action.triggered.connect(self.twitter_manager.show_twitter_artist_tweets)
            twitter_menu.addAction(twitter_tweets_action)
            
            # Añadir menú de Twitter al menú principal
            menu.addMenu(twitter_menu)
        else:
            # Añadir opción deshabilitada de Twitter con información de configuración
            twitter_config_action = QAction("Configurar Twitter...", self)
            twitter_config_action.triggered.connect(self.show_twitter_config_info)
            menu.addAction(twitter_config_action)
        
        # Opciones de menú para Bluesky
        if self.bluesky_username:
            bluesky_menu = QMenu("Bluesky", self)
            
            db_action = QAction("Seguir artistas base de datos en Bluesky", self)
            spotify_action = QAction("Seguir artistas Spotify en Bluesky", self)
            lastfm_action = QAction("Seguir top artistas LastFM en Bluesky", self)
            mb_action = QAction("Seguir artistas de colección de MusicBrainz en Bluesky", self)
            
            # Conectar acciones
            db_action.triggered.connect(self.bluesky_manager.search_db_artists_on_bluesky)
            spotify_action.triggered.connect(self.bluesky_manager.search_spotify_artists_on_bluesky)
            lastfm_action.triggered.connect(self.bluesky_manager.show_lastfm_bluesky_dialog)
            mb_action.triggered.connect(self.bluesky_manager.search_mb_collection_on_bluesky)
            
            bluesky_menu.addAction(db_action)
            bluesky_menu.addAction(spotify_action)
            bluesky_menu.addAction(lastfm_action)
            bluesky_menu.addAction(mb_action)
            
            menu.addMenu(bluesky_menu)
        else:
            # Añadir opción para configurar Bluesky
            config_action = QAction("Configurar Bluesky...", self)
            config_action.triggered.connect(self.bluesky_manager.configure_bluesky_username)
            menu.addAction(config_action)
        
        # Obtener posición del botón
        pos = self.networks_artists_button.mapToGlobal(QPoint(0, self.networks_artists_button.height()))
        
        # Mostrar menú
        menu.exec(pos)





    # def show_bluesky_menu(self):
    #     """
    #     Display a menu with Bluesky integration options
    #     """
    #     # Check if Bluesky username is configured
    #     if not self.bluesky_username:
    #         # If no username, show a warning but still create the menu
    #         # with options disabled
    #         warning_shown = False
            
    #     # Create the menu
    #     menu = QMenu(self)
        
    #     # Add original functionality
    #     original_action = QAction("Obtener todos los lanzamientos", self)
    #     original_action.triggered.connect(self.get_all_my_releases)
    #     menu.addAction(original_action)
        
    #     menu.addSeparator()
        
    #     # Add Bluesky menu options
    #     db_action = QAction("Seguir artistas base de datos en Bluesky", self)
    #     spotify_action = QAction("Seguir artistas Spotify en Bluesky", self)
    #     lastfm_action = QAction("Seguir top artistas LastFM en Bluesky", self)
    #     mb_action = QAction("Seguir artistas de colección de MusicBrainz en Bluesky", self)
        
    #     # Connect actions
    #     db_action.triggered.connect(self.bluesky_manager.search_db_artists_on_bluesky)
    #     spotify_action.triggered.connect(self.bluesky_manager.search_spotify_artists_on_bluesky)
    #     lastfm_action.triggered.connect(self.bluesky_manager.show_lastfm_bluesky_dialog)
    #     mb_action.triggered.connect(self.bluesky_manager.search_mb_collection_on_bluesky)
        
    #     # If no username, disable all Bluesky-related actions
    #     if not self.bluesky_username:
    #         db_action.setEnabled(False)
    #         spotify_action.setEnabled(False)
    #         lastfm_action.setEnabled(False)
    #         mb_action.setEnabled(False)
            
    #         # Add an action to configure Bluesky
    #         config_action = QAction("Configurar usuario de Bluesky...", self)
    #         config_action.triggered.connect(self.bluesky_manager.configure_bluesky_username)
    #         menu.addAction(config_action)
        
    #     # Add actions to menu
    #     menu.addAction(db_action)
    #     menu.addAction(spotify_action)
    #     menu.addAction(lastfm_action)
    #     menu.addAction(mb_action)
        
    #     # Get button position
    #     pos = self.networks_artists_button.mapToGlobal(QPoint(0, self.networks_artists_button.height()))
        
    #     # Show menu
    #     menu.exec(pos)
        
    #     # Show warning after menu is closed if needed
    #     if not self.bluesky_username and not warning_shown:
    #         QMessageBox.warning(self, "Bluesky no configurado", 
    #                         "No hay usuario de Bluesky configurado. Algunas funciones no estarán disponibles.")


    def show_musicbrainz_collection_menu(self):
        """Display a menu with MusicBrainz collection options"""
        if not self.musicbrainz_enabled:
            QMessageBox.warning(self, "Error", "MusicBrainz credentials not configured")
            return
        
        # Verificar si ya estamos autenticados - SIN INTENTAR AUTENTICARSE
        is_auth = self.musicbrainz_manager.musicbrainz_auth.is_authenticated()
        
        # Crear menu
        menu = QMenu(self)
        
        if not is_auth:
            # Add login action if not authenticated
            login_action = QAction("Login to MusicBrainz...", self)
            login_action.triggered.connect(self.authenticate_musicbrainz_silently)
            menu.addAction(login_action)
        else:
            # Ya estamos autenticados, usar colecciones en caché si disponibles
            collections = []
            if hasattr(self, '_mb_collections') and self._mb_collections:
                collections = self._mb_collections
            else:
                # Try API method first
                if hasattr(self.musicbrainz_manager.musicbrainz_auth, 'get_collections_by_api'):
                    collections = self.musicbrainz_manager.musicbrainz_auth.get_collections_by_api()
                
                # Fallback to HTML parsing if API method failed or doesn't exist
                if not collections and hasattr(self.musicbrainz_manager.musicbrainz_auth, 'get_user_collections'):
                    collections = self.musicbrainz_manager.musicbrainz_auth.get_user_collections()
                
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
            
            # Add separator and cache clearing option instead of logout
            menu.addSeparator()
            clear_cache_action = QAction("Clear MusicBrainz Cache", self)
            clear_cache_action.triggered.connect(lambda: self.musicbrainz_manager._invalidate_collection_cache())
            menu.addAction(clear_cache_action)
        
        # Show the menu at the button position
        if hasattr(self, 'get_releases_musicbrainz'):
            pos = self.get_releases_musicbrainz.mapToGlobal(QPoint(0, self.get_releases_musicbrainz.height()))
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



    def show_spotify_menu(self):
        """
        Display a menu with Spotify options when get_releases_spotify_button is clicked
        """
        if not self.ensure_spotify_auth():
            QMessageBox.warning(self, "Error", "Spotify credentials not configured")
            return
        
        # Create menu
        menu = QMenu(self)
        
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


    def show_get_all_releases_dialog(self):
        """
        Show a dialog to configure options for retrieving all releases
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Obtener Lanzamientos")
        dialog.setMinimumWidth(300)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Limit selection
        limit_layout = QHBoxLayout()
        limit_label = QLabel("Número máximo de lanzamientos:")
        limit_spin = QSpinBox()
        limit_spin.setRange(10, 1000)
        limit_spin.setValue(100)
        limit_spin.setSingleStep(10)
        limit_layout.addWidget(limit_label)
        limit_layout.addWidget(limit_spin)
        layout.addLayout(limit_layout)
        
        # Date filter
        date_filter_check = QCheckBox("Solo lanzamientos para HOY")
        date_filter_check.setChecked(True)
        layout.addWidget(date_filter_check)
        
        # Cache option
        cache_check = QCheckBox("Usar datos en caché si están disponibles")
        cache_check.setChecked(True)
        layout.addWidget(cache_check)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get values
            limit = limit_spin.value()
            future_only = date_filter_check.isChecked()
            use_cache = cache_check.isChecked()
            
            # Call function with selected parameters
            self.get_all_releases(limit=limit, future_only=future_only, use_cache=use_cache)



    def show_lastfm_bluesky_dialog(self):
        """
        Show dialog to select period and number of top artists from LastFM to search on Bluesky
        """
        if not self.lastfm_enabled:
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


    def show_twitter_menu(self):
        """
        Muestra un menú con opciones de Twitter cuando se hace clic en el botón de Twitter
        """
        if not self.twitter_enabled:
            QMessageBox.warning(self, "Error", "Las credenciales de Twitter no están configuradas")
            return
        
        # Crear menú
        menu = QMenu(self)
        
        # Añadir opciones de menú
        show_users_action = QAction("Mostrar usuarios seguidos", self)
        show_search_action = QAction("Buscar usuarios", self)
        show_tweets_action = QAction("Ver tweets recientes de artistas", self)
        
        # Conectar acciones a sus respectivas funciones
        show_users_action.triggered.connect(self.twitter_manager.show_twitter_followed_users)
        show_search_action.triggered.connect(self.twitter_manager.show_twitter_search_dialog)
        show_tweets_action.triggered.connect(self.twitter_manager.show_twitter_artist_tweets)
        
        # Añadir acciones al menú
        menu.addAction(show_users_action)
        menu.addAction(show_search_action)
        menu.addAction(show_tweets_action)
        
        # Añadir separador y opciones extra
        menu.addSeparator()
        
        sync_action = QAction("Sincronizar artistas con Twitter", self)
        sync_action.triggered.connect(self.twitter_manager.sync_artists_with_twitter)
        menu.addAction(sync_action)
        
        # Añadir separador y opción de gestión de caché
        menu.addSeparator()
        clear_cache_action = QAction("Limpiar caché de Twitter", self)
        clear_cache_action.triggered.connect(self.twitter_manager.clear_twitter_cache)
        menu.addAction(clear_cache_action)
        
        # Obtener la posición del botón (asumiendo que existe un botón de Twitter)
        if hasattr(self, 'twitter_button'):
            pos = self.twitter_button.mapToGlobal(QPoint(0, self.twitter_button.height()))
            menu.exec(pos)
        else:
            # Si no hay botón específico, mostrar en la posición actual del cursor
            menu.exec(QCursor.pos())



# Métodos de contexto de tabla:

    
    def setup_table_context_menus(self):
        """
        Set up context menus for all tables in the application
        with improved search for nested widgets and debugging logs
        """
        # Lista de tablas a configurar
        table_names = [
            "tabla_musicbrainz_collection",
            "spotify_artists_table", 
            "artists_table",
            "loved_songs_table",
            "releases_table", 
            "tableWidget_muspy_results"
        ]
        
        # Lista de nombres de widgets padres donde buscar las tablas
        parent_names = [
            "musicbrainz_collection_page",
            "spotify_artists_page",
            "artists_page",
            "loved_tracks_page",
            "releases_page",
            "muspy_results_widget"
        ]
        
        # Buscar tablas en toda la jerarquía
        for table_name, parent_name in zip(table_names, parent_names):
            # Intentar encontrar primero el padre
            parent_widget = self.findChild(QWidget, parent_name)
            
            if parent_widget:
                # Buscar la tabla dentro del padre
                table = parent_widget.findChild(QTableWidget, table_name)
                if table:
                    self.logger.debug(f"Found table {table_name} in parent {parent_name}")
                else:
                    self.logger.debug(f"Table {table_name} not found in parent {parent_name}")
                    # Buscar en stackedWidget como último recurso
                    stackedWidget = self.findChild(QStackedWidget, "stackedWidget")
                    if stackedWidget:
                        # Buscar en todas las páginas del stackedWidget
                        for i in range(stackedWidget.count()):
                            page = stackedWidget.widget(i)
                            if page.objectName() == parent_name:
                                table = page.findChild(QTableWidget, table_name)
                                if table:
                                    self.logger.debug(f"Found table {table_name} in stackedWidget page {parent_name}")
                                    break
            else:
                # Buscar la tabla directamente en el widget principal
                table = self.findChild(QTableWidget, table_name)
                if table:
                    self.logger.debug(f"Found table {table_name} directly in main widget")
            
            if table:
                # Set context menu policy
                table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                
                # Desconectar cualquier conexión previa para evitar duplicados
                try:
                    # Guardar la cantidad de receptores antes de desconectar
                    receivers_before = table.receivers(table.customContextMenuRequested)
                    self.logger.debug(f"Table {table_name} has {receivers_before} receivers before disconnect")
                    
                    if receivers_before > 0:
                        table.customContextMenuRequested.disconnect()
                        self.logger.debug(f"Disconnected signals from table {table_name}")
                except Exception as e:
                    self.logger.debug(f"Error disconnecting signals from {table_name}: {e}")
                
                # Conectar señal a nuestro manejador unificado
                try:
                    # Asegurarse de que la conexión se hace correctamente
                    connected = table.customContextMenuRequested.connect(self.show_unified_context_menu)
                    receivers_after = table.receivers(table.customContextMenuRequested)
                    self.logger.debug(f"Table {table_name} connected to unified menu handler. Receivers: {receivers_after}")
                except Exception as e:
                    self.logger.error(f"Failed to connect context menu for {table_name}: {e}")
                
                # Guardar la referencia a la tabla para uso posterior
                setattr(self, f"_{table_name}_ref", table)
                
                # Loguear éxito
                self.logger.info(f"Successfully set up context menu for table: {table_name}")
            else:
                self.logger.warning(f"Could not find table {table_name} anywhere")

   
  # Modificación para muspy_releases_module.py


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
        
        # Add specific actions for MusicBrainz collection table
        if table_name == "tabla_musicbrainz_collection":
            # Get collection information from table properties
            collection_id = table.property("collection_id")
            collection_name = table.property("collection_name")
            release_mbid = info.get('release_mbid')
            release_title = info.get('release_title')
            
            if collection_id and release_mbid and release_title:
                menu.addSeparator()
                remove_action = QAction(f"Eliminar '{release_title}' de la colección", self)
                remove_action.triggered.connect(
                    lambda: self.musicbrainz_manager.remove_release_from_collection_with_confirm(
                        collection_id, collection_name, release_mbid, release_title)
                )
                menu.addAction(remove_action)
        
        # Show the menu
        menu.exec(table.mapToGlobal(position))


    def _extract_item_info_mb_collection(self, table, row):
        """
        Método especializado para extraer información de una tabla de colección MusicBrainz
        
        Args:
            table (QTableWidget): Tabla de colección MusicBrainz
            row (int): Índice de fila seleccionada
            
        Returns:
            dict: Diccionario con información extraída
        """
        info = {
            'artist_name': None,
            'artist_mbid': None,
            'release_title': None,
            'release_mbid': None
        }
        
        # Extraer información básica de las columnas
        if table.item(row, 0):
            info['artist_name'] = table.item(row, 0).text()
        
        if table.columnCount() > 1 and table.item(row, 1):
            info['artist_mbid'] = table.item(row, 1).text()
            
        if table.columnCount() > 2 and table.item(row, 2):
            info['release_title'] = table.item(row, 2).text()
        
        # INTENTO 1: Obtener release_mbid del dato UserRole
        release_mbid = None
        for col in range(min(7, table.columnCount())):
            if table.item(row, col):
                mbid = table.item(row, col).data(Qt.ItemDataRole.UserRole)
                if mbid and isinstance(mbid, str) and len(mbid) == 36 and mbid.count('-') == 4:
                    release_mbid = mbid
                    break
        
        # INTENTO 2: Obtener del diccionario guardado en UserRole+1
        if not release_mbid and table.item(row, 0):
            data_dict = table.item(row, 0).data(Qt.ItemDataRole.UserRole + 1)
            if isinstance(data_dict, dict) and 'release_mbid' in data_dict:
                release_mbid = data_dict['release_mbid']
        
        # INTENTO 3: Buscar en el texto de la fila si es un MBID válido
        if not release_mbid:
            for col in range(min(7, table.columnCount())):
                if table.item(row, col):
                    text = table.item(row, col).text()
                    if text and len(text) == 36 and text.count('-') == 4:
                        # Parece un MBID válido
                        release_mbid = text
                        break
        
        # Guardar el MBID encontrado
        info['release_mbid'] = release_mbid
        
        # Log para depuración
        self.logger.debug(f"Extracted MusicBrainz info: {info}")
        
        return info


    # Modificación mejorada del método _extract_item_info para usar la función especializada

    def _extract_item_info(self, table, row, table_name):
        """
        Extract item information based on the table type with improved MBID extraction
        
        Args:
            table (QTableWidget): The table widget
            row (int): Row index of the selected item
            table_name (str): Name of the table widget
            
        Returns:
            dict: Dictionary with extracted information or None if extraction failed
        """
        try:
            # MusicBrainz collection table - usar método especializado
            if table_name == "tabla_musicbrainz_collection":
                return self._extract_item_info_mb_collection(table, row)
                
            # Para otras tablas, usar el método general
            info = {
                'artist_name': None,
                'artist_mbid': None,
                'release_title': None,
                'release_mbid': None,
                'spotify_artist_id': None,
                'spotify_release_id': None
            }
            
            # Spotify artists table
            if table_name == "spotify_artists_table":
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
                view_spotify_action.triggered.connect(lambda: self.utils.open_spotify_artist(spotify_artist_id))
                menu.addAction(view_spotify_action)
            elif self.spotify_enabled:
                # Search on Spotify
                search_spotify_action = QAction(f"Search '{artist_name}' on Spotify", self)
                search_spotify_action.triggered.connect(lambda: self.spotify_manager.search_and_open_spotify_artist(artist_name))
                menu.addAction(search_spotify_action)
            
            # Add Last.fm actions if applicable
            if self.lastfm_enabled and artist_name:
                view_lastfm_action = QAction(f"View '{artist_name}' on Last.fm", self)
                view_lastfm_action.triggered.connect(lambda: self.utils.open_lastfm_artist(artist_name))
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
                view_release_mb_action.triggered.connect(lambda: self.musicbrainz_manager.open_musicbrainz_release(release_mbid))
                menu.addAction(view_release_mb_action)


  


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







    def show_progress_operation(self, operation_function, operation_args=None, title="Operación en progreso", 
                            label_format="{current}/{total} - {status}", 
                            cancel_button_text="Cancelar", 
                            finish_message=None):
        """Delegación al método implementado en progress_utils"""
        from modules.submodules.muspy.progress_utils import show_progress_operation
        return show_progress_operation(self, operation_function, operation_args, title, 
                                    label_format, cancel_button_text, finish_message)


    def cache_manager(self, cache_type, data=None, force_refresh=False, expiry_hours=24):
        """Delegación al método implementado en cache_manager"""
        return self.cache_manager.cache_manager(cache_type, data, force_refresh, expiry_hours)

    def spotify_cache_manager(self, cache_key, data=None, force_refresh=False, expiry_hours=24):
        """Delegación al método implementado en cache_manager"""
        return self.cache_manager.spotify_cache_manager(cache_key, data, force_refresh, expiry_hours)


# Gestores de carga de datos

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
            script_path = os.path.join(PROJECT_ROOT, "db", "tools", "consultar_items_db.py")
            
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
            script_path = os.path.join(PROJECT_ROOT, "db", "tools", "consultar_items_db.py")
            
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
                script_path = os.path.join(PROJECT_ROOT, "db", "tools", "consultar_items_db.py")
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

# Métodos principales de interacción


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
            script_path = os.path.join(PROJECT_ROOT, "db", "tools", "consultar_items_db.py")
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
            cached_data = self.cache_manager.cache_manager(cache_key, expiry_hours=12)  # Shorter expiry for releases
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
                url = f"{self.muspy_base_url}/releases/{self.muspy_id}"
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
                    self.cache_manager.cache_manager(cache_key, cache_data, expiry_hours=12)
                    
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
   



    def get_all_releases(self, limit=100, future_only=True, use_cache=True):
        """
        Retrieve releases without requiring a user ID, with optional limits
        
        Args:
            limit (int): Maximum number of releases to retrieve
            future_only (bool): Whether to show only future releases
            use_cache (bool): Whether to use cached data when available
        """
        if not self.muspy_username or not self.muspy_api_key:
            QMessageBox.warning(self, "Error", "Muspy configuration not available")
            return

        # Try to get from cache first if allowed
        cache_key = f"all_releases_{limit}_{future_only}"
        if use_cache:
            cached_data = self.cache_manager.cache_manager(cache_key, expiry_hours=12)  # Shorter expiry for releases
            if cached_data:
                future_releases = cached_data.get("future_releases", [])
                if future_releases:
                    self.display_releases_in_stacked_widget(future_releases)
                    return
                elif cached_data.get("all_releases"):
                    QMessageBox.information(self, "No Future Releases", 
                        f"No se encontraron próximos lanzamientos.\n" +
                        f"(Total de lanzamientos: {len(cached_data.get('all_releases', []))})")
                    return

        # Función de operación con progreso
        def fetch_releases(update_progress):
            update_progress(0, 1, "Conectando con Muspy API...", indeterminate=True)
            
            try:
                # Use the releases endpoint without user ID
                url = f"{self.muspy_base_url}/releases"
                auth = (self.muspy_username, self.muspy_api_key)
                
                all_releases = []
                offset = 0
                page_size = min(100, limit)  # Maximum allowed by API is 100
                more_pages = True
                
                while more_pages and offset < limit:
                    params = {
                        "limit": page_size,
                        "offset": offset
                    }
                    
                    # Update progress message
                    update_progress(0, 1, f"Obteniendo lanzamientos ({offset+1}-{min(offset+page_size, limit)})...", indeterminate=True)
                    
                    response = requests.get(url, auth=auth, params=params)
                    
                    if response.status_code != 200:
                        return {
                            "success": False,
                            "error": f"Error retrieving releases: {response.status_code} - {response.text}"
                        }
                    
                    # Process page results
                    page_releases = response.json()
                    all_releases.extend(page_releases)
                    
                    # Stop if we got fewer items than requested
                    if len(page_releases) < page_size:
                        more_pages = False
                    
                    # Update offset for next page
                    offset += len(page_releases)
                    
                    # Stop if we've reached the limit
                    if offset >= limit:
                        more_pages = False
                
                # Procesando datos
                update_progress(1, 2, "Procesando resultados...", indeterminate=True)
                
                # Filter for future releases if requested
                if future_only:
                    today = datetime.date.today().strftime("%Y-%m-%d")
                    future_releases = [release for release in all_releases if release.get('date', '0000-00-00') >= today]
                else:
                    future_releases = all_releases
                
                # Sort by date
                future_releases.sort(key=lambda x: x.get('date', '0000-00-00'))
                
                # Cache the results
                cache_data = {
                    "all_releases": all_releases,
                    "future_releases": future_releases
                }
                self.cache_manager.cache_manager(cache_key, cache_data, expiry_hours=12)
                
                # Actualizar progreso y terminar
                update_progress(2, 2, "Generando visualización...")
                
                return {
                    "success": True,
                    "all_releases": all_releases,
                    "future_releases": future_releases
                }
            
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Connection error with Muspy: {e}"
                }
        
        # Ejecutar con diálogo de progreso
        result = self.show_progress_operation(
            fetch_releases,
            title="Obteniendo Lanzamientos",
            label_format="{status}"
        )
        
        # Procesar resultados
        if result:
            if result.get("success"):
                all_releases = result.get("all_releases", [])
                future_releases = result.get("future_releases", [])
                
                if not future_releases:
                    QMessageBox.information(self, "No Releases Found", 
                        f"No se encontraron{' próximos' if future_only else ''} lanzamientos.\n" +
                        f"(Total de lanzamientos: {len(all_releases)})")
                    return
                
                # Display releases properly using stacked widget
                self.display_releases_in_stacked_widget(future_releases)
            else:
                error_msg = result.get("error", "Unknown error")
                QMessageBox.warning(self, "Error", error_msg)





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
                    url = f"{self.muspy_base_url}/releases/{self.muspy_id}"
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
        
        script_path = os.path.join(PROJECT_ROOT, "db", "tools", "consultar_items_db.py")
        
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
                    url = f"{self.muspy_base_url}/releases"
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



# Mas funciones


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
            
            url = f"{self.muspy_base_url}/releases"
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
            url = f"{self.muspy_base_url}/releases"
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

    def on_release_double_clicked(self, item, column):
        """Handle double-click on a tree item"""
        # Check if this is a release item
        if item.parent():
            # This is a release, get its data
            release_data = item.data(0, Qt.ItemDataRole.UserRole)
            if release_data and 'mbid' in release_data:
                self.open_musicbrainz_release(release_data)



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


  
    def open_muspy_release(self, release_data):
        """Open a release on Muspy website"""
        if 'mbid' in release_data:
            url = f"https://muspy.com/release/{release_data['mbid']}"
            import webbrowser
            webbrowser.open(url)



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







# Métodos de delegación



    def get_muspy_id(self):
        """Delegación al método implementado en muspy_manager"""
        return self.muspy_manager.get_muspy_id()
        
    def add_artist_to_muspy(self, mbid, artist_name=None):
        """Delegación al método implementado en muspy_manager"""
        return self.muspy_manager.add_artist_to_muspy(mbid, artist_name)
        
    def add_artist_to_muspy_silent(self, mbid, artist_name=None):
        """Delegación al método implementado en muspy_manager"""
        return self.muspy_manager.add_artist_to_muspy_silent(mbid, artist_name)
        
    def unfollow_artist_from_muspy(self, mbid, artist_name=None):
        """Delegación al método implementado en muspy_manager"""
        return self.muspy_manager.unfollow_artist_from_muspy(mbid, artist_name)
        
    def unfollow_artist_from_muspy_with_confirm(self, mbid, artist_name):
        """Delegación al método implementado en muspy_manager"""
        return self.muspy_manager.unfollow_artist_from_muspy_with_confirm(mbid, artist_name)
        
    def get_mbid_artist_searched(self, artist_name):
        """Delegación al método implementado en muspy_manager"""
        return self.muspy_manager.get_mbid_artist_searched(artist_name)
        
    def check_api_credentials(self):
        """Delegación al método implementado en muspy_manager"""
        return self.muspy_manager.check_api_credentials()

    # --- Métodos de delegación para DisplayManager ---
    def show_text_page(self, html_content=None):
        """Delegación al método implementado en display_utils"""
        return self.display_manager.show_text_page(html_content)

    def update_status_text(self, text):
        """Delegación al método implementado en display_utils"""
        return self.display_manager.update_status_text(text)

    def display_releases_in_stacked_widget(self, releases):
        """Delegación al método implementado en display_utils"""
        return self.display_manager.display_releases_in_stacked_widget(releases)

    def display_releases_in_muspy_results_page(self, releases, artist_name=None):
        """Delegación al método implementado en display_utils"""
        return self.display_manager.display_releases_in_muspy_results_page(releases, artist_name)

    def add_follow_button_to_results_page(self, artist_name):
        """Delegación al método implementado en display_utils"""
        return self.display_manager.add_follow_button_to_results_page(artist_name)

    def display_releases_tree(self, releases, group_by_artist=True):
        """Delegación al método implementado en display_utils"""
        return self.display_manager.display_releases_tree(releases, group_by_artist)

    def display_sync_results(self, result):
        """Delegación al método implementado en display_utils"""
        return self.display_manager.display_sync_results(result)

    # --- Métodos de delegación para CacheManager ---
    def cache_manager(self, cache_type, data=None, force_refresh=False, expiry_hours=24):
        """Delegación al método implementado en cache_manager"""
        return self.cache_manager.cache_manager(cache_type, data, force_refresh, expiry_hours)

    def spotify_cache_manager(self, cache_key, data=None, force_refresh=False, expiry_hours=24):
        """Delegación al método implementado en cache_manager"""
        return self.cache_manager.spotify_cache_manager(cache_key, data, force_refresh, expiry_hours)

    def clear_lastfm_cache(self):
        """Delegación al método implementado en cache_manager"""
        count = self.cache_manager.clear_lastfm_cache()
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Cache Cleared", f"Cleared {count} LastFM cache files")

    def clear_spotify_cache(self):
        """Delegación al método implementado en cache_manager"""
        count = self.cache_manager.clear_spotify_cache()
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Cache limpiada", f"Se han eliminado {count} archivos de caché de Spotify.")

    # --- Métodos de delegación para LastFMManager ---
    def get_lastfm_top_artists_direct(self, count=50, period="overall"):
        """Delegación al método implementado en lastfm_manager"""
        return self.lastfm_manager.get_lastfm_top_artists_direct(count, period)

    def show_lastfm_top_artists(self, count=50, period="overall", use_cached=True):
        """Delegación al método implementado en lastfm_manager"""
        return self.lastfm_manager.show_lastfm_top_artists(count, period, use_cached)

    def show_lastfm_loved_tracks(self, limit=50, use_cached=True):
        """Delegación al método implementado en lastfm_manager"""
        return self.lastfm_manager.show_lastfm_loved_tracks(limit, use_cached)

    def sync_top_artists_from_lastfm(self, count=50, period="overall"):
        """Delegación al método implementado en lastfm_manager"""
        return self.lastfm_manager.sync_top_artists_from_lastfm(count, period)

    def add_lastfm_artist_to_muspy(self, artist_name):
        """Delegación al método implementado en lastfm_manager"""
        return self.lastfm_manager.add_lastfm_artist_to_muspy(artist_name)

    def show_artist_info(self, artist_name):
        """Delegación al método implementado en lastfm_manager"""
        return self.lastfm_manager.show_artist_info(artist_name)

    def manage_lastfm_auth(self):
        """Delegación al método implementado en lastfm_manager"""
        return self.lastfm_manager.manage_lastfm_auth()

    # --- Métodos de delegación para SpotifyManager ---
    def ensure_spotify_auth(self):
        """Delegación al método implementado en spotify_manager"""
        return self.spotify_manager.ensure_spotify_auth()

    def follow_artist_on_spotify(self, artist_name, spotify_client=None):
        """Delegación al método implementado en spotify_manager"""
        return self.spotify_manager.follow_artist_on_spotify(artist_name, spotify_client)

    def show_spotify_followed_artists(self):
        """Delegación al método implementado en spotify_manager"""
        return self.spotify_manager.show_spotify_followed_artists()

    def show_spotify_new_releases(self):
        """Delegación al método implementado en spotify_manager"""
        return self.spotify_manager.show_spotify_new_releases()

    def show_spotify_saved_tracks(self):
        """Delegación al método implementado en spotify_manager"""
        return self.spotify_manager.show_spotify_saved_tracks()

    def show_spotify_top_items_dialog(self):
        """Delegación al método implementado en spotify_manager"""
        return self.spotify_manager.show_spotify_top_items_dialog()

    def follow_artist_on_spotify_by_name(self, artist_name):
        """Delegación al método implementado en spotify_manager"""
        return self.spotify_manager.follow_artist_on_spotify_by_name(artist_name)

    def follow_artist_on_spotify_by_id(self, artist_id):
        """Delegación al método implementado en spotify_manager"""
        return self.spotify_manager.follow_artist_on_spotify_by_id(artist_id)

    # --- Métodos de delegación para MusicBrainzManager ---
    def show_musicbrainz_collection(self, collection_id, collection_name):
        """Delegación al método implementado en mb_manager"""
        return self.musicbrainz_manager.show_musicbrainz_collection(collection_id, collection_name)

    def authenticate_musicbrainz_silently(self):
        """Delegación al método implementado en mb_manager"""
        return self.musicbrainz_manager.authenticate_musicbrainz_silently()

    def authenticate_musicbrainz_dialog(self):
        """Delegación al método implementado en mb_manager"""
        return self.musicbrainz_manager.authenticate_musicbrainz_dialog()

    def create_new_collection(self):
        """Delegación al método implementado en mb_manager"""
        return self.musicbrainz_manager.create_new_collection()

    def fetch_all_musicbrainz_collections(self):
        """Delegación al método implementado en mb_manager"""
        return self.musicbrainz_manager.fetch_all_musicbrainz_collections()

    def add_release_to_collection(self, collection_id, collection_name, release_mbid):
        """Delegación al método implementado en mb_manager"""
        return self.musicbrainz_manager.add_release_to_collection(collection_id, collection_name, release_mbid)

    def add_selected_albums_to_collection(self, collection_id, collection_name):
        """Delegación al método implementado en mb_manager"""
        return self.musicbrainz_manager.add_selected_albums_to_collection(collection_id, collection_name)

    def open_musicbrainz_artist(self, artist_mbid):
        """Delegación al método implementado en mb_manager"""
        return self.utils.open_musicbrainz_artist(artist_mbid)

    def open_musicbrainz_release(self, release_mbid):
        """Delegación al método implementado en mb_manager"""
        return self.utils.open_musicbrainz_release(release_mbid)

    # --- Métodos de delegación para BlueskyManager ---
    # def show_bluesky_menu(self):
    #     """Delegación al método implementado en bluesky_manager"""
    #     return self.bluesky_manager.show_bluesky_menu()

    def configure_bluesky_username(self):
        """Delegación al método implementado en bluesky_manager"""
        return self.bluesky_manager.configure_bluesky_username()

    def search_spotify_artists_on_bluesky(self):
        """Delegación al método implementado en bluesky_manager"""
        return self.bluesky_manager.search_spotify_artists_on_bluesky()

    def search_db_artists_on_bluesky(self):
        """Delegación al método implementado en bluesky_manager"""
        return self.bluesky_manager.search_db_artists_on_bluesky()

    def search_lastfm_artists_on_bluesky(self, period, count):
        """Delegación al método implementado en bluesky_manager"""
        return self.bluesky_manager.search_lastfm_artists_on_bluesky(period, count)

    def search_mb_collection_on_bluesky(self):
        """Delegación al método implementado en bluesky_manager"""
        return self.bluesky_manager.search_mb_collection_on_bluesky()

    # --- Métodos de delegación para ProgressUtils ---
    def show_progress_operation(self, operation_function, operation_args=None, title="Operación en progreso", 
                                label_format="{current}/{total} - {status}", 
                                cancel_button_text="Cancelar", 
                                finish_message=None):
        """Delegación al método implementado en progress_utils"""
        from modules.submodules.muspy.progress_utils import show_progress_operation
        return show_progress_operation(self, operation_function, operation_args, title, 
                                    label_format, cancel_button_text, finish_message)

    def sync_spotify_selected_artists(self):
        """Delegación al método implementado en spotify_manager"""
        return self.spotify_manager.sync_spotify_selected_artists()


    def _start_background_auth(self):
        """Start background authentication for MusicBrainz, LastFM and Twitter managers"""
        # Start MusicBrainz authentication if credentials are available
        if hasattr(self, 'musicbrainz_manager') and self.musicbrainz_enabled:
            self.logger.info("Iniciando autenticación en segundo plano con MusicBrainz...")
            try:
                self.musicbrainz_manager._start_background_auth()
            except Exception as e:
                self.logger.error(f"Error iniciando autenticación de MusicBrainz: {e}", exc_info=True)
        
        # Start LastFM authentication if credentials are available
        if hasattr(self, 'lastfm_manager') and self.lastfm_enabled:
            self.logger.info("Iniciando autenticación en segundo plano con LastFM...")
            try:
                self.lastfm_manager._start_background_auth()
            except Exception as e:
                self.logger.error(f"Error iniciando autenticación de LastFM: {e}", exc_info=True)
        
        # Start Twitter authentication if credentials are available
        if hasattr(self, 'twitter_manager') and self.twitter_manager.twitter_enabled:
            self.logger.info("Iniciando autenticación en segundo plano con Twitter...")
            try:
                # Create and start auth worker
                from PyQt6.QtCore import QThread, pyqtSignal
                
                class TwitterAuthWorker(QThread):
                    """Worker for Twitter background authentication"""
                    auth_completed = pyqtSignal(bool)
                    
                    def __init__(self, twitter_auth=None, logger=None):
                        super().__init__()
                        self.twitter_auth = twitter_auth
                        self.logger = logger
                        
                    def run(self):
                        if not self.twitter_auth:
                            self.auth_completed.emit(False)
                            return
                            
                        try:
                            result = self.twitter_auth.authenticate(silent=True)
                            self.auth_completed.emit(result)
                        except Exception as e:
                            if self.logger:
                                self.logger.error(f"Error en worker de autenticación Twitter: {e}", exc_info=True)
                            self.auth_completed.emit(False)
                
                # Create and connect worker
                self.twitter_auth_worker = TwitterAuthWorker(
                    self.twitter_manager.twitter_auth, 
                    self.logger
                )
                self.twitter_auth_worker.auth_completed.connect(self._on_twitter_auth_completed)
                self.twitter_auth_worker.start()
                
            except Exception as e:
                self.logger.error(f"Error iniciando autenticación de Twitter: {e}", exc_info=True)

    def _on_twitter_auth_completed(self, success):
        """Handle Twitter authentication completion"""
        if success:
            self.logger.info("Autenticación de Twitter completada con éxito")
        else:
            self.logger.info("Autenticación silenciosa de Twitter no completada")


    def set_twitter_manager(self, twitter_manager):
        """Establece el gestor de Twitter"""
        self.twitter_manager = twitter_manager

# MAIN

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
