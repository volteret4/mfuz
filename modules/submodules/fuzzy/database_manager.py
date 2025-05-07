import sqlite3
from pathlib import Path

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
            query_pattern = f"%{query}%"
            
            if only_local:
                # Consulta para artistas con al menos un álbum local
                sql = """
                    SELECT DISTINCT artists.id, artists.name, artists.formed_year, artists.origin
                    FROM artists
                    INNER JOIN albums ON artists.id = albums.artist_id
                    WHERE artists.name LIKE ? AND albums.origen = 'local'
                    ORDER BY artists.name
                """
                print("SQL (artistas con álbumes locales):", sql)
                cursor.execute(sql, (query_pattern,))
            else:
                # Consulta para todos los artistas
                sql = """
                    SELECT id, name, formed_year, origin
                    FROM artists
                    WHERE name LIKE ?
                    ORDER BY name
                """
                print("SQL (todos los artistas):", sql)
                cursor.execute(sql, (query_pattern,))
            
            # Convert rows to dictionaries
            results = [self._row_to_dict(row) for row in cursor.fetchall()]
            print(f"Encontrados {len(results)} artistas")
            return results
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
            query_pattern = f"%{query}%"
            
            if only_local:
                # Consulta explícita para álbumes locales
                sql = """
                    SELECT albums.id, albums.name, albums.year, albums.genre, 
                        artists.name as artist_name, artists.id as artist_id
                    FROM albums
                    JOIN artists ON albums.artist_id = artists.id
                    WHERE albums.name LIKE ? AND albums.origen = 'local'
                    ORDER BY albums.name
                """
                print("SQL Albums (solo locales):", sql)
                cursor.execute(sql, (query_pattern,))
            else:
                # Consulta para todos los álbumes
                sql = """
                    SELECT albums.id, albums.name, albums.year, albums.genre, 
                        artists.name as artist_name, artists.id as artist_id
                    FROM albums
                    JOIN artists ON albums.artist_id = artists.id
                    WHERE albums.name LIKE ?
                    ORDER BY albums.name
                """
                print("SQL Albums (todos):", sql)
                cursor.execute(sql, (query_pattern,))
            
            # Convert rows to dictionaries
            results = [self._row_to_dict(row) for row in cursor.fetchall()]
            print(f"Encontrados {len(results)} álbumes")
            return results
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
            query_pattern = f"%{query}%"
            
            if only_local:
                # Consulta explícita para canciones locales
                sql = """
                    SELECT s.id, s.title, s.track_number, s.artist, s.album,
                        s.genre, s.date, s.album_art_path_denorm,
                        ar.id as artist_id, al.id as album_id
                    FROM songs s
                    LEFT JOIN artists ar ON s.artist = ar.name
                    LEFT JOIN albums al ON s.album = al.name AND al.artist_id = ar.id
                    WHERE s.title LIKE ? AND s.origen = 'local'
                    ORDER BY s.title
                """
                print("SQL Songs (solo locales):", sql)
                cursor.execute(sql, (query_pattern,))
            else:
                # Consulta para todas las canciones
                sql = """
                    SELECT s.id, s.title, s.track_number, s.artist, s.album,
                        s.genre, s.date, s.album_art_path_denorm,
                        ar.id as artist_id, al.id as album_id
                    FROM songs s
                    LEFT JOIN artists ar ON s.artist = ar.name
                    LEFT JOIN albums al ON s.album = al.name AND al.artist_id = ar.id
                    WHERE s.title LIKE ?
                    ORDER BY s.title
                """
                print("SQL Songs (todos):", sql)
                cursor.execute(sql, (query_pattern,))
            
            # Convert rows to dictionaries
            results = [self._row_to_dict(row) for row in cursor.fetchall()]
            print(f"Encontradas {len(results)} canciones")
            return results
        except sqlite3.Error as e:
            print(f"Error searching songs: {e}")
            return []
        finally:
            conn.close()

  

    def get_album_songs(self, album_id, only_local=False):
        """Get all songs in an album with optional local filtering."""
        conn = self._get_connection()
        if not conn:
            print(f"ERROR: No se pudo conectar a la base de datos para obtener canciones del álbum {album_id}")
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
                print(f"ERROR: No se encontró el álbum con ID {album_id}")
                return []
            
            print(f"Álbum encontrado: {album['name']}, artist_id: {album['artist_id']}")
            
            # Get the artist name
            cursor.execute("""
                SELECT name
                FROM artists
                WHERE id = ?
            """, (album['artist_id'],))
            artist = cursor.fetchone()
            artist_name = artist['name'] if artist else None
            
            if artist_name:
                print(f"Artista encontrado: {artist_name}")
            else:
                print(f"ADVERTENCIA: No se encontró el artista con ID {album['artist_id']}")
                
            # Now get songs for that album and artist
            sql = ""
            params = []
            
            if artist_name:
                if only_local:
                    sql = """
                        SELECT id, title, track_number, artist, duration, bitrate, genre, file_path, origen
                        FROM songs
                        WHERE album = ? AND artist = ? AND origen = 'local'
                        ORDER BY track_number, title
                    """
                    params = [album['name'], artist_name]
                    print(f"Buscando canciones locales para álbum '{album['name']}' del artista '{artist_name}'")
                else:
                    sql = """
                        SELECT id, title, track_number, artist, duration, bitrate, genre, file_path, origen
                        FROM songs
                        WHERE album = ? AND artist = ?
                        ORDER BY track_number, title
                    """
                    params = [album['name'], artist_name]
                    print(f"Buscando todas las canciones para álbum '{album['name']}' del artista '{artist_name}'")
            else:
                if only_local:
                    sql = """
                        SELECT id, title, track_number, artist, duration, bitrate, genre, file_path, origen
                        FROM songs
                        WHERE album = ? AND origen = 'local'
                        ORDER BY track_number, title
                    """
                    params = [album['name']]
                    print(f"Buscando canciones locales para álbum '{album['name']}' sin artista específico")
                else:
                    sql = """
                        SELECT id, title, track_number, artist, duration, bitrate, genre, file_path, origen
                        FROM songs
                        WHERE album = ?
                        ORDER BY track_number, title
                    """
                    params = [album['name']]
                    print(f"Buscando todas las canciones para álbum '{album['name']}' sin artista específico")
            
            print(f"Ejecutando SQL: {sql}")
            print(f"Con parámetros: {params}")
            
            cursor.execute(sql, params)
            songs = cursor.fetchall()
            
            if songs:
                for song in songs:
                    # Usar acceso de diccionario normal para sqlite3.Row
                    origen = song['origen'] if 'origen' in song.keys() else 'desconocido'
                    print(f"Canción encontrada: {song['title']}, origen: {origen}")
            
            print(f"Encontradas {len(songs)} canciones para el álbum {album['name']}")
            
            # Convert rows to dictionaries
            result = [self._row_to_dict(row) for row in songs]
            return result
        except sqlite3.Error as e:
            print(f"Error en get_album_songs para álbum ID {album_id}: {e}")
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
    
    def get_artist_albums(self, artist_id, only_local=False):
        """Get all albums for an artist with optional local filtering."""
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            if only_local:
                cursor.execute("""
                    SELECT id, name, year, genre, total_tracks, origen, folder_path
                    FROM albums
                    WHERE artist_id = ? AND origen = 'local'
                    ORDER BY year DESC, name
                """, (artist_id,))
            else:
                cursor.execute("""
                    SELECT id, name, year, genre, total_tracks, origen, folder_path
                    FROM albums
                    WHERE artist_id = ?
                    ORDER BY year DESC, name
                """, (artist_id,))
                    
            # Convert rows to dictionaries
            albums = [self._row_to_dict(row) for row in cursor.fetchall()]
            
            # Verificar si cada álbum tiene folder_path
            for album in albums:
                if 'folder_path' not in album or not album['folder_path']:
                    print(f"ADVERTENCIA: El álbum {album.get('name', 'Unknown')} (ID: {album.get('id')}) no tiene folder_path")
                    
                    # Intentar obtener folder_path directamente
                    try:
                        cursor.execute("SELECT folder_path FROM albums WHERE id = ?", (album['id'],))
                        folder_path_result = cursor.fetchone()
                        if folder_path_result and folder_path_result['folder_path']:
                            album['folder_path'] = folder_path_result['folder_path']
                            print(f"Obtenido folder_path directamente: {album['folder_path']}")
                    except Exception as e:
                        print(f"Error al obtener folder_path: {e}")
            
            return albums
        except Exception as e:
            print(f"Error getting artist albums: {e}")
            import traceback
            traceback.print_exc()
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
            # Modificar la consulta para obtener las letras correctamente
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
                # Asegurarse de que result sea un diccionario con los campos accesibles
                song_dict = self._row_to_dict(result)
                
                # Verificar si file_path existe y tiene valor
                if 'file_path' in song_dict and song_dict['file_path']:
                    print(f"Song file_path: {song_dict['file_path']}")
                else:
                    print(f"ADVERTENCIA: La canción con ID {song_id} no tiene file_path o file_path está vacío")
                    
                    # Intentar obtener file_path directamente si no está en el resultado
                    cursor.execute("SELECT file_path FROM songs WHERE id = ?", (song_id,))
                    file_path_result = cursor.fetchone()
                    if file_path_result and file_path_result['file_path']:
                        song_dict['file_path'] = file_path_result['file_path']
                        print(f"Obtenido file_path directamente: {song_dict['file_path']}")
                
                return song_dict
            else:
                print(f"No song found with id {song_id}")
                return None
        except Exception as e:
            print(f"Error getting song details: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            conn.close()


    def _row_to_dict(self, row):
        """Convert a sqlite3.Row to a regular dictionary."""
        if row is None:
            return None
        return {key: row[key] for key in row.keys()}