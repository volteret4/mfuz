# submodules/muspy/progress_utils.py
import sys
import os
from PyQt6.QtWidgets import (QProgressDialog, QApplication, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QWidget, QSizePolicy, QMessageBox, QDialog)
from PyQt6.QtCore import pyqtSignal, Qt, QObject, QSize, QEvent, QPoint
from PyQt6.QtGui import QColor, QIcon

class ProgressWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    status_update = pyqtSignal(str)
    
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            result = self.function(
                progress_callback=self.progress.emit, 
                status_callback=self.status_update.emit,
                *self.args, 
                **self.kwargs
            )
            self.finished.emit(result)
        except Exception as e:
            self.status_update.emit(f"Error: {str(e)}")
            self.finished.emit([])


class AuthWorker(QObject):
    finished = pyqtSignal(bool)
    
    def __init__(self, auth_manager, username, password):
        super().__init__()
        self.auth_manager = auth_manager
        self.username = username
        self.password = password
    
    def authenticate(self):
        success = False
        try:
            # Actualizar credenciales
            self.auth_manager.username = self.username
            self.auth_manager.password = self.password
            
            # Intentar autenticar
            success = self.auth_manager.authenticate()
        except Exception as e:
            print(f"Error en autenticación en segundo plano: {e}")
        
        # Emitir señal cuando termine
        self.finished.emit(success)


