import sqlite3
import os
import re
from base_module import BaseModule, PROJECT_ROOT

class ArtistMentions:
    """Clase para buscar menciones de artistas en feeds y crear registros en la tabla 'menciones'"""
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.db_path = self.config.get('db_path', os.path.join(PROJECT_ROOT, 'data', 'music_library.db'))
        self.force_update = self.config.get('force_update', False)
        
    def create_menciones_table(self):
        """Crea la tabla 'menciones' si no existe"""
        sql = """
        CREATE TABLE IF NOT EXISTS menciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER NOT NULL,
            artist_name TEXT NOT NULL,
            feed_id INTEGER NOT NULL,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (feed_id) REFERENCES feeds(id)
        );
        """
        self.execute_query(sql)
        print("Tabla 'menciones' creada o verificada")
        
    def get_all_artists(self):
        """Obtiene todos los artistas de la base de datos"""
        sql = "SELECT id, name FROM artists"
        return self.execute_query(sql, fetch=True)
        
    def get_all_feeds(self):
        """Obtiene todos los feeds con su contenido"""
        sql = "SELECT id, entity_type, entity_id, content FROM feeds WHERE content IS NOT NULL"
        return self.execute_query(sql, fetch=True)
        
    def get_artist_albums(self):
        """Obtiene un mapeo de álbumes a artistas"""
        sql = "SELECT id, artist_id FROM albums"
        result = self.execute_query(sql, fetch=True)
        
        # Crear un diccionario donde la clave es el id del álbum y el valor es el id del artista
        album_to_artist = {}
        for album_id, artist_id in result:
            album_to_artist[album_id] = artist_id
            
        return album_to_artist
        
    def find_mentions(self, artists, feeds):
        """Busca menciones de artistas en el contenido de los feeds"""
        menciones = []
        
        # Si force_update está activado, limpiamos registros previos
        if self.force_update:
            self.execute_query("DELETE FROM menciones")
            print("Registros previos eliminados debido a force_update")
        
        # Verificamos si ya hay menciones para no duplicar
        existing_mentions = self.execute_query(
            "SELECT artist_id, feed_id FROM menciones", 
            fetch=True
        )
        existing_set = {(m[0], m[1]) for m in existing_mentions} if existing_mentions else set()
        
        # Obtenemos el mapeo de álbumes a artistas
        album_to_artist = self.get_artist_albums()
        
        total_feeds = len(feeds)
        for i, (feed_id, entity_type, entity_id, content) in enumerate(feeds):
            if not content:
                continue
                
            print(f"Procesando feed {i+1}/{total_feeds} (ID: {feed_id})")
            
            # Convierte el contenido a minúsculas para comparación sin distinción de mayúsculas
            content_lower = content.lower()
            
            for artist_id, artist_name in artists:
                # Evitar menciones cuando el feed es sobre el propio artista
                if entity_type == 'artists' and int(entity_id) == int(artist_id):
                    continue
                    
                # Evitar menciones cuando el feed es sobre un álbum del artista
                if entity_type == 'album' and int(album_to_artist.get(int(entity_id), -1)) == int(artist_id):
                    continue
                
                # Preparamos el patrón de búsqueda
                pattern = r'\b' + re.escape(artist_name.lower()) + r'\b'
                
                # Buscamos coincidencias completas de palabras
                if re.search(pattern, content_lower):
                    # Evitamos duplicados
                    if (artist_id, feed_id) not in existing_set:
                        menciones.append((artist_id, artist_name, feed_id))
                        existing_set.add((artist_id, feed_id))
        
        return menciones
        
    def save_mentions(self, menciones):
        """Guarda las menciones encontradas en la tabla 'menciones'"""
        if not menciones:
            print("No se encontraron nuevas menciones")
            return
            
        sql = "INSERT INTO menciones (artist_id, artist_name, feed_id) VALUES (?, ?, ?)"
        self.execute_query(sql, params=menciones, many=True)
        print(f"Se guardaron {len(menciones)} nuevas menciones")
        
    def execute_query(self, sql, params=None, fetch=False, many=False):
        """Ejecuta una consulta SQL"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if many and params:
                cursor.executemany(sql, params)
            elif params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
                
            if fetch:
                result = cursor.fetchall()
            else:
                result = None
                
            conn.commit()
            return result
        except Exception as e:
            print(f"Error al ejecutar consulta: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
            
    def run(self):
        """Ejecuta el proceso completo"""
        print("Iniciando búsqueda de menciones de artistas en feeds...")
        
        # Crear tabla si no existe
        self.create_menciones_table()
        
        # Obtener todos los artistas
        artists = self.get_all_artists()
        print(f"Se encontraron {len(artists)} artistas en la base de datos")
        
        # Obtener todos los feeds con contenido
        feeds = self.get_all_feeds()
        print(f"Se encontraron {len(feeds)} feeds con contenido para procesar")
        
        # Buscar menciones
        menciones = self.find_mentions(artists, feeds)
        
        # Guardar menciones
        self.save_mentions(menciones)
        
        print("Proceso completado")

def main(config=None):
    """Función principal para ejecutar desde db_creator.py"""
    processor = ArtistMentions(config)
    processor.run()
    
if __name__ == "__main__":
    main()