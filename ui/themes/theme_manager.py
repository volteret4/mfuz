from pathlib import Path
import json
import yaml
from typing import Dict, Any, Optional
import logging

# Definición de tema Material Design con más variables
MATERIAL_THEME = {
    # Colores primarios
    'primary': '#6200ee',
    'primary_variant': '#3700b3',
    'primary_dark': '#3700b3',
    'primary_light': '#bb86fc',
    
    # Colores secundarios
    'secondary': '#03dac6',
    'secondary_variant': '#018786',
    'secondary_light': '#64ffda',
    
    # Colores de fondo
    'bg': '#ffffff',
    'bg_variant': '#f6f6f6',
    'surface': '#ffffff',
    
    # Elementos de la interfaz
    'bg_card': '#ffffff',
    'bg_dialog': '#ffffff',
    'bg_disabled': '#e0e0e0',
    
    # Colores de error
    'error': '#b00020',
    'error_light': '#cf6679',
    
    # Texto y bordes
    'fg': '#000000',
    'fg_secondary': '#666666',
    'fg_disabled': '#888888',
    'fg_hint': '#999999',
    'border': '#e0e0e0',
    'divider': '#e0e0e0',
    
    # Estados de interacción
    'hover': '#f5f5f5',
    'pressed': '#e0e0e0',
    'ripple': 'rgba(0, 0, 0, 0.1)',
    'focus': 'rgba(98, 0, 238, 0.12)',
    'selection': 'rgba(98, 0, 238, 0.08)',
    
    # Componentes específicos
    'button_bg': '#6200ee',
    'button_text': '#ffffff',
    'button_hover': '#7926ff',
    'button_disabled': '#e0e0e0',
    
    # Elevación y sombras
    'shadow_light': '0 1px 3px rgba(0,0,0,0.12)',
    'shadow_medium': '0 3px 6px rgba(0,0,0,0.15)',
    'shadow_heavy': '0 10px 20px rgba(0,0,0,0.19)',
    
    # Valores de animación (en ms)
    'anim_duration_short': '100',
    'anim_duration_medium': '200',
    'anim_duration_long': '300',
    'anim_curve': 'cubic-bezier(0.4, 0.0, 0.2, 1)',
    
    # Espaciado y bordes
    'border_radius': '4px',
    'padding_small': '8px',
    'padding_medium': '16px',
    'padding_large': '24px',
}

# Tema Material Dark
MATERIAL_DARK_THEME = {
    # Colores primarios
    'primary': '#bb86fc',
    'primary_variant': '#3700b3',
    'primary_dark': '#3700b3',
    'primary_light': '#e1bee7',
    
    # Colores secundarios
    'secondary': '#03dac6',
    'secondary_variant': '#018786',
    'secondary_light': '#64ffda',
    
    # Colores de fondo
    'bg': '#121212',
    'bg_variant': '#1e1e1e',
    'surface': '#1e1e1e',
    
    # Elementos de la interfaz
    'bg_card': '#1e1e1e',
    'bg_dialog': '#2d2d2d',
    'bg_disabled': '#333333',
    
    # Colores de error
    'error': '#cf6679',
    'error_light': '#ffcdd2',
    
    # Texto y bordes
    'fg': '#e0e0e0',
    'fg_secondary': '#b0b0b0',
    'fg_disabled': '#707070',
    'fg_hint': '#808080',
    'border': '#2c2c2c',
    'divider': '#2c2c2c',
    
    # Estados de interacción
    'hover': '#2a2a2a',
    'pressed': '#3a3a3a',
    'ripple': 'rgba(255, 255, 255, 0.1)',
    'focus': 'rgba(187, 134, 252, 0.12)',
    'selection': 'rgba(187, 134, 252, 0.08)',
    
    # Componentes específicos
    'button_bg': '#bb86fc',
    'button_text': '#000000',
    'button_hover': '#c094fd',
    'button_disabled': '#494949',
    
    # Elevación y sombras
    'shadow_light': '0 1px 3px rgba(0,0,0,0.24)',
    'shadow_medium': '0 3px 6px rgba(0,0,0,0.29)',
    'shadow_heavy': '0 10px 20px rgba(0,0,0,0.35)',
    
    # Valores de animación (en ms)
    'anim_duration_short': '100',
    'anim_duration_medium': '200',
    'anim_duration_long': '300',
    'anim_curve': 'cubic-bezier(0.4, 0.0, 0.2, 1)',
    
    # Espaciado y bordes
    'border_radius': '4px',
    'padding_small': '8px',
    'padding_medium': '16px',
    'padding_large': '24px',
}

