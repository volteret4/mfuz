import sqlite3
import os


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
    """Process database links into results with proper hierarchy, including file paths."""
    results = []
    
    # Process artists with their albums and tracks
    for artist_name, artist_data in db_links.get('artists', {}).items():
        # Try to fetch paths for this artist
        paths_data = fetch_artist_song_paths(self, artist_name)
        
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
