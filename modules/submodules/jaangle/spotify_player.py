# spotify_player.py - Solución utilizando Spotipy y reproductor nativo
from PyQt6.QtCore import QObject, pyqtSignal, QUrl, Qt, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import sqlite3
import logging
import os
import time
import traceback
import json
import shutil
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpotifyPlayer(QObject):
    """Submódulo para manejar la reproducción de previews de Spotify en el quiz musical."""
    
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_error = pyqtSignal(str)
    
    def __init__(self, db_path=None, parent=None, config=None):
        super().__init__(parent)
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.current_track_id = None
        self.container = None
        self.message_label = None
        self.progress_bar = None
        self.config = config or {}
        self.current_song_id = None
        self.error_count = 0
        self.max_retries = 2
        
        # Crear instancia del reproductor de audio
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Configurar volumen
        self.audio_output.setVolume(0.8)  # 80% volumen
        
        # Conectar señales del reproductor
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.player.errorOccurred.connect(self.on_player_error)
        
        # Inicializar Spotipy si hay credenciales en la configuración
        self.sp = None
        self.init_spotipy()
        
        # Conectar a la base de datos
        self.connect_to_database()
    
    def init_spotipy(self):
        """Inicializa el cliente de Spotipy si hay credenciales disponibles"""
        try:
            # Intentar obtener credenciales de la configuración
            spotify_config = self.config.get('spotify', {})
            client_id = spotify_config.get('client_id')
            client_secret = spotify_config.get('client_secret')
            
            # Si no hay en la configuración, buscar en variables de entorno
            if not client_id or not client_secret:
                client_id = os.environ.get('SPOTIPY_CLIENT_ID')
                client_secret = os.environ.get('SPOTIPY_CLIENT_SECRET')
            
            # Si se encontraron credenciales, inicializar el cliente
            if client_id and client_secret:
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=client_id, 
                    client_secret=client_secret
                )
                self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
                logger.info("Cliente Spotipy inicializado correctamente")
            else:
                logger.warning("No se encontraron credenciales para Spotipy. "
                             "Se usarán métodos alternativos para obtener URLs de previsualización.")
                
        except Exception as e:
            logger.error(f"Error al inicializar Spotipy: {e}")
            logger.error(traceback.format_exc())
    
    def on_playback_state_changed(self, state):
        """Maneja los cambios en el estado de reproducción"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            logger.info("Reproducción iniciada")
            self.playback_started.emit()
            if self.message_label:
                self.message_label.setText("Reproduciendo canción desde Spotify...")
            if self.progress_bar:
                self.progress_bar.setValue(100)
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            logger.info("Reproducción detenida")
    
    def on_player_error(self, error, error_string):
        """Maneja errores del reproductor"""
        logger.error(f"Error del reproductor: {error_string} (código: {error})")
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            if self.message_label:
                self.message_label.setText(f"Reintentando reproducción... ({self.error_count}/{self.max_retries})")
            QTimer.singleShot(1000, self.retry_playback)
        else:
            if self.message_label:
                self.message_label.setText("Error al reproducir la canción")
            self.playback_error.emit(f"Error de reproducción: {error_string}")
    
    def connect_to_database(self):
        """Establece la conexión con la base de datos."""
        try:
            if not self.db_path:
                raise ValueError("No se proporcionó una ruta de base de datos válida")
            
            # Verificar que el archivo de base de datos existe
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Base de datos no encontrada: {self.db_path}")
            
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"SpotifyPlayer conectado a la base de datos: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error al conectar a la base de datos: {e}")
            self.playback_error.emit(f"Error de base de datos: {str(e)}")
    
    def get_preview_url_from_spotipy(self, track_id):
        """
        Obtiene la URL de previsualización directamente de la API de Spotify usando Spotipy.
        
        Args:
            track_id: ID de pista de Spotify
            
        Returns:
            URL de previsualización si está disponible, None en caso contrario
        """
        if not self.sp:
            logger.warning("Spotipy no está inicializado para obtener previsualización")
            return None
        
        try:
            # Obtener información de la pista de Spotify
            track_info = self.sp.track(track_id)
            
            # Extraer la URL de previsualización
            preview_url = track_info.get('preview_url')
            
            if preview_url:
                logger.info(f"URL de previsualización obtenida con Spotipy: {preview_url}")
                
                # Guardar en base de datos para futuras reproducciones
                self.save_preview_url(track_id, preview_url)
                
                return preview_url
            else:
                logger.warning(f"La pista {track_id} no tiene URL de previsualización disponible")
                return None
                
        except Exception as e:
            logger.error(f"Error al obtener URL de previsualización con Spotipy: {e}")
            return None
    
    def save_preview_url(self, track_id, preview_url):
        """Guarda la URL de previsualización en la base de datos"""
        try:
            # Primero verificar si el track_id está asociado a alguna canción
            self.cursor.execute("""
                SELECT song_id FROM song_links
                WHERE spotify_url LIKE ?
            """, (f"%{track_id}%",))
            
            result = self.cursor.fetchone()
            if not result:
                return
            
            song_id = result['song_id']
            
            # Actualizar la URL de previsualización en la base de datos
            self.cursor.execute("""
                UPDATE song_links
                SET preview_url = ?
                WHERE song_id = ?
            """, (preview_url, song_id))
            
            self.conn.commit()
            logger.info(f"URL de previsualización guardada para canción ID: {song_id}")
            
        except Exception as e:
            logger.error(f"Error al guardar URL de previsualización: {e}")
    
    def get_spotify_preview_url(self, song_id):
        """
        Intenta obtener la URL de previsualización directa de Spotify para una canción.
        
        Args:
            song_id: ID de la canción en la base de datos
                
        Returns:
            URL de previsualización si está disponible, None en caso contrario
        """
        try:
            # Primero intentar obtener preview_url directamente de la tabla song_links
            self.cursor.execute("""
                SELECT preview_url FROM song_links 
                WHERE song_id = ? AND preview_url IS NOT NULL AND preview_url != ''
            """, (song_id,))
            
            result = self.cursor.fetchone()
            if result and result['preview_url']:
                logger.info(f"URL de previsualización encontrada en tabla song_links: {result['preview_url']}")
                return result['preview_url']
            
            # Si no hay preview_url almacenada, intentar obtener spotify_id y construir una URL alternativa
            self.cursor.execute("""
                SELECT spotify_id FROM song_links 
                WHERE song_id = ? AND spotify_id IS NOT NULL AND spotify_id != ''
            """, (song_id,))
            
            result = self.cursor.fetchone()
            if result and result['spotify_id']:
                spotify_id = result['spotify_id']
                # Intenta construir una URL de previsualización usando el patrón conocido
                # Nota: Este patrón podría no funcionar para todas las canciones
                preview_url = f"https://p.scdn.co/mp3-preview/{spotify_id}"
                logger.info(f"Construyendo URL de previsualización alternativa: {preview_url}")
                
                # Guardar esta URL para usos futuros
                try:
                    self.cursor.execute("""
                        UPDATE song_links SET preview_url = ? WHERE song_id = ?
                    """, (preview_url, song_id))
                    self.conn.commit()
                except Exception as e:
                    logger.error(f"Error al guardar URL de previsualización: {e}")
                
                return preview_url
            
            # Si todo falla, intentar obtener spotify_url y extraer track_id para llamar a la API
            self.cursor.execute("""
                SELECT spotify_url FROM song_links 
                WHERE song_id = ? AND spotify_url IS NOT NULL
            """, (song_id,))
            
            result = self.cursor.fetchone()
            if result and result['spotify_url']:
                # Extraer el track_id de la URL
                track_id = self.get_track_id_from_url(result['spotify_url'])
                if track_id:
                    logger.info(f"Extraído track_id: {track_id} de URL: {result['spotify_url']}")
                    
                    # Construir URL de previsualización
                    preview_url = f"https://p.scdn.co/mp3-preview/{track_id}"
                    logger.info(f"Construyendo URL de previsualización: {preview_url}")
                    
                    # Guardar esta URL para usos futuros
                    try:
                        self.cursor.execute("""
                            UPDATE song_links SET preview_url = ? WHERE song_id = ?
                        """, (preview_url, song_id))
                        self.conn.commit()
                    except Exception as e:
                        logger.error(f"Error al guardar URL de previsualización: {e}")
                    
                    return preview_url
            
            logger.warning(f"No se encontró información suficiente para generar URL de previsualización para la canción ID: {song_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener URL de previsualización: {e}")
            return None
    
    def get_spotify_url(self, song_id):
        """
        Obtiene la URL de Spotify para una canción de la base de datos.
        
        Args:
            song_id: ID de la canción en la base de datos
            
        Returns:
            URL de Spotify si está disponible, None en caso contrario
        """
        try:
            # Buscar en song_links
            self.cursor.execute("""
                SELECT spotify_url FROM song_links 
                WHERE song_id = ? AND spotify_url IS NOT NULL
            """, (song_id,))
            
            result = self.cursor.fetchone()
            if not result:
                logger.warning(f"No se encontró URL de Spotify para la canción ID: {song_id}")
                return None
            
            return result['spotify_url']
            
        except Exception as e:
            logger.error(f"Error al obtener URL de Spotify: {e}")
            return None
    
    def get_track_id_from_url(self, spotify_url):
        """
        Extrae el ID de pista de Spotify de una URL.
        
        Args:
            spotify_url: URL de Spotify
            
        Returns:
            ID de pista extraído de la URL
        """
        if not spotify_url:
            return None
            
        # Formato esperado: https://open.spotify.com/track/2EzgGvgxrysDB5uXVpWUWY
        try:
            parts = spotify_url.split('/')
            if len(parts) > 4 and parts[3] == 'track':
                track_id = parts[4].split('?')[0]  # Remover parámetros de consulta si existen
                logger.info(f"ID de pista extraído con éxito: {track_id} de URL: {spotify_url}")
                return track_id
            else:
                logger.warning(f"Formato de URL no reconocido: {spotify_url}")
        except Exception as e:
            logger.error(f"Error al extraer ID de pista: {e}")
        
        return None

    def play_with_terminal_player(self, preview_url):
        """Reproduce el audio usando un reproductor de terminal"""
        try:
            # Detener cualquier proceso existente
            self.stop_process()
            
            # Verificar que la URL es válida
            if not preview_url:
                logger.error("URL de previsualización vacía")
                return False
            
            # Asegurarse de que la URL comienza con http
            if not preview_url.startswith('http'):
                logger.error(f"URL de previsualización no válida: {preview_url}")
                return False
            
            # Log para depuración
            logger.info(f"Reproduciendo URL: {preview_url}")
            
            # Seleccionar el reproductor disponible
            player_cmd = None
            
            if self.available_players['mpg123']:
                player_cmd = ['mpg123', '-q', preview_url]
            elif self.available_players['mplayer']:
                player_cmd = ['mplayer', '-really-quiet', preview_url]
            elif self.available_players['ffplay']:
                player_cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', preview_url]
            elif self.available_players['cvlc']:
                player_cmd = ['cvlc', '--play-and-exit', '--quiet', preview_url]
            else:
                logger.error("No hay reproductores de terminal disponibles")
                return False
            
            logger.info(f"Reproduciendo con: {' '.join(player_cmd)}")
            
            # Usar QProcess para manejar el proceso
            self.process = QProcess()
            self.process.finished.connect(self.on_process_finished)
            self.process.errorOccurred.connect(self.on_process_error)
            
            # Iniciar el proceso
            self.process.start(player_cmd[0], player_cmd[1:])
            
            # Verificar si el proceso ha iniciado correctamente
            started = self.process.waitForStarted(3000)  # Esperar 3 segundos máximo
            if started:
                logger.info("Proceso de reproducción iniciado correctamente")
                self.playback_started.emit()
                return True
            else:
                logger.error("No se pudo iniciar el proceso de reproducción")
                return False
            
        except Exception as e:
            logger.error(f"Error al reproducir con reproductor de terminal: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def play_with_direct_command(self, preview_url):
        """
        Reproduce directamente usando subprocess.
        Este es un método alternativo que no usa QProcess.
        """
        try:
            # Comprobar que la URL es válida
            if not preview_url or not preview_url.startswith('http'):
                logger.error(f"URL de previsualización no válida para reproducción directa: {preview_url}")
                return False
            
            # Seleccionar el reproductor disponible
            cmd = None
            
            if shutil.which('mpg123'):
                cmd = ['mpg123', '-q', preview_url]
            elif shutil.which('mplayer'):
                cmd = ['mplayer', '-really-quiet', preview_url]
            elif shutil.which('ffplay'):
                cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', preview_url]
            elif shutil.which('cvlc'):
                cmd = ['cvlc', '--play-and-exit', '--quiet', preview_url]
            else:
                logger.error("No hay reproductores de terminal disponibles para reproducción directa")
                return False
            
            logger.info(f"Reproduciendo directamente con: {' '.join(cmd)}")
            
            # Ejecutar en segundo plano
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                start_new_session=True  # Separar del proceso principal
            )
            
            # Esperar un poco y verificar que el proceso sigue ejecutándose
            time.sleep(0.5)
            if process.poll() is None:  # Si poll() es None, el proceso sigue ejecutándose
                logger.info("Proceso de reproducción directa iniciado correctamente")
                self.playback_started.emit()
                return True
            else:
                logger.error(f"El proceso terminó prematuramente con código: {process.returncode}")
                return False
                
        except Exception as e:
            logger.error(f"Error al reproducir directamente: {e}")
            logger.error(traceback.format_exc())
            return False


    def create_player_container(self):
        """
        Crea un contenedor simple para mostrar información del reproductor.
        
        Returns:
            Widget contenedor con información
        """
        if self.container is None:
            self.container = QWidget()
            layout = QVBoxLayout(self.container)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Crear una etiqueta informativa
            self.message_label = QLabel("Reproduciendo canción...")
            self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.message_label.setStyleSheet("""
                color: #1DB954;
                background-color: #181818;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            """)
            
            # Agregar una barra de progreso
            self.progress_bar = QProgressBar()
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #282828;
                    border-radius: 5px;
                    height: 6px;
                }
                QProgressBar::chunk {
                    background-color: #1DB954;
                    border-radius: 5px;
                }
            """)
            
            # Agregar widgets al layout
            layout.addWidget(self.message_label)
            layout.addWidget(self.progress_bar)
            
            # Reducir al mínimo el espacio que ocupa
            self.container.setFixedHeight(50)
            self.container.hide()  # Oculto por defecto
        
        return self.container
    
    def retry_playback(self):
        """Reintenta reproducir la canción con un método alternativo"""
        if not self.current_song_id:
            self.playback_error.emit("No hay canción actual para reintentar")
            return
        
        logger.info(f"Reintentando reproducción para canción ID: {self.current_song_id}")
        
        # Si hay un track_id de Spotify, intentar obtener la previsualización nuevamente
        if self.current_track_id and self.sp:
            preview_url = self.get_preview_url_from_spotipy(self.current_track_id)
            if preview_url:
                self.play_with_native_player(preview_url)
                return
        
        # Si no se pudo obtener, intentar reproducir la siguiente canción
        self.playback_error.emit("No se pudo reproducir la canción después de varios intentos")
    
    def play_with_native_player(self, preview_url):
        """Reproduce la URL de previsualización usando el reproductor nativo"""
        try:
            logger.info(f"Reproduciendo con reproductor nativo: {preview_url}")
            
            # Actualizar la interfaz
            if self.message_label:
                self.message_label.setText("Reproduciendo canción...")
            if self.progress_bar:
                self.progress_bar.setValue(50)
            
            # Configurar y reproducir
            self.player.setSource(QUrl(preview_url))
            self.player.play()
            
            return True
        except Exception as e:
            logger.error(f"Error al reproducir con reproductor nativo: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def play(self, song_id):
        """
        Reproduce una canción de Spotify usando un reproductor de terminal.
        
        Args:
            song_id: ID de la canción en la base de datos
            
        Returns:
            True si se pudo iniciar la reproducción, False en caso contrario
        """
        try:
            # Guardar el ID de la canción para posibles reintentos
            self.current_song_id = song_id
            self.error_count = 0
            
            # Detener cualquier reproducción anterior
            self.stop()
            
            # Restablecer y mostrar la UI
            if self.container and self.message_label:
                self.message_label.setText("Cargando reproductor de audio...")
                if self.progress_bar:
                    self.progress_bar.setValue(10)
                self.container.show()
            
            # Obtener la URL de previsualización
            preview_url = self.get_spotify_preview_url(song_id)
            if not preview_url:
                if self.message_label:
                    self.message_label.setText("Error: No se encontró URL de previsualización")
                self.playback_error.emit("No se encontró URL de previsualización para esta canción")
                return False
            
            # Log del preview_url para depuración
            logger.info(f"Intentando reproducir preview_url: {preview_url}")
            
            # Intentar reproducir con un reproductor de terminal
            if self.progress_bar:
                self.progress_bar.setValue(50)
            if self.message_label:
                self.message_label.setText("Reproduciendo canción desde Spotify...")
                
            success = self.play_with_terminal_player(preview_url)
            
            if not success:
                logger.warning("Reproducción con QProcess falló, intentando directamente")
                if self.message_label:
                    self.message_label.setText("Reintentando reproducción...")
                success = self.play_with_direct_command(preview_url)
            
            if success:
                if self.progress_bar:
                    self.progress_bar.setValue(100)
                if self.message_label:
                    self.message_label.setText("Reproduciendo preview de Spotify...")
            else:
                if self.message_label:
                    self.message_label.setText("No se pudo reproducir la canción")
                    
            return success
            
        except Exception as e:
            logger.error(f"Error al reproducir desde Spotify: {e}")
            logger.error(traceback.format_exc())
            self.playback_error.emit(f"Error al reproducir: {str(e)}")
            return False
    
    def stop(self):
        """
        Detiene la reproducción actual.
        
        Returns:
            True si se detuvo correctamente, False en caso contrario
        """
        try:
            # Detener el reproductor
            self.player.stop()
            
            # Ocultar el contenedor
            if self.container:
                self.container.hide()
            
            self.playback_stopped.emit()
            return True
        except Exception as e:
            logger.error(f"Error al detener reproducción: {e}")
            return False
    
    def close(self):
        """Cierra la conexión a la base de datos y limpia recursos."""
        self.stop()
        
        if self.conn:
            self.conn.close()
            logger.info("Conexión a la base de datos cerrada")