import sqlite3
import os
import requests
import time
import json
import re
from base_module import PROJECT_ROOT

class DiscogsDiscographyModule:
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.db_path = config.get('db_path', os.path.join(PROJECT_ROOT, "db", "sqlite", "music.db"))
        self.discogs_token = config.get('discogs_token', '')
        self.force_update = config.get('force_update', False)
        self.accepted_formats = config.get('accepted_formats', ['album', 'ep'])
        self.rol_principal = config.get('rol_principal', False)
    def create_discogs_discography_table(self):
        """
        Crea la tabla discogs_discography en la base de datos si no existe.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS discogs_discography (
            id INTEGER PRIMARY KEY,
            artist_id INTEGER NOT NULL,
            album_id INTEGER,
            album_name TEXT NOT NULL,
            type TEXT,
            main_release INTEGER,
            role TEXT,
            resource_url TEXT,
            year INTEGER,
            thumb TEXT,
            stats_comm_wantlist INTEGER,
            stats_comm_coll INTEGER,
            user_wantlist INTEGER DEFAULT 0,
            user_coll INTEGER DEFAULT 0,
            format TEXT,
            label TEXT,
            status TEXT,
            discogs_id INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (album_id) REFERENCES albums(id)
        )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_disco_artist_id ON discogs_discography(artist_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_disco_album_id ON discogs_discography(album_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_disco_discogs_id ON discogs_discography(discogs_id)')
        
        conn.commit()
        conn.close()
        
        print("Tabla discogs_discography creada correctamente")

    def extract_discogs_id_from_url(self, url):
        """
        Extrae el ID de Discogs desde una URL de Discogs
        
        Args:
            url (str): URL de Discogs (API o web)
            
        Returns:
            int: ID de Discogs, o None si no se encuentra
        """
        if not url:
            return None
            
        # Para URL de API: https://api.discogs.com/artists/123
        api_pattern = r'api\.discogs\.com/artists/(\d+)'
        match = re.search(api_pattern, url)
        if match:
            return int(match.group(1))
            
        # Para URL web: https://www.discogs.com/artist/123-ArtistName
        # o https://www.discogs.com/es/artist/123-ArtistName
        web_pattern = r'discogs\.com/(?:[a-z]{2}/)?artist/(\d+)'
        match = re.search(web_pattern, url)
        if match:
            return int(match.group(1))
            
        return None

    def get_artists_with_discogs(self):
        """
        Obtiene todos los artistas que tienen un enlace de Discogs
        en la tabla artists_networks o en la tabla artists
        
        Si force_update es False, solo devuelve artistas que no tienen
        entradas en la tabla discogs_discography
        
        Returns:
            list: Lista de tuplas (artist_id, discogs_id)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Primero buscar en artists_networks
        cursor.execute('''
        SELECT an.artist_id, an.discogs, an.discogs_http
        FROM artists_networks an
        WHERE an.discogs IS NOT NULL OR an.discogs_http IS NOT NULL
        ''')
        
        results_networks = cursor.fetchall()
        
        # Luego buscar en artists para los que no tienen enlaces en networks
        cursor.execute('''
        SELECT a.id, a.discogs_url
        FROM artists a
        LEFT JOIN artists_networks an ON a.id = an.artist_id
        WHERE a.discogs_url IS NOT NULL 
        AND an.artist_id IS NULL
        ''')
        
        results_artists = cursor.fetchall()
        
        # Si force_update es falso, obtener la lista de artistas que ya tienen entradas
        artists_with_entries = set()
        if not self.force_update:
            cursor.execute('''
            SELECT DISTINCT artist_id FROM discogs_discography
            ''')
            for row in cursor.fetchall():
                artists_with_entries.add(row[0])
        
        artists_with_discogs = []
        
        # Procesar resultados de artists_networks
        for row in results_networks:
            artist_id = row[0]
            
            # Si no es force_update y el artista ya tiene entradas, omitirlo
            if not self.force_update and artist_id in artists_with_entries:
                continue
                
            discogs_api_url = row[1]
            discogs_web_url = row[2]
            
            # Intentar primero con la URL de la API
            discogs_id = self.extract_discogs_id_from_url(discogs_api_url)
            if not discogs_id:
                # Si no funciona, intentar con la URL web
                discogs_id = self.extract_discogs_id_from_url(discogs_web_url)
                
            if discogs_id:
                artists_with_discogs.append((artist_id, discogs_id))
        
        # Procesar resultados de artists (para los que no se encontraron en networks)
        for row in results_artists:
            artist_id = row[0]
            
            # Si no es force_update y el artista ya tiene entradas, omitirlo
            if not self.force_update and artist_id in artists_with_entries:
                continue
                
            discogs_url = row[1]
            
            discogs_id = self.extract_discogs_id_from_url(discogs_url)
            if discogs_id:
                artists_with_discogs.append((artist_id, discogs_id))
        
        conn.close()
        
        # Informar al usuario sobre el modo de operación
        if self.force_update:
            print(f"Modo FORCE UPDATE: Se procesarán todos los {len(artists_with_discogs)} artistas con enlaces a Discogs")
        else:
            print(f"Modo NORMAL: Se procesarán {len(artists_with_discogs)} artistas que no tienen entradas en discogs_discography")
        
        return artists_with_discogs

    def process_discogs_release(self, release_data, artist_id, cursor):
        """
        Procesa un lanzamiento de Discogs y lo inserta en la tabla discogs_discography
        
        Args:
            release_data (dict): Datos JSON del lanzamiento de Discogs
            artist_id (int): ID del artista en la tabla artists
            cursor: Cursor de la base de datos
        
        Returns:
            int: ID del registro insertado
        """
        # Extraer datos del lanzamiento
        discogs_id = release_data.get('id')
        album_name = release_data.get('title')
        release_type = release_data.get('type')
        main_release = release_data.get('main_release')
        role = release_data.get('role')
        resource_url = release_data.get('resource_url')
        year = release_data.get('year')
        thumb = release_data.get('thumb')
        
        # Extraer estadísticas si están disponibles
        stats_comm_wantlist = 0
        stats_comm_coll = 0
        user_wantlist = 0
        user_coll = 0
        
        if 'stats' in release_data:
            if 'community' in release_data['stats']:
                stats_comm_wantlist = release_data['stats']['community'].get('in_wantlist', 0)
                stats_comm_coll = release_data['stats']['community'].get('in_collection', 0)
            
            if 'user' in release_data['stats']:
                user_wantlist = release_data['stats']['user'].get('in_wantlist', 0)
                user_coll = release_data['stats']['user'].get('in_collection', 0)
        
        # Datos adicionales para type=release
        format_info = release_data.get('format')
        label_info = release_data.get('label')
        status_info = release_data.get('status')
        
        # Convertir listas a JSON para almacenamiento
        if isinstance(format_info, list):
            format_info = json.dumps(format_info)
        if isinstance(label_info, list):
            label_info = json.dumps(label_info)
        
        # Buscar si existe un álbum correspondiente en la tabla albums
        cursor.execute('''
        SELECT id FROM albums 
        WHERE artist_id = ? AND name = ?
        ''', (artist_id, album_name))
        
        album_id_result = cursor.fetchone()
        album_id = album_id_result[0] if album_id_result else None
        
        # Verificar si este lanzamiento ya existe en la tabla
        cursor.execute('''
        SELECT id FROM discogs_discography 
        WHERE discogs_id = ? AND artist_id = ?
        ''', (discogs_id, artist_id))
        
        existing_record = cursor.fetchone()
        
        if existing_record and not self.force_update:
            # Si ya existe y no se fuerza actualización, simplemente devolver el ID
            return existing_record[0]
        elif existing_record:
            # Actualizar registro existente
            cursor.execute('''
            UPDATE discogs_discography SET
                album_id = ?,
                album_name = ?,
                type = ?,
                main_release = ?,
                role = ?,
                resource_url = ?,
                year = ?,
                thumb = ?,
                stats_comm_wantlist = ?,
                stats_comm_coll = ?,
                user_wantlist = ?,
                user_coll = ?,
                format = ?,
                label = ?,
                status = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE discogs_id = ? AND artist_id = ?
            ''', (
                album_id, album_name, release_type, main_release, role, resource_url, year, thumb,
                stats_comm_wantlist, stats_comm_coll, user_wantlist, user_coll,
                format_info, label_info, status_info,
                discogs_id, artist_id
            ))
            return existing_record[0]
        else:
            # Insertar nuevo registro
            cursor.execute('''
            INSERT INTO discogs_discography (
                artist_id, album_id, album_name, type, main_release, role, resource_url, year, thumb,
                stats_comm_wantlist, stats_comm_coll, user_wantlist, user_coll,
                format, label, status, discogs_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                artist_id, album_id, album_name, release_type, main_release, role, resource_url, year, thumb,
                stats_comm_wantlist, stats_comm_coll, user_wantlist, user_coll,
                format_info, label_info, status_info,
                discogs_id
            ))
            return cursor.lastrowid

    def import_artist_discogs_releases(self, artist_id, discogs_id, conn=None, cursor=None):
        """
        Importa todos los lanzamientos de un artista desde Discogs
        
        Args:
            artist_id (int): ID del artista en la tabla artists
            discogs_id (int): ID del artista en Discogs
            conn: Conexión a la base de datos (opcional)
            cursor: Cursor de la base de datos (opcional)
        
        Returns:
            int: Número de lanzamientos procesados
        """
        should_close_conn = False
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            should_close_conn = True
        
        if cursor is None:
            cursor = conn.cursor()
        
        if not self.discogs_token:
            print(f"ERROR: No se proporcionó token de Discogs para el artista ID {artist_id}")
            if should_close_conn:
                conn.close()
            return 0
        
        headers = {
            "Authorization": f"Discogs token={self.discogs_token}",
            "User-Agent": "MusicLibraryManager/1.0"
        }
        
        url = f"https://api.discogs.com/artists/{discogs_id}/releases"
        params = {
            "sort": "year",
            "sort_order": "asc",
            "per_page": 100
        }
        
        processed_count = 0
        page = 1
        
        try:
            # Obtener el nombre del artista para los logs
            cursor.execute("SELECT name FROM artists WHERE id = ?", (artist_id,))
            artist_name = cursor.fetchone()[0]
            print(f"Procesando discografía de {artist_name} (ID local: {artist_id}, Discogs ID: {discogs_id})")
            
            while True:
                params["page"] = page
                
                # Añadir un retraso para respetar los límites de la API
                time.sleep(1.5)
                
                print(f"  Obteniendo página {page} de lanzamientos...")
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    print(f"  Error al obtener lanzamientos: {response.status_code}")
                    print(f"  {response.text}")
                    break
                
                data = response.json()
                releases = data.get('releases', [])
                
                if not releases:
                    print("  No se encontraron más lanzamientos")
                    break
                
                page_processed = 0
                for release in releases:
                    # Filtrar lanzamientos según criterios como en el ejemplo de curl
                    role = release.get('role')
                    format_info = release.get('format')
                    title = release.get('title', '')
                    
                    # Verificar los criterios de filtrado
                    format_matches = False
                    if format_info is None:
                        format_matches = True
                    elif isinstance(format_info, list):
                        format_matches = any(f.lower() in self.accepted_formats for f in format_info if isinstance(f, str))
                    elif isinstance(format_info, str):
                        format_matches = any(f.lower() in self.accepted_formats for f in format_info.lower().split(','))
                    

                    # Añadir solo los lanzamientos del artista, o colaboraciones tambien.
                    if self.rol_principal == True:
                        if role == 'Main' and format_matches:
                            self.process_discogs_release(release, artist_id, cursor)
                            processed_count += 1
                            page_processed += 1
                    elif self.rol_principal == False:
                        if  format_matches:
                            self.process_discogs_release(release, artist_id, cursor)
                            processed_count += 1
                            page_processed += 1
                    
                
                print(f"  Procesados {page_processed} lanzamientos de la página {page}")
                
                # Comprobar si hay más páginas
                if page >= data.get('pagination', {}).get('pages', 0):
                    print(f"  Todas las páginas procesadas ({page})")
                    break
                
                page += 1
                
            conn.commit()
            print(f"Procesados un total de {processed_count} lanzamientos para {artist_name}")
            
        except Exception as e:
            print(f"Error procesando artista {artist_id}: {e}")
            
        finally:
            if should_close_conn:
                conn.close()
            
        return processed_count

    def run(self):
        """
        Ejecuta el proceso completo: crear tabla e importar todos los lanzamientos
        """
        print("Iniciando módulo de discografía de Discogs")
        self.create_discogs_discography_table()
        
        if not self.discogs_token:
            print("ERROR: No se proporcionó un token de Discogs. Por favor, añade 'discogs_token' a la configuración.")
            return
        
        artists = self.get_artists_with_discogs()
        print(f"Se encontraron {len(artists)} artistas con enlaces a Discogs")
        
        # Procesar todos los artistas
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        total_processed = 0
        try:
            for artist_id, discogs_id in artists:
                processed = self.import_artist_discogs_releases(artist_id, discogs_id, conn, cursor)
                total_processed += processed
        finally:
            conn.close()
            
        print(f"Proceso completado. Se procesaron {total_processed} lanzamientos en total.")




def main(config=None):
    """
    Función principal para ejecutar el módulo de discografía de Discogs
    
    Args:
        config (dict): Configuración opcional con los siguientes parámetros:
            - discogs_token: Token para la API de Discogs
            - db_path: Ruta a la base de datos (opcional)
            - force_update: Forzar actualización de registros existentes (opcional)
    """
    if config is None:
        config = {}
        
    module = DiscogsDiscographyModule(config)
    module.run()
    
if __name__ == "__main__":
    main()