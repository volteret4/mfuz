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
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QTextEdit, QTabWidget, QMessageBox,
    QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal, QUrl
from PyQt6.QtGui import QIcon
from base_module import BaseModule, PROJECT_ROOT


class UrlPlayer(BaseModule):
    """Módulo para reproducir música desde URLs (YouTube, SoundCloud, Bandcamp)."""
    
    def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
        # Primero extraemos y configuramos los argumentos específicos antes de llamar al constructor padre
        self.mpv_temp_dir = kwargs.pop('mpv_temp_dir', None)
        
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
            "delButton", "addButton", "textEdit"
        ])
        
        if not ui_file_loaded:
            self._fallback_init_ui()
        
        # Verificar que tenemos todos los widgets necesarios
        if not self.check_required_widgets():
            print("[UrlPlayer] Error: No se pudieron inicializar todos los widgets requeridos")
            return
        
        # Configurar nombres y tooltips
        self.searchButton.setText("Buscar")
        self.searchButton.setToolTip("Buscar información sobre la URL")
        self.playButton.setText("▶️")
        self.playButton.setToolTip("Reproducir/Pausar")
        self.rewButton.setText("⏮️")
        self.rewButton.setToolTip("Anterior")
        self.ffButton.setText("⏭️")
        self.ffButton.setToolTip("Siguiente")
        self.delButton.setText("➖")
        self.delButton.setToolTip("Eliminar de la cola")
        self.addButton.setText("➕")
        self.addButton.setToolTip("Añadir a la cola")
        
        # Configurar TreeWidget
        self.treeWidget.setHeaderLabels(["Título", "Artista", "Tipo", "Duración"])
        self.treeWidget.setColumnWidth(0, 250)
        self.treeWidget.setColumnWidth(1, 150)
        self.treeWidget.setColumnWidth(2, 80)
        
        # Configurar TabWidget
        self.tabWidget.setTabText(0, "Cola de reproducción")
        self.tabWidget.setTabText(1, "Información")
        
        # Conectar señales
        self.connect_signals()


    def connect_signals(self):
        """Conecta las señales de los widgets a sus respectivos slots."""
        try:
            # Conectar señales con verificación previa
            if self.searchButton:
                self.searchButton.clicked.connect(self.perform_search)
                self.lineEdit.returnPressed.connect(self.perform_search)
            
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
                self.lineEdit.returnPressed.connect(self.search_url)
            
            # Conectar eventos de doble clic
            if self.treeWidget:
                self.treeWidget.itemDoubleClicked.connect(self.on_tree_double_click)
                self.on_tree_double_click_original = self.on_tree_double_click
                self.treeWidget.itemDoubleClicked.disconnect(self.on_tree_double_click)
                self.treeWidget.itemDoubleClicked.connect(self.on_tree_double_click)

            if self.listWidget:
                self.listWidget.itemDoubleClicked.connect(self.on_list_double_click)
            
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
            "addButton", "delButton", "textEdit"
        ]
        
        all_ok = True
        for widget_name in required_widgets:
            if not hasattr(self, widget_name) or getattr(self, widget_name) is None:
                print(f"[UrlPlayer] Error: Widget {widget_name} no encontrado")
                all_ok = False
        
        return all_ok


    def on_tree_double_click(self, item, column):
        """Handle double click on tree item to add to queue or play immediately"""
        # If it's a root item (source) with children, just expand/collapse
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return
            
        # Get the stored result data
        result_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # If this is a search result
        if isinstance(result_data, dict):
            url = result_data.get('url', '')
            if url:
                # Create a display text
                display_text = f"{result_data['artist']} - {result_data['title']}"
                
                # Add to queue
                self.add_to_queue_from_url(url, display_text, result_data)
                self.log(f"Added to queue: {display_text}")
        else:
            # Handle the existing logic for non-search results
            self.on_tree_double_click_original(item, column)

    def add_to_queue_from_url(self, url, display_text, metadata=None):
        """Add an item to the queue based on URL and display text"""
        # Create a new item for the playlist
        queue_item = QListWidgetItem(display_text)
        queue_item.setData(Qt.ItemDataRole.UserRole, url)
        
        # Add to the list
        self.listWidget.addItem(queue_item)
        
        # Update the internal playlist
        self.current_playlist.append({
            'title': metadata.get('title', display_text),
            'artist': metadata.get('artist', ''),
            'url': url,
            'entry_data': metadata
        })
    
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
            return
                
        # Detener reproducción actual si existe
        self.stop_playback()
                
        # Obtener todas las URLs a partir del índice seleccionado
        urls = [item['url'] for item in self.current_playlist[index:]]
        
        # Reproducir la lista comenzando por el elemento seleccionado
        self.play_with_mpv(urls)

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
            
            # Añadir URLs
            mpv_args.extend(urls)
            
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
                    self.playButton.setText("⏸️")
                    self.log("Reproducción iniciada correctamente")
                else:
                    self.log("Error al iniciar MPV: timeout")
                    error = self.player_process.errorString()
                    self.log(f"Error detallado: {error}")
                        
            except Exception as e:
                self.log(f"Excepción al iniciar MPV: {str(e)}")



    def perform_search(self):
        """Perform a search based on the selected platform and query"""
        query = self.lineEdit.text().strip()
        if not query:
            return
        
        self.log(f"Searching for: {query}")
        
        # Clear previous results
        self.treeWidget.clear()
        self.textEdit.clear()
        
        # Get the selected source
        source = self.source_combo.currentText()
        
        # Show progress
        self.textEdit.append(f"Searching for '{query}' on {source}...")
        QApplication.processEvents()
        
        results = []
        
        # Perform search based on selected source
        if source == "All" or source == "YouTube":
            youtube_results = self.search_youtube(query)
            results.extend(youtube_results)
        
        if source == "All" or source == "Bandcamp":
            bandcamp_results = self.search_bandcamp(query)
            results.extend(bandcamp_results)
        
        if source == "All" or source == "SoundCloud":
            soundcloud_results = self.search_soundcloud(query)
            results.extend(soundcloud_results)
        
        # Display results
        self.display_search_results(results)
        
        self.log(f"Search complete. Found {len(results)} results.")


    def search_bandcamp(self, query):
        """Search for music on Bandcamp and get information for embed"""
        try:
            # Format search URL
            search_url = f"https://bandcamp.com/search?q={query.replace(' ', '+')}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://bandcamp.com/",
                "Connection": "keep-alive",
            }
            
            self.log(f"Searching on Bandcamp: {search_url}")
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                self.log(f"Error searching Bandcamp: Status code {response.status_code}")
                return []
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Search for album and track results
            result_selectors = [
                'div.result-info a.item-title',
                'div.result-info a.search-result-title'
            ]
            
            bandcamp_results = []
            for selector in result_selectors:
                track_elements = soup.select(selector)
                if track_elements:
                    for element in track_elements[:5]:  # Limit to 5 results
                        try:
                            track_url = element.get('href', '')
                            track_name = element.get_text().strip()
                            
                            # Try to get artist information
                            artist_element = element.find_parent('div', class_='result-info').find('div', class_='result-info-inner').find('a', class_='search-result-artist')
                            artist_name = artist_element.get_text().strip() if artist_element else "Unknown Artist"
                            
                            bandcamp_results.append({
                                "source": "bandcamp",
                                "title": track_name,
                                "artist": artist_name,
                                "url": track_url,
                                "type": "track" if "/track/" in track_url else "album"
                            })
                            
                            self.log(f"Found on Bandcamp: {track_name} - URL: {track_url}")
                        except Exception as e:
                            self.log(f"Error processing Bandcamp result: {e}")
                    
                    break  # Exit after finding results
            
            return bandcamp_results
        
        except Exception as e:
            self.log(f"Error searching on Bandcamp: {e}")
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
        """Search for music on YouTube"""
        try:
            # Use yt-dlp for searching
            command = ["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearch5:{query}"]
            self.log(f"Searching YouTube with: {' '.join(command)}")
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Error searching YouTube: {stderr}")
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
                    self.log(f"Found on YouTube: {title} - URL: {url}")
                except json.JSONDecodeError:
                    self.log(f"Error parsing YouTube result: {line}")
                except Exception as e:
                    self.log(f"Error processing YouTube result: {e}")
            
            return results
        except Exception as e:
            self.log(f"Error searching on YouTube: {e}")
            import traceback
            self.log(traceback.format_exc())
            return []



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
        """Display search results in the treeWidget"""
        self.treeWidget.clear()
        
        if not results:
            self.textEdit.append("No results found.")
            return
        
        # Group results by source
        sources = {}
        for result in results:
            source = result.get('source', 'Unknown')
            if source not in sources:
                sources[source] = []
            sources[source].append(result)
        
        # Add results to tree
        for source, source_results in sources.items():
            # Create a source header
            source_item = QTreeWidgetItem(self.treeWidget)
            source_item.setText(0, f"{source.capitalize()} Results")
            source_item.setExpanded(True)
            source_item.is_header = True
            
            # Use a custom font for headers
            font = source_item.font(0)
            font.setBold(True)
            source_item.setFont(0, font)
            
            # Add results for this source
            for result in source_results:
                result_item = QTreeWidgetItem(source_item)
                result_item.setText(0, result['title'])
                result_item.setText(1, result['artist'])
                result_item.setText(2, result.get('type', ''))
                
                # Store the full result data for later use
                result_item.setData(0, Qt.ItemDataRole.UserRole, result)
                result_item.is_header = False
        
        self.textEdit.append(f"Found {len(results)} results.")
        
        # Make sure the tree is visible
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
        elif 'soundcloud.com' in url:
            return "SoundCloud"
        elif 'bandcamp.com' in url:
            return "Bandcamp"
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
        else:
            self.pause_media()
    
    def play_media(self):
        """Reproduce la cola actual con mpv en ventana independiente."""
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
            self.playButton.setText("⏸️")
            return
        
        # Crear lista de URLs para mpv
        urls = [item['url'] for item in self.current_playlist]
        
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
        
        # Preparar argumentos para mpv (sin incrustar)
        mpv_args = [
            "--input-ipc-server=" + socket_path,  # Socket para controlar mpv
            "--ytdl=yes",                # Usar youtube-dl/yt-dlp para streaming
            "--ytdl-format=best",        # Mejor calidad disponible
            "--keep-open=yes",           # Mantener abierto al finalizar
        ]
        
        # Añadir URLs
        mpv_args.extend(urls)
        
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
                self.playButton.setText("⏸️")
                self.log("Reproducción iniciada correctamente")
            else:
                self.log("Error al iniciar MPV: timeout")
                error = self.player_process.errorString()
                self.log(f"Error detallado: {error}")
                    
        except Exception as e:
            self.log(f"Excepción al iniciar MPV: {str(e)}")
    
    # def _start_mpv_playback(self, urls):
    #     """Inicia la reproducción con MPV."""
    #     # Detener cualquier reproducción anterior
    #     self.stop_playback()
        
    #     # Registrar información para depuración
    #     self.log(f"Intentando reproducir {len(urls)} URL(s)")
    #     self.log(f"Primera URL: {urls[0]}")
        
    #     # Obtener el ID de ventana (WID) del frame de video
    #     try:
    #         self.mpv_wid = str(int(self.video.winId()))
    #         self.log(f"WID obtenido: {self.mpv_wid}")
    #     except Exception as e:
    #         self.log(f"Error al obtener WID: {str(e)}")
    #         self.mpv_wid = None
        
    #     # Verificar o crear directorio temporal
    #     if not self.mpv_temp_dir or not os.path.exists(self.mpv_temp_dir):
    #         try:
    #             self.mpv_temp_dir = tempfile.mkdtemp(prefix="mpv_socket_")
    #             self.log(f"Directorio temporal creado o recreado: {self.mpv_temp_dir}")
    #         except Exception as e:
    #             self.log(f"Error al crear directorio temporal: {str(e)}")
    #             # Fallback: usar /tmp directo
    #             self.mpv_temp_dir = "/tmp"
        
    #     # Crear ruta para el socket
    #     socket_path = os.path.join(self.mpv_temp_dir, "mpv_socket")
    #     self.mpv_socket = socket_path
        
    #     # Si existe un socket anterior, eliminarlo
    #     if os.path.exists(socket_path):
    #         try:
    #             os.remove(socket_path)
    #             self.log(f"Socket antiguo eliminado: {socket_path}")
    #         except Exception as e:
    #             self.log(f"Error al eliminar socket antiguo: {str(e)}")
        
    #     # Preparar argumentos para mpv
    #     mpv_args = [
    #         "--no-terminal",             # No mostrar en terminal
    #         "--msg-level=all=v",         # Nivel detallado para depuración
    #         "--keep-open=yes",           # Mantener abierto al finalizar
    #         "--force-window=yes",        # Forzar ventana siempre
    #         "--input-ipc-server=" + socket_path,  # Socket para controlar mpv
    #         "--ytdl=yes",                # Usar youtube-dl/yt-dlp para streaming
    #         "--ytdl-format=best",        # Mejor calidad disponible
    #     ]
        
    #     # Añadir el argumento wid solo si está disponible
    #     if self.mpv_wid:
    #         mpv_args.append("--wid=" + self.mpv_wid)
    #         # Añadir configuraciones específicas para video embebido
    #         mpv_args.extend([
    #             "--no-border",                # Sin bordes
    #             "--video-aspect-override=no", # No cambiar relación de aspecto
    #             "--no-window-decorations",    # Sin decoraciones de ventana
    #             "--hwdec=auto",              # Aceleración de hardware
    #             "--video-sync=display-resample", # Mejor sincronización
    #             "--reset-on-next-file=all",   # Resetear para cada archivo
    #         ])
        
    #     # Configuración de salida de audio/video
    #     mpv_args.extend([
    #         "--no-osc",                  # Sin controles en pantalla
    #         "--osd-level=0",             # Sin OSD
    #     ])
        
    #     # Añadir URLs
    #     mpv_args.extend(urls)
        
    #     # Registrar comando completo para depuración
    #     self.log(f"Comando MPV: mpv {' '.join(mpv_args)}")
        
    #     # Iniciar mpv para reproducir
    #     self.player_process = QProcess()
    #     self.player_process.readyReadStandardOutput.connect(self.handle_player_output)
    #     self.player_process.readyReadStandardError.connect(self.handle_player_error)
    #     self.player_process.finished.connect(self.handle_player_finished)
        
    #     try:
    #         self.player_process.start("mpv", mpv_args)
    #         success = self.player_process.waitForStarted(3000)  # Esperar 3 segundos máximo
            
    #         if success:
    #             self.is_playing = True
    #             self.pushButton.setText("⏸️")
    #             self.log("Reproducción iniciada correctamente")
                
    #             # Asegurarnos de que el video sea visible
    #             self.video.update()
    #         else:
    #             self.log("Error al iniciar MPV: timeout")
    #             error = self.player_process.errorString()
    #             self.log(f"Error detallado: {error}")
                    
    #     except Exception as e:
    #         self.log(f"Excepción al iniciar MPV: {str(e)}")
    
    def stop_playback(self):
        """Detiene cualquier reproducción en curso."""
        if self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
            self.log("Deteniendo reproducción actual...")
            
            # Intentar terminar gracefully primero
            self.send_mpv_command({"command": ["quit"]})
            
            # Esperar un poco y forzar si es necesario
            if not self.player_process.waitForFinished(1000):
                self.player_process.terminate()
                
                if not self.player_process.waitForFinished(1000):
                    self.player_process.kill()
            
            self.is_playing = False
            self.playButton.setText("▶️")
    
    def pause_media(self):
        """Pausa la reproducción actual."""
        if self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
            success = self.send_mpv_command({"command": ["cycle", "pause"]})
            
            if success:
                self.is_playing = False
                self.playButton.setText("▶️")
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
        self.playButton.setText("▶️")
        self.log(f"Reproducción finalizada (código {exit_code})")
        
        # Cerrar recursos asociados
        if self.mpv_socket and os.path.exists(self.mpv_socket):
            try:
                os.remove(self.mpv_socket)
            except:
                pass
    
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
        if self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
            success = self.send_mpv_command({"command": ["playlist-prev"]})
            if success:
                self.log("Pista anterior")
    
    def next_track(self):
        """Reproduce la siguiente pista."""
        if self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
            success = self.send_mpv_command({"command": ["playlist-next"]})
            if success:
                self.log("Siguiente pista")
    
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
    
    # Detener reproducción si está activa
    self.stop_playback()
    
    # Matar procesos pendientes
    if self.yt_dlp_process and self.yt_dlp_process.state() == QProcess.ProcessState.Running:
        self.yt_dlp_process.terminate()
        self.yt_dlp_process.waitForFinished(1000)
    
    # Eliminar directorio temporal
    if self.mpv_temp_dir and os.path.exists(self.mpv_temp_dir) and self.mpv_temp_dir != "/tmp":
        try:
            import shutil
            shutil.rmtree(self.mpv_temp_dir)
            self.log(f"Directorio temporal eliminado: {self.mpv_temp_dir}")
        except Exception as e:
            self.log(f"Error al eliminar directorio temporal: {str(e)}")
    
    # Proceder con el cierre
    super().closeEvent(event)