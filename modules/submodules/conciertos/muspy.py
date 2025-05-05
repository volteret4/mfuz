import os
import json
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path


class MuspyService:
    """Service for interacting with the MuSpy API with cache support"""
    
    def __init__(self, username, password, user_id, cache_dir, cache_duration=24):
        self.username = username
        self.password = password
        self.user_id = user_id
        self.base_url = "https://muspy.com/api/1"
        self.cache_dir = Path(cache_dir)
        self.cache_duration = cache_duration  # hours
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_followed_artists(self, return_full_data=False):
        """
        Obtener artistas seguidos por el usuario desde la API de MuSpy
        
        Args:
            return_full_data (bool): Si es True, devuelve los datos completos, no solo los nombres
            
        Returns:
            tuple: (lista de nombres de artistas o datos completos, mensaje)
        """
        if not self.username or not self.password or not self.user_id:
            return [], "Credenciales de MuSpy no configuradas"
        
        # Comprobar si tenemos resultado en caché válido
        cache_file = self.cache_dir / "artists_muspy.json"
        cached_data = self._load_from_cache(cache_file)
        
        if cached_data:
            if return_full_data:
                return cached_data, f"Se encontraron {len(cached_data)} artistas seguidos en MuSpy (caché)"
            else:
                artist_names = [artist.get('name') for artist in cached_data 
                            if isinstance(artist, dict) and 'name' in artist]
                return artist_names, f"Se encontraron {len(artist_names)} artistas seguidos en MuSpy (caché)"
        
        # Si no hay caché válido, consultar API
        try:
            url = f"{self.base_url}/artists/{self.user_id}"
            response = requests.get(url, auth=(self.username, self.password))
            response.raise_for_status()
            artists_data = response.json()
            
            # Guardar respuesta completa en caché
            self._save_to_cache(cache_file, artists_data)
            
            if return_full_data:
                return artists_data, f"Se encontraron {len(artists_data)} artistas seguidos en MuSpy"
            else:
                # Extraer nombres de artistas
                artist_names = [artist.get('name') for artist in artists_data 
                            if isinstance(artist, dict) and 'name' in artist]
                
                return artist_names, f"Se encontraron {len(artist_names)} artistas seguidos en MuSpy"
                
        except requests.exceptions.RequestException as e:
            return [], f"Error en la solicitud API: {str(e)}"
        except ValueError as e:
            return [], f"Error procesando respuesta: {str(e)}"
    
    def _load_from_cache(self, cache_file):
        """Load data from cache if it exists and is valid"""
        if not cache_file.exists():
            return None
        
        try:
            # Check if the file is recent
            file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            cache_age = datetime.now() - file_time
            
            if cache_age > timedelta(hours=self.cache_duration):
                # Cache expired
                return None
            
            # Load data
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Check cache timestamp
                if 'timestamp' in data:
                    cache_time = datetime.fromisoformat(data['timestamp'])
                    if (datetime.now() - cache_time) > timedelta(hours=self.cache_duration):
                        return None
                    
                    # Return only the artists (not the timestamp)
                    return data.get('artists', [])
                else:
                    # Old format without timestamp
                    return data
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error reading cache: {e}")
            return None
    
    def _save_to_cache(self, cache_file, artists):
        """Save results to cache"""
        try:
            # Save with timestamp
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'artists': artists
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def clear_cache(self):
        """Clear cache"""
        cache_file = self.cache_dir / "artists_muspy.json"
        if cache_file.exists():
            cache_file.unlink()