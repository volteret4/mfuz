#!/usr/bin/env python3
import sqlite3
import os
import sys
import time
import traceback
from pathlib import Path

# Intenta importar desde el directorio padre
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from base_module import PROJECT_ROOT
except ImportError:
    print("No se pudo importar PROJECT_ROOT desde base_module")
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuración
DB_PATH = os.path.join(PROJECT_ROOT, "db", "sqlite", "musica.sqlite")

# Tus credenciales de Spotify
SPOTIFY_CLIENT_ID =   None
SPOTIFY_CLIENT_SECRET = None

def log(message):
    """Registra un mensaje en stdout con marca de tiempo."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def set_spotify_credentials(client_id, client_secret):
    """
    Configura las credenciales de Spotify desde el archivo de configuración.
    
    Args:
        client_id: ID del cliente de Spotify API
        client_secret: Secreto del cliente de Spotify API
    """
    global SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
    SPOTIFY_CLIENT_ID = client_id
    SPOTIFY_CLIENT_SECRET = client_secret
    log(f"Credenciales de Spotify configuradas")


def get_track_id_from_url(spotify_url):
    """
    Extrae el ID de pista de Spotify de una URL.
    
    Args:
        spotify_url: URL de Spotify
        
    Returns:
        ID de pista extraído de la URL
    """
    if not spotify_url:
        return None
        
    
    try:
        parts = spotify_url.split('/')
        if len(parts) > 4 and parts[3] == 'track':
            track_id = parts[4].split('?')[0]  # Remover parámetros de consulta si existen
            return track_id
    except Exception as e:
        log(f"Error al extraer ID de pista: {e}")
    
    return None

def add_preview_url_column():
    """Añade la columna preview_url a la tabla song_links si no existe."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(song_links)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "preview_url" not in columns:
            log("Añadiendo columna preview_url a la tabla song_links...")
            cursor.execute("ALTER TABLE song_links ADD COLUMN preview_url TEXT")
            conn.commit()
            log("Columna añadida exitosamente")
        else:
            log("La columna preview_url ya existe en la tabla song_links")
            
        conn.close()
        return True
        
    except Exception as e:
        log(f"Error al añadir columna preview_url: {e}")
        return False

def update_preview_urls():
    """
    Actualiza las URLs de previsualización para todas las canciones que tienen
    spotify_id o spotify_url pero no tienen preview_url.
    """
    try:
        # Validar que las credenciales estén configuradas
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
            log("Error: Las credenciales de Spotify no están configuradas")
            log("Asegúrese de incluir spotify_client_id y spotify_client_secret en el archivo de configuración")
            return False
        
        # Verificar si spotipy está instalado
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials
        except ImportError:
            log("Error: No se pudo importar la biblioteca spotipy. Instálela con 'pip install spotipy'")
            return False
            
        # Primero asegurarse de que la columna preview_url existe
        add_preview_url_column()
        
        # Conectar a la base de datos
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Configurar cliente de Spotify con credenciales del config
        auth_manager = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
        
        # Verificar la autenticación con una llamada simple
        try:
            sp = spotipy.Spotify(
                client_credentials_manager=auth_manager,
                requests_timeout=10
            )
            sp.search(q="test", limit=1)
            log("Autenticación con Spotify exitosa")
        except Exception as e:
            log(f"Error de autenticación con Spotify: {e}")
            log("Verifique sus credenciales de API en el archivo de configuración")
            return False
        

        cursor.execute("""
            SELECT song_id, spotify_id, spotify_url 
            FROM song_links 
            WHERE (spotify_id IS NOT NULL OR spotify_url IS NOT NULL) 
            AND (preview_url IS NULL OR preview_url = '')
        """)
        
        songs = cursor.fetchall()
        log(f"Encontradas {len(songs)} canciones para actualizar URLs de previsualización")
        
        updated = 0
        failed = 0
        
        for i, song in enumerate(songs):
            try:
                # Mostrar progreso
                if (i + 1) % 10 == 0 or i == 0 or i == len(songs) - 1:
                    log(f"Procesando canción {i+1}/{len(songs)}...")
                
                # Obtener track_id
                track_id = None
                if song['spotify_id']:
                    track_id = song['spotify_id']
                elif song['spotify_url']:
                    track_id = get_track_id_from_url(song['spotify_url'])
                
                if not track_id:
                    log(f"No se pudo obtener track_id para canción ID: {song['song_id']}")
                    failed += 1
                    continue
                
                # Consultar API de Spotify
                try:
                    log(f"Consultando API para track_id: {track_id}")
                    track_info = sp.track(track_id)
                    preview_url = track_info.get('preview_url')
                    
                    if preview_url:
                        log(f"URL de previsualización encontrada: {preview_url}")
                        # Actualizar base de datos
                        cursor.execute("""
                            UPDATE song_links SET preview_url = ? WHERE song_id = ?
                        """, (preview_url, song['song_id']))
                        conn.commit()
                        updated += 1
                    else:
                        log(f"No hay URL de previsualización disponible para track_id: {track_id}")
                        failed += 1
                        
                except Exception as e:
                    log(f"Error al consultar API para track_id {track_id}: {e}")
                    failed += 1
                
                # Prevenir límites de tasa de la API
                time.sleep(0.5)
                
            except Exception as e:
                log(f"Error al procesar canción ID {song['song_id']}: {e}")
                log(traceback.format_exc())
                failed += 1
        
        # Cerrar conexión
        conn.close()
        
        log(f"Actualización completada: {updated} URLs actualizadas, {failed} fallos")
        return True
        
    except Exception as e:
        log(f"Error al actualizar URLs de previsualización: {e}")
        log(traceback.format_exc())
        return False

