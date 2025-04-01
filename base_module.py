from PyQt6.QtWidgets import QWidget, QTableWidget, QTableView, QProgressBar, QFrame, QGroupBox
from typing import Optional
from pathlib import Path
import os
import traceback

# Default themes
THEMES = {
    "Tokyo Night": {  # Tokyo Night
        'bg': '#1a1b26',
        'fg': '#a9b1d6',
        'accent': '#7aa2f7',
        'secondary_bg': '#24283b',
        'border': '#414868',
        'selection': '#364A82',
        'button_hover': '#3d59a1'
    },
    "Solarized Dark": {  # Solarized Dark
        'bg': '#002b36',
        'fg': '#839496',
        'accent': '#268bd2',
        'secondary_bg': '#073642',
        'border': '#586e75',
        'selection': '#2d4b54',
        'button_hover': '#4b6e83'
    },
    "Monokai": {  # Monokai
        'bg': '#272822',
        'fg': '#f8f8f2',
        'accent': '#a6e22e',
        'secondary_bg': '#3e3d32',
        'border': '#75715e',
        'selection': '#49483e',
        'button_hover': '#5c6370'
    },
    "Catppuccin": {  # Catppuccin Mocha
        'bg': '#1e1e2e',
        'fg': '#cdd6f4',
        'accent': '#89b4fa',
        'secondary_bg': '#313244',
        'border': '#6c7086',
        'selection': '#45475a',
        'button_hover': '#585b70'
    },
    "Dracula": {  # Dracula
        'bg': '#282a36',
        'fg': '#f8f8f2',
        'accent': '#bd93f9',
        'secondary_bg': '#44475a',
        'border': '#6272a4',
        'selection': '#44475a',
        'button_hover': '#50fa7b'
    },
    "Nord": {  # Nord
        'bg': '#2e3440',
        'fg': '#eceff4',
        'accent': '#88c0d0',
        'secondary_bg': '#3b4252',
        'border': '#4c566a',
        'selection': '#434c5e',
        'button_hover': '#5e81ac'
    },
    "Synthwave": {  # Synthwave
        'bg': '#262335',
        'fg': '#f8f8f2',
        'accent': '#ff8adc',
        'secondary_bg': '#3b315e',
        'border': '#7d77a9',
        'selection': '#4b3c83',
        'button_hover': '#fe5f86'
    }
}
class BaseModule(QWidget):
    """Clase base para todos los módulos."""
    def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
        super().__init__(parent)
        self.tab_manager = None
        self._module_registry = {}
        self.current_theme = theme
        self.themes = THEMES  # Assuming THEMES is imported or defined
        
        # Configuración de logging
        self.module_name = self.__class__.__name__
        
        # Obtener configuración de logging
        self.log_config = kwargs.get('logging', {})
        self.log_level = self.log_config.get('log_level', 'INFO')
        self.enable_logging = self.log_config.get('debug_enabled', False)
        self.log_types = self.log_config.get('log_types', ['ERROR', 'INFO'])
        
        # Configurar logger si está habilitado
        if self.enable_logging:
            try:
                from terminal_logger import setup_module_logger
                self.logger = setup_module_logger(
                    module_name=self.module_name,
                    log_level=self.log_level,
                    log_types=self.log_types
                )
            except ImportError:
                import logging
                self.logger = logging.getLogger(self.module_name)
        
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        """
        Método que deben implementar las clases hijas.
        Si se está usando con archivos UI, cada clase hija debe:
        1. Intentar cargar su archivo UI correspondiente
        2. Tener un método fallback para crear la UI manualmente
        """
        raise NotImplementedError("Subclasses must implement init_ui method")

    def load_ui_file(self, ui_file_name, required_widgets=None):
        """
        Método auxiliar para cargar un archivo UI con manejo de errores
        
        Args:
            ui_file_name (str): Nombre del archivo UI (sin ruta)
            required_widgets (list, optional): Lista de nombres de widgets requeridos
            
        Returns:
            bool: True si se cargó correctamente, False si hubo error
        """
        try:
            ui_file_path = os.path.join(PROJECT_ROOT, "ui", ui_file_name)
            if not os.path.exists(ui_file_path):
                print(f"Archivo UI no encontrado: {ui_file_path}")
                return False
                
            from PyQt6 import uic
            uic.loadUi(ui_file_path, self)
            
            # Verificar widgets requeridos si se especifican
            if required_widgets:
                missing_widgets = []
                for widget_name in required_widgets:
                    if not hasattr(self, widget_name) or getattr(self, widget_name) is None:
                        widget = self.findChild(QWidget, widget_name)
                        if widget:
                            setattr(self, widget_name, widget)
                        else:
                            missing_widgets.append(widget_name)
                
                if missing_widgets:
                    print(f"Widgets requeridos no encontrados: {', '.join(missing_widgets)}")
                    return False
            
            print(f"UI cargada desde {ui_file_path}")
            return True
        except Exception as e:
            print(f"Error cargando UI desde archivo: {e}")
            traceback.print_exc()
            return False


    def apply_theme(self, theme_name: Optional[str] = None):
        """
        Universal theme application method.
        
        Args:
            theme_name (str, optional): Name of the theme to apply. 
                                        If None, uses the current theme.
        """
        # Update current theme if a new theme is provided
        if theme_name is not None:
            self.current_theme = theme_name

        # Ensure the theme exists, fallback to default if not
        if self.current_theme not in self.themes:
            self.current_theme = list(self.themes.keys())[0]

        # Get the current theme dictionary
        theme = self.themes[self.current_theme]

        # The base module should have more minimal styling to avoid conflicts
        # when it's included in TabManager
        self.setStyleSheet(f"""
            /* Base styles - kept minimal to avoid conflicts */
            QLabel {{
                color: {theme['fg']};
            }}
            
            /* Custom module-specific styling - use class selectors */
            .custom-widget {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
            }}
        """)

        # Recursive theme application to child widgets
        self._apply_theme_to_children(self, theme)

    def _apply_theme_to_children(self, parent, theme):
        """
        Recursively apply theme to child widgets with special handling for specific widget types
        
        Args:
            parent (QWidget): Parent widget to start theme application
            theme (dict): Theme dictionary
        """
        for child in parent.findChildren(QWidget):
            try:
                # First call custom apply_theme if available
                if hasattr(child, 'apply_theme'):
                    child.apply_theme(self.current_theme)
                    continue
                    
                # Special handling for specific widget types
                widget_type = child.__class__.__name__
                    
                # Apply specific styling for various widget types
                if hasattr(child, 'setStyleSheet'):
                    # Using direct style application for better specificity
                    if isinstance(child, QTableWidget) or isinstance(child, QTableView):
                        child.setStyleSheet(f"""
                            QTableWidget, QTableView {{
                                background-color: {theme['secondary_bg']};
                                color: {theme['fg']};
                                gridline-color: {theme['border']};
                            }}
                        """)
                        # Adjust header properties
                        if hasattr(child, 'horizontalHeader') and hasattr(child, 'verticalHeader'):
                            child.horizontalHeader().setStyleSheet(f"""
                                QHeaderView::section {{
                                    background-color: {theme['secondary_bg']};
                                    color: {theme['fg']};
                                    border: 1px solid {theme['border']};
                                }}
                            """)
                            child.verticalHeader().setStyleSheet(f"""
                                QHeaderView::section {{
                                    background-color: {theme['secondary_bg']};
                                    color: {theme['fg']};
                                    border: 1px solid {theme['border']};
                                }}
                            """)
                    
                    # Progress bars need special handling for chunks
                    elif isinstance(child, QProgressBar):
                        child.setStyleSheet(f"""
                            QProgressBar {{
                                text-align: center;
                                border: 1px solid {theme['border']};
                                border-radius: 3px;
                                background-color: {theme['secondary_bg']};
                                color: {theme['fg']};
                            }}
                            QProgressBar::chunk {{
                                background-color: {theme['accent']};
                            }}
                        """)
                    
                    # Apply theme to frames and containers
                    elif isinstance(child, QFrame) or isinstance(child, QGroupBox):
                        child.setStyleSheet(f"""
                            border: 1px solid {theme['border']};
                            background-color: {theme['bg']};
                        """)
            except Exception as e:
                print(f"Warning: Could not apply theme to {child}: {e}")

    def set_tab_manager(self, tab_manager):
        """Establece la referencia al gestor de pestañas y actualiza el registro de módulos"""
        self.tab_manager = tab_manager
        
        # Crear un registro de módulos basado en los tabs disponibles
        if tab_manager and hasattr(tab_manager, 'tabs'):
            self._module_registry = {
                tab_name.lower().replace(' ', '_'): module 
                for tab_name, module in tab_manager.tabs.items()
            }

    def switch_tab(self, tab_name, method_to_call=None, *args, **kwargs):
        """Método de conveniencia para cambiar de pestaña desde el módulo"""
        if self.tab_manager:
            return self.tab_manager.switch_to_tab(tab_name, method_to_call, *args, **kwargs)
        else:
            print("No hay referencia al gestor de pestañas")
            return False

    def get_module(self, module_name):
        """
        Obtiene un módulo del registro por su nombre.
        
        Args:
            module_name (str): Nombre del módulo en formato lowercase con guiones bajos
        
        Returns:
            El módulo solicitado o None si no se encuentra
        """
        return self._module_registry.get(module_name)

    def call_module_method(self, module_name, method_name, *args, **kwargs):
        """Llama a un método de otro módulo
        self.call_module_method('module_name', 'method_name', *args, **kwargs)
        """
        if not self.tab_manager:
            print("TabManager no configurado")
            return None
        
        module = self.tab_manager.tabs.get(module_name)
        if module is None:
            print(f"Módulo '{module_name}' no encontrado")
            return None
        
        if hasattr(module, method_name):
            method = getattr(module, method_name)
            if callable(method):
                return method(*args, **kwargs)
        
        print(f"Método '{method_name}' no encontrado en '{module_name}'")
        return None


        

def find_project_root(marker_files=('requirements.txt', 'base_module.py', 'music_padre.py', 'designer_module.py')):
    """Busca la raíz del proyecto basándose en archivos distintivos."""
    path = Path(__file__).resolve().parent  # Directorio donde está el módulo actual
    while path != path.parent:
        if any((path / marker).exists() for marker in marker_files):
            return path
        path = path.parent
    return Path(__file__).resolve().parent.parent  # Fallback: asumir que estamos en un subdirectorio

# Definir la raíz del proyecto y el directorio de datos
PROJECT_ROOT = find_project_root()
