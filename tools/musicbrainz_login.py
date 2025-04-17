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
    
    def authenticate(self, username=None, password=None, silent=False):
        """
        Authenticate with MusicBrainz with improved token handling
        
        Args:
            username (str, optional): MusicBrainz username (overrides instance attribute)
            password (str, optional): MusicBrainz password (overrides instance attribute)
            silent (bool): Whether to suppress UI interactions
            
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
            
            # Extract CSRF token using more robust methods
            csrf_token = None
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Method 1: Look for input with name="csrf"
            csrf_input = soup.find('input', {'name': 'csrf'})
            if csrf_input and csrf_input.get('value'):
                csrf_token = csrf_input.get('value')
                
            # Method 2: If not found, look for a meta tag with name="csrf-token"
            if not csrf_token:
                meta_csrf = soup.find('meta', {'name': 'csrf-token'})
                if meta_csrf and meta_csrf.get('content'):
                    csrf_token = meta_csrf.get('content')
                    
            # Method 3: Try to find it in any form
            if not csrf_token:
                for form in soup.find_all('form'):
                    csrf_input = form.find('input', {'name': 'csrf'})
                    if csrf_input and csrf_input.get('value'):
                        csrf_token = csrf_input.get('value')
                        break
            
            # Log HTML for debugging if token not found
            if not csrf_token:
                self.logger.error("Could not find CSRF token on login page")
                self.logger.debug(f"HTML content (first 500 chars): {response.text[:500]}...")
                
                # Try to continue without CSRF - might still work for some operations
                csrf_token = ""
            
            # Submit login form
            login_data = {
                'csrf': csrf_token,
                'username': self.username,
                'password': self.password,
                'remember_me': '1'  # Stay logged in
            }
            
            # Make the login request
            response = self.session.post(login_url, data=login_data, allow_redirects=True)
            
            # Check if login was successful - look for common success indicators
            success_indicators = [
                "/login" not in response.url,  # Not redirected back to login
                "logged-in" in response.text,  # Page indicates logged in
                self.session.cookies.get('musicbrainz_server_session')  # Session cookie exists
            ]
            
            # Consider logged in if any success indicator is present
            if any(success_indicators):
                self.logger.info("Login appears successful")
                self._save_cookies()
                
                # Do a final check by trying to access a protected page
                return self.is_authenticated()
            else:
                self.logger.error("Login failed - no success indicators found")
                return False
                
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
            
            # Enable debug output to see the page structure
            self.logger.debug(f"Collection page title: {soup.title.text if soup.title else 'No title'}")
            
            # Specifically look for the user's collections section
            collections = []
            
            # Try different possible selectors for the collections list
            collection_lists = soup.select("div.collection-list")
            if not collection_lists:
                # Try alternative selectors
                collection_lists = soup.select("ul.collections")
                
            if not collection_lists:
                # More aggressive search - find any list that might contain collections
                collection_lists = soup.select("ul")
            
            for collection_list in collection_lists:
                collection_items = collection_list.select("li")
                
                for item in collection_items:
                    # Extract the collection ID from the URL
                    link = item.find('a')
                    if not link or not link.get('href'):
                        continue
                        
                    href = link.get('href')
                    if '/collection/' not in href:
                        continue
                        
                    collection_id = href.split('/')[-1]
                    collection_name = link.text.strip()
                    
                    # Extract count if available
                    count_span = item.select_one("span.count")
                    count_text = count_span.text.strip() if count_span else ""
                    
                    # Try to parse count from text like "(123)"
                    count = 0
                    if count_text:
                        import re
                        count_match = re.search(r'\((\d+)\)', count_text)
                        if count_match:
                            count = int(count_match.group(1))
                    
                    collections.append({
                        'id': collection_id,
                        'name': collection_name,
                        'count': count
                    })
            
            # If still no collections found, try a more direct approach
            if not collections:
                # Look specifically for collection links
                collection_links = soup.select("a[href*='/collection/']")
                
                for link in collection_links:
                    href = link.get('href')
                    if '/collection/' in href:
                        collection_id = href.split('/')[-1]
                        collection_name = link.text.strip()
                        
                        # Add only if it's not a duplicate
                        if not any(c['id'] == collection_id for c in collections):
                            collections.append({
                                'id': collection_id,
                                'name': collection_name,
                                'count': 0  # Count unknown
                            })
            
            # Log all found collections
            self.logger.info(f"Found {len(collections)} collections for user {self.username}")
            for collection in collections:
                self.logger.info(f"Collection: {collection['name']} (ID: {collection['id']}, Count: {collection['count']})")
            
            return collections
            
        except Exception as e:
            self.logger.error(f"Error getting collections: {e}")
            return []
    
   
    
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


    def get_collections_by_api(self, username=None):
        """
        Get all collections for the authenticated user or a specified user using the MusicBrainz API
        
        Args:
            username (str, optional): Username to get collections for. 
                                    If None, uses the authenticated user.
        
        Returns:
            list: List of collection dictionaries with id, name, and count
        """
        if not self.is_authenticated():
            self.logger.error("Not authenticated with MusicBrainz")
            return []
        
        # Use the provided username or default to authenticated user
        username_to_use = username or self.username
        
        if not username_to_use:
            self.logger.error("No username provided and not authenticated")
            return []
        
        try:
            # Use the MusicBrainz API to get collections
            url = f"https://musicbrainz.org/ws/2/collection"
            params = {
                "editor": username_to_use,
                "fmt": "json"
            }
            
            headers = {
                "User-Agent": "MuspyReleasesModule/1.0"
            }
            
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                collections = []
                
                if "collections" in data:
                    for coll in data["collections"]:
                        collection = {
                            "id": coll.get("id"),
                            "name": coll.get("name"),
                            "entity_count": coll.get("entity_count", 0),
                            "type": coll.get("entity_type")
                        }
                        collections.append(collection)
                    
                    self.logger.info(f"Found {len(collections)} collections for user {username_to_use}")
                    return collections
                else:
                    self.logger.warning(f"No collections found in API response for {username_to_use}")
                    return []
            else:
                self.logger.error(f"Error getting collections: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting collections by API: {e}", exc_info=True)
            return []

    def get_collection_contents(self, collection_id, entity_type="release"):
        """
        Get the contents of a MusicBrainz collection using the API
        
        Args:
            collection_id (str): ID of the collection
            entity_type (str): Type of entity in the collection (release, artist, etc.)
            
        Returns:
            list: List of entities in the collection
        """
        if not self.is_authenticated():
            self.logger.error("Not authenticated with MusicBrainz")
            return []
        
        try:
            # Use the MusicBrainz API to get collection contents
            url = f"https://musicbrainz.org/ws/2/{entity_type}"
            params = {
                "collection": collection_id,
                "fmt": "json",
                "limit": 100  # Adjust as needed
            }
            
            headers = {
                "User-Agent": "MuspyReleasesModule/1.0"
            }
            
            entities = []
            offset = 0
            total_count = None
            
            # Paginate through results if needed
            while True:
                params["offset"] = offset
                response = self.session.get(url, params=params, headers=headers)
                
                if response.status_code != 200:
                    self.logger.error(f"Error getting collection contents: {response.status_code} - {response.text}")
                    break
                    
                data = response.json()
                
                # Get total count for pagination
                if total_count is None:
                    total_count = data.get("count", 0)
                    
                # Different entity types have different response structures
                items = []
                if entity_type == "release":
                    items = data.get("releases", [])
                elif entity_type == "artist":
                    items = data.get("artists", [])
                # Add more entity types as needed
                
                entities.extend(items)
                
                # Check if we need to fetch more pages
                offset += len(items)
                if offset >= total_count or len(items) == 0:
                    break
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Error getting collection contents: {e}", exc_info=True)
            return []

    def add_releases_to_collection(self, collection_id, release_mbids):
        """
        Add releases to a MusicBrainz collection using the API
        
        Args:
            collection_id (str): ID of the collection
            release_mbids (list): List of MusicBrainz IDs of releases to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_authenticated():
            self.logger.error("Not authenticated with MusicBrainz")
            return False
        
        try:
            # MusicBrainz API allows adding multiple releases at once
            # But there's a limit to how many we can add in one request
            batch_size = 100  # Adjust as needed
            success = True
            
            for i in range(0, len(release_mbids), batch_size):
                batch = release_mbids[i:i+batch_size]
                
                # Join MBIDs with semicolons as per API spec
                mbids_param = ";".join(batch)
                
                # Use the MusicBrainz API to add releases
                url = f"https://musicbrainz.org/ws/2/collection/{collection_id}/releases/{mbids_param}"
                
                headers = {
                    "User-Agent": "MuspyReleasesModule/1.0"
                }
                
                response = self.session.put(url, headers=headers)
                
                if response.status_code not in [200, 201]:
                    self.logger.error(f"Error adding releases: {response.status_code} - {response.text}")
                    success = False
                    break
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error adding releases to collection: {e}", exc_info=True)
            return False

    def remove_release_from_collection(self, collection_id, release_mbid):
        """
        Remove a release from a MusicBrainz collection using the API
        
        Args:
            collection_id (str): ID of the collection
            release_mbid (str): MusicBrainz ID of the release to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_authenticated():
            self.logger.error("Not authenticated with MusicBrainz")
            return False
        
        try:
            # Use the MusicBrainz API to remove the release
            url = f"https://musicbrainz.org/ws/2/collection/{collection_id}/releases/{release_mbid}"
            
            headers = {
                "User-Agent": "MuspyReleasesModule/1.0"
            }
            
            response = self.session.delete(url, headers=headers)
            
            if response.status_code in [200, 204]:
                return True
            else:
                self.logger.error(f"Error removing release: {response.status_code} - {response.text}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error removing release from collection: {e}", exc_info=True)
            return False             