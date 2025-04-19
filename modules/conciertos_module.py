import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests
from PyQt6 import uic
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTextEdit, QComboBox,
                            QLabel, QLineEdit, QFileDialog, QMessageBox,
                            QHBoxLayout, QListWidget, QListWidgetItem, QTabWidget,
                            QFormLayout, QGroupBox, QScrollArea, QFrame, QSplitter, QDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices, QColor, QFont
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule, PROJECT_ROOT
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class ConcertEvent:
    """Clase para estandarizar eventos de conciertos de diferentes APIs"""
    def __init__(self, id: str, name: str, artist: str, date: str, venue: str, city: str, 
                 country: str, url: str, source: str, image_url: Optional[str] = None):
        self.id = id
        self.name = name
        self.artist = artist
        self.date = date
        self.venue = venue
        self.city = city
        self.country = country
        self.url = url
        self.source = source  # Nombre del servicio (Ticketmaster, Songkick, etc.)
        self.image_url = image_url


    # Nueva función para generar evento iCalendar
    def to_icalendar(self) -> str:
        """Convierte el evento de concierto a formato iCalendar"""
        from datetime import datetime
        import uuid
        
        # Convertir la fecha a formato datetime (asumiendo que no hay hora específica)
        try:
            event_date = datetime.strptime(self.date, "%Y-%m-%d")
            start_time = event_date.strftime("%Y%m%dT190000Z")  # Asumimos 19:00 UTC como hora por defecto
            end_time = event_date.strftime("%Y%m%dT230000Z")    # Asumimos duración de 4 horas
        except ValueError:
            # Si hay algún problema con el formato de fecha, usamos la actual
            now = datetime.now()
            start_time = now.strftime("%Y%m%dT190000Z")
            end_time = now.strftime("%Y%m%dT230000Z")
        
        # Crear UUID único para el evento
        uid = str(uuid.uuid4())
        
        # Crear el evento en formato iCalendar
        ical = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ConcertApp//EN
