#!/usr/bin/env python3
"""
Script para buscar URLs de RateYourMusic para artistas usando SearXNG
Compatible con db_creator.py
"""

import requests
import sqlite3
import time
import re
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variables globales que serán configuradas por db_creator
CONFIG = {}

class RateYourMusicSearcher:
    def __init__(self, db_path, searxng_url, delay=5.0, max_retries=3):
        """
        Inicializa el buscador de RateYourMusic
        
        Args:
            db_path: Ruta a la base de datos SQLite
            searxng_url: URL base de la instancia SearXNG (ej: "http://localhost:8080")
            delay: Retraso entre búsquedas en segundos (aumentado por defecto)
            max_retries: Máximo número de reintentos para rate limiting
        """
        self.db_path = Path(db_path)
        self.searxng_url = searxng_url.rstrip('/')
        self.delay = delay
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Estadísticas
        self.stats = {
            'total_artists': 0,
            'already_have_rym': 0,
            'searches_performed': 0,
            'urls_found': 0,
            'urls_updated': 0,
            'errors': 0,
            'rate_limits': 0
        }

    def get_artists_without_rym_url(self, limit=None):
        """Obtiene artistas que no tienen URL de RateYourMusic"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT id, name 
        FROM artists 
        WHERE (rateyourmusic_url IS NULL OR rateyourmusic_url = '')
        AND name IS NOT NULL 
        AND name != ''
        ORDER BY id
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        cursor.execute(query)
        artists = cursor.fetchall()
        conn.close()
        
        return artists

    def search_artist_on_rym(self, artist_name):
        """
        Busca un artista en RateYourMusic usando SearXNG con manejo de rate limiting
        
        Returns:
            str or None: URL de RateYourMusic si se encuentra, None si no
        """
        max_retries = 3
        base_wait_time = 5  # segundos base para esperar en rate limit
        
        for attempt in range(max_retries):
            try:
                # Construir query de búsqueda para RateYourMusic
                search_query = f"site:rateyourmusic.com {artist_name}"
                
                # Parámetros para SearXNG
                params = {
                    'q': search_query,
                    'format': 'html',
                    'categories': 'general'
                }
                
                # Realizar búsqueda
                search_url = f"{self.searxng_url}/search"
                logger.info(f"Buscando: {artist_name} (intento {attempt + 1}/{max_retries})")
                logger.debug(f"URL: {search_url}")
                logger.debug(f"Query: {search_query}")
                
                response = self.session.get(search_url, params=params, timeout=30)
                
                # Manejar rate limiting
                if response.status_code == 429:
                    wait_time = base_wait_time * (2 ** attempt)  # Backoff exponencial
                    logger.warning(f"Rate limit alcanzado para '{artist_name}'. Esperando {wait_time} segundos...")
                    self.stats['rate_limits'] += 1
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                
                # Parsear resultados HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Buscar resultados en la estructura HTML de SearXNG
                # Los resultados suelen estar en elementos con clase 'result'
                results = soup.find_all('article', class_='result')
                
                if not results:
                    # Intentar con selector alternativo
                    results = soup.find_all('div', class_='result')
                
                rym_urls = []
                
                for result in results:
                    # Buscar el enlace en el resultado
                    link_element = result.find('a')
                    if not link_element:
                        continue
                        
                    url = link_element.get('href', '')
                    
                    # Verificar si es una URL de RateYourMusic válida
                    if self.is_valid_rym_artist_url(url):
                        # Verificar que el nombre del artista coincida aproximadamente
                        if self.artist_name_matches(artist_name, url, result.get_text()):
                            rym_urls.append(url)
                
                if rym_urls:
                    # Retornar la primera URL válida encontrada
                    best_url = self.select_best_rym_url(rym_urls, artist_name)
                    logger.info(f"✓ Encontrado para '{artist_name}': {best_url}")
                    return best_url
                else:
                    logger.info(f"✗ No encontrado para '{artist_name}'")
                    return None
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    wait_time = base_wait_time * (2 ** attempt)
                    logger.warning(f"Rate limit HTTP error para '{artist_name}'. Esperando {wait_time} segundos...")
                    self.stats['rate_limits'] += 1
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Error HTTP en la búsqueda para '{artist_name}': {e}")
                    self.stats['errors'] += 1
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Error en la búsqueda para '{artist_name}': {e}")
                self.stats['errors'] += 1
                return None
            except Exception as e:
                logger.error(f"Error inesperado buscando '{artist_name}': {e}")
                self.stats['errors'] += 1
                return None
        
        # Si llegamos aquí, agotamos todos los intentos
        logger.error(f"Máximo de intentos agotado para '{artist_name}' debido a rate limiting")
        self.stats['errors'] += 1
        return None

    def is_valid_rym_artist_url(self, url):
        """Verifica si una URL es válida de RateYourMusic para artistas"""
        if not url or not isinstance(url, str):
            return False
            
        # Normalizar URL
        url = url.lower()
        
        # Debe ser de rateyourmusic.com
        if 'rateyourmusic.com' not in url:
            return False
            
        # Patrones válidos para páginas de artistas
        artist_patterns = [
            r'rateyourmusic\.com/artist/',
            r'rateyourmusic\.com/artist\.php',
        ]
        
        for pattern in artist_patterns:
            if re.search(pattern, url):
                return True
                
        return False

    def artist_name_matches(self, search_name, url, result_text):
        """
        Verifica si el resultado corresponde al artista buscado
        """
        search_name_clean = self.clean_artist_name(search_name)
        result_text_clean = self.clean_artist_name(result_text)
        url_clean = self.clean_artist_name(url)
        
        # Verificación exacta
        if search_name_clean.lower() in result_text_clean.lower():
            return True
            
        # Verificación en URL
        if search_name_clean.lower() in url_clean.lower():
            return True
            
        # Verificación por palabras clave
        search_words = set(search_name_clean.lower().split())
        result_words = set(result_text_clean.lower().split())
        
        # Al menos 70% de las palabras deben coincidir
        if search_words and len(search_words.intersection(result_words)) / len(search_words) >= 0.7:
            return True
            
        return False

    def clean_artist_name(self, name):
        """Limpia el nombre del artista para comparación"""
        if not name:
            return ""
            
        # Remover caracteres especiales y normalizar
        cleaned = re.sub(r'[^\w\s]', ' ', str(name))
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def select_best_rym_url(self, urls, artist_name):
        """Selecciona la mejor URL de RateYourMusic de una lista"""
        if not urls:
            return None
            
        if len(urls) == 1:
            return urls[0]
            
        # Preferir URLs más simples (menos parámetros)
        urls_sorted = sorted(urls, key=lambda x: len(x))
        
        # Preferir URLs que contengan el nombre del artista
        artist_clean = self.clean_artist_name(artist_name).lower()
        for url in urls_sorted:
            if artist_clean in url.lower():
                return url
                
        return urls_sorted[0]

    def update_artist_rym_url(self, artist_id, rym_url):
        """Actualiza la URL de RateYourMusic en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE artists SET rateyourmusic_url = ? WHERE id = ?",
                (rym_url, artist_id)
            )
            
            conn.commit()
            conn.close()
            
            self.stats['urls_updated'] += 1
            logger.debug(f"Actualizado artista {artist_id} con URL: {rym_url}")
            
        except sqlite3.Error as e:
            logger.error(f"Error actualizando base de datos para artista {artist_id}: {e}")
            self.stats['errors'] += 1

    def get_statistics(self):
        """Obtiene estadísticas del proceso"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM artists")
        self.stats['total_artists'] = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM artists WHERE rateyourmusic_url IS NOT NULL AND rateyourmusic_url != ''"
        )
        self.stats['already_have_rym'] = cursor.fetchone()[0]
        
        conn.close()

    def run_search(self, limit=None, skip_existing=True):
        """
        Ejecuta la búsqueda de URLs de RateYourMusic
        
        Args:
            limit: Límite de artistas a procesar (None para todos)
            skip_existing: Si saltar artistas que ya tienen URL
        """
        logger.info("=== Iniciando búsqueda de URLs de RateYourMusic ===")
        
        # Obtener estadísticas iniciales
        self.get_statistics()
        
        # Obtener artistas sin URL de RYM
        artists = self.get_artists_without_rym_url(limit)
        
        if not artists:
            logger.info("No hay artistas sin URL de RateYourMusic para procesar")
            return
            
        logger.info(f"Procesando {len(artists)} artistas...")
        logger.info(f"Retraso entre búsquedas: {self.delay} segundos")
        
        for i, (artist_id, artist_name) in enumerate(artists, 1):
            try:
                logger.info(f"[{i}/{len(artists)}] Procesando: {artist_name}")
                
                # Buscar URL de RateYourMusic
                rym_url = self.search_artist_on_rym(artist_name)
                self.stats['searches_performed'] += 1
                
                if rym_url:
                    # Actualizar base de datos
                    self.update_artist_rym_url(artist_id, rym_url)
                    self.stats['urls_found'] += 1
                
                # Pausa entre búsquedas
                if i < len(artists):  # No pausar después del último
                    time.sleep(self.delay)
                    
            except KeyboardInterrupt:
                logger.info("\n⚠️ Proceso interrumpido por el usuario")
                break
            except Exception as e:
                logger.error(f"Error procesando artista {artist_name}: {e}")
                self.stats['errors'] += 1
                continue
        
        # Mostrar estadísticas finales
        self.show_final_stats()

    def show_final_stats(self):
        """Muestra estadísticas finales del proceso"""
        logger.info("\n=== Estadísticas Finales ===")
        logger.info(f"Total de artistas en BD: {self.stats['total_artists']}")
        logger.info(f"Ya tenían URL de RYM: {self.stats['already_have_rym']}")
        logger.info(f"Búsquedas realizadas: {self.stats['searches_performed']}")
        logger.info(f"URLs encontradas: {self.stats['urls_found']}")
        logger.info(f"URLs actualizadas en BD: {self.stats['urls_updated']}")
        logger.info(f"Rate limits encontrados: {self.stats['rate_limits']}")
        logger.info(f"Errores: {self.stats['errors']}")
        
        if self.stats['searches_performed'] > 0:
            success_rate = (self.stats['urls_found'] / self.stats['searches_performed']) * 100
            logger.info(f"Tasa de éxito: {success_rate:.1f}%")

def main(config=None):
    """Función principal compatible con db_creator.py"""
    
    # Usar configuración global si no se pasa como parámetro
    if config is None:
        config = CONFIG
    
    # Configuración por defecto
    default_config = {
        'db_path': 'data/music.db',
        'searxng_url': 'https://searx.tiekoetter.com',
        'delay': 5.0,  # Aumentado por defecto
        'max_retries': 3,
        'limit': None,
        'log_level': 'INFO'
    }
    
    # Combinar configuración
    final_config = {**default_config, **config}
    
    # Configurar logging
    log_level = getattr(logging, final_config.get('log_level', 'INFO').upper())
    logging.getLogger().setLevel(log_level)
    
    try:
        # Validar configuración
        db_path = Path(final_config['db_path'])
        if not db_path.exists():
            logger.error(f"Base de datos no encontrada: {db_path}")
            return 1
            
        searxng_url = final_config['searxng_url']
        if not searxng_url:
            logger.error("URL de SearXNG no configurada")
            return 1
        
        # Crear instancia del buscador
        searcher = RateYourMusicSearcher(
            db_path=db_path,
            searxng_url=searxng_url,
            delay=final_config['delay'],
            max_retries=final_config.get('max_retries', 3)
        )
        
        # Ejecutar búsqueda
        searcher.run_search(
            limit=final_config.get('limit'),
            skip_existing=final_config.get('skip_existing', True)
        )
        
        logger.info("✅ Proceso completado exitosamente")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error en el proceso: {e}")
        return 1

if __name__ == "__main__":
    # Configuración para ejecución independiente
    import argparse
    
    parser = argparse.ArgumentParser(description='Buscar URLs de RateYourMusic para artistas')
    parser.add_argument('--db-path', default='data/music.db', help='Ruta a la base de datos')
    parser.add_argument('--searxng-url', default='https://searx.tiekoetter.com', help='URL de SearXNG')
    parser.add_argument('--delay', type=float, default=5.0, help='Retraso entre búsquedas (segundos)')
    parser.add_argument('--max-retries', type=int, default=3, help='Máximo reintentos para rate limiting')
    parser.add_argument('--limit', type=int, help='Límite de artistas a procesar')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    config = {
        'db_path': args.db_path,
        'searxng_url': args.searxng_url,
        'delay': args.delay,
        'max_retries': args.max_retries,
        'limit': args.limit,
        'log_level': args.log_level
    }
    
    exit(main(config))