# listenbrainz_player.py - Submódulo para reproducir previsualizaciones usando ListenBrainz
from PyQt6.QtCore import QObject, pyqtSignal, QUrl, Qt, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import sqlite3
import logging
import os
import time
import traceback
import json
import requests
from urllib.parse import urljoin
from functools import lru_cache

# Importar PlayerManager para usar MPV
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tools.player_manager import PlayerManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ListenBrainzPlayer(QObject):
    """Submódulo para manejar la reproducción de previews de canciones usando MusicBrainz/ListenBrainz."""
    
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
        self.using_mpv = False
        self.current_youtube_url = None
        
        # Base URLs para APIs
        self.listenbrainz_api_url = "https://api.listenbrainz.org/1/"
        self.musicbrainz_api_url = "https://musicbrainz.org/ws/2/"
        self.coverartarchive_api_url = "https://coverartarchive.org/"
        
        # Headers para API requests
        self.headers = {
            'User-Agent': 'JaangleApp/1.0.0 (https://github.com/yourusername/jaangle)'
        }
        
        # Obtener token de ListenBrainz si existe en la configuración
        self.listenbrainz_token = None
        if 'listenbrainz' in self.config and 'token' in self.config['listenbrainz']:
            self.listenbrainz_token = self.config['listenbrainz']['token']
            self.headers['Authorization'] = f"Token {self.listenbrainz_token}"
        
        # Crear instancia del reproductor de audio nativo
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Configurar volumen
        self.audio_output.setVolume(0.8)  # 80% volumen
        
        # Conectar señales del reproductor
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.player.errorOccurred.connect(self.on_player_error)
        
        # Instanciar PlayerManager para usar MPV con YouTube
        self.player_manager = PlayerManager(config=self.config, parent=self, logger=self.log_message)
        
        # Conectar señales del player_manager
        self.player_manager.playback_started.connect(self.on_mpv_playback_started)
        self.player_manager.playback_stopped.connect(self.on_mpv_playback_stopped)
        self.player_manager.playback_error.connect(self.on_mpv_playback_error)
        self.player_manager.track_finished.connect(self.on_mpv_track_finished)
        
        # Conectar a la base de datos
        self.connect_to_database()
    
    def log_message(self, msg):
        """Método para logger del PlayerManager"""
        logger.info(f"PlayerManager: {msg}")
    
    def on_mpv_playback_started(self):
        """Maneja el inicio de reproducción en MPV"""
        logger.info("Reproducción MPV iniciada")
        self.playback_started.emit()
        if self.message_label:
            self.message_label.setText("Reproduciendo video de YouTube...")
        if self.progress_bar:
            self.progress_bar.setValue(100)
    
    def on_mpv_playback_stopped(self):
        """Maneja la detención de reproducción en MPV"""
        logger.info("Reproducción MPV detenida")
        self.playback_stopped.emit()
        
    def on_mpv_playback_error(self, error_message):
        """Maneja errores de reproducción en MPV"""
        logger.error(f"Error en reproductor MPV: {error_message}")
        self.playback_error.emit(f"Error en reproductor MPV: {error_message}")
        
    def on_mpv_track_finished(self):
        """Maneja finalización de pista en MPV"""
        logger.info("Pista MPV finalizada")
        # Si lo necesitas, puedes emitir una señal aquí o tomar alguna acción
    
    def on_playback_state_changed(self, state):
        """Maneja los cambios en el estado de reproducción"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            logger.info("Reproducción iniciada")
            self.playback_started.emit()
            if self.message_label:
                self.message_label.setText("Reproduciendo canción usando ListenBrainz...")
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
            logger.info(f"ListenBrainzPlayer conectado a la base de datos: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error al conectar a la base de datos: {e}")
            self.playback_error.emit(f"Error de base de datos: {str(e)}")
    
    def get_musicbrainz_recording_url(self, song_id):
        """
        Obtiene la URL de MusicBrainz para una grabación específica.
        
        Args:
            song_id: ID de la canción en la base de datos
            
        Returns:
            URL de MusicBrainz si está disponible, None en caso contrario
        """
        try:
            # Primero intentar obtener el MBID de la grabación directamente
            self.cursor.execute("""
                SELECT musicbrainz_recording_id FROM song_links 
                WHERE song_id = ? AND musicbrainz_recording_id IS NOT NULL AND musicbrainz_recording_id != ''
            """, (song_id,))
            
            result = self.cursor.fetchone()
            if result and result['musicbrainz_recording_id']:
                mbid = result['musicbrainz_recording_id']
                return f"https://musicbrainz.org/recording/{mbid}"
            
            # Intentar obtener el MBID genérico de la canción
            self.cursor.execute("""
                SELECT mbid FROM songs 
                WHERE id = ? AND mbid IS NOT NULL AND mbid != ''
            """, (song_id,))
            
            result = self.cursor.fetchone()
            if result and result['mbid']:
                mbid = result['mbid']
                return f"https://musicbrainz.org/recording/{mbid}"
            
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener URL de MusicBrainz: {e}")
            return None
    
    def get_recording_mbid(self, song_id):
        """
        Obtiene el MBID de grabación para una canción.
        
        Args:
            song_id: ID de la canción en la base de datos
            
        Returns:
            MBID de grabación si está disponible, None en caso contrario
        """
        try:
            # Primero intentar obtener directamente de song_links
            self.cursor.execute("""
                SELECT musicbrainz_recording_id FROM song_links 
                WHERE song_id = ? AND musicbrainz_recording_id IS NOT NULL AND musicbrainz_recording_id != ''
            """, (song_id,))
            
            result = self.cursor.fetchone()
            if result and result['musicbrainz_recording_id']:
                return result['musicbrainz_recording_id']
            
            # Intentar obtener el MBID genérico
            self.cursor.execute("""
                SELECT mbid FROM songs 
                WHERE id = ? AND mbid IS NOT NULL AND mbid != ''
            """, (song_id,))
            
            result = self.cursor.fetchone()
            if result and result['mbid']:
                return result['mbid']
            
            # Si no hay MBID directamente, intentar buscar la grabación en MusicBrainz
            # usando título, artista y álbum
            self.cursor.execute("""
                SELECT title, artist, album FROM songs 
                WHERE id = ?
            """, (song_id,))
            
            result = self.cursor.fetchone()
            if not result:
                return None
                
            # Intentar buscar en MusicBrainz usando la API
            title = result['title']
            artist = result['artist']
            album = result['album']
            
            if not title or not artist:
                return None
                
            mbid = self.search_musicbrainz_recording(title, artist, album)
            if mbid:
                # Guardar el MBID encontrado para futuras consultas
                try:
                    self.cursor.execute("""
                        INSERT OR REPLACE INTO song_links (song_id, musicbrainz_recording_id)
                        VALUES (?, ?)
                    """, (song_id, mbid))
                    self.conn.commit()
                except Exception as e:
                    logger.error(f"Error al guardar MBID de grabación: {e}")
                
                return mbid
            
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener MBID de grabación: {e}")
            return None
    
    @lru_cache(maxsize=128)
    def search_musicbrainz_recording(self, title, artist, album=None):
        """
        Busca un MBID de grabación en MusicBrainz usando título, artista y álbum.
        
        Args:
            title: Título de la canción
            artist: Nombre del artista
            album: Nombre del álbum (opcional)
            
        Returns:
            MBID de grabación si se encuentra, None en caso contrario
        """
        try:
            # Preparar la consulta
            query = f'recording:"{title}" AND artist:"{artist}"'
            if album:
                query += f' AND release:"{album}"'
            
            # Hacer la petición a MusicBrainz
            params = {
                'query': query,
                'fmt': 'json'
            }
            
            url = urljoin(self.musicbrainz_api_url, 'recording')
            response = requests.get(url, params=params, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Error en la búsqueda MusicBrainz: {response.status_code}")
                return None
            
            data = response.json()
            
            # Verificar si hay resultados
            if 'recordings' in data and data['recordings']:
                # Tomar el primer resultado que tenga MBID
                for recording in data['recordings']:
                    if 'id' in recording:
                        logger.info(f"MBID de grabación encontrado para '{title}' por '{artist}': {recording['id']}")
                        return recording['id']
            
            logger.warning(f"No se encontró MBID para '{title}' por '{artist}'")
            return None
            
        except Exception as e:
            logger.error(f"Error al buscar en MusicBrainz: {e}")
            return None
    
    def get_preview_url_from_listenbrainz(self, recording_mbid):
        """
        Intenta obtener una URL de previsualización a través de ListenBrainz/MusicBrainz
        sin requerir credenciales.
        
        Args:
            recording_mbid: MBID de la grabación en MusicBrainz
            
        Returns:
            URL de previsualización si está disponible, None en caso contrario
        """
        try:
            if not recording_mbid:
                return None
            
            # 1. Usar la API pública de ListenBrainz (no requiere autenticación)
            url = urljoin(self.listenbrainz_api_url, f"metadata/recording/{recording_mbid}")
            
            # Headers básicos sin token de autenticación
            headers = {
                'User-Agent': 'JaangleApp/1.0.0 (https://github.com/yourusername/jaangle)'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Buscar enlaces a servicios de streaming
                if 'metadata' in data and 'links' in data['metadata']:
                    links = data['metadata']['links']
                    
                    # Priorizar YouTube para usar con MPV
                    for link in links:
                        if 'youtube' in link.get('url', '').lower():
                            logger.info(f"URL de YouTube encontrada: {link['url']}")
                            return link['url']
                    
                    # Luego buscar previsualización oficial
                    for link in links:
                        if 'preview' in link.get('url', '').lower():
                            logger.info(f"URL de previsualización encontrada en ListenBrainz: {link['url']}")
                            return link['url']
                    
                    # Intentar con otros servicios de streaming
                    for link in links:
                        url_lower = link.get('url', '').lower()
                        if any(service in url_lower for service in ['spotify', 'deezer', 'soundcloud', 'bandcamp']):
                            logger.info(f"URL de servicio de streaming encontrada: {link['url']}")
                            return link['url']
            
            # 2. Alternativa: Consultar directamente MusicBrainz
            # MusicBrainz no requiere autenticación para consultas básicas
            mb_url = f"https://musicbrainz.org/ws/2/recording/{recording_mbid}?inc=url-rels&fmt=json"
            
            mb_response = requests.get(mb_url, headers=headers)
            
            if mb_response.status_code == 200:
                mb_data = mb_response.json()
                
                if 'relations' in mb_data:
                    for relation in mb_data['relations']:
                        if relation.get('type') == 'streaming' and 'url' in relation:
                            url_str = relation['url'].get('resource', '')
                            if url_str:
                                logger.info(f"URL de streaming encontrada en MusicBrainz: {url_str}")
                                return url_str
            
            # 3. Alternativa: Buscar en servicios de música sin credenciales
            # Por ejemplo, reconstruir URL de YouTube basada en patrones conocidos
            
            logger.warning(f"No se encontró URL de previsualización para MBID: {recording_mbid}")
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener URL de previsualización desde ListenBrainz: {e}")
            return None
            
    
    def extract_audio_from_youtube(self, youtube_url):
        """
        No extrae el audio directamente, sino que devuelve la URL para ser reproducida
        por el PlayerManager (MPV)
        
        Args:
            youtube_url: URL de YouTube
            
        Returns:
            La misma URL de YouTube (será reproducida por MPV)
        """
        # Guardar la URL para uso futuro
        self.current_youtube_url = youtube_url
        logger.info(f"URL de YouTube encontrada: {youtube_url}")
        return youtube_url  # Simplemente devuelve la URL para que PlayerManager la maneje
    
    def save_preview_url(self, song_id, preview_url):
        """Guarda la URL de previsualización en la base de datos"""
        try:
            # Primero comprobamos si existe el registro en song_links
            self.cursor.execute("""
                SELECT id FROM song_links WHERE song_id = ?
            """, (song_id,))
            
            result = self.cursor.fetchone()
            
            if result:
                # Actualizar el registro existente
                self.cursor.execute("""
                    UPDATE song_links
                    SET listenbrainz_preview_url = ?
                    WHERE song_id = ?
                """, (preview_url, song_id))
            else:
                # Crear un nuevo registro
                self.cursor.execute("""
                    INSERT INTO song_links (song_id, listenbrainz_preview_url)
                    VALUES (?, ?)
                """, (song_id, preview_url))
            
            self.conn.commit()
            logger.info(f"URL de previsualización guardada para canción ID: {song_id}")
            
        except Exception as e:
            logger.error(f"Error al guardar URL de previsualización: {e}")
    
    def get_listenbrainz_preview_url(self, song_id):
        """
        Obtiene la URL de previsualización para una canción utilizando los enlaces almacenados
        en la base de datos (YouTube, SoundCloud, Bandcamp).
        
        Args:
            song_id: ID de la canción en la base de datos
                
        Returns:
            URL de previsualización si está disponible, None en caso contrario
        """
        try:
            # 1. Buscar directamente en song_links por enlaces disponibles
            # Priorizar YouTube, luego SoundCloud, luego Bandcamp
            self.cursor.execute("""
                SELECT youtube_url, soundcloud_url, bandcamp_url 
                FROM song_links 
                WHERE song_id = ?
            """, (song_id,))
            
            result = self.cursor.fetchone()
            if result:
                # Verificar YouTube primero (mejor compatibilidad con MPV)
                if result['youtube_url'] and result['youtube_url'].strip():
                    youtube_url = result['youtube_url'].strip()
                    logger.info(f"URL de YouTube encontrada en la base de datos: {youtube_url}")
                    return youtube_url
                
                # Luego SoundCloud
                if result['soundcloud_url'] and result['soundcloud_url'].strip():
                    soundcloud_url = result['soundcloud_url'].strip()
                    logger.info(f"URL de SoundCloud encontrada en la base de datos: {soundcloud_url}")
                    return soundcloud_url
                
                # Finalmente Bandcamp
                if result['bandcamp_url'] and result['bandcamp_url'].strip():
                    bandcamp_url = result['bandcamp_url'].strip()
                    logger.info(f"URL de Bandcamp encontrada en la base de datos: {bandcamp_url}")
                    return bandcamp_url
            
            # 2. Si no hay enlaces en song_links, buscar en la tabla de scrobbles como fallback
            self.cursor.execute("""
                SELECT s.title, s.artist FROM songs WHERE id = ?
            """, (song_id,))
            
            song_info = self.cursor.fetchone()
            if song_info:
                title = song_info['title']
                artist = song_info['artist']
                
                # Buscar en scrobbles_paqueradejere por posibles URLs
                self.cursor.execute("""
                    SELECT youtube_url, spotify_url, bandcamp_url, soundcloud_url
                    FROM scrobbles_paqueradejere
                    WHERE LOWER(track_name) LIKE LOWER(?) AND LOWER(artist_name) LIKE LOWER(?)
                    AND (youtube_url IS NOT NULL OR soundcloud_url IS NOT NULL OR bandcamp_url IS NOT NULL)
                    LIMIT 1
                """, (f"%{title}%", f"%{artist}%"))
                
                scrobble_result = self.cursor.fetchone()
                if scrobble_result:
                    # Priorizar YouTube
                    if scrobble_result['youtube_url'] and scrobble_result['youtube_url'].strip():
                        url = scrobble_result['youtube_url'].strip()
                        logger.info(f"URL de YouTube encontrada en scrobbles: {url}")
                        return url
                    
                    # Luego SoundCloud
                    if scrobble_result['soundcloud_url'] and scrobble_result['soundcloud_url'].strip():
                        url = scrobble_result['soundcloud_url'].strip()
                        logger.info(f"URL de SoundCloud encontrada en scrobbles: {url}")
                        return url
                    
                    # Finalmente Bandcamp
                    if scrobble_result['bandcamp_url'] and scrobble_result['bandcamp_url'].strip():
                        url = scrobble_result['bandcamp_url'].strip()
                        logger.info(f"URL de Bandcamp encontrada en scrobbles: {url}")
                        return url
            
            logger.warning(f"No se encontró URL online para la canción ID: {song_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener URL online: {e}")
            return None
    
    def search_youtube_url(self, query):
        """
        Busca una URL de YouTube para una consulta dada.
        Nota: Esta es una implementación simulada. En una implementación real,
        usaríamos la API de YouTube o web scraping.
        
        Args:
            query: Texto de búsqueda
            
        Returns:
            URL de YouTube si se encuentra, None en caso contrario
        """
        logger.warning(f"Búsqueda en YouTube para '{query}' no implementada. Se necesita API de YouTube.")
        # En una implementación real, aquí se realizaría una búsqueda
        # y se devolvería la URL del primer resultado
        return None
    
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
                color: #EB743B;
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
                    background-color: #EB743B;
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
        
        # Intentar obtener la previsualización nuevamente con otro método
        preview_url = self.get_listenbrainz_preview_url(self.current_song_id)
        if preview_url:
            self.play_with_native_player(preview_url)
            return
        
        # Si no se pudo obtener, informar del error
        self.playback_error.emit("No se pudo reproducir la canción después de varios intentos")
    
   
    
    def play(self, song_id):
        """
        Reproduce una canción usando ListenBrainz/MusicBrainz.
        
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
            preview_url = self.get_listenbrainz_preview_url(song_id)
            if not preview_url:
                if self.message_label:
                    self.message_label.setText("Error: No se encontró URL de previsualización")
                self.playback_error.emit("No se encontró URL de previsualización para esta canción")
                return False
            
            # Log del preview_url para depuración
            logger.info(f"Intentando reproducir preview_url: {preview_url}")
            
            # Intentar reproducir con el reproductor nativo
            if self.progress_bar:
                self.progress_bar.setValue(50)
            if self.message_label:
                self.message_label.setText("Reproduciendo canción...")
                
            success = self.play_with_native_player(preview_url)
            
            if success:
                if self.progress_bar:
                    self.progress_bar.setValue(100)
                if self.message_label:
                    self.message_label.setText("Reproduciendo preview de ListenBrainz...")
            else:
                if self.message_label:
                    self.message_label.setText("No se pudo reproducir la canción")
                    
            return success
            
        except Exception as e:
            logger.error(f"Error al reproducir desde ListenBrainz: {e}")
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
            if self.using_mpv and self.player_manager:
                # Detener el reproductor MPV
                self.player_manager.stop()
                self.using_mpv = False
            else:
                # Detener el reproductor nativo
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
            self.conn.close()
            logger.info("Conexión a la base de datos cerrada")



    def create_mpv_playlist(self, urls):
        """Crea una playlist en MPV con múltiples URLs."""
        if not urls or len(urls) == 0:
            self.playback_error.emit("No hay URLs para crear una playlist")
            return False
        
        # Verificar si el reproductor MPV está inicializado
        if not hasattr(self, 'player_manager') or not self.player_manager:
            self.playback_error.emit("Reproductor MPV no inicializado")
            return False
        
        try:
            # Detener cualquier reproducción actual
            self.stop()
            
            # Iniciar la reproducción con la primera URL
            first_url = urls[0]
            success = self.player_manager.play(first_url)
            
            if not success:
                self.playback_error.emit("No se pudo iniciar la reproducción de la playlist")
                return False
            
            # Agregar el resto de URLs a la playlist de MPV
            for url in urls[1:]:
                # Usar el socket para agregar a la playlist
                command = {"command": ["loadfile", url, "append-play"]}
                self.player_manager.send_command(command)
            
            self.using_mpv = True
            logger.info(f"Playlist creada con {len(urls)} canciones")
            return True
        
        except Exception as e:
            logger.error(f"Error al crear playlist de MPV: {e}")
            return False

    def get_next_track_in_playlist(self):
        """Avanza a la siguiente pista en la playlist de MPV."""
        if not self.using_mpv:
            logger.warning("No se está usando MPV, no se puede avanzar en la playlist")
            return False
        
        try:
            # Enviar comando para avanzar a la siguiente pista
            command = {"command": ["playlist-next", "force"]}
            success = self.player_manager.send_command(command)
            
            if success:
                logger.info("Avanzando a la siguiente pista en la playlist")
                return True
            else:
                logger.warning("No se pudo avanzar a la siguiente pista")
                return False
        except Exception as e:
            logger.error(f"Error al avanzar en la playlist: {e}")
            return False

    def seek_random_position(self, percent_range=(5, 70)):
        """
        Busca una posición aleatoria en la canción actual.
        
        Args:
            percent_range: Tuple con el rango (min%, max%) para el salto aleatorio
        
        Returns:
            True si se realizó correctamente, False en caso contrario
        """
        if not self.using_mpv:
            logger.warning("No se está usando MPV, no se puede buscar posición aleatoria")
            return False
        
        try:
            # Generar un porcentaje aleatorio dentro del rango especificado
            import random
            min_percent, max_percent = percent_range
            
            # Asegurarse de que los valores son numéricos
            try:
                min_percent = float(min_percent)
                max_percent = float(max_percent)
            except (ValueError, TypeError):
                logger.error("Valores de rango de porcentaje inválidos")
                min_percent, max_percent = 5.0, 70.0
            
            # Generar un valor aleatorio dentro del rango
            random_percent = random.uniform(min_percent, max_percent)
            
            # Formatear el valor para el comando MPV
            # MPV acepta valores float así que no hay problema con decimales
            percent_str = f"{random_percent:.1f}"
            
            # Enviar comando para buscar a ese porcentaje
            command = {"command": ["seek", percent_str, "absolute-percent"]}
            success = self.player_manager.send_command(command)
            
            if success:
                logger.info(f"Posición aleatoria establecida al {random_percent:.1f}%")
                return True
            else:
                logger.warning("No se pudo establecer una posición aleatoria")
                return False
        except Exception as e:
            logger.error(f"Error al buscar posición aleatoria: {e}")
            return False

    def play_with_native_player(self, preview_url):
        """Reproduce la URL de previsualización usando el reproductor nativo o MPV para YouTube"""
        try:
            logger.info(f"Reproduciendo URL: {preview_url}")
            
            # Actualizar la interfaz
            if self.message_label:
                self.message_label.setText("Reproduciendo canción...")
            if self.progress_bar:
                self.progress_bar.setValue(50)
            
            # Verificar si es una URL de YouTube - usar PlayerManager
            if 'youtube.com' in preview_url or 'youtu.be' in preview_url:
                logger.info("Usando MPV para reproducir URL de YouTube (solo audio)")
                self.using_mpv = True
                self.current_youtube_url = preview_url
                
                # Configurar MPV para solo audio ANTES de reproducir
                self.configure_mpv_audio_only()
                
                # Usar PlayerManager para reproducir con MPV
                success = self.player_manager.play(preview_url)
                
                # Si se inició correctamente, intentar establecer una posición aleatoria tras 2 segundos
                if success:
                    QTimer.singleShot(2000, lambda: self.seek_random_position())
                
                return success
            else:
                # Usar el reproductor nativo para otras URLs
                self.using_mpv = False
                logger.info("Usando reproductor nativo para URL no-YouTube")
                
                # Configurar y reproducir
                self.player.setSource(QUrl(preview_url))
                self.player.play()
                
                return True
                
        except Exception as e:
            logger.error(f"Error al reproducir: {e}")
            logger.error(traceback.format_exc())
            return False


    def send_command(self, command):
        """
        Envía un comando a MPV a través del socket IPC.
        Versión mejorada con manejo de errores y conversión de tipos.
        
        Args:
            command: Diccionario con el comando a enviar
                
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        if not self.socket_path or not os.path.exists(self.socket_path):
            self._logger(f"Socket no disponible: {self.socket_path}")
            return False
        
        try:
            import json
            
            # Verificar que el comando es un diccionario
            if not isinstance(command, dict):
                self._logger(f"Comando debe ser un diccionario, recibido: {type(command)}")
                return False
            
            # Validar y ajustar valores en el comando para MPV
            if 'command' in command and isinstance(command['command'], list):
                # Procesar cada elemento del comando para asegurar compatibilidad con MPV
                for i, item in enumerate(command['command']):
                    # Convertir enteros y floats a strings para el JSON
                    if isinstance(item, (int, float)):
                        command['command'][i] = str(item)
            
            # Crear el socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            
            # Intentar conexión con timeout
            sock.settimeout(1.0)  # 1 segundo de timeout
            
            # Convertir a string en caso de que sea un objeto PosixPath
            socket_path_str = str(self.socket_path)
            
            try:
                sock.connect(socket_path_str)
            except socket.timeout:
                self._logger("Timeout al conectar al socket de MPV")
                sock.close()
                return False
            except socket.error as e:
                self._logger(f"Error de socket al conectar: {e}")
                sock.close()
                return False
            
            # Reiniciar timeout para el envío/recepción
            sock.settimeout(2.0)  # 2 segundos para envío/recepción
            
            # Preparar y enviar el comando
            command_str = json.dumps(command) + "\n"
            sock.send(command_str.encode())
            
            # No esperamos respuesta en este caso
            sock.close()
            
            return True
            
        except json.JSONEncodeError as e:
            self._logger(f"Error al codificar comando a JSON: {e}")
            return False
        except Exception as e:
            self._logger(f"Error al enviar comando: {e}")
            return False


    def init_delay_and_seek(self, playerManager):
        """
        Inicializa los métodos para manejar el delay inicial y la posición aleatoria.
        Esta función debe ser agregada al módulo PlayerManager.
        
        Args:
            playerManager: Instancia de PlayerManager a modificar
        """
        # Agregar un método para manejar el delay inicial
        def _play_with_delay(url, delay_ms=2000, seek_percent=None):
            """
            Reproduce una URL con un delay inicial y opcionalmente busca una posición específica.
            
            Args:
                url: URL a reproducir
                delay_ms: Delay en milisegundos antes de reproducir
                seek_percent: Porcentaje opcional al que buscar después del delay
                
            Returns:
                True si se inició la reproducción, False en caso contrario
            """
            try:
                # Primero verificar si la URL es válida
                if not url:
                    playerManager._logger("URL inválida")
                    return False
                    
                # Iniciar la reproducción normalmente
                success = playerManager.play(url)
                
                if not success:
                    playerManager._logger("No se pudo iniciar la reproducción")
                    return False
                    
                # Si se especificó un porcentaje de posición, programar la búsqueda
                if seek_percent is not None:
                    # Crear un QTimer para el delay de la posición
                    seek_timer = QTimer(playerManager)
                    seek_timer.setSingleShot(True)
                    seek_timer.timeout.connect(lambda: playerManager.send_command({
                        "command": ["seek", str(seek_percent), "absolute-percent"]
                    }))
                    seek_timer.start(delay_ms)  # Usar el mismo delay
                    
                return True
            except Exception as e:
                playerManager._logger(f"Error en play_with_delay: {e}")
                return False
                
        # Agregar el método a la instancia
        playerManager.play_with_delay = _play_with_delay
        
        # Agregar un método para obtener información de la canción actual
        def _get_media_info():
            """
            Obtiene información sobre la canción en reproducción.
            
            Returns:
                Diccionario con información (duración, posición, etc.) o None en caso de error
            """
            try:
                # Verificar que hay reproducción activa
                if not playerManager.is_playing:
                    return None
                    
                # Información a obtener
                info = {
                    'duration': None,  # Duración en segundos
                    'position': None,  # Posición actual en segundos
                    'filename': None,  # Nombre del archivo
                    'media-title': None,  # Título del medio
                    'percent-pos': None  # Posición en porcentaje
                }
                    
                # Obtener información disponible
                for key in info.keys():
                    try:
                        # Enviar comando para obtener la propiedad
                        playerManager.send_command({
                            "command": ["get_property", key]
                        })
                        # Nota: En una implementación real, necesitaríamos 
                        # recoger la respuesta del socket
                    except:
                        pass
                        
                return info
            except Exception as e:
                playerManager._logger(f"Error al obtener información de medios: {e}")
                return None
                
        # Agregar el método a la instancia
        playerManager.get_media_info = _get_media_info
        
        # Agregar un método para reproducir una lista de URLs como playlist
        def _play_playlist(urls, start_index=0, random_seek=False):
            """
            Reproduce una lista de URLs como playlist.
            
            Args:
                urls: Lista de URLs a reproducir
                start_index: Índice en la lista para comenzar la reproducción
                random_seek: Si True, busca una posición aleatoria en la primera canción
                
            Returns:
                True si se inició la reproducción, False en caso contrario
            """
            try:
                if not urls or len(urls) == 0:
                    playerManager._logger("No hay URLs para reproducir")
                    return False
                    
                # Asegurar que el índice es válido
                if start_index < 0 or start_index >= len(urls):
                    start_index = 0
                    
                # Detener cualquier reproducción actual
                playerManager.stop()
                
                # Comenzar con la primera URL
                first_url = urls[start_index]
                
                # Decidir si usar posición aleatoria
                seek_percent = None
                if random_seek:
                    import random
                    seek_percent = random.uniform(10, 70)
                    
                # Iniciar la reproducción con delay
                success = _play_with_delay(first_url, 2000, seek_percent)
                
                if not success:
                    playerManager._logger("No se pudo iniciar la reproducción de la playlist")
                    return False
                    
                # Añadir el resto de URLs a la playlist
                for i, url in enumerate(urls):
                    if i != start_index:  # No añadir la primera URL de nuevo
                        playerManager.send_command({
                            "command": ["loadfile", url, "append-play"]
                        })
                        
                playerManager._logger(f"Playlist creada con {len(urls)} elementos")
                return True
            except Exception as e:
                playerManager._logger(f"Error al crear playlist: {e}")
                return False
                
        # Agregar el método a la instancia
        playerManager.play_playlist = _play_playlist
        
        return playerManager

    def integrate_with_musicquiz(self, musicQuiz):
        """
        Integra ListenBrainzPlayer con MusicQuiz para mejorar la reproducción.
        Esta función debe ser agregada al módulo ListenBrainzPlayer.
        
        Args:
            musicQuiz: Instancia de MusicQuiz a integrar
        """
        try:
            # Verificar que tenemos los componentes necesarios
            if not hasattr(self, 'player_manager'):
                self.log_message("PlayerManager no disponible para integración")
                return False
                
            # Mejorar PlayerManager con métodos de delay y posición aleatoria
            if hasattr(self, 'init_delay_and_seek'):
                self.init_delay_and_seek(self.player_manager)
            
            # Configurar la duración de reproducción según MusicQuiz
            if hasattr(musicQuiz, 'song_duration_seconds'):
                self.set_playback_duration(musicQuiz.song_duration_seconds)
                
            # Agregar referencias cruzadas
            musicQuiz.listenbrainz_player = self
            
            # Establecer manejador para eventos de fin de reproducción
            def on_track_finished():
                """Maneja el fin de la reproducción en el contexto del quiz"""
                # Solo actuar si el quiz está activo
                if hasattr(musicQuiz, 'game_active') and musicQuiz.game_active:
                    # Verificar si debemos pasar a la siguiente pregunta
                    if hasattr(musicQuiz, 'remaining_time') and musicQuiz.remaining_time <= 0:
                        # Fin del tiempo de la pregunta, avanzar
                        if hasattr(musicQuiz, 'show_next_question'):
                            QTimer.singleShot(musicQuiz.pause_between_songs * 1000, 
                                            musicQuiz.show_next_question)
            
            # Conectar la señal de fin de pista
            self.player_manager.track_finished.disconnect()  # Desconectar conexiones anteriores
            self.player_manager.track_finished.connect(on_track_finished)
            
            self.log_message("Integración con MusicQuiz completada")
            return True
        except Exception as e:
            self.log_message(f"Error en integración con MusicQuiz: {e}")
            return False

    def optimize_random_position(self, song_duration):
        """
        Optimiza la selección de una posición aleatoria basada en la duración de la canción.
        Esta función debe ser agregada al módulo MusicQuiz.
        
        Args:
            song_duration: Duración de la canción en segundos
            
        Returns:
            Posición inicial en segundos
        """
        try:
            # Valores predeterminados en caso de error
            if not song_duration or song_duration <= 0:
                song_duration = 60  # Valor predeterminado
                
            # Obtener parámetros de configuración
            start_from_beginning = random.random() < self.start_from_beginning_chance
            avoid_last_seconds = min(self.avoid_last_seconds, int(song_duration * 0.1))
            quiz_duration = self.song_duration_seconds
            
            # Si la canción es muy corta o se decide empezar desde el principio
            if start_from_beginning or song_duration <= (quiz_duration + avoid_last_seconds):
                return 0
                
            # Calcular el rango de posición válido
            max_start = int(song_duration - quiz_duration - avoid_last_seconds)
            
            # Asegurar que max_start es positivo
            if max_start <= 0:
                return 0
                
            # Generar una posición aleatoria dentro del rango válido
            start_position = random.randint(10, max_start)
            
            return start_position
            
        except Exception as e:
            print(f"Error al calcular posición aleatoria: {e}")
            return 0  # Valor seguro en caso de error


    def set_playback_duration(self, duration_seconds):
        """
        Establece la duración de reproducción para las previsualizaciones.
        
        Args:
            duration_seconds: Duración en segundos
        """
        self.playback_duration = duration_seconds
        logger.info(f"Duración de reproducción establecida a {duration_seconds} segundos")

class ListenBrainzPlaylist:
    """
    Clase para manejar playlists de canciones en el ListenBrainzPlayer.
    Esta clase permite gestionar una lista de canciones para reproducción secuencial.
    """
    
    def __init__(self, player_manager=None, logger_func=None):
        self.player_manager = player_manager
        self.logger = logger_func or (lambda msg: print(f"[ListenBrainzPlaylist] {msg}"))
        self.urls = []
        self.current_index = -1
        self.is_playing = False
        self.repeat_mode = 'none'  # 'none', 'one', 'all'
        self.shuffle_mode = False
        self.playlist_name = "Playlist temporal"
    
    def set_player_manager(self, player_manager):
        """Establece el reproductor MPV a utilizar"""
        self.player_manager = player_manager
    
    def add(self, url, play_now=False):
        """
        Añade una URL a la playlist.
        
        Args:
            url: URL para añadir a la playlist
            play_now: Si True, comienza a reproducir inmediatamente esta URL
        
        Returns:
            Índice de la URL en la playlist
        """
        if not url:
            return -1
            
        # Añadir la URL a la lista
        self.urls.append(url)
        new_index = len(self.urls) - 1
        
        # Si es la primera URL o se pide reproducir ahora, iniciar la reproducción
        if play_now or len(self.urls) == 1:
            self.play_index(new_index)
        else:
            # Si ya estamos reproduciendo, añadir a la playlist de MPV
            if self.is_playing and self.player_manager:
                self.player_manager.send_command({
                    "command": ["loadfile", url, "append-play"]
                })
        
        return new_index
    
    def add_multiple(self, urls, play_first=False):
        """
        Añade múltiples URLs a la playlist.
        
        Args:
            urls: Lista de URLs para añadir
            play_first: Si True, comienza a reproducir la primera URL
        
        Returns:
            Número de URLs añadidas
        """
        if not urls:
            return 0
            
        # Añadir todas las URLs
        for i, url in enumerate(urls):
            if i == 0 and play_first:
                self.add(url, play_now=True)
            else:
                self.add(url, play_now=False)
        
        return len(urls)
    
    def clear(self):
        """Limpia la playlist y detiene la reproducción"""
        self.stop()
        self.urls = []
        self.current_index = -1
        self.is_playing = False
    
    def play_index(self, index):
        """
        Reproduce la URL en el índice especificado.
        
        Args:
            index: Índice de la URL a reproducir
            
        Returns:
            True si se inició la reproducción, False en caso contrario
        """
        if not self.player_manager or index < 0 or index >= len(self.urls):
            return False
            
        # Establecer el índice actual
        self.current_index = index
        url = self.urls[index]
        
        # Intentar reproducir con el reproductor
        success = self.player_manager.play(url)
        
        if success:
            self.is_playing = True
            self.logger(f"Reproduciendo URL en índice {index}: {url}")
            return True
        else:
            self.logger(f"Error al reproducir URL en índice {index}")
            return False
    
    def play(self):
        """
        Inicia o reanuda la reproducción de la playlist.
        
        Returns:
            True si se inició/reanudó la reproducción, False en caso contrario
        """
        if not self.player_manager:
            return False
            
        # Si no hay URLs, no hay nada que reproducir
        if not self.urls:
            return False
            
        # Si ya estamos reproduciendo, no hacer nada
        if self.is_playing:
            return True
            
        # Si tenemos un índice actual, reanudar desde ahí
        if self.current_index >= 0 and self.current_index < len(self.urls):
            return self.play_index(self.current_index)
            
        # Si no, comenzar desde el principio
        return self.play_index(0)
    
    def stop(self):
        """
        Detiene la reproducción.
        
        Returns:
            True si se detuvo correctamente, False en caso contrario
        """
        if not self.player_manager:
            return False
            
        if not self.is_playing:
            return True
            
        try:
            self.player_manager.stop()
            self.is_playing = False
            return True
        except Exception as e:
            self.logger(f"Error al detener reproducción: {e}")
            return False
    
    def next(self):
        """
        Avanza a la siguiente URL en la playlist.
        
        Returns:
            True si se avanzó correctamente, False en caso contrario
        """
        if not self.player_manager or not self.urls:
            return False
            
        # Calcular el siguiente índice según el modo de repetición
        next_index = self.current_index + 1
        
        if next_index >= len(self.urls):
            if self.repeat_mode == 'all':
                next_index = 0
            else:
                # Fin de la playlist
                return False
        
        # Reproducir la siguiente URL
        return self.play_index(next_index)
    
    def previous(self):
        """
        Retrocede a la URL anterior en la playlist.
        
        Returns:
            True si se retrocedió correctamente, False en caso contrario
        """
        if not self.player_manager or not self.urls:
            return False
            
        # Calcular el índice anterior
        prev_index = self.current_index - 1
        
        if prev_index < 0:
            if self.repeat_mode == 'all':
                prev_index = len(self.urls) - 1
            else:
                # Ya estamos en la primera URL
                return False
        
        # Reproducir la URL anterior
        return self.play_index(prev_index)
    
    def shuffle(self):
        """
        Activa/desactiva el modo aleatorio.
        
        Returns:
            El nuevo estado del modo aleatorio
        """
        if not self.urls:
            return False
            
        import random
        
        # Invertir el estado actual
        self.shuffle_mode = not self.shuffle_mode
        
        if self.shuffle_mode:
            # Guardar el índice actual
            current_url = self.urls[self.current_index] if self.current_index >= 0 else None
            
            # Mezclar las URLs
            random.shuffle(self.urls)
            
            # Actualizar el índice actual si estábamos reproduciendo algo
            if current_url:
                try:
                    self.current_index = self.urls.index(current_url)
                except ValueError:
                    self.current_index = 0
        
        return self.shuffle_mode
    
    def set_repeat_mode(self, mode):
        """
        Establece el modo de repetición.
        
        Args:
            mode: Modo de repetición ('none', 'one', 'all')
            
        Returns:
            El modo establecido
        """
        if mode in ['none', 'one', 'all']:
            self.repeat_mode = mode
        
        return self.repeat_mode
    
    def get_current_url(self):
        """
        Obtiene la URL actual en reproducción.
        
        Returns:
            URL actual o None si no hay reproducción
        """
        if self.current_index >= 0 and self.current_index < len(self.urls):
            return self.urls[self.current_index]
        return None
    
    def save_to_file(self, filename):
        """
        Guarda la playlist en un archivo.
        
        Args:
            filename: Ruta del archivo donde guardar
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            import json
            
            # Crear un diccionario con la información de la playlist
            playlist_data = {
                'name': self.playlist_name,
                'urls': self.urls,
                'repeat_mode': self.repeat_mode,
                'shuffle_mode': self.shuffle_mode
            }
            
            # Guardar en el archivo
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, indent=2)
                
            self.logger(f"Playlist guardada en: {filename}")
            return True
            
        except Exception as e:
            self.logger(f"Error al guardar playlist: {e}")
            return False
    
    def load_from_file(self, filename):
        """
        Carga una playlist desde un archivo.
        
        Args:
            filename: Ruta del archivo de donde cargar
            
        Returns:
            True si se cargó correctamente, False en caso contrario
        """
        try:
            import json
            
            # Leer el archivo
            with open(filename, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)
                
            # Verificar el formato
            if not isinstance(playlist_data, dict) or 'urls' not in playlist_data:
                self.logger("Formato de archivo de playlist inválido")
                return False
                
            # Cargar los datos
            self.urls = playlist_data.get('urls', [])
            self.playlist_name = playlist_data.get('name', "Playlist cargada")
            self.repeat_mode = playlist_data.get('repeat_mode', 'none')
            self.shuffle_mode = playlist_data.get('shuffle_mode', False)
            
            # Reiniciar el índice actual
            self.current_index = -1
            self.is_playing = False
            
            self.logger(f"Playlist cargada desde: {filename}")
            return True
            
        except Exception as e:
            self.logger(f"Error al cargar playlist: {e}")
            return False

    def get_playlist_for_quiz(self, song_ids):
        """
        Obtiene una lista de URLs de previsualización para una lista de IDs de canciones.
        
        Args:
            song_ids: Lista de IDs de canciones
            
        Returns:
            Lista de URLs de previsualización
        """
        if not song_ids or len(song_ids) == 0:
            logger.warning("No hay IDs de canciones para crear playlist")
            return []
        
        urls = []
        for song_id in song_ids:
            # Obtener URL de previsualización para esta canción
            url = self.get_listenbrainz_preview_url(song_id)
            if url:
                urls.append(url)
        
        logger.info(f"Se encontraron {len(urls)} URLs para la playlist del quiz")
        return urls


    def create_playlist(self, urls):
        """
        Crea una playlist con las URLs proporcionadas.
        
        Args:
            urls: Lista de URLs para reproducir
            
        Returns:
            True si se creó correctamente, False en caso contrario
        """
        if not urls or len(urls) == 0:
            logger.warning("No hay URLs para crear playlist")
            return False
        
        # Si estamos usando MPV, crear la playlist allí
        if self.player_manager:
            try:
                return self.create_mpv_playlist(urls)
            except Exception as e:
                logger.error(f"Error al crear playlist en MPV: {e}")
        
        # Fallback al reproductor nativo
        try:
            # Reproducir la primera URL
            self.play_with_native_player(urls[0])
            return True
        except Exception as e:
            logger.error(f"Error al crear playlist: {e}")
            return False


    def configure_mpv_audio_only(self):
        """Configura MPV para reproducir solo audio sin ventana de video"""
        try:
            if hasattr(self.player_manager, 'send_command'):
                # Configurar MPV para solo audio
                commands = [
                    {"command": ["set", "video", "no"]},
                    {"command": ["set", "vid", "no"]},
                    {"command": ["set", "force-window", "no"]},
                    {"command": ["set", "terminal", "yes"]},
                    {"command": ["set", "no-video", ""]},
                ]
                
                for cmd in commands:
                    self.player_manager.send_command(cmd)
                    
                logger.info("MPV configurado para solo audio")
                return True
        except Exception as e:
            logger.error(f"Error al configurar MPV para solo audio: {e}")
            return False

    def create_game_playlist(self, song_count=100):
        """
        Crea una playlist de URLs para el juego con múltiples canciones.
        
        Args:
            song_count: Número de canciones a incluir en la playlist
            
        Returns:
            Lista de URLs válidas para el juego
        """
        try:
            if not self.cursor:
                logger.error("No hay conexión a la base de datos")
                return []
            
            # Obtener canciones con URLs online disponibles
            self.cursor.execute("""
                SELECT DISTINCT s.id, s.title, s.artist, sl.youtube_url, sl.soundcloud_url, sl.bandcamp_url
                FROM songs s
                JOIN song_links sl ON s.id = sl.song_id
                WHERE (sl.youtube_url IS NOT NULL AND sl.youtube_url != '')
                OR (sl.soundcloud_url IS NOT NULL AND sl.soundcloud_url != '')
                OR (sl.bandcamp_url IS NOT NULL AND sl.bandcamp_url != '')
                ORDER BY RANDOM()
                LIMIT ?
            """, (song_count * 2,))  # Obtener el doble por si algunas URLs fallan
            
            results = self.cursor.fetchall()
            playlist_urls = []
            
            for row in results:
                song_id, title, artist, youtube_url, soundcloud_url, bandcamp_url = row
                
                # Priorizar YouTube, luego SoundCloud, luego Bandcamp
                url = None
                if youtube_url and youtube_url.strip():
                    url = youtube_url.strip()
                elif soundcloud_url and soundcloud_url.strip():
                    url = soundcloud_url.strip()
                elif bandcamp_url and bandcamp_url.strip():
                    url = bandcamp_url.strip()
                
                if url:
                    playlist_urls.append({
                        'song_id': song_id,
                        'title': title,
                        'artist': artist,
                        'url': url
                    })
                    
                    if len(playlist_urls) >= song_count:
                        break
            
            logger.info(f"Playlist creada con {len(playlist_urls)} canciones")
            return playlist_urls
            
        except Exception as e:
            logger.error(f"Error al crear playlist del juego: {e}")
            return []