# Añadir a init_ui o en una función específica para configurar la UI
def setup_progress_bar(self):
    """Configura una barra de progreso minimalista en la parte inferior"""
    try:
        from PyQt6.QtWidgets import QProgressBar
        from PyQt6.QtCore import Qt
        
        # Crear la barra de progreso minimalista
        self.status_progress_bar = QProgressBar(self)
        self.status_progress_bar.setMaximumHeight(2)  # Altura de 2px
        self.status_progress_bar.setTextVisible(False)  # Sin texto
        self.status_progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: transparent;
                margin: 0px;
                padding: 0px;
            }
            QProgressBar::chunk {
                background-color: #3498db;  /* Color azul */
            }
        """)
        
        # Ocultar inicialmente
        self.status_progress_bar.hide()
        
        # Añadir al layout principal - necesitamos encontrar el layout adecuado
        main_layout = None
        
        # Intentar encontrar el layout principal
        if hasattr(self, 'layout'):
            main_layout = self.layout()
        else:
            # Buscar por nombre
            main_frame = self.findChild(QFrame, 'main_frame')
            if main_frame and main_frame.layout():
                main_layout = main_frame.layout()
        
        if main_layout:
            main_layout.addWidget(self.status_progress_bar)
            self.log("Barra de progreso configurada")
            return True
        else:
            # Si no encontramos un layout adecuado, añadirlo directamente
            self.status_progress_bar.setParent(self)
            self.status_progress_bar.setGeometry(0, self.height() - 2, self.width(), 2)
            
            # Conectar a cambios de tamaño para mantener la posición
            self.resizeEvent = lambda event: self._update_progress_bar_position(event)
            
            self.log("Barra de progreso configurada manualmente")
            return True
            
    except Exception as e:
        self.log(f"Error configurando barra de progreso: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False

def _update_progress_bar_position(self, event):
    """Actualiza la posición de la barra de progreso cuando cambia el tamaño"""
    if hasattr(self, 'status_progress_bar'):
        self.status_progress_bar.setGeometry(0, self.height() - 2, self.width(), 2)
    
    # Llamar al evento original si existe
    if hasattr(self, '_original_resize_event'):
        self._original_resize_event(event)

# Modificar las funciones de manejo de señales para usar la barra de progreso
def _on_process_started(self, message):
    """Handle process started signal (runs in main thread)"""
    from PyQt6.QtWidgets import QProgressDialog
    from PyQt6.QtCore import Qt
    
    # Ocultar diálogo de progreso anterior si existe
    if hasattr(self, '_progress_dialog') and self._progress_dialog:
        self._progress_dialog.close()
        self._progress_dialog = None
    
    # Usar la barra de progreso minimalista si está disponible
    if hasattr(self, 'status_progress_bar'):
        self.status_progress_bar.setValue(0)
        self.status_progress_bar.show()
        # Opcional: actualizar statusbar con el mensaje si existe
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(message)
    else:
        # Fallback al diálogo tradicional
        self._progress_dialog = QProgressDialog(message, "Cancel", 0, 100, self)
        self._progress_dialog.setWindowTitle("Processing")
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()

def _on_process_progress(self, value, message=None):
    """Handle process progress signal (runs in main thread)"""
    # Usar la barra de progreso minimalista si está disponible
    if hasattr(self, 'status_progress_bar'):
        self.status_progress_bar.setValue(value)
        # Opcional: actualizar statusbar con el mensaje si existe
        if message and hasattr(self, 'statusBar'):
            self.statusBar().showMessage(message)
    elif hasattr(self, '_progress_dialog') and self._progress_dialog:
        # Fallback al diálogo tradicional
        if message:
            self._progress_dialog.setLabelText(message)
        self._progress_dialog.setValue(value)

def _on_process_finished(self, message, success_count, total_count):
    """Handle process finished signal (runs in main thread)"""
    # Usar la barra de progreso minimalista si está disponible
    if hasattr(self, 'status_progress_bar'):
        self.status_progress_bar.setValue(100)
        # Programar ocultamiento después de un tiempo
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self.status_progress_bar.hide)
        # Opcional: actualizar statusbar con el mensaje si existe
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(f"{message} - Procesados: {success_count}/{total_count}", 3000)
    elif hasattr(self, '_progress_dialog') and self._progress_dialog:
        # Fallback al diálogo tradicional
        self._progress_dialog.setValue(100)
        self._progress_dialog.setLabelText(f"{message}\nProcesados: {success_count}/{total_count}")
        
        # Keep dialog open briefly
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self._progress_dialog.close)

def _on_process_error(self, error_message):
    """Handle process error signal (runs in main thread)"""
    from PyQt6.QtWidgets import QMessageBox
    
    # Ocultar la barra de progreso si existe
    if hasattr(self, 'status_progress_bar'):
        self.status_progress_bar.hide()
        # Opcional: actualizar statusbar con el mensaje si existe
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage("Error: " + error_message, 5000)  # Mostrar por 5 segundos
    
    # Cerrar el diálogo de progreso si existe
    if hasattr(self, '_progress_dialog') and self._progress_dialog:
        self._progress_dialog.close()
    
    # Mostrar mensaje de error
    QMessageBox.critical(self, "Error", error_message)