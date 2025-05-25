import os
from typing import Dict
import json
import yaml
from pathlib import Path
import importlib.util
from PyQt6 import uic
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                            QVBoxLayout, QTabWidget, QScrollArea,
                            QLabel, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, QCoreApplication
from base_module import BaseModule, THEMES, PROJECT_ROOT
import traceback
import sys
import argparse
import logging

# Configurar el atributo antes de crear QApplication
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

# Otros atributos recomendados para WebEngine
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL, True)
#QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)

# Crear la aplicación
app = QApplication(sys.argv)



def load_config_file(file_path):
    """Carga un archivo de configuración en formato JSON o YAML."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"ERROR: Archivo de configuración no encontrado: {file_path}")
        
    file_extension = file_path.suffix.lower()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if file_extension == '.json':
                import json
                return json.loads(content)
            elif file_extension in ['.yml', '.yaml']:
                import yaml
                return yaml.safe_load(content)
            else:
                # Intentar determinar formato basado en contenido
                try:
                    import json
                    return json.loads(content)
                except json.JSONDecodeError:
                    try:
                        import yaml
                        return yaml.safe_load(content)
                    except yaml.YAMLError:
                        raise ValueError(f"No se pudo determinar el formato del archivo: {file_path}")
    except Exception as e:
        raise Exception(f"Error loading config: {str(e)}")


def save_config_file(file_path, data):
    """Guarda un archivo de configuración en formato JSON o YAML."""
    file_extension = Path(file_path).suffix.lower()
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            if file_extension == '.json':
                import json
                json.dump(data, f, indent=2)
            elif file_extension in ['.yml', '.yaml']:
                import yaml
                yaml.dump(data, f, sort_keys=False, default_flow_style=False, indent=2, allow_unicode=True)
            else:
                # Por defecto usar JSON
                import json
                json.dump(data, f, indent=2)
    except Exception as e:
        raise Exception(f"Error saving config: {str(e)}")


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

# Add this to main.py, before the ColoredFormatter class
COLORS = {
    'DEBUG': '\033[94m',  # Blue
    'INFO': '\033[92m',   # Green
    'WARNING': '\033[93m', # Yellow
    'ERROR': '\033[91m',   # Red
    'CRITICAL': '\033[91m\033[1m', # Red Bold
    'RESET': '\033[0m'     # Reset to default
}


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

log_file = PROJECT_ROOT / ".content" / "logs" / "multi_module_manager.log"

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler()
    ]
)

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
        
        # Cargar la configuración, NUNCA crear si no existe
        try:
            self.config = load_config_file(config_path)
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            raise  # Re-lanzar para que main() pueda manejarlo
        except Exception as e:
            print(f"ERROR al cargar la configuración: {e}")
            raise  # Re-lanzar para que main() pueda manejarlo


        # Load initial theme from config
        try:
            config = load_config_file(config_path)
        
            #self.available_themes = config.get('temas', ['Tokyo Night', 'Solarized Dark', 'Monokai'])
            #self.current_theme = config.get('tema_seleccionado', 'Tokyo Night')
            


            # Cargar el sistema de temas centralizado
            try:
                from themes.themes import THEMES, init_theme_system
                self.available_themes = list(THEMES.keys())
                
                # Obtener tema seleccionado de la configuración
                self.current_theme = self.config.get('tema_seleccionado', 'Tokyo Night')
                if self.current_theme not in self.available_themes:
                    self.current_theme = self.available_themes[0]  # Usar el primer tema si no es válido
                    
            except ImportError:
                # Fallback a los temas definidos en base_module
                from base_module import THEMES
                self.available_themes = list(THEMES.keys())
                self.current_theme = self.config.get('tema_seleccionado', 'Tokyo Night')


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
            #self.available_themes = ['Tokyo Night', 'Solarized Dark', 'Monokai']
            #self.current_theme = 'Tokyo Night'
            logging_level = logging.INFO
            config = {}
            print(f"Error al cargar la configuración: {e}")
        
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
        console_handler.setFormatter(ColoredFormatter('%(asctime)s - %(name)s [%(levelname)s] - %(message)s'))        
        
        # Establecemos path para el log_file
        log_file = PROJECT_ROOT / ".content" / "logs" / "multi_module_manager.log"
        
        file_handler = logging.FileHandler(log_file)
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
                
                # SOLUCIÓN SIMPLE: Hacer el QTabWidget existente arrastrables
                if hasattr(self, 'tab_widget'):
                    # Hacer las pestañas movibles
                    self.tab_widget.setMovable(True)
                    self.tab_widget.setTabsClosable(False)
                    
                    # Conectar señal de movimiento nativa de Qt
                    self.tab_widget.tabBar().tabMoved.connect(self.on_tab_moved)
                    
                    print("QTabWidget configurado como arrastrables")
                else:
                    print("No se encontró tab_widget, usando fallback")
                    self._fallback_init_ui()
                    return
                
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

        self.add_simple_animations()

    def on_tab_moved(self, from_index, to_index):
        """Manejar el movimiento de tabs y actualizar configuración"""
        try:
            # Cargar configuración actual
            config = load_config_file(self.config_path)
            
            if 'modules' in config and len(config['modules']) > max(from_index, to_index):
                # Mover el módulo en la configuración
                modules = config['modules']
                moved_module = modules.pop(from_index)
                modules.insert(to_index, moved_module)
                
                # Guardar configuración actualizada
                save_config_file(self.config_path, config)
                
                print(f"Tab moved from {from_index} to {to_index} - Configuration updated")
                
        except Exception as e:
            print(f"Error updating configuration after tab move: {e}")



    def _fallback_init_ui(self):
        """Método de respaldo para crear la UI manualmente si el archivo UI falla"""
        print("Usando método fallback para crear UI principal")
        self.setWindowTitle('Multi-Module Manager')
        self.setMinimumSize(1200, 800)

        # Widget principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Crear el widget de pestañas NORMAL
        self.tab_widget = QTabWidget()
        
        # Hacer las pestañas movibles
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabsClosable(False)
        
        # Conectar señal de movimiento
        self.tab_widget.tabBar().tabMoved.connect(self.on_tab_moved)
        
        layout.addWidget(self.tab_widget)

    def add_simple_animations(self):
        """Añade animaciones simples al tab widget existente"""
        if not hasattr(self, 'tab_widget'):
            return
            
        try:
            # Animación simple al cambiar de pestaña
            original_setCurrentIndex = self.tab_widget.setCurrentIndex
            
            def animated_tab_change(index):
                # Cambio normal sin animaciones complejas por ahora
                original_setCurrentIndex(index)
                
                # Efecto visual simple
                current_widget = self.tab_widget.currentWidget()
                if current_widget:
                    # Aplicar efecto de opacidad muy sutil
                    current_widget.setStyleSheet(
                        current_widget.styleSheet() + 
                        "QWidget { background-color: rgba(0,0,0,0); }"
                    )
            
            self.tab_widget.setCurrentIndex = animated_tab_change
            
            print("Animaciones simples aplicadas al tab widget")
        except Exception as e:
            print(f"Error aplicando animaciones: {e}")


    def load_modules(self):
        """Loads modules from configuration."""
        try:
            config = load_config_file(self.config_path)
                
            # Get global settings that modules might need
            global_config = config.get('global_theme_config', {})
            
            for module_config in config['modules']:
                parent_dir = Path(__file__).parent
                relative_path = Path(module_config['path'])
                module_path = str(parent_dir / relative_path)
                module_name = module_config.get('name', Path(module_path).stem)
                module_args = module_config.get('args', {})
                
                # Add ALL global config to module_args
                for key, value in global_config.items():
                    # Only add if not already defined in module-specific args
                    if key not in module_args:
                        module_args[key] = value
                
                # Also pass complete lastfm section if available
                if 'lastfm' in config and 'lastfm' not in module_args:
                    module_args['lastfm'] = config.get('lastfm', {})
                
                # Add global_theme_config itself for modules that need access to all global settings
                module_args['global_theme_config'] = global_config
                
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


    def apply_theme(self, theme_name=None):
        """
        Aplica el tema especificado a toda la aplicación.
        
        Args:
            theme_name (str, optional): Nombre del tema a aplicar.
                                    Si es None, usa self.current_theme.
        """
        # Actualizar el tema actual si se proporciona uno nuevo
        if theme_name is not None:
            self.current_theme = theme_name
        
        # Asegurar que el tema existe, usar el primero por defecto si no
        if self.current_theme not in self.available_themes:
            self.current_theme = self.available_themes[0]
        
        # Intentar usar el sistema centralizado de temas
        try:
            from themes.themes import init_theme_system
            
            # Establecer el objectName de la ventana principal para poder aplicar estilos específicos
            if not self.objectName():
                self.setObjectName("main_window")
            
            # Aplicar el tema a nivel de aplicación
            init_theme_system(QApplication.instance(), self.current_theme)
            
            # No es necesario hacer más, ya que init_theme_system aplica el tema a toda la aplicación
            return
        except (ImportError, AttributeError) as e:
            print(f"No se pudo cargar el sistema centralizado de temas: {e}")
        
        # Fallback: Usar el método antiguo
        theme = THEMES.get(self.current_theme, THEMES['Tokyo Night'])
        
        # Aplicar estilos básicos
        self.setStyleSheet(f"""
            /* Estilos base */
            QWidget {{
                background-color: {theme['bg']};
                color: {theme['fg']};
                font-family: "Segoe UI", "Noto Fonts Emoji", sans-serif;
                font-size: 10pt;
            }}

            /* Quitar bordes de todos los frames */
            QFrame, QGroupBox {{
                border: none;
                border-radius: 4px;
            }}

            /* Campos de entrada de texto */
            QLineEdit, QTextEdit {{
                border: 1px solid;
                border-radius: 4px;
                padding: 8px;
                background-color: {theme['bg']};
            }}

            /* Botones */
            QPushButton {{
                background-color: {theme['bg']};
                border: 2px;
                border-radius: 19px;
            }}
            
            QPushButton:hover {{
                background-color: {theme['button_hover']};
                margin: 1px;
                margin-top: 0px;
                margin-bottom: 2px;
            }}
            
            QPushButton:pressed {{
                background-color: {theme['selection']};
                border: none;
            }}

            /* Listas y árboles */
            QTreeWidget, QListWidget {{
                background-color: {theme['bg']};
                border: none;
                border-radius: 4px;
            }}

            /* Tabs */
            QTabWidget::pane {{
                border: none;
                background-color: {theme['secondary_bg']};
                border-radius: 4px;
            }}

            QTabBar::tab {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: none;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}

            QTabBar::tab:selected {{
                background-color: {theme['button_hover']};
                color: {theme['fg']};
            }}

            QTabBar::tab:hover:!selected {{
                background-color: {theme['secondary_bg']};
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
            try:
                config = load_config_file(self.config_path)
            
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
                
                # Save configuration
                save_config_file(self.config_path, config)
                
            except Exception as e:
                print(f"Error al aplicar cambio de tema: {e}")
                traceback.print_exc()


    def setup_info_widget(self):
        """Configura los widgets de información dentro de los ScrollAreas."""
        try:
            # Verificar que info_scroll existe
            if not hasattr(self, 'info_scroll') or not self.info_scroll:
                print("Error: info_scroll no existe")
                self._fallback_setup_info_widget()
                return
                
            # 1. Cargar el panel de información principal (enlaces, wikipedia, lastfm, etc.)
            info_ui_path = Path(PROJECT_ROOT, "ui", "music_fuzzy_info_panel.ui")
            if os.path.exists(info_ui_path):
                try:
                    self.info_widget = QWidget()
                    uic.loadUi(info_ui_path, self.info_widget)
                    
                    # Obtener referencias a los labels
                    self.links_label = self.info_widget.findChild(QLabel, "links_label")
                    self.wikipedia_artist_label = self.info_widget.findChild(QLabel, "wikipedia_artist_label")
                    self.lastfm_label = self.info_widget.findChild(QLabel, "lastfm_label")
                    self.wikipedia_album_label = self.info_widget.findChild(QLabel, "wikipedia_album_label")
                    
                    # Importante: Configurar el ancho mínimo para los labels
                    # Esto es crucial para que el contenido se expanda horizontalmente
                    if self.info_scroll and self.info_scroll.width() > 0:
                        scroll_width = self.info_scroll.width() - 30  # Restar un poco para scrollbar y margen
                    else:
                        scroll_width = 800  # Un valor razonable por defecto
                    
                    # Configurar el ancho mínimo para todos los labels
                    for label in [self.links_label, self.wikipedia_artist_label, 
                                self.lastfm_label, self.wikipedia_album_label]:
                        if label:
                            label.setMinimumWidth(scroll_width)
                    
                    # El ajuste crítico: Configurar el tamaño del widget
                    # Esto fuerza al QScrollArea a mostrar contenido con el ancho adecuado
                    self.info_widget.setMinimumWidth(scroll_width)
                    
                    # Establecer el widget en el ScrollArea
                    self.info_scroll.setWidget(self.info_widget)
                    
                    # IMPORTANTE: Eliminar cualquier restricción de scroll horizontal
                    self.info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                    
                    print("Panel de información cargado desde UI")
                except Exception as e:
                    print(f"Error al cargar el panel de información: {e}")
                    traceback.print_exc()
                    self._fallback_setup_info_widget()
                    return
            else:
                print(f"Archivo UI del panel de información no encontrado: {info_ui_path}")
                self._fallback_setup_info_widget()
                return
                
            # Resto de tu código actual...
            
            # IMPORTANTE: Añadir un evento de redimensionamiento para actualizar anchos
            # cuando la ventana cambie de tamaño
            self.info_scroll.resizeEvent = self._on_info_scroll_resize
            
            self.ui_components_loaded['info'] = True
            print("Widgets de información configurados correctamente")
        except Exception as e:
            print(f"Error general al configurar los widgets de información: {e}")
            traceback.print_exc()
            self._fallback_setup_info_widget()


    def _on_info_scroll_resize(self, event):
        """Actualiza el ancho mínimo de los labels cuando se redimensiona el scroll area"""
        if hasattr(self, 'info_widget') and self.info_widget:
            # Calcular el nuevo ancho óptimo
            scroll_width = event.size().width() - 30  # Restar para scrollbar y margen
            
            # Actualizar el ancho mínimo del widget contenedor
            self.info_widget.setMinimumWidth(scroll_width)
            
            # Actualizar el ancho mínimo de todos los labels
            for label in [self.links_label, self.wikipedia_artist_label, 
                        self.lastfm_label, self.wikipedia_album_label]:
                if label:
                    label.setMinimumWidth(scroll_width)
        
        # Llamar al evento original si está disponible
        original_resize = getattr(QScrollArea, "resizeEvent", None)
        if original_resize:
            original_resize(self.info_scroll, event)







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
                            print(f"El atributo '{method_to_call}' no es una función en el módulo '{tab_name}'")
                    else:
                        print(f"El módulo '{tab_name}' no tiene un método llamado '{method_to_call}'")
                return True
        
        print(f"No se encontró la pestaña '{tab_name}'")
        return False

def main():
    parser = argparse.ArgumentParser(description='Multi-Module Manager')
    parser.add_argument('config_path', help='Ruta al archivo de configuración (JSON o YAML)')
    parser.add_argument('--font', default='Inter', help='Fuente a usar en la interfaz')
    parser.add_argument('--font_size', default='12px', help='Tamaño de la Fuente a usar en la interfaz')
    parser.add_argument('--log', type=str,
                        choices=['true', 'false'],
                        default=None,
                        help='Habilitar logging detallado (true/false)')
    
    args = parser.parse_args()

    # Verificar explícitamente que el archivo de configuración existe
    config_path = Path(args.config_path)
    if not config_path.exists():
        print(f"ERROR: El archivo de configuración no existe: {config_path}")
        sys.exit(1)

    app = QApplication(sys.argv)
    
    try:
        manager = TabManager(args.config_path, font_family=args.font, font_size=args.font_size)
        manager.show()
        sys.exit(app.exec())
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR FATAL: {e}")
        traceback.print_exc()
        sys.exit(1)
    # Load configuration to potentially override logging setting
    try:
        config = load_config_file(args.config_path)
        
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
            console_handler.setFormatter(ColoredFormatter('%(asctime)s - %(name)s [%(levelname)s] - %(message)s'))            

            log_file = PROJECT_ROOT / ".content" / "logs" / "tab_manager.log"

            file_handler = logging.FileHandler(log_file)
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
            log_file = PROJECT_ROOT / ".content" / "logs" / "tab_manager.log"
            # Fallback al logging básico en caso de error
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(),  # Print to console
                    logging.FileHandler(log_file)  # Log to file
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
