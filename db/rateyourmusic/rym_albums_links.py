import requests
from time import sleep
from urllib.parse import quote
import sqlite3
from bs4 import BeautifulSoup
import re

def process_artist(artist_id, artist_name, config, conn):
    log_level = config.get('log_level', 'INFO')
    
    print(f"[DEBUG] Processing artist ID: {artist_id}, Name: {artist_name}")
    print(f"[DEBUG] Database path: {config.get('db_path', 'NOT SPECIFIED')}")
    
    cursor = conn.cursor()
    
    # Debug: Check if artist exists and count their albums in musicbrainz_discography
    cursor.execute("SELECT COUNT(*) FROM musicbrainz_discography WHERE artist_id = ?", (artist_id,))
    mb_album_count = cursor.fetchone()[0]
    print(f"[DEBUG] Artist {artist_name} has {mb_album_count} albums in musicbrainz_discography")
    
    # Debug: Check current RYM albums for this artist
    cursor.execute("""
        SELECT COUNT(*) FROM rym_albums ra 
        WHERE ra.artist_id = ?
    """, (artist_id,))
    existing_rym_count = cursor.fetchone()[0]
    print(f"[DEBUG] Artist {artist_name} already has {existing_rym_count} RYM albums in database")
    
    # Search for artist's albums on RateYourMusic via Searx
    encoded_artist = quote(artist_name)
    search_url = f"{config['searxng_url']}/search?q=!go+site%3Drateyourmusic.com%2Frelease%2Fep%2F{encoded_artist}+{encoded_artist}"
    
    print(f"[DEBUG] Search URL: {search_url}")

    albums_found = 0
    page = 1
    pages_without_results = 0
    max_pages_without_results = 5
    
    while pages_without_results < max_pages_without_results:
        try:
            # Construct URL for current page
            if page == 1:
                current_url = search_url
            else:
                current_url = f"{search_url}&pageno={page}"
            
            print(f"[DEBUG] Making request to Searx page {page}: {current_url}")
            response = requests.get(current_url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML content instead of JSON
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all result links that point to RateYourMusic
            results = []
            processed_base_urls = set()  # To avoid duplicates
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'rateyourmusic.com/release/' in href:
                            # Clean and normalize the URL
                            try:
                                # Remove any query parameters and fragments
                                clean_url = href.split('?')[0].split('#')[0]
                                
                                # Normalize different language domains to main domain
                                clean_url = re.sub(r'://\w{2}\.rateyourmusic\.com', '://rateyourmusic.com', clean_url)

                                
                                # Split URL to get parts
                                url_parts = clean_url.rstrip('/').split('/')
                                
                                # Find the release part and extract base URL
                                release_index = -1
                                for i, part in enumerate(url_parts):
                                    if part == 'release':
                                        release_index = i
                                        break
                                
                                if release_index >= 0 and release_index + 3 < len(url_parts):
                                    # Extract only the base album URL: /release/type/artist/album
                                    base_parts = url_parts[:release_index + 4]  # Keep only up to album name
                                    base_url = '/'.join(base_parts) + '/'
                                    
                                    # Ensure it's a proper album URL (not reviews, charts, etc.)
                                    if len(base_parts) == release_index + 4:  # Exactly the right number of parts
                                        # Only add if we haven't seen this base URL before
                                        if base_url not in processed_base_urls:
                                            processed_base_urls.add(base_url)
                                            results.append({'url': base_url})
                                            if href != base_url:
                                                print(f"[DEBUG] Normalized URL: {href} -> {base_url}")
                                        else:
                                            print(f"[DEBUG] Skipping duplicate base URL: {base_url}")
                                    else:
                                        print(f"[DEBUG] Skipping non-base URL: {href}")
                                else:
                                    print(f"[DEBUG] Malformed URL structure, skipping: {href}")
                            except Exception as e:
                                print(f"[DEBUG] Error processing URL {href}: {e}")
                                continue
            
            print(f"[DEBUG] Page {page}: Found {len(results)} unique RYM links in HTML")
            
            if len(results) == 0:
                pages_without_results += 1
                print(f"[DEBUG] No results on page {page}. Pages without results: {pages_without_results}/{max_pages_without_results}")
            else:
                pages_without_results = 0  # Reset counter when we find results
                
                # Process results from this page
                page_albums_found = 0
                for i, result in enumerate(results):
                    rym_url = result.get('url', '')
                    print(f"[DEBUG] Page {page}, processing result {i+1}: {rym_url}")
                    
                    if not rym_url or 'rateyourmusic.com/release/' not in rym_url:
                        print(f"[DEBUG] Skipping invalid URL: {rym_url}")
                        continue
                        
                    try:
                        path_parts = rym_url.rstrip('/').split('/')  # Remove trailing slash before split
                        # Should be: ['https:', '', 'rateyourmusic.com', 'release', 'type', 'artist', 'album']
                        if len(path_parts) >= 7 and path_parts[4] in ['ep', 'album', 'single']:
                            # Extract album name from URL (last part, replace hyphens with spaces)
                            album_name_from_url = path_parts[6].replace('-', ' ').replace('_', ' ')
                            print(f"[DEBUG] Extracted album name from URL: {album_name_from_url}")
                            
                            # Try to find matching album in musicbrainz_discography
                            cursor.execute("""
                                SELECT md.album_id, md.title, a.name as album_name_in_albums
                                FROM musicbrainz_discography md
                                LEFT JOIN albums a ON md.album_id = a.id
                                WHERE md.artist_id = ? AND (
                                    LOWER(md.title) = LOWER(?) OR
                                    LOWER(md.title) LIKE LOWER(?) OR
                                    LOWER(?) LIKE LOWER('%' || md.title || '%')
                                )
                                LIMIT 1
                            """, (artist_id, album_name_from_url, f'%{album_name_from_url}%', album_name_from_url))
                            
                            album = cursor.fetchone()
                            
                            if album:
                                album_id = album[0]
                                mb_title = album[1]
                                album_name_in_albums = album[2] if album[2] else mb_title
                                print(f"[DEBUG] Found matching album in musicbrainz_discography: album_id={album_id}, mb_title={mb_title}")
                                
                                # Check if this exact URL already exists (regardless of album_id)
                                cursor.execute("SELECT id, album_id FROM rym_albums WHERE rym_url = ?", (rym_url,))
                                existing_url = cursor.fetchone()
                                
                                if existing_url:
                                    print(f"[DEBUG] URL already exists (ID: {existing_url[0]}, album_id: {existing_url[1]}) - skipping: {rym_url}")
                                    continue
                                
                                # Also check if this album_id already has ANY RYM URL
                                cursor.execute("SELECT id, rym_url FROM rym_albums WHERE album_id = ?", (album_id,))
                                existing_album = cursor.fetchone()
                                
                                if existing_album:
                                    print(f"[DEBUG] Album {album_name_in_albums} already has RYM URL (ID: {existing_album[0]}): {existing_album[1]} - skipping new URL: {rym_url}")
                                    continue
                                
                                # If we get here, neither the URL nor the album_id exist
                                print(f"[DEBUG] Inserting new RYM album: album_id={album_id}, artist_id={artist_id}, url={rym_url}")
                                try:
                                    # Insert new album URL with artist_id and timestamp
                                    cursor.execute("""
                                        INSERT INTO rym_albums (album_id, artist_id, rym_url, actualizado) 
                                        VALUES (?, ?, ?, datetime('now'))
                                    """, (album_id, artist_id, rym_url))
                                    conn.commit()  # Commit immediately after each insertion
                                    albums_found += 1
                                    page_albums_found += 1
                                    
                                    print(f"[SUCCESS] Added {album_name_in_albums} (MB: {mb_title}) - {rym_url}")
                                except sqlite3.IntegrityError as e:
                                    print(f"[WARNING] Failed to insert due to constraint violation: {e} - URL: {rym_url}")
                                    continue
                            else:
                                print(f"[DEBUG] No matching album found in musicbrainz_discography for: {album_name_from_url}")
                        else:
                            print(f"[DEBUG] Invalid URL structure after cleaning: {rym_url}")
                                
                    except (IndexError, ValueError) as e:
                        print(f"[ERROR] Error processing URL {rym_url}: {e}")
                        continue
                        
                    # Check limit per artist
                    if config.get('limit') and config['limit'] != 'None' and albums_found >= int(config['limit']):
                        print(f"[DEBUG] Limit of {config['limit']} albums reached for {artist_name}.")
                        break
                
                print(f"[DEBUG] Page {page} completed: {page_albums_found} albums found")
                
                # Check if we should stop based on limit
                if config.get('limit') and config['limit'] != 'None' and albums_found >= int(config['limit']):
                    break
            
            # Move to next page
            page += 1
            sleep(config['delay'])
            
        except Exception as e:
            print(f"[DEBUG] Request failed on page {page}: {e}. Skipping page.")
            page += 1
            sleep(config['delay'])
    
    if pages_without_results >= max_pages_without_results:
        print(f"[DEBUG] Stopped searching after {max_pages_without_results} consecutive pages without results")
    
    print(f"[RESULT] Found {albums_found} new RYM albums for {artist_name}")
    
    sleep(config['delay'])
    
    return albums_found

def main(config):
    # Connect to SQLite DB 
    print(f"[DEBUG] Connecting to database: {config['db_path']}")
    
    try:
        conn = sqlite3.connect(config['db_path'])
        cursor = conn.cursor()
        print(f"[DEBUG] Successfully connected to database")
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        return

    # Debug: Check database structure
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('artists', 'albums', 'rym_albums', 'musicbrainz_discography')")
    tables = cursor.fetchall()
    print(f"[DEBUG] Found tables: {[t[0] for t in tables]}")
    
    # Check and update rym_albums table structure
    cursor.execute("PRAGMA table_info(rym_albums)")
    rym_table_info = cursor.fetchall()
    column_names = [col[1] for col in rym_table_info]
    print(f"[DEBUG] rym_albums current columns: {column_names}")
    
    # Add missing columns if they don't exist
    if 'artist_id' not in column_names:
        print("[DEBUG] Adding artist_id column to rym_albums table")
        cursor.execute("ALTER TABLE rym_albums ADD COLUMN artist_id INTEGER")
        conn.commit()
    
    if 'actualizado' not in column_names:
        print("[DEBUG] Adding actualizado column to rym_albums table")
        # SQLite doesn't allow CURRENT_TIMESTAMP as default when adding column to existing table
        cursor.execute("ALTER TABLE rym_albums ADD COLUMN actualizado TIMESTAMP")
        conn.commit()
        
        # Update existing rows to have a timestamp
        cursor.execute("UPDATE rym_albums SET actualizado = CURRENT_TIMESTAMP WHERE actualizado IS NULL")
        conn.commit()
        print("[DEBUG] Updated existing rows with current timestamp")
    
    # Create unique index for URL if it doesn't exist
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_rym_albums_url ON rym_albums(rym_url)")
        conn.commit()
        print("[DEBUG] Created unique index for rym_url")
    except Exception as e:
        print(f"[DEBUG] Index creation skipped or failed: {e}")
    
    # Get updated table structure
    cursor.execute("PRAGMA table_info(rym_albums)")
    rym_table_info_updated = cursor.fetchall()
    print(f"[DEBUG] rym_albums final structure: {rym_table_info_updated}")

    # Retrieve all artists
    cursor.execute("SELECT COUNT(*) FROM artists")
    total_artists = cursor.fetchone()[0]
    print(f"[DEBUG] Total artists in database: {total_artists}")
    
    cursor.execute("SELECT id, name FROM artists LIMIT 5")
    sample_artists = cursor.fetchall()
    print(f"[DEBUG] Sample artists: {sample_artists}")

    # Get configuration details
    limit = config.get('limit', 'None')
    skip_existing = config.get('skip_existing', True)
    print(f"[DEBUG] Configuration - limit: {limit}, skip_existing: {skip_existing}")

    # Retrieve all artists (or filtered based on config)
    if skip_existing:
        # Only process artists that don't have any RYM albums yet and have albums in musicbrainz_discography
        cursor.execute("""
            SELECT a.id, a.name 
            FROM artists a
            JOIN musicbrainz_discography md ON a.id = md.artist_id
            LEFT JOIN rym_albums ra ON a.id = ra.artist_id
            WHERE ra.id IS NULL
            GROUP BY a.id, a.name
        """)
        print("[DEBUG] Using skip_existing filter - only artists with musicbrainz_discography but without RYM albums")
    else:
        # Process all artists that have albums in musicbrainz_discography
        cursor.execute("""
            SELECT DISTINCT a.id, a.name 
            FROM artists a
            JOIN musicbrainz_discography md ON a.id = md.artist_id
        """)
        print("[DEBUG] Processing all artists that have albums in musicbrainz_discography")
    
    artists = cursor.fetchall()
    print(f"[DEBUG] Artists to process: {len(artists)}")

    if len(artists) == 0:
        print("[WARNING] No artists to process!")
        conn.close()
        return

    # Process artists
    processed_count = 0
    total_albums_found = 0
    
    for artist_id, artist_name in artists:
        print(f"\n[DEBUG] === Processing artist {processed_count + 1}/{len(artists)} ===")
        
        # Process each artist individually
        albums_found = process_artist(artist_id, artist_name, config, conn)
        total_albums_found += albums_found
        processed_count += 1
        
        # Check if we should stop based on limit
        if limit and limit != 'None' and processed_count >= int(limit):
            print(f"[DEBUG] Reached processing limit of {limit} artists")
            break

    print(f"\n[FINAL RESULT] Processed {processed_count} artists, found {total_albums_found} total RYM albums")
    conn.close()