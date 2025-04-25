from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal

class EntityView(QWidget):
    """
    Base class for entity detail views (artist, album, track).
    Provides common functionality and signals.
    """
    
    # Signals
    requestPlayback = pyqtSignal(object)  # Emitted when playback is requested
    requestOpenFolder = pyqtSignal(object)  # Emitted when folder opening is requested
    
    def __init__(self, parent=None, db=None, media_finder=None, link_buttons=None):
        """
        Initialize entity view.
        
        Args:
            parent: Parent widget
            db: Database instance
            media_finder: MediaFinder instance
            link_buttons: LinkButtonsManager instance
        """
        super().__init__(parent)
        self.db = db
        self.media_finder = media_finder
        self.link_buttons = link_buttons
        
        # Set up base layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        
        # Initialize components
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up UI components. Override in subclasses."""
        pass
        
    def clear(self):
        """Clear all content. Override in subclasses."""
        pass
        
    def show_entity(self, entity_data):
        """
        Show entity details. Override in subclasses.
        
        Args:
            entity_data: Data of the entity to display
        """
        pass
    
    def create_info_card(self, title, content, css_class="info-card"):
        """
        Create an information card with title and content.
        
        Args:
            title (str): Title of the card
            content (str): Content of the card
            css_class (str): CSS class for styling
            
        Returns:
            QFrame: Frame containing the card
        """
        from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
        
        # Create card frame
        card = QFrame()
        card.setObjectName(css_class)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        
        # Create title label
        title_label = QLabel(f"<h3>{title}</h3>")
        title_label.setTextFormat(Qt.TextFormat.RichText)
        card_layout.addWidget(title_label)
        
        # Create content label
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.TextFormat.RichText)
        content_label.setOpenExternalLinks(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        card_layout.addWidget(content_label)
        
        return card
        
    def create_metadata_card(self, metadata_dict, css_class="metadata-card"):
        """
        Create a metadata card from a dictionary of metadata.
        
        Args:
            metadata_dict (dict): Dictionary of metadata {label: value}
            css_class (str): CSS class for styling
            
        Returns:
            QFrame: Frame containing the metadata card
        """
        from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
        
        # Create card frame
        card = QFrame()
        card.setObjectName(css_class)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        
        # Create content from metadata dictionary
        content = ""
        for label, value in metadata_dict.items():
            if value:  # Only add non-empty values
                content += f"<b>{label}:</b> {value}<br>"
        
        # Create content label
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.TextFormat.RichText)
        content_label.setOpenExternalLinks(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        card_layout.addWidget(content_label)
        
        return card
        
    def extract_links(self, entity_data, entity_type):
        """
        Extract links from entity data.
        
        Args:
            entity_data: Data of the entity
            entity_type (str): Type of entity ('artist', 'album', 'track')
            
        Returns:
            dict: Dictionary of links {service_name: url}
        """
        links = {}
        
        if not entity_data:
            return links
            
        # Extract from dictionary
        if isinstance(entity_data, dict):
            for key, value in entity_data.items():
                if key.endswith('_url') and value and isinstance(value, str) and value.strip():
                    service_name = key.replace('_url', '')
                    links[service_name] = value
        
        # Extract from tuple/list (database query result)
        elif isinstance(entity_data, (list, tuple)):
            # Mappings for known indices
            if entity_type == 'artist' and len(entity_data) > 20:
                url_indices = {
                    'spotify': 16,
                    'youtube': 17,
                    'musicbrainz': 18,
                    'discogs': 19,
                    'rateyourmusic': 20,
                    'wikipedia': 26
                }
                
                for service, idx in url_indices.items():
                    if idx < len(entity_data) and entity_data[idx]:
                        links[service] = entity_data[idx]
                        
            elif entity_type == 'album' and len(entity_data) > 25:
                url_indices = {
                    'spotify': 21,
                    'youtube': 22,
                    'musicbrainz': 23,
                    'discogs': 24,
                    'rateyourmusic': 25,
                    'wikipedia': 28
                }
                
                for service, idx in url_indices.items():
                    if idx < len(entity_data) and entity_data[idx]:
                        links[service] = entity_data[idx]
        
        return links