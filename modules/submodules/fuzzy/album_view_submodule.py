from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt

class AlbumView(EntityView):
    """
    View for displaying album details.
    """
    
    def __init__(self, parent=None, db=None, media_finder=None, link_buttons=None):
        """Initialize Album View."""
        super().__init__(parent, db, media_finder, link_buttons)
        
    def _setup_ui(self):
        """Set up UI components for album view."""
        # Clear existing layout
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create scroll area for content
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create content widget for scroll area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(16)
        
        # Add widgets to content layout
        self.metadata_container = QWidget()
        self.metadata_layout = QVBoxLayout(self.metadata_container)
        self.metadata_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tracks_container = QWidget()
        self.tracks_layout = QVBoxLayout(self.tracks_container)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)
        
        self.wiki_container = QWidget()
        self.wiki_layout = QVBoxLayout(self.wiki_container)
        self.wiki_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add containers to content layout
        self.content_layout.addWidget(self.metadata_container)
        self.content_layout.addWidget(self.tracks_container)
        self.content_layout.addWidget(self.wiki_container)
        self.content_layout.addStretch()
        
        # Set content widget to scroll area
        self.scroll_area.setWidget(self.content_widget)
        
        # Add scroll area to main layout
        self.layout.addWidget(self.scroll_area)
        
    def clear(self):
        """Clear all content."""
        # Clear container layouts
        self._clear_layout(self.metadata_layout)
        self._clear_layout(self.tracks_layout)
        self._clear_layout(self.wiki_layout)
        
        # Hide containers
        self.metadata_container.setVisible(False)
        self.tracks_container.setVisible(False)
        self.wiki_container.setVisible(False)
        
        # Clear link buttons if available
        if self.link_buttons:
            self.link_buttons.update_album_links({})
            
    def _clear_layout(self, layout):
        """Clear all widgets from a layout."""
        if not layout:
            return
            
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def show_entity(self, album_data, tracks=None):
        """
        Show album details.
        
        Args:
            album_data: Dictionary with album data or tuple from database query
            tracks: List of track items (optional)
        """
        if not album_data:
            return
            
        # Clear previous content
        self.clear()
        
        # Get album info
        album_name = None
        artist_name = None
        year = None
        genre = None
        
        if isinstance(album_data, dict):
            album_name = album_data.get('name')
            artist_name = album_data.get('artist')
            year = album_data.get('year')
            genre = album_data.get('genre')
        elif isinstance(album_data, (list, tuple)) and len(album_data) > 5:
            album_name = album_data[5]  # Assuming index 5 is album name
            artist_name = album_data[3]  # Assuming index 3 is artist name
            if len(album_data) > 6:
                year = album_data[6]  # Assuming index 6 is date/year
            if len(album_data) > 7:
                genre = album_data[7]  # Assuming index 7 is genre
            
        if not album_name or not artist_name:
            return
            
        # Get complete album info from database if needed
        album_db_info = None
        
        if isinstance(album_data, dict) and album_data.get('type') == 'album':
            # We only have basic info, fetch complete info
            album_db_info = self.db.get_album_info(album_name, artist_name)
        elif isinstance(album_data, (list, tuple)):
            # We have a song tuple, fetch album info
            album_db_info = self.db.get_album_info(album_name, artist_name)
        else:
            # We already have complete info
            album_db_info = album_data
            
        # Calculate total tracks and duration
        total_tracks = 0
        total_duration = 0
        
        if tracks:
            total_tracks = len(tracks)
            for track in tracks:
                track_data = track.data(0, Qt.ItemDataRole.UserRole)
                if track_data and len(track_data) > 19:  # Assuming index 19 is duration
                    try:
                        duration = track_data[19]
                        if isinstance(duration, (int, float)) and duration > 0:
                            total_duration += duration
                    except (ValueError, TypeError, IndexError):
                        pass
                        
        # Format duration
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        seconds = int(total_duration % 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
        # Show metadata
        self._show_album_metadata(album_db_info, album_name, artist_name, year, genre, total_tracks, duration_str)
        
        # Show Wikipedia content
        self._show_album_wiki(album_db_info)
        
        # Show link buttons
        self._update_link_buttons(album_db_info)
        
    def _show_album_metadata(self, album_db_info, album_name, artist_name, year, genre, total_tracks, duration_str):
        """Show album metadata."""
        metadata = {}
        
        # Basic metadata
        metadata["Álbum"] = album_name
        metadata["Artista"] = artist_name
        
        # Add additional info
        if album_db_info:
            if album_db_info.get('year'):
                metadata["Fecha"] = album_db_info['year']
            elif year:
                metadata["Fecha"] = year
                
            if album_db_info.get('genre'):
                metadata["Género"] = album_db_info['genre']
            elif genre:
                metadata["Género"] = genre
                
            if album_db_info.get('label'):
                metadata["Sello"] = album_db_info['label']
                
            if album_db_info.get('total_tracks'):
                metadata["Pistas"] = album_db_info['total_tracks']
            elif total_tracks > 0:
                metadata["Pistas"] = total_tracks
                
            metadata["Duración"] = duration_str
            
            # Additional album-specific metadata
            if album_db_info.get('producers'):
                metadata["Productores"] = album_db_info['producers']
            if album_db_info.get('engineers'):
                metadata["Ingenieros"] = album_db_info['engineers']
            if album_db_info.get('mastering_engineers'):
                metadata["Mastering"] = album_db_info['mastering_engineers']
        else:
            # Use provided info if database info not available
            if year:
                metadata["Fecha"] = year
            if genre:
                metadata["Género"] = genre
            if total_tracks > 0:
                metadata["Pistas"] = total_tracks
            metadata["Duración"] = duration_str
                
        # Create and add metadata card
        metadata_card = self.create_metadata_card(metadata)
        self.metadata_layout.addWidget(metadata_card)
        self.metadata_container.setVisible(True)
            
    def _show_album_wiki(self, album_db_info):
        """Show album Wikipedia content."""
        if not album_db_info:
            return
            
        wiki = album_db_info.get('wikipedia_content')
        if wiki and wiki.strip():
            wiki_card = self.create_info_card("Wikipedia", wiki)
            self.wiki_layout.addWidget(wiki_card)
            self.wiki_container.setVisible(True)
            
    def _update_link_buttons(self, album_db_info):
        """Update album link buttons."""
        if not self.link_buttons or not album_db_info:
            return
            
        # Extract links from album info
        links = self.extract_links(album_db_info, 'album')
            
        # Update link buttons
        self.link_buttons.update_album_links(links)