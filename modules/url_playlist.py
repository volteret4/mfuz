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
import spotipy

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
    setup_lastfm_menu_items, sync_lastfm_scrobbles, load_lastfm_scrobbles_period, sync_lastfm_scrobbles_safe,
    load_lastfm_scrobbles_month, load_lastfm_scrobbles_year, 
    populate_scrobbles_time_menus, get_track_links_from_db, get_lastfm_cache_path, load_lastfm_cache_if_exists,
    setup_scrobbles_menu, connect_lastfm_controls, force_load_scrobbles_data_from_db, load_lastfm_cache_if_exists
) 

from modules.submodules.url_playlist.lastfm_db import (
    display_scrobbles_in_tree
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
    setup_unified_playlist_menu, setup_context_menus, add_single_result_to_tree,
    display_search_results, display_external_results, on_tree_double_click, on_list_double_click,
    show_advanced_settings, on_tree_selection_changed, on_spotify_playlist_changed,
    on_playlist_rss_changed, on_playlist_local_changed, clear_playlist, show_mark_as_listened_dialog,
    _add_result_to_tree, load_rss_playlist_content_to_tree, show_loading_indicator
)
from modules.submodules.url_playlist.db_manager import (
    search_database_links, _process_database_results, perform_search_with_service_filter
)
from modules.submodules.url_playlist.rss_manager import (
    setup_rss_controls, update_unified_playlist_menu
)

from modules.submodules.url_playlist.progress_bar import setup_progress_bar

