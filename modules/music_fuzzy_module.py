from PyQt6.QtWidgets import QWidget, QTreeWidgetItem, QPushButton, QLabel, QVBoxLayout, QCheckBox, QStackedWidget, QGroupBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
import os
import sqlite3
from base_module import BaseModule, PROJECT_ROOT
from pathlib import Path
import resources_rc
# Import submodules (adjust paths as needed based on your project structure)

from modules.submodules.fuzzy.search_handler import SearchHandler
from modules.submodules.fuzzy.database_manager import DatabaseManager
from modules.submodules.fuzzy.ui_updater import UIUpdater
from modules.submodules.fuzzy.link_manager import LinkManager

class MusicFuzzyModule(BaseModule):
    """Music browser module with fuzzy search capabilities."""
    
    # Señal que se emitirá cuando la UI esté inicializada
    ui_initialized = pyqtSignal()


    def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
        # Inicializar propiedades básicas antes de super().__init__
        self.db_path = kwargs.get('db_path', Path(Path.home(), '.local', 'share', 'music_app', 'music.db'))
        
        # Get config-related parameters
        self.config_path = kwargs.get('config_path', Path(PROJECT_ROOT, "config", "config.yml"))
        
        # Obtener el estado del only_local_files directamente de los kwargs
        # Esto obtiene el valor del archivo de configuración
        
        self.only_local_files_state = kwargs.get('only_local_files', False)
        
        # Convertir a booleano si es string
        if isinstance(self.only_local_files_state, str):
            self.only_local_files_state = self.only_local_files_state.lower() == 'true'
        
        print(f"Estado inicial de 'only_local_files' desde config: {self.only_local_files_state}")
        
        # Llamar a super().__init__ para cargar la UI
        super().__init__(parent, theme, **kwargs)
        
        # Inicializar componentes después de cargar la UI
        self.db_manager = DatabaseManager(self.db_path)
        self.search_handler = SearchHandler(self)
        self.ui_updater = UIUpdater(self)
        self.link_manager = LinkManager(self)
        
        # Conectar señales adicionales después de inicializar todos los componentes
        self._connect_additional_signals()
        
        # Configurar el estado del filtro de "solo archivos locales" independientemente del widget
        self.search_handler.set_only_local(self.only_local_files_state)
        
    def init_ui(self):
        """Initialize UI from the .ui file"""
        ui_file_name = "fuzzy/music_fuzzy_module.ui"
        if self.load_ui_file(ui_file_name):
            # Set up tree widget
            self.results_tree_widget.setHeaderLabels(["Artista / Álbum / Canción", "Año", "Género"])
            self.results_tree_widget.setColumnWidth(0, 300)
            self.results_tree_widget.setColumnWidth(1, 60)
            self.results_tree_widget.setColumnWidth(2, 100)
            
            # Ensure the advanced settings container exists
            self._ensure_widget_exists('advanced_settings_container')
            
            # Verificar y acceder a todos los widgets importantes
            # Group boxes
            self._ensure_widget_exists('artist_group')
            self._ensure_widget_exists('album_group')
            self._ensure_widget_exists('lastfm_bio_group')
            self._ensure_widget_exists('lyrics_group')
            
            # Link groups
            self._ensure_widget_exists('artist_links_group')
            self._ensure_widget_exists('album_links_group')
            
            # Labels para contenido e imágenes
            self._ensure_widget_exists('lyrics_label')
            self._ensure_widget_exists('cover_label')
            self._ensure_widget_exists('artist_image_label')
            
            # Conectar señales después de inicializar la UI
            self._connect_signals()
            
            # Check if the advanced_settings_check exists and connect it
            self._ensure_widget_exists('advanced_settings_check')
            if hasattr(self, 'advanced_settings_check') and self.advanced_settings_check:
                self.advanced_settings_check.toggled.connect(self._toggle_advanced_settings)
            
            # Ensure we have references to the stacked widget pages
            self._ensure_widget_exists('info_panel_stacked')
            if hasattr(self, 'info_panel_stacked'):
                # Get references to the pages
                self.info_page = self.info_panel_stacked.findChild(QWidget, "info_page")
                self.feeds_page = self.info_panel_stacked.findChild(QWidget, "feeds_page")

            # Ensure we have a reference to the feeds groupbox
            self._ensure_widget_exists('feeds_groupbox')


            # Emitir señal de que la UI está inicializada
            self.ui_initialized.emit()
            
            return True
        else:
            print(f"Error loading UI file: {ui_file_name}")
            return False

    def _ensure_widget_exists(self, widget_name):
        """Asegurarse de que un widget existe y está accesible."""
        if not hasattr(self, widget_name):
            # Intentar encontrarlo usando findChild
            from PyQt6.QtWidgets import QWidget
            widget = self.findChild(QWidget, widget_name)
            if widget:
                setattr(self, widget_name, widget)
                print(f"Widget '{widget_name}' encontrado y asignado")
            else:
                print(f"WARNING: Widget '{widget_name}' no encontrado")
    
    def _connect_signals(self):
        """Connect basic UI signals (llamado desde init_ui)"""
        # Conexiones básicas que no dependen de componentes externos
        if hasattr(self, 'advanced_settings_check'):
            self.advanced_settings_check.toggled.connect(self._toggle_advanced_settings)
        
        if hasattr(self, 'results_tree_widget'):
            self.results_tree_widget.itemClicked.connect(self._handle_item_clicked)

        if hasattr(self, 'feeds_button'):
            self.feeds_button.clicked.connect(self._toggle_feeds_view)
            
        # Conectar los botones de navegación de feeds
        self._connect_feed_tab_buttons()


    def _connect_feed_tab_buttons(self):
        """Connect the feed tab navigation buttons."""
        artists_button = self.findChild(QPushButton, "artists_pushButton")
        albums_button = self.findChild(QPushButton, "albums_pushButton")
        menciones_button = self.findChild(QPushButton, "menciones_pushButton")
        stack_widget = self.findChild(QStackedWidget, "stackedWidget_feeds")
        
        if artists_button and albums_button and menciones_button and stack_widget:
            # Connect buttons to switch between feed tabs
            artists_button.clicked.connect(lambda: stack_widget.setCurrentIndex(0))
            albums_button.clicked.connect(lambda: stack_widget.setCurrentIndex(1))
            menciones_button.clicked.connect(lambda: stack_widget.setCurrentIndex(2))

    def _connect_additional_signals(self):
        """Connect signals that depend on initialized components"""
        # Conexiones que dependen de componentes como search_handler
        if hasattr(self, 'search_box') and hasattr(self, 'search_handler'):
            self.search_box.textChanged.connect(self.search_handler.perform_search)
            #self.search_box.returnPressed.connect(self.search_handler.perform_search)
        
        # El checkbox ya debería estar conectado en _load_advanced_settings_ui
        print(f"Señales adicionales conectadas correctamente")


    def _load_advanced_settings_ui(self):
        """Carga la UI de configuración avanzada independientemente de su visibilidad"""
        if not hasattr(self, 'advanced_settings_container') or not self.advanced_settings_container:
            print("No se encontró el contenedor de ajustes avanzados")
            return
            
        # Si ya tiene un layout, probablemente ya está cargado
        if self.advanced_settings_container.layout():
            return
            
        try:
            # Crear un layout si no existe
            layout = QVBoxLayout(self.advanced_settings_container)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Crear un widget para los ajustes avanzados
            advanced_widget = QWidget()
            
            # Cargar archivo UI
            ui_path = Path(PROJECT_ROOT, "ui", "fuzzy", "music_fuzzy_advanced_settings.ui")
            if os.path.exists(ui_path):
                from PyQt6 import uic
                uic.loadUi(ui_path, advanced_widget)
                
                # Añadir widget al layout
                layout.addWidget(advanced_widget)
                
                # Obtener referencia al checkbox
                self.only_local_files = advanced_widget.findChild(QCheckBox, "only_local_files")
                
                if self.only_local_files:
                    print("Checkbox 'only_local_files' encontrado")
                    # Desconectar primero para evitar conexiones duplicadas
                    try:
                        self.only_local_files.toggled.disconnect()
                    except:
                        pass
                        
                    # Conectar señales
                    self.only_local_files.toggled.connect(self.search_handler.perform_search)
                    self.only_local_files.toggled.connect(self._save_checkbox_state)
                    
                    # Establecer el estado inicial desde la configuración cargada en __init__
                    print(f"Estableciendo estado inicial del checkbox: {self.only_local_files_state}")
                    self.only_local_files.setChecked(bool(self.only_local_files_state))
                else:
                    print("WARNING: Checkbox 'only_local_files' no encontrado en el archivo UI")
                    # Crearlo programáticamente como fallback
                    self.only_local_files = QCheckBox("Mostrar solo archivos locales")
                    layout.addWidget(self.only_local_files)
                    self.only_local_files.toggled.connect(self.search_handler.perform_search)
                    self.only_local_files.toggled.connect(self._save_checkbox_state)
                    self.only_local_files.setChecked(bool(self.only_local_files_state))
            else:
                print(f"Archivo UI de ajustes avanzados no encontrado: {ui_path}")
                # Crear una UI básica como fallback
                self.only_local_files = QCheckBox("Mostrar solo archivos locales")
                layout.addWidget(self.only_local_files)
                self.only_local_files.toggled.connect(self.search_handler.perform_search)
                self.only_local_files.toggled.connect(self._save_checkbox_state)
                self.only_local_files.setChecked(bool(self.only_local_files_state))
                
        except Exception as e:
            print(f"Error cargando UI de ajustes avanzados: {e}")
            import traceback
            traceback.print_exc()


    def _toggle_advanced_settings(self, checked):
        """Toggle advanced settings container visibility and load UI if needed."""
        if hasattr(self, 'advanced_settings_container'):
            # Verify if we already loaded the content
            if checked and not self.advanced_settings_container.layout():
                try:
                    # Create a layout if it doesn't exist yet
                    layout = QVBoxLayout(self.advanced_settings_container)
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    # Create a widget for advanced settings
                    advanced_widget = QWidget()
                    
                    # Load UI file
                    ui_path = Path(PROJECT_ROOT, "ui", "fuzzy", "music_fuzzy_advanced_settings.ui")
                    if os.path.exists(ui_path):
                        from PyQt6 import uic
                        uic.loadUi(ui_path, advanced_widget)
                        
                        # Add widget to layout
                        layout.addWidget(advanced_widget)
                        
                        # Get reference to the checkbox
                        self.only_local_files = advanced_widget.findChild(QCheckBox, "only_local_files")
                        
                        if self.only_local_files:
                            print("Found only_local_files checkbox")
                            
                            # Establecer el estado basado en la configuración
                            self.only_local_files.setChecked(self.only_local_files_state)
                            
                            # Connect to search and to save config
                            self.only_local_files.toggled.connect(self._on_only_local_toggled)
                        else:
                            print("WARNING: Checkbox 'only_local_files' not found in the UI file")
                            # Create it programmatically as a fallback
                            self.only_local_files = QCheckBox("Show only local files")
                            layout.addWidget(self.only_local_files)
                            self.only_local_files.setChecked(self.only_local_files_state)
                            self.only_local_files.toggled.connect(self._on_only_local_toggled)
                    else:
                        print(f"Advanced settings UI file not found: {ui_path}")
                        # Create a basic UI programmatically as fallback
                        self.only_local_files = QCheckBox("Show only local files")
                        layout.addWidget(self.only_local_files)
                        self.only_local_files.setChecked(self.only_local_files_state)
                        self.only_local_files.toggled.connect(self._on_only_local_toggled)
                    
                except Exception as e:
                    print(f"Error loading advanced settings UI: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Show/hide the container based on checkbox state
            self.advanced_settings_container.setVisible(checked)
        

    def _on_only_local_toggled(self, checked):
        """Handle checkbox state change - update search and save config"""
        # Actualizar nuestra variable de estado
        self.only_local_files_state = checked
        
        # Actualizar el estado en el search handler
        if hasattr(self, 'search_handler'):
            self.search_handler.set_only_local(checked)
        
        # Realizar búsqueda (si es necesario) 
        if hasattr(self, 'search_handler'):
            self.search_handler.perform_search()
        
        # Guardar configuración
        self._save_checkbox_state(checked)


    def _setup_link_buttons(self):
        """Initially hide all link buttons"""
        # Artist links
        for child in self.artist_links_group.findChildren(QPushButton):
            child.setVisible(False)
            
        # Album links
        for child in self.album_links_group.findChildren(QPushButton):
            child.setVisible(False)
    

    def _handle_item_clicked(self, item, column):
        """Handle clicks on tree widget items"""
        # Get item data
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if item_data is None:
            print("No item data found")
            return
                
        item_type = item_data.get('type')
        item_id = item_data.get('id')
        
        if not item_type or not item_id:
            print(f"Invalid item data: {item_data}")
            return
        
        print(f"Handling click on {item_type} with ID: {item_id}")
        
        try:
            if item_type == 'artist':
                self.ui_updater.update_artist_view(item_id)
            elif item_type == 'album':
                self.ui_updater.update_album_view(item_id)
            elif item_type == 'song':
                self.ui_updater.update_song_view(item_id)
            else:
                print(f"Unhandled item type: {item_type}")
        except Exception as e:
            print(f"Error handling item click: {e}")
            import traceback
            traceback.print_exc()




    def _load_checkbox_state(self):
        """Load the checkbox state from config file"""
        if not hasattr(self, 'only_local_files') or self.only_local_files is None:
            return
        
        try:
            # Try to import from main.py to reuse existing function
            from main import load_config_file
            
            config = load_config_file(self.config_path)
            if not config:
                return
            
            # Check if our module has specific settings
            for module_config in config.get('modules', []):
                if module_config.get('name') == 'Music Browser':
                    # Get checkbox state from module config
                    only_local = module_config.get('args', {}).get('only_local_files', self.only_local_files_default)
                    
                    # Convert string to boolean if needed
                    if isinstance(only_local, str):
                        only_local = only_local.lower() == 'true'
                    
                    # Set checkbox state
                    self.only_local_files.setChecked(bool(only_local))
                    print(f"Loaded 'only_local_files' state: {only_local}")
                    return
        except Exception as e:
            print(f"Error loading checkbox state: {e}")
            import traceback
            traceback.print_exc()

    def _save_checkbox_state(self, state):
        """Save the checkbox state to config file"""
        try:
            # Import functions from main.py to reuse existing code
            from main import load_config_file, save_config_file
            
            # Load current config
            config = load_config_file(self.config_path)
            if not config:
                print("Failed to load config file")
                return
            
            # Find our module in the config
            for module_config in config.get('modules', []):
                if module_config.get('name') == 'Music Browser':
                    # Create args dict if it doesn't exist
                    if 'args' not in module_config:
                        module_config['args'] = {}
                    
                    # Update checkbox state
                    module_config['args']['only_local_files'] = state
                    print(f"Saving 'only_local_files' state: {state}")
                    
                    # Save config file
                    save_config_file(self.config_path, config)
                    return
            
            print("Module 'Music Browser' not found in config")
        except Exception as e:
            print(f"Error saving checkbox state: {e}")
            import traceback
            traceback.print_exc()

    def _toggle_feeds_view(self):
        """Alterna entre las 3 vistas: info, feeds y más_info."""
        if not hasattr(self, 'info_panel_stacked') or not self.info_panel_stacked:
            return
        
        # Obtener la página actual y el número total de páginas
        current_index = self.info_panel_stacked.currentIndex()
        total_pages = self.info_panel_stacked.count()
        
        # Asegurar que tenemos las referencias a todas las páginas
        if not hasattr(self, 'info_page'):
            self.info_page = self.info_panel_stacked.widget(0)
        if not hasattr(self, 'feeds_page'):
            self.feeds_page = self.info_panel_stacked.widget(1)
        if not hasattr(self, 'mas_info_page'):
            self.mas_info_page = self.info_panel_stacked.widget(2)
        
        # Cambiar a la siguiente página en secuencia
        next_index = (current_index + 1) % total_pages
        self.info_panel_stacked.setCurrentIndex(next_index)
        
        # Actualizar tooltip del botón según la página actual
        if hasattr(self, 'feeds_button'):
            if next_index == 0:  # Info básica
                self.feeds_button.setToolTip("Mostrar feeds")
            elif next_index == 1:  # Feeds
                self.feeds_button.setToolTip("Mostrar más información")
                # Si estamos en la página de feeds, asegurar que la pestaña predeterminada sea la de artistas
                stackedWidget = self.findChild(QStackedWidget, "stackedWidget_feeds")
                if stackedWidget:
                    stackedWidget.setCurrentIndex(0)
            elif next_index == 2:  # Más información
                self.feeds_button.setToolTip("Mostrar información básica")
                # Actualizar los GroupBox con la información detallada
                self._update_detailed_info()


    def _update_detailed_info(self):
        """Actualiza los GroupBox de la página 'más_info' con información detallada."""
        # Verificar si tenemos el item seleccionado
        if not hasattr(self, 'results_tree_widget') or not self.results_tree_widget:
            return
        
        # Obtener el item seleccionado
        selected_items = self.results_tree_widget.selectedItems()
        if not selected_items:
            return
        
        selected_item = selected_items[0]
        item_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            print("No hay datos disponibles para el item seleccionado")
            return
        
        item_type = item_data.get('type')
        item_id = item_data.get('id')
        
        if not item_type or not item_id:
            print(f"Datos de item inválidos: {item_data}")
            return
        
        # Encontrar los GroupBox para mostrar la información
        metadata_group = self.findChild(QGroupBox, "groupBox_metadata")
        release_group = self.findChild(QGroupBox, "groupBox_inforelease")
        label_group = self.findChild(QGroupBox, "groupBox_infosello")
        
        # Limpiar los GroupBox
        for group in [metadata_group, release_group, label_group]:
            if group and group.layout():
                self._clear_layout(group.layout())
        
        # Obtener información detallada según el tipo de item
        if item_type == 'artist':
            self._update_artist_detailed_info(item_id, metadata_group, release_group, label_group)
        elif item_type == 'album':
            self._update_album_detailed_info(item_id, metadata_group, release_group, label_group)
        elif item_type == 'song':
            self._update_song_detailed_info(item_id, metadata_group, release_group, label_group)


    def _update_song_detailed_info(self, song_id, metadata_group, release_group, label_group):
        """Actualiza la información detallada para una canción."""
        # Obtener los detalles de la canción
        song = self.db_manager.get_song_details(song_id)
        if not song:
            print(f"No se pudo obtener detalles para la canción con ID {song_id}")
            return
        
        # 1. Actualizar metadata
        if metadata_group:
            self._add_metadata_info(metadata_group, song, 'song')
        
        # 2. Actualizar información de release
        if release_group:
            conn = self.db_manager._get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Consultar información de MusicBrainz para esta canción
                    cursor.execute("""
                        SELECT s.musicbrainz_recordingid, s.musicbrainz_releasegroupid,
                            mr.title as release_title, mr.status, mr.releasedate,
                            mr.country, mr.annotation, mr.packaging
                        FROM songs s
                        LEFT JOIN mb_release_group mr ON s.musicbrainz_releasegroupid = mr.release_group_id
                        WHERE s.id = ?
                    """, (song_id,))
                    release_info = cursor.fetchone()
                    if release_info:
                        self._add_release_info(release_group, release_info)
                    else:
                        label = QLabel("No hay información de release disponible para esta canción")
                        release_group.layout().addWidget(label)
                except Exception as e:
                    print(f"Error obteniendo información de release: {e}")
                finally:
                    conn.close()
        
        # 3. Actualizar información de sello
        if label_group:
            conn = self.db_manager._get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Consultar información de sello para esta canción
                    cursor.execute("""
                        SELECT l.name as label_name, lr.relationship_type, l.country, lr.begin_date, lr.end_date, l.founded_year,
                            lr.release_id, lr.catalog_number, lr.release_status, l.wikipedia_url, l.discogs_url, l.bandcamp_url, l.mb_type  
                        FROM songs s
                        JOIN albums a ON s.album = a.name
                        LEFT JOIN label_release_relationships lr ON a.id = lr.release_id
                        LEFT JOIN labels l ON lr.label_id = l.id
                        WHERE s.id = ?
                    """, (song_id,))
                    label_info = cursor.fetchone()
                    if label_info:
                        self._add_label_info(label_group, label_info)
                    else:
                        label = QLabel("No hay información de sello disponible para esta canción")
                        label_group.layout().addWidget(label)
                except Exception as e:
                    print(f"Error obteniendo información de sello: {e}")
                finally:
                    conn.close()

    def _add_metadata_info(self, group_box, item, item_type):
        """Añade información de metadata al GroupBox."""
        if not group_box.layout():
            layout = QVBoxLayout(group_box)
        else:
            layout = group_box.layout()
        
        # Crear un texto con la metadata formateada
        metadata_text = f"<h3>Metadata de {item_type}</h3>"
        
        # Añadir campos relevantes según el tipo de item
        if item_type == 'song':
            fields = [
                ('Title', 'title'), ('Artist', 'artist'), ('Album', 'album'),
                ('Track', 'track_number'), ('Genre', 'genre'), ('Duration', 'duration'),
                ('Bitrate', 'bitrate'), ('Sample Rate', 'sample_rate'), 
                ('Added', 'added_timestamp'), ('Modified', 'last_modified')
            ]
        elif item_type == 'album':
            fields = [
                ('Name', 'name'), ('Year', 'year'), ('Genre', 'genre'),
                ('Label', 'label'), ('Tracks', 'total_tracks'),
                ('Added', 'added_timestamp'), ('Updated', 'last_updated')
            ]
        else:  # artist
            fields = [
                ('Name', 'name'), ('Origin', 'origin'), ('Formed', 'formed_year'),
                ('Ended', 'ended_year'), ('Albums', 'total_albums'),
                ('Added', 'added_timestamp'), ('Updated', 'last_updated')
            ]
        
        # Añadir cada campo si existe en el item
        for label, key in fields:
            try:
                if hasattr(item, 'keys') and key in item.keys() and item[key]:
                    value = item[key]
                    if key == 'duration' and value:
                        # Formatear duración como minutos:segundos
                        minutes = int(value) // 60
                        seconds = int(value) % 60
                        value = f"{minutes}:{seconds:02d}"
                    metadata_text += f"<p><b>{label}:</b> {value}</p>"
                elif isinstance(item, dict) and key in item and item[key]:
                    value = item[key]
                    if key == 'duration' and value:
                        minutes = int(value) // 60
                        seconds = int(value) % 60
                        value = f"{minutes}:{seconds:02d}"
                    metadata_text += f"<p><b>{label}:</b> {value}</p>"
            except:
                pass
        
        # Crear el widget de texto
        label = QLabel(metadata_text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label)

    def _add_release_info(self, group_box, release_info):
        """Añade información de release al GroupBox."""
        if not group_box.layout():
            layout = QVBoxLayout(group_box)
        else:
            layout = group_box.layout()
        
        # Crear un texto con la información formateada
        release_text = "<h3>Información de Release</h3>"
        
        # Añadir campos disponibles
        fields = [
            ('Título', 'release_title'), ('Estado', 'status'), 
            ('Fecha', 'releasedate'), ('País', 'country'),
            ('Packaging', 'packaging'), ('Anotación', 'annotation'),
            ('ID MusicBrainz Recording', 'musicbrainz_recordingid'),
            ('ID MusicBrainz Release Group', 'musicbrainz_releasegroupid')
        ]
        
        for label, key in fields:
            try:
                if hasattr(release_info, 'keys') and key in release_info.keys() and release_info[key]:
                    release_text += f"<p><b>{label}:</b> {release_info[key]}</p>"
            except:
                pass
        
        # Crear el widget de texto
        label = QLabel(release_text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label)

    def _add_label_info(self, group_box, label_info):
        """Añade información del sello al GroupBox."""
        if not group_box.layout():
            layout = QVBoxLayout(group_box)
        else:
            layout = group_box.layout()
        
        # Crear un texto con la información formateada
        label_text = "<h3>Información del Sello</h3>"
        
        # Añadir campos disponibles
        fields = [
            ('Nombre', 'label_name'), ('Tipo', 'type'), 
            ('País', 'country'), ('Fecha Inicio', 'begin_date'),
            ('Fecha Fin', 'end_date'), ('Nº Catálogo', 'catalog_number'),
            ('Estado', 'release_status')
        ]
        
        for label, key in fields:
            try:
                if hasattr(label_info, 'keys') and key in label_info.keys() and label_info[key]:
                    label_text += f"<p><b>{label}:</b> {label_info[key]}</p>"
            except:
                pass
        
        # Crear el widget de texto
        label = QLabel(label_text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label)

    def _clear_layout(self, layout):
        """Limpia todos los widgets de un layout."""
        if layout is None:
            return
        
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
            child_layout = item.layout()
            if child_layout:
                self._clear_layout(child_layout)



    def _update_artist_detailed_info(self, artist_id, metadata_group, release_group, label_group):
        """Actualiza la información detallada para un artista."""
        # Obtener los detalles del artista
        artist = self.db_manager.get_artist_details(artist_id)
        if not artist:
            print(f"No se pudo obtener detalles para el artista con ID {artist_id}")
            return
        
        # 1. Actualizar metadata
        if metadata_group:
            self._add_metadata_info(metadata_group, artist, 'artista')
        
        # 2. Actualizar información de release
        if release_group:
            conn = self.db_manager._get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Consultar información de MusicBrainz para este artista
                    cursor.execute("""
                        SELECT DISTINCT mr.* 
                        FROM mb_release_group mr
                        JOIN albums a ON mr.release_group_id = a.musicbrainz_releasegroupid
                        WHERE a.artist_id = ?
                        ORDER BY mr.releasedate DESC
                        LIMIT 5
                    """, (artist_id,))
                    releases = cursor.fetchall()
                    
                    if releases and len(releases) > 0:
                        layout = release_group.layout() or QVBoxLayout(release_group)
                        header = QLabel("<h3>Últimos releases</h3>")
                        header.setTextFormat(Qt.TextFormat.RichText)
                        layout.addWidget(header)
                        
                        for release in releases:
                            self._add_release_item(layout, release)
                    else:
                        label = QLabel("No hay información de releases disponible para este artista")
                        release_layout = release_group.layout() or QVBoxLayout(release_group)
                        release_layout.addWidget(label)
                except Exception as e:
                    print(f"Error obteniendo información de releases: {e}")
                finally:
                    conn.close()
        
        # 3. Actualizar información de sello
        if label_group:
            conn = self.db_manager._get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Consultar información de sellos para este artista
                    cursor.execute("""
                        SELECT DISTINCT l.name as label_name, l.type, l.country, 
                            l.begin_date, l.end_date, COUNT(lr.release_id) as release_count
                        FROM albums a
                        JOIN label_release_relationships lr ON a.id = lr.release_id
                        JOIN labels l ON lr.label_id = l.id
                        WHERE a.artist_id = ?
                        GROUP BY l.id
                        ORDER BY release_count DESC
                    """, (artist_id,))
                    labels = cursor.fetchall()
                    
                    if labels and len(labels) > 0:
                        layout = label_group.layout() or QVBoxLayout(label_group)
                        header = QLabel("<h3>Sellos relacionados</h3>")
                        header.setTextFormat(Qt.TextFormat.RichText)
                        layout.addWidget(header)
                        
                        for label_info in labels:
                            self._add_label_item(layout, label_info)
                    else:
                        label = QLabel("No hay información de sellos disponible para este artista")
                        label_layout = label_group.layout() or QVBoxLayout(label_group)
                        label_layout.addWidget(label)
                except Exception as e:
                    print(f"Error obteniendo información de sellos: {e}")
                finally:
                    conn.close()


    def _update_album_detailed_info(self, album_id, metadata_group, release_group, label_group):
        """Actualiza la información detallada para un álbum."""
        # Obtener los detalles del álbum
        album = self.db_manager.get_album_details(album_id)
        if not album:
            print(f"No se pudo obtener detalles para el álbum con ID {album_id}")
            return
        
        # 1. Actualizar metadata
        if metadata_group:
            self._add_metadata_info(metadata_group, album, 'álbum')
            
            # Información adicional de audio - detalles técnicos
            conn = self.db_manager._get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT AVG(bitrate) as avg_bitrate, 
                            MIN(bitrate) as min_bitrate, 
                            MAX(bitrate) as max_bitrate,
                            AVG(duration) as avg_duration,
                            SUM(duration) as total_duration,
                            AVG(sample_rate) as avg_sample_rate
                        FROM songs
                        WHERE album_id = ?
                    """, (album_id,))
                    audio_stats = cursor.fetchone()
                    
                    if audio_stats:
                        stats_text = "<h3>Estadísticas de Audio</h3>"
                        
                        # Formatear duración total
                        total_minutes = int(audio_stats['total_duration'] or 0) // 60
                        total_seconds = int(audio_stats['total_duration'] or 0) % 60
                        total_duration_str = f"{total_minutes}:{total_seconds:02d}"
                        
                        # Añadir estadísticas
                        stats_text += f"<p><b>Duración total:</b> {total_duration_str}</p>"
                        if audio_stats['avg_bitrate']:
                            stats_text += f"<p><b>Bitrate promedio:</b> {int(audio_stats['avg_bitrate'])} kbps</p>"
                        if audio_stats['min_bitrate'] and audio_stats['max_bitrate']:
                            stats_text += f"<p><b>Rango de bitrate:</b> {int(audio_stats['min_bitrate'])} - {int(audio_stats['max_bitrate'])} kbps</p>"
                        if audio_stats['avg_sample_rate']:
                            stats_text += f"<p><b>Sample rate promedio:</b> {int(audio_stats['avg_sample_rate'])} Hz</p>"
                        
                        stats_label = QLabel(stats_text)
                        stats_label.setWordWrap(True)
                        stats_label.setTextFormat(Qt.TextFormat.RichText)
                        metadata_group.layout().addWidget(stats_label)
                except Exception as e:
                    print(f"Error obteniendo estadísticas de audio: {e}")
                finally:
                    conn.close()
        
        # 2. Actualizar información de release
        if release_group:
            conn = self.db_manager._get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Consultar información de MusicBrainz para este álbum
                    cursor.execute("""
                        SELECT mr.*
                        FROM mb_release_group mr
                        JOIN albums a ON mr.release_group_id = a.musicbrainz_releasegroupid
                        WHERE a.id = ?
                    """, (album_id,))
                    release_info = cursor.fetchone()
                    
                    if release_info:
                        self._add_release_info(release_group, release_info)
                        
                        # Añadir información de versiones alternativas
                        cursor.execute("""
                            SELECT mr.*
                            FROM mb_release_group mr
                            WHERE mr.release_group_id = ? AND mr.id != ?
                            ORDER BY mr.releasedate
                        """, (release_info['release_group_id'], release_info['id']))
                        alt_releases = cursor.fetchall()
                        
                        if alt_releases and len(alt_releases) > 0:
                            alt_header = QLabel("<h3>Versiones alternativas</h3>")
                            alt_header.setTextFormat(Qt.TextFormat.RichText)
                            release_group.layout().addWidget(alt_header)
                            
                            for alt_release in alt_releases:
                                alt_text = f"<p><b>{alt_release['title']}</b> ({alt_release['country'] or 'Unknown'}, {alt_release['releasedate'] or 'Unknown'})</p>"
                                if alt_release['status']:
                                    alt_text += f"<p>Estado: {alt_release['status']}</p>"
                                if alt_release['packaging']:
                                    alt_text += f"<p>Packaging: {alt_release['packaging']}</p>"
                                
                                alt_label = QLabel(alt_text)
                                alt_label.setWordWrap(True)
                                alt_label.setTextFormat(Qt.TextFormat.RichText)
                                release_group.layout().addWidget(alt_label)
                    else:
                        label = QLabel("No hay información de release disponible para este álbum")
                        release_layout = release_group.layout() or QVBoxLayout(release_group)
                        release_layout.addWidget(label)
                except Exception as e:
                    print(f"Error obteniendo información de release: {e}")
                finally:
                    conn.close()
        
        # 3. Actualizar información de sello
        if label_group:
            conn = self.db_manager._get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Consultar información de sello para este álbum
                    cursor.execute("""
                        SELECT l.name as label_name, l.type, l.country, l.begin_date, l.end_date,
                            lr.catalog_number, lr.release_status, lr.release_id
                        FROM label_release_relationships lr
                        JOIN labels l ON lr.label_id = l.id
                        WHERE lr.release_id = ?
                    """, (album_id,))
                    label_info = cursor.fetchone()
                    
                    if label_info:
                        self._add_label_info(label_group, label_info)
                        
                        # Añadir información de relaciones del sello
                        cursor.execute("""
                            SELECT lr.relationship_type, lr.entity_type, lr.entity_name
                            FROM label_relationships lr
                            JOIN label_release_relationships lrr ON lr.label_id = lrr.label_id
                            WHERE lrr.release_id = ?
                        """, (album_id,))
                        relations = cursor.fetchall()
                        
                        if relations and len(relations) > 0:
                            rel_header = QLabel("<h3>Relaciones del sello</h3>")
                            rel_header.setTextFormat(Qt.TextFormat.RichText)
                            label_group.layout().addWidget(rel_header)
                            
                            for relation in relations:
                                rel_text = f"<p><b>{relation['relationship_type']}:</b> {relation['entity_name']} ({relation['entity_type']})</p>"
                                rel_label = QLabel(rel_text)
                                rel_label.setWordWrap(True)
                                rel_label.setTextFormat(Qt.TextFormat.RichText)
                                label_group.layout().addWidget(rel_label)
                    else:
                        label = QLabel("No hay información de sello disponible para este álbum")
                        label_layout = label_group.layout() or QVBoxLayout(label_group)
                        label_layout.addWidget(label)
                except Exception as e:
                    print(f"Error obteniendo información de sello: {e}")
                finally:
                    conn.close()


    def _add_release_item(self, layout, release):
        """Añade un ítem de release al layout."""
        release_text = f"<p><b>{release['title']}</b>"
        if release['releasedate']:
            release_text += f" ({release['releasedate']})"
        release_text += "</p>"
        
        if release['status']:
            release_text += f"<p>Estado: {release['status']}</p>"
        if release['country']:
            release_text += f"<p>País: {release['country']}</p>"
            
        release_label = QLabel(release_text)
        release_label.setWordWrap(True)
        release_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(release_label)

    def _add_label_item(self, layout, label_info):
        """Añade un ítem de sello al layout."""
        label_text = f"<p><b>{label_info['label_name']}</b>"
        if label_info['type']:
            label_text += f" ({label_info['type']})"
        label_text += "</p>"
        
        if label_info['country']:
            label_text += f"<p>País: {label_info['country']}</p>"
        if label_info['begin_date']:
            date_text = f"Fundado: {label_info['begin_date']}"
            if label_info['end_date']:
                date_text += f" - Cerrado: {label_info['end_date']}"
            label_text += f"<p>{date_text}</p>"
        if 'release_count' in label_info.keys() and label_info['release_count']:
            label_text += f"<p>Releases: {label_info['release_count']}</p>"
            
        label_label = QLabel(label_text)
        label_label.setWordWrap(True)
        label_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label_label)