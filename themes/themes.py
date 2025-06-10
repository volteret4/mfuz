import os
from PyQt6.QtWidgets import QWidget, QApplication, QPushButton, QTabBar
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QSize, Qt, QPoint, QVariantAnimation, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

# Definición de temas con variables de color
THEMES = {
    "Tokyo Night": {
        'bg': '#1a1b26',              # Color de fondo principal
        'fg': '#a9b1d6',              # Color de texto principal
        'accent': '#3d59a1',          # Color de acento para elementos destacados
        'secondary_bg': '#24283b',    # Color de fondo secundario
        'border': '#414868',          # Color de bordes
        'selection': '#364A82',       # Color para elementos seleccionados
        'button_hover': '#3d59a1',    # Color de botones al pasar el ratón
        'success': '#9ece6a',         # Color de éxito
        'warning': '#e0af68',         # Color de advertencia
        'error': '#f7768e',           # Color de error
        'info': '#7dcfff',            # Color informativo
        'disabled': '#565f89',        # Color para elementos deshabilitados
        'header_bg': '#1e2030',       # Color de fondo para encabezados
        'alternate_row': '#262b3f',   # Color para filas alternas en tablas
        'shadow': 'rgba(0, 0, 0, 0.4)', # Color para sombras
        'card_bg': '#24283b',         # Fondo de tarjetas
        'icon_color': '#757575',      # Color de iconos (gris medio)
    },
    "Material Light": {
        'bg': '#ffffff',              # Color de fondo principal
        'fg': '#212121',              # Color de texto principal
        'accent': '#6200ee',          # Color de acento
        'secondary_bg': '#f5f5f5',    # Color de fondo secundario
        'border': '#e0e0e0',          # Color de bordes
        'selection': '#e3f2fd',       # Color para elementos seleccionados
        'button_hover': '#ede7f6',    # Color de botones al pasar el ratón
        'success': '#4caf50',         # Color de éxito
        'warning': '#fb8c00',         # Color de advertencia
        'error': '#f44336',           # Color de error
        'info': '#2196f3',            # Color informativo
        'disabled': '#9e9e9e',        # Color para elementos deshabilitados
        'header_bg': '#fafafa',       # Color de fondo para encabezados
        'alternate_row': '#f5f5f5',   # Color para filas alternas
        'shadow': 'rgba(0, 0, 0, 0.1)', # Color para sombras
        'card_bg': '#ffffff',         # Fondo de tarjetas (blanco puro)
        'icon_color': '#757575',      # Color de iconos (gris medio)
    },
    "Material Dark": {
        'bg': '#121212',              # Color de fondo principal
        'fg': '#eeeeee',              # Color de texto principal
        'accent': '#bb86fc',          # Color de acento para elementos destacados
        'secondary_bg': '#1e1e1e',    # Color de fondo secundario
        'border': '#333333',          # Color de bordes
        'selection': '#3700b3',       # Color para elementos seleccionados
        'button_hover': '#3d4048',    # Color de botones al pasar el ratón
        'success': '#4caf50',         # Color de éxito
        'warning': '#ffb74d',         # Color de advertencia
        'error': '#cf6679',           # Color de error
        'info': '#64b5f6',            # Color informativo
        'disabled': '#6c6c6c',        # Color para elementos deshabilitados
        'header_bg': '#1f1f1f',       # Color de fondo para encabezados
        'alternate_row': '#242424',   # Color para filas alternas en tablas
        'shadow': 'rgba(0, 0, 0, 0.5)', # Color para sombras
        'card_bg': '#1e1e1e',         # Fondo de tarjetas
        'icon_color': '#757575',      # Color de iconos (gris medio)
    },
    "Nord": {
        'bg': '#2e3440',              # Color de fondo principal
        'fg': '#eceff4',              # Color de texto principal
        'accent': '#88c0d0',          # Color de acento para elementos destacados
        'secondary_bg': '#3b4252',    # Color de fondo secundario
        'border': '#4c566a',          # Color de bordes
        'selection': '#434c5e',       # Color para elementos seleccionados
        'button_hover': '#5e81ac',    # Color de botones al pasar el ratón
        'success': '#a3be8c',         # Color de éxito
        'warning': '#ebcb8b',         # Color de advertencia
        'error': '#bf616a',           # Color de error
        'info': '#81a1c1',            # Color informativo
        'disabled': '#7a889b',        # Color para elementos deshabilitados
        'header_bg': '#3b4252',       # Color de fondo para encabezados
        'alternate_row': '#3b4252',   # Color para filas alternas en tablas
        'shadow': 'rgba(0, 0, 0, 0.3)', # Color para sombras
        'card_bg': '#3b4252',         # Fondo de tarjetas
        'icon_color': '#757575',      # Color de iconos (gris medio)
    },
    "Material Minimalista": {
        'bg': '#fafafa',              # Fondo principal (claro)
        'fg': '#212121',              # Texto principal (casi negro)
        'accent': '#2196F3',          # Azul material como acento
        'secondary_bg': '#f5f5f5',    # Fondo secundario (un poco más oscuro)
        'border': '#e0e0e0',          # Bordes sutiles
        'selection': '#e3f2fd',       # Selección suave (azul muy claro)
        'button_hover': '#eeeeee',    # Hover muy sutil
        'success': '#4CAF50',         # Verde material
        'warning': '#FFC107',         # Amarillo material
        'error': '#F44336',           # Rojo material
        'info': '#2196F3',            # Azul material
        'disabled': '#9E9E9E',        # Gris medio
        'header_bg': '#e0e0e0',       # Encabezados ligeramente destacados
        'alternate_row': '#f0f0f0',   # Filas alternas casi imperceptibles
        'shadow': 'rgba(0, 0, 0, 0.1)', # Sombras muy sutiles
        'card_bg': '#ffffff',         # Fondo de tarjetas (blanco puro)
        'icon_color': '#757575',      # Color de iconos (gris medio)
    },
    "Material Minimalista Dark": {
        'bg': '#121212',              # Fondo principal (casi negro)
        'fg': '#ffffff',              # Texto principal (blanco)
        'accent': '#90CAF9',          # Azul claro como acento
        'secondary_bg': '#1e1e1e',    # Fondo secundario (un poco más claro)
        'border': '#333333',          # Bordes sutiles
        'selection': '#1e3a56',       # Selección azul oscura
        'button_hover': '#2c2c2c',    # Hover sutil
        'success': '#81C784',         # Verde material más claro
        'warning': '#FFD54F',         # Amarillo material más claro
        'error': '#E57373',           # Rojo material más claro
        'info': '#64B5F6',            # Azul material más claro
        'disabled': '#757575',        # Gris medio
        'header_bg': '#1f1f1f',       # Encabezados ligeramente destacados
        'alternate_row': '#1a1a1a',   # Filas alternas casi imperceptibles
        'shadow': 'rgba(0, 0, 0, 0.2)', # Sombras sutiles
        'card_bg': '#1e1e1e',         # Fondo de tarjetas
        'icon_color': '#9e9e9e',      # Color de iconos (gris claro)
    }
}

