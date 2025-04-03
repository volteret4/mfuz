import os
from typing import Dict
import json
from pathlib import Path
import importlib.util
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                            QVBoxLayout, QTabWidget)
from PyQt6.QtCore import QThread
from base_module import BaseModule, THEMES, PROJECT_ROOT
import traceback
import sys
import argparse
import logging

# class PyQtFilter(logging.Filter):
#     def filter(self, record):
#         # Filtrar mensajes de PyQt y uic
#         if record.name.startswith('PyQt6') or 'uic' in record.name.lower():
#             return False
#         return True

class ConditionalPyQtFilter(logging.Filter):
    def __init__(self, show_ui_logs=False):
        super().__init__()
        self.show_ui_logs = show_ui_logs
    
    def filter(self, record):
        # Si UI está habilitado, mostrar todos los logs
        if self.show_ui_logs:
            return True
        
        # Si UI no está habilitado, filtrar logs de PyQt y uic
        if record.name.startswith('PyQt6') or 'uic' in record.name.lower():
            return False
        return True




class ColoredFormatter(logging.Formatter):
    """Formateador que añade colores a los logs en terminal"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_module = None
    
    def format(self, record):
        levelname = record.levelname
        # Obtener el color o usar RESET si no está definido
        color = COLORS.get(levelname, COLORS['RESET'])
        # Formatear con color
        record.levelname = f"{color}{levelname}{COLORS['RESET']}"
        
        # Añadir separador si cambiamos de módulo
        result = super().format(record)
        current_module = record.name.split('.')[0]
        
        if self.last_module and self.last_module != current_module:
            result = f"\n{result}"
        
        self.last_module = current_module
        return result


def exception_hook(exc_type, exc_value, exc_traceback):
    """Global exception handler to log unhandled exceptions"""
    error_msg = "Uncaught exception:\n" + "".join(
        traceback.format_exception(exc_type, exc_value, exc_traceback)
    )
    logging.critical(error_msg)
    print(error_msg)  # Also print to console
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

# Ensure log directory exists
log_dir = os.path.expanduser('~/.config/your_app_name/logs')
os.makedirs(log_dir, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'application_debug.log'), mode='w'),
        logging.StreamHandler()
    ]
)

# Set the global exception hook
sys.excepthook = exception_hook

# Set the global exception hook
sys.excepthook = exception_hook

# Tema Tokyo Night (puedes personalizarlo o cargar desde config)
THEME = {
    'bg': '#1a1b26',
    'fg': '#a9b1d6',
    'accent': '#7aa2f7',
    'secondary_bg': '#24283b',
    'border': '#414868',
    'selection': '#364A82',
    'button_hover': '#3d59a1'
}

class TabManager(QMainWindow):
    def __init__(self, config_path: str, font_family="Inter", font_size="14px"):
        super().__init__()
        self.font_family = font_family
        self.font_size = font_size
        self.config_path = config_path
        self.tabs: Dict[str, QWidget] = {}
        
        # Load initial theme from config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.available_themes = config.get('temas', ['Tokyo Night', 'Solarized Dark', 'Monokai'])
        self.current_theme = config.get('tema_seleccionado', 'Tokyo Night')
        
        try:
            
            # Convertir el nivel de string a constante de logging
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL,
                'UI': 15  # Nivel personalizado
            }
            logging_level_str = config.get('logging_level', 'INFO')
            logging_level = level_map.get(logging_level_str, logging.INFO)
        except Exception as e:
            # En caso de error, usar un valor predeterminado
            logging_level = logging.INFO
            print(f"Error al leer el nivel de logging desde la configuración: {e}")


        # Obtener los tipos de log habilitados
        log_types = config.get('log_types', ['ERROR', 'INFO', 'WARNING'])
        show_ui_logs = 'UI' in log_types

        # Registrar nivel UI personalizado si no existe
        if not hasattr(logging, 'UI'):
            logging.addLevelName(15, 'UI')  # 15 es un valor entre DEBUG (10) e INFO (20)
            
            def ui_log(self, message, *args, **kwargs):
                self.log(15, message, *args, **kwargs)
            
            logging.Logger.ui = ui_log

        # Configurar los handlers
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredFormatter)

        file_handler = logging.FileHandler('multi_module_manager.log')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

        # Configurar root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging_level)
        root_logger.handlers = []  # Eliminar handlers existentes
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        # Aplicar filtro condicional
        pyqt_filter = ConditionalPyQtFilter(show_ui_logs)
        root_logger.addFilter(pyqt_filter)



        self.init_ui()
        self.load_modules()

    def init_ui(self):
        """Inicializa la interfaz principal."""
        # Cargar la UI desde el archivo
        ui_file_path = os.path.join(PROJECT_ROOT, "ui", "tab_manager.ui")
        if os.path.exists(ui_file_path):
            try:
                # Cargar el archivo UI
                from PyQt6 import uic
                uic.loadUi(ui_file_path, self)
                
                # Asegurarse de que tenemos referencia al widget de pestañas
                if not hasattr(self, 'tab_widget'):
                    # Si el nombre no coincide exactamente, intenta buscarlo
                    tab_widgets = self.findChildren(QTabWidget)
                    if tab_widgets:
                        self.tab_widget = tab_widgets[0]
                    else:
                        raise AttributeError("No se pudo encontrar QTabWidget en el archivo UI")
                
                print(f"UI cargada desde {ui_file_path}")
            except Exception as e:
                print(f"Error cargando UI desde archivo: {e}")
                traceback.print_exc()
                self._fallback_init_ui()
        else:
            print(f"Archivo UI no encontrado: {ui_file_path}, usando creación manual")
            self._fallback_init_ui()

        # Aplicar el tema
        self.apply_theme(self.font_size)

    def _fallback_init_ui(self):
        """Método de respaldo para crear la UI manualmente si el archivo UI falla"""
        print("Usando método fallback para crear UI principal")
        self.setWindowTitle('Multi-Module Manager')
        self.setMinimumSize(1200, 800)

        # Widget principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Crear el widget de pestañas
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)


    def load_modules(self):
        """Loads modules from configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            for module_config in config['modules']:
                parent_dir = Path(__file__).parent
                relative_path = Path(module_config['path'])
                module_path = str(parent_dir / relative_path)
                module_name = module_config.get('name', Path(module_path).stem)
                module_args = module_config.get('args', {})
                
                try:
                    # Dynamically load the module
                    print(f"Intentando cargar módulo desde {module_path}")
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Find the main class of the module
                        main_class = None
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and issubclass(attr, BaseModule) and attr != BaseModule:
                                main_class = attr
                                break
                                
                        if main_class:
                            try:
                                # Instantiate the module
                                module_instance = main_class(**module_args)
                            
                                # Pass reference to TabManager
                                if hasattr(module_instance, 'set_tab_manager'):
                                    module_instance.set_tab_manager(self)                           

                                # If it's the config editor, connect the signals
                                if module_name == "Config Editor":
                                    if hasattr(module_instance, 'config_updated'):
                                        module_instance.config_updated.connect(self.reload_application)
                                    
                                    # Connect the module theme changed signal
                                    if hasattr(module_instance, 'module_theme_changed'):
                                        module_instance.module_theme_changed.connect(self.change_module_theme)
                                
                                # Add to tab manager
                                self.tab_widget.addTab(module_instance, module_name)
                                self.tabs[module_name] = module_instance
                                print(f"Módulo {module_name} cargado correctamente")
                            except Exception as e:
                                print(f"Error instanciando el módulo {module_name}: {e}")
                                traceback.print_exc()
                        else:
                            print(f"No se encontró una clase válida en el módulo {module_name}")
                            
                except Exception as e:
                    print(f"Error cargando módulo {module_name}: {e}")
                    traceback.print_exc()
                    
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            traceback.print_exc()

    def change_module_theme(self, module_name, new_theme):
        """
        Change theme for a specific module or global theme
        
        Args:
            module_name (str): Name of the module to change theme for, or 'global'
            new_theme (str): New theme name
        """
        if module_name == 'global':
            # If global theme, change all module themes
            for module in self.tabs.values():
                module.apply_theme(new_theme)
        elif module_name in self.tabs:
            # Change theme for specific module
            self.tabs[module_name].apply_theme(new_theme)


    def apply_theme(self, font_size="14px"):
        """Applies theme to the entire application."""
        theme = THEMES.get(self.current_theme, THEMES['Tokyo Night'])
        
        self.setStyleSheet(f"""
            /* Base Styles */
            QWidget {{
                background-color: {theme['bg']};
                color: {theme['fg']};
                font-family: {self.font_family};
                font-size: {self.font_size};
                border: none
            }}
            
            /* Main Window */
            QMainWindow {{
                background-color: {theme['bg']};
            }}
            
            
            /* Tabs */
            QTabWidget::pane {{
                border: 1px solid {theme['border']};
                background-color: {theme['bg']};
                border-radius: 3px;
            }}
            

            QTabBar::tab {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                padding: 5px 10px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {theme['bg']};
                border-bottom-color: {theme['bg']};
                color: {theme['fg']};
            }}
            
            QTabBar::tab:hover {{
                background-color: {theme['button_hover']};
            }}
            
            /* Forms and Inputs */
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                
                padding: 5px;
                border-radius: 3px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme['border']};
            }}

            QComboBox {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 0.5px solid {theme['border']};
                border-radius: 3px;
                padding: 5px;
                min-height: 25px;
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left: 1px solid {theme['border']};
            }}
            
            QComboBox::down-arrow {{
                border: none;
                background-color: {theme['accent']};
                width: 10px;
                height: 10px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                selection-background-color: {theme['selection']};
            }}
            
            /* Buttons */
            QPushButton {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                padding: 5px 10px;
                border-radius: 3px;
                min-height: 15px;
            }}
            
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
            
            QPushButton:pressed {{
                background-color: {theme['selection']};
            }}
            
            QPushButton:disabled {{
                background-color: {theme['secondary_bg']};
                color: rgba({int(theme['fg'].lstrip('#')[0:2], 16)}, 
                            {int(theme['fg'].lstrip('#')[2:4], 16)}, 
                            {int(theme['fg'].lstrip('#')[4:6], 16)}, 0.5);
            }}
            
            /* Lists and Tables */
            QListWidget, QTreeWidget, QTableWidget, QTableView, QTreeView, QListView {{
                background-color: {theme['secondary_bg']};
                alternate-background-color: {theme['bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                
                padding: 5px;
            }}
            
            QListWidget::item, QTreeWidget::item, QTableWidget::item {{
                padding: 5px;
            }}
            
            QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected,
            QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {{
                background-color: {theme['selection']};
                color: {theme['fg']};
            }}
            
            QHeaderView::section {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                padding: 5px;
                border: 1px solid {theme['border']};
            }}
            
            /* Scroll Bars */
            QScrollBar:vertical {{
                background-color: {theme['bg']};
                width: 10px;
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {theme['border']};
                min-height: 20px;
                border-radius: 7px;
                margin: 2px;
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar:horizontal {{
                background-color: {theme['bg']};
                height: 14px;
                margin: 0px;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {theme['border']};
                min-width: 10px;
                border-radius: 7px;
                margin: 2px;
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            
            /* Additional Widgets */
            QCheckBox, QRadioButton {{
                color: {theme['fg']};
                spacing: 5px;
            }}
            
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {theme['border']};
                background-color: {theme['secondary_bg']};
            }}
            
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                background-color: {theme['accent']};
            }}
            
            QGroupBox {{
                border: 1px solid {theme['border']};
                border-radius: 3px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }}
            
            QProgressBar {{
                border: 1px solid {theme['border']};
                border-radius: 3px;
                background-color: {theme['secondary_bg']};
                text-align: center;
                color: {theme['fg']};
            }}
            
            QProgressBar::chunk {{
                background-color: {theme['accent']};
                width: 10px;
            }}
            
            QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                border-radius: 3px;
                padding: 5px;
            }}
            
            QSpinBox::up-button, QDoubleSpinBox::up-button, 
            QDateEdit::up-button, QTimeEdit::up-button, QDateTimeEdit::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                border-left: 1px solid {theme['border']};
                width: 16px;
            }}
            
            QSpinBox::down-button, QDoubleSpinBox::down-button,
            QDateEdit::down-button, QTimeEdit::down-button, QDateTimeEdit::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                border-left: 1px solid {theme['border']};
                width: 16px;
            }}
            
            /* Dialogs */
            QDialog {{
                background-color: {theme['bg']};
            }}
            
            QFrame {{
                border: 1px solid {theme['border']};
                border-radius: 3px;
            }}
            
            QSplitter::handle {{
                background-color: {theme['border']};
            }}
            
            QToolTip {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                border-radius: 3px;
            }}
            
            QMenu {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
            }}
            
            QMenu::item {{
                padding: 5px 20px 5px 20px;
            }}
            
            QMenu::item:selected {{
                background-color: {theme['selection']};
            }}
            
            QMenuBar {{
                background-color: {theme['bg']};
                color: {theme['fg']};
            }}
            
            QMenuBar::item {{
                spacing: 5px;
                padding: 5px 10px;
                background: transparent;
            }}
            
            QMenuBar::item:selected {{
                background-color: {theme['selection']};
            }}
        """)


    def reload_application(self):
        """Recarga todos los módulos después de un cambio en la configuración"""
        # Guardar el índice de la pestaña actual
        current_index = self.tab_widget.currentIndex()
        
        # Eliminar todas las pestañas existentes
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)
        
        # Limpiar el diccionario de pestañas
        self.tabs.clear()
        
        # Recargar los módulos
        self.load_modules()
        
        # Restaurar el índice de la pestaña si es posible
        if current_index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(current_index)


    def cleanup_threads():
        """Ensure all threads are properly stopped before application exit"""
        for thread in QThread.allThreads():
            if thread != QThread.currentThread():
                try:
                    # If it's our worker, call stop method
                    if hasattr(thread, 'stop'):
                        thread.stop()
                    # Wait for thread to finish
                    thread.wait(5000)  # 5 second timeout
                except Exception as e:
                    print(f"Error cleaning up thread: {e}")


    def change_theme(self, new_theme):
        """Cambia el tema de toda la aplicación."""
        if new_theme in self.available_themes:
            self.current_theme = new_theme
            
            # Reapply theme to TabManager
            self.apply_theme()
            
            # Check global theme configuration
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Determine if individual themes are enabled
            enable_individual_themes = config.get('global_theme_config', {}).get('enable_individual_themes', True)
            
            # Reapply theme to modules
            for module_name, module in self.tabs.items():
                # If individual themes are disabled, or the module doesn't have a specific theme set
                module_config = next((m for m in config['modules'] if m['name'] == module_name), None)
                
                if not enable_individual_themes or (module_config and 'tema_seleccionado' not in module_config.get('args', {})):
                    module.apply_theme(new_theme)
                else:
                    # If individual themes are enabled and a specific theme is set, keep that theme
                    module.apply_theme(module_config['args'].get('tema_seleccionado', new_theme))
            
            # Update config file
            config['tema_seleccionado'] = new_theme
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)


    def switch_to_tab(self, tab_name, method_to_call=None, *args, **kwargs):
        """
        Cambia a la pestaña especificada y opcionalmente llama a un método en ese módulo.
        
        Args:
            tab_name (str): Nombre de la pestaña a la que cambiar
            method_to_call (str, optional): Nombre del método a llamar en el módulo destino
            *args, **kwargs: Argumentos a pasar al método
        
        Returns:
            bool: True si se pudo cambiar y llamar al método, False en caso contrario
        """
        # Buscar el índice de la pestaña por nombre
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == tab_name:
                # Cambiar a esa pestaña
                self.tab_widget.setCurrentIndex(i)
                
                # Si hay un método que llamar
                if method_to_call and tab_name in self.tabs:
                    tab_module = self.tabs[tab_name]
                    if hasattr(tab_module, method_to_call):
                        method = getattr(tab_module, method_to_call)
                        if callable(method):
                            method(*args, **kwargs)
                            return True
                        else:
                            print(f"    El atributo '{method_to_call}' no es una función en el módulo '{tab_name}'")
                    else:
                        print(f"    El módulo '{tab_name}' no tiene un método llamado '{method_to_call}'")
                return True
        
        print(f"   No se encontró la pestaña '{tab_name}'")
        return False





