import os
import json
import time
import sqlite3
import datetime
from pathlib import Path
import threading
from PyQt6.QtWidgets import QApplication

from modules.submodules.url_playlist.ui_helpers import get_service_priority

def log(message):
    """Registra un mensaje en el TextEdit y en la consola."""
    print(f"[UrlPlayer-lastfm_db] {message}")  # Using print instead of calling log again


def get_lastfm_cache_path(lastfm_username=None):
    """Get the path to the Last.fm scrobbles cache file"""
    try:
        # Try to import PROJECT_ROOT from base module
        from base_module import PROJECT_ROOT
    except ImportError:
        # Use a fallback if not available
        PROJECT_ROOT = os.path.abspath(Path(os.path.dirname(__file__), "..", "..", ".."))
    
    cache_dir = Path(PROJECT_ROOT, ".content", "cache", "url_playlist")
    os.makedirs(cache_dir, exist_ok=True)
    
    if lastfm_username:
        return Path(cache_dir, f"scrobbles_{lastfm_username}.json")
    else:
        return Path(cache_dir, "lastfm_scrobbles.json")

def create_scrobbles_table(conn, lastfm_username):
    """
    Create or modify the scrobbles tables to match the required schema.
    Respects existing columns and doesn't try to add columns that already exist.
    
    Args:
        conn: Database connection
        lastfm_username: Last.fm username
    """
    cursor = conn.cursor()
    
    # Check if songs table exists and its columns
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='songs'")
    songs_exists = cursor.fetchone() is not None
    
    if songs_exists:
        # Get existing columns
        cursor.execute("PRAGMA table_info(songs)")
        songs_columns = [row[1] for row in cursor.fetchall()]
        log(f"Existing songs table columns: {songs_columns}")
        
        # Add missing columns to songs table if needed
        if 'reproducciones' not in songs_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN reproducciones INTEGER DEFAULT 1")
            log("Added column reproducciones to songs table")
            
        if 'fecha_reproducciones' not in songs_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN fecha_reproducciones TEXT")
            log("Added column fecha_reproducciones to songs table")
            
        if 'scrobbles_ids' not in songs_columns:
            cursor.execute("ALTER TABLE songs ADD COLUMN scrobbles_ids TEXT")
            log("Added column scrobbles_ids to songs table")
    
    # User-specific table name for scrobbles
    user_table = f"scrobbles_{lastfm_username}"
    
    # Check if user table exists
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{user_table}'")
    user_table_exists = cursor.fetchone() is not None
    
    # Create user table with the correct schema if it doesn't exist
    if not user_table_exists:
        log(f"Creating {user_table} table with correct schema")
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {user_table} (
            id INTEGER PRIMARY KEY,
            artist_name TEXT NOT NULL,
            artist_mbid TEXT,
            name TEXT NOT NULL,
            track_name TEXT NOT NULL,
            album_name TEXT,
            album_mbid TEXT,
            timestamp INTEGER NOT NULL,
            fecha_scrobble TEXT NOT NULL,
            scrobble_date TEXT,
            lastfm_url TEXT,
            fecha_adicion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reproducciones INTEGER DEFAULT 1,
            fecha_reproducciones TEXT,
            youtube_url TEXT,
            spotify_url TEXT,
            bandcamp_url TEXT,
            soundcloud_url TEXT,
            song_id INTEGER,
            artist_id INTEGER,
            album_id INTEGER
        """)
        log(f"Created {user_table} table")
        
        # Create indexes for the new table
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{user_table}_artist ON {user_table}(artist_name)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{user_table}_name ON {user_table}(name)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{user_table}_timestamp ON {user_table}(timestamp)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{user_table}_artist_name ON {user_table}(artist_name, name)")
        cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{user_table}_unique ON {user_table}(artist_name, name, timestamp)")
    else:
        # Check existing columns for user table
        cursor.execute(f"PRAGMA table_info({user_table})")
        user_columns = [row[1] for row in cursor.fetchall()]
        log(f"Existing {user_table} columns: {user_columns}")
        
        # Add any missing required columns
        required_columns = {
            'artist_name': 'TEXT NOT NULL',
            'artist_mbid': 'TEXT',
            'name': 'TEXT NOT NULL',
            'track_name': 'TEXT',
            'album_name': 'TEXT',
            'album_mbid': 'TEXT',
            'timestamp': 'INTEGER NOT NULL',
            'fecha_scrobble': 'TEXT',
            'scrobble_date': 'TEXT',
            'lastfm_url': 'TEXT',
            'fecha_adicion': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'reproducciones': 'INTEGER DEFAULT 1',
            'fecha_reproducciones': 'TEXT',
            'youtube_url': 'TEXT',
            'spotify_url': 'TEXT',
            'bandcamp_url': 'TEXT',
            'soundcloud_url': 'TEXT',
            'song_id': 'INTEGER',
            'artist_id': 'INTEGER',
            'album_id': 'INTEGER'
        }
        
        # Add missing columns
        for col_name, col_type in required_columns.items():
            if col_name not in user_columns:
                try:
                    cursor.execute(f"ALTER TABLE {user_table} ADD COLUMN {col_name} {col_type}")
                    log(f"Added column {col_name} to {user_table} table")
                except Exception as e:
                    log(f"Error adding column {col_name} to {user_table}: {e}")
        
        # Make sure the unique index exists
        try:
            cursor.execute(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_{user_table}_unique 
            ON {user_table}(artist_name, name, timestamp)
            """)
        except Exception as e:
            log(f"Error creating unique index on {user_table}: {e}")
    
    # Check if song_links table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_links'")
    song_links_exists = cursor.fetchone() is not None
    
    # Create song_links table if it doesn't exist
    if not song_links_exists:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS song_links (
            id INTEGER PRIMARY KEY,
            song_id INTEGER,
            spotify_url TEXT,
            spotify_id TEXT,
            lastfm_url TEXT,
            links_updated TIMESTAMP,
            youtube_url TEXT,
            musicbrainz_url TEXT,
            musicbrainz_recording_id TEXT,
            bandcamp_url TEXT,
            soundcloud_url TEXT,
            boomkat_url TEXT
        )
        """)
        log("Created song_links table")
        
        # Create index for song_id
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)")
    else:
        # Ensure song_links has all necessary columns
        cursor.execute("PRAGMA table_info(song_links)")
        link_columns = [row[1] for row in cursor.fetchall()]
        
        # Check for required columns
        for col_name, col_type in {
            'spotify_url': 'TEXT', 
            'spotify_id': 'TEXT', 
            'lastfm_url': 'TEXT',
            'youtube_url': 'TEXT', 
            'musicbrainz_url': 'TEXT', 
            'bandcamp_url': 'TEXT',
            'soundcloud_url': 'TEXT',
            'boomkat_url': 'TEXT'
        }.items():
            if col_name not in link_columns:
                try:
                    cursor.execute(f"ALTER TABLE song_links ADD COLUMN {col_name} {col_type}")
                    log(f"Added column {col_name} to song_links table")
                except Exception as e:
                    log(f"Error adding column {col_name} to song_links: {e}")
    
    # User-specific LastFM config table
    config_table = f"lastfm_config_{lastfm_username}"
    
    # Check if user-specific config table exists
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{config_table}'")
    config_exists = cursor.fetchone() is not None
    
    # Create user-specific config table if needed
    if not config_exists:
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {config_table} (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            lastfm_username TEXT,
            last_timestamp INTEGER,
            last_updated TIMESTAMP
        )
        """)
        log(f"Created {config_table} table")
        
        # Initialize with default values
        cursor.execute(f"""
        INSERT INTO {config_table} (id, lastfm_username, last_timestamp, last_updated)
        VALUES (1, ?, 0, CURRENT_TIMESTAMP)
        """, (lastfm_username,))
    
    # Additionally, check for the old global config table and migrate if needed
    if lastfm_username== "paqueradejere":  # Primary username
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lastfm_config'")
        if cursor.fetchone():
            # Check if it has data and we don't already have data in the user table
            cursor.execute("SELECT last_timestamp FROM lastfm_config WHERE id = 1")
            global_result = cursor.fetchone()
            
            if global_result and global_result[0] > 0:
                # Check if user-specific table has data
                cursor.execute(f"SELECT last_timestamp FROM {config_table} WHERE id = 1")
                user_result = cursor.fetchone()
                
                if not user_result or user_result[0] == 0:
                    # Migrate data from global to user-specific
                    cursor.execute(f"""
                    UPDATE {config_table}
                    SET last_timestamp = ?, last_updated = (SELECT last_updated FROM lastfm_config WHERE id = 1)
                    WHERE id = 1
                    """, (global_result[0],))
                    log(f"Migrated timestamp {global_result[0]} from global config to {config_table}")
    
    # Commit changes
    conn.commit()
    log(f"Tables and indexes created or verified for user {lastfm_username}")

