from PyQt6.QtWidgets import QTreeWidgetItem, QSpinBox, QComboBox, QCheckBox, QPushButton, QRadioButton, QWidget, QGroupBox
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
        # Conectar los controles de filtro de tiempo cuando la UI esté inicializada
        if hasattr(parent, 'ui_initialized'):
            parent.ui_initialized.connect(self._connect_time_filters)            


    def perform_search(self):
        """Inicia el temporizador para realizar la búsqueda después de una pausa en la escritura."""
        query = self.parent.search_box.text().strip()
        
        # Si está vacío, limpiar resultados y salir
        if not query:
            self.parent.results_tree_widget.clear()
            return
        
        # Verificar si tenemos filtros especiales
        has_filters = self._has_special_filters(query)
        
        # Si tenemos filtros, verificamos si hay suficiente texto después del último filtro o operador
        if has_filters:
            # Encontrar el último filtro en la consulta
            filters = ["a:", "d:", "g:", "y:", "s:", "rs:", "rm:", "ra:", "t:", "b:"]
            operators = ["+", "&"]
            
            last_filter_pos = -1
            last_filter = None
            
            # Buscar el último filtro
            for f in filters:
                pos = query.rfind(f)
                if pos > last_filter_pos:
                    last_filter_pos = pos
                    last_filter = f
            
            # Buscar el último operador
            last_operator_pos = -1
            last_operator = None
            
            for op in operators:
                pos = query.rfind(op)
                if pos > last_operator_pos:
                    last_operator_pos = pos
                    last_operator = op
            
            # Determinar qué verificar: el último filtro o el último operador
            if last_operator_pos > last_filter_pos:
                # Si el último operador está después del último filtro
                text_after_operator = query[last_operator_pos + len(last_operator):].strip()
                
                # Si hay menos de 3 caracteres después del operador, no buscar todavía
                if len(text_after_operator) < 3:
                    return
                    
                # Si se acaba de añadir un nuevo filtro después del operador (termina en :), esperar más caracteres
                if ":" in text_after_operator and len(text_after_operator.split(":")[-1]) < 2:
                    return
            elif last_filter_pos >= 0:
                # Si el último filtro es lo más reciente
                text_after_filter = query[last_filter_pos + len(last_filter):].strip()
                
                # Si hay menos de 3 caracteres después del filtro, no buscar todavía
                # A menos que sea un filtro de año o tiempo (y:, rs:, rm:, ra:)
                if len(text_after_filter) < 3 and last_filter not in ["y:", "rs:", "rm:", "ra:"]:
                    return
                    
                # Si se acaba de añadir un nuevo filtro (termina en :), esperar más caracteres
                if text_after_filter == "" or (len(text_after_filter) < 2 and ":" in text_after_filter[-1:]):
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
        
        print(f"Ejecutando búsqueda con query: '{query}'")
        
        # Check if "only_local_files" is checked or set via configuration
        only_local = False
        
        # Primero, comprobar si tenemos un estado establecido programáticamente
        if hasattr(self, 'only_local_state'):
            only_local = self.only_local_state
        # Luego, verificar el widget si existe (esto permitirá que el usuario cambie el estado)
        elif hasattr(self.parent, 'only_local_files') and self.parent.only_local_files is not None:
            only_local = self.parent.only_local_files.isChecked()
        
        print(f"Realizando búsqueda con filtro 'only_local': {only_local}")
        
        # Verificar si hay operadores de combinación en la consulta
        if "&" in query:
            print("Detectado operador '&' - realizando búsqueda combinada")
            sub_queries = query.split("&")
            print(f"Sub-consultas: {sub_queries}")
            
            # Realizar la primera búsqueda en un árbol temporal
            self.parent.results_tree_widget.clear()
            first_query = sub_queries[0].strip()
            
            # Si la primera consulta está vacía, no hacer nada
            if not first_query:
                return
                
            # Realizar la primera búsqueda
            if self._has_special_filters(first_query):
                self._perform_filtered_search_combined(first_query, only_local)
            else:
                self._perform_simple_search(first_query, only_local)
            
            # Para cada sub-consulta adicional, aplicar un filtro adicional
            for i in range(1, len(sub_queries)):
                sub_query = sub_queries[i].strip()
                if not sub_query:
                    continue
                    
                print(f"Aplicando filtro adicional: '{sub_query}'")
                
                # Construir una lista de ítems clonados para no perder los originales
                cloned_items = []
                for j in range(self.parent.results_tree_widget.topLevelItemCount()):
                    original_item = self.parent.results_tree_widget.topLevelItem(j)
                    cloned_items.append(self._clone_tree_item(original_item))
                
                # Limpiar el árbol y aplicar el siguiente filtro
                self.parent.results_tree_widget.clear()
                
                # Filtrar los elementos clonados con la subconsulta
                self._apply_filter_to_items(sub_query, cloned_items, only_local)
        
        # Procesar filtros especiales normales o consultas con +
        elif self._has_special_filters(query):
            self._perform_filtered_search(query, only_local)
        else:
            # Búsqueda normal
            self._perform_simple_search(query, only_local)


    def _apply_filter_to_items(self, sub_query, items, only_local=False):
        """Aplica un filtro a una lista de ítems ya clonados."""
        print(f"Aplicando filtro '{sub_query}' a {len(items)} ítems")
        
        # Extract filter type and value
        filter_type = None
        filter_value = sub_query
        
        # Check for specific filters
        filters = {"a:": "artist", "t:": "title", "b:": "album", "g:": "genre"}
        for prefix, filter_name in filters.items():
            if sub_query.startswith(prefix):
                filter_type = filter_name
                filter_value = sub_query[len(prefix):].strip()
                break
        
        print(f"Tipo de filtro: {filter_type}, valor: '{filter_value}'")
        
        # Process each top-level item (artists)
        for artist_item in items:
            artist_text = artist_item.text(0).lower()
            
            # Check if artist matches the filter
            if filter_type == "artist" and filter_value.lower() not in artist_text:
                continue
            
            # If we're looking for albums or titles, we need to check children
            if filter_type in ["album", "title"]:
                matching_albums = []
                
                # Check each album of this artist
                for a_idx in range(artist_item.childCount()):
                    album_item = artist_item.child(a_idx)
                    album_text = album_item.text(0).lower()
                    
                    # Check if album matches the filter
                    if filter_type == "album" and filter_value.lower() not in album_text:
                        continue
                    
                    # If filtering by title, check songs in this album
                    if filter_type == "title":
                        matching_songs = []
                        
                        for s_idx in range(album_item.childCount()):
                            song_item = album_item.child(s_idx)
                            song_text = song_item.text(0).lower()
                            
                            if filter_value.lower() in song_text:
                                # Add this song
                                matching_songs.append(self._clone_tree_item(song_item))
                        
                        # If we found matching songs, add the album with just those songs
                        if matching_songs:
                            album_clone = self._clone_tree_item(album_item, include_children=False)
                            for song in matching_songs:
                                album_clone.addChild(song)
                            matching_albums.append(album_clone)
                    else:
                        # Not filtering by title, add the whole album
                        matching_albums.append(self._clone_tree_item(album_item))
                
                # If we found matching albums, add the artist with just those albums
                if matching_albums:
                    artist_clone = self._clone_tree_item(artist_item, include_children=False)
                    for album in matching_albums:
                        artist_clone.addChild(album)
                    self.parent.results_tree_widget.addTopLevelItem(artist_clone)
                
            else:
                # Not filtering by album or title, check if artist matches genre filter
                if filter_type == "genre":
                    # Check if any album or song matches the genre
                    has_matching_genre = False
                    
                    for a_idx in range(artist_item.childCount()):
                        album_item = artist_item.child(a_idx)
                        album_genre = album_item.text(2).lower()
                        
                        if filter_value.lower() in album_genre:
                            has_matching_genre = True
                            break
                        
                        # Check songs in this album
                        for s_idx in range(album_item.childCount()):
                            song_item = album_item.child(s_idx)
                            song_genre = song_item.text(2).lower()
                            
                            if filter_value.lower() in song_genre:
                                has_matching_genre = True
                                break
                        
                        if has_matching_genre:
                            break
                    
                    if not has_matching_genre:
                        continue
                
                # Add the artist item to the tree
                self.parent.results_tree_widget.addTopLevelItem(self._clone_tree_item(artist_item))
        
        # Expand top-level items
        for i in range(self.parent.results_tree_widget.topLevelItemCount()):
            self.parent.results_tree_widget.topLevelItem(i).setExpanded(True)


    # def _filter_existing_results(self, sub_query, initial_results):
    #     """Filtra los resultados existentes basados en una subconsulta."""
    #     print(f"Filtrando resultados existentes con subconsulta: '{sub_query}'")
        
    #     # Clear the tree first to rebuild it with filtered results
    #     self.parent.results_tree_widget.clear()
        
    #     # Extract filter type and value
    #     filter_type = None
    #     filter_value = sub_query
        
    #     # Check for specific filters
    #     filters = {"a:": "artist", "t:": "title", "b:": "album", "g:": "genre"}
    #     for prefix, filter_name in filters.items():
    #         if sub_query.startswith(prefix):
    #             filter_type = filter_name
    #             filter_value = sub_query[len(prefix):].strip()
    #             break
        
    #     print(f"Tipo de filtro: {filter_type}, valor: '{filter_value}'")
        
    #     # Process each top-level item (artists)
    #     for artist_item in initial_results:
    #         artist_data = artist_item.data(0, Qt.ItemDataRole.UserRole)
    #         artist_text = artist_item.text(0).lower()
            
    #         # Check if artist matches the filter
    #         if filter_type == "artist" and filter_value.lower() not in artist_text:
    #             continue
            
    #         # If we're looking for albums or titles, we need to check children
    #         if filter_type in ["album", "title"]:
    #             matching_albums = []
                
    #             # Check each album of this artist
    #             for a_idx in range(artist_item.childCount()):
    #                 album_item = artist_item.child(a_idx)
    #                 album_text = album_item.text(0).lower()
    #                 album_data = album_item.data(0, Qt.ItemDataRole.UserRole)
                    
    #                 # Check if album matches the filter
    #                 if filter_type == "album" and filter_value.lower() not in album_text:
    #                     # If looking for titles, check songs in this album
    #                     if filter_type == "title":
    #                         matching_songs = []
                            
    #                         for s_idx in range(album_item.childCount()):
    #                             song_item = album_item.child(s_idx)
    #                             song_text = song_item.text(0).lower()
                                
    #                             if filter_value.lower() in song_text:
    #                                 # Clone the song item
    #                                 matching_songs.append(self._clone_tree_item(song_item))
                            
    #                         # If we found matching songs, add the album with just those songs
    #                         if matching_songs:
    #                             cloned_album = self._clone_tree_item(album_item, include_children=False)
    #                             for song in matching_songs:
    #                                 cloned_album.addChild(song)
    #                             matching_albums.append(cloned_album)
                        
    #                     # If not looking for titles or no matches, skip this album
    #                     continue
                    
    #                 # Album matches or we're not filtering by album, check songs if filtering by title
    #                 if filter_type == "title":
    #                     matching_songs = []
                        
    #                     for s_idx in range(album_item.childCount()):
    #                         song_item = album_item.child(s_idx)
    #                         song_text = song_item.text(0).lower()
                            
    #                         if filter_value.lower() in song_text:
    #                             # Clone the song item
    #                             matching_songs.append(self._clone_tree_item(song_item))
                        
    #                     # If we found matching songs, add the album with just those songs
    #                     if matching_songs:
    #                         cloned_album = self._clone_tree_item(album_item, include_children=False)
    #                         for song in matching_songs:
    #                             cloned_album.addChild(song)
    #                         matching_albums.append(cloned_album)
    #                 else:
    #                     # Not filtering by title, add the whole album
    #                     matching_albums.append(self._clone_tree_item(album_item))
                
    #             # If we found matching albums, add the artist with just those albums
    #             if matching_albums:
    #                 cloned_artist = self._clone_tree_item(artist_item, include_children=False)
    #                 for album in matching_albums:
    #                     cloned_artist.addChild(album)
    #                 self.parent.results_tree_widget.addTopLevelItem(cloned_artist)
                
    #         else:
    #             # Not filtering by album or title, check if artist matches genre filter
    #             if filter_type == "genre":
    #                 # Check if any album or song matches the genre
    #                 has_matching_genre = False
                    
    #                 for a_idx in range(artist_item.childCount()):
    #                     album_item = artist_item.child(a_idx)
    #                     album_genre = album_item.text(2).lower()
                        
    #                     if filter_value.lower() in album_genre:
    #                         has_matching_genre = True
    #                         break
                        
    #                     # Check songs in this album
    #                     for s_idx in range(album_item.childCount()):
    #                         song_item = album_item.child(s_idx)
    #                         song_genre = song_item.text(2).lower()
                            
    #                         if filter_value.lower() in song_genre:
    #                             has_matching_genre = True
    #                             break
                        
    #                     if has_matching_genre:
    #                         break
                    
    #                 if not has_matching_genre:
    #                     continue
                
    #             # Add the artist item to the tree
    #             self.parent.results_tree_widget.addTopLevelItem(self._clone_tree_item(artist_item))
        
    #     # Expand top-level items
    #     for i in range(self.parent.results_tree_widget.topLevelItemCount()):
    #         self.parent.results_tree_widget.topLevelItem(i).setExpanded(True)

    def _clone_tree_item(self, item, include_children=True):
        """Clona un item del árbol, opcionalmente incluyendo sus hijos."""
        # Create a new item
        new_item = QTreeWidgetItem()
        
        # Copy text from columns
        for i in range(3):  # Assuming 3 columns
            new_item.setText(i, item.text(i))
        
        # Copy user data
        new_item.setData(0, Qt.ItemDataRole.UserRole, item.data(0, Qt.ItemDataRole.UserRole))
        
        # Recursively clone children if requested
        if include_children:
            for i in range(item.childCount()):
                new_item.addChild(self._clone_tree_item(item.child(i)))
        
        return new_item


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
        
        # Si ya existen los radio buttons, actualizar su estado
        if hasattr(self.parent, 'only_local_files') and self.parent.only_local_files is not None:
            # Evitar actualizar si ya tiene el mismo estado (para evitar eventos en cascada)
            current_state = self.parent.only_local_files.isChecked()
            if current_state != self.only_local_state:
                print(f"Actualizando radio button de {current_state} a {self.only_local_state}")
                self.parent.only_local_files.setChecked(self.only_local_state)
                if hasattr(self.parent, 'show_all') and self.parent.show_all is not None:
                    self.parent.show_all.setChecked(not self.only_local_state)





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
        filters = ["a:", "d:", "g:", "y:", "s:", "rs:", "rm:", "ra:", "t:"]
        operators = ["+", "&"]  
        # Comprobar si hay algún filtro
        has_filters = any(f in query for f in filters)
        
        # Si no hay filtros directos, comprobar si hay operadores combinados
        if not has_filters:
            return False
            
        # Si hay filtros, comprobar si hay operadores combinados
        has_operators = any(op in query for op in operators)
        
        return has_filters

    def _perform_filtered_search(self, query, only_local=False):
        """Realiza una búsqueda con filtros especiales manteniendo la estructura jerárquica."""
        # Si hay + en la consulta, separar en subconsultas
        if "+" in query:
            sub_queries = query.split("+")
            print(f"Detectado operador '+' - realizando búsquedas independientes: {sub_queries}")
            
            # Realizar cada búsqueda independientemente
            for sub_query in sub_queries:
                sub_query = sub_query.strip()
                if sub_query:
                    self._perform_filtered_search_combined(sub_query, only_local)
            
            # Expandir elementos de primer nivel
            for i in range(self.parent.results_tree_widget.topLevelItemCount()):
                self.parent.results_tree_widget.topLevelItem(i).setExpanded(True)
            
            return
        
        # Búsqueda normal con un solo filtro
        self._perform_filtered_search_combined(query, only_local)


    def _perform_filtered_search_combined(self, query, only_local=False):
        """Realiza una búsqueda con filtros especiales para consultas combinadas."""
        print(f"Realizando búsqueda filtrada con: '{query}'")
        
        # Analizar la consulta para extraer los filtros
        filters = self._extract_filters(query)
        
        # Aplicar los filtros según su tipo
        if "artist" in filters:
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
        
        elif "title" in filters:
            # Buscar canciones por título
            self._search_songs_by_title(filters["title"], only_local)


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
        print(f"Ejecutando búsqueda por año: {year_query}")
        
        # Intentar convertir a entero para búsqueda exacta
        try:
            year_value = int(year_query.strip())
        except ValueError:
            print(f"Valor de año inválido: {year_query}")
            return
        
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Construir la consulta SQL para encontrar álbumes por año
            # Nos aseguramos de buscar tanto el año exacto como años en formato YYYY-MM-DD
            if only_local:
                sql = """
                    SELECT DISTINCT a.id as album_id, a.name as album_name, a.year, a.genre, a.label, a.origen,
                        ar.id as artist_id, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE (a.year = ? OR a.year LIKE ?) AND a.origen = 'local'
                    ORDER BY ar.name, a.year DESC
                """
            else:
                sql = """
                    SELECT DISTINCT a.id as album_id, a.name as album_name, a.year, a.genre, a.label, a.origen,
                        ar.id as artist_id, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.year = ? OR a.year LIKE ?
                    ORDER BY ar.name, a.year DESC
                """
            
            # Usar dos patrones: año exacto y año con formato YYYY-*
            year_pattern = f"{year_value}-%"
            params = (str(year_value), year_pattern)
            
            print(f"Ejecutando SQL: {sql} con parámetros: {params}")
            cursor.execute(sql, params)
            
            # Diccionario para almacenar los artistas ya añadidos
            artists_added = {}
            
            # Procesar resultados
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
            
            # Expandir elementos de primer nivel
            for i in range(self.parent.results_tree_widget.topLevelItemCount()):
                item = self.parent.results_tree_widget.topLevelItem(i)
                item.setExpanded(True)
        
        except sqlite3.Error as e:
            print(f"Error en búsqueda por año: {e}")
            import traceback
            traceback.print_exc()
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
        
        # Limpiar resultados actuales
        self.parent.results_tree_widget.clear()
        
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Obtener la fecha actual para comparar
            import datetime
            now = datetime.datetime.now()
            
            # Determinar la columna y valor a usar según la unidad de tiempo
            if time_unit == "week":
                column = "added_week"
                current_value = int(now.strftime("%V"))  # Número de semana actual (1-53)
                compare_value = max(1, current_value - time_value)  # No permitir valores menores a 1
                
                # Considerar cambio de año
                if compare_value > current_value:
                    # Estamos cruzando al año anterior
                    where_clause = f"({column} >= {compare_value} OR {column} <= {current_value})"
                else:
                    where_clause = f"{column} >= {compare_value} AND {column} <= {current_value}"
                    
            elif time_unit == "month":
                column = "added_month"
                current_value = now.month
                compare_value = current_value - time_value
                
                # Considerar cambio de año
                if compare_value <= 0:
                    # Estamos cruzando al año anterior
                    months_in_current_year = current_value
                    months_in_prev_year = abs(compare_value)
                    year_column = "added_year"
                    current_year = now.year
                    prev_year = current_year - 1
                    
                    where_clause = f"({column} >= 1 AND {column} <= {current_value} AND {year_column} = {current_year}) OR " \
                                f"({column} > {12 - months_in_prev_year} AND {year_column} = {prev_year})"
                else:
                    where_clause = f"{column} >= {compare_value} AND {column} <= {current_value}"
                    
            elif time_unit == "year":
                column = "added_year"
                current_value = now.year
                compare_value = current_value - time_value
                where_clause = f"{column} >= {compare_value} AND {column} <= {current_value}"
                
            else:
                print(f"Unidad de tiempo inválida: {time_unit}")
                return
            
            print(f"Filtrando por tiempo: {where_clause}")
            
            # Construir consultas separadas para canciones, álbumes y artistas
            # 1. Primero, encontrar artistas que tienen elementos recientes
            if only_local:
                artist_sql = f"""
                    SELECT DISTINCT ar.id, ar.name, ar.formed_year, ar.origin
                    FROM artists ar
                    JOIN albums al ON ar.id = al.artist_id
                    JOIN songs s ON s.album = al.name
                    WHERE (s.{where_clause}) AND s.origen = 'local'
                    ORDER BY ar.name
                """
            else:
                artist_sql = f"""
                    SELECT DISTINCT ar.id, ar.name, ar.formed_year, ar.origin
                    FROM artists ar
                    JOIN albums al ON ar.id = al.artist_id
                    JOIN songs s ON s.album = al.name
                    WHERE s.{where_clause}
                    ORDER BY ar.name
                """
            
            cursor.execute(artist_sql)
            artists = cursor.fetchall()
            
            # Para cada artista, añadirlo al árbol
            for artist in artists:
                artist_item = self._add_filtered_artist({
                    'id': artist['id'],
                    'name': artist['name'],
                    'formed_year': artist['formed_year'],
                    'origin': artist['origin'],
                }, only_local, load_content=False)
                
                if artist_item:
                    # 2. Encontrar álbumes recientes para este artista
                    if only_local:
                        album_sql = f"""
                            SELECT DISTINCT al.id, al.name, al.year, al.genre
                            FROM albums al
                            JOIN songs s ON s.album = al.name
                            WHERE al.artist_id = ? AND (s.{where_clause}) AND s.origen = 'local'
                            ORDER BY al.year DESC, al.name
                        """
                    else:
                        album_sql = f"""
                            SELECT DISTINCT al.id, al.name, al.year, al.genre
                            FROM albums al
                            JOIN songs s ON s.album = al.name
                            WHERE al.artist_id = ? AND s.{where_clause}
                            ORDER BY al.year DESC, al.name
                        """
                    
                    cursor.execute(album_sql, (artist['id'],))
                    albums = cursor.fetchall()
                    
                    for album in albums:
                        album_item = self._add_filtered_album({
                            'id': album['id'],
                            'name': album['name'],
                            'year': album['year'],
                            'genre': album['genre'],
                        }, artist_item, only_local, load_content=False)
                        
                        if album_item:
                            # 3. Encontrar canciones recientes para este álbum
                            if only_local:
                                song_sql = f"""
                                    SELECT id, title, track_number, artist, album, genre, file_path, duration, origen
                                    FROM songs
                                    WHERE album = ? AND artist = ? AND {where_clause} AND origen = 'local'
                                    ORDER BY track_number, title
                                """
                            else:
                                song_sql = f"""
                                    SELECT id, title, track_number, artist, album, genre, file_path, duration, origen
                                    FROM songs
                                    WHERE album = ? AND artist = ? AND {where_clause}
                                    ORDER BY track_number, title
                                """
                            
                            cursor.execute(song_sql, (album['name'], artist['name']))
                            songs = cursor.fetchall()
                            
                            for song in songs:
                                self._add_filtered_song({
                                    'id': song['id'],
                                    'title': song['title'],
                                    'track_number': song['track_number'],
                                    'artist': song['artist'],
                                    'album': song['album'],
                                    'genre': song['genre'],
                                    'file_path': song['file_path'],
                                    'duration': song['duration'],
                                    'origen': song['origen'],
                                }, album_item, only_local)
            
            # Expandir elementos de nivel superior
            for i in range(self.parent.results_tree_widget.topLevelItemCount()):
                item = self.parent.results_tree_widget.topLevelItem(i)
                item.setExpanded(True)
        
        except Exception as e:
            print(f"Error en búsqueda de elementos recientes: {e}")
            import traceback
            traceback.print_exc()
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

