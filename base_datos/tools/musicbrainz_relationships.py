#!/usr/bin/env python3
import argparse
import sqlite3
import requests
import json
import time
import sys
from bs4 import BeautifulSoup
from readability import Document
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mb_links_extractor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2"
USER_AGENT = "MusicbrainzLinksExtractor/1.0 (your-email@example.com)"  # Replace with your email
RATE_LIMIT_SLEEP = 1.1  # MusicBrainz requires at least 1 second between requests

# Release relationship types to extract
RELEASE_REL_TYPES = [
    "covers", 
    "transl-tracklisting", 
    "remaster", 
    "replaced-by", 
    "part-of-set"
]

# Recording relationship types to extract
RECORDING_REL_TYPES = [
    "samples-material"
]

# Create database tables if they don't exist
def setup_database(conn):
    cursor = conn.cursor()
    
    # Create album_links table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS album_links (
        id INTEGER PRIMARY KEY,
        album_id INTEGER NOT NULL,
        service_name TEXT NOT NULL,
        url TEXT NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (album_id) REFERENCES albums(id)
    )
    ''')
    
    # Create album_reviews table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS album_reviews (
        id INTEGER PRIMARY KEY,
        album_id INTEGER NOT NULL,
        source TEXT NOT NULL,
        content TEXT NOT NULL,
        url TEXT NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (album_id) REFERENCES albums(id)
    )
    ''')
    
    # Create album_relationships table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS album_relationships (
        id INTEGER PRIMARY KEY,
        album_id INTEGER NOT NULL,
        relationship_type TEXT NOT NULL,
        related_mbid TEXT NOT NULL,
        related_name TEXT NOT NULL,
        direction TEXT NOT NULL,  -- 'forward' or 'backward'
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (album_id) REFERENCES albums(id)
    )
    ''')
    
    conn.commit()
    logger.info("Database tables set up successfully")

# Get albums with MBIDs that need processing
def get_albums_to_process(conn, force_update=False):
    cursor = conn.cursor()
    
    if force_update:
        # Get all albums with valid MBIDs
        cursor.execute('''
        SELECT id, name, mbid FROM albums 
        WHERE mbid IS NOT NULL AND mbid != ''
        ''')
        logger.info("Force update enabled - processing all albums with valid MBIDs")
    else:
        # Get only albums that don't have data in all three tables
        cursor.execute('''
        SELECT id, name, mbid FROM albums 
        WHERE mbid IS NOT NULL AND mbid != '' AND (
            id NOT IN (SELECT DISTINCT album_id FROM album_links) OR
            id NOT IN (SELECT DISTINCT album_id FROM album_reviews) OR
            id NOT IN (SELECT DISTINCT album_id FROM album_relationships)
        )
        ''')
        logger.info("Processing only albums with missing data")
    
    return cursor.fetchall()

# Check which data types are missing for an album
def check_missing_data(conn, album_id):
    cursor = conn.cursor()
    missing_data = {
        'links': False,
        'reviews': False,
        'relationships': False
    }
    
    # Check album_links
    cursor.execute('SELECT COUNT(*) FROM album_links WHERE album_id = ?', (album_id,))
    if cursor.fetchone()[0] == 0:
        missing_data['links'] = True
    
    # Check album_reviews
    cursor.execute('SELECT COUNT(*) FROM album_reviews WHERE album_id = ?', (album_id,))
    if cursor.fetchone()[0] == 0:
        missing_data['reviews'] = True
    
    # Check album_relationships
    cursor.execute('SELECT COUNT(*) FROM album_relationships WHERE album_id = ?', (album_id,))
    if cursor.fetchone()[0] == 0:
        missing_data['relationships'] = True
    
    return missing_data

# Query MusicBrainz API for album relationships
def query_musicbrainz(mbid):
    # Include release-rels and recording-rels in addition to url-rels
    url = f"{MUSICBRAINZ_API_URL}/release/{mbid}?inc=url-rels+release-rels+recording-rels&fmt=json"
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to fetch data for MBID {mbid}. Status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching data for MBID {mbid}: {str(e)}")
        return None

# Process and extract URL relationships from MusicBrainz data
def extract_url_relationships(mb_data):
    links = []
    review_links = []
    
    if not mb_data or 'relations' not in mb_data:
        return links, review_links
    
    for relation in mb_data['relations']:
        if relation.get('target-type') == 'url':
            if relation['type'] == 'review':
                review_links.append({
                    'service_name': relation.get('type-id', 'review'),
                    'url': relation['url']['resource']
                })
            else:
                service_name = relation['type']
                if 'url' in relation and 'resource' in relation['url']:
                    links.append({
                        'service_name': service_name,
                        'url': relation['url']['resource']
                    })
    
    return links, review_links

# Extract release-to-release relationships
def extract_release_relationships(mb_data):
    relationships = []
    
    if not mb_data or 'relations' not in mb_data:
        return relationships
    
    for relation in mb_data['relations']:
        if relation.get('target-type') == 'release' and relation['type'] in RELEASE_REL_TYPES:
            relationships.append({
                'type': relation['type'],
                'direction': 'forward',
                'mbid': relation['release']['id'],
                'name': relation['release'].get('title', 'Unknown Release')
            })
    
    return relationships

# Extract recording-to-release relationships
def extract_recording_relationships(mb_data):
    relationships = []
    
    if not mb_data or 'relations' not in mb_data:
        return relationships
    
    for relation in mb_data['relations']:
        if relation.get('target-type') == 'recording' and relation['type'] in RECORDING_REL_TYPES:
            relationships.append({
                'type': relation['type'],
                'direction': 'backward',  # the recording samples from this release
                'mbid': relation['recording']['id'],
                'name': relation['recording'].get('title', 'Unknown Recording')
            })
    
    return relationships

# Extract review content using readability
def extract_review_content(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            doc = Document(response.text)
            title = doc.title()
            content = doc.summary()
            
            # Use BeautifulSoup to extract clean text
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text(separator=' ', strip=True)
            
            return text_content
        else:
            logger.warning(f"Failed to fetch review from {url}. Status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error extracting review from {url}: {str(e)}")
        return None

# Save links to the database
def save_links(conn, album_id, links):
    cursor = conn.cursor()
    for link in links:
        try:
            cursor.execute('''
            INSERT INTO album_links (album_id, service_name, url)
            VALUES (?, ?, ?)
            ''', (album_id, link['service_name'], link['url']))
        except sqlite3.Error as e:
            logger.error(f"Error saving link for album ID {album_id}: {str(e)}")
    
    conn.commit()
    logger.info(f"Saved {len(links)} links for album ID {album_id}")

# Save review to the database
def save_review(conn, album_id, source, content, url):
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO album_reviews (album_id, source, content, url)
        VALUES (?, ?, ?, ?)
        ''', (album_id, source, content, url))
        conn.commit()
        logger.info(f"Saved review for album ID {album_id} from {source}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error saving review for album ID {album_id}: {str(e)}")
        conn.rollback()
        return False