def get_stylesheet(theme_name):
    """
    Genera la hoja de estilos CSS para el tema especificado
    
    Args:
        theme_name (str): Nombre del tema a utilizar
        
    Returns:
        str: Hoja de estilos CSS completa
    """
    # Obtener los colores del tema
    if theme_name not in THEMES:
        theme_name = list(THEMES.keys())[0]  # Usa el primer tema como fallback
    
    theme = THEMES[theme_name]
    
    # Estilo base para toda la aplicación
    base_style = f"""
    /* Estilo base para todos los widgets */
    QWidget {{
        background-color: {theme['bg']};
        color: {theme['fg']};
        font-family: "Segoe UI", "Noto Sans", sans-serif;
        font-size: 10pt;
        selection-background-color: {theme['selection']};
        selection-color: {theme['fg']};
    }}
    
    /* Tooltips */
    QToolTip {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        border-radius: 4px;
        padding: 2px;
    }}
    
    /* Bordes y marcos */
    QFrame, QGroupBox {{
        border: none;
        border-radius: 4px;
    }}
    
    QGroupBox {{
        background-color: {theme['bg']};
        margin-top: 12px;
        padding-top: 12px;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 5px;
        color: {theme['accent']};
    }}
    
    /* Campos de texto */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {theme['bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        border-radius: 4px;
        padding: 5px;
        selection-background-color: {theme['selection']};
    }}
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {theme['accent']};
    }}
    
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
        background-color: {theme['secondary_bg']};
        color: {theme['disabled']};
        border: 1px solid {theme['border']};
    }}
    
    /* Botones básicos */
    QPushButton {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 24px;
    }}
    
    QPushButton:hover {{
        background-color: {theme['button_hover']};
        border: 1px solid {theme['accent']};
    }}
    
    QPushButton:pressed {{
        background-color: {theme['selection']};
        padding: 7px 11px 5px 13px;
    }}
    
    QPushButton:disabled {{
        background-color: {theme['secondary_bg']};
        color: {theme['disabled']};
        border: 1px solid {theme['border']};
    }}
    
    /* Botones circulares/cuadrados para iconos */
    QPushButton[objectName*="icon_button"], QPushButton[objectName*="_button"] {{
        border-radius: 17px;
        min-width: 34px;
        max-width: 34px;
        min-height: 34px;
        max-height: 34px;
        padding: 0px;
    }}
    
    QPushButton[objectName*="icon_button"]:hover, QPushButton[objectName*="_button"]:hover {{
        background-color: {theme['button_hover']};
        border: 1px solid {theme['accent']};
    }}
    
    QPushButton[objectName*="icon_button"]:pressed, QPushButton[objectName*="_button"]:pressed {{
        background-color: {theme['selection']};
        padding: 1px 0 0 1px;
    }}
    
    /* Menús y barras de menú */
    QMenuBar {{
        background-color: {theme['bg']};
        color: {theme['fg']};
        border-bottom: 1px solid {theme['border']};
    }}
    
    QMenuBar::item {{
        background-color: transparent;
        padding: 6px 10px;
    }}
    
    QMenuBar::item:selected {{
        background-color: {theme['selection']};
        color: {theme['fg']};
    }}
    
    QMenu {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        border-radius: 2px;
    }}
    
    QMenu::item {{
        padding: 6px 25px 6px 20px;
        border-radius: 2px;
    }}
    
    QMenu::item:selected {{
        background-color: {theme['selection']};
        color: {theme['fg']};
    }}
    
    QMenu::separator {{
        height: 1px;
        background-color: {theme['border']};
        margin: 5px 10px;
    }}
    
    /* Listas y tablas */
    QListView, QTreeView, QTableView {{
        background-color: {theme['bg']};
        alternate-background-color: {theme['alternate_row']};
        border: none;
        border-radius: 4px;
        selection-background-color: {theme['selection']};
        selection-color: {theme['fg']};
        show-decoration-selected: 1;
    }}
    
    QListView::item, QTreeView::item, QTableView::item {{
        padding: 4px;
        border-radius: 2px;
    }}
    
    QListView::item:hover, QTreeView::item:hover, QTableView::item:hover {{
        background-color: {theme['button_hover']};
    }}
    
    QListView::item:selected, QTreeView::item:selected, QTableView::item:selected {{
        background-color: {theme['selection']};
    }}
    
    QHeaderView::section {{
        background-color: {theme['header_bg']};
        color: {theme['fg']};
        padding: 5px;
        border: none;
    }}
    
    /* Scrollbars */
    QScrollBar:vertical {{
        background-color: {theme['bg']};
        width: 8px;
        margin: 0px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {theme['border']};
        min-height: 20px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {theme['accent']};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        background-color: {theme['bg']};
        height: 8px;
        margin: 0px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {theme['border']};
        min-width: 20px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {theme['accent']};
    }}
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    
    /* Barras de progreso */
    QProgressBar {{
        border: 1px solid {theme['border']};
        border-radius: 4px;
        background-color: {theme['secondary_bg']};
        text-align: center;
        color: {theme['fg']};
    }}
    
    QProgressBar::chunk {{
        background-color: {theme['accent']};
        border-radius: 3px;
    }}
    
    /* Pestañas */
    QTabWidget::pane {{
        border: 1px solid {theme['border']};
        border-radius: 4px;
        background-color: {theme['bg']};
        top: -1px;
    }}
    
    QTabBar {{
        qproperty-drawBase: 0;
        background-color: transparent;
    }}
    
    QTabBar::tab {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 16px;
        min-width: 80px;
        margin-right: 2px;
        min-height: 15px;
    }}
    
    QTabBar::tab:selected {{
        background-color: {theme['bg']};
        border-bottom: 1px solid {theme['bg']};
        border-top: 2px solid {theme['accent']};
        font-weight: bold;
    }}
    
    QTabBar::tab:hover:!selected {{
        background-color: {theme['button_hover']};
        border-top: 2px solid {theme['accent']};
    }}
    
    QTabBar::tab:!selected {{
        margin-top: 2px;
    }}
    
    /* Indicador visual mientras se arrastra */
    QTabBar::tab:selected:active {{
        background-color: {theme['selection']};
        border: 2px solid {theme['accent']};
    }}
    
    /* Checkboxes y radio buttons */
    QCheckBox, QRadioButton {{
        spacing: 8px;
    }}
    
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
    }}
    
    QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {{
        background-color: {theme['secondary_bg']};
        border: 1px solid {theme['border']};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {theme['accent']};
        border: 1px solid {theme['accent']};
    }}
    
    QRadioButton::indicator:unchecked {{
        border-radius: 9px;
    }}
    
    QRadioButton::indicator:checked {{
        background-color: {theme['accent']};
        border: 1px solid {theme['accent']};
        border-radius: 9px;
    }}
    
    /* Combobox */
    QComboBox {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        border-radius: 4px;
        padding: 5px;
        min-height: 28px;
    }}
    
    QComboBox:hover {{
        border: 1px solid {theme['accent']};
    }}
    
    QComboBox:focus {{
        border: 1px solid {theme['accent']};
    }}
    
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border: none;
        background-color: {theme['secondary_bg']};
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border: none;
        width: 0px;
        height: 0px;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {theme['fg']};
        margin: 0px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        selection-background-color: {theme['selection']};
        selection-color: {theme['fg']};
        outline: 0;
        border-radius: 4px;
    }}
    
    QComboBox QAbstractItemView::item {{
        padding: 6px;
        border: none;
    }}
    
    QComboBox QAbstractItemView::item:selected {{
        background-color: {theme['selection']};
        color: {theme['fg']};
    }}
    
    /* ScrollArea */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    
    /* StatusBar */
    QStatusBar {{
        background-color: {theme['header_bg']};
        color: {theme['fg']};
        border-top: 1px solid {theme['border']};
    }}
    
    QStatusBar::item {{
        border: none;
    }}
    
    /* Splitter */
    QSplitter::handle {{
        background-color: {theme['border']};
    }}
    
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    
    QSplitter::handle:vertical {{
        height: 2px;
    }}
    
    QSplitter::handle:hover {{
        background-color: {theme['secondary_bg']};
    }}
    
    /* Labels importantes */
    QLabel[objectName="title_label"] {{
        color: {theme['accent']};
        font-size: 14pt;
        font-weight: bold;
    }}
    
    QLabel[objectName="header_label"] {{
        color: {theme['fg']};
        font-size: 12pt;
        font-weight: bold;
    }}
    
    QLabel[objectName="info_label"] {{
        color: {theme['info']};
    }}
    
    QLabel[objectName="warning_label"] {{
        color: {theme['warning']};
    }}
    
    QLabel[objectName="error_label"] {{
        color: {theme['error']};
    }}
    
    QLabel[objectName="success_label"] {{
        color: {theme['success']};
    }}

    QLabel a {{
        color: {theme['accent']};
    }}
    
    QLabel a:hover {{
        color: {theme['button_hover']};
    }}
    """
    
    # Estilos específicos para módulos por objectName
    module_specific_styles = f"""
    /* Estilos específicos para music_fuzzy_module */
    #music_fuzzy_module QTreeWidget {{
        alternate-background-color: {theme['alternate_row']};
    }}
    
    QLineEdit[objectName="search_box"] {{
        background-color: {theme['card_bg']};
        border: 1px solid {theme['border']};
        border-radius: 18px;
        padding: 8px 16px;
        color: {theme['fg']};
    }}
        QLineEdit[objectName="conciertos_search_box"] {{
        background-color: {theme['card_bg']};
        border: 1px solid {theme['border']};
        border-radius: 18px;
        padding: 8px 16px;
        color: {theme['fg']};
    }}
    
    QLineEdit[objectName="search_box"]:focus {{
        border: 1px solid {theme['accent']};
    }}

    QLineEdit[objectName="conciertos_search_box"]:focus {{
        border: 1px solid {theme['accent']};
    }}

    /* Card styles para paneles de información */
    QLabel[objectName*="info_label"], QLabel[objectName*="metadata_details_label"] {{
        background-color: {theme['card_bg']};
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        border: 1px solid {theme['border']};
    }}

    /* Contenedores de imágenes */
    QLabel[objectName="cover_label"], QLabel[objectName="artist_image_label"] {{
        background-color: {theme['card_bg']};
        border: 1px solid {theme['border']};
        border-radius: 8px;
        padding: 4px;
    }}
    
    /* ScrollAreas específicos */
    QScrollArea[objectName="info_scroll"], QScrollArea[objectName="metadata_scroll"] {{
        border: none;
        background-color: transparent;
    }}
    
    /* Checkbox de configuración avanzada */
    QCheckBox[objectName="advanced_settings_check"] {{
        color: {theme['fg']};
        spacing: 8px;
    }}
    
    QCheckBox[objectName="advanced_settings_check"]::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 3px;
        border: 1px solid {theme['border']};
    }}
    
    QCheckBox[objectName="advanced_settings_check"]::indicator:checked {{
        background-color: {theme['accent']};
    }}
    
    /* Contenedor de resultados y árbol */
    QWidget[objectName="results_tree_widget"] {{
        background-color: {theme['card_bg']};
        border-radius: 8px;
        border: 1px solid {theme['border']};
    }}
    
    QTreeWidget[objectName="results_tree_widget"] {{
        background-color: transparent;
        border: none;
    }}
    
    QTreeWidget[objectName="results_tree_widget"]::item {{
        padding: 4px;
        border-radius: 2px;
    }}
    
    QTreeWidget[objectName="results_tree_widget"]::item:selected {{
        background-color: {theme['selection']};
    }}
    """
    
    return base_style + module_specific_styles


