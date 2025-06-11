#!/usr/bin/env python3
"""
Script para buscar y almacenar URLs de artistas en equipboard.com
"""

import sqlite3
import requests
import time
import re
from urllib.parse import quote, urljoin
import logging
from pathlib import Path
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_equipboard_artists_table(cursor):
    """Crea tabla para almacenar URLs de artistas de equipboard"""
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipboard_artists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER,
            artist_name TEXT NOT NULL,
            equipboard_url TEXT,
            found_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checked TIMESTAMP,
            status TEXT DEFAULT 'found',
            equipment_count INTEGER DEFAULT 0,
            
            FOREIGN KEY (artist_id) REFERENCES artists (id),
            UNIQUE(artist_id, artist_name)
        )''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_artists_name ON equipboard_artists (artist_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_artists_status ON equipboard_artists (status)')
        
        logger.info("Tabla equipboard_artists creada/verificada")
        
    except Exception as e:
        logger.error(f"Error creando tabla: {e}")
        raise

def extract_band_members_from_page(soup, band_name):
    """Extrae miembros de una banda desde la página principal del grupo - CORREGIDO"""
    members = []
    
    try:
        # Buscar enlaces a otros artistas/miembros
        member_links = soup.find_all('a', href=re.compile(r'/pros/[^/]+/?$'))
        
        # Lista extendida de términos a filtrar
        invalid_terms = [
            'view all', 'more', 'add', 'gear', 'equipment', 'pros', 'artists',
            'add artist or band', 'studio equipment', 'keyboards and synthesizers',
            'dawrs', 'daws', 'all', 'guitars', 'amplifiers', 'effects pedals',
            'microphones', 'drums', 'software', 'accessories', 'monitors',
            'interfaces', 'preamps', 'compressors', 'equalizers', 'reverbs',
            'delays', 'distortions', 'overdrives', 'chorus', 'flangers',
            'phasers', 'wah pedals', 'volume pedals', 'tuners', 'cables',
            'strings', 'picks', 'straps', 'cases', 'stands', 'racks',
            'power supplies', 'batteries', 'headphones', 'speakers',
            # Términos específicos de la interfaz de equipboard
            'artist or band', 'load more', 'show more', 'see all', 'browse all',
            'search', 'filter', 'sort', 'category', 'brand', 'model',
            'featured', 'popular', 'trending', 'new', 'latest', 'top',
            'community', 'forum', 'blog', 'news', 'reviews', 'help',
            'about', 'contact', 'privacy', 'terms', 'login', 'signup',
            'music artist', 'artist', 'musician'  # Términos genéricos nuevos
        ]
        
        # Patrones adicionales para filtrar
        invalid_patterns = [
            r'^all\d+$',
            r'^[a-z\s]+\d+$',
            r'^\d+$',
            r'^(add|view|more|all|load|show|see|browse)[\s-]',
            r'\d+$',
            r'^(artist|band|member|musician)[\s-]?(or|and)[\s-]?(band|artist)$',
            r'^(load|show|see)[\s-]?more$',
            r'^music[\s-]?artist$',  # Nuevo patrón
        ]
        
        for link in member_links:
            try:
                member_url = urljoin("https://equipboard.com", link['href'])
                member_text = link.get_text(strip=True)
                
                if not member_text or len(member_text) < 2:
                    continue
                
                # Filtrar términos inválidos (insensible a mayúsculas)
                if member_text.lower() in invalid_terms:
                    logger.debug(f"Filtrado por término inválido: {member_text}")
                    continue
                
                # Filtrar patrones inválidos
                is_invalid = False
                for pattern in invalid_patterns:
                    if re.search(pattern, member_text.lower()):
                        logger.debug(f"Filtrado por patrón inválido: {member_text}")
                        is_invalid = True
                        break
                
                if is_invalid:
                    continue
                
                # Verificar que sea realmente un nombre de persona/artista
                if not is_valid_artist_name(member_text):
                    logger.debug(f"Filtrado por nombre inválido: {member_text}")
                    continue
                
                # Para nombres de una sola palabra como "AURORA", ser más estricto
                band_words = band_name.lower().split()
                if len(band_words) == 1:
                    # Solo incluir si es exactamente el mismo nombre
                    if member_text.lower() == band_name.lower():
                        members.append((member_url, band_name))
                        logger.info(f"✅ Artista principal individual: {band_name}")
                    # Para artistas individuales, no buscar "miembros"
                    continue
                
                # Para grupos (múltiples palabras)
                if member_text.lower() == band_name.lower():
                    # Si es el mismo nombre, es el artista principal
                    members.append((member_url, band_name))
                    logger.info(f"✅ Página principal del grupo: {band_name}")
                else:
                    # Verificar que la URL sea válida antes de añadir
                    if is_valid_artist_url(member_url, band_name):
                        member_display_name = f"{band_name} ({member_text})"
                        members.append((member_url, member_display_name))
                        logger.info(f"✅ Miembro potencial: {member_text}")
                    
            except Exception as e:
                continue
        
        # Eliminar duplicados manteniendo orden
        unique_members = []
        seen_urls = set()
        
        for url, name in members:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_members.append((url, name))
        
        # Para artistas individuales, devolver solo la entrada principal
        band_words = band_name.lower().split()
        if len(band_words) == 1:
            main_artist = [(url, name) for url, name in unique_members if '(' not in name]
            if main_artist:
                return main_artist
            else:
                # Si no hay entrada principal, crear una
                main_url = f"https://equipboard.com/pros/{normalize_artist_name_for_url(band_name)}"
                return [(main_url, band_name)]
        
        # Para grupos, aplicar límites
        if len(unique_members) > 8:
            logger.warning(f"Demasiados miembros encontrados ({len(unique_members)}), probablemente son categorías")
            main_artist = [(url, name) for url, name in unique_members if '(' not in name]
            return main_artist if main_artist else [(f"https://equipboard.com/pros/{normalize_artist_name_for_url(band_name)}", band_name)]
        
        # Si no encontramos miembros válidos, devolver solo el artista principal
        if not unique_members:
            main_url = f"https://equipboard.com/pros/{normalize_artist_name_for_url(band_name)}"
            unique_members = [(main_url, band_name)]
        
        logger.info(f"Extraídos {len(unique_members)} miembros válidos para {band_name}")
        return unique_members
        
    except Exception as e:
        logger.error(f"Error extrayendo miembros de {band_name}: {e}")
        main_url = f"https://equipboard.com/pros/{normalize_artist_name_for_url(band_name)}"
        return [(main_url, band_name)]
        
def is_valid_artist_name(name):
    """Verifica si un texto parece ser un nombre de artista válido"""
    if not name or len(name.strip()) < 2:
        return False
    
    name = name.strip()
    
    # Debe contener al menos una letra
    if not re.search(r'[a-zA-Z]', name):
        return False
    
    # No debe ser solo números
    if re.match(r'^\d+$', name):
        return False
    
    # No debe terminar con números (indicativo de categorías de equipboard)
    if re.search(r'\d+$', name):
        return False
    
    # No debe contener caracteres especiales extraños
    if re.search(r'[<>@#$%^&*()+={}[\]|\\:";\'<>?/]', name):
        return False
    
    # Longitud razonable para nombre de artista
    if len(name) > 50:
        return False
    
    # Rechazar términos obviamente no válidos para nombres de artista
    invalid_artist_terms = [
        'artist or band', 'load more', 'show more', 'view all', 'see all',
        'browse all', 'add artist', 'search', 'filter', 'category',
        'equipment', 'gear', 'studio', 'software', 'hardware'
    ]
    
    if name.lower() in invalid_artist_terms:
        return False
    
    # No debe contener palabras que indican UI/navegación
    ui_indicators = ['load', 'more', 'view', 'show', 'see', 'browse', 'add', 'all']
    name_words = name.lower().split()
    
    # Si el nombre tiene 2 palabras o menos y contiene términos de UI, rechazarlo
    if len(name_words) <= 2 and any(word in ui_indicators for word in name_words):
        return False
    
    return True


def is_valid_artist_url(url, band_name):
    """Verifica si una URL parece ser de un artista real"""
    if not url:
        return False
    
    # Extraer el nombre de la URL
    url_parts = url.split('/')
    if len(url_parts) < 2:
        return False
    
    url_name = url_parts[-1] or url_parts[-2]
    
    # No debe ser categorías conocidas de equipboard
    invalid_url_parts = [
        'gear', 'equipment', 'guitars', 'amplifiers', 'effects',
        'keyboards', 'drums', 'microphones', 'software', 'accessories'
    ]
    
    if url_name.lower() in invalid_url_parts:
        return False
    
    return True


def extract_artists_from_search(soup, original_artist_name):
    """Extrae artistas de los resultados de búsqueda con mejor filtrado"""
    found_artists = []
    
    try:
        # Buscar enlaces de artistas en resultados de búsqueda
        artist_links = soup.find_all('a', href=re.compile(r'/pros/[^/]+/?$'))
        
        for link in artist_links:
            try:
                link_text = link.get_text(strip=True)
                link_url = urljoin("https://equipboard.com", link['href'])
                
                if not link_text or len(link_text) < 2:
                    continue
                
                # Verificar si es válido antes de procesar
                if not is_valid_artist_name(link_text):
                    continue
                
                # Buscar contexto más amplio alrededor del enlace
                context_element = link.find_parent()
                context_text = ""
                
                # Buscar contexto en varios niveles padre
                for level in range(3):  # Buscar hasta 3 niveles arriba
                    if context_element:
                        context_text = context_element.get_text(strip=True)
                        if len(context_text) > 50:  # Si hay suficiente contexto, usar ese
                            break
                        context_element = context_element.find_parent()
                    else:
                        break
                
                # Verificar si es miembro de la banda
                is_member, relationship_type = is_band_member_context(
                    original_artist_name, link_text, context_text
                )
                
                if is_member:
                    if relationship_type == "main_artist":
                        found_artists.append((link_url, original_artist_name))
                        logger.info(f"✅ Artista principal: {link_text}")
                    else:
                        display_name = f"{original_artist_name} ({link_text})"
                        found_artists.append((link_url, display_name))
                        logger.info(f"✅ Miembro de banda: {link_text} (contexto: {context_text[:100]}...)")
                else:
                    logger.debug(f"❌ Descartado {link_text}: no relacionado con {original_artist_name}")
                        
            except Exception as e:
                logger.debug(f"Error procesando enlace: {e}")
                continue
        
        # Eliminar duplicados manteniendo orden
        unique_artists = []
        seen_urls = set()
        
        for url, name in found_artists:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_artists.append((url, name))
        
        logger.info(f"Encontrados {len(unique_artists)} artistas relacionados en búsqueda para {original_artist_name}")
        
        return unique_artists
        
    except Exception as e:
        logger.error(f"Error extrayendo artistas de búsqueda: {e}")
        return []


def clean_name(name):
    """Limpia un nombre de artista removiendo stopwords y caracteres especiales"""
    stopwords = ['the', 'and', 'or', 'of', 'a', 'an']
    words = re.findall(r'\b\w+\b', name.lower())
    return [w for w in words if w not in stopwords]

def similar_artist_names(name1, name2):
    """Verifica si dos nombres de artistas son similares"""
    words1 = clean_name(name1)
    words2 = clean_name(name2)
    
    common_words = set(words1) & set(words2)
    if common_words and len(common_words) >= min(len(words1), len(words2)) * 0.5:
        return True
    
    return False


def normalize_artist_name_for_url(artist_name):
    """Normaliza el nombre del artista para la URL de equipboard"""
    normalized = re.sub(r'[^\w\s-]', '', artist_name.lower())
    normalized = re.sub(r'[\s_-]+', '-', normalized)
    normalized = normalized.strip('-')
    return normalized

def generate_name_variations(artist_name):
    """Genera variaciones del nombre del artista"""
    variations = [artist_name]
    
    # Remover "The" al inicio
    if artist_name.lower().startswith('the '):
        variations.append(artist_name[4:])
    else:
        variations.append(f"The {artist_name}")
    
    # Reemplazar & con and
    if '&' in artist_name:
        variations.append(artist_name.replace('&', 'and'))
        variations.append(artist_name.replace('&', ' and '))
    
    # Reemplazar espacios con guiones
    variations.append(artist_name.replace(' ', '-'))
    
    return variations

def search_artist_equipboard(artist_name, session):
    """Busca un artista en equipboard.com y retorna lista de URLs encontradas - CORREGIDO"""
    try:
        if not artist_name or not artist_name.strip():
            return []
        
        artist_name = artist_name.strip()
        found_urls = []
        
        # Estrategia 1: URL directa del artista/grupo
        normalized_name = normalize_artist_name_for_url(artist_name)
        direct_url = f"https://equipboard.com/pros/{normalized_name}"
        
        response = session.get(direct_url, timeout=10)
        if response.status_code == 200 and ('equipment' in response.text.lower() or 'gear' in response.text.lower()):
            logger.info(f"✅ Encontrado directamente: {direct_url}")
            
            # Verificar si es una página de grupo con miembros
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar miembros del grupo en la misma página
            member_urls = extract_band_members_from_page(soup, artist_name)
            if member_urls:
                found_urls.extend(member_urls)
                logger.info(f"✅ Encontrados {len(member_urls)} entradas en página directa")
        
        # Estrategia 2: Búsqueda en el sitio (SIEMPRE realizar para grupos)
        artist_words = artist_name.lower().split()
        if len(artist_words) > 1:  # Solo para grupos, no para artistas individuales
            search_url = f"https://equipboard.com/search?search_term={quote(artist_name)}"
            logger.info(f"Realizando búsqueda para grupo: {search_url}")
            
            try:
                time.sleep(1)
                response = session.get(search_url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    search_results = extract_artists_from_search(soup, artist_name)
                    
                    # Combinar resultados evitando duplicados
                    existing_urls = set(url for url, name in found_urls)
                    
                    for url, name in search_results:
                        if url not in existing_urls:
                            found_urls.append((url, name))
                            logger.info(f"✅ Añadido desde búsqueda: {name}")
                    
                    logger.info(f"Búsqueda completada: {len(search_results)} resultados adicionales")
                else:
                    logger.warning(f"Búsqueda falló con código: {response.status_code}")
                    
            except Exception as search_error:
                logger.error(f"Error en búsqueda: {search_error}")
        
        # Estrategia 3: Variaciones del nombre (solo si no encontramos nada aún)
        if not found_urls:
            logger.info("Probando variaciones del nombre...")
            variations = generate_name_variations(artist_name)
            for variation in variations:
                try:
                    normalized_var = normalize_artist_name_for_url(variation)
                    var_url = f"https://equipboard.com/pros/{normalized_var}"
                    
                    response = session.get(var_url, timeout=5)
                    if response.status_code == 200 and ('equipment' in response.text.lower() or 'gear' in response.text.lower()):
                        logger.info(f"✅ Encontrado con variación '{variation}': {var_url}")
                        found_urls.append((var_url, artist_name))
                        break
                except:
                    continue
        
        # Ordenar resultados: artista principal primero, luego miembros
        main_artist = [item for item in found_urls if '(' not in item[1]]
        members = [item for item in found_urls if '(' in item[1]]
        
        final_results = main_artist + members
        
        if final_results:
            logger.info(f"✅ Resultado final para {artist_name}: {len(final_results)} entradas")
            for url, name in final_results:
                logger.info(f"  - {name}")
        else:
            logger.warning(f"❌ No se encontró {artist_name} en equipboard")
        
        return final_results
        
    except Exception as e:
        logger.error(f"Error buscando {artist_name}: {e}")
        return []

def similar_artist_names(name1, name2, threshold=0.3):
    """Verifica si dos nombres de artistas son similares con umbral ajustable"""
    words1 = clean_name(name1)
    words2 = clean_name(name2)
    
    if not words1 or not words2:
        return False
    
    common_words = set(words1) & set(words2)
    min_words = min(len(words1), len(words2))
    
    # Si tienen al menos una palabra en común y es significativa
    if common_words and len(common_words) >= max(1, min_words * threshold):
        return True
    
    # Verificar si un nombre está contenido en el otro
    name1_lower = name1.lower()
    name2_lower = name2.lower()
    
    if name1_lower in name2_lower or name2_lower in name1_lower:
        return True
    
    return False

def save_multiple_artist_urls(cursor, artist_id, found_urls, original_name):
    """Guarda múltiples URLs para un artista (grupo con miembros)"""
    try:
        for equipboard_url, display_name in found_urls:
            cursor.execute('''
                INSERT OR REPLACE INTO equipboard_artists 
                (artist_id, artist_name, equipboard_url, last_checked, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (artist_id, display_name, equipboard_url, datetime.now(), 'found'))
            
    except Exception as e:
        logger.error(f"Error guardando URLs múltiples para {original_name}: {e}")

def process_artists_urls(database_path, force_update=False, limit=None):
    """Procesa las URLs de los artistas"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Crear tabla
        create_equipboard_artists_table(cursor)
        
        # Obtener artistas a procesar
        artists = get_artists_to_process(cursor, force_update, limit)
        
        if not artists:
            logger.info("No hay artistas para procesar")
            return
        
        logger.info(f"🚀 Procesando URLs de {len(artists)} artistas")
        
        # Configurar sesión
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        stats = {'found': 0, 'not_found': 0, 'errors': 0, 'total_entries': 0}
        
        for i, (artist_id, artist_name) in enumerate(artists, 1):
            try:
                logger.info(f"[{i}/{len(artists)}] Buscando: {artist_name}")
                
                # Buscar URLs del artista (puede devolver múltiples para grupos)
                found_urls = search_artist_equipboard(artist_name, session)
                
                if found_urls:
                    # Guardar todas las URLs encontradas
                    save_multiple_artist_urls(cursor, artist_id, found_urls, artist_name)
                    stats['found'] += 1
                    stats['total_entries'] += len(found_urls)
                    
                    if len(found_urls) == 1:
                        logger.info(f"✅ {artist_name}: 1 entrada guardada")
                    else:
                        logger.info(f"✅ {artist_name}: {len(found_urls)} miembros guardados")
                        for url, name in found_urls:
                            logger.info(f"   - {name}")
                else:
                    save_artist_url(cursor, artist_id, artist_name, None, 'not_found')
                    stats['not_found'] += 1
                    logger.warning(f"❌ No encontrado: {artist_name}")
                
                # Commit cada 10 artistas
                if i % 10 == 0:
                    conn.commit()
                    logger.info(f"💾 Progreso guardado: {i}/{len(artists)}")
                
                # Pausa para no sobrecargar el servidor
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error procesando {artist_name}: {e}")
                save_artist_url(cursor, artist_id, artist_name, None, 'error')
                stats['errors'] += 1
                continue
        
        conn.commit()
        
        logger.info(f"\n=== ESTADÍSTICAS FINALES ===")
        logger.info(f"Artistas encontrados: {stats['found']}")
        logger.info(f"Total entradas creadas: {stats['total_entries']}")
        logger.info(f"No encontrados: {stats['not_found']}")
        logger.info(f"Errores: {stats['errors']}")
        
    except Exception as e:
        logger.error(f"Error en procesamiento: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
        if 'session' in locals():
            session.close()

def get_artist_url_stats(database_path):
    """Muestra estadísticas de URLs de artistas"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT status, COUNT(*) FROM equipboard_artists GROUP BY status")
        stats = cursor.fetchall()
        
        print("\n=== ESTADÍSTICAS DE URLs DE ARTISTAS ===")
        for status, count in stats:
            print(f"{status}: {count}")
        
        # Artistas con múltiples entradas (grupos con miembros)
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN artist_name LIKE '%(%' THEN SUBSTR(artist_name, 1, INSTR(artist_name, ' (') - 1)
                    ELSE artist_name 
                END as base_name,
                COUNT(*) as member_count
            FROM equipboard_artists 
            WHERE status = 'found' 
            GROUP BY base_name
            HAVING COUNT(*) > 1
            ORDER BY member_count DESC
            LIMIT 10
        """)
        groups = cursor.fetchall()
        
        if groups:
            print(f"\n--- TOP 10 GRUPOS CON MÁS MIEMBROS ---")
            for group_name, count in groups:
                print(f"{group_name}: {count} miembros")
        
        # Ejemplos de entradas de miembros
        cursor.execute("""
            SELECT artist_name, equipboard_url 
            FROM equipboard_artists 
            WHERE status = 'found' 
            AND artist_name LIKE '%(%'
            ORDER BY found_date DESC 
            LIMIT 10
        """)
        members = cursor.fetchall()
        
        if members:
            print(f"\n--- ÚLTIMOS 10 MIEMBROS ENCONTRADOS ---")
            for name, url in members:
                print(f"{name}")
                print(f"  🔗 {url}")
        
        # Top artistas individuales encontrados
        cursor.execute("""
            SELECT artist_name, equipboard_url 
            FROM equipboard_artists 
            WHERE status = 'found' 
            AND artist_name NOT LIKE '%(%'
            ORDER BY found_date DESC 
            LIMIT 10
        """)
        individual = cursor.fetchall()
        
        if individual:
            print(f"\n--- ÚLTIMOS 10 ARTISTAS INDIVIDUALES ---")
            for name, url in individual:
                print(f"{name}: {url}")
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


def get_artists_to_process(cursor, force_update=False, limit=None):
    """Obtiene artistas que necesitan procesamiento"""
    if force_update:
        # Si force_update, procesar todos los artistas
        query = "SELECT id, name FROM artists WHERE name IS NOT NULL AND TRIM(name) != ''"
    else:
        # Solo procesar artistas que no han sido verificados
        query = """
            SELECT a.id, a.name 
            FROM artists a 
            LEFT JOIN equipboard_artists ea ON a.id = ea.artist_id 
            WHERE a.name IS NOT NULL 
            AND TRIM(a.name) != '' 
            AND ea.artist_id IS NULL
        """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    return cursor.fetchall()

def save_artist_url(cursor, artist_id, artist_name, equipboard_url, status='found'):
    """Guarda o actualiza la URL del artista"""
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO equipboard_artists 
            (artist_id, artist_name, equipboard_url, last_checked, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (artist_id, artist_name, equipboard_url, datetime.now(), status))
        
    except Exception as e:
        logger.error(f"Error guardando URL para {artist_name}: {e}")

# SELENIUM

def setup_undetected_driver(headless=True):
    """Configura el driver undetected-chromedriver"""
    try:
        options = uc.ChromeOptions()
        
        if headless:
            options.add_argument("--headless=new")
            logger.info("🔇 Modo headless activado")
        else:
            logger.info("🖥️ Modo con interfaz gráfica activado")
        
        # Configuraciones anti-detección
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--window-size=1920,1080")
        
        # User agent más realista
        options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = uc.Chrome(options=options, version_main=None)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.set_page_load_timeout(30)
        
        logger.info("✅ Driver undetected-chromedriver configurado exitosamente")
        return driver
        
    except Exception as e:
        logger.error(f"Error configurando driver: {e}")
        return None

def wait_for_cloudflare(driver, max_wait=15):
    """Espera a que Cloudflare se resuelva"""
    try:
        logger.info("☁️ Verificando Cloudflare...")
        
        # Esperar a que no haya indicadores de Cloudflare
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if ('cloudflare' not in driver.page_source.lower() and 
                'checking your browser' not in driver.page_source.lower() and
                'challenge' not in driver.page_source.lower()):
                logger.info("✅ Cloudflare resuelto")
                return True
            
            time.sleep(2)
            logger.info("⏳ Esperando resolución de Cloudflare...")
        
        logger.warning("⚠️ Cloudflare no se resolvió completamente")
        return False
        
    except Exception as e:
        logger.error(f"Error verificando Cloudflare: {e}")
        return False

def extract_artists_from_search_selenium(driver, artist_name):
    """Extrae artistas de los resultados de búsqueda usando Selenium"""
    try:
        search_url = f"https://equipboard.com/search?search_term={quote(artist_name)}"
        logger.info(f"🔍 Buscando con Selenium: {search_url}")
        
        driver.get(search_url)
        
        # Esperar Cloudflare
        wait_for_cloudflare(driver)
        
        # Esperar a que cargue la página
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Esperar a que carguen los resultados de búsqueda
        time.sleep(3)
        
        # Scroll para cargar contenido dinámico
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Buscar enlaces de artistas con diferentes selectores
        artist_selectors = [
            "a[href*='/pros/']",
            "a[href^='/pros/']",
            ".artist-link",
            ".pro-link"
        ]
        
        found_artists = []
        processed_urls = set()
        
        for selector in artist_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                logger.info(f"🔍 Selector '{selector}': {len(elements)} elementos encontrados")
                
                for element in elements:
                    try:
                        link_url = element.get_attribute('href')
                        link_text = element.text.strip()
                        
                        if not link_url or not link_text or len(link_text) < 2:
                            continue
                        
                        # Verificar que es un enlace de artista válido
                        if not re.search(r'/pros/[^/]+/?$', link_url):
                            continue
                        
                        if link_url in processed_urls:
                            continue
                        processed_urls.add(link_url)
                        
                        # Verificar si es válido
                        if not is_valid_artist_name(link_text):
                            continue
                        
                        # Buscar contexto adicional para verificar relación con el grupo
                        parent_element = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'result') or contains(@class, 'item') or contains(@class, 'pro')][1]")
                        context_text = parent_element.text if parent_element else ""
                        
                        # Verificar relación con el grupo buscado
                        is_related = False
                        
                        # Criterio 1: Mención directa del grupo en el contexto
                        if artist_name.lower() in context_text.lower():
                            is_related = True
                            logger.info(f"✅ Encontrado por contexto: {link_text}")
                        
                        # Criterio 2: Similitud de nombres
                        elif similar_artist_names(artist_name, link_text):
                            is_related = True
                            logger.info(f"✅ Encontrado por similitud: {link_text}")
                        
                        # Criterio 3: Palabras comunes
                        else:
                            group_words = set(artist_name.lower().split())
                            artist_words = set(link_text.lower().split())
                            if group_words & artist_words:
                                is_related = True
                                logger.info(f"✅ Encontrado por palabras comunes: {link_text}")
                        
                        if is_related:
                            if link_text.lower() == artist_name.lower():
                                # Es el artista principal
                                found_artists.append((link_url, artist_name))
                            else:
                                # Es un miembro
                                display_name = f"{artist_name} ({link_text})"
                                found_artists.append((link_url, display_name))
                        
                    except Exception as e:
                        logger.debug(f"Error procesando elemento: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Error con selector {selector}: {e}")
                continue
        
        # Remover duplicados
        unique_artists = []
        seen_urls = set()
        
        for url, name in found_artists:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_artists.append((url, name))
        
        logger.info(f"🎯 Selenium encontró {len(unique_artists)} artistas para '{artist_name}':")
        for url, name in unique_artists:
            logger.info(f"  - {name}: {url}")
        
        return unique_artists
        
    except Exception as e:
        logger.error(f"Error en búsqueda con Selenium: {e}")
        return []

def search_artist_equipboard_selenium(artist_name, driver):
    """Busca un artista en equipboard.com usando Selenium"""
    try:
        if not artist_name or not artist_name.strip():
            return []
        
        artist_name = artist_name.strip()
        found_urls = []
        
        # Estrategia 1: URL directa del artista/grupo
        normalized_name = normalize_artist_name_for_url(artist_name)
        direct_url = f"https://equipboard.com/pros/{normalized_name}"
        
        try:
            logger.info(f"🔗 Probando URL directa: {direct_url}")
            driver.get(direct_url)
            
            # Esperar Cloudflare si aparece
            wait_for_cloudflare(driver)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Verificar si es una página válida de artista
            page_text = driver.page_source.lower()
            if ('equipment' in page_text or 'gear' in page_text) and 'not found' not in page_text:
                logger.info(f"✅ Encontrado directamente: {direct_url}")
                
                # Buscar miembros en la página del grupo
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                member_urls = extract_band_members_from_page(soup, artist_name)
                if member_urls:
                    found_urls.extend(member_urls)
                    logger.info(f"✅ Encontrados {len(member_urls)} miembros en página directa")
            
        except Exception as e:
            logger.warning(f"Error con URL directa: {e}")
        
        # Estrategia 2: Búsqueda en el sitio (SIEMPRE)
        search_results = extract_artists_from_search_selenium(driver, artist_name)
        
        # Combinar resultados evitando duplicados
        existing_urls = set(url for url, name in found_urls)
        
        for url, name in search_results:
            if url not in existing_urls:
                found_urls.append((url, name))
                logger.info(f"✅ Añadido desde búsqueda: {name}")
        
        # Estrategia 3: Variaciones del nombre (solo si no encontramos nada)
        if not found_urls:
            logger.info("🔄 Probando variaciones del nombre...")
            variations = generate_name_variations(artist_name)
            
            for variation in variations[:3]:  # Solo primeras 3 variaciones
                try:
                    normalized_var = normalize_artist_name_for_url(variation)
                    var_url = f"https://equipboard.com/pros/{normalized_var}"
                    
                    driver.get(var_url)
                    wait_for_cloudflare(driver)
                    
                    WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    page_text = driver.page_source.lower()
                    if ('equipment' in page_text or 'gear' in page_text) and 'not found' not in page_text:
                        logger.info(f"✅ Encontrado con variación '{variation}': {var_url}")
                        found_urls.append((var_url, artist_name))
                        break
                        
                except Exception as e:
                    logger.debug(f"Error con variación {variation}: {e}")
                    continue
        
        # Ordenar resultados: artista principal primero, luego miembros
        main_artist = [item for item in found_urls if '(' not in item[1]]
        members = [item for item in found_urls if '(' in item[1]]
        
        final_results = main_artist + members
        
        if final_results:
            logger.info(f"🎯 Resultado final para {artist_name}: {len(final_results)} entradas")
            for url, name in final_results:
                logger.info(f"  - {name}")
        else:
            logger.warning(f"❌ No se encontró {artist_name} en equipboard")
        
        return final_results
        
    except Exception as e:
        logger.error(f"Error buscando {artist_name} con Selenium: {e}")
        return []

def process_artists_urls_selenium(database_path, force_update=False, limit=None, headless=True):
    """Procesa las URLs de los artistas usando Selenium"""
    driver = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Crear tabla
        create_equipboard_artists_table(cursor)
        
        # Obtener artistas a procesar
        artists = get_artists_to_process(cursor, force_update, limit)
        
        if not artists:
            logger.info("No hay artistas para procesar")
            return
        
        logger.info(f"🚀 Procesando URLs de {len(artists)} artistas con Selenium")
        
        # Configurar driver
        driver = setup_undetected_driver(headless=headless)
        if not driver:
            logger.error("❌ No se pudo crear driver")
            return
        
        stats = {'found': 0, 'not_found': 0, 'errors': 0, 'total_entries': 0}
        
        for i, (artist_id, artist_name) in enumerate(artists, 1):
            try:
                logger.info(f"[{i}/{len(artists)}] Buscando: {artist_name}")
                
                # Buscar URLs del artista
                found_urls = search_artist_equipboard_selenium(artist_name, driver)
                
                if found_urls:
                    # Guardar todas las URLs encontradas
                    save_multiple_artist_urls(cursor, artist_id, found_urls, artist_name)
                    stats['found'] += 1
                    stats['total_entries'] += len(found_urls)
                    
                    if len(found_urls) == 1:
                        logger.info(f"✅ {artist_name}: 1 entrada guardada")
                    else:
                        logger.info(f"✅ {artist_name}: {len(found_urls)} miembros guardados")
                else:
                    save_artist_url(cursor, artist_id, artist_name, None, 'not_found')
                    stats['not_found'] += 1
                    logger.warning(f"❌ No encontrado: {artist_name}")
                
                # Commit cada 5 artistas
                if i % 5 == 0:
                    conn.commit()
                    logger.info(f"💾 Progreso guardado: {i}/{len(artists)}")
                
                # Pausa para no sobrecargar el servidor
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error procesando {artist_name}: {e}")
                save_artist_url(cursor, artist_id, artist_name, None, 'error')
                stats['errors'] += 1
                continue
        
        conn.commit()
        
        logger.info(f"\n=== ESTADÍSTICAS FINALES ===")
        logger.info(f"Artistas encontrados: {stats['found']}")
        logger.info(f"Total entradas creadas: {stats['total_entries']}")
        logger.info(f"No encontrados: {stats['not_found']}")
        logger.info(f"Errores: {stats['errors']}")
        
    except Exception as e:
        logger.error(f"Error en procesamiento: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        if 'conn' in locals():
            conn.close()

def debug_search_artist_selenium(artist_name, database_path, headless=False):
    """Función de debug para probar búsquedas con Selenium"""
    driver = None
    try:
        driver = setup_undetected_driver(headless=headless)
        if not driver:
            logger.error("❌ No se pudo crear driver")
            return
        
        logger.info(f"\n=== DEBUGGING BÚSQUEDA SELENIUM PARA: {artist_name} ===")
        
        # Ejecutar búsqueda
        results = search_artist_equipboard_selenium(artist_name, driver)
        
        logger.info(f"\n=== RESULTADOS FINALES ===")
        for url, name in results:
            logger.info(f"{name}: {url}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error en debug: {e}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def is_band_member_context(artist_name, candidate_name, context_text):
    """
    Verifica si un candidato es realmente miembro de la banda basándose en contexto
    """
    # Normalizar textos
    artist_lower = artist_name.lower().strip()
    candidate_lower = candidate_name.lower().strip()
    context_lower = context_text.lower()
    
    # Si es exactamente el mismo nombre, es el artista principal
    if candidate_lower == artist_lower:
        return True, "main_artist"
    
    # Para artistas de una sola palabra como "AURORA", ser más estrictos
    artist_words = artist_lower.split()
    
    if len(artist_words) == 1:
        # Para nombres de una palabra, requerir mención explícita de la banda/artista en el contexto
        if artist_lower in context_lower:
            # Verificar que no sea solo coincidencia de palabra común
            if (f"{artist_lower} band" in context_lower or 
                f"{artist_lower} member" in context_lower or
                f"of {artist_lower}" in context_lower or
                f"from {artist_lower}" in context_lower):
                return True, "band_member"
        return False, "not_related"
    
    # Para nombres de múltiples palabras (como "Alabama Shakes")
    else:
        # Buscar mención explícita del grupo en el contexto
        if artist_lower in context_lower:
            return True, "band_member"
        
        # Buscar palabras clave del grupo
        group_keywords = set(artist_words)
        context_words = set(context_lower.split())
        
        # Si al menos la mitad de las palabras del grupo aparecen en el contexto
        common_words = group_keywords & context_words
        if len(common_words) >= len(group_keywords) / 2:
            return True, "band_member"
    
    return False, "not_related"

def main(config=None):
    """Función principal actualizada con soporte para Selenium"""
    if config is None:
        import argparse
        
        parser = argparse.ArgumentParser(description='Buscar URLs de artistas en equipboard.com')
        parser.add_argument('--action', choices=['search', 'search-selenium', 'stats', 'clean', 'debug', 'debug-selenium'], default='search')
        parser.add_argument('--db_path', type=str, default='db/sqlite/musica.sqlite')
        parser.add_argument('--limit', type=int, help='Límite de artistas a procesar')
        parser.add_argument('--force-update', action='store_true')
        parser.add_argument('--artist', type=str, help='Nombre del artista para debug')
        parser.add_argument('--headless', action='store_true', default=True)
        parser.add_argument('--no-headless', action='store_false', dest='headless')
        
        args = parser.parse_args()
        config = vars(args)
    
    action = config.get('action', 'search')
    
    if action == 'search':
        # Búsqueda original con requests
        process_artists_urls(
            database_path=config.get('db_path', 'db/sqlite/musica.sqlite'),
            force_update=config.get('force_update', False),
            limit=config.get('limit')
        )
    elif action == 'search-selenium':
        # Nueva búsqueda con Selenium
        process_artists_urls_selenium(
            database_path=config.get('db_path', 'db/sqlite/musica.sqlite'),
            force_update=config.get('force_update', False),
            limit=config.get('limit'),
            headless=config.get('headless', True)
        )
    elif action == 'stats':
        get_artist_url_stats(config.get('db_path', 'db/sqlite/musica.sqlite'))

    elif action == 'debug-selenium':
        artist_name = config.get('artist')
        if not artist_name:
            print("Error: --artist es requerido para la acción debug-selenium")
            return
        debug_search_artist_selenium(
            artist_name, 
            config.get('db_path', 'db/sqlite/musica.sqlite'),
            headless=config.get('headless', True)
        )

if __name__ == "__main__":
    main()