#!/usr/bin/env python3
"""
Script para extraer URLs de instrumentos de las páginas de artistas en equipboard.com
"""
import sqlite3
import time
import re
import logging
from datetime import datetime
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains


# Importaciones opcionales para mejor evasión
try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

try:
    from fake_useragent import UserAgent
    FAKE_UA_AVAILABLE = True
except ImportError:
    FAKE_UA_AVAILABLE = False

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_equipboard_instruments_table(cursor):
    """Crea tabla para almacenar URLs de instrumentos"""
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipboard_instruments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER,
            artist_name TEXT NOT NULL,
            equipment_id TEXT,
            equipment_name TEXT NOT NULL,
            equipment_url TEXT NOT NULL,
            brand TEXT,
            model TEXT,
            equipment_type TEXT,
            extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed BOOLEAN DEFAULT 0,
            
            FOREIGN KEY (artist_id) REFERENCES artists (id),
            UNIQUE(artist_id, equipment_id)
        )''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_instruments_artist ON equipboard_instruments (artist_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_instruments_processed ON equipboard_instruments (processed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipboard_instruments_equipment_id ON equipboard_instruments (equipment_id)')
        
        logger.info("Tabla equipboard_instruments creada/verificada")
        
    except Exception as e:
        logger.error(f"Error creando tabla: {e}")
        raise

# REEMPLAZA tu función setup_selenium_driver con esta versión corregida:

def setup_selenium_driver(headless=True):
    """Configura driver con compatibilidad mejorada"""
    try:
        if UNDETECTED_AVAILABLE:
            options = uc.ChromeOptions()
            logger.info("🔧 Usando undetected-chromedriver")
        else:
            options = Options()
            logger.info("🔧 Usando selenium normal con evasión mejorada")
        
        if headless:
            options.add_argument("--headless=new")
            logger.info("🔇 Modo headless activado")
        else:
            logger.info("🖥️ Modo con interfaz gráfica activado")
        
        # Opciones básicas compatibles con undetected_chromedriver
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        
        # User agent según disponibilidad
        if FAKE_UA_AVAILABLE:
            ua = UserAgent()
            user_agent = ua.random
            logger.info(f"🎭 Usando user agent aleatorio: {user_agent[:50]}...")
        else:
            user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            logger.info("🎭 Usando user agent fijo")
        
        options.add_argument(f'--user-agent={user_agent}')
        
        # Solo aplicar opciones experimentales con selenium normal
        if not UNDETECTED_AVAILABLE:
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
        
        # Crear driver según disponibilidad
        if UNDETECTED_AVAILABLE:
            driver = uc.Chrome(options=options, version_main=None)
        else:
            driver = webdriver.Chrome(options=options)
        
        # Scripts de evasión solo con selenium normal
        if not UNDETECTED_AVAILABLE:
            stealth_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})",
                "window.chrome = {runtime: {}}"
            ]
            
            for script in stealth_scripts:
                try:
                    driver.execute_script(script)
                except:
                    pass
        
        driver.set_page_load_timeout(45)
        
        if UNDETECTED_AVAILABLE:
            logger.info("✅ Driver undetected-chrome configurado exitosamente")
        else:
            logger.info("✅ Driver selenium mejorado configurado exitosamente")
        
        return driver
        
    except Exception as e:
        logger.error(f"Error configurando driver: {e}")
        
        # Fallback: intentar con opciones mínimas
        try:
            logger.info("🔄 Intentando configuración fallback...")
            
            if UNDETECTED_AVAILABLE:
                options = uc.ChromeOptions()
                if headless:
                    options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                driver = uc.Chrome(options=options)
            else:
                options = Options()
                if headless:
                    options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                driver = webdriver.Chrome(options=options)
            
            driver.set_page_load_timeout(45)
            logger.info("✅ Driver fallback configurado exitosamente")
            return driver
            
        except Exception as fallback_error:
            logger.error(f"Error en configuración fallback: {fallback_error}")
            return None


def handle_cloudflare_improved(driver, max_wait=30):
    """Versión mejorada para detectar Cloudflare con menos falsos positivos"""
    try:
        logger.info("🔍 Verificando Cloudflare...")
        
        # Esperar tiempo inicial más corto
        time.sleep(random.uniform(2, 3))
        
        # Indicadores más específicos de Cloudflare
        cloudflare_indicators = [
            "checking your browser before accessing",
            "please wait while we check your browser",
            "verifying you are human",
            "ray id:",
            "cf-browser-verification",
            "challenge-platform",
            "cf-challenge",
            "turnstile-wrapper",
            "cloudflare-static"
        ]
        
        # Indicadores positivos de que la página está bien
        positive_indicators = [
            "equipboard",
            "gear",
            "equipment", 
            "instruments",
            "uses",
            "artist",
            "setup",
            "studio"
        ]
        
        wait_time = 0
        checks_count = 0
        
        while wait_time < max_wait and checks_count < 5:
            try:
                page_source = driver.page_source.lower()
                current_url = driver.current_url.lower()
                page_title = driver.title.lower()
                
                # Verificar primero si hay contenido positivo
                positive_content = any(indicator in page_source for indicator in positive_indicators)
                positive_title = any(indicator in page_title for indicator in positive_indicators)
                valid_url = 'equipboard.com/pros/' in current_url
                
                # Si hay contenido positivo y URL válida, no es Cloudflare
                if (positive_content or positive_title) and valid_url:
                    logger.info("✅ Contenido válido detectado, no hay Cloudflare")
                    return True
                
                # Solo buscar Cloudflare si no hay contenido positivo
                if not positive_content:
                    is_cloudflare = any(indicator in page_source for indicator in cloudflare_indicators)
                    
                    # Verificaciones adicionales más específicas
                    title_check = any(cf_term in page_title for cf_term in ['checking', 'verifying', 'cloudflare'])
                    
                    if is_cloudflare or title_check:
                        logger.warning(f"☁️ Cloudflare confirmado, esperando... {wait_time}s/{max_wait}s")
                        
                        # Solo simular actividad cada 4 checks para no ser tan obvio
                        if checks_count % 4 == 0:
                            simulate_human_behavior(driver)
                        
                        sleep_time = random.uniform(4, 7)
                        time.sleep(sleep_time)
                        wait_time += sleep_time
                        checks_count += 1
                        continue
                
                # Si llegamos aquí, verificar longitud mínima del contenido
                if len(page_source) > 1000:
                    logger.info("✅ Página con contenido suficiente, asumiendo válida")
                    return True
                else:
                    logger.warning("⚠️ Página con poco contenido, esperando más carga...")
                    time.sleep(3)
                    wait_time += 3
                    checks_count += 1
                        
            except Exception as e:
                logger.warning(f"Error verificando página: {e}")
                time.sleep(2)
                wait_time += 2
                checks_count += 1
        
        # Si salimos del bucle, verificar una última vez
        try:
            final_source = driver.page_source.lower()
            final_positive = any(indicator in final_source for indicator in positive_indicators)
            
            if final_positive:
                logger.info("✅ Contenido válido encontrado en verificación final")
                return True
            else:
                logger.error("❌ No se encontró contenido válido después de esperar")
                return False
        except:
            logger.error("❌ Error en verificación final")
            return False
        
    except Exception as e:
        logger.error(f"Error manejando Cloudflare: {e}")
        return False


