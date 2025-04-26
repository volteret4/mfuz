import sqlite3
import os
import traceback
from typing import Optional, Dict, List, Tuple, Any, Union

class MusicDatabase:
    """
    Handles all database operations for the music browser.
    Centralizes database access and query execution.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize with database path.
        
        Args:
            db_path (str): Path to SQLite database file
        """
        self.db_path = db_path
        
    def _get_connection(self):
        """Get a database connection with optimized settings."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
            
        conn = sqlite3.connect(self.db_path)
        # Enable memory for temp storage to improve performance
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn
        
    def get_artist_info(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """
        Get artist information from the database with improved error handling.
        
        Args:
            artist_name (str): Artist name to search for
            
        Returns:
            Optional[Dict[str, Any]]: Artist information or None if not found
        """
        if not artist_name:
            print("[DEBUG] Nombre de artista vacío en get_artist_info")
            return None
            
        try:
            print(f"[DEBUG] Buscando información para artista: {artist_name}")
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT id, name, bio, tags, similar_artists, last_updated, origin,
                    formed_year, total_albums, spotify_url, youtube_url,
                    musicbrainz_url, discogs_url, rateyourmusic_url,
                    links_updated, wikipedia_url, wikipedia_content,
                    wikipedia_updated, mbid, bandcamp_url, member_of, aliases, lastfm_url
                FROM artists
                WHERE LOWER(name) = LOWER(?)
            """
            
            cursor.execute(query, (artist_name,))
            result = cursor.fetchone()
            
            if not result:
                print(f"[DEBUG] No se encontró información para el artista: {artist_name}")
                
                # Intento alternativo: búsqueda por LIKE
                alt_query = """
                    SELECT id, name, bio, tags, similar_artists, last_updated, origin,
                        formed_year, total_albums, spotify_url, youtube_url,
                        musicbrainz_url, discogs_url, rateyourmusic_url,
                        links_updated, wikipedia_url, wikipedia_content,
                        wikipedia_updated, mbid, bandcamp_url, member_of, aliases, lastfm_url
                    FROM artists
                    WHERE LOWER(name) LIKE LOWER(?)
                    LIMIT 1
                """
                cursor.execute(alt_query, (f"%{artist_name}%",))
                result = cursor.fetchone()
                
                if not result:
                    print(f"[DEBUG] Tampoco se encontró con búsqueda aproximada: {artist_name}")
                    conn.close()
                    return None
                else:
                    print(f"[DEBUG] Se encontró artista con búsqueda aproximada: {result[1]}")
            else:
                print(f"[DEBUG] Artista encontrado: {result[1]}")
                
            # Create dictionary with column names
            columns = [
                'id', 'name', 'bio', 'tags', 'similar_artists', 'last_updated',
                'origin', 'formed_year', 'total_albums', 'spotify_url',
                'youtube_url', 'musicbrainz_url', 'discogs_url', 'rateyourmusic_url',
                'links_updated', 'wikipedia_url', 'wikipedia_content',
                'wikipedia_updated', 'mbid', 'bandcamp_url', 'member_of', 'aliases', 'lastfm_url'
            ]
            
            artist_info = {columns[i]: result[i] for i in range(len(columns)) if i < len(result)}
            
            # Debug: verificar campos clave
            for key in ['id', 'name', 'bio', 'wikipedia_content', 'spotify_url', 'lastfm_url']:
                if key in artist_info:
                    has_value = bool(artist_info[key])
                    value_preview = str(artist_info[key])[:30] + "..." if has_value and isinstance(artist_info[key], str) else str(artist_info[key])
                    print(f"[DEBUG] Campo {key}: {has_value} - {value_preview}")
            
            conn.close()
            return artist_info
            
        except Exception as e:
            import traceback
            print(f"[DEBUG] Error getting artist info: {e}")
            traceback.print_exc()
            return None

    def get_artist_networks(self, artist_id: int) -> Dict[str, str]:
        """
        Get all social media and external links for an artist with improved error handling.
        
        Args:
            artist_id (int): ID of the artist
            
        Returns:
            Dict[str, str]: Dictionary of network links
        """
        if not artist_id:
            print("[DEBUG] ID de artista vacío en get_artist_networks")
            return {}
            
        try:
            print(f"[DEBUG] Obteniendo redes sociales para artist_id: {artist_id}")
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Verificar si la tabla existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artists_networks'")
            if not cursor.fetchone():
                print("[DEBUG] La tabla artists_networks no existe en la base de datos")
                conn.close()
                return {}
            
            # Get column names first (excluding id, artist_id, enlaces, last_updated)
            cursor.execute("PRAGMA table_info(artists_networks)")
            all_columns = [row[1] for row in cursor.fetchall()]
            link_columns = [col for col in all_columns if col not in ('id', 'artist_id', 'enlaces', 'last_updated')]
            
            print(f"[DEBUG] Columnas de enlaces encontradas: {link_columns}")
            
            if not link_columns:
                print("[DEBUG] No se encontraron columnas de enlaces en la tabla")
                conn.close()
                return {}
            
            # Build dynamic query
            columns_str = ', '.join(link_columns)
            query = f"SELECT {columns_str} FROM artists_networks WHERE artist_id = ?"
            
            cursor.execute(query, (artist_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if not result:
                print(f"[DEBUG] No se encontraron redes sociales para artist_id: {artist_id}")
                return {}
                
            # Create dictionary of links
            links = {}
            for i, col in enumerate(link_columns):
                if result[i]:  # If the link exists
                    links[col] = result[i]
                    
            print(f"[DEBUG] Enlaces de redes sociales encontrados: {links}")
            return links
            
        except Exception as e:
            import traceback
            print(f"[DEBUG] Error getting artist networks: {e}")
            traceback.print_exc()
            return {}
            
    def get_album_info(self, album_name: str, artist_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get album information from the database.
        
        Args:
            album_name (str): Album name to search for
            artist_name (Optional[str]): Artist name for more precise search
            
        Returns:
            Optional[Dict[str, Any]]: Album information or None if not found
        """
        if not album_name:
            return None
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if artist_name:
                # Get artist ID first
                artist_query = "SELECT id FROM artists WHERE LOWER(name) = LOWER(?)"
                cursor.execute(artist_query, (artist_name,))
                artist_result = cursor.fetchone()
                
                if artist_result:
                    artist_id = artist_result[0]
                    
                    # Get album with artist ID
                    query = """
                        SELECT id, artist_id, name, year, label, genre, total_tracks,
                            album_art_path, last_updated, spotify_url, spotify_id,
                            youtube_url, musicbrainz_url, discogs_url, rateyourmusic_url,
                            links_updated, wikipedia_url, wikipedia_content,
                            wikipedia_updated, mbid, folder_path, bitrate_range,
                            bandcamp_url, producers, engineers, mastering_engineers,
                            credits, lastfm_url
                        FROM albums
                        WHERE LOWER(name) = LOWER(?) AND artist_id = ?
                    """
                    cursor.execute(query, (album_name, artist_id))
                else:
                    # Artist not found, try just with album name
                    query = """
                        SELECT id, artist_id, name, year, label, genre, total_tracks,
                            album_art_path, last_updated, spotify_url, spotify_id,
                            youtube_url, musicbrainz_url, discogs_url, rateyourmusic_url,
                            links_updated, wikipedia_url, wikipedia_content,
                            wikipedia_updated, mbid, folder_path, bitrate_range,
                            bandcamp_url, producers, engineers, mastering_engineers,
                            credits, lastfm_url
                        FROM albums
                        WHERE LOWER(name) = LOWER(?)
                    """
                    cursor.execute(query, (album_name,))
            else:
                # Just search by album name
                query = """
                    SELECT id, artist_id, name, year, label, genre, total_tracks,
                        album_art_path, last_updated, spotify_url, spotify_id,
                        youtube_url, musicbrainz_url, discogs_url, rateyourmusic_url,
                        links_updated, wikipedia_url, wikipedia_content,
                        wikipedia_updated, mbid, folder_path, bitrate_range,
                        bandcamp_url, producers, engineers, mastering_engineers,
                        credits, lastfm_url
                    FROM albums
                    WHERE LOWER(name) = LOWER(?)
                """
                cursor.execute(query, (album_name,))
                
            result = cursor.fetchone()
            
            conn.close()
            
            if not result:
                return None
                
            # Create dictionary with column names
            columns = [
                'id', 'artist_id', 'name', 'year', 'label', 'genre', 'total_tracks',
                'album_art_path', 'last_updated', 'spotify_url', 'spotify_id',
                'youtube_url', 'musicbrainz_url', 'discogs_url', 'rateyourmusic_url',
                'links_updated', 'wikipedia_url', 'wikipedia_content',
                'wikipedia_updated', 'mbid', 'folder_path', 'bitrate_range',
                'bandcamp_url', 'producers', 'engineers', 'mastering_engineers',
                'credits', 'lastfm_url'
            ]
            
            return {columns[i]: result[i] for i in range(len(columns)) if i < len(result)}
            
        except Exception as e:
            print(f"Error getting album info: {e}")
            traceback.print_exc()
            return None
    
    def get_lyrics(self, track_id: int) -> Optional[Tuple[str, str]]:
        """
        Get lyrics for a track.
        
        Args:
            track_id (int): ID of the track
            
        Returns:
            Optional[Tuple[str, str]]: Tuple of (lyrics, source) or None if not found
        """
        if not track_id:
            return None
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get lyrics
            cursor.execute("SELECT lyrics, source FROM lyrics WHERE track_id = ?", (track_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result and result[0]:
                return (result[0], result[1] if result[1] else "Unknown")
                
            return None
            
        except Exception as e:
            print(f"Error getting lyrics: {e}")
            return None
    
   
    
    def get_feeds_data(self, entity_type: str, entity_id: int) -> List[Dict[str, Any]]:
        """
        Get feeds data for an entity.
        
        Args:
            entity_type (str): Type of entity ('artist', 'album', 'song')
            entity_id (int): ID of the entity
            
        Returns:
            List[Dict[str, Any]]: List of feed dictionaries
        """
        if not entity_id:
            return []
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT id, feed_name, post_title, post_url, post_date, content, added_date
                FROM feeds
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY post_date DESC
            """
            
            cursor.execute(query, (entity_type, entity_id))
            rows = cursor.fetchall()
            
            conn.close()
            
            feeds = []
            for row in rows:
                feed = {
                    'id': row[0],
                    'feed_name': row[1],
                    'post_title': row[2],
                    'post_url': row[3],
                    'post_date': row[4],
                    'content': row[5],
                    'added_date': row[6]
                }
                feeds.append(feed)
                
            return feeds
            
        except Exception as e:
            print(f"Error fetching feeds data: {e}")
            return []
    
    def get_spotify_url(self, song_id: int) -> Optional[str]:
        """
        Get Spotify URL for a song.
        
        Args:
            song_id (int): ID of the song
            
        Returns:
            Optional[str]: Spotify URL or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT spotify_url FROM song_links WHERE song_id = ?", (song_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] if result and result[0] else None
            
        except Exception as e:
            print(f"Error getting Spotify URL: {e}")
            return None
    
    def search_music(self, conditions: List[str], params: List[Any], limit: int = 1000) -> List[Tuple]:
        """
        Search for music in the database.
        
        Args:
            conditions (List[str]): SQL WHERE conditions
            params (List[Any]): Parameters for the conditions
            limit (int): Maximum number of results
            
        Returns:
            List[Tuple]: List of result rows
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build the base query
            sql = """
                SELECT DISTINCT
                    s.id,
                    s.file_path,
                    s.title,
                    s.artist,
                    s.album_artist,
                    s.album,
                    s.date,
                    s.genre,
                    s.label,
                    s.mbid,
                    s.bitrate,
                    s.bit_depth,
                    s.sample_rate,
                    s.last_modified,
                    s.track_number
                FROM songs s
                LEFT JOIN artists art ON s.artist = art.name
                LEFT JOIN albums alb ON s.album = alb.name
            """
            
            # Add conditions if any
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
                
            # Add ordering
            sql += " ORDER BY s.artist, s.album, CAST(s.track_number AS INTEGER)"
            
            # Add limit
            sql += f" LIMIT {limit}"
            
            # Execute query
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            conn.close()
            
            return results
            
        except Exception as e:
            print(f"Error searching music: {e}")
            traceback.print_exc()
            return []
    
    def get_entity_id(self, entity_type: str, name: str, artist_name: Optional[str] = None) -> Optional[int]:
        """
        Get entity ID by name.
        
        Args:
            entity_type (str): Type of entity ('artist', 'album', 'song')
            name (str): Name of the entity
            artist_name (Optional[str]): Artist name for albums
            
        Returns:
            Optional[int]: Entity ID or None if not found
        """
        if not name:
            return None
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if entity_type == 'artist':
                cursor.execute("SELECT id FROM artists WHERE LOWER(name) = LOWER(?)", (name,))
            elif entity_type == 'album':
                if artist_name:
                    # Get artist ID first
                    cursor.execute("SELECT id FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name,))
                    artist_result = cursor.fetchone()
                    
                    if artist_result:
                        artist_id = artist_result[0]
                        cursor.execute("SELECT id FROM albums WHERE LOWER(name) = LOWER(?) AND artist_id = ?", 
                                    (name, artist_id))
                    else:
                        cursor.execute("SELECT id FROM albums WHERE LOWER(name) = LOWER(?)", (name,))
                else:
                    cursor.execute("SELECT id FROM albums WHERE LOWER(name) = LOWER(?)", (name,))
            
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] if result else None
            
        except Exception as e:
            print(f"Error getting entity ID: {e}")
            return None