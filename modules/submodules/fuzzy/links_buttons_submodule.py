# 1. Modifica la clase LinkButtonsManager para que acepte los nombres de variables correctos
# Añade este cambio al archivo links_buttons_submodule.py

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
        from PyQt6.QtWidgets import QHBoxLayout
        
        self.artist_group = artist_group  # Esta variable se llama artist_group aquí
        self.album_group = album_group    # Esta variable se llama album_group aquí
        self.artist_buttons = {}
        self.album_buttons = {}
        
        # Debug de estado inicial
        print(f"[DEBUG] Inicializando LinkButtonsManager")
        print(f"[DEBUG] artist_group: {self.artist_group}")
        print(f"[DEBUG] album_group: {self.album_group}")
        
        # Verificar los layouts
        if self.artist_group:
            if not self.artist_group.layout():
                print(f"[DEBUG] artist_group no tiene layout, creando uno nuevo")
                layout = QHBoxLayout(self.artist_group)
                layout.setContentsMargins(5, 25, 5, 5)
                layout.setSpacing(5)
            else:
                print(f"[DEBUG] artist_group tiene layout: {self.artist_group.layout()}")
                # En lugar de crear un nuevo layout, simplemente limpiar el existente
                self._clear_layout(self.artist_group.layout(), self.artist_buttons)
        else:
            print(f"[DEBUG] artist_group no existe")
                
        if self.album_group:
            if not self.album_group.layout():
                print(f"[DEBUG] album_group no tiene layout, creando uno nuevo")
                layout = QHBoxLayout(self.album_group)
                layout.setContentsMargins(5, 25, 5, 5)
                layout.setSpacing(5)
            else:
                print(f"[DEBUG] album_group tiene layout: {self.album_group.layout()}")
                # En lugar de crear un nuevo layout, simplemente limpiar el existente
                self._clear_layout(self.album_group.layout(), self.album_buttons)
        else:
            print(f"[DEBUG] album_group no existe")
                
        # Ocultar inicialmente
        if self.artist_group:
            self.artist_group.hide()
        if self.album_group:
            self.album_group.hide()
    
    def update_artist_links(self, links_dict):
        """
        Update artist link buttons.
        
        Args:
            links_dict (dict): Dictionary of links {service_name: url}
            
        Returns:
            bool: True if buttons were shown, False otherwise
        """
        print(f"[DEBUG] update_artist_links: {len(links_dict)} enlaces")
        
        # Verificar que el grupo existe
        if not self.artist_group:
            print(f"[DEBUG] ERROR: artist_group no existe")
            return False
        
        # Verificar que podemos obtener su layout
        layout = self.artist_group.layout()
        if not layout:
            print(f"[DEBUG] ERROR: artist_group no tiene layout")
            return False
            
        # Limpiar el layout
        self._clear_layout(layout, self.artist_buttons)
            
        # Actualizar los botones
        result = self._update_buttons(self.artist_group, layout, links_dict, self.artist_buttons, 'artist')
        
        # Forzar visibilidad después de actualizar
        if result:
            self.artist_group.setVisible(True)
            self.artist_group.show()
            parent = self.artist_group.parent()
            if parent:
                parent.setVisible(True)
                parent.show()
        
        return result
    
    def update_album_links(self, links_dict):
        """
        Update album link buttons.
        
        Args:
            links_dict (dict): Dictionary of links {service_name: url}
            
        Returns:
            bool: True if buttons were shown, False otherwise
        """
        print(f"[DEBUG] update_album_links: {len(links_dict)} enlaces")
        
        # Verificar que el grupo existe
        if not self.album_group:
            print(f"[DEBUG] ERROR: album_group no existe")
            return False
        
        # Verificar que podemos obtener su layout
        layout = self.album_group.layout()
        if not layout:
            print(f"[DEBUG] ERROR: album_group no tiene layout")
            return False
            
        # Limpiar el layout
        self._clear_layout(layout, self.album_buttons)
            
        # Actualizar los botones
        result = self._update_buttons(self.album_group, layout, links_dict, self.album_buttons, 'album')
        
        # Forzar visibilidad después de actualizar
        if result:
            self.album_group.setVisible(True)
            self.album_group.show()
            parent = self.album_group.parent()
            if parent:
                parent.setVisible(True)
                parent.show()
        
        return result
        
    def _clear_layout(self, layout, buttons_dict):
        """Clear all widgets from a layout and empty the buttons dictionary."""
        if not layout:
            print(f"[DEBUG] No hay layout para limpiar")
            return
            
        # Take all items from the layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear the buttons dictionary
        buttons_dict.clear()
        print(f"[DEBUG] Layout limpiado correctamente")
    
    def _update_buttons(self, container, layout, links_dict, button_store, entity_type):
        """
        Actualiza los botones de enlaces.
        
        Args:
            container (QGroupBox): Group box container
            layout (QLayout): Layout of the container
            links_dict (dict): Dictionary of links {service_name: url}
            button_store (dict): Dictionary to store button references
            entity_type (str): Type of entity ('artist' or 'album')
            
        Returns:
            bool: True if buttons were shown, False otherwise
        """
        import traceback
        
        print(f"[DEBUG] Actualizando botones para {entity_type}")
        
        if not links_dict:
            print(f"[DEBUG] No hay enlaces para mostrar en {entity_type}")
            container.hide()
            return False
        
        # Filtrar enlaces no válidos o especiales
        filtered_links = {}
        for service_name, url in links_dict.items():
            if not url or not isinstance(url, str) or not url.strip():
                continue
            # Excluir campos que no son enlaces
            if service_name in ['s_updated', 'links_updated']:
                continue
            filtered_links[service_name] = url
            
        if not filtered_links:
            print(f"[DEBUG] No hay enlaces válidos para {entity_type} después de filtrar")
            container.hide()
            return False
            
        print(f"[DEBUG] Creando {len(filtered_links)} botones para {entity_type}")
        
        try:
            # Create buttons for each link
            for service_name, url in filtered_links.items():
                try:
                    # Create button
                    button = self._create_service_button(service_name, url, entity_type)
                    
                    # Add to layout
                    layout.addWidget(button)
                    
                    # Store reference
                    button_store[service_name] = button
                    
                    print(f"[DEBUG] Botón creado para {service_name}: {url[:30]}...")
                except Exception as btn_err:
                    print(f"[DEBUG] Error al crear botón para {service_name}: {btn_err}")
                    traceback.print_exc()
            
            # Add stretch at the end to push buttons to the left
            layout.addStretch()
            
            # Show container if buttons were added
            has_buttons = len(button_store) > 0
            
            # Forzar la visibilidad del contenedor
            if has_buttons:
                container.setVisible(True)
                container.show()  # Forzar mostrar
                print(f"[DEBUG] Contenedor de {entity_type} visible con {len(button_store)} botones")
                
                # Forzar actualización
                container.update()
                
                # Importante: asegurar que el contenedor padre también es visible
                parent = container.parent()
                if parent:
                    parent.setVisible(True)
                    parent.show()
                    print(f"[DEBUG] Contenedor padre de {entity_type} también visible")
            else:
                container.hide()
                print(f"[DEBUG] Contenedor de {entity_type} oculto - sin botones")
            
            return has_buttons
        except Exception as e:
            print(f"[DEBUG] Error en _update_buttons: {e}")
            traceback.print_exc()
            return False


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
        from PyQt6.QtWidgets import QPushButton
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize, QUrl
        
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


