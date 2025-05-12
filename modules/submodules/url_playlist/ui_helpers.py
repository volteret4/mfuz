import os
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import ( QMenu, QTreeWidgetItem, QDialog, QMessageBox, QLineEdit, QApplication,
                            QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialogButtonBox, QFrame, QDialog,
                            QComboBox, QCheckBox, QListWidgetItem
                            )
from PyQt6.QtCore import Qt, QSize, QThreadPool
import traceback
from PyQt6 import uic
from pathlib import Path

from modules.submodules.url_playlist.spotify_manager import api_call_with_retry, create_spotify_playlist
from modules.submodules.url_playlist.media_utils import play_media, add_to_queue, play_item, add_item_to_queue, play_from_index, stop_playback
from modules.submodules.url_playlist.playlist_manager import (determine_source_from_url,
                         create_local_playlist, save_playlists, display_local_playlist,
                         _determine_source_from_url, count_tracks_in_playlist
                         )
from modules.submodules.url_playlist.rss_manager import (load_rss_playlist_content, actualizar_playlists_rss)
# Asegurarse de que PROJECT_ROOT está disponible
try:
    from base_module import PROJECT_ROOT
except ImportError:
    import os
    PROJECT_ROOT = os.path.abspath(Path(os.path.dirname(__file__), "..", ".."))

