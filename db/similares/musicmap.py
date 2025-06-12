#!/usr/bin/env python3
"""
Script para extraer recomendaciones de artistas desde Music-Map.com
Compatible con db_creator.py
"""

import sqlite3
import time
import urllib.parse
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_driver(headless=True):
    """Configura el driver de Chrome para Selenium"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        logger.error(f"Error al configurar el driver de Chrome: {e}")
        return None

def extract_musicmap_recommendations(driver, artist_name, max_wait=10):
    """
    Extrae las recomendaciones de artistas de Music-Map
    
    Args:
        driver: Driver de Selenium
        artist_name: Nombre del artista a buscar
        max_wait: Tiempo máximo de espera en segundos
    
    Returns:
        Lista de nombres de artistas recomendados
    """
    url_artist = urllib.parse.quote_plus(artist_name.lower())
    url = f"https://www.music-map.com/{url_artist}"
    
    logger.info(f"Buscando recomendaciones para: {artist_name}")
    logger.info(f"URL: {url}")
    
    try:
        driver.get(url)
        
        # Esperar a que la página cargue
        wait = WebDriverWait(driver, max_wait)
        
        # Diferentes estrategias para encontrar los elementos
        selectors = [
            "span.Name",  # Selector principal reportado
            ".Name",      # Alternativo sin span
            "[class*='Name']",  # Cualquier clase que contenga 'Name'
            "a[title]",   # Enlaces con título
            ".artist",    # Clase artist genérica
            "span",       # Fallback a todos los spans
        ]
        
        recommendations = []
        
        for selector in selectors:
            try:
                # Esperar a que aparezcan elementos
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                if elements:
                    logger.info(f"Encontrados {len(elements)} elementos con selector: {selector}")
                    
                    for element in elements:
                        try:
                            # Intentar obtener el texto del elemento
                            text = element.text.strip()
                            if not text:
                                text = element.get_attribute('title')
                            if not text:
                                text = element.get_attribute('data-artist')
                            
                            if text and text.lower() != artist_name.lower():
                                # Filtrar textos que no parecen nombres de artistas
                                if len(text) > 1 and not text.startswith('http') and not re.match(r'^\d+$', text):
                                    recommendations.append(text)
                                    
                        except Exception as e:
                            continue
                    
                    if recommendations:
                        break  # Si encontramos recomendaciones, no probar más selectores
                        
            except TimeoutException:
                logger.debug(f"Timeout con selector: {selector}")
                continue
            except Exception as e:
                logger.debug(f"Error con selector {selector}: {e}")
                continue
        
        # Eliminar duplicados manteniendo el orden
        unique_recommendations = []
        seen = set()
        for rec in recommendations:
            if rec.lower() not in seen:
                unique_recommendations.append(rec)
                seen.add(rec.lower())
        
        logger.info(f"Encontradas {len(unique_recommendations)} recomendaciones únicas para {artist_name}")
        return unique_recommendations[:20]  # Limitar a 20 recomendaciones
        
    except Exception as e:
        logger.error(f"Error extrayendo recomendaciones para {artist_name}: {e}")
        return []

def create_musicmap_table(db_path):
    """Crea la tabla para almacenar recomendaciones de Music-Map"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS musicmap_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER NOT NULL,
            artist_name TEXT NOT NULL,
            recommended_artist TEXT NOT NULL,
            similarity_score INTEGER DEFAULT 1,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists (id),
            UNIQUE(artist_id, recommended_artist COLLATE NOCASE)
        )
    ''')
    
    # Crear índices para mejor performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_musicmap_artist_id ON musicmap_recommendations(artist_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_musicmap_artist_name ON musicmap_recommendations(artist_name)')
    
    conn.commit()
    conn.close()
    
    logger.info("Tabla musicmap_recommendations creada/verificada")

def get_artists_from_db(db_path, limit=None, force_update=False, missing_only=True):
    """Obtiene la lista de artistas de la base de datos"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if missing_only and not force_update:
        # Solo artistas sin recomendaciones
        query = '''
            SELECT DISTINCT a.id, a.name 
            FROM artists a 
            LEFT JOIN musicmap_recommendations mr ON a.id = mr.artist_id 
            WHERE mr.artist_id IS NULL
            AND a.name IS NOT NULL 
            AND a.name != ''
            ORDER BY a.name
        '''
    else:
        # Todos los artistas
        query = '''
            SELECT DISTINCT id, name 
            FROM artists 
            WHERE name IS NOT NULL 
            AND name != ''
            ORDER BY name
        '''
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    artists = cursor.fetchall()
    conn.close()
    
    logger.info(f"Obtenidos {len(artists)} artistas de la base de datos")
    return artists

def save_recommendations(db_path, artist_id, artist_name, recommendations):
    """Guarda las recomendaciones en la base de datos"""
    if not recommendations:
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Limpiar recomendaciones existentes si existe force_update
    cursor.execute('DELETE FROM musicmap_recommendations WHERE artist_id = ?', (artist_id,))
    
    # Insertar nuevas recomendaciones
    for i, rec in enumerate(recommendations):
        similarity_score = len(recommendations) - i  # Score basado en orden
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO musicmap_recommendations 
                (artist_id, artist_name, recommended_artist, similarity_score, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (artist_id, artist_name, rec, similarity_score, datetime.now()))
        except sqlite3.Error as e:
            logger.error(f"Error insertando recomendación {rec} para {artist_name}: {e}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Guardadas {len(recommendations)} recomendaciones para {artist_name}")

def main(config=None):
    """Función principal del script"""
    # Valores por defecto
    default_config = {
        'db_path': '/home/huan/gits/pollo/music-fuzzy/db/sqlite/musica_local.sqlite',
        'headless': True,
        'limit': None,
        'force_update': False,
        'missing_only': True,
        'rate_limit': 2.0,
        'max_retries': 3,
        'log_level': 'INFO'
    }
    
    # Usar configuración pasada o por defecto
    if config:
        default_config.update(config)
    
    # Configurar logging
    log_level = getattr(logging, default_config['log_level'].upper(), logging.INFO)
    logger.setLevel(log_level)
    
    db_path = default_config['db_path']
    headless = default_config['headless']
    limit = default_config['limit']
    force_update = default_config['force_update']
    missing_only = default_config['missing_only']
    rate_limit = default_config['rate_limit']
    max_retries = default_config['max_retries']
    
    logger.info("Iniciando extracción de recomendaciones de Music-Map")
    logger.info(f"Base de datos: {db_path}")
    logger.info(f"Modo headless: {headless}")
    logger.info(f"Límite: {limit}")
    logger.info(f"Forzar actualización: {force_update}")
    logger.info(f"Solo faltantes: {missing_only}")
    
    # Crear tabla si no existe
    create_musicmap_table(db_path)
    
    # Obtener artistas
    artists = get_artists_from_db(db_path, limit, force_update, missing_only)
    
    if not artists:
        logger.info("No hay artistas para procesar")
        return
    
    # Configurar driver
    driver = setup_driver(headless)
    if not driver:
        logger.error("No se pudo configurar el driver de Chrome")
        return
    
    try:
        processed = 0
        errors = 0
        
        for artist_id, artist_name in artists:
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    logger.info(f"Procesando artista {processed + 1}/{len(artists)}: {artist_name}")
                    
                    recommendations = extract_musicmap_recommendations(driver, artist_name)
                    
                    if recommendations:
                        save_recommendations(db_path, artist_id, artist_name, recommendations)
                        logger.info(f"✓ {artist_name}: {len(recommendations)} recomendaciones")
                        success = True
                    else:
                        logger.warning(f"✗ {artist_name}: No se encontraron recomendaciones")
                        success = True  # No reintentar si simplemente no hay recomendaciones
                    
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Error procesando {artist_name} (intento {retry_count}/{max_retries}): {e}")
                    
                    if retry_count < max_retries:
                        time.sleep(rate_limit * 2)  # Espera extra en caso de error
                    else:
                        errors += 1
            
            processed += 1
            
            # Rate limiting
            time.sleep(rate_limit)
            
            # Progreso cada 10 artistas
            if processed % 10 == 0:
                logger.info(f"Progreso: {processed}/{len(artists)} artistas procesados")
    
    finally:
        driver.quit()
        logger.info(f"Procesamiento completado. Total: {processed}, Errores: {errors}")

if __name__ == "__main__":
    main()