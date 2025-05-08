import os
import json
import time
import threading
import urllib.parse
import requests
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu, QProgressDialog, QApplication, QMessageBox, QPushButton, QSlider, QSpinBox
from PyQt6.QtGui import QIcon

from modules.submodules.url_playlist.ui_helpers import get_service_priority
# Asegurarse de que PROJECT_ROOT está disponible
try:
    from base_module import PROJECT_ROOT
except ImportError:
    import os
    PROJECT_ROOT = os.path.abspath(Path(os.path.dirname(__file__), "..", ".."))

def setup_lastfm_menu_items(parent_instance, menu):
    """Set up Last.fm menu items in any menu"""
    try:
        # Add "Sync Scrobbles" option
        sync_action = menu.addAction(QIcon(":/services/refresh"), "Sincronizar scrobbles")
        sync_action.triggered.connect(lambda: sync_lastfm_scrobbles(parent_instance))
        
        menu.addSeparator()
        
        # Add "Latest" submenu
        latest_menu = menu.addMenu(QIcon(":/services/lastfm"), "Últimos")
        last_week = latest_menu.addAction("Última semana")
        last_week.triggered.connect(lambda: load_lastfm_scrobbles_period(parent_instance, "week"))
        
        last_month = latest_menu.addAction("Último mes")
        last_month.triggered.connect(lambda: load_lastfm_scrobbles_period(parent_instance, "month"))
        
        last_year = latest_menu.addAction("Último año")
        last_year.triggered.connect(lambda: load_lastfm_scrobbles_period(parent_instance, "year"))
        
        # Add "Months" submenu (will be populated dynamically later)
        months_menu = menu.addMenu(QIcon(":/services/calendar"), "Meses")
        
        # Add "Years" submenu (will be populated dynamically later)
        years_menu = menu.addMenu(QIcon(":/services/calendar"), "Años")
        
        return {
            'months_menu': months_menu,
            'years_menu': years_menu
        }
    except Exception as e:
        print(f"Error setting up Last.fm menu items: {str(e)}")
        return {}