def format_duration(duration):
    """Formats duration into a readable string"""
    if not duration:
        return "Unknown"
        
    try:
        duration = float(duration)
        minutes, seconds = divmod(int(duration), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return str(duration)

def setup_service_icons(self):
    """Configura iconos para cada servicio."""
    self.service_icons = {
        'local': QIcon(":/services/plslove"),  
        'database': QIcon(":/services/database"),
        'bandcamp': QIcon(":/services/bandcamp"),
        'spotify': QIcon(":/services/spotify"),
        'lastfm': QIcon(":/services/lastfm"),
        'youtube': QIcon(":/services/youtube"),
        'soundcloud': QIcon(":/services/soundcloud"),
        'unknown': QIcon(":/services/wiki"),
        'loading': QIcon(":services/loading")
    }

    # Guardar el icono original del botón de búsqueda para restaurarlo después
    if hasattr(self, 'searchButton'):
        self.original_search_icon = self.searchButton.icon()

def get_source_icon(self, url, metadata=None):
    """
    Determine the source icon for a URL or metadata.
    Returns a QIcon for the appropriate service.
    """
    if metadata and isinstance(metadata, dict) and 'source' in metadata:
        # If metadata has a source field, use that directly
        source = metadata['source'].lower()
    else:
        # Try to determine source from URL
        url = str(url).lower()
        if 'spotify.com' in url:
            source = 'spotify'
        elif 'youtube.com' in url or 'youtu.be' in url:
            source = 'youtube'
        elif 'soundcloud.com' in url:
            source = 'soundcloud'
        elif 'bandcamp.com' in url:
            source = 'bandcamp'
        elif url.startswith(('/', 'file:', '~', 'C:', 'D:')):
            # Local file paths
            source = 'local'
        else:
            # Default or unknown
            source = 'unknown'
    
    # Return the appropriate icon
    if source in self.service_icons:
        return self.service_icons[source]
    return self.service_icons.get('unknown', QIcon())

def setup_loading_indicator(self):
    """Configura un indicador de carga simple que no interfiere con la UI."""
    try:
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtGui import QMovie
        from PyQt6.QtCore import QSize
        
        # Crear un simple label para el indicador
        self.loading_label = QLabel(self)
        self.loading_label.setFixedSize(QSize(24, 24))
        
        # Cargar el gif animado
        self.loading_movie = QMovie(":/services/loading")
        if self.loading_movie.isValid():
            self.loading_movie.setScaledSize(QSize(24, 24))
            self.loading_label.setMovie(self.loading_movie)
        
        # Posicionar junto al botón de búsqueda pero sin alterar layouts
        button_pos = self.searchButton.pos()
        self.loading_label.move(button_pos.x() - 1, button_pos.y() + 1)
        
        # Inicialmente oculto
        self.loading_label.hide()
        
    except Exception as e:
        self.log(f"Error setting up loading indicator: {str(e)}")

def _update_button_icon(self):
    """Actualiza el icono del botón con el frame actual del GIF."""
    if hasattr(self, 'loading_movie') and self.loading_movie.isValid():
        # Crear un QIcon a partir del frame actual del QMovie
        from PyQt6.QtGui import QIcon, QPixmap
        pixmap = self.loading_movie.currentPixmap()
        icon = QIcon(pixmap)
        
        # Aplicar al botón
        self.searchButton.setIcon(icon)

def show_loading_indicator(self, visible=True):
    """Cambia el icono del botón de búsqueda entre el icono normal y el GIF de carga."""
    try:
        if visible:
            # Crear un QMovie con el GIF
            from PyQt6.QtGui import QMovie
            from PyQt6.QtCore import QSize
            
            # Si no tenemos ya el movie creado
            if not hasattr(self, 'loading_movie'):
                self.loading_movie = QMovie(":/services/loading")
                
                if self.loading_movie.isValid():
                    # Configurar el tamaño adecuado para que coincida con el icono original
                    icon_size = self.searchButton.iconSize()
                    self.loading_movie.setScaledSize(icon_size)
                    
                    # Conectar una señal para actualizar el icono del botón con cada frame
                    self.loading_movie.frameChanged.connect(lambda: _update_button_icon(self))
                else:
                    self.log("Error: GIF de carga no válido")
                    return
            
            # Iniciar la animación
            self.loading_movie.start()
            
            # Aplicar el primer frame al botón
            _update_button_icon(self)
            
            # Mantener el botón habilitado para que el usuario pueda cancelar si lo desea
            self.searchButton.setEnabled(True)
        else:
            # Detener la animación si existe
            if hasattr(self, 'loading_movie'):
                self.loading_movie.stop()
            
            # Restaurar el icono original
            if hasattr(self, 'original_search_icon'):
                self.searchButton.setIcon(self.original_search_icon)
            
            # Asegurarse de que el botón esté habilitado
            self.searchButton.setEnabled(True)
        
        # Procesar eventos para actualizar la UI
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
    except Exception as e:
        self.log(f"Error al cambiar icono de carga: {str(e)}")
        # Restaurar el estado original en caso de error
        if hasattr(self, 'original_search_icon'):
            self.searchButton.setIcon(self.original_search_icon)
        self.searchButton.setEnabled(True)

def setup_context_menus(self):
    """Set up context menus for tree and list widgets"""
    # Set custom context menu for treeWidget
    self.treeWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    self.treeWidget.customContextMenuRequested.connect(show_tree_context_menu)
    
    # Set custom context menu for listWidget
    self.listWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    #self.listWidget.customContextMenuRequested.connect(self.show_list_context_menu)

def setup_action_unified_playlist(self):
    """Create a unified button that shows a hierarchical menu of all playlist types"""
    try:
        # Create the unified button if it doesn't exist
        if not hasattr(self, 'action_unified_playlist'):
            self.action_unified_playlist = self.findChild(QPushButton, 'action_unified_playlist')
            
        if not self.action_unified_playlist:
            self.log("Error: No se pudo encontrar el botón 'action_unified_playlist'")
            return False
        
        # Create the menu
        self.playlist_menu = QMenu(self.action_unified_playlist)
        
        # Set up the menu
        setup_unified_playlist_menu(self)
        
        # Make sure the button is visible
        self.action_unified_playlist.setVisible(True)
        
        self.log("Unified playlist button set up")
        return True
    except Exception as e:
        self.log(f"Error setting up unified playlist button: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False

def setup_unified_playlist_menu(self):
    """Configura el menú del botón unificado de playlists"""
    try:
        # Create the main menu in the main thread
        from PyQt6.QtCore import QMetaObject, Qt
        
        # Definir el método que se ejecutará en el hilo principal
        def _create_menu_in_main_thread():
            try:
                # Create the main menu
                menu = QMenu(self)
                self.action_unified_playlist.setMenu(menu)
                
                # Use proper attribute check to avoid TypeError
                local_playlists = []
                if hasattr(self, 'playlists') and isinstance(self.playlists, dict) and 'local' in self.playlists:
                    local_playlists = self.playlists['local']
                
                # Rest of your existing code...
                
                # Get visibility configuration
                show_local = self.get_setting_value('show_local_playlists', True)
                show_spotify = self.get_setting_value('show_spotify_playlists', True) 
                show_rss = self.get_setting_value('show_rss_playlists', True)
                
                # Add local playlists section
                if show_local:
                    # Create a local submenu
                    local_menu = menu.addMenu(QIcon(":/services/plslove"), "Playlists Locales")
                    
                    # Add option to create new playlist
                    create_local_action = local_menu.addAction(QIcon(":/services/b_plus_cross"), "Nueva Playlist Local")
                    create_local_action.triggered.connect(lambda: show_create_playlist_dialog(self, "local"))
                    
                    local_menu.addSeparator()
                    
                    # Add existing playlists
                    for playlist in sorted(local_playlists, key=lambda x: x.get('name', '').lower()):
                        name = playlist.get('name', 'Sin nombre')
                        
                        # Create action with explicit variable capture
                        action = local_menu.addAction(QIcon(":/services/plslove"), name)
                        # CRITICAL: Make a deep copy of the playlist data
                        playlist_copy = dict(playlist)
                        # Connect with lambdas that have default arguments to capture current value
                        action.triggered.connect(lambda checked=False, p=playlist_copy: display_local_playlist(self,p))
                
                # Add Spotify playlists section
                if show_spotify and hasattr(self, 'spotify_authenticated') and self.spotify_authenticated:
                    spotify_menu = menu.addMenu(QIcon(":/services/spotify"), "Playlists de Spotify")
                    
                    # Add option to create new playlist
                    create_spotify_action = spotify_menu.addAction(QIcon(":/services/b_plus_cross"), "Nueva Playlist de Spotify")
                    create_spotify_action.triggered.connect(lambda: show_create_playlist_dialog(self, "spotify"))
                    
                    spotify_menu.addSeparator()
                    
                    # Add existing playlists
                    if hasattr(self, 'spotify_playlists'):
                        for name, playlist in self.spotify_playlists.items():
                            # Create playlist action
                            action = spotify_menu.addAction(QIcon(":/services/spotify"), name)
                            # Store playlist ID and name in local variables
                            playlist_id = playlist['id']
                            playlist_name = name
                            # Connect with explicit parameters
                            action.triggered.connect(lambda checked=False, id=playlist_id, name=playlist_name: 
                                                show_spotify_playlist_content(self, id, name))
                
                # Add RSS playlists section
                if show_rss:
                    rss_menu = menu.addMenu(QIcon(":/services/rss"), "Blogs RSS")
                    
                    # Organize by blog
                    blogs = {}
                    
                    # Scan RSS directories
                    if os.path.exists(self.rss_pending_dir):
                        for blog_dir in os.listdir(self.rss_pending_dir):
                            blog_path = Path(self.rss_pending_dir, blog_dir)
                            if os.path.isdir(blog_path):
                                blogs[blog_dir] = {'path': blog_path, 'playlists': []}
                                
                                # Find playlists for this blog
                                for playlist_file in os.listdir(blog_path):
                                    if playlist_file.endswith('.m3u'):
                                        abs_path = os.path.abspath(Path(blog_path, playlist_file))
                                        track_count = count_tracks_in_playlist(abs_path)
                                        
                                        blogs[blog_dir]['playlists'].append({
                                            'name': playlist_file,
                                            'path': abs_path,
                                            'track_count': track_count,
                                            'blog': blog_dir,
                                            'state': 'pending'
                                        })
                    
                    # Create submenu for each blog
                    for blog_name, blog_data in sorted(blogs.items()):
                        if blog_data['playlists']:
                            blog_menu = rss_menu.addMenu(blog_name)
                            
                            # Add playlists for this blog
                            for playlist in sorted(blog_data['playlists'], key=lambda x: x['name']):
                                display_text = f"{playlist['name']} ({playlist['track_count']} pistas)"
                                action = blog_menu.addAction(QIcon(":/services/rss"), display_text)
                                
                                # CRITICAL: Make a deep copy of the playlist data
                                playlist_copy = {
                                    'name': playlist['name'],
                                    'path': playlist['path'],
                                    'track_count': playlist['track_count'],
                                    'blog': playlist['blog'],
                                    'state': playlist['state']
                                }
                                
                                # Connect with specific handler function
                                action.triggered.connect(lambda checked=False, data=playlist_copy: 
                                                    on_rss_playlist_menu_clicked(self, data))

                    # Añadir opción para actualizar RSS justo después de crear el menú RSS
                    from modules.submodules.url_playlist.rss_manager import actualizar_playlists_rss
                    refresh_action = rss_menu.addAction(QIcon(":/services/feeds"), "Actualizar Feeds RSS")
                    refresh_action.triggered.connect(lambda: actualizar_playlists_rss(self))
                    rss_menu.addSeparator()

                # After setting up the regular menu items, add a separator
                menu.addSeparator()
                
                # Add Last.fm submenu
                from modules.submodules.url_playlist.lastfm_manager import setup_lastfm_menu_items
                lastfm_menu = menu.addMenu(QIcon(":/services/lastfm"), "Last.fm Scrobbles")
                
                # Set up Last.fm menu items in the submenu
                lastfm_menu_refs = setup_lastfm_menu_items(self, lastfm_menu)
                
                # Store additional references for the unified menu
                self.unified_months_menu = lastfm_menu_refs.get('months_menu')
                self.unified_years_menu = lastfm_menu_refs.get('years_menu')
                
                self.log("Unified playlist menu setup complete")
                return True
            except Exception as e:
                self.log(f"Error in _create_menu_in_main_thread: {str(e)}")
                import traceback
                self.log(traceback.format_exc())
                return False
        
        # Si estamos en el hilo principal, ejecutar directamente
        from PyQt6.QtCore import QThread
        if QThread.currentThread() == QApplication.instance().thread():
            return _create_menu_in_main_thread()
        else:
            # Ejecutar la creación del menú en el hilo principal de forma bloqueante
            # para asegurar que está listo cuando retornamos
            result = [False]  # Lista para almacenar el resultado
            
            def run_and_store_result():
                result[0] = _create_menu_in_main_thread()
            
            QMetaObject.invokeMethod(self, run_and_store_result, 
                                   Qt.ConnectionType.BlockingQueuedConnection)
            
            self.log(f"Unified playlist menu setup from thread: {result[0]}")
            return result[0]
        
    except Exception as e:
        self.log(f"Error setting up unified menu: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False

def add_single_result_to_tree(self, result, parent_item):
    """
    Añade un único resultado al árbol de forma segura.
    Esta versión simplificada evita recursión excesiva y estructuras complejas.
    """
    if not result or not parent_item:
        return None
        
    try:
        from PyQt6.QtWidgets import QTreeWidgetItem
        from PyQt6.QtCore import Qt
        
        # Extraer información básica
        item_type = result.get('type', 'unknown').lower()
        title = result.get('title', 'Unknown')
        artist = result.get('artist', '')
        
        # Crear ítem para el resultado
        result_item = QTreeWidgetItem(parent_item)
        result_item.setText(0, title)
        result_item.setText(1, artist)
        
        # Establecer tipo de ítem
        if item_type == 'artist':
            result_item.setText(2, "Artista")
        elif item_type == 'album':
            result_item.setText(2, "Álbum")
            if 'year' in result:
                result_item.setText(3, str(result['year']))
        elif item_type in ['track', 'song']:
            result_item.setText(2, "Canción")
            if 'track_number' in result:
                result_item.setText(3, str(result['track_number']))
            if 'duration' in result:
                # Formatear duración si está disponible
                try:
                    duration = int(result['duration'])
                    minutes = duration // 60
                    seconds = duration % 60
                    duration_str = f"{minutes}:{seconds:02d}"
                    result_item.setText(4, duration_str)
                except:
                    pass
        else:
            result_item.setText(2, item_type.capitalize())
        
        # Almacenar datos completos
        result_item.setData(0, Qt.ItemDataRole.UserRole, result)
        
        # Establecer icono basado en la fuente
        source = result.get('source', 'unknown')
        if hasattr(self, 'service_icons') and source in self.service_icons:
            result_item.setIcon(0, self.service_icons[source])
            
        return result_item
    except Exception as e:
        self.log(f"Error en add_single_result_to_tree: {str(e)}")
        return None

def display_search_results(self, results, clear_existing=True):
    """
    Muestra los resultados de búsqueda en el árbol con la estructura jerárquica correcta:
    servicio > artista > álbum > canción.
    """
    if not results:
        self.log("No hay resultados que mostrar")
        return False
    
    # Limpiar resultados anteriores si se solicita
    if clear_existing and hasattr(self, 'treeWidget'):
        self.treeWidget.clear()
    
    # Organizar resultados por servicio, artista, álbum, canción
    organized = {}
    
    for result in results:
        source = result.get('source', 'unknown')
        artist = result.get('artist', '')
        item_type = result.get('type', '')
        
        # Inicializar estructura
        if source not in organized:
            organized[source] = {}
        
        if artist not in organized[source]:
            organized[source][artist] = {'info': None, 'albums': {}, 'tracks': []}
        
        # Almacenar información según el tipo
        if item_type == 'artist':
            organized[source][artist]['info'] = result
        elif item_type in ['album', 'álbum']:
            album_title = result.get('title', '')
            if album_title not in organized[source][artist]['albums']:
                organized[source][artist]['albums'][album_title] = {'info': result, 'tracks': []}
            else:
                organized[source][artist]['albums'][album_title]['info'] = result
        elif item_type in ['track', 'song', 'canción']:
            album_title = result.get('album', '')
            
            if album_title:
                # Añadir a álbum si existe
                if album_title not in organized[source][artist]['albums']:
                    organized[source][artist]['albums'][album_title] = {'info': None, 'tracks': []}
                organized[source][artist]['albums'][album_title]['tracks'].append(result)
            else:
                # Añadir a pistas sin álbum
                organized[source][artist]['tracks'].append(result)
    
    from PyQt6.QtWidgets import QTreeWidgetItem
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    
    # Crear elementos en el árbol
    for source, artists in organized.items():
        # Crear nodo para el servicio
        source_item = QTreeWidgetItem(self.treeWidget)
        source_item.setText(0, source.capitalize())
        source_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'service', 'source': source})
        
        # Establecer icono de servicio
        if hasattr(self, 'service_icons') and source in self.service_icons:
            source_item.setIcon(0, self.service_icons[source])
        elif hasattr(self, 'get_source_icon'):
            source_item.setIcon(0, self.get_source_icon('', {'source': source}))
        
        for artist_name, artist_data in artists.items():
            # Crear nodo para el artista
            artist_item = QTreeWidgetItem(source_item)
            artist_item.setText(0, artist_name)
            artist_item.setText(1, artist_name)  # Repetir en columna de artista
            artist_item.setText(2, "Artista")
            
            # Usar datos del artista si están disponibles
            if artist_data['info']:
                artist_item.setData(0, Qt.ItemDataRole.UserRole, artist_data['info'])
            else:
                artist_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'artist',
                    'title': artist_name,
                    'artist': artist_name,
                    'source': source
                })
            
            # Añadir álbumes
            for album_title, album_data in artist_data['albums'].items():
                # Crear nodo para el álbum
                album_item = QTreeWidgetItem(artist_item)
                album_item.setText(0, album_title)
                album_item.setText(1, artist_name)
                album_item.setText(2, "Álbum")
                
                # Añadir año si está disponible
                if album_data['info'] and 'year' in album_data['info']:
                    album_item.setText(3, str(album_data['info']['year']))
                
                # Usar datos del álbum
                if album_data['info']:
                    album_item.setData(0, Qt.ItemDataRole.UserRole, album_data['info'])
                else:
                    album_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'type': 'album',
                        'title': album_title,
                        'artist': artist_name,
                        'source': source
                    })
                
                # Añadir pistas del álbum
                for track in album_data['tracks']:
                    _add_result_to_tree(self, track, album_item)
            
            # Añadir pistas sin álbum directamente bajo el artista
            for track in artist_data['tracks']:
                _add_result_to_tree(self, track, artist_item)
    
    # Expandir todos los nodos de servicio
    for i in range(self.treeWidget.topLevelItemCount()):
        self.treeWidget.topLevelItem(i).setExpanded(True)
    
    return True

