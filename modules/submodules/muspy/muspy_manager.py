# submodules/muspy/auth_manager.py
import os
import json
import requests
import logging
import subprocess

from PyQt6.QtWidgets import (QMessageBox, QApplication)

class MuspyAuthManager:
    def __init__(self,
                parent, 
                project_root, 
                muspy_username=None,
                muspy_api_key=None, 
                muspy_password=None, 
                muspy_id=None, 
                ui_callback=None,
                display_manager=None,
                spotify_client_id: str='',
                spotify_client_secret: str='',
                spotify_redirect_uri: str='',
                musicbrainz_username=None,
                musicbrainz_password=None,
                lastfm_api_key=None,
                lastfm_api_secret=None,
                lastfm_username=None,

                ):
        self.parent = parent
        self.project_root = project_root
        self.muspy_username = muspy_username
        self.muspy_api_key = muspy_api_key
        self.muspy_password = muspy_password
        self.muspy_id = muspy_id
        #self.logger = logging.getLogger(__name__)
        self.logger = self.parent.logger
        self.base_url = "https://muspy.com/api/1"
        self.ui_callback = ui_callback or UICallback(None)
        self.display_manager = display_manager
        
        #spotify
        self.spotify_client_id = spotify_client_id,
        self.spotify_client_secret = spotify_client_secret
        self.spotify_redirect_uri = spotify_redirect_uri

        #lastfm
        self.lastfm_api_key = lastfm_api_key,
        self.lastfm_api_secret = lastfm_api_secret,
        self.lastfm_username = lastfm_username,

        #musicbrainz
        self.musicbrainz_username=None
        self.musicbrainz_password=None

    def get_muspy_id(self):
        """
        Returns the Muspy ID, using the one from config and only fetching if not available
        
        Returns:
            str: ID de usuario de Muspy
        """
        # Si ya tenemos un ID, usarlo
        if self.muspy_id:
            self.logger.debug(f"Using existing Muspy ID: {self.muspy_id}")
            return self.muspy_id
            
        # Si no está disponible y tenemos credenciales, intentar obtenerlo
        if not self.muspy_id and self.muspy_username and self.muspy_api_key:
            try:
                self.logger.info("No Muspy ID in config, attempting to fetch from API")
                # Using the /user endpoint to get user info
                url = f"{self.base_url}/user"
                auth = (self.muspy_username, self.muspy_api_key)
                
                response = requests.get(url, auth=auth)
                
                if response.status_code == 200:
                    # Try to parse user_id from response
                    user_data = response.json()
                    if 'userid' in user_data:
                        self.muspy_id = user_data['userid']
                        self.logger.info(f"Muspy ID obtained: {self.muspy_id}")
                        return self.muspy_id
                    else:
                        self.logger.error(f"No 'userid' in response JSON: {user_data}")
                else:
                    self.logger.error(f"Error calling Muspy API: {response.status_code} - {response.text}")
            except Exception as e:
                self.logger.error(f"Error getting Muspy ID: {e}", exc_info=True)
        
        # Si todavía no tenemos un ID, registrar el error
        if not self.muspy_id:
            self.logger.error("No valid Muspy ID available. Please set it in configuration.")
        
        return self.muspy_id




    def get_mbid_artist_searched(self, artist_name):
        """
        Retrieve the MusicBrainz ID for a given artist
        
        Args:
            artist_name (str): Name of the artist to search
        
        Returns:
            str or None: MusicBrainz ID of the artist
        """
        if artist_name is None:
            return None
        
        try:
            # First attempt: query existing database
            if self.parent.query_db_script_path:
                # Add full absolute paths
                full_db_path = os.path.expanduser(self.parent.db_path) if self.parent.db_path else None
                full_script_path = os.path.expanduser(self.parent.query_db_script_path)
                
                # Log the search
                self.ui_callback.append(f"Searching for MBID for {artist_name}...")
                self.logger.debug(f"Script Path: {full_script_path}")
                self.logger.debug(f"DB Path: {full_db_path}")
                self.logger.debug(f"Artist: {artist_name}")

                # Try to find the artist in the database
                mbid_result = subprocess.run(
                    ['python', full_script_path, "--db", full_db_path, "--artist", artist_name, "--mbid"], 
                    capture_output=True, 
                    text=True
                )
                
                # Check if the output contains an error message
                if mbid_result.returncode == 0 and mbid_result.stdout.strip():
                    # Clean the result
                    mbid = mbid_result.stdout.strip().strip('"\'')
                    # Verify that the MBID looks valid (should be a UUID)
                    if len(mbid) == 36 and mbid.count('-') == 4:
                        self.logger.debug(f"MBID found in database: {mbid}")
                        return mbid
                
                # If we didn't find the MBID in the database, try searching MusicBrainz directly
                self.ui_callback.append(f"Searching MusicBrainz for {artist_name}...")
                QApplication.processEvents()
                
                # Use the MusicBrainz API directly
                try:
                    import requests
                    url = "https://musicbrainz.org/ws/2/artist/"
                    params = {
                        "query": f"artist:{artist_name}",
                        "fmt": "json"
                    }
                    headers = {
                        "User-Agent": "MuspyReleasesModule/1.0"
                    }
                    
                    response = requests.get(url, params=params, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "artists" in data and data["artists"]:
                            # Get the first artist result
                            artist = data["artists"][0]
                            mbid = artist.get("id")
                            
                            if mbid and len(mbid) == 36 and mbid.count('-') == 4:
                                self.ui_callback.append(f"MBID found on MusicBrainz: {mbid}")
                                return mbid
                except Exception as e:
                    self.logger.error(f"Error searching MusicBrainz API: {e}")
            
            self.ui_callback.append(f"Could not find MBID for {artist_name}")
            return None
        
        except Exception as e:
            self.ui_callback.append(f"Error searching for MBID: {e}")
            self.logger.error(f"Error getting MBID for {artist_name}: {e}", exc_info=True)
            return None
 




    def add_artist_to_muspy(self, mbid=None, artist_name=None):
        """
        Add/Follow an artist to Muspy using their MBID - fixed to match working curl pattern
        
        Args:
            mbid (str, optional): MusicBrainz ID of the artist
            artist_name (str, optional): Name of the artist for logging
        
        Returns:
            bool: True if artist was successfully added, False otherwise
        """
        if not self.muspy_username or not self.muspy_api_key:
            self.logger.error("Muspy credentials not configured")
            return False

        if not mbid:
            self.logger.error(f"No MBID provided for {artist_name or 'Unknown'}")
            return False

        # Ensure muspy_id is available
        if not self.muspy_id:
            self.get_muspy_id()
            if not self.muspy_id:
                self.logger.error("Could not get Muspy ID")
                return False

        try:
            # Use exactly the same URL format as in the working curl command
            url = f"https://muspy.com/api/1/artists/{self.muspy_id}/{mbid}"
            
            # Use the same authentication method
            auth = (self.muspy_username, self.muspy_password)
            
            # Use a PUT request with no body, exactly like the curl command
            response = requests.put(url, auth=auth)
            
            # Log detailed information for debugging
            self.logger.debug(f"PUT request to {url}")
            self.logger.debug(f"Using auth: {self.muspy_username}:***")
            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response text: {response.text}")
            
            if response.status_code in [200, 201]:
                self.logger.info(f"Successfully added {artist_name or mbid} to Muspy")
                return True
            else:
                self.logger.error(f"Error adding artist to Muspy: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Exception adding artist to Muspy: {e}", exc_info=True)
            return False






    def add_artist_to_muspy_silent(self, mbid, artist_name=None):
        """
        Add artist to Muspy without showing dialog boxes
        
        Args:
            mbid (str): MusicBrainz ID of the artist
            artist_name (str, optional): Name of the artist for logging
        
        Returns:
            int: 1 for success, 0 for already exists, -1 for error
        """
        if not self.muspy_username or not self.muspy_api_key or not self.muspy_id:
            return -1

        try:
            # Use the same URL format as the working curl command
            url = f"https://muspy.com/api/1/artists/{self.muspy_id}/{mbid}"
            auth = (self.muspy_username, self.muspy_password)
            
            # Check if artist already exists first
            check_response = requests.get(url, auth=auth)
            
            # If status code is 200, artist already exists
            if check_response.status_code == 200:
                return 0  # Already exists
            
            # Otherwise, add the artist
            response = requests.put(url, auth=auth)
            
            if response.status_code in [200, 201]:
                return 1  # Success
            else:
                self.logger.error(f"Error adding artist {artist_name or mbid} to Muspy: {response.status_code} - {response.text}")
                return -1  # Error
        except Exception as e:
            self.logger.error(f"Error adding artist {artist_name or mbid} to Muspy: {e}")
            return -1  # Error



    def unfollow_artist_from_muspy(self, mbid, artist_name=None):
        """
        Unfollow an artist from Muspy using the DELETE API endpoint
        
        Args:
            mbid (str): MusicBrainz ID of the artist to unfollow
            artist_name (str, optional): Artist name for display purposes
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.muspy_username or not self.muspy_api_key or not self.muspy_id:
            self.logger.error("Muspy credentials not configured")
            return False

        try:
            # Use the DELETE endpoint as specified in the API docs
            url = f"{self.base_url}/artists/{self.muspy_id}/{mbid}"
            auth = (self.muspy_username, self.muspy_api_key)
            
            # Make the DELETE request
            response = requests.delete(url, auth=auth)
            
            # Log response details for debugging
            self.logger.debug(f"DELETE request to {url}")
            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response text: {response.text}")
            
            if response.status_code in [200, 204]:
                artist_display = artist_name or mbid
                self.logger.info(f"Successfully unfollowed {artist_display} from Muspy")
                return True
            else:
                self.logger.error(f"Error unfollowing artist from Muspy: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Exception unfollowing artist from Muspy: {e}", exc_info=True)
            return False




    def unfollow_artist_from_muspy_with_confirm(self, mbid, artist_name):
        """Show confirmation dialog before unfollowing an artist from Muspy"""
        reply = QMessageBox.question(
            self.parent,
            "Confirm Unfollow",
            f"Are you sure you want to unfollow '{artist_name}' from Muspy?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.unfollow_artist_from_muspy(mbid, artist_name)
            
            if success:
                QMessageBox.information(self.parent, "Success", f"Successfully unfollowed {artist_name} from Muspy")
            else:
                QMessageBox.warning(self.parent, "Error", f"Failed to unfollow {artist_name} from Muspy")




    def follow_artist_from_name(self, artist_name):
        """Follow artist by searching for their MBID first"""
        if not artist_name or isinstance(artist_name, dict):
            # Si es un diccionario, intentamos extraer el nombre
            if isinstance(artist_name, dict) and 'artist_name' in artist_name:
                artist_name = artist_name['artist_name']
            else:
                QMessageBox.warning(self.parent, "Error", "No se pudo obtener el nombre del artista")
                return
        
        # First get the MBID
        mbid = self.get_mbid_artist_searched(artist_name)
        
        if mbid:
            # Store current artist
            self.current_artist = {"name": artist_name, "mbid": mbid}
            
            # Follow the artist
            success = self.add_artist_to_muspy(mbid, artist_name)
            
            if success:
                QMessageBox.information(self.parent, "Success", f"Now following {artist_name} on Muspy")
            else:
                QMessageBox.warning(self.parent, "Error", f"Could not follow {artist_name} on Muspy")
        else:
            QMessageBox.warning(self.parent, "Error", f"Could not find MBID for {artist_name}")



    def check_api_credentials(self):
        """
        Check and display the status of API credentials for debugging
        """
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        
        self.ui_callback.append("API Credentials Status:\n")
        
        # Check Muspy credentials
        self.ui_callback.append("Muspy Credentials:")
        if self.muspy_username and self.muspy_api_key:
            self.ui_callback.append(f"  Username: {self.muspy_username}")
            self.ui_callback.append(f"  API Key: {'*' * len(self.muspy_api_key) if self.muspy_api_key else 'Not configured'}")
            self.ui_callback.append(f"  Muspy ID: {self.muspy_id or 'Not detected'}")
            self.ui_callback.append("  Status: Configured")
        else:
            self.ui_callback.append("  Status: Not fully configured")
        
        # Check Spotify credentials
        self.ui_callback.append("\nSpotify Credentials:")
        if self.spotify_client_id and self.spotify_client_secret:
            self.ui_callback.append(f"  Client ID: {self.spotify_client_id[:5]}...{self.spotify_client_id[-5:] if len(self.spotify_client_id) > 10 else ''}")
            self.ui_callback.append(f"  Client Secret: {'*' * 10}")
            self.ui_callback.append("  Status: Configured")
            
            # Test authentication if credentials are available
            if hasattr(self, 'spotify_auth') and self.spotify_auth:
                is_auth = self.spotify_auth.is_authenticated()
                self.ui_callback.append(f"  Authentication: {'Successful' if is_auth else 'Failed or not attempted'}")
        else:
            self.ui_callback.append("  Status: Not fully configured")
        
        # Check Last.fm credentials
        self.ui_callback.append("\nLast.fm Credentials:")
        if self.lastfm_api_key and self.lastfm_username:
            self.ui_callback.append(f"  API Key: {self.lastfm_api_key[:5]}...{self.lastfm_api_key[-5:] if len(self.lastfm_api_key) > 10 else ''}")
            self.ui_callback.append(f"  Username: {self.lastfm_username}")
            self.ui_callback.append("  Status: Configured")
            
            # Test authentication if LastFM auth manager exists
            if hasattr(self, 'lastfm_auth'):
                is_auth = self.lastfm_auth.is_authenticated()
                self.ui_callback.append(f"  Authentication: {'Successful' if is_auth else 'Not authenticated for write operations'}")
        else:
            self.ui_callback.append("  Status: Not fully configured")
        
        self.ui_callback.append("\nTo test connections, use the sync menu options.")
    