# Clase para animaciones y efectos (ÚNICA Y CORREGIDA)
class ThemeEffects:
    @staticmethod
    def apply_button_hover_animation(button):
        """
        Aplica una animación de hover simple y funcional a un botón
        """
        # Guardar el estilo original
        original_stylesheet = button.styleSheet()
        
        def enterEvent(event):
            # Cambio de color simple al hacer hover (SIN transform)
            hover_style = original_stylesheet + """
                QPushButton {
                    background-color: rgba(61, 89, 161, 0.8) !important;
                    border: 1px solid #7aa2f7 !important;
                }
            """
            button.setStyleSheet(hover_style)
            
            # Llamar al evento original si existe
            if hasattr(type(button), "enterEvent"):
                super(type(button), button).enterEvent(event)
        
        def leaveEvent(event):
            # Restaurar estilo original
            button.setStyleSheet(original_stylesheet)
            
            # Llamar al evento original si existe
            if hasattr(type(button), "leaveEvent"):
                super(type(button), button).leaveEvent(event)
        
        # Reemplazar los métodos del botón
        button.enterEvent = enterEvent
        button.leaveEvent = leaveEvent

    @staticmethod
    def apply_ripple_effect(button):
        """
        Aplica un efecto de ondulación (ripple) simplificado y funcional
        """
        # Guardar el estilo original
        if not hasattr(button, '_original_stylesheet'):
            button._original_stylesheet = button.styleSheet()
        
        def on_button_pressed():
            # Obtener colores del tema actual (extraer del stylesheet del padre)
            accent_color = "#3d59a1"  # Color predeterminado
            
            # Aplicar estilo de presionado
            pressed_style = button._original_stylesheet + f"""
                QPushButton {{
                    background-color: {accent_color} !important;
                    color: #ffffff !important;
                }}
            """
            button.setStyleSheet(pressed_style)
            
            # Restaurar después de un tiempo
            QTimer.singleShot(150, lambda: button.setStyleSheet(button._original_stylesheet))
        
        # Conectar señal
        if button.pressed:
            button.pressed.connect(on_button_pressed)

    @staticmethod
    def apply_smooth_scroll_animation(scroll_area):
        """
        Aplica animación suave al scroll
        """
        def wheelEvent(event):
            # Obtener la scrollbar vertical
            scroll_bar = scroll_area.verticalScrollBar()
            current_value = scroll_bar.value()
            
            # Calcular nuevo valor
            delta = event.angleDelta().y()
            step = delta // 8  # Suavizar el movimiento
            new_value = current_value - step
            
            # Limitar valores
            new_value = max(0, min(scroll_bar.maximum(), new_value))
            
            # Crear animación
            animation = QPropertyAnimation(scroll_bar, b"value")
            animation.setDuration(150)
            animation.setStartValue(current_value)
            animation.setEndValue(new_value)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.start()
            
            # Guardar referencia para evitar que se elimine
            scroll_area._scroll_animation = animation
        
        # Reemplazar evento de rueda
        scroll_area.wheelEvent = wheelEvent


