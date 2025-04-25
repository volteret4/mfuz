from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QGroupBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize, QUrl, pyqtSignal
import os

class LinkButtonsManager:
    """
    Manages link buttons for artists and albums.
    Handles creating, updating, and displaying buttons for external service links.
    """
    
    def __init__(self, artist_group, album_group):
        """
        Initialize with existing group boxes from UI.
        
        Args:
            artist_group (QGroupBox): Group box for artist links
            album_group (QGroupBox): Group box for album links
        """
        self.artist_group = artist_group
        self.album_group = album_group
        self.artist_buttons = {}
        self.album_buttons = {}
        
        # Initialize layouts safely
        self._setup_layouts()
        
    def _setup_layouts(self):
        """Safely set up layouts for both group boxes."""
        # Set up artist group layout
        if self.artist_group:
            if self.artist_group.layout():
                self.artist_layout = self.artist_group.layout()
            else:
                self.artist_layout = QHBoxLayout(self.artist_group)
                self.artist_layout.setContentsMargins(5, 25, 5, 5)
                self.artist_layout.setSpacing(5)
            self.artist_group.hide()
        
        # Set up album group layout
        if self.album_group:
            if self.album_group.layout():
                self.album_layout = self.album_group.layout()
            else:
                self.album_layout = QHBoxLayout(self.album_group)
                self.album_layout.setContentsMargins(5, 25, 5, 5)
                self.album_layout.setSpacing(5)
            self.album_group.hide()
    
    def clear_all(self):
        """Clear all buttons from both layouts."""
        self._clear_layout(self.artist_layout, self.artist_buttons)
        self._clear_layout(self.album_layout, self.album_buttons)
    
    def _clear_layout(self, layout, buttons_dict):
        """Clear all widgets from a layout and empty the buttons dictionary."""
        if not layout:
            return
            
        # Take all items from the layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear the buttons dictionary
        buttons_dict.clear()
    
    def update_artist_links(self, links_dict):
        """
        Update artist link buttons.
        
        Args:
            links_dict (dict): Dictionary of links {service_name: url}
            
        Returns:
            bool: True if buttons were shown, False otherwise
        """
        return self._update_buttons(
            self.artist_group,
            self.artist_layout,
            links_dict,
            self.artist_buttons,
            'artist'
        )
    
    def update_album_links(self, links_dict):
        """
        Update album link buttons.
        
        Args:
            links_dict (dict): Dictionary of links {service_name: url}
            
        Returns:
            bool: True if buttons were shown, False otherwise
        """
        return self._update_buttons(
            self.album_group,
            self.album_layout,
            links_dict,
            self.album_buttons,
            'album'
        )
    
    def _update_buttons(self, container, layout, links_dict, button_store, entity_type):
        """
        Update buttons in a container.
        
        Args:
            container (QGroupBox): Group box container
            layout (QLayout): Layout of the container
            links_dict (dict): Dictionary of links {service_name: url}
            button_store (dict): Dictionary to store button references
            entity_type (str): Type of entity ('artist' or 'album')
            
        Returns:
            bool: True if buttons were shown, False otherwise
        """
        if not container or not layout:
            return False
        
        # Clear existing buttons
        self._clear_layout(layout, button_store)
        
        if not links_dict:
            container.hide()
            return False
        
        # Create buttons for each link
        for service_name, url in links_dict.items():
            if not url or not isinstance(url, str) or not url.strip():
                continue
            
            # Create button
            button = self._create_service_button(service_name, url, entity_type)
            
            # Add to layout
            layout.addWidget(button)
            
            # Store reference
            button_store[service_name] = button
        
        # Add stretch at the end to push buttons to the left
        layout.addStretch()
        
        # Show container if buttons were added
        has_buttons = len(button_store) > 0
        container.setVisible(has_buttons)
        
        return has_buttons
    
    def _create_service_button(self, service_name, url, entity_type):
        """
        Create a button for a service link.
        
        Args:
            service_name (str): Name of the service
            url (str): URL of the service
            entity_type (str): Type of entity ('artist' or 'album')
            
        Returns:
            QPushButton: The created button
        """
        from PyQt6.QtGui import QDesktopServices
        
        # Normalize service name for icon and object name
        normalized_name = service_name.lower().replace('_', '')
        object_name = f"{normalized_name}_link_button"
        if entity_type == 'album':
            object_name = f"{normalized_name}_link_album_button"
        
        # Create button
        button = QPushButton()
        button.setFixedSize(34, 34)
        button.setObjectName(object_name)
        
        # Get icon from resources
        icon_path = f":/services/{normalized_name}"
        icon = QIcon(icon_path)
        
        if icon.isNull():
            # Try alternative icon names
            alternatives = [
                f":/services/{service_name.lower()}",
                f":/services/{service_name.lower().replace('-', '')}",
                f":/services/{service_name.lower().split('_')[0]}",
                f":/services/{service_name.lower().split('-')[0]}"
            ]
            
            for alt_path in alternatives:
                icon = QIcon(alt_path)
                if not icon.isNull():
                    break
        
        # If still no icon, use text fallback
        if icon.isNull():
            button.setText(service_name[:2].upper())
            print(f"No icon found for {service_name}, using text fallback")
        else:
            button.setIcon(icon)
            button.setIconSize(QSize(28, 28))
        
        # Set tooltip with service name
        button.setToolTip(f"{service_name.title()}: {url}")
        
        # Set URL as property
        button.setProperty("url", url)
        
        # Connect click event
        button.clicked.connect(lambda: self._open_url(url))
        
        return button
    
    @staticmethod
    def _open_url(url):
        """Open a URL in the default browser."""
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        
        if url and isinstance(url, str) and url.strip():
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            QDesktopServices.openUrl(QUrl(url))