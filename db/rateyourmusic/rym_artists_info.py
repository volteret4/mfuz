#!/usr/bin/env python3
"""
Script para extraer información detallada de artistas desde RateYourMusic
Utiliza nodriver para web scraping y actualiza la tabla rym_artists
"""

import asyncio
import sqlite3
import re
import json
from datetime import datetime
from pathlib import Path
import nodriver as uc
from urllib.parse import urljoin, urlparse

# Variables globales para configuración
CONFIG = {}

def setup_database(db_path):
    """Configura la base de datos añadiendo las columnas necesarias a rym_artists"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Obtener estructura actual de la tabla
    cursor.execute("PRAGMA table_info(rym_artists)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    # Definir nuevas columnas necesarias
    new_columns = [
        ('birth_date', 'TEXT'),
        ('birth_place', 'TEXT'),
        ('death_date', 'TEXT'),
        ('death_place', 'TEXT'),
        ('notes', 'TEXT'),
        ('also_known_as', 'TEXT'),
        ('genres', 'TEXT'),
        ('top_songs', 'TEXT'),  # JSON con canciones populares
        ('biography', 'TEXT'),
        ('info_updated', 'TIMESTAMP'),
        ('scraping_status', 'TEXT DEFAULT "pending"'),
        ('error_message', 'TEXT')
    ]
    
    # Añadir columnas que no existan
    for column_name, column_type in new_columns:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE rym_artists ADD COLUMN {column_name} {column_type}")
                print(f"✓ Añadida columna: {column_name}")
            except sqlite3.Error as e:
                print(f"Error añadiendo columna {column_name}: {e}")
    
    conn.commit()
    conn.close()

def get_artists_to_process(db_path, limit=None):
    """Obtiene lista de artistas para procesar desde rym_artists"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Buscar artistas con URLs que no han sido procesados o necesitan actualización
    query = """
    SELECT id, artist_id, artist_name, rym_url 
    FROM rym_artists 
    WHERE rym_url IS NOT NULL 
    AND rym_url != ''
    AND (scraping_status IS NULL OR scraping_status = 'pending' OR scraping_status = 'error')
    ORDER BY id
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    artists = cursor.fetchall()
    conn.close()
    
    return artists

def parse_date_info(text):
    """Extrae fecha y lugar de texto como 'Nacido en 26 May 1926, Alton, IL, United States'"""
    if not text:
        return None, None
    
    # Patrón para fechas como "26 May 1926, Alton, IL, United States"
    date_pattern = r'(\d{1,2}\s+\w+\s+\d{4})'
    date_match = re.search(date_pattern, text)
    
    date = date_match.group(1) if date_match else None
    
    # El lugar es lo que viene después de la fecha
    if date:
        place = text.split(date, 1)[1].strip().lstrip(',').strip()
    else:
        place = text.strip()
    
    return date, place

def clean_text(text):
    """Limpia texto eliminando espacios extra y caracteres especiales"""
    if not text:
        return None
    return ' '.join(text.split()).strip()

async def scrape_artist_info(browser, rym_url):
    """Extrae información detallada de un artista desde su página de RYM"""
    try:
        print(f"Accediendo a: {rym_url}")
        page = await browser.get(rym_url)
        
        # Esperar a que la página cargue
        await asyncio.sleep(2)
        
        artist_info = {
            'birth_date': None,
            'birth_place': None,
            'death_date': None,
            'death_place': None,
            'notes': None,
            'also_known_as': None,
            'genres': None,
            'top_songs': None,
            'biography': None
        }
        
        # Extraer información básica (INFO section)
        try:
            # Buscar sección de información básica
            info_section = await page.select('.info_hdr')
            if info_section:
                info_content = await page.select('.info_content')
                
                for content in info_content:
                    text = await content.get_text()
                    
                    if 'Nacido en' in text or 'Born' in text:
                        birth_info = text.replace('Nacido en', '').replace('Born', '').strip()
                        artist_info['birth_date'], artist_info['birth_place'] = parse_date_info(birth_info)
                    
                    elif 'Fallecido en' in text or 'Died' in text:
                        death_info = text.replace('Fallecido en', '').replace('Died', '').strip()
                        artist_info['death_date'], artist_info['death_place'] = parse_date_info(death_info)
                    
                    elif 'Notas' in text or 'Notes' in text:
                        artist_info['notes'] = clean_text(text.replace('Notas', '').replace('Notes', ''))
                    
                    elif 'También conocido como' in text or 'Also known as' in text:
                        aka_text = text.replace('También conocido como', '').replace('Also known as', '')
                        artist_info['also_known_as'] = clean_text(aka_text)
        
        except Exception as e:
            print(f"Error extrayendo info básica: {e}")
        
        # Extraer géneros
        try:
            genre_links = await page.select('.genre > a')
            if genre_links:
                genres = []
                for link in genre_links:
                    genre_text = await link.get_text()
                    if genre_text:
                        genres.append(genre_text.strip())
                artist_info['genres'] = ', '.join(genres) if genres else None
        
        except Exception as e:
            print(f"Error extrayendo géneros: {e}")
        
        # Extraer top songs
        try:
            songs_data = []
            song_rows = await page.select('.chart_item')
            
            for row in song_rows[:15]:  # Top 15 canciones
                try:
                    # Título de la canción
                    title_elem = await row.select('.chart_item_name a')
                    title = await title_elem[0].get_text() if title_elem else None
                    
                    # Rating
                    rating_elem = await row.select('.chart_item_rating')
                    rating = await rating_elem[0].get_text() if rating_elem else None
                    
                    # Número de ratings
                    count_elem = await row.select('.chart_item_count')
                    count = await count_elem[0].get_text() if count_elem else None
                    
                    if title:
                        song_data = {
                            'title': clean_text(title),
                            'rating': clean_text(rating),
                            'count': clean_text(count)
                        }
                        songs_data.append(song_data)
                
                except Exception as e:
                    print(f"Error procesando canción: {e}")
                    continue
            
            if songs_data:
                artist_info['top_songs'] = json.dumps(songs_data, ensure_ascii=False)
        
        except Exception as e:
            print(f"Error extrayendo canciones: {e}")
        
        # Extraer biografía
        try:
            bio_section = await page.select('.artist_info_brief')
            if bio_section:
                bio_text = await bio_section[0].get_text()
                artist_info['biography'] = clean_text(bio_text)
        
        except Exception as e:
            print(f"Error extrayendo biografía: {e}")
        
        return artist_info
    
    except Exception as e:
        print(f"Error general en scraping: {e}")
        return None

def update_artist_info(db_path, artist_id, artist_info, status='completed'):
    """Actualiza la información del artista en la base de datos"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        update_query = """
        UPDATE rym_artists SET
            birth_date = ?,
            birth_place = ?,
            death_date = ?,
            death_place = ?,
            notes = ?,
            also_known_as = ?,
            genres = ?,
            top_songs = ?,
            biography = ?,
            info_updated = ?,
            scraping_status = ?,
            error_message = NULL
        WHERE id = ?
        """
        
        cursor.execute(update_query, (
            artist_info['birth_date'],
            artist_info['birth_place'],
            artist_info['death_date'],
            artist_info['death_place'],
            artist_info['notes'],
            artist_info['also_known_as'],
            artist_info['genres'],
            artist_info['top_songs'],
            artist_info['biography'],
            datetime.now().isoformat(),
            status,
            artist_id
        ))
        
        conn.commit()
        print(f"✓ Actualizado artista ID {artist_id}")
    
    except Exception as e:
        print(f"Error actualizando base de datos: {e}")
    
    finally:
        conn.close()

def update_artist_error(db_path, artist_id, error_message):
    """Marca un artista como error en la base de datos"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE rym_artists SET
            scraping_status = 'error',
            error_message = ?,
            info_updated = ?
        WHERE id = ?
    """, (error_message, datetime.now().isoformat(), artist_id))
    
    conn.commit()
    conn.close()

async def process_artists(config):
    """Función principal para procesar artistas"""
    db_path = config.get('db_path')
    limit = config.get('limit', None)
    delay = config.get('delay', 2.0)
    
    if not db_path:
        print("Error: db_path no especificado en configuración")
        return
    
    print("Configurando base de datos...")
    setup_database(db_path)
    
    print("Obteniendo lista de artistas...")
    artists = get_artists_to_process(db_path, limit)
    
    if not artists:
        print("No hay artistas para procesar")
        return
    
    print(f"Procesando {len(artists)} artistas...")
    
    # Configurar browser
    browser = await uc.start(headless=True)
    
    try:
        for i, (row_id, artist_id, artist_name, rym_url) in enumerate(artists, 1):
            print(f"\n[{i}/{len(artists)}] Procesando: {artist_name}")
            
            try:
                # Extraer información
                artist_info = await scrape_artist_info(browser, rym_url)
                
                if artist_info:
                    # Actualizar base de datos
                    update_artist_info(db_path, row_id, artist_info)
                else:
                    update_artist_error(db_path, row_id, "No se pudo extraer información")
                
                # Delay entre requests
                if i < len(artists):
                    print(f"Esperando {delay} segundos...")
                    await asyncio.sleep(delay)
            
            except Exception as e:
                error_msg = f"Error procesando artista: {str(e)}"
                print(f"❌ {error_msg}")
                update_artist_error(db_path, row_id, error_msg)
                continue
    
    finally:
        await browser.stop()

def main(config=None):
    """Función principal del script"""
    global CONFIG
    
    if config:
        CONFIG.update(config)
    
    # Configuración por defecto
    default_config = {
        'delay': 2.0,
        'limit': None,
        'headless': True
    }
    
    for key, value in default_config.items():
        if key not in CONFIG:
            CONFIG[key] = value
    
    print("=== RateYourMusic Artist Info Scraper ===")
    print(f"Base de datos: {CONFIG.get('db_path', 'No especificada')}")
    print(f"Límite: {CONFIG.get('limit', 'Sin límite')}")
    print(f"Delay: {CONFIG.get('delay')} segundos")
    
    # Ejecutar proceso asíncrono
    asyncio.run(process_artists(CONFIG))
    
    print("\n✅ Proceso completado")

if __name__ == "__main__":
    main()