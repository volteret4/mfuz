import sqlite3
import requests
import time
import json
from datetime import datetime
import os
import argparse

# MusicBrainz API base URL
MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2"

# User agent is required by MusicBrainz API
USER_AGENT = "MyMusicApp/1.0 (your-email@example.com)"

# Rate limiting: MusicBrainz allows 1 request per second for authenticated users
# For non-authenticated users, it's best to keep it lower, like 1 request per 2 seconds
RATE_LIMIT = 2  # seconds between requests


def create_label_tables(db_path):
    """Create the necessary tables if they don't exist"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create the labels table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS labels (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        mbid TEXT UNIQUE,
        founded_year INTEGER,
        country TEXT,
        description TEXT,
        last_updated TIMESTAMP,
        
        official_website TEXT,
        wikipedia_url TEXT,
        wikipedia_content TEXT,
        wikipedia_updated TIMESTAMP,
        discogs_url TEXT,
        bandcamp_url TEXT,
        
        mb_type TEXT,
        mb_code TEXT,
        mb_last_updated TIMESTAMP
    )
    ''')
    
    # Create the label relationships table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS label_relationships (
        id INTEGER PRIMARY KEY,
        source_label_id INTEGER NOT NULL,
        target_label_id INTEGER NOT NULL,
        relationship_type TEXT NOT NULL,
        begin_date TEXT,
        end_date TEXT,
        last_updated TIMESTAMP,
        
        FOREIGN KEY (source_label_id) REFERENCES labels(id),
        FOREIGN KEY (target_label_id) REFERENCES labels(id)
    )
    ''')
    
    # Create the label-release relationships table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS label_release_relationships (
        id INTEGER PRIMARY KEY,
        label_id INTEGER NOT NULL,
        album_id INTEGER NOT NULL,
        relationship_type TEXT NOT NULL,
        catalog_number TEXT,
        begin_date TEXT,
        end_date TEXT,
        last_updated TIMESTAMP,
        
        FOREIGN KEY (label_id) REFERENCES labels(id),
        FOREIGN KEY (album_id) REFERENCES albums(id)
    )
    ''')
    
    conn.commit()
    conn.close()


def fetch_label_data(label_mbid):
    """
    Fetch label data from MusicBrainz API
    
    Args:
        label_mbid (str): MusicBrainz ID of the label
    
    Returns:
        dict: Label data
    """
    # Define the URL with all needed includes
    url = f"{MUSICBRAINZ_API_URL}/label/{label_mbid}"
    
    # Includes: label info, URLs, release relationships, label relationships
    params = {
        "inc": "url-rels+label-rels+release-rels",
        "fmt": "json"
    }
    
    headers = {
        "User-Agent": USER_AGENT
    }
    
    # Make the request
    response = requests.get(url, params=params, headers=headers)
    
    # Respect the rate limit
    time.sleep(RATE_LIMIT)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching label {label_mbid}: {response.status_code} - {response.text}")
        return None


def extract_label_info(label_data):
    """
    Extract relevant information from the API response
    
    Args:
        label_data (dict): Label data from MusicBrainz API
    
    Returns:
        tuple: (label_info, label_relationships, release_relationships)
    """
    label_info = {
        'mbid': label_data.get('id'),
        'name': label_data.get('name'),
        'country': label_data.get('country'),
        'mb_type': label_data.get('type'),
        'mb_code': label_data.get('label-code'),
        'founded_year': None,
        'official_website': None,
        'wikipedia_url': None,
        'discogs_url': None,
        'bandcamp_url': None,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'mb_last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Extract founding date if available
    if 'life-span' in label_data and 'begin' in label_data['life-span']:
        begin_date = label_data['life-span']['begin']
        if begin_date and len(begin_date) >= 4:
            try:
                label_info['founded_year'] = int(begin_date[:4])
            except ValueError:
                pass
    
    # Extract URLs
    if 'relations' in label_data:
        for relation in label_data['relations']:
            if relation['type'] == 'official homepage' and 'url' in relation:
                label_info['official_website'] = relation['url']['resource']
            elif relation['type'] == 'wikipedia' and 'url' in relation:
                label_info['wikipedia_url'] = relation['url']['resource']
            elif relation['type'] == 'discogs' and 'url' in relation:
                label_info['discogs_url'] = relation['url']['resource']
            elif relation['type'] == 'bandcamp' and 'url' in relation:
                label_info['bandcamp_url'] = relation['url']['resource']
    
    # Extract label relationships
    label_relationships = []
    if 'relations' in label_data:
        for relation in label_data['relations']:
            if relation['target-type'] == 'label':
                relationship = {
                    'source_mbid': label_data['id'],
                    'target_mbid': relation['label']['id'],
                    'relationship_type': relation['type'],
                    'begin_date': relation.get('begin') if 'begin' in relation else None,
                    'end_date': relation.get('end') if 'end' in relation else None
                }
                label_relationships.append(relationship)
    
    # Extract release relationships
    release_relationships = []
    if 'relations' in label_data:
        for relation in label_data['relations']:
            if relation['target-type'] == 'release':
                catalog_number = None
                for attribute in relation.get('attributes', []):
                    if attribute.startswith('catalog number:'):
                        catalog_number = attribute.split(':', 1)[1].strip()
                        break
                
                relationship = {
                    'label_mbid': label_data['id'],
                    'release_mbid': relation['release']['id'],
                    'relationship_type': relation['type'],
                    'catalog_number': catalog_number,
                    'begin_date': relation.get('begin') if 'begin' in relation else None,
                    'end_date': relation.get('end') if 'end' in relation else None
                }
                release_relationships.append(relationship)
    
    return label_info, label_relationships, release_relationships


def save_label_data(db_path, label_info, label_relationships, release_relationships):
    """
    Save the label data to the database
    
    Args:
        db_path (str): Path to SQLite database
        label_info (dict): Basic label information
        label_relationships (list): List of label relationships
        release_relationships (list): List of release relationships
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Insert or update label info
    cursor.execute('''
    INSERT OR REPLACE INTO labels (
        mbid, name, country, founded_year, 
        official_website, wikipedia_url, discogs_url, bandcamp_url,
        mb_type, mb_code, last_updated, mb_last_updated
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        label_info['mbid'], label_info['name'], label_info['country'], label_info['founded_year'],
        label_info['official_website'], label_info['wikipedia_url'], 
        label_info['discogs_url'], label_info['bandcamp_url'],
        label_info['mb_type'], label_info['mb_code'], 
        label_info['last_updated'], label_info['mb_last_updated']
    ))
    
    # Get the label ID
    cursor.execute("SELECT id FROM labels WHERE mbid = ?", (label_info['mbid'],))
    label_id = cursor.fetchone()[0]
    
    # Save label relationships
    for rel in label_relationships:
        # Get or create the target label
        cursor.execute("SELECT id FROM labels WHERE mbid = ?", (rel['target_mbid'],))
        result = cursor.fetchone()
        
        if result:
            target_id = result[0]
        else:
            # Insert a placeholder for the target label to be updated later
            cursor.execute('''
            INSERT INTO labels (mbid, name, last_updated)
            VALUES (?, ?, ?)
            ''', (rel['target_mbid'], f"Unknown (MusicBrainz ID: {rel['target_mbid']})", 
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            target_id = cursor.lastrowid
        
        # Insert the relationship
        cursor.execute('''
        INSERT OR REPLACE INTO label_relationships (
            source_label_id, target_label_id, relationship_type, 
            begin_date, end_date, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            label_id, target_id, rel['relationship_type'],
            rel['begin_date'], rel['end_date'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    # Save release relationships
    for rel in release_relationships:
        # Check if we have this release in our database
        cursor.execute("SELECT id FROM albums WHERE mbid = ?", (rel['release_mbid'],))
        result = cursor.fetchone()
        
        if result:
            album_id = result[0]
            
            # Insert the relationship
            cursor.execute('''
            INSERT OR REPLACE INTO label_release_relationships (
                label_id, album_id, relationship_type, catalog_number,
                begin_date, end_date, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                label_id, album_id, rel['relationship_type'], rel['catalog_number'],
                rel['begin_date'], rel['end_date'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
    
    conn.commit()
    conn.close()


def search_labels(query, limit=10):
    """
    Search for labels in MusicBrainz
    
    Args:
        query (str): Search query
        limit (int): Maximum number of results
    
    Returns:
        list: Label search results
    """
    url = f"{MUSICBRAINZ_API_URL}/label"
    
    params = {
        "query": query,
        "limit": limit,
        "fmt": "json"
    }
    
    headers = {
        "User-Agent": USER_AGENT
    }
    
    response = requests.get(url, params=params, headers=headers)
    
    # Respect the rate limit
    time.sleep(RATE_LIMIT)
    
    if response.status_code == 200:
        data = response.json()
        results = []
        
        if 'labels' in data:
            for label in data['labels']:
                results.append({
                    'mbid': label.get('id'),
                    'name': label.get('name'),
                    'country': label.get('country'),
                    'type': label.get('type')
                })
        
        return results
    else:
        print(f"Error searching for labels: {response.status_code} - {response.text}")
        return []


def fetch_label_by_album(db_path, album_mbid, existing_conn=None):
    """
    Fetch all labels associated with an album
    
    Args:
        db_path (str): Path to SQLite database
        album_mbid (str): MusicBrainz ID of the album
        existing_conn (sqlite3.Connection, optional): Existing database connection
    
    Returns:
        bool: Success status
    """
    url = f"{MUSICBRAINZ_API_URL}/release/{album_mbid}"
    
    params = {
        "inc": "labels",
        "fmt": "json"
    }
    
    headers = {
        "User-Agent": USER_AGENT
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        
        # Respect the rate limit
        time.sleep(RATE_LIMIT)
        
        if response.status_code != 200:
            print(f"Error fetching album {album_mbid}: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        
        # Determine if we should close the connection at the end
        should_close = existing_conn is None
        
        # Use existing connection or create a new one with longer timeout
        conn = existing_conn if existing_conn else sqlite3.connect(db_path, timeout=60)
        cursor = conn.cursor()
        
        try:
            # Get album ID from database
            cursor.execute("SELECT id FROM albums WHERE mbid = ?", (album_mbid,))
            result = cursor.fetchone()
            
            if not result:
                print(f"Album with MBID {album_mbid} not found in database")
                if should_close:
                    conn.close()
                return False
            
            album_id = result[0]
            
            # Process labels
            if 'label-info' in data:
                for label_info in data['label-info']:
                    if 'label' in label_info:
                        label_mbid = label_info['label']['id']
                        
                        # Check if we already have this label
                        cursor.execute("SELECT id FROM labels WHERE mbid = ?", (label_mbid,))
                        label_result = cursor.fetchone()
                        
                        label_id = None
                        if not label_result:
                            # Fetch and save the label
                            label_data = fetch_label_data(label_mbid)
                            if label_data:
                                label_info_dict, label_rels, release_rels = extract_label_info(label_data)
                                
                                # Insert the label with retry mechanism
                                retry_count = 0
                                max_retries = 3
                                while retry_count < max_retries:
                                    try:
                                        # Insert the label directly without relationships first
                                        cursor.execute('''
                                        INSERT OR REPLACE INTO labels (
                                            mbid, name, country, founded_year, 
                                            official_website, wikipedia_url, discogs_url, bandcamp_url,
                                            mb_type, mb_code, last_updated, mb_last_updated
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        ''', (
                                            label_info_dict['mbid'], label_info_dict['name'], 
                                            label_info_dict['country'], label_info_dict['founded_year'],
                                            label_info_dict['official_website'], label_info_dict['wikipedia_url'], 
                                            label_info_dict['discogs_url'], label_info_dict['bandcamp_url'],
                                            label_info_dict['mb_type'], label_info_dict['mb_code'], 
                                            label_info_dict['last_updated'], label_info_dict['mb_last_updated']
                                        ))
                                        conn.commit()
                                        break
                                    except sqlite3.OperationalError as e:
                                        if "database is locked" in str(e) and retry_count < max_retries - 1:
                                            retry_count += 1
                                            print(f"Database locked, retrying in {retry_count*2} seconds... (attempt {retry_count}/{max_retries})")
                                            time.sleep(retry_count * 2)
                                        else:
                                            print(f"Failed to insert label after {max_retries} attempts: {e}")
                                            raise
                                
                                # Get the new label ID
                                cursor.execute("SELECT id FROM labels WHERE mbid = ?", (label_mbid,))
                                label_result = cursor.fetchone()
                        
                        if label_result:
                            label_id = label_result[0]
                            
                            # Save the relationship with retry mechanism
                            if label_id and album_id:
                                catalog_number = label_info.get('catalog-number')
                                
                                max_retries = 3

                                retry_count = 0
                                while retry_count < max_retries:
                                    try:
                                        cursor.execute('''
                                        INSERT OR REPLACE INTO label_release_relationships (
                                            label_id, album_id, relationship_type, catalog_number, last_updated
                                        ) VALUES (?, ?, ?, ?, ?)
                                        ''', (
                                            label_id, album_id, 'published', catalog_number, 
                                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        ))
                                        conn.commit()
                                        break
                                    except sqlite3.OperationalError as e:
                                        if "database is locked" in str(e) and retry_count < max_retries - 1:
                                            retry_count += 1
                                            print(f"Database locked, retrying in {retry_count*2} seconds... (attempt {retry_count}/{max_retries})")
                                            time.sleep(retry_count * 2)
                                        else:
                                            print(f"Failed to insert relationship after {max_retries} attempts: {e}")
                                            raise
            
            if should_close:
                conn.close()
            return True
        
        except Exception as e:
            # Handle any other exceptions
            print(f"Error processing album {album_mbid}: {str(e)}")
            if should_close:
                try:
                    conn.close()
                except:
                    pass
            return False
    
    except Exception as e:
        print(f"Exception during API request for album {album_mbid}: {str(e)}")
        return False



def update_all_albums_with_labels(db_path):
    """
    Update all albums in the database with label information
    
    Args:
        db_path (str): Path to SQLite database
    """
    # Enable WAL mode for better concurrency
    conn = sqlite3.connect(db_path, timeout=60)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=60000")  # 60 second timeout
        
        cursor = conn.cursor()
        
        # Get all albums with MusicBrainz IDs
        cursor.execute("SELECT id, mbid FROM albums WHERE mbid IS NOT NULL")
        albums = cursor.fetchall()
        
        total = len(albums)
        print(f"Found {total} albums with MusicBrainz IDs")
        
        for i, (album_id, album_mbid) in enumerate(albums):
            print(f"Processing album {i+1}/{total}: {album_mbid}")
            try:
                success = fetch_label_by_album(db_path, album_mbid, conn)
                if not success:
                    print(f"Skipping album {album_mbid} due to errors")
            except Exception as e:
                print(f"Error processing album {album_mbid}: {str(e)}")
                # Continue with next album
    finally:
        try:
            conn.close()
        except:
            pass


def main(config=None):
    parser = argparse.ArgumentParser(description='Extract MusicBrainz links and reviews for albums')
    parser.add_argument('--config', help='Path to json config ')
    parser.add_argument('--db-path', help='Path to the SQLite database')

    args = parser.parse_args()


        
    with open(args.config, 'r') as f:
        config_data = json.load(f)
        
    # Combinar configuraciones
    config = {}
    config.update(config_data.get("common", {}))
    config.update(config_data.get("mb_sellos", {}))

    db_path = args.db_path or config['db_path']

    if not db_path:
        db_path = input("Enter the path to your SQLite database file: ")
        if not os.path.exists(db_path):
            print(f"Database file {db_path} doesn't exist.")
            return
        conn = sqlite3.connect(db_path)

    create_label_tables(db_path)
    
    while True:
        print("\nMusicBrainz Label Data Fetcher")
        print("1. Search for a label")
        print("2. Fetch label by MusicBrainz ID")
        print("3. Fetch labels for an album")
        print("4. Update all albums with label information")
        print("5. Exit")
        
        choice = input("Enter your choice (1-5): ")
        
        if choice == '1':
            query = input("Enter search query: ")
            results = search_labels(query)
            
            if results:
                print("\nSearch results:")
                for i, result in enumerate(results):
                    print(f"{i+1}. {result['name']} ({result.get('country', 'Unknown')}) - {result['mbid']}")
                
                fetch_choice = input("\nEnter number to fetch details (or 0 to return to menu): ")
                if fetch_choice.isdigit() and 1 <= int(fetch_choice) <= len(results):
                    label_mbid = results[int(fetch_choice)-1]['mbid']
                    label_data = fetch_label_data(label_mbid)
                    
                    if label_data:
                        label_info, label_rels, release_rels = extract_label_info(label_data)
                        save_label_data(db_path, label_info, label_rels, release_rels)
                        print(f"Successfully saved label: {label_info['name']}")
            else:
                print("No results found.")
        
        elif choice == '2':
            label_mbid = input("Enter MusicBrainz ID: ")
            label_data = fetch_label_data(label_mbid)
            
            if label_data:
                label_info, label_rels, release_rels = extract_label_info(label_data)
                save_label_data(db_path, label_info, label_rels, release_rels)
                print(f"Successfully saved label: {label_info['name']}")
            else:
                print("Label not found or error fetching data.")
        
        elif choice == '3':
            album_mbid = input("Enter album MusicBrainz ID: ")
            result = fetch_label_by_album(db_path, album_mbid)
            
            if result:
                print("Successfully processed album labels.")
            else:
                print("Error processing album.")
        
        elif choice == '4':
            confirm = input("This will update all albums with label information. This may take a while. Continue? (y/n): ")
            if confirm.lower() == 'y':
                update_all_albums_with_labels(db_path)
                print("All albums updated with label information.")
        
        elif choice == '5':
            break
        
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()