# TODO: Crear modo alternativo a dotenv

import os
import sys
import threading
import urllib.parse
import time
import json
import subprocess
import tempfile
import logging
import traceback
import re
import base64
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QInputDialog, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QTextEdit, QTabWidget, QMessageBox, QMenu, QDialogButtonBox, QLabel,
    QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy, QApplication, QDialog, QComboBox, QProgressDialog,
    QStackedWidget, QSlider, QSpinBox, QRadioButton
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal, QUrl, QRunnable, pyqtSlot, QObject, QThreadPool, QSize, QTimer
from PyQt6.QtGui import QIcon, QMovie

# Añadir el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import resources_rc
from base_module import BaseModule, PROJECT_ROOT

# Importar submódulos
from submodules.url_playlist.search_workers import InfoLoadWorker, SearchWorker, SearchSignals
from submodules.url_playlist.spotify_manager import SpotifyManager
from submodules.url_playlist.lastfm_manager import LastfmManager
from submodules.url_playlist.media_utils import MediaUtils
from submodules.url_playlist.rss_handler import RssHandler
from submodules.url_playlist.db_manager import DbManager
from submodules.url_playlist.playlist_manager import PlaylistManager
from submodules.url_playlist.ui_helpers import UiHelpers

class UrlPlayer(BaseModule):
    """Módulo para reproducir música desde URLs (YouTube, SoundCloud, Bandcamp)."""
    # Definir señales personalizadas para comunicación entre hilos
    ask_mark_as_listened_signal = pyqtSignal(dict)  # Para preguntar si marcar como escuchada
    show_error_signal = pyqtSignal(str)  # Para mostrar errores desde hilos

    def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
        # Extract specific configurations from kwargs with improved defaults
        self.mpv_temp_dir = kwargs.pop('mpv_temp_dir', os.path.join(os.path.expanduser("~"), ".config", "mpv", "_mpv_socket"))
        
        # Extract database configuration with better handling
        self.db_path = kwargs.get('db_path')
        if self.db_path and not os.path.isabs(self.db_path):
            self.db_path = os.path.join(PROJECT_ROOT, self.db_path)
        
        # Extract API credentials from kwargs with explicit handling
        self.spotify_authenticated = False
        self.spotify_playlists = {}
        self.spotify_user_id = None
        self.spotify_client_id = kwargs.get('spotify_client_id')
        self.spotify_client_secret = kwargs.get('spotify_client_secret')
        self.lastfm_api_key = kwargs.get('lastfm_api_key')
        self.lastfm_user = kwargs.get('lastfm_user')
        self.exclude_spotify_from_local = kwargs.get('exclude_spotify_from_local', True)
        self.playlists = {'spotify': [], 'local': [], 'rss': []}

        # Log the received configuration
        print(f"[UrlPlayer] Received configs - DB: {self.db_path}, Spotify credentials: {bool(self.spotify_client_id)}, Last.fm credentials: {bool(self.lastfm_api_key)}")
        
        # Initialize other instance variables
        self.player_process = None
        self.current_playlist = []
        self.current_track_index = -1
        self.media_info_cache = {}
        self.yt_dlp_process = None
        self.is_playing = False
        self.mpv_socket = None
        self.mpv_wid = None

        # Credenciales Servidor FreshRss
        self.freshrss_url = kwargs.pop('freshrss_url', None)
        self.freshrss_username = kwargs.pop('freshrss_user', None)
        self.freshrss_auth_token = kwargs.pop('freshrss_api_key', None)

        # Directorios para playlists RSS
        self.rss_pending_dir = kwargs.pop('rss_pending_dir', os.path.join(PROJECT_ROOT, ".content", "playlists", "blogs", "pendiente"))
        self.rss_listened_dir = kwargs.pop('rss_listened_dir', os.path.join(PROJECT_ROOT, ".content", "playlists", "blogs", "escuchado"))
        
        # Asegurar que los directorios existan
        os.makedirs(self.rss_pending_dir, exist_ok=True)
        os.makedirs(self.rss_listened_dir, exist_ok=True)

        # Define default services
        default_services = {
            'youtube': True,
            'soundcloud': True,
            'bandcamp': True,
            'spotify': False,  # Will be updated after loading credentials
            'lastfm': False    # Will be updated after loading credentials
        }
        
        # Get service configuration from kwargs
        included_services = kwargs.pop('included_services', {})
        
        # Initialize services dictionary
        self.included_services = {}
        
        # Ensure all default services are included with boolean values
        for service, default_state in default_services.items():
            if service not in included_services:
                self.included_services[service] = default_state
            else:
                # Convert string representation to boolean if needed
                value = included_services[service]
                if isinstance(value, str):
                    self.included_services[service] = value.lower() == 'true'
                else:
                    self.included_services[service] = bool(value)
        
        # Initialize attributes for widgets
        self.lineEdit = None
        self.searchButton = None
        self.treeWidget = None
        self.playButton = None
        self.rewButton = None
        self.ffButton = None
        self.tabWidget = None
        self.listWidget = None
        self.delButton = None
        self.addButton = None
        self.textEdit = None
        self.info_wiki_textedit = None
        
        # Get pagination configuration
        self.num_servicios_spinBox = kwargs.pop('pagination_value', 10)
        
        # Now call the parent constructor which will call init_ui()
        super().__init__(parent, theme, **kwargs)
        
        self._is_initializing = True
        
        # Inicializar gestores
        self.spotify_manager = SpotifyManager(self)
        self.lastfm_manager = LastfmManager(self)
        self.media_utils = MediaUtils(self)
        self.rss_handler = RssHandler(self)
        self.db_manager = DbManager(self)
        self.playlist_manager = PlaylistManager(self)
        self.ui_helpers = UiHelpers(self)
        
        # Cargar las credenciales con tu método existente
        self._load_api_credentials_from_env()  # Tu método existente

        # Configurar Spotify solo si tenemos credenciales
        if self.spotify_client_id and self.spotify_client_secret:
            self.spotify_manager.setup_spotify()
            
            # Una vez configurado, cargar las playlists
            if hasattr(self, 'playlist_spotify_comboBox') and self.spotify_authenticated:
                self.spotify_manager.load_spotify_playlists()

        # Ensure these are available in environment variables for imported modules
        self._set_api_credentials_as_env()
        
        # Update service enabled flags based on credentials
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        self.lastfm_enabled = bool(self.lastfm_api_key)
        
        # Update included_services based on credentials
        self.included_services['spotify'] = self.spotify_enabled
        self.included_services['lastfm'] = self.lastfm_enabled
        
        # Log the final configuration
        print(f"[UrlPlayer] Final config - DB: {self.db_path}, Spotify enabled: {self.spotify_enabled}, Last.fm enabled: {self.lastfm_enabled}")
        
        self._is_initializing = False

    def get_app_path(self, file_path):
        """Create standardized paths relative to PROJECT_ROOT"""
        return os.path.join(PROJECT_ROOT, file_path)

    def log(self, message):
        """Registra un mensaje en el TextEdit y en la consola."""
        if hasattr(self, 'textEdit') and self.textEdit:
            self.textEdit.append(message)
        print(f"[UrlPlayer] {message}")
        
    def init_ui(self):
        """Inicializa la interfaz de usuario desde el archivo UI."""
        # Intentar cargar desde archivo UI
        ui_file_loaded = self.load_ui_file("url_player.ui", [
            "lineEdit", "searchButton", "treeWidget", "playButton", 
            "rewButton", "ffButton", "tabWidget", "listWidget",
            "delButton", "addButton", "textEdit", "servicios", "ajustes_avanzados"
        ])
        
        if not ui_file_loaded:
            self._fallback_init_ui()
        
        # Verificar que tenemos todos los widgets necesarios
        if not self.check_required_widgets():
            print("[UrlPlayer] Error: No se pudieron inicializar todos los widgets requeridos")
            return
        
        # Inicializar referencias a widgets después de cargar la UI
        self.ui_helpers.initialize_playlist_ui_references()
        
        # Cargar configuración
        self.load_settings()

        # Configurar nombres y tooltips
        self.searchButton.setText("Buscar")
        self.searchButton.setToolTip("Buscar información sobre la URL")
        self.playButton.setIcon(QIcon(":/services/b_play"))
        self.playButton.setToolTip("Reproducir/Pausar")
        self.playButton.setIcon(QIcon(":/services/b_prev"))
        self.rewButton.setToolTip("Anterior")
        self.playButton.setIcon(QIcon(":/services/b_ff"))
        self.ffButton.setToolTip("Siguiente")
        self.playButton.setIcon(QIcon(":/services/b_minus_star"))
        self.delButton.setToolTip("Eliminar de la cola")
        self.playButton.setIcon(QIcon(":/services/b_addstar"))
        self.addButton.setToolTip("Añadir a la cola")
        
        self.ui_helpers.setup_unified_playlist_button()  # Create the button
        self.ui_helpers.update_playlist_view()  # Apply current view settings
        
        # Configure TreeWidget for better display of hierarchical data
        if hasattr(self, 'treeWidget') and self.treeWidget:
            # Set column headers
            self.treeWidget.setHeaderLabels(["Título", "Artista", "Tipo", "Track/Año", "Duración"])
            
            # Set column widths
            self.tree_container.setStyleSheet(f"""
                QFrame {{
                    border: 1px;
                    border-radius: 4px;
                }}
                """)
            self.treeWidget.setColumnWidth(0, 250)  # Título
            self.treeWidget.setColumnWidth(1, 100)  # Artista
            self.treeWidget.setColumnWidth(2, 80)   # Tipo
            self.treeWidget.setColumnWidth(3, 70)   # Track/Año
            self.treeWidget.setColumnWidth(4, 70)   # Duración
            
            # Set indent for better hierarchy visualization
            self.treeWidget.setIndentation(20)
            
            # Enable sorting
            self.treeWidget.setSortingEnabled(True)
            self.treeWidget.sortByColumn(0, Qt.SortOrder.AscendingOrder)
            
            # Enable item expanding/collapsing on single click
            self.treeWidget.setExpandsOnDoubleClick(False)
            self.treeWidget.itemClicked.connect(self.on_tree_item_clicked)
        
        # Configurar TabWidget
        self.tabWidget.setTabText(0, "Cola de reproducción")
        self.tabWidget.setTabText(1, "Información")
        self.setup_services_combo()
        
        # Find the tipo_combo if it exists
        if not hasattr(self, 'tipo_combo'):
            self.tipo_combo = self.findChild(QComboBox, 'tipo_combo')
            
        # If tipo_combo exists, set default items if empty
        if self.tipo_combo and self.tipo_combo.count() == 0:
            self.tipo_combo.addItem("Todo")
            self.tipo_combo.addItem("Artista")
            self.tipo_combo.addItem("Álbum")
            self.tipo_combo.addItem("Canción")

        # Ensure that playlist_rss_comboBox is accessible
        if not hasattr(self, 'playlist_rss_comboBox'):
            self.playlist_rss_comboBox = self.findChild(QComboBox, 'playlist_rss_comboBox')
            if self.playlist_rss_comboBox:
                self.log("Combobox 'playlist_rss_comboBox' encontrado utilizando findChild")
            else:
                self.log("ERROR: No se pudo encontrar el combobox 'playlist_rss_comboBox'")
        
        # Check for critical widgets
        critical_widgets = [
            'playlist_stack', 
            'separate_page', 
            'unified_page', 
            'unified_playlist_button',
            'playlist_local_comboBox',
            'playlist_spotify_comboBox',
            'playlist_rss_comboBox'
        ]
        for widget_name in critical_widgets:
            widget = self.findChild(QWidget, widget_name)
            self.log(f"Widget '{widget_name}': {'Encontrado' if widget else 'NO ENCONTRADO'}")
        
        # After all UI initialization, add Last.fm scrobbles setup
        self.lastfm_manager.setup_scrobbles_menu()
        
        # Connect spinbox and slider in settings
        scrobbles_slider = self.findChild(QSlider, 'scrobbles_slider')
        scrobbles_spinbox = self.findChild(QSpinBox, 'scrobblers_spinBox')
        
        if scrobbles_slider and scrobbles_spinbox:
            # Connect them bidirectionally
            scrobbles_slider.valueChanged.connect(scrobbles_spinbox.setValue)
            scrobbles_spinbox.valueChanged.connect(scrobbles_slider.setValue)
        
        # Default service priority indices (YouTube, SoundCloud, Bandcamp, Spotify)
        if not hasattr(self, 'service_priority_indices'):
            self.service_priority_indices = [0, 1, 3, 2]

        # Configurar los controles de Last.fm
        self.lastfm_manager.connect_lastfm_controls()
        
        # Configurar menús de Last.fm
        self.lastfm_manager.setup_scrobbles_menu()
        
        # Cargar configuración de Last.fm
        self.lastfm_manager.load_lastfm_settings()
        
        # Comprobar si hay caché existente y cargar datos
        self.lastfm_manager.load_lastfm_cache_if_exists()

        # Load playlists at startup
        self.load_all_playlists()

        # Setup service icons
        self.ui_helpers.setup_service_icons()

        # Configurar indicador de carga
        self.ui_helpers.setup_loading_indicator()

        # Actualizar el combo de servicios según la configuración
        self.update_service_combo()

        # Conectar señales
        self.connect_signals()

    def on_tree_item_clicked(self, item, column):
        """Handle click on tree items to expand/collapse without switching tabs"""
        try:
            # If item has children, toggle expanded state
            if item.childCount() > 0:
                item.setExpanded(not item.isExpanded())
                    
            # Display info without changing tabs
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(item_data, dict) and (item_data.get('title') or item_data.get('artist')):
                # Display info in text edit instead of wiki tab
                title = item_data.get('title', '')
                artist = item_data.get('artist', '')
                item_type = item_data.get('type', '')
                
                info_text = f"Selected: {title}\n"
                if artist:
                    info_text += f"Artist: {artist}\n"
                if item_type:
                    info_text += f"Type: {item_type}\n"
                
                self.textEdit.append(info_text)
        except Exception as e:
            self.log(f"Error in tree item clicked: {str(e)}")

    def connect_signals(self):
        """Conecta las señales de los widgets a sus respectivos slots."""
        try:
            # Conectar señales con verificación previa
            if self.searchButton:
                self.searchButton.clicked.connect(self.perform_search)
                
            if self.playButton:
                self.playButton.clicked.connect(self.toggle_play_pause)
            
            if self.rewButton:
                self.rewButton.clicked.connect(self.previous_track)
            
            if self.ffButton:
                self.ffButton.clicked.connect(self.next_track)
            
            if self.addButton:
                self.addButton.clicked.connect(self.add_to_queue)
            
            if self.delButton:
                self.delButton.clicked.connect(self.remove_from_queue)
            
            if self.lineEdit:
                self.lineEdit.returnPressed.connect(self.perform_search)
                print("LineEdit conectado para búsqueda con Enter")

            # Conectar eventos de doble clic
            if self.treeWidget:
                self.treeWidget.itemDoubleClicked.connect(self.on_tree_double_click)
                self.on_tree_double_click_original = self.on_tree_double_click
                self.treeWidget.itemDoubleClicked.disconnect(self.on_tree_double_click)
                self.treeWidget.itemDoubleClicked.connect(self.on_tree_double_click)

            if self.listWidget:
                # First disconnect to avoid multiple connections
                try:
                    self.listWidget.itemDoubleClicked.disconnect()
                except TypeError:
                    pass  # If it wasn't connected, that's fine
                # Connect to the right method
                self.listWidget.itemDoubleClicked.connect(self.on_list_double_click)
            
            if hasattr(self, 'ajustes_avanzados'):
                self.ajustes_avanzados.clicked.connect(self.show_advanced_settings)

            # Add this at the end
            if self.treeWidget:
                # Connect item selection changed
                self.treeWidget.itemSelectionChanged.connect(self.on_tree_selection_changed)
                print("[UrlPlayer] Señales conectadas correctamente")

            # Add new playlist-related connections
            if hasattr(self, 'playlist_spotify_comboBox'):
                self.playlist_spotify_comboBox.currentIndexChanged.connect(self.spotify_manager.on_spotify_playlist_changed)
            
            # Conectar señal del combobox RSS
            if hasattr(self, 'playlist_rss_comboBox'):
                try:
                    self.playlist_rss_comboBox.currentIndexChanged.disconnect()
                except:
                    pass
                self.playlist_rss_comboBox.currentIndexChanged.connect(self.rss_handler.on_playlist_rss_changed)
                
            # Set up additional controls for RSS
            self.rss_handler.setup_rss_controls()
                
            if hasattr(self, 'playlist_local_comboBox'):
                # First disconnect to avoid multiple connections
                try:
                    self.playlist_local_comboBox.currentIndexChanged.disconnect()
                except:
                    pass  # If it wasn't connected, that's fine
                
                # Connect to the on_playlist_local_changed method
                self.playlist_local_comboBox.currentIndexChanged.connect(self.playlist_manager.on_playlist_local_changed)                

            # For the save playlist button, properly disconnect first
            if hasattr(self, 'GuardarPlaylist'):
                try:
                    self.GuardarPlaylist.clicked.disconnect()
                except TypeError:
                    pass  # Not connected yet, that's fine
                self.GuardarPlaylist.clicked.connect(self.on_guardar_playlist_clicked)
            
            # Same for the combobox
            if hasattr(self, 'guardar_playlist_comboBox'):
                try:
                    self.guardar_playlist_comboBox.currentIndexChanged.disconnect()
                except TypeError:
                    pass  # Not connected yet, that's fine

            if hasattr(self, 'VaciarPlaylist'):
                self.VaciarPlaylist.clicked.connect(self.clear_playlist)

            self.ask_mark_as_listened_signal.connect(self.rss_handler.show_mark_as_listened_dialog)
            self.show_error_signal.connect(lambda msg: QMessageBox.critical(self, "Error", msg))

            # Setup context menus
            self.ui_helpers.setup_context_menus()

            # Actualiza las playlists automáticamente al inicio para el combobox RSS
            self.rss_handler.reload_rss_playlists()

        except Exception as e:
            print(f"[UrlPlayer] Error al conectar señales: {str(e)}")

    def clear_playlist(self):
        """Clear the current queue/playlist with confirmation"""
        # Check if there are items to clear
        if self.listWidget.count() == 0:
            return
            
        # Confirm with user
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Limpiar lista", 
            "¿Estás seguro de que quieres eliminar todas las canciones de la lista?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear the list widget
            self.listWidget.clear()
            
            # Clear the internal playlist
            self.current_playlist = []
            
            # Reset current track index
            self.current_track_index = -1
            
            # Stop any current playback
            self.media_utils.stop_playback()
            
            self.log("Cola de reproducción limpiada")

    def load_selected_playlist(self, playlist):
        """Load a selected playlist into the player"""
        return self.playlist_manager.load_selected_playlist(playlist)

    def _fallback_init_ui(self):
        """Crea la UI manualmente en caso de que falle la carga del archivo UI."""
        layout = QVBoxLayout(self)
        
        # Panel de búsqueda
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        self.lineEdit = QLineEdit()
        self.searchButton = QPushButton("Buscar")
        search_layout.addWidget(self.lineEdit)
        search_layout.addWidget(self.searchButton)
        
        # Panel principal
        main_frame = QFrame()
        main_layout = QHBoxLayout(main_frame)
        
        # Contenedor del árbol
        tree_frame = QFrame()
        tree_layout = QVBoxLayout(tree_frame)
        self.treeWidget = QTreeWidget()
        self.treeWidget.setHeaderLabels(["Título", "Artista", "Tipo", "Duración"])
        tree_layout.addWidget(self.treeWidget)
        
        # Contenedor del reproductor
        player_frame = QFrame()
        player_layout = QVBoxLayout(player_frame)
        
        # Panel de botones del reproductor
        player_buttons_frame = QFrame()
        player_buttons_layout = QHBoxLayout(player_buttons_frame)
        self.rewButton = QPushButton("⏮️")
        self.ffButton = QPushButton("⏭️")
        self.playButton = QPushButton("▶️")
        player_buttons_layout.addWidget(self.rewButton)
        player_buttons_layout.addWidget(self.ffButton)
        player_buttons_layout.addWidget(self.playButton)
        
        # Panel de información
        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        self.tabWidget = QTabWidget()
        
        # Tab de playlists
        playlists_tab = QWidget()
        playlists_layout = QVBoxLayout(playlists_tab)
        self.listWidget = QListWidget()
        
        playlist_buttons_frame = QFrame()
        playlist_buttons_layout = QHBoxLayout(playlist_buttons_frame)
        self.addButton = QPushButton("➕")
        self.delButton = QPushButton("➖")
        playlist_buttons_layout.addWidget(self.addButton)
        playlist_buttons_layout.addWidget(self.delButton)
        
        playlists_layout.addWidget(self.listWidget)
        playlists_layout.addWidget(playlist_buttons_frame)
        
        # Tab de información de texto
        info_tab = QWidget()
        info_tab_layout = QVBoxLayout(info_tab)
        self.textEdit = QTextEdit()
        info_tab_layout.addWidget(self.textEdit)
        
        # Añadir tabs
        self.tabWidget.addTab(playlists_tab, "Cola de reproducción")
        self.tabWidget.addTab(info_tab, "Información")
        
        info_layout.addWidget(self.tabWidget)
        
        # Añadir todo al layout del reproductor
        player_layout.addWidget(player_buttons_frame)
        player_layout.addWidget(info_frame)
        
        # Añadir frames al layout principal
        main_layout.addWidget(tree_frame)
        main_layout.addWidget(player_frame)
        
        # Añadir todo al layout principal
        layout.addWidget(search_frame)
        layout.addWidget(main_frame)

    def check_required_widgets(self):
        """Verifica que todos los widgets requeridos existan."""
        required_widgets = [
            "lineEdit", "searchButton", "treeWidget", "playButton", 
            "ffButton", "rewButton", "tabWidget", "listWidget",
            "addButton", "delButton", "textEdit", "servicios", "ajustes_avanzados"
        ]
        
        all_ok = True
        for widget_name in required_widgets:
            if not hasattr(self, widget_name) or getattr(self, widget_name) is None:
                print(f"[UrlPlayer] Error: Widget {widget_name} no encontrado")
                all_ok = False
        
        return all_ok

    def show_advanced_settings(self):
        """Show the advanced settings dialog."""
        return self.ui_helpers.show_advanced_settings()

    def load_settings(self):
        """Loads module configuration with standard paths"""
        try:
            # Standard config path
            config_path = self.get_app_path("config/config.yml")
            
            if not os.path.exists(config_path):
                self.log(f"Config file not found at: {config_path}")
                self.ui_helpers._initialize_default_values()
                return
                
            # Load configuration file    
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    
                # Get global credentials first
                if 'global_theme_config' in config_data:
                    global_config = config_data['global_theme_config']
                    
                    # Get database path
                    if 'db_path' in global_config and not self.db_path:
                        self.db_path = self.get_app_path(global_config['db_path'])
                    
                    # Get API credentials
                    if 'spotify_client_id' in global_config:
                        self.spotify_client_id = global_config['spotify_client_id']
                    if 'spotify_client_secret' in global_config:
                        self.spotify_client_secret = global_config['spotify_client_secret']
                    if 'lastfm_api_key' in global_config:
                        self.lastfm_api_key = global_config['lastfm_api_key']
                
                # Find module-specific settings
                for module in config_data.get('modules', []):
                    if module.get('name') in ['Url Playlists', 'URL Playlist', 'URL Player']:
                        module_args = module.get('args', {})
                        
                        # Load paths with standardization
                        if 'db_path' in module_args:
                            self.db_path = self.get_app_path(module_args['db_path'])
                        
                        if 'spotify_token' in module_args:
                            self.spotify_token_path = self.get_app_path(module_args['spotify_token'])
                        else:
                            self.spotify_token_path = self.get_app_path(".content/cache/spotify_token.txt")
                        
                        # Load other settings
                        self._load_module_settings(module_args)
                        break
            except Exception as e:
                self.log(f"Error loading YAML config: {e}")
                self.ui_helpers._initialize_default_values()
        except Exception as e:
            self.log(f"Overall error in load_settings: {e}")
            self.ui_helpers._initialize_default_values()

