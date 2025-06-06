#!/usr/bin/env python3
"""
Script para obtener URLs de álbumes desde páginas de artistas en RateYourMusic
Usa las URLs de artistas ya obtenidas en la base de datos
Integrado con db_creator.py
"""

import asyncio
import sqlite3
import logging
import time
import sys
import os
from pathlib import Path
from urllib.parse import quote_plus
import nodriver as uc


logger = logging.getLogger(__name__)

class RYMAlbumScraper:
    def __init__(self, config=None):
        if config is None:
            config = {}
        
        self.config = config
        self.db_path = config.get('db_path', 'music.db')
        self.browser = None
        self.page = None
        
        # Verificar que la base de datos existe y tiene las tablas necesarias
        self.verify_database()
        
        # Configuración por defecto
        self.search_delay = self.config.get('search_delay', 3)
        self.page_load_delay = self.config.get('page_load_delay', 5)
        self.headless = self.config.get('headless', False)
        
    def verify_database(self):
        """Verificar que la base de datos existe y tiene las tablas necesarias"""
        import os
        
        if not os.path.exists(self.db_path):
            logger.error(f"Base de datos no encontrada: {self.db_path}")
            raise FileNotFoundError(f"Base de datos no encontrada: {self.db_path}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Verificar que existen las tablas necesarias
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artists'")
                if not cursor.fetchone():
                    logger.error("Tabla 'artists' no encontrada en la base de datos")
                    raise ValueError("Tabla 'artists' no encontrada en la base de datos")
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='albums'")
                if not cursor.fetchone():
                    logger.error("Tabla 'albums' no encontrada en la base de datos")
                    raise ValueError("Tabla 'albums' no encontrada en la base de datos")
                
                logger.info(f"Base de datos verificada: {self.db_path}")
                
        except sqlite3.Error as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            raise
    
    async def init_browser(self):
        """Inicializar el navegador"""
        try:
            self.browser = await uc.start(
                headless=self.headless, 
                browser_args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = await self.browser.get('https://rateyourmusic.com')
            await asyncio.sleep(self.page_load_delay)
            logger.info("Navegador inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar navegador: {e}")
            raise
    
    async def close_browser(self):
        """Cerrar el navegador"""
        if self.browser is not None:
            try:
                self.browser.stop()
                logger.info("Navegador cerrado")
            except Exception as e:
                logger.error(f"Error al cerrar navegador: {e}")
            finally:
                self.browser = None
        else:
            logger.debug("No hay navegador para cerrar")
    
    async def restart_browser(self):
        """Reiniciar el navegador"""
        logger.info("Reiniciando navegador...")
        await self.close_browser()
        await asyncio.sleep(3)
        await self.init_browser()
    
    def get_artists_with_rym_url(self):
        """Obtener artistas que YA tienen URL de RateYourMusic"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, rateyourmusic_url FROM artists 
                WHERE rateyourmusic_url IS NOT NULL 
                AND rateyourmusic_url != '' 
                AND rateyourmusic_url != 'NOT_FOUND'
                AND rateyourmusic_url LIKE 'https://rateyourmusic.com/artist/%'
                ORDER BY name
            """)
            
            artists = cursor.fetchall()
            logger.info(f"Encontrados {len(artists)} artistas con URL de RateYourMusic")
            return artists
    
    def get_albums_without_rym_url(self, artist_id):
        """Obtener álbumes de un artista específico que no tienen URL de RateYourMusic"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name FROM albums
                WHERE artist_id = ?
                AND (rateyourmusic_url IS NULL OR rateyourmusic_url = '' OR rateyourmusic_url = 'NOT_FOUND')
                ORDER BY name
            """, (artist_id,))
            
            albums = cursor.fetchall()
            logger.debug(f"Artista {artist_id} tiene {len(albums)} álbumes sin URL")
            return albums
    
    async def check_browser_status(self):
        """Verificar si el navegador está funcionando"""
        try:
            if self.page is None:
                logger.error("Page is None - browser not initialized properly")
                return False
            
            # Verificar que podemos ejecutar JavaScript básico
            try:
                title = await self.page.title
                logger.debug(f"Page title: {title}")
                return True
            except Exception as e:
                logger.error(f"Cannot get page title: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Browser check failed: {e}")
            return False
    
    async def get_artist_albums_from_page(self, artist_url):
        """Obtener TODOS los álbumes desde la página del artista"""
        albums_found = []
        try:
            logger.info(f"Navegando a página del artista: {artist_url}")
            await self.page.get(artist_url)
            await asyncio.sleep(self.page_load_delay)
            
            # Verificar si hay un botón "Show all" y hacer clic
            try:
                show_all_selectors = [
                    'a.disco_expand_all',  # Botón "Show all" típico
                    'a[href*="show=all"]',  # Enlaces que muestran todo
                    '.disco_expand a',  # Enlaces de expansión
                    'a:contains("Show all")'  # Texto "Show all"
                ]
                
                for selector in show_all_selectors:
                    try:
                        show_all_btn = await self.page.find(selector, timeout=2)
                        if show_all_btn:
                            logger.info("Encontrado botón 'Show all', haciendo clic...")
                            await show_all_btn.click()
                            await asyncio.sleep(self.page_load_delay)
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"No se encontró botón 'Show all': {e}")
            
            # Selectores para álbumes en páginas de artistas de RYM
            album_selectors = [
                'a[href*="/release/album/"]',  # Enlaces directos a álbumes
                '.disco_release_title a',  # Títulos de álbumes en discografía
                '.disco_main_release a',  # Releases principales
                'td.release a[href*="/release/"]',  # Enlaces en tabla de releases
                '.album_link a',  # Enlaces específicos de álbum
                'a[href*="/release/"]'  # Enlaces generales de release
            ]
            
            for selector in album_selectors:
                try:
                    album_links = await self.page.find_all(selector, timeout=5)
                    if album_links:
                        logger.info(f"Encontrados {len(album_links)} enlaces con selector: {selector}")
                        for link in album_links:
                            try:
                                album_url = await link.get_attribute('href')
                                if album_url and '/release/' in album_url:
                                    if album_url.startswith('/'):
                                        album_url = f"https://rateyourmusic.com{album_url}"
                                    
                                    album_name = await link.get_text()
                                    if album_name and album_name.strip():
                                        # Evitar duplicados
                                        album_data = {
                                            'name': album_name.strip(), 
                                            'url': album_url
                                        }
                                        if album_data not in albums_found:
                                            albums_found.append(album_data)
                            except Exception as e:
                                logger.debug(f"Error procesando enlace de álbum: {e}")
                                continue
                        break  # Si encontramos álbumes, no necesitamos otros selectores
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Error con selector {selector}: {e}")
                    continue
                    
        except Exception as e:
            logger.exception(f"Error obteniendo álbumes desde {artist_url}: {e}")
        
        logger.info(f"Encontrados {len(albums_found)} álbumes únicos en la página")
        return albums_found
    
    def match_album_to_database(self, artist_id, page_albums):
        """Hacer match de álbumes de la página con álbumes en la base de datos"""
        db_albums = self.get_albums_without_rym_url(artist_id)
        matches = []
        
        for db_album_id, db_album_name in db_albums:
            best_match = None
            best_score = 0
            
            for page_album in page_albums:
                # Comparación simple por nombre (puedes mejorar esto)
                page_name = page_album['name'].lower().strip()
                db_name = db_album_name.lower().strip()
                
                # Match exacto
                if page_name == db_name:
                    matches.append({
                        'db_album_id': db_album_id,
                        'db_name': db_album_name,
                        'page_name': page_album['name'],
                        'url': page_album['url'],
                        'match_type': 'exact'
                    })
                    break
                
                # Match parcial (contiene)
                elif page_name in db_name or db_name in page_name:
                    score = max(len(page_name), len(db_name)) / (len(page_name) + len(db_name))
                    if score > best_score:
                        best_score = score
                        best_match = {
                            'db_album_id': db_album_id,
                            'db_name': db_album_name,
                            'page_name': page_album['name'],
                            'url': page_album['url'],
                            'match_type': f'partial_{best_score:.2f}'
                        }
            
            # Agregar el mejor match parcial si no hubo match exacto
            if best_match and best_score > 0.6:  # Umbral de similitud
                matches.append(best_match)
        
        logger.info(f"Encontrados {len(matches)} matches entre página y base de datos")
        return matches
    
    def update_album_url(self, album_id, url):
        """Actualizar URL del álbum en la base de datos"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE albums 
                SET rateyourmusic_url = ?
                WHERE id = ?
            """, (url, album_id))
            
            conn.commit()
            logger.info(f"URL actualizada para álbum ID {album_id}: {url}")
    
    def insert_new_album(self, artist_id, album_name, url):
        """Insertar álbum nuevo encontrado en RYM pero no en la base de datos"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO albums (name, artist_id, rateyourmusic_url)
                VALUES (?, ?, ?)
            """, (album_name, artist_id, url))
            
            conn.commit()
            logger.info(f"Álbum nuevo insertado: {album_name} para artista {artist_id}")
    
    async def process_artist_albums(self, artist_id, artist_name, artist_url):
        """Procesar álbumes de un artista específico"""
        try:
            logger.info(f"Procesando álbumes para: {artist_name}")
            
            # Obtener álbumes desde la página del artista
            page_albums = await self.get_artist_albums_from_page(artist_url)
            
            if not page_albums:
                logger.warning(f"No se encontraron álbumes en la página de {artist_name}")
                return
            
            # Hacer match con álbumes en la base de datos
            matches = self.match_album_to_database(artist_id, page_albums)
            
            # Actualizar URLs de álbumes que hicieron match
            for match in matches:
                self.update_album_url(match['db_album_id'], match['url'])
                logger.info(f"Match {match['match_type']}: '{match['db_name']}' -> '{match['page_name']}'")
            
            # Opcionalmente, insertar álbumes nuevos que no están en la DB
            if self.config.get('insert_new_albums', False):
                matched_names = [m['page_name'].lower() for m in matches]
                for album in page_albums:
                    if album['name'].lower() not in matched_names:
                        self.insert_new_album(artist_id, album['name'], album['url'])
            
        except Exception as e:
            logger.error(f"Error procesando álbumes para {artist_name}: {e}")
    
    async def process_all_artists(self):
        """Procesar álbumes de todos los artistas con URL"""
        artists = self.get_artists_with_rym_url()
        logger.info(f"Procesando álbumes para {len(artists)} artistas")
        
        for i, (artist_id, artist_name, artist_url) in enumerate(artists):
            try:
                logger.info(f"Artista {i+1}/{len(artists)}: {artist_name}")
                
                await self.process_artist_albums(artist_id, artist_name, artist_url)
                
                # Pausa entre artistas
                await asyncio.sleep(self.search_delay)
                
            except Exception as e:
                logger.error(f"Error procesando artista {artist_name}: {e}")
                await self.restart_browser()
                continue
    
    async def run(self):
        """Ejecutar el scraping de álbumes"""
        try:
            await self.init_browser()
            await self.process_all_artists()
                
        except Exception as e:
            logger.error(f"Error durante la ejecución: {e}")
        finally:
            await self.close_browser()

