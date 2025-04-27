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