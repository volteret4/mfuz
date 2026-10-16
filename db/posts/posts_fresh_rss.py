import os
import json
import sqlite3
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.db_connection import apply_pragmas
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from urllib.parse import quote
import requests
import re
from html import unescape

# Configurar logging
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30
# Tokens de palabra (unicode) usados para indexar nombres y contenido
WORD_RE = re.compile(r'\w+')


def tokenize(text: str) -> Tuple[str, ...]:
    """Divide un texto en palabras en minúsculas"""
    return tuple(WORD_RE.findall(text.lower()))

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
        # Nueva opción para permitir/bloquear términos cortos
        self.search_short_terms = config.get('search_short_terms', False)
        # Nueva opción para filtrar posts por patrones
        self.ignore_patterns = config.get('ignore_patterns', [
            'mix-for-nts', 
            'my favorite songs',
            'weekly playlist',
            'monthly mix',
            'podcast'
        ])
        
        # Sesión HTTP reutilizable (keep-alive, evita un handshake TLS por petición)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'FreshRSS-Script/1.0'

        # Cargar cache si existe
        self.cache = self._load_cache()

        # Lista para mantener los posts ya rechazados
        self.rejected_urls = set(self.cache.get('rejected_urls', []))

        # Timestamps obtenidos en esta ejecución; solo se guardan en el cache al
        # terminar la selección, para que una interrupción no pierda posts
        self._pending_timestamps = {}

        # Inicializar la base de datos
        self._setup_database()

    def _should_ignore_post(self, post):
        """Determina si un post debe ser ignorado basado en patrones configurados"""
        # Si no hay patrones a ignorar, no ignoramos nada
        if not self.ignore_patterns:
            return False
            
        # Convertir título y contenido a minúsculas para comparación insensible a mayúsculas
        title_lower = post['title'].lower()
        content_lower = post['content'].lower()
        
        # Verificar si algún patrón está presente en el título o contenido
        for pattern in self.ignore_patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in title_lower or pattern_lower in content_lower:
                logger.info(f"Ignorando post que coincide con patrón '{pattern}': {post['title']}")
                return True
                
        return False
        
    def _setup_database(self):
        """Configura la tabla feeds en la base de datos si no existe"""
        try:
            conn = sqlite3.connect(self.db_path)
            apply_pragmas(conn)
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
            
            # Guardar las URLs rechazadas
            if hasattr(self, 'rejected_urls') and self.rejected_urls:
                self.cache['rejected_urls'] = list(self.rejected_urls)
            
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
            response = self.session.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            for line in response.text.splitlines():
                if line.startswith('Auth='):
                    self.auth_token = line.replace('Auth=', '').strip()
                    self.session.headers['Authorization'] = f'GoogleLogin auth={self.auth_token}'
                    logger.info(f"Token obtenido correctamente")
                    return True
            
            logger.error("No se encontró el token de autenticación")
            return False
        except Exception as e:
            logger.error(f"Error en login: {str(e)}")
            return False

    def get_category_posts(self, category_name: str, include_read: bool = False) -> List[Dict]:
        """Obtiene los posts de todos los feeds de una categoría con una sola consulta paginada"""
        return self.get_posts(f"user/-/label/{category_name}", include_read)

    def get_posts(self, stream_id: str, include_read: bool = False) -> List[Dict[str, str]]:
        """Obtiene los posts de un stream (feed o categoría), por defecto solo los no leídos"""
        endpoint = f"{self.api_endpoint}/reader/api/0/stream/contents/{quote(stream_id)}"
        params = {
            'output': 'json',
            'n': 1000,  # Número máximo de artículos por página
        }
        
        # Si solo queremos los no leídos
        if not include_read:
            params['xt'] = 'user/-/state/com.google/read'
        
        # Obtener último timestamp guardado para este stream
        last_timestamp = self.cache.get(stream_id, {}).get('last_timestamp', 0)
        if last_timestamp > 0:
            params['ot'] = last_timestamp
        
        posts = []
        latest_timestamp = last_timestamp
        
        try:
            while True:
                response = self.session.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                
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
                
                # Paginar solo si el servidor indica que hay más resultados
                continuation = data.get('continuation')
                if not continuation:
                    break
                params['c'] = continuation
            
            self._pending_timestamps[stream_id] = latest_timestamp
            return posts
        except Exception as e:
            logger.error(f"Error obteniendo posts de {stream_id}: {str(e)}")
            return posts
    
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
            apply_pragmas(conn)
            cursor = conn.cursor()
            
            existing_tables = {row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            
            # Obtener nombres de artistas, álbumes y sellos con sus IDs
            for entity_type, table, enabled in (('artists', 'artists', self.search_artists),
                                                ('albums', 'albums', self.search_albums),
                                                ('labels', 'labels', self.search_labels)):
                if not enabled:
                    continue
                if table not in existing_tables:
                    logger.warning(f"La tabla '{table}' no existe en {self.db_path}; se omite la búsqueda de {entity_type}")
                    continue
                cursor.execute(f"SELECT id, name FROM {table}")
                for row in cursor.fetchall():
                    if row[1] and len(row[1]) > 2:  # Evitar nombres muy cortos
                        terms[entity_type].append({'id': row[0], 'name': row[1]})
            
            conn.close()
            
            # Logging de resultados
            logger.info(f"Términos de búsqueda encontrados: {len(terms['artists'])} artistas, "
                       f"{len(terms['albums'])} álbumes, {len(terms['labels'])} sellos")
            
            return terms
        except Exception as e:
            logger.error(f"Error obteniendo términos de búsqueda: {str(e)}")
            return terms
    
    def _get_existing_post_urls(self) -> Set[str]:
        """Obtiene las URLs de posts que ya están en la base de datos (una sola consulta)"""
        try:
            conn = sqlite3.connect(self.db_path)
            apply_pragmas(conn)
            urls = {row[0] for row in conn.execute("SELECT post_url FROM feeds")}
            conn.close()
            return urls
        except Exception as e:
            logger.error(f"Error obteniendo posts existentes: {str(e)}")
            return set()
    
    def _build_term_index(self, search_terms: Dict[str, List[Dict]]) -> Dict[Tuple[str, ...], List[Tuple[str, int, str]]]:
        """Indexa los nombres por su secuencia de palabras para buscarlos en O(palabras del post)"""
        index = {}
        for entity_type, terms in search_terms.items():
            for term in terms:
                name = term['name']
                # Saltarse términos cortos a menos que se permita explícitamente
                if len(name) <= 4 and not self.search_short_terms:
                    continue
                key = tokenize(name)
                if key:
                    index.setdefault(key, []).append((entity_type, term['id'], name))
        return index
    
    def _save_selected_posts(self, entity_type: str, entity_id: int, selected_posts: List[Dict]) -> int:
        """Guarda los posts seleccionados en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            apply_pragmas(conn)
            cursor = conn.cursor()
            
            posts_added = 0
            
            for post in selected_posts:
                # post_url es UNIQUE: si ya existe se ignora
                cursor.execute('''
                INSERT OR IGNORE INTO feeds 
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
                
                if cursor.rowcount:
                    posts_added += 1
                else:
                    logger.info(f"El post ya existe en la base de datos: {post['url']}")
            
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
        
        # Obtener términos de búsqueda e indexarlos por palabras
        search_terms = self.get_search_terms()
        term_index = self._build_term_index(search_terms)
        term_lengths = sorted({len(key) for key in term_index})
        
        # Posts ya guardados o rechazados no se vuelven a analizar
        known_urls = self._get_existing_post_urls() | self.rejected_urls
        
        # Mapa para almacenar los posts encontrados por entidad
        entity_posts = {
            'artists': {},  # {artist_id: {'name', 'posts', 'urls'}}
            'albums': {},   # {album_id: ...}
            'labels': {}    # {label_id: ...}
        }
        
        # Procesar cada categoría con una sola consulta (paginada) al servidor
        for category in self.target_categories:
            posts = self.get_category_posts(category)
            logger.info(f"Categoría '{category}': {len(posts)} posts obtenidos para analizar")
            
            # Buscar coincidencias en cada post
            for post in posts:
                if post['url'] in known_urls:
                    continue
                known_urls.add(post['url'])
                
                # Añadir feed al post para referencia posterior
                post['feed'] = post['feed_title']
                post['category'] = category
                
                # Verificar si el post debe ser ignorado
                if self._should_ignore_post(post):
                    continue
                
                words = tokenize(f"{post['title']} {post['content']}")
                
                # Buscar cada nombre como secuencia completa de palabras
                matches = set()
                for n in term_lengths:
                    for i in range(len(words) - n + 1):
                        entities = term_index.get(words[i:i + n])
                        if entities:
                            matches.update(entities)
                
                for entity_type, entity_id, name in matches:
                    bucket = entity_posts[entity_type].setdefault(entity_id, {'name': name, 'posts': []})
                    bucket['posts'].append(post)
        
        # Procesar interactivamente los resultados
        self._interactive_selection(entity_posts)
        
        # Solo al terminar la selección se avanzan los timestamps de cada categoría
        for stream_id, timestamp in self._pending_timestamps.items():
            self.cache.setdefault(stream_id, {})['last_timestamp'] = timestamp
        self._save_cache()
        
    def _interactive_selection(self, entity_posts: Dict):
        """Permite al usuario seleccionar interactivamente qué posts guardar"""
        # Definir colores ANSI
        class Colors:
            BLUE = '\033[94m'
            GREEN = '\033[92m'
            YELLOW = '\033[93m'
            RED = '\033[91m'
            BOLD = '\033[1m'
            UNDERLINE = '\033[4m'
            END = '\033[0m'
        
        # Estadísticas
        total_entities = sum(len(entity_posts[entity_type]) for entity_type in entity_posts)
        total_posts = sum(
            sum(len(entity['posts']) for entity in entity_posts[entity_type].values())
            for entity_type in entity_posts
        )
        
        print(f"\n=== {Colors.BOLD}Resultados de la búsqueda{Colors.END} ===")
        print(f"Se encontraron {Colors.YELLOW}{total_posts}{Colors.END} artículos en {Colors.YELLOW}{total_entities}{Colors.END} entidades:")
        print(f"- Artistas: {Colors.GREEN}{len(entity_posts['artists'])}{Colors.END}")
        print(f"- Álbumes: {Colors.GREEN}{len(entity_posts['albums'])}{Colors.END}")
        print(f"- Sellos: {Colors.GREEN}{len(entity_posts['labels'])}{Colors.END}")
        print("=" * 40)
        print(f"{Colors.BOLD}Presiona Ctrl+C en cualquier momento para pausar el proceso.{Colors.END}")
        
        # Los posts ya guardados o rechazados se descartan antes de buscar, así que
        # una sesión interrumpida continúa sola donde se quedó
        if self._get_progress():
            print(f"\n{Colors.BOLD}Continuando la sesión anterior{Colors.END} (se omiten los artículos ya revisados).")
        if self.rejected_urls:
            print(f"Cargadas {Colors.YELLOW}{len(self.rejected_urls)}{Colors.END} URLs rechazadas anteriormente.")
        
        # URLs guardadas en esta sesión (un post puede mencionar varias entidades)
        saved_urls = set()
        
        # Procesar cada tipo de entidad
        entity_types = ['artists', 'albums', 'labels']
        
        for entity_type in entity_types:
            entities = entity_posts[entity_type]
            type_name = {
                'artists': 'Artista',
                'albums': 'Álbum',
                'labels': 'Sello'
            }.get(entity_type, 'Entidad')
            
            if not entities:
                continue
                
            print(f"\n{Colors.BOLD}Procesando {len(entities)} {type_name}s:{Colors.END}")
            
            # Convertir a lista para poder acceder por índice
            entity_items = list(entities.items())
            
            # Procesar cada entidad
            for idx, (entity_id, entity_data) in enumerate(entity_items):
                entity_name = entity_data['name']
                posts = entity_data['posts']
                
                # Filtrar posts ya rechazados o guardados en esta sesión
                filtered_posts = [post for post in posts if post['url'] not in self.rejected_urls and post['url'] not in saved_urls]
                
                # Si todos los posts han sido rechazados, pasar a la siguiente entidad
                if not filtered_posts:
                    print(f"\n{Colors.BOLD}{type_name}{Colors.END}: {Colors.GREEN}{entity_name}{Colors.END} ({Colors.YELLOW}ID: {entity_id}{Colors.END}) - Progreso: {Colors.YELLOW}{idx+1}/{len(entity_items)}{Colors.END}")
                    print(f"Todos los {len(posts)} posts para esta entidad ya han sido revisados. Pasando a la siguiente.")
                    self._save_progress(entity_type, idx + 1, entity_id)
                    continue
                
                print(f"\n{Colors.BOLD}{type_name}{Colors.END}: {Colors.GREEN}{entity_name}{Colors.END} ({Colors.YELLOW}ID: {entity_id}{Colors.END}) - Progreso: {Colors.YELLOW}{idx+1}/{len(entity_items)}{Colors.END}")
                
                if len(posts) > len(filtered_posts):
                    print(f"Se encontraron {Colors.YELLOW}{len(posts)}{Colors.END} artículos, {Colors.RED}{len(posts) - len(filtered_posts)}{Colors.END} ya revisados.")
                
                print(f"Mostrando {Colors.YELLOW}{len(filtered_posts)}{Colors.END} artículos:")
                
                # Mostrar todos los posts encontrados de una vez
                for i, post in enumerate(filtered_posts):
                    print(f"{Colors.BOLD}{i+1}.{Colors.END} {Colors.YELLOW}{post['title']}{Colors.END} - {post['feed']} ({post['date'].strftime('%Y-%m-%d')})")
                    print(f"   {Colors.BLUE}{Colors.UNDERLINE}URL:{Colors.END} {Colors.BLUE}{post['url']}{Colors.END}")
                    print(f"   Extracto: {post['content'][:150]}...")
                    print()  # Línea en blanco para mejorar legibilidad
                
                # Opciones de selección
                print(f"\n{Colors.BOLD}Opciones de selección:{Colors.END}")
                print("- Ingrese números separados por espacios (ej: '1 3 5') para seleccionar posts específicos")
                print("- 'a' o 'all' para seleccionar todos")
                print("- 'n' o 'none' para no seleccionar ninguno")
                
                choice = input(f"{Colors.GREEN}Su selección:{Colors.END} ").lower().strip()
                
                selected_posts = []
                rejected_posts = []
                
                if choice in ['a', 'all', 'todos']:
                    # Seleccionar todos los posts
                    selected_posts = filtered_posts
                    print(f"Se seleccionaron {Colors.GREEN}todos{Colors.END} los posts ({Colors.YELLOW}{len(filtered_posts)}{Colors.END}).")
                elif choice in ['n', 'none', 'ninguno']:
                    # No seleccionar ningún post
                    rejected_posts = filtered_posts
                    print(f"{Colors.RED}No se seleccionó ningún post.{Colors.END}")
                else:
                    # Seleccionar posts por números
                    try:
                        # Dividir la entrada en números individuales
                        numbers = [int(num) for num in choice.split()]
                        
                        # Validar rango y seleccionar posts
                        for num in numbers:
                            if 1 <= num <= len(filtered_posts):
                                selected_posts.append(filtered_posts[num-1])
                                print(f"Post {Colors.YELLOW}{num}{Colors.END} seleccionado: {Colors.GREEN}{filtered_posts[num-1]['title']}{Colors.END}")
                            else:
                                print(f"Número {Colors.RED}{num}{Colors.END} fuera de rango. Ignorado.")
                        
                        # Los posts no seleccionados se consideran rechazados
                        for i, post in enumerate(filtered_posts, 1):
                            if i not in numbers:
                                rejected_posts.append(post)
                    except ValueError:
                        print(f"{Colors.RED}Entrada no válida. No se seleccionó ningún post.{Colors.END}")
                        rejected_posts = filtered_posts
                
                # Guardar los posts seleccionados
                if selected_posts:
                    posts_added = self._save_selected_posts(entity_type, entity_id, selected_posts)
                    saved_urls.update(post['url'] for post in selected_posts)
                    print(f"Se guardaron {Colors.GREEN}{posts_added}{Colors.END} posts nuevos para {Colors.YELLOW}{entity_name}{Colors.END}.")
                else:
                    print(f"{Colors.RED}No se guardó ningún post{Colors.END} para {Colors.YELLOW}{entity_name}{Colors.END}.")
                
                # Añadir los posts rechazados a la lista de rechazados
                for post in rejected_posts:
                    self.rejected_urls.add(post['url'])
                
                # Guardar progreso (y las URLs rechazadas) después de procesar cada entidad
                self._save_progress(entity_type, idx + 1, entity_id)
        
        # Reiniciar el progreso cuando se completa todo
        if 'progress' in self.cache:
            del self.cache['progress']
            self._save_cache()
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}Proceso completado.{Colors.END}")
        print(f"Total de URLs rechazadas: {Colors.YELLOW}{len(self.rejected_urls)}{Colors.END}")
    
    
    
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

    def clear(self):
        # Para sistemas UNIX (Linux/Mac)
        if os.name == 'posix':
            os.system('clear')
        # Para sistemas Windows
        elif os.name == 'nt':
            os.system('cls')


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