def apply_theme_to_widget(widget, theme_name):
    """
    Aplica un tema a un widget específico y todos sus hijos
    
    Args:
        widget: QWidget al que aplicar el tema
        theme_name: Nombre del tema a aplicar
    """
    # Obtener la hoja de estilos
    stylesheet = get_stylesheet(theme_name)
    
    # Aplicar al widget
    widget.setStyleSheet(stylesheet)
    
    # Aplicar efectos a widgets específicos
    apply_effects_to_widget(widget)


def apply_effects_to_widget(widget):
    """Aplica efectos a widgets específicos de forma recursiva"""
    from PyQt6.QtWidgets import QPushButton, QScrollArea
    
    # Aplicar efectos de hover a botones
    for button in widget.findChildren(QPushButton):
        if not hasattr(button, '_hover_effect_applied'):
            ThemeEffects.apply_button_hover_animation(button)
            button._hover_effect_applied = True
    
    # Aplicar scroll suave a scroll areas
    # for scroll_area in widget.findChildren(QScrollArea):
    #     if not hasattr(scroll_area, '_smooth_scroll_applied'):
    #         ThemeEffects.apply_smooth_scroll_animation(scroll_area)
    #         scroll_area._smooth_scroll_applied = True


def init_theme_system(app, initial_theme='Tokyo Night'):
    """
    Inicializa el sistema de temas en toda la aplicación
    
    Args:
        app: QApplication
        initial_theme: Tema inicial a aplicar
    """
    # Obtener la hoja de estilos
    stylesheet = get_stylesheet(initial_theme)
    
    # Aplicar a toda la aplicación
    app.setStyleSheet(stylesheet)
    
    return stylesheet


