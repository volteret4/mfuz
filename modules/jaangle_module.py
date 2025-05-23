from PyQt6.QtWidgets import (QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QRadioButton,
                          QGroupBox, QGridLayout, QSpinBox, QProgressBar,  QButtonGroup, QTabWidget,
                          QComboBox, QWidget, QMessageBox, QScrollArea, QDialog, QTableWidgetItem,
                          QLineEdit, QCheckBox, QTableWidget, QHeaderView)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView
import random
import sqlite3
from pathlib import Path
import time
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import os
import logging
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from base_module import BaseModule, PROJECT_ROOT
from modules.submodules.jaangle.spotify_player import SpotifyPlayer
from modules.submodules.jaangle.listenbrainz_player import ListenBrainzPlayer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScalableLabel(QLabel):
    def __init__(self, text="", min_font_size=8, max_font_size=16):
        super().__init__(text)
        self._min_font_size = min_font_size
        self._max_font_size = max_font_size
        self._base_font_size = 10  # Tamaño base de fuente
        
        # Configuración inicial de la fuente
        font = self.font()
        font.setPointSize(self._base_font_size)
        self.setFont(font)
        
        # Permitir que el texto se ajuste
        self.setWordWrap(True)
        self.setScaledContents(True)
        
    def resizeEvent(self, event):
        """Ajustar tamaño de fuente al redimensionar"""
        super().resizeEvent(event)
        self.adjust_font_size()
    
    def adjust_font_size(self):
        """Calcular y establecer el tamaño de fuente óptimo"""
        font = self.font()
        
        # Calcular tamaño de fuente basado en el alto del widget
        new_font_size = max(self._min_font_size, 
                             min(self._max_font_size, 
                                 int(self.height() * 0.4)))  # Ajuste empírico
        
        font.setPointSize(new_font_size)
        self.setFont(font)
        
    def set_font_range(self, min_size=8, max_size=16):
        """Método para cambiar el rango de tamaño de fuente"""
        self._min_font_size = min_size
        self._max_font_size = max_size
        self.adjust_font_size()


