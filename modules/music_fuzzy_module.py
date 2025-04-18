import sys
import os
import re
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import sqlite3
import json
from PyQt6 import uic
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
                           QLabel, QScrollArea, QSplitter, QTextEdit, QTableWidget,
                           QHeaderView, QTreeWidget, QTreeWidgetItem, QAbstractItemView,
                           QMenu, QFrame, QStyle, QApplication, QCheckBox, QSizePolicy,
                           QTabWidget, QSpinBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QPixmap, QShortcut, QKeySequence
import subprocess
import importlib.util
import glob
import random
import urllib.parse
import time
import logging
import traceback

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule, THEMES, PROJECT_ROOT  # Importar la clase base
import resources_rc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


reproductor = 'deadbeef'


class GroupedListItem(QTreeWidgetItem):
    def __init__(self, text, is_header=False, paths=None):
        # QTreeWidgetItem no acepta texto como primer argumento
        # Usamos una lista de strings para las columnas
        super().__init__([text])  # Pasar el texto como una lista para la primera columna

        self.is_header = is_header
        self.paths = paths or []

        if is_header:
            font = self.font(0)  # El font debe especificar la columna (0)
            font.setBold(True)
            font.setPointSize(font.pointSize() + 2)
            self.setFont(0, font)  # Establecer la fuente para la columna 0

            # Si quieres también establecer colores de fondo y texto:
            # self.setBackground(0, QColor(theme['secondary_bg']))
            # self.setForeground(0, QColor(theme['accent']))

class SearchParser:
    def __init__(self):
        self.filters = {
            'a:': 'artist',
            'b:': 'album',
            'g:': 'genre',
            'l:': 'label',
            't:': 'title',
            'aa:': 'album_artist',
            'br:': 'bitrate',
            'd:': 'date',
            'w:': 'weeks',      # Últimas X semanas
            'm:': 'months',     # Últimos X meses
            'y:': 'years',      # Últimos X años
            'am:': 'added_month', # Añadido en mes X del año Y
            'ay:': 'added_year'   # Añadido en año Z
        }

        # Caché simple para consultas frecuentes
        self.cache = {}
        self.cache_size = 20

    def build_sql_conditions(self, parsed_query: dict) -> tuple:
        """Construye las condiciones SQL y parámetros basados en la query parseada."""
        if not parsed_query:
            return [], []

        conditions = []
        params = []

        # Procesar filtros específicos
        for field, value in parsed_query['filters'].items():
            if field in ['weeks', 'months', 'years']:
                try:
                    value = int(value)
                    if field == 'weeks':
                        conditions.append("s.last_modified >= datetime('now', '-' || ? || ' weeks')")
                    elif field == 'months':
                        conditions.append("s.last_modified >= datetime('now', '-' || ? || ' months')")
                    else:  # years
                        conditions.append("s.last_modified >= datetime('now', '-' || ? || ' years')")
                    params.append(value)
                except ValueError:
                    print(f"Valor inválido para {field}: {value}")
                    continue
            elif field == 'added_month':
                try:
                    month, year = value.split('/')
                    month = int(month)
                    year = int(year)
                    conditions.append("strftime('%m', s.last_modified) = ? AND strftime('%Y', s.last_modified) = ?")
                    params.extend([f"{month:02d}", str(year)])
                except (ValueError, TypeError):
                    print(f"Formato inválido para mes/año: {value}")
                    continue
            elif field == 'added_year':
                try:
                    year = int(value)
                    conditions.append("strftime('%Y', s.last_modified) = ?")
                    params.append(str(year))
                except ValueError:
                    print(f"Año inválido: {value}")
                    continue
            elif field == 'bitrate':
                # Manejar rangos de bitrate (>192, <192, =192)
                if value.startswith('>'):
                    conditions.append(f"s.{field} > ?")
                    params.append(int(value[1:]))
                elif value.startswith('<'):
                    conditions.append(f"s.{field} < ?")
                    params.append(int(value[1:]))
                else:
                    conditions.append(f"s.{field} = ?")
                    params.append(int(value))
            else:
                conditions.append(f"s.{field} LIKE ?")
                params.append(f"%{value}%")

        # Procesar términos generales
        if parsed_query['general']:
            general_fields = ['artist', 'title', 'album', 'genre', 'label', 'album_artist']
            general_conditions = []
            for field in general_fields:
                general_conditions.append(f"s.{field} LIKE ?")
                params.append(f"%{parsed_query['general']}%")
            if general_conditions:
                conditions.append(f"({' OR '.join(general_conditions)})")

        return conditions, params

    def parse_query(self, query: str) -> dict:
        """Parsea la query y devuelve diccionario con filtros y término general."""
        # Verificar caché
        if query in self.cache:
            return self.cache[query]

        filters = {}
        general_terms = []
        current_term = ''
        i = 0

        while i < len(query):
            # Buscar si hay un filtro al inicio de esta parte
            found_filter = False
            for prefix, field in self.filters.items():
                if query[i:].startswith(prefix):
                    # Si hay un término acumulado, añadirlo a términos generales
                    if current_term.strip():
                        general_terms.append(current_term.strip())
                        current_term = ''

                    # Avanzar más allá del prefijo
                    i += len(prefix)
                    # Recoger el valor hasta el siguiente filtro o fin de cadena
                    value = ''
                    while i < len(query):
                        # Comprobar si empieza otro filtro
                        next_filter = False
                        for next_prefix in self.filters:
                            if query[i:].startswith(next_prefix):
                                next_filter = True
                                break
                        if next_filter:
                            break
                        value += query[i]
                        i += 1

                    value = value.strip()
                    if value:
                        filters[field] = value
                    found_filter = True
                    break

            if not found_filter and i < len(query):
                current_term += query[i]
                i += 1

        # Añadir el último término si existe
        if current_term.strip():
            general_terms.append(current_term.strip())

        result = {
            'filters': filters,
            'general': ' '.join(general_terms)
        }

        # Actualizar caché
        if len(self.cache) >= self.cache_size:
            # Eliminar el primero si está lleno
            self.cache.pop(next(iter(self.cache)))
        self.cache[query] = result

        return result