def process_scrobbles(self, scrobbles):
    """
    Process raw scrobbles from Last.fm, maintaining the original format.
    Handles both formats: API format and database/cache format.
    
    Args:
        self: The parent object with log method
        scrobbles: List of scrobbles from Last.fm API or database
        
    Returns:
        List of processed scrobbles
    """
    if not scrobbles:
        return []
    
    log("Processing scrobbles...")
    
    processed = []
    
    for scrobble in scrobbles:
        # Ensure we have the essential fields - handle both formats
        try:
            # Handle different formats for artist name
            if 'artist' in scrobble:
                if isinstance(scrobble['artist'], dict):
                    # API format
                    artist_name = scrobble['artist'].get('#text', '')
                else:
                    # Database format (already string)
                    artist_name = scrobble['artist']
            else:
                # Try artist_name field
                artist_name = scrobble.get('artist_name', '')
            
            # Handle different formats for track name
            if 'name' in scrobble:
                track_name = scrobble['name']
            else:
                track_name = scrobble.get('title', '')
            
            # Handle different formats for timestamp and date
            timestamp = scrobble.get('timestamp', 0)
            if 'date' in scrobble and isinstance(scrobble['date'], dict):
                fecha = scrobble['date'].get('#text', '')
                if 'uts' in scrobble['date'] and not timestamp:
                    timestamp = int(scrobble['date']['uts'])
            else:
                fecha = scrobble.get('fecha_scrobble', '')
            
            # Handle album info in different formats
            if 'album' in scrobble:
                if isinstance(scrobble['album'], dict):
                    # API format
                    album_name = scrobble['album'].get('#text', '')
                    album_mbid = scrobble['album'].get('mbid', '')
                else:
                    # Database format (already string)
                    album_name = scrobble['album']
                    album_mbid = scrobble.get('album_mbid', '')
            else:
                # Try album_name field
                album_name = scrobble.get('album_name', '')
                album_mbid = scrobble.get('album_mbid', '')
            
            # Check for minimum required fields
            if not artist_name or not track_name:
                log(f"Skipping scrobble with missing artist or track: {scrobble}")
                continue
            
            # Create a standardized scrobble record
            processed_scrobble = {
                'artist_name': artist_name,
                'artist': artist_name,  # Add this for compatibility
                'artist_mbid': scrobble.get('artist_mbid', ''),
                'name': track_name,
                'title': track_name,  # Add this for compatibility
                'album_name': album_name,
                'album': album_name,  # For compatibility
                'album_mbid': album_mbid,
                'timestamp': int(timestamp) if timestamp else 0,
                'fecha_scrobble': fecha,
                'lastfm_url': scrobble.get('lastfm_url', scrobble.get('url', ''))
            }
            
            # Copy service URLs if available
            for service in ['youtube', 'spotify', 'bandcamp', 'soundcloud']:
                service_url_key = f'{service}_url'
                if service_url_key in scrobble:
                    processed_scrobble[service_url_key] = scrobble[service_url_key]
            
            processed.append(processed_scrobble)
            
        except (KeyError, ValueError, TypeError) as e:
            log(f"Error processing scrobble: {e}, Data: {scrobble}")
            continue
    
    log(f"Processed {len(processed)} scrobbles")
    return processed


