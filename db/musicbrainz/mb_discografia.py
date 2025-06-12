#!/usr/bin/env python3
"""
Script para obtener la discografía completa de artistas desde MusicBrainz
Busca primero por MBID, luego por nombre de artista
Compatible con db_creator.py
"""

import sqlite3
import requests
import time
import json
from pathlib import Path
from datetime import datetime
import sys
import os


# Configuración de la API de MusicBrainz
MB_BASE_URL = "https://musicbrainz.org/ws/2"
USER_AGENT = "MusicDiscoveryApp/1.0 (https://github.com/yourusername/musicapp)"
RATE_LIMIT_DELAY = 1.0  # Segundos entre requests (MusicBrainz recomienda mínimo 1 segundo)

def setup_database(db_path):
    """Crea la tabla musicbrainz_discography si no existe"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS musicbrainz_discography (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER NOT NULL,
            album_id INTEGER,
            discogs_discography_id INTEGER,
            mbid TEXT NOT NULL,
            title TEXT NOT NULL,
            release_type TEXT,
            first_release_date TEXT,
            secondary_types TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists (id),
            FOREIGN KEY (album_id) REFERENCES albums (id),
            FOREIGN KEY (discogs_discography_id) REFERENCES discogs_discography (id),
            UNIQUE(artist_id, mbid)
        )
    """)
    
    # Índices para mejorar rendimiento
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mb_discography_artist ON musicbrainz_discography(artist_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mb_discography_mbid ON musicbrainz_discography(mbid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mb_discography_album ON musicbrainz_discography(album_id)")
    
    conn.commit()
    conn.close()

def make_mb_request(endpoint, params=None):
    """Realiza una petición a la API de MusicBrainz con rate limiting respetuoso"""
    if params is None:
        params = {}
    
    params['fmt'] = 'json'
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json'
    }
    
    url = f"{MB_BASE_URL}/{endpoint}"
    
    try:
        # Rate limiting ANTES de la petición para ser más respetuosos
        time.sleep(RATE_LIMIT_DELAY)
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error en petición MusicBrainz: {e}")
        return None

def search_artist_by_name(artist_name):
    """Busca un artista en MusicBrainz por nombre"""
    params = {
        'query': f'artist:"{artist_name}"',
        'limit': 5
    }
    
    result = make_mb_request('artist', params)
    if not result or 'artists' not in result:
        return None
    
    # Buscar coincidencia exacta primero
    for artist in result['artists']:
        if artist['name'].lower() == artist_name.lower():
            return artist['id']
    
    # Si no hay coincidencia exacta, tomar el primer resultado con alta puntuación
    if result['artists'] and result['artists'][0].get('score', 0) > 95:
        return result['artists'][0]['id']
    
    return None

def get_artist_release_groups(artist_mbid):
    """Obtiene todos los release groups de un artista con manejo de errores mejorado"""
    params = {
        'artist': artist_mbid,
        'limit': 100,
        'offset': 0
    }
    
    all_release_groups = []
    total_expected = None
    
    while True:
        result = make_mb_request('release-group', params)
        if not result or 'release-groups' not in result:
            # Si falló la petición, retornamos None para indicar error
            print(f"  Error: Falló la petición en offset {params['offset']}")
            return None
        
        release_groups = result['release-groups']
        all_release_groups.extend(release_groups)
        
        # En la primera página, obtenemos el total esperado
        if total_expected is None:
            total_expected = result.get('release-group-count', len(release_groups))
            print(f"  Total esperado: {total_expected} release groups")
        
        # Verificar si hay más páginas
        if len(release_groups) < params['limit']:
            break
        
        params['offset'] += params['limit']
        page_num = params['offset'] // params['limit']
        print(f"  Obteniendo página {page_num}... ({len(all_release_groups)}/{total_expected})")
    
    # Verificar si obtuvimos todos los datos esperados
    if total_expected and len(all_release_groups) < total_expected:
        print(f"  Advertencia: Se esperaban {total_expected} pero solo se obtuvieron {len(all_release_groups)}")
        # Si falta más del 10% de los datos, considerarlo como fallo
        if len(all_release_groups) < (total_expected * 0.9):
            print(f"  Error: Datos incompletos, se considera fallo")
            return None
    
    return all_release_groups

def find_matching_album(title, artist_id, conn):
    """Busca un álbum local que coincida con el release group"""
    cursor = conn.cursor()
    
    # Búsqueda exacta primero
    cursor.execute("""
        SELECT id FROM albums 
        WHERE artist_id = ? AND LOWER(name) = LOWER(?)
    """, (artist_id, title))
    
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Búsqueda difusa (sin acentos, caracteres especiales)
    import re
    normalized_title = re.sub(r'[^\w\s]', '', title.lower())
    
    cursor.execute("""
        SELECT id, name FROM albums WHERE artist_id = ?
    """, (artist_id,))
    
    albums = cursor.fetchall()
    for album_id, album_name in albums:
        normalized_album = re.sub(r'[^\w\s]', '', album_name.lower())
        if normalized_album == normalized_title:
            return album_id
    
    return None

def find_matching_discogs(title, artist_id, conn):
    """Busca en discogs_discography un álbum que coincida"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM discogs_discography 
        WHERE artist_id = ? AND LOWER(album_name) = LOWER(?)
    """, (artist_id, title))
    
    result = cursor.fetchone()
    return result[0] if result else None