def verify_page_content(driver, artist_name, max_wait=10):
    """Verifica que la página cargada sea válida para el artista"""
    try:
        logger.info(f"🔍 Verificando contenido para {artist_name}")
        
        wait_time = 0
        while wait_time < max_wait:
            try:
                page_source = driver.page_source.lower()
                current_url = driver.current_url.lower()
                page_title = driver.title.lower()
                
                # Verificar si es una página de error o redirección
                error_indicators = [
                    'sign up for equipboard',
                    'create your equipboard account',
                    'join equipboard',
                    'page not found',
                    '404',
                    'artist not found',
                    'no gear found'
                ]
                
                if any(indicator in page_source for indicator in error_indicators):
                    logger.warning(f"⚠️ Página de error detectada para {artist_name}")
                    return False
                
                # Verificar contenido positivo más específico
                gear_indicators = [
                    'uses this',
                    'gear',
                    'equipment',
                    'instruments',
                    'setup',
                    'studio gear',
                    'bass',
                    'guitar',
                    'synth',
                    'drums',
                    'microphone',
                    'amp'
                ]
                
                has_gear_content = any(indicator in page_source for indicator in gear_indicators)
                
                # Verificar que no sea página genérica
                generic_indicators = [
                    'select an artist',
                    'browse artists',
                    'find your favorite artist',
                    'search for artists'
                ]
                
                is_generic = any(indicator in page_source for indicator in generic_indicators)
                
                if has_gear_content and not is_generic:
                    logger.info(f"✅ Contenido válido confirmado para {artist_name}")
                    return True
                elif is_generic:
                    logger.warning(f"⚠️ Página genérica detectada para {artist_name}")
                    return False
                else:
                    # Dar más tiempo para que cargue
                    time.sleep(2)
                    wait_time += 2
                    
            except Exception as e:
                logger.warning(f"Error verificando contenido: {e}")
                time.sleep(1)
                wait_time += 1
        
        # Verificación final menos estricta
        try:
            final_source = driver.page_source.lower()
            # Si al menos tiene contenido de equipboard y no es error, aceptar
            if 'equipboard' in final_source and len(final_source) > 2000:
                logger.info(f"✅ Página aceptada con verificación relajada para {artist_name}")
                return True
        except:
            pass
        
        logger.warning(f"⚠️ No se pudo verificar contenido válido para {artist_name}")
        return False
        
    except Exception as e:
        logger.error(f"Error verificando contenido: {e}")
        return False



def debug_page_content(driver, artist_name):
    """Función de debug para inspeccionar el contenido de la página"""
    try:
        logger.info(f"🔍 DEBUG: Inspeccionando página para {artist_name}")
        
        page_source = driver.page_source
        current_url = driver.current_url
        page_title = driver.title
        
        logger.info(f"URL actual: {current_url}")
        logger.info(f"Título: {page_title}")
        logger.info(f"Longitud del contenido: {len(page_source)} caracteres")
        
        # Buscar palabras clave importantes
        keywords_to_check = [
            'cloudflare', 'checking', 'verifying', 'equipboard', 
            'gear', 'equipment', 'sign up', 'login', 'error'
        ]
        
        found_keywords = []
        for keyword in keywords_to_check:
            if keyword in page_source.lower():
                found_keywords.append(keyword)
        
        logger.info(f"Palabras clave encontradas: {found_keywords}")
        
        # Mostrar primeras líneas del contenido
        lines = page_source.split('\n')[:10]
        logger.info("Primeras líneas del HTML:")
        for i, line in enumerate(lines):
            logger.info(f"  {i+1}: {line.strip()[:100]}")
        
    except Exception as e:
        logger.error(f"Error en debug de página: {e}")