# Añadir más temas para integrarse con los existentes
ALL_THEMES = {
    # Temas existentes adaptados (mantenemos compatibilidad con los nombres anteriores)
    "Tokyo Night": {  # Tokyo Night
        'bg': '#1a1b26',
        'bg_variant': '#16161e',
        'surface': '#1a1b26',
        'fg': '#a9b1d6',
        'fg_secondary': '#787c99',
        'primary': '#7aa2f7',
        'primary_variant': '#5d7aea',
        'secondary': '#bb9af7',
        'error': '#f7768e',
        'border': '#414868',
        'divider': '#414868',
        'selection': '#364A82',
        'hover': '#2c324a',
        'pressed': '#3d4666',
        'button_bg': '#414868',
        'button_text': '#a9b1d6',
        'button_hover': '#3d59a1',
    },
    "Solarized Dark": {  # Solarized Dark
        'bg': '#002b36',
        'bg_variant': '#00212b',
        'surface': '#073642',
        'fg': '#839496',
        'fg_secondary': '#657b83',
        'primary': '#268bd2',
        'primary_variant': '#0e6bab',
        'secondary': '#2aa198',
        'error': '#dc322f',
        'border': '#586e75',
        'divider': '#586e75',
        'selection': '#2d4b54',
        'hover': '#093642',
        'pressed': '#0f4957',
        'button_bg': '#073642',
        'button_text': '#839496',
        'button_hover': '#4b6e83',
    },
    
    # Nuevos temas Material Design
    "Material Light": MATERIAL_THEME,
    "Material Dark": MATERIAL_DARK_THEME,
}

# Mapa para mantener la retrocompatibilidad con los nombres de variables antiguos
COMPAT_MAP = {
    'secondary_bg': 'bg_variant',     # Renombramos para más claridad
    'accent': 'primary',              # Lo que era 'accent' ahora es 'primary'
    'button_hover': 'button_hover',   # Este se mantiene igual
}

