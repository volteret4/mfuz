import sqlite3
import argparse
import os
from datetime import datetime

def connect_to_db(db_path):
    """Conecta a la base de datos SQLite."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"La base de datos no existe en la ruta: {db_path}")
    return sqlite3.connect(db_path)

def check_missing_values(conn, args):
    """Verifica campos vacíos o nulos en tablas principales."""
    results = []
    
    if args.all or args.missing:
        print("\n=== Campos obligatorios faltantes ===")
        
        # Verificar canciones sin título, artista o álbum
        query = """
        SELECT id, file_path, 
               CASE WHEN title IS NULL OR title = '' THEN 'Falta título' ELSE '' END as missing_title,
               CASE WHEN artist IS NULL OR artist = '' THEN 'Falta artista' ELSE '' END as missing_artist,
               CASE WHEN album IS NULL OR album = '' THEN 'Falta álbum' ELSE '' END as missing_album
        FROM songs
        WHERE title IS NULL OR title = '' OR artist IS NULL OR artist = '' OR album IS NULL OR album = ''
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"Encontradas {len(rows)} canciones con información básica faltante:")
            for row in rows:
                missing = []
                if row[2]: missing.append(row[2])
                if row[3]: missing.append(row[3])
                if row[4]: missing.append(row[4])
                print(f"  ID: {row[0]}, Ruta: {row[1]}, Problemas: {', '.join(missing)}")
        else:
            print("No se encontraron canciones con información básica faltante.")
        
        # Verificar artistas sin nombre
        query = """
        SELECT id FROM artists 
        WHERE name IS NULL OR name = '' 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontrados {len(rows)} artistas sin nombre: {', '.join([str(row[0]) for row in rows])}")
        
        # Verificar álbumes sin nombre
        query = """
        SELECT id FROM albums 
        WHERE name IS NULL OR name = '' 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontrados {len(rows)} álbumes sin nombre: {', '.join([str(row[0]) for row in rows])}")
    
    return results

def check_orphan_records(conn, args):
    """Verifica registros huérfanos entre tablas relacionadas."""
    if args.all or args.orphans:
        print("\n=== Registros huérfanos ===")
        
        # Canciones con artistas que no existen en la tabla artists
        query = """
        SELECT s.id, s.title, s.artist 
        FROM songs s 
        LEFT JOIN artists a ON s.artist = a.name 
        WHERE a.name IS NULL 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"Encontradas {len(rows)} canciones con artistas que no existen en la tabla artists:")
            for row in rows:
                print(f"  Canción ID: {row[0]}, Título: {row[1]}, Artista: {row[2]}")
        else:
            print("No se encontraron canciones con artistas inexistentes.")
        
        # Canciones con álbumes que no existen en la tabla albums
        query = """
        SELECT s.id, s.title, s.album 
        FROM songs s 
        LEFT JOIN albums alb ON s.album = alb.name 
        WHERE alb.name IS NULL 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontradas {len(rows)} canciones con álbumes que no existen en la tabla albums:")
            for row in rows:
                print(f"  Canción ID: {row[0]}, Título: {row[1]}, Álbum: {row[2]}")
        else:
            print("No se encontraron canciones con álbumes inexistentes.")
        
        # Letras sin canción asociada
        query = """
        SELECT l.id, l.track_id 
        FROM lyrics l 
        LEFT JOIN songs s ON l.track_id = s.id 
        WHERE s.id IS NULL 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontradas {len(rows)} letras sin canción asociada:")
            for row in rows:
                print(f"  Letra ID: {row[0]}, Track ID inexistente: {row[1]}")
        else:
            print("No se encontraron letras sin canción asociada.")
        
        # Enlaces de canciones sin canción asociada
        query = """
        SELECT sl.id, sl.song_id 
        FROM song_links sl 
        LEFT JOIN songs s ON sl.song_id = s.id 
        WHERE s.id IS NULL 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontrados {len(rows)} enlaces de canciones sin canción asociada:")
            for row in rows:
                print(f"  Enlace ID: {row[0]}, Song ID inexistente: {row[1]}")
        else:
            print("No se encontraron enlaces de canciones sin canción asociada.")

