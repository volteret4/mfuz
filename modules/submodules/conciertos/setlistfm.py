import requests
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import time
from pathlib import Path
import json
import re
from datetime import datetime, timedelta
import sys 
import os

import sys
import os



def _setup_imports():
    """
    Configurar imports de manera robusta evitando conflictos entre módulos
    """
    import sys
    import os
    from pathlib import Path
    
    # Método 1: Intentar obtener PROJECT_ROOT del contexto actual
    project_root = None
    
    # Si estamos siendo importados desde el módulo principal, usar su PROJECT_ROOT
    try:
        # Buscar en los módulos ya cargados
        for module_name, module in sys.modules.items():
            if hasattr(module, 'PROJECT_ROOT'):
                project_root = str(module.PROJECT_ROOT)
                print(f"Found PROJECT_ROOT from module {module_name}: {project_root}")
                break
    except Exception as e:
        print(f"Error getting PROJECT_ROOT from modules: {e}")
    
    # Método 2: Calcular desde la ubicación actual del archivo
    if not project_root:
        try:
            current_file = Path(__file__)
            # setlistfm.py está en: PROJECT_ROOT/modules/submodules/conciertos/
            # Necesitamos subir 4 niveles para llegar a PROJECT_ROOT
            potential_root = current_file.parent.parent.parent.parent
            
            # Verificar que es realmente PROJECT_ROOT buscando archivos característicos
            if (potential_root / 'main.py').exists() or (potential_root / 'config').exists():
                project_root = str(potential_root)
                print(f"Calculated PROJECT_ROOT from file location: {project_root}")
        except Exception as e:
            print(f"Error calculating PROJECT_ROOT: {e}")
    
    # Método 3: Buscar en directorios padre hasta encontrar main.py
    if not project_root:
        try:
            current_dir = Path(__file__).parent
            for _ in range(6):  # Buscar hasta 6 niveles arriba
                if (current_dir / 'main.py').exists():
                    project_root = str(current_dir)
                    print(f"Found PROJECT_ROOT by searching upwards: {project_root}")
                    break
                current_dir = current_dir.parent
                if str(current_dir) == str(current_dir.parent):  # Llegamos al root del sistema
                    break
        except Exception as e:
            print(f"Error searching for PROJECT_ROOT upwards: {e}")
    
    # Si encontramos PROJECT_ROOT, añadirlo al path
    if project_root:
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            print(f"Added {project_root} to sys.path")
        return project_root
    
    print("WARNING: Could not determine PROJECT_ROOT")
    return None

def _import_mb_artist_info():
    """
    Importar mb_artist_info de manera segura con múltiples fallbacks
    """
    try:
        import sys
        # Configurar el path primero
        project_root = _setup_imports()
        
        # Intentar la importación directa
        try:
            import db.musicbrainz.mb_artist_info as mb_artist_info
            print("Successfully imported mb_artist_info directly")
            return mb_artist_info
        except ImportError as e:
            print(f"Direct import failed: {e}")
        
        # Intentar importación absoluta si tenemos PROJECT_ROOT
        if project_root:
            try:
                # Añadir la ruta específica del módulo mb_artist_info
                mb_path = os.path.join(project_root, 'db', 'musicbrainz')
                if mb_path not in sys.path:
                    sys.path.insert(0, mb_path)
                
                import mb_artist_info
                print("Successfully imported mb_artist_info from specific path")
                return mb_artist_info
            except ImportError as e:
                print(f"Specific path import failed: {e}")
        
        # Último intento: importación relativa desde la ubicación actual
        try:
            import sys
            current_dir = os.path.dirname(__file__)
            mb_dir = os.path.join(current_dir, '..', '..', '..', 'db', 'musicbrainz')
            mb_dir = os.path.abspath(mb_dir)
            
            if os.path.exists(mb_dir) and mb_dir not in sys.path:
                sys.path.insert(0, mb_dir)
                import mb_artist_info
                print("Successfully imported mb_artist_info via relative path")
                return mb_artist_info
        except Exception as e:
            print(f"Relative path import failed: {e}")
        
        print("All import attempts failed - mb_artist_info not available")
        return None
        
    except Exception as e:
        print(f"Critical error in _import_mb_artist_info: {e}")
        return None

