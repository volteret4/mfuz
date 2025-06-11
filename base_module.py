from PyQt6.QtWidgets import QWidget, QTableWidget, QTableView, QProgressBar, QFrame, QGroupBox
from typing import Optional
from pathlib import Path
import os
import traceback
import importlib


# Verificar si existe el módulo themes.py
themes_path = Path(__file__).parent / "themes" / "themes.py"
if themes_path.exists():
    try:
        # Importar dinámicamente el módulo themes.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("themes", themes_path)
        themes_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(themes_module)
        
        # Importar las funciones correctas del nuevo sistema
        THEMES = themes_module.THEMES
        apply_theme_to_widget_function = getattr(themes_module, 'apply_theme_to_widget', None)
        apply_effects_to_widget_function = getattr(themes_module, 'apply_effects_to_widget', None)
        setup_objectnames_function = getattr(themes_module, 'setup_objectnames_for_theme', None)
        
        #print("Sistema de temas centralizado cargado correctamente")
    except Exception as e:
        print(f"Error cargando sistema de temas: {e}")
        themes_module = None
        apply_theme_to_widget_function = None
        apply_effects_to_widget_function = None
        setup_objectnames_function = None
else:
    themes_module = None
    apply_theme_to_widget_function = None
    apply_effects_to_widget_function = None
    setup_objectnames_function = None

# Definición de temas fallback si no existe themes.py o falla la carga
if themes_module is None:
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
        "Material Light": {
            'bg': '#ffffff',
            'fg': '#212121',
            'accent': '#6200ee',
            'secondary_bg': '#f5f5f5',
            'border': '#e0e0e0',
            'selection': '#e3f2fd',
            'button_hover': '#ede7f6'
        },
        "Material Dark": {
            'bg': '#121212',
            'fg': '#eeeeee',
            'accent': '#bb86fc',
            'secondary_bg': '#1e1e1e',
            'border': '#333333',
            'selection': '#3700b3',
            'button_hover': '#3d4048'
        },
        "Nord": {
            'bg': '#2e3440',
            'fg': '#eceff4',
            'accent': '#88c0d0',
            'secondary_bg': '#3b4252',
            'border': '#4c566a',
            'selection': '#434c5e',
            'button_hover': '#5e81ac'
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

        # Aplicar efectos adicionales si el sistema centralizado está disponible
        try:
            if apply_effects_to_widget_function is not None:
                apply_effects_to_widget_function(self)
        except Exception as e:
            print(f"Error aplicando efectos: {e}")

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
            ui_file_path = Path(PROJECT_ROOT, "ui", ui_file_name)
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
        Aplica un tema al módulo usando ÚNICAMENTE el sistema centralizado de temas.
        NO aplica estilos adicionales, solo usa el CSS de themes.py
        
        Args:
            theme_name (str, optional): Nombre del tema a aplicar. 
                                        Si es None, usa el tema actual.
        """
        # Actualizar el tema actual si se proporciona uno nuevo
        if theme_name is not None:
            self.current_theme = theme_name

        # Asegurar que el tema existe, usar el primero por defecto si no
        if self.current_theme not in self.themes:
            self.current_theme = list(self.themes.keys())[0]

        # SOLO usar el sistema de temas centralizado
        try:
            if apply_theme_to_widget_function is not None:
                # Añadir objectName al widget si no lo tiene
                if not self.objectName():
                    module_class_name = self.__class__.__name__.lower()
                    self.setObjectName(module_class_name)
                    
                # Configurar objectNames automáticamente
                if setup_objectnames_function is not None:
                    setup_objectnames_function(self)
                
                # Usar ÚNICAMENTE la función centralizada - NO añadir CSS adicional
                apply_theme_to_widget_function(self, self.current_theme)
                
                # Aplicar efectos si están disponibles
                if apply_effects_to_widget_function is not None:
                    apply_effects_to_widget_function(self)
                
                print(f"Tema '{self.current_theme}' aplicado via sistema centralizado")
                return
                
        except Exception as e:
            print(f"Error al aplicar tema centralizado: {e}")
            traceback.print_exc()
        
        # Si no hay sistema centralizado, NO aplicar ningún estilo
        # Dejar que Qt use sus estilos por defecto
        #print(f"Sistema de temas centralizado no disponible. Widget sin tema personalizado.")



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