def _count_tree_items(item):
    """Cuenta recursivamente el número total de ítems en un árbol."""
    if not item:
        return 0
        
    count = 1  # Contar el ítem actual
    
    # Contar recursivamente todos los hijos
    for i in range(item.childCount()):
        count += _count_tree_items(item.child(i))
        
    return count


def _count_service_items(service_item):
    """Cuenta el número de artistas, álbumes y canciones en un servicio."""
    if not service_item:
        return 0
        
    # No contamos el ítem del servicio en sí, solo sus hijos
    count = 0
    
    # Contar todos los artistas, álbumes y canciones
    for i in range(service_item.childCount()):
        artist_item = service_item.child(i)
        count += 1  # Contar artista
        
        # Contar álbumes de este artista
        for j in range(artist_item.childCount()):
            album_item = artist_item.child(j)
            count += 1  # Contar álbum
            
            # Contar canciones de este álbum
            count += album_item.childCount()
    
    return count


def display_external_results(self, results, group_by_service=False):
    """Display external search results, keeping database results already shown."""
    if not results:
        self.log("No se encontraron resultados externos.")
        return
    
    # Check for group_by_service setting from urlplaylist_only_local
    if hasattr(self, 'urlplaylist_only_local') and self.urlplaylist_only_local:
        group_by_service = True
    
    # Filter out results from database to avoid duplicates
    external_results = [r for r in results if not r.get('from_database', False)]
    
    # Filter by origen if urlplaylist_only_local is enabled
    if hasattr(self, 'urlplaylist_only_local') and self.urlplaylist_only_local:
        external_results = [r for r in external_results if r.get('origen', '') == 'local']
    
    if external_results:
        display_search_results(self, external_results, group_by_service)
        self.log(f"Se añadieron {len(external_results)} resultados de servicios externos")


        
def on_list_double_click(item):
    """Maneja el doble clic en un elemento de la lista."""
    # Obtener el widget padre
    list_widget = item.listWidget()
    # Obtener la instancia principal
    self = list_widget.parent()
    while self and not hasattr(self, 'current_track_index'):
        self = self.parent()
    
    if not self or not hasattr(self, 'current_track_index'):
        self.log("Error: No se pudo encontrar la instancia principal")
        return
    
    row = list_widget.row(item)
    self.current_track_index = row
    
    # Iniciar reproducción del elemento seleccionado
    from modules.submodules.url_playlist.media_utils import play_from_index
    play_from_index(self, row)
    self.log(f"Reproduciendo '{item.text()}'")


def show_advanced_settings(parent_instance):
    """Show the advanced settings dialog."""
    try:
        # Create the dialog from UI file
        dialog = QDialog(parent_instance)
        ui_file = Path(PROJECT_ROOT, "ui", "url_playlist_advanced_settings_dialog.ui")
        
        if os.path.exists(ui_file):
            uic.loadUi(ui_file, dialog)
            
            # Check if urlplaylist_only_local already exists
            only_local_checkbox = dialog.findChild(QCheckBox, 'urlplaylist_only_local')
            
            # If it doesn't exist, create it
            if not only_local_checkbox:
                # Add the checkbox to the dialog
                frame = dialog.findChild(QFrame, 'frame')
                if frame and frame.layout():
                    only_local_checkbox = QCheckBox("Mostrar solo archivos locales", dialog)
                    only_local_checkbox.setObjectName('urlplaylist_only_local')
                    
                    # Get current value from parent instance
                    if hasattr(parent_instance, 'urlplaylist_only_local'):
                        only_local_checkbox.setChecked(parent_instance.urlplaylist_only_local)
                    else:
                        only_local_checkbox.setChecked(False)
                        
                    # Add to layout
                    frame.layout().addWidget(only_local_checkbox)
            
            # Set up current values
            if hasattr(dialog, 'num_servicios_spinBox'):
                dialog.num_servicios_spinBox.setValue(parent_instance.num_servicios_spinBox)
            
            # Set up checkboxes based on current settings
            _setup_service_checkboxes(parent_instance, dialog)
            
            # Connect the button box
            if hasattr(dialog, 'adv_sett_buttonBox'):
                # Conecta los botones estándar de QDialogButtonBox
                dialog.adv_sett_buttonBox.accepted.connect(lambda: parent_instance._save_advanced_settings(dialog))
                dialog.adv_sett_buttonBox.rejected.connect(dialog.reject)
            
            # Show the dialog
            result = dialog.exec()
            
            # Si el resultado es QDialog.Accepted, los ajustes ya se habrán guardado
            # mediante la conexión con _save_advanced_settings
        else:
            parent_instance.log(f"UI file not found: {ui_file}")
            QMessageBox.warning(parent_instance, "Error", f"UI file not found: {ui_file}")
    except Exception as e:
        parent_instance.log(f"Error showing advanced settings: {str(e)}")
        import traceback
        parent_instance.log(traceback.format_exc())