def main():


    parser = argparse.ArgumentParser(description='Multi-Module Manager')
    parser.add_argument('config_path', help='Ruta al archivo de configuración JSON')
    parser.add_argument('--font', default='Inter', help='Fuente a usar en la interfaz')
    parser.add_argument('--font_size', default='12px', help='Tamaño de la Fuente a usar en la interfaz')
    parser.add_argument('--log', type=str,
                        choices=['true', 'false'],
                        default=None,
                        help='Habilitar logging detallado (true/false)')
    
    args = parser.parse_args()

    # Load configuration to potentially override logging setting
    try:
        with open(args.config_path, 'r') as f:
            config = json.load(f)
        
        # Determine logging state with multiple configuration options
        if args.log is not None:
            # CLI argument takes precedence
            log_enabled = args.log.lower() == 'true'
        else:
            # Check for different logging configuration formats
            logging_options = config.get('logging_options', ['true', 'false'])
            logging_state = config.get('logging_state', 'false')
            log_enabled = logging_state.lower() == 'true'

    except Exception as e:
        print(f"Error reading config: {e}")
        log_enabled = False

    # Configure logging if logging is enabled
    if log_enabled:
        # Importar nuestro formateador personalizado
        try:
            from terminal_logger import ColoredFormatter, COLORS
            
            # Obtener configuración detallada de logging
            logging_level_str = config.get('logging_level', 'INFO')
            log_types = config.get('log_types', ['ERROR', 'INFO', 'WARNING'])
            
            # Convertir nivel de string a constante de logging
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL,
                'UI': 15  # Nivel personalizado
            }
            logging_level = level_map.get(logging_level_str, logging.INFO)
            
            # Registrar nivel UI si no existe
            if not hasattr(logging, 'UI'):
                logging.addLevelName(15, 'UI')
                
                def ui_log(self, message, *args, **kwargs):
                    self.log(15, message, *args, **kwargs)
                
                logging.Logger.ui = ui_log
            
            # Configurar logging básico con formato colorizado
            ColoredFormatter = ColoredFormatter('%(asctime)s - %(name)s [%(levelname)s] - %(message)s')
            
            # Handlers
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(ColoredFormatter)
            
            file_handler = logging.FileHandler('multi_module_manager.log')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            
            # Configurar root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging_level)
            root_logger.handlers = []  # Eliminar handlers existentes
            root_logger.addHandler(console_handler)
            root_logger.addHandler(file_handler)
            
            # Clase para redirigir stdout/stderr con colores según el módulo
            class ColoredLoggerWriter:
                def __init__(self, logger, level, module_name=None):
                    self.logger = logger
                    self.level = level
                    self.module_name = module_name or 'STDOUT' if level == logging.INFO else 'STDERR'
                    self.buffer = []
                
                def write(self, message):
                    if message and message.strip():
                        # Determinar el tipo de log basado en el nivel
                        level_name = logging.getLevelName(self.level)
                        color = COLORS.get(level_name, COLORS['RESET'])
                        
                        # Log con formato específico para stdout/stderr redirigido
                        self.logger.log(self.level, f"[{self.module_name}] {message.rstrip()}")
                
                def flush(self):
                    pass
            
            # Redirigir stdout y stderr 
            sys.stdout = ColoredLoggerWriter(logging.getLogger('STDOUT'), logging.INFO)
            sys.stderr = ColoredLoggerWriter(logging.getLogger('STDERR'), logging.ERROR)
            
            logging.info(f"Sistema de logging inicializado con nivel {logging_level_str}")
            
        except Exception as e:
            # Fallback al logging básico en caso de error
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(),  # Print to console
                    logging.FileHandler('multi_module_manager.log')  # Log to file
                ]
            )
            
            # Clase simple para redirigir stdout/stderr
            class LoggerWriter:
                def __init__(self, logger, level):
                    self.logger = logger
                    self.level = level
                    self.buffer = []
                
                def write(self, message):
                    if message.strip():
                        self.logger.log(self.level, message.rstrip())
                
                def flush(self):
                    pass
            
            sys.stdout = LoggerWriter(logging.getLogger('STDOUT'), logging.INFO)
            sys.stderr = LoggerWriter(logging.getLogger('STDERR'), logging.ERROR)
            
            logging.error(f"Error configurando sistema de logging avanzado: {e}. Usando configuración básica.")
    
    app = QApplication(sys.argv)
    manager = TabManager(args.config_path, font_family=args.font, font_size=args.font_size)
    manager.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
