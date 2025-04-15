import sys
import os
import json
import time
import logging
import requests
from pathlib import Path
from bs4 import BeautifulSoup  # Add this dependency

class MusicBrainzAuthManager:
    """Handles authentication with MusicBrainz API"""
    
    def __init__(self, username=None, password=None, app_name="MuspyModule", app_version="1.0", 
                 parent_widget=None, project_root=None):
        """
        Initialize the MusicBrainz authentication manager
        
        Args:
            username (str): MusicBrainz username
            password (str): MusicBrainz password
            app_name (str): Name of the application for user agent
            app_version (str): Version of the application for user agent
            parent_widget: Parent widget for UI interactions
            project_root (Path): Project root directory for cache storage
        """
        self.username = username
        self.password = password
        self.app_name = app_name
        self.app_version = app_version
        self.parent_widget = parent_widget

        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from base_module import PROJECT_ROOT
        self.project_root = project_root or Path.cwd()
        
        # Set up cache directory
        self.cache_dir = self.project_root / ".content" / "cache" / "musicbrainz"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # User agent for API requests (required by MusicBrainz)
        self.user_agent = f"{self.app_name}/{self.app_version} ( user@example.com )"
        
        # Session and cookies
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        
        # Logger
        self.logger = logging.getLogger("MusicBrainzAuth")
        
        # Load saved cookies if available
        self._load_cookies()
    
    def _load_cookies(self):
        """Load authentication cookies from cache if available"""
        cookies_path = self.cache_dir / "mb_cookies.json"
        if cookies_path.exists():
            try:
                with open(cookies_path, 'r') as f:
                    cookies_dict = json.load(f)
                    
                # Recreate the session with saved cookies
                self.session = requests.Session()
                self.session.headers.update({"User-Agent": self.user_agent})
                
                for name, value in cookies_dict.items():
                    self.session.cookies.set(name, value)
                    
                self.logger.info("Loaded cookies from cache")
                return True
            except Exception as e:
                self.logger.error(f"Error loading cached cookies: {e}")
                return False
        return False
    
    def _save_cookies(self):
        """Save authentication cookies to cache"""
        cookies_path = self.cache_dir / "mb_cookies.json"
        try:
            # Convert cookies jar to dict
            cookies_dict = {name: value for name, value in self.session.cookies.items()}
            
            with open(cookies_path, 'w') as f:
                json.dump(cookies_dict, f)
                
            self.logger.info("Saved cookies to cache")
            return True
        except Exception as e:
            self.logger.error(f"Error saving cookies: {e}")
            return False
    
    def is_authenticated(self):
        """Check if user is authenticated by testing a restricted page"""
        try:
            # Test authentication by accessing the user's collection page
            test_url = f"https://musicbrainz.org/user/{self.username}/collections"
            response = self.session.get(test_url)
            
            # If we're redirected to login, we're not authenticated
            if "/login" in response.url:
                self.logger.info("Not authenticated with MusicBrainz")
                return False
                
            # If we get a 200 response, we're authenticated
            if response.status_code == 200:
                self.logger.info("Successfully authenticated with MusicBrainz")
                return True
                
            self.logger.warning(f"Unknown authentication state: {response.status_code}")
            return False
        except Exception as e:
            self.logger.error(f"Error checking authentication: {e}")
            return False
    
    def authenticate(self, username=None, password=None):
        """
        Authenticate with MusicBrainz
        
        Args:
            username (str, optional): MusicBrainz username (overrides instance attribute)
            password (str, optional): MusicBrainz password (overrides instance attribute)
            
        Returns:
            bool: Whether authentication was successful
        """
        # Update credentials if provided
        if username:
            self.username = username
        if password:
            self.password = password
            
        # Check if we have credentials
        if not self.username or not self.password:
            self.logger.error("Cannot authenticate: username or password not provided")
            return False
            
        try:
            # Reset session
            self.session = requests.Session()
            self.session.headers.update({"User-Agent": self.user_agent})
            
            # First get the login page to get the CSRF token
            login_url = "https://musicbrainz.org/login"
            response = self.session.get(login_url)
            
            if response.status_code != 200:
                self.logger.error(f"Failed to get login page: {response.status_code}")
                return False
            
            # Extract CSRF token from the page
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf'})
            
            if not csrf_input or not csrf_input.get('value'):
                self.logger.error("Could not find CSRF token on login page")
                return False
                
            csrf_token = csrf_input.get('value')
            
            # Submit login form
            login_data = {
                'csrf': csrf_token,
                'username': self.username,
                'password': self.password,
                'remember_me': '1'  # Stay logged in
            }
            
            # Make the login request
            response = self.session.post(login_url, data=login_data)
            
            # Check if login was successful
            if "/login" in response.url:
                # Still on login page - probably failed
                self.logger.error("Login failed - redirected back to login page")
                return False
                
            # Save cookies for future sessions
            self._save_cookies()
            
            # Verify we're actually logged in
            return self.is_authenticated()
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def get_user_collections(self):
        """
        Get user's MusicBrainz collections
        
        Returns:
            list: List of collections or empty list if error
        """
        if not self.is_authenticated():
            self.logger.warning("Not authenticated, cannot get collections")
            return []
            
        try:
            # Get the user's collections page
            url = f"https://musicbrainz.org/user/{self.username}/collections"
            response = self.session.get(url)
            
            if response.status_code != 200:
                self.logger.error(f"Error getting collections page: {response.status_code}")
                return []
                
            # Parse the HTML to extract collections
            soup = BeautifulSoup(response.text, 'html.parser')
            collection_items = soup.select("ul.collections li")
            
            collections = []
            for item in collection_items:
                # Extract the collection ID from the URL
                link = item.find('a')
                if not link or not link.get('href'):
                    continue
                    
                href = link.get('href')
                collection_id = href.split('/')[-1]
                collection_name = link.text.strip()
                
                # Extract count if available
                count_span = item.select_one("span.count")
                count = int(count_span.text.strip('()')) if count_span else 0
                
                collections.append({
                    'id': collection_id,
                    'name': collection_name,
                    'count': count
                })
                
            return collections
            
        except Exception as e:
            self.logger.error(f"Error getting collections: {e}")
            return []
    
    def add_releases_to_collection(self, collection_id, release_ids):
        """
        Add releases to a MusicBrainz collection
        
        Args:
            collection_id (str): ID of the collection
            release_ids (list): List of release MBIDs to add
            
        Returns:
            bool: Whether the operation was successful
        """
        if not self.is_authenticated():
            self.logger.warning("Not authenticated, cannot add to collection")
            return False
            
        if not collection_id or not release_ids:
            self.logger.error("Collection ID or release IDs not provided")
            return False
            
        try:
            # First get the edit collection page to extract CSRF token
            url = f"https://musicbrainz.org/collection/{collection_id}/edit"
            response = self.session.get(url)
            
            if response.status_code != 200:
                self.logger.error(f"Error accessing collection edit page: {response.status_code}")
                return False
                
            # Parse the HTML to extract CSRF token
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf'})
            
            if not csrf_input or not csrf_input.get('value'):
                self.logger.error("Could not find CSRF token on collection edit page")
                return False
                
            csrf_token = csrf_input.get('value')
            
            # Prepare release IDs
            if isinstance(release_ids, list):
                releases_str = ','.join(release_ids)
            else:
                releases_str = release_ids
                
            # Build data for the POST request
            data = {
                'csrf': csrf_token,
                'add-releases': releases_str
            }
            
            # Make the POST request
            response = self.session.post(url, data=data)
            
            # Check response
            if response.status_code in [200, 201, 302, 303]:
                # Success status codes (302 is redirect after success)
                self.logger.info(f"Successfully added releases to collection {collection_id}")
                return True
            else:
                self.logger.error(f"Error adding to collection: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding to collection: {e}")
            return False
    
    def clear_session(self):
        """Clear authentication session"""
        # Reset session
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        
        # Remove cached cookies
        cookies_path = self.cache_dir / "mb_cookies.json"
        if cookies_path.exists():
            try:
                os.remove(cookies_path)
                self.logger.info("Removed cached cookies")
            except Exception as e:
                self.logger.error(f"Error removing cached cookies: {e}")