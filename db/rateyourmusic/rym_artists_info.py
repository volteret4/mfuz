#!/usr/bin/env python3
"""
Script para extraer información detallada de artistas desde RateYourMusic
Utiliza Playwright para web scraping y actualiza la tabla rym_artists
Compatible con db_creator.py
"""

import asyncio
import sqlite3
import re
import json
import random
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import time

# Variables globales para configuración
CONFIG = {}
INTERACTIVE_MODE = False

def setup_database(db_path):
    """Configura la base de datos añadiendo las columnas necesarias a rym_artists"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Crear tabla si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rym_artists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id TEXT,
            artist_name TEXT,
            rym_url TEXT
        )
    ''')
    
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
        ('top_songs', 'TEXT'),
        ('biography', 'TEXT'),
        ('info_updated', 'TIMESTAMP'),
        ('scraping_status', 'TEXT DEFAULT "pending"'),
        ('error_message', 'TEXT'),
        ('page_title', 'TEXT'),
        ('member_rating', 'TEXT'),
        ('avg_rating', 'TEXT')
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
    """Extrae fecha y lugar de texto como 'June 8, 1977, Atlanta, GA, United States'"""
    if not text:
        return None, None
    
    # Limpiar texto
    text = text.strip()
    
    # Patrones para fechas
    date_patterns = [
        r'(\w+ \d{1,2}, \d{4})',  # June 8, 1977
        r'(\d{1,2} \w+ \d{4})',   # 8 June 1977
        r'(\w+ \d{4})',           # June 1977
        r'(\d{4})'                # 1977
    ]
    
    date = None
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date = match.group(1)
            break
    
    # El lugar es lo que viene después de la fecha
    if date:
        place_match = re.search(rf'{re.escape(date)},?\s*(.+)', text)
        place = place_match.group(1).strip() if place_match else None
    else:
        place = text.strip()
    
    return date, place

def clean_text(text):
    """Limpia texto eliminando espacios extra y caracteres especiales"""
    if not text:
        return None
    
    # Eliminar saltos de línea excesivos y espacios
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

async def create_stealth_context(playwright):
    """Crea un contexto de navegador con configuración stealth avanzada anti-Cloudflare"""
    
    # User agents más recientes y realistas
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    ]
    
    headless_mode = CONFIG.get('headless', False)
    
    # Configuración de args anti-detección
    browser_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-features=TranslateUI',
        '--disable-ipc-flooding-protection',
        '--disable-blink-features=AutomationControlled',
        '--disable-component-extensions-with-background-pages',
        '--disable-default-apps',
        '--disable-extensions',
        '--disable-features=VizDisplayCompositor',
        '--disable-background-networking',
        '--disable-sync',
        '--metrics-recording-only',
        '--no-default-browser-check',
        '--no-first-run',
        '--disable-plugins-discovery',
        '--disable-preconnect',
        '--disable-web-security',
        '--allow-running-insecure-content'
    ]
    
    print(f"🌐 Iniciando navegador stealth (headless: {headless_mode})")
    
    # Detectar qué navegador usar
    browser_options = {
        'headless': headless_mode,
        'args': browser_args,
        'slow_mo': 100 if not headless_mode else 0
    }
    
    # Intentar diferentes opciones según el sistema
    try:
        # Opción 1: Usar Chromium del sistema (Arch Linux)
        import shutil
        chromium_path = shutil.which('chromium') or shutil.which('chromium-browser')
        
        if chromium_path:
            print(f"📍 Usando Chromium del sistema: {chromium_path}")
            browser_options['executable_path'] = chromium_path
            browser = await playwright.chromium.launch(**browser_options)
        else:
            # Opción 2: Chromium de Playwright
            print("📍 Usando Chromium de Playwright")
            browser = await playwright.chromium.launch(**browser_options)
            
    except Exception as e:
        print(f"⚠️ Error con Chromium: {e}")
        try:
            # Opción 3: Firefox como fallback
            print("📍 Intentando con Firefox...")
            browser = await playwright.firefox.launch(**browser_options)
        except Exception as e2:
            print(f"❌ Error con Firefox: {e2}")
            raise Exception("No se pudo iniciar ningún navegador")
    
    # Configuración de contexto con headers realistas
    selected_ua = random.choice(user_agents)
    
    context = await browser.new_context(
        user_agent=selected_ua,
        viewport={'width': 1920, 'height': 1080},
        locale='en-US',
        timezone_id='America/New_York',
        permissions=['geolocation'],
        geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC
        extra_http_headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Linux"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
    )
    
    # Inyectar scripts anti-detección
    await context.add_init_script("""
        // Eliminar webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mockear plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // Mockear languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        // Mockear permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Eliminar automation flags
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        
        // Mockear chrome runtime
        window.chrome = {
            runtime: {},
        };
        
        // Inyectar comportamiento humano en mouse
        let mouseX = 0, mouseY = 0;
        document.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;
        });
        
        // Simular comportamiento humano de scroll
        let lastScrollTime = Date.now();
        document.addEventListener('scroll', () => {
            lastScrollTime = Date.now();
        });
        
        // Ocultar automation traces
        const getParameter = WebGLRenderingContext.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter(parameter);
        };
    """)
    
    # Solo interceptar recursos en modo headless
    if headless_mode:
        await context.route('**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ico}', lambda route: route.abort())
    
    return browser, context

async def handle_cloudflare_challenge(page):
    """Maneja challenges de Cloudflare automáticamente"""
    try:
        # Esperar a que la página cargue
        await page.wait_for_load_state('domcontentloaded', timeout=10000)
        
        # Verificar si hay challenge de Cloudflare
        cloudflare_selectors = [
            'div[class*="cf-browser-verification"]',
            'div[class*="cf-checking"]', 
            '#cf-wrapper',
            '.cf-error-overview',
            'div[data-translate="checking_browser"]',
            '.ray-id'
        ]
        
        for selector in cloudflare_selectors:
            if await page.query_selector(selector):
                print("🛡️ Cloudflare challenge detectado, esperando...")
                
                # Simular comportamiento humano
                await human_behavior(page)
                
                # Esperar hasta 30 segundos para que pase el challenge
                try:
                    await page.wait_for_function(
                        """() => {
                            const cfElements = document.querySelectorAll('[class*="cf-"], #cf-wrapper, .ray-id');
                            return cfElements.length === 0 || document.title.includes('Rate Your Music');
                        }""",
                        timeout=30000
                    )
                    print("✅ Challenge de Cloudflare superado")
                    return True
                except:
                    print("⚠️ Timeout esperando challenge de Cloudflare")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error manejando Cloudflare: {e}")
        return False

async def human_behavior(page):
    """Simula comportamiento humano para evitar detección"""
    try:
        # Movimientos de mouse aleatorios
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1000)
            y = random.randint(100, 800)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Scroll aleatorio
        await page.evaluate(f"window.scrollTo(0, {random.randint(0, 500)})")
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Simular lectura (pausas)
        await asyncio.sleep(random.uniform(1, 3))
        
    except Exception as e:
        print(f"⚠️ Error en comportamiento humano: {e}")

async def scrape_artist_info(page, rym_url):
    """Extrae información detallada de un artista desde su página de RYM"""
    try:
        print(f"🔍 Accediendo a: {rym_url}")
        
        # Navegar a la página
        response = await page.goto(rym_url, wait_until='domcontentloaded', timeout=30000)
        
        if not response or response.status >= 400:
            print(f"❌ Error HTTP: {response.status if response else 'Sin respuesta'}")
            return None
        
        # Manejar Cloudflare si es necesario
        if not await handle_cloudflare_challenge(page):
            print("❌ No se pudo superar el challenge de Cloudflare")
            return None
        
        # Simular comportamiento humano
        await human_behavior(page)
        
        artist_info = {
            'birth_date': None,
            'birth_place': None,
            'death_date': None,
            'death_place': None,
            'notes': None,
            'also_known_as': None,
            'genres': None,
            'top_songs': None,
            'biography': None,
            'page_title': None,
            'member_rating': None,
            'avg_rating': None
        }
        
        # Verificar si la página cargó correctamente
        page_content = await page.content()
        if 'rateyourmusic.com' not in page_content and len(page_content) < 1000:
            print("⚠️ La página parece no haber cargado correctamente")
            return None
        
        # Verificar si hay bloqueo o error
        if 'blocked' in page_content.lower() or 'access denied' in page_content.lower():
            print("🚫 Acceso bloqueado detectado")
            return None
        
        # Obtener título de la página
        try:
            title = await page.title()
            artist_info['page_title'] = clean_text(title)
            print(f"📄 Título de página: {title}")
        except Exception as e:
            print(f"❌ Error obteniendo título: {e}")
        
        # Debug: Mostrar estructura de la página
        try:
            # Buscar elementos característicos de RYM
            artist_name_elem = await page.query_selector('h1, .artist_name_hdr, .page_title')
            if artist_name_elem:
                artist_name = await artist_name_elem.inner_text()
                print(f"🎵 Artista detectado: {artist_name}")
            
            # Verificar si hay tabla de información
            info_table = await page.query_selector('table.artist_info, .artist_info, .info_table')
            if info_table:
                print("📋 Tabla de información encontrada")
            else:
                print("⚠️ No se encontró tabla de información del artista")
        except Exception as e:
            print(f"❌ Error en debug de página: {e}")
        
        # Extraer información de la tabla del artista con múltiples estrategias
        try:
            print("🔍 Buscando información del artista...")
            
            # Estrategia 1: Buscar tabla específica del artista
            info_rows = await page.query_selector_all('table.artist_info tr')
            
            # Estrategia 2: Si no hay tabla, buscar elementos generales
            if not info_rows:
                info_rows = await page.query_selector_all('.artist_info tr, .info_row, div[class*="info"]')
            
            # Estrategia 3: Buscar todo el contenido y parsearlo
            if not info_rows:
                page_text = await page.inner_text('body')
                print("📝 Analizando contenido completo de la página...")
                
                # Buscar patrones en el texto completo
                lines = page_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if re.search(r'born:?\s*', line, re.IGNORECASE):
                        content = re.sub(r'^.*?born:?\s*', '', line, flags=re.IGNORECASE)
                        artist_info['birth_date'], artist_info['birth_place'] = parse_date_info(content)
                        print(f"📅 Nacimiento encontrado: {content}")
                    
                    elif re.search(r'died:?\s*', line, re.IGNORECASE):
                        content = re.sub(r'^.*?died:?\s*', '', line, flags=re.IGNORECASE)
                        artist_info['death_date'], artist_info['death_place'] = parse_date_info(content)
                        print(f"⚰️ Fallecimiento encontrado: {content}")
                    
                    elif re.search(r'also known as:?\s*', line, re.IGNORECASE):
                        content = re.sub(r'^.*?also known as:?\s*', '', line, flags=re.IGNORECASE)
                        artist_info['also_known_as'] = clean_text(content)
                        print(f"👤 También conocido como: {content}")
            
            else:
                print(f"📋 Procesando {len(info_rows)} filas de información...")
                
                for i, row in enumerate(info_rows):
                    try:
                        row_text = await row.inner_text()
                        if not row_text or len(row_text.strip()) < 3:
                            continue
                        
                        print(f"  Fila {i+1}: {row_text[:100]}...")
                        
                        # Buscar patrones específicos
                        if re.search(r'born', row_text, re.IGNORECASE):
                            content = re.sub(r'^.*?born:?\s*', '', row_text, flags=re.IGNORECASE)
                            artist_info['birth_date'], artist_info['birth_place'] = parse_date_info(content)
                            print(f"  ✓ Nacimiento: {content}")
                        
                        elif re.search(r'died', row_text, re.IGNORECASE):
                            content = re.sub(r'^.*?died:?\s*', '', row_text, flags=re.IGNORECASE)
                            artist_info['death_date'], artist_info['death_place'] = parse_date_info(content)
                            print(f"  ✓ Fallecimiento: {content}")
                        
                        elif re.search(r'also known as', row_text, re.IGNORECASE):
                            content = re.sub(r'^.*?also known as:?\s*', '', row_text, flags=re.IGNORECASE)
                            artist_info['also_known_as'] = clean_text(content)
                            print(f"  ✓ También conocido como: {content}")
                        
                        elif re.search(r'notes?', row_text, re.IGNORECASE):
                            content = re.sub(r'^.*?notes?:?\s*', '', row_text, flags=re.IGNORECASE)
                            artist_info['notes'] = clean_text(content)
                            print(f"  ✓ Notas: {content[:50]}...")
                    
                    except Exception as e:
                        print(f"  ❌ Error procesando fila {i+1}: {e}")
                        continue
        
        except Exception as e:
            print(f"❌ Error extrayendo info básica: {e}")
        
        # Extraer géneros con múltiples estrategias
        try:
            print("🎼 Buscando géneros...")
            genre_elements = await page.query_selector_all('a[href*="/genre/"], a[href*="/rgenre/"], .genre a, a[href*="rgenre"]')
            genres = []
            
            for element in genre_elements:
                try:
                    genre_text = await element.inner_text()
                    href = await element.get_attribute('href')
                    
                    if genre_text and genre_text.strip() and 'genre' in (href or ''):
                        genres.append(genre_text.strip())
                        print(f"  🎵 Género encontrado: {genre_text.strip()}")
                except:
                    continue
            
            if genres:
                # Eliminar duplicados manteniendo orden
                unique_genres = []
                for genre in genres:
                    if genre not in unique_genres:
                        unique_genres.append(genre)
                artist_info['genres'] = ', '.join(unique_genres)
                print(f"✓ Géneros finales: {artist_info['genres']}")
        
        except Exception as e:
            print(f"❌ Error extrayendo géneros: {e}")
        
        # Verificar si se extrajo alguna información
        has_data = any(v for v in artist_info.values() if v)
        if not has_data:
            print("⚠️ No se pudo extraer ninguna información del artista")
            
            # Debug adicional
            print("🔍 Realizando análisis adicional de la página...")
            try:
                # Obtener algunos elementos para debug
                all_text = await page.inner_text('body')
                print(f"📄 Tamaño del contenido: {len(all_text)} caracteres")
                
                # Buscar palabras clave en todo el contenido
                keywords = ['born', 'died', 'genre', 'also known', 'biography']
                for keyword in keywords:
                    if keyword.lower() in all_text.lower():
                        print(f"  ✓ Encontrada palabra clave: {keyword}")
                
            except Exception as e:
                print(f"❌ Error en análisis adicional: {e}")
        else:
            extracted_fields = [k for k, v in artist_info.items() if v]
            print(f"✅ Información extraída exitosamente: {extracted_fields}")
        
        return artist_info
    
    except Exception as e:
        print(f"❌ Error general en scraping: {e}")
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
            page_title = ?,
            member_rating = ?,
            avg_rating = ?,
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
            artist_info['page_title'],
            artist_info['member_rating'],
            artist_info['avg_rating'],
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
    min_delay = config.get('min_delay', 2)
    max_delay = config.get('max_delay', 5)
    
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
    
    async with async_playwright() as playwright:
        browser, context = await create_stealth_context(playwright)
        page = await context.new_page()
        
        try:
            for i, (row_id, artist_id, artist_name, rym_url) in enumerate(artists, 1):
                print(f"\n[{i}/{len(artists)}] Procesando: {artist_name}")
                
                try:
                    # Extraer información
                    artist_info = await scrape_artist_info(page, rym_url)
                    
                    if artist_info:
                        update_artist_info(db_path, row_id, artist_info)
                    else:
                        update_artist_error(db_path, row_id, "No se pudo extraer información")
                    
                    # Delay aleatorio entre requests
                    if i < len(artists):
                        delay = random.uniform(min_delay, max_delay)
                        print(f"Esperando {delay:.1f} segundos...")
                        await asyncio.sleep(delay)
                
                except Exception as e:
                    error_msg = f"Error procesando artista: {str(e)}"
                    print(f"❌ {error_msg}")
                    update_artist_error(db_path, row_id, error_msg)
                    continue
        
        finally:
            await context.close()
            await browser.close()

def main(config=None):
    """Función principal del script"""
    global CONFIG
    
    if config:
        CONFIG.update(config)
    
    # Configuración por defecto
    default_config = {
        'min_delay': 2,
        'max_delay': 5,
        'limit': None,
        'headless': False
    }
    
    for key, value in default_config.items():
        if key not in CONFIG:
            CONFIG[key] = value
    
    print("=== RateYourMusic Artist Info Scraper (Playwright) ===")
    print(f"Base de datos: {CONFIG.get('db_path', 'No especificada')}")
    print(f"Límite: {CONFIG.get('limit', 'Sin límite')}")
    print(f"Delay: {CONFIG.get('min_delay')}-{CONFIG.get('max_delay')} segundos")
    print(f"Headless: {CONFIG.get('headless')}")
    
    # Ejecutar proceso asíncrono
    try:
        asyncio.run(process_artists(CONFIG))
        print("\n✅ Proceso completado")
    except KeyboardInterrupt:
        print("\n⚠️ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error en proceso principal: {e}")

if __name__ == "__main__":
    main()