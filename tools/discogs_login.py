import requests
import time
import logging
from urllib.parse import urljoin

class DiscogsClient:
    """
    Cliente para interactuar con la API de Discogs.
    
    Atributos:
        token (str): Token de autenticación para la API de Discogs.
        rate_limit (float): Tiempo mínimo entre peticiones a la API (en segundos).
        base_url (str): URL base para la API de Discogs.
        user_agent (str): User-Agent para las peticiones HTTP.
        last_request_time (float): Timestamp de la última petición realizada.
        logger (logging.Logger): Logger para registrar actividad.
    """
    
    def __init__(self, token, rate_limit=1.0, user_agent=None):
        """
        Inicializa el cliente de Discogs.
        
        Args:
            token (str): Token de autenticación para la API de Discogs.
            rate_limit (float, optional): Tiempo mínimo entre peticiones (en segundos). Por defecto 1.0.
            user_agent (str, optional): User-Agent para las peticiones HTTP.
        """
        self.token = token
        self.rate_limit = rate_limit
        self.base_url = "https://api.discogs.com/"
        self.user_agent = user_agent or "MusicDatabaseApp/1.0"
        self.last_request_time = 0
        self.logger = logging.getLogger("discogs_client")
        
    def _throttle(self):
        """
        Garantiza que se respete el límite de tasa entre peticiones.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
        
    def _make_request(self, endpoint, params=None):
        """
        Realiza una petición a la API de Discogs.
        
        Args:
            endpoint (str): Endpoint de la API a consultar.
            params (dict, optional): Parámetros adicionales para la petición.
            
        Returns:
            dict: La respuesta JSON de la API.
            
        Raises:
            Exception: Si la petición falla.
        """
        url = urljoin(self.base_url, endpoint)
        headers = {
            "Authorization": f"Discogs token={self.token}",
            "User-Agent": self.user_agent
        }
        
        self._throttle()
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error en la petición a Discogs: {str(e)}")
            raise
    
    def search_artist(self, artist_name):
        """
        Busca un artista en Discogs.
        
        Args:
            artist_name (str): Nombre del artista a buscar.
            
        Returns:
            dict: La primera coincidencia del artista, o None si no se encontró.
        """
        params = {
            "q": artist_name,
            "type": "artist",
            "per_page": 1
        }
        
        try:
            results = self._make_request("database/search", params)
            if results.get("results") and len(results["results"]) > 0:
                return results["results"][0]
            return None
        except Exception as e:
            self.logger.error(f"Error al buscar artista '{artist_name}': {str(e)}")
            return None
    
    def get_artist_details(self, artist_id):
        """
        Obtiene detalles de un artista específico por su ID.
        
        Args:
            artist_id (int): ID del artista en Discogs.
            
        Returns:
            dict: Detalles del artista.
        """
        try:
            return self._make_request(f"artists/{artist_id}")
        except Exception as e:
            self.logger.error(f"Error al obtener detalles del artista ID {artist_id}: {str(e)}")
            return None
    
    def get_artist_discography(self, artist_id, per_page=100):
        """
        Obtiene la discografía de un artista.
        
        Args:
            artist_id (int): ID del artista en Discogs.
            per_page (int, optional): Número de resultados por página. Por defecto 100.
            
        Returns:
            list: Lista de lanzamientos del artista.
        """
        try:
            return self._make_request(f"artists/{artist_id}/releases", {"per_page": per_page})
        except Exception as e:
            self.logger.error(f"Error al obtener discografía del artista ID {artist_id}: {str(e)}")
            return None