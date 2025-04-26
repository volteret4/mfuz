from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from modules.submodules.fuzzy.entity_view_submodule import EntityView

class FeedsView(QWidget):
    """
    View for displaying feeds data.
    """
    
    # Signal for returning to main view
    backRequested = pyqtSignal()
    
    def __init__(self, parent=None, db=None):
        """
        Initialize Feeds View.
        
        Args:
            parent: Parent widget
            db: Database instance
        """
        super().__init__(parent)
        self.db = db
        
        # Set up UI
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        
        # Add back button
        self.back_button = QPushButton("Volver a Info")
        self.back_button.setObjectName("back_button")
        self.back_button.clicked.connect(self.backRequested.emit)
        self.layout.addWidget(self.back_button)
        
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
        
        # Set content widget to scroll area
        self.scroll_area.setWidget(self.content_widget)
        
        # Add scroll area to main layout
        self.layout.addWidget(self.scroll_area)
        
    def clear(self):
        """Clear all content."""
        # Clear content layout
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def show_feeds(self, entity_type, entity_id):
        """
        Show feeds for an entity.
        
        Args:
            entity_type (str): Type of entity ('artist', 'album', 'song')
            entity_id (int): ID of the entity
        """
        # Clear previous content
        self.clear()
        
        if not self.db or not entity_type or not entity_id:
            self._show_no_feeds_message()
            return
            
        # Get feeds from database
        feeds = self.db.get_feeds_data(entity_type, entity_id)
        
        if not feeds:
            self._show_no_feeds_message()
            return
            
        # Display feeds
        for feed in feeds:
            self._create_feed_card(feed)
            
        # Add stretch at the end
        self.content_layout.addStretch()
        
    def _show_no_feeds_message(self):
        """Show message when no feeds are available."""
        message = QLabel("No hay feeds disponibles para esta entidad.")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(message)
        self.content_layout.addStretch()
        
    def _create_feed_card(self, feed_data):
        """
        Create a card for a feed.
        
        Args:
            feed_data (dict): Feed data
        """
        from tools.music_fuzzy.collapsible_groupbox import CollapsibleGroupBox
        
        # Extract feed data
        feed_name = feed_data.get('feed_name', 'Feed')
        post_title = feed_data.get('post_title', '')
        post_url = feed_data.get('post_url', '')
        post_date = feed_data.get('post_date', '')
        content = feed_data.get('content', '')
        
        if not content.strip():
            return
            
        # Create title with date if available
        title = feed_name
        if post_title:
            title += f" - {post_title}"
        if post_date:
            title += f" ({post_date})"
            
        # Create collapsible group box
        group = CollapsibleGroupBox(title)
        
        # Create content label
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.TextFormat.RichText)
        content_label.setOpenExternalLinks(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        
        # Add link to post if available
        if post_url:
            content_label.setText(content + f"<br><br><a href='{post_url}'>Ver publicación original</a>")
            
        # Add content to group
        group.add_widget(content_label)
        
        # Add group to layout
        self.content_layout.addWidget(group)