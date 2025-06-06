import sqlite3
import requests
import time
import json
from datetime import datetime
import os
import argparse
import traceback
from bs4 import BeautifulSoup
from urllib.parse import quote
import sys

# MusicBrainz API base URL
MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2"

# User agent is required by MusicBrainz API
USER_AGENT = "MyMusicApp/1.0 (frodobolson@disroot.org)"

# Rate limiting: MusicBrainz allows 1 request per second for authenticated users
# For non-authenticated users, it's best to keep it lower, like 1 request per 2 seconds
RATE_LIMIT = 1.1  # seconds between requests



def create_label_tables(db_path):
    """Create the necessary tables if they don't exist and add any missing columns"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # First check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='labels'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Create the labels table with all necessary fields
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
                lastfm_url TEXT,
                
                mb_type TEXT,
                mb_code TEXT,
                mb_last_updated TIMESTAMP,
                
                profile TEXT,
                parent_label TEXT,
                parent_label_id INTEGER,
                contact_info TEXT,
                
                social_links TEXT,
                streaming_links TEXT,
                purchase_links TEXT,
                blog_links TEXT,
                
                founder_info TEXT,
                creative_persons TEXT,
                signed_artists TEXT,
                subsidiary_labels TEXT,
                
                FOREIGN KEY (parent_label_id) REFERENCES labels(id)
            )
            ''')
        else:
            # Check if we need to add any columns to the existing table
            cursor.execute("PRAGMA table_info(labels)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # List of columns that might need to be added
            columns_to_check = {
                'wikipedia_content': 'TEXT',
                'wikipedia_updated': 'TIMESTAMP',
                'profile': 'TEXT',
                'parent_label': 'TEXT',
                'contact_info': 'TEXT',
                'social_links': 'TEXT',
                'streaming_links': 'TEXT',
                'purchase_links': 'TEXT',
                'blog_links': 'TEXT',
                'founder_info': 'TEXT',
                'creative_persons': 'TEXT',
                'signed_artists': 'TEXT',
                'subsidiary_labels': 'TEXT',
                'lastfm_url': 'TEXT'
            }
            
            # Add any missing columns
            for col_name, col_type in columns_to_check.items():
                if col_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE labels ADD COLUMN {col_name} {col_type}")
                        print(f"Added missing column '{col_name}' to labels table")
                    except sqlite3.OperationalError as e:
                        print(f"Error adding column {col_name}: {e}")
        
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
        
        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_labels_mbid ON labels(mbid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_labels_name ON labels(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_label_relationships_source ON label_relationships(source_label_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_label_relationships_target ON label_relationships(target_label_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_label_release_relationships_label ON label_release_relationships(label_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_label_release_relationships_album ON label_release_relationships(album_id)")
        
        # Optional: Add an artist-label relationships table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS label_artist_relationships (
            id INTEGER PRIMARY KEY,
            label_id INTEGER NOT NULL,
            artist_id INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            begin_date TEXT,
            end_date TEXT,
            last_updated TIMESTAMP,
            
            FOREIGN KEY (label_id) REFERENCES labels(id),
            FOREIGN KEY (artist_id) REFERENCES artists(id)
        )
        ''')
        
        # Optional: Create a table for external catalog entities (those not in our DB)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS label_external_catalog (
            id INTEGER PRIMARY KEY,
            label_id INTEGER NOT NULL,
            entity_type TEXT NOT NULL,  -- 'artist', 'album', etc.
            entity_mbid TEXT,
            entity_name TEXT,
            relationship_type TEXT,
            last_updated TIMESTAMP,
            
            FOREIGN KEY (label_id) REFERENCES labels(id)
        )
        ''')
        
        conn.commit()
        #conn.close()
        print("Label tables created or updated successfully")
        
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
        #conn.close()

def update_existing_labels(db_path):
    """
    Actualiza las etiquetas existentes que puedan tener información incompleta
    
    Args:
        db_path (str): Ruta a la base de datos SQLite
    """
    conn = sqlite3.connect(db_path, timeout=60)
    try:
        cursor = conn.cursor()
        
        # Obtener todas las etiquetas que tienen URL pero no contenido
        cursor.execute("""
        SELECT id, mbid, name, wikipedia_url, discogs_url 
        FROM labels 
        WHERE (wikipedia_url IS NOT NULL AND wikipedia_content IS NULL) 
           OR (discogs_url IS NOT NULL AND profile IS NULL)
        """)
        
        labels = cursor.fetchall()
        total = len(labels)
        
        if total == 0:
            print("No se encontraron etiquetas que necesiten actualización.")
            return
            
        print(f"Encontradas {total} etiquetas para actualizar.")
        
        for i, (label_id, mbid, name, wikipedia_url, discogs_url) in enumerate(labels):
            print(f"Procesando etiqueta {i+1}/{total}: {name} (MBID: {mbid})")
            
            # Verificar y actualizar contenido de Wikipedia
            if wikipedia_url and (wikipedia_url.strip() != ""):
                try:
                    print(f"Buscando contenido de Wikipedia para: {name}")
                    content = get_wikipedia_content(wikipedia_url)
                    if content:
                        cursor.execute("""
                        UPDATE labels SET 
                            wikipedia_content = ?, 
                            wikipedia_updated = ? 
                        WHERE id = ?
                        """, (content, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), label_id))
                        conn.commit()
                        print(f"Contenido de Wikipedia actualizado: {len(content)} caracteres")
                except Exception as e:
                    print(f"Error al actualizar contenido de Wikipedia: {str(e)}")
            
            # Verificar y actualizar información de Discogs
            if discogs_url and (discogs_url.strip() != ""):
                try:
                    print(f"Buscando información de Discogs para: {name}")
                    discogs_data = fetch_discogs_label_data(discogs_url)
                    if discogs_data:
                        profile = discogs_data.get('profile', '')
                        parent_label = discogs_data.get('parent_label')
                        contact_info = discogs_data.get('contact_info', '')
                        
                        # Construir una consulta de actualización dinámica
                        update_fields = []
                        values = []
                        
                        if profile:
                            update_fields.append("profile = ?")
                            values.append(profile)
                            print(f"Perfil de Discogs encontrado: {len(profile)} caracteres")
                        
                        if parent_label:
                            update_fields.append("parent_label = ?")
                            values.append(parent_label)
                            print(f"Etiqueta padre encontrada: {parent_label}")
                        
                        if contact_info:
                            update_fields.append("contact_info = ?")
                            values.append(contact_info)
                            print(f"Información de contacto encontrada: {len(contact_info)} caracteres")
                        
                        # URLs organizadas por categoría
                        urls = discogs_data.get('urls', [])
                        if urls:
                            social = []
                            streaming = []
                            purchase = []
                            blog = []
                            
                            for url in urls:
                                if 'facebook.com' in url or 'twitter.com' in url or 'instagram.com' in url:
                                    social.append(url)
                                elif 'soundcloud.com' in url or 'youtube.com' in url or 'spotify.com' in url:
                                    streaming.append(url)
                                elif 'bandcamp.com' in url:
                                    update_fields.append("bandcamp_url = ?")
                                    values.append(url)
                                    streaming.append(url)
                                elif 'apple.com/music' in url or 'music.apple.com' in url:
                                    purchase.append(url)
                                elif 'tumblr.com' in url or 'blog' in url or 'wordpress.com' in url:
                                    blog.append(url)
                            
                            if social:
                                update_fields.append("social_links = ?")
                                values.append(json.dumps(social))
                                print(f"Enlaces sociales encontrados: {len(social)}")
                            
                            if streaming:
                                update_fields.append("streaming_links = ?")
                                values.append(json.dumps(streaming))
                                print(f"Enlaces de streaming encontrados: {len(streaming)}")
                            
                            if purchase:
                                update_fields.append("purchase_links = ?")
                                values.append(json.dumps(purchase))
                                print(f"Enlaces de compra encontrados: {len(purchase)}")
                            
                            if blog:
                                update_fields.append("blog_links = ?")
                                values.append(json.dumps(blog))
                                print(f"Enlaces de blog encontrados: {len(blog)}")
                        
                        # Sellos subsidiarios
                        sublabels = discogs_data.get('sublabels', [])
                        if sublabels:
                            update_fields.append("subsidiary_labels = ?")
                            values.append(json.dumps(sublabels))
                            print(f"Sellos subsidiarios encontrados: {len(sublabels)}")
                        
                        # Ejecutar la actualización si hay campos para actualizar
                        if update_fields and values:
                            update_fields.append("last_updated = ?")
                            values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            values.append(label_id)  # Para la cláusula WHERE
                            
                            query = f"UPDATE labels SET {', '.join(update_fields)} WHERE id = ?"
                            cursor.execute(query, values)
                            conn.commit()
                            print(f"Información de Discogs actualizada para: {name}")
                except Exception as e:
                    print(f"Error al actualizar información de Discogs: {str(e)}")
                    traceback.print_exc()
            
        print(f"Actualización completada para {total} etiquetas.")
    finally:
        conn.close()



def fetch_label_data(label_mbid):
    """
    Fetch label data from MusicBrainz API with improved Wikipedia URL extraction
    
    Args:
        label_mbid (str): MusicBrainz ID of the label
    
    Returns:
        dict: Label data
    """
    # Define the URL with all needed includes
    url = f"{MUSICBRAINZ_API_URL}/label/{label_mbid}"
    
    # Include all relevant relationships
    params = {
        "inc": "url-rels+label-rels+release-rels+artist-rels",
        "fmt": "json"
    }
    
    headers = {
        "User-Agent": USER_AGENT
    }
    
    # Make the request
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Respect the rate limit
        time.sleep(RATE_LIMIT)
        
        data = response.json()
        
        # Explicitly check for and extract the Wikipedia URL 
        # This is a more reliable approach than depending on the relations parsing later
        wikipedia_url = extract_wikipedia_url_from_musicbrainz(label_mbid)
        if wikipedia_url:
            # If we found a Wikipedia URL, make sure it's in the data
            if 'relations' not in data:
                data['relations'] = []
            
            # Check if the relation already exists
            wiki_relation_exists = False
            for relation in data['relations']:
                if relation.get('type') == 'wikipedia' and relation.get('target-type') == 'url' and 'url' in relation:
                    wiki_relation_exists = True
                    # Update the URL in case it changed
                    relation['url']['resource'] = wikipedia_url
                    break
            
            # If no Wikipedia relation exists, create one
            if not wiki_relation_exists:
                wiki_relation = {
                    'type': 'wikipedia',
                    'target-type': 'url',
                    'url': {
                        'resource': wikipedia_url
                    }
                }
                data['relations'].append(wiki_relation)
                print(f"Added missing Wikipedia relation to data: {wikipedia_url}")
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching label {label_mbid}: {str(e)}")
        return None

def extract_label_info(label_data):
    """
    Extract relevant information from the API response including Wikipedia content and Discogs data
    
    Args:
        label_data (dict): Label data from MusicBrainz API
    
    Returns:
        tuple: (label_info, label_relationships, release_relationships)
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    label_info = {
        'mbid': label_data.get('id'),
        'name': label_data.get('name'),
        'country': label_data.get('country'),
        'mb_type': label_data.get('type'),
        'mb_code': label_data.get('label-code'),
        'founded_year': None,
        'official_website': None,
        'wikipedia_url': None,
        'wikipedia_content': None,
        'wikipedia_updated': None,
        'discogs_url': None,
        'bandcamp_url': None,
        'last_updated': now,
        'mb_last_updated': now,
        'profile': None,
        'parent_label': None,
        'contact_info': None,
        'social_links': None,
        'streaming_links': None,
        'purchase_links': None,
        'blog_links': None,
        'founder_info': None,
        'creative_persons': None,
        'signed_artists': None,
        'subsidiary_labels': None
    }
    
    # Extract founding date if available
    if 'life-span' in label_data and 'begin' in label_data['life-span']:
        begin_date = label_data['life-span']['begin']
        if begin_date and len(begin_date) >= 4:
            try:
                label_info['founded_year'] = int(begin_date[:4])
            except ValueError:
                pass
    
    # Initialize collections for different link types
    social_links = []
    streaming_links = []
    purchase_links = []
    blog_links = []
    creative_persons = []
    founder_info = []
    signed_artists = []
    subsidiary_labels = []
    
    # Extract URLs, relationships and fetch Wikipedia content if available
    if 'relations' in label_data:
        for relation in label_data['relations']:
            # Process URL relationships
            if relation['target-type'] == 'url' and 'url' in relation:
                url = relation['url']['resource']
                rel_type = relation['type']
                
                # Categorize based on type
                if rel_type == 'official homepage':
                    label_info['official_website'] = url
                # Fetch Wikipedia content using the improved function
                elif rel_type == 'wikipedia':
                    label_info['wikipedia_url'] = url
                    print(url)
                    # Fetch Wikipedia content using the improved function
                    if url:
                        print(f"Found Wikipedia URL: {url}")
                        try:
                            wikipedia_content = get_wikipedia_content(url)
                            if wikipedia_content:
                                # Descomentar estas líneas para guardar el contenido
                                label_info['wikipedia_content'] = wikipedia_content
                                label_info['wikipedia_updated'] = now
                                print(f"Successfully extracted Wikipedia content ({len(wikipedia_content)} characters)")
                                # Debug: Print the first 100 characters of content
                                content_preview = wikipedia_content[:100] + "..." if len(wikipedia_content) > 100 else wikipedia_content
                                print(f"Content preview: {content_preview}")
                            else:
                                print("Could not extract Wikipedia content")
                        except Exception as e:
                            print(f"Error extracting Wikipedia content: {str(e)}")


                elif rel_type == 'discogs':
                    label_info['discogs_url'] = url
                    
                    # Fetch additional data from Discogs
                    try:
                        discogs_data = fetch_discogs_label_data(url)
                        if discogs_data:
                            # Store profile information
                            if 'profile' in discogs_data and discogs_data['profile']:
                                label_info['profile'] = discogs_data['profile']
                                print(f"Found Discogs profile ({len(discogs_data['profile'])} characters)")
                            
                            # Store parent label
                            if 'parent_label' in discogs_data and discogs_data['parent_label']:
                                label_info['parent_label'] = discogs_data['parent_label']
                                print(f"Found parent label: {discogs_data['parent_label']}")
                            
                            # Store contact info
                            if 'contact_info' in discogs_data and discogs_data['contact_info']:
                                label_info['contact_info'] = discogs_data['contact_info']
                                print(f"Found contact info ({len(discogs_data['contact_info'])} characters)")
                            
                            # Process sublabels
                            if 'sublabels' in discogs_data and discogs_data['sublabels']:
                                subsidiary_labels.extend(discogs_data['sublabels'])
                                print(f"Found {len(discogs_data['sublabels'])} sublabels")
                                
                            # Process URLs from Discogs
                            if 'urls' in discogs_data and discogs_data['urls']:
                                for discogs_url in discogs_data['urls']:
                                    if 'facebook.com' in discogs_url or 'twitter.com' in discogs_url or 'instagram.com' in discogs_url:
                                        social_links.append(discogs_url)
                                    elif 'soundcloud.com' in discogs_url or 'youtube.com' in discogs_url or 'spotify.com' in discogs_url:
                                        streaming_links.append(discogs_url)
                                    elif 'bandcamp.com' in discogs_url:
                                        label_info['bandcamp_url'] = discogs_url
                                        streaming_links.append(discogs_url)
                                    elif 'apple.com/music' in discogs_url or 'music.apple.com' in discogs_url:
                                        purchase_links.append(discogs_url)
                                    elif 'tumblr.com' in discogs_url or 'blog' in discogs_url or 'wordpress.com' in discogs_url:
                                        blog_links.append(discogs_url)
                    except Exception as e:
                        print(f"Error processing Discogs data: {str(e)}")
            
            # Process person relationships (founders, creative persons)
            elif relation['target-type'] == 'artist' and 'artist' in relation:
                rel_type = relation['type']
                artist_name = relation['artist'].get('name', 'Unknown')
                
                # Extract date information if available
                date_info = ""
                if 'begin' in relation and relation['begin']:
                    date_info += f" (from {relation['begin']}"
                    if 'end' in relation and relation['end']:
                        date_info += f" to {relation['end']})"
                    else:
                        date_info += " to present)"
                
                if rel_type == 'founder':
                    founder_info.append(f"{artist_name}{date_info}")
                elif rel_type in ['creative personnel', 'illustrator', 'designer', 'graphic artist', 'art director']:
                    creative_persons.append(f"{artist_name} ({rel_type}){date_info}")
                elif rel_type == 'signed':
                    signed_artists.append(f"{artist_name}{date_info}")
            
            # Process subsidiary label relationships
            elif relation['target-type'] == 'label' and relation['type'] == 'subsidiary':
                if 'label' in relation and 'name' in relation['label']:
                    subsidiary_labels.append(relation['label']['name'])
    
    # Convert lists to strings
    if social_links:
        label_info['social_links'] = json.dumps(social_links)
        print(f"Found {len(social_links)} social links")
    if streaming_links:
        label_info['streaming_links'] = json.dumps(streaming_links)
        print(f"Found {len(streaming_links)} streaming links")
    if purchase_links:
        label_info['purchase_links'] = json.dumps(purchase_links)
        print(f"Found {len(purchase_links)} purchase links")
    if blog_links:
        label_info['blog_links'] = json.dumps(blog_links)
        print(f"Found {len(blog_links)} blog links")
    if founder_info:
        label_info['founder_info'] = json.dumps(founder_info)
        print(f"Found {len(founder_info)} founder information items")
    if creative_persons:
        label_info['creative_persons'] = json.dumps(creative_persons)
        print(f"Found {len(creative_persons)} creative persons")
    if signed_artists:
        label_info['signed_artists'] = json.dumps(signed_artists)
        print(f"Found {len(signed_artists)} signed artists")
    if subsidiary_labels:
        label_info['subsidiary_labels'] = json.dumps(list(set(subsidiary_labels)))  # Remove duplicates
        print(f"Found {len(set(subsidiary_labels))} subsidiary labels")
    
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
    
    # Debug info to verify the content was extracted
    if label_info['wikipedia_content']:
        print(f"Wikipedia content set in label_info: {len(label_info['wikipedia_content'])} characters")
    if label_info['profile']:
        print(f"Discogs profile set in label_info: {len(label_info['profile'])} characters")
    
    return label_info, label_relationships, release_relationships