def save_scrobbles_to_db(self, scrobbles, lastfm_username):
    """
    Save the scrobbles to the database without integrating with songs table.
    Just saves to the user-specific scrobbles table.
    
    Args:
        scrobbles: List of processed scrobbles
        lastfm_username: Name of the Last.fm user
        
    Returns:
        Number of scrobbles saved (new + updated)
    """
    if not scrobbles:
        return 0
    
    if not hasattr(self, 'db_path') or not self.db_path:
        log("Error: No database path configured")
        return 0
    
    try:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table name will be user-specific
        table_name = f"scrobbles_{lastfm_username}"
        
        # Create table if it doesn't exist
        create_scrobbles_table(conn, lastfm_username)
        
        # Get table columns to understand its structure
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        columns = [row[1] for row in columns_info]
        
        # Check for the necessary fields in table schema
        uses_track_name = 'track_name' in columns
        uses_name = 'name' in columns
        uses_scrobble_date = 'scrobble_date' in columns
        uses_fecha_scrobble = 'fecha_scrobble' in columns
        
        log(f"Table columns found: {columns}")
        log(f"Using field mapping - track_name: {uses_track_name}, name: {uses_name}, " + 
                f"scrobble_date: {uses_scrobble_date}, fecha_scrobble: {uses_fecha_scrobble}")
        
        new_count = 0
        updated_count = 0
        duplicate_count = 0
        
        # Create a transaction for better performance
        conn.execute("BEGIN TRANSACTION")
        
        log(f"Saving {len(scrobbles)} scrobbles to {table_name}")
        
        # Process in batches for better performance
        batch_size = 100
        for batch_start in range(0, len(scrobbles), batch_size):
            batch_end = min(batch_start + batch_size, len(scrobbles))
            batch = scrobbles[batch_start:batch_end]
            
            for scrobble in batch:
                # Extract essential fields
                artist_name = scrobble.get('artist_name', scrobble.get('artist', ''))
                name = scrobble.get('name', scrobble.get('title', ''))
                album_name = scrobble.get('album_name', scrobble.get('album', ''))
                timestamp = scrobble.get('timestamp', 0)
                
                # Handle date fields 
                date_text = ""
                if 'fecha_scrobble' in scrobble:
                    date_text = scrobble['fecha_scrobble']
                elif 'date' in scrobble:
                    if isinstance(scrobble['date'], dict):
                        date_text = scrobble['date'].get('#text', '')
                    else:
                        date_text = scrobble['date']
                
                # If date is still empty but we have a timestamp, create a date string
                if not date_text and timestamp:
                    import time
                    date_text = time.strftime("%d %b %Y, %H:%M", time.localtime(int(timestamp)))
                
                # Ensure we have non-NULL values for required fields
                if not date_text:
                    import time
                    date_text = time.strftime("%d %b %Y, %H:%M", time.localtime(time.time()))
                
                # Get lastfm_url
                lastfm_url = scrobble.get('lastfm_url', scrobble.get('url', ''))
                
                if not artist_name or not name:
                    log(f"Skipping scrobble with missing data: {scrobble}")
                    continue
                
                # Check if this scrobble already exists
                track_field = 'track_name' if uses_track_name else 'name'
                date_field = 'scrobble_date' if uses_scrobble_date else 'fecha_scrobble'
                
                # Use a better query to detect duplicates: artist, track, AND timestamp
                query = f"""
                SELECT id FROM {table_name} 
                WHERE LOWER(artist_name) = LOWER(?) AND LOWER({track_field}) = LOWER(?) AND timestamp = ?
                """
                
                cursor.execute(query, (artist_name, name, timestamp))
                result = cursor.fetchone()
                
                if result:
                    # Update existing record
                    scrobble_id = result[0]
                    duplicate_count += 1
                    
                    # Skip update if it's a duplicate
                    continue
                    
                else:
                    # Build column list based on the table structure
                    insert_cols = ['artist_name']
                    insert_vals = ['?']
                    insert_params = [artist_name]
                    
                    # Use appropriate track field name
                    if uses_track_name:
                        insert_cols.append('track_name')
                        insert_vals.append('?')
                        insert_params.append(name)
                    if uses_name:
                        insert_cols.append('name')
                        insert_vals.append('?')
                        insert_params.append(name)
                    
                    # Add timestamp
                    if 'timestamp' in columns:
                        insert_cols.append('timestamp')
                        insert_vals.append('?')
                        insert_params.append(timestamp)
                    
                    # Add date field with appropriate column name
                    if uses_scrobble_date:
                        insert_cols.append('scrobble_date')
                        insert_vals.append('?')
                        insert_params.append(date_text)
                    if uses_fecha_scrobble:
                        insert_cols.append('fecha_scrobble')
                        insert_vals.append('?')
                        insert_params.append(date_text)
                    
                    # Add album name if present
                    if 'album_name' in columns and album_name:
                        insert_cols.append('album_name')
                        insert_vals.append('?')
                        insert_params.append(album_name)
                    
                    # Add lastfm_url if present
                    if 'lastfm_url' in columns and lastfm_url:
                        insert_cols.append('lastfm_url')
                        insert_vals.append('?')
                        insert_params.append(lastfm_url)
                    
                    # Add service URLs if available
                    for service in ['youtube', 'spotify', 'bandcamp', 'soundcloud']:
                        service_url_key = f'{service}_url'
                        if service_url_key in scrobble and scrobble[service_url_key] and service_url_key in columns:
                            insert_cols.append(service_url_key)
                            insert_vals.append('?')
                            insert_params.append(scrobble[service_url_key])
                    
                    # Insert new scrobble record
                    insert_sql = f"""
                    INSERT INTO {table_name} ({', '.join(insert_cols)})
                    VALUES ({', '.join(insert_vals)})
                    """
                    
                    try:
                        cursor.execute(insert_sql, insert_params)
                        new_count += 1
                    except sqlite3.Error as e:
                        # More detailed error reporting
                        log(f"Error inserting scrobble: {e}")
                        log(f"SQL: {insert_sql}")
                        log(f"Params: {insert_params}")
                        continue
        
        # Update user-specific Last.fm config
        config_table = f"lastfm_config_{lastfm_username}"
        
        # Find the latest timestamp from scrobbles
        latest_timestamp = 0
        for scrobble in scrobbles:
            timestamp = scrobble.get('timestamp', 0)
            if timestamp > latest_timestamp:
                latest_timestamp = timestamp
        
        if latest_timestamp > 0:
            try:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{config_table}'")
                if cursor.fetchone():
                    cursor.execute(f"SELECT id FROM {config_table} WHERE id = 1")
                    if cursor.fetchone():
                        cursor.execute(f"""
                        UPDATE {config_table}
                        SET last_timestamp = MAX(last_timestamp, ?), lastfm_username = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE id = 1
                        """, (latest_timestamp, lastfm_username))
                    else:
                        cursor.execute(f"""
                        INSERT INTO {config_table} (id, lastfm_username, last_timestamp, last_updated)
                        VALUES (1, ?, ?, CURRENT_TIMESTAMP)
                        """, (lastfm_username, latest_timestamp))
                else:
                    cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {config_table} (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        lastfm_username TEXT,
                        last_timestamp INTEGER,
                        last_updated TIMESTAMP
                    )
                    """)
                    cursor.execute(f"""
                    INSERT INTO {config_table} (id, lastfm_username, last_timestamp, last_updated)
                    VALUES (1, ?, ?, CURRENT_TIMESTAMP)
                    """, (lastfm_username, latest_timestamp))
            except sqlite3.Error as e:
                log(f"Error updating config table: {e}")
        
        # Commit the transaction
        conn.commit()
        conn.close()
        
        log(f"Database update summary: {new_count} new, {updated_count} updated, {duplicate_count} duplicates skipped")
        return new_count + updated_count
        
    except Exception as e:
        log(f"Error saving scrobbles to database: {str(e)}")
        import traceback
        log(traceback.format_exc())
        
        # Try to rollback if we're in a transaction
        try:
            if conn:
                conn.rollback()
                conn.close()
        except:
            pass
            
        return 0



def load_scrobbles_from_db(self, lastfm_username, start_time=None, end_time=None, limit=None):
    """
    Versión mejorada para cargar scrobbles desde la base de datos.
    """
    try:
        if not hasattr(self, 'db_path') or not self.db_path:
            log("Error: No database path configured")
            return []
            
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Si limit es None o 0, usar valor por defecto
        if not limit:
            limit = getattr(self, 'scrobbles_limit', 100)
            log(f"Using default scrobbles limit: {limit}")
        
        # Nombre de tabla específico de usuario
        table_name = f"scrobbles_{lastfm_username}"
        
        # Verificar si la tabla existe
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            log(f"Table {table_name} does not exist, checking for paqueradejere")
            # Intentar con paqueradejere como fallback
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scrobbles_paqueradejere'")
            if cursor.fetchone():
                table_name = "scrobbles_paqueradejere"
                log("Using scrobbles_paqueradejere table instead")
            else:
                # También intentar con el nombre sin el prefijo 'scrobbles_'
                alternate_table_name = lastfm_username
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{alternate_table_name}'")
                if cursor.fetchone():
                    table_name = alternate_table_name
                    log(f"Using {alternate_table_name} table instead")
                else:
                    log("No scrobbles table found")
                    conn.close()
                    return []
        
        # Obtener columnas disponibles
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        log(f"Available columns in {table_name}: {columns}")
        
        # Determinar el nombre del campo para la pista
        if 'track_name' in columns:
            track_field = 'track_name'
        elif 'name' in columns:
            track_field = 'name'
        else:
            # Intentar encontrar cualquier columna que contenga 'name' o 'track'
            name_columns = [col for col in columns if 'name' in col.lower() or 'track' in col.lower()]
            if name_columns:
                track_field = name_columns[0]
            else:
                track_field = 'name'  # Fallback predeterminado
                
        log(f"Using track field: {track_field}")
        
        # Construir consulta - incluir tantas URLs de servicios como estén disponibles
        select_cols = [f's.id', 's.artist_name', f's.{track_field} AS name', 's.album_name', 
                        's.timestamp']
        
        # Añadir campo de fecha según disponibilidad
        if 'scrobble_date' in columns:
            select_cols.append('s.scrobble_date AS fecha_scrobble')
        elif 'fecha_scrobble' in columns:
            select_cols.append('s.fecha_scrobble')
        
        # Añadir campos de URL que existan
        for url_field in ['lastfm_url', 'youtube_url', 'spotify_url', 'bandcamp_url', 'soundcloud_url']:
            if url_field in columns:
                select_cols.append(f's.{url_field}')
        
        # Añadir columna song_id si existe
        if 'song_id' in columns:
            select_cols.append('s.song_id')
        
        query = f"""
        SELECT {', '.join(select_cols)} FROM {table_name} s
        """
        
        params = []
        where_clauses = []
        
        # Añadir filtros de tiempo
        if start_time is not None:
            where_clauses.append("s.timestamp >= ?")
            params.append(start_time)
        
        if end_time is not None:
            where_clauses.append("s.timestamp <= ?")
            params.append(end_time)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Añadir orden y límite
        query += " ORDER BY s.timestamp DESC"
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        # Ejecutar consulta
        log(f"Executing query: {query} with params: {params}")
        
        try:
            cursor.execute(query, params)
        except sqlite3.OperationalError as e:
            # Si ocurre un error, intentar con una consulta más simple
            log(f"Error with query, trying simpler version: {e}")
            query = f"""
            SELECT id, artist_name, {track_field} AS name, album_name, 
                   timestamp
            FROM {table_name}
            """
            
            if where_clauses:
                query += " WHERE " + " AND ".join([clause.replace('s.', '') for clause in where_clauses])
                
            query += " ORDER BY timestamp DESC"
            
            if limit is not None:
                query += " LIMIT ?"
            
            cursor.execute(query, params)
        
        # Convertir a lista de diccionarios
        columns = [col[0] for col in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            scrobble = dict(zip(columns, row))
            
            # Añadir campos de compatibilidad
            scrobble['artist'] = scrobble.get('artist_name', '')
            scrobble['title'] = scrobble.get('name', '')
            scrobble['album'] = scrobble.get('album_name', '')
            scrobble['type'] = 'track'
            scrobble['source'] = 'lastfm'
            
            results.append(scrobble)
        
        conn.close()
        
        log(f"Loaded {len(results)} scrobbles from database")
        return results
        
    except Exception as e:
        log(f"Error loading scrobbles from database: {str(e)}")
        import traceback
        log(traceback.format_exc())
        return []


def display_scrobbles_in_tree(parent_instance, scrobbles, title):
    """Display scrobbles in the tree widget with improved organization"""
    try:
        # Clear the tree
        parent_instance.treeWidget.clear()
        
        # Check if we have scrobbles
        if not scrobbles:
            parent_instance.log("No scrobbles to display")
            return False
        
        # Import required classes
        from PyQt6.QtWidgets import QTreeWidgetItem
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QIcon
        
        # Check if we need to reorganize by play count
        by_play_count = not getattr(parent_instance, 'scrobbles_by_date', True)
        parent_instance.log(f"Displaying scrobbles by {'play count' if by_play_count else 'date'}")
        
        # Create root item
        root_item = QTreeWidgetItem(parent_instance.treeWidget)
        root_title = f"{'Top Tracks' if by_play_count else 'Scrobbles'}: {title}"
        root_item.setText(0, root_title)
        root_item.setText(1, getattr(parent_instance, 'lastfm_username', 'Unknown User'))
        root_item.setText(2, "Last.fm")
        
        # Format as bold
        font = root_item.font(0)
        font.setBold(True)
        root_item.setFont(0, font)
        
        # Add icon
        root_item.setIcon(0, QIcon(":/services/lastfm"))
        
        # Store data for the root item
        root_item.setData(0, Qt.ItemDataRole.UserRole, {
            'title': root_title,
            'artist': getattr(parent_instance, 'lastfm_username', 'Unknown User'),
            'type': 'playlist',
            'source': 'lastfm'
        })
        
        # Set column headers based on display mode
        if by_play_count:
            parent_instance.treeWidget.headerItem().setText(3, "Reproducciones")
            parent_instance.treeWidget.headerItem().setText(4, "Primer Play")
        else:
            parent_instance.treeWidget.headerItem().setText(3, "Álbum")
            parent_instance.treeWidget.headerItem().setText(4, "Fecha")
        
        # Process scrobbles based on display mode
        if by_play_count:
            # Group by artist and title
            play_counts = {}
            for scrobble in scrobbles:
                # Get fields, supporting both naming conventions
                artist = scrobble.get('artist', scrobble.get('artist_name', ''))
                title = scrobble.get('title', scrobble.get('name', ''))
                album = scrobble.get('album', scrobble.get('album_name', ''))
                
                if not artist or not title:
                    continue
                
                key = f"{artist.lower()}|{title.lower()}"
                if key not in play_counts:
                    play_counts[key] = {
                        'artist': artist,
                        'title': title,
                        'album': album,
                        'count': 0,
                        'timestamps': [],
                        'song_id': scrobble.get('song_id')
                    }
                    
                    # Copy all service URLs
                    for service in ['youtube', 'spotify', 'bandcamp', 'soundcloud']:
                        service_url_key = f'{service}_url'
                        if service_url_key in scrobble and scrobble[service_url_key]:
                            play_counts[key][service_url_key] = scrobble[service_url_key]
                
                play_counts[key]['count'] += 1
                
                # Add timestamp if available
                timestamp = scrobble.get('timestamp')
                if timestamp:
                    try:
                        timestamp = int(timestamp)
                        play_counts[key]['timestamps'].append(timestamp)
                    except (ValueError, TypeError):
                        pass
            
            # Convert to list and sort by play count
            sorted_tracks = sorted(
                play_counts.values(), 
                key=lambda x: x.get('count', 0), 
                reverse=True
            )
            
            # Add tracks with limit
            max_tracks = min(len(sorted_tracks), getattr(parent_instance, 'scrobbles_limit', 100))
            for track in sorted_tracks[:max_tracks]:
                # Create track item
                track_item = QTreeWidgetItem(root_item)
                track_item.setText(0, track['title'])
                track_item.setText(1, track['artist'])
                track_item.setText(2, "Track")
                track_item.setText(3, str(track.get('count', 0)))
                
                # Format first play date if we have timestamps
                if track.get('timestamps'):
                    import time
                    try:
                        first_play = min(track['timestamps'])
                        date_str = time.strftime("%Y-%m-%d", time.localtime(first_play))
                        track_item.setText(4, date_str)
                    except:
                        track_item.setText(4, "Unknown")
                
                # Store data for playback
                track_data = {
                    'title': track['title'],
                    'artist': track['artist'],
                    'album': track.get('album', ''),
                    'type': 'track',
                    'source': 'lastfm',
                    'origen': 'scrobble',  # Add origen field
                    'song_id': track.get('song_id')
                }
                
                # Add service URLs if available
                for service in ['youtube', 'spotify', 'bandcamp', 'soundcloud']:
                    service_url_key = f'{service}_url'
                    if service_url_key in track:
                        track_data[service_url_key] = track[service_url_key]
                
                # Set data on the item
                track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
                
                # Set icon based on available URLs
                icon_set = False
                for service in ['youtube', 'spotify', 'bandcamp', 'soundcloud']:
                    service_url_key = f'{service}_url'
                    if service_url_key in track and track[service_url_key]:
                        track_item.setIcon(0, QIcon(f":/services/{service}"))
                        icon_set = True
                        break
                
                # Default to Last.fm icon if no other service icons available
                if not icon_set:
                    track_item.setIcon(0, QIcon(":/services/lastfm"))
        else:
            # Display chronologically (by date)
            import time
            
            # Sort by timestamp (newest first)
            def get_timestamp(s):
                try:
                    return int(s.get('timestamp', 0))
                except (ValueError, TypeError):
                    return 0
                
            sorted_scrobbles = sorted(scrobbles, key=get_timestamp, reverse=True)
            
            # Add tracks chronologically with limit
            max_scrobbles = min(len(sorted_scrobbles), getattr(parent_instance, 'scrobbles_limit', 100))
            for scrobble in sorted_scrobbles[:max_scrobbles]:
                # Get fields, supporting both naming conventions
                artist = scrobble.get('artist', scrobble.get('artist_name', ''))
                title = scrobble.get('title', scrobble.get('name', ''))
                album = scrobble.get('album', scrobble.get('album_name', ''))
                timestamp = scrobble.get('timestamp', 0)
                song_id = scrobble.get('song_id')
                
                if not artist or not title:
                    continue
                
                # Create track item
                track_item = QTreeWidgetItem(root_item)
                track_item.setText(0, title)
                track_item.setText(1, artist)
                track_item.setText(2, "Track")
                
                if album:
                    track_item.setText(3, album)
                
                # Format date
                if timestamp:
                    try:
                        date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(int(timestamp)))
                        track_item.setText(4, date_str)
                    except (ValueError, TypeError, OverflowError):
                        track_item.setText(4, "Unknown date")
                
                # Store data for playback
                track_data = {
                    'title': title,
                    'artist': artist,
                    'album': album,
                    'type': 'track',
                    'source': 'lastfm',
                    'origen': 'scrobble',
                    'timestamp': timestamp,
                    'song_id': song_id
                }
                
                # Add service URLs if available
                for service in ['youtube', 'spotify', 'bandcamp', 'soundcloud']:
                    service_url_key = f'{service}_url'
                    if service_url_key in scrobble:
                        track_data[service_url_key] = scrobble[service_url_key]
                
                track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
                
                # Set icon based on available URLs
                icon_set = False
                for service in ['youtube', 'spotify', 'bandcamp', 'soundcloud']:
                    service_url_key = f'{service}_url'
                    if service_url_key in scrobble and scrobble[service_url_key]:
                        track_item.setIcon(0, QIcon(f":/services/{service}"))
                        icon_set = True
                        break
                
                # Default to Last.fm icon if no other service icons available
                if not icon_set:
                    track_item.setIcon(0, QIcon(":/services/lastfm"))
        
        # Expand the root item to show all scrobbles
        root_item.setExpanded(True)
        
        # Store the displayed data for reference
        parent_instance.current_scrobbles_data = scrobbles
        
        # Log summary
        scrobble_count = root_item.childCount()
        parent_instance.log(f"Displayed {scrobble_count} scrobbles for {title}")
        
        return True
    except Exception as e:
        parent_instance.log(f"Error displaying scrobbles: {str(e)}")
        import traceback
        parent_instance.log(traceback.format_exc())
        return False


def get_latest_timestamp_from_db(self, lastfm_username):
    """
    Get the latest timestamp from the database for the specified user.
    
    Args:
        self: The parent object with log method
        lastfm_username: Last.fm username
        
    Returns:
        Latest timestamp or 0 if no records
    """
    try:
        if not hasattr(self, 'db_path') or not self.db_path:
            log("Error: No database path configured")
            return 0
            
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First try user-specific config table
        config_table = f"lastfm_config_{lastfm_username}"
        log(f"Checking config table {config_table} for timestamp")
        
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{config_table}'")
        if cursor.fetchone():
            cursor.execute(f"SELECT last_timestamp FROM {config_table} WHERE id = 1")
            result = cursor.fetchone()
            if result and result[0]:
                conn.close()
                log(f"Latest timestamp from config table: {result[0]}")
                return result[0]
        
        # Then try user-specific scrobbles table 
        scrobbles_table = f"scrobbles_{lastfm_username}"
        log(f"Checking scrobbles table {scrobbles_table} for timestamp")
        
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{scrobbles_table}'")
        if cursor.fetchone():
            cursor.execute(f"SELECT MAX(timestamp) FROM {scrobbles_table}")
            result = cursor.fetchone()
            
            if result and result[0]:
                conn.close()
                log(f"Latest timestamp from {scrobbles_table}: {result[0]}")
                return result[0]
        
        # Finally, check the paqueradejere table (fallback)
        # log("Checking scrobbles_paqueradejere table for timestamp")
        # cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scrobbles_paqueradejere'")
        # if cursor.fetchone():
        #     # Make sure the timestamp column exists
        #     cursor.execute("PRAGMA table_info(scrobbles_paqueradejere)")
        #     columns = [row[1] for row in cursor.fetchall()]
            
        #     if 'timestamp' in columns:
        #         cursor.execute("SELECT MAX(timestamp) FROM scrobbles_paqueradejere")
        #         result = cursor.fetchone()
                
        #         if result and result[0] and result[0] > 0:
        #             conn.close()
        #             log(f"Latest timestamp from scrobbles_paqueradejere: {result[0]}")
        #             return result[0]
        #     else:
        #         log("No timestamp column found in scrobbles_paqueradejere table")
        
        log("No valid timestamp found in any table, will perform full sync")
        conn.close()
        return 0
    except Exception as e:
        log(f"Error getting latest timestamp: {str(e)}")
        import traceback
        log(traceback.format_exc())
        return 0

def integrate_scrobbles_to_songs(self, lastfm_username):
    """
    Integrate scrobbles from user-specific table to songs table.
    Updates songs with scrobble information and creates links in song_links.
    
    Args:
        lastfm_username: Name of the Last.fm user
    
    Returns:
        Tuple of (songs_updated, songs_created)
    """
    # Run in a thread
    thread = threading.Thread(
        target=_integrate_scrobbles_to_songs_thread,
        args=(self, lastfm_username),
        daemon=True
    )
    thread.start()
    return True

def _integrate_scrobbles_to_songs_thread(parent, lastfm_username):
    """Thread function for integrating scrobbles into songs table"""
    try:
        # Emitir señal de inicio
        parent.process_started_signal.emit(f"Integrating scrobbles for {lastfm_username}...")
        
        # Conectar a la base de datos
        import sqlite3
        conn = sqlite3.connect(parent.db_path)
        cursor = conn.cursor()
        
        # Verificar que la tabla específica del usuario existe
        table_name = f"scrobbles_{lastfm_username}"
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            parent.process_error_signal.emit(f"Table {table_name} does not exist")
            return (0, 0)
        
        # Contar scrobbles totales
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_scrobbles = cursor.fetchone()[0]
        
        if total_scrobbles == 0:
            parent.process_error_signal.emit(f"No scrobbles found in {table_name}")
            return (0, 0)
        
        # Obtener scrobbles que no han sido integrados (donde song_id es NULL)
        cursor.execute(f"SELECT * FROM {table_name} WHERE song_id IS NULL")
        unintegrated_scrobbles = cursor.fetchall()
        
        # Obtener nombres de columnas
        cursor.execute(f"PRAGMA table_info({table_name})")
        column_info = cursor.fetchall()
        column_names = [col[1] for col in column_info]
        
        # Convertir a lista de diccionarios
        scrobbles = []
        for row in unintegrated_scrobbles:
            scrobble = dict(zip(column_names, row))
            scrobbles.append(scrobble)
        
        # Emitir progreso con mensaje
        parent.process_progress_signal.emit(5, f"Found {len(scrobbles)} unintegrated scrobbles out of {total_scrobbles} total")
        
        # Estadísticas
        songs_updated = 0
        songs_created = 0
        
        # Agrupar scrobbles por artista+título para consolidar
        parent.process_progress_signal.emit(10, "Grouping scrobbles by song...")
        songs_by_key = {}
        
        for i, scrobble in enumerate(scrobbles):
            # Calcular progreso
            if i % 100 == 0:
                prog_value = 10 + int(20 * (i / max(len(scrobbles), 1)))
                parent.process_progress_signal.emit(prog_value, f"Grouping scrobbles: {i}/{len(scrobbles)}")
                
            artist = scrobble.get('artist_name', '')
            title = scrobble.get('track_name', scrobble.get('name', ''))
            scrobble_id = scrobble.get('id')
            timestamp = scrobble.get('timestamp')
            scrobble_date = scrobble.get('scrobble_date', scrobble.get('fecha_scrobble', ''))
            
            key = f"{artist.lower()}|{title.lower()}"
            
            if key not in songs_by_key:
                songs_by_key[key] = {
                    'artist': artist,
                    'title': title,
                    'album': scrobble.get('album_name', ''),
                    'scrobble_ids': [scrobble_id],
                    'scrobble_dates': [scrobble_date],
                    'timestamps': [timestamp],
                    'most_recent': timestamp,
                    'scrobbles': [scrobble]
                }
            else:
                songs_by_key[key]['scrobble_ids'].append(scrobble_id)
                songs_by_key[key]['scrobble_dates'].append(scrobble_date)
                songs_by_key[key]['timestamps'].append(timestamp)
                songs_by_key[key]['scrobbles'].append(scrobble)
                
                if timestamp > songs_by_key[key]['most_recent']:
                    songs_by_key[key]['most_recent'] = timestamp
                    songs_by_key[key]['album'] = scrobble.get('album_name', songs_by_key[key]['album'])
        
        # Emitir progreso
        parent.process_progress_signal.emit(30, f"Processing {len(songs_by_key)} unique songs...")
        
        # Procesar cada canción única
        for i, (key, song_data) in enumerate(songs_by_key.items()):
            # Calcular progreso
            if i % 20 == 0:
                prog_value = 30 + int(60 * (i / max(len(songs_by_key), 1)))
                parent.process_progress_signal.emit(prog_value, f"Processing songs: {i}/{len(songs_by_key)}")
            
            artist = song_data['artist']
            title = song_data['title']
            album = song_data['album']
            scrobble_ids = song_data['scrobble_ids']
            scrobble_dates = song_data['scrobble_dates']
            
            # Encontrar artist_id si está disponible
            artist_id = None
            try:
                cursor.execute("SELECT id FROM artists WHERE LOWER(name) = LOWER(?)", (artist,))
                artist_result = cursor.fetchone()
                if artist_result:
                    artist_id = artist_result[0]
            except sqlite3.Error:
                pass
            
            # Encontrar album_id si está disponible (solo si tenemos artist_id)
            album_id = None
            if artist_id and album:
                try:
                    cursor.execute("""
                    SELECT id FROM albums 
                    WHERE LOWER(name) = LOWER(?) AND artist_id = ?
                    """, (album, artist_id))
                    album_result = cursor.fetchone()
                    if album_result:
                        album_id = album_result[0]
                except sqlite3.Error:
                    pass
            
            # Verificar si la canción ya existe
            cursor.execute("""
            SELECT id, reproducciones, fecha_reproducciones, scrobbles_ids FROM songs 
            WHERE LOWER(artist) = LOWER(?) AND LOWER(title) = LOWER(?)
            """, (artist, title))
            
            song_result = cursor.fetchone()
            
            song_id = None
            
            if song_result:
                # Actualizar canción existente
                song_id = song_result[0]
                
                # Obtener reproducciones y fecha_reproducciones actuales
                reproducciones = song_result[1] if song_result[1] is not None else len(scrobble_ids)
                
                try:
                    existing_dates = json.loads(song_result[2] or '[]')
                    if not isinstance(existing_dates, list):
                        existing_dates = []
                except (json.JSONDecodeError, TypeError):
                    existing_dates = []
                
                try:
                    existing_scrobble_ids = json.loads(song_result[3] or '[]')
                    if not isinstance(existing_scrobble_ids, list):
                        existing_scrobble_ids = []
                except (json.JSONDecodeError, TypeError):
                    existing_scrobble_ids = []
                
                # Combinar listas sin duplicados
                all_dates = list(set(existing_dates + scrobble_dates))
                all_scrobble_ids = list(set(existing_scrobble_ids + [str(id) for id in scrobble_ids]))
                
                # Actualizar registro de canción
                cursor.execute("""
                UPDATE songs SET 
                    reproducciones = ?,
                    fecha_reproducciones = ?,
                    scrobbles_ids = ?,
                    origen = ?,
                    last_modified = CURRENT_TIMESTAMP
                WHERE id = ?
                """, (
                    len(all_scrobble_ids),  # reproducciones = count of unique scrobbles
                    json.dumps(all_dates),  # All dates
                    json.dumps(all_scrobble_ids),  # All scrobble IDs
                    f"scrobble_{lastfm_username}",  # origen con usuario
                    song_id
                ))
                
                songs_updated += 1
            else:
                # Crear nueva canción
                cursor.execute("""
                INSERT INTO songs 
                (title, album, artist, origen, reproducciones, fecha_reproducciones, scrobbles_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    title,
                    album,
                    artist,
                    f"scrobble_{lastfm_username}",  # origen con usuario
                    len(scrobble_ids),  # reproducciones = count of unique scrobbles
                    json.dumps(scrobble_dates),  # All dates
                    json.dumps([str(id) for id in scrobble_ids])  # All scrobble IDs
                ))
                
                song_id = cursor.lastrowid
                songs_created += 1
            
            # Ahora actualizar los scrobbles con song_id, artist_id y album_id
            if song_id:
                # Obtener todos los IDs en una cadena separada por comas
                id_list = ",".join(str(id) for id in scrobble_ids)
                
                # Actualizar tabla de scrobbles
                update_fields = ["song_id = ?"]
                update_params = [song_id]
                
                if artist_id:
                    update_fields.append("artist_id = ?")
                    update_params.append(artist_id)
                
                if album_id:
                    update_fields.append("album_id = ?")
                    update_params.append(album_id)
                
                # Actualizar los scrobbles
                if id_list:  # Asegurarse de que tenemos IDs para actualizar
                    cursor.execute(f"""
                    UPDATE {table_name} 
                    SET {', '.join(update_fields)}
                    WHERE id IN ({id_list})
                    """, update_params)
                
                # Actualizar tabla song_links si es posible
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_links'")
                if cursor.fetchone():
                    # Verificar si la entrada existe
                    cursor.execute("SELECT id FROM song_links WHERE song_id = ?", (song_id,))
                    link_exists = cursor.fetchone()
                    
                    # Recopilar todas las URLs de servicio de todos los scrobbles para esta canción
                    service_urls = {}
                    for scrobble in song_data['scrobbles']:
                        for service in ['youtube', 'spotify', 'bandcamp', 'soundcloud', 'lastfm']:
                            service_url_key = f'{service}_url'
                            if service_url_key in scrobble and scrobble[service_url_key]:
                                # Mantener la URL más reciente si existen múltiples
                                if (service_url_key not in service_urls or 
                                    scrobble.get('timestamp', 0) > service_urls.get(f"{service_url_key}_timestamp", 0)):
                                    service_urls[service_url_key] = scrobble[service_url_key]
                                    service_urls[f"{service_url_key}_timestamp"] = scrobble.get('timestamp', 0)
                    
                    # Eliminar claves de timestamp
                    clean_urls = {k: v for k, v in service_urls.items() if not k.endswith('_timestamp')}
                    
                    if clean_urls:
                        if link_exists:
                            # Actualizar registro existente
                            update_clauses = []
                            update_params = []
                            
                            for service_url_key, url in clean_urls.items():
                                update_clauses.append(f"{service_url_key} = COALESCE(?, {service_url_key})")
                                update_params.append(url)
                            
                            update_params.append(song_id)
                            
                            cursor.execute(f"""
                            UPDATE song_links 
                            SET {', '.join(update_clauses)}, links_updated = CURRENT_TIMESTAMP
                            WHERE song_id = ?
                            """, update_params)
                        else:
                            # Insertar nuevo registro
                            fields = ['song_id', 'links_updated']
                            placeholders = ['?', 'CURRENT_TIMESTAMP']
                            params = [song_id]
                            
                            for field, value in clean_urls.items():
                                fields.append(field)
                                placeholders.append('?')
                                params.append(value)
                            
                            cursor.execute(f"""
                            INSERT INTO song_links ({', '.join(fields)})
                            VALUES ({', '.join(placeholders)})
                            """, params)
        
        # Guardar cambios
        conn.commit()
        
        # Emitir progreso
        parent.process_progress_signal.emit(95, f"Completed! Updated {songs_updated} songs, created {songs_created} new songs")
        
        # Mensaje final
        result_message = f"Integration complete! Updated {songs_updated} songs, created {songs_created} new songs."
        parent.process_finished_signal.emit(result_message, songs_updated + songs_created, total_scrobbles)
        
        conn.close()
        return (songs_updated, songs_created)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        parent.process_error_signal.emit(f"Error: {str(e)}\n\n{error_trace}")
        return (0, 0)