def setup_logging():
    """Configurar logging para debug"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configurar el logger específico del script
    global logger
    logger = logging.getLogger(__name__)

def main(config=None):
    """Función principal para db_creator"""
    if config is None:
        config = {}
    
    # Configurar logging
    setup_logging()
    
    # Verificar configuración
    db_path = config.get('db_path', 'music.db')
    logger.info(f"Usando base de datos: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"Base de datos no encontrada: {db_path}")
        print(f"ERROR: Base de datos no encontrada: {db_path}")
        return
    
    try:
        scraper = RYMAlbumScraper(config)
        
        # Verificar que hay artistas para procesar
        artists = scraper.get_artists_with_rym_url()
        
        if not artists:
            logger.info("No hay artistas con URLs de RateYourMusic para procesar")
            print("No hay artistas con URLs de RateYourMusic. Ejecuta primero el script de artistas.")
            return
        
        logger.info(f"Artistas con URL para procesar: {len(artists)}")
        
        asyncio.run(scraper.run())
        logger.info("Scraping de álbumes completado exitosamente")
        
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        import traceback
        traceback.print_exc()
        print(f"ERROR FATAL: {e}")

if __name__ == "__main__":
    # Configuración de ejemplo
    config = {
        'db_path': 'music.db',
        'search_delay': 3,
        'page_load_delay': 5,
        'headless': False,
        'insert_new_albums': False  # Si insertar álbumes nuevos no encontrados en la DB
    }
    main(config)