import os
import sys
import json
import re
import requests
import subprocess
import traceback
import urllib.parse
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from PyQt6.QtCore import Qt, QObject, QRunnable, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication
from pathlib import Path

from modules.submodules.url_playlist.ui_helpers import display_wiki_info
# Asegurarse de que PROJECT_ROOT está disponible
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from base_module import PROJECT_ROOT
except ImportError:
    import os
    PROJECT_ROOT = os.path.abspath(Path(os.path.dirname(__file__), "..", ".."))

# Clases para los trabajadores de búsqueda
class InfoLoadWorker(QRunnable):
    """Worker thread for loading detailed information asynchronously."""
    
    class Signals(QObject):
        """Signal class for the worker."""
        finished = pyqtSignal(dict, dict)  # Pass result and basic_data
        results = pyqtSignal(list)
        error = pyqtSignal(str)
    
    def __init__(self, item_type, title, artist, album=None, db_path=None, basic_data=None):
        super().__init__()
        self.item_type = item_type
        self.title = title
        self.artist = artist
        self.album = album
        self.db_path = db_path
        self.basic_data = basic_data  # Store the basic data
        self.signals = self.Signals()
    
    def log(self, message):
        """Método seguro para registrar mensajes en el TextEdit y en la consola."""
        # Siempre imprimir en la consola
        print(f"[UrlPlayer] {message}")
        
        # Intentar añadir al TextEdit si está disponible
        if hasattr(self, 'textEdit') and self.textEdit:
            try:
                # Simplemente usar append que maneja el cursor internamente
                self.textEdit.append(str(message))
            except Exception as e:
                print(f"[UrlPlayer] Error escribiendo en textEdit: {e}")
    
    @pyqtSlot()
    def run(self):
        """Execute the search in the background."""
        try:
            # Get the search type from the parent widget
            search_type = getattr(self, 'search_type', 'all')
            self.log(f"Searching with type: {search_type}")
            
            # Attempt to get detailed information
            result = self.get_detailed_info()
            
            # Emit the results and finish signals
            self.signals.results.emit([result] if result else [])
            self.signals.finished.emit(result or {}, self.basic_data or {})
        
        except Exception as e:
            error_msg = f"Error loading information: {str(e)}"
            self.log(error_msg)
            
            # Emit error and finished signals
            self.signals.error.emit(error_msg)
            self.signals.finished.emit({"error": str(e)}, self.basic_data or {})
    
    def get_detailed_info(self):
        """
        Get detailed information from the database.
        This method should be implemented in the parent class or passed as a parameter.
        """
        try:
            # Import the database query class
            from db.tools.consultar_items_db import MusicDatabaseQuery
            
            # Use the configured database path
            db_path = self.db_path
            
            if not os.path.exists(db_path):
                self.log(f"Database not found at: {db_path}")
                return None
            
            db = MusicDatabaseQuery(db_path)
            result = {}
            
            if self.item_type.lower() == 'artist':
                # Get artist information
                artist_info = db.get_artist_info(self.artist)
                if artist_info:
                    result['artist_info'] = artist_info
                
                # Get artist links
                artist_links = db.get_artist_links(self.artist)
                if artist_links:
                    result['artist_links'] = artist_links
                
                # Get artist genres
                genres = db.get_artist_genres(self.artist)
                if genres:
                    result['genres'] = genres
                
                # Get wiki content
                wiki_content = db.get_artist_wiki_content(self.artist)
                if wiki_content:
                    result['wiki_content'] = wiki_content
                
            elif self.item_type.lower() in ['album', 'álbum']:
                # Get album information
                album_info = db.get_album_info(self.title, self.artist)
                if album_info:
                    result['album_info'] = album_info
                
                # Get album links
                album_links = db.get_album_links(self.artist, self.title)
                if album_links:
                    result['album_links'] = album_links
                
                # Get wiki content
                wiki_content = db.get_album_wiki(self.artist, self.title)
                if wiki_content:
                    result['wiki_content'] = wiki_content
                
            elif self.item_type.lower() in ['track', 'song', 'canción']:
                # Get song information
                song_info = db.get_song_info(self.title, self.artist, self.album)
                if song_info:
                    result['song_info'] = song_info
                
                # Get track links
                if self.album:
                    track_links = db.get_track_links(self.album, self.title)
                    if track_links:
                        result['track_links'] = track_links
                
                # Get album information
                if self.album:
                    album_info = db.get_album_info(self.album, self.artist)
                    if album_info:
                        result['album_info'] = album_info
            
            db.close()
            return result
        
        except Exception as e:
            self.log(f"Error getting detailed information: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return None

class SearchSignals(QObject):
    """Define the signals available for the SearchWorker."""
    results = pyqtSignal(list)
    error = pyqtSignal(str)
    finished = pyqtSignal(dict, dict)  # Changed to accept two dictionaries

class SearchWorker(QObject):
    """Worker thread for performing searches in different services."""
    
    # Señales
    finished = pyqtSignal()
    db_results_ready = pyqtSignal(list)
    external_results_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, parent, query, only_local):
        super().__init__()
        self.parent = parent
        self.query = query
        self.only_local = only_local
        self._stop_requested = False
        self.only_local = (filter_mode == 'local')

    def log(self, message):
        """Método seguro para registrar mensajes en el TextEdit y en la consola."""
        # Siempre imprimir en la consola
        print(f"[UrlPlayer] {message}")
        
        # Intentar añadir al TextEdit si está disponible
        if hasattr(self, 'textEdit') and self.textEdit:
            try:
                # Simplemente usar append que maneja el cursor internamente
                self.textEdit.append(str(message))
            except Exception as e:
                print(f"[UrlPlayer] Error escribiendo en textEdit: {e}")
    

    def stop(self):
        """Indicar que se debe detener la búsqueda"""
        self._stop_requested = True
    
    def run(self):
        """Método principal que se ejecuta en el hilo"""
        try:
            # Primero buscar en la base de datos para resultados rápidos
            from modules.submodules.url_playlist.db_manager import search_database_links
            
            # NEW: Only search database if filter allows it
            db_links = {}
            if self.filter_mode in ['all', 'local', 'db']:
                db_links = search_database_links(self.parent, self.parent.db_path, self.query, "all")
            
            if self._stop_requested:
                self.finished.emit()
                return
            
            if db_links:
                try:
                    # NEW: Process results with filter mode
                    results = self._process_database_results_with_filter(db_links)
                    
                    if results:
                        self.db_results_ready.emit(results)
                    
                except Exception as proc_error:
                    self.error.emit(f"Error al procesar resultados de BD: {str(proc_error)}")
            
            # NEW: Handle external search based on filter mode
            if self._stop_requested:
                self.finished.emit()
                return
                
            if self.filter_mode in ['all', 'online']:
                try:
                    self._perform_external_search()
                except Exception as search_error:
                    self.error.emit(f"Error en búsqueda externa: {str(search_error)}")
                    
        except Exception as e:
            self.error.emit(f"Error general en búsqueda: {str(e)}")
        finally:
            self.finished.emit()


    def _process_database_results_with_filter(self, db_links):
        """NEW: Process database results with the new filter system"""
        try:
            from modules.submodules.url_playlist.db_manager import _process_database_results
            all_results = _process_database_results(self.parent, db_links)
            
            if self.filter_mode == 'all':
                return all_results
            elif self.filter_mode == 'local':
                # Filter for items with origen='local' only
                return [r for r in all_results if r.get('origen') == 'local']
            elif self.filter_mode == 'db':
                # Return all database results regardless of origen
                return all_results
            else:  # online mode
                # Return empty list (no database results for online-only)
                return []
                
        except Exception as e:
            self.error.emit(f"Error procesando resultados con filtro: {str(e)}")
            return []


    def _process_database_results(self, db_links):
        """Procesa los resultados de la base de datos"""
        try:
            from modules.submodules.url_playlist.db_manager import _process_database_results
            return _process_database_results(self.parent, db_links)
        except Exception as e:
            self.error.emit(f"Error procesando resultados: {str(e)}")
            return []
    
    def _perform_external_search(self):
        """Realiza búsquedas en servicios externos"""
        try:
            from modules.submodules.url_playlist.db_manager import perform_search_with_service_filter
            
            # La función original no está diseñada para hilos QThread
            # Por ahora, usaremos un enfoque seguro:
            if hasattr(self.parent, 'included_services'):
                active_services = [s for s, enabled in self.parent.included_services.items() if enabled]
                
                # Aquí deberías implementar la búsqueda servicio por servicio de manera segura
                # Este código es simplificado y habría que adaptarlo según tus necesidades
                for service in active_services:
                    if self._stop_requested:
                        break
                    
                    # Lógica de búsqueda específica para cada servicio
                    # Este es solo un ejemplo y necesitaría adaptarse
                    if service == 'soundcloud':
                        self._search_soundcloud()
                    elif service == 'youtube':
                        self._search_youtube()
                    # etc. para otros servicios
            
        except Exception as e:
            self.error.emit(f"Error en búsqueda externa: {str(e)}")
    # Implementación segura para SoundCloud
    def _search_soundcloud(self):
        """Búsqueda segura en SoundCloud"""
        try:
            import requests
            from bs4 import BeautifulSoup
            import time
            
            # Implementar con mecanismos de timeout y recuperación
            search_url = f"https://soundcloud.com/search?q={self.query}"
            
            # Usar session para mejor manejo
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Usar timeout para evitar bloqueos
            response = session.get(search_url, timeout=10)
            
            if response.status_code != 200:
                self.error.emit(f"Error en búsqueda SoundCloud: Código {response.status_code}")
                return
                
            # Procesar el HTML de forma segura
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Resultado mínimo para evitar objetos pesados en memoria
            results = []
            
            # Procesamiento limitado
            items = soup.select('li.searchItem')[:10]  # Limitar a 10 resultados para evitar sobrecarga
            
            for item in items:
                if self._stop_requested:
                    break
                    
                # Extraer información básica con manejo de excepciones para cada campo
                try:
                    title = item.select_one('.soundTitle__title span') 
                    title = title.get_text().strip() if title else "Unknown Track"
                    
                    artist = item.select_one('.soundTitle__username')
                    artist = artist.get_text().strip() if artist else "Unknown Artist"
                    
                    url = item.select_one('a.soundTitle__title')
                    url = url.get('href') if url else None
                    
                    if url and not url.startswith('http'):
                        url = f"https://soundcloud.com{url}"
                    
                    if url:
                        results.append({
                            'title': title,
                            'artist': artist,
                            'url': url,
                            'source': 'soundcloud',
                            'type': 'track'
                        })
                except Exception as item_error:
                    # Manejar errores por item sin romper el ciclo completo
                    continue
            
            # Emitir resultados de forma segura
            if results:
                self.external_results_ready.emit({'soundcloud': results})
        
        except Exception as e:
            # Capturar cualquier error y reportarlo sin romper el hilo
            self.error.emit(f"Error en búsqueda SoundCloud: {str(e)}")



    def search_finished(self, result=None, basic_data=None):
        """Función llamada cuando termina la búsqueda."""
        try:
            # Si self es un diccionario y no el objeto esperado, usar el parent
            if isinstance(self, dict):
                # Acceder a través del parent del worker
                if hasattr(self, 'parent') and hasattr(self.parent, 'log'):
                    self.parent.log(f"Búsqueda completada.")
                    
                    # Hide loading indicator
                    self.parent.show_loading_indicator(False)
                    
                    # Reactivar controles
                    self.parent.searchButton.setEnabled(True)
                    self.parent.lineEdit.setEnabled(True)
                    
                    # Resto del código...
                else:
                    self.log("Búsqueda completada. (No se pudo acceder al método log)")
            else:
                # Comportamiento normal si self es la instancia correcta
                self.log(f"Búsqueda completada.")
                
                # Hide loading indicator
                self.show_loading_indicator(False)
                
                # Reactivar controles
                self.searchButton.setEnabled(True)
                self.lineEdit.setEnabled(True)
                
                # Make sure tree items are visible
                for i in range(self.treeWidget.topLevelItemCount()):
                    self.treeWidget.topLevelItem(i).setExpanded(True)
                
                # Select the first item if available
                if self.treeWidget.topLevelItemCount() > 0:
                    first_item = self.treeWidget.topLevelItem(0)
                    self.treeWidget.setCurrentItem(first_item)
                    if first_item.childCount() > 0:
                        child = first_item.child(0)
                        display_wiki_info(self, child.data(0, Qt.ItemDataRole.UserRole))
                
                QApplication.processEvents()  # Actualiza la UI
                
        except Exception as e:
            self.log(f"Error en search_finished: {str(e)}")
            import traceback
            self.log(traceback.format_exc())



    def search_youtube(self, query):
        """Search YouTube with standardized result format and respect only_local filter."""
        try:
            # Verificar si debemos aplicar filtro only_local
            only_local = getattr(self, 'only_local', False)
            
            # Si only_local está activo, buscar solo enlaces en la base de datos
            if only_local:
                return self._search_youtube_from_database(query)
            
            # Si no, realizar una búsqueda normal en YouTube
            import subprocess
            import json
            
            command = [
                "yt-dlp", 
                "--flat-playlist", 
                "--dump-json", 
                f"ytsearch{self.max_results}:{query}"
            ]
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if stderr and not stdout:
                self.log(f"Error searching YouTube: {stderr}")
                return []
                
            results = []
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    data = json.loads(line)
                    
                    # Extract artist from title using multiple strategies
                    title = data.get('title', 'Unknown Title')
                    artist = self._extract_artist_from_title(title)
                    
                    result = {
                        "source": "youtube",
                        "title": title,
                        "artist": artist,
                        "url": data.get('webpage_url', ''),
                        "type": "track",
                        "duration": data.get('duration')
                    }
                    results.append(result)
                    self.log(f"Found on YouTube: {title} by {artist}")
                except json.JSONDecodeError:
                    self.log(f"Error parsing YouTube result: {line}")
            
            return results
            
        except Exception as e:
            self.log(f"YouTube search error: {e}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def _search_youtube_from_database(self, query):
        """
        Busca enlaces de YouTube en la base de datos para elementos con origen 'local'.
        Solo se usa cuando only_local=True.
        """
        try:
            self.log(f"Buscando enlaces de YouTube en la base de datos para: {query}")
            
            # Verificar acceso a la base de datos
            if not hasattr(self, 'db_path') or not self.db_path:
                self.log("Error: No se especificó ruta de base de datos")
                return []
                
            # Obtener enlaces de la base de datos
            import sqlite3
            import os
            
            if not os.path.exists(self.db_path):
                self.log(f"Error: Base de datos no encontrada en {self.db_path}")
                return []
            
            # Conectar a la base de datos
            results = []
            
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Consulta para canciones con enlaces de YouTube y origen 'local'
                sql_songs = """
                SELECT s.title, s.artist, s.album, sl.youtube_url
                FROM songs s 
                JOIN song_links sl ON s.id = sl.song_id
                WHERE sl.youtube_url IS NOT NULL AND s.origen = 'local'
                AND (s.title LIKE ? OR s.artist LIKE ? OR s.album LIKE ?)
                """
                
                # Consulta para álbumes con enlaces de YouTube y origen 'local'
                sql_albums = """
                SELECT a.name, ar.name, a.year, a.youtube_url
                FROM albums a 
                JOIN artists ar ON a.artist_id = ar.id
                WHERE a.youtube_url IS NOT NULL AND a.origen = 'local'
                AND (a.name LIKE ? OR ar.name LIKE ?)
                """
                
                # Parámetros de búsqueda
                search_param = f"%{query}%"
                
                # Buscar canciones
                cursor.execute(sql_songs, (search_param, search_param, search_param))
                for row in cursor.fetchall():
                    title, artist, album, youtube_url = row
                    results.append({
                        "source": "youtube",
                        "title": title,
                        "artist": artist,
                        "album": album,
                        "url": youtube_url,
                        "type": "track",
                        "origen": "local",
                        "from_database": True
                    })
                    self.log(f"Found local YouTube track: {title} by {artist}")
                
                # Buscar álbumes
                cursor.execute(sql_albums, (search_param, search_param))
                for row in cursor.fetchall():
                    album_name, artist_name, year, youtube_url = row
                    results.append({
                        "source": "youtube",
                        "title": album_name,
                        "artist": artist_name,
                        "year": year,
                        "url": youtube_url,
                        "type": "album",
                        "origen": "local",
                        "from_database": True
                    })
                    self.log(f"Found local YouTube album: {album_name} by {artist_name}")
                
                conn.close()
                
                # Búsqueda más amplia en caso de no encontrar resultados directos
                if not results:
                    self.log("No se encontraron resultados directos, realizando búsqueda más amplia...")
                    results = self._expand_youtube_database_search(query)
                
                return results
                
            except sqlite3.Error as e:
                self.log(f"Error de base de datos: {str(e)}")
                return []
                
        except Exception as e:
            self.log(f"Error buscando enlaces de YouTube en la base de datos: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def _expand_youtube_database_search(self, query):
        """
        Búsqueda expandida de enlaces de YouTube en la base de datos.
        Intenta buscar coincidencias parciales o en otras tablas.
        """
        try:
            import sqlite3
            
            results = []
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Consulta para artistas con enlaces de redes sociales y origen local
            sql_artists = """
            SELECT ar.name, an.youtube
            FROM artists ar 
            JOIN artists_networks an ON ar.id = an.artist_id
            WHERE an.youtube IS NOT NULL AND ar.origen = 'local'
            AND ar.name LIKE ?
            """
            
            # Consulta de todas las tablas que pueden tener enlaces de YouTube
            sql_all_tables = """
            SELECT 'song' as type, s.title, s.artist, s.album, sl.youtube_url
            FROM songs s 
            JOIN song_links sl ON s.id = sl.song_id
            WHERE sl.youtube_url IS NOT NULL AND s.origen = 'local'
            
            UNION
            
            SELECT 'album' as type, a.name, ar.name, '', a.youtube_url
            FROM albums a 
            JOIN artists ar ON a.artist_id = ar.id
            WHERE a.youtube_url IS NOT NULL AND a.origen = 'local'
            
            UNION
            
            SELECT 'artist' as type, ar.name, '', '', an.youtube
            FROM artists ar 
            JOIN artists_networks an ON ar.id = an.artist_id
            WHERE an.youtube IS NOT NULL AND ar.origen = 'local'
            """
            
            # Parámetros de búsqueda
            search_param = f"%{query}%"
            
            # Buscar artistas
            cursor.execute(sql_artists, (search_param,))
            for row in cursor.fetchall():
                artist_name, youtube_url = row
                results.append({
                    "source": "youtube",
                    "title": artist_name,
                    "artist": artist_name,
                    "url": youtube_url,
                    "type": "artist",
                    "origen": "local",
                    "from_database": True
                })
                self.log(f"Found local YouTube artist: {artist_name}")
            
            # Si aún no hay resultados, usar la consulta unificada
            if not results:
                cursor.execute(sql_all_tables)
                for row in cursor.fetchall():
                    item_type, title, artist, album, youtube_url = row
                    
                    results.append({
                        "source": "youtube",
                        "title": title,
                        "artist": artist,
                        "album": album if album else "",
                        "url": youtube_url,
                        "type": item_type,
                        "origen": "local",
                        "from_database": True
                    })
                    self.log(f"Found local YouTube {item_type}: {title}" + (f" by {artist}" if artist else ""))
            
            conn.close()
            
            return results
            
        except Exception as e:
            self.log(f"Error en búsqueda expandida de YouTube: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def _extract_artist_from_title(self, title):
        """Extract artist from title with multiple strategies."""
        # Strategy 1: Split by hyphen (most common format "Artist - Title")
        parts = title.split(' - ', 1)
        if len(parts) > 1:
            return parts[0].strip()
        
        # Strategy 2: Look for "by" in the title
        parts = title.lower().split(' by ', 1)
        if len(parts) > 1:
            return parts[1].strip().title()
        
        # Strategy 3: Remove common keywords
        keywords = ['official video', 'official audio', 'lyric video', 'lyrics', 'official music video']
        cleaned_title = title.lower()
        for keyword in keywords:
            if keyword in cleaned_title:
                cleaned_title = cleaned_title.replace(keyword, '').strip()
        
        # If no clear artist found
        return "Unknown Artist"




    def search_spotify(self, query, search_type):
        """Searches on Spotify using existing module and database links if available."""
        try:
            # Check if we have database links for this query
            db_links = getattr(self, 'db_links', {})
            results = []
            
            # Import the necessary modules
            from db.enlaces_canciones_spot_lastfm import MusicLinkUpdater
            from db.enlaces_artista_album import MusicLinksManager
                
            # Use configuration from parent if available
            db_path = self.db_path
            spotify_client_id = self.spotify_client_id
            spotify_client_secret = self.spotify_client_secret
            
            # Prepare search based on search type
            if search_type.lower() in ['artist', 'artista']:
                # Check if we already have this artist in database with Spotify links
                artist_found = False
                for artist_name, artist_data in db_links.get('artists', {}).items():
                    # Check if artist name matches query
                    if artist_name.lower() == query.lower() or query.lower() in artist_name.lower():
                        # Look for spotify URL in links or direct field
                        spotify_url = None
                        if 'links' in artist_data and 'spotify' in artist_data['links']:
                            spotify_url = artist_data['links']['spotify']
                        elif 'spotify_url' in artist_data:
                            spotify_url = artist_data['spotify_url']
                        
                        if spotify_url:
                            results.append({
                                "source": "spotify",
                                "title": artist_name,
                                "artist": artist_name,
                                "url": spotify_url,
                                "type": "artist",
                                "from_database": True
                            })
                            artist_found = True
                            self.log(f"Found artist on Spotify from database: {artist_name}")
                            break
                
                # If not found in database, search via API
                if not artist_found and spotify_client_id and spotify_client_secret:
                    # Create MusicLinksManager for artist search
                    config = {
                        'db_path': db_path,
                        'spotify_client_id': spotify_client_id,
                        'spotify_client_secret': spotify_client_secret
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
                        self.log(f"Found artist on Spotify: {query}")
            
            elif search_type.lower() in ['album', 'álbum']:
                # Determine artist and album
                parts = query.split(" - ", 1)
                artist = parts[0] if len(parts) > 1 else ""
                album = parts[1] if len(parts) > 1 else query
                
                # Check if we have this album in database
                album_found = False
                
                # Try with artist - album format first
                if artist:
                    album_key = f"{artist} - {album}"
                    if album_key in db_links.get('albums', {}):
                        album_data = db_links['albums'][album_key]
                        
                        # Look for spotify URL in links or direct field
                        spotify_url = None
                        spotify_id = None
                        
                        if 'links' in album_data and 'spotify' in album_data['links']:
                            spotify_url = album_data['links']['spotify']
                        elif 'spotify_url' in album_data:
                            spotify_url = album_data['spotify_url']
                        
                        if 'spotify_id' in album_data:
                            spotify_id = album_data['spotify_id']
                        
                        if spotify_url:
                            results.append({
                                "source": "spotify",
                                "title": album,
                                "artist": artist,
                                "url": spotify_url,
                                "type": "album",
                                "spotify_id": spotify_id,
                                "from_database": True
                            })
                            album_found = True
                            self.log(f"Found album on Spotify from database: {album} by {artist}")
                
                # If not found with artist-album, check all albums
                if not album_found:
                    for album_key, album_data in db_links.get('albums', {}).items():
                        # Check if album title matches
                        if album_data['title'].lower() == album.lower():
                            # Look for spotify URL in links or direct field
                            spotify_url = None
                            spotify_id = None
                            
                            if 'links' in album_data and 'spotify' in album_data['links']:
                                spotify_url = album_data['links']['spotify']
                            elif 'spotify_url' in album_data:
                                spotify_url = album_data['spotify_url']
                            
                            if 'spotify_id' in album_data:
                                spotify_id = album_data['spotify_id']
                            
                            if spotify_url:
                                results.append({
                                    "source": "spotify",
                                    "title": album_data['title'],
                                    "artist": album_data['artist'],
                                    "url": spotify_url,
                                    "type": "album",
                                    "spotify_id": spotify_id,
                                    "from_database": True
                                })
                                album_found = True
                                self.log(f"Found album on Spotify from database: {album_data['title']} by {album_data['artist']}")
                                break
                
                # If not found in database, search via API
                if not album_found and spotify_client_id and spotify_client_secret:
                    # Create MusicLinksManager for album search
                    config = {
                        'db_path': db_path,
                        'spotify_client_id': spotify_client_id,
                        'spotify_client_secret': spotify_client_secret
                    }
                    
                    manager = MusicLinksManager(config)
                    
                    # Search for album
                    if artist:
                        album_data = manager._get_spotify_album_data(artist, album)
                    else:
                        album_data = manager._get_spotify_album_data("", album)
                    
                    if album_data and 'album_url' in album_data:
                        artist_name = artist or ""
                        album_name = album
                        
                        results.append({
                            "source": "spotify",
                            "title": album_name,
                            "artist": artist_name,
                            "url": album_data['album_url'],
                            "type": "album",
                            "spotify_id": album_data.get('album_id', '')
                        })
                        self.log(f"Found album on Spotify: {album_name}")
            
            else:
                # For tracks or general search
                # First check if query is in "artist - title" format
                parts = query.split(" - ", 1)
                artist = parts[0] if len(parts) > 1 else ""
                title = parts[1] if len(parts) > 1 else query
                
                # Check if we have this track in database
                track_found = False
                
                # Try with artist - title format first
                if artist:
                    track_key = f"{artist} - {title}"
                    if track_key in db_links.get('tracks', {}):
                        track_data = db_links['tracks'][track_key]
                        
                        # Look for spotify URL in links or direct field
                        spotify_url = None
                        spotify_id = None
                        
                        if 'links' in track_data and 'spotify' in track_data['links']:
                            spotify_url = track_data['links']['spotify']
                        elif 'spotify_url' in track_data:
                            spotify_url = track_data['spotify_url']
                        
                        if 'spotify_id' in track_data:
                            spotify_id = track_data['spotify_id']
                        
                        if spotify_url:
                            results.append({
                                "source": "spotify",
                                "title": title,
                                "artist": artist,
                                "album": track_data.get('album', ''),
                                "url": spotify_url,
                                "type": "track",
                                "spotify_id": spotify_id,
                                "from_database": True
                            })
                            track_found = True
                            self.log(f"Found track on Spotify from database: {title} by {artist}")
                
                # If not found with artist-title, check all tracks
                if not track_found:
                    for track_key, track_data in db_links.get('tracks', {}).items():
                        # Check if track title matches
                        if track_data['title'].lower() == title.lower():
                            # Look for spotify URL in links or direct field
                            spotify_url = None
                            spotify_id = None
                            
                            if 'links' in track_data and 'spotify' in track_data['links']:
                                spotify_url = track_data['links']['spotify']
                            elif 'spotify_url' in track_data:
                                spotify_url = track_data['spotify_url']
                            
                            if 'spotify_id' in track_data:
                                spotify_id = track_data['spotify_id']
                            
                            if spotify_url:
                                results.append({
                                    "source": "spotify",
                                    "title": track_data['title'],
                                    "artist": track_data['artist'],
                                    "album": track_data.get('album', ''),
                                    "url": spotify_url,
                                    "type": "track",
                                    "spotify_id": spotify_id,
                                    "from_database": True
                                })
                                track_found = True
                                self.log(f"Found track on Spotify from database: {track_data['title']} by {track_data['artist']}")
                                break
                
                # If not found in database, search via API
                if not track_found and spotify_client_id and spotify_client_secret:
                    # Set up configuration
                    temp_config = {
                        'db_path': db_path,
                        'checkpoint_path': ":memory:",
                        'services': ['spotify'],
                        'spotify_client_id': spotify_client_id,
                        'spotify_client_secret': spotify_client_secret,
                        'limit': self.max_results
                    }
                    
                    updater = MusicLinkUpdater(**temp_config)
                    
                    # Prepare the song object
                    song = {'title': title, 'artist': artist, 'album': ''}
                    
                    # Search for the track
                    spotify_url, spotify_id = updater.search_spotify(song, 
                                                                spotify_client_id,
                                                                spotify_client_secret)
                    
                    if spotify_url:
                        results.append({
                            "source": "spotify",
                            "title": song['title'],
                            "artist": song['artist'],
                            "url": spotify_url,
                            "type": "track",
                            "spotify_id": spotify_id
                        })
                        self.log(f"Found track on Spotify: {song['title']}")
            
            return results
            
        except Exception as e:
            self.log(f"Error searching on Spotify: {str(e)}")
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
                    
                    # Extract paths to help determine the type (track, playlist, user)
                    path_parts = url_path.strip('/').split('/')
                    item_type = "track"  # Default
                    
                    # Determine type from URL structure
                    if len(path_parts) > 1:
                        if path_parts[1] == "sets":
                            item_type = "playlist"
                        elif path_parts[1] == "tracks":
                            item_type = "track"
                    else:
                        item_type = "profile"  # Just username in URL
                    
                    soundcloud_results.append({
                        "source": "soundcloud",
                        "title": title,
                        "artist": artist,
                        "url": full_url,
                        "type": item_type
                    })
                    self.log(f"Found on SoundCloud: {title} by {artist} - URL: {full_url}")
                except Exception as e:
                    self.log(f"Error parsing SoundCloud result: {e}")
            
            return soundcloud_results
        except Exception as e:
            self.log(f"Error searching on SoundCloud: {e}")
            import traceback
            self.log(traceback.format_exc())
            return []