def fetch_links_for_scrobbles(self, lastfm_username):
    """
    Fetches service links for scrobbles and updates song_links table.
    
    Args:
        lastfm_username: Name of the Last.fm user
    """
    # Run in a thread
    thread = threading.Thread(
        target=_fetch_links_thread,
        args=(self, lastfm_username),
        daemon=True
    )
    thread.start()
    return True

def _fetch_links_thread(parent, lastfm_username):
    """Thread function for fetching links"""
    try:
        # Emitir señal de inicio
        parent.process_started_signal.emit(f"Fetching links for {lastfm_username}'s scrobbles...")
        
        # Conectar a la base de datos
        import sqlite3
        conn = sqlite3.connect(parent.db_path)
        cursor = conn.cursor()
        
        # Nombre de tabla específico de usuario
        table_name = f"scrobbles_{lastfm_username}"
        
        # Verificar que la tabla existe
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            parent.process_error_signal.emit(f"Table {table_name} does not exist")
            return 0
        
        # Obtener prioridad de servicio
        service_priority = get_service_priority(parent) if hasattr(parent, 'get_service_priority') else ['youtube', 'spotify', 'bandcamp', 'soundcloud']
        
        # Contar scrobbles totales
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_scrobbles = cursor.fetchone()[0]
        
        if total_scrobbles == 0:
            parent.process_error_signal.emit(f"No scrobbles found in {table_name}")
            return 0
        
        # Contar scrobbles sin enlaces de servicio
        link_conditions = []
        for service in service_priority:
            service_field = f"{service}_url"
            link_conditions.append(f"{service_field} IS NULL")
        
        cursor.execute(f"""
        SELECT COUNT(*) FROM {table_name} 
        WHERE {' AND '.join(link_conditions)}
        """)
        unlinked_count = cursor.fetchone()[0]
        
        parent.process_progress_signal.emit(5, f"Found {unlinked_count} scrobbles without links out of {total_scrobbles} total")
        
        # Obtener los scrobbles sin enlaces
        cursor.execute(f"""
        SELECT * FROM {table_name} 
        WHERE {' AND '.join(link_conditions)}
        LIMIT 1000  /* Limitar para evitar procesar demasiados a la vez */
        """)
        unlinked_rows = cursor.fetchall()
        
        # Obtener nombres de columnas
        cursor.execute(f"PRAGMA table_info({table_name})")
        column_info = cursor.fetchall()
        column_names = [col[1] for col in column_info]
        
        # Convertir a lista de diccionarios
        unlinked_scrobbles = []
        for row in unlinked_rows:
            scrobble = dict(zip(column_names, row))
            unlinked_scrobbles.append(scrobble)
        
        # Procesar scrobbles
        links_found = 0
        
        for i, scrobble in enumerate(unlinked_scrobbles):                
            # Calcular progreso
            prog_value = 5 + int(90 * (i / len(unlinked_scrobbles)))
            if i % 10 == 0:
                parent.process_progress_signal.emit(prog_value, f"Processing scrobble {i+1}/{len(unlinked_scrobbles)}, found {links_found} links")
            
            # Obtener información básica
            scrobble_id = scrobble.get('id')
            artist_name = scrobble.get('artist_name', '')
            track_name = scrobble.get('track_name', scrobble.get('name', ''))
            album_name = scrobble.get('album_name', '')
            lastfm_url = scrobble.get('lastfm_url', '')
            song_id = scrobble.get('song_id')
            
            # Primero intentar obtener enlaces de fuentes existentes
            links = None
            
            # Método 1: Verificar si tenemos la misma pista en otro scrobble con enlaces
            for service in service_priority:
                service_field = f"{service}_url"
                
                cursor.execute(f"""
                SELECT {service_field} FROM {table_name}
                WHERE LOWER(artist_name) = LOWER(?) AND LOWER(track_name) = LOWER(?)
                AND {service_field} IS NOT NULL
                LIMIT 1
                """, (artist_name, track_name))
                
                result = cursor.fetchone()
                if result and result[0]:
                    # Actualizar este scrobble con el enlace encontrado
                    cursor.execute(f"""
                    UPDATE {table_name}
                    SET {service_field} = ?
                    WHERE id = ?
                    """, (result[0], scrobble_id))
                    
                    links_found += 1
                    
                    # Si tenemos un song_id, también actualizar song_links
                    if song_id:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_links'")
                        if cursor.fetchone():
                            cursor.execute("SELECT id FROM song_links WHERE song_id = ?", (song_id,))
                            if cursor.fetchone():
                                # Actualizar registro existente
                                cursor.execute(f"""
                                UPDATE song_links
                                SET {service_field} = COALESCE(?, {service_field}),
                                    links_updated = CURRENT_TIMESTAMP
                                WHERE song_id = ?
                                """, (result[0], song_id))
                            else:
                                # Insertar nuevo registro
                                cursor.execute(f"""
                                INSERT INTO song_links (song_id, {service_field}, links_updated)
                                VALUES (?, ?, CURRENT_TIMESTAMP)
                                """, (song_id, result[0]))
                    
                    # Encontramos un enlace, eso es suficiente por ahora
                    links = {service: result[0]}
                    break
            
            # Si no encontramos enlaces y tenemos una lastfm_url, intentar extraer de ahí
            if not links and lastfm_url:
                for service in service_priority:
                    try:
                        from modules.submodules.url_playlist.lastfm_manager import extract_link_from_lastfm
                        service_url = extract_link_from_lastfm(parent, lastfm_url, service)
                        if service_url:
                            service_field = f"{service}_url"
                            
                            # Actualizar el scrobble
                            cursor.execute(f"""
                            UPDATE {table_name}
                            SET {service_field} = ?
                            WHERE id = ?
                            """, (service_url, scrobble_id))
                            
                            links_found += 1
                            
                            # Si tenemos un song_id, también actualizar song_links
                            if song_id:
                                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_links'")
                                if cursor.fetchone():
                                    cursor.execute("SELECT id FROM song_links WHERE song_id = ?", (song_id,))
                                    if cursor.fetchone():
                                        # Actualizar registro existente
                                        cursor.execute(f"""
                                        UPDATE song_links
                                        SET {service_field} = COALESCE(?, {service_field}),
                                            links_updated = CURRENT_TIMESTAMP
                                        WHERE song_id = ?
                                        """, (service_url, song_id))
                                    else:
                                        # Insertar nuevo registro
                                        cursor.execute(f"""
                                        INSERT INTO song_links (song_id, {service_field}, links_updated)
                                        VALUES (?, ?, CURRENT_TIMESTAMP)
                                        """, (song_id, service_url))
                            
                            # Encontramos un enlace, eso es suficiente por ahora
                            links = {service: service_url}
                            break
                    except Exception as e:
                        parent.log(f"Error extracting {service} link: {e}")
            
            # Si procesamos un lote de scrobbles, hacer commit periódicamente
            if i % 50 == 0:
                conn.commit()
        
        # Commit final
        conn.commit()
        
        # Actualización final
        parent.process_finished_signal.emit(f"Complete! Found {links_found} links for {len(unlinked_scrobbles)} scrobbles", links_found, len(unlinked_scrobbles))
        
        conn.close()
        return links_found
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        parent.process_error_signal.emit(f"Error: {str(e)}\n\n{error_trace}")
        return 0