class UrlPlayer(BaseModule):
    """Módulo para reproducir música desde URLs (YouTube, SoundCloud, Bandcamp)."""
    # Definir señales personalizadas para comunicación entre hilos
    ask_mark_as_listened_signal = pyqtSignal(dict)  # Para preguntar si marcar como escuchada
    show_error_signal = pyqtSignal(str)  # Para mostrar errores desde hilos
    process_started_signal = pyqtSignal(str)
    process_progress_signal = pyqtSignal(int, str)
    process_finished_signal = pyqtSignal(str, int, int)  # message, success_count, total_count
    process_error_signal = pyqtSignal(str)
    spotify_albums_loaded_signal = pyqtSignal(object, object)  # Para álbumes cargados
    spotify_tracks_loaded_signal = pyqtSignal(object, object)  # Para pistas cargadas
    spotify_error_signal = pyqtSignal(object, str)  # Para errores
    request_spotify_auth = pyqtSignal()

    def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
        # Extraer configuraciones específicas de kwargs
        self.mpv_temp_dir = kwargs.pop('mpv_temp_dir', Path(os.path.expanduser("~"), ".config", "mpv", "_mpv_socket"))
        self.script_path = Path(f"{PROJECT_ROOT}/db/posts/crear_playlists_freshrss.py")
        
        # Extraer configuración de la base de datos con mejor manejo
        self.db_path = kwargs.get('db_path')
        if self.db_path and not os.path.isabs(self.db_path):
            self.db_path = Path(PROJECT_ROOT, self.db_path)
        
        # Extraer credenciales API
        self.spotify_authenticated = False
        self.spotify_playlists = {}
        self.spotify_user_id = None
        self.spotify_client_id = kwargs.get('spotify_client_id')
        self.spotify_client_secret = kwargs.get('spotify_client_secret')
        self.spotify_redirect_uri = kwargs.get('spotify_redirect_uri', 'http://localhost:8888/callback')
        
        self.lastfm_manager_key = kwargs.get('lastfm_manager_key')
        self.lastfm_username = kwargs.get('lastfm_username')
        self.exclude_spotify_from_local = kwargs.get('exclude_spotify_from_local', True)
        self.playlists = {'spotify': [], 'local': [], 'rss': []}
        


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
        self.spotify_token_path = kwargs.get('spotify_token_path', Path(PROJECT_ROOT, ".content", "cache", "spotify_token.txt"))
        self.spotify_playlist_path = kwargs.get('spotify_playlist_path', Path(PROJECT_ROOT, ".content", "cache", "spotify_playlist_path"))
        self.lastfm_cache_path = kwargs.get('lastfm_cache_path', Path(PROJECT_ROOT, ".content", "cache", "lastfm_cache.json"))



        # Credenciales Servidor FreshRss
        self.freshrss_url = kwargs.pop('freshrss_url', '')
        self.freshrss_username = kwargs.pop('freshrss_user', '')
        self.freshrss_auth_token = kwargs.pop('freshrss_api_key', '')
        

        # Log the received configuration
        print(f"[UrlPlayer] Received configs - DB: {self.db_path}, Spotify credentials: {bool(self.spotify_client_id)}, Last.fm credentials: {bool(self.lastfm_manager_key)}")
 


        # Inicializar variables esenciales
        self.player_process = None
        self.current_playlist = []
        self.current_track_index = -1
        self.media_info_cache = {}
        self.yt_dlp_process = None
        self.is_playing = False
        self.mpv_socket = None
        self.mpv_wid = None
        
        # Directorios para playlists RSS
        self.rss_pending_dir = kwargs.pop('rss_pending_dir', Path(PROJECT_ROOT, ".content", "playlists", "blogs", "pendiente"))
        self.rss_listened_dir = kwargs.pop('rss_listened_dir', Path(PROJECT_ROOT, ".content", "playlists", "blogs", "escuchado"))
        
        # Asegurar que los directorios existan
        os.makedirs(self.rss_pending_dir, exist_ok=True)
        os.makedirs(self.rss_listened_dir, exist_ok=True)

        # Servicios incluidos
        default_services = {
            'youtube': True,
            'soundcloud': True,
            'bandcamp': True,
            'spotify': False,
            'lastfm': False
        }
        
        included_services = kwargs.pop('included_services', {})
        self.included_services = {}
        
        # Configurar servicios incluidos
        for service, default_state in default_services.items():
            if service not in included_services:
                self.included_services[service] = default_state
            else:
                value = included_services[service]
                if isinstance(value, str):
                    self.included_services[service] = value.lower() == 'true'
                else:
                    self.included_services[service] = bool(value)
        
        # Inicialización de widgets
        self.lineEdit = None
        self.searchButton = None
        self.treeWidget = None
        self.play_button = None
        self.rew_button = None
        self.ff_button = None
        self.tabWidget = None
        self.listWidget = None
        self.del_button = None
        self.add_button = None
        self.textEdit = None
        self.info_wiki_textedit = None
        
        # Configuración de paginación
        self.num_servicios_spinBox = kwargs.pop('pagination_value', 10)
        
        # Llamar al constructor padre
        super().__init__(parent, theme, **kwargs)
        
        # Flag para indicar inicialización en progreso
        self._is_initializing = True
        
        # Configurar barras de progreso
        setup_progress_bar(self)
        
        # Conectar señales para comunicación entre hilos
        self._connect_thread_signals()

        # Inicializar PlayerManager
        from tools.player_manager import PlayerManager
        self.player_manager = PlayerManager(parent=self, logger=self.log)
        self._connect_player_signals()
        
        # Set up periodic memory cleanup every 5 minutes
        from PyQt6.QtCore import QTimer
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self.perform_memory_cleanup)
        self._cleanup_timer.start(300000)  # 5 minutes in milliseconds

        # Iniciar los procesos pesados en hilos separados
        self._start_async_initialization()

        # Conexión de señales Spotify
        self.spotify_albums_loaded_signal.connect(self._update_ui_with_albums)
        self.spotify_tracks_loaded_signal.connect(self._update_ui_with_tracks)
        self.spotify_error_signal.connect(self._show_spotify_error)
        
        self.request_spotify_auth.connect(self.authenticate_spotify_main_thread)


    def _update_ui_with_albums(self, artist_item, albums_data):
        """Actualiza la UI con los álbumes cargados por el hilo de Spotify"""
        try:
            # Eliminar el ítem de carga
            if artist_item.childCount() > 0:
                artist_item.takeChild(0)
            
            # Desempaquetar datos
            albums_by_type = albums_data.get('albums_by_type', {})
            artist_data = albums_data.get('artist_data', {})
            
            # Si no hay álbumes, añadir un mensaje
            if not any(albums_by_type.values()):
                from PyQt6.QtWidgets import QTreeWidgetItem
                no_albums_item = QTreeWidgetItem(artist_item)
                no_albums_item.setText(0, "No se encontraron álbumes")
                return
            
            # Añadir los álbumes organizados por tipo
            album_types_names = {
                'album': 'Álbumes',
                'single': 'Singles',
                'compilation': 'Recopilaciones'
            }
            
            from PyQt6.QtWidgets import QTreeWidgetItem
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QIcon
            
            for album_type, albums_list in albums_by_type.items():
                if not albums_list:
                    continue
                
                # Crear un nodo para el tipo de álbum
                type_item = QTreeWidgetItem(artist_item)
                type_item.setText(0, album_types_names.get(album_type, album_type.capitalize()))
                type_item.setIcon(0, QIcon(":/services/folder"))
                
                # Marcar este nodo como un agrupador, no un elemento real
                type_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'group', 'source': 'spotify'})
                
                # Añadir cada álbum
                for album in albums_list:
                    album_item = QTreeWidgetItem(type_item)
                    album_item.setText(0, album['name'])
                    album_item.setText(1, artist_data.get('artist', ''))
                    album_item.setText(2, "Álbum")
                    
                    # Añadir año si está disponible
                    if 'release_date' in album:
                        release_year = album['release_date'][:4] if album['release_date'] else ''
                        album_item.setText(3, release_year)
                    
                    # Añadir icono
                    album_item.setIcon(0, QIcon(":/services/spotify"))
                    
                    # Almacenar datos del álbum
                    album_data = {
                        'type': 'album',
                        'title': album['name'],
                        'artist': artist_data.get('artist', ''),
                        'url': album['external_urls']['spotify'],
                        'source': 'spotify',
                        'spotify_id': album['id'],
                        'spotify_uri': album['uri'],
                        'year': album.get('release_date', '')[:4] if album.get('release_date') else '',
                        'total_tracks': album.get('total_tracks', 0)
                    }
                    album_item.setData(0, Qt.ItemDataRole.UserRole, album_data)
                    
                    # Añadir un nodo hijo temporal para que se muestre el signo +
                    loading_item = QTreeWidgetItem(album_item)
                    loading_item.setText(0, "Cargando canciones...")
                    
                    # Configurar para mostrar indicador de expansión
                    album_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                
                # Expandir el nodo de tipo de álbum
                type_item.setExpanded(True)
        except Exception as e:
            self.log(f"Error actualizando UI con álbumes: {e}")
            import traceback
            self.log(traceback.format_exc())
    
    
    def authenticate_spotify_main_thread(self):
        """Esta función inicializa Spotify en el hilo principal"""
        self.log("Authenticating Spotify from main thread...")
        
        # Llamar directamente a la función en el módulo spotify_manager
        from modules.submodules.url_playlist.spotify_manager import setup_spotify
        result = setup_spotify(self)
        
        if result:
            self.log("Spotify authentication successful")
            # Cargar playlists después de la autenticación exitosa
            from modules.submodules.url_playlist.spotify_manager import load_spotify_playlists
            load_spotify_playlists(self)
            
            # Actualizar UI si es necesario
            if hasattr(self, 'update_service_combo'):
                self.update_service_combo()
        else:
            self.log("Spotify authentication failed")
        
        return result


    def _update_ui_with_tracks(self, album_item, tracks_data):
        """Actualiza la UI con las pistas cargadas por el hilo de Spotify"""
        try:
            # Eliminar el ítem de carga
            if album_item.childCount() > 0:
                album_item.takeChild(0)
            
            # Desempaquetar datos
            tracks = tracks_data.get('tracks', [])
            album_data = tracks_data.get('album_data', {})
            
            # Si no hay canciones, añadir un mensaje
            if not tracks:
                from PyQt6.QtWidgets import QTreeWidgetItem
                no_tracks_item = QTreeWidgetItem(album_item)
                no_tracks_item.setText(0, "No se encontraron canciones")
                return
            
            # Añadir cada canción
            from PyQt6.QtWidgets import QTreeWidgetItem
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QIcon
            
            for track in tracks:
                track_item = QTreeWidgetItem(album_item)
                track_item.setText(0, track['name'])
                
                # Artistas de la canción (pueden ser diferentes al artista del álbum)
                artists = [artist['name'] for artist in track['artists']]
                artist_str = ", ".join(artists)
                track_item.setText(1, artist_str)
                
                track_item.setText(2, "Canción")
                
                # Añadir número de pista
                if 'track_number' in track:
                    track_item.setText(3, str(track['track_number']))
                
                # Añadir duración si está disponible
                if 'duration_ms' in track:
                    duration_ms = track['duration_ms']
                    minutes = int(duration_ms / 60000)
                    seconds = int((duration_ms % 60000) / 1000)
                    track_item.setText(4, f"{minutes}:{seconds:02d}")
                
                # Añadir icono
                track_item.setIcon(0, QIcon(":/services/spotify"))
                
                # Almacenar datos de la canción
                track_data = {
                    'type': 'track',
                    'title': track['name'],
                    'artist': artist_str,
                    'album': album_data.get('title', ''),
                    'url': track['external_urls']['spotify'],
                    'source': 'spotify',
                    'spotify_id': track['id'],
                    'spotify_uri': track['uri'],
                    'track_number': track.get('track_number', 0),
                    'duration': track.get('duration_ms', 0) / 1000  # Convertir a segundos
                }
                track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
        except Exception as e:
            self.log(f"Error actualizando UI con canciones: {e}")
            import traceback
            self.log(traceback.format_exc())

    def _show_spotify_error(self, parent_item, error_message):
        """Muestra un mensaje de error en el árbol de Spotify"""
        try:
            # Eliminar el ítem de carga si existe
            if parent_item.childCount() > 0:
                parent_item.takeChild(0)
            
            # Añadir mensaje de error
            from PyQt6.QtWidgets import QTreeWidgetItem
            from PyQt6.QtGui import QIcon
            error_item = QTreeWidgetItem(parent_item)
            error_item.setText(0, f"Error: {error_message}")
            error_item.setIcon(0, QIcon(":/services/wiki"))
        except Exception as e:
            self.log(f"Error mostrando mensaje de error: {e}")


    def _connect_thread_signals(self):
        """Connect signals for thread communication"""
        self.process_started_signal.connect(self._on_process_started)
        self.process_progress_signal.connect(self._on_process_progress)
        self.process_finished_signal.connect(self._on_process_finished)
        self.process_error_signal.connect(self._on_process_error)
        
        # Inicializar variables para el diálogo de progreso
        self._progress_dialog = None

    def _connect_player_signals(self):
        """Conecta las señales del player manager"""
        self.player_manager.playback_started.connect(self.on_playback_started)
        self.player_manager.playback_stopped.connect(self.on_playback_stopped)
        self.player_manager.playback_paused.connect(self.on_playback_paused)
        self.player_manager.playback_resumed.connect(self.on_playback_resumed)
        self.player_manager.track_finished.connect(self.on_track_finished)
        self.player_manager.playback_error.connect(self.on_playback_error)

    def _start_async_initialization(self):
        """Inicia procesos de inicialización en hilos separados"""
        import threading
        
        # Crear hilos con nombres descriptivos para facilitar depuración
        api_thread = threading.Thread(target=self._initialize_apis, name="_initialize_apis", daemon=True)
        playlists_thread = threading.Thread(target=self._load_playlists_async, name="_load_playlists", daemon=True)
        
        # Iniciar hilos
        api_thread.start()
        playlists_thread.start()
        
        # Establecer un temporizador para verificar cuando todos los hilos hayan terminado
        from PyQt6.QtCore import QTimer
        self._init_check_timer = QTimer(self)
        self._init_check_timer.timeout.connect(self._check_initialization_complete)
        self._init_check_timer.start(100)  # Verificar cada 100 ms
  
    def _initialize_apis(self):
        """Inicializa las APIs en un hilo separado"""
        try:
            # Cargar credenciales desde el entorno o configuración
            self._load_api_credentials_from_env()
            
            # Configurar las credenciales como variables de entorno 
            self._set_api_credentials_as_env()
            
            # Configurar Spotify usando QTimer para ejecutar en el hilo principal
            if self.spotify_client_id and self.spotify_client_secret:
                self.log("Scheduling Spotify initialization on main thread...")
                # Usar la señal en lugar de QTimer
                self.request_spotify_auth.emit()              

            # Cargar caché de Last.fm si existe
            from modules.submodules.url_playlist.lastfm_manager import load_lastfm_cache_if_exists
            load_lastfm_cache_if_exists(self)
            
            # NUEVA LÍNEA: Cargar menús de scrobbles existentes desde la base de datos
            self._load_existing_scrobbles_menus()
            
            # Actualizar flags de servicios habilitados
            self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
            self.lastfm_enabled = bool(self.lastfm_api_key)
            
            # Actualizar included_services según credenciales
            self.included_services['spotify'] = self.spotify_enabled
            self.included_services['lastfm'] = self.lastfm_enabled
            
            self.log("Inicialización de APIs completada")
        except Exception as e:
            self.log(f"Error en inicialización de APIs: {str(e)}")
            import traceback
            self.log(traceback.format_exc())


    def _load_existing_scrobbles_menus(self):
        """Carga los menús de scrobbles con datos existentes en la base de datos"""
        try:
            if not hasattr(self, 'db_path') or not self.db_path:
                return False
                
            # Ejecutar en un hilo separado para no bloquear la UI
            import threading
            thread = threading.Thread(
                target=self._load_scrobbles_menus_from_db_thread,
                name="LoadScrobblesMenus",
                daemon=True
            )
            thread.start()
            
        except Exception as e:
            self.log(f"Error iniciando carga de menús de scrobbles: {str(e)}")

    def _load_scrobbles_menus_from_db_thread(self):
        """Carga los menús de scrobbles desde la base de datos en un hilo separado"""
        try:
            import sqlite3
            import os
            from datetime import datetime
            
            if not os.path.exists(self.db_path):
                self.log("Base de datos no encontrada para cargar menús de scrobbles")
                return
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Buscar tabla de scrobbles del usuario actual
            lastfm_username = getattr(self, 'lastfm_username', 'paqueradejere')
            possible_tables = [
                f"scrobbles_{lastfm_username}",
                "scrobbles_paqueradejere"
            ]
            
            scrobbles_table = None
            for table in possible_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone():
                    scrobbles_table = table
                    break
            
            if not scrobbles_table:
                self.log("No se encontró tabla de scrobbles")
                conn.close()
                return
                
            self.log(f"Cargando menús desde tabla: {scrobbles_table}")
            
            # Verificar que la tabla tiene timestamp
            cursor.execute(f"PRAGMA table_info({scrobbles_table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'timestamp' not in columns:
                self.log(f"Tabla {scrobbles_table} no tiene columna timestamp")
                conn.close()
                return
            
            # Obtener años con datos
            cursor.execute(f"""
            SELECT 
                CAST(strftime('%Y', datetime(timestamp, 'unixepoch')) AS INTEGER) as year,
                COUNT(*) as count
            FROM {scrobbles_table}
            WHERE timestamp > 0
            GROUP BY year
            ORDER BY year DESC
            """)
            
            years_results = cursor.fetchall()
            
            if not years_results:
                self.log("No se encontraron años con scrobbles")
                conn.close()
                return
            
            years_dict = {}
            
            for year_row in years_results:
                if not year_row[0]:
                    continue
                    
                year = year_row[0]
                count = year_row[1]
                
                if count > 0:
                    years_dict[year] = set()
                    
                    # Obtener meses para este año
                    cursor.execute(f"""
                    SELECT 
                        CAST(strftime('%m', datetime(timestamp, 'unixepoch')) AS INTEGER) as month,
                        COUNT(*) as count
                    FROM {scrobbles_table}
                    WHERE timestamp > 0 
                    AND strftime('%Y', datetime(timestamp, 'unixepoch')) = ?
                    GROUP BY month
                    ORDER BY month
                    """, (str(year),))
                    
                    months_results = cursor.fetchall()
                    
                    for month_row in months_results:
                        if not month_row[0]:
                            continue
                            
                        month = month_row[0]
                        month_count = month_row[1]
                        
                        if month_count > 0:
                            years_dict[year].add(month)
            
            conn.close()
            
            if years_dict:
                self.log(f"Encontrados {len(years_dict)} años con scrobbles en la base de datos")
                
                # Programar actualización de menús en el hilo principal
                from PyQt6.QtCore import QTimer
                
                def update_menus_main_thread():
                    try:
                        from modules.submodules.url_playlist.lastfm_manager import populate_scrobbles_time_menus
                        populate_scrobbles_time_menus(self, years_dict=years_dict)
                        self.log("Menús de scrobbles cargados desde base de datos existente")
                    except Exception as e:
                        self.log(f"Error actualizando menús desde base de datos: {e}")
                
                QTimer.singleShot(0, update_menus_main_thread)
            else:
                self.log("No se encontraron datos válidos de años/meses en la base de datos")
                
        except Exception as e:
            self.log(f"Error cargando menús de scrobbles desde base de datos: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

    def init_spotify_in_main_thread(self):
        """Esta función inicializa Spotify en el hilo principal"""
        from modules.submodules.url_playlist.spotify_manager import setup_spotify
        
        # Verificar que estamos en el hilo principal
        from PyQt6.QtCore import QThread, QCoreApplication
        if QThread.currentThread() != QCoreApplication.instance().thread():
            self.log("Error: Spotify initialization must be performed from the main thread")
            return False
        
        self.log("Initializing Spotify from main thread...")
        
        return setup_spotify(self)

    def _load_playlists_async(self):
        """Carga las playlists en un hilo separado"""
        try:
            # Inicializar estructura de playlists si es necesario
            if not hasattr(self, 'playlists') or not isinstance(self.playlists, dict):
                self.playlists = {'spotify': [], 'local': [], 'rss': []}
            
            # Cargar desde el archivo guardado si existe
            loaded_playlists = self.load_playlists()
            if isinstance(loaded_playlists, dict):
                self.playlists = loaded_playlists
            
            # Cargar playlists locales
            from modules.submodules.url_playlist.playlist_manager import load_local_playlists
            local_playlists = load_local_playlists(self)
            if local_playlists:
                self.playlists['local'] = local_playlists
            
            # Cargar playlists RSS
            if os.path.exists(self.rss_pending_dir):
                from modules.submodules.url_playlist.playlist_manager import load_rss_playlists
                load_rss_playlists(self)
            
            self.log("Carga de playlists completada")
        except Exception as e:
            self.log(f"Error en carga de playlists: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

    def _check_initialization_complete(self):
        """Verifica si todos los procesos de inicialización han terminado"""
        # Implementar lógica para verificar finalización de hilos
        import threading
        active_threads = [t for t in threading.enumerate() 
                        if t.name.startswith("_initialize_") or t.name.startswith("_load_")]
        
        if not active_threads:
            # Todos los hilos han terminado
            self._init_check_timer.stop()
            self._is_initializing = False
            
            # Actualizar UI en el hilo principal usando un timer de un solo disparo
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._update_ui_after_initialization)

    def _update_ui_after_initialization(self):
        """Actualiza la UI después de que todos los procesos de inicialización han terminado"""
        try:
            # Actualizar comboboxes con playlists cargadas
            from modules.submodules.url_playlist.playlist_manager import update_playlist_comboboxes
            update_playlist_comboboxes(self)
            
            # Actualizar vista de playlist
            self.update_playlist_view()
            
            # Actualizar combo de servicios
            self.update_service_combo()
            
            self.log("Inicialización completa, UI actualizada")
        except Exception as e:
            self.log(f"Error actualizando UI después de inicialización: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

    def _on_process_started(self, message):
        """Handle process started signal (runs in main thread)"""
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import Qt
        
        self._progress_dialog = QProgressDialog(message, "Cancel", 0, 100, self)
        self._progress_dialog.setWindowTitle("Processing")
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()

    def _on_process_progress(self, value, message=None):
        """Handle process progress signal (runs in main thread)"""
        if self._progress_dialog:
            if message:
                self._progress_dialog.setLabelText(message)
            self._progress_dialog.setValue(value)

    def _on_process_finished(self, message, success_count, total_count):
        """Handle process finished signal (runs in main thread)"""
        if self._progress_dialog:
            self._progress_dialog.setValue(100)
            self._progress_dialog.setLabelText(f"{message}\nProcesados: {success_count}/{total_count}")
            
            # Keep dialog open briefly
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(3000, self._progress_dialog.close)

    def _on_process_error(self, error_message):
        """Handle process error signal (runs in main thread)"""
        from PyQt6.QtWidgets import QMessageBox
        
        if self._progress_dialog:
            self._progress_dialog.close()
        
        QMessageBox.critical(self, "Error", error_message)


    def init_ui(self):
        """Inicializa la interfaz de usuario con carga diferida para elementos no críticos"""
        # Intentar cargar desde archivo UI
        ui_file_loaded = self.load_ui_file("url_player.ui", [
            "lineEdit", "searchButton", "treeWidget", "play_button", 
            "rew_button", "ff_button", "tabWidget", "listWidget",
            "del_button", "add_button", "textEdit", "servicios", "ajustes_avanzados"
        ])
        
        if not ui_file_loaded:
            self._fallback_init_ui()
        
        # Verificar widgets críticos
        if not self.check_required_widgets():
            self.log("Error: No se pudieron inicializar todos los widgets requeridos")
            return
        
        # Inicializar referencias a widgets después de cargar la UI
        self.initialize_playlist_ui_references()
        
        # Cargar configuración
        self.load_settings()
        
        # Configurar widgets críticos inmediatamente
        self._setup_critical_widgets()
        
        # Programar configuración de elementos no críticos para después
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._setup_non_critical_widgets)

    def _setup_critical_widgets(self):
        """Configura los widgets críticos que deben estar listos inmediatamente"""
        # Configurar nombres y tooltips básicos
        self.searchButton.setText("Buscar")
        self.searchButton.setToolTip("Buscar información sobre la URL")
        self.play_button.setIcon(QIcon(":/services/b_play"))
        self.play_button.setToolTip("Reproducir/Pausar")
        self.rew_button.setIcon(QIcon(":/services/b_prev"))
        self.rew_button.setToolTip("Anterior")
        self.ff_button.setIcon(QIcon(":/services/b_ff"))
        self.ff_button.setToolTip("Siguiente")
        self.del_button.setIcon(QIcon(":/services/b_minus_star"))
        self.del_button.setToolTip("Eliminar de la cola")
        self.add_button.setIcon(QIcon(":/services/addstar"))
        self.add_button.setToolTip("Añadir a la cola")
        
        # Configurar TabWidget básico
        self.tabWidget.setTabText(0, "Cola de reproducción")
        self.tabWidget.setTabText(1, "Información")
        
        # Conectar señales críticas
        self.connect_critical_signals()


    def _setup_non_critical_widgets(self):
        """Configura los widgets no críticos que pueden cargarse después"""
        try:
            # Configurar tree widget para mejor visualización
            if hasattr(self, 'treeWidget') and self.treeWidget:
                self.treeWidget.setHeaderLabels(["Título", "Artista", "Tipo", "Track/Año", "Duración"])
                self.treeWidget.setColumnWidth(0, 250)
                self.treeWidget.setColumnWidth(1, 100)
                self.treeWidget.setColumnWidth(2, 80)
                self.treeWidget.setColumnWidth(3, 70)
                self.treeWidget.setColumnWidth(4, 70)
                self.treeWidget.setIndentation(20)
                self.treeWidget.setSortingEnabled(True)
                from PyQt6.QtCore import Qt
                self.treeWidget.sortByColumn(0, Qt.SortOrder.AscendingOrder)
                self.treeWidget.setExpandsOnDoubleClick(False)
                self.treeWidget.itemClicked.connect(self.on_tree_item_clicked)
            
            # Configurar resto de widgets no críticos en una secuencia de timers
            from PyQt6.QtCore import QTimer
            
            # Usar una función para encadenar las configuraciones
            def setup_services():
                self.setup_services_combo()
                QTimer.singleShot(50, setup_tipo_combo)
            
            def setup_tipo_combo():
                # Configurar tipo_combo si existe
                if not hasattr(self, 'tipo_combo'):
                    from PyQt6.QtWidgets import QComboBox
                    self.tipo_combo = self.findChild(QComboBox, 'tipo_combo')
                if self.tipo_combo and self.tipo_combo.count() == 0:
                    self.tipo_combo.addItem("Todo")
                    self.tipo_combo.addItem("Artista")
                    self.tipo_combo.addItem("Álbum")
                    self.tipo_combo.addItem("Canción")
                QTimer.singleShot(50, setup_lastfm)
            
            def setup_lastfm():
                # Configurar Last.fm
                from modules.submodules.url_playlist.lastfm_manager import connect_lastfm_controls, setup_scrobbles_menu
                connect_lastfm_controls(self)
                setup_scrobbles_menu(self)
                QTimer.singleShot(50, setup_icons_and_menus)
                
            def setup_icons_and_menus():
                # Configurar iconos y menús
                from modules.submodules.url_playlist.ui_helpers import setup_service_icons, setup_loading_indicator, setup_context_menus
                setup_service_icons(self)
                setup_loading_indicator(self)
                setup_context_menus(self)
                QTimer.singleShot(50, setup_playlists)
                
            def setup_playlists():
                # Configurar el botón unificado de playlists
                from modules.submodules.url_playlist.ui_helpers import setup_action_unified_playlist
                setup_action_unified_playlist(self)
                
                # Aplicar la configuración de vista actual
                self.update_playlist_view()
                QTimer.singleShot(50, connect_signals)
                
            def connect_signals():
                # Conectar resto de señales
                self.connect_remaining_signals()
                self._check_and_run_auto_sync()
                self.log("Configuración diferida de widgets completada")
            
            # Iniciar la cadena de configuración
            QTimer.singleShot(10, setup_services)
        
        except Exception as e:
            self.log(f"Error en configuración diferida: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

    def connect_critical_signals(self):
        """Conecta solo las señales críticas para la funcionalidad básica"""
        # Botones principales
        if self.searchButton:
            self.searchButton.clicked.connect(self.perform_search)
        if self.play_button:
            from modules.submodules.url_playlist.media_utils import toggle_play_pause
            self.play_button.clicked.connect(lambda: toggle_play_pause(self))
        if self.rew_button:
            from modules.submodules.url_playlist.media_utils import previous_track
            self.rew_button.clicked.connect(lambda: previous_track(self))
        if self.ff_button:
            from modules.submodules.url_playlist.media_utils import next_track
            self.ff_button.clicked.connect(lambda: next_track(self))
        if self.add_button:
            from modules.submodules.url_playlist.media_utils import add_to_queue
            self.add_button.clicked.connect(lambda: add_to_queue(self))
        if self.del_button:
            from modules.submodules.url_playlist.media_utils import remove_from_queue
            self.del_button.clicked.connect(lambda: remove_from_queue(self))
        if self.lineEdit:
            self.lineEdit.returnPressed.connect(self.perform_search)
            print("LineEdit conectado para búsqueda con Enter")

    def connect_remaining_signals(self):
        """Conecta el resto de señales después de la inicialización crítica"""
        try:
            # Conectar eventos de doble clic para el árbol y la lista
            if self.treeWidget:
                try:
                    self.treeWidget.itemDoubleClicked.disconnect()
                except:
                    pass
                from modules.submodules.url_playlist.ui_helpers import on_tree_double_click
                self.treeWidget.itemDoubleClicked.connect(on_tree_double_click)
            
            if self.listWidget:
                try:
                    self.listWidget.itemDoubleClicked.disconnect()
                except:
                    pass
                from modules.submodules.url_playlist.ui_helpers import on_list_double_click
                self.listWidget.itemDoubleClicked.connect(on_list_double_click)
            
            if hasattr(self, 'ajustes_avanzados'):
                from modules.submodules.url_playlist.ui_helpers import show_advanced_settings
                self.ajustes_avanzados.clicked.connect(lambda: show_advanced_settings(self))

            # Conectar cambio de selección en el árbol
            if self.treeWidget:
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
            if hasattr(self, 'GuardarPlaylist_button'):
                try:
                    self.GuardarPlaylist_button.clicked.disconnect()
                except:
                    pass
                from modules.submodules.url_playlist.playlist_manager import on_guardar_playlist_clicked
                self.GuardarPlaylist_button.clicked.connect(lambda: on_guardar_playlist_clicked(self))
            
            if hasattr(self, 'VaciarPlaylist_button'):
                from modules.submodules.url_playlist.ui_helpers import clear_playlist
                self.VaciarPlaylist_button.clicked.connect(lambda: clear_playlist(self))
            
            # Connect signals for RSS playlist operations
            self.ask_mark_as_listened_signal.connect(lambda data: show_mark_as_listened_dialog(self, data))
            self.show_error_signal.connect(lambda msg: QMessageBox.critical(self, "Error", msg))

            if self.play_button:
                self.play_button.clicked.connect(self.toggle_play_pause)
            
            if self.rew_button:
                self.rew_button.clicked.connect(self.play_previous)
            
            if self.ff_button:
                self.ff_button.clicked.connect(self.play_next)

        except Exception as e:
            self.log(f"Error al conectar señales adicionales: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

    def _check_and_run_auto_sync(self):
        """Verifica si debe ejecutar sincronización automática al iniciar"""
        try:
            # Verificar si está habilitada la sincronización automática
            sync_at_boot = getattr(self, 'sync_at_boot', False)
            
            if not sync_at_boot:
                self.log("Sincronización automática al inicio deshabilitada")
                return
            
            # Verificar que tenemos las credenciales necesarias
            if not self.lastfm_api_key or not self.lastfm_username:
                self.log("No se puede sincronizar automáticamente: faltan credenciales de Last.fm")
                return
            
            self.log("Iniciando sincronización automática de Last.fm al arranque...")
            
            # Ejecutar sincronización en un hilo separado con un pequeño retraso
            # para asegurar que la UI esté completamente inicializada
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, self._run_auto_sync)  # 2 segundos de retraso
            
        except Exception as e:
            self.log(f"Error verificando sincronización automática: {str(e)}")


    def _run_auto_sync(self):
        """Ejecuta la sincronización automática de forma segura entre hilos"""
        try:
            # Usar la versión segura sin diálogos
            import threading
            sync_thread = threading.Thread(
                target=lambda: sync_lastfm_scrobbles_safe(self, show_dialogs=False),
                name="SafeAutoSyncLastFM",
                daemon=True
            )
            sync_thread.start()
            
            self.log("Sincronización automática de Last.fm iniciada de forma segura")
            
        except Exception as e:
            self.log(f"Error ejecutando sincronización automática: {str(e)}")

    def _execute_sync_in_main_thread(self):
        """Ejecuta la sincronización en el hilo principal"""
        try:
            from modules.submodules.url_playlist.lastfm_manager import sync_lastfm_scrobbles
            
            # Ahora que estamos en el hilo principal, podemos crear un nuevo hilo para la tarea larga
            # pero evitando diálogos para no causar problemas de hilos
            import threading
            sync_thread = threading.Thread(
                target=lambda: sync_lastfm_scrobbles(self, show_dialogs=False),
                name="AutoSyncLastFM",
                daemon=True
            )
            sync_thread.start()
            
        except Exception as e:
            self.log(f"Error ejecutando sincronización en hilo principal: {str(e)}")


    def _safe_sync_lastfm(self):
        """Versión segura de sincronización que evita manipular UI directamente"""
        try:
            from modules.submodules.url_playlist.lastfm_manager import sync_lastfm_scrobbles
            
            # Usar una variable de instancia para indicar que estamos sincronizando
            self._is_syncing_lastfm = True
            
            # Ejecutar sincronización sin diálogos de progreso (evita manipulación de UI)
            # Modifica la función sync_lastfm_scrobbles para tener un parámetro show_dialogs=True
            result = sync_lastfm_scrobbles(self, show_dialogs=False)
            
            # Limpiar la marca de sincronización
            self._is_syncing_lastfm = False
            
            # Notificar resultado en el hilo principal
            from PyQt6.QtCore import QTimer, QCoreApplication
            QTimer.singleShot(0, lambda: self._notify_sync_result(result))
            
        except Exception as e:
            self.log(f"Error en sincronización segura: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            
            # Limpiar la marca de sincronización
            self._is_syncing_lastfm = False
            
            # Notificar error en el hilo principal
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._notify_sync_error(str(e)))

    def _notify_sync_result(self, success):
        """Notifica el resultado de la sincronización en el hilo principal"""
        from PyQt6.QtWidgets import QMessageBox
        if success:
            self.log("Sincronización automática completada exitosamente")
            # Opcional: mostrar mensaje de éxito
            # QMessageBox.information(self, "Sincronización Completa", "Sincronización de Last.fm completada exitosamente")
        else:
            self.log("Sincronización automática no completada correctamente")
            # Opcional: mostrar mensaje de error
            # QMessageBox.warning(self, "Sincronización Incompleta", "La sincronización de Last.fm no se completó correctamente")

    def _notify_sync_error(self, error_msg):
        """Notifica un error de sincronización en el hilo principal"""
        self.log(f"Error en sincronización automática: {error_msg}")
        # Opcional: mostrar mensaje de error
        # from PyQt6.QtWidgets import QMessageBox
        # QMessageBox.critical(self, "Error de Sincronización", f"Error en sincronización de Last.fm: {error_msg}")



    def _initialize_player_manager(self):
        """Inicializa y configura el reproductor según la configuración"""
        from tools.player_manager import PlayerManager
        
        # Obtener la configuración de player desde el config
        player_config = {}
        if hasattr(self, 'config') and 'music_players' in self.config:
            player_config = self.config['music_players']
        
        # Crear el PlayerManager con la configuración
        self.player_manager = PlayerManager(config=player_config, parent=self, logger=self.log)
        
        # Conectar las señales
        self._connect_player_signals()
        
        self.log(f"Player Manager inicializado: {self.player_manager.current_player.get('player_name', 'desconocido')}")   

    def log(self, message):
        """Método seguro para registrar mensajes en el TextEdit y en la consola."""
        # Siempre imprimir en la consola
        print(f"[UrlPlayer] {message}")
        
        # Intentar añadir al TextEdit si está disponible
        if hasattr(self, 'textEdit') and self.textEdit:
            try:
                # Simplemente usar append que maneja el cursor internamente
                self.textEdit.append(str(message))
            except Exception as e:
                print(f"[UrlPlayer] Error escribiendo en textEdit: {e}")

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
        self.rew_button = QPushButton("⏮️")
        self.ff_button = QPushButton("⏭️")
        self.play_button = QPushButton("▶️")
        player_buttons_layout.addWidget(self.rew_button)
        player_buttons_layout.addWidget(self.ff_button)
        player_buttons_layout.addWidget(self.play_button)
        
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
        self.add_button = QPushButton("➕")
        self.del_button = QPushButton("➖")
        playlist_buttons_layout.addWidget(self.add_button)
        playlist_buttons_layout.addWidget(self.del_button)
        
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
            "lineEdit", "searchButton", "treeWidget", "play_button", 
            "ff_button", "rew_button", "tabWidget", "listWidget",
            "add_button", "del_button", "textEdit", "servicios", "ajustes_avanzados"
        ]
        
        all_ok = True
        for widget_name in required_widgets:
            if not hasattr(self, widget_name) or getattr(self, widget_name) is None:
                print(f"[UrlPlayer] Error: Widget {widget_name} no encontrado")
                all_ok = False
        
        return all_ok



    def perform_search(self):
        """Versión optimizada del buscador con manejo seguro de hilos QThread"""
        query = self.lineEdit.text().strip()
        if not query:
            return
        
        # Verificar si estamos buscando específicamente en Spotify
        if hasattr(self, 'servicios') and self.servicios.currentText() == "Spotify" and hasattr(self, 'search_spotify_content'):
            # Usar la búsqueda específica de Spotify
            self.search_spotify_content(query)
            return
        
        # Resto del código original de perform_search para otras búsquedas...
        # Cancelar búsqueda anterior si está en progreso
        if hasattr(self, '_current_search_thread') and self._current_search_thread is not None:
            if isinstance(self._current_search_thread, QThread) and self._current_search_thread.isRunning():
                self.log("Cancelando búsqueda anterior en QThread")
                # Indicar a los trabajadores que deben cancelarse
                if hasattr(self, '_search_worker') and hasattr(self._search_worker, 'stop'):
                    self._search_worker.stop()
                # Esperar a que termine
                self._current_search_thread.quit()
                self._current_search_thread.wait(500)  # Esperar máximo 500ms
        
        # Verificar límite de tiempo entre búsquedas
        if hasattr(self, '_last_search_time'):
            import time
            if time.time() - self._last_search_time < 0.5:  # Mínimo 0.5 segundos entre búsquedas
                self.log("Búsqueda demasiado frecuente, ignorando")
                return
        
        # Registrar tiempo de búsqueda
        import time
        self._last_search_time = time.time()
        
        # Mostrar indicador de búsqueda
        if hasattr(self, 'show_loading_indicator'):
            self.show_loading_indicator(True)
        self.searchButton.setEnabled(False)
        
        # Obtener el estado de only_local
        only_local = getattr(self, 'urlplaylist_only_local', False)
        
        # Crear QThread y worker para la búsqueda
        from PyQt6.QtCore import QThread
        from modules.submodules.url_playlist.search_workers import SearchWorker
        
        # Crear un nuevo QThread
        self._current_search_thread = QThread()
        
        # Crear el worker y moverlo al hilo
        self._search_worker = SearchWorker(self, query, only_local)
        self._search_worker.moveToThread(self._current_search_thread)
        
        # Conectar señales
        self._current_search_thread.started.connect(self._search_worker.run)
        self._search_worker.finished.connect(self._current_search_thread.quit)
        self._search_worker.finished.connect(self._search_worker.deleteLater)
        self._current_search_thread.finished.connect(self._current_search_thread.deleteLater)
        self._current_search_thread.finished.connect(self._search_finished)
        
        # Conectar señales de resultados
        self._search_worker.db_results_ready.connect(self._show_db_results_safe)
        self._search_worker.error.connect(lambda e: self.log(f"Error en búsqueda: {e}"))
        
        # Iniciar el hilo
        self._current_search_thread.start()

    def _perform_search_async(self, query, only_local):
        """Realiza la búsqueda en un hilo separado con mejor gestión de memoria."""
        try:
            # Verificar cancelación
            if hasattr(self, '_cancel_search') and self._cancel_search:
                self.log("Búsqueda cancelada")
                # Actualizar UI en el hilo principal
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self._search_finished)
                return
            
            # Primero buscar en la base de datos para resultados rápidos
            from modules.submodules.url_playlist.db_manager import search_database_links
            db_links = search_database_links(self, self.db_path, query, "all")
            
            if db_links:
                # Procesar resultados de forma segura
                results = None
                try:
                    # Usar nuestra nueva función de procesamiento
                    results = self._process_database_results(db_links)
                    
                    # Enviar resultados al hilo principal para mostrar
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self._show_db_results_safe(results))
                    
                    # Liberar memoria
                    del results
                    
                except Exception as proc_error:
                    self.log(f"Error al procesar resultados de base de datos: {proc_error}")
                    import traceback
                    self.log(traceback.format_exc())
            
            # Si no se cancela, continuar con la búsqueda externa
            if not hasattr(self, '_cancel_search') or not self._cancel_search:
                # Usar un enfoque más seguro que minimice la memoria
                try:
                    from modules.submodules.url_playlist.db_manager import perform_search_with_service_filter
                    perform_search_with_service_filter(self, query, only_local)
                except Exception as search_error:
                    self.log(f"Error en búsqueda externa: {search_error}")
                    import traceback
                    self.log(traceback.format_exc())
                
            # Forzar liberación de memoria
            import gc
            gc.collect()
                    
        except Exception as e:
            self.log(f"Error en búsqueda: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            # Actualizar UI en el hilo principal
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._search_finished)

    def _show_db_results_safe(self, results):
        """Muestra los resultados de la base de datos de forma segura con manejo de memoria"""
        try:
            if not results:
                return
                    
            self.log(f"Mostrando resultados preliminares de la base de datos ({len(results)} elementos)")
            
            # Limitar resultados para evitar sobrecarga
            if len(results) > 100:
                results = results[:100]
                self.log("Limitando a 100 resultados para evitar sobrecarga")
            
            # Borrar resultados antiguos
            self.treeWidget.clear()
            
            # Mostrar resultados iniciales en bloques para evitar congelamiento
            from PyQt6.QtCore import QTimer
            
            # Dividir en bloques de 20 para procesar
            chunk_size = 20
            for i in range(0, len(results), chunk_size):
                chunk = results[i:i+chunk_size]
                # Usar un timer para permitir que la UI respire
                QTimer.singleShot(i * 10, lambda c=chunk: self._show_result_chunk(c))
            
        except Exception as e:
            self.log(f"Error mostrando resultados preliminares: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

    def _show_result_chunk(self, results_chunk):
        """Muestra un subconjunto de resultados para evitar bloquear la UI"""
        try:
            from modules.submodules.url_playlist.ui_helpers import display_search_results
            display_search_results(self, results_chunk, False)  # False para no borrar resultados existentes
        except Exception as e:
            self.log(f"Error mostrando bloque de resultados: {str(e)}")


    def _show_db_results(self, db_links):
        """Mostrar resultados de la base de datos mientras se continúa la búsqueda externa"""
        try:
            if not db_links:
                return
                    
            self.log(f"Mostrando resultados preliminares de la base de datos")
            
            # Procesar y mostrar los resultados
            from modules.submodules.url_playlist.db_manager import _process_database_results
            db_results = _process_database_results(self, db_links)
            
            if db_results:
                # Borrar resultados antiguos solo si encontramos nuevos
                self.treeWidget.clear()
                
                # Mostrar resultados iniciales
                from modules.submodules.url_playlist.ui_helpers import display_search_results
                display_search_results(self, db_results, True)
                
                # Actualizar la UI para mostrar los resultados
                QApplication.processEvents()
                    
        except Exception as e:
            self.log(f"Error mostrando resultados preliminares: {str(e)}")

    def _search_finished(self):
        """Actualiza la UI después de terminar la búsqueda con limpieza de memoria"""
        if hasattr(self, 'show_loading_indicator'):
            self.show_loading_indicator(False)
        if hasattr(self, 'searchButton'):
            self.searchButton.setEnabled(True)
        
        # Realizar limpieza explícita de memoria
        if hasattr(self, '_search_worker'):
            self._search_worker = None
        if hasattr(self, '_current_search_thread'):
            self._current_search_thread = None
        
        # Forzar recolección de basura
        import gc
        gc.collect()
        
        self.log("Búsqueda finalizada y memoria liberada")


    def connect_signals(self):
        """Conecta las señales de los widgets a sus respectivos slots."""
        try:
            # Conectar señales con verificación previa
            if self.searchButton:
                self.searchButton.clicked.connect(self.perform_search)
                    
            if self.play_button:
                self.play_button.clicked.connect(lambda: toggle_play_pause(self))            
            if self.rew_button:
                self.rew_button.clicked.connect(lambda: previous_track(self))
            
            if self.ff_button:
                self.ff_button.clicked.connect(lambda: next_track(self))
            
            if self.add_button:
                self.add_button.clicked.connect(lambda: add_to_queue(self))
            
            if self.del_button:
                self.del_button.clicked.connect(lambda: remove_from_queue(self))            

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
            if hasattr(self, 'GuardarPlaylist_button'):
                try:
                    self.GuardarPlaylist_button.clicked.disconnect()
                except TypeError:
                    pass
                from modules.submodules.url_playlist.playlist_manager import on_guardar_playlist_clicked
                self.GuardarPlaylist_button.clicked.connect(lambda: on_guardar_playlist_clicked(self))
            
            if hasattr(self, 'VaciarPlaylist_button'):
                from modules.submodules.url_playlist.ui_helpers import clear_playlist
                self.VaciarPlaylist_button.clicked.connect(lambda: clear_playlist(self))
            
            # Connect signals for RSS playlist operations
            self.ask_mark_as_listened_signal.connect(lambda data: show_mark_as_listened_dialog(self, data))
            self.show_error_signal.connect(lambda msg: QMessageBox.critical(self, "Error", msg))

            # Setup context menus
            from modules.submodules.url_playlist.ui_helpers import setup_context_menus
            setup_context_menus(self)

            # Update RSS playlists automatically at startup
            from modules.submodules.url_playlist.playlist_manager import load_rss_playlists
            load_rss_playlists(self)
            
            from modules.submodules.url_playlist.rss_manager import setup_rss_controls
            # Asegúrese de que todos los atributos necesarios estén disponibles en el módulo rss_manager
            setup_rss_controls(self)

            if self.play_button:
                self.play_button.clicked.connect(self.toggle_play_pause)
            
            if self.rew_button:
                self.rew_button.clicked.connect(self.play_previous)
            
            if self.ff_button:
                self.ff_button.clicked.connect(self.play_next)



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
        query = self.lineEdit.text().strip()
        if query:
            if service == "Spotify" and hasattr(self, 'search_spotify_content'):
                # Usar la búsqueda específica de Spotify
                self.search_spotify_content(query)
            else:
                # Usar la búsqueda general para otros servicios
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
            self.action_unified_playlist = self.findChild(QPushButton, 'action_unified_playlist')
            if not self.action_unified_playlist:
                self.log("Error: No se pudo encontrar el botón 'action_unified_playlist'")
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


    def save_settings(self):
        """Guarda la configuración del módulo en el archivo de configuración general."""
        try:
            # Try multiple config paths
            config_paths = [
                Path(PROJECT_ROOT, "config", "config.yml"),
                Path(PROJECT_ROOT, "config", "config_placeholder.yaml"),
                Path(PROJECT_ROOT, ".content", "config", "config.yml")
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

            # Helper function to convert Path objects to relative strings
            def path_to_relative_string(path_value):
                """Convert Path objects or absolute paths to relative strings"""
                if path_value is None:
                    return ''
                
                # Convert to string first
                path_str = str(path_value)
                
                # If it's an absolute path, try to make it relative to PROJECT_ROOT
                if os.path.isabs(path_str):
                    try:
                        rel_path = os.path.relpath(path_str, PROJECT_ROOT)
                        # Only use relative path if it doesn't go up directories
                        if not rel_path.startswith('..'):
                            return rel_path
                        else:
                            return path_str
                    except ValueError:
                        return path_str
                
                return path_str

            # Add Last.fm specific settings
            lastfm_settings = {
                'lastfm_username': getattr(self, 'lastfm_username', ''),
                'scrobbles_limit': getattr(self, 'scrobbles_limit', 50),
                'scrobbles_by_date': getattr(self, 'scrobbles_by_date', True),
                'service_priority_indices': getattr(self, 'service_priority_indices', [0, 1, 2, 3])
            }

            # Asegurar que pagination_value esté sincronizado con num_servicios_spinBox
            self.pagination_value = getattr(self, 'num_servicios_spinBox', 10)
            
            # Store current database path - convert to relative string
            db_path_to_save = path_to_relative_string(getattr(self, 'db_path', ''))
            
            # Convert all paths to simple relative strings
            spotify_token_path = path_to_relative_string(getattr(self, 'spotify_token_path', '.content/cache/spotify_token.txt'))
            spotify_playlist_path = path_to_relative_string(getattr(self, 'spotify_playlist_path', '.content/cache/spotify_playlist_path'))
            lastfm_cache_path = path_to_relative_string(getattr(self, 'lastfm_cache_path', '.content/cache/lastfm_cache.json'))
            rss_pending_dir = path_to_relative_string(getattr(self, 'rss_pending_dir', '.content/playlists/blogs/pendiente'))
            rss_listened_dir = path_to_relative_string(getattr(self, 'rss_listened_dir', '.content/playlists/blogs/escuchado'))
            local_playlist_path = path_to_relative_string(getattr(self, 'local_playlist_path', '.content/playlists/locales'))
            mpv_temp_dir = path_to_relative_string(getattr(self, 'mpv_temp_dir', '.content/mpv/_mpv_socket'))
            
            # Preparar configuración de este módulo - TODAS LAS RUTAS COMO STRINGS SIMPLES
            new_settings = {
                'mpv_temp_dir': mpv_temp_dir,
                'pagination_value': self.pagination_value,
                'included_services': getattr(self, 'included_services', {}),
                'db_path': db_path_to_save,
                'spotify_client_id': getattr(self, 'spotify_client_id', ''),
                'spotify_client_secret': getattr(self, 'spotify_client_secret', ''),
                'lastfm_api_key': getattr(self, 'lastfm_api_key', ''),
                'lastfm_username': getattr(self, 'lastfm_username', ''),
                
                # Configuración de vista de playlists
                'playlist_unified_view': getattr(self, 'playlist_unified_view', False),
                'show_local_playlists': getattr(self, 'show_local_playlists', True),
                'show_spotify_playlists': getattr(self, 'show_spotify_playlists', True),
                'show_rss_playlists': getattr(self, 'show_rss_playlists', True),
                
                # Añadir configuración de urlplaylist_only_local
                'urlplaylist_only_local': getattr(self, 'urlplaylist_only_local', False),
                
                # Añadir configuración de sincronización automática
                'sync_at_boot': getattr(self, 'sync_at_boot', False),
                
                # lastfm specific settings
                'scrobbles_limit': lastfm_settings['scrobbles_limit'],
                'scrobbles_by_date': lastfm_settings['scrobbles_by_date'],
                'service_priority_indices': lastfm_settings['service_priority_indices'],
                
                # freshrss
                'freshrss_url': getattr(self, 'freshrss_url', ''),
                'freshrss_user': getattr(self, 'freshrss_username', ''),
                'freshrss_api_key': getattr(self, 'freshrss_auth_token', ''),
                
                # Paths as simple strings - NO MORE Path objects
                'spotify_token_path': spotify_token_path,
                'spotify_playlist_path': spotify_playlist_path,
                'lastfm_cache_path': lastfm_cache_path,
                'rss_pending_dir': rss_pending_dir,
                'rss_listened_dir': rss_listened_dir,
                'local_playlist_path': local_playlist_path,
                
                # Additional settings
                'exclude_spotify_from_local': getattr(self, 'exclude_spotify_from_local', True),
                'show_lastfm_scrobbles': getattr(self, 'show_lastfm_scrobbles', True)
            }
            
            # Añadir valores de depuración
            self.log(f"Guardando configuración - Vista unificada: {new_settings['playlist_unified_view']}")
            self.log(f"Guardando configuración - Only local: {new_settings['urlplaylist_only_local']}")
            self.log(f"Guardando configuración - Sync at boot: {new_settings['sync_at_boot']}")
            self.log(f"Guardando configuración - Paths convertidas a strings simples")
            
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
                    self.log(f"Updated existing module: {module.get('name')}")
                    break
            
            # Si no se encontró en los módulos activos, buscar en los desactivados
            if not module_updated:
                for module in config_data.get('modulos_desactivados', []):
                    if module.get('name') in module_names:
                        # Reemplazar completamente los argumentos para evitar duplicados
                        module['args'] = new_settings
                        module_updated = True
                        self.log(f"Updated existing disabled module: {module.get('name')}")
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
                    'path': 'modules/url_playlist.py',
                    'args': new_settings
                })
            
            # Guardar la configuración actualizada con configuración específica de YAML
            try:
                # Try to use save function from main module
                try:
                    from main import save_config_file
                    save_config_file(config_path, config_data)
                except ImportError:
                    # Fallback method with specific YAML configuration
                    extension = os.path.splitext(config_path)[1].lower()
                    if extension in ['.yml', '.yaml']:
                        import yaml
                        # Configure YAML to avoid complex object serialization
                        with open(config_path, 'w', encoding='utf-8') as f:
                            yaml.dump(
                                config_data, 
                                f, 
                                sort_keys=False, 
                                default_flow_style=False, 
                                indent=2,
                                allow_unicode=True,
                                width=1000  # Avoid line wrapping
                            )
                    else:  # Assume JSON
                        import json
                        with open(config_path, 'w', encoding='utf-8') as f:
                            json.dump(config_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                self.log(f"Error saving config: {e}")
                return
                
            self.log(f"Configuración guardada correctamente en {config_path}")
        except Exception as e:
            self.log(f"Error al guardar configuración: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

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
                        
                        # Load scrobbles-related settings
                        self.scrobbles_limit = module_args.get('scrobbles_limit', 50)  # Default to 50
                        self.scrobbles_by_date = module_args.get('scrobbles_by_date', True)  # Default to True
                        
                        # Set Last.fm username
                        self.lastfm_username = module_args.get('lastfm_username', '')
                        
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
        
        self.sync_at_boot = False

        # Create necessary directories
        os.makedirs(os.path.dirname(self.spotify_token_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.spotify_playlist_path), exist_ok=True)


    def get_app_path(self, file_path):
        """Create standardized paths relative to PROJECT_ROOT"""
        return Path(PROJECT_ROOT, file_path)



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
            if not hasattr(self, 'action_unified_playlist'):
                self.log("Error: QPushButton 'action_unified_playlist' no encontrado")
                return False
            
            # Make sure the button is visible first (this is critical)
            self.action_unified_playlist.setVisible(True)
                
            # Configurar el botón unificado si aún no tiene menú
            if not self.action_unified_playlist.menu():
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
            Path(PROJECT_ROOT, "config", "api_keys.json"),
            Path(PROJECT_ROOT, ".content", "config", "api_keys.json"),
            Path(os.path.expanduser("~"), ".config", "music_app", "api_keys.json")
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
        
        if self.lastfm_username and isinstance(self.lastfm_username, str) and self.lastfm_username.strip():
            os.environ["LASTFM_USERNAME"] = self.lastfm_username.strip()
            print(f"[UrlPlayer] Set LASTFM_USERNAME in environment")
            
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
            if 'lastfm_username' in module_args:
                self.lastfm_username = module_args['lastfm_username']
            
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
                    local_playlist_path = Path(PROJECT_ROOT, local_playlist_path)
                self.local_playlist_path = local_playlist_path
                self.log(f"Ruta de playlists locales cargada: {self.local_playlist_path}")
            else:
                # Ruta por defecto
                self.local_playlist_path = Path(PROJECT_ROOT, ".content", "playlists", "locales")
                self.log(f"Usando ruta de playlists locales por defecto: {self.local_playlist_path}")


            if 'sync_at_boot' in module_args:
                value = module_args['sync_at_boot']
                if isinstance(value, str):
                    self.sync_at_boot = value.lower() == 'true'
                else:
                    self.sync_at_boot = bool(value)
                self.log(f"Loaded sync_at_boot: {self.sync_at_boot}")
            else:
                self.sync_at_boot = False


            # Load MPV temp directory
            if 'mpv_temp_dir' in module_args:
                mpv_temp_dir = module_args['mpv_temp_dir']
                # Handle relative path
                if not os.path.isabs(mpv_temp_dir):
                    mpv_temp_dir = Path(os.path.expanduser("~"), mpv_temp_dir)
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
                    lastfm_username = user_input.text().strip()
                    if lastfm_username:
                        self.lastfm_username = lastfm_username
                        self.log(f"Set Last.fm user to: {self.lastfm_username}")
            
            # Scrobbles limit
            if hasattr(dialog, 'scrobbles_slider') and hasattr(dialog, 'scrobblers_spinBox'):
                # Prefer spinbox value over slider for precision
                scrobbles_limit = dialog.scrobblers_spinBox.value()
                
                # Optional: Sync slider with spinbox value if needed
                dialog.scrobbles_slider.setValue(scrobbles_limit)
                
                self.scrobbles_limit = scrobbles_limit
                self.log(f"Set scrobbles limit to: {self.scrobbles_limit}")
            
            # Display mode
            if hasattr(dialog, 'scrobbles_fecha') and hasattr(dialog, 'scrobbles_reproducciones'):
                self.scrobbles_by_date = dialog.scrobbles_fecha.isChecked()
                self.log(f"Set scrobbles display mode: by_date={self.scrobbles_by_date}")
            

            # Last.fm username - ahora usando QLineEdit
            lastfm_username_input = dialog.findChild(QLineEdit, 'entrada_usuario')
            if lastfm_username_input:
                lastfm_username = lastfm_username_input.text().strip()
                if lastfm_username:
                    self.lastfm_username = lastfm_username
                    self.log(f"Set Last.fm user to: {self.lastfm_username}")
            
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


           
            sync_at_boot_checkbox = dialog.findChild(QCheckBox, 'sync_at_boot')
            if sync_at_boot_checkbox:
                self.sync_at_boot = sync_at_boot_checkbox.isChecked()
                self.log(f"Set sync_at_boot to: {self.sync_at_boot}")
            else:
                self.log("sync_at_boot checkbox not found in dialog")

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


    def setup_advanced_settings_dialog(self, dialog):
        """Set up advanced settings dialog with synchronized controls"""
        try:
            # Find scrobbles slider and spinbox
            scrobbles_slider = dialog.findChild(QSlider, 'scrobbles_slider')
            scrobblers_spinBox = dialog.findChild(QSpinBox, 'scrobblers_spinBox')
            
            if scrobbles_slider and scrobblers_spinBox:
                # Set ranges to match
                scrobbles_slider.setRange(10, 5000)  # Reasonable range for scrobbles
                scrobblers_spinBox.setRange(10, 5000)
                
                # Set initial values from object's settings
                current_limit = getattr(self, 'scrobbles_limit', 50)
                scrobbles_slider.setValue(current_limit)
                scrobblers_spinBox.setValue(current_limit)
                
                # Connect slider and spinbox for synchronization
                def sync_slider_spinbox():
                    scrobblers_spinBox.setValue(scrobbles_slider.value())
                
                def sync_spinbox_slider():
                    scrobbles_slider.setValue(scrobblers_spinBox.value())
                
                scrobbles_slider.valueChanged.connect(sync_slider_spinbox)
                scrobblers_spinBox.valueChanged.connect(sync_spinbox_slider)
                
                self.log(f"Synchronized scrobbles limit controls with value: {current_limit}")
        except Exception as e:
            self.log(f"Error setting up scrobbles controls: {str(e)}")


        # Preparar configuración de este módulo
            new_settings = {
                'mpv_temp_dir': mpv_socket,
                'pagination_value': self.pagination_value,
                'included_services': self.included_services,
                'db_path': db_path_to_save,
                'spotify_client_id': self.spotify_client_id,
                'spotify_client_secret': self.spotify_client_secret,
                'lastfm_api_key': self.lastfm_api_key,
                'lastfm_username': self.lastfm_username,
                
                # Configuración de vista de playlists
                'playlist_unified_view': getattr(self, 'playlist_unified_view', False),
                'show_local_playlists': getattr(self, 'show_local_playlists', True),
                'show_spotify_playlists': getattr(self, 'show_spotify_playlists', True),
                'show_rss_playlists': getattr(self, 'show_rss_playlists', True),
                
                # Añadir configuración de urlplaylist_only_local
                'urlplaylist_only_local': getattr(self, 'urlplaylist_only_local', False),
                
                # NUEVA LÍNEA: Añadir configuración de sincronización automática
                'sync_at_boot': getattr(self, 'sync_at_boot', False),
                
                # lastfm
                'lastfm_username': lastfm_settings['lastfm_username'],
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
            self.log(f"Guardando configuración - Sync at boot: {new_settings['sync_at_boot']}")
            
            
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
        self.play_button.setIcon(QIcon(":/services/b_pause"))
        self.log("Playback started")
        self.highlight_current_track()

    def on_playback_stopped(self):
        """Handle player stopping playback"""
        self.is_playing = False
        self.play_button.setIcon(QIcon(":/services/b_play"))
        self.log("Playback stopped")

    def on_playback_paused(self):
        """Handle player pausing playback"""
        self.is_playing = False
        self.play_button.setIcon(QIcon(":/services/b_play"))
        self.log("Playback paused")

    def on_playback_resumed(self):
        """Handle player resuming playback"""
        self.is_playing = True
        self.play_button.setIcon(QIcon(":/services/b_pause"))
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
                self.play_button.setIcon(QIcon(":/services/b_play"))
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
        from modules.submodules.url_playlist.media_utils import play_from_index, add_to_queue
        if not hasattr(self, 'current_playlist') or not self.current_playlist:
            # Nothing in playlist, try to add the selected item
            add_to_queue(self)
            if not self.current_playlist:
                self.log("Nothing to play")
                return
        
        if not self.is_playing:
            # If we have a current track, play/resume it
            if self.current_track_index >= 0 and self.current_track_index < len(self.current_playlist):
                if self.player_manager.is_playing:
                    self.player_manager.resume()
                else:
                    play_from_index(self, self.current_track_index)
            else:
                # Start from the beginning
                play_from_index(self, 0)
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

# INTERACCION DESDE MUSIC FUZZY
    def add_songs_to_queue(self, songs):
        """
        Add songs from other modules to the queue
        
        Args:
            songs: List of song dictionaries with at least 'file_path', 'title', and 'artist'
            
        Returns:
            bool: True if songs were added successfully
        """
        if not songs:
            self.log("No songs provided to add_songs_to_queue")
            return False
            
        self.log(f"Received {len(songs)} songs to add to the queue")
        num_added = 0
        
        for song in songs:
            # Debug info
            self.log(f"Processing song: {song.get('title', 'Unknown')}")
            
            # Verify we have a file_path
            file_path = song.get('file_path')
            if not file_path:
                self.log(f"No file_path for song {song.get('title', 'Unknown')} - trying alternate fields")
                
                # Try other possible field names
                for field in ['path', 'url', 'filepath']:
                    if field in song and song[field]:
                        file_path = song[field]
                        self.log(f"Found alternate path in {field}: {file_path}")
                        break
            
            if not file_path:
                self.log(f"Skipping song with no valid path: {song.get('title', 'Unknown')}")
                continue
                
            # Verify file exists
            import os
            if not os.path.exists(file_path):
                self.log(f"Skipping song - file does not exist: {file_path}")
                continue
            
            # Get song details - handle different dictionary structures
            title = song.get('title')
            if not title:
                title = song.get('name', os.path.basename(file_path))
                
            artist = song.get('artist')
            if not artist:
                artist = song.get('artist_name', 'Unknown Artist')
            
            # Create the display text
            display_text = f"{artist} - {title}" if artist else title
            
            # Add to the listWidget
            from PyQt6.QtWidgets import QListWidgetItem
            from PyQt6.QtCore import Qt
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            
            # Set icon based on source
            if hasattr(self, 'get_source_icon'):
                icon = self.get_source_icon(file_path, {'source': 'local'})
                item.setIcon(icon)
            elif hasattr(self, 'service_icons') and 'local' in self.service_icons:
                item.setIcon(self.service_icons['local'])
            
            # Add to listWidget
            self.listWidget.addItem(item)
            
            # Add to internal playlist
            if not hasattr(self, 'current_playlist'):
                self.current_playlist = []
                
            self.current_playlist.append({
                'title': title,
                'artist': artist,
                'url': file_path,
                'file_path': file_path,
                'source': 'local',
                'type': 'track'
            })
            
            num_added += 1
        
        # Log the result
        if num_added > 0:
            self.log(f"Added {num_added} songs to queue from music browser")
            return True
        else:
            self.log("No valid songs to add to queue")
            return False


# INTERACCION MUSIC FUZZY SPOTIFY

    def add_spotify_songs_to_queue(self, songs):
        """
        Add songs with Spotify URLs from another module to the queue
        
        Args:
            songs: List of song dictionaries with Spotify URLs
        """
        if not songs:
            self.log("No songs received to add to queue")
            return False
        
        self.log(f"Received {len(songs)} songs with Spotify URLs to add to queue")
        songs_added = 0
        
        for song in songs:
            # Create a tree item for the song
            from PyQt6.QtWidgets import QTreeWidgetItem
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QIcon
            
            item = QTreeWidgetItem()
            item.setText(0, song.get('title', 'Unknown Track'))
            item.setText(1, song.get('artist', ''))
            item.setText(2, "Canción")
            
            if 'track_number' in song:
                item.setText(3, str(song['track_number']))
                
            if 'duration' in song:
                from modules.submodules.url_playlist.ui_helpers import format_duration
                duration_str = format_duration(song['duration'])
                item.setText(4, duration_str)
            
            # Set Spotify icon
            if hasattr(self, 'service_icons') and 'spotify' in self.service_icons:
                item.setIcon(0, self.service_icons['spotify'])
            
            # Store data
            item_data = {
                'title': song.get('title', 'Unknown Track'),
                'artist': song.get('artist', ''),
                'url': song.get('spotify_url', song.get('url', '')),  # This is the Spotify URL
                'source': 'spotify',
                'type': 'track',
                'spotify_url': song.get('spotify_url', song.get('url', ''))  # Duplicate to ensure it's accessible
            }
            
            item.setData(0, Qt.ItemDataRole.UserRole, item_data)
            
            # Add to treeWidget temporarily
            self.treeWidget.addTopLevelItem(item)
            
            # Add to queue using the existing method
            from modules.submodules.url_playlist.media_utils import add_item_to_queue
            result = add_item_to_queue(self, item)
            
            if result:
                songs_added += 1
            
            # Remove from treeWidget (now it's in the queue)
            self.treeWidget.takeTopLevelItem(self.treeWidget.indexOfTopLevelItem(item))
        
        if songs_added > 0:
            self.log(f"Added {songs_added} Spotify songs to queue")
            return True
        else:
            self.log("No songs could be added to queue")
            return False


# CLEAN MEMEORY

    def clear_search_cache(self):
        """Clear search cache to free memory"""
        if hasattr(self, '_db_query_cache'):
            self._db_query_cache.clear()
            
        # Clear any other caches
        if hasattr(self, 'path_cache'):
            self.path_cache.clear()
            
        if hasattr(self, '_info_cache'):
            self._info_cache.clear()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        self.log("Search cache cleared")

    def perform_memory_cleanup(self):
        """Perform memory cleanup periodically"""
        # Clear any caches that are too large
        if hasattr(self, '_db_query_cache') and len(self._db_query_cache) > 20:
            # Keep the 10 most recent items only
            items = list(self._db_query_cache.items())
            items.sort(key=lambda x: x[1].get('_cache_time', 0), reverse=True)
            
            # Create new cache with recent items
            new_cache = {}
            for i, (key, value) in enumerate(items):
                if i < 10:
                    new_cache[key] = value
                    
            self._db_query_cache = new_cache
            
        # Force garbage collection
        import gc
        gc.collect()




# Spotify busqueda individual

    def search_spotify_content(self, query):
        """
        Realizar búsqueda en Spotify y mostrar resultados jerárquicamente
        """
        if not hasattr(self, 'sp') or not self.sp:
            self.log("Spotify no está inicializado. Intenta autenticarte primero.")
            return False
        
        self.log(f"Buscando en Spotify: {query}")
        
        try:
            # Mostrar indicador de búsqueda - CORREGIDO
            if hasattr(self, 'show_loading_indicator'):
                self.show_loading_indicator(True)
            else:
                from modules.submodules.url_playlist.ui_helpers import show_loading_indicator
                show_loading_indicator(self, True)
            
            # Realizar búsqueda de artistas
            results = self.sp.search(q=query, type='artist', limit=5)
            artists = results['artists']['items']
            
            if not artists:
                self.log(f"No se encontraron artistas para '{query}' en Spotify")
                # Intentar búsqueda de álbumes y canciones
                self.search_spotify_albums_tracks(query)
                return True
            
            # Limpiar resultados anteriores
            self.treeWidget.clear()
            
            # Crear nodo raíz para Spotify
            from PyQt6.QtWidgets import QTreeWidgetItem
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QIcon
            
            spotify_root = QTreeWidgetItem(self.treeWidget)
            spotify_root.setText(0, "Spotify")
            spotify_root.setIcon(0, QIcon(":/services/spotify"))
            
            # Procesar cada artista encontrado
            for artist in artists:
                # Crear nodo para el artista
                artist_item = QTreeWidgetItem(spotify_root)
                artist_item.setText(0, artist['name'])
                artist_item.setText(1, artist['name'])
                artist_item.setText(2, "Artista")
                
                # Almacenar datos del artista
                artist_data = {
                    'type': 'artist',
                    'title': artist['name'],
                    'artist': artist['name'],
                    'url': artist['external_urls']['spotify'],
                    'source': 'spotify',
                    'spotify_id': artist['id'],
                    'spotify_uri': artist['uri']
                }
                artist_item.setData(0, Qt.ItemDataRole.UserRole, artist_data)
                artist_item.setIcon(0, QIcon(":/services/spotify"))
                
                # Añadir un nodo hijo temporal para que se muestre el signo +
                loading_item = QTreeWidgetItem(artist_item)
                loading_item.setText(0, "Cargando álbumes...")
                
                # Conectar evento de expansión para cargar álbumes bajo demanda
                artist_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            
            # Expandir el nodo raíz de Spotify
            spotify_root.setExpanded(True)
            
            # Conectar señal para carga bajo demanda si no está conectada
            if not hasattr(self, '_spotify_tree_expand_connected'):
                self.treeWidget.itemExpanded.connect(self.on_spotify_tree_item_expanded)
                self._spotify_tree_expand_connected = True
            
            # Ocultar indicador de búsqueda - CORREGIDO
            if hasattr(self, 'show_loading_indicator'):
                self.show_loading_indicator(False)
            else:
                from modules.submodules.url_playlist.ui_helpers import show_loading_indicator
                show_loading_indicator(self, False)
            
            self.log(f"Encontrados {len(artists)} artistas en Spotify")
            return True
        
        except Exception as e:
            self.log(f"Error buscando en Spotify: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            
            # Ocultar indicador de búsqueda - CORREGIDO
            if hasattr(self, 'show_loading_indicator'):
                self.show_loading_indicator(False)
            else:
                from modules.submodules.url_playlist.ui_helpers import show_loading_indicator
                try:
                    show_loading_indicator(self, False)
                except:
                    pass  # Ignorar errores aquí para evitar bucles recursivos
                    
            return False

    def on_spotify_tree_item_expanded(self, item):
        """
        Carga los álbumes o canciones cuando se expande un ítem del árbol de Spotify
        """
        # Verificar que tenemos datos de Spotify
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or not isinstance(item_data, dict) or item_data.get('source') != 'spotify':
            return
        
        # Si ya está cargado (más de un hijo y el primer hijo no es "Cargando..."), no hacer nada
        if item.childCount() > 0 and item.child(0).text(0) != "Cargando álbumes..." and item.child(0).text(0) != "Cargando canciones...":
            return
        
        # Crear un worker y un hilo para cargar en segundo plano
        from PyQt6.QtCore import QThread
        
        # Crear una clase worker específica para esta tarea
        class SpotifyWorker(QObject):
            # Definir señales
            finished = pyqtSignal()
            
            def __init__(self, parent, item, item_data, item_type):
                super().__init__()
                self.parent = parent
                self.item = item
                self.item_data = item_data
                self.item_type = item_type
            
            def run(self):
                try:
                    if self.item_type == 'artist':
                        self.parent._load_spotify_albums_for_artist(self.item, self.item_data)
                    elif self.item_type == 'album':
                        self.parent._load_spotify_tracks_for_album(self.item, self.item_data)
                except Exception as e:
                    self.parent.log(f"Error en SpotifyWorker: {e}")
                finally:
                    self.finished.emit()
        
        # Obtener el tipo de ítem
        item_type = item_data.get('type')
        
        if item_type in ['artist', 'album']:
            # Limpiar el nodo de carga
            if item.childCount() > 0:
                item.takeChild(0)
            
            # Crear un elemento temporal de carga
            from PyQt6.QtWidgets import QTreeWidgetItem
            loading_item = QTreeWidgetItem(item)
            loading_item.setText(0, f"Cargando {'álbumes' if item_type == 'artist' else 'canciones'}...")
            loading_item.setIcon(0, QIcon(":/services/loading"))
            
            # Crear el thread y el worker
            thread = QThread()
            worker = SpotifyWorker(self, item, item_data, item_type)
            
            # Mover el worker al thread
            worker.moveToThread(thread)
            
            # Conectar señales
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            
            # Guardar referencias para evitar recolección de basura
            self._current_spotify_thread = thread
            self._current_spotify_worker = worker
            
            # Iniciar el thread
            thread.start()

    def _load_spotify_albums_for_artist(self, artist_item, artist_data):
        """
        Carga los álbumes de un artista en segundo plano
        """
        try:
            artist_id = artist_data.get('spotify_id')
            if not artist_id:
                # Emitir señal de error
                self.spotify_error_signal.emit(artist_item, "ID de artista no encontrado")
                return
            
            # Usar el cliente Spotify para obtener los álbumes
            albums = self.sp.artist_albums(
                artist_id, 
                album_type='album,single,compilation',
                limit=50
            )
            
            # Organizar álbumes por tipo
            albums_by_type = {
                'album': [],
                'single': [],
                'compilation': []
            }
            
            for album in albums['items']:
                album_type = album.get('album_type', 'album')
                if album_type in albums_by_type:
                    albums_by_type[album_type].append(album)
            
            # Ordenar cada tipo de álbum por fecha de lanzamiento
            for album_type in albums_by_type:
                albums_by_type[album_type].sort(
                    key=lambda x: x.get('release_date', '0000'),
                    reverse=True  # Más recientes primero
                )
            
            # Preparar datos para enviar a través de la señal
            albums_data = {
                'albums_by_type': albums_by_type,
                'artist_data': artist_data
            }
            
            # Emitir señal con los datos cargados
            self.spotify_albums_loaded_signal.emit(artist_item, albums_data)
            
        except Exception as e:
            self.log(f"Error cargando álbumes de Spotify: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            
            # Emitir señal de error
            self.spotify_error_signal.emit(artist_item, str(e))

    def _load_spotify_tracks_for_album(self, album_item, album_data):
        """
        Carga las canciones de un álbum en segundo plano
        """
        try:
            album_id = album_data.get('spotify_id')
            if not album_id:
                # Emitir señal de error
                self.spotify_error_signal.emit(album_item, "ID de álbum no encontrado")
                return
            
            # Usar el cliente Spotify para obtener las canciones
            album_info = self.sp.album_tracks(album_id, limit=50)
            tracks = album_info['items']
            
            # Ordenar por número de pista
            tracks.sort(key=lambda x: x.get('track_number', 0))
            
            # Preparar datos para enviar a través de la señal
            tracks_data = {
                'tracks': tracks,
                'album_data': album_data
            }
            
            # Emitir señal con los datos cargados
            self.spotify_tracks_loaded_signal.emit(album_item, tracks_data)
            
        except Exception as e:
            self.log(f"Error cargando canciones de Spotify: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            
            # Emitir señal de error
            self.spotify_error_signal.emit(album_item, str(e))

            
    def search_spotify_albums_tracks(self, query):
        """
        Realizar búsqueda de álbumes y canciones en Spotify cuando no se encuentran artistas
        """
        try:
            # Limpiar resultados anteriores
            self.treeWidget.clear()
            
            # Crear nodo raíz para Spotify
            spotify_root = QTreeWidgetItem(self.treeWidget)
            spotify_root.setText(0, "Spotify")
            spotify_root.setIcon(0, QIcon(":/services/spotify"))
            
            # Buscar álbumes
            self.log(f"Buscando álbumes para '{query}' en Spotify")
            album_results = self.sp.search(q=query, type='album', limit=10)
            albums = album_results['albums']['items']
            
            if albums:
                # Crear nodo para álbumes
                albums_node = QTreeWidgetItem(spotify_root)
                albums_node.setText(0, "Álbumes")
                albums_node.setIcon(0, QIcon(":/services/folder"))
                albums_node.setData(0, Qt.ItemDataRole.UserRole, {'type': 'group', 'source': 'spotify'})
                
                # Añadir cada álbum
                for album in albums:
                    album_item = QTreeWidgetItem(albums_node)
                    album_item.setText(0, album['name'])
                    
                    # Artistas del álbum
                    artists = [artist['name'] for artist in album['artists']]
                    artist_str = ", ".join(artists)
                    album_item.setText(1, artist_str)
                    
                    album_item.setText(2, "Álbum")
                    
                    # Añadir año si está disponible
                    if 'release_date' in album:
                        release_year = album['release_date'][:4] if album['release_date'] else ''
                        album_item.setText(3, release_year)
                    
                    # Añadir icono
                    album_item.setIcon(0, QIcon(":/services/spotify"))
                    
                    # Almacenar datos del álbum
                    album_data = {
                        'type': 'album',
                        'title': album['name'],
                        'artist': artist_str,
                        'url': album['external_urls']['spotify'],
                        'source': 'spotify',
                        'spotify_id': album['id'],
                        'spotify_uri': album['uri'],
                        'year': album.get('release_date', '')[:4] if album.get('release_date') else '',
                        'total_tracks': album.get('total_tracks', 0)
                    }
                    album_item.setData(0, Qt.ItemDataRole.UserRole, album_data)
                    
                    # Añadir un nodo hijo temporal para que se muestre el signo +
                    loading_item = QTreeWidgetItem(album_item)
                    loading_item.setText(0, "Cargando canciones...")
                    
                    # Configurar para mostrar indicador de expansión
                    album_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                
                # Expandir el nodo de álbumes
                albums_node.setExpanded(True)
            
            # Buscar canciones
            self.log(f"Buscando canciones para '{query}' en Spotify")
            track_results = self.sp.search(q=query, type='track', limit=20)
            tracks = track_results['tracks']['items']
            
            if tracks:
                # Crear nodo para canciones
                tracks_node = QTreeWidgetItem(spotify_root)
                tracks_node.setText(0, "Canciones")
                tracks_node.setIcon(0, QIcon(":/services/folder"))
                tracks_node.setData(0, Qt.ItemDataRole.UserRole, {'type': 'group', 'source': 'spotify'})
                
                # Añadir cada canción
                for track in tracks:
                    track_item = QTreeWidgetItem(tracks_node)
                    track_item.setText(0, track['name'])
                    
                    # Artistas de la canción
                    artists = [artist['name'] for artist in track['artists']]
                    artist_str = ", ".join(artists)
                    track_item.setText(1, artist_str)
                    
                    track_item.setText(2, "Canción")
                    
                    # Álbum y número de pista
                    if track.get('album'):
                        track_item.setText(3, track['album']['name'])
                    
                    # Añadir duración si está disponible
                    if 'duration_ms' in track:
                        duration_ms = track['duration_ms']
                        minutes = int(duration_ms / 60000)
                        seconds = int((duration_ms % 60000) / 1000)
                        track_item.setText(4, f"{minutes}:{seconds:02d}")
                    
                    # Añadir icono
                    track_item.setIcon(0, QIcon(":/services/spotify"))
                    
                    # Almacenar datos de la canción
                    track_data = {
                        'type': 'track',
                        'title': track['name'],
                        'artist': artist_str,
                        'album': track['album']['name'] if track.get('album') else '',
                        'url': track['external_urls']['spotify'],
                        'source': 'spotify',
                        'spotify_id': track['id'],
                        'spotify_uri': track['uri'],
                        'track_number': track.get('track_number', 0),
                        'duration': track.get('duration_ms', 0) / 1000  # Convertir a segundos
                    }
                    track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
                
                # Expandir el nodo de canciones
                tracks_node.setExpanded(True)
            
            # Expandir el nodo raíz de Spotify
            spotify_root.setExpanded(True)
            
            # Mostrar mensaje si no se encontró nada
            if not albums and not tracks:
                no_results_item = QTreeWidgetItem(spotify_root)
                no_results_item.setText(0, f"No se encontraron resultados para '{query}'")
                spotify_root.setExpanded(True)
            
            return True
            
        except Exception as e:
            self.log(f"Error buscando álbumes y canciones en Spotify: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return False