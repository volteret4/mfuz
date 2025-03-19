import sqlite3
import os
import argparse
from collections import defaultdict
import shutil
from datetime import datetime

class DuplicateManager:

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.backup_path = None
        self.stats = {
            "songs_deleted": 0,
            "artists_deleted": 0,
            "albums_deleted": 0,
            "albums_merged": 0,
            "files_deleted": 0,
            "files_kept": 0,
            "skipped": 0
        }

    
    def connect_to_db(self):
        """Conecta a la base de datos SQLite"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"La base de datos no existe en: {self.db_path}")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
    
    def backup_database(self):
        """Crea una copia de seguridad de la base de datos antes de modificarla"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.dirname(self.db_path)
        db_name = os.path.basename(self.db_path)
        self.backup_path = os.path.join(backup_dir, f"{db_name}_backup_{timestamp}")
        shutil.copy2(self.db_path, self.backup_path)
        print(f"\n✅ Copia de seguridad creada: {self.backup_path}")
    
    def find_and_manage_duplicate_songs(self):
        """Encuentra canciones duplicadas y permite gestionar cada conjunto"""
        print("\n=== DETECTANDO Y GESTIONANDO DUPLICADOS EN CANCIONES ===")
        
        # 1. Duplicados por ruta de archivo
        print("\n1. Canciones con rutas de archivo duplicadas:")
        self.cursor.execute("""
            SELECT file_path, COUNT(*) as count 
            FROM songs 
            GROUP BY file_path 
            HAVING count > 1
        """)
        
        file_path_dupes = self.cursor.fetchall()
        if file_path_dupes:
            print(f"  ¡Encontrados {len(file_path_dupes)} archivos duplicados!")
            
            for file_path, count in file_path_dupes:
                print(f"\n  📂 Archivo: {file_path} ({count} entradas)")
                
                # Obtener los duplicados específicos
                self.cursor.execute("""
                    SELECT id, title, artist, album, last_modified, added_timestamp 
                    FROM songs 
                    WHERE file_path = ?
                    ORDER BY added_timestamp DESC
                """, (file_path,))
                
                duplicates = self.cursor.fetchall()
                
                self._handle_duplicate_selection(
                    duplicates,
                    "songs",
                    ["ID", "Título", "Artista", "Álbum", "Última modificación", "Añadido"],
                    file_path
                )
        else:
            print("  ✓ No se encontraron rutas de archivo duplicadas.")
        
        # 2. Canciones con misma combinación título-artista-álbum
        print("\n2. Canciones con la misma combinación título-artista-álbum:")
        self.cursor.execute("""
            SELECT title, artist, album, COUNT(*) as count 
            FROM songs 
            WHERE title IS NOT NULL AND artist IS NOT NULL AND album IS NOT NULL
            GROUP BY title, artist, album 
            HAVING count > 1
        """)
        
        metadata_dupes = self.cursor.fetchall()
        if metadata_dupes:
            print(f"  ¡Encontrados {len(metadata_dupes)} conjuntos de metadatos duplicados!")
            
            for title, artist, album, count in metadata_dupes:
                print(f"\n  🎵 '{title}' por {artist} en '{album}' ({count} entradas)")
                
                # Obtener los duplicados específicos
                self.cursor.execute("""
                    SELECT id, file_path, last_modified, added_timestamp, duration, bitrate 
                    FROM songs 
                    WHERE title = ? AND artist = ? AND album = ?
                    ORDER BY bitrate DESC, added_timestamp DESC
                """, (title, artist, album))
                
                duplicates = self.cursor.fetchall()
                
                self._handle_duplicate_selection(
                    duplicates,
                    "songs",
                    ["ID", "Ruta", "Última modificación", "Añadido", "Duración", "Bitrate"],
                    f"{title} - {artist}"
                )
        else:
            print("  ✓ No se encontraron metadatos duplicados.")
    
    def find_and_manage_duplicate_artists(self):
        """Encuentra artistas duplicados y permite gestionar cada conjunto"""
        print("\n=== DETECTANDO Y GESTIONANDO DUPLICADOS EN ARTISTAS ===")
        
        self.cursor.execute("""
            SELECT name, COUNT(*) as count 
            FROM artists 
            GROUP BY name 
            HAVING count > 1
        """)
        
        name_dupes = self.cursor.fetchall()
        if name_dupes:
            print(f"  ¡Encontrados {len(name_dupes)} nombres de artistas duplicados!")
            
            for name, count in name_dupes:
                print(f"\n  🎤 Artista: '{name}' ({count} entradas)")
                
                # Obtener los duplicados específicos
                self.cursor.execute("""
                    SELECT id, mbid, tags, origin, formed_year, last_updated
                    FROM artists 
                    WHERE name = ?
                    ORDER BY last_updated DESC
                """, (name,))
                
                duplicates = self.cursor.fetchall()
                
                self._handle_duplicate_selection(
                    duplicates,
                    "artists",
                    ["ID", "MBID", "Tags", "Origen", "Año formación", "Última actualización"],
                    name
                )
        else:
            print("  ✓ No se encontraron nombres de artistas duplicados.")
    
    def find_and_manage_duplicate_albums(self):
        """Encuentra álbumes duplicados y permite gestionar cada conjunto"""
        print("\n=== DETECTANDO Y GESTIONANDO DUPLICADOS EN ÁLBUMES ===")
        
        self.cursor.execute("""
            SELECT a.name, art.name as artist_name, COUNT(*) as count 
            FROM albums a
            JOIN artists art ON a.artist_id = art.id
            GROUP BY a.name, art.name 
            HAVING count > 1
        """)
        
        album_dupes = self.cursor.fetchall()
        if album_dupes:
            print(f"  ¡Encontrados {len(album_dupes)} álbumes duplicados!")
            
            for album_name, artist_name, count in album_dupes:
                print(f"\n  💿 Álbum: '{album_name}' por {artist_name} ({count} entradas)")
                
                # Obtener los duplicados específicos
                self.cursor.execute("""
                    SELECT a.id, a.year, a.mbid, a.folder_path, a.total_tracks, a.last_updated
                    FROM albums a
                    JOIN artists art ON a.artist_id = art.id
                    WHERE a.name = ? AND art.name = ?
                    ORDER BY a.last_updated DESC
                """, (album_name, artist_name))
                
                duplicates = self.cursor.fetchall()
                
                self._handle_duplicate_selection(
                    duplicates,
                    "albums",
                    ["ID", "Año", "MBID", "Ruta", "Pistas", "Actualización"],
                    f"{album_name} - {artist_name}"
                )
        else:
            print("  ✓ No se encontraron álbumes duplicados.")
    
    def _handle_duplicate_selection(self, duplicates, table, headers, item_description):
        """Maneja la selección interactiva de registros duplicados"""
        print("\n  Elige qué entrada conservar y cuáles eliminar:")
        
        # Mostrar opciones
        for i, dupe in enumerate(duplicates, 1):
            print(f"\n  [{i}] {headers[0]}: {dupe[0]}")
            for j, value in enumerate(dupe[1:], 1):
                if value is not None:
                    print(f"      {headers[j]}: {value}")
        
        print("\n  [A] Conservar todo")
        print("  [S] Omitir este conjunto")
        
        while True:
            choice = input("\n  Entrada a conservar (número, 'A' para conservar todo, 'S' para omitir): ").strip().upper()
            
            if choice == 'A':
                print("  ➡️ Conservando todas las entradas")
                self.stats["skipped"] += 1
                return
            
            if choice == 'S':
                print("  ➡️ Omitiendo este conjunto")
                self.stats["skipped"] += 1
                return
            
            try:
                idx = int(choice)
                if 1 <= idx <= len(duplicates):
                    # Registro a conservar
                    keep_id = duplicates[idx-1][0]
                    
                    # Confirmación
                    confirm = input(f"  ¿Eliminar todos excepto #{idx}? (S/N): ").strip().upper()
                    if confirm == 'S':
                        self._delete_duplicates(table, duplicates, keep_id, item_description)
                        return
                    else:
                        print("  ➡️ Operación cancelada")
                else:
                    print(f"  ❌ Opción inválida. Elige entre 1 y {len(duplicates)}, 'A' o 'S'")
            except ValueError:
                print("  ❌ Entrada inválida. Introduce un número, 'A' o 'S'")
    
    def _delete_duplicates(self, table, duplicates, keep_id, item_description):
        """Elimina los registros duplicados excepto el seleccionado para conservar"""
        try:
            # IDs a eliminar
            delete_ids = [d[0] for d in duplicates if d[0] != keep_id]
            
            if table == "songs":
                # Comprobar si debemos eliminar archivos físicos
                file_paths = []
                for dupe in duplicates:
                    if dupe[0] != keep_id and len(dupe) > 1 and dupe[1] and os.path.exists(dupe[1]):
                        file_paths.append(dupe[1])
                
                # Primero eliminar de la base de datos
                for delete_id in delete_ids:
                    self.cursor.execute(f"DELETE FROM {table} WHERE id = ?", (delete_id,))
                    print(f"  🗑️ Eliminado registro #{delete_id} de {table}")
                
                # Luego preguntar por los archivos físicos
                if file_paths:
                    for path in file_paths:
                        choice = input(f"\n  ¿Eliminar archivo físico '{path}'? (S/N): ").strip().upper()
                        if choice == 'S':
                            try:
                                os.remove(path)
                                print(f"  🗑️ Archivo físico eliminado: {path}")
                                self.stats["files_deleted"] += 1
                            except Exception as e:
                                print(f"  ❌ Error al eliminar archivo: {e}")
                        else:
                            print("  ➡️ Archivo físico conservado")
                            self.stats["files_kept"] += 1
                
                self.stats["songs_deleted"] += len(delete_ids)
            
            elif table == "artists":
                # Eliminar artistas duplicados
                for delete_id in delete_ids:
                    self.cursor.execute(f"DELETE FROM {table} WHERE id = ?", (delete_id,))
                    print(f"  🗑️ Eliminado artista #{delete_id}")
                self.stats["artists_deleted"] += len(delete_ids)
            
            elif table == "albums":
                # Eliminar álbumes duplicados
                for delete_id in delete_ids:
                    self.cursor.execute(f"DELETE FROM {table} WHERE id = ?", (delete_id,))
                    print(f"  🗑️ Eliminado álbum #{delete_id}")
                self.stats["albums_deleted"] += len(delete_ids)
            
            self.conn.commit()
            print(f"  ✅ Se eliminaron {len(delete_ids)} entradas duplicadas para '{item_description}'")
        
        except Exception as e:
            self.conn.rollback()
            print(f"  ❌ Error al eliminar duplicados: {e}")
    

    def show_summary(self):
        """Muestra un resumen de las acciones realizadas"""
        print("\n" + "="*60)
        print(" RESUMEN DE OPERACIONES ")
        print("="*60)
        print(f"✅ Canciones eliminadas: {self.stats['songs_deleted']}")
        print(f"✅ Artistas eliminados: {self.stats['artists_deleted']}")
        print(f"✅ Álbumes eliminados: {self.stats['albums_deleted']}")
        print(f"✅ Álbumes fusionados: {self.stats['albums_merged']}")
        print(f"✅ Archivos físicos eliminados: {self.stats['files_deleted']}")
        print(f"✅ Archivos físicos conservados: {self.stats['files_kept']}")
        print(f"✅ Conjuntos de duplicados omitidos: {self.stats['skipped']}")
        
        # Recuento actual
        self.cursor.execute("SELECT COUNT(*) FROM albums")
        current_albums = self.cursor.fetchone()[0]
        print(f"\n📊 Total actual de álbumes en la base de datos: {current_albums}")
        
        print("\n📋 Copia de seguridad de la base de datos original: {self.backup_path}")
        print("="*60)
        

    def find_and_manage_duplicate_albums(self):
        """Encuentra álbumes duplicados y permite gestionar cada conjunto"""
        print("\n=== DETECTANDO Y GESTIONANDO DUPLICADOS EN ÁLBUMES ===")
        
        # 1. Álbumes con el mismo nombre y artista (posiblemente con rutas diferentes)
        self.cursor.execute("""
            SELECT a.name, art.name as artist_name, COUNT(*) as count 
            FROM albums a
            JOIN artists art ON a.artist_id = art.id
            GROUP BY a.name, art.name 
            HAVING count > 1
        """)
        
        album_dupes = self.cursor.fetchall()
        if album_dupes:
            print(f"  ¡Encontrados {len(album_dupes)} álbumes duplicados!")
            
            for album_name, artist_name, count in album_dupes:
                print(f"\n  💿 Álbum: '{album_name}' por {artist_name} ({count} entradas)")
                
                # Obtener los duplicados específicos con más detalles
                self.cursor.execute("""
                    SELECT a.id, a.year, a.mbid, a.folder_path, a.total_tracks, a.last_updated
                    FROM albums a
                    JOIN artists art ON a.artist_id = art.id
                    WHERE a.name = ? AND art.name = ?
                    ORDER BY a.folder_path, a.last_updated DESC
                """, (album_name, artist_name))
                
                duplicates = self.cursor.fetchall()
                
                # Verificar si tienen rutas diferentes
                paths = set(d[3] for d in duplicates if d[3] is not None)
                if len(paths) > 1:
                    print(f"  ⚠️ Este álbum tiene {len(paths)} rutas diferentes!")
                
                self._handle_duplicate_selection(
                    duplicates,
                    "albums",
                    ["ID", "Año", "MBID", "Ruta", "Pistas", "Actualización"],
                    f"{album_name} - {artist_name}"
                )
        else:
            print("  ✓ No se encontraron álbumes duplicados.")
        
        # 2. Búsqueda adicional por rutas de carpeta similares
        print("\n  Buscando rutas de álbumes similares...")
        
        # Obtener todas las rutas de álbumes
        self.cursor.execute("""
            SELECT DISTINCT folder_path FROM albums 
            WHERE folder_path IS NOT NULL AND folder_path != ''
        """)
        
        path_similarities = defaultdict(list)
        paths = [p[0] for p in self.cursor.fetchall()]
        
        # Agrupar rutas por nombre de carpeta base (último componente)
        for path in paths:
            if path:
                base_folder = os.path.basename(os.path.normpath(path))
                path_similarities[base_folder].append(path)
        
        # Filtrar solo aquellos con múltiples rutas para el mismo nombre de carpeta
        similar_paths = {k: v for k, v in path_similarities.items() if len(v) > 1}
        
        if similar_paths:
            print(f"  ¡Encontradas {len(similar_paths)} carpetas con nombres similares!")
            
            for folder_name, folder_paths in similar_paths.items():
                print(f"\n  📁 Carpetas con nombre '{folder_name}':")
                
                for i, path in enumerate(folder_paths, 1):
                    print(f"    [{i}] {path}")
                    
                    # Obtener álbumes en esta ruta
                    self.cursor.execute("""
                        SELECT a.id, a.name, art.name as artist_name, a.year, a.total_tracks
                        FROM albums a
                        JOIN artists art ON a.artist_id = art.id
                        WHERE a.folder_path = ?
                    """, (path,))
                    
                    albums = self.cursor.fetchall()
                    if albums:
                        for album in albums:
                            print(f"       - [{album[0]}] '{album[1]}' por {album[2]} ({album[3]}) - {album[4]} pistas")
                
                self._handle_similar_paths(folder_name, folder_paths)
        else:
            print("  ✓ No se encontraron rutas de carpetas similares.")

    def _handle_similar_paths(self, folder_name, paths):
        """Maneja rutas similares para álbumes, permitiendo fusionar o mantener separadas"""
        print("\n  Opciones para carpetas similares:")
        print("  [F] Fusionar álbumes (conservar una ruta y actualizar referencias)")
        print("  [I] Ignorar (mantener todas las rutas)")
        
        while True:
            choice = input("\n  ¿Qué deseas hacer? (F/I): ").strip().upper()
            
            if choice == 'I':
                print("  ➡️ Manteniendo todas las rutas separadas")
                self.stats["skipped"] += 1
                return
            
            if choice == 'F':
                print("\n  Elige la ruta principal a conservar:")
                for i, path in enumerate(paths, 1):
                    print(f"  [{i}] {path}")
                
                try:
                    idx = int(input("\n  Ruta a conservar (número): ").strip())
                    if 1 <= idx <= len(paths):
                        # Ruta a conservar
                        keep_path = paths[idx-1]
                        
                        # Confirmación
                        confirm = input(f"  ¿Fusionar todos los álbumes en '{keep_path}'? (S/N): ").strip().upper()
                        if confirm == 'S':
                            self._merge_album_paths(keep_path, [p for p in paths if p != keep_path], folder_name)
                            return
                        else:
                            print("  ➡️ Operación cancelada")
                    else:
                        print(f"  ❌ Opción inválida. Elige entre 1 y {len(paths)}")
                except ValueError:
                    print("  ❌ Entrada inválida. Introduce un número")
            else:
                print("  ❌ Opción inválida. Introduce 'F' o 'I'")

    def _merge_album_paths(self, keep_path, remove_paths, folder_name):
        """Fusiona álbumes con rutas similares"""
        try:
            merged_count = 0
            
            # Para cada ruta a eliminar
            for path in remove_paths:
                # Obtener álbumes en esta ruta
                self.cursor.execute("""
                    SELECT id, name, artist_id, year
                    FROM albums
                    WHERE folder_path = ?
                """, (path,))
                
                albums_to_update = self.cursor.fetchall()
                
                # Para cada álbum en la ruta a eliminar
                for album_id, album_name, artist_id, year in albums_to_update:
                    # Verificar si existe un álbum equivalente en la ruta a conservar
                    self.cursor.execute("""
                        SELECT id
                        FROM albums
                        WHERE folder_path = ? AND name = ? AND artist_id = ?
                    """, (keep_path, album_name, artist_id))
                    
                    matching_album = self.cursor.fetchone()
                    
                    if matching_album:
                        # Existe un álbum equivalente, actualizar referencias de canciones
                        target_album_id = matching_album[0]
                        
                        # Contar canciones afectadas
                        self.cursor.execute("SELECT COUNT(*) FROM songs WHERE album_id = ?", (album_id,))
                        songs_count = self.cursor.fetchone()[0]
                        
                        # Actualizar referencias de canciones
                        self.cursor.execute("""
                            UPDATE songs
                            SET album_id = ?
                            WHERE album_id = ?
                        """, (target_album_id, album_id))
                        
                        # Eliminar el álbum duplicado
                        self.cursor.execute("DELETE FROM albums WHERE id = ?", (album_id,))
                        
                        merged_count += 1
                        print(f"  ✅ Fusionado: '{album_name}' (ID {album_id} → {target_album_id}), {songs_count} canciones actualizadas")
                    else:
                        # No existe equivalente, solo actualizar la ruta
                        self.cursor.execute("""
                            UPDATE albums
                            SET folder_path = ?
                            WHERE id = ?
                        """, (keep_path, album_id))
                        
                        print(f"  ✅ Actualizada ruta: '{album_name}' (ID {album_id})")
                        merged_count += 1
            
            self.conn.commit()
            print(f"  ✅ Se fusionaron/actualizaron {merged_count} álbumes para carpeta '{folder_name}'")
            self.stats["albums_merged"] = self.stats.get("albums_merged", 0) + merged_count
        
        except Exception as e:
            self.conn.rollback()
            print(f"  ❌ Error al fusionar álbumes: {e}")


    def run(self):
        """Ejecuta el gestor de duplicados completo"""
        try:
            self.connect_to_db()
            self.backup_database()
            
            print("\n¡Bienvenido al Gestor Interactivo de Duplicados!")
            print("\nCon esta herramienta podrás:")
            print("- Ver todos los álbumes duplicados en tu base de datos")
            print("- Detectar álbumes con rutas diferentes")
            print("- Elegir qué registros conservar y cuáles fusionar")
            print("\nSe ha creado una copia de seguridad de tu base de datos antes de comenzar.")
            
            input("\nPresiona ENTER para comenzar...")
            
            # Obtener conteo inicial
            self.cursor.execute("SELECT COUNT(*) FROM albums")
            initial_albums = self.cursor.fetchone()[0]
            print(f"\n📊 Total inicial de álbumes en la base de datos: {initial_albums}")
            
            # Ejecutar los análisis y gestión interactiva (enfocado en álbumes)
            self.find_and_manage_duplicate_albums()
            
            # También podemos ejecutar los demás si se desea
            choice = input("\n¿Deseas también buscar duplicados en canciones y artistas? (S/N): ").strip().upper()
            if choice == 'S':
                self.find_and_manage_duplicate_songs()
                self.find_and_manage_duplicate_artists()
            
            # Mostrar resumen final
            self.show_summary()
            
            self.conn.close()
            
        except Exception as e:
            print(f"\n❌ Error durante la ejecución: {e}")
            if self.conn:
                self.conn.close()

def main():
    parser = argparse.ArgumentParser(description="Gestor interactivo de duplicados para base de datos musical")
    parser.add_argument("--db", required=True, help="Ruta al archivo de la base de datos SQLite")
    args = parser.parse_args()
    
    manager = DuplicateManager(args.db)
    manager.run()

if __name__ == "__main__":
    main()