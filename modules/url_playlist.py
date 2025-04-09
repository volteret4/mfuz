# TODO: Crear modo alternativo a dotenv


import os
import re
import requests
from bs4 import BeautifulSoup
import urllib3
import sys
import json
import subprocess
import tempfile
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QTextEdit, QTabWidget, QMessageBox,
    QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy, QApplication, QDialog, QComboBox
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal, QUrl, QRunnable, pyqtSlot, QObject, QThreadPool
from PyQt6.QtGui import QIcon

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import resources_rc
from base_module import BaseModule, PROJECT_ROOT





class SearchSignals(QObject):
    """Define las señales disponibles para el SearchWorker."""
    results = pyqtSignal(list)
    error = pyqtSignal(str)
    finished = pyqtSignal()

class SearchWorker(QRunnable):
    """Worker thread para realizar búsquedas en distintos servicios."""
    
    def __init__(self, services, query, max_results=10):
        super().__init__()
        self.services = services if isinstance(services, list) else [services]
        self.query = query
        self.max_results = max_results
        self.signals = SearchSignals()
        
    def log(self, message):
        """Envía un mensaje de log a través de la señal de error."""
        print(f"[SearchWorker] {message}")
    
    @pyqtSlot()
    def run(self):
        """Ejecuta la búsqueda en segundo plano."""
        try:
            results = []
            
            # Get the search type from the parent widget
            search_type = getattr(self, 'search_type', 'all')
            self.log(f"Searching with type: {search_type}")
            
            # Primero, buscar en la base de datos
            if hasattr(self, 'parent'):
                db_results = self.parent.search_in_database(self.query, search_type)
                if db_results:
                    results.extend(db_results)
                    self.log(f"Found {len(db_results)} results in database")
            
            # Continuar con búsquedas en servicios solo si no hay suficientes resultados o fuerza actualización
            if len(results) < self.max_results:
                for service in self.services:
                    service_results = []
                    
                    if service == "youtube":
                        service_results = self.search_youtube(self.query)
                    elif service == "soundcloud":
                        service_results = self.search_soundcloud(self.query)
                    elif service == "bandcamp":
                        # Corregir aquí - pasar solo la consulta y el tipo de búsqueda
                        service_results = self.search_bandcamp(self.query, search_type)
                    elif service == "spotify":
                        service_results = self.search_spotify(self.query, search_type)
                    elif service == "lastfm":
                        service_results = self.search_lastfm(self.query, search_type)
                    
                    # Aplicar paginación por servicio
                    if service_results:
                        results.extend(service_results[:self.max_results])
            
            self.signals.results.emit(results)
        
        except Exception as e:
            self.signals.error.emit(f"Error en la búsqueda: {str(e)}")
            import traceback
            print(traceback.format_exc())
        
        finally:
            self.signals.finished.emit()

    def search_bandcamp(self, query, search_type):
        """Busca en Bandcamp usando el módulo existente"""
        try:
            # Importar el módulo existente
            from base_datos.enlaces_artista_album import MusicLinksManager
            
            # Crear configuración basada en los parámetros del módulo
            config = {
                'db_path': getattr(self.parent, 'db_path', os.path.join(PROJECT_ROOT, "base_datos", "music_database.db")),
                'rate_limit': 1.0,
                'disable_services': ['musicbrainz', 'discogs', 'youtube', 'spotify', 'rateyourmusic'],
                'log_level': 'WARNING'  # Use WARNING level to reduce log messages
            }
            
            # Crear instancia con la configuración
            manager = MusicLinksManager(config)
            bandcamp_results = []
            
            # Determinar si es artista, álbum o canción según el tipo de búsqueda
            if search_type.lower() in ['artist', 'artista']:
                artist_url = manager._get_bandcamp_artist_url(query)
                if artist_url:
                    bandcamp_results.append({
                        "source": "bandcamp",
                        "title": query,
                        "artist": query,
                        "url": artist_url,
                        "type": "artist"
                    })
                    self.log(f"Encontrado artista en Bandcamp: {query}")
            
            elif search_type.lower() in ['album', 'álbum']:
                # Si el formato es "artista - álbum"
                parts = query.split(" - ", 1)
                if len(parts) > 1:
                    artist, album = parts
                    album_url = manager._get_bandcamp_album_url(artist, album)
                    if album_url:
                        bandcamp_results.append({
                            "source": "bandcamp",
                            "title": album,
                            "artist": artist,
                            "url": album_url,
                            "type": "album"
                        })
                        self.log(f"Encontrado álbum en Bandcamp: {album} por {artist}")
                else:
                    # Buscar solo con el nombre del álbum
                    album_url = manager._get_bandcamp_album_url("", query)
                    if album_url:
                        bandcamp_results.append({
                            "source": "bandcamp",
                            "title": query,
                            "artist": "Unknown Artist",
                            "url": album_url,
                            "type": "album"
                        })
                        self.log(f"Encontrado álbum en Bandcamp: {query}")
            
            else:
                # Búsqueda general
                # Probar como artista
                artist_url = manager._get_bandcamp_artist_url(query)
                if artist_url:
                    bandcamp_results.append({
                        "source": "bandcamp",
                        "title": query,
                        "artist": query,
                        "url": artist_url,
                        "type": "artist"
                    })
                    self.log(f"Encontrado artista en Bandcamp: {query}")
                
                # Si el formato es "artista - título"
                parts = query.split(" - ", 1)
                if len(parts) > 1:
                    artist, title = parts
                    # Probar como álbum
                    album_url = manager._get_bandcamp_album_url(artist, title)
                    if album_url:
                        bandcamp_results.append({
                            "source": "bandcamp",
                            "title": title,
                            "artist": artist,
                            "url": album_url,
                            "type": "album"
                        })
                        self.log(f"Encontrado álbum en Bandcamp: {title} por {artist}")
            
            return bandcamp_results
            
        except Exception as e:
            self.log(f"Error al buscar en Bandcamp: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def search_spotify(self, query, search_type):
        """Busca en Spotify usando el módulo existente"""
        try:
            # Importar los módulos necesarios
            from base_datos.enlaces_canciones_spot_lastfm import MusicLinkUpdater
            
            # Usar configuración del padre si está disponible
            db_path = getattr(self.parent, 'db_path', os.path.join(PROJECT_ROOT, "base_datos", "musica.sqlite"))
            spotify_client_id = getattr(self.parent, 'spotify_client_id', os.environ.get("SPOTIFY_CLIENT_ID"))
            spotify_client_secret = getattr(self.parent, 'spotify_client_secret', os.environ.get("SPOTIFY_CLIENT_SECRET"))
            
            # Configurar
            temp_config = {
                'db_path': db_path,
                'checkpoint_path': ":memory:",
                'services': ['spotify'],
                'spotify_client_id': spotify_client_id,
                'spotify_client_secret': spotify_client_secret,
                'limit': self.max_results
            }
            
            updater = MusicLinkUpdater(**temp_config)
            results = []
            
            # Preparar la consulta según el tipo de búsqueda
            if search_type.lower() in ['artist', 'artista']:
                # Para este caso usaremos enlaces_artista_album.py
                from base_datos.enlaces_artista_album import MusicLinksManager
                
                config = {
                    'db_path': os.path.join(project_root, "base_datos", "musica.sqlite"),
                    'spotify_client_id': os.environ.get("SPOTIFY_CLIENT_ID"),
                    'spotify_client_secret': os.environ.get("SPOTIFY_CLIENT_SECRET")
                }
                
                manager = MusicLinksManager(config)
                artist_url = manager._get_spotify_artist_url(query)
                
                if artist_url:
                    results.append({
                        "source": "spotify",
                        "title": query,
                        "artist": query,
                        "url": artist_url,
                        "type": "artist"
                    })
                    self.log(f"Encontrado artista en Spotify: {query}")
            
            elif search_type.lower() in ['album', 'álbum']:
                # Para álbumes también usamos enlaces_artista_album.py
                from base_datos.enlaces_artista_album import MusicLinksManager
                
                config = {
                    'db_path': os.path.join(project_root, "base_datos", "musica.sqlite"),
                    'spotify_client_id': os.environ.get("SPOTIFY_CLIENT_ID"),
                    'spotify_client_secret': os.environ.get("SPOTIFY_CLIENT_SECRET")
                }
                
                manager = MusicLinksManager(config)
                
                # Determinar artista y álbum
                parts = query.split(" - ", 1)
                if len(parts) > 1:
                    artist, album = parts
                    album_data = manager._get_spotify_album_data(artist, album)
                else:
                    album_data = manager._get_spotify_album_data("", query)
                
                if album_data and 'album_url' in album_data:
                    artist_name = parts[0] if len(parts) > 1 else ""
                    album_name = parts[1] if len(parts) > 1 else query
                    
                    results.append({
                        "source": "spotify",
                        "title": album_name,
                        "artist": artist_name,
                        "url": album_data['album_url'],
                        "type": "album",
                        "spotify_id": album_data.get('album_id', '')
                    })
                    self.log(f"Encontrado álbum en Spotify: {album_name}")
            
            else:
                # Búsqueda de canciones o general
                # Preparar el objeto de canción para la búsqueda
                song = {'title': query, 'artist': '', 'album': ''}
                
                # Si el formato es "artista - título"
                parts = query.split(" - ", 1)
                if len(parts) > 1:
                    song['artist'] = parts[0].strip()
                    song['title'] = parts[1].strip()
                
                # Buscar la canción
                spotify_url, spotify_id = updater.search_spotify(song, 
                                                             os.environ.get("SPOTIFY_CLIENT_ID"),
                                                             os.environ.get("SPOTIFY_CLIENT_SECRET"))
                
                if spotify_url:
                    results.append({
                        "source": "spotify",
                        "title": song['title'],
                        "artist": song['artist'],
                        "url": spotify_url,
                        "type": "track",
                        "spotify_id": spotify_id
                    })
                    self.log(f"Encontrada canción en Spotify: {song['title']}")
            
            return results
            
        except Exception as e:
            self.log(f"Error al buscar en Spotify: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def search_lastfm(self, query, search_type):
        """Busca en Last.fm usando el módulo existente"""
        try:
            # Importar el módulo existente
            from base_datos.enlaces_artista_album import MusicLinksManager
            
            # Usar configuración del padre si está disponible
            db_path = getattr(self.parent, 'db_path', os.path.join(PROJECT_ROOT, "base_datos", "musica.sqlite"))
            lastfm_api_key = getattr(self.parent, 'lastfm_api_key', os.environ.get("LASTFM_API_KEY"))
            lastfm_user = getattr(self.parent, 'lastfm_user', os.environ.get("LASTFM_USER", ""))
            
            config = {
                'db_path': db_path,
                'lastfm_api_key': lastfm_api_key,
                'lastfm_user': lastfm_user,
                'disable_services': ['musicbrainz', 'discogs', 'youtube', 'spotify', 'bandcamp', 'rateyourmusic']
            }
            
            manager = MusicLinksManager(config)
            results = []
            
            # Buscar según el tipo
            if search_type.lower() in ['artist', 'artista']:
                # Obtener información del artista
                lastfm_result = manager._get_lastfm_artist_bio(query)
                if lastfm_result and lastfm_result[0]:  # [0] es la URL
                    artist_url = lastfm_result[0]
                    results.append({
                        "source": "lastfm",
                        "title": query,
                        "artist": query,
                        "url": artist_url,
                        "type": "artist"
                    })
                    self.log(f"Encontrado artista en Last.fm: {query}")
            
            elif search_type.lower() in ['album', 'álbum']:
                # Para álbumes
                parts = query.split(" - ", 1)
                if len(parts) > 1:
                    artist, album = parts
                    album_url = manager._get_lastfm_album_url(artist, album)
                    if album_url:
                        results.append({
                            "source": "lastfm",
                            "title": album,
                            "artist": artist,
                            "url": album_url,
                            "type": "album"
                        })
                        self.log(f"Encontrado álbum en Last.fm: {album} por {artist}")
            
            else:
                # Búsqueda general
                # Probar como artista
                lastfm_result = manager._get_lastfm_artist_bio(query)
                if lastfm_result and lastfm_result[0]:
                    artist_url = lastfm_result[0]
                    results.append({
                        "source": "lastfm",
                        "title": query,
                        "artist": query,
                        "url": artist_url,
                        "type": "artist"
                    })
                    self.log(f"Encontrado artista en Last.fm: {query}")
                
                # Si el formato es "artista - título/álbum"
                parts = query.split(" - ", 1)
                if len(parts) > 1:
                    artist, title = parts
                    # Probar como álbum
                    album_url = manager._get_lastfm_album_url(artist, title)
                    if album_url:
                        results.append({
                            "source": "lastfm",
                            "title": title,
                            "artist": artist,
                            "url": album_url,
                            "type": "album"
                        })
                        self.log(f"Encontrado álbum en Last.fm: {title} por {artist}")
            
            return results
            
        except Exception as e:
            self.log(f"Error al buscar en Last.fm: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return []


    def search_soundcloud(self, query):
        """Search for music on SoundCloud"""
        try:
            # Format search URL
            search_url = f"https://soundcloud.com/search?q={query.replace(' ', '%20')}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://soundcloud.com/",
                "Connection": "keep-alive",
            }
            
            self.log(f"Searching on SoundCloud: {search_url}")
            response = requests.get(search_url, headers=headers, timeout=15, verify=False)
            
            if response.status_code != 200:
                self.log(f"Error searching SoundCloud: Status code {response.status_code}")
                return []
            
            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            soundcloud_results = []
            
            # Try different selectors to adapt to structure changes
            selectors = [
                'h2 a[href^="/"]',
                'a.soundTitle__title',
                'a[itemprop="url"]',
                '.sound__content a'
            ]
            
            track_elements = []
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    track_elements = elements
                    self.log(f"SoundCloud: using selector {selector}, found {len(elements)} elements")
                    break
            
            # If no results found, try extracting from JSON scripts
            if not track_elements:
                self.log("Attempting to extract data from SoundCloud scripts")
                try:
                    # Look for data in JSON scripts
                    scripts = soup.find_all('script')
                    for script in scripts:
                        if script.string and '"url":' in script.string and '"title":' in script.string:
                            # Extract URLs and titles with regex
                            urls = re.findall(r'"url":"(https://soundcloud.com/[^"]+)"', script.string)
                            titles = re.findall(r'"title":"([^"]+)"', script.string)
                            artists = re.findall(r'"username":"([^"]+)"', script.string)
                            
                            # Create results from found data
                            for i in range(min(len(urls), len(titles), 5)):
                                full_url = urls[i].replace('\\u0026', '&')
                                title = titles[i]
                                artist = artists[i] if i < len(artists) else "Unknown Artist"
                                
                                soundcloud_results.append({
                                    "source": "soundcloud",
                                    "title": title,
                                    "artist": artist,
                                    "url": full_url,
                                    "type": "track"
                                })
                                self.log(f"Found on SoundCloud (JSON): {title} - URL: {full_url}")                        
                except Exception as e:
                    self.log(f"Error extracting JSON from SoundCloud: {e}")
            
            # Process track elements found by selectors
            for i, track_element in enumerate(track_elements[:5]):
                try:
                    url_path = track_element.get('href', '')
                    if not url_path or not url_path.startswith('/'):
                        continue
                        
                    # Get full URL
                    full_url = f"https://soundcloud.com{url_path}"
                    
                    # Get title from link text
                    title = track_element.get_text().strip()
                    
                    # Try to find the artist
                    artist = "Unknown Artist"
                    artist_selectors = [
                        lambda el: el.find_previous('a', attrs={'class': 'soundTitle__username'}),
                        lambda el: el.find_previous('span', attrs={'class': 'soundTitle__username'}),
                        lambda el: el.parent.find_next('a', attrs={'class': 'soundTitle__username'}),
                        lambda el: el.find_parent('div').find_previous('a', attrs={'itemprop': 'author'})
                    ]
                    
                    for selector_func in artist_selectors:
                        artist_element = selector_func(track_element)
                        if artist_element:
                            artist = artist_element.get_text().strip()
                            break
                    
                    soundcloud_results.append({
                        "source": "soundcloud",
                        "title": title,
                        "artist": artist,
                        "url": full_url,
                        "type": "track" if "/tracks/" in full_url else "playlist" if "/sets/" in full_url else "profile"
                    })
                    self.log(f"Found on SoundCloud: {title} - URL: {full_url}")
                except Exception as e:
                    self.log(f"Error parsing SoundCloud result: {e}")
            
            return soundcloud_results
        except Exception as e:
            self.log(f"Error searching on SoundCloud: {e}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def search_youtube(self, query):
        """Search for music on YouTube with pagination."""
        try:
            # Use yt-dlp for searching (modify to respect max_results)
            command = ["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearch{self.max_results}:{query}"]
            print(f"[SearchWorker] Searching YouTube with: {' '.join(command)}")
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"[SearchWorker] Error searching YouTube: {stderr}")
                return []
            
            results = []
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Extract relevant info
                    title = data.get('title', 'Unknown Title')
                    url = data.get('webpage_url', '')
                    # Try to extract artist from title
                    artist = "Unknown Artist"
                    if " - " in title:
                        artist, title = title.split(" - ", 1)
                    
                    results.append({
                        "source": "youtube",
                        "title": title,
                        "artist": artist,
                        "url": url,
                        "type": "video"
                    })
                    print(f"[SearchWorker] Found on YouTube: {title} - URL: {url}")
                except json.JSONDecodeError:
                    print(f"[SearchWorker] Error parsing YouTube result: {line}")
                except Exception as e:
                    print(f"[SearchWorker] Error processing YouTube result: {e}")
            
            return results
        except Exception as e:
            print(f"[SearchWorker] Error searching on YouTube: {e}")
            import traceback
            print(traceback.format_exc())
            return []



class UrlPlayer(BaseModule):
    """Módulo para reproducir música desde URLs (YouTube, SoundCloud, Bandcamp)."""
    
    def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
        # Extraer configuraciones específicas de los kwargs
        self.mpv_temp_dir = kwargs.pop('mpv_temp_dir', None)
        
        # Extraer configuraciones de API desde los argumentos
        self.spotify_client_id = kwargs.pop('spotify_client_id', None)
        self.spotify_client_secret = kwargs.pop('spotify_client_secret', None)
        self.lastfm_api_key = kwargs.pop('lastfm_api_key', None)
        self.lastfm_user = kwargs.pop('lastfm_user', None)
        
        # Configuración de base de datos
        self.db_path = kwargs.pop('db_path', os.path.join(PROJECT_ROOT, "base_datos", "musica.sqlite"))
        
        # Establecer variables de entorno para que los módulos existentes puedan usarlas
        if self.spotify_client_id:
            os.environ["SPOTIFY_CLIENT_ID"] = self.spotify_client_id
        if self.spotify_client_secret:
            os.environ["SPOTIFY_CLIENT_SECRET"] = self.spotify_client_secret
        if self.lastfm_api_key:
            os.environ["LASTFM_API_KEY"] = self.lastfm_api_key
        if self.lastfm_user:
            os.environ["LASTFM_USER"] = self.lastfm_user
        
        # Si no se proporcionó un directorio, creamos uno temporal
        if not self.mpv_temp_dir:
            try:
                import tempfile
                self.mpv_temp_dir = tempfile.mkdtemp(prefix="mpv_socket_")
                print(f"[UrlPlayer] Directorio temporal creado: {self.mpv_temp_dir}")
            except Exception as e:
                print(f"[UrlPlayer] Error al crear directorio temporal: {str(e)}")
                self.mpv_temp_dir = "/tmp"  # Fallback a /tmp si falla la creación
        
        # Inicializar otras variables de instancia
        self.player_process = None
        self.current_playlist = []
        self.current_track_index = -1
        self.media_info_cache = {}
        self.yt_dlp_process = None
        self.is_playing = False
        self.mpv_socket = None
        self.mpv_wid = None
        
        # Comprobar si los servicios están habilitados según las credenciales
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        self.lastfm_enabled = bool(self.lastfm_api_key)
        
        # Obtener la configuración de servicios incluidos
        self.included_services = kwargs.pop('included_services', {
            'youtube': True,
            'soundcloud': True,
            'bandcamp': True,
            'spotify': self.spotify_enabled,
            'lastfm': self.lastfm_enabled
        })
        
        # Si un servicio no tiene credenciales, asegurarse de que esté desactivado
        if not self.spotify_enabled:
            self.included_services['spotify'] = False
        if not self.lastfm_enabled:
            self.included_services['lastfm'] = False
        
        # Inicializar variables para widgets
        self.lineEdit = None
        self.searchButton = None
        self.treeWidget = None
        self.playButton = None
        self.rewButton = None
        self.ffButton_3 = None
        self.tabWidget = None
        self.listWidget = None
        self.delButton = None
        self.addButton = None
        self.textEdit = None
        
        # Obtener configuración de paginación
        self.num_servicios_spinBox = kwargs.pop('pagination_value', 10)
        
        # Ahora llamamos al constructor padre que llamará a init_ui()
        super().__init__(parent, theme, **kwargs)

        
    def log(self, message):
        """Registra un mensaje en el TextEdit y en la consola."""
        if hasattr(self, 'textEdit') and self.textEdit:
            self.textEdit.append(message)
        print(f"[UrlPlayer] {message}")
        
    def init_ui(self):
        """Inicializa la interfaz de usuario desde el archivo UI."""
        # Intentar cargar desde archivo UI
        ui_file_loaded = self.load_ui_file("url_player.ui", [
            "lineEdit", "searchButton", "treeWidget", "playButton", 
            "rewButton", "ffButton", "tabWidget", "listWidget",
            "delButton", "addButton", "textEdit", "servicios", "ajustes_avanzados"
        ])
        
        if not ui_file_loaded:
            self._fallback_init_ui()
        
        # Verificar que tenemos todos los widgets necesarios
        if not self.check_required_widgets():
            print("[UrlPlayer] Error: No se pudieron inicializar todos los widgets requeridos")
            return
        
        
        # Cargar configuración
        self.load_settings()

        # Configurar nombres y tooltips
        self.searchButton.setText("Buscar")
        self.searchButton.setToolTip("Buscar información sobre la URL")
        #self.playButton.setText("▶️")
        self.playButton.setIcon(QIcon(":/services/b_play"))

        self.playButton.setToolTip("Reproducir/Pausar")
        #self.rewButton.setText("⏮️")
        self.playButton.setIcon(QIcon(":/services/b_prev"))

        self.rewButton.setToolTip("Anterior")
        #self.ffButton.setText("⏭️")
        self.playButton.setIcon(QIcon(":/services/b_ff"))

        self.ffButton.setToolTip("Siguiente")
        #self.delButton.setText("➖")
        self.playButton.setIcon(QIcon(":/services/b_minus_star"))

        self.delButton.setToolTip("Eliminar de la cola")
        #self.addButton.setText("➕")
        self.playButton.setIcon(QIcon(":/services/b_addstar"))

        self.addButton.setToolTip("Añadir a la cola")
        
        # Configurar TreeWidget
        #self.treeWidget.setHeaderLabels(["Título", "Artista", "Tipo", "Duración"])
        self.treeWidget.setColumnWidth(0, 250)
        self.treeWidget.setColumnWidth(1, 150)
        self.treeWidget.setColumnWidth(2, 80)
        
        # Configurar TabWidget
        self.tabWidget.setTabText(0, "Cola de reproducción")
        self.tabWidget.setTabText(1, "Información")
        self.setup_services_combo()
        
        # Find the tipo_combo if it exists
        if not hasattr(self, 'tipo_combo'):
            self.tipo_combo = self.findChild(QComboBox, 'tipo_combo')
            
        # If tipo_combo exists, set default items if empty
        if self.tipo_combo and self.tipo_combo.count() == 0:
            self.tipo_combo.addItem("Todo")
            self.tipo_combo.addItem("Artista")
            self.tipo_combo.addItem("Álbum")
            self.tipo_combo.addItem("Canción")


        # Actualizar el combo de servicios según la configuración
        self.update_service_combo()

        # Conectar señales
        self.connect_signals()


    def connect_signals(self):
        """Conecta las señales de los widgets a sus respectivos slots."""
        try:
            # Conectar señales con verificación previa
            if self.searchButton:
                self.searchButton.clicked.connect(self.perform_search)
                print("Botón de búsqueda conectado")
            if self.playButton:
                self.playButton.clicked.connect(self.toggle_play_pause)
            
            if self.rewButton:
                self.rewButton.clicked.connect(self.previous_track)
            
            if self.ffButton:
                self.ffButton.clicked.connect(self.next_track)
            
            if self.addButton:
                self.addButton.clicked.connect(self.add_to_queue)
            
            if self.delButton:
                self.delButton.clicked.connect(self.remove_from_queue)
            
            if self.lineEdit:
                self.lineEdit.returnPressed.connect(self.perform_search)
                print("LineEdit conectado para búsqueda con Enter")

            # Conectar eventos de doble clic
            if self.treeWidget:
                self.treeWidget.itemDoubleClicked.connect(self.on_tree_double_click)
                self.on_tree_double_click_original = self.on_tree_double_click
                self.treeWidget.itemDoubleClicked.disconnect(self.on_tree_double_click)
                self.treeWidget.itemDoubleClicked.connect(self.on_tree_double_click)

            if self.listWidget:
                # First disconnect to avoid multiple connections
                try:
                    self.listWidget.itemDoubleClicked.disconnect()
                except TypeError:
                    pass  # If it wasn't connected, that's fine
                # Connect to the right method
                self.listWidget.itemDoubleClicked.connect(self.on_list_double_click)
            
            if hasattr(self, 'ajustes_avanzados'):
                self.ajustes_avanzados.clicked.connect(self.show_advanced_settings)


            # Add this at the end
            if self.treeWidget:
                # Connect item selection changed
                self.treeWidget.itemSelectionChanged.connect(self.on_tree_selection_changed)
                print("[UrlPlayer] Señales conectadas correctamente")

        except Exception as e:
            print(f"[UrlPlayer] Error al conectar señales: {str(e)}")

    def _fallback_init_ui(self):
        """Crea la UI manualmente en caso de que falle la carga del archivo UI."""
        layout = QVBoxLayout(self)
        
        # Panel de búsqueda
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        self.lineEdit = QLineEdit()
        self.searchButton = QPushButton("Buscar")
        search_layout.addWidget(self.lineEdit)
        search_layout.addWidget(self.searchButton)
        
        # Panel principal
        main_frame = QFrame()
        main_layout = QHBoxLayout(main_frame)
        
        # Contenedor del árbol
        tree_frame = QFrame()
        tree_layout = QVBoxLayout(tree_frame)
        self.treeWidget = QTreeWidget()
        self.treeWidget.setHeaderLabels(["Título", "Artista", "Tipo", "Duración"])
        tree_layout.addWidget(self.treeWidget)
        
        # Contenedor del reproductor
        player_frame = QFrame()
        player_layout = QVBoxLayout(player_frame)
        
        # Panel de botones del reproductor
        player_buttons_frame = QFrame()
        player_buttons_layout = QHBoxLayout(player_buttons_frame)
        self.rewButton = QPushButton("⏮️")
        self.ffButton = QPushButton("⏭️")
        self.playButton = QPushButton("▶️")
        player_buttons_layout.addWidget(self.rewButton)
        player_buttons_layout.addWidget(self.ffButton)
        player_buttons_layout.addWidget(self.playButton)
        

        
        # Panel de información
        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        self.tabWidget = QTabWidget()
        
        # Tab de playlists
        playlists_tab = QWidget()
        playlists_layout = QVBoxLayout(playlists_tab)
        self.listWidget = QListWidget()
        
        playlist_buttons_frame = QFrame()
        playlist_buttons_layout = QHBoxLayout(playlist_buttons_frame)
        self.addButton = QPushButton("➕")
        self.delButton = QPushButton("➖")
        playlist_buttons_layout.addWidget(self.addButton)
        playlist_buttons_layout.addWidget(self.delButton)
        
        playlists_layout.addWidget(self.listWidget)
        playlists_layout.addWidget(playlist_buttons_frame)
        
        # Tab de información de texto
        info_tab = QWidget()
        info_tab_layout = QVBoxLayout(info_tab)
        self.textEdit = QTextEdit()
        info_tab_layout.addWidget(self.textEdit)
        
        # Añadir tabs
        self.tabWidget.addTab(playlists_tab, "Cola de reproducción")
        self.tabWidget.addTab(info_tab, "Información")
        
        info_layout.addWidget(self.tabWidget)
        
        # Añadir todo al layout del reproductor
        player_layout.addWidget(player_buttons_frame)
        player_layout.addWidget(info_frame)
        
        # Añadir frames al layout principal
        main_layout.addWidget(tree_frame)
        main_layout.addWidget(player_frame)
        
        # Añadir todo al layout principal
        layout.addWidget(search_frame)
        layout.addWidget(main_frame)

    def check_required_widgets(self):
        """Verifica que todos los widgets requeridos existan."""
        required_widgets = [
            "lineEdit", "searchButton", "treeWidget", "playButton", 
            "ffButton", "rewButton", "tabWidget", "listWidget",
            "addButton", "delButton", "textEdit", "servicios", "ajustes_avanzados"
        ]
        
        all_ok = True
        for widget_name in required_widgets:
            if not hasattr(self, widget_name) or getattr(self, widget_name) is None:
                print(f"[UrlPlayer] Error: Widget {widget_name} no encontrado")
                all_ok = False
        
        return all_ok



    def show_advanced_settings(self):
        """Show the advanced settings dialog."""
        try:
            # Create the dialog from UI file
            dialog = QDialog(self)
            ui_file = os.path.join(PROJECT_ROOT, "ui", "url_playlist_advanced_settings_dialog.ui")
            
            if os.path.exists(ui_file):
                uic.loadUi(ui_file, dialog)
                
                # Set up current values
                if hasattr(dialog, 'num_servicios_spinBox'):
                    dialog.num_servicios_spinBox.setValue(self.num_servicios_spinBox)
                
                # Set up checkboxes based on current settings
                self._setup_service_checkboxes(dialog)
                
                # Connect the button box
                if hasattr(dialog, 'adv_sett_buttonBox'):
                    # Conecta los botones estándar de QDialogButtonBox
                    dialog.adv_sett_buttonBox.accepted.connect(lambda: self._save_advanced_settings(dialog))
                    dialog.adv_sett_buttonBox.rejected.connect(dialog.reject)
                
                # Show the dialog
                result = dialog.exec()
                
                # Si el resultado es QDialog.Accepted, los ajustes ya se habrán guardado
                # mediante la conexión con _save_advanced_settings
            else:
                self.log(f"UI file not found: {ui_file}")
                QMessageBox.warning(self, "Error", f"UI file not found: {ui_file}")
        except Exception as e:
            self.log(f"Error showing advanced settings: {str(e)}")
            import traceback
            self.log(traceback.format_exc())


    def _setup_service_checkboxes(self, dialog):
        """Set up service checkboxes based on current settings."""
        # Initialize the services dict if it doesn't exist
        if not hasattr(self, 'included_services'):
            self.included_services = {
                'youtube': True,
                'soundcloud': True,
                'bandcamp': True,
                'spotify': True,
                'lastfm': True,
                # Add more services as needed
            }
        
        # Map checkboxes to service keys
        checkbox_mapping = {
            'youtube_check': 'youtube',
            'soundcloud_check': 'soundcloud',
            'bandcamp_check': 'bandcamp',
            'spotify_check': 'spotify',
            'lastfm_check': 'lastfm'
            # Add more as needed
        }
        
        # Set checkbox states based on current settings
        for checkbox_name, service_key in checkbox_mapping.items():
            if hasattr(dialog, checkbox_name):
                checkbox = getattr(dialog, checkbox_name)
                # Convert string 'True'/'False' to actual boolean if needed
                value = self.included_services.get(service_key, True)
                if isinstance(value, str):
                    value = value.lower() == 'true'
                checkbox.setChecked(value)

    def _save_advanced_settings(self, dialog):
        """Guarda los ajustes del diálogo en las variables del objeto."""
        try:
            # Guardar valor de paginación
            if hasattr(dialog, 'num_servicios_spinBox'):
                self.num_servicios_spinBox = dialog.num_servicios_spinBox.value()
                self.log(f"Set pagination to {self.num_servicios_spinBox} results per page")
            
            # Guardar configuración de inclusión de servicios
            checkbox_mapping = {
                'youtube_check': 'youtube',
                'soundcloud_check': 'soundcloud',
                'bandcamp_check': 'bandcamp',
                'lastfm_check': 'lastfm'
                    # Añadir más según sea necesario
            }
            
            for checkbox_name, service_key in checkbox_mapping.items():
                if hasattr(dialog, checkbox_name):
                    checkbox = getattr(dialog, checkbox_name)
                    # Store actual boolean, not string
                    self.included_services[service_key] = checkbox.isChecked()
                    self.log(f"Service {service_key} included: {checkbox.isChecked()}")
            
            # Actualizar UI o estado si es necesario
            self.update_service_combo()
            
            # Guardar en archivo YAML
            self.save_settings()
            
            # Cerrar el diálogo
            dialog.accept()
        except Exception as e:
            self.log(f"Error saving advanced settings: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            QMessageBox.warning(self, "Error", f"Error al guardar la configuración: {str(e)}")

    def load_settings(self):
        """Carga la configuración del módulo desde el archivo de configuración general."""
        try:
            config_path = os.path.join(PROJECT_ROOT, "config", "config.yml")
            
            if os.path.exists(config_path):
                # Usar las funciones de carga de configuración global
                from main import load_config_file
                config_data = load_config_file(config_path)
                
                # Buscar la configuración específica para este módulo
                # Primero entre los módulos activos
                module_config = None
                for module in config_data.get('modules', []):
                    if module.get('name') == 'Url Playlists':
                        module_config = module.get('args', {})
                        break
                
                # Si no se encuentra en los activos, buscar en los desactivados
                if module_config is None:
                    for module in config_data.get('modulos_desactivados', []):
                        if module.get('name') == 'Url Playlists':
                            module_config = module.get('args', {})
                            break
                
                if module_config:
                    # Cargar pagination_value
                    self.pagination_value = module_config.get('pagination_value', 10)
                    self.num_servicios_spinBox = self.pagination_value  # Sincronizar ambos valores
                    
                    # Cargar included_services
                    included_services = module_config.get('included_services', {})
                    
                    # Ensure included_services values are booleans, not strings
                    self.included_services = {}
                    for key, value in included_services.items():
                        if isinstance(value, str):
                            self.included_services[key] = value.lower() == 'true'
                        else:
                            self.included_services[key] = bool(value)
                    
                    if not self.included_services:
                        # Valores por defecto si no hay configuración específica
                        self.included_services = {
                            'youtube': True,
                            'soundcloud': True,
                            'bandcamp': True,
                            'lastfm': False,
                        }
                    
                    self.log(f"Configuración cargada desde config.yml: {module_config}")
                else:
                    self.log("No se encontró configuración específica en config.yml, usando valores por defecto")
                    # Inicializar con valores por defecto
                    self.pagination_value = 10
                    self.num_servicios_spinBox = 10
                    self.included_services = {
                        'youtube': True,
                        'soundcloud': True,
                        'bandcamp': True,
                        'lastfm': False,
                    }
            else:
                self.log(f"Archivo de configuración general no encontrado, usando valores por defecto")
                # Inicializar con valores por defecto
                self.pagination_value = 10
                self.num_servicios_spinBox = 10
                self.included_services = {
                    'youtube': True,
                    'soundcloud': True,
                    'bandcamp': True,
                    'lastfm': False,
                }
        except Exception as e:
            self.log(f"Error al cargar configuración: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            
            # Inicializar con valores por defecto en caso de error
            self.pagination_value = 10
            self.num_servicios_spinBox = 10
            self.included_services = {
                'youtube': True,
                'soundcloud': True,
                'bandcamp': True,
                'lastfm': False,
            }

    def save_settings(self):
        """Guarda la configuración del módulo en el archivo de configuración general."""
        try:
            config_path = os.path.join(PROJECT_ROOT, "config", "config.yml")
            
            if not os.path.exists(config_path):
                self.log(f"El archivo de configuración general no existe: {config_path}")
                return
            
            # Usar las funciones de carga/guardado de configuración global
            from main import load_config_file, save_config_file
            
            # Cargar la configuración actual
            config_data = load_config_file(config_path)
            
            # Asegurar que pagination_value esté sincronizado con num_servicios_spinBox
            self.pagination_value = self.num_servicios_spinBox
            
            # Preparar configuración de este módulo
            new_settings = {
                'mpv_temp_dir': '.config/mpv/_mpv_socket',  # Mantener valor existente o usar por defecto
                'pagination_value': self.pagination_value,
                'included_services': self.included_services  # Now storing actual boolean values
            }
            
            # Bandera para saber si se encontró y actualizó el módulo
            module_updated = False
            
            # Actualizar la configuración en el módulo correspondiente
            for module in config_data.get('modules', []):
                if module.get('name') == 'Url Playlists':
                    # Reemplazar completamente los argumentos para evitar duplicados
                    module['args'] = new_settings
                    module_updated = True
                    break
            
            # Si no se encontró en los módulos activos, buscar en los desactivados
            if not module_updated:
                for module in config_data.get('modulos_desactivados', []):
                    if module.get('name') == 'Url Playlists':
                        # Reemplazar completamente los argumentos para evitar duplicados
                        module['args'] = new_settings
                        module_updated = True
                        break
            
            # Si no se encontró el módulo, registrar un aviso
            if not module_updated:
                self.log("No se encontró el módulo 'Url Playlists' en la configuración")
                return
            
            # Guardar la configuración actualizada
            save_config_file(config_path, config_data)
            
            self.log(f"Configuración guardada en {config_path}")
        except Exception as e:
            self.log(f"Error al guardar configuración: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
   

    def setup_services_combo(self):
        """Configura el combo box de servicios disponibles."""
        self.servicios.addItem(QIcon(":/services/add"), "Todos")
        self.servicios.addItem(QIcon(":/services/youtube"), "YouTube")
        self.servicios.addItem(QIcon(":/services/spotify"), "Spotify")
        self.servicios.addItem(QIcon(":/services/soundcloud"), "SoundCloud")
        self.servicios.addItem(QIcon(":/services/lastfm"), "Last.fm")
        self.servicios.addItem(QIcon(":/services/bandcamp"), "Bandcamp")
        
        # Conectar la señal de cambio del combo box
        self.servicios.currentIndexChanged.connect(self.service_changed)

    def update_service_combo(self):
        """Update the service combo to reflect current settings."""
        # Keep current selection
        current_selection = self.servicios.currentText() if hasattr(self, 'servicios') else "Todos"
        
        # Disconnect signals temporarily to avoid triggering events
        if hasattr(self, 'servicios'):
            try:
                self.servicios.currentIndexChanged.disconnect(self.service_changed)
            except:
                pass
                
            # Clear the combo box
            self.servicios.clear()
            
            # Add "Todos" option
            self.servicios.addItem(QIcon(":/services/wiki"), "Todos")
            
            # Add individual services
            service_icons = {
                'youtube': ":/services/youtube",
                'soundcloud': ":/services/soundcloud",
                'bandcamp': ":/services/bandcamp",  # Assuming you have this icon
                'lastmf': ":/services/lastfm"

                # Add more as needed
            }
            
            for service, icon_path in service_icons.items():
                # Only add if service is available (you might want to check this)
                service_name = service.capitalize()
                self.servicios.addItem(QIcon(icon_path), service_name)
            
            # Restore previous selection if possible
            index = self.servicios.findText(current_selection)
            if index >= 0:
                self.servicios.setCurrentIndex(index)
            
            # Reconnect signal
            self.servicios.currentIndexChanged.connect(self.service_changed)


    def service_changed(self, index):
        """Maneja el cambio de servicio seleccionado."""
        service = self.servicios.currentText()
        self.log(f"Servicio seleccionado: {service}")
        
        # Limpiar resultados anteriores si hay alguno
        self.treeWidget.clear()
        
        # Modificar placeholder del LineEdit según el servicio
        placeholders = {
            "Todos": "Buscar en todos los servicios...",
            "YouTube": "Buscar en YouTube...",
            "Spotify": "Buscar en Spotify...",
            "SoundCloud": "Buscar en SoundCloud...",
            "Last.fm": "Buscar en Last.fm...",
            "Bandcamp": "Buscar en Bandcamp..."
        }
        
        self.lineEdit.setPlaceholderText(placeholders.get(service, "Buscar..."))
        
        # Si hay un texto en el campo de búsqueda, realizar la búsqueda con el nuevo servicio
        if self.lineEdit.text().strip():
            self.perform_search()

    def search_in_database(self, query, search_type="all"):
        """
        Busca enlaces en la base de datos antes de recurrir a APIs externas
        
        Args:
            query: Texto de búsqueda
            search_type: Tipo de búsqueda ('artist', 'album', 'track', 'all')
        
        Returns:
            List de resultados encontrados
        """
        try:
            # Importar la clase de consulta
            from base_datos.tools.consultar_items_db import MusicDatabaseQuery
            
            # Usar la ruta de base de datos configurada
            db_path = self.db_path
            
            if not os.path.exists(db_path):
                self.log(f"Base de datos no encontrada en: {db_path}")
                return []
                    
            db = MusicDatabaseQuery(db_path)
            results = []
            
            # Mapear tipo de búsqueda a función correspondiente
            if search_type.lower() in ["artista", "artist"]:
                # Buscar artista
                self.log(f"Buscando artista '{query}' en la base de datos")
                artist_info = db.get_artist_info(query)
                if artist_info:
                    # Extraer enlaces
                    links = artist_info.get('links', {})
                    base_result = {
                        "source": "database",
                        "title": query,
                        "artist": query,
                        "type": "artist",
                        "from_database": True
                    }
                    
                    # Añadir URLs de cada servicio al resultado
                    for service, url in links.items():
                        if url:
                            service_key = f"{service}_url"
                            base_result[service_key] = url
                    
                    # Asegurar que hay al menos una URL
                    has_urls = any(key.endswith('_url') and base_result[key] for key in base_result)
                    if has_urls:
                        # Usar la primera URL disponible como URL principal
                        for key in base_result:
                            if key.endswith('_url') and base_result[key]:
                                base_result["url"] = base_result[key]
                                break
                        
                        results.append(base_result)
                        self.log(f"Encontrados enlaces para artista '{query}' en la base de datos")
                
            elif search_type.lower() in ["album", "álbum"]:
                # Intentar extraer artista y álbum del query
                parts = query.split(" - ", 1)
                if len(parts) > 1:
                    artist, album = parts
                    self.log(f"Buscando álbum '{album}' de '{artist}' en la base de datos")
                    album_info = db.get_album_info(album, artist)
                    if album_info:
                        album_links = db.get_album_links(artist, album)
                        if album_links:
                            base_result = {
                                "source": "database",
                                "title": album,
                                "artist": artist,
                                "type": "album",
                                "from_database": True
                            }
                            
                            # Añadir URLs de cada servicio
                            for service, url in album_links.items():
                                if url:
                                    service_key = f"{service}_url"
                                    base_result[service_key] = url
                            
                            # Asegurar que hay al menos una URL
                            has_urls = any(key.endswith('_url') and base_result[key] for key in base_result)
                            if has_urls:
                                # Usar la primera URL disponible como URL principal
                                for key in base_result:
                                    if key.endswith('_url') and base_result[key]:
                                        base_result["url"] = base_result[key]
                                        break
                                    
                                results.append(base_result)
                                self.log(f"Encontrados enlaces para álbum '{album}' en la base de datos")
                else:
                    # Si no hay formato artista - álbum, buscar solo por álbum
                    self.log(f"Buscando álbum '{query}' en la base de datos")
                    album_info = db.get_album_info(query)
                    if album_info:
                        album_links = db.get_album_links(None, query)
                        if album_links:
                            base_result = {
                                "source": "database",
                                "title": query,
                                "artist": album_info.get('artist', ''),
                                "type": "album",
                                "from_database": True
                            }
                            
                            # Añadir URLs de cada servicio
                            for service, url in album_links.items():
                                if url:
                                    service_key = f"{service}_url"
                                    base_result[service_key] = url
                            
                            # Asegurar que hay al menos una URL
                            has_urls = any(key.endswith('_url') and base_result[key] for key in base_result)
                            if has_urls:
                                # Usar la primera URL disponible como URL principal
                                for key in base_result:
                                    if key.endswith('_url') and base_result[key]:
                                        base_result["url"] = base_result[key]
                                        break
                                    
                                results.append(base_result)
                                self.log(f"Encontrados enlaces para álbum '{query}' en la base de datos")
                    
            elif search_type.lower() in ["canción", "track", "song"]:
                # Código similar para canciones...
                # [Código existente para la búsqueda de canciones]
                pass
                
            else:
                # Búsqueda general en todos los tipos
                artist_results = self.search_in_database(query, "artist")
                album_results = self.search_in_database(query, "album")
                song_results = self.search_in_database(query, "track")
                
                results = artist_results + album_results + song_results
            
            db.close()
            return results
                
        except Exception as e:
            self.log(f"Error al buscar en la base de datos: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def contextMenuEvent(self, event):
        """Maneja el evento de menú contextual."""
        # Comprobar si estamos sobre el TreeWidget
        if self.treeWidget.underMouse():
            # Crear menú contextual
            context_menu = QMenu(self)
            
            # Verificar si hay un ítem seleccionado
            current_item = self.treeWidget.currentItem()
            if current_item:
                # Obtener datos del ítem
                item_data = current_item.data(0, Qt.ItemDataRole.UserRole)
                
                url = None
                if isinstance(item_data, dict) and 'url' in item_data:
                    url = item_data['url']
                elif current_item.toolTip(0) and current_item.toolTip(0).startswith("URL: "):
                    url = current_item.toolTip(0)[5:]
                
                if url:
                    # Añadir acciones al menú
                    copy_action = context_menu.addAction("Copiar URL")
                    copy_action.triggered.connect(self.copy_url_to_clipboard)
                    
                    open_action = context_menu.addAction("Abrir en navegador")
                    open_action.triggered.connect(lambda: self.open_url_in_browser(url))
                    
                    add_queue_action = context_menu.addAction("Añadir a la cola")
                    add_queue_action.triggered.connect(lambda: self.add_to_queue())
                    
                    # Mostrar el menú en la posición del cursor
                    context_menu.exec(event.globalPos())
                    return
        
        # Pasar el evento al padre para su procesamiento normal
        super().contextMenuEvent(event)


    def on_tree_double_click(self, item, column):
        """Handle double click on tree item to add to queue or play immediately"""
        # Si es un item raíz (fuente) con hijos, solo expandir/colapsar
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return
                
        # Obtener los datos del resultado almacenados
        result_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Si es un resultado de búsqueda
        if isinstance(result_data, dict):
            url = result_data.get('url', '')
            if url:
                # Crear un texto para mostrar
                display_text = f"{result_data.get('artist', '')} - {result_data.get('title', '')}"
                display_text = display_text.strip()
                if not display_text:
                    display_text = url
                
                # Añadir a la cola
                self.add_to_queue_from_url(url, display_text, result_data)
                self.log(f"Añadido a la cola: {display_text}")
                
                # Opcional: Reproducir inmediatamente si no hay nada reproduciéndose
                if not self.is_playing and self.current_track_index == -1:
                    self.current_track_index = len(self.current_playlist) - 1
                    self.play_media()
        else:
            # Manejar la lógica existente para resultados no de búsqueda
            if hasattr(self, 'on_tree_double_click_original'):
                self.on_tree_double_click_original(item, column)

    def add_to_queue_from_url(self, url, display_text, metadata=None):
        """Añade un elemento a la cola basado en URL y texto a mostrar."""
        # Crear un nuevo item para la playlist
        queue_item = QListWidgetItem(display_text)
        queue_item.setData(Qt.ItemDataRole.UserRole, url)
        
        # Añadir a la lista
        self.listWidget.addItem(queue_item)
        
        # Actualizar la lista interna
        self.current_playlist.append({
            'title': metadata.get('title', display_text),
            'artist': metadata.get('artist', ''),
            'url': url,
            'entry_data': metadata
        })
        
        self.log(f"Elemento añadido a la cola: {display_text}")
        
        # Si no hay nada reproduciéndose actualmente, seleccionar este elemento
        if not self.is_playing and self.current_track_index == -1:
            self.current_track_index = len(self.current_playlist) - 1
            self.listWidget.setCurrentRow(self.current_track_index)
    
    def highlight_current_track(self):
        """Resalta visualmente la pista que se está reproduciendo actualmente."""
        # Primero, eliminar formato especial de todos los elementos
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            font = item.font()
            font.setBold(False)
            item.setFont(font)
            # Usar QBrush y QColor para el color
            from PyQt6.QtGui import QBrush, QColor
            item.setForeground(QBrush(QColor("#a9b1d6")))  # Color normal
        
        # Resaltar elemento actual si hay alguno
        if self.current_track_index >= 0 and self.current_track_index < self.listWidget.count():
            current_item = self.listWidget.item(self.current_track_index)
            font = current_item.font()
            font.setBold(True)
            current_item.setFont(font)
            current_item.setForeground(QBrush(QColor("#7aa2f7")))  # Color de resaltado
            
            # Asegurar que el elemento es visible
            self.listWidget.scrollToItem(current_item)


    def on_list_double_click(self, item):
        """Maneja el doble clic en un elemento de la lista."""
        row = self.listWidget.row(item)
        self.current_track_index = row
        
        # Iniciar reproducción del elemento seleccionado
        self.play_from_index(row)
        self.log(f"Reproduciendo '{item.text()}'")

    def play_from_index(self, index):
        """Reproduce desde un índice específico de la cola."""
        if not self.current_playlist or index < 0 or index >= len(self.current_playlist):
            self.log("No hay elementos válidos para reproducir")
            return
        
        # Actualizar el índice actual
        self.current_track_index = index
        
        # Seleccionar visualmente el elemento en la lista
        self.listWidget.setCurrentRow(index)
        
        # Obtener la URL del elemento a reproducir
        current_item = self.current_playlist[index]
        url = current_item['url']
        
        # Verificar que la URL sea válida
        if not url:
            self.log("URL inválida para reproducción")
            return
        
        # Detener reproducción actual si existe
        self.stop_playback()
        
        # Reproducir la URL actual
        self.play_single_url(url)
        
        # Resaltar elemento actual
        self.highlight_current_track()
        
        # Mostrar información en el log
        title = current_item.get('title', 'Desconocido')
        artist = current_item.get('artist', '')
        display = f"{artist} - {title}" if artist else title
        self.log(f"Reproduciendo: {display}")

    def play_single_url(self, url):
        """Reproduce una única URL con MPV."""
        if not url:
            self.log("Error: URL vacía")
            return
        
        # Asegurarse de que la URL es un string
        if isinstance(url, dict):
            url = url.get('url', str(url))
        url = str(url)
        
        # Verificar o crear directorio temporal para el socket
        if not self.mpv_temp_dir or not os.path.exists(self.mpv_temp_dir):
            try:
                self.mpv_temp_dir = tempfile.mkdtemp(prefix="mpv_socket_")
                self.log(f"Directorio temporal creado o recreado: {self.mpv_temp_dir}")
            except Exception as e:
                self.log(f"Error al crear directorio temporal: {str(e)}")
                self.mpv_temp_dir = "/tmp"
        
        # Crear ruta para el socket
        socket_path = os.path.join(self.mpv_temp_dir, "mpv_socket")
        self.mpv_socket = socket_path
        
        # Si existe un socket anterior, eliminarlo
        if os.path.exists(socket_path):
            try:
                os.remove(socket_path)
                self.log(f"Socket antiguo eliminado: {socket_path}")
            except Exception as e:
                self.log(f"Error al eliminar socket antiguo: {str(e)}")
        
        # Preparar argumentos para mpv (ventana independiente)
        mpv_args = [
            "--input-ipc-server=" + socket_path,  # Socket para controlar mpv
            "--ytdl=yes",                # Usar youtube-dl/yt-dlp para streaming
            "--ytdl-format=best",        # Mejor calidad disponible
            "--keep-open=yes",           # Mantener abierto al finalizar
            url                          # La URL a reproducir
        ]
        
        # Registrar comando completo para depuración
        self.log(f"Comando MPV: mpv {' '.join(mpv_args)}")
        
        # Iniciar mpv para reproducir
        self.player_process = QProcess()
        self.player_process.readyReadStandardOutput.connect(self.handle_player_output)
        self.player_process.readyReadStandardError.connect(self.handle_player_error)
        self.player_process.finished.connect(self.handle_player_finished)
        
        try:
            self.player_process.start("mpv", mpv_args)
            success = self.player_process.waitForStarted(3000)  # Esperar 3 segundos máximo
            
            if success:
                self.is_playing = True
                self.playButton.setIcon(QIcon(":/services/b_pause"))
                self.log("Reproducción iniciada correctamente")
            else:
                self.log("Error al iniciar MPV: timeout")
                error = self.player_process.errorString()
                self.log(f"Error detallado: {error}")
                    
        except Exception as e:
            self.log(f"Excepción al iniciar MPV: {str(e)}")



    def play_from_index(self, index):
        """Reproduce desde un índice específico de la cola."""
        if not self.current_playlist or index < 0 or index >= len(self.current_playlist):
            return
                
        # Detener reproducción actual si existe
        self.stop_playback()
                
        # Obtener todas las URLs a partir del índice seleccionado
        urls = [item['url'] for item in self.current_playlist[index:]]
        
        # Reproducir la lista comenzando por el elemento seleccionado
        self.play_with_mpv(urls)

    def play_with_mpv(self, urls):
        """Reproduce las URLs proporcionadas con MPV en ventana independiente."""
        if not urls:
            return
        
        # Verificar o crear directorio temporal para el socket
        if not self.mpv_temp_dir or not os.path.exists(self.mpv_temp_dir):
            try:
                self.mpv_temp_dir = tempfile.mkdtemp(prefix="mpv_socket_")
                self.log(f"Directorio temporal creado o recreado: {self.mpv_temp_dir}")
            except Exception as e:
                self.log(f"Error al crear directorio temporal: {str(e)}")
                self.mpv_temp_dir = "/tmp"
        
        # Crear ruta para el socket
        socket_path = os.path.join(self.mpv_temp_dir, "mpv_socket")
        self.mpv_socket = socket_path
        
        # Si existe un socket anterior, eliminarlo
        if os.path.exists(socket_path):
            try:
                os.remove(socket_path)
                self.log(f"Socket antiguo eliminado: {socket_path}")
            except Exception as e:
                self.log(f"Error al eliminar socket antiguo: {str(e)}")
        
        # Preparar argumentos para mpv (ventana independiente)
        mpv_args = [
            "--input-ipc-server=" + socket_path,  # Socket para controlar mpv
            "--ytdl=yes",                # Usar youtube-dl/yt-dlp para streaming
            "--ytdl-format=best",        # Mejor calidad disponible
            "--keep-open=yes",           # Mantener abierto al finalizar
        ]
        
        # Convertir todas las URLs a strings si no lo son
        url_args = []
        for url in urls:
            if isinstance(url, dict):
                # Si es un diccionario, intentar extraer la URL
                url_str = url.get('url', str(url))
                url_args.append(url_str)
            else:
                url_args.append(str(url))
        
        # Añadir URLs
        mpv_args.extend(url_args)
        
        # Registrar comando completo para depuración
        self.log(f"Comando MPV: mpv {' '.join(mpv_args)}")
        
        # Iniciar mpv para reproducir
        self.player_process = QProcess()
        self.player_process.readyReadStandardOutput.connect(self.handle_player_output)
        self.player_process.readyReadStandardError.connect(self.handle_player_error)
        self.player_process.finished.connect(self.handle_player_finished)
        
        try:
            self.player_process.start("mpv", mpv_args)
            success = self.player_process.waitForStarted(3000)  # Esperar 3 segundos máximo
            
            if success:
                self.is_playing = True
                self.playButton.setIcon(QIcon(":/services/b_pause"))
                self.log("Reproducción iniciada correctamente")
            else:
                self.log("Error al iniciar MPV: timeout")
                error = self.player_process.errorString()
                self.log(f"Error detallado: {error}")
                    
        except Exception as e:
            self.log(f"Excepción al iniciar MPV: {str(e)}")
    def perform_search(self):
        """Realiza una búsqueda basada en el servicio seleccionado y la consulta."""
        query = self.lineEdit.text().strip()
        if not query:
            return
        
        self.log(f"Buscando: {query}")
        
        # Limpiar resultados previos
        self.treeWidget.clear()
        self.textEdit.clear()
        QApplication.processEvents()  # Actualiza la UI
        
        # Obtener el servicio seleccionado
        service = self.servicios.currentText()
        
        # Obtener el tipo de búsqueda seleccionado (artista, álbum, canción, todo)
        search_type = "all"
        if hasattr(self, 'tipo_combo') and self.tipo_combo:
            search_type = self.tipo_combo.currentText().lower()
        
        # Determinar qué servicios incluir
        if service == "Todos":
            active_services = [s for s, included in self.included_services.items() if included]
            if not active_services:
                self.log("No hay servicios seleccionados para la búsqueda. Por favor, actívalos en Configuración Avanzada.")
                return
        else:
            # Convert from display name to service id
            service_id = service.lower()
            active_services = [service_id]
        
        # Mostrar progreso
        self.textEdit.append(f"Buscando '{query}' en {service} (tipo: {search_type}, máx. {self.pagination_value} resultados por servicio)...")
        QApplication.processEvents()  # Actualiza la UI
        
        # Desactivar controles durante la búsqueda
        self.searchButton.setEnabled(False)
        self.lineEdit.setEnabled(False)
        QApplication.processEvents()  # Actualiza la UI
        
        # Crear y configurar el worker
        worker = SearchWorker(active_services, query, max_results=self.pagination_value)
        worker.parent = self  # Set parent to access search_in_database
        worker.search_type = search_type  # Pass search type to worker
        
        # Conectar señales
        worker.signals.results.connect(self.display_search_results)
        worker.signals.error.connect(lambda err: self.log(f"Error en la búsqueda: {err}"))
        worker.signals.finished.connect(self.search_finished)
        
        # Iniciar el worker en el thread pool
        QThreadPool.globalInstance().start(worker)


        
    def search_finished(self):
        """Función llamada cuando termina la búsqueda."""
        self.log(f"Búsqueda completada.")
        # Reactivar controles
        self.searchButton.setEnabled(True)
        self.lineEdit.setEnabled(True)
        QApplication.processEvents()  # Actualiza la UI

 
    def handle_direct_url(self, url):
        """Maneja la entrada de una URL directa."""
        self.log(f"Procesando URL directa: {url}")
        
        # Determinar tipo de servicio basado en la URL
        service_type = "desconocido"
        if "youtube.com" in url or "youtu.be" in url:
            service_type = "YouTube"
        elif "soundcloud.com" in url:
            service_type = "SoundCloud"
        elif "bandcamp.com" in url:
            service_type = "Bandcamp"
        elif "spotify.com" in url:
            service_type = "Spotify"
        elif "last.fm" in url:
            service_type = "lastfm"
        
        self.log(f"Detectado servicio: {service_type}")
        
        # Crear un item simple para mostrar en el árbol
        self.treeWidget.clear()
        root_item = QTreeWidgetItem(self.treeWidget)
        root_item.setText(0, "URL directa")
        root_item.setText(1, service_type)
        
        url_item = QTreeWidgetItem(root_item)
        url_item.setText(0, url)
        url_item.setText(1, "")
        url_item.setText(2, service_type)
        
        # Guardar la URL para uso posterior
        url_item.setData(0, Qt.ItemDataRole.UserRole, {
            "source": service_type.lower(),
            "title": url,
            "artist": "",
            "url": url,
            "type": "url"
        })
        
        root_item.setExpanded(True)
        
        # Opcionalmente, obtener más información sobre la URL
        self.get_media_info(url)


    def process_media_info(self, exit_code, url):
        """Procesa la información obtenida de yt-dlp."""
        if exit_code != 0:
            self.log(f"Error al obtener información de: {url}")
            return
        
        output = self.yt_dlp_process.readAllStandardOutput().data().decode('utf-8')
        error = self.yt_dlp_process.readAllStandardError().data().decode('utf-8')
        
        if error and not output:
            self.log(f"Error: {error}")
            return
        
        try:
            # Puede ser un JSON por línea en caso de playlists
            entries = []
            for line in output.strip().split('\n'):
                if line.strip():
                    entries.append(json.loads(line))
            
            # Guardar en caché
            self.media_info_cache[url] = entries
            self.display_media_info(entries, url)
            
        except json.JSONDecodeError as e:
            self.log(f"Error al procesar la información JSON: {str(e)}")
    
    def display_search_results(self, results):
        """Muestra los resultados de la búsqueda en el TreeWidget."""
        self.treeWidget.clear()
        QApplication.processEvents()  # Actualiza la UI
        
        if not results:
            self.textEdit.append("No se encontraron resultados.")
            QApplication.processEvents()  # Actualiza la UI
            return
        
        # Primero, agrupar resultados por tipo (artist, album, track) y luego por fuente
        grouped_results = {}
        db_results = []
        api_results = []
        
        # Separar resultados de DB vs API
        for result in results:
            if 'from_database' in result and result['from_database']:
                db_results.append(result)
            else:
                api_results.append(result)
        
        # Procesar resultados de la base de datos primero
        if db_results:
            db_group = QTreeWidgetItem(self.treeWidget)
            db_group.setText(0, "Resultados de Base de Datos")
            db_group.setExpanded(True)
            
            # Usar una fuente personalizada para encabezados
            font = db_group.font(0)
            font.setBold(True)
            db_group.setFont(0, font)
            
            # Agrupar por tipo (artist, album, track)
            db_by_type = {}
            for result in db_results:
                result_type = result.get('type', 'unknown')
                if result_type not in db_by_type:
                    db_by_type[result_type] = []
                db_by_type[result_type].append(result)
            
            # Crear subgrupos por tipo
            for result_type, type_results in db_by_type.items():
                type_item = QTreeWidgetItem(db_group)
                type_label = {
                    'artist': 'Artistas',
                    'album': 'Álbumes',
                    'track': 'Canciones',
                }.get(result_type, result_type.capitalize())
                
                type_item.setText(0, f"{type_label} ({len(type_results)})")
                type_item.setExpanded(True)
                
                # Font para el tipo
                type_font = type_item.font(0)
                type_font.setItalic(True)
                type_item.setFont(0, type_font)
                
                # Añadir cada resultado dentro de su tipo
                for result in type_results:
                    result_item = QTreeWidgetItem(type_item)
                    result_item.setText(0, result['title'])
                    result_item.setText(1, result['artist'])
                    result_item.setText(2, result_type)
                    
                    # Añadir URL como tooltip
                    if 'url' in result:
                        result_item.setToolTip(0, f"URL: {result['url']}")
                        # Guardar URL para copia al portapapeles
                        result_item.setData(0, Qt.ItemDataRole.UserRole, result)
                    
                    # Si hay múltiples enlaces, crear elementos hijo para cada servicio
                    services = ['spotify', 'bandcamp', 'lastfm', 'youtube', 'musicbrainz', 'discogs']
                    has_links = False
                    
                    for service in services:
                        service_key = f"{service}_url"
                        if service_key in result and result[service_key]:
                            has_links = True
                            service_item = QTreeWidgetItem(result_item)
                            service_name = service.capitalize()
                            service_item.setText(0, service_name)
                            service_item.setText(1, "")
                            service_item.setText(2, "enlace")
                            
                            # Guardar la URL específica del servicio
                            service_url = result[service_key]
                            service_item.setToolTip(0, service_url)
                            service_data = {'url': service_url, 'source': service, 'title': result['title'], 'artist': result['artist']}
                            service_item.setData(0, Qt.ItemDataRole.UserRole, service_data)
                    
                    if has_links:
                        result_item.setExpanded(True)
        
        # Ahora procesar resultados de APIs
        if api_results:
            # Agrupar por fuente
            sources = {}
            for result in api_results:
                source = result.get('source', 'Desconocido')
                if source not in sources:
                    sources[source] = []
                sources[source].append(result)
            
            # Añadir resultados al árbol
            for source, source_results in sources.items():
                # Crear un encabezado de fuente
                source_item = QTreeWidgetItem(self.treeWidget)
                source_item.setText(0, f"{source.capitalize()} ({len(source_results)})")
                source_item.setExpanded(True)
                
                # Usar una fuente personalizada para encabezados
                font = source_item.font(0)
                font.setBold(True)
                source_item.setFont(0, font)
                
                # Añadir resultados para esta fuente
                for result in source_results:
                    result_item = QTreeWidgetItem(source_item)
                    result_item.setText(0, result['title'])
                    result_item.setText(1, result['artist'])
                    result_item.setText(2, result.get('type', ''))
                    
                    # Añadir URL como tooltip
                    if 'url' in result:
                        result_item.setToolTip(0, f"URL: {result['url']}")
                    
                    # Almacenar los datos completos del resultado para uso posterior
                    result_item.setData(0, Qt.ItemDataRole.UserRole, result)
        
        if results:
                first_result = None
                # Find first actual result item (not a header)
                if 'from_database' in results[0] and results[0]['from_database']:
                    first_result = results[0]
                else:
                    for result in results:
                        if 'url' in result:
                            first_result = result
                            break
                
                if first_result:
                    self.display_wiki_info(first_result)

        # Actualizar contador de resultados
        total_results = len(db_results) + len(api_results)
        self.textEdit.append(f"Encontrados {total_results} resultados.")
        if db_results:
            self.textEdit.append(f"- {len(db_results)} desde la base de datos")
        if api_results:
            self.textEdit.append(f"- {len(api_results)} desde servicios en línea")
        
        QApplication.processEvents()  # Actualiza la UI final
        
        # Asegurarnos de que el árbol sea visible
        self.treeWidget.setVisible(True)



    def display_media_info(self, entries, url):
        """Muestra la información obtenida en el TreeWidget."""
        if not entries:
            self.log(f"No se encontró información para: {url}")
            return
        
        self.treeWidget.clear()
        
        # Determinar si es una playlist o un solo elemento
        is_playlist = len(entries) > 1
        
        if is_playlist:
            # Crear un elemento raíz para la playlist
            playlist_title = entries[0].get('playlist_title', 'Playlist')
            root_item = QTreeWidgetItem(self.treeWidget, [playlist_title, "", "Playlist", f"{len(entries)} elementos"])
            
            # Añadir cada entrada como hijo
            for entry in entries:
                self.add_media_item(entry, root_item)
            
            root_item.setExpanded(True)
        else:
            # Añadir el único elemento directamente
            self.add_media_item(entries[0])
        
        # Mostrar información detallada del primer elemento
        if entries:
            self.show_detailed_info(entries[0])
    
    def add_media_item(self, entry, parent=None):
        """Añade un elemento multimedia al TreeWidget."""
        title = entry.get('title', 'Sin título')
        
        # Extraer el artista
        artist = self.extract_artist(entry)
        
        # Determinar el tipo de contenido
        media_type = self.determine_media_type(entry)
        
        # Formatear duración
        duration_str = self.format_duration(entry)
        
        # Crear el item
        item = QTreeWidgetItem([title, artist, media_type, duration_str])
        
        # Almacenar la URL y la información completa como datos del item
        item.setData(0, Qt.ItemDataRole.UserRole, entry.get('webpage_url', entry.get('url', '')))
        item.setData(0, Qt.ItemDataRole.UserRole + 1, entry)  # Guardar toda la info para uso posterior
        
        # Añadir al árbol
        if parent:
            parent.addChild(item)
        else:
            self.treeWidget.addTopLevelItem(item)
            
        return item
    
    def extract_artist(self, entry):
        """Extrae el nombre del artista de la información."""
        # Intenta obtener el artista de diferentes campos según la plataforma
        artist = entry.get('artist', '')
        
        if not artist:
            artist = entry.get('uploader', '')
        
        if not artist:
            # Para Bandcamp, a menudo está en el título como "Artista - Título"
            if 'bandcamp.com' in entry.get('webpage_url', ''):
                title = entry.get('title', '')
                if ' - ' in title:
                    artist = title.split(' - ')[0].strip()
            
            # Para YouTube, a veces está en la descripción o en el canal
            elif 'youtube.com' in entry.get('webpage_url', '') or 'youtu.be' in entry.get('webpage_url', ''):
                artist = entry.get('channel', '')
                
            # Para SoundCloud, suele estar en el uploader
            elif 'soundcloud.com' in entry.get('webpage_url', ''):
                artist = entry.get('uploader', '')
        
        return artist
    
    def determine_media_type(self, entry):
        """Determina el tipo de medio basado en la URL."""
        url = entry.get('webpage_url', '')
        
        if 'youtube.com' in url or 'youtu.be' in url:
            return "YouTube"
        elif 'soundcloud' in url:
            return "SoundCloud"
        elif 'bandcamp' in url:
            return "Bandcamp"
        elif 'last.fm' in url:
            return "Lastfm"
        else:
            return "Desconocido"
    
    def format_duration(self, entry):
        """Formatea la duración en un formato legible."""
        duration = entry.get('duration')
        if not duration:
            return "Desconocido"
        
        try:
            duration = float(duration)
            minutes, seconds = divmod(int(duration), 60)
            hours, minutes = divmod(minutes, 60)
            
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        except (ValueError, TypeError):
            return "Desconocido"
    
    # def showEvent(self, event):
    #     """Cuando el widget se muestra, ajustar el tamaño del frame de video."""
    #     super().showEvent(event)
        
    #     # Asegurarnos de que el frame de video tenga suficiente espacio
    #     if hasattr(self, 'video'):
    #         # Calcular un buen tamaño para el video
    #         available_width = self.width() // 2  # La mitad del ancho del widget
    #         self.video.setMinimumWidth(available_width)
            
    #         # Altura proporcional (formato 16:9 aproximado)
    #         aspect_ratio = 9/16
    #         suggested_height = int(available_width * aspect_ratio)
    #         self.video.setMinimumHeight(suggested_height)


    def show_detailed_info(self, entry):
        """Muestra información detallada de un elemento en el TextEdit."""
        info_text = "Información detallada:\n\n"
        
        # Campos importantes a mostrar
        fields = [
            ('title', 'Título'),
            ('uploader', 'Subido por'),
            ('upload_date', 'Fecha de subida'),
            ('description', 'Descripción'),
            ('view_count', 'Vistas'),
            ('like_count', 'Me gusta'),
            ('channel', 'Canal'),
            ('album', 'Álbum'),
            ('artist', 'Artista'),
            ('track', 'Pista'),
            ('genre', 'Género')
        ]
        
        for field, label in fields:
            if field in entry and entry[field]:
                # Formatear fecha si es necesario
                if field == 'upload_date' and entry[field]:
                    try:
                        date_str = entry[field]
                        if len(date_str) == 8:  # Formato YYYYMMDD
                            formatted_date = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
                            info_text += f"{label}: {formatted_date}\n"
                        else:
                            info_text += f"{label}: {entry[field]}\n"
                    except:
                        info_text += f"{label}: {entry[field]}\n"
                else:
                    info_text += f"{label}: {entry[field]}\n"
        
        # URL directa
        if 'webpage_url' in entry:
            info_text += f"\nURL: {entry['webpage_url']}\n"
        
        self.textEdit.setText(info_text)
    
    def add_to_queue(self):
        """Añade el elemento seleccionado a la cola de reproducción."""
        selected_items = self.treeWidget.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            # Si es un elemento padre (playlist), añadir todos los hijos
            if item.childCount() > 0:
                for i in range(item.childCount()):
                    child = item.child(i)
                    self.add_item_to_queue(child)
            else:
                self.add_item_to_queue(item)
    
    def add_item_to_queue(self, item):
        """Añade un elemento específico a la cola."""
        title = item.text(0)
        artist = item.text(1)
        url = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not url:
            return
        
        # Crear un nuevo item para la lista de reproducción
        display_text = title
        if artist:
            display_text = f"{artist} - {title}"
            
        queue_item = QListWidgetItem(display_text)
        queue_item.setData(Qt.ItemDataRole.UserRole, url)
        
        # Añadir a la lista
        self.listWidget.addItem(queue_item)
        
        # Actualizar la lista interna de reproducción
        entry_data = item.data(0, Qt.ItemDataRole.UserRole + 1)
        self.current_playlist.append({
            'title': title, 
            'artist': artist, 
            'url': url,
            'entry_data': entry_data
        })
    
    def remove_from_queue(self):
        """Elimina el elemento seleccionado de la cola de reproducción."""
        selected_items = self.listWidget.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            row = self.listWidget.row(item)
            self.listWidget.takeItem(row)
            
            # Actualizar la lista interna
            if 0 <= row < len(self.current_playlist):
                self.current_playlist.pop(row)
    
    def toggle_play_pause(self):
        """Alterna entre reproducir y pausar."""
        if not self.is_playing:
            self.play_media()
            self.playButton.setIcon(QIcon(":/services/b_pause"))
        else:
            self.pause_media()
            self.playButton.setIcon(QIcon(":/services/b_play"))
    
    def play_media(self):
        """Reproduce la cola actual."""
        if not self.current_playlist:
            if self.listWidget.count() == 0:
                # Si no hay nada en la cola, intentar reproducir lo seleccionado en el árbol
                self.add_to_queue()
                if not self.current_playlist:
                    QMessageBox.information(self, "Información", "No hay elementos para reproducir")
                    return
            else:
                # Reconstruir la lista de reproducción desde la lista visual
                self.rebuild_playlist_from_listwidget()
        
        # Si ya está reproduciendo, simplemente enviar comando de pausa/play
        if self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
            self.send_mpv_command({"command": ["cycle", "pause"]})
            self.is_playing = True
            self.playButton.setIcon(QIcon(":/services/b_pause"))
            return
        
        # Si tenemos un índice actual válido, reproducir desde él
        if self.current_track_index >= 0 and self.current_track_index < len(self.current_playlist):
            self.play_from_index(self.current_track_index)
        else:
            # Si no, comenzar desde el principio
            self.play_from_index(0)
    
    
    def pause_media(self):
        """Pausa la reproducción actual."""
        if self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
            success = self.send_mpv_command({"command": ["cycle", "pause"]})
            
            if success:
                self.is_playing = False
                self.playButton.setIcon(QIcon(":/services/b_play"))
                self.log("Reproducción pausada")
            else:
                self.log("Error al pausar la reproducción")
    
    def stop_playback(self):
        """Detiene cualquier reproducción en curso."""
        if self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
            self.log("Deteniendo reproducción actual...")
            
            # Intentar terminar gracefully primero
            try:
                self.send_mpv_command({"command": ["quit"]})
                
                # Esperar un poco para que mpv se cierre por sí mismo
                if not self.player_process.waitForFinished(1000):
                    self.player_process.terminate()
                    
                    if not self.player_process.waitForFinished(1000):
                        self.player_process.kill()
                        self.log("Forzando cierre del reproductor")
            except Exception as e:
                self.log(f"Error al detener reproducción: {str(e)}")
                # Forzar terminación en caso de error
                self.player_process.kill()
            
            self.is_playing = False
            self.playButton.setIcon(QIcon(":/services/b_play"))
            self.log("Reproducción detenida")
    
    def pause_media(self):
        """Pausa la reproducción actual."""
        if self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
            success = self.send_mpv_command({"command": ["cycle", "pause"]})
            
            if success:
                self.is_playing = False
                #self.playButton.setText("▶️")
                self.playButton.setIcon(QIcon(":/services/b_play"))

                self.log("Reproducción pausada")
            else:
                self.log("Error al pausar la reproducción")
    
    def handle_player_output(self):
        """Maneja la salida estándar del reproductor."""
        if self.player_process:
            output = self.player_process.readAllStandardOutput().data().decode('utf-8')
            if output.strip():
                self.log(f"MPV: {output.strip()}")
    
    def handle_player_error(self):
        """Maneja la salida de error del reproductor."""
        if self.player_process:
            error = self.player_process.readAllStandardError().data().decode('utf-8')
            if error.strip():
                self.log(f"MPV Error: {error.strip()}")
    
    def handle_player_finished(self, exit_code, exit_status):
        """Maneja el evento de finalización del reproductor."""
        self.is_playing = False
        self.playButton.setIcon(QIcon(":/services/b_play"))
        
        exit_msg = "finalizada normalmente" if exit_code == 0 else f"finalizada con error (código {exit_code})"
        self.log(f"Reproducción {exit_msg}")
        
        # Cerrar recursos asociados
        if self.mpv_socket and os.path.exists(self.mpv_socket):
            try:
                os.remove(self.mpv_socket)
            except:
                pass
        
        # Solo avanzar automáticamente si el reproductor terminó normalmente (exit_code == 0)
        # y no por una acción del usuario (exit_code != 0 típicamente)
        if exit_code == 0 and self.current_playlist and self.current_track_index >= 0:
            # Verificar si es el último elemento de la lista
            if self.current_track_index < len(self.current_playlist) - 1:
                # Si no es el último, pasar a la siguiente pista
                self.next_track()
            else:
                # Si es el último, no continuar reproduciendo
                self.log("Fin de la lista de reproducción")


    def send_mpv_command(self, command):
        """Envía un comando a mpv a través del socket IPC."""
        if not self.mpv_socket or not os.path.exists(self.mpv_socket):
            self.log(f"No se puede enviar comando: socket no disponible")
            return False
        
        try:
            import socket
            import json
            
            self.log(f"Enviando comando: {json.dumps(command)}")
            
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.mpv_socket)
            
            command_str = json.dumps(command) + "\n"
            sock.send(command_str.encode())
            sock.close()
            
            return True
        except Exception as e:
            self.log(f"Error enviando comando a mpv: {str(e)}")
            return False
    
    def previous_track(self):
        """Reproduce la pista anterior."""
        if not self.current_playlist:
            return
        
        prev_index = self.current_track_index - 1
        if prev_index < 0:
            prev_index = len(self.current_playlist) - 1  # Ir al final si estamos al principio
        
        self.log(f"Cambiando a la pista anterior (índice {prev_index})")
        self.play_from_index(prev_index)


    def next_track(self):
        """Reproduce la siguiente pista."""
        if not self.current_playlist:
            return
        
        next_index = self.current_track_index + 1
        if next_index >= len(self.current_playlist):
            next_index = 0  # Volver al principio si estamos al final
        
        self.log(f"Cambiando a la siguiente pista (índice {next_index})")
        self.play_from_index(next_index)
    
    def rebuild_playlist_from_listwidget(self):
        """Reconstruye la lista de reproducción desde el ListWidget."""
        self.current_playlist = []
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            title = item.text()
            url = item.data(Qt.ItemDataRole.UserRole)
            
            # Extraer artista si está presente en el formato "Artista - Título"
            artist = ""
            if " - " in title:
                parts = title.split(" - ", 1)
                artist = parts[0]
                title = parts[1]
                
            self.current_playlist.append({
                'title': title, 
                'artist': artist, 
                'url': url,
                'entry_data': None  # No tenemos los datos completos en este caso
            })
            
        self.log(f"Lista de reproducción reconstruida con {len(self.current_playlist)} elementos")  

    def check_dependencies(self):
        """Verifica que las dependencias necesarias estén instaladas."""
        dependencies = ['mpv', 'yt-dlp']
        missing = []
        
        for dep in dependencies:
            try:
                result = subprocess.run(['which', dep], capture_output=True, text=True)
                if result.returncode != 0:
                    missing.append(dep)
            except Exception:
                missing.append(dep)
        
        if missing:
            missing_deps = ', '.join(missing)
            error_msg = f"Faltan dependencias necesarias: {missing_deps}"
            self.log(error_msg)
            QMessageBox.critical(self, "Error de dependencias", 
                                f"Faltan dependencias necesarias para ejecutar este módulo: {missing_deps}\n\n"
                                f"Por favor, instálalas con tu gestor de paquetes.")
            return False
        
        return True


    def load_api_credentials(self):
        """Carga credenciales de API desde la configuración o variables de entorno"""
        # Intentar cargar desde variables de entorno
        spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        lastfm_api_key = os.environ.get("LASTFM_API_KEY")
        
        # Si no están disponibles, intentar cargar desde la configuración
        if not spotify_client_id or not spotify_client_secret or not lastfm_api_key:
            try:
                config_path = os.path.join(PROJECT_ROOT, "config", "api_keys.json")
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        
                        # Establecer credenciales como variables de entorno
                        if 'spotify' in config:
                            os.environ["SPOTIFY_CLIENT_ID"] = config['spotify'].get('client_id', '')
                            os.environ["SPOTIFY_CLIENT_SECRET"] = config['spotify'].get('client_secret', '')
                        
                        if 'lastfm' in config:
                            os.environ["LASTFM_API_KEY"] = config['lastfm'].get('api_key', '')
                            os.environ["LASTFM_USER"] = config['lastfm'].get('user', '')
            except Exception as e:
                self.log(f"Error al cargar credenciales de API: {str(e)}")
        
        # Verificar si se cargaron las credenciales
        self.spotify_enabled = bool(os.environ.get("SPOTIFY_CLIENT_ID") and os.environ.get("SPOTIFY_CLIENT_SECRET"))
        self.lastfm_enabled = bool(os.environ.get("LASTFM_API_KEY"))
        
        # Actualizar la configuración de servicios
        if not self.spotify_enabled and 'spotify' in self.included_services:
            self.included_services['spotify'] = False
            self.log("Spotify deshabilitado por falta de credenciales de API")
        
        if not self.lastfm_enabled and 'lastfm' in self.included_services:
            self.included_services['lastfm'] = False
            self.log("Last.fm deshabilitado por falta de credenciales de API")


    def keyPressEvent(self, event):
        """Maneja eventos de teclado para todo el widget."""
        # Comprobar si es Ctrl+C
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Verificar si estamos enfocados en el TreeWidget y hay un ítem seleccionado
            if self.treeWidget.hasFocus() and self.treeWidget.currentItem():
                self.copy_url_to_clipboard()
                event.accept()
                return
        
        # Pasar el evento al padre para su procesamiento normal
        super().keyPressEvent(event)

    def copy_url_to_clipboard(self):
        """Copia la URL del elemento seleccionado al portapapeles."""
        current_item = self.treeWidget.currentItem()
        if not current_item:
            return
        
        # Obtener datos asociados al ítem
        item_data = current_item.data(0, Qt.ItemDataRole.UserRole)
        
        url = None
        if isinstance(item_data, dict) and 'url' in item_data:
            url = item_data['url']
        elif current_item.toolTip(0) and current_item.toolTip(0).startswith("URL: "):
            url = current_item.toolTip(0)[5:]  # Extraer URL del tooltip
        
        if url:
            # Copiar al portapapeles
            clipboard = QApplication.clipboard()
            clipboard.setText(url)
            
            # Mostrar mensaje de confirmación
            self.log(f"URL copiada al portapapeles: {url}")
            QMessageBox.information(self, "URL Copiada", "La URL ha sido copiada al portapapeles")


    def open_url_in_browser(self, url):
        """Abre la URL en el navegador predeterminado."""
        try:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            
            QDesktopServices.openUrl(QUrl(url))
            self.log(f"Abriendo URL en navegador: {url}")
        except Exception as e:
            self.log(f"Error al abrir URL en navegador: {str(e)}")
            QMessageBox.warning(self, "Error", f"No se pudo abrir la URL: {str(e)}")




    def get_detailed_info(self, item_type, title, artist):
        """Obtiene información detallada desde la base de datos"""
        try:
            # Importar la clase de consulta si es necesario
            from base_datos.tools.consultar_items_db import MusicDatabaseQuery
            
            # Usar la ruta de base de datos configurada
            db_path = self.db_path
            
            if not os.path.exists(db_path):
                self.log(f"Base de datos no encontrada en: {db_path}")
                return None
            
            db = MusicDatabaseQuery(db_path)
            
            if item_type == 'artist':
                # Obtener información completa del artista
                return db.get_artist_info(artist)
            elif item_type == 'album':
                # Obtener información completa del álbum
                return db.get_album_info(title, artist)
            elif item_type in ['track', 'song']:
                # Obtener información completa de la canción
                return db.get_song_info(title, artist)
            
            db.close()
            return None
        except Exception as e:
            self.log(f"Error al obtener información detallada: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return None

    def format_artist_info(self, artist_info):
        """Formatea la información del artista en HTML"""
        html = ""
        
        # Biografía
        if artist_info.get('bio'):
            html += "<h3>Biografía</h3>"
            html += f"<p>{artist_info['bio']}</p>"
        
        # Origen y año de formación
        if artist_info.get('origin') or artist_info.get('formed_year'):
            html += "<h3>Información General</h3>"
            if artist_info.get('origin'):
                html += f"<p><b>Origen:</b> {artist_info['origin']}</p>"
            if artist_info.get('formed_year'):
                html += f"<p><b>Año de formación:</b> {artist_info['formed_year']}</p>"
        
        # Géneros
        if artist_info.get('tags'):
            html += "<h3>Géneros</h3>"
            tags = artist_info['tags'].split(',') if isinstance(artist_info['tags'], str) else artist_info['tags']
            html += "<ul>"
            for tag in tags:
                html += f"<li>{tag}</li>"
            html += "</ul>"
        
        # Artistas similares
        if artist_info.get('similar_artists'):
            html += "<h3>Artistas Similares</h3>"
            similar = artist_info['similar_artists'].split(',') if isinstance(artist_info['similar_artists'], str) else artist_info['similar_artists']
            html += "<ul>"
            for artist in similar:
                html += f"<li>{artist}</li>"
            html += "</ul>"
        
        # Álbumes
        if artist_info.get('albums'):
            html += f"<h3>Álbumes ({len(artist_info['albums'])})</h3>"
            html += "<ul>"
            for album in artist_info['albums']:
                year = f" ({album.get('year', '')})" if album.get('year') else ""
                html += f"<li><b>{album.get('name', '')}</b>{year}</li>"
            html += "</ul>"
        
        return html

    def format_album_info(self, album_info):
        """Formatea la información del álbum en HTML"""
        html = ""
        
        # Año y género
        if album_info.get('year') or album_info.get('genre'):
            html += "<h3>Información General</h3>"
            if album_info.get('year'):
                html += f"<p><b>Año:</b> {album_info['year']}</p>"
            if album_info.get('genre'):
                html += f"<p><b>Género:</b> {album_info['genre']}</p>"
            if album_info.get('label'):
                html += f"<p><b>Sello:</b> {album_info['label']}</p>"
        
        # Créditos si existen
        if album_info.get('producers') or album_info.get('engineers') or album_info.get('mastering_engineers'):
            html += "<h3>Créditos</h3>"
            if album_info.get('producers'):
                html += f"<p><b>Productores:</b> {album_info['producers']}</p>"
            if album_info.get('engineers'):
                html += f"<p><b>Ingenieros:</b> {album_info['engineers']}</p>"
            if album_info.get('mastering_engineers'):
                html += f"<p><b>Masterización:</b> {album_info['mastering_engineers']}</p>"
        
        # Canciones
        if album_info.get('songs'):
            html += f"<h3>Canciones ({len(album_info['songs'])})</h3>"
            html += "<ol>"
            for song in album_info['songs']:
                duration = ""
                if song.get('duration'):
                    # Formatear duración (si está en segundos)
                    duration_seconds = song['duration']
                    if isinstance(duration_seconds, (int, float)):
                        minutes = int(duration_seconds // 60)
                        seconds = int(duration_seconds % 60)
                        duration = f" ({minutes}:{seconds:02d})"
                html += f"<li>{song.get('title', '')}{duration}</li>"
            html += "</ol>"
        
        # Wikipedia
        if album_info.get('wikipedia_content'):
            html += "<h3>Wikipedia</h3>"
            wiki_preview = album_info['wikipedia_content'][:500] + "..." if len(album_info['wikipedia_content']) > 500 else album_info['wikipedia_content']
            html += f"<p>{wiki_preview}</p>"
        
        return html

    def format_song_info(self, song_info):
        """Formatea la información de la canción en HTML"""
        html = ""
        
        # Información general
        html += "<h3>Información General</h3>"
        if song_info.get('track_number'):
            html += f"<p><b>Número de pista:</b> {song_info['track_number']}</p>"
        if song_info.get('album'):
            html += f"<p><b>Álbum:</b> {song_info['album']}</p>"
        if song_info.get('duration'):
            # Formatear duración (si está en segundos)
            duration_seconds = song_info['duration']
            if isinstance(duration_seconds, (int, float)):
                minutes = int(duration_seconds // 60)
                seconds = int(duration_seconds % 60)
                html += f"<p><b>Duración:</b> {minutes}:{seconds:02d}</p>"
        
        # Letra
        if song_info.get('lyrics'):
            html += "<h3>Letra</h3>"
            # Formatear la letra reemplazando saltos de línea por <br>
            lyrics = song_info['lyrics'].replace('\n', '<br>')
            html += f"<p>{lyrics}</p>"
        
        # Información del álbum correspondiente (extracto)
        if song_info.get('album_links') or song_info.get('album_info'):
            html += "<h3>Información del Álbum</h3>"
            if song_info.get('album_links'):
                html += "<p>Enlaces disponibles para el álbum.</p>"
            
        return html

    def format_available_links(self, result_data):
        """Formatea los enlaces disponibles en HTML"""
        html = "<h3>Enlaces</h3>"
        
        # Enlaces directos en result_data
        if result_data.get('url'):
            service = result_data.get('source', 'Desconocido')
            html += f"<p><b>{service.capitalize()}:</b> <a href='{result_data['url']}'>{result_data['url']}</a></p>"
        
        # Enlaces de servicios específicos
        services = ['spotify', 'youtube', 'bandcamp', 'soundcloud', 'lastfm', 'musicbrainz', 'discogs', 'rateyourmusic']
        
        for service in services:
            url_key = f"{service}_url"
            if result_data.get(url_key):
                html += f"<p><b>{service.capitalize()}:</b> <a href='{result_data[url_key]}'>{result_data[url_key]}</a></p>"
        
        return html

    def display_wiki_info(self, result_data):
        """Muestra información detallada del elemento en el panel info_wiki"""
        try:
            # Verificar que el textEdit existe
            if not hasattr(self, 'info_wiki_textedit') or not self.info_wiki_textedit:
                self.log("Error: No se encontró el widget info_wiki_textedit")
                return
            
            # Limpiar contenido anterior
            self.info_wiki_textedit.clear()
            
            # Tipo de elemento (artista, álbum, canción)
            item_type = result_data.get('type', '').lower()
            title = result_data.get('title', '')
            artist = result_data.get('artist', '')
            
            if not title and not artist:
                self.info_wiki_textedit.setText("No hay suficiente información para mostrar detalles")
                return
            
            # Encabezado con información básica
            html_content = f"<h2>{title}</h2>"
            if artist:
                html_content += f"<h3>por {artist}</h3>"
            
            html_content += f"<p><b>Tipo:</b> {item_type.capitalize()}</p>"
            html_content += "<hr>"
            
            # Intentar obtener información adicional desde la base de datos
            additional_info = self.get_detailed_info(item_type, title, artist)
            
            if additional_info:
                # Agregar información dependiendo del tipo
                if item_type == 'artist':
                    html_content += self.format_artist_info(additional_info)
                elif item_type == 'album':
                    html_content += self.format_album_info(additional_info)
                elif item_type in ['track', 'song']:
                    html_content += self.format_song_info(additional_info)
                else:
                    html_content += f"<p>Información disponible para: {', '.join(additional_info.keys())}</p>"
                    
                    # Mostrar cualquier dato disponible
                    for key, value in additional_info.items():
                        if key not in ['links', 'album_links', 'artist_links']:
                            html_content += f"<h4>{key.replace('_', ' ').title()}</h4>"
                            if isinstance(value, str):
                                html_content += f"<p>{value}</p>"
                            elif isinstance(value, dict):
                                html_content += "<ul>"
                                for k, v in value.items():
                                    html_content += f"<li><b>{k}:</b> {v}</li>"
                                html_content += "</ul>"
                            elif isinstance(value, list):
                                html_content += "<ul>"
                                for item in value:
                                    html_content += f"<li>{item}</li>"
                                html_content += "</ul>"
            else:
                html_content += "<p>No se encontró información adicional en la base de datos.</p>"
            
            # Enlaces disponibles
            html_content += self.format_available_links(result_data)
            
            # Establecer el contenido HTML
            self.info_wiki_textedit.setHtml(html_content)
            
            # Cambiar al tab de info_wiki para mostrar la información
            if hasattr(self, 'tabWidget') and self.tabWidget:
                # Buscar el índice del tab info_wiki
                for i in range(self.tabWidget.count()):
                    if self.tabWidget.tabText(i) == "Info Wiki":
                        self.tabWidget.setCurrentIndex(i)
                        break
            
        except Exception as e:
            self.log(f"Error al mostrar información detallada: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

def run_direct_command(self, cmd, args=None):
    """Ejecuta un comando directo y devuelve su salida."""
    if args is None:
        args = []
        
    try:
        result = subprocess.run([cmd] + args, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", f"Error: {str(e)}", -1

def closeEvent(self, event):
    """Limpia recursos al cerrar."""
    self.log("Cerrando módulo y liberando recursos...")
    
    # Cancelar búsquedas en curso
    QThreadPool.globalInstance().clear()  # Limpia cualquier trabajo pendiente
    
    # Detener reproducción si está activa
    self.stop_playback()
    
    # Matar procesos pendientes
    if hasattr(self, 'yt_dlp_process') and self.yt_dlp_process and self.yt_dlp_process.state() == QProcess.ProcessState.Running:
        self.yt_dlp_process.terminate()
        if not self.yt_dlp_process.waitForFinished(1000):
            self.yt_dlp_process.kill()
    
    if hasattr(self, 'player_process') and self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
        # Intentar terminar gracefully primero
        self.send_mpv_command({"command": ["quit"]})
        
        # Esperar un poco y forzar si es necesario
        if not self.player_process.waitForFinished(1000):
            self.player_process.terminate()
            
            if not self.player_process.waitForFinished(1000):
                self.player_process.kill()
    
    # Eliminar sockets
    if hasattr(self, 'mpv_socket') and self.mpv_socket and os.path.exists(self.mpv_socket):
        try:
            os.remove(self.mpv_socket)
            self.log(f"Socket eliminado: {self.mpv_socket}")
        except Exception as e:
            self.log(f"Error al eliminar socket: {str(e)}")
    
    # Eliminar directorio temporal
    if hasattr(self, 'mpv_temp_dir') and self.mpv_temp_dir and os.path.exists(self.mpv_temp_dir) and self.mpv_temp_dir != "/tmp":
        try:
            import shutil
            shutil.rmtree(self.mpv_temp_dir)
            self.log(f"Directorio temporal eliminado: {self.mpv_temp_dir}")
        except Exception as e:
            self.log(f"Error al eliminar directorio temporal: {str(e)}")
    
    # Guardar configuración antes de cerrar
    self.save_settings()
    
    # Proceder con el cierre
    super().closeEvent(event)