# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import traceback
import subprocess
import threading
from pathlib import Path
import resources_rc

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QInputDialog, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QTextEdit, QTabWidget, QMessageBox, QMenu, QDialogButtonBox, QLabel,
    QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy, QApplication, QDialog, QComboBox, QProgressDialog,
    QStackedWidget, QSlider, QSpinBox, QRadioButton
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal, QUrl, QRunnable, pyqtSlot, QObject, QThreadPool, QSize, QTimer
from PyQt6.QtGui import QIcon, QMovie

# Añadir ruta raíz al path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import resources_rc
from base_module import BaseModule, PROJECT_ROOT

# Importar submódulos
from modules.submodules.url_playlist.search_workers import InfoLoadWorker, SearchWorker, SearchSignals
from modules.submodules.url_playlist.spotify_manager import (
    setup_spotify, get_spotify_token, refresh_token, api_call_with_retry,
    create_spotify_playlist, add_tracks_to_spotify_playlist, load_spotify_playlists
)
from modules.submodules.url_playlist.lastfm_manager import (
    setup_lastfm_menu_items, sync_lastfm_scrobbles, load_lastfm_scrobbles_period,
    load_lastfm_scrobbles_month, load_lastfm_scrobbles_year, display_scrobbles_in_tree,
    populate_scrobbles_time_menus, get_track_links_from_db, get_lastfm_cache_path
)
from modules.submodules.url_playlist.playlist_manager import (
    parse_pls_file, load_local_playlists, create_local_playlist, save_playlists,
    load_rss_playlists, move_rss_playlist_to_listened, update_playlist_comboboxes,
    on_guardar_playlist_clicked, count_tracks_in_playlist
)
from modules.submodules.url_playlist.media_utils import (
    play_from_index, play_single_url, stop_playback, send_mpv_command,
    toggle_play_pause, next_track, previous_track, add_to_queue, remove_from_queue
)
from modules.submodules.url_playlist.ui_helpers import (
    setup_service_icons, get_source_icon, format_duration, 
    setup_unified_playlist_menu, update_unified_playlist_menu, setup_context_menus,
    display_search_results, display_external_results, on_tree_double_click, on_list_double_click,
    show_advanced_settings, on_tree_selection_changed, on_spotify_playlist_changed,
    on_playlist_rss_changed, on_playlist_local_changed, clear_playlist, show_mark_as_listened_dialog,
    _add_result_to_tree, load_rss_playlist_content_to_tree
)
from modules.submodules.url_playlist.db_manager import (
    search_database_links, _process_database_results, perform_search_with_service_filter
)
from modules.submodules.url_playlist.rss_manager import (
    setup_rss_controls
)

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
        self.lastfm_manager_key = kwargs.get('lastfm_manager_key')
        self.lastfm_username = kwargs.get('lastfm_username')
        self.exclude_spotify_from_local = kwargs.get('exclude_spotify_from_local', True)
        self.playlists = {'spotify': [], 'local': [], 'rss': []}





        # Credentials
        
        # Lastfm
        self.lastfm_api_key = os.environ.get("LASTFM_API_KEY") or kwargs.get('lastfm_api_key')
        self.lastfm_username = os.environ.get("LASTFM_USERNAME") or kwargs.get('lastfm_username')
        self.lastfm_secret = os.environ.get("LASTFM_SECRET") or kwargs.get('lastfm_secret')
        self.scrobbles_limit = os.environ.get("SCROBBLES_LIMIT") or kwargs.get('scrobbles_limit')
        self.scrobbles_by_date = os.environ.get("SCROBBLES_BY_DATE") or kwargs.get('scrobbles_by_date')
        
        # Spotify
        # self.spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID") or kwargs.get('spotify_client_id')
        # self.spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET") or kwargs.get('spotify_client_secret')
        self.spotify_user_id = os.environ.get("SPOTIFY_USER_ID") or kwargs.get('spotify_user_id')
        self.spotify_redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI") or kwargs.get('spotify_redirect_uri')
        
        # RSS
        self.rss_url = os.environ.get("FRESHRSS_URL") or kwargs.get('freshrss_url')
        self.rss_user = os.environ.get("FRESHRSS_USER") or kwargs.get('freshrss_user')
        self.rss_auth_token = os.environ.get("FRESHRSS_API_KEY") or kwargs.get('freshrss_api_key')

        # Musicbrainz
        self.musicbrainz_username = os.environ.get("MUSICBRAINZ_USERNAME") or kwargs.get('musicbrainz_username')
        self.musicbrainz_password = os.environ.get("MUSICBRAINZ_PASSWORD") or kwargs.get('musicbrainz_password')
        

        # Paths
        self.spotify_token_path = kwargs.get('spotify_token_path', os.path.join(PROJECT_ROOT, ".content", "cache", "spotify_token.txt"))
        self.spotify_playlist_path = kwargs.get('spotify_playlist_path', os.path.join(PROJECT_ROOT, ".content", "cache", "spotify_playlist_path"))
        self.lastfm_cache_path = kwargs.get('lastfm_cache_path', os.path.join(PROJECT_ROOT, ".content", "cache", "lastfm_cache.json"))

        # Log the received configuration
        print(f"[UrlPlayer] Received configs - DB: {self.db_path}, Spotify credentials: {bool(self.spotify_client_id)}, Last.fm credentials: {bool(self.lastfm_manager_key)}")
        
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
        self.freshrss_url = kwargs.pop('freshrss_url', '')
        self.freshrss_username = kwargs.pop('freshrss_user', '')
        self.freshrss_auth_token = kwargs.pop('freshrss_api_key', '')
        
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

        from tools.player_manager import PlayerManager
        self.player_manager = PlayerManager(parent=self)

        # Connect player manager signals
        self.player_manager.playback_started.connect(self.on_playback_started)
        self.player_manager.playback_stopped.connect(self.on_playback_stopped)
        self.player_manager.playback_paused.connect(self.on_playback_paused)
        self.player_manager.playback_resumed.connect(self.on_playback_resumed)
        self.player_manager.track_finished.connect(self.on_track_finished)
        self.player_manager.playback_error.connect(self.on_playback_error)



        self.treeWidget.setProperty("controller", self)
        self._is_initializing = True
        
        # Primero cargar las credenciales con tu método existente
        self._load_api_credentials_from_env()  # Tu método existente

        # Luego configurar Spotify solo si tenemos credenciales
        if self.spotify_client_id and self.spotify_client_secret:
            setup_spotify(self)
            
            # Una vez configurado, cargar las playlists
            if hasattr(self, 'playlist_spotify_comboBox') and self.spotify_authenticated:
                load_spotify_playlists(self)

        # Ensure these are available in environment variables for imported modules
        self._set_api_credentials_as_env()
        
        # Update service enabled flags based on credentials
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        self.lastfm_enabled = bool(self.lastfm_manager_key)
        
        # Update included_services based on credentials
        self.included_services['spotify'] = self.spotify_enabled
        self.included_services['lastfm'] = self.lastfm_enabled
        
        # Log the final configuration
        print(f"[UrlPlayer] Final config - DB: {self.db_path}, Spotify enabled: {self.spotify_enabled}, Last.fm enabled: {self.lastfm_enabled}")

        # Initialize the "only local" setting with default value of False
        self.urlplaylist_only_local = kwargs.get('urlplaylist_only_local', False)
        
        # Convert to boolean if it's a string
        if isinstance(self.urlplaylist_only_local, str):
            self.urlplaylist_only_local = self.urlplaylist_only_local.lower() == 'true'
            
        # Set flag as attribute
        self.log(f"Initialize urlplaylist_only_local: {self.urlplaylist_only_local}")   

        self._is_initializing = False

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
        self.initialize_playlist_ui_references()
        
        # Cargar configuración
        self.load_settings()

        # Configurar nombres y tooltips
        self.searchButton.setText("Buscar")
        self.searchButton.setToolTip("Buscar información sobre la URL")
        self.playButton.setIcon(QIcon(":/services/b_play"))
        self.playButton.setToolTip("Reproducir/Pausar")
        self.rewButton.setIcon(QIcon(":/services/b_prev"))
        self.rewButton.setToolTip("Anterior")
        self.ffButton.setIcon(QIcon(":/services/b_ff"))
        self.ffButton.setToolTip("Siguiente")
        self.delButton.setIcon(QIcon(":/services/b_minus_star"))
        self.delButton.setToolTip("Eliminar de la cola")
        self.addButton.setIcon(QIcon(":/services/b_addstar"))
        self.addButton.setToolTip("Añadir a la cola")
        
        # Configurar el botón unificado de playlists
        from modules.submodules.url_playlist.ui_helpers import setup_unified_playlist_button
        setup_unified_playlist_button(self)
        
        # Aplicar la configuración de vista actual
        self.update_playlist_view()
        
        # Configure TreeWidget for better display
        if hasattr(self, 'treeWidget') and self.treeWidget:
            # Set column headers
            self.treeWidget.setHeaderLabels(["Título", "Artista", "Tipo", "Track/Año", "Duración"])
            

            self.treeWidget.setColumnWidth(0, 250)  # Título
            self.treeWidget.setColumnWidth(1, 100)  # Artista
            self.treeWidget.setColumnWidth(2, 80)   # Tipo
            self.treeWidget.setColumnWidth(3, 70)   # Track/Año
            self.treeWidget.setColumnWidth(4, 70)   # Duración
            
            # Set indentation for hierarchy visualization
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
        
        # Setup services combo
        self.setup_services_combo()
        
        # Find and setup tipo_combo if it exists
        if not hasattr(self, 'tipo_combo'):
            self.tipo_combo = self.findChild(QComboBox, 'tipo_combo')
            
        # If tipo_combo exists, set default items if empty
        if self.tipo_combo and self.tipo_combo.count() == 0:
            self.tipo_combo.addItem("Todo")
            self.tipo_combo.addItem("Artista")
            self.tipo_combo.addItem("Álbum")
            self.tipo_combo.addItem("Canción")

        # Ensure RSS combobox is accessible
        if not hasattr(self, 'playlist_rss_comboBox'):
            self.playlist_rss_comboBox = self.findChild(QComboBox, 'playlist_rss_comboBox')
        
        # Set up Last.fm scrobbles menu
        from modules.submodules.url_playlist.lastfm_manager import setup_scrobbles_menu
        setup_scrobbles_menu(self)
        
        # Connect slider and spinbox in settings
        scrobbles_slider = self.findChild(QSlider, 'scrobbles_slider')
        scrobbles_spinbox = self.findChild(QSpinBox, 'scrobblers_spinBox')
        
        if scrobbles_slider and scrobbles_spinbox:
            # Connect them bidirectionally
            scrobbles_slider.valueChanged.connect(scrobbles_spinbox.setValue)
            scrobbles_spinbox.valueChanged.connect(scrobbles_slider.setValue)
        
        # Default service priority indices
        if not hasattr(self, 'service_priority_indices'):
            self.service_priority_indices = [0, 1, 3, 2]

        # Set up Last.fm controls and menus
        from modules.submodules.url_playlist.lastfm_manager import connect_lastfm_controls, setup_scrobbles_menu, load_lastfm_cache_if_exists
        connect_lastfm_controls(self)
        setup_scrobbles_menu(self)
        load_lastfm_cache_if_exists(self)

        # Load playlists at startup
        self.load_all_playlists()

        # Setup service icons
        from modules.submodules.url_playlist.ui_helpers import setup_service_icons
        setup_service_icons(self)

        # Setup loading indicator
        from modules.submodules.url_playlist.ui_helpers import setup_loading_indicator
        setup_loading_indicator(self)

        # Update service combo based on configuration
        self.update_service_combo()

        # Connect signals
        self.connect_signals()

    def log(self, message):
        """Registra un mensaje en el TextEdit y en la consola."""
        if hasattr(self, 'textEdit') and self.textEdit:
            self.textEdit.append(message)
        print(f"[UrlPlayer] {message}")

    # Método para cargar la UI
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



    def perform_search(self):
        """Performs a search based on the selected service and query."""
        query = self.lineEdit.text().strip()
        if not query:
            return
        
        # Obtener el estado de only_local
        only_local = False
        if hasattr(self, 'urlplaylist_only_local'):
            only_local = self.urlplaylist_only_local
        
        # Utilizar la nueva función de búsqueda
        perform_search_with_service_filter(self, query, only_local)

    def connect_signals(self):
        """Conecta las señales de los widgets a sus respectivos slots."""
        try:
            # Conectar señales con verificación previa
            if self.searchButton:
                self.searchButton.clicked.connect(self.perform_search)
                    
            if self.playButton:
                self.playButton.clicked.connect(lambda: toggle_play_pause(self))            
            if self.rewButton:
                self.rewButton.clicked.connect(lambda: previous_track(self))
            
            if self.ffButton:
                self.ffButton.clicked.connect(lambda: next_track(self))
            
            if self.addButton:
                self.addButton.clicked.connect(lambda: add_to_queue(self))
            
            if self.delButton:
                self.delButton.clicked.connect(lambda: remove_from_queue(self))            

            if self.lineEdit:
                self.lineEdit.returnPressed.connect(self.perform_search)
                print("LineEdit conectado para búsqueda con Enter")

            # Conectar eventos de doble clic
            if self.treeWidget:
                # Ensure signal is connected only once
                try:
                    # Primero desconectamos la señal si ya estaba conectada
                    self.treeWidget.itemDoubleClicked.disconnect()
                except:
                    pass
                # Conectamos la señal directamente a la función, que ahora espera dos argumentos
                from modules.submodules.url_playlist.ui_helpers import on_tree_double_click
                self.treeWidget.itemDoubleClicked.connect(on_tree_double_click)

            if self.listWidget:
                # First disconnect to avoid multiple connections
                try:
                    self.listWidget.itemDoubleClicked.disconnect()
                except TypeError:
                    pass  # If it wasn't connected, that's fine
                # Connect to the right method
                from modules.submodules.url_playlist.ui_helpers import on_list_double_click
                self.listWidget.itemDoubleClicked.connect(on_list_double_click)
            
            if hasattr(self, 'ajustes_avanzados'):
                self.ajustes_avanzados.clicked.connect(lambda: show_advanced_settings(self))

            # Add this at the end
            if self.treeWidget:
                # Connect item selection changed
                from modules.submodules.url_playlist.ui_helpers import on_tree_selection_changed
                self.treeWidget.itemSelectionChanged.connect(lambda: on_tree_selection_changed(self))
                print("[UrlPlayer] Señales conectadas correctamente")

            # Playlist-related connections
            if hasattr(self, 'playlist_spotify_comboBox'):
                from modules.submodules.url_playlist.ui_helpers import on_spotify_playlist_changed
                self.playlist_spotify_comboBox.currentIndexChanged.connect(lambda idx: on_spotify_playlist_changed(self, idx))
            
            # Conectar señal del combobox RSS
            if hasattr(self, 'playlist_rss_comboBox'):
                try:
                    self.playlist_rss_comboBox.currentIndexChanged.disconnect()
                except:
                    pass
                from modules.submodules.url_playlist.ui_helpers import on_playlist_rss_changed
                self.playlist_rss_comboBox.currentIndexChanged.connect(lambda idx: on_playlist_rss_changed(self, idx))
                    
            # Set up additional controls for RSS
            from modules.submodules.url_playlist.rss_manager import setup_rss_controls
            setup_rss_controls(self)
            
            if hasattr(self, 'playlist_local_comboBox'):
                # First disconnect to avoid multiple connections
                try:
                    self.playlist_local_comboBox.currentIndexChanged.disconnect()
                except:
                    pass
                
                from modules.submodules.url_playlist.ui_helpers import on_playlist_local_changed
                self.playlist_local_comboBox.currentIndexChanged.connect(lambda idx: on_playlist_local_changed(self, idx))

            # For the save playlist button
            if hasattr(self, 'GuardarPlaylist'):
                try:
                    self.GuardarPlaylist.clicked.disconnect()
                except TypeError:
                    pass
                from modules.submodules.url_playlist.playlist_manager import on_guardar_playlist_clicked
                self.GuardarPlaylist.clicked.connect(lambda: on_guardar_playlist_clicked(self))
            
            if hasattr(self, 'VaciarPlaylist'):
                from modules.submodules.url_playlist.ui_helpers import clear_playlist
                self.VaciarPlaylist.clicked.connect(lambda: clear_playlist(self))
            
            # Connect signals for RSS playlist operations
            self.ask_mark_as_listened_signal.connect(lambda data: show_mark_as_listened_dialog(self, data))
            self.show_error_signal.connect(lambda msg: QMessageBox.critical(self, "Error", msg))

            # Setup context menus
            from modules.submodules.url_playlist.ui_helpers import setup_context_menus
            setup_context_menus(self)

            # Update RSS playlists automatically at startup
            from modules.submodules.url_playlist.playlist_manager import load_rss_playlists
            load_rss_playlists(self)

            if self.playButton:
                self.playButton.clicked.connect(self.toggle_play_pause)
            
            if self.rewButton:
                self.rewButton.clicked.connect(self.play_previous)
            
            if self.ffButton:
                self.ffButton.clicked.connect(self.play_next)



        except Exception as e:
            print(f"[UrlPlayer] Error al conectar señales: {str(e)}")
            import traceback
            print(traceback.format_exc())

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


    def initialize_playlist_ui_references(self):
        """Inicializa las referencias a los widgets de playlist en la UI"""
        try:
            # Comprobar si el stacked widget existe
            self.playlist_stack = self.findChild(QStackedWidget, 'playlist_stack')
            if not self.playlist_stack:
                self.log("Error: No se pudo encontrar el widget 'playlist_stack'")
                return False
                
            # Buscar las páginas
            self.separate_page = self.findChild(QWidget, 'separate_page')
            self.unified_page = self.findChild(QWidget, 'unified_page')
            
            # Buscar el botón unificado
            self.unified_playlist_button = self.findChild(QPushButton, 'unified_playlist_button')
            if not self.unified_playlist_button:
                self.log("Error: No se pudo encontrar el botón 'unified_playlist_button'")
                return False
                
            # Inicializar el botón unificado
            setup_unified_playlist_menu(self)
            
            self.log("Referencias UI de playlist inicializadas correctamente")
            return True
        except Exception as e:
            self.log(f"Error inicializando referencias UI: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return False


    def load_settings(self):
        """Loads module configuration with standard paths"""
        try:
            # Standard config path
            config_path = self.get_app_path("config/config.yml")
            
            if not os.path.exists(config_path):
                self.log(f"Config file not found at: {config_path}")
                self._initialize_default_values()
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
                    if 'lastfm_manager_key' in global_config:
                        self.lastfm_manager_key = global_config['lastfm_manager_key']
                
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
                self._initialize_default_values()
        except Exception as e:
            self.log(f"Overall error in load_settings: {e}")
            self._initialize_default_values()



    def _initialize_default_values(self):
        """Initialize default values for settings when configuration can't be loaded"""
        self.log("Initializing default values for settings")
        
        # Default paths
        self.db_path = self.get_app_path("db/musica.sqlite")
        self.spotify_token_path = self.get_app_path(".content/cache/spotify_token.txt")
        self.spotify_playlist_path = self.get_app_path(".content/cache/spotify_playlist_path")
        
        # Default service configuration
        self.included_services = {
            'youtube': True,
            'soundcloud': True,
            'bandcamp': True,
            'spotify': False,  # Will be enabled if credentials are found
            'lastfm': False    # Will be enabled if credentials are found
        }
        
        # Default pagination
        self.num_servicios_spinBox = 10
        self.pagination_value = 10
        
        # Default API credentials (empty)
        self.spotify_client_id = None
        self.spotify_client_secret = None
        self.lastfm_manager_key = None
        self.lastfm_username = None
        
        # Default flags
        self.spotify_enabled = False
        self.lastfm_enabled = False
        
        # Create necessary directories
        os.makedirs(os.path.dirname(self.spotify_token_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.spotify_playlist_path), exist_ok=True)


    def get_app_path(self, file_path):
        """Create standardized paths relative to PROJECT_ROOT"""
        return os.path.join(PROJECT_ROOT, file_path)



    def update_playlist_view(self):
        """Actualiza la vista de las playlists según la configuración actual"""
        try:
            # Diagnóstico inicial
            self.log(f"Actualizando vista de playlist. Modo unificado: {getattr(self, 'playlist_unified_view', False)}")

            # Asegurarnos que tenemos el widget stack
            if not hasattr(self, 'playlist_stack'):
                self.log("Error: QStackedWidget 'playlist_stack' no encontrado")
                return False
                
            # Verificar botón unificado
            if not hasattr(self, 'unified_playlist_button'):
                self.log("Error: QPushButton 'unified_playlist_button' no encontrado")
                return False
            
            # Make sure the button is visible first (this is critical)
            self.unified_playlist_button.setVisible(True)
                
            # Configurar el botón unificado si aún no tiene menú
            if not self.unified_playlist_button.menu():
                setup_unified_playlist_menu(self)
                

            # Diagnóstico de los widgets
            self.log(f"playlist_stack tiene {self.playlist_stack.count()} páginas")
            self.log(f"Widget actual: {self.playlist_stack.currentWidget()}")

            # Cambiar a la vista según la configuración
            if hasattr(self, 'playlist_unified_view') and self.playlist_unified_view:
                # Cambiar al índice de la página unificada (asumiendo que es el índice 1)
                self.playlist_stack.setCurrentIndex(1)
                
                # Actualizar el menú unificado
                update_unified_playlist_menu(self)
                self.log("Cambiado a vista de playlist unificada")
            else:
                # Cambiar al índice de la página separada (asumiendo que es el índice 0)
                self.playlist_stack.setCurrentIndex(0)
                
                # Actualizar visibilidad de los comboboxes individuales
                if hasattr(self, 'playlist_local_comboBox'):
                    self.playlist_local_comboBox.setVisible(
                        self.get_setting_value('show_local_playlists', True))
                    
                if hasattr(self, 'playlist_spotify_comboBox'):
                    self.playlist_spotify_comboBox.setVisible(
                        self.get_setting_value('show_spotify_playlists', True))
                    
                if hasattr(self, 'playlist_rss_comboBox'):
                    self.playlist_rss_comboBox.setVisible(
                        self.get_setting_value('show_rss_playlists', True))
                    
                self.log("Cambiado a vista de playlists separadas")
            
            return True
        except Exception as e:
            self.log(f"Error actualizando vista de playlist: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return False


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


    def load_all_playlists(self):
        """Carga todas las playlists (Spotify, locales, RSS) al inicio"""
        try:
            # Cargar playlists existentes (Spotify, locales, etc.)
            if not hasattr(self, 'playlists') or not isinstance(self.playlists, dict):
                self.log("Inicializando estructura de playlists...")
                self.playlists = {'spotify': [], 'local': [], 'rss': []}
            
            # Cargar desde el archivo guardado si existe
            loaded_playlists = self.load_playlists()
            if isinstance(loaded_playlists, dict):
                self.playlists = loaded_playlists
            
            # Cargar playlists de Spotify si está configurado
            if self.spotify_client_id and self.spotify_client_secret:
                setup_spotify(self)
                if hasattr(self, 'spotify_authenticated') and self.spotify_authenticated:
                    load_spotify_playlists(self)
            
            # Cargar playlists locales explícitamente
            local_playlists = load_local_playlists(self)
            if local_playlists:
                self.playlists['local'] = local_playlists
            
            # IMPORTANTE: Cargar playlists RSS en el combobox
            self.log("Cargando playlists RSS...")
            if os.path.exists(self.rss_pending_dir):
                result = load_rss_playlists(self)
                self.log(f"Resultado de carga de playlists RSS: {result}")
            
            # Actualizar los comboboxes con las playlists cargadas
            update_playlist_comboboxes(self)
            
            # Update playlist view
            self.update_playlist_view()
            
        except Exception as e:
            self.log(f"Error cargando playlists: {str(e)}")
            import traceback
            self.log(traceback.format_exc())


    def _load_api_credentials_from_env(self):
        """Load API credentials from environment variables with better fallbacks"""
        # First try environment variables
        if not self.spotify_client_id:
            self.spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
            if not self.spotify_client_id:
                print("No se encontraron credenciales (client) de Spotify en las variables de entorno.")
        
        if not self.spotify_client_secret:
            self.spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
            if not self.spotify_client_secret:
                print("No se encontraron credenciales (secreto) de Spotify en las variables de entorno.")
        
        if not self.lastfm_api_key:
            self.lastfm_api_key = os.environ.get("LASTFM_API_KEY")
            if not self.lastfm_api_key:
                print("No se encontraron credenciales (API) de Last.fm en las variables de entorno.")

        if not self.lastfm_username:
            self.lastfm_username = os.environ.get("LASTFM_USERNAME")
            if not self.lastfm_username:
                print("No se encontraron credenciales (usuario) de Last.fm en las variables de entorno.")
        
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
                            if not self.lastfm_username:
                                self.lastfm_username = api_config['lastfm'].get('user')
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
            if not self.lastfm_username:
                self.lastfm_username = os.environ.get("LASTFM_USERNAME")
                
            print("[UrlPlayer] Attempted to load credentials from .env files")
        except ImportError:
            # dotenv is not installed, that's fine
            pass



    def get_setting_value(self, key, default=None):
        """Get a setting value with default fallback"""
        if hasattr(self, key):
            return getattr(self, key)
        return default


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
            
        # Update enabled flags based on credentials
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        self.lastfm_enabled = bool(self.lastfm_api_key)
        
        # Update included_services based on what's available
        if not self.spotify_enabled and 'spotify' in self.included_services:
            self.included_services['spotify'] = False
            print("[UrlPlayer] Disabled Spotify service due to missing credentials")
            
        if not self.lastfm_enabled and 'lastfm' in self.included_services:
            self.included_services['lastfm'] = False
            print("[UrlPlayer] Disabled Last.fm service due to missing credentials")


    def load_playlists(self):
        """Load playlists from the standard location"""
        try:
            # Check if the path exists and is a file
            if not os.path.exists(self.spotify_playlist_path) or not os.path.isfile(self.spotify_playlist_path):
                # Create empty playlist structure
                playlists_data = {
                    'spotify': [],
                    'local': [],
                    'rss': []
                }
                save_playlists(playlists_data)
                return playlists_data
            
            # Try to load the file
            with open(self.spotify_playlist_path, 'r', encoding='utf-8') as f:
                playlists_data = json.load(f)
                
            # Validate that it's a dictionary
            if not isinstance(playlists_data, dict):
                self.log("Error: El archivo de playlists no contiene un diccionario válido")
                return {'spotify': [], 'local': [], 'rss': []}
                
            # Ensure all expected keys exist
            for key in ['spotify', 'local', 'rss']:
                if key not in playlists_data:
                    playlists_data[key] = []
                    
            return playlists_data
                
        except Exception as e:
            self.log(f"Error loading playlists: {e}")
            # Return a valid empty structure
            return {'spotify': [], 'local': [], 'rss': []}


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
            
            # Load urlplaylist_only_local setting
            if 'urlplaylist_only_local' in module_args:
                value = module_args['urlplaylist_only_local']
                if isinstance(value, str):
                    self.urlplaylist_only_local = value.lower() == 'true'
                else:
                    self.urlplaylist_only_local = bool(value)
                self.log(f"Loaded urlplaylist_only_local: {self.urlplaylist_only_local}")
            else:
                self.urlplaylist_only_local = False
            
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
            
            # Additional your existing code...
            
            self.log("Module settings loaded successfully")
        except Exception as e:
            self.log(f"Error loading module settings: {e}")


    def _save_advanced_settings(self, dialog):
        """Guarda los ajustes del diálogo en las variables del objeto."""
        try:
            # Guardar valor de paginación
            if hasattr(dialog, 'num_servicios_spinBox'):
                self.num_servicios_spinBox = dialog.num_servicios_spinBox.value()
                self.log(f"Set pagination to {self.num_servicios_spinBox} results per page")
            
            # Guardar configuración de inclusión de servicios
            checkbox_mapping = {
                'youtube_check': 'youtube',
                'soundcloud_check': 'soundcloud',
                'bandcamp_check': 'bandcamp',
                'spotify_check': 'spotify',
                'lastfm_check': 'lastfm'
            }
            
            for checkbox_name, service_key in checkbox_mapping.items():
                if hasattr(dialog, checkbox_name):
                    checkbox = getattr(dialog, checkbox_name)
                    # Store actual boolean, not string
                    self.included_services[service_key] = checkbox.isChecked()
                    self.log(f"Service {service_key} included: {checkbox.isChecked()}")
            
            # Save playlist view settings
            self.playlist_unified_view = dialog.pl_unidas.isChecked()
            
            # Save playlist visibility settings
            self.show_local_playlists = dialog.locale_checkbox.isChecked()
            self.show_spotify_playlists = dialog.sp_checkbox.isChecked()
            self.show_rss_playlists = dialog.blogs_checkbox.isChecked()
            
            # Save "Only Local" setting
            only_local_checkbox = dialog.findChild(QCheckBox, 'urlplaylist_only_local')
            if only_local_checkbox:
                self.urlplaylist_only_local = only_local_checkbox.isChecked()
                self.log(f"Set urlplaylist_only_local to: {self.urlplaylist_only_local}")

            # Last.fm username
            if hasattr(dialog, 'entrada_usuario'):
                # El problema es que 'entrada_usuario' es un QLabel, no un QLineEdit
                # Necesitamos encontrar el campo de entrada correcto
                user_input = dialog.findChild(QLineEdit, 'user_input')
                if user_input:
                    lastfm_user = user_input.text().strip()
                    if lastfm_user:
                        self.lastfm_user = lastfm_user
                        self.log(f"Set Last.fm user to: {self.lastfm_user}")
            
            # Scrobbles limit
            if hasattr(dialog, 'scrobbles_slider') and hasattr(dialog, 'scrobblers_spinBox'):
                # Prefer spinbox value over slider for precision
                scrobbles_limit = dialog.scrobblers_spinBox.value()
                self.scrobbles_limit = scrobbles_limit
                self.log(f"Set scrobbles limit to: {self.scrobbles_limit}")
            
            # Display mode
            if hasattr(dialog, 'scrobbles_fecha') and hasattr(dialog, 'scrobbles_reproducciones'):
                self.scrobbles_by_date = dialog.scrobbles_fecha.isChecked()
                self.log(f"Set scrobbles display mode: by_date={self.scrobbles_by_date}")
            

            # Last.fm username - ahora usando QLineEdit
            lastfm_user_input = dialog.findChild(QLineEdit, 'entrada_usuario')
            if lastfm_user_input:
                lastfm_user = lastfm_user_input.text().strip()
                if lastfm_user:
                    self.lastfm_user = lastfm_user
                    self.log(f"Set Last.fm user to: {self.lastfm_user}")
            
            # Scrobbles limit - prioritize spinbox value
            scrobbles_spinbox = dialog.findChild(QSpinBox, 'scrobblers_spinBox')
            if scrobbles_spinbox:
                self.scrobbles_limit = scrobbles_spinbox.value()
                self.log(f"Set scrobbles limit to: {self.scrobbles_limit}")
            
            # Display mode
            by_date_radio = dialog.findChild(QRadioButton, 'scrobbles_fecha')
            by_plays_radio = dialog.findChild(QRadioButton, 'scrobbles_reproducciones')
            if by_date_radio and by_plays_radio:
                self.scrobbles_by_date = by_date_radio.isChecked()
                self.log(f"Set scrobbles display mode: by_date={self.scrobbles_by_date}")
            
            # Last.fm checkbox
            lastfm_checkbox = dialog.findChild(QCheckBox, 'lastfm_checkbox')
            if lastfm_checkbox:
                self.show_lastfm_scrobbles = lastfm_checkbox.isChecked()
                self.log(f"Set show Last.fm scrobbles to: {self.show_lastfm_scrobbles}")
            
            # Service priority
            service_priority_indices = []
            for combo_name in ['comboBox', 'comboBox_2', 'comboBox_3', 'comboBox_4']:
                combo = dialog.findChild(QComboBox, combo_name)
                if combo:
                    service_priority_indices.append(combo.currentIndex())
            
            if len(service_priority_indices) == 4:
                self.service_priority_indices = service_priority_indices
                self.log(f"Saved service priority indices: {service_priority_indices}")


            # Save settings to file
            self.save_settings()


            # Update the playlist view based on the new settings
            self.update_playlist_view()
            
            # Guardar en archivo YAML
            self.save_settings()
            
            # Actualizar UI o estado si es necesario
            self.update_service_combo()

            
            # Cerrar el diálogo
            dialog.accept()
        except Exception as e:
            self.log(f"Error saving advanced settings: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            QMessageBox.warning(self, "Error", f"Error al guardar la configuración: {str(e)}")



    def save_settings(self):
        """Guarda la configuración del módulo en el archivo de configuración general."""
        try:
            # Try multiple config paths
            config_paths = [
                os.path.join(PROJECT_ROOT, "config", "config.yml"),
                os.path.join(PROJECT_ROOT, "config", "config_placeholder.yaml"),
                os.path.join(PROJECT_ROOT, ".content", "config", "config.yml")
            ]
            
        
            config_path = None
            for path in config_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            
            if not config_path:
                self.log(f"No configuration file found. Creating new one at: {config_paths[0]}")
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(config_paths[0]), exist_ok=True)
                config_path = config_paths[0]
                
                # Create empty config
                config_data = {
                    'modules': [],
                    'modulos_desactivados': []
                }
            else:
                # Load existing config
                try:
                    # Try to use function from main module
                    try:
                        from main import load_config_file
                        config_data = load_config_file(config_path)
                    except ImportError:
                        # Fallback method
                        extension = os.path.splitext(config_path)[1].lower()
                        if extension in ['.yml', '.yaml']:
                            import yaml
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config_data = yaml.safe_load(f)
                        else:  # Assume JSON
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config_data = json.load(f)
                except Exception as e:
                    self.log(f"Error loading config file: {e}")
                    return

            # Add Last.fm specific settings
            lastfm_settings = {
                'lastfm_user': self.lastfm_user,
                'scrobbles_limit': self.scrobbles_limit,
                'scrobbles_by_date': self.scrobbles_by_date,
                'service_priority_indices': getattr(self, 'service_priority_indices', [0, 1, 2, 3])
            }

            # Asegurar que pagination_value esté sincronizado con num_servicios_spinBox
            self.pagination_value = self.num_servicios_spinBox
            
            # Store current database path - relative to PROJECT_ROOT if possible
            db_path_to_save = self.db_path
            if db_path_to_save and os.path.isabs(db_path_to_save):
                try:
                    # Convert to relative path if inside PROJECT_ROOT
                    rel_path = os.path.relpath(db_path_to_save, PROJECT_ROOT)
                    # Only use relative path if it doesn't go up directories
                    if not rel_path.startswith('..'):
                        db_path_to_save = rel_path
                except ValueError:
                    # Keep using absolute path if there's an error
                    pass
            
            # Preparar configuración de este módulo
            new_settings = {
                'mpv_temp_dir': '.config/mpv/_mpv_socket',  # Mantener valor existente o usar por defecto
                'pagination_value': self.pagination_value,
                'included_services': self.included_services,  # Now storing actual boolean values
                'db_path': db_path_to_save,
                'spotify_client_id': self.spotify_client_id,
                'spotify_client_secret': self.spotify_client_secret,
                'lastfm_api_key': self.lastfm_api_key,
                'lastfm_user': self.lastfm_user,
                
                # Configuración de vista de playlists
                'playlist_unified_view': getattr(self, 'playlist_unified_view', False),
                'show_local_playlists': getattr(self, 'show_local_playlists', True),
                'show_spotify_playlists': getattr(self, 'show_spotify_playlists', True),
                'show_rss_playlists': getattr(self, 'show_rss_playlists', True),
                
                # Añadir configuración de urlplaylist_only_local
                'urlplaylist_only_local': getattr(self, 'urlplaylist_only_local', False),
                
                # lastfm
                'lastfm_user': lastfm_settings['lastfm_user'],
                'scrobbles_limit': lastfm_settings['scrobbles_limit'],
                'scrobbles_by_date': lastfm_settings['scrobbles_by_date'],
                'service_priority_indices': lastfm_settings['service_priority_indices'],
                
                #freshrss
                'freshrss_url': self.freshrss_url,
                'freshrss_user': self.freshrss_username,
                'freshrss_api_key': self.freshrss_auth_token
            }
            
            # Añadir valores de depuración
            self.log(f"Guardando configuración - Vista unificada: {new_settings['playlist_unified_view']}")
            self.log(f"Guardando configuración - Only local: {new_settings['urlplaylist_only_local']}")
            
            # Bandera para saber si se encontró y actualizó el módulo
            module_updated = False
            
            # Try all possible module names
            module_names = ['Url Playlists', 'URL Playlist', 'URL Player']
            
            # Actualizar la configuración en el módulo correspondiente
            for module in config_data.get('modules', []):
                if module.get('name') in module_names:
                    # Reemplazar completamente los argumentos para evitar duplicados
                    module['args'] = new_settings
                    module_updated = True
                    break
            
            # Si no se encontró en los módulos activos, buscar en los desactivados
            if not module_updated:
                for module in config_data.get('modulos_desactivados', []):
                    if module.get('name') in module_names:
                        # Reemplazar completamente los argumentos para evitar duplicados
                        module['args'] = new_settings
                        module_updated = True
                        break
            
            # Si no se encontró el módulo, añadirlo a los módulos activos
            if not module_updated:
                self.log("Module not found in config, adding it to active modules")
                # Make sure the modules list exists
                if 'modules' not in config_data:
                    config_data['modules'] = []
                    
                # Add new module entry
                config_data['modules'].append({
                    'name': 'URL Playlist',
                    'path': 'modulos/url_playlist.py',
                    'args': new_settings
                })
            
            # Guardar la configuración actualizada
            try:
                # Try to use save function from main module
                try:
                    from main import save_config_file
                    save_config_file(config_path, config_data)
                except ImportError:
                    # Fallback method
                    extension = os.path.splitext(config_path)[1].lower()
                    if extension in ['.yml', '.yaml']:
                        import yaml
                        with open(config_path, 'w', encoding='utf-8') as f:
                            yaml.dump(config_data, f, sort_keys=False, default_flow_style=False, indent=2)
                    else:  # Assume JSON
                        import json
                        with open(config_path, 'w', encoding='utf-8') as f:
                            json.dump(config_data, f, indent=2)
            except Exception as e:
                self.log(f"Error saving config: {e}")
                return
                
            self.log(f"Configuración guardada en {config_path}")
        except Exception as e:
            self.log(f"Error al guardar configuración: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
   

    def on_playback_started(self):
        """Handle player starting playback"""
        self.is_playing = True
        self.playButton.setIcon(QIcon(":/services/b_pause"))
        self.log("Playback started")
        self.highlight_current_track()

    def on_playback_stopped(self):
        """Handle player stopping playback"""
        self.is_playing = False
        self.playButton.setIcon(QIcon(":/services/b_play"))
        self.log("Playback stopped")

    def on_playback_paused(self):
        """Handle player pausing playback"""
        self.is_playing = False
        self.playButton.setIcon(QIcon(":/services/b_play"))
        self.log("Playback paused")

    def on_playback_resumed(self):
        """Handle player resuming playback"""
        self.is_playing = True
        self.playButton.setIcon(QIcon(":/services/b_pause"))
        self.log("Playback resumed")

    def on_track_finished(self):
        """Handle track finishing playback"""
        self.log("Track finished")
        
        # Play next track if available
        if hasattr(self, 'current_playlist') and self.current_playlist:
            next_index = self.current_track_index + 1
            
            if next_index < len(self.current_playlist):
                # Play the next track
                self.current_track_index = next_index
                self.play_from_index(next_index)
            else:
                # End of playlist
                self.current_track_index = -1
                self.is_playing = False
                self.playButton.setIcon(QIcon(":/services/b_play"))
                self.log("End of playlist reached")

    def on_playback_error(self, error):
        """Handle player errors"""
        self.log(f"Playback error: {error}")
        
        # Try to recover by playing next track
        if hasattr(self, 'current_playlist') and self.current_playlist:
            next_index = self.current_track_index + 1
            
            if next_index < len(self.current_playlist):
                # Try to play the next track
                self.current_track_index = next_index
                self.play_from_index(next_index)


    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if not hasattr(self, 'current_playlist') or not self.current_playlist:
            # Nothing in playlist, try to add the selected item
            self.add_to_queue()
            if not self.current_playlist:
                self.log("Nothing to play")
                return
        
        if not self.is_playing:
            # If we have a current track, play/resume it
            if self.current_track_index >= 0 and self.current_track_index < len(self.current_playlist):
                if self.player_manager.is_playing:
                    self.player_manager.resume()
                else:
                    self.play_from_index(self.current_track_index)
            else:
                # Start from the beginning
                self.play_from_index(0)
        else:
            # Pause current playback
            self.player_manager.pause()

    def play_next(self):
        """Play the next track in the playlist"""
        if not hasattr(self, 'current_playlist') or not self.current_playlist:
            self.log("No playlist available")
            return
        
        next_index = self.current_track_index + 1
        
        # Loop back to beginning if at the end
        if next_index >= len(self.current_playlist):
            next_index = 0
        
        self.play_from_index(next_index)

    def play_previous(self):
        """Play the previous track in the playlist"""
        if not hasattr(self, 'current_playlist') or not self.current_playlist:
            self.log("No playlist available")
            return
        
        prev_index = self.current_track_index - 1
        
        # Loop to end if at the beginning
        if prev_index < 0:
            prev_index = len(self.current_playlist) - 1
        
        self.play_from_index(prev_index)

    def highlight_current_track(self):
        """Highlight the currently playing track in the list"""
        if not hasattr(self, 'listWidget') or not hasattr(self, 'current_track_index'):
            return
        
        # Reset all items to normal style
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            item.setForeground(self.palette().text())
            font = item.font()
            font.setBold(False)
            item.setFont(font)
        
        # Highlight the current track if valid
        if 0 <= self.current_track_index < self.listWidget.count():
            item = self.listWidget.item(self.current_track_index)
            item.setForeground(self.palette().highlight())
            font = item.font()
            font.setBold(True)
            item.setFont(font)