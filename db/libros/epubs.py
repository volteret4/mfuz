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
    Versión mejorada que respeta límites de oraciones y párrafos
    """
    # Crear patrón regex para palabras completas
    pattern_flags = re.IGNORECASE if not case_sensitive else 0
    escaped_name = re.escape(artist_name)
    pattern = r'\b' + escaped_name + r'\b'
    
    references = []
    
    # Buscar todas las coincidencias
    for match in re.finditer(pattern, text, pattern_flags):
        pos = match.start()
        
        # Extraer contexto inteligente
        context = extract_smart_context(text, pos, len(artist_name), min_context, max_context)
        
        if not context or len(context) < min_context:
            continue
        
        # Evitar duplicados muy similares
        if not any(are_contexts_similar(context, ref) for ref in references):
            references.append(context)
    
    return references

def extract_smart_context(text, match_pos, match_len, min_context, max_context):
    """
    Extrae contexto inteligente alrededor de una coincidencia
    Prioriza oraciones completas y párrafos coherentes
    """
    # Primero intentar extraer por párrafos
    context = extract_paragraph_context(text, match_pos, match_len, max_context)
    
    # Si el párrafo es muy corto, expandir por oraciones
    if len(context) < min_context:
        context = extract_sentence_context(text, match_pos, match_len, min_context, max_context)
    
    # Si aún es corto, usar ventana de caracteres como último recurso
    if len(context) < min_context:
        context = extract_character_window(text, match_pos, match_len, max_context)
    
    return clean_context(context)

def extract_paragraph_context(text, match_pos, match_len, max_context):
    """
    Extrae el párrafo completo que contiene la coincidencia
    """
    # Buscar inicio del párrafo
    start_pos = match_pos
    while start_pos > 0:
        # Buscar doble salto de línea o inicio de texto
        if start_pos >= 2 and text[start_pos-2:start_pos] in ['\n\n', '\r\n\r\n']:
            break
        elif start_pos >= 1 and text[start_pos-1] == '\n':
            # Verificar si hay línea vacía anterior
            line_start = start_pos - 1
            while line_start > 0 and text[line_start-1] not in '\n\r':
                line_start -= 1
            if line_start == start_pos - 1:  # Línea vacía
                break
        start_pos -= 1
    
    # Buscar final del párrafo
    end_pos = match_pos + match_len
    while end_pos < len(text):
        # Buscar doble salto de línea o final de texto
        if end_pos < len(text) - 1 and text[end_pos:end_pos+2] in ['\n\n', '\r\n\r\n']:
            break
        elif text[end_pos] == '\n':
            # Verificar si la siguiente línea está vacía
            if end_pos + 1 < len(text) and text[end_pos + 1] in '\n\r':
                break
        end_pos += 1
    
    # Limitar tamaño máximo
    context = text[start_pos:end_pos].strip()
    if len(context) > max_context:
        # Si es muy largo, usar estrategia de oraciones
        return extract_sentence_context(text, match_pos, match_len, max_context // 2, max_context)
    
    return context

def extract_sentence_context(text, match_pos, match_len, min_context, max_context):
    """
    Extrae contexto basado en oraciones completas
    """
    # Buscar inicio de la oración que contiene la coincidencia
    start_pos = find_sentence_start(text, match_pos)
    
    # Buscar final de la oración que contiene la coincidencia
    end_pos = find_sentence_end(text, match_pos + match_len)
    
    # Expandir hacia atrás si es necesario
    while len(text[start_pos:end_pos]) < min_context and start_pos > 0:
        new_start = find_sentence_start(text, start_pos - 1)
        if new_start == start_pos:  # No se pudo retroceder más
            break
        start_pos = new_start
        if len(text[start_pos:end_pos]) > max_context:
            break
    
    # Expandir hacia adelante si es necesario
    while len(text[start_pos:end_pos]) < min_context and end_pos < len(text):
        new_end = find_sentence_end(text, end_pos + 1)
        if new_end == end_pos:  # No se pudo avanzar más
            break
        end_pos = new_end
        if len(text[start_pos:end_pos]) > max_context:
            break
    
    # Truncar si es muy largo
    context = text[start_pos:end_pos]
    if len(context) > max_context:
        # Mantener la coincidencia centrada
        match_relative_pos = match_pos - start_pos
        half_max = max_context // 2
        
        if match_relative_pos > half_max:
            # Recortar desde el inicio
            new_start = start_pos + (match_relative_pos - half_max)
            new_start = find_sentence_start(text, new_start)
            context = text[new_start:start_pos + min(len(context), max_context)]
        else:
            # Recortar desde el final
            context = context[:max_context]
            last_period = context.rfind('.')
            if last_period > len(context) - 50:  # Si el punto está cerca del final
                context = context[:last_period + 1]
    
    return context

def find_sentence_start(text, pos):
    """
    Encuentra el inicio de la oración que contiene la posición dada
    """
    if pos <= 0:
        return 0
    
    # Buscar hacia atrás por terminadores de oración
    current_pos = pos
    while current_pos > 0:
        char = text[current_pos]
        prev_char = text[current_pos - 1] if current_pos > 0 else ''
        
        # Terminadores de oración: . ! ? seguidos de espacio y mayúscula
        if prev_char in '.!?' and char in ' \n\r\t':
            # Verificar que después del espacio hay mayúscula o número
            next_pos = current_pos
            while next_pos < len(text) and text[next_pos] in ' \n\r\t':
                next_pos += 1
            if next_pos < len(text) and (text[next_pos].isupper() or text[next_pos].isdigit()):
                return next_pos
        
        # Inicio de párrafo
        elif char == '\n' and current_pos > 0:
            # Verificar si es inicio de párrafo (línea anterior vacía o inicio de texto)
            line_start = current_pos - 1
            while line_start > 0 and text[line_start] not in '\n\r':
                line_start -= 1
            if line_start == current_pos - 1:  # Línea vacía anterior
                next_pos = current_pos + 1
                while next_pos < len(text) and text[next_pos] in ' \t':
                    next_pos += 1
                if next_pos < len(text):
                    return next_pos
        
        current_pos -= 1
    
    return 0

def find_sentence_end(text, pos):
    """
    Encuentra el final de la oración que contiene la posición dada
    """
    if pos >= len(text):
        return len(text)
    
    current_pos = pos
    while current_pos < len(text):
        char = text[current_pos]
        
        # Terminadores de oración
        if char in '.!?':
            # Verificar que no es una abreviación común
            if not is_abbreviation(text, current_pos):
                # Buscar el final real (después de espacios)
                end_pos = current_pos + 1
                while end_pos < len(text) and text[end_pos] in ' \t':
                    end_pos += 1
                return end_pos
        
        # Final de párrafo
        elif char == '\n':
            # Verificar si es final de párrafo (línea siguiente vacía o final de texto)
            if current_pos + 1 >= len(text):
                return len(text)
            elif text[current_pos + 1] in '\n\r':
                return current_pos
        
        current_pos += 1
    
    return len(text)

def is_abbreviation(text, pos):
    """
    Verifica si un punto es parte de una abreviación común
    """
    if pos < 1:
        return False
    
    # Verificar abreviaciones comunes
    abbreviations = ['Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sr', 'Jr', 'vs', 'etc', 'i.e', 'e.g']
    
    for abbr in abbreviations:
        start = pos - len(abbr)
        if start >= 0 and text[start:pos] == abbr:
            return True
    
    # Verificar si es una inicial (una letra seguida de punto)
    if pos >= 1 and text[pos-1].isupper():
        if pos == 1 or not text[pos-2].isalpha():
            return True
    
    return False

def extract_character_window(text, match_pos, match_len, max_context):
    """
    Extrae una ventana de caracteres como último recurso
    """
    half_window = max_context // 2
    start_pos = max(0, match_pos - half_window)
    end_pos = min(len(text), match_pos + match_len + half_window)
    
    return text[start_pos:end_pos]

def clean_context(context):
    """
    Limpia el contexto extraído
    """
    if not context:
        return ""
    
    # Limpiar espacios múltiples y saltos de línea
    context = re.sub(r'\s+', ' ', context.strip())
    
    # Asegurar que empiece con mayúscula si es posible
    if context and context[0].islower():
        # Buscar si hay una oración completa
        first_period = context.find('. ')
        if first_period > 0 and first_period < len(context) // 2:
            context = context[first_period + 2:]
    
    return context.strip()

def are_contexts_similar(context1, context2, similarity_threshold=0.8):
    """
    Verifica si dos contextos son demasiado similares
    """
    if not context1 or not context2:
        return False
    
    # Comparar primeras y últimas palabras
    words1 = context1.split()
    words2 = context2.split()
    
    if len(words1) < 3 or len(words2) < 3:
        return context1[:50] == context2[:50]
    
    # Verificar solapamiento significativo
    start_match = words1[:3] == words2[:3]
    end_match = words1[-3:] == words2[-3:]
    
    return start_match and end_match


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
        "can",
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