def get_wikipedia_content(url):
    """
    Obtiene el contenido principal de una página de Wikipedia preservando los saltos de línea
    
    Args:
        url (str): URL de la página de Wikipedia
        
    Returns:
        str or None: Contenido principal o None si hay error
    """
    if not url:
        return None
    
    try:
        print(f"Fetching Wikipedia content from URL: {url}")
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract the main content (first try with mw-content-text)
            main_content = soup.find('div', {'id': 'mw-content-text'})
            
            if main_content:
                # Remove unwanted elements
                for unwanted in main_content.select('.navbox, .infobox, .toc, .metadata, .tmbox, .ambox, .reference, .reflist, .thumb, .mw-editsection'):
                    if unwanted:
                        unwanted.decompose()
                
                # Get the first div with class 'mw-parser-output' which contains the actual content
                parser_output = main_content.find('div', {'class': 'mw-parser-output'})
                if parser_output:
                    # Extract paragraphs, skipping empty ones and tables
                    paragraphs = []
                    for child in parser_output.children:
                        if child.name == 'p' and child.text.strip():
                            paragraphs.append(child.text.strip())
                        elif child.name == 'h2' or child.name == 'h3':
                            # Add section headers
                            header_text = child.find('span', {'class': 'mw-headline'})
                            if header_text:
                                paragraphs.append(f"\n## {header_text.text.strip()}\n")
                    
                    # Join all paragraphs with double newlines
                    content = "\n\n".join(paragraphs)
                    
                    if content:
                        print(f"Successfully extracted Wikipedia content: {len(content)} characters")
                        # Debug: show a preview
                        preview = content[:100] + "..." if len(content) > 100 else content
                        print(f"Content preview: {preview}")
                        return content
                    else:
                        print("Extracted content was empty (parser-output method)")
                else:
                    # Fallback method: try to get all paragraphs directly
                    paragraphs = main_content.find_all('p')
                    content = "\n\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
                    
                    if content:
                        print(f"Successfully extracted Wikipedia content (fallback method): {len(content)} characters")
                        return content
                    else:
                        print("Extracted content was empty (fallback method)")
            else:
                print("Could not find main content element (mw-content-text) in Wikipedia page")
        else:
            print(f"Wikipedia request failed with status code: {response.status_code}")
        
        return None
    except Exception as e:
        print(f"Error extracting Wikipedia content: {str(e)}")
        traceback.print_exc()
        return None

