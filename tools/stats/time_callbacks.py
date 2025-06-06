"""
Time Callbacks Module - Handles callbacks for the TimeSubmodule
"""
import logging

class TimeCallbackHandler:
    """
    A class to manage callbacks for the TimeSubmodule.
    """
    
    def __init__(self, time_submodule, main_callback_handler):
        """
        Initialize the time callback handler.
        
        Args:
            time_submodule: Reference to the TimeSubmodule instance
            main_callback_handler: Reference to the main StatsCallbackHandler
        """
        self.time_submodule = time_submodule
        self.main_callback_handler = main_callback_handler
    
    def register_callbacks(self):
        """Register all callbacks needed for the time submodule."""
        # Register the time_page_activated callback with the main handler
        self.main_callback_handler.register_callback(
            'after_category_changed',
            self.on_category_changed,
            'time_submodule'
        )
        
        # Connect the time buttons
        self.connect_time_buttons()
        
        # Register table click handlers
        self.connect_table_handlers()

    def connect_time_buttons(self):
        """Connect time navigation buttons directly from stats_module."""
        buttons = [
            ('time_button_artist', self.time_submodule.show_artists_page),
            ('time_button_album', self.time_submodule.show_albums_page),
            ('time_button_labels', self.time_submodule.show_labels_page),
            ('time_button_genres', self.on_genres_button_clicked),
            ('time_button_feeds', self.on_feeds_button_clicked),
            ('time_button_listens', self.on_listens_button_clicked),
            ('time_button_info', self.on_info_button_clicked)
        ]
        
        for button_name, handler in buttons:
            if hasattr(self.time_submodule.stats_module, button_name):
                button = getattr(self.time_submodule.stats_module, button_name)
                try:
                    button.clicked.disconnect()
                except:
                    pass
                button.clicked.connect(handler)
                logging.info(f"Connected time button: {button_name}")
            else:
                logging.warning(f"Button {button_name} not found in stats_module")

    def connect_table_handlers(self):
        """Connect all table click handlers."""
        # Artists tables
        tables_artists = [
            ('table_time_artists_top', self.time_submodule.on_artist_year_selected),
            ('table_time_artists_bott', self.time_submodule.on_artist_decade_selected)
        ]
        
        for table_name, handler in tables_artists:
            if hasattr(self.time_submodule.stats_module, table_name):
                table = getattr(self.time_submodule.stats_module, table_name)
                try:
                    table.itemClicked.disconnect()
                except:
                    pass
                table.itemClicked.connect(handler)
                logging.info(f"Connected table: {table_name}")
            else:
                logging.warning(f"Table {table_name} not found in stats_module")
        
        # Albums tables
        tables_albums = [
            ('table_time_albums_top', self.time_submodule.on_album_year_selected),
            ('table_time_albums_bott', self.time_submodule.on_album_decade_selected)
        ]
        
        for table_name, handler in tables_albums:
            if hasattr(self.time_submodule.stats_module, table_name):
                table = getattr(self.time_submodule.stats_module, table_name)
                try:
                    table.itemClicked.disconnect()
                except:
                    pass
                table.itemClicked.connect(handler)
                logging.info(f"Connected table: {table_name}")
            else:
                logging.warning(f"Table {table_name} not found in stats_module")
        
        # Labels tables
        tables_labels = [
            ('table_time_labels_top', self.time_submodule.on_label_year_selected),
            ('table_time_labels_bott', self.time_submodule.on_label_decade_selected)
        ]
        
        for table_name, handler in tables_labels:
            if hasattr(self.time_submodule.stats_module, table_name):
                table = getattr(self.time_submodule.stats_module, table_name)
                try:
                    table.itemClicked.disconnect()
                except:
                    pass
                table.itemClicked.connect(handler)
                logging.info(f"Connected table: {table_name}")
            else:
                logging.warning(f"Table {table_name} not found in stats_module")
    
    def on_category_changed(self, index, category_name):
        """
        Handle category change events.
        
        Args:
            index: The index of the selected category
            category_name: The name of the selected category
        """
        # Check if the "Tiempo" category is selected
        if category_name == "Tiempo":
            logging.info("Time category selected, initializing time view")
            self.time_submodule.load_time_stats()
    
    # Placeholder methods for other buttons that could be implemented later

    def on_listens_button_clicked(self):
        """Handle listens button click."""
        if (self.time_submodule.stackedWidget_time and 
            hasattr(self.time_submodule.stats_module, 'time_page_listens') and 
            self.time_submodule.time_page_listens):
            self.time_submodule.stackedWidget_time.setCurrentWidget(
                self.time_submodule.time_page_listens
            )
            # Optionally load listens data here
            if hasattr(self.time_submodule, 'load_listens_time_data'):
                self.time_submodule.load_listens_time_data()

    def on_info_button_clicked(self):
        """Handle info button click."""
        if (self.time_submodule.stackedWidget_time and 
            hasattr(self.time_submodule.stats_module, 'time_page_info') and 
            self.time_submodule.time_page_info):
            self.time_submodule.stackedWidget_time.setCurrentWidget(
                self.time_submodule.time_page_info
            )
            # Optionally load info data here
            if hasattr(self.time_submodule, 'load_info_time_data'):
                self.time_submodule.load_info_time_data()


    def on_genres_button_clicked(self):
        """Handle genres button click."""
        if (self.time_submodule.stackedWidget_time and 
            hasattr(self.time_submodule.stats_module, 'time_page_genres') and 
            self.time_submodule.time_page_genres):
            self.time_submodule.stackedWidget_time.setCurrentWidget(
                self.time_submodule.time_page_genres
            )
            # Load genre data
            if hasattr(self.time_submodule, 'load_genre_time_data'):
                self.time_submodule.load_genre_time_data()

    def on_feeds_button_clicked(self):
        """Handle feeds button click."""
        if (self.time_submodule.stackedWidget_time and 
            hasattr(self.time_submodule.stats_module, 'time_page_feeds') and 
            self.time_submodule.time_page_feeds):
            self.time_submodule.stackedWidget_time.setCurrentWidget(
                self.time_submodule.time_page_feeds
            )
            # Load feeds data
            if hasattr(self.time_submodule, 'load_feeds_time_data'):
                self.time_submodule.load_feeds_time_data()