def smart_page_load(driver, url, artist_name, max_retries=2, debug_mode=False):
    """Carga de página con validación de contenido y debug opcional"""
    validated_url = validate_and_fix_url(url, artist_name)
    if not validated_url:
        logger.error(f"❌ URL no válida para {artist_name}: {url}")
        return False
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🌐 Cargando {validated_url} (intento {attempt + 1}/{max_retries})")
            
            if attempt > 0:
                delay = random.uniform(3, 7)
                logger.info(f"⏳ Delay entre intentos: {delay:.1f}s...")
                time.sleep(delay)
            
            driver.get(validated_url)
            
            # Debug opcional
            if debug_mode:
                debug_page_content(driver, artist_name)
            
            # Manejar Cloudflare con detección mejorada
            if not handle_cloudflare_improved(driver, max_wait=10):
                logger.warning(f"⚠️ Problema con Cloudflare en intento {attempt + 1}")
                continue
            
            # Verificar contenido
            if verify_page_content(driver, artist_name):
                logger.info("✅ Página cargada y validada exitosamente")
                return True
            else:
                logger.warning(f"⚠️ Contenido no válido en intento {attempt + 1}")
                continue
                
        except Exception as e:
            logger.error(f"❌ Error en intento {attempt + 1}: {e}")
            continue
    
    logger.error(f"❌ Falló carga de {validated_url} después de {max_retries} intentos")
    return False




def extract_instruments_data(driver, artist_name):
    """Extrae los datos de instrumentos filtrand elementos de navegación"""
    instruments = []
    processed_ids = set()
    
    try:
        # Usar selectores específicos para equipboard
        gear_selectors = [
            "a[href*='/gear/']",
            "a[href*='/items/']"
        ]
        
        for selector in gear_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                logger.info(f"🔍 Selector '{selector}': {len(elements)} elementos encontrados")
                
                for element in elements:
                    try:
                        gear_href = element.get_attribute('href')
                        equipment_name = element.text.strip()
                        
                        # Extraer texto del elemento si está vacío
                        if not equipment_name:
                            try:
                                equipment_name = element.get_attribute('title') or ""
                                if not equipment_name:
                                    child = element.find_element(By.CSS_SELECTOR, "span, div, h1, h2, h3, h4")
                                    equipment_name = child.text.strip()
                            except:
                                continue
                        
                        if not gear_href or not equipment_name or len(equipment_name) < 3:
                            continue
                        
                        # Filtrar elementos de navegación y botones "Add gear"
                        nav_terms = [
                            'gear', 'equipment', 'view all', 'more', 'add gear', 'show more', 
                            'load more', 'add music gear', 'new', 'add', 'create', 'submit'
                        ]
                        if equipment_name.lower() in nav_terms:
                            continue
                        
                        # Filtrar URLs que contengan '/new', '/add' o '/create'
                        if any(term in gear_href.lower() for term in ['/new', '/add', '/create', '/submit']):
                            logger.debug(f"⏭️ Saltando URL de creación: {gear_href}")
                            continue
                        
                        # Extraer ID del equipo
                        gear_match = re.search(r'/(gear|items)/([^/?#]+)', gear_href)
                        if not gear_match:
                            continue
                        
                        equipment_id = gear_match.group(2)
                        
                        # Filtrar IDs que sean claramente de navegación
                        if equipment_id.lower() in ['new', 'add', 'create', 'submit']:
                            continue
                        
                        if equipment_id in processed_ids:
                            continue
                        processed_ids.add(equipment_id)
                        
                        # Extraer información básica
                        brand, model = parse_brand_model_simple(equipment_name)
                        equipment_type = infer_equipment_type_simple(equipment_name)
                        
                        instrument_data = {
                            'artist_name': artist_name,
                            'equipment_id': equipment_id,
                            'equipment_name': equipment_name,
                            'equipment_url': gear_href,
                            'brand': brand,
                            'model': model,
                            'equipment_type': equipment_type
                        }
                        
                        instruments.append(instrument_data)
                        
                    except Exception as e:
                        logger.debug(f"Error procesando elemento individual: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Error con selector {selector}: {e}")
                continue
        
        # Eliminar duplicados por nombre + tipo
        unique_instruments = []
        seen_combinations = set()
        
        for instrument in instruments:
            combo_key = f"{instrument['equipment_name'].lower()}-{instrument['equipment_type']}"
            if combo_key not in seen_combinations:
                seen_combinations.add(combo_key)
                unique_instruments.append(instrument)
        
        logger.info(f"🎯 Instrumentos únicos extraídos: {len(unique_instruments)}")
        return unique_instruments
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo datos de instrumentos: {e}")
        return []


def restart_driver(driver, headless=True):
    """Reinicia el driver para evitar que se cuelgue"""
    try:
        logger.info("🔄 Reiniciando driver para evitar cuelgues...")
        
        # Cerrar driver actual
        if driver:
            try:
                driver.quit()
                logger.info("✅ Driver anterior cerrado")
            except:
                pass
        
        # Esperar un poco antes de crear nuevo driver
        time.sleep(random.uniform(3, 5))
        
        # Crear nuevo driver
        new_driver = setup_selenium_driver(headless=headless)
        if new_driver:
            logger.info("✅ Nuevo driver creado exitosamente")
            return new_driver
        else:
            logger.error("❌ Error creando nuevo driver")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error reiniciando driver: {e}")
        return None



def extract_instruments_from_page(driver, artist_name, artist_url):
    """Versión simplificada sin scrolls excesivos"""
    try:
        logger.info(f"🎵 Extrayendo instrumentos de {artist_url}")
        
        # Cargar página con estrategia mejorada
        if not smart_page_load(driver, artist_url, artist_name, debug_mode=False):
            logger.error(f"❌ No se pudo cargar la página para {artist_name}")
            return []
        
        # Verificar contenido válido básico
        try:
            WebDriverWait(driver, 10).until(
                lambda d: 'equipboard' in d.page_source.lower() and len(d.page_source) > 2000
            )
        except:
            logger.warning(f"⚠️ Contenido de equipboard no detectado para {artist_name}")
            return []
        
        # Pausa inicial mínima
        time.sleep(random.uniform(2, 3))
        
        # Contar elementos iniciales
        initial_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='/gear/'], a[href*='/items/']"))
        logger.info(f"🎸 Instrumentos iniciales detectados: {initial_count}")
        
        # Manejar LOAD MORE de forma conservadora
        if initial_count > 0:
            load_more_clicks = handle_load_more_button(driver, max_clicks=8)
        else:
            logger.warning(f"⚠️ No se detectaron instrumentos iniciales")
            load_more_clicks = 0
        
        # Contar elementos finales
        final_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='/gear/'], a[href*='/items/']"))
        logger.info(f"🎸 Resultado final: {initial_count} → {final_count} instrumentos")
        
        # Extraer instrumentos
        instruments = extract_instruments_data(driver, artist_name)
        
        logger.info(f"🎯 Extracción completada: {len(instruments)} instrumentos para {artist_name}")
        return instruments
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo instrumentos para {artist_name}: {e}")
        return []



