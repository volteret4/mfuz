from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt, QTimer
import sqlite3


class SearchHandler:
    """Handles search operations for the music browser."""
    
    def __init__(self, parent):
        self.parent = parent
        # Añadir un temporizador para retrasar la búsqueda
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._execute_search)
        self.search_delay = 500  # milisegundos de espera antes de ejecutar la búsqueda
        
    def perform_search(self):
        """Inicia el temporizador para realizar la búsqueda después de una pausa en la escritura."""
        query = self.parent.search_box.text().strip()
        
        # Si está vacío, limpiar resultados y salir
        if not query:
            self.parent.results_tree_widget.clear()
            return
        
        # Verificar si tenemos filtros especiales
        has_filters = self._has_special_filters(query)
        
        # Si tenemos filtros, verificamos si hay suficiente texto después del último filtro
        if has_filters:
            # Encontrar el último filtro en la consulta
            filters = ["a:", "d:", "g:", "y:", "s:", "rs:", "rm:", "ra:", "t:"]  # Añadir t: para título
            last_filter_pos = -1
            last_filter = None
            
            for f in filters:
                pos = query.rfind(f)
                if pos > last_filter_pos:
                    last_filter_pos = pos
                    last_filter = f
            
            # Si encontramos un filtro, verificar si hay suficiente texto después de él
            if last_filter_pos >= 0:
                text_after_filter = query[last_filter_pos + len(last_filter):].strip()
                # Si hay menos de 3 caracteres después del filtro, no buscar todavía
                # A menos que sea un filtro de año o tiempo (y:, rs:, rm:, ra:)
                if len(text_after_filter) < 3 and last_filter not in ["y:", "rs:", "rm:", "ra:"]:
                    return
        else:
            # Si no hay filtros, verificar longitud mínima
            if len(query) < 3:
                return

        # Para filtros numéricos, ejecutar la búsqueda inmediatamente sin esperar el temporizador
        if has_filters and last_filter in ["y:", "rs:", "rm:", "ra:"]:
            self.search_timer.stop()
            self._execute_search()
        
        # Reiniciar el temporizador cada vez que el usuario escribe
        self.search_timer.stop()
        self.search_timer.start(self.search_delay)

    def _execute_search(self):
        """Ejecuta la búsqueda real después de que el temporizador expire."""
        query = self.parent.search_box.text().strip()
        if not query:
            # Si el campo de búsqueda está vacío, limpiamos los resultados
            self.parent.results_tree_widget.clear()
            return
        
        # Clear current results
        self.parent.results_tree_widget.clear()
        
        # Check if "only_local_files" is checked or set via configuration
        only_local = False
        
        # Primero, comprobar si tenemos un estado establecido programáticamente
        if hasattr(self, 'only_local_state'):
            only_local = self.only_local_state
        # Luego, verificar el widget si existe (esto permitirá que el usuario cambie el estado)
        elif hasattr(self.parent, 'only_local_files') and self.parent.only_local_files is not None:
            only_local = self.parent.only_local_files.isChecked()
        
        print(f"Realizando búsqueda con filtro 'only_local': {only_local}")
        
        # Procesar filtros especiales
        if self._has_special_filters(query):
            self._perform_filtered_search(query, only_local)
        else:
            # Búsqueda normal
            self._perform_simple_search(query, only_local)

    def _perform_simple_search(self, query, only_local=False):
        """Perform a simple search across all entity types with proper local filtering."""
        # Clear the tree first
        self.parent.results_tree_widget.clear()
        
        print(f"Realizando búsqueda simple con query: '{query}', only_local: {only_local}")
        
        # Search artists
        artists = self.parent.db_manager.search_artists(query, only_local)
        print(f"Encontrados {len(artists)} artistas que coinciden con '{query}'")
        
        # For each artist, add them to the tree and load their local content
        for artist in artists:
            print(f"Añadiendo artista: {artist.get('name')}, ID: {artist.get('id')}")
            artist_item = self._add_filtered_artist(artist, only_local)
        
        # Search albums that match the query directly
        albums = self.parent.db_manager.search_albums(query, only_local)
        print(f"Encontrados {len(albums)} álbumes que coinciden con '{query}'")
        
        for album in albums:
            print(f"Procesando álbum: {album.get('name')}, ID: {album.get('id')}")
            # Get the artist
            artist_id = album.get('artist_id')
            print(f"  Artista del álbum - ID: {artist_id}")
            
            if artist_id:
                # Check if this artist is already in the tree
                artist_item = self._find_artist_item(artist_id)
                
                # If not, add the artist first
                if not artist_item:
                    print(f"  Artista no encontrado en el árbol, buscando detalles para ID: {artist_id}")
                    artist = self.parent.db_manager.get_artist_details(artist_id)
                    if artist:
                        print(f"  Añadiendo artista: {artist.get('name')}")
                        artist_item = self._add_filtered_artist(artist, only_local, load_content=False)
                    else:
                        print(f"  No se encontraron detalles para el artista con ID: {artist_id}")
                else:
                    print(f"  Artista ya existe en el árbol")
                
                # Add the album if we have a valid artist item
                if artist_item:
                    print(f"  Añadiendo álbum {album.get('name')} al artista")
                    album_item = self._add_filtered_album(album, artist_item, only_local)
                    
                    if album_item:
                        print(f"  Álbum añadido correctamente, cargando canciones...")
                        songs = self.parent.db_manager.get_album_songs(album['id'], only_local)
                        print(f"  Encontradas {len(songs)} canciones para el álbum {album.get('name')}")
                        
                        for song in songs:
                            print(f"    Añadiendo canción: {song.get('title')}")
                            song_item = self._add_filtered_song(song, album_item, only_local)
                            if not song_item:
                                print(f"    ADVERTENCIA: No se pudo añadir la canción {song.get('title')}")
                    else:
                        print(f"  ERROR: No se pudo añadir el álbum {album.get('name')} al árbol")
            else:
                print(f"  ERROR: El álbum {album.get('name')} no tiene un artist_id válido")
        
        # Search songs that match the query directly
        songs = self.parent.db_manager.search_songs(query, only_local)
        print(f"Encontradas {len(songs)} canciones que coinciden con '{query}'")
        
        for song in songs:
            # Find or add artist and album
            artist_id = song.get('artist_id')
            album_id = song.get('album_id')
            
            print(f"Procesando canción: {song.get('title')}, artist_id: {artist_id}, album_id: {album_id}")
            
            if artist_id:
                # Find or add artist
                artist_item = self._find_artist_item(artist_id)
                if not artist_item:
                    print(f"  Artista no encontrado en el árbol, buscando detalles para ID: {artist_id}")
                    artist = self.parent.db_manager.get_artist_details(artist_id)
                    if artist:
                        print(f"  Añadiendo artista: {artist.get('name')}")
                        artist_item = self._add_filtered_artist(artist, only_local, load_content=False)
                    else:
                        print(f"  No se encontraron detalles para el artista con ID: {artist_id}")
                
                if artist_item and album_id:
                    # Find or add album
                    album_item = self._find_album_item(artist_item, album_id)
                    if not album_item:
                        print(f"  Álbum no encontrado en el árbol, buscando detalles para ID: {album_id}")
                        album = self.parent.db_manager.get_album_details(album_id)
                        if album:
                            print(f"  Añadiendo álbum: {album.get('name')}")
                            album_item = self._add_filtered_album(album, artist_item, only_local, load_content=False)
                        else:
                            print(f"  No se encontraron detalles para el álbum con ID: {album_id}")
                    
                    # Add song to album
                    if album_item:
                        print(f"  Añadiendo canción: {song.get('title')} al álbum")
                        song_item = self._add_filtered_song(song, album_item, only_local)
                        if not song_item:
                            print(f"  ERROR: No se pudo añadir la canción al álbum")
                    else:
                        print(f"  ERROR: No se pudo encontrar o crear el álbum para la canción")
                elif not album_id:
                    print(f"  ADVERTENCIA: La canción {song.get('title')} no tiene album_id")
            else:
                print(f"  ERROR: La canción {song.get('title')} no tiene artist_id")
        
        # Expand top-level items
        top_count = self.parent.results_tree_widget.topLevelItemCount()
        print(f"Expanding {top_count} elementos de nivel superior")
        for i in range(top_count):
            self.parent.results_tree_widget.topLevelItem(i).setExpanded(True)
        
        print("Búsqueda simple completada")


    def _find_artist_item(self, artist_id):
        """Find an artist item in the tree by ID."""
        for i in range(self.parent.results_tree_widget.topLevelItemCount()):
            item = self.parent.results_tree_widget.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'artist' and data.get('id') == artist_id:
                return item
        return None

    def _find_album_item(self, artist_item, album_id):
        """Find an album item under an artist by ID."""
        print(f"Buscando álbum con ID {album_id} bajo el artista")
        for i in range(artist_item.childCount()):
            item = artist_item.child(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'album' and data.get('id') == album_id:
                print(f"Álbum encontrado")
                return item
        print(f"Álbum con ID {album_id} no encontrado bajo el artista")
        return None

    def _add_filtered_artist(self, artist, only_local=False, load_content=True):
        """Add an artist to the tree with filtered content."""
        # Create artist item
        artist_item = QTreeWidgetItem(self.parent.results_tree_widget)
        artist_item.setText(0, artist.get('name', 'Unknown Artist'))
        artist_item.setText(1, str(artist.get('formed_year', '')) if artist.get('formed_year') else "")
        artist_item.setText(2, artist.get('origin', ''))
        
        # Store artist ID in the item
        artist_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'artist', 'id': artist['id']})
        
        # Load artist's albums and songs if requested
        if load_content:
            # Get all albums for this artist
            albums = self.parent.db_manager.get_artist_albums(artist['id'])
            
            # Filter and add albums
            for album in albums:
                # Skip non-local albums if filtering is enabled
                if only_local and album.get('origen') != 'local':
                    continue
                    
                self._add_filtered_album(album, artist_item, only_local)
        
        return artist_item

    def _add_filtered_album(self, album, artist_item, only_local=False, load_content=True):
        """Add an album to an artist with filtered content."""
        # Skip non-local albums if filtering is enabled
        if only_local and ('origen' in album and album['origen'] != 'local'):
            print(f"Verificando si el álbum tiene canciones locales: {album['name']}, ID: {album['id']}")
            
            # Obtener canciones del álbum para verificar si hay alguna local
            songs = self.parent.db_manager.get_album_songs(album['id'], only_local=True)
            
            # Si hay canciones locales, mostrar el álbum aunque no sea local
            if not songs or len(songs) == 0:
                print(f"Saltando álbum no local sin canciones locales: {album['name']}")
                return None
            else:
                print(f"Álbum no local pero con {len(songs)} canciones locales, mostrando: {album['name']}")
        
        # Check if album is already added
        for i in range(artist_item.childCount()):
            item = artist_item.child(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'album' and data.get('id') == album['id']:
                print(f"Álbum ya añadido: {album['name']}")
                return item
        
        # Create album item
        print(f"Creando nuevo item de álbum: {album['name']}")
        album_item = QTreeWidgetItem(artist_item)
        album_item.setText(0, album['name'] if 'name' in album else 'Unknown Album')
        album_item.setText(1, str(album['year']) if 'year' in album and album['year'] else "")
        album_item.setText(2, album['genre'] if 'genre' in album else "")
        
        # Store album ID in the item
        album_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'album', 'id': album['id']})
        
        # Load album's songs if requested
        if load_content:
            print(f"Cargando canciones para el álbum: {album['name']}")
            # Get songs for this album (usando only_local si está activado)
            songs = self.parent.db_manager.get_album_songs(album['id'], only_local)
            print(f"Encontradas {len(songs)} canciones para el álbum")
            
            # Add songs to album
            for song in songs:
                title = song['title'] if 'title' in song else 'Unknown Title'
                print(f"Añadiendo canción: {title} al álbum")
                song_item = self._add_filtered_song(song, album_item, only_local)
                if not song_item:
                    print(f"ERROR: No se pudo añadir la canción {title} al álbum")
        else:
            print(f"Saltando carga de canciones para el álbum: {album['name']}")
        
        return album_item
 



    def set_only_local(self, state):
        """Establecer el estado de filtrado de solo archivos locales sin depender del checkbox"""
        self.only_local_state = bool(state)
        print(f"Estado de filtrado 'only_local' establecido a: {self.only_local_state}")
        
        # Si ya existe el widget, actualizar su estado
        if hasattr(self.parent, 'only_local_files') and self.parent.only_local_files is not None:
            # Evitar actualizar si ya tiene el mismo estado (para evitar eventos en cascada)
            current_state = self.parent.only_local_files.isChecked()
            if current_state != self.only_local_state:
                print(f"Actualizando checkbox de {current_state} a {self.only_local_state}")
                self.parent.only_local_files.setChecked(self.only_local_state)





