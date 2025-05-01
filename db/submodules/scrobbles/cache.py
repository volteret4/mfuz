import json
import os
import time
import hashlib

class APICache:
    """
    Unified cache system for API responses.
    Can be used with multiple API services like Last.fm, MusicBrainz, etc.
    """
    
    def __init__(self, service_name, cache_file=None, cache_duration=7):
        """
        Initialize the cache
        
        Args:
            service_name: Name of the service (lastfm, musicbrainz, etc.)
            cache_file: Optional path to persist the cache
            cache_duration: Cache duration in days
        """
        self.service_name = service_name
        self.cache = {}
        self.cache_file = cache_file
        self.cache_duration = cache_duration  # in days
        
        if cache_file and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    loaded_cache = json.load(f)
                    
                    # Filter expired entries
                    now = time.time()
                    for key, entry in loaded_cache.items():
                        if 'timestamp' in entry:
                            age_days = (now - entry['timestamp']) / (60 * 60 * 24)
                            if age_days <= self.cache_duration:
                                self.cache[key] = entry
                        else:
                            # If no timestamp, assume it's recent
                            self.cache[key] = entry
                            
                print(f"{service_name} cache: Loaded {len(self.cache)} valid entries out of {len(loaded_cache)} total")
            except Exception as e:
                print(f"Error loading {service_name} cache file: {e}")
                # Start with empty cache if there's an error
                self.cache = {}
    
    def get(self, key_params):
        """
        Get a cached result if available and not expired
        
        Args:
            key_params: Parameters to create the cache key
            
        Returns:
            Cached data or None if not found or expired
        """
        cache_key = self._make_key(key_params)
        entry = self.cache.get(cache_key)
        
        if not entry:
            return None
            
        # Check expiration
        if 'timestamp' in entry:
            age_days = (time.time() - entry['timestamp']) / (60 * 60 * 24)
            if age_days > self.cache_duration:
                # Expired, remove and return None
                del self.cache[cache_key]
                return None
        
        return entry.get('data')
    
    def put(self, key_params, result):
        """
        Store a result in the cache
        
        Args:
            key_params: Parameters to create the cache key
            result: Result to store
        """
        cache_key = self._make_key(key_params)
        
        # Don't cache error responses
        if isinstance(result, dict) and 'error' in result:
            return
        
        # Store with timestamp for expiration
        self.cache[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }
        
        # Save to file if configured
        self._save_cache()
    
    def clear(self, save=True):
        """Clear the entire cache"""
        self.cache = {}
        if save and self.cache_file:
            self._save_cache()
    
    def _save_cache(self):
        """Save cache to disk if file is configured"""
        if not self.cache_file:
            return
            
        try:
            # Create directory if it doesn't exist
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
                
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving {self.service_name} cache file: {e}")
    
    def _make_key(self, params):
        """
        Create a unique cache key from parameters
        
        Args:
            params: Dictionary or other parameters
            
        Returns:
            String uniquely identifying the query
        """
        # Convert params to stable representation
        if isinstance(params, dict):
            # Special handling for Last.fm - exclude API key from cache key
            if self.service_name.lower() == 'lastfm' and 'api_key' in params:
                params = {k: v for k, v in params.items() if k != 'api_key'}
            
            # Sort keys for consistency
            param_str = json.dumps(params, sort_keys=True)
        else:
            param_str = str(params)
        
        # Use hash for very long keys
        if len(param_str) > 200:
            param_hash = hashlib.md5(param_str.encode('utf-8')).hexdigest()
            return f"{self.service_name}:{param_hash}"
        else:
            return f"{self.service_name}:{param_str}"


class LastFMCache(APICache):
    """Last.fm specific cache implementation"""
    
    def __init__(self, cache_file=None, cache_duration=7):
        super().__init__('lastfm', cache_file, cache_duration)
    
    def get(self, method, params):
        """
        Get cached Last.fm response
        
        Args:
            method: API method (artist.getInfo, etc.)
            params: API parameters
            
        Returns:
            Cached response or None
        """
        # Create combined parameters with method
        key_params = {'method': method}
        key_params.update(params)
        return super().get(key_params)
    
    def put(self, method, params, result):
        """
        Store Last.fm response in cache
        
        Args:
            method: API method
            params: API parameters
            result: API response
        """
        # Create combined parameters with method
        key_params = {'method': method}
        key_params.update(params)
        super().put(key_params, result)


class MusicBrainzCache(APICache):
    """MusicBrainz specific cache implementation"""
    
    def __init__(self, cache_file=None, cache_duration=30):
        super().__init__('musicbrainz', cache_file, cache_duration)
    
    def get(self, query_type, query_id=None, query_params=None):
        """
        Get cached MusicBrainz response
        
        Args:
            query_type: Type of query (artist, release, recording, etc.)
            query_id: ID for direct lookups
            query_params: Parameters for searches
            
        Returns:
            Cached response or None
        """
        key_params = {
            'type': query_type,
            'id': query_id,
            'params': query_params
        }
        return super().get(key_params)
    
    def put(self, query_type, result, query_id=None, query_params=None):
        """
        Store MusicBrainz response in cache
        
        Args:
            query_type: Type of query
            result: Result to store
            query_id: ID for direct lookups
            query_params: Parameters for searches
        """
        key_params = {
            'type': query_type,
            'id': query_id,
            'params': query_params
        }
        super().put(key_params, result)


def setup_cache_system(cache_dir=None):
    """
    Set up the caching system with appropriate cache files
    
    Args:
        cache_dir: Directory to store cache files
        
    Returns:
        Dictionary with cache instances
    """
    cache_system = {
        'lastfm': None,
        'musicbrainz': None
    }
    
    if cache_dir:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            
            lastfm_cache_file = os.path.join(cache_dir, "lastfm_cache.json")
            mb_cache_file = os.path.join(cache_dir, "musicbrainz_cache.json")
            
            cache_system['lastfm'] = LastFMCache(lastfm_cache_file)
            cache_system['musicbrainz'] = MusicBrainzCache(mb_cache_file)
            
            print(f"Cache system configured in: {cache_dir}")
        except Exception as e:
            print(f"Error setting up persistent cache: {e}")
            print("Using in-memory cache")
            
            # Fall back to in-memory cache
            cache_system['lastfm'] = LastFMCache()
            cache_system['musicbrainz'] = MusicBrainzCache()
    else:
        # Use in-memory cache
        cache_system['lastfm'] = LastFMCache()
        cache_system['musicbrainz'] = MusicBrainzCache()
        print("Cache system configured in memory (non-persistent)")
    
    return cache_system