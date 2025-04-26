from PyQt6.QtWidgets import QWidget, QTreeWidgetItem, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
import os
import sqlite3
from base_module import BaseModule
from pathlib import Path
import resources_rc
# Import submodules (adjust paths as needed based on your project structure)

from modules.submodules.fuzzy.search_handler import SearchHandler
from modules.submodules.fuzzy.database_manager import DatabaseManager
from modules.submodules.fuzzy.ui_updater import UIUpdater
from modules.submodules.fuzzy.link_manager import LinkManager

class MusicFuzzyModule(BaseModule):
    """Music browser module with fuzzy search capabilities."""
    
    def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
        super().__init__(parent, theme, **kwargs)
        
        # Initialize database path
        self.db_path = kwargs.get('db_path', os.path.join(Path.home(), '.local', 'share', 'music_app', 'music.db'))
        
        # Initialize subcomponents
        self.db_manager = DatabaseManager(self.db_path)
        self.search_handler = SearchHandler(self)
        self.ui_updater = UIUpdater(self)
        self.link_manager = LinkManager(self)
        
        # Connect signals
        self._connect_signals()
        
    def init_ui(self):
        """Initialize UI from the .ui file"""
        ui_file_name = "music_fuzzy_module.ui"
        if self.load_ui_file(ui_file_name):
            # Set up tree widget
            self.results_tree_widget.setHeaderLabels(["Artista / Álbum / Canción", "Año", "Género"])
            self.results_tree_widget.setColumnWidth(0, 300)
            self.results_tree_widget.setColumnWidth(1, 60)
            self.results_tree_widget.setColumnWidth(2, 100)
            
            # Hide all link buttons initially
            self._setup_link_buttons()
        else:
            print(f"Error loading UI file: {ui_file_name}")
    
    def _connect_signals(self):
        """Connect UI signals to slots"""
        # Search box signal
        self.search_box.returnPressed.connect(self.search_handler.perform_search)
        
        # Tree widget signals
        self.results_tree_widget.itemClicked.connect(self._handle_item_clicked)
        
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