#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MusicBrainz Album Info Module (mb_album_info.py)

Fetches and updates music database with album information from the MusicBrainz API.
"""

import os
import sys
import time
import json
import sqlite3
import logging
import requests
from datetime import datetime



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('mb_album_info')

# Global variables that can be set by db_creator.py
CONFIG = {}
INTERACTIVE_MODE = False
force_update = False

def _connect_db(db_path, timeout=30):
    """Connect to the SQLite database with improved error handling."""
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        # Speed up transactions
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        sys.exit(1)




def _ensure_tables_exist(conn):
    """Ensure all required tables and columns exist in the database."""
    cursor = conn.cursor()
    
    # Check and update the albums table
    _ensure_table_columns(cursor, "albums", {
        "mbid": "TEXT",
        "musicbrainz_albumid": "TEXT",
        "musicbrainz_albumartistid": "TEXT",
        "musicbrainz_releasegroupid": "TEXT",
        "catalog_number": "TEXT",
        "media": "TEXT",
        "discnumber": "INTEGER",
        "releasecountry": "TEXT",
        "last_updated": "TIMESTAMP"
    })
    
    # Verificar la columna last_updated en la tabla song_links
    _ensure_table_columns(cursor, "song_links", {
        "last_updated": "TIMESTAMP"
    })
    
    _ensure_table_columns(cursor, "albums_links", {
        "last_updated": "TIMESTAMP"
    })
    

    # Check and update the album_links table
    if not _table_exists(cursor, "album_links"):
        cursor.execute('''
            CREATE TABLE album_links (
                id INTEGER PRIMARY KEY,
                album_id INTEGER NOT NULL,
                musicbrainz_url TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (album_id) REFERENCES albums(id)
            )
        ''')
        logger.info("Created album_links table")
        
        # Create index for faster lookups
        cursor.execute('CREATE INDEX idx_album_links_album_id ON album_links(album_id)')
    
    # Create indexes for efficient lookups
    _create_index_if_not_exists(cursor, "albums", "idx_albums_mbid", "mbid")
    _create_index_if_not_exists(cursor, "albums", "idx_albums_name", "name")
    _create_index_if_not_exists(cursor, "albums", "idx_albums_musicbrainz_albumid", "musicbrainz_albumid")
    
    conn.commit()

def _table_exists(cursor, table_name):
    """Check if a table exists in the database."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def _ensure_table_columns(cursor, table_name, columns):
    """Ensure a table exists and has all required columns."""
    if not _table_exists(cursor, table_name):
        logger.error(f"Table {table_name} doesn't exist. Please create it first.")
        return False
    
    # Get existing columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row['name']: row['type'] for row in cursor.fetchall()}
    
    logger.debug(f"Existing columns in {table_name}: {existing_columns}")
    
    # Add missing columns
    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            try:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                logger.debug(f"Executing SQL: {sql}")
                cursor.execute(sql)
                logger.info(f"Added column {column_name} to {table_name}")
            except sqlite3.Error as e:
                logger.error(f"Error adding column {column_name} to {table_name}: {str(e)}")
    
    return True





def _create_index_if_not_exists(cursor, table_name, index_name, column_name):
    """Create an index if it doesn't exist."""
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'")
    if cursor.fetchone() is None:
        cursor.execute(f"CREATE INDEX {index_name} ON {table_name}({column_name})")
        logger.info(f"Created index {index_name} on {table_name}({column_name})")

def _api_request(mb_api_url, endpoint, params=None, user_agent="MusicLibraryApp/1.0"):
    """Make a rate-limited request to the MusicBrainz API."""
    if params is None:
        params = {}
    
    # Add format parameter
    params['fmt'] = 'json'
    
    # Respect rate limiting (1 request per second)
    request_delay = 1.1
    
    # Set headers
    headers = {
        'User-Agent': user_agent
    }
    
    # Make the request with retries
    url = f"{mb_api_url}/{endpoint}"
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Too Many Requests
                retry_after = int(response.headers.get('Retry-After', '5'))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                logger.warning(f"API request failed with status {response.status_code}. Attempt {attempt+1}/{max_retries}")
                time.sleep(request_delay * 2)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error: {str(e)}. Attempt {attempt+1}/{max_retries}")
            time.sleep(request_delay * 2)
        
        # Add delay between retries
        time.sleep(request_delay)
    
    logger.error(f"Failed to get data from MusicBrainz API after {max_retries} attempts")
    return None

