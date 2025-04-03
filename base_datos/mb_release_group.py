#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import time
import requests
from datetime import datetime
import traceback
from typing import Dict, List, Optional, Tuple, Any
import re

# MusicBrainz API constants
MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2"
USER_AGENT = "MyMusicApp/1.0 (your-email@example.com)"
RATE_LIMIT = 1.1  # seconds between requests

class MusicBrainzReleaseGroups:
    def __init__(self, db_path: str, config: Dict = None):
        self.db_path = db_path
        self.config = config or {}
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Modo de operación: 'auto' o 'manual'
        self.mode = self.config.get('mode', 'auto')
        self.cache_file = self.config.get('cache_file', 'mb_release_groups_cache.json')
        
        # Cargar caché si existe
        self.cache = self.load_cache()
        
        # Conjunto para rastrear columnas aprobadas/rechazadas en modo manual
        self.approved_columns = set(self.cache.get('approved_columns', []))
        self.rejected_columns = set(self.cache.get('rejected_columns', []))
        
        # Estadísticas para reporting
        self.stats = self.cache.get('stats', {
            "total_releases": 0,
            "processed_releases": 0,
            "release_groups_added": 0,
            "wikidata_entries_added": 0,
            "failed_fetch": 0,
            "skipped": 0,
            "new_columns_added": 0,
            "columns_rejected": 0
        })
        
        # Rastrear el último ID procesado
        self.last_processed_id = self.cache.get('last_processed_id', 0)
        
        self.setup_tables()


    def load_cache(self) -> Dict:
        """Cargar datos de caché desde archivo JSON."""
        if not self.cache_file:
            return {}
            
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading cache file: {str(e)}")
        
        return {}

    def save_cache(self) -> None:
        """Guardar datos de caché en archivo JSON."""
        if not self.cache_file:
            return
            
        try:
            # Actualizar datos de caché
            cache_data = {
                'last_processed_id': self.last_processed_id,
                'stats': self.stats,
                'approved_columns': list(self.approved_columns),
                'rejected_columns': list(self.rejected_columns),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Crear directorio si no existe
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
                
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving cache file: {str(e)}")




    def setup_tables(self) -> None:
        """Create necessary tables if they don't exist and añade campos necesarios."""
        # Table for release groups
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS mb_release_group (
            id INTEGER PRIMARY KEY,
            mbid TEXT NOT NULL UNIQUE,
            title TEXT,
            artist_credit TEXT,
            first_release_date TEXT,
            primary_type TEXT,
            secondary_types TEXT,
            album_id INTEGER,
            artist_id INTEGER,
            genre TEXT,
            associated_singles TEXT,
            discogs_url TEXT,
            rateyourmusic_url TEXT,
            allmusic_url TEXT,
            wikidata_id TEXT,
            last_updated TIMESTAMP,
            FOREIGN KEY (album_id) REFERENCES albums(id),
            FOREIGN KEY (artist_id) REFERENCES artists(id)
        )
        ''')
        
        # Table for wikidata entries - aseguramos que tiene todas las columnas necesarias
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS mb_wikidata (
            id INTEGER PRIMARY KEY,
            wikidata_id TEXT NOT NULL,
            release_group_mbid TEXT,
            album_id INTEGER,
            artist_id INTEGER,
            label_id INTEGER, 
            property_id TEXT,
            property_label TEXT,
            property_value TEXT,
            last_updated TIMESTAMP,
            FOREIGN KEY (album_id) REFERENCES albums(id),
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (label_id) REFERENCES labels(id),
            FOREIGN KEY (release_group_mbid) REFERENCES mb_release_group(mbid)
        )
        ''')
        
        # Verificar y añadir las columnas necesarias a mb_wikidata
        try:
            # Verificar primero si la tabla existe
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mb_wikidata'")
            if self.cursor.fetchone():
                # Comprobar si la columna value_type existe
                try:
                    self.cursor.execute("SELECT value_type FROM mb_wikidata LIMIT 1")
                except sqlite3.OperationalError:
                    # La columna no existe, así que la agregamos
                    self.cursor.execute("ALTER TABLE mb_wikidata ADD COLUMN value_type TEXT")
                    print("Added column 'value_type' to mb_wikidata table")
                
                # Comprobar si la columna is_link existe
                try:
                    self.cursor.execute("SELECT is_link FROM mb_wikidata LIMIT 1")
                except sqlite3.OperationalError:
                    # La columna no existe, así que la agregamos
                    self.cursor.execute("ALTER TABLE mb_wikidata ADD COLUMN is_link INTEGER DEFAULT 0")
                    print("Added column 'is_link' to mb_wikidata table")
        except Exception as e:
            print(f"Error checking/adding columns: {e}")
        
        # Añadir las columnas aprobadas previamente a la tabla mb_release_group
        for column in self.approved_columns:
            self.add_column_if_not_exists('mb_release_group', column, 'TEXT')
        
        # Create indexes for better performance
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_mb_release_group_mbid ON mb_release_group(mbid)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_mb_release_group_album_id ON mb_release_group(album_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_mb_wikidata_id ON mb_wikidata(wikidata_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_mb_wikidata_release_group ON mb_wikidata(release_group_mbid)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_mb_wikidata_property ON mb_wikidata(property_id)')
        
        self.conn.commit()
        print("Database tables setup complete")
        print(f"Mode: {self.mode}")
        if self.approved_columns:
            print(f"Previously approved columns: {', '.join(self.approved_columns)}")

    def add_column_if_not_exists(self, table: str, column: str, column_type: str) -> bool:
        """Añadir una columna a la tabla si no existe ya."""
        try:
            # Verificar si la columna ya existe
            self.cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
            return False  # La columna ya existe
        except sqlite3.OperationalError:
            # La columna no existe, así que la agregamos
            safe_column = self.safe_column_name(column)
            self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN {safe_column} {column_type}")
            print(f"Added column '{safe_column}' to {table} table")
            return True

    def safe_column_name(self, column: str) -> str:
        """Convertir un nombre de columna en un nombre seguro para SQL."""
        # Eliminar caracteres especiales y espacios, convertir a minúsculas
        safe_name = re.sub(r'[^\w]', '_', column.lower())
        
        # Asegurarse de que comienza con una letra o guion bajo
        if safe_name and not safe_name[0].isalpha() and safe_name[0] != '_':
            safe_name = 'col_' + safe_name
        
        # Truncar si es demasiado largo
        if len(safe_name) > 63:  # Límite común en muchas bases de datos
            safe_name = safe_name[:63]
        
        return safe_name

    def get_releases_with_mbid(self) -> List[Dict]:
        """Retrieve all releases in the database that have a MusicBrainz ID."""
        # Si tenemos un último ID procesado, continuar desde allí
        start_id = self.last_processed_id if self.last_processed_id > 0 else 0
        
        self.cursor.execute('''
        SELECT a.id as album_id, a.name as album_name, a.mbid as release_mbid, 
            ar.id as artist_id, ar.name as artist_name, ar.mbid as artist_mbid
        FROM albums a
        JOIN artists ar ON a.artist_id = ar.id
        WHERE a.mbid IS NOT NULL AND a.mbid != '' AND a.id > ?
        ORDER BY a.id
        ''', (start_id,))
        
        releases = [dict(row) for row in self.cursor.fetchall()]
        self.stats["total_releases"] = len(releases)
        return releases

    
    def fetch_release_group(self, release_mbid: str) -> Optional[Dict]:
        """Fetch release group data for a release from MusicBrainz API."""
        url = f"{MUSICBRAINZ_API_URL}/release/{release_mbid}"
        params = {
            "inc": "release-groups+url-rels+genres",
            "fmt": "json"
        }
        
        headers = {
            "User-Agent": USER_AGENT
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            time.sleep(RATE_LIMIT)  # Respect rate limit
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching release {release_mbid}: {str(e)}")
            self.stats["failed_fetch"] += 1
            return None
    
    def fetch_release_group_details(self, group_mbid: str) -> Optional[Dict]:
        """Fetch detailed information about a release group."""
        url = f"{MUSICBRAINZ_API_URL}/release-group/{group_mbid}"
        params = {
            "inc": "url-rels+artist-credits+releases+genres",
            "fmt": "json"
        }
        
        headers = {
            "User-Agent": USER_AGENT
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            time.sleep(RATE_LIMIT)  # Respect rate limit
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching release group {group_mbid}: {str(e)}")
            return None
    
    def extract_release_group_data(self, release_data: Dict, album_id: int, artist_id: int) -> Optional[Dict]:
        """Extract release group data from release response."""
        if 'release-group' not in release_data:
            print(f"No release-group found in response")
            return None
            
        release_group = release_data['release-group']
        group_mbid = release_group.get('id')
        
        if not group_mbid:
            print(f"No MBID found for release group")
            return None
            
        # Fetch more detailed release group info
        group_details = self.fetch_release_group_details(group_mbid)
        if not group_details:
            print(f"Could not fetch details for release group {group_mbid}")
            
        # Extract basic release group data
        result = {
            'mbid': group_mbid,
            'title': release_group.get('title', ''),
            'artist_credit': ", ".join([credit.get('name', '') for credit in release_group.get('artist-credit', [])]),
            'first_release_date': release_group.get('first-release-date', ''),
            'primary_type': release_group.get('primary-type', ''),
            'secondary_types': ', '.join(release_group.get('secondary-types', [])),
            'album_id': album_id,
            'artist_id': artist_id,
            'genre': '', 
            'associated_singles': '',
            'discogs_url': '',
            'rateyourmusic_url': '',
            'allmusic_url': '',
            'wikidata_id': '',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Extract genres if available
        if 'genres' in release_group:
            genres = [genre.get('name', '') for genre in release_group.get('genres', [])]
            result['genre'] = ', '.join(genres)
            
        # Look for associated singles and URLs in the detailed data
        if group_details:
            # Extract URLs from relations
            if 'relations' in group_details:
                for relation in group_details['relations']:
                    if relation['target-type'] == 'url' and 'url' in relation:
                        url = relation['url']['resource']
                        relation_type = relation.get('type', '')
                        
                        if 'discogs.com' in url:
                            result['discogs_url'] = url
                        elif 'rateyourmusic.com' in url or 'rym.com' in url:
                            result['rateyourmusic_url'] = url
                        elif 'allmusic.com' in url:
                            result['allmusic_url'] = url
                        elif 'wikidata.org' in url:
                            result['wikidata_id'] = url.split('/')[-1]
                            
            # Find associated singles
            if 'releases' in group_details:
                singles = []
                for release in group_details['releases']:
                    # Check if it's a single or has fewer tracks
                    if (release.get('status') == 'Official' and 
                        (release.get('media', [{}])[0].get('format') in ['CD Single', '7"', '12"'] or 
                         release.get('track-count', 0) < 4)):
                        singles.append({
                            'mbid': release.get('id'),
                            'title': release.get('title'),
                            'date': release.get('date')
                        })
                
                # Check if any of these singles exist in our database
                associated_singles = []
                for single in singles:
                    self.cursor.execute('''
                    SELECT id, name FROM albums WHERE mbid = ?
                    ''', (single['mbid'],))
                    result_row = self.cursor.fetchone()
                    if result_row:
                        associated_singles.append({
                            'id': result_row['id'],
                            'name': result_row['name'],
                            'mbid': single['mbid']
                        })
                
                if associated_singles:
                    result['associated_singles'] = json.dumps(associated_singles)
                    
        return result
    
  

    
    def get_property_label(self, property_id: str, property_data: Dict) -> str:
        """Obtener la etiqueta legible de una propiedad de Wikidata."""
        if property_id in property_data:
            # Intentar primero en español, luego en inglés
            if 'labels' in property_data[property_id]:
                if 'es' in property_data[property_id]['labels']:
                    return property_data[property_id]['labels']['es']['value']
                elif 'en' in property_data[property_id]['labels']:
                    return property_data[property_id]['labels']['en']['value']
        
        # Si no se encuentra, devolver el ID de la propiedad
        return property_id

    def should_skip_property(self, property_id: str, property_label: str) -> bool:
        """Determinar si una propiedad debe omitirse."""
        # Propiedades que queremos omitir
        skip_properties = {
            'P31',   # instance of (normalmente redundante)
            'P577',  # publication date (si ya está en albums)
            'P407',  # language of work
            'P361',  # part of (normalmente redundante)
            'P527',  # has part (normalmente redundante)
            'P1411', # nominated for (suele ser demasiado específico)
            'P1343', # described by source (metadatos no útiles)
            'P2860', # cites (normalmente irrelevante para música)
        }
        
        # Lista configurable desde los parámetros
        if 'skip_properties' in self.config:
            skip_properties.update(self.config['skip_properties'])
        
        # Comprobar si está en la lista de rechazados
        if property_id in self.rejected_columns or property_label in self.rejected_columns:
            return True
        
        return property_id in skip_properties

   
    def get_value_or_link(self, claim: Dict, entity_data: Dict) -> Tuple[str, str, bool]:
        """
        Extraer el valor real o enlace de un claim de Wikidata.
        
        Returns:
            Tuple[str, str, bool]: (valor procesado, tipo de valor, es_enlace)
        """
        if 'mainsnak' not in claim or 'datavalue' not in claim['mainsnak']:
            return "", "unknown", False
            
        datavalue = claim['mainsnak']['datavalue']
        value_type = datavalue.get('type', '')
        property_id = claim['mainsnak'].get('property', '')
        
        # Valor por defecto
        processed_value = ""
        is_link = False
        
        # Intentar usar el formatter URL si está disponible
        formatter_urls = entity_data.get('formatter_urls', {})
        if property_id in formatter_urls and value_type == 'string':
            formatter_url = formatter_urls[property_id]
            if '$1' in formatter_url:
                # Reemplazar $1 con el valor
                processed_value = formatter_url.replace('$1', datavalue['value'])
                is_link = True
                return processed_value, value_type, is_link
        
        # Procesamiento según el tipo de valor
        if value_type == 'string':
            processed_value = datavalue['value']
            
            # Verificar si parece una URL
            if processed_value.startswith(('http://', 'https://')):
                is_link = True
        
        elif value_type == 'wikibase-entityid':
            entity_id = datavalue['value'].get('id', '')
            related_entities = entity_data.get('related_entities', {})
            
            # Buscar etiqueta en español o inglés para entidades
            if entity_id in related_entities:
                entity = related_entities[entity_id]
                
                # Buscar enlaces externos en la entidad relacionada
                if 'claims' in entity:
                    # Buscar la propiedad oficial URL (P856) o cualquier URL
                    url_found = False
                    
                    # Primero buscar URL oficial
                    if 'P856' in entity['claims']:
                        for url_claim in entity['claims']['P856']:
                            if 'mainsnak' in url_claim and 'datavalue' in url_claim['mainsnak']:
                                url_value = url_claim['mainsnak']['datavalue'].get('value', '')
                                if url_value and isinstance(url_value, str) and url_value.startswith(('http://', 'https://')):
                                    processed_value = url_value
                                    is_link = True
                                    url_found = True
                                    break
                    
                    # Si no encuentra URL oficial, buscar cualquier URL
                    if not url_found:
                        for prop_id, claims_list in entity['claims'].items():
                            if prop_id.startswith('P') and not url_found:
                                for subclaim in claims_list:
                                    if 'mainsnak' in subclaim and 'datavalue' in subclaim['mainsnak']:
                                        subclaim_value = subclaim['mainsnak']['datavalue'].get('value', '')
                                        if isinstance(subclaim_value, str) and subclaim_value.startswith(('http://', 'https://')):
                                            processed_value = subclaim_value
                                            is_link = True
                                            url_found = True
                                            break
                
                # Si no encontramos URL, usar etiqueta
                if not is_link:
                    if 'labels' in entity:
                        if 'es' in entity['labels']:
                            processed_value = entity['labels']['es']['value']
                        elif 'en' in entity['labels']:
                            processed_value = entity['labels']['en']['value']
                        else:
                            processed_value = entity_id
                
                # Si aún no tenemos valor, intentar con sitelinks
                if not is_link and not processed_value and 'sitelinks' in entity:
                    # Preferir Wikipedia en español
                    if 'eswiki' in entity['sitelinks']:
                        title = entity['sitelinks']['eswiki']['title']
                        processed_value = f"https://es.wikipedia.org/wiki/{title.replace(' ', '_')}"
                        is_link = True
                    # Luego Wikipedia en inglés
                    elif 'enwiki' in entity['sitelinks']:
                        title = entity['sitelinks']['enwiki']['title']
                        processed_value = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                        is_link = True
            
            # Si no pudimos encontrar información, usar el ID de Wikidata
            if not processed_value:
                processed_value = entity_id
                
            # Si el valor final es solo el ID de entidad, crear link a Wikidata
            if processed_value == entity_id:
                processed_value = f"https://www.wikidata.org/wiki/{entity_id}"
                is_link = True
        
        elif value_type == 'time':
            time_value = datavalue['value']
            # Convertir formato ISO a formato más legible
            # Ejemplo: +1967-01-01T00:00:00Z -> 1967-01-01
            if 'time' in time_value:
                time_str = time_value['time']
                # Eliminar el + inicial si existe y la parte de la hora
                if time_str.startswith('+'):
                    time_str = time_str[1:]
                time_str = time_str.split('T')[0]
                processed_value = time_str
        
        elif value_type == 'monolingualtext':
            if 'text' in datavalue['value']:
                processed_value = datavalue['value']['text']
        
        elif value_type == 'quantity':
            if 'amount' in datavalue['value']:
                amount = datavalue['value']['amount']
                unit = datavalue['value'].get('unit', '')
                if unit and unit != '1':
                    # Si la unidad es una entidad de Wikidata, extraer solo el ID
                    if 'wikidata.org/entity/' in unit:
                        unit_id = unit.split('/')[-1]
                        processed_value = f"{amount} {unit_id}"
                    else:
                        processed_value = f"{amount} {unit}"
                else:
                    processed_value = amount
        
        elif value_type == 'globecoordinate':
            if 'latitude' in datavalue['value'] and 'longitude' in datavalue['value']:
                lat = datavalue['value']['latitude']
                lon = datavalue['value']['longitude']
                processed_value = f"{lat}, {lon}"
        
        elif value_type == 'url':
            processed_value = datavalue['value']
            is_link = True
        
        # Si no pudimos procesar el valor, usar str()
        if not processed_value:
            processed_value = str(datavalue['value'])
        
        return processed_value, value_type, is_link

    def process_special_property(self, property_id: str, property_label: str, 
                                value: str, album_id: int, release_group_mbid: str) -> Optional[Tuple[str, str]]:
        """
        Procesar propiedades especiales como etiquetas discográficas o seguidores en redes sociales.
        
        Args:
            property_id: ID de la propiedad de Wikidata
            property_label: Etiqueta legible de la propiedad
            value: Valor de la propiedad
            album_id: ID del álbum en nuestra base de datos
            release_group_mbid: MBID del grupo de lanzamiento
            
        Returns:
            Optional[Tuple[str, str]]: (nombre_columna, valor) o None si no hay nueva columna
        """
        # Propiedades de sellos discográficos
        if property_id == 'P264' or property_label.lower() in ['record label', 'sello discográfico']:
            # Comprobar si el álbum ya tiene un sello asignado
            self.cursor.execute("SELECT label FROM albums WHERE id = ?", (album_id,))
            result = self.cursor.fetchone()
            current_label = result[0] if result else None
            
            if not current_label:
                # Actualizar el sello del álbum
                self.cursor.execute("UPDATE albums SET label = ? WHERE id = ?", (value, album_id))
                self.conn.commit()
                print(f"Updated album label to '{value}'")
                
                # Comprobar si el sello existe en la tabla de sellos
                self.cursor.execute("SELECT id FROM labels WHERE name = ?", (value,))
                label_result = self.cursor.fetchone()
                
                if not label_result:
                    # Crear una entrada básica para el sello
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.cursor.execute("""
                    INSERT INTO labels (name, last_updated)
                    VALUES (?, ?)
                    """, (value, now))
                    self.conn.commit()
                    print(f"Added new label '{value}' to labels table")
            
            return None  # No hay nueva columna, actualizamos una existente
        
        # Verificar si el valor parece ser una URL
        is_url = value.startswith(('http://', 'https://'))
        
        # Si ya es una URL, usarla directamente
        if is_url:
            # Determinar el nombre de la columna basado en el dominio
            import re
            from urllib.parse import urlparse
            
            parsed_url = urlparse(value)
            domain = parsed_url.netloc
            
            # Extraer el nombre del servicio del dominio (por ejemplo, "discogs.com" -> "discogs")
            match = re.search(r'([a-zA-Z0-9-]+)\.[a-zA-Z]+$', domain)
            if match:
                service_name = match.group(1).lower()
                column_name = f"{service_name}_url"
                
                # Verificar si la columna ya está aprobada o rechazada
                if column_name in self.approved_columns:
                    self.update_release_group_column(release_group_mbid, column_name, value)
                    return None
                elif column_name in self.rejected_columns:
                    return None
                else:
                    return (column_name, value)
        
        # Propiedades de redes sociales y servicios musicales con mapeo predefinido
        known_platforms = {
            # Redes sociales
            'P2002': ('twitter_url', lambda v: f"https://twitter.com/{v}" if not v.startswith('http') else v),
            'P2003': ('instagram_url', lambda v: f"https://instagram.com/{v}" if not v.startswith('http') else v),
            'P2013': ('facebook_url', lambda v: f"https://facebook.com/{v}" if not v.startswith('http') else v),
            'P2397': ('youtube_url', lambda v: f"https://youtube.com/channel/{v}" if not v.startswith('http') else v),
            'P4033': ('soundcloud_url', lambda v: v),
            'P5166': ('tiktok_url', lambda v: f"https://tiktok.com/@{v}" if not v.startswith('http') else v),
            
            # Servicios musicales
            'P1004': ('musicbrainz_url', lambda v: f"https://musicbrainz.org/release-group/{v}" if not v.startswith('http') else v),
            'P1651': ('youtube_video_url', lambda v: f"https://youtube.com/watch?v={v}" if not v.startswith('http') else v),
            'P1729': ('allmusic_url', lambda v: f"https://www.allmusic.com/album/{v}" if not v.startswith('http') else v),
            'P1902': ('spotify_url', lambda v: f"https://open.spotify.com/album/{v}" if not v.startswith('http') else v),
            'P2205': ('soundcloud_url', lambda v: v),
            'P2207': ('apple_music_url', lambda v: f"https://music.apple.com/album/{v}" if not v.startswith('http') else v),
            'P2850': ('metacritic_url', lambda v: f"https://www.metacritic.com/music/{v}/" if not v.startswith('http') else v),
            'P5404': ('bandcamp_url', lambda v: v),
            'P8661': ('deezer_url', lambda v: f"https://www.deezer.com/album/{v}" if not v.startswith('http') else v),
            
            # Códigos y bases de datos de la industria
            'P3295': ('discogs_master_url', lambda v: f"https://www.discogs.com/master/{v}" if not v.startswith('http') else v),
            'P1954': ('discogs_release_url', lambda v: f"https://www.discogs.com/release/{v}" if not v.startswith('http') else v),
            'P3861': ('bpm_url', lambda v: f"https://www.bpm.so/album/{v}" if not v.startswith('http') else v),
            'P5150': ('rym_url', lambda v: f"https://rateyourmusic.com/release/{v}" if not v.startswith('http') else v),
            'P6367': ('genius_url', lambda v: f"https://genius.com/albums/{v}" if not v.startswith('http') else v),
            'P966': ('musicmoz_url', lambda v: f"https://musicmoz.org/release/{v}" if not v.startswith('http') else v),
            'P745': ('recording_industry_url', lambda v: f"https://www.riaa.com/gold-platinum/?{v}" if not v.startswith('http') else v),
            'P3709': ('britsh_phonographic_url', lambda v: f"https://www.bpi.co.uk/award/{v}" if not v.startswith('http') else v),
            'P4947': ('music_map_url', lambda v: f"https://musicmap.info/album/{v}" if not v.startswith('http') else v),
        }
        
        # Si es una plataforma conocida
        if property_id in known_platforms:
            column_name, value_transformer = known_platforms[property_id]
            
            # Verificar si la columna ya está aprobada o rechazada
            if column_name in self.approved_columns:
                transformed_value = value_transformer(value)
                
                # Actualizar directamente en la base de datos
                self.update_release_group_column(release_group_mbid, column_name, transformed_value)
                return None  # No necesitamos preguntar, ya está aprobada
                
            elif column_name in self.rejected_columns:
                return None  # Columna rechazada anteriormente
                
            else:
                transformed_value = value_transformer(value)
                return (column_name, transformed_value)  # Devolver para aprobación manual
        
        # Para propiedades desconocidas, crear un nombre de columna a partir de la etiqueta
        if property_label and property_label != property_id:
            column_name = self.safe_column_name(property_label)
            
            # Verificar si ya está aprobada o rechazada
            if column_name in self.approved_columns:
                self.update_release_group_column(release_group_mbid, column_name, value)
                return None
            elif column_name in self.rejected_columns:
                return None
            else:
                return (column_name, value)
                
        return None

        
    def update_release_group_column(self, release_group_mbid: str, column_name: str, value: str) -> None:
        """Actualizar una columna en la tabla mb_release_group."""
        try:
            query = f"UPDATE mb_release_group SET {column_name} = ? WHERE mbid = ?"
            self.cursor.execute(query, (value, release_group_mbid))
            self.conn.commit()
        except sqlite3.OperationalError as e:
            # Si falla porque la columna no existe, intentar crearla
            if "no such column" in str(e):
                self.add_column_if_not_exists('mb_release_group', column_name, 'TEXT')
                query = f"UPDATE mb_release_group SET {column_name} = ? WHERE mbid = ?"
                self.cursor.execute(query, (value, release_group_mbid))
                self.conn.commit()
            else:
                raise

    def fetch_wikidata_entities(self, wikidata_id: str) -> Optional[Dict]:
        """Fetch entity data from Wikidata with property labels and claim URLs."""
        if not wikidata_id:
            return None
            
        # Primera solicitud para obtener los claims y labels
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbgetentities",
            "ids": wikidata_id,
            "format": "json",
            "languages": "en|es",  # Preferencia por español e inglés
            "props": "claims|labels|sitelinks"
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            time.sleep(1)  # Be nice to Wikidata API
            
            if response.status_code != 200:
                print(f"Error fetching Wikidata entity {wikidata_id}: {response.status_code}")
                return None
                
            entity_data = response.json()
            
            # Obtener IDs de todas las propiedades para consultar sus etiquetas
            property_ids = set()
            entity_ids = set()  # Para obtener información sobre entidades relacionadas
            
            if ('entities' in entity_data and wikidata_id in entity_data['entities'] and
                'claims' in entity_data['entities'][wikidata_id]):
                
                claims = entity_data['entities'][wikidata_id]['claims']
                property_ids = set(claims.keys())
                
                # Recolectar IDs de entidades relacionadas
                for prop_id, claim_list in claims.items():
                    for claim in claim_list:
                        if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                            datavalue = claim['mainsnak']['datavalue']
                            if datavalue.get('type') == 'wikibase-entityid':
                                entity_id = datavalue['value'].get('id')
                                if entity_id:
                                    entity_ids.add(entity_id)
            
            # Si no hay propiedades, no necesitamos hacer más consultas
            if not property_ids:
                return entity_data
            
            # Segunda solicitud para obtener etiquetas de propiedades
            property_data = {}
            # Procesamos las propiedades en lotes de 50 para no sobrecargar la API
            property_chunks = [list(property_ids)[i:i + 50] for i in range(0, len(property_ids), 50)]
            
            for chunk in property_chunks:
                prop_params = {
                    "action": "wbgetentities",
                    "ids": "|".join(chunk),
                    "format": "json",
                    "languages": "en|es",
                    "props": "labels"
                }
                
                try:
                    prop_response = requests.get(url, params=prop_params, timeout=30)
                    time.sleep(1)  # Be nice to Wikidata API
                    
                    if prop_response.status_code == 200:
                        prop_data = prop_response.json()
                        if 'entities' in prop_data:
                            property_data.update(prop_data['entities'])
                except Exception as e:
                    print(f"Error fetching property labels: {str(e)}")
            
            # Tercera solicitud: obtener información sobre entidades relacionadas
            entity_data_related = {}
            if entity_ids:
                entity_chunks = [list(entity_ids)[i:i + 50] for i in range(0, len(entity_ids), 50)]
                
                for chunk in entity_chunks:
                    entity_params = {
                        "action": "wbgetentities",
                        "ids": "|".join(chunk),
                        "format": "json",
                        "languages": "en|es",
                        "props": "labels|claims|sitelinks"
                    }
                    
                    try:
                        entity_response = requests.get(url, params=entity_params, timeout=30)
                        time.sleep(1)  # Be nice to Wikidata API
                        
                        if entity_response.status_code == 200:
                            entity_resp_data = entity_response.json()
                            if 'entities' in entity_resp_data:
                                entity_data_related.update(entity_resp_data['entities'])
                    except Exception as e:
                        print(f"Error fetching related entities: {str(e)}")
            
            # Cuarta solicitud: consultar los formatter URLs para las propiedades
            # Esto ayuda a obtener las URLs completas para los identificadores
            formatter_urls = {}
            try:
                # SPARQL query para obtener los formatter URLs
                sparql_query = """
                SELECT ?property ?formatterURL WHERE {
                ?property wdt:P1630 ?formatterURL.
                VALUES ?property { %s }
                }
                """ % " ".join(f"wd:{pid}" for pid in property_ids)
                
                sparql_url = "https://query.wikidata.org/sparql"
                sparql_params = {
                    "query": sparql_query,
                    "format": "json"
                }
                
                sparql_headers = {
                    "Accept": "application/json",
                    "User-Agent": "MusicLibraryWikidataFetcher/1.0"
                }
                
                sparql_response = requests.get(
                    sparql_url, 
                    params=sparql_params, 
                    headers=sparql_headers,
                    timeout=30
                )
                time.sleep(1)  # Be nice to Wikidata API
                
                if sparql_response.status_code == 200:
                    sparql_data = sparql_response.json()
                    if 'results' in sparql_data and 'bindings' in sparql_data['results']:
                        for binding in sparql_data['results']['bindings']:
                            if 'property' in binding and 'formatterURL' in binding:
                                prop_uri = binding['property']['value']
                                prop_id = prop_uri.split('/')[-1]
                                formatter_url = binding['formatterURL']['value']
                                formatter_urls[prop_id] = formatter_url
            except Exception as e:
                print(f"Error fetching formatter URLs: {str(e)}")
            
            # Anexar los datos adicionales al resultado
            entity_data['property_labels'] = property_data
            entity_data['related_entities'] = entity_data_related
            entity_data['formatter_urls'] = formatter_urls
            
            return entity_data
            
        except Exception as e:
            print(f"Error fetching Wikidata entity {wikidata_id}: {str(e)}")
            return None


    def process_wikidata_entity(self, wikidata_id: str, release_group_mbid: str, 
                                album_id: int, artist_id: int) -> List[Dict]:
        """Process a Wikidata entity and extract properties with improved data quality."""
        entity_data = self.fetch_wikidata_entities(wikidata_id)
        if not entity_data or 'entities' not in entity_data or wikidata_id not in entity_data['entities']:
            return []
        
        entity = entity_data['entities'][wikidata_id]
        wikidata_entries = []
        
        # Consultar posibles nuevas columnas en modo manual
        new_columns = []
        
        # Extraer enlaces a sitios externos (Wikipedia, etc.)
        if 'sitelinks' in entity:
            for site_key, site_data in entity['sitelinks'].items():
                # Priorizar Wikipedia en español, luego en inglés
                if site_key == 'eswiki':
                    title = site_data['title']
                    wiki_url = f"https://es.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    
                    # En modo manual, comprobar si wikipedia_url está aprobada
                    if self.mode == 'manual' and 'wikipedia_url' not in self.approved_columns and 'wikipedia_url' not in self.rejected_columns:
                        new_columns.append(('wikipedia_url', wiki_url))
                    elif 'wikipedia_url' in self.approved_columns:
                        # Actualizar directamente
                        self.update_release_group_column(release_group_mbid, 'wikipedia_url', wiki_url)
                    break
                elif site_key == 'enwiki':
                    title = site_data['title']
                    wiki_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    
                    # Solo si no encontramos una versión en español
                    if self.mode == 'manual' and 'wikipedia_url' not in self.approved_columns and 'wikipedia_url' not in self.rejected_columns:
                        new_columns.append(('wikipedia_url', wiki_url))
                    elif 'wikipedia_url' in self.approved_columns:
                        # Consultar si ya hay una URL en español
                        self.cursor.execute("""
                        SELECT wikipedia_url FROM mb_release_group WHERE mbid = ?
                        """, (release_group_mbid,))
                        result = self.cursor.fetchone()
                        if not result or not result[0]:
                            self.update_release_group_column(release_group_mbid, 'wikipedia_url', wiki_url)
        
        if 'claims' in entity:
            # Obtener las etiquetas de propiedades si están disponibles
            property_labels = entity_data.get('property_labels', {})
            
            for property_id, claims in entity['claims'].items():
                # Obtener etiqueta legible para la propiedad
                property_label = self.get_property_label(property_id, property_labels)
                
                # Omitir propiedades que no nos interesan
                if self.should_skip_property(property_id, property_label):
                    continue
                
                for claim in claims:
                    processed_value, value_type, is_link = self.get_value_or_link(claim, entity_data)
                    
                    # En modo manual, recopilar posibles nuevas columnas
                    column_info = self.process_special_property(
                        property_id, property_label, processed_value, 
                        album_id, release_group_mbid
                    )
                    
                    if column_info and self.mode == 'manual':
                        new_columns.append(column_info)
                    
                    # Crear entrada para la tabla mb_wikidata (sin importar el modo)
                    entry = {
                        'wikidata_id': wikidata_id,
                        'release_group_mbid': release_group_mbid,
                        'album_id': album_id,
                        'artist_id': artist_id,
                        'label_id': None,  # Would need additional lookup
                        'property_id': property_id,
                        'property_label': property_label,
                        'property_value': processed_value,
                        'value_type': value_type,
                        'is_link': 1 if is_link else 0,
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    wikidata_entries.append(entry)
        
        # En modo manual, preguntar por todas las nuevas columnas juntas
        if new_columns and self.mode == 'manual':
            self.ask_for_column_approval(new_columns, release_group_mbid)
        
        return wikidata_entries
    
    def ask_for_column_approval(self, new_columns: List[Tuple[str, str]], release_group_mbid: str) -> None:
        """Preguntar al usuario si aprobar nuevas columnas en modo manual."""
        if not new_columns:
            return
            
        print("\n===== NUEVAS COLUMNAS DETECTADAS =====")
        print(f"Para el release group: {release_group_mbid}")
        
        # Mostrar todas las columnas numeradas
        for i, (column_name, value) in enumerate(new_columns, 1):
            print(f"{i}. {column_name}: {value[:100]}{' (truncado)' if len(value) > 100 else ''}")
        
        # Preguntar al usuario
        print("\nOpciones:")
        print("- Números separados por comas (ej: '1,3,5')")
        print("- Para renombrar una columna: '3:nuevo_nombre'")
        print("- 'a' para aprobar todas")
        print("- 'n' para rechazar todas")
        
        response = input("\n¿Qué columnas aprobar?: ")
        
        approved_columns = []
        
        if response.lower() == 'a':
            # Aprobar todas
            approved_columns = [(i, None) for i in range(1, len(new_columns) + 1)]
        elif response.lower() != 'n':
            # Procesar selección del usuario
            try:
                parts = response.split(',')
                for part in parts:
                    part = part.strip()
                    if '-' in part:
                        # Rango (ej: 1-5)
                        start, end = part.split('-')
                        approved_columns.extend([(i, None) for i in range(int(start), int(end) + 1)])
                    elif ':' in part:
                        # Renombrar (ej: 3:nueva_columna)
                        idx, new_name = part.split(':', 1)
                        approved_columns.append((int(idx), new_name.strip()))
                    elif part.isdigit():
                        # Número individual
                        approved_columns.append((int(part), None))
            except Exception as e:
                print(f"Error al procesar la selección: {str(e)}")
                approved_columns = []
        
        # Procesar aprobaciones y rechazos
        for i, (column_name, value) in enumerate(new_columns, 1):
            # Buscar si este índice está aprobado
            approved_entry = next(((idx, new_name) for idx, new_name in approved_columns if idx == i), None)
            
            if approved_entry:
                idx, new_name = approved_entry
                
                # Si hay un nuevo nombre, preguntarlo o usarlo
                final_column_name = column_name
                if new_name:
                    final_column_name = new_name
                else:
                    # Verificar si parece un ID en lugar de una URL
                    if (('_id' in column_name.lower() or 'id_' in column_name.lower()) and
                        not value.startswith('http') and not 'url' in column_name.lower()):
                        print(f"\nLa columna '{column_name}' parece ser un identificador.")
                        print(f"Valor actual: {value}")
                        
                        # Preguntar si prefiere una URL
                        url_choice = input(f"¿Convertir a URL o cambiar nombre? (u=URL, r=renombrar, Enter=mantener): ")
                        
                        if url_choice.lower() == 'u':
                            # Intentar generar una URL
                            domain = input("Ingrese el dominio base (ej: discogs.com): ")
                            if domain:
                                # Construir URL y actualizar valor
                                if not domain.startswith('http'):
                                    domain = 'https://' + domain
                                if not domain.endswith('/'):
                                    domain += '/'
                                
                                # Preguntar por el path
                                path = input("Ingrese el path (ej: 'master/' para Discogs): ")
                                
                                # Construir la URL completa
                                url_value = f"{domain}{path}{value}"
                                print(f"URL generada: {url_value}")
                                value = url_value
                                
                                # Cambiar el nombre de la columna para reflejar que es una URL
                                source_name = domain.split('//')[1].split('.')[0]
                                final_column_name = f"{source_name}_url"
                        elif url_choice.lower() == 'r':
                            # Renombrar la columna
                            new_column_name = input(f"Nuevo nombre para la columna '{column_name}': ")
                            if new_column_name:
                                final_column_name = new_column_name
                
                # Sanitizar el nombre de la columna
                final_column_name = self.safe_column_name(final_column_name)
                
                print(f"Aprobada: {column_name} → {final_column_name}")
                self.approved_columns.add(final_column_name)
                self.add_column_if_not_exists('mb_release_group', final_column_name, 'TEXT')
                self.update_release_group_column(release_group_mbid, final_column_name, value)
                self.stats["new_columns_added"] += 1
            else:
                print(f"Rechazada: {column_name}")
                self.rejected_columns.add(column_name)
                self.stats["columns_rejected"] += 1
        
        # Guardar en caché las decisiones
        self.save_cache()



    def save_release_group(self, group_data: Dict) -> int:
        """Save release group data to the database."""
        try:
            # Check if we already have this release group
            self.cursor.execute('''
            SELECT id FROM mb_release_group WHERE mbid = ?
            ''', (group_data['mbid'],))
            
            existing = self.cursor.fetchone()
            
            if existing:
                # Update existing record
                placeholders = ", ".join([f"{k} = ?" for k in group_data.keys()])
                values = list(group_data.values())
                values.append(group_data['mbid'])
                
                query = f"UPDATE mb_release_group SET {placeholders} WHERE mbid = ?"
                self.cursor.execute(query, values)
                self.conn.commit()
                return existing['id']
            else:
                # Insert new record
                columns = ", ".join(group_data.keys())
                placeholders = ", ".join(["?" for _ in group_data.keys()])
                values = list(group_data.values())
                
                query = f"INSERT INTO mb_release_group ({columns}) VALUES ({placeholders})"
                self.cursor.execute(query, values)
                self.conn.commit()
                self.stats["release_groups_added"] += 1
                return self.cursor.lastrowid
                
        except Exception as e:
            print(f"Error saving release group: {str(e)}")
            traceback.print_exc()
            return 0
    

    def save_wikidata_entries(self, entries: List[Dict]) -> int:
        """Save wikidata entries to the database."""
        saved_count = 0
        
        for entry in entries:
            try:
                # Check if the table has all necessary columns
                expected_columns = set(entry.keys())
                actual_columns = set()
                
                # Get the actual columns from the table
                self.cursor.execute("PRAGMA table_info(mb_wikidata)")
                for col in self.cursor.fetchall():
                    actual_columns.add(col[1])  # column name is at index 1
                
                # Find which columns are missing and remove them from entry
                missing_columns = expected_columns - actual_columns
                entry_filtered = {k: v for k, v in entry.items() if k not in missing_columns}
                
                # Generate dynamic SQL
                columns = ", ".join(entry_filtered.keys())
                placeholders = ", ".join(["?" for _ in entry_filtered.keys()])
                values = list(entry_filtered.values())
                
                query = f"INSERT INTO mb_wikidata ({columns}) VALUES ({placeholders})"
                self.cursor.execute(query, values)
                saved_count += 1
                
                # Si hay warnings de columnas faltantes, mostrarlos solo la primera vez
                if missing_columns and saved_count == 1:
                    print(f"Warning: Columns {', '.join(missing_columns)} not found in mb_wikidata table. Data for these columns will be ignored.")
            except Exception as e:
                print(f"Error saving wikidata entry: {str(e)}")
                continue
                    
        self.conn.commit()
        self.stats["wikidata_entries_added"] += saved_count
        return saved_count
        
    def process_release(self, release: Dict) -> None:
        """Process a single release to fetch and save its release group data."""
        print(f"Processing release: {release['album_name']} by {release['artist_name']}")
        
        # Actualizar el último ID procesado
        self.last_processed_id = release['album_id']
        
        # Check if we already have this release group
        self.cursor.execute('''
        SELECT id FROM mb_release_group WHERE album_id = ?
        ''', (release['album_id'],))
        
        if self.cursor.fetchone() and not self.config.get('force_update', False):
            print(f"Release group already exists for {release['album_name']}. Skipping.")
            self.stats["skipped"] += 1
            return
            
        # Fetch release data from MusicBrainz
        release_data = self.fetch_release_group(release['release_mbid'])
        if not release_data:
            print(f"Could not fetch data for release {release['release_mbid']}")
            return
            
        # Extract release group data
        group_data = self.extract_release_group_data(
            release_data, 
            release['album_id'], 
            release['artist_id']
        )
        
        if not group_data:
            print(f"Could not extract release group data for {release['album_name']}")
            return
            
        # Save release group data
        group_id = self.save_release_group(group_data)
        
        # Process Wikidata if available
        if group_data.get('wikidata_id'):
            wikidata_entries = self.process_wikidata_entity(
                group_data['wikidata_id'],
                group_data['mbid'],
                release['album_id'],
                release['artist_id']
            )
            
            if wikidata_entries:
                saved_count = self.save_wikidata_entries(wikidata_entries)
                print(f"Saved {saved_count} Wikidata entries for {release['album_name']}")
            else:
                print(f"No Wikidata entries found for {release['album_name']}")
                
        self.stats["processed_releases"] += 1
        
        # Guardar caché después de cada lanzamiento para poder continuar
        self.save_cache()
        
    def process_all_releases(self, limit: int = None) -> None:
        """Process all releases with MBIDs in the database."""
        releases = self.get_releases_with_mbid()
        total = len(releases)
        
        print(f"Found {total} releases with MusicBrainz IDs")
        print(f"Starting from release ID: {self.last_processed_id}")
        
        if limit and limit < total:
            releases = releases[:limit]
            print(f"Limiting to {limit} releases")
            
        for i, release in enumerate(releases):
            print(f"\nProcessing {i+1}/{len(releases)}: {release['album_name']} by {release['artist_name']}")
            try:
                self.process_release(release)
            except Exception as e:
                print(f"Error processing release {release['album_name']}: {str(e)}")
                traceback.print_exc()
                # Guardar caché incluso si hay error
                self.save_cache()
                    
            # Print progress every 10 releases
            if (i + 1) % 10 == 0:
                self.print_stats()
                    
        self.print_stats()
        
     
    def print_stats(self) -> None:
        """Print current processing statistics."""
        print("\n--- Processing Statistics ---")
        print(f"Total releases: {self.stats['total_releases']}")
        print(f"Processed: {self.stats['processed_releases']}")
        print(f"Release groups added: {self.stats['release_groups_added']}")
        print(f"Wikidata entries added: {self.stats['wikidata_entries_added']}")
        print(f"Failed fetches: {self.stats['failed_fetch']}")
        print(f"Skipped (already exists): {self.stats['skipped']}")
        
        # Estadísticas de columnas en modo manual
        if self.mode == 'manual':
            print(f"New columns added: {self.stats['new_columns_added']}")
            print(f"Columns rejected: {self.stats['columns_rejected']}")
        
        print("----------------------------\n")
        
    def close(self) -> None:
        """Close database connection and save cache."""
        self.save_cache()
        if self.conn:
            self.conn.close()
            
def main(config=None):
    """Main function that can be called directly or from another script."""
    if config is None:
        parser = argparse.ArgumentParser(description='Fetch release group data from MusicBrainz')
        parser.add_argument('--config', help='Path to configuration file')
        parser.add_argument('--db-path', help='Path to SQLite database')
        parser.add_argument('--limit', type=int, help='Limit the number of releases to process')
        parser.add_argument('--force-update', action='store_true', help='Force update existing entries')
        parser.add_argument('--mode', choices=['auto', 'manual'], default='auto', 
                          help='Mode of operation: auto or manual (for new columns)')
        parser.add_argument('--cache-file', help='Path to cache file to resume processing')
        parser.add_argument('--skip-properties', nargs='+', help='List of Wikidata property IDs to skip')
        
        args = parser.parse_args()
        
        # Load configuration file if provided
        if args.config:
            with open(args.config, 'r') as f:
                config_data = json.load(f)
                
            # Combine configurations
            config = {}
            config.update(config_data.get("common", {}))
            config.update(config_data.get("mb_release_groups", {}))
            
            # Command line arguments override config file
            if args.db_path:
                config['db_path'] = args.db_path
            if args.limit:
                config['limit'] = args.limit
            if args.force_update:
                config['force_update'] = args.force_update
            if args.mode:
                config['mode'] = args.mode
            if args.cache_file:
                config['cache_file'] = args.cache_file
            if args.skip_properties:
                config['skip_properties'] = args.skip_properties
        else:
            config = {
                'db_path': args.db_path,
                'limit': args.limit,
                'force_update': args.force_update,
                'mode': args.mode,
                'cache_file': args.cache_file,
                'skip_properties': args.skip_properties
            }
    
    # Validate required parameters
    if not config.get('db_path'):
        print("Error: Database path must be specified")
        return 1
        
    if not os.path.exists(config['db_path']):
        print(f"Error: Database file {config['db_path']} does not exist")
        return 1
    
    # Ensure config has mode and cache_file
    config.setdefault('mode', 'auto')
    if 'cache_file' not in config:
        # Generate a default cache file name based on the database name
        db_name = os.path.basename(config['db_path'])
        cache_dir = os.path.dirname(config['db_path']) or '.'
        config['cache_file'] = os.path.join(cache_dir, f"{os.path.splitext(db_name)[0]}_mb_release_groups_cache.json")
    
    print(f"Mode: {config['mode']}")
    print(f"Cache file: {config['cache_file']}")
        
    # Initialize and run the processor
    try:
        processor = MusicBrainzReleaseGroups(config['db_path'], config)
        
        # Pregunta si quiere continuar desde el caché o empezar de nuevo
        if processor.last_processed_id > 0:
            print(f"Found cache with last processed album ID: {processor.last_processed_id}")
            response = input("Continue from last position? [Y/n]: ")
            if response.lower() == 'n':
                print("Starting from the beginning...")
                processor.last_processed_id = 0
                processor.stats = {
                    "total_releases": 0,
                    "processed_releases": 0,
                    "release_groups_added": 0,
                    "wikidata_entries_added": 0,
                    "failed_fetch": 0,
                    "skipped": 0,
                    "new_columns_added": 0,
                    "columns_rejected": 0
                }
                processor.save_cache()
        
        # Run the process
        processor.process_all_releases(config.get('limit'))
    except KeyboardInterrupt:
        print("\nProcess interrupted by user!")
        if 'processor' in locals():
            processor.save_cache()  # Save cache on keyboard interrupt
            print(f"Cache saved to {config['cache_file']}")
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        traceback.print_exc()
        if 'processor' in locals():
            processor.save_cache()  # Save cache on error
        return 1
    finally:
        if 'processor' in locals():
            processor.close()
            
    return 0

if __name__ == "__main__":
    exit(main())
