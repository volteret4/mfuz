import os
import spotipy

class SpotifyAuth:
    def __init__(self, client_id, client_secret, redirect_uri, cache_path=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.cache_path = cache_path or os.path.join(PROJECT_ROOT, ".content", "cache", "spotify_auth.json")
        self.sp = None
        self.sp_oauth = None
        self.authenticated = False

    def setup(self):
        """Configura y autentica con Spotify"""

                
        try:
            # Si ya tienes los valores de tus credenciales, úsalos
            if not client_id:
                client_id = os.environ.get('SPOTIFY_CLIENT_ID') or self.spotify_client_id
            
            if not client_secret:
                client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET') or self.spotify_client_secret
                
            if not client_id or not client_secret:
                self.log("Spotify client ID and secret are required for Spotify functionality")
                return False

            if not redirect_uri:
                redirect_uri = os.environ.get('SPOTIFY_REDIRECT_URI') or self.spotify_redirect_uri

            if hasattr(self, 'playlist_spotify_comboBox'):
                self.playlist_spotify_comboBox.blockSignals(True)



            print("Setting up Spotify client...")
            
            # Ensure cache directory exists - usa la ruta que prefieras
            if not cache_path:
                cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "music_app", "spotify")
                os.makedirs(cache_dir, exist_ok=True)
                cache_path = os.path.join(cache_dir, "spotify_token.txt")
                
            print(f"Using token cache path: {cache_path}")
            
            # Define scope for Spotify permissions
            scope = "playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative"
            
            # Create a new OAuth instance
            try:
                self.sp_oauth = SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri,
                    scope=scope,
                    open_browser=False,
                    cache_path=cache_path
                )
                
                # Intenta obtener el token usando tu método existente primero
                token_info = None
                if hasattr(self, '_load_api_credentials_from_env'):
                    self._load_api_credentials_from_env()  # Tu método existente
                    
                    # Si después de cargar las credenciales tenemos un token, úsalo
                    if hasattr(self, 'spotify_token') and self.spotify_token:
                        token_info = {'access_token': self.spotify_token}
                
                # Si no tenemos token, usar el nuevo método
                if not token_info:
                    token_info = get_token_or_authenticate(self)
                
                # Create Spotify client with the token
                print("Creating Spotify client with token")
                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                
                print("Getting current user info")
                user_info = self.sp.current_user()
                self.spotify_user_id = user_info['id']
                print(f"Authenticated as user: {self.spotify_user_id}")

                # Resultado exitoso, ahora activamos las señales
                if hasattr(self, 'playlist_spotify_comboBox'):
                    self.playlist_spotify_comboBox.blockSignals(False)
                
                # Flag that Spotify is authenticated
                self.spotify_authenticated = True
                return True
                
            except Exception as e:
                print(f"Spotify setup error: {str(e)}")
                import traceback
                traceback.print_exc()
                self.log(f"Error de autenticación con Spotify: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Error setting up Spotify: {str(e)}")
            return False
            


    def get_client(self):
        """Retorna el cliente Spotify autenticado"""
        return self.sp