# Save relationships to the database
def save_relationships(conn, album_id, relationships):
    cursor = conn.cursor()
    saved_count = 0
    
    for rel in relationships:
        try:
            cursor.execute('''
            INSERT INTO album_relationships (album_id, relationship_type, related_mbid, related_name, direction)
            VALUES (?, ?, ?, ?, ?)
            ''', (album_id, rel['type'], rel['mbid'], rel['name'], rel['direction']))
            saved_count += 1
        except sqlite3.Error as e:
            logger.error(f"Error saving relationship for album ID {album_id}: {str(e)}")
    
    conn.commit()
    logger.info(f"Saved {saved_count} relationships for album ID {album_id}")

# Process a single album
def process_album(conn, album_id, album_name, mbid, interactive):
    # Check what data is missing for this album
    missing_data = check_missing_data(conn, album_id)
    
    logger.info(f"Processing album: {album_name} (MBID: {mbid})")
    logger.info(f"Missing data: Links: {missing_data['links']}, Reviews: {missing_data['reviews']}, Relationships: {missing_data['relationships']}")
    
    # If all data is present, skip processing
    if not any(missing_data.values()):
        logger.info(f"Album {album_name} already has all data. Skipping.")
        return
    
    # Query MusicBrainz API
    mb_data = query_musicbrainz(mbid)
    if not mb_data:
        logger.warning(f"No data found for album {album_name}")
        return
    
    # Extract and save only the missing data
    if missing_data['links'] or missing_data['reviews']:
        # Extract URL relationships
        links, review_links = extract_url_relationships(mb_data)
        
        # Save regular links if missing
        if missing_data['links'] and links:
            save_links(conn, album_id, links)
        
        # Process reviews if missing
        if missing_data['reviews'] and review_links:
            for review in review_links:
                service_name = review['service_name']
                url = review['url']
                
                logger.info(f"Extracting review from {url}")
                review_content = extract_review_content(url)
                
                if not review_content:
                    logger.warning(f"Could not extract review content from {url}")
                    continue
                
                if interactive:
                    print("\n" + "="*80)
                    print(f"REVIEW FOR: {album_name}")
                    print(f"SOURCE: {url}")
                    print("="*80)
                    print(review_content[:500] + "..." if len(review_content) > 500 else review_content)
                    print("\n" + "="*80)
                    
                    save_it = input("Save this review? (y/n): ").strip().lower()
                    if save_it == 'y':
                        save_review(conn, album_id, service_name, review_content, url)
                    else:
                        logger.info(f"Review from {url} skipped by user")
                else:
                    save_review(conn, album_id, service_name, review_content, url)
    
    # Extract and save relationships if missing
    if missing_data['relationships']:
        # Extract release and recording relationships
        release_relationships = extract_release_relationships(mb_data)
        recording_relationships = extract_recording_relationships(mb_data)
        
        # Combine all relationship types
        all_relationships = release_relationships + recording_relationships
        
        # Save relationships
        if all_relationships:
            save_relationships(conn, album_id, all_relationships)
    
    # Rate limiting for MusicBrainz API
    time.sleep(RATE_LIMIT_SLEEP)

