"""
Módulo de integración con Last.fm para la base de datos de música
Este módulo permite importar escuchas (scrobbles) desde Last.fm y enriquecer
la base de datos con metadatos adicionales.
"""

# Exportar las funciones principales que necesitará usar db_creator.py
from .api import get_lastfm_scrobbles, get_artist_info, get_track_info, get_album_info
from .db_handler import (
    setup_database, 
    lookup_artist_in_database, 
    lookup_album_in_database, 
    lookup_song_in_database,
    get_last_timestamp,
    save_last_timestamp
)
from .cache import setup_cache_system
from .indexing import create_optimized_indices, analyze_database_performance
from .utils import handle_force_update

# Variables globales que se configurarán desde db_creator.py
INTERACTIVE_MODE = False
FORCE_UPDATE = False

# Inicialización del sistema de caché
cache_system = None

def setup(cache_dir=None):
    """
    Configura el módulo con un directorio de caché opcional
    
    Args:
        cache_dir: Directorio para guardar archivos de caché
    """
    global cache_system
    
    # Configurar el sistema de caché
    cache_system = setup_cache_system(cache_dir)
    
    # Configurar el cliente de MusicBrainz
    import musicbrainzngs
    musicbrainzngs.set_useragent(
        "TuAppMusical", 
        "1.0", 
        "tu_email@example.com"
    )
    
    print(f"Módulo LastFM inicializado. Caché: {'Persistente' if cache_dir else 'En memoria'}")

# Función principal que será llamada por db_creator.py
def main(config):
    """
    Función principal para la integración con Last.fm
    
    Args:
        config: Diccionario con la configuración
        
    Returns:
        Tupla con estadísticas sobre scrobbles procesados
    """
    global INTERACTIVE_MODE, FORCE_UPDATE, cache_system
    
    # Configurar variables globales desde config
    INTERACTIVE_MODE = config.get('interactive', False)
    FORCE_UPDATE = config.get('force_update', False)
    
    # Extraer parámetros requeridos
    db_path = config.get('db_path')
    if not db_path:
        print("Error: db_path es requerido en la configuración")
        return 0, 0, 0, 0

    lastfm_user = config.get('lastfm_user')
    if not lastfm_user:
        print("Error: lastfm_user es requerido en la configuración")
        return 0, 0, 0, 0

    lastfm_api_key = config.get('lastfm_api_key')
    if not lastfm_api_key:
        print("Error: lastfm_api_key es requerido en la configuración")
        return 0, 0, 0, 0
    
    # Configurar caché si no está ya configurado
    cache_dir = config.get('cache_dir')
    if cache_system is None:
        setup(cache_dir)
    
    # El resto de la lógica se implementa en el script principal lastfm_escuchas.py
    # que será importado y ejecutado por db_creator.py
    
    # Esta función simplemente devuelve lo que habría devuelto una implementación completa
    # pero la verdadera implementación está en el script lastfm_escuchas.py
    return 0, 0, 0, 0