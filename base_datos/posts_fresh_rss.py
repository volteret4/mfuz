import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from urllib.parse import quote
import requests
import sys
import re
from html import unescape

# Configurar logging
logger = logging.getLogger(__name__)

class FreshRSSContentFinder():
    def __init__(self, config):
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
        
        # Inicializar la base de datos
        self._setup_database()
        
    def _setup_database(self):
        """Configura la tabla feeds en la base de datos si no existe"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Crear tabla feeds si no existe
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY,
                entity_type TEXT NOT NULL,  -- 'artist', 'album', o 'label'
                entity_id INTEGER NOT NULL,
                feed_name TEXT NOT NULL,
                post_title TEXT NOT NULL,
                post_url TEXT UNIQUE NOT NULL,
                post_date TIMESTAMP,
                content TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Crear índices para búsquedas eficientes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feeds_entity_type_id ON feeds(entity_type, entity_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feeds_post_url ON feeds(post_url)')
            
            conn.commit()
            conn.close()
            logger.info("Base de datos configurada correctamente")
        except Exception as e:
            logger.error(f"Error configurando la base de datos: {str(e)}")
            raise
        
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
        """Guarda el cache actualizado con información de progreso"""
        if not self.cache_path:
            return
                
        try:
            # Asegurar que existe la estructura básica del cache
            if 'progress' not in self.cache:
                self.cache['progress'] = {}
                
            # Actualizar la marca de tiempo
            self.cache['last_updated'] = datetime.now().isoformat()
            
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w') as f:
                json.dump(self.cache, f, indent=2)
            logger.info(f"Cache guardado en {self.cache_path}")
        except Exception as e:
            logger.error(f"Error guardando cache: {str(e)}")
    
    def _save_progress(self, entity_type, current_entity_index, entity_id=None):
        """Guarda el progreso actual en el cache"""
        if 'progress' not in self.cache:
            self.cache['progress'] = {}
            
        self.cache['progress'].update({
            'entity_type': entity_type,
            'entity_index': current_entity_index,
            'entity_id': entity_id,
            'timestamp': datetime.now().isoformat()
        })
        
        self._save_cache()
        
    def _get_progress(self):
        """Obtiene el último progreso guardado"""
        if 'progress' not in self.cache:
            return None
            
        return self.cache['progress']


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
                    
                    # Eliminar etiquetas HTML del contenido
                    content_text = self._strip_html_tags(content)
                    
                    posts.append({
                        'url': url,
                        'date': published_date,
                        'title': item.get('title', 'Sin título'),
                        'month_key': published_date.strftime('%Y-%m'),
                        'feed_title': item.get('origin', {}).get('title', 'Unknown Feed'),
                        'content': content_text,
                        'raw_content': content
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
    
    def _strip_html_tags(self, html_content):
        """Elimina las etiquetas HTML de un string manteniendo el formato básico"""
        if not html_content:
            return ""
        
        # Primero decodificar entidades HTML
        text = unescape(html_content)
        
        # Reemplazar etiquetas de párrafo, div, br con saltos de línea antes de eliminarlas
        text = re.sub(r'<br\s*/?>|</?p>|</div>', '\n', text)
        
        # Eliminar el resto de etiquetas HTML
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Manejar múltiples saltos de línea (máximo 2 seguidos)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Eliminar espacios en blanco extra en cada línea pero preservar los saltos de línea
        lines = []
        for line in text.split('\n'):
            lines.append(re.sub(r'\s+', ' ', line).strip())
        
        # Volver a unir las líneas
        text = '\n'.join(lines)
        
        return text
    
    def get_search_terms(self) -> Dict[str, List[Dict]]:
        """Obtiene términos de búsqueda de la base de datos con sus IDs"""
        terms = {
            'artists': [],
            'albums': [],
            'labels': []
        }
        
        if not os.path.exists(self.db_path):
            logger.error(f"Base de datos no encontrada: {self.db_path}")
            return terms
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener nombres de artistas con sus IDs
            if self.search_artists:
                cursor.execute("SELECT id, name FROM artists")
                for row in cursor.fetchall():
                    if row[1] and len(row[1]) > 2:  # Evitar nombres muy cortos
                        terms['artists'].append({'id': row[0], 'name': row[1]})
            
            # Obtener nombres de álbumes con sus IDs
            if self.search_albums:
                cursor.execute("SELECT id, name FROM albums")
                for row in cursor.fetchall():
                    if row[1] and len(row[1]) > 2:  # Evitar nombres muy cortos
                        terms['albums'].append({'id': row[0], 'name': row[1]})
            
            # Obtener nombres de sellos discográficos con sus IDs
            if self.search_labels:
                cursor.execute("SELECT id, name FROM labels")
                for row in cursor.fetchall():
                    if row[1] and len(row[1]) > 2:  # Evitar nombres muy cortos
                        terms['labels'].append({'id': row[0], 'name': row[1]})
            
            conn.close()
            
            # Logging de resultados
            logger.info(f"Términos de búsqueda encontrados: {len(terms['artists'])} artistas, "
                       f"{len(terms['albums'])} álbumes, {len(terms['labels'])} sellos")
            
            return terms
        except Exception as e:
            logger.error(f"Error obteniendo términos de búsqueda: {str(e)}")
            return terms
    
    def _check_post_exists(self, post_url: str) -> bool:
        """Verifica si un post ya existe en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM feeds WHERE post_url = ?", (post_url,))
            result = cursor.fetchone()
            
            conn.close()
            return result is not None
        except Exception as e:
            logger.error(f"Error verificando si el post existe: {str(e)}")
            return False
    
    def _save_selected_posts(self, entity_type: str, entity_id: int, selected_posts: List[Dict]) -> int:
        """Guarda los posts seleccionados en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            posts_added = 0
            
            for post in selected_posts:
                # Verificar si el post ya existe
                if self._check_post_exists(post['url']):
                    logger.info(f"El post ya existe en la base de datos: {post['url']}")
                    continue
                
                cursor.execute('''
                INSERT INTO feeds 
                (entity_type, entity_id, feed_name, post_title, post_url, post_date, content)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entity_type,
                    entity_id,
                    post['feed'],
                    post['title'],
                    post['url'],
                    post['date'].isoformat(),
                    post['content']
                ))
                
                posts_added += 1
            
            conn.commit()
            conn.close()
            
            return posts_added
        except Exception as e:
            logger.error(f"Error guardando posts seleccionados: {str(e)}")
            return 0
    
    def find_and_process_content(self) -> None:
        """Busca artículos y permite al usuario seleccionar cuáles guardar"""
        # Configurar manejo de interrupciones
        import signal
        
        def signal_handler(sig, frame):
            print("\nDetectada interrupción manual.")
            progress = self._get_progress()
            if progress:
                entity_type = progress.get('entity_type')
                idx = progress.get('entity_index')
                entity_id = progress.get('entity_id')
                self._handle_user_interruption(entity_type, idx, entity_id)
            else:
                print("No hay progreso para guardar. Saliendo.")
                sys.exit(0)
        
        # Registrar el manejador para SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, signal_handler)

        
        if not self.login():
            logger.error("No se pudo iniciar sesión en FreshRSS")
            return
        
        # Obtener términos de búsqueda
        search_terms = self.get_search_terms()
        
        # Mapa para almacenar los posts encontrados por entidad
        entity_posts = {
            'artists': {},  # {artist_id: [posts]}
            'albums': {},   # {album_id: [posts]}
            'labels': {}    # {label_id: [posts]}
        }
        
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
                    # Añadir feed al post para referencia posterior
                    post['feed'] = feed_title
                    post['category'] = category
                    
                    content = f"{post['title']} {post['content']}".lower()
                    
                    # Buscar coincidencias de artistas
                    if self.search_artists:
                        for artist in search_terms['artists']:
                            if artist['name'].lower() in content:
                                artist_id = artist['id']
                                if artist_id not in entity_posts['artists']:
                                    entity_posts['artists'][artist_id] = {
                                        'name': artist['name'],
                                        'posts': []
                                    }
                                # Verificar que no esté duplicado
                                post_urls = [p['url'] for p in entity_posts['artists'][artist_id]['posts']]
                                if post['url'] not in post_urls:
                                    entity_posts['artists'][artist_id]['posts'].append(post)
                    
                    # Buscar coincidencias de álbumes
                    if self.search_albums:
                        for album in search_terms['albums']:
                            if album['name'].lower() in content:
                                album_id = album['id']
                                if album_id not in entity_posts['albums']:
                                    entity_posts['albums'][album_id] = {
                                        'name': album['name'],
                                        'posts': []
                                    }
                                # Verificar que no esté duplicado
                                post_urls = [p['url'] for p in entity_posts['albums'][album_id]['posts']]
                                if post['url'] not in post_urls:
                                    entity_posts['albums'][album_id]['posts'].append(post)
                    
                    # Buscar coincidencias de sellos
                    if self.search_labels:
                        for label in search_terms['labels']:
                            if label['name'].lower() in content:
                                pattern = r'\b' + re.escape(label['name'].lower()) + r'\b'
                                if re.search(pattern, content):
                                    label_id = label['id']
                                label_id = label['id']
                                if label_id not in entity_posts['labels']:
                                    entity_posts['labels'][label_id] = {
                                        'name': label['name'],
                                        'posts': []
                                    }
                                # Verificar que no esté duplicado
                                post_urls = [p['url'] for p in entity_posts['labels'][label_id]['posts']]
                                if post['url'] not in post_urls:
                                    entity_posts['labels'][label_id]['posts'].append(post)
        
        # Guardar el cache actualizado
        self._save_cache()
        
        # Procesar interactivamente los resultados
        self._interactive_selection(entity_posts)
        
    def _interactive_selection(self, entity_posts: Dict):
        """Permite al usuario seleccionar interactivamente qué posts guardar"""
        # Estadísticas
        total_entities = sum(len(entity_posts[entity_type]) for entity_type in entity_posts)
        total_posts = sum(
            sum(len(entity['posts']) for entity in entity_posts[entity_type].values())
            for entity_type in entity_posts
        )
        
        print(f"\n=== Resultados de la búsqueda ===")
        print(f"Se encontraron {total_posts} artículos en {total_entities} entidades:")
        print(f"- Artistas: {len(entity_posts['artists'])}")
        print(f"- Álbumes: {len(entity_posts['albums'])}")
        print(f"- Sellos: {len(entity_posts['labels'])}")
        print("=" * 40)
        
        # Verificar si hay progreso guardado
        progress = self._get_progress()
        start_from_type = None
        start_from_index = 0
        
        if progress:
            print(f"\n=== Progreso detectado ===")
            print(f"Última entidad procesada: {progress.get('entity_type')} (índice {progress.get('entity_index')})")
            resume = input("¿Desea continuar desde el último punto guardado? (s/n): ").lower()
            
            if resume == 's':
                start_from_type = progress.get('entity_type')
                start_from_index = progress.get('entity_index', 0)
                print(f"Continuando desde {start_from_type}, índice {start_from_index}...")
        
        # Procesar cada tipo de entidad
        entity_types = ['artists', 'albums', 'labels']
        
        # Saltar tipos de entidad si estamos reanudando
        if start_from_type:
            skip_until = entity_types.index(start_from_type)
            entity_types = entity_types[skip_until:]
        
        for entity_type in entity_types:
            entities = entity_posts[entity_type]
            type_name = {
                'artists': 'Artista',
                'albums': 'Álbum',
                'labels': 'Sello'
            }.get(entity_type, 'Entidad')
            
            if not entities:
                continue
                
            print(f"\nProcesando {len(entities)} {type_name}s:")
            
            # Convertir a lista para poder acceder por índice
            entity_items = list(entities.items())
            
            # Saltar elementos si estamos reanudando y es el tipo de entidad correcto
            start_idx = start_from_index if entity_type == start_from_type else 0
            
            # Procesar cada entidad
            for idx, (entity_id, entity_data) in enumerate(entity_items[start_idx:], start_idx):
                entity_name = entity_data['name']
                entity_posts = entity_data['posts']
                
                print(f"\n{type_name}: {entity_name} (ID: {entity_id}) - Progreso: {idx+1}/{len(entity_items)}")
                print(f"Se encontraron {len(entity_posts)} artículos:")
                
                # ... (resto del código para mostrar y seleccionar posts) ...
                
                # Guardar progreso después de procesar cada entidad
                self._save_progress(entity_type, idx + 1, entity_id)
                
                # Verificar si el usuario quiere pausar
                if idx < len(entity_items) - 1:  # No preguntar en el último elemento
                    pause = input("¿Desea pausar el proceso y continuar más tarde? (p/Enter para continuar): ")
                    if pause.lower() == 'p':
                        print(f"Proceso pausado. Se ha guardado el progreso.")
                        return
        
        # Reiniciar el progreso cuando se completa todo
        if 'progress' in self.cache:
            del self.cache['progress']
            self._save_cache()
        
        print("\nProceso completado.")


    def _handle_user_interruption(self, entity_type, current_idx, entity_id):
        """Maneja interrupciones del usuario durante el procesamiento"""
        try:
            self._save_progress(entity_type, current_idx, entity_id)
            print("\nProgreso guardado. Puede reanudar más tarde desde este punto.")
        except Exception as e:
            print(f"\nError al guardar el progreso: {str(e)}")
        finally:
            print("Proceso pausado.")
            sys.exit(0)

def main(config):
    """Función principal del script"""
    # Comprobar argumentos requeridos
    required_args = ['freshrss_url', 'freshrss_username', 'freshrss_password', 'db_path']
    missing_args = [arg for arg in required_args if not config.get(arg)]
    
    if missing_args:
        logger.error(f"Faltan argumentos requeridos: {', '.join(missing_args)}")
        return
    
    try:
        finder = FreshRSSContentFinder(config)
        
        # Ejecutar la búsqueda interactiva
        finder.find_and_process_content()
    except Exception as e:
        logger.error(f"Error en la ejecución: {str(e)}")
        import traceback
        traceback.print_exc()