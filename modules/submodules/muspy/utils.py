import subprocess
import os
import platform
import logging


class MuspyUtils:
    def __init__(self, parent, spotify_manager=None, muspy_manager=None):
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        self.spotify_manager = spotify_manager
        self.muspy_manager = muspy_manager



    def open_spotify_album(self, album_id):
        """Open Spotify album page in browser"""
        if not album_id:
            return
            
        url = f"https://open.spotify.com/album/{album_id}"
        
        import webbrowser
        webbrowser.open(url)

    def open_spotify_artist(self, artist_id):
        """Open Spotify artist page in browser without blocking"""
        if not artist_id:
            return
            
        url = f"https://open.spotify.com/artist/{artist_id}"
        
        # Usar subprocess para abrir el navegador sin bloquear (aplicación no espera)
        try:

            
            # Abrir de manera diferente según el sistema operativo
            system = platform.system()
            
            if system == 'Darwin':  # macOS
                subprocess.Popen(['open', url], start_new_session=True)
            elif system == 'Windows':
                os.startfile(url)
            else:  # Linux y otros
                subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                                start_new_session=True)
        except Exception as e:
            self.logger.error(f"Error opening URL: {e}")
            # Fallback a webbrowser como último recurso
            import webbrowser
            webbrowser.open_new_tab(url)

    def open_spotify_uri(self, uri):
            """Open Spotify URI directly in the Spotify app without blocking"""
            if not uri:
                return
            
            try:
                import subprocess
                import os
                import platform
                
                system = platform.system()
                
                if system == 'Darwin':  # macOS
                    subprocess.Popen(['open', uri], start_new_session=True)
                elif system == 'Windows':
                    os.startfile(uri)
                else:  # Linux y otros
                    subprocess.Popen(['xdg-open', uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                                    start_new_session=True)
            except Exception as e:
                self.logger.error(f"Error opening URI: {e}")
                # Para URIs, también podemos intentar abrir la versión web
                import webbrowser
                # Convertir URI a URL web si es posible
                if uri.startswith('spotify:track:'):
                    track_id = uri.split(':')[2]
                    webbrowser.open_new_tab(f"https://open.spotify.com/track/{track_id}")
                elif uri.startswith('spotify:artist:'):
                    artist_id = uri.split(':')[2]
                    webbrowser.open_new_tab(f"https://open.spotify.com/artist/{artist_id}")
                elif uri.startswith('spotify:album:'):
                    album_id = uri.split(':')[2]
                    webbrowser.open_new_tab(f"https://open.spotify.com/album/{album_id}")


    def open_spotify_track(self, track_id):
            """Open Spotify track page in browser without blocking"""
            if not track_id:
                return
                
            url = f"https://open.spotify.com/track/{track_id}"
            
            # Usar el mismo método que en tools.open_spotify_artist
            try:
                import subprocess
                import os
                import platform
                
                system = platform.system()
                
                if system == 'Darwin':  # macOS
                    subprocess.Popen(['open', url], start_new_session=True)
                elif system == 'Windows':
                    os.startfile(url)
                else:  # Linux y otros
                    subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                                    start_new_session=True)
            except Exception as e:
                self.logger.error(f"Error opening URL: {e}")
                import webbrowser
                webbrowser.open_new_tab(url)


# LASTFM 

    def open_lastfm_artist(self, artist_name):
        """Open Last.fm artist page in browser"""
        if not artist_name:
            return
            
        # URL encode the artist name for the URL
        import urllib.parse
        encoded_name = urllib.parse.quote(artist_name)
        
        url = f"https://www.last.fm/music/{encoded_name}"
        
        import webbrowser
        webbrowser.open(url)
        

# Bluesky
    def open_url(self, url):
        """
        Open a URL in the default browser
        
        Args:
            url (str): URL to open
        """
        import webbrowser
        webbrowser.open(url)