# Display album relationship information
def display_relationships(conn):
    cursor = conn.cursor()
    cursor.execute('''
    SELECT a.name, ar.relationship_type, ar.related_name, ar.direction
    FROM album_relationships ar
    JOIN albums a ON ar.album_id = a.id
    LIMIT 10
    ''')
    rows = cursor.fetchall()
    
    if not rows:
        print("No album relationships found in the database.")
        return
    
    print("\n" + "="*100)
    print("SAMPLE ALBUM RELATIONSHIPS")
    print("="*100)
    for row in rows:
        album_name, rel_type, related_name, direction = row
        if direction == 'forward':
            print(f"{album_name} → {rel_type} → {related_name}")
        else:
            print(f"{album_name} ← {rel_type} ← {related_name}")
    print("="*100)

# Show database statistics
def show_database_stats(conn):
    cursor = conn.cursor()
    
    # Count total albums
    cursor.execute('SELECT COUNT(*) FROM albums WHERE mbid IS NOT NULL AND mbid != ""')
    total_albums = cursor.fetchone()[0]
    
    # Count albums with links
    cursor.execute('SELECT COUNT(DISTINCT album_id) FROM album_links')
    albums_with_links = cursor.fetchone()[0]
    
    # Count albums with reviews
    cursor.execute('SELECT COUNT(DISTINCT album_id) FROM album_reviews')
    albums_with_reviews = cursor.fetchone()[0]
    
    # Count albums with relationships
    cursor.execute('SELECT COUNT(DISTINCT album_id) FROM album_relationships')
    albums_with_relationships = cursor.fetchone()[0]
    
    # Count albums with all data types
    cursor.execute('''
    SELECT COUNT(*) FROM (
        SELECT a.id 
        FROM albums a
        WHERE a.mbid IS NOT NULL AND a.mbid != ""
        AND EXISTS (SELECT 1 FROM album_links WHERE album_id = a.id)
        AND EXISTS (SELECT 1 FROM album_reviews WHERE album_id = a.id)
        AND EXISTS (SELECT 1 FROM album_relationships WHERE album_id = a.id)
    )
    ''')
    albums_complete = cursor.fetchone()[0]
    
    # Print stats
    print("\n" + "="*80)
    print("DATABASE STATISTICS")
    print("="*80)
    print(f"Total albums with MBIDs: {total_albums}")
    print(f"Albums with links: {albums_with_links} ({albums_with_links/total_albums*100:.1f}%)")
    print(f"Albums with reviews: {albums_with_reviews} ({albums_with_reviews/total_albums*100:.1f}%)")
    print(f"Albums with relationships: {albums_with_relationships} ({albums_with_relationships/total_albums*100:.1f}%)")
    print(f"Albums with complete data: {albums_complete} ({albums_complete/total_albums*100:.1f}%)")
    print(f"Albums missing data: {total_albums - albums_complete}")
    print("="*80)

# Main function
def main():
    parser = argparse.ArgumentParser(description='Extract MusicBrainz links, relationships, and reviews for albums')
    parser.add_argument('--db-path', required=True, help='Path to the SQLite database')
    parser.add_argument('--interactive', action='store_true', help='Show reviews before saving for validation')
    parser.add_argument('--show-relations', action='store_true', help='Display a sample of extracted relationships')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--force-update', action='store_true', help='Force update all albums, even those with existing data')
    
    args = parser.parse_args()
    
    try:
        conn = sqlite3.connect(args.db_path)
        setup_database(conn)
        
        if args.stats:
            show_database_stats(conn)
        
        albums = get_albums_to_process(conn, args.force_update)
        logger.info(f"Found {len(albums)} albums to process")
        
        for album_id, album_name, mbid in albums:
            process_album(conn, album_id, album_name, mbid, args.interactive)
        
        if args.show_relations:
            display_relationships(conn)
        
        # Show updated stats if requested
        if args.stats:
            show_database_stats(conn)
        
        logger.info("Processing completed successfully")
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()