def _get_albums_to_update(conn, use_force_update=False, limit=100):
    """Get albums that need to be updated from MusicBrainz."""
    cursor = conn.cursor()
    
    base_query = """
    SELECT a.id, a.name, a.artist_id, ar.name as artist_name, 
           a.mbid, a.year, s.mbid as song_mbid
    FROM albums a
    LEFT JOIN artists ar ON a.artist_id = ar.id
    LEFT JOIN songs s ON s.album = a.name AND s.artist = ar.name
    """
    
    # By default, only process albums with missing information
    if use_force_update:
        # Force update all albums
        condition = "1=1"
    else:
        # Only update albums with missing essential information
        condition = """
            (a.mbid IS NULL OR 
             a.musicbrainz_albumid IS NULL OR 
             a.musicbrainz_albumartistid IS NULL OR 
             a.musicbrainz_releasegroupid IS NULL OR
             a.catalog_number IS NULL OR
             NOT EXISTS (SELECT 1 FROM album_links al WHERE al.album_id = a.id AND al.musicbrainz_url IS NOT NULL))
        """
    
    query = f"{base_query} WHERE {condition} GROUP BY a.id LIMIT ?"
    
    cursor.execute(query, (limit,))
    return cursor.fetchall()

def _search_release_by_mbid(mb_api_url, mbid, user_agent):
    """Search for a release by its MBID."""
    return _api_request(mb_api_url, f"release/{mbid}", {
        'inc': 'artists+labels+recordings+release-groups+media'
    }, user_agent)

def _search_release_by_info(mb_api_url, album_name, artist_name=None, user_agent=None):
    """Search for a release by album name and optionally artist name."""
    query = f"release:{album_name}"
    if artist_name:
        query += f" AND artist:{artist_name}"
    
    return _api_request(mb_api_url, "release", {
        'query': query,
        'limit': 5
    }, user_agent)

def _search_recording_by_mbid(mb_api_url, mbid, user_agent):
    """Search for a recording by MBID."""
    return _api_request(mb_api_url, f"recording/{mbid}", {
        'inc': 'releases+artists'
    }, user_agent)

def _update_album_from_mb_data(conn, album_id, mb_data):
    """Update album information from MusicBrainz data."""
    if not mb_data or 'error' in mb_data:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Extract relevant data
        album_mbid = mb_data.get('id')
        album_title = mb_data.get('title')
        
        # Get release date info
        release_date = mb_data.get('date', '')
        release_year = release_date.split('-')[0] if release_date and '-' in release_date else None
        
        # Get label info
        label_info = None
        if 'label-info-list' in mb_data and mb_data['label-info-list']:
            label_info = mb_data['label-info-list'][0]
            label_name = label_info.get('label', {}).get('name') if 'label' in label_info else None
            catalog_number = label_info.get('catalog-number')
        else:
            label_name = None
            catalog_number = None
        
        # Get artist MBID
        artist_mbid = None
        if 'artist-credit' in mb_data and mb_data['artist-credit']:
            artist = mb_data['artist-credit'][0]
            if 'artist' in artist and 'id' in artist['artist']:
                artist_mbid = artist['artist']['id']
        
        # Get release group MBID
        release_group_mbid = None
        if 'release-group' in mb_data and 'id' in mb_data['release-group']:
            release_group_mbid = mb_data['release-group']['id']
        
        # Get media info
        media_format = None
        disc_number = None
        total_tracks = 0
        if 'media' in mb_data and mb_data['media']:
            for media in mb_data['media']:
                total_tracks += int(media.get('track-count', 0))
                if not media_format and 'format' in media:
                    media_format = media.get('format')
                if not disc_number and 'position' in media:
                    disc_number = media.get('position')
        
        # Get country
        country = mb_data.get('country')
        
        # Update the albums table
        update_query = """
        UPDATE albums
        SET mbid = ?,
            year = COALESCE(?, year),
            label = COALESCE(?, label),
            total_tracks = COALESCE(?, total_tracks),
            musicbrainz_albumid = ?,
            musicbrainz_albumartistid = ?,
            musicbrainz_releasegroupid = ?,
            catalog_number = ?,
            media = ?,
            discnumber = ?,
            releasecountry = ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        
        cursor.execute(update_query, (
            album_mbid,
            release_year,
            label_name,
            total_tracks,
            album_mbid,
            artist_mbid,
            release_group_mbid,
            catalog_number,
            media_format,
            disc_number,
            country,
            album_id
        ))
        
        # Update or insert into album_links table
        cursor.execute("SELECT id FROM album_links WHERE album_id = ?", (album_id,))
        link_row = cursor.fetchone()
        
        musicbrainz_url = f"https://musicbrainz.org/release/{album_mbid}"
        
        if link_row:
            cursor.execute("""
            UPDATE album_links
            SET musicbrainz_url = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE album_id = ?
            """, (musicbrainz_url, album_id))
        else:
            cursor.execute("""
            INSERT INTO album_links (album_id, musicbrainz_url, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (album_id, musicbrainz_url))
        
        conn.commit()
        logger.info(f"Updated album: {album_title} (ID: {album_id})")
        return True
        
    except Exception as e:
        logger.error(f"Error updating album {album_id}: {str(e)}")
        conn.rollback()
        return False