class ThemeManager:
    """
    Gestor centralizado de temas para la aplicación.
    - Carga configuraciones de temas desde archivos
    - Proporciona acceso a los temas y sus variables
    - Genera hojas de estilo CSS para QT
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.logger = logging.getLogger('ThemeManager')
        self.themes = ALL_THEMES.copy()
        self.current_theme = "Material Light"  # Tema por defecto
        self.custom_styles = {}  # Estilos específicos por objectName
        
        # Si hay una ruta de configuración, cargarla
        if config_path:
            self.load_config(config_path)
            
    def load_config(self, config_path: Path):
        """Carga la configuración de temas desde un archivo"""
        if not config_path.exists():
            self.logger.warning(f"Archivo de configuración no encontrado: {config_path}")
            return
            
        try:
            # Determinar formato basado en extensión
            ext = config_path.suffix.lower()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                if ext == '.json':
                    config = json.load(f)
                elif ext in ['.yml', '.yaml']:
                    config = yaml.safe_load(f)
                else:
                    self.logger.error(f"Formato de archivo no soportado: {ext}")
                    return
                
            # Cargar temas personalizados si existen
            if 'themes' in config:
                for theme_name, theme_values in config['themes'].items():
                    # Si ya existe, actualizar solo los valores proporcionados
                    if theme_name in self.themes:
                        self.themes[theme_name].update(theme_values)
                    else:
                        self.themes[theme_name] = theme_values
                        
            # Cargar tema actual si está definido
            if 'current_theme' in config:
                theme_name = config['current_theme']
                if theme_name in self.themes:
                    self.current_theme = theme_name
                else:
                    self.logger.warning(f"Tema '{theme_name}' no encontrado, usando el predeterminado")
                    
            # Cargar estilos personalizados por objectName
            if 'custom_styles' in config:
                self.custom_styles = config['custom_styles']
                
            self.logger.info(f"Configuración de temas cargada desde {config_path}")
            
        except Exception as e:
            self.logger.error(f"Error al cargar configuración de temas: {e}")
            
    def save_config(self, config_path: Path):
        """Guarda la configuración de temas en un archivo"""
        try:
            config = {
                'current_theme': self.current_theme,
                'themes': self.themes,
                'custom_styles': self.custom_styles
            }
            
            # Determinar formato basado en extensión
            ext = config_path.suffix.lower()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                if ext == '.json':
                    json.dump(config, f, indent=2)
                elif ext in ['.yml', '.yaml']:
                    yaml.dump(config, f, sort_keys=False, default_flow_style=False, indent=2, allow_unicode=True)
                else:
                    # Por defecto usar JSON
                    json.dump(config, f, indent=2)
                    
            self.logger.info(f"Configuración de temas guardada en {config_path}")
            
        except Exception as e:
            self.logger.error(f"Error al guardar configuración de temas: {e}")
            
    def get_theme(self, theme_name: Optional[str] = None) -> Dict[str, str]:
        """
        Obtiene un tema por su nombre.
        Si no se proporciona un nombre, devuelve el tema actual.
        """
        name = theme_name or self.current_theme
        
        # Si el tema solicitado no existe, volver al predeterminado
        if name not in self.themes:
            self.logger.warning(f"Tema '{name}' no encontrado, usando 'Material Light'")
            name = "Material Light"
            
        theme = self.themes[name].copy()
        
        # Añadir variables de compatibilidad
        for old_key, new_key in COMPAT_MAP.items():
            if new_key in theme and old_key not in theme:
                theme[old_key] = theme[new_key]
                
        return theme
        
    def set_current_theme(self, theme_name: str) -> bool:
        """
        Establece el tema actual.
        Devuelve True si se ha cambiado correctamente, False en caso contrario.
        """
        if theme_name in self.themes:
            self.current_theme = theme_name
            self.logger.info(f"Tema actual cambiado a '{theme_name}'")
            return True
        else:
            self.logger.warning(f"Tema '{theme_name}' no encontrado")
            return False
            
    def get_widget_style(self, object_name: str) -> str:
        """
        Obtiene el estilo específico para un widget por su objectName.
        """
        if object_name in self.custom_styles:
            # Obtener variables del tema actual
            theme = self.get_theme()
            
            # Reemplazar variables en el estilo personalizado
            style = self.custom_styles[object_name]
            for var_name, var_value in theme.items():
                placeholder = f"${var_name}"
                style = style.replace(placeholder, var_value)
                
            return style
        return ""
        
    def get_stylesheet(self) -> str:
        """
        Genera una hoja de estilo QSS completa basada en el tema actual.
        Incluye reglas generales para todos los widgets y algunas específicas.
        """
        theme = self.get_theme()
        
        # Estilo base Material Design
        stylesheet = f"""
        /* Base Styles */
        QWidget {{
            background-color: {theme['bg']};
            color: {theme['fg']};
            selection-background-color: {theme.get('selection', theme['primary'] + '33')};
            selection-color: {theme['fg']};
        }}
        
        /* Frames, GroupBoxes, y contenedores */
        QFrame, QGroupBox {{
            border: none;
            border-radius: {theme.get('border_radius', '4px')};
            background-color: {theme['bg']};
        }}
        
        QGroupBox {{
            margin-top: 20px;
            padding-top: 24px;
            padding-bottom: 4px;
            padding-left: 4px;
            padding-right: 4px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            color: {theme.get('fg_secondary', theme['fg'])};
            padding: 5px;
            left: 10px;
        }}
        
        /* Campos de texto */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
            background-color: {theme.get('surface', theme['bg'])};
            border: 1px solid {theme['border']};
            border-radius: {theme.get('border_radius', '4px')};
            padding: {theme.get('padding_small', '8px')};
            selection-background-color: {theme.get('selection', theme['primary'] + '33')};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {theme['primary']};
        }}
        
        QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
            background-color: {theme.get('hover', theme['bg'])};
        }}
        
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
            background-color: {theme.get('bg_disabled', theme['bg'])};
            color: {theme.get('fg_disabled', theme['fg'])};
        }}
        
        /* Botones */
        QPushButton {{
            background-color: {theme.get('button_bg', theme['primary'])};
            color: {theme.get('button_text', '#ffffff')};
            border: none;
            border-radius: {theme.get('border_radius', '4px')};
            padding: {theme.get('padding_small', '8px')} {theme.get('padding_medium', '16px')};
            min-height: 36px;
            outline: none;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {theme.get('button_hover', '#7926ff')};
        }}
        
        QPushButton:pressed {{
            background-color: {theme.get('pressed', theme['primary'])};
            padding-top: 9px;
            padding-bottom: 7px;
        }}
        
        QPushButton:disabled {{
            background-color: {theme.get('button_disabled', '#e0e0e0')};
            color: {theme.get('fg_disabled', theme['fg'])};
        }}
        
        /* Botones planos o de texto */
        QPushButton[flat="true"] {{
            background-color: transparent;
            color: {theme['primary']};
            border: none;
        }}
        
        QPushButton[flat="true"]:hover {{
            background-color: {theme['primary'] + '22'};
        }}
        
        QPushButton[flat="true"]:pressed {{
            background-color: {theme['primary'] + '33'};
        }}
        
        /* Labels */
        QLabel {{
            color: {theme['fg']};
            padding: 0px;
            background: transparent;
        }}
        
        QLabel[heading="true"] {{
            font-size: 18px;
            font-weight: bold;
            color: {theme.get('fg', theme['fg'])};
        }}
        
        QLabel[subheading="true"] {{
            font-size: 16px;
            color: {theme.get('fg_secondary', theme['fg'])};
        }}
        
        /* Tablas */
        QTableView, QTableWidget {{
            background-color: {theme.get('surface', theme['bg'])};
            alternate-background-color: {theme.get('bg_variant', theme['bg'])};
            border: none;
            gridline-color: {theme['divider']};
            selection-background-color: {theme.get('selection', theme['primary'] + '33')};
        }}
        
        QTableView::item, QTableWidget::item {{
            padding: 6px;
        }}
        
        QTableView::item:selected, QTableWidget::item:selected {{
            background-color: {theme.get('selection', theme['primary'] + '33')};
            color: {theme['fg']};
        }}
        
        QHeaderView::section {{
            background-color: {theme.get('bg_variant', theme['bg'])};
            color: {theme.get('fg_secondary', theme['fg'])};
            padding: 8px;
            border: none;
            border-bottom: 1px solid {theme['divider']};
            border-right: 1px solid {theme['divider']};
        }}
        
        /* Menús */
        QMenuBar {{
            background-color: {theme.get('bg_variant', theme['bg'])};
            border-bottom: 1px solid {theme['divider']};
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 8px 12px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {theme.get('hover', theme['bg'])};
        }}
        
        QMenu {{
            background-color: {theme.get('bg_card', theme['bg'])};
            border: 1px solid {theme['divider']};
            border-radius: {theme.get('border_radius', '4px')};
        }}
        
        QMenu::item {{
            padding: 8px 24px 8px 16px;
        }}
        
        QMenu::item:selected {{
            background-color: {theme.get('hover', theme['bg'])};
        }}
        
        /* Pestañas */
        QTabWidget::pane {{
            border: 1px solid {theme['divider']};
            border-radius: {theme.get('border_radius', '4px')};
            background-color: {theme.get('surface', theme['bg'])};
            position: absolute;
            top: -1px;
        }}
        
        QTabBar::tab {{
            background-color: transparent;
            color: {theme.get('fg_secondary', theme['fg'])};
            border-top-left-radius: {theme.get('border_radius', '4px')};
            border-top-right-radius: {theme.get('border_radius', '4px')};
            padding: 8px 16px;
            min-width: 80px;
            border-bottom: 2px solid transparent;
        }}
        
        QTabBar::tab:selected {{
            color: {theme['primary']};
            border-bottom: 2px solid {theme['primary']};
        }}
        
        QTabBar::tab:hover:!selected {{
            color: {theme['fg']};
            background-color: {theme.get('hover', theme['bg'])};
        }}
        
        /* Scrollbars */
        QScrollBar:vertical {{
            background-color: {theme.get('bg_variant', theme['bg'])};
            width: 12px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {theme.get('fg_secondary', theme['fg']) + '44'};
            border-radius: 4px;
            min-height: 20px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {theme.get('fg_secondary', theme['fg']) + '88'};
        }}
        
        QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            background: none;
            border: none;
        }}
        
        QScrollBar:horizontal {{
            background-color: {theme.get('bg_variant', theme['bg'])};
            height: 12px;
            margin: 0px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {theme.get('fg_secondary', theme['fg']) + '44'};
            border-radius: 4px;
            min-width: 20px;
            margin: 2px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {theme.get('fg_secondary', theme['fg']) + '88'};
        }}
        
        QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            background: none;
            border: none;
        }}
        
        /* Barras de progreso */
        QProgressBar {{
            border: none;
            background-color: {theme.get('bg_variant', theme['bg'])};
            border-radius: {theme.get('border_radius', '4px')};
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: {theme['primary']};
            border-radius: {theme.get('border_radius', '4px')};
        }}
        
        /* Sliders */
        QSlider::groove:horizontal {{
            height: 4px;
            background-color: {theme.get('bg_variant', theme['bg'])};
            border-radius: 2px;
        }}
        
        QSlider::handle:horizontal {{
            background-color: {theme['primary']};
            border: none;
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background-color: {theme.get('button_hover', theme['primary'])};
        }}
        
        /* Listas y árboles */
        QListView, QTreeView {{
            background-color: {theme.get('surface', theme['bg'])};
            border: none;
            outline: none;
        }}
        
        QListView::item, QTreeView::item {{
            padding: 6px;
            border-radius: {theme.get('border_radius', '4px')};
        }}
        
        QListView::item:hover, QTreeView::item:hover {{
            background-color: {theme.get('hover', theme['bg'])};
        }}
        
        QListView::item:selected, QTreeView::item:selected {{
            background-color: {theme.get('selection', theme['primary'] + '33')};
            color: {theme['fg']};
        }}
        
        /* Tooltips */
        QToolTip {{
            background-color: {theme.get('bg_card', theme['bg'])};
            color: {theme['fg']};
            border: 1px solid {theme['border']};
            border-radius: {theme.get('border_radius', '4px')};
            padding: 4px 8px;
        }}
        
        /* Combo Box (desplegables) */
        QComboBox {{
            background-color: {theme.get('surface', theme['bg'])};
            border: 1px solid {theme['border']};
            border-radius: {theme.get('border_radius', '4px')};
            padding: 6px 10px;
            min-height: 36px;
        }}
        
        QComboBox:hover {{
            background-color: {theme.get('hover', theme['bg'])};
        }}
        
        QComboBox:focus {{
            border: 2px solid {theme['primary']};
        }}
        
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: right center;
            width: 20px;
            border: none;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {theme.get('bg_card', theme['bg'])};
            border: 1px solid {theme['border']};
            border-radius: {theme.get('border_radius', '4px')};
            selection-background-color: {theme.get('selection', theme['primary'] + '33')};
        }}
        
        /* CheckBox y RadioButton */
        QCheckBox, QRadioButton {{
            spacing: 8px;
            color: {theme['fg']};
        }}
        
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px;
            height: 18px;
        }}
        
        QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {{
            border: 2px solid {theme.get('fg_secondary', theme['fg'])};
        }}
        
        QCheckBox::indicator:unchecked {{
            border-radius: 3px;
        }}
        
        QRadioButton::indicator:unchecked {{
            border-radius: 10px;
        }}
        
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background-color: {theme['primary']};
        }}
        
        QCheckBox::indicator:checked {{
            border: 2px solid {theme['primary']};
            border-radius: 3px;
        }}
        
        QRadioButton::indicator:checked {{
            border: 2px solid {theme['primary']};
            border-radius: 10px;
        }}
        
        /* Scroll Area */
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        
        /* Separador */
        QFrame[frameShape="HLine"] {{
            background-color: {theme['divider']};
            height: 1px;
            border: none;
        }}
        
        QFrame[frameShape="VLine"] {{
            background-color: {theme['divider']};
            width: 1px;
            border: none;
        }}
        
        /* Soporte para animaciones de QPropertyAnimation */
        /* Estas clases deben existir para que se puedan animar propiedades como background-color */
        .animated {{
            transition-property: background-color, color, border-color, padding;
            transition-duration: {theme.get('anim_duration_medium', '200')}ms;
            transition-timing-function: {theme.get('anim_curve', 'cubic-bezier(0.4, 0.0, 0.2, 1)')};
        }}
        
        .quick-animated {{
            transition-duration: {theme.get('anim_duration_short', '100')}ms;
        }}
        
        .slow-animated {{
            transition-duration: {theme.get('anim_duration_long', '300')}ms;
        }}
        """
        
        # Añadir estilos para objectName específicos
        for object_name, style in self.custom_styles.items():
            # Reemplazar variables del tema
            for var_name, var_value in theme.items():
                placeholder = f"${var_name}"
                style = style.replace(placeholder, var_value)
                
            # Añadir estilo para este objectName
            stylesheet += f"""
            #{object_name} {{
                {style}
            }}
            """
            
        return stylesheet

# Crear una instancia global del gestor de temas
theme_manager = ThemeManager()