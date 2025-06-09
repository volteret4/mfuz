import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import requests

class TicketmasterService:
    """Servicio para interactuar con la API de Ticketmaster con soporte de caché"""
    
    def __init__(self, api_key, cache_dir, cache_duration=24):
        self.api_key = api_key
        self.base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
        self.cache_dir = Path(cache_dir)
        self.cache_duration = cache_duration  # horas
        
        # Crear directorio de caché si no existe
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def search_concerts_paginated(self, artist_name, country_code="ES", max_results=200):
        """
        Buscar conciertos con paginación automática para obtener todos los resultados
        
        Args:
            artist_name (str): Nombre del artista a buscar
            country_code (str): Código de país ISO (ES, US, etc.)
            max_results (int): Máximo número de resultados a obtener (para evitar bucles infinitos)
            
        Returns:
            tuple: (lista de conciertos, mensaje)
        """
        if not self.api_key:
            return [], "No se ha configurado API Key para Ticketmaster"
        
        # Comprobar caché primero
        cache_file = self._get_cache_file_path(artist_name, country_code)
        cached_data = self._load_from_cache(cache_file)
        
        if cached_data:
            return cached_data, f"Se encontraron {len(cached_data)} conciertos para {artist_name} (caché)"
        
        all_concerts = []
        page = 0
        page_size = 50  # Tamaño óptimo por página
        total_pages = None
        total_elements = None
        
        try:
            while len(all_concerts) < max_results:
                # Parámetros para esta página
                params = {
                    "keyword": artist_name,
                    "countrycode": country_code.lower(),
                    "size": str(page_size),
                    "page": str(page),
                    "apikey": self.api_key
                }
                
                print(f"Consultando página {page + 1} para {artist_name}...")
                
                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                if not response.content:
                    break
                
                data = response.json()
                
                # Verificar errores
                if 'fault' in data:
                    fault_msg = data['fault'].get('faultstring', 'Error de autenticación')
                    return [], f"Error de autenticación: {fault_msg}"
                
                if 'errors' in data:
                    error_msg = data['errors'][0].get('detail', 'Error desconocido')
                    return [], f"Error de API: {error_msg}"
                
                # Verificar estructura
                if '_embedded' not in data or 'events' not in data['_embedded']:
                    break
                
                events = data['_embedded']['events']
                
                # Información de paginación
                if 'page' in data:
                    page_info = data['page']
                    total_pages = page_info.get('totalPages', 1)
                    total_elements = page_info.get('totalElements', len(events))
                    current_page = page_info.get('number', page)
                    
                    print(f"Página {current_page + 1}/{total_pages} - {len(events)} eventos en esta página")
                
                # Procesar eventos de esta página
                page_concerts = []
                for event in events:
                    try:
                        concert = self._process_event(event, artist_name)
                        if concert:
                            page_concerts.append(concert)
                    except Exception as e:
                        print(f"Error procesando evento: {e}")
                        continue
                
                all_concerts.extend(page_concerts)
                
                # Verificar si hay más páginas
                if total_pages and page >= total_pages - 1:
                    print(f"Última página alcanzada ({page + 1}/{total_pages})")
                    break
                
                if len(events) < page_size:
                    print("Página incompleta, no hay más resultados")
                    break
                
                # Pasar a la siguiente página
                page += 1
                
                # Pausa entre requests para no sobrecargar la API
                import time
                time.sleep(0.2)
            
            # Guardar en caché si hay resultados
            if all_concerts:
                self._save_to_cache(cache_file, all_concerts)
            
            # Mensaje informativo
            message_parts = [f"Se encontraron {len(all_concerts)} conciertos para {artist_name}"]
            if total_elements and total_elements > len(all_concerts):
                message_parts.append(f"(limitado a {max_results} de {total_elements} totales)")
            if total_pages and total_pages > 1:
                message_parts.append(f"({page + 1} páginas consultadas)")
            
            return all_concerts, " ".join(message_parts)
            
        except requests.exceptions.Timeout:
            return all_concerts, f"Timeout - se obtuvieron {len(all_concerts)} conciertos parciales"
        except requests.exceptions.RequestException as e:
            return all_concerts, f"Error en solicitud - se obtuvieron {len(all_concerts)} conciertos parciales: {str(e)}"
        except Exception as e:
            import traceback
            print(f"Error inesperado: {traceback.format_exc()}")
            return all_concerts, f"Error inesperado - se obtuvieron {len(all_concerts)} conciertos parciales: {str(e)}"

    def _process_event(self, event, artist_name):
        """
        Procesar un evento individual y convertirlo en formato de concierto
        
        Args:
            event (dict): Datos del evento de Ticketmaster
            artist_name (str): Nombre del artista
            
        Returns:
            dict: Datos del concierto procesados o None si hay error
        """
        try:
            # Extraer datos del venue
            venues = event.get('_embedded', {}).get('venues', [])
            venue_data = venues[0] if venues else {}
            
            # Construir dirección
            address_parts = []
            address_obj = venue_data.get('address', {})
            if address_obj.get('line1'):
                address_parts.append(address_obj['line1'])
            if address_obj.get('line2'):
                address_parts.append(address_obj['line2'])
            if venue_data.get('postalCode'):
                address_parts.append(venue_data['postalCode'])
            
            address = ', '.join(address_parts)
            
            # Extraer fecha y hora
            dates = event.get('dates', {})
            start_date = dates.get('start', {})
            local_date = start_date.get('localDate', 'Unknown date')
            local_time = start_date.get('localTime', '')
            
            # Extraer imagen
            images = event.get('images', [])
            image_url = ''
            if images:
                # Buscar imagen ideal (16:9, resolución media)
                for img in images:
                    if (img.get('ratio') == '16_9' and 
                        img.get('width', 0) > 500 and 
                        img.get('width', 0) < 1200):
                        image_url = img.get('url', '')
                        break
                
                # Fallback a primera imagen disponible
                if not image_url:
                    image_url = images[0].get('url', '')
            
            # Extraer ciudad
            city_obj = venue_data.get('city', {})
            city_name = city_obj.get('name', 'Unknown city')
            
            # Crear objeto concierto
            concert = {
                'artist': artist_name,
                'name': event.get('name', 'No title'),
                'venue': venue_data.get('name', 'Unknown venue'),
                'address': address,
                'city': city_name,
                'date': local_date,
                'time': local_time,
                'image': image_url,
                'url': event.get('url', ''),
                'id': event.get('id', ''),
                'source': 'Ticketmaster'
            }
            
            return concert
            
        except Exception as e:
            print(f"Error procesando evento individual: {e}")
            return None

    def search_concerts(self, artist_name, country_code="ES", size=50):
        """
        Método original actualizado para usar paginación por defecto
        
        Args:
            artist_name (str): Nombre del artista a buscar
            country_code (str): Código de país ISO (ES, US, etc.)
            size (int): Número máximo de resultados (se usa como límite total)
            
        Returns:
            tuple: (lista de conciertos, mensaje)
        """
        # Usar la función paginada con el size como límite máximo
        return self.search_concerts_paginated(artist_name, country_code, max_results=size)

    def get_pagination_info(self, artist_name, country_code="ES"):
        """
        Obtener información de paginación sin descargar todos los resultados
        
        Args:
            artist_name (str): Nombre del artista
            country_code (str): Código de país
            
        Returns:
            dict: Información de paginación (total_pages, total_elements, etc.)
        """
        params = {
            "keyword": artist_name,
            "countrycode": country_code.lower(),
            "size": "1",  # Solo necesitamos info de paginación
            "page": "0",
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if 'page' in data:
                page_info = data['page']
                return {
                    'total_pages': page_info.get('totalPages', 0),
                    'total_elements': page_info.get('totalElements', 0),
                    'size': page_info.get('size', 0),
                    'has_multiple_pages': page_info.get('totalPages', 0) > 1
                }
            
            return {'total_pages': 0, 'total_elements': 0, 'size': 0, 'has_multiple_pages': False}
            
        except Exception as e:
            print(f"Error obteniendo información de paginación: {e}")
            return {'error': str(e)}
    
    def _get_cache_file_path(self, artist_name, country_code):
        """Generar ruta al archivo de caché para un artista y país"""
        # Normalizar nombre para archivo
        safe_name = "".join(x for x in artist_name if x.isalnum() or x in " _-").rstrip()
        safe_name = safe_name.replace(" ", "_").lower()
        
        return self.cache_dir / f"ticketmaster_{safe_name}_{country_code}.json"
    
    def _load_from_cache(self, cache_file):
        """Cargar datos de caché si existen y son válidos"""
        if not cache_file.exists():
            return None
        
        try:
            # Verificar si el archivo es reciente
            file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            cache_age = datetime.now() - file_time
            
            if cache_age > timedelta(hours=self.cache_duration):
                # Caché expirado
                return None
            
            # Cargar datos
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Verificar timestamp del caché
                if 'timestamp' in data:
                    cache_time = datetime.fromisoformat(data['timestamp'])
                    if (datetime.now() - cache_time) > timedelta(hours=self.cache_duration):
                        return None
                    
                    # Devolver solo los conciertos (no el timestamp)
                    return data.get('concerts', [])
                else:
                    # Formato antiguo sin timestamp
                    return data
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error leyendo caché: {e}")
            return None
    
    def _save_to_cache(self, cache_file, concerts):
        """Guardar resultados en caché"""
        try:
            # Guardar con timestamp
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'concerts': concerts
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Error guardando caché: {e}")
    
    def clear_cache(self, artist_name=None, country_code=None):
        """
        Limpiar caché con logging mejorado
        
        Args:
            artist_name (str, optional): Si se proporciona, solo limpia caché de ese artista
            country_code (str, optional): Si se proporciona junto con artist_name, solo limpia 
                                        caché de ese artista en ese país
        """
        try:
            files_deleted = 0
            
            if artist_name and country_code:
                # Limpiar caché específico
                cache_file = self._get_cache_file_path(artist_name, country_code)
                if cache_file.exists():
                    cache_file.unlink()
                    files_deleted = 1
                    print(f"Caché limpiado para {artist_name} en {country_code}")
            elif artist_name:
                # Limpiar todos los cachés de un artista
                safe_name = "".join(x for x in artist_name if x.isalnum() or x in " _-").rstrip()
                safe_name = safe_name.replace(" ", "_").lower()
                
                for file in self.cache_dir.glob(f"ticketmaster_{safe_name}_*.json"):
                    file.unlink()
                    files_deleted += 1
                print(f"Limpiados {files_deleted} archivos de caché para {artist_name}")
            else:
                # Limpiar todos los cachés
                for file in self.cache_dir.glob("ticketmaster_*.json"):
                    file.unlink()
                    files_deleted += 1
                print(f"Limpiados {files_deleted} archivos de caché de Ticketmaster")
                
            return files_deleted
            
        except Exception as e:
            print(f"Error limpiando caché: {e}")
            return 0