# borrar?

    def _build_filtered_tree(self, artists, albums, songs, only_local=False):
        """Build tree structure with proper local filtering for all elements."""
        # Track artists already added to avoid duplicates
        added_artists = {}
        added_albums = {}  # Track by (artist_id, album_id) tuple
        
        # Process artists first
        for artist in artists:
            artist_item = self._add_artist_to_tree(artist, only_local)
            if artist_item:
                added_artists[artist['id']] = artist_item
        
        # Process albums, ensuring they belong to proper artists
        for album in albums:
            artist_id = album.get('artist_id')
            if artist_id:
                # If artist is already added, use that item
                if artist_id in added_artists:
                    artist_item = added_artists[artist_id]
                else:
                    # Get artist details and add to tree
                    artist = self.parent.db_manager.get_artist_details(artist_id)
                    if artist:
                        artist_item = self._add_artist_to_tree(artist, only_local)
                        if artist_item:
                            added_artists[artist_id] = artist_item
                    else:
                        continue  # Skip if artist not found
                    
                # Now add album to its artist
                album_item = self._add_album_to_tree(album, artist_item, only_local)
                if album_item:
                    added_albums[(artist_id, album['id'])] = album_item
        
        # Process songs, ensuring they belong to proper albums
        for song in songs:
            album_id = song.get('album_id')
            artist_id = song.get('artist_id')
            
            if album_id and artist_id:
                # If album is already added, use that item
                if (artist_id, album_id) in added_albums:
                    album_item = added_albums[(artist_id, album_id)]
                else:
                    # Get album details
                    album = self.parent.db_manager.get_album_details(album_id)
                    if not album:
                        continue  # Skip if album not found
                    
                    # If origin filtering is enabled, check album origin
                    if only_local and album.get('origen') != 'local':
                        continue
                    
                    # Find or add artist
                    if artist_id in added_artists:
                        artist_item = added_artists[artist_id]
                    else:
                        artist = self.parent.db_manager.get_artist_details(artist_id)
                        if not artist:
                            continue  # Skip if artist not found
                        
                        artist_item = self._add_artist_to_tree(artist, only_local)
                        if not artist_item:
                            continue
                        added_artists[artist_id] = artist_item
                    
                    # Add album to artist
                    album_item = self._add_album_to_tree(album, artist_item, only_local)
                    if not album_item:
                        continue
                    added_albums[(artist_id, album_id)] = album_item
                
                # Add song to album
                self._add_song_to_tree(song, album_item, only_local)

    def _add_artist_to_tree(self, artist, only_local=False):
        """Add an artist to the tree widget with local filtering."""
        # Check if origin filtering is needed
        if only_local:
            # Check if this artist has any local albums
            conn = self.parent.db_manager._get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) as count 
                        FROM albums 
                        WHERE artist_id = ? AND origen = 'local'
                    """, (artist['id'],))
                    result = cursor.fetchone()
                    if result and result['count'] == 0:
                        return None  # Skip artist with no local albums
                except Exception as e:
                    print(f"Error checking local albums: {e}")
                finally:
                    conn.close()
        
        # Create artist item
        artist_item = QTreeWidgetItem(self.parent.results_tree_widget)
        artist_item.setText(0, artist['name'])
        artist_item.setText(1, str(artist['formed_year']) if artist.get('formed_year') else "")
        artist_item.setText(2, artist.get('origin', ""))
        
        # Store artist ID in the item
        artist_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'artist', 'id': artist['id']})
        
        return artist_item

    def _add_album_to_tree(self, album, artist_item, only_local=False):
        """Add an album to the artist item with local filtering."""
        # Check if origin filtering is needed
        if only_local and album.get('origen') != 'local':
            return None
        
        # Check if this album is already a child of the artist
        for i in range(artist_item.childCount()):
            child = artist_item.child(i)
            if child.text(0) == album['name']:
                return child  # Return existing item
        
        # Create album item
        album_item = QTreeWidgetItem(artist_item)
        album_item.setText(0, album['name'])
        album_item.setText(1, str(album['year']) if album.get('year') else "")
        album_item.setText(2, album.get('genre', ""))
        
        # Store album ID in the item
        album_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'album', 'id': album['id']})
        
        # If we're not doing a full load of songs here (deferring to _add_song_to_tree),
        # we could add a check to ensure this album has local songs if only_local is True
        
        return album_item

    def _add_song_to_tree(self, song, album_item, only_local=False):
        """Add a song to the album item with local filtering."""
        # Check if origin filtering is needed
        if only_local and song.get('origen') != 'local':
            return None
        
        # Create a unique identifier to check for duplicates
        title = song.get('title', 'Unknown Title')
        track_number = song.get('track_number', '')
        song_id = f"{track_number}_{title}"
        
        # Check if this song is already a child of the album
        for i in range(album_item.childCount()):
            child = album_item.child(i)
            child_text = child.text(0)
            if track_number and '.' in child_text:
                parts = child_text.split('.')
                if parts[0].strip() == str(track_number) and parts[1].strip() == title:
                    return child  # Return existing item
            elif child_text == title:
                return child  # Return existing item
        
        # Create song item
        song_item = QTreeWidgetItem(album_item)
        
        # Format the song title with track number if available
        if track_number:
            song_item.setText(0, f"{track_number}. {title}")
        else:
            song_item.setText(0, title)
        
        # Format duration (convert seconds to mm:ss)
        duration_str = ""
        if song.get('duration'):
            minutes = int(song['duration']) // 60
            seconds = int(song['duration']) % 60
            duration_str = f"{minutes}:{seconds:02d}"
        
        song_item.setText(1, duration_str)
        song_item.setText(2, song.get('genre', ""))
        
        # Store song ID in the item
        song_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'song', 'id': song['id']})
        
        return song_item



# FILTROS ESPECIALES

    def _has_special_filters(self, query):
        """Verifica si la consulta contiene filtros especiales."""
        filters = ["a:", "d:", "g:", "y:", "s:", "rs:", "rm:", "ra:", "t:"]  # Añadir t: para título
        return any(f in query for f in filters)

    def _perform_filtered_search(self, query, only_local=False):
        """Realiza una búsqueda con filtros especiales manteniendo la estructura jerárquica."""
        # Analizar la consulta para extraer los filtros
        filters = self._extract_filters(query)
        
        print(f"Filtros detectados: {filters}")
        
        # Aplicar los filtros según su tipo
        if "title" in filters:  # Filtro para título de canción (t:)
            # Buscar solo canciones que coincidan con el filtro de título
            self._search_songs_by_title(filters["title"], only_local)
        elif "artist" in filters:
            # Buscar artistas que coincidan con el filtro
            artists = self.parent.db_manager.search_artists(filters["artist"], only_local)
            for artist in artists:
                self._add_filtered_artist(artist, only_local)
        elif "album" in filters:
            # Buscar álbumes que coincidan con el filtro
            self._search_albums_filtered(filters["album"], only_local)
        elif "genre" in filters:
            # Buscar por género manteniendo la estructura
            self._search_by_genre(filters["genre"], only_local)
        elif "year" in filters:
            # Buscar por año manteniendo la estructura
            self._search_by_year(filters["year"], only_local)
        elif "label" in filters:
            # Buscar por sello manteniendo la estructura
            self._search_by_label(filters["label"], only_local)
        elif "recent_weeks" in filters:
            # Buscar por semanas recientes manteniendo la estructura
            self._search_recent(filters["recent_weeks"], "week", only_local)
        elif "recent_months" in filters:
            # Buscar por meses recientes manteniendo la estructura
            self._search_recent(filters["recent_months"], "month", only_local)
        elif "recent_years" in filters:
            # Buscar por años recientes manteniendo la estructura
            self._search_recent(filters["recent_years"], "year", only_local)
        
        # Expandir elementos de primer nivel
        for i in range(self.parent.results_tree_widget.topLevelItemCount()):
            self.parent.results_tree_widget.topLevelItem(i).setExpanded(True)

    def _extract_filters(self, query):
        """Extrae los filtros de la consulta."""
        filters = {}
        
        # Lista de prefijos a buscar
        prefix_map = {
            "a:": "artist",
            "d:": "album",
            "g:": "genre",
            "y:": "year",
            "s:": "label",
            "rs:": "recent_weeks",
            "rm:": "recent_months",
            "ra:": "recent_years",
            "t:": "title"  # Añadir filtro para título
        }
        
        # Buscar cada prefijo en la consulta
        for prefix, filter_name in prefix_map.items():
            if prefix in query:
                # Encontrar la posición del prefijo
                pos = query.find(prefix)
                # Extraer el resto de la cadena después del prefijo
                substring = query[pos + len(prefix):]
                
                # Buscar el siguiente prefijo, si existe
                next_prefix_pos = len(substring)
                for p in prefix_map.keys():
                    if p in substring:
                        p_pos = substring.find(p)
                        if 0 <= p_pos < next_prefix_pos:
                            next_prefix_pos = p_pos
                
                # Extraer el valor hasta el siguiente prefijo o el final
                filter_value = substring[:next_prefix_pos].strip()
                filters[filter_name] = filter_value
        
        return filters

    def _search_songs_by_title(self, title_query, only_local=False):
        """Busca canciones por título y las muestra en el árbol de resultados."""
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            query_pattern = f"%{title_query}%"
            
            # Consulta para encontrar canciones por título
            if only_local:
                sql = """
                    SELECT s.id, s.title, s.track_number, s.artist, s.album,
                        s.genre, s.date, s.duration, s.file_path, s.origen,
                        ar.id as artist_id, al.id as album_id
                    FROM songs s
                    LEFT JOIN artists ar ON s.artist = ar.name
                    LEFT JOIN albums al ON s.album = al.name AND al.artist_id = ar.id
                    WHERE s.title LIKE ? AND s.origen = 'local'
                    ORDER BY s.artist, s.album, s.track_number, s.title
                """
            else:
                sql = """
                    SELECT s.id, s.title, s.track_number, s.artist, s.album,
                        s.genre, s.date, s.duration, s.file_path, s.origen,
                        ar.id as artist_id, al.id as album_id
                    FROM songs s
                    LEFT JOIN artists ar ON s.artist = ar.name
                    LEFT JOIN albums al ON s.album = al.name AND al.artist_id = ar.id
                    WHERE s.title LIKE ?
                    ORDER BY s.artist, s.album, s.track_number, s.title
                """
            
            print(f"SQL para búsqueda de títulos: {sql}")
            cursor.execute(sql, (query_pattern,))
            
            # Obtener todas las filas
            rows = cursor.fetchall()
            print(f"Encontradas {len(rows)} canciones con título: {title_query}")
            
            # Convertir filas a diccionarios
            songs = [dict(row) for row in rows]
            
            # Almacenar artistas y álbumes ya añadidos para evitar duplicados
            artists_added = {}
            albums_added = {}
            
            for song in songs:
                # Obtener IDs de artista y álbum
                artist_id = song.get('artist_id')
                album_id = song.get('album_id')
                
                if not artist_id:
                    print(f"Canción sin artista ID: {song.get('title')}")
                    continue
                    
                # Añadir artista si no está ya en el árbol
                if artist_id not in artists_added:
                    artist = self.parent.db_manager.get_artist_details(artist_id)
                    if artist:
                        artist_item = self._add_filtered_artist(artist, only_local, load_content=False)
                        artists_added[artist_id] = artist_item
                    else:
                        print(f"No se encontró el artista con ID: {artist_id}")
                        continue
                
                artist_item = artists_added.get(artist_id)
                
                # Añadir álbum si no está ya en el árbol
                if album_id and (artist_id, album_id) not in albums_added:
                    album = self.parent.db_manager.get_album_details(album_id)
                    if album:
                        album_item = self._add_filtered_album(album, artist_item, only_local, load_content=False)
                        albums_added[(artist_id, album_id)] = album_item
                    else:
                        print(f"No se encontró el álbum con ID: {album_id}")
                        continue
                
                album_item = albums_added.get((artist_id, album_id))
                
                # Añadir canción al álbum
                if album_item:
                    self._add_filtered_song(song, album_item, only_local)
                else:
                    print(f"No se pudo añadir la canción {song.get('title')} al árbol")
            
        except sqlite3.Error as e:
            print(f"Error en búsqueda de títulos: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()


    def _search_by_genre(self, genre_query, only_local=False):
        """Busca por género manteniendo la estructura jerárquica completa."""
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            query_pattern = f"%{genre_query}%"
            
            # Consulta para encontrar álbumes por género
            if only_local:
                sql = """
                    SELECT DISTINCT a.id as album_id, a.name as album_name, a.year, a.genre, a.label, a.origen,
                        ar.id as artist_id, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.genre LIKE ? AND a.origen = 'local'
                    ORDER BY ar.name, a.year DESC
                """
            else:
                sql = """
                    SELECT DISTINCT a.id as album_id, a.name as album_name, a.year, a.genre, a.label, a.origen,
                        ar.id as artist_id, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.genre LIKE ?
                    ORDER BY ar.name, a.year DESC
                """
            
            cursor.execute(sql, (query_pattern,))
            
            # Diccionario para almacenar los artistas ya añadidos
            artists_added = {}
            
            for row in cursor.fetchall():
                artist_id = row['artist_id']
                album_id = row['album_id']
                
                # Verificar filtro de solo local
                if only_local and ('origen' in row.keys() and row['origen'] != 'local'):
                    continue
                
                # Si el artista no está en nuestro diccionario, lo añadimos
                if artist_id not in artists_added:
                    # Obtener detalles del artista
                    artist = self.parent.db_manager.get_artist_details(artist_id)
                    if artist:
                        # Añadir artista al árbol
                        artist_item = self._add_filtered_artist(artist, only_local, load_content=False)
                        artists_added[artist_id] = artist_item
                
                # Obtener el item del artista
                artist_item = artists_added.get(artist_id)
                
                if artist_item:
                    # Crear objeto álbum y añadirlo al artista
                    album = {}
                    for key in row.keys():
                        album[key] = row[key]
                    
                    # Renombrar campos para que coincidan con la estructura esperada
                    if 'album_id' in album:
                        album['id'] = album['album_id']
                    if 'album_name' in album:
                        album['name'] = album['album_name']
                    
                    # Añadir álbum al artista
                    album_item = self._add_filtered_album(album, artist_item, only_local, load_content=False)
                    
                    # Asegurarnos de que el álbum se haya añadido correctamente
                    if album_item:
                        # Ahora cargar las canciones de este álbum
                        songs = self.parent.db_manager.get_album_songs(album_id, only_local)
                        for song in songs:
                            self._add_filtered_song(song, album_item, only_local)
        
        except sqlite3.Error as e:
            print(f"Error en búsqueda por género: {e}")
        finally:
            conn.close()

    def _search_by_year(self, year_query, only_local=False):
        """Busca por año manteniendo la estructura jerárquica completa."""
        # Procesar el año que puede venir en varios formatos
        year_range = self._process_year_query(year_query)
        if not year_range:
            return
        
        min_year, max_year = year_range
        
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Construir la consulta SQL
            if only_local:
                sql = """
                    SELECT DISTINCT a.id as album_id, a.name as album_name, a.year, a.genre, a.label, a.origen,
                        ar.id as artist_id, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.origen = 'local' AND 
                """
            else:
                sql = """
                    SELECT DISTINCT a.id as album_id, a.name as album_name, a.year, a.genre, a.label, a.origen,
                        ar.id as artist_id, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE 
                """
            
            # Condición para el año
            if min_year == max_year:
                # Buscar un año específico
                sql += "(a.year = ? OR a.year LIKE ?)"
                year_pattern = f"{min_year}%"
                params = (str(min_year), year_pattern)
            else:
                # Buscar un rango de años
                sql += "(CAST(substr(a.year, 1, 4) AS INTEGER) BETWEEN ? AND ?)"
                params = (min_year, max_year)
            
            sql += " ORDER BY ar.name, a.year DESC"
            
            cursor.execute(sql, params)
            
            # Diccionario para almacenar los artistas ya añadidos
            artists_added = {}
            
            for row in cursor.fetchall():
                artist_id = row['artist_id']
                album_id = row['album_id']
                
                # Verificar filtro de solo local
                if only_local and ('origen' in row.keys() and row['origen'] != 'local'):
                    continue
                
                # Si el artista no está en nuestro diccionario, lo añadimos
                if artist_id not in artists_added:
                    # Obtener detalles del artista
                    artist = self.parent.db_manager.get_artist_details(artist_id)
                    if artist:
                        # Añadir artista al árbol
                        artist_item = self._add_filtered_artist(artist, only_local, load_content=False)
                        artists_added[artist_id] = artist_item
                
                # Obtener el item del artista
                artist_item = artists_added.get(artist_id)
                
                if artist_item:
                    # Crear objeto álbum y añadirlo al artista
                    album = {}
                    for key in row.keys():
                        album[key] = row[key]
                    
                    # Renombrar campos para que coincidan con la estructura esperada
                    if 'album_id' in album:
                        album['id'] = album['album_id']
                    if 'album_name' in album:
                        album['name'] = album['album_name']
                    
                    # Añadir álbum al artista
                    album_item = self._add_filtered_album(album, artist_item, only_local, load_content=False)
                    
                    # Asegurarnos de que el álbum se haya añadido correctamente
                    if album_item:
                        # Ahora cargar las canciones de este álbum
                        songs = self.parent.db_manager.get_album_songs(album_id, only_local)
                        for song in songs:
                            self._add_filtered_song(song, album_item, only_local)
        
        except sqlite3.Error as e:
            print(f"Error en búsqueda por año: {e}")
        finally:
            conn.close()

    def _search_by_label(self, label_query, only_local=False):
        """Busca por sello discográfico creando una estructura jerárquica con el sello como nodo raíz."""
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            query_pattern = f"%{label_query}%"
            
            # Primero, obtener los sellos que coinciden con la búsqueda
            if only_local:
                label_sql = """
                    SELECT DISTINCT a.label
                    FROM albums a
                    WHERE a.label LIKE ? AND a.origen = 'local'
                    ORDER BY a.label
                """
            else:
                label_sql = """
                    SELECT DISTINCT a.label
                    FROM albums a
                    WHERE a.label LIKE ?
                    ORDER BY a.label
                """
            
            cursor.execute(label_sql, (query_pattern,))
            labels = cursor.fetchall()
            
            # Para cada sello encontrado, crear un nodo raíz
            for label_row in labels:
                label_name = label_row['label']
                if not label_name:
                    continue
                    
                # Crear un item para el sello
                label_item = QTreeWidgetItem(self.parent.results_tree_widget)
                label_item.setText(0, f"Sello: {label_name}")
                label_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'label', 'name': label_name})
                
                # Consultar los artistas que tienen álbumes bajo este sello
                if only_local:
                    artist_sql = """
                        SELECT DISTINCT ar.id as artist_id, ar.name as artist_name
                        FROM albums a
                        JOIN artists ar ON a.artist_id = ar.id
                        WHERE a.label = ? AND a.origen = 'local'
                        ORDER BY ar.name
                    """
                else:
                    artist_sql = """
                        SELECT DISTINCT ar.id as artist_id, ar.name as artist_name
                        FROM albums a
                        JOIN artists ar ON a.artist_id = ar.id
                        WHERE a.label = ?
                        ORDER BY ar.name
                    """
                
                cursor.execute(artist_sql, (label_name,))
                artists = cursor.fetchall()
                
                # Para cada artista, crear un nodo hijo bajo el sello
                for artist_row in artists:
                    artist_id = artist_row['artist_id']
                    
                    # Obtener detalles completos del artista
                    artist = self.parent.db_manager.get_artist_details(artist_id)
                    if not artist:
                        continue
                    
                    # Crear un item para el artista bajo el sello
                    artist_item = QTreeWidgetItem(label_item)
                    artist_item.setText(0, artist.get('name', 'Unknown Artist'))
                    artist_item.setText(1, str(artist.get('formed_year', '')) if artist.get('formed_year') else "")
                    artist_item.setText(2, artist.get('origin', ''))
                    artist_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'artist', 'id': artist['id']})
                    
                    # Consultar los álbumes de este artista para este sello
                    if only_local:
                        album_sql = """
                            SELECT id, name, year, genre, total_tracks, origen
                            FROM albums
                            WHERE artist_id = ? AND label = ? AND origen = 'local'
                            ORDER BY year DESC, name
                        """
                    else:
                        album_sql = """
                            SELECT id, name, year, genre, total_tracks, origen
                            FROM albums
                            WHERE artist_id = ? AND label = ?
                            ORDER BY year DESC, name
                        """
                    
                    cursor.execute(album_sql, (artist_id, label_name))
                    albums = cursor.fetchall()
                    
                    # Para cada álbum, crear un nodo hijo bajo el artista
                    for album_row in albums:
                        # Convertir el objeto sqlite3.Row a diccionario para usar .get()
                        album = self._row_to_dict(album_row)
                        
                        # Verificar filtro de solo local
                        if only_local and album.get('origen') != 'local':
                            continue
                        
                        # Añadir álbum al artista
                        album_item = self._add_filtered_album(album, artist_item, only_local, load_content=False)
                        
                        # Asegurarnos de que el álbum se haya añadido correctamente
                        if album_item:
                            # Ahora cargar las canciones de este álbum
                            songs = self.parent.db_manager.get_album_songs(album['id'], only_local)
                            for song in songs:
                                self._add_filtered_song(song, album_item, only_local)
                
                # Expandir el nodo del sello para mostrar los artistas
                label_item.setExpanded(True)
        
        except sqlite3.Error as e:
            print(f"Error en búsqueda por sello: {e}")
        finally:
            conn.close()

    def _search_recent(self, time_value, time_unit, only_local=False):
        """Busca elementos añadidos recientemente manteniendo la estructura jerárquica."""
        try:
            # Convertir valor a entero
            time_value = int(time_value.strip())
        except ValueError:
            print(f"Valor de tiempo inválido: {time_value}")
            return
        
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Construir la consulta según la unidad de tiempo
            if time_unit == "week":
                column = "added_week"
            elif time_unit == "month":
                column = "added_month"
            elif time_unit == "year":
                column = "added_year"
            else:
                print(f"Unidad de tiempo inválida: {time_unit}")
                return
            
            # Construir la consulta SQL
            if only_local:
                sql = f"""
                    SELECT DISTINCT s.id as song_id, s.title, s.track_number, s.artist, s.album, s.genre, 
                        s.file_path, s.duration, s.bitrate, ar.id as artist_id, al.id as album_id,
                        al.name as album_name, al.year as album_year, al.genre as album_genre
                    FROM songs s
                    LEFT JOIN artists ar ON s.artist = ar.name
                    LEFT JOIN albums al ON s.album = al.name AND al.artist_id = ar.id
                    WHERE s.{column} <= ? AND s.origen = 'local'
                    ORDER BY ar.name, al.name, s.track_number
                """
            else:
                sql = f"""
                    SELECT DISTINCT s.id as song_id, s.title, s.track_number, s.artist, s.album, s.genre, 
                        s.file_path, s.duration, s.bitrate, ar.id as artist_id, al.id as album_id,
                        al.name as album_name, al.year as album_year, al.genre as album_genre
                    FROM songs s
                    LEFT JOIN artists ar ON s.artist = ar.name
                    LEFT JOIN albums al ON s.album = al.name AND al.artist_id = ar.id
                    WHERE s.{column} <= ?
                    ORDER BY ar.name, al.name, s.track_number
                """
            
            cursor.execute(sql, (time_value,))
            
            # Diccionarios para almacenar los artistas y álbumes ya añadidos
            artists_added = {}
            albums_added = {}
            
            for row in cursor.fetchall():
                artist_id = row['artist_id']
                album_id = row['album_id']
                
                if not artist_id or not album_id:
                    continue
                
                # Si el artista no está en nuestro diccionario, lo añadimos
                if artist_id not in artists_added:
                    # Obtener detalles del artista
                    artist = self.parent.db_manager.get_artist_details(artist_id)
                    if artist:
                        # Añadir artista al árbol
                        artist_item = self._add_filtered_artist(artist, only_local, load_content=False)
                        artists_added[artist_id] = artist_item
                
                # Obtener el item del artista
                artist_item = artists_added.get(artist_id)
                
                if artist_item:
                    # Si el álbum no está en nuestro diccionario, lo añadimos
                    album_key = (artist_id, album_id)
                    if album_key not in albums_added:
                        # Crear objeto álbum
                        album = {
                            'id': album_id,
                            'name': row['album_name'],
                            'year': row['album_year'],
                            'genre': row['album_genre'],
                            'artist_id': artist_id
                        }
                        
                        # Añadir álbum al artista
                        album_item = self._add_filtered_album(album, artist_item, only_local, load_content=False)
                        albums_added[album_key] = album_item
                    
                    # Obtener el item del álbum
                    album_item = albums_added.get(album_key)
                    
                    # Si tenemos el álbum, añadir la canción
                    if album_item:
                        song = {
                            'id': row['song_id'],
                            'title': row['title'],
                            'track_number': row['track_number'],
                            'artist': row['artist'],
                            'album': row['album'],
                            'genre': row['genre'],
                            'file_path': row['file_path'],
                            'duration': row['duration'],
                            'bitrate': row['bitrate']
                        }
                        self._add_filtered_song(song, album_item, only_local)
        
        except sqlite3.Error as e:
            print(f"Error en búsqueda de elementos recientes: {e}")
        finally:
            conn.close()

    def _process_year_query(self, year_query):
        """Procesa la consulta de año y devuelve un rango (min_year, max_year)."""
        # Verificar si es un rango (por ejemplo, "2010-2020")
        if "-" in year_query:
            try:
                parts = year_query.split("-")
                min_year = int(parts[0].strip())
                max_year = int(parts[1].strip())
                return (min_year, max_year)
            except (ValueError, IndexError):
                print(f"Formato de rango de años inválido: {year_query}")
                return None
        
        # Si es un año específico
        try:
            year = int(year_query.strip())
            return (year, year)
        except ValueError:
            print(f"Formato de año inválido: {year_query}")
            return None


    def _search_artists_filtered(self, artist_query, only_local=False):
        """Busca artistas específicamente."""
        artists = self.parent.db_manager.search_artists(artist_query, only_local)
        for artist in artists:
            artist_item = self._add_filtered_artist(artist, only_local)

    def _search_albums_filtered(self, album_query, only_local=False):
        """Busca álbumes específicamente y construye una estructura jerárquica completa."""
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            query_pattern = f"%{album_query}%"
            
            # Consulta para encontrar álbumes con sus artistas asociados
            if only_local:
                sql = """
                    SELECT a.id as album_id, a.name as album_name, a.year, a.genre, a.origen,
                        ar.id as artist_id, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.name LIKE ? AND a.origen = 'local'
                    ORDER BY ar.name, a.year DESC
                """
            else:
                sql = """
                    SELECT a.id as album_id, a.name as album_name, a.year, a.genre, a.origen,
                        ar.id as artist_id, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.name LIKE ?
                    ORDER BY ar.name, a.year DESC
                """
            
            cursor.execute(sql, (query_pattern,))
            
            # Diccionario para almacenar los artistas ya añadidos
            artists_added = {}
            
            for row in cursor.fetchall():
                artist_id = row['artist_id']
                album_id = row['album_id']
                
                # Verificar filtro de solo local
                if only_local and ('origen' in row.keys() and row['origen'] != 'local'):
                    continue
                
                # Si el artista no está en nuestro diccionario, lo añadimos
                if artist_id not in artists_added:
                    # Obtener detalles del artista
                    artist = self.parent.db_manager.get_artist_details(artist_id)
                    if artist:
                        # Añadir artista al árbol
                        artist_item = self._add_filtered_artist(artist, only_local, load_content=False)
                        artists_added[artist_id] = artist_item
                
                # Obtener el item del artista
                artist_item = artists_added.get(artist_id)
                
                if artist_item:
                    # Crear objeto álbum
                    album = {}
                    for key in row.keys():
                        album[key] = row[key]
                    
                    # Renombrar campos para que coincidan con la estructura esperada
                    if 'album_id' in album:
                        album['id'] = album['album_id']
                    if 'album_name' in album:
                        album['name'] = album['album_name']
                    
                    # Añadir álbum al artista
                    album_item = self._add_filtered_album(album, artist_item, only_local)
                    
                    # Asegurarnos de que el álbum se haya añadido correctamente
                    if album_item:
                        # Ahora cargar las canciones de este álbum
                        songs = self.parent.db_manager.get_album_songs(album_id, only_local)
                        for song in songs:
                            self._add_filtered_song(song, album_item, only_local)
        
        except sqlite3.Error as e:
            print(f"Error en búsqueda de álbumes: {e}")
        finally:
            conn.close()



    def _add_filtered_song(self, song, album_item, only_local=False):
        """Add a song to an album with filtering."""
        # Return immediately if album_item is None
        if album_item is None:
            print("album_item es None, no se puede añadir canción")
            return None
                
        # Skip non-local songs if filtering is enabled
        origen = None
        if 'origen' in song:
            origen = song['origen']
        
        if only_local and origen != 'local':
            print(f"Saltando canción no local: {song['title'] if 'title' in song else 'Unknown Title'}")
            return None
                
        # Get song title and track number safely
        title = None
        track_number = None
        
        if 'title' in song:
            title = song['title']
        else:
            title = 'Unknown Title'
            
        if 'track_number' in song:
            track_number = song['track_number']
        else:
            track_number = ''
        
        # Check if song is already added
        for i in range(album_item.childCount()):
            item = album_item.child(i)
            # Check by ID if available
            data = item.data(0, Qt.ItemDataRole.UserRole)
            song_id = None
            if 'id' in song:
                song_id = song['id']
                    
            if data and data.get('type') == 'song' and data.get('id') == song_id:
                print(f"Canción ya añadida: {title}")
                return item
            
            # Or check by title and track number
            item_text = item.text(0)
            if track_number and '.' in item_text:
                parts = item_text.split('.', 1)
                if parts[0].strip() == str(track_number) and parts[1].strip() == title:
                    print(f"Canción ya añadida: {title}")
                    return item
            elif item_text == title:
                print(f"Canción ya añadida: {title}")
                return item
        
        # Create song item
        print(f"Creando nuevo item de canción: {title}")
        song_item = QTreeWidgetItem(album_item)
        
        # Format title with track number if available
        if track_number:
            song_item.setText(0, f"{track_number}. {title}")
        else:
            song_item.setText(0, title)
        
        # Format duration
        duration_str = ""
        if 'duration' in song and song['duration']:
            try:
                minutes = int(song['duration']) // 60
                seconds = int(song['duration']) % 60
                duration_str = f"{minutes}:{seconds:02d}"
            except Exception as e:
                print(f"Error formatting duration: {e}")
        
        song_item.setText(1, duration_str)
        
        # Get genre safely
        genre = ""
        if 'genre' in song:
            genre = song['genre']
        
        song_item.setText(2, genre)
        
        # Store song ID in the item
        song_id = None
        if 'id' in song:
            song_id = song['id']
        
        song_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'song', 'id': song_id})
        
        return song_item


  
    def _row_to_dict(self, row):
        """Convierte un objeto sqlite3.Row a un diccionario."""
        if row is None:
            return {}
        return {key: row[key] for key in row.keys()}

