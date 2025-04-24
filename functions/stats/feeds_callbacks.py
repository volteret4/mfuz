"""
Feeds Callbacks - Handles specific callbacks for the Feeds submodule
"""
import logging

class FeedsCallbackHandler:
    """Handler for Feeds-specific callbacks and events."""
    
    def __init__(self, feeds_submodule=None, main_callback_handler=None):
        """
        Initialize with references to the feeds submodule and main callback handler.
        
        Args:
            feeds_submodule: Reference to the FeedsSubmodule instance
            main_callback_handler: Reference to the main StatsCallbackHandler
        """
        self.feeds_submodule = feeds_submodule
        self.main_handler = main_callback_handler
        
    def register_callbacks(self):
        """Register all feeds-related callbacks with the main handler."""
        if not self.main_handler:
            logging.error("Cannot register callbacks: No main callback handler provided")
            return
            
        # Register for category changes
        self.main_handler.register_callback(
            'after_category_changed',
            self.on_category_changed,
            'feeds_callbacks'
        )
        
        # Register feeds button events
        self._register_button_callbacks()
        
        logging.info("Feeds callbacks registered")
        
    def _register_button_callbacks(self):
        """Register callbacks for the feeds buttons."""
        if not self.feeds_submodule:
            return
            
        # Get button references from the submodule
        btn_artists = getattr(self.feeds_submodule, 'btn_artists', None)
        btn_albums = getattr(self.feeds_submodule, 'btn_albums', None)
        btn_labels = getattr(self.feeds_submodule, 'btn_labels', None)
        btn_genres = getattr(self.feeds_submodule, 'btn_genres', None)
        btn_time = getattr(self.feeds_submodule, 'btn_time', None)
        btn_listens = getattr(self.feeds_submodule, 'btn_listens', None)
        btn_info = getattr(self.feeds_submodule, 'btn_info', None)
        
        # Connect buttons using the main handler
        if btn_artists:
            btn_artists.clicked.connect(
                lambda: self.main_handler.trigger_event('feeds_artists_clicked')
            )
            self.main_handler.register_callback(
                'feeds_artists_clicked',
                self.feeds_submodule.on_artists_clicked,
                'feeds_submodule'
            )
            
        if btn_albums:
            btn_albums.clicked.connect(
                lambda: self.main_handler.trigger_event('feeds_albums_clicked')
            )
            self.main_handler.register_callback(
                'feeds_albums_clicked',
                self.feeds_submodule.on_albums_clicked,
                'feeds_submodule'
            )
            
        if btn_labels:
            btn_labels.clicked.connect(
                lambda: self.main_handler.trigger_event('feeds_labels_clicked')
            )
            self.main_handler.register_callback(
                'feeds_labels_clicked',
                self.feeds_submodule.on_labels_clicked,
                'feeds_submodule'
            )
            
        # Connect the remaining buttons similarly
        if btn_genres:
            btn_genres.clicked.connect(
                lambda: self.main_handler.trigger_event('feeds_genres_clicked')
            )
            self.main_handler.register_callback(
                'feeds_genres_clicked',
                self.feeds_submodule.on_genres_clicked,
                'feeds_submodule'
            )
            
        if btn_time:
            btn_time.clicked.connect(
                lambda: self.main_handler.trigger_event('feeds_time_clicked')
            )
            self.main_handler.register_callback(
                'feeds_time_clicked',
                self.feeds_submodule.on_time_clicked,
                'feeds_submodule'
            )
            
        if btn_listens:
            btn_listens.clicked.connect(
                lambda: self.main_handler.trigger_event('feeds_listens_clicked')
            )
            self.main_handler.register_callback(
                'feeds_listens_clicked',
                self.feeds_submodule.on_listens_clicked,
                'feeds_submodule'
            )
            
        if btn_info:
            btn_info.clicked.connect(
                lambda: self.main_handler.trigger_event('feeds_info_clicked')
            )
            self.main_handler.register_callback(
                'feeds_info_clicked',
                self.feeds_submodule.on_info_clicked,
                'feeds_submodule'
            )
        
    def on_category_changed(self, index, category_name):
        """
        Handle category changes to initialize feeds data when needed.
        
        Args:
            index: The index of the selected category
            category_name: The name of the selected category
        """
        if category_name == "Feeds" and self.feeds_submodule:
            # The feeds tab was selected, initialize its data
            self.feeds_submodule.load_feed_stats()
            logging.info("Feeds category selected, initializing data")
        
        # Additional feeds-specific category change handling can go here
