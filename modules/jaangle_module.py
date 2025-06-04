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
from modules.submodules.jaangle.jaangle_advanced_config import JaangleAdvancedConfig


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
        self.advanced_filters = {}

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

        # Inicializar tablas de filtros de Jaangle
        if hasattr(self, 'cursor') and self.cursor:
            self.initialize_jaangle_tables()
        else:
            print("Advertencia: No se pudieron inicializar las tablas de filtros de Jaangle")
            
        # Cargar configuración después de inicializar UI
        self.load_config()

        self.init_ui_additions()

        self.complete_ui_setup()

        self.add_advanced_settings_button()
        

        # Inicializar configuración avanzada
        self.advanced_config = JaangleAdvancedConfig(parent=self, project_root=PROJECT_ROOT)
        
        # Conectar señales de la configuración avanzada
        self.advanced_config.config_changed.connect(self.on_advanced_config_changed)
        self.advanced_config.player_changed.connect(self.on_player_changed)

        # Cargar jugador por defecto o crear uno si no existe
        self.initialize_default_player()


    def init_ui_additions(self):
        """Adiciones al método init_ui para añadir el progressbar total."""
        try:
            # Buscar el layout donde están las estadísticas
            stats_parent = None
            if hasattr(self, 'score_label') and self.score_label.parent():
                stats_parent = self.score_label.parent()
            
            if stats_parent and stats_parent.layout():
                # Crear el progressbar para el tiempo total del quiz
                self.total_quiz_progressbar = QProgressBar()
                self.total_quiz_progressbar.setMinimum(0)
                self.total_quiz_progressbar.setMaximum(100)
                self.total_quiz_progressbar.setValue(0)
                self.total_quiz_progressbar.setTextVisible(True)
                self.total_quiz_progressbar.setFormat("Tiempo restante: %p%")
                
                # Estilo del progressbar
                self.total_quiz_progressbar.setStyleSheet("""
                    QProgressBar {
                        border: 2px;
                        border-radius: 5px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        border-radius: 3px;
                    }
                """)
                
                # Label para mostrar tiempo restante en formato legible
                # self.total_time_label = QLabel("Tiempo restante: --:--")
                # self.total_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                # font = self.total_time_label.font()
                # font.setBold(True)
                # self.total_time_label.setFont(font)
                
                # # Añadir al layout
                # stats_parent.layout().addWidget(self.total_time_label)
                stats_parent.layout().addWidget(self.total_quiz_progressbar)
                
                print("Progress bar del quiz total añadido correctamente")
            else:
                print("No se pudo encontrar el layout de estadísticas para añadir el progressbar")
            
            self.create_player_indicator()
            print("Indicador de jugador añadido correctamente")
        
        except Exception as e:
            print(f"Error al añadir progressbar total: {e}")
            import traceback
            traceback.print_exc()

    def format_time(self, seconds):
        """Convierte segundos a formato MM:SS."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    
    def update_advanced_filters_indicator(self):
        """Actualiza el indicador de filtros avanzados en la UI."""
        try:
            if not hasattr(self, 'advanced_filters_indicator'):
                # Crear el indicador si no existe
                self.advanced_filters_indicator = QLabel()
                self.advanced_filters_indicator.setStyleSheet("color: #FFA500; font-weight: bold;")
                
                # Agregarlo a tu layout principal
                if hasattr(self, 'stats_layout'):
                    self.stats_layout.addWidget(self.advanced_filters_indicator)
            
            # Actualizar texto
            summary = self.get_active_advanced_filters_summary()
            self.advanced_filters_indicator.setText(summary)
            self.advanced_filters_indicator.setVisible("Sin filtros" not in summary)
            
        except Exception as e:
            print(f"Error actualizando indicador de filtros: {e}")

    def update_total_quiz_progress(self):
        """Actualiza el progressbar del tiempo total del quiz."""
        try:
            if not self.game_active:
                return
                
            self.remaining_total_time -= 1
            
            if self.remaining_total_time <= 0:
                self.remaining_total_time = 0
                print("Tiempo del quiz agotado, finalizando...")
                # Detener reproducción inmediatamente
                self.stop_all_playback()
                # Si se acabó el tiempo, finalizar el quiz
                self.end_quiz()
                return
                
            # Calcular porcentaje
            progress_percent = (self.remaining_total_time / self.total_quiz_duration_seconds) * 100
            
            # Actualizar progressbar
            if hasattr(self, 'total_quiz_progressbar'):
                self.total_quiz_progressbar.setValue(int(progress_percent))
                self.total_quiz_progressbar.setFormat(f"Tiempo restante: {self.format_time(self.remaining_total_time)}")
                
                # Cambiar color cuando queda poco tiempo
                if progress_percent <= 10:  # Menos del 10%
                    self.total_quiz_progressbar.setStyleSheet("""
                        QProgressBar {
                            border: 2px solid grey;
                            border-radius: 5px;
                            text-align: center;
                        }
                        QProgressBar::chunk {
                            background-color: #f44336;
                            border-radius: 3px;
                        }
                    """)
                elif progress_percent <= 25:  # Menos del 25%
                    self.total_quiz_progressbar.setStyleSheet("""
                        QProgressBar {
                            border: 2px solid grey;
                            border-radius: 5px;
                            text-align: center;
                        }
                        QProgressBar::chunk {
                            background-color: #FF9800;
                            border-radius: 3px;
                        }
                    """)
                else:
                    # Estilo normal
                    self.total_quiz_progressbar.setStyleSheet("""
                        QProgressBar {
                            border: 2px solid grey;
                            border-radius: 5px;
                            text-align: center;
                        }
                        QProgressBar::chunk {
                            background-color: #4CAF50;
                            border-radius: 3px;
                        }
                    """)
            
            # Actualizar label
            # if hasattr(self, 'total_time_label'):
            #     self.total_time_label.setText(f"Tiempo restante: {self.format_time(self.remaining_total_time)}")
                
            #     # Cambiar color del texto cuando queda poco tiempo
            #     if progress_percent <= 10:
            #         self.total_time_label.setStyleSheet("color: #f44336; font-weight: bold;")
            #     elif progress_percent <= 25:
            #         self.total_time_label.setStyleSheet("color: #FF9800; font-weight: bold;")
            #     else:
            #         self.total_time_label.setStyleSheet("font-weight: bold;")
            
        except Exception as e:
            print(f"Error al actualizar progressbar total: {e}")
            import traceback
            traceback.print_exc()

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
                # self.filter_artists_btn.clicked.connect(self.show_artist_filter_dialog)
                # self.filter_albums_btn.clicked.connect(self.show_album_filter_dialog)
                # self.filter_folders_btn.clicked.connect(self.show_folder_filter_dialog)
                # self.filter_genres_btn.clicked.connect(self.show_genre_filter_dialog)
                # self.filter_sellos_btn.clicked.connect(self.show_sellos_filter_dialog)
                # self.session_filters_btn.clicked.connect(self.show_session_filter_dialog)
                # self.clear_session_btn.clicked.connect(self.clear_session_filters)
                
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
        
        self.add_config_change_handlers()
        
        # Timer para countdown
        self.timer = QTimer()
        self.timer.setInterval(1000)  # 1 segundo
        self.timer.timeout.connect(self.update_countdown)
        
        # Timer para el quiz completo
        self.quiz_timer = QTimer()
        self.quiz_timer.timeout.connect(self.end_quiz)
        
        # Deshabilitar opciones al inicio
        self.enable_options(False)

    def show_basic_config(self):
        """Muestra u oculta la sección de configuración básica (método alternativo)."""
        if hasattr(self, 'config_group'):
            self.config_group.setVisible(not self.config_group.isVisible())

    def add_hotkeys_button_to_basic_config(self):
        """Añade solo el botón de hotkeys a la configuración básica si se mantiene visible."""
        try:
            if hasattr(self, 'config_group'):
                config_layout = self.config_group.layout()
                if config_layout:
                    # Crear botón para configurar hotkeys
                    hotkeys_btn = QPushButton("Configurar Teclas Rápidas")
                    hotkeys_btn.clicked.connect(self.show_hotkey_config_dialog)
                    
                    # Añadir al layout
                    config_layout.addWidget(hotkeys_btn)
                    
                    print("Botón de hotkeys añadido a configuración básica")
            
        except Exception as e:
            print(f"Error al añadir botón de hotkeys: {e}")


    def complete_ui_setup(self):
        """Completa la configuración de la UI después de la inicialización."""
        try:
            # Código existente...
            if hasattr(self, 'config_group'):
                self.add_hotkeys_button_to_basic_config()
            
            # NUEVO: Configurar menú contextual del indicador de jugador
            self.setup_player_indicator_context_menu()
            
            print("Configuración de UI completada - filtros movidos a diálogo avanzado")
            
        except Exception as e:
            print(f"Error al completar configuración de UI: {e}")


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
        action_select = QPushButton("Seleccionar")
        action_select.setProperty("option_id", i)
        action_select.clicked.connect(self.on_option_selected)
        
        # Guardar referencias para actualizar después
        action_select.song_label = song_label
        action_select.artist_label = artist_label
        action_select.album_label = album_label
        action_select.album_image = album_image
        
        option_layout.addWidget(action_select)
        option_group.setLayout(option_layout)
        
        options_layout.addWidget(option_group, row, col)
        self.option_buttons.append(action_select)



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
                action_select = option_widget.findChild(QPushButton, "action_select")
                song_label = option_widget.findChild(QLabel, "song_label")
                artist_label = option_widget.findChild(QLabel, "artist_label")
                album_label = option_widget.findChild(QLabel, "album_label")
                album_image = option_widget.findChild(QLabel, "album_image")
                
                # Configurar el botón
                action_select.setText(f"Opción {i+1}")
                action_select.setProperty("option_id", i)
                action_select.clicked.connect(self.on_option_selected)
                
                # Guardar referencias para actualizar después
                action_select.song_label = song_label
                action_select.artist_label = artist_label
                action_select.album_label = album_label
                action_select.album_image = album_image
                
                options_layout.addWidget(option_widget, row, col)
                self.option_buttons.append(action_select)
                
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
        """Abre directamente el diálogo de configuración avanzada."""
        self.show_advanced_settings_dialog()

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
        
        # Inicializar tiempo total del quiz
        self.total_quiz_duration_seconds = self.quiz_duration_minutes * 60
        self.remaining_total_time = self.total_quiz_duration_seconds
        
        # Configurar progressbar total
        if hasattr(self, 'total_quiz_progressbar'):
            self.total_quiz_progressbar.setValue(100)
            self.total_quiz_progressbar.setFormat(f"Tiempo restante: {self.format_time(self.remaining_total_time)}")
        
        # if hasattr(self, 'total_time_label'):
        #     self.total_time_label.setText(f"Tiempo restante: {self.format_time(self.remaining_total_time)}")
        
        # Activar el estado del juego
        self.game_active = True
        
        # Configurar el timer del quiz completo
        try:
            self.quiz_timer.timeout.disconnect()  # Desconectar señales previas
        except TypeError:
            pass  # No hay conexiones previas
        self.quiz_timer.timeout.connect(self.end_quiz)
        self.quiz_timer.start(self.total_quiz_duration_seconds * 1000)  # En milisegundos
        
        # Timer para actualizar el progreso total cada segundo
        if not hasattr(self, 'total_progress_timer'):
            self.total_progress_timer = QTimer()
            self.total_progress_timer.setInterval(1000)  # 1 segundo
        
        try:
            self.total_progress_timer.timeout.disconnect()  # Desconectar señales previas
        except TypeError:
            pass  # No hay conexiones previas
        self.total_progress_timer.timeout.connect(self.update_total_quiz_progress)
        self.total_progress_timer.start()
        
        # Iniciar la primera pregunta
        self.show_next_question()
   
   
    def stop_quiz(self):
        """Detiene el juego en curso."""
        self.game_active = False
        
        # Actualizar estados de botones
        if hasattr(self, 'start_button') and hasattr(self, 'stop_button'):
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
        elif hasattr(self, 'action_toggle'):
            self.action_toggle.setText("Iniciar Quiz")
        
        # Detener TODOS los timers
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'quiz_timer'):
            self.quiz_timer.stop()
        if hasattr(self, 'total_progress_timer'):
            self.total_progress_timer.stop()
        
        # MODIFICADO: Usar el nuevo método para detener toda la reproducción
        self.stop_all_playback()
        
        # Ocultar los contenedores de los reproductores
        if hasattr(self, 'spotify_container') and self.spotify_container:
            self.spotify_container.hide()
        if hasattr(self, 'listenbrainz_container') and self.listenbrainz_container:
            self.listenbrainz_container.hide()
        
        # Deshabilitar opciones
        self.enable_options(False)
        
        # Restablecer la visualización
        if hasattr(self, 'countdown_label'):
            self.countdown_label.setText("---")
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(0)
        
        # Restablecer el progressbar total
        if hasattr(self, 'total_quiz_progressbar'):
            self.total_quiz_progressbar.setValue(0)
            self.total_quiz_progressbar.setFormat("Tiempo restante: --:--")
            self.total_quiz_progressbar.setStyleSheet("""
                QProgressBar {
                    border: 2px;
                    border-radius: 5px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    border-radius: 3px;
                }
            """)
        
        # if hasattr(self, 'total_time_label'):
        #     self.total_time_label.setText("Tiempo restante: --:--")
        #     self.total_time_label.setStyleSheet("font-weight: bold;")


    def end_quiz(self):
        """Finaliza el quiz cuando se acaba el tiempo total."""
        print("Finalizando quiz...")
        
        # Detener el timer de progreso total
        if hasattr(self, 'total_progress_timer'):
            self.total_progress_timer.stop()
        
        # Detener reproducción ANTES de todo lo demás
        self.stop_all_playback()
        
        # NUEVO: Actualizar estadísticas del jugador
        self.update_player_game_statistics()
        
        # Pequeña pausa para asegurar que la reproducción se ha detenido
        QTimer.singleShot(500, self._show_final_results)


    def update_player_game_statistics(self):
        """Actualiza las estadísticas del jugador al final del juego."""
        try:
            if not hasattr(self, 'advanced_config') or not self.advanced_config.get_current_player():
                return
            
            # Calcular tiempo jugado en segundos
            total_duration = self.quiz_duration_minutes * 60
            time_played = total_duration - (self.remaining_total_time if hasattr(self, 'remaining_total_time') else 0)
            
            # Actualizar estadísticas
            self.advanced_config.update_player_statistics(
                games_played=1,
                questions=self.total_played,
                correct=self.score,
                time_played=time_played
            )
            
            print(f"Estadísticas actualizadas para {self.advanced_config.get_current_player()}")
            
        except Exception as e:
            print(f"Error al completar configuración de UI: {e}")

    def stop_all_playback(self):
        """Detiene toda la reproducción de música activa de forma más agresiva."""
        try:
            print("Deteniendo toda la reproducción...")
            
            # Detener reproducción local - método más agresivo
            if hasattr(self, 'player') and self.player:
                # Primero pausar
                self.player.pause()
                # Luego detener
                self.player.stop()
                # Limpiar la fuente completamente
                self.player.setSource(QUrl())
                # Establecer posición a 0
                self.player.setPosition(0)
                print("Reproductor local detenido")
            
            # Detener audio output si existe
            if hasattr(self, 'audio_output') and self.audio_output:
                self.audio_output.setVolume(0.0)  # Silenciar inmediatamente
                print("Audio output silenciado")
            
            # Detener reproducción de Spotify
            if hasattr(self, 'spotify_player') and self.spotify_player:
                self.spotify_player.stop()
                print("Reproductor Spotify detenido")
                
            # Detener reproducción de ListenBrainz/Online
            if hasattr(self, 'listenbrainz_player') and self.listenbrainz_player:
                self.listenbrainz_player.stop()
                print("Reproductor online detenido")
            
            print("Toda la reproducción ha sido detenida")
            
        except Exception as e:
            print(f"Error al detener reproducción: {e}")
            import traceback
            traceback.print_exc()

    def get_random_songs(self, count=4, max_retries=3):
        """Reemplaza el método existente con esta versión que incluye filtros avanzados."""
        self.get_random_songs_with_advanced_filters(count, max_retries)
        

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


    def restore_audio_volume(self):
        """Restaura el volumen del audio output después de silenciarlo."""
        try:
            if hasattr(self, 'audio_output') and self.audio_output:
                self.audio_output.setVolume(1.0)  # Volumen completo por defecto
                print("Volumen del audio output restaurado")
        except Exception as e:
            print(f"Error al restaurar volumen: {e}")

    def show_next_question(self):
        """Muestra la siguiente pregunta del quiz con soporte mejorado para reproducción."""
        if not self.game_active:
            return

        # Restaurar volumen si fue silenciado
        self.restore_audio_volume()
    
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
            
            # NUEVO: Detener reproducción cuando se acaba el tiempo de la canción
            self.stop_all_playback()
            
            # NUEVO: Aplicar penalización por tiempo agotado
            self.apply_time_adjustment(False, self.current_song_id)  # False = respuesta incorrecta
            
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
        
        # NUEVO: Detener reproducción cuando se selecciona una opción
        self.stop_all_playback()
        
        # Determinar si la respuesta es correcta
        is_correct = selected_option == self.current_correct_option
        
        # NUEVO: Aplicar ajuste de tiempo basado en penalizaciones/premios
        self.apply_time_adjustment(is_correct, self.current_song_id)
        
        # Actualizar estadísticas
        self.total_played += 1
        if is_correct:
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
        # Código existente...
        self.save_config()
        self.stop_quiz()
        
        # NUEVO: Guardar configuración del jugador actual antes de cerrar
        if hasattr(self, 'advanced_config') and self.advanced_config.get_current_player():
            self.advanced_config.save_current_player_config()
        
        # Limpiar timer de progreso total
        if hasattr(self, 'total_progress_timer'):
            self.total_progress_timer.stop()
        
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
            dialog.setWindowTitle("Filtrar Artistas")
            dialog.setMinimumWidth(800)
            dialog.setMinimumHeight(600)
            
            layout = QVBoxLayout()
            
            # Añadir un buscador
            search_layout = QHBoxLayout()
            search_label = QLabel("Buscar:")
            search_edit = QLineEdit()
            search_edit.setPlaceholderText("Escribe para filtrar...")
            search_layout.addWidget(search_label)
            search_layout.addWidget(search_edit)
            layout.addLayout(search_layout)
            
            # Crear tabla directamente en lugar de buscarla en UI
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Artista", "Álbumes", "Sellos"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(table)
            
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

            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar artistas: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")

  


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
            dialog.setWindowTitle("Filtrar Álbumes")
            dialog.setMinimumWidth(800)
            dialog.setMinimumHeight(600)
            
            layout = QVBoxLayout()
            
            # Añadir un buscador
            search_layout = QHBoxLayout()
            search_label = QLabel("Buscar:")
            search_edit = QLineEdit()
            search_edit.setPlaceholderText("Escribe para filtrar...")
            search_layout.addWidget(search_label)
            search_layout.addWidget(search_edit)
            layout.addLayout(search_layout)
            
            # Crear tabla
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Álbum", "Artista", "Sello", "Año"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            layout.addWidget(table)
            
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
                label_item = QTableWidgetItem(str(label) if label else "")
                label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 2, label_item)
                
                # Añadir información del año
                year_item = QTableWidgetItem(str(year) if year else "")
                year_item.setFlags(year_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 3, year_item)
            
            # Función para filtrar la tabla
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

            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar álbumes: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")





    def show_artist_filter_dialog(self):
        """Muestra un diálogo para filtrar artistas con información de álbumes y sellos."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar Artistas")
            dialog.setMinimumWidth(800)
            dialog.setMinimumHeight(600)
            
            layout = QVBoxLayout()
            
            # Añadir un buscador
            search_layout = QHBoxLayout()
            search_label = QLabel("Buscar:")
            search_edit = QLineEdit()
            search_edit.setPlaceholderText("Escribe para filtrar...")
            search_layout.addWidget(search_label)
            search_layout.addWidget(search_edit)
            layout.addLayout(search_layout)
            
            # Crear tabla directamente en lugar de buscarla en UI
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Artista", "Álbumes", "Sellos"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(table)
            
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

            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar artistas: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")


    def show_album_filter_dialog(self):
        """Muestra un diálogo para filtrar álbumes con información de artista, sello y año."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar Álbumes")
            dialog.setMinimumWidth(800)
            dialog.setMinimumHeight(600)
            
            layout = QVBoxLayout()
            
            # Añadir un buscador
            search_layout = QHBoxLayout()
            search_label = QLabel("Buscar:")
            search_edit = QLineEdit()
            search_edit.setPlaceholderText("Escribe para filtrar...")
            search_layout.addWidget(search_label)
            search_layout.addWidget(search_edit)
            layout.addLayout(search_layout)
            
            # Crear tabla
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Álbum", "Artista", "Sello", "Año"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            layout.addWidget(table)
            
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
                label_item = QTableWidgetItem(str(label) if label else "")
                label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 2, label_item)
                
                # Añadir información del año
                year_item = QTableWidgetItem(str(year) if year else "")
                year_item.setFlags(year_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 3, year_item)
            
            # Función para filtrar la tabla
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

            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar álbumes: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")


    def show_genre_filter_dialog(self):
        """Muestra un diálogo para filtrar géneros con información de artistas y sellos."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar Géneros")
            dialog.setMinimumWidth(800)
            dialog.setMinimumHeight(600)
            
            layout = QVBoxLayout()
            
            # Añadir un buscador
            search_layout = QHBoxLayout()
            search_label = QLabel("Buscar:")
            search_edit = QLineEdit()
            search_edit.setPlaceholderText("Escribe para filtrar...")
            search_layout.addWidget(search_label)
            search_layout.addWidget(search_edit)
            layout.addLayout(search_layout)
            
            # Crear tabla
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Género", "Artistas", "Sellos"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(table)
            
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
            
            # Función para filtrar la tabla
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

            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar géneros: {e}")
            import traceback
            traceback.print_exc()
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
        """
        Obtiene los elementos excluidos de la base de datos con prefijo jaangle_exclude_.
        
        Args:
            table_name (str): Nombre del tipo de tabla (ej: "excluded_artists")
            
        Returns:
            list: Lista de nombres de elementos excluidos
        """
        try:
            if not hasattr(self, 'cursor') or not self.cursor:
                print("Error: No database cursor available")
                return []
            
            # Mapear tipos de filtros a nombres de tabla con prefijo
            table_mapping = {
                "excluded_artists": "jaangle_exclude_artists",
                "excluded_albums": "jaangle_exclude_albums",
                "excluded_genres": "jaangle_exclude_genres",
                "excluded_folders": "jaangle_exclude_folders", 
                "excluded_decades": "jaangle_exclude_decades",
                "excluded_years": "jaangle_exclude_years",
                "included_decades": "jaangle_include_decades",
                "included_years": "jaangle_include_years",
                "excluded_labels": "jaangle_exclude_labels",
                "excluded_countries": "jaangle_exclude_countries"
            }
            
            actual_table = table_mapping.get(table_name, f"jaangle_exclude_{table_name}")
            
            # Verificar si la tabla existe
            self.cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{actual_table}'
            """)
            if not self.cursor.fetchone():
                print(f"Tabla {actual_table} no existe, creándola automáticamente")
                # Crear la tabla automáticamente si no existe
                self.cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {actual_table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.conn.commit()
                return []
            
            # Obtener los elementos
            self.cursor.execute(f"SELECT name FROM {actual_table} ORDER BY name")
            items = self.cursor.fetchall()
            result = [item[0] for item in items if item[0]]
            print(f"Elementos excluidos obtenidos de {actual_table}: {len(result)} elementos")
            return result
            
        except Exception as e:
            print(f"Error al obtener elementos excluidos de {table_name}: {e}")
            import traceback
            print(traceback.format_exc())
            return []

    def get_included_items(self, table_name):
        """
        Obtiene los elementos incluidos de la base de datos con prefijo jaangle_include_.
        
        Args:
            table_name (str): Nombre del tipo de tabla (ej: "included_decades")
            
        Returns:
            list: Lista de nombres de elementos incluidos
        """
        try:
            if not hasattr(self, 'cursor') or not self.cursor:
                print("Error: No database cursor available")
                return []
            
            # Mapear tipos de filtros a nombres de tabla con prefijo
            table_mapping = {
                "included_decades": "jaangle_include_decades",
                "included_years": "jaangle_include_years",
                "included_labels": "jaangle_include_labels",
                "included_countries": "jaangle_include_countries"
            }
            
            actual_table = table_mapping.get(table_name, f"jaangle_include_{table_name}")
            
            # Verificar si la tabla existe
            self.cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{actual_table}'
            """)
            if not self.cursor.fetchone():
                print(f"Tabla {actual_table} no existe, creándola automáticamente")
                # Crear la tabla automáticamente si no existe
                self.cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {actual_table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.conn.commit()
                return []
            
            # Obtener los elementos
            self.cursor.execute(f"SELECT name FROM {actual_table} ORDER BY name")
            items = self.cursor.fetchall()
            result = [item[0] for item in items if item[0]]
            print(f"Elementos incluidos obtenidos de {actual_table}: {len(result)} elementos")
            return result
            
        except Exception as e:
            print(f"Error al obtener elementos incluidos de {table_name}: {e}")
            import traceback
            print(traceback.print_exc())
            return []

    def initialize_jaangle_tables(self):
        """
        Inicializa todas las tablas de filtros de Jaangle si no existen.
        Debe llamarse durante la inicialización del módulo.
        """
        try:
            if not hasattr(self, 'cursor') or not self.cursor:
                print("Error: No database cursor available for table initialization")
                return False
            
            # Lista de todas las tablas de filtros que necesitamos
            filter_tables = [
                "jaangle_exclude_artists",
                "jaangle_exclude_albums", 
                "jaangle_exclude_genres",
                "jaangle_exclude_folders",
                "jaangle_exclude_decades",
                "jaangle_exclude_years",
                "jaangle_exclude_labels",
                "jaangle_exclude_countries",
                "jaangle_include_decades",
                "jaangle_include_years",
                "jaangle_include_labels", 
                "jaangle_include_countries"
            ]
            
            cursor = self.cursor
            conn = self.conn
            
            for table_name in filter_tables:
                try:
                    cursor.execute(f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL UNIQUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    print(f"Tabla {table_name} inicializada correctamente")
                except Exception as e:
                    print(f"Error inicializando tabla {table_name}: {e}")
            
            # Confirmar todos los cambios
            conn.commit()
            print("Todas las tablas de filtros Jaangle inicializadas correctamente")
            return True
            
        except Exception as e:
            print(f"Error inicializando tablas de filtros Jaangle: {e}")
            import traceback
            traceback.print_exc()
            return False

    def clear_all_jaangle_filters(self):
        """
        Limpia todos los filtros de Jaangle (útil para reset completo).
        """
        try:
            if not hasattr(self, 'cursor') or not self.cursor:
                print("Error: No database cursor available")
                return False
                
            # Lista de todas las tablas de filtros
            filter_tables = [
                "jaangle_exclude_artists",
                "jaangle_exclude_albums",
                "jaangle_exclude_genres", 
                "jaangle_exclude_folders",
                "jaangle_exclude_decades",
                "jaangle_exclude_years",
                "jaangle_exclude_labels",
                "jaangle_exclude_countries",
                "jaangle_include_decades",
                "jaangle_include_years",
                "jaangle_include_labels",
                "jaangle_include_countries"
            ]
            
            cursor = self.cursor
            conn = self.conn
            
            for table_name in filter_tables:
                try:
                    cursor.execute(f"DELETE FROM {table_name}")
                    print(f"Filtros limpiados de {table_name}")
                except Exception as e:
                    # Si la tabla no existe, simplemente continuar
                    print(f"Tabla {table_name} no existe o error al limpiar: {e}")
            
            conn.commit()
            print("Todos los filtros de Jaangle han sido limpiados")
            return True
            
        except Exception as e:
            print(f"Error limpiando filtros de Jaangle: {e}")
            return False

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
            dialog.setWindowTitle("Filtrar Carpetas")
            dialog.setMinimumWidth(600)
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
            
            # Si no se encuentra la columna folder_path en albums, buscar en songs
            if not folders:
                try:
                    self.cursor.execute("""
                        SELECT DISTINCT SUBSTR(file_path, 1, INSTR(file_path, '/') - 1) as folder_path
                        FROM songs 
                        WHERE file_path IS NOT NULL AND file_path LIKE '%/%'
                        ORDER BY folder_path
                    """)
                    folders = self.cursor.fetchall()
                except:
                    # Si también falla, extraer carpetas de las rutas de archivos
                    self.cursor.execute("""
                        SELECT DISTINCT file_path
                        FROM songs 
                        WHERE file_path IS NOT NULL
                        ORDER BY file_path
                    """)
                    file_paths = self.cursor.fetchall()
                    folder_set = set()
                    for (file_path,) in file_paths:
                        if file_path and '/' in file_path:
                            folder = '/'.join(file_path.split('/')[:-1])
                            if folder:
                                folder_set.add(folder)
                    folders = [(folder,) for folder in sorted(folder_set)]
            
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
            
            dialog.exec()
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar carpetas: {e}")
            import traceback
            traceback.print_exc()
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
                        return
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
            
            # NUEVO: Sincronizar con radio buttons del diálogo avanzado si existe
            self.sync_advanced_dialog_radio_buttons()
            
            # NUEVO: Guardar configuración automáticamente
            self.save_config()
                
        except Exception as e:
            print(f"Error en on_music_origin_changed: {e}")
            import traceback
            traceback.print_exc()

    def sync_advanced_dialog_radio_buttons(self):
        """Sincroniza los radio buttons del diálogo avanzado con la configuración actual."""
        try:
            # Esta función se llamará para mantener sincronizados los radio buttons
            # No necesita hacer nada específico aquí, pero permite extensibilidad futura
            pass
        except Exception as e:
            print(f"Error sincronizando radio buttons del diálogo: {e}")


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
        """Guarda la configuración actual a un archivo (versión mejorada)."""
        try:
            # Guardar la configuración general (código existente...)
            result = super().save_config() if hasattr(super(), 'save_config') else True
            
            # NUEVO: Guardar también la configuración del jugador actual
            if hasattr(self, 'advanced_config') and self.advanced_config.get_current_player():
                self.advanced_config.save_current_player_config()
            
            return result
            
        except Exception as e:
            print(f"Error al guardar configuración: {e}")
            return False

    def add_advanced_settings_button(self):
        """Añade un botón para acceder a la configuración avanzada en la UI principal."""
        try:
            # Buscar el grupo de configuración existente
            if hasattr(self, 'config_group'):
                config_layout = self.config_group.layout()
                if config_layout:
                    # Crear botón para configuración avanzada
                    advanced_btn = QPushButton("Configuración Avanzada...")
                    advanced_btn.clicked.connect(self.show_advanced_settings_dialog)
                    
                    # Añadir al layout de configuración
                    config_layout.addWidget(advanced_btn)
                    
                    print("Botón de configuración avanzada añadido")
                    return True
                else:
                    print("No se encontró layout de configuración")
            else:
                print("No se encontró grupo de configuración")
                
        except Exception as e:
            print(f"Error al añadir botón de configuración avanzada: {e}")
            return False

    
    def load_config(self):
        """Carga la configuración desde un archivo (versión mejorada)."""
        try:
            import json
            from pathlib import Path
            from PyQt6.QtCore import Qt
            
            config_path = Path(PROJECT_ROOT, "config", "jaangle", "config.json")
            if not config_path.exists():
                print(f"Archivo de configuración no encontrado: {config_path}")
                # Establecer valores por defecto para configuración avanzada
                self.set_advanced_defaults()
                return False
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            print(f"Cargando configuración desde: {config_path}")
            
            # Aplicar configuración básica cargada
            if "option_hotkeys" in config_data:
                # Convertir hotkeys de vuelta a objetos Qt.Key
                loaded_hotkeys = {}
                for option_str, key_value in config_data["option_hotkeys"].items():
                    option_index = int(option_str)
                    # Crear el objeto Qt.Key desde el valor numérico
                    qt_key = Qt.Key(key_value)
                    loaded_hotkeys[option_index] = qt_key
                self.option_hotkeys = loaded_hotkeys
                print(f"Hotkeys cargadas: {self.option_hotkeys}")
                
            if "music_origin" in config_data:
                self.music_origin = config_data["music_origin"]
            if "spotify_user" in config_data:
                self.spotify_user = config_data["spotify_user"]
            if "listenbrainz_user" in config_data:
                self.listenbrainz_user = config_data["listenbrainz_user"]
            if "quiz_duration_minutes" in config_data:
                self.quiz_duration_minutes = int(float(str(config_data["quiz_duration_minutes"])))
            if "song_duration_seconds" in config_data:
                self.song_duration_seconds = int(float(str(config_data["song_duration_seconds"])))
            if "pause_between_songs" in config_data:
                self.pause_between_songs = int(float(str(config_data["pause_between_songs"])))
            if "options_count" in config_data:
                self.options_count = int(float(str(config_data["options_count"])))
            if "min_song_duration" in config_data:
                self.min_song_duration = int(float(str(config_data["min_song_duration"])))
            if "start_from_beginning_chance" in config_data:
                self.start_from_beginning_chance = float(str(config_data["start_from_beginning_chance"]))
            if "avoid_last_seconds" in config_data:
                self.avoid_last_seconds = int(float(str(config_data["avoid_last_seconds"])))
                
            # Cargar configuración avanzada
            self.load_advanced_config_from_data(config_data)
            
            # Actualizar UI con valores cargados
            self.update_ui_from_config()
            
            print("Configuración cargada correctamente")
            return True
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
            import traceback
            traceback.print_exc()
            # Establecer valores por defecto en caso de error
            self.set_advanced_defaults()
            return False

    def load_advanced_config_from_data(self, config_data):
        """Carga la configuración avanzada desde los datos del archivo."""
        try:
            # Configuración de Spotify
            self.spotify_auto_login = config_data.get("spotify_auto_login", False)
            
            # Configuración Online
            self.preferred_online_source = config_data.get("preferred_online_source", "youtube")
            
            # Configuración de UI
            self.min_font_size = int(float(str(config_data.get("min_font_size", 8))))
            self.max_font_size = int(float(str(config_data.get("max_font_size", 16))))
            self.show_album_art = config_data.get("show_album_art", True)
            self.show_progress_details = config_data.get("show_progress_details", True)
            
            # Configuración de base de datos
            if "db_path" in config_data and config_data["db_path"]:
                new_db_path = Path(config_data["db_path"])
                if new_db_path.exists():
                    self.db_path = new_db_path
                else:
                    print(f"Advertencia: La base de datos configurada no existe: {new_db_path}")
            
            # Configuración de rendimiento
            self.cache_size = int(float(str(config_data.get("cache_size", 200))))
            self.preload_songs = int(float(str(config_data.get("preload_songs", 5))))
            self.auto_backup = config_data.get("auto_backup", False)
            self.enable_debug = config_data.get("enable_debug", False)
            
            # Aplicar configuraciones que requieren acción inmediata
            if hasattr(self, 'enable_debug') and self.enable_debug:
                import logging
                logging.getLogger(__name__).setLevel(logging.DEBUG)
                print("Modo debug habilitado")
            
        except Exception as e:
            print(f"Error al cargar configuración avanzada: {e}")
            self.set_advanced_defaults()

    def set_advanced_defaults(self):
        """Establece los valores por defecto para la configuración avanzada."""
        try:
            # Configuración de Spotify
            self.spotify_auto_login = False
            
            # Configuración Online
            self.preferred_online_source = "youtube"
            
            # Configuración de UI
            self.min_font_size = 8
            self.max_font_size = 16
            self.show_album_art = True
            self.show_progress_details = True
            
            # Configuración de rendimiento
            self.cache_size = 200
            self.preload_songs = 5
            self.auto_backup = False
            self.enable_debug = False
            
            print("Configuración avanzada establecida a valores por defecto")
            
        except Exception as e:
            print(f"Error al establecer valores por defecto: {e}")

    def get_key_display_name(self, qt_key):
        """Obtiene el nombre descriptivo de una tecla Qt."""
        try:
            # Mapear las teclas más comunes a nombres legibles
            key_names = {
                Qt.Key.Key_1: "1",
                Qt.Key.Key_2: "2", 
                Qt.Key.Key_3: "3",
                Qt.Key.Key_4: "4",
                Qt.Key.Key_5: "5",
                Qt.Key.Key_6: "6",
                Qt.Key.Key_7: "7",
                Qt.Key.Key_8: "8",
                Qt.Key.Key_A: "A",
                Qt.Key.Key_B: "B",
                Qt.Key.Key_C: "C",
                Qt.Key.Key_D: "D",
                Qt.Key.Key_E: "E",
                Qt.Key.Key_F: "F",
                Qt.Key.Key_G: "G",
                Qt.Key.Key_H: "H",
                Qt.Key.Key_I: "I",
                Qt.Key.Key_J: "J",
                Qt.Key.Key_K: "K",
                Qt.Key.Key_L: "L",
                Qt.Key.Key_M: "M",
                Qt.Key.Key_N: "N",
                Qt.Key.Key_O: "O",
                Qt.Key.Key_P: "P",
                Qt.Key.Key_Q: "Q",
                Qt.Key.Key_R: "R",
                Qt.Key.Key_S: "S",
                Qt.Key.Key_T: "T",
                Qt.Key.Key_U: "U",
                Qt.Key.Key_V: "V",
                Qt.Key.Key_W: "W",
                Qt.Key.Key_X: "X",
                Qt.Key.Key_Y: "Y",
                Qt.Key.Key_Z: "Z",
                Qt.Key.Key_Space: "Espacio",
                Qt.Key.Key_Return: "Enter",
                Qt.Key.Key_Enter: "Enter",
                Qt.Key.Key_Escape: "Escape",
                Qt.Key.Key_Tab: "Tab",
                Qt.Key.Key_Backspace: "Backspace"
            }
            
            return key_names.get(qt_key, f"Tecla {qt_key.value}")
        except:
            return f"Tecla {qt_key}"

    def show_hotkey_config_dialog(self):
        """Muestra un diálogo para configurar las hotkeys de las opciones."""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QPushButton, QLabel, QHBoxLayout
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
                key_text = self.get_key_display_name(current_key)
                
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
                    new_hotkeys[capturing_for] = Qt.Key(key)
                    
                    # Actualizar el texto del botón
                    button = hotkey_buttons[capturing_for]
                    key_text = self.get_key_display_name(Qt.Key(key))
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
                    key_text = self.get_key_display_name(key)
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
                print(f"Nuevas hotkeys configuradas: {self.option_hotkeys}")
                # Guardar automáticamente
                self.save_config()
                return True
            
            return False
            
        except Exception as e:
            print(f"Error al mostrar el diálogo de configuración de hotkeys: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")
            return False

    def update_ui_from_config(self):
        """Actualiza la UI con los valores de configuración cargados."""
        try:
            # Código existente para combos...
            if hasattr(self, 'quiz_duration_combo'):
                for i in range(self.quiz_duration_combo.count()):
                    if int(self.quiz_duration_combo.itemText(i).split()[0]) == self.quiz_duration_minutes:
                        self.quiz_duration_combo.setCurrentIndex(i)
                        break
            
            if hasattr(self, 'song_duration_combo'):
                for i in range(self.song_duration_combo.count()):
                    if int(self.song_duration_combo.itemText(i).split()[0]) == self.song_duration_seconds:
                        self.song_duration_combo.setCurrentIndex(i)
                        break
            
            if hasattr(self, 'pause_duration_combo'):
                for i in range(self.pause_duration_combo.count()):
                    if int(self.pause_duration_combo.itemText(i).split()[0]) == self.pause_between_songs:
                        self.pause_duration_combo.setCurrentIndex(i)
                        break
            
            if hasattr(self, 'options_count_combo'):
                for i in range(self.options_count_combo.count()):
                    if int(self.options_count_combo.itemText(i)) == self.options_count:
                        self.options_count_combo.setCurrentIndex(i)
                        break
            
            # ACTUALIZADO: Actualizar radio buttons de origen de música con sincronización mejorada
            if hasattr(self, 'local_radio') and hasattr(self, 'spotify_radio') and hasattr(self, 'listenbrainz_radio'):
                # Desconectar temporalmente las señales
                try:
                    self.local_radio.toggled.disconnect()
                    if hasattr(self, 'spotify_radio'):
                        self.spotify_radio.toggled.disconnect()
                    self.listenbrainz_radio.toggled.disconnect()
                except TypeError:
                    pass  # Las señales no estaban conectadas
                
                # Actualizar según la configuración
                if self.music_origin == 'spotify':
                    self.spotify_radio.setChecked(True)
                    self.local_radio.setChecked(False)
                    self.listenbrainz_radio.setChecked(False)
                elif self.music_origin == 'online':
                    self.listenbrainz_radio.setChecked(True)
                    self.local_radio.setChecked(False)
                    if hasattr(self, 'spotify_radio'):
                        self.spotify_radio.setChecked(False)
                else:  # local
                    self.local_radio.setChecked(True)
                    self.listenbrainz_radio.setChecked(False)
                    if hasattr(self, 'spotify_radio'):
                        self.spotify_radio.setChecked(False)
                
                # Reconectar las señales
                self.local_radio.toggled.connect(self.on_music_origin_changed)
                if hasattr(self, 'spotify_radio'):
                    self.spotify_radio.toggled.connect(self.on_music_origin_changed)
                self.listenbrainz_radio.toggled.connect(self.on_music_origin_changed)
            
            print("UI actualizada con la configuración cargada")
        except Exception as e:
            print(f"Error al actualizar UI desde configuración: {e}")
            import traceback
            traceback.print_exc()


    def add_config_change_handlers(self):
        """Añade handlers para guardar automáticamente cuando cambia la configuración."""
        try:
            # Conectar señales de cambio en los combos
            if hasattr(self, 'quiz_duration_combo'):
                self.quiz_duration_combo.currentIndexChanged.connect(self.on_config_changed)
            if hasattr(self, 'song_duration_combo'):
                self.song_duration_combo.currentIndexChanged.connect(self.on_config_changed)
            if hasattr(self, 'pause_duration_combo'):
                self.pause_duration_combo.currentIndexChanged.connect(self.on_config_changed)
            if hasattr(self, 'options_count_combo'):
                self.options_count_combo.currentIndexChanged.connect(self.on_config_changed)
            
            # Conectar señales de los radio buttons (ya están conectadas en on_music_origin_changed)
            if hasattr(self, 'local_radio'):
                self.local_radio.toggled.connect(self.on_config_changed)
            if hasattr(self, 'spotify_radio'):
                self.spotify_radio.toggled.connect(self.on_config_changed)
            if hasattr(self, 'listenbrainz_radio'):
                self.listenbrainz_radio.toggled.connect(self.on_config_changed)
                
            print("Handlers de configuración añadidos")
        except Exception as e:
            print(f"Error al añadir handlers de configuración: {e}")

    def on_config_changed(self):
        """Maneja cambios en la configuración y guarda automáticamente."""
        try:
            # Pequeño delay para evitar guardar múltiples veces seguidas
            if not hasattr(self, 'config_save_timer'):
                self.config_save_timer = QTimer()
                self.config_save_timer.setSingleShot(True)
                self.config_save_timer.timeout.connect(self.save_config)
            
            self.config_save_timer.start(1000)  # Guardar después de 1 segundo de inactividad
        except Exception as e:
            print(f"Error en on_config_changed: {e}")


# ADVANCED SETTINGS

    def show_advanced_settings_dialog(self):
        """Muestra el diálogo de configuración avanzada."""
        try:
            from PyQt6 import uic
            from PyQt6.QtWidgets import QDialog, QFileDialog
            
            dialog = QDialog(self)
            
            # Cargar la UI del diálogo
            dialog_ui_path = Path(PROJECT_ROOT, "ui", "jaangle", "jaangle_advanced_settings_dialog.ui")
            
            if os.path.exists(dialog_ui_path):
                print("Cargando UI del diálogo...")
                uic.loadUi(dialog_ui_path, dialog)
                
                print("UI cargada, iniciando carga de configuración...")
                # Cargar valores actuales en la UI
                self.load_advanced_settings_to_ui(dialog)
                
                print("Configuración cargada, conectando señales...")
                # Conectar señales
                self.connect_advanced_settings_signals(dialog)
                
                print("Mostrando diálogo...")
                # Mostrar el diálogo
                result = dialog.exec()
                
                if result == QDialog.DialogCode.Accepted:
                    # Aplicar cambios
                    self.apply_advanced_settings_from_ui(dialog)
                    # Guardar configuración
                    self.save_config()
                    return True
            else:
                self.show_error_message("Error", f"No se encontró el archivo UI: {dialog_ui_path}")
                
        except Exception as e:
            print(f"Error al mostrar configuración avanzada: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_message("Error", f"Error al mostrar configuración avanzada: {e}")
        
        return False
    def safe_int_conversion(self, value, default=0):
        """Convierte un valor a entero de forma segura."""
        try:
            if value is None:
                return default
            # Si es string, verificar si contiene punto decimal
            if isinstance(value, str) and '.' in value:
                return int(float(value))
            # Convertir directamente a float primero, luego a int
            return int(float(value))
        except (ValueError, TypeError):
            print(f"Advertencia: No se pudo convertir '{value}' a entero, usando valor por defecto: {default}")
            return default

    def safe_float_conversion(self, value, default=0.0):
        """Convierte un valor a float de forma segura."""
        try:
            if value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            print(f"Advertencia: No se pudo convertir '{value}' a float, usando valor por defecto: {default}")
            return default


    def load_advanced_settings_to_ui(self, dialog):
        """Carga los valores actuales de configuración en la UI del diálogo."""
        try:
            print("Iniciando carga de configuración avanzada...")
            
            # Configuración de reproducción - usar conversiones seguras
            print("Configurando min_duration_spin...")
            min_duration_value = self.safe_int_conversion(getattr(self, 'min_song_duration', 60), 60)
            dialog.min_duration_spin.setValue(min_duration_value)
            
            print("Configurando avoid_last_spin...")
            avoid_last_value = self.safe_int_conversion(getattr(self, 'avoid_last_seconds', 15), 15)
            dialog.avoid_last_spin.setValue(avoid_last_value)
            
            print("Configurando beginning_chance_spin...")
            beginning_chance_value = self.safe_float_conversion(getattr(self, 'start_from_beginning_chance', 0.3), 0.3) * 100
            dialog.beginning_chance_spin.setValue(beginning_chance_value)
            
            # NUEVO: Configurar spinboxes de penalización/premio
            print("Configurando penalizaciones y premios...")
            penalty_value = self.safe_int_conversion(self.advanced_config.get_penalty_seconds(), 60)
            dialog.min_penal_spin.setValue(penalty_value)
            
            reward_value = self.safe_int_conversion(self.advanced_config.get_reward_seconds(), 60)
            dialog.min_premio_spin.setValue(reward_value)
            
            favorite_penalty_value = self.safe_int_conversion(self.advanced_config.get_favorite_penalty_seconds(), 60)
            dialog.min_multa_spin.setValue(favorite_penalty_value)
            
            # NUEVO: Configurar radio buttons de origen de música
            print("Configurando radio buttons de origen...")
            current_origin = getattr(self, 'music_origin', 'local')
            if hasattr(dialog, 'local_radio') and hasattr(dialog, 'listenbrainz_radio'):
                if current_origin == 'online':
                    dialog.listenbrainz_radio.setChecked(True)
                    dialog.local_radio.setChecked(False)
                else:
                    dialog.local_radio.setChecked(True)
                    dialog.listenbrainz_radio.setChecked(False)
                print(f"Radio buttons configurados para: {current_origin}")
            else:
                print("Advertencia: Radio buttons no encontrados en el diálogo")
            
            # NUEVO: Configurar combobox de jugadores  
            print("Configurando combobox de jugadores...")
            self.populate_player_combo(dialog.player_comboBox)
            
            # Configuración Online/ListenBrainz
            print("Configurando Online/ListenBrainz...")
            if hasattr(self, 'listenbrainz_user') and self.listenbrainz_user:
                dialog.listenbrainz_user_edit.setText(str(self.listenbrainz_user))
            
            # Configuración de UI - usar conversiones seguras
            print("Configurando UI...")
            min_font_value = self.safe_int_conversion(getattr(self, 'min_font_size', 8), 8)
            dialog.min_font_size_spin.setValue(min_font_value)
            
            max_font_value = self.safe_int_conversion(getattr(self, 'max_font_size', 16), 16)
            dialog.max_font_size_spin.setValue(max_font_value)
            
            # Configuración de base de datos
            print("Configurando base de datos...")
            if hasattr(self, 'db_path') and self.db_path:
                dialog.db_path_edit.setText(str(self.db_path))
            
            # Configuración de rendimiento - usar conversiones seguras
            print("Configurando rendimiento...")
            cache_size_value = self.safe_int_conversion(getattr(self, 'cache_size', 200), 200)
            dialog.cache_size_spin.setValue(cache_size_value)
            
            preload_value = self.safe_int_conversion(getattr(self, 'preload_songs', 5), 5)
            dialog.preload_songs_spin.setValue(preload_value)
            
            # Checkboxes
            print("Configurando checkboxes...")
            dialog.show_album_art_check.setChecked(getattr(self, 'show_album_art', True))
            dialog.show_progress_details_check.setChecked(getattr(self, 'show_progress_details', True))
            dialog.auto_backup_check.setChecked(getattr(self, 'auto_backup', False))
            dialog.enable_debug_check.setChecked(getattr(self, 'enable_debug', False))
            
            print("Configuración avanzada cargada correctamente")
            
        except Exception as e:
            print(f"Error al cargar configuración avanzada en UI: {e}")
            import traceback
            traceback.print_exc()



    def connect_advanced_settings_signals(self, dialog):
        """Conecta las señales del diálogo de configuración avanzada."""
        try:
            # Código existente...
            dialog.browse_db_btn.clicked.connect(lambda: self.browse_database_path(dialog))
            
            # Conectar botones de filtros
            dialog.filter_artists_btn.clicked.connect(self.show_artist_filter_dialog)
            dialog.filter_albums_btn.clicked.connect(self.show_album_filter_dialog)
            dialog.filter_genres_btn.clicked.connect(self.show_genre_filter_dialog)
            dialog.filter_folders_btn.clicked.connect(self.show_folder_filter_dialog)
            dialog.filter_sellos_btn.clicked.connect(self.show_sellos_filter_dialog)
            dialog.session_filters_btn.clicked.connect(self.show_session_filter_dialog)
            dialog.clear_session_btn.clicked.connect(lambda: self.clear_session_filters_and_update_status(dialog))
            
            # Conectar botón de hotkeys
            dialog.configure_hotkeys_btn.clicked.connect(self.show_hotkey_config_dialog)
            
            # Conectar combobox de jugadores
            dialog.player_comboBox.currentTextChanged.connect(lambda: self.on_player_combo_changed(dialog.player_comboBox))
            
            # Conectar spinboxes de penalización/premio a funciones de actualización
            dialog.min_penal_spin.valueChanged.connect(lambda val: self.advanced_config.set_penalty_seconds(val))
            dialog.min_premio_spin.valueChanged.connect(lambda val: self.advanced_config.set_reward_seconds(val))
            dialog.min_multa_spin.valueChanged.connect(lambda val: self.advanced_config.set_favorite_penalty_seconds(val))
            
            # NUEVO: Conectar radio buttons de origen de música del diálogo avanzado
            if hasattr(dialog, 'local_radio') and hasattr(dialog, 'listenbrainz_radio'):
                dialog.local_radio.toggled.connect(lambda: self.on_advanced_music_origin_changed(dialog))
                dialog.listenbrainz_radio.toggled.connect(lambda: self.on_advanced_music_origin_changed(dialog))
                print("Radio buttons del diálogo avanzado conectados")
            
            # Actualizar estado de filtros de sesión
            self.update_session_status_in_dialog(dialog)
            
            # Conectar botón de restaurar valores por defecto
            if hasattr(dialog.button_box, 'button'):
                restore_btn = dialog.button_box.button(dialog.button_box.StandardButton.RestoreDefaults)
                if restore_btn:
                    restore_btn.clicked.connect(lambda: self.restore_advanced_defaults(dialog))
            
            # Conectar botón de aplicar
            if hasattr(dialog.button_box, 'button'):
                apply_btn = dialog.button_box.button(dialog.button_box.StandardButton.Apply)
                if apply_btn:
                    apply_btn.clicked.connect(lambda: self.apply_advanced_settings_from_ui(dialog))

            self.connect_new_filter_buttons(dialog)

        except Exception as e:
            print(f"Error al conectar señales de configuración avanzada: {e}")



    def on_advanced_music_origin_changed(self, dialog):
        """Maneja el cambio de origen de música desde el diálogo avanzado."""
        try:
            if not hasattr(dialog, 'local_radio') or not hasattr(dialog, 'listenbrainz_radio'):
                print("Radio buttons no encontrados en el diálogo")
                return
            
            # Determinar qué radio button está seleccionado
            if dialog.local_radio.isChecked():
                self.music_origin = 'local'
                print("Origen de música cambiado a: Local (desde diálogo avanzado)")
                
                # Ocultar reproductores online si están visibles
                if hasattr(self, 'listenbrainz_container') and self.listenbrainz_container:
                    self.listenbrainz_container.hide()
                if hasattr(self, 'spotify_container') and self.spotify_container:
                    self.spotify_container.hide()
                    
            elif dialog.listenbrainz_radio.isChecked():
                self.music_origin = 'online'
                print("Origen de música cambiado a: Online (desde diálogo avanzado)")
                
                # Ocultar contenedor de Spotify si está visible
                if hasattr(self, 'spotify_container') and self.spotify_container:
                    self.spotify_container.hide()
            
            # Sincronizar con radio buttons principales
            self.sync_main_radio_buttons()
            
            # Guardar la configuración automáticamente
            self.save_config()
            
        except Exception as e:
            print(f"Error en on_advanced_music_origin_changed: {e}")
            import traceback
            traceback.print_exc()

    def sync_main_radio_buttons(self):
        """Sincroniza los radio buttons principales con la configuración actual."""
        try:
            # Actualizar los radio buttons principales si existen
            if hasattr(self, 'local_radio') and hasattr(self, 'listenbrainz_radio'):
                # Desconectar temporalmente las señales para evitar bucles
                self.local_radio.toggled.disconnect()
                self.listenbrainz_radio.toggled.disconnect()
                
                if self.music_origin == 'local':
                    self.local_radio.setChecked(True)
                    self.listenbrainz_radio.setChecked(False)
                elif self.music_origin == 'online':
                    self.listenbrainz_radio.setChecked(True)
                    self.local_radio.setChecked(False)
                
                # Reconectar las señales
                self.local_radio.toggled.connect(self.on_music_origin_changed)
                self.listenbrainz_radio.toggled.connect(self.on_music_origin_changed)
                
                print(f"Radio buttons principales sincronizados para: {self.music_origin}")
                
        except Exception as e:
            print(f"Error sincronizando radio buttons principales: {e}")


    def clear_session_filters_and_update_status(self, dialog):
        """Limpia los filtros de sesión y actualiza el estado en el diálogo."""
        self.clear_session_filters()
        self.update_session_status_in_dialog(dialog)

    def update_session_status_in_dialog(self, dialog):
        """Actualiza el estado de los filtros de sesión en el diálogo."""
        try:
            if hasattr(self, 'session_filters') and self.session_filters:
                # Contar filtros activos
                filters = self.session_filters.get('filters', {})
                total_filters = sum(len(items) for items in filters.values() if items)
                
                if total_filters > 0:
                    session_name = self.session_filters.get('name', 'Sesión sin nombre')
                    dialog.session_status_label.setText(f"Filtros activos: {session_name} ({total_filters} elementos)")
                    dialog.session_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                else:
                    dialog.session_status_label.setText("Estado de filtros: Sin filtros activos")
                    dialog.session_status_label.setStyleSheet("color: #666; font-style: italic;")
            else:
                dialog.session_status_label.setText("Estado de filtros: Sin filtros activos")
                dialog.session_status_label.setStyleSheet("color: #666; font-style: italic;")
        except Exception as e:
            print(f"Error al actualizar estado de sesión: {e}")


    def browse_database_path(self, dialog):
        """Permite al usuario seleccionar la ruta de la base de datos."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getOpenFileName(
                dialog,
                "Seleccionar Base de Datos",
                str(Path.home()),
                "Archivos de Base de Datos (*.db *.sqlite *.sqlite3);;Todos los archivos (*)"
            )
            
            if file_path:
                dialog.db_path_edit.setText(file_path)
                
        except Exception as e:
            print(f"Error al examinar ruta de base de datos: {e}")

    def restore_advanced_defaults(self, dialog):
        """Restaura los valores por defecto de la configuración avanzada."""
        try:
            # Valores por defecto de reproducción
            dialog.min_duration_spin.setValue(60)
            dialog.avoid_last_spin.setValue(15)
            dialog.beginning_chance_spin.setValue(30.0)
            
            # NUEVO: Valores por defecto de penalizaciones/premios
            dialog.min_penal_spin.setValue(3)
            dialog.min_premio_spin.setValue(1)
            dialog.min_multa_spin.setValue(10)
            
            # Limpiar campos de usuario
            dialog.spotify_user_edit.clear()
            dialog.listenbrainz_user_edit.clear()
            
            # Valores por defecto de UI
            dialog.min_font_size_spin.setValue(8)
            dialog.max_font_size_spin.setValue(16)
            
            # Valores por defecto de rendimiento
            dialog.cache_size_spin.setValue(200)
            dialog.preload_songs_spin.setValue(5)
            
            # Checkboxes por defecto
            dialog.show_album_art_check.setChecked(True)
            dialog.show_progress_details_check.setChecked(True)
            dialog.auto_backup_check.setChecked(False)
            dialog.spotify_auto_login_check.setChecked(False)
            dialog.enable_debug_check.setChecked(False)
            
            # Fuente online por defecto
            dialog.online_source_combo.setCurrentIndex(0)  # YouTube
            
            # NUEVO: Restablecer jugador
            dialog.player_comboBox.setCurrentIndex(0)  # "Añadir nuevo jugador..."
            
        except Exception as e:
            print(f"Error al restaurar valores por defecto: {e}")

    def apply_advanced_settings_from_ui(self, dialog):
        """Aplica la configuración avanzada desde la UI."""
        try:
            # Configuración de reproducción
            self.min_song_duration = dialog.min_duration_spin.value()
            self.avoid_last_seconds = dialog.avoid_last_spin.value()
            self.start_from_beginning_chance = dialog.beginning_chance_spin.value() / 100.0
            
            # NUEVO: Aplicar configuración de penalizaciones/premios
            self.advanced_config.set_penalty_seconds(dialog.min_penal_spin.value())
            self.advanced_config.set_reward_seconds(dialog.min_premio_spin.value())
            self.advanced_config.set_favorite_penalty_seconds(dialog.min_multa_spin.value())
            
            # NUEVO: Aplicar configuración de origen de música desde radio buttons
            if hasattr(dialog, 'local_radio') and hasattr(dialog, 'listenbrainz_radio'):
                if dialog.local_radio.isChecked():
                    self.music_origin = 'local'
                elif dialog.listenbrainz_radio.isChecked():
                    self.music_origin = 'online'
                print(f"Origen de música aplicado: {self.music_origin}")
            
            # Configuración Online/ListenBrainz
            self.listenbrainz_user = dialog.listenbrainz_user_edit.text().strip() or None
            self.preferred_online_source = dialog.online_source_combo.currentText().lower()
            
            # Configuración de UI
            self.min_font_size = dialog.min_font_size_spin.value()
            self.max_font_size = dialog.max_font_size_spin.value()
            self.show_album_art = dialog.show_album_art_check.isChecked()
            self.show_progress_details = dialog.show_progress_details_check.isChecked()
            
            # Configuración de base de datos
            new_db_path = dialog.db_path_edit.text().strip()
            if new_db_path and new_db_path != str(self.db_path):
                # Cambiar base de datos requiere reconexión
                self.change_database_path(new_db_path)
            
            # Configuración de rendimiento
            self.cache_size = dialog.cache_size_spin.value()
            self.preload_songs = dialog.preload_songs_spin.value()
            self.auto_backup = dialog.auto_backup_check.isChecked()
            self.enable_debug = dialog.enable_debug_check.isChecked()
            
            # Aplicar cambios inmediatos en la UI
            self.apply_ui_changes()
            
            # NUEVO: Guardar configuración del jugador actual
            if hasattr(self, 'advanced_config'):
                self.advanced_config.save_current_player_config()
            
            print("Configuración avanzada aplicada correctamente")
            
        except Exception as e:
            print(f"Error al aplicar configuración avanzada: {e}")
            self.show_error_message("Error", f"Error al aplicar configuración: {e}")


    def change_database_path(self, new_path):
        """Cambia la ruta de la base de datos y reconecta."""
        try:
            # Cerrar conexión actual
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
            
            # Establecer nueva ruta
            self.db_path = Path(new_path)
            
            # Reconectar
            self.connect_to_database()
            
            print(f"Base de datos cambiada a: {self.db_path}")
            
        except Exception as e:
            print(f"Error al cambiar base de datos: {e}")
            self.show_error_message("Error", f"Error al cambiar base de datos: {e}")

    def apply_ui_changes(self):
        """Aplica cambios inmediatos en la interfaz de usuario."""
        try:
            # Actualizar tamaños de fuente en los labels escalables
            if hasattr(self, 'option_buttons'):
                for button in self.option_buttons:
                    if hasattr(button, 'song_label') and hasattr(button.song_label, 'set_font_range'):
                        button.song_label.set_font_range(self.min_font_size, self.max_font_size)
                    if hasattr(button, 'artist_label') and hasattr(button.artist_label, 'set_font_range'):
                        button.artist_label.set_font_range(self.min_font_size, self.max_font_size)
                    if hasattr(button, 'album_label') and hasattr(button.album_label, 'set_font_range'):
                        button.album_label.set_font_range(self.min_font_size, self.max_font_size)
            
            # Configurar modo debug
            if hasattr(self, 'enable_debug') and self.enable_debug:
                import logging
                logging.getLogger(__name__).setLevel(logging.DEBUG)
            else:
                import logging
                logging.getLogger(__name__).setLevel(logging.INFO)
            
        except Exception as e:
            print(f"Error al aplicar cambios de UI: {e}")

    def save_advanced_config(self):
        """Guarda la configuración avanzada adicional al archivo de configuración."""
        try:
            # Extender el método save_config existente para incluir configuración avanzada
            config_data = {
                # Configuración básica (ya existente)
                "option_hotkeys": getattr(self, 'option_hotkeys', {}),
                "music_origin": getattr(self, 'music_origin', 'local'),
                "spotify_user": getattr(self, 'spotify_user', None),
                "listenbrainz_user": getattr(self, 'listenbrainz_user', None),
                "quiz_duration_minutes": getattr(self, 'quiz_duration_minutes', 5),
                "song_duration_seconds": getattr(self, 'song_duration_seconds', 30),
                "pause_between_songs": getattr(self, 'pause_between_songs', 5),
                "options_count": getattr(self, 'options_count', 4),
                "min_song_duration": getattr(self, 'min_song_duration', 60),
                "start_from_beginning_chance": getattr(self, 'start_from_beginning_chance', 0.3),
                "avoid_last_seconds": getattr(self, 'avoid_last_seconds', 15),
                
                # Configuración avanzada nueva
                "spotify_auto_login": getattr(self, 'spotify_auto_login', False),
                "preferred_online_source": getattr(self, 'preferred_online_source', 'youtube'),
                "min_font_size": getattr(self, 'min_font_size', 8),
                "max_font_size": getattr(self, 'max_font_size', 16),
                "show_album_art": getattr(self, 'show_album_art', True),
                "show_progress_details": getattr(self, 'show_progress_details', True),
                "cache_size": getattr(self, 'cache_size', 200),
                "preload_songs": getattr(self, 'preload_songs', 5),
                "auto_backup": getattr(self, 'auto_backup', False),
                "enable_debug": getattr(self, 'enable_debug', False),
            }
            
            # Agregar ruta de base de datos si existe
            if hasattr(self, 'db_path') and self.db_path:
                config_data["db_path"] = str(self.db_path)
            
            return config_data
            
        except Exception as e:
            print(f"Error al preparar configuración avanzada: {e}")
            return {}


# PREMIOS Y PENALIZACIONES 

    def apply_time_adjustment(self, is_correct, song_id=None):
        """
        Aplica ajuste de tiempo basado en respuesta correcta/incorrecta y si es favorita.
        
        Args:
            is_correct (bool): Si la respuesta fue correcta
            song_id: ID de la canción (opcional, usa la actual si no se proporciona)
        """
        try:
            # Usar la canción actual si no se proporciona ID
            if song_id is None:
                song_id = self.current_song_id
            
            if not song_id:
                print("No hay ID de canción para aplicar ajuste de tiempo")
                return
            
            # Verificar si es favorita
            is_favorite = self.advanced_config.is_song_favorite(song_id)
            
            # Calcular ajuste de tiempo
            time_adjustment = self.advanced_config.calculate_time_adjustment(is_correct, is_favorite)
            
            # Aplicar el ajuste al tiempo restante del quiz total
            if hasattr(self, 'remaining_total_time'):
                self.remaining_total_time += time_adjustment
                
                # Asegurar que no sea negativo
                if self.remaining_total_time < 0:
                    self.remaining_total_time = 0
                
                # Mostrar notificación del ajuste
                self.show_time_adjustment_notification(time_adjustment, is_favorite, is_correct)
                
                print(f"Ajuste de tiempo aplicado: {time_adjustment}s (Favorita: {is_favorite}, Correcta: {is_correct})")
            
        except Exception as e:
            print(f"Error aplicando ajuste de tiempo: {e}")
            import traceback
            traceback.print_exc()

    def show_time_adjustment_notification(self, adjustment_seconds, is_favorite, is_correct):
        """
        Muestra una notificación visual del ajuste de tiempo.
        
        Args:
            adjustment_seconds (int): Segundos añadidos (positivo) o quitados (negativo)
            is_favorite (bool): Si la canción era favorita
            is_correct (bool): Si la respuesta fue correcta
        """
        try:
            # Crear mensaje de notificación
            if is_correct:
                message = f"¡Correcto! +{adjustment_seconds}s"
                style = "color: #4CAF50; font-weight: bold;"
            else:
                if is_favorite:
                    message = f"¡Fallaste una favorita! {adjustment_seconds}s"
                    style = "color: #f44336; font-weight: bold;"
                else:
                    message = f"Incorrecto {adjustment_seconds}s"
                    style = "color: #FF9800; font-weight: bold;"
            
            # Mostrar en un label temporal
            if hasattr(self, 'countdown_label'):
                original_text = self.countdown_label.text()
                original_style = self.countdown_label.styleSheet()
                
                # Mostrar notificación
                self.countdown_label.setText(message)
                self.countdown_label.setStyleSheet(style)
                
                # Restaurar después de 2 segundos
                QTimer.singleShot(2000, lambda: self.restore_countdown_display(original_text, original_style))
            
        except Exception as e:
            print(f"Error mostrando notificación de ajuste: {e}")


    def restore_countdown_display(self, original_text, original_style):
        """Restaura la visualización original del countdown."""
        try:
            if hasattr(self, 'countdown_label'):
                self.countdown_label.setText(original_text)
                self.countdown_label.setStyleSheet(original_style)
        except Exception as e:
            print(f"Error restaurando countdown: {e}")



# JUGADOR 

    def populate_player_combo(self, combo):
        """
        Llena el combobox con los jugadores disponibles.
        
        Args:
            combo: El QComboBox a llenar
        """
        try:
            combo.clear()
            combo.addItem("Añadir nuevo jugador...")
            
            # Obtener jugadores existentes
            players = self.advanced_config.get_available_players()
            for player in players:
                combo.addItem(player)
            
            # Seleccionar el jugador actual si existe
            current_player = self.advanced_config.get_current_player()
            if current_player:
                index = combo.findText(current_player)
                if index >= 0:
                    combo.setCurrentIndex(index)
            
        except Exception as e:
            print(f"Error llenando combo de jugadores: {e}")

    def on_player_combo_changed(self, combo):
        """
        Maneja el cambio en el combobox de jugadores.
        
        Args:
            combo: El QComboBox que cambió
        """
        try:
            selected_text = combo.currentText()
            
            if selected_text == "Añadir nuevo jugador...":
                self.create_new_player_dialog(combo)
            elif selected_text:
                # Cargar configuración del jugador seleccionado
                if self.advanced_config.load_player_config(selected_text):
                    # SOLO mostrar mensaje cuando se cambia MANUALMENTE desde el combo
                    self.show_info_message("Jugador cargado", f"Configuración de '{selected_text}' cargada correctamente")
                else:
                    self.show_error_message("Error", f"No se pudo cargar la configuración de '{selected_text}'")
            
        except Exception as e:
            print(f"Error en cambio de jugador: {e}")

    def create_new_player_dialog(self, combo):
        """
        Muestra diálogo para crear un nuevo jugador.
        
        Args:
            combo: El QComboBox para actualizar después de crear
        """
        try:
            from PyQt6.QtWidgets import QInputDialog
            
            player_name, ok = QInputDialog.getText(
                self,
                "Nuevo Jugador",
                "Introduce el nombre del nuevo jugador:",
                text=""
            )
            
            if ok and player_name.strip():
                player_name = player_name.strip()
                
                if self.advanced_config.create_new_player(player_name):
                    # Actualizar combobox
                    self.populate_player_combo(combo)
                    
                    # Seleccionar el nuevo jugador
                    index = combo.findText(player_name)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                    
                    # Cargar su configuración
                    self.advanced_config.load_player_config(player_name)
                    
                    self.show_info_message("Jugador creado", f"Jugador '{player_name}' creado y cargado correctamente")
                else:
                    self.show_error_message("Error", f"No se pudo crear el jugador '{player_name}'. Puede que ya exista.")
            else:
                # Si se cancela, volver a seleccionar el jugador actual
                current_player = self.advanced_config.get_current_player()
                if current_player:
                    index = combo.findText(current_player)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                else:
                    combo.setCurrentIndex(0)
        
        except Exception as e:
            print(f"Error creando nuevo jugador: {e}")
            self.show_error_message("Error", f"Error creando jugador: {e}")

    def on_advanced_config_changed(self):
        """Maneja cambios en la configuración avanzada."""
        print("Configuración avanzada cambiada")
        # Guardar automáticamente
        if hasattr(self, 'advanced_config'):
            self.advanced_config.save_current_player_config()

    def on_player_changed(self, player_name):
        """
        Maneja el cambio de jugador.
        
        Args:
            player_name (str): Nombre del nuevo jugador
        """
        print(f"Jugador cambiado a: {player_name}")
        
        # Actualizar indicador visual
        self.update_player_indicator()
        
        # Actualizar UI si es necesario
        if hasattr(self, 'update_ui_from_config'):
            self.update_ui_from_config()
        
        # Mostrar notificación
        #self.show_info_message("Jugador cargado", f"Perfil de '{player_name}' cargado correctamente")




    def initialize_default_player(self):
        """Inicializa un jugador por defecto si no existe ninguno."""
        try:
            available_players = self.advanced_config.get_available_players()
            
            if not available_players:
                # No hay jugadores, crear uno por defecto
                default_player = "Jugador1"
                if self.advanced_config.create_new_player(default_player):
                    self.advanced_config.load_player_config(default_player)
                    print(f"Jugador por defecto '{default_player}' creado y cargado")
                else:
                    print("No se pudo crear jugador por defecto")
            else:
                # Cargar el primer jugador disponible SILENCIOSAMENTE
                first_player = available_players[0]
                if self.advanced_config.load_player_config(first_player):
                    print(f"Jugador '{first_player}' cargado automáticamente al inicio")
                else:
                    print(f"No se pudo cargar jugador '{first_player}'")
                    
        except Exception as e:
            print(f"Error inicializando jugador por defecto: {e}")


    def create_player_indicator(self):
        """Crea un indicador visual del jugador actual en la UI principal."""
        try:
            if not hasattr(self, 'player_indicator'):
                # Crear label para mostrar el jugador actual
                self.player_indicator = QLabel("👤 Sin jugador seleccionado")
                self.player_indicator.setStyleSheet("""
                    QLabel {
                        
                        font-size: 12px;
                        font-weight: bold;
                        padding: 4px 8px;
                        border: 1px solid #ccc;
                        border-radius: 4px;
                        
                    }
                """)
                
                # Agregar al layout principal (buscar un lugar apropiado)
                if hasattr(self, 'main_layout'):
                    self.main_layout.addWidget(self.player_indicator)
                elif hasattr(self, 'score_label') and self.score_label.parent():
                    # Agregar cerca de las estadísticas
                    stats_layout = self.score_label.parent().layout()
                    if stats_layout:
                        stats_layout.addWidget(self.player_indicator)
            
            # Actualizar el texto del indicador
            self.update_player_indicator()
            
        except Exception as e:
            print(f"Error creando indicador de jugador: {e}")

    def update_player_indicator(self):
        """Actualiza el indicador visual del jugador actual."""
        try:
            if not hasattr(self, 'player_indicator') or not hasattr(self, 'advanced_config'):
                return
            
            current_player = self.advanced_config.get_current_player()
            
            if current_player:
                # Obtener estadísticas básicas del jugador
                stats = self.advanced_config.get_player_statistics()
                accuracy = stats.get("accuracy", 0)
                games_played = stats.get("games_played", 0)
                
                self.player_indicator.setText(f"👤 {current_player} | 🎯 {accuracy:.1f}% | 🎮 {games_played} juegos")
                self.player_indicator.setStyleSheet("""
                    QLabel {
                        
                        font-size: 12px;
                        font-weight: bold;
                        padding: 4px 8px;
                        border: 1px;
                        border-radius: 4px;
                        
                    }
                """)
            else:
                self.player_indicator.setText("👤 Sin jugador seleccionado")
                self.player_indicator.setStyleSheet("""
                    QLabel {
                        color: #666;
                        font-size: 12px;
                        font-weight: bold;
                        padding: 4px 8px;
                        border: 1px solid #ccc;
                        border-radius: 4px;
                        
                    }
                """)
            
        except Exception as e:
            print(f"Error actualizando indicador de jugador: {e}")


    def show_player_statistics_dialog(self):
        """Muestra un diálogo con las estadísticas detalladas del jugador actual."""
        try:
            if not hasattr(self, 'advanced_config'):
                return
            
            current_player = self.advanced_config.get_current_player()
            if not current_player:
                self.show_info_message("Sin jugador", "No hay ningún jugador seleccionado")
                return
            
            stats = self.advanced_config.get_player_statistics()
            
            # Crear diálogo de estadísticas
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Estadísticas de {current_player}")
            dialog.setMinimumWidth(400)
            dialog.setMinimumHeight(300)
            
            layout = QVBoxLayout()
            
            # Título
            title = QLabel(f"📊 Estadísticas de {current_player}")
            title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
            layout.addWidget(title)
            
            # Crear texto de estadísticas
            stats_text = f"""
🎮 Juegos jugados: {stats.get('games_played', 0)}
❓ Total de preguntas: {stats.get('total_questions', 0)}
✅ Respuestas correctas: {stats.get('correct_answers', 0)}
🎯 Precisión: {stats.get('accuracy', 0):.1f}%
⏱️ Tiempo total jugado: {self.format_time(stats.get('total_time_played', 0))}
📅 Última partida: {stats.get('last_played', 'Nunca')[:19] if stats.get('last_played') else 'Nunca'}
🎵 Género favorito: {stats.get('favorite_genre', 'No determinado')}
            """.strip()
            
            stats_display = QTextEdit()
            stats_display.setPlainText(stats_text)
            stats_display.setReadOnly(True)
            stats_display.setMaximumHeight(200)
            layout.addWidget(stats_display)
            
            # Botón de cerrar
            close_btn = QPushButton("Cerrar")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            print(f"Error mostrando estadísticas del jugador: {e}")
            self.show_error_message("Error", f"Error mostrando estadísticas: {e}")


    def setup_player_indicator_context_menu(self):
        """Configura el menú contextual del indicador de jugador."""
        try:
            if not hasattr(self, 'player_indicator'):
                return
            
            from PyQt6.QtWidgets import QMenu
            from PyQt6.QtCore import Qt
            
            # Habilitar menú contextual
            self.player_indicator.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.player_indicator.customContextMenuRequested.connect(self.show_player_context_menu)
            
        except Exception as e:
            print(f"Error configurando menú contextual: {e}")

    def show_player_context_menu(self, position):
        """Muestra el menú contextual del indicador de jugador."""
        try:
            from PyQt6.QtWidgets import QMenu
            
            menu = QMenu(self)
            
            # Opción para ver estadísticas
            stats_action = menu.addAction("📊 Ver estadísticas")
            stats_action.triggered.connect(self.show_player_statistics_dialog)
            
            # Opción para cambiar jugador
            change_action = menu.addAction("👤 Cambiar jugador")
            change_action.triggered.connect(self.show_advanced_settings_dialog)
            
            # Separador
            menu.addSeparator()
            
            # Opción para crear nuevo jugador
            new_action = menu.addAction("➕ Nuevo jugador")
            new_action.triggered.connect(lambda: self.create_new_player_dialog(None))
            
            # Mostrar menú
            global_pos = self.player_indicator.mapToGlobal(position)
            menu.exec(global_pos)
            
        except Exception as e:
            print(f"Error mostrando menú contextual: {e}")


# advanced 

    def show_time_filter_dialog(self):
        """Muestra un diálogo para filtrar por tiempo (años y décadas)."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar por Tiempo")
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
            
            # Crear un widget de tabla para mostrar años/décadas, artistas y álbumes
            table = QTableWidget()
            table.setColumnCount(3)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(table)
            
            # Variables para mantener los checkboxes
            current_checkboxes = {}
            
            # Función para actualizar la tabla según el modo seleccionado
            def update_table_data():
                nonlocal current_checkboxes
                current_checkboxes = {}
                
                if mode_combo.currentText() == "Década":
                    table.setHorizontalHeaderLabels(["Década", "Artistas", "Álbumes"])
                    load_decades_data()
                else:
                    table.setHorizontalHeaderLabels(["Año", "Artistas", "Álbumes"])
                    load_years_data()
            
            # Cargar datos de décadas
            def load_decades_data():
                nonlocal current_checkboxes
                try:
                    # Usar la columna 'date' de songs y 'year' de albums para obtener décadas
                    self.cursor.execute("""
                        SELECT DISTINCT 
                            CASE 
                                WHEN LENGTH(s.date) >= 4 THEN CAST(SUBSTR(s.date, 1, 3) || '0' AS TEXT)
                                WHEN a.year IS NOT NULL AND LENGTH(CAST(a.year AS TEXT)) >= 4 THEN CAST(SUBSTR(CAST(a.year AS TEXT), 1, 3) || '0' AS TEXT)
                                ELSE NULL
                            END AS decade
                        FROM songs s
                        LEFT JOIN albums a ON s.album = a.name 
                        WHERE decade IS NOT NULL
                        ORDER BY decade
                    """)
                    decades = self.cursor.fetchall()
                    
                    # Obtener décadas excluidas (usar tabla estándar de exclusiones)
                    excluded_decades = self.get_excluded_items("excluded_decades")
                    
                    # Configurar el número de filas de la tabla
                    table.setRowCount(len(decades))
                    current_checkboxes = {}
                    
                    # Llenar la tabla con datos
                    for row, (decade,) in enumerate(decades):
                        # Crear widget para checkbox de la década
                        checkbox_widget = QWidget()
                        checkbox_layout = QHBoxLayout(checkbox_widget)
                        checkbox_layout.setContentsMargins(5, 0, 0, 0)
                        checkbox = QCheckBox(f"{decade}s")
                        checkbox.setChecked(decade in excluded_decades)
                        checkbox_layout.addWidget(checkbox)
                        checkbox_layout.addStretch()
                        
                        # Guardar referencia al checkbox
                        current_checkboxes[decade] = checkbox
                        
                        # Añadir el widget con checkbox a la tabla
                        table.setCellWidget(row, 0, checkbox_widget)
                        
                        # Obtener artistas de esta década
                        self.cursor.execute("""
                            SELECT DISTINCT s.artist 
                            FROM songs s
                            LEFT JOIN albums a ON s.album = a.name 
                            WHERE (
                                (LENGTH(s.date) >= 4 AND SUBSTR(s.date, 1, 3) || '0' = ?) OR
                                (s.date IS NULL AND a.year IS NOT NULL AND LENGTH(CAST(a.year AS TEXT)) >= 4 AND SUBSTR(CAST(a.year AS TEXT), 1, 3) || '0' = ?)
                            )
                            ORDER BY s.artist
                            LIMIT 10
                        """, (decade, decade))
                        artists = self.cursor.fetchall()
                        artists_text = ", ".join([artist[0] for artist in artists if artist[0]])
                        if len(artists) == 10:
                            artists_text += "..."
                        
                        # Añadir artistas a la segunda columna
                        artists_item = QTableWidgetItem(artists_text)
                        artists_item.setFlags(artists_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        table.setItem(row, 1, artists_item)
                        
                        # Obtener álbumes de esta década
                        self.cursor.execute("""
                            SELECT DISTINCT s.album 
                            FROM songs s
                            LEFT JOIN albums a ON s.album = a.name 
                            WHERE s.album IS NOT NULL AND s.album != '' AND (
                                (LENGTH(s.date) >= 4 AND SUBSTR(s.date, 1, 3) || '0' = ?) OR
                                (s.date IS NULL AND a.year IS NOT NULL AND LENGTH(CAST(a.year AS TEXT)) >= 4 AND SUBSTR(CAST(a.year AS TEXT), 1, 3) || '0' = ?)
                            )
                            ORDER BY s.album
                            LIMIT 10
                        """, (decade, decade))
                        albums = self.cursor.fetchall()
                        albums_text = ", ".join([album[0] for album in albums if album[0]])
                        if len(albums) == 10:
                            albums_text += "..."
                        
                        # Añadir álbumes a la tercera columna
                        albums_item = QTableWidgetItem(albums_text)
                        albums_item.setFlags(albums_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        table.setItem(row, 2, albums_item)
                        
                    print(f"Cargadas {len(decades)} décadas")
                        
                except Exception as e:
                    print(f"Error cargando décadas: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Cargar datos de años
            def load_years_data():
                nonlocal current_checkboxes
                try:
                    # Usar la columna 'date' de songs y 'year' de albums para obtener años
                    self.cursor.execute("""
                        SELECT DISTINCT 
                            CASE 
                                WHEN LENGTH(s.date) >= 4 THEN SUBSTR(s.date, 1, 4)
                                WHEN a.year IS NOT NULL THEN CAST(a.year AS TEXT)
                                ELSE NULL
                            END AS year
                        FROM songs s
                        LEFT JOIN albums a ON s.album = a.name 
                        WHERE year IS NOT NULL AND LENGTH(year) = 4
                        ORDER BY year
                    """)
                    years = self.cursor.fetchall()
                    
                    # Obtener años excluidos
                    excluded_years = self.get_excluded_items("excluded_years")
                    
                    # Configurar el número de filas de la tabla
                    table.setRowCount(len(years))
                    current_checkboxes = {}
                    
                    # Llenar la tabla con datos
                    for row, (year,) in enumerate(years):
                        # Crear widget para checkbox del año
                        checkbox_widget = QWidget()
                        checkbox_layout = QHBoxLayout(checkbox_widget)
                        checkbox_layout.setContentsMargins(5, 0, 0, 0)
                        checkbox = QCheckBox(year)
                        checkbox.setChecked(year in excluded_years)
                        checkbox_layout.addWidget(checkbox)
                        checkbox_layout.addStretch()
                        
                        # Guardar referencia al checkbox
                        current_checkboxes[year] = checkbox
                        
                        # Añadir el widget con checkbox a la tabla
                        table.setCellWidget(row, 0, checkbox_widget)
                        
                        # Obtener artistas de este año
                        self.cursor.execute("""
                            SELECT DISTINCT s.artist 
                            FROM songs s
                            LEFT JOIN albums a ON s.album = a.name 
                            WHERE (
                                (LENGTH(s.date) >= 4 AND SUBSTR(s.date, 1, 4) = ?) OR
                                (s.date IS NULL AND CAST(a.year AS TEXT) = ?)
                            )
                            ORDER BY s.artist
                            LIMIT 10
                        """, (year, year))
                        artists = self.cursor.fetchall()
                        artists_text = ", ".join([artist[0] for artist in artists if artist[0]])
                        if len(artists) == 10:
                            artists_text += "..."
                        
                        # Añadir artistas a la segunda columna
                        artists_item = QTableWidgetItem(artists_text)
                        artists_item.setFlags(artists_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        table.setItem(row, 1, artists_item)
                        
                        # Obtener álbumes de este año
                        self.cursor.execute("""
                            SELECT DISTINCT s.album 
                            FROM songs s
                            LEFT JOIN albums a ON s.album = a.name 
                            WHERE s.album IS NOT NULL AND s.album != '' AND (
                                (LENGTH(s.date) >= 4 AND SUBSTR(s.date, 1, 4) = ?) OR
                                (s.date IS NULL AND CAST(a.year AS TEXT) = ?)
                            )
                            ORDER BY s.album
                            LIMIT 10
                        """, (year, year))
                        albums = self.cursor.fetchall()
                        albums_text = ", ".join([album[0] for album in albums if album[0]])
                        if len(albums) == 10:
                            albums_text += "..."
                        
                        # Añadir álbumes a la tercera columna
                        albums_item = QTableWidgetItem(albums_text)
                        albums_item.setFlags(albums_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        table.setItem(row, 2, albums_item)
                        
                    print(f"Cargados {len(years)} años")
                        
                except Exception as e:
                    print(f"Error cargando años: {e}")
                    import traceback
                    traceback.print_exc()
            
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
            
            # Función para cargar los datos según el modo seleccionado
            def update_mode():
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
            
            def save_changes():
                try:
                    selected = []
                    
                    # Determinar qué tipo de filtro estamos guardando
                    is_decade = mode_combo.currentText() == "Década"
                    
                    filter_key = "excluded_decades" if is_decade else "excluded_years"
                    
                    # Guardar los elementos seleccionados
                    for period, checkbox in current_checkboxes.items():
                        if checkbox.isChecked():
                            selected.append(period)
                    
                    self.save_excluded_items(filter_key, selected)
                    dialog.accept()
                    
                except Exception as e:
                    print(f"Error guardando filtros de tiempo: {e}")
                    self.show_error_message("Error", f"Error al guardar filtros: {e}")
            
            select_all_btn.clicked.connect(select_all)
            deselect_all_btn.clicked.connect(deselect_all)
            save_btn.clicked.connect(save_changes)
            cancel_btn.clicked.connect(dialog.reject)
            
            # Cargar datos iniciales
            update_table_data()
            
            dialog.exec()
            
        except Exception as e:
            print(f"Error al mostrar el diálogo de filtrar por año/década: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_message("Error", f"Error al mostrar el diálogo: {e}")


    def save_excluded_items(self, item_type, excluded_items):
        """
        Guarda los elementos excluidos en la base de datos con prefijo jaangle_exclude_.
        
        Args:
            item_type: Tipo de elementos ("excluded_artists", "excluded_albums", etc.)
            excluded_items: Lista de nombres de elementos a excluir
            
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario
        """
        try:
            if not hasattr(self, 'cursor') or not self.cursor:
                print("Error: No database cursor available")
                return False
            
            # Mapear tipos de filtros a nombres de tabla con prefijo jaangle_exclude_
            table_mapping = {
                "excluded_artists": "jaangle_exclude_artists",
                "excluded_albums": "jaangle_exclude_albums",
                "excluded_genres": "jaangle_exclude_genres", 
                "excluded_folders": "jaangle_exclude_folders",
                "excluded_decades": "jaangle_exclude_decades",
                "excluded_years": "jaangle_exclude_years",
                "included_decades": "jaangle_include_decades",
                "included_years": "jaangle_include_years",
                "excluded_labels": "jaangle_exclude_labels",
                "excluded_countries": "jaangle_exclude_countries"
            }
            
            actual_table = table_mapping.get(item_type, f"jaangle_exclude_{item_type}")
            
            # Usar la conexión existente en lugar de crear una nueva
            cursor = self.cursor
            conn = self.conn
            
            # Crear la tabla si no existe
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {actual_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Limpiar datos existentes
            cursor.execute(f"DELETE FROM {actual_table}")
            
            # Insertar nuevos elementos excluidos
            excluded_count = 0
            for item in excluded_items:
                if item and str(item).strip():  # Asegurar que no sea None, vacío o solo espacios
                    try:
                        cursor.execute(f"INSERT OR IGNORE INTO {actual_table} (name) VALUES (?)", (str(item).strip(),))
                        excluded_count += 1
                    except Exception as e:
                        print(f"Error inserting item '{item}': {e}")
            
            # Confirmar cambios
            conn.commit()
            
            print(f"Successfully saved {excluded_count} items to {actual_table}")
            return True
            
        except Exception as e:
            print(f"Error saving excluded items to {item_type}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            # Intentar hacer rollback si es posible
            try:
                if hasattr(self, 'conn') and self.conn:
                    self.conn.rollback()
            except:
                pass
                
            return False

    def _get_month_number(self, month_name):
        """Convierte el nombre del mes a número."""
        months = {
            "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
            "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
            "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
        }
        return months.get(month_name, 1)

    def clear_advanced_filters(self):
        """Limpia todos los filtros avanzados."""
        try:
            if hasattr(self, 'advanced_filters'):
                self.advanced_filters.clear()
            print("Filtros avanzados limpiados")
            
        except Exception as e:
            print(f"Error limpiando filtros avanzados: {e}")

    def get_active_advanced_filters_summary(self):
        """
        Obtiene un resumen de los filtros avanzados activos.
        
        Returns:
            str: Resumen de los filtros activos
        """
        try:
            if not hasattr(self, 'advanced_filters') or not self.advanced_filters:
                return "Sin filtros avanzados activos"
            
            summary_parts = []
            
            if 'time' in self.advanced_filters:
                time_filter = self.advanced_filters['time']
                time_parts = []
                if time_filter.get('decades'):
                    time_parts.append(f"{len(time_filter['decades'])} décadas")
                if time_filter.get('years'):
                    time_parts.append(f"{len(time_filter['years'])} años")
                if time_parts:
                    summary_parts.append(f"Tiempo: {', '.join(time_parts)}")
            
            if 'countries' in self.advanced_filters and self.advanced_filters['countries']:
                summary_parts.append(f"Países: {len(self.advanced_filters['countries'])}")
            
            if 'genres' in self.advanced_filters:
                genre_filter = self.advanced_filters['genres']
                genre_count = sum(len(v) for v in genre_filter.values() if v)
                if genre_count > 0:
                    summary_parts.append(f"Géneros: {genre_count}")
            
            if 'labels' in self.advanced_filters and self.advanced_filters['labels']:
                summary_parts.append(f"Sellos: {len(self.advanced_filters['labels'])}")
            
            if 'producers' in self.advanced_filters:
                producer_filter = self.advanced_filters['producers']
                producer_count = sum(len(v) for v in producer_filter.values() if v)
                if producer_count > 0:
                    summary_parts.append(f"Productores: {producer_count}")
            
            if 'listens' in self.advanced_filters:
                listen_filter = self.advanced_filters['listens']
                listen_count = sum(len(v) for v in listen_filter.values() if v)
                if listen_count > 0:
                    summary_parts.append(f"Escuchas: {listen_count}")
            
            if 'lyrics' in self.advanced_filters:
                lyrics_filter = self.advanced_filters['lyrics']
                if lyrics_filter.get('text'):
                    summary_parts.append(f"Letras: '{lyrics_filter['text'][:20]}...'")
            
            if 'favorites' in self.advanced_filters:
                fav_filter = self.advanced_filters['favorites']
                fav_types = []
                if fav_filter.get('artists'):
                    fav_types.append("artistas")
                if fav_filter.get('albums'):
                    fav_types.append("álbumes")
                if fav_filter.get('songs'):
                    fav_types.append("canciones")
                if fav_types:
                    summary_parts.append(f"Favoritos: {', '.join(fav_types)}")
            
            if summary_parts:
                return f"Filtros activos: {' | '.join(summary_parts)}"
            else:
                return "Sin filtros avanzados activos"
            
        except Exception as e:
            print(f"Error obteniendo resumen de filtros: {e}")
            return "Error al obtener resumen de filtros"

    def get_random_songs_with_advanced_filters(self, count=4, max_retries=3):
        """
        Versión modificada de get_random_songs que incorpora los filtros avanzados.
        Reemplaza o complementa el método original.
        """
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
                
                # Aplicar filtros avanzados PRIMERO
                query, params = self.apply_advanced_filters_to_query(query, params)
                
                # Aplicar filtro por origen de música
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
                
                # Verificar si hay artistas excluidos (filtros normales)
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
                
                print(f"Ejecutando consulta con filtros avanzados: {query[:200]}...")
                self.cursor.execute(query, params)
                candidates = self.cursor.fetchall()
                
                if len(candidates) == 0:
                    print(f"La consulta no devolvió resultados con filtros avanzados")
                    print(f"Parámetros: {params}")
                    retries += 1
                    continue
                
                print(f"Encontradas {len(candidates)} canciones candidatas")
                
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
                    print(f"Devolviendo {len(valid_songs[:count])} canciones válidas")
                    return valid_songs[:count]
                
                # Si no hay suficientes canciones válidas, intentar de nuevo
                retries += 1
                print(f"No se encontraron suficientes canciones válidas para {count} opciones. Reintento {retries}/{max_retries}")
            
            except Exception as e:
                print(f"Error al obtener canciones aleatorias con filtros avanzados: {e}")
                import traceback
                traceback.print_exc()
                retries += 1
        
        # Si llegamos aquí, no pudimos obtener suficientes canciones
        print(f"Error: No se pudieron obtener suficientes canciones válidas ({count}) después de varios intentos")
        return []

    def integrate_advanced_filters_with_existing_system(self):
        """
        Integra los filtros avanzados con el método get_random_songs existente.
        Llama a este método después de inicializar los filtros avanzados.
        """
        # Guardar el método original si aún no se ha hecho
        if not hasattr(self, '_original_get_random_songs'):
            self._original_get_random_songs = self.get_random_songs
        
            # Reemplazar con la versión que incluye filtros avanzados
            self.get_random_songs = self.get_random_songs_with_advanced_filters
            combos_layout = QHBoxLayout()
            
            # Combobox para décadas
            decades_layout = QVBoxLayout()
            decades_label = QLabel("Décadas:")
            self.decades_combo = QComboBox()
            self.decades_combo.setEditable(True)
            self.decades_combo.lineEdit().setPlaceholderText("Seleccionar décadas...")
            decades_layout.addWidget(decades_label)
            decades_layout.addWidget(self.decades_combo)
            
            # Combobox para años
            years_layout = QVBoxLayout()
            years_label = QLabel("Años:")
            self.years_combo = QComboBox()
            self.years_combo.setEditable(True)
            self.years_combo.lineEdit().setPlaceholderText("Seleccionar años...")
            years_layout.addWidget(years_label)
            years_layout.addWidget(self.years_combo)
            
            combos_layout.addLayout(decades_layout)
            combos_layout.addLayout(years_layout)
            layout.addLayout(combos_layout)
            
            # Tabla para mostrar selecciones
            self.time_table = QTableWidget()
            self.time_table.setColumnCount(3)
            self.time_table.setHorizontalHeaderLabels(["Seleccionar", "Tipo", "Valor"])
            self.time_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.time_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.time_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.time_table)
            
            # Botones de selección
            buttons_layout = QHBoxLayout()
            select_all_btn = QPushButton("Seleccionar Todo")
            deselect_all_btn = QPushButton("Deseleccionar Todo")
            add_decade_btn = QPushButton("Añadir Década")
            add_year_btn = QPushButton("Añadir Año")
            
            buttons_layout.addWidget(select_all_btn)
            buttons_layout.addWidget(deselect_all_btn)
            buttons_layout.addWidget(add_decade_btn)
            buttons_layout.addWidget(add_year_btn)
            layout.addLayout(buttons_layout)
            
            # Botones de diálogo
            dialog_buttons = QHBoxLayout()
            save_btn = QPushButton("Guardar")
            cancel_btn = QPushButton("Cancelar")
            dialog_buttons.addWidget(save_btn)
            dialog_buttons.addWidget(cancel_btn)
            layout.addLayout(dialog_buttons)
            
            dialog.setLayout(layout)
            
            # Cargar datos disponibles
            self._load_decades_and_years()
            
            # Conectar señales
            add_decade_btn.clicked.connect(lambda: self._add_time_filter("década"))
            add_year_btn.clicked.connect(lambda: self._add_time_filter("año"))
            select_all_btn.clicked.connect(lambda: self._select_all_time_filters(True))
            deselect_all_btn.clicked.connect(lambda: self._select_all_time_filters(False))
            save_btn.clicked.connect(lambda: self._save_time_filters(dialog))
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
            



    def _load_decades_and_years(self):
        """Carga las décadas y años disponibles en los comboboxes."""
        try:
            # Cargar décadas
            self.cursor.execute("""
                SELECT DISTINCT CAST(SUBSTR(album_year, 1, 3) || '0' AS TEXT) AS decade
                FROM songs 
                WHERE album_year IS NOT NULL AND album_year != '' AND LENGTH(album_year) >= 4
                ORDER BY decade
            """)
            decades = [row[0] + "s" for row in self.cursor.fetchall()]
            self.decades_combo.addItems(decades)
            
            # Cargar años
            self.cursor.execute("""
                SELECT DISTINCT album_year
                FROM songs 
                WHERE album_year IS NOT NULL AND album_year != '' AND LENGTH(album_year) >= 4
                ORDER BY album_year
            """)
            years = [row[0] for row in self.cursor.fetchall()]
            self.years_combo.addItems(years)
            
        except Exception as e:
            print(f"Error cargando décadas y años: {e}")

    def _add_time_filter(self, filter_type):
        """Añade un filtro de tiempo a la tabla."""
        try:
            if filter_type == "década":
                value = self.decades_combo.currentText()
                if not value or value in [item.text() for item in self.decades_combo.findItems(value)]:
                    return
            else:
                value = self.years_combo.currentText()
                if not value or value in [item.text() for item in self.years_combo.findItems(value)]:
                    return
            
            # Verificar si ya existe
            for row in range(self.time_table.rowCount()):
                if (self.time_table.item(row, 1).text() == filter_type.capitalize() and 
                    self.time_table.item(row, 2).text() == value):
                    return
            
            # Añadir nueva fila
            row = self.time_table.rowCount()
            self.time_table.insertRow(row)
            
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.time_table.setCellWidget(row, 0, checkbox)
            
            # Tipo y valor
            self.time_table.setItem(row, 1, QTableWidgetItem(filter_type.capitalize()))
            self.time_table.setItem(row, 2, QTableWidgetItem(value))
            
        except Exception as e:
            print(f"Error añadiendo filtro de tiempo: {e}")

    def _select_all_time_filters(self, checked):
        """Selecciona o deselecciona todos los filtros de tiempo."""
        for row in range(self.time_table.rowCount()):
            checkbox = self.time_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)

    def _save_time_filters(self, dialog):
        """Guarda los filtros de tiempo seleccionados."""
        try:
            selected_filters = {"decades": [], "years": []}
            
            for row in range(self.time_table.rowCount()):
                checkbox = self.time_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    filter_type = self.time_table.item(row, 1).text().lower()
                    value = self.time_table.item(row, 2).text()
                    
                    if filter_type == "década":
                        selected_filters["decades"].append(value.replace("s", ""))
                    else:
                        selected_filters["years"].append(value)
            
            # Guardar en la configuración
            if not hasattr(self, 'advanced_filters'):
                self.advanced_filters = {}
            self.advanced_filters['time'] = selected_filters
            
            dialog.accept()
            
        except Exception as e:
            print(f"Error guardando filtros de tiempo: {e}")

    def show_countries_filter_dialog(self):
        """Muestra un diálogo para filtrar por países."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar por Países")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(500)
            
            layout = QVBoxLayout()
            
            # Combobox de países
            combo_layout = QHBoxLayout()
            countries_label = QLabel("Países:")
            self.countries_combo = QComboBox()
            self.countries_combo.setEditable(True)
            self.countries_combo.lineEdit().setPlaceholderText("Seleccionar países...")
            combo_layout.addWidget(countries_label)
            combo_layout.addWidget(self.countries_combo)
            layout.addLayout(combo_layout)
            
            # Tabla para mostrar selecciones
            self.countries_table = QTableWidget()
            self.countries_table.setColumnCount(2)
            self.countries_table.setHorizontalHeaderLabels(["Seleccionar", "País"])
            self.countries_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.countries_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.countries_table)
            
            # Botones
            self._setup_filter_dialog_buttons(layout, dialog, self._add_country_filter, 
                                            self._select_all_countries, self._save_countries_filters)
            
            # Cargar países disponibles
            self._load_countries()
            
            dialog.exec()
            
        except Exception as e:
            print(f"Error en filtro de países: {e}")
            self.show_error_message("Error", f"Error en filtro de países: {e}")

    def _load_countries(self):
        """Carga los países disponibles."""
        try:
            self.cursor.execute("""
                SELECT DISTINCT country
                FROM songs 
                WHERE country IS NOT NULL AND country != ''
                ORDER BY country
            """)
            countries = [row[0] for row in self.cursor.fetchall()]
            self.countries_combo.addItems(countries)
            
        except Exception as e:
            print(f"Error cargando países: {e}")

    def _add_country_filter(self):
        """Añade un país a la tabla de filtros."""
        value = self.countries_combo.currentText()
        if not value:
            return
            
        # Verificar si ya existe
        for row in range(self.countries_table.rowCount()):
            if self.countries_table.item(row, 1).text() == value:
                return
        
        # Añadir nueva fila
        row = self.countries_table.rowCount()
        self.countries_table.insertRow(row)
        
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        self.countries_table.setCellWidget(row, 0, checkbox)
        self.countries_table.setItem(row, 1, QTableWidgetItem(value))

    def _select_all_countries(self, checked):
        """Selecciona todos los países."""
        for row in range(self.countries_table.rowCount()):
            checkbox = self.countries_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)

    def _save_countries_filters(self, dialog):
        """Guarda los filtros de países."""
        try:
            selected_countries = []
            for row in range(self.countries_table.rowCount()):
                checkbox = self.countries_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    selected_countries.append(self.countries_table.item(row, 1).text())
            
            if not hasattr(self, 'advanced_filters'):
                self.advanced_filters = {}
            self.advanced_filters['countries'] = selected_countries
            
            dialog.accept()
            
        except Exception as e:
            print(f"Error guardando filtros de países: {e}")

    def show_genres_filter_dialog(self):
        """Muestra un diálogo para filtrar por géneros (múltiples fuentes)."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar por Géneros")
            dialog.setMinimumWidth(800)
            dialog.setMinimumHeight(600)
            
            layout = QVBoxLayout()
            
            # Tres comboboxes para diferentes fuentes de géneros
            combos_layout = QHBoxLayout()
            
            # Géneros de songs
            songs_layout = QVBoxLayout()
            songs_label = QLabel("Géneros (Songs):")
            self.songs_genres_combo = QComboBox()
            self.songs_genres_combo.setEditable(True)
            songs_layout.addWidget(songs_label)
            songs_layout.addWidget(self.songs_genres_combo)
            
            # Tags de artists
            artists_layout = QVBoxLayout()
            artists_label = QLabel("Tags (Artists):")
            self.artists_tags_combo = QComboBox()
            self.artists_tags_combo.setEditable(True)
            artists_layout.addWidget(artists_label)
            artists_layout.addWidget(self.artists_tags_combo)
            
            # Discogs
            discogs_layout = QVBoxLayout()
            discogs_label = QLabel("Discogs:")
            self.discogs_genres_combo = QComboBox()
            self.discogs_genres_combo.setEditable(True) 
            discogs_layout.addWidget(discogs_label)
            discogs_layout.addWidget(self.discogs_genres_combo)
            
            combos_layout.addLayout(songs_layout)
            combos_layout.addLayout(artists_layout)
            combos_layout.addLayout(discogs_layout)
            layout.addLayout(combos_layout)
            
            # Tabla
            self.genres_table = QTableWidget()
            self.genres_table.setColumnCount(3)
            self.genres_table.setHorizontalHeaderLabels(["Seleccionar", "Fuente", "Género"])
            self.genres_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.genres_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.genres_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.genres_table)
            
            # Botones específicos para géneros
            buttons_layout = QHBoxLayout()
            select_all_btn = QPushButton("Seleccionar Todo")
            deselect_all_btn = QPushButton("Deseleccionar Todo")
            add_songs_btn = QPushButton("Añadir Songs")
            add_artists_btn = QPushButton("Añadir Artists")
            add_discogs_btn = QPushButton("Añadir Discogs")
            
            buttons_layout.addWidget(select_all_btn)
            buttons_layout.addWidget(deselect_all_btn)
            buttons_layout.addWidget(add_songs_btn)
            buttons_layout.addWidget(add_artists_btn)
            buttons_layout.addWidget(add_discogs_btn)
            layout.addLayout(buttons_layout)
            
            # Botones de diálogo
            dialog_buttons = QHBoxLayout()
            save_btn = QPushButton("Guardar")
            cancel_btn = QPushButton("Cancelar")
            dialog_buttons.addWidget(save_btn)
            dialog_buttons.addWidget(cancel_btn)
            layout.addLayout(dialog_buttons)
            
            dialog.setLayout(layout)
            
            # Cargar datos
            self._load_genres_data()
            
            # Conectar señales
            add_songs_btn.clicked.connect(lambda: self._add_genre_filter("Songs"))
            add_artists_btn.clicked.connect(lambda: self._add_genre_filter("Artists"))
            add_discogs_btn.clicked.connect(lambda: self._add_genre_filter("Discogs"))
            select_all_btn.clicked.connect(lambda: self._select_all_genres(True))
            deselect_all_btn.clicked.connect(lambda: self._select_all_genres(False))
            save_btn.clicked.connect(lambda: self._save_genres_filters(dialog))
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
            
        except Exception as e:
            print(f"Error en filtro de géneros: {e}")
            self.show_error_message("Error", f"Error en filtro de géneros: {e}")

    def _load_genres_data(self):
        """Carga los datos de géneros de las diferentes fuentes."""
        try:
            # Géneros de songs
            self.cursor.execute("""
                SELECT DISTINCT genre FROM songs 
                WHERE genre IS NOT NULL AND genre != '' 
                ORDER BY genre
            """)
            songs_genres = [row[0] for row in self.cursor.fetchall()]
            self.songs_genres_combo.addItems(songs_genres)
            
            # Tags de artists
            self.cursor.execute("""
                SELECT DISTINCT tags FROM artists 
                WHERE tags IS NOT NULL AND tags != '' 
                ORDER BY tags
            """)
            artists_tags = []
            for row in self.cursor.fetchall():
                # Las tags pueden estar separadas por comas
                tags = [tag.strip() for tag in row[0].split(',')]
                artists_tags.extend(tags)
            self.artists_tags_combo.addItems(sorted(set(artists_tags)))
            
            # Géneros de discogs
            self.cursor.execute("""
                SELECT DISTINCT genres, styles FROM discogs_discography 
                WHERE (genres IS NOT NULL AND genres != '') 
                OR (styles IS NOT NULL AND styles != '')
            """)
            discogs_genres = []
            for row in self.cursor.fetchall():
                if row[0]:  # genres
                    genres = [g.strip() for g in row[0].split(',')]
                    discogs_genres.extend(genres)
                if row[1]:  # styles
                    styles = [s.strip() for s in row[1].split(',')]
                    discogs_genres.extend(styles)
            self.discogs_genres_combo.addItems(sorted(set(discogs_genres)))
            
        except Exception as e:
            print(f"Error cargando datos de géneros: {e}")

    def _add_genre_filter(self, source):
        """Añade un filtro de género según la fuente."""
        try:
            if source == "Songs":
                value = self.songs_genres_combo.currentText()
            elif source == "Artists":
                value = self.artists_tags_combo.currentText()
            else:  # Discogs
                value = self.discogs_genres_combo.currentText()
            
            if not value:
                return
            
            # Verificar si ya existe
            for row in range(self.genres_table.rowCount()):
                if (self.genres_table.item(row, 1).text() == source and 
                    self.genres_table.item(row, 2).text() == value):
                    return
            
            # Añadir nueva fila
            row = self.genres_table.rowCount()
            self.genres_table.insertRow(row)
            
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.genres_table.setCellWidget(row, 0, checkbox)
            self.genres_table.setItem(row, 1, QTableWidgetItem(source))
            self.genres_table.setItem(row, 2, QTableWidgetItem(value))
            
        except Exception as e:
            print(f"Error añadiendo filtro de género: {e}")

    def _select_all_genres(self, checked):
        """Selecciona todos los géneros."""
        for row in range(self.genres_table.rowCount()):
            checkbox = self.genres_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)

    def _save_genres_filters(self, dialog):
        """Guarda los filtros de géneros."""
        try:
            selected_filters = {"songs": [], "artists": [], "discogs": []}
            
            for row in range(self.genres_table.rowCount()):
                checkbox = self.genres_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    source = self.genres_table.item(row, 1).text().lower()
                    value = self.genres_table.item(row, 2).text()
                    
                    if source == "songs":
                        selected_filters["songs"].append(value)
                    elif source == "artists":
                        selected_filters["artists"].append(value)
                    else:
                        selected_filters["discogs"].append(value)
            
            if not hasattr(self, 'advanced_filters'):
                self.advanced_filters = {}
            self.advanced_filters['genres'] = selected_filters
            
            dialog.accept()
            
        except Exception as e:
            print(f"Error guardando filtros de géneros: {e}")

    def show_labels_filter_dialog(self):
        """Muestra un diálogo para filtrar por sellos discográficos."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar por Sellos")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(500)
            
            layout = QVBoxLayout()
            
            # Combobox de sellos
            combo_layout = QHBoxLayout()
            labels_label = QLabel("Sellos:")
            self.labels_combo = QComboBox()
            self.labels_combo.setEditable(True)
            self.labels_combo.lineEdit().setPlaceholderText("Seleccionar sellos...")
            combo_layout.addWidget(labels_label)
            combo_layout.addWidget(self.labels_combo)
            layout.addLayout(combo_layout)
            
            # Tabla
            self.labels_table = QTableWidget()  
            self.labels_table.setColumnCount(2)
            self.labels_table.setHorizontalHeaderLabels(["Seleccionar", "Sello"])
            self.labels_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.labels_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.labels_table)
            
            # Botones
            self._setup_filter_dialog_buttons(layout, dialog, self._add_label_filter,
                                            self._select_all_labels, self._save_labels_filters)
            
            # Cargar sellos
            self._load_labels()
            
            dialog.exec()
            
        except Exception as e:
            print(f"Error en filtro de sellos: {e}")
            self.show_error_message("Error", f"Error en filtro de sellos: {e}")

    def _load_labels(self):
        """Carga los sellos disponibles."""
        try:
            self.cursor.execute("""
                SELECT DISTINCT label FROM songs 
                WHERE label IS NOT NULL AND label != '' 
                ORDER BY label
            """)
            labels = [row[0] for row in self.cursor.fetchall()]
            self.labels_combo.addItems(labels)
            
        except Exception as e:
            print(f"Error cargando sellos: {e}")

    def _add_label_filter(self):
        """Añade un sello al filtro."""
        value = self.labels_combo.currentText()
        if not value:
            return
            
        # Verificar si ya existe
        for row in range(self.labels_table.rowCount()):
            if self.labels_table.item(row, 1).text() == value:
                return
        
        row = self.labels_table.rowCount()
        self.labels_table.insertRow(row)
        
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        self.labels_table.setCellWidget(row, 0, checkbox)
        self.labels_table.setItem(row, 1, QTableWidgetItem(value))

    def _select_all_labels(self, checked):
        """Selecciona todos los sellos."""
        for row in range(self.labels_table.rowCount()):
            checkbox = self.labels_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)

    def _save_labels_filters(self, dialog):
        """Guarda los filtros de sellos."""
        try:
            selected_labels = []
            for row in range(self.labels_table.rowCount()):
                checkbox = self.labels_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    selected_labels.append(self.labels_table.item(row, 1).text())
            
            if not hasattr(self, 'advanced_filters'):
                self.advanced_filters = {}
            self.advanced_filters['labels'] = selected_labels
            
            dialog.accept()
            
        except Exception as e:
            print(f"Error guardando filtros de sellos: {e}")

    def show_producers_filter_dialog(self):
        """Muestra un diálogo para filtrar por productores."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar por Productores")
            dialog.setMinimumWidth(800)
            dialog.setMinimumHeight(600)
            
            layout = QVBoxLayout()
            
            # Tres comboboxes para diferentes tipos de productores
            combos_layout = QHBoxLayout()
            
            # Productores
            producers_layout = QVBoxLayout()
            producers_label = QLabel("Productores:")
            self.producers_combo = QComboBox()
            self.producers_combo.setEditable(True)
            producers_layout.addWidget(producers_label)
            producers_layout.addWidget(self.producers_combo)
            
            # Ingenieros
            engineers_layout = QVBoxLayout()
            engineers_label = QLabel("Ingenieros:")
            self.engineers_combo = QComboBox()
            self.engineers_combo.setEditable(True)
            engineers_layout.addWidget(engineers_label)
            engineers_layout.addWidget(self.engineers_combo)
            
            # Ingenieros de masterización
            mastering_layout = QVBoxLayout()
            mastering_label = QLabel("Mastering:")
            self.mastering_combo = QComboBox()
            self.mastering_combo.setEditable(True)
            mastering_layout.addWidget(mastering_label)
            mastering_layout.addWidget(self.mastering_combo)
            
            combos_layout.addLayout(producers_layout)
            combos_layout.addLayout(engineers_layout)
            combos_layout.addLayout(mastering_layout)
            layout.addLayout(combos_layout)
            
            # Tabla
            self.producers_table = QTableWidget()
            self.producers_table.setColumnCount(3)
            self.producers_table.setHorizontalHeaderLabels(["Seleccionar", "Tipo", "Nombre"])
            self.producers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.producers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.producers_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.producers_table)
            
            # Botones específicos
            buttons_layout = QHBoxLayout()
            select_all_btn = QPushButton("Seleccionar Todo")
            deselect_all_btn = QPushButton("Deseleccionar Todo")
            add_producer_btn = QPushButton("Añadir Productor")
            add_engineer_btn = QPushButton("Añadir Ingeniero")
            add_mastering_btn = QPushButton("Añadir Mastering")
            
            buttons_layout.addWidget(select_all_btn)
            buttons_layout.addWidget(deselect_all_btn)
            buttons_layout.addWidget(add_producer_btn)
            buttons_layout.addWidget(add_engineer_btn)
            buttons_layout.addWidget(add_mastering_btn)
            layout.addLayout(buttons_layout)
            
            # Botones de diálogo
            dialog_buttons = QHBoxLayout()
            save_btn = QPushButton("Guardar")
            cancel_btn = QPushButton("Cancelar")
            dialog_buttons.addWidget(save_btn)
            dialog_buttons.addWidget(cancel_btn)
            layout.addLayout(dialog_buttons)
            
            dialog.setLayout(layout)
            
            # Cargar datos
            self._load_producers_data()
            
            # Conectar señales
            add_producer_btn.clicked.connect(lambda: self._add_producer_filter("Productor"))
            add_engineer_btn.clicked.connect(lambda: self._add_producer_filter("Ingeniero"))
            add_mastering_btn.clicked.connect(lambda: self._add_producer_filter("Mastering"))
            select_all_btn.clicked.connect(lambda: self._select_all_producers(True))
            deselect_all_btn.clicked.connect(lambda: self._select_all_producers(False))
            save_btn.clicked.connect(lambda: self._save_producers_filters(dialog))
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
            
        except Exception as e:
            print(f"Error en filtro de productores: {e}")
            self.show_error_message("Error", f"Error en filtro de productores: {e}")

    def _load_producers_data(self):
        """Carga los datos de productores."""
        try:
            # Productores
            self.cursor.execute("""
                SELECT DISTINCT producers FROM albums 
                WHERE producers IS NOT NULL AND producers != '' 
                ORDER BY producers
            """)
            producers = []
            for row in self.cursor.fetchall():
                prods = [p.strip() for p in row[0].split(',')]
                producers.extend(prods)
            self.producers_combo.addItems(sorted(set(producers)))
            
            # Ingenieros
            self.cursor.execute("""
                SELECT DISTINCT engineers FROM albums 
                WHERE engineers IS NOT NULL AND engineers != '' 
                ORDER BY engineers
            """)
            engineers = []
            for row in self.cursor.fetchall():
                engs = [e.strip() for e in row[0].split(',')]
                engineers.extend(engs)
            self.engineers_combo.addItems(sorted(set(engineers)))
            
            # Ingenieros de masterización
            self.cursor.execute("""
                SELECT DISTINCT mastering_engineers FROM albums 
                WHERE mastering_engineers IS NOT NULL AND mastering_engineers != '' 
                ORDER BY mastering_engineers
            """)
            mastering = []
            for row in self.cursor.fetchall():
                masts = [m.strip() for m in row[0].split(',')]
                mastering.extend(masts)
            self.mastering_combo.addItems(sorted(set(mastering)))
            
        except Exception as e:
            print(f"Error cargando datos de productores: {e}")

    def _add_producer_filter(self, producer_type):
        """Añade un filtro de productor según el tipo."""
        try:
            if producer_type == "Productor":
                value = self.producers_combo.currentText()
            elif producer_type == "Ingeniero":
                value = self.engineers_combo.currentText()
            else:  # Mastering
                value = self.mastering_combo.currentText()
            
            if not value:
                return
            
            # Verificar si ya existe
            for row in range(self.producers_table.rowCount()):
                if (self.producers_table.item(row, 1).text() == producer_type and 
                    self.producers_table.item(row, 2).text() == value):
                    return
            
            # Añadir nueva fila
            row = self.producers_table.rowCount()
            self.producers_table.insertRow(row)
            
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.producers_table.setCellWidget(row, 0, checkbox)
            self.producers_table.setItem(row, 1, QTableWidgetItem(producer_type))
            self.producers_table.setItem(row, 2, QTableWidgetItem(value))
            
        except Exception as e:
            print(f"Error añadiendo filtro de productor: {e}")

    def _select_all_producers(self, checked):
        """Selecciona todos los productores."""
        for row in range(self.producers_table.rowCount()):
            checkbox = self.producers_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)

    def _save_producers_filters(self, dialog):
        """Guarda los filtros de productores."""
        try:
            selected_filters = {"producers": [], "engineers": [], "mastering": []}
            
            for row in range(self.producers_table.rowCount()):
                checkbox = self.producers_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    producer_type = self.producers_table.item(row, 1).text().lower()
                    value = self.producers_table.item(row, 2).text()
                    
                    if producer_type == "productor":
                        selected_filters["producers"].append(value)
                    elif producer_type == "ingeniero":
                        selected_filters["engineers"].append(value)
                    else:
                        selected_filters["mastering"].append(value)
            
            if not hasattr(self, 'advanced_filters'):
                self.advanced_filters = {}
            self.advanced_filters['producers'] = selected_filters
            
            dialog.accept()
            
        except Exception as e:
            print(f"Error guardando filtros de productores: {e}")

    def show_listens_filter_dialog(self):
        """Muestra un diálogo para filtrar por escuchas (temporales)."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar por Escuchas")
            dialog.setMinimumWidth(800)
            dialog.setMinimumHeight(600)
            
            layout = QVBoxLayout()
            
            # Tres comboboxes para diferentes períodos
            combos_layout = QHBoxLayout()
            
            # Meses
            months_layout = QVBoxLayout()
            months_label = QLabel("Meses:")
            self.months_combo = QComboBox()
            self.months_combo.setEditable(True)
            months_items = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            self.months_combo.addItems(months_items)
            months_layout.addWidget(months_label)
            months_layout.addWidget(self.months_combo)
            
            # Años
            years_layout = QVBoxLayout()
            years_label = QLabel("Años:")
            self.listen_years_combo = QComboBox()
            self.listen_years_combo.setEditable(True)
            years_layout.addWidget(years_label)
            years_layout.addWidget(self.listen_years_combo)
            
            # Períodos recientes
            recent_layout = QVBoxLayout()
            recent_label = QLabel("Recientes:")
            self.recent_combo = QComboBox()
            recent_items = ["Últimas 24 horas", "Última semana", "Último mes", "Último año"]
            self.recent_combo.addItems(recent_items)
            recent_layout.addWidget(recent_label)
            recent_layout.addWidget(self.recent_combo)
            
            combos_layout.addLayout(months_layout)
            combos_layout.addLayout(years_layout)
            combos_layout.addLayout(recent_layout)
            layout.addLayout(combos_layout)
            
            # Tabla
            self.listens_table = QTableWidget()
            self.listens_table.setColumnCount(3)
            self.listens_table.setHorizontalHeaderLabels(["Seleccionar", "Tipo", "Período"])
            self.listens_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.listens_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.listens_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.listens_table)
            
            # Botones específicos
            buttons_layout = QHBoxLayout()
            select_all_btn = QPushButton("Seleccionar Todo")
            deselect_all_btn = QPushButton("Deseleccionar Todo")
            add_month_btn = QPushButton("Añadir Mes")
            add_year_btn = QPushButton("Añadir Año")
            add_recent_btn = QPushButton("Añadir Reciente")
            
            buttons_layout.addWidget(select_all_btn)
            buttons_layout.addWidget(deselect_all_btn)
            buttons_layout.addWidget(add_month_btn)
            buttons_layout.addWidget(add_year_btn)
            buttons_layout.addWidget(add_recent_btn)
            layout.addLayout(buttons_layout)
            
            # Botones de diálogo
            dialog_buttons = QHBoxLayout()
            save_btn = QPushButton("Guardar")
            cancel_btn = QPushButton("Cancelar")
            dialog_buttons.addWidget(save_btn)
            dialog_buttons.addWidget(cancel_btn)
            layout.addLayout(dialog_buttons)
            
            dialog.setLayout(layout)
            
            # Cargar años disponibles de escuchas
            self._load_listen_years()
            
            # Conectar señales
            add_month_btn.clicked.connect(lambda: self._add_listen_filter("Mes"))
            add_year_btn.clicked.connect(lambda: self._add_listen_filter("Año"))
            add_recent_btn.clicked.connect(lambda: self._add_listen_filter("Reciente"))
            select_all_btn.clicked.connect(lambda: self._select_all_listens(True))
            deselect_all_btn.clicked.connect(lambda: self._select_all_listens(False))
            save_btn.clicked.connect(lambda: self._save_listens_filters(dialog))
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
            
        except Exception as e:
            print(f"Error en filtro de escuchas: {e}")
            self.show_error_message("Error", f"Error en filtro de escuchas: {e}")

    def _load_listen_years(self):
        """Carga los años disponibles de escuchas."""
        try:
            # Obtener años de la tabla de escuchas si existe
            self.cursor.execute("""
                SELECT name FROM sqlite_master WHERE type='table' AND name='listens'
            """)
            if self.cursor.fetchone():
                self.cursor.execute("""
                    SELECT DISTINCT strftime('%Y', listen_date) as year
                    FROM listens 
                    WHERE listen_date IS NOT NULL
                    ORDER BY year DESC
                """)
                years = [row[0] for row in self.cursor.fetchall()]
                self.listen_years_combo.addItems(years)
            else:
                # Si no existe la tabla, usar años actuales
                from datetime import datetime
                current_year = datetime.now().year
                years = [str(year) for year in range(current_year - 10, current_year + 1)]
                self.listen_years_combo.addItems(reversed(years))
            
        except Exception as e:
            print(f"Error cargando años de escuchas: {e}")

    def _add_listen_filter(self, filter_type):
        """Añade un filtro de escuchas."""
        try:
            if filter_type == "Mes":
                value = self.months_combo.currentText()
            elif filter_type == "Año":
                value = self.listen_years_combo.currentText()
            else:  # Reciente
                value = self.recent_combo.currentText()
            
            if not value:
                return
            
            # Verificar si ya existe
            for row in range(self.listens_table.rowCount()):
                if (self.listens_table.item(row, 1).text() == filter_type and 
                    self.listens_table.item(row, 2).text() == value):
                    return
            
            # Añadir nueva fila
            row = self.listens_table.rowCount()
            self.listens_table.insertRow(row)
            
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.listens_table.setCellWidget(row, 0, checkbox)
            self.listens_table.setItem(row, 1, QTableWidgetItem(filter_type))
            self.listens_table.setItem(row, 2, QTableWidgetItem(value))
            
        except Exception as e:
            print(f"Error añadiendo filtro de escuchas: {e}")

    def _select_all_listens(self, checked):
        """Selecciona todas las escuchas."""
        for row in range(self.listens_table.rowCount()):
            checkbox = self.listens_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)

    def _save_listens_filters(self, dialog):
        """Guarda los filtros de escuchas."""
        try:
            selected_filters = {"months": [], "years": [], "recent": []}
            
            for row in range(self.listens_table.rowCount()):
                checkbox = self.listens_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    filter_type = self.listens_table.item(row, 1).text().lower()
                    value = self.listens_table.item(row, 2).text()
                    
                    if filter_type == "mes":
                        selected_filters["months"].append(value)
                    elif filter_type == "año":
                        selected_filters["years"].append(value)
                    else:
                        selected_filters["recent"].append(value)
            
            if not hasattr(self, 'advanced_filters'):
                self.advanced_filters = {}
            self.advanced_filters['listens'] = selected_filters
            
            dialog.accept()
            
        except Exception as e:
            print(f"Error guardando filtros de escuchas: {e}")

    def show_lyrics_filter_dialog(self):
        """Muestra un diálogo para filtrar por letras."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar por Letras")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(300)
            
            layout = QVBoxLayout()
            
            # Instrucciones
            instructions = QLabel("Introduce el texto que debe aparecer en las letras de las canciones:")
            instructions.setWordWrap(True)
            layout.addWidget(instructions)
            
            # Campo de texto
            self.lyrics_edit = QLineEdit()
            self.lyrics_edit.setPlaceholderText("Escribe aquí el texto a buscar en las letras...")
            layout.addWidget(self.lyrics_edit)
            
            # Opciones de búsqueda
            options_group = QGroupBox("Opciones de búsqueda")
            options_layout = QVBoxLayout()
            
            self.case_sensitive_check = QCheckBox("Distinguir entre mayúsculas y minúsculas")
            self.whole_words_check = QCheckBox("Solo palabras completas")
            
            options_layout.addWidget(self.case_sensitive_check)
            options_layout.addWidget(self.whole_words_check)
            options_group.setLayout(options_layout)
            layout.addWidget(options_group)
            
            # Vista previa de resultados
            preview_label = QLabel("Vista previa (primeras 10 canciones encontradas):")
            layout.addWidget(preview_label)
            
            self.lyrics_preview = QTableWidget()
            self.lyrics_preview.setColumnCount(3)
            self.lyrics_preview.setHorizontalHeaderLabels(["Artista", "Canción", "Fragmento"])
            self.lyrics_preview.setMaximumHeight(200)
            layout.addWidget(self.lyrics_preview)
            
            # Botón de vista previa
            preview_btn = QPushButton("Vista Previa")
            preview_btn.clicked.connect(self._preview_lyrics_search)
            layout.addWidget(preview_btn)
            
            # Botones de diálogo
            buttons_layout = QHBoxLayout()
            save_btn = QPushButton("Aplicar Filtro")
            cancel_btn = QPushButton("Cancelar")
            
            save_btn.clicked.connect(lambda: self._save_lyrics_filter(dialog))
            cancel_btn.clicked.connect(dialog.reject)
            
            buttons_layout.addWidget(save_btn)
            buttons_layout.addWidget(cancel_btn)
            layout.addLayout(buttons_layout)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            print(f"Error en filtro de letras: {e}")
            self.show_error_message("Error", f"Error en filtro de letras: {e}")

    def _preview_lyrics_search(self):
        """Muestra una vista previa de la búsqueda en letras."""
        try:
            search_text = self.lyrics_edit.text().strip()
            if not search_text:
                return
            
            # Construir la consulta SQL
            if self.case_sensitive_check.isChecked():
                if self.whole_words_check.isChecked():
                    # Búsqueda de palabras completas sensible a mayúsculas
                    condition = f"lyrics REGEXP '\\b{search_text}\\b'"
                else:
                    # Búsqueda normal sensible a mayúsculas
                    condition = f"lyrics LIKE '%{search_text}%'"
            else:
                if self.whole_words_check.isChecked():
                    # Búsqueda de palabras completas insensible a mayúsculas
                    condition = f"LOWER(lyrics) REGEXP '\\b{search_text.lower()}\\b'"
                else:
                    # Búsqueda normal insensible a mayúsculas
                    condition = f"LOWER(lyrics) LIKE '%{search_text.lower()}%'"
            
            # Ejecutar consulta
            query = f"""
                SELECT artist, title, lyrics
                FROM songs 
                WHERE lyrics IS NOT NULL AND lyrics != '' AND {condition}
                LIMIT 10
            """
            
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            
            # Mostrar resultados en la tabla
            self.lyrics_preview.setRowCount(len(results))
            
            for row, (artist, title, lyrics) in enumerate(results):
                self.lyrics_preview.setItem(row, 0, QTableWidgetItem(artist or ""))
                self.lyrics_preview.setItem(row, 1, QTableWidgetItem(title or ""))
                
                # Mostrar un fragmento de las letras con contexto
                fragment = self._extract_lyrics_fragment(lyrics, search_text)
                self.lyrics_preview.setItem(row, 2, QTableWidgetItem(fragment))
            
            # Ajustar columnas
            self.lyrics_preview.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error en vista previa de letras: {e}")

    def _extract_lyrics_fragment(self, lyrics, search_text, context_chars=100):
        """Extrae un fragmento de las letras con contexto alrededor del texto buscado."""
        try:
            if not lyrics or not search_text:
                return ""
            
            # Buscar la posición del texto
            if self.case_sensitive_check.isChecked():
                pos = lyrics.find(search_text)
            else:
                pos = lyrics.lower().find(search_text.lower())
            
            if pos == -1:
                return lyrics[:context_chars] + "..." if len(lyrics) > context_chars else lyrics
            
            # Extraer contexto
            start = max(0, pos - context_chars // 2)
            end = min(len(lyrics), pos + len(search_text) + context_chars // 2)
            
            fragment = lyrics[start:end]
            
            # Añadir puntos suspensivos si es necesario
            if start > 0:
                fragment = "..." + fragment
            if end < len(lyrics):
                fragment = fragment + "..."
            
            return fragment
            
        except Exception as e:
            print(f"Error extrayendo fragmento: {e}")
            return ""

    def _save_lyrics_filter(self, dialog):
        """Guarda el filtro de letras."""
        try:
            search_text = self.lyrics_edit.text().strip()
            if not search_text:
                self.show_error_message("Error", "Debe introducir un texto para buscar")
                return
            
            filter_config = {
                "text": search_text,
                "case_sensitive": self.case_sensitive_check.isChecked(),
                "whole_words": self.whole_words_check.isChecked()
            }
            
            if not hasattr(self, 'advanced_filters'):
                self.advanced_filters = {}
            self.advanced_filters['lyrics'] = filter_config
            
            dialog.accept()
            
        except Exception as e:
            print(f"Error guardando filtro de letras: {e}")

    def show_favorites_filter_dialog(self):
        """Muestra un diálogo para filtrar por favoritos."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Filtrar por Favoritos")
            dialog.setMinimumWidth(400)
            dialog.setMinimumHeight(300)
            
            layout = QVBoxLayout()
            
            # Instrucciones
            instructions = QLabel("Selecciona qué tipos de favoritos incluir en el quiz:")
            instructions.setWordWrap(True)
            layout.addWidget(instructions)
            
            # Checkboxes para tipos de favoritos
            self.favorite_artists_check = QCheckBox("Artistas favoritos")
            self.favorite_albums_check = QCheckBox("Álbumes favoritos")
            self.favorite_songs_check = QCheckBox("Canciones favoritas")
            
            layout.addWidget(self.favorite_artists_check)
            layout.addWidget(self.favorite_albums_check)
            layout.addWidget(self.favorite_songs_check)
            
            # Información sobre favoritos encontrados
            info_group = QGroupBox("Información")
            info_layout = QVBoxLayout()
            
            self.artists_count_label = QLabel("Artistas favoritos: Calculando...")
            self.albums_count_label = QLabel("Álbumes favoritos: Calculando...")
            self.songs_count_label = QLabel("Canciones favoritas: Calculando...")
            
            info_layout.addWidget(self.artists_count_label)
            info_layout.addWidget(self.albums_count_label)
            info_layout.addWidget(self.songs_count_label)
            info_group.setLayout(info_layout)
            layout.addWidget(info_group)
            
            # Botones de diálogo
            buttons_layout = QHBoxLayout()
            save_btn = QPushButton("Aplicar Filtro")
            cancel_btn = QPushButton("Cancelar")
            
            save_btn.clicked.connect(lambda: self._save_favorites_filter(dialog))
            cancel_btn.clicked.connect(dialog.reject)
            
            buttons_layout.addWidget(save_btn)
            buttons_layout.addWidget(cancel_btn)
            layout.addLayout(buttons_layout)
            
            dialog.setLayout(layout)
            
            # Cargar información de favoritos
            self._load_favorites_info()
            
            dialog.exec()
            
        except Exception as e:
            print(f"Error en filtro de favoritos: {e}")
            self.show_error_message("Error", f"Error en filtro de favoritos: {e}")

    def _load_favorites_info(self):
        """Carga información sobre los favoritos disponibles."""
        try:
            # Contar artistas favoritos
            self.cursor.execute("""
                SELECT COUNT(*) FROM artists WHERE favorita = 1
            """)
            artists_count = self.cursor.fetchone()[0]
            self.artists_count_label.setText(f"Artistas favoritos: {artists_count}")
            
            # Contar álbumes favoritos
            self.cursor.execute("""
                SELECT COUNT(*) FROM albums WHERE favorita = 1
            """)
            albums_count = self.cursor.fetchone()[0]
            self.albums_count_label.setText(f"Álbumes favoritos: {albums_count}")
            
            # Contar canciones favoritas
            self.cursor.execute("""
                SELECT COUNT(*) FROM songs WHERE favorita = 1
            """)
            songs_count = self.cursor.fetchone()[0]
            self.songs_count_label.setText(f"Canciones favoritas: {songs_count}")
            
        except Exception as e:
            print(f"Error cargando información de favoritos: {e}")
            # Establecer valores por defecto si hay error
            self.artists_count_label.setText("Artistas favoritos: Error al cargar")
            self.albums_count_label.setText("Álbumes favoritos: Error al cargar")
            self.songs_count_label.setText("Canciones favoritas: Error al cargar")

    def _save_favorites_filter(self, dialog):
        """Guarda el filtro de favoritos."""
        try:
            filter_config = {
                "artists": self.favorite_artists_check.isChecked(),
                "albums": self.favorite_albums_check.isChecked(),
                "songs": self.favorite_songs_check.isChecked()
            }
            
            # Verificar que al menos una opción esté seleccionada
            if not any(filter_config.values()):
                self.show_error_message("Error", "Debe seleccionar al menos un tipo de favorito")
                return
            
            if not hasattr(self, 'advanced_filters'):
                self.advanced_filters = {}
            self.advanced_filters['favorites'] = filter_config
            
            dialog.accept()
            
        except Exception as e:
            print(f"Error guardando filtro de favoritos: {e}")

    def _setup_filter_dialog_buttons(self, layout, dialog, add_func, select_all_func, save_func):
        """Configuración común de botones para diálogos de filtros."""
        # Botones de selección
        buttons_layout = QHBoxLayout()
        select_all_btn = QPushButton("Seleccionar Todo")
        deselect_all_btn = QPushButton("Deseleccionar Todo")
        add_btn = QPushButton("Añadir")
        
        buttons_layout.addWidget(select_all_btn)
        buttons_layout.addWidget(deselect_all_btn)
        buttons_layout.addWidget(add_btn)
        layout.addLayout(buttons_layout)
        
        # Botones de diálogo
        dialog_buttons = QHBoxLayout()
        save_btn = QPushButton("Guardar")
        cancel_btn = QPushButton("Cancelar")
        dialog_buttons.addWidget(save_btn)
        dialog_buttons.addWidget(cancel_btn)
        layout.addLayout(dialog_buttons)
        
        # Conectar señales
        add_btn.clicked.connect(add_func)
        select_all_btn.clicked.connect(lambda: select_all_func(True))
        deselect_all_btn.clicked.connect(lambda: select_all_func(False))
        save_btn.clicked.connect(lambda: save_func(dialog))
        cancel_btn.clicked.connect(dialog.reject)

    # Método para conectar los nuevos filtros en el diálogo principal
    def connect_new_filter_buttons(self, dialog):
        """Conecta los botones de los nuevos filtros en el diálogo de configuración avanzada."""
        try:
            # Conectar botones de filtros avanzados
            if hasattr(dialog, 'filter_time_btn'):
                dialog.filter_time_btn.clicked.connect(self.show_time_filter_dialog)
            if hasattr(dialog, 'filter_countries_btn'):
                dialog.filter_countries_btn.clicked.connect(self.show_countries_filter_dialog)
            if hasattr(dialog, 'filter_genres_btn'):
                dialog.filter_genres_btn.clicked.connect(self.show_genres_filter_dialog)
            if hasattr(dialog, 'filter_sellos_btn'):
                dialog.filter_sellos_btn.clicked.connect(self.show_labels_filter_dialog)
            if hasattr(dialog, 'filter_productores_btn'):
                dialog.filter_productores_btn.clicked.connect(self.show_producers_filter_dialog)
            if hasattr(dialog, 'filter_listens_btn'):
                dialog.filter_listens_btn.clicked.connect(self.show_listens_filter_dialog)
            if hasattr(dialog, 'filter_letras_btn'):
                dialog.filter_letras_btn.clicked.connect(self.show_lyrics_filter_dialog)
            if hasattr(dialog, 'filter_favs_btn'):
                dialog.filter_favs_btn.clicked.connect(self.show_favorites_filter_dialog)
                
            print("Botones de filtros avanzados conectados correctamente")
            
        except Exception as e:
            print(f"Error conectando botones de filtros: {e}")

    # Método para aplicar los filtros avanzados en las consultas SQL
    def apply_advanced_filters_to_query(self, base_query, params):
        """
        Aplica los filtros avanzados a una consulta SQL base.
        
        Args:
            base_query (str): Consulta SQL base
            params (list): Parámetros de la consulta
            
        Returns:
            tuple: (query_modificada, params_modificados)
        """
        try:
            if not hasattr(self, 'advanced_filters') or not self.advanced_filters:
                return base_query, params
            
            additional_conditions = []
            
            # Filtro de tiempo
            if 'time' in self.advanced_filters:
                time_filter = self.advanced_filters['time']
                time_conditions = []
                
                if time_filter.get('decades'):
                    decade_conditions = []
                    for decade in time_filter['decades']:
                        decade_conditions.append("SUBSTR(s.album_year, 1, 3) || '0' = ?")
                        params.append(decade)
                    if decade_conditions:
                        time_conditions.append(f"({' OR '.join(decade_conditions)})")
                
                if time_filter.get('years'):
                    year_conditions = []
                    for year in time_filter['years']:
                        year_conditions.append("s.album_year = ?")
                        params.append(year)
                    if year_conditions:
                        time_conditions.append(f"({' OR '.join(year_conditions)})")
                
                if time_conditions:
                    additional_conditions.append(f"({' OR '.join(time_conditions)})")
            
            # Filtro de países
            if 'countries' in self.advanced_filters and self.advanced_filters['countries']:
                country_placeholders = ', '.join(['?' for _ in self.advanced_filters['countries']])
                additional_conditions.append(f"s.country IN ({country_placeholders})")
                params.extend(self.advanced_filters['countries'])
            
            # Filtro de géneros
            if 'genres' in self.advanced_filters:
                genre_filter = self.advanced_filters['genres']
                genre_conditions = []
                
                if genre_filter.get('songs'):
                    song_genre_conditions = []
                    for genre in genre_filter['songs']:
                        song_genre_conditions.append("s.genre = ?")
                        params.append(genre)
                    if song_genre_conditions:
                        genre_conditions.append(f"({' OR '.join(song_genre_conditions)})")
                
                if genre_filter.get('artists'):
                    for tag in genre_filter['artists']:
                        genre_conditions.append("""
                            EXISTS (SELECT 1 FROM artists ar 
                            WHERE ar.name = s.artist 
                            AND ar.tags LIKE ?)
                        """)
                        params.append(f"%{tag}%")
                
                if genre_filter.get('discogs'):
                    for discogs_genre in genre_filter['discogs']:
                        genre_conditions.append("""
                            EXISTS (SELECT 1 FROM discogs_discography d 
                            WHERE d.artist = s.artist 
                            AND (d.genres LIKE ? OR d.styles LIKE ?))
                        """)
                        params.extend([f"%{discogs_genre}%", f"%{discogs_genre}%"])
                
                if genre_conditions:
                    additional_conditions.append(f"({' OR '.join(genre_conditions)})")
            
            # Filtro de sellos
            if 'labels' in self.advanced_filters and self.advanced_filters['labels']:
                label_placeholders = ', '.join(['?' for _ in self.advanced_filters['labels']])
                additional_conditions.append(f"s.label IN ({label_placeholders})")
                params.extend(self.advanced_filters['labels'])
            
            # Filtro de productores
            if 'producers' in self.advanced_filters:
                producer_filter = self.advanced_filters['producers']
                producer_conditions = []
                
                if producer_filter.get('producers'):
                    for producer in producer_filter['producers']:
                        producer_conditions.append("""
                            EXISTS (SELECT 1 FROM albums alb 
                            WHERE alb.name = s.album 
                            AND alb.artist_id = (SELECT id FROM artists WHERE name = s.artist)
                            AND alb.producers LIKE ?)
                        """)
                        params.append(f"%{producer}%")
                
                if producer_filter.get('engineers'):
                    for engineer in producer_filter['engineers']:
                        producer_conditions.append("""
                            EXISTS (SELECT 1 FROM albums alb 
                            WHERE alb.name = s.album 
                            AND alb.artist_id = (SELECT id FROM artists WHERE name = s.artist)
                            AND alb.engineers LIKE ?)
                        """)
                        params.append(f"%{engineer}%")
                
                if producer_filter.get('mastering'):
                    for mastering in producer_filter['mastering']:
                        producer_conditions.append("""
                            EXISTS (SELECT 1 FROM albums alb 
                            WHERE alb.name = s.album 
                            AND alb.artist_id = (SELECT id FROM artists WHERE name = s.artist)
                            AND alb.mastering_engineers LIKE ?)
                        """)
                        params.append(f"%{mastering}%")
                
                if producer_conditions:
                    additional_conditions.append(f"({' OR '.join(producer_conditions)})")
            
            # Filtro de escuchas
            if 'listens' in self.advanced_filters:
                listen_filter = self.advanced_filters['listens']
                listen_conditions = []
                
                # Verificar si existe la tabla de escuchas
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='listens'")
                if self.cursor.fetchone():
                    if listen_filter.get('months'):
                        for month in listen_filter['months']:
                            month_num = self._get_month_number(month)
                            listen_conditions.append("""
                                EXISTS (SELECT 1 FROM listens l 
                                WHERE l.song_id = s.id 
                                AND strftime('%m', l.listen_date) = ?)
                            """)
                            params.append(f"{month_num:02d}")
                    
                    if listen_filter.get('years'):
                        for year in listen_filter['years']:
                            listen_conditions.append("""
                                EXISTS (SELECT 1 FROM listens l 
                                WHERE l.song_id = s.id 
                                AND strftime('%Y', l.listen_date) = ?)
                            """)
                            params.append(year)
                    
                    if listen_filter.get('recent'):
                        for recent in listen_filter['recent']:
                            if recent == "Últimas 24 horas":
                                listen_conditions.append("""
                                    EXISTS (SELECT 1 FROM listens l 
                                    WHERE l.song_id = s.id 
                                    AND l.listen_date >= datetime('now', '-1 day'))
                                """)
                            elif recent == "Última semana":
                                listen_conditions.append("""
                                    EXISTS (SELECT 1 FROM listens l 
                                    WHERE l.song_id = s.id 
                                    AND l.listen_date >= datetime('now', '-7 days'))
                                """)
                            elif recent == "Último mes":
                                listen_conditions.append("""
                                    EXISTS (SELECT 1 FROM listens l 
                                    WHERE l.song_id = s.id 
                                    AND l.listen_date >= datetime('now', '-1 month'))
                                """)
                            elif recent == "Último año":
                                listen_conditions.append("""
                                    EXISTS (SELECT 1 FROM listens l 
                                    WHERE l.song_id = s.id 
                                    AND l.listen_date >= datetime('now', '-1 year'))
                                """)
                    
                    if listen_conditions:
                        additional_conditions.append(f"({' OR '.join(listen_conditions)})")
                else:
                    print("Tabla 'listens' no encontrada, filtro de escuchas ignorado")
            
            # Filtro de letras
            if 'lyrics' in self.advanced_filters:
                lyrics_filter = self.advanced_filters['lyrics']
                search_text = lyrics_filter.get('text', '')
                
                if search_text:
                    # Escapar caracteres especiales para evitar inyección SQL
                    search_text = search_text.replace("'", "''")
                    
                    if lyrics_filter.get('case_sensitive', False):
                        if lyrics_filter.get('whole_words', False):
                            # Búsqueda de palabras completas sensible a mayúsculas usando LIKE
                            additional_conditions.append("s.lyrics LIKE ?")
                            params.append(f"% {search_text} %")
                        else:
                            # Búsqueda normal sensible a mayúsculas
                            additional_conditions.append("s.lyrics LIKE ?")
                            params.append(f"%{search_text}%")
                    else:
                        if lyrics_filter.get('whole_words', False):
                            # Búsqueda de palabras completas insensible a mayúsculas
                            additional_conditions.append("LOWER(s.lyrics) LIKE ?")
                            params.append(f"% {search_text.lower()} %")
                        else:
                            # Búsqueda normal insensible a mayúsculas
                            additional_conditions.append("LOWER(s.lyrics) LIKE ?")
                            params.append(f"%{search_text.lower()}%")
            
            # Filtro de favoritos
            if 'favorites' in self.advanced_filters:
                fav_filter = self.advanced_filters['favorites']
                fav_conditions = []
                
                if fav_filter.get('songs', False):
                    fav_conditions.append("s.favorita = 1")
                
                if fav_filter.get('albums', False):
                    fav_conditions.append("""
                        EXISTS (SELECT 1 FROM albums alb 
                        WHERE alb.name = s.album 
                        AND alb.artist_id = (SELECT id FROM artists WHERE name = s.artist)
                        AND alb.favorita = 1)
                    """)
                
                if fav_filter.get('artists', False):
                    fav_conditions.append("""
                        EXISTS (SELECT 1 FROM artists ar 
                        WHERE ar.name = s.artist 
                        AND ar.favorita = 1)
                    """)
                
                if fav_conditions:
                    additional_conditions.append(f"({' OR '.join(fav_conditions)})")
            
            # Agregar todas las condiciones adicionales a la consulta
            if additional_conditions:
                # Buscar dónde insertar las condiciones
                base_query_upper = base_query.upper()
                
                if 'WHERE' in base_query_upper:
                    # Ya hay una cláusula WHERE, agregar con AND
                    base_query += f" AND ({' AND '.join(additional_conditions)})"
                else:
                    # No hay cláusula WHERE, agregar una
                    # Buscar dónde insertarla (antes de ORDER BY, GROUP BY, LIMIT, etc.)
                    insert_keywords = ['ORDER BY', 'GROUP BY', 'HAVING', 'LIMIT', 'OFFSET']
                    insert_pos = len(base_query)
                    
                    for keyword in insert_keywords:
                        pos = base_query_upper.find(keyword)
                        if pos != -1 and pos < insert_pos:
                            insert_pos = pos
                    
                    if insert_pos < len(base_query):
                        # Insertar WHERE antes de la primera cláusula encontrada
                        base_query = (base_query[:insert_pos].strip() + 
                                    f" WHERE {' AND '.join(additional_conditions)} " + 
                                    base_query[insert_pos:])
                    else:
                        # Agregar WHERE al final
                        base_query += f" WHERE {' AND '.join(additional_conditions)}"
            
            return base_query, params
            
        except Exception as e:
            print(f"Error aplicando filtros avanzados: {e}")
            import traceback
            traceback.print_exc()
            return base_query, params