def check_duplicates(conn, args):
    """Verifica registros duplicados."""
    if args.all or args.duplicates:
        print("\n=== Registros duplicados ===")
        
        # Canciones duplicadas (mismo título, artista y álbum)
        query = """
        SELECT title, artist, album, COUNT(*) as count 
        FROM songs 
        GROUP BY title, artist, album 
        HAVING COUNT(*) > 1 
        ORDER BY count DESC 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"Encontrados {len(rows)} conjuntos de canciones duplicadas:")
            for row in rows:
                print(f"  Título: '{row[0]}', Artista: '{row[1]}', Álbum: '{row[2]}', Duplicados: {row[3]}")
                
                # Obtener detalles de las duplicadas
                detail_query = """
                SELECT id, file_path, duration, bitrate 
                FROM songs 
                WHERE title = ? AND artist = ? AND album = ? 
                LIMIT ?
                """
                detail_cursor = conn.execute(detail_query, (row[0], row[1], row[2], args.limit * 2))
                details = detail_cursor.fetchall()
                for detail in details:
                    print(f"    ID: {detail[0]}, Ruta: {detail[1]}, Duración: {detail[2]}, Bitrate: {detail[3]}")
        else:
            print("No se encontraron canciones duplicadas.")
        
        # Artistas duplicados
        query = """
        SELECT name, COUNT(*) as count 
        FROM artists 
        GROUP BY name 
        HAVING COUNT(*) > 1 
        ORDER BY count DESC 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontrados {len(rows)} artistas duplicados:")
            for row in rows:
                print(f"  Nombre: '{row[0]}', Duplicados: {row[1]}")
                
                # Obtener IDs de los duplicados
                detail_query = "SELECT id FROM artists WHERE name = ? LIMIT ?"
                detail_cursor = conn.execute(detail_query, (row[0], args.limit * 2))
                details = detail_cursor.fetchall()
                ids = [str(detail[0]) for detail in details]
                print(f"    IDs: {', '.join(ids)}")
        else:
            print("No se encontraron artistas duplicados.")
        
        # Álbumes duplicados (mismo nombre y artista)
        query = """
        SELECT a.name, art.name, COUNT(*) as count 
        FROM albums a
        JOIN artists art ON a.artist_id = art.id
        GROUP BY a.name, art.name 
        HAVING COUNT(*) > 1 
        ORDER BY count DESC 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontrados {len(rows)} álbumes duplicados:")
            for row in rows:
                print(f"  Álbum: '{row[0]}', Artista: '{row[1]}', Duplicados: {row[2]}")
        else:
            print("No se encontraron álbumes duplicados.")

def check_inconsistent_metadata(conn, args):
    """Verifica inconsistencias en los metadatos."""
    if args.all or args.metadata:
        print("\n=== Inconsistencias en metadatos ===")
        
        # Canciones del mismo álbum con diferentes artistas de álbum
        query = """
        SELECT album, COUNT(DISTINCT album_artist) as different_artists 
        FROM songs 
        GROUP BY album 
        HAVING COUNT(DISTINCT album_artist) > 1 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"Encontrados {len(rows)} álbumes con inconsistencias en el artista del álbum:")
            for row in rows:
                print(f"  Álbum: '{row[0]}', Número de artistas diferentes: {row[1]}")
                
                # Mostrar los diferentes artistas de álbum
                detail_query = """
                SELECT DISTINCT album_artist, COUNT(*) as track_count 
                FROM songs 
                WHERE album = ? 
                GROUP BY album_artist 
                LIMIT ?
                """
                detail_cursor = conn.execute(detail_query, (row[0], args.limit * 2))
                details = detail_cursor.fetchall()
                for detail in details:
                    print(f"    Artista de álbum: '{detail[0]}', Pistas: {detail[1]}")
        else:
            print("No se encontraron álbumes con inconsistencias en el artista del álbum.")
        
        # Canciones del mismo álbum con diferentes años
        query = """
        SELECT album, COUNT(DISTINCT date) as different_dates 
        FROM songs 
        GROUP BY album 
        HAVING COUNT(DISTINCT date) > 1 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontrados {len(rows)} álbumes con inconsistencias en la fecha:")
            for row in rows:
                print(f"  Álbum: '{row[0]}', Fechas diferentes: {row[1]}")
                
                # Mostrar las diferentes fechas
                detail_query = """
                SELECT DISTINCT date, COUNT(*) as track_count 
                FROM songs 
                WHERE album = ? 
                GROUP BY date 
                LIMIT ?
                """
                detail_cursor = conn.execute(detail_query, (row[0], args.limit * 2))
                details = detail_cursor.fetchall()
                for detail in details:
                    print(f"    Fecha: '{detail[0]}', Pistas: {detail[1]}")
        else:
            print("No se encontraron álbumes con inconsistencias en la fecha.")
        
        # Canciones del mismo álbum con diferentes géneros
        query = """
        SELECT album, COUNT(DISTINCT genre) as different_genres 
        FROM songs 
        GROUP BY album 
        HAVING COUNT(DISTINCT genre) > 1 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontrados {len(rows)} álbumes con inconsistencias en el género:")
            for row in rows:
                print(f"  Álbum: '{row[0]}', Géneros diferentes: {row[1]}")
                
                # Mostrar los diferentes géneros
                detail_query = """
                SELECT DISTINCT genre, COUNT(*) as track_count 
                FROM songs 
                WHERE album = ? 
                GROUP BY genre 
                LIMIT ?
                """
                detail_cursor = conn.execute(detail_query, (row[0], args.limit * 2))
                details = detail_cursor.fetchall()
                for detail in details:
                    print(f"    Género: '{detail[0]}', Pistas: {detail[1]}")
        else:
            print("No se encontraron álbumes con inconsistencias en el género.")

