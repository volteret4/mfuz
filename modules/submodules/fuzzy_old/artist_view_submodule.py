from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt
from modules.submodules.fuzzy.entity_view_submodule import EntityView


class ArtistView(EntityView):
    """
    View for displaying artist details.
    """
    
    def __init__(self, parent=None, db=None, media_finder=None, link_buttons=None):
        """Initialize Artist View."""
        super().__init__(parent, db, media_finder, link_buttons)
        
    def _setup_ui(self):
        """Set up UI components for artist view."""
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
        
        self.bio_container = QWidget()
        self.bio_layout = QVBoxLayout(self.bio_container)
        self.bio_layout.setContentsMargins(0, 0, 0, 0)
        
        self.wiki_container = QWidget()
        self.wiki_layout = QVBoxLayout(self.wiki_container)
        self.wiki_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add containers to content layout
        self.content_layout.addWidget(self.metadata_container)
        self.content_layout.addWidget(self.bio_container)
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
        self._clear_layout(self.bio_layout)
        self._clear_layout(self.wiki_layout)
        
        # Hide containers
        self.metadata_container.setVisible(False)
        self.bio_container.setVisible(False)
        self.wiki_container.setVisible(False)
        
        # Clear link buttons if available
        if self.link_buttons:
            self.link_buttons.update_artist_links({})
            
    def _clear_layout(self, layout):
        """Clear all widgets from a layout."""
        if not layout:
            return
            
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def show_entity(self, entity_data):
        """
        Show artist details con mejor manejo de errores.
        
        Args:
            entity_data: Dictionary with artist data or tuple from database query
        """
        if not entity_data:
            print("[DEBUG] No hay datos de artista para mostrar")
            return
            
        # Clear previous content
        self.clear()
        
        # Get artist name
        artist_name = None
        
        if isinstance(entity_data, dict):
            artist_name = entity_data.get('name')
            print(f"[DEBUG] Nombre de artista obtenido de diccionario: {artist_name}")
        elif isinstance(entity_data, (list, tuple)) and len(entity_data) > 3:
            artist_name = entity_data[3]  # Assuming index 3 is artist name
            print(f"[DEBUG] Nombre de artista obtenido de tupla: {artist_name}")
            
        if not artist_name:
            print("[DEBUG] No se pudo extraer el nombre del artista")
            return
            
        # Get complete artist info from database if needed
        artist_db_info = None
        
        try:
            if isinstance(entity_data, dict) and entity_data.get('type') == 'artist':
                # We only have basic info, fetch complete info
                print(f"[DEBUG] Obteniendo información completa del artista desde la BD: {artist_name}")
                artist_db_info = self.db.get_artist_info(artist_name)
            elif isinstance(entity_data, (list, tuple)):
                # We have a song tuple, fetch artist info
                print(f"[DEBUG] Obteniendo información del artista desde la BD (de canción): {artist_name}")
                artist_db_info = self.db.get_artist_info(artist_name)
            else:
                # We already have complete info
                artist_db_info = entity_data
                
            # Debug print for troubleshooting
            print(f"[DEBUG] Información de BD del artista: {artist_db_info}")
                
            # Show metadata
            self._show_artist_metadata(artist_db_info, artist_name)
            
            # Show bio
            self._show_artist_bio(artist_db_info)
            
            # Show Wikipedia content
            self._show_artist_wiki(artist_db_info)
            
            # Show link buttons
            self._update_link_buttons(artist_db_info)
        except Exception as e:
            import traceback
            print(f"[DEBUG] Error al mostrar detalles del artista: {e}")
            traceback.print_exc()

    def _update_buttons(self, container, layout, links_dict, button_store, entity_type):
        """
        Actualiza los botones de enlaces con mejor manejo de visibilidad.
        
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
            if service_name in ['s_updated', 'links_updated', 'last_updated']:
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
                # IMPORTANTE: Forzar actualización del layout
                container.layout().update()
                container.show()  # Forzar mostrar
                # Asegurarse de que el padre también es visible
                if container.parent():
                    container.parent().show()
                print(f"[DEBUG] Contenedor de {entity_type} visible con {len(button_store)} botones")
                
                # Forzar actualización
                container.update()
            else:
                container.hide()
                print(f"[DEBUG] Contenedor de {entity_type} oculto - sin botones")
            
            return has_buttons
        except Exception as e:
            print(f"[DEBUG] Error en _update_buttons: {e}")
            traceback.print_exc()
            return False


    def _show_artist_wiki(self, artist_db_info):
        """Show artist Wikipedia content con mejor manejo de errores."""
        if not artist_db_info:
            print("[DEBUG] No hay información de artista para mostrar Wikipedia")
            return
            
        try:
            wiki = artist_db_info.get('wikipedia_content')
            if wiki and wiki.strip():
                print(f"[DEBUG] Contenido de Wikipedia encontrado: {len(wiki)} caracteres")
                wiki_card = self.create_info_card("Wikipedia", wiki)
                self.wiki_layout.addWidget(wiki_card)
                self.wiki_container.setVisible(True)
            else:
                print("[DEBUG] No hay contenido de Wikipedia disponible")
                self.wiki_container.setVisible(False)
        except Exception as e:
            import traceback
            print(f"[DEBUG] Error al mostrar Wikipedia: {e}")
            traceback.print_exc()
            self.wiki_container.setVisible(False)

    def _show_artist_bio(self, artist_db_info):
        """Show artist biography con mejor manejo de errores."""
        if not artist_db_info:
            print("[DEBUG] No hay información de artista para mostrar biografía")
            return
            
        try:
            bio = artist_db_info.get('bio')
            if bio and bio.strip() and bio != "No hay información del artista disponible":
                print(f"[DEBUG] Biografía encontrada: {len(bio)} caracteres")
                bio_card = self.create_info_card("Información del Artista", bio)
                self.bio_layout.addWidget(bio_card)
                self.bio_container.setVisible(True)
            else:
                print("[DEBUG] No hay biografía disponible")
                self.bio_container.setVisible(False)
        except Exception as e:
            import traceback
            print(f"[DEBUG] Error al mostrar biografía: {e}")
            traceback.print_exc()
            self.bio_container.setVisible(False)
        
    def _show_artist_metadata(self, artist_db_info, artist_name):
        """Show artist metadata."""
        metadata = {}
        
        # Basic metadata
        metadata["Artista"] = artist_name
        
        # Add additional info if available
        if artist_db_info:
            if artist_db_info.get('origin'):
                metadata["Origen"] = artist_db_info['origin']
            if artist_db_info.get('formed_year'):
                metadata["Año de formación"] = artist_db_info['formed_year']
            if artist_db_info.get('total_albums'):
                metadata["Total de álbumes"] = artist_db_info['total_albums']
            if artist_db_info.get('tags'):
                metadata["Etiquetas"] = artist_db_info['tags']
            if artist_db_info.get('aliases'):
                metadata["Alias"] = artist_db_info['aliases']
            if artist_db_info.get('member_of'):
                metadata["Miembro de"] = artist_db_info['member_of']
                
        # Create and add metadata card
        metadata_card = self.create_metadata_card(metadata)
        self.metadata_layout.addWidget(metadata_card)
        self.metadata_container.setVisible(True)


    def _update_link_buttons(self, artist_db_info):
        """Update artist link buttons con mejor manejo de errores."""
        if not self.link_buttons:
            print("[DEBUG] No hay gestor de botones disponible")
            return
            
        try:
            # Extract links from artist info
            print("[DEBUG] Extrayendo enlaces del artista...")
            links = self.extract_links(artist_db_info, 'artist')
            
            # Add social media links if available
            if artist_db_info and artist_db_info.get('id'):
                print(f"[DEBUG] Obteniendo redes sociales para artist_id: {artist_db_info['id']}")
                network_links = self.db.get_artist_networks(artist_db_info['id'])
                print(f"[DEBUG] Enlaces de redes sociales obtenidos: {network_links}")
                links.update(network_links)
            
            # Asegurar que el grupo de enlaces sea visible
            if hasattr(self.link_buttons, 'artist_group') and self.link_buttons.artist_group:
                self.link_buttons.artist_group.show()
                
            # Update link buttons
            print(f"[DEBUG] Actualizando botones con {len(links)} enlaces")
            result = self.link_buttons.update_artist_links(links)
            print(f"[DEBUG] Resultado de actualización de enlaces: {result}")
            
        except Exception as e:
            import traceback
            print(f"[DEBUG] Error al actualizar botones de enlaces: {e}")
            traceback.print_exc()