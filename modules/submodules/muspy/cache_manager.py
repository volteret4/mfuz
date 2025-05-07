# submodules/muspy/cache_manager.py
import os
import json
import time
from pathlib import Path
import logging

class CacheManager:
    def __init__(self, project_root):
        self.project_root = project_root
        self.logger = logging.getLogger(__name__)
        
    def cache_manager(self, cache_type, data=None, force_refresh=False, expiry_hours=24):
        """
        Manages caching for different types of data (top_artists, loved_tracks, releases)
        
        Args:
            cache_type (str): Type of cache ('top_artists', 'loved_tracks', 'releases')
            data (dict, optional): Data to cache. If None, retrieves cache.
            force_refresh (bool): Whether to ignore cache and force refresh
            expiry_hours (int): Hours after which cache expires (default 24)
            
        Returns:
            dict or None: Cached data if available and not expired, None otherwise
        """
        # Ensure cache directory exists
        cache_dir = Path(self.project_root, ".content", "cache", "muspy_module")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Define cache file path
        cache_file = Path(cache_dir, f"{cache_type}_cache.json")
        
        # If we're storing data
        if data is not None:
            cache_data = {
                "timestamp": time.time(),
                "data": data
            }
            
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                self.logger.debug(f"Cached {cache_type} data successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error caching {cache_type} data: {e}")
                return False
        
        # If we're retrieving data
        else:
            # If force refresh, don't use cache
            if force_refresh:
                return None
                
            # Check if cache file exists
            if not os.path.exists(cache_file):
                return None
                
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                # Check if cache is expired
                timestamp = cache_data.get("timestamp", 0)
                expiry_time = timestamp + (expiry_hours * 3600)  # Convert hours to seconds
                
                if time.time() > expiry_time:
                    self.logger.debug(f"{cache_type} cache expired")
                    return None
                    
                # Cache is valid
                self.logger.debug(f"Using cached {cache_type} data")
                return cache_data.get("data")
                
            except Exception as e:
                self.logger.error(f"Error loading {cache_type} cache: {e}")
                return None

    def spotify_cache_manager(self, cache_key, data=None, force_refresh=False, expiry_hours=24):
        """
        Manages caching for Spotify data
        
        Args:
            cache_key (str): Unique key for the cache entry
            data (dict, optional): Data to cache. If None, retrieves cache.
            force_refresh (bool): Whether to ignore cache and force refresh
            expiry_hours (int): Hours after which cache expires (default 24)
                
        Returns:
            dict or None: Cached data if available and not expired, None otherwise
        """
        # Ensure cache directory exists
        cache_dir = Path(self.project_root, ".content", "cache", "muspy", "spotify")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Define cache file path
        cache_file = Path(cache_dir, f"{cache_key}_cache.json")
        
        # If we're storing data
        if data is not None:
            cache_data = {
                "timestamp": time.time(),
                "data": data
            }
            
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                self.logger.debug(f"Cached Spotify {cache_key} data successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error caching Spotify {cache_key} data: {e}")
                return False
        
        # If we're retrieving data
        else:
            # If force refresh, don't use cache
            if force_refresh:
                return None
                    
            # Check if cache file exists
            if not os.path.exists(cache_file):
                return None
                    
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                        
                # Check if cache is expired
                timestamp = cache_data.get("timestamp", 0)
                expiry_time = timestamp + (expiry_hours * 3600)  # Convert hours to seconds
                    
                if time.time() > expiry_time:
                    self.logger.debug(f"Spotify {cache_key} cache expired")
                    return None
                        
                # Cache is valid
                self.logger.debug(f"Using cached Spotify {cache_key} data")
                return cache_data.get("data")
                    
            except Exception as e:
                self.logger.error(f"Error loading Spotify {cache_key} cache: {e}")
                return None

    def clear_lastfm_cache(self):
        """
        Clear the LastFM cache files
        """
        import glob
        from PyQt6.QtWidgets import QMessageBox
        
        cache_dir = Path(self.project_root, ".content", "cache", "muspy_module")
        
        if not os.path.exists(cache_dir):
            return
        
        try:
            # Find all LastFM cache files
            lastfm_cache_files = glob.glob(Path(cache_dir, "top_artists_*.json"))
            lastfm_cache_files.extend(glob.glob(Path(cache_dir, "loved_tracks_*.json")))
            
            for cache_file in lastfm_cache_files:
                try:
                    os.remove(cache_file)
                    self.logger.debug(f"Removed cache file: {cache_file}")
                except Exception as e:
                    self.logger.error(f"Error removing cache file {cache_file}: {e}")
            
            return len(lastfm_cache_files)
        except Exception as e:
            self.logger.error(f"Error clearing LastFM cache: {e}")
            return 0

    def clear_spotify_cache(self):
        """
        Clear all Spotify cache files
        """
        import glob
        
        # Ensure cache directory exists
        cache_dir = Path(self.project_root, ".content", "cache", "muspy", "spotify")
        
        if not os.path.exists(cache_dir):
            return 0
        
        try:
            # Find all Spotify cache files
            cache_files = glob.glob(Path(cache_dir, "*_cache.json"))
            
            if not cache_files:
                return 0
            
            # Delete each cache file
            count = 0
            for cache_file in cache_files:
                try:
                    os.remove(cache_file)
                    count += 1
                except Exception as e:
                    self.logger.error(f"Error removing cache file {cache_file}: {e}")
            
            return count
        except Exception as e:
            self.logger.error(f"Error clearing Spotify cache: {e}")
            return 0



 
    def display_releases_table(self, releases):
        """
        Display releases in a table that takes up all available space
        
        Args:
            releases (list): List of release dictionaries
        """
        # Hide the results text if visible
        if hasattr(self, 'results_text') and self.results_text.isVisible():
            self.results_text.hide()
        
        # Remove any existing table widget if present
        for i in reversed(range(self.layout().count())):
            item = self.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QTableWidget):
                item.widget().deleteLater()
        
        # Create the table widget
        table = QTableWidget(self)
        table.setObjectName("releases_table")
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Artist", "Release Title", "Type", "Date", "Disambiguation"])
        
        # Make the table expand to fill all available space
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table.setMinimumHeight(400)  # Ensure reasonable minimum height
        
        # Configure table headers
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Artist
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Type
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Date
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Disambiguation
        
        # Set row count
        table.setRowCount(len(releases))
        
        # Fill the table with data
        self._fill_releases_table(table, releases)
        
        # Insert the table into the layout in the correct position
        # This should be after the search area and before the button area
        main_layout = self.layout()
        
        # Create a count label for the number of releases
        count_label = QLabel(f"Showing {len(releases)} upcoming releases")
        count_label.setObjectName("count_label")
        
        # Use consistent positioning - insert widgets before the last item (button row)
        insert_position = main_layout.count() - 1
        main_layout.insertWidget(insert_position, count_label)
        main_layout.insertWidget(insert_position + 1, table)
        
        # Add styling to make the table fit the aesthetic
        table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
            }
            QHeaderView::section {
                background-color: #24283b;
                color: #a9b1d6;
                border: none;
                padding: 6px;
            }
            QTableWidget::item {
                border: none;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #364A82;
            }
        """)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
    
        # Resize columns to fit content
        table.resizeColumnsToContents()
        
        # Store reference for later access
        self.releases_table = table
        
        return table