def get_theme_colors(theme_name):
    """
    Obtiene los colores de un tema específico
    
    Args:
        theme_name: Nombre del tema
        
    Returns:
        dict: Diccionario con los colores del tema
    """
    return THEMES.get(theme_name, THEMES['Tokyo Night'])


def update_widget_theme(widget, theme_name):
    """
    Actualiza el tema de un widget específico sin afectar a otros
    
    Args:
        widget: Widget a actualizar
        theme_name: Nombre del nuevo tema
    """
    apply_theme_to_widget(widget, theme_name)


# Clases personalizadas para widgets con animaciones

class DraggableTabBar(QTabBar):
    """TabBar que permite reordenar tabs arrastrando"""
    
    tab_moved_signal = pyqtSignal(int, int)  # from_index, to_index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(False)
        self.drag_start_position = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
            
        if not self.drag_start_position:
            super().mouseMoveEvent(event)
            return
            
        # Calcular distancia del arrastre
        distance = (event.position().toPoint() - self.drag_start_position).manhattanLength()
        
        if distance < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return
            
        # Permitir el arrastre nativo de PyQt6
        super().mouseMoveEvent(event)
        
    def tabMoved(self, from_index, to_index):
        """Evento cuando se mueve una tab"""
        super().tabMoved(from_index, to_index)
        self.tab_moved_signal.emit(from_index, to_index)