class FloatingNavigationButtons(QObject):
    """
    Class to manage floating navigation buttons for a stacked widget.
    The buttons appear when mouse hovers over the left/right edge of the widget.
    """
    def __init__(self, stacked_widget, parent=None):
        super().__init__(parent)
        self.stacked_widget = stacked_widget
        self.parent_widget = parent if parent else stacked_widget.parent()
        
        # Create buttons
        self.prev_button = QPushButton(self.parent_widget)
        self.next_button = QPushButton(self.parent_widget)
        
        # Configure buttons
        self.setup_buttons()
        
        # Set up event filter for mouse tracking
        self.stacked_widget.setMouseTracking(True)
        self.stacked_widget.installEventFilter(self)
        
        # Hide buttons initially
        self.prev_button.hide()
        self.next_button.hide()
        
        # Connect signals
        self.connect_signals()
        
        # Track active areas
        self.left_active = False
        self.right_active = False
        
    def setup_buttons(self):
        """Set up button appearance and positioning"""
        # Set fixed size
        button_size = 40
        self.prev_button.setFixedSize(button_size, button_size)
        self.next_button.setFixedSize(button_size, button_size)
        
        # Set icons - use predefined icons from theme if available
        self.prev_button.setText("←")  # Fallback to text
        self.next_button.setText("→")  # Fallback to text
        
        try:
            self.prev_button.setIcon(QIcon.fromTheme("go-previous"))
            self.next_button.setIcon(QIcon.fromTheme("go-next"))
            # Set icon size
            icon_size = int(button_size * 0.7)
            self.prev_button.setIconSize(QSize(icon_size, icon_size))
            self.next_button.setIconSize(QSize(icon_size, icon_size))
        except:
            # Fallback to text if icons not available
            pass
        
        # Set style
        button_style = """
            QPushButton {
                background-color: rgba(66, 133, 244, 0.8);
                border-radius: 20px;
                color: white;
                border: none;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(82, 148, 255, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(58, 118, 216, 0.9);
            }
        """
        self.prev_button.setStyleSheet(button_style)
        self.next_button.setStyleSheet(button_style)
        
        # Add drop shadow effect for better visibility
        try:
            from PyQt6.QtWidgets import QGraphicsDropShadowEffect
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setColor(QColor(0, 0, 0, 160))
            shadow.setOffset(0, 0)
            self.prev_button.setGraphicsEffect(shadow)
            
            shadow2 = QGraphicsDropShadowEffect()
            shadow2.setBlurRadius(10)
            shadow2.setColor(QColor(0, 0, 0, 160))
            shadow2.setOffset(0, 0)
            self.next_button.setGraphicsEffect(shadow2)
        except:
            # Skip shadow effect if not available
            pass
        
        # Position the buttons
        self.update_button_positions()
        
    def update_button_positions(self):
        """Update the position of navigation buttons based on stacked widget size"""
        if not self.stacked_widget:
            return
            
        # Get the size of the stacked widget
        widget_rect = self.stacked_widget.rect()
        widget_height = widget_rect.height()
        
        # Position buttons vertically centered, on the edges
        y_position = (widget_height - self.prev_button.height()) // 2
        
        # Position the previous button on the left edge
        self.prev_button.move(10, y_position)
        
        # Position the next button on the right edge
        self.next_button.move(
            self.stacked_widget.width() - self.next_button.width() - 10, 
            y_position
        )
        
    def connect_signals(self):
        """Connect button signals to navigation functions"""
        self.prev_button.clicked.connect(self.go_to_previous_page)
        self.next_button.clicked.connect(self.go_to_next_page)
        
        # Connect to parent resize for repositioning
        if self.parent_widget:
            self.parent_widget.resizeEvent = self.handle_parent_resize
        
    def handle_parent_resize(self, event):
        """Handle parent resize event to update button positions"""
        self.update_button_positions()
        
        # Call original resize event if it exists
        original_resize = getattr(self.parent_widget.__class__, "resizeEvent", None)
        if original_resize and original_resize != self.handle_parent_resize:
            original_resize(self.parent_widget, event)
    
    def go_to_previous_page(self):
        """Navigate to the previous page in the stacked widget"""
        current_index = self.stacked_widget.currentIndex()
        if current_index > 0:
            self.stacked_widget.setCurrentIndex(current_index - 1)
        else:
            # Wrap around to the last page
            self.stacked_widget.setCurrentIndex(self.stacked_widget.count() - 1)
            
    def go_to_next_page(self):
        """Navigate to the next page in the stacked widget"""
        current_index = self.stacked_widget.currentIndex()
        if current_index < self.stacked_widget.count() - 1:
            self.stacked_widget.setCurrentIndex(current_index + 1)
        else:
            # Wrap around to the first page
            self.stacked_widget.setCurrentIndex(0)
    
    def eventFilter(self, obj, event):
        """Filter events to detect mouse hover on edges"""
        if obj == self.stacked_widget:
            if event.type() == QEvent.Type.Enter:
                # Mouse entered widget, show buttons if near edges
                # Fix: QEnterEvent uses position() not pos()
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                self.check_mouse_position(pos)
                
            elif event.type() == QEvent.Type.Leave:
                # Mouse left widget, hide buttons
                self.prev_button.hide()
                self.next_button.hide()
                self.left_active = False
                self.right_active = False
                
            elif event.type() == QEvent.Type.MouseMove:
                # Mouse moved inside widget, check position
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                self.check_mouse_position(pos)
        
        # Let the event continue to be processed
        return super().eventFilter(obj, event)
    
    def check_mouse_position(self, pos):
        """Check if mouse is near left or right edge and show appropriate button"""
        # Define edge sensitivity (px from edge)
        edge_sensitivity = 50
        
        # Check left edge
        if pos.x() <= edge_sensitivity:
            if not self.left_active:
                self.prev_button.show()
                self.left_active = True
        else:
            if self.left_active:
                self.prev_button.hide()
                self.left_active = False
        
        # Check right edge
        if pos.x() >= (self.stacked_widget.width() - edge_sensitivity):
            if not self.right_active:
                self.next_button.show()
                self.right_active = True
        else:
            if self.right_active:
                self.next_button.hide()
                self.right_active = False

