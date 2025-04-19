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
        """Check if user is authenticated by testing a restricted page with improved checking"""
        try:
            if not self.username:
                self.logger.error("No username set for authentication check")
                return False
                
            # Test authentication by accessing the user's collection page
            test_url = f"https://musicbrainz.org/user/{self.username}/collections"
            
            # Add headers to mimic browser behavior
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "User-Agent": self.user_agent,
                "Referer": "https://musicbrainz.org/"
            }
            
            response = self.session.get(test_url, headers=headers)
            
            # Log detailed info
            self.logger.debug(f"Auth check response URL: {response.url}")
            self.logger.debug(f"Auth check status code: {response.status_code}")
            
            # If we're redirected to login, we're not authenticated
            if "/login" in response.url:
                self.logger.info("Not authenticated with MusicBrainz (redirected to login)")
                return False
                
            # If we get a 200 response, check for additional indicators of being logged in
            if response.status_code == 200:
                # Check for presence of username in the response
                if self.username.lower() in response.text.lower():
                    self.logger.info("Successfully authenticated with MusicBrainz")
                    return True
                    
                # Check for typical elements only shown to logged in users
                soup = BeautifulSoup(response.text, 'html.parser')
                logged_in_indicators = [
                    soup.select_one('.logged-in'),
                    soup.select_one('#header-menu-user'),
                    soup.find('a', string='Log out') or soup.find('a', string='Logout')
                ]
                
                if any(logged_in_indicators):
                    self.logger.info("Successfully authenticated with MusicBrainz (found UI indicators)")
                    return True
                
                self.logger.warning("Got 200 response but no clear indicators of being logged in")
                return False
                
            self.logger.warning(f"Unknown authentication state: {response.status_code}")
            return False
        except Exception as e:
            self.logger.error(f"Error checking authentication: {e}", exc_info=True)
            return False
    
    def authenticate(self, username=None, password=None, silent=False):
        """
        Authenticate with MusicBrainz with improved token handling and OAuth support
        
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
            # Reset session with proper headers
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            })
            
            # First get the login page to get the CSRF token
            login_url = "https://musicbrainz.org/login"
            response = self.session.get(login_url)
            
            if response.status_code != 200:
                self.logger.error(f"Failed to get login page: {response.status_code}")
                self.logger.debug(f"Response content: {response.text[:200]}...")
                return False
            
            # Extract CSRF token using more robust methods
            csrf_token = None
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Method 1: Look for input with name="csrf"
            csrf_input = soup.find('input', {'name': 'csrf'})
            if csrf_input and csrf_input.get('value'):
                csrf_token = csrf_input.get('value')
                self.logger.debug(f"Found CSRF token from input: {csrf_token[:10]}...")
                    
            # Method 2: If not found, look for a meta tag with name="csrf-token"
            if not csrf_token:
                meta_csrf = soup.find('meta', {'name': 'csrf-token'})
                if meta_csrf and meta_csrf.get('content'):
                    csrf_token = meta_csrf.get('content')
                    self.logger.debug(f"Found CSRF token from meta tag: {csrf_token[:10]}...")
                        
            # Method 3: Try to find it in any form
            if not csrf_token:
                for form in soup.find_all('form'):
                    csrf_input = form.find('input', {'name': 'csrf'})
                    if csrf_input and csrf_input.get('value'):
                        csrf_token = csrf_input.get('value')
                        self.logger.debug(f"Found CSRF token from form: {csrf_token[:10]}...")
                        break
            
            # Method 4: Look for hidden inputs in login form
            if not csrf_token:
                login_form = soup.find('form', {'action': '/login'}) or soup.find('form', {'id': 'login-form'})
                if login_form:
                    hidden_inputs = login_form.find_all('input', {'type': 'hidden'})
                    for hidden in hidden_inputs:
                        if hidden.get('name') and hidden.get('value'):
                            if hidden.get('name') == 'csrf':
                                csrf_token = hidden.get('value')
                                self.logger.debug(f"Found CSRF token from login form: {csrf_token[:10]}...")
                                break
            
            # Method 5: Extract from cookies if present
            if not csrf_token:
                csrf_cookie = self.session.cookies.get('_mb_csrf_token')
                if csrf_cookie:
                    csrf_token = csrf_cookie
                    self.logger.debug(f"Found CSRF token from cookies: {csrf_token[:10]}...")
            
            # Log information for debugging
            if csrf_token:
                self.logger.debug(f"Found CSRF token: {csrf_token[:10]}...")
                self.logger.debug(f"Current cookies: {dict(self.session.cookies)}")
            else:
                # Log more details to diagnose the issue
                self.logger.error("Could not find CSRF token on login page")
                # Save HTML to file for debugging
                try:
                    debug_dir = os.path.join(self.cache_dir, "debug")
                    os.makedirs(debug_dir, exist_ok=True)
                    with open(os.path.join(debug_dir, "login_page.html"), 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    self.logger.debug(f"Saved login page HTML to {debug_dir}/login_page.html")
                except Exception as e:
                    self.logger.error(f"Failed to save debug HTML: {e}")
                
                # Try to continue without CSRF - might still work for some operations
                csrf_token = ""
            
            # Submit login form - must include all expected fields
            login_data = {
                'csrf': csrf_token,
                'username': self.username,
                'password': self.password,
                'remember_me': '1',  # Stay logged in
                'loginform': '1'     # Indicate this is the login form
            }
            
            # Set proper headers for form submission
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": login_url,
                "Origin": "https://musicbrainz.org"
            }
            
            # Make the login request
            response = self.session.post(login_url, data=login_data, headers=headers, allow_redirects=True)
            
            # Check if login was successful - look for common success indicators
            success_indicators = [
                "/login" not in response.url,  # Not redirected back to login
                "logged-in" in response.text,  # Page indicates logged in
                self.session.cookies.get('musicbrainz_server_session')  # Session cookie exists
            ]
            
            # Log detailed info for debugging
            self.logger.debug(f"Login response URL: {response.url}")
            self.logger.debug(f"Login response status: {response.status_code}")
            self.logger.debug(f"Session cookies after login: {dict(self.session.cookies)}")
            
            # Consider logged in if any success indicator is present
            if any(success_indicators):
                self.logger.info("Login appears successful")
                self._save_cookies()
                
                # Store CSRF token for later use in the session
                if csrf_token:
                    self.session.headers.update({'X-MB-CSRF-Token': csrf_token})
                
                # Do a final check by trying to access a protected page
                return self.is_authenticated()
            else:
                self.logger.error("Login failed - no success indicators found")
                
                # Try to extract error message if present
                try:
                    error_soup = BeautifulSoup(response.text, 'html.parser')
                    error_elem = error_soup.select_one('.error') or error_soup.select_one('.alert-error')
                    if error_elem:
                        error_message = error_elem.text.strip()
                        self.logger.error(f"Login error message: {error_message}")
                except Exception as e:
                    self.logger.error(f"Error parsing login response: {e}")
                    
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}", exc_info=True)
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
        with improved error handling and authentication
        
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
                "User-Agent": "MuspyReleasesModule/1.0",
                "Accept": "application/json"
            }
            
            # Make the request with proper headers
            response = self.session.get(url, params=params, headers=headers)
            
            # Log the response for debugging
            self.logger.debug(f"API response for collections: status={response.status_code}")
            
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
            elif response.status_code == 401:
                self.logger.warning("Authentication issue when fetching collections - trying to re-authenticate")
                
                # Try to re-authenticate and try again
                if self.authenticate(silent=True):
                    # If successful, make a recursive call with the same parameters
                    return self.get_collections_by_api(username)
                else:
                    self.logger.error("Re-authentication failed, cannot get collections")
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
        Add releases to a MusicBrainz collection using the API with improved authentication
        
        Args:
            collection_id (str): ID of the collection
            release_mbids (list): List of MusicBrainz IDs of releases to add
                
        Returns:
            dict: Result with success status and details
        """
        if not self.is_authenticated():
            self.logger.error("Not authenticated with MusicBrainz")
            return {"success": False, "error": "Not authenticated"}
        
        try:
            # MusicBrainz API allows adding multiple releases at once
            # But there's a limit to how many we can add in one request
            batch_size = 20  # Smaller batch size to reduce errors
            results = {
                "success": False,
                "total": len(release_mbids),
                "added": 0,
                "failed_batches": []
            }
            
            # Ensure we have a valid CSRF token
            csrf_token = self.session.headers.get('X-MB-CSRF-Token')
            
            # If no CSRF token in headers, try to extract from cookies
            if not csrf_token:
                csrf_cookie = self.session.cookies.get('_mb_csrf_token')
                if csrf_cookie:
                    csrf_token = csrf_cookie
                    self.session.headers.update({'X-MB-CSRF-Token': csrf_token})
                    self.logger.info(f"Using CSRF token from cookies: {csrf_token[:10]}...")
            
            # Still no CSRF token, try to re-authenticate to get a fresh one
            if not csrf_token:
                self.logger.warning("No CSRF token found, re-authenticating...")
                if not self.authenticate(silent=True):
                    return {"success": False, "error": "Failed to obtain CSRF token"}
                csrf_token = self.session.headers.get('X-MB-CSRF-Token')
                if not csrf_token:
                    return {"success": False, "error": "Still couldn't obtain CSRF token after re-auth"}
            
            for i in range(0, len(release_mbids), batch_size):
                batch = release_mbids[i:i+batch_size]
                batch_idx = i // batch_size + 1
                
                # Join MBIDs with semicolons as per API spec
                mbids_param = ";".join(batch)
                
                # Use the MusicBrainz API to add releases
                url = f"https://musicbrainz.org/ws/2/collection/{collection_id}/releases/{mbids_param}"
                
                # Proper headers with content type, CSRF token and cookies
                headers = {
                    "User-Agent": self.user_agent,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-MB-CSRF-Token": csrf_token,
                    "Origin": "https://musicbrainz.org",
                    "Referer": f"https://musicbrainz.org/collection/{collection_id}"
                }
                
                # Log full request details for debugging
                self.logger.debug(f"PUT request to {url}")
                self.logger.debug(f"Headers: {headers}")
                self.logger.debug(f"Cookies: {dict(self.session.cookies)}")
                
                # Make the request
                response = self.session.put(url, headers=headers)
                
                # Log response details
                self.logger.debug(f"Response status: {response.status_code}")
                self.logger.debug(f"Response headers: {dict(response.headers)}")
                try:
                    self.logger.debug(f"Response body: {response.text[:200]}")
                except:
                    pass
                
                if response.status_code in [200, 201]:
                    self.logger.info(f"Successfully added batch {batch_idx} ({len(batch)} releases)")
                    results["added"] += len(batch)
                elif response.status_code == 401:
                    self.logger.warning(f"Authentication failed for batch {batch_idx}, trying to re-authenticate")
                    results["failed_batches"].append(batch_idx)
                    
                    # Try to re-authenticate and continue
                    if self.authenticate(silent=True):
                        csrf_token = self.session.headers.get('X-MB-CSRF-Token')
                        self.logger.info(f"Re-authenticated successfully with new CSRF token: {csrf_token[:10] if csrf_token else None}")
                        
                        # Try this batch again after successful re-auth
                        headers["X-MB-CSRF-Token"] = csrf_token  # Update with new token
                        response = self.session.put(url, headers=headers)
                        
                        if response.status_code in [200, 201]:
                            self.logger.info(f"Successfully added batch {batch_idx} after re-auth")
                            results["added"] += len(batch)
                            # Remove from failed batches since it succeeded
                            results["failed_batches"].remove(batch_idx)
                        else:
                            self.logger.error(f"Still failed after re-auth: {response.status_code} - {response.text}")
                    else:
                        self.logger.error("Re-authentication failed, stopping batch processing")
                        results["error"] = "Authentication failed during processing"
                        break
                else:
                    self.logger.error(f"Failed to add batch {batch_idx}: {response.status_code} - {response.text}")
                    results["failed_batches"].append(batch_idx)
                    results["error"] = f"API error: {response.status_code} - {response.text[:100]}"
                
                # Add a small delay between batches to avoid rate limiting
                import time
                time.sleep(0.5)
            
            # Update success flag based on results
            results["success"] = results["added"] > 0
            
            return results
                
        except Exception as e:
            self.logger.error(f"Error adding releases to collection: {e}", exc_info=True)
            return {"success": False, "error": str(e), "added": 0, "total": len(release_mbids)}

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



    def create_collection(self, name, entity_type="release"):
        """
        Create a new MusicBrainz collection with proper authorization
        
        Args:
            name (str): Name for the new collection
            entity_type (str): Type of entities in the collection (default: "release")
                
        Returns:
            dict: Result with success status and collection info
        """
        if not self.is_authenticated():
            self.logger.error("Not authenticated with MusicBrainz")
            return {"success": False, "error": "Not authenticated"}
        
        try:
            # Make sure we're fully authenticated before trying to create
            if not self.authenticate(silent=True):
                self.logger.error("Failed to re-authenticate before creating collection")
                return {"success": False, "error": "Authentication refresh failed"}
            
            # Prepare the API endpoint and data
            url = "https://musicbrainz.org/ws/2/collection"
            
            # Set proper headers for JSON data
            headers = {
                "User-Agent": self.user_agent,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Prepare the request data - only send required fields
            data = {
                "name": name,
                "entity_type": entity_type
            }
            
            # Make the request to create a collection
            response = self.session.post(url, json=data, headers=headers)
            
            # Process the response
            if response.status_code in [200, 201]:
                try:
                    result_data = response.json()
                    collection_id = result_data.get("id")
                    
                    self.logger.info(f"Successfully created collection '{name}' with ID {collection_id}")
                    
                    return {
                        "success": True,
                        "id": collection_id,
                        "name": name,
                        "type": entity_type
                    }
                except Exception as e:
                    self.logger.error(f"Error parsing successful response: {e}")
                    return {
                        "success": True,
                        "error": "Created but failed to parse response",
                        "response_code": response.status_code,
                        "response_text": response.text[:100]
                    }
            elif response.status_code == 401:
                self.logger.error("Authentication error when creating collection")
                return {"success": False, "error": "Authentication error", "status_code": 401}
            else:
                self.logger.error(f"API error: {response.status_code} - {response.text}")
                return {
                    "success": False, 
                    "error": f"API error: {response.status_code}", 
                    "response_text": response.text[:200]
                }
        
        except Exception as e:
            self.logger.error(f"Error creating collection: {e}", exc_info=True)
            return {"success": False, "error": str(e)}





# musicbrainzngs

    def authenticate_with_musicbrainzngs(self, username=None, password=None, silent=False):
        """
        Autenticar con MusicBrainz usando la biblioteca musicbrainzngs
        
        Args:
            username (str, optional): Nombre de usuario MusicBrainz (sobreescribe atributo de instancia)
            password (str, optional): Contraseña MusicBrainz (sobreescribe atributo de instancia)
            silent (bool): Si se deben suprimir interacciones de UI
                
        Returns:
            bool: Si la autenticación fue exitosa
        """
        # Actualizar credenciales si se proporcionan
        if username:
            self.username = username
        if password:
            self.password = password
            
        # Verificar si tenemos credenciales
        if not self.username or not self.password:
            self.logger.error("No se puede autenticar: username o password no proporcionados")
            return False
        
        try:
            # Importar musicbrainzngs
            import musicbrainzngs
            
            # Configurar el agente de usuario
            musicbrainzngs.set_useragent(
                app=self.app_name,
                version=self.app_version,
                contact="user@example.com"  # Reemplaza con una dirección de contacto real
            )
            
            # Autenticar
            musicbrainzngs.auth(self.username, self.password)
            
            # Almacenar la instancia para usarla en otras funciones
            self.mb_ngs = musicbrainzngs
            
            # Probar si la autenticación fue exitosa
            try:
                # Intentar obtener las colecciones del usuario (requiere autenticación)
                collections = musicbrainzngs.get_collections()
                self.logger.info(f"Autenticación exitosa con musicbrainzngs")
                return True
            except musicbrainzngs.AuthenticationError:
                self.logger.error("Error de autenticación con musicbrainzngs")
                return False
            except Exception as e:
                self.logger.error(f"Error al verificar autenticación: {e}")
                return False
                
        except ImportError:
            self.logger.error("Módulo musicbrainzngs no encontrado. Instalándolo automáticamente...")
            try:
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "musicbrainzngs"])
                
                # Intentar nuevamente después de instalar
                import musicbrainzngs
                musicbrainzngs.set_useragent(self.app_name, self.app_version, "user@example.com")
                musicbrainzngs.auth(self.username, self.password)
                self.mb_ngs = musicbrainzngs
                
                try:
                    collections = musicbrainzngs.get_collections()
                    self.logger.info(f"Autenticación exitosa con musicbrainzngs después de instalar")
                    return True
                except:
                    self.logger.error("Error de autenticación después de instalar musicbrainzngs")
                    return False
            except Exception as e:
                self.logger.error(f"Error al instalar musicbrainzngs: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Error al autenticar con musicbrainzngs: {e}")
            return False


    def get_collections_with_ngs(self):
        """
        Obtener todas las colecciones del usuario usando musicbrainzngs
        
        Returns:
            list: Lista de diccionarios con información de colecciones
        """
        if not hasattr(self, 'mb_ngs'):
            if not self.authenticate_with_musicbrainzngs(silent=True):
                self.logger.error("No se pudo autenticar con musicbrainzngs")
                return []
        
        try:
            # Obtener colecciones usando musicbrainzngs
            collections_data = self.mb_ngs.get_collections()
            
            # Procesar las colecciones al formato esperado
            collections = []
            
            for collection in collections_data.get('collection-list', []):
                collection_info = {
                    'id': collection.get('id'),
                    'name': collection.get('name', 'Colección sin nombre'),
                    'entity_count': collection.get('release-count', 0),
                    'type': collection.get('entity-type', 'release')
                }
                collections.append(collection_info)
                
            self.logger.info(f"Se encontraron {len(collections)} colecciones con musicbrainzngs")
            return collections
        except Exception as e:
            self.logger.error(f"Error al obtener colecciones con musicbrainzngs: {e}")
            return []


    def get_collection_contents_ngs(self, collection_id, entity_type="release"):
        """
        Obtener el contenido de una colección de MusicBrainz usando musicbrainzngs
        
        Args:
            collection_id (str): ID de la colección
            entity_type (str): Tipo de entidad en la colección (release, artist, etc.)
                
        Returns:
            list: Lista de entidades en la colección
        """
        if not hasattr(self, 'mb_ngs'):
            if not self.authenticate_with_musicbrainzngs(silent=True):
                self.logger.error("No autenticado con MusicBrainz")
                return []
        
        try:
            # Obtener contenido de colección directamente
            result = self.mb_ngs.get_releases_in_collection(collection_id)
            
            # Procesar resultados
            releases = []
            release_list = result.get('collection', {}).get('release-list', [])
            
            for release in release_list:
                processed_release = {
                    'mbid': release.get('id', ''),
                    'title': release.get('title', 'Título Desconocido'),
                    'artist': "",
                    'artist_mbid': "",
                    'type': "",
                    'date': release.get('date', ''),
                    'status': release.get('status', ''),
                    'country': release.get('country', '')
                }
                
                # Extraer tipo del grupo de release (si existe)
                if 'release-group' in release:
                    processed_release['type'] = release['release-group'].get('primary-type', '')
                
                # Procesar información de artistas
                if 'artist-credit' in release:
                    artist_credits = release['artist-credit']
                    
                    artist_names = []
                    artist_mbids = []
                    
                    for credit in artist_credits:
                        if 'artist' in credit:
                            artist = credit['artist']
                            artist_names.append(artist.get('name', ''))
                            artist_mbids.append(artist.get('id', ''))
                        elif 'name' in credit:
                            artist_names.append(credit['name'])
                    
                    processed_release['artist'] = " ".join(filter(None, artist_names))
                    if artist_mbids:
                        processed_release['artist_mbid'] = artist_mbids[0]
                
                releases.append(processed_release)
            
            return releases
                
        except Exception as e:
            self.logger.error(f"Error obteniendo contenido de colección: {e}")
            return []


    def add_releases_to_collection_ngs(self, collection_id, release_mbids):
        """
        Añadir releases a una colección de MusicBrainz usando musicbrainzngs
        
        Args:
            collection_id (str): ID de la colección
            release_mbids (list): Lista de IDs de MusicBrainz de releases para añadir
                
        Returns:
            dict: Resultado con estado de éxito y detalles
        """
        if not hasattr(self, 'mb_ngs'):
            if not self.authenticate_with_musicbrainzngs(silent=True):
                self.logger.error("No se pudo autenticar con musicbrainzngs")
                return {"success": False, "error": "No autenticado"}
        
        try:
            # Tamaño de lote más pequeño para reducir errores
            batch_size = 20
            results = {
                "success": False,
                "total": len(release_mbids),
                "added": 0,
                "failed_batches": []
            }
            
            for i in range(0, len(release_mbids), batch_size):
                batch = release_mbids[i:i+batch_size]
                batch_idx = i // batch_size + 1
                
                try:
                    # Añadir releases a la colección
                    for release_id in batch:
                        self.mb_ngs.add_releases_to_collection(collection_id, [release_id])
                        results["added"] += 1
                        
                    self.logger.info(f"Añadido con éxito el lote {batch_idx} ({len(batch)} releases)")
                except self.mb_ngs.AuthenticationError:
                    self.logger.warning(f"Falló la autenticación para el lote {batch_idx}, intentando reautenticar")
                    results["failed_batches"].append(batch_idx)
                    
                    # Intentar reautenticar y continuar
                    if self.authenticate_with_musicbrainzngs(silent=True):
                        self.logger.info("Reautenticación exitosa, continuando con el siguiente lote")
                    else:
                        self.logger.error("Falló la reautenticación, deteniendo el procesamiento por lotes")
                        results["error"] = "Falló la autenticación durante el procesamiento"
                        break
                except Exception as e:
                    self.logger.error(f"Error añadiendo lote {batch_idx}: {e}")
                    results["failed_batches"].append(batch_idx)
                    results["error"] = f"Error de API: {str(e)}"
                
                # Añadir un pequeño retraso entre lotes para evitar límites de tasa
                import time
                time.sleep(0.5)
            
            # Actualizar bandera de éxito basado en resultados
            results["success"] = results["added"] > 0
            
            return results
                
        except Exception as e:
            self.logger.error(f"Error añadiendo releases a la colección: {e}")
            return {"success": False, "error": str(e), "added": 0, "total": len(release_mbids)}


    # def add_selected_albums_to_collection(self, collection_id, collection_name):
    #     """
    #     Añadir álbumes desde albums_selected.json a una colección de MusicBrainz usando musicbrainzngs
        
    #     Args:
    #         collection_id (str): ID de la colección a la que añadir álbumes
    #         collection_name (str): Nombre de la colección para mostrar
    #     """
    #     import os
    #     import json
    #     from PyQt6.QtWidgets import QMessageBox, QApplication
        
    #     # Intentar autenticar primero
    #     if not hasattr(self.musicbrainz_auth, 'mb_ngs'):
    #         self.logger.info("Autenticando con musicbrainzngs...")
    #         self.ui_callback.clear()
    #         self.ui_callback.show()
    #         self.ui_callback.append("Autenticando con MusicBrainz usando musicbrainzngs...")
    #         QApplication.processEvents()
            
    #         if not self.musicbrainz_auth.authenticate_with_musicbrainzngs(silent=True):
    #             reply = QMessageBox.question(
    #                 self.parent,
    #                 "Se requiere autenticación",
    #                 "Se requiere autenticación de MusicBrainz para añadir álbumes a colecciones. ¿Desea iniciar sesión ahora?",
    #                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    #             )
                
    #             if reply == QMessageBox.StandardButton.Yes:
    #                 username, ok = QInputDialog.getText(
    #                     self.parent,
    #                     "Autenticación MusicBrainz",
    #                     "Introduzca su nombre de usuario MusicBrainz:",
    #                     QLineEdit.EchoMode.Normal,
    #                     self.musicbrainz_username or ""
    #                 )
                    
    #                 if not ok or not username:
    #                     return
                    
    #                 password, ok = QInputDialog.getText(
    #                     self.parent,
    #                     "Autenticación MusicBrainz",
    #                     f"Introduzca contraseña para el usuario MusicBrainz {username}:",
    #                     QLineEdit.EchoMode.Password
    #                 )
                    
    #                 if not ok or not password:
    #                     return
                    
    #                 self.musicbrainz_username = username
    #                 self.musicbrainz_password = password
                    
    #                 if not self.musicbrainz_auth.authenticate_with_musicbrainzngs(username, password):
    #                     QMessageBox.warning(self.parent, "Error", "No se pudo autenticar con MusicBrainz")
    #                     return
    #             else:
    #                 return
        
    #     # Ruta al archivo JSON
    #     json_path = os.path.join(self.project_root, ".content", "cache", "albums_selected.json")
        
    #     # Verificar si existe el archivo
    #     if not os.path.exists(json_path):
    #         QMessageBox.warning(self.parent, "Error", "No se encontró el archivo de álbumes seleccionados. Por favor, cargue álbumes primero.")
    #         return
        
    #     # Cargar álbumes desde JSON
    #     try:
    #         with open(json_path, 'r', encoding='utf-8') as f:
    #             albums_data = json.load(f)
                
    #         if not albums_data:
    #             QMessageBox.warning(self.parent, "Error", "No se encontraron álbumes en el archivo de selección.")
    #             return
    #     except Exception as e:
    #         QMessageBox.warning(self.parent, "Error", f"Error al cargar álbumes seleccionados: {str(e)}")
    #         return
        
    #     # Función para añadir álbumes con diálogo de progreso
    #     def add_albums_to_collection(update_progress):
    #         # Preparar lista de MBIDs
    #         album_mbids = []
    #         valid_albums = []
            
    #         update_progress(0, 3, "Preparando datos de álbumes...", indeterminate=True)
            
    #         # Extraer MBIDs de los datos de álbumes
    #         for album in albums_data:
    #             mbid = album.get('mbid')
    #             if mbid and len(mbid) == 36 and mbid.count('-') == 4:
    #                 album_mbids.append(mbid)
    #                 valid_albums.append(album)
            
    #         if not album_mbids:
    #             return {
    #                 "success": False,
    #                 "error": "No se encontraron IDs de MusicBrainz válidos en los álbumes seleccionados"
    #             }
            
    #         update_progress(1, 3, f"Añadiendo {len(album_mbids)} álbumes a la colección...", indeterminate=True)
            
    #         # Usar el método add_releases_to_collection_ngs mejorado
    #         result = self.musicbrainz_auth.add_releases_to_collection_ngs(collection_id, album_mbids)
            
    #         update_progress(3, 3, "Finalizando...", indeterminate=True)
            
    #         return result
        
    #     # Ejecutar con diálogo de progreso
    #     result = self.parent.show_progress_operation(
    #         add_albums_to_collection,
    #         title=f"Añadiendo a Colección: {collection_name}",
    #         label_format="{status}"
    #     )
        
    #     # Procesar resultados
    #     if result and result.get("success"):
    #         success_count = result.get("added", 0)
    #         total = result.get("total", 0)
    #         failed_batches = result.get("failed_batches", [])
            
    #         if failed_batches:
    #             message = (f"Se añadieron {success_count} de {total} álbumes a la colección '{collection_name}'.\n\n"
    #                     f"Algunos lotes fallaron: {', '.join(map(str, failed_batches))}.\n"
    #                     "Esto puede deberse a problemas de permisos o a que algunos álbumes ya estén en la colección.")
    #             QMessageBox.warning(self.parent, "Éxito Parcial", message)
    #         else:
    #             QMessageBox.information(
    #                 self.parent, 
    #                 "Éxito", 
    #                 f"Se añadieron con éxito {success_count} álbumes a la colección '{collection_name}'"
    #             )
            
    #         # Ofrecer mostrar la colección
    #         reply = QMessageBox.question(
    #             self.parent,
    #             "Ver Colección",
    #             f"¿Desea ver la colección actualizada '{collection_name}'?",
    #             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    #         )
            
    #         if reply == QMessageBox.StandardButton.Yes:
    #             self.show_musicbrainz_collection(collection_id, collection_name)
    #     else:
    #         error_msg = result.get("error", "Error desconocido") if result else "La operación falló"
    #         QMessageBox.warning(self.parent, "Error", f"No se pudieron añadir álbumes a la colección: {error_msg}")


    def get_collection_contents_ngs(self, collection_id, entity_type="release"):
        """
        Obtener el contenido de una colección de MusicBrainz usando musicbrainzngs
        
        Args:
            collection_id (str): ID de la colección
            entity_type (str): Tipo de entidad en la colección (release, artist, etc.)
                
        Returns:
            list: Lista de entidades en la colección
        """
        if not hasattr(self, 'mb_ngs'):
            if not self.authenticate_with_musicbrainzngs(silent=True):
                self.logger.error("No autenticado con MusicBrainz")
                return []
        
        try:
            # Obtener contenido de colección directamente
            result = self.mb_ngs.get_releases_in_collection(collection_id)
            
            # Procesar resultados
            releases = []
            release_list = result.get('collection', {}).get('release-list', [])
            
            for release in release_list:
                processed_release = {
                    'mbid': release.get('id', ''),
                    'title': release.get('title', 'Título Desconocido'),
                    'artist': "",
                    'artist_mbid': "",
                    'type': "",
                    'date': release.get('date', ''),
                    'status': release.get('status', ''),
                    'country': release.get('country', '')
                }
                
                # Extraer tipo del grupo de release (si existe)
                if 'release-group' in release:
                    processed_release['type'] = release['release-group'].get('primary-type', '')
                
                # Procesar información de artistas
                if 'artist-credit' in release:
                    artist_credits = release['artist-credit']
                    
                    artist_names = []
                    artist_mbids = []
                    
                    for credit in artist_credits:
                        if 'artist' in credit:
                            artist = credit['artist']
                            artist_names.append(artist.get('name', ''))
                            artist_mbids.append(artist.get('id', ''))
                        elif 'name' in credit:
                            artist_names.append(credit['name'])
                    
                    processed_release['artist'] = " ".join(filter(None, artist_names))
                    if artist_mbids:
                        processed_release['artist_mbid'] = artist_mbids[0]
                
                releases.append(processed_release)
            
            return releases
                
        except Exception as e:
            self.logger.error(f"Error obteniendo contenido de colección: {e}")
            return []