class MusicBrowser(BaseModule):
    def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
        """
        Inicializa el módulo de exploración de música.

        Args:
            parent (QWidget, optional): Widget padre. Defaults to None.
            theme (str, optional): Tema de la interfaz. Defaults to 'Tokyo Night'.
            db_path (str, optional): Ruta al archivo de la base de datos de
                música. Defaults to ''.
            font_family (str, optional): Familia de fuente para la interfaz.
                Defaults to 'Inter'.
            artist_images_dir (str, optional): Directorio para las imágenes de
                artistas. Defaults to ''.
        """
        # Extraer los argumentos específicos de MusicBrowser
        self.db_path = kwargs.pop('db_path', '')
        self.font_family = kwargs.pop('font_family', 'Inter')
        self.artist_images_dir = kwargs.pop('artist_images_dir', '')
        self.hotkeys_config = kwargs.pop('hotkeys', None)

        self.available_themes = kwargs.pop('temas', [])
        self.selected_theme = kwargs.pop('tema_seleccionado', theme)
        self.boton_pulsado = 0  # Estado inicial

        # Inicializar atributos importantes con valores por defecto
        self.results_tree = None
        self.results_tree_widget = None
        self.results_tree_container = None
        self.lastfm_label = None
        self.metadata_label = None
        self.info_widget = None
        self.cover_label = None
        self.artist_image_label = None
        self.advanced_buttons = []
        self.ui_components_loaded = {'main': False, 'tree': False, 'info': False, 'advanced': False}

        # Llamar al constructor de la clase padre con los argumentos restantes
        super().__init__(parent=parent, theme=theme, **kwargs)

        # Inicializar componentes específicos de MusicBrowser
        self.search_parser = SearchParser()
        self.setup_hotkeys(self.hotkeys_config)

    def init_ui(self):
        """Inicializa la interfaz del módulo."""
        # Limpiar el layout existente si hay alguno
        if self.layout():
            QWidget().setLayout(self.layout())

        # Crear un layout principal para el módulo
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Cargar la UI principal
        ui_file_path = os.path.join(PROJECT_ROOT, "ui", "music_fuzzy_module.ui")
        if os.path.exists(ui_file_path):
            try:
                # Cargar el archivo UI principal
                self.main_ui = QWidget()
                uic.loadUi(ui_file_path, self.main_ui)

                # Añadir el widget principal al layout
                main_layout.addWidget(self.main_ui)

                # Transferir referencias importantes
                self._setup_references()
                self.ui_components_loaded['main'] = True
                print(f"UI MusicBrowser cargada desde {ui_file_path}")
            except Exception as e:
                print(f"Error cargando UI MusicBrowser: {e}")
                traceback.print_exc()
                self._fallback_init_ui()
        else:
            print(f"Archivo UI MusicBrowser no encontrado: {ui_file_path}")
            self._fallback_init_ui()

        # Cargar otros componentes de la UI
        self._load_results_tree()

        # Inicializar con NULL los widgets de información para evitar errores
        self.lastfm_label = None
        self.metadata_label = None
        self.links_label = None
        self.wikipedia_artist_label = None
        self.wikipedia_album_label = None

        # Configurar los widgets de información
        self.setup_info_widget()

        # Verificar que los widgets importantes se configuraron
        if not self.lastfm_label or not self.metadata_label:
            print("ADVERTENCIA: Los widgets de información no se configuraron correctamente.")
            # Forzar el método fallback
            self._fallback_setup_info_widget()

        # Configuración común
        self.connect_signals()
        self.apply_theme()

        # Inicializar el estado de los ajustes avanzados
        self._advanced_settings_loaded = False

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
            ui_widget = QWidget()
            uic.loadUi(ui_file_path, ui_widget)

            # Verificar widgets requeridos si se especifican
            if required_widgets:
                missing_widgets = []
                for widget_name in required_widgets:
                    widget = ui_widget.findChild(QWidget, widget_name)
                    if widget:
                        # Transferir referencias al widget a self
                        setattr(self, widget_name, widget)
                    else:
                        missing_widgets.append(widget_name)

                if missing_widgets:
                    print(f"Widgets requeridos no encontrados: {', '.join(missing_widgets)}")
                    return False

            # Añadir el widget completo al layout principal si existe
            if hasattr(self, 'layout') and self.layout():
                self.layout().addWidget(ui_widget)
                # Guardar una referencia al widget UI principal
                self.ui_widget = ui_widget

            print(f"UI cargada desde {ui_file_path}")
            return True
        except Exception as e:
            print(f"Error cargando UI desde archivo: {e}")
            traceback.print_exc()
            return False


    def _fallback_init_ui(self):
        """Método de respaldo para crear la UI manualmente si el archivo UI falla."""
        # Verificar si ya existe un layout
        if self.layout():
            # Si ya hay un layout, no creamos uno nuevo
            # Simplemente limpiamos los widgets existentes
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Contenedor superior
        self.top_container = QFrame()
        self.top_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.top_container.setFrameShadow(QFrame.Shadow.Raised)
        self.top_container.setMaximumHeight(50)
        top_layout = QVBoxLayout(self.top_container)
        top_layout.setSpacing(5)

        # Inicializar los botones antes de usarlos
        self.play_button = QPushButton('Reproducir')
        self.folder_button = QPushButton('Abrir Carpeta')
        self.custom_button1 = QPushButton('Reproduciendo')
        self.custom_button2 = QPushButton('Script 2')
        self.custom_button3 = QPushButton('Script 3')

        # Barra de búsqueda y checkbox para ajustes avanzados
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('a:artista - b:álbum - g:género - l:sello - t:título - aa:album-artist - br:bitrate - d:fecha - w:semanas - m:meses - y:años - am:mes/año - ay:año')
        search_layout.addWidget(self.search_box)

        # Botones básicos (siempre visibles)
        for button in [self.play_button, self.folder_button]:
            button.setFixedWidth(100)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            search_layout.addWidget(button)

        # Checkbox para ajustes avanzados
        self.advanced_settings_check = QCheckBox("Más")
        self.advanced_settings_check.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        search_layout.addWidget(self.advanced_settings_check)

        # Botones avanzados (inicialmente ocultos)
        self.advanced_buttons = []
        for button in [self.custom_button1, self.custom_button2, self.custom_button3]:
            button.setFixedWidth(100)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.hide()  # Ocultar inicialmente
            search_layout.addWidget(button)
            self.advanced_buttons.append(button)

        top_layout.addLayout(search_layout)
        layout.addWidget(self.top_container)

        # Contenedor para ajustes avanzados (inicialmente oculto)
        self.advanced_settings_container = QFrame()
        self.advanced_settings_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.advanced_settings_container.setFrameShadow(QFrame.Shadow.Raised)
        self.advanced_settings_container.hide()
        layout.addWidget(self.advanced_settings_container)

        # Splitter principal: árbol de resultados y panel de detalles
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panel izquierdo (contenedor para el árbol de resultados)
        self.results_tree_container = QFrame()
        self.results_tree_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.results_tree_container.setFrameShadow(QFrame.Shadow.Raised)
        self.results_tree_container.setMinimumWidth(300)
        self.main_splitter.addWidget(self.results_tree_container)

        # Panel derecho (detalles)
        details_widget = QFrame()
        details_widget.setFrameShape(QFrame.Shape.StyledPanel)
        details_widget.setFrameShadow(QFrame.Shadow.Raised)
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


        # Primer tab (panel original de detalles)
        details_tab = QWidget()
        details_tab_layout = QVBoxLayout(details_tab)
        details_tab_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter vertical para separar imágenes y texto
        self.details_splitter = QSplitter(Qt.Orientation.Vertical)

        # Contenedor superior para las imágenes (colocadas horizontalmente)
        images_container = QFrame()
        images_container.setFrameShape(QFrame.Shape.StyledPanel)
        images_container.setFrameShadow(QFrame.Shadow.Raised)
        images_layout = QHBoxLayout(images_container)
        images_layout.setSpacing(10)
        images_layout.setContentsMargins(45, 5, 45, 5)
        images_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Cover del álbum
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(200, 200)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("border: 1px solid #333;")
        images_layout.addWidget(self.cover_label)

        # Añadir margen entre las imagenes
        images_layout.addSpacing(60)  # Añade un espacio fijo de 60 píxeles

        # Imagen del artista
        self.artist_image_label = QLabel()
        self.artist_image_label.setFixedSize(200, 200)
        self.artist_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artist_image_label.setStyleSheet("border: 1px solid #333;")
        images_layout.addWidget(self.artist_image_label)

        # Añadir contenedor de botones verticales a la derecha
        buttons_container = QFrame()
        buttons_container.setFrameShape(QFrame.Shape.NoFrame)
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['bg']};
                border-radius: 25px;
                padding: 8px 16px;
                border: 2px;
            }}
            
            
            QPushButton:hover {{
                background-color: {theme['button_hover']};
                margin: 1px;
                margin-top: 0px;
                margin-bottom: 3px;
            }}
            
            QPushButton:pressed {{
                background-color: {theme['selection']};
                border: none;
            }}
            
        """)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        # Botón para enviar a Spotify
        self.spotify_button = QPushButton("Enviar a Spotify")
        self.spotify_button.setFixedWidth(120)
        buttons_layout.addWidget(self.spotify_button)

        buttons_layout.addStretch()

        # Añadir el contenedor de botones al layout de imágenes
        images_layout.addWidget(buttons_container)
        # Añadir el contenedor de imágenes al splitter vertical
        self.details_splitter.addWidget(images_container)

        # Contenedor para el scroll con la información
        info_container = QFrame()
        info_container.setFrameShape(QFrame.Shape.StyledPanel)
        info_container.setFrameShadow(QFrame.Shadow.Raised)
        info_container_layout = QVBoxLayout(info_container)
        info_container_layout.setContentsMargins(5, 5, 5, 5)
        info_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # ScrollArea para la información
        self.info_scroll = QScrollArea()
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.info_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.info_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.info_scroll.setMinimumWidth(600)

        info_container_layout.addWidget(self.info_scroll)

        # Añadir el contenedor de información al splitter vertical
        self.details_splitter.addWidget(info_container)

        # Configurar proporciones iniciales del splitter vertical (imágenes/información)
        self.details_splitter.setSizes([200, 800])

        # Añadir el splitter vertical al layout del tab de detalles
        details_tab_layout.addWidget(self.details_splitter)

        # Segundo tab (Playlist)
        playlist_tab = QWidget()
        playlist_layout = QVBoxLayout(playlist_tab)
        playlist_layout.setContentsMargins(10, 10, 10, 10)



        # Contenedor para los botones de la playlist
        playlist_buttons_container = QFrame()
        playlist_buttons_container.setFrameShape(QFrame.Shape.NoFrame)
        playlist_buttons_layout = QHBoxLayout(playlist_buttons_container)
        playlist_buttons_layout.setSpacing(10)

        # Botones para la playlist
        self.clear_playlist_button = QPushButton("Vaciar Playlist")
        playlist_buttons_layout.addWidget(self.clear_playlist_button)

        self.playlist_button1 = QPushButton("Función 1")
        playlist_buttons_layout.addWidget(self.playlist_button1)

        self.playlist_button2 = QPushButton("Función 2")
        playlist_buttons_layout.addWidget(self.playlist_button2)

        self.playlist_button3 = QPushButton("Función 3")
        playlist_buttons_layout.addWidget(self.playlist_button3)

        self.playlist_button4 = QPushButton("Función 4")
        playlist_buttons_layout.addWidget(self.playlist_button4)

        playlist_layout.addWidget(playlist_buttons_container)



        # Añadir el panel de detalles al splitter principal
        self.main_splitter.addWidget(details_widget)

        # Configurar proporciones iniciales del splitter principal (árbol/detalles)
        self.main_splitter.setSizes([400, 800])

        # Añadir el splitter principal al layout de la ventana
        layout.addWidget(self.main_splitter)

        # El árbol de resultados se cargará posteriormente con load_results_tree_ui


    def setup_hotkeys(self, hotkeys_config=None):
        """
        Configura atajos de teclado desde la configuración JSON
        
        Args:
            hotkeys_config (dict): Diccionario con configuración de hotkeys
                formato: {"action_name": "shortcut_key", ...}
        """
        # Valores predeterminados si no se proporciona configuración
        default_hotkeys = {
            "open_folder": "Ctrl+O",
            "play_selected": "Return",
            "spotify": "Ctrl+S",
            "jaangle": "Ctrl+J",
            "search_focus": "Ctrl+F",
            # Añade más según necesites
        }
        
        # Usar configuración proporcionada o predeterminada
        hotkeys = hotkeys_config or default_hotkeys
        
        # Crear y conectar los atajos
        self.shortcuts = {}
        
        # Abrir carpeta (Ctrl+O)
        self.shortcuts["open_folder"] = QShortcut(QKeySequence(hotkeys["open_folder"]), self)
        self.shortcuts["open_folder"].activated.connect(self.open_selected_folder)
        
        # Reproducir seleccionado (Enter)
        self.shortcuts["play_selected"] = QShortcut(QKeySequence(hotkeys["play_selected"]), self)
        self.shortcuts["play_selected"].activated.connect(self.play_selected_item)
        
        # Spotify (Ctrl+S)
        if hasattr(self, "spotify_button") and self.spotify_button:
            self.shortcuts["spotify"] = QShortcut(QKeySequence(hotkeys["spotify"]), self)
            self.shortcuts["spotify"].activated.connect(self.handle_spotify_button)
        
        # Jaangle (Ctrl+J) - Ejemplo para implementación futura
        # self.shortcuts["jaangle"] = QShortcut(QKeySequence(hotkeys["jaangle"]), self)
        # self.shortcuts["jaangle"].activated.connect(self.handle_jaangle_button)
        
        # Establecer el foco en el cuadro de búsqueda (Ctrl+F)
        self.shortcuts["search_focus"] = QShortcut(QKeySequence(hotkeys["search_focus"]), self)
        self.shortcuts["search_focus"].activated.connect(self.search_box.setFocus)
        
        print(f"Hotkeys configurados: {list(self.shortcuts.keys())}")



    def is_tree_valid(self):
        """Verifica si el árbol está disponible y válido."""
        if not hasattr(self, 'results_tree') or self.results_tree is None:
            print("El árbol de resultados no existe o es None")
            return False

        # Verificar si no ha sido destruido (si tiene el método)
        if hasattr(self.results_tree, 'isDestroyed') and self.results_tree.isDestroyed():
            print("El árbol de resultados ha sido destruido")
            return False

        return True


    def _create_fallback_tree(self):
        """Crea un árbol de resultados básico como respaldo si falla la carga dinámica."""
        # Asegurarse de que el contenedor tiene un layout
        if not self.results_tree_container.layout():
            container_layout = QVBoxLayout(self.results_tree_container)
            container_layout.setContentsMargins(0, 0, 0, 0)
        else:
            container_layout = self.results_tree_container.layout()
            # Limpiar cualquier widget previo
            while container_layout.count():
                item = container_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # Crear un QTreeWidget básico
        self.results_tree = QTreeWidget()
        self.results_tree.setAlternatingRowColors(False)
        self.results_tree.setHeaderHidden(False)
        self.results_tree.setColumnCount(3)
        self.results_tree.setHeaderLabels(["Artistas / Álbumes / Canciones", "Año", "Género"])

        # Configurar la selección
        self.results_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Añadir al layout existente
        container_layout.addWidget(self.results_tree)
        print("Árbol de resultados fallback creado y añadido al layout")

        # Configurar eventos básicos
        self.results_tree.currentItemChanged.connect(self.handle_tree_item_change)
        self.results_tree.itemDoubleClicked.connect(self.handle_tree_item_double_click)
        self.results_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_tree.customContextMenuRequested.connect(self.show_tree_context_menu)

    def _setup_references(self):
        """Configura las referencias a los widgets cargados desde la UI principal."""
        # Botones y controles principales
        self.search_box = self.main_ui.findChild(QLineEdit, "search_box")
        self.play_button = self.main_ui.findChild(QPushButton, "play_button")
        self.folder_button = self.main_ui.findChild(QPushButton, "folder_button")
        self.spotify_button = self.main_ui.findChild(QPushButton, "spotify_button")
        self.advanced_settings_check = self.main_ui.findChild(QCheckBox, "advanced_settings_check")

        # Botones avanzados
        self.custom_button1 = self.main_ui.findChild(QPushButton, "custom_button1")
        self.custom_button2 = self.main_ui.findChild(QPushButton, "custom_button2")
        self.custom_button3 = self.main_ui.findChild(QPushButton, "custom_button3")
        self.advanced_buttons = [self.custom_button1, self.custom_button2, self.custom_button3]

        # Contenedores
        self.top_container = self.main_ui.findChild(QFrame, "top_container")
        self.advanced_settings_container = self.main_ui.findChild(QFrame, "advanced_settings_container")
        self.results_tree_container = self.main_ui.findChild(QFrame, "results_tree_container")

        # Splitters
        self.main_splitter = self.main_ui.findChild(QSplitter, "main_splitter")
        self.details_splitter = self.main_ui.findChild(QSplitter, "details_splitter")

        # Etiquetas de imágenes
        self.cover_label = self.main_ui.findChild(QLabel, "cover_label")
        self.artist_image_label = self.main_ui.findChild(QLabel, "artist_image_label")

        # Scroll de información
        self.info_scroll = self.main_ui.findChild(QScrollArea, "info_scroll")
        self.metadata_scroll = self.main_ui.findChild(QScrollArea, "metadata_scroll")

        # Verificar que los scrolls existen, si no, crearlos manualmente
        if not self.info_scroll:
            print("info_scroll no encontrado, creando uno manualmente")
            # Buscar un contenedor adecuado para añadir el scroll
            container = self.main_ui.findChild(QFrame, "info_container")
            if container:
                self.info_scroll = QScrollArea(container)
                self.info_scroll.setWidgetResizable(True)
                self.info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                self.info_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

                # Añadir al layout del contenedor
                if container.layout():
                    container.layout().addWidget(self.info_scroll)
                else:
                    layout = QVBoxLayout(container)
                    layout.addWidget(self.info_scroll)

        if not self.metadata_scroll:
            print("metadata_scroll no encontrado, creando uno manualmente")
            # Buscar un contenedor adecuado para añadir el scroll
            container = self.main_ui.findChild(QFrame, "images_container")
            if container:
                self.metadata_scroll = QScrollArea(container)
                self.metadata_scroll.setWidgetResizable(True)
                self.metadata_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                self.metadata_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

                # Añadir al layout del contenedor
                if container.layout():
                    container.layout().addWidget(self.metadata_scroll)



    def _load_results_tree(self):
        """Carga el árbol de resultados desde un archivo UI separado."""
        # Verificar que el contenedor existe
        if not hasattr(self, 'results_tree_container') or not self.results_tree_container:
            print("Error: results_tree_container no existe")
            return

        # Si ya existe un layout en el contenedor, eliminarlo
        if self.results_tree_container.layout():
            while self.results_tree_container.layout().count():
                item = self.results_tree_container.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(self.results_tree_container.layout())

        # Crear un nuevo layout para el contenedor
        container_layout = QVBoxLayout(self.results_tree_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Cargar el widget del árbol desde un archivo UI separado
        ui_file_path = os.path.join(PROJECT_ROOT, "ui", "music_fuzzy_results_tree.ui")
        if os.path.exists(ui_file_path):
            try:
                # Cargar el archivo UI
                self.results_tree_widget = QWidget()
                uic.loadUi(ui_file_path, self.results_tree_widget)

                # Obtener la referencia al árbol y añadirlo al layout
                self.results_tree = self.results_tree_widget.findChild(QTreeWidget, "results_tree")
                if self.results_tree:
                    container_layout.addWidget(self.results_tree_widget)
                    self.results_tree.setColumnWidth(0, 150)
                    self.results_tree.setColumnWidth(1, 50)
                    self.results_tree.setColumnWidth(2, 80)

                    # Configurar eventos del árbol
                    self.results_tree.currentItemChanged.connect(self.handle_tree_item_change)
                    self.results_tree.itemDoubleClicked.connect(self.handle_tree_item_double_click)
                    self.results_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    self.results_tree.customContextMenuRequested.connect(self.show_tree_context_menu)

                    self.ui_components_loaded['tree'] = True
                    print("Árbol de resultados cargado desde UI y añadido al layout")
                else:
                    print("No se encontró el widget 'results_tree' en el archivo UI")
                    self._create_fallback_tree()
            except Exception as e:
                print(f"Error cargando UI del árbol de resultados: {e}")
                traceback.print_exc()
                self._create_fallback_tree()
        else:
            print(f"Archivo UI del árbol no encontrado: {ui_file_path}")
            self._create_fallback_tree()


    def _setup_widgets(self):
        """Configuración adicional para los widgets después de cargar la UI."""
        # Configurar el combo de meses solo si existe
        if hasattr(self, 'month_combo'):
            if self.month_combo.count() == 0:
                self.month_combo.addItems([f"{i:02d}" for i in range(1, 13)])

        # Configurar los spinners de año solo si existen
        if hasattr(self, 'year_spin'):
            current_year = QDate.currentDate().year()
            if self.year_spin.value() == 0:
                self.year_spin.setValue(current_year)

        if hasattr(self, 'year_only_spin'):
            current_year = QDate.currentDate().year()
            if self.year_only_spin.value() == 0:
                self.year_only_spin.setValue(current_year)

        # Configurar el splitter principal si es necesario
        if hasattr(self, 'main_splitter'):
            if self.main_splitter.sizes() == [0, 0]:
                self.main_splitter.setSizes([400, 800])

        # Configurar el splitter de detalles si es necesario
        if hasattr(self, 'details_splitter'):
            if self.details_splitter.sizes() == [0, 0]:
                self.details_splitter.setSizes([200, 800])

        # Inicializar la lista de botones avanzados si estamos usando la UI
        if all(hasattr(self, btn) for btn in ['custom_button1', 'custom_button2', 'custom_button3']):
            self.advanced_buttons = [self.custom_button1, self.custom_button2, self.custom_button3]

        # Inicializar la lista para almacenar los elementos de la playlist
        self.playlist_items = []

        # Configurar políticas de foco si los widgets existen
        if hasattr(self, 'search_box'):
            self.search_box.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        for button_name in ['play_button', 'folder_button']:
            if hasattr(self, button_name):
                getattr(self, button_name).setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for button in self.advanced_buttons:
            if button:
                button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        if hasattr(self, 'advanced_settings_check'):
            self.advanced_settings_check.setFocusPolicy(Qt.FocusPolicy.NoFocus)



    def setup_info_widget(self):
        """Configura los widgets de información dentro de los ScrollAreas."""
        try:
            # Verificar que info_scroll existe
            if not hasattr(self, 'info_scroll') or not self.info_scroll:
                print("Error: info_scroll no existe")
                self._fallback_setup_info_widget()
                return

            # 1. Cargar el panel de información principal (enlaces, wikipedia, lastfm, etc.)
            info_ui_path = os.path.join(PROJECT_ROOT, "ui", "music_fuzzy_info_panel.ui")
            if os.path.exists(info_ui_path):
                try:
                    self.info_widget = QWidget()
                    uic.loadUi(info_ui_path, self.info_widget)

                    # Obtener referencias a los labels
                    self.links_label = self.info_widget.findChild(QLabel, "links_label")
                    self.wikipedia_artist_label = self.info_widget.findChild(QLabel, "wikipedia_artist_label")
                    self.lastfm_label = self.info_widget.findChild(QLabel, "lastfm_label")
                    self.wikipedia_album_label = self.info_widget.findChild(QLabel, "wikipedia_album_label")

                    # Verificar que se obtuvieron todas las referencias
                    if not all([self.links_label, self.wikipedia_artist_label, self.lastfm_label, self.wikipedia_album_label]):
                        print("No se pudieron obtener todas las referencias a los labels de información")
                        for name, widget in [("links_label", self.links_label),
                                            ("wikipedia_artist_label", self.wikipedia_artist_label),
                                            ("lastfm_label", self.lastfm_label),
                                            ("wikipedia_album_label", self.wikipedia_album_label)]:
                            if widget is None:
                                print(f"  - {name} es None")
                        self._fallback_setup_info_widget()
                        return

                    # Establecer el widget en el ScrollArea
                    self.info_scroll.setWidget(self.info_widget)
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

            # 2. Cargar el panel de metadatos solo si metadata_scroll existe
            if hasattr(self, 'metadata_scroll') and self.metadata_scroll:
                metadata_ui_path = os.path.join(PROJECT_ROOT, "ui", "music_fuzzy_metadata_panel.ui")
                if os.path.exists(metadata_ui_path):
                    try:
                        self.metadata_widget = QWidget()
                        uic.loadUi(metadata_ui_path, self.metadata_widget)

                        # Obtener referencia al label de metadatos
                        self.metadata_label = self.metadata_widget.findChild(QLabel, "metadata_label")
                        if not self.metadata_label:
                            print("No se pudo obtener la referencia al label de metadatos")
                            # Crear manualmente
                            self.metadata_label = QLabel(self.metadata_widget)
                            self.metadata_label.setWordWrap(True)
                            self.metadata_label.setTextFormat(Qt.TextFormat.RichText)
                            self.metadata_label.setOpenExternalLinks(True)
                            layout = QVBoxLayout(self.metadata_widget)
                            layout.addWidget(self.metadata_label)

                        # Establecer el widget en el ScrollArea
                        self.metadata_scroll.setWidget(self.metadata_widget)
                        print("Panel de metadatos cargado desde UI")
                    except Exception as e:
                        print(f"Error al cargar el panel de metadatos: {e}")
                        traceback.print_exc()
                        # Crear un widget básico para mostrar metadatos
                        self.metadata_widget = QWidget()
                        self.metadata_label = QLabel(self.metadata_widget)
                        self.metadata_label.setWordWrap(True)
                        self.metadata_label.setTextFormat(Qt.TextFormat.RichText)
                        self.metadata_label.setOpenExternalLinks(True)
                        layout = QVBoxLayout(self.metadata_widget)
                        layout.addWidget(self.metadata_label)
                        self.metadata_scroll.setWidget(self.metadata_widget)
                else:
                    print(f"Archivo UI del panel de metadatos no encontrado: {metadata_ui_path}")
                    # Crear un widget básico para mostrar metadatos
                    self.metadata_widget = QWidget()
                    self.metadata_label = QLabel(self.metadata_widget)
                    self.metadata_label.setWordWrap(True)
                    self.metadata_label.setTextFormat(Qt.TextFormat.RichText)
                    self.metadata_label.setOpenExternalLinks(True)
                    layout = QVBoxLayout(self.metadata_widget)
                    layout.addWidget(self.metadata_label)
                    self.metadata_scroll.setWidget(self.metadata_widget)

            self.ui_components_loaded['info'] = True
            print("Widgets de información configurados correctamente")
        except Exception as e:
            print(f"Error general al configurar los widgets de información: {e}")
            traceback.print_exc()
            self._fallback_setup_info_widget()

    def _fallback_setup_info_widget(self):
        """Método de respaldo para crear el widget de información manualmente."""
        print("Usando método fallback para configurar widgets de información")

        # Crear el widget para el interior del scroll principal
        self.info_widget = QWidget()
        info_layout = QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(5, 5, 5, 5)

        # Labels para la información
        self.links_label = QLabel()
        self.links_label.setWordWrap(True)
        self.links_label.setTextFormat(Qt.TextFormat.RichText)
        self.links_label.setOpenExternalLinks(True)
        self.links_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.links_label.setMinimumWidth(600)

        self.wikipedia_artist_label = QLabel()
        self.wikipedia_artist_label.setWordWrap(True)
        self.wikipedia_artist_label.setTextFormat(Qt.TextFormat.RichText)
        self.wikipedia_artist_label.setOpenExternalLinks(True)
        self.wikipedia_artist_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.wikipedia_artist_label.setMinimumWidth(600)

        self.lastfm_label = QLabel()
        self.lastfm_label.setWordWrap(True)
        self.lastfm_label.setTextFormat(Qt.TextFormat.RichText)
        self.lastfm_label.setOpenExternalLinks(True)
        self.lastfm_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.lastfm_label.setMinimumWidth(600)

        self.wikipedia_album_label = QLabel()
        self.wikipedia_album_label.setWordWrap(True)
        self.wikipedia_album_label.setTextFormat(Qt.TextFormat.RichText)
        self.wikipedia_album_label.setOpenExternalLinks(True)
        self.wikipedia_album_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.wikipedia_album_label.setMinimumWidth(600)

        self.metadata_label = QLabel()
        self.metadata_label.setWordWrap(True)
        self.metadata_label.setTextFormat(Qt.TextFormat.RichText)
        self.metadata_label.setOpenExternalLinks(True)
        self.metadata_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.metadata_label.setMinimumWidth(600)

        # Agregar las etiquetas al layout en el orden correcto
        info_layout.addWidget(self.links_label)
        info_layout.addWidget(self.wikipedia_artist_label)
        info_layout.addWidget(self.lastfm_label)
        info_layout.addWidget(self.wikipedia_album_label)
        info_layout.addStretch()

        # Configurar el ScrollArea principal
        if hasattr(self, 'info_scroll') and self.info_scroll:
            self.info_scroll.setWidget(self.info_widget)

        # Configurar el ScrollArea de metadatos si existe
        if hasattr(self, 'metadata_scroll') and self.metadata_scroll:
            self.metadata_widget = QWidget()
            metadata_layout = QVBoxLayout(self.metadata_widget)
            metadata_layout.addWidget(self.metadata_label)
            self.metadata_scroll.setWidget(self.metadata_widget)

        print("Panels de información y metadatos creados manualmente (fallback)")


    def load_advanced_settings_ui(self):
        """Carga dinámicamente el widget de configuraciones avanzadas desde un archivo UI separado."""
        # Verificar que advanced_settings_container existe
        if not hasattr(self, 'advanced_settings_container') or not self.advanced_settings_container:
            print("Error: advanced_settings_container no existe")
            return False

        # Si ya existe un layout en el contenedor, eliminarlo
        if self.advanced_settings_container.layout():
            while self.advanced_settings_container.layout().count():
                item = self.advanced_settings_container.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(self.advanced_settings_container.layout())

        # Crear un nuevo layout para el contenedor
        container_layout = QVBoxLayout(self.advanced_settings_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Cargar el widget desde un archivo UI separado
        ui_file_path = os.path.join(PROJECT_ROOT, "ui", "music_fuzzy_advanced_settings.ui")
        if os.path.exists(ui_file_path):
            try:
                # Cargar el archivo UI
                advanced_settings = QWidget()
                uic.loadUi(ui_file_path, advanced_settings)

                # Añadir el widget cargado al contenedor
                container_layout.addWidget(advanced_settings)

                # Transferir referencias a los widgets importantes
                self.time_value = advanced_settings.findChild(QSpinBox, "time_value")
                self.time_unit = advanced_settings.findChild(QComboBox, "time_unit")
                self.apply_time_filter = advanced_settings.findChild(QPushButton, "apply_time_filter")
                self.month_combo = advanced_settings.findChild(QComboBox, "month_combo")
                self.year_spin = advanced_settings.findChild(QSpinBox, "year_spin")
                self.apply_month_year = advanced_settings.findChild(QPushButton, "apply_month_year")
                self.year_only_spin = advanced_settings.findChild(QSpinBox, "year_only_spin")
                self.apply_year = advanced_settings.findChild(QPushButton, "apply_year")

                # Inicializar campos
                if self.month_combo and self.month_combo.count() == 0:
                    self.month_combo.addItems([f"{i:02d}" for i in range(1, 13)])

                # Establecer el año actual
                current_year = QDate.currentDate().year()
                if self.year_spin and self.year_spin.value() == 0:
                    self.year_spin.setValue(current_year)
                if self.year_only_spin and self.year_only_spin.value() == 0:
                    self.year_only_spin.setValue(current_year)

                # Conectar señales
                if self.apply_time_filter:
                    self.apply_time_filter.clicked.connect(self.apply_temporal_filter)
                if self.apply_month_year:
                    self.apply_month_year.clicked.connect(self.apply_month_year_filter)
                if self.apply_year:
                    self.apply_year.clicked.connect(self.apply_year_filter)

                self.ui_components_loaded['advanced'] = True
                print("Configuraciones avanzadas cargadas desde UI")
                return True
            except Exception as e:
                print(f"Error cargando UI de ajustes avanzados: {e}")
                traceback.print_exc()
                return False
        else:
            print(f"Archivo UI de ajustes avanzados no encontrado: {ui_file_path}")
            return False



    def connect_signals(self):
        """Conecta las señales de los widgets con sus manejadores."""
        # Botones de acción
        self.play_button.clicked.connect(lambda: self.play_selected_item())
        self.folder_button.clicked.connect(lambda: self.open_selected_folder())
        self.custom_button1.clicked.connect(self.buscar_musica_en_reproduccion)

        # Filtros temporales (cuando estén cargados)
        # Estas conexiones se hacen en load_advanced_settings_ui

        # Búsqueda
        self.search_box.textChanged.connect(self.search)
        self.search_box.returnPressed.connect(self.search)

        # Checkbox de configuración avanzada
        self.advanced_settings_check.stateChanged.connect(self.toggle_advanced_settings)

        # Árbol de resultados (cuando esté cargado)
        # Estas conexiones se hacen en setup_results_tree


        # Botón de Spotify
        self.spotify_button.clicked.connect(self.handle_spotify_button)



    def setup_space_key(self):
        """Configura el evento para añadir a playlist al presionar espacio"""
        self.results_list.keyPressEvent = self.custom_key_press_event

    def custom_key_press_event(self, event):
        """Maneja eventos de teclado en la lista de resultados"""
        if event.key() == Qt.Key.Key_Space:
            self.add_to_playlist()
        # Llamar al método original para manejar otros eventos de teclado
        QListWidget.keyPressEvent(self.results_list, event)

    def toggle_advanced_settings(self, state):
        """
        Muestra u oculta los elementos de configuración avanzada según el estado del checkbox.
        Carga el UI la primera vez que se activa.
        """
        # Verificar el estado del checkbox
        is_visible = (state == 2)  # 2 es Qt.Checked

        # Mostrar/ocultar botones avanzados
        for button in self.advanced_buttons:
            button.setVisible(is_visible)

        # Si es la primera vez que se activa, cargar el UI
        if is_visible:
            if not hasattr(self, '_advanced_settings_loaded') or not self._advanced_settings_loaded:
                self._advanced_settings_loaded = self.load_advanced_settings_ui()

        # Mostrar/ocultar el contenedor de ajustes avanzados
        self.advanced_settings_container.setVisible(is_visible)

        # Ajustar la altura del contenedor según corresponda
        if is_visible:
            self.top_container.setMaximumHeight(90)
        else:
            self.top_container.setMaximumHeight(50)

        # Forzar actualización
        self.repaint()
        QApplication.processEvents()

    def buscar_musica_en_reproduccion(self):
        """Busca la música en reproducción y rota la búsqueda"""
        artista = subprocess.run(['playerctl', 'metadata', '--format', '{{artist}}'], capture_output=True, text=True).stdout.strip()
        album = subprocess.run(['playerctl', 'metadata', '--format', '{{album}}'], capture_output=True, text=True).stdout.strip()
        cancion = subprocess.run(['playerctl', 'metadata', '--format', '{{title}}'], capture_output=True, text=True).stdout.strip()

        opciones = [cancion, album, artista]  # Lista cíclica
        self.boton_pulsado = (self.boton_pulsado + 1) % len(opciones)  # Rotar entre 0, 1, 2

        if opciones[self.boton_pulsado]:  # Evitar búsquedas vacías
            self.set_search_text(opciones[self.boton_pulsado])





    def get_song_data_from_current_item(self):
        """Extrae los datos de canción del ítem actualmente seleccionado"""
        current_item = self.results_list.currentItem()
        if not current_item:
            return None

        # Intenta obtener los datos completos del ítem
        track_data = current_item.data(Qt.ItemDataRole.UserRole)

        # Si no hay datos adjuntos al ítem o son incorrectos, intentar
        # obtener información del texto visible y metadatos disponibles
        if not track_data or not hasattr(track_data, 'artist'):
            # Extraer información de las etiquetas de metadatos
            # Suponiendo que esta información está disponible en algún lugar
            artist = self._extract_artist_from_ui()
            album = self._extract_album_from_ui()
            title = current_item.text()
            label = self._extract_label_from_ui()
            date = self._extract_date_from_ui()

            # Crear un objeto o diccionario con los datos extraídos
            track_data = {
                'artist': artist,
                'album': album,
                'title': title,
                'label': label,
                'date': date
            }

        return track_data

    def _extract_artist_from_ui(self):
        """Extrae información del artista desde la UI actual"""
        # Este es un método auxiliar para extraer el artista de la UI
        # Por ejemplo, podrías buscar en el texto de metadata_label o lastfm_label

        # Ejemplo muy básico:
        artist = "Desconocido"

        metadata_text = self.metadata_label.text()
        if "Artista:" in metadata_text:
            # Intenta extraer el artista usando expresiones regulares o parsing de texto
            import re
            match = re.search(r'Artista:\s*([^<]+)', metadata_text)
            if match:
                artist = match.group(1).strip()

        return artist

    def _extract_album_from_ui(self):
        """Extrae información del álbum desde la UI actual"""
        # Similar al método anterior, pero para el álbum
        album = "Desconocido"

        metadata_text = self.metadata_label.text()
        if "Álbum:" in metadata_text:
            import re
            match = re.search(r'Álbum:\s*([^<]+)', metadata_text)
            if match:
                album = match.group(1).strip()

        return album

    def _extract_label_from_ui(self):
        """Extrae información del sello desde la UI actual"""
        # Similar a los métodos anteriores, pero para el sello
        label = "Desconocido"

        metadata_text = self.metadata_label.text()
        if "Sello:" in metadata_text:
            import re
            match = re.search(r'Sello:\s*([^<]+)', metadata_text)
            if match:
                label = match.group(1).strip()

        return label

    def _extract_date_from_ui(self):
        """Extrae información de la fecha desde la UI actual"""
        # Similar a los métodos anteriores, pero para la fecha
        date = "Desconocido"

        metadata_text = self.metadata_label.text()
        if "Fecha:" in metadata_text:
            import re
            match = re.search(r'Fecha:\s*([^<]+)', metadata_text)
            if match:
                date = match.group(1).strip()

        return date





    def set_search_text(self, query):
        """
        Establece el texto en el cuadro de búsqueda y ejecuta la búsqueda.

        Args:
            query (str): El texto de búsqueda a establecer
        """
        self.search_box.setText(query)
        self.search()  # Ejecuta la búsqueda con el texto establecido



    def apply_temporal_filter(self):
        """Aplica el filtro de últimas X unidades de tiempo."""
        value = self.time_value.value()
        unit = self.time_unit.currentText()

        filter_map = {
            'Semanas': 'w',
            'Meses': 'm',
            'Años': 'y'
        }

        unit_code = filter_map.get(unit, 'w')
        self.search_box.setText(f"{unit_code}:{value}")
        self.search()

    def apply_month_year_filter(self):
        """Aplica el filtro de mes/año específico."""
        month = self.month_combo.currentText()
        year = self.year_spin.value()
        self.search_box.setText(f"am:{month}/{year}")
        self.search()

    def apply_year_filter(self):
        """Aplica el filtro de año específico."""
        year = self.year_only_spin.value()
        self.search_box.setText(f"ay:{year}")
        self.search()


    def handle_item_click(self, item):
        """Maneja el clic en un ítem. Ya no es necesario hacer nada aquí
        porque handle_item_change se encargará de todo."""
        pass  # La funcionalidad ahora está en handle_item_change


    def handle_item_change(self, current, previous):
        """Maneja el cambio de ítem seleccionado, ya sea por clic o navegación con teclado."""
        if not current:
            self.clear_details()
            return

        if current.is_header:
            self.clear_details()
            self.show_album_info(current)
        else:
            self.clear_details()
            self.show_details(current, previous)


    def find_cover_image(self, file_path: str) -> Optional[str]:
        """Busca la carátula en la carpeta del archivo."""
        dir_path = Path(file_path).parent
        cover_names = ['cover', 'folder', 'front', 'album']
        image_extensions = ['.jpg', '.jpeg', '.png']

        # Primero buscar nombres específicos
        for name in cover_names:
            for ext in image_extensions:
                cover_path = dir_path / f"{name}{ext}"
                if cover_path.exists():
                    return str(cover_path)

        # Si no se encuentra, buscar cualquier imagen
        for file in dir_path.glob('*'):
            if file.suffix.lower() in image_extensions:
                return str(file)

        return None

    def find_artist_image(self, artist_name: str) -> Optional[str]:
        """Busca la imagen del artista en el directorio especificado y retorna una aleatoria si hay varias."""
        if not self.artist_images_dir or not artist_name:
            return None

        # Importar random para selección aleatoria
        import random

        # Normalizar el nombre del artista (quitar acentos, convertir a minúsculas)
        import unicodedata
        artist_name_norm = unicodedata.normalize('NFKD', artist_name.lower()) \
            .encode('ASCII', 'ignore').decode('utf-8')

        # Probar diferentes formatos de nombre
        name_formats = [
            artist_name,  # Original
            artist_name.replace(' ', '_'),  # Con guiones bajos
            artist_name.replace(' ', '-'),  # Con guiones
            artist_name_norm,  # Normalizado
            artist_name_norm.replace(' ', '_'),
            artist_name_norm.replace(' ', '-')
        ]

        # Extensiones comunes de imagen
        extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif']

        # Lista para almacenar todas las imágenes encontradas
        all_matching_files = []

        # Probar todas las combinaciones
        for name in name_formats:
            # Búsqueda exacta con diferentes extensiones
            for ext in extensions:
                path = os.path.join(self.artist_images_dir, f"{name}.{ext}")
                if os.path.exists(path):
                    all_matching_files.append(path)

            # Búsqueda con patrón glob (para archivos que empiezan con el nombre)
            pattern = os.path.join(self.artist_images_dir, f"{name}*")
            matching_files = glob.glob(pattern)
            # Filtrar por extensiones válidas
            for file in matching_files:
                ext = file.lower().split('.')[-1]
                if ext in extensions:
                    all_matching_files.append(file)

        # Eliminar duplicados
        all_matching_files = list(set(all_matching_files))

        # Si se encontraron imágenes, devolver una aleatoria
        if all_matching_files:
            return random.choice(all_matching_files)

        return None

    def get_artist_info_from_db(self, artist_name):
        """
        Obtiene información completa del artista desde la base de datos.

        Args:
            artist_name (str): Nombre del artista a buscar

        Returns:
            dict: Diccionario con la información del artista o None si no se encuentra
        """
        if not artist_name or not self.db_path:
            return None

        try:
            # Conectar a la base de datos
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Buscar el artista
            query = """
                SELECT id, name, bio, tags, similar_artists, last_updated, origin,
                    formed_year, total_albums, spotify_url, youtube_url,
                    musicbrainz_url, discogs_url, rateyourmusic_url,
                    links_updated, wikipedia_url, wikipedia_content,
                    wikipedia_updated, mbid, bandcamp_url, member_of, aliases, lastfm_url
                FROM artists
                WHERE LOWER(name) = LOWER(?)
            """
            cursor.execute(query, (artist_name,))
            result = cursor.fetchone()

            conn.close()

            if not result:
                print(f"No se encontró información en la base de datos para el artista: {artist_name}")
                return None

            # Crear un diccionario con los resultados
            columns = [
                'id', 'name', 'bio', 'tags', 'similar_artists', 'last_updated',
                'origin', 'formed_year', 'total_albums', 'spotify_url',
                'youtube_url', 'musicbrainz_url', 'discogs_url', 'rateyourmusic_url',
                'links_updated', 'wikipedia_url', 'wikipedia_content',
                'wikipedia_updated', 'mbid', 'bandcamp_url', 'member_of', 'aliases', 'lastfm_url'
            ]

            artist_info = {}
            for i, col in enumerate(columns):
                artist_info[col] = result[i] if i < len(result) else None

            print(f"Información obtenida de la BD para artista: {artist_name}")
            return artist_info

        except Exception as e:
            print(f"Error al obtener información del artista desde la base de datos: {e}")
            traceback.print_exc()
            return None


    def get_album_info_from_db(self, album_name, artist_name=None):
        """
        Obtiene información completa del álbum desde la base de datos.

        Args:
            album_name (str): Nombre del álbum a buscar
            artist_name (str, optional): Nombre del artista para búsqueda más precisa

        Returns:
            dict: Diccionario con la información del álbum o None si no se encuentra
        """
        if not album_name or not self.db_path:
            return None

        try:
            # Conectar a la base de datos
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Buscar el álbum
            if artist_name:
                # Si tenemos el nombre del artista, usar para una búsqueda más precisa
                # Primero buscar el ID del artista
                artist_query = "SELECT id FROM artists WHERE LOWER(name) = LOWER(?)"
                cursor.execute(artist_query, (artist_name,))
                artist_result = cursor.fetchone()

                if artist_result:
                    artist_id = artist_result[0]

                    # Buscar el álbum con ese artist_id
                    query = """
                        SELECT id, artist_id, name, year, label, genre, total_tracks,
                            album_art_path, last_updated, spotify_url, spotify_id,
                            youtube_url, musicbrainz_url, discogs_url, rateyourmusic_url,
                            links_updated, wikipedia_url, wikipedia_content,
                            wikipedia_updated, mbid, folder_path, bitrate_range,
                            bandcamp_url, producers, engineers, mastering_engineers,
                            credits, lastfm_url
                        FROM albums
                        WHERE LOWER(name) = LOWER(?) AND artist_id = ?
                    """
                    cursor.execute(query, (album_name, artist_id))
                else:
                    # No se encontró el ID del artista, buscar por nombre del álbum solamente
                    query = """
                        SELECT id, artist_id, name, year, label, genre, total_tracks,
                            album_art_path, last_updated, spotify_url, spotify_id,
                            youtube_url, musicbrainz_url, discogs_url, rateyourmusic_url,
                            links_updated, wikipedia_url, wikipedia_content,
                            wikipedia_updated, mbid, folder_path, bitrate_range,
                            bandcamp_url, producers, engineers, mastering_engineers,
                            credits, lastfm_url
                        FROM albums
                        WHERE LOWER(name) = LOWER(?)
                    """
                    cursor.execute(query, (album_name,))
            else:
                # Buscar solo por nombre del álbum
                query = """
                    SELECT id, artist_id, name, year, label, genre, total_tracks,
                        album_art_path, last_updated, spotify_url, spotify_id,
                        youtube_url, musicbrainz_url, discogs_url, rateyourmusic_url,
                        links_updated, wikipedia_url, wikipedia_content,
                        wikipedia_updated, mbid, folder_path, bitrate_range,
                        bandcamp_url, producers, engineers, mastering_engineers,
                        credits, lastfm_url
                    FROM albums
                    WHERE LOWER(name) = LOWER(?)
                """
                cursor.execute(query, (album_name,))

            result = cursor.fetchone()

            conn.close()

            if not result:
                print(f"No se encontró información en la base de datos para el álbum: {album_name}")
                return None

            # Crear un diccionario con los resultados
            columns = [
                'id', 'artist_id', 'name', 'year', 'label', 'genre', 'total_tracks',
                'album_art_path', 'last_updated', 'spotify_url', 'spotify_id',
                'youtube_url', 'musicbrainz_url', 'discogs_url', 'rateyourmusic_url',
                'links_updated', 'wikipedia_url', 'wikipedia_content',
                'wikipedia_updated', 'mbid', 'folder_path', 'bitrate_range',
                'bandcamp_url', 'producers', 'engineers', 'mastering_engineers',
                'credits', 'lastfm_url'
            ]

            album_info = {}
            for i, col in enumerate(columns):
                album_info[col] = result[i] if i < len(result) else None

            print(f"Información obtenida de la BD para álbum: {album_name}")
            return album_info

        except Exception as e:
            print(f"Error al obtener información del álbum desde la base de datos: {e}")
            traceback.print_exc()
            return None


    def show_album_info(self, album_item):
        """Muestra la información del álbum."""
        # Verificar si es un ítem de álbum válido
        if not album_item:
            return

        # Obtener datos del álbum del UserRole
        item_data = album_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or not isinstance(item_data, dict) or item_data.get('type') != 'album':
            return

        # Obtener información directamente de los datos estructurados
        artist_name = item_data.get('artist', 'Desconocido')
        album_name = item_data.get('name', 'Desconocido')
        year = item_data.get('year', '')
        genre = item_data.get('genre', '')

        # Buscar información del álbum en la base de datos
        album_db_info = self.get_album_info_from_db(album_name, artist_name)

        # Contar canciones y obtener información adicional
        total_tracks = album_item.childCount()
        total_duration = 0
        album_paths = []
        first_track_data = None

        # Recorrer todos los tracks hijos del álbum
        for i in range(total_tracks):
            track_item = album_item.child(i)
            if track_item:
                track_data = track_item.data(0, Qt.ItemDataRole.UserRole)
                if track_data:
                    if not first_track_data:
                        first_track_data = track_data
                    # Añadir duración si está disponible
                    if len(track_data) > 19:  # Índice 19 es duration en la tabla songs
                        try:
                            duration_value = track_data[19]
                            if isinstance(duration_value, (int, float)) and duration_value > 0:
                                total_duration += duration_value
                        except (ValueError, TypeError, IndexError):
                            pass
                    # Añadir path si está disponible
                    if hasattr(track_item, 'paths') and track_item.paths:
                        album_paths.extend(track_item.paths)
                    elif len(track_data) > 1:  # Si el path está en el track_data
                        album_paths.append(track_data[1])

        # Guardar las rutas en el header para usarlas en play_album y open_album_folder
        album_item.paths = album_paths if hasattr(album_item, 'paths') else []

        # Formatear la duración total
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        seconds = int(total_duration % 60)

        # Buscar la carátula usando la ruta del primer track
        self.clear_details()  # Limpiar imágenes primero

        # Verificar que los widgets necesarios estén disponibles
        if not all([hasattr(self, 'lastfm_label'), hasattr(self, 'metadata_label')]):
            print("Error: Widgets de información no disponibles, reconfigurando...")
            self.setup_info_widget()

        # Si aún no tenemos los widgets, mostrar un mensaje de error y salir
        if not hasattr(self, 'lastfm_label') or not self.lastfm_label:
            print("Error crítico: lastfm_label no disponible después de reconfigurar")
            return

        if not hasattr(self, 'metadata_label') or not self.metadata_label:
            print("Error crítico: metadata_label no disponible después de reconfigurar")
            return

        if first_track_data and len(first_track_data) > 1:
            # Mostrar la carátula del álbum
            if hasattr(self, 'cover_label') and self.cover_label:
                cover_path = None

                # Priorizar ruta de carátula de la base de datos
                if album_db_info and album_db_info.get('album_art_path'):
                    cover_path = album_db_info['album_art_path']
                    if not os.path.exists(cover_path):
                        cover_path = None

                # Si no hay ruta en la base de datos o no existe, buscar en la carpeta
                if not cover_path:
                    cover_path = self.find_cover_image(first_track_data[1])

                if cover_path:
                    pixmap = QPixmap(cover_path)
                    pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)
                    self.cover_label.setPixmap(pixmap)
                else:
                    self.cover_label.setText("No imagen")

            # Mostrar la imagen del artista
            if hasattr(self, 'artist_image_label') and self.artist_image_label:
                artist_image_path = self.find_artist_image(artist_name)
                if artist_image_path:
                    artist_pixmap = QPixmap(artist_image_path)
                    artist_pixmap = artist_pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)
                    self.artist_image_label.setPixmap(artist_pixmap)
                else:
                    self.artist_image_label.setText("No imagen de artista")

        try:
            # 1. METADATA LABEL (Información breve para el panel central)
            if self.metadata_label:
                # Construir la metadata básica del álbum para el panel central
                metadata = f"""
                    <b>Álbum:</b> {album_name}<br>
                    <b>Artista:</b> {artist_name}<br>
                """

                # Añadir información de la base de datos
                if album_db_info:
                    if album_db_info.get('year'):
                        metadata += f"<b>Fecha:</b> {album_db_info['year']}<br>"
                    elif year:
                        metadata += f"<b>Fecha:</b> {year}<br>"
                    else:
                        metadata += f"<b>Fecha:</b> {first_track_data[6] if len(first_track_data) > 6 else 'N/A'}<br>"

                    if album_db_info.get('genre'):
                        metadata += f"<b>Género:</b> {album_db_info['genre']}<br>"
                    elif genre:
                        metadata += f"<b>Género:</b> {genre}<br>"
                    else:
                        metadata += f"<b>Género:</b> {first_track_data[7] if len(first_track_data) > 7 else 'N/A'}<br>"

                    if album_db_info.get('label'):
                        metadata += f"<b>Sello:</b> {album_db_info['label']}<br>"
                    else:
                        metadata += f"<b>Sello:</b> {first_track_data[8] if len(first_track_data) > 8 else 'N/A'}<br>"

                    # Información adicional específica del álbum
                    if album_db_info.get('total_tracks'):
                        metadata += f"<b>Pistas:</b> {album_db_info['total_tracks']}<br>"
                    else:
                        metadata += f"<b>Pistas:</b> {total_tracks}<br>"

                    metadata += f"<b>Duración:</b> {hours:02d}:{minutes:02d}:{seconds:02d}<br>"

                    if album_db_info.get('producers'):
                        metadata += f"<b>Productores:</b> {album_db_info['producers']}<br>"
                    if album_db_info.get('engineers'):
                        metadata += f"<b>Ingenieros:</b> {album_db_info['engineers']}<br>"
                    if album_db_info.get('mastering_engineers'):
                        metadata += f"<b>Mastering:</b> {album_db_info['mastering_engineers']}<br>"
                else:
                    # Usar datos del primer track como respaldo
                    metadata += f"<b>Fecha:</b> {year or first_track_data[6] or 'N/A'}<br>"
                    metadata += f"<b>Género:</b> {genre or first_track_data[7] or 'N/A'}<br>"
                    metadata += f"<b>Sello:</b> {first_track_data[8] or 'N/A'}<br>"
                    metadata += f"<b>Pistas:</b> {total_tracks}<br>"
                    metadata += f"<b>Duración:</b> {hours:02d}:{minutes:02d}:{seconds:02d}<br>"

                self.metadata_label.setText(metadata)

            # 2. LINKS LABEL (Enlaces del artista y del álbum)
            if hasattr(self, 'links_label') and self.links_label:
                links_text = "<h3>Enlaces:</h3>"

                # Enlaces del álbum
                album_links = []

                # Priorizar enlaces de la base de datos
                if album_db_info:
                    if album_db_info.get('spotify_url'):
                        album_links.append(f"<a href='{album_db_info['spotify_url']}'>Spotify</a>")
                    if album_db_info.get('youtube_url'):
                        album_links.append(f"<a href='{album_db_info['youtube_url']}'>YouTube</a>")
                    if album_db_info.get('musicbrainz_url'):
                        album_links.append(f"<a href='{album_db_info['musicbrainz_url']}'>MusicBrainz</a>")
                    if album_db_info.get('discogs_url'):
                        album_links.append(f"<a href='{album_db_info['discogs_url']}'>Discogs</a>")
                    if album_db_info.get('rateyourmusic_url'):
                        album_links.append(f"<a href='{album_db_info['rateyourmusic_url']}'>RateYourMusic</a>")
                    if album_db_info.get('wikipedia_url'):
                        album_links.append(f"<a href='{album_db_info['wikipedia_url']}'>Wikipedia</a>")
                    if album_db_info.get('bandcamp_url'):
                        album_links.append(f"<a href='{album_db_info['bandcamp_url']}'>Bandcamp</a>")
                    if album_db_info.get('lastfm_url'):
                        album_links.append(f"<a href='{album_db_info['lastfm_url']}'>Last.fm</a>")
                # Usar enlaces del track como respaldo
                elif len(first_track_data) > 21:
                    if first_track_data[21]:  # album_spotify
                        album_links.append(f"<a href='{first_track_data[21]}'>Spotify</a>")
                    if first_track_data[22]:  # album_youtube
                        album_links.append(f"<a href='{first_track_data[22]}'>YouTube</a>")
                    if first_track_data[23]:  # album_musicbrainz
                        album_links.append(f"<a href='{first_track_data[23]}'>MusicBrainz</a>")
                    if first_track_data[24]:  # album_discogs
                        album_links.append(f"<a href='{first_track_data[24]}'>Discogs</a>")
                    if first_track_data[25]:  # album_rateyourmusic
                        album_links.append(f"<a href='{first_track_data[25]}'>RateYourMusic</a>")
                    if first_track_data[28]:  # album_wikipedia_url
                        album_links.append(f"<a href='{first_track_data[28]}'>Wikipedia</a>")

                # Enlaces del artista
                # Buscar información del artista en la base de datos
                artist_db_info = self.get_artist_info_from_db(artist_name)

                artist_links = []

                # Priorizar enlaces de la base de datos
                if artist_db_info:
                    if artist_db_info.get('spotify_url'):
                        artist_links.append(f"<a href='{artist_db_info['spotify_url']}'>Spotify</a>")
                    if artist_db_info.get('youtube_url'):
                        artist_links.append(f"<a href='{artist_db_info['youtube_url']}'>YouTube</a>")
                    if artist_db_info.get('musicbrainz_url'):
                        artist_links.append(f"<a href='{artist_db_info['musicbrainz_url']}'>MusicBrainz</a>")
                    if artist_db_info.get('discogs_url'):
                        artist_links.append(f"<a href='{artist_db_info['discogs_url']}'>Discogs</a>")
                    if artist_db_info.get('rateyourmusic_url'):
                        artist_links.append(f"<a href='{artist_db_info['rateyourmusic_url']}'>RateYourMusic</a>")
                    if artist_db_info.get('wikipedia_url'):
                        artist_links.append(f"<a href='{artist_db_info['wikipedia_url']}'>Wikipedia</a>")
                    if artist_db_info.get('bandcamp_url'):
                        artist_links.append(f"<a href='{artist_db_info['bandcamp_url']}'>Bandcamp</a>")
                    if artist_db_info.get('lastfm_url'):
                        artist_links.append(f"<a href='{artist_db_info['lastfm_url']}'>Last.fm</a>")
                # Usar enlaces del track como respaldo
                elif len(first_track_data) > 16:
                    if first_track_data[16]:  # artist_spotify
                        artist_links.append(f"<a href='{first_track_data[16]}'>Spotify</a>")
                    if first_track_data[17]:  # artist_youtube
                        artist_links.append(f"<a href='{first_track_data[17]}'>YouTube</a>")
                    if first_track_data[18]:  # artist_musicbrainz
                        artist_links.append(f"<a href='{first_track_data[18]}'>MusicBrainz</a>")
                    if first_track_data[19]:  # artist_discogs
                        artist_links.append(f"<a href='{first_track_data[19]}'>Discogs</a>")
                    if first_track_data[20]:  # artist_rateyourmusic
                        artist_links.append(f"<a href='{first_track_data[20]}'>RateYourMusic</a>")
                    if first_track_data[26]:  # artist_wikipedia_url
                        artist_links.append(f"<a href='{first_track_data[26]}'>Wikipedia</a>")

                # Añadir enlaces organizados
                if album_links:
                    links_text += f"<p><b>Álbum {album_name}:</b> {' | '.join(album_links)}</p>"
                if artist_links:
                    links_text += f"<p><b>Artista {artist_name}:</b> {' | '.join(artist_links)}</p>"

                self.links_label.setText(links_text)

            # 3. WIKIPEDIA ARTIST LABEL
            if hasattr(self, 'wikipedia_artist_label') and self.wikipedia_artist_label:
                # Priorizar contenido de Wikipedia de la base de datos del artista
                artist_wiki_content = None
                if artist_db_info and artist_db_info.get('wikipedia_content'):
                    artist_wiki_content = artist_db_info['wikipedia_content']
                elif len(first_track_data) > 27 and first_track_data[27]:
                    artist_wiki_content = first_track_data[27]

                if artist_wiki_content:
                    self.wikipedia_artist_label.setText(f"<h3>Wikipedia - Artista:</h3><div style='white-space: pre-wrap;'>{artist_wiki_content}</div>")
                else:
                    self.wikipedia_artist_label.setText("")

            # 4. LASTFM LABEL
            if self.lastfm_label:
                # Obtener bio del artista
                artist_bio = None
                if artist_db_info and artist_db_info.get('bio'):
                    artist_bio = artist_db_info['bio']
                elif len(first_track_data) > 15 and first_track_data[15]:
                    artist_bio = first_track_data[15]
                else:
                    artist_bio = "No hay información del artista disponible"

                self.lastfm_label.setText(f"<h3>Información del Artista:</h3><div style='white-space: pre-wrap;'>{artist_bio}</div>")

            # 5. WIKIPEDIA ALBUM LABEL
            if hasattr(self, 'wikipedia_album_label') and self.wikipedia_album_label:
                # Priorizar contenido de Wikipedia de la base de datos del álbum
                album_wiki_content = None
                if album_db_info and album_db_info.get('wikipedia_content'):
                    album_wiki_content = album_db_info['wikipedia_content']
                elif len(first_track_data) > 29 and first_track_data[29]:
                    album_wiki_content = first_track_data[29]

                if album_wiki_content:
                    self.wikipedia_album_label.setText(f"<h3>Wikipedia - Álbum:</h3><div style='white-space: pre-wrap;'>{album_wiki_content}</div>")
                else:
                    self.wikipedia_album_label.setText("")
        except Exception as e:
            print(f"Error mostrando detalles del álbum: {e}")
            traceback.print_exc()

            # En caso de error, mostrar información básica
            if self.metadata_label:
                self.metadata_label.setText(f"<b>Álbum:</b> {album_name}<br><b>Artista:</b> {artist_name}<br><b>Error:</b> {str(e)}")



    def apply_theme(self):
        """Aplica el tema específico del módulo."""

        print(f"Aplicando tema con fuente: {self.font_family}")

        # Verificar que los labels existen antes de intentar modificarlos
        if not hasattr(self, 'lastfm_label') or self.lastfm_label is None:
            print("lastfm_label no está disponible para aplicar el tema")
            return

        if not hasattr(self, 'metadata_label') or self.metadata_label is None:
            print("metadata_label no está disponible para aplicar el tema")
            return

        # Obtener el tema actual
        theme = self.themes.get(self.current_theme, self.themes['Tokyo Night'])

        # Aplicar estilos globales
        self.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;

            }}
            QLineEdit {{
                font-size: 13px;
                border: 1px solid {theme['border']};
                border-radius: 3px;
                padding: 5px;
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
            }}

            QTreeWidget {{
                border: none;
                background-color: {theme['bg']};
                alternate-background-color: {theme['bg']};
                show-decoration-selected: 1;
            }}
            QTreeWidget::item {{
                padding: 6px;
                border-bottom: 1px solid rgba(65, 72, 104, 0.1);
            }}
            QTreeWidget::item:selected {{
                background-color: {theme['selection']};
                color: {theme['fg']};
            }}
            QTreeWidget::item:hover {{
                background-color: rgba(65, 72, 104, 0.1);
            }}
            QHeaderView::section {{
                background-color: {theme['bg']};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {theme['border']};
                font-weight: bold;
            }}
            QHeaderView::section {{
                background-color: transparent;
                padding: 5px;
                border: none;
                border-radius: 3px;
                border-bottom: 1px solid {theme['border']};
            }}
            QTableWidget {{
                border: none;
            }}
            QScrollArea {{
                border: none;
            }}

        """)

        # Set object names for the labels so the CSS can target them
        self.lastfm_label.setObjectName("lastfm_label")
        self.metadata_label.setObjectName("metadata_label")

        # También aplicar el tema a widgets específicos si lo necesitan
        if hasattr(self, 'results_tree') and self.results_tree:
            self.results_tree.setStyleSheet(f"""
                QTreeWidget {{
                    border: none;
                    background-color: {theme['bg']};
                }}
                QTreeWidget::item {{
                    padding: 4px;
                    border-bottom: 1px solid rgba(65, 72, 104, 0.2);
                }}
                QTreeWidget::item:selected {{
                    background-color: {theme['selection']};
                    color: {theme['fg']};
                }}
            """)

        if hasattr(self, 'advanced_settings_container') and self.advanced_settings_container:
            self.advanced_settings_container.setStyleSheet(f"""
                QSpinBox, QComboBox {{
                    border: 1px solid {theme['border']};
                    border-radius: 3px;
                    padding: 3px;
                    background-color: {theme['secondary_bg']};
                }}
                QPushButton {{
                    background-color: {theme['button_hover']};
                    color: {theme['fg']};
                    border-radius: 3px;
                    padding: 5px;
                }}
            """)


    def show_details(self, current, previous):
        """Muestra los detalles del ítem seleccionado."""
        if not current:
            self.clear_details()
            return

        data = current.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            self.clear_details()
            return

        try:
            # Verificar que los widgets necesarios estén disponibles
            if not hasattr(self, 'metadata_label') or not self.metadata_label or not hasattr(self, 'lastfm_label') or not self.lastfm_label:
                print("Error: Widgets de información no disponibles, reconfigurando...")
                self.setup_info_widget()

                # Si aún no tenemos los widgets después de reconfigurar, salir con gracia
                if not hasattr(self, 'metadata_label') or not self.metadata_label:
                    print("Error crítico: metadata_label no disponible después de reconfigurar")
                    return

                if not hasattr(self, 'lastfm_label') or not self.lastfm_label:
                    print("Error crítico: lastfm_label no disponible después de reconfigurar")
                    return

            # Limpiar detalles anteriores
            self.clear_details()

            # Extraer información básica de los datos
            artist = data[3] if len(data) > 3 and data[3] else ""
            album = data[5] if len(data) > 5 and data[5] else ""
            title = data[2] if len(data) > 2 and data[2] else ""

            # Buscar información adicional en la base de datos
            artist_db_info = self.get_artist_info_from_db(artist) if artist else None
            album_db_info = self.get_album_info_from_db(album, artist) if album else None

            # Mostrar carátula
            if len(data) > 1 and hasattr(self, 'cover_label') and self.cover_label:
                cover_path = None

                # Priorizar ruta de carátula de la base de datos
                if album_db_info and album_db_info.get('album_art_path'):
                    cover_path = album_db_info['album_art_path']
                    if not os.path.exists(cover_path):
                        cover_path = None

                # Si no hay ruta en la base de datos o no existe, buscar en la carpeta
                if not cover_path:
                    cover_path = self.find_cover_image(data[1])

                if cover_path:
                    pixmap = QPixmap(cover_path)
                    pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)
                    self.cover_label.setPixmap(pixmap)
                else:
                    self.cover_label.setText("No imagen")

                # Mostrar imagen del artista usando el nombre extraído
                if artist and hasattr(self, 'artist_image_label') and self.artist_image_label:
                    artist_image_path = self.find_artist_image(artist)
                    if artist_image_path:
                        artist_pixmap = QPixmap(artist_image_path)
                        artist_pixmap = artist_pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)
                        self.artist_image_label.setPixmap(artist_pixmap)
                    else:
                        self.artist_image_label.setText("No imagen de artista")
                elif hasattr(self, 'artist_image_label') and self.artist_image_label:
                    self.artist_image_label.setText("No imagen de artista")
            elif hasattr(self, 'cover_label') and self.cover_label:
                self.cover_label.setText("No imagen")
                if hasattr(self, 'artist_image_label') and self.artist_image_label:
                    self.artist_image_label.setText("No imagen de artista")

            # Mostrar información en el widget scrollable
            info_text = ""

            # Mostrar letra de la canción si está disponible
            lyrics = data[30] if len(data) > 30 and data[30] else None
            lyrics_source = data[31] if len(data) > 31 and data[31] else "Desconocida"

            if lyrics:
                info_text += f"<h3>Letra</h3><div style='white-space: pre-wrap;'>{lyrics}</div>"
                info_text += f"<p><i>Fuente: {lyrics_source}</i></p><hr>"

            # Mostrar info de LastFM (bio del artista)
            artist_bio = None
            if artist_db_info and artist_db_info.get('bio'):
                artist_bio = artist_db_info['bio']
            elif len(data) > 15 and data[15]:
                artist_bio = data[15]
            else:
                artist_bio = "No hay información del artista disponible"

            info_text += f"<h3>Lastfm {artist}:</h3><div style='white-space: pre-wrap;'>{artist_bio}</div><br><br>"

            # Mostrar info de Wikipedia del artista
            wikipedia_content = None
            if artist_db_info and artist_db_info.get('wikipedia_content'):
                wikipedia_content = artist_db_info['wikipedia_content']
            elif len(data) > 27:  # Verificar que los nuevos campos existen
                wikipedia_content = data[27] if data[27] else None

            if wikipedia_content:
                info_text += f"<h3>Wikipedia - {artist}:</h3><div style='white-space: pre-wrap;'>{wikipedia_content}</div><br><br>"

            # Asignar el contenido actualizado
            if self.lastfm_label:
                self.lastfm_label.setText(info_text)

            # Mostrar metadata
            if len(data) >= 15 and self.metadata_label:  # Aseguramos que tengamos todos los campos necesarios
                track_num = data[14] if data[14] else "N/A"  # track_number está en el índice 14

                # Construir la sección de metadata básica
                metadata = f"""
                    <b>Título:</b> {title or 'N/A'}<br>
                    <b>Artista:</b> {artist or 'N/A'}<br>
                    <b>Album Artist:</b> {data[4] or 'N/A'}<br>
                    <b>Álbum:</b> {album or 'N/A'}<br>
                    <b>Fecha:</b> {data[6] or 'N/A'}<br>
                    <b>Género:</b> {data[7] or 'N/A'}<br>
                    <b>Sello:</b> {data[8] or 'N/A'}<br>
                    <b>Bitrate:</b> {data[10] or 'N/A'} kbps<br>
                    <b>Profundidad:</b> {data[11] or 'N/A'} bits<br>
                    <b>Frecuencia:</b> {data[12] or 'N/A'} Hz<br>
                """

                # Añadir enlaces externos del artista si existen
                metadata += "<br><b>Enlaces del Artista:</b><br>"

                artist_links = []

                # Priorizar enlaces de la base de datos
                if artist_db_info:
                    if artist_db_info.get('spotify_url'):
                        artist_links.append(f"<a href='{artist_db_info['spotify_url']}'>Spotify</a>")
                    if artist_db_info.get('youtube_url'):
                        artist_links.append(f"<a href='{artist_db_info['youtube_url']}'>YouTube</a>")
                    if artist_db_info.get('musicbrainz_url'):
                        artist_links.append(f"<a href='{artist_db_info['musicbrainz_url']}'>MusicBrainz</a>")
                    if artist_db_info.get('discogs_url'):
                        artist_links.append(f"<a href='{artist_db_info['discogs_url']}'>Discogs</a>")
                    if artist_db_info.get('rateyourmusic_url'):
                        artist_links.append(f"<a href='{artist_db_info['rateyourmusic_url']}'>RateYourMusic</a>")
                    if artist_db_info.get('wikipedia_url'):
                        artist_links.append(f"<a href='{artist_db_info['wikipedia_url']}'>Wikipedia</a>")
                    if artist_db_info.get('bandcamp_url'):
                        artist_links.append(f"<a href='{artist_db_info['bandcamp_url']}'>Bandcamp</a>")
                    if artist_db_info.get('lastfm_url'):
                        artist_links.append(f"<a href='{artist_db_info['lastfm_url']}'>Last.fm</a>")
                # Usar enlaces del track como respaldo
                elif len(data) > 16:
                    if data[16]:  # spotify_url
                        artist_links.append(f"<a href='{data[16]}'>Spotify</a>")
                    if data[17]:  # youtube_url
                        artist_links.append(f"<a href='{data[17]}'>YouTube</a>")
                    if data[18]:  # musicbrainz_url
                        artist_links.append(f"<a href='{data[18]}'>MusicBrainz</a>")
                    if data[19]:  # discogs_url
                        artist_links.append(f"<a href='{data[19]}'>Discogs</a>")
                    if data[20]:  # rateyourmusic_url
                        artist_links.append(f"<a href='{data[20]}'>RateYourMusic</a>")
                    if data[26]:  # artist_wikipedia_url (nuevo campo)
                        artist_links.append(f"<a href='{data[26]}'>Wikipedia</a>")

                if artist_links:
                    metadata += " | ".join(artist_links)
                else:
                    metadata += "No hay enlaces disponibles."

                # Añadir enlaces del álbum si los hay
                if album_db_info:
                    metadata += "<br><br><b>Enlaces del Álbum:</b><br>"
                    album_links = []

                    if album_db_info.get('spotify_url'):
                        album_links.append(f"<a href='{album_db_info['spotify_url']}'>Spotify</a>")
                    if album_db_info.get('youtube_url'):
                        album_links.append(f"<a href='{album_db_info['youtube_url']}'>YouTube</a>")
                    if album_db_info.get('musicbrainz_url'):
                        album_links.append(f"<a href='{album_db_info['musicbrainz_url']}'>MusicBrainz</a>")
                    if album_db_info.get('discogs_url'):
                        album_links.append(f"<a href='{album_db_info['discogs_url']}'>Discogs</a>")
                    if album_db_info.get('rateyourmusic_url'):
                        album_links.append(f"<a href='{album_db_info['rateyourmusic_url']}'>RateYourMusic</a>")
                    if album_db_info.get('wikipedia_url'):
                        album_links.append(f"<a href='{album_db_info['wikipedia_url']}'>Wikipedia</a>")

                    if album_links:
                        metadata += " | ".join(album_links)
                    else:
                        metadata += "No hay enlaces disponibles."

                self.metadata_label.setText(metadata)
                self.metadata_label.setOpenExternalLinks(True)

                # Actualizar otros labels si existen
                if hasattr(self, 'links_label') and self.links_label:
                    links_text = "<h3>Enlaces:</h3>"

                    # Añadir enlaces del artista
                    if artist_links:
                        links_text += f"<p><b>Artista {artist}:</b> {' | '.join(artist_links)}</p>"

                    # Añadir enlaces del álbum
                    if album_db_info:
                        album_links = []

                        if album_db_info.get('spotify_url'):
                            album_links.append(f"<a href='{album_db_info['spotify_url']}'>Spotify</a>")
                        if album_db_info.get('youtube_url'):
                            album_links.append(f"<a href='{album_db_info['youtube_url']}'>YouTube</a>")
                        if album_db_info.get('musicbrainz_url'):
                            album_links.append(f"<a href='{album_db_info['musicbrainz_url']}'>MusicBrainz</a>")
                        if album_db_info.get('discogs_url'):
                            album_links.append(f"<a href='{album_db_info['discogs_url']}'>Discogs</a>")
                        if album_db_info.get('rateyourmusic_url'):
                            album_links.append(f"<a href='{album_db_info['rateyourmusic_url']}'>RateYourMusic</a>")
                        if album_db_info.get('wikipedia_url'):
                            album_links.append(f"<a href='{album_db_info['wikipedia_url']}'>Wikipedia</a>")

                        if album_links:
                            links_text += f"<p><b>Álbum {album}:</b> {' | '.join(album_links)}</p>"

                    self.links_label.setText(links_text)

                # Mostrar Wikipedia del artista si está disponible
                if hasattr(self, 'wikipedia_artist_label') and self.wikipedia_artist_label and wikipedia_content:
                    self.wikipedia_artist_label.setText(f"<h3>Wikipedia - Artista:</h3><div style='white-space: pre-wrap;'>{wikipedia_content}</div>")

                # Mostrar Wikipedia del álbum si está disponible
                if hasattr(self, 'wikipedia_album_label') and self.wikipedia_album_label:
                    album_wiki_content = None
                    if album_db_info and album_db_info.get('wikipedia_content'):
                        album_wiki_content = album_db_info['wikipedia_content']

                    if album_wiki_content:
                        self.wikipedia_album_label.setText(f"<h3>Wikipedia - {album}:</h3><div style='white-space: pre-wrap;'>{album_wiki_content}</div>")
            elif self.metadata_label:
                self.metadata_label.setText("No hay suficientes datos de metadata")

        except Exception as e:
            # manejar la excepción
            print(f"Error en show_details: {e}")
            traceback.print_exc()

            # Intento de recuperación mostrando información básica
            if hasattr(self, 'metadata_label') and self.metadata_label and len(data) > 2:
                self.metadata_label.setText(f"<b>Título:</b> {data[2] or 'N/A'}<br><b>Error:</b> No se pudo cargar información completa.")

            if hasattr(self, 'lastfm_label') and self.lastfm_label and len(data) > 3:
                self.lastfm_label.setText(f"<h3>Error</h3><p>No se pudo cargar la información detallada para {data[3] or 'este elemento'}.</p>")


    def search(self):
        """Realiza una búsqueda en la base de datos según la consulta escrita en la caja de texto."""
        print("Método search() llamado")

        if not self.is_tree_valid():
            print("El árbol de resultados no está disponible. Cargando uno nuevo...")
            self._load_results_tree()
            if not self.is_tree_valid():
                print("No se pudo crear el árbol de resultados. Abortando búsqueda.")
                return

        query = self.search_box.text()
        print(f"Realizando búsqueda con texto: '{query}'")
        parsed = self.search_parser.parse_query(query)

        # Conectar a la base de datos
        conn = sqlite3.connect(self.db_path)

        # Habilitar escritura a memoria para mejorar rendimiento
        conn.execute("PRAGMA temp_store = MEMORY")

        c = conn.cursor()

        # Obtener condiciones SQL basadas en la consulta parseada
        conditions, params = self.search_parser.build_sql_conditions(parsed)
        # Construir la consulta SQL
        sql = """
            SELECT DISTINCT
                s.id,
                s.file_path,
                s.title,
                s.artist,
                s.album_artist,
                s.album,
                s.date,
                s.genre,
                s.label,
                s.mbid,
                s.bitrate,
                s.bit_depth,
                s.sample_rate,
                s.last_modified,
                s.track_number
                -- Otros campos que necesites
        """

        sql += """
            FROM songs s
            LEFT JOIN artists art ON s.artist = art.name
            LEFT JOIN albums alb ON s.album = alb.name
        """

        # Añadir cláusula WHERE si hay condiciones
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        # Ordenamiento
        sql += " ORDER BY s.artist, s.album, CAST(s.track_number AS INTEGER)"

        # Añadir un límite razonable
        sql += " LIMIT 1000"

        try:
            # Ejecutar la consulta
            c.execute(sql, params)
            results = c.fetchall()

            # Limpiar el árbol de resultados
            if self.results_tree:
                self.results_tree.clear()
            else:
                print("Error: results_tree no está inicializado")
                return

            # Organizar los resultados por artista > álbum > canción
            artists = {}


            for row in results:
                # Usar album_artist (índice 4) en lugar de artist (índice 3)
                album_artist = row[4] if row[4] else row[3] if row[3] else "Sin artista"
                artist = row[3] if row[3] else "Sin artista"
                album = row[5] if row[5] else "Sin álbum"
                title = row[2] if row[2] else "Sin título"
                date = row[6] if row[6] else ""
                year = date.split('-')[0] if date and '-' in date else date
                genre = row[7] if row[7] else ""
                track_number = row[14] if row[14] else "0"

                # Crear estructura anidada
                if album_artist not in artists:
                    artists[album_artist] = {}

                album_key = f"{album}"
                if album_key not in artists[album_artist]:
                    artists[album_artist][album_key] = []

                # Añadir la canción con su número de pista
                track_info = {
                    'number': track_number,
                    'title': title,
                    'data': row,
                    'year': year,
                    'genre': genre,
                    'paths': [row[1]]  # Añadir path al track info
                }
                artists[album_artist][album_key].append(track_info)

            # Añadir elementos al árbol
            for artist_name, albums in artists.items():
                # Crear elemento de artista
                artist_item = QTreeWidgetItem(self.results_tree)
                artist_item.setText(0, f"🗣 {artist_name}")
                artist_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'artist', 'name': artist_name})
                artist_item.is_header = True  # Marcar como header para compatibilidad

                # Añadir álbumes como hijos del artista
                for album_name, tracks in albums.items():
                    # Obtener información del álbum del primer track
                    album_year = tracks[0]['year'] if tracks else ""
                    album_genre = tracks[0]['genre'] if tracks else ""

                    # Crear elemento de álbum
                    album_item = QTreeWidgetItem(artist_item)
                    album_item.setText(0, f"💿 {album_name}")
                    album_item.setText(1, album_year)
                    album_item.setText(2, album_genre)
                    album_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'type': 'album',
                        'name': album_name,
                        'artist': artist_name,
                        'year': album_year,
                        'genre': album_genre
                    })
                    album_item.is_header = True  # Marcar como header para compatibilidad

                    # Obtener todas las rutas para este álbum
                    album_paths = []

                    # Ordenar las pistas por número
                    try:
                        def track_sort_key(track):
                            number = track['number']
                            # Manejar diferentes tipos de 'number'
                            if isinstance(number, str):
                                if number.isdigit():
                                    return int(number)
                                else:
                                    return float('inf')  # No es un número, ponerlo al final
                            elif isinstance(number, (int, float)):
                                return number
                            else:
                                return float('inf')  # Otro tipo, ponerlo al final

                        tracks.sort(key=track_sort_key)
                    except Exception as e:
                        print(f"Error al ordenar pistas: {e}")

                    # Añadir canciones como hijos del álbum
                    for track in tracks:
                        try:
                            track_num = int(track['number'])
                            display_text = f"{track_num:02d}. {track['title']}"
                        except (ValueError, TypeError):
                            display_text = f"--. {track['title']}"

                        # Crear elemento de canción
                        track_item = QTreeWidgetItem(album_item)
                        track_item.setText(0, display_text)
                        track_item.setText(1, track['year'])
                        track_item.setText(2, track['genre'])
                        track_item.setData(0, Qt.ItemDataRole.UserRole, track['data'])
                        track_item.is_header = False  # Marcar como no header para compatibilidad
                        track_item.paths = track['paths']  # Guardar rutas

                        # Añadir ruta a las rutas del álbum
                        album_paths.extend(track['paths'])

                    # Guardar rutas en el item del álbum
                    album_item.paths = album_paths

            # Expandir los artistas para mostrar los álbumes
            for i in range(self.results_tree.topLevelItemCount()):
                self.results_tree.topLevelItem(i).setExpanded(True)

        except Exception as e:
            print(f"Error en la búsqueda: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

        if hasattr(self, 'results_tree') and self.results_tree:
                self.results_tree.setVisible(True)
                print(f"Árbol actualizado con {self.results_tree.topLevelItemCount()} artistas")


    def clear_details(self):
        """Limpia todos los campos de detalles."""
        # Limpiar imágenes
        if hasattr(self, 'cover_label') and self.cover_label:
            self.cover_label.clear()
            self.cover_label.setText("No imagen")

        if hasattr(self, 'artist_image_label') and self.artist_image_label:
            self.artist_image_label.clear()
            self.artist_image_label.setText("No imagen de artista")

        # Limpiar información de metadatos (panel central)
        if hasattr(self, 'metadata_label') and self.metadata_label:
            self.metadata_label.setText("")

        # Limpiar información detallada (panel inferior)
        if hasattr(self, 'links_label') and self.links_label:
            self.links_label.setText("")

        if hasattr(self, 'wikipedia_artist_label') and self.wikipedia_artist_label:
            self.wikipedia_artist_label.setText("")

        if hasattr(self, 'lastfm_label') and self.lastfm_label:
            self.lastfm_label.setText("")

        if hasattr(self, 'wikipedia_album_label') and self.wikipedia_album_label:
            self.wikipedia_album_label.setText("")

        # Forzar actualización visual
        if hasattr(self, 'cover_label') and self.cover_label:
            self.cover_label.update()

        if hasattr(self, 'artist_image_label') and self.artist_image_label:
            self.artist_image_label.update()

        # Actualizar scroll areas si existen
        if hasattr(self, 'info_scroll') and self.info_scroll:
            self.info_scroll.update()

        if hasattr(self, 'metadata_scroll') and self.metadata_scroll:
            self.metadata_scroll.update()

    def handle_spotify_button(self):
        """Manejador para el botón de Spotify que decide qué argumento pasar a enviar_spoti"""
        if not self.is_tree_valid():
            print("El árbol de resultados no está disponible")
            return

        current_item = self.results_tree.currentItem()
        if not current_item:
            print("No hay elemento seleccionado")
            return

        # Obtener datos del ítem seleccionado
        item_data = current_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            print("No hay datos asociados al elemento seleccionado")
            return

        # Verificar si es un artista/álbum o una canción
        if isinstance(item_data, dict):
            # Es un artista o álbum
            if item_data.get('type') == 'artist':
                artist_name = item_data.get('name', '')
                if artist_name:
                    self.enviar_spoti(artist_name)
                else:
                    print("No hay suficiente información del artista para buscar")
            elif item_data.get('type') == 'album':
                album_name = item_data.get('name', '')
                artist_name = item_data.get('artist', '')
                if album_name and artist_name:
                    self.enviar_spoti(f"{artist_name} - {album_name}")
                else:
                    print("No hay suficiente información del álbum para buscar")
        else:
            # Es una canción (los datos son el resultado de la consulta)
            # Buscar el enlace de Spotify - Índice 16 en los enlaces originales mostrados en show_details
            spotify_url = None

            # Primero verificamos si tenemos el ID de la canción para buscar en song_links
            if len(item_data) > 0 and item_data[0]:
                song_id = item_data[0]
                spotify_url = self.get_spotify_url_from_db(song_id)

            if spotify_url:
                # Si tenemos una URL de Spotify, la pasamos como argumento
                self.enviar_spoti(spotify_url)
            else:
                # Si no hay URL, creamos un string con "artista - título"
                artist = item_data[3] if len(item_data) > 3 and item_data[3] else ""
                title = item_data[2] if len(item_data) > 2 and item_data[2] else ""

                if artist and title:
                    query = f"{artist} - {title}"
                    self.enviar_spoti(query)
                else:
                    # Mostrar mensaje si no hay suficiente información
                    print("No hay suficiente información para buscar en Spotify")


    def enviar_spoti(self, arg):
        """Envía a Spotify basado en el argumento proporcionado

        Args:
            arg: Puede ser una URL de Spotify o una cadena con 'artista - título'
        """
        try:
            # Verificar si el argumento es una URL de Spotify
            if arg.startswith("https://open.spotify.com/") or arg.startswith("spotify:"):
                # Aquí la lógica para manejar URLs de Spotify directamente
                print(f"Enviando URL de Spotify al creador de listas: {arg}")
                self.switch_tab("Spotify Playlists", "add_track_by_url", arg)
            else:
                self.switch_tab("Spotify Playlists", "search_track_by_query", arg)
                print(f"Buscando en Spotify: {arg}")

        except Exception as e:
            print(f"Error al enviar a Spotify: {e}")


    def get_spotify_url_from_db(self, song_id):
        """Obtiene la URL de Spotify desde la base de datos para una canción específica"""
        try:
            # Conectar a la base de datos
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Consultar la URL de Spotify para el song_id proporcionado
            cursor.execute("SELECT spotify_url FROM song_links WHERE song_id = ?", (song_id,))
            result = cursor.fetchone()

            conn.close()

            # Devolver la URL si existe
            if result and result[0]:
                return result[0]
            return None
        except Exception as e:
            print(f"Error al obtener la URL de Spotify: {e}")
            return None

    def play_selected_item(self):
        """Reproduce el ítem seleccionado en el árbol."""
        if not hasattr(self, 'results_tree') or not self.results_tree:
            return

        item = self.results_tree.currentItem()
        if not item:
            return

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        if isinstance(item_data, dict):
            # Es un artista o álbum
            if item_data.get('type') == 'album':
                self.play_album(item)
        else:
            # Es una canción
            self.play_track(item)


    def open_selected_folder(self):
        """Abre la carpeta del ítem seleccionado en el árbol."""
        if not hasattr(self, 'results_tree') or not self.results_tree:
            return

        item = self.results_tree.currentItem()
        if not item:
            return

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        if isinstance(item_data, dict):
            # Es un artista o álbum
            if item_data.get('type') == 'album':
                self.open_album_folder(item)
        else:
            # Es una canción
            self.open_track_folder(item_data)


    def play_item(self):
        """Reproduce el ítem seleccionado con verificaciones de seguridad."""
        current = self.results_list.currentItem()
        if not current:
            print("No hay ítem seleccionado")
            return

        # Verificar si es un header
        if getattr(current, 'is_header', False):
            self.play_album()
            return

        # Obtener los datos del ítem
        data = current.data(Qt.ItemDataRole.UserRole)
        if not data:
            print("No hay datos asociados al ítem")
            return

        try:
            file_path = data[1]  # Índice 1 contiene file_path
            if not file_path or not os.path.exists(file_path):
                print(f"Ruta de archivo no válida: {file_path}")
                return

            subprocess.Popen([reproductor, file_path])
        except (IndexError, TypeError) as e:
            print(f"Error al acceder a los datos del ítem: {e}")
        except Exception as e:
            print(f"Error al reproducir el archivo: {e}")

    def play_album(self, album_item):
        """
        Reproduce todas las pistas de un álbum.

        Args:
            album_item: Elemento del árbol que representa un álbum.
        """
        # Verificar que es un álbum
        item_data = album_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or not isinstance(item_data, dict) or item_data.get('type') != 'album':
            return

        # Recolectar todas las rutas de archivo del álbum
        album_paths = []

        for i in range(album_item.childCount()):
            track_item = album_item.child(i)
            track_data = track_item.data(0, Qt.ItemDataRole.UserRole)
            if track_data and len(track_data) > 1:
                file_path = track_data[1]
                if file_path and os.path.exists(file_path):
                    album_paths.append(file_path)

        if album_paths:
            subprocess.Popen([reproductor] + album_paths)
        else:
            print("No se encontraron archivos válidos para reproducir")

    def open_folder(self):
        """Abre la carpeta del ítem seleccionado."""
        current = self.results_list.currentItem()
        if not current:
            return

        if getattr(current, 'is_header', True):
            # Si es un header, abrir la carpeta del primer archivo del álbum
            self.open_album_folder()

        try:
            if getattr(current, 'is_header', False):
                # Si es un header, abrir la carpeta del primer archivo del álbum
                index = self.results_list.row(current) + 1
                if index < self.results_list.count():
                    item = self.results_list.item(index)
                    if item:
                        data = item.data(Qt.ItemDataRole.UserRole)
                        if data and len(data) > 1:
                            file_path = data[1]
                        else:
                            return
                else:
                    return
            else:
                # Si es una canción individual
                data = current.data(Qt.ItemDataRole.UserRole)
                if not data or len(data) <= 1:
                    return
                file_path = data[1]

            if file_path and os.path.exists(file_path):
                folder_path = str(Path(file_path).parent)
                subprocess.Popen(['thunar', folder_path])
            else:
                print(f"Ruta no válida: {file_path}")

        except Exception as e:
            print(f"Error al abrir la carpeta: {e}")

    def open_album_folder(self, album_item):
        """
        Abre la carpeta de un álbum.

        Args:
            album_item: Elemento del árbol que representa un álbum.
        """
        # Verificar que es un álbum
        item_data = album_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or not isinstance(item_data, dict) or item_data.get('type') != 'album':
            return

        # Usar la primera pista del álbum para obtener la ruta
        if album_item.childCount() > 0:
            track_item = album_item.child(0)
            track_data = track_item.data(0, Qt.ItemDataRole.UserRole)
            if track_data:
                self.open_track_folder(track_data)

    def open_track_folder(self, track_data):
        """
        Abre la carpeta de una pista.

        Args:
            track_data: Datos de la pista (resultado de la consulta).
        """
        try:
            if len(track_data) > 1:
                file_path = track_data[1]
                if file_path and os.path.exists(file_path):
                    folder_path = str(Path(file_path).parent)
                    subprocess.Popen(['thunar', folder_path])
                else:
                    print(f"Ruta no válida: {file_path}")
        except Exception as e:
            print(f"Error al abrir la carpeta: {e}")


    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab:
            # Alternar entre la caja de búsqueda y el árbol de resultados
            if self.search_box.hasFocus():
                # Verificar si results_tree existe y es válido
                if self.is_tree_valid():
                    self.results_tree.setFocus()
            else:
                self.search_box.setFocus()
            event.accept()
            return

        # Solo procesar las flechas si el árbol de resultados existe, es válido y tiene el foco
        if self.is_tree_valid() and self.results_tree.hasFocus():
            if event.key() in [Qt.Key.Key_Left, Qt.Key.Key_Right]:
                self.navigate_tree_headers(event.key())
                event.accept()
                return

        # Verificar si results_tree existe antes de usarlo
        if hasattr(self, 'results_tree') and self.results_tree:
            current_item = self.results_tree.currentItem()
            if current_item:
                item_data = current_item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(item_data, dict) and item_data.get('type') == 'album':
                    if event.key() == Qt.Key.Key_Return:
                        self.play_album(current_item)
                        event.accept()
                        return
                    elif event.key() == Qt.Key.Key_O and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                        self.open_album_folder(current_item)
                        event.accept()
                        return

        super().keyPressEvent(event)


    def navigate_tree_headers(self, key):
        """Navega entre los elementos de nivel superior del árbol (artistas)."""
        if not hasattr(self, 'results_tree') or not self.results_tree:
            return

        current_item = self.results_tree.currentItem()
        if not current_item:
            return

        # Encontrar el elemento de nivel superior (artista) actual
        top_level_item = current_item
        while top_level_item.parent():
            top_level_item = top_level_item.parent()

        current_index = self.results_tree.indexOfTopLevelItem(top_level_item)
        if current_index == -1:
            return

        # Navegar al siguiente o anterior elemento de nivel superior
        new_index = current_index
        if key == Qt.Key.Key_Right:
            new_index = min(current_index + 1, self.results_tree.topLevelItemCount() - 1)
        else:  # key == Qt.Key.Key_Left
            new_index = max(current_index - 1, 0)

        if new_index != current_index:
            new_item = self.results_tree.topLevelItem(new_index)
            self.results_tree.setCurrentItem(new_item)
            self.results_tree.scrollToItem(new_item, QAbstractItemView.ScrollHint.PositionAtCenter)


    # def navigate_headers(self, key):
    #     """Navega entre los headers de álbumes usando las flechas izquierda/derecha."""
    #     current_row = self.results_list.currentRow()
    #     if current_row == -1:
    #         return

    #     total_items = self.results_list.count()
    #     header_positions = []

    #     # Encontrar todas las posiciones de los headers
    #     for i in range(total_items):
    #         item = self.results_list.item(i)
    #         if item and getattr(item, 'is_header', False):
    #             header_positions.append(i)

    #     if not header_positions:
    #         return

    #     # Encontrar el header actual o el más cercano
    #     current_header_index = -1
    #     for i, pos in enumerate(header_positions):
    #         if key == Qt.Key.Key_Right:
    #             # Para flecha derecha, buscar el siguiente header
    #             if pos > current_row:
    #                 current_header_index = i
    #                 break
    #         else:
    #             # Para flecha izquierda, buscar el header anterior
    #             if pos >= current_row:
    #                 current_header_index = i - 1
    #                 break

    #     # Si no encontramos un header siguiente, ir al primero
    #     if key == Qt.Key.Key_Right and current_header_index == -1:
    #         current_header_index = 0
    #     # Si no encontramos un header anterior, ir al último
    #     elif key == Qt.Key.Key_Left and current_header_index == -1:
    #         current_header_index = len(header_positions) - 1

    #     # Asegurarse de que el índice es válido
    #     if 0 <= current_header_index < len(header_positions):
    #         # Seleccionar el nuevo header
    #         new_row = header_positions[current_header_index]
    #         self.results_list.setCurrentRow(new_row)
    #         self.results_list.scrollToItem(
    #             self.results_list.item(new_row),
    #             QAbstractItemView.ScrollHint.PositionAtCenter
    #         )


    def run_custom_script(self, script_num):
        current = self.results_list.currentItem()
        if not current:
            return

        data = current.data(Qt.ItemDataRole.UserRole)
        # Definir los scripts aquí o cargarlos desde configuración
        scripts = {
            1: '/path/to/script1.sh',
            2: '/path/to/script2.sh',
            3: '/path/to/script3.sh'
        }

        if script_num in scripts and os.path.exists(scripts[script_num]):
            subprocess.Popen([scripts[script_num], data[1]])



    def load_results_tree_ui(self):
        """Este método ya no se usa directamente"""
        print("ADVERTENCIA: load_results_tree_ui() está obsoleto, usa _load_results_tree()")
        return False



    def setup_results_tree(self):
        """Configura el árbol de resultados con sus propiedades y señales."""
        if not hasattr(self, 'results_tree') or self.results_tree is None:
            print("Cargando árbol de resultados por primera vez")
            try:
                if not self.load_results_tree_ui():
                    print("Advertencia: No se pudo cargar el árbol de resultados dinámicamente.")
                    self._create_fallback_tree()
            except Exception as e:
                print(f"Error al cargar el árbol de resultados: {e}")
                traceback.print_exc()
                self._create_fallback_tree()
        else:
            print("El árbol de resultados ya existe, no es necesario cargarlo nuevamente")

        # Configurar el aspecto del árbol
        self.results_tree.setAlternatingRowColors(False)
        self.results_tree.setHeaderHidden(False)
        self.results_tree.setColumnCount(3)
        self.results_tree.setHeaderLabels(["Artistas / Álbumes / Canciones", "Año", "Género"])

        # Ajustar el tamaño de las columnas
        self.results_tree.setColumnWidth(0, 250)  # Nombre más amplio
        self.results_tree.setColumnWidth(1, 60)   # Año más estrecho
        self.results_tree.setColumnWidth(2, 90)  # Género tamaño medio

        # Configurar la selección
        self.results_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Configurar eventos
        self.results_tree.currentItemChanged.connect(self.handle_tree_item_change)
        self.results_tree.itemDoubleClicked.connect(self.handle_tree_item_double_click)
        self.results_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_tree.customContextMenuRequested.connect(self.show_tree_context_menu)

        # Permitir expandir/colapsar con doble clic y teclas
        self.results_tree.setExpandsOnDoubleClick(True)

        # Configurar arrastrar y soltar para playlist
        self.results_tree.setDragEnabled(True)
        self.results_tree.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

    def update_results_tree(self, results):
        """
        Actualiza el árbol de resultados con los resultados de búsqueda.
        Organiza los resultados en una estructura jerárquica: Artista > Álbum > Canción

        Args:
            results: Lista de tuplas con los resultados de la búsqueda.
        """
        if not hasattr(self, 'results_tree') or self.results_tree is None:
            print("No se encuentra el árbol de resultados")
            return

        # Limpiar el árbol
        self.results_tree.clear()

        # Organizar los resultados por artista > álbum > canción
        artists = {}

        for row in results:
            artist = row[3] if row[3] else "Sin artista"
            album = row[5] if row[5] else "Sin álbum"
            title = row[2] if row[2] else "Sin título"
            date = row[6] if row[6] else ""
            year = date.split('-')[0] if date and '-' in date else date
            genre = row[7] if row[7] else ""
            track_number = row[14] if row[14] else "0"

            # Crear estructura anidada
            if artist not in artists:
                artists[artist] = {}

            album_key = f"{album}"
            if album_key not in artists[artist]:
                artists[artist][album_key] = []

            # Añadir la canción con su número de pista
            track_info = {
                'number': track_number,
                'title': title,
                'data': row,
                'year': year,
                'genre': genre
            }
            artists[artist][album_key].append(track_info)

        # Añadir elementos al árbol
        for artist_name, albums in artists.items():
            # Crear elemento de artista
            artist_item = QTreeWidgetItem(self.results_tree)
            artist_item.setText(0, artist_name)
            artist_item.setIcon(0, self.get_artist_icon())
            artist_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'artist', 'name': artist_name})

            # Añadir álbumes como hijos del artista
            for album_name, tracks in albums.items():
                # Obtener información del álbum del primer track
                album_year = tracks[0]['year'] if tracks else ""
                album_genre = tracks[0]['genre'] if tracks else ""

                # Crear elemento de álbum
                album_item = QTreeWidgetItem(artist_item)
                album_item.setText(0, album_name)
                album_item.setText(1, album_year)
                album_item.setText(2, album_genre)
                album_item.setIcon(0, self.get_album_icon())
                album_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'album',
                    'name': album_name,
                    'artist': artist_name,
                    'year': album_year,
                    'genre': album_genre
                })

                # Ordenar las pistas por número
                try:
                    tracks.sort(key=lambda x: int(x['number']) if x['number'].isdigit() else float('inf'))
                except (ValueError, AttributeError):
                    # En caso de error, no ordenar
                    pass

                # Añadir canciones como hijos del álbum
                for track in tracks:
                    try:
                        track_num = int(track['number'])
                        display_text = f"{track_num:02d}. {track['title']}"
                    except (ValueError, TypeError):
                        display_text = f"--. {track['title']}"

                    # Crear elemento de canción
                    track_item = QTreeWidgetItem(album_item)
                    track_item.setText(0, display_text)
                    track_item.setText(1, track['year'])
                    track_item.setText(2, track['genre'])
                    track_item.setIcon(0, self.get_track_icon())
                    track_item.setData(0, Qt.ItemDataRole.UserRole, track['data'])

        # Expandir los artistas para mostrar los álbumes
        for i in range(self.results_tree.topLevelItemCount()):
            self.results_tree.topLevelItem(i).setExpanded(True)

        # Mostrar información en la barra de estado si está disponible
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(f"Encontrados {len(results)} resultados")

    def get_artist_icon(self):
        """Retorna un icono para representar artistas en el árbol."""
        return self.style().standardIcon(QStyle.StandardPixmap.SP_CommandLink)

    def get_album_icon(self):
        """Retorna un icono para representar álbumes en el árbol."""
        return self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)

    def get_track_icon(self):
        """Retorna un icono para representar canciones en el árbol."""
        return self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def handle_tree_item_change(self, current, previous):
        """
        Maneja el cambio de selección en el árbol.
        Muestra la información del elemento seleccionado.

        Args:
            current: Elemento actual seleccionado.
            previous: Elemento previamente seleccionado.
        """
        if not current:
            self.clear_details()
            return

        try:
            # Obtener datos del elemento
            item_data = current.data(0, Qt.ItemDataRole.UserRole)

            if not item_data:
                self.clear_details()
                return

            # Determinar qué tipo de elemento es
            if isinstance(item_data, dict):
                # Es un artista o álbum
                if item_data.get('type') == 'artist':
                    # Verificar que tenemos los widgets necesarios antes de mostrar info
                    if not hasattr(self, 'lastfm_label') or not self.lastfm_label:
                        print("lastfm_label no disponible, reconfigurando widgets...")
                        self.setup_info_widget()
                    self.show_artist_info(current)
                elif item_data.get('type') == 'album':
                    # Verificar que tenemos los widgets necesarios antes de mostrar info
                    if not hasattr(self, 'lastfm_label') or not self.lastfm_label:
                        print("lastfm_label no disponible, reconfigurando widgets...")
                        self.setup_info_widget()
                    self.show_album_info(current)
                else:
                    self.clear_details()
            else:
                # Es una canción (los datos son el resultado de la consulta)
                self.show_details(current, previous)
        except Exception as e:
            print(f"Error en handle_tree_item_change: {e}")
            traceback.print_exc()
            self.clear_details()

    def handle_tree_item_double_click(self, item, column):
        """
        Maneja el doble clic en un elemento del árbol.
        Si es una canción, la reproduce.
        Si es un artista, simplemente lo expande.

        Args:
            item: Elemento en el que se hizo doble clic.
            column: Columna en la que se hizo clic.
        """
        # Obtener datos del elemento
        item_data = item.data(0, Qt.ItemDataRole.UserRole)

        if not item_data:
            return

        # Determinar qué tipo de elemento es
        if isinstance(item_data, dict):
            # Es un artista o álbum
            if item_data.get('type') == 'artist':
                # Expandir/colapsar artista
                item.setExpanded(not item.isExpanded())
            elif item_data.get('type') == 'album':
                # Reproducir el álbum directamente
                self.play_album(item)
        else:
            # Es una canción, la reproducimos
            self.play_track(item)


    def play_track(self, track_item):
        """
        Reproduce una pista.

        Args:
            track_item: Elemento del árbol que representa una canción.
        """
        # Obtener datos de la pista
        track_data = track_item.data(0, Qt.ItemDataRole.UserRole)
        if not track_data:
            return

        try:
            file_path = track_data[1]  # Índice 1 contiene file_path
            if not file_path or not os.path.exists(file_path):
                print(f"Ruta de archivo no válida: {file_path}")
                return

            subprocess.Popen([reproductor, file_path])
        except (IndexError, TypeError) as e:
            print(f"Error al acceder a los datos de la pista: {e}")
        except Exception as e:
            print(f"Error al reproducir el archivo: {e}")

    def show_tree_context_menu(self, position):
        """
        Muestra un menú contextual para el árbol de resultados.

        Args:
            position: Posición donde se hizo clic derecho.
        """
        # Obtener el elemento bajo el cursor
        item = self.results_tree.itemAt(position)
        if not item:
            return

        # Crear menú contextual
        context_menu = QMenu(self)

        # Obtener datos del elemento
        item_data = item.data(0, Qt.ItemDataRole.UserRole)

        if isinstance(item_data, dict):
            # Es un artista o álbum
            if item_data.get('type') == 'artist':
                # Opciones para artista
                context_menu.addAction("Expandir/Colapsar", lambda: item.setExpanded(not item.isExpanded()))
                context_menu.addAction("Ver detalles del artista", lambda: self.show_artist_info(item))
                context_menu.addAction("Añadir todos los álbumes a la playlist", lambda: self.add_artist_to_playlist(item))
            elif item_data.get('type') == 'album':
                # Opciones para álbum
                context_menu.addAction("Reproducir álbum", lambda: self.play_album(item))
                context_menu.addAction("Añadir álbum a playlist", lambda: self.add_album_to_playlist(item))
                context_menu.addAction("Abrir carpeta del álbum", lambda: self.open_album_folder(item))
        else:
            # Es una canción
            context_menu.addAction("Reproducir", lambda: self.play_track(item))
            context_menu.addAction("Añadir a playlist", lambda: self.add_track_to_playlist(item_data))
            context_menu.addAction("Abrir carpeta", lambda: self.open_track_folder(item_data))

        # Mostrar el menú
        context_menu.exec(self.results_tree.viewport().mapToGlobal(position))

    def show_artist_info(self, artist_item):
        """
        Muestra información detallada de un artista.

        Args:
            artist_item: Elemento del árbol que representa un artista.
        """
        # Verificar que es un artista
        item_data = artist_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or not isinstance(item_data, dict) or item_data.get('type') != 'artist':
            return

        artist_name = item_data.get('name', 'Desconocido')

        # Verificar que los widgets necesarios estén disponibles
        if not all([hasattr(self, 'lastfm_label'), hasattr(self, 'metadata_label')]):
            print("Error: Widgets de información no disponibles, reconfigurando...")
            self.setup_info_widget()

        # Si aún no tenemos los widgets, mostrar un mensaje de error y salir
        if not hasattr(self, 'lastfm_label') or not self.lastfm_label:
            print("Error crítico: lastfm_label no disponible después de reconfigurar")
            return

        if not hasattr(self, 'metadata_label') or not self.metadata_label:
            print("Error crítico: metadata_label no disponible después de reconfigurar")
            return

        # Buscar información del artista en la base de datos
        artist_db_info = self.get_artist_info_from_db(artist_name)

        # También buscar en el primer track por compatibilidad con el código existente
        first_track_data = None
        for album_idx in range(artist_item.childCount()):
            album_item = artist_item.child(album_idx)
            for track_idx in range(album_item.childCount()):
                track_item = album_item.child(track_idx)
                track_data = track_item.data(0, Qt.ItemDataRole.UserRole)
                if track_data:
                    first_track_data = track_data
                    break
            if first_track_data:
                break

        # Limpiar detalles anteriores
        self.clear_details()

        # Mostrar imagen del artista
        if artist_name and hasattr(self, 'artist_image_label') and self.artist_image_label:
            artist_image_path = self.find_artist_image(artist_name)
            if artist_image_path:
                artist_pixmap = QPixmap(artist_image_path)
                artist_pixmap = artist_pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)
                self.artist_image_label.setPixmap(artist_pixmap)
            else:
                self.artist_image_label.setText("No imagen de artista")

        # Mostrar la información en el panel de detalles
        try:
            # Crear el contenido para el panel de información (LastFM + Wikipedia)
            info_text = ""

            # Mostrar info de LastFM si está disponible
            artist_bio = None

            # Priorizar la bio de la base de datos
            if artist_db_info and artist_db_info.get('bio'):
                artist_bio = artist_db_info['bio']
            # Usar la bio del track si está disponible como respaldo
            elif first_track_data and len(first_track_data) > 15 and first_track_data[15]:
                artist_bio = first_track_data[15]

            if artist_bio:
                info_text += f"<h3>Información del Artista:</h3><div style='white-space: pre-wrap;'>{artist_bio}</div><br><br>"
            else:
                info_text += "<h3>Información del Artista:</h3><p>No hay información disponible</p><br>"

            # Mostrar info de Wikipedia del artista
            wikipedia_content = None
            if artist_db_info and artist_db_info.get('wikipedia_content'):
                wikipedia_content = artist_db_info['wikipedia_content']
            elif first_track_data and len(first_track_data) > 27 and first_track_data[27]:
                wikipedia_content = first_track_data[27]

            if wikipedia_content:
                info_text += f"<h3>Wikipedia - Artista:</h3><div style='white-space: pre-wrap;'>{wikipedia_content}</div><br><br>"

            # Establecer texto en lastfm_label
            if self.lastfm_label:
                self.lastfm_label.setText(info_text)

            # Construir la metadata básica del artista
            metadata = f"<b>Artista:</b> {artist_name}<br>"

            # Añadir información adicional si está disponible
            if artist_db_info:
                if artist_db_info.get('origin'):
                    metadata += f"<b>Origen:</b> {artist_db_info['origin']}<br>"
                if artist_db_info.get('formed_year'):
                    metadata += f"<b>Año de formación:</b> {artist_db_info['formed_year']}<br>"
                if artist_db_info.get('total_albums'):
                    metadata += f"<b>Total de álbumes:</b> {artist_db_info['total_albums']}<br>"
                if artist_db_info.get('tags'):
                    metadata += f"<b>Etiquetas:</b> {artist_db_info['tags']}<br>"

            # Contar álbumes desde el árbol
            albums_count = artist_item.childCount()
            if not artist_db_info or not artist_db_info.get('total_albums'):
                metadata += f"<b>Álbumes encontrados:</b> {albums_count}<br>"

            metadata += "<br>"

            # Añadir enlaces externos del artista
            metadata += "<b>Enlaces del Artista:</b><br>"

            artist_links = []

            # Priorizar enlaces de la base de datos
            if artist_db_info:
                if artist_db_info.get('spotify_url'):
                    artist_links.append(f"<a href='{artist_db_info['spotify_url']}'>Spotify</a>")
                if artist_db_info.get('youtube_url'):
                    artist_links.append(f"<a href='{artist_db_info['youtube_url']}'>YouTube</a>")
                if artist_db_info.get('musicbrainz_url'):
                    artist_links.append(f"<a href='{artist_db_info['musicbrainz_url']}'>MusicBrainz</a>")
                if artist_db_info.get('discogs_url'):
                    artist_links.append(f"<a href='{artist_db_info['discogs_url']}'>Discogs</a>")
                if artist_db_info.get('rateyourmusic_url'):
                    artist_links.append(f"<a href='{artist_db_info['rateyourmusic_url']}'>RateYourMusic</a>")
                if artist_db_info.get('wikipedia_url'):
                    artist_links.append(f"<a href='{artist_db_info['wikipedia_url']}'>Wikipedia</a>")
                if artist_db_info.get('bandcamp_url'):
                    artist_links.append(f"<a href='{artist_db_info['bandcamp_url']}'>Bandcamp</a>")
                if artist_db_info.get('lastfm_url'):
                    artist_links.append(f"<a href='{artist_db_info['lastfm_url']}'>Last.fm</a>")
            # Usar enlaces del track como respaldo
            elif first_track_data and len(first_track_data) > 16:
                if first_track_data[16]:  # spotify_url
                    artist_links.append(f"<a href='{first_track_data[16]}'>Spotify</a>")
                if first_track_data[17]:  # youtube_url
                    artist_links.append(f"<a href='{first_track_data[17]}'>YouTube</a>")
                if first_track_data[18]:  # musicbrainz_url
                    artist_links.append(f"<a href='{first_track_data[18]}'>MusicBrainz</a>")
                if first_track_data[19]:  # discogs_url
                    artist_links.append(f"<a href='{first_track_data[19]}'>Discogs</a>")
                if first_track_data[20]:  # rateyourmusic_url
                    artist_links.append(f"<a href='{first_track_data[20]}'>RateYourMusic</a>")
                if first_track_data[26]:  # artist_wikipedia_url
                    artist_links.append(f"<a href='{first_track_data[26]}'>Wikipedia</a>")

            if artist_links:
                metadata += " | ".join(artist_links)
            else:
                metadata += "No hay enlaces disponibles."

            # Establecer texto en metadata_label
            if self.metadata_label:
                self.metadata_label.setText(metadata)
                self.metadata_label.setOpenExternalLinks(True)

            # Actualizar otros labels si existen
            if hasattr(self, 'links_label') and self.links_label:
                # Construir enlaces
                links_text = "<h3>Enlaces:</h3>"
                if artist_links:
                    links_text += f"<p><b>Artista {artist_name}:</b> {' | '.join(artist_links)}</p>"
                self.links_label.setText(links_text)

            if hasattr(self, 'wikipedia_artist_label') and self.wikipedia_artist_label:
                if wikipedia_content:
                    self.wikipedia_artist_label.setText(f"<h3>Wikipedia - Artista:</h3><div style='white-space: pre-wrap;'>{wikipedia_content}</div>")
                else:
                    self.wikipedia_artist_label.setText("")
        except Exception as e:
            print(f"Error al mostrar información del artista: {e}")
            traceback.print_exc()

            # En caso de error, mostrar información básica
            if self.lastfm_label:
                self.lastfm_label.setText(f"<h3>Artista: {artist_name}</h3><p>Error al cargar información detallada: {str(e)}</p>")
            if self.metadata_label:
                self.metadata_label.setText(f"<b>Artista:</b> {artist_name}<br><b>Error:</b> No se pudo cargar información adicional.")




if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Navegador de música')
    parser.add_argument('db_path', help='Ruta a la base de datos SQLite')
    parser.add_argument('--font', default='Inter', help='Fuente a usar en la interfaz')
    parser.add_argument('--artist-images-dir', help='Carpeta donde buscar las imágenes de los artistas')

    args = parser.parse_args()

    app = QApplication(sys.argv)
    browser = MusicBrowser(
        args.db_path,
        font_family=args.font,
        artist_images_dir=args.artist_images_dir
    )
    browser.show()
    sys.exit(app.exec())