def process_albums(conn, config):
    """Process albums that need MusicBrainz info."""
    # Extract configuration
    limit = config.get('limit', 100)
    mb_api_url = "https://musicbrainz.org/ws/2"
    user_agent = config.get('user_agent', 'MusicLibraryApp/1.0 (your-email@example.com)')
    use_force_update = force_update or config.get('force_update', False)
    
    # Get albums to update
    albums = _get_albums_to_update(conn, use_force_update, limit)
    total_albums = len(albums)
    logger.info(f"Found {total_albums} albums to process (Force update: {use_force_update})")
    
    if total_albums == 0:
        logger.info("No albums need updating")
        return
    
    updated_count = 0
    for i, album in enumerate(albums):
        album_id = album['id']
        album_name = album['name']
        artist_name = album['artist_name']
        album_mbid = album['mbid']
        song_mbid = album['song_mbid']
        
        logger.info(f"Processing {i+1}/{total_albums}: {artist_name} - {album_name}")
        
        mb_data = None
        
        # Strategy 1: Try with album MBID if available
        if album_mbid:
            logger.info(f"Searching by album MBID: {album_mbid}")
            mb_data = _search_release_by_mbid(mb_api_url, album_mbid, user_agent)
        
        # Strategy 2: Try with song MBID if available
        if not mb_data and song_mbid:
            logger.info(f"Searching by song MBID: {song_mbid}")
            recording_data = _search_recording_by_mbid(mb_api_url, song_mbid, user_agent)
            
            if recording_data and 'releases' in recording_data and recording_data['releases']:
                # Get the first release that matches album name
                for release in recording_data['releases']:
                    if release['title'].lower() == album_name.lower():
                        mb_data = _search_release_by_mbid(mb_api_url, release['id'], user_agent)
                        break
        
        # Strategy 3: Search by album and artist name
        if not mb_data:
            logger.info(f"Searching by album and artist name: {artist_name} - {album_name}")
            search_results = _search_release_by_info(mb_api_url, album_name, artist_name, user_agent)
            
            if search_results and 'releases' in search_results and search_results['releases']:
                # Find the closest match
                for release in search_results['releases']:
                    if release['title'].lower() == album_name.lower() and any(
                        artist['artist']['name'].lower() == artist_name.lower() 
                        for artist in release['artist-credit'] if 'artist' in artist
                    ):
                        mb_data = _search_release_by_mbid(mb_api_url, release['id'], user_agent)
                        break
        
        # Update the database with the retrieved data
        if mb_data:
            success = _update_album_from_mb_data(conn, album_id, mb_data)
            if success:
                updated_count += 1
        else:
            logger.warning(f"No MusicBrainz data found for: {artist_name} - {album_name}")
        
        # Interactive mode confirmation
        if INTERACTIVE_MODE and (i+1) % 10 == 0:
            continue_processing = input(f"Processed {i+1}/{total_albums} albums. Continue? (y/n): ")
            if continue_processing.lower() != 'y':
                logger.info("Processing interrupted by user")
                break
        
        # Add delay to respect rate limiting
        time.sleep(1.1)
    
    logger.info(f"Processing complete. Updated {updated_count}/{total_albums} albums")



def main(config=None):
    """Main entry point for the module."""
    # Get configuration either from parameter or from globals
    if config is None:
        config = CONFIG.copy() if CONFIG else {}
    
    # Database connection
    db_path = config.get('db_path', 'music.db')
    conn = None
    
    try:
        logger.info("Starting MusicBrainz album info processing")
        
        # Connect to the database
        conn = _connect_db(db_path)

        
        # Process albums
        process_albums(conn, config)
        
        logger.info("MusicBrainz album info processing complete")
        return 0  # Success
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 1  # User interruption
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 2  # Error
    finally:
        if conn:
            conn.close()

# For direct execution
if __name__ == "__main__":
    sys.exit(main())