def check_technical_issues(conn, args):
    """Verifica problemas técnicos en los archivos de audio."""
    if args.all or args.technical:
        print("\n=== Problemas técnicos ===")
        
        # Canciones con bitrate bajo (menos de 128 kbps)
        query = """
        SELECT id, title, artist, album, bitrate 
        FROM songs 
        WHERE bitrate > 0 AND bitrate < 128 
        ORDER BY bitrate ASC 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"Encontradas {len(rows)} canciones con bitrate bajo (< 128 kbps):")
            for row in rows:
                print(f"  ID: {row[0]}, Título: '{row[1]}', Artista: '{row[2]}', Álbum: '{row[3]}', Bitrate: {row[4]} kbps")
        else:
            print("No se encontraron canciones con bitrate bajo.")
        
        # Canciones con duración sospechosamente larga (más de 20 minutos) o corta (menos de 30 segundos)
        query = """
        SELECT id, title, artist, album, duration 
        FROM songs 
        WHERE (duration > 1200 OR (duration > 0 AND duration < 30)) 
        ORDER BY duration DESC 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontradas {len(rows)} canciones con duración sospechosa (>20 min o <30 seg):")
            for row in rows:
                duration_min = int(row[4] // 60)
                duration_sec = int(row[4] % 60)
                print(f"  ID: {row[0]}, Título: '{row[1]}', Artista: '{row[2]}', Álbum: '{row[3]}', Duración: {duration_min}:{duration_sec:02d}")
        else:
            print("No se encontraron canciones con duración sospechosa.")
        
        # Archivos sin bitrate o sample_rate
        query = """
        SELECT id, title, artist, album 
        FROM songs 
        WHERE bitrate IS NULL OR bitrate = 0 OR sample_rate IS NULL OR sample_rate = 0 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontradas {len(rows)} canciones sin información técnica completa:")
            for row in rows:
                print(f"  ID: {row[0]}, Título: '{row[1]}', Artista: '{row[2]}', Álbum: '{row[3]}'")
        else:
            print("No se encontraron canciones sin información técnica completa.")

def check_path_issues(conn, args):
    """Verifica problemas con rutas de archivos."""
    if args.all or args.paths:
        print("\n=== Problemas con rutas de archivos ===")
        
        # Canciones con rutas duplicadas
        query = """
        SELECT file_path, COUNT(*) as count 
        FROM songs 
        GROUP BY file_path 
        HAVING COUNT(*) > 1 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"Encontradas {len(rows)} rutas de archivo duplicadas:")
            for row in rows:
                print(f"  Ruta: '{row[0]}', Duplicados: {row[1]}")
                
                # Mostrar los detalles de las canciones duplicadas
                detail_query = """
                SELECT id, title, artist, album 
                FROM songs 
                WHERE file_path = ? 
                LIMIT ?
                """
                detail_cursor = conn.execute(detail_query, (row[0], args.limit * 2))
                details = detail_cursor.fetchall()
                for detail in details:
                    print(f"    ID: {detail[0]}, Título: '{detail[1]}', Artista: '{detail[2]}', Álbum: '{detail[3]}'")
        else:
            print("No se encontraron rutas de archivo duplicadas.")
        
        # Canciones con rutas vacías
        query = """
        SELECT id, title, artist, album 
        FROM songs 
        WHERE file_path IS NULL OR file_path = '' 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontradas {len(rows)} canciones sin ruta de archivo:")
            for row in rows:
                print(f"  ID: {row[0]}, Título: '{row[1]}', Artista: '{row[2]}', Álbum: '{row[3]}'")
        else:
            print("No se encontraron canciones sin ruta de archivo.")
        
        # Álbumes con rutas de arte de álbum vacías o nulas
        query = """
        SELECT id, name, artist_id 
        FROM albums 
        WHERE album_art_path IS NULL OR album_art_path = '' 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontrados {len(rows)} álbumes sin ruta de arte de álbum:")
            for row in rows:
                # Obtener el nombre del artista
                artist_query = "SELECT name FROM artists WHERE id = ?"
                artist_cursor = conn.execute(artist_query, (row[2],))
                artist_row = artist_cursor.fetchone()
                artist_name = artist_row[0] if artist_row else "Desconocido"
                
                print(f"  ID: {row[0]}, Álbum: '{row[1]}', Artista: '{artist_name}'")
        else:
            print("No se encontraron álbumes sin ruta de arte de álbum.")

