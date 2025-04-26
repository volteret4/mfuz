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
        self.parent.cover_label.setText("No imagen")
        self.parent.artist_image_label.setText("No imagen de artista")
        
        # Clear content from group boxes and hide them
        self._clear_group_box(self.parent.artist_group)
        self._clear_group_box(self.parent.album_group)
        self._clear_group_box(self.parent.lastfm_bio_group)
        self._clear_group_box(self.parent.lyrics_group)
        
        # Hide all groups by default
        self.parent.artist_group.setVisible(False)
        self.parent.album_group.setVisible(False)
        self.parent.lastfm_bio_group.setVisible(False)
        self.parent.lyrics_group.setVisible(False)
        
        # Reset lyrics
        self.parent.lyrics_label.setText("")
        
        # Hide all link buttons
        self.parent.link_manager.hide_all_links()
    
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