def on_tree_double_click(item, column):
    """Handle double click on tree item to either expand/collapse or load content"""
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication
        
        # Get the tree widget
        tree_widget = item.treeWidget()
        
        # First, try to get the controller through the property
        controller = tree_widget.property("controller")
        
        # If no controller is found through property, look through parent hierarchy
        if not controller:
            # Start with tree widget's parent
            parent = tree_widget.parent()
            while parent:
                if hasattr(parent, 'add_item_to_queue') and callable(getattr(parent, 'add_item_to_queue')):
                    controller = parent
                    break
                parent = parent.parent()
        
        # If still not found, try to find in all top-level widgets
        if not controller:
            for widget in QApplication.instance().topLevelWidgets():
                if hasattr(widget, 'add_item_to_queue') and callable(getattr(widget, 'add_item_to_queue')):
                    controller = widget
                    break
        
        # If still not found, look through ALL widgets (last resort - could be slow)
        if not controller:
            for widget in QApplication.instance().allWidgets():
                if hasattr(widget, 'add_item_to_queue') and callable(getattr(widget, 'add_item_to_queue')):
                    controller = widget
                    break
        
        # If we can't find the controller, log it and return
        if not controller:
            #self.log(f"Could not find controller with add_item_to_queue method.")
            #self.log(f"Item text: {item.text(0)}")
            return
        
        # Now use the controller for all operations
        
        # Get the item data
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # If it's a parent item with children, just expand/collapse
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return
        
        # If it's a playlist item, load its content
        if item_data and isinstance(item_data, dict) and item_data.get('type') == 'playlist' and 'path' in item_data:
            if hasattr(controller, 'load_rss_playlist_content'):
                controller.load_rss_playlist_content(item, item_data)
            elif hasattr(controller, 'load_rss_playlist_content_to_tree'):
                controller.load_rss_playlist_content_to_tree(item_data)
            else:
                # Fallback to direct import
                from modules.submodules.url_playlist.rss_manager import load_rss_playlist_content
                load_rss_playlist_content(controller, item, item_data)
            return
            
        # If it's a track item with URL, play it
        if item_data and isinstance(item_data, dict) and item_data.get('type') in ['track', 'song'] and ('url' in item_data or 'file_path' in item_data):
            if hasattr(controller, 'play_item'):
                controller.play_item(item)
            else:
                # Track but no play_item method, add to queue
                controller.add_item_to_queue(item)
                # And try to play the queue
                if hasattr(controller, 'play_from_index') and hasattr(controller, 'current_playlist'):
                    index = len(controller.current_playlist) - 1
                    if index >= 0:
                        controller.play_from_index(index)
            return
        
        # For all other items, add to queue
        controller.add_item_to_queue(item)
        
        # If nothing is playing, play the newly added item
        if hasattr(controller, 'is_playing') and hasattr(controller, 'current_playlist'):
            if (not controller.is_playing) and len(controller.current_playlist) > 0:
                index = len(controller.current_playlist) - 1
                if hasattr(controller, 'play_from_index'):
                    controller.play_from_index(index)
        
    except Exception as e:
        import traceback
        self.log(f"Error in on_tree_double_click: {e}")
        self.log(traceback.format_exc())



def on_spotify_playlist_changed(self, index):
    """Handle selection change in the Spotify playlist comboBox"""
    if hasattr(self, '_is_initializing') and self._is_initializing:
        return  # No hacer nada durante la inicialización
        
    combo = self.playlist_spotify_comboBox
    if not combo:
        return
        
    selected_text = combo.currentText()
    
    # Ignorar la selección de placeholder
    if index == 0 or selected_text == "Playlists Spotify":
        self.log("Seleccionado placeholder de Spotify")
        return
    
    # Opción "Nueva Playlist Spotify"
    if index == 1 or selected_text == "Nueva Playlist Spotify":
        # Forzar llamada directa (no a través de señal)
        self.log("Mostrando diálogo de creación de playlist Spotify")
        QTimer.singleShot(100, lambda: show_create_playlist_dialog(self, "spotify"))
        return
    
    # Mostrar contenido de la playlist seleccionada
    if hasattr(self, 'spotify_playlists') and selected_text in self.spotify_playlists:
        playlist = self.spotify_playlists[selected_text]
        show_spotify_playlist_content(self, playlist['id'], playlist['name'])



def on_playlist_rss_changed(self, index):
    """Maneja el cambio de selección en el combobox de playlists RSS"""
    try:
        if index <= 0:  # Skip the default item
            return
            
        # Get the selected item's text and data
        item_text = self.playlist_rss_comboBox.itemText(index)
        item_data = self.playlist_rss_comboBox.itemData(index, Qt.ItemDataRole.UserRole)
        
        self.log(f"Selected RSS item: '{item_text}' with data: {item_data}")
        
        # Skip headers (items starting with ---)
        if item_text.startswith("---") or item_data is None:
            self.log("Skipping header or item with no data")
            return
        
        # Validate the data
        if not isinstance(item_data, dict) or 'path' not in item_data:
            self.log(f"Invalid item data: {item_data}")
            return
            
        # Load the playlist content

        load_rss_playlist_content_to_tree(self, item_data)
        
    except Exception as e:
        self.log(f"Error in on_playlist_rss_changed: {str(e)}")
        import traceback
        self.log(traceback.format_exc())