def parse_brand_model_simple(equipment_name):
    """Extrae marca y modelo de forma simple"""
    try:
        # Lista de marcas conocidas más comunes
        known_brands = [
            # Software/DAW
            'Apple Logic', 'Apple', 'Ableton', 'Native Instruments', 'FabFilter', 'Waves',
            
            # Guitarras
            'Fender', 'Gibson', 'Martin', 'Taylor', 'Yamaha', 'Ibanez', 'PRS', 'Gretsch',
            'Rickenbacker', 'Epiphone', 'Squier', 'ESP', 'Jackson',
            
            # Amplificadores
            'Marshall', 'Fender', 'Vox', 'Orange', 'Mesa Boogie', 'Ampeg', 'Roland',
            'Peavey', 'Blackstar',
            
            # Efectos
            'Boss', 'Ibanez', 'Electro-Harmonix', 'MXR', 'TC Electronic', 'Strymon',
            
            # Sintetizadores
            'Korg', 'Moog', 'Roland', 'Sequential', 'Arturia',
            
            # Otros
            'Shure', 'AKG', 'Neumann', 'DW', 'Pearl'
        ]
        
        # Buscar marca al inicio del nombre
        for brand in sorted(known_brands, key=len, reverse=True):
            if equipment_name.lower().startswith(brand.lower()):
                model = equipment_name[len(brand):].strip()
                model = re.sub(r'^[\s\-–—]+', '', model)
                return brand, model
        
        # Si no encuentra marca, usar primera palabra
        words = equipment_name.split()
        if len(words) >= 2:
            return words[0], ' '.join(words[1:])
        
        return equipment_name, ""
        
    except Exception as e:
        return equipment_name, ""

def infer_equipment_type_simple(equipment_name):
    """Infiere el tipo de equipo de forma simple"""
    name_lower = equipment_name.lower()
    
    type_patterns = {
        'electric_guitar': ['guitar', 'strat', 'telecaster', 'les paul'],
        'bass_guitar': ['bass'],
        'amplifier': ['amp', 'amplifier', 'head', 'combo'],
        'effect_pedal': ['pedal', 'distortion', 'overdrive', 'delay', 'reverb'],
        'synthesizer': ['synth', 'synthesizer', 'moog'],
        'software': ['logic', 'ableton', 'pro tools', 'plugin', 'vst'],
        'microphone': ['microphone', 'mic', 'sm57', 'sm58'],
        'drums': ['drums', 'kit', 'snare', 'cymbal']
    }
    
    for eq_type, patterns in type_patterns.items():
        for pattern in patterns:
            if pattern in name_lower:
                return eq_type
    
    return 'unknown'

def get_artists_to_process(cursor, force_update=False, limit=None):
    """Obtiene artistas que necesitan procesamiento de instrumentos"""
    if force_update:
        # Si force_update, procesar todos los artistas con URL válida de equipboard_artists
        query = """
            SELECT ea.artist_id, ea.artist_name, ea.equipboard_url 
            FROM equipboard_artists ea 
            WHERE ea.status = 'found' 
            AND ea.equipboard_url IS NOT NULL
            AND ea.equipboard_url != ''
            AND ea.equipboard_url NOT LIKE '%/pros/select%'
            AND ea.equipboard_url NOT LIKE '%signup%'
            AND ea.equipboard_url NOT LIKE '%login%'
        """
    else:
        # Solo procesar artistas que no han sido procesados para instrumentos
        query = """
            SELECT ea.artist_id, ea.artist_name, ea.equipboard_url 
            FROM equipboard_artists ea 
            LEFT JOIN (
                SELECT artist_id, COUNT(*) as instrument_count 
                FROM equipboard_instruments 
                GROUP BY artist_id
            ) ei ON ea.artist_id = ei.artist_id 
            WHERE ea.status = 'found' 
            AND ea.equipboard_url IS NOT NULL 
            AND ea.equipboard_url != ''
            AND ea.equipboard_url NOT LIKE '%/pros/select%'
            AND ea.equipboard_url NOT LIKE '%signup%'
            AND ea.equipboard_url NOT LIKE '%login%'
            AND ei.instrument_count IS NULL
        """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    return cursor.fetchall()

