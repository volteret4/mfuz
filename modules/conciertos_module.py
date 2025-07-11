from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QApplication
from PyQt6.QtWidgets import QLabel, QWidget, QCheckBox, QMenu, QAbstractItemView, QTableWidget, QTableWidgetItem, QComboBox
from PyQt6 import uic
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices, QPixmap, QAction, QShortcut, QKeySequence
from base_module import BaseModule, PROJECT_ROOT
import os
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
import traceback
import time
import sqlite3
from pathlib import Path
from modules.submodules.conciertos.ticketmaster import TicketmasterService
from modules.submodules.conciertos.artist_selector import ArtistSelectorDialog
from modules.submodules.conciertos.worker import ConcertSearchWorker
from modules.submodules.conciertos.spotify import SpotifyService
from modules.submodules.conciertos.setlistfm import SetlistfmService
from modules.submodules.conciertos.muspy import MuspyService
from modules.submodules.conciertos.muspy_artist_selector import MuspyArtistSelectorDialog
from modules.submodules.conciertos import setlistfm
import resources_rc

class ConciertosModule(BaseModule):
    """Módulo para gestionar conciertos de artistas"""
    
    def __init__(self, db_path, **kwargs):
        super().__init__(**kwargs)
        
        # Configuración del módulo
        self.global_config = kwargs.get('global_theme_config', {})  # Configuración global
        self.config = kwargs.get('config', {})  # Configuración específica del módulo
        self.apis = self.config.get('apis', {})
        self.db_path = db_path or self.config.get('db_path', Path(Path.home(), 'db', 'sqlite', 'music.db'))
        
        # Configuración de país
        self.default_country = self.config.get('country_code', 'ES')
        
        # Configuración de Ticketmaster API
        self.ticketmaster_config = self.apis.get('ticketmaster', {})
        self.ticketmaster_enabled = self.ticketmaster_config.get('enabled', 'False').lower() == 'true'
        self.ticketmaster_api_key = self.ticketmaster_config.get('api_key', '')
        
        #Credenciales Spotify
        self.spotify_config = self.apis.get('spotify', {})
        self.spotify_enabled = self.spotify_config.get('enabled', 'False').lower() == 'true'
        self.spotify_client_id = self.global_config.get('spotify_client_id', '')
        self.spotify_client_secret = self.global_config.get('spotify_client_secret', '')
        self.spotify_redirect_uri = self.global_config.get('spotify_redirect_uri', '')

        # Credenciales setlisfm
        self.setlistfm_config = self.apis.get('setlistfm', {})
        self.setlistfm_enabled = self.setlistfm_config.get('enabled', 'False').lower() == 'true'
        self.setlistfm_apikey = self.setlistfm_config.get('setlistfm_apikey')
        


        # Crear directorios de caché si no existen
        self.cache_dir = Path(PROJECT_ROOT) / ".content" / "cache" / "conciertos"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivo de artistas seleccionados (JSON)
        self.saved_artists_file = self.cache_dir / "artistas_conciertos.json"
        self.saved_artists = self._load_saved_artists()
        
        # Lista para almacenar conciertos actuales
        self.current_concerts = []
        
        # Worker para búsquedas en segundo plano
        self.search_worker = None
        
        # Inicializar servicios de APIs
        if self.ticketmaster_enabled:
            self.ticketmaster_service = TicketmasterService(
                api_key=self.ticketmaster_api_key,
                cache_dir=self.cache_dir,
                cache_duration=24
            )
        else:
            self.log_area.append("API de Ticketmaster no está habilitada en la configuración")
        
        # Inicializar servicio de Spotify si está habilitado
        if self.spotify_enabled:
            from modules.submodules.conciertos.spotify import SpotifyService
            
            # Verificar credenciales antes de intentar inicializar
            if not self.spotify_client_id or not self.spotify_client_secret:
                self.log_area.append("Error: Credenciales de Spotify no configuradas")
                self.log_area.append(f"Client ID: {'Configurado' if self.spotify_client_id else 'No configurado'}")
                self.log_area.append(f"Client Secret: {'Configurado' if self.spotify_client_secret else 'No configurado'}")
                self.spotify_enabled = False
            else:
                try:
                    self.spotify_service = SpotifyService(
                        client_id=self.spotify_client_id,
                        client_secret=self.spotify_client_secret,
                        redirect_uri=self.spotify_redirect_uri,
                        cache_dir=self.cache_dir,
                        cache_duration=24
                    )
                    
                    if self.spotify_service.setup():
                        self.log_area.append("Servicio de Spotify inicializado correctamente")
                    else:
                        self.spotify_enabled = False
                        self.log_area.append("Error en la configuración de Spotify")
                        # Agregar diagnóstico más detallado
                        if hasattr(self.spotify_service, 'last_error'):
                            self.log_area.append(f"Detalle del error: {self.spotify_service.last_error}")
                except Exception as e:
                    self.spotify_enabled = False
                    self.log_area.append(f"Excepción al inicializar Spotify: {str(e)}")
                    import traceback
                    self.log_area.append(traceback.format_exc())


        # Inicializar servicio de Setlistfm si está habilitado
        if self.setlistfm_enabled:
            try:
                # Pasar la configuración completa de setlistfm al servicio
                setlistfm_config = self.setlistfm_config.copy()
                setlistfm_config['cache_directory'] = self.cache_dir
                
                self.setlistfm_service = SetlistfmService(
                    api_key=self.setlistfm_apikey,
                    cache_dir=self.cache_dir,
                    cache_duration=24,  # duración de caché en horas
                    db_path=self.db_path,
                    config=setlistfm_config  # Pasar la configuración completa
                )
                self.log_area.append(f"Setlistfm API Key: {self.setlistfm_apikey[:5]}...")  # Solo muestra los primeros 5 caracteres
                self.log_area.append("Servicio de Setlist.fm inicializado correctamente")
            except Exception as e:
                self.log_area.append(f"Error inicializando Setlist.fm: {str(e)}")
                self.log_area.append(traceback.format_exc())
                self.setlistfm_enabled = False
        else:
            self.log_area.append("API de Setlist.fm no está habilitada en la configuración")

        # Inicializar servicio de MuSpy si está habilitado
        self.muspy_config = self.apis.get('muspy', {})
        self.muspy_enabled = self.muspy_config.get('enabled', 'False').lower() == 'true'
        self.muspy_username = self.global_config.get('muspy_username', '')
        self.muspy_password = self.global_config.get('muspy_password', '')
        self.muspy_id = self.global_config.get('muspy_id', '')

        if self.muspy_enabled:
            try:
                self.muspy_service = MuspyService(
                    username=self.muspy_username,
                    password=self.muspy_password,
                    user_id=self.muspy_id,
                    cache_dir=self.cache_dir,
                    cache_duration=24
                )
                self.log_area.append("MuSpy service initialized correctly")
            except Exception as e:
                self.muspy_enabled = False
                self.log_area.append(f"Exception initializing MuSpy: {str(e)}")
                import traceback
                self.log_area.append(traceback.format_exc())
        else:
            self.log_area.append("MuSpy API is not enabled in configuration")

        # Add to your debug log information:
        self.log_area.append(f"MuSpy service exists: {hasattr(self, 'muspy_service')}")


        # Añadir mensaje al campo de búsqueda si está vacío
        if hasattr(self, 'conciertos_search_box') and not self.conciertos_search_box.text():
            self.conciertos_search_box.setPlaceholderText("Buscar artistas individualmente")
        
        # Configurar combobox de fuentes si está vacío
        if hasattr(self, 'source_combo') and self.source_combo.count() == 0:
            sources = ["Artistas de la base de datos", "Artistas de muspy", 
                    "Artistas de Spotify", "Artistas de lastfm", "Artistas de musicbrainz"]
            self.source_combo.addItems(sources)


        
        # Conectar señales después de inicializar la UI
        self.connect_signals()
        
        # Configuración inicial de la UI
        self.update_ui_state()
        
        # Configurar menús contextuales
        self.setup_context_menus()

        # Configurar atajos de teclado
        self.setup_keyboard_shortcuts()

        # Debug: verificar inicialización de servicios
        self.log_area.append(f"Ticketmaster service exists: {hasattr(self, 'ticketmaster_service')}")
        self.log_area.append(f"Spotify service exists: {hasattr(self, 'spotify_service')}")
        self.log_area.append(f"Setlistfm service exists: {hasattr(self, 'setlistfm_service')}")

        self.chrome_config = self.config.get('chrome', {})
        self.chrome_headless = self.chrome_config.get('headless', True)  # Por defecto True

        # Pasar configuración de Chrome al servicio de Spotify
        if self.spotify_enabled:
            from modules.submodules.conciertos.spotify import SpotifyService
            
            # Verificar credenciales antes de intentar inicializar
            if not self.spotify_client_id or not self.spotify_client_secret:
                self.log_area.append("Error: Credenciales de Spotify no configuradas")
                self.log_area.append(f"Client ID: {'Configurado' if self.spotify_client_id else 'No configurado'}")
                self.log_area.append(f"Client Secret: {'Configurado' if self.spotify_client_secret else 'No configurado'}")
                self.spotify_enabled = False
            else:
                try:
                    self.spotify_service = SpotifyService(
                        client_id=self.spotify_client_id,
                        client_secret=self.spotify_client_secret,
                        redirect_uri=self.spotify_redirect_uri,
                        cache_dir=self.cache_dir,
                        cache_duration=24,
                        chrome_headless=self.chrome_headless  # Nueva opción
                    )
                    
                    if self.spotify_service.setup():
                        self.log_area.append("Servicio de Spotify inicializado correctamente")
                    else:
                        self.spotify_enabled = False
                        self.log_area.append("Error en la configuración de Spotify")
                        if hasattr(self.spotify_service, 'last_error'):
                            self.log_area.append(f"Detalle del error: {self.spotify_service.last_error}")
                except Exception as e:
                    self.spotify_enabled = False
                    self.log_area.append(f"Excepción al inicializar Spotify: {str(e)}")
                    import traceback
                    self.log_area.append(traceback.format_exc())
    
    def init_ui(self):
        """Inicializar la UI desde el archivo .ui"""
        if hasattr(self, 'concerts_tree'):
            self.concerts_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.concerts_tree.resizeColumnsToContents()
        ui_file = Path(PROJECT_ROOT, "ui", "conciertos", "conciertos_module.ui")
        try:
            uic.loadUi(ui_file, self)
            
            # IMPORTANTE: Forzar estado inicial DESPUÉS de cargar UI y ANTES de conectar señales
            # Hacer esto SIN triggear la señal
            self.advanced_settings.blockSignals(True)  # Bloquear señales temporalmente
            self.advanced_settings.setChecked(False)   # Desmarcar checkbox
            self.widget_7.setVisible(False)            # Ocultar widget_7
            self.advanced_settings.blockSignals(False) # Reactivar señales
            

            
            # Configurar el placeholder del campo de búsqueda
            self.conciertos_search_box.setPlaceholderText("Buscar artistas individualmente")
        
            return True
        except Exception as e:
            print(f"Error cargando UI: {e}")
            traceback.print_exc()
            return False


    def setup_keyboard_shortcuts(self):
        """
        Configurar atajos de teclado para la aplicación principal
        
        Esta función debe ser llamada después de que la UI esté completamente cargada,
        típicamente al final del método __init__ o setup_ui de la clase principal.
        
        Atajos implementados:
        - Ctrl+F: Foco en el campo de búsqueda
        - Enter en lineEdit: Ejecutar búsqueda
        """
        # Crear atajo Ctrl+F para foco en campo de búsqueda
        shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_search.activated.connect(self.focus_search_box)
        
        # Conectar evento de Enter en conciertos_search_box para realizar búsqueda
        if hasattr(self, 'conciertos_search_box'):
            self.conciertos_search_box.returnPressed.connect(self.search_from_lineedit)
        
    def focus_search_box(self):
        """Establecer foco en el cuadro de búsqueda"""
        if hasattr(self, 'conciertos_search_box'):
            self.conciertos_search_box.setFocus()
            self.conciertos_search_box.selectAll()  # Selecciona todo el texto actual para facilitar reemplazo


    def connect_signals(self):
        """Conectar señales de la UI a métodos"""
        # Conectar el cambio de combobox a la función correspondiente
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        
        # Conectar el botón de búsqueda
        self.pushButton.clicked.connect(self.search_concerts)
        
        # Conectar entrada de texto para búsqueda individual
        self.conciertos_search_box.textChanged.connect(self.on_search_text_changed)
        
                
        # Conectar botón de selección de archivo
        self.select_file_btn.clicked.connect(self.select_artists_file)

        self.paginas_btn.clicked.connect(self.toggle_stacked_widget_page)
        #self.clear_cache_btn.clicked.connect(self.clear_all_cache)
        self.buscar_searchbox.clicked.connect(self.search_from_lineedit)
        self.concerts_tree.cellClicked.connect(self.on_concert_selected)

            # Set up the menu for the add_to_cal button
        self.cal_menu = QMenu(self)
        
        # Select All/None actions
        self.select_all_action = QAction("Seleccionar todos", self)
        self.select_all_action.triggered.connect(self.select_all_concerts)
        self.cal_menu.addAction(self.select_all_action)
        
        self.deselect_all_action = QAction("Deseleccionar todos", self)
        self.deselect_all_action.triggered.connect(self.deselect_all_concerts)
        self.cal_menu.addAction(self.deselect_all_action)
        
        self.cal_menu.addSeparator()
        
        # Create ICS action
        self.create_ics_action = QAction("Crear archivo ICS", self)
        self.create_ics_action.triggered.connect(self.create_ics_file)
        self.cal_menu.addAction(self.create_ics_action)
        
        # Connect the add_to_cal button to show the menu
        self.add_to_cal.setMenu(self.cal_menu)

        # Signal connection for advanced settings checkbox
        self.advanced_settings.stateChanged.connect(self.toggle_advanced_settings)

        # Debug buttons connections if they exist
        # if hasattr(self, 'debug_btn'):
        #     self.debug_btn.clicked.connect(lambda: self.debug_ticketmaster_api(self.lineEdit.text()))
        
        # if hasattr(self, 'debug_btn_2'):
        #     self.debug_btn_2.clicked.connect(lambda: self.debug_ticketmaster_response(self.lineEdit.text()))

        # Conectar botón de ajustes avanzados para abrir diálogo
        if hasattr(self, 'ajustes_button'):
            self.ajustes_button.clicked.connect(self.show_advanced_settings_dialog)

    def toggle_advanced_settings(self, state):
        """Toggle visibility of the entire widget_7 based on checkbox state"""
        # Qt.Checked is equal to 2
        show_advanced = (state == 2)
        
        # Debug: imprimir qué está pasando
        print(f"toggle_advanced_settings called with state: {state}, show_advanced: {show_advanced}")
        
        # Mostrar/ocultar todo el widget_7 que contiene todos los botones
        if hasattr(self, 'widget_7'):
            self.widget_7.setVisible(show_advanced)
            print(f"widget_7 visibility set to: {show_advanced}")
            
            # Debug: listar todos los botones dentro de widget_7
            if show_advanced:
                print("Botones en widget_7:")
                for child in self.widget_7.findChildren(QPushButton):
                    print(f"  - {child.objectName()}: {child.text()}")
                for child in self.widget_7.findChildren(QComboBox):
                    print(f"  - {child.objectName()}: ComboBox")
        else:
            print("ERROR: widget_7 no encontrado!")

    def show_advanced_settings_dialog(self):
        """Mostrar diálogo de ajustes avanzados"""
        dialog = AdvancedSettingsDialog(self, self.config)
        dialog.exec()


    def apply_config_changes(self, updated_config):
        """Aplicar cambios de configuración desde el diálogo"""
        try:
            # Actualizar configuración interna
            self.config.update(updated_config)
            
            # Actualizar variables específicas
            self.default_country = updated_config.get('country_code', 'ES')
            
            # Reinicializar servicios con nueva configuración
            self.reinitialize_services(updated_config)
            
            # Actualizar UI
            self.update_ui_state()
            
            self.log_area.append("Configuración actualizada correctamente")
            self.log_area.append(f"Código de país actualizado a: {self.default_country}")
            
        except Exception as e:
            self.log_area.append(f"Error aplicando cambios de configuración: {e}")


    def reinitialize_services(self, config):
        """Reinicializar servicios con nueva configuración"""
        apis = config.get('apis', {})
        
        # Reinicializar Ticketmaster
        ticketmaster_config = apis.get('ticketmaster', {})
        self.ticketmaster_enabled = ticketmaster_config.get('enabled', 'False').lower() == 'true'
        self.ticketmaster_api_key = ticketmaster_config.get('api_key', '')
        
        if self.ticketmaster_enabled and self.ticketmaster_api_key:
            try:
                self.ticketmaster_service = TicketmasterService(
                    api_key=self.ticketmaster_api_key,
                    cache_dir=self.cache_dir,
                    cache_duration=24
                )
                self.log_area.append("Servicio de Ticketmaster reinicializado")
            except Exception as e:
                self.log_area.append(f"Error reinicializando Ticketmaster: {e}")
        
        # Reinicializar Setlist.fm
        setlistfm_config = apis.get('setlistfm', {})
        self.setlistfm_enabled = setlistfm_config.get('enabled', 'False').lower() == 'true'
        self.setlistfm_apikey = setlistfm_config.get('setlistfm_apikey', '')
        
        if self.setlistfm_enabled and self.setlistfm_apikey:
            try:
                self.setlistfm_service = SetlistfmService(
                    api_key=self.setlistfm_apikey,
                    cache_dir=self.cache_dir,
                    cache_duration=24,
                    db_path=self.db_path,
                    config=setlistfm_config
                )
                self.log_area.append("Servicio de Setlist.fm reinicializado")
            except Exception as e:
                self.log_area.append(f"Error reinicializando Setlist.fm: {e}")
        
        # Reinicializar Spotify
        spotify_config = apis.get('spotify', {})
        self.spotify_enabled = spotify_config.get('enabled', 'False').lower() == 'true'
        
        if self.spotify_enabled:
            try:
                # Spotify usa credenciales globales, solo necesitamos actualizar el estado enabled
                if hasattr(self, 'spotify_service'):
                    self.log_area.append("Servicio de Spotify actualizado")
            except Exception as e:
                self.log_area.append(f"Error actualizando Spotify: {e}")


    def select_all_concerts(self):
        """Select all concerts in the table for calendar export"""
        for row in range(self.concerts_tree.rowCount()):
            checkbox_widget = self.concerts_tree.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
        self.log_area.append("Selected all concerts for calendar export")

    def deselect_all_concerts(self):
        """Deselect all concerts in the table for calendar export"""
        for row in range(self.concerts_tree.rowCount()):
            checkbox_widget = self.concerts_tree.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
        self.log_area.append("Deselected all concerts for calendar export")

    def search_from_lineedit(self):
        """Buscar conciertos para el artista introducido en el lineEdit"""
        # Verificar si ya hay una búsqueda en curso
        if self.search_worker and self.search_worker.isRunning():
            self.log_area.append("Ya hay una búsqueda en curso. Espera a que termine o cancélala.")
            return
        
        # Obtener el texto del lineEdit
        artist_name = self.conciertos_search_box.text().strip()
        
        # Verificar que hay texto y no es el placeholder
        if not artist_name or artist_name == "Buscar artistas individualmente":
            self.log_area.append("Introduce el nombre de un artista para buscar")
            return
        
        # Obtener código de país usando método centralizado
        country_code = self.get_country_code()
        
        # Verificar APIs habilitadas
        enabled_apis = self._get_enabled_apis()
        if not enabled_apis:
            self.log_area.append("No hay APIs habilitadas para buscar conciertos")
            return
        
        # Buscar conciertos para este artista
        self.search_concerts_for_artist(artist_name, country_code)


    def on_concert_selected(self, row, column):
        """Handle selection of a concert in the table"""
        if row < 0 or column < 0:
            return
        
        # Get concert data from the artist column (column 1)
        concert_data = self.concerts_tree.item(row, 1).data(Qt.ItemDataRole.UserRole)
        if not concert_data:
            return
        
        # Build detailed HTML info
        html_info = f"""
        <div style="font-family: sans-serif;">
            <h2>{concert_data['artist']} - {concert_data['name']}</h2>
            <p><b>Venue:</b> {concert_data['venue']}</p>
            <p><b>Location:</b> {concert_data['city']}</p>
            <p><b>Date:</b> {concert_data['date']}</p>
        """
        
        # Add time if available
        if concert_data.get('time'):
            html_info += f"<p><b>Time:</b> {concert_data['time']}</p>"
        
        # Add ticket sources section
        sources = concert_data.get('sources', [])
        if sources:
            html_info += "<h3>Find tickets at:</h3><ul>"
            for source in sources:
                source_name = source.get('name', 'Unknown')
                source_url = source.get('url', '')
                if source_url:
                    html_info += f"<li><a href=\"{source_url}\" style=\"text-decoration: none; color: #3d59a1;\">{source_name}</a></li>"
                else:
                    html_info += f"<li>{source_name} (no link available)</li>"
            html_info += "</ul>"
        
        html_info += "</div>"
        
        # Show information in info area
        self.info_area.setHtml(html_info)
        
        # Load and show image if available
        if concert_data.get('image'):
            self.load_image_for_concert(concert_data)

    def load_image_for_concert(self, concert_data):
        """Cargar imagen del concierto en segundo plano"""
        class ImageLoader(QThread):
            image_loaded = pyqtSignal(QPixmap)
            
            def __init__(self, image_url, cache_dir):
                super().__init__()
                self.image_url = image_url
                self.cache_dir = cache_dir
                
            def run(self):
                try:
                    # Calcular hash para el nombre de archivo en caché
                    import hashlib
                    image_hash = hashlib.md5(self.image_url.encode()).hexdigest()
                    img_path = self.cache_dir / f"img_{image_hash}.jpg"
                    
                    # Verificar si ya existe en caché
                    if img_path.exists():
                        pixmap = QPixmap(str(img_path))
                    else:
                        # Descargar imagen
                        response = requests.get(self.image_url, timeout=10)
                        image_data = response.content
                        
                        # Guardar en caché
                        with open(img_path, 'wb') as f:
                            f.write(image_data)
                        
                        # Cargar en pixmap
                        pixmap = QPixmap()
                        pixmap.loadFromData(image_data)
                    
                    # Emitir señal con la imagen cargada
                    if not pixmap.isNull():
                        self.image_loaded.emit(pixmap)
                except Exception as e:
                    print(f"Error cargando imagen: {e}")
        
        # Iniciar worker para cargar imagen
        image_url = concert_data.get('image')
        if image_url and image_url.startswith('http'):
            self.image_loader = ImageLoader(image_url, self.cache_dir)
            self.image_loader.image_loaded.connect(self.display_concert_image)
            self.image_loader.start()
        elif image_url and Path(image_url).exists():
            # Es una ruta local
            pixmap = QPixmap(image_url)
            if not pixmap.isNull():
                self.display_concert_image(pixmap)
        else:
            # Limpiar imagen anterior
            if hasattr(self, 'foto_label'):
                self.foto_label.clear()

    def display_concert_image(self, pixmap):
        """Display concert image with click to enlarge"""
        if hasattr(self, 'foto_label'):
            # Scale for the thumbnail
            scaled_pixmap = pixmap.scaled(
                self.foto_label.width(), 
                self.foto_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.foto_label.setPixmap(scaled_pixmap)
            
            # Store original pixmap for the dialog
            self.foto_label.setProperty("original_pixmap", pixmap)
            
            # Connect click event if not already connected
            if not self.foto_label.property("click_connected"):
                self.foto_label.mousePressEvent = self.on_image_clicked
                self.foto_label.setCursor(Qt.CursorShape.PointingHandCursor)
                self.foto_label.setProperty("click_connected", True)
                self.foto_label.setToolTip("Click to enlarge")

    def on_image_clicked(self, event):
        """Handle click on image to show enlarged version"""
        label = self.sender()
        if hasattr(label, "property") and label.property("original_pixmap"):
            pixmap = label.property("original_pixmap")
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Concert Image")
            
            # Create label for image
            image_label = QLabel(dialog)
            
            # Calculate size (80% of screen size)
            screen = QApplication.primaryScreen().geometry()
            width = int(screen.width() * 0.8)
            height = int(screen.height() * 0.8)
            
            # Scale image for dialog
            large_pixmap = pixmap.scaled(
                width, height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            image_label.setPixmap(large_pixmap)
            
            # Layout
            layout = QVBoxLayout(dialog)
            layout.addWidget(image_label)
            
            # Add close button
            close_button = QPushButton("Close", dialog)
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)
            
            # Show dialog
            dialog.exec()

    def on_source_changed(self, index):
        """Manejar cambio en el origen de los artistas"""
        # Restablecer el área de búsqueda
        self.conciertos_search_box.clear()
        
        if index == 0:  # Artistas de la base de datos
            self.show_db_artists_dialog()
        elif index == 1:  # Artistas de muspy
            if self.muspy_enabled:
                self.get_muspy_followed_artists()
            else:
                self.log_area.append("API de MuSpy no está habilitada en la configuración")
        elif index == 2:  # Artistas de Spotify
            if self.spotify_enabled:
                self.get_spotify_followed_artists()
            else:
                self.log_area.append("API de Spotify no está habilitada")
        elif index == 3:  # Artistas de lastfm
            self.log_area.append("Funcionalidad de lastfm no implementada aún")
        elif index == 4:  # Artistas de musicbrainz
            self.log_area.append("Funcionalidad de musicbrainz no implementada aún")
    
    def show_db_artists_dialog(self):
        """Mostrar diálogo para seleccionar artistas de la BD y guardar en JSON"""
        conn = self.get_db_connection()
        if not conn:
            self.log_area.append("No se pudo conectar a la base de datos")
            return
        
        dialog = ArtistSelectorDialog(self, conn)
        if dialog.exec():
            selected_artists = dialog.get_selected_artists()
            if selected_artists:
                # Guardar en el archivo JSON
                success = self.save_selected_artists(selected_artists)
                if success:
                    self.log_area.append(f"Se seleccionaron {len(selected_artists)} artistas y se guardaron en {self.saved_artists_file}")
                    # Preguntar si desea buscar conciertos inmediatamente
                    from PyQt6.QtWidgets import QMessageBox
                    reply = QMessageBox.question(
                        self, 
                        'Buscar Conciertos', 
                        '¿Deseas buscar conciertos para los artistas seleccionados ahora?',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        # Obtener código de país
                        country_code = self.country_code_input.text() or self.default_country
                        self.search_concerts_for_saved_artists(country_code)
    
    def on_search_text_changed(self, text):
        """Manejar cambios en el texto de búsqueda individual"""
        # Si era el texto placeholder y ahora está vacío, no hacer nada
        if text == "" and hasattr(self, '_was_placeholder') and self._was_placeholder:
            self._was_placeholder = False
            return
        
        # Si es el texto predeterminado, marcar como placeholder
        if text == "Buscar artistas individualmente":
            self._was_placeholder = True
            return
        
        # Limpiar flag de placeholder
        self._was_placeholder = False
    
    def show_loading_indicator(self, show=True, message=None):
        """Mostrar/ocultar indicador de carga con mensaje opcional"""
        if not hasattr(self, 'loading_widget'):
            # Crear widget de carga si no existe
            from PyQt6.QtWidgets import QProgressBar, QLabel, QVBoxLayout, QWidget
            
            self.loading_widget = QWidget(self)
            layout = QVBoxLayout(self.loading_widget)
            
            self.loading_label = QLabel("Cargando...")
            layout.addWidget(self.loading_label)
            
            self.loading_progress = QProgressBar()
            self.loading_progress.setRange(0, 0)  # Modo indeterminado
            layout.addWidget(self.loading_progress)
            
            self.loading_widget.setLayout(layout)
            self.loading_widget.setStyleSheet("""
                background-color: rgba(255, 255, 255, 220);
                border-radius: 5px;
                padding: 20px;
            """)
            self.loading_widget.hide()
        
        if show:
            # Actualizar mensaje si se proporciona
            if message:
                self.loading_label.setText(message)
            
            # Calcular posición centrada en la página actual
            current_widget = self.stackedWidget.currentWidget()
            x = (current_widget.width() - self.loading_widget.width()) // 2
            y = (current_widget.height() - self.loading_widget.height()) // 2
            self.loading_widget.move(x, y)
            self.loading_widget.show()
            self.loading_widget.raise_()
        else:
            self.loading_widget.hide()



    def search_concerts(self, artist_name, country_code="ES", size=100):  
        """
        Buscar conciertos para un artista en un país específico, primero en caché y luego en API
        
        Args:
            artist_name (str): Nombre del artista a buscar
            country_code (str): Código de país ISO (ES, US, etc.)
            size (int): Número máximo de resultados
            
        Returns:
            tuple: (lista de conciertos, mensaje)
        """
        if not self.ticketmaster_api_key:
            return [], "No se ha configurado API Key para Ticketmaster"
        
        # Comprobar si tenemos resultado en caché válido
        cache_file = TicketmasterService._get_cache_file_path(self, artist_name, country_code)
        cached_data = TicketmasterService._load_from_cache(self, cache_file)
        
        if cached_data:
            return cached_data, f"Se encontraron {len(cached_data)} conciertos para {artist_name} (caché)"
        
        # Si no hay caché válido, consultar API
        params = {
            "keyword": artist_name,
            "classificationName": "music",
            "countryCode": country_code,
            "size": size,
            "sort": "date,asc",
            "apikey": self.api_key
        }
        
        try:
            print(f"Consultando Ticketmaster API para {artist_name} con parámetros: {params}")
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Debug: Imprimir JSON completo para análisis detallado
            import json
            print(f"Respuesta API para {artist_name}:")
            print(json.dumps(data, indent=2)[:1000])  # Limitado a 1000 caracteres
            
            concerts = []
            for event in data['_embedded']['events']:
                # Extract venue data
                venue_data = event.get('_embedded', {}).get('venues', [{}])[0]
                
                # Build address from venue data
                address_parts = []
                if venue_data.get('address', {}).get('line1'):
                    address_parts.append(venue_data['address']['line1'])
                
                if venue_data.get('postalCode'):
                    address_parts.append(venue_data['postalCode'])
                
                address = ', '.join(address_parts)
                
                # Create concert data
                concert = {
                    'artist': artist_name,
                    'name': event.get('name', 'No title'),
                    'venue': venue_data.get('name', 'Unknown venue'),
                    'address': address,  # Add address to concert data
                    'city': venue_data.get('city', {}).get('name', 'Unknown city'),
                    'date': event.get('dates', {}).get('start', {}).get('localDate', 'Unknown date'),
                    'time': event.get('dates', {}).get('start', {}).get('localTime', ''),
                    'image': next((img.get('url', '') for img in event.get('images', []) 
                            if img.get('ratio') == '16_9' and img.get('width') > 500), 
                            event.get('images', [{}])[0].get('url', '') if event.get('images') else ''),
                    'url': event.get('url', ''),
                    'id': event.get('id', '')
                }
                concerts.append(concert)
            
            # Existing code...
        
        except Exception as e:
            print(f"Error API request: {str(e)}")
            return [], f"Error en la solicitud: {str(e)}"
        except ValueError as e:
            print(f"Error procesando API response: {str(e)}")
            return [], f"Error procesando respuesta: {str(e)}"
        except Exception as e:
            import traceback
            print(f"Error general en API: {str(e)}")
            print(traceback.format_exc())
            return [], f"Error inesperado: {str(e)}"
    
    def search_concerts_for_artist(self, artist_name, country_code):
        """Buscar conciertos para un solo artista"""
        # Cambiar a la página de log
        self.stackedWidget.setCurrentIndex(1)
        self.log_area.append(f"Buscando conciertos para: {artist_name} en {country_code}")
        
        # Verificar APIs habilitadas
        enabled_apis = self._get_enabled_apis()
        if not enabled_apis:
            self.log_area.append("No hay APIs habilitadas para buscar conciertos")
            return
        
        # Determinar qué servicios usar
        services = []
        
        if 'ticketmaster' in enabled_apis:
            services.append(('ticketmaster', self.ticketmaster_service))
        
        if 'spotify' in enabled_apis:
            # Verificar que spotify_service existe antes de añadirlo
            if hasattr(self, 'spotify_service') and self.spotify_service is not None:
                services.append(('spotify', self.spotify_service))
                self.log_area.append("Spotify service added to search")
            else:
                self.log_area.append("Spotify no disponible - servicio no inicializado correctamente")
        else:
            self.log_area.append("Spotify no disponible - cliente no inicializado")

        if 'setlistfm' in enabled_apis:
                if hasattr(self, 'setlistfm_service'):
                    services.append(('setlistfm', self.setlistfm_service))
                    self.log_area.append("Setlistfm service added to search")
                else:
                    self.log_area.append("Setlistfm no disponible - servicio no inicializado")



        # Iniciar el worker en un hilo separado con todos los servicios disponibles
        self.search_worker = ConcertSearchWorker(
            services,
            [artist_name], 
            country_code,
            self.db_path  # Pasar ruta de BD
        )
        self.search_worker.log_message.connect(self.log_message)
        self.search_worker.concerts_found.connect(self.display_concerts)
        self.search_worker.search_finished.connect(self.on_search_finished)
        self.search_worker.progress_update.connect(self.update_progress)
        self.search_worker.start()

    def search_concerts_for_saved_artists(self, country_code):
        """
        Buscar conciertos para los artistas guardados en el archivo JSON
        a través de todas las APIs habilitadas
        
        Args:
            country_code (str): Código de país para la búsqueda
        """
        if not self.saved_artists:
            self.log_area.append("No hay artistas guardados. Por favor selecciona artistas primero.")
            return
        
        # Verificar APIs habilitadas
        enabled_apis = self._get_enabled_apis()
        self.log_area.append(f"Enabled APIs before creating services list: {enabled_apis}")
        if not enabled_apis:
            self.log_area.append("No hay APIs habilitadas para buscar conciertos")
            return
        
        # Cambiar a la página de log para mostrar progreso
        self.stackedWidget.setCurrentIndex(1)
        self.log_area.append(f"Buscando conciertos para {len(self.saved_artists)} artistas en {country_code}")
        self.log_area.append(f"Usando APIs: {', '.join(enabled_apis)}")
        
        # Reiniciar progreso si existe una barra de progreso
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(len(self.saved_artists))
        
        # Crear lista de servicios
        services = []
        
        if 'ticketmaster' in enabled_apis:
            services.append(('ticketmaster', self.ticketmaster_service))
        
        if 'spotify' in enabled_apis:
            if hasattr(self, 'spotify_service') and self.spotify_service is not None:
                services.append(('spotify', self.spotify_service))        
        if 'setlistfm' in enabled_apis:
            if hasattr(self, 'setlistfm_service'):
                services.append(('setlistfm', self.setlistfm_service))

        # Crear e iniciar worker
        self.search_worker = ConcertSearchWorker(
            services,
            self.saved_artists, 
            country_code,
            self.db_path
        )
        
        # Conectar señales
        self.search_worker.log_message.connect(self.log_message)
        self.search_worker.concerts_found.connect(self.display_concerts)
        self.search_worker.search_finished.connect(self.on_search_finished)
        
        # Conectar actualización de progreso si tenemos barra de progreso
        if hasattr(self, 'progress_bar'):
            self.search_worker.progress_update.connect(self.update_progress)
        
        # Iniciar búsqueda
        self.search_worker.start()

    def update_progress(self, current, total):
        """
        Actualizar indicador de progreso
        
        Args:
            current (int): Valor actual
            total (int): Valor total
        """
        # Actualizar barra de progreso si existe
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(current)
            self.progress_bar.setMaximum(total)
        
        # Añadir al log
        percentage = int((current / total) * 100)
        self.log_area.append(f"Progreso: {current}/{total} artistas ({percentage}%)")

    def stop_search(self):
        """Detener búsqueda en curso"""
        if self.search_worker and self.search_worker.isRunning():
            self.log_area.append("Deteniendo búsqueda...")
            self.search_worker.stop()
            
            # Opcional: esperar a que termine (con timeout)
            self.search_worker.wait(1000)  # 1 segundo máximo
            
            # Actualizar UI
            self.log_area.append("Búsqueda detenida")

    def clear_cache(self):
        """Limpiar caché de conciertos"""
        if hasattr(self, 'ticketmaster_service'):
            self.ticketmaster_service.clear_cache()
            self.log_area.append("Caché de conciertos limpiado")
    
    def log_message(self, message):
        """Agregar mensaje al área de log"""
        self.log_area.append(message)
    
    def display_concerts(self, concerts):
        """Display concerts in the table widget"""
        # Unificar conciertos antes de mostrar
        unified_concerts = self.unify_concerts(concerts)
        
        # Guardar lista unificada
        self.current_concerts = unified_concerts
        
        # Clear table
        self.concerts_tree.setRowCount(0)
        
        if not unified_concerts:
            self.log_area.append("No concerts found")
            return
        
        # Sort concerts by date
        try:
            def sort_by_date(concert):
                date_str = concert.get('date', '9999-99-99')
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    return datetime(9999, 12, 31)
                    
            concerts_sorted = sorted(unified_concerts, key=sort_by_date)
        except Exception as e:
            self.log_area.append(f"Error sorting concerts: {e}")
            concerts_sorted = unified_concerts
        
        # Configure table headers if needed
        if self.concerts_tree.columnCount() != 4:
            self.concerts_tree.setColumnCount(4)
            self.concerts_tree.setHorizontalHeaderLabels(["Cal", "Artista", "Ciudad", "Fecha"])
        
        # Add concerts to the table
        for i, concert in enumerate(concerts_sorted):
            self.concerts_tree.insertRow(i)
            
            # Calendar checkbox column (first column)
            checkbox = QCheckBox()
            checkbox.setChecked(False)  # Default unchecked
            
            # Create a widget to hold the checkbox and center it
            checkbox_widget = QWidget()
            layout = QHBoxLayout(checkbox_widget)
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Set the widget as the cell widget
            self.concerts_tree.setCellWidget(i, 0, checkbox_widget)
            
            # Artist (second column)
            artist_item = QTableWidgetItem(concert.get('artist', 'Unknown Artist'))
            self.concerts_tree.setItem(i, 1, artist_item)
            
            # City (third column)
            city_item = QTableWidgetItem(concert.get('city', 'Unknown City'))
            self.concerts_tree.setItem(i, 2, city_item)
            
            # Format date (fourth column)
            date_str = concert.get('date', '')
            try:
                if date_str and date_str != 'Unknown date':
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    date_str = date_obj.strftime("%d/%m/%Y")
            except ValueError:
                pass
            
            date_item = QTableWidgetItem(date_str)
            self.concerts_tree.setItem(i, 3, date_item)
            
            # Store full concert data in the artist item
            artist_item.setData(Qt.ItemDataRole.UserRole, concert)
        
        # Resize columns to content
        self.concerts_tree.resizeColumnsToContents()
        
        # Show message with number of concerts
        total_sources = sum(len(c.get('sources', [{}])) for c in unified_concerts)
        self.log_area.append(f"Found {len(unified_concerts)} unique concerts from {total_sources} sources")
        
        # Add summary by source
        sources = {}
        for concert in unified_concerts:
            for source in concert.get('sources', []):
                source_name = source.get('name', 'Unknown')
                sources[source_name] = sources.get(source_name, 0) + 1
        
        for source, count in sources.items():
            self.log_area.append(f"  - {source}: {count} concerts")
        
        # Switch to concerts page if there are results
        if unified_concerts:
            self.stackedWidget.setCurrentIndex(0)
    
    def on_search_finished(self):
        """Handle search completion"""
        self.log_area.append("Search completed")
        
        # Clear reference to worker
        self.search_worker = None
        
        # QTableWidget uses rowCount() instead of count()
        if self.concerts_tree.rowCount() == 0:
            self.log_area.append("No concerts found")
        else:
            # Switch to concerts page
            self.stackedWidget.setCurrentIndex(0)
    
    def save_selected_artists(self, artists):
        """
        Guardar artistas seleccionados en archivo JSON
        
        Args:
            artists (list): Lista de nombres de artistas
            
        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        self.saved_artists = artists
        try:
            # Asegurar que el directorio existe
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Crear estructura de datos para guardar
            data = {
                "timestamp": datetime.now().isoformat(),
                "artists": artists,
                "total": len(artists)
            }
            
            # Guardar en formato JSON
            with open(self.saved_artists_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            self.log_area.append(f"Artistas guardados en {self.saved_artists_file}")
            return True
            
        except Exception as e:
            self.log_area.append(f"Error guardando artistas: {e}")
            return False
    
    def _load_saved_artists(self):
        """
        Cargar artistas guardados desde archivo JSON
        
        Returns:
            list: Lista de nombres de artistas
        """
        if not self.saved_artists_file.exists():
            return []
        
        try:
            with open(self.saved_artists_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Comprobar formato del archivo
                if isinstance(data, list):
                    # Formato antiguo: lista directa de artistas
                    return data
                elif isinstance(data, dict) and 'artists' in data:
                    # Formato nuevo: diccionario con clave 'artists'
                    return data['artists']
                else:
                    self.log_area.append("Formato de archivo de artistas desconocido")
                    return []
        except Exception as e:
            self.log_area.append(f"Error cargando artistas guardados: {e}")
            return []
    
    def export_concerts(self, file_path=None):
        """Exportar conciertos actuales a un archivo JSON"""
        if not self.current_concerts:
            self.log_area.append("No hay conciertos para exportar")
            return
        
        if file_path is None:
            from PyQt6.QtWidgets import QFileDialog
            
            # Convertir a string si es Path
            cache_dir_str = str(self.cache_dir)
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Exportar conciertos",
                cache_dir_str,
                "Archivos JSON (*.json)"
            )
        
        if not file_path:
            return
        
        try:
            # Preparar datos para exportar
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'concerts': self.current_concerts,
                'total': len(self.current_concerts)
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.log_area.append(f"Se exportaron {len(self.current_concerts)} conciertos a {file_path}")
            return True
        except Exception as e:
            self.log_area.append(f"Error exportando conciertos: {e}")
            return False

    def setup_context_menus(self):
        """Configurar menús contextuales para las listas"""
        # Menú contextual para la lista de conciertos
        self.concerts_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.concerts_tree.customContextMenuRequested.connect(self.show_concerts_context_menu)

    def show_concerts_context_menu(self, position):
        """Mostrar menú contextual para la lista de conciertos"""
        # Crear menú contextual
        context_menu = QMenu(self)
        
        # Obtener item seleccionado
        selected_row = self.concerts_tree.rowAt(position.y())
        if selected_row >= 0:
            # Get the item in the artist column (column 1) of the selected row
            selected_item = self.concerts_tree.item(selected_row, 1)
            if selected_item and selected_item.data(Qt.ItemDataRole.UserRole):
                # Acciones para item seleccionado
                concert_data = selected_item.data(Qt.ItemDataRole.UserRole)
                
                # Acción para abrir URL
                if concert_data.get('url'):
                    open_url_action = QAction("Abrir página de entradas", self)
                    open_url_action.triggered.connect(lambda: self.open_concert_url(concert_data))
                    context_menu.addAction(open_url_action)
                
                # Acción para ver detalles
                view_details_action = QAction("Ver detalles", self)
                view_details_action.triggered.connect(lambda: self.on_concert_selected(selected_row, 1))
                context_menu.addAction(view_details_action)
                
                context_menu.addSeparator()
        
        # Acciones generales
        export_action = QAction("Exportar conciertos", self)
        export_action.triggered.connect(self.export_concerts)
        context_menu.addAction(export_action)
        
        clear_cache_action = QAction("Limpiar caché", self)
        clear_cache_action.triggered.connect(self.clear_cache)
        context_menu.addAction(clear_cache_action)
        
        # Mostrar menú contextual
        context_menu.exec(self.concerts_tree.mapToGlobal(position))

    def open_concert_url(self, concert_data):
        """Abrir URL del concierto en el navegador"""
        url = concert_data.get('url')
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def update_ui_state(self):
        """Actualizar el estado de la UI basado en configuración"""
        # Establecer valor predeterminado para país
        # if not self.country_code_input.text():
        #     self.country_code_input.setText(self.default_country)
        
        # Verificar si la API está habilitada
        if not self.ticketmaster_enabled:
            self.log_area.append("ADVERTENCIA: API de Ticketmaster no está habilitada en la configuración")
        
        # Mostrar estado inicial del caché
        cache_files = list(self.cache_dir.glob("*.json"))
        self.log_area.append(f"Caché: {len(cache_files)} archivos")
        
        # Comenzar en la página de lista de conciertos (vacía inicialmente)
        self.stackedWidget.setCurrentIndex(0)

    def get_db_connection(self):
        """
        Obtener conexión a la base de datos
        
        Returns:
            Connection: Objeto de conexión SQLite o None si hay error
        """
        try:
            # Buscar la base de datos en varias ubicaciones posibles
            db_paths = [
                self.db_path,
                Path(PROJECT_ROOT) / ".content" / "database" / "music.db",
                Path(PROJECT_ROOT) / "database" / "music.db",
                Path(PROJECT_ROOT) / "music.db"
            ]
            
            for db_path in db_paths:
                if os.path.exists(str(db_path)):
                    return sqlite3.connect(str(db_path))
            
            self.log_area.append(f"Base de datos no encontrada en ninguna ubicación")
            return None
        except Exception as e:
            self.log_area.append(f"Error conectando a la base de datos: {str(e)}")
            return None

    def select_artists_file(self):
        """Mostrar diálogo para seleccionar archivo de artistas"""
        from PyQt6.QtWidgets import QFileDialog
        
        # Convertir PROJECT_ROOT a string si es un objeto Path
        directory = str(PROJECT_ROOT) if isinstance(PROJECT_ROOT, Path) else PROJECT_ROOT
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de artistas",
            directory,
            "Archivos de texto (*.txt);;Archivos JSON (*.json);;Todos los archivos (*.*)"
        )
        
        if file_path:
            self.artists_file_path = file_path
            self.log_area.append(f"Archivo seleccionado: {file_path}")
            self.load_artists_from_file()

    def load_artists_from_file(self):
        """Cargar artistas desde archivo"""
        if not os.path.exists(self.artists_file_path):
            self.log_area.append(f"El archivo {self.artists_file_path} no existe")
            return []
        
        try:
            artists = []
            ext = os.path.splitext(self.artists_file_path)[1].lower()
            
            if ext == '.json':
                # Cargar de JSON
                with open(self.artists_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Soportar diferentes formatos de JSON
                    if isinstance(data, list):
                        # Lista directa de artistas
                        artists = data
                    elif isinstance(data, dict) and 'artists' in data:
                        # Objeto con clave 'artists'
                        artists = data['artists']
                    else:
                        # Intentar extraer todos los valores que parezcan nombres de artistas
                        for key, value in data.items():
                            if isinstance(value, str) and len(value) > 1:
                                artists.append(value)
            else:
                # Asumir formato de texto (una línea por artista)
                with open(self.artists_file_path, 'r', encoding='utf-8') as f:
                    artists = [line.strip() for line in f if line.strip()]
            
            # Guardar artistas cargados
            self.save_selected_artists(artists)
            self.log_area.append(f"Se cargaron {len(artists)} artistas del archivo")
            
            return artists
        
        except Exception as e:
            self.log_area.append(f"Error cargando artistas del archivo: {str(e)}")
            return []

    def _get_enabled_apis(self):
        """Get list of enabled API services"""
        enabled_apis = []
        
        # Debug: Check the status of each service
        self.log_area.append(f"Checking APIs:")
        self.log_area.append(f"- Ticketmaster enabled: {self.ticketmaster_enabled}")
        self.log_area.append(f"- Spotify enabled: {self.spotify_enabled}")
        self.log_area.append(f"- Setlistfm enabled: {self.setlistfm_enabled}")
        self.log_area.append(f"- MuSpy enabled: {self.muspy_enabled}")
        
        # Check Ticketmaster
        if hasattr(self, 'ticketmaster_service') and self.ticketmaster_enabled:
            enabled_apis.append('ticketmaster')
        
        # Check Spotify
        if hasattr(self, 'spotify_service') and self.spotify_enabled:
            enabled_apis.append('spotify')
        
        # Check Setlist.fm
        if self.setlistfm_enabled:
            enabled_apis.append('setlistfm')
        
        # Check MuSpy
        if hasattr(self, 'muspy_service') and self.muspy_enabled:
            enabled_apis.append('muspy')
        
        self.log_area.append(f"Enabled APIs found: {enabled_apis}")
        return enabled_apis


    def toggle_stacked_widget_page(self):
        """
        Alterna entre las páginas del stackedWidget.
        """
        current_index = self.stackedWidget.currentIndex()
        # Cambiar a la otra página (alterna entre 0 y 1)
        new_index = 1 if current_index == 0 else 0
        self.stackedWidget.setCurrentIndex(new_index)



# Spotify

    def get_spotify_followed_artists(self):
        """Obtener artistas seguidos de Spotify y buscar conciertos"""
        if not hasattr(self, 'spotify_service') or not self.spotify_service:
            self.log_area.append("Servicio de Spotify no está inicializado")
            return
        
        # Obtener artistas seguidos
        artists, message = self.spotify_service.get_user_followed_artists()
        
        # Mostrar mensaje en el log
        self.log_area.append(message)
        
        if not artists:
            # Si necesitamos autorización, iniciar flujo
            if "autorizar" in message.lower():
                self.log_area.append("Iniciando flujo de autorización de Spotify...")
                self.spotify_service.authorize_user_flow(self.on_spotify_auth_completed)
            return
        
        # Guardar artistas en archivo temporal
        self.save_selected_artists(artists)
        self.log_area.append(f"Se guardaron {len(artists)} artistas de Spotify")
        
        # Preguntar si buscar conciertos ahora
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            'Buscar Conciertos',
            f'¿Deseas buscar conciertos para los {len(artists)} artistas seguidos en Spotify?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Obtener código de país
            country_code = self.country_code_input.text() or self.default_country
            self.search_concerts_for_saved_artists(country_code)

    # Add a callback method for Spotify authorization:
    def on_spotify_auth_completed(self, success):
        """Callback para manejar resultado de autorización de Spotify"""
        if success:
            self.log_area.append("Autorización de Spotify completada correctamente")
            # Intentar nuevamente obtener artistas seguidos
            self.get_spotify_followed_artists()
        else:
            self.log_area.append("Error en la autorización de Spotify")


    def unify_concerts(self, concerts):
        """
        Unifica conciertos duplicados manteniendo información de todas las fuentes
        
        Args:
            concerts (list): Lista de conciertos potencialmente duplicados
            
        Returns:
            list: Lista de conciertos unificados
        """
        # Crear diccionario para agrupar conciertos por clave única
        concerts_dict = {}
        
        for concert in concerts:
            # Crear clave única basada en artista, fecha y venue
            key = (
                concert.get('artist', '').lower(),
                concert.get('date', ''),
                concert.get('venue', '').lower()
            )
            
            if key not in concerts_dict:
                # Primer concierto con esta clave
                concerts_dict[key] = {
                    'artist': concert.get('artist', ''),
                    'venue': concert.get('venue', ''),
                    'city': concert.get('city', ''),
                    'date': concert.get('date', ''),
                    'time': concert.get('time', ''),
                    'name': concert.get('name', ''),
                    'image': concert.get('image', ''),
                    'sources': [{
                        'name': concert.get('source', 'Unknown'),
                        'url': concert.get('url', ''),
                        'id': concert.get('id', '')
                    }],
                    # Mantener estructura para compatibilidad
                    'source': concert.get('source', ''),
                    'url': concert.get('url', ''),
                    'id': concert.get('id', '')
                }
            else:
                # Agregar nueva fuente al concierto existente
                existing = concerts_dict[key]
                new_source = {
                    'name': concert.get('source', 'Unknown'),
                    'url': concert.get('url', ''),
                    'id': concert.get('id', '')
                }
                # Evitar duplicados de fuente
                if not any(s['name'] == new_source['name'] and s['url'] == new_source['url'] 
                        for s in existing['sources']):
                    existing['sources'].append(new_source)
                
                # Actualizar información si está vacía
                if not existing.get('time') and concert.get('time'):
                    existing['time'] = concert['time']
                if not existing.get('image') and concert.get('image'):
                    existing['image'] = concert['image']
        
        return list(concerts_dict.values())



# DEBUG

# ticketmaster
    def debug_ticketmaster_response(self, artist_name):
        """
        Método para depurar la respuesta de Ticketmaster
        """
        if not hasattr(self, 'ticketmaster_service') or not self.ticketmaster_enabled:
            self.log_area.append("API de Ticketmaster no está habilitada")
            return
        
        # Usar método centralizado para obtener código de país
        country_code = self.get_country_code()
        self.log_area.append(f"Depurando respuesta de Ticketmaster para: {artist_name} en {country_code}")
        
        # Realizar llamada directa a Ticketmaster
        params = {
            "keyword": artist_name,
            "classificationName": "music",
            "countryCode": country_code,
            "size": 10,  # Limitar para depuración
            "sort": "date,asc",
            "apikey": self.ticketmaster_api_key
        }
        
        try:
            base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Comprobar si hay eventos
            if '_embedded' in data and 'events' in data['_embedded']:
                events = data['_embedded']['events']
                self.log_area.append(f"Se encontraron {len(events)} eventos en la respuesta")
                
                # Mostrar información básica de los primeros 3 eventos
                for i, event in enumerate(events[:3]):
                    event_name = event.get('name', 'Sin nombre')
                    event_date = event.get('dates', {}).get('start', {}).get('localDate', 'Sin fecha')
                    venue = event.get('_embedded', {}).get('venues', [{}])[0].get('name', 'Lugar desconocido')
                    
                    self.log_area.append(f"Evento {i+1}: {event_name} - {event_date} - {venue}")
            else:
                self.log_area.append("No se encontraron eventos en la respuesta")
                if 'errors' in data:
                    self.log_area.append(f"Errores: {data['errors']}")
        
        except Exception as e:
            self.log_area.append(f"Error depurando Ticketmaster: {str(e)}")

    def debug_ticketmaster_api(self, artist_name):
        """Método para depurar directamente la API de Ticketmaster"""
        if not self.ticketmaster_api_key:
            self.log_area.append("No hay API key configurada para Ticketmaster")
            return
        
        # Usar método centralizado para obtener código de país
        country_code = self.get_country_code()
        self.log_area.append(f"Depurando API de Ticketmaster para '{artist_name}' en '{country_code}'")
        
        # Construir URL y parámetros directamente
        base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
        params = {
            "keyword": artist_name,
            "classificationName": "music",
            "countryCode": country_code,
            "size": 100,  # Solicitar más resultados
            "sort": "date,asc",
            "apikey": self.ticketmaster_api_key
        }
        
        # Mostrar URL completa
        from urllib.parse import urlencode
        query_string = urlencode(params)
        full_url = f"{base_url}?{query_string}"
        self.log_area.append(f"URL de consulta: {full_url}")
        
        try:
            # Realizar solicitud directa
            import requests
            response = requests.get(base_url, params=params)
            
            # Mostrar código de estado
            self.log_area.append(f"Código de estado: {response.status_code}")
            
            # Si hay error, mostrar detalles
            if response.status_code != 200:
                self.log_area.append(f"Error en respuesta: {response.text[:500]}")
                return
            
            # Procesar respuesta JSON
            data = response.json()
            
            # Comprobar estructura de respuesta
            if '_embedded' not in data:
                self.log_area.append("No hay sección '_embedded' en la respuesta")
                if 'errors' in data:
                    self.log_area.append(f"Errores: {data['errors']}")
                return
            
            if 'events' not in data['_embedded']:
                self.log_area.append("No hay sección 'events' en '_embedded'")
                return
            
            # Obtener y mostrar eventos
            events = data['_embedded']['events']
            self.log_area.append(f"Número total de eventos: {len(events)}")
            
            # Mostrar detalles de los primeros 5 eventos
            for i, event in enumerate(events[:5]):
                self.log_area.append(f"\nEVENTO {i+1}:")
                self.log_area.append(f"  Nombre: {event.get('name', 'Sin nombre')}")
                self.log_area.append(f"  Fecha: {event.get('dates', {}).get('start', {}).get('localDate', 'Sin fecha')}")
                
                # Mostrar atracciones (artistas)
                if '_embedded' in event and 'attractions' in event['_embedded']:
                    attractions = event['_embedded']['attractions']
                    attraction_names = [a.get('name', 'Sin nombre') for a in attractions]
                    self.log_area.append(f"  Atracciones: {', '.join(attraction_names)}")
                else:
                    self.log_area.append("  No hay información de atracciones")
                    
                # Mostrar lugar
                if '_embedded' in event and 'venues' in event['_embedded']:
                    venue = event['_embedded']['venues'][0]
                    venue_name = venue.get('name', 'Sin nombre')
                    city = venue.get('city', {}).get('name', 'Sin ciudad')
                    country = venue.get('country', {}).get('name', 'Sin país')
                    self.log_area.append(f"  Lugar: {venue_name}, {city}, {country}")
                else:
                    self.log_area.append("  No hay información de lugar")
            
            # Comprobar si hay página siguiente (para ver si hay más resultados)
            if '_links' in data and 'next' in data['_links']:
                self.log_area.append("\nHay una página siguiente con más resultados")
            
            # Si hay muchos eventos, indicar cuántos más hay
            if len(events) > 5:
                self.log_area.append(f"\nHay {len(events) - 5} eventos más que no se muestran aquí")
                
        except Exception as e:
            import traceback
            self.log_area.append(f"Error depurando API: {str(e)}")
            self.log_area.append(traceback.format_exc())

    def clear_all_cache(self):
        """Clear all concert cache"""
        try:
            for file in self.cache_dir.glob("*.json"):
                file.unlink()
            self.log_area.append(f"All concert cache has been cleared")
        except Exception as e:
            self.log_area.append(f"Error clearing cache: {str(e)}")



    def get_event_details(self, event_id):
        """
        Get detailed information about an event from Ticketmaster API
        
        Args:
            event_id (str): Ticketmaster event ID
            
        Returns:
            dict: Event details or empty dict if error
        """
        if not self.ticketmaster_api_key:
            self.log_area.append("No API Key configured for Ticketmaster")
            return {}
        
        # Check if we have valid cached result
        cache_file = self.cache_dir / f"event_details_{event_id}.json"
        cached_data = TicketmasterService._load_from_cache(self, cache_file)
        
        if cached_data:
            return cached_data
        
        # If no valid cache, query API
        base_url = f"https://app.ticketmaster.com/discovery/v2/events/{event_id}"
        params = {
            "apikey": self.ticketmaster_api_key
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Save cache
            self._save_to_cache(cache_file, data)
            
            return data
            
        except requests.exceptions.RequestException as e:
            self.log_area.append(f"Request error: {str(e)}")
            return {}
        except ValueError as e:
            self.log_area.append(f"Error processing response: {str(e)}")
            return {}
        except Exception as e:
            self.log_area.append(f"Unexpected error: {str(e)}")
            return {}

# SETLIST.FM

    def display_setlist_details(self, setlist_id):
        """
        Display setlist details when available
        
        Args:
            setlist_id (str): ID of the setlist
        """
        if not hasattr(self, 'setlistfm_service') or not self.setlistfm_enabled:
            return
        
        try:
            # Fetch setlist details
            headers = {
                'Accept': 'application/json',
                'x-api-key': self.setlistfm_api_key
            }
            
            url = f"https://api.setlist.fm/rest/1.0/setlist/{setlist_id}"
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return
            
            data = response.json()
            
            # Extract setlist information
            sets_data = data.get('sets', {})
            sets = sets_data.get('set', [])
            
            if not sets:
                return
            
            # Build HTML for the setlist
            html = "<h3>Setlist:</h3><ol>"
            
            for set_info in sets:
                songs = set_info.get('song', [])
                
                for song in songs:
                    song_name = song.get('name', '')
                    if song_name:
                        html += f"<li>{song_name}</li>"
            
            html += "</ol>"
            
            # Add to the current info display
            current_html = self.info_area.toHtml()
            new_html = current_html.replace("</div>", f"{html}</div>")
            
            self.info_area.setHtml(new_html)
        
        except Exception as e:
            self.log_area.append(f"Error showing setlist details: {str(e)}")


# MUSPY
    def get_muspy_followed_artists(self):
        """Obtener artistas seguidos en MuSpy y mostrar diálogo de selección"""
        if not hasattr(self, 'muspy_service') or not self.muspy_service:
            self.log_area.append("Servicio de MuSpy no está inicializado")
            return
        
        # Mostrar indicador de carga
        self.show_loading_indicator(True, "Obteniendo artistas de MuSpy...")
        
        # Obtener artistas seguidos
        artists, message = self.muspy_service.get_followed_artists()
        
        # Ocultar indicador de carga
        self.show_loading_indicator(False)
        
        # Mostrar mensaje en el log
        self.log_area.append(message)
        
        if not artists:
            self.log_area.append("No se encontraron artistas en MuSpy o ocurrió un error")
            return
        
        # Mostrar diálogo de selección
        dialog = MuspyArtistSelectorDialog(self, artists)
        if dialog.exec():
            selected_artists = dialog.get_selected_artists()
            if selected_artists:
                # Guardar en el archivo JSON
                success = self.save_selected_artists(selected_artists)
                if success:
                    self.log_area.append(f"Se seleccionaron {len(selected_artists)} artistas de MuSpy y se guardaron")
                    # Preguntar si desea buscar conciertos inmediatamente
                    from PyQt6.QtWidgets import QMessageBox
                    reply = QMessageBox.question(
                        self, 
                        'Buscar Conciertos', 
                        '¿Deseas buscar conciertos para los artistas seleccionados ahora?',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        # Obtener código de país
                        country_code = self.country_code_input.text() or self.default_country
                        self.search_concerts_for_saved_artists(country_code)


# DEBUG SPOTIFY
    def diagnose_spotify_config(self):
        """Diagnosticar configuración de Spotify"""
        self.log_area.append("\n=== DIAGNÓSTICO SPOTIFY ===")
        
        # Verificar variables de entorno
        env_client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        env_client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        
        self.log_area.append(f"Variables de entorno:")
        self.log_area.append(f"  SPOTIFY_CLIENT_ID: {'Configurado' if env_client_id else 'No configurado'}")
        self.log_area.append(f"  SPOTIFY_CLIENT_SECRET: {'Configurado' if env_client_secret else 'No configurado'}")
        
        # Verificar configuración del módulo
        self.log_area.append(f"\nConfiguración del módulo:")
        self.log_area.append(f"  spotify_enabled: {self.spotify_enabled}")
        self.log_area.append(f"  spotify_client_id: {'Configurado' if self.spotify_client_id else 'No configurado'}")
        self.log_area.append(f"  spotify_client_secret: {'Configurado' if self.spotify_client_secret else 'No configurado'}")
        self.log_area.append(f"  spotify_redirect_uri: {self.spotify_redirect_uri}")
        
        # Verificar caché
        cache_files = list(self.cache_dir.glob("spotify_*.json"))
        self.log_area.append(f"\nArchivos de caché:")
        for cache_file in cache_files:
            self.log_area.append(f"  - {cache_file.name}")
        
        self.log_area.append("========================\n")



# CALENDARIO
    def create_ics_file(self):
        """Create an ICS file for selected concerts"""
        selected_concerts = []
        
        # Collect all selected concerts
        for row in range(self.concerts_tree.rowCount()):
            # Get the checkbox from the first column
            checkbox_widget = self.concerts_tree.cellWidget(row, 0)
            if checkbox_widget:
                # Find the checkbox within the widget
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # Get concert data from the artist column (index 1)
                    concert_data = self.concerts_tree.item(row, 1).data(Qt.ItemDataRole.UserRole)
                    if concert_data:
                        selected_concerts.append(concert_data)
        
        if not selected_concerts:
            self.log_area.append("No concerts selected for calendar export")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "No Concerts Selected", 
                                    "Please select at least one concert by checking the box in the calendar column.")
            return
        

        # Ask user for file location
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Calendar File",
            str(Path.home() / "Downloads" / "concerts.ics"),
            "iCalendar Files (*.ics)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Generate ICS content
            ics_content = self.generate_ics_content(selected_concerts)
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(ics_content)
            
            self.log_area.append(f"Calendar file saved to: {file_path}")
            self.log_area.append(f"Added {len(selected_concerts)} concerts to calendar")
            
            # Ask if user wants to open the file
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 
                'Open Calendar File', 
                'Do you want to open the calendar file now?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Open file with default application
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
                
        except Exception as e:
            self.log_area.append(f"Error creating calendar file: {str(e)}")
            import traceback
            self.log_area.append(traceback.format_exc())

    def generate_ics_content(self, concerts):
        """Generate ICS file content for the selected concerts"""
        # Basic ICS header
        ics_content = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Concert Calendar//Music App//ES",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH"
        ]
        
        # Current timestamp for DTSTAMP
        from datetime import datetime
        now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        
        # Generate unique ID base
        import uuid
        uid_base = str(uuid.uuid4())
        
        # Add each concert as an event
        for i, concert in enumerate(concerts):
            # Get basic information
            summary = f"{concert.get('artist', 'Unknown Artist')} @ {concert.get('venue', 'Unknown Venue')}"
            location = f"{concert.get('venue', '')}, {concert.get('city', '')}"
            description = concert.get('name', 'Concert')
            
            # Add venue and other info to description if available
            if concert.get('venue'):
                description += f"\nVenue: {concert.get('venue')}"
            
            # Add URL if available
            if concert.get('url'):
                description += f"\nTicket Info: {concert.get('url')}"
            
            # Format date and time
            date_str = concert.get('date', '')
            time_str = concert.get('time', '19:00')  # Default to 7 PM if not specified
            
            start_date = date_str.replace('-', '')
            
            # Handle time if available, otherwise make it an all-day event
            if time_str and ':' in time_str:
                # Try to parse the time string
                try:
                    hour, minute = time_str.split(':')[:2]
                    start_datetime = f"{start_date}T{hour.zfill(2)}{minute.zfill(2)}00"
                    end_datetime = f"{start_date}T{str(int(hour) + 3).zfill(2)}{minute.zfill(2)}00"  # Default 3-hour concert
                    
                    dtstart = f"DTSTART:{start_datetime}"
                    dtend = f"DTEND:{end_datetime}"
                except:
                    # Fallback to all-day event
                    dtstart = f"DTSTART;VALUE=DATE:{start_date}"
                    dtend = f"DTEND;VALUE=DATE:{start_date}"
            else:
                # All-day event
                dtstart = f"DTSTART;VALUE=DATE:{start_date}"
                dtend = f"DTEND;VALUE=DATE:{start_date}"
            
            # Create unique ID for this event
            uid = f"{uid_base}-{i}@musicapp"
            
            # Add event to calendar
            ics_content.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                dtstart,
                dtend,
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description.replace(chr(10), chr(10) + ' ')}",  # Properly format multi-line description
                f"LOCATION:{location}",
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                "DESCRIPTION:Reminder",
                "TRIGGER:-P1D",  # 1 day before
                "END:VALARM",
                "END:VEVENT"
            ])
        
        # Close calendar
        ics_content.append("END:VCALENDAR")
        
        # Join all lines with CRLF as per ICS spec
        return "\r\n".join(ics_content)

    def get_country_code(self):
        """
        Obtener código de país desde configuración o valor por defecto
        
        Returns:
            str: Código de país (por defecto 'ES')
        """
        # Intentar obtener de configuración actual
        if hasattr(self, 'config') and self.config:
            return self.config.get('country_code', self.default_country)
        
        # Fallback al valor por defecto
        return getattr(self, 'default_country', 'ES')



class AdvancedSettingsDialog(QDialog):
    """Diálogo para configurar ajustes avanzados de APIs"""
    
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.parent = parent
        self.config = config or {}
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Inicializar la UI desde el archivo .ui"""
        if hasattr(self, 'concerts_tree'):
            self.concerts_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.concerts_tree.resizeColumnsToContents()
        ui_file = Path(PROJECT_ROOT, "ui", "conciertos", "conciertos_advanced_settings.ui")
        try:
            uic.loadUi(ui_file, self)
            self.setWindowTitle("Configuración Avanzada - Conciertos")
            self.connect_signals()
            return True
        except Exception as e:
            print(f"Error cargando UI de ajustes: {e}")
            return False
    
    def connect_signals(self):
        """Conectar señales del diálogo"""
        # Conectar botones del QDialogButtonBox
        self.buttonBox.accepted.connect(self.accept_settings)
        self.buttonBox.rejected.connect(self.reject)
        
        # Conectar botones de debug si existen
        if hasattr(self, 'debug_btn'):
            self.debug_btn.clicked.connect(self.debug_response)
        
        if hasattr(self, 'debug_btn_2'):
            self.debug_btn_2.clicked.connect(self.debug_api)
        
        if hasattr(self, 'clear_cache_btn'):
            self.clear_cache_btn.clicked.connect(self.clear_cache)
        
        if hasattr(self, 'select_file_btn'):
            self.select_file_btn.clicked.connect(self.select_file)
    
    def load_settings(self):
        """Cargar configuración actual en los campos del diálogo"""
        if not self.config:
            return
        
        # Cargar código de país
        country_code = self.config.get('country_code', 'ES')
        if hasattr(self, 'country_code_input'):
            self.country_code_input.setText(country_code)
        
        # Cargar configuración de APIs
        apis = self.config.get('apis', {})
        
        # Ticketmaster
        ticketmaster = apis.get('ticketmaster', {})
        if hasattr(self, 'checkBox'):  # Ticketmaster activo
            self.checkBox.setChecked(ticketmaster.get('enabled', 'False').lower() == 'true')
        if hasattr(self, 'conciertos_search_box'):  # API Key Ticketmaster
            self.conciertos_search_box.setText(ticketmaster.get('api_key', ''))
        
        # Setlist.fm
        setlistfm = apis.get('setlistfm', {})
        if hasattr(self, 'checkBox_2'):  # Setlist.fm activo
            self.checkBox_2.setChecked(setlistfm.get('enabled', 'False').lower() == 'true')
        if hasattr(self, 'lineEdit_2'):  # API Key Setlist.fm
            self.lineEdit_2.setText(setlistfm.get('setlistfm_apikey', ''))
        
        # Spotify
        spotify = apis.get('spotify', {})
        if hasattr(self, 'checkBox_3'):  # Spotify activo
            self.checkBox_3.setChecked(spotify.get('enabled', 'False').lower() == 'true')
        if hasattr(self, 'lineEdit_3'):  # Placeholder para Spotify (podría ser Client ID)
            # Como Spotify usa credenciales globales, podrías mostrar el Client ID como referencia
            global_config = getattr(self.parent, 'global_config', {})
            client_id = global_config.get('spotify_client_id', '')
            self.lineEdit_3.setText(client_id[:20] + '...' if len(client_id) > 20 else client_id)
            self.lineEdit_3.setReadOnly(True)  # Solo lectura ya que se configura globalmente



    def accept_settings(self):
        """Guardar configuración y cerrar diálogo"""
        try:
            # Actualizar configuración del módulo
            updated_config = self.get_updated_config()
            
            # Aplicar cambios al módulo padre
            if self.parent:
                self.parent.apply_config_changes(updated_config)
            
            self.accept()
        except Exception as e:
            print(f"Error guardando configuración: {e}")
            # Mostrar mensaje de error al usuario
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Error guardando configuración: {str(e)}")
    
    def get_updated_config(self):
        """Obtener configuración actualizada desde los campos del diálogo"""
        updated_config = self.config.copy()
        
        # Actualizar código de país
        if hasattr(self, 'country_code_input'):
            updated_config['country_code'] = self.country_code_input.text().strip() or 'ES'
        
        # Asegurar que existe la sección apis
        if 'apis' not in updated_config:
            updated_config['apis'] = {}
        
        apis = updated_config['apis']
        
        # Actualizar Ticketmaster
        if 'ticketmaster' not in apis:
            apis['ticketmaster'] = {}
        
        if hasattr(self, 'checkBox'):
            apis['ticketmaster']['enabled'] = 'True' if self.checkBox.isChecked() else 'False'
        if hasattr(self, 'conciertos_search_box'):
            apis['ticketmaster']['api_key'] = self.conciertos_search_box.text().strip()
        
        # Actualizar Setlist.fm
        if 'setlistfm' not in apis:
            apis['setlistfm'] = {}
        
        if hasattr(self, 'checkBox_2'):
            apis['setlistfm']['enabled'] = 'True' if self.checkBox_2.isChecked() else 'False'
        if hasattr(self, 'lineEdit_2'):
            apis['setlistfm']['setlistfm_apikey'] = self.lineEdit_2.text().strip()
        
        # Actualizar Spotify
        if 'spotify' not in apis:
            apis['spotify'] = {}
        
        if hasattr(self, 'checkBox_3'):
            apis['spotify']['enabled'] = 'True' if self.checkBox_3.isChecked() else 'False'
        
        return updated_config
    
    def clear_cache(self):
        """Llamar al método de limpiar caché del módulo padre"""
        if self.parent and hasattr(self.parent, 'clear_all_cache'):
            self.parent.clear_all_cache()
            # Opcionalmente cerrar el diálogo después de limpiar caché
            # self.accept()

    def debug_response(self):
        """Llamar al método de debug de respuesta del módulo padre"""
        if self.parent and hasattr(self.parent, 'debug_ticketmaster_response'):
            artist_name = getattr(self.parent, 'conciertos_search_box', None)
            if artist_name and artist_name.text().strip():
                self.parent.debug_ticketmaster_response(artist_name.text())
            else:
                # Si no hay texto en el lineEdit principal, usar un valor por defecto o pedir al usuario
                self.parent.debug_ticketmaster_response("test")

    def debug_api(self):
        """Llamar al método de debug de API del módulo padre"""
        if self.parent and hasattr(self.parent, 'debug_ticketmaster_api'):
            artist_name = getattr(self.parent, 'conciertos_search_box', None)
            if artist_name and artist_name.text().strip():
                self.parent.debug_ticketmaster_api(artist_name.text())
            else:
                self.parent.debug_ticketmaster_api("test")
    
    def select_file(self):
        """Llamar al método de seleccionar archivo del módulo padre"""
        if self.parent and hasattr(self.parent, 'select_artists_file'):
            self.parent.select_artists_file()