def update_wikipedia_content(db_path, label_mbid=None):
    """
    Actualiza el contenido de Wikipedia para sellos que tienen una URL pero no contenido
    
    Args:
        db_path (str): Ruta a la base de datos SQLite
        label_mbid (str, optional): Si se proporciona, actualiza solo este sello específico
        
    Returns:
        int: Número de sellos actualizados
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    updated_count = 0
    
    try:
        if label_mbid:
            # Actualizar un sello específico
            cursor.execute("""
                SELECT id, name, wikipedia_url FROM labels 
                WHERE mbid = ? AND wikipedia_url IS NOT NULL AND 
                (wikipedia_content IS NULL OR wikipedia_content = '')
            """, (label_mbid,))
        else:
            # Actualizar todos los sellos con URL pero sin contenido
            cursor.execute("""
                SELECT id, name, wikipedia_url FROM labels 
                WHERE wikipedia_url IS NOT NULL AND 
                (wikipedia_content IS NULL OR wikipedia_content = '')
            """)
        
        labels = cursor.fetchall()
        total = len(labels)
        
        if total == 0:
            print("No se encontraron sellos que necesiten actualización de Wikipedia.")
            return 0
        
        print(f"Encontrados {total} sellos para actualizar contenido de Wikipedia.")
        
        for i, (label_id, name, wikipedia_url) in enumerate(labels):
            print(f"Procesando sello {i+1}/{total}: {name}")
            
            if wikipedia_url:
                try:
                    # Obtener contenido de Wikipedia
                    content = get_wikipedia_content(wikipedia_url)
                    
                    if content:
                        # Actualizar la base de datos con el contenido
                        cursor.execute("""
                            UPDATE labels SET 
                                wikipedia_content = ?, 
                                wikipedia_updated = ? 
                            WHERE id = ?
                        """, (content, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), label_id))
                        
                        conn.commit()
                        updated_count += 1
                        print(f"Contenido de Wikipedia actualizado para {name}: {len(content)} caracteres")
                    else:
                        print(f"No se pudo extraer contenido de Wikipedia para {name}")
                except Exception as e:
                    print(f"Error al actualizar contenido de Wikipedia para {name}: {str(e)}")
                    traceback.print_exc()
            
            # Pequeño retraso para no sobrecargar Wikipedia
            time.sleep(0.5)
        
        print(f"Actualización completada. {updated_count} sellos actualizados.")
        return updated_count
    
    finally:
        conn.close()

def extract_wikipedia_url_from_musicbrainz(label_mbid):
    """
    Extrae la URL de Wikipedia directamente desde la API de MusicBrainz
    
    Args:
        label_mbid (str): MusicBrainz ID del sello discográfico
        
    Returns:
        str or None: URL de Wikipedia o None si no se encuentra
    """
    if not label_mbid:
        return None
    
    # Endpoint de la API de MusicBrainz para sellos
    endpoint = f"{MUSICBRAINZ_API_URL}/label/{label_mbid}?inc=url-rels&fmt=json"
    
    headers = {
        "User-Agent": USER_AGENT
    }
    
    try:
        print(f"Consultando MusicBrainz para obtener URL de Wikipedia para sello ID: {label_mbid}")
        response = requests.get(endpoint, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Respetar el límite de tasa de MusicBrainz
        time.sleep(RATE_LIMIT)
        
        data = response.json()
        
        # Buscar específicamente la relación con Wikipedia
        if 'relations' in data:
            for relation in data['relations']:
                if relation['target-type'] == 'url' and relation['type'] == 'wikipedia' and 'url' in relation:
                    wiki_url = relation['url']['resource']
                    print(f"URL de Wikipedia encontrada: {wiki_url}")
                    return wiki_url
        
        print("No se encontró URL de Wikipedia en MusicBrainz")
        return None
    except Exception as e:
        print(f"Error al consultar MusicBrainz para obtener URL de Wikipedia: {str(e)}")
        traceback.print_exc()
        return None


def update_wikipedia_urls(db_path, label_mbid=None):
    """
    Actualiza todas las URLs de Wikipedia de MusicBrainz para sellos existentes
    
    Args:
        db_path (str): Ruta a la base de datos SQLite
        label_mbid (str, optional): Si se proporciona, actualiza solo este sello específico
        
    Returns:
        int: Número de URLs actualizadas
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    updated_count = 0
    
    try:
        if label_mbid:
            # Actualizar un sello específico
            cursor.execute("""
                SELECT id, name, mbid FROM labels 
                WHERE mbid = ? AND 
                (wikipedia_url IS NULL OR wikipedia_url = '')
            """, (label_mbid,))
            labels = cursor.fetchall()
        else:
            # Obtener todos los sellos que tienen MBID pero no URL de Wikipedia
            cursor.execute("""
                SELECT id, name, mbid FROM labels 
                WHERE mbid IS NOT NULL AND 
                (wikipedia_url IS NULL OR wikipedia_url = '')
            """)
            labels = cursor.fetchall()
        
        total = len(labels)
        
        if total == 0:
            print("No se encontraron sellos sin URL de Wikipedia.")
            return 0
        
        print(f"Encontrados {total} sellos para actualizar URLs de Wikipedia.")
        
        for i, (label_id, name, mbid) in enumerate(labels):
            print(f"Procesando sello {i+1}/{total}: {name} (MBID: {mbid})")
            
            # Extraer URL de Wikipedia directamente de MusicBrainz
            wiki_url = extract_wikipedia_url_from_musicbrainz(mbid)
            
            if wiki_url:
                print(f"Encontrada URL de Wikipedia: {wiki_url}")
                
                # Actualizar la base de datos con la URL
                try:
                    # Primero actualizar solo la URL
                    cursor.execute("""
                        UPDATE labels SET 
                            wikipedia_url = ?, 
                            last_updated = ? 
                        WHERE id = ?
                    """, (wiki_url, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), label_id))
                    
                    conn.commit()
                    
                    # Luego intentar obtener el contenido
                    try:
                        content = get_wikipedia_content(wiki_url)
                        if content:
                            cursor.execute("""
                                UPDATE labels SET 
                                    wikipedia_content = ?,
                                    wikipedia_updated = ?
                                WHERE id = ?
                            """, (content, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), label_id))
                            
                            conn.commit()
                            print(f"Contenido de Wikipedia actualizado: {len(content)} caracteres")
                        else:
                            print("No se pudo extraer contenido de Wikipedia")
                    except Exception as e:
                        print(f"Error al obtener contenido de Wikipedia: {str(e)}")
                    
                    updated_count += 1
                except Exception as e:
                    print(f"Error al actualizar la base de datos: {str(e)}")
                    traceback.print_exc()
            else:
                print(f"No se encontró URL de Wikipedia para {name} (MBID: {mbid})")
            
            # Esperar un poco para respetar los límites de tasa
            time.sleep(RATE_LIMIT)
        
        print(f"Actualización completada. {updated_count}/{total} URLs de Wikipedia actualizadas.")
        return updated_count
    
    finally:
        conn.close()

def find_catalog_relationships(db_path, label_id, label_mbid, artist_relationships=None):
    """
    Find artists and albums in the database that belong to this label's catalog
    based on MusicBrainz IDs.
    
    Args:
        db_path (str): Path to SQLite database
        label_id (int): Database ID of the label
        label_mbid (str): MusicBrainz ID of the label
        artist_relationships (list): Optional list of artist relationships from MusicBrainz
    
    Returns:
        tuple: (found_artists, found_albums) counts
    """
    if not label_mbid:
        return 0, 0
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        found_artists = 0
        found_albums = 0
        
        try:
            print(f"Finding catalog relationships for label {label_mbid}...")
            
            # Process artist relationships from MusicBrainz if provided
            if artist_relationships:
                print(f"Processing {len(artist_relationships)} artist relationships from MusicBrainz")
                for relation in artist_relationships:
                    artist_mbid = relation['artist_mbid']
                    artist_name = relation['artist_name']
                    rel_type = relation['relationship_type']
                    
                    # Check if the artist exists in our database
                    cursor.execute("SELECT id FROM artists WHERE mbid = ?", (artist_mbid,))
                    artist_result = cursor.fetchone()
                    
                    if artist_result:
                        # Artist exists in our database
                        artist_id = artist_result[0]
                        
                        # Check if relationship already exists
                        cursor.execute("""
                            SELECT id FROM label_artist_relationships
                            WHERE label_id = ? AND artist_id = ?
                        """, (label_id, artist_id))
                        
                        if not cursor.fetchone():
                            # Create the relationship
                            cursor.execute("""
                                INSERT INTO label_artist_relationships
                                (label_id, artist_id, relationship_type, begin_date, end_date, last_updated)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                label_id, artist_id, rel_type, 
                                relation.get('begin_date'), relation.get('end_date'),
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            ))
                            
                            found_artists += 1
                            print(f"Found artist in our database: {artist_name}")
                    else:
                        # Artist doesn't exist in our database, add to external catalog
                        cursor.execute("""
                            INSERT OR IGNORE INTO label_external_catalog
                            (label_id, entity_type, entity_mbid, entity_name, relationship_type, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            label_id, 'artist', artist_mbid, artist_name, rel_type,
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ))
                        print(f"Added external artist to catalog: {artist_name}")
            
            # Look for albums with existing MusicBrainz IDs
            cursor.execute("""
                SELECT id, name, mbid, artist_id FROM albums
                WHERE mbid IS NOT NULL AND mbid != ''
            """)
            
            albums = cursor.fetchall()
            
            # For each album, check if it has a relationship with this label
            for album_id, album_name, album_mbid, artist_id in albums:
                # Check if relationship already exists
                cursor.execute("""
                    SELECT id FROM label_release_relationships
                    WHERE label_id = ? AND album_id = ?
                """, (label_id, album_id))
                
                if cursor.fetchone():
                    continue  # Relationship already exists
                
                # Get artist name for logging
                cursor.execute("SELECT name FROM artists WHERE id = ?", (artist_id,))
                artist_result = cursor.fetchone()
                artist_name = artist_result[0] if artist_result else "Unknown Artist"
                    
                # Check with MusicBrainz API
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
                    time.sleep(RATE_LIMIT)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check for label information
                        if 'label-info' in data:
                            for label_info in data['label-info']:
                                if 'label' in label_info and label_info['label']['id'] == label_mbid:
                                    # Found a relationship
                                    catalog_number = label_info.get('catalog-number')
                                    
                                    # Insert the relationship
                                    cursor.execute("""
                                        INSERT INTO label_release_relationships
                                        (label_id, album_id, relationship_type, catalog_number, last_updated)
                                        VALUES (?, ?, ?, ?, ?)
                                    """, (
                                        label_id, album_id, 'release', catalog_number,
                                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    ))
                                    
                                    found_albums += 1
                                    conn.commit()
                                    print(f"Found album relationship: Label '{label_mbid}' - Album '{album_name}' by {artist_name}")
                                    break
                except Exception as e:
                    print(f"Error checking album {album_name} relationship: {str(e)}")
        
            conn.commit()
        except Exception as e:
            print(f"Error finding catalog relationships: {str(e)}")
            traceback.print_exc()
        
        # finally:
        #     conn.close()
        
        return found_artists, found_albums


