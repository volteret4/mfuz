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
    
    def search_concerts(self, artist_name, country_code="ES", size=50):
        """
        Buscar conciertos para un artista en un país específico, primero en caché y luego en API
        
        Args:
            artist_name (str): Nombre del artista a buscar
            country_code (str): Código de país ISO (ES, US, etc.)
            size (int): Número máximo de resultados
            
        Returns:
            tuple: (lista de conciertos, mensaje)
        """
        if not self.api_key:
            return [], "No se ha configurado API Key para Ticketmaster"
        
        # Comprobar si tenemos resultado en caché válido
        cache_file = self._get_cache_file_path(artist_name, country_code)
        cached_data = self._load_from_cache(cache_file)
        
        if cached_data:
            return cached_data, f"Se encontraron {len(cached_data)} conciertos para {artist_name} (caché)"
        
        # Si no hay caché válido, consultar API
        # Parámetros exactos que funcionan en tu curl
        params = {
            "keyword": artist_name,
            "countrycode": country_code.lower(),  # Minúsculas como en tu curl
            "size": size,
            "apikey": self.api_key  # Sin parámetros adicionales primero
        }
        
        try:
            print(f"Consultando Ticketmaster API para {artist_name} con parámetros: {params}")
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Verificar si la respuesta tiene contenido
            if not response.content:
                return [], f"Respuesta vacía de la API para {artist_name}"
            
            data = response.json()
            
            # Verificar estructura de respuesta según documentación oficial
            if '_embedded' not in data:
                if 'errors' in data:
                    error_msg = data['errors'][0].get('detail', 'Error desconocido')
                    return [], f"Error de API: {error_msg}"
                elif 'fault' in data:
                    fault_msg = data['fault'].get('faultstring', 'Error de autenticación')
                    return [], f"Error de autenticación: {fault_msg}"
                else:
                    return [], f"No se encontraron eventos para {artist_name}"
            
            if 'events' not in data['_embedded']:
                return [], f"No hay eventos disponibles para {artist_name}"
            
            events = data['_embedded']['events']
            concerts = []
            
            for event in events:
                try:
                    # Extraer datos del venue con manejo de errores mejorado
                    venues = event.get('_embedded', {}).get('venues', [])
                    venue_data = venues[0] if venues else {}
                    
                    # Construir dirección desde los datos del venue
                    address_parts = []
                    address_obj = venue_data.get('address', {})
                    if address_obj.get('line1'):
                        address_parts.append(address_obj['line1'])
                    if address_obj.get('line2'):
                        address_parts.append(address_obj['line2'])
                    if venue_data.get('postalCode'):
                        address_parts.append(venue_data['postalCode'])
                    
                    address = ', '.join(address_parts)
                    
                    # Extraer fecha y hora con mejor manejo
                    dates = event.get('dates', {})
                    start_date = dates.get('start', {})
                    local_date = start_date.get('localDate', 'Unknown date')
                    local_time = start_date.get('localTime', '')
                    
                    # Extraer imagen con mejor lógica
                    images = event.get('images', [])
                    image_url = ''
                    if images:
                        # Buscar imagen 16:9 con buena resolución
                        for img in images:
                            if (img.get('ratio') == '16_9' and 
                                img.get('width', 0) > 500 and 
                                img.get('width', 0) < 1200):
                                image_url = img.get('url', '')
                                break
                        
                        # Si no se encontró imagen ideal, usar la primera disponible
                        if not image_url and images:
                            image_url = images[0].get('url', '')
                    
                    # Extraer ciudad con manejo mejorado
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
                    concerts.append(concert)
                    
                except Exception as e:
                    print(f"Error procesando evento: {e}")
                    continue
            
            # Guardar en caché solo si hay resultados
            if concerts:
                self._save_to_cache(cache_file, concerts)
            
            return concerts, f"Se encontraron {len(concerts)} conciertos para {artist_name}"
            
        except requests.exceptions.Timeout:
            return [], f"Timeout al conectar con Ticketmaster para {artist_name}"
        except requests.exceptions.RequestException as e:
            return [], f"Error en la solicitud: {str(e)}"
        except ValueError as e:
            return [], f"Error procesando respuesta JSON: {str(e)}"
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error inesperado: {error_trace}")
            return [], f"Error inesperado: {str(e)}"
    
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