# Funciones de utilidad para Qt Designer

def setup_objectnames_for_theme(widget):
    """
    Configura objectNames automáticamente para widgets comunes
    que necesitan estilos específicos
    
    Args:
        widget: Widget padre a procesar
    """
    from PyQt6.QtWidgets import QPushButton, QLineEdit, QLabel, QTreeWidget, QScrollArea
    
    # Configurar botones con iconos
    for button in widget.findChildren(QPushButton):
        if not button.objectName():
            # Si el botón es pequeño, probablemente es un botón de icono
            if button.maximumWidth() <= 40 and button.maximumHeight() <= 40:
                button.setObjectName("icon_button")
            elif "search" in button.text().lower():
                button.setObjectName("search_button")
            elif "play" in button.text().lower():
                button.setObjectName("play_button")
    
    # Configurar campos de búsqueda
    for line_edit in widget.findChildren(QLineEdit):
        if not line_edit.objectName():
            if "search" in line_edit.placeholderText().lower():
                line_edit.setObjectName("search_box")
    
    # Configurar labels importantes
    for label in widget.findChildren(QLabel):
        if not label.objectName():
            text = label.text().lower()
            if "title" in text or "título" in text:
                label.setObjectName("title_label")
            elif "info" in text or "información" in text:
                label.setObjectName("info_label")
            elif "error" in text:
                label.setObjectName("error_label")
            elif "warning" in text or "advertencia" in text:
                label.setObjectName("warning_label")


