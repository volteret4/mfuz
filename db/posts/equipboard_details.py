#!/usr/bin/env python3
"""
Script para extraer información detallada de instrumentos desde equipboard.com
"""

import sqlite3
import requests
import time
import re
import json
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_equipboard_details_table(cursor):
    """Crea tabla para almacenar información detallada de instrumentos"""
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipboard_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument_id INTEGER,
            equipment_id TEXT,
            equipment_name TEXT,
            equipment_url TEXT,
            
            -- Información de precios
            min_price REAL,
            average_price REAL,
            max_price REAL,
            price_tier TEXT,
            stores_available INTEGER,
            
            -- Reviews y valoraciones
            total_reviews INTEGER,
            review_score REAL,
            used_by_artists_count INTEGER,
            
            -- Descripción y especificaciones
            detailed_description TEXT,
            specifications TEXT,
            pros TEXT,
            cons TEXT,
            user_comments TEXT,
            
            -- Contexto musical
            genre_usage TEXT,
            related_artists TEXT,
            
            -- Metadatos técnicos
            analog_digital TEXT,
            polyphony INTEGER,
            oscillators INTEGER,
            year_made INTEGER,
            
            -- Control de calidad
            data_quality_score INTEGER,
            extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            extraction_method TEXT,
            
            FOREIGN KEY (instrument_id) REFERENCES equipboard_instruments (id),
            UNIQUE(equipment_id)
        )''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_details_instrument ON equipboard_details (instrument_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_details_equipment_id ON equipboard_details (equipment_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_details_quality ON equipboard_details (data_quality_score)')
        
        logger.info("Tabla equipboard_details creada/verificada")
        
    except Exception as e:
        logger.error(f"Error creando tabla: {e}")
        raise

def get_instruments_to_process(cursor, force_update=False, limit=None):
    """Obtiene instrumentos que necesitan procesamiento detallado"""
    if force_update:
        # Si force_update, procesar todos los instrumentos
        query = """
            SELECT id, equipment_id, equipment_name, equipment_url 
            FROM equipboard_instruments 
            WHERE equipment_url IS NOT NULL
        """
    else:
        # Solo procesar instrumentos que no han sido procesados
        query = """
            SELECT ei.id, ei.equipment_id, ei.equipment_name, ei.equipment_url 
            FROM equipboard_instruments ei 
            LEFT JOIN equipboard_details ed ON ei.equipment_id = ed.equipment_id 
            WHERE ei.equipment_url IS NOT NULL 
            AND ed.equipment_id IS NULL
        """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    return cursor.fetchall()

def extract_price_information(soup, page_text):
    """Extrae información de precios"""
    price_info = {}
    
    try:
        # Precio mínimo
        price_patterns = [
            r'best price(?:s)? from \$([0-9,]+\.?[0-9]*)',
            r'starting at \$([0-9,]+\.?[0-9]*)',
            r'from \$([0-9,]+\.?[0-9]*)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                try:
                    min_price = float(match.group(1).replace(',', ''))
                    price_info['min_price'] = min_price
                    break
                except ValueError:
                    continue
        
        # Tier de precio
        tier_patterns = [
            r'priced in the ([^.]+) range',
            r'In the [^,]+ category[^,]*is priced in the ([^.]+)\.',
        ]
        
        for pattern in tier_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                tier_text = match.group(1).strip()
                price_info['price_tier'] = normalize_price_tier(tier_text)
                break
        
        # Número de tiendas
        stores_match = re.search(r'(\d+)\s+available\s+stores?', page_text, re.I)
        if stores_match:
            price_info['stores_available'] = int(stores_match.group(1))
        
        return price_info
        
    except Exception as e:
        logger.debug(f"Error extrayendo precios: {e}")
        return {}

def extract_reviews_info(soup, page_text):
    """Extrae información de reviews y valoraciones"""
    reviews_info = {}
    
    try:
        # Número de reviews
        reviews_patterns = [
            r'read (\d+) real reviews?',
            r'(\d+) real reviews?',
            r'Rated [0-9.]+ stars by (\d+) artists?',
        ]
        
        for pattern in reviews_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                reviews_info['total_reviews'] = int(match.group(1))
                break
        
        # Número de artistas
        artists_patterns = [
            r'discover how (\d+) pro artists? use it',
            r'(\d+) pro artists? use it',
            r'(\d+) artists? using',
        ]
        
        for pattern in artists_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                reviews_info['used_by_artists_count'] = int(match.group(1))
                break
        
        # Calificación promedio
        rating_patterns = [
            r'Rated ([0-9.]+) stars',
            r'([0-9.]+) stars by',
            r'Rating: ([0-9.]+)/5',
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                try:
                    reviews_info['review_score'] = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        return reviews_info
        
    except Exception as e:
        logger.debug(f"Error extrayendo reviews: {e}")
        return {}

def extract_description(soup):
    """Extrae descripción detallada del producto"""
    try:
        # Buscar descripción principal
        description_section = soup.find('section', id='description')
        
        if description_section:
            content_div = description_section.find('div', class_=lambda x: x and 'sectionToggleContent' in x)
            if content_div:
                prose_div = content_div.find('div', class_=lambda x: x and 'prose' in x)
                if prose_div:
                    paragraphs = prose_div.find_all('p')
                    description_parts = []
                    
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            description_parts.append(text)
                    
                    if description_parts:
                        return ' '.join(description_parts)[:2000]
        
        # Método de respaldo
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 200 and not text.startswith('Product prices'):
                return text[:1000]
        
        return None
        
    except Exception as e:
        logger.debug(f"Error extrayendo descripción: {e}")
        return None

def extract_specifications(soup, page_text):
    """Extrae especificaciones técnicas"""
    specs_info = {}
    
    try:
        # Buscar tabla de especificaciones
        specs_section = soup.find(text=re.compile(r'Product specs', re.I))
        if specs_section:
            specs_container = specs_section.find_parent()
            if specs_container:
                specs_data = {}
                
                # Buscar en tabla
                table = specs_container.find_next('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            key = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            specs_data[key] = value
                
                if specs_data:
                    specs_info.update(map_specifications(specs_data))
                    specs_info['specifications'] = json.dumps(specs_data)
        
        # Extraer información específica del texto
        if 'analog' in page_text.lower():
            specs_info['analog_digital'] = 'Analog'
        elif 'digital' in page_text.lower():
            specs_info['analog_digital'] = 'Digital'
        
        # Osciladores
        osc_match = re.search(r'(\d+)\s*oscillators?', page_text, re.I)
        if osc_match:
            specs_info['oscillators'] = int(osc_match.group(1))
        
        # Polifonía
        poly_match = re.search(r'(\d+)[\s-]voice', page_text, re.I)
        if poly_match:
            specs_info['polyphony'] = int(poly_match.group(1))
        
        # Año
        year_match = re.search(r'(19\d{2}|20\d{2})', page_text)
        if year_match:
            specs_info['year_made'] = int(year_match.group(1))
        
        return specs_info
        
    except Exception as e:
        logger.debug(f"Error extrayendo especificaciones: {e}")
        return {}

def extract_pros_cons(soup, page_text):
    """Extrae pros y contras"""
    pros_cons = {}
    
    try:
        # Buscar sección de PROS
        pros_section = soup.find(text=re.compile(r'PROS', re.I))
        if pros_section:
            pros_container = pros_section.find_parent()
            if pros_container:
                pros_list = []
                items = pros_container.find_next_siblings(['li', 'p'])[:10]
                for item in items:
                    text = item.get_text(strip=True)
                    if text and not text.upper().startswith('CONS'):
                        pros_list.append(text)
                        if len(pros_list) >= 10:
                            break
                
                if pros_list:
                    pros_cons['pros'] = json.dumps(pros_list)
        
        # Buscar sección de CONS
        cons_section = soup.find(text=re.compile(r'CONS', re.I))
        if cons_section:
            cons_container = cons_section.find_parent()
            if cons_container:
                cons_list = []
                items = cons_container.find_next_siblings(['li', 'p'])[:10]
                for item in items:
                    text = item.get_text(strip=True)
                    if text:
                        cons_list.append(text)
                        if len(cons_list) >= 10:
                            break
                
                if cons_list:
                    pros_cons['cons'] = json.dumps(cons_list)
        
        return pros_cons
        
    except Exception as e:
        logger.debug(f"Error extrayendo pros/cons: {e}")
        return {}

def extract_related_artists(soup):
    """Extrae artistas relacionados"""
    try:
        related_artists = []
        
        # Buscar enlaces a artistas
        artist_links = soup.find_all('a', href=re.compile(r'/pros/[^/]+/?$'))
        
        for link in artist_links[:20]:
            artist_name = link.get_text(strip=True)
            if artist_name and len(artist_name) > 2:
                nav_terms = ['pros', 'artists', 'more', 'view all']
                if artist_name.lower() not in nav_terms:
                    related_artists.append(artist_name)
        
        # Eliminar duplicados
        unique_artists = []
        seen_lower = set()
        
        for artist in related_artists:
            artist_lower = artist.lower()
            if artist_lower not in seen_lower and len(artist) > 2:
                seen_lower.add(artist_lower)
                unique_artists.append(artist)
        
        if unique_artists:
            return json.dumps(unique_artists[:15])
        
        return None
        
    except Exception as e:
        logger.debug(f"Error extrayendo artistas relacionados: {e}")
        return None

def extract_genres(soup, page_text):
    """Extrae géneros musicales"""
    try:
        genres_found = []
        
        # Lista de géneros
        genre_list = [
            'Electronic', 'Dubstep', 'EDM', 'House', 'Techno', 'Trance',
            'Rock', 'Pop', 'Folk', 'Country', 'Alternative rock', 'Indie rock',
            'Jazz', 'Blues', 'Classical', 'Hip hop', 'Reggae', 'Funk', 'Soul'
        ]
        
        for genre in genre_list:
            if re.search(rf'\b{re.escape(genre)}\b', page_text, re.I):
                if genre not in genres_found:
                    genres_found.append(genre)
        
        if genres_found:
            return json.dumps(genres_found[:10])
        
        return None
        
    except Exception as e:
        logger.debug(f"Error extrayendo géneros: {e}")
        return None

def extract_user_comments(soup, page_text):
    """Extrae comentarios de usuarios"""
    try:
        comments = []
        
        # Comentarios entre comillas
        quoted_comments = re.findall(r'"([^"]{50,400})"', page_text)
        for comment in quoted_comments[:5]:
            if not any(skip in comment.lower() for skip in ['equipboard', 'copyright']):
                comments.append(comment.strip())
        
        if comments:
            return json.dumps(comments)
        
        return None
        
    except Exception as e:
        logger.debug(f"Error extrayendo comentarios: {e}")
        return None

def map_specifications(specs_data):
    """Mapea especificaciones a campos específicos"""
    mapped = {}
    
    field_mapping = {
        'Analog / Digital': 'analog_digital',
        'Polyphony': 'polyphony',
        'Number of Keys': 'number_of_keys',
        'Year': 'year_made'
    }
    
    for spec_key, db_field in field_mapping.items():
        if spec_key in specs_data:
            value = specs_data[spec_key]
            
            if db_field in ['polyphony', 'number_of_keys']:
                number_match = re.search(r'(\d+)', str(value))
                if number_match:
                    mapped[db_field] = int(number_match.group(1))
            elif db_field == 'year_made':
                year_match = re.search(r'(\d{4})', str(value))
                if year_match:
                    mapped[db_field] = int(year_match.group(1))
            else:
                mapped[db_field] = str(value)
    
    return mapped

def normalize_price_tier(price_tier_text):
    """Normaliza el tier de precio"""
    if not price_tier_text:
        return None
        
    tier_lower = str(price_tier_text).lower()
    
    if any(term in tier_lower for term in ['budget', 'beginner', 'entry']):
        return 'Budget'
    elif any(term in tier_lower for term in ['standard', 'professional', 'intermediate']):
        return 'Standard'
    elif any(term in tier_lower for term in ['high-end', 'boutique', 'premium']):
        return 'High-end'
    
    return price_tier_text

def calculate_quality_score(details):
    """Calcula puntuación de calidad basada en campos completados"""
    score = 0
    
    # Información básica (20 puntos)
    if details.get('equipment_name'): score += 10
    if details.get('detailed_description'): score += 10
    
    # Información de precio (15 puntos)
    if details.get('min_price'): score += 10
    if details.get('price_tier'): score += 5
    
    # Reviews y comunidad (25 puntos)
    if details.get('total_reviews'): score += 15
    if details.get('used_by_artists_count'): score += 10
    
    # Especificaciones (20 puntos)
    if details.get('specifications'): score += 15
    if details.get('analog_digital'): score += 5
    
    # Contenido adicional (20 puntos)
    if details.get('pros'): score += 5
    if details.get('cons'): score += 5
    if details.get('related_artists'): score += 5
    if details.get('genre_usage'): score += 5
    
    return min(score, 100)

def extract_instrument_details(equipment_url, session):
    """Extrae información detallada de un instrumento"""
    detailed_info = {}
    
    try:
        logger.debug(f"Extrayendo detalles de {equipment_url}")
        
        response = session.get(equipment_url, timeout=15)
        if response.status_code != 200:
            logger.warning(f"Error HTTP {response.status_code} para {equipment_url}")
            return {}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = soup.get_text()
        
        # Extraer información de precios
        price_info = extract_price_information(soup, page_text)
        detailed_info.update(price_info)
        
        # Extraer reviews
        reviews_info = extract_reviews_info(soup, page_text)
        detailed_info.update(reviews_info)
        
        # Extraer descripción
        description = extract_description(soup)
        if description:
            detailed_info['detailed_description'] = description
        
        # Extraer especificaciones
        specs_info = extract_specifications(soup, page_text)
        detailed_info.update(specs_info)
        
        # Extraer pros y cons
        pros_cons = extract_pros_cons(soup, page_text)
        detailed_info.update(pros_cons)
        
        # Extraer artistas relacionados
        related_artists = extract_related_artists(soup)
        if related_artists:
            detailed_info['related_artists'] = related_artists
        
        # Extraer géneros
        genres = extract_genres(soup, page_text)
        if genres:
            detailed_info['genre_usage'] = genres
        
        # Extraer comentarios
        comments = extract_user_comments(soup, page_text)
        if comments:
            detailed_info['user_comments'] = comments
        
        # Calcular calidad
        detailed_info['data_quality_score'] = calculate_quality_score(detailed_info)
        detailed_info['extraction_method'] = 'detailed_page_analysis'
        
        logger.debug(f"Calidad de datos: {detailed_info.get('data_quality_score', 0)}/100")
        
        return detailed_info
        
    except Exception as e:
        logger.error(f"Error extrayendo detalles de {equipment_url}: {e}")
        return {}

def save_instrument_details(cursor, instrument_id, equipment_id, equipment_name, equipment_url, details):
    """Guarda los detalles del instrumento en la base de datos"""
    try:
        # Preparar datos
        data = {
            'instrument_id': instrument_id,
            'equipment_id': equipment_id,
            'equipment_name': equipment_name,
            'equipment_url': equipment_url
        }
        
        # Añadir detalles extraídos
        data.update(details)
        
        # Filtrar valores nulos
        data = {k: v for k, v in data.items() if v is not None}
        
        # Construir query
        columns = list(data.keys())
        placeholders = ['?' for _ in columns]
        values = [data[col] for col in columns]
        
        query = f'''
            INSERT OR REPLACE INTO equipboard_details ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        '''
        
        cursor.execute(query, values)
        
    except Exception as e:
        logger.error(f"Error guardando detalles: {e}")

def process_instruments_details(database_path, force_update=False, limit=None):
    """Procesa los detalles de los instrumentos"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Crear tabla
        create_equipboard_details_table(cursor)
        
        # Obtener instrumentos a procesar
        instruments = get_instruments_to_process(cursor, force_update, limit)
        
        if not instruments:
            logger.info("No hay instrumentos para procesar")
            return
        
        logger.info(f"🚀 Procesando detalles de {len(instruments)} instrumentos")
        
        # Configurar sesión
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        stats = {'processed': 0, 'with_details': 0, 'errors': 0}
        
        for i, (instrument_id, equipment_id, equipment_name, equipment_url) in enumerate(instruments, 1):
            try:
                logger.info(f"[{i}/{len(instruments)}] Procesando: {equipment_name}")
                
                # Extraer detalles
                details = extract_instrument_details(equipment_url, session)
                
                if details:
                    # Guardar detalles
                    save_instrument_details(cursor, instrument_id, equipment_id, equipment_name, equipment_url, details)
                    stats['with_details'] += 1
                    
                    quality = details.get('data_quality_score', 0)
                    logger.info(f"✅ {equipment_name}: Calidad {quality}/100")
                else:
                    logger.warning(f"⚠️ {equipment_name}: Sin detalles extraídos")
                
                stats['processed'] += 1
                
                # Commit cada 10 instrumentos
                if i % 10 == 0:
                    conn.commit()
                    logger.info(f"💾 Progreso guardado: {i}/{len(instruments)}")
                
                # Pausa para no sobrecargar el servidor
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Error procesando {equipment_name}: {e}")
                stats['errors'] += 1
                continue
        
        conn.commit()
        
        logger.info(f"\n=== ESTADÍSTICAS FINALES ===")
        logger.info(f"Instrumentos procesados: {stats['processed']}")
        logger.info(f"Con detalles extraídos: {stats['with_details']}")
        logger.info(f"Errores: {stats['errors']}")
        
    except Exception as e:
        logger.error(f"Error en procesamiento: {e}")
    finally:
        if 'session' in locals():
            session.close()
        if 'conn' in locals():
            conn.close()

def get_details_stats(database_path):
    """Muestra estadísticas de detalles extraídos"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Estadísticas básicas
        cursor.execute("SELECT COUNT(*) FROM equipboard_details")
        total_details = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(data_quality_score) FROM equipboard_details WHERE data_quality_score > 0")
        avg_quality = cursor.fetchone()[0] or 0
        
        print(f"\n=== ESTADÍSTICAS DE DETALLES ===")
        print(f"Total instrumentos con detalles: {total_details}")
        print(f"Calidad promedio: {avg_quality:.1f}/100")
        
        # Distribución de calidad
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN data_quality_score >= 80 THEN 'Excelente (80-100)'
                    WHEN data_quality_score >= 60 THEN 'Buena (60-79)'
                    WHEN data_quality_score >= 40 THEN 'Regular (40-59)'
                    WHEN data_quality_score >= 20 THEN 'Pobre (20-39)'
                    ELSE 'Muy pobre (0-19)'
                END as quality_range,
                COUNT(*) as count
            FROM equipboard_details 
            WHERE data_quality_score > 0
            GROUP BY quality_range
            ORDER BY MIN(data_quality_score) DESC
        """)
        quality_distribution = cursor.fetchall()
        
        print(f"\n--- DISTRIBUCIÓN DE CALIDAD ---")
        for quality_range, count in quality_distribution:
            print(f"{quality_range}: {count}")
        
        # Instrumentos con información de precio
        cursor.execute("SELECT COUNT(*) FROM equipboard_details WHERE min_price IS NOT NULL")
        with_price = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(min_price) FROM equipboard_details WHERE min_price IS NOT NULL")
        avg_price = cursor.fetchone()[0] or 0
        
        print(f"\n--- INFORMACIÓN DE PRECIOS ---")
        print(f"Instrumentos con precio: {with_price}")
        print(f"Precio promedio: ${avg_price:.2f}")
        
        # Instrumentos con reviews
        cursor.execute("SELECT COUNT(*) FROM equipboard_details WHERE total_reviews > 0")
        with_reviews = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(review_score) FROM equipboard_details WHERE review_score IS NOT NULL")
        avg_rating = cursor.fetchone()[0] or 0
        
        print(f"\n--- INFORMACIÓN DE REVIEWS ---")
        print(f"Instrumentos con reviews: {with_reviews}")
        print(f"Calificación promedio: {avg_rating:.1f}/5")
        
        # Top instrumentos por calidad
        cursor.execute("""
            SELECT equipment_name, data_quality_score, min_price, total_reviews
            FROM equipboard_details 
            WHERE data_quality_score > 0
            ORDER BY data_quality_score DESC, total_reviews DESC
            LIMIT 10
        """)
        top_quality = cursor.fetchall()
        
        print(f"\n--- TOP 10 INSTRUMENTOS POR CALIDAD ---")
        for name, quality, price, reviews in top_quality:
            price_str = f"${price:.0f}" if price else "N/A"
            reviews_str = f"{reviews} reviews" if reviews else "Sin reviews"
            print(f"{name}: {quality}/100 | {price_str} | {reviews_str}")
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def search_instrument_details(database_path, search_term):
    """Busca detalles de instrumentos por término"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ed.equipment_name, ed.detailed_description, ed.min_price, 
                   ed.price_tier, ed.total_reviews, ed.review_score,
                   ed.used_by_artists_count, ed.data_quality_score,
                   ed.pros, ed.cons
            FROM equipboard_details ed
            WHERE ed.equipment_name LIKE ? 
            ORDER BY ed.data_quality_score DESC
            LIMIT 10
        """, (f"%{search_term}%",))
        
        results = cursor.fetchall()
        
        if not results:
            print(f"No se encontraron instrumentos que coincidan con '{search_term}'")
            return
        
        print(f"\n=== RESULTADOS PARA '{search_term}' ===")
        
        for result in results:
            (name, desc, price, tier, reviews, rating, artists, quality, pros, cons) = result
            
            print(f"\n🎸 {name}")
            print(f"   📊 Calidad: {quality}/100")
            
            if price:
                print(f"   💰 Precio: ${price:.2f}" + (f" ({tier})" if tier else ""))
            
            if reviews and rating:
                print(f"   ⭐ {rating}/5 ({reviews} reviews)")
            
            if artists:
                print(f"   🎵 Usado por {artists} artistas")
            
            if desc:
                print(f"   📝 {desc[:200]}{'...' if len(desc) > 200 else ''}")
            
            if pros:
                try:
                    pros_list = json.loads(pros)
                    if pros_list:
                        print(f"   ✅ Pros: {', '.join(pros_list[:3])}")
                except:
                    pass
            
            if cons:
                try:
                    cons_list = json.loads(cons)
                    if cons_list:
                        print(f"   ❌ Cons: {', '.join(cons_list[:2])}")
                except:
                    pass
        
    except Exception as e:
        logger.error(f"Error buscando instrumentos: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def export_details_to_json(database_path, output_file):
    """Exporta detalles a archivo JSON"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ed.equipment_name, ed.equipment_url, ed.min_price, ed.price_tier,
                   ed.total_reviews, ed.review_score, ed.used_by_artists_count,
                   ed.detailed_description, ed.specifications, ed.pros, ed.cons,
                   ed.related_artists, ed.genre_usage, ed.data_quality_score
            FROM equipboard_details ed
            WHERE ed.data_quality_score > 0
            ORDER BY ed.data_quality_score DESC
        """)
        
        results = cursor.fetchall()
        
        export_data = []
        for row in results:
            (name, url, price, tier, reviews, rating, artists, desc, specs, 
             pros, cons, related, genres, quality) = row
            
            item = {
                'equipment_name': name,
                'equipment_url': url,
                'min_price': price,
                'price_tier': tier,
                'total_reviews': reviews,
                'review_score': rating,
                'used_by_artists_count': artists,
                'detailed_description': desc,
                'data_quality_score': quality
            }
            
            # Añadir campos JSON si existen
            for field, value in [('specifications', specs), ('pros', pros), 
                               ('cons', cons), ('related_artists', related), 
                               ('genre_usage', genres)]:
                if value:
                    try:
                        item[field] = json.loads(value)
                    except:
                        item[field] = value
            
            export_data.append(item)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exportados {len(export_data)} instrumentos a {output_file}")
        
    except Exception as e:
        logger.error(f"Error exportando datos: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def main(config=None):
    """Función principal"""
    if config is None:
        import argparse
        
        parser = argparse.ArgumentParser(description='Extraer detalles de instrumentos de equipboard.com')
        parser.add_argument('--action', 
                           choices=['extract', 'stats', 'search', 'export'], 
                           default='extract')
        parser.add_argument('--db-path', type=str, default='db/sqlite/musica.sqlite')
        parser.add_argument('--limit', type=int, help='Límite de instrumentos a procesar')
        parser.add_argument('--force-update', action='store_true')
        parser.add_argument('--search-term', type=str, help='Término de búsqueda')
        parser.add_argument('--output', type=str, default='equipboard_details.json')
        
        args = parser.parse_args()
        config = vars(args)
    
    action = config.get('action', 'extract')
    
    if action == 'extract':
        process_instruments_details(
            database_path=config.get('db_path', 'db/sqlite/musica.sqlite'),
            force_update=config.get('force_update', False),
            limit=config.get('limit')
        )
    elif action == 'stats':
        get_details_stats(config.get('db_path', 'db/sqlite/musica.sqlite'))
    elif action == 'search':
        if not config.get('search_term'):
            logger.error("Se requiere --search-term para la acción search")
            return 1
        search_instrument_details(
            config.get('db_path', 'db/sqlite/musica.sqlite'),
            config['search_term']
        )
    elif action == 'export':
        export_details_to_json(
            config.get('db_path', 'db/sqlite/musica.sqlite'),
            config.get('output', 'equipboard_details.json')
        )

if __name__ == "__main__":
    main()