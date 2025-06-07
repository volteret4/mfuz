#!/usr/bin/env python3
"""
Script para buscar referencias a artistas de la base de datos en archivos EPUB
Compatible con db_creator.py
"""

import os
import sqlite3
import re
from pathlib import Path
from datetime import datetime
import zipfile
import xml.etree.ElementTree as ET
from html import unescape
import argparse
from base_module import BaseModule

def extract_text_from_epub(epub_path):
    """
    Extrae el texto de un archivo EPUB
    Retorna un diccionario con metadatos y contenido
    """
    try:
        with zipfile.ZipFile(epub_path, 'r') as zip_file:
            # Buscar el archivo OPF (Open Packaging Format)
            container_path = 'META-INF/container.xml'
            if container_path not in zip_file.namelist():
                return None
            
            container_content = zip_file.read(container_path)
            container_root = ET.fromstring(container_content)
            
            # Obtener la ruta del archivo OPF
            opf_path = None
            for rootfile in container_root.findall('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile'):
                opf_path = rootfile.get('full-path')
                break
            
            if not opf_path:
                return None
            
            # Leer el archivo OPF para obtener metadatos y orden de archivos
            opf_content = zip_file.read(opf_path)
            opf_root = ET.fromstring(opf_content)
            
            # Extraer metadatos
            metadata = {}
            ns = {'dc': 'http://purl.org/dc/elements/1.1/', 'opf': 'http://www.idpf.org/2007/opf'}
            
            title_elem = opf_root.find('.//dc:title', ns)
            metadata['title'] = title_elem.text if title_elem is not None else os.path.basename(epub_path)
            
            creator_elem = opf_root.find('.//dc:creator', ns)
            metadata['author'] = creator_elem.text if creator_elem is not None else 'Desconocido'
            
            subject_elem = opf_root.find('.//dc:subject', ns)
            metadata['genre'] = subject_elem.text if subject_elem is not None else 'Sin género'
            
            # Obtener archivos de contenido en orden
            spine_items = []
            for itemref in opf_root.findall('.//opf:itemref', ns):
                idref = itemref.get('idref')
                for item in opf_root.findall('.//opf:item', ns):
                    if item.get('id') == idref and item.get('media-type') == 'application/xhtml+xml':
                        spine_items.append(item.get('href'))
                        break
            
            # Extraer texto de cada archivo XHTML
            full_text = ""
            opf_dir = os.path.dirname(opf_path)
            
            for spine_item in spine_items:
                file_path = os.path.join(opf_dir, spine_item) if opf_dir else spine_item
                if file_path in zip_file.namelist():
                    try:
                        content = zip_file.read(file_path).decode('utf-8')
                        # Parsear XHTML y extraer texto
                        text = extract_text_from_xhtml(content)
                        full_text += text + "\n"
                    except Exception as e:
                        print(f"Error procesando {file_path}: {e}")
                        continue
            
            # Calcular estadísticas
            char_count = len(full_text)
            # Estimación aproximada de páginas (250 palabras por página)
            word_count = len(full_text.split())
            page_estimate = max(1, word_count // 250)
            
            return {
                'title': metadata['title'],
                'author': metadata['author'],
                'genre': metadata['genre'],
                'content': full_text,
                'char_count': char_count,
                'page_estimate': page_estimate
            }
            
    except Exception as e:
        print(f"Error procesando EPUB {epub_path}: {e}")
        return None

def extract_text_from_xhtml(xhtml_content):
    """Extrae texto plano de contenido XHTML"""
    try:
        # Eliminar namespaces para simplificar el parsing
        clean_content = re.sub(r'xmlns[^=]*="[^"]*"', '', xhtml_content)
        root = ET.fromstring(clean_content)
        
        # Extraer todo el texto
        text_parts = []
        for elem in root.iter():
            if elem.text:
                text_parts.append(elem.text.strip())
            if elem.tail:
                text_parts.append(elem.tail.strip())
        
        text = ' '.join(filter(None, text_parts))
        return unescape(text)
        
    except ET.ParseError:
        # Si falla el parsing XML, usar regex para extraer texto
        text = re.sub(r'<[^>]+>', ' ', xhtml_content)
        text = unescape(text)
        return ' '.join(text.split())

def get_artists_from_db(db_path):
    """Obtiene la lista de artistas de la base de datos, excluyendo nombres problemáticos"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM artists WHERE name IS NOT NULL AND name != ''")
    all_artists = cursor.fetchall()
    
    conn.close()
    
    # Filtrar artistas problemáticos
    special_artists = get_special_artists_list()
    filtered_artists = [(artist_id, name) for artist_id, name in all_artists 
                       if name.lower() not in special_artists]
    
    print(f"Artistas totales: {len(all_artists)}, después de filtrar: {len(filtered_artists)}")
    if len(all_artists) != len(filtered_artists):
        excluded = len(all_artists) - len(filtered_artists)
        print(f"Excluidos {excluded} artistas con nombres problemáticos")
    
    return filtered_artists


def create_artists_books_table(db_path):
    """Crea la tabla artists_books si no existe"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS artists_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER NOT NULL,
            book_title TEXT NOT NULL,
            book_author TEXT,
            genre TEXT,
            filename TEXT NOT NULL,
            page_count INTEGER,
            char_count INTEGER,
            content TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists (id)
        )
    ''')
    
    # Crear índices para mejorar el rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_artists_books_artist_id ON artists_books(artist_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_artists_books_filename ON artists_books(filename)')
    
    conn.commit()
    conn.close()

def find_artist_references(text, artist_name, min_context=100, max_context=500, case_sensitive=False):
    """
    Busca referencias al artista en el texto y extrae el contexto
    Retorna una lista de párrafos que contienen menciones
    Busca palabras completas, no subcadenas
    Mejorado para detectar separaciones de párrafos correctamente
    """
    # Crear patrón regex para palabras completas
    pattern_flags = re.IGNORECASE if not case_sensitive else 0
    escaped_name = re.escape(artist_name)
    pattern = r'\b' + escaped_name + r'\b'
    
    references = []
    
    # Buscar todas las coincidencias
    for match in re.finditer(pattern, text, pattern_flags):
        pos = match.start()
        
        # Buscar el inicio del párrafo
        context_start = pos
        # Buscar hacia atrás hasta encontrar separador de párrafo o límite
        while context_start > 0 and context_start > pos - max_context:
            # Buscar separadores: ". " seguido de mayúscula, ".\n", ".\r\n", o saltos de línea múltiples
            char = text[context_start]
            if char in '\n\r':
                # Verificar si hay múltiples saltos de línea (separación de párrafo)
                line_breaks = 0
                temp_pos = context_start
                while temp_pos >= 0 and text[temp_pos] in '\n\r\t ':
                    if text[temp_pos] in '\n\r':
                        line_breaks += 1
                    temp_pos -= 1
                if line_breaks >= 2 or context_start == 0:
                    context_start += 1
                    break
            elif context_start > 1 and text[context_start-1:context_start+1] == '. ':
                # Verificar si después del punto y espacio hay mayúscula (nueva oración)
                if context_start + 1 < len(text) and text[context_start + 1].isupper():
                    break
            context_start -= 1
        
        # Buscar el final del párrafo
        context_end = pos + len(artist_name)
        while context_end < len(text) and context_end < pos + len(artist_name) + max_context:
            char = text[context_end]
            if char in '\n\r':
                # Verificar si hay múltiples saltos de línea (separación de párrafo)
                line_breaks = 0
                temp_pos = context_end
                while temp_pos < len(text) and text[temp_pos] in '\n\r\t ':
                    if text[temp_pos] in '\n\r':
                        line_breaks += 1
                    temp_pos += 1
                if line_breaks >= 2:
                    break
            elif context_end > 0 and text[context_end-1:context_end+1] == '. ':
                # Verificar si después del punto y espacio hay mayúscula (nueva oración)
                if context_end + 1 < len(text) and text[context_end + 1].isupper():
                    context_end -= 1  # Incluir el punto pero no el espacio
                    break
            context_end += 1
        
        # Extraer y limpiar el contexto
        context = text[context_start:context_end].strip()
        
        # Limpiar espacios múltiples y saltos de línea dentro del párrafo
        context = re.sub(r'\s+', ' ', context)
        
        # Verificar que el contexto tenga un tamaño mínimo
        if len(context) < min_context:
            continue
        
        # Evitar duplicados muy similares
        if not any(abs(len(context) - len(ref)) < 50 and context[:100] == ref[:100] 
                  for ref in references):
            references.append(context)
    
    return references


# Modificaciones para epubs.py

def get_artists_from_db(db_path):
    """Obtiene la lista de artistas de la base de datos, excluyendo nombres problemáticos"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM artists WHERE name IS NOT NULL AND name != ''")
    all_artists = cursor.fetchall()
    
    conn.close()
    
    # Filtrar artistas problemáticos
    special_artists = get_special_artists_list()
    filtered_artists = [(artist_id, name) for artist_id, name in all_artists 
                       if name.lower() not in special_artists]
    
    print(f"Artistas totales: {len(all_artists)}, después de filtrar: {len(filtered_artists)}")
    if len(all_artists) != len(filtered_artists):
        excluded = len(all_artists) - len(filtered_artists)
        print(f"Excluidos {excluded} artistas con nombres problemáticos")
    
    return filtered_artists

def process_epub_files(config):
    """Procesa todos los archivos EPUB en la carpeta especificada"""
    db_path = config['db_path']
    epub_folder = config['epub_folder']
    force_update = config.get('force_update', False)
    
    if not os.path.exists(epub_folder):
        print(f"Error: La carpeta {epub_folder} no existe")
        return
    
    # Crear tabla si no existe
    create_artists_books_table(db_path)
    
    # Obtener artistas de la base de datos (ya filtrados)
    print("Obteniendo lista de artistas de la base de datos...")
    artists = get_artists_from_db(db_path)
    print(f"Procesando {len(artists)} artistas válidos")
    
    # Obtener archivos EPUB
    epub_files = list(Path(epub_folder).glob('**/*.epub'))
    print(f"Encontrados {len(epub_files)} archivos EPUB")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    processed_count = 0
    references_found = 0
    
    for epub_file in epub_files:
        filename = epub_file.name
        
        # Verificar si ya fue procesado (si no es force_update)
        if not force_update:
            cursor.execute("SELECT COUNT(*) FROM artists_books WHERE filename = ?", (filename,))
            if cursor.fetchone()[0] > 0:
                print(f"Saltando {filename} (ya procesado)")
                continue
        
        print(f"Procesando: {filename}")
        
        # Extraer contenido del EPUB
        book_data = extract_text_from_epub(str(epub_file))
        if not book_data:
            print(f"  Error: No se pudo extraer contenido de {filename}")
            continue
        
        print(f"  Título: {book_data['title']}")
        print(f"  Autor: {book_data['author']}")
        print(f"  Páginas estimadas: {book_data['page_estimate']}")
        
        # Buscar referencias a artistas (solo usar la función normal)
        book_references = 0
        
        for artist_id, artist_name in artists:
            references = find_artist_references(
                book_data['content'], 
                artist_name,
                config.get('min_context_chars', 100),
                config.get('max_context_chars', 500),
                config.get('case_sensitive', False)
            )
            
            for reference in references:
                # Eliminar referencias existentes si es force_update
                if force_update:
                    cursor.execute("""
                        DELETE FROM artists_books 
                        WHERE artist_id = ? AND filename = ? AND content = ?
                    """, (artist_id, filename, reference))
                
                # Insertar nueva referencia
                cursor.execute("""
                    INSERT INTO artists_books 
                    (artist_id, book_title, book_author, genre, filename, 
                     page_count, char_count, content, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    artist_id,
                    book_data['title'],
                    book_data['author'],
                    book_data['genre'],
                    filename,
                    book_data['page_estimate'],
                    book_data['char_count'],
                    reference,
                    datetime.now()
                ))
                
                book_references += 1
                references_found += 1
        
        if book_references > 0:
            print(f"  Encontradas {book_references} referencias a artistas")
        
        processed_count += 1
        
        # Commit cada 10 archivos
        if processed_count % 10 == 0:
            conn.commit()
            print(f"Procesados {processed_count} archivos...")
    
    conn.commit()
    conn.close()
    
    print(f"\nProcesamiento completado:")
    print(f"- Archivos procesados: {processed_count}")
    print(f"- Referencias encontradas: {references_found}")

def get_special_artists_list():
    """
    Retorna una lista de artistas especiales que pueden causar problemas
    en las búsquedas por ser palabras comunes o muy cortas
    """
    return [
        "and",
        "the the", 
        "dark",
        "yes",
        "no",
        "air",
        "ash",
        "war",
        "sun",
        "moon",
        "fire",
        "ice",
        "black",
        "white",
        "red",
        "blue",
        "green",
        "hot",
        "cold",
        "low",
        "high",
        "born",
        "live",
        "dead",
        "new",
        "old",
        "big",
        "small",
        "love",
        "hate",
        "good",
        "bad",
        "real",
        "fake",
        "true",
        "false",
        "easy",
        "hard"
    ]





def main(config=None):
    """Función principal compatible con db_creator"""
    if config is None:
        # Modo standalone
        parser = argparse.ArgumentParser(description='Buscar referencias a artistas en archivos EPUB')
        parser.add_argument('--epub-folder', required=True, help='Carpeta con archivos EPUB')
        parser.add_argument('--db-path', required=True, help='Ruta a la base de datos SQLite')
        parser.add_argument('--force-update', action='store_true', help='Forzar actualización')
        parser.add_argument('--min-context', type=int, default=100, help='Mínimo contexto en caracteres')
        parser.add_argument('--max-context', type=int, default=500, help='Máximo contexto en caracteres')
        parser.add_argument('--case-sensitive', action='store_true', help='Búsqueda sensible a mayúsculas')
        
        args = parser.parse_args()
        
        config = {
            'epub_folder': args.epub_folder,
            'db_path': args.db_path,
            'force_update': args.force_update,
            'min_context_chars': args.min_context,
            'max_context_chars': args.max_context,
            'case_sensitive': args.case_sensitive
        }
    else:
        # Modo db_creator - usar configuración pasada
        pass
    
    try:
        process_epub_files(config)
        print("Proceso completado exitosamente")
        
    except Exception as e:
        print(f"Error durante el procesamiento: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())