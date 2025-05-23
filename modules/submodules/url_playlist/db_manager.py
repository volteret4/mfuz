import sqlite3
import os
from modules.submodules.url_playlist.ui_helpers import display_search_results, display_external_results
from PyQt6.QtCore import QThreadPool


def search_database_links(self, db_path, query, search_type="all"):
    """
    Versión optimizada para búsqueda en base de datos con caché de resultados.
    """
    # Implementar caché para consultas recientes
    if not hasattr(self, '_db_query_cache'):
        self._db_query_cache = {}
    
    # Generar clave para caché
    cache_key = f"{query}|{search_type}"
    
    # Verificar si ya tenemos esta consulta en caché
    if cache_key in self._db_query_cache:
        self.log(f"Usando resultados en caché para '{query}'")
        return self._db_query_cache[cache_key]
    
    try:
        # Continuar con la implementación original
        from db.tools.consultar_items_db import MusicDatabaseQuery
        self.db_path = db_path
        if not self.db_path or not os.path.exists(self.db_path):
            self.log(f"Database not found at: {self.db_path}")
            return {}
        
        # Usar conexión con timeout para evitar bloqueos
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
        # Guardar resultados en caché antes de devolver
        self._db_query_cache[cache_key] = results
        
        # Limitar tamaño de caché
        if len(self._db_query_cache) > 50:  # Mantener solo las últimas 50 consultas
            # Eliminar la entrada más antigua
            oldest_key = next(iter(self._db_query_cache))
            del self._db_query_cache[oldest_key]

        return results
        
    except Exception as e:
        self.log(f"Error searching database links: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return {}

def _process_database_results(self, db_links):
    """
    Versión mejorada para procesar los resultados de la base de datos con mejor
    organización de archivos locales.
    """
    # Crear lista para almacenar resultados finales
    results = []
    
    # Registros para evitar duplicados
    processed = set()
    
    try:
        # Log para depuración
        artist_count = len(db_links.get('artists', {}))
        album_count = len(db_links.get('albums', {}))
        track_count = len(db_links.get('tracks', {}))
        self.log(f"Procesando resultados de base de datos con {artist_count} artistas, {album_count} álbumes, {track_count} pistas")
        
        # PASO 1: Procesar artistas
        for artist_name, artist_data in db_links.get('artists', {}).items():
            # Crear un ID único para este artista
            artist_id = f"artist_{artist_name}"
            
            # Evitar duplicados
            if artist_id in processed:
                continue
                
            processed.add(artist_id)
            
            # Crear resultado básico para este artista
            artist_result = {
                "source": "unknown",  # Por defecto, se actualizará más adelante
                "title": artist_name,
                "artist": artist_name,
                "type": "artist",
                "from_database": True,
                "albums": []  # Lista vacía para álbumes
            }
            
            # Determinar fuente basada en los datos disponibles
            if artist_data.get('origen') == 'local':
                artist_result['source'] = 'local'
                artist_result['origen'] = 'local'
            elif 'links' in artist_data:
                for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                    if service in artist_data['links'] and artist_data['links'][service]:
                        artist_result['source'] = service
                        # Añadir URL específica de servicio
                        artist_result[f'{service}_url'] = artist_data['links'][service]
                        break
            
            # Añadir enlaces si están disponibles
            if 'links' in artist_data:
                artist_result['links'] = artist_data['links'].copy() if isinstance(artist_data['links'], dict) else {}
            
            # Añadir a resultados
            results.append(artist_result)
            
        # PASO 2: Procesar álbumes
        for album_key, album_data in db_links.get('albums', {}).items():
            # Obtener información básica
            album_title = album_data.get('title', '')
            album_artist = album_data.get('artist', '')
            
            if not album_title:
                continue
                
            # Crear un ID único para este álbum
            album_id = f"album_{album_artist}_{album_title}"
            
            # Evitar duplicados
            if album_id in processed:
                continue
                
            processed.add(album_id)
            
            # Crear resultado básico para este álbum
            album_result = {
                "source": "unknown",  # Por defecto, se actualizará más adelante
                "title": album_title,
                "artist": album_artist,
                "type": "album",
                "from_database": True,
                "tracks": []  # Lista vacía para pistas
            }
            
            # Añadir año si está disponible
            if 'year' in album_data:
                album_result['year'] = album_data['year']
            
            # Determinar fuente basada en los datos disponibles
            if album_data.get('origen') == 'local':
                album_result['source'] = 'local'
                album_result['origen'] = 'local'
            elif 'links' in album_data:
                for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                    if service in album_data['links'] and album_data['links'][service]:
                        album_result['source'] = service
                        # Añadir URL específica de servicio
                        album_result[f'{service}_url'] = album_data['links'][service]
                        break
            
            # Añadir enlaces si están disponibles
            if 'links' in album_data:
                album_result['links'] = album_data['links'].copy() if isinstance(album_data['links'], dict) else {}
            
            # Añadir a resultados
            results.append(album_result)
            
        # PASO 3: Procesar pistas con especial atención a file_path
        for track_key, track_data in db_links.get('tracks', {}).items():
            # Obtener información básica
            track_title = track_data.get('title', '')
            track_artist = track_data.get('artist', '')
            track_album = track_data.get('album', '')
            
            if not track_title:
                continue
                
            # Crear un ID único para esta pista
            track_id = f"track_{track_artist}_{track_album}_{track_title}"
            
            # Evitar duplicados
            if track_id in processed:
                continue
                
            processed.add(track_id)
            
            # Crear resultado básico para esta pista
            track_result = {
                "source": "unknown",  # Por defecto, se actualizará más adelante
                "title": track_title,
                "artist": track_artist,
                "album": track_album,
                "type": "track",
                "from_database": True
            }
            
            # Añadir número de pista si está disponible
            if 'track_number' in track_data:
                track_result['track_number'] = track_data['track_number']
                
            # Añadir duración si está disponible
            if 'duration' in track_data:
                track_result['duration'] = track_data['duration']
            
            # Añadir file_path si está disponible (IMPORTANTE para archivos locales)
            if 'file_path' in track_data and track_data['file_path']:
                track_result['file_path'] = track_data['file_path']
                # Si tiene file_path, marcar como local
                track_result['source'] = 'local'
                track_result['origen'] = 'local'
                # También establecer como URL primaria
                track_result['url'] = track_data['file_path']
            else:
                # Determinar fuente basada en los datos disponibles
                if track_data.get('origen') == 'local':
                    track_result['source'] = 'local'
                    track_result['origen'] = 'local'
                elif 'links' in track_data:
                    for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                        if service in track_data['links'] and track_data['links'][service]:
                            track_result['source'] = service
                            # Añadir URL específica de servicio
                            track_result[f'{service}_url'] = track_data['links'][service]
                            
                            # Si es la primera URL encontrada, usarla como URL primaria
                            if not track_result.get('url'):
                                track_result['url'] = track_data['links'][service]
                            break
            
            # Añadir enlaces si están disponibles
            if 'links' in track_data:
                track_result['links'] = track_data['links'].copy() if isinstance(track_data['links'], dict) else {}
            
            # Añadir a resultados
            results.append(track_result)
        
        # PASO 4: Asegurar que los resultados locales se agrupen correctamente
        # Este paso es crucial para la organización en "Archivos locales" > Artista > Álbum > Canción
        local_results = []
        other_results = []
        
        for result in results:
            # Separar los resultados locales del resto
            if result.get('file_path') or result.get('source') == 'local':
                # Asegurar que tengan 'origen' establecido a 'local'
                result['origen'] = 'local'
                # Si tiene file_path, asegurar que 'source' sea 'local'
                if result.get('file_path'):
                    result['source'] = 'local'
                local_results.append(result)
            else:
                other_results.append(result)
        
        # Combinar los resultados, poniendo los locales primero
        final_results = local_results + other_results
        
        return final_results
        
    except Exception as e:
        self.log(f"Error en _process_database_results: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return []

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
                
                # Filtrar para mostrar solo elementos con origen 'local' o file_path
                local_results = []
                for result in db_results:
                    if (result.get('origen') == 'local' or 
                        result.get('file_path') or 
                        'local' in str(result.get('source', '')).lower()):
                        local_results.append(result)
                
                if local_results:
                    self.log(f"Encontrados {len(local_results)} resultados locales")
                    # Reorganizar por servicio con estructura correcta
                    db_results = filter_results_by_origen(local_results, True, True)
                else:
                    db_results = []
                    self.log("No se encontraron resultados locales")
            
            # Mostrar los resultados en el árbol
            if db_results:
                from modules.submodules.url_playlist.ui_helpers import display_search_results
                display_search_results(self, db_results, True)  # True para limpiar resultados existentes
            else:
                self.log("No hay resultados que mostrar después del filtrado")
                if hasattr(self, 'textEdit'):
                    self.textEdit.append("No se encontraron resultados locales")
        else:
            self.log("No se encontraron resultados procesables en la base de datos")
            if hasattr(self, 'textEdit'):
                self.textEdit.append("No se encontraron resultados en la base de datos")
    else:
        self.log("No se encontraron resultados en la base de datos")
        if hasattr(self, 'textEdit'):
            self.textEdit.append("No se encontraron resultados en la base de datos")
    
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
    Filtra resultados según su origen y los agrupa por servicio.
    Si only_local es True, solo se mantienen los resultados con origen 'local'.
    Asegura una estructura de árbol jerárquica con una única sección "Archivos locales".
    """
    if not only_local:
        return results
    
    # Solo para depuración
    print(f"[filter_results_by_origen] Filtrando {len(results)} resultados, only_local={only_local}")
    
    # Resultado final
    filtered_results = []
    
    # Paso 1: Filtrar solo elementos con origen 'local'
    local_results = []
    for result in results:
        origen = result.get('origen', '')
        if origen == 'local':
            # Mantener solo los elementos con origen 'local'
            # Crear una copia profunda para modificar
            local_result = result.copy()
            
            # Asegurarse de que todos tienen source='local' para agruparlos correctamente
            local_result['source'] = 'local'
            
            # Asegurar que la URL es correcta - preferir file_path si existe
            if local_result.get('file_path'):
                local_result['url'] = local_result['file_path']
            
            # Si todavía no tiene URL pero tiene enlaces a servicios, usar uno de ellos
            if not local_result.get('url'):
                for service in ['spotify', 'youtube', 'bandcamp', 'soundcloud']:
                    service_key = f"{service}_url"
                    if service_key in local_result and local_result[service_key]:
                        local_result['url'] = local_result[service_key]
                        break
            
            # Añadir a local_results solo si tiene título (para evitar elementos inválidos)
            if local_result.get('title'):
                local_results.append(local_result)
    
    # Añadir todos los resultados locales filtrados
    for result in local_results:
        filtered_results.append(result)
    
    print(f"[filter_results_by_origen] Resultados locales filtrados: {len(filtered_results)}")
    return filtered_results