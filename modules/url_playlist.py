# TODO: Crear modo alternativo a dotenv


import os
import spotipy
import re
import requests
from bs4 import BeautifulSoup
import urllib3
import sys
import json
import subprocess
import tempfile
import logging
import traceback
import base64
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QInputDialog, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QTextEdit, QTabWidget, QMessageBox, QMenu, QDialogButtonBox, QLabel,
    QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy, QApplication, QDialog, QComboBox, QProgressDialog
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal, QUrl, QRunnable, pyqtSlot, QObject, QThreadPool, QSize
from PyQt6.QtGui import QIcon, QMovie



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
            
            # Get the database links if available
            db_links = getattr(self, 'db_links', {})
            
            # Track which services we've already found in the database
            db_services_found = set()
            db_results = []
            
            # Check if we already have service-specific links in the database
            if db_links:
                # Process each entity type for links
                for entity_type in ['artists', 'albums', 'tracks']:
                    for item_key, item_data in db_links.get(entity_type, {}).items():
                        # Get all links from this item
                        links = item_data.get('links', {})
                        
                        for service, url in links.items():
                            service_lower = service.lower()
                            if service_lower in self.services and url:
                                # Add to services found
                                db_services_found.add(service_lower)
                                
                                # Create a result item for this database link
                                result_item = {
                                    "source": service_lower,
                                    "title": item_data.get('title', ''),
                                    "artist": item_data.get('artist', ''),
                                    "url": url,
                                    "type": item_data.get('type', entity_type[:-1]),  # Remove 's' from entity_type
                                    "from_database": True
                                }
                                
                                # Add additional data
                                if entity_type == 'albums' and 'year' in item_data:
                                    result_item['year'] = item_data['year']
                                elif entity_type == 'tracks':
                                    if 'album' in item_data:
                                        result_item['album'] = item_data['album']
                                    if 'track_number' in item_data:
                                        result_item['track_number'] = item_data['track_number']
                                    if 'duration' in item_data:
                                        result_item['duration'] = item_data['duration']
                                
                                db_results.append(result_item)
                
                # Add all db results to the final results list
                if db_results:
                    self.log(f"Found {len(db_results)} results in database")
                    results.extend(db_results)
            
            # Log database findings
            self.log(f"Already have links in database for: {db_services_found}")
            
            # Filter services that don't have links in the database
            services_to_search = [s for s in self.services if s not in db_services_found]
            self.log(f"Will search additional services: {services_to_search}")
            
            # Continue with service searches for those not found in database
            for service in services_to_search:
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
            
            # Emit results
            self.signals.results.emit(results)
            self.signals.finished.emit({}, {})
        
        except Exception as e:
            error_msg = f"Error in search: {str(e)}"
            self.log(error_msg)
            self.signals.error.emit(error_msg)
            # Emit finished with error information
            self.signals.finished.emit({"error": str(e)}, {})

    def search_bandcamp(self, query, search_type):
        """Searches on Bandcamp with enhanced album and track support."""
        try:
            # Check database links
            db_links = getattr(self, 'db_links', {})
            bandcamp_results = []
            
            # Log progress
            self.log(f"Buscando en Bandcamp: {query} (tipo: {search_type})")
            
            # Extract artist and title components
            parts = query.split(" - ", 1)
            artist = parts[0].strip() if len(parts) > 1 else ""
            title = parts[1].strip() if len(parts) > 1 else query.strip()
            
            # Import module for external search if needed
            from base_datos.enlaces_artista_album import MusicLinksManager
            
            config = {
                'db_path': self.db_path,
                'rate_limit': 1.0,
                'disable_services': ['musicbrainz', 'discogs', 'youtube', 'rateyourmusic'],
                'log_level': 'WARNING'
            }
            
            # Try to create the manager object
            try:
                manager = MusicLinksManager(config)
                self.log("MusicLinksManager initialized successfully")
            except Exception as e:
                self.log(f"Error initializing MusicLinksManager: {str(e)}")
                manager = None
            
            # Search in database first
            db_result = self._search_bandcamp_in_db(artist, title, db_links, search_type)
            if db_result:
                self.log(f"Found Bandcamp result in database: {db_result['title']}")
                bandcamp_results.append(db_result)
            
            # If nothing found in database and we have a manager, try external search
            if not bandcamp_results and manager:
                self.log("No database results found, attempting external search...")
                if search_type.lower() in ['artist', 'artista', 'all']:
                    # Try to get artist URL
                    artist_name = artist or title
                    try:
                        artist_url = manager._get_bandcamp_artist_url(artist_name)
                        if artist_url:
                            self.log(f"Found Bandcamp artist URL: {artist_url}")
                            artist_result = {
                                "source": "bandcamp",
                                "title": artist_name,
                                "artist": artist_name,
                                "url": artist_url,
                                "type": "artist"
                            }
                            
                            # Get albums
                            try:
                                albums = self.get_bandcamp_artist_albums(artist_url)
                                if albums:
                                    self.log(f"Found {len(albums)} albums for artist")
                                    # For each album, get tracks
                                    for album in albums:
                                        album_url = album.get('url')
                                        if album_url:
                                            try:
                                                tracks = self.get_bandcamp_album_tracks(album_url)
                                                if tracks:
                                                    album['tracks'] = tracks
                                                    self.log(f"Added {len(tracks)} tracks to album {album['title']}")
                                            except Exception as e:
                                                self.log(f"Error getting tracks for album {album['title']}: {str(e)}")
                                    
                                    artist_result['albums'] = albums
                            except Exception as e:
                                self.log(f"Error getting albums for artist: {str(e)}")
                            
                            bandcamp_results.append(artist_result)
                    except Exception as e:
                        self.log(f"Error getting Bandcamp artist URL: {str(e)}")
                
                elif search_type.lower() in ['album', 'álbum', 'all']:
                    try:
                        album_url = manager._get_bandcamp_album_url(artist, title)
                        if album_url:
                            self.log(f"Found Bandcamp album URL: {album_url}")
                            
                            # Extract artist from URL if needed
                            artist_name = artist or self.extract_bandcamp_artist_from_url(album_url) or "Unknown Artist"
                            album_name = title or self.extract_bandcamp_album_from_url(album_url)
                            
                            album_result = {
                                "source": "bandcamp",
                                "title": album_name,
                                "artist": artist_name,
                                "url": album_url,
                                "type": "album"
                            }
                            
                            # Get tracks
                            try:
                                tracks = self.get_bandcamp_album_tracks(album_url)
                                if tracks:
                                    album_result['tracks'] = tracks
                                    self.log(f"Added {len(tracks)} tracks to album")
                            except Exception as e:
                                self.log(f"Error getting tracks for album: {str(e)}")
                            
                            bandcamp_results.append(album_result)
                    except Exception as e:
                        self.log(f"Error getting Bandcamp album URL: {str(e)}")
            
            return bandcamp_results
                
        except Exception as e:
            self.log(f"Error in Bandcamp search: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return []

  
            
    def _find_parent_album_url(self, track_data):
        """Find the URL of the parent album for a track"""
        try:
            album_name = track_data.get('album')
            artist_name = track_data.get('artist')
            
            if not album_name or not artist_name:
                return None
                
            # Search the tree for matching album
            for i in range(self.treeWidget.topLevelItemCount()):
                top_item = self.treeWidget.topLevelItem(i)
                
                # Search child items (artists)
                for j in range(top_item.childCount()):
                    artist_item = top_item.child(j)
                    
                    # Check if this is the right artist
                    if artist_item.text(1).lower() == artist_name.lower():
                        # Search for the album
                        for k in range(artist_item.childCount()):
                            album_item = artist_item.child(k)
                            
                            # If this is an album and the name matches
                            if album_item.text(2).lower() == "álbum" and album_item.text(0).lower() == album_name.lower():
                                # Get album data
                                album_data = album_item.data(0, Qt.ItemDataRole.UserRole)
                                if isinstance(album_data, dict) and album_data.get('url'):
                                    return album_data.get('url')
            
            return None
        except Exception as e:
            self.log(f"Error finding parent album URL: {str(e)}")
            return None


    def _search_bandcamp_in_db(self, artist, title, db_links, search_type):
        """Helper method to search Bandcamp info in database."""
        try:
            # Search based on type
            if search_type.lower() in ['artist', 'artista', 'all']:
                # If we have an artist name, search for it
                artist_name = artist or title
                
                for db_artist_name, artist_data in db_links.get('artists', {}).items():
                    if db_artist_name.lower() == artist_name.lower() or artist_name.lower() in db_artist_name.lower():
                        # Check for Bandcamp link
                        bandcamp_url = None
                        if 'links' in artist_data and 'bandcamp' in artist_data['links']:
                            bandcamp_url = artist_data['links']['bandcamp']
                        elif 'bandcamp_url' in artist_data:
                            bandcamp_url = artist_data['bandcamp_url']
                        
                        if bandcamp_url:
                            # Create artist result
                            result = {
                                "source": "bandcamp",
                                "title": db_artist_name,
                                "artist": db_artist_name,
                                "url": bandcamp_url,
                                "type": "artist",
                                "from_database": True
                            }
                            
                            # Add albums if available
                            if 'albums' in artist_data and artist_data['albums']:
                                albums = []
                                for album in artist_data['albums']:
                                    album_name = album.get('title', album.get('name', ''))
                                    album_bandcamp_url = None
                                    
                                    if 'links' in album and 'bandcamp' in album['links']:
                                        album_bandcamp_url = album['links']['bandcamp']
                                    elif 'bandcamp_url' in album:
                                        album_bandcamp_url = album['bandcamp_url']
                                    
                                    if album_bandcamp_url:
                                        # Create album entry
                                        album_entry = {
                                            "source": "bandcamp",
                                            "title": album_name,
                                            "artist": db_artist_name,
                                            "url": album_bandcamp_url,
                                            "type": "album",
                                            "year": album.get('year'),
                                            "from_database": True
                                        }
                                        
                                        # Get tracks if available
                                        if 'tracks' in album and album['tracks']:
                                            tracks = []
                                            for track in album['tracks']:
                                                track_entry = {
                                                    "source": "bandcamp",
                                                    "title": track.get('title', ''),
                                                    "artist": db_artist_name,
                                                    "album": album_name,
                                                    "type": "track",
                                                    "track_number": track.get('track_number'),
                                                    "duration": track.get('duration'),
                                                    "from_database": True
                                                }
                                                
                                                # Add track URL if available
                                                track_bandcamp_url = None
                                                if 'links' in track and 'bandcamp' in track['links']:
                                                    track_bandcamp_url = track['links']['bandcamp']
                                                elif 'bandcamp_url' in track:
                                                    track_bandcamp_url = track['bandcamp_url']
                                                
                                                if track_bandcamp_url:
                                                    track_entry['url'] = track_bandcamp_url
                                                
                                                tracks.append(track_entry)
                                            
                                            album_entry['tracks'] = tracks
                                        else:
                                            # Try to get tracks from Bandcamp directly
                                            try:
                                                tracks = self.get_bandcamp_album_tracks(album_bandcamp_url)
                                                if tracks:
                                                    album_entry['tracks'] = tracks
                                            except Exception as e:
                                                self.log(f"Error getting tracks for album: {str(e)}")
                                        
                                        albums.append(album_entry)
                                
                                if albums:
                                    result['albums'] = albums
                            
                            return result
            
            elif search_type.lower() in ['album', 'álbum', 'all']:
                # If we have artist and title, search for album
                if artist:
                    album_key = f"{artist} - {title}"
                    if album_key in db_links.get('albums', {}):
                        album_data = db_links['albums'][album_key]
                        
                        # Check for Bandcamp link
                        bandcamp_url = None
                        if 'links' in album_data and 'bandcamp' in album_data['links']:
                            bandcamp_url = album_data['links']['bandcamp']
                        elif 'bandcamp_url' in album_data:
                            bandcamp_url = album_data['bandcamp_url']
                        
                        if bandcamp_url:
                            # Create album result
                            result = {
                                "source": "bandcamp",
                                "title": title,
                                "artist": artist,
                                "url": bandcamp_url,
                                "type": "album",
                                "year": album_data.get('year'),
                                "from_database": True
                            }
                            
                            # Get tracks
                            if 'tracks' in album_data and album_data['tracks']:
                                tracks = []
                                for track in album_data['tracks']:
                                    track_entry = {
                                        "source": "bandcamp",
                                        "title": track.get('title', ''),
                                        "artist": artist,
                                        "album": title,
                                        "type": "track",
                                        "track_number": track.get('track_number'),
                                        "duration": track.get('duration'),
                                        "from_database": True
                                    }
                                    
                                    # Add track URL if available
                                    track_bandcamp_url = None
                                    if 'links' in track and 'bandcamp' in track['links']:
                                        track_bandcamp_url = track['links']['bandcamp']
                                    elif 'bandcamp_url' in track:
                                        track_bandcamp_url = track['bandcamp_url']
                                    
                                    if track_bandcamp_url:
                                        track_entry['url'] = track_bandcamp_url
                                    
                                    tracks.append(track_entry)
                                
                                result['tracks'] = tracks
                            else:
                                # Try to get tracks from Bandcamp directly
                                try:
                                    tracks = self.get_bandcamp_album_tracks(bandcamp_url)
                                    if tracks:
                                        result['tracks'] = tracks
                                except Exception as e:
                                    self.log(f"Error getting tracks for album: {str(e)}")
                            
                            return result
            
            # If we reach here, nothing was found
            return None
            
        except Exception as e:
            self.log(f"Error searching Bandcamp in database: {str(e)}")
            return None



    def get_bandcamp_artist_albums(self, artist_url):
        """Obtiene los álbumes de un artista de Bandcamp."""
        if not artist_url:
            return []
        
        try:
            # Extraer nombre del artista de la URL
            artist_name = self.extract_bandcamp_artist_from_url(artist_url)
            self.log(f"Obteniendo álbumes para: {artist_name}")
            
            # Usar yt-dlp para obtener información
            command = [
                "yt-dlp", 
                "--flat-playlist",
                "--dump-json",
                artist_url
            ]
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if stderr and not stdout:
                self.log(f"Error al obtener álbumes: {stderr}")
                return []
            
            albums = []
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Filtrar solo entradas que sean álbumes
                    webpage_url = data.get('webpage_url', '')
                    if '/album/' in webpage_url:
                        # Extraer nombre del álbum de la URL
                        album_name = self.extract_bandcamp_album_from_url(webpage_url)
                        
                        album = {
                            "source": "bandcamp",
                            "title": album_name,
                            "artist": artist_name,
                            "url": webpage_url,
                            "type": "album"
                        }
                        
                        # Añadir el año si está disponible
                        if data.get('upload_date') and len(data.get('upload_date', '')) >= 4:
                            album["year"] = data.get('upload_date')[:4]
                        
                        self.log(f"Álbum encontrado: {album_name}")
                        albums.append(album)
                except json.JSONDecodeError:
                    continue
            
            self.log(f"Total de álbumes encontrados: {len(albums)}")
            return albums
                
        except Exception as e:
            self.log(f"Error en get_bandcamp_artist_albums: {e}")
            import traceback
            self.log(traceback.format_exc())
            return []


    def _extract_bandcamp_album_year(self, description):
        """Extrae el año de lanzamiento de la descripción de un álbum de Bandcamp."""
        try:
            # Patrones comunes en las descripciones de Bandcamp
            patterns = [
                r'released (\w+ \d{1,2}, (\d{4}))',
                r'released: (\w+ \d{1,2}, (\d{4}))',
                r'released in (\d{4})',
                r'released (\d{4})',
                r'(\d{4}) release',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match and len(match.groups()) >= 2 and match.group(2):
                    return match.group(2)
                elif match and match.group(1) and match.group(1).isdigit():
                    return match.group(1)
                    
            return None
        except Exception:
            return None


    def _parse_query(self, query):
        """Parse a query into artist and title components."""
        parts = query.split(" - ", 1)
        if len(parts) > 1:
            return parts[0].strip(), parts[1].strip()
        return None, query.strip()

    def _get_bandcamp_artist_from_db(self, artist_name, db_links):
        """Extract Bandcamp artist data from database."""
        if not artist_name or 'artists' not in db_links:
            return None
            
        # Look for exact match first, then partial match
        for db_artist_name, artist_data in db_links.get('artists', {}).items():
            if (artist_name.lower() == db_artist_name.lower() or 
                artist_name.lower() in db_artist_name.lower()):
                
                # Check if Bandcamp URL exists
                bandcamp_url = self._extract_service_url(artist_data, 'bandcamp')
                if not bandcamp_url:
                    continue
                    
                # Create artist result
                result = {
                    "source": "bandcamp",
                    "title": db_artist_name,
                    "artist": db_artist_name,
                    "url": bandcamp_url,
                    "type": "artist",
                    "from_database": True
                }
                
                # Add albums if available
                if 'albums' in artist_data and artist_data['albums']:
                    result['albums'] = self._extract_artist_albums(artist_data['albums'], db_artist_name)
                    
                return result
        
        return None

    def _get_bandcamp_album_from_db(self, artist_name, album_name, db_links):
        """Extract Bandcamp album data from database."""
        if not album_name or 'albums' not in db_links:
            return None
        
        # Try with artist+album key first if artist is provided
        if artist_name:
            album_key = f"{artist_name} - {album_name}"
            if album_key in db_links.get('albums', {}):
                album_data = db_links['albums'][album_key]
                bandcamp_url = self._extract_service_url(album_data, 'bandcamp')
                
                if bandcamp_url:
                    return self._create_album_result(album_data, bandcamp_url)
        
        # Otherwise search all albums for a match on album title
        for album_key, album_data in db_links.get('albums', {}).items():
            if album_data['title'].lower() == album_name.lower():
                bandcamp_url = self._extract_service_url(album_data, 'bandcamp')
                
                if bandcamp_url:
                    return self._create_album_result(album_data, bandcamp_url)
        
        return None

    def _extract_service_url(self, data, service):
        """Extract service URL from data with various possible structures."""
        if 'links' in data and service in data['links']:
            return data['links'][service]
        elif f'{service}_url' in data:
            return data[f'{service}_url']
        return None

    def _create_album_result(self, album_data, bandcamp_url):
        """Create a structured album result from album data."""
        result = {
            "source": "bandcamp",
            "title": album_data['title'],
            "artist": album_data['artist'],
            "url": bandcamp_url,
            "type": "album",
            "year": album_data.get('year'),
            "from_database": True
        }
        
        # Add tracks if available
        if 'tracks' in album_data and album_data['tracks']:
            result['tracks'] = []
            for track in album_data['tracks']:
                track_result = {
                    "source": "bandcamp",
                    "title": track['title'],
                    "artist": album_data['artist'],
                    "album": album_data['title'],
                    "type": "track",
                    "track_number": track.get('track_number'),
                    "duration": track.get('duration'),
                    "from_database": True
                }
                
                # Add track URL if available
                track_url = self._extract_service_url(track, 'bandcamp')
                if track_url:
                    track_result['url'] = track_url
                
                result['tracks'].append(track_result)
        
        return result

    def _get_bandcamp_track_from_db(self, artist_name, track_name, db_links):
        """Extract Bandcamp track data from database."""
        if not track_name or 'tracks' not in db_links:
            return None
        
        # Try with artist+track key first if artist is provided
        if artist_name:
            track_key = f"{artist_name} - {track_name}"
            if track_key in db_links.get('tracks', {}):
                track_data = db_links['tracks'][track_key]
                bandcamp_url = self._extract_service_url(track_data, 'bandcamp')
                
                if bandcamp_url:
                    return {
                        "source": "bandcamp",
                        "title": track_data['title'],
                        "artist": track_data['artist'],
                        "album": track_data.get('album', ''),
                        "url": bandcamp_url,
                        "type": "track",
                        "track_number": track_data.get('track_number'),
                        "duration": track_data.get('duration'),
                        "from_database": True
                    }
        
        # Search all tracks for a match on track title
        for track_key, track_data in db_links.get('tracks', {}).items():
            if track_data['title'].lower() == track_name.lower():
                bandcamp_url = self._extract_service_url(track_data, 'bandcamp')
                
                if bandcamp_url:
                    return {
                        "source": "bandcamp",
                        "title": track_data['title'],
                        "artist": track_data['artist'],
                        "album": track_data.get('album', ''),
                        "url": bandcamp_url,
                        "type": "track",
                        "track_number": track_data.get('track_number'),
                        "duration": track_data.get('duration'),
                        "from_database": True
                    }
        
        return None


    def get_bandcamp_album_tracks(self, album_url):
        """Obtiene las pistas de un álbum de Bandcamp."""
        if not album_url:
            return []
        
        self.log(f"Obteniendo pistas para álbum: {album_url}")
        
        try:
            # Extraer información básica del álbum y artista
            artist_name = self.extract_bandcamp_artist_from_url(album_url)
            album_name = self.extract_bandcamp_album_from_url(album_url)
            
            # Usar yt-dlp para obtener información
            command = [
                "yt-dlp",
                "--flat-playlist",
                "--dump-single-json",  # Obtener toda la información en un solo JSON
                album_url
            ]
            
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Error de yt-dlp: {stderr}")
                return []
            
            if not stdout:
                self.log("Sin respuesta de yt-dlp")
                return []
            
            # Procesar JSON
            try:
                data = json.loads(stdout)
                tracks = []
                
                # Procesar las entradas que son pistas
                if 'entries' in data:
                    self.log(f"Encontradas {len(data['entries'])} entradas en el álbum")
                    for entry in data['entries']:
                        # Skip the main album entry
                        if entry.get('webpage_url') == album_url:
                            continue
                        
                        # Get track URL - use track-specific URL if available, otherwise use album URL
                        track_url = entry.get('webpage_url', '')
                        if not track_url:
                            track_url = album_url
                            self.log(f"Using album URL for track: {entry.get('title', 'Unknown Track')}")
                        
                        # Get track number if available
                        track_number = None
                        if 'track_number' in entry:
                            track_number = entry['track_number']
                        else:
                            # Try to extract from track title (e.g., "1. Track Name")
                            title = entry.get('title', '')
                            match = re.match(r'^(\d+)[\.:\)-]?\s+(.+)$', title)
                            if match:
                                track_number = match.group(1)
                        
                        # Create track object
                        track = {
                            "source": "bandcamp",
                            "title": entry.get('title', 'Unknown Track'),
                            "artist": artist_name,
                            "album": album_name,
                            "url": entry.get('webpage_url', album_url),  # Use track URL if available, otherwise album URL
                            "type": "track",
                            "track_number": track_number,
                            "duration": entry.get('duration')
                        }
                        
                        tracks.append(track)
                    
                    self.log(f"Procesadas {len(tracks)} pistas para el álbum {album_name}")
                    return tracks
                else:
                    self.log("No se encontraron pistas en la respuesta")
                    return []
                    
            except json.JSONDecodeError as e:
                self.log(f"Error parseando JSON: {e}")
                return []
                
        except Exception as e:
            self.log(f"Error en get_bandcamp_album_tracks: {e}")
            import traceback
            self.log(traceback.format_exc())
            return []

    def _search_bandcamp_external(self, artist_name, query, search_type):
        """Fallback method to search Bandcamp via external API."""
        # This would be a simplified version of your existing external search
        # Only used when database search fails
        try:
            # Create configuration for external search
            from base_datos.enlaces_artista_album import MusicLinksManager
            
            config = {
                'db_path': self.db_path,
                'rate_limit': 1.0,
                'disable_services': ['musicbrainz', 'discogs', 'youtube', 'rateyourmusic']
            }
            
            manager = MusicLinksManager(config)
            result = None
            
            # Perform search based on type
            if search_type.lower() in ['artist', 'artista']:
                artist_url = manager._get_bandcamp_artist_url(artist_name or query)
                if artist_url:
                    result = {
                        "source": "bandcamp",
                        "title": artist_name or query,
                        "artist": artist_name or query,
                        "url": artist_url,
                        "type": "artist"
                    }
                    # You could add fetching albums here if needed
                    
            elif search_type.lower() in ['album', 'álbum']:
                album_url = manager._get_bandcamp_album_url(artist_name or "", query)
                if album_url:
                    result = {
                        "source": "bandcamp",
                        "title": query,
                        "artist": artist_name or self.extract_bandcamp_artist_from_url(album_url) or "Unknown Artist",
                        "url": album_url,
                        "type": "album"
                    }
                    # You could add fetching tracks here if needed
                    
            return result
            
        except Exception as e:
            self.log(f"Error in external Bandcamp search: {str(e)}")
            return None

    def extract_bandcamp_artist_from_url(self, url):
        """Extrae el nombre del artista de una URL de Bandcamp."""
        try:
            # Patrón estándar: https://artista.bandcamp.com/...
            match = re.search(r'https?://([^.]+)\.bandcamp\.com', url)
            if match:
                artist_slug = match.group(1)
                # Simplemente reemplazar guiones por espacios y capitalizar
                artist_name = artist_slug.replace('-', ' ').title()
                self.log(f"Artista extraído de URL: {artist_name}")
                return artist_name
            
            return "Unknown Artist"
        except Exception as e:
            self.log(f"Error al extraer artista de URL: {str(e)}")
            return "Unknown Artist"

    def extract_bandcamp_album_from_url(self, url):
        """Extrae el nombre del álbum de una URL de Bandcamp."""
        try:
            # Patrón para álbumes: /album/nombre-album
            match = re.search(r'/album/([^/?&#]+)', url)
            if match:
                album_slug = match.group(1)
                
                # Quitar sufijos comunes si existen
                if '-luxus' in album_slug:
                    album_slug = album_slug.split('-luxus')[0]
                    
                # Reemplazar guiones por espacios y capitalizar cada palabra
                album_name = ' '.join(word.capitalize() for word in album_slug.replace('-', ' ').split())
                
                self.log(f"Álbum extraído de URL: {album_name}")
                return album_name
            
            return "Unknown Album"
        except Exception as e:
            self.log(f"Error al extraer álbum de URL: {str(e)}")
            return "Unknown Album"





    def search_spotify(self, query, search_type):
        """Searches on Spotify using existing module and database links if available."""
        try:
            # Check if we have database links for this query
            db_links = getattr(self, 'db_links', {})
            results = []
            
            # Import the necessary modules
            from base_datos.enlaces_canciones_spot_lastfm import MusicLinkUpdater
            from base_datos.enlaces_artista_album import MusicLinksManager
                
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




    def search_lastfm(self, query, search_type):
        """Searches on Last.fm using existing module and database links if available."""
        try:
            # Check if we have database links for this query
            db_links = getattr(self, 'db_links', {})
            results = []
            
            # Import the existing module
            from base_datos.enlaces_artista_album import MusicLinksManager
            
            # Get API credentials
            lastfm_api_key = self.lastfm_api_key
            lastfm_user = self.lastfm_user
            
            if not lastfm_api_key:
                self.log("Last.fm API key not available")
                return []
            
            # Set up configuration
            config = {
                'db_path': self.db_path,
                'lastfm_api_key': lastfm_api_key,
                'lastfm_user': lastfm_user,
                'disable_services': ['musicbrainz', 'discogs', 'youtube', 'spotify', 'bandcamp', 'rateyourmusic']
            }
            
            # Check based on search type
            if search_type.lower() in ['artist', 'artista']:
                # Check if we have this artist in database
                artist_found = False
                
                for artist_name, artist_data in db_links.get('artists', {}).items():
                    # Check if artist name matches
                    if artist_name.lower() == query.lower() or query.lower() in artist_name.lower():
                        # Look for lastfm URL in links or direct field
                        lastfm_url = None
                        
                        if 'links' in artist_data and 'lastfm' in artist_data['links']:
                            lastfm_url = artist_data['links']['lastfm']
                        elif 'lastfm_url' in artist_data:
                            lastfm_url = artist_data['lastfm_url']
                        
                        if lastfm_url:
                            results.append({
                                "source": "lastfm",
                                "title": artist_name,
                                "artist": artist_name,
                                "url": lastfm_url,
                                "type": "artist",
                                "from_database": True
                            })
                            
                            # Add bio and tags if available
                            if 'bio' in artist_data:
                                results[-1]['bio'] = artist_data['bio']
                            
                            if 'tags' in artist_data:
                                results[-1]['tags'] = artist_data['tags']
                            
                            artist_found = True
                            self.log(f"Found artist on Last.fm from database: {artist_name}")
                            break
                
                # If not found in database, search via API
                if not artist_found:
                    manager = MusicLinksManager(config)
                    
                    # Get artist information
                    lastfm_result = manager._get_lastfm_artist_bio(query)
                    
                    if lastfm_result and lastfm_result[0]:  # [0] is the URL
                        artist_url = lastfm_result[0]
                        
                        result = {
                            "source": "lastfm",
                            "title": query,
                            "artist": query,
                            "url": artist_url,
                            "type": "artist"
                        }
                        
                        # Add bio, similar artists, and tags if available
                        if len(lastfm_result) > 1 and lastfm_result[1]:
                            result['bio'] = lastfm_result[1]
                        
                        if len(lastfm_result) > 2 and lastfm_result[2]:
                            result['similar_artists'] = lastfm_result[2]
                        
                        if len(lastfm_result) > 3 and lastfm_result[3]:
                            result['tags'] = lastfm_result[3]
                        
                        results.append(result)
                        self.log(f"Found artist on Last.fm: {query}")
            
            elif search_type.lower() in ['album', 'álbum']:
                # Check if format is "artist - album"
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
                        
                        # Look for lastfm URL in links or direct field
                        lastfm_url = None
                        
                        if 'links' in album_data and 'lastfm' in album_data['links']:
                            lastfm_url = album_data['links']['lastfm']
                        elif 'lastfm_url' in album_data:
                            lastfm_url = album_data['lastfm_url']
                        
                        if lastfm_url:
                            results.append({
                                "source": "lastfm",
                                "title": album,
                                "artist": artist,
                                "url": lastfm_url,
                                "type": "album",
                                "from_database": True
                            })
                            album_found = True
                            self.log(f"Found album on Last.fm from database: {album} by {artist}")
                
                # If not found with artist-album, check all albums
                if not album_found:
                    for album_key, album_data in db_links.get('albums', {}).items():
                        # Check if album title matches
                        if album_data['title'].lower() == album.lower():
                            # Look for lastfm URL in links or direct field
                            lastfm_url = None
                            
                            if 'links' in album_data and 'lastfm' in album_data['links']:
                                lastfm_url = album_data['links']['lastfm']
                            elif 'lastfm_url' in album_data:
                                lastfm_url = album_data['lastfm_url']
                            
                            if lastfm_url:
                                results.append({
                                    "source": "lastfm",
                                    "title": album_data['title'],
                                    "artist": album_data['artist'],
                                    "url": lastfm_url,
                                    "type": "album",
                                    "from_database": True
                                })
                                album_found = True
                                self.log(f"Found album on Last.fm from database: {album_data['title']} by {album_data['artist']}")
                                break
                
                # If not found in database, search via API
                if not album_found and artist:
                    manager = MusicLinksManager(config)
                    
                    # Get album URL
                    album_url = manager._get_lastfm_album_url(artist, album)
                    
                    if album_url:
                        results.append({
                            "source": "lastfm",
                            "title": album,
                            "artist": artist,
                            "url": album_url,
                            "type": "album"
                        })
                        self.log(f"Found album on Last.fm: {album} by {artist}")
            
            else:
                # General search or track search
                # First check if query is in "artist - title" format
                parts = query.split(" - ", 1)
                artist = parts[0] if len(parts) > 1 else ""
                title = parts[1] if len(parts) > 1 else query
                
                # Try artist first (if query is just an artist name)
                if not ' - ' in query:
                    # Check all artists
                    for artist_name, artist_data in db_links.get('artists', {}).items():
                        # Check if artist name matches
                        if artist_name.lower() == query.lower() or query.lower() in artist_name.lower():
                            # Look for lastfm URL in links or direct field
                            lastfm_url = None
                            
                            if 'links' in artist_data and 'lastfm' in artist_data['links']:
                                lastfm_url = artist_data['links']['lastfm']
                            elif 'lastfm_url' in artist_data:
                                lastfm_url = artist_data['lastfm_url']
                            
                            if lastfm_url:
                                results.append({
                                    "source": "lastfm",
                                    "title": artist_name,
                                    "artist": artist_name,
                                    "url": lastfm_url,
                                    "type": "artist",
                                    "from_database": True
                                })
                                self.log(f"Found artist on Last.fm from database: {artist_name}")
                                break
                
                # If there's an artist and title, try as album
                if artist and title:
                    album_key = f"{artist} - {title}"
                    
                    # Check if this might be an album
                    if album_key in db_links.get('albums', {}):
                        album_data = db_links['albums'][album_key]
                        
                        # Look for lastfm URL in links or direct field
                        lastfm_url = None
                        
                        if 'links' in album_data and 'lastfm' in album_data['links']:
                            lastfm_url = album_data['links']['lastfm']
                        elif 'lastfm_url' in album_data:
                            lastfm_url = album_data['lastfm_url']
                        
                        if lastfm_url:
                            results.append({
                                "source": "lastfm",
                                "title": title,
                                "artist": artist,
                                "url": lastfm_url,
                                "type": "album",
                                "from_database": True
                            })
                            self.log(f"Found album on Last.fm from database: {title} by {artist}")
                
                # If no results yet, try lastfm API
                if not results:
                    manager = MusicLinksManager(config)
                    
                    # Try as artist
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
                        self.log(f"Found artist on Last.fm: {query}")
                    
                    # If format is "artist - title", try as album
                    if artist and title:
                        album_url = manager._get_lastfm_album_url(artist, title)
                        if album_url:
                            results.append({
                                "source": "lastfm",
                                "title": title,
                                "artist": artist,
                                "url": album_url,
                                "type": "album"
                            })
                            self.log(f"Found album on Last.fm: {title} by {artist}")
            
            return results
            
        except Exception as e:
            self.log(f"Error searching on Last.fm: {str(e)}")
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
        # Extract specific configurations from kwargs with improved defaults
        self.mpv_temp_dir = kwargs.pop('mpv_temp_dir', os.path.join(os.path.expanduser("~"), ".config", "mpv", "_mpv_socket"))
        
        # Extract database configuration with better handling
        self.db_path = kwargs.get('db_path')
        if self.db_path and not os.path.isabs(self.db_path):
            self.db_path = os.path.join(PROJECT_ROOT, self.db_path)
        
        # Extract API credentials from kwargs with explicit handling
        self.spotify_authenticated = False
        self.spotify_playlists = {}
        self.spotify_user_id = None
        self.spotify_client_id = kwargs.get('spotify_client_id')
        self.spotify_client_secret = kwargs.get('spotify_client_secret')
        self.lastfm_api_key = kwargs.get('lastfm_api_key')
        self.lastfm_user = kwargs.get('lastfm_user')
        self.exclude_spotify_from_local = kwargs.get('exclude_spotify_from_local', True)

 

        # Log the received configuration
        print(f"[UrlPlayer] Received configs - DB: {self.db_path}, Spotify credentials: {bool(self.spotify_client_id)}, Last.fm credentials: {bool(self.lastfm_api_key)}")
        
        # Initialize other instance variables
        self.player_process = None
        self.current_playlist = []
        self.current_track_index = -1
        self.media_info_cache = {}
        self.yt_dlp_process = None
        self.is_playing = False
        self.mpv_socket = None
        self.mpv_wid = None
        
        # Define default services
        default_services = {
            'youtube': True,
            'soundcloud': True,
            'bandcamp': True,
            'spotify': False,  # Will be updated after loading credentials
            'lastfm': False    # Will be updated after loading credentials
        }
        
        # Get service configuration from kwargs
        included_services = kwargs.pop('included_services', {})
        
        # Initialize services dictionary
        self.included_services = {}
        
        # Ensure all default services are included with boolean values
        for service, default_state in default_services.items():
            if service not in included_services:
                self.included_services[service] = default_state
            else:
                # Convert string representation to boolean if needed
                value = included_services[service]
                if isinstance(value, str):
                    self.included_services[service] = value.lower() == 'true'
                else:
                    self.included_services[service] = bool(value)
        
        # Initialize attributes for widgets
        self.lineEdit = None
        self.searchButton = None
        self.treeWidget = None
        self.playButton = None
        self.rewButton = None
        self.ffButton = None
        self.tabWidget = None
        self.listWidget = None
        self.delButton = None
        self.addButton = None
        self.textEdit = None
        self.info_wiki_textedit = None
        
        # Get pagination configuration
        self.num_servicios_spinBox = kwargs.pop('pagination_value', 10)
        
        # Now call the parent constructor which will call init_ui()
        super().__init__(parent, theme, **kwargs)
        
        # After parent initialization is complete, now we can safely load API credentials
        # and set environment variables
        if not all([self.spotify_client_id, self.spotify_client_secret, self.lastfm_api_key]):
            self._load_api_credentials_from_env()
        
        # Primero cargar las credenciales con tu método existente
        self._load_api_credentials_from_env()  # Tu método existente

        # Luego configurar Spotify solo si tenemos credenciales
        if self.spotify_client_id and self.spotify_client_secret:
            self.setup_spotify()
            
            # Una vez configurado, cargar las playlists
            if hasattr(self, 'playlist_spotify_comboBox') and self.spotify_authenticated:
                self.load_spotify_playlists()

        # Ensure these are available in environment variables for imported modules
        self._set_api_credentials_as_env()
        
        # Update service enabled flags based on credentials
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        self.lastfm_enabled = bool(self.lastfm_api_key)
        
        # Update included_services based on credentials
        self.included_services['spotify'] = self.spotify_enabled
        self.included_services['lastfm'] = self.lastfm_enabled
        
        # Log the final configuration
        print(f"[UrlPlayer] Final config - DB: {self.db_path}, Spotify enabled: {self.spotify_enabled}, Last.fm enabled: {self.lastfm_enabled}")
        

    def get_app_path(self, file_path):
        """Create standardized paths relative to PROJECT_ROOT"""
        return os.path.join(PROJECT_ROOT, file_path)


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
            self.tree_container.setStyleSheet(f"""
                QFrame {{
                    
                    border: 1px;
                    border-radius: 4px;
                }}
                """)
            self.treeWidget.setColumnWidth(0, 250)  # Título
            self.treeWidget.setColumnWidth(1, 100)  # Artista
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

        # Setup service icons
        self.setup_service_icons()

        # Configurar indicador de carga
        self.setup_loading_indicator()

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


             # Add new playlist-related connections
            if hasattr(self, 'playlist_spotify_comboBox'):
                self.playlist_spotify_comboBox.currentIndexChanged.connect(self.on_spotify_playlist_changed)
            
            if hasattr(self, 'playlist_rss_comboBox'):
                self.playlist_rss_comboBox.currentIndexChanged.connect(self.on_playlist_rss_changed)
                #self.playlist_rss_comboBox.currentIndexChanged.connect(self.on_rss_playlist_selected)
            
            #if hasattr(self, 'playlist_local_comboBox'):
                #self.playlist_local_comboBox.currentIndexChanged.connect(self.on_playlist_local_changed)
                

            if hasattr(self, 'GuardarPlaylist'):
                self.GuardarPlaylist.clicked.connect(self.on_guardar_playlist_clicked)
                #self.GuardarPlaylist.clicked.connect(self.save_current_playlist)

            if hasattr(self, 'VaciarPlaylist'):
                #self.VaciarPlaylist.clicked.connect(self.clear_temp_playlist)
                self.VaciarPlaylist.clicked.connect(self.clear_playlist)
            
            # Setup context menus
            self.setup_context_menus()

        except Exception as e:
            print(f"[UrlPlayer] Error al conectar señales: {str(e)}")


    def clear_playlist(self):
        """Clear the current queue/playlist with confirmation"""
        # Check if there are items to clear
        if self.listWidget.count() == 0:
            return
            
        # Confirm with user
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Limpiar lista", 
            "¿Estás seguro de que quieres eliminar todas las canciones de la lista?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear the list widget
            self.listWidget.clear()
            
            # Clear the internal playlist
            self.current_playlist = []
            
            # Reset current track index
            self.current_track_index = -1
            
            # Stop any current playback
            self.stop_playback()
            
            self.log("Cola de reproducción limpiada")

    def load_selected_playlist(self, playlist):
        """Load a selected playlist into the player"""
        if not playlist or 'items' not in playlist:
            return
        
        # Ask for confirmation if current playlist is not empty
        if self.listWidget.count() > 0:
            reply = QMessageBox.question(
                self, "Load Playlist", 
                f"Load playlist '{playlist.get('name')}'? Current playlist will be replaced.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        # Clear current playlist
        self.listWidget.clear()
        self.current_playlist = []
        
        # Add items from selected playlist
        for item in playlist.get('items', []):
            title = item.get('title', '')
            artist = item.get('artist', '')
            url = item.get('url', '')
            
            if not url:
                continue
            
            # Create display text
            display_text = title
            if artist:
                display_text = f"{artist} - {title}"
            
            # Add to list widget
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, url)
            self.listWidget.addItem(list_item)
            
            # Add to internal playlist
            self.current_playlist.append({
                'title': title,
                'artist': artist,
                'url': url
            })
        
        # Reset current track index
        self.current_track_index = -1
        
        # Update UI
        self.log(f"Loaded playlist '{playlist.get('name')}' with {len(playlist.get('items', []))} items")

    def clear_temp_playlist(self):
        """Clear the current queue/playlist"""
        # Clear the list widget
        self.listWidget.clear()
        
        # Clear the internal playlist
        self.current_playlist = []
        
        # Reset current track index
        self.current_track_index = -1
        
        # Stop any current playback
        self.stop_playback()
        
        self.log("Cola de reproducción limpiada")

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

    def _initialize_default_values(self):
        """Initialize default values for settings when configuration can't be loaded"""
        self.log("Initializing default values for settings")
        
        # Default paths
        self.db_path = get_app_path("base_datos/musica.sqlite")
        self.spotify_token_path = get_app_path(".content/cache/spotify_token.txt")
        self.spotify_playlist_path = get_app_path(".content/cache/spotify_playlist.json")
        
        # Default service configuration
        self.included_services = {
            'youtube': True,
            'soundcloud': True,
            'bandcamp': True,
            'spotify': False,  # Will be enabled if credentials are found
            'lastfm': False    # Will be enabled if credentials are found
        }
        
        # Default pagination
        self.num_servicios_spinBox = 10
        self.pagination_value = 10
        
        # Default API credentials (empty)
        self.spotify_client_id = None
        self.spotify_client_secret = None
        self.lastfm_api_key = None
        self.lastfm_user = None
        
        # Default flags
        self.spotify_enabled = False
        self.lastfm_enabled = False
        
        # Create necessary directories
        os.makedirs(os.path.dirname(self.spotify_token_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.spotify_playlist_path), exist_ok=True)


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
        """Loads module configuration with standard paths"""
        try:
            # Standard config path
            config_path = self.get_app_path("config/config.yml")
            
            if not os.path.exists(config_path):
                self.log(f"Config file not found at: {config_path}")
                self._initialize_default_values()
                return
                
            # Load configuration file    
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    
                # Get global credentials first
                if 'global_theme_config' in config_data:
                    global_config = config_data['global_theme_config']
                    
                    # Get database path
                    if 'db_path' in global_config and not self.db_path:
                        self.db_path = self.get_app_path(global_config['db_path'])
                    
                    # Get API credentials
                    if 'spotify_client_id' in global_config:
                        self.spotify_client_id = global_config['spotify_client_id']
                    if 'spotify_client_secret' in global_config:
                        self.spotify_client_secret = global_config['spotify_client_secret']
                    if 'lastfm_api_key' in global_config:
                        self.lastfm_api_key = global_config['lastfm_api_key']
                
                # Find module-specific settings
                for module in config_data.get('modules', []):
                    if module.get('name') in ['Url Playlists', 'URL Playlist', 'URL Player']:
                        module_args = module.get('args', {})
                        
                        # Load paths with standardization
                        if 'db_path' in module_args:
                            self.db_path = self.get_app_path(module_args['db_path'])
                        
                        if 'spotify_token' in module_args:
                            self.spotify_token_path = self.get_app_path(module_args['spotify_token'])
                        else:
                            self.spotify_token_path = self.get_app_path(".content/cache/spotify_token.txt")
                        
                        # Load other settings
                        self._load_module_settings(module_args)
                        break
            except Exception as e:
                self.log(f"Error loading YAML config: {e}")
                self._initialize_default_values()
        except Exception as e:
            self.log(f"Overall error in load_settings: {e}")
            self._initialize_default_values()



    def _load_module_settings(self, module_args):
        """Load module-specific settings from args dictionary"""
        try:
            # Load API credentials
            if 'spotify_client_id' in module_args:
                self.spotify_client_id = module_args['spotify_client_id']
            if 'spotify_client_secret' in module_args:
                self.spotify_client_secret = module_args['spotify_client_secret']
            if 'lastfm_api_key' in module_args:
                self.lastfm_api_key = module_args['lastfm_api_key']
            if 'lastfm_user' in module_args:
                self.lastfm_user = module_args['lastfm_user']
            
            # Load pagination value
            if 'pagination_value' in module_args:
                self.pagination_value = module_args.get('pagination_value', 10)
                self.num_servicios_spinBox = self.pagination_value
            
            # Load included services
            if 'included_services' in module_args:
                included_services = module_args.get('included_services', {})
                
                # Ensure values are boolean
                self.included_services = {}
                for key, value in included_services.items():
                    if isinstance(value, str):
                        self.included_services[key] = value.lower() == 'true'
                    else:
                        self.included_services[key] = bool(value)
            
            # Load MPV temp directory
            if 'mpv_temp_dir' in module_args:
                mpv_temp_dir = module_args['mpv_temp_dir']
                # Handle relative path
                if not os.path.isabs(mpv_temp_dir):
                    mpv_temp_dir = os.path.join(os.path.expanduser("~"), mpv_temp_dir)
                self.mpv_temp_dir = mpv_temp_dir
                
            self.log("Module settings loaded successfully")
        except Exception as e:
            self.log(f"Error loading module settings: {e}")

    def update_playlist_comboboxes(self):
        """Update all playlist combobox contents from saved playlists"""
        if not hasattr(self, 'playlists'):
            self.playlists = self.load_playlists()
        
        # Update Spotify playlists combo
        if hasattr(self, 'playlist_spotify_comboBox'):
            self.playlist_spotify_comboBox.clear()
            self.playlist_spotify_comboBox.addItem(QIcon(":/services/b_plus_cross"), "Nueva Playlist Spotify")
            
            for playlist in self.playlists.get('spotify', []):
                self.playlist_spotify_comboBox.addItem(
                    QIcon(":/services/spotify"), 
                    playlist.get('name', 'Unnamed Playlist')
                )
        
        # Update local playlists combo
        if hasattr(self, 'playlist_local_comboBox'):
            self.playlist_local_comboBox.clear()
            
            for playlist in self.playlists.get('local', []):
                self.playlist_local_comboBox.addItem(
                    QIcon(":/services/plslove"), 
                    playlist.get('name', 'Unnamed Playlist')
                )
        
        # Update RSS playlists combo
        if hasattr(self, 'playlist_rss_comboBox'):
            self.playlist_rss_comboBox.clear()
            
            for playlist in self.playlists.get('rss', []):
                self.playlist_rss_comboBox.addItem(
                    QIcon(":/services/rss"), 
                    playlist.get('name', 'Unnamed Blog')
                )

    def save_current_playlist(self):
        """Save the current playlist based on the selected format in guardar_playlist_comboBox."""
        # Get the selected playlist type
        if not hasattr(self, 'guardar_playlist_comboBox'):
            self.log("guardar_playlist_comboBox not found")
            return
        
        playlist_type = self.guardar_playlist_comboBox.currentText()
        self.log(f"Saving playlist as {playlist_type}")
        
        # Verify we have items to save
        if self.listWidget.count() == 0:
            self.log("No items to save in playlist")
            return
        
        # Ask for playlist name
        name, ok = QInputDialog.getText(self, "Playlist Name", "Enter a name for the playlist:")
        if not ok or not name:
            self.log("Playlist name dialog canceled or empty name")
            return
        
        # For local playlists
        if playlist_type == "Playlist local":
            self.log(f"Saving as local playlist: {name}")
            self.save_local_playlist(name)
        elif playlist_type == "Spotify":
            # Use existing Spotify save functionality
            self.log(f"Saving as Spotify playlist: {name}")
            self.save_to_spotify_playlist()
        elif playlist_type == "Youtube":
            # Future implementation
            self.log("Youtube playlist saving not implemented yet")

    def fetch_artist_song_paths(self, artist_name):
        """Fetch song paths for an artist using the database query API"""
            # Check cache first
        if not hasattr(self, 'path_cache'):
            self.path_cache = {}
            
        if artist_name in self.path_cache:
            return self.path_cache[artist_name]
        try:
            if not self.db_path or not os.path.exists(self.db_path):
                self.log(f"Database not found at: {self.db_path}")
                return None
                
            from base_datos.tools.consultar_items_db import MusicDatabaseQuery
            db = MusicDatabaseQuery(self.db_path)
            
            # Use the existing method from consultar_items_db.py
            result = db.get_artist_song_paths(artist_name)
            db.close()
            if result:
                self.path_cache[artist_name] = result
            return result
        except Exception as e:
            self.log(f"Error fetching song paths: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return None



    def save_local_playlist(self, name):
        """Save the current queue as a local playlist file."""
        try:
            # Ensure playlists directory exists
            local_playlist_dir = self.get_local_playlist_path()
            os.makedirs(local_playlist_dir, exist_ok=True)
            
            # Create a clean filename
            import re
            safe_name = re.sub(r'[^\w\-_\. ]', '_', name)
            playlist_path = os.path.join(local_playlist_dir, f"{safe_name}.pls")
            
            # Debug output to verify we have items
            self.log(f"Saving playlist with {self.listWidget.count()} items")
            
            # Collect items from the list, excluding Spotify items if requested
            items = []
            for i in range(self.listWidget.count()):
                item = self.listWidget.item(i)
                if not item:
                    self.log(f"Warning: Item at index {i} is None, skipping")
                    continue
                    
                url = item.data(Qt.ItemDataRole.UserRole)
                if not url:
                    self.log(f"Warning: No URL for item at index {i}, skipping")
                    continue
                    
                title = item.text()
                
                # Determine if this is a Spotify URL (skip if exclude_spotify is True)
                is_spotify = 'spotify.com' in str(url).lower()
                if is_spotify and self.exclude_spotify_from_local:
                    self.log(f"Skipping Spotify item: {title}")
                    continue
                
                # Extract artist and title if possible
                artist = ""
                if " - " in title:
                    parts = title.split(" - ", 1)
                    artist = parts[0]
                    title = parts[1]
                
                # Add to items list
                items.append({
                    "url": url,
                    "title": title,
                    "artist": artist,
                    "source": self._determine_source_from_url(url)
                })
                self.log(f"Added item to playlist: {artist} - {title}")
            
            # Debug check - if we still have no items, something is wrong
            if not items:
                self.log("Warning: No items collected from the listWidget")
                
                # Fallback: try to use the current_playlist instead
                if self.current_playlist:
                    self.log(f"Attempting to use current_playlist with {len(self.current_playlist)} items")
                    for item in self.current_playlist:
                        if not item.get('url'):
                            continue
                            
                        # Skip Spotify if requested
                        is_spotify = 'spotify.com' in str(item.get('url')).lower()
                        if is_spotify and self.exclude_spotify_from_local:
                            continue
                            
                        items.append({
                            "url": item.get('url', ''),
                            "title": item.get('title', ''),
                            "artist": item.get('artist', ''),
                            "source": item.get('source', self._determine_source_from_url(item.get('url', '')))
                        })
            
            # Save in a simple PLS format
            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write("[playlist]\n")
                f.write(f"NumberOfEntries={len(items)}\n\n")
                
                for i, item in enumerate(items, 1):
                    f.write(f"File{i}={item['url']}\n")
                    f.write(f"Title{i}={item['artist']} - {item['title']}\n" if item['artist'] else f"Title{i}={item['title']}\n")
                    f.write(f"Length{i}=-1\n\n")  # -1 means unknown length
            
            # Also save as JSON for more metadata
            json_path = os.path.join(local_playlist_dir, f"{safe_name}.json")
            playlist_data = {
                "name": name,
                "items": items,
                "created": int(time.time()),
                "modified": int(time.time())
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, indent=2, ensure_ascii=False)
            
            # Update internal playlists
            if not hasattr(self, 'playlists'):
                self.playlists = self.load_playlists()
            
            if 'local' not in self.playlists:
                self.playlists['local'] = []
            
            # Check if playlist with same name exists
            playlist_updated = False
            for i, existing in enumerate(self.playlists['local']):
                if existing.get('name') == name:
                    # Replace existing
                    self.playlists['local'][i] = playlist_data
                    playlist_updated = True
                    break
            
            # Add new playlist if not found
            if not playlist_updated:
                self.playlists['local'].append(playlist_data)
                
            # Save and update UI
            self.save_playlists()
            self.update_playlist_comboboxes()
            
            self.log(f"Saved local playlist '{name}' with {len(items)} items to {playlist_path}")
            
        except Exception as e:
            self.log(f"Error saving local playlist: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

    def load_local_playlist(self, playlist_name):
        """Load a local playlist into the player."""
        try:
            # Find the playlist in our playlists data
            if not hasattr(self, 'playlists'):
                self.playlists = self.load_playlists()
            
            selected_playlist = None
            for playlist in self.playlists.get('local', []):
                if playlist.get('name') == playlist_name:
                    selected_playlist = playlist
                    break
            
            if not selected_playlist:
                self.log(f"Local playlist '{playlist_name}' not found")
                return
            
            # Ask for confirmation if current playlist is not empty
            if self.listWidget.count() > 0:
                reply = QMessageBox.question(
                    self, "Load Playlist", 
                    f"Load playlist '{playlist_name}'? Current playlist will be replaced.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Clear current playlist
            self.listWidget.clear()
            self.current_playlist = []
            
            # Add items from selected playlist
            for item in selected_playlist.get('items', []):
                title = item.get('title', '')
                artist = item.get('artist', '')
                url = item.get('url', '')
                source = item.get('source', self._determine_source_from_url(url))
                
                if not url:
                    continue
                
                # Create display text
                display_text = title
                if artist:
                    display_text = f"{artist} - {title}"
                
                # Add to list widget with icon
                list_item = QListWidgetItem(display_text)
                list_item.setData(Qt.ItemDataRole.UserRole, url)
                
                # Add the appropriate icon
                icon = self.get_source_icon(url, {'source': source})
                list_item.setIcon(icon)
                
                self.listWidget.addItem(list_item)
                
                # Add to internal playlist
                self.current_playlist.append({
                    'title': title,
                    'artist': artist,
                    'url': url,
                    'source': source
                })
            
            # Reset current track index
            self.current_track_index = -1
            
            # Update UI
            self.log(f"Loaded local playlist '{playlist_name}' with {len(selected_playlist.get('items', []))} items")
            
        except Exception as e:
            self.log(f"Error loading local playlist: {str(e)}")
            import traceback
            self.log(traceback.format_exc())


    def _extract_global_credentials(self, config_data):
        """Extract credentials from global configuration section."""
        # Check for global_theme_config section
        if 'global_theme_config' in config_data:
            global_config = config_data['global_theme_config']
            
            # Extract database path
            if 'db_path' in global_config and not self.db_path:
                db_path = global_config['db_path']
                # Handle both relative and absolute paths
                if not os.path.isabs(db_path):
                    db_path = os.path.join(PROJECT_ROOT, db_path)
                
                if os.path.exists(db_path):
                    self.db_path = db_path
                    self.log(f"Loaded db_path from global config: {self.db_path}")
            
            # Extract Spotify credentials
            if 'spotify_client_id' in global_config and not self.spotify_client_id:
                self.spotify_client_id = global_config['spotify_client_id']
                self.log("Loaded spotify_client_id from global config")
                
            if 'spotify_client_secret' in global_config and not self.spotify_client_secret:
                self.spotify_client_secret = global_config['spotify_client_secret']
                self.log("Loaded spotify_client_secret from global config")
                
            # Extract Last.fm credentials
            if 'lastfm_api_key' in global_config and not self.lastfm_api_key:
                self.lastfm_api_key = global_config['lastfm_api_key']
                self.log("Loaded lastfm_api_key from global config")
                
            if 'lastfm_user' in global_config and not self.lastfm_user:
                self.lastfm_user = global_config['lastfm_user']
                self.log("Loaded lastfm_user from global config")
        
        # Also check for credentials at the root level
        if 'db_path' in config_data and not self.db_path:
            db_path = config_data['db_path']
            if not os.path.isabs(db_path):
                db_path = os.path.join(PROJECT_ROOT, db_path)
            
            if os.path.exists(db_path):
                self.db_path = db_path
                self.log(f"Loaded db_path from config root: {self.db_path}")

    def _extract_module_config(self, config_data):
        """Extract configuration specific to this module."""
        module_config = None
        module_names = ['Url Playlists', 'URL Playlist', 'URL Player']
        
        # Search in active modules
        for module in config_data.get('modules', []):
            if module.get('name') in module_names:
                module_config = module.get('args', {})
                self.log(f"Found module configuration for '{module.get('name')}'")
                break
        
        # If not found, check disabled modules
        if module_config is None:
            for module in config_data.get('modulos_desactivados', []):
                if module.get('name') in module_names:
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
                
                if os.path.exists(db_path):
                    self.db_path = db_path
                    self.log(f"Loaded db_path from module config: {self.db_path}")
            
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
            
            # Load pagination_value
            if 'pagination_value' in module_config:
                self.pagination_value = module_config.get('pagination_value', 10)
                self.num_servicios_spinBox = self.pagination_value  # Sync both values
            
            # Load included_services
            if 'included_services' in module_config:
                included_services = module_config.get('included_services', {})
                
                # Ensure included_services values are booleans, not strings
                self.included_services = {}
                for key, value in included_services.items():
                    if isinstance(value, str):
                        self.included_services[key] = value.lower() == 'true'
                    else:
                        self.included_services[key] = bool(value)

    def _find_database_fallback(self):
        """Try to find database file as a fallback."""
        if not self.db_path:
            # Try common locations for the database
            common_db_paths = [
                os.path.join(PROJECT_ROOT, "base_datos", "musica.sqlite"),
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
                                print(f"[UrlPlayer] Loaded Spotify client ID from {config_path}")
                            if not self.spotify_client_secret:
                                self.spotify_client_secret = api_config['spotify'].get('client_secret')
                                print(f"[UrlPlayer] Loaded Spotify client secret from {config_path}")
                        
                        if 'lastfm' in api_config:
                            if not self.lastfm_api_key:
                                self.lastfm_api_key = api_config['lastfm'].get('api_key')
                                print(f"[UrlPlayer] Loaded Last.fm API key from {config_path}")
                            if not self.lastfm_user:
                                self.lastfm_user = api_config['lastfm'].get('user')
                                print(f"[UrlPlayer] Loaded Last.fm user from {config_path}")
                        
                    # If we found and loaded the config, break the loop
                    if all([self.spotify_client_id, self.spotify_client_secret, self.lastfm_api_key]):
                        print(f"[UrlPlayer] Successfully loaded all API credentials from {config_path}")
                        break
                except Exception as e:
                    print(f"[UrlPlayer] Error loading API credentials from {config_path}: {str(e)}")

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
                
            print("[UrlPlayer] Attempted to load credentials from .env files")
        except ImportError:
            # dotenv is not installed, that's fine
            pass

    def _set_api_credentials_as_env(self):
        """Set API credentials as environment variables for imported modules with better validation"""
        if self.spotify_client_id and isinstance(self.spotify_client_id, str) and self.spotify_client_id.strip():
            os.environ["SPOTIFY_CLIENT_ID"] = self.spotify_client_id.strip()
            print(f"[UrlPlayer] Set SPOTIFY_CLIENT_ID in environment")
        
        if self.spotify_client_secret and isinstance(self.spotify_client_secret, str) and self.spotify_client_secret.strip():
            os.environ["SPOTIFY_CLIENT_SECRET"] = self.spotify_client_secret.strip()
            print(f"[UrlPlayer] Set SPOTIFY_CLIENT_SECRET in environment")
        
        if self.lastfm_api_key and isinstance(self.lastfm_api_key, str) and self.lastfm_api_key.strip():
            os.environ["LASTFM_API_KEY"] = self.lastfm_api_key.strip()
            print(f"[UrlPlayer] Set LASTFM_API_KEY in environment")
        
        if self.lastfm_user and isinstance(self.lastfm_user, str) and self.lastfm_user.strip():
            os.environ["LASTFM_USER"] = self.lastfm_user.strip()
            print(f"[UrlPlayer] Set LASTFM_USER in environment")
            
        # Update enabled flags based on credentials
        self.spotify_enabled = bool(self.spotify_client_id and self.spotify_client_secret)
        self.lastfm_enabled = bool(self.lastfm_api_key)
        
        # Update included_services based on what's available
        if not self.spotify_enabled and 'spotify' in self.included_services:
            self.included_services['spotify'] = False
            print("[UrlPlayer] Disabled Spotify service due to missing credentials")
            
        if not self.lastfm_enabled and 'lastfm' in self.included_services:
            self.included_services['lastfm'] = False
            print("[UrlPlayer] Disabled Last.fm service due to missing credentials")


    def extract_playable_url(self, item_data):
        """
        Extract a playable URL or file path from item data.
        Returns the most appropriate URL or path for playback.
        """
        try:
            # Default to the item's URL if it exists
            url = None
            
            if isinstance(item_data, dict):
                # First check for a file path (for local files)
                url = item_data.get('file_path')
                
                # If no file path, fall back to URL
                if not url:
                    url = item_data.get('url')
                
                # Handle different sources
                source = item_data.get('source', '').lower()
                item_type = item_data.get('type', '').lower()
                
                if source == 'bandcamp' and item_type == 'track':
                    # For Bandcamp tracks:
                    # 1. Try direct track URL
                    # 2. Fall back to album URL if necessary
                    
                    # If no URL but we have album URL, use that
                    if not url and item_data.get('album_url'):
                        url = item_data.get('album_url')
                        self.log(f"Using album URL for Bandcamp track: {url}")
                    
                    # Try to get URL from parent album if still needed
                    if not url and item_data.get('album') and item_data.get('artist'):
                        parent_album_url = self._find_parent_album_url(item_data)
                        if parent_album_url:
                            url = parent_album_url
                            self.log(f"Using parent album URL for track: {url}")
            else:
                # If item_data is a string, assume it's the URL or path
                url = str(item_data)
                
            return url
        except Exception as e:
            self.log(f"Error extracting playable URL: {str(e)}")
            return None


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
                self.log(f"Base de datos no encontrada en: {self.db_path}")
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
        # If it's a root item (source) with children, just expand/collapse
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return
                
        # Get the result data stored with the item
        result_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # If it's a search result
        if isinstance(result_data, dict):
            url = result_data.get('url', '')
            
            # For database items that might not have a direct URL
            if not url and result_data.get('source', '').lower() in ['database', 'local']:
                # This is likely a database item, extract the best URL we can
                if 'links' in result_data:
                    # Try to find a playable URL in the links
                    for service, service_url in result_data['links'].items():
                        if service_url:
                            url = service_url
                            break
            
            if url:
                # Create display text
                title = result_data.get('title', '')
                artist = result_data.get('artist', '')
                display_text = f"{artist} - {title}" if artist and title else title or url
                display_text = display_text.strip()
                
                # Add to the queue
                self.add_to_queue_from_url(url, display_text, result_data)
                self.log(f"Added to queue: {display_text}")
                
                # Optional: Play immediately if nothing is playing
                if not self.is_playing and self.current_track_index == -1:
                    self.current_track_index = len(self.current_playlist) - 1
                    self.play_media()
            else:
                self.log(f"No playable URL found for {result_data.get('title', 'Unknown item')}")
        else:
            # Handle the logic for non-search results
            if hasattr(self, 'on_tree_double_click_original'):
                self.on_tree_double_click_original(item, column)

    def add_to_queue_from_url(self, url, display_text, metadata=None):
        """Adds an item to the queue with the appropriate icon based on URL source."""
        # Create a new item for the playlist
        queue_item = QListWidgetItem(display_text)
        queue_item.setData(Qt.ItemDataRole.UserRole, url)
        
        # Add the appropriate icon
        icon = self.get_source_icon(url, metadata)
        queue_item.setIcon(icon)
        
        # Add to the list
        self.listWidget.addItem(queue_item)
        
        # Update the internal list
        self.current_playlist.append({
            'title': metadata.get('title', display_text),
            'artist': metadata.get('artist', ''),
            'url': url,
            'source': metadata.get('source', self._determine_source_from_url(url)),
            'entry_data': metadata
        })
        
        self.log(f"Element added to queue: {display_text}")
        
        # If nothing is playing, select this item
        if not self.is_playing and self.current_track_index == -1:
            self.current_track_index = len(self.current_playlist) - 1
            self.listWidget.setCurrentRow(self.current_track_index)
    
    def _determine_source_from_url(self, url):
        """Determine the source (service) from a URL."""
        url = str(url).lower()
        if 'spotify.com' in url:
            return 'spotify'
        elif 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'soundcloud.com' in url:
            return 'soundcloud'
        elif 'bandcamp.com' in url:
            return 'bandcamp'
        elif url.startswith(('/', 'file:', '~', 'C:', 'D:')):
            return 'local'
        return 'unknown'



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
        
        # Obtener la URL o path del elemento a reproducir
        current_item = self.current_playlist[index]
        url = current_item.get('file_path', current_item.get('url'))  # Try file_path first, then URL
        
        # Verificar que la URL o path sea válido
        if not url:
            self.log("URL/path inválido para reproducción")
            return
        
        # Detener reproducción actual si existe
        self.stop_playback()
        
        # Reproducir la URL/path actual
        self.play_single_url(url)
        
        # Resaltar elemento actual
        self.highlight_current_track()
        
        # Mostrar información en el log
        title = current_item.get('title', 'Desconocido')
        artist = current_item.get('artist', '')
        display = f"{artist} - {title}" if artist else title
        self.log(f"Reproduciendo: {display}")


    def play_single_url(self, url):
        """Reproduce una única URL o archivo local con MPV."""
        if not url:
            self.log("Error: URL/path vacío")
            return
        
        # Asegurarse de que la URL/path es un string
        if isinstance(url, dict):
            url = url.get('file_path', url.get('url', str(url)))
        url = str(url)
        
        self.log(f"Reproduciendo URL/path: {url}")
        
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
        
        # Special handling for local files vs. stream URLs
        is_local_file = url.startswith(('/', '~', 'file:', 'C:', 'D:'))
        
        if is_local_file:
            self.log("Reproduciendo archivo local")
            # Make sure the file exists
            if not os.path.exists(os.path.expanduser(url.replace('file://', ''))):
                self.log(f"Advertencia: El archivo no existe: {url}")
        
        # Special handling for Bandcamp URLs
        elif "bandcamp.com" in url:
            # For Bandcamp, we might want to use specific options
            mpv_args.extend([
                "--ytdl-raw-options=yes-playlist=",  # Handle as single track even if it's an album
                "--force-window=yes",               # Force window creation
            ])
            self.log("Aplicando configuración especial para Bandcamp")
        
        # Add the URL
        mpv_args.append(url)
        
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
        """Performs a search based on the selected service and query."""
        query = self.lineEdit.text().strip()
        if not query:
            return
        
        self.log(f"Searching: {query}")
        
        # Clear previous results
        self.treeWidget.clear()
        self.textEdit.clear()
        QApplication.processEvents()  # Update UI
        
        # Show loading indicator
        self.show_loading_indicator(True)
        
        # Get the selected service
        service = self.servicios.currentText()
        
        # Get the search type
        search_type = "all"
        if hasattr(self, 'tipo_combo') and self.tipo_combo:
            search_type = self.tipo_combo.currentText().lower()
        
        # Show progress
        self.textEdit.append(f"Buscando '{query}' en {service} (tipo: {search_type}, máx {self.pagination_value} resultados por servicio)...")
        QApplication.processEvents()  # Update UI
        
        # Create a structure to track added items
        self.added_items = {
            'artists': set(),      # Set of artist names
            'albums': set(),       # Set of "artist - album" keys
            'tracks': set()        # Set of "artist - title" keys
        }
        
        # First check database for existing links and structure
        self.log("Consultando la base de datos local primero...")
        db_links = self.search_database_links(query, search_type)
        
        # Process database results immediately
        if db_links:
            db_results = self._process_database_results(db_links)
            if db_results:
                self.display_search_results(db_results)
                self.log(f"Encontrados {len(db_results)} resultados en la base de datos local")
        
        # Determine which services to include
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
            self.log("No hay servicios seleccionados para la búsqueda. Actívalos en Ajustes Avanzados.")
            return
        
        # Disable controls during search
        self.searchButton.setEnabled(False)
        self.lineEdit.setEnabled(False)
        QApplication.processEvents()  # Update UI
        
        # Create and configure the worker with the necessary attributes
        worker = SearchWorker(active_services, query, max_results=self.pagination_value)
        worker.parent = self  # Set parent to access search_in_database
        worker.search_type = search_type  # Pass search type to worker
        
        # Pass database links to worker
        worker.db_links = db_links
        
        # Pass necessary attributes from parent
        worker.db_path = self.db_path
        worker.spotify_client_id = self.spotify_client_id
        worker.spotify_client_secret = self.spotify_client_secret
        worker.lastfm_api_key = self.lastfm_api_key
        worker.lastfm_user = self.lastfm_user
        
        # Pass the tracking structure to avoid duplicates
        worker.added_items = self.added_items
        
        # Connect signals
        worker.signals.results.connect(self.display_external_results)  # Changed to a new method
        worker.signals.error.connect(lambda err: self.log(f"Error en búsqueda: {err}"))
        worker.signals.finished.connect(self.search_finished)
        
        # Start the worker in the thread pool
        QThreadPool.globalInstance().start(worker)
        

    def display_external_results(self, results):
        """Display external search results, keeping database results already shown."""
        if not results:
            self.log("No se encontraron resultados externos.")
            return
        
        # Filter out results from database to avoid duplicates
        external_results = [r for r in results if not r.get('from_database', False)]
        
        if external_results:
            self.display_search_results(external_results)
            self.log(f"Se añadieron {len(external_results)} resultados de servicios externos")


    def search_finished(self, result=None, basic_data=None):
        """Función llamada cuando termina la búsqueda."""
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
                self.display_wiki_info(child.data(0, Qt.ItemDataRole.UserRole))
        
        QApplication.processEvents()  # Actualiza la UI

 
    def search_database_links(self, query, search_type="all"):
        """
        Search for existing links and structure in the database before making API calls.
        Returns a hierarchical structure of artists/albums/tracks with their links.
        """
        try:
            from base_datos.tools.consultar_items_db import MusicDatabaseQuery
            
            if not self.db_path or not os.path.exists(self.db_path):
                self.log(f"Database not found at: {self.db_path}")
                return {}
            
            self.log(f"Searching for existing links in database at: {self.db_path}")
            db = MusicDatabaseQuery(self.db_path)
            
            # Dictionary to store all found links by type
            results = {
                'artists': {},  # Keyed by artist name
                'albums': {},   # Keyed by "artist - album"
                'tracks': {}    # Keyed by "artist - title"
            }
            
            # Parse query to determine what to search for
            artist_name = None
            album_name = None
            track_name = None
            
            # If the format is "artist - title", split it
            parts = query.split(" - ", 1)
            if len(parts) > 1:
                artist_name = parts[0].strip()
                if search_type.lower() in ['album', 'álbum']:
                    album_name = parts[1].strip()
                else:
                    track_name = parts[1].strip()
            else:
                # Single term could be artist, album, or track
                artist_name = query.strip()
                if search_type.lower() in ['album', 'álbum']:
                    album_name = query.strip()
                elif search_type.lower() in ['track', 'song', 'canción']:
                    track_name = query.strip()
            
            # 1. Search for artist links
            if search_type.lower() in ['artist', 'artista', 'all']:
                self.log(f"Checking database for artist: {artist_name}")
                
                # Get basic artist info
                artist_info = db.get_artist_info(artist_name)
                
                if artist_info:
                    # Initialize artist entry
                    artist_entry = {
                        'name': artist_name,
                        'links': {},
                        'type': 'artist',
                        'albums': [],
                        'from_database': True
                    }
                    
                    # Get artist links
                    artist_links = db.get_artist_links(artist_name)
                    if artist_links:
                        artist_entry['links'] = artist_links
                        
                        # Add specific fields for direct access
                        for service, url in artist_links.items():
                            if url:
                                artist_entry[f'{service.lower()}_url'] = url
                    
                    # Get artist bio
                    if 'bio' in artist_info:
                        artist_entry['bio'] = artist_info['bio']
                    
                    # Get additional artist metadata
                    for field in ['origin', 'formed_year', 'tags', 'similar_artists']:
                        if field in artist_info and artist_info[field]:
                            artist_entry[field] = artist_info[field]
                    
                    # Get artist albums
                    artist_albums = db.get_artist_albums(artist_name)
                    if artist_albums:
                        for album_tuple in artist_albums:
                            album_name = album_tuple[0]
                            year = album_tuple[1] if len(album_tuple) > 1 else None
                            
                            # Get album info
                            album_info = db.get_album_info(album_name, artist_name)
                            
                            # Create album entry
                            album_entry = {
                                'title': album_name,
                                'artist': artist_name,
                                'year': year,
                                'type': 'album',
                                'tracks': [],
                                'from_database': True
                            }
                            
                            # Get album links
                            album_links = db.get_album_links(artist_name, album_name)
                            if album_links:
                                album_entry['links'] = album_links
                                
                                # Add specific fields for direct access
                                for service, url in album_links.items():
                                    if url:
                                        album_entry[f'{service.lower()}_url'] = url
                            
                            # Add tracks if available in album_info
                            if album_info and 'songs' in album_info:
                                for song in album_info['songs']:
                                    track_title = song.get('title', '')
                                    
                                    # Create track entry
                                    track_entry = {
                                        'title': track_title,
                                        'artist': artist_name,
                                        'album': album_name,
                                        'type': 'track',
                                        'track_number': song.get('track_number'),
                                        'duration': song.get('duration'),
                                        'from_database': True
                                    }
                                    
                                    # Get track links
                                    track_links = db.get_track_links(album_name, track_title)
                                    if track_links:
                                        track_entry['links'] = track_links
                                        
                                        # Add specific fields for direct access
                                        for service, url in track_links.items():
                                            if url:
                                                track_entry[f'{service.lower()}_url'] = url
                                    
                                    # Add to album tracks
                                    album_entry['tracks'].append(track_entry)
                                    
                                    # Store in tracks dictionary
                                    track_key = f"{artist_name} - {track_title}"
                                    results['tracks'][track_key] = track_entry
                            
                            # Add to artist albums
                            artist_entry['albums'].append(album_entry)
                            
                            # Store in albums dictionary
                            album_key = f"{artist_name} - {album_name}"
                            results['albums'][album_key] = album_entry
                    
                    # Store in artists dictionary
                    results['artists'][artist_name] = artist_entry
            
            # 2. Search for album links (if not already found via artist)
            if search_type.lower() in ['album', 'álbum', 'all'] and album_name:
                # If we already have the album (from artist search), skip
                album_key = f"{artist_name} - {album_name}"
                if album_key not in results['albums']:
                    self.log(f"Checking database for album: {album_name} by {artist_name}")
                    
                    # Get album info
                    album_info = db.get_album_info(album_name, artist_name)
                    
                    if album_info:
                        # Create album entry
                        album_entry = {
                            'title': album_name,
                            'artist': artist_name,
                            'year': album_info.get('year'),
                            'type': 'album',
                            'tracks': [],
                            'from_database': True
                        }
                        
                        # Get album links
                        album_links = db.get_album_links(artist_name, album_name)
                        if album_links:
                            album_entry['links'] = album_links
                            
                            # Add specific fields for direct access
                            for service, url in album_links.items():
                                if url:
                                    album_entry[f'{service.lower()}_url'] = url
                        
                        # Add tracks if available
                        if 'songs' in album_info:
                            for song in album_info['songs']:
                                track_title = song.get('title', '')
                                
                                # Create track entry
                                track_entry = {
                                    'title': track_title,
                                    'artist': artist_name,
                                    'album': album_name,
                                    'type': 'track',
                                    'track_number': song.get('track_number'),
                                    'duration': song.get('duration'),
                                    'from_database': True
                                }
                                
                                # Get track links
                                track_links = db.get_track_links(album_name, track_title)
                                if track_links:
                                    track_entry['links'] = track_links
                                    
                                    # Add specific fields for direct access
                                    for service, url in track_links.items():
                                        if url:
                                            track_entry[f'{service.lower()}_url'] = url
                                
                                # Add to album tracks
                                album_entry['tracks'].append(track_entry)
                                
                                # Store in tracks dictionary
                                track_key = f"{artist_name} - {track_title}"
                                results['tracks'][track_key] = track_entry
                        
                        # Store in albums dictionary
                        results['albums'][album_key] = album_entry
            
            # 3. Search for track links (if not already found)
            if search_type.lower() in ['track', 'song', 'canción', 'all'] and track_name:
                track_key = f"{artist_name} - {track_name}"
                if track_key not in results['tracks']:
                    self.log(f"Checking database for track: {track_name} by {artist_name}")
                    
                    # Get song info
                    song_info = db.get_song_info(track_name, artist_name)
                    
                    if song_info:
                        # Get album name from song info
                        album_name = song_info.get('album', '')
                        
                        # Create track entry
                        track_entry = {
                            'title': track_name,
                            'artist': artist_name,
                            'album': album_name,
                            'type': 'track',
                            'track_number': song_info.get('track_number'),
                            'duration': song_info.get('duration'),
                            'lyrics': song_info.get('lyrics'),
                            'from_database': True
                        }
                        
                        # Get track links
                        if album_name:
                            track_links = db.get_track_links(album_name, track_name)
                            if track_links:
                                track_entry['links'] = track_links
                                
                                # Add specific fields for direct access
                                for service, url in track_links.items():
                                    if url:
                                        track_entry[f'{service.lower()}_url'] = url
                        
                        # Store in tracks dictionary
                        results['tracks'][track_key] = track_entry
            
            db.close()
            return results
            
        except Exception as e:
            self.log(f"Error searching database links: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return {}


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
        """Shows search results in the TreeWidget with proper nesting."""
        if not results:
            self.textEdit.append("No se encontraron resultados.")
            QApplication.processEvents()
            return
        
        # Count items before adding new ones
        initial_count = self.treeWidget.topLevelItemCount()
        
        # Separate results by source and type
        db_results = [r for r in results if r.get('from_database', False) or r.get('source', '').lower() == 'local']
        external_results = [r for r in results if not r.get('from_database', False) and r.get('source', '').lower() != 'local']
        
        # First, add database results under "Música Local" node
        if db_results:
            local_music_item = QTreeWidgetItem(self.treeWidget)
            local_music_item.setText(0, "Música Local")
            local_music_item.setText(2, "Fuente")
            
            # Add icon for local music
            local_music_item.setIcon(0, self.service_icons.get('local', QIcon()))
            
            # Format as bold
            font = local_music_item.font(0)
            font.setBold(True)
            local_music_item.setFont(0, font)
            
            # Group by artist first
            by_artist = {}
            standalone_albums = []
            standalone_tracks = []
            
            # First pass - sort items by type
            for result in db_results:
                item_type = result.get('type', '').lower()
                
                if item_type == 'artist':
                    artist_name = result.get('title', '')
                    by_artist[artist_name] = result
                elif item_type == 'album':
                    artist_name = result.get('artist', '')
                    if artist_name:
                        if artist_name not in by_artist:
                            by_artist[artist_name] = {
                                'title': artist_name,
                                'artist': artist_name,
                                'type': 'artist',
                                'albums': []
                            }
                        if 'albums' not in by_artist[artist_name]:
                            by_artist[artist_name]['albums'] = []
                        by_artist[artist_name]['albums'].append(result)
                    else:
                        standalone_albums.append(result)
                elif item_type in ['track', 'song']:
                    standalone_tracks.append(result)
            
            # Add artists with their albums and tracks
            for artist_name, artist_data in by_artist.items():
                artist_item = QTreeWidgetItem(local_music_item)
                artist_item.setText(0, artist_name)
                artist_item.setText(1, artist_name)
                artist_item.setText(2, "Artista")
                
                # Format as bold
                font = artist_item.font(0)
                font.setBold(True)
                artist_item.setFont(0, font)
                
                # Store complete data
                artist_item.setData(0, Qt.ItemDataRole.UserRole, artist_data)
                
                # Add albums
                if 'albums' in artist_data and artist_data['albums']:
                    for album in artist_data['albums']:
                        album_item = QTreeWidgetItem(artist_item)
                        album_item.setText(0, album.get('title', ''))
                        album_item.setText(1, artist_name)
                        album_item.setText(2, "Álbum")
                        if album.get('year'):
                            album_item.setText(3, str(album.get('year')))
                        
                        # Store complete data
                        album_item.setData(0, Qt.ItemDataRole.UserRole, album)
                        
                        # Add tracks
                        if 'tracks' in album and album['tracks']:
                            for track in album['tracks']:
                                self._add_result_to_tree(track, album_item)
                
                # Expand artist item
                artist_item.setExpanded(True)
            
            # Add standalone albums
            for album in standalone_albums:
                album_item = QTreeWidgetItem(local_music_item)
                album_item.setText(0, album.get('title', ''))
                album_item.setText(1, album.get('artist', ''))
                album_item.setText(2, "Álbum")
                if album.get('year'):
                    album_item.setText(3, str(album.get('year')))
                
                # Store complete data
                album_item.setData(0, Qt.ItemDataRole.UserRole, album)
                
                # Add tracks
                if 'tracks' in album and album['tracks']:
                    for track in album['tracks']:
                        self._add_result_to_tree(track, album_item)
                
                # Expand album item
                album_item.setExpanded(True)
            
            # Add standalone tracks
            for track in standalone_tracks:
                self._add_result_to_tree(track, local_music_item)
            
            # Expand local music item
            local_music_item.setExpanded(True)
            
            # Add result count badge
            local_count = len(db_results)
            if local_count > 0:
                local_music_item.setText(0, f"Música Local ({local_count})")
        
        # Add external results by service
        if external_results:
            by_service = {}
            
            # Group by service
            for result in external_results:
                service = result.get('source', 'unknown').lower()
                if service not in by_service:
                    by_service[service] = []
                by_service[service].append(result)
            
            # Add each service
            for service, service_results in by_service.items():
                service_item = QTreeWidgetItem(self.treeWidget)
                service_item.setText(0, service.capitalize())
                service_item.setText(2, "Servicio")
                
                # Add service icon
                service_item.setIcon(0, self.service_icons.get(service, self.service_icons.get('unknown')))
                
                # Format as bold
                font = service_item.font(0)
                font.setBold(True)
                service_item.setFont(0, font)
                
                # Group by artist
                by_artist = {}
                standalone_items = []
                
                for result in service_results:
                    artist_name = result.get('artist', '')
                    item_type = result.get('type', '').lower()
                    
                    if item_type == 'artist':
                        by_artist[artist_name] = result
                    elif item_type == 'album' and artist_name:
                        if artist_name not in by_artist:
                            by_artist[artist_name] = {
                                'title': artist_name,
                                'artist': artist_name,
                                'type': 'artist',
                                'albums': []
                            }
                        if 'albums' not in by_artist[artist_name]:
                            by_artist[artist_name]['albums'] = []
                        by_artist[artist_name]['albums'].append(result)
                    else:
                        standalone_items.append(result)
                
                # Add artists with their content
                for artist_name, artist_data in by_artist.items():
                    artist_item = QTreeWidgetItem(service_item)
                    artist_item.setText(0, artist_name)
                    artist_item.setText(1, artist_name)
                    artist_item.setText(2, "Artista")
                    
                    # Format as bold
                    font = artist_item.font(0)
                    font.setBold(True)
                    artist_item.setFont(0, font)
                    
                    # Store complete data
                    artist_item.setData(0, Qt.ItemDataRole.UserRole, artist_data)
                    
                    # Add albums
                    if 'albums' in artist_data and artist_data['albums']:
                        for album in artist_data['albums']:
                            album_item = self._add_result_to_tree(album, artist_item)
                    
                    # Expand artist item
                    artist_item.setExpanded(True)
                
                # Add standalone items
                for item in standalone_items:
                    self._add_result_to_tree(item, service_item)
                
                # Expand service item
                service_item.setExpanded(True)
                
                # Add result count badge to service
                service_count = len(service_results)
                if service_count > 0:
                    service_item.setText(0, f"{service.capitalize()} ({service_count})")
        
        # Update count of results
        new_count = self.treeWidget.topLevelItemCount() - initial_count
        self.textEdit.append(f"Se encontraron {len(results)} resultados")
        QApplication.processEvents()
        
        # Select the first item if exists
        if self.treeWidget.topLevelItemCount() > 0:
            first_root = self.treeWidget.topLevelItem(0)
            
            if first_root.childCount() > 0:
                first_child = first_root.child(0)
                self.treeWidget.setCurrentItem(first_child)
                
                # Try to display info for this item
                item_data = first_child.data(0, Qt.ItemDataRole.UserRole)
                if item_data:
                    self.display_wiki_info(item_data)

    def _add_result_to_tree(self, result, parent_item):
        """Add a single result to the tree with proper nesting for album tracks."""
        item_type = result.get('type', '').lower()
        title = result.get('title', 'Unknown')
        artist = result.get('artist', '')
        from_db = result.get('from_database', False)
        
        # Create item for result
        result_item = QTreeWidgetItem(parent_item)
        result_item.setText(0, title)
        result_item.setText(1, artist)
        
        # Set type with database indicator
        db_indicator = " (DB)" if from_db else ""
        
        if item_type == 'artist':
            result_item.setText(2, f"Artista{db_indicator}")
        elif item_type == 'album':
            result_item.setText(2, f"Álbum{db_indicator}")
            if result.get('year'):
                result_item.setText(3, str(result.get('year')))
        elif item_type in ['track', 'song']:
            result_item.setText(2, f"Canción{db_indicator}")
            if result.get('track_number'):
                result_item.setText(3, str(result.get('track_number')))
            if result.get('duration'):
                duration_str = self.format_duration(result.get('duration'))
                result_item.setText(4, duration_str)
        else:
            result_item.setText(2, f"{item_type.capitalize()}{db_indicator}")
        
        # Store complete data
        result_item.setData(0, Qt.ItemDataRole.UserRole, result)
        
        # CRITICAL: Add albums for artists correctly
        if item_type == 'artist' and 'albums' in result and result['albums']:
            self.log(f"Añadiendo {len(result['albums'])} álbumes al artista {title}")
            
            # Add each album as a child
            for album in result['albums']:
                album_item = QTreeWidgetItem(result_item)
                album_item.setText(0, album.get('title', 'Álbum sin título'))
                album_item.setText(1, title)  # Artist name
                album_item.setText(2, f"Álbum{db_indicator}")
                
                # Add year if available
                if album.get('year'):
                    album_item.setText(3, str(album.get('year')))
                
                # Store album data
                album_item.setData(0, Qt.ItemDataRole.UserRole, album)
                
                # Add tracks if available
                if 'tracks' in album and album['tracks']:
                    for track in album['tracks']:
                        track_item = QTreeWidgetItem(album_item)
                        track_item.setText(0, track.get('title', 'Unknown Track'))
                        track_item.setText(1, title)  # Artist name
                        track_item.setText(2, f"Canción{db_indicator}")
                        
                        # Add track number if available
                        if track.get('track_number'):
                            track_item.setText(3, str(track.get('track_number')))
                        
                        # Add duration if available
                        if track.get('duration'):
                            duration_str = self.format_duration(track.get('duration'))
                            track_item.setText(4, duration_str)
                        
                        # Store track data
                        track_item.setData(0, Qt.ItemDataRole.UserRole, track)
        
        # Add tracks for albums correctly
        elif item_type == 'album' and 'tracks' in result and result['tracks']:
            # Get the tracks from the result
            tracks = result['tracks']
            
            # Sort tracks by track number if available
            if tracks and all(t.get('track_number') is not None for t in tracks):
                try:
                    # Try to sort tracks by track number
                    tracks = sorted(
                        tracks, 
                        key=lambda t: (int(t.get('track_number', 9999)) 
                            if t.get('track_number') and str(t.get('track_number')).isdigit() 
                            else 9999)
                    )
                except Exception as e:
                    self.log(f"Error sorting tracks: {str(e)}")
            
            # Log for debugging
            self.log(f"Añadiendo {len(tracks)} pistas al álbum {result.get('title')}")
            
            for track in tracks:
                # Create track item
                track_item = QTreeWidgetItem(result_item)
                track_item.setText(0, track.get('title', 'Unknown Track'))
                track_item.setText(1, track.get('artist', artist))
                track_item.setText(2, f"Canción{db_indicator}")
                
                # Add track number
                if track.get('track_number'):
                    try:
                        # Handle track numbers like "1/10"
                        track_num = str(track.get('track_number')).split('/')[0]
                        track_item.setText(3, track_num)
                    except:
                        track_item.setText(3, str(track.get('track_number')))
                
                # Add duration
                if track.get('duration'):
                    duration_str = self.format_duration(track.get('duration'))
                    track_item.setText(4, duration_str)
                
                # Ensure track has complete information
                track_data = track.copy()  # Make a copy to avoid modifying the original
                
                # Add missing information
                if 'album' not in track_data:
                    track_data['album'] = result.get('title')
                if 'artist' not in track_data and artist:
                    track_data['artist'] = artist
                if 'from_database' not in track_data:
                    track_data['from_database'] = from_db
                
                # CRITICAL FIX FOR BANDCAMP: Ensure URL is preserved
                if ('url' not in track_data or not track_data['url']) and result.get('url'):
                    # If track has no URL but we have album URL, create a fallback
                    # This helps with Bandcamp tracks that might not have individual URLs
                    track_data['url'] = result.get('url')
                    self.log(f"Using album URL for track: {track_data['title']}")
                
                # Store the enhanced track data
                track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
        
        return result_item

    def _process_database_results(self, db_links):
        """Process database links into results with proper hierarchy, including file paths."""
        results = []
        
        # Process artists with their albums and tracks
        for artist_name, artist_data in db_links.get('artists', {}).items():
            # Try to fetch paths for this artist
            paths_data = self.fetch_artist_song_paths(artist_name)
            
            artist_result = {
                "source": "local",
                "title": artist_name,
                "artist": artist_name,
                "type": "artist",
                "from_database": True
            }
            
            # Add links if available
            if 'links' in artist_data:
                artist_result['links'] = artist_data['links']
            
            # Process albums
            if 'albums' in artist_data and artist_data['albums']:
                artist_albums = []
                
                for album in artist_data['albums']:
                    album_title = album.get('title', album.get('name', ''))
                    
                    album_result = {
                        "source": "local",
                        "title": album_title,
                        "artist": artist_name,
                        "type": "album",
                        "year": album.get('year'),
                        "from_database": True
                    }
                    
                    # Add links if available
                    if 'links' in album:
                        album_result['links'] = album['links']
                    
                    # Process tracks and add paths if available
                    if 'tracks' in album and album['tracks']:
                        album_tracks = []
                        
                        for track in album['tracks']:
                            track_title = track.get('title', '')
                            track_result = {
                                "source": "local",
                                "title": track_title,
                                "artist": artist_name,
                                "album": album_title,
                                "type": "track",
                                "track_number": track.get('track_number'),
                                "duration": track.get('duration'),
                                "from_database": True
                            }
                            
                            # Add links if available
                            if 'links' in track:
                                track_result['links'] = track['links']
                            
                            # Try to find the file path from paths_data
                            if paths_data and 'albums' in paths_data:
                                # Look for the album in paths_data
                                for album_key, album_data in paths_data['albums'].items():
                                    if album_data['nombre'] == album_title:
                                        # Look for the track in the album
                                        for song in album_data['canciones']:
                                            if song['título'] == track_title:
                                                track_result['file_path'] = song['ruta']
                                                break
                            
                            album_tracks.append(track_result)
                        
                        # Add tracks to album result
                        album_result['tracks'] = album_tracks
                    
                    artist_albums.append(album_result)
                
                # Add albums to artist result
                artist_result['albums'] = artist_albums
            
            results.append(artist_result)
        
        # Process standalone albums (not associated with artists)
        for album_key, album_data in db_links.get('albums', {}).items():
            # Skip albums already processed through artists
            artist_name = album_data.get('artist', '')
            album_title = album_data.get('title', '')
            
            # Check if this album was already added through an artist
            already_added = False
            for result in results:
                if result.get('type') == 'artist' and result.get('title') == artist_name:
                    for album in result.get('albums', []):
                        if album.get('title') == album_title:
                            already_added = True
                            break
                    if already_added:
                        break
            
            if already_added:
                continue
            
            album_result = {
                "source": "local",
                "title": album_title,
                "artist": artist_name,
                "type": "album",
                "year": album_data.get('year'),
                "from_database": True
            }
            
            # Add links if available
            if 'links' in album_data:
                album_result['links'] = album_data['links']
            
            # Process tracks
            if 'tracks' in album_data and album_data['tracks']:
                album_tracks = []
                
                for track in album_data['tracks']:
                    track_result = {
                        "source": "local",
                        "title": track.get('title', ''),
                        "artist": artist_name,
                        "album": album_title,
                        "type": "track",
                        "track_number": track.get('track_number'),
                        "duration": track.get('duration'),
                        "from_database": True
                    }
                    
                    # Add links if available
                    if 'links' in track:
                        track_result['links'] = track['links']
                    
                    album_tracks.append(track_result)
                
                # Add tracks to album result
                album_result['tracks'] = album_tracks
            
            results.append(album_result)
        
        # Process standalone tracks
        for track_key, track_data in db_links.get('tracks', {}).items():
            # Skip tracks already processed through albums
            album_title = track_data.get('album', '')
            artist_name = track_data.get('artist', '')
            track_title = track_data.get('title', '')
            
            # Check if this track was already added through an album
            already_added = False
            for result in results:
                if result.get('type') == 'artist' and result.get('title') == artist_name:
                    for album in result.get('albums', []):
                        if album.get('title') == album_title:
                            for track in album.get('tracks', []):
                                if track.get('title') == track_title:
                                    already_added = True
                                    break
                            if already_added:
                                break
                    if already_added:
                        break
                elif result.get('type') == 'album' and result.get('title') == album_title:
                    for track in result.get('tracks', []):
                        if track.get('title') == track_title:
                            already_added = True
                            break
                    if already_added:
                        break
            
            if already_added:
                continue
            
            track_result = {
                "source": "local",
                "title": track_title,
                "artist": artist_name,
                "album": album_title,
                "type": "track",
                "track_number": track_data.get('track_number'),
                "duration": track_data.get('duration'),
                "from_database": True
            }
            
            # Add links if available
            if 'links' in track_data:
                track_result['links'] = track_data['links']
            
            results.append(track_result)
        
        return results


    def _is_duplicate_result(self, result):
        """
        Checks if a result is a duplicate of something already in the tree.
        
        Args:
            result: The result dictionary to check
            
        Returns:
            bool: True if it's a duplicate, False otherwise
        """
        item_type = result.get('type', '').lower()
        artist_name = result.get('artist', '').lower()
        title = result.get('title', '').lower()
        
        if item_type == 'artist':
            return artist_name in self.added_items['artists']
        elif item_type == 'album':
            album_key = f"{artist_name} - {title}"
            return album_key in self.added_items['albums']
        elif item_type in ['track', 'song']:
            track_key = f"{artist_name} - {title}"
            return track_key in self.added_items['tracks']
        
        return False


    def _add_database_results(self, db_results):
        """
        Adds database results to the tree in a hierarchical manner.
        Ensures proper tracking of added items.
        """
        for result in db_results:
            if result.get('type', '').lower() == 'artist' and result.get('artist'):
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
                
                # Track this artist
                self.added_items['artists'].add(artist_name.lower())
                
                # Añadir álbumes
                for album in result.get('albums', []):
                    album_name = album.get('title', 'Unknown Album')
                    
                    # Crear item de álbum
                    album_item = QTreeWidgetItem(artist_item)
                    album_item.setText(0, album_name)
                    album_item.setText(1, artist_name)
                    album_item.setText(2, "Álbum")
                    
                    # Add year information if available
                    if album.get('year'):
                        album_item.setText(3, str(album.get('year')))
                    
                    # Almacenar datos del álbum
                    album_item.setData(0, Qt.ItemDataRole.UserRole, album)
                    
                    # Track this album
                    album_key = f"{artist_name.lower()} - {album_name.lower()}"
                    self.added_items['albums'].add(album_key)
                    
                    # Añadir canciones del álbum
                    for track in album.get('tracks', []):
                        track_name = track.get('title', 'Canción sin título')
                        
                        track_item = QTreeWidgetItem(album_item)
                        track_item.setText(0, track_name)
                        track_item.setText(1, artist_name)
                        track_item.setText(2, "Canción")
                        
                        # Add track number if available
                        if track.get('track_number'):
                            track_item.setText(3, str(track.get('track_number')))
                        
                        # Add duration if available
                        if track.get('duration'):
                            duration_str = self.format_duration(track.get('duration'))
                            track_item.setText(4, duration_str)
                        
                        # Almacenar datos de la canción
                        track_item.setData(0, Qt.ItemDataRole.UserRole, track)
                        
                        # Track this track
                        track_key = f"{artist_name.lower()} - {track_name.lower()}"
                        self.added_items['tracks'].add(track_key)

    def _add_service_results(self, service_results):
        """
        Adds external service results to the tree, skipping duplicates.
        """
        # Group results by service
        for result in service_results:
            service = result.get('source', 'Otros').capitalize()
            
            # Create a root item for the service if it doesn't exist yet
            service_items = self.treeWidget.findItems(service, Qt.MatchFlag.MatchExactly, 0)
            service_item = None
            
            if not service_items:
                service_item = QTreeWidgetItem(self.treeWidget)
                service_item.setText(0, service)
                service_item.setText(2, "Servicio")
                
                # Format as bold
                font = service_item.font(0)
                font.setBold(True)
                service_item.setFont(0, font)
            else:
                service_item = service_items[0]
            
            # Add result as child of service
            item_type = result.get('type', '').lower()
            title = result.get('title', 'Unknown')
            artist = result.get('artist', '')
            
            # Create item for result
            result_item = QTreeWidgetItem(service_item)
            result_item.setText(0, title)
            result_item.setText(1, artist)
            
            # Set type
            if item_type == 'artist':
                result_item.setText(2, "Artista")
            elif item_type == 'album':
                result_item.setText(2, "Álbum")
                if result.get('year'):
                    result_item.setText(3, str(result.get('year')))
            elif item_type in ['track', 'song']:
                result_item.setText(2, "Canción")
                if result.get('track_number'):
                    result_item.setText(3, str(result.get('track_number')))
                if result.get('duration'):
                    duration_str = self.format_duration(result.get('duration'))
                    result_item.setText(4, duration_str)
            else:
                result_item.setText(2, item_type.capitalize())
            
            # Store complete data
            result_item.setData(0, Qt.ItemDataRole.UserRole, result)
            
            # Track this item to avoid future duplicates
            if item_type == 'artist':
                self.added_items['artists'].add(artist.lower())
            elif item_type == 'album':
                album_key = f"{artist.lower()} - {title.lower()}"
                self.added_items['albums'].add(album_key)
            elif item_type in ['track', 'song']:
                track_key = f"{artist.lower()} - {title.lower()}"
                self.added_items['tracks'].add(track_key)
            
        self.log(f"Added {len(service_results)} service results to tree")
                        
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
        """Adds the selected item to the playback queue without changing tabs."""
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
        """Add a specific item to the queue with appropriate icon."""
        title = item.text(0)
        artist = item.text(1)
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            return
        
        # Use our extraction function to get the best URL or file path
        url = None
        
        if isinstance(item_data, dict):
            # Check for file path first for local files
            url = item_data.get('file_path')
            
            # If no file path, then check URL
            if not url:
                url = item_data.get('url')
            
            # For database items that might not have a direct URL
            if not url and item_data.get('source', '').lower() in ['database', 'local']:
                # Try to find a playable URL in the links
                if 'links' in item_data:
                    for service, service_url in item_data['links'].items():
                        if service_url:
                            url = service_url
                            break
            
            # For Bandcamp tracks, ensure we have a usable URL
            if not url and item_data.get('source', '').lower() == 'bandcamp':
                url = self.extract_playable_url(item_data)
                self.log(f"Extracted Bandcamp playable URL: {url}")
        else:
            url = str(item_data)
        
        if not url:
            self.log(f"No URL or file path found for: {title}")
            return
        
        # Create a new item for the playlist
        display_text = title
        if artist:
            display_text = f"{artist} - {title}"
        
        # Create the item with appropriate icon
        queue_item = QListWidgetItem(display_text)
        queue_item.setData(Qt.ItemDataRole.UserRole, url)
        
        # Determine source for icon
        source = item_data.get('source', '') if isinstance(item_data, dict) else ''
        icon = self.get_source_icon(url, {'source': source})
        queue_item.setIcon(icon)
        
        # Add to the list
        self.listWidget.addItem(queue_item)
        
        # Update internal playlist - include file_path if available
        entry_data = item.data(0, Qt.ItemDataRole.UserRole + 1) or item_data
        playlist_item = {
            'title': title, 
            'artist': artist, 
            'url': url,
            'source': source or self._determine_source_from_url(url),
            'entry_data': entry_data
        }
        
        # Add file_path if it exists in the item data
        if isinstance(item_data, dict) and 'file_path' in item_data:
            playlist_item['file_path'] = item_data['file_path']
        
        self.current_playlist.append(playlist_item)
        
        self.log(f"Added to queue: {display_text} with URL/path: {url}")
    
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
        """Rebuilds the playlist from the ListWidget, preserving icons and source information."""
        self.current_playlist = []
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            text = item.text()
            url = item.data(Qt.ItemDataRole.UserRole)
            
            # Extract artist if present in the format "Artist - Title"
            artist = ""
            title = text
            if " - " in text:
                parts = text.split(" - ", 1)
                artist = parts[0]
                title = parts[1]
            
            # Determine source from URL if not available from icon
            source = self._determine_source_from_url(url)
            
            self.current_playlist.append({
                'title': title, 
                'artist': artist, 
                'url': url,
                'source': source,
                'entry_data': None  # No full data available in this case
            })
            
        self.log(f"Playlist rebuilt with {len(self.current_playlist)} items")



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
        """Load API credentials with consistent path handling"""
        # Define standard paths
        token_path = self.get_app_path(".content/cache/spotify_token.txt")
        playlist_path = self.get_app_path(".content/cache/spotify_playlist.json")
        
        # First check config values
        spotify_client_id = self.spotify_client_id
        spotify_client_secret = self.spotify_client_secret
        lastfm_api_key = self.lastfm_api_key
        
        # If not available, try environment variables
        if not spotify_client_id:
            spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        if not spotify_client_secret:
            spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        if not lastfm_api_key:
            lastfm_api_key = os.environ.get("LASTFM_API_KEY")
        
        # Create cache directory if it doesn't exist
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        
        # Store the standard paths
        self.spotify_token_path = token_path
        self.spotify_playlist_path = playlist_path
        
        # Set environment variables for imported modules
        if spotify_client_id:
            os.environ["SPOTIFY_CLIENT_ID"] = spotify_client_id
        if spotify_client_secret:
            os.environ["SPOTIFY_CLIENT_SECRET"] = spotify_client_secret
        if lastfm_api_key:
            os.environ["LASTFM_API_KEY"] = lastfm_api_key
        
        # Update service flags
        self.spotify_enabled = bool(spotify_client_id and spotify_client_secret)
        self.lastfm_enabled = bool(lastfm_api_key)


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


    def setup_service_icons(self):
        """Configura iconos para cada servicio."""
        self.service_icons = {
            'local': QIcon(":/services/plslove"),  
            'database': QIcon(":/services/database"),
            'bandcamp': QIcon(":/services/bandcamp"),
            'spotify': QIcon(":/services/spotify"),
            'lastfm': QIcon(":/services/lastfm"),
            'youtube': QIcon(":/services/youtube"),
            'soundcloud': QIcon(":/services/soundcloud"),
            'unknown': QIcon(":/services/wiki"),
            'loading': QIcon(":services/loading")
        }

        # Guardar el icono original del botón de búsqueda para restaurarlo después
        if hasattr(self, 'searchButton'):
            self.original_search_icon = self.searchButton.icon()

    def setup_loading_indicator(self):
        """Configura un indicador de carga simple que no interfiere con la UI."""
        try:
            from PyQt6.QtWidgets import QLabel
            from PyQt6.QtGui import QMovie
            from PyQt6.QtCore import QSize
            
            # Crear un simple label para el indicador
            self.loading_label = QLabel(self)
            self.loading_label.setFixedSize(QSize(24, 24))
            
            # Cargar el gif animado
            self.loading_movie = QMovie(":/services/loading")
            if self.loading_movie.isValid():
                self.loading_movie.setScaledSize(QSize(24, 24))
                self.loading_label.setMovie(self.loading_movie)
            
            # Posicionar junto al botón de búsqueda pero sin alterar layouts
            button_pos = self.searchButton.pos()
            self.loading_label.move(button_pos.x() - 1, button_pos.y() + 1)
            
            # Inicialmente oculto
            self.loading_label.hide()
            
        except Exception as e:
            self.log(f"Error setting up loading indicator: {str(e)}")

    def _update_button_icon(self):
        """Actualiza el icono del botón con el frame actual del GIF."""
        if hasattr(self, 'loading_movie') and self.loading_movie.isValid():
            # Crear un QIcon a partir del frame actual del QMovie
            from PyQt6.QtGui import QIcon, QPixmap
            pixmap = self.loading_movie.currentPixmap()
            icon = QIcon(pixmap)
            
            # Aplicar al botón
            self.searchButton.setIcon(icon)


    def show_loading_indicator(self, visible=True):
        """Cambia el icono del botón de búsqueda entre el icono normal y el GIF de carga."""
        try:
            if visible:
                # Crear un QMovie con el GIF
                from PyQt6.QtGui import QMovie
                from PyQt6.QtCore import QSize
                
                # Si no tenemos ya el movie creado
                if not hasattr(self, 'loading_movie'):
                    self.loading_movie = QMovie(":/services/loading")
                    
                    if self.loading_movie.isValid():
                        # Configurar el tamaño adecuado para que coincida con el icono original
                        icon_size = self.searchButton.iconSize()
                        self.loading_movie.setScaledSize(icon_size)
                        
                        # Conectar una señal para actualizar el icono del botón con cada frame
                        self.loading_movie.frameChanged.connect(lambda: self._update_button_icon())
                    else:
                        self.log("Error: GIF de carga no válido")
                        return
                
                # Iniciar la animación
                self.loading_movie.start()
                
                # Aplicar el primer frame al botón
                self._update_button_icon()
                
                # Mantener el botón habilitado para que el usuario pueda cancelar si lo desea
                self.searchButton.setEnabled(True)
            else:
                # Detener la animación si existe
                if hasattr(self, 'loading_movie'):
                    self.loading_movie.stop()
                
                # Restaurar el icono original
                if hasattr(self, 'original_search_icon'):
                    self.searchButton.setIcon(self.original_search_icon)
                
                # Asegurarse de que el botón esté habilitado
                self.searchButton.setEnabled(True)
            
            # Procesar eventos para actualizar la UI
            QApplication.processEvents()
            
        except Exception as e:
            self.log(f"Error al cambiar icono de carga: {str(e)}")
            # Restaurar el estado original en caso de error
            if hasattr(self, 'original_search_icon'):
                self.searchButton.setIcon(self.original_search_icon)
            self.searchButton.setEnabled(True)


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

    def get_spotify_token(self):
        """Get or refresh Spotify API token"""
        if not self.spotify_enabled:
            return None
        
        token = None
        token_expired = True
        
        # Try to read existing token
        if os.path.exists(self.spotify_token_path):
            try:
                with open(self.spotify_token_path, 'r') as f:
                    token_data = json.load(f)
                    token = token_data.get('access_token')
                    expires_at = token_data.get('expires_at', 0)
                    
                    # Check if token is still valid (with 60 second margin)
                    if expires_at > time.time() + 60:
                        token_expired = False
            except Exception as e:
                self.log(f"Error reading Spotify token: {e}")
        
        # Refresh token if needed
        if token_expired:
            token = self._refresh_spotify_token()
        
        return token

    def _refresh_spotify_token(self):
        """Refresh Spotify API token and save it to disk"""
        if not self.spotify_client_id or not self.spotify_client_secret:
            return None
            
        try:
            # Use requests to get a new token
            auth_url = 'https://accounts.spotify.com/api/token'
            auth_header = base64.b64encode(f"{self.spotify_client_id}:{self.spotify_client_secret}".encode()).decode()
            
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {'grant_type': 'client_credentials'}
            
            response = requests.post(auth_url, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Add expires_at timestamp
                token_data['expires_at'] = time.time() + token_data['expires_in']
                
                # Save token to file
                with open(self.spotify_token_path, 'w') as f:
                    json.dump(token_data, f)
                    
                self.log("Spotify token refreshed successfully")
                return token_data['access_token']
            else:
                self.log(f"Error refreshing Spotify token: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            self.log(f"Exception refreshing Spotify token: {e}")
            return None

    def load_playlists(self):
        """Load playlists from the standard location"""
        if not os.path.exists(self.spotify_playlist_path):
            # Create empty playlist structure
            playlists = {
                'spotify': [],
                'local': [],
                'rss': []
            }
            self.save_playlists(playlists)
            return playlists
        
        try:
            with open(self.spotify_playlist_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.log(f"Error loading playlists: {e}")
            return {'spotify': [], 'local': [], 'rss': []}

    def save_playlists(self, playlists=None):
        """Save playlists to the standard location"""
        if playlists is None:
            playlists = self.playlists
        
        try:
            with open(self.spotify_playlist_path, 'w') as f:
                json.dump(playlists, f, indent=2)
            self.log("Playlists saved successfully")
        except Exception as e:
            self.log(f"Error saving playlists: {e}")

    def setup_spotify(self, client_id=None, client_secret=None, cache_path=None):
        """Configure Spotify client with improved token management"""
        try:
            # Si ya tienes los valores de tus credenciales, úsalos
            if not client_id:
                client_id = self.spotify_client_id
            
            if not client_secret:
                client_secret = self.spotify_client_secret
                
            if not client_id or not client_secret:
                self.log("Spotify client ID and secret are required for Spotify functionality")
                return False
                
            print("Setting up Spotify client...")
            
            # Ensure cache directory exists - usa la ruta que prefieras
            if not cache_path:
                cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "music_app", "spotify")
                os.makedirs(cache_dir, exist_ok=True)
                cache_path = os.path.join(cache_dir, "spotify_token.txt")
                
            print(f"Using token cache path: {cache_path}")
            
            # Define scope for Spotify permissions
            scope = "playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative"
            
            # Create a new OAuth instance
            try:
                import spotipy
                from spotipy.oauth2 import SpotifyOAuth
                
                self.sp_oauth = SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri='http://localhost:8998',
                    scope=scope,
                    open_browser=False,
                    cache_path=cache_path
                )
                
                # Intenta obtener el token usando tu método existente primero
                token_info = None
                if hasattr(self, '_load_api_credentials_from_env'):
                    self._load_api_credentials_from_env()  # Tu método existente
                    
                    # Si después de cargar las credenciales tenemos un token, úsalo
                    if hasattr(self, 'spotify_token') and self.spotify_token:
                        token_info = {'access_token': self.spotify_token}
                
                # Si no tenemos token, usar el nuevo método
                if not token_info:
                    token_info = self.get_token_or_authenticate()
                
                # Create Spotify client with the token
                print("Creating Spotify client with token")
                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                
                print("Getting current user info")
                user_info = self.sp.current_user()
                self.spotify_user_id = user_info['id']
                print(f"Authenticated as user: {self.spotify_user_id}")
                
                # Flag that Spotify is authenticated
                self.spotify_authenticated = True
                return True
                
            except ImportError:
                self.log("spotipy module not found. Please install it with 'pip install spotipy'")
                return False
            except Exception as e:
                print(f"Spotify setup error: {str(e)}")
                import traceback
                traceback.print_exc()
                self.log(f"Error de autenticación con Spotify: {str(e)}")
                return False
                
        except Exception as e:
            self.log(f"Error setting up Spotify: {str(e)}")
            return False


    def get_token_or_authenticate(self):
        """Get valid token or initiate authentication"""
        try:
            # Si ya tienes un token desde tu método existente, úsalo
            if hasattr(self, 'spotify_token') and self.spotify_token:
                return {'access_token': self.spotify_token}
                
            # Check if we have a valid cached token
            token_info = None
            try:
                cached_token = self.sp_oauth.get_cached_token()
                if cached_token and not self.sp_oauth.is_token_expired(cached_token):
                    print("Using valid cached token")
                    return cached_token
                elif cached_token:
                    print("Cached token is expired, trying to refresh")
                    try:
                        new_token = self.sp_oauth.refresh_access_token(cached_token['refresh_token'])
                        print("Token refreshed successfully")
                        return new_token
                    except Exception as e:
                        print(f"Token refresh failed: {str(e)}")
                        # If refresh fails, we'll continue to new authentication
                else:
                    print("No valid cached token found")
            except Exception as e:
                print(f"Error checking cached token: {str(e)}")
                # Continue to new authentication
            
            # If we get here, we need to authenticate from scratch
            print("Starting new authentication flow")
            return self.perform_new_authentication()
        except Exception as e:
            print(f"Error in get_token_or_authenticate: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def perform_new_authentication(self):
        """Perform new authentication from scratch"""
        # Get the authorization URL
        auth_url = self.sp_oauth.get_authorize_url()
        
        # Show instructions dialog with the URL
        from PyQt6.QtWidgets import QMessageBox, QInputDialog, QLineEdit
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Autorización de Spotify")
        msg_box.setText(
            "Para usar las funciones de Spotify, necesita autorizar esta aplicación.\n\n"
            "1. Copie el siguiente enlace y ábralo manualmente en su navegador:\n\n"
            f"{auth_url}\n\n"
            "2. Inicie sesión en Spotify si se le solicita.\n"
            "3. Haga clic en 'Agree' para autorizar la aplicación.\n"
            "4. Será redirigido a una página. Copie la URL completa de esa página."
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg_box.button(QMessageBox.StandardButton.Ok).setText("Continuar")
        
        if msg_box.exec() == QMessageBox.StandardButton.Cancel:
            raise Exception("Autorización cancelada por el usuario")
        
        # Use QInputDialog for the redirect URL
        redirect_url, ok = QInputDialog.getText(
            self,
            "Ingrese URL de redirección",
            "Después de autorizar en Spotify, copie la URL completa de la página a la que fue redirigido:",
            QLineEdit.EchoMode.Normal,
            ""
        )
        
        if not ok or not redirect_url:
            raise Exception("Autorización cancelada por el usuario")
        
        # Process the URL to get the authorization code
        try:
            import urllib.parse
            
            # Handle URL-encoded URLs
            if '%3A' in redirect_url or '%2F' in redirect_url:
                redirect_url = urllib.parse.unquote(redirect_url)
            
            print(f"Processing redirect URL: {redirect_url[:30]}...")
            
            # Extract the code from the URL
            code = None
            if redirect_url.startswith('http'):
                code = self.sp_oauth.parse_response_code(redirect_url)
            elif 'code=' in redirect_url:
                code = redirect_url.split('code=')[1].split('&')[0]
            else:
                code = redirect_url
            
            if not code or code == redirect_url:
                raise Exception("No se pudo extraer el código de autorización")
            
            print(f"Extracted code: {code[:5]}...")
            
            # Get token with the code
            token_info = self.sp_oauth.get_access_token(code)
            
            if not token_info or 'access_token' not in token_info:
                raise Exception("No se pudo obtener el token de acceso")
            
            print("Authentication successful")
            return token_info
            
        except Exception as e:
            print(f"Error processing authentication: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Show error and offer retry
            from PyQt6.QtWidgets import QMessageBox
            
            retry = QMessageBox.question(
                self,
                "Error de autenticación",
                f"Ocurrió un error: {str(e)}\n\n¿Desea intentar nuevamente?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if retry == QMessageBox.StandardButton.Yes:
                return self.perform_new_authentication()
            else:
                raise Exception("Autenticación fallida")



    def refresh_token(self):
        """Refresh token if necessary"""
        try:
            token_info = self.sp_oauth.get_cached_token()
            if token_info and self.sp_oauth.is_token_expired(token_info):
                print("Refreshing expired token")
                token_info = self.sp_oauth.refresh_access_token(token_info['refresh_token'])
                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                return True
            return False
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # If refresh fails, try getting a new token
            try:
                print("Attempting new authentication after refresh failure")
                token_info = self.perform_new_authentication()
                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                return True
            except Exception as e2:
                print(f"New authentication also failed: {str(e2)}")
                self.log(f"Error renovando token: {str(e)}")
                return False

    def api_call_with_retry(self, func, *args, **kwargs):
        """Execute API call with retry if token expires"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"API call failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    if "token" in str(e).lower():
                        print("Token error detected, refreshing...")
                        if self.refresh_token():
                            print("Token refreshed, retrying...")
                            continue
                        else:
                            print("Token refresh failed")
                    else:
                        print("Non-token error")
                
                # Last attempt failed or it's not a token error
                raise



    def load_spotify_playlists(self, force_update=False):
        """Load user Spotify playlists from cache or Spotify"""
        if not hasattr(self, 'sp') or not self.sp:
            self.log("Spotify client not initialized")
            return False
            
        try:
            cache_path = os.path.join(os.path.expanduser("~"), ".cache", "music_app", "spotify", "playlists.json")
            
            if not force_update and os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    self.update_spotify_playlists_ui(cached_data['items'])
                    self.log("Spotify playlists loaded from cache")
                    return True

            results = self.api_call_with_retry(self.sp.current_user_playlists)
            
            # Save to cache
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            self.update_spotify_playlists_ui(results['items'])
            return True
            
        except Exception as e:
            self.log(f"Error loading Spotify playlists: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return False

    def update_spotify_playlists_ui(self, playlists_data):
        """Update UI with Spotify playlist data"""
        # First clear the combo box keeping only the first "New Playlist" item
        combo = self.playlist_spotify_comboBox
        while combo.count() > 1:
            combo.removeItem(1)
        
        # Store playlists for later use
        self.spotify_playlists = {}
        
        for playlist in playlists_data:
            playlist_name = playlist['name']
            playlist_id = playlist['id']
            
            # Store the playlist
            self.spotify_playlists[playlist_name] = playlist
            
            # Add to combo box
            from PyQt6.QtGui import QIcon
            combo.addItem(QIcon(":/services/spotify"), playlist_name)
        
        # Connect signal if not already connected
        try:
            combo.currentIndexChanged.disconnect(self.on_spotify_playlist_changed)
        except:
            pass
        combo.currentIndexChanged.connect(self.on_spotify_playlist_changed)
        
        self.log(f"Loaded {len(playlists_data)} Spotify playlists")


    def get_local_playlist_path(self):
        """Get the local playlist save path from configuration."""
        # Default path if not specified in config
        default_path = PROJECT_ROOT / ".content" / "local_playlists"
        
        try:
            # Try to read from config
            config_path = self.get_app_path("config/config.yml")
            if not os.path.exists(config_path):
                os.makedirs(os.path.dirname(default_path), exist_ok=True)
                return default_path
            
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Check global configuration first
            if 'global_theme_config' in config and 'local_playlist_path' in config['global_theme_config']:
                path = config['global_theme_config']['local_playlist_path']
                # Handle relative paths
                if not os.path.isabs(path):
                    path = os.path.join(PROJECT_ROOT, path)
                return path
            
            # Then check module configuration
            for module in config.get('modules', []):
                if module.get('name') in ['Url Playlists', 'URL Playlist', 'URL Player']:
                    if 'args' in module and 'local_playlist_path' in module['args']:
                        path = module['args']['local_playlist_path']
                        # Handle relative paths
                        if not os.path.isabs(path):
                            path = os.path.join(PROJECT_ROOT, path)
                        return path
            
            # Default if not found
            return default_path
        except Exception as e:
            self.log(f"Error reading local playlist path from config: {str(e)}")
            return default_path

    def on_spotify_playlist_changed(self, index):
        """Handle selection change in the Spotify playlist comboBox"""
        combo = self.playlist_spotify_comboBox
        selected_text = combo.currentText()
        
        if index == 0:  # "New Playlist" option
            self.show_create_spotify_playlist_dialog()
        else:
            # Show the selected playlist content
            if hasattr(self, 'spotify_playlists') and selected_text in self.spotify_playlists:
                playlist = self.spotify_playlists[selected_text]
                self.show_spotify_playlist_content(playlist['id'], playlist['name'])
        
    def show_create_spotify_playlist_dialog(self):
        """Show dialog to create a new Spotify playlist"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Crear Nueva Playlist de Spotify")
        
        layout = QVBoxLayout(dialog)
        
        # Name input
        layout.addWidget(QLabel("Nombre de la playlist:"))
        name_input = QLineEdit()
        layout.addWidget(name_input)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            playlist_name = name_input.text().strip()
            if playlist_name:
                self.create_spotify_playlist(playlist_name)
                
    def create_spotify_playlist(self, name):
        """Create a new Spotify playlist"""
        if not name:
            return
            
        if not hasattr(self, 'sp') or not self.sp:
            self.log("Spotify client not initialized")
            return
            
        try:
            self.sp.user_playlist_create(
                user=self.spotify_user_id,
                name=name,
                public=False,
                description="Created from Music App"
            )
            
            self.log(f"Playlist created: {name}")
            
            # Reload playlists to update UI
            self.load_spotify_playlists(force_update=True)
            
            # Select the newly created playlist in the comboBox
            combo = self.playlist_spotify_comboBox
            index = combo.findText(name)
            if index > 0:
                combo.setCurrentIndex(index)
                
        except Exception as e:
            self.log(f"Error creating playlist: {str(e)}")

    def show_spotify_playlist_content(self, playlist_id, playlist_name):
        """Show Spotify playlist tracks in the tree widget"""
        if not hasattr(self, 'sp') or not self.sp:
            self.log("Spotify client not initialized")
            return
            
        try:
            # Clear the tree widget
            self.treeWidget.clear()
            
            # Create a root item for the playlist
            from PyQt6.QtWidgets import QTreeWidgetItem
            from PyQt6.QtCore import Qt
            
            root_item = QTreeWidgetItem(self.treeWidget)
            root_item.setText(0, playlist_name)
            root_item.setText(1, "Spotify")
            root_item.setText(2, "Playlist")
            
            # Make the root item bold
            font = root_item.font(0)
            font.setBold(True)
            root_item.setFont(0, font)
            root_item.setFont(1, font)
            
            # Fetch tracks from Spotify
            results = self.api_call_with_retry(self.sp.playlist_items, playlist_id)
            
            # Add tracks as children of the root item
            for item in results['items']:
                if item['track']:
                    track = item['track']
                    
                    track_item = QTreeWidgetItem(root_item)
                    track_item.setText(0, track['name'])
                    
                    # Join artist names
                    artists = [artist['name'] for artist in track['artists']]
                    artist_str = ", ".join(artists)
                    track_item.setText(1, artist_str)
                    
                    track_item.setText(2, "Canción")
                    
                    # Add duration if available
                    if 'duration_ms' in track:
                        duration_ms = track['duration_ms']
                        minutes = int(duration_ms / 60000)
                        seconds = int((duration_ms % 60000) / 1000)
                        track_item.setText(4, f"{minutes}:{seconds:02d}")
                    
                    # Store track data for use with context menus, etc.
                    track_data = {
                        'source': 'spotify',
                        'title': track['name'],
                        'artist': artist_str,
                        'url': track['external_urls']['spotify'],
                        'type': 'track',
                        'spotify_id': track['id']
                    }
                    
                    # Store the data
                    track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
            
            # Expand the root item
            root_item.setExpanded(True)
            
            self.log(f"Loaded {len(results['items'])} tracks from playlist '{playlist_name}'")
            
        except Exception as e:
            self.log(f"Error loading playlist content: {str(e)}")
            print(traceback.format_exc())


    def add_to_spotify_playlist(self, track_data=None):
        """Add selected tracks to a Spotify playlist"""
        # If no track_data provided, get from selected items in tree
        if not track_data:
            selected_items = self.treeWidget.selectedItems()
            if not selected_items:
                self.log("No tracks selected")
                return
                
            # Get the data from the first selected item
            track_data = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        
        if not track_data:
            self.log("No valid track data found")
            return
            
        # Check if we have a Spotify client
        if not hasattr(self, 'sp') or not self.sp:
            self.log("Spotify client not initialized")
            return
            
        # Get a list of user's playlists to choose from
        if not hasattr(self, 'spotify_playlists') or not self.spotify_playlists:
            self.load_spotify_playlists()
            
        # Create a dialog to select a playlist
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Añadir a Playlist de Spotify")
        
        layout = QVBoxLayout(dialog)
        
        # Add a label with track info
        if isinstance(track_data, dict):
            track_name = track_data.get('title', 'Unknown Track')
            artist_name = track_data.get('artist', 'Unknown Artist')
            layout.addWidget(QLabel(f"Añadir '{track_name}' por {artist_name} a:"))
        else:
            layout.addWidget(QLabel("Seleccionar playlist:"))
        
        # Playlist selector
        playlist_combo = QComboBox()
        for name in self.spotify_playlists.keys():
            playlist_combo.addItem(name)
        layout.addWidget(playlist_combo)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_playlist = playlist_combo.currentText()
            if selected_playlist in self.spotify_playlists:
                playlist_id = self.spotify_playlists[selected_playlist]['id']
                
                # Get the track Spotify URI
                track_uri = None
                
                # If this is already a Spotify track, get its ID
                if isinstance(track_data, dict) and track_data.get('source') == 'spotify' and track_data.get('spotify_id'):
                    track_uri = f"spotify:track:{track_data['spotify_id']}"
                else:
                    # Try to search for the track on Spotify
                    track_uri = self.search_spotify_track_uri(track_data)
                    
                if track_uri:
                    try:
                        # Add the track to the playlist
                        self.sp.playlist_add_items(playlist_id, [track_uri])
                        self.log(f"Track added to playlist '{selected_playlist}'")
                    except Exception as e:
                        self.log(f"Error adding track to playlist: {str(e)}")
                else:
                    self.log("Could not find track on Spotify")

    def search_spotify_track_uri(self, track_data):
        """Search for a track on Spotify and return its URI"""
        if not hasattr(self, 'sp') or not self.sp:
            self.log("Spotify client not initialized")
            return None
            
        try:
            # Extract search terms
            if isinstance(track_data, dict):
                title = track_data.get('title', '')
                artist = track_data.get('artist', '')
                query = f"{title} artist:{artist}" if artist else title
            else:
                # If just a string was passed, use it as the query
                query = str(track_data)
            
            # Search Spotify
            results = self.api_call_with_retry(self.sp.search, q=query, type='track', limit=1)
            
            # Check if we got any results
            if results and 'tracks' in results and 'items' in results['tracks'] and results['tracks']['items']:
                track = results['tracks']['items'][0]
                return f"spotify:track:{track['id']}"
                
            return None
            
        except Exception as e:
            self.log(f"Error searching Spotify: {str(e)}")
            return None

    def setup_context_menus(self):
        """Set up context menus for tree and list widgets"""
        # Set custom context menu for treeWidget
        self.treeWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeWidget.customContextMenuRequested.connect(self.show_tree_context_menu)
        
        # Set custom context menu for listWidget
        self.listWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        #self.listWidget.customContextMenuRequested.connect(self.show_list_context_menu)


    def get_source_icon(self, url, metadata=None):
        """
        Determine the source icon for a URL or metadata.
        Returns a QIcon for the appropriate service.
        """
        if metadata and isinstance(metadata, dict) and 'source' in metadata:
            # If metadata has a source field, use that directly
            source = metadata['source'].lower()
        else:
            # Try to determine source from URL
            url = str(url).lower()
            if 'spotify.com' in url:
                source = 'spotify'
            elif 'youtube.com' in url or 'youtu.be' in url:
                source = 'youtube'
            elif 'soundcloud.com' in url:
                source = 'soundcloud'
            elif 'bandcamp.com' in url:
                source = 'bandcamp'
            elif url.startswith(('/', 'file:', '~', 'C:', 'D:')):
                # Local file paths
                # Check extension to determine audio file type
                if url.endswith(('.mp3', '.flac', '.wav', '.ogg', '.m4a', '.opus')):
                    source = 'local'
                else:
                    source = 'unknown'
            else:
                # Default or unknown
                source = 'unknown'
        
        # Return the appropriate icon
        if source in self.service_icons:
            return self.service_icons[source]
        return self.service_icons.get('unknown', QIcon())

    def show_tree_context_menu(self, position):
        """Show context menu for tree widget items"""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        # Get the item at this position
        item = self.treeWidget.itemAt(position)
        if not item:
            return
            
        # Get the item data
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return
        
        # Create the menu
        menu = QMenu(self)
        
        # Add standard actions
        play_action = menu.addAction("Reproducir")
        add_to_queue_action = menu.addAction("Añadir a cola")
        copy_url_action = menu.addAction("Copiar URL")
        
        # Add Spotify-specific actions if Spotify is authenticated
        if hasattr(self, 'spotify_authenticated') and self.spotify_authenticated:
            menu.addSeparator()
            add_to_spotify_action = menu.addAction("Añadir a playlist de Spotify")
        
        # Show the menu and handle the selected action
        action = menu.exec(self.treeWidget.mapToGlobal(position))
        
        if action == play_action:
            self.play_item(item)
        elif action == add_to_queue_action:
            self.add_item_to_queue(item)
        elif action == copy_url_action:
            self.copy_url_to_clipboard()
        elif hasattr(self, 'spotify_authenticated') and self.spotify_authenticated and action == add_to_spotify_action:
            self.add_to_spotify_playlist(item_data)


    def play_item(self, item):
        """Play a tree item directly"""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return
            
        url = None
        if isinstance(item_data, dict):
            url = item_data.get('url')
        else:
            url = str(item_data)
            
        if url:
            # Add to queue and play immediately
            title = item.text(0)
            artist = item.text(1)
            display_text = f"{artist} - {title}" if artist else title
            
            # Add to queue first
            self.add_to_queue_from_url(url, display_text, item_data)
            
            # Get the index of the newly added item
            index = len(self.current_playlist) - 1
            
            # Play it
            self.current_track_index = index
            self.play_from_index(index)

    def on_tree_selection_changed(self):
        """Handle selection changes in the tree widget"""
        try:
            # Get the current selected item
            selected_items = self.treeWidget.selectedItems()
            if not selected_items:
                return
                
            item = selected_items[0]
            
            # Get the data associated with the item
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Display information about the selected item if available
            if item_data:
                self.display_wiki_info(item_data)
        except Exception as e:
            self.log(f"Error handling tree selection change: {str(e)}")


    def on_guardar_playlist_clicked(self):
        """Handle save playlist button click"""
        # Use the correct combobox name from your UI file
        if not hasattr(self, 'guardar_playlist_comboBox'):
            self.log("ComboBox para guardar playlist no encontrado")
            return
            
        combo = self.guardar_playlist_comboBox
        selected = combo.currentText()
        print(f"selected!!! {selected}")
        if selected == "Spotify":
            self.save_to_spotify_playlist()
        elif selected == "Playlist local":
            self.save_current_playlist()  # Tu función existente
        elif selected == "Youtube":
            self.log("Guardado en Youtube no implementado aún")

    def save_to_spotify_playlist(self):
        """Save current queue to an existing Spotify playlist"""
        if not hasattr(self, 'sp') or not self.sp:
            self.log("Cliente de Spotify no inicializado")
            QMessageBox.warning(self, "Error", "No se ha podido conectar con Spotify")
            return
                
        # Check if we have items in the queue
        if not self.current_playlist or self.listWidget.count() == 0:
            self.log("No hay canciones en la cola para guardar")
            QMessageBox.warning(self, "Error", "No hay canciones en la cola para guardar")
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Guardar en Playlist de Spotify")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Add explanation text
        layout.addWidget(QLabel(f"Selecciona una playlist de Spotify para añadir {self.listWidget.count()} canciones:"))
        
        # Add playlist selector combo box similar to playlist_spotify_comboBox
        playlist_combo = QComboBox()
        
        # Add items from spotify_playlists
        if hasattr(self, 'spotify_playlists') and self.spotify_playlists:
            for name in self.spotify_playlists.keys():
                playlist_combo.addItem(QIcon(":/services/spotify"), name)
        else:
            # If playlists haven't been loaded yet, load them
            self.load_spotify_playlists()
            if hasattr(self, 'spotify_playlists') and self.spotify_playlists:
                for name in self.spotify_playlists.keys():
                    playlist_combo.addItem(QIcon(":/services/spotify"), name)
        
        # Default to currently selected playlist in playlist_spotify_comboBox if any
        if hasattr(self, 'playlist_spotify_comboBox') and self.playlist_spotify_comboBox.currentIndex() > 0:
            current_playlist = self.playlist_spotify_comboBox.currentText()
            index = playlist_combo.findText(current_playlist)
            if index >= 0:
                playlist_combo.setCurrentIndex(index)
        
        layout.addWidget(playlist_combo)
        
        # Add option to create new playlist
        create_new_checkbox = QCheckBox("Crear nueva playlist")
        layout.addWidget(create_new_checkbox)
        
        # New playlist name (initially hidden)
        new_playlist_label = QLabel("Nombre de la nueva playlist:")
        new_playlist_input = QLineEdit()
        new_playlist_label.setVisible(False)
        new_playlist_input.setVisible(False)
        layout.addWidget(new_playlist_label)
        layout.addWidget(new_playlist_input)
        
        # Connect checkbox to show/hide new playlist inputs
        create_new_checkbox.stateChanged.connect(
            lambda state: [new_playlist_label.setVisible(state == Qt.CheckState.Checked),
                        new_playlist_input.setVisible(state == Qt.CheckState.Checked),
                        playlist_combo.setEnabled(state != Qt.CheckState.Checked)]
        )
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if create_new_checkbox.isChecked():
                playlist_name = new_playlist_input.text().strip()
                if not playlist_name:
                    self.log("Nombre de playlist vacío")
                    QMessageBox.warning(self, "Error", "Por favor, introduce un nombre para la playlist")
                    return
                
                # Create new playlist and add songs
                self.create_spotify_playlist_with_tracks(playlist_name)
            else:
                # Add to existing playlist
                selected_playlist = playlist_combo.currentText()
                if not selected_playlist or selected_playlist not in self.spotify_playlists:
                    self.log("No se ha seleccionado ninguna playlist válida")
                    return
                
                playlist_id = self.spotify_playlists[selected_playlist]['id']
                self.add_tracks_to_spotify_playlist(playlist_id, selected_playlist)


    def create_spotify_playlist_with_tracks(self, playlist_name):
        """Create a new Spotify playlist and add tracks from the current queue"""
        try:
            # First create the playlist
            result = self.api_call_with_retry(
                self.sp.user_playlist_create,
                user=self.spotify_user_id,
                name=playlist_name,
                public=False,
                description="Created from Music App Queue"
            )
            
            playlist_id = result['id']
            self.log(f"Playlist '{playlist_name}' creada correctamente")
            
            # Add tracks to the playlist
            self.add_tracks_to_spotify_playlist(playlist_id, playlist_name)
            
            # Reload playlists to update UI
            self.load_spotify_playlists(force_update=True)
            
        except Exception as e:
            self.log(f"Error creando playlist: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error creando playlist: {str(e)}")

    def add_tracks_to_spotify_playlist(self, playlist_id, playlist_name):
        """Add tracks from the current queue to a Spotify playlist"""
        try:
            # Show a progress dialog
            progress_dialog = QProgressDialog("Añadiendo canciones a Spotify...", "Cancelar", 0, self.listWidget.count(), self)
            progress_dialog.setWindowTitle("Guardando Playlist")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            
            # Get Spotify URIs for all tracks in the queue
            track_uris = []
            not_found = []
            skipped = 0
            
            for i in range(self.listWidget.count()):
                # Update progress
                progress_dialog.setValue(i)
                if progress_dialog.wasCanceled():
                    self.log("Operación cancelada por el usuario")
                    return
                
                # Get item data
                item = self.listWidget.item(i)
                if not item:
                    continue
                    
                # Get track data
                track_data = {}
                if i < len(self.current_playlist):
                    track_data = self.current_playlist[i]
                else:
                    # Extract from item text
                    text = item.text()
                    title = text
                    artist = ""
                    if " - " in text:
                        parts = text.split(" - ", 1)
                        artist = parts[0]
                        title = parts[1]
                    track_data = {'title': title, 'artist': artist, 'url': item.data(Qt.ItemDataRole.UserRole)}
                
                track_uri = None
                
                # Check if this is already a Spotify track with ID
                entry_data = track_data.get('entry_data', {})
                if isinstance(entry_data, dict) and entry_data.get('source') == 'spotify' and entry_data.get('spotify_id'):
                    track_uri = f"spotify:track:{entry_data['spotify_id']}"
                # Check if URL is a Spotify URL with track ID
                elif 'url' in track_data and 'spotify.com/track/' in track_data['url']:
                    track_id = track_data['url'].split('spotify.com/track/')[1].split('?')[0]
                    track_uri = f"spotify:track:{track_id}"
                else:
                    # Try to search for the track on Spotify
                    search_query = f"{track_data.get('title', '')} artist:{track_data.get('artist', '')}" 
                    track_uri = self.search_spotify_track_uri(search_query)
                
                if track_uri:
                    track_uris.append(track_uri)
                else:
                    not_found.append(track_data.get('title', f"Track {i+1}"))
                    skipped += 1
            
            progress_dialog.setValue(self.listWidget.count())
            
            # Add tracks to the playlist (in batches of 100 if needed)
            if track_uris:
                batch_size = 100
                for i in range(0, len(track_uris), batch_size):
                    batch = track_uris[i:i+batch_size]
                    self.api_call_with_retry(self.sp.playlist_add_items, playlist_id, batch)
            
            # Show results
            if skipped > 0:
                QMessageBox.information(
                    self, 
                    "Playlist guardada", 
                    f"Playlist '{playlist_name}' actualizada con {len(track_uris)} canciones.\n"
                    f"No se encontraron {skipped} canciones en Spotify."
                )
            else:
                QMessageBox.information(
                    self, 
                    "Playlist guardada", 
                    f"Playlist '{playlist_name}' actualizada con {len(track_uris)} canciones."
                )
            
            self.log(f"Playlist '{playlist_name}' actualizada con {len(track_uris)} canciones")
            if skipped > 0:
                self.log(f"No se encontraron {skipped} canciones en Spotify: {', '.join(not_found[:5])}" + 
                    ("..." if len(not_found) > 5 else ""))
            
        except Exception as e:
            self.log(f"Error añadiendo canciones a la playlist: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            QMessageBox.warning(self, "Error", f"Error añadiendo canciones a la playlist: {str(e)}")


    def save_queue_to_spotify_playlist(self):
        """Save current queue as a Spotify playlist"""
        if not hasattr(self, 'sp') or not self.sp:
            self.log("Spotify client not initialized")
            return
            
        # Check if we have items in the queue
        if not self.current_playlist:
            self.log("No hay canciones en la cola para guardar")
            return
            
        # Show dialog to get playlist name
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Guardar Cola como Playlist de Spotify")
        
        layout = QVBoxLayout(dialog)
        
        # Add a label
        layout.addWidget(QLabel(f"Guardar {len(self.current_playlist)} canciones como nueva playlist:"))
        
        # Name input
        layout.addWidget(QLabel("Nombre de la playlist:"))
        name_input = QLineEdit()
        layout.addWidget(name_input)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            playlist_name = name_input.text().strip()
            if playlist_name:
                try:
                    # First create the playlist
                    result = self.sp.user_playlist_create(
                        user=self.spotify_user_id,
                        name=playlist_name,
                        public=False,
                        description="Created from Music App Queue"
                    )
                    
                    playlist_id = result['id']
                    
                    # Now get Spotify URIs for all tracks in the queue
                    track_uris = []
                    not_found = []
                    
                    for i, item in enumerate(self.current_playlist):
                        # Update progress
                        if i % 5 == 0:
                            self.log(f"Procesando canción {i+1}/{len(self.current_playlist)}...")
                        
                        track_uri = None
                        
                        # If this is already a Spotify track, get its ID
                        entry_data = item.get('entry_data', {})
                        if isinstance(entry_data, dict) and entry_data.get('source') == 'spotify' and entry_data.get('spotify_id'):
                            track_uri = f"spotify:track:{entry_data['spotify_id']}"
                        else:
                            # Try to search for the track on Spotify
                            track_uri = self.search_spotify_track_uri(item)
                        
                        if track_uri:
                            track_uris.append(track_uri)
                        else:
                            not_found.append(item.get('title', f"Track {i+1}"))
                    
                    # Add tracks to the playlist (in batches of 100 if needed)
                    if track_uris:
                        batch_size = 100
                        for i in range(0, len(track_uris), batch_size):
                            batch = track_uris[i:i+batch_size]
                            self.sp.playlist_add_items(playlist_id, batch)
                    
                    # Show results
                    self.log(f"Playlist '{playlist_name}' creada con {len(track_uris)} canciones")
                    
                    if not_found:
                        self.log(f"No se encontraron {len(not_found)} canciones en Spotify")
                    
                    # Reload playlists to update UI
                    self.load_spotify_playlists(force_update=True)
                    
                except Exception as e:
                    self.log(f"Error guardando playlist: {str(e)}")


    def on_playlist_rss_changed(self, index):
        """Handle selection change in the RSS playlist comboBox"""
        combo = self.playlist_rss_comboBox
        selected_text = combo.currentText()
        
        # In a real implementation, you would load RSS content here
        self.log(f"RSS Playlist selected: {selected_text}")
        
        # For now, just show a placeholder message
        self.treeWidget.clear()
        from PyQt6.QtWidgets import QTreeWidgetItem
        
        root_item = QTreeWidgetItem(self.treeWidget)
        root_item.setText(0, selected_text)
        root_item.setText(1, "RSS")
        root_item.setText(2, "Feed")
        
        # Make the root item bold
        font = root_item.font(0)
        font.setBold(True)
        root_item.setFont(0, font)
        
        # Add a placeholder item
        item = QTreeWidgetItem(root_item)
        item.setText(0, "Implementación pendiente")
        item.setText(1, "")
        item.setText(2, "Info")
        
        root_item.setExpanded(True)

    def on_playlist_local_changed(self, index):
        """Handle selection change in the local playlist comboBox."""
        if index <= 0:
            return
            
        combo = self.playlist_local_comboBox
        selected_text = combo.currentText()
        
        self.log(f"Local Playlist selected: {selected_text}")
        
        # Load the selected playlist
        self.load_local_playlist(selected_text)



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