def check_mbid_issues(conn, args):
    """Verifica problemas con MusicBrainz IDs."""
    if args.all or args.mbid:
        print("\n=== Problemas con MusicBrainz IDs ===")
        
        # Canciones con MBIDs duplicados
        query = """
        SELECT mbid, COUNT(*) as count 
        FROM songs 
        WHERE mbid IS NOT NULL AND mbid != '' 
        GROUP BY mbid 
        HAVING COUNT(*) > 1 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"Encontrados {len(rows)} MBIDs duplicados en canciones:")
            for row in rows:
                print(f"  MBID: '{row[0]}', Duplicados: {row[1]}")
                
                # Mostrar los detalles de las canciones con el mismo MBID
                detail_query = """
                SELECT id, title, artist, album 
                FROM songs 
                WHERE mbid = ? 
                LIMIT ?
                """
                detail_cursor = conn.execute(detail_query, (row[0], args.limit * 2))
                details = detail_cursor.fetchall()
                for detail in details:
                    print(f"    ID: {detail[0]}, Título: '{detail[1]}', Artista: '{detail[2]}', Álbum: '{detail[3]}'")
        else:
            print("No se encontraron MBIDs duplicados en canciones.")
        
        # Artistas con MBIDs duplicados
        query = """
        SELECT mbid, COUNT(*) as count 
        FROM artists 
        WHERE mbid IS NOT NULL AND mbid != '' 
        GROUP BY mbid 
        HAVING COUNT(*) > 1 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontrados {len(rows)} MBIDs duplicados en artistas:")
            for row in rows:
                print(f"  MBID: '{row[0]}', Duplicados: {row[1]}")
                
                # Mostrar los detalles de los artistas con el mismo MBID
                detail_query = """
                SELECT id, name 
                FROM artists 
                WHERE mbid = ? 
                LIMIT ?
                """
                detail_cursor = conn.execute(detail_query, (row[0], args.limit * 2))
                details = detail_cursor.fetchall()
                for detail in details:
                    print(f"    ID: {detail[0]}, Nombre: '{detail[1]}'")
        else:
            print("No se encontraron MBIDs duplicados en artistas.")
        
        # Álbumes con MBIDs duplicados
        query = """
        SELECT mbid, COUNT(*) as count 
        FROM albums 
        WHERE mbid IS NOT NULL AND mbid != '' 
        GROUP BY mbid 
        HAVING COUNT(*) > 1 
        LIMIT ?
        """
        cursor = conn.execute(query, (args.limit,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nEncontrados {len(rows)} MBIDs duplicados en álbumes:")
            for row in rows:
                print(f"  MBID: '{row[0]}', Duplicados: {row[1]}")
                
                # Mostrar los detalles de los álbumes con el mismo MBID
                detail_query = """
                SELECT a.id, a.name, art.name as artist_name 
                FROM albums a 
                JOIN artists art ON a.artist_id = art.id 
                WHERE a.mbid = ? 
                LIMIT ?
                """
                detail_cursor = conn.execute(detail_query, (row[0], args.limit * 2))
                details = detail_cursor.fetchall()
                for detail in details:
                    print(f"    ID: {detail[0]}, Álbum: '{detail[1]}', Artista: '{detail[2]}'")
        else:
            print("No se encontraron MBIDs duplicados en álbumes.")

def generate_summary(conn, args):
    """Genera un resumen de la base de datos"""
    if args.all or args.summary:
        print("\n=== Resumen de la base de datos ===")
        
        # Estadísticas generales
        stats = []
        queries = [
            ("Canciones", "SELECT COUNT(*) FROM songs"),
            ("Artistas", "SELECT COUNT(*) FROM artists"),
            ("Álbumes", "SELECT COUNT(*) FROM albums"),
            ("Géneros", "SELECT COUNT(*) FROM genres"),
            ("Letras", "SELECT COUNT(*) FROM lyrics"),
            ("Sellos discográficos", "SELECT COUNT(*) FROM labels")
        ]
        
        for label, query in queries:
            cursor = conn.execute(query)
            count = cursor.fetchone()[0]
            stats.append(f"{label}: {count}")
        
        print("Estadísticas generales:")
        print("  " + ", ".join(stats))
        
        # Top 5 artistas con más canciones
        query = """
        SELECT artist, COUNT(*) as count 
        FROM songs 
        GROUP BY artist 
        ORDER BY count DESC 
        LIMIT 5
        """
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        
        print("\nTop 5 artistas con más canciones:")
        for i, row in enumerate(rows, 1):
            print(f"  {i}. {row[0]}: {row[1]} canciones")
        
        # Top 5 géneros
        query = """
        SELECT genre, COUNT(*) as count 
        FROM songs 
        WHERE genre IS NOT NULL AND genre != '' 
        GROUP BY genre 
        ORDER BY count DESC 
        LIMIT 5
        """
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        
        print("\nTop 5 géneros más comunes:")
        for i, row in enumerate(rows, 1):
            print(f"  {i}. {row[0]}: {row[1]} canciones")
        
        # Distribución de bitrates
        query = """
        SELECT 
            COUNT(CASE WHEN bitrate < 128 THEN 1 END) as low,
            COUNT(CASE WHEN bitrate >= 128 AND bitrate < 192 THEN 1 END) as medium,
            COUNT(CASE WHEN bitrate >= 192 AND bitrate < 256 THEN 1 END) as high,
            COUNT(CASE WHEN bitrate >= 256 AND bitrate < 320 THEN 1 END) as very_high,
            COUNT(CASE WHEN bitrate >= 320 THEN 1 END) as lossless,
            COUNT(CASE WHEN bitrate IS NULL OR bitrate = 0 THEN 1 END) as unknown
        FROM songs
        """
        cursor = conn.execute(query)
        row = cursor.fetchone()
        
        print("\nDistribución de bitrates:")
        print(f"  Bajo (<128kbps): {row[0]}")
        print(f"  Medio (128-191kbps): {row[1]}")
        print(f"  Alto (192-255kbps): {row[2]}")
        print(f"  Muy alto (256-319kbps): {row[3]}")
        print(f"  Lossless (>=320kbps): {row[4]}")
        print(f"  Desconocido: {row[5]}")

def main():
    parser = argparse.ArgumentParser(description='Verificador de inconsistencias en base de datos de música')
    parser.add_argument('--db-path', help='Ruta al archivo de base de datos SQLite')
    parser.add_argument('--all', action='store_true', help='Ejecutar todas las verificaciones')
    parser.add_argument('--missing', action='store_true', help='Verificar valores faltantes')
    parser.add_argument('--orphans', action='store_true', help='Verificar registros huérfanos')
    parser.add_argument('--duplicates', action='store_true', help='Verificar registros duplicados')
    parser.add_argument('--metadata', action='store_true', help='Verificar inconsistencias en metadatos')
    parser.add_argument('--technical', action='store_true', help='Verificar problemas técnicos')
    parser.add_argument('--paths', action='store_true', help='Verificar problemas con rutas de archivos')
    parser.add_argument('--mbid', action='store_true', help='Verificar problemas con MusicBrainz IDs')
    parser.add_argument('--summary', action='store_true', help='Generar resumen de la base de datos')
    parser.add_argument('--limit', type=int, default=100, help='Límite de resultados por consulta (predeterminado: 100)')
    parser.add_argument('--output', help='Ruta para guardar el reporte en un archivo')
    args = parser.parse_args()
    
    # Si no se especifica ninguna verificación, ejecutar todas
    if not (args.all or args.missing or args.orphans or args.duplicates or args.metadata or 
            args.technical or args.paths or args.mbid or args.summary):
        args.all = True
    
    try:
        print(f"Conectando a la base de datos: {args.db_path}")
        conn = connect_to_db(args.db_path)
        
        # Redirigir la salida a un archivo si se especifica
        original_stdout = None
        if args.output:
            original_stdout = sys.stdout
            sys.stdout = open(args.output, 'w', encoding='utf-8')
        
        print("=== Informe de inconsistencias en la base de datos ===")
        print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base de datos: {args.db_path}")
        
        # Ejecutar verificaciones
        check_missing_values(conn, args)
        check_orphan_records(conn, args)
        check_duplicates(conn, args)
        check_inconsistent_metadata(conn, args)
        check_technical_issues(conn, args)
        check_path_issues(conn, args)
        check_mbid_issues(conn, args)
        generate_summary(conn, args)
        
        # Cerrar la conexión
        conn.close()
        
        # Restaurar la salida estándar si fue redirigida
        if args.output:
            sys.stdout.close()
            sys.stdout = original_stdout
            print(f"Informe guardado en: {args.output}")
        
        print("\nVerificación completada.")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())