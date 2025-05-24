# submodules/muspy/display_utils.py
import os
import logging
import datetime
import requests
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QLabel, QTextEdit, QPushButton, QCheckBox,
                          QApplication, QStackedWidget, QWidget, QMenu, QHBoxLayout, QAbstractItemView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QAction
import datetime
from modules.submodules.muspy import lastfm_manager
from modules.submodules.muspy.table_widgets import NumericTableWidgetItem, DateTableWidgetItem

class DisplayManager:
    def __init__(self, parent, spotify_manager=None, muspy_manager=None, utils=None, lastfm_manager=None, bluesky_manager=None):
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        self.spotify_manager = spotify_manager
        self.muspy_manager = muspy_manager
        self.lastfm_manager = lastfm_manager
        self.utils = utils
        self.bluesky_manager = bluesky_manager
    
    def show_text_page(self, html_content=None):
        """
        Switch to the text page and optionally update its content
        
        Args:
            html_content (str, optional): HTML content to display
        """
        # Find the stacked widget
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            # Asegurarnos de que results_text es visible como fallback
            if hasattr(self.parent, 'results_text'):
                self.parent.results_text.show()
            return
        
        # Find the text page
        text_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "text_page":
                text_page = widget
                break
        
        if not text_page:
            self.logger.error("text_page not found in stacked widget")
            # Asegurarnos de que results_text es visible como fallback
            if hasattr(self.parent, 'results_text'):
                self.parent.results_text.show()
            return
        
        # Update content if provided
        if html_content and hasattr(self.parent, 'results_text'):
            self.parent.results_text.setHtml(html_content)
        
        # Switch to text page
        stack_widget.setCurrentWidget(text_page)
        
        # Asegurarnos de que results_text es visible dentro de text_page
        if hasattr(self.parent, 'results_text'):
            self.parent.results_text.setVisible(True)
    
    def update_status_text(self, text):
        """Update the status text in the results area"""
        if hasattr(self.parent, 'results_text'):
            self.parent.results_text.append(text)
            QApplication.processEvents()  # Keep UI responsive
    
    def display_releases_in_stacked_widget(self, releases):
        """
        Display releases in the proper page of the stacked widget
        
        Args:
            releases (list): List of release dictionaries
        """
        # Find the stacked widget
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the releases table page
        releases_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "releases_page":
                releases_page = widget
                break
        
        if not releases_page:
            self.logger.error("Releases page not found in stacked widget")
            return
        
        # Get the table widget from the releases page
        table = releases_page.findChild(QTableWidget, "releases_table")
        if not table:
            self.logger.error("Releases table not found in releases page")
            return
        
        # Get count label
        count_label = releases_page.findChild(QLabel, "count_label")
        if count_label:
            count_label.setText(f"Showing {len(releases)} upcoming releases")
        
        # Configure table
        table.setRowCount(len(releases))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table
        self._fill_releases_table(table, releases)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
    
        # Resize columns to fit content
        table.resizeColumnsToContents()
        
        # Switch to the releases page - this will fully hide the text page
        stack_widget.setCurrentWidget(releases_page)
 
    def _fill_releases_table(self, table, releases):
        """
        Rellena una tabla existente con los datos de lanzamientos
        
        Args:
            table (QTableWidget): Tabla a rellenar
            releases (list): Lista de lanzamientos
        """
        # Fill the table
        for row, release in enumerate(releases):
            artist = release.get('artist', {})
            
            # Create items for each column
            artist_name_item = QTableWidgetItem(artist.get('name', 'Unknown'))
            if artist.get('disambiguation'):
                artist_name_item.setToolTip(artist.get('disambiguation'))
            table.setItem(row, 0, artist_name_item)
            
            # Title with proper casing and full information
            title_item = QTableWidgetItem(release.get('title', 'Untitled'))
            if release.get('comments'):
                title_item.setToolTip(release.get('comments'))
            table.setItem(row, 1, title_item)
            # Release type (Album, EP, etc.)
            type_item = QTableWidgetItem(release.get('type', 'Unknown').title())
            table.setItem(row, 2, type_item)
            
        
            # Date column with proper date sorting
            date_str = release.get('date', 'No date')
            date_item = DateTableWidgetItem(date_str)  # Use our custom class
            table.setItem(row, 3, date_item)
            
            # Highlight dates that are within the next month  
            try:
                release_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                today = datetime.date.today()
                one_month = today + datetime.timedelta(days=30)
                
                if release_date <= today + datetime.timedelta(days=7):
                    # Coming very soon - red
                    date_item.setBackground(QColor(31, 60, 28))
                elif release_date <= one_month:
                    # Coming in a month - yellow
                    date_item.setBackground(QColor(60, 28, 31))
            except ValueError:
                # If date parsing fails, don't color
                pass
                
            table.setItem(row, 3, date_item)
            
            # Additional details
            details = []
            if release.get('format'):
                details.append(f"Format: {release.get('format')}")
            if release.get('tracks'):
                details.append(f"Tracks: {release.get('tracks')}")
            if release.get('country'):
                details.append(f"Country: {release.get('country')}")
            if artist.get('disambiguation'):
                details.append(artist.get('disambiguation'))

            details_item = QTableWidgetItem("; ".join(details) if details else "")
            table.setItem(row, 4, details_item)



    def display_releases_in_muspy_results_page(self, releases, artist_name=None):
        """
        Muestra los lanzamientos en la página específica de resultados de Muspy
        
        Args:
            releases (list): Lista de lanzamientos
            artist_name (str, optional): Nombre del artista para el título
        """
        # Find the stacked widget
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            # Fallback a la función original si no encontramos el widget
            self.display_releases_table(releases)
            return
        
        # Find the muspy_results page - CHANGED TO MATCH UI OBJECT NAME
        results_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "muspy_results_widget":  # Updated object name
                results_page = widget
                break
        
        if not results_page:
            self.logger.error("muspy_results_widget page not found in stacked widget")
            # Log more details for debugging
            self.logger.error(f"Available pages in stackedWidget ({stack_widget.count()}):")
            for i in range(stack_widget.count()):
                widget = stack_widget.widget(i)
                self.logger.error(f"  - Page {i}: {widget.objectName()}")            
            
            # Fallback a la función original si no encontramos la página
            self.display_releases_table(releases)
            return
        
        # Get the table widget and count label from the results page
        table = results_page.findChild(QTableWidget, "tableWidget_muspy_results")
        count_label = results_page.findChild(QLabel, "label_result_count")
        
        if not table:
            self.logger.error("tableWidget_muspy_results not found in results page")
            return
        
        # Update count label if exists
        if count_label:
            count_label.setText(f"Showing {len(releases)} upcoming releases for {artist_name or 'artist'}")
        
        # Configure table
        table.setRowCount(len(releases))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table
        self._fill_releases_table(table, releases)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
    
        # Resize columns to fit content
        table.resizeColumnsToContents()
        
        # Switch to the results page
        stack_widget.setCurrentWidget(results_page)



    def display_lastfm_artists_in_stacked_widget(self, artists):
        """
        Display Last.fm artists in the artists page of the stacked widget
        
        Args:
            artists (list): List of artist dictionaries from Last.fm
        """
        # Find the stacked widget
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            # Fallback if stacked widget not found
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the artists page
        artists_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "artists_page":
                artists_page = widget
                break
        
        if not artists_page:
            self.logger.error("Artists page not found in stacked widget")
            return
        
        # Get the table widget and count label
        table = artists_page.findChild(QTableWidget, "artists_table")
        count_label = artists_page.findChild(QLabel, "artists_count_label")
        
        if not table:
            self.logger.error("Artists table not found in artists page")
            return
        
        # Update count label
        if count_label:
            count_label.setText(f"Showing {len(artists)} top artists for {self.lastfm_username}")
        
        # Configure table to include new columns - make sure we have 5 columns now
        table.setColumnCount(5)  # Update column count to include listeners and URL
        table.setHorizontalHeaderLabels(["Artist", "Playcount", "Listeners", "URL", "Actions"])
        
        # Configure table
        table.setRowCount(len(artists))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill table with artist data
        for i, artist in enumerate(artists):
            artist_name = artist.get('name', '')
            playcount = str(artist.get('playcount', 'N/A'))
            listeners = str(artist.get('listeners', 'N/A'))
            url = artist.get('url', '')
            
            # Artist name
            name_item = QTableWidgetItem(artist_name)
            table.setItem(i, 0, name_item)
            
            # Playcount - with numeric sorting capability
            playcount_item = NumericTableWidgetItem(playcount)
            playcount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 1, playcount_item)
            
            # Listeners - with numeric sorting capability
            listeners_item = NumericTableWidgetItem(listeners)
            listeners_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 2, listeners_item)
            
            # URL - add the Last.fm URL
            url_item = QTableWidgetItem(url)
            table.setItem(i, 3, url_item)
            
            # Actions - create a widget with buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)
            
            # Add "Follow" button
            follow_button = QPushButton("Follow")
            follow_button.setProperty("artist_name", artist_name)
            follow_button.setMaximumWidth(80)
            follow_button.clicked.connect(lambda checked, a=artist_name: self.lastfm_manager.add_lastfm_artist_to_muspy(a))
            actions_layout.addWidget(follow_button)
            
            # Store URL and MBID in the item data for context menu use
            if url:
                name_item.setData(Qt.ItemDataRole.UserRole, {'url': url, 'mbid': artist.get('mbid', '')})
            
            table.setCellWidget(i, 4, actions_widget)
        
            # Re-enable sorting
            table.setSortingEnabled(True)
        
            # Resize columns to fit content
            table.resizeColumnsToContents()
        
        
        # Configure context menu for the table
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_unified_context_menu)
        
        # Switch to the artists page
        stack_widget.setCurrentWidget(artists_page)



    def display_loved_tracks_in_stacked_widget(self, loved_tracks):
        """
        Display loved tracks in the loved tracks page of the stacked widget
        
        Args:
            loved_tracks (list): List of loved track objects from Last.fm or cached dictionaries
        """
        # Find the stacked widget
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the loved tracks page
        loved_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "loved_tracks_page":
                loved_page = widget
                break
        
        if not loved_page:
            self.logger.error("Loved tracks page not found in stacked widget")
            return
        
        # Get the table and count label
        table = loved_page.findChild(QTableWidget, "loved_tracks_table")
        count_label = loved_page.findChild(QLabel, "loved_count_label")
        
        if not table:
            self.logger.error("Loved tracks table not found in loved tracks page")
            return
        
        # Update count label
        if count_label:
            count_label.setText(f"Showing {len(loved_tracks)} loved tracks for {self.lastfm_username}")
        
        # Configure table
        table.setRowCount(len(loved_tracks))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table with data
        for i, loved_track in enumerate(loved_tracks):
            # Check if this is a pylast object or dictionary from cache
            if hasattr(loved_track, 'track'):
                # Extract data from pylast objects
                track = loved_track.track
                artist_name = track.artist.name
                track_name = track.title
                
                # Get album if available
                album_name = ""
                try:
                    album = track.get_album()
                    if album:
                        album_name = album.title
                except:
                    pass
                    
                # Get date if available
                date_text = ""
                if hasattr(loved_track, "date") and loved_track.date:
                    try:
                        date_obj = datetime.datetime.fromtimestamp(int(loved_track.date))
                        date_text = date_obj.strftime("%Y-%m-%d")
                        date_str = loved_track.get(date_text, 'No date')
                        date_item = DateTableWidgetItem(date_str)
                    except:
                        date_text = str(loved_track.date)
            else:
                # This is a dictionary from cache
                artist_name = loved_track.get('artist', '')
                track_name = loved_track.get('title', '')
                album_name = loved_track.get('album', '')
                
                # Format date
                date_value = loved_track.get('date')
                date_text = ""
                if date_value:
                    try:
                        import datetime
                        date_obj = datetime.datetime.fromtimestamp(int(date_value))
                        date_text = date_obj.strftime("%Y-%m-%d")
                    except:
                        date_text = str(date_value)
            
            # Set artist name column
            artist_item = QTableWidgetItem(artist_name)
            table.setItem(i, 0, artist_item)
            
            # Set track name column
            track_item = QTableWidgetItem(track_name)
            table.setItem(i, 1, track_item)
            
            # Set album column
            album_item = QTableWidgetItem(album_name)
            table.setItem(i, 2, album_item)
            
            # Date column

            date_item = DateTableWidgetItem(date_text)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 3, date_item)
            
            # Actions column with buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)
            
            # Follow artist button
            follow_button = QPushButton("Follow Artist")
            follow_button.setMaximumWidth(90)
            follow_button.setProperty("artist_name", artist_name)
            follow_button.clicked.connect(lambda checked, a=artist_name: self.lastfm_manager.add_lastfm_artist_to_muspy(a))
            actions_layout.addWidget(follow_button)
            
            table.setCellWidget(i, 4, actions_widget)
        
            # Re-enable sorting
            table.setSortingEnabled(True)
            
            # Resize columns to fit content
            table.resizeColumnsToContents()
        
        # Switch to the loved tracks page
        stack_widget.setCurrentWidget(loved_page)





    def display_spotify_artists_in_stacked_widget(self, artists):
            """
            Display Spotify artists in the stacked widget
            
            Args:
                artists (list): List of artist dictionaries
            """
            # Find the stacked widget
            stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
            if not stack_widget:
                self.logger.error("Stacked widget not found in UI")
                return
            
            # Find the spotify_artists_page (assuming it exists in the UI)
            spotify_page = None
            for i in range(stack_widget.count()):
                widget = stack_widget.widget(i)
                if widget.objectName() == "spotify_artists_page":
                    spotify_page = widget
                    break
            
            if not spotify_page:
                self.logger.error("spotify_artists_page not found in stacked widget")
                # Fallback to text display
                self._display_spotify_artists_as_text(artists)
                return
            
            # Get the table from the page
            table = spotify_page.findChild(QTableWidget, "spotify_artists_table")
            if not table:
                self.logger.error("spotify_artists_table not found in spotify_artists_page")
                # Fallback to text display
                self._display_spotify_artists_as_text(artists)
                return
            
            # Get the count label
            count_label = spotify_page.findChild(QLabel, "spotify_artists_count_label")
            if count_label:
                count_label.setText(f"Showing {len(artists)} artists you follow on Spotify")
            
            # Configure table
            table.setRowCount(len(artists))
            table.setSortingEnabled(False)  # Disable sorting while updating
            
            # Fill the table with data
            for i, artist in enumerate(artists):
                # Name column
                name_item = QTableWidgetItem(artist.get('name', 'Unknown'))
                table.setItem(i, 0, name_item)
                
                # Genres column
                genres_item = QTableWidgetItem(artist.get('genres', ''))
                table.setItem(i, 1, genres_item)
                
                # Followers column - Usar NumericTableWidgetItem
                followers = artist.get('followers', 0)
                followers_item = NumericTableWidgetItem(f"{followers:,}" if followers else "0")
                followers_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(i, 2, followers_item)
                
                # Popularity column - Usar NumericTableWidgetItem
                popularity = artist.get('popularity', 0)
                popularity_item = NumericTableWidgetItem(str(popularity))
                popularity_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(i, 3, popularity_item)
            
            # Re-enable sorting
            table.setSortingEnabled(True)
        
            # Resize columns to fit content
            table.resizeColumnsToContents()
            
            # Configure context menu for the table
            if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
                table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                table.customContextMenuRequested.connect(self.spotify_manager.show_spotify_artist_context_menu)
            
            # Switch to the Spotify artists page
            stack_widget.setCurrentWidget(spotify_page)


    def display_spotify_artist_albums_in_stacked_widget(self, albums, artist_name):
        """
        Display albums for a specific Spotify artist in the stacked widget
        
        Args:
            albums (list): List of album dictionaries
            artist_name (str): Name of the artist
        """
        # Find the stacked widget
        stack_widget = self.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the spotify_releases_page (we'll reuse it for albums)
        spotify_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "spotify_releases_page":
                spotify_page = widget
                break
        
        if not spotify_page:
            self.logger.error("spotify_releases_page not found in stacked widget")
            # Fallback to text display
            self._display_spotify_artist_albums_as_text(albums, artist_name)
            return
        
        # Get the table from the page
        table = spotify_page.findChild(QTableWidget, "spotify_releases_table")
        if not table:
            self.logger.error("spotify_releases_table not found in spotify_releases_page")
            # Fallback to text display
            self._display_spotify_artist_albums_as_text(albums, artist_name)
            return
        
        # Get the count label
        count_label = spotify_page.findChild(QLabel, "spotify_releases_count_label")
        if count_label:
            count_label.setText(f"Showing {len(albums)} albums for {artist_name}")
        
        # Configure table
        table.setRowCount(len(albums))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table with data
        for i, album in enumerate(albums):
            # Artist column
            artist_item = QTableWidgetItem(artist_name)
            table.setItem(i, 0, artist_item)
            
            # Title column
            title_item = QTableWidgetItem(album.get('title', 'Unknown'))
            table.setItem(i, 1, title_item)
            
            # Type column
            type_item = QTableWidgetItem(album.get('type', ''))
            table.setItem(i, 2, type_item)
            
            # Date column
            date_item = QTableWidgetItem(album.get('date', ''))
            table.setItem(i, 3, date_item)
            
            # Tracks column - Usar NumericTableWidgetItem
            tracks_item = NumericTableWidgetItem(str(release.get('total_tracks', 0)))
            tracks_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 4, tracks_item)
            
            # Store the Spotify IDs for context menu actions
            for col in range(table.columnCount()):
                if table.item(i, col):
                    # Store both album ID and artist ID
                    item_data = {
                        'release_id': album.get('id', ''),
                        'artist_id': album.get('artist_id', '')
                    }
                    table.item(i, col).setData(Qt.ItemDataRole.UserRole, item_data)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
    
        # Resize columns to fit content
        table.resizeColumnsToContents()
        
        # Configure context menu for the table
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_spotify_release_context_menu)
        
        # Switch to the Spotify releases page
        stack_widget.setCurrentWidget(spotify_page)


    def display_spotify_releases_in_stacked_widget(self, releases):
        """
        Display Spotify releases in the stacked widget
        
        Args:
            releases (list): List of release dictionaries
        """
        # Find the stacked widget
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the spotify_releases_page (assuming it exists in the UI)
        spotify_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "spotify_releases_page":
                spotify_page = widget
                break
        
        if not spotify_page:
            self.logger.error("spotify_releases_page not found in stacked widget")
            # Fallback to text display
            self._display_spotify_releases_as_text(releases)
            return
        
        # Get the table from the page
        table = spotify_page.findChild(QTableWidget, "spotify_releases_table")
        if not table:
            self.logger.error("spotify_releases_table not found in spotify_releases_page")
            # Fallback to text display
            self._display_spotify_releases_as_text(releases)
            return
        
        # Get the count label
        count_label = spotify_page.findChild(QLabel, "spotify_releases_count_label")
        if count_label:
            count_label.setText(f"Showing {len(releases)} new releases from artists you follow on Spotify")
        
        # Configure table
        table.setRowCount(len(releases))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table with data
        for i, release in enumerate(releases):
            # Artist column
            artist_item = QTableWidgetItem(release.get('artist', 'Unknown'))
            table.setItem(i, 0, artist_item)
            
            # Title column
            title_item = QTableWidgetItem(release.get('title', 'Unknown'))
            table.setItem(i, 1, title_item)
            
            # Type column
            type_item = QTableWidgetItem(release.get('type', ''))
            table.setItem(i, 2, type_item)
            
            # Date column
            date_str = release.get('date', 'No date')
            date_item = DateTableWidgetItem(date_str)
            table.setItem(i, 3, date_item)
            
            # Tracks column - Usar NumericTableWidgetItem
            tracks_item = NumericTableWidgetItem(str(release.get('total_tracks', 0)))
            tracks_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 4, tracks_item)
            
            # Store the Spotify IDs for context menu actions
            for col in range(table.columnCount()):
                if table.item(i, col):
                    # Store both release ID and artist ID
                    item_data = {
                        'release_id': release.get('id', ''),
                        'artist_id': release.get('artist_id', '')
                    }
                    table.item(i, col).setData(Qt.ItemDataRole.UserRole, item_data)
        
        # Re-enable sorting
        table.setSortingEnabled(True)
    
        # Resize columns to fit content
        table.resizeColumnsToContents()
        
        # Configure context menu for the table
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_spotify_release_context_menu)
        
        # Switch to the Spotify releases page
        stack_widget.setCurrentWidget(spotify_page)



    def display_spotify_saved_tracks_in_stacked_widget(self, tracks):
        """
        Display Spotify saved tracks in the stacked widget
        
        Args:
            tracks (list): List of track dictionaries
        """
        # Find the stacked widget
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the spotify_saved_tracks_page
        saved_tracks_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "spotify_saved_tracks_page":
                saved_tracks_page = widget
                break
        
        if not saved_tracks_page:
            self.logger.error("spotify_saved_tracks_page not found in stacked widget")
            # Fallback to text display
            self._display_spotify_saved_tracks_as_text(tracks)
            return
        
        # Get the table from the page
        table = saved_tracks_page.findChild(QTableWidget, "spotify_saved_tracks_table")
        if not table:
            self.logger.error("spotify_saved_tracks_table not found in spotify_saved_tracks_page")
            # Fallback to text display
            self._display_spotify_saved_tracks_as_text(tracks)
            return
        
        # Get the count label
        count_label = saved_tracks_page.findChild(QLabel, "spotify_saved_tracks_count_label")
        if count_label:
            count_label.setText(f"Showing {len(tracks)} saved tracks on Spotify")
        
        # Configure table - NO AÑADIMOS COLUMNAS, USAMOS LAS EXISTENTES
        # Asumimos que la tabla ya tiene las columnas configuradas según el UI
        table.setRowCount(len(tracks))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table with data
        # Asumimos el orden: Canción(0), Artista(1), Álbum(2), Duración(3), Fecha(4)
        for i, track in enumerate(tracks):
            # Track name column (Canción)
            name_item = QTableWidgetItem(track.get('name', 'Unknown'))
            table.setItem(i, 0, name_item)
            
            # Artist column (Artista)
            artist_item = QTableWidgetItem(track.get('artist', 'Unknown'))
            table.setItem(i, 1, artist_item)
            
            # Album column (Álbum)
            album_item = QTableWidgetItem(track.get('album', 'Unknown'))
            table.setItem(i, 2, album_item)
            
            # Duration column (Duración) - convert ms to min:sec format
            duration_ms = track.get('duration_ms', 0)
            minutes, seconds = divmod(duration_ms // 1000, 60)
            duration_str = f"{minutes}:{seconds:02d}"
            duration_item = QTableWidgetItem(duration_str)
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 3, duration_item)
            
            # Added date column (Fecha)
            added_at = track.get('added_at', '')
            if added_at:
                # Convert ISO 8601 date to more readable format
                try:
                    import datetime
                    date_obj = datetime.datetime.fromisoformat(added_at.replace('Z', '+00:00'))
                    added_date = date_obj.strftime("%Y-%m-%d")
                except:
                    added_date = added_at
            else:
                added_date = ''
            
            date_item = QTableWidgetItem(added_date)
            table.setItem(i, 4, date_item)
            
            # Store track data for context menu actions - para todos los ítems de la fila
            for col in range(table.columnCount()):
                if table.item(i, col):
                    table.item(i, col).setData(Qt.ItemDataRole.UserRole, {
                        'track_id': track.get('id', ''),
                        'track_uri': track.get('uri', ''),
                        'track_name': track.get('name', ''),
                        'artist_name': track.get('artist', '')
                    })
        
        # Re-enable sorting
        table.setSortingEnabled(True)
    
        # Resize columns to fit content
        table.resizeColumnsToContents()
        
        # Configure context menu for the table
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_spotify_track_context_menu)
        
        # Switch to the Spotify saved tracks page
        stack_widget.setCurrentWidget(saved_tracks_page)



 
    def display_spotify_top_items_in_stacked_widget(self, items, item_type):
        """
        Display Spotify top items in the stacked widget
        
        Args:
            items (list): List of item dictionaries
            item_type (str): Type of items ('artists' or 'tracks')
        """
        # Find the stacked widget
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            return
        
        # Find the spotify_top_items_page
        top_items_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "spotify_top_items_page":
                top_items_page = widget
                break
        
        if not top_items_page:
            self.logger.error("spotify_top_items_page not found in stacked widget")
            # Fallback to text display
            self._display_spotify_top_items_as_text(items, item_type)
            return
        
        # Get the table from the page
        table = top_items_page.findChild(QTableWidget, "spotify_top_items_table")
        if not table:
            self.logger.error("spotify_top_items_table not found in spotify_top_items_page")
            # Fallback to text display
            self._display_spotify_top_items_as_text(items, item_type)
            return
        
        # Get the count label
        count_label = top_items_page.findChild(QLabel, "spotify_top_items_count_label")
        if count_label:
            count_label.setText(f"Showing your top {len(items)} {item_type}")
        
        # Configure columns based on item type
        if item_type == "artists":
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Rank", "Artist", "Genres", "Popularity"])
        else:  # tracks
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Rank", "Track", "Artist", "Album", "Popularity"])
        
        # Configure table
        table.setRowCount(len(items))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Fill the table with data
        for i, item in enumerate(items):
            # Rank column (1-based)
            rank_item = QTableWidgetItem(str(i + 1))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 0, rank_item)
            
            if item_type == "artists":
                # Artist name column
                name_item = QTableWidgetItem(item.get('name', 'Unknown'))
                table.setItem(i, 1, name_item)
                
                # Genres column
                genres_item = QTableWidgetItem(item.get('genres', ''))
                table.setItem(i, 2, genres_item)
                
                # Popularity column
                popularity = item.get('popularity', 0)
                popularity_item = NumericTableWidgetItem(str(popularity))
                popularity_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(i, 3, popularity_item)
                
                # Store artist ID for context menu actions
                for col in range(table.columnCount()):
                    if table.item(i, col):
                        table.item(i, col).setData(Qt.ItemDataRole.UserRole, {
                            'spotify_artist_id': item.get('id', ''),
                            'artist_name': item.get('name', '')
                        })
            else:  # tracks
                # Track name column
                name_item = QTableWidgetItem(item.get('name', 'Unknown'))
                table.setItem(i, 1, name_item)
                
                # Artist column
                artist_item = QTableWidgetItem(item.get('artist', 'Unknown'))
                table.setItem(i, 2, artist_item)
                
                # Album column
                album_item = QTableWidgetItem(item.get('album', 'Unknown'))
                table.setItem(i, 3, album_item)
                
                # Popularity column
                popularity = item.get('popularity', 0)
                popularity_item = NumericTableWidgetItem(str(popularity))
                popularity_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(i, 4, popularity_item)
                
                # Store track data for context menu actions
                for col in range(table.columnCount()):
                    if table.item(i, col):
                        table.item(i, col).setData(Qt.ItemDataRole.UserRole, {
                            'track_id': item.get('id', ''),
                            'track_uri': item.get('uri', ''),
                            'track_name': item.get('name', ''),
                            'artist_name': item.get('artist', '')
                        })
        
        # Re-enable sorting
        table.setSortingEnabled(True)
    
        # Resize columns to fit content
        table.resizeColumnsToContents()
        
        # Configure context menu for the table
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            # Connect to either artist or track context menu based on type
            if item_type == "artists":
                table.customContextMenuRequested.connect(self.spotify_manager.show_spotify_artist_context_menu)
            else:
                table.customContextMenuRequested.connect(self.show_spotify_track_context_menu)
        
        # Switch to the Spotify top items page
        stack_widget.setCurrentWidget(top_items_page)
     
    def display_bluesky_artists_in_table(self, artists):
        """
        Display Bluesky artists in the stacked widget table
        
        Args:
            artists (list): List of artist dictionaries with Bluesky info
        """
        # Find the stacked widget
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("Stacked widget not found in UI")
            # Fallback to text display
            self._display_bluesky_artists_as_text(artists)
            return
        
        # Find the bluesky_page
        bluesky_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "bluesky_page":
                bluesky_page = widget
                break
        
        if not bluesky_page:
            self.logger.error("bluesky_page not found in stacked widget")
            # Fallback to text display
            self._display_bluesky_artists_as_text(artists)
            return
        
        # Get the table from the page
        table = bluesky_page.findChild(QTableWidget, "bluesky_artists_table")
        if not table:
            self.logger.error("bluesky_artists_table not found in bluesky_page")
            # Fallback to text display
            self._display_bluesky_artists_as_text(artists)
            return
        
        # Get count label if exists
        count_label = bluesky_page.findChild(QLabel, "bluesky_count_label")
        if count_label:
            count_label.setText(f"Encontrados {len(artists)} artistas en Bluesky")
        
        # Configure table - Asegurar que tenemos la columna de checkbox primero
        table.setColumnCount(4)  # Reducido a 4 columnas: Checkbox, Artista, Handle, URL
        headers = ["Seguir", "Artista", "Handle", "URL"]
        table.setHorizontalHeaderLabels(headers)
        
        table.setRowCount(len(artists))
        table.setSortingEnabled(False)  # Disable sorting while updating
        
        # Find sidebar elements
        image_label = bluesky_page.findChild(QLabel, "bluesky_selected_artist_foto")
        messages_text = bluesky_page.findChild(QTextEdit, "bluesky_selected_artist_mensajes")
        sidebar_panel = bluesky_page.findChild(QWidget, "bluesky_selected_artist_panel")
        profile_panel = bluesky_page.findChild(QTextEdit, "bluesky_profile_panel")

        # Find the follow button
        follow_button = bluesky_page.findChild(QPushButton, "bluesky_follow")
        if follow_button:
            # Desconectar posibles conexiones anteriores
            try:
                follow_button.clicked.disconnect()
            except:
                pass
            # Conectar a la nueva función de seguimiento masivo
            follow_button.clicked.connect(lambda: self.bluesky_manager.follow_selected_bluesky_artists(table))
        
        # Hide sidebar panel initially
        if sidebar_panel:
            sidebar_panel.setVisible(len(artists) > 0)
        
        # Clear messages panel
        if messages_text:
            messages_text.clear()
        
        # Clear profile panel
        if profile_panel:
            profile_panel.clear()
        
        # Store artists data for selection handling
        self._bluesky_artists = artists
        
        # Fill the table with data
        for i, artist in enumerate(artists):
            # Checkbox para seguir - creamos un widget contenedor con un checkbox (primera columna)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setContentsMargins(4, 4, 4, 4)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            checkbox = QCheckBox()
            checkbox.setChecked(False)  # Por defecto no está marcado
            
            # Almacenar los datos del artista en el checkbox
            checkbox.setProperty("artist_data", {
                'name': artist.get('name', ''),
                'handle': artist.get('handle', ''),
                'did': artist.get('did', ''),
                'url': f"https://bsky.app/profile/{artist.get('handle', '')}",
            })
            
            checkbox_layout.addWidget(checkbox)
            table.setCellWidget(i, 0, checkbox_widget)
            
            # Artist name column (segunda columna)
            name_item = QTableWidgetItem(artist.get('name', 'Unknown'))
            table.setItem(i, 1, name_item)
            
            # Bluesky ID column (handle) (tercera columna)
            handle_item = QTableWidgetItem(artist.get('handle', ''))
            table.setItem(i, 2, handle_item)
            
            # Bluesky URL column (cuarta columna)
            url = f"https://bsky.app/profile/{artist.get('handle', '')}"
            url_item = QTableWidgetItem(url)
            table.setItem(i, 3, url_item)
            
            # Store artist data in items for context menu and selection handling
            for col in range(1, 4):  # Solo en las columnas de datos (no en la del checkbox)
                if table.item(i, col):
                    artist_data = {
                        'name': artist.get('name', ''),
                        'handle': artist.get('handle', ''),
                        'did': artist.get('did', ''),
                        'url': url,
                        'posts': artist.get('posts', []),
                        'profile': artist.get('profile', {})
                    }
                    table.item(i, col).setData(Qt.ItemDataRole.UserRole, artist_data)
        
        # Connect selection signal if not already connected
        if table.selectionBehavior() != QAbstractItemView.SelectionBehavior.SelectRows:
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Disconnect existing signals to avoid multiple connections
        try:
            table.itemSelectionChanged.disconnect()
        except:
            pass
        
        # Connect new signal
        table.itemSelectionChanged.connect(lambda: self.handle_bluesky_artist_selection(table))
        
        # Re-enable sorting
        table.setSortingEnabled(True)
        
        # Resize columns to fit content
        table.resizeColumnsToContents()
        
        # Configure context menu for the table
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_bluesky_context_menu)
        
        # Switch to the Bluesky page
        stack_widget.setCurrentWidget(bluesky_page)
        
        # Select first artist if available
        if len(artists) > 0:
            table.selectRow(0)



    def handle_bluesky_artist_selection(self, table):
        """
        Handle selection of a Bluesky artist in the table
        
        Args:
            table (QTableWidget): Table with selected artist
        """
        # Get the selected row
        selected_rows = table.selectedIndexes()
        if not selected_rows:
            return
        
        # Get the row of the first selected item
        row = selected_rows[0].row()
        
        # Get artist data from item in column 1 (name column), not column 0 (checkbox)
        item = table.item(row, 1)
        if not item:
            return
        
        artist_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(artist_data, dict):
            return
        
        # Find sidebar elements in the bluesky_page
        bluesky_page = None
        for i in range(self.parent.stackedWidget.count()):
            widget = self.parent.stackedWidget.widget(i)
            if widget.objectName() == "bluesky_page":
                bluesky_page = widget
                break
        
        if not bluesky_page:
            return
        
        # Find all the required UI elements
        image_label = bluesky_page.findChild(QLabel, "bluesky_selected_artist_foto")
        messages_text = bluesky_page.findChild(QTextEdit, "bluesky_selected_artist_mensajes")
        sidebar_panel = bluesky_page.findChild(QWidget, "bluesky_selected_artist_panel")
        profile_panel = bluesky_page.findChild(QTextEdit, "bluesky_profile_panel")  # Ahora buscamos un QTextEdit

        # Make sure panel is visible
        if sidebar_panel:
            sidebar_panel.setVisible(True)
        
        # Update profile panel if available
        if profile_panel:
            description = ""
            if 'profile' in artist_data and isinstance(artist_data['profile'], dict):
                description = artist_data['profile'].get('description', '')
            
            # Clear the profile panel and set the description
            profile_panel.clear()
            if description:
                profile_panel.setPlainText(f"Perfil de {artist_data['name']}: \n\n {description}" if description else description)
            else:
                profile_panel.setPlainText("No hay descripción disponible")

        # Update image if available
        if image_label:
            # Try to get the avatar URL from profile
            avatar_url = None
            if 'profile' in artist_data and isinstance(artist_data['profile'], dict):
                avatar = artist_data['profile'].get('avatar')
                if avatar:
                    avatar_url = avatar
            
            if avatar_url:
                # Download and display the image
                self.load_image_for_label(image_label, avatar_url)
            else:
                # Clear image if no avatar available
                image_label.clear()
                image_label.setText("No image available")
        
        # Update messages panel
        if messages_text:
            messages_text.clear()
            posts = artist_data.get('posts', [])
            
            if posts:
                messages_text.setHtml("<h3>Recent Posts</h3>")
                
                for i, post in enumerate(posts):
                    text = post.get('text', '')
                    created_at = post.get('created_at', '')
                    
                    # Format date if available
                    date_str = ""
                    if created_at:
                        try:
                            # Convert ISO 8601 format to readable date
                            from datetime import datetime
                            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                        except:
                            date_str = created_at
                    
                    # Add formatted post to text edit
                    messages_text.append(f"<p><b>{date_str}</b></p>")
                    messages_text.append(f"<p>{text}</p>")
                    
                    # Add separator between posts
                    if i < len(posts) - 1:
                        messages_text.append("<hr>")
            else:
                messages_text.setPlainText("No recent posts available")



    def load_image_for_label(self, label, url):                     # label de qtdesigner, no sello discografico
        """
        Load an image from URL and display it in a QLabel
        
        Args:
            label (QLabel): Label to display the image in
            url (str): URL of the image to load
        """
        try:
            # Import Qt modules
            from PyQt6.QtCore import QByteArray, QBuffer
            from PyQt6.QtGui import QPixmap, QImage
            
            # Create request
            response = requests.get(url)
            
            if response.status_code == 200:
                # Load image data into QPixmap
                img_data = QByteArray(response.content)
                buffer = QBuffer(img_data)
                buffer.open(QBuffer.OpenModeFlag.ReadOnly)
                
                # Load image
                image = QImage()
                image.load(buffer, "")
                
                # Create pixmap and scale to fit label while maintaining aspect ratio
                pixmap = QPixmap.fromImage(image)
                label_size = label.size()
                scaled_pixmap = pixmap.scaled(
                    label_size.width(), label_size.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Set pixmap to label
                label.setPixmap(scaled_pixmap)
            else:
                label.clear()
                label.setText(f"Failed to load image: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error loading image from {url}: {e}")
            label.clear()
            label.setText("Error loading image")


# spotify


    def _display_spotify_artists_as_text(self, artists):
        """
        Display Spotify artists as text in the results area
        
        Args:
            artists (list): List of artist dictionaries
        """
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"You follow {len(artists)} artists on Spotify")
        self.results_text.append("-" * 50)
        
        # Sort by name
        sorted_artists = sorted(artists, key=lambda x: x.get('name', '').lower())
        
        for i, artist in enumerate(sorted_artists):
            name = artist.get('name', 'Unknown')
            followers = artist.get('followers', 0)
            genres = artist.get('genres', '')
            popularity = artist.get('popularity', 0)
            
            self.results_text.append(f"{i+1}. {name}")
            self.results_text.append(f"   Followers: {followers:,}")
            if genres:
                self.results_text.append(f"   Genres: {genres}")
            self.results_text.append(f"   Popularity: {popularity}/100")
            self.results_text.append("")
        
        self.results_text.append("-" * 50)





    def _display_spotify_releases_as_text(self, releases):
        """
        Display Spotify releases as text in the results area
        
        Args:
            releases (list): List of release dictionaries
        """
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Found {len(releases)} new releases from artists you follow")
        self.results_text.append("-" * 50)
        
        for i, release in enumerate(releases):
            artist = release.get('artist', 'Unknown')
            title = release.get('title', 'Unknown')
            release_type = release.get('type', '')
            date = release.get('date', '')
            tracks = release.get('total_tracks', 0)
            
            self.results_text.append(f"{i+1}. {artist} - {title}")
            self.results_text.append(f"   Type: {release_type}")
            self.results_text.append(f"   Released: {date}")
            self.results_text.append(f"   Tracks: {tracks}")
            self.results_text.append("")
        
        self.results_text.append("-" * 50)


    def _display_spotify_saved_tracks_as_text(self, tracks):
        """
        Display Spotify saved tracks as text in the results area
        
        Args:
            tracks (list): List of track dictionaries
        """
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"You have {len(tracks)} saved tracks on Spotify")
        self.results_text.append("-" * 50)
        
        # Sort by added date (newest first)
        try:
            sorted_tracks = sorted(tracks, key=lambda x: x.get('added_at', ''), reverse=True)
        except:
            sorted_tracks = tracks
        
        for i, track in enumerate(sorted_tracks[:100]):  # Limit to 100 tracks for text display
            name = track.get('name', 'Unknown')
            artist = track.get('artist', 'Unknown')
            album = track.get('album', 'Unknown')
            
            # Format duration
            duration_ms = track.get('duration_ms', 0)
            minutes, seconds = divmod(duration_ms // 1000, 60)
            duration_str = f"{minutes}:{seconds:02d}"
            
            # Format date
            added_at = track.get('added_at', '')
            if added_at:
                try:
                    import datetime
                    date_obj = datetime.datetime.fromisoformat(added_at.replace('Z', '+00:00'))
                    added_date = date_obj.strftime("%Y-%m-%d")
                except:
                    added_date = added_at
            else:
                added_date = ''
            
            self.results_text.append(f"{i+1}. {name} - {artist}")
            self.results_text.append(f"   Album: {album}")
            self.results_text.append(f"   Duration: {duration_str}")
            if added_date:
                self.results_text.append(f"   Added: {added_date}")
            self.results_text.append("")
        
        if len(tracks) > 100:
            self.results_text.append(f"(Showing 100 of {len(tracks)} tracks)")
        
        self.results_text.append("-" * 50)


   
    def _display_spotify_top_items_as_text(self, items, item_type):
        """
        Display Spotify top items as text in the results area
        
        Args:
            items (list): List of item dictionaries
            item_type (str): Type of items ('artists' or 'tracks')
        """
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Your Top {len(items)} {item_type.title()} on Spotify")
        self.results_text.append("-" * 50)
        
        for i, item in enumerate(items):
            if item_type == "artists":
                name = item.get('name', 'Unknown')
                genres = item.get('genres', '')
                popularity = item.get('popularity', 0)
                followers = item.get('followers', 0)
                
                self.results_text.append(f"{i+1}. {name}")
                if genres:
                    self.results_text.append(f"   Genres: {genres}")
                self.results_text.append(f"   Popularity: {popularity}/100")
                self.results_text.append(f"   Followers: {followers:,}")
            else:  # tracks
                name = item.get('name', 'Unknown')
                artist = item.get('artist', 'Unknown')
                album = item.get('album', 'Unknown')
                popularity = item.get('popularity', 0)
                
                # Format duration
                duration_ms = item.get('duration_ms', 0)
                minutes, seconds = divmod(duration_ms // 1000, 60)
                duration_str = f"{minutes}:{seconds:02d}"
                
                self.results_text.append(f"{i+1}. {name} - {artist}")
                self.results_text.append(f"   Album: {album}")
                if duration_ms > 0:
                    self.results_text.append(f"   Duration: {duration_str}")
                self.results_text.append(f"   Popularity: {popularity}/100")
            
            self.results_text.append("")
        
        self.results_text.append("-" * 50)



    def _display_bluesky_artists_as_text(self, artists):
        """
        Fallback method to display Bluesky artists as text
        
        Args:
            artists (list): List of artist dictionaries with Bluesky info
        """
        self.show_text_page()
        self.results_text.clear()
        self.results_text.append(f"Encontrados {len(artists)} artistas en Bluesky:")
        self.results_text.append("-" * 50)
        
        for i, artist in enumerate(artists):
            name = artist.get('name', 'Unknown')
            handle = artist.get('handle', '')
            url = f"https://bsky.app/profile/{handle}"
            
            # Get description if available
            description = ""
            if 'profile' in artist and isinstance(artist['profile'], dict):
                description = artist['profile'].get('description', '')
            
            # Recent posts
            posts = artist.get('posts', [])
            
            self.results_text.append(f"{i+1}. {name} (@{handle})")
            self.results_text.append(f"   URL: {url}")
            
            if description:
                self.results_text.append(f"   Descripción: {description}")
            
            if posts:
                self.results_text.append("   Posts recientes:")
                for j, post in enumerate(posts):
                    self.results_text.append(f"     - {post.get('text', '')}")
            
            self.results_text.append("")
        
        self.results_text.append("-" * 50)

   
    def show_bluesky_context_menu(self, position):
        """
        Show context menu for Bluesky artists in the table
        
        Args:
            position (QPoint): Position where the context menu was requested
        """
        table = self.parent.sender()
        if not table:
            return
        
        item = table.itemAt(position)
        if not item:
            return
        
        # Get the artist data from the item
        artist_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(artist_data, dict):
            return
        
        name = artist_data.get('name', '')
        handle = artist_data.get('handle', '')
        did = artist_data.get('did', '')
        url = artist_data.get('url', '')
        
        if not handle or not url:
            return
        
        # Create context menu
        menu = QMenu(self.parent)
        
        # Add actions
        open_profile_action = QAction(f"Abrir perfil de {name} en Bluesky", self.parent)
        open_profile_action.triggered.connect(lambda: self.utils.open_url(url))
        menu.addAction(open_profile_action)
        
        # Add follow action if we have a DID and username
        if did and self.bluesky_manager.bluesky_username:
            follow_action = QAction(f"Seguir a {name} en Bluesky", self.parent)
            follow_action.triggered.connect(lambda: self.bluesky_manager.follow_artist_on_bluesky(did, name))
            menu.addAction(follow_action)
        
        copy_url_action = QAction("Copiar URL", self.parent)
        copy_url_action.triggered.connect(lambda: self.utils.copy_to_clipboard(url))
        menu.addAction(copy_url_action)
        
        copy_handle_action = QAction("Copiar handle", self.parent)
        copy_handle_action.triggered.connect(lambda: self.utils.copy_to_clipboard(handle))
        menu.addAction(copy_handle_action)
        
        # If we have artist name, add related actions
        if name:
            menu.addSeparator()
            
            # Add Muspy actions if configured
            if hasattr(self, 'muspy_username') and self.muspy_username:
                follow_muspy_action = QAction(f"Seguir a {name} en Muspy", self.parent)
                follow_muspy_action.triggered.connect(lambda: self.muspy_manager.follow_artist_from_name(name))
                menu.addAction(follow_muspy_action)
            
            # Add Spotify actions if enabled
            if self.spotify_manager.spotify_enabled:
                follow_spotify_action = QAction(f"Seguir a {name} en Spotify", self.parent)
                follow_spotify_action.triggered.connect(lambda: self.spotify_manager.follow_artist_on_spotify_by_name(name))
                menu.addAction(follow_spotify_action)
        
        # Show menu
        menu.exec(table.mapToGlobal(position))


    def action_add_follow_to_results_page(self, artist_name):
        """
        Añade un botón para seguir al artista actual en la página de resultados
        
        Args:
            artist_name (str): Nombre del artista
        """
        # Find the muspy_results page
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("stackedWidget not found")
            return
        
        results_page = None
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget.objectName() == "muspy_results_widget":
                results_page = widget
                break
        
        if not results_page:
            self.logger.error("muspy_results_widget page not found")
            return
        
        # Buscar un botón existente o crear uno nuevo
        follow_button = results_page.findChild(QPushButton, "follow_artist_button")
        
        if not follow_button:
            self.logger.info("Creating new follow button")
            # Si no existe, buscar un layout donde añadirlo
            layout = None
            
            # Look for the button container
            button_container = results_page.findChild(QWidget, "button_container")
            if button_container:
                for child in button_container.children():
                    if isinstance(child, QVBoxLayout) or isinstance(child, QHBoxLayout):
                        layout = child
                        break
            
            # If no specific container found, look for any layout
            if not layout:
                for child in results_page.children():
                    if isinstance(child, QVBoxLayout) or isinstance(child, QHBoxLayout):
                        layout = child
                        break
            
            if layout:
                # Crear el botón
                follow_button = QPushButton(f"Seguir a {artist_name} en Muspy")
                follow_button.setObjectName("follow_artist_button")
                layout.addWidget(follow_button)
            else:
                self.logger.error("No suitable layout found in muspy_results page for follow button")
                return
        else:
            # Si ya existe, actualizar el texto
            self.logger.info(f"Updating existing follow button for {artist_name}")
            follow_button.setText(f"Seguir a {artist_name} en Muspy")
        
        # Check if this artist is already being followed
        if hasattr(self, 'current_artist') and self.current_artist and self.current_artist.get('name') == artist_name:
            # Check with the API if we're already following this artist
            if self.muspy_id and self.current_artist.get('mbid'):
                url = f"{self.base_url}/artists/{self.muspy_id}/{self.current_artist['mbid']}"
                auth = (self.muspy_username, self.muspy_api_key)
                
                try:
                    response = requests.get(url, auth=auth)
                    if response.status_code == 200:
                        # We're already following this artist
                        follow_button.setText(f"Ya sigues a {artist_name} en Muspy")
                        follow_button.setEnabled(False)
                        return
                except:
                    # If check fails, assume we're not following
                    pass
        
        # Conectar el botón a la acción
        # Disconnect any previous connections to avoid multiple triggers
        try:
            follow_button.clicked.disconnect()
        except:
            pass
        
        follow_button.clicked.connect(self.follow_current_artist)
        follow_button.setEnabled(True)



    def _display_sync_results(self, result):
        """
        Display the results of the synchronization
        
        Args:
            result (dict or list): Sync results summary
        """
        # Handle case where result is a list (from certain API calls)
        if isinstance(result, list):
            self.results_text.clear()
            self.results_text.append("Synchronization completed!\n")
            
            # Basic stats for list results
            self.results_text.append(f"Processed {len(result)} items")
            
            # Show success message
            QMessageBox.information(self, "Synchronization Complete", 
                                f"Synchronization completed successfully with {len(result)} items processed.")
            return
            
        # Continue with original dictionary-based handling
        if result and result.get('success'):
            self.results_text.clear()
            self.results_text.append("Synchronization completed successfully!\n")
            self.results_text.append(result.get('message', ""))
            
            # Show additional details if available
            if 'stats' in result:
                stats = result['stats']
                self.results_text.append(f"\nSummary:")
                self.results_text.append(f"Total artists processed: {stats.get('total', 0)}")
                self.results_text.append(f"Successfully added: {stats.get('success', 0)}")
                self.results_text.append(f"Not found (no MBID): {stats.get('no_mbid', 0)}")
                self.results_text.append(f"Failed to add: {stats.get('failed', 0)}")
            
            self.results_text.append("\nYou can now view your upcoming releases using the 'Mis próximos discos' button")
            
            # Show success message
            QMessageBox.information(self, "Synchronization Complete", result.get('message', "Synchronization successful"))
        elif result:  # Result exists but no success flag
            self.results_text.append("\nSynchronization status unclear.")
            self.results_text.append(result.get('message', "Unknown status"))
        else:
            self.results_text.append("\nSynchronization failed or returned no data.")

  


    def display_releases_tree(self, releases, group_by_artist=True):
        """
        Display releases in a tree view grouped by artist
        
        Args:
            releases (list): List of release dictionaries
            group_by_artist (bool): Whether to group by artist or not
        """
        # Clear any existing table/tree widget
        for i in reversed(range(self.layout().count())): 
            item = self.layout().itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None and (isinstance(widget, QTreeWidget) or 
                                        isinstance(widget, QTableWidget) or 
                                        (hasattr(self, 'action_add_follow') and widget == self.action_add_follow)):
                    self.layout().removeItem(item)
                    widget.deleteLater()
        
        # Create new tree widget with specific object name
        tree = QTreeWidget()
        tree.setObjectName("releases_tree")
        tree.setHeaderLabels(["Artist/Release", "Type", "Date", "Details"])
        tree.setColumnCount(4)
        tree.setAlternatingRowColors(True)
        tree.setSortingEnabled(True)
        
        # Set the size policy to make it fill available space
        tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tree.setMinimumHeight(400)  # Set minimum height to ensure visibility
        
        # Organize releases by artist if requested
        if group_by_artist:
            artists = {}
            for release in releases:
                artist_name = release.get('artist', {}).get('name', 'Unknown Artist')
                if artist_name not in artists:
                    artists[artist_name] = []
                artists[artist_name].append(release)
                
            # Create tree items
            for artist_name, artist_releases in artists.items():
                # Create parent item for artist
                artist_item = QTreeWidgetItem(tree)
                artist_item.setText(0, artist_name)
                artist_item.setText(1, "")
                artist_item.setExpanded(True)  # Expand by default
                
                # Add child items for each release
                for release in artist_releases:
                    release_item = QTreeWidgetItem(artist_item)
                    release_item.setText(0, release.get('title', 'Unknown'))
                    release_item.setText(1, release.get('type', 'Unknown').title())
                    release_item.setText(2, release.get('date', 'No date'))
                    
                    # Format details
                    details = []
                    if release.get('format'):
                        details.append(f"Format: {release.get('format')}")
                    if release.get('tracks'):
                        details.append(f"Tracks: {release.get('tracks')}")
                    release_item.setText(3, "; ".join(details) if details else "")
                    
                    # Store release data for later reference
                    release_item.setData(0, Qt.ItemDataRole.UserRole, release)
                    
                    # Color by date
                    try:
                        release_date = datetime.datetime.strptime(release.get('date', '9999-99-99'), "%Y-%m-%d").date()
                        today = datetime.date.today()
                        one_month = today + datetime.timedelta(days=30)
                        
                        if release_date <= today + datetime.timedelta(days=7):
                            # Coming very soon - red background
                            for col in range(4):
                                release_item.setBackground(col, QColor(31, 60, 28))
                        elif release_date <= one_month:
                            # Coming in a month - yellow background
                            for col in range(4):
                                release_item.setBackground(col, QColor(60, 28, 31))
                    except ValueError:
                        # Invalid date format, don't color
                        pass
        else:
            # Simple flat list
            for release in releases:
                release_item = QTreeWidgetItem(tree)
                artist_name = release.get('artist', {}).get('name', 'Unknown Artist')
                release_item.setText(0, f"{artist_name} - {release.get('title', 'Unknown')}")
                release_item.setText(1, release.get('type', 'Unknown').title())
                release_item.setText(2, release.get('date', 'No date'))
                
                # Format details
                details = []
                if release.get('format'):
                    details.append(f"Format: {release.get('format')}")
                if release.get('tracks'):
                    details.append(f"Tracks: {release.get('tracks')}")
                release_item.setText(3, "; ".join(details) if details else "")
                
                # Store release data
                release_item.setData(0, Qt.ItemDataRole.UserRole, release)
        
        # Resize columns to content
        for i in range(4):
            tree.resizeColumnToContents(i)
        
        # Connect signals
        tree.itemDoubleClicked.connect(self.on_release_double_clicked)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.show_release_context_menu)
        
        # Hide the text edit and add the tree to the layout at a specific position
        self.results_text.hide()
        
        # If we have a stacked widget, use it
        stacked_widget = self.findChild(QStackedWidget, "stackedWidget")
        if stacked_widget:
            # Find the releases page by name or add the tree to it
            releases_page = None
            for i in range(stacked_widget.count()):
                page = stacked_widget.widget(i)
                if page.objectName() == "releases_page":
                    releases_page = page
                    break
                    
            if releases_page:
                # Clear the existing layout
                if releases_page.layout():
                    while releases_page.layout().count():
                        item = releases_page.layout().takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()
                else:
                    # Create a layout if it doesn't exist
                    page_layout = QVBoxLayout(releases_page)
                    
                # Add the tree to the page
                releases_page.layout().addWidget(tree)
                
                # Switch to the releases page
                stacked_widget.setCurrentWidget(releases_page)
            else:
                # If no specific page found, add to main layout
                self.layout().insertWidget(self.layout().count() - 1, tree)
        else:
            # No stacked widget, add to main layout
            self.layout().insertWidget(self.layout().count() - 1, tree)
        
        # Store reference to tree widget
        self.tree_widget = tree
        
        return tree


    def update_status_text(self, text):
        """Update the status text in the results area"""
        self.results_text.append(text)
        QApplication.processEvents()  # Keep UI responsive



    def show_spotify_release_context_menu(self, position):
        """
        Show context menu for Spotify releases in the table
        
        Args:
            position (QPoint): Position where the context menu was requested
        """
        table = self.parent.sender()
        if not table:
            return
        
        item = table.itemAt(position)
        if not item:
            return
        
        # Get the release and artist IDs from the item
        item_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(item_data, dict):
            return
        
        release_id = item_data.get('release_id', '')
        artist_id = item_data.get('artist_id', '')
        
        if not release_id:
            return
        
        # Get the release title and artist name from the row
        row = item.row()
        artist_name = table.item(row, 0).text() if table.item(row, 0) else "Unknown"
        release_title = table.item(row, 1).text() if table.item(row, 1) else "Unknown"
        
        # Create the context menu
        menu = QMenu(self.parent)
        
        # Add actions
        view_release_action = QAction(f"View '{release_title}' on Spotify", self.parent)
        view_release_action.triggered.connect(lambda: self.utils.open_spotify_album(release_id))
        menu.addAction(view_release_action)
        
        if artist_id:
            view_artist_action = QAction(f"View artist '{artist_name}' on Spotify", self.parent)
            view_artist_action.triggered.connect(lambda: self.utilsopen_spotify_artist(artist_id))
            menu.addAction(view_artist_action)
            
            # Add action to follow artist on Muspy
            follow_muspy_action = QAction(f"Follow '{artist_name}' on Muspy", self.parent)
            follow_muspy_action.triggered.connect(lambda: self.spotify_manager.follow_spotify_artist_on_muspy(artist_id, artist_name))
            menu.addAction(follow_muspy_action)
        
        # Show the menu
        menu.exec(table.mapToGlobal(position))


    def show_spotify_track_context_menu(self, position):
        """
        Show context menu for Spotify tracks in the table
        
        Args:
            position (QPoint): Position where the context menu was requested
        """
        table = self.parent.sender()
        if not table:
            return
        
        item = table.itemAt(position)
        if not item:
            return
        
        # Get the track data from the item
        track_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(track_data, dict):
            return
        
        track_id = track_data.get('track_id', '')
        track_uri = track_data.get('track_uri', '')
        track_name = track_data.get('track_name', '')
        artist_name = track_data.get('artist_name', '')
        
        if not track_id:
            return
        
        # Create the context menu
        menu = QMenu(self.parent)
        
        # Add actions
        play_action = QAction(f"Play '{track_name}'", self.parent)
        play_action.triggered.connect(lambda: self.utils.open_spotify_uri(track_uri))
        menu.addAction(play_action)
        
        view_track_action = QAction(f"View Track on Spotify", self.parent)
        view_track_action.triggered.connect(lambda: self.utils.open_spotify_track(track_id))
        menu.addAction(view_track_action)
        
        if artist_name:
            menu.addSeparator()
            view_artist_action = QAction(f"View Artist '{artist_name}'", self.parent)
            view_artist_action.triggered.connect(lambda: self.spotify_manager.search_and_open_spotify_artist(artist_name))
            menu.addAction(view_artist_action)
            
            follow_artist_action = QAction(f"Follow Artist '{artist_name}'", self.parent)
            follow_artist_action.triggered.connect(lambda: self.spotify_manager.follow_artist_on_spotify_by_name(artist_name))
            menu.addAction(follow_artist_action)
            
            add_to_muspy_action = QAction(f"Follow '{artist_name}' on Muspy", self.parent)
            add_to_muspy_action.triggered.connect(lambda: self.muspy_manager.follow_artist_from_name(artist_name))
            menu.addAction(add_to_muspy_action)
        
        menu.addSeparator()
        
        remove_action = QAction("Remove from Saved Tracks", self.parent)
        remove_action.triggered.connect(lambda: self.spotify_manager.remove_track_from_spotify_saved(track_id, track_name))
        menu.addAction(remove_action)
        
        # Show the menu
        menu.exec(table.mapToGlobal(position))






    def set_muspy_manager(self, muspy_manager):
        self.muspy_manager = muspy_manager
    
    def set_spotify_manager(self, spotify_manager):
        self.spotify_manager = spotify_manager
    
    def set_lastfm_manager(self, lastfm_manager):
        self.lastfm_manager = lastfm_manager

    def set_bluesky_manager(self, bluesky_manager):
        self.bluesky_manager = bluesky_manager