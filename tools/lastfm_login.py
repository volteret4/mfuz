import os
import json
import logging
from pathlib import Path

# Import LastFM-related modules
try:
    import pylast
    PYLAST_AVAILABLE = True
except ImportError:
    PYLAST_AVAILABLE = False
    logging.warning("pylast not installed. LastFM functionality will be limited.")

# Import QT components for dialog if needed
try:
    from PyQt6.QtWidgets import QInputDialog, QMessageBox
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    logging.warning("PyQt6 not available. Will use console for authentication.")


class LastFMAuthManager:
    """
    A class to handle LastFM authentication across different modules.
    Manages API key, user authentication, and provides a configured LastFM network.
    """
    
    def __init__(self, api_key=None, api_secret=None, username=None, password=None, 
                 session_key_path=None, project_root=None, parent_widget=None):
        """
        Initialize the LastFM Authentication Manager.
        
        Args:
            api_key (str): LastFM API key
            api_secret (str, optional): LastFM API secret for authenticated actions
            username (str, optional): LastFM username
            password (str, optional): LastFM password (used only for authentication)
            session_key_path (str, optional): Path to store the session key
            project_root (str, optional): Root path of the application
            parent_widget (QWidget, optional): Parent widget for dialogs
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.username = username
        self.password = password
        self.parent_widget = parent_widget
        self.logger = logging.getLogger("LastFMAuthManager")
        
        # Try to determine PROJECT_ROOT if not provided
        if project_root:
            self.PROJECT_ROOT = Path(project_root)
        else:
            # Try to get it from the global variable if available
            try:
                import sys
                sys.path.append(os.path.dirname(os.path.dirname(__file__)))
                from base_module import PROJECT_ROOT
                self.PROJECT_ROOT = PROJECT_ROOT
            except ImportError:
                # Fallback to current directory
                self.PROJECT_ROOT = Path.cwd()
        
        # Set up session key path
        if session_key_path:
            self.session_key_path = session_key_path
        else:
            cache_dir = self.PROJECT_ROOT / ".content" / "cache"
            os.makedirs(cache_dir, exist_ok=True)
            self.session_key_path = str(cache_dir / ".lastfm_session.json")
        
        # Initialize variables
        self.network = None
        self.session_key = None
        
        # Check if pylast is available
        if not PYLAST_AVAILABLE:
            self.logger.error("pylast library not available. Please install with 'pip install pylast'")
            return
            
        # Setup network and try to load existing session
        self._setup_network()
        self._load_session_key()
    
    def _setup_network(self):
        """Set up the LastFM network object with appropriate configurations."""
        if not PYLAST_AVAILABLE:
            return
            
        if not self.api_key:
            self.logger.warning("LastFM api_key not provided")
            return
            
        try:
            # Create network with minimal parameters
            network_params = {
                "api_key": self.api_key,
            }
            
            # Add optional parameters if available
            if self.api_secret:
                network_params["api_secret"] = self.api_secret
            if self.username:
                network_params["username"] = self.username
            if self.password and self.api_secret:
                # Password hash is only used when we need to authenticate
                import hashlib
                password_hash = pylast.md5(self.password)
                network_params["password_hash"] = password_hash
            
            self.network = pylast.LastFMNetwork(**network_params)
            self.logger.info("LastFM network initialized successfully")
            
            # If we have a stored session key, set it
            if self.session_key:
                self.network.session_key = self.session_key
                
            return True
        except Exception as e:
            self.logger.error(f"Error setting up LastFM network: {e}")
            self.network = None
            return False
    
    def _load_session_key(self):
        """Load the cached session key if available."""
        if not os.path.exists(self.session_key_path):
            return False
            
        try:
            with open(self.session_key_path, 'r') as f:
                data = json.load(f)
                if 'session_key' in data and data['session_key']:
                    self.session_key = data['session_key']
                    # Update network with session key
                    if self.network:
                        self.network.session_key = self.session_key
                    self.logger.info("Loaded cached LastFM session key")
                    return True
                else:
                    self.logger.info("No valid session key found in cache")
                    return False
        except Exception as e:
            self.logger.error(f"Error loading cached session key: {e}")
            return False
    
    def _save_session_key(self):
        """Save the session key to the cache file."""
        if not self.session_key:
            return False
            
        try:
            with open(self.session_key_path, 'w') as f:
                json.dump({'session_key': self.session_key}, f)
            self.logger.info(f"Saved session key to {self.session_key_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving session key: {e}")
            return False
    
    def authenticate(self, force_new_auth=False):
        """
        Authenticate with LastFM using the API key and secret.
        
        Args:
            force_new_auth (bool): Force a new authentication flow even if a session exists.
                
        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        if not PYLAST_AVAILABLE or not self.network:
            return False
        
        # If we already have a session key and are not forcing new auth, just return
        if self.session_key and not force_new_auth:
            return self._verify_session()
            
        # We need api_secret for authentication
        if not self.api_secret:
            self.logger.error("api_secret is required for authentication")
            return False
            
        # Authentication requires username and password
        if not self.username or not self.password:
            self.logger.error("Username and password are required for authentication")
            return False
        
        try:
            # Create a password hash
            import hashlib
            password_hash = pylast.md5(self.password)
            
            # Try to authenticate and get a session key
            skg = pylast.SessionKeyGenerator(self.network)
            self.session_key = skg.get_session_key(self.username, password_hash)
            
            if self.session_key:
                # Set the session key on the network
                self.network.session_key = self.session_key
                # Save the session key
                self._save_session_key()
                self.logger.info("LastFM authentication successful")
                return True
            else:
                self.logger.error("Failed to get LastFM session key")
                return False
                
        except pylast.WSError as e:
            # Handle specific LastFM web service errors
            error_msg = f"LastFM authentication error: {e}"
            self.logger.error(error_msg)
            
            if QT_AVAILABLE and self.parent_widget:
                QMessageBox.warning(
                    self.parent_widget,
                    "LastFM Authentication Error",
                    error_msg
                )
            return False
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def _verify_session(self):
        """Verify that the current session key is valid."""
        if not self.network or not self.session_key:
            return False
            
        try:
            # Try to get current user info as a simple test
            user = self.network.get_user(self.username)
            # Trigger an API call to verify the session
            playcount = user.get_playcount()
            self.logger.info(f"Verified LastFM session for user {self.username}")
            return True
        except pylast.WSError as e:
            self.logger.error(f"Session verification failed: {e}")
            # If authentication failed, clear the session key
            if "Invalid session key" in str(e):
                self.clear_session()
            return False
        except Exception as e:
            self.logger.error(f"Error verifying session: {e}")
            return False
    
    def get_network(self):
        """
        Get an authenticated LastFM network.
        
        Returns:
            pylast.LastFMNetwork or None: The authenticated LastFM network or None if unavailable.
        """
        if not PYLAST_AVAILABLE:
            return None
            
        # If we already have a network with a session key, verify and return it
        if self.network and self.session_key:
            if self._verify_session():
                return self.network
        
        # If we don't have a working session, try to authenticate if we have credentials
        if self.username and self.password and self.api_secret:
            if self.authenticate():
                return self.network
        
        # If we can't authenticate but still have API key, return a non-authenticated network
        if self.network:
            return self.network
        
        return None
    
    def clear_session(self):
        """Clear the cached session to force a new authentication."""
        if os.path.exists(self.session_key_path):
            try:
                os.remove(self.session_key_path)
                self.logger.info(f"Removed cached session key at {self.session_key_path}")
            except Exception as e:
                self.logger.error(f"Error removing cached session key: {e}")
        
        # Reset instance variables
        self.session_key = None
        if self.network:
            self.network.session_key = None
        
        return True
    
    def is_authenticated(self):
        """Check if we have a valid session key."""
        return self._verify_session() if self.session_key else False
    
    def get_user_info(self):
        """
        Get information about the authenticated user.
        
        Returns:
            dict or None: User information or None if not authenticated.
        """
        if not self.network or not self.username:
            return None
            
        try:
            user = self.network.get_user(self.username)
            
            # Get basic user info
            info = {
                'name': self.username,
                'playcount': user.get_playcount(),
                'url': user.get_url(),
            }
            
            # Try to get more info if we're authenticated
            if self.is_authenticated():
                try:
                    info['loved_tracks_count'] = len(user.get_loved_tracks(limit=1))
                    info['subscriber'] = user.is_subscriber()
                except:
                    pass
                    
            return info
        except Exception as e:
            self.logger.error(f"Error getting user info: {e}")
            return None
    
    def get_top_artists(self, limit=50, period='overall'):
        """
        Get user's top artists from LastFM.
        
        Args:
            limit (int): Maximum number of artists to return
            period (str): Time period - overall, 7day, 1month, 3month, 6month, 12month
            
        Returns:
            list: List of artist dictionaries with name and playcount
        """
        if not self.network or not self.username:
            return []
            
        try:
            user = self.network.get_user(self.username)
            top_artists = user.get_top_artists(period=period, limit=limit)
            
            result = []
            for artist_item in top_artists:
                artist = artist_item.item
                result.append({
                    'name': artist.get_name(),
                    'playcount': artist_item.weight,
                    'url': artist.get_url(),
                    # Try to get mbid if available
                    'mbid': artist.get_mbid() if hasattr(artist, 'get_mbid') else None
                })
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting top artists: {e}")
            return []
    
    def love_track(self, artist_name, track_name):
        """
        Love a track on LastFM.
        
        Args:
            artist_name (str): Name of the artist
            track_name (str): Name of the track
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_authenticated():
            self.logger.error("Authentication required to love tracks")
            return False
            
        try:
            track = self.network.get_track(artist_name, track_name)
            track.love()
            self.logger.info(f"Loved track: {artist_name} - {track_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error loving track: {e}")
            return False
    
    def get_artist_top_tracks(self, artist_name, limit=10):
        """
        Get top tracks for an artist.
        
        Args:
            artist_name (str): Name of the artist
            limit (int): Maximum number of tracks to return
            
        Returns:
            list: List of track dictionaries
        """
        if not self.network:
            return []
            
        try:
            artist = self.network.get_artist(artist_name)
            top_tracks = artist.get_top_tracks(limit=limit)
            
            result = []
            for track_item in top_tracks:
                track = track_item.item
                result.append({
                    'name': track.get_name(),
                    'playcount': track_item.weight,
                    'url': track.get_url(),
                    'artist': track.get_artist().get_name()
                })
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting top tracks for {artist_name}: {e}")
            return []
    
    def follow_artist(self, artist_name):
        """
        Follow an artist by loving their top track (LastFM doesn't have direct artist follow).
        
        Args:
            artist_name (str): Name of the artist to follow
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_authenticated():
            self.logger.error("Authentication required to follow artists")
            return False
            
        try:
            # Find the artist's top track
            artist = self.network.get_artist(artist_name)
            top_tracks = artist.get_top_tracks(limit=1)
            
            if not top_tracks:
                self.logger.warning(f"No tracks found for artist {artist_name}")
                return False
                
            # Love the top track
            top_track = top_tracks[0].item
            top_track.love()
            
            self.logger.info(f"Followed artist {artist_name} by loving track: {top_track.get_name()}")
            return True
        except Exception as e:
            self.logger.error(f"Error following artist {artist_name}: {e}")
            return False