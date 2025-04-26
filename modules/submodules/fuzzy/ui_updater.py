from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os
from PyQt6.QtWidgets import QLabel

class UIUpdater:
    """Updates UI elements based on selection in the tree widget."""
    
    def __init__(self, parent):
        self.parent = parent
    
    def update_artist_view(self, artist_id):
        """Update UI with artist details."""
        # Get artist details
        artist = self.parent.db_manager.get_artist_details(artist_id)
        if not artist:
            print(f"No artist found with id {artist_id}")
            return
        
        # Clear previous content (and hide all groups)
        self._clear_content()
        
        # Extract artist name for image path
        artist_name = artist.get('name', '')
        
        # Update artist image if available
        artist_image_path = self._get_artist_image_path(artist_name)
        if artist_image_path and os.path.exists(artist_image_path):
            pixmap = QPixmap(artist_image_path)
            self.parent.artist_image_label.setPixmap(pixmap.scaled(
                self.parent.artist_image_label.width(),
                self.parent.artist_image_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.parent.artist_image_label.setText("No imagen de artista")
        
        # Update Wikipedia content - only show if content exists
        if artist.get('wikipedia_content'):
            self.parent.artist_group.setVisible(True)
            if hasattr(self.parent.artist_group, 'layout'):
                label = QLabel(artist['wikipedia_content'])
                label.setWordWrap(True)
                label.setTextFormat(Qt.TextFormat.RichText)
                self.parent.artist_group.layout().addWidget(label)
        
        # Update LastFM bio - only show if content exists
        if artist.get('bio'):
            self.parent.lastfm_bio_group.setVisible(True)
            if hasattr(self.parent.lastfm_bio_group, 'layout'):
                label = QLabel(artist['bio'])
                label.setWordWrap(True)
                label.setTextFormat(Qt.TextFormat.RichText)
                self.parent.lastfm_bio_group.layout().addWidget(label)
        
        # Update artist links
        self._update_artist_links(artist)
        
        # Load feeds for this artist
        self.load_artist_feeds(artist_id)
        
        # Show the info page by default
        if hasattr(self.parent, 'info_panel_stacked'):
            self.parent.info_panel_stacked.setCurrentWidget(self.parent.info_page)
    
    def update_album_view(self, album_id):
        """Update UI with album details."""
        # Get album details
        album = self.parent.db_manager.get_album_details(album_id)
        if not album:
            print(f"No album found with id {album_id}")
            return
        
        # Get artist details for this album
        artist_id = album.get('artist_id')
        artist = None
        if artist_id:
            artist = self.parent.db_manager.get_artist_details(artist_id)
        
        # Clear previous content (and hide all groups)
        self._clear_content()
        
        # Update album cover if available
        album_art_path = album.get('album_art_path')
        if album_art_path and os.path.exists(album_art_path):
            pixmap = QPixmap(album_art_path)
            self.parent.cover_label.setPixmap(pixmap.scaled(
                self.parent.cover_label.width(),
                self.parent.cover_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.parent.cover_label.setText("No imagen")
        
        # Update artist image if available
        artist_name = artist.get('name', '') if artist else ""
        artist_image_path = self._get_artist_image_path(artist_name)
        if artist_image_path and os.path.exists(artist_image_path):
            pixmap = QPixmap(artist_image_path)
            self.parent.artist_image_label.setPixmap(pixmap.scaled(
                self.parent.artist_image_label.width(),
                self.parent.artist_image_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.parent.artist_image_label.setText("No imagen de artista")
        
        # Update Wikipedia content (album) - only show if content exists
        if album.get('wikipedia_content'):
            self.parent.album_group.setVisible(True)
            if hasattr(self.parent.album_group, 'layout'):
                label = QLabel(album['wikipedia_content'])
                label.setWordWrap(True)
                label.setTextFormat(Qt.TextFormat.RichText)
                self.parent.album_group.layout().addWidget(label)
        
        # Update Wikipedia content (artist) - only show if content exists
        if artist and artist.get('wikipedia_content'):
            self.parent.artist_group.setVisible(True)
            if hasattr(self.parent.artist_group, 'layout'):
                label = QLabel(artist['wikipedia_content'])
                label.setWordWrap(True)
                label.setTextFormat(Qt.TextFormat.RichText)
                self.parent.artist_group.layout().addWidget(label)
        
        # Update LastFM bio - only show if content exists
        if artist and artist.get('bio'):
            self.parent.lastfm_bio_group.setVisible(True)
            if hasattr(self.parent.lastfm_bio_group, 'layout'):
                label = QLabel(artist['bio'])
                label.setWordWrap(True)
                label.setTextFormat(Qt.TextFormat.RichText)
                self.parent.lastfm_bio_group.layout().addWidget(label)
        
        # Update album links
        self._update_album_links(album)
        
        # Update artist links if available
        if artist:
            self._update_artist_links(artist)
    
    def update_song_view(self, song_id):
        """Update UI with song details."""
        # Get song details
        song = self.parent.db_manager.get_song_details(song_id)
        if not song:
            return
        
        # Clear previous content (and hide all groups)
        self._clear_content()
        
        # Check if 'lyrics' is in the song object
        has_lyrics = False
        try:
            # This works for sqlite3.Row objects or dictionaries
            if (hasattr(song, 'keys') and 'lyrics' in song.keys() and song['lyrics']) or \
            (isinstance(song, dict) and 'lyrics' in song and song['lyrics']):
                has_lyrics = True
                lyrics_text = song['lyrics']
        except (AttributeError, TypeError):
            has_lyrics = False
        
        # Update lyrics if available
        if has_lyrics:
            self.parent.lyrics_group.setVisible(True)
            self.parent.lyrics_label.setText(lyrics_text)
        
        # Update album cover if available
        album_art_path = None
        try:
            if (hasattr(song, 'keys') and 'album_art_path_denorm' in song.keys() and song['album_art_path_denorm']) or \
            (isinstance(song, dict) and 'album_art_path_denorm' in song and song['album_art_path_denorm']):
                album_art_path = song['album_art_path_denorm']
        except (AttributeError, TypeError):
            pass
        
        if album_art_path and os.path.exists(album_art_path):
            pixmap = QPixmap(album_art_path)
            self.parent.cover_label.setPixmap(pixmap.scaled(
                self.parent.cover_label.width(),
                self.parent.cover_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.parent.cover_label.setText("No imagen")
        
        # Try to get artist and album information
        artist_name = None
        album_name = None
        try:
            if hasattr(song, 'keys'):
                if 'artist' in song.keys():
                    artist_name = song['artist']
                if 'album' in song.keys():
                    album_name = song['album']
            elif isinstance(song, dict):
                artist_name = song.get('artist')
                album_name = song.get('album')
        except (AttributeError, TypeError):
            pass
        
        # If we have artist name, try to get artist details
        if artist_name:
            # Get artist ID from database
            conn = self.parent.db_manager._get_connection()
            artist_id = None
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM artists WHERE name = ?", (artist_name,))
                    result = cursor.fetchone()
                    if result:
                        artist_id = result['id']
                except Exception as e:
                    print(f"Error getting artist ID: {e}")
                finally:
                    conn.close()
            
            # If we found the artist ID, update artist view
            if artist_id:
                # Update artist image
                artist_image_path = self._get_artist_image_path(artist_name)
                if artist_image_path and os.path.exists(artist_image_path):
                    pixmap = QPixmap(artist_image_path)
                    self.parent.artist_image_label.setPixmap(pixmap.scaled(
                        self.parent.artist_image_label.width(),
                        self.parent.artist_image_label.height(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                else:
                    self.parent.artist_image_label.setText("No imagen de artista")
                
                # Get artist details
                artist = self.parent.db_manager.get_artist_details(artist_id)
                if artist:
                    # Update Wikipedia content - only show if content exists
                    if 'wikipedia_content' in artist and artist['wikipedia_content']:
                        self.parent.artist_group.setVisible(True)
                        if hasattr(self.parent.artist_group, 'layout'):
                            label = QLabel(artist['wikipedia_content'])
                            label.setWordWrap(True)
                            label.setTextFormat(Qt.TextFormat.RichText)
                            self.parent.artist_group.layout().addWidget(label)
                    
                    # Update LastFM bio - only show if content exists
                    if 'bio' in artist and artist['bio']:
                        self.parent.lastfm_bio_group.setVisible(True)
                        if hasattr(self.parent.lastfm_bio_group, 'layout'):
                            label = QLabel(artist['bio'])
                            label.setWordWrap(True)
                            label.setTextFormat(Qt.TextFormat.RichText)
                            self.parent.lastfm_bio_group.layout().addWidget(label)
                    
                    # Update artist links
                    self._update_artist_links(artist)
    
    def _clear_content(self):
        """Clear previous content from UI and hide all groups."""
        # Reset images
        if hasattr(self.parent, 'cover_label') and self.parent.cover_label:
            try:
                self.parent.cover_label.setText("No imagen")
            except RuntimeError:
                print("Warning: cover_label ya no es válido")
        
        if hasattr(self.parent, 'artist_image_label') and self.parent.artist_image_label:
            try:
                self.parent.artist_image_label.setText("No imagen de artista")
            except RuntimeError:
                print("Warning: artist_image_label ya no es válido")
        
        # Verificar y limpiar con seguridad los group boxes
        self._safely_clear_group_box('artist_group')
        self._safely_clear_group_box('album_group')
        self._safely_clear_group_box('lastfm_bio_group')
        self._safely_clear_group_box('lyrics_group')
        self._safely_clear_group_box('feeds_groupbox')  # Also clear the feeds group box
        
        # Ocultar todos los grupos de forma segura
        self._safely_set_visible('artist_group', False)
        self._safely_set_visible('album_group', False)
        self._safely_set_visible('lastfm_bio_group', False)
        self._safely_set_visible('lyrics_group', False)
        
        # Resetear lyrics con seguridad
        if hasattr(self.parent, 'lyrics_label') and self.parent.lyrics_label:
            try:
                self.parent.lyrics_label.setText("")
            except RuntimeError:
                print("Warning: lyrics_label ya no es válido")
        
        # Ocultar todos los botones de enlaces con seguridad
        if hasattr(self.parent, 'link_manager') and self.parent.link_manager:
            try:
                self.parent.link_manager.hide_all_links()
            except RuntimeError:
                print("Warning: No se pueden ocultar los enlaces")

    def _safely_clear_group_box(self, group_name):
        """Limpiar un group box de forma segura."""
        if hasattr(self.parent, group_name):
            group_box = getattr(self.parent, group_name)
            if group_box:
                try:
                    if hasattr(group_box, 'layout') and group_box.layout():
                        layout = group_box.layout()
                        # Remover todos los items del layout
                        while layout.count():
                            item = layout.takeAt(0)
                            widget = item.widget()
                            if widget:
                                try:
                                    widget.deleteLater()
                                except RuntimeError:
                                    pass
                except RuntimeError:
                    print(f"Warning: {group_name} ya no es válido")

    def _safely_set_visible(self, widget_name, visible):
        """Establecer la visibilidad de un widget de forma segura."""
        if hasattr(self.parent, widget_name):
            widget = getattr(self.parent, widget_name)
            if widget:
                try:
                    widget.setVisible(visible)
                except RuntimeError:
                    print(f"Warning: No se puede establecer la visibilidad de {widget_name}")
    
    def _clear_group_box(self, group_box):
        """Clear all widgets from a group box layout."""
        if hasattr(group_box, 'layout'):
            layout = group_box.layout()
            if layout:
                # Remove all items from the layout
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
    
    def _get_artist_image_path(self, artist_name):
        """Get the path to the artist's image."""
        # This is a placeholder - implement according to your image storage strategy
        # For example, you might look in a specific directory for an image file named after the artist
        base_path = os.path.join(os.path.expanduser("~"), ".local", "share", "music_app", "images", "artists")
        
        # Check for various extensions
        for ext in ['jpg', 'jpeg', 'png']:
            path = os.path.join(base_path, f"{artist_name}.{ext}")
            if os.path.exists(path):
                return path
        
        return None
    
    def _update_artist_links(self, artist):
        """Update artist link buttons based on available links."""
        self.parent.link_manager.update_artist_links(artist)
    
    def _update_album_links(self, album):
        """Update album link buttons based on available links."""
        self.parent.link_manager.update_album_links(album)

    def load_artist_feeds(self, artist_id):
        """Load and display feeds for an artist."""
        if not artist_id:
            return
        
        # Get connection to database
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            # Query feeds table for this artist
            cursor.execute("""
                SELECT id, entity_type, entity_id, post_title, post_url, content, post_date
                FROM feeds
                WHERE entity_type = 'artists' AND entity_id = ?
                ORDER BY post_date DESC
            """, (artist_id,))
            
            feeds = cursor.fetchall()
            
            # Clear existing feeds layout
            if hasattr(self.parent, 'feeds_groupbox') and self.parent.feeds_groupbox:
                # Clear existing widgets first
                if self.parent.feeds_groupbox.layout():
                    self._clear_layout(self.parent.feeds_groupbox.layout())
                else:
                    # Create layout if it doesn't exist
                    from PyQt6.QtWidgets import QVBoxLayout
                    layout = QVBoxLayout(self.parent.feeds_groupbox)
                    self.parent.feeds_groupbox.setLayout(layout)
            
            # If no feeds found, show a message
            if not feeds or len(feeds) == 0:
                from PyQt6.QtWidgets import QLabel
                no_feeds_label = QLabel("No hay feeds disponibles para este artista")
                self.parent.feeds_groupbox.layout().addWidget(no_feeds_label)
                return
            
            # Add feeds to the layout
            from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel
            from PyQt6.QtCore import Qt
            import re
            
            # Get the layout of the feeds_groupbox
            feeds_layout = self.parent.feeds_groupbox.layout()
            
            for feed in feeds:
                # Extract domain from URL
                domain = ""
                if feed['post_url']:
                    match = re.search(r'https?://(?:www\.)?([^/]+)', feed['post_url'])
                    if match:
                        domain = match.group(1)
                
                # Create a group box for each feed
                feed_box = QGroupBox(f"{feed['post_title']} - {domain}")
                feed_layout = QVBoxLayout(feed_box)
                
                # Create content label
                content_label = QLabel(feed['content'])
                content_label.setWordWrap(True)
                content_label.setTextFormat(Qt.TextFormat.RichText)
                content_label.setOpenExternalLinks(True)
                
                # Add content to feed box
                feed_layout.addWidget(content_label)
                
                # Add feed box to main layout
                feeds_layout.addWidget(feed_box)
            
            # Add stretch to push feeds to the top
            feeds_layout.addStretch()
            
        except Exception as e:
            print(f"Error loading feeds: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

    def _clear_layout(self, layout):
        """Clear all items from a layout."""
        if layout is None:
            return
        
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
            child_layout = item.layout()
            if child_layout:
                self._clear_layout(child_layout)