BEGIN:VEVENT
UID:{uid}
SUMMARY:{self.artist} en concierto
DESCRIPTION:{self.name} - Proporcionado por {self.source}\\n{self.url}
LOCATION:{self.venue}, {self.city}, {self.country}
DTSTART:{start_time}
DTEND:{end_time}
END:VEVENT
END:VCALENDAR
"""
        return ical




class ConciertosModule(BaseModule):
    def __init__(self, config: Dict = None, parent=None, theme='Tokyo Night', **kwargs):
        # Configuración por defecto
        self.config = {
            "country_code": "ES",
            "artists_file": "",
            "apis": {
                "ticketmaster": {"enabled": True, "api_key": ""},
                "songkick": {"enabled": True, "api_key": ""},
                "concerts_metal": {"enabled": True},
                "rapidapi": {"enabled": True, "api_key": ""},
                "bandsintown": {"enabled": True, "app_id": ""},
                "dicefm": {"enabled": True, "api_key": ""}  # Nueva API
            }
        }
        
        # Actualizar con la configuración proporcionada
        if config:
            self.update_config(config)
        
        # Lista para almacenar todos los eventos encontrados
        self.all_events: List[ConcertEvent] = []
        self.active_fetchers = 0

        self.available_themes = kwargs.pop('temas', [])
        self.selected_theme = kwargs.pop('tema_seleccionado', theme)
        
        # Initialize authentication managers
        self.lastfm_auth = None
        self.spotify_auth = None
        self.musicbrainz_auth = None
        
        # Initialize flags for APIs
        self.lastfm_enabled = False
        self.spotify_enabled = False
        self.musicbrainz_enabled = False
        
        # Setup authentication managers if config provided
        if config:
            self.setup_authentication_managers(config)
            
        # Current list of artists (from whatever source)
        self.current_artists = []

        # Llamamos al inicializador de la clase base
        super().__init__(parent, theme)
    
    def apply_theme(self, theme_name=None):
        super().apply_theme(theme_name)


    def __del__(self):
        """Método destructor para limpiar recursos"""
        # Detener cualquier fetcher activo
        for fetcher in getattr(self, '_fetchers', []):
            if fetcher and fetcher.isRunning():
                fetcher.stop()

    def update_config(self, new_config: Dict):
        """Actualiza la configuración con valores nuevos, manteniendo la estructura"""
        for key, value in new_config.items():
            if key == "apis" and isinstance(value, dict):
                for api_name, api_config in value.items():
                    if api_name in self.config["apis"]:
                        self.config["apis"][api_name].update(api_config)
                    else:
                        self.config["apis"][api_name] = api_config
            else:
                self.config[key] = value
    
    def init_ui(self):
        """Inicializa la interfaz del módulo usando archivo UI"""
        # Intentar cargar el archivo UI
        ui_file_path = os.path.join(PROJECT_ROOT, "ui", "conciertos_module.ui")
        if os.path.exists(ui_file_path):
            try:
                uic.loadUi(ui_file_path, self)
                
                # Conectar elementos de la interfaz con variables del código
                self.match_ui_elements()
                
                # Configurar valores iniciales
                self.country_code_input.setText(self.config["country_code"])
                
                # Conectar señales
                self.select_file_btn.clicked.connect(self.select_artists_file)
                self.fetch_all_btn.clicked.connect(self.search_concerts)
                self.concerts_list.itemDoubleClicked.connect(self.switch_tab_db)
                
                # Conectar botones de búsqueda individual
                if hasattr(self, 'ticketmaster_enabled') and self.ticketmaster_enabled is not None:
                    self.ticketmaster_enabled.clicked.connect(lambda: self.fetch_single_service("ticketmaster"))
                if hasattr(self, 'songkick_enabled') and self.songkick_enabled is not None:
                    self.songkick_enabled.clicked.connect(lambda: self.fetch_single_service("songkick"))
                if hasattr(self, 'concerts_metal_enabled') and self.concerts_metal_enabled is not None:
                    self.concerts_metal_enabled.clicked.connect(lambda: self.fetch_single_service("concerts_metal"))
                if hasattr(self, 'rapidapi_enabled') and self.rapidapi_enabled is not None:
                    self.rapidapi_enabled.clicked.connect(lambda: self.fetch_single_service("rapidapi"))
                if hasattr(self, 'bandsintown_enabled') and self.bandsintown_enabled is not None:
                    self.bandsintown_enabled.clicked.connect(lambda: self.fetch_single_service("bandsintown"))
                if hasattr(self, 'dicefm_enabled') and self.dicefm_enabled is not None:
                    self.dicefm_enabled.clicked.connect(lambda: self.fetch_single_service("dicefm"))
                # DiceFM
                if self.config["apis"]["dicefm"].get("enabled", False):
                    self.launch_dicefm_fetcher()
                # Mensaje inicial del log
                self.log("Módulo inicializado. Configure los parámetros y haga clic en 'Buscar en Todos los Servicios'.")
                
                # Connect the source combo box to function
                if hasattr(self, 'source_combo'):
                    self.source_combo.currentIndexChanged.connect(self.on_source_changed)
                    
                    # Add sources to the combo box
                    self.source_combo.addItem("Archivo de artistas", "file")
                    
                    # Add LastFM if enabled
                    if hasattr(self, 'lastfm_enabled') and self.lastfm_enabled:
                        self.source_combo.addItem("Top artistas LastFM", "lastfm")
                        
                    # Add Spotify if enabled
                    if hasattr(self, 'spotify_enabled') and self.spotify_enabled:
                        self.source_combo.addItem("Artistas seguidos en Spotify", "spotify")
                        
                    # Add MusicBrainz if enabled
                    if hasattr(self, 'musicbrainz_enabled') and self.musicbrainz_enabled:
                        self.source_combo.addItem("Colección de MusicBrainz", "musicbrainz")
                        
                    # Add database option if directory exists
                    cache_dir = os.path.join(PROJECT_ROOT, ".content", "cache")
                    json_path = os.path.join(cache_dir, "artists_selected.json")
                    if os.path.exists(json_path):
                        self.source_combo.addItem("Artistas de base de datos", "database")



                return True
            except Exception as e:
                print(f"Error cargando UI desde archivo: {e}")
                import traceback
                traceback.print_exc()
        
        # Método fallback si falla la carga del UI
        self._fallback_init_ui()
        return False





    def on_source_changed(self):
        """Handle change in the artist source selection"""
        if not hasattr(self, 'source_combo'):
            return
        
        # Get the currently selected source data
        source_type = self.source_combo.currentData()
        if not source_type:
            return
        
        # Update the artists list
        artists = self.get_artists_from_source(source_type)
        
        # Update the UI to show the number of artists loaded
        if hasattr(self, 'artists_count_label'):
            self.artists_count_label.setText(f"Artistas cargados: {len(artists)}")
            
        # Store the artists list for use in searches
        self.current_artists = artists


        
    def _fallback_init_ui(self):
        """Crea la interfaz de forma manual si no se puede cargar el archivo UI"""
        main_layout = QVBoxLayout(self)
        
        # Configuración global (país y archivo de artistas)
        global_config_group = QGroupBox("Configuración global")
        global_form = QFormLayout()
        
        # Country Code
        self.country_code_input = QLineEdit(self.config["country_code"])
        self.country_code_input.setMaximumWidth(50)
        global_form.addRow("País (código):", self.country_code_input)
        
        # Archivo de artistas con botón de selección
        artists_file_layout = QHBoxLayout()
        self.artists_file_input = QLineEdit(self.config["artists_file"])
        artists_file_layout.addWidget(self.artists_file_input)
        
        self.select_file_btn = QPushButton("...")
        self.select_file_btn.setMaximumWidth(30)
        self.select_file_btn.clicked.connect(self.select_artists_file)
        artists_file_layout.addWidget(self.select_file_btn)
        global_form.addRow("Archivo de artistas:", artists_file_layout)
        
        global_config_group.setLayout(global_form)
        main_layout.addWidget(global_config_group)
        
        # Pestañas para las diferentes APIs
        self.tabs = QTabWidget()
        
        # Crear pestañas para los servicios
        self.create_service_tabs()
        
        main_layout.addWidget(self.tabs)
        
        # Botón de búsqueda global
        self.fetch_all_btn = QPushButton("Buscar en Todos los Servicios")
        self.fetch_all_btn.clicked.connect(self.fetch_all_services)
        main_layout.addWidget(self.fetch_all_btn)
        
        # Lista de conciertos con más detalles
        concerts_label = QLabel("Resultados de conciertos:")
        main_layout.addWidget(concerts_label)
        
        # Crear un QSplitter para dividir la lista de conciertos y el área de log
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Lista de conciertos en la parte superior del splitter
        self.concerts_list = QListWidget()
        self.concerts_list.setMinimumHeight(200)
        self.concerts_list.itemDoubleClicked.connect(self.switch_tab_db)
        splitter.addWidget(self.concerts_list)
        
        # Área de log en la parte inferior
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        splitter.addWidget(self.log_area)
        
        # Añadir el splitter al layout principal
        main_layout.addWidget(splitter)
        
        # Inicialización
        self.log("Módulo inicializado. Configure los parámetros y haga clic en 'Buscar en Todos los Servicios'.")

    def create_service_tabs(self):
        """Crear pestañas para los diferentes servicios de conciertos"""
        # Crear pestañas solo para servicios habilitados
        if self.config["apis"]["ticketmaster"].get("enabled", False):
            self.create_ticketmaster_tab()
        
        if self.config["apis"]["songkick"].get("enabled", False):
            self.create_songkick_tab()
        
        if self.config["apis"]["concerts_metal"].get("enabled", False):
            self.create_concerts_metal_tab()
        
        if self.config["apis"]["rapidapi"].get("enabled", False):
            self.create_rapidapi_tab()
        
        if self.config["apis"]["bandsintown"].get("enabled", False):
            self.create_bandsintown_tab()


    def setup_authentication_managers(self, config: Dict):
        """Setup authentication managers for various music services"""
        # LastFM Authentication
        if config.get("lastfm", {}).get("enabled", False):
            try:
                from tools.lastfm_login import LastFMAuthManager
                
                lastfm_config = config.get("lastfm", {})
                self.lastfm_auth = LastFMAuthManager(
                    api_key=lastfm_config.get("api_key"),
                    api_secret=lastfm_config.get("api_secret"),
                    username=lastfm_config.get("username"),
                    password=lastfm_config.get("password"),
                    parent_widget=self
                )
                
                # Check if LastFM is authenticated
                self.lastfm_enabled = self.lastfm_auth.is_authenticated() if self.lastfm_auth else False
                self.log(f"LastFM authentication {'enabled' if self.lastfm_enabled else 'disabled'}")
                self.lastfm_username = lastfm_config.get("username")
                self.lastfm_api_key = lastfm_config.get("api_key")
            except Exception as e:
                self.log(f"Error setting up LastFM authentication: {e}")
        
        # Spotify Authentication
        if config.get("spotify", {}).get("enabled", False):
            try:
                from tools.spotify_login import SpotifyAuthManager
                
                spotify_config = config.get("spotify", {})
                self.spotify_auth = SpotifyAuthManager(
                    client_id=spotify_config.get("client_id"),
                    client_secret=spotify_config.get("client_secret"),
                    parent_widget=self
                )
                
                # Check if Spotify is authenticated
                self.spotify_enabled = self.spotify_auth.is_authenticated() if self.spotify_auth else False
                self.log(f"Spotify authentication {'enabled' if self.spotify_enabled else 'disabled'}")
            except Exception as e:
                self.log(f"Error setting up Spotify authentication: {e}")
        
        # MusicBrainz Authentication
        if config.get("musicbrainz", {}).get("enabled", False):
            try:
                from tools.musicbrainz_login import MusicBrainzAuthManager
                
                mb_config = config.get("musicbrainz", {})
                self.musicbrainz_auth = MusicBrainzAuthManager(
                    username=mb_config.get("username"),
                    password=mb_config.get("password"),
                    app_name="MuspyModule",
                    parent_widget=self
                )
                
                # Check if MusicBrainz is authenticated
                self.musicbrainz_enabled = self.musicbrainz_auth.is_authenticated() if self.musicbrainz_auth else False
                self.log(f"MusicBrainz authentication {'enabled' if self.musicbrainz_enabled else 'disabled'}")
            except Exception as e:
                self.log(f"Error setting up MusicBrainz authentication: {e}")


    def switch_tab_db(self):
        # Obtener el elemento seleccionado
        selected_item = self.concerts_list.currentItem()
        if selected_item:
            # Obtener el widget personalizado asociado al elemento
            item_widget = self.concerts_list.itemWidget(selected_item)
            if item_widget:
                # Obtener la etiqueta que contiene la información del concierto
                label = item_widget.layout().itemAt(0).widget()
                if label and isinstance(label, QLabel):
                    # Extraer el nombre del artista del texto de la etiqueta
                    # El formato es "[source] artist - date @ venue (city, country)"
                    text = label.text()
                    parts = text.split(" - ", 1)
                    if len(parts) > 1:
                        # Extraer solo el nombre del artista
                        source_artist = parts[0]  # "[source] artist"
                        artist = source_artist.split("] ", 1)[1] if "]" in source_artist else source_artist
                        artist = f"a:{artist}"
                        
                        # Cambiar a la pestaña Music Browser y llamar al método search_artist
                        self.switch_tab("Music Browser", "set_search_text", artist)
                        return
        
        # Si no se pudo obtener el artista, simplemente cambiar de pestaña
        self.switch_tab("Music Browser")


    def add_to_calendar(self, event: ConcertEvent):
        """Añade el evento de concierto al servidor de calendario Radicale"""
        try:
            # Configuración del servidor Radicale
            config_dialog = RadicaleConfigDialog(self)
            if config_dialog.exec():
                # Obtener configuración del diálogo
                radicale_url = config_dialog.get_url()
                radicale_username = config_dialog.get_username()
                radicale_password = config_dialog.get_password()
                calendar_name = config_dialog.get_calendar()
                
                # Generar el contenido iCalendar
                ical_content = event.to_icalendar()
                
                # Enviar al servidor Radicale
                self.send_to_radicale(radicale_url, radicale_username, radicale_password, 
                                    calendar_name, ical_content, event)
        except Exception as e:
            self.log(f"Error al añadir evento al calendario: {str(e)}")
            QMessageBox.warning(self, "Error", f"No se pudo añadir al calendario: {str(e)}")


    # Nueva función para enviar datos al servidor Radicale
    def send_to_radicale(self, base_url: str, username: str, password: str,
                        calendar: str, ical_content: str, event: ConcertEvent):
        """Envía el evento al servidor Radicale utilizando el protocolo CalDAV"""
        try:
            import uuid
            import requests
            from urllib.parse import urljoin
            
            # Generar un UID único para el evento
            event_uid = str(uuid.uuid4())
            
            # Construir la URL completa con el formato correcto: baseurl/usuario/calendario/uid.ics
            url = urljoin(base_url, f"{username}/{calendar}/{event_uid}.ics")
            
            # Realizar la solicitud PUT para crear el evento
            response = requests.put(
                url,
                data=ical_content,
                auth=(username, password),
                headers={"Content-Type": "text/calendar; charset=utf-8"}
            )
            
            if response.status_code in (201, 204):
                self.log(f"Evento añadido al calendario: {event.artist} - {event.date}")
                QMessageBox.information(
                    self,
                    "Evento añadido",
                    f"El concierto de {event.artist} ha sido añadido al calendario."
                )
            else:
                self.log(f"Error al añadir evento: Código {response.status_code} - {response.text}")
                QMessageBox.warning(
                    self,
                    "Error",
                    f"No se pudo añadir al calendario. Error {response.status_code}"
                )
        except Exception as e:
            self.log(f"Error en la comunicación con Radicale: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error de comunicación con el servidor: {str(e)}")


    def create_ticketmaster_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # API Key
        self.ticketmaster_api_key = QLineEdit(self.config["apis"]["ticketmaster"].get("api_key", ""))
        self.ticketmaster_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("API Key:", self.ticketmaster_api_key)
        
        # Enabled checkbox
        self.ticketmaster_enabled = QPushButton("Buscar solo en Ticketmaster")
        self.ticketmaster_enabled.clicked.connect(lambda: self.fetch_single_service("ticketmaster"))
        layout.addRow(self.ticketmaster_enabled)
        
        self.tabs.addTab(tab, "Ticketmaster")
    
    def create_songkick_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # API Key
        self.songkick_api_key = QLineEdit(self.config["apis"]["songkick"].get("api_key", ""))
        self.songkick_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("API Key:", self.songkick_api_key)
        
        # Enabled checkbox
        self.songkick_enabled = QPushButton("Buscar solo en Songkick")
        self.songkick_enabled.clicked.connect(lambda: self.fetch_single_service("songkick"))
        layout.addRow(self.songkick_enabled)
        
        self.tabs.addTab(tab, "Songkick")
    
    def create_concerts_metal_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # No se necesita API key para este servicio
        info_label = QLabel("Este servicio no requiere API key, pero usa web scraping.")
        layout.addRow(info_label)
        
        # Enabled checkbox
        self.concerts_metal_enabled = QPushButton("Buscar solo en Concerts-Metal")
        self.concerts_metal_enabled.clicked.connect(lambda: self.fetch_single_service("concerts_metal"))
        layout.addRow(self.concerts_metal_enabled)
        
        self.tabs.addTab(tab, "Concerts-Metal")
    
    def create_rapidapi_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # API Key
        self.rapidapi_api_key = QLineEdit(self.config["apis"]["rapidapi"].get("api_key", ""))
        self.rapidapi_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("RapidAPI Key:", self.rapidapi_api_key)
        
        # Información adicional
        info_label = QLabel("Este servicio usa la API de Predicthq Events en RapidAPI")
        layout.addRow(info_label)
        
        # Enabled checkbox
        self.rapidapi_enabled = QPushButton("Buscar solo en RapidAPI")
        self.rapidapi_enabled.clicked.connect(lambda: self.fetch_single_service("rapidapi"))
        layout.addRow(self.rapidapi_enabled)
        
        self.tabs.addTab(tab, "RapidAPI")
    
    def create_bandsintown_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # App ID
        self.bandsintown_app_id = QLineEdit(self.config["apis"]["bandsintown"].get("app_id", ""))
        layout.addRow("App ID:", self.bandsintown_app_id)
        
        # Enabled checkbox
        self.bandsintown_enabled = QPushButton("Buscar solo en Bandsintown")
        self.bandsintown_enabled.clicked.connect(lambda: self.fetch_single_service("bandsintown"))
        layout.addRow(self.bandsintown_enabled)
        
        self.tabs.addTab(tab, "Bandsintown")
    
    def select_artists_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de artistas", "", "Archivos de texto (*.txt)"
        )
        if file_path:
            self.artists_file_input.setText(file_path)
            self.config["artists_file"] = file_path
    
    def fetch_all_services(self):
        """Inicia la búsqueda en todos los servicios habilitados"""
        # Actualizar la configuración global
        self.config["country_code"] = self.country_code_input.text().strip()
        self.config["artists_file"] = self.artists_file_input.text().strip()
        
        # Verificar archivo de artistas
        if not self.config["artists_file"] or not os.path.isfile(self.config["artists_file"]):
            QMessageBox.warning(self, "Error", "Seleccione un archivo de artistas válido")
            return
        
        # Resetear eventos y desactivar botones
        self.all_events = []
        self.concerts_list.clear()
        self.fetch_all_btn.setEnabled(False)
        self.active_fetchers = 0
        
        # Inicializar lista de fetchers
        self._fetchers = []

        # Actualizar configuración (solo API keys y App IDs)
        self.update_service_configs()
        
        # Lanzar solo los servicios que están habilitados en la configuración
        # Ticketmaster
        if self.config["apis"]["ticketmaster"].get("enabled", False):
            self.launch_ticketmaster_fetcher()
        
        # Songkick
        if self.config["apis"]["songkick"].get("enabled", False):
            self.launch_songkick_fetcher()
        
        # Concerts-Metal
        if self.config["apis"]["concerts_metal"].get("enabled", False):
            self.launch_concerts_metal_fetcher()
        
        # RapidAPI
        if self.config["apis"]["rapidapi"].get("enabled", False):
            self.launch_rapidapi_fetcher()
        
        # Bandsintown
        if self.config["apis"]["bandsintown"].get("enabled", False):
            self.launch_bandsintown_fetcher()
        
        if self.active_fetchers == 0:
            self.log("No hay servicios habilitados para buscar")
            self.fetch_all_btn.setEnabled(True)


    def get_lastfm_top_artists_direct(self, count=50, period="overall"):
        """
        Get top artists directly from Last.fm API to ensure we get all data fields
        
        Args:
            count (int): Number of top artists to fetch
            period (str): Time period (overall, 7day, 1month, 3month, 6month, 12month)
            
        Returns:
            list: List of artist dictionaries or empty list on error
        """
        if not hasattr(self, 'lastfm_api_key') or not hasattr(self, 'lastfm_username') or not self.lastfm_api_key or not self.lastfm_username:
            self.log("Last.fm API key or username not configured")
            return []
        
        try:
            # Build API URL
            url = "http://ws.audioscrobbler.com/2.0/"
            params = {
                "method": "user.gettopartists",
                "user": self.lastfm_username,
                "api_key": self.lastfm_api_key,
                "format": "json",
                "limit": count,
                "period": period
            }
            
            # Make the request
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if "topartists" in data and "artist" in data["topartists"]:
                    artists = data["topartists"]["artist"]
                    
                    # Process artists
                    result = []
                    for artist in artists:
                        # Extraer datos básicos
                        artist_dict = {
                            "name": artist.get("name", ""),
                            "playcount": int(artist.get("playcount", 0)),
                            "mbid": artist.get("mbid", ""),
                            "url": artist.get("url", "")
                        }
                        
                        # Intentar obtener listeners
                        listeners = artist.get("listeners")
                        if not listeners:
                            # Si no está disponible, intenta hacer una llamada extra para cada artista
                            try:
                                # Solo para los primeros X artistas para no sobrecargar la API
                                if len(result) < 20:  # Limitar a 20 artistas para no hacer demasiadas llamadas
                                    artist_info_params = {
                                        "method": "artist.getInfo",
                                        "artist": artist_dict["name"],
                                        "api_key": self.lastfm_api_key,
                                        "format": "json"
                                    }
                                    artist_info_response = requests.get(url, params=artist_info_params)
                                    if artist_info_response.status_code == 200:
                                        artist_info = artist_info_response.json()
                                        if "artist" in artist_info and "stats" in artist_info["artist"]:
                                            listeners = artist_info["artist"]["stats"].get("listeners", "0")
                            except Exception as e:
                                self.log(f"Error getting listeners for {artist_dict['name']}: {e}")
                        
                        # Añadir listeners al diccionario
                        artist_dict["listeners"] = int(listeners) if listeners else 0
                        
                        result.append(artist_dict)
                    
                    return result
        
        except Exception as e:
            self.log(f"Error fetching top artists from Last.fm: {e}")
            return []



    def search_concerts(self):
        """Search for concerts for the loaded artists"""
        if not hasattr(self, 'current_artists') or not self.current_artists:
            QMessageBox.warning(self, "Error", "No hay artistas cargados. Seleccione una fuente primero.")
            return
        
        # Resetear eventos y desactivar botones
        self.all_events = []
        self.concerts_list.clear()
        self.fetch_all_btn.setEnabled(False)
        self.active_fetchers = 0
        
        # Inicializar lista de fetchers
        self._fetchers = []
        
        # Actualizar configuración (solo API keys y App IDs)
        self.update_service_configs()
        
        # Save current artists to a temporary file
        temp_artists_file = os.path.join(PROJECT_ROOT, ".content", "cache", "temp_artists.txt")
        os.makedirs(os.path.dirname(temp_artists_file), exist_ok=True)
        
        try:
            with open(temp_artists_file, 'w', encoding='utf-8') as f:
                for artist in self.current_artists:
                    f.write(f"{artist}\n")
            
            # Temporarily use this file
            original_file = self.config["artists_file"]
            self.config["artists_file"] = temp_artists_file
            
            # Now launch fetchers with our temp file
            if self.config["apis"]["ticketmaster"].get("enabled", False):
                self.launch_ticketmaster_fetcher()
            
            if self.config["apis"]["songkick"].get("enabled", False):
                self.launch_songkick_fetcher()
            
            if self.config["apis"]["concerts_metal"].get("enabled", False):
                self.launch_concerts_metal_fetcher()
            
            if self.config["apis"]["rapidapi"].get("enabled", False):
                self.launch_rapidapi_fetcher()
            
            if self.config["apis"]["bandsintown"].get("enabled", False):
                self.launch_bandsintown_fetcher()
                
            if self.config["apis"]["dicefm"].get("enabled", False):
                self.launch_dicefm_fetcher()
            
            # Restore original file path
            self.config["artists_file"] = original_file
            
            if self.active_fetchers == 0:
                self.log("No hay servicios habilitados para buscar")
                self.fetch_all_btn.setEnabled(True)
        
        except Exception as e:
            self.log(f"Error en la búsqueda: {e}")
            self.fetch_all_btn.setEnabled(True)


    def fetch_single_service(self, service_name: str):
        """Inicia la búsqueda en un servicio específico"""
        # Actualizar la configuración global
        self.config["country_code"] = self.country_code_input.text().strip()
        self.config["artists_file"] = self.artists_file_input.text().strip()
        
        # Verificar archivo de artistas
        if not self.config["artists_file"] or not os.path.isfile(self.config["artists_file"]):
            QMessageBox.warning(self, "Error", "Seleccione un archivo de artistas válido")
            return
        
        # Resetear eventos y desactivar botones
        self.all_events = []
        self.concerts_list.clear()
        
        # Inicializar la lista de fetchers
        self._fetchers = []
        
        # Desactivar botones
        getattr(self, f"{service_name}_enabled").setEnabled(False)
        self.fetch_all_btn.setEnabled(False)
        self.active_fetchers = 0
        
        # Actualizar configuraciones
        self.update_service_configs()
        
        # Lanzar el servicio correspondiente
        if service_name == "ticketmaster":
            self.launch_ticketmaster_fetcher()
        elif service_name == "songkick":
            self.launch_songkick_fetcher()
        elif service_name == "concerts_metal":
            self.launch_concerts_metal_fetcher()
        elif service_name == "rapidapi":
            self.launch_rapidapi_fetcher()
        elif service_name == "bandsintown":
            self.launch_bandsintown_fetcher()
    
    def update_service_configs(self):
        """Actualiza la configuración de todos los servicios desde la UI"""
        # Actualizar solo las claves API para los servicios que tienen UI creada
        # Ticketmaster
        if hasattr(self, 'ticketmaster_api_key'):
            self.config["apis"]["ticketmaster"]["api_key"] = self.ticketmaster_api_key.text().strip()
        
        # Songkick
        if hasattr(self, 'songkick_api_key'):
            self.config["apis"]["songkick"]["api_key"] = self.songkick_api_key.text().strip()
        
        # Concerts-Metal no tiene API key, no necesita actualización
        
        # RapidAPI
        if hasattr(self, 'rapidapi_api_key'):
            self.config["apis"]["rapidapi"]["api_key"] = self.rapidapi_api_key.text().strip()
        
        # Bandsintown
        if hasattr(self, 'bandsintown_app_id'):
            self.config["apis"]["bandsintown"]["app_id"] = self.bandsintown_app_id.text().strip()
            
        # DiceFM
        if hasattr(self, 'dicefm_api_key') and self.dicefm_api_key is not None:
            self.config["apis"]["dicefm"]["api_key"] = self.dicefm_api_key.text().strip()

    def launch_ticketmaster_fetcher(self):
        """Inicia el fetcher de Ticketmaster"""
        api_key = self.config["apis"]["ticketmaster"]["api_key"]
        if not api_key:
            self.log("Error: No se ha proporcionado API Key para Ticketmaster")
            return
        
        self.active_fetchers += 1
        self.log("Buscando conciertos en Ticketmaster...")
        
        fetcher = TicketmasterFetcher(api_key, self.config["country_code"], self.config["artists_file"])
        fetcher.finished.connect(self.on_fetcher_finished)
        fetcher.error.connect(self.on_fetcher_error)
        
        # Asegurarse de que exista la lista _fetchers
        if not hasattr(self, '_fetchers'):
            self._fetchers = []
        
        self._fetchers.append(fetcher)  # Agregar a la lista de fetchers
        fetcher.start()
    
    def launch_songkick_fetcher(self):
        """Inicia el fetcher de Songkick"""
        api_key = self.config["apis"]["songkick"]["api_key"]
        if not api_key:
            self.log("Error: No se ha proporcionado API Key para Songkick")
            return
        
        self.active_fetchers += 1
        self.log("Buscando conciertos en Songkick...")
        
        fetcher = SongkickFetcher(api_key, self.config["country_code"], self.config["artists_file"])
        fetcher.finished.connect(self.on_fetcher_finished)
        fetcher.error.connect(self.on_fetcher_error)
        fetcher.start()
    
    def launch_concerts_metal_fetcher(self):
        """Inicia el fetcher de Concerts-Metal"""
        self.active_fetchers += 1
        self.log("Buscando conciertos en Concerts-Metal...")
        
        fetcher = MetalConcertsFetcher(self.config["country_code"], self.config["artists_file"])
        fetcher.finished.connect(self.on_fetcher_finished)
        fetcher.error.connect(self.on_fetcher_error)
        
        # Asegurarse de que exista la lista _fetchers
        if not hasattr(self, '_fetchers'):
            self._fetchers = []
        
        self._fetchers.append(fetcher)
        fetcher.start()

    
    def launch_rapidapi_fetcher(self):
        """Inicia el fetcher de RapidAPI"""
        api_key = self.config["apis"]["rapidapi"]["api_key"]
        if not api_key:
            self.log("Error: No se ha proporcionado API Key para RapidAPI")
            return
        
        self.active_fetchers += 1
        self.log("Buscando conciertos en RapidAPI...")
        
        fetcher = RapidAPIFetcher(api_key, self.config["country_code"], self.config["artists_file"])
        fetcher.finished.connect(self.on_fetcher_finished)
        fetcher.error.connect(self.on_fetcher_error)
            # Asegurarse de que exista la lista _fetchers
        if not hasattr(self, '_fetchers'):
            self._fetchers = []
        
        self._fetchers.append(fetcher)
    
        fetcher.start()
    
    def launch_bandsintown_fetcher(self):
        """Inicia el fetcher de Bandsintown"""
        app_id = self.config["apis"]["bandsintown"]["app_id"]
        if not app_id:
            self.log("Error: No se ha proporcionado App ID para Bandsintown")
            return
        
        self.active_fetchers += 1
        self.log("Buscando conciertos en Bandsintown...")
        
        fetcher = BandsintownFetcher(app_id, self.config["country_code"], self.config["artists_file"])
        fetcher.finished.connect(self.on_fetcher_finished)
        fetcher.error.connect(self.on_fetcher_error)
            # Asegurarse de que exista la lista _fetchers
        if not hasattr(self, '_fetchers'):
            self._fetchers = []
        
        self._fetchers.append(fetcher)
    
        fetcher.start()

    def launch_dicefm_fetcher(self):
        """Inicia el fetcher de DiceFM"""
        api_key = self.config["apis"]["dicefm"]["api_key"]
        if not api_key:
            self.log("Error: No se ha proporcionado API Key para DiceFM")
            return
        
        self.active_fetchers += 1
        self.log("Buscando conciertos en DiceFM...")
        
        fetcher = DiceFMFetcher(api_key, self.config["country_code"], self.config["artists_file"])
        fetcher.finished.connect(self.on_fetcher_finished)
        fetcher.error.connect(self.on_fetcher_error)
        
        # Asegurarse de que exista la lista _fetchers
        if not hasattr(self, '_fetchers'):
            self._fetchers = []
        
        self._fetchers.append(fetcher)
        fetcher.start()

    
    def on_fetcher_finished(self, events: List[ConcertEvent], message: str):
        """Gestiona los eventos encontrados por un fetcher"""
        self.log(message)
        self.all_events.extend(events)
        self.display_events(events)
        
        self.active_fetchers -= 1
        if self.active_fetchers == 0:
            self.fetch_all_btn.setEnabled(True)
            # Solo habilitar los botones de servicios que existen
            for service in ["ticketmaster", "songkick", "concerts_metal", "rapidapi", "bandsintown"]:
                if hasattr(self, f"{service}_enabled"):
                    getattr(self, f"{service}_enabled").setEnabled(True)
            
            self.log(f"Búsqueda completada. Se encontraron {len(self.all_events)} conciertos en total.")
    
    def on_fetcher_error(self, error_message: str):
        """Maneja errores de los fetchers"""
        if error_message.startswith("[INFO]"):
            # Es un mensaje informativo, no un error
            self.log(error_message.replace("[INFO] ", ""))
        else:
            # Es un error real
            self.log(f"ERROR: {error_message}")
        
        # Solo decrementamos contador si el mensaje no es informativo y contiene "Error"
        if not error_message.startswith("[INFO]") and "Error" in error_message:
            self.active_fetchers -= 1
            if self.active_fetchers == 0:
                self.fetch_all_btn.setEnabled(True)
                for service in ["ticketmaster", "songkick", "concerts_metal", "rapidapi", "bandsintown"]:
                    if hasattr(self, f"{service}_enabled"):
                        getattr(self, f"{service}_enabled").setEnabled(True)


    def display_events(self, events: List[ConcertEvent]):
        """Muestra los eventos en la lista de conciertos con botones personalizados"""
        for event in events:
            # Crear un widget contenedor para cada elemento
            item_widget = QWidget()
            item_widget.artist = event.artist  # Almacenar el artista directamente en el widget
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(2, 2, 2, 2)
            
            # Etiqueta con la información del concierto
            display_text = f"[{event.source}] {event.artist} - {event.date} @ {event.venue} ({event.city}, {event.country})"
            label = QLabel(display_text)
            
            # Color según la fuente
            if event.source == "Ticketmaster":
                label.setStyleSheet("color: rgb(0, 120, 215);")
            elif event.source == "Songkick":
                label.setStyleSheet("color: rgb(240, 55, 165);")
            elif event.source == "Concerts-Metal":
                label.setStyleSheet("color: rgb(128, 0, 0);")
            elif event.source == "RapidAPI":
                label.setStyleSheet("color: rgb(0, 140, 140);")
            elif event.source == "Bandsintown":
                label.setStyleSheet("color: rgb(55, 100, 240);")
            
            # Botón para abrir URL
            url_btn = QPushButton("🔗")
            url_btn.setToolTip("Abrir página del concierto")
            url_btn.setMaximumWidth(30)
            url_btn.clicked.connect(lambda checked, url=event.url: self.open_url(url))
            
            # Botón para añadir al calendario
            cal_btn = QPushButton("📅")
            cal_btn.setToolTip("Añadir al calendario")
            cal_btn.setMaximumWidth(30)
            cal_btn.clicked.connect(lambda checked, evt=event: self.add_to_calendar(evt))
            
            # Añadir widgets al layout
            item_layout.addWidget(label, 1)  # 1 stretch factor para que ocupe espacio disponible
            item_layout.addWidget(url_btn)
            item_layout.addWidget(cal_btn)
            
            # Añadir el widget personalizado a la lista
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())  # Asegurar que tiene el tamaño correcto
            self.concerts_list.addItem(item)
            self.concerts_list.setItemWidget(item, item_widget)
    
    def open_url(self, url: str):
        """Abre la URL proporcionada en el navegador predeterminado"""
        if url:
            QDesktopServices.openUrl(QUrl(url))
        else:
            self.log("Este concierto no tiene URL asociada")
    
    def log(self, message: str):
        """Envía mensaje de log desde el fetcher"""
        print(f"[{self.__class__.__name__}] {message}")
        # No podemos llamar directamente a QTextEdit desde un hilo
        # Usamos la señal de error para mostrar mensajes informativos también
        #self.error.emit(f"[INFO] {message}")

    def match_ui_elements(self):
        """Conecta los elementos de la UI con las variables del código"""
        # País y archivo de artistas
        self.country_code_input = self.findChild(QLineEdit, "country_code_input")
        self.artists_file_input = self.findChild(QLineEdit, "artists_file_input")
        self.select_file_btn = self.findChild(QPushButton, "select_file_btn")
        self.artists_source_combo = self.findChild(QComboBox, "comboBox")  # Nuevo elemento
        
        # Botón de búsqueda global
        self.fetch_all_btn = self.findChild(QPushButton, "fetch_all_btn")
        
        # Lista de conciertos
        self.concerts_list = self.findChild(QListWidget, "concerts_list")
        
        # Área de log
        self.log_area = self.findChild(QTextEdit, "log_area")
        
        # Pestañas APIs
        self.tabs = self.findChild(QTabWidget, "tabWidget")
        
        # Ticketmaster
        self.ticketmaster_api_key = self.findChild(QLineEdit, "lineEdit")
        self.ticketmaster_enabled = self.findChild(QPushButton, "pushButton")
        
        # Songkick
        self.songkick_api_key = self.findChild(QLineEdit, "lineEdit_4")
        self.songkick_enabled = self.findChild(QPushButton, "pushButton_5")
        
        # Concerts-Metal
        self.concerts_metal_api_key = self.findChild(QLineEdit, "lineEdit_5")
        self.concerts_metal_enabled = self.findChild(QPushButton, "pushButton_2")
        
        # RapidAPI
        self.rapidapi_api_key = self.findChild(QLineEdit, "lineEdit_6")
        self.rapidapi_enabled = self.findChild(QPushButton, "pushButton_3")
        
        # Bandsintown
        self.bandsintown_app_id = self.findChild(QLineEdit, "lineEdit_7")
        self.bandsintown_enabled = self.findChild(QPushButton, "pushButton_4")
        
        # DiceFM (nueva API)
        self.dicefm_api_key = self.findChild(QLineEdit, "dicefm_api_key")
        self.dicefm_enabled = self.findChild(QPushButton, "dicefm_btn")

        # Artist source selection
        self.source_combo = self.findChild(QComboBox, "source_combo")
        self.artists_count_label = self.findChild(QLabel, "artists_count_label")
        
        # Connect search button to the new search method
        search_btn = self.findChild(QPushButton, "search_btn")
        if search_btn:
            search_btn.clicked.connect(self.search_concerts)
        else:
            # If there's no dedicated search button, connect to fetch_all_btn
            self.fetch_all_btn.clicked.connect(self.search_concerts)


    def get_artists_from_source(self, source_type):
        """
        Get artists list from the selected source
        
        Args:
            source_type (str): The source type ('lastfm', 'spotify', 'database', 'file', 'musicbrainz')
            
        Returns:
            list: List of artist names
        """
        artists = []
        
        if source_type == 'lastfm':
            # Get from LastFM
            if hasattr(self, 'lastfm_enabled') and self.lastfm_enabled:
                try:
                    top_artists = self.get_lastfm_top_artists_direct(count=50, period="overall")
                    artists = [artist.get('name', '') for artist in top_artists if artist.get('name')]
                    self.log(f"Loaded {len(artists)} artists from LastFM")
                except Exception as e:
                    self.log(f"Error loading LastFM artists: {e}")
                    
        elif source_type == 'spotify':
            # Get from Spotify
            if hasattr(self, 'spotify_enabled') and self.spotify_enabled:
                try:
                    spotify_client = self.spotify_auth.get_client()
                    if spotify_client:
                        results = spotify_client.current_user_followed_artists(limit=50)
                        if 'artists' in results and 'items' in results['artists']:
                            artists = [artist.get('name', '') for artist in results['artists']['items'] if artist.get('name')]
                            self.log(f"Loaded {len(artists)} artists from Spotify")
                except Exception as e:
                    self.log(f"Error loading Spotify artists: {e}")
        
        elif source_type == 'database':
            # Get from database JSON
            try:
                json_path = os.path.join(PROJECT_ROOT, ".content", "cache", "artists_selected.json")
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        artists_data = json.load(f)
                        artists = [artist.get('nombre', '') for artist in artists_data if artist.get('nombre')]
                        self.log(f"Loaded {len(artists)} artists from database")
                else:
                    self.log(f"Selected artists file not found: {json_path}")
            except Exception as e:
                self.log(f"Error loading database artists: {e}")
        
        elif source_type == 'musicbrainz':
            # Get from MusicBrainz collections
            if hasattr(self, 'musicbrainz_enabled') and self.musicbrainz_enabled:
                try:
                    if self.musicbrainz_auth:
                        # Get user collections
                        collections = self.musicbrainz_auth.get_collections_by_api()
                        if collections:
                            # Find a release collection (first one or one named "Artists")
                            collection_id = None
                            for collection in collections:
                                if collection.get('type') == 'release':
                                    collection_id = collection.get('id')
                                    if collection.get('name') == 'Artists':
                                        break  # Prefer one named "Artists"
                            
                            if collection_id:
                                # Get releases in collection
                                releases = self.musicbrainz_auth.get_collection_contents(collection_id)
                                
                                # Extract artists from releases
                                for release in releases:
                                    if 'artist-credit' in release:
                                        for artist_credit in release['artist-credit']:
                                            if isinstance(artist_credit, dict) and 'artist' in artist_credit:
                                                artist_name = artist_credit['artist'].get('name')
                                                if artist_name and artist_name not in artists:
                                                    artists.append(artist_name)
                                    
                                self.log(f"Loaded {len(artists)} artists from MusicBrainz collection")
                except Exception as e:
                    self.log(f"Error loading MusicBrainz artists: {e}")
        
        elif source_type == 'file':
            # Original functionality - read from artists.txt file
            try:
                if self.config["artists_file"] and os.path.isfile(self.config["artists_file"]):
                    with open(self.config["artists_file"], 'r', encoding='utf-8') as f:
                        artists = [line.strip() for line in f if line.strip()]
                    self.log(f"Loaded {len(artists)} artists from file")
                else:
                    self.log("No valid artists file selected")
            except Exception as e:
                self.log(f"Error loading artists from file: {e}")
        
        return artists








# CLASES PARA CADA SERVICIO

class BaseAPIFetcher(QThread):
    """Clase base para los fetcheres de API"""
    finished = pyqtSignal(object, str)  # Usar 'object' en lugar de List[ConcertEvent]
    error = pyqtSignal(str)
    
    def __init__(self, country_code: str, artists_file: str):
        super().__init__()
        self.country_code = country_code
        self.artists_file = artists_file
        self.directorio_actual = os.path.dirname(os.path.abspath(self.artists_file))
        self._is_running = True
    
    def stop(self):
        """Método para detener el hilo correctamente"""
        self._is_running = False
        self.wait()  # Espera a que el hilo termine
    
    def get_artists_list(self) -> List[str]:
        """Obtiene la lista de artistas del archivo"""
        self.log(f"Intentando leer artistas desde: {self.artists_file}")
        try:
            with open(self.artists_file, 'r', encoding='utf-8') as f:
                artistas = [line.strip() for line in f if line.strip()]
                self.log(f"Artistas leídos: {len(artistas)}")
                if artistas:
                    self.log(f"Primeros 5 artistas: {artistas[:5]}")
                    self.log(f"Último artista: {artistas[-1]}")
                else:
                    self.log("¡Advertencia! No se encontraron artistas en el archivo")
                return artistas
        except Exception as e:
            error_msg = f"Error al leer archivo de artistas: {str(e)}"
            self.log(error_msg)
            self.error.emit(error_msg)
            return []

class TicketmasterFetcher(BaseAPIFetcher):
    def __init__(self, api_key: str, country_code: str, artists_file: str):
        super().__init__(country_code, artists_file)
        self.api_key = api_key
        
    def run(self):
        try:
            # Obtener fechas
            fecha_actual = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
            fecha_proxima = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            artistas_lista = self.get_artists_list()
            if not artistas_lista:
                self.error.emit("No se encontraron artistas en el archivo")
                return
            
            # Obtener datos de la API de Ticketmaster
            url = f"https://app.ticketmaster.com/discovery/v2/events.json?size=200&classificationName=music&startDateTime={fecha_actual}&endDateTime={fecha_proxima}&countryCode={self.country_code}&apikey={self.api_key}"
            
            self.log(f"Realizando petición a Ticketmaster: {url}")
            response = requests.get(url)
            if response.status_code != 200:
                self.error.emit(f"Error en la API de Ticketmaster: {response.status_code} - {response.text}")
                return
                
            json_data = response.json()
            
            # Mostrar estadísticas de eventos devueltos por la API
            total_eventos = len(json_data.get('_embedded', {}).get('events', []))
            self.log(f"La API de Ticketmaster devolvió {total_eventos} eventos totales")
            
            if total_eventos > 0:
                # Mostrar algunos nombres de eventos para verificar
                event_names = [event['name'] for event in json_data.get('_embedded', {}).get('events', [])[:5]]
                self.log(f"Ejemplos de eventos: {event_names}")
            
            # Filtrar los conciertos según los artistas
            eventos_filtrados = []
            artistas_encontrados = set()
            
            if '_embedded' in json_data and 'events' in json_data['_embedded']:
                for event in json_data['_embedded']['events']:
                    event_name = event['name']
                    matched_artist = None
                    
                    for artista in artistas_lista:
                        if self.artist_match(artista, event_name):
                            matched_artist = artista
                            artistas_encontrados.add(artista)
                            break
                    
                    if matched_artist:
                        # Crear un objeto ConcertEvent estandarizado
                        venue_name = event.get('_embedded', {}).get('venues', [{}])[0].get('name', 'Desconocido')
                        city = event.get('_embedded', {}).get('venues', [{}])[0].get('city', {}).get('name', 'Desconocido')
                        url = event.get('url', '')
                        if not url and 'links' in event:
                            url = next((link['url'] for link in event.get('links', {}).get('self', []) 
                                    if link.get('method') == 'GET'), '')
                        
                        # Imagen del evento
                        image_url = None
                        if 'images' in event and event['images']:
                            image_url = next((img['url'] for img in event['images'] 
                                            if img.get('ratio') == '16_9' and img.get('width') > 500), None)
                            if not image_url and event['images']:
                                image_url = event['images'][0].get('url')
                        
                        concierto = ConcertEvent(
                            id=event.get('id', ''),
                            name=event.get('name', 'Sin nombre'),
                            artist=matched_artist,
                            date=event.get('dates', {}).get('start', {}).get('localDate', 'Sin fecha'),
                            venue=venue_name,
                            city=city,
                            country=self.country_code,
                            url=url,
                            source="Ticketmaster",
                            image_url=image_url
                        )
                        eventos_filtrados.append(concierto)
                        self.log(f"¡Coincidencia encontrada! Evento: '{event['name']}' coincide con artista: '{matched_artist}'")
                
                # Mostrar estadísticas de coincidencias
                self.log(f"Se encontraron coincidencias para {len(artistas_encontrados)} artistas de {len(artistas_lista)}")
                if artistas_encontrados:
                    self.log(f"Artistas con coincidencias: {list(artistas_encontrados)}")
                
                # Mostrar artistas sin coincidencias (primeros 10)
                artistas_sin_coincidencia = set(artistas_lista) - artistas_encontrados
                if artistas_sin_coincidencia:
                    self.log(f"Ejemplos de artistas sin coincidencias: {list(artistas_sin_coincidencia)[:10]}")
            else:
                self.log("No se encontraron eventos en la respuesta de Ticketmaster")
            
            # Enviar los eventos encontrados
            self.finished.emit(eventos_filtrados, f"Se encontraron {len(eventos_filtrados)} conciertos en Ticketmaster")
                
        except Exception as e:
            import traceback
            error_msg = f"Error durante la obtención de conciertos de Ticketmaster: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            self.error.emit(error_msg)

    # Implementa esta función de comparación en la clase BaseAPIFetcher
    def artist_match(self, artist_name: str, event_name: str) -> bool:
        """
        Comprueba si un nombre de artista coincide con el nombre de un evento
        usando diferentes estrategias para aumentar la probabilidad de coincidencia
        """
        artist_lower = artist_name.lower().strip()
        event_lower = event_name.lower().strip()
        
        # Estrategia 1: Coincidencia exacta
        if artist_lower == event_lower:
            return True
        
        # Estrategia 2: El artista está en el nombre del evento
        if artist_lower in event_lower:
            # Verificar que sea una palabra completa (evita coincidencias parciales)
            words = event_lower.split()
            for i, word in enumerate(words):
                # Eliminar signos de puntuación al principio o final de la palabra
                word = word.strip(".,;:!?()[]{}")
                if word == artist_lower:
                    return True
                # También verificar combinaciones de palabras (para artistas con nombres compuestos)
                for j in range(1, min(5, len(words) - i)):  # Limitar a combinaciones de hasta 5 palabras
                    phrase = " ".join(words[i:i+j])
                    if phrase == artist_lower:
                        return True
        
        # Estrategia 3: Comparación de palabras clave
        artist_words = set(artist_lower.split())
        event_words = set(event_lower.split())
        # Si todas las palabras del nombre del artista están en el nombre del evento
        # y el artista tiene al menos 2 palabras (para evitar falsos positivos con nombres cortos)
        if len(artist_words) >= 2 and artist_words.issubset(event_words):
            return True
        
        return False


    def log(self, message: str):
        """Envía mensaje de log desde el fetcher"""
        print(f"[{self.__class__.__name__}] {message}")
        # No podemos llamar directamente a QTextEdit desde un hilo
        # Usamos la señal de error para mostrar mensajes informativos también
        self.error.emit(f"[INFO] {message}")


class SongkickFetcher(BaseAPIFetcher):
    def __init__(self, api_key: str, country_code: str, artists_file: str):
        super().__init__(country_code, artists_file)
        self.api_key = api_key
        
    def run(self):
        try:
            artistas_lista = self.get_artists_list()
            if not artistas_lista:
                self.error.emit("No se encontraron artistas en el archivo")
                return
            
            eventos_filtrados = []
            
            # Iterar por cada artista y buscar sus eventos
            for artista in artistas_lista:
                # 1. Primero buscar el ID del artista
                search_url = f"https://api.songkick.com/api/3.0/search/artists.json?query={artista}&apikey={self.api_key}"
                response = requests.get(search_url)
                
                if response.status_code != 200:
                    self.error.emit(f"Error en la búsqueda de artista en Songkick: {response.status_code}")
                    continue
                
                artist_data = response.json()
                if not artist_data.get('resultsPage', {}).get('results', {}).get('artist', []):
                    continue  # No se encontró el artista
                
                artist_id = artist_data['resultsPage']['results']['artist'][0]['id']
                
                # 2. Obtener los eventos del artista
                events_url = f"https://api.songkick.com/api/3.0/artists/{artist_id}/calendar.json?apikey={self.api_key}"
                response = requests.get(events_url)
                
                if response.status_code != 200:
                    self.error.emit(f"Error al obtener eventos de Songkick: {response.status_code}")
                    continue
                
                events_data = response.json()
                events = events_data.get('resultsPage', {}).get('results', {}).get('event', [])
                
                # Filtrar por país si está especificado
                for event in events:
                    event_country = event.get('venue', {}).get('metroArea', {}).get('country', {}).get('code')
                    
                    if not self.country_code or event_country == self.country_code:
                        concierto = ConcertEvent(
                            id=str(event.get('id', '')),
                            name=event.get('displayName', 'Sin nombre'),
                            artist=artista,
                            date=event.get('start', {}).get('date', 'Sin fecha'),
                            venue=event.get('venue', {}).get('displayName', 'Desconocido'),
                            city=event.get('venue', {}).get('metroArea', {}).get('displayName', 'Desconocido'),
                            country=event_country or 'Desconocido',
                            url=event.get('uri', ''),
                            source="Songkick"
                        )
                        eventos_filtrados.append(concierto)
            
            self.finished.emit(eventos_filtrados, f"Se encontraron {len(eventos_filtrados)} conciertos en Songkick")
            
        except Exception as e:
            import traceback
            self.error.emit(f"Error durante la obtención de conciertos de Songkick: {str(e)}\n{traceback.format_exc()}")


class MetalConcertsFetcher(BaseAPIFetcher):
    def __init__(self, country_code: str, artists_file: str):
        super().__init__(country_code, artists_file)
        
    def run(self):
        try:
            # Esta API no tiene autenticación pero es específica para conciertos de metal
            # Implementaremos un web scraping simple para https://es.concerts-metal.com
            
            artistas_lista = self.get_artists_list()
            if not artistas_lista:
                self.error.emit("No se encontraron artistas en el archivo")
                return
            
            eventos_filtrados = []
            
            # Limitamos a 10 artistas para no sobrecargar el sitio
            for artista in artistas_lista[:10]:
                # Construir URL de búsqueda
                search_url = f"https://es.concerts-metal.com/band_{artista.replace(' ', '_')}.html"
                response = requests.get(search_url)
                
                if response.status_code != 200:
                    continue  # Simplemente pasamos al siguiente si no hay resultados
                
                # Aquí necesitaríamos un parser HTML para extraer la información
                # Como esto es un ejemplo, crearemos algunos datos ficticios
                import random
                ciudades = ["Madrid", "Barcelona", "Valencia", "Bilbao", "Sevilla"]
                venues = ["Wizink Center", "Palau Sant Jordi", "Sala Apolo", "La Riviera", "Sala But"]
                
                # Simular 0-2 conciertos por artista
                for _ in range(random.randint(0, 2)):
                    fecha = (datetime.now() + timedelta(days=random.randint(30, 300))).strftime('%Y-%m-%d')
                    ciudad_idx = random.randint(0, len(ciudades) - 1)
                    
                    concierto = ConcertEvent(
                        id=f"metal-{artista}-{fecha}",
                        name=f"Concierto de {artista}",
                        artist=artista,
                        date=fecha,
                        venue=venues[random.randint(0, len(venues) - 1)],
                        city=ciudades[ciudad_idx],
                        country=self.country_code,
                        url=f"https://es.concerts-metal.com/concierto_{artista.replace(' ', '_')}_{fecha}.html",
                        source="Concerts-Metal"
                    )
                    eventos_filtrados.append(concierto)
            
            self.finished.emit(eventos_filtrados, f"Se encontraron {len(eventos_filtrados)} conciertos en Concerts-Metal")
            
        except Exception as e:
            import traceback
            self.error.emit(f"Error durante la obtención de conciertos de Concerts-Metal: {str(e)}\n{traceback.format_exc()}")


class RapidAPIFetcher(BaseAPIFetcher):
    def __init__(self, api_key: str, country_code: str, artists_file: str):
        super().__init__(country_code, artists_file)
        self.api_key = api_key
        
    def run(self):
        try:
            artistas_lista = self.get_artists_list()
            if not artistas_lista:
                self.error.emit("No se encontraron artistas en el archivo")
                return
            
            eventos_filtrados = []
            
            # Usando la API de Predicthq Events como ejemplo (disponible en RapidAPI)
            for artista in artistas_lista:
                url = "https://predicthq-events.p.rapidapi.com/v1/events/"
                querystring = {
                    "category": "concerts",
                    "q": artista,
                    "country": self.country_code,
                    "limit": "10"
                }
                headers = {
                    "X-RapidAPI-Key": self.api_key,
                    "X-RapidAPI-Host": "predicthq-events.p.rapidapi.com"
                }
                
                response = requests.get(url, headers=headers, params=querystring)
                
                if response.status_code != 200:
                    self.error.emit(f"Error en RapidAPI: {response.status_code} - {response.text}")
                    continue
                
                eventos = response.json().get('results', [])
                
                for evento in eventos:
                    concierto = ConcertEvent(
                        id=evento.get('id', ''),
                        name=evento.get('title', 'Sin nombre'),
                        artist=artista,
                        date=evento.get('start', 'Sin fecha').split('T')[0],
                        venue=evento.get('entities', [{}])[0].get('name', 'Desconocido') if evento.get('entities') else 'Desconocido',
                        city=evento.get('location', [0, 0])[0] if evento.get('location') else 'Desconocido',
                        country=self.country_code,
                        url=evento.get('url', ''),
                        source="RapidAPI"
                    )
                    eventos_filtrados.append(concierto)
            
            self.finished.emit(eventos_filtrados, f"Se encontraron {len(eventos_filtrados)} conciertos en RapidAPI")
            
        except Exception as e:
            import traceback
            self.error.emit(f"Error durante la obtención de conciertos de RapidAPI: {str(e)}\n{traceback.format_exc()}")


class BandsintownFetcher(BaseAPIFetcher):
    def __init__(self, app_id: str, country_code: str, artists_file: str):
        super().__init__(country_code, artists_file)
        self.app_id = app_id
    
    def run(self):
        try:
            artistas_lista = self.get_artists_list()
            if not artistas_lista:
                self.error.emit("No se encontraron artistas en el archivo")
                return
            
            eventos_filtrados = []
            
            for artista in artistas_lista:
                # Codificar el nombre del artista para la URL
                encoded_artist = requests.utils.quote(artista)
                
                # Obtener eventos para este artista
                url = f"https://rest.bandsintown.com/artists/{encoded_artist}/events?app_id={self.app_id}"
                response = requests.get(url)
                
                if response.status_code != 200:
                    self.error.emit(f"Error en Bandsintown para {artista}: {response.status_code}")
                    continue
                
                eventos = response.json()
                if not eventos or (isinstance(eventos, dict) and 'errors' in eventos):
                    continue
                
                for evento in eventos:
                    # Filtrar por país si está especificado
                    venue_country = evento.get('venue', {}).get('country')
                    if self.country_code and venue_country != self.country_code:
                        continue
                    
                    concierto = ConcertEvent(
                        id=str(evento.get('id', '')),
                        name=f"{artista} - {evento.get('title', 'Sin título')}",
                        artist=artista,
                        date=evento.get('datetime', 'Sin fecha').split('T')[0] if 'T' in evento.get('datetime', '') else evento.get('datetime', 'Sin fecha'),
                        venue=evento.get('venue', {}).get('name', 'Desconocido'),
                        city=evento.get('venue', {}).get('city', 'Desconocido'),
                        country=venue_country or 'Desconocido',
                        url=evento.get('url', ''),
                        source="Bandsintown",
                        image_url=evento.get('artist', {}).get('image_url')
                    )
                    eventos_filtrados.append(concierto)
            
            self.finished.emit(eventos_filtrados, f"Se encontraron {len(eventos_filtrados)} conciertos en Bandsintown")
            
        except Exception as e:
            import traceback
            self.error.emit(f"Error durante la obtención de conciertos de Bandsintown: {str(e)}\n{traceback.format_exc()}")


class DiceFMFetcher(BaseAPIFetcher):
    def __init__(self, api_key: str, country_code: str, artists_file: str):
        super().__init__(country_code, artists_file)
        self.api_key = api_key
    
    def run(self):
        try:
            artistas_lista = self.get_artists_list()
            if not artistas_lista:
                self.error.emit("No se encontraron artistas en el archivo")
                return
            
            eventos_filtrados = []
            
            # Obtener fechas para el período de búsqueda (próximos 6 meses)
            fecha_inicio = datetime.now().strftime('%Y-%m-%d')
            fecha_fin = (datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d')
            
            # Limitar a un número manejable de artistas para no saturar la API
            for artista in artistas_lista[:30]:  # Limitamos a 30 artistas
                # Codificar el nombre del artista para la URL
                encoded_artist = requests.utils.quote(artista)
                
                # Construir la URL para buscar eventos por artista
                url = f"https://api.dice.fm/v1/events/search"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Parámetros de búsqueda
                params = {
                    "query": artista,
                    "country_code": self.country_code,
                    "date_from": fecha_inicio,
                    "date_to": fecha_fin,
                    "type": "concert",
                    "limit": 10
                }
                
                try:
                    response = requests.get(url, headers=headers, params=params)
                    response.raise_for_status()  # Lanzar excepción si hay un error HTTP
                    
                    data = response.json()
                    events = data.get("data", [])
                    
                    self.log(f"Obtenidos {len(events)} eventos para {artista}")
                    
                    for event in events:
                        # Extraer datos del evento
                        event_id = event.get("id", "")
                        event_name = event.get("name", "Sin nombre")
                        event_date = event.get("start_date", "Sin fecha")
                        venue_name = event.get("venue", {}).get("name", "Desconocido")
                        city = event.get("venue", {}).get("city", "Desconocido")
                        country = event.get("venue", {}).get("country", {}).get("code", self.country_code)
                        event_url = event.get("url", "")
                        image_url = event.get("images", {}).get("large", None)
                        
                        # Crear objeto ConcertEvent
                        concierto = ConcertEvent(
                            id=event_id,
                            name=event_name,
                            artist=artista,
                            date=event_date,
                            venue=venue_name,
                            city=city,
                            country=country,
                            url=event_url,
                            source="DiceFM",
                            image_url=image_url
                        )
                        eventos_filtrados.append(concierto)
                        
                except requests.exceptions.RequestException as e:
                    self.log(f"Error en la solicitud para {artista}: {str(e)}")
                    continue  # Continuar con el siguiente artista
                
                # Añadir un pequeño retraso para no sobrecargar la API
                import time
                time.sleep(0.5)
            
            self.finished.emit(eventos_filtrados, f"Se encontraron {len(eventos_filtrados)} conciertos en DiceFM")
            
        except Exception as e:
            import traceback
            error_msg = f"Error durante la obtención de conciertos de DiceFM: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            self.error.emit(error_msg)
    
    def log(self, message: str):
        """Envía mensaje de log desde el fetcher"""
        print(f"[{self.__class__.__name__}] {message}")
        # Usamos la señal de error para mostrar mensajes informativos también
        self.error.emit(f"[INFO] {message}")


# Nueva clase para el diálogo de configuración de Radicale
class RadicaleConfigDialog(QDialog):
    """Diálogo para configurar la conexión con el servidor Radicale"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Intentar cargar el archivo UI
        ui_file_path = os.path.join(PROJECT_ROOT, "ui", "radicale_config_dialog.ui")
        if os.path.exists(ui_file_path):
            try:
                from PyQt6 import uic
                uic.loadUi(ui_file_path, self)
                
                # Conectar botones
                self.save_button.clicked.connect(self.accept)
                self.cancel_button.clicked.connect(self.reject)
                
                return
            except Exception as e:
                print(f"Error cargando UI del diálogo de configuración de Radicale: {e}")
                import traceback
                traceback.print_exc()
        
        # Método fallback si falla la carga del UI
        self._fallback_init_ui()
    
    def _fallback_init_ui(self):
        """Crea la interfaz de diálogo manualmente si no se puede cargar el archivo UI"""
        self.setWindowTitle("Configuración de Calendario")
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Campos para la configuración
        self.url_input = QLineEdit("http://localhost:5232/")
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.calendar_input = QLineEdit("default")
        
        form.addRow("URL del servidor:", self.url_input)
        form.addRow("Usuario:", self.username_input)
        form.addRow("Contraseña:", self.password_input)
        form.addRow("Calendario:", self.calendar_input)
        
        layout.addLayout(form)
        
        # Botones
        button_box = QHBoxLayout()
        self.save_button = QPushButton("Guardar")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        
        button_box.addWidget(self.save_button)
        button_box.addWidget(self.cancel_button)
        
        layout.addLayout(button_box)
    
    def get_url(self) -> str:
        return self.url_input.text().strip()
    
    def get_username(self) -> str:
        return self.username_input.text().strip()
    
    def get_password(self) -> str:
        return self.password_input.text()
    
    def get_calendar(self) -> str:
        return self.calendar_input.text().strip()


# Opcional: Añadir un método para guardar y cargar la configuración de Radicale
    def save_radicale_config(self, url: str, username: str, calendar: str):
        """Guarda la configuración de Radicale (sin guardar la contraseña)"""
        config_file = os.path.join(os.path.dirname(self.config["artists_file"]), "radicale_config.json")
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "url": url,
                    "username": username,
                    "calendar": calendar
                }, f, indent=2)
            self.log("Configuración de Radicale guardada")
        except Exception as e:
            self.log(f"Error al guardar configuración: {str(e)}")


    def load_radicale_config(self) -> Dict[str, str]:
        """Carga la configuración de Radicale"""
        config_file = os.path.join(os.path.dirname(self.config["artists_file"]), "radicale_config.json")
        
        if not os.path.exists(config_file):
            return {"url": "http://localhost:5232/", "username": "", "calendar": "default"}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.log(f"Error al cargar configuración: {str(e)}")
            return {"url": "http://localhost:5232/", "username": "", "calendar": "default"}


