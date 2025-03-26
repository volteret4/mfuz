import sqlite3
import requests
import time
import json
from datetime import datetime

MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2/"


# Function to fetch recording relationships from MusicBrainz
def fetch_recording_relationships(mbid):
    # MusicBrainz API requires a user agent with your app name and contact info
    headers = {
        "User-Agent": "YourMusicApp/1.0 (your.email@example.com)"
    }
    
    # Relationship types we're interested in
    relationship_types = [
        "samples", "a cappella", "instrumental", "karaoke", "edit", 
        "music video", "first track release", "remaster", "remix", 
        "compilation", "DJ-mix", "mashes up", "part of", "recorded during"
    ]
    
    # Include relationships in the API request
    url = f"{MUSICBRAINZ_API_URL}recording/{mbid}?inc=artist-credits+releases+recording-rels+series-rels+release-rels&fmt=json"
    
    # Make the request with proper rate limiting (1 request per second)
    try:
        response = requests.get(url, headers=headers)
        time.sleep(1)  # MusicBrainz rate limit
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching data for MBID {mbid}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception when fetching data for MBID {mbid}: {str(e)}")
        return None

# Function to process relationships and store in database
def process_relationships(song_id, mbid, cursor, conn):
    data = fetch_recording_relationships(mbid)
    if not data:
        return
    
    # Process recording-recording relationships
    if 'relations' in data:
        for relation in data['relations']:
            # Extract relationship type
            rel_type = relation.get('type')
            if not rel_type:
                continue
                
            # Get the direction (target or source)
            direction = "outgoing"  # Default
            if 'direction' in relation:
                direction = relation['direction']
            
            # Get related entity data
            related_mbid = None
            related_title = None
            related_artist = None
            
            if 'recording' in relation:
                related_mbid = relation['recording'].get('id')
                related_title = relation['recording'].get('title')
                
                # Get artist if available
                if 'artist-credit' in relation['recording']:
                    artists = []
                    for artist_credit in relation['recording']['artist-credit']:
                        if isinstance(artist_credit, dict) and 'artist' in artist_credit:
                            artists.append(artist_credit['artist']['name'])
                    related_artist = ", ".join(artists) if artists else None
            
            elif 'release' in relation:
                related_mbid = relation['release'].get('id')
                related_title = relation['release'].get('title')
                
                # Get artist if available
                if 'artist-credit' in relation['release']:
                    artists = []
                    for artist_credit in relation['release']['artist-credit']:
                        if isinstance(artist_credit, dict) and 'artist' in artist_credit:
                            artists.append(artist_credit['artist']['name'])
                    related_artist = ", ".join(artists) if artists else None
            
            elif 'series' in relation:
                related_mbid = relation['series'].get('id')
                related_title = relation['series'].get('name')
            
            # Only store if we have the required data
            if related_mbid:
                cursor.execute("""
                    INSERT INTO mb_data_songs 
                    (song_id, relationship_type, related_mbid, related_title, related_artist, relationship_direction, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    song_id,
                    rel_type,
                    related_mbid,
                    related_title,
                    related_artist,
                    direction,
                    datetime.now()
                ))
                conn.commit()

# Main function
def main(config=None):
    parser = argparse.ArgumentParser(description='Extract MusicBrainz links and reviews for albums')
    parser.add_argument('--config', help='Path to json config ')
    parser.add_argument('--db-path', required=True, help='Path to the SQLite database')

    args = parser.parse_args()
    
    with open(args.config, 'r') as f:
        config_data = json.load(f)
        
    # Combinar configuraciones
    config = {}
    config.update(config_data.get("common", {}))
    config.update(config_data.get("mb_data_canciones", {}))

    db_path = args.db_path or config['db_path']

    
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if mb_data_songs table exists, create if not
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mb_data_songs (
        id INTEGER PRIMARY KEY,
        song_id INTEGER NOT NULL,
        relationship_type TEXT NOT NULL,
        related_mbid TEXT NOT NULL,
        related_title TEXT,
        related_artist TEXT,
        relationship_direction TEXT NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (song_id) REFERENCES songs(id)
    );
    """)
    conn.commit()
    
    # Get songs with MusicBrainz IDs
    cursor.execute("SELECT id, mbid FROM songs WHERE mbid IS NOT NULL AND mbid != ''")
    songs = cursor.fetchall()
    
    print(f"Found {len(songs)} songs with MusicBrainz IDs")
    
    # Process each song
    for i, (song_id, mbid) in enumerate(songs):
        print(f"Processing song {i+1}/{len(songs)} with ID {song_id} and MBID {mbid}")
        
        # Check if we already have data for this song
        cursor.execute("SELECT COUNT(*) FROM mb_data_songs WHERE song_id = ?", (song_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"Song {song_id} already has relationship data. Skipping...")
            continue
        
        # Process relationships for this song
        process_relationships(song_id, mbid, cursor, conn)
        
        # Add a small delay to be nice to the MusicBrainz API
        time.sleep(1)
    
    # Close the database connection
    conn.close()
    print("Done!")

if __name__ == "__main__":
    main()