def setup_rss_controls(self):
    """Configura controles adicionales para playlists RSS"""
    try:
        # Buscar el botón existente en la UI
        existing_button = self.findChild(QPushButton, 'mark_as_listened_button')
        
        if existing_button:
            # Si existe, simplemente conectar su señal
            existing_button.clicked.connect(self.mark_current_rss_as_listened)
            self.log("Botón 'mark_as_listened_button' encontrado en UI y conectado")
            
            # Guardar referencia para uso posterior
            self.mark_as_listened_button = existing_button
                
        # Añadir un botón de actualización para depuración
        refresh_button = self.findChild(QPushButton, 'refresh_rss_button')
        if not refresh_button:
            # Create a refresh button if it doesn't exist
            refresh_button = QPushButton("Actualizar RSS")
            refresh_button.setIcon(QIcon(":/services/rss"))
            refresh_button.setToolTip("Recargar playlists RSS")
            refresh_button.setObjectName("refresh_rss_button")
            
            # Find a place to add the button
            if hasattr(self, 'tree_container_frame'):
                self.tree_container_frame.layout().addWidget(refresh_button)
            elif hasattr(self, 'tree_container'):
                if self.tree_container.layout():
                    self.tree_container.layout().addWidget(refresh_button)
                else:
                    layout = QVBoxLayout(self.tree_container)
                    layout.addWidget(refresh_button)
            
            # Connect signal
            refresh_button.clicked.connect(self.actualizar_playlists_rss)
            self.log("Botón de actualización RSS creado y conectado")
            
        else:
            refresh_button.clicked.connect(self.reload_rss_playlists)
            self.log("Botón de actualización RSS existente conectado")
            
        self.log("Controles RSS configurados")
        return True
            
    except Exception as e:
        self.log(f"Error configurando controles RSS: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False


def load_rss_playlist_content(self, playlist_item, playlist_data):
    """Carga el contenido de una playlist RSS como hijos del item de la playlist"""
    try:
        # Limpiar cualquier contenido previo
        while playlist_item.childCount() > 0:
            playlist_item.removeChild(playlist_item.child(0))
            
        # Ruta de la playlist
        playlist_path = playlist_data['path']
        
        # Verificar archivo relacionado de títulos (txt con mismo nombre que la playlist)
        txt_path = os.path.splitext(playlist_path)[0] + '.txt'
        titles = []
        
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                titles = [line.strip() for line in f.readlines()]
        
        # Leer la playlist
        track_index = 0
        with open(playlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Obtener título si está disponible, de lo contrario usar URL
                    title = line
                    if track_index < len(titles) and titles[track_index]:
                        title = titles[track_index]
                    
                    # Crear item para la pista
                    track_item = QTreeWidgetItem(playlist_item)
                    track_item.setText(0, title)
                    track_item.setText(1, playlist_data['blog']) # Blog como "artista"
                    track_item.setText(2, "Track") # Tipo
                    
                    # Determinar fuente y establecer icono adecuado
                    source = self._determine_source_from_url(line)
                    track_item.setIcon(0, self.get_source_icon(line, {'source': source}))
                    
                    # Almacenar datos para reproducción
                    track_data = {
                        'title': title,
                        'url': line,
                        'type': 'track',
                        'source': source,
                        'blog': playlist_data['blog'],
                        'playlist': playlist_data['name']
                    }
                    track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
                    
                    track_index += 1
        
        # Expandir el item de la playlist
        playlist_item.setExpanded(True)
        
        # Almacenar datos de la playlist actual para otras operaciones
        self.current_rss_playlist = playlist_data
        
        self.log(f"Cargada playlist RSS '{playlist_data['name']}' con {track_index} pistas")
        return True
    except Exception as e:
        self.log(f"Error cargando contenido de playlist RSS: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False