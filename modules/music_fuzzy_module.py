from PyQt6.QtWidgets import (QComboBox, QWidget, QTreeWidgetItem, QPushButton,
                             QLabel, QVBoxLayout, QCheckBox, QStackedWidget, QGroupBox, 
                             QRadioButton, QSpinBox, QComboBox, QGridLayout, QDialog)
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
from modules.submodules.fuzzy.player_manager import PlayerManager
from modules.submodules.fuzzy.module_integrations import ModuleIntegrator 

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

        # Initialize player manager with config
        self.player_manager = PlayerManager(kwargs)
        print("PlayerManager inicializado")

        # Load saved button configuration
        self._load_saved_button_configuration()

        # Initialize module integrator
        self.module_integrator = ModuleIntegrator(self)
        print("ModuleIntegrator inicializado")

        # Cargar UI de ajustes avanzados después de inicializar todos los componentes
        # IMPORTANTE: Movido después de la inicialización de search_handler
        if hasattr(self, 'advanced_settings_container'):
            self._load_advanced_settings_ui()

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
            
            # Cargar la UI de ajustes avanzados preventivamente
            if hasattr(self, 'advanced_settings_container'):
                self._load_advanced_settings_ui()
            
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
            
            # Intentar conectar el botón apply_time_filter directamente
            apply_time_filter = self.findChild(QPushButton, "apply_time_filter")
            if apply_time_filter:
                try:
                    apply_time_filter.clicked.disconnect()
                except:
                    pass
                apply_time_filter.clicked.connect(self._handle_apply_time_filter)
                print("Botón apply_time_filter conectado directamente desde init_ui")

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

        # Connect player buttons if they exist
        if hasattr(self, 'play_button'):
            self.play_button.clicked.connect(self._handle_play_button)
            print("Play button connected")

        # Conectar botón de reproducción actual
        if hasattr(self, 'playing_button'):  # Asumiendo que 'custom_button1' es tu 'playing_button'
            self.playing_button.clicked.connect(self._handle_playing_button)

        # Conectar los botones del reproductor
        self._connect_player_buttons()

        # Conectar los botones de navegación de feeds
        self._connect_feed_tab_buttons()
        
        # Intentar conectar botones de filtro de tiempo
        self._connect_time_filter_buttons()

        # Connect edit_buttons button (this is the "pushButton" with an icon in your UI)
        self._connect_edit_buttons()


    def _connect_time_filter_buttons(self):
        """Conectar los botones de filtro de tiempo directamente."""
        # Buscar los controles dentro del widget avanzado
        apply_time_filter = self.findChild(QPushButton, "apply_time_filter")
        time_value = self.findChild(QSpinBox, "time_value")
        time_unit = self.findChild(QComboBox, "time_unit")
        
        if apply_time_filter and time_value and time_unit:
            # Guardar referencias a los controles
            self.time_value = time_value
            self.time_unit = time_unit
            
            # Conectar el botón de aplicar filtro
            try:
                apply_time_filter.clicked.disconnect()
            except:
                pass
            
            if hasattr(self, 'search_handler') and self.search_handler:
                apply_time_filter.clicked.connect(self.search_handler._apply_time_filter)
                print("Botón de filtro de tiempo conectado correctamente")
            else:
                print("WARNING: search_handler no inicializado, no se puede conectar botón de filtro")
        else:
            print("No se encontraron todos los controles de filtro de tiempo")


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
                
                # Obtener referencia al radio button
                self.only_local_files = advanced_widget.findChild(QRadioButton, "only_local_files")
                
                if self.only_local_files:
                    print("Radio button 'only_local_files' encontrado")
                    # Desconectar primero para evitar conexiones duplicadas
                    try:
                        self.only_local_files.toggled.disconnect()
                    except:
                        pass
                        
                    # Verificar que search_handler existe antes de usarlo
                    if hasattr(self, 'search_handler') and self.search_handler:
                        # Conectar señales
                        self.only_local_files.toggled.connect(self.search_handler.perform_search)
                        self.only_local_files.toggled.connect(self._save_checkbox_state)
                    else:
                        print("WARNING: search_handler no inicializado, no se pueden conectar señales")
                    
                    # Establecer el estado inicial desde la configuración cargada en __init__
                    print(f"Estableciendo estado inicial del radio button: {self.only_local_files_state}")
                    self.only_local_files.setChecked(bool(self.only_local_files_state))
                    
                    # También obtener el show_all para mantener el grupo consistente
                    self.show_all = advanced_widget.findChild(QRadioButton, "show_all")
                    if self.show_all:
                        self.show_all.setChecked(not bool(self.only_local_files_state))
                else:
                    print("WARNING: Radio button 'only_local_files' no encontrado en el archivo UI")
                    # Crearlo programáticamente como fallback
                    self.only_local_files = QRadioButton("Mostrar solo archivos locales")
                    layout.addWidget(self.only_local_files)
                    # Verificar que search_handler existe antes de usarlo
                    if hasattr(self, 'search_handler') and self.search_handler:
                        self.only_local_files.toggled.connect(self.search_handler.perform_search)
                    self.only_local_files.toggled.connect(self._save_checkbox_state)
                    self.only_local_files.setChecked(bool(self.only_local_files_state))
                    
                # Conectar el botón apply_time_filter si existe
                apply_time_filter = advanced_widget.findChild(QPushButton, "apply_time_filter")
                if apply_time_filter:
                    try:
                        apply_time_filter.clicked.disconnect()
                    except:
                        pass
                    
                    # Conectar DIRECTAMENTE al método en esta clase, no en search_handler
                    apply_time_filter.clicked.connect(self._handle_apply_time_filter)
                    print("Botón apply_time_filter conectado directamente a _handle_apply_time_filter")
                    
                    # Guardar referencias a los controles de tiempo
                    self.time_value = advanced_widget.findChild(QSpinBox, "time_value")
                    self.time_unit = advanced_widget.findChild(QComboBox, "time_unit")
                    
                    if self.time_value and self.time_unit:
                        print("Controles de tiempo encontrados y asignados correctamente")
                    else:
                        print("WARNING: No se pudieron encontrar los controles de tiempo")


                # Conectar el botón apply_year si existe
                apply_year = advanced_widget.findChild(QPushButton, "apply_year")
                if apply_year:
                    try:
                        apply_year.clicked.disconnect()
                    except:
                        pass
                    
                    # Conectar directamente al método en esta clase
                    apply_year.clicked.connect(self._handle_apply_year)
                    print("Botón apply_year conectado directamente a _handle_apply_year")
                    
                    # Guardar referencia al control year_only_spin
                    self.year_only_spin = advanced_widget.findChild(QSpinBox, "year_only_spin")
                    
                    if self.year_only_spin:
                        print("Control year_only_spin encontrado y asignado correctamente")
                    else:
                        print("WARNING: No se pudo encontrar el control year_only_spin")


                # Conectar el botón de décadas (suponiendo que se llama "apply_decade" o similar)
                apply_decade = advanced_widget.findChild(QPushButton, "apply_decade")
                if not apply_decade:
                    # Si no se encuentra, podría ser el botón "apply_month_year" renombrado
                    apply_decade = advanced_widget.findChild(QPushButton, "apply_month_year")

                if apply_decade:
                    try:
                        apply_decade.clicked.disconnect()
                    except:
                        pass
                    
                    # Conectar directamente al método en esta clase
                    apply_decade.clicked.connect(self._handle_apply_decade)
                    print("Botón de décadas conectado directamente a _handle_apply_decade")
                    
                    # Guardar referencias a los controles
                    self.year_spin_begin = advanced_widget.findChild(QSpinBox, "year_spin_begin")
                    self.year_spin_end = advanced_widget.findChild(QSpinBox, "year_spin_end")
                    
                    if self.year_spin_begin and self.year_spin_end:
                        print("Controles de rango de años encontrados y asignados correctamente")
                    else:
                        print("WARNING: No se pudieron encontrar los controles de rango de años")


            else:
                print(f"Archivo UI de ajustes avanzados no encontrado: {ui_path}")
                # Crear una UI básica como fallback

            playing_button = advanced_widget.findChild(QPushButton, "playing_button")
            if playing_button:
                try:
                    playing_button.clicked.disconnect()
                except:
                    pass
                playing_button.clicked.connect(self._handle_playing_button)
                print("Botón 'Reproduciendo' en configuraciones avanzadas conectado")

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
                        
                        # Get reference to the radio button (not checkbox)
                        self.only_local_files = advanced_widget.findChild(QRadioButton, "only_local_files")
                        
                        if self.only_local_files:
                            print("Found only_local_files radio button")
                            
                            # Establecer el estado basado en la configuración
                            self.only_local_files.setChecked(self.only_local_files_state)
                            
                            # Connect to search and to save config
                            self.only_local_files.toggled.connect(self._on_only_local_toggled)
                            
                            # Also get reference to show_all button
                            self.show_all = advanced_widget.findChild(QRadioButton, "show_all")
                            if self.show_all:
                                self.show_all.setChecked(not self.only_local_files_state)
                                self.show_all.toggled.connect(self._on_show_all_toggled)
                        else:
                            print("WARNING: Radio button 'only_local_files' not found in the UI file")
                            # Create it programmatically as a fallback
                            self.only_local_files = QRadioButton("Show only local files")
                            layout.addWidget(self.only_local_files)
                            self.only_local_files.setChecked(self.only_local_files_state)
                            self.only_local_files.toggled.connect(self._on_only_local_toggled)
                    else:
                        print(f"Advanced settings UI file not found: {ui_path}")
                        # Create a basic UI programmatically as fallback
                        self.only_local_files = QRadioButton("Show only local files")
                        layout.addWidget(self.only_local_files)
                        self.only_local_files.setChecked(self.only_local_files_state)
                        self.only_local_files.toggled.connect(self._on_only_local_toggled)
                    
                except Exception as e:
                    print(f"Error loading advanced settings UI: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Conectar el botón apply_time_filter
                apply_time_filter = advanced_widget.findChild(QPushButton, "apply_time_filter")
                if apply_time_filter:
                    try:
                        apply_time_filter.clicked.disconnect()
                    except:
                        pass
                    apply_time_filter.clicked.connect(self._handle_apply_time_filter)
                    print("Botón apply_time_filter conectado desde _toggle_advanced_settings")
            
            # Show/hide the container based on checkbox state
            self.advanced_settings_container.setVisible(checked)
        

    def _on_only_local_toggled(self, checked):
        """Manejador para el radio button 'only_local_files'."""
        if checked:
            print("Radio button 'only_local_files' activado")
            self.only_local_state = True
            self._save_checkbox_state(True)
            self.search_handler.perform_search()

    def _on_show_all_toggled(self, checked):
        """Manejador para el radio button 'show_all'."""
        if checked:
            print("Radio button 'show_all' activado")
            self.only_local_state = False
            self._save_checkbox_state(False)
            self.search_handler.perform_search()


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


# PLAYER

# Player control methods

    def _connect_player_buttons(self):
        """Conecta los botones del reproductor a sus manejadores."""
        # Botón de reproducción principal
        if hasattr(self, 'play_button'):
            try:
                self.play_button.clicked.disconnect()  # Desconectar primero para evitar múltiples conexiones
            except:
                pass
            self.play_button.clicked.connect(self._handle_play_button)
            print("Botón de reproducción conectado")
        
        # Botón para añadir a la cola (tiene que ser 'add_to_queue', no 'add_to_queue_button')
        add_queue_button = self.findChild(QPushButton, "add_to_queue")
        if add_queue_button:
            try:
                add_queue_button.clicked.disconnect()
            except:
                pass
            add_queue_button.clicked.connect(self._handle_add_to_queue)
            print("Botón de cola conectado")
        
        # Botón de siguiente pista (es 'play_button_4' según el UI)
        next_button = self.findChild(QPushButton, "play_button_4")
        if next_button:
            try:
                next_button.clicked.disconnect()
            except:
                pass
            next_button.clicked.connect(self._handle_next_button)
            print("Botón siguiente conectado")
        
        # Botón de pista anterior (es 'play_button_3' según el UI)
        prev_button = self.findChild(QPushButton, "play_button_3")
        if prev_button:
            try:
                prev_button.clicked.disconnect()
            except:
                pass
            prev_button.clicked.connect(self._handle_prev_button)
            print("Botón anterior conectado")
        
        # Botón de detener (es 'muspy_button_2' según el UI)
        stop_button = self.findChild(QPushButton, "muspy_button_2")
        if stop_button:
            try:
                stop_button.clicked.disconnect()
            except:
                pass
            stop_button.clicked.connect(self._handle_stop_button)
            print("Botón de detener conectado")
        
        # Si estamos usando custom_button1 como "Reproduciendo"
        if hasattr(self, 'custom_button1') and self.custom_button1:
            if self.custom_button1.text() == "Reproduciendo":
                try:
                    self.custom_button1.clicked.disconnect()
                except:
                    pass
                self.custom_button1.clicked.connect(self._handle_playing_button)
                print("Botón custom 'Reproduciendo' conectado")
                
        # También conectar el botón "Reproduciendo" en las configuraciones avanzadas
        playing_button = self.findChild(QPushButton, "playing_button")
        if playing_button:
            try:
                playing_button.clicked.disconnect()
            except:
                pass
            playing_button.clicked.connect(self._handle_playing_button)
            print("Botón 'Reproduciendo' en configuraciones avanzadas conectado")

        # Botón para abrir carpeta
        folder_button = self.findChild(QPushButton, "folder_button")
        if folder_button:
            try:
                folder_button.clicked.disconnect()
            except:
                pass
            folder_button.clicked.connect(self._handle_folder_button)
            print("Botón de carpeta conectado")

    def _handle_play_button(self):
        """Maneja el clic en el botón de reproducción según el elemento seleccionado."""
        print("Botón de reproducción pulsado")
        
        if not hasattr(self, 'player_manager'):
            print("ERROR: player_manager no inicializado")
            return
            
        # Obtener el elemento seleccionado
        selected_items = self.results_tree_widget.selectedItems()
        if not selected_items:
            print("No hay elementos seleccionados, alternando play/pause")
            # Solo alternar play/pause si no hay elementos seleccionados
            self.player_manager.play_pause()
            return
            
        selected_item = selected_items[0]
        item_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            print("No se encontraron datos del elemento para el elemento seleccionado")
            return
            
        item_type = item_data.get('type')
        item_id = item_data.get('id')
        
        print(f"Elemento seleccionado: tipo={item_type}, id={item_id}")
        
        if item_type == 'song':
            # Obtener detalles de la canción
            print(f"Obteniendo detalles de la canción para ID: {item_id}")
            song = self.db_manager.get_song_details(item_id)
            
            # Imprimir todas las claves disponibles para depuración
            if song:
                print(f"Found song with id {item_id}, keys: {song.keys() if hasattr(song, 'keys') else 'No keys method'}")
                
                # Verificar si file_path existe en el objeto song
                file_path = None
                if hasattr(song, 'keys') and 'file_path' in song.keys():
                    file_path = song['file_path']
                elif isinstance(song, dict) and 'file_path' in song:
                    file_path = song['file_path']
                elif hasattr(song, 'file_path'):
                    file_path = song.file_path
                
                if file_path:
                    if os.path.exists(file_path):
                        print(f"Reproduciendo archivo de canción: {file_path}")
                        result = self.player_manager.play(file_path)
                        print(f"Resultado de la reproducción: {result}")
                    else:
                        print(f"El archivo no existe: {file_path}")
                else:
                    print("La canción no tiene file_path o file_path está vacío")
                    
                    # Intentar obtener el file_path directamente de la base de datos
                    conn = self.db_manager._get_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT file_path FROM songs WHERE id = ?", (item_id,))
                            result = cursor.fetchone()
                            if result and result['file_path']:
                                file_path = result['file_path']
                                if os.path.exists(file_path):
                                    print(f"Reproduciendo archivo de canción (obtenido directamente): {file_path}")
                                    result = self.player_manager.play(file_path)
                                    print(f"Resultado de la reproducción: {result}")
                                else:
                                    print(f"El archivo no existe: {file_path}")
                            else:
                                print("No se pudo obtener file_path de la base de datos")
                        except Exception as e:
                            print(f"Error al obtener file_path de la base de datos: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            conn.close()
            else:
                print(f"No se encontró la canción con ID: {item_id}")
        
        elif item_type == 'album':
            # Obtener detalles del álbum
            print(f"Obteniendo detalles del álbum para ID: {item_id}")
            album = self.db_manager.get_album_details(item_id)
            if album:
                # Comprobar si el álbum tiene folder_path
                folder_path = None
                if hasattr(album, 'keys') and 'folder_path' in album.keys():
                    folder_path = album['folder_path']
                elif isinstance(album, dict) and 'folder_path' in album:
                    folder_path = album['folder_path']
                elif hasattr(album, 'folder_path'):
                    folder_path = album.folder_path
                
                if folder_path and os.path.exists(folder_path):
                    print(f"Reproduciendo carpeta del álbum: {folder_path}")
                    result = self.player_manager.play(folder_path)
                    print(f"Resultado de la reproducción: {result}")
                else:
                    print(f"El álbum no tiene folder_path válido: {folder_path}")
                    
                    # Si no hay folder_path, intentar reproducir todas las canciones del álbum
                    songs = self.db_manager.get_album_songs(item_id)
                    if songs and len(songs) > 0:
                        # Buscar la primera canción con file_path válido
                        for song in songs:
                            file_path = None
                            if hasattr(song, 'keys') and 'file_path' in song.keys():
                                file_path = song['file_path']
                            elif isinstance(song, dict) and 'file_path' in song:
                                file_path = song['file_path']
                            elif hasattr(song, 'file_path'):
                                file_path = song.file_path
                            
                            if file_path and os.path.exists(file_path):
                                print(f"Reproduciendo primera canción del álbum: {file_path}")
                                result = self.player_manager.play(file_path)
                                print(f"Resultado de la reproducción: {result}")
                                
                                # Encolar el resto de canciones
                                for next_song in songs:
                                    if next_song != song:  # No encolar la primera canción de nuevo
                                        next_file_path = None
                                        if hasattr(next_song, 'keys') and 'file_path' in next_song.keys():
                                            next_file_path = next_song['file_path']
                                        elif isinstance(next_song, dict) and 'file_path' in next_song:
                                            next_file_path = next_song['file_path']
                                        elif hasattr(next_song, 'file_path'):
                                            next_file_path = next_song.file_path
                                        
                                        if next_file_path and os.path.exists(next_file_path):
                                            self.player_manager.add_to_queue(next_file_path)
                                
                                return
                                
                        print("No se encontraron canciones con file_path válido en el álbum")
                    else:
                        print("No se encontraron canciones para el álbum")
            else:
                print(f"No se encontró el álbum con ID: {item_id}")
        
        elif item_type == 'artist':
            # Obtener álbumes del artista
            print(f"Obteniendo álbumes para el artista ID: {item_id}")
            albums = self.db_manager.get_artist_albums(item_id)
            if albums and len(albums) > 0:
                # Recopilar rutas de carpetas de álbumes
                folder_paths = []
                for album in albums:
                    folder_path = None
                    if hasattr(album, 'keys') and 'folder_path' in album.keys():
                        folder_path = album['folder_path']
                    elif isinstance(album, dict) and 'folder_path' in album:
                        folder_path = album['folder_path']
                    elif hasattr(album, 'folder_path'):
                        folder_path = album.folder_path
                    
                    if folder_path and os.path.exists(folder_path):
                        folder_paths.append(folder_path)
                
                if folder_paths:
                    print(f"Reproduciendo {len(folder_paths)} carpetas de álbumes del artista")
                    result = self.player_manager.play_artist(folder_paths)
                    print(f"Resultado de la reproducción: {result}")
                else:
                    print("No se encontraron carpetas de álbumes válidas para el artista")
                    
                    # Si no hay folder_paths, intentar obtenerlos directamente de la base de datos
                    conn = self.db_manager._get_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT folder_path FROM albums WHERE artist_id = ?", (item_id,))
                            results = cursor.fetchall()
                            
                            folder_paths = []
                            for result in results:
                                if result and result['folder_path'] and os.path.exists(result['folder_path']):
                                    folder_paths.append(result['folder_path'])
                            
                            if folder_paths:
                                print(f"Reproduciendo {len(folder_paths)} carpetas de álbumes del artista (obtenidas directamente)")
                                result = self.player_manager.play_artist(folder_paths)
                                print(f"Resultado de la reproducción: {result}")
                            else:
                                print("No se encontraron carpetas de álbumes válidas en la base de datos")
                                
                                # Si todavía no hay carpetas, intentar reproducir la primera canción de cada álbum
                                print("Intentando reproducir canciones de álbumes...")
                                all_songs = []
                                
                                # Obtener IDs de álbumes
                                cursor.execute("SELECT id FROM albums WHERE artist_id = ?", (item_id,))
                                album_results = cursor.fetchall()
                                
                                if album_results:
                                    for album_result in album_results:
                                        album_id = album_result['id']
                                        cursor.execute("SELECT file_path FROM songs WHERE album_id = ? LIMIT 1", (album_id,))
                                        song_result = cursor.fetchone()
                                        if song_result and song_result['file_path'] and os.path.exists(song_result['file_path']):
                                            all_songs.append(song_result['file_path'])
                                
                                if all_songs:
                                    # Reproducir la primera canción
                                    print(f"Reproduciendo primera canción: {all_songs[0]}")
                                    self.player_manager.play(all_songs[0])
                                    
                                    # Encolar el resto
                                    if len(all_songs) > 1:
                                        print(f"Encolando {len(all_songs)-1} canciones adicionales")
                                        self.player_manager.add_to_queue(all_songs[1:])
                                else:
                                    print("No se encontraron canciones para reproducir")
                        except Exception as e:
                            print(f"Error al obtener folder_paths de la base de datos: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            conn.close()
            else:
                print("No se encontraron álbumes para el artista")

    def _handle_add_to_queue(self):
        """Maneja el clic en el botón de añadir a la cola según el elemento seleccionado."""
        print("Botón de cola pulsado")
        
        if not hasattr(self, 'player_manager'):
            print("ERROR: player_manager no inicializado")
            return
            
        # Obtener el elemento seleccionado
        selected_items = self.results_tree_widget.selectedItems()
        if not selected_items:
            print("No hay elementos seleccionados para encolar")
            return
            
        selected_item = selected_items[0]
        item_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            print("No se encontraron datos del elemento para el elemento seleccionado")
            return
            
        item_type = item_data.get('type')
        item_id = item_data.get('id')
        
        print(f"Elemento seleccionado para encolar: tipo={item_type}, id={item_id}")
        
        if item_type == 'song':
            # Obtener detalles de la canción
            song = self.db_manager.get_song_details(item_id)
            
            # Obtener el file_path
            file_path = None
            if song:
                if hasattr(song, 'keys') and 'file_path' in song.keys():
                    file_path = song['file_path']
                elif isinstance(song, dict) and 'file_path' in song:
                    file_path = song['file_path']
                elif hasattr(song, 'file_path'):
                    file_path = song.file_path
            
            if file_path and os.path.exists(file_path):
                print(f"Encolando archivo de canción: {file_path}")
                result = self.player_manager.add_to_queue(file_path)
                print(f"Resultado de encolar: {result}")
            else:
                print("La canción no tiene file_path válido")
                
                # Intentar obtener el file_path directamente de la base de datos
                conn = self.db_manager._get_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("SELECT file_path FROM songs WHERE id = ?", (item_id,))
                        result = cursor.fetchone()
                        if result and result['file_path'] and os.path.exists(result['file_path']):
                            file_path = result['file_path']
                            print(f"Encolando archivo de canción (obtenido directamente): {file_path}")
                            result = self.player_manager.add_to_queue(file_path)
                            print(f"Resultado de encolar: {result}")
                        else:
                            print("No se pudo obtener un file_path válido de la base de datos")
                    except Exception as e:
                        print(f"Error al obtener file_path de la base de datos: {e}")
                        import traceback
                        traceback.print_exc()
                    finally:
                        conn.close()
        
        elif item_type == 'album':
            # Obtener canciones del álbum
            songs = self.db_manager.get_album_songs(item_id)
            if songs and len(songs) > 0:
                # Recopilar rutas de archivos de canciones
                song_paths = []
                for song in songs:
                    file_path = None
                    if hasattr(song, 'keys') and 'file_path' in song.keys():
                        file_path = song['file_path']
                    elif isinstance(song, dict) and 'file_path' in song:
                        file_path = song['file_path']
                    elif hasattr(song, 'file_path'):
                        file_path = song.file_path
                    
                    if file_path and os.path.exists(file_path):
                        song_paths.append(file_path)
                
                if song_paths:
                    print(f"Encolando {len(song_paths)} canciones del álbum")
                    result = self.player_manager.add_to_queue(song_paths)
                    print(f"Resultado de encolar: {result}")
                else:
                    print("No se encontraron archivos de canciones válidos para el álbum")
                    
                    # Intentar obtener los file_paths directamente de la base de datos
                    conn = self.db_manager._get_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT file_path FROM songs WHERE album_id = ?", (item_id,))
                            results = cursor.fetchall()
                            
                            song_paths = []
                            for result in results:
                                if result and result['file_path'] and os.path.exists(result['file_path']):
                                    song_paths.append(result['file_path'])
                            
                            if song_paths:
                                print(f"Encolando {len(song_paths)} canciones del álbum (obtenidas directamente)")
                                result = self.player_manager.add_to_queue(song_paths)
                                print(f"Resultado de encolar: {result}")
                            else:
                                print("No se encontraron archivos de canciones válidos en la base de datos")
                        except Exception as e:
                            print(f"Error al obtener file_paths de la base de datos: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            conn.close()
            else:
                print("No se encontraron canciones para el álbum")
        
        elif item_type == 'artist':
            # Obtener álbumes del artista y sus canciones
            albums = self.db_manager.get_artist_albums(item_id)
            if albums and len(albums) > 0:
                # Recopilar rutas de archivos de todas las canciones
                all_song_paths = []
                for album in albums:
                    album_id = album['id'] if isinstance(album, dict) and 'id' in album else getattr(album, 'id', None)
                    if album_id:
                        songs = self.db_manager.get_album_songs(album_id)
                        for song in songs:
                            file_path = None
                            if hasattr(song, 'keys') and 'file_path' in song.keys():
                                file_path = song['file_path']
                            elif isinstance(song, dict) and 'file_path' in song:
                                file_path = song['file_path']
                            elif hasattr(song, 'file_path'):
                                file_path = song.file_path
                            
                            if file_path and os.path.exists(file_path):
                                all_song_paths.append(file_path)
                
                if all_song_paths:
                    print(f"Encolando {len(all_song_paths)} canciones del artista")
                    result = self.player_manager.add_to_queue(all_song_paths)
                    print(f"Resultado de encolar: {result}")
                else:
                    print("No se encontraron archivos de canciones válidos para el artista")
                    
                    # Intentar obtener los file_paths directamente de la base de datos
                    conn = self.db_manager._get_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            # Obtener todos los álbumes del artista
                            cursor.execute("SELECT id FROM albums WHERE artist_id = ?", (item_id,))
                            album_results = cursor.fetchall()
                            
                            all_song_paths = []
                            for album_result in album_results:
                                album_id = album_result['id']
                                # Obtener todas las canciones de cada álbum
                                cursor.execute("SELECT file_path FROM songs WHERE album_id = ?", (album_id,))
                                song_results = cursor.fetchall()
                                
                                for song_result in song_results:
                                    if song_result and song_result['file_path'] and os.path.exists(song_result['file_path']):
                                        all_song_paths.append(song_result['file_path'])
                            
                            if all_song_paths:
                                print(f"Encolando {len(all_song_paths)} canciones del artista (obtenidas directamente)")
                                result = self.player_manager.add_to_queue(all_song_paths)
                                print(f"Resultado de encolar: {result}")
                            else:
                                print("No se encontraron archivos de canciones válidos en la base de datos")
                        except Exception as e:
                            print(f"Error al obtener file_paths de la base de datos: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            conn.close()
            else:
                print("No se encontraron álbumes para el artista")


    def _handle_playing_button(self):
        """Maneja el clic en el botón de reproducción actual."""
        print("Botón 'Reproduciendo' pulsado")
        
        # Obtener la cadena de búsqueda para lo que está sonando
        search_query = self.player_manager.get_now_playing_search_query()
        
        if search_query:
            # Establecer la consulta en el cuadro de búsqueda
            self.search_box.setText(search_query)
            
            # Iniciar la búsqueda
            self.search_handler.perform_search()
        else:
            print("No se pudo obtener información de la reproducción actual")

    # def _handle_playing_button(self):
    #     """
    #     Maneja el clic en el botón de 'reproduciendo ahora'.
    #     Obtiene la canción actual y la muestra en el árbol.
    #     """
    #     print("Botón de 'reproduciendo ahora' pulsado")
        
    #     if not hasattr(self, 'player_manager'):
    #         print("ERROR: player_manager no inicializado")
    #         return
            
    #     # Obtener la ruta del archivo en reproducción
    #     current_path = self.player_manager.get_now_playing()
    #     if not current_path:
    #         print("No hay nada reproduciéndose actualmente")
    #         return
            
    #     print(f"Actualmente reproduciendo: {current_path}")
        
    #     # Buscar la canción en la base de datos
    #     conn = self.db_manager._get_connection()
    #     if not conn:
    #         print("No se pudo conectar a la base de datos")
    #         return
            
    #     try:
    #         cursor = conn.cursor()
    #         # Buscar la canción por ruta de archivo
    #         cursor.execute("""
    #             SELECT id, title, artist, album
    #             FROM songs
    #             WHERE file_path = ?
    #         """, (current_path,))
            
    #         song = cursor.fetchone()
    #         if not song:
    #             print(f"No se encontró la canción en la base de datos: {current_path}")
    #             return
                
    #         song_id = song['id']
    #         artist_name = song['artist']
    #         album_name = song['album']
            
    #         print(f"Canción encontrada: ID={song_id}, Artista={artist_name}, Álbum={album_name}")
            
    #         # Buscar el ID del artista
    #         cursor.execute("""
    #             SELECT id
    #             FROM artists
    #             WHERE name = ?
    #         """, (artist_name,))
            
    #         artist_row = cursor.fetchone()
    #         if not artist_row:
    #             print(f"No se encontró el artista en la base de datos: {artist_name}")
    #             return
                
    #         artist_id = artist_row['id']
            
    #         # Buscar el ID del álbum
    #         cursor.execute("""
    #             SELECT id
    #             FROM albums
    #             WHERE name = ? AND artist_id = ?
    #         """, (album_name, artist_id))
            
    #         album_row = cursor.fetchone()
    #         if not album_row:
    #             print(f"No se encontró el álbum en la base de datos: {album_name}")
    #             return
                
    #         album_id = album_row['id']
            
    #         # Ahora que tenemos los IDs, actualizar la vista
    #         # Para mostrar la discografía del artista con el álbum desplegado
    #         self.ui_updater.update_artist_view(artist_id)
            
    #         # Expandir el álbum correspondiente
    #         for i in range(self.results_tree_widget.topLevelItemCount()):
    #             artist_item = self.results_tree_widget.topLevelItem(i)
    #             artist_data = artist_item.data(0, Qt.ItemDataRole.UserRole)
                
    #             if artist_data and artist_data.get('type') == 'artist' and artist_data.get('id') == artist_id:
    #                 # Expandir el artista
    #                 artist_item.setExpanded(True)
                    
    #                 # Buscar y expandir el álbum
    #                 for j in range(artist_item.childCount()):
    #                     album_item = artist_item.child(j)
    #                     album_data = album_item.data(0, Qt.ItemDataRole.UserRole)
                        
    #                     if album_data and album_data.get('type') == 'album' and album_data.get('id') == album_id:
    #                         # Expandir el álbum
    #                         album_item.setExpanded(True)
                            
    #                         # Buscar y seleccionar la canción
    #                         for k in range(album_item.childCount()):
    #                             song_item = album_item.child(k)
    #                             song_data = song_item.data(0, Qt.ItemDataRole.UserRole)
                                
    #                             if song_data and song_data.get('type') == 'song' and song_data.get('id') == song_id:
    #                                 # Seleccionar la canción
    #                                 self.results_tree_widget.setCurrentItem(song_item)
    #                                 break
                            
    #                         break
                    
    #                 break
            
    #         print("Árbol actualizado con la canción actual")
    #     except Exception as e:
    #         print(f"Error al buscar la canción actual: {e}")
    #         import traceback
    #         traceback.print_exc()
    #     finally:
    #         conn.close()

    def _handle_next_button(self):
        """Maneja el clic en el botón de siguiente pista."""
        print("Botón siguiente pulsado")
        
        if not hasattr(self, 'player_manager'):
            print("ERROR: player_manager no inicializado")
            return
            
        result = self.player_manager.next_track()
        print(f"Resultado del comando siguiente: {result}")

    def _handle_prev_button(self):
        """Maneja el clic en el botón de pista anterior."""
        print("Botón anterior pulsado")
        
        if not hasattr(self, 'player_manager'):
            print("ERROR: player_manager no inicializado")
            return
            
        result = self.player_manager.previous_track()
        print(f"Resultado del comando anterior: {result}")

    def _handle_stop_button(self):
        """Maneja el clic en el botón de detener."""
        print("Botón detener pulsado")
        
        if not hasattr(self, 'player_manager'):
            print("ERROR: player_manager no inicializado")
            return
            
        result = self.player_manager.stop()
        print(f"Resultado del comando detener: {result}")



    def _handle_folder_button(self):
        """Abre la carpeta o archivo del elemento seleccionado en el explorador de archivos."""
        print("Botón de carpeta pulsado")
        
        # Obtener el elemento seleccionado
        selected_items = self.results_tree_widget.selectedItems()
        if not selected_items:
            print("No hay elementos seleccionados para abrir")
            return
            
        selected_item = selected_items[0]
        item_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            print("No se encontraron datos del elemento para el elemento seleccionado")
            return
            
        item_type = item_data.get('type')
        item_id = item_data.get('id')
        
        print(f"Elemento seleccionado para abrir carpeta: tipo={item_type}, id={item_id}")
        
        # Determinar la ruta a abrir según el tipo de elemento
        path_to_open = None
        
        if item_type == 'song':
            # Para canciones, obtenemos la ruta del archivo
            song = self.db_manager.get_song_details(item_id)
            if song:
                if hasattr(song, 'keys') and 'file_path' in song.keys():
                    file_path = song['file_path']
                elif isinstance(song, dict) and 'file_path' in song:
                    file_path = song['file_path']
                
                # Si tenemos la ruta del archivo, obtener la carpeta que lo contiene
                if file_path:
                    # Usar os.path.abspath para asegurarse de que la ruta es absoluta
                    from pathlib import Path
                    file_path = os.path.abspath(file_path)
                    print(f"Ruta absoluta del archivo: {file_path}")
                    path_to_open = str(Path(file_path).parent)
                    print(f"Carpeta padre a abrir: {path_to_open}")
        
        elif item_type == 'album':
            # Para álbumes, buscar la carpeta del álbum
            album = self.db_manager.get_album_details(item_id)
            if album:
                if hasattr(album, 'keys') and 'folder_path' in album.keys():
                    folder_path = album['folder_path']
                elif isinstance(album, dict) and 'folder_path' in album:
                    folder_path = album['folder_path']
                
                if folder_path:
                    # Usar os.path.abspath para asegurarse de que la ruta es absoluta
                    folder_path = os.path.abspath(folder_path)
                    path_to_open = folder_path
                    print(f"Carpeta del álbum a abrir: {path_to_open}")
        
        elif item_type == 'artist':
            # Para artistas, buscar la carpeta superior común a todos los álbumes
            albums = self.db_manager.get_artist_albums(item_id)
            if albums:
                # Almacenar todas las rutas de carpetas de álbumes válidas
                album_paths = []
                for album in albums:
                    folder_path = None
                    if hasattr(album, 'keys') and 'folder_path' in album.keys():
                        folder_path = album['folder_path']
                    elif isinstance(album, dict) and 'folder_path' in album:
                        folder_path = album['folder_path']
                    
                    if folder_path and os.path.exists(folder_path):
                        album_paths.append(os.path.abspath(folder_path))
                
                if album_paths:
                    # Encontrar la carpeta común que contiene todos los álbumes
                    from pathlib import Path
                    common_parent = None
                    
                    for album_path in album_paths:
                        # Obtener el directorio padre del álbum (un nivel arriba)
                        parent_dir = Path(album_path).parent
                        
                        # Si es el primer álbum o si esta carpeta contiene la anterior carpeta común
                        if common_parent is None:
                            common_parent = parent_dir
                        else:
                            # Mientras las rutas no sean iguales, subir un nivel
                            current = parent_dir
                            previous = common_parent
                            
                            # Encontrar el ancestro común
                            while str(current) != str(previous):
                                if len(str(current)) > len(str(previous)):
                                    current = current.parent
                                else:
                                    previous = previous.parent
                            
                            common_parent = current
                    
                    if common_parent:
                        path_to_open = str(common_parent)
                        print(f"Carpeta común de artista a abrir: {path_to_open}")
                    else:
                        # Si no se puede determinar una carpeta común, usar la primera disponible
                        first_album_path = album_paths[0]
                        path_to_open = str(Path(first_album_path).parent)
                        print(f"No se pudo determinar carpeta común, usando primera disponible: {path_to_open}")
        
        # Si no se encontró ninguna ruta, intentar buscar directamente en la base de datos
        if not path_to_open or not os.path.exists(path_to_open):
            print(f"No se encontró una ruta válida para abrir: {path_to_open}")
            conn = self.db_manager._get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    
                    if item_type == 'song':
                        cursor.execute("SELECT file_path FROM songs WHERE id = ?", (item_id,))
                        result = cursor.fetchone()
                        if result and result['file_path'] and os.path.exists(result['file_path']):
                            from pathlib import Path
                            file_path = os.path.abspath(result['file_path'])
                            path_to_open = str(Path(file_path).parent)
                    
                    elif item_type == 'album':
                        cursor.execute("SELECT folder_path FROM albums WHERE id = ?", (item_id,))
                        result = cursor.fetchone()
                        if result and result['folder_path'] and os.path.exists(result['folder_path']):
                            path_to_open = os.path.abspath(result['folder_path'])
                    
                    elif item_type == 'artist':
                        # Obtener todas las rutas de álbumes para este artista
                        cursor.execute("""
                            SELECT folder_path FROM albums 
                            WHERE artist_id = ? AND folder_path IS NOT NULL
                        """, (item_id,))
                        results = cursor.fetchall()
                        
                        album_paths = []
                        for result in results:
                            if result['folder_path'] and os.path.exists(result['folder_path']):
                                album_paths.append(os.path.abspath(result['folder_path']))
                        
                        if album_paths:
                            # Encontrar la carpeta común que contiene todos los álbumes
                            from pathlib import Path
                            common_parent = None
                            
                            for album_path in album_paths:
                                parent_dir = Path(album_path).parent
                                
                                if common_parent is None:
                                    common_parent = parent_dir
                                else:
                                    # Mientras las rutas no sean iguales, subir un nivel
                                    current = parent_dir
                                    previous = common_parent
                                    
                                    while str(current) != str(previous):
                                        if len(str(current)) > len(str(previous)):
                                            current = current.parent
                                        else:
                                            previous = previous.parent
                                    
                                    common_parent = current
                            
                            if common_parent:
                                path_to_open = str(common_parent)
                            elif album_paths:
                                # Usar el directorio padre del primer álbum si no hay común
                                path_to_open = str(Path(album_paths[0]).parent)
                
                except Exception as e:
                    print(f"Error al obtener ruta de la base de datos: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    conn.close()
        
        # Asegurarse de que path_to_open es una ruta absoluta antes de abrirla
        if path_to_open:
            path_to_open = os.path.abspath(path_to_open)
            
        # Abrir la carpeta si se encontró una ruta válida
        if path_to_open and os.path.exists(path_to_open):
            print(f"Abriendo ruta absoluta: {path_to_open}")
            self._open_path_in_file_explorer(path_to_open)
        else:
            print(f"No se pudo encontrar una ruta válida para abrir: {path_to_open}")

    def _open_path_in_file_explorer(self, path):
        """
        Abre una ruta en el explorador de archivos del sistema operativo.
        Compatible con Linux, Windows y macOS.
        
        Args:
            path: Ruta del archivo o directorio a abrir
        """
        import platform
        import subprocess
        import os
        import shlex
        from pathlib import Path
        
        if not path or not os.path.exists(path):
            print(f"La ruta no existe: {path}")
            return False
        
        try:
            # Asegurarse de que estamos usando una ruta absoluta
            # Evitar que se añada el directorio del proyecto al principio
            path = str(Path(path).absolute())
            
            print(f"Ruta absoluta a abrir: {path}")
            
            system = platform.system()
            print(f"Sistema operativo: {system}")
            
            if system == 'Linux':
                # Primero intentamos con el explorador específico (Thunar, Nautilus, Dolphin, etc.)
                file_explorers = ['thunar', 'nautilus', 'dolphin', 'pcmanfm', 'nemo']
                
                # Verificar qué exploradores están instalados
                for explorer in file_explorers:
                    # Comprobar si el explorador está disponible en el sistema
                    which_result = subprocess.run(['which', explorer], 
                                                stdout=subprocess.PIPE, 
                                                stderr=subprocess.PIPE)
                    
                    if which_result.returncode == 0:
                        explorer_path = which_result.stdout.decode().strip()
                        print(f"Usando explorador: {explorer} ({explorer_path})")
                        
                        # Usar directamente la ruta absoluta sin ningún escape adicional
                        print(f"Ejecutando: {explorer_path} {path}")
                        
                        # Ejecutar el explorador con la ruta
                        subprocess.Popen([explorer_path, path], 
                                        start_new_session=True,
                                        stdout=subprocess.DEVNULL, 
                                        stderr=subprocess.DEVNULL)
                        return True
                
                # Si no encontramos ningún explorador específico, intentar con xdg-open
                print(f"No se encontró ningún explorador específico, usando xdg-open: {path}")
                subprocess.Popen(['xdg-open', path], 
                                start_new_session=True,
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
            
            elif system == 'Windows':
                # En Windows, usar explorer.exe
                print(f"Abriendo con explorer: {path}")
                # Reemplazar / por \ para compatibilidad con Windows
                path = path.replace('/', '\\')
                subprocess.Popen(['explorer', path], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
            
            elif system == 'Darwin':  # macOS
                # En macOS, usar open
                print(f"Abriendo con open: {path}")
                subprocess.Popen(['open', path], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
            
            else:
                print(f"Sistema operativo no reconocido: {system}")
                return False
            
            return True
        
        except Exception as e:
            print(f"Error al abrir la ruta en el explorador: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _handle_apply_time_filter(self):
        """Manejador directo del botón apply_time_filter."""
        print("Botón apply_time_filter pulsado - método directo")
        
        # Verificar que tenemos referencias a los controles necesarios
        if not hasattr(self, 'time_value') or not hasattr(self, 'time_unit'):
            # Intentar encontrarlos directamente
            time_value = self.findChild(QSpinBox, "time_value")
            time_unit = self.findChild(QComboBox, "time_unit")
            
            if time_value and time_unit:
                self.time_value = time_value
                self.time_unit = time_unit
            else:
                print("ERROR: No se pudieron encontrar los controles de tiempo")
                return
        
        # Obtener el valor y la unidad de tiempo seleccionados
        time_value = self.time_value.value()
        time_unit_index = self.time_unit.currentIndex()
        
        # Obtener el estado de only_local
        only_local = False
        if hasattr(self, 'only_local_files') and self.only_local_files:
            only_local = self.only_local_files.isChecked()
        
        # Convertir índice a unidad de tiempo
        time_unit = ""
        if time_unit_index == 0:
            time_unit = "week"
        elif time_unit_index == 1:
            time_unit = "month"
        elif time_unit_index == 2:
            time_unit = "year"
        
        print(f"Filtrando por {time_value} {time_unit}(s), only_local: {only_local}")
        
        # Llamar directamente al método de búsqueda en search_handler
        if hasattr(self, 'search_handler') and self.search_handler:
            # Asegurarnos de que la búsqueda es visible
            if hasattr(self, 'results_tree_widget'):
                self.results_tree_widget.clear()
            
            # Llamar al método de búsqueda
            self.search_handler._search_recent(str(time_value), time_unit, only_local)
        else:
            print("ERROR: search_handler no está disponible")


    def _handle_apply_year(self):
        """Manejador directo del botón apply_year."""
        print("Botón apply_year pulsado - método directo")
        
        # Verificar que tenemos referencias al control necesario
        if not hasattr(self, 'year_only_spin'):
            # Intentar encontrarlo directamente
            year_only_spin = self.findChild(QSpinBox, "year_only_spin")
            
            if year_only_spin:
                self.year_only_spin = year_only_spin
            else:
                print("ERROR: No se pudo encontrar el control year_only_spin")
                return
        
        # Obtener el año seleccionado
        year_value = self.year_only_spin.value()
        
        # Obtener el estado de only_local
        only_local = False
        if hasattr(self, 'only_local_files') and self.only_local_files:
            only_local = self.only_local_files.isChecked()
        
        print(f"Filtrando por año: {year_value}, only_local: {only_local}")
        
        # Limpiar resultados actuales
        if hasattr(self, 'results_tree_widget'):
            self.results_tree_widget.clear()
        
        # Realizar la búsqueda por año usando search_handler
        if hasattr(self, 'search_handler') and self.search_handler:
            self.search_handler._search_by_year(str(year_value), only_local)
        else:
            print("ERROR: search_handler no está disponible")


    def _handle_apply_decade(self):
        """Manejador directo del botón de filtro por décadas."""
        print("Botón de filtro por décadas pulsado - método directo")
        
        # Verificar que tenemos referencias a los controles necesarios
        if not hasattr(self, 'year_spin_begin'):
            # Intentar encontrarlo directamente
            year_spin_begin = self.findChild(QSpinBox, "year_spin_begin")
            
            if year_spin_begin:
                self.year_spin_begin = year_spin_begin
            else:
                print("ERROR: No se pudo encontrar el control year_spin_begin")
                return
        
        if not hasattr(self, 'year_spin_end'):
            # Intentar encontrarlo directamente
            year_spin_end = self.findChild(QSpinBox, "year_spin_end")
            
            if year_spin_end:
                self.year_spin_end = year_spin_end
            else:
                print("ERROR: No se pudo encontrar el control year_spin_end")
                return
        
        # Obtener los años seleccionados
        year_begin = self.year_spin_begin.value()
        year_end = self.year_spin_end.value()
        
        # Verificar que el rango es válido
        if year_begin > year_end:
            print(f"Rango de años inválido: {year_begin}-{year_end}")
            return
        
        # Obtener el estado de only_local
        only_local = False
        if hasattr(self, 'only_local_files') and self.only_local_files:
            only_local = self.only_local_files.isChecked()
        
        print(f"Filtrando por rango de años: {year_begin}-{year_end}, only_local: {only_local}")
        
        # Limpiar resultados actuales
        if hasattr(self, 'results_tree_widget'):
            self.results_tree_widget.clear()
        
        # Realizar la búsqueda por rango de años usando search_handler
        if hasattr(self, 'search_handler') and self.search_handler:
            # Crear un string con el formato "año_inicio-año_fin"
            year_range = f"{year_begin}-{year_end}"
            self.search_handler._search_by_year_range(year_range, only_local)
        else:
            print("ERROR: search_handler no está disponible")


# EDIT BUTTONS 
    def _connect_edit_buttons(self):
        """Connect the edit_buttons button to the dialog."""
        # Find the edit_buttons button (the one with the ghost icon)
        edit_buttons = self.findChild(QPushButton, "pushButton")
        if edit_buttons:
            try:
                edit_buttons.clicked.disconnect()
            except:
                pass
            edit_buttons.clicked.connect(self._show_button_config_dialog)
            print("Botón 'edit_buttons' (pushButton) conectado")
        else:
            print("WARNING: Button 'pushButton' not found")
            # Try to find by tooltip
            for button in self.findChildren(QPushButton):
                if button.toolTip() == "Personalizar botones":
                    print(f"Found edit button by tooltip: {button.objectName()}")
                    try:
                        button.clicked.disconnect()
                    except:
                        pass
                    button.clicked.connect(self._show_button_config_dialog)
                    print("Botón 'edit_buttons' conectado by tooltip")
                    return

    def _show_button_config_dialog(self):
        """Show the dialog to configure visible buttons."""
        try:
            # Import the dialog class
            from modules.submodules.fuzzy.button_config_dialog import ButtonConfigDialog
            
            # Get current button configuration
            print("Getting current button configuration...")
            current_config = self._get_current_button_config()
            print(f"Current configuration: {current_config}")
            
            # Create dialog
            dialog = ButtonConfigDialog(self, current_config)
            
            # Get available buttons
            print("Getting available buttons...")
            available_buttons = self._get_available_buttons()
            print(f"Found {len(available_buttons)} available buttons")
            
            # Set available buttons in dialog
            dialog.set_available_buttons(available_buttons)
            
            # Show dialog and process result
            print("Showing dialog...")
            result = dialog.exec()
            print(f"Dialog result: {result}")
            
            if result == 1:  # QDialog.Accepted (using the value directly)
                print("Dialog accepted, applying new configuration...")
                # Get new configuration
                new_config = dialog.get_button_configuration()
                print(f"New configuration: {new_config}")
                # Apply the new configuration
                self._apply_button_configuration(new_config)
                # Save the configuration
                self._save_button_configuration(new_config)
            else:
                print("Dialog rejected, keeping current configuration")
        except Exception as e:
            print(f"Error showing button config dialog: {e}")
            import traceback
            traceback.print_exc()

    def _get_available_buttons(self):
        """Get list of all available buttons in buttons_container."""
        buttons = []
        if hasattr(self, 'buttons_container'):
            # Find all buttons in the container
            for button in self.buttons_container.findChildren(QPushButton):
                # Get button name
                name = button.objectName()
                
                # Skip buttons without proper names
                if not name or name.isspace():
                    continue
                    
                # Try to create a display name by removing '_button' suffix and capitalizing
                if name.endswith('_button'):
                    display_name = name[:-7].capitalize()
                else:
                    display_name = name.capitalize()
                
                # Special cases for better display names
                button_display_names = {
                    'play_button': 'Reproducir',
                    'add_to_queue': 'Añadir a Cola',
                    'spotify_button': 'Spotify',
                    'folder_button': 'Carpeta',
                    'playing_button': 'Reproduciendo',
                    'muspy_button': 'Muspy',
                    'feeds_button': 'Feeds',
                    'scrobble_button': 'Last.fm',
                    'muspy_button_2': 'Detener',
                    'play_button_3': 'Anterior',
                    'play_button_4': 'Siguiente',
                    'jaangle_button': 'Juego',
                    'db_editor_button': 'Editor BD',
                    'url_playlists_button': 'Playlists URL',
                    'conciertos_button': 'Conciertos',
                    'stats_button': 'Estadísticas'
                }
                
                if name in button_display_names:
                    display_name = button_display_names[name]
                
                buttons.append({
                    'name': name,
                    'display_name': display_name,
                    'widget': button
                })
                
        print(f"Found {len(buttons)} available buttons: {[b['name'] for b in buttons]}")
        return buttons

    def _get_current_button_config(self):
        """Get current button configuration."""
        # Try to load config from settings
        from PyQt6.QtCore import QSettings
        settings = QSettings("MusicApp", "ButtonConfig")
        
        # Check if we have a saved configuration
        if settings.contains("button_config"):
            # Load and return the configuration
            config = settings.value("button_config", [])
            if isinstance(config, list) and len(config) == 16:
                return config
        
        # Default configuration: build a 4x4 grid reflecting current layout
        if hasattr(self, 'buttons_container'):
            # Create an empty grid
            grid = [["none" for _ in range(4)] for _ in range(4)]
            
            # Get layout
            layout = self.buttons_container.layout()
            if layout and isinstance(layout, QGridLayout):
                # Get each button from the layout
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        if isinstance(widget, QPushButton):
                            # Try to get position information
                            pos_info = layout.getItemPosition(i)
                            if pos_info:
                                row, col = pos_info[0], pos_info[1]
                                if 0 <= row < 4 and 0 <= col < 4:
                                    # Store button name in the grid
                                    grid[row][col] = widget.objectName()
            
            # Flatten grid to a list
            config = []
            for row in grid:
                config.extend(row)
            
            # Ensure we have exactly 16 items
            while len(config) < 16:
                config.append("none")
            
            return config[:16]  # Only take first 16 items if somehow we have more
        
        # Fallback: empty configuration
        return ["none"] * 16

    def _apply_button_configuration(self, config):
        """Apply button configuration: show/hide buttons and rearrange."""
        if not hasattr(self, 'buttons_container'):
            print("ERROR: buttons_container not found")
            return
        
        print(f"Applying button configuration: {config}")
        
        # Get all buttons by name
        all_buttons = {}
        for button in self.buttons_container.findChildren(QPushButton):
            button_name = button.objectName()
            if button_name:  # Skip buttons without names
                all_buttons[button_name] = button
                # Initially hide all buttons
                button.setVisible(False)
        
        print(f"Found {len(all_buttons)} buttons in container")
        
        # Get grid layout
        layout = self.buttons_container.layout()
        if not layout:
            print("Creating new QGridLayout for buttons_container")
            layout = QGridLayout(self.buttons_container)
        elif not isinstance(layout, QGridLayout):
            print("WARNING: buttons_container layout is not a QGridLayout")
            # Remove old layout and create new one
            QWidget().setLayout(self.buttons_container.layout())
            layout = QGridLayout(self.buttons_container)
        
        # Clear the grid layout
        while layout.count():
            item = layout.takeAt(0)
            if item and item.widget():
                layout.removeWidget(item.widget())
        
        # Set some spacing in the layout
        layout.setSpacing(5)
        
        # Apply new configuration
        for idx, button_name in enumerate(config):
            if button_name == "none":
                continue
                
            if button_name in all_buttons:
                button = all_buttons[button_name]
                row = idx // 4
                col = idx % 4
                
                print(f"Placing {button_name} at position ({row}, {col})")
                
                # Make button visible and add to layout
                button.setVisible(True)
                layout.addWidget(button, row, col)
            else:
                print(f"Button not found: {button_name}")
        
        # Update layout
        self.buttons_container.setLayout(layout)
        print("Button configuration applied successfully")
    
    def _save_button_configuration(self, config):
        """Save button configuration to settings."""
        from PyQt6.QtCore import QSettings
        settings = QSettings("MusicApp", "ButtonConfig")
        settings.setValue("button_config", config)
        print("Button configuration saved successfully")

    # This method needs to be added to _connect_additional_signals
    def _load_saved_button_configuration(self):
        """Load and apply saved button configuration on startup."""
        # Try to load config from settings
        from PyQt6.QtCore import QSettings
        settings = QSettings("MusicApp", "ButtonConfig")
        
        # Check if we have a saved configuration
        if settings.contains("button_config"):
            # Load the configuration
            config = settings.value("button_config", [])
            # Apply the configuration
            self._apply_button_configuration(config)
            print("Loaded saved button configuration")


# INTEGRACIONES CON OTROS MODULOS

    def set_tab_manager(self, tab_manager):
        """Recibir referencia al gestor de pestañas"""
        self.tab_manager = tab_manager
        
        # Also update the module_integrator if it exists
        if hasattr(self, 'module_integrator') and self.module_integrator:
            self.module_integrator.parent.tab_manager = tab_manager
            print("Tab manager reference updated in module_integrator")