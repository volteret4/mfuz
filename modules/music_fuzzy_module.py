import sys
import os
from PyQt6 import uic
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QApplication, QTreeWidgetItem, 
                             QAbstractItemView, QMenu, QStackedWidget, QLineEdit,
                             QCheckBox, QSplitter, QLabel, QPushButton, QStackedWidget,
                             QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
import subprocess
import traceback
import resources_rc

from modules.submodules.fuzzy.database_submodule import MusicDatabase
from modules.submodules.fuzzy.media_finder import MediaFinder
from modules.submodules.fuzzy.links_buttons_submodule import LinkButtonsManager
from modules.submodules.fuzzy.artist_view_submodule import ArtistView
from modules.submodules.fuzzy.album_view_submodule import AlbumView
from modules.submodules.fuzzy.track_view_submodule import TrackView
from modules.submodules.fuzzy.feed_view_submodule import FeedsView
from modules.submodules.fuzzy.search_parser import SearchParser  # Assuming you'll refactor your search parser too
from modules.submodules.fuzzy.entity_view_submodule import EntityView
from modules.submodules.fuzzy.search_panel import SearchPanel 
# Import base module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule, PROJECT_ROOT

class MusicBrowser(BaseModule):
    """
    Main music browser module with a modular architecture.
    """
    
    def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
        """
        Initialize the music browser module.
        
        Args:
            parent (QWidget, optional): Parent widget
            theme (str, optional): UI theme
            **kwargs: Additional keyword arguments
        """
        # Extract module-specific arguments
        self.db_path = kwargs.pop('db_path', '')
        self.artist_images_dir = kwargs.pop('artist_images_dir', '')
        self.hotkeys_config = kwargs.pop('hotkeys', None)
        
        # Initialize parent class
        super().__init__(parent=parent, theme=theme, **kwargs)
        
        # Initialize components
        self.db = MusicDatabase(self.db_path)
        self.media_finder = MediaFinder(self.artist_images_dir)
        self.search_parser = SearchParser()
        

        # Initialize UI
        self.setup_hotkeys(self.hotkeys_config)
        
    def init_ui(self):
        """Inicializa la interfaz de usuario."""
        # Preparar layout
        if self.layout():
            QWidget().setLayout(self.layout())
            
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Cargar el archivo UI principal
        ui_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "music_fuzzy_module.ui")
        if os.path.exists(ui_file_path):
            try:
                # Cargar UI
                self.main_ui = QWidget()
                uic.loadUi(ui_file_path, self.main_ui)
                main_layout.addWidget(self.main_ui)
                
                # Establecer objectName para estilo CSS
                self.setObjectName("music_fuzzy_module")
                
                # Configurar componentes y referencias UI
                self._setup_ui_references()
                self._load_results_tree()
                self._setup_search_panel()
                self._setup_details_panel()
                
                # Conectar señales
                self._connect_signals()
                
                # Aplicar tema
                self.apply_theme(theme=getattr(self, 'selected_theme', 'Tokyo Night'))
                
            except Exception as e:
                print(f"Error cargando UI: {e}")
                traceback.print_exc()
                self._create_fallback_ui()
        else:
            print(f"Archivo UI no encontrado: {ui_file_path}")
            self._create_fallback_ui()

    def _create_fallback_ui(self):
        """Create a fallback UI if the main UI file can't be loaded."""
        # Clear existing layout if any
        if self.layout():
            QWidget().setLayout(self.layout())
            
        # Create a simple layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Add a label explaining the issue
        from PyQt6.QtWidgets import QLabel
        error_label = QLabel("Error loading Music Browser UI. Check console for details.")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(error_label)
        
        print("Using fallback UI due to loading errors")

    def _setup_search_panel(self):
        """Set up the search panel component."""
        # Create search panel
        self.search_panel = SearchPanel(self)
        
        # Get reference to top container from UI
        top_container = self.main_ui.findChild(QWidget, "top_container")
        if top_container and top_container.layout():
            # Replace existing search widgets with search panel
            while top_container.layout().count():
                item = top_container.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
            top_container.layout().addWidget(self.search_panel)
            
            # Connect search panel signals
            self.search_panel.searchRequested.connect(self.search)
            self.search_panel.filterRequested.connect(self.search)
            
            # Set custom button handlers
            self.search_panel.set_custom_button_handlers(
                button1_handler=self.buscar_musica_en_reproduccion
            )
        else:
            print(f"Warning: top_container not found in UI")
    
    def _setup_ui_references(self):
        """Obtiene referencias a widgets del UI cargado."""
        # Referencias a widgets principales
        self.search_box = self.main_ui.findChild(QLineEdit, "search_box")
        self.advanced_settings_check = self.main_ui.findChild(QCheckBox, "advanced_settings_check")
        self.advanced_settings_container = self.main_ui.findChild(QWidget, "advanced_settings_container")
        self.results_tree_container = self.main_ui.findChild(QWidget, "results_tree_container")
        self.main_splitter = self.main_ui.findChild(QSplitter, "main_splitter")
        
        # Referencias a etiquetas de imagen
        self.cover_label = self.main_ui.findChild(QLabel, "cover_label")
        self.artist_image_label = self.main_ui.findChild(QLabel, "artist_image_label")
        
        # Referencias a botones de acción
        self.play_button = self.main_ui.findChild(QPushButton, "play_button")
        self.folder_button = self.main_ui.findChild(QPushButton, "folder_button")
        self.spotify_button = self.main_ui.findChild(QPushButton, "spotify_button")
        
        # Referencias a botones personalizados
        self.custom_button1 = self.main_ui.findChild(QPushButton, "custom_button1")
        self.custom_button2 = self.main_ui.findChild(QPushButton, "custom_button2")
        self.custom_button3 = self.main_ui.findChild(QPushButton, "custom_button3")
        
        # Seguimiento de botones avanzados para alternar
        self.advanced_buttons = []
        if self.custom_button1:
            self.advanced_buttons.append(self.custom_button1)
        if self.custom_button2:
            self.advanced_buttons.append(self.custom_button2)
        if self.custom_button3:
            self.advanced_buttons.append(self.custom_button3)
        
        # Referencias a los grupos de enlaces (ya definidos en el archivo UI)
        self.artist_links_group = self.main_ui.findChild(QGroupBox, "artist_links_group")
        self.album_links_group = self.main_ui.findChild(QGroupBox, "album_links_group")
        
        print(f"[DEBUG] Referencias a grupos de enlaces: artist={self.artist_links_group}, album={self.album_links_group}")
        
        # Referencia al botón de feeds
        self.feeds_button = self.main_ui.findChild(QPushButton, "feeds_button")

    def _setup_details_panel(self):
        """Set up the details panel with modular views."""
        # Importar LinkButtonsManager explícitamente aquí
        from modules.submodules.fuzzy.links_buttons_submodule import LinkButtonsManager
        
        # Obtener referencias a los grupos desde el UI
        self.artist_links_group = self.main_ui.findChild(QGroupBox, "artist_links_group")
        self.album_links_group = self.main_ui.findChild(QGroupBox, "album_links_group")
        
        if not self.artist_links_group or not self.album_links_group:
            print("[ERROR] No se pudieron encontrar los grupos de enlaces en el UI")
            print(f"[DEBUG] artist_links_group: {self.artist_links_group}")
            print(f"[DEBUG] album_links_group: {self.album_links_group}")
            return
        
        # Crear link buttons manager con las referencias a los grupos existentes
        print("[DEBUG] Creando LinkButtonsManager...")
        self.link_buttons = LinkButtonsManager(
            artist_group=self.artist_links_group,
            album_group=self.album_links_group
        )
        
        # Obtener referencia al widget apilado desde el UI
        # Primero intentar con el nombre exacto
        self.details_stacked_widget = self.main_ui.findChild(QStackedWidget, "info_panel_stacked")
        
        # Si no lo encuentra, intentar buscar cualquier QStackedWidget en el UI
        if not self.details_stacked_widget:
            print("[DEBUG] No se encontró info_panel_stacked por nombre, buscando cualquier QStackedWidget...")
            all_stacked_widgets = self.main_ui.findChildren(QStackedWidget)
            if all_stacked_widgets:
                self.details_stacked_widget = all_stacked_widgets[0]
                print(f"[DEBUG] Encontrado QStackedWidget alternativo: {self.details_stacked_widget}")
            else:
                print("[ERROR] No se encontró ningún QStackedWidget en el UI")
                # Crear uno programáticamente como última opción
                details_container = self.main_ui.findChild(QWidget, "info_container")
                if details_container and details_container.layout():
                    print("[DEBUG] Creando QStackedWidget programáticamente...")
                    self.details_stacked_widget = QStackedWidget(details_container)
                    details_container.layout().addWidget(self.details_stacked_widget)
                else:
                    print("[ERROR] No se pudo crear un QStackedWidget, no se encontró contenedor adecuado")
                    return
        
        # Crear entity views
        self.entity_view = QWidget()
        entity_layout = QVBoxLayout(self.entity_view)
        entity_layout.setContentsMargins(0, 0, 0, 0)
        self.db = MusicDatabase(self.db_path)
        self.media_finder = MediaFinder(self.artist_images_dir)
        # Crear las vistas individuales
        self.artist_view = ArtistView(parent=self, db=self.db, 
                                    media_finder=self.media_finder, 
                                    link_buttons=self.link_buttons)
        self.album_view = AlbumView(parent=self, db=self.db, 
                                media_finder=self.media_finder, 
                                link_buttons=self.link_buttons)
        self.track_view = TrackView(parent=self, db=self.db, 
                                media_finder=self.media_finder, 
                                link_buttons=self.link_buttons)
        
        # Añadir vistas al contenedor
        entity_layout.addWidget(self.artist_view)
        entity_layout.addWidget(self.album_view)
        entity_layout.addWidget(self.track_view)
        
        # Ocultar todas las vistas inicialmente
        self.artist_view.hide()
        self.album_view.hide()
        self.track_view.hide()
        
        # Crear la vista de feeds
        self.feeds_view = FeedsView(parent=self, db=self.db)
        self.feeds_view.backRequested.connect(lambda: self.details_stacked_widget.setCurrentIndex(0))
        
        # Limpiar los widgets existentes en el stacked widget si hay alguno
        try:
            while self.details_stacked_widget.count() > 0:
                self.details_stacked_widget.removeWidget(self.details_stacked_widget.widget(0))
        except Exception as e:
            print(f"[DEBUG] Error al limpiar widgets del stacked widget: {e}")
        
        # Añadir vistas al widget apilado
        self.details_stacked_widget.addWidget(self.entity_view)
        self.details_stacked_widget.addWidget(self.feeds_view)
        
        # Mostrar la vista entity por defecto
        self.details_stacked_widget.setCurrentIndex(0)
        
        print("[DEBUG] _setup_details_panel completado correctamente")

    def _load_results_tree(self):
        """Load the results tree widget from UI file or create fallback."""
        # Try to load from UI file first
        ui_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "music_fuzzy_results_tree.ui")
        
        if os.path.exists(ui_file_path) and self.results_tree_container:
            try:
                # Clear existing layout if any
                if self.results_tree_container.layout():
                    while self.results_tree_container.layout().count():
                        item = self.results_tree_container.layout().takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                    QWidget().setLayout(self.results_tree_container.layout())
                
                # Create new layout
                container_layout = QVBoxLayout(self.results_tree_container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(0)
                
                # Load tree widget from UI
                self.results_tree_widget = QWidget()
                uic.loadUi(ui_file_path, self.results_tree_widget)
                container_layout.addWidget(self.results_tree_widget)
                
                # Get tree widget reference
                self.results_tree = self.results_tree_widget.results_tree
                
                # Configure tree
                self._configure_results_tree()
                
                print("Results tree loaded from UI file")
                
            except Exception as e:
                print(f"Error loading results tree UI: {e}")
                traceback.print_exc()
                self._create_fallback_tree()
        else:
            print("Results tree UI file not found, creating fallback")
            self._create_fallback_tree()
            
    def _configure_results_tree(self):
        """Configure the results tree widget."""
        if not self.results_tree:
            return
            
        # Set column widths
        self.results_tree.setColumnWidth(0, 300)  # Title column
        self.results_tree.setColumnWidth(1, 70)   # Year column
        self.results_tree.setColumnWidth(2, 100)  # Genre column
        
        # Configure selection behavior
        self.results_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Set up events
        self.results_tree.currentItemChanged.connect(self.handle_tree_item_change)
        self.results_tree.itemDoubleClicked.connect(self.handle_tree_item_double_click)
        self.results_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        
        # Configure tree appearance
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setExpandsOnDoubleClick(True)
        
    def _create_fallback_tree(self):
        """Create a fallback tree widget if loading from UI fails."""
        if not self.results_tree_container:
            return
            
        # Clear existing layout if any
        if self.results_tree_container.layout():
            while self.results_tree_container.layout().count():
                item = self.results_tree_container.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(self.results_tree_container.layout())
            
        # Create new layout
        container_layout = QVBoxLayout(self.results_tree_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Create tree widget
        from PyQt6.QtWidgets import QTreeWidget
        self.results_tree = QTreeWidget()
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setHeaderHidden(False)
        self.results_tree.setColumnCount(3)
        self.results_tree.setHeaderLabels(["Artistas / Álbumes / Canciones", "Año", "Género"])
        
        # Configure tree
        self._configure_results_tree()
        
        # Add to layout
        container_layout.addWidget(self.results_tree)
        
        print("Fallback tree created")
        
   
        
    def _connect_signals(self):
        """Connect UI signals to handlers."""
        # Search box
        self.search_box.textChanged.connect(self._on_search_text_changed)
        self.search_box.returnPressed.connect(self.search)
        
        # Advanced settings
        self.advanced_settings_check.stateChanged.connect(self.toggle_advanced_settings)
        
        # Action buttons
        self.play_button.clicked.connect(self.play_selected_item)
        self.folder_button.clicked.connect(self.open_selected_folder)
        self.spotify_button.clicked.connect(self.handle_spotify_button)
        
        # Custom buttons
        self.custom_button1.clicked.connect(self.buscar_musica_en_reproduccion)
        
        # Feeds button if available
        if self.feeds_button:
            self.feeds_button.clicked.connect(self.show_feeds)
            
    def _on_search_text_changed(self, text):
        """
        Handle search box text changes.
        Implementa una búsqueda automática al tipear.
        
        Args:
            text (str): Texto actual en el campo de búsqueda
        """
        # Si hay al menos 3 caracteres, ejecutar la búsqueda
        # o si hay prefijos especiales como "a:", "b:", etc.
        if len(text) >= 2 or any(prefix in text for prefix in ["a:", "b:", "g:", "l:", "t:", "aa:", "br:", "d:", "w:", "m:", "y:", "am:", "ay:"]):
            self.search(text)
    
    # Métodos faltantes que causan los errores        
    def handle_tree_item_double_click(self, item, column):
        """
        Handle double click on tree item - play the item.
        
        Args:
            item: The clicked tree widget item
            column: The column that was clicked
        """
        # Simple implementation: just play the item
        self.play_selected_item()
    
    def show_tree_context_menu(self, position):
        """
        Show context menu for the results tree.
        
        Args:
            position: Position where the context menu should be shown
        """
        item = self.results_tree.itemAt(position)
        if not item:
            return
            
        # Create the context menu
        context_menu = QMenu(self)
        
        # Add common actions
        play_action = context_menu.addAction("Reproducir")
        play_action.triggered.connect(self.play_selected_item)
        
        open_folder_action = context_menu.addAction("Abrir Carpeta")
        open_folder_action.triggered.connect(self.open_selected_folder)
        
        # Add item-specific actions based on type
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if isinstance(item_data, dict):
            # It's an artist or album
            if item_data.get('type') == 'artist':
                # Artist-specific actions
                search_artist_action = context_menu.addAction("Buscar por este Artista")
                search_artist_action.triggered.connect(
                    lambda: self.search_panel.set_search_text(f"a:{item_data.get('name')}")
                )
            elif item_data.get('type') == 'album':
                # Album-specific actions
                search_album_action = context_menu.addAction("Buscar por este Álbum")
                search_album_action.triggered.connect(
                    lambda: self.search_panel.set_search_text(f"b:{item_data.get('name')}")
                )
        else:
            # It's a track
            if len(item_data) > 2:  # Make sure we have title
                copy_title_action = context_menu.addAction("Copiar Título")
                copy_title_action.triggered.connect(
                    lambda: QApplication.clipboard().setText(item_data[2])
                )
            
            if len(item_data) > 0:  # Make sure we have ID
                spotify_action = context_menu.addAction("Buscar en Spotify")
                spotify_action.triggered.connect(self.handle_spotify_button)
                
        # Show the context menu
        context_menu.exec(self.results_tree.mapToGlobal(position))
            
    def handle_tree_item_change(self, current, previous):
        """
        Handle change of selected item in the tree.
        
        Args:
            current: Currently selected item
            previous: Previously selected item
        """
        if not current:
            self.clear_details()
            return
            
        # Get item data
        item_data = current.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            self.clear_details()
            return
            
        # Determine entity type and show appropriate view
        if isinstance(item_data, dict):
            # It's an artist or album
            if item_data.get('type') == 'artist':
                self.show_artist_details(current)
            elif item_data.get('type') == 'album':
                self.show_album_details(current)
        else:
            # It's a track
            self.show_track_details(current)
            


    def show_album_details(self, album_item):
        """
        Show album details with better visibility handling.
        
        Args:
            album_item: Tree item for an album
        """
        # Hide all views first
        self.artist_view.hide()
        self.album_view.show()
        self.track_view.hide()
        
        # Get album data
        item_data = album_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or not isinstance(item_data, dict) or item_data.get('type') != 'album':
            return
            
        # Collect all tracks
        tracks = []
        for i in range(album_item.childCount()):
            tracks.append(album_item.child(i))
            
        # Show album details
        self.album_view.show_entity(item_data, tracks)
        
        # Resto del código...
        
        # Forzar visibilidad de los contenedores
        print("[DEBUG] Forzando visibilidad de los contenedores de enlaces en show_album_details")
        
        if hasattr(self, 'album_links_group') and self.album_links_group:
            # Asegurar que tanto el contenedor como su padre estén visibles
            self.album_links_group.setVisible(True)
            self.album_links_group.show()
            
            parent = self.album_links_group.parent()
            if parent:
                parent.setVisible(True)
                parent.show()
        
        if hasattr(self, 'artist_links_group') and self.artist_links_group:
            # También mostrar el contenedor de artista para mantener consistencia
            self.artist_links_group.setVisible(True)
            self.artist_links_group.show()
        
        # Llamar a un método que nos ayude a verificar el estado
        self.debug_link_groups_status()

            
    def show_artist_details(self, artist_item):
        """
        Show artist details con mejor manejo de visibilidad.
        
        Args:
            artist_item: Tree item for an artist
        """
        # Hide all views first
        self.artist_view.show()
        self.album_view.hide()
        self.track_view.hide()
        
        # Get artist data
        item_data = artist_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or not isinstance(item_data, dict) or item_data.get('type') != 'artist':
            return
            
        # Show artist details
        self.artist_view.show_entity(item_data)
        
        # Update artist image
        artist_name = item_data.get('name')
        if artist_name and self.media_finder:
            artist_image_path = self.media_finder.find_artist_image(artist_name)
            self.media_finder.load_image_to_label(
                artist_image_path, 
                self.artist_image_label, 
                "No imagen de artista"
            )
            
        # Clear album image
        if self.cover_label:
            self.cover_label.setText("No imagen")
            
        # Set feeds button visibility
        if self.feeds_button:
            artist_id = self.db.get_entity_id('artist', artist_name)
            feeds = self.db.get_feeds_data('artist', artist_id) if artist_id else []
            self.feeds_button.setVisible(bool(feeds))
        
        # Forzar visibilidad de los contenedores
        print("[DEBUG] Forzando visibilidad de los contenedores de enlaces en show_artist_details")
        
        if hasattr(self, 'artist_links_group') and self.artist_links_group:
            # Asegurar que tanto el contenedor como su padre estén visibles
            self.artist_links_group.setVisible(True)
            self.artist_links_group.show()
            
            parent = self.artist_links_group.parent()
            if parent:
                parent.setVisible(True)
                parent.show()
        
        # Llamar a un método que nos ayude a verificar el estado
        self.debug_link_groups_status()
            
    def show_track_details(self, track_item):
        """
        Show track details.
        
        Args:
            track_item: Tree item for a track
        """
        # Hide all views first
        self.artist_view.hide()
        self.album_view.hide()
        self.track_view.show()
        
        # Get track data
        track_data = track_item.data(0, Qt.ItemDataRole.UserRole)
        if not track_data:
            return
            
        # Show track details
        self.track_view.show_entity(track_data)
        
        # Update cover image
        if len(track_data) > 1 and self.media_finder:
            file_path = track_data[1]
            cover_path = self.media_finder.find_cover_image(file_path)
            self.media_finder.load_image_to_label(
                cover_path, 
                self.cover_label, 
                "No imagen"
            )
            
        # Update artist image
        if len(track_data) > 3 and self.media_finder:
            artist_name = track_data[3]
            artist_image_path = self.media_finder.find_artist_image(artist_name)
            self.media_finder.load_image_to_label(
                artist_image_path, 
                self.artist_image_label, 
                "No imagen de artista"
            )
            
        # Set feeds button visibility
        if self.feeds_button and len(track_data) > 0:
            track_id = track_data[0]
            feeds = self.db.get_feeds_data('song', track_id) if track_id else []
            self.feeds_button.setVisible(bool(feeds))
            
    def clear_details(self):
        """Clear all details panels."""
        # Hide all entity views
        self.artist_view.hide()
        self.album_view.hide()
        self.track_view.hide()
        
        # Clear view content
        self.artist_view.clear()
        self.album_view.clear()
        self.track_view.clear()
        
        # Clear images
        if self.cover_label:
            self.cover_label.setText("No imagen")
        if self.artist_image_label:
            self.artist_image_label.setText("No imagen de artista")
            
        # Hide feeds button
        if self.feeds_button:
            self.feeds_button.setVisible(False)
            
    def toggle_advanced_settings(self, state):
        """
        Show or hide advanced settings.
        
        Args:
            state: Checkbox state
        """
        is_checked = (state == Qt.CheckState.Checked.value)
        
        # Show/hide advanced settings container
        if self.advanced_settings_container:
            self.advanced_settings_container.setVisible(is_checked)
            
        # Show/hide advanced buttons
        for button in self.advanced_buttons:
            if button:
                button.setVisible(is_checked)
                
    def play_selected_item(self):
        """Play the currently selected item."""
        selected_items = self.results_tree.selectedItems()
        if not selected_items:
            return
            
        # Get selected item data
        item = selected_items[0]
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Determine what to play
        if isinstance(item_data, dict):
            # It's an artist or album - play all child items
            self._play_tree_item_with_children(item)
        else:
            # It's a track - play directly
            self._play_track(item_data)
            
    def _play_tree_item_with_children(self, item):
        """
        Play an item with its children.
        
        Args:
            item: Tree item to play
        """
        # Collect file paths from all children
        file_paths = []
        
        # If no children, do nothing
        if item.childCount() == 0:
            return
            
        # Add all child file paths
        for i in range(item.childCount()):
            child = item.child(i)
            child_data = child.data(0, Qt.ItemDataRole.UserRole)
            
            # If it's a track and has a file path
            if not isinstance(child_data, dict) and len(child_data) > 1:
                file_path = child_data[1]
                if file_path and os.path.exists(file_path):
                    file_paths.append(file_path)
            
            # If it's an album, add all its track file paths
            if isinstance(child_data, dict) and child_data.get('type') == 'album':
                for j in range(child.childCount()):
                    track_child = child.child(j)
                    track_data = track_child.data(0, Qt.ItemDataRole.UserRole)
                    if not isinstance(track_data, dict) and len(track_data) > 1:
                        file_path = track_data[1]
                        if file_path and os.path.exists(file_path):
                            file_paths.append(file_path)
        
        # Play all collected file paths
        if file_paths:
            self._play_files(file_paths)
            
    def _play_track(self, track_data):
        """
        Play a track.
        
        Args:
            track_data: Track data from tree item
        """
        if not track_data or len(track_data) < 2:
            return
            
        file_path = track_data[1]
        if not file_path or not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
            
        self._play_files([file_path])
        
    def _play_files(self, file_paths):
        """
        Play a list of files.
        
        Args:
            file_paths: List of file paths to play
        """
        if not file_paths:
            return
            
        # Implement your playback logic here
        # For example, you could emit a signal with the list of files
        # to be handled by a player module
        print(f"Playing {len(file_paths)} files")
        
        # Use EntityView signal if tracks should be played through an external module
        if hasattr(self, 'track_view') and isinstance(self.track_view, EntityView):
            self.track_view.requestPlayback.emit(file_paths)
            
    def open_selected_folder(self):
        """Open folder of the currently selected item."""
        selected_items = self.results_tree.selectedItems()
        if not selected_items:
            return
            
        # Get selected item data
        item = selected_items[0]
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Get file path
        file_path = None
        
        if isinstance(item_data, dict):
            # Find the first child track and use its path
            if item.childCount() > 0:
                for i in range(item.childCount()):
                    child = item.child(i)
                    child_data = child.data(0, Qt.ItemDataRole.UserRole)
                    if isinstance(child_data, dict) and child_data.get('type') == 'album':
                        # It's an album, check its tracks
                        if child.childCount() > 0:
                            track_data = child.child(0).data(0, Qt.ItemDataRole.UserRole)
                            if not isinstance(track_data, dict) and len(track_data) > 1:
                                file_path = track_data[1]
                                break
                    elif not isinstance(child_data, dict) and len(child_data) > 1:
                        # It's a track
                        file_path = child_data[1]
                        break
        else:
            # It's a track
            if len(item_data) > 1:
                file_path = item_data[1]
        
        # Open folder if we have a file path
        if file_path and os.path.exists(file_path):
            folder_path = os.path.dirname(file_path)
            self._open_folder(folder_path)
            
    def _open_folder(self, folder_path):
        """
        Open a folder in the system file explorer.
        
        Args:
            folder_path: Path to the folder
        """
        if not folder_path or not os.path.exists(folder_path):
            print(f"Folder not found: {folder_path}")
            return
            
        try:
            if sys.platform == 'win32':
                # Windows
                os.startfile(folder_path)
            elif sys.platform == 'darwin':
                # macOS
                subprocess.run(['open', folder_path])
            else:
                # Linux
                subprocess.run(['xdg-open', folder_path])
                
            print(f"Opened folder: {folder_path}")
        except Exception as e:
            print(f"Error opening folder: {e}")
            
    def handle_spotify_button(self):
        """Handle Spotify button click - search for current track in Spotify."""
        selected_items = self.results_tree.selectedItems()
        if not selected_items:
            return
            
        # Get selected item data
        item = selected_items[0]
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # If it's a track
        if not isinstance(item_data, dict) and len(item_data) > 0:
            track_id = item_data[0]
            spotify_url = self.db.get_spotify_url(track_id)
            
            if spotify_url:
                # Open existing URL
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl(spotify_url))
            else:
                # No URL, search by metadata
                self._search_spotify_for_track(item_data)
        else:
            # Try to get first child track
            if item.childCount() > 0:
                child = item.child(0)
                child_data = child.data(0, Qt.ItemDataRole.UserRole)
                if not isinstance(child_data, dict):
                    self._search_spotify_for_track(child_data)
                    
    def _search_spotify_for_track(self, track_data):
        """
        Search for a track in Spotify.
        
        Args:
            track_data: Track data from tree item
        """
        if not track_data or len(track_data) < 3:
            return
            
        # Get track metadata
        title = track_data[2] if len(track_data) > 2 else ""
        artist = track_data[3] if len(track_data) > 3 else ""
        
        if not title or not artist:
            return
            
        # Create search query
        search_query = f"{title} {artist}"
        search_query = search_query.replace(" ", "%20")
        
        # Create Spotify search URL
        spotify_url = f"https://open.spotify.com/search/{search_query}"
        
        # Open URL
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(spotify_url))
        
    def show_feeds(self):
        """Show feeds for the currently selected item."""
        # Get current item
        current_item = self.results_tree.currentItem()
        if not current_item:
            return
            
        # Get entity type and ID
        entity_type = None
        entity_id = None
        
        item_data = current_item.data(0, Qt.ItemDataRole.UserRole)
        
        if isinstance(item_data, dict):
            # It's an artist or album
            if item_data.get('type') == 'artist':
                entity_type = 'artist'
                entity_id = self.db.get_entity_id('artist', item_data.get('name'))
            elif item_data.get('type') == 'album':
                entity_type = 'album'
                entity_id = self.db.get_entity_id('album', item_data.get('name'), item_data.get('artist'))
        else:
            # It's a track
            if len(item_data) > 0:
                entity_type = 'song'
                entity_id = item_data[0]
                
        if not entity_type or not entity_id:
            return
            
        # Show feeds in feeds view
        self.feeds_view.show_feeds(entity_type, entity_id)
        
        # Switch to feeds panel
        self.details_stacked_widget.setCurrentIndex(1)
        
    def search(self, query=None):
        """
        Perform a search based on the query.
        
        Args:
            query (str, optional): Search query. If None, use the search box text.
        """
        if query is None:
            query = self.search_box.text()
            
        if not query:
            self.results_tree.clear()
            return
            
        # Parse query
        parsed_query = self.search_parser.parse_query(query)
        
        # Build SQL conditions
        conditions, params = self.search_parser.build_sql_conditions(parsed_query)
        
        # Perform search
        results = self.db.search_music(conditions, params)
        
        # Display results
        self._display_search_results(results)
        
    def _display_search_results(self, results):
        """
        Display search results in the tree widget.
        
        Args:
            results: List of result rows from database
        """
        # Clear previous results
        self.results_tree.clear()
        
        if not results:
            return
            
        # Dictionary to keep track of artists and albums
        artists = {}
        
        # Organize results by artist and album
        for result in results:
            # Extract data
            track_id = result[0]
            file_path = result[1]
            title = result[2]
            artist = result[3]
            album_artist = result[4]
            album = result[5]
            date = result[6]
            genre = result[7]
            
            # Skip invalid entries
            if not title or not artist or not album:
                continue
                
            # Create artist item if not exists
            if artist not in artists:
                artists[artist] = {
                    'item': self._create_artist_item(artist),
                    'albums': {}
                }
                
            artist_data = artists[artist]
            
            # Create album item if not exists
            if album not in artist_data['albums']:
                artist_data['albums'][album] = {
                    'item': self._create_album_item(album, artist, date, genre),
                    'tracks': []
                }
                artist_data['item'].addChild(artist_data['albums'][album]['item'])
                
            # Create track item
            track_item = self._create_track_item(result)
            
            # Add track to album
            artist_data['albums'][album]['item'].addChild(track_item)
            
            # Store track in albums data
            artist_data['albums'][album]['tracks'].append(track_item)
            
        # Add artist items to tree
        for artist_data in artists.values():
            self.results_tree.addTopLevelItem(artist_data['item'])
            
        # Expand all artists
        for i in range(self.results_tree.topLevelItemCount()):
            self.results_tree.topLevelItem(i).setExpanded(True)
            
    def _create_artist_item(self, artist_name):
        """
        Create an artist tree item.
        
        Args:
            artist_name: Name of the artist
            
        Returns:
            QTreeWidgetItem: The created item
        """
        item = QTreeWidgetItem([artist_name, "", ""])
        item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'artist',
            'name': artist_name
        })
        
        return item
        
    def _create_album_item(self, album_name, artist_name, date=None, genre=None):
        """
        Create an album tree item.
        
        Args:
            album_name: Name of the album
            artist_name: Name of the artist
            date: Release date
            genre: Genre
            
        Returns:
            QTreeWidgetItem: The created item
        """
        item = QTreeWidgetItem([album_name, date or "", genre or ""])
        item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'album',
            'name': album_name,
            'artist': artist_name,
            'date': date,
            'genre': genre
        })
        
        return item
        
    def _create_track_item(self, track_data):
        """
        Create a track tree item.
        
        Args:
            track_data: Track data from database
            
        Returns:
            QTreeWidgetItem: The created item
        """
        track_id = track_data[0]
        title = track_data[2]
        date = track_data[6]
        genre = track_data[7]
        
        # Get track number if available
        track_number = ""
        if len(track_data) > 14:
            try:
                track_number = str(int(track_data[14]))
                title = f"{track_number}. {title}"
            except (ValueError, TypeError):
                pass
                
        item = QTreeWidgetItem([title, date or "", genre or ""])
        item.setData(0, Qt.ItemDataRole.UserRole, track_data)
        
        return item
        
    def setup_hotkeys(self, hotkeys_config=None):
        """
        Set up keyboard shortcuts.
        
        Args:
            hotkeys_config: Dictionary with hotkey configurations
        """
        if not hotkeys_config:
            # Default hotkeys
            hotkeys_config = {
                'play': 'Space',
                'folder': 'Ctrl+O',
                'spotify': 'Ctrl+S'
            }
            
        # Play hotkey
        if 'play' in hotkeys_config:
            play_shortcut = QShortcut(QKeySequence(hotkeys_config['play']), self)
            play_shortcut.activated.connect(self.play_selected_item)
            
        # Folder hotkey
        if 'folder' in hotkeys_config:
            folder_shortcut = QShortcut(QKeySequence(hotkeys_config['folder']), self)
            folder_shortcut.activated.connect(self.open_selected_folder)
            
        # Spotify hotkey
        if 'spotify' in hotkeys_config:
            spotify_shortcut = QShortcut(QKeySequence(hotkeys_config['spotify']), self)
            spotify_shortcut.activated.connect(self.handle_spotify_button)
            
    def buscar_musica_en_reproduccion(self):
        """Search for currently playing music in external players."""
        # This implementation depends on your system and what players you want to support
        # For now, we'll just show a simple message
        print("Buscando música en reproducción...")
        
        # Example: For Linux with MPRIS (DBus)
        try:
            if sys.platform == 'linux':
                # Try to get currently playing track from MPRIS
                import dbus
                bus = dbus.SessionBus()
                
                # List of common MPRIS player service names
                players = [
                    'org.mpris.MediaPlayer2.spotify',
                    'org.mpris.MediaPlayer2.rhythmbox',
                    'org.mpris.MediaPlayer2.vlc',
                    'org.mpris.MediaPlayer2.clementine'
                ]
                
                # Try each player
                for player_service in players:
                    try:
                        player_obj = bus.get_object(player_service, '/org/mpris/MediaPlayer2')
                        player_props = dbus.Interface(player_obj, 'org.freedesktop.DBus.Properties')
                        metadata = player_props.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
                        
                        # Extract track info
                        artist = str(metadata.get('xesam:artist', [''])[0])
                        title = str(metadata.get('xesam:title', ''))
                        album = str(metadata.get('xesam:album', ''))
                        
                        if artist and title:
                            # Set search query
                            search_query = f"a:{artist} t:{title}"
                            self.search_box.setText(search_query)
                            self.search(search_query)
                            return
                    except Exception as e:
                        # This player failed, try next one
                        continue
                        
                print("No se encontró música en reproducción.")
        except ImportError:
            print("Módulo dbus no encontrado. No se puede buscar música en reproducción.")
        except Exception as e:
            print(f"Error al buscar música en reproducción: {e}")
        
    def apply_theme(self, theme=None):
        """
        Apply a theme to the module.
        
        Args:
            theme (str, optional): Name of the theme
        """
        # This would be implemented based on your theming system
        self.selected_theme = theme
        
        # Apply theme to tree widget
        if hasattr(self, 'results_tree'):
            # Add theme-specific styling
            pass


    def debug_current_item(self):
        """
        Muestra información detallada del elemento seleccionado para diagnóstico.
        Esta función puede agregarse a MusicBrowser para facilitar la depuración.
        """
        import traceback
        
        print("\n===== DIAGNÓSTICO DEL ELEMENTO ACTUAL =====")
        
        try:
            # 1. Obtener el elemento seleccionado
            selected_items = self.results_tree.selectedItems()
            if not selected_items:
                print("[DIAGNÓSTICO] No hay elementos seleccionados")
                return
            
            item = selected_items[0]
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            
            # 2. Verificar tipo de elemento
            if isinstance(item_data, dict):
                print(f"[DIAGNÓSTICO] Tipo de elemento: {'artista' if item_data.get('type') == 'artist' else 'álbum'}")
                for key, value in item_data.items():
                    print(f"[DIAGNÓSTICO] {key}: {value}")
                    
                # Si es artista, buscar en la base de datos
                if item_data.get('type') == 'artist':
                    artist_name = item_data.get('name')
                    print(f"\n[DIAGNÓSTICO] Obteniendo información completa para artista: {artist_name}")
                    artist_db_info = self.db.get_artist_info(artist_name)
                    
                    if artist_db_info:
                        print("[DIAGNÓSTICO] Información de base de datos disponible")
                        # Mostrar campos importantes
                        important_fields = ['id', 'name', 'bio', 'spotify_url', 'youtube_url', 'lastfm_url', 'wikipedia_url']
                        for field in important_fields:
                            has_value = field in artist_db_info and bool(artist_db_info[field])
                            print(f"[DIAGNÓSTICO] {field}: {'PRESENTE' if has_value else 'AUSENTE'}")
                        
                        # Verificar enlaces
                        print("\n[DIAGNÓSTICO] Extrayendo enlaces...")
                        links = self.artist_view.extract_links(artist_db_info, 'artist')
                        print(f"[DIAGNÓSTICO] Enlaces encontrados: {links}")
                        
                        # Verificar redes sociales
                        if artist_db_info.get('id'):
                            print(f"\n[DIAGNÓSTICO] Obteniendo redes sociales para ID: {artist_db_info['id']}")
                            networks = self.db.get_artist_networks(artist_db_info['id'])
                            print(f"[DIAGNÓSTICO] Redes sociales: {networks}")
                    else:
                        print("[DIAGNÓSTICO] No se encontró información en la base de datos")
                        
                    # Verificar estado de contenedores y grupos
                    print("\n[DIAGNÓSTICO] Estado de componentes UI:")
                    print(f"[DIAGNÓSTICO] artist_view visible: {self.artist_view.isVisible()}")
                    print(f"[DIAGNÓSTICO] wiki_container existe: {hasattr(self.artist_view, 'wiki_container')}")
                    if hasattr(self.artist_view, 'wiki_container'):
                        print(f"[DIAGNÓSTICO] wiki_container visible: {self.artist_view.wiki_container.isVisible()}")
                    print(f"[DIAGNÓSTICO] bio_container existe: {hasattr(self.artist_view, 'bio_container')}")
                    if hasattr(self.artist_view, 'bio_container'):
                        print(f"[DIAGNÓSTICO] bio_container visible: {self.artist_view.bio_container.isVisible()}")
                    print(f"[DIAGNÓSTICO] artist_links_group existe: {self.artist_links_group is not None}")
                    if self.artist_links_group:
                        print(f"[DIAGNÓSTICO] artist_links_group visible: {self.artist_links_group.isVisible()}")
                    print(f"[DIAGNÓSTICO] link_buttons existe: {hasattr(self, 'link_buttons') and self.link_buttons is not None}")
            else:
                # Es una canción
                print("[DIAGNÓSTICO] Tipo de elemento: canción")
                if len(item_data) > 5:
                    print(f"[DIAGNÓSTICO] ID: {item_data[0]}")
                    print(f"[DIAGNÓSTICO] Ruta: {item_data[1]}")
                    print(f"[DIAGNÓSTICO] Título: {item_data[2]}")
                    print(f"[DIAGNÓSTICO] Artista: {item_data[3]}")
                    print(f"[DIAGNÓSTICO] Álbum: {item_data[5]}")
                    
                    # Verificar si existe URL de Spotify
                    track_id = item_data[0]
                    spotify_url = self.db.get_spotify_url(track_id)
                    print(f"[DIAGNÓSTICO] URL de Spotify: {spotify_url}")
                    
            print("\n[DIAGNÓSTICO] Verificando estructura de la base de datos...")
            db_status = self.check_database_connection() if hasattr(self, 'check_database_connection') else None
            if db_status:
                print(f"[DIAGNÓSTICO] Estado de la base de datos: {db_status}")
                
        except Exception as e:
            print(f"[DIAGNÓSTICO] Error durante el diagnóstico: {e}")
            traceback.print_exc()
        
        print("===== FIN DEL DIAGNÓSTICO =====\n")
        
    def check_database_connection(self):
        """
        Verifica la conexión a la base de datos y su estructura.
        
        Returns:
            dict: Resultados de la verificación
        """
        try:
            import sqlite3
            import os
            
            if not self.db_path or not os.path.exists(self.db_path):
                return {"success": False, "error": f"Archivo de base de datos no encontrado: {self.db_path}"}
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar tablas principales
            tables_check = {}
            for table in ["artists", "albums", "songs", "lyrics", "artists_networks"]:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                tables_check[table] = bool(cursor.fetchone())
                
            # Verificar si hay datos
            data_check = {}
            if tables_check["artists"]:
                cursor.execute("SELECT COUNT(*) FROM artists")
                data_check["artists_count"] = cursor.fetchone()[0]
                
            if tables_check["albums"]:
                cursor.execute("SELECT COUNT(*) FROM albums")
                data_check["albums_count"] = cursor.fetchone()[0]
                
            if tables_check["songs"]:
                cursor.execute("SELECT COUNT(*) FROM songs")
                data_check["songs_count"] = cursor.fetchone()[0]
                
            # Verificar si hay contenido de Wikipedia
            wiki_check = {}
            if tables_check["artists"]:
                cursor.execute("SELECT COUNT(*) FROM artists WHERE wikipedia_content IS NOT NULL AND wikipedia_content != ''")
                wiki_check["artists_with_wiki"] = cursor.fetchone()[0]
                
            # Verificar si hay enlaces
            links_check = {}
            if tables_check["artists"]:
                cursor.execute("SELECT COUNT(*) FROM artists WHERE spotify_url IS NOT NULL AND spotify_url != ''")
                links_check["artists_with_spotify"] = cursor.fetchone()[0]
                
            # Verificar tabla de redes sociales
            network_check = {}
            if tables_check["artists_networks"]:
                cursor.execute("SELECT COUNT(*) FROM artists_networks")
                network_check["artists_networks_count"] = cursor.fetchone()[0]
                
                # Obtener las columnas de la tabla
                cursor.execute("PRAGMA table_info(artists_networks)")
                network_check["columns"] = [row[1] for row in cursor.fetchall()]
                
            conn.close()
            
            return {
                "success": True,
                "tables": tables_check,
                "data": data_check,
                "wiki": wiki_check,
                "links": links_check,
                "networks": network_check
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}



    def debug_link_containers(self):
        """
        Función para diagnosticar problemas con los contenedores de enlaces.
        """
        from PyQt6.QtWidgets import QGroupBox, QLayout
        
        print("\n===== DIAGNÓSTICO DE CONTENEDORES DE ENLACES =====")
        
        # 1. Verificar instancia de link_buttons
        print(f"[DIAGNÓSTICO] link_buttons existe: {hasattr(self, 'link_buttons')}")
        if hasattr(self, 'link_buttons'):
            print(f"[DIAGNÓSTICO] link_buttons es None: {self.link_buttons is None}")
        
        # 2. Examinar artist_links_group
        print(f"\n[DIAGNÓSTICO] artist_links_group existe: {hasattr(self, 'artist_links_group')}")
        if hasattr(self, 'artist_links_group') and self.artist_links_group:
            print(f"[DIAGNÓSTICO] artist_links_group clase: {self.artist_links_group.__class__.__name__}")
            print(f"[DIAGNÓSTICO] artist_links_group es QGroupBox: {isinstance(self.artist_links_group, QGroupBox)}")
            print(f"[DIAGNÓSTICO] artist_links_group objectName: {self.artist_links_group.objectName()}")
            print(f"[DIAGNÓSTICO] artist_links_group visible: {self.artist_links_group.isVisible()}")
            print(f"[DIAGNÓSTICO] artist_links_group tiene layout: {self.artist_links_group.layout() is not None}")
            
            if self.artist_links_group.layout():
                print(f"[DIAGNÓSTICO] artist_links_group layout clase: {self.artist_links_group.layout().__class__.__name__}")
                print(f"[DIAGNÓSTICO] artist_links_group layout contiene: {self.artist_links_group.layout().count()} elementos")
        
        # 3. Examinar album_links_group
        print(f"\n[DIAGNÓSTICO] album_links_group existe: {hasattr(self, 'album_links_group')}")
        if hasattr(self, 'album_links_group') and self.album_links_group:
            print(f"[DIAGNÓSTICO] album_links_group clase: {self.album_links_group.__class__.__name__}")
            print(f"[DIAGNÓSTICO] album_links_group es QGroupBox: {isinstance(self.album_links_group, QGroupBox)}")
            print(f"[DIAGNÓSTICO] album_links_group objectName: {self.album_links_group.objectName()}")
            print(f"[DIAGNÓSTICO] album_links_group visible: {self.album_links_group.isVisible()}")
            print(f"[DIAGNÓSTICO] album_links_group tiene layout: {self.album_links_group.layout() is not None}")
            
            if self.album_links_group.layout():
                print(f"[DIAGNÓSTICO] album_links_group layout clase: {self.album_links_group.layout().__class__.__name__}")
                print(f"[DIAGNÓSTICO] album_links_group layout contiene: {self.album_links_group.layout().count()} elementos")
        
        # 4. Reparar layouts si es necesario
        print("\n[DIAGNÓSTICO] Reparando layouts...")
        self.fix_link_group_layouts()
        
        print("===== FIN DEL DIAGNÓSTICO DE CONTENEDORES =====\n")
        

    def fix_link_buttons(self):
        """
        Asegura que las referencias a los botones de enlaces estén correctamente establecidas.
        No crea nuevos elementos, solo actualiza referencias si es necesario.
        """
        print("[DEBUG] Actualizando referencias a LinkButtonsManager...")
        
        # Verificar que los contenedores existen en el UI
        if not hasattr(self, 'artist_links_group') or not self.artist_links_group:
            self.artist_links_group = self.main_ui.findChild(QWidget, "artist_links_group")
            
        if not hasattr(self, 'album_links_group') or not self.album_links_group:
            self.album_links_group = self.main_ui.findChild(QWidget, "album_links_group")
        
        # Si no se encontraron los contenedores, no podemos continuar
        if not self.artist_links_group or not self.album_links_group:
            print("[DEBUG] Error: No se encontraron los contenedores de enlaces en el UI")
            return False
        
        # Si el gestor de enlaces no existe, crearlo con las referencias existentes
        if not hasattr(self, 'link_buttons') or not self.link_buttons:
            from modules.submodules.fuzzy.links_buttons_submodule import LinkButtonsManager
            self.link_buttons = LinkButtonsManager(self.artist_links_group, self.album_links_group)
            print("[DEBUG] LinkButtonsManager recreado con las referencias existentes")
            
        return True



    def _ensure_link_containers(self):
        """
        Obtiene referencias a los contenedores de enlaces existentes en el UI.
        No crea nuevos elementos, solo asegura que las referencias estén establecidas.
        """
        # Obtener referencias a los grupos de enlaces ya definidos en el archivo UI
        self.artist_links_group = self.main_ui.findChild(QWidget, "artist_links_group")
        self.album_links_group = self.main_ui.findChild(QWidget, "album_links_group")
        
        print(f"[DEBUG] Referencia a artist_links_group: {self.artist_links_group}")
        print(f"[DEBUG] Referencia a album_links_group: {self.album_links_group}")
        
        # Verificar que se encontraron los grupos
        if not self.artist_links_group or not self.album_links_group:
            print("[DEBUG] ADVERTENCIA: No se encontraron los grupos de enlaces en el UI")



    def debug_link_groups_status(self):
        """Muestra el estado actual de los grupos de enlaces y sus layouts."""
        print("\n===== ESTADO DE LOS GRUPOS DE ENLACES =====")
        
        if hasattr(self, 'artist_links_group'):
            print(f"artist_links_group existe: {self.artist_links_group is not None}")
            if self.artist_links_group:
                print(f"artist_links_group clase: {self.artist_links_group.__class__.__name__}")
                print(f"artist_links_group tiene layout: {self.artist_links_group.layout() is not None}")
                print(f"artist_links_group es visible: {self.artist_links_group.isVisible()}")
                if self.artist_links_group.layout():
                    print(f"artist_links_group layout tipo: {self.artist_links_group.layout().__class__.__name__}")
                    print(f"artist_links_group layout elementos: {self.artist_links_group.layout().count()}")
        else:
            print("artist_links_group no está definido en la clase")
        
        if hasattr(self, 'album_links_group'):
            print(f"album_links_group existe: {self.album_links_group is not None}")
            if self.album_links_group:
                print(f"album_links_group clase: {self.album_links_group.__class__.__name__}")
                print(f"album_links_group tiene layout: {self.album_links_group.layout() is not None}")
                print(f"album_links_group es visible: {self.album_links_group.isVisible()}")
                if self.album_links_group.layout():
                    print(f"album_links_group layout tipo: {self.album_links_group.layout().__class__.__name__}")
                    print(f"album_links_group layout elementos: {self.album_links_group.layout().count()}")
        else:
            print("album_links_group no está definido en la clase")
        
        if hasattr(self, 'link_buttons'):
            print(f"link_buttons existe: {self.link_buttons is not None}")
            if self.link_buttons:
                print(f"link_buttons.artist_group existe: {hasattr(self.link_buttons, 'artist_group') and self.link_buttons.artist_group is not None}")
                print(f"link_buttons.album_group existe: {hasattr(self.link_buttons, 'album_group') and self.link_buttons.album_group is not None}")
                
                if hasattr(self.link_buttons, 'artist_group') and self.link_buttons.artist_group:
                    print(f"link_buttons.artist_group es el mismo que artist_links_group: {self.link_buttons.artist_group is self.artist_links_group}")
                
                if hasattr(self.link_buttons, 'album_group') and self.link_buttons.album_group:
                    print(f"link_buttons.album_group es el mismo que album_links_group: {self.link_buttons.album_group is self.album_links_group}")
        else:
            print("link_buttons no está definido en la clase")
            
        print("===== FIN DEL ESTADO =====\n")