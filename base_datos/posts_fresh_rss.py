import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional
from urllib.parse import quote
import requests

# Configurar logging
logger = logging.getLogger(__name__)

class FreshRSSContentFinder():
    def __init__(self, config):
        super().__init__(config)
        self.base_url = config.get('freshrss_url')
        self.username = config.get('freshrss_username')
        self.api_password = config.get('freshrss_password')
        self.api_endpoint = f"{self.base_url.rstrip('/')}/api/greader.php"
        self.auth_token = None
        self.db_path = config.get('db_path')
        self.cache_path = config.get('freshrss_cache_path')
        self.target_categories = config.get('categories', ['Blogs', 'Revistas', 'Wallabag'])
        self.search_artists = 'artists' in config.get('search_entities', [])
        self.search_albums = 'albums' in config.get('search_entities', [])
        self.search_labels = 'labels' in config.get('search_entities', [])
        
        # Cargar cache si existe
        self.cache = self._load_cache()
        
    def _load_cache(self) -> Dict:
        """Carga el cache de feeds procesados"""
        if not self.cache_path or not os.path.exists(self.cache_path):
            return {}
            
        try:
            with open(self.cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando cache: {str(e)}")
            return {}
    
    def _save_cache(self):
        """Guarda el cache actualizado"""
        if not self.cache_path:
            return
            
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w') as f:
                json.dump(self.cache, f, indent=2)
            logger.info(f"Cache guardado en {self.cache_path}")
        except Exception as e:
            logger.error(f"Error guardando cache: {str(e)}")
    
    def login(self) -> bool:
        """Inicia sesión en la API de FreshRSS"""
        endpoint = f"{self.api_endpoint}/accounts/ClientLogin"
        params = {
            'Email': self.username,
            'Passwd': self.api_password
        }
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            
            for line in response.text.splitlines():
                if line.startswith('Auth='):
                    self.auth_token = line.replace('Auth=', '').strip()
                    logger.info(f"Token obtenido correctamente")
                    return True
            
            logger.error("No se encontró el token de autenticación")
            return False
        except Exception as e:
            logger.error(f"Error en login: {str(e)}")
            return False
            
    def get_headers(self) -> Dict[str, str]:
        """Obtiene los headers para las peticiones a la API"""
        if not self.auth_token:
            raise ValueError("No se ha realizado el login")
            
        return {
            'Authorization': f'GoogleLogin auth={self.auth_token}',
            'User-Agent': 'FreshRSS-Script/1.0'
        }

    def get_feed_subscriptions(self) -> List[Dict]:
        """Obtiene los feeds subscritos"""
        endpoint = f"{self.api_endpoint}/reader/api/0/subscription/list"
        params = {'output': 'json'}
        
        try:
            response = requests.get(endpoint, headers=self.get_headers(), params=params)
            response.raise_for_status()
            return response.json().get('subscriptions', [])
        except Exception as e:
            logger.error(f"Error obteniendo subscripciones: {str(e)}")
            return []

    def get_category_feeds(self, category_name: str) -> List[Dict]:
        """Obtiene los feeds de una categoría especificada"""
        subscriptions = self.get_feed_subscriptions()
        category_feeds = []
        
        for feed in subscriptions:
            for category in feed.get('categories', []):
                if category['label'] == category_name:
                    category_feeds.append(feed)
                    break
                    
        return category_feeds

    def get_posts(self, feed_id: str, include_read: bool = False) -> List[Dict[str, str]]:
        """Obtiene los posts de un feed, por defecto solo los no leídos"""
        endpoint = f"{self.api_endpoint}/reader/api/0/stream/contents/{quote(feed_id)}"
        params = {
            'output': 'json',
            'n': 1000,  # Número máximo de artículos a obtener
        }
        
        # Si solo queremos los no leídos
        if not include_read:
            params['xt'] = 'user/-/state/com.google/read'
        
        # Obtener último timestamp guardado para este feed
        last_timestamp = self.cache.get(feed_id, {}).get('last_timestamp', 0)
        if last_timestamp > 0:
            params['ot'] = last_timestamp
        
        try:
            response = requests.get(endpoint, headers=self.get_headers(), params=params)
            response.raise_for_status()
            data = response.json()
            
            posts = []
            latest_timestamp = last_timestamp
            
            for item in data.get('items', []):
                url = None
                if 'canonical' in item and item['canonical']:
                    url = item['canonical'][0]['href']
                elif 'alternate' in item and item['alternate']:
                    url = item['alternate'][0]['href']
                
                timestamp = item.get('published', 0)
                if timestamp > latest_timestamp:
                    latest_timestamp = timestamp
                
                if url:
                    published_date = datetime.fromtimestamp(timestamp)
                    content = item.get('summary', {}).get('content', '')
                    content += item.get('content', {}).get('content', '')
                    
                    posts.append({
                        'url': url,
                        'date': published_date,
                        'title': item.get('title', 'Sin título'),
                        'month_key': published_date.strftime('%Y-%m'),
                        'feed_title': item.get('origin', {}).get('title', 'Unknown Feed'),
                        'content': content
                    })
            
            # Actualizar cache con el timestamp más reciente
            if feed_id not in self.cache:
                self.cache[feed_id] = {}
            
            self.cache[feed_id]['last_timestamp'] = latest_timestamp
            self.cache[feed_id]['feed_title'] = data.get('title', 'Unknown Feed')
                    
            return posts
        except Exception as e:
            logger.error(f"Error obteniendo posts de {feed_id}: {str(e)}")
            return []
    
    def get_search_terms(self) -> Dict[str, Set[str]]:
        """Obtiene términos de búsqueda de la base de datos"""
        terms = {
            'artists': set(),
            'albums': set(),
            'labels': set()
        }
        
        if not os.path.exists(self.db_path):
            logger.error(f"Base de datos no encontrada: {self.db_path}")
            return terms
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener nombres de artistas
            if self.search_artists:
                cursor.execute("SELECT name FROM artists")
                for row in cursor.fetchall():
                    if row[0] and len(row[0]) > 2:  # Evitar nombres muy cortos
                        terms['artists'].add(row[0])
            
            # Obtener nombres de álbumes
            if self.search_albums:
                cursor.execute("SELECT name FROM albums")
                for row in cursor.fetchall():
                    if row[0] and len(row[0]) > 2:  # Evitar nombres muy cortos
                        terms['albums'].add(row[0])
            
            # Obtener nombres de sellos discográficos
            if self.search_labels:
                cursor.execute("SELECT name FROM labels")
                for row in cursor.fetchall():
                    if row[0] and len(row[0]) > 2:  # Evitar nombres muy cortos
                        terms['labels'].add(row[0])
            
            conn.close()
            
            # Logging de resultados
            logger.info(f"Términos de búsqueda encontrados: {len(terms['artists'])} artistas, "
                       f"{len(terms['albums'])} álbumes, {len(terms['labels'])} sellos")
            
            return terms
        except Exception as e:
            logger.error(f"Error obteniendo términos de búsqueda: {str(e)}")
            return terms
    
    def find_matching_content(self) -> List[Dict]:
        """
        Busca artículos que contengan términos relacionados con artistas, álbumes o sellos
        """
        if not self.login():
            logger.error("No se pudo iniciar sesión en FreshRSS")
            return []
        
        # Obtener términos de búsqueda
        search_terms = self.get_search_terms()
        
        # Lista para almacenar los resultados
        matching_posts = []
        
        # Procesar cada categoría
        for category in self.target_categories:
            feeds = self.get_category_feeds(category)
            logger.info(f"Procesando {len(feeds)} feeds en categoría '{category}'")
            
            # Procesar cada feed en la categoría
            for feed in feeds:
                feed_id = feed.get('id')
                feed_title = feed.get('title', 'Unknown Feed')
                logger.info(f"Analizando feed: {feed_title}")
                
                # Obtener posts
                posts = self.get_posts(feed_id)
                logger.info(f"  - {len(posts)} posts obtenidos para analizar")
                
                # Buscar coincidencias en cada post
                for post in posts:
                    matches = {
                        'artists': [],
                        'albums': [],
                        'labels': []
                    }
                    
                    content = f"{post['title']} {post['content']}".lower()
                    
                    # Buscar coincidencias de artistas
                    if self.search_artists:
                        for artist in search_terms['artists']:
                            if artist.lower() in content:
                                matches['artists'].append(artist)
                    
                    # Buscar coincidencias de álbumes
                    if self.search_albums:
                        for album in search_terms['albums']:
                            if album.lower() in content:
                                matches['albums'].append(album)
                    
                    # Buscar coincidencias de sellos
                    if self.search_labels:
                        for label in search_terms['labels']:
                            if label.lower() in content:
                                matches['labels'].append(label)
                    
                    # Si hay coincidencias, añadir a resultados
                    if matches['artists'] or matches['albums'] or matches['labels']:
                        post_result = {
                            'url': post['url'],
                            'title': post['title'],
                            'date': post['date'].isoformat(),
                            'feed': feed_title,
                            'category': category,
                            'matches': matches
                        }
                        matching_posts.append(post_result)
                        logger.info(f"  - Coincidencia encontrada: {post['title']}")
        
        # Guardar el cache actualizado
        self._save_cache()
        
        logger.info(f"Encontrados {len(matching_posts)} artículos con coincidencias")
        return matching_posts

def main(config):
    """Función principal del script"""
    finder = FreshRSSContentFinder(config)
    
    # Comprobar argumentos requeridos
    required_args = ['freshrss_url', 'freshrss_username', 'freshrss_password', 'db_path']
    missing_args = [arg for arg in required_args if not config.get(arg)]
    
    if missing_args:
        logger.error(f"Faltan argumentos requeridos: {', '.join(missing_args)}")
        return
    
    # Ejecutar la búsqueda
    matching_posts = finder.find_matching_content()
    
    # Guardar resultados si es necesario
    if config.get('output_path'):
        try:
            os.makedirs(os.path.dirname(config.get('output_path')), exist_ok=True)
            with open(config.get('output_path'), 'w') as f:
                json.dump(matching_posts, f, indent=2)
            logger.info(f"Resultados guardados en {config.get('output_path')}")
        except Exception as e:
            logger.error(f"Error guardando resultados: {str(e)}")
    
    # Mostrar resultados en consola
    print(f"\nResumen de búsqueda:")
    print(f"- Artículos encontrados: {len(matching_posts)}")
    
    for i, post in enumerate(matching_posts, 1):
        print(f"\n{i}. {post['title']}")
        print(f"   Feed: {post['feed']} ({post['category']})")
        print(f"   Fecha: {post['date']}")
        print(f"   URL: {post['url']}")
        
        if post['matches']['artists']:
            print(f"   Artistas: {', '.join(post['matches']['artists'])}")
        if post['matches']['albums']:
            print(f"   Álbumes: {', '.join(post['matches']['albums'])}")
        if post['matches']['labels']:
            print(f"   Sellos: {', '.join(post['matches']['labels'])}")
    
    print("\nProceso completado correctamente.")