def get_discogs_label_info(discogs_url, discogs_token=None):
    """
    Fetch additional information about a label from Discogs API
    
    Args:
        discogs_url (str): Discogs URL for the label
        discogs_token (str): Discogs API token
        
    Returns:
        dict: Label information from Discogs
    """
    if not discogs_url or not discogs_token:
        return None
    
    try:
        # Check if discogs_client is available
        import discogs_client
        
        # Extract label ID from URL
        label_id = None
        match = re.search(r'/label/(\d+)', discogs_url)
        if match:
            label_id = match.group(1)
        else:
            print(f"Could not extract Discogs label ID from URL: {discogs_url}")
            return None
        
        print(f"Fetching Discogs info for label ID {label_id}...")
        
        # Initialize Discogs client
        client = discogs_client.Client('MyMusicLibrary/1.0', user_token=discogs_token)
        
        # Fetch label information
        label = client.label(int(label_id))
        
        # Extract relevant information
        label_info = {
            'discogs_profile': getattr(label, 'profile', None),
            'discogs_contact_info': getattr(label, 'contact_info', None),
            'discogs_parent_label': None,
            'discogs_sublabels': None
        }
        
        # Get parent label
        try:
            parent_label = getattr(label, 'parent_label', None)
            if parent_label:
                label_info['discogs_parent_label'] = parent_label.name
                print(f"Found parent label: {parent_label.name}")
        except Exception as e:
            print(f"Error getting parent label: {str(e)}")
            
        # Get sublabels
        try:
            sublabels = getattr(label, 'sublabels', [])
            if sublabels:
                sublabels_names = [sl.name for sl in sublabels]
                label_info['discogs_sublabels'] = ', '.join(sublabels_names)
                print(f"Found {len(sublabels_names)} sublabels")
        except Exception as e:
            print(f"Error getting sublabels: {str(e)}")
        
        print(f"Successfully retrieved Discogs data for label ID {label_id}")
        return label_info
        
    except ImportError:
        print("discogs_client module not available")
        return None
    except Exception as e:
        print(f"Error fetching Discogs info for {discogs_url}: {str(e)}")
        return None




def fetch_discogs_label_data(discogs_url):
    """
    Fetch additional label information from Discogs
    
    Args:
        discogs_url (str): Discogs URL for the label
    
    Returns:
        dict: Label data from Discogs
    """
    if not discogs_url:
        return None
    
    # Extract Discogs ID from URL
    discogs_id = None
    try:
        # URL format is typically https://www.discogs.com/label/12345-Label-Name
        if 'discogs.com/label/' in discogs_url:
            id_part = discogs_url.split('/label/')[1].split('-')[0]
            if id_part.isdigit():
                discogs_id = id_part
            else:
                # Try another pattern
                parts = discogs_url.split('/label/')
                if len(parts) > 1:
                    discogs_id = parts[1]
    except Exception as e:
        print(f"Error extracting Discogs ID from URL {discogs_url}: {str(e)}")
        return None
    
    if not discogs_id:
        print(f"Could not extract Discogs ID from URL: {discogs_url}")
        return None
    
    # Fetch the label data from Discogs API
    url = f"https://api.discogs.com/labels/{discogs_id}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Respect rate limits
        time.sleep(1)
        
        data = response.json()
        
        # Extract relevant information
        discogs_data = {
            'profile': data.get('profile', ''),
            'parent_label': None,
            'sublabels': [],
            'contact_info': data.get('contact_info', ''),
            'urls': data.get('urls', [])
        }
        
        # Get parent label
        if 'parent_label' in data and data['parent_label']:
            discogs_data['parent_label'] = data['parent_label'].get('name')
        
        # Get sublabels
        if 'sublabels' in data and data['sublabels']:
            discogs_data['sublabels'] = [sublabel.get('name') for sublabel in data['sublabels']]
        
        print(f"Successfully fetched Discogs data for label")
        return discogs_data
    
    except Exception as e:
        print(f"Error fetching Discogs data: {str(e)}")
        return None

