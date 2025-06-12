import re
import sqlite3
import sys
import time
import logging
from pathlib import Path
from typing import Optional
import requests

# Configuración global que será establecida por db_creator
CONFIG = {}

def setup_logging():
    """Setup basic logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def get_spotify_preview_url(spotify_track_id: str) -> Optional[str]:
    """
    Get the preview URL for a Spotify track using the embed page workaround.
    
    Args:
        spotify_track_id (str): The Spotify track ID
        
    Returns:
        Optional[str]: The preview URL if found, else None
    """
    try:
        embed_url = f"https://open.spotify.com/embed/track/{spotify_track_id}"
        response = requests.get(embed_url, timeout=10)
        response.raise_for_status()
        
        html = response.text
        match = re.search(r'"audioPreview":\s*{\s*"url":\s*"([^"]+)"', html)
        return match.group(1) if match else None
        
    except Exception as e:
        logger.debug(f"Failed to fetch Spotify preview URL for {spotify_track_id}: {e}")
        return None

def extract_spotify_id(spotify_url: str) -> Optional[str]:
    """Extract Spotify track ID from various URL formats."""
    if not spotify_url:
        return None
        
    patterns = [
        r'spotify:track:([a-zA-Z0-9]{22})',
        r'open\.spotify\.com/track/([a-zA-Z0-9]{22})',
        r'spotify\.com/track/([a-zA-Z0-9]{22})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, spotify_url)
        if match:
            return match.group(1)
    return None

def test_preview_url(preview_url: str) -> bool:
    """Test if preview URL is accessible."""
    try:
        response = requests.head(preview_url, timeout=5)
        return response.status_code == 200
    except:
        return False

def ensure_spotify_preview_column(db):
    """Ensure the spotify_preview column exists in song_links table."""
    try:
        cursor = db.cursor()
        # Check if column exists
        cursor.execute("PRAGMA table_info(song_links)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'spotify_preview' not in columns:
            logger.info("Adding spotify_preview column to song_links table...")
            cursor.execute("ALTER TABLE song_links ADD COLUMN spotify_preview TEXT")
            db.commit()
            logger.info("✓ Column spotify_preview added successfully")
        else:
            logger.info("Column spotify_preview already exists")
            
    except Exception as e:
        logger.error(f"Error ensuring spotify_preview column: {e}")
        raise

def get_songs_needing_preview(db, force_update=False, batch_size=None):
    """Get songs that have Spotify URLs but no preview URL."""
    condition = "sl.spotify_url IS NOT NULL AND sl.spotify_url != ''"
    
    if not force_update:
        condition += " AND (sl.spotify_preview IS NULL OR sl.spotify_preview = '')"
    
    query = f"""
    SELECT DISTINCT 
        sl.song_id,
        sl.spotify_url,
        sl.spotify_id,
        s.title,
        s.artist
    FROM song_links sl
    JOIN songs s ON sl.song_id = s.id
    WHERE {condition}
    ORDER BY sl.song_id
    """
    
    if batch_size:
        query += f" LIMIT {batch_size}"
        
    cursor = db.cursor()
    cursor.execute(query)
    return cursor.fetchall()

def update_preview_url(db, song_id: int, preview_url: Optional[str]):
    """Update preview URL for a song."""
    cursor = db.cursor()
    cursor.execute("""
        UPDATE song_links 
        SET spotify_preview = ?, 
            links_updated = CURRENT_TIMESTAMP
        WHERE song_id = ?
    """, (preview_url, song_id))
    db.commit()

def process_songs(db, config):
    """Process songs and update their preview URLs."""
    force_update = config.get('force_update', False)
    batch_size = config.get('batch_size', 100)
    rate_limit = config.get('rate_limit', 1.0)
    max_retries = config.get('max_retries', 3)
    test_playback = config.get('test_playback', False)
    
    songs = get_songs_needing_preview(db, force_update, batch_size)
    
    if not songs:
        logger.info("No songs need preview URL updates")
        return
        
    logger.info(f"Processing {len(songs)} songs for Spotify preview URLs...")
    
    successful_updates = 0
    failed_updates = 0
    
    for i, (song_id, spotify_url, spotify_id, title, artist) in enumerate(songs, 1):
        try:
            # Extract Spotify ID if not already available
            track_id = spotify_id or extract_spotify_id(spotify_url)
            
            if not track_id:
                logger.warning(f"Could not extract Spotify ID from: {spotify_url}")
                failed_updates += 1
                continue
            
            logger.info(f"[{i}/{len(songs)}] Processing: {artist} - {title}")
            
            # Get preview URL with retries
            preview_url = None
            for attempt in range(max_retries):
                preview_url = get_spotify_preview_url(track_id)
                if preview_url:
                    break
                if attempt < max_retries - 1:
                    time.sleep(1)
            
            # Test preview URL if requested
            if preview_url and test_playback:
                if not test_preview_url(preview_url):
                    logger.warning(f"Preview URL not accessible: {preview_url}")
                    preview_url = None
            
            # Update database
            update_preview_url(db, song_id, preview_url)
            
            if preview_url:
                logger.info(f"✓ Preview URL found: {preview_url[:50]}...")
                successful_updates += 1
            else:
                logger.info("✗ No preview URL found")
                failed_updates += 1
            
            # Rate limiting
            if rate_limit and i < len(songs):
                time.sleep(rate_limit)
                
        except Exception as e:
            logger.error(f"Error processing song {song_id}: {e}")
            failed_updates += 1
            continue
    
    logger.info(f"Completed! Success: {successful_updates}, Failed: {failed_updates}")

def main(config=None):
    """Main function for the script."""
    global CONFIG, logger
    
    # Set up configuration
    CONFIG = config or {}
    logger = setup_logging()
    
    try:
        logger.info("Starting Spotify Preview URL updater...")
        
        # Connect to database
        db_path = CONFIG.get('db_path')
        if not db_path:
            raise ValueError("db_path not found in configuration")
            
        db = sqlite3.connect(db_path)
        
        try:
            # Ensure database column exists
            ensure_spotify_preview_column(db)
            
            # Process songs
            process_songs(db, CONFIG)
            
            logger.info("Spotify preview URL update completed successfully!")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in Spotify preview updater: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()