def inspect_equipboard_urls(database_path, limit=10):
    """Inspecciona las URLs de equipboard en la base de datos"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Verificar tabla equipboard_artists
        cursor.execute("SELECT COUNT(*) FROM equipboard_artists")
        total_artists = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM equipboard_artists 
            WHERE equipboard_url IS NOT NULL AND equipboard_url != ''
        """)
        artists_with_urls = cursor.fetchone()[0]
        
        print(f"=== INSPECCIÓN DE URLs EQUIPBOARD ===")
        print(f"Total artistas en equipboard_artists: {total_artists}")
        print(f"Artistas con URLs: {artists_with_urls}")
        
        # Mostrar ejemplos de URLs
        cursor.execute("""
            SELECT artist_name, equipboard_url, status 
            FROM equipboard_artists 
            WHERE equipboard_url IS NOT NULL 
            AND equipboard_url != ''
            LIMIT ?
        """, (limit,))
        
        sample_urls = cursor.fetchall()
        
        print(f"\n--- MUESTRA DE URLs ({len(sample_urls)} primeras) ---")
        for artist_name, url, status in sample_urls:
            print(f"{artist_name}: {url} (status: {status})")
        
        # Verificar URLs problemáticas
        cursor.execute("""
            SELECT COUNT(*) FROM equipboard_artists 
            WHERE equipboard_url LIKE '%/pros/select%' 
            OR equipboard_url LIKE '%signup%' 
            OR equipboard_url LIKE '%login%'
        """)
        problematic_urls = cursor.fetchone()[0]
        
        print(f"\n--- ANÁLISIS DE URLs ---")
        print(f"URLs problemáticas (select/signup/login): {problematic_urls}")
        
        # URLs válidas para procesamiento
        cursor.execute("""
            SELECT COUNT(*) FROM equipboard_artists 
            WHERE equipboard_url IS NOT NULL 
            AND equipboard_url != ''
            AND equipboard_url NOT LIKE '%/pros/select%'
            AND equipboard_url NOT LIKE '%signup%'
            AND equipboard_url NOT LIKE '%login%'
            AND status = 'found'
        """)
        valid_urls = cursor.fetchone()[0]
        
        print(f"URLs válidas para procesamiento: {valid_urls}")
        
        # Verificar si hay instrumentos ya extraídos
        cursor.execute("SELECT COUNT(*) FROM equipboard_instruments")
        total_instruments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT artist_id) FROM equipboard_instruments")
        artists_with_instruments = cursor.fetchone()[0]
        
        print(f"\n--- ESTADO DE INSTRUMENTOS ---")
        print(f"Total instrumentos extraídos: {total_instruments}")
        print(f"Artistas con instrumentos: {artists_with_instruments}")
        
        # Artistas pendientes de procesar
        cursor.execute("""
            SELECT COUNT(*) FROM equipboard_artists ea
            LEFT JOIN (
                SELECT DISTINCT artist_id 
                FROM equipboard_instruments
            ) ei ON ea.artist_id = ei.artist_id 
            WHERE ea.status = 'found' 
            AND ea.equipboard_url IS NOT NULL 
            AND ea.equipboard_url != ''
            AND ea.equipboard_url NOT LIKE '%/pros/select%'
            AND ea.equipboard_url NOT LIKE '%signup%'
            AND ea.equipboard_url NOT LIKE '%login%'
            AND ei.artist_id IS NULL
        """)
        pending_artists = cursor.fetchone()[0]
        
        print(f"Artistas pendientes de procesar: {pending_artists}")
        
    except Exception as e:
        print(f"Error inspeccionando URLs: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


def debug_urls(database_path):
    """Función de debugging para inspeccionar URLs"""
    print("=== MODO DEBUG: INSPECCIONANDO URLs ===")
    inspect_equipboard_urls(database_path, limit=20)
    
    # Mostrar URLs problemáticas específicas
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT artist_name, equipboard_url 
            FROM equipboard_artists 
            WHERE equipboard_url LIKE '%/pros/select%' 
            OR equipboard_url LIKE '%signup%'
            OR equipboard_url LIKE '%login%'
            LIMIT 10
        """)
        
        problematic = cursor.fetchall()
        if problematic:
            print(f"\n--- URLs PROBLEMÁTICAS ENCONTRADAS ---")
            for artist, url in problematic:
                print(f"{artist}: {url}")
        
    except Exception as e:
        print(f"Error en debug: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


def save_instruments(cursor, artist_id, instruments):
    """Guarda los instrumentos en la base de datos"""
    try:
        for instrument in instruments:
            cursor.execute('''
                INSERT OR REPLACE INTO equipboard_instruments 
                (artist_id, artist_name, equipment_id, equipment_name, equipment_url, 
                 brand, model, equipment_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                artist_id,
                instrument['artist_name'],
                instrument['equipment_id'],
                instrument['equipment_name'],
                instrument['equipment_url'],
                instrument['brand'],
                instrument['model'],
                instrument['equipment_type']
            ))
        
    except Exception as e:
        logger.error(f"Error guardando instrumentos: {e}")



def process_artists_instruments(database_path, force_update=False, limit=None, headless=True):
    """Versión con reinicio de driver cada 5 artistas"""
    driver = None
    try:
        logger.info("🔄 Iniciando process_artists_instruments")
        
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        logger.info("✅ Conexión a base de datos establecida")
        
        create_equipboard_instruments_table(cursor)
        logger.info("✅ Tabla equipboard_instruments verificada")
        
        artists = get_artists_to_process(cursor, force_update, limit)
        logger.info(f"✅ Obtenidos {len(artists)} artistas para procesar")
        
        if not artists:
            logger.info("ℹ️ No hay artistas para procesar instrumentos")
            return
        
        logger.info(f"🚀 Procesando instrumentos de {len(artists)} artistas")
        
        # Configurar driver inicial
        logger.info("🔧 Configurando driver inicial...")
        driver = setup_selenium_driver(headless=headless)
        if not driver:
            logger.error("❌ No se pudo crear driver inicial")
            return
        
        logger.info("✅ Driver inicial configurado exitosamente")
        
        stats = {'processed': 0, 'total_instruments': 0, 'errors': 0}
        
        for i, (artist_id, artist_name, artist_url) in enumerate(artists, 1):
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"[{i}/{len(artists)}] 🎵 PROCESANDO: {artist_name}")
                logger.info(f"URL: {artist_url}")
                logger.info(f"Artist ID: {artist_id}")
                logger.info(f"{'='*60}")
                
                # Reiniciar driver cada 5 artistas para evitar cuelgues
                if i > 1 and (i - 1) % 5 == 0:
                    logger.info(f"🔄 Reiniciando driver después de {i-1} artistas...")
                    driver = restart_driver(driver, headless)
                    if not driver:
                        logger.error("❌ No se pudo reiniciar driver")
                        break
                
                # Verificar URL antes de continuar
                if not artist_url or artist_url.strip() == '':
                    logger.error(f"❌ URL vacía para {artist_name}")
                    continue
                
                logger.info(f"🌐 Iniciando extracción para {artist_name}")
                
                # Extraer instrumentos
                instruments = extract_instruments_from_page(driver, artist_name, artist_url)
                
                if instruments:
                    logger.info(f"💾 Guardando {len(instruments)} instrumentos...")
                    save_instruments(cursor, artist_id, instruments)
                    stats['total_instruments'] += len(instruments)
                    logger.info(f"✅ {artist_name}: {len(instruments)} instrumentos guardados")
                else:
                    logger.warning(f"⚠️ {artist_name}: No se encontraron instrumentos")
                
                stats['processed'] += 1
                
                # Commit cada 3 artistas
                if i % 3 == 0:
                    conn.commit()
                    logger.info(f"💾 Progreso guardado: {i}/{len(artists)}")
                
                # Pausa entre artistas (más larga después de reinicio)
                if (i - 1) % 5 == 0 and i > 1:
                    delay = random.uniform(5, 10)  # Pausa más larga después de reinicio
                else:
                    delay = random.uniform(1, 5)  # Pausa normal
                
                logger.info(f"⏳ Pausa de {delay:.1f}s antes del siguiente artista...")
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"❌ Error procesando {artist_name}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                stats['errors'] += 1
                
                # Pausa extra en caso de error
                time.sleep(random.uniform(15, 25))
                continue
        
        conn.commit()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"=== ESTADÍSTICAS FINALES ===")
        logger.info(f"Artistas procesados: {stats['processed']}")
        logger.info(f"Total instrumentos: {stats['total_instruments']}")
        logger.info(f"Errores: {stats['errors']}")
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"❌ Error en procesamiento principal: {e}")
        import traceback
        logger.error(f"Traceback completo: {traceback.format_exc()}")
    finally:
        if driver:
            try:
                logger.info("🔄 Cerrando driver...")
                driver.quit()
                logger.info("✅ Driver cerrado")
            except:
                pass
        if 'conn' in locals():
            conn.close()
            logger.info("✅ Conexión a BD cerrada")

def simulate_human_behavior(driver):
    """Comportamiento humano muy simplificado"""
    try:
        # Solo un scroll aleatorio pequeño
        scroll_amount = random.randint(200, 500)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(1, 2))
        
    except Exception as e:
        logger.debug(f"Error simulando comportamiento: {e}")

def check_load_more_exists(driver):
    """Verifica rápidamente si existe botón LOAD MORE"""
    try:
        xpath_patterns = [
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
            "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
        ]
        
        for xpath in xpath_patterns:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                return True
        
        return False
        
    except Exception:
        return False

def perform_complete_scroll(driver, max_scrolls=20):
    """Realiza scroll completo hasta el final de la página"""
    try:
        logger.info("📜 Iniciando scroll completo de la página...")
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        no_change_count = 0
        
        while scroll_count < max_scrolls and no_change_count < 2:
            # Scroll grande hacia abajo
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Esperar que cargue contenido
            time.sleep(random.uniform(2, 4))
            
            # Verificar si la altura cambió (nuevo contenido cargado)
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height > last_height:
                logger.info(f"📈 Nuevo contenido cargado: {last_height} → {new_height}")
                last_height = new_height
                no_change_count = 0
            else:
                no_change_count += 1
                logger.info(f"⏸️ Sin cambio de altura ({no_change_count}/2)")
            
            scroll_count += 1
            
            # Scroll intermedio para simular lectura
            if scroll_count % 3 == 0:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
                time.sleep(random.uniform(1, 2))
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        logger.info(f"📜 Scroll completado: {scroll_count} scrolls realizados")
        return scroll_count
        
    except Exception as e:
        logger.error(f"Error en scroll completo: {e}")
        return 0

# REEMPLAZA tu función handle_load_more_button con esta versión mejorada:

def handle_load_more_button(driver, max_clicks=20):
    """Versión mejorada con scroll más agresivo"""
    clicks_count = 0
    no_progress_count = 0
    
    try:
        logger.info("🔄 Buscando botones LOAD MORE...")
        
        # Hacer scroll completo primero para cargar contenido inicial
        perform_complete_scroll(driver, max_scrolls=5)
        
        while clicks_count < max_clicks and no_progress_count < 3:
            # Scroll hasta el final antes de buscar botón
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 3))
            
            load_more_button = None
            xpath_patterns = [
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
                "//button[contains(@class, 'load') or contains(@class, 'more')]",
                "//div[contains(@class, 'load-more')]//button",
                "//div[contains(@class, 'show-more')]//button",
            ]
            
            for xpath in xpath_patterns:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if (element.is_displayed() and element.is_enabled() and 
                            element.size['height'] > 0 and element.size['width'] > 0):
                            load_more_button = element
                            break
                    if load_more_button:
                        break
                except Exception:
                    continue
            
            if not load_more_button:
                logger.info(f"🔚 No más botones LOAD MORE (clicks: {clicks_count})")
                break
            
            try:
                current_gear_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='/gear/'], a[href*='/items/']"))
                
                # Scroll hasta el botón con más precisión
                driver.execute_script("""
                    arguments[0].scrollIntoView({
                        behavior: 'smooth',
                        block: 'center'
                    });
                """, load_more_button)
                time.sleep(random.uniform(2, 3))
                
                # Hover antes del click
                try:
                    ActionChains(driver).move_to_element(load_more_button).pause(random.uniform(0.5, 1.0)).perform()
                except:
                    pass
                
                # Click con múltiples métodos de fallback
                click_success = False
                for method in ['click', 'js_click', 'action_click']:
                    try:
                        if method == 'click':
                            load_more_button.click()
                        elif method == 'js_click':
                            driver.execute_script("arguments[0].click();", load_more_button)
                        elif method == 'action_click':
                            ActionChains(driver).click(load_more_button).perform()
                        
                        click_success = True
                        break
                    except Exception as e:
                        logger.debug(f"Método {method} falló: {e}")
                        continue
                
                if not click_success:
                    logger.warning("❌ No se pudo hacer click en LOAD MORE")
                    break
                
                clicks_count += 1
                logger.info(f"🔄 Clic #{clicks_count} en LOAD MORE")
                
                # Espera más larga para cargar contenido
                wait_time = random.uniform(4, 8)
                time.sleep(wait_time)
                
                # Scroll agresivo después del click para cargar todo
                perform_complete_scroll(driver, max_scrolls=3)
                
                # Verificar progreso
                new_gear_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='/gear/'], a[href*='/items/']"))
                
                if new_gear_count > current_gear_count:
                    logger.info(f"📈 Contenido cargado: {current_gear_count} → {new_gear_count}")
                    no_progress_count = 0
                else:
                    no_progress_count += 1
                    logger.warning(f"⚠️ Sin progreso #{no_progress_count}/3")
                    
                    # Intentar scroll más agresivo si no hay progreso
                    if no_progress_count < 3:
                        logger.info("🚀 Intentando scroll más agresivo...")
                        for _ in range(5):
                            driver.execute_script("window.scrollBy(0, 1000);")
                            time.sleep(1)
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Error procesando botón LOAD MORE: {e}")
                break
        
        # Scroll final completo para asegurar todo cargado
        logger.info("📜 Realizando scroll final completo...")
        perform_complete_scroll(driver, max_scrolls=10)
        
        logger.info(f"🎯 LOAD MORE completado: {clicks_count} clics realizados")
        return clicks_count
        
    except Exception as e:
        logger.error(f"❌ Error en manejo de LOAD MORE: {e}")
        return clicks_count

# MODIFICA la función extract_instruments_from_page_debug para incluir mejor scroll:

def extract_instruments_from_page_debug(driver, artist_name, artist_url):
    """Versión simplificada con scroll mínimo necesario"""
    try:
        logger.info(f"🎵 [DEBUG] Iniciando extracción para {artist_name}")
        
        # Cargar página
        if not smart_page_load_debug(driver, artist_url, artist_name):
            logger.error(f"❌ [DEBUG] smart_page_load falló para {artist_name}")
            return []
        
        logger.info(f"✅ [DEBUG] Página cargada exitosamente")
        
        # Un solo scroll inicial hasta el final
        logger.info(f"📜 [DEBUG] Scroll inicial hasta el final...")
        perform_single_scroll_to_bottom(driver)
        
        # Comportamiento humano mínimo
        time.sleep(random.uniform(2, 3))
        
        # Contar elementos iniciales
        initial_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='/gear/'], a[href*='/items/']"))
        logger.info(f"🎸 [DEBUG] Instrumentos iniciales detectados: {initial_count}")
        
        # Manejar LOAD MORE (simplificado)
        if initial_count > 0:
            load_more_clicks = handle_load_more_button(driver, max_clicks=10)
            logger.info(f"🔄 [DEBUG] Clicks en LOAD MORE realizados: {load_more_clicks}")
        else:
            logger.warning(f"⚠️ [DEBUG] No se detectaron instrumentos iniciales")
            load_more_clicks = 0
        
        # Contar elementos finales
        final_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='/gear/'], a[href*='/items/']"))
        logger.info(f"🎸 [DEBUG] Resultado final: {initial_count} → {final_count} instrumentos")
        
        # Solo extraer si hay elementos
        if final_count > 0:
            instruments = extract_instruments_data(driver, artist_name)
            logger.info(f"🎯 [DEBUG] Instrumentos extraídos: {len(instruments)}")
            return instruments
        else:
            logger.warning(f"⚠️ [DEBUG] No se encontraron elementos para extraer")
            return []
        
    except Exception as e:
        logger.error(f"❌ [DEBUG] Error en extracción: {e}")
        return []



def perform_single_scroll_to_bottom(driver):
    """Hace UN SOLO scroll hasta el final sin repetir"""
    try:
        logger.info("📜 Scroll único hasta el final...")
        
        # Obtener altura actual antes del scroll
        initial_height = driver.execute_script("return document.body.scrollHeight")
        
        # UN SOLO scroll hasta el final
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Esperar a que cargue contenido
        time.sleep(random.uniform(3, 5))
        
        # Verificar si cambió la altura
        final_height = driver.execute_script("return document.body.scrollHeight")
        
        if final_height > initial_height:
            logger.info(f"✅ Scroll completado - Altura: {initial_height} → {final_height}")
        else:
            logger.info(f"✅ Scroll completado - Sin cambio de altura: {initial_height}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en scroll: {e}")
        return False




def smart_page_load_debug(driver, url, artist_name, max_retries=2):
    """Versión con debug detallado de smart_page_load"""
    try:
        logger.info(f"🌐 [DEBUG] Iniciando smart_page_load_debug")
        logger.info(f"🔗 [DEBUG] URL original: {url}")
        
        # Validar URL
        validated_url = validate_and_fix_url(url, artist_name)
        if not validated_url:
            logger.error(f"❌ [DEBUG] URL no válida para {artist_name}: {url}")
            return False
        
        logger.info(f"✅ [DEBUG] URL validada: {validated_url}")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🚀 [DEBUG] Intento {attempt + 1}/{max_retries}")
                logger.info(f"🌐 [DEBUG] Cargando {validated_url}")
                
                if attempt > 0:
                    delay = random.uniform(3, 7)
                    logger.info(f"⏳ [DEBUG] Delay entre intentos: {delay:.1f}s...")
                    time.sleep(delay)
                
                # Intentar cargar la página
                logger.info(f"🔄 [DEBUG] Ejecutando driver.get()...")
                driver.get(validated_url)
                logger.info(f"✅ [DEBUG] driver.get() completado")
                
                # Verificar estado inmediato
                try:
                    immediate_url = driver.current_url
                    immediate_title = driver.title
                    logger.info(f"🌐 [DEBUG] URL inmediata: {immediate_url}")
                    logger.info(f"📄 [DEBUG] Título inmediato: {immediate_title}")
                except Exception as e:
                    logger.error(f"❌ [DEBUG] Error obteniendo estado inmediato: {e}")
                
                # Esperar un poco y verificar nuevamente
                time.sleep(3)
                
                try:
                    delayed_url = driver.current_url
                    delayed_title = driver.title
                    page_length = len(driver.page_source)
                    logger.info(f"🌐 [DEBUG] URL después de 3s: {delayed_url}")
                    logger.info(f"📄 [DEBUG] Título después de 3s: {delayed_title}")
                    logger.info(f"📏 [DEBUG] Longitud del contenido: {page_length}")
                except Exception as e:
                    logger.error(f"❌ [DEBUG] Error en verificación retardada: {e}")
                
                # Manejo simplificado - asumir éxito si llegamos aquí
                logger.info(f"✅ [DEBUG] Carga básica completada en intento {attempt + 1}")
                return True
                
            except Exception as e:
                logger.error(f"❌ [DEBUG] Error en intento {attempt + 1}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                continue
        
        logger.error(f"❌ [DEBUG] Todos los intentos fallaron")
        return False
        
    except Exception as e:
        logger.error(f"❌ [DEBUG] Error en smart_page_load_debug: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def get_instruments_stats(database_path):
    """Muestra estadísticas de instrumentos extraídos"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Estadísticas básicas
        cursor.execute("SELECT COUNT(*) FROM equipboard_instruments")
        total_instruments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT artist_id) FROM equipboard_instruments")
        artists_with_instruments = cursor.fetchone()[0]
        
        print(f"\n=== ESTADÍSTICAS DE INSTRUMENTOS ===")
        print(f"Total instrumentos: {total_instruments}")
        print(f"Artistas con instrumentos: {artists_with_instruments}")
        
        # Top marcas
        cursor.execute("""
            SELECT brand, COUNT(*) as count 
            FROM equipboard_instruments 
            WHERE brand IS NOT NULL AND brand != ''
            GROUP BY brand 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_brands = cursor.fetchall()
        
        print(f"\n--- TOP 10 MARCAS ---")
        for brand, count in top_brands:
            print(f"{brand}: {count}")
        
        # Top tipos de equipo
        cursor.execute("""
            SELECT equipment_type, COUNT(*) as count 
            FROM equipboard_instruments 
            WHERE equipment_type IS NOT NULL 
            GROUP BY equipment_type 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_types = cursor.fetchall()
        
        print(f"\n--- TOP 10 TIPOS DE EQUIPO ---")
        for eq_type, count in top_types:
            print(f"{eq_type}: {count}")
        
        # Artistas con más instrumentos
        cursor.execute("""
            SELECT artist_name, COUNT(*) as count 
            FROM equipboard_instruments 
            GROUP BY artist_name 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_artists = cursor.fetchall()
        
        print(f"\n--- TOP 10 ARTISTAS CON MÁS INSTRUMENTOS ---")
        for artist, count in top_artists:
            print(f"{artist}: {count}")
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def validate_and_fix_url(artist_url, artist_name):
    """Valida y corrige URLs de equipboard"""
    try:
        # URLs problemáticas conocidas
        invalid_patterns = [
            '/pros/select',
            '/sign',
            '/signup',
            '/login',
            '/register'
        ]
        
        # Verificar si la URL es válida
        if not artist_url or any(pattern in artist_url for pattern in invalid_patterns):
            logger.warning(f"⚠️ URL inválida para {artist_name}: {artist_url}")
            
            # Intentar construir URL correcta
            artist_slug = artist_name.lower().replace(' ', '-').replace('(', '').replace(')', '').replace('&', 'and')
            artist_slug = re.sub(r'[^a-z0-9\-]', '', artist_slug)
            corrected_url = f"https://equipboard.com/pros/{artist_slug}"
            
            logger.info(f"🔧 URL corregida: {corrected_url}")
            return corrected_url
        
        # Verificar formato correcto de equipboard
        if 'equipboard.com/pros/' not in artist_url:
            logger.warning(f"⚠️ URL no parece de equipboard: {artist_url}")
            return None
        
        return artist_url
        
    except Exception as e:
        logger.error(f"Error validando URL: {e}")
        return None



def main(config=None):
    """Función principal"""
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.DEBUG)
    if config is None:
        import argparse
        
        parser = argparse.ArgumentParser(description='Extraer instrumentos de equipboard.com')
        parser.add_argument('--action', choices=['extract', 'stats', 'debug'], default='extract')
        parser.add_argument('--db_path', type=str, default='db/sqlite/musica.sqlite')
        parser.add_argument('--limit', type=int, help='Límite de artistas a procesar')
        parser.add_argument('--force-update', action='store_true')
        parser.add_argument('--headless', action='store_true', default=True)
        parser.add_argument('--no-headless', action='store_false', dest='headless')
        
        args = parser.parse_args()
        config = vars(args)
    
    action = config.get('action', 'extract')
    
    if action == 'debug':
        debug_urls(config.get('db_path', 'db/sqlite/musica.sqlite'))
    elif action == 'extract':
        process_artists_instruments(
            database_path=config.get('db_path', 'db/sqlite/musica.sqlite'),
            force_update=config.get('force_update', False),
            limit=config.get('limit'),
            headless=config.get('headless', True)
        )
    elif action == 'stats':
        get_instruments_stats(config.get('db_path', 'db/sqlite/musica.sqlite'))

if __name__ == "__main__":
    main()