# Realizar la importación al cargar el módulo
mb_artist_info = _import_mb_artist_info()
class SetlistfmService:
    def __init__(self, api_key, cache_dir, cache_duration=24, db_path=None, config=None):
        """Initialize the Setlist.fm service - versión mejorada sin conflictos"""
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.cache_duration = cache_duration
        self.base_url = "https://api.setlist.fm/rest/1.0/search/setlists"
        self.db_path = db_path
        
        # Configurar logging de manera más específica para evitar conflictos
        import logging
        
        # Crear un logger específico para este módulo
        self.logger = logging.getLogger(f"{__name__}.SetlistfmService")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(name)s] %(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Verificar que mb_artist_info se importó correctamente
        global mb_artist_info
        if mb_artist_info is None:
            self.logger.warning("MusicBrainz module not available - some features will be limited")
            self.mb_available = False
        else:
            self.mb_available = True
            self.logger.info("MusicBrainz module loaded successfully")
            
            # Configurar MusicBrainz si se proporciona config
            if config:
                try:
                    # Crear diccionario de credenciales MusicBrainz
                    user_agent_config = config.get('user_agent', {})
                    mb_config = {
                        'user_agent': user_agent_config,
                        'cache_directory': config.get('cache_directory')
                    }
                    
                    # Configurar MusicBrainz con las credenciales correctas
                    if hasattr(mb_artist_info, 'setup_musicbrainz'):
                        mb_artist_info.setup_musicbrainz(
                            user_agent=user_agent_config,
                            cache_directory=config.get('cache_directory')
                        )
                        self.logger.info("MusicBrainz configured successfully")
                    else:
                        self.logger.warning("MusicBrainz module doesn't have setup_musicbrainz method")
                except Exception as e:
                    self.logger.warning(f"Error configuring MusicBrainz: {e}")
                    self.mb_available = False




    def search_concerts(self, artist_name, country_code="ES"):
        """Buscar conciertos próximos usando web scraping"""
        return self.get_upcoming_concerts(artist_name, country_code)


    def _search_artist_by_mbid(self, mbid):
        """Busca un artista en Setlist.fm usando MBID"""
        try:
            url = f"https://api.setlist.fm/rest/1.0/search/artists?artistMbid={mbid}&p=1&sort=sortName"
            headers = {
                'Accept': 'application/json',
                'x-api-key': self.api_key
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 429:
                time.sleep(5)
                response = requests.get(url, headers=headers)
                
            if response.status_code == 200:
                data = response.json()
                if 'artist' in data and data['artist']:
                    return data['artist'][0].get('id')
                    
        except Exception as e:
            self.logger.error(f"Error searching artist by MBID {mbid}: {e}")
            
        return None
        
    def get_artist_setlistfm_id(self, artist_name):
        """
        Obtiene el ID de Setlist.fm para un artista - versión mejorada con mejor aislamiento
        """
        if not self.db_path:
            self.logger.info(f"No DB path configured for {artist_name}")
            return None
            
        try:
            # Conectar a la base de datos con manejo de errores mejorado
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Buscar setlistfm_id en la tabla artists
            cursor.execute("SELECT setlist_id FROM artists_setlistfm WHERE artist_name = ?", (artist_name,))
            result = cursor.fetchone()
            
            if result and result['setlistfm_id']:
                self.logger.info(f"Found cached setlistfm_id for {artist_name}: {result['setlistfm_id']}")
                conn.close()
                return result['setlistfm_id']
                
            # Si no existe, buscar mbid
            cursor.execute("SELECT mbid FROM artists WHERE name = ?", (artist_name,))
            result = cursor.fetchone()
            
            if result and result['mbid']:
                self.logger.info(f"Found MBID for {artist_name}: {result['mbid']}")
                setlistfm_id = self._get_setlistfm_id_by_mbid(result['mbid'])
                if setlistfm_id:
                    self.logger.info(f"Obtained setlistfm_id from MBID for {artist_name}: {setlistfm_id}")
                    # Actualizar la tabla artists con el setlistfm_id
                    cursor.execute("UPDATE artists_setlistfm SET setlist_id = ? WHERE artist_name = ?", 
                                (setlistfm_id, artist_name))
                    conn.commit()
                conn.close()
                return setlistfm_id
            
            conn.close()
            
            # Si no existe mbid, obtenerlo usando MusicBrainz (solo si está disponible)
            if not self.mb_available:
                self.logger.info(f"MusicBrainz not available, cannot search for {artist_name}")
                return None
                
            self.logger.info(f"No MBID found for {artist_name}, searching in MusicBrainz...")
            
            # Usar el módulo global mb_artist_info de manera segura
            global mb_artist_info
            if mb_artist_info and hasattr(mb_artist_info, 'search_artist_in_musicbrainz'):
                mb_results = mb_artist_info.search_artist_in_musicbrainz(artist_name)
                
                if mb_results and mb_results[0] and 'id' in mb_results[0]:
                    mbid = mb_results[0]['id']
                    self.logger.info(f"Found new MBID for {artist_name}: {mbid}")
                    setlistfm_id = self._get_setlistfm_id_by_mbid(mbid)
                    
                    if setlistfm_id:
                        self.logger.info(f"Obtained setlistfm_id for {artist_name}: {setlistfm_id}")
                        # Actualizar la tabla artists
                        conn = sqlite3.connect(self.db_path)
                        cursor = conn.cursor()
                        cursor.execute("""UPDATE artists_setlistfm SET setlist_id = ? WHERE artist_name = ?""", 
                                    (setlistfm_id, artist_name))
                        conn.commit()
                        conn.close()                              
                        # cursor.execute("""UPDATE artists mbid = ? WHERE name = ?""", 
                        #             (mbid, artist_name))
                        # conn.commit()
                        # conn.close()
                        
                    return setlistfm_id
                else:
                    self.logger.info(f"No MBID found in MusicBrainz for {artist_name}")
            else:
                self.logger.warning("MusicBrainz search function not available")
                    
        except Exception as e:
            self.logger.error(f"Error searching for artist {artist_name}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            
        return None


    def _get_setlistfm_id_by_mbid(self, mbid):
        """
        Obtiene el setlistfm_id de un artista usando su MBID - versión robusta
        """
        try:
            import requests
            import time
            import re
            
            url = f"https://api.setlist.fm/rest/1.0/search/artists"
            headers = {
                'Accept': 'application/json',
                'x-api-key': self.api_key,
                'User-Agent': 'SetlistfmService/1.0'  # Añadir User-Agent
            }
            params = {
                'artistMbid': mbid,
                'p': 1,
                'sort': 'sortName'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 404:
                self.logger.info(f"Artist not found in Setlist.fm for MBID {mbid}")
                return None
            
            if response.status_code == 429:  # Too Many Requests
                self.logger.warning(f"Rate limit reached for MBID {mbid}, waiting...")
                time.sleep(60)
                # Reintentar una vez más
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code != 200:
                    self.logger.error(f"Still rate limited after waiting for MBID {mbid}")
                    return None
            
            if response.status_code != 200:
                self.logger.error(f"HTTP {response.status_code} getting setlistfm_id for MBID {mbid}")
                return None
            
            data = response.json()
            artists = data.get('artist', [])
            
            if artists and len(artists) > 0:
                artist_url = artists[0].get('url')
                if artist_url:
                    # Extraer el ID de la URL
                    # https://www.setlist.fm/setlists/the-beatles-23d6a88b.html
                    match = re.search(r'-([0-9a-f]+)\.html$', artist_url)
                    if match:
                        setlistfm_id = match.group(1)
                        self.logger.info(f"Extracted setlistfm_id {setlistfm_id} from URL {artist_url}")
                        return setlistfm_id
                    else:
                        self.logger.warning(f"Could not extract ID from URL: {artist_url}")
                else:
                    self.logger.warning(f"No URL found for artist with MBID {mbid}")
            else:
                self.logger.info(f"No artists found for MBID {mbid}")
            
            return None
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error getting setlistfm_id for MBID {mbid}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting setlistfm_id for MBID {mbid}: {e}")
            return None

    def get_upcoming_concerts(self, artist_name, country_code="ES"):
        """Obtiene conciertos próximos mediante web scraping y enriquece con datos del venue"""
        setlistfm_id = self.get_artist_setlistfm_id(artist_name)
        current_year = datetime.now().year

        if not setlistfm_id:
            message = f"No Setlist.fm ID found for {artist_name}"
            self.logger.error(message)
            return [], message
            
        # Verificar cache
        cache_key = f"setlistfm_upcoming_{setlistfm_id}_{country_code}_{current_year}"
        cache_hash = self._get_cache_hash(cache_key)
        cache_file = self.cache_dir / f"setlistfm_{cache_hash}.json"
        
        cached_data = self._load_from_cache(cache_file)
        if cached_data:
            message = f"Found {len(cached_data)} upcoming concerts for {artist_name} (cache)"
            self.logger.info(message)
            return cached_data, message
            
        try:
            all_concerts = []
            page = 1
            has_more_pages = True
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            while has_more_pages:
                # Construir URL con filtros específicos de año
                url = f"https://www.setlist.fm/search?artist={setlistfm_id}&year={current_year}&upcoming=true&page={page}"
                
                self.logger.info(f"===== SETLIST.FM DEBUG =====")
                self.logger.info(f"Artist: {artist_name}")
                self.logger.info(f"Setlistfm ID: {setlistfm_id}")
                self.logger.info(f"Year: {current_year}")
                self.logger.info(f"Page: {page}")
                self.logger.info(f"URL: {url}")
                self.logger.info(f"==========================")
                
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Tu selector existente
                concert_blocks = soup.select('div.row.contentBox.visiblePrint div.col-xs-12.setlistPreview')
                
                self.logger.info(f"Found {len(concert_blocks)} concert blocks on page {page}")
                
                # Si no hay bloques en esta página, terminar
                if not concert_blocks:
                    has_more_pages = False
                    break
                
                for idx, block in enumerate(concert_blocks):
                    try:
                        # Debug: Mostrar información de cada bloque
                        self.logger.info(f"Processing concert block {idx+1} on page {page}")
                        
                        # Extraer fecha
                        date_div = block.select_one('.dateBlock')
                        if date_div:
                            month = date_div.select_one('.month')
                            day = date_div.select_one('.day')
                            year = date_div.select_one('.year')
                            
                            if month and day and year:
                                month_text = month.text.strip()
                                day_text = day.text.strip()
                                year_text = year.text.strip()
                                
                                self.logger.info(f"Date found: {month_text} {day_text} {year_text}")
                                
                                # Convertir a formato YYYY-MM-DD
                                month_num = {
                                    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                                    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                                    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                                }.get(month_text, '01')
                                
                                formatted_date = f"{year_text}-{month_num}-{day_text.zfill(2)}"
                            else:
                                self.logger.warning(f"Missing date elements in block {idx+1}")
                                formatted_date = "Unknown"
                        else:
                            self.logger.warning(f"No date div found in block {idx+1}")
                            formatted_date = "Unknown"
                        
                        # Extraer detalles del concierto
                        details = block.select_one('.details')
                        if details:
                            # Obtener el nombre del concierto directamente del h2
                            h2 = block.select_one('h2 a')
                            concert_name = h2.text.strip() if h2 else f"{artist_name} concert"
                            
                            # Artista
                            artist_span = details.select_one('strong a span')
                            artist_name_concert = artist_span.text.strip() if artist_span else artist_name
                            
                            # Tour
                            tour_name = ''
                            tour_span = details.select_one('span:nth-of-type(2)')
                            if tour_span and 'Tour:' in tour_span.text:
                                tour_link = tour_span.select_one('strong a')
                                if tour_link:
                                    tour_name = tour_link.text.strip()
                            
                            # Venue
                            venue_name = ''
                            city = ''
                            country = ''
                            venue_url = ''
                            
                            venue_span = details.select_one('span:nth-of-type(3)')
                            if venue_span and 'Venue:' in venue_span.text:
                                venue_link = venue_span.select_one('strong a')
                                venue_span_text = venue_span.select_one('strong a span')
                                
                                if venue_link:
                                    venue_url = venue_link.get('href', '')
                                    if venue_url and not venue_url.startswith('http'):
                                        venue_url = f"https://www.setlist.fm{venue_url}"
                                
                                if venue_span_text:
                                    venue_text = venue_span_text.text.strip()
                                    parts = venue_text.split(', ')
                                    venue_name = parts[0] if parts else venue_text
                                    if len(parts) > 1:
                                        city = parts[1]
                                    if len(parts) > 2:
                                        country = parts[2]
                            
                            # URL del concierto
                            setlist_link = h2 if h2 else block.select_one('a[href*="setlist"]')
                            concert_url = f"https://www.setlist.fm{setlist_link['href']}" if setlist_link and 'href' in setlist_link.attrs else ''
                            
                            # Crear el objeto concierto
                            concert = {
                                'artist': artist_name_concert,
                                'name': concert_name,
                                'venue': venue_name,
                                'city': city,
                                'country': country,
                                'date': formatted_date,
                                'url': concert_url,
                                'id': setlistfm_id,
                                'source': 'Setlist.fm'
                            }
                            
                            # Si tenemos la URL del venue, obtener detalles adicionales
                            if venue_url:
                                # Hacer una pausa breve para no saturar el servidor
                                time.sleep(0.3)
                                
                                venue_details = self.get_venue_details(venue_url)
                                if venue_details:
                                    concert['venue_details'] = venue_details
                            
                            self.logger.info(f"Concert extracted: {concert}")
                            all_concerts.append(concert)
                        else:
                            self.logger.warning(f"No details found in block {idx+1}")
                                
                    except Exception as e:
                        self.logger.warning(f"Error parsing concert block {idx+1}: {e}")
                        continue
                
                # Verificar si hay una página siguiente
                next_page_link = soup.select_one('.listPagingNavigator > li:nth-last-child(1) > a')

                if next_page_link and 'page=' in next_page_link.get('href', ''):
                    # Extractar el href completo
                    next_url = next_page_link.get('href')
                    
                    # Verificar que la URL sigue conteniendo el filtro de año
                    if f'year={current_year}' in next_url and 'upcoming=true' in next_url:
                        page_match = re.search(r'page=(\d+)', next_url)
                        if page_match:
                            page = int(page_match.group(1))
                            self.logger.info(f"Navegando a página {page}")
                            time.sleep(0.5)
                        else:
                            has_more_pages = False
                    else:
                        # Si Setlist.fm nos está redirigiendo a una página sin el filtro de año, detenemos
                        has_more_pages = False
                        self.logger.info(f"Filtro de año perdido, deteniendo navegación")
                else:
                    has_more_pages = False
                    self.logger.info(f"No se encontraron más páginas para el año {current_year}")
            
            # Guardar en cache
            self._save_to_cache(cache_file, all_concerts)
            
            message = f"Found {len(all_concerts)} upcoming events for {artist_name} from Setlist.fm across {page} pages"
            self.logger.info(message)
            return all_concerts, message
            
        except Exception as e:
            message = f"Error fetching setlist.fm data: {str(e)}"
            self.logger.error(message)
            return [], message

    def _load_from_cache(self, cache_file):
        """
        Load data from cache if valid
        
        Args:
            cache_file (Path): Path to the cache file
            
        Returns:
            list/dict: Cached data or None if invalid
        """
        if not cache_file.exists():
            return None
        
        # Check cache age
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        cache_age = datetime.now() - file_time
        
        if cache_age > timedelta(hours=self.cache_duration):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _save_to_cache(self, cache_file, data):
        """
        Save data to cache
        
        Args:
            cache_file (Path): Path to the cache file
            data (list/dict): Data to save
        """
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def clear_cache(self):
        """Clear all cache files for this service - versión mejorada"""
        try:
            import glob
            import os
            
            # Usar glob para encontrar archivos de caché específicos de setlistfm
            cache_pattern = os.path.join(self.cache_dir, "setlistfm_*.json")
            cache_files = glob.glob(cache_pattern)
            
            removed_count = 0
            for file_path in cache_files:
                try:
                    os.unlink(file_path)
                    removed_count += 1
                except Exception as e:
                    self.logger.warning(f"Could not remove cache file {file_path}: {e}")
            
            self.logger.info(f"Cleared {removed_count} setlistfm cache files")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return False


    def get_setlistfm_id_by_mbid(mbid, api_key, retry_count=0):
        """Obtiene el setlistfm_id de un artista usando su MBID"""
        url = f"https://api.setlist.fm/rest/1.0/search/artists"
        headers = {
            'Accept': 'application/json',
            'x-api-key': api_key
        }
        params = {
            'artistMbid': mbid,
            'p': 1,
            'sort': 'sortName'
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 404:
            return None
        
        if response.status_code == 429:  # Too Many Requests
            if retry_count >= 2:
                print(f"Rate limit alcanzado para MBID {mbid} después de 2 intentos, saltando al siguiente artista...")
                return None
                
            print(f"Rate limit alcanzado para MBID {mbid}, esperando 60 segundos... (intento {retry_count + 1}/2)")
            time.sleep(60)
            return get_setlistfm_id_by_mbid(mbid, api_key, retry_count + 1)
        
        if response.status_code != 200:
            print(f"Error al obtener setlistfm_id para MBID {mbid}: {response.status_code}")
            print(response.text)
            return None
        
        data = response.json()
        artists = data.get('artist', [])
        
        if artists and len(artists) > 0:
            artist_url = artists[0].get('url')
            if artist_url:
                # Extraer el ID de la URL
                # https://www.setlist.fm/setlists/the-beatles-23d6a88b.html
                match = re.search(r'-([0-9a-f]+)\.html$', artist_url)
                if match:
                    return match.group(1)
        
        return None


    def _get_cache_hash(self, key):
        """Genera un hash para usar como nombre de archivo cache"""
        import hashlib
        return hashlib.md5(key.encode()).hexdigest()

    def get_venue_details(self, venue_url):
        """
        Obtiene información detallada de un venue desde su página en Setlist.fm
        
        Args:
            venue_url (str): URL completa del venue en Setlist.fm
            
        Returns:
            dict: Diccionario con los detalles del venue
        """
        try:
            # Verificar formato de URL
            if not venue_url.startswith('http'):
                venue_url = f"https://www.setlist.fm{venue_url}"
                
            # Hacer la solicitud con headers para evitar bloqueos
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            self.logger.info(f"Obteniendo detalles del venue: {venue_url}")
            response = requests.get(venue_url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar el div de información
            info_div = soup.select_one('div.info')
            if not info_div:
                return {}
                
            venue_details = {}
            
            # Extraer todos los grupos de información
            form_groups = info_div.select('div.form-group')
            for group in form_groups:
                label = group.select_one('span.label')
                if not label:
                    continue
                    
                label_text = label.text.strip()
                
                # Extraer información según el tipo de campo
                if label_text == "City":
                    city_span = group.select_one('span:nth-of-type(1)')
                    if city_span:
                        venue_details['city'] = city_span.text.strip()
                        
                    # Verificar si hay información de cercanía
                    near_span = group.select_one('span.small')
                    if near_span:
                        near_text = near_span.text.strip()
                        if near_text.startswith('(near ') and near_text.endswith(')'):
                            venue_details['near'] = near_text[6:-1]  # Extraer texto entre paréntesis
                    
                elif label_text == "Address":
                    address_span = group.select_one('span.address')
                    if address_span:
                        # Obtener texto completo de la dirección
                        venue_details['address'] = address_span.text.strip()
                        
                elif label_text == "Opened":
                    year_span = group.select_one('span > span')
                    if year_span:
                        try:
                            venue_details['opened'] = int(year_span.text.strip())
                        except ValueError:
                            venue_details['opened'] = year_span.text.strip()
                            
                elif label_text == "Web":
                    # Extraer todos los enlaces
                    links = group.select('a.nested')
                    website_links = []
                    
                    for link in links:
                        url = link.get('href', '')
                        label = link.select_one('span')
                        label_text = label.text.strip() if label else ''
                        
                        website_links.append({
                            'url': url,
                            'label': label_text
                        })
                        
                    venue_details['websites'] = website_links
                    
                elif label_text == "Info":
                    info_span = group.select_one('span')
                    if info_span:
                        venue_details['description'] = info_span.text.strip()
                        
                elif label_text == "Also known as":
                    # Extraer todos los nombres alternativos
                    alt_names = []
                    for span in group.select('span:not(.label)'):
                        name = span.text.strip()
                        if name and name != ',':  # Ignorar comas sueltas
                            alt_names.append(name.rstrip(',').strip())
                            
                    venue_details['alt_names'] = alt_names
            
            return venue_details
            
        except Exception as e:
            self.logger.error(f"Error obteniendo detalles del venue: {str(e)}")
            return {}