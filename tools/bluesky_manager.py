import logging
import requests

class BlueskyManager:
    """
    Class to manage Bluesky operations for artists
    """
    def __init__(self, parent=None, project_root=None, username=None):
        """
        Initialize the Bluesky Manager
        
        Args:
            parent (QWidget, optional): Parent widget for UI operations
            project_root (str, optional): Project root directory
            username (str, optional): Bluesky username to use for operations
        """
        self.logger = logging.getLogger("BlueskyManager")
        self.parent = parent
        self.project_root = project_root
        self.username = username  # Nombre de usuario de Bluesky
        
        # Cache for Bluesky results
        self.cache = {}
        
        self.logger.info(f"BlueskyManager initialized with username: {self.username}")
        
    def check_bluesky_user(self, username):
        """
        Check if a user exists on Bluesky
        
        Args:
            username (str): Username to check
            
        Returns:
            dict or None: User info if found, None otherwise
        """
        # Normalize the username
        username = username.strip().lower()
        if not username:
            return None
            
        # If not has the domain .bsky.social, add it
        if not username.endswith('.bsky.social'):
            username = f"{username}.bsky.social"
        
        # URL of the Bluesky API
        url = f"https://api.bsky.app/xrpc/com.atproto.identity.resolveHandle"
        params = {'handle': username}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return {
                    'handle': username,
                    'did': data.get('did', ''),
                    'found': True
                }
            else:
                return None
        except Exception as e:
            self.logger.error(f"Error checking Bluesky user {username}: {e}")
            return None
            
    def get_user_profile(self, user_did):
        """
        Get profile information for a Bluesky user
        
        Args:
            user_did (str): DID of the user
            
        Returns:
            dict or None: Profile info if found, None otherwise
        """
        if not user_did:
            return None
            
        # URL for getting profile info
        url = f"https://api.bsky.app/xrpc/app.bsky.actor.getProfile"
        params = {'actor': user_did}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            self.logger.error(f"Error getting profile for {user_did}: {e}")
            return None
            
    def get_recent_posts(self, user_did, limit=3):
        """
        Get recent posts for a Bluesky user
        
        Args:
            user_did (str): DID of the user
            limit (int): Maximum number of posts to return
            
        Returns:
            list: List of recent posts
        """
        if not user_did:
            return []
            
        # URL for getting user feed
        url = f"https://api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
        params = {'actor': user_did, 'limit': limit}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                # Extract the posts from the feed
                if 'feed' in data:
                    for post_item in data['feed'][:limit]:
                        if 'post' in post_item and 'record' in post_item['post']:
                            posts.append({
                                'text': post_item['post']['record'].get('text', ''),
                                'created_at': post_item['post']['record'].get('createdAt', '')
                            })
                
                return posts
            else:
                return []
        except Exception as e:
            self.logger.error(f"Error getting posts for {user_did}: {e}")
            return []



    def follow_user(self, did):
        """
        Follow a user on Bluesky
        
        Args:
            did (str): DID of the user to follow
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.username or not did:
            return False
        
        # First we need to authenticate with our username
        if not self._authenticate():
            return False
        
        # Then we can follow the user
        url = "https://api.bsky.app/xrpc/app.bsky.graph.follow"
        
        # Prepare data for follow request
        data = {
            "subject": did,
            "createdAt": datetime.datetime.now().isoformat()
        }
        
        try:
            # Make the request with our access token
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code in [200, 201]:
                return True
            else:
                self.logger.error(f"Failed to follow user: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error following user on Bluesky: {e}")
            return False

    def _authenticate(self):
        """
        Authenticate with Bluesky
        
        Returns:
            bool: True if authentication is successful, False otherwise
        """
        if not self.username:
            self.logger.error("No Bluesky username configured")
            return False
        
        # Check if we already have a valid access token
        if hasattr(self, 'access_token') and hasattr(self, 'token_expiry'):
            # Check if token is still valid
            if datetime.datetime.now() < self.token_expiry:
                return True
        
        # We need a password to authenticate
        if not hasattr(self, 'password') or not self.password:
            # Ask for password through parent widget if available
            if self.parent:
                from PyQt6.QtWidgets import QInputDialog, QLineEdit
                password, ok = QInputDialog.getText(
                    self.parent,
                    "Bluesky Authentication",
                    f"Enter password for Bluesky user {self.username}:",
                    QLineEdit.EchoMode.Password
                )
                
                if ok and password:
                    self.password = password
                else:
                    return False
            else:
                return False
        
        # Now attempt to authenticate
        url = "https://api.bsky.app/xrpc/com.atproto.server.createSession"
        
        # Prepare login data
        data = {
            "identifier": self.username,
            "password": self.password
        }
        
        try:
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                
                # Store the access token
                self.access_token = result.get('accessJwt')
                self.refresh_token = result.get('refreshJwt')
                
                # Set token expiry (typically 2 hours for Bluesky)
                self.token_expiry = datetime.datetime.now() + datetime.timedelta(hours=2)
                
                # Store the DID for the authenticated user
                self.did = result.get('did')
                
                return True
            else:
                self.logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error during authentication: {e}")
            return False