def clean_duplicates(conn):
    """Elimina duplicados basados en artist_id y mbid, manteniendo el más reciente"""
    cursor = conn.cursor()
    
    # Encontrar duplicados
    cursor.execute("""
        SELECT artist_id, mbid, COUNT(*) as count
        FROM musicbrainz_discography 
        WHERE title != '__PROCESSING_COMPLETE__'
        GROUP BY artist_id, mbid 
        HAVING COUNT(*) > 1
    """)
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("No se encontraron duplicados")
        return
    
    print(f"Encontrados {len(duplicates)} grupos de duplicados")
    
    for artist_id, mbid, count in duplicates:
        # Mantener solo el más reciente
        cursor.execute("""
            DELETE FROM musicbrainz_discography 
            WHERE artist_id = ? AND mbid = ? AND id NOT IN (
                SELECT id FROM musicbrainz_discography 
                WHERE artist_id = ? AND mbid = ? 
                ORDER BY last_updated DESC 
                LIMIT 1
            )
        """, (artist_id, mbid, artist_id, mbid))
        
        deleted = cursor.rowcount
        print(f"  Eliminados {deleted} duplicados para artist_id={artist_id}, mbid={mbid}")
    
    conn.commit()


def process_artist_discography(artist_id, artist_name, artist_mbid, conn, force_update=False):
    """Procesa la discografía de un artista específico"""
    cursor = conn.cursor()
    
    # Verificar si ya tenemos datos COMPLETOS de este artista
    if not force_update:
        cursor.execute("""
            SELECT 1 FROM musicbrainz_discography 
            WHERE artist_id = ? AND title = '__PROCESSING_COMPLETE__'
        """, (artist_id,))
        
        if cursor.fetchone():
            print(f"  Artista {artist_name} ya procesado completamente, saltando...")
            return True
    
    # Determinar MBID del artista
    mb_artist_id = artist_mbid
    
    if not mb_artist_id:
        print(f"  Buscando MBID para: {artist_name}")
        mb_artist_id = search_artist_by_name(artist_name)
        
        if not mb_artist_id:
            print(f"  No se encontró en MusicBrainz: {artist_name}")
            return False
    
    print(f"  Obteniendo discografía para: {artist_name} (MBID: {mb_artist_id})")
    
    # Obtener release groups con manejo de errores
    release_groups = get_artist_release_groups(mb_artist_id)
    
    if release_groups is None:
        print(f"  ERROR: Falló la obtención de datos para {artist_name}, no se marca como procesado")
        return False
    
    if not release_groups:
        print(f"  No se encontraron release groups para: {artist_name}")
        # Marcar como procesado aunque no tenga release groups
        cursor.execute("""
            INSERT OR REPLACE INTO musicbrainz_discography 
            (artist_id, album_id, discogs_discography_id, mbid, title, 
             release_type, first_release_date, secondary_types, last_updated)
            VALUES (?, NULL, NULL, ?, ?, NULL, NULL, NULL, CURRENT_TIMESTAMP)
        """, (artist_id, 'no-releases', '__PROCESSING_COMPLETE__'))
        conn.commit()
        return True
    
    print(f"  Encontrados {len(release_groups)} release groups")
    
    # Obtener MBIDs ya existentes para este artista
    cursor.execute("""
        SELECT mbid FROM musicbrainz_discography 
        WHERE artist_id = ? AND title != '__PROCESSING_COMPLETE__'
    """, (artist_id,))
    existing_mbids = {row[0] for row in cursor.fetchall()}
    
    # Procesar cada release group
    processed = 0
    failed = 0
    new_releases = 0
    
    for rg in release_groups:
        try:
            title = rg.get('title', '')
            mbid = rg.get('id', '')
            primary_type = rg.get('primary-type', '')
            secondary_types = ', '.join(rg.get('secondary-types', []))
            first_release_date = rg.get('first-release-date', '')
            
            # Solo procesar si no existe ya
            if mbid in existing_mbids:
                processed += 1
                continue
            
            # Buscar coincidencias en tablas locales
            album_id = find_matching_album(title, artist_id, conn)
            discogs_id = find_matching_discogs(title, artist_id, conn)
            
            # Insertar nuevo release
            cursor.execute("""
                INSERT INTO musicbrainz_discography 
                (artist_id, album_id, discogs_discography_id, mbid, title, 
                 release_type, first_release_date, secondary_types, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (artist_id, album_id, discogs_id, mbid, title, 
                  primary_type, first_release_date, secondary_types))
            
            processed += 1
            new_releases += 1
            
        except Exception as e:
            print(f"    Error procesando release group {rg.get('title', 'Unknown')}: {e}")
            failed += 1
            continue
    
    # Solo marcar como completado si se procesaron exitosamente todos o la mayoría
    if failed == 0 or (processed > 0 and failed / (processed + failed) < 0.1):
        # Eliminar marca anterior de procesamiento completo si existe
        cursor.execute("""
            DELETE FROM musicbrainz_discography 
            WHERE artist_id = ? AND title = '__PROCESSING_COMPLETE__'
        """, (artist_id,))
        
        # Insertar nueva marca de procesamiento completo
        cursor.execute("""
            INSERT INTO musicbrainz_discography 
            (artist_id, album_id, discogs_discography_id, mbid, title, 
             release_type, first_release_date, secondary_types, last_updated)
            VALUES (?, NULL, NULL, ?, ?, NULL, NULL, NULL, CURRENT_TIMESTAMP)
        """, (artist_id, 'processing-complete', '__PROCESSING_COMPLETE__'))
        
        conn.commit()
        print(f"  Procesados {processed} release groups para {artist_name} ({new_releases} nuevos)")
        return True
    else:
        # No marcar como completo si hubo muchos errores
        conn.rollback()
        print(f"  ERROR: Demasiados fallos ({failed}) procesando {artist_name}, no se guarda")
        return False

def get_artists_to_process(conn, artist_limit=None, skip_artists=None):
    """Obtiene la lista de artistas a procesar, excluyendo los especificados"""
    cursor = conn.cursor()
    
    # Lista por defecto de artistas a omitir si no se especifica
    if skip_artists is None:
        skip_artists = [
            'varios artistas',
            'various artists', 
            'varios',
            'various',
            'compilation',
            'v.a.',
            'v/a',
            'soundtrack'
        ]
    
    # Crear placeholders para la consulta SQL
    placeholders = ','.join(['?' for _ in skip_artists])
    
    query = f"""
        SELECT a.id, a.name, a.mbid 
        FROM artists a
        WHERE LOWER(a.name) NOT IN ({placeholders})
        AND a.name IS NOT NULL
        AND TRIM(a.name) != ''
        ORDER BY a.id
    """
    
    if artist_limit:
        query += f" LIMIT {artist_limit}"
    
    # Convertir skip_artists a minúsculas para la comparación
    skip_artists_lower = [artist.lower() for artist in skip_artists]
    cursor.execute(query, skip_artists_lower)
    return cursor.fetchall()

def main(config=None):
    """Función principal"""
    if config is None:
        config = {}
    
    # Configuración por defecto
    db_path = config.get('db_path', 'music_database.db')
    force_update = config.get('force_update', False)
    artist_limit = config.get('artist_limit', None)
    interactive = config.get('interactive', True)
    clean_existing_duplicates = config.get('clean_duplicates', True)
    
    # Nueva configuración para artistas a omitir
    skip_artists = config.get('skip_artists', [
        'varios artistas',
        'various artists', 
        'varios',
        'various',
        'compilation',
        'v.a.',
        'v/a',
        'soundtrack'
    ])
    
    print("=== MusicBrainz Discography Fetcher ===")
    print(f"Base de datos: {db_path}")
    print(f"Force update: {force_update}")
    print(f"Límite de artistas: {artist_limit or 'Sin límite'}")
    print(f"Artistas a omitir: {', '.join(skip_artists)}")
    
    # Verificar que existe la base de datos
    if not os.path.exists(db_path):
        print(f"Error: No se encuentra la base de datos: {db_path}")
        return 1
    
    # Configurar base de datos
    setup_database(db_path)
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    
    try:
        # Limpiar duplicados existentes si se solicita
        if clean_existing_duplicates:
            print("\n=== Limpiando duplicados existentes ===")
            clean_duplicates(conn)
        
        # Obtener artistas (ahora con filtro)
        artists = get_artists_to_process(conn, artist_limit, skip_artists)
        total_artists = len(artists)
        
        print(f"\nEncontrados {total_artists} artistas para procesar (después de filtros)")
        
        # Procesar cada artista
        success_count = 0
        for i, (artist_id, artist_name, artist_mbid) in enumerate(artists, 1):
            print(f"\n[{i}/{total_artists}] Procesando: {artist_name}")
            
            try:
                if process_artist_discography(artist_id, artist_name, artist_mbid, conn, force_update):
                    success_count += 1
                    
            except KeyboardInterrupt:
                print("\nInterrumpido por el usuario")
                break
            except Exception as e:
                print(f"Error procesando {artist_name}: {e}")
                continue
        
        print(f"\n=== Resumen ===")
        print(f"Artistas procesados exitosamente: {success_count}/{total_artists}")
        
        # Estadísticas finales
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM musicbrainz_discography 
            WHERE title != '__PROCESSING_COMPLETE__'
        """)
        total_releases = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT release_type, COUNT(*) 
            FROM musicbrainz_discography 
            WHERE release_type IS NOT NULL AND title != '__PROCESSING_COMPLETE__'
            GROUP BY release_type 
            ORDER BY COUNT(*) DESC
        """)
        
        print(f"Total de release groups obtenidos: {total_releases}")
        print("\nDistribución por tipo:")
        for release_type, count in cursor.fetchall():
            print(f"  {release_type}: {count}")
        
        # Mostrar artistas con procesamiento incompleto
        cursor.execute("""
            SELECT a.name, COUNT(md.id) 
            FROM artists a
            LEFT JOIN musicbrainz_discography md ON a.id = md.artist_id 
                AND md.title != '__PROCESSING_COMPLETE__'
            WHERE a.id NOT IN (
                SELECT artist_id FROM musicbrainz_discography 
                WHERE title = '__PROCESSING_COMPLETE__'
            )
            GROUP BY a.id, a.name
            HAVING COUNT(md.id) > 0
            ORDER BY COUNT(md.id) DESC
            LIMIT 10
        """)
        
        incomplete = cursor.fetchall()
        if incomplete:
            print(f"\nArtistas con procesamiento incompleto:")
            for artist_name, count in incomplete:
                print(f"  {artist_name}: {count} releases (incompleto)")

        
    finally:
        conn.close()
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())