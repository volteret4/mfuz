from PyQt6.QtCore import pyqtSignal, QObject

class LogSignals(QObject):
    """Signal class for logging from threads."""
    log_message = pyqtSignal(str)

# In the UrlPlayer class __init__:
def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
    # ... (existing code)
    
    # Create log signals for thread-safe logging
    self.log_signals = LogSignals()
    self.log_signals.log_message.connect(self._log_from_main_thread)
    
    # ... (rest of init)

def log(self, message):
    """Método seguro para registrar mensajes en el TextEdit y en la consola."""
    # Siempre imprimir en la consola
    print(f"[UrlPlayer] {message}")
    
    # Intentar añadir al TextEdit si está disponible
    if hasattr(self, 'textEdit') and self.textEdit:
        try:
            # Simplemente usar append que maneja el cursor internamente
            self.textEdit.append(str(message))
        except Exception as e:
            print(f"[UrlPlayer] Error escribiendo en textEdit: {e}")

def _log_from_main_thread(self, message):
    """Handler that runs in the main thread to log messages."""
    self._log_direct(message)

def _log_direct(self, message):
    """Direct logging implementation that must run from main thread."""
    if hasattr(self, 'textEdit') and self.textEdit:
        self.textEdit.append(message)
    print(f"[UrlPlayer] {message}")