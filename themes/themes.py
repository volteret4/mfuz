import os
from PyQt6.QtWidgets import QWidget, QApplication, QPushButton
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QSize, Qt, QPoint, QVariantAnimation

# Definición de temas con variables de color
THEMES = {
    "Tokyo Night": {
        'bg': '#1a1b26',              # Color de fondo principal
        'fg': '#a9b1d6',              # Color de texto principal
        'accent': '#7aa2f7',          # Color de acento para elementos destacados
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
        'card_bg': '#24283b',         # Fondo de tarjetas (blanco puro)
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
        'card_bg': '#ffffff',         # Fondo de tarjetas (blanco puro)
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
        'card_bg': '#ffffff',         # Fondo de tarjetas (blanco puro)
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
        background-color: {theme['secondary_bg']};
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
        background-color: {theme['secondary_bg']};
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
        border-radius: 19px;
        padding: 2px 2px;
        min-height: 38px;
        min-width: 38px;
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
    QPushButton[objectName^="icon_button"] {{
        border-radius: 16px;
        min-width: 32px;
        max-width: 32px;
        min-height: 32px;
        max-height: 32px;
        padding: 0px;
    }}
    
    /* Botones con iconos y texto */
    QPushButton[objectName^="action_button"] {{
        text-align: left;
        padding-left: 36px;
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
        background-color: {theme['secondary_bg']};
        alternate-background-color: {theme['alternate_row']};
        border: 1px solid {theme['border']};
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
        background-color: {theme['secondary_bg']};
    }}
    
    QListView::item:selected, QTreeView::item:selected, QTableView::item:selected {{
        background-color: {theme['selection']};
    }}
    
    QHeaderView::section {{
        background-color: {theme['header_bg']};
        color: {theme['fg']};
        padding: 5px;
        border: 1px solid {theme['border']};
    }}
    
    /* Deslizadores y barras de progreso */
    QScrollBar:vertical {{
        background-color: {theme['bg']};
        width: 12px;
        margin: 0px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {theme['border']};
        min-height: 20px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {theme['accent']};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        background-color: {theme['bg']};
        height: 12px;
        margin: 0px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {theme['border']};
        min-width: 20px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {theme['accent']};
    }}
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    
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
    
    QTabBar::tab {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 8px 12px;
        min-width: 80px;
    }}
    
    QTabBar::tab:selected {{
        background-color: {theme['bg']};
        border-bottom: 1px solid {theme['bg']};
    }}
    
    QTabBar::tab:hover:!selected {{
        background-color: {theme['button_hover']};
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
    
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid {theme['border']};
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        selection-background-color: {theme['selection']};
        selection-color: {theme['fg']};
        outline: 0;
    }}
    
    /* Spinbox */
    QSpinBox, QDoubleSpinBox {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        border-radius: 4px;
        padding: 5px;
        min-height: 28px;
    }}
    
    QSpinBox:hover, QDoubleSpinBox:hover {{
        border: 1px solid {theme['accent']};
    }}
    
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid {theme['border']};
        border-top-right-radius: 3px;
    }}
    
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        border-left: 1px solid {theme['border']};
        border-bottom-right-radius: 3px;
    }}
    
    /* Sliders */
    QSlider::groove:horizontal {{
        border: none;
        height: 4px;
        background-color: {theme['secondary_bg']};
        border-radius: 2px;
    }}
    
    QSlider::handle:horizontal {{
        background-color: {theme['accent']};
        border: none;
        width: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    
    QSlider::handle:horizontal:hover {{
        background-color: {theme['button_hover']};
    }}
    
    QSlider::groove:vertical {{
        border: none;
        width: 4px;
        background-color: {theme['secondary_bg']};
        border-radius: 2px;
    }}
    
    QSlider::handle:vertical {{
        background-color: {theme['accent']};
        border: none;
        height: 16px;
        margin: 0 -6px;
        border-radius: 8px;
    }}
    
    QSlider::handle:vertical:hover {{
        background-color: {theme['button_hover']};
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
        background-color: {theme['accent']};
    }}
    
    /* Calendar */
    QCalendarWidget QAbstractItemView:enabled {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        selection-background-color: {theme['selection']};
        selection-color: {theme['fg']};
    }}
    
    QCalendarWidget QWidget {{
        alternate-background-color: {theme['bg']};
    }}
    
    QCalendarWidget QToolButton {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        border-radius: 4px;
        padding: 6px;
        margin: 2px;
    }}
    
    QCalendarWidget QToolButton:hover {{
        background-color: {theme['button_hover']};
        border: 1px solid {theme['accent']};
    }}
    
    QCalendarWidget QMenu {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
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
    """
    
    # Estilos específicos para el módulo music_fuzzy_module
    music_fuzzy_style = f"""
    /* Estilos específicos para music_fuzzy_module */
    #music_fuzzy_module QTreeWidget {{
        alternate-background-color: {theme['alternate_row']};
    }}
    
    #music_fuzzy_module #search_box {{
        background-color: {theme['card_bg'] if 'card_bg' in theme else theme['secondary_bg']};
        border: 1px solid {theme['border']};
        border-radius: 18px;
        padding: 8px 16px;
        color: {theme['fg']};
    }}
    
    #music_fuzzy_module #search_box:focus {{
        border: 1px solid {theme['accent']};
    }}
    
    /* Botones circulares con iconos */
    #play_button, #folder_button, #spotify_button, #scrobble_button, #jaangle_button, #extra_button {{
        background-color: {theme['secondary_bg']};
        border: none;
        border-radius: 19px;
        min-width: 38px;
        min-height: 38px;
        max-width: 38px;
        max-height: 38px;
        padding: 0;
    }}
    
        /* Botones circulares con iconos */
    #allmusic_link_button, #bc_link_button, #soundcloud_link_button, #yt_link_button, #spot_link_button, #vimeo_link_button
    #boomkat_link_button, #juno_link_button, #discogs_link_button, #imdb_link_button, #lastfm_link_button, #mb_link_button,
    #prog_link_button, #rym_link_button, #ra_link_button, #setlist_link_button, #wiki_link_button, #whosampled_link_button,
    #bluesky_link_button, #fb_link_button, #ig_link_button, #mastodon_link_button, #myspace_link_button, #twitter_link_button, #tumblr_link_button   {{
        background-color: {theme['secondary_bg']};
        border: none;
        border-radius: 17px;
        min-width: 34px;
        min-height: 34px;
        max-width: 34px;
        max-height: 34px;
        padding: 0;
    }}

    #play_button:hover, #folder_button:hover, #spotify_button:hover, #scrobble_button:hover, 
    #jaangle_button:hover, #extra_button:hover,
    #allmusic_link_button:hover, #bc_link_button:hover, #soundcloud_link_button:hover, #yt_link_button:hover, #spot_link_button:hover, #vimeo_link_button:hover
    #boomkat_link_button:hover, #juno_link_button:hover, #discogs_link_button:hover, #imdb_link_button:hover, #lastfm_link_button:hover, #mb_link_button:hover,
    #prog_link_button:hover, #rym_link_button:hover, #ra_link_button:hover, #setlist_link_button:hover, #wiki_link_button:hover, #whosampled_link_button:hover,
    #bluesky_link_button:hover, #fb_link_button:hover, #ig_link_button:hover, #mastodon_link_button:hover, #myspace_link_button:hover, #twitter_link_button:hover, #tumblr_link_button:hover {{
        background-color: {theme['button_hover']};
        border: 1px solid {theme['accent']};
    }}
    
    /* Contenedores de imágenes */
    #cover_label, #artist_image_label {{
        background-color: {theme['card_bg'] if 'card_bg' in theme else theme['secondary_bg']};
        border: 1px solid {theme['border']};
        border-radius: 8px;
        padding: 4px;
    }}
    
    /* ScrollAreas */
    #info_scroll, #metadata_scroll {{
        border: none;
        background-color: transparent;
    }}
    
    /* Etiquetas informativas */
    #info_label {{
        color: {theme['fg']};
        padding: 8px;
        background-color: {theme['card_bg'] if 'card_bg' in theme else theme['secondary_bg']};
        border-radius: 4px;
        margin-bottom: 4px;
    }}
    
    #metadata_details_label {{
        color: {theme['fg']};
        padding: 12px;
        background-color: {theme['card_bg'] if 'card_bg' in theme else theme['secondary_bg']};
        border-radius: 8px;
    }}
    
    /* Checkbox de configuración avanzada */
    #advanced_settings_check {{
        color: {theme['fg']};
        spacing: 8px;
    }}
    
    #advanced_settings_check::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 3px;
        border: 1px solid {theme['border']};
    }}
    
    #advanced_settings_check::indicator:checked {{
        background-color: {theme['accent']};
    }}
    
    /* Contenedor de resultados y árbol */
    #results_tree_container {{
        background-color: {theme['card_bg'] if 'card_bg' in theme else theme['secondary_bg']};
        border-radius: 8px;
        border: 1px solid {theme['border']};
    }}
    
    #results_tree {{
        background-color: transparent;
        border: none;
    }}
    
    #results_tree::item {{
        padding: 4px;
        border-radius: 2px;
    }}
    
    #results_tree::item:selected {{
        background-color: {theme['selection']};
    }}
    
    /* Botones de acción */
    QPushButton[objectName^="action_button"] {{
        background-color: {theme['card_bg'] if 'card_bg' in theme else theme['secondary_bg']};
        border: 1px solid {theme['border']};
        border-radius: 18px;
        padding: 6px 12px;
        text-align: center;
    }}
    
    QPushButton[objectName^="action_button"]:hover {{
        background-color: {theme['button_hover']};
        border: 1px solid {theme['accent']};
    }}
    """
    
    # Estilos específicos para TabManager
    tab_manager_style = f"""
    /* Estilos específicos para TabManager */
    #tab_widget QTabBar::tab {{
        background-color: {theme['secondary_bg']};
        color: {theme['fg']};
        border: none;
        padding: 8px 16px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}
    
    #tab_widget QTabBar::tab:selected {{
        background-color: {theme['accent']};
        color: {theme['bg']};
    }}
    
    #tab_widget QTabBar::tab:hover:!selected {{
        background-color: {theme['button_hover']};
    }}
    
    #tab_widget QTabWidget::pane {{
        border: none;
    }}
    """
    
    # Combinamos todos los estilos
    return base_style + music_fuzzy_style + tab_manager_style


# Clase para animaciones y efectos
class ThemeEffects:
    @staticmethod
    def apply_button_hover_animation(button):
        """
        Aplica una animación de hover a un botón
        
        Args:
            button: QPushButton al que aplicar la animación
        """

        
        # Guardar tamaño original
        original_size = button.size()
        
        def enterEvent(event):
            # Animación de expansión
            animation = QPropertyAnimation(button, b"size")
            animation.setDuration(150)
            animation.setStartValue(button.size())
            
            # Calcular nuevo tamaño (103% del original)
            new_width = int(original_size.width() * 1.03)
            new_height = int(original_size.height() * 1.03)
            animation.setEndValue(QSize(new_width, new_height))
            
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.start()
            
            # Llamar al evento original si existe
            if hasattr(type(button), "enterEvent"):
                type(button).enterEvent(button, event)
        
        def leaveEvent(event):
            # Animación de contracción
            animation = QPropertyAnimation(button, b"size")
            animation.setDuration(150)
            animation.setStartValue(button.size())
            animation.setEndValue(original_size)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.start()
            
            # Llamar al evento original si existe
            if hasattr(type(button), "leaveEvent"):
                type(button).leaveEvent(button, event)
        
        # Reemplazar los métodos del botón
        button.enterEvent = enterEvent
        button.leaveEvent = leaveEvent

    @staticmethod
    def apply_ripple_effect(button):
        """
        Aplica un efecto de ondulación (ripple) simplificado a un botón, 
        compatible con cualquier versión de PyQt.
        
        Args:
            button: QPushButton al que aplicar el efecto
        """
        from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve
        
        # Obtener el tema actual del botón mediante su stylesheet
        button_style = button.styleSheet()
        
        # Guardar el estilo original
        original_stylesheet = button.styleSheet()
        
        def on_button_pressed():
            # Guardar el estilo original si no está guardado
            if not hasattr(button, '_original_stylesheet'):
                button._original_stylesheet = button.styleSheet()
            
            # Obtener el color de acento del tema actual
            # Esto extrae el color de acento del estilo del botón, o usa un color predeterminado
            accent_color = "#7aa2f7"  # Valor predeterminado de Tokyo Night
            bg_color = "#1a1b26"      # Valor predeterminado de Tokyo Night
            
            # Intentar encontrar el color de acento en el estilo o el estilo del padre
            for stylesheet in [button.styleSheet(), button.parent().styleSheet() if button.parent() else ""]:
                if "QPushButton:hover" in stylesheet and "background-color:" in stylesheet:
                    import re
                    match = re.search(r'background-color:\s*(#[0-9a-fA-F]{6})', stylesheet)
                    if match:
                        accent_color = match.group(1)
                        break
            
            # Aplicar estilo de presionado (simulando ripple)
            button.setStyleSheet(button._original_stylesheet + """
                QPushButton {
                    background-color: """ + accent_color + """ !important;
                    color: #ffffff !important;
                }
            """)
            
            # Programar temporizador para restaurar el estilo original
            QTimer.singleShot(300, restore_style)
        
        def restore_style():
            # Restaurar el estilo original con una transición visual
            button.setStyleSheet(button._original_stylesheet)
        
        # Conectar el clic del botón al efecto
        button.pressed.connect(on_button_pressed)



def apply_theme(widget, theme_name):
    """
    Aplica un tema a un widget y todos sus hijos recursivamente
    
    Args:
        widget: QWidget al que aplicar el tema
        theme_name: Nombre del tema a aplicar
    """
    # Obtener la hoja de estilos
    stylesheet = get_stylesheet(theme_name)
    
    # Aplicar al widget
    widget.setStyleSheet(stylesheet)
    
    # Aplicar efectos a widgets específicos
    apply_effects(widget)


def apply_effects(widget):
    """
    Aplica efectos especiales a widgets específicos
    
    Args:
        widget: QWidget raíz donde buscar widgets para aplicar efectos
    """
    # Obtener todos los botones con objectName específico para animaciones
    for button in widget.findChildren(QPushButton, "animated_button*"):
        ThemeEffects.apply_button_hover_animation(button)


# Función auxiliar para reemplazar rutas de recursos en la hoja de estilos
def replace_resource_paths(stylesheet, project_root):
    """
    Reemplaza las rutas de recursos en la hoja de estilos por rutas absolutas
    
    Args:
        stylesheet: Hoja de estilos CSS
        project_root: Ruta raíz del proyecto
        
    Returns:
        str: Hoja de estilos con rutas absolutas
    """
    return stylesheet.replace('PROJECT_ROOT', project_root)


def init_theme_system(app, initial_theme='Tokyo Night'):
    """
    Inicializa el sistema de temas en toda la aplicación
    
    Args:
        app: QApplication
        initial_theme: Tema inicial a aplicar
    """
    # Obtener la ruta del proyecto
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Obtener la hoja de estilos y reemplazar rutas
    stylesheet = get_stylesheet(initial_theme)
    stylesheet = replace_resource_paths(stylesheet, project_root)
    
    # Aplicar a toda la aplicación
    app.setStyleSheet(stylesheet)


if __name__ == "__main__":
    # Ejemplo de uso
    app = QApplication([])
    init_theme_system(app, 'Tokyo Night')
    
    # Resto del código de la aplicación
    sys.exit(app.exec())