def test_playback():
    """
    Prueba la reproducción de algunas URLs de previsualización para verificar que funcionan.
    """
    try:
        import subprocess
        
        # Conectar a la base de datos
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Obtener algunas URLs de previsualización
        cursor.execute("""
            SELECT preview_url 
            FROM song_links 
            WHERE preview_url IS NOT NULL AND preview_url != '' 
            LIMIT 3
        """)
        
        urls = [row['preview_url'] for row in cursor.fetchall()]
        conn.close()
        
        if not urls:
            log("No se encontraron URLs de previsualización para probar")
            return False
            
        for url in urls:
            log(f"Probando reproducción de: {url}")
            
            # Detectar reproductor disponible
            players = ['mpg123', 'mplayer', 'ffplay', 'cvlc']
            player_cmd = None
            
            for player in players:
                try:
                    subprocess.run(['which', player], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if player == 'mpg123':
                        player_cmd = ['mpg123', '-q', url]
                    elif player == 'mplayer':
                        player_cmd = ['mplayer', '-really-quiet', url]
                    elif player == 'ffplay':
                        player_cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', url]
                    elif player == 'cvlc':
                        player_cmd = ['cvlc', '--play-and-exit', '--quiet', url]
                    break
                except subprocess.CalledProcessError:
                    continue
            
            if not player_cmd:
                log("No se encontró ningún reproductor de audio compatible")
                return False
                
            log(f"Reproduciendo con: {' '.join(player_cmd)}")
            
            try:
                # Reproducir durante 5 segundos y luego detener
                process = subprocess.Popen(player_cmd)
                time.sleep(5)
                process.terminate()
                log("Reproducción exitosa")
            except Exception as e:
                log(f"Error al reproducir: {e}")
                
            # Esperar antes de la siguiente prueba
            time.sleep(1)
            
        return True
        
    except Exception as e:
        log(f"Error en la prueba de reproducción: {e}")
        return False

def main(config=None):
    """
    Función principal que puede recibir configuración desde db_creator.
    
    Args:
        config: Diccionario con configuración incluyendo credenciales de Spotify
    """
    # Verificar que la base de datos existe
    if not os.path.exists(DB_PATH):
        log(f"Error: La base de datos no existe en {DB_PATH}")
        return False
        
    # Configurar credenciales si se proporcionan en el config
    if config:
        client_id = config.get('spotify_client_id')
        client_secret = config.get('spotify_client_secret')
        
        if client_id and client_secret:
            set_spotify_credentials(client_id, client_secret)
        else:
            log("Advertencia: No se encontraron credenciales de Spotify en la configuración")
            log("Se requieren 'spotify_client_id' y 'spotify_client_secret'")
            return False
    
    # Actualizar las URLs de previsualización
    success = update_preview_urls()
    
    # Opcional: Probar la reproducción si está habilitado en config
    if config and config.get('test_playback', False):
        test_playback()
    
    return success

if __name__ == "__main__":
    # Cuando se ejecuta directamente, usar credenciales por defecto o del entorno
    import os
    
    default_client_id = os.getenv('SPOTIFY_CLIENT_ID', "")
    default_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET', "")
    
    config = {
        'spotify_client_id': default_client_id,
        'spotify_client_secret': default_client_secret,
        'test_playback': False
    }
    
    main(config)