def get_theme_icon_color(theme_name):
    """
    Obtiene el color apropiado para iconos según el tema
    
    Args:
        theme_name: Nombre del tema
        
    Returns:
        str: Color en formato hexadecimal
    """
    theme = THEMES.get(theme_name, THEMES['Tokyo Night'])
    return theme.get('icon_color', '#757575')


def is_dark_theme(theme_name):
    """
    Determina si un tema es oscuro o claro
    
    Args:
        theme_name: Nombre del tema
        
    Returns:
        bool: True si es tema oscuro, False si es claro
    """
    theme = THEMES.get(theme_name, THEMES['Tokyo Night'])
    bg_color = theme['bg']
    
    # Convertir hex a RGB y calcular luminancia
    hex_color = bg_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # Fórmula de luminancia
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    
    return luminance < 0.5


# Funciones auxiliares para reemplazar rutas de recursos
def replace_resource_paths(stylesheet, project_root):
    """
    Reemplaza las rutas de recursos en la hoja de estilos por rutas absolutas
    
    Args:
        stylesheet: Hoja de estilos CSS
        project_root: Ruta raíz del proyecto
        
    Returns:
        str: Hoja de estilos con rutas absolutas
    """
    return stylesheet.replace('PROJECT_ROOT', str(project_root))


# Ejemplo de uso y testing
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
    
    app = QApplication(sys.argv)
    
    # Inicializar sistema de temas
    init_theme_system(app, 'Tokyo Night')
    
    # Crear ventana de prueba
    window = QMainWindow()
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout(central_widget)
    
    # Añadir algunos widgets de prueba
    button1 = QPushButton("Botón Normal")
    button2 = QPushButton("🔍")
    button2.setObjectName("search_button")
    button2.setMaximumSize(40, 40)
    
    layout.addWidget(button1)
    layout.addWidget(button2)
    
    # Aplicar efectos
    apply_effects_to_widget(central_widget)
    
    window.show()
    sys.exit(app.exec())