class MusicQuiz(BaseModule):
    """Módulo de quiz musical que permite a los usuarios adivinar canciones."""
    
    quiz_completed = pyqtSignal()
    
    def __init__(self, parent=None, theme='Tokyo Night', db_path=None, config=None, **kwargs):
        # IMPORTANTE: Inicializar todos los atributos al principio
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Configuración por defecto
        self.quiz_duration_minutes = 5
        self.song_duration_seconds = 30
        self.pause_between_songs = 5
        self.min_song_duration = 60  # Duración mínima en segundos
        self.start_from_beginning_chance = 0.3  # 30% de posibilidad de comenzar desde el principio
        self.avoid_last_seconds = 15  # Evitar los últimos 15 segundos
        self.options_count = 4  # Número de opciones por defecto
        
        # Estado del juego
        self.current_correct_option = None
        self.remaining_time = 0
        self.score = 0
        self.total_played = 0
        self.game_active = False
        self.current_song_path = None
        self.current_song_id = None
        self.current_song = None
        
        # Filtros de sesión
        self.session_filters = None
        
        # Configuración de origen de música - MOVER ESTO AQUÍ
        self.music_origin = 'local'  # Por defecto, usar canciones locales
        self.spotify_user = None
        self.local_radio = None
        self.spotify_radio = None
        self.spotify_container = None
        self.listenbrainz_user = None
        self.listenbrainz_container = None
        
        # Si hay configuración personalizada, aplicarla
        if config:
            if 'min_song_duration' in config:
                self.min_song_duration = config['min_song_duration']
            if 'start_from_beginning_chance' in config:
                self.start_from_beginning_chance = config['start_from_beginning_chance']
            if 'avoid_last_seconds' in config:
                self.avoid_last_seconds = config['avoid_last_seconds']
            if 'options_count' in config:
                self.options_count = config['options_count']
            if 'music_origin' in config:
                self.music_origin = config['music_origin']
            if 'spotify_user' in config:
                self.spotify_user = config['spotify_user']
            if 'listenbrainz_user' in config:
                self.listenbrainz_user = config['listenbrainz_user']
        
        # Media player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Inicializar la UI
        super().__init__(parent, theme)
        
        self.global_config = self.get_global_config()

        # Spotify player - inicializar antes de super().__init__
        self.spotify_player = SpotifyPlayer(db_path=self.db_path, parent=self, config=self.global_config)        
        
        # ListenBrainz player
        self.listenbrainz_player = ListenBrainzPlayer(db_path=self.db_path, parent=self, config=self.global_config)

        self.load_config()

        # Configuración de hotkeys
        self.option_hotkeys = {
            0: Qt.Key.Key_1,  # Opción 1 -> tecla 1
            1: Qt.Key.Key_2,  # Opción 2 -> tecla 2
            2: Qt.Key.Key_3,  # Opción 3 -> tecla 3
            3: Qt.Key.Key_4,  # Opción 4 -> tecla 4
            4: Qt.Key.Key_5,  # Opción 5 -> tecla 5
            5: Qt.Key.Key_6,  # Opción 6 -> tecla 6
            6: Qt.Key.Key_7,  # Opción 7 -> tecla 7
            7: Qt.Key.Key_8,  # Opción 8 -> tecla 8
        }
        
        # Si hay configuración de hotkeys en config, aplicarla
        if config and 'option_hotkeys' in config:
            self.option_hotkeys.update(config['option_hotkeys'])

        # Conectar a la base de datos
        self.connect_to_database()

    def keyPressEvent(self, event):
        """Maneja eventos de teclado para las hotkeys de opciones."""
        if not self.game_active:
            # Si el juego no está activo, ignorar las hotkeys
            super().keyPressEvent(event)
            return
        
        key = event.key()
        
        # Verificar si la tecla presionada coincide con alguna hotkey de opción
        for option_index, hotkey in self.option_hotkeys.items():
            if key == hotkey and option_index < len(self.option_buttons):
                # Simular clic en el botón correspondiente
                self.option_buttons[option_index].click()
                return
        
        # Si no se manejó la tecla, pasar el evento al padre
        super().keyPressEvent(event)


    def show_hotkey_config_dialog(self):
        """Muestra un diálogo para configurar las hotkeys de las opciones."""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QPushButton, QLabel
            from PyQt6.QtCore import Qt
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Configurar Hotkeys para Opciones")
            dialog.setMinimumWidth(350)
            dialog.setMinimumHeight(300)
            
            layout = QVBoxLayout()
            
            # Título e instrucciones
            title_label = QLabel("Configura las teclas para seleccionar opciones")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = title_label.font()
            font.setBold(True)
            title_label.setFont(font)
            
            instructions = QLabel("Haz clic en un botón y presiona la tecla que quieres asignar a esa opción.")
            instructions.setWordWrap(True)
            
            layout.addWidget(title_label)
            layout.addWidget(instructions)
            
            # Grid para los botones de configuración
            grid = QGridLayout()
            hotkey_buttons = {}
            
            # Calcular filas y columnas para una distribución similar a las opciones
            options_count = max(8, self.options_count)  # Permitir hasta 8 opciones
            if options_count <= 4:
                cols = 2
            else:
                cols = 3
            
            # Crear botones para cada opción
            for i in range(options_count):
                row, col = divmod(i, cols)
                
                # Obtener la tecla actual
                current_key = self.option_hotkeys.get(i, Qt.Key.Key_unknown)
                key_text = chr(current_key) if current_key >= Qt.Key.Key_A and current_key <= Qt.Key.Key_Z else f"Tecla {i+1}"
                
                # Crear botón
                button = QPushButton(f"Opción {i+1}: {key_text}")
                button.setCheckable(True)
                button.setProperty("option_index", i)
                hotkey_buttons[i] = button
                
                grid.addWidget(button, row, col)
            
            layout.addLayout(grid)
            
            # Botones de aceptar/cancelar
            buttons_layout = QHBoxLayout()
            save_btn = QPushButton("Guardar")
            cancel_btn = QPushButton("Cancelar")
            reset_btn = QPushButton("Restablecer")
            
            buttons_layout.addWidget(reset_btn)
            buttons_layout.addWidget(save_btn)
            buttons_layout.addWidget(cancel_btn)
            
            layout.addLayout(buttons_layout)
            dialog.setLayout(layout)
            
            # Variables para el estado de captura de teclas
            capturing_for = None
            new_hotkeys = dict(self.option_hotkeys)
            
            # Función para capturar teclas
            def start_capture(button):
                nonlocal capturing_for
                # Desmarcar cualquier otro botón marcado
                for other_button in hotkey_buttons.values():
                    if other_button != button:
                        other_button.setChecked(False)
                
                # Si el botón fue desmarcado, detener la captura
                if not button.isChecked():
                    capturing_for = None
                    return
                    
                # Iniciar captura para este botón
                option_index = button.property("option_index")
                capturing_for = option_index
                button.setText(f"Opción {option_index+1}: Presiona una tecla...")
            
            # Función para manejar el evento de tecla en el diálogo
            def dialog_key_press(event):
                nonlocal capturing_for
                if capturing_for is not None:
                    key = event.key()
                    
                    # Actualizar la asignación de tecla
                    new_hotkeys[capturing_for] = key
                    
                    # Actualizar el texto del botón
                    button = hotkey_buttons[capturing_for]
                    key_text = chr(key) if key >= Qt.Key.Key_A and key <= Qt.Key.Key_Z else f"Tecla {key}"
                    button.setText(f"Opción {capturing_for+1}: {key_text}")
                    
                    # Desmarcar el botón y detener la captura
                    button.setChecked(False)
                    capturing_for = None
                    
                    # Consumir el evento
                    event.accept()
                    return True
                    
                return False
            
            # Función para restablecer las hotkeys predeterminadas
            def reset_hotkeys():
                nonlocal new_hotkeys
                # Restablecer a valores predeterminados
                new_hotkeys = {
                    0: Qt.Key.Key_1,
                    1: Qt.Key.Key_2,
                    2: Qt.Key.Key_3,
                    3: Qt.Key.Key_4,
                    4: Qt.Key.Key_5,
                    5: Qt.Key.Key_6,
                    6: Qt.Key.Key_7,
                    7: Qt.Key.Key_8,
                }
                
                # Actualizar los botones
                for i, button in hotkey_buttons.items():
                    key = new_hotkeys.get(i, Qt.Key.Key_unknown)
                    key_text = chr(key) if key >= Qt.Key.Key_A and key <= Qt.Key.Key_Z else f"Tecla {key}"
                    button.setText(f"Opción {i+1}: {key_text}")
            
            # Conectar señales
            for button in hotkey_buttons.values():
                button.clicked.connect(lambda checked, b=button: start_capture(b))
            
            save_btn.clicked.connect(lambda: dialog.accept())
            cancel_btn.clicked.connect(lambda: dialog.reject())
            reset_btn.clicked.connect(reset_hotkeys)
            
            # Sobreescribir el método keyPressEvent del diálogo
            dialog.keyPressEvent = lambda event: dialog_key_press(event) or QDialog.keyPressEvent(dialog, event)
            
            # Mostrar el diálogo
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Guardar la nueva configuración
                self.option_hotkeys = new_hotkeys
                return True
            
            return False
            
        except Exception as e:
            print(f"Error al mostrar el diálogo de configuración de hotkeys: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")
            return False


    def get_global_config(self):
        """Obtiene la configuración global desde el archivo de configuración."""
        try:
            import yaml
            from pathlib import Path
            
            config_path = Path(PROJECT_ROOT, "config", "config.yml")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config
            return {}
        except Exception as e:
            print(f"Error al cargar la configuración global: {e}")
            return {}


    def init_ui(self):
        """Inicializa la interfaz de usuario del módulo."""
        # Cargar la UI desde el archivo
        ui_file_path = Path(PROJECT_ROOT, "ui", "jaangle", "jaangle_module.ui")
        
        if os.path.exists(ui_file_path):
            try:
                # Cargar el archivo UI
                from PyQt6 import uic
                uic.loadUi(ui_file_path, self)
                
                # Conectar señales y slots
                self.action_toggle.clicked.connect(self.toggle_quiz)
                self.config_button.clicked.connect(self.toggle_config)
                self.filter_artists_btn.clicked.connect(self.show_artist_filter_dialog)
                self.filter_albums_btn.clicked.connect(self.show_album_filter_dialog)
                self.filter_folders_btn.clicked.connect(self.show_folder_filter_dialog)
                self.filter_genres_btn.clicked.connect(self.show_genre_filter_dialog)
                self.filter_sellos_btn.clicked.connect(self.show_sellos_filter_dialog)
                self.session_filters_btn.clicked.connect(self.show_session_filter_dialog)
                self.clear_session_btn.clicked.connect(self.clear_session_filters)
                
                # Agregar controles para seleccionar el origen de música
                self.add_music_origin_controls()
                
                # Inicializar componentes adicionales que no están en el archivo UI
                self.init_options_grid()
                
                # Inicializar el contenedor del reproductor de Spotify si es posible
                if hasattr(self, 'spotify_player'):
                    self.spotify_container = self.spotify_player.create_player_container()
                    if self.spotify_container:
                        # Buscar un lugar adecuado para agregar el contenedor
                        # Primero intentar con un contenedor específico para el reproductor
                        player_container = None
                        
                        if hasattr(self, 'player_container'):
                            player_container = self.player_container
                        elif hasattr(self, 'media_container'):
                            player_container = self.media_container
                        # Intentar encontrar un contenedor principal si no hay uno específico
                        elif hasattr(self, 'main_layout'):
                            # Si hay un layout principal, crear un contenedor
                            player_container = QWidget()
                            self.main_layout.addWidget(player_container)
                        
                        if player_container and player_container.layout():
                            player_container.layout().addWidget(self.spotify_container)
                        elif player_container:
                            layout = QVBoxLayout(player_container)
                            layout.addWidget(self.spotify_container)
                        else:
                            # En último caso, agregar al widget principal
                            layout = QVBoxLayout()
                            layout.addWidget(self.spotify_container)
                            self.setLayout(layout)
                        
                        # Ocultar el contenedor inicialmente
                        self.spotify_container.hide()

                if hasattr(self, 'listenbrainz_player'):
                    self.listenbrainz_container = self.listenbrainz_player.create_player_container()
                    if self.listenbrainz_container:
                        # Buscar un lugar adecuado para agregar el contenedor
                        player_container = None
                        
                        if hasattr(self, 'player_container'):
                            player_container = self.player_container
                        elif hasattr(self, 'media_container'):
                            player_container = self.media_container
                        # Intentar encontrar un contenedor principal si no hay uno específico
                        elif hasattr(self, 'main_layout'):
                            # Si hay un layout principal, crear un contenedor
                            player_container = QWidget()
                            self.main_layout.addWidget(player_container)
                        
                        if player_container and player_container.layout():
                            player_container.layout().addWidget(self.listenbrainz_container)
                        elif player_container:
                            layout = QVBoxLayout(player_container)
                            layout.addWidget(self.listenbrainz_container)
                        else:
                            # En último caso, agregar al widget principal
                            layout = QVBoxLayout()
                            layout.addWidget(self.listenbrainz_container)
                            self.setLayout(layout)
                        
                        # Ocultar el contenedor inicialmente
                        self.listenbrainz_container.hide()

                # Añadir botón para configurar hotkeys
                if hasattr(self, 'config_group'):
                    # Verificar si hay un layout para el grupo de configuración
                    config_layout = self.config_group.layout()
                    if config_layout:
                        # Crear botón para configurar hotkeys
                        hotkeys_btn = QPushButton("Configurar Teclas Rápidas")
                        hotkeys_btn.clicked.connect(self.show_hotkey_config_dialog)
                        
                        # Añadir al layout
                        config_layout.addWidget(hotkeys_btn)

                
            except Exception as e:
                print(f"Error cargando UI desde archivo: {e}")
                import traceback
                traceback.print_exc()
                self._fallback_init_ui()
        else:
            print(f"Archivo UI no encontrado: {ui_file_path}, usando creación manual")
            self._fallback_init_ui()
        
        # Timer para countdown
        self.timer = QTimer()
        self.timer.setInterval(1000)  # 1 segundo
        self.timer.timeout.connect(self.update_countdown)
        
        # Timer para el quiz completo
        self.quiz_timer = QTimer()
        self.quiz_timer.timeout.connect(self.end_quiz)
        
        # Deshabilitar opciones al inicio
        self.enable_options(False)

    def _fallback_init_ui(self):
        """Método de respaldo para inicializar la UI si falla la carga del archivo .ui"""
        # Código existente...
        
        # Agregar los controles de origen de música aquí también
        try:
            # Crear un GroupBox para las opciones de origen
            origin_group = QGroupBox("Origen de Música")
            origin_layout = QHBoxLayout()
            
            # Crear radio buttons
            self.local_radio = QRadioButton("Local")
            self.spotify_radio = QRadioButton("Spotify")
            self.listenbrainz_radio = QRadioButton("ListenBrainz")
            
            # Establecer el valor por defecto según la configuración
            if self.music_origin == 'spotify':
                self.spotify_radio.setChecked(True)
            elif self.music_origin == 'listenbrainz':
                self.listenbrainz_radio.setChecked(True)
            else:
                self.local_radio.setChecked(True)
            
            # Conectar señales
            self.local_radio.toggled.connect(self.on_music_origin_changed)
            self.spotify_radio.toggled.connect(self.on_music_origin_changed)
            self.listenbrainz_radio.toggled.connect(self.on_music_origin_changed)
            
            # Añadir a layout
            origin_layout.addWidget(self.local_radio)
            origin_layout.addWidget(self.spotify_radio)
            origin_layout.addWidget(self.listenbrainz_radio)
            origin_group.setLayout(origin_layout)
            
            # Añadir al layout de configuración (si existe)
            if hasattr(self, 'config_group') and self.config_group.layout():
                self.config_group.layout().addWidget(origin_group)
        except Exception as e:
            print(f"Error al agregar controles de origen de música en fallback: {e}")
        
        # Inicializar el contenedor del reproductor de Spotify si es posible
        if hasattr(self, 'spotify_player'):
            self.spotify_container = self.spotify_player.create_player_container()
            if self.spotify_container and hasattr(self, 'player_container'):
                self.player_container.layout().addWidget(self.spotify_container)
                self.spotify_container.hide()
        
        # Inicializar el contenedor del reproductor de ListenBrainz
        if hasattr(self, 'listenbrainz_player'):
            self.listenbrainz_container = self.listenbrainz_player.create_player_container()
            if self.listenbrainz_container and hasattr(self, 'player_container'):
                self.player_container.layout().addWidget(self.listenbrainz_container)
                self.listenbrainz_container.hide()



    def _fallback_init_option(self, i, row, col, options_layout):
        """Método de respaldo para crear una opción si falla la carga de la UI"""
        option_group = QGroupBox(f"Opción {i+1}")
        option_layout = QHBoxLayout()
        
        # Imagen del álbum
        album_image = QLabel()
        album_image.setFixedSize(80, 80)
        album_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        album_image.setText("Portada")
        album_image.setStyleSheet("border: 1px solid gray; background-color: lightgray;")
        option_layout.addWidget(album_image)
        
        # Información de la canción
        song_info = QVBoxLayout()
        song_label = ScalableLabel("Título:")
        artist_label = ScalableLabel("Artista:")
        album_label = ScalableLabel("Álbum:")
        
        song_info.addWidget(song_label)
        song_info.addWidget(artist_label)
        song_info.addWidget(album_label)
        
        # Contenedor para la información de la canción
        info_container = QWidget()
        info_container.setLayout(song_info)
        option_layout.addWidget(info_container, 1)
        
        # Botón de selección
        select_button = QPushButton("Seleccionar")
        select_button.setProperty("option_id", i)
        select_button.clicked.connect(self.on_option_selected)
        
        # Guardar referencias para actualizar después
        select_button.song_label = song_label
        select_button.artist_label = artist_label
        select_button.album_label = album_label
        select_button.album_image = album_image
        
        option_layout.addWidget(select_button)
        option_group.setLayout(option_layout)
        
        options_layout.addWidget(option_group, row, col)
        self.option_buttons.append(select_button)



    def add_music_origin_controls(self):
        """Agrega controles para seleccionar el origen de música."""
        try:
            # Verificar si ya existe un layout para los controles de configuración
            if not hasattr(self, 'config_group'):
                print("No se encontró config_group para agregar controles de origen")
                return
                    
            config_layout = None
            if hasattr(self.config_group, 'layout'):
                config_layout = self.config_group.layout()
            
            if not config_layout:
                # Si no hay layout, crear uno
                config_layout = QVBoxLayout(self.config_group)
            
            # Crear grupo para origen de música
            origin_group = QGroupBox("Origen de Música")
            origin_layout = QHBoxLayout()
            
            # Crear radio buttons
            self.local_radio = QRadioButton("Local")
            self.spotify_radio = QRadioButton("Spotify")
            self.listenbrainz_radio = QRadioButton("Online")  # Cambiar "ListenBrainz" por "Online"
            
            # Establecer el valor por defecto según la configuración
            if self.music_origin == 'spotify':
                self.spotify_radio.setChecked(True)
            elif self.music_origin == 'online':  # Cambiar 'listenbrainz' por 'online'
                self.listenbrainz_radio.setChecked(True)
            else:
                self.local_radio.setChecked(True)
            
            # Conectar señales
            self.local_radio.toggled.connect(self.on_music_origin_changed)
            self.spotify_radio.toggled.connect(self.on_music_origin_changed)
            self.listenbrainz_radio.toggled.connect(self.on_music_origin_changed)
            
            # Añadir a layout
            origin_layout.addWidget(self.local_radio)
            origin_layout.addWidget(self.spotify_radio)
            origin_layout.addWidget(self.listenbrainz_radio)
            origin_group.setLayout(origin_layout)
            
            # Añadir al layout principal de configuración
            config_layout.addWidget(origin_group)
            
            print("Controles de origen de música agregados correctamente")
        except Exception as e:
            print(f"Error al agregar controles de origen de música: {e}")
            import traceback
            traceback.print_exc()


    def init_options_grid(self):
        """Inicializa la cuadrícula de opciones dinámicamente con un número variable de opciones."""
        # Actualizar el número de opciones desde la configuración en la UI
        if hasattr(self, 'options_count_combo'):
            self.options_count = int(self.options_count_combo.currentText())
        
        # Obtener el layout para las opciones
        options_layout = self.options_grid
        
        # Limpiar el layout si ya tiene widgets
        self.clear_layout(options_layout)
        
        self.option_buttons = []
        
        # Calcular filas y columnas para una distribución equilibrada
        if self.options_count <= 4:
            cols = 2
        else:
            cols = 3
        
        # Ruta al archivo UI de la opción
        option_ui_path = Path(PROJECT_ROOT, "ui", "jaangle", "jaangle_option_item.ui")
        
        for i in range(self.options_count):
            row, col = divmod(i, cols)
            
            try:
                # Cargar la UI de la opción
                option_widget = QWidget()
                from PyQt6 import uic
                uic.loadUi(option_ui_path, option_widget)
                
                # Obtener referencias a los elementos
                select_button = option_widget.findChild(QPushButton, "select_button")
                song_label = option_widget.findChild(QLabel, "song_label")
                artist_label = option_widget.findChild(QLabel, "artist_label")
                album_label = option_widget.findChild(QLabel, "album_label")
                album_image = option_widget.findChild(QLabel, "album_image")
                
                # Configurar el botón
                select_button.setText(f"Opción {i+1}")
                select_button.setProperty("option_id", i)
                select_button.clicked.connect(self.on_option_selected)
                
                # Guardar referencias para actualizar después
                select_button.song_label = song_label
                select_button.artist_label = artist_label
                select_button.album_label = album_label
                select_button.album_image = album_image
                
                options_layout.addWidget(option_widget, row, col)
                self.option_buttons.append(select_button)
                
            except Exception as e:
                print(f"Error al cargar la UI de la opción: {e}")
                # Si falla la carga de la UI, usar el método anterior
                self._fallback_init_option(i, row, col, options_layout)


    # Método auxiliar para limpiar un layout
    def clear_layout(self, layout):
        """Limpia todos los widgets de un layout."""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    sublayout = item.layout()
                    if sublayout is not None:
                        self.clear_layout(sublayout)


    def connect_to_database(self):
        """Establece la conexión con la base de datos."""
        try:
            if not self.db_path:
                project_root = PROJECT_ROOT
                self.db_path = project_root / "data" / "music.db"
            
            # Verificar que el archivo de base de datos existe
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Base de datos no encontrada: {self.db_path}")
            
            self.conn = sqlite3.connect(str(self.db_path))
            self.cursor = self.conn.cursor()
            print(f"Conectado a la base de datos: {self.db_path}")
            
            # Verificar la estructura de la base de datos
            self.cursor.execute("PRAGMA table_info(songs)")
            columns = self.cursor.fetchall()
            required_columns = ["id", "title", "artist", "album", "file_path", "duration"]
            
            column_names = [column[1] for column in columns]
            missing_columns = [col for col in required_columns if col not in column_names]
            
            if missing_columns:
                raise Exception(f"La tabla 'songs' no tiene las columnas necesarias: {', '.join(missing_columns)}")
                
        except Exception as e:
            print(f"Error al conectar a la base de datos: {e}")
            self.show_error_message("Error de base de datos", 
                              f"No se pudo conectar a la base de datos: {e}")

    def toggle_config(self):
        """Muestra u oculta la sección de configuración."""
        self.config_group.setVisible(not self.config_group.isVisible())

    def toggle_quiz(self):
        """Alterna entre iniciar y detener el quiz."""
        if not self.game_active:
            self.start_quiz()
            self.action_toggle.setText("Detener Quiz")  # Actualizar texto del botón
        else:
            self.stop_quiz()
            self.action_toggle.setText("Iniciar Quiz")  # Esto ya está en stop_quiz

    def start_quiz(self):
        """Inicia el juego de quiz musical."""
        # Actualizar configuraciones desde los combobox
        self.quiz_duration_minutes = int(self.quiz_duration_combo.currentText().split()[0])
        self.song_duration_seconds = int(self.song_duration_combo.currentText().split()[0])
        self.pause_between_songs = int(self.pause_duration_combo.currentText().split()[0])
        
        # Actualizar el número de opciones y reconstruir la cuadrícula
        old_options_count = self.options_count
        self.options_count = int(self.options_count_combo.currentText())
        
        # Solo reconstruir si cambió el número de opciones
        if old_options_count != self.options_count:
            self.init_options_grid()
        
        # Inicializar playlist del juego si es necesario
        if self.music_origin == 'online':
            if not self.initialize_game_playlist():
                self.show_error_message("Error", "No se pudo inicializar la playlist del juego")
                return
        
        # Reiniciar estadísticas
        self.score = 0
        self.total_played = 0
        self.update_stats_display()
        
        # Activar el juego
        self.game_active = True
        
        # Actualizar estados de botones
        if hasattr(self, 'start_button') and hasattr(self, 'stop_button'):
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        
        # Iniciar el primer turno
        self.show_next_question()
        
        # Programar el final del quiz
        total_duration_ms = self.quiz_duration_minutes * 60 * 1000
        self.quiz_timer.start(total_duration_ms)
   
   
    def stop_quiz(self):
        """Detiene el juego en curso."""
        self.game_active = False
        
        # Actualizar estados de botones
        if hasattr(self, 'start_button') and hasattr(self, 'stop_button'):
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
        elif hasattr(self, 'action_toggle'):
            self.action_toggle.setText("Iniciar Quiz")
        
        # Detener los timers
        self.timer.stop()
        self.quiz_timer.stop()
        
        # Detener la reproducción local
        self.player.stop()
        
        # Detener reproducción de Spotify
        if hasattr(self, 'spotify_player'):
            self.spotify_player.stop()
            
        # Detener reproducción de ListenBrainz
        if hasattr(self, 'listenbrainz_player'):
            self.listenbrainz_player.stop()
        
        # Ocultar los contenedores de los reproductores
        if hasattr(self, 'spotify_container') and self.spotify_container:
            self.spotify_container.hide()
        if hasattr(self, 'listenbrainz_container') and self.listenbrainz_container:
            self.listenbrainz_container.hide()
        
        # Deshabilitar opciones
        self.enable_options(False)
        
        # Restablecer la visualización
        self.countdown_label.setText("---")
        self.progress_bar.setValue(0)


    def end_quiz(self):
        """Finaliza el quiz cuando se acaba el tiempo total."""
        self.stop_quiz()
        
        # Mostrar resultados finales
        score_percent = 0 if self.total_played == 0 else (self.score / self.total_played) * 100
        msg = QMessageBox()
        msg.setWindowTitle("Quiz completado")
        msg.setText(f"¡Quiz completado!\n\nPuntuación: {self.score}/{self.total_played}\nPrecisión: {score_percent:.1f}%")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
        
        # Emitir señal de quiz completado
        self.quiz_completed.emit()


    # Modificación de get_random_songs() para incluir ListenBrainz

    def get_random_songs(self, count=4, max_retries=3):
        """Versión modificada que incorpora los filtros de sesión y origen de música."""
        retries = 0
        while retries < max_retries:
            try:
                # Construir la consulta base
                query = """
                    SELECT s.id, s.title, s.artist, s.album, s.file_path, s.duration, 
                        a.album_art_path, s.track_number, s.album_art_path_denorm, s.origen
                    FROM songs s
                    LEFT JOIN albums a ON s.album = a.name AND s.artist = (
                        SELECT name FROM artists WHERE id = a.artist_id
                    )
                    WHERE s.duration >= ?
                """
                params = [self.min_song_duration]
                
                # Aplicar filtro por origen
                if self.music_origin == 'local':
                    query += " AND s.origen = 'local' AND s.file_path IS NOT NULL"
                elif self.music_origin == 'spotify':
                    if self.spotify_user:
                        query += " AND s.origen = ?"
                        params.append(f"spotify_{self.spotify_user}")
                    else:
                        query += " AND s.origen LIKE 'spotify_%'"
                    
                    # Asegurarse que hay un enlace de Spotify disponible
                    query += """ 
                    AND EXISTS (
                        SELECT 1 FROM song_links sl 
                        WHERE sl.song_id = s.id 
                        AND sl.spotify_url IS NOT NULL
                    )
                    """
                elif self.music_origin == 'online':
                    # Cambiar para buscar cualquier enlace online (YouTube, SoundCloud, Bandcamp)
                    query += """ 
                    AND EXISTS (
                        SELECT 1 FROM song_links sl 
                        WHERE sl.song_id = s.id 
                        AND (sl.youtube_url IS NOT NULL 
                            OR sl.soundcloud_url IS NOT NULL 
                            OR sl.bandcamp_url IS NOT NULL)
                    )
                    """
                
                # Verificar si hay artistas excluidos
                excluded_artists = self.get_excluded_items("excluded_artists")
                if excluded_artists:
                    placeholders = ", ".join(["?" for _ in excluded_artists])
                    query += f" AND s.artist NOT IN ({placeholders})"
                    params.extend(excluded_artists)
                
                # Verificar si hay álbumes excluidos
                excluded_albums = self.get_excluded_items("excluded_albums")
                if excluded_albums:
                    placeholders = ", ".join(["?" for _ in excluded_albums])
                    query += f" AND s.album NOT IN ({placeholders})"
                    params.extend(excluded_albums)
                
                # Verificar si hay géneros excluidos
                excluded_genres = self.get_excluded_items("excluded_genres")
                if excluded_genres:
                    placeholders = ", ".join(["?" for _ in excluded_genres])
                    query += f" AND s.genre NOT IN ({placeholders})"
                    params.extend(excluded_genres)
                
                # Verificar si hay carpetas excluidas
                excluded_folders = self.get_excluded_items("excluded_folders")
                if excluded_folders:
                    folder_conditions = []
                    for folder in excluded_folders:
                        folder_conditions.append("s.file_path NOT LIKE ?")
                        params.append(f"{folder}%")
                    if folder_conditions:
                        query += f" AND {' AND '.join(folder_conditions)}"
                
                # Aplicar filtros de sesión si están activos
                if hasattr(self, 'session_filters') and self.session_filters:
                    session_filters = self.session_filters.get('filters', {})
                    
                    # Filtrar por artistas incluidos
                    included_artists = session_filters.get('Artistas', [])
                    if included_artists:
                        placeholders = ", ".join(["?" for _ in included_artists])
                        query += f" AND s.artist IN ({placeholders})"
                        params.extend(included_artists)
                    
                    # Filtrar por álbumes incluidos
                    included_albums = session_filters.get('Álbumes', [])
                    if included_albums:
                        placeholders = ", ".join(["?" for _ in included_albums])
                        query += f" AND s.album IN ({placeholders})"
                        params.extend(included_albums)
                    
                    # Filtrar por géneros incluidos
                    included_genres = session_filters.get('Géneros', [])
                    if included_genres:
                        placeholders = ", ".join(["?" for _ in included_genres])
                        query += f" AND s.genre IN ({placeholders})"
                        params.extend(included_genres)
                    
                    # Filtrar por carpetas incluidas
                    included_folders = session_filters.get('Carpetas', [])
                    if included_folders:
                        folder_conditions = []
                        for folder in included_folders:
                            folder_conditions.append("s.file_path LIKE ?")
                            params.append(f"{folder}%")
                        if folder_conditions:
                            query += f" AND ({' OR '.join(folder_conditions)})"
                
                # Agregar orden aleatorio y límite
                query += " ORDER BY RANDOM() LIMIT ?"
                params.append(count * 4)  # Obtener más canciones para tener margen
                
                self.cursor.execute(query, params)
                candidates = self.cursor.fetchall()
                
                if len(candidates) == 0:
                    print(f"La consulta no devolvió resultados: {query}")
                    print(f"Parámetros: {params}")
                    retries += 1
                    continue
                
                # Verificar las canciones según el origen
                valid_songs = []
                for song in candidates:
                    valid = False
                    
                    if self.music_origin == 'local':
                        # Para canciones locales, verificar que el archivo existe
                        if song[4] and os.path.exists(song[4]):
                            valid = True
                    elif self.music_origin == 'spotify':
                        # Para canciones de Spotify, verificar que tengan un enlace válido
                        self.cursor.execute("""
                            SELECT spotify_url FROM song_links 
                            WHERE song_id = ? AND spotify_url IS NOT NULL
                        """, (song[0],))
                        
                        if self.cursor.fetchone():
                            valid = True
                    elif self.music_origin == 'online':
                        # Para canciones online, verificar que tengan un enlace válido
                        self.cursor.execute("""
                            SELECT youtube_url, soundcloud_url, bandcamp_url 
                            FROM song_links 
                            WHERE song_id = ? 
                            AND (youtube_url IS NOT NULL OR soundcloud_url IS NOT NULL OR bandcamp_url IS NOT NULL)
                        """, (song[0],))
                        
                        if self.cursor.fetchone():
                            valid = True
                    
                    if valid:
                        valid_songs.append(song)
                        if len(valid_songs) >= count:
                            break
                
                if len(valid_songs) >= count:
                    return valid_songs[:count]
                
                # Si no hay suficientes canciones válidas, intentar de nuevo
                retries += 1
                print(f"No se encontraron suficientes canciones válidas para {count} opciones. Reintento {retries}/{max_retries}")
            
            except Exception as e:
                print(f"Error al obtener canciones aleatorias: {e}")
                import traceback
                traceback.print_exc()
                retries += 1
        
        # Si llegamos aquí, no pudimos obtener suficientes canciones
        print(f"Error: No se pudieron obtener suficientes canciones válidas ({count}) después de varios intentos")
        return []

    def load_album_art(self, album_art_path):
        """Carga la imagen de la portada del álbum para mostrarla en la UI."""
        if not album_art_path or not os.path.exists(album_art_path):
            # Intentar usar el campo album_art_path_denorm si está disponible
            if hasattr(self, 'current_song') and self.current_song:
                # Comprobar primero la longitud de la tupla para evitar el error de índice
                if len(self.current_song) > 8 and self.current_song[8]:
                    album_art_path = self.current_song[8]
                    if not os.path.exists(album_art_path):
                        return None
                else:
                    return None
            else:
                return None
        
        try:
            pixmap = QPixmap(album_art_path)
            if not pixmap.isNull():
                return pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio)
            else:
                print(f"Error: Pixmap nulo para {album_art_path}")
        except Exception as e:
            print(f"Error al cargar portada del álbum: {e}")
        
        return None

    def initialize_game_playlist(self):
        """Inicializa una playlist de canciones para el juego completo"""
        try:
            if self.music_origin == 'online' and hasattr(self, 'listenbrainz_player'):
                # Crear playlist de 100 canciones
                self.game_playlist = self.listenbrainz_player.create_game_playlist(100)
                if self.game_playlist:
                    logger.info(f"Playlist del juego inicializada con {len(self.game_playlist)} canciones")
                    return True
                else:
                    logger.warning("No se pudo crear playlist del juego")
                    return False
            return True  # Para otros modos no necesitamos playlist
        except Exception as e:
            logger.error(f"Error al inicializar playlist del juego: {e}")
            return False

    def show_next_question(self):
        """Muestra la siguiente pregunta del quiz con soporte mejorado para reproducción."""
        if not self.game_active:
            return
            
        # Detener la reproducción anterior si existe
        self.player.stop()
        if hasattr(self, 'spotify_player'):
            self.spotify_player.stop()
        if hasattr(self, 'listenbrainz_player'):
            self.listenbrainz_player.stop()
        
        # Obtener las canciones aleatorias (ahora con número variable)
        songs = self.get_random_songs(self.options_count)
        
        if not songs or len(songs) < self.options_count:
            self.show_error_message("Error", f"No hay suficientes canciones en la base de datos para mostrar {self.options_count} opciones.")
            self.stop_quiz()
            return
            
        # Elegir una canción aleatoria como correcta
        self.current_correct_option = random.randint(0, self.options_count - 1)
        self.current_song = songs[self.current_correct_option]
        
        # Configurar las opciones
        for i, button in enumerate(self.option_buttons):
            song = songs[i]
            song_id, title, artist, album, file_path, duration, album_art_path, track_number, album_art_path_denorm, origen = song
            
            # Actualizar información de la canción
            button.song_label.setText(f"♪ {title}")
            button.artist_label.setText(f"👤 {artist}")
            button.album_label.setText(f"💿 {album}")
            
            # Cargar imagen del álbum
            pixmap = self.load_album_art(album_art_path_denorm if album_art_path_denorm else album_art_path)
            if pixmap:
                button.album_image.setPixmap(pixmap)
            else:
                button.album_image.setText("🎵")
                button.album_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Restablecer estilo del botón
            button.setStyleSheet("")
            button.setEnabled(True)
        
        # Habilitar los botones
        self.enable_options(True)
        
        # Mostrar mensaje de carga
        if hasattr(self, 'countdown_label'):
            self.countdown_label.setText("Cargando...")
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(10)
        
        # Obtener los IDs de todas las canciones para una posible playlist
        song_ids = [song[0] for song in songs if song[0] is not None]
        
        # Iniciar la reproducción de la canción correcta según el origen
        correct_song = songs[self.current_correct_option]
        self.current_song_id = correct_song[0] if len(correct_song) > 0 else None  # ID de la canción

        try:
            if self.music_origin == 'spotify':
                # Usar el reproductor de Spotify
                if hasattr(self, 'spotify_container') and self.spotify_container:
                    self.spotify_container.show()
                    
                if self.current_song_id is not None:
                    QTimer.singleShot(2000, lambda: self._play_spotify_track())
                else:
                    logger.error("ID de canción no válido para reproducción de Spotify, intentando con otra pregunta")
                    QTimer.singleShot(1000, self.show_next_question)
                    return
                    
            elif self.music_origin == 'online':
                # Usar el reproductor online (anteriormente listenbrainz)
                if hasattr(self, 'listenbrainz_container') and self.listenbrainz_container:
                    self.listenbrainz_container.show()
                    
                if self.current_song_id is not None:
                    # Añadir un delay para dar tiempo a la carga del reproductor
                    QTimer.singleShot(2000, lambda: self._play_online_track())
                else:
                    logger.error("ID de canción no válido para reproducción online, intentando con otra pregunta")
                    QTimer.singleShot(1000, self.show_next_question)
                    return
            else:
                # Reproducción local tradicional
                if len(correct_song) > 4 and correct_song[4]:
                    self.current_song_path = correct_song[4]  # Ruta del archivo local
                else:
                    raise Exception("No hay ruta de archivo disponible para esta canción")
                
                # Verificar que la ruta del archivo exista
                if not os.path.exists(self.current_song_path):
                    print(f"Error: El archivo de audio no existe: {self.current_song_path}")
                    raise FileNotFoundError(f"Archivo de audio no encontrado: {self.current_song_path}")
                    
                # Añadir un delay para dar tiempo a la carga del reproductor
                QTimer.singleShot(1500, lambda: self._play_local_track())
                
        except Exception as e:
            print(f"Error al reproducir la canción: {e}")
            import traceback
            traceback.print_exc()
            # Intentar con la siguiente pregunta si hay error
            QTimer.singleShot(500, self.show_next_question)
            return

    def _play_online_track(self):
        """Método auxiliar para reproducir canción online después del delay inicial."""
        try:
            if not hasattr(self, 'listenbrainz_player') or not self.current_song_id:
                raise Exception("Reproductor online no disponible o ID de canción no válido")
            
            # Configurar el reproductor para la duración del quiz
            self.listenbrainz_player.set_playback_duration(self.song_duration_seconds)
            
            # Actualizar la interfaz
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setValue(50)
            
            # Intentar reproducir la canción
            success = self.listenbrainz_player.play(self.current_song_id)
            
            if success:
                # Configurar el temporizador para la cuenta regresiva
                self.remaining_time = self.song_duration_seconds
                self.countdown_label.setText(str(self.remaining_time))
                self.progress_bar.setValue(100)
                
                # Iniciar la cuenta regresiva
                self.timer.start()
            else:
                raise Exception("No se pudo reproducir la canción online")
                
        except Exception as e:
            print(f"Error al reproducir canción online: {e}")
            import traceback
            traceback.print_exc()
            
            # Intentar con la siguiente pregunta si hay error
            QTimer.singleShot(1000, self.show_next_question)

    def _play_with_listenbrainz_playlist(self, song_ids):
        """Método auxiliar para reproducir con ListenBrainz usando playlist."""
        try:
            if not hasattr(self, 'listenbrainz_player') or not self.current_song_id:
                raise Exception("Reproductor online no disponible o ID de canción no válido")
            
            # Configurar el reproductor para la duración del quiz
            self.listenbrainz_player.set_playback_duration(self.song_duration_seconds)
            
            # Actualizar la interfaz
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setValue(30)
            
            # Intentar crear una playlist con todas las canciones
            urls = self.listenbrainz_player.get_playlist_for_quiz(song_ids)
            
            # Si hay al menos una URL, intentar usar playlist
            if urls:
                # Buscar la URL correcta
                correct_url = None
                success = False
                
                # Obtener la URL de la canción correcta
                correct_url = self.listenbrainz_player.get_listenbrainz_preview_url(self.current_song_id)
                
                if correct_url and correct_url in urls:
                    # Mover la URL correcta al principio para reproducirla primero
                    urls.remove(correct_url)
                    urls.insert(0, correct_url)
                    
                # Crear la playlist con las URLs disponibles
                if len(urls) > 0:
                    success = self.listenbrainz_player.create_playlist(urls)
                    if success:
                        # Configurar el temporizador para la cuenta regresiva
                        self.remaining_time = self.song_duration_seconds
                        self.countdown_label.setText(str(self.remaining_time))
                        self.progress_bar.setValue(100)
                        
                        # Iniciar la cuenta regresiva
                        self.timer.start()
                        return
            
            # Si no se pudo usar playlist, intentar reproducir solo la canción correcta
            success = self.listenbrainz_player.play(self.current_song_id)
            
            if success:
                # Configurar el temporizador para la cuenta regresiva
                self.remaining_time = self.song_duration_seconds
                self.countdown_label.setText(str(self.remaining_time))
                self.progress_bar.setValue(100)
                
                # Iniciar la cuenta regresiva
                self.timer.start()
            else:
                raise Exception("No se pudo reproducir la canción online")
                
        except Exception as e:
            print(f"Error al reproducir online: {e}")
            import traceback
            traceback.print_exc()
            
            # Intentar con reproducción local como fallback
            if hasattr(self, 'current_song') and len(self.current_song) > 4 and self.current_song[4]:
                self.current_song_path = self.current_song[4]
                if os.path.exists(self.current_song_path):
                    self._play_local_track()
                    return
            
            # Si todo falla, pasar a la siguiente pregunta
            QTimer.singleShot(1000, self.show_next_question)

    def _get_song_playable_urls(self, song_id):
        """Obtiene URLs reproducibles para una canción desde la tabla song_links."""
        try:
            if not song_id:
                return []
                
            # Consulta para obtener enlaces reproducibles
            self.cursor.execute("""
                SELECT youtube_url, bandcamp_url, soundcloud_url, spotify_url
                FROM song_links
                WHERE song_id = ?
            """, (song_id,))
            
            result = self.cursor.fetchone()
            
            if not result:
                return []
                
            # Recopilar URLs disponibles en orden de preferencia
            urls = []
            youtube_url, bandcamp_url, soundcloud_url, spotify_url = result
            
            # Añadir URLs en orden de preferencia (puedes cambiar este orden)
            if youtube_url:
                urls.append(youtube_url)
            if bandcamp_url:
                urls.append(bandcamp_url)
            if soundcloud_url:
                urls.append(soundcloud_url)
            if spotify_url:
                urls.append(spotify_url)
                
            return urls
            
        except Exception as e:
            print(f"Error al obtener URLs reproducibles: {e}")
            return []




    def check_playback_started(self):
        """Verifica si la reproducción ha comenzado correctamente."""
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            print("Error: No se pudo iniciar la reproducción")
            # Intentar reproducir de nuevo
            self.player.play()
            
            # Si sigue sin funcionar después de otro intento, pasar a la siguiente pregunta
            QTimer.singleShot(1000, lambda: self.check_if_still_not_playing())

    def check_if_still_not_playing(self):
        """Comprueba si la canción sigue sin reproducirse después de un segundo intento."""
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            print("Error persistente: La canción no se puede reproducir después de varios intentos")
            QTimer.singleShot(500, self.show_next_question)



    def update_countdown(self):
        """Actualiza la cuenta atrás y el progreso."""
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.countdown_label.setText(str(self.remaining_time))
            
            # Actualizar barra de progreso
            progress_value = (self.remaining_time / self.song_duration_seconds) * 100
            self.progress_bar.setValue(int(progress_value))
            
            # Si hay poco tiempo, cambiar el color
            if self.remaining_time <= 5:
                self.countdown_label.setStyleSheet("color: red;")
            else:
                self.countdown_label.setStyleSheet("")
        else:
            # Se acabó el tiempo
            self.timer.stop()
            
            # Marcar como incorrecto (sin respuesta)
            self.total_played += 1
            self.update_stats_display()
            
            # Resaltar la opción correcta
            self.option_buttons[self.current_correct_option].setStyleSheet("background-color: green;")
            
            # Deshabilitar opciones
            self.enable_options(False)
            
            # Pausa antes de la siguiente pregunta
            QTimer.singleShot(self.pause_between_songs * 1000, self.show_next_question)

    def on_option_selected(self):
        """Maneja la selección de una opción por parte del usuario."""
        if not self.game_active:
            return
            
        # Obtener el botón que se presionó
        button = self.sender()
        selected_option = button.property("option_id")
        
        # Detener el timer
        self.timer.stop()
        
        # Actualizar estadísticas
        self.total_played += 1
        if selected_option == self.current_correct_option:
            self.score += 1
            button.setStyleSheet("background-color: green;")
        else:
            button.setStyleSheet("background-color: red;")
            # Mostrar la opción correcta
            self.option_buttons[self.current_correct_option].setStyleSheet("background-color: green;")
        
        self.update_stats_display()
        
        # Deshabilitar opciones
        self.enable_options(False)
        
        # Pausa antes de la siguiente pregunta
        QTimer.singleShot(self.pause_between_songs * 1000, self.show_next_question)

    def update_stats_display(self):
        """Actualiza los labels de estadísticas."""
        self.score_label.setText(f"Aciertos: {self.score}")
        self.total_label.setText(f"Total: {self.total_played}")
        
        accuracy = 0 if self.total_played == 0 else (self.score / self.total_played) * 100
        self.accuracy_label.setText(f"Precisión: {accuracy:.1f}%")

    def enable_options(self, enabled):
        """Habilita o deshabilita las opciones de respuesta."""
        for button in self.option_buttons:
            button.setEnabled(enabled)

    def show_error_message(self, title, message):
        """Muestra un mensaje de error."""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()
    
    def closeEvent(self, event):
        """Limpia los recursos al cerrar el módulo."""
        self.save_config()
        self.stop_quiz()
        if self.conn:
            self.conn.close()
        if hasattr(self, 'spotify_player'):
            self.spotify_player.close()
        if hasattr(self, 'listenbrainz_player'):
            self.listenbrainz_player.close()
        super().closeEvent(event)


    def show_artist_filter_dialog(self):
        """Muestra un diálogo para filtrar artistas con información de álbumes y sellos."""
        try:
            dialog = QDialog(self)
            
            # Cargar la UI del diálogo
            dialog_ui_path = Path(PROJECT_ROOT, "ui", "jaangle", "jaangle_artist_filter_dialog.ui")
            
            if os.path.exists(dialog_ui_path):
                from PyQt6 import uic
                uic.loadUi(dialog_ui_path, dialog)
                
                # Obtener referencias a los widgets
                table = dialog.findChild(QTableWidget, "artists_table")
                search_edit = dialog.findChild(QLineEdit, "search_edit")
                select_all_btn = dialog.findChild(QPushButton, "select_all_btn")
                deselect_all_btn = dialog.findChild(QPushButton, "deselect_all_btn")
                save_btn = dialog.findChild(QPushButton, "save_btn")
                cancel_btn = dialog.findChild(QPushButton, "cancel_btn")
            
                # Obtener la lista de artistas
                self.cursor.execute("SELECT id, name FROM artists ORDER BY name")
                artists = self.cursor.fetchall()
                
                # Obtener artistas excluidos
                excluded_artists = self.get_excluded_items("excluded_artists")
                
                # Configurar el número de filas de la tabla
                table.setRowCount(len(artists))
                
                # Diccionario para mantener referencia a los checkboxes
                checkboxes = {}
                
                # Llenar la tabla con datos
                for row, (artist_id, artist_name) in enumerate(artists):
                    # Crear widget para checkbox del artista
                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout(checkbox_widget)
                    checkbox_layout.setContentsMargins(5, 0, 0, 0)
                    checkbox = QCheckBox(artist_name)
                    checkbox.setChecked(artist_name in excluded_artists)
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.addStretch()
                    
                    # Guardar referencia al checkbox
                    checkboxes[artist_name] = checkbox
                    
                    # Añadir el widget con checkbox a la tabla
                    table.setCellWidget(row, 0, checkbox_widget)
                    
                    # Obtener álbumes del artista
                    self.cursor.execute("""
                        SELECT name FROM albums 
                        WHERE artist_id = ? 
                        ORDER BY year DESC, name
                    """, (artist_id,))
                    albums = self.cursor.fetchall()
                    albums_text = ", ".join([album[0] for album in albums])
                    
                    # Añadir álbumes a la segunda columna
                    albums_item = QTableWidgetItem(albums_text)
                    albums_item.setFlags(albums_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 1, albums_item)
                    
                    # Obtener sellos discográficos del artista
                    self.cursor.execute("""
                        SELECT DISTINCT label FROM albums 
                        WHERE artist_id = ? AND label IS NOT NULL AND label != ''
                        ORDER BY label
                    """, (artist_id,))
                    labels = self.cursor.fetchall()
                    labels_text = ", ".join([label[0] for label in labels])
                    
                    # Añadir sellos a la tercera columna
                    labels_item = QTableWidgetItem(labels_text)
                    labels_item.setFlags(labels_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 2, labels_item)
                
                # Función para filtrar la tabla según el texto de búsqueda
                def filter_table(text):
                    text = text.lower()
                    for row in range(table.rowCount()):
                        artist_widget = table.cellWidget(row, 0)
                        if artist_widget:
                            checkbox = artist_widget.layout().itemAt(0).widget()
                            artist_name = checkbox.text()
                            
                            # También buscar en álbumes y sellos
                            albums_text = table.item(row, 1).text().lower() if table.item(row, 1) else ""
                            labels_text = table.item(row, 2).text().lower() if table.item(row, 2) else ""
                            
                            visible = (text in artist_name.lower() or 
                                    text in albums_text or 
                                    text in labels_text)
                            
                            table.setRowHidden(row, not visible)
                
                # Conectar señales
                search_edit.textChanged.connect(filter_table)
                
                def select_all():
                    for row in range(table.rowCount()):
                        if not table.isRowHidden(row):
                            widget = table.cellWidget(row, 0)
                            if widget:
                                checkbox = widget.layout().itemAt(0).widget()
                                checkbox.setChecked(True)
                
                def deselect_all():
                    for row in range(table.rowCount()):
                        if not table.isRowHidden(row):
                            widget = table.cellWidget(row, 0)
                            if widget:
                                checkbox = widget.layout().itemAt(0).widget()
                                checkbox.setChecked(False)
                
                def save_changes():
                    excluded = []
                    for artist_name, checkbox in checkboxes.items():
                        if checkbox.isChecked():
                            excluded.append(artist_name)
                    self.save_excluded_items("excluded_artists", excluded)
                    dialog.accept()
                  
                # Conectar botones
                select_all_btn.clicked.connect(select_all)
                deselect_all_btn.clicked.connect(deselect_all)
                save_btn.clicked.connect(save_changes)
                cancel_btn.clicked.connect(dialog.reject)
            
            else:
                raise FileNotFoundError(f"No se encontró el archivo UI: {dialog_ui_path}")

            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar artistas: {e}")
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")

    def save_excluded_items(self, item_type, excluded_items):
        """
        Guarda los elementos excluidos en la base de datos.
        Los elementos excluidos tendrán jaangle_ready=0, los incluidos jaangle_ready=1.
        
        Args:
            item_type: Tipo de elementos ("excluded_artists", "excluded_albums", etc.)
            excluded_items: Lista de IDs o nombres de elementos a excluir
            
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario
        """
        try:
            if not hasattr(self, 'db_path') or not self.db_path:
                print("Error: No database path configured")
                return False
                
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Determinar la tabla según el tipo de elemento
            if item_type == "excluded_artists":
                table_name = "artists"
            elif item_type == "excluded_albums":
                table_name = "albums"
            else:
                print(f"Unsupported item type: {item_type}")
                return False
            
            # Verificar si la tabla existe
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                print(f"{table_name} table does not exist, creating it")
                
                if table_name == "artists":
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS artists (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        bio TEXT,
                        tags TEXT,
                        jaangle_ready BOOLEAN DEFAULT 1,
                        lastfm_url TEXT,
                        spotify_url TEXT,
                        mbid TEXT,
                        origin TEXT,
                        last_updated TIMESTAMP
                    )
                    """)
                    # Crear índice para búsqueda eficiente
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name)")
                elif table_name == "albums":
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS albums (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        artist_id INTEGER,
                        year INTEGER,
                        jaangle_ready BOOLEAN DEFAULT 1,
                        lastfm_url TEXT,
                        spotify_url TEXT,
                        mbid TEXT,
                        last_updated TIMESTAMP,
                        FOREIGN KEY (artist_id) REFERENCES artists(id)
                    )
                    """)
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_name ON albums(name)")
            
            # Verificar si la columna jaangle_ready existe
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'jaangle_ready' not in columns:
                print(f"Adding jaangle_ready column to {table_name} table")
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN jaangle_ready BOOLEAN DEFAULT 1")
            
            # Iniciar transacción
            conn.execute("BEGIN TRANSACTION")
            
            # NUEVO ENFOQUE: Primero actualizamos TODOS los elementos a jaangle_ready=1
            cursor.execute(f"UPDATE {table_name} SET jaangle_ready = 1")
            print(f"Reset all items in {table_name} to jaangle_ready=1")
            
            # Si no hay elementos excluidos, simplemente dejamos todo marcado como incluido
            if not excluded_items:
                print(f"No {item_type} to exclude, all items marked as ready")
                conn.commit()
                conn.close()
                return True
            
            # Ahora actualizamos solo los elementos excluidos a jaangle_ready=0
            excluded_count = 0
            
            # Determinar si los elementos excluidos son IDs o nombres
            is_id_list = all(isinstance(item, int) or (isinstance(item, str) and item.isdigit()) for item in excluded_items)
            
            if is_id_list:
                # Convertir a lista de strings para la consulta SQL
                id_list = ",".join(str(id) for id in excluded_items)
                
                if id_list:  # Asegurarse de que no esté vacía
                    # Actualizar por ID
                    cursor.execute(f"""
                    UPDATE {table_name} 
                    SET jaangle_ready = 0 
                    WHERE id IN ({id_list})
                    """)
                    
                    excluded_count = cursor.rowcount
            else:
                # Actualizar por nombre (uno por uno para evitar problemas con comillas)
                for item_name in excluded_items:
                    cursor.execute(f"""
                    UPDATE {table_name} 
                    SET jaangle_ready = 0 
                    WHERE LOWER(name) = LOWER(?)
                    """, (item_name,))
                    
                    excluded_count += cursor.rowcount
                    
                    # Si no se actualizó ninguna fila, el elemento no existe, así que lo insertamos
                    if cursor.rowcount == 0:
                        if table_name == "artists":
                            cursor.execute("""
                            INSERT INTO artists (name, jaangle_ready)
                            VALUES (?, 0)
                            """, (item_name,))
                        elif table_name == "albums":
                            cursor.execute("""
                            INSERT INTO albums (name, jaangle_ready)
                            VALUES (?, 0)
                            """, (item_name,))
                        
                        excluded_count += 1
            
            # Guardar cambios
            conn.commit()
            conn.close()
            
            print(f"Successfully marked {excluded_count} {item_type} as excluded (jaangle_ready=0)")
            return True
            
        except Exception as e:
            print(f"Error saving excluded items: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            # Intentar hacer rollback si es posible
            try:
                if conn:
                    conn.rollback()
                    conn.close()
            except:
                pass
                
            return False


    def get_excluded_artists(self):
        """
        Retrieve a list of artists marked as not ready for processing.
        
        Returns:
            list: Names of artists not ready for processing
        """
        try:
            import sqlite3
            
            # Verify database path
            if not hasattr(self, 'db_path') or not self.db_path:
                #print("Error: No database path configured")
                return []
            
            # Connect to the database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if artists table and jaangle_ready column exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artists'")
            if not cursor.fetchone():
                #print("Error: Artists table does not exist")
                conn.close()
                return []
            
            # Check if jaangle_ready column exists
            try:
                cursor.execute("SELECT jaangle_ready FROM artists LIMIT 1")
            except sqlite3.OperationalError:
                # Column does not exist
                conn.close()
                return []
            
            # Fetch excluded artists
            cursor.execute("SELECT name FROM artists WHERE jaangle_ready = 0 OR jaangle_ready IS NULL")
            excluded_artists = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            return excluded_artists
        
        except Exception as e:
            #print(f"Error retrieving excluded artists: {str(e)}")
            import traceback
            #print(traceback.format_exc())
            
            return []

    def show_album_filter_dialog(self):
        """Muestra un diálogo para filtrar álbumes con información de artista, sello y año."""
        try:
            dialog = QDialog(self)
            
            # Cargar la UI del diálogo
            dialog_ui_path = Path(PROJECT_ROOT, "ui", "jaangle", "jaangle_album_filter_dialog.ui")
            
            if os.path.exists(dialog_ui_path):
                from PyQt6 import uic
                uic.loadUi(dialog_ui_path, dialog)
                
                # Obtener referencias a los widgets
                table = dialog.findChild(QTableWidget, "artists_table")
                search_edit = dialog.findChild(QLineEdit, "search_edit")
                select_all_btn = dialog.findChild(QPushButton, "select_all_btn")
                deselect_all_btn = dialog.findChild(QPushButton, "deselect_all_btn")
                save_btn = dialog.findChild(QPushButton, "save_btn")
                cancel_btn = dialog.findChild(QPushButton, "cancel_btn")
                dialog.setWindowTitle("Filtrar Álbumes")
                dialog.setMinimumWidth(700)
                dialog.setMinimumHeight(500)
                
                layout = QVBoxLayout()
                
                # Añadir un buscador
                search_layout = QHBoxLayout()
                search_label = QLabel("Buscar:")
                search_edit = QLineEdit()
                search_edit.setPlaceholderText("Escribe para filtrar...")
                search_layout.addWidget(search_label)
                search_layout.addWidget(search_edit)
                layout.addLayout(search_layout)
                
                # Crear un widget de tabla para mostrar álbumes, artistas, sellos y años
                table = QTableWidget()
                table.setColumnCount(4)
                table.setHorizontalHeaderLabels(["Álbum", "Artista", "Sello", "Año"])
                table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
                table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
                table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
                table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
                
                # Obtener la lista de álbumes con información adicional
                self.cursor.execute("""
                    SELECT a.id, a.name, ar.name, a.label, a.year
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    ORDER BY a.name
                """)
                albums = self.cursor.fetchall()
                
                # Obtener álbumes excluidos
                excluded_albums = self.get_excluded_items("excluded_albums")
                
                # Configurar el número de filas de la tabla
                table.setRowCount(len(albums))
                
                # Diccionario para mantener referencia a los checkboxes
                checkboxes = {}
                
                # Llenar la tabla con datos
                for row, (album_id, album_name, artist_name, label, year) in enumerate(albums):
                    # Crear widget para checkbox del álbum
                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout(checkbox_widget)
                    checkbox_layout.setContentsMargins(5, 0, 0, 0)
                    checkbox = QCheckBox(album_name)
                    checkbox.setChecked(album_name in excluded_albums)
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.addStretch()
                    
                    # Guardar referencia al checkbox
                    checkboxes[album_name] = checkbox
                    
                    # Añadir el widget con checkbox a la tabla
                    table.setCellWidget(row, 0, checkbox_widget)
                    
                    # Añadir información del artista
                    artist_item = QTableWidgetItem(artist_name or "")
                    artist_item.setFlags(artist_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 1, artist_item)
                    
                    # Añadir información del sello
                    label_item = QTableWidgetItem(label or "")
                    label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 2, label_item)
                    
                    # Añadir información del año
                    year_item = QTableWidgetItem(year or "")
                    year_item.setFlags(year_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 3, year_item)
                
                layout.addWidget(table)
                
                # Función para filtrar la tabla según el texto de búsqueda
                def filter_table(text):
                    text = text.lower()
                    for row in range(table.rowCount()):
                        album_widget = table.cellWidget(row, 0)
                        if album_widget:
                            checkbox = album_widget.layout().itemAt(0).widget()
                            album_name = checkbox.text().lower()
                            
                            artist_text = table.item(row, 1).text().lower() if table.item(row, 1) else ""
                            label_text = table.item(row, 2).text().lower() if table.item(row, 2) else ""
                            year_text = table.item(row, 3).text().lower() if table.item(row, 3) else ""
                            
                            visible = (text in album_name or 
                                    text in artist_text or 
                                    text in label_text or 
                                    text in year_text)
                            
                            table.setRowHidden(row, not visible)
                
                search_edit.textChanged.connect(filter_table)
                
                # Botones
                buttons_layout = QHBoxLayout()
                select_all_btn = QPushButton("Seleccionar Todos")
                deselect_all_btn = QPushButton("Deseleccionar Todos")
                save_btn = QPushButton("Guardar")
                cancel_btn = QPushButton("Cancelar")
                
                buttons_layout.addWidget(select_all_btn)
                buttons_layout.addWidget(deselect_all_btn)
                buttons_layout.addWidget(save_btn)
                buttons_layout.addWidget(cancel_btn)
                
                layout.addLayout(buttons_layout)
                dialog.setLayout(layout)
                
                # Conectar señales
                def select_all():
                    for row in range(table.rowCount()):
                        if not table.isRowHidden(row):
                            widget = table.cellWidget(row, 0)
                            if widget:
                                checkbox = widget.layout().itemAt(0).widget()
                                checkbox.setChecked(True)
                
                def deselect_all():
                    for row in range(table.rowCount()):
                        if not table.isRowHidden(row):
                            widget = table.cellWidget(row, 0)
                            if widget:
                                checkbox = widget.layout().itemAt(0).widget()
                                checkbox.setChecked(False)
                
                def save_changes():
                    excluded = []
                    for album_name, checkbox in checkboxes.items():
                        if checkbox.isChecked():
                            excluded.append(album_name)
                    self.save_excluded_items("excluded_albums", excluded)
                    dialog.accept()
                
                select_all_btn.clicked.connect(select_all)
                deselect_all_btn.clicked.connect(deselect_all)
                save_btn.clicked.connect(save_changes)
                cancel_btn.clicked.connect(dialog.reject)
            
            else:
                raise FileNotFoundError(f"No se encontró el archivo UI: {dialog_ui_path}")

            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar álbumes: {e}")
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")





    def show_genre_filter_dialog(self):
        """Muestra un diálogo para filtrar géneros con información de artistas y sellos."""
        try:
            dialog = QDialog(self)
            
            # Cargar la UI del diálogo
            dialog_ui_path = Path(PROJECT_ROOT, "ui", "jaangle", "jaangle_genre_filter_dialog.ui")
            
            if os.path.exists(dialog_ui_path):
                from PyQt6 import uic
                uic.loadUi(dialog_ui_path, dialog)
                
                # Obtener referencias a los widgets
                table = dialog.findChild(QTableWidget, "artists_table")
                search_edit = dialog.findChild(QLineEdit, "search_edit")
                select_all_btn = dialog.findChild(QPushButton, "select_all_btn")
                deselect_all_btn = dialog.findChild(QPushButton, "deselect_all_btn")
                save_btn = dialog.findChild(QPushButton, "save_btn")
                cancel_btn = dialog.findChild(QPushButton, "cancel_btn")
            
                dialog.setWindowTitle("Filtrar Géneros")
                dialog.setMinimumWidth(700)
                dialog.setMinimumHeight(500)
                
                layout = QVBoxLayout()
                
                # Añadir un buscador
                search_layout = QHBoxLayout()
                search_label = QLabel("Buscar:")
                search_edit = QLineEdit()
                search_edit.setPlaceholderText("Escribe para filtrar...")
                search_layout.addWidget(search_label)
                search_layout.addWidget(search_edit)
                layout.addLayout(search_layout)
                
                # Crear un widget de tabla para mostrar géneros, artistas y sellos
                table = QTableWidget()
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["Género", "Artistas", "Sellos"])
                table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
                
                # Obtener la lista de géneros
                self.cursor.execute("SELECT DISTINCT genre FROM songs WHERE genre IS NOT NULL AND genre != '' ORDER BY genre")
                genres = self.cursor.fetchall()
                
                # Obtener géneros excluidos
                excluded_genres = self.get_excluded_items("excluded_genres")
                
                # Configurar el número de filas de la tabla
                table.setRowCount(len(genres))
                
                # Diccionario para mantener referencia a los checkboxes
                checkboxes = {}
                
                # Llenar la tabla con datos
                for row, (genre,) in enumerate(genres):
                    # Crear widget para checkbox del género
                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout(checkbox_widget)
                    checkbox_layout.setContentsMargins(5, 0, 0, 0)
                    checkbox = QCheckBox(genre)
                    checkbox.setChecked(genre in excluded_genres)
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.addStretch()
                    
                    # Guardar referencia al checkbox
                    checkboxes[genre] = checkbox
                    
                    # Añadir el widget con checkbox a la tabla
                    table.setCellWidget(row, 0, checkbox_widget)
                    
                    # Obtener artistas de este género
                    self.cursor.execute("""
                        SELECT DISTINCT artist 
                        FROM songs 
                        WHERE genre = ? 
                        ORDER BY artist
                    """, (genre,))
                    artists = self.cursor.fetchall()
                    artists_text = ", ".join([artist[0] for artist in artists[:10]])
                    if len(artists) > 10:
                        artists_text += f"... (+{len(artists) - 10} más)"
                    
                    # Añadir artistas a la segunda columna
                    artists_item = QTableWidgetItem(artists_text)
                    artists_item.setFlags(artists_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 1, artists_item)
                    
                    # Obtener sellos de este género
                    self.cursor.execute("""
                        SELECT DISTINCT label 
                        FROM songs 
                        WHERE genre = ? AND label IS NOT NULL AND label != '' 
                        ORDER BY label
                    """, (genre,))
                    labels = self.cursor.fetchall()
                    labels_text = ", ".join([label[0] for label in labels[:10]])
                    if len(labels) > 10:
                        labels_text += f"... (+{len(labels) - 10} más)"
                    
                    # Añadir sellos a la tercera columna
                    labels_item = QTableWidgetItem(labels_text)
                    labels_item.setFlags(labels_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 2, labels_item)
                
                layout.addWidget(table)
                
                # Función para filtrar la tabla según el texto de búsqueda
                def filter_table(text):
                    text = text.lower()
                    for row in range(table.rowCount()):
                        genre_widget = table.cellWidget(row, 0)
                        if genre_widget:
                            checkbox = genre_widget.layout().itemAt(0).widget()
                            genre_name = checkbox.text().lower()
                            
                            artists_text = table.item(row, 1).text().lower() if table.item(row, 1) else ""
                            labels_text = table.item(row, 2).text().lower() if table.item(row, 2) else ""
                            
                            visible = (text in genre_name or 
                                    text in artists_text or 
                                    text in labels_text)
                            
                            table.setRowHidden(row, not visible)
                
                search_edit.textChanged.connect(filter_table)
                
                # Botones
                buttons_layout = QHBoxLayout()
                select_all_btn = QPushButton("Seleccionar Todos")
                deselect_all_btn = QPushButton("Deseleccionar Todos")
                save_btn = QPushButton("Guardar")
                cancel_btn = QPushButton("Cancelar")
                
                buttons_layout.addWidget(select_all_btn)
                buttons_layout.addWidget(deselect_all_btn)
                buttons_layout.addWidget(save_btn)
                buttons_layout.addWidget(cancel_btn)
                
                layout.addLayout(buttons_layout)
                dialog.setLayout(layout)
                
                # Conectar señales
                def select_all():
                    for row in range(table.rowCount()):
                        if not table.isRowHidden(row):
                            widget = table.cellWidget(row, 0)
                            if widget:
                                checkbox = widget.layout().itemAt(0).widget()
                                checkbox.setChecked(True)
                
                def deselect_all():
                    for row in range(table.rowCount()):
                        if not table.isRowHidden(row):
                            widget = table.cellWidget(row, 0)
                            if widget:
                                checkbox = widget.layout().itemAt(0).widget()
                                checkbox.setChecked(False)
                
                def save_changes():
                    excluded = []
                    for genre_name, checkbox in checkboxes.items():
                        if checkbox.isChecked():
                            excluded.append(genre_name)
                    self.save_excluded_items("excluded_genres", excluded)
                    dialog.accept()
                
                select_all_btn.clicked.connect(select_all)
                deselect_all_btn.clicked.connect(deselect_all)
                save_btn.clicked.connect(save_changes)
                cancel_btn.clicked.connect(dialog.reject)

            else:
                raise FileNotFoundError(f"No se encontró el archivo UI: {dialog_ui_path}")

            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar géneros: {e}")
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")


    def show_sellos_filter_dialog(self):
        """Muestra un diálogo para filtrar por sellos discográficos con información de artistas y álbumes."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar por Sellos Discográficos")
            dialog.setMinimumWidth(700)
            dialog.setMinimumHeight(500)
            
            layout = QVBoxLayout()
            
            # Añadir un buscador
            search_layout = QHBoxLayout()
            search_label = QLabel("Buscar:")
            search_edit = QLineEdit()
            search_edit.setPlaceholderText("Escribe para filtrar...")
            search_layout.addWidget(search_label)
            search_layout.addWidget(search_edit)
            layout.addLayout(search_layout)
            
            # Crear pestañas para filtros positivos y negativos
            tabs = QTabWidget()
            
            # Crear widgets para ambas pestañas
            include_tab = QWidget()
            exclude_tab = QWidget()
            
            include_layout = QVBoxLayout(include_tab)
            exclude_layout = QVBoxLayout(exclude_tab)
            
            # Crear tablas para ambas pestañas
            include_table = QTableWidget()
            exclude_table = QTableWidget()
            
            for table in [include_table, exclude_table]:
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["Sello", "Artistas", "Álbumes"])
                table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            
            # Obtener la lista de sellos
            self.cursor.execute("""
                SELECT DISTINCT label 
                FROM albums 
                WHERE label IS NOT NULL AND label != '' 
                ORDER BY label
            """)
            labels = self.cursor.fetchall()
            
            # Obtener sellos incluidos y excluidos
            included_labels = self.get_included_items("included_labels")
            excluded_labels = self.get_excluded_items("excluded_labels")
            
            # Configurar el número de filas de las tablas
            include_table.setRowCount(len(labels))
            exclude_table.setRowCount(len(labels))
            
            # Diccionarios para mantener referencia a los checkboxes
            include_checkboxes = {}
            exclude_checkboxes = {}
            
            # Llenar las tablas con datos
            for row, (label,) in enumerate(labels):
                # Tabla de inclusión
                include_checkbox_widget = QWidget()
                include_checkbox_layout = QHBoxLayout(include_checkbox_widget)
                include_checkbox_layout.setContentsMargins(5, 0, 0, 0)
                include_checkbox = QCheckBox(label)
                include_checkbox.setChecked(label in included_labels)
                include_checkbox_layout.addWidget(include_checkbox)
                include_checkbox_layout.addStretch()
                
                include_checkboxes[label] = include_checkbox
                include_table.setCellWidget(row, 0, include_checkbox_widget)
                
                # Tabla de exclusión
                exclude_checkbox_widget = QWidget()
                exclude_checkbox_layout = QHBoxLayout(exclude_checkbox_widget)
                exclude_checkbox_layout.setContentsMargins(5, 0, 0, 0)
                exclude_checkbox = QCheckBox(label)
                exclude_checkbox.setChecked(label in excluded_labels)
                exclude_checkbox_layout.addWidget(exclude_checkbox)
                exclude_checkbox_layout.addStretch()
                
                exclude_checkboxes[label] = exclude_checkbox
                exclude_table.setCellWidget(row, 0, exclude_checkbox_widget)
                
                # Obtener artistas de este sello
                self.cursor.execute("""
                    SELECT DISTINCT ar.name 
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.label = ? 
                    ORDER BY ar.name
                """, (label,))
                artists = self.cursor.fetchall()
                artists_text = ", ".join([artist[0] for artist in artists[:10]])
                if len(artists) > 10:
                    artists_text += f"... (+{len(artists) - 10} más)"
                
                # Añadir artistas a ambas tablas
                artists_item_include = QTableWidgetItem(artists_text)
                artists_item_include.setFlags(artists_item_include.flags() & ~Qt.ItemFlag.ItemIsEditable)
                include_table.setItem(row, 1, artists_item_include)
                
                artists_item_exclude = QTableWidgetItem(artists_text)
                artists_item_exclude.setFlags(artists_item_exclude.flags() & ~Qt.ItemFlag.ItemIsEditable)
                exclude_table.setItem(row, 1, artists_item_exclude)
                
                # Obtener álbumes de este sello
                self.cursor.execute("""
                    SELECT name 
                    FROM albums 
                    WHERE label = ? 
                    ORDER BY year DESC, name
                """, (label,))
                albums = self.cursor.fetchall()
                albums_text = ", ".join([album[0] for album in albums[:10]])
                if len(albums) > 10:
                    albums_text += f"... (+{len(albums) - 10} más)"
                
                # Añadir álbumes a ambas tablas
                albums_item_include = QTableWidgetItem(albums_text)
                albums_item_include.setFlags(albums_item_include.flags() & ~Qt.ItemFlag.ItemIsEditable)
                include_table.setItem(row, 2, albums_item_include)
                
                albums_item_exclude = QTableWidgetItem(albums_text)
                albums_item_exclude.setFlags(albums_item_exclude.flags() & ~Qt.ItemFlag.ItemIsEditable)
                exclude_table.setItem(row, 2, albums_item_exclude)
            
            # Añadir tablas a los layouts
            include_layout.addWidget(include_table)
            exclude_layout.addWidget(exclude_table)
            
            # Añadir pestañas al widget
            tabs.addTab(include_tab, "Incluir Sellos")
            tabs.addTab(exclude_tab, "Excluir Sellos")
            layout.addWidget(tabs)
            
            # Funciones para filtrar las tablas
            def filter_include_table(text):
                text = text.lower()
                for row in range(include_table.rowCount()):
                    label_widget = include_table.cellWidget(row, 0)
                    if label_widget:
                        checkbox = label_widget.layout().itemAt(0).widget()
                        label_name = checkbox.text().lower()
                        
                        artists_text = include_table.item(row, 1).text().lower() if include_table.item(row, 1) else ""
                        albums_text = include_table.item(row, 2).text().lower() if include_table.item(row, 2) else ""
                        
                        visible = (text in label_name or 
                                text in artists_text or 
                                text in albums_text)
                        
                        include_table.setRowHidden(row, not visible)
            
            def filter_exclude_table(text):
                text = text.lower()
                for row in range(exclude_table.rowCount()):
                    label_widget = exclude_table.cellWidget(row, 0)
                    if label_widget:
                        checkbox = label_widget.layout().itemAt(0).widget()
                        label_name = checkbox.text().lower()
                        
                        artists_text = exclude_table.item(row, 1).text().lower() if exclude_table.item(row, 1) else ""
                        albums_text = exclude_table.item(row, 2).text().lower() if exclude_table.item(row, 2) else ""
                        
                        visible = (text in label_name or 
                                text in artists_text or 
                                text in albums_text)
                        
                        exclude_table.setRowHidden(row, not visible)
            
            def filter_tables(text):
                current_index = tabs.currentIndex()
                if current_index == 0:
                    filter_include_table(text)
                else:
                    filter_exclude_table(text)
            
            search_edit.textChanged.connect(filter_tables)
            tabs.currentChanged.connect(lambda: filter_tables(search_edit.text()))
            
            # Botones
            buttons_layout = QHBoxLayout()
            select_all_btn = QPushButton("Seleccionar Todos")
            deselect_all_btn = QPushButton("Deseleccionar Todos")
            save_btn = QPushButton("Guardar")
            cancel_btn = QPushButton("Cancelar")
            
            buttons_layout.addWidget(select_all_btn)
            buttons_layout.addWidget(deselect_all_btn)
            buttons_layout.addWidget(save_btn)
            buttons_layout.addWidget(cancel_btn)
            
            layout.addLayout(buttons_layout)
            dialog.setLayout(layout)
            
            # Conectar señales
            for row in range(table.rowCount()):
                    if not table.isRowHidden(row):
                        widget = table.cellWidget(row, 0)
                        if widget:
                            checkbox = widget.layout().itemAt(0).widget()
                            checkbox.setChecked(True)
            
            def deselect_all():
                for row in range(table.rowCount()):
                    if not table.isRowHidden(row):
                        widget = table.cellWidget(row, 0)
                        if widget:
                            checkbox = widget.layout().itemAt(0).widget()
                            checkbox.setChecked(False)
            
            def save_changes():
                excluded = []
                for genre_name, checkbox in checkboxes.items():
                    if checkbox.isChecked():
                        excluded.append(genre_name)
                self.save_excluded_items("excluded_genres", excluded)
                dialog.accept()
            
            select_all_btn.clicked.connect(select_all)
            deselect_all_btn.clicked.connect(deselect_all)
            save_btn.clicked.connect(save_changes)
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar géneros: {e}")
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")


    def show_year_filter_dialog(self):
        """Muestra un diálogo para filtrar años/décadas con información de artistas y álbumes."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar por Año/Década")
            dialog.setMinimumWidth(800)
            dialog.setMinimumHeight(600)
            
            layout = QVBoxLayout()
            
            # Selector de modo: Año o Década
            mode_layout = QHBoxLayout()
            mode_label = QLabel("Filtrar por:")
            mode_combo = QComboBox()
            mode_combo.addItems(["Década", "Año"])
            mode_layout.addWidget(mode_label)
            mode_layout.addWidget(mode_combo)
            layout.addLayout(mode_layout)
            
            # Añadir un buscador
            search_layout = QHBoxLayout()
            search_label = QLabel("Buscar:")
            search_edit = QLineEdit()
            search_edit.setPlaceholderText("Escribe para filtrar...")
            search_layout.addWidget(search_label)
            search_layout.addWidget(search_edit)
            layout.addLayout(search_layout)
            
            # Selector de tipo de filtro
            filter_type_layout = QHBoxLayout()
            filter_type_label = QLabel("Tipo de filtro:")
            filter_type_combo = QComboBox()
            filter_type_combo.addItems(["Incluir (Positivo)", "Excluir (Negativo)"])
            filter_type_layout.addWidget(filter_type_label)
            filter_type_layout.addWidget(filter_type_combo)
            layout.addLayout(filter_type_layout)
            
            # Crear un widget de tabla para mostrar años/décadas, artistas y álbumes
            table = QTableWidget()
            table.setColumnCount(3)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            
            # Función para actualizar la tabla según el modo seleccionado
            def update_table_data():
                if mode_combo.currentText() == "Década":
                    table.setHorizontalHeaderLabels(["Década", "Artistas", "Álbumes"])
                    load_decades_data()
                else:
                    table.setHorizontalHeaderLabels(["Año", "Artistas", "Álbumes"])
                    load_years_data()
            
            # Cargar datos de décadas
            def load_decades_data():
                # Obtener décadas de las canciones
                self.cursor.execute("""
                    SELECT DISTINCT CAST(SUBSTR(album_year, 1, 3) || '0' AS TEXT) AS decade
                    FROM songs 
                    WHERE album_year IS NOT NULL AND album_year != '' AND LENGTH(album_year) >= 4
                    ORDER BY decade
                """)
                decades = self.cursor.fetchall()
                
                # Obtener décadas incluidas o excluidas según el tipo de filtro
                filter_type = "included_decades" if filter_type_combo.currentText() == "Incluir (Positivo)" else "excluded_decades"
                filtered_decades = self.get_excluded_items(filter_type)
                
                # Configurar el número de filas de la tabla
                table.setRowCount(len(decades))
                
                # Diccionario para mantener referencia a los checkboxes
                checkboxes = {}
                
                # Llenar la tabla con datos
                for row, (decade,) in enumerate(decades):
                    # Crear widget para checkbox de la década
                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout(checkbox_widget)
                    checkbox_layout.setContentsMargins(5, 0, 0, 0)
                    checkbox = QCheckBox(f"{decade}s")
                    checkbox.setChecked(decade in filtered_decades)
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.addStretch()
                    
                    # Guardar referencia al checkbox
                    checkboxes[decade] = checkbox
                    
                    # Añadir el widget con checkbox a la tabla
                    table.setCellWidget(row, 0, checkbox_widget)
                    
                    # Obtener artistas de esta década
                    self.cursor.execute("""
                        SELECT DISTINCT artist 
                        FROM songs 
                        WHERE SUBSTR(album_year, 1, 3) || '0' = ? 
                        ORDER BY artist
                    """, (decade,))
                    artists = self.cursor.fetchall()
                    artists_text = ", ".join([artist[0] for artist in artists[:10]])
                    if len(artists) > 10:
                        artists_text += f"... (+{len(artists) - 10} más)"
                    
                    # Añadir artistas a la segunda columna
                    artists_item = QTableWidgetItem(artists_text)
                    artists_item.setFlags(artists_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 1, artists_item)
                    
                    # Obtener álbumes de esta década
                    self.cursor.execute("""
                        SELECT DISTINCT album 
                        FROM songs 
                        WHERE SUBSTR(album_year, 1, 3) || '0' = ? AND album IS NOT NULL AND album != '' 
                        ORDER BY album
                    """, (decade,))
                    albums = self.cursor.fetchall()
                    albums_text = ", ".join([album[0] for album in albums[:10]])
                    if len(albums) > 10:
                        albums_text += f"... (+{len(albums) - 10} más)"
                    
                    # Añadir álbumes a la tercera columna
                    albums_item = QTableWidgetItem(albums_text)
                    albums_item.setFlags(albums_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 2, albums_item)
                
                return checkboxes
            
            # Cargar datos de años
            def load_years_data():
                # Obtener años de las canciones
                self.cursor.execute("""
                    SELECT DISTINCT album_year
                    FROM songs 
                    WHERE album_year IS NOT NULL AND album_year != '' AND LENGTH(album_year) >= 4
                    ORDER BY album_year
                """)
                years = self.cursor.fetchall()
                
                # Obtener años incluidos o excluidos según el tipo de filtro
                filter_type = "included_years" if filter_type_combo.currentText() == "Incluir (Positivo)" else "excluded_years"
                filtered_years = self.get_excluded_items(filter_type)
                
                # Configurar el número de filas de la tabla
                table.setRowCount(len(years))
                
                # Diccionario para mantener referencia a los checkboxes
                checkboxes = {}
                
                # Llenar la tabla con datos
                for row, (year,) in enumerate(years):
                    # Crear widget para checkbox del año
                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout(checkbox_widget)
                    checkbox_layout.setContentsMargins(5, 0, 0, 0)
                    checkbox = QCheckBox(year)
                    checkbox.setChecked(year in filtered_years)
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.addStretch()
                    
                    # Guardar referencia al checkbox
                    checkboxes[year] = checkbox
                    
                    # Añadir el widget con checkbox a la tabla
                    table.setCellWidget(row, 0, checkbox_widget)
                    
                    # Obtener artistas de este año
                    self.cursor.execute("""
                        SELECT DISTINCT artist 
                        FROM songs 
                        WHERE album_year = ? 
                        ORDER BY artist
                    """, (year,))
                    artists = self.cursor.fetchall()
                    artists_text = ", ".join([artist[0] for artist in artists[:10]])
                    if len(artists) > 10:
                        artists_text += f"... (+{len(artists) - 10} más)"
                    
                    # Añadir artistas a la segunda columna
                    artists_item = QTableWidgetItem(artists_text)
                    artists_item.setFlags(artists_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 1, artists_item)
                    
                    # Obtener álbumes de este año
                    self.cursor.execute("""
                        SELECT DISTINCT album 
                        FROM songs 
                        WHERE album_year = ? AND album IS NOT NULL AND album != '' 
                        ORDER BY album
                    """, (year,))
                    albums = self.cursor.fetchall()
                    albums_text = ", ".join([album[0] for album in albums[:10]])
                    if len(albums) > 10:
                        albums_text += f"... (+{len(albums) - 10} más)"
                    
                    # Añadir álbumes a la tercera columna
                    albums_item = QTableWidgetItem(albums_text)
                    albums_item.setFlags(albums_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, 2, albums_item)
                
                return checkboxes
            
            layout.addWidget(table)
            
            # Variables para mantener los checkboxes
            decade_checkboxes = {}
            year_checkboxes = {}
            current_checkboxes = {}
            
            # Función para filtrar la tabla según el texto de búsqueda
            def filter_table(text):
                text = text.lower()
                for row in range(table.rowCount()):
                    period_widget = table.cellWidget(row, 0)
                    if period_widget:
                        checkbox = period_widget.layout().itemAt(0).widget()
                        period_name = checkbox.text().lower()
                        
                        artists_text = table.item(row, 1).text().lower() if table.item(row, 1) else ""
                        albums_text = table.item(row, 2).text().lower() if table.item(row, 2) else ""
                        
                        visible = (text in period_name or 
                                text in artists_text or 
                                text in albums_text)
                        
                        table.setRowHidden(row, not visible)
            
            search_edit.textChanged.connect(filter_table)
            
            # Función para actualizar el tipo de filtro
            def update_filter_type():
                nonlocal current_checkboxes
                update_table_data()
            
            filter_type_combo.currentIndexChanged.connect(update_filter_type)
            
            # Función para cargar los datos según el modo seleccionado
            def update_mode():
                nonlocal current_checkboxes
                
                # Guardar los datos actuales si hay alguno
                if current_checkboxes:
                    save_current_state()
                
                update_table_data()
            
            mode_combo.currentIndexChanged.connect(update_mode)
            
            # Botones
            buttons_layout = QHBoxLayout()
            select_all_btn = QPushButton("Seleccionar Todos")
            deselect_all_btn = QPushButton("Deseleccionar Todos")
            save_btn = QPushButton("Guardar")
            cancel_btn = QPushButton("Cancelar")
            
            buttons_layout.addWidget(select_all_btn)
            buttons_layout.addWidget(deselect_all_btn)
            buttons_layout.addWidget(save_btn)
            buttons_layout.addWidget(cancel_btn)
            
            layout.addLayout(buttons_layout)
            dialog.setLayout(layout)
            
            # Conectar señales
            def select_all():
                for row in range(table.rowCount()):
                    if not table.isRowHidden(row):
                        widget = table.cellWidget(row, 0)
                        if widget:
                            checkbox = widget.layout().itemAt(0).widget()
                            checkbox.setChecked(True)
            
            def deselect_all():
                for row in range(table.rowCount()):
                    if not table.isRowHidden(row):
                        widget = table.cellWidget(row, 0)
                        if widget:
                            checkbox = widget.layout().itemAt(0).widget()
                            checkbox.setChecked(False)
            
            def save_current_state():
                selected = []
                
                # Determinar qué tipo de filtro estamos guardando
                is_decade = mode_combo.currentText() == "Década"
                is_positive = filter_type_combo.currentText() == "Incluir (Positivo)"
                
                filter_key = ""
                if is_decade and is_positive:
                    filter_key = "included_decades"
                elif is_decade and not is_positive:
                    filter_key = "excluded_decades"
                elif not is_decade and is_positive:
                    filter_key = "included_years"
                else:
                    filter_key = "excluded_years"
                
                # Guardar los elementos seleccionados
                for period, checkbox in current_checkboxes.items():
                    if checkbox.isChecked():
                        selected.append(period)
                
                self.save_excluded_items(filter_key, selected)
            
            def save_changes():
                save_current_state()
                dialog.accept()
            
            select_all_btn.clicked.connect(select_all)
            deselect_all_btn.clicked.connect(deselect_all)
            save_btn.clicked.connect(save_changes)
            cancel_btn.clicked.connect(dialog.reject)
            
            # Cargar datos iniciales
            if mode_combo.currentText() == "Década":
                current_checkboxes = load_decades_data()
            else:
                current_checkboxes = load_years_data()
            
            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar por año/década: {e}")
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")



    def get_excluded_items(self, table_name):
        """Obtiene los elementos excluidos de la base de datos."""
        try:
            # Verificar si la tabla existe
            self.cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table_name}'
            """)
            if not self.cursor.fetchone():
                return []
            
            # Obtener los elementos
            self.cursor.execute(f"SELECT name FROM {table_name}")
            items = self.cursor.fetchall()
            return [item[0] for item in items]
        except Exception as e:
            print(f"Error al obtener elementos excluidos de {table_name}: {e}")
            return []


    def show_session_filter_dialog(self):
        """Muestra un diálogo para configurar filtros de sesión temporales."""
        try:
            dialog = QDialog(self)

            # Cargar la UI del diálogo
            dialog_ui_path = Path(PROJECT_ROOT, "ui", "jaangle", "jaangle_session_filter_dialog.ui")
            
            if os.path.exists(dialog_ui_path):
                from PyQt6 import uic
                uic.loadUi(dialog_ui_path, dialog)
                
                # Obtener referencias a los widgets
                table = dialog.findChild(QTableWidget, "artists_table")
                search_edit = dialog.findChild(QLineEdit, "search_edit")
                select_all_btn = dialog.findChild(QPushButton, "select_all_btn")
                deselect_all_btn = dialog.findChild(QPushButton, "deselect_all_btn")
                save_btn = dialog.findChild(QPushButton, "save_btn")
                cancel_btn = dialog.findChild(QPushButton, "cancel_btn")

                dialog.setWindowTitle("Filtros de Sesión")
                dialog.setMinimumWidth(450)
                dialog.setMinimumHeight(550)
                
                layout = QVBoxLayout()
                
                # Selector de tipo de filtro
                filter_type_layout = QHBoxLayout()
                filter_type_label = QLabel("Tipo de filtro:")
                filter_type_combo = QComboBox()
                filter_type_combo.addItems(["Artistas", "Álbumes", "Géneros", "Carpetas"])
                filter_type_layout.addWidget(filter_type_label)
                filter_type_layout.addWidget(filter_type_combo)
                layout.addLayout(filter_type_layout)
                
                # Añadir un buscador
                search_layout = QHBoxLayout()
                search_label = QLabel("Buscar:")
                search_edit = QLineEdit()
                search_edit.setPlaceholderText("Escribe para filtrar...")
                search_layout.addWidget(search_label)
                search_layout.addWidget(search_edit)
                layout.addLayout(search_layout)
                
                # Crear una lista con checkboxes
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll_content = QWidget()
                checkbox_layout = QVBoxLayout(scroll_content)
                
                # Variables para almacenar los checkboxes por categoría
                all_checkboxes = {
                    "Artistas": {},
                    "Álbumes": {},
                    "Géneros": {},
                    "Carpetas": {}
                }
                
                # Obtener elementos para cada categoría
                # Artistas
                self.cursor.execute("SELECT name FROM artists ORDER BY name")
                artists = self.cursor.fetchall()
                for artist in artists:
                    artist_name = artist[0]
                    checkbox = QCheckBox(artist_name)
                    checkbox.setVisible(False)  # Inicialmente oculto
                    checkbox_layout.addWidget(checkbox)
                    all_checkboxes["Artistas"][artist_name] = checkbox
                    
                # Álbumes
                self.cursor.execute("SELECT name FROM albums ORDER BY name")
                albums = self.cursor.fetchall()
                for album in albums:
                    album_name = album[0]
                    checkbox = QCheckBox(album_name)
                    checkbox.setVisible(False)  # Inicialmente oculto
                    checkbox_layout.addWidget(checkbox)
                    all_checkboxes["Álbumes"][album_name] = checkbox
                    
                # Géneros
                self.cursor.execute("SELECT name FROM genres ORDER BY name")
                genres = self.cursor.fetchall()
                if not genres:
                    self.cursor.execute("SELECT DISTINCT genre FROM songs WHERE genre IS NOT NULL ORDER BY genre")
                    genres = self.cursor.fetchall()
                for genre in genres:
                    genre_name = genre[0]
                    if genre_name:
                        checkbox = QCheckBox(genre_name)
                        checkbox.setVisible(False)  # Inicialmente oculto
                        checkbox_layout.addWidget(checkbox)
                        all_checkboxes["Géneros"][genre_name] = checkbox
                        
                # Carpetas
                self.cursor.execute("""
                    SELECT DISTINCT folder_path FROM albums 
                    WHERE folder_path IS NOT NULL 
                    ORDER BY folder_path
                """)
                folders = self.cursor.fetchall()
                for folder in folders:
                    folder_path = folder[0]
                    if folder_path:
                        checkbox = QCheckBox(folder_path)
                        checkbox.setVisible(False)  # Inicialmente oculto
                        checkbox_layout.addWidget(checkbox)
                        all_checkboxes["Carpetas"][folder_path] = checkbox
                
                scroll_content.setLayout(checkbox_layout)
                scroll.setWidget(scroll_content)
                layout.addWidget(scroll)
                
                # Función para mostrar los checkboxes correspondientes al tipo seleccionado
                def update_visible_checkboxes():
                    selected_type = filter_type_combo.currentText()
                    search_text = search_edit.text().lower()
                    
                    # Ocultar todos los checkboxes
                    for category in all_checkboxes.values():
                        for checkbox in category.values():
                            checkbox.setVisible(False)
                    
                    # Mostrar solo los del tipo seleccionado que coincidan con la búsqueda
                    for item_name, checkbox in all_checkboxes[selected_type].items():
                        checkbox.setVisible(search_text in item_name.lower())
                
                filter_type_combo.currentTextChanged.connect(update_visible_checkboxes)
                search_edit.textChanged.connect(update_visible_checkboxes)
                
                # Mostrar los checkboxes iniciales (artistas por defecto)
                update_visible_checkboxes()
                
                # Área para nombre de sesión
                session_layout = QHBoxLayout()
                session_label = QLabel("Nombre de la sesión:")
                session_edit = QLineEdit()
                session_edit.setPlaceholderText("Mi sesión personalizada")
                session_layout.addWidget(session_label)
                session_layout.addWidget(session_edit)
                layout.addLayout(session_layout)
                
                # Botones de operaciones de sesión
                session_ops_layout = QHBoxLayout()
                save_session_btn = QPushButton("Guardar Sesión")
                load_session_btn = QPushButton("Cargar Sesión")
                session_ops_layout.addWidget(save_session_btn)
                session_ops_layout.addWidget(load_session_btn)
                layout.addLayout(session_ops_layout)
                
                # Botones de acciones
                buttons_layout = QHBoxLayout()
                select_all_btn = QPushButton("Seleccionar Todos")
                deselect_all_btn = QPushButton("Deseleccionar Todos")
                apply_btn = QPushButton("Aplicar")
                cancel_btn = QPushButton("Cancelar")
                
                buttons_layout.addWidget(select_all_btn)
                buttons_layout.addWidget(deselect_all_btn)
                buttons_layout.addWidget(apply_btn)
                buttons_layout.addWidget(cancel_btn)
                
                layout.addLayout(buttons_layout)
                dialog.setLayout(layout)
                
                # Conectar señales
                def select_all():
                    selected_type = filter_type_combo.currentText()
                    for checkbox in all_checkboxes[selected_type].values():
                        if checkbox.isVisible():
                            checkbox.setChecked(True)
                
                def deselect_all():
                    selected_type = filter_type_combo.currentText()
                    for checkbox in all_checkboxes[selected_type].values():
                        if checkbox.isVisible():
                            checkbox.setChecked(False)
                
                def apply_filters():
                    # Guardar los filtros de sesión
                    session_filters = {
                        "name": session_edit.text() or "Sesión temporal",
                        "filters": {}
                    }
                    
                    for filter_type, checkboxes in all_checkboxes.items():
                        session_filters["filters"][filter_type] = [
                            item for item, checkbox in checkboxes.items() 
                            if checkbox.isChecked()
                        ]
                    
                    # Almacenar en el objeto
                    self.session_filters = session_filters
                    # Aplicar los filtros inmediatamente
                    self.apply_session_filters()
                    dialog.accept()
                
                def save_session():
                    # Primero recopilar los filtros seleccionados
                    session_name = session_edit.text() or "Sesión temporal"
                    session_data = {
                        "name": session_name,
                        "filters": {}
                    }
                    
                    for filter_type, checkboxes in all_checkboxes.items():
                        session_data["filters"][filter_type] = [
                            item for item, checkbox in checkboxes.items() 
                            if checkbox.isChecked()
                        ]
                    
                    # Guardar en un archivo JSON
                    self.save_session_to_file(session_data)
                
                def load_session():
                    # Cargar desde un archivo JSON
                    session_data = self.load_session_from_file()
                    if not session_data:
                        return
                    
                    # Actualizar la UI con los filtros cargados
                    session_edit.setText(session_data.get("name", "Sesión cargada"))
                    
                    # Limpiar todas las selecciones actuales
                    for category in all_checkboxes.values():
                        for checkbox in category.values():
                            checkbox.setChecked(False)
                    
                    # Marcar las selecciones según los datos cargados
                    loaded_filters = session_data.get("filters", {})
                    for filter_type, items in loaded_filters.items():
                        if filter_type in all_checkboxes:
                            for item in items:
                                if item in all_checkboxes[filter_type]:
                                    all_checkboxes[filter_type][item].setChecked(True)
                
                select_all_btn.clicked.connect(select_all)
                deselect_all_btn.clicked.connect(deselect_all)
                apply_btn.clicked.connect(apply_filters)
                save_session_btn.clicked.connect(save_session)
                load_session_btn.clicked.connect(load_session)
                cancel_btn.clicked.connect(dialog.reject)

            else:
                raise FileNotFoundError(f"No se encontró el archivo UI: {dialog_ui_path}")

            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtros de sesión: {e}")
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")

    def save_session_to_file(self, session_data):
        """Guarda los filtros de sesión en un archivo JSON."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            import json
            
            # Obtener la ubicación donde guardar el archivo
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Guardar Sesión", 
                str(Path.home()), 
                "Archivos JSON (*.json)"
            )
            
            if not file_path:
                return
            
            # Añadir la extensión .json si no está
            if not file_path.endswith('.json'):
                file_path += '.json'
            
            # Guardar los datos en el archivo
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=4)
            
            self.show_info_message("Sesión guardada", f"La sesión se ha guardado correctamente en: {file_path}")
        except Exception as e:
            print(f"Error al guardar la sesión: {e}")
            self.show_error_message("Error", f"Error al guardar la sesión: {e}")

    def load_session_from_file(self):
        """Carga los filtros de sesión desde un archivo JSON."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            import json
            
            # Solicitar la ubicación del archivo a cargar
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Cargar Sesión", 
                str(Path.home()), 
                "Archivos JSON (*.json)"
            )
            
            if not file_path:
                return None
            
            # Cargar los datos del archivo
            with open(file_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            self.show_info_message("Sesión cargada", f"La sesión '{session_data.get('name', 'sin nombre')}' se ha cargado correctamente")
            return session_data
        except Exception as e:
            print(f"Error al cargar la sesión: {e}")
            self.show_error_message("Error", f"Error al cargar la sesión: {e}")
            return None

    def apply_session_filters(self):
        """Aplica los filtros de sesión actual al obtener canciones."""
        if hasattr(self, 'session_filters') and self.session_filters:
            # Mostrar un indicador visual de que hay filtros de sesión activos
            self.update_session_filter_indicator(True)
        else:
            self.update_session_filter_indicator(False)

    def update_session_filter_indicator(self, is_active):
        """Actualiza el indicador visual de filtros de sesión activos."""
        if not hasattr(self, 'session_filter_indicator'):
            # Crear el indicador si no existe
            self.session_filter_indicator = QLabel("⭐ Filtros de sesión activos")
            self.session_filter_indicator.setStyleSheet("color: #FFD700; font-weight: bold;")
            
            # Agregarlo a un layout existente (usar el mismo layout donde están los labels de estadísticas)
            # Asumiendo que hay un stats_layout donde están score_label, total_label, etc.
            stats_layout = self.score_label.parent().layout()
            if stats_layout:
                stats_layout.addWidget(self.session_filter_indicator)
        
        # Mostrar u ocultar el indicador
        self.session_filter_indicator.setVisible(is_active)

    def clear_session_filters(self):
        """Limpia los filtros de sesión actuales."""
        self.session_filters = None
        self.update_session_filter_indicator(False)
        self.show_info_message("Filtros eliminados", "Los filtros de sesión han sido eliminados")

    def show_info_message(self, title, message):
        """Muestra un mensaje informativo."""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()



    def show_folder_filter_dialog(self):
        """Muestra un diálogo para filtrar carpetas de álbumes."""
        try:
            dialog = QDialog(self)

            dialog_ui_path = Path(PROJECT_ROOT, "ui", "jaangle", "jaangle_artist_filter_dialog.ui")
            
            if os.path.exists(dialog_ui_path):
                from PyQt6 import uic
                uic.loadUi(dialog_ui_path, dialog)
                
                # Obtener referencias a los widgets
                table = dialog.findChild(QTableWidget, "artists_table")
                search_edit = dialog.findChild(QLineEdit, "search_edit")
                select_all_btn = dialog.findChild(QPushButton, "select_all_btn")
                deselect_all_btn = dialog.findChild(QPushButton, "deselect_all_btn")
                save_btn = dialog.findChild(QPushButton, "save_btn")
                cancel_btn = dialog.findChild(QPushButton, "cancel_btn")

                dialog.setWindowTitle("Filtrar Carpetas")
                dialog.setMinimumWidth(400)
                dialog.setMinimumHeight(500)
                
                layout = QVBoxLayout()
                
                # Añadir un buscador
                search_layout = QHBoxLayout()
                search_label = QLabel("Buscar:")
                search_edit = QLineEdit()
                search_edit.setPlaceholderText("Escribe para filtrar...")
                search_layout.addWidget(search_label)
                search_layout.addWidget(search_edit)
                layout.addLayout(search_layout)
                
                # Crear una lista con checkboxes
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll_content = QWidget()
                checkbox_layout = QVBoxLayout(scroll_content)
                
                # Obtener la lista de carpetas únicas
                self.cursor.execute("""
                    SELECT DISTINCT folder_path FROM albums 
                    WHERE folder_path IS NOT NULL 
                    ORDER BY folder_path
                """)
                folders = self.cursor.fetchall()
                
                # Obtener carpetas excluidas
                excluded_folders = self.get_excluded_items("excluded_folders")
                
                checkboxes = {}
                for folder in folders:
                    folder_path = folder[0]
                    if folder_path:  # Asegurarse de que no es None
                        checkbox = QCheckBox(folder_path)
                        checkbox.setChecked(folder_path in excluded_folders)
                        checkbox_layout.addWidget(checkbox)
                        checkboxes[folder_path] = checkbox
                
                scroll_content.setLayout(checkbox_layout)
                scroll.setWidget(scroll_content)
                layout.addWidget(scroll)
                
                # Conectar el buscador para filtrar los checkboxes
                def filter_folders(text):
                    text = text.lower()
                    for folder_path, checkbox in checkboxes.items():
                        checkbox.setVisible(text in folder_path.lower())
                
                search_edit.textChanged.connect(filter_folders)
                
                # Botones
                buttons_layout = QHBoxLayout()
                select_all_btn = QPushButton("Seleccionar Todos")
                deselect_all_btn = QPushButton("Deseleccionar Todos")
                save_btn = QPushButton("Guardar")
                cancel_btn = QPushButton("Cancelar")
                
                buttons_layout.addWidget(select_all_btn)
                buttons_layout.addWidget(deselect_all_btn)
                buttons_layout.addWidget(save_btn)
                buttons_layout.addWidget(cancel_btn)
                
                layout.addLayout(buttons_layout)
                dialog.setLayout(layout)
                
                # Conectar señales
                def select_all():
                    for checkbox in checkboxes.values():
                        if checkbox.isVisible():
                            checkbox.setChecked(True)
                
                def deselect_all():
                    for checkbox in checkboxes.values():
                        if checkbox.isVisible():
                            checkbox.setChecked(False)
                
                def save_changes():
                    excluded = [folder for folder, checkbox in checkboxes.items() if checkbox.isChecked()]
                    self.save_excluded_items("excluded_folders", excluded)
                    dialog.accept()
                
                select_all_btn.clicked.connect(select_all)
                deselect_all_btn.clicked.connect(deselect_all)
                save_btn.clicked.connect(save_changes)
                cancel_btn.clicked.connect(dialog.reject)
        
        
            else:
                raise FileNotFoundError(f"No se encontró el archivo UI: {dialog_ui_path}")
        
        
            
            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar carpetas: {e}")
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")

    def on_music_origin_changed(self):
        """Maneja el cambio de origen de la música (local, Spotify, o Online)."""
        try:
            if not hasattr(self, 'local_radio') or not hasattr(self, 'spotify_radio') or not hasattr(self, 'listenbrainz_radio'):
                print("Radio buttons no inicializados")
                return
                    
            if self.local_radio.isChecked():
                self.music_origin = 'local'
                print("Origen de música cambiado a: Local")
                    
                # Ocultar reproductores si están visibles
                if hasattr(self, 'spotify_container') and self.spotify_container:
                    self.spotify_container.hide()
                if hasattr(self, 'listenbrainz_container') and self.listenbrainz_container:
                    self.listenbrainz_container.hide()
                    
            elif self.spotify_radio.isChecked():
                self.music_origin = 'spotify'
                # Verificar si necesitamos un usuario de Spotify
                if not self.spotify_user:
                    from PyQt6.QtWidgets import QInputDialog
                    user, ok = QInputDialog.getText(
                        self, 
                        "Usuario de Spotify", 
                        "Introduce tu nombre de usuario de Spotify:"
                    )
                    if ok and user:
                        self.spotify_user = user
                        print(f"Usuario de Spotify configurado: {user}")
                    else:
                        # Si no se proporciona usuario, volver a Local
                        self.local_radio.setChecked(True)
                        self.music_origin = 'local'
                        print("Volviendo a origen local por falta de usuario de Spotify")
                else:
                    print(f"Origen de música cambiado a: Spotify (usuario: {self.spotify_user})")
                    
                # Ocultar contenedor de ListenBrainz si está visible
                if hasattr(self, 'listenbrainz_container') and self.listenbrainz_container:
                    self.listenbrainz_container.hide()
                    
            elif self.listenbrainz_radio.isChecked():
                # Cambiar a "online" en lugar de "listenbrainz"
                self.music_origin = 'online'
                # Ya no necesitamos usuario para reproducción online
                print(f"Origen de música cambiado a: Online")
                    
                # Ocultar contenedor de Spotify si está visible
                if hasattr(self, 'spotify_container') and self.spotify_container:
                    self.spotify_container.hide()
                    
        except Exception as e:
            print(f"Error en on_music_origin_changed: {e}")
            import traceback
            traceback.print_exc()

    def _play_spotify_track(self):
        """Método auxiliar para reproducir canción de Spotify después del delay inicial."""
        try:
            success = self.spotify_player.play(self.current_song_id)
            if not success:
                logger.error(f"Error al reproducir canción de Spotify con ID {self.current_song_id}, intentando con otra pregunta")
                QTimer.singleShot(1000, self.show_next_question)
                return
                
            # Configurar el temporizador para la cuenta regresiva
            self.remaining_time = self.song_duration_seconds
            self.countdown_label.setText(str(self.remaining_time))
            self.progress_bar.setValue(100)
            
            # Iniciar la cuenta regresiva
            self.timer.start()
        except Exception as e:
            print(f"Error al reproducir canción de Spotify: {e}")
            QTimer.singleShot(1000, self.show_next_question)

    def _play_local_track(self):
        """Método auxiliar para reproducir canción local después del delay inicial."""
        try:
            # Obtener la información relevante de la canción actual
            song_duration = 0
            if hasattr(self, 'current_song') and self.current_song and len(self.current_song) > 5:
                song_duration = self.current_song[5]
            
            if not song_duration or song_duration <= 0:
                song_duration = 60  # Valor predeterminado si la duración no es válida
                
            # Calcular los límites de reproducción
            start_from_beginning = random.random() < self.start_from_beginning_chance
            avoid_last_seconds = min(self.avoid_last_seconds, int(song_duration * 0.1))
            
            # Si la canción tiene suficiente duración, elegir un punto aleatorio para comenzar
            if start_from_beginning or song_duration <= (self.song_duration_seconds + avoid_last_seconds):
                start_position = 0
            else:
                max_start = max(0, song_duration - self.song_duration_seconds - avoid_last_seconds)
                if max_start > 0:
                    # Corregir el error: convertir max_start a entero antes de usarlo en randint
                    max_start_int = int(max_start)
                    start_position = random.randint(10, max_start_int)
                else:
                    start_position = 0
            
            # Mostrar progreso de carga
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setValue(50)
                
            # Configurar el reproductor
            source = QUrl.fromLocalFile(self.current_song_path)
            self.player.setSource(source)
            
            # Verificar si la fuente es válida antes de reproducir
            QTimer.singleShot(200, lambda: self.play_song_at_position(start_position))
            
            # Configurar el temporizador
            self.remaining_time = self.song_duration_seconds
            self.countdown_label.setText(str(self.remaining_time))
            self.progress_bar.setValue(90)
            
            # Iniciar la cuenta regresiva
            self.timer.start()
        except Exception as e:
            print(f"Error al reproducir canción local: {e}")
            import traceback
            traceback.print_exc()
            QTimer.singleShot(1000, self.show_next_question)

    def play_song_at_position(self, position_seconds):
        """Reproduce la canción desde una posición específica."""
        try:
            # Verificar si estamos reproduciendo desde Spotify
            if self.music_origin == 'spotify' and hasattr(self, 'spotify_player'):
                # Si estamos usando Spotify, intentar posicionar la reproducción
                # Nota: esto dependerá de las capacidades del reproductor de Spotify
                if hasattr(self.spotify_player, 'seek_to_position'):
                    self.spotify_player.seek_to_position(position_seconds)
                return
            
            # Código para reproducción local
            if not hasattr(self, 'player') or not self.player:
                print("Error: Reproductor no disponible")
                return
                
            if self.player.mediaStatus() in [QMediaPlayer.MediaStatus.InvalidMedia, 
                                            QMediaPlayer.MediaStatus.NoMedia]:
                print(f"Error: Fuente de media inválida: {self.current_song_path}")
                # Intentar reproducir la siguiente canción
                QTimer.singleShot(500, self.show_next_question)
                return
                
            # Establecer la posición y reproducir
            self.player.setPosition(int(position_seconds * 1000))  # Convertir a milisegundos enteros
            self.player.play()
            
            # Verificar después de un breve retraso si la reproducción comenzó
            QTimer.singleShot(500, self.check_playback_started)
        except Exception as e:
            print(f"Error al establecer la posición de reproducción: {e}")
            import traceback
            traceback.print_exc()
            QTimer.singleShot(500, self.show_next_question)



    def save_config(self):
        """Guarda la configuración actual a un archivo."""
        try:
            import json
            import os
            from pathlib import Path
            
            # Crear directorio para configuración si no existe
            config_dir = Path(PROJECT_ROOT, "config", "jaangle")
            os.makedirs(config_dir, exist_ok=True)
            
            # Preparar datos a guardar
            config_data = {
                "option_hotkeys": self.option_hotkeys,
                "music_origin": self.music_origin,
                "quiz_duration_minutes": self.quiz_duration_minutes,
                "song_duration_seconds": self.song_duration_seconds,
                "pause_between_songs": self.pause_between_songs,
                "options_count": self.options_count
            }
            
            # Guardar en archivo
            config_path = Path(config_dir, "config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error al guardar configuración: {e}")
            return False

    def load_config(self):
        """Carga la configuración desde un archivo."""
        try:
            import json
            from pathlib import Path
            
            config_path = Path(PROJECT_ROOT, "config", "jaangle", "config.json")
            if not config_path.exists():
                return False
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            # Aplicar configuración cargada
            if "option_hotkeys" in config_data:
                self.option_hotkeys = config_data["option_hotkeys"]
            if "music_origin" in config_data:
                self.music_origin = config_data["music_origin"]
            if "quiz_duration_minutes" in config_data:
                self.quiz_duration_minutes = config_data["quiz_duration_minutes"]
            if "song_duration_seconds" in config_data:
                self.song_duration_seconds = config_data["song_duration_seconds"]
            if "pause_between_songs" in config_data:
                self.pause_between_songs = config_data["pause_between_songs"]
            if "options_count" in config_data:
                self.options_count = config_data["options_count"]
                
            return True
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
            return False

