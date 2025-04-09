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
        """Log method to emit error messages."""
        print(f"[InfoLoadWorker] {message}")
        self.signals.error.emit(message)
    
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
            from base_datos.tools.consultar_items_db import MusicDatabaseQuery
            
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

class SearchWorker(QRunnable):
    """Worker thread for performing searches in different services."""
    
    def __init__(self, services, query, max_results=10):
        super().__init__()
        self.services = services if isinstance(services, list) else [services]
        self.query = query
        self.max_results = max_results
        self.signals = SearchSignals()
        
    def log(self, message):
        """Send a log message through the error signal."""
        print(f"[SearchWorker] {message}")
        self.signals.error.emit(message)
    
    @pyqtSlot()
    def run(self):
        """Execute the search in the background."""
        try:
            results = []
            
            # Get the search type from the parent widget
            search_type = getattr(self, 'search_type', 'all')
            self.log(f"Searching with type: {search_type}")
            
            # First, search in the database
            if hasattr(self, 'parent'):
                db_results = self.parent.search_in_database(self.query, search_type)
                if db_results:
                    results.extend(db_results)
                    self.log(f"Found {len(db_results)} results in database")
            
            # Continue with service searches only if not enough results or force update
            if len(results) < self.max_results:
                for service in self.services:
                    service_results = []
                    
                    if service == "youtube":
                        service_results = self.search_youtube(self.query)
                    elif service == "soundcloud":
                        service_results = self.search_soundcloud(self.query)
                    elif service == "bandcamp":
                        service_results = self.search_bandcamp(self.query, search_type)
                    elif service == "spotify":
                        service_results = self.search_spotify(self.query, search_type)
                    elif service == "lastfm":
                        service_results = self.search_lastfm(self.query, search_type)
                    
                    # Apply pagination per service
                    if service_results:
                        results.extend(service_results[:self.max_results])
                        self.log(f"Found {len(service_results[:self.max_results])} results in {service}")
            
            # Emit results with an empty dictionary for the second argument to match signal
            self.signals.results.emit(results)
            self.signals.finished.emit({}, {})
        
        except Exception as e:
            error_msg = f"Error in search: {str(e)}"
            self.log(error_msg)
            self.signals.error.emit(error_msg)
            # Emit finished with error information
            self.signals.finished.emit({"error": str(e)}, {})

    def search_bandcamp(self, query, search_type):
        """Searches on Bandcamp with enhanced album and track support"""
        try:
            # Import the existing module
            from base_datos.enlaces_artista_album import MusicLinksManager
            
            # Create configuration based on module parameters
            config = {
                'db_path': getattr(self, self.db_path, os.path.join(PROJECT_ROOT, "base_datos", "musica1.db")),
                'rate_limit': 1.0,
                'disable_services': ['musicbrainz', 'discogs', 'youtube', 'spotify', 'rateyourmusic'],
                'log_level': 'WARNING'
            }
            
            # Create instance with configuration
            manager = MusicLinksManager(config)
            bandcamp_results = []
            
            # Determine if it's artist, album or song based on search type
            if search_type.lower() in ['artist', 'artista']:
                # First get artist URL
                artist_url = manager._get_bandcamp_artist_url(query)
                if artist_url:
                    # Create artist result
                    artist_result = {
                        "source": "bandcamp",
                        "title": query,
                        "artist": query,
                        "url": artist_url,
                        "type": "artist"
                    }
                    bandcamp_results.append(artist_result)
                    self.log(f"Found artist on Bandcamp: {query}")
                    
                    # Now, get albums for this artist
                    albums = self.get_bandcamp_artist_albums(artist_url)
                    if albums:
                        artist_result['albums'] = albums
                        self.log(f"Found {len(albums)} albums for artist {query}")
            
            elif search_type.lower() in ['album', 'álbum']:
                # If format is "artist - album"
                parts = query.split(" - ", 1)
                if len(parts) > 1:
                    artist, album = parts
                    album_url = manager._get_bandcamp_album_url(artist, album)
                    if album_url:
                        album_result = {
                            "source": "bandcamp",
                            "title": album,
                            "artist": artist,
                            "url": album_url,
                            "type": "album"
                        }
                        
                        # Get tracks for this album
                        tracks = self.get_bandcamp_album_tracks(album_url)
                        if tracks:
                            album_result['tracks'] = tracks
                            
                        bandcamp_results.append(album_result)
                        self.log(f"Found album on Bandcamp: {album} by {artist} with {len(tracks) if tracks else 0} tracks")
                else:
                    # Search only with album name
                    album_url = manager._get_bandcamp_album_url("", query)
                    if album_url:
                        # Try to extract artist name from URL
                        artist_name = self.extract_bandcamp_artist_from_url(album_url) or "Unknown Artist"
                        
                        album_result = {
                            "source": "bandcamp",
                            "title": query,
                            "artist": artist_name,
                            "url": album_url,
                            "type": "album"
                        }
                        
                        # Get tracks for this album
                        tracks = self.get_bandcamp_album_tracks(album_url)
                        if tracks:
                            album_result['tracks'] = tracks
                            
                        bandcamp_results.append(album_result)
                        self.log(f"Found album on Bandcamp: {query} with {len(tracks) if tracks else 0} tracks")
            
            else:
                # General search
                # Try as artist
                artist_url = manager._get_bandcamp_artist_url(query)
                if artist_url:
                    artist_result = {
                        "source": "bandcamp",
                        "title": query,
                        "artist": query,
                        "url": artist_url,
                        "type": "artist"
                    }
                    
                    # Get albums for this artist
                    albums = self.get_bandcamp_artist_albums(artist_url)
                    if albums:
                        artist_result['albums'] = albums
                        
                    bandcamp_results.append(artist_result)
                    self.log(f"Found artist on Bandcamp: {query} with {len(albums) if albums else 0} albums")
                
                # If format is "artist - title"
                parts = query.split(" - ", 1)
                if len(parts) > 1:
                    artist, title = parts
                    # Try as album
                    album_url = manager._get_bandcamp_album_url(artist, title)
                    if album_url:
                        album_result = {
                            "source": "bandcamp",
                            "title": title,
                            "artist": artist,
                            "url": album_url,
                            "type": "album"
                        }
                        
                        # Get tracks for this album
                        tracks = self.get_bandcamp_album_tracks(album_url)
                        if tracks:
                            album_result['tracks'] = tracks
                            
                        bandcamp_results.append(album_result)
                        self.log(f"Found album on Bandcamp: {title} by {artist} with {len(tracks) if tracks else 0} tracks")
            
            return bandcamp_results
                
        except Exception as e:
            self.log(f"Error searching on Bandcamp: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def get_bandcamp_artist_albums(self, artist_url):
        """Gets albums for a specific Bandcamp artist"""
        try:
            if not artist_url:
                return []
                
            # Use yt-dlp to get artist page info
            command = [
                "yt-dlp", 
                "--flat-playlist",
                "--dump-json",
                artist_url
            ]
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if stderr and not stdout:
                self.log(f"Error fetching Bandcamp artist albums: {stderr}")
                return []
                
            albums = []
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    data = json.loads(line)
                    # Filter out non-album entries (like tracks)
                    if 'album' in data.get('webpage_url', '').lower() or '/album/' in data.get('webpage_url', ''):
                        album = {
                            "source": "bandcamp",
                            "title": data.get('title', 'Unknown Album'),
                            "artist": data.get('artist', data.get('uploader', 'Unknown Artist')),
                            "url": data.get('webpage_url', ''),
                            "type": "album",
                            "year": self._extract_bandcamp_album_year(data.get('description', '')),
                        }
                        albums.append(album)
                except json.JSONDecodeError:
                    continue
                    
            return albums
                    
        except Exception as e:
            self.log(f"Error getting Bandcamp artist albums: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def _extract_bandcamp_album_year(self, description):
        """Extracts release year from Bandcamp album description"""
        try:
            # Common patterns in Bandcamp descriptions
            patterns = [
                r'released (\w+ \d{1,2}, (\d{4}))',
                r'released: (\w+ \d{1,2}, (\d{4}))',
                r'released in (\d{4})',
                r'released (\d{4})',
                r'(\d{4}) release',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match and match.group(2):
                    return match.group(2)
                elif match and match.group(1) and match.group(1).isdigit():
                    return match.group(1)
                    
            return None
        except Exception:
            return None

    def get_bandcamp_album_tracks(self, album_url):
        """Gets tracks for a specific Bandcamp album"""
        try:
            if not album_url:
                return []
                
            # Use yt-dlp to get album tracks
            command = [
                "yt-dlp", 
                "--flat-playlist",
                "--dump-json",
                album_url
            ]
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if stderr and not stdout:
                self.log(f"Error fetching Bandcamp album tracks: {stderr}")
                return []
                
            tracks = []
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    data = json.loads(line)
                    # Check if this is a track entry
                    if 'track' in data:
                        track = {
                            "source": "bandcamp",
                            "title": data.get('title', 'Unknown Track'),
                            "artist": data.get('artist', data.get('uploader', 'Unknown Artist')),
                            "url": data.get('webpage_url', ''),
                            "type": "track",
                            "track_number": data.get('track_number', ''),
                            "duration": data.get('duration'),
                            "album": data.get('album', '')
                        }
                        tracks.append(track)
                except json.JSONDecodeError:
                    continue
                    
            return tracks
                    
        except Exception as e:
            self.log(f"Error getting Bandcamp album tracks: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def extract_bandcamp_artist_from_url(self, url):
        """Extracts artist name from Bandcamp URL"""
        try:
            # Pattern like: https://artistname.bandcamp.com/
            match = re.search(r'https?://([^.]+)\.bandcamp\.com', url)
            if match:
                artist_slug = match.group(1)
                # Convert slug to readable name
                artist_name = artist_slug.replace('-', ' ').title()
                return artist_name
                
            # For pages like https://bandcamp.com/artist/artistname
            match = re.search(r'bandcamp\.com/artist/([^/]+)', url)
            if match:
                artist_slug = match.group(1)
                artist_name = artist_slug.replace('-', ' ').title()
                return artist_name
                
            return None
        except Exception:
            return None




    def search_spotify(self, query, search_type):
        """Busca en Spotify usando el módulo existente"""
        try:
            # Importar los módulos necesarios
            from base_datos.enlaces_canciones_spot_lastfm import MusicLinkUpdater
            
            # Usar configuración del padre si está disponible
            db_path = self.db_path or os.path.join(PROJECT_ROOT, "base_datos", "musica.db")
            spotify_client_id = self.spotify_client_id or os.environ.get("SPOTIFY_CLIENT_ID")
            spotify_client_secret = self.spotify_client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")            
            
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
                    'db_path': self.db_path or os.path.join(project_root, "base_datos", "musica1.sqlite"),
                    'spotify_client_id': self.spotify_client_id or os.environ.get("SPOTIFY_CLIENT_ID"),
                    'spotify_client_secret': self.spotify_client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")
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
                    'db_path': self.db_path or os.path.join(project_root, "base_datos", "musica.db"),
                    'spotify_client_id': self.spotify_client_id or os.environ.get("SPOTIFY_CLIENT_ID"),
                    'spotify_client_secret': self.spotify_client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")
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
            db_path = self.db_path or os.path.join(PROJECT_ROOT, "base_datos", "musica1.sqlite")
            lastfm_api_key = self.lastfm_api_key or os.environ.get("LASTFM_API_KEY")
            lastfm_user = self.lastfm_user or  os.environ.get("LASTFM_USER", "")
            
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

    def search_youtube(self, query):
        """Search YouTube with standardized result format."""
        try:
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




class UrlPlayer(BaseModule):
    """Módulo para reproducir música desde URLs (YouTube, SoundCloud, Bandcamp)."""
    
    def __init__(self, parent=None, theme='Tokyo Night', **kwargs):
        # Extract specific configurations from kwargs
        self.mpv_temp_dir = kwargs.pop('mpv_temp_dir', None)
        
        # Extract database configuration with more robust handling
        self.db_path = kwargs.get('db_path')
        if not self.db_path:
            # Check if db_path can be derived from config_path
            config_path = kwargs.get('config_path')
            if config_path and os.path.exists(config_path):
                try:
                    # Try to import the function directly
                    try:
                        from main import load_config_file
                        config_data = load_config_file(config_path)
                    except ImportError:
                        # Fallback method
                        extension = os.path.splitext(config_path)[1].lower()
                        if extension in ['.yml', '.yaml']:
                            import yaml
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config_data = yaml.safe_load(f)
                        else:  # Assume JSON
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config_data = json.load(f)
                    
                    # Check if db_path is in the loaded config
                    if 'db_path' in config_data:
                        db_path = config_data['db_path']
                        # Handle relative paths
                        if not os.path.isabs(db_path):
                            if os.path.isabs(config_path):
                                config_dir = os.path.dirname(config_path)
                                db_path = os.path.join(config_dir, db_path)
                            else:
                                db_path = os.path.join(PROJECT_ROOT, db_path)
                        
                        # Verify the database exists
                        if os.path.exists(db_path):
                            self.db_path = db_path
                            print(f"[UrlPlayer] Loaded db_path from config: {self.db_path}")
                        else:
                            print(f"[UrlPlayer] Warning: Database path from config ({db_path}) does not exist")
                except Exception as e:
                    print(f"[UrlPlayer] Error loading db_path from config file: {str(e)}")
            
            # Fallback to default if still not found
            if not self.db_path:
                # Try common locations for the database
                common_db_paths = [
                    os.path.join(PROJECT_ROOT, "base_datos", "musica.sqlite"),
                    os.path.join(PROJECT_ROOT, "base_datos", "musica1.sqlite"),
                    os.path.join(PROJECT_ROOT, "base_datos", "musica.db"),
                    os.path.join(PROJECT_ROOT, ".content", "db", "musica.sqlite")
                ]
                
                for path in common_db_paths:
                    if os.path.exists(path):
                        self.db_path = path
                        print(f"[UrlPlayer] Found database at: {self.db_path}")
                        break
                        
                if not self.db_path:
                    # Ultimate fallback
                    self.db_path = os.path.join(PROJECT_ROOT, "base_datos", "musica.sqlite")
                    print(f"[UrlPlayer] Using default db_path: {self.db_path}")
        
        # Extract API credentials from kwargs with fallbacks
        self.spotify_client_id = kwargs.get('spotify_client_id')
        self.spotify_client_secret = kwargs.get('spotify_client_secret')
        self.lastfm_api_key = kwargs.get('lastfm_api_key')
        self.lastfm_user = kwargs.get('lastfm_user')
        
        # Check if any of these are None and try to get them from environment
        if not all([self.spotify_client_id, self.spotify_client_secret, self.lastfm_api_key]):
            print(f"[UrlPlayer] Some API credentials not found in kwargs, checking environment variables")
            self._load_api_credentials_from_env()
        
        # Ensure these are available in environment variables for imported modules
        self._set_api_credentials_as_env()

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
        
        # Definir los servicios por defecto
        default_services = {
            'youtube': True,
            'soundcloud': True,
            'bandcamp': True,
            'spotify': self.spotify_enabled,
            'lastfm': self.lastfm_enabled
        }
        
        # Obtener la configuración de servicios incluidos de los kwargs
        included_services = kwargs.pop('included_services', {})
        
        # Inicializar el diccionario de servicios
        self.included_services = {}
        
        # Asegurar que todos los servicios predeterminados estén incluidos con valores booleanos
        for service, default_state in default_services.items():
            if service not in included_services:
                self.included_services[service] = default_state
            else:
                # Convertir representación de cadena a booleano si es necesario
                value = included_services[service]
                if isinstance(value, str):
                    self.included_services[service] = value.lower() == 'true'
                else:
                    self.included_services[service] = bool(value)
        
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
        self.ffButton = None  # Corregido de ffButton_3
        self.tabWidget = None
        self.listWidget = None
        self.delButton = None
        self.addButton = None
        self.textEdit = None
        self.info_wiki_textedit = None  # Añadido para evitar errores posteriores
        
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
        
         # Configure TreeWidget for better display of hierarchical data
        if hasattr(self, 'treeWidget') and self.treeWidget:
            # Set column headers
            self.treeWidget.setHeaderLabels(["Título", "Artista", "Tipo", "Track/Año", "Duración"])
            
            # Set column widths
            self.treeWidget.setColumnWidth(0, 250)  # Título
            self.treeWidget.setColumnWidth(1, 150)  # Artista
            self.treeWidget.setColumnWidth(2, 80)   # Tipo
            self.treeWidget.setColumnWidth(3, 70)   # Track/Año
            self.treeWidget.setColumnWidth(4, 70)   # Duración
            
            # Set indent for better hierarchy visualization
            self.treeWidget.setIndentation(20)
            
            # Enable sorting
            self.treeWidget.setSortingEnabled(True)
            self.treeWidget.sortByColumn(0, Qt.SortOrder.AscendingOrder)
            
            # Enable item expanding/collapsing on single click
            self.treeWidget.setExpandsOnDoubleClick(False)
            self.treeWidget.itemClicked.connect(self.on_tree_item_clicked)
        
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

    def on_tree_item_clicked(self, item, column):
        """Handle click on tree items to expand/collapse and display info."""
        try:
            # If item has children, toggle expanded state
            if item.childCount() > 0:
                item.setExpanded(not item.isExpanded())
                
                # If it's a parent item with data, display info
                item_data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(item_data, dict) and (item_data.get('title') or item_data.get('artist')):
                    self.display_wiki_info(item_data)
            else:
                # Get item data and display info
                item_data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(item_data, dict):
                    # Ensure album data is available for songs
                    if item_data.get('type') in ['track', 'song'] and not item_data.get('album'):
                        # If no album but has parent, get album from parent
                        parent = item.parent()
                        if parent and parent.text(2) == "Álbum":
                            item_data['album'] = parent.text(0)
                            
                    self.display_wiki_info(item_data)
        except Exception as e:
            self.log(f"Error en tree item clicked: {str(e)}")

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
                'spotify_check': 'spotify',
                'lastfm_check': 'lastfm'
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
        """Loads module configuration from the general configuration file with more robust path handling."""
        try:
            # Try multiple config file locations
            config_paths = [
                os.path.join(PROJECT_ROOT, "config", "config.yml"),
                #os.path.join(PROJECT_ROOT, "config", "config.yaml"),
                os.path.join(PROJECT_ROOT, ".content", "config", "config.yml"),
                os.path.join(os.path.expanduser("~"), ".config", "music_app", "config.yml")
            ]
            
            config_loaded = False
            for config_path in config_paths:
                if os.path.exists(config_path):
                    self.log(f"Found configuration file at: {config_path}")
                    try:
                        # Use the global configuration loading functions if available
                        try:
                            from main import load_config_file
                            config_data = load_config_file(config_path)
                        except ImportError:
                            # Fallback if main module is not importable
                            extension = os.path.splitext(config_path)[1].lower()
                            if extension in ['.yml', '.yaml']:
                                import yaml
                                with open(config_path, 'r', encoding='utf-8') as f:
                                    config_data = yaml.safe_load(f)
                            else:  # Assume JSON
                                with open(config_path, 'r', encoding='utf-8') as f:
                                    config_data = json.load(f)
                        
                        config_loaded = True
                        self.log(f"Successfully loaded configuration from {config_path}")
                        break
                    except Exception as e:
                        self.log(f"Error loading configuration from {config_path}: {str(e)}")
                        continue
            
            if not config_loaded:
                self.log("No configuration file found, using default values")
                config_data = {}
            
            # First try to load db_path from config_data root if available
            if 'db_path' in config_data and not self.db_path:
                db_path = config_data['db_path']
                # Handle both relative and absolute paths
                if not os.path.isabs(db_path):
                    db_path = os.path.join(PROJECT_ROOT, db_path)
                
                # Verify the path exists and is readable
                if os.path.exists(db_path):
                    self.db_path = db_path
                    self.log(f"Loaded db_path from config root: {self.db_path}")
                else:
                    self.log(f"Warning: Database path from config ({db_path}) does not exist")
                    
                    # Try common alternative locations for the database
                    alt_db_paths = [
                        os.path.join(PROJECT_ROOT, "base_datos", "musica2.sqlite"),
                        os.path.join(PROJECT_ROOT, "base_datos", "musica1.sqlite"),
                        os.path.join(PROJECT_ROOT, "base_datos", "musica.db"),
                        os.path.join(PROJECT_ROOT, ".content", "db", "musica.sqlite")
                    ]
                    
                    for alt_path in alt_db_paths:
                        if os.path.exists(alt_path):
                            self.db_path = alt_path
                            self.log(f"Using alternative database path: {self.db_path}")
                            break
            
            # Find module configuration within the loaded config
            # Search for this module's specific configuration
            # First in active modules
            module_config = None
            for module in config_data.get('modules', []):
                if module.get('name') in ['Url Playlists', 'URL Playlist', 'URL Player']:
                    module_config = module.get('args', {})
                    self.log(f"Found module configuration for '{module.get('name')}'")
                    break
            
            # If not found in active modules, check disabled modules
            if module_config is None:
                for module in config_data.get('modulos_desactivados', []):
                    if module.get('name') in ['Url Playlists', 'URL Playlist', 'URL Player']:
                        module_config = module.get('args', {})
                        self.log(f"Found module configuration in disabled modules for '{module.get('name')}'")
                        break
            
            if module_config:
                # Load db_path from module config if not already set
                if 'db_path' in module_config and not self.db_path:
                    db_path = module_config.get('db_path')
                    # Handle both relative and absolute paths
                    if not os.path.isabs(db_path):
                        db_path = os.path.join(PROJECT_ROOT, db_path)
                    
                    # Verify the path exists
                    if os.path.exists(db_path):
                        self.db_path = db_path
                        self.log(f"Loaded db_path from module config: {self.db_path}")
                    else:
                        self.log(f"Warning: Database path from module config ({db_path}) does not exist")
                
                # Load API credentials if not already set
                if 'spotify_client_id' in module_config and not self.spotify_client_id:
                    self.spotify_client_id = module_config.get('spotify_client_id')
                    self.log("Loaded spotify_client_id from module config")
                    
                if 'spotify_client_secret' in module_config and not self.spotify_client_secret:
                    self.spotify_client_secret = module_config.get('spotify_client_secret')
                    self.log("Loaded spotify_client_secret from module config")
                    
                if 'lastfm_api_key' in module_config and not self.lastfm_api_key:
                    self.lastfm_api_key = module_config.get('lastfm_api_key')
                    self.log("Loaded lastfm_api_key from module config")
                    
                if 'lastfm_user' in module_config and not self.lastfm_user:
                    self.lastfm_user = module_config.get('lastfm_user')
                    self.log("Loaded lastfm_user from module config")
                
                # Update environment variables with new credentials
                self._set_api_credentials_as_env()
                
                # Load pagination_value
                self.pagination_value = module_config.get('pagination_value', 10)
                self.num_servicios_spinBox = self.pagination_value  # Sync both values
                
                # Load included_services
                included_services = module_config.get('included_services', {})
                
                # Ensure included_services values are booleans, not strings
                self.included_services = {}
                for key, value in included_services.items():
                    if isinstance(value, str):
                        self.included_services[key] = value.lower() == 'true'
                    else:
                        self.included_services[key] = bool(value)
                
                self.log(f"Loaded configuration from config file")
            else:
                self.log("No specific module configuration found, using default values")
                # Initialize with default values
                self.pagination_value = 10
                self.num_servicios_spinBox = 10
                self.included_services = {
                    'youtube': True,
                    'soundcloud': True,
                    'bandcamp': True,
                    'spotify': self.spotify_enabled,
                    'lastfm': self.lastfm_enabled,
                }
            
            # If we still don't have a db_path, try to find the database file
            if not self.db_path:
                # Try common locations for the database
                common_db_paths = [
                    os.path.join(PROJECT_ROOT, "base_datos", "musica2.sqlite"),
                    os.path.join(PROJECT_ROOT, "base_datos", "musica1.sqlite"),
                    os.path.join(PROJECT_ROOT, "base_datos", "musica.db"),
                    os.path.join(PROJECT_ROOT, ".content", "db", "musica.sqlite")
                ]
                
                for path in common_db_paths:
                    if os.path.exists(path):
                        self.db_path = path
                        self.log(f"Found database at common location: {self.db_path}")
                        break
                
                if not self.db_path:
                    self.log("Warning: Could not find a database file. Search functionality may be limited.")
            
            # If still no API credentials, try loading from environment/other sources
            if not all([self.spotify_client_id, self.spotify_client_secret, self.lastfm_api_key]):
                self._load_api_credentials_from_env()
                
        except Exception as e:
            self.log(f"Error loading configuration: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            
            # Initialize with default values in case of error
            self.pagination_value = 10
            self.num_servicios_spinBox = 10
            self.included_services = {
                'youtube': True,
                'soundcloud': True,
                'bandcamp': True,
                'spotify': self.spotify_enabled,
                'lastfm': self.lastfm_enabled,
            }
            
            # Try to find the database as a last resort
            if not self.db_path:
                common_db_paths = [
                    os.path.join(PROJECT_ROOT, "base_datos", "musica2.sqlite"),
                    os.path.join(PROJECT_ROOT, "base_datos", "musica1.sqlite"),
                    os.path.join(PROJECT_ROOT, "base_datos", "musica.db"),
                    os.path.join(PROJECT_ROOT, ".content", "db", "musica.sqlite")
                ]
                
                for path in common_db_paths:
                    if os.path.exists(path):
                        self.db_path = path
                        self.log(f"Found database at common location: {self.db_path}")
                        break

    def save_settings(self):
        """Guarda la configuración del módulo en el archivo de configuración general."""
        try:
            # Try multiple config paths
            config_paths = [
                os.path.join(PROJECT_ROOT, "config", "config.yml"),
                os.path.join(PROJECT_ROOT, "config", "config.yaml"),
                os.path.join(PROJECT_ROOT, ".content", "config", "config.yml")
            ]
            
            config_path = None
            for path in config_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            
            if not config_path:
                self.log(f"No configuration file found. Creating new one at: {config_paths[0]}")
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(config_paths[0]), exist_ok=True)
                config_path = config_paths[0]
                
                # Create empty config
                config_data = {
                    'modules': [],
                    'modulos_desactivados': []
                }
            else:
                # Load existing config
                try:
                    # Try to use function from main module
                    try:
                        from main import load_config_file
                        config_data = load_config_file(config_path)
                    except ImportError:
                        # Fallback method
                        extension = os.path.splitext(config_path)[1].lower()
                        if extension in ['.yml', '.yaml']:
                            import yaml
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config_data = yaml.safe_load(f)
                        else:  # Assume JSON
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config_data = json.load(f)
                except Exception as e:
                    self.log(f"Error loading config file: {e}")
                    return
            
            # Asegurar que pagination_value esté sincronizado con num_servicios_spinBox
            self.pagination_value = self.num_servicios_spinBox
            
            # Store current database path - relative to PROJECT_ROOT if possible
            db_path_to_save = self.db_path
            if db_path_to_save and os.path.isabs(db_path_to_save):
                try:
                    # Convert to relative path if inside PROJECT_ROOT
                    rel_path = os.path.relpath(db_path_to_save, PROJECT_ROOT)
                    # Only use relative path if it doesn't go up directories
                    if not rel_path.startswith('..'):
                        db_path_to_save = rel_path
                except ValueError:
                    # Keep using absolute path if there's an error
                    pass
            
            # Preparar configuración de este módulo
            new_settings = {
                'mpv_temp_dir': '.config/mpv/_mpv_socket',  # Mantener valor existente o usar por defecto
                'pagination_value': self.pagination_value,
                'included_services': self.included_services,  # Now storing actual boolean values
                'db_path': db_path_to_save,
                'spotify_client_id': self.spotify_client_id,
                'spotify_client_secret': self.spotify_client_secret,
                'lastfm_api_key': self.lastfm_api_key,
                'lastfm_user': self.lastfm_user
            }
            
            # Bandera para saber si se encontró y actualizó el módulo
            module_updated = False
            
            # Try all possible module names
            module_names = ['Url Playlists', 'URL Playlist', 'URL Player']
            
            # Actualizar la configuración en el módulo correspondiente
            for module in config_data.get('modules', []):
                if module.get('name') in module_names:
                    # Reemplazar completamente los argumentos para evitar duplicados
                    module['args'] = new_settings
                    module_updated = True
                    break
            
            # Si no se encontró en los módulos activos, buscar en los desactivados
            if not module_updated:
                for module in config_data.get('modulos_desactivados', []):
                    if module.get('name') in module_names:
                        # Reemplazar completamente los argumentos para evitar duplicados
                        module['args'] = new_settings
                        module_updated = True
                        break
            
            # Si no se encontró el módulo, añadirlo a los módulos activos
            if not module_updated:
                self.log("Module not found in config, adding it to active modules")
                # Make sure the modules list exists
                if 'modules' not in config_data:
                    config_data['modules'] = []
                    
                # Add new module entry
                config_data['modules'].append({
                    'name': 'URL Playlist',
                    'path': 'modulos/url_playlist.py',
                    'args': new_settings
                })
            
            # Guardar la configuración actualizada
            try:
                # Try to use save function from main module
                try:
                    from main import save_config_file
                    save_config_file(config_path, config_data)
                except ImportError:
                    # Fallback method
                    extension = os.path.splitext(config_path)[1].lower()
                    if extension in ['.yml', '.yaml']:
                        import yaml
                        with open(config_path, 'w', encoding='utf-8') as f:
                            yaml.dump(config_data, f, sort_keys=False, default_flow_style=False, indent=2)
                    else:  # Assume JSON
                        import json
                        with open(config_path, 'w', encoding='utf-8') as f:
                            json.dump(config_data, f, indent=2)
            except Exception as e:
                self.log(f"Error saving config: {e}")
                return
                
            self.log(f"Configuración guardada en {config_path}")
        except Exception as e:
            self.log(f"Error al guardar configuración: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
   
    def _load_api_credentials_from_env(self):
        """Load API credentials from environment variables with better fallbacks"""
        # First try environment variables
        if not self.spotify_client_id:
            self.spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        
        if not self.spotify_client_secret:
            self.spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
            
        if not self.lastfm_api_key:
            self.lastfm_api_key = os.environ.get("LASTFM_API_KEY")
            
        if not self.lastfm_user:
            self.lastfm_user = os.environ.get("LASTFM_USER")
        
        # If still missing, systematically try all config file locations
        config_files = [
            os.path.join(PROJECT_ROOT, "config", "api_keys.json"),
            os.path.join(PROJECT_ROOT, ".content", "config", "api_keys.json"),
            os.path.join(os.path.expanduser("~"), ".config", "music_app", "api_keys.json")
        ]
        
        for config_path in config_files:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        api_config = json.load(f)
                        
                        if 'spotify' in api_config:
                            if not self.spotify_client_id:
                                self.spotify_client_id = api_config['spotify'].get('client_id')
                                self.log(f"Loaded Spotify client ID from {config_path}")
                            if not self.spotify_client_secret:
                                self.spotify_client_secret = api_config['spotify'].get('client_secret')
                                self.log(f"Loaded Spotify client secret from {config_path}")
                        
                        if 'lastfm' in api_config:
                            if not self.lastfm_api_key:
                                self.lastfm_api_key = api_config['lastfm'].get('api_key')
                                self.log(f"Loaded Last.fm API key from {config_path}")
                            if not self.lastfm_user:
                                self.lastfm_user = api_config['lastfm'].get('user')
                                self.log(f"Loaded Last.fm user from {config_path}")
                        
                    # If we found and loaded the config, break the loop
                    if all([self.spotify_client_id, self.spotify_client_secret, self.lastfm_api_key]):
                        self.log(f"Successfully loaded all API credentials from {config_path}")
                        break
                except Exception as e:
                    self.log(f"Error loading API credentials from {config_path}: {str(e)}")

        # Try dotenv as a last resort
        try:
            from dotenv import load_dotenv
            # Load from any potential .env files
            load_dotenv()
            
            # Check again if environment variables are now available
            if not self.spotify_client_id:
                self.spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
            if not self.spotify_client_secret:
                self.spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
            if not self.lastfm_api_key:
                self.lastfm_api_key = os.environ.get("LASTFM_API_KEY")
            if not self.lastfm_user:
                self.lastfm_user = os.environ.get("LASTFM_USER")
                
            self.log("Attempted to load credentials from .env files")
        except ImportError:
            # dotenv is not installed, that's fine
            pass

    def _set_api_credentials_as_env(self):
        """Set API credentials as environment variables for imported modules with better validation"""
        if self.spotify_client_id and isinstance(self.spotify_client_id, str) and self.spotify_client_id.strip():
            os.environ["SPOTIFY_CLIENT_ID"] = self.spotify_client_id.strip()
            self.log(f"Set SPOTIFY_CLIENT_ID in environment")
        
        if self.spotify_client_secret and isinstance(self.spotify_client_secret, str) and self.spotify_client_secret.strip():
            os.environ["SPOTIFY_CLIENT_SECRET"] = self.spotify_client_secret.strip()
            self.log(f"Set SPOTIFY_CLIENT_SECRET in environment")
        
        if self.lastfm_api_key and isinstance(self.lastfm_api_key, str) and self.lastfm_api_key.strip():
            os.environ["LASTFM_API_KEY"] = self.lastfm_api_key.strip()
            self.log(f"Set LASTFM_API_KEY in environment")
        
        if self.lastfm_user and isinstance(self.lastfm_user, str) and self.lastfm_user.strip():
            os.environ["LASTFM_USER"] = self.lastfm_user.strip()
            self.log(f"Set LASTFM_USER in environment")
            
        # Update enabled flags based on credentials
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        self.lastfm_enabled = bool(self.lastfm_api_key)
        
        # Update included_services based on what's available
        if not self.spotify_enabled and 'spotify' in self.included_services:
            self.included_services['spotify'] = False
            self.log("Disabled Spotify service due to missing credentials")
            
        if not self.lastfm_enabled and 'lastfm' in self.included_services:
            self.included_services['lastfm'] = False
            self.log("Disabled Last.fm service due to missing credentials")


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
            
            # Add individual services with proper capitalization
            service_info = [
                ('youtube', "YouTube", ":/services/youtube"),
                ('soundcloud', "SoundCloud", ":/services/soundcloud"),
                ('bandcamp', "Bandcamp", ":/services/bandcamp"),
                ('spotify', "Spotify", ":/services/spotify"),
                ('lastfm', "Last.fm", ":/services/lastfm")
            ]
            
            for service_id, display_name, icon_path in service_info:
                # Only add if service is included
                included = self.included_services.get(service_id, False)
                if isinstance(included, str):
                    included = included.lower() == 'true'
                    
                if included:
                    self.servicios.addItem(QIcon(icon_path), display_name)
            
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
        Busca enlaces en la base de datos con estructura de álbumes y canciones
        """
        try:
            from base_datos.tools.consultar_items_db import MusicDatabaseQuery
            
            if not self.db_path or not os.path.exists(self.db_path):
                self.log(f"Database not found at: {self.db_path}")
                return []
            
            if not os.path.exists(self.db_path):
                self.log(f"Base de datos no encontrada en: {db_path}")
                return []
                    
            self.log(f"Searching database at: {self.db_path}")
            db = MusicDatabaseQuery(self.db_path)
            results = []
            
            # Búsqueda de artistas
            if search_type.lower() in ["artista", "artist", "all"]:
                self.log(f"Buscando artista '{query}' en la base de datos")
                artist_info = db.get_artist_info(query)
                
                if artist_info:
                    # Resultado base del artista
                    base_result = {
                        "source": "database",
                        "title": query,
                        "artist": query,
                        "type": "artist",
                        "from_database": True
                    }
                    
                    # Obtener álbumes del artista
                    artist_albums = db.get_artist_albums(query)
                    album_results = []
                    
                    for album in artist_albums:
                        album_name = album[0]  # Nombre del álbum
                        album_year = album[1] if len(album) > 1 else None
                        
                        # Obtener información detallada del álbum
                        album_info = db.get_album_info(album_name, query)
                        
                        album_result = {
                            "source": "database",
                            "title": album_name,
                            "artist": query,
                            "type": "album",
                            "year": album_year,
                            "from_database": True
                        }
                        
                        # Obtener canciones del álbum
                        if album_info and 'songs' in album_info:
                            track_results = []
                            for song in album_info['songs']:
                                track_result = {
                                    "source": "database",
                                    "title": song.get('title', 'Canción sin título'),
                                    "artist": query,
                                    "album": album_name,
                                    "type": "track",
                                    "track_number": song.get('track_number'),
                                    "duration": song.get('duration')
                                }
                                track_results.append(track_result)
                            
                            # Añadir canciones al álbum
                            album_result['tracks'] = track_results
                        
                        album_results.append(album_result)
                    
                    # Añadir álbumes al resultado del artista
                    base_result['albums'] = album_results
                    
                    results.append(base_result)
                    for result in results:
                        self.log(f"Resultado de búsqueda: {json.dumps(result, indent=2)}")
            
            db.close()
            return results
        
        except Exception as e:
            self.log(f"Error buscando en la base de datos: {str(e)}")
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
        active_services = []
        if service == "Todos":
            # Check each service in the included_services dictionary
            for service_id, included in self.included_services.items():
                # Convert included to boolean if it's a string
                if isinstance(included, str):
                    included = included.lower() == 'true'
                
                if included:
                    active_services.append(service_id)
        else:
            # Convert from display name to service id (lowercase)
            service_id = service.lower()
            active_services = [service_id]
        
        if not active_services:
            self.log("No hay servicios seleccionados para la búsqueda. Por favor, actívalos en Configuración Avanzada.")
            return
        
        # Mostrar progreso
        self.textEdit.append(f"Buscando '{query}' en {service} (tipo: {search_type}, máx. {self.pagination_value} resultados por servicio)...")
        QApplication.processEvents()  # Actualiza la UI
        
        # Desactivar controles durante la búsqueda
        self.searchButton.setEnabled(False)
        self.lineEdit.setEnabled(False)
        QApplication.processEvents()  # Actualiza la UI
        
        # Crear y configurar el worker con los atributos necesarios
        worker = SearchWorker(active_services, query, max_results=self.pagination_value)
        worker.parent = self  # Set parent to access search_in_database
        worker.search_type = search_type  # Pass search type to worker
        
        # Pass necessary attributes from parent
        worker.db_path = self.db_path
        worker.spotify_client_id = self.spotify_client_id
        worker.spotify_client_secret = self.spotify_client_secret
        worker.lastfm_api_key = self.lastfm_api_key
        worker.lastfm_user = self.lastfm_user
        
        # Conectar señales
        worker.signals.results.connect(self.display_search_results)
        worker.signals.error.connect(lambda err: self.log(f"Search error: {err}"))
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
        """
        Muestra los resultados de la búsqueda en el TreeWidget de forma jerárquica,
        priorizando resultados de la base de datos y luego añadiendo resultados de servicios.
        """
        # Limpiar resultados previos
        self.treeWidget.clear()
        QApplication.processEvents()  # Actualiza la UI
        
        if not results:
            self.textEdit.append("No se encontraron resultados.")
            QApplication.processEvents()  # Actualiza la UI
            return
        
        # Separar resultados de base de datos y servicios
        db_results = [r for r in results if r.get('source', '').lower() == 'database']
        service_results = [r for r in results if r.get('source', '').lower() != 'database']
        
        # Primero procesar resultados de base de datos
        if db_results:
            self._add_database_results(db_results)
        
        # Luego añadir resultados de servicios externos
        if service_results:
            self._add_service_results(service_results)
        
        # Expandir todos los nodos por defecto
        for i in range(self.treeWidget.topLevelItemCount()):
            self.treeWidget.topLevelItem(i).setExpanded(True)
        
        # Mostrar información del primer resultado si existe
        if results:
            self.display_wiki_info(results[0])
        
        # Actualizar conteo de resultados
        self.textEdit.append(f"Encontrados {len(results)} resultados.")
        QApplication.processEvents()  # Actualización final de UI

    def _add_database_results(self, db_results):
        """
        Añade resultados de la base de datos al árbol de manera jerárquica.
        """
        for result in db_results:
            if result.get('type', '').lower() == 'artist' and result.get('albums'):
                artist_name = result.get('artist', 'Unknown Artist')
                
                # Crear item raíz para el artista
                artist_item = QTreeWidgetItem(self.treeWidget)
                artist_item.setText(0, artist_name)
                artist_item.setText(1, artist_name)
                artist_item.setText(2, "Artista (Base de Datos)")
                
                # Formatear en negrita
                font = artist_item.font(0)
                font.setBold(True)
                artist_item.setFont(0, font)
                artist_item.setFont(1, font)
                
                # Almacenar datos del artista
                artist_item.setData(0, Qt.ItemDataRole.UserRole, result)
                
                # Añadir álbumes
                for album in result.get('albums', []):
                    album_name = album.get('title', 'Unknown Album')
                    
                    # Crear item de álbum
                    album_item = QTreeWidgetItem(artist_item)
                    album_item.setText(0, album_name)
                    album_item.setText(1, artist_name)
                    album_item.setText(2, "Álbum")
                    
                    # Almacenar datos del álbum
                    album_item.setData(0, Qt.ItemDataRole.UserRole, album)
                    
                    # Añadir canciones del álbum
                    for track in album.get('tracks', []):
                        track_item = QTreeWidgetItem(album_item)
                        track_item.setText(0, track.get('title', 'Canción sin título'))
                        track_item.setText(1, artist_name)
                        track_item.setText(2, "Canción")
                        
                        # Almacenar datos de la canción
                        track_item.setData(0, Qt.ItemDataRole.UserRole, track)

    def _add_service_results(self, service_results):
        """
        Adds external service results to the tree in a hierarchical structure.
        Enhanced to better handle Bandcamp albums and tracks, and flatten YouTube results.
        """
        # Group results by service and artist
        services_map = {}
        
        # Initialize special structure for YouTube
        services_map['Youtube'] = {'results': []}
        
        for result in service_results:
            service = result.get('source', 'Otros').capitalize()
            
            # Special handling for YouTube results
            if service.lower() == 'youtube':
                # Add directly to the flat YouTube results list
                services_map['Youtube']['results'].append(result)
                continue
            
            # For other services, use hierarchical structure
            artist_name = result.get('artist', 'Unknown Artist')
            
            if service not in services_map:
                services_map[service] = {}
            
            if artist_name not in services_map[service]:
                services_map[service][artist_name] = {
                    'info': None,
                    'albums': {},
                    'tracks': []
                }
            
            result_type = result.get('type', '').lower()
            
            if result_type == 'artist':
                services_map[service][artist_name]['info'] = result
                
                # If this artist result has albums, add them to the albums dict
                if 'albums' in result and isinstance(result['albums'], list):
                    for album in result['albums']:
                        album_name = album.get('title', 'Unknown Album')
                        services_map[service][artist_name]['albums'][album_name] = album
            elif result_type == 'album':
                album_name = result.get('title', 'Unknown Album')
                services_map[service][artist_name]['albums'][album_name] = result
                
                # If this album has tracks, don't add to the generic tracks list
                if 'tracks' in result and isinstance(result['tracks'], list):
                    pass
            elif result_type in ['track', 'song']:
                # Add to general tracks list only if not part of an album
                album_name = result.get('album', '')
                if not album_name:
                    services_map[service][artist_name]['tracks'].append(result)
        
        # Add service results to the tree
        for service, data in services_map.items():
            # Skip empty services
            if service == 'Youtube' and not data['results']:
                continue
            elif service != 'Youtube' and not data:
                continue
                
            service_item = QTreeWidgetItem(self.treeWidget)
            service_item.setText(0, service)
            service_item.setText(2, "Servicio Externo")
            
            # Format service in italic
            font = service_item.font(0)
            font.setItalic(True)
            service_item.setFont(0, font)
            
            # Special case for YouTube - flat list
            if service == 'Youtube':
                # Add results directly under service item
                for result in data['results']:
                    track_item = QTreeWidgetItem(service_item)
                    track_item.setText(0, result.get('title', 'Unknown Track'))
                    track_item.setText(1, result.get('artist', 'Unknown Artist'))
                    track_item.setText(2, "Video")
                    
                    # Add duration if available
                    if result.get('duration'):
                        duration_str = self.format_duration(result.get('duration'))
                        track_item.setText(4, duration_str)
                        
                    # Store track information
                    track_item.setData(0, Qt.ItemDataRole.UserRole, result)
                
                # Continue to next service
                continue
            
            # Normal hierarchical structure for other services
            for artist_name, artist_data in data.items():
                artist_item = QTreeWidgetItem(service_item)
                artist_item.setText(0, artist_name)
                artist_item.setText(1, artist_name)
                artist_item.setText(2, f"Artista ({service})")
                
                # Store artist information
                if artist_data.get('info'):
                    artist_item.setData(0, Qt.ItemDataRole.UserRole, artist_data['info'])
                
                # Add albums
                for album_name, album_info in artist_data.get('albums', {}).items():
                    album_item = QTreeWidgetItem(artist_item)
                    album_item.setText(0, album_name)
                    album_item.setText(1, artist_name)
                    album_item.setText(2, f"Álbum ({service})")
                    
                    # Add year information if available
                    if album_info.get('year'):
                        album_item.setText(3, str(album_info.get('year')))
                    
                    # Store album information
                    album_item.setData(0, Qt.ItemDataRole.UserRole, album_info)
                    
                    # Add tracks if available in the album
                    if 'tracks' in album_info and isinstance(album_info['tracks'], list):
                        for track_idx, track in enumerate(album_info['tracks']):
                            track_item = QTreeWidgetItem(album_item)
                            track_item.setText(0, track.get('title', f'Track {track_idx+1}'))
                            track_item.setText(1, artist_name)
                            track_item.setText(2, f"Canción ({service})")
                            
                            # Add track number and duration if available
                            if track.get('track_number'):
                                track_item.setText(3, str(track.get('track_number')))
                            elif track_idx is not None:
                                track_item.setText(3, str(track_idx+1))
                                
                            if track.get('duration'):
                                duration_str = self.format_duration(track.get('duration'))
                                track_item.setText(4, duration_str)
                                
                            # Store track information
                            track_item.setData(0, Qt.ItemDataRole.UserRole, track)
                
                # Add standalone tracks
                if artist_data.get('tracks'):
                    for track in artist_data.get('tracks', []):
                        track_item = QTreeWidgetItem(artist_item)
                        track_item.setText(0, track.get('title', 'Unknown Track'))
                        track_item.setText(1, artist_name)
                        track_item.setText(2, f"Canción ({service})")
                        
                        # Add duration if available
                        if track.get('duration'):
                            duration_str = self.format_duration(track.get('duration'))
                            track_item.setText(4, duration_str)
                            
                        # Store track information
                        track_item.setData(0, Qt.ItemDataRole.UserRole, track)

                        
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
    
    def format_duration(self, duration):
        """Formats duration into a readable string"""
        if not duration:
            return "Unknown"
            
        try:
            duration = float(duration)
            minutes, seconds = divmod(int(duration), 60)
            hours, minutes = divmod(minutes, 60)
            
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        except (ValueError, TypeError):
            return str(duration)
    
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
        """Adds the selected item to the playback queue."""
        selected_items = self.treeWidget.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            # Get the item type
            item_type = item.text(2).split(' ')[0].lower()  # Extract the basic type
            
            # If it's an album, ask if user wants to add all tracks
            if item_type == "álbum":
                if item.childCount() > 0:  # Album has tracks as children
                    reply = QMessageBox.question(
                        self, 
                        "Agregar Álbum", 
                        f"¿Deseas agregar todo el álbum '{item.text(0)}' a la cola?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        # Add all child tracks
                        for i in range(item.childCount()):
                            child = item.child(i)
                            self.add_item_to_queue(child)
                        continue  # Skip adding the album itself
            
            # If it's a parent item with children (like artist or playlist)
            elif item.childCount() > 0:
                for i in range(item.childCount()):
                    child = item.child(i)
                    self.add_item_to_queue(child)
                continue  # Skip adding the parent itself
            
            # For individual tracks or other items without special handling
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
        spotify_client_id = self.spotify_client_id or os.environ.get("SPOTIFY_CLIENT_ID")
        spotify_client_secret = self.spotify_client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")
        lastfm_api_key = self.lastfm_api_key or os.environ.get("LASTFM_API_KEY")
        
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




    def get_detailed_info(self):
        """
        Get detailed information from the database.
        This method should be implemented in the parent class or passed as a parameter.
        """
        try:
            # Import the database query class
            from base_datos.tools.consultar_items_db import MusicDatabaseQuery
            
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

    def format_artist_info(self, artist_info):
        """Formatea la información del artista en HTML"""
        html = ""
        
        # Biografía
        if artist_info.get('bio'):
            html += "<h3>Biografía</h3>"
            html += f"<p>{self.format_large_text(artist_info['bio'])}</p>"
        
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
        
        return html

    def format_song_info(self, song_info):
        """Formatea la información de la canción en HTML"""
        # Safety check for None
        if song_info is None:
            return "<p>No hay información disponible para esta canción.</p>"
        
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
            else:
                html += f"<p><b>Duración:</b> {duration_seconds}</p>"
        
        # Letra
        if song_info.get('lyrics'):
            html += "<h3>Letra</h3>"
            # Formatear la letra reemplazando saltos de línea por <br>
            lyrics = song_info['lyrics'].replace('\n', '<br>')
            html += f"<p>{self.format_large_text(lyrics)}</p>"
        
        return html


    def format_available_links(self, result_data, additional_links=None):
        """Formatea los enlaces disponibles en HTML"""
        html = "<h3>Enlaces</h3>"
        
        # Track which services we've already displayed to avoid duplicates
        displayed_services = set()
        
        # Enlaces adicionales (de la base de datos)
        if additional_links:
            # Artist links
            if additional_links.get('artist_links'):
                html += "<h4>Enlaces del Artista</h4>"
                for service, url in additional_links['artist_links'].items():
                    if url:
                        service_key = service.lower()
                        html += f"<p><b>{service.capitalize()}:</b> <a href='{url}' target='_blank'>{url}</a></p>"
                        displayed_services.add(service_key)
            
            # Album links
            if additional_links.get('album_links'):
                html += "<h4>Enlaces del Álbum</h4>"
                for service, url in additional_links['album_links'].items():
                    if url:
                        service_key = service.lower()
                        html += f"<p><b>{service.capitalize()}:</b> <a href='{url}' target='_blank'>{url}</a></p>"
                        displayed_services.add(service_key)
            
            # Track links
            if additional_links.get('track_links'):
                html += "<h4>Enlaces de la Canción</h4>"
                for service, url in additional_links['track_links'].items():
                    if url:
                        service_key = service.lower()
                        html += f"<p><b>{service.capitalize()}:</b> <a href='{url}' target='_blank'>{url}</a></p>"
                        displayed_services.add(service_key)
        
        # Enlaces directos en result_data (de la búsqueda)
        html += "<h4>Enlaces de Servicios</h4>"
        links_found = False
        
        # Enlaces directos
        if result_data.get('url'):
            service = result_data.get('source', 'Desconocido')
            service_key = service.lower()
            if service_key not in displayed_services:
                html += f"<p><b>{service.capitalize()}:</b> <a href='{result_data['url']}' target='_blank'>{result_data['url']}</a></p>"
                displayed_services.add(service_key)
                links_found = True
        
        # Enlaces de servicios específicos
        services = ['spotify', 'youtube', 'bandcamp', 'soundcloud', 'lastfm', 'musicbrainz', 'discogs', 'rateyourmusic']
        
        for service in services:
            url_key = f"{service}_url"
            if result_data.get(url_key) and service not in displayed_services:
                html += f"<p><b>{service.capitalize()}:</b> <a href='{result_data[url_key]}' target='_blank'>{result_data[url_key]}</a></p>"
                displayed_services.add(service)
                links_found = True
        
        if not links_found and not additional_links:
            html += "<p>No se encontraron enlaces directos para este elemento.</p>"
        
        return html


    def format_large_text(self, text, max_length=2000):
        """Format large text with a 'Show more' button for readability."""
        if not text or len(text) <= max_length:
            return text
        
        # Truncate text and add a "Show more" button
        short_text = text[:max_length].strip() + "..."
        
        # Create HTML with a button
        html = f"""
        <div id="short-text">{short_text}</div>
        <div id="full-text" style="display:none;">{text}</div>
        <a href="#" onclick="
            document.getElementById('short-text').style.display='none';
            document.getElementById('full-text').style.display='block';
            this.style.display='none';
            return false;
        " style="color: blue; text-decoration: underline;">
            Mostrar texto completo
        </a>
        """
        return html


    def display_wiki_info(self, result_data):
        """Muestra información detallada del elemento en el panel info_wiki de forma asíncrona"""
        try:
            # Verificar que el textEdit existe
            if not hasattr(self, 'info_wiki_textedit') or not self.info_wiki_textedit:
                self.log("Error: No se encontró el widget info_wiki_textedit")
                return
            
            # Verificar datos mínimos
            if not result_data or not isinstance(result_data, dict):
                self.info_wiki_textedit.setHtml("<h2>Error</h2><p>No hay datos válidos para mostrar.</p>")
                return
            
            # Mostrar un mensaje de carga
            loading_html = """
            <div style="text-align: center; margin-top: 50px;">
                <h2>Cargando información...</h2>
                <div class="loader" style="
                    border: 16px solid #f3f3f3;
                    border-radius: 50%;
                    border-top: 16px solid #3498db;
                    width: 120px;
                    height: 120px;
                    animation: spin 2s linear infinite;
                    margin: 20px auto;
                "></div>
                <style>
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
                <p>Obteniendo información detallada...</p>
            </div>
            """
            self.info_wiki_textedit.setHtml(loading_html)
            
            # Cambiar al tab de info_wiki para mostrar la información
            if hasattr(self, 'tabWidget') and self.tabWidget:
                # Buscar el índice del tab info_wiki
                for i in range(self.tabWidget.count()):
                    if self.tabWidget.tabText(i) == "Info Wiki":
                        self.tabWidget.setCurrentIndex(i)
                        break
            
            # Extraer datos básicos del elemento
            item_type = result_data.get('type', '').lower()
            title = result_data.get('title', '')
            artist = result_data.get('artist', '')
            album = result_data.get('album', '')
            
            if not (title or artist):
                self.info_wiki_textedit.setHtml("<h2>Información no disponible</h2><p>No hay suficientes datos para mostrar información detallada.</p>")
                return
            
            # Crear y configurar el worker para carga asíncrona
            worker = InfoLoadWorker(
                item_type=item_type, 
                title=title, 
                artist=artist, 
                album=album,  # Pass album parameter
                db_path=self.db_path, 
                basic_data=result_data  # Pass the basic data to the worker
            )
            
            # Conectar señales
            worker.signals.results.connect(self.process_detailed_results)
            worker.signals.error.connect(self.handle_info_load_error)
            worker.signals.finished.connect(self.on_info_load_finished)
            
            # Initiate the worker
            QThreadPool.globalInstance().start(worker)
            
        except Exception as e:
            self.log(f"Error al preparar carga de información: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            self.info_wiki_textedit.setHtml(f"<h2>Error</h2><p>Se produjo un error al cargar la información: {str(e)}</p>")

    def process_detailed_results(self, results):
        """Process the detailed results from the worker."""
        if results:
            # Handle the results if needed
            self.log(f"Received {len(results)} detailed results")

    def handle_info_load_error(self, error_msg):
        """Handle errors from the info load worker."""
        self.log(f"Info load error: {error_msg}")
        self.info_wiki_textedit.setHtml(f"<h2>Error</h2><p>{error_msg}</p>")


    def on_info_load_finished(self, result, basic_data):
        """Callback when information loading is complete."""
        try:
            item_type = basic_data.get('type', '').lower()
            title = basic_data.get('title', '')
            artist = basic_data.get('artist', '')
            album = basic_data.get('album', '')
            
            # Generate HTML to display the information with enhanced format
            if item_type == 'artist':
                # Only show artist name
                html_content = f"<h2>{artist}</h2>"
            elif item_type == 'album':
                # Show album by artist in one line
                html_content = f"<h2>{title} por {artist}</h2>"
            elif item_type in ['track', 'song']:
                # Show song from album by artist
                album_text = f" del álbum {album}" if album else ""
                html_content = f"<h2>{title}{album_text} por {artist}</h2>"
            else:
                # General format for other types
                html_content = f"<h2>{title}</h2>"
                if artist:
                    html_content += f"<h3>por {artist}</h3>"
            
            html_content += "<hr>"
            
            # Dictionary to store all links found
            all_links = {}
            
            # Special handling for Bandcamp content
            if basic_data.get('source', '').lower() == 'bandcamp':
                if item_type == 'artist':
                    # Show Bandcamp artist info
                    html_content += "<h3>Bandcamp Artist</h3>"
                    
                    # List albums if available
                    if 'albums' in basic_data and basic_data['albums']:
                        html_content += f"<h3>Albums ({len(basic_data['albums'])})</h3>"
                        html_content += "<ul>"
                        for album in basic_data['albums']:
                            album_year = f" ({album.get('year')})" if album.get('year') else ""
                            html_content += f"<li><a href='{album.get('url', '#')}'>{album.get('title', 'Unknown Album')}</a>{album_year}</li>"
                        html_content += "</ul>"
                
                elif item_type == 'album':
                    # Show Bandcamp album info
                    html_content += "<h3>Bandcamp Album</h3>"
                    
                    if basic_data.get('year'):
                        html_content += f"<p><b>Year:</b> {basic_data['year']}</p>"
                    
                    # List tracks if available
                    if 'tracks' in basic_data and basic_data['tracks']:
                        html_content += f"<h3>Tracks ({len(basic_data['tracks'])})</h3>"
                        html_content += "<ol>"
                        for track in basic_data['tracks']:
                            duration_str = self.format_duration(track.get('duration', 0))
                            html_content += f"<li><a href='{track.get('url', '#')}'>{track.get('title', 'Unknown Track')}</a> ({duration_str})</li>"
                        html_content += "</ol>"
                
                elif item_type in ['track', 'song']:
                    # Show Bandcamp track info
                    html_content += "<h3>Bandcamp Track</h3>"
                    
                    if basic_data.get('duration'):
                        duration_str = self.format_duration(basic_data.get('duration', 0))
                        html_content += f"<p><b>Duration:</b> {duration_str}</p>"
                    
                    if basic_data.get('track_number'):
                        html_content += f"<p><b>Track Number:</b> {basic_data['track_number']}</p>"
            
            # Format info according to type
            if item_type == 'artist':
                # Artist data
                if 'artist_info' in result:
                    html_content += self.format_artist_info(result['artist_info'])
                
                # Wikipedia content
                if result.get('wiki_content'):
                    html_content += "<h3>Wikipedia</h3>"
                    html_content += f"<p>{self.format_large_text(result['wiki_content'])}</p>"
                    
                # Genres
                if result.get('genres'):
                    html_content += "<h3>Genres</h3>"
                    html_content += "<ul>"
                    for genre in result['genres']:
                        html_content += f"<li>{genre}</li>"
                    html_content += "</ul>"
                
                # Store links for later display
                if result.get('artist_links'):
                    all_links['artist_links'] = result['artist_links']
                    
                # Update the tree with albums if available
                if result.get('albums'):
                    self.add_artist_albums_to_tree(artist, result['albums'])
                
            elif item_type == 'album':
                # Album data
                if 'album_info' in result:
                    html_content += self.format_album_info(result['album_info'])
                
                # Wikipedia content
                if result.get('wiki_content'):
                    html_content += "<h3>Wikipedia</h3>"
                    html_content += f"<p>{self.format_large_text(result['wiki_content'])}</p>"
                
                # Store links for later display
                if result.get('album_links'):
                    all_links['album_links'] = result['album_links']
                    
                # Update tree with songs if available
                if result.get('album_info') and result['album_info'].get('songs'):
                    self.add_album_songs_to_tree(artist, title, result['album_info']['songs'])
                
            elif item_type in ['track', 'song']:
                # Song data - With None handling for song_info
                if result.get('song_info'):
                    html_content += self.format_song_info(result['song_info'])
                else:
                    html_content += "<p>No detailed song information found.</p>"
                
                # Related album data
                if result.get('album_info'):
                    html_content += "<h3>Album Information</h3>"
                    html_content += self.format_album_info(result['album_info'])
                
                # Store links for later display
                if result.get('track_links'):
                    all_links['track_links'] = result['track_links']
                if result.get('album_links'):
                    all_links['album_links'] = result['album_links']
            
            # Links from active services
            html_content += self.format_available_links(basic_data, all_links)
            
            # Set HTML content
            self.info_wiki_textedit.setHtml(html_content)
            
        except Exception as e:
            self.log(f"Error processing loaded information: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            self.info_wiki_textedit.setHtml(f"<h2>Error</h2><p>An error occurred while processing the information: {str(e)}</p>")


    def add_artist_albums_to_tree(self, artist_name, albums):
        """Añade los álbumes de un artista al árbol de forma jerárquica."""
        try:
            # Verificar que el TreeWidget existe
            if not hasattr(self, 'treeWidget') or not self.treeWidget:
                return
                
            # Buscar si el artista ya está en el árbol
            artist_items = self.treeWidget.findItems(artist_name, Qt.MatchFlag.MatchExactly, 1)  # Columna 1 = artista
            
            artist_item = None
            
            # Si el artista no existe, crearlo
            if not artist_items:
                # Crear un item raíz para el artista
                artist_item = QTreeWidgetItem(self.treeWidget)
                artist_item.setText(0, artist_name)  # Columna 0 = tipo
                artist_item.setText(1, artist_name)  # Columna 1 = nombre
                artist_item.setText(2, "Artista")  # Columna 2 = tipo
                
                # Configurar como expandido
                artist_item.setExpanded(True)
                
                # Aplicar un formato especial
                font = artist_item.font(0)
                font.setBold(True)
                artist_item.setFont(0, font)
                artist_item.setFont(1, font)
                
                # Almacenar datos completos
                artist_data = {
                    'title': artist_name,
                    'artist': artist_name,
                    'type': 'artist'
                }
                artist_item.setData(0, Qt.ItemDataRole.UserRole, artist_data)
            else:
                # Usar el primer item encontrado
                artist_item = artist_items[0]
                
                # Limpiar álbumes antiguos si existieran
                while artist_item.childCount() > 0:
                    artist_item.removeChild(artist_item.child(0))
            
            # Añadir álbumes como hijos
            for album in albums:
                # Extraer datos del álbum según el formato
                if isinstance(album, dict):
                    album_name = album.get('name', '')
                    album_year = album.get('year', '')
                else:
                    # Si es una tupla (resultado de get_artist_albums)
                    album_name = album[0] if len(album) > 0 else ''
                    album_year = album[1] if len(album) > 1 else ''
                
                # Crear item para el álbum
                album_item = QTreeWidgetItem(artist_item)
                album_item.setText(0, album_name)  # Columna 0 = nombre del álbum
                album_item.setText(1, artist_name)  # Columna 1 = artista
                album_item.setText(2, "Álbum")  # Columna 2 = tipo
                
                # Añadir año si existe
                if album_year:
                    album_item.setText(3, str(album_year))  # Columna 3 = año
                
                # Almacenar datos completos
                album_data = {
                    'title': album_name,
                    'artist': artist_name,
                    'year': album_year,
                    'type': 'album'
                }
                album_item.setData(0, Qt.ItemDataRole.UserRole, album_data)
                
            self.log(f"Agregados {len(albums)} álbumes al árbol para el artista {artist_name}")
            
        except Exception as e:
            self.log(f"Error al añadir álbumes al árbol: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

    def add_album_songs_to_tree(self, artist_name, album_name, songs):
        """Añade las canciones de un álbum al árbol de forma jerárquica."""
        try:
            # Verificar que el TreeWidget existe
            if not hasattr(self, 'treeWidget') or not self.treeWidget:
                return
                
            # Buscar si el álbum ya está en el árbol
            album_found = False
            album_item = None
            
            # Primero, buscar si existe el artista
            artist_items = self.treeWidget.findItems(artist_name, Qt.MatchFlag.MatchExactly, 1)  # Columna 1 = artista
            
            if artist_items:
                # Buscar el álbum entre los hijos del artista
                for i in range(artist_items[0].childCount()):
                    child = artist_items[0].child(i)
                    if child.text(0) == album_name:
                        album_item = child
                        album_found = True
                        break
            
            # Si no se encontró, crear la estructura artista -> álbum
            if not album_found:
                # Crear artista si no existe
                if not artist_items:
                    artist_item = QTreeWidgetItem(self.treeWidget)
                    artist_item.setText(0, artist_name)
                    artist_item.setText(1, artist_name)
                    artist_item.setText(2, "Artista")
                    
                    # Configurar formato
                    font = artist_item.font(0)
                    font.setBold(True)
                    artist_item.setFont(0, font)
                    artist_item.setFont(1, font)
                    
                    # Almacenar datos
                    artist_data = {
                        'title': artist_name,
                        'artist': artist_name,
                        'type': 'artist'
                    }
                    artist_item.setData(0, Qt.ItemDataRole.UserRole, artist_data)
                else:
                    artist_item = artist_items[0]
                
                # Crear álbum como hijo del artista
                album_item = QTreeWidgetItem(artist_item)
                album_item.setText(0, album_name)
                album_item.setText(1, artist_name)
                album_item.setText(2, "Álbum")
                
                # Almacenar datos
                album_data = {
                    'title': album_name,
                    'artist': artist_name,
                    'type': 'album'
                }
                album_item.setData(0, Qt.ItemDataRole.UserRole, album_data)
            else:
                # Limpiar canciones antiguas si existieran
                while album_item.childCount() > 0:
                    album_item.removeChild(album_item.child(0))
            
            # Expandir artista y álbum
            album_item.parent().setExpanded(True)
            
            # Añadir canciones como hijos del álbum
            for song in songs:
                # Extraer datos de la canción
                if isinstance(song, dict):
                    song_title = song.get('title', '')
                    track_number = song.get('track_number', '')
                    duration = song.get('duration', '')
                else:
                    # Si es tupla o lista
                    song_title = song[0] if len(song) > 0 else ''
                    track_number = song[1] if len(song) > 1 else ''
                    duration = song[2] if len(song) > 2 else ''
                
                # Crear item para la canción
                song_item = QTreeWidgetItem(album_item)
                song_item.setText(0, song_title)
                song_item.setText(1, artist_name)
                song_item.setText(2, "Canción")
                
                # Añadir número de pista y duración si existen
                if track_number:
                    song_item.setText(3, str(track_number))
                
                if duration:
                    # Formatear duración si está en segundos
                    if isinstance(duration, (int, float)):
                        minutes = int(duration // 60)
                        seconds = int(duration % 60)
                        song_item.setText(4, f"{minutes}:{seconds:02d}")
                    else:
                        song_item.setText(4, str(duration))
                
                # Almacenar datos completos
                song_data = {
                    'title': song_title,
                    'artist': artist_name,
                    'album': album_name,
                    'track_number': track_number,
                    'duration': duration,
                    'type': 'track'
                }
                song_item.setData(0, Qt.ItemDataRole.UserRole, song_data)
            
            self.log(f"Agregadas {len(songs)} canciones al árbol para el álbum {album_name}")
            
        except Exception as e:
            self.log(f"Error al añadir canciones al árbol: {str(e)}")
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