from PyQt6.QtWidgets import QWidget, QTreeWidgetItem, QPushButton, QLabel, QVBoxLayout, QCheckBox
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


    def _connect_additional_signals(self):
        """Connect signals that depend on initialized components"""
        # Conexiones que dependen de componentes como search_handler
        if hasattr(self, 'search_box') and hasattr(self, 'search_handler'):
            self.search_box.returnPressed.connect(self.search_handler.perform_search)
        
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
        """Toggle between info view and feeds view."""
        if not hasattr(self, 'info_panel_stacked') or not self.info_panel_stacked:
            return
        
        # Get the current widget
        current_widget = self.info_panel_stacked.currentWidget()
        
        # Toggle between the two pages
        if current_widget == self.info_page:
            self.info_panel_stacked.setCurrentWidget(self.feeds_page)
            # Update button text/tooltip to reflect current state
            if hasattr(self, 'feeds_button'):
                self.feeds_button.setToolTip("Mostrar información")
        else:
            self.info_panel_stacked.setCurrentWidget(self.info_page)
            # Update button text/tooltip to reflect current state
            if hasattr(self, 'feeds_button'):
                self.feeds_button.setToolTip("Mostrar feeds")