def _load_module_settings(self, module_args):
        """Load module-specific settings from args dictionary"""
        try:
            # Load API credentials
            if 'spotify_client_id' in module_args:
                self.spotify_client_id = module_args['spotify_client_id']
            if 'spotify_client_secret' in module_args:
                self.spotify_client_secret = module_args['spotify_client_secret']
            if 'lastfm_api_key' in module_args:
                self.lastfm_api_key = module_args['lastfm_api_key']
            if 'lastfm_user' in module_args:
                self.lastfm_user = module_args['lastfm_user']
            
            # Load pagination value
            if 'pagination_value' in module_args:
                self.pagination_value = module_args.get('pagination_value', 10)
                self.num_servicios_spinBox = self.pagination_value
            
            # Load included services
            if 'included_services' in module_args:
                included_services = module_args.get('included_services', {})
                
                # Ensure values are boolean
                self.included_services = {}
                for key, value in included_services.items():
                    if isinstance(value, str):
                        self.included_services[key] = value.lower() == 'true'
                    else:
                        self.included_services[key] = bool(value)
            
            # Cargar ruta de playlists locales
            if 'local_playlist_path' in module_args:
                local_playlist_path = module_args['local_playlist_path']
                # Manejar ruta relativa
                if not os.path.isabs(local_playlist_path):
                    local_playlist_path = os.path.join(PROJECT_ROOT, local_playlist_path)
                self.local_playlist_path = local_playlist_path
                self.log(f"Ruta de playlists locales cargada: {self.local_playlist_path}")
            else:
                # Ruta por defecto
                self.local_playlist_path = os.path.join(PROJECT_ROOT, ".content", "playlists", "locales")
                self.log(f"Usando ruta de playlists locales por defecto: {self.local_playlist_path}")

            # Load MPV temp directory
            if 'mpv_temp_dir' in module_args:
                mpv_temp_dir = module_args['mpv_temp_dir']
                # Handle relative path
                if not os.path.isabs(mpv_temp_dir):
                    mpv_temp_dir = os.path.join(os.path.expanduser("~"), mpv_temp_dir)
                self.mpv_temp_dir = mpv_temp_dir
                
            # Load playlist view settings
            self.playlist_unified_view = module_args.get('playlist_unified_view', False)
            
            # Load playlist visibility settings
            self.show_local_playlists = module_args.get('show_local_playlists', True)
            self.show_spotify_playlists = module_args.get('show_spotify_playlists', True)
            self.show_rss_playlists = module_args.get('show_rss_playlists', True)
            
            self.log("Module settings loaded successfully")
        except Exception as e:
            self.log(f"Error loading module settings: {e}")

    def save_settings(self):
        """Guarda la configuración del módulo en el archivo de configuración general."""
        # Delegate to ui_helpers
        self.ui_helpers.save_settings()

    def _load_api_credentials_from_env(self):
        """Load API credentials from environment variables with better fallbacks"""
        # First try environment variables
        if not self.spotify_client_id:
            self.spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        
        if not self.spotify_client_secret:
            self.spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
            
        if not self.lastfm_api_key:
            self.lastfm_api_key = os.environ.get("LASTFM_API_KEY")
            
        if not self.lastfm_user:
            self.lastfm_user = os.environ.get("LASTFM_USER")
        
        # If still missing, systematically try all config file locations
        config_files = [
            os.path.join(PROJECT_ROOT, "config", "api_keys.json"),
            os.path.join(PROJECT_ROOT, ".content", "config", "api_keys.json"),
            os.path.join(os.path.expanduser("~"), ".config", "music_app", "api_keys.json")
        ]
        
        for config_path in config_files:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        api_config = json.load(f)
                        
                        if 'spotify' in api_config:
                            if not self.spotify_client_id:
                                self.spotify_client_id = api_config['spotify'].get('client_id')
                                print(f"[UrlPlayer] Loaded Spotify client ID from {config_path}")
                            if not self.spotify_client_secret:
                                self.spotify_client_secret = api_config['spotify'].get('client_secret')
                                print(f"[UrlPlayer] Loaded Spotify client secret from {config_path}")
                        
                        if 'lastfm' in api_config:
                            if not self.lastfm_api_key:
                                self.lastfm_api_key = api_config['lastfm'].get('api_key')
                                print(f"[UrlPlayer] Loaded Last.fm API key from {config_path}")
                            if not self.lastfm_user:
                                self.lastfm_user = api_config['lastfm'].get('user')
                                print(f"[UrlPlayer] Loaded Last.fm user from {config_path}")
                        
                    # If we found and loaded the config, break the loop
                    if all([self.spotify_client_id, self.spotify_client_secret, self.lastfm_api_key]):
                        print(f"[UrlPlayer] Successfully loaded all API credentials from {config_path}")
                        break
                except Exception as e:
                    print(f"[UrlPlayer] Error loading API credentials from {config_path}: {str(e)}")

        # Try dotenv as a last resort
        try:
            from dotenv import load_dotenv
            # Load from any potential .env files
            load_dotenv()
            
            # Check again if environment variables are now available
            if not self.spotify_client_id:
                self.spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
            if not self.spotify_client_secret:
                self.spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
            if not self.lastfm_api_key:
                self.lastfm_api_key = os.environ.get("LASTFM_API_KEY")
            if not self.lastfm_user:
                self.lastfm_user = os.environ.get("LASTFM_USER")
                
            print("[UrlPlayer] Attempted to load credentials from .env files")
        except ImportError:
            # dotenv is not installed, that's fine
            pass

    def _set_api_credentials_as_env(self):
        """Set API credentials as environment variables for imported modules with better validation"""
        if self.spotify_client_id and isinstance(self.spotify_client_id, str) and self.spotify_client_id.strip():
            os.environ["SPOTIFY_CLIENT_ID"] = self.spotify_client_id.strip()
            print(f"[UrlPlayer] Set SPOTIFY_CLIENT_ID in environment")
        
        if self.spotify_client_secret and isinstance(self.spotify_client_secret, str) and self.spotify_client_secret.strip():
            os.environ["SPOTIFY_CLIENT_SECRET"] = self.spotify_client_secret.strip()
            print(f"[UrlPlayer] Set SPOTIFY_CLIENT_SECRET in environment")
        
        if self.lastfm_api_key and isinstance(self.lastfm_api_key, str) and self.lastfm_api_key.strip():
            os.environ["LASTFM_API_KEY"] = self.lastfm_api_key.strip()
            print(f"[UrlPlayer] Set LASTFM_API_KEY in environment")
        
        if self.lastfm_user and isinstance(self.lastfm_user, str) and self.lastfm_user.strip():
            os.environ["LASTFM_USER"] = self.lastfm_user.strip()
            print(f"[UrlPlayer] Set LASTFM_USER in environment")
            
        # Update service flags
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        self.lastfm_enabled = bool(self.lastfm_api_key)
        
        # Update included_services based on what's available
        if not self.spotify_enabled and 'spotify' in self.included_services:
            self.included_services['spotify'] = False
            print("[UrlPlayer] Disabled Spotify service due to missing credentials")
            
        if not self.lastfm_enabled and 'lastfm' in self.included_services:
            self.included_services['lastfm'] = False
            print("[UrlPlayer] Disabled Last.fm service due to missing credentials")

    def setup_services_combo(self):
        """Configura el combo box de servicios disponibles."""
        self.servicios.addItem(QIcon(":/services/add"), "Todos")
        self.servicios.addItem(QIcon(":/services/youtube"), "YouTube")
        self.servicios.addItem(QIcon(":/services/spotify"), "Spotify")
        self.servicios.addItem(QIcon(":/services/soundcloud"), "SoundCloud")
        self.servicios.addItem(QIcon(":/services/lastfm"), "Last.fm")
        self.servicios.addItem(QIcon(":/services/bandcamp"), "Bandcamp")
        
        # Conectar la señal de cambio del combo box
        self.servicios.currentIndexChanged.connect(self.service_changed)

    def update_service_combo(self):
        """Update the service combo to reflect current settings."""
        # Keep current selection
        current_selection = self.servicios.currentText() if hasattr(self, 'servicios') else "Todos"
        
        # Disconnect signals temporarily to avoid triggering events
        if hasattr(self, 'servicios'):
            try:
                self.servicios.currentIndexChanged.disconnect(self.service_changed)
            except:
                pass
                
            # Clear the combo box
            self.servicios.clear()
            
            # Add "Todos" option
            self.servicios.addItem(QIcon(":/services/wiki"), "Todos")
            
            # Add individual services with proper capitalization
            service_info = [
                ('youtube', "YouTube", ":/services/youtube"),
                ('soundcloud', "SoundCloud", ":/services/soundcloud"),
                ('bandcamp', "Bandcamp", ":/services/bandcamp"),
                ('spotify', "Spotify", ":/services/spotify"),
                ('lastfm', "Last.fm", ":/services/lastfm")
            ]
            
            for service_id, display_name, icon_path in service_info:
                # Only add if service is included
                included = self.included_services.get(service_id, False)
                if isinstance(included, str):
                    included = included.lower() == 'true'
                    
                if included:
                    self.servicios.addItem(QIcon(icon_path), display_name)
            
            # Restore previous selection if possible
            index = self.servicios.findText(current_selection)
            if index >= 0:
                self.servicios.setCurrentIndex(index)
            
            # Reconnect signal
            self.servicios.currentIndexChanged.connect(self.service_changed)

    def service_changed(self, index):
        """Maneja el cambio de servicio seleccionado."""
        service = self.servicios.currentText()
        self.log(f"Servicio seleccionado: {service}")
        
        # Limpiar resultados anteriores si hay alguno
        self.treeWidget.clear()
        
        # Modificar placeholder del LineEdit según el servicio
        placeholders = {
            "Todos": "Buscar en todos los servicios...",
            "YouTube": "Buscar en YouTube...",
            "Spotify": "Buscar en Spotify...",
            "SoundCloud": "Buscar en SoundCloud...",
            "Last.fm": "Buscar en Last.fm...",
            "Bandcamp": "Buscar en Bandcamp..."
        }
        
        self.lineEdit.setPlaceholderText(placeholders.get(service, "Buscar..."))
        
        # Si hay un texto en el campo de búsqueda, realizar la búsqueda con el nuevo servicio
        if self.lineEdit.text().strip():
            self.perform_search()

    def perform_search(self):
        """Performs a search based on the selected service and query."""
        query = self.lineEdit.text().strip()
        if not query:
            return
        
        self.log(f"Searching: {query}")
        
        # Clear previous results
        self.treeWidget.clear()
        self.textEdit.clear()
        QApplication.processEvents()  # Update UI
        
        # Show loading indicator
        self.ui_helpers.show_loading_indicator(True)
        
        # Get the selected service
        service = self.servicios.currentText()
        
        # Get the search type
        search_type = "all"
        if hasattr(self, 'tipo_combo') and self.tipo_combo:
            search_type = self.tipo_combo.currentText().lower()
        
        # Show progress
        self.textEdit.append(f"Buscando '{query}' en {service} (tipo: {search_type}, máx {self.pagination_value} resultados por servicio)...")
        QApplication.processEvents()  # Update UI
        
        # Create a structure to track added items
        self.added_items = {
            'artists': set(),      # Set of artist names
            'albums': set(),       # Set of "artist - album" keys
            'tracks': set()        # Set of "artist - title" keys
        }
        
        # First check database for existing links and structure
        self.log("Consultando la base de datos local primero...")
        db_links = self.db_manager.search_database_links(query, search_type)
        
        # Process database results immediately
        if db_links:
            db_results = self.db_manager._process_database_results(db_links)
            if db_results:
                self.ui_helpers.display_search_results(db_results)
                self.log(f"Encontrados {len(db_results)} resultados en la base de datos local")
        
        # Determine which services to include
        active_services = []
        if service == "Todos":
            # Check each service in the included_services dictionary
            for service_id, included in self.included_services.items():
                # Convert included to boolean if it's a string
                if isinstance(included, str):
                    included = included.lower() == 'true'
                
                if included:
                    active_services.append(service_id)
        else:
            # Convert from display name to service id (lowercase)
            service_id = service.lower()
            active_services = [service_id]
        
        if not active_services:
            self.log("No hay servicios seleccionados para la búsqueda. Actívalos en Ajustes Avanzados.")
            return
            
        # Disable controls during search
        self.searchButton.setEnabled(False)
        self.lineEdit.setEnabled(False)
        QApplication.processEvents()  # Update UI
        
        # Create and configure the worker with the necessary attributes
        worker = SearchWorker(active_services, query, max_results=self.pagination_value)
        worker.parent = self  # Set parent to access search_in_database
        worker.search_type = search_type  # Pass search type to worker
        
        # Pass database links to worker
        worker.db_links = db_links
        
        # Pass necessary attributes from parent
        worker.db_path = self.db_path
        worker.spotify_client_id = self.spotify_client_id
        worker.spotify_client_secret = self.spotify_client_secret
        worker.lastfm_api_key = self.lastfm_api_key
        worker.lastfm_user = self.lastfm_user
        
        # Pass the tracking structure to avoid duplicates
        worker.added_items = self.added_items
        
        # Connect signals
        worker.signals.results.connect(self.display_external_results)  # Changed to a new method
        worker.signals.error.connect(lambda err: self.log(f"Error en búsqueda: {err}"))
        worker.signals.finished.connect(self.search_finished)
        
        # Start the worker in the thread pool
        QThreadPool.globalInstance().start(worker)

    def display_external_results(self, results):
        """Display external search results, keeping database results already shown."""
        if not results:
            self.log("No se encontraron resultados externos.")
            return
        
        # Filter out results from database to avoid duplicates
        external_results = [r for r in results if not r.get('from_database', False)]
        
        if external_results:
            self.ui_helpers.display_search_results(external_results)
            self.log(f"Se añadieron {len(external_results)} resultados de servicios externos")

    def search_finished(self, result=None, basic_data=None):
        """Función llamada cuando termina la búsqueda."""
        self.log(f"Búsqueda completada.")
        
        # Hide loading indicator
        self.ui_helpers.show_loading_indicator(False)
        
        # Reactivar controles
        self.searchButton.setEnabled(True)
        self.lineEdit.setEnabled(True)
        
        # Make sure tree items are visible
        for i in range(self.treeWidget.topLevelItemCount()):
            self.treeWidget.topLevelItem(i).setExpanded(True)
        
        # Select the first item if available
        if self.treeWidget.topLevelItemCount() > 0:
            first_item = self.treeWidget.topLevelItem(0)
            self.treeWidget.setCurrentItem(first_item)
            if first_item.childCount() > 0:
                child = first_item.child(0)
                self.display_wiki_info(child.data(0, Qt.ItemDataRole.UserRole))
        
        QApplication.processEvents()  # Actualiza la UI

    def display_wiki_info(self, result_data):
        """Muestra información detallada del elemento en el panel info_wiki de forma asíncrona"""
        # Delegate to db_manager
        self.db_manager.display_wiki_info(result_data)

    def on_tree_double_click(self, item, column):
        """Handle double click on tree item to either expand/collapse or load content"""
        # Get the item data
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # If it's a playlist item, load its content
        if item_data and 'type' in item_data and item_data['type'] == 'playlist' and 'path' in item_data:
            self.rss_handler.load_rss_playlist_content(item, item_data)
            return
            
        # If it's a track item, play it
        if item_data and 'type' in item_data and item_data['type'] == 'track' and 'url' in item_data:
            self.ui_helpers.play_item(item)
            return

        # If it's a root item (source) with children, just expand/collapse
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return
        
        # Use the same method as the Add button to ensure paths are included
        self.add_item_to_queue(item)
        
        # If nothing is playing, play the newly added item
        if not self.is_playing and self.current_track_index == -1:
            self.current_track_index = len(self.current_playlist) - 1
            self.play_media()

    def on_list_double_click(self, item):
        """Maneja el doble clic en un elemento de la lista."""
        row = self.listWidget.row(item)
        self.current_track_index = row
        
        # Iniciar reproducción del elemento seleccionado
        self.media_utils.play_from_index(row)
        self.log(f"Reproduciendo '{item.text()}'")

    def add_to_queue(self):
        """Adds the selected item to the playback queue without changing tabs."""
        selected_items = self.treeWidget.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            # Get the item type
            item_type = item.text(2).split(' ')[0].lower()  # Extract the basic type
            
            # If it's an album, ask if user wants to add all tracks
            if item_type == "álbum":
                if item.childCount() > 0:  # Album has tracks as children
                    reply = QMessageBox.question(
                        self, 
                        "Agregar Álbum", 
                        f"¿Deseas agregar todo el álbum '{item.text(0)}' a la cola?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        # Add all child tracks
                        for i in range(item.childCount()):
                            child = item.child(i)
                            self.add_item_to_queue(child)
                        continue  # Skip adding the album itself
            
            # If it's a parent item with children (like artist or playlist)
            elif item.childCount() > 0:
                for i in range(item.childCount()):
                    child = item.child(i)
                    self.add_item_to_queue(child)
                continue  # Skip adding the parent itself
            
            # For individual tracks or other items without special handling
            self.add_item_to_queue(item)

    def add_item_to_queue(self, item):
        """Add a specific item to the queue with appropriate icon"""
        title = item.text(0)
        artist = item.text(1)
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            return
        
        # Debug logging to identify the issue
        self.log(f"Adding item with data: {json.dumps(item_data, default=str)}")
        
        # Get the playable URL based on priority
        url = None
        source = None
        
        if isinstance(item_data, dict):
            # Get service priority
            service_priority = self.lastfm_manager.get_service_priority()
            
            # Try each service in priority order
            for service in service_priority:
                service_url_key = f'{service}_url'
                if service_url_key in item_data and item_data[service_url_key]:
                    url = item_data[service_url_key]
                    source = service
                    self.log(f"Using {service} URL: {url}")
                    break
            
            # If no service URL found, try file path or generic URL
            if not url:
                # Check for file path first for local files
                file_path = item_data.get('file_path')
                if file_path:
                    url = file_path
                    source = 'local'
                    self.log(f"Using file path: {file_path}")
                else:
                    # Fall back to generic URL
                    url = item_data.get('url')
                    source = item_data.get('source', self.media_utils._determine_source_from_url(url))
                    self.log(f"Using generic URL: {url}")
        else:
            url = str(item_data)
            source = self.media_utils._determine_source_from_url(url)
        
        if not url:
            self.log(f"No URL or file path found for: {title}")
            return
        
        # Create a new item for the playlist
        display_text = title
        if artist:
            display_text = f"{artist} - {title}"
        
        # Create the item with appropriate icon
        queue_item = QListWidgetItem(display_text)
        queue_item.setData(Qt.ItemDataRole.UserRole, url)
        
        # Set icon based on source
        icon = self.ui_helpers.get_source_icon(url, {'source': source})
        queue_item.setIcon(icon)
        
        # Add to the list
        self.listWidget.addItem(queue_item)
        
        # Update internal playlist - include file_path if available
        playlist_item = {
            'title': title, 
            'artist': artist, 
            'url': url,
            'source': source,
            'entry_data': item_data
        }
        
        # Add file_path if it exists
        if isinstance(item_data, dict) and 'file_path' in item_data:
            playlist_item['file_path'] = item_data['file_path']
        
        self.current_playlist.append(playlist_item)
        
        self.log(f"Added to queue: {display_text} with URL/path: {url}")

    def remove_from_queue(self):
        """Elimina el elemento seleccionado de la cola de reproducción."""
        selected_items = self.listWidget.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            row = self.listWidget.row(item)
            self.listWidget.takeItem(row)
            
            # Actualizar la lista interna
            if 0 <= row < len(self.current_playlist):
                self.current_playlist.pop(row)

    def toggle_play_pause(self):
        """Alterna entre reproducir y pausar."""
        if not self.is_playing:
            self.play_media()
            self.playButton.setIcon(QIcon(":/services/b_pause"))
        else:
            self.media_utils.pause_media()
            self.playButton.setIcon(QIcon(":/services/b_play"))

    def play_media(self):
        """Reproduce la cola actual."""
        if not self.current_playlist:
            if self.listWidget.count() == 0:
                # Si no hay nada en la cola, intentar reproducir lo seleccionado en el árbol
                self.add_to_queue()
                if not self.current_playlist:
                    QMessageBox.information(self, "Información", "No hay elementos para reproducir")
                    return
            else:
                # Reconstruir la lista de reproducción desde la lista visual
                self.media_utils.rebuild_playlist_from_listwidget()
        
        # Si ya está reproduciendo, simplemente enviar comando de pausa/play
        if self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
            self.media_utils.send_mpv_command({"command": ["cycle", "pause"]})
            self.is_playing = True
            self.playButton.setIcon(QIcon(":/services/b_pause"))
            return
        
        # Si tenemos un índice actual válido, reproducir desde él
        if self.current_track_index >= 0 and self.current_track_index < len(self.current_playlist):
            self.media_utils.play_from_index(self.current_track_index)
        else:
            # Si no, comenzar desde el principio
            self.media_utils.play_from_index(0)

    def previous_track(self):
        """Reproduce la pista anterior."""
        self.media_utils.previous_track()

    def next_track(self):
        """Reproduce la siguiente pista."""
        self.media_utils.next_track()

    def on_tree_selection_changed(self):
        """Handle selection changes in the tree widget without switching tabs"""
        try:
            # Get the current selected item
            selected_items = self.treeWidget.selectedItems()
            if not selected_items:
                return
                
            item = selected_items[0]
            
            # Get the data associated with the item
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Display information about the selected item without changing tabs
            if item_data and hasattr(self, 'textEdit'):
                # Format basic info in the text area instead of switching to Wiki tab
                title = item_data.get('title', '')
                artist = item_data.get('artist', '')
                item_type = item_data.get('type', '')
                
                info_text = f"Selected: {title}\n"
                if artist:
                    info_text += f"Artist: {artist}\n"
                if item_type:
                    info_text += f"Type: {item_type}\n"
                    
                # Add file path if available
                if item_data.get('file_path'):
                    info_text += f"Path: {item_data.get('file_path')}\n"
                    
                # Update the text area
                self.textEdit.append(info_text)
        except Exception as e:
            self.log(f"Error handling tree selection change: {str(e)}")

    def on_guardar_playlist_clicked(self):
        """Handle save playlist button click"""
        # Use the correct combobox name from your UI file
        if not hasattr(self, 'guardar_playlist_comboBox'):
            self.log("ComboBox para guardar playlist no encontrado")
            return
            
        combo = self.guardar_playlist_comboBox
        selected = combo.currentText()
        print(f"selected!!! {selected}")
        if selected == "Spotify":
            self.spotify_manager.save_to_spotify_playlist()
        elif selected == "Playlist local":
            self.playlist_manager.save_current_playlist()  # Tu función existente
        elif selected == "Youtube":
            self.log("Guardado en Youtube no implementado aún")

    def load_all_playlists(self):
        """Carga todas las playlists (Spotify, locales, RSS) al inicio"""
        try:
            # Cargar playlists existentes (Spotify, locales, etc.)
            if not hasattr(self, 'playlists') or not isinstance(self.playlists, dict):
                self.log("Inicializando estructura de playlists...")
                self.playlists = {'spotify': [], 'local': [], 'rss': []}
            
            # Cargar desde el archivo guardado si existe
            loaded_playlists = self.playlist_manager.load_playlists()
            if isinstance(loaded_playlists, dict):
                self.playlists = loaded_playlists
            
            # Cargar playlists de Spotify si está configurado
            if self.spotify_client_id and self.spotify_client_secret:
                self.spotify_manager.setup_spotify()
                if hasattr(self, 'spotify_authenticated') and self.spotify_authenticated:
                    self.spotify_manager.load_spotify_playlists()
            
            # Cargar playlists locales explícitamente
            local