def on_playlist_local_changed(self, index):
    """Maneja el cambio de selección en el combobox de playlist local."""
    if hasattr(self, '_is_initializing') and self._is_initializing:
        return  # No hacer nada durante la inicialización
        
    combo = self.playlist_local_comboBox
    selected_text = combo.currentText()
    
    # Ignorar la selección de placeholder
    if index == 0 or selected_text == "Playlists locales":
        self.log("Seleccionado placeholder de playlists locales")
        return
    
    # Opción "Nueva Playlist Local"
    if index == 1 or selected_text == "Nueva Playlist Local":
        # Mostrar diálogo para crear una nueva playlist local
        self.log("Mostrando diálogo de creación de playlist local")
        show_create_playlist_dialog(self, "local")
        return
    
    self.log(f"Playlist Local seleccionada: {selected_text}")

    
    # Verificar que self.playlists existe y es válido
    if not hasattr(self, 'playlists') or not isinstance(self.playlists, dict) or 'local' not in self.playlists:
        self.log("Estructura de playlists no válida, recargando...")
        # Cargar playlists
        self.playlists = self.load_playlists()
        # Cargar playlists locales directamente
        local_playlists = self.load_local_playlists()
        # Actualizar estructura
        if isinstance(self.playlists, dict):
            self.playlists['local'] = local_playlists
        else:
            self.playlists = {'spotify': [], 'local': local_playlists, 'rss': []}
        # Guardar cambios
        save_playlists(self, )
    
    # Mostrar todas las playlists locales disponibles (para diagnóstico)
    local_playlist_names = [p.get('name', 'Sin nombre') for p in self.playlists.get('local', [])]
    self.log(f"Playlists locales disponibles: {', '.join(local_playlist_names)}")
    
    # Buscar la playlist seleccionada
    selected_playlist = None
    for playlist in self.playlists.get('local', []):
        if playlist.get('name') == selected_text:
            selected_playlist = playlist
            self.log(f"Playlist '{selected_text}' encontrada en la estructura de datos")
            break
    
    # Si no se encuentra, intentar cargar directamente del archivo
    if not selected_playlist:
        self.log(f"Playlist '{selected_text}' no encontrada en la estructura, buscando archivo...")
        
        # Obtener ruta de playlists
        local_playlist_path = self.get_local_playlist_path()
        
        # Buscar archivo JSON
        json_file = Path(local_playlist_path, f"{selected_text}.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    selected_playlist = json.load(f)
                #self.log(f"Playlist cargada directamente del archivo JSON")
            except Exception as e:
                self.log(f"Error cargando archivo JSON: {str(e)}")
        
        # Si no hay JSON, buscar archivo PLS
        if not selected_playlist:
            pls_file = Path(local_playlist_path, f"{selected_text}.pls")
            if os.path.exists(pls_file):
                try:
                    items = self.parse_pls_file(pls_file)
                    if items:
                        selected_playlist = {
                            'name': selected_text,
                            'items': items,
                            'created': int(time.time()),
                            'modified': int(time.time())
                        }
                        #self.log(f"Playlist cargada directamente del archivo PLS")
                except Exception as e:
                    self.log(f"Error cargando archivo PLS: {str(e)}")
    
    if not selected_playlist:
        self.log(f"No se pudo encontrar la playlist '{selected_text}' en ninguna ubicación")
        return
    
    # Mostrar la playlist en el tree widget
    display_local_playlist(self, selected_playlist)
    
    # Actualizar la estructura de playlists si la playlist se cargó de archivo
    if selected_playlist and selected_playlist not in self.playlists.get('local', []):
        self.log("Añadiendo playlist a la estructura de datos...")
        self.playlists['local'].append(selected_playlist)
        save_playlists(self, )



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
        self.stop_playback()
        
        self.log("Cola de reproducción limpiada")

def show_mark_as_listened_dialog(self, playlist_data):
    """Muestra un diálogo preguntando si marcar la playlist como escuchada"""
    reply = QMessageBox.question(
        self,
        "Playlist Terminada",
        f"¿Deseas marcar la playlist '{playlist_data['name']}' como escuchada?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes
    )
    
    if reply == QMessageBox.StandardButton.Yes:
        self.move_rss_playlist_to_listened(playlist_data)



def on_rss_playlist_menu_clicked(self, playlist_data):
    """Handle clicking a playlist from the unified button menu"""
    try:
        self.log(f"Menu clicked with playlist data: {playlist_data}")
        
        # Make a clean copy of the data
        playlist_copy = {
            'name': playlist_data['name'],
            'path': playlist_data['path'],
            'track_count': playlist_data.get('track_count', 0),
            'blog': playlist_data.get('blog', ''),
            'state': playlist_data.get('state', 'pending')
        }
        
        # Load the playlist content
        load_rss_playlist_content_to_tree(self, playlist_copy)
        
    except Exception as e:
        self.log(f"Error in on_rss_playlist_menu_clicked: {str(e)}")
        import traceback
        self.log(traceback.format_exc())



def show_create_playlist_dialog(self, playlist_type):
    """Muestra el diálogo para crear una nueva playlist local o de Spotify"""
    self.log(f"Iniciando diálogo de creación de playlist {playlist_type}")
    
    # Cargar el archivo UI para el diálogo
    dialog = QDialog(self)
    ui_path = Path(PROJECT_ROOT, "ui", "create_playlist_dialog.ui")
    
    if os.path.exists(ui_path):
        uic.loadUi(ui_path, dialog)
    else:
        # Fallback si no existe el archivo UI
        _create_fallback_dialog(self, dialog, playlist_type)
    
    # Configurar el título y el icono según el tipo
    if playlist_type == "local":
        dialog.setWindowTitle("Crear Nueva Playlist Local")
        if hasattr(dialog, 'playlist_icon_label'):
            dialog.playlist_icon_label.setPixmap(QIcon(":/services/plslove").pixmap(QSize(32, 32)))
        if hasattr(dialog, 'title_label'):
            dialog.title_label.setText("Crear nueva playlist local")
    else:  # spotify
        dialog.setWindowTitle("Crear Nueva Playlist de Spotify")
        if hasattr(dialog, 'playlist_icon_label'):
            dialog.playlist_icon_label.setPixmap(QIcon(":/services/spotify").pixmap(QSize(32, 32)))
        if hasattr(dialog, 'title_label'):
            dialog.title_label.setText("Crear nueva playlist de Spotify")
    
    # Conectar botones (asumiendo nombres en el UI)
    if hasattr(dialog, 'buttonBox'):
        dialog.buttonBox.accepted.connect(dialog.accept)
        dialog.buttonBox.rejected.connect(dialog.reject)
    
    # Mostrar el diálogo
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        # Obtener el nombre de la playlist (asumiendo un campo con nombre 'playlist_name_edit')
        playlist_name = ""
        description = ""
        
        if hasattr(dialog, 'playlist_name_edit'):
            playlist_name = dialog.playlist_name_edit.text().strip()
        
        if hasattr(dialog, 'description_edit'):
            description = dialog.description_edit.text().strip()
        
        if playlist_name:
            if playlist_type == "local":
                create_local_playlist(self, playlist_name)
            else:  # spotify
                create_spotify_playlist(self, playlist_name, public=False, description=description)
        else:
            self.log(f"Nombre de playlist vacío, no se creó la playlist {playlist_type}")
    
    # Si se canceló, restablecer el combobox correspondiente
    if result != QDialog.DialogCode.Accepted:
        if playlist_type == "local" and hasattr(self, 'playlist_local_comboBox'):
            # Volver al placeholder
            self.playlist_local_comboBox.setCurrentIndex(0)
        elif playlist_type == "spotify" and hasattr(self, 'playlist_spotify_comboBox'):
            # Volver al placeholder
            self.playlist_spotify_comboBox.setCurrentIndex(0)
        
        self.log(f"Creación de playlist {playlist_type} cancelada")


def _create_fallback_dialog(self, dialog, playlist_type):
    """Crea un diálogo de respaldo si no existe el archivo UI"""
    dialog.setMinimumWidth(300)
    layout = QVBoxLayout(dialog)
    
    # Icono y título
    header_layout = QHBoxLayout()
    icon_label = QLabel()
    if playlist_type == "local":
        icon_label.setPixmap(QIcon(":/services/plslove").pixmap(QSize(32, 32)))
    else:  # spotify
        icon_label.setPixmap(QIcon(":/services/spotify").pixmap(QSize(32, 32)))
    
    title_label = QLabel(f"Crear nueva playlist {playlist_type}")
    font = title_label.font()
    font.setBold(True)
    title_label.setFont(font)
    
    header_layout.addWidget(icon_label)
    header_layout.addWidget(title_label)
    header_layout.addStretch()
    
    layout.addLayout(header_layout)
    
    # Separador
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    layout.addWidget(line)
    
    # Campo de nombre
    layout.addWidget(QLabel("Nombre de la playlist:"))
    name_edit = QLineEdit()
    name_edit.setObjectName("playlist_name_edit")  # Nombre importante para acceder después
    layout.addWidget(name_edit)
    
    # Botones
    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    button_box.setObjectName("buttonBox")  # Nombre importante para acceder después
    layout.addWidget(button_box)
    
    # Guardar referencias
    dialog.playlist_name_edit = name_edit
    dialog.buttonBox = button_box




def show_spotify_playlist_content(self, playlist_id, playlist_name):
    """Show Spotify playlist tracks in the tree widget"""
    if not hasattr(self, 'sp') or not self.sp:
        self.log("Spotify client not initialized")
        return
        
    try:
        # Clear the tree widget
        self.treeWidget.clear()
        
        # Create a root item for the playlist
        from PyQt6.QtWidgets import QTreeWidgetItem
        from PyQt6.QtCore import Qt
        
        root_item = QTreeWidgetItem(self.treeWidget)
        root_item.setText(0, playlist_name)
        root_item.setText(1, "Spotify")
        root_item.setText(2, "Playlist")
        
        # Make the root item bold
        font = root_item.font(0)
        font.setBold(True)
        root_item.setFont(0, font)
        root_item.setFont(1, font)
        
        # Set the Spotify icon explicitly
        root_item.setIcon(0, QIcon(":/services/spotify"))
        
        # Fetch tracks from Spotify
        results = api_call_with_retry(self, self.sp.playlist_items, playlist_id)
        

        # Add tracks as children of the root item
        for item in results['items']:
            if item['track']:
                track = item['track']
                
                track_item = QTreeWidgetItem(root_item)
                track_item.setText(0, track['name'])
                
                # Join artist names
                artists = [artist['name'] for artist in track['artists']]
                artist_str = ", ".join(artists)
                track_item.setText(1, artist_str)
                
                track_item.setText(2, "Canción")
                
                # Add duration if available
                if 'duration_ms' in track:
                    duration_ms = track['duration_ms']
                    minutes = int(duration_ms / 60000)
                    seconds = int((duration_ms % 60000) / 1000)
                    track_item.setText(4, f"{minutes}:{seconds:02d}")
                
                # Store track data for use with context menus, etc.
                track_data = {
                    'source': 'spotify',
                    'title': track['name'],
                    'artist': artist_str,
                    'url': track['external_urls']['spotify'],
                    'type': 'track',
                    'spotify_id': track['id']
                }
                
                # Store the data
                track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
        
        # Expand the root item
        root_item.setExpanded(True)
        
        self.log(f"Loaded {len(results['items'])} tracks from playlist '{playlist_name}'")
        
    except Exception as e:
        self.log(f"Error loading playlist content: {str(e)}")
        self.log(traceback.format_exc())


def _add_result_to_tree(self, result, parent_item):
    """
    Añade un resultado individual al árbol bajo el ítem padre especificado.
    """
    from PyQt6.QtWidgets import QTreeWidgetItem
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    
    # Crear el ítem para el resultado
    item = QTreeWidgetItem(parent_item)
    
    # Establecer texto en las columnas
    item.setText(0, result.get('title', ''))
    item.setText(1, result.get('artist', ''))
    item.setText(2, result.get('type', '').capitalize())
    
    # Añadir detalles adicionales
    if result.get('track_number'):
        item.setText(3, str(result['track_number']))
    elif result.get('year'):
        item.setText(3, str(result['year']))
    
    # Añadir duración si está disponible
    if 'duration' in result and result['duration']:
        from modules.submodules.url_playlist.ui_helpers import format_duration
        duration_str = format_duration(result['duration'])
        item.setText(4, duration_str)
    
    # Establecer el icono basado en la fuente
    source = result.get('source', 'unknown')
    if hasattr(self, 'service_icons') and source in self.service_icons:
        item.setIcon(0, self.service_icons[source])
    elif hasattr(self, 'get_source_icon'):
        item.setIcon(0, self.get_source_icon(result.get('url', ''), result))
    
    # Guardar los datos completos en el ítem
    item.setData(0, Qt.ItemDataRole.UserRole, result)
    
    return item


def load_rss_playlist_content_to_tree(self, playlist_data):
    """Carga el contenido de una playlist RSS en el treeWidget"""
    try:
        # Clear the tree widget first
        self.treeWidget.clear()
        
        self.log(f"Loading playlist data: {playlist_data}")
        
        # Crear item raíz para la playlist
        root_item = QTreeWidgetItem(self.treeWidget)
        root_item.setText(0, playlist_data['name'])
        root_item.setText(1, playlist_data.get('blog', 'Unknown'))
        root_item.setText(2, "Playlist")
        
        # Formatear como negrita
        font = root_item.font(0)
        font.setBold(True)
        root_item.setFont(0, font)
        
        # Añadir icono RSS
        root_item.setIcon(0, QIcon(":/services/rss"))
        
        # Almacenar datos para uso posterior
        root_item.setData(0, Qt.ItemDataRole.UserRole, playlist_data)
        
        # Ruta de la playlist
        playlist_path = playlist_data['path']
        self.log(f"Attempting to read playlist from: {playlist_path}")
        
        # Verify the path exists
        if not os.path.exists(playlist_path):
            self.log(f"ERROR: Playlist file not found: {playlist_path}")
            # Attempt to reconstruct the correct path
            if playlist_data.get('blog') and playlist_data.get('name'):
                corrected_path = Path(self.rss_pending_dir, playlist_data['blog'], playlist_data['name'])
                self.log(f"Trying corrected path: {corrected_path}")
                if os.path.exists(corrected_path):
                    playlist_path = corrected_path
                    # Update path in data
                    playlist_data['path'] = corrected_path
                    self.log(f"Using corrected path")
                else:
                    self.log(f"Corrected path also doesn't exist")
                    return False
            else:
                return False
        
        # Check for related titles file (.txt with same name as playlist)
        txt_path = os.path.splitext(playlist_path)[0] + '.txt'
        titles = []
        
        if os.path.exists(txt_path):
            self.log(f"Title file found: {txt_path}")
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                titles = [line.strip() for line in f.readlines()]
            self.log(f"Read {len(titles)} titles from file")
        else:
            self.log(f"No title file found at: {txt_path}")
        
        # Read the playlist file
        try:
            self.log(f"Reading playlist file: {playlist_path}")
            with open(playlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            self.log(f"Playlist contains {len(lines)} lines")
            
            # Process each line
            track_index = 0
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and comments/metadata
                if not line or line.startswith('#'):
                    continue
                
                # Parse the URL line
                self.log(f"Processing line: {line}")
                
                # Get title if available, otherwise use URL as title
                title = line
                if track_index < len(titles) and titles[track_index]:
                    title = titles[track_index]
                elif "youtube.com" in line or "youtu.be" in line:
                    # Extract video ID for a better title
                    import re
                    video_id = re.search(r'(?:v=|be/)([^&\?]+)', line)
                    if video_id:
                        title = f"YouTube Video: {video_id.group(1)}"
                
                # Create tree item for the track
                track_item = QTreeWidgetItem(root_item)
                track_item.setText(0, title)
                track_item.setText(1, playlist_data.get('blog', '')) # Blog as "artist"
                track_item.setText(2, "Track") # Type
                
                # Determine source and set appropriate icon
                source = determine_source_from_url(line)
                track_item.setIcon(0, get_source_icon(self, line, {'source': source}))
                
                # Store data for playback
                track_data = {
                    'title': title,
                    'url': line,
                    'type': 'track',
                    'source': source,
                    'blog': playlist_data.get('blog', ''),
                    'playlist': playlist_data.get('name', ''),
                    'parent_playlist': playlist_data
                }
                track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
                
                self.log(f"Added track item: {title}")
                track_index += 1
            
            # Expand the playlist item
            root_item.setExpanded(True)
            
            # Store current playlist data
            self.current_rss_playlist = playlist_data
            
            self.log(f"Loaded RSS playlist with {track_index} tracks")
            
            # Select the root item to ensure visibility
            self.treeWidget.setCurrentItem(root_item)
            
            # Make sure the tree is visible
            if hasattr(self, 'tabWidget'):
                # First, ensure we're in the correct tab
                for i in range(self.tabWidget.count()):
                    if hasattr(self, 'tree_container') and self.tree_container.isAncestorOf(self.treeWidget):
                        # If the tree is in the current tab, no need to switch tabs
                        pass
                    else:
                        # Otherwise, try to find the tab containing the tree
                        if i < self.tabWidget.count():
                            widget = self.tabWidget.widget(i)
                            if self.treeWidget.isVisible() and widget.isAncestorOf(self.treeWidget):
                                self.tabWidget.setCurrentIndex(i)
                                break
            
            return True
        except Exception as e:
            self.log(f"Error reading playlist file: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return False
            
    except Exception as e:
        self.log(f"Error loading RSS playlist content: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False


def _setup_service_checkboxes(parent_instance, dialog):
    """Set up service checkboxes based on current settings."""
    # Initialize the services dict if it doesn't exist
    if not hasattr(parent_instance, 'included_services'):
        parent_instance.included_services = {
            'youtube': True,
            'soundcloud': True,
            'bandcamp': True,
            'spotify': True,
            'lastfm': True,
            # Add more services as needed
        }
    
    # Map checkboxes to service keys
    checkbox_mapping = {
        'youtube_check': 'youtube',
        'soundcloud_check': 'soundcloud',
        'bandcamp_check': 'bandcamp',
        'spotify_check': 'spotify',
        'lastfm_check': 'lastfm'
        # Add more as needed
    }
    
    # Set checkbox states based on current settings
    for checkbox_name, service_key in checkbox_mapping.items():
        if hasattr(dialog, checkbox_name):
            checkbox = getattr(dialog, checkbox_name)
            # Convert string 'True'/'False' to actual boolean if needed
            value = parent_instance.included_services.get(service_key, True)
            if isinstance(value, str):
                value = value.lower() == 'true'
            checkbox.setChecked(value)

    # Set the urlplaylist_only_local checkbox
    only_local_checkbox = dialog.findChild(QCheckBox, 'urlplaylist_only_local')
    if only_local_checkbox:
        # Set state from parent instance
        only_local_checkbox.setChecked(parent_instance.urlplaylist_only_local)
        parent_instance.log(f"Setting urlplaylist_only_local checkbox to: {parent_instance.urlplaylist_only_local}")
    else:
        parent_instance.log("urlplaylist_only_local checkbox not found in dialog")

    # Set the playlist view radio buttons
    if hasattr(dialog, 'pl_unidas') and hasattr(dialog, 'pl_separadas'):
        unified_view = getattr(parent_instance, 'playlist_unified_view', False)
        # Convertir a booleano si es string
        if isinstance(unified_view, str):
            unified_view = unified_view.lower() == 'true'
        dialog.pl_unidas.setChecked(unified_view)
        dialog.pl_separadas.setChecked(not unified_view)
    
    # Set the playlist visibility checkboxes
    if hasattr(dialog, 'locale_checkbox'):
        show_local = getattr(parent_instance, 'show_local_playlists', True)
        if isinstance(show_local, str):
            show_local = show_local.lower() == 'true'
        dialog.locale_checkbox.setChecked(show_local)
    
    if hasattr(dialog, 'sp_checkbox'):
        show_spotify = getattr(parent_instance, 'show_spotify_playlists', True)
        if isinstance(show_spotify, str):
            show_spotify = show_spotify.lower() == 'true'
        dialog.sp_checkbox.setChecked(show_spotify)
    
    if hasattr(dialog, 'blogs_checkbox'):
        show_rss = getattr(parent_instance, 'show_rss_playlists', True)
        if isinstance(show_rss, str):
            show_rss = show_rss.lower() == 'true'
        dialog.blogs_checkbox.setChecked(show_rss)



def display_wiki_info(self, result_data):
    """Muestra información detallada del elemento en el panel info_wiki de forma asíncrona"""
    try:
        # Verificar que el textEdit existe
        if not hasattr(self, 'info_wiki_textedit') or not self.info_wiki_textedit:
            self.log("Error: No se encontró el widget info_wiki_textedit")
            return
        
        # Verificar datos mínimos
        if not result_data or not isinstance(result_data, dict):
            self.info_wiki_textedit.setHtml("<h2>Error</h2><p>No hay datos válidos para mostrar.</p>")
            return
        
        # Mostrar un mensaje de carga
        loading_html = """
        <div style="text-align: center; margin-top: 50px;">
            <h2>Cargando información...</h2>
            <div class="loader" style="
                border: 16px solid #f3f3f3;
                border-radius: 50%;
                border-top: 16px solid #3498db;
                width: 120px;
                height: 120px;
                animation: spin 2s linear infinite;
                margin: 20px auto;
            "></div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
            <p>Obteniendo información detallada...</p>
        </div>
        """
        self.info_wiki_textedit.setHtml(loading_html)
        
        # Cambiar al tab de info_wiki para mostrar la información
        if hasattr(self, 'tabWidget') and self.tabWidget:
            # Buscar el índice del tab info_wiki
            for i in range(self.tabWidget.count()):
                if self.tabWidget.tabText(i) == "Info Wiki":
                    self.tabWidget.setCurrentIndex(i)
                    break
        
        # Extraer datos básicos del elemento
        item_type = result_data.get('type', '').lower()
        title = result_data.get('title', '')
        artist = result_data.get('artist', '')
        album = result_data.get('album', '')
        
        if not (title or artist):
            self.info_wiki_textedit.setHtml("<h2>Información no disponible</h2><p>No hay suficientes datos para mostrar información detallada.</p>")
            return
        
        # Crear y configurar el worker para carga asíncrona
        from modules.submodules.url_playlist.search_workers import InfoLoadWorker

        worker = InfoLoadWorker(
            item_type=item_type, 
            title=title, 
            artist=artist, 
            album=album,  # Pass album parameter
            db_path=self.db_path, 
            basic_data=result_data  # Pass the basic data to the worker
        )
        
        # Definir funciones callback para conectar a las señales del worker
        def on_results_received(results):
            if results:
                self.log(f"Recibida información detallada: {len(results)} resultados")
        
        def on_error_occurred(error_msg):
            self.log(f"Error al cargar información: {error_msg}")
            self.info_wiki_textedit.setHtml(f"<h2>Error</h2><p>{error_msg}</p>")
        
        def on_loading_finished(result, basic_data):
            try:
                item_type = basic_data.get('type', '').lower()
                title = basic_data.get('title', '')
                artist = basic_data.get('artist', '')
                album = basic_data.get('album', '')
                
                # Generate HTML to display the information with enhanced format
                if item_type == 'artist':
                    # Only show artist name
                    html_content = f"<h2>{artist}</h2>"
                elif item_type == 'album':
                    # Show album by artist in one line
                    html_content = f"<h2>{title} por {artist}</h2>"
                elif item_type in ['track', 'song']:
                    # Show song from album by artist
                    album_text = f" del álbum {album}" if album else ""
                    html_content = f"<h2>{title}{album_text} por {artist}</h2>"
                else:
                    # General format for other types
                    html_content = f"<h2>{title}</h2>"
                    if artist:
                        html_content += f"<h3>por {artist}</h3>"
                
                html_content += "<hr>"
                
                # Dictionary to store all links found
                all_links = {}
                
                # Special handling for Bandcamp content
                if basic_data.get('source', '').lower() == 'bandcamp':
                    if item_type == 'artist':
                        # Show Bandcamp artist info
                        html_content += "<h3>Bandcamp Artist</h3>"
                        
                        # List albums if available
                        if 'albums' in basic_data and basic_data['albums']:
                            html_content += f"<h3>Albums ({len(basic_data['albums'])})</h3>"
                            html_content += "<ul>"
                            for album in basic_data['albums']:
                                album_year = f" ({album.get('year')})" if album.get('year') else ""
                                html_content += f"<li><a href='{album.get('url', '#')}'>{album.get('title', 'Unknown Album')}</a>{album_year}</li>"
                            html_content += "</ul>"
                    
                    elif item_type == 'album':
                        # Show Bandcamp album info
                        html_content += "<h3>Bandcamp Album</h3>"
                        
                        if basic_data.get('year'):
                            html_content += f"<p><b>Year:</b> {basic_data['year']}</p>"
                        
                        # List tracks if available
                        if 'tracks' in basic_data and basic_data['tracks']:
                            html_content += f"<h3>Tracks ({len(basic_data['tracks'])})</h3>"
                            html_content += "<ol>"
                            for track in basic_data['tracks']:
                                duration_str = format_duration(track.get('duration', 0))
                                html_content += f"<li><a href='{track.get('url', '#')}'>{track.get('title', 'Unknown Track')}</a> ({duration_str})</li>"
                            html_content += "</ol>"
                    
                    elif item_type in ['track', 'song']:
                        # Show Bandcamp track info
                        html_content += "<h3>Bandcamp Track</h3>"
                        
                        if basic_data.get('duration'):
                            duration_str = format_duration(basic_data.get('duration', 0))
                            html_content += f"<p><b>Duration:</b> {duration_str}</p>"
                        
                        if basic_data.get('track_number'):
                            html_content += f"<p><b>Track Number:</b> {basic_data['track_number']}</p>"
                
                # Format info according to type
                if item_type == 'artist':
                    # Artist data
                    if result and 'artist_info' in result:
                        # Replace with proper function for formatting artist info
                        html_content += "<h3>Artist Info</h3>"
                        for key, value in result['artist_info'].items():
                            if value and key not in ['id', 'name']:
                                html_content += f"<p><b>{key.capitalize()}:</b> {value}</p>"
                    
                    # Wikipedia content
                    if result and result.get('wiki_content'):
                        html_content += "<h3>Wikipedia</h3>"
                        html_content += f"<p>{result['wiki_content'][:500]}...</p>"
                        
                    # Genres
                    if result and result.get('genres'):
                        html_content += "<h3>Genres</h3>"
                        html_content += "<ul>"
                        for genre in result['genres']:
                            html_content += f"<li>{genre}</li>"
                        html_content += "</ul>"
                    
                    # Store links for later display
                    if result and result.get('artist_links'):
                        all_links['artist_links'] = result['artist_links']
                    
                elif item_type == 'album':
                    # Album data
                    if result and 'album_info' in result:
                        # Replace with proper function for formatting album info
                        html_content += "<h3>Album Info</h3>"
                        for key, value in result['album_info'].items():
                            if value and key not in ['id', 'name', 'songs']:
                                html_content += f"<p><b>{key.capitalize()}:</b> {value}</p>"
                    
                    # Wikipedia content
                    if result and result.get('wiki_content'):
                        html_content += "<h3>Wikipedia</h3>"
                        html_content += f"<p>{result['wiki_content'][:500]}...</p>"
                    
                    # Store links for later display
                    if result and result.get('album_links'):
                        all_links['album_links'] = result['album_links']
                    
                elif item_type in ['track', 'song']:
                    # Song data
                    if result and result.get('song_info'):
                        # Replace with proper function for formatting song info
                        html_content += "<h3>Song Info</h3>"
                        for key, value in result['song_info'].items():
                            if value and key not in ['id', 'title']:
                                html_content += f"<p><b>{key.capitalize()}:</b> {value}</p>"
                    else:
                        html_content += "<p>No detailed song information found.</p>"
                    
                    # Related album data
                    if result and result.get('album_info'):
                        html_content += "<h3>Album Information</h3>"
                        for key, value in result['album_info'].items():
                            if value and key not in ['id', 'name', 'songs']:
                                html_content += f"<p><b>{key.capitalize()}:</b> {value}</p>"
                    
                    # Store links for later display
                    if result and result.get('track_links'):
                        all_links['track_links'] = result['track_links']
                    if result and result.get('album_links'):
                        all_links['album_links'] = result['album_links']
                
                # Links from services (Spotify, Bandcamp, etc.)
                if all_links:
                    html_content += "<h3>Links</h3><ul>"
                    for link_type, links in all_links.items():
                        for service, url in links.items():
                            if url:
                                html_content += f"<li><a href='{url}'>{service.capitalize()}</a></li>"
                    html_content += "</ul>"
                
                # Set HTML content
                self.info_wiki_textedit.setHtml(html_content)
                
            except Exception as e:
                self.log(f"Error processing loaded information: {str(e)}")
                import traceback
                self.log(traceback.format_exc())
                self.info_wiki_textedit.setHtml(f"<h2>Error</h2><p>An error occurred while processing the information: {str(e)}</p>")
        
        # Conectar señales
        worker.signals.results.connect(on_results_received)
        worker.signals.error.connect(on_error_occurred)
        worker.signals.finished.connect(on_loading_finished)
        
        # Iniciar el worker
        QThreadPool.globalInstance().start(worker)
        
    except Exception as e:
        self.log(f"Error al preparar carga de información: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        self.info_wiki_textedit.setHtml(f"<h2>Error</h2><p>Se produjo un error al cargar la información: {str(e)}</p>")

def process_detailed_results(self, results):
        """Process the detailed results from the worker."""
        if results:
            # Handle the results if needed
            self.log(f"Received {len(results)} detailed results")

def handle_info_load_error(self, error_msg):
    """Handle errors from the info load worker."""
    self.log(f"Info load error: {error_msg}")
    self.info_wiki_textedit.setHtml(f"<h2>Error</h2><p>{error_msg}</p>")




def on_info_load_finished(self, result, basic_data):
    """Callback when information loading is complete."""
    try:
        item_type = basic_data.get('type', '').lower()
        title = basic_data.get('title', '')
        artist = basic_data.get('artist', '')
        album = basic_data.get('album', '')
        
        # Generate HTML to display the information with enhanced format
        if item_type == 'artist':
            # Only show artist name
            html_content = f"<h2>{artist}</h2>"
        elif item_type == 'album':
            # Show album by artist in one line
            html_content = f"<h2>{title} por {artist}</h2>"
        elif item_type in ['track', 'song']:
            # Show song from album by artist
            album_text = f" del álbum {album}" if album else ""
            html_content = f"<h2>{title}{album_text} por {artist}</h2>"
        else:
            # General format for other types
            html_content = f"<h2>{title}</h2>"
            if artist:
                html_content += f"<h3>por {artist}</h3>"
        
        html_content += "<hr>"
        
        # Dictionary to store all links found
        all_links = {}
        
        # Special handling for Bandcamp content
        if basic_data.get('source', '').lower() == 'bandcamp':
            if item_type == 'artist':
                # Show Bandcamp artist info
                html_content += "<h3>Bandcamp Artist</h3>"
                
                # List albums if available
                if 'albums' in basic_data and basic_data['albums']:
                    html_content += f"<h3>Albums ({len(basic_data['albums'])})</h3>"
                    html_content += "<ul>"
                    for album in basic_data['albums']:
                        album_year = f" ({album.get('year')})" if album.get('year') else ""
                        html_content += f"<li><a href='{album.get('url', '#')}'>{album.get('title', 'Unknown Album')}</a>{album_year}</li>"
                    html_content += "</ul>"
            
            elif item_type == 'album':
                # Show Bandcamp album info
                html_content += "<h3>Bandcamp Album</h3>"
                
                if basic_data.get('year'):
                    html_content += f"<p><b>Year:</b> {basic_data['year']}</p>"
                
                # List tracks if available
                if 'tracks' in basic_data and basic_data['tracks']:
                    html_content += f"<h3>Tracks ({len(basic_data['tracks'])})</h3>"
                    html_content += "<ol>"
                    for track in basic_data['tracks']:
                        duration_str = self.format_duration(track.get('duration', 0))
                        html_content += f"<li><a href='{track.get('url', '#')}'>{track.get('title', 'Unknown Track')}</a> ({duration_str})</li>"
                    html_content += "</ol>"
            
            elif item_type in ['track', 'song']:
                # Show Bandcamp track info
                html_content += "<h3>Bandcamp Track</h3>"
                
                if basic_data.get('duration'):
                    duration_str = self.format_duration(basic_data.get('duration', 0))
                    html_content += f"<p><b>Duration:</b> {duration_str}</p>"
                
                if basic_data.get('track_number'):
                    html_content += f"<p><b>Track Number:</b> {basic_data['track_number']}</p>"
        
        # Format info according to type
        if item_type == 'artist':
            # Artist data
            if 'artist_info' in result:
                html_content += self.format_artist_info(result['artist_info'])
            
            # Wikipedia content
            if result.get('wiki_content'):
                html_content += "<h3>Wikipedia</h3>"
                html_content += f"<p>{self.format_large_text(result['wiki_content'])}</p>"
                
            # Genres
            if result.get('genres'):
                html_content += "<h3>Genres</h3>"
                html_content += "<ul>"
                for genre in result['genres']:
                    html_content += f"<li>{genre}</li>"
                html_content += "</ul>"
            
            # Store links for later display
            if result.get('artist_links'):
                all_links['artist_links'] = result['artist_links']
                
            # Update the tree with albums if available
            if result.get('albums'):
                self.add_artist_albums_to_tree(artist, result['albums'])
            
        elif item_type == 'album':
            # Album data
            if 'album_info' in result:
                html_content += self.format_album_info(result['album_info'])
            
            # Wikipedia content
            if result.get('wiki_content'):
                html_content += "<h3>Wikipedia</h3>"
                html_content += f"<p>{self.format_large_text(result['wiki_content'])}</p>"
            
            # Store links for later display
            if result.get('album_links'):
                all_links['album_links'] = result['album_links']
                
            # Update tree with songs if available
            if result.get('album_info') and result['album_info'].get('songs'):
                self.add_album_songs_to_tree(artist, title, result['album_info']['songs'])
            
        elif item_type in ['track', 'song']:
            # Song data - With None handling for song_info
            if result.get('song_info'):
                html_content += self.format_song_info(result['song_info'])
            else:
                html_content += "<p>No detailed song information found.</p>"
            
            # Related album data
            if result.get('album_info'):
                html_content += "<h3>Album Information</h3>"
                html_content += self.format_album_info(result['album_info'])
            
            # Store links for later display
            if result.get('track_links'):
                all_links['track_links'] = result['track_links']
            if result.get('album_links'):
                all_links['album_links'] = result['album_links']
        
        # Links from active services
        html_content += self.format_available_links(basic_data, all_links)
        
        # Set HTML content
        self.info_wiki_textedit.setHtml(html_content)
        
    except Exception as e:
        self.log(f"Error processing loaded information: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        self.info_wiki_textedit.setHtml(f"<h2>Error</h2><p>An error occurred while processing the information: {str(e)}</p>")



def get_service_priority(self):
    """Get the service priority from settings"""
    try:
        # Default priority
        default_priority = ['youtube', 'spotify', 'bandcamp', 'soundcloud']
        
        # Check if we have the combo boxes in settings
        combo1 = self.findChild(QComboBox, 'comboBox_1')
        combo2 = self.findChild(QComboBox, 'comboBox_2')
        combo3 = self.findChild(QComboBox, 'comboBox_3')
        combo4 = self.findChild(QComboBox, 'comboBox_4')
        
        if all([combo1, combo2, combo3, combo4]):
            # Get the selected services
            service1 = combo1.currentText().lower()
            service2 = combo2.currentText().lower()
            service3 = combo3.currentText().lower()
            service4 = combo4.currentText().lower()
            
            # Create priority list
            priority = [service1, service2, service3, service4]
            
            # Validate that we have valid services
            valid_services = ['youtube', 'spotify', 'bandcamp', 'soundcloud']
            validated_priority = [s for s in priority if s in valid_services]
            
            # Make sure all required services are included
            for service in valid_services:
                if service not in validated_priority:
                    validated_priority.append(service)
            
            return validated_priority
        else:
            return default_priority
    except Exception as e:
        self.log(f"Error getting service priority: {str(e)}")
        return ['youtube', 'spotify', 'bandcamp', 'soundcloud']



def show_tree_context_menu(self, position):
    """Show context menu for tree widget items with specific options based on item type"""
    # Get the item at this position
    item = self.treeWidget.itemAt(position)
    if not item:
        return
        
    # Get the item data
    item_data = item.data(0, Qt.ItemDataRole.UserRole)
    if not item_data:
        return
    
    # Create the menu
    menu = QMenu(self)
    
    # Different options based on item type
    if isinstance(item_data, dict) and 'type' in item_data:
        if item_data['type'] == 'track':
            # Track options
            play_action = menu.addAction("Reproducir")
            add_to_queue_action = menu.addAction("Añadir a cola")
            menu.addSeparator()
            copy_url_action = menu.addAction("Copiar URL")
            
            # Spotify option if available
            if hasattr(self, 'spotify_authenticated') and self.spotify_authenticated:
                menu.addSeparator()
                add_to_spotify_action = menu.addAction("Añadir a playlist de Spotify")
        
        elif item_data['type'] == 'playlist' and 'blog' in item_data and 'state' in item_data:
            # Playlist options
            play_playlist_action = menu.addAction("Reproducir playlist")
            add_all_to_queue_action = menu.addAction("Añadir todo a cola")
            menu.addSeparator()
            
            # Solo mostrar opción de marcar como escuchada si está pendiente
            if item_data['state'] == 'pending':
                mark_listened_action = menu.addAction("Marcar como escuchada")
    
    # Show the menu and handle the selected action
    action = menu.exec(self.treeWidget.mapToGlobal(position))
    
    if not action:
        return
        
    # Handle actions based on item type
    if isinstance(item_data, dict) and 'type' in item_data:
        if item_data['type'] == 'track':
            if action == play_action:
                self.play_item(item)
            elif action == add_to_queue_action:
                add_item_to_queue(self, item)
            elif action == copy_url_action:
                # Actualizar para usar 'url' de track_data
                track_url = item_data.get('url', '')
                self.copy_text_to_clipboard(track_url)
            elif hasattr(self, 'spotify_authenticated') and self.spotify_authenticated and action == add_to_spotify_action:
                self.add_to_spotify_playlist(item_data)
                
        elif item_data['type'] == 'playlist':
            if action == play_playlist_action:
                self.play_rss_playlist(item_data)
            elif action == add_all_to_queue_action:
                self.add_rss_playlist_to_queue(item)
            elif 'state' in item_data and item_data['state'] == 'pending' and action == mark_listened_action:
                self.move_rss_playlist_to_listened(item_data)


def on_tree_selection_changed(self):
    """Handle selection changes in the tree widget with optimized loading"""
    try:
        # Get the current selected item
        selected_items = self.treeWidget.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        
        # Get the data associated with the item
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Cancelar carga anterior si existe
        if hasattr(self, '_info_load_timer') and self._info_load_timer.isActive():
            self._info_load_timer.stop()
        
        # Programar la carga con un pequeño retraso para evitar cargas innecesarias
        # si el usuario está desplazándose rápidamente entre elementos
        from PyQt6.QtCore import QTimer
        self._info_load_timer = QTimer(self)
        self._info_load_timer.setSingleShot(True)
        self._info_load_timer.timeout.connect(lambda: _load_item_info(self, item_data))
        self._info_load_timer.start(150)  # 150ms de retraso
        
    except Exception as e:
        self.log(f"Error handling tree selection change: {str(e)}")

def _load_item_info(self, item_data):
    """Load item info with optimized caching"""
    try:
        if not item_data:
            return
            
        # Usar caché si disponible
        cache_key = f"{item_data.get('type', '')}-{item_data.get('artist', '')}-{item_data.get('title', '')}"
        
        if hasattr(self, '_info_cache') and cache_key in self._info_cache:
            self.log(f"Usando información en caché para {cache_key}")
            info = self._info_cache[cache_key]
            # Mostrar la información en caché
            self.display_cached_info(info, item_data)
            return
            
        # Display information about the selected item without changing tabs
        if hasattr(self, 'textEdit'):
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
            
        # Cargar información detallada en segundo plano
        from modules.submodules.url_playlist.ui_helpers import display_wiki_info
        display_wiki_info(self, item_data)
        
    except Exception as e:
        self.log(f"Error loading item info: {str(e)}")