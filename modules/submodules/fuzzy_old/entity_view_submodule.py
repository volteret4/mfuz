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
        Extrae enlaces de los datos de entidad con mejor manejo de formatos.
        
        Args:
            entity_data: Data of the entity
            entity_type (str): Type of entity ('artist', 'album', 'track')
            
        Returns:
            dict: Dictionary of links {service_name: url}
        """
        links = {}
        
        if not entity_data:
            print(f"[DEBUG] No hay datos para extraer enlaces - entity_type: {entity_type}")
            return links
            
        # Extract from dictionary
        if isinstance(entity_data, dict):
            for key, value in entity_data.items():
                # Busca cualquier campo que contenga "url" o "link"
                if ('url' in key.lower() or 'link' in key.lower()) and value and isinstance(value, str) and value.strip():
                    # Normaliza el nombre del servicio
                    service_name = key.replace('_url', '').replace('url', '').replace('_link', '').replace('link', '')
                    if service_name.startswith('_') or service_name.endswith('_'):
                        service_name = service_name.strip('_')
                    if service_name:
                        links[service_name] = value
                        print(f"[DEBUG] Enlace encontrado en diccionario: {service_name}: {value[:30]}...")
        
        # Manejo especial para los índices conocidos basados en el tipo de entidad
        elif isinstance(entity_data, (list, tuple)):
            # Define índices flexibles para diferentes versiones de la BD
            url_indices = {}
            
            if entity_type == 'artist':
                # Índices conocidos para artistas (ampliar rangos)
                url_indices = {
                    'spotify': [9, 16, 'spotify'],
                    'youtube': [10, 17, 'youtube'],
                    'musicbrainz': [11, 18, 'musicbrainz'],
                    'discogs': [12, 19, 'discogs'],
                    'rateyourmusic': [13, 20, 'rateyourmusic'],
                    'wikipedia': [15, 26, 'wiki'],
                    'bandcamp': [19, 20, 'bandcamp'],
                    'lastfm': [22, 23, 'lastfm']
                }
            elif entity_type == 'album':
                # Índices conocidos para álbumes (ampliar rangos)
                url_indices = {
                    'spotify': [9, 21, 'spotify'],
                    'youtube': [11, 22, 'youtube'],
                    'musicbrainz': [12, 23, 'musicbrainz'],
                    'discogs': [13, 24, 'discogs'],
                    'rateyourmusic': [14, 25, 'rateyourmusic'],
                    'wikipedia': [16, 28, 'wiki'],
                    'bandcamp': [22, 23, 'bandcamp'],
                    'lastfm': [26, 27, 'lastfm']
                }
                
            # Revisar todos los índices conocidos
            for service, info in url_indices.items():
                idx1, idx2, keyword = info
                # Probar el primer índice
                if idx1 < len(entity_data) and entity_data[idx1] and isinstance(entity_data[idx1], str) and entity_data[idx1].strip():
                    links[service] = entity_data[idx1]
                    print(f"[DEBUG] Enlace de {entity_type} encontrado en índice {idx1}: {service}")
                # Probar el segundo índice si el primero falló
                elif idx2 < len(entity_data) and entity_data[idx2] and isinstance(entity_data[idx2], str) and entity_data[idx2].strip():
                    links[service] = entity_data[idx2]
                    print(f"[DEBUG] Enlace de {entity_type} encontrado en índice {idx2}: {service}")
            
            # Buscar enlaces por contenido en cualquier campo de tipo string
            for i, item in enumerate(entity_data):
                if isinstance(item, str) and ('http://' in item or 'https://' in item):
                    # Intentar determinar el tipo de servicio por URL
                    for service, info in url_indices.items():
                        keyword = info[2]
                        if keyword in item.lower():
                            links[service] = item
                            print(f"[DEBUG] Enlace encontrado en posición {i}: {service}: {item[:30]}...")
                            break
        
        # Si no se encontraron enlaces, imprimir mensaje
        if not links:
            print(f"[DEBUG] No se encontraron enlaces para {entity_type} en los datos proporcionados")
        else:
            print(f"[DEBUG] Enlaces encontrados: {len(links)}")
            
        return links