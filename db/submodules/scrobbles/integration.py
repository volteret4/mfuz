#!/usr/bin/env python3
import sqlite3
import requests
import json
import argparse
import datetime
import time
import os
from pathlib import Path
import musicbrainzngs

# Globals
INTERACTIVE_MODE = False  # This will be set by db_creator.py
FORCE_UPDATE = False      # This will be set by db_creator.py
CONFIG = {}               # Will store the configuration

# Global cache instances
cache_system = {
    'lastfm': None,
    'musicbrainz': None
}

def setup_musicbrainz(cache_directory=None):
    """Configures the MusicBrainz client and cache system"""
    global cache_system
    
    # Configure MusicBrainz client
    musicbrainzngs.set_useragent(
        "TuAppMusical", 
        "1.0", 
        "tu_email@example.com"
    )
    
    # Initialize cache if needed
    if cache_directory:
        try:
            from cache_handler import setup_cache_system
            cache_system = setup_cache_system(cache_directory)
            print(f"Cache system configured in: {cache_directory}")
        except ImportError:
            print("Warning: cache_handler module not found, running without cache")
    else:
        print("Running without persistent cache")

def handle_force_update(db_path, lastfm_username):
    """
    Critical function: Runs at the beginning of the module to ensure force_update works
    
    Args:
        db_path: Path to the database file
        lastfm_username: Last.fm username to customize the table
    """
    global FORCE_UPDATE
    if not FORCE_UPDATE or not db_path or not lastfm_username:
        return
        
    print("\n" + "!"*80)
    print(f"FORCE_UPDATE MODE ACTIVATED: Deleting all existing scrobbles for {lastfm_username}")
    print("!"*80 + "\n")
    
    try:
        # Connect directly to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Name of the customized scrobbles table
        scrobbles_table = f"scrobbles_{lastfm_username}"
        
        # Check if the table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{scrobbles_table}'")
        if cursor.fetchone():
            # Delete data
            cursor.execute(f"DELETE FROM {scrobbles_table}")
            # Reset timestamp
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lastfm_config'")
            if cursor.fetchone():
                cursor.execute("UPDATE lastfm_config SET last_timestamp = 0 WHERE id = 1")
            
            conn.commit()
            print(f"Database cleaned successfully: {db_path}")
            print(f"All scrobbles for {lastfm_username} have been deleted. A full update will be performed.\n")
        else:
            print(f"Table '{scrobbles_table}' doesn't exist yet in the database: {db_path}")
        
        conn.close()
    except Exception as e:
        print(f"Error trying to clean the database: {e}")

def setup_database(conn, lastfm_username):
    """Sets up the database with the tables needed for scrobbles
    
    Args:
        conn: Database connection
        lastfm_username: Last.fm username to customize the table
    """
    cursor = conn.cursor()
    
    # Name of the customized scrobbles table for this user
    scrobbles_table = f"scrobbles_{lastfm_username}"
    
    # Create scrobbles table for this specific user if it doesn't exist
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {scrobbles_table} (
        id INTEGER PRIMARY KEY,
        track_name TEXT NOT NULL,
        album_name TEXT,
        artist_name TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        scrobble_date TIMESTAMP NOT NULL,
        lastfm_url TEXT,
        song_id INTEGER,
        album_id INTEGER,
        artist_id INTEGER,
        FOREIGN KEY (song_id) REFERENCES songs(id),
        FOREIGN KEY (album_id) REFERENCES albums(id),
        FOREIGN KEY (artist_id) REFERENCES artists(id)
    )
    """)
    
    # Create table for configuration
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lastfm_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        lastfm_username TEXT,
        last_timestamp INTEGER,
        last_updated TIMESTAMP
    )
    """)
    
    # Create scrobbled_songs table for songs that don't exist in the main DB
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scrobbled_songs (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        artist_name TEXT NOT NULL,
        artist_id INTEGER,
        album_name TEXT,
        album_id INTEGER,
        song_id INTEGER,
        lastfm_url TEXT,
        scrobble_timestamps TEXT,  -- JSON list of timestamps
        mbid TEXT,
        FOREIGN KEY (artist_id) REFERENCES artists(id),
        FOREIGN KEY (album_id) REFERENCES albums(id),
        FOREIGN KEY (song_id) REFERENCES songs(id)
    )
    """)
    
    # Create indices for efficient searches
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_timestamp ON {scrobbles_table}(timestamp)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist ON {scrobbles_table}(artist_name)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_song_id ON {scrobbles_table}(song_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scrobbled_songs_title ON scrobbled_songs(title)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scrobbled_songs_artist ON scrobbled_songs(artist_name)")
    
    # Function to check if a column exists in a table
    def column_exists(table, column):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [info[1] for info in cursor.fetchall()]