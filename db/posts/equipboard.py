    
#!/usr/bin/env python3
"""
Script completo para extraer datos de equipboard.com y almacenarlos en SQLite
Extrae todo el equipo de los artistas: guitarras, amplificadores, pedales, etc.
"""

import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, quote, urlparse
import json
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_equipboard_table(cursor):
    """Crea la tabla equipboard para almacenar información completa del equipo"""
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipboard (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artist_id INTEGER,
        artist_name TEXT NOT NULL,
        equipboard_url TEXT,
        equipment_id TEXT,  -- ID único del equipo en equipboard
        equipment_name TEXT NOT NULL,
        brand TEXT,
        model TEXT,
        equipment_type TEXT,  -- guitar, bass, drums, microphone, etc.
        category TEXT,  -- guitars, amplifiers, effects-pedals, etc.
        description TEXT,
        usage_notes TEXT,  -- Notas sobre cómo usa el equipo
        image_url TEXT,
        votes INTEGER DEFAULT 0,
        submission_status TEXT,  -- correct, needs-review, needs-improvement
        verified BOOLEAN DEFAULT 0,
        gear_page_url TEXT,  -- URL del equipo específico
        price_range TEXT,
        availability TEXT,
        year_made INTEGER,
        source_info TEXT,  -- Información de la fuente que confirma el uso
        tags TEXT,  -- Tags JSON
        specifications TEXT,  -- Especificaciones técnicas JSON
        related_artists TEXT,  -- Otros artistas que usan el mismo equipo
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (artist_id) REFERENCES artists (id)
    )''')
    
    # Índices para mejorar el rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_artist_id ON equipboard (artist_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_equipment_type ON equipboard (equipment_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_brand ON equipboard (brand)')

def normalize_artist_name_for_url(artist_name):
    """Normaliza el nombre del artista para la URL de equipboard"""
    # Convertir a minúsculas y reemplazar espacios y caracteres especiales
    normalized = re.sub(r'[^\w\s-]', '', artist_name.lower())
    normalized = re.sub(r'[\s_-]+', '-', normalized)
    normalized = normalized.strip('-')
    return normalized

def search_artist_equipboard(artist_name, session):
    """Busca un artista en equipboard.com usando múltiples estrategias"""
    try:
        # Estrategia 1: URL directa del artista
        normalized_name = normalize_artist_name_for_url(artist_name)
        direct_url = f"https://equipboard.com/pros/{normalized_name}"
        
        response = session.get(direct_url, timeout=10)
        if response.status_code == 200 and 'equipment' in response.text.lower():
            logger.info(f"Encontrado directamente: {direct_url}")
            return direct_url
        
        # Estrategia 2: Búsqueda en el sitio
        search_term = quote(artist_name.strip())
        search_url = f"https://equipboard.com/search?search_term={search_term}"
        
        response = session.get(search_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscar enlaces de artistas en los resultados
        # Buscamos enlaces que apunten a páginas de profesionales
        artist_links = soup.find_all('a', href=re.compile(r'/pros/[^/]+/?$'))
        
        for link in artist_links:
            link_text = link.get_text(strip=True).lower()
            artist_lower = artist_name.lower()
            
            # Verificar coincidencia exacta o parcial
            if (artist_lower in link_text or 
                link_text in artist_lower or 
                similar_artist_names(artist_name, link_text)):
                full_url = urljoin("https://equipboard.com", link['href'])
                logger.info(f"Encontrado en búsqueda: {full_url}")
                return full_url
        
        # Estrategia 3: Variaciones del nombre
        variations = generate_name_variations(artist_name)
        for variation in variations:
            normalized_var = normalize_artist_name_for_url(variation)
            var_url = f"https://equipboard.com/pros/{normalized_var}"
            
            response = session.get(var_url, timeout=10)
            if response.status_code == 200 and 'equipment' in response.text.lower():
                logger.info(f"Encontrado con variación '{variation}': {var_url}")
                return var_url
        
        logger.warning(f"No se encontró {artist_name} en equipboard")
        return None
        
    except Exception as e:
        logger.error(f"Error buscando {artist_name} en equipboard: {e}")
        return None

def similar_artist_names(name1, name2):
    """Verifica si dos nombres de artistas son similares"""
    # Remover artículos y preposiciones comunes
    stopwords = ['the', 'and', 'or', 'of', 'a', 'an']
    
    def clean_name(name):
        words = re.findall(r'\b\w+\b', name.lower())
        return [w for w in words if w not in stopwords]
    
    words1 = clean_name(name1)
    words2 = clean_name(name2)
    
    # Si tienen palabras en común
    common_words = set(words1) & set(words2)
    if common_words and len(common_words) >= min(len(words1), len(words2)) * 0.5:
        return True
    
    return False

def generate_name_variations(artist_name):
    """Genera variaciones del nombre del artista"""
    variations = []
    
    # Remover "The" al inicio
    if artist_name.lower().startswith('the '):
        variations.append(artist_name[4:])
    else:
        variations.append(f"The {artist_name}")
    
    # Reemplazar & con and
    if '&' in artist_name:
        variations.append(artist_name.replace('&', 'and'))
    
    # Reemplazar espacios con guiones
    variations.append(artist_name.replace(' ', '-'))
    
    return variations

def extract_artist_equipment(artist_url, artist_name, session):
    """Extrae todo el equipo de un artista desde su página de equipboard"""
    try:
        response = session.get(artist_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        equipment_list = []
        
        logger.info(f"Extrayendo equipo de {artist_url}")
        
        # Método principal: buscar bloques de equipo individuales
        # En equipboard, cada pieza de equipo parece estar en contenedores específicos
        
        # Buscar diferentes patrones de contenedores de equipo
        equipment_containers = []
        
        # Patrón 1: Buscar divs que contengan nombres de equipo y categorías
        potential_containers = soup.find_all(['div', 'article', 'section'], 
            class_=re.compile(r'gear|equipment|item|submission|product', re.I))
        equipment_containers.extend(potential_containers)
        
        # Patrón 2: Buscar por estructura de texto (nombre + categoría)
        text_blocks = soup.find_all(text=re.compile(r'(Guitar|Bass|Drum|Synth|Pedal|Amplifier|Microphone)'))
        for text_block in text_blocks:
            parent = text_block.parent
            if parent and parent not in equipment_containers:
                equipment_containers.append(parent)
        
        # Patrón 3: Buscar enlaces a gear y sus contenedores padre
        gear_links = soup.find_all('a', href=re.compile(r'/gear/'))
        for link in gear_links:
            # Buscar el contenedor más apropiado (que contenga toda la info del equipo)
            container = find_equipment_container(link)
            if container and container not in equipment_containers:
                equipment_containers.append(container)
        
        logger.info(f"Encontrados {len(equipment_containers)} posibles contenedores de equipo")
        
        # Procesar cada contenedor potencial
        for container in equipment_containers:
            equipment_data = extract_equipment_details_improved(container, artist_url, session)
            if equipment_data:
                equipment_data['artist_name'] = artist_name
                equipment_data['equipboard_url'] = artist_url
                equipment_list.append(equipment_data)
        
        # Si aún no encuentra equipo, usar método de respaldo
        if not equipment_list:
            equipment_list = extract_equipment_fallback_method(soup, artist_url, artist_name, session)
        
        # Eliminar duplicados
        unique_equipment = remove_duplicate_equipment(equipment_list)
        
        logger.info(f"Extraídos {len(unique_equipment)} elementos únicos de equipo para {artist_name}")
        return unique_equipment
        
    except Exception as e:
        logger.error(f"Error extrayendo equipo de {artist_name}: {e}")
        return []

def find_equipment_container(gear_link):
    """Encuentra el contenedor apropiado que contiene toda la información del equipo"""
    current = gear_link.parent
    
    # Subir en el DOM hasta encontrar un contenedor que tenga toda la info
    for _ in range(5):  # Máximo 5 niveles hacia arriba
        if not current:
            break
            
        # Verificar si este contenedor tiene información completa del equipo
        text_content = current.get_text()
        
        # Debe contener tanto el nombre del equipo como la categoría
        has_equipment_name = bool(re.search(r'[A-Za-z0-9]{3,}', text_content))
        has_category = bool(re.search(r'(Guitar|Bass|Drum|Synth|Pedal|Amplifier|Microphone|Software|DJ|Keyboard)', text_content, re.I))
        
        if has_equipment_name and has_category:
            return current
            
        current = current.parent
    
    return gear_link.parent

def extract_equipment_details_improved(container, base_url, session):
    """Versión mejorada para extraer detalles de equipo basada en la estructura real de equipboard"""
    try:
        container_text = container.get_text(strip=True)
        
        # Si el contenedor es muy pequeño, probablemente no sea equipo válido
        if len(container_text) < 10:
            return None
        
        equipment_data = {}
        
        # Buscar el nombre del equipo (generalmente en un enlace o encabezado)
        equipment_name = None
        gear_link = None
        
        # Método 1: Buscar enlaces a gear
        gear_link_elem = container.find('a', href=re.compile(r'/gear/'))
        if gear_link_elem:
            equipment_name = gear_link_elem.get_text(strip=True)
            gear_link = urljoin(base_url, gear_link_elem['href'])
        
        # Método 2: Buscar en encabezados
        if not equipment_name:
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                header = container.find(tag)
                if header:
                    header_text = header.get_text(strip=True)
                    if len(header_text) > 3 and not header_text.lower() in ['gear', 'equipment']:
                        equipment_name = header_text
                        break
        
        # Método 3: Buscar el primer texto "sustancial" que no sea una categoría
        if not equipment_name:
            text_elements = container.find_all(text=True)
            for text_elem in text_elements:
                text = text_elem.strip()
                if (len(text) > 5 and 
                    not re.match(r'^(Guitar|Bass|Drum|Synth|Pedal|Amplifier|Microphone|Software|DJ|Keyboard)', text, re.I) and
                    not text.lower() in ['find it on:', 'used by', 'more info']):
                    equipment_name = text
                    break
        
        if not equipment_name:
            return None
        
        equipment_data['equipment_name'] = equipment_name
        equipment_data['gear_page_url'] = gear_link
        
        # Extraer ID del equipo
        if gear_link:
            gear_match = re.search(r'/gear/([^/?]+)', gear_link)
            if gear_match:
                equipment_data['equipment_id'] = gear_match.group(1)
        
        # Extraer categoría (tipo de equipo)
        category = extract_category_from_text(container_text)
        equipment_data['category'] = category
        equipment_data['equipment_type'] = normalize_equipment_type(category)
        
        # Extraer marca y modelo
        brand, model = parse_brand_model(equipment_name)
        equipment_data['brand'] = brand
        equipment_data['model'] = model
        
        # Extraer descripción/notas de uso
        description = extract_description_from_container(container)
        if description:
            equipment_data['description'] = description
        
        # Extraer información adicional
        usage_notes = extract_usage_notes(container_text)
        if usage_notes:
            equipment_data['usage_notes'] = usage_notes
        
        # Buscar imagen
        img_elem = container.find('img')
        if img_elem and img_elem.get('src'):
            img_url = img_elem['src']
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                img_url = urljoin(base_url, img_url)
            equipment_data['image_url'] = img_url
        
        # Extraer información de enlaces "Find it on"
        find_it_links = extract_find_it_on_links(container)
        if find_it_links:
            equipment_data['availability'] = json.dumps(find_it_links)
        
        return equipment_data
        
    except Exception as e:
        logger.warning(f"Error extrayendo detalles del equipo: {e}")
        return None

def extract_category_from_text(text):
    """Extrae la categoría del equipo del texto"""
    category_patterns = {
        'DAW Software': r'DAW Software',
        'Synth Plugins': r'Synth Plugins',
        'Guitar Amplifier Cabinets': r'Guitar Amplifier Cabinets',
        'Guitar Amplifier Heads': r'Guitar Amplifier Heads',
        'Solid Body Electric Guitars': r'Solid Body Electric Guitars',
        'DJ Controllers': r'DJ Controllers',
        'Bass Guitars': r'Bass Guitars',
        'Drums': r'Drums',
        'Microphones': r'Microphones',
        'Effects Pedals': r'Effects Pedals',
        'Keyboards': r'Keyboards',
        'Studio Recording Gear': r'Studio Recording Gear'
    }
    
    for category, pattern in category_patterns.items():
        if re.search(pattern, text, re.I):
            return category
    
    # Patrones más generales
    if re.search(r'guitar', text, re.I):
        return 'Guitars'
    elif re.search(r'amplifier|amp', text, re.I):
        return 'Amplifiers' 
    elif re.search(r'pedal|effect', text, re.I):
        return 'Effects Pedals'
    elif re.search(r'software|plugin|vst', text, re.I):
        return 'Software'
    elif re.search(r'bass', text, re.I):
        return 'Bass Guitars'
    elif re.search(r'drum', text, re.I):
        return 'Drums'
    elif re.search(r'microphone|mic', text, re.I):
        return 'Microphones'
    elif re.search(r'keyboard|synth', text, re.I):
        return 'Keyboards'
    
    return 'Unknown'

def normalize_equipment_type(category):
    """Normaliza la categoría a un tipo de equipo estándar"""
    if not category:
        return 'unknown'
    
    category_lower = category.lower()
    
    if 'guitar' in category_lower and 'amplifier' not in category_lower:
        return 'electric_guitar'
    elif 'amplifier' in category_lower or 'amp' in category_lower:
        if 'cabinet' in category_lower:
            return 'speaker_cabinet'
        elif 'head' in category_lower:
            return 'amplifier_head'
        else:
            return 'amplifier_combo'
    elif 'pedal' in category_lower or 'effect' in category_lower:
        return 'effect_pedal'
    elif 'software' in category_lower or 'plugin' in category_lower:
        return 'software'
    elif 'dj' in category_lower:
        return 'dj_equipment'
    elif 'bass' in category_lower:
        return 'bass_guitar'
    elif 'drum' in category_lower:
        return 'drums'
    elif 'microphone' in category_lower or 'mic' in category_lower:
        return 'microphone'
    elif 'keyboard' in category_lower or 'synth' in category_lower:
        return 'keyboard'
    
    return 'unknown'

def extract_description_from_container(container):
    """Extrae descripción/contexto del uso del equipo"""
    # Buscar texto entre comillas que suele contener citas sobre el uso
    quoted_text = container.find_all(text=re.compile(r'"[^"]{10,}"'))
    if quoted_text:
        return quoted_text[0].strip('"')
    
    # Buscar párrafos con información descriptiva
    paragraphs = container.find_all('p')
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 20 and not text.startswith('Find it on'):
            return text
    
    return None

def extract_usage_notes(text):
    """Extrae notas sobre el uso del equipo"""
    # Buscar patrones comunes de uso
    usage_patterns = [
        r'from\s+(.+?)\s+interview',
        r'mentioned\s+(.+?)(?:\.|$)',
        r'can be seen\s+(.+?)(?:\.|$)',
        r'used in\s+(.+?)(?:\.|$)',
        r'at\s+\d+:\d+',
        r'photographed by\s+(.+?)(?:\.|$)'
    ]
    
    for pattern in usage_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(0)
    
    return None

def extract_find_it_on_links(container):
    """Extrae los enlaces 'Find it on' para saber dónde comprar/encontrar el equipo"""
    find_it_links = []
    
    # Buscar el texto "Find it on:" y los enlaces que le siguen
    find_it_text = container.find(text=re.compile(r'Find it on', re.I))
    if find_it_text:
        parent = find_it_text.parent
        # Buscar enlaces en el mismo contenedor
        links = parent.find_all('a', href=True)
        for link in links:
            link_text = link.get_text(strip=True)
            if link_text and link_text.lower() not in ['find it on']:
                find_it_links.append({
                    'text': link_text,
                    'url': link['href']
                })
    
    return find_it_links

def extract_equipment_fallback_method(soup, artist_url, artist_name, session):
    """Método de respaldo si los métodos principales fallan"""
    equipment_list = []
    
    try:
        # Buscar todo el texto de la página y dividirlo en bloques
        page_text = soup.get_text()
        
        # Buscar líneas que parecen nombres de equipos seguidos de categorías
        lines = page_text.split('\n')
        current_equipment = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Si la línea parece ser una categoría, y la anterior era un nombre de equipo
            if (is_equipment_category(line) and current_equipment and 
                not is_equipment_category(current_equipment)):
                
                equipment_data = {
                    'artist_name': artist_name,
                    'equipboard_url': artist_url,
                    'equipment_name': current_equipment,
                    'category': line,
                    'equipment_type': normalize_equipment_type(line)
                }
                
                # Buscar descripción en las siguientes líneas
                description_lines = []
                for j in range(i+1, min(i+4, len(lines))):
                    next_line = lines[j].strip()
                    if (next_line and not next_line.startswith('Find it on') and 
                        not is_equipment_category(next_line) and len(next_line) > 10):
                        description_lines.append(next_line)
                
                if description_lines:
                    equipment_data['description'] = ' '.join(description_lines)
                
                # Extraer marca y modelo
                brand, model = parse_brand_model(current_equipment)
                equipment_data['brand'] = brand
                equipment_data['model'] = model
                
                equipment_list.append(equipment_data)
                current_equipment = None
            else:
                # Si la línea parece un nombre de equipo potencial
                if (len(line) > 5 and not is_equipment_category(line) and 
                    not line.startswith('Find it on') and
                    not line.lower() in ['more', 'info', 'used by', 'gear']):
                    current_equipment = line
        
        logger.info(f"Método de respaldo extrajo {len(equipment_list)} elementos")
        return equipment_list
        
    except Exception as e:
        logger.error(f"Error en método de respaldo: {e}")
        return []

def is_equipment_category(text):
    """Verifica si un texto es una categoría de equipo"""
    categories = [
        'DAW Software', 'Synth Plugins', 'Guitar Amplifier Cabinets', 
        'Guitar Amplifier Heads', 'Solid Body Electric Guitars', 'DJ Controllers',
        'Bass Guitars', 'Drums', 'Microphones', 'Effects Pedals', 'Keyboards',
        'Studio Recording Gear', 'Software', 'Amplifiers', 'Guitars'
    ]
    
    return any(cat.lower() in text.lower() for cat in categories)

def remove_duplicate_equipment(equipment_list):
    """Elimina equipos duplicados de la lista"""
    seen = set()
    unique_equipment = []
    
    for eq in equipment_list:
        # Crear una clave única basada en nombre y tipo
        key = f"{eq.get('equipment_name', '').lower()}-{eq.get('equipment_type', '')}"
        if key not in seen and eq.get('equipment_name'):
            seen.add(key)
            unique_equipment.append(eq)
    
    return unique_equipment

def extract_by_categories(soup, artist_url, artist_name, session):
    """Extrae equipo navegando por categorías específicas"""
    equipment_list = []
    
    # URLs de categorías comunes en equipboard
    category_patterns = [
        'guitars', 'amplifiers', 'effects-pedals', 'bass-guitars',
        'drums', 'keyboards', 'microphones', 'studio-gear', 'accessories'
    ]
    
    for category in category_patterns:
        try:
            category_url = f"{artist_url}?gear={category}"
            response = session.get(category_url, timeout=10)
            
            if response.status_code == 200:
                cat_soup = BeautifulSoup(response.content, 'html.parser')
                
                # Buscar elementos en esta categoría
                gear_items = cat_soup.find_all(['div', 'article'], 
                    class_=re.compile(r'gear|equipment|product|submission'))
                
                for item in gear_items:
                    equipment_data = extract_equipment_details(item, category_url, session)
                    if equipment_data:
                        equipment_data['artist_name'] = artist_name
                        equipment_data['equipboard_url'] = artist_url
                        equipment_data['category'] = category
                        equipment_list.append(equipment_data)
            
            # Pausa entre solicitudes
            time.sleep(1)
            
        except Exception as e:
            logger.warning(f"Error extrayendo categoría {category}: {e}")
    
    return equipment_list

def extract_equipment_details(item_element, base_url, session):
    """Extrae los detalles completos de un elemento de equipo específico - MÉTODO LEGACY"""
    # Esta función se mantiene por compatibilidad, pero ahora usa el método mejorado
    return extract_equipment_details_improved(item_element, base_url, session)

def extract_gear_page_details(gear_url, session):
    """Extrae información adicional de la página específica del equipo"""
    additional_data = {}
    
    try:
        response = session.get(gear_url, timeout=10)
        if response.status_code != 200:
            return additional_data
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Especificaciones técnicas
        specs_section = soup.select_one('[class*="specs"], [class*="specifications"]')
        if specs_section:
            specs = {}
            spec_items = specs_section.find_all(['dt', 'dd', 'li'])
            for item in spec_items:
                text = item.get_text(strip=True)
                if ':' in text:
                    key, value = text.split(':', 1)
                    specs[key.strip()] = value.strip()
            
            if specs:
                additional_data['specifications'] = json.dumps(specs)
        
        # Precio aproximado
        price_elem = soup.select_one('[class*="price"], [class*="cost"]')
        if price_elem:
            additional_data['price_range'] = price_elem.get_text(strip=True)
        
        # Año de fabricación
        year_pattern = r'(19\d{2}|20\d{2})'
        page_text = soup.get_text()
        year_matches = re.findall(year_pattern, page_text)
        if year_matches:
            # Tomar el año más común o el primero
            additional_data['year_made'] = int(year_matches[0])
        
        # Otros artistas que usan este equipo
        artists_section = soup.select_one('[class*="used-by"], [class*="artists"]')
        if artists_section:
            artist_links = artists_section.find_all('a', href=re.compile(r'/pros/'))
            if artist_links:
                related_artists = [link.get_text(strip=True) for link in artist_links[:10]]
                additional_data['related_artists'] = json.dumps(related_artists)
        
        # Pausa para no sobrecargar el servidor
        time.sleep(0.5)
        
    except Exception as e:
        logger.warning(f"Error extrayendo detalles adicionales de {gear_url}: {e}")
    
    return additional_data

def parse_brand_model(equipment_name):
    """Analiza el nombre del equipo para extraer marca y modelo"""
    try:
        # Lista extendida de marcas conocidas
        known_brands = [
            # Guitarras
            'Fender', 'Gibson', 'Martin', 'Taylor', 'Yamaha', 'Ibanez', 'PRS', 'Gretsch',
            'Rickenbacker', 'Epiphone', 'Squier', 'Guild', 'Takamine', 'Ovation', 'Washburn',
            'ESP', 'LTD', 'Jackson', 'Charvel', 'Dean', 'BC Rich', 'Schecter', 'Airline',
            'Harmony', 'Kay', 'Danelectro', 'Supro', 'National', 'Dobro',
            
            # Amplificadores
            'Marshall', 'Fender', 'Vox', 'Orange', 'Mesa', 'Boogie', 'Ampeg', 'Roland',
            'Peavey', 'Blackstar', 'Laney', 'Hiwatt', 'Soldano', 'Bogner', 'Diezel',
            'Engl', 'Hughes', 'Kettner', 'Friedman', 'Two Rock', 'Matchless', 'Bad Cat',
            'Silvertone', 'Supro', 'Victoria', 'Carr', 'Dr Z',
            
            # Efectos
            'Boss', 'Ibanez', 'Electro-Harmonix', 'MXR', 'TC Electronic', 'Strymon',
            'Chase Bliss', 'Eventide', 'Line 6', 'Digitech', 'Wampler', 'JHS', 'Empress',
            'Source Audio', 'Earthquaker Devices', 'Death By Audio', 'Big Muff', 'ProCo',
            'Dunlop', 'Cry Baby', 'Fulltone', 'Catalinbread', 'Walrus Audio', 'ZVEX',
            
            # Teclados/Sintetizadores
            'Korg', 'Roland', 'Yamaha', 'Moog', 'Sequential', 'Elektron', 'Arturia',
            'Dave Smith', 'Oberheim', 'ARP', 'Minimoog', 'Prophet', 'Jupiter', 'Juno',
            
            # Micrófonos
            'Shure', 'AKG', 'Neumann', 'Audio-Technica', 'Sennheiser', 'Blue', 'Rode',
            'Electro-Voice', 'Coles', 'RCA', 'Sony', 'Beyerdynamic',
            
            # Batería
            'DW', 'Pearl', 'Tama', 'Ludwig', 'Gretsch', 'Mapex', 'Sonor', 'Premier',
            'Zildjian', 'Sabian', 'Paiste', 'Meinl', 'Istanbul', 'Bosphorus',
            
            # Bajo
            'Fender', 'Music Man', 'Rickenbacker', 'Warwick', 'Fodera', 'Sadowsky',
            'Lakland', 'Spector', 'Ken Smith', 'Modulus', 'Alembic'
        ]
        
        # Buscar marca conocida en el nombre
        equipment_lower = equipment_name.lower()
        found_brand = None
        
        for brand in known_brands:
            if brand.lower() in equipment_lower:
                found_brand = brand
                break
        
        if found_brand:
            # Extraer el modelo removiendo la marca
            model = equipment_name.replace(found_brand, '').strip()
            # Limpiar caracteres extra al inicio
            model = re.sub(r'^[\s\-\–]+', '', model)
            return found_brand, model
        
        # Si no encuentra marca conocida, usar la primera palabra como marca
        words = equipment_name.split()
        if len(words) >= 2:
            return words[0], ' '.join(words[1:])
        
        return equipment_name, ""
        
    except Exception as e:
        logger.warning(f"Error analizando marca/modelo de '{equipment_name}': {e}")
        return equipment_name, ""

def infer_equipment_type(equipment_name):
    """Infiere el tipo de equipo basado en el nombre"""
    name_lower = equipment_name.lower()
    
    # Patrones para diferentes tipos de equipo
    type_patterns = {
        'electric_guitar': [
            'guitar', 'strat', 'telecaster', 'les paul', 'sg', 'explorer', 'flying v',
            'jazzmaster', 'jaguar', 'mustang', 'firebird', 'thunderbird'
        ],
        'acoustic_guitar': ['acoustic', 'dreadnought', 'jumbo', 'parlor', 'classical'],
        'bass_guitar': ['bass', 'precision', 'jazz bass', 'thunderbird bass'],
        'amplifier_head': ['head', 'amp head', 'amplifier head'],
        'amplifier_combo': ['combo', 'amp combo', 'amplifier combo', 'twin reverb', 'deluxe reverb'],
        'speaker_cabinet': ['cabinet', 'cab', '4x12', '2x12', '1x12', 'speaker'],
        'effect_pedal': [
            'pedal', 'distortion', 'overdrive', 'fuzz', 'delay', 'reverb', 'chorus',
            'phaser', 'flanger', 'wah', 'compressor', 'tremolo', 'vibrato', 'octave',
            'pitch shifter', 'whammy', 'big muff'
        ],
        'synthesizer': ['synth', 'synthesizer', 'moog', 'prophet', 'jupiter', 'juno'],
        'keyboard': ['keyboard', 'piano', 'electric piano', 'organ', 'hammond'],
        'microphone': ['microphone', 'mic', 'sm57', 'sm58', 'u87', 'c414'],
        'drums': ['drums', 'kit', 'snare', 'kick', 'tom', 'cymbal', 'hi-hat'],
        'audio_interface': ['interface', 'preamp', 'converter', 'recording'],
        'monitor_speakers': ['monitor', 'speaker', 'studio monitor'],
        'headphones': ['headphones', 'headphone', 'earphones'],
        'accessories': ['strap', 'pick', 'capo', 'tuner', 'case', 'stand', 'cable']
    }
    
    for eq_type, patterns in type_patterns.items():
        for pattern in patterns:
            if pattern in name_lower:
                return eq_type
    
    return 'unknown'

def get_artists_from_db(cursor, limit=None):
    """Obtiene artistas de la base de datos"""
    query = "SELECT id, name FROM artists"
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    return cursor.fetchall()

def save_equipment_to_db(cursor, equipment_list):
    """Guarda la lista de equipos en la base de datos"""
    for equipment in equipment_list:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO equipboard (
                    artist_id, artist_name, equipboard_url, equipment_id, equipment_name,
                    brand, model, equipment_type, category, description, usage_notes,
                    image_url, votes, submission_status, verified, gear_page_url,
                    price_range, availability, year_made, source_info, tags,
                    specifications, related_artists, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                equipment.get('artist_id'),
                equipment.get('artist_name'),
                equipment.get('equipboard_url'),
                equipment.get('equipment_id'),
                equipment.get('equipment_name'),
                equipment.get('brand'),
                equipment.get('model'),
                equipment.get('equipment_type'),
                equipment.get('category'),
                equipment.get('description'),
                equipment.get('usage_notes'),
                equipment.get('image_url'),
                equipment.get('votes', 0),
                equipment.get('submission_status'),
                equipment.get('verified', False),
                equipment.get('gear_page_url'),
                equipment.get('price_range'),
                equipment.get('availability'),
                equipment.get('year_made'),
                equipment.get('source_info'),
                equipment.get('tags'),
                equipment.get('specifications'),
                equipment.get('related_artists'),
                datetime.now().isoformat()
            ))
        except Exception as e:
            logger.error(f"Error guardando equipo {equipment.get('equipment_name', 'unknown')}: {e}")

def process_artist_equipboard(artist_id, artist_name, cursor, session):
    """Procesa un artista individual para extraer su equipo de equipboard"""
    logger.info(f"Procesando artista: {artist_name}")
    
    # Buscar la página del artista en equipboard
    artist_url = search_artist_equipboard(artist_name, session)
    
    if not artist_url:
        logger.warning(f"No se encontró página de equipboard para {artist_name}")
        return 0
    
    # Extraer todo el equipo del artista
    equipment_list = extract_artist_equipment(artist_url, artist_name, session)
    
    if not equipment_list:
        logger.warning(f"No se encontró equipo para {artist_name}")
        return 0
    
    # Añadir artist_id a cada elemento
    for equipment in equipment_list:
        equipment['artist_id'] = artist_id
    
    # Guardar en la base de datos
    save_equipment_to_db(cursor, equipment_list)
    
    logger.info(f"Guardados {len(equipment_list)} elementos de equipo para {artist_name}")
    return len(equipment_list)

def main():
    """Función principal del script"""
    # Configuración
    database_path = ''  # Ajustar según tu base de datos
    delay_between_requests = 2  # Segundos entre peticiones
    max_artists = None  # None para procesar todos, o un número para limitar
    
    # Configurar sesión HTTP con headers realistas
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Crear tabla de equipboard si no existe
        create_equipboard_table(cursor)
        conn.commit()
        
        # Obtener artistas de la base de datos
        artists = get_artists_from_db(cursor, max_artists)
        logger.info(f"Procesando {len(artists)} artistas")
        
        total_equipment = 0
        processed_artists = 0
        
        for artist_id, artist_name in artists:
            try:
                # Verificar si ya hemos procesado este artista
                cursor.execute(
                    "SELECT COUNT(*) FROM equipboard WHERE artist_id = ?", 
                    (artist_id,)
                )
                existing_count = cursor.fetchone()[0]
                
                if existing_count > 0:
                    logger.info(f"Saltando {artist_name} - ya procesado ({existing_count} elementos)")
                    continue
                
                # Procesar el artista
                equipment_count = process_artist_equipboard(artist_id, artist_name, cursor, session)
                total_equipment += equipment_count
                processed_artists += 1
                
                # Guardar cambios periódicamente
                if processed_artists % 10 == 0:
                    conn.commit()
                    logger.info(f"Progreso: {processed_artists} artistas procesados, {total_equipment} elementos de equipo")
                
                # Pausa entre artistas para no sobrecargar el servidor
                time.sleep(delay_between_requests)
                
            except Exception as e:
                logger.error(f"Error procesando artista {artist_name}: {e}")
                continue
        
        # Guardar cambios finales
        conn.commit()
        
        logger.info(f"Proceso completado: {processed_artists} artistas procesados, {total_equipment} elementos de equipo extraídos")
        
    except Exception as e:
        logger.error(f"Error en el proceso principal: {e}")
    
    finally:
        if 'conn' in locals():
            conn.close()
        session.close()

def update_existing_artist_equipment(artist_name, database_path):
    """Función para actualizar el equipo de un artista específico"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Crear tabla si no existe
        create_equipboard_table(cursor)
        
        # Buscar el artista en la base de datos
        cursor.execute("SELECT id, name FROM artists WHERE name LIKE ?", (f"%{artist_name}%",))
        artist = cursor.fetchone()
        
        if not artist:
            logger.error(f"Artista '{artist_name}' no encontrado en la base de datos")
            return
        
        artist_id, artist_name = artist
        
        # Eliminar equipo existente del artista
        cursor.execute("DELETE FROM equipboard WHERE artist_id = ?", (artist_id,))
        
        # Extraer nuevo equipo
        equipment_count = process_artist_equipboard(artist_id, artist_name, cursor, session)
        
        conn.commit()
        logger.info(f"Actualizado equipo para {artist_name}: {equipment_count} elementos")
        
    except Exception as e:
        logger.error(f"Error actualizando artista {artist_name}: {e}")
    
    finally:
        conn.close()
        session.close()

def get_equipment_statistics(database_path):
    """Función para obtener estadísticas del equipo extraído"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Estadísticas generales
        cursor.execute("SELECT COUNT(*) FROM equipboard")
        total_equipment = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT artist_id) FROM equipboard")
        total_artists = cursor.fetchone()[0]
        
        # Top marcas
        cursor.execute("""
            SELECT brand, COUNT(*) as count 
            FROM equipboard 
            WHERE brand IS NOT NULL 
            GROUP BY brand 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_brands = cursor.fetchall()
        
        # Top tipos de equipo
        cursor.execute("""
            SELECT equipment_type, COUNT(*) as count 
            FROM equipboard 
            WHERE equipment_type IS NOT NULL 
            GROUP BY equipment_type 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_types = cursor.fetchall()
        
        # Artistas con más equipo
        cursor.execute("""
            SELECT artist_name, COUNT(*) as count 
            FROM equipboard 
            GROUP BY artist_name 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_artists = cursor.fetchall()
        
        print(f"\n=== ESTADÍSTICAS DE EQUIPBOARD ===")
        print(f"Total elementos de equipo: {total_equipment}")
        print(f"Total artistas con equipo: {total_artists}")
        
        print(f"\n--- TOP 10 MARCAS ---")
        for brand, count in top_brands:
            print(f"{brand}: {count}")
        
        print(f"\n--- TOP 10 TIPOS DE EQUIPO ---")
        for eq_type, count in top_types:
            print(f"{eq_type}: {count}")
        
        print(f"\n--- TOP 10 ARTISTAS CON MÁS EQUIPO ---")
        for artist, count in top_artists:
            print(f"{artist}: {count}")
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
    
    finally:
        conn.close()

def search_equipment_by_artist(artist_name, database_path):
    """Función para buscar equipo de un artista específico"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT equipment_name, brand, model, equipment_type, description, votes, verified
            FROM equipboard 
            WHERE artist_name LIKE ? 
            ORDER BY votes DESC, equipment_type
        """, (f"%{artist_name}%",))
        
        equipment = cursor.fetchall()
        
        if not equipment:
            print(f"No se encontró equipo para '{artist_name}'")
            return
        
        print(f"\n=== EQUIPO DE {artist_name.upper()} ===")
        for eq_name, brand, model, eq_type, desc, votes, verified in equipment:
            status = "✓ Verificado" if verified else f"Votos: {votes or 0}"
            print(f"\n{eq_name}")
            print(f"  Marca: {brand or 'N/A'}")
            print(f"  Modelo: {model or 'N/A'}")
            print(f"  Tipo: {eq_type or 'N/A'}")
            print(f"  Estado: {status}")
            if desc:
                print(f"  Descripción: {desc[:100]}{'...' if len(desc) > 100 else ''}")
        
    except Exception as e:
        logger.error(f"Error buscando equipo: {e}")
    
    finally:
        conn.close()

def export_equipment_to_json(database_path, output_file):
    """Exporta todos los datos de equipboard a un archivo JSON"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT artist_name, equipment_name, brand, model, equipment_type, 
                   category, description, usage_notes, image_url, votes, 
                   verified, gear_page_url, specifications, related_artists
            FROM equipboard 
            ORDER BY artist_name, equipment_type, equipment_name
        """)
        
        equipment_data = []
        for row in cursor.fetchall():
            equipment_data.append({
                'artist_name': row[0],
                'equipment_name': row[1],
                'brand': row[2],
                'model': row[3],
                'equipment_type': row[4],
                'category': row[5],
                'description': row[6],
                'usage_notes': row[7],
                'image_url': row[8],
                'votes': row[9],
                'verified': bool(row[10]),
                'gear_page_url': row[11],
                'specifications': json.loads(row[12]) if row[12] else None,
                'related_artists': json.loads(row[13]) if row[13] else None
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(equipment_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Datos exportados a {output_file}: {len(equipment_data)} elementos")
        
    except Exception as e:
        logger.error(f"Error exportando datos: {e}")
    
    finally:
        conn.close()


def is_valid_equipment_element(element, text_content):
    """
    Determina si un elemento contiene información válida de equipo musical
    y no es parte de la navegación, UI o contenido irrelevante
    """
    if not element or not text_content:
        return False
    
    # Lista de textos que NO son equipo válido
    invalid_patterns = [
        # Elementos de navegación
        r'^(view all|gear|equipment|artists|home|about|sign up|sign in|login|logout)$',
        r'^(©|copyright|equipboard inc|follow|social|contact)$',
        r'^(gear guides|learning center|forum|community|photos)$',
        r'^(add your gear|add artist|add gear|contributor guidelines)$',
        
        # Elementos de UI y navegación
        r'^(demo|promo|merch store|gear demo)$',
        r'^(you need to sign|before continuing)$',
        r'^(artist or band|music producers|guitarists|drummers)$',
        r'^(bassists|djs|rappers|composers|keyboardists|singers)$',
        r'^(production & groove|electronic drums|studio monitors)$',
        
        # Categorías genéricas (sin nombre específico de equipo)
        r'^(guitars|amplifiers|effects pedals|microphones|keyboards)$',
        r'^(bass guitars|drums|software|dj controllers)$',
        r'^(electric guitars|acoustic guitars|studio recording gear)$',
        r'^(combo guitar amplifiers|guitar amplifier heads|cabinets)$',
        
        # Enlaces y elementos HTML
        r'href=|class=|<a |</a>|<div|</div>',
        r'www\.|http|\.com|\.org|\.net',
        
        # Texto muy corto o genérico
        r'^[a-z]{1,2}$',  # Texto de 1-2 caracteres
        r'^\d+$',         # Solo números
        r'^[\s\-_]+$',    # Solo espacios, guiones o guiones bajos
    ]
    
    text_lower = text_content.lower().strip()
    
    # Verificar patrones inválidos
    for pattern in invalid_patterns:
        if re.match(pattern, text_lower, re.IGNORECASE):
            return False
    
    # Debe tener al menos 3 caracteres y contener letras
    if len(text_content.strip()) < 3 or not re.search(r'[a-zA-Z]', text_content):
        return False
    
    # Verificar que no sea solo una categoría sin nombre específico
    if is_only_category_without_specifics(text_content):
        return False
    
    # Verificar estructura HTML - debe estar en un contexto apropiado
    if not is_appropriate_html_context(element):
        return False
    
    return True

def is_only_category_without_specifics(text):
    """
    Verifica si el texto es solo una categoría genérica sin información específica de equipo
    """
    generic_categories = [
        'solid body electric guitars', 'bass guitars', 'effects pedals',
        'combo guitar amplifiers', 'guitar amplifier cabinets', 'studio monitors',
        'daw software', 'multi effects pedals', 'electronic drums',
        'steel-string acoustic guitars', 'turntables', 'gear setups'
    ]
    
    text_lower = text.lower().strip()
    return text_lower in generic_categories

def is_appropriate_html_context(element):
    """
    Verifica si el elemento HTML está en un contexto apropiado para equipo musical
    """
    if not element:
        return False
    
    # Buscar en el contexto del elemento padre para ver si está en una zona de contenido
    current = element
    for _ in range(5):  # Máximo 5 niveles hacia arriba
        if not current:
            break
        
        # Verificar clases que indican contenido de equipo
        if hasattr(current, 'get'):
            class_attr = current.get('class', [])
            if isinstance(class_attr, list):
                class_str = ' '.join(class_attr).lower()
            else:
                class_str = str(class_attr).lower()
            
            # Contextos válidos de equipo
            valid_contexts = [
                'gear', 'equipment', 'item', 'product', 'submission',
                'artist-gear', 'gear-item', 'equipment-list'
            ]
            
            # Contextos inválidos (navegación, UI)
            invalid_contexts = [
                'nav', 'menu', 'header', 'footer', 'sidebar',
                'breadcrumb', 'pagination', 'social', 'advertisement'
            ]
            
            for invalid in invalid_contexts:
                if invalid in class_str:
                    return False
            
            for valid in valid_contexts:
                if valid in class_str:
                    return True
        
        current = current.parent if hasattr(current, 'parent') else None
    
    return True

def extract_equipment_from_structured_data(soup):
    """
    Extrae equipo de datos estructurados JSON-LD o microdata si están disponibles
    """
    equipment_list = []
    
    try:
        # Buscar JSON-LD
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                equipment_from_json = parse_structured_equipment_data(data)
                equipment_list.extend(equipment_from_json)
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Buscar microdata
        microdata_items = soup.find_all(attrs={'itemtype': True})
        for item in microdata_items:
            itemtype = item.get('itemtype', '')
            if 'product' in itemtype.lower() or 'musicinstrument' in itemtype.lower():
                equipment_data = extract_microdata_equipment(item)
                if equipment_data:
                    equipment_list.append(equipment_data)
    
    except Exception as e:
        logger.warning(f"Error extrayendo datos estructurados: {e}")
    
    return equipment_list

def parse_structured_equipment_data(data):
    """
    Analiza datos estructurados JSON-LD para extraer información de equipo
    """
    equipment_list = []
    
    if isinstance(data, dict):
        # Buscar productos o instrumentos musicales
        if data.get('@type') in ['Product', 'MusicInstrument', 'Thing']:
            equipment_data = {
                'equipment_name': data.get('name'),
                'brand': data.get('brand', {}).get('name') if isinstance(data.get('brand'), dict) else data.get('brand'),
                'model': data.get('model'),
                'description': data.get('description'),
                'image_url': data.get('image'),
                'gear_page_url': data.get('url')
            }
            
            if equipment_data['equipment_name']:
                equipment_list.append(equipment_data)
        
        # Buscar recursivamente en objetos anidados
        for value in data.values():
            if isinstance(value, (dict, list)):
                equipment_list.extend(parse_structured_equipment_data(value))
    
    elif isinstance(data, list):
        for item in data:
            equipment_list.extend(parse_structured_equipment_data(item))
    
    return equipment_list

def extract_clean_equipment_list(soup, artist_url, artist_name, session):
    """
    Versión mejorada que extrae solo equipo real evitando elementos de UI/navegación
    """
    equipment_list = []
    
    try:
        # Método 1: Intentar extraer de datos estructurados primero
        structured_equipment = extract_equipment_from_structured_data(soup)
        equipment_list.extend(structured_equipment)
        
        # Método 2: Buscar contenedores específicos de equipo
        equipment_containers = find_equipment_containers_improved(soup)
        
        for container in equipment_containers:
            equipment_data = extract_equipment_from_container_improved(container, artist_url)
            if equipment_data and is_valid_equipment_data(equipment_data):
                equipment_data['artist_name'] = artist_name
                equipment_data['equipboard_url'] = artist_url
                equipment_list.append(equipment_data)
        
        # Método 3: Buscar enlaces de gear específicos
        gear_links = soup.find_all('a', href=re.compile(r'/gear/[^/?#]+/?$'))
        for link in gear_links:
            container = find_closest_equipment_container(link)
            if container:
                equipment_data = extract_equipment_from_container_improved(container, artist_url)
                if equipment_data and is_valid_equipment_data(equipment_data):
                    equipment_data['artist_name'] = artist_name
                    equipment_data['equipboard_url'] = artist_url
                    # Asegurar que tenemos el enlace del gear
                    equipment_data['gear_page_url'] = urljoin(artist_url, link['href'])
                    equipment_list.append(equipment_data)
        
        # Eliminar duplicados
        unique_equipment = remove_duplicates_improved(equipment_list)
        
        logger.info(f"Extraídos {len(unique_equipment)} elementos válidos de equipo para {artist_name}")
        return unique_equipment
        
    except Exception as e:
        logger.error(f"Error extrayendo equipo limpio para {artist_name}: {e}")
        return []

def find_equipment_containers_improved(soup):
    """
    Encuentra contenedores que realmente contienen información de equipo
    """
    containers = []
    
    # Patrones de clases que típicamente contienen equipo
    equipment_class_patterns = [
        r'gear(?!.*nav)',  # 'gear' pero no 'gear-nav'
        r'equipment(?!.*menu)',
        r'item(?!.*nav)',
        r'product(?!.*nav)',
        r'submission',
        r'artist.*gear',
        r'pro.*gear'
    ]
    
    for pattern in equipment_class_patterns:
        elements = soup.find_all(attrs={'class': re.compile(pattern, re.I)})
        for element in elements:
            if is_equipment_container(element):
                containers.append(element)
    
    # También buscar por estructura de contenido
    potential_containers = soup.find_all(['article', 'section', 'div'], 
                                       attrs={'data-gear': True})
    containers.extend(potential_containers)
    
    return list(set(containers))  # Eliminar duplicados

def is_equipment_container(element):
    """
    Verifica si un elemento es realmente un contenedor de equipo
    """
    if not element:
        return False
    
    text_content = element.get_text(strip=True)
    
    # Debe tener contenido sustancial
    if len(text_content) < 10:
        return False
    
    # Debe contener indicadores de equipo musical
    equipment_indicators = [
        r'\b(guitar|bass|drum|synth|amp|pedal|mic|keyboard)\b',
        r'\b(fender|gibson|marshall|yamaha|roland|boss|mxr)\b',
        r'\b(stratocaster|telecaster|les paul|precision|jazz)\b'
    ]
    
    has_equipment_indicator = any(
        re.search(pattern, text_content, re.I) 
        for pattern in equipment_indicators
    )
    
    if not has_equipment_indicator:
        return False
    
    # No debe ser navegación o UI
    ui_indicators = [
        r'sign up|sign in|follow|contact|about us',
        r'view all|browse|search|filter',
        r'©|copyright|privacy|terms'
    ]
    
    has_ui_indicator = any(
        re.search(pattern, text_content, re.I) 
        for pattern in ui_indicators
    )
    
    return not has_ui_indicator

def extract_equipment_from_container_improved(container, base_url):
    """
    Extrae información de equipo de un contenedor validado
    """
    try:
        equipment_data = {}
        
        # 1. Extraer nombre del equipo
        equipment_name = extract_equipment_name_improved(container)
        if not equipment_name or not is_valid_equipment_name(equipment_name):
            return None
        
        equipment_data['equipment_name'] = equipment_name
        
        # 2. Extraer enlace del gear
        gear_link = container.find('a', href=re.compile(r'/gear/'))
        if gear_link:
            equipment_data['gear_page_url'] = urljoin(base_url, gear_link['href'])
            
            # Extraer ID del equipo
            gear_match = re.search(r'/gear/([^/?]+)', gear_link['href'])
            if gear_match:
                equipment_data['equipment_id'] = gear_match.group(1)
        
        # 3. Extraer categoría/tipo
        category = extract_equipment_category_improved(container)
        if category:
            equipment_data['category'] = category
            equipment_data['equipment_type'] = normalize_equipment_type(category)
        
        # 4. Extraer marca y modelo
        brand, model = parse_brand_model_improved(equipment_name)
        equipment_data['brand'] = brand
        equipment_data['model'] = model
        
        # 5. Extraer descripción si existe
        description = extract_equipment_description_improved(container)
        if description:
            equipment_data['description'] = description
        
        # 6. Extraer imagen
        img = container.find('img')
        if img and img.get('src'):
            img_url = img['src']
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                img_url = urljoin(base_url, img_url)
            equipment_data['image_url'] = img_url
        
        return equipment_data
        
    except Exception as e:
        logger.warning(f"Error extrayendo equipo del contenedor: {e}")
        return None

def extract_equipment_name_improved(container):
    """
    Extrae el nombre del equipo de forma más precisa
    """
    # Método 1: Buscar en enlaces de gear
    gear_link = container.find('a', href=re.compile(r'/gear/'))
    if gear_link:
        name = gear_link.get_text(strip=True)
        if is_valid_equipment_name(name):
            return name
    
    # Método 2: Buscar en encabezados
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        header = container.find(tag)
        if header:
            name = header.get_text(strip=True)
            if is_valid_equipment_name(name):
                return name
    
    # Método 3: Buscar texto con atributos específicos
    name_elements = container.find_all(attrs={'data-name': True})
    for elem in name_elements:
        name = elem.get_text(strip=True)
        if is_valid_equipment_name(name):
            return name
    
    # Método 4: Buscar el primer texto sustancial que parezca un nombre de equipo
    text_elements = container.find_all(text=True)
    for text_elem in text_elements:
        text = text_elem.strip()
        if is_valid_equipment_name(text) and not is_category_text(text):
            return text
    
    return None

def is_valid_equipment_name(name):
    """
    Verifica si un texto es un nombre válido de equipo musical
    """
    if not name or len(name.strip()) < 3:
        return False
    
    name = name.strip()
    
    # No debe ser solo una categoría
    if is_category_text(name):
        return False
    
    # No debe ser texto de UI/navegación
    ui_texts = [
        'view all', 'add gear', 'find it on', 'more info',
        'sign up', 'follow', 'gear demo', 'merch store'
    ]
    
    if name.lower() in ui_texts:
        return False
    
    # Debe contener al menos una letra y no ser solo números/símbolos
    if not re.search(r'[a-zA-Z]', name):
        return False
    
    # Longitud razonable (entre 3 y 100 caracteres)
    if len(name) > 100:
        return False
    
    return True

def is_category_text(text):
    """
    Verifica si el texto es solo una categoría de equipo sin especificar modelo
    """
    categories = [
        'guitars', 'bass guitars', 'amplifiers', 'effects pedals',
        'keyboards', 'drums', 'microphones', 'software',
        'electric guitars', 'acoustic guitars', 'studio recording gear',
        'combo guitar amplifiers', 'guitar amplifier heads',
        'guitar amplifier cabinets', 'solid body electric guitars',
        'daw software', 'multi effects pedals'
    ]
    
    return text.lower().strip() in categories

def extract_equipment_category_improved(container):
    """
    Extrae la categoría del equipo de forma más precisa
    """
    container_text = container.get_text()
    
    # Buscar elementos específicos con categorías
    category_elem = container.find(attrs={'data-category': True})
    if category_elem:
        return category_elem.get('data-category')
    
    # Buscar en texto con patrones específicos
    category_patterns = {
        'Solid Body Electric Guitars': r'Solid Body Electric Guitars',
        'Bass Guitars': r'Bass Guitars',
        'Effects Pedals': r'Effects Pedals',
        'Guitar Amplifier Heads': r'Guitar Amplifier Heads',
        'Guitar Amplifier Cabinets': r'Guitar Amplifier Cabinets',
        'Combo Guitar Amplifiers': r'Combo Guitar Amplifiers',
        'Keyboards': r'Keyboards',
        'Synthesizers': r'Synthesizers',
        'Microphones': r'Microphones',
        'Studio Recording Gear': r'Studio Recording Gear',
        'DAW Software': r'DAW Software',
        'Drums': r'Drums'
    }
    
    for category, pattern in category_patterns.items():
        if re.search(pattern, container_text, re.I):
            return category
    
    return extract_category_from_text(container_text)

def is_valid_equipment_data(equipment_data):
    """
    Valida que los datos de equipo extraídos sean válidos
    """
    if not equipment_data or not isinstance(equipment_data, dict):
        return False
    
    # Debe tener al menos un nombre de equipo válido
    equipment_name = equipment_data.get('equipment_name', '').strip()
    if not equipment_name or len(equipment_name) < 3:
        return False
    
    # No debe ser texto de navegación/UI
    if not is_valid_equipment_name(equipment_name):
        return False
    
    return True

def remove_duplicates_improved(equipment_list):
    """
    Elimina duplicados de equipo de forma más inteligente
    """
    seen = set()
    unique_equipment = []
    
    for equipment in equipment_list:
        # Crear clave única más robusta
        name = equipment.get('equipment_name', '').lower().strip()
        brand = equipment.get('brand', '').lower().strip()
        model = equipment.get('model', '').lower().strip()
        
        # Normalizar nombre para comparación
        normalized_name = re.sub(r'\s+', ' ', name)
        key = f"{brand}-{normalized_name}-{model}"
        
        if key not in seen and name:
            seen.add(key)
            unique_equipment.append(equipment)
    
    return unique_equipment

def parse_brand_model_improved(equipment_name):
    """
    Versión mejorada para extraer marca y modelo con mejor precisión
    """
    try:
        # Lista más completa de marcas conocidas
        known_brands = [
            # Guitarras principales
            'Fender', 'Gibson', 'Martin', 'Taylor', 'Yamaha', 'Ibanez', 'PRS', 'Gretsch',
            'Rickenbacker', 'Epiphone', 'Squier', 'Guild', 'ESP', 'Jackson', 'Charvel',
            
            # Amplificadores principales  
            'Marshall', 'Fender', 'Vox', 'Orange', 'Mesa Boogie', 'Ampeg', 'Roland',
            'Peavey', 'Blackstar', 'Hughes & Kettner', 'Friedman', 'Two Rock',
            
            # Efectos principales
            'Boss', 'Ibanez', 'Electro-Harmonix', 'MXR', 'TC Electronic', 'Strymon',
            'Chase Bliss', 'Eventide', 'Line 6', 'DigiTech', 'Wampler', 'JHS',
            
            # Otros instrumentos
            'Korg', 'Moog', 'Sequential', 'Shure', 'AKG', 'Neumann', 'DW', 'Pearl'
        ]
        
        # Buscar marca al inicio del nombre
        equipment_words = equipment_name.split()
        found_brand = None
        
        for brand in known_brands:
            # Buscar coincidencia exacta al inicio
            if equipment_name.lower().startswith(brand.lower()):
                found_brand = brand
                break
            # Buscar como primera palabra
            elif len(equipment_words) > 0 and equipment_words[0].lower() == brand.lower():
                found_brand = brand
                break
        
        if found_brand:
            # Extraer modelo removiendo la marca
            model = equipment_name[len(found_brand):].strip()
            # Limpiar caracteres extra
            model = re.sub(r'^[\s\-–—]+', '', model)
            return found_brand, model
        
        # Si no encuentra marca conocida, usar primera palabra como marca
        if len(equipment_words) >= 2:
            return equipment_words[0], ' '.join(equipment_words[1:])
        
        return equipment_name, ""
        
    except Exception as e:
        logger.warning(f"Error analizando marca/modelo de '{equipment_name}': {e}")
        return equipment_name, ""

def extract_equipment_description_improved(container):
    """
    Extrae descripción del uso del equipo evitando texto de UI
    """
    # Buscar descripciones en elementos específicos
    desc_selectors = [
        '[data-description]',
        '.description',
        '.notes',
        '.usage',
        '.details'
    ]
    
    for selector in desc_selectors:
        desc_elem = container.select_one(selector)
        if desc_elem:
            desc = desc_elem.get_text(strip=True)
            if is_valid_description(desc):
                return desc
    
    # Buscar en párrafos
    paragraphs = container.find_all('p')
    for p in paragraphs:
        text = p.get_text(strip=True)
        if is_valid_description(text):
            return text
    
    # Buscar texto entre comillas
    quoted_texts = re.findall(r'"([^"]{20,})"', container.get_text())
    for quote in quoted_texts:
        if is_valid_description(quote):
            return quote
    
    return None

def is_valid_description(text):
    """
    Verifica si un texto es una descripción válida del equipo
    """
    if not text or len(text) < 15:
        return False
    
    # No debe ser texto de UI/navegación
    invalid_desc_patterns = [
        r'^(find it on|more info|view all|add gear)',
        r'^(sign up|follow|contact|about)',
        r'^(© equipboard|copyright)',
        r'^(gear guides|learning center)'
    ]
    
    text_lower = text.lower().strip()
    for pattern in invalid_desc_patterns:
        if re.match(pattern, text_lower):
            return False
    
    return True

def extract_artist_equipment_improved(artist_url, artist_name, session):
    """
    FUNCIÓN PRINCIPAL MEJORADA - Reemplaza extract_artist_equipment
    Extrae solo equipo real evitando elementos de navegación/UI
    """
    try:
        response = session.get(artist_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        logger.info(f"Extrayendo equipo (método mejorado) de {artist_url}")
        
        # Método mejorado que filtra elementos no válidos
        equipment_list = extract_clean_equipment_list(soup, artist_url, artist_name, session)
        
        # Si no encuentra equipo con el método principal, usar método de respaldo mejorado
        if not equipment_list:
            equipment_list = extract_equipment_fallback_improved(soup, artist_url, artist_name)
        
        # Validación final - filtrar cualquier elemento inválido que haya pasado
        valid_equipment = []
        for equipment in equipment_list:
            if is_valid_equipment_data(equipment):
                # Validación adicional del nombre
                name = equipment.get('equipment_name', '').strip()
                if (len(name) >= 3 and 
                    not is_category_text(name) and 
                    is_valid_equipment_name(name)):
                    valid_equipment.append(equipment)
        
        logger.info(f"Extraídos {len(valid_equipment)} elementos válidos de equipo para {artist_name}")
        return valid_equipment
        
    except Exception as e:
        logger.error(f"Error extrayendo equipo de {artist_name}: {e}")
        return []

def extract_equipment_fallback_improved(soup, artist_url, artist_name):
    """
    Método de respaldo mejorado que evita elementos de UI/navegación
    """
    equipment_list = []
    
    try:
        # Buscar solo enlaces específicos de gear
        gear_links = soup.find_all('a', href=re.compile(r'/gear/[^/?#]+/?'))

        
        processed_gear_ids = set()
        
        for link in gear_links:
            try:
                # Extraer ID del gear para evitar duplicados
                gear_match = re.search(r'/gear/([^/?#]+)', link['href'])
                if not gear_match:
                    continue
                
                gear_id = gear_match.group(1)
                if gear_id in processed_gear_ids:
                    continue
                processed_gear_ids.add(gear_id)
                
                # Extraer nombre del equipo
                equipment_name = link.get_text(strip=True)
                
                # Validar que sea un nombre de equipo válido
                if not is_valid_equipment_name(equipment_name):
                    continue
                
                # Buscar contenedor padre para más información
                container = find_closest_equipment_container(link)
                
                equipment_data = {
                    'artist_name': artist_name,
                    'equipboard_url': artist_url,
                    'equipment_name': equipment_name,
                    'equipment_id': gear_id,
                    'gear_page_url': urljoin(artist_url, link['href'])
                }
                
                # Extraer información adicional del contenedor si existe
                if container:
                    category = extract_equipment_category_improved(container)
                    if category:
                        equipment_data['category'] = category
                        equipment_data['equipment_type'] = normalize_equipment_type(category)
                    
                    description = extract_equipment_description_improved(container)
                    if description:
                        equipment_data['description'] = description
                
                # Extraer marca y modelo
                brand, model = parse_brand_model_improved(equipment_name)
                equipment_data['brand'] = brand
                equipment_data['model'] = model
                
                equipment_list.append(equipment_data)
                
            except Exception as e:
                logger.warning(f"Error procesando enlace de gear: {e}")
                continue
        
        logger.info(f"Método de respaldo extrajo {len(equipment_list)} elementos")
        return equipment_list
        
    except Exception as e:
        logger.error(f"Error en método de respaldo: {e}")
        return []

def find_closest_equipment_container(gear_link):
    """
    Encuentra el contenedor más cercano que contiene información completa del equipo
    """
    current = gear_link.parent
    
    for _ in range(6):  # Máximo 6 niveles hacia arriba
        if not current:
            break
        
        # Verificar si este contenedor tiene información del equipo
        if is_equipment_container(current):
            return current
        
        current = current.parent if hasattr(current, 'parent') else None
    
    return gear_link.parent

def debug_extraction_for_artist(artist_name, database_path, limit_output=True):
    """
    Función de depuración para analizar qué se está extrayendo de un artista específico
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        # Buscar artista
        artist_url = search_artist_equipboard(artist_name, session)
        if not artist_url:
            print(f"❌ No se encontró {artist_name} en equipboard")
            return
        
        print(f"✅ Encontrado: {artist_url}")
        
        # Obtener página
        response = session.get(artist_url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Analizar contenido extraído
        print(f"\n=== ANÁLISIS DE EXTRACCIÓN PARA {artist_name.upper()} ===")
        
        # Método actual (problemático)
        print("\n--- MÉTODO ACTUAL (PROBLEMÁTICO) ---")
        old_equipment = extract_artist_equipment(artist_url, artist_name, session)
        print(f"Elementos extraídos: {len(old_equipment)}")
        
        if limit_output:
            for i, eq in enumerate(old_equipment[:5]):  # Solo mostrar primeros 5
                name = eq.get('equipment_name', 'N/A')
                eq_type = eq.get('equipment_type', 'N/A')
                print(f"  {i+1}. {name} ({eq_type})")
            if len(old_equipment) > 5:
                print(f"  ... y {len(old_equipment) - 5} más")
        
        # Método mejorado
        print("\n--- MÉTODO MEJORADO ---")
        new_equipment = extract_artist_equipment_improved(artist_url, artist_name, session)
        print(f"Elementos extraídos: {len(new_equipment)}")
        
        for i, eq in enumerate(new_equipment):
            name = eq.get('equipment_name', 'N/A')
            brand = eq.get('brand', 'N/A')
            eq_type = eq.get('equipment_type', 'N/A')
            print(f"  {i+1}. {name} | {brand} | {eq_type}")
        
        # Análisis de elementos filtrados
        print(f"\n--- ANÁLISIS ---")
        print(f"Elementos filtrados: {len(old_equipment) - len(new_equipment)}")
        print(f"Mejora: {((len(old_equipment) - len(new_equipment)) / max(len(old_equipment), 1) * 100):.1f}% de elementos inválidos eliminados")
        
        # Mostrar algunos elementos que fueron filtrados
        if len(old_equipment) > len(new_equipment):
            print(f"\n--- EJEMPLOS DE ELEMENTOS FILTRADOS ---")
            old_names = {eq.get('equipment_name', '') for eq in old_equipment}
            new_names = {eq.get('equipment_name', '') for eq in new_equipment}
            filtered_names = old_names - new_names
            
            for i, name in enumerate(list(filtered_names)[:5]):
                print(f"  ❌ {name}")
            
            if len(filtered_names) > 5:
                print(f"  ... y {len(filtered_names) - 5} más")
        
    except Exception as e:
        logger.error(f"Error en depuración: {e}")
    finally:
        session.close()

def validate_equipment_extraction_quality(database_path, sample_size=10):
    """
    Valida la calidad de la extracción comparando métodos antiguo vs nuevo
    """
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Obtener muestra de artistas
        cursor.execute("SELECT id, name FROM artists ORDER BY RANDOM() LIMIT ?", (sample_size,))
        artists = cursor.fetchall()
        
        print(f"=== VALIDACIÓN DE CALIDAD DE EXTRACCIÓN ===")
        print(f"Analizando {len(artists)} artistas...")
        
        total_old = 0
        total_new = 0
        improvements = []
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        for artist_id, artist_name in artists:
            try:
                artist_url = search_artist_equipboard(artist_name, session)
                if not artist_url:
                    continue
                
                # Método antiguo
                old_equipment = extract_artist_equipment(artist_url, artist_name, session)
                old_count = len(old_equipment)
                
                # Método nuevo
                new_equipment = extract_artist_equipment_improved(artist_url, artist_name, session)
                new_count = len(new_equipment)
                
                total_old += old_count
                total_new += new_count
                
                if old_count > 0:
                    improvement = ((old_count - new_count) / old_count) * 100
                    improvements.append(improvement)
                    
                    print(f"{artist_name:20} | Antiguo: {old_count:3} | Nuevo: {new_count:3} | Filtrado: {improvement:5.1f}%")
                
                time.sleep(1)  # Pausa entre solicitudes
                
            except Exception as e:
                logger.warning(f"Error validando {artist_name}: {e}")
                continue
        
        # Estadísticas finales
        if improvements:
            avg_improvement = sum(improvements) / len(improvements)
            print(f"\n=== RESULTADOS ===")
            print(f"Total elementos antiguos: {total_old}")
            print(f"Total elementos nuevos: {total_new}")
            print(f"Elementos filtrados: {total_old - total_new}")
            print(f"Mejora promedio: {avg_improvement:.1f}% de elementos inválidos eliminados")
            print(f"Calidad mejorada: {(total_new / max(total_old, 1)) * 100:.1f}% de precisión")
        
    except Exception as e:
        logger.error(f"Error en validación: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
        if 'session' in locals():
            session.close()

# FUNCIÓN PARA REEMPLAZAR EN EL SCRIPT PRINCIPAL
def process_artist_equipboard(artist_id, artist_name, cursor, session):
    """
    REEMPLAZA A process_artist_equipboard - Versión mejorada que evita basura
    """
    logger.info(f"Procesando artista (método mejorado): {artist_name}")
    
    # Buscar la página del artista en equipboard
    artist_url = search_artist_equipboard(artist_name, session)
    
    if not artist_url:
        logger.warning(f"No se encontró página de equipboard para {artist_name}")
        return 0
    
    # Extraer equipo usando método mejorado
    equipment_list = extract_artist_equipment_improved(artist_url, artist_name, session)
    
    if not equipment_list:
        logger.warning(f"No se encontró equipo válido para {artist_name}")
        return 0
    
    # Añadir artist_id a cada elemento
    for equipment in equipment_list:
        equipment['artist_id'] = artist_id
    
    # Guardar en la base de datos
    save_equipment_to_db(cursor, equipment_list)
    
    logger.info(f"Guardados {len(equipment_list)} elementos de equipo válidos para {artist_name}")
    return len(equipment_list)

# FUNCIONES DE UTILIDAD ADICIONALES

def clean_existing_database_entries(database_path, dry_run=True):
    """
    Limpia entradas existentes en la base de datos eliminando elementos inválidos
    """
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Obtener todas las entradas
        cursor.execute("SELECT id, equipment_name, equipment_type FROM equipboard")
        all_entries = cursor.fetchall()
        
        invalid_entries = []
        
        for entry_id, name, eq_type in all_entries:
            if not is_valid_equipment_name(name):
                invalid_entries.append((entry_id, name, eq_type))
        
        print(f"=== LIMPIEZA DE BASE DE DATOS ===")
        print(f"Total entradas: {len(all_entries)}")
        print(f"Entradas inválidas encontradas: {len(invalid_entries)}")
        
        if invalid_entries:
            print(f"\n--- EJEMPLOS DE ENTRADAS INVÁLIDAS ---")
            for i, (entry_id, name, eq_type) in enumerate(invalid_entries[:10]):
                print(f"  ID {entry_id}: '{name}' ({eq_type})")
            
            if len(invalid_entries) > 10:
                print(f"  ... y {len(invalid_entries) - 10} más")
        
        if not dry_run and invalid_entries:
            # Eliminar entradas inválidas
            invalid_ids = [str(entry[0]) for entry in invalid_entries]
            placeholders = ','.join(['?' for _ in invalid_ids])
            cursor.execute(f"DELETE FROM equipboard WHERE id IN ({placeholders})", invalid_ids)
            conn.commit()
            print(f"\n✅ Eliminadas {len(invalid_entries)} entradas inválidas")
        elif dry_run:
            print(f"\n⚠️  Ejecución en modo DRY RUN - no se eliminó nada")
            print(f"Para eliminar realmente, usar: clean_existing_database_entries(database_path, dry_run=False)")
        
    except Exception as e:
        logger.error(f"Error limpiando base de datos: {e}")
    finally:
        if 'conn' in locals():
            conn.close()



if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Extractor de datos de Equipboard.com')
    parser.add_argument('--action', choices=['extract', 'update', 'stats', 'search', 'export'], 
                       default='extract', help='Acción a realizar')
    parser.add_argument('--artist', type=str, help='Nombre del artista (para update/search)')
    parser.add_argument('--database', type=str, default='db/sqlite/musica.sqlite', 
                       help='Ruta de la base de datos')
    parser.add_argument('--limit', type=int, help='Límite de artistas a procesar')
    parser.add_argument('--output', type=str, default='equipboard_data.json', 
                       help='Archivo de salida para export')
    
    args = parser.parse_args()
    
    if args.database:
        database_path = args.database
    else:
        database_path = 'db/sqlite/musica.sqlite'

    if args.action == 'extract':
        if args.limit:
            # Actualizar la variable global
            import __main__
            __main__.max_artists = args.limit
        main()
    
    elif args.action == 'update':
        if not args.artist:
            print("Se requiere --artist para la acción update")
            exit(1)
        update_existing_artist_equipment(args.artist, args.database)
    
    elif args.action == 'stats':
        get_equipment_statistics(args.database)
    
    elif args.action == 'search':
        if not args.artist:
            print("Se requiere --artist para la acción search")
            exit(1)
        search_equipment_by_artist(args.artist, args.database)
    
    elif args.action == 'export':
        export_equipment_to_json(args.database, args.output)
    
    print("\n=== Uso del script ===")
    print("python equipboard_scraper.py --action extract              # Extraer todo")
    print("python equipboard_scraper.py --action extract --limit 50   # Extraer 50 artistas")
    print("python equipboard_scraper.py --action update --artist 'Jack White'  # Actualizar artista")
    print("python equipboard_scraper.py --action search --artist 'Jack White'  # Buscar equipo")
    print("python equipboard_scraper.py --action stats               # Ver estadísticas")
    print("python equipboard_scraper.py --action export              # Exportar a JSON")