def save_label_data(db_path, label_info, label_relationships, release_relationships):
    """
    Save the label data to the database with improved error handling and retries
    """
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        conn = None
        try:
            conn = sqlite3.connect(db_path, timeout=60)
            cursor = conn.cursor()
            
            # Debug: Check which fields have content
            for key, value in label_info.items():
                if value and key in ['wikipedia_content', 'profile', 'subsidiary_labels']:
                    print(f"Field {key} has {len(str(value))} characters to save")
            
            # Basic label data that should always be present
            mbid = label_info.get('mbid')
            name = label_info.get('name')
            country = label_info.get('country')
            founded_year = label_info.get('founded_year')
            mb_type = label_info.get('mb_type')
            mb_code = label_info.get('mb_code')
            last_updated = label_info.get('last_updated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            mb_last_updated = label_info.get('mb_last_updated', last_updated)
            
            # URLs and web content
            official_website = label_info.get('official_website')
            wikipedia_url = label_info.get('wikipedia_url')
            wikipedia_content = label_info.get('wikipedia_content')
            wikipedia_updated = label_info.get('wikipedia_updated')
            discogs_url = label_info.get('discogs_url')
            bandcamp_url = label_info.get('bandcamp_url')
            
            # Additional metadata
            profile = label_info.get('profile')
            parent_label = label_info.get('parent_label')
            contact_info = label_info.get('contact_info')
            
            # Serialized collections
            social_links = label_info.get('social_links')
            streaming_links = label_info.get('streaming_links')
            purchase_links = label_info.get('purchase_links')
            blog_links = label_info.get('blog_links')
            founder_info = label_info.get('founder_info')
            creative_persons = label_info.get('creative_persons')
            signed_artists = label_info.get('signed_artists')
            subsidiary_labels = label_info.get('subsidiary_labels')
            
            # Check if label already exists
            cursor.execute("SELECT id FROM labels WHERE mbid = ?", (mbid,))
            existing = cursor.fetchone()
            
            label_id = None  # INICIALIZAR AQUÍ
            
            if existing:
                label_id = existing[0]  # OBTENER ID DEL REGISTRO EXISTENTE
                # Update existing label
                cursor.execute("""
                UPDATE labels SET
                    name = ?, country = ?, founded_year = ?,
                    official_website = ?, wikipedia_url = ?, 
                    wikipedia_content = ?, wikipedia_updated = ?,
                    discogs_url = ?, bandcamp_url = ?,
                    mb_type = ?, mb_code = ?,
                    last_updated = ?, mb_last_updated = ?,
                    profile = ?, parent_label = ?, contact_info = ?,
                    social_links = ?, streaming_links = ?,
                    purchase_links = ?, blog_links = ?,
                    founder_info = ?, creative_persons = ?,
                    signed_artists = ?, subsidiary_labels = ?
                WHERE mbid = ?
                """, (
                    name, country, founded_year, 
                    official_website, wikipedia_url, 
                    wikipedia_content, wikipedia_updated,
                    discogs_url, bandcamp_url,
                    mb_type, mb_code,
                    last_updated, mb_last_updated,
                    profile, parent_label, contact_info,
                    social_links, streaming_links,
                    purchase_links, blog_links,
                    founder_info, creative_persons,
                    signed_artists, subsidiary_labels,
                    mbid
                ))
                print(f"Updated existing label: {name}")
            else:
                # Insert new label
                cursor.execute("""
                INSERT INTO labels (
                    mbid, name, country, founded_year,
                    official_website, wikipedia_url, 
                    wikipedia_content, wikipedia_updated,
                    discogs_url, bandcamp_url,
                    mb_type, mb_code,
                    last_updated, mb_last_updated,
                    profile, parent_label, contact_info,
                    social_links, streaming_links,
                    purchase_links, blog_links,
                    founder_info, creative_persons,
                    signed_artists, subsidiary_labels
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mbid, name, country, founded_year, 
                    official_website, wikipedia_url, 
                    wikipedia_content, wikipedia_updated,
                    discogs_url, bandcamp_url,
                    mb_type, mb_code,
                    last_updated, mb_last_updated,
                    profile, parent_label, contact_info,
                    social_links, streaming_links,
                    purchase_links, blog_links,
                    founder_info, creative_persons,
                    signed_artists, subsidiary_labels
                ))
                label_id = cursor.lastrowid  # OBTENER ID DEL NUEVO REGISTRO
                print(f"Inserted new label: {name}")
            
            conn.commit()
            
            # Debug: Verify the data was saved
            cursor.execute("SELECT id, wikipedia_content, profile, subsidiary_labels, social_links FROM labels WHERE mbid = ?", (mbid,))
            result = cursor.fetchone()
            if result:
                saved_id, wiki_content_saved, profile_saved, subsidiary_saved, social_saved = result
                print(f"Label ID: {saved_id}")
                print(f"Wikipedia content saved in DB: {len(wiki_content_saved) if wiki_content_saved else 0} characters")
                print(f"Discogs profile saved in DB: {len(profile_saved) if profile_saved else 0} characters")
                print(f"Subsidiary labels saved: {len(subsidiary_saved) if subsidiary_saved else 0} characters")
                print(f"Social links saved: {len(social_saved) if social_saved else 0} characters")
            else:
                print(f"Error: Could not find label with MBID {mbid} after insert/update")
                return False
            
            # Process relationships (resto del código igual...)
            for rel in label_relationships:
                # Get or create the target label
                target_mbid = rel['target_mbid']
                cursor.execute("SELECT id FROM labels WHERE mbid = ?", (target_mbid,))
                result = cursor.fetchone()
                
                if result:
                    target_id = result[0]
                else:
                    # Insert a placeholder for the target label
                    cursor.execute("""
                    INSERT INTO labels (mbid, name, last_updated)
                    VALUES (?, ?, ?)
                    """, (
                        target_mbid, 
                        f"Unknown (MusicBrainz ID: {target_mbid})", 
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    target_id = cursor.lastrowid
                
                # Add the relationship
                cursor.execute("""
                INSERT OR REPLACE INTO label_relationships (
                    source_label_id, target_label_id, relationship_type,
                    begin_date, end_date, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    label_id, target_id, rel['relationship_type'],
                    rel.get('begin_date'), rel.get('end_date'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            # Process release relationships
            for rel in release_relationships:
                # Check if we have this release in our database
                cursor.execute("SELECT id FROM albums WHERE mbid = ?", (rel['release_mbid'],))
                result = cursor.fetchone()
                
                if result:
                    album_id = result[0]
                    
                    # Add the relationship
                    cursor.execute("""
                    INSERT OR REPLACE INTO label_release_relationships (
                        label_id, album_id, relationship_type, catalog_number,
                        begin_date, end_date, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        label_id, album_id, rel['relationship_type'], 
                        rel.get('catalog_number'),
                        rel.get('begin_date'), rel.get('end_date'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
            
            conn.commit()
            print(f"Successfully saved label data for {name} (MBID: {mbid})")
            return True
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"Database is locked, retrying in {wait_time} seconds (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"Database error: {str(e)}")
                traceback.print_exc()
                return False
        except Exception as e:
            print(f"Error saving label data: {str(e)}")
            traceback.print_exc()
            return False
        finally:
            if conn:
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
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Respect the rate limit
        time.sleep(RATE_LIMIT)
        
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
    except Exception as e:
        print(f"Error searching for labels: {str(e)}")
        return []

def fetch_label_by_album(db_path, album_mbid, conn=None):
    """
    Fetch label information for an album from MusicBrainz with improved error handling
    
    Args:
        db_path (str): Path to SQLite database
        album_mbid (str): MusicBrainz ID of the album
        conn: Optional database connection to reuse
        
    Returns:
        bool: True if successful, False otherwise
    """
    should_close_conn = False
    
    try:
        if conn is None:
            conn = sqlite3.connect(db_path, timeout=60)
            should_close_conn = True
        
        # Validate album_mbid
        if not album_mbid or not isinstance(album_mbid, str):
            print(f"Invalid album MBID: {album_mbid}")
            return False
        
        print(f"Fetching label information for album: {album_mbid}")
        
        # Rate limiting
        time.sleep(1.1)
        
        # Fetch release information from MusicBrainz
        url = f"https://musicbrainz.org/ws/2/release/{album_mbid}?inc=labels+label-rels&fmt=json"
        headers = {
            'User-Agent': 'YourMusicApp/1.0 (frodobolson@disroot.org)'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching album data from MusicBrainz: {e}")
            return False
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return False
        
        # Check if we have valid data
        if not data or 'error' in data:
            print(f"No valid data returned for album {album_mbid}")
            return False
        
        # Extract label information
        labels_processed = 0
        
        # Process direct labels
        if 'label-info' in data and data['label-info']:
            for label_info in data['label-info']:
                if 'label' not in label_info or not label_info['label']:
                    continue
                    
                label_data = label_info['label']
                if 'id' not in label_data:
                    continue
                
                label_mbid = label_data['id']
                
                try:
                    success = fetch_label_by_mbid(db_path, label_mbid, conn)
                    if success:
                        labels_processed += 1
                        
                        # Create release relationship
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM albums WHERE mbid = ?", (album_mbid,))
                        album_result = cursor.fetchone()
                        
                        if album_result:
                            album_id = album_result[0]
                            
                            cursor.execute("SELECT id FROM labels WHERE mbid = ?", (label_mbid,))
                            label_result = cursor.fetchone()
                            
                            if label_result:
                                label_id = label_result[0]
                                
                                # Insert relationship
                                cursor.execute("""
                                INSERT OR REPLACE INTO label_release_relationships (
                                    label_id, album_id, relationship_type, catalog_number,
                                    last_updated
                                ) VALUES (?, ?, ?, ?, ?)
                                """, (
                                    label_id, album_id, 'release',
                                    label_info.get('catalog-number'),
                                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                ))
                                conn.commit()
                                print(f"Created relationship: Label {label_mbid} -> Album {album_mbid}")
                            else:
                                print(f"Warning: Label {label_mbid} not found in database after fetch")
                        else:
                            print(f"Warning: Album {album_mbid} not found in local database")
                            
                except Exception as e:
                    print(f"Error processing label {label_mbid}: {e}")
                    continue
        
        # Process label relationships
        if 'relations' in data and data['relations']:
            for relation in data['relations']:
                if (relation.get('type') == 'label' and 
                    'label' in relation and 
                    relation['label'] and 
                    'id' in relation['label']):
                    
                    label_mbid = relation['label']['id']
                    
                    try:
                        success = fetch_label_by_mbid(db_path, label_mbid, conn)
                        if success:
                            labels_processed += 1
                    except Exception as e:
                        print(f"Error processing label relationship {label_mbid}: {e}")
                        continue
        
        if labels_processed > 0:
            print(f"Successfully processed {labels_processed} labels for album {album_mbid}")
            return True
        else:
            print(f"No labels found for album {album_mbid}")
            return True  # Not an error, just no labels
            
    except Exception as e:
        print(f"Unexpected error in fetch_label_by_album: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if should_close_conn and conn:
            try:
                conn.close()
            except:
                pass




def fetch_label_by_mbid(db_path, label_mbid, conn=None):
    """
    Fetch comprehensive label information from MusicBrainz with improved error handling
    
    Args:
        db_path (str): Path to SQLite database
        label_mbid (str): MusicBrainz ID of the label
        conn: Optional database connection to reuse
        
    Returns:
        bool: True if successful, False otherwise
    """
    should_close_conn = False
    
    try:
        if conn is None:
            conn = sqlite3.connect(db_path, timeout=60)
            should_close_conn = True
        
        # Validate label_mbid
        if not label_mbid or not isinstance(label_mbid, str):
            print(f"Invalid label MBID: {label_mbid}")
            return False
        
        print(f"Fetching label information for: {label_mbid}")
        
        # Check if we already have this label
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, last_updated FROM labels WHERE mbid = ?", (label_mbid,))
        existing = cursor.fetchone()
        
        if existing:
            label_id, name, last_updated = existing
            print(f"Label already exists: {name} (ID: {label_id})")
            
            # Check if it's recent (less than 30 days old)
            if last_updated:
                try:
                    last_update_date = datetime.strptime(last_updated, '%Y-%m-%d %H:%M:%S')
                    if (datetime.now() - last_update_date).days < 30:
                        print(f"Label {name} was updated recently, skipping")
                        return True
                except ValueError:
                    pass  # Continue with update if date parsing fails
        
        # Rate limiting
        time.sleep(1.1)
        
        # Fetch basic label information
        url = f"https://musicbrainz.org/ws/2/label/{label_mbid}?inc=url-rels+aliases&fmt=json"
        headers = {
            'User-Agent': 'YourMusicApp/1.0 (frodobolson@disroot.org)'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching label data from MusicBrainz: {e}")
            return False
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return False
        
        # Check if we have valid data
        if not data or 'error' in data:
            print(f"No valid data returned for label {label_mbid}")
            return False
        
        # Validate required fields
        if 'name' not in data or not data['name']:
            print(f"Label {label_mbid} has no name, skipping")
            return False
        
        # Extract basic label information with safe access
        label_info = {
            'mbid': label_mbid,
            'name': data.get('name', ''),
            'country': data.get('country'),
            'founded_year': None,
            'official_website': None,
            'wikipedia_url': None,
            'discogs_url': None,
            'bandcamp_url': None,
            'mb_type': data.get('type'),
            'mb_code': data.get('label-code'),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'mb_last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Extract founded year from life-span
        if 'life-span' in data and data['life-span'] and 'begin' in data['life-span']:
            begin_date = data['life-span']['begin']
            if begin_date and len(begin_date) >= 4:
                try:
                    label_info['founded_year'] = int(begin_date[:4])
                except (ValueError, TypeError):
                    pass
        
        # Extract URLs with safe access
        social_links = []
        streaming_links = []
        purchase_links = []
        blog_links = []
        
        if 'relations' in data and data['relations']:
            for relation in data['relations']:
                if not relation or 'type' not in relation or 'url' not in relation:
                    continue
                
                url_data = relation['url']
                if not url_data or 'resource' not in url_data:
                    continue
                
                url = url_data['resource']
                rel_type = relation['type']
                
                # Categorize URLs
                if rel_type == 'official homepage':
                    label_info['official_website'] = url
                elif 'wikipedia' in url.lower():
                    label_info['wikipedia_url'] = url
                elif 'discogs' in url.lower():
                    label_info['discogs_url'] = url
                elif 'bandcamp' in url.lower():
                    label_info['bandcamp_url'] = url
                elif rel_type in ['social network', 'social media']:
                    social_links.append({'type': rel_type, 'url': url})
                elif rel_type in ['streaming', 'streaming music']:
                    streaming_links.append({'type': rel_type, 'url': url})
                elif rel_type in ['purchase for download', 'purchase for mail-order']:
                    purchase_links.append({'type': rel_type, 'url': url})
                elif rel_type in ['blog', 'review']:
                    blog_links.append({'type': rel_type, 'url': url})
        
        # Serialize link collections
        label_info['social_links'] = json.dumps(social_links) if social_links else None
        label_info['streaming_links'] = json.dumps(streaming_links) if streaming_links else None
        label_info['purchase_links'] = json.dumps(purchase_links) if purchase_links else None
        label_info['blog_links'] = json.dumps(blog_links) if blog_links else None
        
        # Initialize other fields
        label_info['profile'] = None
        label_info['parent_label'] = None
        label_info['contact_info'] = None
        label_info['founder_info'] = None
        label_info['creative_persons'] = None
        label_info['signed_artists'] = None
        label_info['subsidiary_labels'] = None
        label_info['wikipedia_content'] = None
        label_info['wikipedia_updated'] = None
        
        print(f"Found {len(social_links)} social links")
        print(f"Found {len(streaming_links)} streaming links")
        
        # Fetch additional information if we have URLs
        try:
            if label_info['wikipedia_url']:
                wikipedia_content = fetch_wikipedia_content(label_info['wikipedia_url'])
                if wikipedia_content:
                    label_info['wikipedia_content'] = wikipedia_content
                    label_info['wikipedia_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"Error fetching Wikipedia content: {e}")
        
        try:
            if label_info['discogs_url']:
                discogs_data = fetch_discogs_label_info(label_info['discogs_url'])
                if discogs_data:
                    label_info.update(discogs_data)
        except Exception as e:
            print(f"Error fetching Discogs data: {e}")
        
        # Save the label data
        try:
            success = save_label_data(db_path, label_info, [], [])
            if success:
                print(f"Successfully saved label: {label_info['name']}")
                return True
            else:
                print(f"Failed to save label: {label_info['name']}")
                return False
        except Exception as e:
            print(f"Error saving label data: {e}")
            return False
            
    except Exception as e:
        print(f"Unexpected error in fetch_label_by_mbid: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if should_close_conn and conn:
            try:
                conn.close()
            except:
                pass

# DISCOGS

def init_discogs_config(config):
    """
    Initialize Discogs configuration from config dict
    
    Args:
        config (dict): Configuration dictionary
    """
    global DISCOGS_TOKEN, USER_AGENT
    
    # Get Discogs token from config
    DISCOGS_TOKEN = config.get('discogs_token')
    
    # Get user agent from config if available
    if 'user_agent' in config:
        USER_AGENT = config['user_agent']
    
    if DISCOGS_TOKEN:
        print(f"Discogs API token configured")
    else:
        print("Warning: No Discogs token configured. API requests will be limited.")
        print("Get a token at: https://www.discogs.com/settings/developers")


def fetch_discogs_label_info(discogs_url):
    """
    Fetch additional label information from Discogs
    
    Args:
        discogs_url (str): Discogs URL for the label
        
    Returns:
        dict: Dictionary with additional label information or None if error
    """
    try:
        if not discogs_url:
            return None
        
        # Extract label ID from URL
        # URLs like: https://www.discogs.com/label/1234-Label-Name
        import re
        match = re.search(r'/label/(\d+)', discogs_url)
        if not match:
            print(f"Could not extract label ID from Discogs URL: {discogs_url}")
            return None
        
        label_id = match.group(1)
        
        # Rate limiting for Discogs API
        time.sleep(1.5)
        
        # Discogs API endpoint
        api_url = f"https://api.discogs.com/labels/{label_id}"
        
        headers = {
            'User-Agent': USER_AGENT
        }
        
        # Add authorization if token is available
        if DISCOGS_TOKEN:
            headers['Authorization'] = f'Discogs token={DISCOGS_TOKEN}'
        
        print(f"Fetching Discogs data for label ID: {label_id}")
        
        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching from Discogs API: {e}")
            # If API fails, try scraping the page directly
            return scrape_discogs_label_page(discogs_url)
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"Error parsing Discogs JSON response: {e}")
            return None
        
        # Check for API errors
        if 'message' in data and 'error' in data.get('message', '').lower():
            print(f"Discogs API error: {data.get('message')}")
            return scrape_discogs_label_page(discogs_url)
        
        # Extract information from Discogs API response
        discogs_info = {}
        
        # Basic information
        if 'profile' in data and data['profile']:
            discogs_info['profile'] = data['profile']
        
        if 'contact_info' in data and data['contact_info']:
            discogs_info['contact_info'] = data['contact_info']
        
        # Parent label information
        if 'parent_label' in data and data['parent_label']:
            parent = data['parent_label']
            if isinstance(parent, dict) and 'name' in parent:
                discogs_info['parent_label'] = parent['name']
        
        # Extract URLs and social links
        urls = data.get('urls', [])
        social_links = []
        streaming_links = []
        purchase_links = []
        blog_links = []
        
        for url in urls:
            if not url:
                continue
                
            url_lower = url.lower()
            
            # Categorize URLs
            if any(social in url_lower for social in ['facebook', 'twitter', 'instagram', 'youtube']):
                social_links.append({'type': 'social', 'url': url})
            elif any(stream in url_lower for stream in ['spotify', 'soundcloud', 'bandcamp']):
                streaming_links.append({'type': 'streaming', 'url': url})
            elif any(shop in url_lower for shop in ['shop', 'store', 'buy', 'purchase']):
                purchase_links.append({'type': 'purchase', 'url': url})
            elif any(blog in url_lower for blog in ['blog', 'news', 'press']):
                blog_links.append({'type': 'blog', 'url': url})
        
        # Serialize URL collections (combine with existing if present)
        if social_links:
            discogs_info['social_links'] = json.dumps(social_links)
        if streaming_links:
            discogs_info['streaming_links'] = json.dumps(streaming_links)
        if purchase_links:
            discogs_info['purchase_links'] = json.dumps(purchase_links)
        if blog_links:
            discogs_info['blog_links'] = json.dumps(blog_links)
        
        # Extract sublabels/subsidiaries
        sublabels = data.get('sublabels', [])
        if sublabels:
            subsidiary_list = []
            for sublabel in sublabels:
                if isinstance(sublabel, dict) and 'name' in sublabel:
                    subsidiary_list.append({
                        'name': sublabel['name'],
                        'id': sublabel.get('id'),
                        'resource_url': sublabel.get('resource_url')
                    })
            
            if subsidiary_list:
                discogs_info['subsidiary_labels'] = json.dumps(subsidiary_list)
                print(f"Found {len(subsidiary_list)} sublabels")
        
        # Extract founder/key personnel information
        if 'data_quality' in data:  # This often contains founder info in the notes
            discogs_info['founder_info'] = data.get('data_quality')
        
        print(f"Successfully extracted Discogs data for {data.get('name', 'Unknown Label')}")
        return discogs_info
        
    except Exception as e:
        print(f"Error fetching Discogs label info: {e}")
        import traceback
        traceback.print_exc()
        return None

def scrape_discogs_label_page(discogs_url):
    """
    Scrape Discogs label page when API is not available
    
    Args:
        discogs_url (str): Discogs URL for the label
        
    Returns:
        dict: Dictionary with scraped label information or None if error
    """
    try:
        print(f"Scraping Discogs page: {discogs_url}")
        
        # Rate limiting
        time.sleep(2)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(discogs_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        scraped_info = {}
        
        # Try to extract profile/description
        profile_section = soup.find('div', {'class': 'profile'})
        if profile_section:
            profile_text = profile_section.get_text(strip=True)
            if profile_text and len(profile_text) > 10:
                scraped_info['profile'] = profile_text
        
        # Try to extract contact info
        contact_section = soup.find('div', {'class': 'section_contact'})
        if contact_section:
            contact_text = contact_section.get_text(strip=True)
            if contact_text:
                scraped_info['contact_info'] = contact_text
        
        # Extract URLs from the page
        social_links = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            if any(social in href.lower() for social in ['facebook', 'twitter', 'instagram', 'youtube']):
                social_links.append({'type': 'social', 'url': href})
        
        if social_links:
            scraped_info['social_links'] = json.dumps(social_links)
        
        print(f"Successfully scraped Discogs page")
        return scraped_info if scraped_info else None
        
    except Exception as e:
        print(f"Error scraping Discogs page: {e}")
        return None

def fetch_wikipedia_content(wikipedia_url):
    """
    Fetch content from Wikipedia page
    
    Args:
        wikipedia_url (str): Wikipedia URL
        
    Returns:
        str: Wikipedia content or None if error
    """
    try:
        if not wikipedia_url:
            return None
        
        print(f"Fetching Wikipedia content from: {wikipedia_url}")
        
        # Rate limiting
        time.sleep(1)
        
        headers = {
            'User-Agent': USER_AGENT
        }
        
        response = requests.get(wikipedia_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract main content
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if not content_div:
            return None
        
        # Remove unwanted elements
        for unwanted in content_div.find_all(['script', 'style', 'table', 'div.navbox']):
            unwanted.decompose()
        
        # Get text content
        paragraphs = content_div.find_all('p')
        content_parts = []
        
        for p in paragraphs[:10]:  # Limit to first 10 paragraphs
            text = p.get_text(strip=True)
            if text and len(text) > 20:  # Only meaningful paragraphs
                content_parts.append(text)
        
        if content_parts:
            content = '\n\n'.join(content_parts)
            print(f"Successfully extracted Wikipedia content ({len(content)} characters)")
            return content[:5000]  # Limit content length
        
        return None
        
    except Exception as e:
        print(f"Error fetching Wikipedia content: {e}")
        return None

def get_albums_without_labels(conn, limit=None):
    """
    Get albums that don't have label relationships
    
    Args:
        conn: Database connection
        limit (int): Maximum number of albums to return
        
    Returns:
        list: List of (album_id, album_mbid, album_name) tuples
    """
    query = """
        SELECT a.id, a.mbid, a.name 
        FROM albums a
        WHERE a.mbid IS NOT NULL 
        AND NOT EXISTS (
            SELECT 1 FROM label_release_relationships lrr 
            WHERE lrr.album_id = a.id
        )
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    results = safe_db_query(conn, query)
    return results if results else []


def update_all_albums_with_labels(db_path, skip_existing=True):
    """
    Update all albums in the database with label information
    
    Args:
        db_path (str): Path to SQLite database
        skip_existing (bool): Skip albums that already have label relationships
    """
    # Enable WAL mode for better concurrency
    conn = sqlite3.connect(db_path, timeout=60)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=60000")  # 60 second timeout
        
        if skip_existing:
            print("Buscando álbumes sin información de sello...")
            albums = get_albums_without_labels(conn)
        else:
            print("Buscando todos los álbumes con MusicBrainz ID...")
            albums = safe_db_query(conn, "SELECT id, mbid, name FROM albums WHERE mbid IS NOT NULL")
        
        if not albums:
            print("No albums found to process")
            return
        
        total = len(albums)
        print(f"Found {total} albums {'without label information' if skip_existing else 'with MusicBrainz IDs'}")
        
        processed = 0
        errors = 0
        skipped = 0
        
        for i, album_data in enumerate(albums):
            if len(album_data) >= 3:
                album_id, album_mbid, album_name = album_data[:3]
            else:
                album_id, album_mbid = album_data
                album_name = "Unknown"
            
            print(f"Processing album {i+1}/{total}: {album_name} ({album_mbid})")
            
            # Validate album data
            if not album_mbid or album_mbid.strip() == '':
                print(f"Skipping album with empty MBID: {album_name}")
                skipped += 1
                continue
            
            try:
                success = fetch_label_by_album(db_path, album_mbid, conn)
                if success:
                    processed += 1
                elif success is False:  # Explicitly False (not None)
                    errors += 1
                    print(f"Failed to process album {album_mbid}")
                else:
                    skipped += 1
                    print(f"Skipped album {album_mbid}")
                    
            except Exception as e:
                errors += 1
                print(f"Error processing album {album_mbid}: {str(e)}")
                import traceback
                traceback.print_exc()
                # Continue with next album
        
        print(f"\nProcessing completed:")
        print(f"  Total albums: {total}")
        print(f"  Successfully processed: {processed}")
        print(f"  Errors: {errors}")
        print(f"  Skipped: {skipped}")
        
    except Exception as e:
        print(f"Critical error in update_all_albums_with_labels: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            conn.close()
        except:
            pass

    # Print summary statistics
    try:
        with sqlite3.connect(db_path) as conn:
            label_count = safe_db_query(conn, "SELECT COUNT(*) FROM labels", fetch_one=True)
            label_with_content = safe_db_query(conn, "SELECT COUNT(*) FROM labels WHERE wikipedia_content IS NOT NULL", fetch_one=True)
            relationships_count = safe_db_query(conn, "SELECT COUNT(*) FROM label_release_relationships", fetch_one=True)
            
            print(f"\nDatabase summary:")
            print(f"  Total labels: {label_count[0] if label_count else 0}")
            print(f"  Labels with Wikipedia content: {label_with_content[0] if label_with_content else 0}")
            print(f"  Label-album relationships: {relationships_count[0] if relationships_count else 0}")
    except Exception as e:
        print(f"Error getting database summary: {e}")



def safe_db_query(conn, query, params=None, fetch_one=False):
    """
    Execute a database query safely with proper error handling
    
    Args:
        conn: Database connection
        query (str): SQL query
        params (tuple): Query parameters
        fetch_one (bool): Whether to fetch only one result
        
    Returns:
        Query result or None if error
    """
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_one:
            return cursor.fetchone()
        else:
            return cursor.fetchall()
            
    except sqlite3.Error as e:
        print(f"Database query error: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        return None
    except Exception as e:
        print(f"Unexpected error in database query: {e}")
        return None

def repair_database_schema(db_path):
    """
    Verifica y repara posibles problemas en el esquema de la base de datos
    que podrían estar impidiendo guardar contenido de Wikipedia
    
    Args:
        db_path (str): Ruta a la base de datos SQLite
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Iniciando verificación y reparación de la base de datos...")
        
        # 1. Verificar el tipo de columna para wikipedia_content
        cursor.execute("PRAGMA table_info(labels)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        repairs_needed = False
        
        if 'wikipedia_content' in columns:
            content_type = columns['wikipedia_content']
            print(f"Tipo actual de columna wikipedia_content: {content_type}")
            
            # Si no es TEXT, necesitamos corregirlo
            if content_type != 'TEXT':
                repairs_needed = True
                print("El tipo de columna wikipedia_content es incorrecto.")
        else:
            repairs_needed = True
            print("La columna wikipedia_content no existe en la tabla labels.")
        
        if repairs_needed:
            print("Se necesitan reparaciones. Creando una nueva tabla con el esquema correcto...")
            
            # Crear una tabla temporal con el esquema correcto
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS labels_new (
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
                mb_last_updated TIMESTAMP,
                profile TEXT,
                parent_label TEXT,
                parent_label_id INTEGER,
                contact_info TEXT,
                social_links TEXT,
                streaming_links TEXT,
                purchase_links TEXT,
                blog_links TEXT,
                founder_info TEXT,
                creative_persons TEXT,
                signed_artists TEXT,
                subsidiary_labels TEXT,
                FOREIGN KEY (parent_label_id) REFERENCES labels(id)
            )
            """)
            
            # Copiar los datos a la nueva tabla
            try:
                existing_columns = ', '.join(columns.keys())
                cursor.execute(f"INSERT INTO labels_new SELECT {existing_columns} FROM labels")
            except sqlite3.OperationalError as e:
                print(f"Error al copiar datos: {e}")
                print("Intentando copiar columna por columna...")
                
                # Obtener los registros actuales
                cursor.execute("SELECT * FROM labels")
                records = cursor.fetchall()
                
                # Obtener los nombres de las columnas actuales
                cursor.execute("PRAGMA table_info(labels)")
                current_columns = [col[1] for col in cursor.fetchall()]
                
                # Insertar manualmente los registros
                for record in records:
                    values = []
                    for i, col_name in enumerate(current_columns):
                        values.append(record[i])
                    
                    # Asegurar que tenemos suficientes placeholders
                    placeholders = ', '.join(['?' for _ in values])
                    
                    cursor.execute(f"""
                    INSERT INTO labels_new ({', '.join(current_columns)})
                    VALUES ({placeholders})
                    """, values)
            
            # Renombrar tablas
            cursor.execute("DROP TABLE labels")
            cursor.execute("ALTER TABLE labels_new RENAME TO labels")
            
            # Recrear índices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_labels_mbid ON labels(mbid)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_labels_name ON labels(name)")
            
            print("Reparación completada. Ahora wikipedia_content es de tipo TEXT.")
        else:
            print("El esquema de la base de datos parece correcto.")
        
        # 2. Verificar integridad general de la base de datos
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        
        if integrity == 'ok':
            print("Verificación de integridad de la base de datos: OK")
        else:
            print(f"La base de datos tiene problemas de integridad: {integrity}")
            print("Realizando VACUUM para intentar reparar...")
            cursor.execute("VACUUM")
            conn.commit()
            print("VACUUM completado. Verifica manualmente si la base de datos está en buen estado.")
        
        # 3. Verificar y reparar tamaño de página y otros parámetros
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        print(f"Tamaño de página actual: {page_size} bytes")
        
        if page_size < 4096:
            print("El tamaño de página es pequeño. Optimizando...")
            cursor.execute("PRAGMA page_size = 4096")
            cursor.execute("VACUUM")
            conn.commit()
            print("Tamaño de página aumentado a 4096 bytes para mejor rendimiento.")
        
        # 4. Verificar índices
        cursor.execute("PRAGMA index_list(labels)")
        indices = cursor.fetchall()
        print(f"La tabla labels tiene {len(indices)} índices:")
        for idx in indices:
            print(f"  - {idx[1]}")
        
        # 5. Realizar mantenimiento general (ANALYZE)
        cursor.execute("ANALYZE")
        conn.commit()
        print("Análisis de la base de datos completado para optimizar consultas.")
        
        print("\nReparación y optimización de la base de datos completada.")
        
    except Exception as e:
        print(f"Error durante la reparación: {str(e)}")
        traceback.print_exc()
    finally:
        conn.close()




def check_wikipedia_content(db_path, label_mbid=None):
    """
    Verifica si el contenido de Wikipedia se ha guardado correctamente
    
    Args:
        db_path (str): Ruta a la base de datos SQLite
        label_mbid (str, optional): Si se proporciona, verifica solo este sello específico
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        if label_mbid:
            # Verificar un sello específico
            cursor.execute("""
                SELECT name, wikipedia_url, wikipedia_content, wikipedia_updated
                FROM labels WHERE mbid = ?
            """, (label_mbid,))
            labels = cursor.fetchall()
        else:
            # Verificar todos los sellos con URL de Wikipedia
            cursor.execute("""
                SELECT name, wikipedia_url, wikipedia_content, wikipedia_updated
                FROM labels WHERE wikipedia_url IS NOT NULL
                ORDER BY wikipedia_updated DESC
                LIMIT 20
            """)
            labels = cursor.fetchall()
        
        if not labels:
            print("No se encontraron sellos con URL de Wikipedia.")
            return
        
        print("\nVerificando contenido de Wikipedia:")
        print("=" * 80)
        
        for name, url, content, updated in labels:
            print(f"Sello: {name}")
            print(f"URL: {url}")
            
            if content:
                print(f"Contenido: {len(content)} caracteres")
                preview = content[:150] + "..." if len(content) > 150 else content
                print(f"Vista previa: {preview}")
                print(f"Última actualización: {updated}")
            else:
                print("Contenido: No disponible")
            
            print("-" * 80)
    
    finally:
        conn.close()





def main(config=None):
    """
    Función principal que puede recibir configuración del orquestador
    
    Args:
        config (dict): Configuración desde el archivo JSON
    """
    # Si no hay configuración, usar argumentos de línea de comandos
    if config is None:
        parser = argparse.ArgumentParser(description='Extract MusicBrainz label information')
        parser.add_argument('--config', help='Path to json config')
        parser.add_argument('--db-path', help='Path to the SQLite database')
        parser.add_argument('--mode', choices=['interactive', 'auto'], default='interactive',
                          help='Execution mode: interactive or auto')
        parser.add_argument('--skip-existing', action='store_true', 
                          help='Skip albums that already have label relationships')
        parser.add_argument('--update-wikipedia', action='store_true',
                          help='Update Wikipedia content for labels')
        args = parser.parse_args()

        # Cargar configuración si se proporciona
        if args.config:
            with open(args.config, 'r') as f:
                config_data = json.load(f)
            
            # Combinar configuraciones
            config = {}
            config.update(config_data.get("common", {}))
            config.update(config_data.get("musicbrainz/mb_sellos", {}))
        else:
            config = {}
        
        # Sobrescribir con argumentos de línea de comandos
        if args.db_path:
            config['db_path'] = args.db_path
        if args.mode:
            config['mode'] = args.mode
        if args.skip_existing:
            config['skip_existing'] = True
        if args.update_wikipedia:
            config['update_wikipedia'] = True

    # Inicializar configuración de Discogs
    init_discogs_config(config)
    
    # Obtener configuración
    db_path = config.get('db_path')
    mode = config.get('mode', 'interactive')
    skip_existing = config.get('skip_existing', True)
    update_wikipedia = config.get('update_wikipedia', False)
    force_update = config.get('force_update', False)
    batch_size = config.get('batch_size', 50)
    
    # Validar db_path
    if not db_path:
        if mode == 'interactive':
            db_path = input("Enter the path to your SQLite database file: ")
        else:
            print("Error: db_path is required")
            return 1
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} doesn't exist.")
        return 1
        
    # Initialize database tables
    create_label_tables(db_path)
    
    # Modo automático - procesar todos los álbumes
    if mode == 'auto':
        print(f"Running in automatic mode...")
        print(f"Configuration:")
        print(f"  Database: {db_path}")
        print(f"  Skip existing: {skip_existing}")
        print(f"  Force update: {force_update}")
        print(f"  Batch size: {batch_size}")
        print(f"  Update Wikipedia: {update_wikipedia}")
        
        # Actualizar álbumes con información de sellos
        update_all_albums_with_labels(db_path, skip_existing=skip_existing)
        
        # Actualizar contenido de Wikipedia si se solicita
        if update_wikipedia:
            print("\nUpdating Wikipedia content...")
            updated = update_wikipedia_content(db_path)
            print(f"Wikipedia content updated for {updated} labels.")
        
        print("Automatic processing completed.")
        return 0
    
    # Modo interactivo (código existente)
    while True:
        print("\nMusicBrainz Label Data Fetcher")
        print("1. Search for a label")
        print("2. Fetch label by MusicBrainz ID")
        print("3. Fetch labels for an album")
        print("4. Update all albums with label information")
        print("5. Show label details")
        print("6. Show database statistics")
        print("7. Update Wikipedia URLs from MusicBrainz")
        print("8. Update Wikipedia content for labels with URLs")
        print("9. Update all missing information for labels")
        print("10. Verify Wikipedia content")
        print("11. Repair database schema")
        print("12. Exit")
        
        choice = input("Enter your choice (1-12): ")
        
        
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
                        
                        # Show the info that was saved
                        print(f"\nSaved label information:")
                        print(f"Name: {label_info['name']}")
                        print(f"Country: {label_info['country'] or 'Unknown'}")
                        print(f"Founded: {label_info['founded_year'] or 'Unknown'}")
                        print(f"Type: {label_info['mb_type'] or 'Unknown'}")
                        print(f"Code: {label_info['mb_code'] or 'Unknown'}")
                        
                        # Display URLs
                        if label_info['official_website']:
                            print(f"Official website: {label_info['official_website']}")
                        if label_info['wikipedia_url']:
                            print(f"Wikipedia URL: {label_info['wikipedia_url']}")
                            if label_info['wikipedia_content']:
                                print(f"Wikipedia content: {len(label_info['wikipedia_content'])} characters")
                        if label_info['discogs_url']:
                            print(f"Discogs URL: {label_info['discogs_url']}")
                        if label_info['bandcamp_url']:
                            print(f"Bandcamp URL: {label_info['bandcamp_url']}")
                            
                        # Show success message
                        print(f"\nSuccessfully saved label: {label_info['name']}")
            else:
                print("No results found.")
        
        elif choice == '2':
            label_mbid = input("Enter MusicBrainz ID: ")
            label_data = fetch_label_data(label_mbid)
            
            if label_data:
                label_info, label_rels, release_rels = extract_label_info(label_data)
                save_label_data(db_path, label_info, label_rels, release_rels)
                
                # Show info about the number of relationships found
                print(f"\nSaved label information:")
                print(f"Name: {label_info['name']}")
                print(f"Label relationships: {len(label_rels)}")
                print(f"Release relationships: {len(release_rels)}")
                print(f"Wikipedia content: {'Yes' if label_info['wikipedia_content'] else 'No'}")
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
            skip_choice = input("Skip albums that already have label relationships? (y/n, default: y): ")
            skip_existing_albums = skip_choice.lower() != 'n'
            
            confirm = input(f"This will update albums with label information (skip_existing={skip_existing_albums}). Continue? (y/n): ")
            
            if confirm.lower() == 'y':
                update_all_albums_with_labels(db_path, skip_existing=skip_existing_albums)
                print("Albums updated with label information.")
                
        elif choice == '5':
            # Show label details by MBID or search
            mbid_option = input("Enter a MusicBrainz ID directly or type 'search' to find by name: ")
            
            if mbid_option.lower() == 'search':
                search_term = input("Enter label name to search: ")
                results = search_labels(search_term)
                
                if results:
                    print("\nSearch results:")
                    for i, result in enumerate(results):
                        print(f"{i+1}. {result['name']} ({result.get('country', 'Unknown')}) - {result['mbid']}")
                    
                    choice = input("\nEnter number to view details: ")
                    if choice.isdigit() and 1 <= int(choice) <= len(results):
                        mbid = results[int(choice)-1]['mbid']
                        display_label_info(db_path, mbid)
                else:
                    print("No labels found matching that name.")
            else:
                # Assume it's a MBID
                display_label_info(db_path, mbid_option)
                
        elif choice == '6':
            # Show database statistics
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM labels")
                label_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM labels WHERE wikipedia_content IS NOT NULL")
                wiki_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM label_relationships")
                rel_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM label_release_relationships")
                album_rel_count = cursor.fetchone()[0]
                
                print("\nDatabase Statistics:")
                print(f"Total labels: {label_count}")
                if label_count > 0:
                    print(f"Labels with Wikipedia content: {wiki_count} ({wiki_count/label_count*100:.1f}%)")
                else:
                    print("Labels with Wikipedia content: 0 (0.0%)")
                print(f"Label-to-label relationships: {rel_count}")
                print(f"Label-to-album relationships: {album_rel_count}")
                
                #conn.close()
                
        elif choice == '7':
            wiki_url_choice = input("¿Actualizar URLs de Wikipedia para todos los sellos o solo uno específico? (all/specific): ")
            
            if wiki_url_choice.lower() == 'specific':
                mbid = input("Introduce el MusicBrainz ID del sello: ")
                if mbid:
                    updated = update_wikipedia_urls(db_path, mbid)
                    print(f"Actualización completada: {updated} URLs de Wikipedia actualizadas.")
            else:
                confirm = input("¿Estás seguro de que quieres actualizar las URLs de Wikipedia para TODOS los sellos? Esto puede tardar y generar muchas solicitudes a MusicBrainz. (y/n): ")
                if confirm.lower() == 'y':
                    updated = update_wikipedia_urls(db_path)
                    print(f"Actualización completada: {updated} URLs de Wikipedia actualizadas.")

        # Actualiza los números de las siguientes opciones del menú
        elif choice == '8':
            wiki_choice = input("¿Actualizar contenido de Wikipedia para todos los sellos o solo uno específico? (all/specific): ")
            
            if wiki_choice.lower() == 'specific':
                mbid = input("Introduce el MusicBrainz ID del sello: ")
                if mbid:
                    updated = update_wikipedia_content(db_path, mbid)
                    print(f"Actualización completada: {updated} sellos actualizados.")
            else:
                confirm = input("¿Estás seguro de que quieres actualizar TODOS los sellos con URLs de Wikipedia? Esto puede tardar y generar muchas solicitudes a Wikipedia. (y/n): ")
                if confirm.lower() == 'y':
                    updated = update_wikipedia_content(db_path)
                    print(f"Actualización completada: {updated} sellos actualizados.")

        elif choice == '9':
            confirm = input("¿Quieres actualizar todas las etiquetas con información incompleta? Esto puede tardar un tiempo. (y/n): ")
            if confirm.lower() == 'y':
                update_existing_labels(db_path)
                print("Actualización de etiquetas completada.")

        elif choice == '10':
            check_choice = input("¿Verificar contenido de Wikipedia para todos los sellos o uno específico? (all/specific): ")
            
            if check_choice.lower() == 'specific':
                mbid = input("Introduce el MusicBrainz ID del sello: ")
                if mbid:
                    check_wikipedia_content(db_path, mbid)
            else:
                check_wikipedia_content(db_path)
                
        elif choice == '11':
            confirm = input("¿Estás seguro de que quieres reparar el esquema de la base de datos? Esto puede modificar la estructura de las tablas. Se recomienda hacer una copia de seguridad primero. (y/n): ")
            if confirm.lower() == 'y':
                repair_database_schema(db_path)
                
        elif choice == '12':  # Actualizar número de la opción Exit
            break
                
        else:
            print("Invalid choice. Please try again.")