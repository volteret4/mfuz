import sqlite3

class DatabaseManager:
    """Manages database interactions for the music browser."""
    
    def __init__(self, db_path):
        self.db_path = db_path
    
    def _get_connection(self):
        """Get a database connection."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return None
    
    def search_artists(self, query, only_local=False):
        """Search artists matching the query."""
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            query = f"%{query}%"
            
            sql = """
                SELECT id, name, formed_year, origin
                FROM artists
                WHERE name LIKE ?
            """
            
            params = [query]
            
            if only_local:
                sql += " AND origen = 'local'"
                
            sql += " ORDER BY name"
            
            cursor.execute(sql, params)
            
            # Convert rows to dictionaries
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error searching artists: {e}")
            return []
        finally:
            conn.close()

    def search_albums(self, query, only_local=False):
        """Search albums matching the query."""
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            query = f"%{query}%"
            
            sql = """
                SELECT albums.id, albums.name, albums.year, albums.genre, 
                    artists.name as artist_name, artists.id as artist_id
                FROM albums
                JOIN artists ON albums.artist_id = artists.id
                WHERE albums.name LIKE ?
            """
            
            params = [query]
            
            if only_local:
                sql += " AND albums.origen = 'local'"
                
            sql += " ORDER BY albums.name"
            
            cursor.execute(sql, params)
            
            # Convert rows to dictionaries
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error searching albums: {e}")
            return []
        finally:
            conn.close()

    def search_songs(self, query, only_local=False):
        """Search songs matching the query."""
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            query = f"%{query}%"
            
            sql = """
                SELECT s.id, s.title, s.track_number, s.artist, s.album,
                    s.genre, s.date, s.album_art_path_denorm,
                    ar.id as artist_id, al.id as album_id
                FROM songs s
                LEFT JOIN artists ar ON s.artist = ar.name
                LEFT JOIN albums al ON s.album = al.name AND al.artist_id = ar.id
                WHERE s.title LIKE ?
            """
            
            params = [query]
            
            if only_local:
                sql += " AND s.origen = 'local'"
                
            sql += " ORDER BY s.title"
            
            cursor.execute(sql, params)
            
            # Convert rows to dictionaries
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error searching songs: {e}")
            return []
        finally:
            conn.close()
    
  

    def get_album_songs(self, album_id):
        """Get all songs in an album."""
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            # Get the album details
            cursor.execute("""
                SELECT name, artist_id
                FROM albums
                WHERE id = ?
            """, (album_id,))
            album = cursor.fetchone()
            if not album:
                return []
            
            # Get the artist name
            cursor.execute("""
                SELECT name
                FROM artists
                WHERE id = ?
            """, (album['artist_id'],))
            artist = cursor.fetchone()
            artist_name = artist['name'] if artist else None
                
            # Now get songs for that album and artist
            if artist_name:
                cursor.execute("""
                    SELECT id, title, track_number, artist, duration, bitrate, genre, file_path
                    FROM songs
                    WHERE album = ? AND artist = ?
                    ORDER BY track_number, title
                """, (album['name'], artist_name))
            else:
                cursor.execute("""
                    SELECT id, title, track_number, artist, duration, bitrate, genre, file_path
                    FROM songs
                    WHERE album = ?
                    ORDER BY track_number, title
                """, (album['name'],))
            
            # Convert rows to dictionaries
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting album songs: {e}")
            return []
        finally:
            conn.close()
    
    def get_artist_details(self, artist_id):
        """Get details for an artist."""
        conn = self._get_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT artists.*, artists_networks.*
                FROM artists
                LEFT JOIN artists_networks ON artists.id = artists_networks.artist_id
                WHERE artists.id = ?
            """, (artist_id,))
            row = cursor.fetchone()  # Get a single row instead of fetchall()
            if row:
                return self._row_to_dict(row)  # Convert to dictionary
            return None
        except sqlite3.Error as e:
            print(f"Error getting artist details: {e}")
            return None
        finally:
            conn.close()

    def get_album_details(self, album_id):
        """Get details for an album."""
        conn = self._get_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM albums
                WHERE id = ?
            """, (album_id,))
            row = cursor.fetchone()  # Get a single row
            if row:
                return self._row_to_dict(row)  # Convert to dictionary
            return None
        except sqlite3.Error as e:
            print(f"Error getting album details: {e}")
            return None
        finally:
            conn.close()
    
    def get_artist_albums(self, artist_id):
        """Get all albums for an artist."""
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, year, genre, total_tracks
                FROM albums
                WHERE artist_id = ?
                ORDER BY year DESC, name
            """, (artist_id,))
            # Convert rows to dictionaries
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting artist albums: {e}")
            return []
        finally:
            conn.close()
    

    
 
    def get_song_details(self, song_id):
        """Get all details for a song."""
        conn = self._get_connection()
        if not conn:
            print(f"Error: Could not get database connection")
            return None
            
        try:
            cursor = conn.cursor()
            query = """
                SELECT s.*, l.lyrics
                FROM songs s
                LEFT JOIN lyrics l ON s.lyrics_id = l.id
                WHERE s.id = ?
            """
            print(f"Executing query: {query} with song_id={song_id}")
            cursor.execute(query, (song_id,))
            result = cursor.fetchone()
            
            if result:
                print(f"Found song with id {song_id}, keys: {result.keys()}")
            else:
                print(f"No song found with id {song_id}")
                
            return result
        except sqlite3.Error as e:
            print(f"Error getting song details: {e}")
            return None
        finally:
            conn.close()


    def _row_to_dict(self, row):
        """Convert a sqlite3.Row to a regular dictionary."""
        if row is None:
            return None
        return {key: row[key] for key in row.keys()}