# TIME FILTERS

    def _connect_time_filters(self):
        """Conectar los controles de filtro de tiempo cuando la UI esté inicializada."""
        print("Conectando controles de filtro de tiempo")
        
        # Obtener referencias a los controles relevantes
        if not hasattr(self.parent, 'advanced_settings_container'):
            print("WARNING: No se encontró el contenedor de ajustes avanzados")
            return
            
        # Buscar los controles dentro del widget avanzado
        time_value = self.parent.findChild(QSpinBox, "time_value")
        time_unit = self.parent.findChild(QComboBox, "time_unit")
        show_time_check = self.parent.findChild(QCheckBox, "show_time_unit_check")
        apply_time_filter = self.parent.findChild(QPushButton, "apply_time_filter")
        
        # Actualizar referencias locales
        if time_value:
            self.parent.time_value = time_value
            print("Control time_value encontrado")
        else:
            print("WARNING: Control time_value no encontrado")
            
        if time_unit:
            self.parent.time_unit = time_unit
            print("Control time_unit encontrado")
        else:
            print("WARNING: Control time_unit no encontrado")
        
        # Si tenemos el botón, conectarlo a la función adecuada
        if apply_time_filter:
            print("Conectando botón de filtro de tiempo")
            try:
                # Desconectar primero para evitar múltiples conexiones
                apply_time_filter.clicked.disconnect()
            except:
                pass
            
            # IMPORTANTE: Conectamos la señal al método correcto
            # El problema estaba aquí, estábamos conectando al método _apply_time_filter
            # pero ese método está en la clase SearchHandler, no en el parent
            apply_time_filter.clicked.connect(self._apply_time_filter)
            print("Botón apply_time_filter conectado correctamente")
        else:
            print("WARNING: Botón apply_time_filter no encontrado")
            
        # Conectar los radio buttons de origen
        only_local = self.parent.findChild(QRadioButton, "only_local_files")
        show_all = self.parent.findChild(QRadioButton, "show_all")
        
        if only_local and show_all:
            # Actualizar referencias para usarlas en otros métodos
            self.parent.only_local_files = only_local
            self.parent.show_all = show_all
            
            # Configurar grupo de botones
            if not hasattr(self.parent, 'origin_button_group'):
                from PyQt6.QtWidgets import QButtonGroup
                self.parent.origin_button_group = QButtonGroup(self.parent)
                self.parent.origin_button_group.addButton(only_local)
                self.parent.origin_button_group.addButton(show_all)
            
            # Conectar señales de cambio
            try:
                only_local.toggled.disconnect()
            except:
                pass
            try:
                show_all.toggled.disconnect()
            except:
                pass
            
            only_local.toggled.connect(self._on_only_local_toggled)
            show_all.toggled.connect(self._on_show_all_toggled)
            
            # Establecer estado inicial de los botones según configuración guardada
            only_local_state = getattr(self.parent, 'only_local_files_state', False)
            only_local.setChecked(only_local_state)
            show_all.setChecked(not only_local_state)


    def _apply_time_filter(self):
        """Aplica el filtro de tiempo según los valores seleccionados."""
        print("Aplicando filtro de tiempo")
        
        # Verificar que tenemos acceso a los controles necesarios
        if not hasattr(self.parent, 'time_value') or not hasattr(self.parent, 'time_unit'):
            print("ERROR: No se encontraron los controles de filtro de tiempo")
            print("Buscando controles de tiempo directamente...")
            
            # Intento de recuperación: buscar los controles directamente
            time_value = self.parent.findChild(QSpinBox, "time_value")
            time_unit = self.parent.findChild(QComboBox, "time_unit")
            
            if time_value and time_unit:
                # Guardar referencias para futuras llamadas
                self.parent.time_value = time_value
                self.parent.time_unit = time_unit
                print("Controles de tiempo encontrados y asignados")
            else:
                print("No se pudieron encontrar los controles de tiempo")
                return
        
        # Obtener el valor y la unidad de tiempo seleccionados
        time_value = self.parent.time_value.value()
        time_unit_index = self.parent.time_unit.currentIndex()
        
        # Determinar si aplica el filtro de "only_local"
        only_local = False
        if hasattr(self, 'only_local_state'):
            only_local = self.only_local_state
        elif hasattr(self.parent, 'only_local_files') and self.parent.only_local_files:
            only_local = self.parent.only_local_files.isChecked()
        
        # Convertir índice a unidad de tiempo
        time_unit = ""
        if time_unit_index == 0:
            time_unit = "week"
        elif time_unit_index == 1:
            time_unit = "month"
        elif time_unit_index == 2:
            time_unit = "year"
        
        print(f"Filtrando por {time_value} {time_unit}(s), only_local: {only_local}")
        
        # Limpiar resultados actuales y ejecutar la búsqueda
        self.parent.results_tree_widget.clear()
        self._search_recent(str(time_value), time_unit, only_local)


    def _search_by_year_range(self, year_range, only_local=False):
        """Busca por rango de años manteniendo la estructura jerárquica completa."""
        print(f"Ejecutando búsqueda por rango de años: {year_range}")
        
        # Analizar el rango de años
        try:
            year_begin, year_end = map(int, year_range.split('-'))
            if year_begin > year_end:
                year_begin, year_end = year_end, year_begin
        except (ValueError, TypeError):
            print(f"Formato de rango de años inválido: {year_range}")
            return
        
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Construir la consulta SQL para encontrar álbumes en el rango de años
            if only_local:
                sql = """
                    SELECT DISTINCT a.id as album_id, a.name as album_name, a.year, a.genre, a.label, a.origen,
                        ar.id as artist_id, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.origen = 'local' AND (
                        (CAST(substr(a.year, 1, 4) AS INTEGER) BETWEEN ? AND ?) OR
                        (a.year BETWEEN ? AND ?)
                    )
                    ORDER BY ar.name, a.year DESC
                """
            else:
                sql = """
                    SELECT DISTINCT a.id as album_id, a.name as album_name, a.year, a.genre, a.label, a.origen,
                        ar.id as artist_id, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE 
                        (CAST(substr(a.year, 1, 4) AS INTEGER) BETWEEN ? AND ?) OR
                        (a.year BETWEEN ? AND ?)
                    ORDER BY ar.name, a.year DESC
                """
            
            # Parámetros para la consulta
            params = (year_begin, year_end, str(year_begin), str(year_end))
            
            print(f"Ejecutando SQL: {sql} con parámetros: {params}")
            cursor.execute(sql, params)
            
            # Diccionario para almacenar los artistas ya añadidos
            artists_added = {}
            
            # Procesar resultados
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
            
            # Expandir elementos de primer nivel
            for i in range(self.parent.results_tree_widget.topLevelItemCount()):
                item = self.parent.results_tree_widget.topLevelItem(i)
                item.setExpanded(True)
        
        except sqlite3.Error as e:
            print(f"Error en búsqueda por rango de años: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()