def show_progress_operation(self, operation_function, operation_args=None, title="Operación en progreso", 
                            label_format="{current}/{total} - {status}", 
                            cancel_button_text="Cancelar", 
                            finish_message=None):
    """
    Ejecuta una operación con una barra de progreso, permitiendo cancelación.
    
    Args:
        operation_function (callable): Función a ejecutar que debe aceptar un objeto QProgressDialog
                                    como su primer argumento
        operation_args (dict, optional): Argumentos para pasar a la función de operación
        title (str): Título de la ventana de progreso
        label_format (str): Formato del texto de progreso, con placeholders {current}, {total}, {status}
        cancel_button_text (str): Texto del botón cancelar
        finish_message (str, optional): Mensaje a mostrar cuando la operación termina con éxito
                                    (None para no mostrar ningún mensaje)
    
    Returns:
        Any: El valor devuelto por la función de operación
    """
    # Crear el diálogo de progreso
    progress = QProgressDialog(self)
    progress.setWindowTitle(title)
    progress.setCancelButtonText(cancel_button_text)
    progress.setMinimumDuration(0)  # Mostrar inmediatamente
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    
    # Configuramos la progress bar para que permita rastreo indeterminado si es necesario
    progress.setMinimum(0)
    progress.setMaximum(100)  # Se puede cambiar desde la operación
    progress.setValue(0)
    
    # Configurar el status label inicial
    initial_status = label_format.format(current=0, total=0, status="Iniciando...")
    progress.setLabelText(initial_status)
    
    # Crear una función de actualización que la operación pueda utilizar
    def update_progress(current, total, status="Procesando...", indeterminate=False):
        if progress.wasCanceled():
            return False
        
        if indeterminate:
            # Modo indeterminado: 0 indica progreso indeterminado en Qt
            progress.setMinimum(0)
            progress.setMaximum(0)
        else:
            # Modo normal con porcentaje
            progress.setMinimum(0)
            progress.setMaximum(total)
            progress.setValue(current)
            
        # Actualizar el texto
        progress_text = label_format.format(current=current, total=total, status=status)
        progress.setLabelText(progress_text)
        
        # Procesar eventos para mantener la UI responsiva
        QApplication.processEvents()
        return True
    
    # Preparar argumentos
    if operation_args is None:
        operation_args = {}
    
    # Ejecutar la operación con la función de progreso
    try:
        result = operation_function(update_progress, **operation_args)
        
        # Mostrar mensaje de finalización si se proporciona
        if finish_message and not progress.wasCanceled():
            QMessageBox.information(self, "Operación completa", finish_message)
            
        return result
    except Exception as e:
        # Capturar cualquier excepción para no dejar el diálogo colgado
        import logging
        logging.error(f"Error en la operación: {e}", exc_info=True)
        
        # Solo mostrar error si no fue cancelado
        if not progress.wasCanceled():
            QMessageBox.critical(self, "Error", f"Se produjo un error durante la operación: {str(e)}")
        
        return None
    finally:
        # Asegurarse de que el diálogo se cierre
        progress.close()


def _sync_artists_with_progress(self, progress_callback, status_callback, count):
    """
    Background worker function to sync artists with progress updates
    
    Args:
        progress_callback: Function to call for progress updates
        status_callback: Function to call for status text updates
        count: Number of artists to sync
        
    Returns:
        dict: Sync results summary
    """
    try:
        # First try direct API import
        import_url = f"{self.base_url}/import/{self.muspy_id}"
        auth = (self.muspy_username, self.muspy_api_key)
        
        import_data = {
            'type': 'lastfm',
            'username': self.lastfm_username,
            'count': count,
            'period': 'overall'
        }
        
        status_callback("Sending request to Muspy API...")
        progress_callback(20)
        
        # Use POST for the import endpoint
        response = requests.post(import_url, auth=auth, json=import_data)
        
        if response.status_code in [200, 201]:
            status_callback(f"Successfully synchronized top {count} artists from Last.fm account {self.lastfm_username}")
            progress_callback(100)
            return {
                'success': True,
                'message': f"Successfully synchronized top {count} artists from Last.fm",
                'api_method': 'direct'
            }
        else:
            # If direct API fails, try using our LastFM manager as fallback
            status_callback("Direct API import failed. Trying alternative method...")
            progress_callback(30)
            
            # Use the alternative method
            result = self.sync_top_artists_from_lastfm(
                progress_callback=lambda p: progress_callback(30 + int(p * 0.7)),  # Scale to 30-100%
                status_callback=status_callback,
                count=count
            )
            
            return result
    except Exception as e:
        error_msg = f"Error syncing with Muspy API: {e}"
        status_callback(error_msg)
        self.logger.error(error_msg, exc_info=True)
        
        # Try alternative method
        status_callback("Trying alternative synchronization method...")
        progress_callback(30)
        
        # Use the alternative method
        result = self.sync_top_artists_from_lastfm(
            progress_callback=lambda p: progress_callback(30 + int(p * 0.7)),  # Scale to 30-100%
            status_callback=status_callback,
            count=count
        )
        
        return result
