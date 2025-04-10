import sys
import os
import json
from pathlib import Path
import subprocess
import requests
import logging
import datetime
from PyQt6 import uic
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
                             QLabel, QLineEdit, QMessageBox, QApplication, QFileDialog, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QDialog, QCheckBox, QScrollArea, QDialogButtonBox)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QTextDocument

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule, THEMES, PROJECT_ROOT

# Configure logging
try:
    from loggin_helper import setup_module_logger
    logger = setup_module_logger(
        module_name="MuspyArtistModule",
        log_level="INFO",
        log_types=["ERROR", "INFO", "WARNING", "UI"]
    )
except ImportError:
    # Fallback a logging estándar si no está disponible terminal_logger
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MuspyArtistModule")


# Añade esto después de importar terminal_logger
class PyQtFilter(logging.Filter):
    def filter(self, record):
        # Filtrar mensajes de PyQt
        if record.name.startswith('PyQt6'):
            return False
        return True

# Y aplica el filtro al logger global
logging.getLogger().addFilter(PyQtFilter())


class MuspyArtistModule(BaseModule):
    def __init__(self, 
                muspy_username=None, 
                muspy_api_key=None,
                muspy_password=None,
                muspy_id=None,
                artists_file=None,
                query_db_script_path=None,
                search_mbid_script_path=None,
                lastfm_username=None,
                parent=None, 
                db_path='music_database.db',
                theme='Tokyo Night', 
                *args, **kwargs):
        """
        Initialize the Muspy Artist Management Module
        
        Args:
            muspy_username (str, optional): Muspy username
            muspy_api_key (str, optional): Muspy API key
            artists_file (str, optional): Path to artists file
            query_db_script_path (str, optional): Path to MBID query script
            search_mbid_script_path (str, optional): Path to MBID search script
            parent (QWidget, optional): Parent widget
            theme (str, optional): UI theme
        """
        # Configuración de logging primero
        self.module_name = self.__class__.__name__
        
        # Obtener configuración de logging
        self.log_config = kwargs.get('logging', {})
        self.log_level = self.log_config.get('log_level', 'INFO')
        self.enable_logging = self.log_config.get('debug_enabled', False)
        self.log_types = self.log_config.get('log_types', ['ERROR', 'INFO'])
        
        # Propiedades de Muspy
        self.muspy_username = muspy_username
        self.muspy_password = muspy_password
        self.muspy_api_key = muspy_api_key
        self.muspy_id = muspy_api_key
        
        # Intentar obtener el Muspy ID si no está configurado
        if not self.muspy_id or self.muspy_id == '' or self.muspy_id == 'None':
            self.get_muspy_id()
            
        self.base_url = "https://muspy.com/api/1"
        self.artists_file = artists_file
        self.query_db_script_path = query_db_script_path
        self.lastfm_username = lastfm_username
        self.db_path = db_path

        # Usar logger específico para este módulo si está habilitado
        if self.enable_logging:
            try:
                from terminal_logger import setup_module_logger
                self.logger = setup_module_logger(
                    module_name=self.module_name,
                    log_level=self.log_level,
                    log_types=self.log_types
                )
                global logger
                logger = self.logger  # Actualiza la referencia global
            except ImportError:
                self.logger = logger  # Usar el logger global
        else:
            self.logger = logger  # Usar el logger global

        self.available_themes = kwargs.pop('temas', [])
        self.selected_theme = kwargs.pop('tema_seleccionado', theme)        
        
        # Llamar al constructor de la superclase AL FINAL
        super().__init__(parent, theme, **kwargs)
        

   # Actualización del método init_ui en la clase MuspyArtistModule
    def init_ui(self):
        """Initialize the user interface for Muspy artist management"""
        # Lista de widgets requeridos
        required_widgets = [
            'artist_input', 'search_button', 'results_text', 
            'load_artists_button', 'sync_artists_button', 'sync_lastfm_button',
            'get_releases_button', 'get_new_releases_button', 'get_my_releases_button'
        ]
        
        # Intentar cargar desde archivo UI
        ui_file_path = os.path.join(PROJECT_ROOT, "ui", "muspy_releases_module.ui")
        
        if os.path.exists(ui_file_path):
            try:
                # Cargar el archivo UI
                uic.loadUi(ui_file_path, self)
                
                # Verificar que se han cargado los widgets principales
                missing_widgets = []
                for widget_name in required_widgets:
                    if not hasattr(self, widget_name) or getattr(self, widget_name) is None:
                        widget = self.findChild(QWidget, widget_name)
                        if widget:
                            setattr(self, widget_name, widget)
                        else:
                            missing_widgets.append(widget_name)
                
                if missing_widgets:
                    logger.error(f"Widgets no encontrados en UI: {', '.join(missing_widgets)}")
                    raise AttributeError(f"Widgets no encontrados en UI: {', '.join(missing_widgets)}")
                
                # Configuración adicional después de cargar UI
                self._connect_signals()
                
                logger.ui(f"UI MuspyArtistModule cargada desde {ui_file_path}")
            except Exception as e:
                logger.error(f"Error cargando UI MuspyArtistModule desde archivo: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                self._fallback_init_ui()
        else:
            logger.ui(f"Archivo UI MuspyArtistModule no encontrado: {ui_file_path}, usando creación manual")
            self._fallback_init_ui()

    def _fallback_init_ui(self):
        """Método de respaldo para crear la UI manualmente si el archivo UI falla."""
        # Main vertical layout
        main_layout = QVBoxLayout(self)

        # Top section with search
        top_layout = QHBoxLayout()
        
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Introduce el nombre de un artista para buscar discos anunciados")
        top_layout.addWidget(self.artist_input)

        self.search_button = QPushButton("Voy a tener suerte")
        top_layout.addWidget(self.search_button)

        main_layout.addLayout(top_layout)

        # Results area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.append("""
            \n\n\n\n
            Leer db: Mostrará una selección con los artistas a escoger para sincronizar con muspy
            Sincronizar artistas: Añadirá los artistas faltantes a Muspy
            Sincronizar Lastfm: Sincronizará artistas seguidos en lastfm en Muspy
            Mis Próximos discos: Buscará lanzamientos anunciados de tus artistas seguidos
            Discos ausentes: Comprobará qué discos de los artistas seleccionados no existe en tu base de datos
            Obtener todo: Obtiene TODO lo anunciado, serán decenas de miles...
            \n\n\n\n
            """)
        main_layout.addWidget(self.results_text)

        # Bottom buttons layout
        bottom_layout = QHBoxLayout()
        
        self.load_artists_button = QPushButton("Leer db")
        bottom_layout.addWidget(self.load_artists_button)

        self.sync_artists_button = QPushButton("Sincronizar Artistas")
        bottom_layout.addWidget(self.sync_artists_button)

        self.sync_lastfm_button = QPushButton("Sync Lastfm")
        bottom_layout.addWidget(self.sync_lastfm_button)
        
        self.get_releases_button = QPushButton("Mis próximos discos")
        bottom_layout.addWidget(self.get_releases_button)
        
        self.get_new_releases_button = QPushButton("Discos ausentes")
        bottom_layout.addWidget(self.get_new_releases_button)
        
        self.get_my_releases_button = QPushButton("Obtener todo...")
        bottom_layout.addWidget(self.get_my_releases_button)

        main_layout.addLayout(bottom_layout)
        
        # Conectar señales
        self._connect_signals()

    def _connect_signals(self):
        """Conectar las señales de los widgets a sus respectivos slots."""
        # Conectar la señal de búsqueda
        self.search_button.clicked.connect(self.search_and_get_releases)
        self.artist_input.returnPressed.connect(self.search_and_get_releases)
        
        # Conectar las señales de los botones de acción
        self.load_artists_button.clicked.connect(self.load_artists_from_file)
        self.sync_artists_button.clicked.connect(self.sync_artists_with_muspy)
        self.sync_lastfm_button.clicked.connect(self.sync_lastfm_muspy)
        self.get_releases_button.clicked.connect(self.get_muspy_releases)
        self.get_new_releases_button.clicked.connect(self.get_new_releases)
        self.get_my_releases_button.clicked.connect(self.get_all_my_releases)


    def get_muspy_id(self):
        """
        Obtiene el ID de usuario de Muspy si no está configurado
        
        Returns:
            str: ID de usuario de Muspy
        """
        if not self.muspy_id and self.muspy_username and self.muspy_api_key:
            try:
                url = f"{self.base_url}/user"
                auth = (self.muspy_username, self.muspy_api_key)
                
                response = requests.get(url, auth=auth)
                
                if response.status_code == 200:
                    # La API devuelve información del usuario en el formato JSON
                    # Intentamos obtener el ID directamente de la respuesta
                    user_info_url = f"{self.base_url}/user"
                    user_response = requests.get(user_info_url, auth=auth)
                    
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        if 'userid' in user_data:
                            self.muspy_id = user_data['userid']
                            logger.debug(f"Muspy ID obtenido: {self.muspy_id}")
                            return self.muspy_id
                        else:
                            logger.error("No se encontró 'userid' en la respuesta JSON")
                    else:
                        logger.error(f"Error al obtener información del usuario: {user_response.status_code}")
                else:
                    logger.error(f"Error en la llamada a la API de Muspy: {response.status_code}")
            except Exception as e:
                logger.error(f"Error al obtener Muspy ID: {e}")
        
        return self.muspy_id


    def load_artists_from_file(self):
        """
        Ejecuta un script para cargar artistas desde la base de datos, 
        muestra un diálogo con checkboxes para seleccionar artistas y
        guarda los seleccionados en un archivo JSON
        """
        try:
            # Asegurar que tenemos PROJECT_ROOT
            self.results_text.append(f"PROJECT_ROOT: {PROJECT_ROOT}")

            # Construir la ruta al script
            script_path = PROJECT_ROOT / "base_datos" / "tools" / "consultar_items_db.py"
            
            # Ejecutar el script de consulta
            self.results_text.clear()
            self.results_text.append("Ejecutando consulta de artistas en la base de datos...")
            QApplication.processEvents()  # Actualizar UI
            
            cmd = f"python {script_path} --db {self.db_path} --buscar artistas"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.results_text.append(f"Error al ejecutar el script: {result.stderr}")
                return
            
            # Cargar los resultados como JSON
            try:
                artists_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                self.results_text.append(f"Error al procesar la salida del script: {e}")
                return
            
            # Verificar si hay artistas
            if not artists_data:
                self.results_text.append("No se encontraron artistas en la base de datos.")
                return
            
            # Cargar artistas existentes si el archivo ya existe
            json_path = PROJECT_ROOT / ".content" / "cache" / "artists_selected.json"
            existing_artists = []
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        existing_artists = json.load(f)
                except Exception as e:
                    self.results_text.append(f"Error al cargar artistas existentes: {e}")
            
            # Crear una lista de nombres de artistas existentes para verificaciones más rápidas
            existing_names = {artist["nombre"] for artist in existing_artists}
            
            # Crear el diálogo usando el archivo UI
            dialog = QDialog(self)
            ui_file_path = os.path.join(PROJECT_ROOT, "ui", "muspy_artist_selection_dialog.ui")
            if os.path.exists(ui_file_path):
                try:
                    # Cargar el archivo UI
                    uic.loadUi(ui_file_path, dialog)
                    
                    # Actualizar la etiqueta con el número de artistas
                    dialog.info_label.setText(f"Selecciona los artistas que deseas guardar ({len(artists_data)} encontrados)")
                    
                    # Limpiar los artistas de ejemplo que vienen en el UI
                    for i in reversed(range(dialog.scroll_layout.count())):
                        widget = dialog.scroll_layout.itemAt(i).widget()
                        if widget is not None:
                            widget.deleteLater()
                    
                    # Crear checkboxes para cada artista
                    checkboxes = []
                    for artist in artists_data:
                        checkbox = QCheckBox(f"{artist['nombre']} ({artist['mbid']})")
                        checkbox.setChecked(artist['nombre'] in existing_names)  # Pre-seleccionar si ya existe
                        checkbox.setProperty("artist_data", artist)  # Almacenar datos del artista en el checkbox
                        checkboxes.append(checkbox)
                        dialog.scroll_layout.addWidget(checkbox)
                    
                    # Conectar señales
                    dialog.search_input.textChanged.connect(lambda text: self.filter_artists(text, checkboxes))
                    dialog.select_all_button.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes if cb.isVisible()])
                    dialog.deselect_all_button.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes if cb.isVisible()])
                    dialog.buttons.accepted.connect(dialog.accept)
                    dialog.buttons.rejected.connect(dialog.reject)
                except Exception as e:
                    self.results_text.append(f"Error cargando UI de selección de artistas: {e}")
                    return
            else:
                self.results_text.append(f"Archivo UI no encontrado: {ui_file_path}, usando creación manual")
                self._fallback_artist_selection_dialog(dialog, artists_data, existing_names)
            
            # Mostrar el diálogo
            if dialog.exec() == 1:  # 1 generalmente significa "aceptado"
                self.results_text.append("Diálogo aceptado, procesando selección...")
            else:
                self.results_text.append("Operación cancelada por el usuario.")
                return
            
            # Recopilar artistas seleccionados
            selected_artists = []
            for i in range(dialog.scroll_layout.count()):
                widget = dialog.scroll_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox) and widget.isChecked():
                    selected_artists.append(widget.property("artist_data"))
            
            # Guardar artistas seleccionados en JSON
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(selected_artists, f, ensure_ascii=False, indent=2)
                
                # Actualizar artists en la instancia
                self.artists = [artist["nombre"] for artist in selected_artists]
                
                self.results_text.append(f"Se guardaron {len(selected_artists)} artistas en {json_path}")
            except Exception as e:
                self.results_text.append(f"Error al guardar los artistas: {e}")
        
        except Exception as e:
            self.results_text.append(f"Error: {str(e)}")
            logger.error(f"Error en load_artists_from_file: {e}", exc_info=True)

    def _fallback_artist_selection_dialog(self, dialog, artists_data, existing_names):
        """
        Método de respaldo para crear el diálogo de selección de artistas manualmente
        si el archivo UI no se encuentra.
        
        Args:
            dialog (QDialog): Diálogo a configurar
            artists_data (list): Lista de datos de artistas
            existing_names (set): Conjunto de nombres de artistas existentes
        """
        dialog.setWindowTitle("Seleccionar Artistas")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(600)
        
        # Layout principal
        layout = QVBoxLayout(dialog)
        
        # Etiqueta informativa
        info_label = QLabel(f"Selecciona los artistas que deseas guardar ({len(artists_data)} encontrados)")
        layout.addWidget(info_label)
        
        # Campo de búsqueda
        search_layout = QHBoxLayout()
        search_label = QLabel("Buscar:")
        search_input = QLineEdit()
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_input)
        layout.addLayout(search_layout)
        
        # Área de scroll con checkboxes
        scroll_area = QWidget()
        scroll_layout = QVBoxLayout(scroll_area)
        
        # Lista para almacenar los checkboxes
        checkboxes = []
        
        # Crear un checkbox para cada artista
        for artist in artists_data:
            checkbox = QCheckBox(f"{artist['nombre']} ({artist['mbid']})")
            checkbox.setChecked(artist['nombre'] in existing_names)  # Pre-seleccionar si ya existe
            checkbox.setProperty("artist_data", artist)  # Almacenar datos del artista en el checkbox
            checkboxes.append(checkbox)
            scroll_layout.addWidget(checkbox)
        
        # Crear área de desplazamiento
        scroll_widget = QScrollArea()
        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(scroll_area)
        layout.addWidget(scroll_widget)
        
        # Botones de selección
        button_layout = QHBoxLayout()
        select_all_button = QPushButton("Seleccionar Todos")
        deselect_all_button = QPushButton("Deseleccionar Todos")
        button_layout.addWidget(select_all_button)
        button_layout.addWidget(deselect_all_button)
        layout.addLayout(button_layout)
        
        # Botones de aceptar/cancelar
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)
        
        # Guardamos referencias para acceder a ellos desde otras funciones
        dialog.scroll_layout = scroll_layout
        dialog.search_input = search_input
        dialog.select_all_button = select_all_button
        dialog.deselect_all_button = deselect_all_button
        dialog.buttons = buttons
        
        # Conectar señales
        search_input.textChanged.connect(lambda text: self.filter_artists(text, checkboxes))
        select_all_button.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes if cb.isVisible()])
        deselect_all_button.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes if cb.isVisible()])
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

    def filter_artists(self, search_text, checkboxes):
        """
        Filtra los artistas en el diálogo según el texto de búsqueda.
        
        Args:
            search_text (str): Texto de búsqueda
            checkboxes (list): Lista de checkboxes de artistas
        """
        search_text = search_text.lower()
        for checkbox in checkboxes:
            artist_data = checkbox.property("artist_data")
            visible = search_text in artist_data["nombre"].lower()
            checkbox.setVisible(visible)

    def search_and_get_releases(self):
        """Search for artist releases without adding to Muspy"""
        artist_name = self.artist_input.text().strip()
        if not artist_name:
            QMessageBox.warning(self, "Error", "Please enter an artist name")
            return

        # Ensure results_text is visible
        self.results_text.show()

        # Get MBID for the artist
        mbid = self.get_mbid_artist_searched(artist_name)
        
        if not mbid:
            QMessageBox.warning(self, "Error", f"Could not find MBID for {artist_name}")
            return
        
        # Store the current artist for possible addition later
        self.current_artist = {"name": artist_name, "mbid": mbid}
        
        # Get releases for the artist
        self.get_artist_releases(mbid, artist_name)

    def get_artist_releases(self, mbid, artist_name=None):
        """
        Get future releases for a specific artist by MBID
        
        Args:
            mbid (str): MusicBrainz ID of the artist
            artist_name (str, optional): Name of the artist for display
        """
        if not self.muspy_username or not self.muspy_api_key:
            QMessageBox.warning(self, "Error", "Muspy configuration not available")
            return

        try:
            url = f"{self.base_url}/releases"
            params = {"mbid": mbid}
            auth = (self.muspy_username, self.muspy_api_key)
            
            response = requests.get(url, auth=auth, params=params)
            
            if response.status_code == 200:
                all_releases = response.json()
                
                # Filter for future releases
                today = datetime.date.today().strftime("%Y-%m-%d")
                future_releases = [release for release in all_releases if release.get('date', '0000-00-00') >= today]
                
                if not future_releases:
                    self.results_text.append(f"No future releases found for {artist_name or 'Unknown'}")
                    return
                
                # Log releases for debugging
                logger.info(f"Received {len(future_releases)} future releases out of {len(all_releases)} total")
                if future_releases:
                    logger.info(f"Sample release data: {future_releases[0]}")
                
                # Display releases in table
                table = self.display_releases_table(future_releases)
                
                # Add a button to follow this artist
                self.add_follow_button = QPushButton(f"Follow {artist_name}")
                self.add_follow_button.clicked.connect(self.follow_current_artist)
                self.layout().insertWidget(self.layout().count() - 1, self.add_follow_button)
            else:
                self.results_text.append(f"Error retrieving releases: {response.status_code} - {response.text}")
        
        except Exception as e:
            self.results_text.append(f"Connection error with Muspy: {e}")
            logger.error(f"Error getting releases: {e}")

    def follow_current_artist(self):
        """Follow the currently displayed artist"""
        if hasattr(self, 'current_artist') and self.current_artist:
            success = self.add_artist_to_muspy(self.current_artist["mbid"], self.current_artist["name"])
            if success:
                # Si estamos usando el widget de tabla desde el archivo UI
                if hasattr(self, 'table_widget') and hasattr(self.table_widget, 'add_follow_button'):
                    self.table_widget.add_follow_button.setText(f"Following {self.current_artist['name']}")
                    self.table_widget.add_follow_button.setEnabled(False)
                # Si estamos usando el fallback
                elif hasattr(self, 'add_follow_button'):
                    self.add_follow_button.setText(f"Following {self.current_artist['name']}")
                    self.add_follow_button.setEnabled(False)
        else:
            QMessageBox.warning(self, "Error", "No artist currently selected")

    def get_new_releases(self, PROJECT_ROOT):
        """
        Retrieve new releases using the Muspy API endpoint
        Gets a list of album MBIDs from a local script and checks for new releases since each album
        Displays new releases in a QTableWidget
        """
        try:
            script_path = PROJECT_ROOT / "base_datos" / "tools" / "consultar_items_db.py"
            # Ejecutar el script que devuelve el JSON de álbumes
            result = subprocess.run(
                f"python {script_pat}",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                QMessageBox.warning(self, "Error", f"Error ejecutando el script: {result.stderr}")
                return
            
            # Cargar el JSON de álbumes
            try:
                albums = json.loads(result.stdout)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Error", "Error al parsear la respuesta del script")
                return
            
            # Lista para almacenar todos los nuevos lanzamientos
            all_new_releases = []
            
            # Consultar a muspy por cada MBID
            for album in albums:
                mbid = album.get('mbid')
                if not mbid:
                    continue
                    
                # Construir la URL con el parámetro 'since'
                url = f"{self.base_url}/releases"
                params = {'since': mbid}
                
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    releases = response.json()
                    # Filtrar lanzamientos futuros
                    today = datetime.date.today().strftime("%Y-%m-%d")
                    future_releases = [release for release in releases if release.get('date', '0000-00-00') >= today]
                    
                    # Agregar a la lista de todos los lanzamientos
                    all_new_releases.extend(future_releases)
                else:
                    log.error(f"Error consultando lanzamientos para MBID {mbid}: {response.text}")
            
            # Eliminar duplicados (si el mismo lanzamiento aparece para varios álbumes)
            unique_releases = []
            seen_ids = set()
            for release in all_new_releases:
                if release.get('mbid') not in seen_ids:
                    seen_ids.add(release.get('mbid'))
                    unique_releases.append(release)
            
            # Ordenar por fecha
            unique_releases.sort(key=lambda x: x.get('date', '0000-00-00'))
            
            if not unique_releases:
                QMessageBox.information(self, "No New Releases", "No new releases available")
                return
            
            # Mostrar en la tabla
            self.display_releases_table(unique_releases)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al obtener nuevos lanzamientos: {str(e)}")

    def sync_artists_with_muspy(self):
        """Synchronize artists from JSON file with Muspy"""
        # Ruta al archivo JSON
        json_path = PROJECT_ROOT / "artists_selected.json"
        
        # Verificar si el archivo existe
        if not json_path.exists():
            QMessageBox.warning(self, "Error", "El archivo artists_selected.json no existe.")
            return
        
        # Leer el archivo JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al leer el archivo JSON: {e}")
            return
        
        # Verificar si hay artistas en el JSON
        if not artists_data:
            QMessageBox.warning(self, "Error", "No hay artistas en el archivo JSON.")
            return
            
        # Limpiar solo una vez al principio
        self.results_text.clear()
        self.results_text.append("Comenzando sincronización de artistas desde JSON...\n")
        
        # Mostrar una barra de progreso simple
        total_artists = len(artists_data)
        self.results_text.append(f"Total artistas a sincronizar: {total_artists}\n")
        self.results_text.append("Progreso: [" + "-" * 50 + "]\n")
        
        # Variables para llevar el conteo
        successful_adds = 0
        failed_adds = 0
        duplicates = 0
        
        # Procesar por lotes para no sobrecargar la interfaz
        for i, artist_data in enumerate(artists_data):
            try:
                # Obtener el nombre y MBID directamente del JSON
                artist_name = artist_data["nombre"]
                mbid = artist_data["mbid"]
                
                # Intentar añadir el artista con el MBID proporcionado
                if mbid:
                    response = self.add_artist_to_muspy_silent(mbid, artist_name)
                    if response == 1:
                        successful_adds += 1
                    elif response == 0:
                        duplicates += 1
                    else:
                        failed_adds += 1
                else:
                    logger.error(f"MBID no válido para el artista {artist_name}")
                    failed_adds += 1
                
                # Actualizar la barra de progreso cada 5 artistas o al final
                if (i + 1) % 5 == 0 or i == total_artists - 1:
                    progress = int((i + 1) / total_artists * 50)
                    self.results_text.clear()
                    self.results_text.append(f"Sincronizando artistas... {i + 1}/{total_artists}\n")
                    self.results_text.append(f"Progreso: [" + "#" * progress + "-" * (50 - progress) + "]\n")
                    self.results_text.append(f"Añadidos: {successful_adds}, Duplicados: {duplicates}, Fallos: {failed_adds}\n")
                    QApplication.processEvents()  # Permite que la interfaz se actualice
            
            except Exception as e:
                logger.error(f"Error al sincronizar artista {artist_name if 'artist_name' in locals() else 'desconocido'}: {e}")
                failed_adds += 1
        
        # Mostrar el resumen final
        self.results_text.clear()
        self.results_text.append(f"Sincronización completada\n")
        self.results_text.append(f"Total artistas procesados: {total_artists}\n")
        self.results_text.append(f"Añadidos correctamente: {successful_adds}\n")
        self.results_text.append(f"Duplicados (ya existían): {duplicates}\n")
        self.results_text.append(f"Fallos: {failed_adds}\n")

    def add_artist_to_muspy_silent(self, mbid=None, artist_name=None):
        """
        Versión silenciosa de add_artist_to_muspy que no escribe en la interfaz
        
        Args:
            mbid (str, optional): MusicBrainz ID of the artist
            artist_name (str, optional): Name of the artist for logging
        
        Returns:
            int: 1 para éxito, 0 para duplicado, -1 para error
        """
        if not self.muspy_username or not self.muspy_api_key or not self.muspy_id:
            return -1

        if not mbid or not (len(mbid) == 36 and mbid.count('-') == 4):
            return -1

        try:
            # Follow artist by MBID
            url = f"{self.base_url}/artists/{self.muspy_id}/{mbid}"
            auth = (self.muspy_username, self.muspy_password)
            
            response = requests.put(url, auth=auth)
            
            if response.status_code in [200, 201]:
                # Verificar si ya existía el artista
                if "already exists" in response.text.lower():
                    return 0  # Duplicado
                return 1  # Éxito
            else:
                return -1  # Error
        except Exception:
            return -1  # Error

    def get_mbid_artist_searched(self, artist_name):
        """
        Retrieve the MusicBrainz ID for a given artist
        
        Args:
            artist_name (str): Name of the artist to search
        
        Returns:
            str or None: MusicBrainz ID of the artist
        """
        if artist_name is None:
            return None
        
        try:
            #First attempt: query existing database
            if self.query_db_script_path:
                # Add full absolute paths
                full_db_path = os.path.expanduser(self.db_path) if self.db_path else None
                full_script_path = os.path.expanduser(self.query_db_script_path)
                
                # Print out the actual paths being used
                self.results_text.append(f"Consultando base de datos para {artist_name}...")
                logger.debug(f"Script Path: {full_script_path}")
                logger.debug(f"DB Path: {full_db_path}")
                logger.debug(f"Artist: {artist_name}")

                mbid_result = subprocess.run(
                    ['python', full_script_path, "--db", full_db_path, "--artist", artist_name, "--mbid"], 
                    capture_output=True, 
                    text=True
                )
                
                # Check if the output contains an error message
                if "Error: no such table" in mbid_result.stderr:
                    self.results_text.append("Error: La tabla 'artists' no existe en la base de datos.")
                    logger.error(f"Database error: {mbid_result.stderr}")
                elif mbid_result.returncode != 0:
                    self.results_text.append(f"Error en la consulta: {mbid_result.stderr}")
                    logger.error(f"Query error: {mbid_result.stderr}")
                elif mbid_result.stdout.strip():
                    # Limpiar el resultado eliminando comillas y espacios en blanco
                    mbid = mbid_result.stdout.strip().strip('"\'')
                    # Verify that the MBID looks valid (should be a UUID)
                    if len(mbid) == 36 and mbid.count('-') == 4:
                        self.results_text.append(f"MBID encontrado en la base de datos: {mbid}")
                        return mbid
                    else:
                        self.results_text.append(f"MBID inválido encontrado: {mbid}")
                        logger.warning(f"Invalid MBID format: {mbid}")
                else:
                    self.results_text.append("No se encontró MBID en la base de datos.")
            
            # Second attempt: search for MBID if first method fails
            # if self.query_db_script_path:
            #     self.results_text.append(f"Buscando MBID para {artist_name} en MusicBrainz...")
            #     full_search_script_path = os.path.expanduser(self.query_db_script_path)
                
            #     mbid_search_result = subprocess.run(
            #         ['python', full_search_script_path, "--db", full_db_path if full_db_path else "", "--artist", artist_name, "--mbid"], 
            #         capture_output=True, 
            #         text=True
            #     )
                
            #     if mbid_search_result.returncode == 0 and mbid_search_result.stdout.strip():
            #         # Limpiar el resultado eliminando comillas y espacios en blanco
            #         mbid = mbid_search_result.stdout.strip().strip('"\'')
            #         if len(mbid) == 38 and mbid.count('-') == 4:
            #             self.results_text.append(f"MBID encontrado en MusicBrainz: {mbid}")
            #             return mbid
            #         else:
            #             self.results_text.append(f"MBID inválido recibido de MusicBrainz: {mbid}")
            #             logger.warning(f"Invalid MBID format from search: {mbid}")
            #     else:
            #         self.results_text.append(f"No se pudo encontrar MBID: {mbid_search_result.stderr}")
            #         logger.error(f"MBID search error: {mbid_search_result.stderr}")
            
            # self.results_text.append(f"No se pudo encontrar MBID para {artist_name}")
            # return None
        
        except subprocess.TimeoutExpired:
            self.results_text.append("La ejecución del script expiró")
            logger.error("Script execution timed out")
        except PermissionError:
            self.results_text.append(f"Permiso denegado al ejecutar el script")
            logger.error(f"Permission denied running script: {self.query_db_script_path}")
        except FileNotFoundError as e:
            self.results_text.append(f"Script o base de datos no encontrados: {e}")
            logger.error(f"File not found: {e}")
        except Exception as e:
            self.results_text.append(f"Error inesperado: {e}")
            logger.error(f"Unexpected error getting MBID for {artist_name}: {e}")
        
        return None
 
    def add_artist_to_muspy(self, mbid=None, artist_name=None):
        """
        Add/Follow an artist to Muspy using their MBID or name
        
        Args:
            mbid (str, optional): MusicBrainz ID of the artist
            artist_name (str, optional): Name of the artist for logging
        
        Returns:
            bool: True if artist was successfully added, False otherwise
        """
        if not self.muspy_username or not self.muspy_api_key:
            QMessageBox.warning(self, "Error", "Configuración de Muspy no disponible")
            return False

        if not mbid:
            message = f"No se pudo agregar {artist_name or 'Desconocido'} a Muspy: MBID no disponible"
            self.results_text.append(message)
            logger.error(message)
            return False

        # Validate MBID format (should be a UUID)
        if not (len(mbid) == 36 and mbid.count('-') == 4):
            message = f"MBID inválido para {artist_name or 'Desconocido'}: {mbid}"
            self.results_text.append(message)
            logger.error(message)
            return False

        try:
            # Ensure results_text is visible
            self.results_text.show()

            # Follow artist by MBID
            url = f"{self.base_url}/artists/{self.muspy_id}/{mbid}"
            
            # Usar autenticación básica en lugar de token
            auth = (self.muspy_username, self.muspy_api_key)
            
            logger.info(f"Agregando artista a Muspy: {artist_name} (MBID: {mbid})")
            response = requests.put(url, auth=auth)
            
            if response.status_code in [200, 201]:
                message = f"Artista {artist_name or 'Desconocido'} agregado a Muspy"
                self.results_text.append(message)
                logger.info(message)
                return True
            else:
                message = f"No se pudo agregar {artist_name or 'Desconocido'} a Muspy: {response.status_code} - {response.text}"
                self.results_text.append(message)
                logger.error(message)
                return False
        except Exception as e:
            message = f"Error al agregar a Muspy: {e}"
            self.results_text.append(message)
            logger.error(message)
            return False

    def sync_lastfm_muspy(self):
        """Synchronize Last.fm artists with Muspy"""
        if not self.lastfm_username:
            QMessageBox.warning(self, "Error", "Last.fm username not configured")
            return

        try:
            # Import artists via last.fm
            url = f"{self.base_url}/{self.muspy_username}"
            method = 'PUT'
            data = {
                'import': 'last.fm',
                'username': self.lastfm_username,
                'count': 10,
                'period': 'overall'
            }

            # Usar autenticación básica en lugar de token
            auth = (self.muspy_username, self.muspy_api_key)
            
            # Use the appropriate request method
            if method == 'PUT':
                response = requests.put(url, auth=auth, json=data)
            else:
                response = requests.post(url, auth=auth, json=data)
            
            if response.status_code in [200, 201]:
                self.results_text.append(f"Synchronized artists from Last.fm account {self.lastfm_username}\n")
                return True
            else:
                self.results_text.append(f"Could not sync Last.fm artists: {response.text}\n")
                return False
        except Exception as e:
            self.results_text.append(f"Error syncing with Muspy: {e}\n")
            return False

    def get_muspy_releases(self):
        """
        Retrieve future releases from Muspy for the current user
        
        Displays future releases in a QTableWidget
        """
        if not self.muspy_username or not self.muspy_api_key:
            QMessageBox.warning(self, "Error", "Muspy configuration not available")
            return

        try:
            url = f"{self.base_url}/releases/{self.muspy_api_key}"
            # Usar autenticación básica en lugar de token
            auth = (self.muspy_username, self.muspy_api_key)
            
            response = requests.get(url, auth=auth)
            
            if response.status_code == 200:
                all_releases = response.json()
                
                # Filter for future releases
                today = datetime.date.today().strftime("%Y-%m-%d")
                future_releases = [release for release in all_releases if release.get('date', '0000-00-00') >= today]
                
                if not future_releases:
                    QMessageBox.information(self, "No Future Releases", "No upcoming releases in Muspy")
                    return
                
                # Display releases in table
                self.display_releases_table(future_releases)
            else:
                QMessageBox.warning(self, "Error", f"Error retrieving releases: {response.text}")
        
        except Exception as e:
            QMessageBox.warning(self, "Connection Error", f"Connection error with Muspy: {e}")
   
   
   
    def get_all_my_releases(self):
        """
        Retrieve all releases for the user's artists using the user ID
        
        Handles pagination to get all releases even when there are many artists
        """
        if not self.muspy_api_key:
            QMessageBox.warning(self, "Error", "Muspy ID not available. Please check your configuration.")
            return

        try:
            # Show progress in the text area
            self.results_text.clear()
            self.results_text.show()
            self.results_text.append("Fetching your releases... This might take a while.")
            QApplication.processEvents()  # Update UI
            
            all_releases = []
            offset = 0
            limit = 100  # Maximum allowed by API
            more_releases = True
            
            while more_releases:
                # Create URL with user ID, offset, and limit
                url = f"{self.base_url}/releases/{self.muspy_id}"
                params = {
                    "offset": offset,
                    "limit": limit
                }
                
                self.results_text.append(f"Fetching releases {offset+1}-{offset+limit}...")
                QApplication.processEvents()  # Update UI
                
                # Make the request
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    batch_releases = response.json()
                    
                    if not batch_releases:
                        # No more releases to fetch
                        more_releases = False
                    else:
                        # Add to our collection and update offset
                        all_releases.extend(batch_releases)
                        offset += limit
                        
                        # Progress update
                        self.results_text.append(f"Found {len(all_releases)} releases so far.")
                        QApplication.processEvents()  # Update UI
                        
                        # If we got fewer than the limit, we've reached the end
                        if len(batch_releases) < limit:
                            more_releases = False
                else:
                    self.results_text.append(f"Error retrieving releases: {response.status_code} - {response.text}")
                    more_releases = False
            
            # Filter for future releases
            today = datetime.date.today().strftime("%Y-%m-%d")
            future_releases = [release for release in all_releases if release.get('date', '0000-00-00') >= today]
            
            self.results_text.append(f"Processing complete! Found {len(future_releases)} upcoming releases out of {len(all_releases)} total releases.")
            
            if not future_releases:
                self.results_text.append("No upcoming releases found for your artists.")
                return
            
            # Sort releases by date
            future_releases.sort(key=lambda x: x.get('date', '9999-99-99'))
            
            # Display releases in table
            self.display_releases_table(future_releases)
        
        except Exception as e:
            self.results_text.append(f"Connection error with Muspy: {str(e)}")
            logger.error(f"Error getting all releases: {e}")



 
    def display_releases_table(self, releases):
        """
        Display releases in a QTableWidget for better rendering
        
        Args:
            releases (list): List of release dictionaries to display
        """
        # First, clear any existing table and follow button
        for i in reversed(range(self.layout().count())): 
            item = self.layout().itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None and (isinstance(widget, QTableWidget) or (hasattr(self, 'add_follow_button') and widget == self.add_follow_button)):
                    self.layout().removeItem(item)
                    widget.deleteLater()

        # Create the table widget using the UI file
        table_widget = QWidget()
        ui_file_path = os.path.join(PROJECT_ROOT, "ui", "muspy_releases_table.ui")
        
        if os.path.exists(ui_file_path):
            try:
                # Cargar el archivo UI
                uic.loadUi(ui_file_path, table_widget)
                
                # Configuraciones iniciales
                table_widget.count_label.setText(f"Showing {len(releases)} upcoming releases")
                table = table_widget.table
                table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

                # Limpiar filas de ejemplo que vienen en el UI
                table.setRowCount(0)
                
                # Configurar número de filas para datos reales
                table.setRowCount(len(releases))
                
                # Fill the table
                self._fill_releases_table(table, releases)
                
                # Configurar el botón de seguir artista si estamos viendo un artista específico
                if hasattr(self, 'current_artist') and self.current_artist:
                    table_widget.add_follow_button.setText(f"Follow {self.current_artist['name']}")
                    table_widget.add_follow_button.clicked.connect(self.follow_current_artist)
                else:
                    table_widget.add_follow_button.setVisible(False)
                
                # Resize rows to content
                table.resizeRowsToContents()
                
                # Make the table sortable
                table.setSortingEnabled(True)
                
                # Hide the text edit and add the table to the layout
                self.results_text.hide()
                # Insert the table widget
                self.layout().insertWidget(self.layout().count() - 1, table_widget)
                
                # Store reference to table widget
                self.table_widget = table_widget
                return table
            except Exception as e:
                self.results_text.append(f"Error cargando UI de la tabla: {e}")
                logger.error(f"Error cargando UI de la tabla: {e}")
                # Fall back to the old method
                return self._fallback_display_releases_table(releases)
        else:
            self.results_text.append(f"Archivo UI no encontrado: {ui_file_path}, usando creación manual")
            return self._fallback_display_releases_table(releases)



    def _fallback_display_releases_table(self, releases):
        """
        Método de respaldo para mostrar la tabla de lanzamientos si no se encuentra el archivo UI
        
        Args:
            releases (list): Lista de lanzamientos
        """
        # Create the table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(['Artist', 'Release Title', 'Type', 'Date', 'Disambiguation'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Add a label showing how many releases we're displaying
        count_label = QLabel(f"Showing {len(releases)} upcoming releases")
        self.layout().insertWidget(self.layout().count() - 1, count_label)
        
        # Configure number of rows
        table.setRowCount(len(releases))
        
        # Fill the table
        self._fill_releases_table(table, releases)
        
        # If we have a current artist, add a follow button
        if hasattr(self, 'current_artist') and self.current_artist:
            self.add_follow_button = QPushButton(f"Follow {self.current_artist['name']}")
            self.add_follow_button.clicked.connect(self.follow_current_artist)
            self.layout().insertWidget(self.layout().count() - 1, self.add_follow_button)
        
        # Resize rows to content
        table.resizeRowsToContents()
        
        # Make the table sortable
        table.setSortingEnabled(True)
        
        # Hide the text edit and add the table to the layout
        self.results_text.hide()
        # Insert the table just above the bottom buttons
        self.layout().insertWidget(self.layout().count() - 1, table)
        return table


    def _fill_releases_table(self, table, releases):
        """
        Rellena una tabla existente con los datos de lanzamientos
        
        Args:
            table (QTableWidget): Tabla a rellenar
            releases (list): Lista de lanzamientos
        """
        # Fill the table
        for row, release in enumerate(releases):
            artist = release.get('artist', {})
            
            # Create items for each column
            artist_name_item = QTableWidgetItem(artist.get('name', 'Unknown'))
            if artist.get('disambiguation'):
                artist_name_item.setToolTip(artist.get('disambiguation'))
            table.setItem(row, 0, artist_name_item)
            
            # Title with proper casing and full information
            title_item = QTableWidgetItem(release.get('title', 'Untitled'))
            if release.get('comments'):
                title_item.setToolTip(release.get('comments'))
            table.setItem(row, 1, title_item)
            
            # Release type (Album, EP, etc.)
            type_item = QTableWidgetItem(release.get('type', 'Unknown').title())
            table.setItem(row, 2, type_item)
            
            # Date with color highlighting for upcoming releases
            date_str = release.get('date', 'No date')
            date_item = QTableWidgetItem(date_str)
            
            # Highlight dates that are within the next month  
            try:
                release_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                today = datetime.date.today()
                one_month = today + datetime.timedelta(days=30)
                
                if release_date <= today + datetime.timedelta(days=7):
                    # Coming very soon - red
                    date_item.setBackground(QColor(31, 60, 28))
                elif release_date <= one_month:
                    # Coming in a month - yellow
                    date_item.setBackground(QColor(60, 28, 31))
            except ValueError:
                # If date parsing fails, don't color
                pass
                
            table.setItem(row, 3, date_item)
            
            # Additional details
            details = []
            if release.get('format'):
                details.append(f"Format: {release.get('format')}")
            if release.get('tracks'):
                details.append(f"Tracks: {release.get('tracks')}")
            if release.get('country'):
                details.append(f"Country: {release.get('country')}")
            if artist.get('disambiguation'):
                details.append(artist.get('disambiguation'))

            details_item = QTableWidgetItem("; ".join(details) if details else "")
            table.setItem(row, 4, details_item)


def main():
    """Main function to run the Muspy Artist Management Module"""
    app = QApplication(sys.argv)
    
    # Parse command-line arguments
    muspy_username = None
    muspy_api_key = None
    artists_file = None
    query_db_script_path = None
    #search_mbid_script_path = None
    db_path = None
    for arg in sys.argv[1:]:
        if arg.startswith('--muspy-username='):
            muspy_username = arg.split('=')[1]
        elif arg.startswith('--muspy-api-key='):
            muspy_api_key = arg.split('=')[1]
        elif arg.startswith('--artists-file='):
            artists_file = arg.split('=')[1]
        elif arg.startswith('--query-db-script-path='):
            query_db_script_path = arg.split('=')[1]
        # elif arg.startswith('--search-mbid-script-path='):
        #     search_mbid_script_path = arg.split('=')[1]
        elif arg.startswith('--lastfm-username='):
            lastfm_username = arg.split('=')[1]
        elif arg.startswith('--db-path='):
            db_path = arg.split('=')[1]

    # Create module instance
    module = MuspyArtistModule(
        muspy_username=muspy_username, 
        muspy_api_key=muspy_api_key,
        artists_file=artists_file,
        query_db_script_path=query_db_script_path,
        #search_mbid_script_path=search_mbid_script_path,
        lastfm_username=lastfm_username,
        db_path=db_path
    )
    module.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
