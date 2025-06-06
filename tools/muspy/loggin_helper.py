# Añade esto en un nuevo archivo llamado terminal_logger.py
import logging
import sys

# Códigos ANSI para colores en terminal
COLORS = {
    'DEBUG': '\033[90m',     # Gris
    'INFO': '\033[94m',      # Azul
    'WARNING': '\033[93m',   # Amarillo
    'ERROR': '\033[91m',     # Rojo
    'CRITICAL': '\033[31m',  # Rojo intenso
    'UI': '\033[95m',        # Morado
    'RESET': '\033[0m'       # Reset color
}

class ColoredFormatter(logging.Formatter):
    """Formateador que añade colores a los logs en terminal"""
    
    def format(self, record):
        levelname = record.levelname
        # Obtener el color o usar RESET si no está definido
        color = COLORS.get(levelname, COLORS['RESET'])
        # Formatear con color
        record.levelname = f"{color}{levelname}{COLORS['RESET']}"
        return super().format(record)

def setup_module_logger(module_name, log_level='INFO', log_types=None):
    """
    Configura un logger para un módulo específico con colores en terminal
    
    Args:
        module_name (str): Nombre del módulo
        log_level (str): Nivel de log ('DEBUG', 'INFO', etc.)
        log_types (list): Tipos de log habilitados
    
    Returns:
        logging.Logger: Logger configurado
    """
    # Registrar nivel UI si no existe
    if not hasattr(logging, 'UI'):
        logging.addLevelName(15, 'UI')
        
        def ui_log(self, message, *args, **kwargs):
            self.log(15, message, *args, **kwargs)
        
        logging.Logger.ui = ui_log
    
    # Crear logger
    logger = logging.getLogger(f"{module_name}")
    
    # Evitar duplicados
    if logger.handlers:
        return logger
    
    # Configurar nivel
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
        'UI': 15
    }
    logger.setLevel(level_map.get(log_level, logging.INFO))
    
    # Crear handler para terminal
    handler = logging.StreamHandler(sys.stdout)
    
    # Crear formateador con colores
    formatter = ColoredFormatter('%(asctime)s - %(name)s [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    
    # Añadir handler al logger
    logger.addHandler(handler)
    
    # Deshabilitar propagación para evitar duplicados
    logger.propagate = False
    
    # Filtrar tipos de log si se especifican
    if log_types:
        class LogTypeFilter(logging.Filter):
            def filter(self, record):
                return record.levelname in log_types
        
        log_filter = LogTypeFilter()
        handler.addFilter(log_filter)
    
    return logger