import os
import sys
import sqlite3
import json
import requests
import time
from datetime import datetime
from base_module import PROJECT_ROOT

class DiscogsArtistInfoUpdater:
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.db_path = self.config.get('db_path', os.path.join(PROJECT_ROOT, 'music.db'))
        self.force_update = self.config.get('force_update', False)
        self.sleep_time = self.config.get('sleep_time', 1)  # Para respetar rate limits de Discogs
        self.token = self.config.get('discogs_token', '')
        
        # Asegurar que la tabla existe
        self.create_table_if_not_exists()

    def create_table_if_not_exists(self):
        """Crea la tabla artists_discogs_info si no existe"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS artists_discogs_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                artist_name TEXT,
                realname TEXT,
                profile TEXT,
                namevariations TEXT,
                aliases TEXT,
                groups TEXT,
                url TEXT,
                discogs_id INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(artist_id)
            )
            ''')
            conn.commit()

    def get_artists_to_update(self):
        """Obtiene los artistas que necesitan actualización en la tabla artists_discogs_info"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if self.force_update:
                # Si force_update es True, obtén todos los artistas con URL de Discogs
                # de ambas fuentes (artists_networks y artists.discogs_url)
                query = '''
                SELECT a.id, a.name, COALESCE(an.discogs, a.discogs_url) as discogs_source
                FROM artists a
                LEFT JOIN artists_networks an ON a.id = an.artist_id
                WHERE an.discogs IS NOT NULL OR a.discogs_url IS NOT NULL
                '''
            else:
                # Si force_update es False, obtén solo los artistas sin entrada en artists_discogs_info
                query = '''
                SELECT a.id, a.name, COALESCE(an.discogs, a.discogs_url) as discogs_source
                FROM artists a
                LEFT JOIN artists_networks an ON a.id = an.artist_id
                LEFT JOIN artists_discogs_info adi ON a.id = adi.artist_id
                WHERE (an.discogs IS NOT NULL OR a.discogs_url IS NOT NULL)
                AND adi.artist_id IS NULL
                '''
            
            cursor.execute(query)
            return cursor.fetchall()

    def fetch_discogs_data(self, discogs_url):
        """Obtiene los datos de un artista desde la API de Discogs"""
        # Convertir URL de web de Discogs a URL de API
        if '/artist/' in discogs_url:
            artist_id = discogs_url.split('/')[-1]
            api_url = f"https://api.discogs.com/artists/{artist_id}"
        else:
            api_url = discogs_url
        
        # Añadir token para autenticación si está configurado
        headers = {'User-Agent': 'MusicDBUpdater/1.0'}  # User-Agent requerido por Discogs
        if self.token:
            headers['Authorization'] = f'Discogs token={self.token}'
        
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error al obtener datos de Discogs: {e}")
            return None

    def process_array_field(self, field_data):
        """Procesa campos de tipo array para almacenarlos como JSON"""
        if not field_data:
            return None
        return json.dumps(field_data, ensure_ascii=False)

    def update_artist_discogs_info(self, artist_id, artist_name, discogs_data):
        """Actualiza la información de Discogs para un artista"""
        if not discogs_data:
            return False
        
        # Extraer los campos relevantes
        realname = discogs_data.get('realname', '')
        profile = discogs_data.get('profile', '')
        namevariations = self.process_array_field(discogs_data.get('namevariations', []))
        
        # Procesamiento de aliases (contiene objetos con más información)
        aliases_data = discogs_data.get('aliases', [])
        aliases = self.process_array_field([alias.get('name', '') for alias in aliases_data] if aliases_data else [])
        
        # Procesamiento de groups (contiene objetos con más información)
        groups_data = discogs_data.get('groups', [])
        groups = self.process_array_field([group.get('name', '') for group in groups_data] if groups_data else [])
        
        # URL completa de Discogs
        url = discogs_data.get('uri', '')
        
        # ID de Discogs (extraído de la URL)
        discogs_id = None
        if url:
            try:
                discogs_id = int(url.split('/')[-1])
            except (ValueError, IndexError):
                pass
        
        # Guardar en la base de datos
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Usar INSERT OR REPLACE para manejar actualizaciones y nuevas inserciones
            cursor.execute('''
            INSERT OR REPLACE INTO artists_discogs_info 
            (artist_id, artist_name, realname, profile, namevariations, aliases, groups, url, discogs_id, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                artist_id, 
                artist_name, 
                realname, 
                profile, 
                namevariations,
                aliases,
                groups,
                url,
                discogs_id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            conn.commit()
            
            print(f"Actualizada información de Discogs para: {artist_name}")
            return True

    def run(self):
        """Ejecuta el proceso de actualización de información de Discogs"""
        artists_to_update = self.get_artists_to_update()
        print(f"Encontrados {len(artists_to_update)} artistas para actualizar")
        
        updated_count = 0
        error_count = 0
        
        for artist_id, artist_name, discogs_url in artists_to_update:
            print(f"Procesando: {artist_name} ({discogs_url})")
            
            if not discogs_url:
                print(f"URL de Discogs vacía para {artist_name}, saltando...")
                continue
            
            # Obtener datos de la API de Discogs
            discogs_data = self.fetch_discogs_data(discogs_url)
            
            if discogs_data:
                if self.update_artist_discogs_info(artist_id, artist_name, discogs_data):
                    updated_count += 1
            else:
                error_count += 1
            
            # Esperar para respetar el rate limiting de Discogs
            time.sleep(self.sleep_time)
        
        print(f"Proceso completado. Actualizados: {updated_count}, Errores: {error_count}")

def main(config=None):
    updater = DiscogsArtistInfoUpdater(config)
    updater.run()

if __name__ == "__main__":
    # Si se ejecuta como script principal
    main()