def get_lastfm_cache_path():
    """Get the path to the Last.fm scrobbles cache file"""
    cache_dir = Path(PROJECT_ROOT, ".content", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return Path(cache_dir, "lastfm_scrobbles.json")

def sync_lastfm_scrobbles(self):
    """Synchronize Last.fm scrobbles and store them in a cache file"""
    try:
        # Check if we have valid configuration
        if not self.lastfm_api_key:
            self.log("Error: Last.fm API key not configured")
            QMessageBox.warning(self, "Error", "Last.fm API key not configured. Check settings.")
            return False
                
        if not self.lastfm_user:
            self.log("Error: Last.fm username not configured")
            QMessageBox.warning(self, "Error", "Last.fm username not configured. Check settings.")
            return False
        
        # Show progress dialog
        progress = QProgressDialog("Syncing Last.fm scrobbles...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Last.fm Sync")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        QApplication.processEvents()
        
        # Determine cache file path
        cache_file = get_lastfm_cache_path()
        
        # Load existing cache if available
        scrobbles_data = {
            "last_updated": 0,
            "scrobbles": []
        }
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    scrobbles_data = json.load(f)
                    self.log(f"Loaded {len(scrobbles_data.get('scrobbles', []))} cached scrobbles")
                    progress.setValue(10)
            except Exception as e:
                self.log(f"Error loading scrobbles cache: {str(e)}")
                # Continue with empty cache
        
        # Get the timestamp of the last update
        last_updated = scrobbles_data.get("last_updated", 0)
        
        # Prepare for API requests
        all_new_scrobbles = []
        page = 1
        total_pages = 1
        
        # Update progress to 20%
        progress.setValue(20)
        
        while page <= total_pages:
            if progress.wasCanceled():
                break
                
            # Request parameters
            params = {
                'method': 'user.getrecenttracks',
                'user': self.lastfm_user,
                'api_key': self.lastfm_api_key,
                'format': 'json',
                'limit': 200,  # Maximum allowed by Last.fm
                'page': page
            }
            
            # Add from_timestamp if we have a previous update
            if last_updated > 0:
                params['from'] = last_updated + 1  # +1 to avoid duplicates
            
            # Make the request
            try:
                url = f"https://ws.audioscrobbler.com/2.0/?{urllib.parse.urlencode(params)}"
                response = requests.get(url)
                data = response.json()
                
                if 'error' in data:
                    self.log(f"Last.fm API error: {data.get('message', 'Unknown error')}")
                    break
                
                # Get total pages if first request
                if page == 1:
                    recenttracks = data.get('recenttracks', {})
                    attr = recenttracks.get('@attr', {})
                    total_pages = int(attr.get('totalPages', '1'))
                    
                    self.log(f"Found {attr.get('total', '0')} new scrobbles across {total_pages} pages")
                
                # Process tracks
                tracks = data.get('recenttracks', {}).get('track', [])
                if not isinstance(tracks, list):
                    tracks = [tracks]  # Handle single track response
                
                for track in tracks:
                    # Skip 'now playing' tracks
                    if '@attr' in track and track['@attr'].get('nowplaying') == 'true':
                        continue
                        
                    # Create scrobble object
                    scrobble = {
                        'artist': track.get('artist', {}).get('#text', ''),
                        'title': track.get('name', ''),
                        'album': track.get('album', {}).get('#text', ''),
                        'timestamp': int(track.get('date', {}).get('uts', '0')),
                        'url': track.get('url', ''),
                        'image': track.get('image', [{}])[-1].get('#text', ''),  # Get largest image
                        'youtube_url': None  # Will be populated later
                    }
                    
                    all_new_scrobbles.append(scrobble)
                
                # Update progress
                progress_value = 20 + int(70 * (page / total_pages))
                progress.setValue(progress_value)
                
                # Next page
                page += 1
                
            except Exception as e:
                self.log(f"Error fetching scrobbles from Last.fm: {str(e)}")
                break
        
        # Update progress to 90%
        progress.setValue(90)
        
        # Merge new scrobbles with existing ones
        if all_new_scrobbles:
            # Sorting by timestamp (newest first)
            all_new_scrobbles.sort(key=lambda s: s['timestamp'], reverse=True)
            
            # Update last_updated timestamp
            newest_timestamp = all_new_scrobbles[0]['timestamp']
            if newest_timestamp > scrobbles_data['last_updated']:
                scrobbles_data['last_updated'] = newest_timestamp
            
            # Merge with existing scrobbles
            existing_scrobbles = scrobbles_data.get('scrobbles', [])
            
            # Create a set of existing timestamps for quick lookup
            existing_timestamps = {s['timestamp'] for s in existing_scrobbles}
            
            # Only add scrobbles with unique timestamps
            unique_new_scrobbles = [s for s in all_new_scrobbles if s['timestamp'] not in existing_timestamps]
            
            # Combine and sort all scrobbles
            all_scrobbles = existing_scrobbles + unique_new_scrobbles
            all_scrobbles.sort(key=lambda s: s['timestamp'], reverse=True)
            
            scrobbles_data['scrobbles'] = all_scrobbles
            
            # Save updated data
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(scrobbles_data, f, indent=2)
                
            self.log(f"Saved {len(all_scrobbles)} scrobbles to cache ({len(unique_new_scrobbles)} new)")
            
            # Start a background thread to fetch YouTube links
            if unique_new_scrobbles:
                self.log(f"Starting background thread to fetch YouTube links for {len(unique_new_scrobbles)} tracks")
                fetch_thread = threading.Thread(
                    target=fetch_youtube_links,
                    args=(self, unique_new_scrobbles, cache_file),
                    daemon=True
                )
                fetch_thread.start()
                
            # Populate the year/month menus
            populate_scrobbles_time_menus(self, all_scrobbles)
        
        # Complete progress
        progress.setValue(100)
        
        QMessageBox.information(
            self,
            "Sync Complete", 
            f"Synchronized Last.fm scrobbles for {self.lastfm_user}.\n\n" +
            f"Added {len(unique_new_scrobbles if 'unique_new_scrobbles' in locals() else [])} new scrobbles.\n" +
            f"Total scrobbles: {len(scrobbles_data.get('scrobbles', []))}"
        )
        
        return True
    except Exception as e:
        self.log(f"Error synchronizing Last.fm scrobbles: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        QMessageBox.warning(self, "Error", f"Error synchronizing Last.fm scrobbles: {str(e)}")
        return False

def fetch_youtube_links(self, scrobbles, cache_file):
    """Fetch URLs for scrobbles in a background thread, checking database first"""
    try:
        self.log(f"Starting link fetching for {len(scrobbles)} scrobbles")
        
        # Load the current cache
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
        except Exception as e:
            self.log(f"Error loading cache file for link updates: {str(e)}")
            return
        
        # Track scrobbles by a unique key for efficient updates
        all_scrobbles = cache_data.get('scrobbles', [])
        scrobbles_dict = {f"{s['artist']}|{s['title']}|{s['timestamp']}": s for s in all_scrobbles}
        
        # Get service priority from settings
        service_priority = get_service_priority(self)
        self.log(f"Service priority: {', '.join(service_priority)}")
        
        # Process each scrobble
        processed_count = 0
        updated_count = 0
        
        for scrobble in scrobbles:
            # Skip if already has a URL
            if any(scrobble.get(f'{service}_url') for service in service_priority):
                continue
                
            # Create a unique key
            key = f"{scrobble['artist']}|{scrobble['title']}|{scrobble['timestamp']}"
            
            # Try to get URL from database first
            links = get_track_links_from_db(self, scrobble['artist'], scrobble['title'], scrobble.get('album', ''))
            
            if links:
                # Check for each service in priority order
                for service in service_priority:
                    if service in links and links[service]:
                        # Update both the local scrobble and the cache dictionary
                        service_url_key = f'{service}_url'
                        scrobble[service_url_key] = links[service]
                        
                        if key in scrobbles_dict:
                            scrobbles_dict[key][service_url_key] = links[service]
                            updated_count += 1
                            
                            # Log successful link retrieval
                            self.log(f"Found {service} link for {scrobble['artist']} - {scrobble['title']} in database")
                            
                            # Once we have one service URL, we can skip to the next scrobble
                            break
            
            # If no links were found in the database, try fetching from Last.fm
            if not any(scrobble.get(f'{service}_url') for service in service_priority):
                try:
                    # Check if we have a Last.fm URL
                    lastfm_url = scrobble.get('url')
                    if lastfm_url:
                        # Use the extract_links_from_lastfm function
                        for service in service_priority:
                            service_url = extract_link_from_lastfm(self, lastfm_url, service)
                            
                            if service_url:
                                # Update both the local scrobble and the cache dictionary
                                service_url_key = f'{service}_url'
                                scrobble[service_url_key] = service_url
                                
                                if key in scrobbles_dict:
                                    scrobbles_dict[key][service_url_key] = service_url
                                    updated_count += 1
                                    
                                    # Log successful link retrieval
                                    self.log(f"Found {service} link for {scrobble['artist']} - {scrobble['title']} from Last.fm")
                                    
                                    # Once we have one service URL, we can skip to the next service
                                    break
                except Exception as e:
                    self.log(f"Error fetching links for {scrobble['artist']} - {scrobble['title']}: {str(e)}")
            
            # Update progress periodically
            processed_count += 1
            if processed_count % 20 == 0:
                self.log(f"Processed {processed_count}/{len(scrobbles)} scrobbles, found {updated_count} links")
                
                # Save intermediate results
                try:
                    # Rebuild the scrobbles list from the dictionary
                    cache_data['scrobbles'] = list(scrobbles_dict.values())
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache_data, f, indent=2)
                except Exception as e:
                    self.log(f"Error saving intermediate link updates: {str(e)}")
        
        # Final save
        try:
            # Rebuild the scrobbles list from the dictionary
            cache_data['scrobbles'] = list(scrobbles_dict.values())
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
                
            self.log(f"Link fetching complete. Updated {updated_count} scrobbles.")
        except Exception as e:
            self.log(f"Error saving final link updates: {str(e)}")
    
    except Exception as e:
        self.log(f"Error in link fetching thread: {str(e)}")
        import traceback
        self.log(traceback.format_exc())

def extract_link_from_lastfm(self, lastfm_url, service):
    """Extract service link from a Last.fm page"""
    try:
        # Check if we have BeautifulSoup
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            self.log("BeautifulSoup not installed, cannot extract links")
            return None
            
        # Make request to Last.fm page
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(lastfm_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
            
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Service-specific extractors
        if service == 'youtube':
            return extract_youtube_from_lastfm_soup(soup)
        elif service == 'spotify':
            return extract_spotify_from_lastfm_soup(soup)
        elif service == 'bandcamp':
            return extract_bandcamp_from_lastfm_soup(soup)
        elif service == 'soundcloud':
            return extract_soundcloud_from_lastfm_soup(soup)
        else:
            return None
            
    except Exception as e:
        self.log(f"Error extracting {service} link from Last.fm: {str(e)}")
        return None

def extract_youtube_from_lastfm_soup(soup):
    """Extract YouTube URL from a Last.fm page soup"""
    try:
        # Try different methods to find YouTube links
        
        # Method 1: Look for elements with data-youtube-id or data-youtube-url
        youtube_elements = soup.select('[data-youtube-id], [data-youtube-url]')
        for element in youtube_elements:
            if 'data-youtube-url' in element.attrs:
                return element['data-youtube-url']
            elif 'data-youtube-id' in element.attrs:
                return f"https://www.youtube.com/watch?v={element['data-youtube-id']}"
        
        # Method 2: Look for standard YouTube links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'youtube.com/watch' in href or 'youtu.be/' in href:
                return href
        
        return None
    except Exception as e:
        print(f"Error extracting YouTube from soup: {str(e)}")
        return None

def extract_spotify_from_lastfm_soup(soup):
    """Extract Spotify URL from a Last.fm page soup"""
    try:
        # Look for Spotify links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'open.spotify.com' in href:
                return href
        
        return None
    except Exception as e:
        print(f"Error extracting Spotify from soup: {str(e)}")
        return None

def extract_bandcamp_from_lastfm_soup(soup):
    """Extract Bandcamp URL from a Last.fm page soup"""
    try:
        # Look for Bandcamp links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'bandcamp.com' in href:
                return href
        
        return None
    except Exception as e:
        print(f"Error extracting Bandcamp from soup: {str(e)}")
        return None

def extract_soundcloud_from_lastfm_soup(soup):
    """Extract SoundCloud URL from a Last.fm page soup"""
    try:
        # Look for SoundCloud links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'soundcloud.com' in href:
                return href
        
        return None
    except Exception as e:
        print(f"Error extracting SoundCloud from soup: {str(e)}")
        return None

def load_lastfm_scrobbles_period(parent_instance, period):
    """Load Last.fm scrobbles for a specific time period"""
    try:
        # Determine cache file path
        cache_file = get_lastfm_cache_path()
        
        if not os.path.exists(cache_file):
            parent_instance.log(f"No cache file found for {parent_instance.lastfm_user}")
            QMessageBox.warning(parent_instance, "Error", f"No scrobbles data found for {parent_instance.lastfm_user}. Please sync first.")
            return False
        
        # Load the cache
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
                
        scrobbles = cache_data.get('scrobbles', [])
        
        if not scrobbles:
            parent_instance.log("No scrobbles found in cache")
            QMessageBox.information(parent_instance, "No Data", "No scrobbles found in cache. Please sync first.")
            return False
        
        # Determine time range
        current_time = int(time.time())
        start_time = 0
        title = ""

        if period == "week":
            start_time = current_time - (7 * 24 * 60 * 60)  # 7 days
            title = "Última semana"
        elif period == "month":
            start_time = current_time - (30 * 24 * 60 * 60)  # 30 days
            title = "Último mes"
        elif period == "year":
            start_time = current_time - (365 * 24 * 60 * 60)  # 365 days
            title = "Último año"
        
        # Filter scrobbles by time period
        filtered_scrobbles = [s for s in scrobbles if s['timestamp'] >= start_time]
        
        # Limit the number of scrobbles to display
        max_scrobbles = min(len(filtered_scrobbles), parent_instance.scrobbles_limit)
        display_scrobbles = filtered_scrobbles[:max_scrobbles]
        
        # Display in tree
        display_scrobbles_in_tree(parent_instance, display_scrobbles, title)
        
        return True
    except Exception as e:
        parent_instance.log(f"Error loading scrobbles for period {period}: {str(e)}")
        import traceback
        parent_instance.log(traceback.format_exc())
        return False

def load_lastfm_scrobbles_month(self, year, month):
    """Load Last.fm scrobbles for a specific year and month"""
    try:
        # Determine cache file path
        cache_file = get_lastfm_cache_path()
        
        if not os.path.exists(cache_file):
            self.log(f"No cache file found for {self.lastfm_user}")
            QMessageBox.warning(self, "Error", f"No scrobbles data found for {self.lastfm_user}. Please sync first.")
            return False
        
        # Load the cache
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
                
        scrobbles = cache_data.get('scrobbles', [])
        
        # Calculate start and end timestamps for the month
        if month == 12:
            end_year = year + 1
            end_month = 1
        else:
            end_year = year
            end_month = month + 1
            
        start = datetime(year, month, 1, 0, 0, 0).timestamp()
        end = datetime(end_year, end_month, 1, 0, 0, 0).timestamp()
        
        # Filter scrobbles for the month
        month_scrobbles = [s for s in scrobbles if start <= s['timestamp'] < end]
        
        # Get month name
        month_name = datetime(year, month, 1).strftime("%B")
        title = f"{month_name} {year}"
        
        # Limit the number of scrobbles to display
        max_scrobbles = min(len(month_scrobbles), self.scrobbles_limit)
        display_scrobbles = month_scrobbles[:max_scrobbles]
        
        # Display in tree
        display_scrobbles_in_tree(self, display_scrobbles, title)
        
        return True
    except Exception as e:
        self.log(f"Error loading scrobbles for {month}/{year}: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False

def load_lastfm_scrobbles_year(self, year):
    """Load Last.fm scrobbles for a specific year"""
    try:
        # Determine cache file path
        cache_file = get_lastfm_cache_path()
        
        if not os.path.exists(cache_file):
            self.log(f"No cache file found for {self.lastfm_user}")
            QMessageBox.warning(self, "Error", f"No scrobbles data found for {self.lastfm_user}. Please sync first.")
            return False
        
        # Load the cache
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
                
        scrobbles = cache_data.get('scrobbles', [])
        
        # Calculate start and end timestamps for the year
        start = datetime(year, 1, 1, 0, 0, 0).timestamp()
        end = datetime(year + 1, 1, 1, 0, 0, 0).timestamp()
        
        # Filter scrobbles for the year
        year_scrobbles = [s for s in scrobbles if start <= s['timestamp'] < end]
        
        # Limit the number of scrobbles to display
        max_scrobbles = min(len(year_scrobbles), self.scrobbles_limit)
        display_scrobbles = year_scrobbles[:max_scrobbles]
        
        # Display in tree
        display_scrobbles_in_tree(self, display_scrobbles, f"Año {year}")
        
        return True
    except Exception as e:
        self.log(f"Error loading scrobbles for year {year}: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False


def display_scrobbles_in_tree(parent_instance, scrobbles, title):
    """Display scrobbles in the tree widget"""
    try:
        # Clear the tree
        parent_instance.treeWidget.clear()
        
        # Get service priority for icon selection
        service_priority = get_service_priority(parent_instance)

        # Check if we need to reorganize by play count
        if not parent_instance.scrobbles_by_date:
            # Group by artist and title
            play_counts = {}
            for scrobble in scrobbles:
                key = f"{scrobble['artist']}|{scrobble['title']}"
                if key not in play_counts:
                    play_counts[key] = {
                        'artist': scrobble['artist'],
                        'title': scrobble['title'],
                        'album': scrobble['album'],
                        'youtube_url': scrobble.get('youtube_url'),
                        'count': 0,
                        'timestamps': []
                    }
                
                play_counts[key]['count'] += 1
                play_counts[key]['timestamps'].append(scrobble['timestamp'])
            
            # Convert to list and sort by play count
            sorted_tracks = sorted(
                play_counts.values(), 
                key=lambda x: x['count'], 
                reverse=True
            )
            
            # Create root item
            from PyQt6.QtWidgets import QTreeWidgetItem
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QIcon
            
            root_item = QTreeWidgetItem(parent_instance.treeWidget)
            root_item.setText(0, f"Top Tracks: {title}")
            root_item.setText(1, parent_instance.lastfm_user)
            root_item.setText(2, "Last.fm")
            
            # Format as bold
            font = root_item.font(0)
            font.setBold(True)
            root_item.setFont(0, font)
            
            # Add icon
            root_item.setIcon(0, QIcon(":/services/lastfm"))
            
            # Change column headers
            parent_instance.treeWidget.headerItem().setText(3, "Reproducciones")
            parent_instance.treeWidget.headerItem().setText(4, "Primer Play")
            
            # Add tracks
            for track in sorted_tracks[:parent_instance.scrobbles_limit]:
                track_item = QTreeWidgetItem(root_item)
                track_item.setText(0, track['title'])
                track_item.setText(1, track['artist'])
                track_item.setText(2, "Track")
                track_item.setText(3, str(track['count']))
                
                # Format first play date
                import time
                first_play = min(track['timestamps'])
                date_str = time.strftime("%Y-%m-%d", time.localtime(first_play))
                track_item.setText(4, date_str)
                
                # Store all available URLs
                track_data = {
                    'title': track['title'],
                    'artist': track['artist'],
                    'album': track['album'],
                    'type': 'track',
                    'source': 'lastfm'
                }
                
                # Add service URLs if available
                for service in service_priority:
                    service_url_key = f'{service}_url'
                    if service_url_key in track:
                        track_data[service_url_key] = track[service_url_key]
                
                track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
                
                # Set icon based on available URLs (use first available service in priority order)
                icon_set = False
                for service in service_priority:
                    service_url_key = f'{service}_url'
                    if service_url_key in track and track[service_url_key]:
                        track_item.setIcon(0, QIcon(f":/services/{service}"))
                        icon_set = True
                        break
                
                # Default to Last.fm icon if no other service icons available
                if not icon_set:
                    track_item.setIcon(0, QIcon(":/services/lastfm"))
        
        else:
            # Display chronologically (by date)
            from PyQt6.QtWidgets import QTreeWidgetItem
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QIcon
            import time
            
            # Create root item
            root_item = QTreeWidgetItem(parent_instance.treeWidget)
            root_item.setText(0, f"Scrobbles: {title}")
            root_item.setText(1, parent_instance.lastfm_user)
            root_item.setText(2, "Last.fm")
            
            # Format as bold
            font = root_item.font(0)
            font.setBold(True)
            root_item.setFont(0, font)
            
            # Add icon
            root_item.setIcon(0, QIcon(":/services/lastfm"))
            
            # Change column headers
            parent_instance.treeWidget.headerItem().setText(4, "Fecha")
            
            # Add tracks chronologically
            for scrobble in scrobbles:
                track_item = QTreeWidgetItem(root_item)
                track_item.setText(0, scrobble['title'])
                track_item.setText(1, scrobble['artist'])
                track_item.setText(2, "Track")
                
                if scrobble['album']:
                    track_item.setText(3, scrobble['album'])
                
                # Format date
                date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(scrobble['timestamp']))
                track_item.setText(4, date_str)
                
                # Store data for playback
                track_data = {
                    'title': scrobble['title'],
                    'artist': scrobble['artist'],
                    'album': scrobble['album'],
                    'type': 'track',
                    'source': 'lastfm',
                    'timestamp': scrobble['timestamp']
                }
                
                # Add service URLs if available
                for service in service_priority:
                    service_url_key = f'{service}_url'
                    if service_url_key in scrobble:
                        track_data[service_url_key] = scrobble[service_url_key]
                
                track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
                
                # Set icon based on available URLs
                icon_set = False
                for service in service_priority:
                    service_url_key = f'{service}_url'
                    if service_url_key in scrobble:
                        track_item.setIcon(0, QIcon(f":/services/{service}"))
                        icon_set = True
                        break
                
                # Default to Last.fm icon if no other service icons available
                if not icon_set:
                    track_item.setIcon(0, QIcon(":/services/lastfm"))
        
        # Expand root item
        root_item.setExpanded(True)
        
        # Log summary
        parent_instance.log(f"Displayed {len(scrobbles)} scrobbles for {title}")
        
        return True
    except Exception as e:
        parent_instance.log(f"Error displaying scrobbles: {str(e)}")
        import traceback
        parent_instance.log(traceback.format_exc())
        return False

def populate_scrobbles_time_menus(self, scrobbles):
    """Populate the year and month menus based on available scrobbles data"""
    try:
        if not scrobbles:
            return False
            
        # Get menu references
        menus_to_update = [
            # Main scrobbles button menus
            {'months': self.months_menu, 'years': self.years_menu},
            # Unified button menus
            {'months': getattr(self, 'unified_months_menu', None), 
            'years': getattr(self, 'unified_years_menu', None)}
        ]
        
        # Extract years and months from scrobbles
        years_dict = {}
        
        for scrobble in scrobbles:
            timestamp = scrobble['timestamp']
            date = time.localtime(timestamp)
            year = date.tm_year
            month = date.tm_mon
            
            if year not in years_dict:
                years_dict[year] = set()
            
            years_dict[year].add(month)
        
        # Update each set of menus
        for menu_set in menus_to_update:
            months_menu = menu_set.get('months')
            years_menu = menu_set.get('years')
            
            if not months_menu or not years_menu:
                continue
                
            # Clear menus
            months_menu.clear()
            years_menu.clear()
            
            # Populate Years menu
            years = sorted(years_dict.keys(), reverse=True)
            for year in years:
                year_action = years_menu.addAction(str(year))
                year_action.triggered.connect(lambda checked, y=year: load_lastfm_scrobbles_year(self, y))
            
            # Populate Months menu (years as submenus, months within each year)
            for year in years:
                year_menu = months_menu.addMenu(str(year))
                
                # Get months for this year and sort them
                months = sorted(years_dict[year])
                
                # Add month items
                for month in months:
                    month_name = time.strftime("%B", time.struct_time((2000, month, 1, 0, 0, 0, 0, 0, 0)))
                    month_action = year_menu.addAction(month_name)
                    month_action.triggered.connect(lambda checked, y=year, m=month: load_lastfm_scrobbles_month(self, y, m))
        
        self.log(f"Populated scrobbles menus with {len(years)} years")
        return True
    except Exception as e:
        self.log(f"Error populating scrobbles time menus: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False

def get_track_links_from_db(self, artist, title, album=None):
    """Get track links from the database"""
    try:
        # Use the get_detailed_info method foundation
        if not self.db_path or not os.path.exists(self.db_path):
            self.log(f"Database not found at: {self.db_path}")
            return None
        
        # Import the database query class
        from db.tools.consultar_items_db import MusicDatabaseQuery
        
        db = MusicDatabaseQuery(self.db_path)
        
        # Get track links
        if album:
            track_links = db.get_track_links(album, title)
        else:
            # Try to find without album
            # First get song info to find album
            song_info = db.get_song_info(title, artist)
            if song_info and song_info.get('album'):
                track_links = db.get_track_links(song_info['album'], title)
            else:
                # If we don't have album info, we can't get links this way
                track_links = None
        
        # If we didn't find links via track, try artist->album->track path
        if not track_links:
            # Get albums by artist
            artist_albums = db.get_artist_albums(artist)
            if artist_albums:
                for album_tuple in artist_albums:
                    album_name = album_tuple[0]
                    
                    # Get album info
                    album_info = db.get_album_info(album_name, artist)
                    
                    if album_info and 'songs' in album_info:
                        for song in album_info['songs']:
                            if song.get('title', '').lower() == title.lower():
                                # Found the track, get links
                                track_links = db.get_track_links(album_name, title)
                                if track_links:
                                    break
                    
                    if track_links:
                        break
        
        db.close()
        return track_links
        
    except Exception as e:
        self.log(f"Error getting track links from database: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return None


def setup_scrobbles_menu(self):
    """Configure the scrobbles menu for the Last.fm button"""
    try:
        # Find the scrobbles button
        self.scrobbles_button = self.findChild(QPushButton, 'scrobbles_menu')  # As named in your UI file
        
        if not self.scrobbles_button:
            self.log("Error: Scrobbles button not found")
            return False
            
        # Create the menu
        self.scrobbles_menu = QMenu(self.scrobbles_button)
        
        # Set up Last.fm menu items
        menu_refs = setup_lastfm_menu_items(self, self.scrobbles_menu)
        
        # Store menu references
        self.months_menu = menu_refs.get('months_menu')
        self.years_menu = menu_refs.get('years_menu')
        
        # Set the menu for the button
        self.scrobbles_button.setMenu(self.scrobbles_menu)
        
        self.log("Scrobbles menu set up")
        return True
    except Exception as e:
        self.log(f"Error setting up scrobbles menu: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False


def connect_lastfm_controls(self):
    """Connect Last.fm controls (slider and spinbox) bidirectionally"""
    try:
        # Find the controls
        scrobbles_slider = self.findChild(QSlider, 'scrobbles_slider')
        scrobbles_spinbox = self.findChild(QSpinBox, 'scrobblers_spinBox')
        
        if scrobbles_slider and scrobbles_spinbox:
            # Set proper ranges
            scrobbles_slider.setMinimum(25)
            scrobbles_slider.setMaximum(1000)
            scrobbles_spinbox.setMinimum(25)
            scrobbles_spinbox.setMaximum(1000)
            
            # Block signals during initial setup
            scrobbles_slider.blockSignals(True)
            scrobbles_spinbox.blockSignals(True)
            
            # Set initial values
            scrobbles_slider.setValue(self.scrobbles_limit)
            scrobbles_spinbox.setValue(self.scrobbles_limit)
            
            # Unblock signals
            scrobbles_slider.blockSignals(False)
            scrobbles_spinbox.blockSignals(False)
            
            # Connect bidirectionally
            scrobbles_slider.valueChanged.connect(scrobbles_spinbox.setValue)
            scrobbles_spinbox.valueChanged.connect(scrobbles_slider.setValue)
            
            # Also connect to save settings on change
            scrobbles_slider.valueChanged.connect(lambda value: self.set_scrobbles_limit(value))
            
            self.log("Connected Last.fm controls")
            return True
        else:
            self.log("Could not find scrobbles slider or spinbox")
            return False
    except Exception as e:
        self.log(f"Error connecting Last.fm controls: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False


def load_lastfm_cache_if_exists(self):
    """Load Last.fm cache if it exists and populate menus"""
    try:
        cache_file = get_lastfm_cache_path()
        
        if os.path.exists(cache_file):
            self.log(f"Found Last.fm cache file: {cache_file}")
            
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    scrobbles = cache_data.get('scrobbles', [])
                    
                    if scrobbles:
                        self.log(f"Loaded {len(scrobbles)} scrobbles from cache")
                        # Populate menus
                        populate_scrobbles_time_menus(self, scrobbles)
                        return True
            except Exception as e:
                self.log(f"Error loading Last.fm cache: {str(e)}")
        else:
            self.log("No Last.fm cache file found")
        
        return False
    except Exception as e:
        self.log(f"Error checking Last.fm cache: {str(e)}")
        return False

