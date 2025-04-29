import sqlite3
import os
from modules.submodules.url_playlist.ui_helpers import display_search_results, display_external_results
from PyQt6.QtCore import QThreadPool


def search_database_links(self, db_path, query, search_type="all"):
    """
    Search for existing links and structure in the database before making API calls.
    Returns a hierarchical structure of artists/albums/tracks with their links.
    """
    try:
        from db.tools.consultar_items_db import MusicDatabaseQuery
        self.db_path = db_path
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


def _process_database_results(self, db_links):
    """Process database links into results with proper hierarchy by service (LOCAL, SPOTIFY, etc.)."""
    results = []
    
    # Track unique items to avoid duplicates
    processed_artists = set()
    processed_albums = set()
    processed_tracks = set()
    
    # Log para depuración
    self.log(f"Procesando resultados de base de datos con {len(db_links.get('artists', {}))} artistas, {len(db_links.get('albums', {}))} álbumes, {len(db_links.get('tracks', {}))} pistas")
    
    # Importar la clase MusicDatabaseQuery para obtener orígenes
    from db.tools.consultar_items_db import MusicDatabaseQuery
    db = MusicDatabaseQuery(self.db_path)
    
    # Primero, procesar artistas con sus álbumes y pistas
    for artist_name, artist_data in db_links.get('artists', {}).items():
        # Try to fetch paths for this artist
        paths_data = fetch_artist_song_paths(self, artist_name)
        
        # Determinar el origen del artista
        origen = artist_data.get('origen')
        if not origen:
            # Intentar obtener origen directamente de la base de datos
            origen = db.get_item_origen('artist', name=artist_name)
            
        self.log(f"Artista: {artist_name}, origen: {origen}")
        
        # Definir source basado en el origen o disponibilidad de enlaces
        source = "local" if origen == "local" else "unknown"
        
        # Si no es local, determinar source basado en enlaces disponibles
        if source == "unknown" and 'links' in artist_data:
            for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                if service in artist_data['links'] and artist_data['links'][service]:
                    source = service
                    break
        
        # Crear resultado para este artista
        artist_result = {
            "source": source,
            "title": artist_name,
            "artist": artist_name,
            "type": "artist",
            "origen": origen,
            "from_database": True
        }
        
        # Add links if available
        if 'links' in artist_data:
            artist_result['links'] = artist_data['links']
        
        # Process albums for this artist
        if 'albums' in artist_data and artist_data['albums']:
            artist_albums = []
            
            for album in artist_data['albums']:
                album_title = album.get('title', album.get('name', ''))
                album_key = f"{artist_name}_{album_title}"
                
                if album_key in processed_albums:
                    continue
                processed_albums.add(album_key)
                
                # Determine album origen
                album_origen = album.get('origen')
                if not album_origen:
                    # Intentar obtener origen directamente de la base de datos
                    album_origen = db.get_item_origen('album', name=album_title, artist=artist_name)
                    
                self.log(f"Álbum: {album_title}, origen: {album_origen}")
                
                # Determine album source based on origen
                album_source = "local" if album_origen == "local" else source
                
                # Si el álbum no es local, determinar source por sus enlaces
                if album_source != "local" and 'links' in album:
                    for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                        if service in album['links'] and album['links'][service]:
                            album_source = service
                            break
                
                album_result = {
                    "source": album_source,
                    "title": album_title,
                    "artist": artist_name,
                    "type": "album",
                    "year": album.get('year'),
                    "origen": album_origen,
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
                        track_key = f"{artist_name}_{album_title}_{track_title}"
                        
                        if track_key in processed_tracks:
                            continue
                        processed_tracks.add(track_key)
                        
                        # Determine track origen
                        track_origen = track.get('origen')
                        if not track_origen:
                            # Intentar obtener origen directamente de la base de datos
                            track_origen = db.get_item_origen('song', name=track_title, artist=artist_name, album=album_title)
                            
                        self.log(f"Pista: {track_title}, origen: {track_origen}")
                        
                        # Determine track source basado en origen
                        track_source = "local" if track_origen == "local" else album_source
                        
                        # Si la pista no es local, determinar source por sus enlaces
                        if track_source != "local" and 'links' in track:
                            for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                                if service in track['links'] and track['links'][service]:
                                    track_source = service
                                    break
                        
                        track_result = {
                            "source": track_source,
                            "title": track_title,
                            "artist": artist_name,
                            "album": album_title,
                            "type": "track",
                            "track_number": track.get('track_number'),
                            "duration": track.get('duration'),
                            "origen": track_origen,
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
                                            # Si tiene file_path, marcar como local para asegurar
                                            if 'ruta' in song and song['ruta']:
                                                track_result['origen'] = 'local'
                                            break
                        
                        album_tracks.append(track_result)
                    
                    # Add tracks to album result
                    album_result['tracks'] = album_tracks
                
                artist_albums.append(album_result)
            
            # Add albums to artist result
            artist_result['albums'] = artist_albums
        
        # Only add artist to results if not already processed
        if artist_name not in processed_artists:
            processed_artists.add(artist_name)
            results.append(artist_result)
    
    # Cerrar la conexión a la base de datos
    db.close()
    
    # Información de depuración
    self.log(f"Resultados procesados: {len(results)} artistas, {len(processed_albums)} álbumes, {len(processed_tracks)} pistas")
    
    return results

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
            
        from db.tools.consultar_items_db import MusicDatabaseQuery
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

def perform_search_with_service_filter(self, query, only_local=False):
    """
    Realiza una búsqueda en la base de datos y organiza los resultados por servicio.
    Si only_local es True, solo se muestran resultados con origen 'local'.
    """
    # Limpiar resultados anteriores
    if hasattr(self, 'treeWidget'):
        self.treeWidget.clear()
        
    # Mostrar indicador de carga
    self.log(f"Buscando '{query}' con filtro only_local={only_local}")
    if hasattr(self, 'textEdit'):
        self.textEdit.clear()
        self.textEdit.append(f"Buscando '{query}'...")
    
    from PyQt6.QtWidgets import QApplication
    QApplication.processEvents()  # Actualizar la UI
    
    # Realizar búsqueda en la base de datos
    db_links = search_database_links(self, self.db_path, query, "all")
    
    # Depuración para ver qué se encontró
    if db_links:
        self.log(f"Resultados de la base de datos: {len(db_links.get('artists', {}))} artistas, {len(db_links.get('albums', {}))} álbumes, {len(db_links.get('tracks', {}))} pistas")
        
        # Procesar resultados 
        db_results = _process_database_results(self, db_links)
        
        self.log(f"Obtenidos {len(db_results)} elementos después del procesamiento")
        
        # Mostrar resultados
        if db_results:
            # Si only_local es True, filtrar resultados
            if only_local:
                self.log(f"Filtrando {len(db_results)} resultados para mostrar solo origen 'local'")
                
                # Pre-filtrar manualmente resultados locales
                filtered_results = []
                
                for result in db_results:
                    origen = result.get('origen')
                    file_path = result.get('file_path')
                    title = result.get('title', '')
                    
                    # Solo incluir resultados con origen 'local' o con file_path
                    if origen == 'local' or file_path:
                        filtered_results.append(result)
                        self.log(f"Elemento local: {title}, origen: {origen}, file_path: {file_path}")
                
                # Aplicar filtrado más detallado manteniendo la organización por servicio
                if filtered_results:
                    # Aplicar el filtro con agrupación por servicio
                    db_results = filter_results_by_origen(filtered_results, only_local=True, service_grouping=True)
                else:
                    db_results = []
                    
                self.log(f"Después del filtrado quedan {len(db_results)} resultados")
            
            # Mostrar los resultados en el árbol
            display_search_results(self, db_results, True)  # Siempre agrupar por servicio
            
            # Contar resultados por servicio
            services_count = {}
            for result in db_results:
                source = result.get('source', 'unknown')
                if source not in services_count:
                    services_count[source] = 0
                services_count[source] += 1
            
            # Mostrar informe de resultados
            result_info = "Resultados encontrados: "
            for service, count in services_count.items():
                result_info += f"{service.capitalize()}: {count}, "
            
            self.log(result_info.rstrip(", "))
        else:
            self.log("No se encontraron resultados en la base de datos")
            if hasattr(self, 'textEdit'):
                self.textEdit.append("No se encontraron resultados en la base de datos")
    else:
        self.log("No se encontraron resultados en la base de datos")
        if hasattr(self, 'textEdit'):
            self.textEdit.append("No se encontraron resultados en la base de datos")
    
    # Buscar en servicios externos si no estamos limitados a local o si buscamos enlaces locales con servicios externos
    if not only_local or (only_local and any(self.included_services.get(svc, False) for svc in ['spotify', 'youtube', 'bandcamp', 'soundcloud'])):
        # Determinar qué servicios buscar
        active_services = []
        selected_service = self.servicios.currentText() if hasattr(self, 'servicios') else "Todos"
        
        if selected_service == "Todos":
            # Check each service in the included_services dictionary
            for service_id, included in self.included_services.items():
                # Convert included to boolean if it's a string
                if isinstance(included, str):
                    included = included.lower() == 'true'
                
                if included:
                    active_services.append(service_id)
        else:
            # Convert from display name to service id (lowercase)
            service_id = selected_service.lower()
            active_services = [service_id]
        
        if active_services:
            # Crear y configurar el worker para la búsqueda externa
            from modules.submodules.url_playlist.search_workers import SearchWorker
            
            worker = SearchWorker(active_services, query, max_results=self.pagination_value)
            worker.parent = self
            worker.search_type = "all"
            worker.db_links = db_links
            worker.db_path = self.db_path
            worker.spotify_client_id = self.spotify_client_id
            worker.spotify_client_secret = self.spotify_client_secret
            worker.lastfm_manager_key = self.lastfm_manager_key
            worker.lastfm_username = self.lastfm_username
            worker.only_local = only_local  # Pasar el flag de only_local al worker
            
            # Crear una estructura para rastrear elementos añadidos
            self.added_items = {
                'artists': set(),
                'albums': set(),
                'tracks': set()
            }
            worker.added_items = self.added_items
            
            # Configurar el flag group_by_service
            worker.group_by_service = True
            
            # Conectar señales
            worker.signals.results.connect(lambda results: display_external_results_with_filter(self, results, True, only_local))
            worker.signals.error.connect(lambda err: self.log(f"Error en búsqueda: {err}"))
            worker.signals.finished.connect(SearchWorker.search_finished)
            
            # Iniciar el worker
            QThreadPool.globalInstance().start(worker)
        else:
            self.log("No hay servicios externos seleccionados para la búsqueda")
            if hasattr(self, 'textEdit'):
                self.textEdit.append("No hay servicios externos seleccionados para la búsqueda")
    
    # Actualizar la UI
    QApplication.processEvents()

def display_external_results_with_filter(self, results, group_by_service=False, only_local=False):
    """Display external search results with local origin filtering if needed."""
    if not results:
        self.log("No se encontraron resultados externos.")
        return
    
    # Filter results if only_local is enabled
    if only_local:
        # Para resultados externos, solo mostrar aquellos con origen 'local' o file_path
        filtered_results = []
        for r in results:
            if r.get('origen') == 'local' or r.get('file_path'):
                filtered_results.append(r)
                self.log(f"Resultado externo con origen local: {r.get('title', '')}")
        
        # Use the original function with filtered results
        display_external_results(self, filtered_results, group_by_service)
        self.log(f"Se añadieron {len(filtered_results)} resultados locales de servicios externos")
    else:
        # Use the original function as-is for non-filtered results
        display_external_results(self, results, group_by_service)
        self.log(f"Se añadieron {len(results)} resultados de servicios externos")


        
def filter_results_by_origen(results, only_local=False, service_grouping=True):
    """
    Filtra resultados según su origen y opcionalmente los agrupa por servicio.
    Si only_local es True, solo se mantienen los resultados con origen 'local'.
    Si service_grouping es True, reorganiza los resultados para agruparlos por servicio.
    """
    if not only_local:
        return results
    
    # Log para depuración
    print(f"[filter_results_by_origen] Filtrando {len(results)} resultados, only_local={only_local}")
    
    filtered_results = []
    services_by_local = {}  # Almacenará enlaces de servicios para elementos locales
    
    # Primera pasada: identificar los elementos locales y almacenar sus datos
    for result in results:
        item_type = result.get('type', '').lower()
        origen = result.get('origen')
        file_path = result.get('file_path')
        
        # Verificación estricta de origen local
        is_local = origen == 'local' or file_path
        
        # Si es artista, revisamos sus álbumes y canciones individualmente
        if item_type == 'artist':
            # Crear una copia del resultado para modificarla
            filtered_artist = result.copy()
            
            # Si el artista en sí es local o tiene filepath
            if is_local:
                # Filtrar álbumes locales de este artista
                if 'albums' in result:
                    filtered_albums = []
                    
                    for album in result['albums']:
                        album_origen = album.get('origen')
                        album_file_path = album.get('file_path')
                        
                        # Si el álbum es local
                        if album_origen == 'local' or album_file_path:
                            # Crear copia del álbum para modificarla
                            filtered_album = album.copy()
                            
                            # Filtrar canciones locales de este álbum
                            if 'tracks' in album:
                                filtered_tracks = []
                                
                                for track in album['tracks']:
                                    track_origen = track.get('origen')
                                    track_file_path = track.get('file_path')
                                    
                                    # Si la canción es local
                                    if track_origen == 'local' or track_file_path:
                                        filtered_tracks.append(track)
                                        
                                        # Almacenar enlaces a servicios para esta canción local
                                        if service_grouping:
                                            # Verificar y almacenar enlaces específicos de servicios
                                            for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                                                service_url = None
                                                
                                                # Buscar URLs en diferentes lugares
                                                if 'links' in track and service in track['links']:
                                                    service_url = track['links'][service]
                                                elif f'{service}_url' in track:
                                                    service_url = track[f'{service}_url']
                                                
                                                if service_url:
                                                    track_key = f"{track.get('artist', '')}-{track.get('album', '')}-{track.get('title', '')}"
                                                    if service not in services_by_local:
                                                        services_by_local[service] = {}
                                                    
                                                    if track_key not in services_by_local[service]:
                                                        # Crear una copia para este servicio
                                                        service_track = track.copy()
                                                        service_track['source'] = service
                                                        service_track['url'] = service_url
                                                        # Preservar el origen local
                                                        service_track['origen'] = 'local'
                                                        services_by_local[service][track_key] = service_track
                                
                                # Actualizar tracks solo con los que son locales
                                if filtered_tracks:
                                    filtered_album['tracks'] = filtered_tracks
                                else:
                                    # Si no hay canciones locales, no incluir este álbum
                                    continue
                            
                            # Almacenar enlaces a servicios para este álbum local
                            if service_grouping:
                                for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                                    service_url = None
                                    
                                    if 'links' in album and service in album['links']:
                                        service_url = album['links'][service]
                                    elif f'{service}_url' in album:
                                        service_url = album[f'{service}_url']
                                    
                                    if service_url:
                                        album_key = f"{album.get('artist', '')}-{album.get('title', '')}"
                                        if service not in services_by_local:
                                            services_by_local[service] = {}
                                        
                                        if album_key not in services_by_local[service]:
                                            # Crear una copia para este servicio
                                            service_album = album.copy()
                                            service_album['source'] = service
                                            service_album['url'] = service_url
                                            # Preservar el origen local
                                            service_album['origen'] = 'local'
                                            services_by_local[service][album_key] = service_album
                            
                            filtered_albums.append(filtered_album)
                    
                    # Actualizar lista de álbumes solo con los que son locales
                    if filtered_albums:
                        filtered_artist['albums'] = filtered_albums
                    else:
                        # Si no hay álbumes locales pero el artista es local, mantener el artista
                        filtered_artist['albums'] = []
                
                # Almacenar enlaces a servicios para este artista local
                if service_grouping:
                    for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                        service_url = None
                        
                        if 'links' in result and service in result['links']:
                            service_url = result['links'][service]
                        elif f'{service}_url' in result:
                            service_url = result[f'{service}_url']
                        
                        if service_url:
                            artist_key = result.get('title', '')
                            if service not in services_by_local:
                                services_by_local[service] = {}
                            
                            if artist_key not in services_by_local[service]:
                                # Crear una copia para este servicio
                                service_artist = result.copy()
                                service_artist['source'] = service
                                service_artist['url'] = service_url
                                # Preservar el origen local
                                service_artist['origen'] = 'local'
                                services_by_local[service][artist_key] = service_artist
                
                # Añadir artista filtrado a resultados si tiene algún álbum o es local por sí mismo
                if 'albums' in filtered_artist and filtered_artist['albums'] or is_local:
                    filtered_results.append(filtered_artist)
        
        # Si es un álbum directamente, verificar si es local
        elif item_type == 'album':
            if is_local:
                # Crear una copia del álbum para modificarla
                filtered_album = result.copy()
                
                # Filtrar tracks locales si existen
                if 'tracks' in result:
                    filtered_tracks = []
                    
                    for track in result['tracks']:
                        track_origen = track.get('origen')
                        track_file_path = track.get('file_path')
                        
                        if track_origen == 'local' or track_file_path:
                            filtered_tracks.append(track)
                            
                            # Almacenar enlaces a servicios para esta canción local
                            if service_grouping:
                                for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                                    service_url = None
                                    
                                    if 'links' in track and service in track['links']:
                                        service_url = track['links'][service]
                                    elif f'{service}_url' in track:
                                        service_url = track[f'{service}_url']
                                    
                                    if service_url:
                                        track_key = f"{track.get('artist', '')}-{track.get('album', '')}-{track.get('title', '')}"
                                        if service not in services_by_local:
                                            services_by_local[service] = {}
                                        
                                        if track_key not in services_by_local[service]:
                                            service_track = track.copy()
                                            service_track['source'] = service
                                            service_track['url'] = service_url
                                            # Preservar el origen local
                                            service_track['origen'] = 'local'
                                            services_by_local[service][track_key] = service_track
                    
                    # Actualizar tracks solo con los locales
                    if filtered_tracks:
                        filtered_album['tracks'] = filtered_tracks
                    else:
                        filtered_album['tracks'] = []
                
                # Almacenar enlaces a servicios para este álbum local
                if service_grouping:
                    for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                        service_url = None
                        
                        if 'links' in result and service in result['links']:
                            service_url = result['links'][service]
                        elif f'{service}_url' in result:
                            service_url = result[f'{service}_url']
                        
                        if service_url:
                            album_key = f"{result.get('artist', '')}-{result.get('title', '')}"
                            if service not in services_by_local:
                                services_by_local[service] = {}
                            
                            if album_key not in services_by_local[service]:
                                service_album = result.copy()
                                service_album['source'] = service
                                service_album['url'] = service_url
                                # Preservar el origen local
                                service_album['origen'] = 'local'
                                services_by_local[service][album_key] = service_album
                
                filtered_results.append(filtered_album)
        
        # Si es una canción directamente, verificar si es local
        elif item_type in ['track', 'song']:
            if is_local:
                # Añadir la canción original
                filtered_results.append(result)
                
                # Almacenar enlaces a servicios para esta canción local
                if service_grouping:
                    for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                        service_url = None
                        
                        if 'links' in result and service in result['links']:
                            service_url = result['links'][service]
                        elif f'{service}_url' in result:
                            service_url = result[f'{service}_url']
                        
                        if service_url:
                            track_key = f"{result.get('artist', '')}-{result.get('album', '')}-{result.get('title', '')}"
                            if service not in services_by_local:
                                services_by_local[service] = {}
                            
                            if track_key not in services_by_local[service]:
                                service_track = result.copy()
                                service_track['source'] = service
                                service_track['url'] = service_url
                                # Preservar el origen local
                                service_track['origen'] = 'local'
                                services_by_local[service][track_key] = service_track
    
    # Añadir elementos de servicios a los resultados filtrados
    if service_grouping:
        for service, items_dict in services_by_local.items():
            for item_key, service_item in items_dict.items():
                # Asegurarnos de establecer correctamente el source y mantener origen local
                service_item['source'] = service
                service_item['origen'] = 'local'
                filtered_results.append(service_item)
    
    print(f"[filter_results_by_origen] Resultados filtrados finales: {len(filtered_results)}")
    return filtered_results