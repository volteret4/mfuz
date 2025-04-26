from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt
from modules.submodules.fuzzy.entity_view_submodule import EntityView


class TrackView(EntityView):
    """
    View for displaying track details.
    """
    
    def __init__(self, parent=None, db=None, media_finder=None, link_buttons=None):
        """Initialize Track View."""
        super().__init__(parent, db, media_finder, link_buttons)
        
    def _setup_ui(self):
        """Set up UI components for track view."""
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
        
        self.lyrics_container = QWidget()
        self.lyrics_layout = QVBoxLayout(self.lyrics_container)
        self.lyrics_layout.setContentsMargins(0, 0, 0, 0)
        
        self.artist_info_container = QWidget()
        self.artist_info_layout = QVBoxLayout(self.artist_info_container)
        self.artist_info_layout.setContentsMargins(0, 0, 0, 0)
        
        self.wiki_container = QWidget()
        self.wiki_layout = QVBoxLayout(self.wiki_container)
        self.wiki_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add containers to content layout
        self.content_layout.addWidget(self.metadata_container)
        self.content_layout.addWidget(self.lyrics_container)
        self.content_layout.addWidget(self.artist_info_container)
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
        self._clear_layout(self.lyrics_layout)
        self._clear_layout(self.artist_info_layout)
        self._clear_layout(self.wiki_layout)
        
        # Hide containers
        self.metadata_container.setVisible(False)
        self.lyrics_container.setVisible(False)
        self.artist_info_container.setVisible(False)
        self.wiki_container.setVisible(False)
        
        # Clear link buttons if available
        if self.link_buttons:
            self.link_buttons.update_artist_links({})
            self.link_buttons.update_album_links({})
            
    def _clear_layout(self, layout):
        """Clear all widgets from a layout."""
        if not layout:
            return
            
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def show_entity(self, track_data):
        """
        Show track details.
        
        Args:
            track_data: Tuple from database query with track data
        """
        if not track_data or not isinstance(track_data, (list, tuple)) or len(track_data) < 3:
            return
            
        # Clear previous content
        self.clear()
        
        # Get basic track info
        track_id = track_data[0] if len(track_data) > 0 else None
        file_path = track_data[1] if len(track_data) > 1 else None
        title = track_data[2] if len(track_data) > 2 else "Unknown Title"
        artist = track_data[3] if len(track_data) > 3 else "Unknown Artist"
        album_artist = track_data[4] if len(track_data) > 4 else None
        album = track_data[5] if len(track_data) > 5 else "Unknown Album"
        
        # Get artist and album info from database
        artist_db_info = self.db.get_artist_info(artist) if artist else None
        album_db_info = self.db.get_album_info(album, artist) if album and artist else None
        
        # Debug información - descomentar para depuración
        # print(f"Track ID: {track_id}")
        # print(f"Artist DB Info: {artist_db_info}")
        # print(f"Album DB Info: {album_db_info}")
        
        # Show track metadata
        self._show_track_metadata(track_data)
        
        # Show lyrics if available
        if track_id:
            self._show_track_lyrics(track_id)
        
        # Show artist info
        if artist_db_info:
            self._show_artist_info(artist_db_info)
            
        # Show Wikipedia content if available
        if artist_db_info and artist_db_info.get('wikipedia_content'):
            self._show_wikipedia_content("Wikipedia del Artista", artist_db_info.get('wikipedia_content'))
            
        if album_db_info and album_db_info.get('wikipedia_content'):
            self._show_wikipedia_content("Wikipedia del Álbum", album_db_info.get('wikipedia_content'))
        
        # Update link buttons
        self._update_link_buttons(artist_db_info, album_db_info)
        
    def _show_track_metadata(self, track_data):
        """Show track metadata."""
        if not track_data or len(track_data) < 3:
            return
            
        metadata = {}
        
        # Extract metadata fields
        title = track_data[2] if len(track_data) > 2 else "Unknown Title"
        artist = track_data[3] if len(track_data) > 3 else "Unknown Artist"
        album_artist = track_data[4] if len(track_data) > 4 else None
        album = track_data[5] if len(track_data) > 5 else "Unknown Album"
        date = track_data[6] if len(track_data) > 6 else None
        genre = track_data[7] if len(track_data) > 7 else None
        label = track_data[8] if len(track_data) > 8 else None
        bitrate = track_data[10] if len(track_data) > 10 else None
        bit_depth = track_data[11] if len(track_data) > 11 else None
        sample_rate = track_data[12] if len(track_data) > 12 else None
        
        # Build metadata dictionary
        metadata["Título"] = title
        metadata["Artista"] = artist
        if album_artist and album_artist != artist:
            metadata["Album Artist"] = album_artist
        metadata["Álbum"] = album
        if date:
            metadata["Fecha"] = date
        if genre:
            metadata["Género"] = genre
        if label:
            metadata["Sello"] = label
        if bitrate:
            metadata["Bitrate"] = f"{bitrate} kbps"
        if bit_depth:
            metadata["Profundidad"] = f"{bit_depth} bits"
        if sample_rate:
            metadata["Frecuencia"] = f"{sample_rate} Hz"
            
        # Create and add metadata card
        metadata_card = self.create_metadata_card(metadata)
        self.metadata_layout.addWidget(metadata_card)
        self.metadata_container.setVisible(True)
        
    def _show_track_lyrics(self, track_id):
        """Show track lyrics."""
        if not track_id or not self.db:
            return
            
        # Get lyrics from database
        lyrics_data = self.db.get_lyrics(track_id)
        if not lyrics_data:
            return
            
        lyrics, source = lyrics_data
        
        if lyrics and lyrics.strip():
            # Create content with lyrics and source
            content = f"{lyrics}\n\n<i>Fuente: {source}</i>"
            
            # Create and add lyrics card
            lyrics_card = self.create_info_card("Letra", content)
            self.lyrics_layout.addWidget(lyrics_card)
            self.lyrics_container.setVisible(True)
            
    def _show_artist_info(self, artist_db_info):
        """Show artist information."""
        if not artist_db_info:
            return
            
        bio = artist_db_info.get('bio')
        if bio and bio.strip() and bio != "No hay información del artista disponible":
            # Create and add artist info card
            artist_card = self.create_info_card("Información del Artista", bio)
            self.artist_info_layout.addWidget(artist_card)
            self.artist_info_container.setVisible(True)
            
    def _show_wikipedia_content(self, title, content):
        """Show Wikipedia content."""
        if not content or not content.strip():
            return
            
        # Create and add wiki card
        wiki_card = self.create_info_card(title, content)
        self.wiki_layout.addWidget(wiki_card)
        self.wiki_container.setVisible(True)
            
    def _update_link_buttons(self, artist_db_info, album_db_info):
        """Update link buttons for artist and album."""
        if not self.link_buttons:
            return
            
        # Update artist links
        if artist_db_info:
            # Extract links from artist info
            artist_links = self.extract_links(artist_db_info, 'artist')
            
            # Add social media links if available
            if artist_db_info.get('id'):
                network_links = self.db.get_artist_networks(artist_db_info['id'])
                artist_links.update(network_links)
                
            # Update artist link buttons
            self.link_buttons.update_artist_links(artist_links)
            
        # Update album links
        if album_db_info:
            # Extract links from album info
            album_links = self.extract_links(album_db_info, 'album')
                
            # Update album link buttons
            self.link_buttons.update_album_links(album_links)