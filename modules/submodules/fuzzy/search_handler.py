from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt

class SearchHandler:
    """Handles search operations for the music browser."""
    
    def __init__(self, parent):
        self.parent = parent
        
    def perform_search(self):
        """Perform a search based on the search box text."""
        query = self.parent.search_box.text().strip()
        if not query:
            return
        
        # Clear current results
        self.parent.results_tree_widget.clear()
        
        # Split the query into parts to handle advanced search
        # For now, just use the simple search
        self._perform_simple_search(query)
    
    def _perform_simple_search(self, query):
        """Perform a simple search across all entity types."""
        # Search artists
        artists = self.parent.db_manager.search_artists(query)
        self._add_artists_to_tree(artists)
        
        # Search albums
        albums = self.parent.db_manager.search_albums(query)
        self._add_albums_to_tree(albums)
        
        # Search songs
        songs = self.parent.db_manager.search_songs(query)
        self._add_songs_to_tree(songs)
        
        # Expand top-level items
        for i in range(self.parent.results_tree_widget.topLevelItemCount()):
            self.parent.results_tree_widget.topLevelItem(i).setExpanded(True)
    
    def _add_artists_to_tree(self, artists):
        """Add artists to the tree widget."""
        if not artists:
            return
            
        for artist in artists:
            # Create artist item
            artist_item = QTreeWidgetItem(self.parent.results_tree_widget)
            artist_item.setText(0, artist['name'])
            artist_item.setText(1, str(artist['formed_year']) if artist['formed_year'] else "")
            artist_item.setText(2, artist['origin'] if artist['origin'] else "")
            
            # Store artist ID in the item
            artist_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'artist', 'id': artist['id']})
            
            # Get albums for this artist
            albums = self.parent.db_manager.get_artist_albums(artist['id'])
            
            # Add album items
            for album in albums:
                album_item = QTreeWidgetItem(artist_item)
                album_item.setText(0, album['name'])
                album_item.setText(1, str(album['year']) if album['year'] else "")
                album_item.setText(2, album['genre'] if album['genre'] else "")
                
                # Store album ID in the item
                album_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'album', 'id': album['id']})
                
                # Get songs for this album
                songs = self.parent.db_manager.get_album_songs(album['id'])
                
                # Add song items
                for song in songs:
                    song_item = QTreeWidgetItem(album_item)
                    song_item.setText(0, f"{song['track_number']}. {song['title']}")
                    
                    # Format duration (convert seconds to mm:ss)
                    duration_str = ""
                    if song['duration']:
                        minutes = int(song['duration']) // 60
                        seconds = int(song['duration']) % 60
                        duration_str = f"{minutes}:{seconds:02d}"
                    
                    song_item.setText(1, duration_str)
                    song_item.setText(2, f"{song['bitrate']}kbps" if song['bitrate'] else "")
                    
                    # Store song ID in the item
                    song_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'song', 'id': song['id']})
    
    def _add_albums_to_tree(self, albums):
        """Add albums to the tree widget."""
        if not albums:
            return
            
        # Group albums by artist
        artist_albums = {}
        for album in albums:
            artist_id = album['artist_id'] if 'artist_id' in album else None
            artist_name = album['artist_name'] if 'artist_name' in album else 'Unknown Artist'
            
            if artist_id is None:
                # If artist_id is None, use the artist name as a key
                artist_key = f"artist_{artist_name}"
            else:
                artist_key = artist_id
                
            if artist_key not in artist_albums:
                artist_albums[artist_key] = {
                    'name': artist_name,
                    'id': artist_id,  # This might be None
                    'albums': []
                }
            
            artist_albums[artist_key]['albums'].append(album)
        
        # Add artists and their albums
        for artist_key, data in artist_albums.items():
            # Check if this artist is already in the tree
            artist_item = None
            for i in range(self.parent.results_tree_widget.topLevelItemCount()):
                item = self.parent.results_tree_widget.topLevelItem(i)
                if item.text(0) == data['name']:
                    artist_item = item
                    break
            
            # If artist isn't in the tree yet, add it
            if artist_item is None:
                artist_item = QTreeWidgetItem(self.parent.results_tree_widget)
                artist_item.setText(0, data['name'])
                
                # Store artist ID in the item if available
                if data['id'] is not None:
                    artist_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'artist', 'id': data['id']})
            
            # Add album items, checking for duplicates
            for album in data['albums']:
                # Check if this album is already a child of the artist
                album_exists = False
                for i in range(artist_item.childCount()):
                    item = artist_item.child(i)
                    if item.text(0) == album['name']:
                        album_exists = True
                        break
                
                # If album isn't a child of this artist yet, add it
                if not album_exists:
                    album_item = QTreeWidgetItem(artist_item)
                    album_item.setText(0, album['name'])
                    
                    # Use indexing for sqlite3.Row objects
                    if 'year' in album and album['year']:
                        album_item.setText(1, str(album['year']))
                    else:
                        album_item.setText(1, "")
                        
                    if 'genre' in album and album['genre']:
                        album_item.setText(2, album['genre'])
                    else:
                        album_item.setText(2, "")
                    
                    # Store album ID in the item
                    album_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'album', 'id': album['id']})
                    
                    # Get songs for this album
                    if 'id' in album and album['id'] is not None:
                        songs = self.parent.db_manager.get_album_songs(album['id'])
                        
                        # Add song items
                        for song in songs:
                            song_item = QTreeWidgetItem(album_item)
                            
                            # Format the song title with track number if available
                            title = song['title'] if 'title' in song else 'Unknown Title'
                            if 'track_number' in song and song['track_number']:
                                song_item.setText(0, f"{song['track_number']}. {title}")
                            else:
                                song_item.setText(0, title)
                            
                            # Format duration
                            duration_str = ""
                            if 'duration' in song and song['duration']:
                                minutes = int(song['duration']) // 60
                                seconds = int(song['duration']) % 60
                                duration_str = f"{minutes}:{seconds:02d}"
                            
                            song_item.setText(1, duration_str)
                            
                            if 'genre' in song and song['genre']:
                                song_item.setText(2, song['genre'])
                            else:
                                song_item.setText(2, "")
                            
                            # Store song ID in the item
                            song_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'song', 'id': song['id']})
    
    def _add_artists_to_tree(self, artists):
        """Add artists to the tree widget."""
        if not artists:
            return
            
        for artist in artists:
            # Check if this artist is already in the tree
            artist_exists = False
            for i in range(self.parent.results_tree_widget.topLevelItemCount()):
                item = self.parent.results_tree_widget.topLevelItem(i)
                if item.text(0) == artist['name']:
                    artist_exists = True
                    artist_item = item
                    break
            
            # If artist isn't in the tree yet, add it
            if not artist_exists:
                artist_item = QTreeWidgetItem(self.parent.results_tree_widget)
                artist_item.setText(0, artist['name'])
                
                # Use indexing for sqlite3.Row objects instead of .get()
                if 'formed_year' in artist and artist['formed_year']:
                    artist_item.setText(1, str(artist['formed_year']))
                else:
                    artist_item.setText(1, "")
                    
                if 'origin' in artist and artist['origin']:
                    artist_item.setText(2, artist['origin'])
                else:
                    artist_item.setText(2, "")
                
                # Store artist ID in the item
                artist_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'artist', 'id': artist['id']})
            
            # Get albums for this artist
            albums = self.parent.db_manager.get_artist_albums(artist['id'])
            
            # Add album items
            for album in albums:
                # Check if this album is already a child of the artist
                album_exists = False
                for i in range(artist_item.childCount()):
                    item = artist_item.child(i)
                    if item.text(0) == album['name']:
                        album_exists = True
                        album_item = item
                        break
                
                # If album isn't a child of this artist yet, add it
                if not album_exists:
                    album_item = QTreeWidgetItem(artist_item)
                    album_item.setText(0, album['name'])
                    
                    # Use indexing for sqlite3.Row objects instead of .get()
                    if 'year' in album and album['year']:
                        album_item.setText(1, str(album['year']))
                    else:
                        album_item.setText(1, "")
                        
                    if 'genre' in album and album['genre']:
                        album_item.setText(2, album['genre'])
                    else:
                        album_item.setText(2, "")
                    
                    # Store album ID in the item
                    album_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'album', 'id': album['id']})
                
                # Get songs for this album
                songs = self.parent.db_manager.get_album_songs(album['id'])
                
                # Add song items
                for song in songs:
                    # Create a unique identifier for the song (title + track number)
                    track_number = song['track_number'] if 'track_number' in song else ''
                    title = song['title'] if 'title' in song else 'Unknown Title'
                    song_id = f"{track_number}_{title}"
                    
                    # Check if this song is already a child of the album
                    song_exists = False
                    for i in range(album_item.childCount()):
                        item = album_item.child(i)
                        item_text = item.text(0)
                        if '.' in item_text:
                            parts = item_text.split('.')
                            item_id = f"{parts[0].strip()}_{parts[1].strip()}"
                        else:
                            item_id = f"_{item_text}"
                        if item_id == song_id:
                            song_exists = True
                            break
                    
                    # If song isn't a child of this album yet, add it
                    if not song_exists:
                        song_item = QTreeWidgetItem(album_item)
                        
                        # Format the song title with track number if available
                        if 'track_number' in song and song['track_number']:
                            song_item.setText(0, f"{song['track_number']}. {title}")
                        else:
                            song_item.setText(0, title)
                        
                        # Format duration (convert seconds to mm:ss)
                        duration_str = ""
                        if 'duration' in song and song['duration']:
                            minutes = int(song['duration']) // 60
                            seconds = int(song['duration']) % 60
                            duration_str = f"{minutes}:{seconds:02d}"
                        
                        song_item.setText(1, duration_str)
                        
                        if 'bitrate' in song and song['bitrate']:
                            song_item.setText(2, f"{song['bitrate']}kbps")
                        else:
                            song_item.setText(2, "")
                        
                        # Store song ID in the item
                        song_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'song', 'id': song['id']})


    def _add_songs_to_tree(self, songs):
        """Add songs to the tree widget."""
        if not songs:
            return
            
        # Group songs by artist and album
        artist_albums = {}
        for song in songs:
            # Handle case where artist_id might be missing
            artist_id = song['artist_id'] if 'artist_id' in song else None
            artist_name = song['artist'] if 'artist' in song else 'Unknown Artist'
            
            if artist_id is None:
                # If artist_id is None, use the artist name as a key
                artist_key = f"artist_{artist_name}"
            else:
                artist_key = artist_id
                
            if artist_key not in artist_albums:
                artist_albums[artist_key] = {
                    'name': artist_name,
                    'id': artist_id,  # This might be None
                    'albums': {}
                }
            
            # Handle case where album_id might be missing
            album_id = song['album_id'] if 'album_id' in song else None
            album_name = song['album'] if 'album' in song else 'Unknown Album'
            
            if album_id is None:
                # If album_id is None, use the album name as a key
                album_key = f"album_{album_name}"
            else:
                album_key = album_id
                
            if album_key not in artist_albums[artist_key]['albums']:
                artist_albums[artist_key]['albums'][album_key] = {
                    'name': album_name,
                    'id': album_id,  # This might be None
                    'songs': []
                }
            
            artist_albums[artist_key]['albums'][album_key]['songs'].append(song)
        
        # Add artists, albums, and songs
        for artist_key, artist_data in artist_albums.items():
            # Check if this artist is already in the tree
            artist_item = None
            for i in range(self.parent.results_tree_widget.topLevelItemCount()):
                item = self.parent.results_tree_widget.topLevelItem(i)
                if item.text(0) == artist_data['name']:
                    artist_item = item
                    break
            
            # If artist isn't in the tree yet, add it
            if artist_item is None:
                artist_item = QTreeWidgetItem(self.parent.results_tree_widget)
                artist_item.setText(0, artist_data['name'])
                
                # Store artist ID in the item if available
                if artist_data['id'] is not None:
                    artist_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'artist', 'id': artist_data['id']})
            
            # Add album items, checking for duplicates
            for album_key, album_data in artist_data['albums'].items():
                # Check if this album is already a child of the artist
                album_item = None
                for i in range(artist_item.childCount()):
                    item = artist_item.child(i)
                    if item.text(0) == album_data['name']:
                        album_item = item
                        break
                
                # If album isn't a child of this artist yet, add it
                if album_item is None:
                    album_item = QTreeWidgetItem(artist_item)
                    album_item.setText(0, album_data['name'])
                    
                    # Store album ID in the item if available
                    if album_data['id'] is not None:
                        album_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'album', 'id': album_data['id']})
                
                # Add song items, checking for duplicates
                for song in album_data['songs']:
                    # Create a unique identifier for the song (title + track number)
                    track_number = song['track_number'] if 'track_number' in song else ''
                    title = song['title'] if 'title' in song else 'Unknown Title'
                    song_id = f"{track_number}_{title}"
                    
                    # Check if this song is already a child of the album
                    song_exists = False
                    for i in range(album_item.childCount()):
                        item = album_item.child(i)
                        item_text = item.text(0)
                        if '.' in item_text:
                            parts = item_text.split('.')
                            item_id = f"{parts[0].strip()}_{parts[1].strip()}"
                        else:
                            item_id = f"_{item_text}"
                        if item_id == song_id:
                            song_exists = True
                            break
                    
                    # If song isn't a child of this album yet, add it
                    if not song_exists:
                        song_item = QTreeWidgetItem(album_item)
                        
                        # Format the song title with track number if available
                        if 'track_number' in song and song['track_number']:
                            song_item.setText(0, f"{song['track_number']}. {title}")
                        else:
                            song_item.setText(0, title)
                        
                        # Set date and genre
                        date_str = song['date'] if 'date' in song else ""
                        genre_str = song['genre'] if 'genre' in song else ""
                        
                        song_item.setText(1, date_str)
                        song_item.setText(2, genre_str)
                        
                        # Store song ID in the item
                        song_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'song', 'id': song['id']})