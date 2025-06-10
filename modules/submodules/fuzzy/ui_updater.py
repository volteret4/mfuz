from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os
from PyQt6.QtWidgets import (QLabel, QGroupBox, QTextEdit, QPushButton, QStackedWidget, 
                            QWidget, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView)
from pathlib import Path
import sys
import json
import webbrowser
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from base_module import PROJECT_ROOT


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

        # Load feeds specific to this album
        artist_id = album.get('artist_id') if album else None
        self.load_artist_feeds(artist_id, album_id)
    
    def update_song_view(self, song_id):
        """Update UI with song details."""
        # Importar las clases necesarias
        from PyQt6.QtWidgets import QLabel, QVBoxLayout, QGroupBox
        from PyQt6.QtCore import Qt
        
        # Get song details
        song = self.parent.db_manager.get_song_details(song_id)
        if not song:
            return
        
        # Clear previous content (and hide all groups)
        self._clear_content()
        
        # Check if 'lyrics' is in the song object
        has_lyrics = False
        lyrics_text = ""
        try:
            if hasattr(song, 'keys') and 'lyrics' in song.keys():
                lyrics_text = song['lyrics']
                has_lyrics = lyrics_text is not None and lyrics_text.strip() != ""
            elif isinstance(song, dict) and 'lyrics' in song:
                lyrics_text = song['lyrics']
                has_lyrics = lyrics_text is not None and lyrics_text.strip() != ""
        except (AttributeError, TypeError) as e:
            print(f"Error checking lyrics: {e}")
            has_lyrics = False
        
        # Update lyrics if available
        if has_lyrics:
            try:
                # Encontrar el contenedor donde irá el grupo de letras
                texto_widget = self.parent.findChild(QWidget, "texto_widget")
                if not texto_widget:
                    print("No se encontró el contenedor 'texto_widget'")
                    return
                
                # Encontrar los grupos existentes para poder insertar entre ellos
                album_links_group = self.parent.findChild(QGroupBox, "album_links_group")
                artist_group = self.parent.findChild(QGroupBox, "artist_group")
                
                # Eliminar el grupo anterior si existe
                if hasattr(self.parent, 'lyrics_group') and self.parent.lyrics_group:
                    old_group = self.parent.lyrics_group
                    if old_group.parent():
                        old_group.parent().layout().removeWidget(old_group)
                    old_group.deleteLater()
                    self.parent.lyrics_group = None
                    self.parent.lyrics_label = None
                
                # Crear un nuevo grupo de letras
                song_title = song['title'] if 'title' in song.keys() else ''
                lyrics_group = QGroupBox(f"Letra - {song_title}")
                
                # Configurar el grupo para que se expanda horizontalmente
                lyrics_group.setSizePolicy(
                    QSizePolicy.Policy.Expanding, 
                    QSizePolicy.Policy.Minimum
                )
                
                # Crear un layout para el grupo con CERO márgenes
                layout = QVBoxLayout(lyrics_group)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)
                
                # Preprocesar el texto para preservar el formato
                # Reemplazar saltos de línea con etiquetas <br>
                formatted_lyrics = lyrics_text.replace('\n', '<br>')
                
                # Crear un QLabel simple para mostrar las letras
                lyrics_label = QLabel()
                lyrics_label.setText(formatted_lyrics)
                lyrics_label.setWordWrap(True)
                lyrics_label.setTextFormat(Qt.TextFormat.RichText)
                lyrics_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                lyrics_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                
                # Configurar el label para que se expanda horizontalmente
                lyrics_label.setSizePolicy(
                    QSizePolicy.Policy.Expanding, 
                    QSizePolicy.Policy.MinimumExpanding
                )
                
                # Eliminar cualquier margen o padding interno
                lyrics_label.setStyleSheet("""
                    QLabel {
                        margin: 0;
                        padding: 0;
                        border: none;
                    }
                """)
                
                # Añadir el label al layout
                layout.addWidget(lyrics_label)
                
                # Añadir el grupo al layout del contenedor en la posición correcta
                content_layout = texto_widget.layout()
                
                # Determinar la posición para insertar
                insert_position = 0
                
                if album_links_group and artist_group:
                    # Encontrar la posición del album_links_group y del artist_group
                    for i in range(content_layout.count()):
                        item = content_layout.itemAt(i)
                        if item.widget() == album_links_group:
                            insert_position = i + 1  # Justo después del album_links_group
                            break
                
                # Insertar el grupo de letras en la posición correcta
                content_layout.insertWidget(insert_position, lyrics_group)
                
                # Guardar referencias
                self.parent.lyrics_group = lyrics_group
                self.parent.lyrics_label = lyrics_label
                
                print(f"Lyrics group added at position {insert_position}")
                
            except Exception as e:
                print(f"Error creating lyrics group: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("No lyrics to display")


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
            try:
                # Intentar obtener artist_id desde la base de datos para esta canción
                conn = self.parent.db_manager._get_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT ar.id
                            FROM songs s
                            JOIN artists ar ON s.artist = ar.name
                            WHERE s.id = ?
                        """, (song_id,))
                        result = cursor.fetchone()
                        if result:
                            artist_id = result['id']
                            # Cargar feeds para este artista
                            self.load_artist_feeds(artist_id)
                    except Exception as e:
                        print(f"Error obteniendo artist_id para cargar feeds: {e}")
                    finally:
                        conn.close()
            except Exception as e:
                print(f"Error general cargando feeds para canción: {e}")
            
            # If we found the artist ID, update artist view
            if artist_id:
                # Update artist image
                artist_image_path = self._get_artist_image_path(artist_name)
                if artist_image_path:
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
        
        # Get artist_id and album_id for this song
        artist_id = None
        album_id = None
        
        # Intentar obtener artist_id y album_id desde la base de datos
        conn = self.parent.db_manager._get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ar.id as artist_id, al.id as album_id
                    FROM songs s
                    LEFT JOIN artists ar ON s.artist = ar.name
                    LEFT JOIN albums al ON s.album = al.name AND al.artist_id = ar.id
                    WHERE s.id = ?
                """, (song_id,))
                
                result = cursor.fetchone()
                if result:
                    if 'artist_id' in result.keys():
                        artist_id = result['artist_id']
                    if 'album_id' in result.keys():
                        album_id = result['album_id']
            except Exception as e:
                print(f"Error obteniendo artist_id/album_id para song: {e}")
            finally:
                conn.close()
        
        # Cargar feeds para la canción específica
        print(f"Cargando feeds para canción id={song_id}, album_id={album_id}, artist_id={artist_id}")
        self.load_artist_feeds(artist_id=artist_id, album_id=album_id, song_id=song_id)
    
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
        
        # Resetear lyrics con seguridad - en lugar de ocultarlo, simplemente limpiar su contenido
        if hasattr(self.parent, 'lyrics_label') and self.parent.lyrics_label:
            try:
                # Limpiar el texto sin ocultar el widget
                self.parent.lyrics_label.setText("")
                
                # Opcionalmente, puedes hacer que el widget sea visualmente "invisible"
                # estableciendo su altura mínima y máxima a cero
                self.parent.lyrics_label.setMinimumHeight(0)
                self.parent.lyrics_label.setMaximumHeight(0)
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
                    print(f"Warning: No se puede establecer la visibilidad de {widget_name}, el objeto C++ subyacente ha sido eliminado")
                    # Intentar recrear el widget si es necesario
                    if widget_name == 'lyrics_group':
                        try:
                            self._ensure_lyrics_group_exists()
                        except Exception as e:
                            print(f"No se pudo recrear {widget_name}: {e}")
    
    def _ensure_lyrics_group_exists(self):
        """Asegura que el grupo de letras existe."""
        from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QWidget
        
        if not hasattr(self.parent, 'lyrics_group') or not self.parent.lyrics_group:
            # Encontrar el contenedor padre
            parent_container = self.parent.findChild(QWidget, "texto_widget")
            if not parent_container:
                return
                
            # Crear un nuevo QGroupBox para las letras
            self.parent.lyrics_group = QGroupBox("Letra", parent_container)
            layout = QVBoxLayout(self.parent.lyrics_group)
            
            # Crear un nuevo QLabel para el contenido
            self.parent.lyrics_label = QLabel("")
            layout.addWidget(self.parent.lyrics_label)
            
            # Añadir el grupo al layout del padre
            if parent_container.layout():
                parent_container.layout().addWidget(self.parent.lyrics_group)


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
        conn = self.parent.db_manager._get_connection()
        cursor = conn.cursor()
        artist_path = cursor.execute(
            """
            SELECT img
            FROM artists
            WHERE name = ?
            """,
            (artist_name, )
        )
        result = cursor.fetchone()
        img = result[0]
        conn.close()
        if img:
            print(img)
            return img

        # For example, you might look in a specific directory for an image file named after the artist
        base_path = Path(PROJECT_ROOT, ".content", "artistas_img", artist_name)
        
        # Check for various extensions
        for ext in ['jpg', 'jpeg', 'png']:
            path = Path(base_path, f"image_1.{ext}")
            print(path)
            if os.path.exists(path):
                return str(path)  # Convertir Path a string
        
        return None
    
    def _update_artist_links(self, artist):
        """Update artist link buttons based on available links."""
        self.parent.link_manager.update_artist_links(artist)
    
    def _update_album_links(self, album):
        """Update album link buttons based on available links."""
        self.parent.link_manager.update_album_links(album)

        
    def load_artist_feeds(self, artist_id, album_id=None, song_id=None):
        """Load and display feeds based on what was selected.
        
        If album_id or song_id is provided, show feeds specific to that item.
        If only artist_id is provided, show feeds for all the artist's albums.
        """
        if not artist_id and not album_id and not song_id:
            return
        
        # Get connection to database
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Variables para almacenar los feeds
            artist_feeds = []
            album_feeds = []
            mention_feeds = []
            libros_feeds = []  # NUEVO
            
            # Si tenemos un song_id, conseguimos su album_id
            if song_id and not album_id:
                try:
                    cursor.execute("""
                        SELECT album_id FROM songs
                        WHERE id = ?
                    """, (song_id,))
                    result = cursor.fetchone()
                    if result and 'album_id' in result:
                        album_id = result['album_id']
                except Exception as e:
                    print(f"Error getting album_id from song: {e}")
            
            # Determinar qué feeds cargar según lo que se haya seleccionado
            if album_id:
                # Caso 1: Si se seleccionó un álbum o canción, mostrar feeds específicos para ese álbum
                cursor.execute("""
                    SELECT f.id, f.entity_type, f.entity_id, f.post_title, f.post_url, f.content, f.post_date, f.feed_name
                    FROM feeds f
                    WHERE f.entity_type = 'album' AND f.entity_id = ?
                    ORDER BY f.post_date DESC
                """, (album_id,))
                
                album_feeds = cursor.fetchall()
                
                # También conseguimos el artist_id si no se proporcionó
                if not artist_id:
                    try:
                        cursor.execute("""
                            SELECT artist_id FROM albums
                            WHERE id = ?
                        """, (album_id,))
                        result = cursor.fetchone()
                        if result and 'artist_id' in result:
                            artist_id = result['artist_id']
                    except Exception as e:
                        print(f"Error getting artist_id from album: {e}")
            
            if artist_id:
                # Caso 2: Cargar feeds del artista
                cursor.execute("""
                    SELECT id, entity_type, entity_id, post_title, post_url, content, post_date, feed_name
                    FROM feeds
                    WHERE entity_type = 'artists' AND entity_id = ?
                    ORDER BY post_date DESC
                """, (artist_id,))
                
                artist_feeds = cursor.fetchall()
                
                # Caso 3: Si no hay album_id (es decir, se seleccionó directamente un artista),
                # cargar todos los feeds de todos los álbumes del artista
                if not album_id:
                    cursor.execute("""
                        SELECT f.id, f.entity_type, f.entity_id, f.post_title, f.post_url, f.content, f.post_date, f.feed_name
                        FROM feeds f
                        JOIN albums a ON f.entity_id = a.id 
                        WHERE f.entity_type = 'album' AND a.artist_id = ?
                        ORDER BY f.post_date DESC
                    """, (artist_id,))
                    
                    album_feeds = cursor.fetchall()
                
                # Siempre cargar menciones para el artista
                cursor.execute("""
                    SELECT f.id, f.entity_type, f.entity_id, f.post_title, f.post_url, f.content, f.post_date, f.feed_name
                    FROM feeds f
                    JOIN menciones m ON f.id = m.feed_id
                    WHERE m.artist_id = ?
                    ORDER BY f.post_date DESC
                """, (artist_id,))
                
                mention_feeds = cursor.fetchall()
                
                # NUEVO: Cargar libros para el artista
                cursor.execute("""
                    SELECT id, book_title, book_author, genre, page_count, char_count, content, updated_at
                    FROM artists_books
                    WHERE artist_id = ?
                    ORDER BY updated_at DESC
                """, (artist_id,))
                
                libros_feeds = cursor.fetchall()


                # NUEVO: Cargar setlists para el artista
                cursor.execute("""
                    SELECT id, artist_name, setlist_id, eventDate, venue_name, city_name, 
                        city_state, country_name, url, tour, sets, last_updated
                    FROM artists_setlistfm
                    WHERE artist_id = ?
                    ORDER BY eventDate DESC
                """, (artist_id,))

                conciertos_feeds = cursor.fetchall()

                # NUEVO: Cargar instrumentos para el artista
                cursor.execute("""
                    SELECT ei.id, ei.equipment_name, ei.equipment_url, ei.brand, 
                        ei.model, ei.equipment_type, ei.extraction_date,
                        ed.min_price, ed.average_price, ed.max_price, ed.price_tier,
                        ed.stores_available, ed.total_reviews, ed.review_score,
                        ed.detailed_description, ed.specifications
                    FROM equipboard_instruments ei
                    LEFT JOIN equipboard_details ed ON ei.equipment_id = ed.equipment_id
                    WHERE ei.artist_id = ?
                    ORDER BY ei.equipment_type, ei.equipment_name
                """, (artist_id,))

                instrumentos_feeds = cursor.fetchall()
            
            # Actualizar los cuatro grupos de feeds  # MODIFICADO
            self._update_feed_group('artistas', artist_feeds)
            self._update_feed_group('albums', album_feeds)
            self._update_feed_group('menciones', mention_feeds)
            self._update_feed_group('libros', libros_feeds)
            self._update_feed_group('conciertos', conciertos_feeds)
            self._update_feed_group('instrumentos', instrumentos_feeds)
            
            # Asegurarse de que la página de feeds esté disponible
            if hasattr(self.parent, 'info_panel_stacked') and self.parent.info_panel_stacked:
                if hasattr(self.parent, 'feeds_page'):
                    # Establecer la pestaña inicial de feeds a artistas o álbumes según el contexto
                    stackedWidget = self.parent.findChild(QStackedWidget, "stackedWidget_feeds")
                    if stackedWidget:
                        # Si se seleccionó un álbum, mostrar primero esa pestaña
                        if album_id and len(album_feeds) > 0:
                            stackedWidget.setCurrentIndex(1)  # Índice para álbumes
                        else:
                            stackedWidget.setCurrentIndex(0)  # Índice para artistas
                    
                    # Conectar los botones de las pestañas si no están ya conectados
                    self._connect_feed_buttons()
            
        except Exception as e:
            print(f"Error loading feeds: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()


    
    def _populate_concerts_table(self, table_widget, concerts):
        """Populate the concerts table with concert data."""
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        from PyQt6.QtCore import Qt
        from datetime import datetime
        import json
        import sys
        import os
        
        # Importar las clases personalizadas para ordenación
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from submodules.muspy.table_widgets import DateTableWidgetItem, NumericTableWidgetItem
        
        # Clear existing content
        table_widget.clear()
        
        if not concerts:
            table_widget.setRowCount(1)
            table_widget.setColumnCount(1)
            table_widget.setItem(0, 0, QTableWidgetItem("No hay conciertos disponibles"))
            return
        
        # Definir las columnas
        headers = ["Fecha", "Venue", "Ciudad", "País", "Tour", "Tracklist", "URL"]
        table_widget.setColumnCount(len(headers))
        table_widget.setHorizontalHeaderLabels(headers)
        
        # Configurar número de filas
        table_widget.setRowCount(len(concerts))
        
        # Poblar la tabla
        for row, concert in enumerate(concerts):
            # DEBUG: Imprimir el primer concierto para ver la estructura
            if row == 0:
                print(f"Estructura del concierto: {concert}")
                print(f"Tipo de concert: {type(concert)}")
            
            # Los datos vienen como tuplas, usar índices según la consulta SQL:
            # SELECT id, artist_name, setlist_id, eventDate, venue_name, city_name, 
            #        city_state, country_name, url, tour, sets, last_updated
            
            # Fecha (índice 3: eventDate)
            event_date = concert[3] if len(concert) > 3 and concert[3] else ''
            if event_date:
                try:
                    # Intentar parsear la fecha desde el formato DD-MM-YYYY al formato YYYY-MM-DD
                    parsed_date = datetime.strptime(event_date, '%d-%m-%Y')
                    formatted_date = parsed_date.strftime('%Y-%m-%d')  # Formato para ordenación
                    # Usar DateTableWidgetItem con el formato correcto para ordenación
                    date_item = DateTableWidgetItem(formatted_date, "%Y-%m-%d")
                    # Cambiar el texto mostrado al formato original pero mantener la ordenación correcta
                    date_item.setData(Qt.ItemDataRole.DisplayRole, event_date)  # Mostrar DD-MM-YYYY
                except ValueError:
                    # Si no se puede parsear, usar como texto normal
                    date_item = QTableWidgetItem(event_date)
            else:
                date_item = QTableWidgetItem("Sin fecha")
            
            # Guardar datos completos del concierto en el primer item de la fila
            # Convertir tupla a diccionario para facilitar el acceso
            concert_dict = {
                'id': concert[0],
                'artist_name': concert[1],
                'setlist_id': concert[2],
                'eventDate': concert[3],
                'venue_name': concert[4],
                'city_name': concert[5],
                'city_state': concert[6],
                'country_name': concert[7],
                'url': concert[8],
                'tour': concert[9],
                'sets': concert[10],
                'last_updated': concert[11]
            }
            date_item.setData(Qt.ItemDataRole.UserRole + 1, concert_dict)
            table_widget.setItem(row, 0, date_item)
            
            # Venue (índice 4: venue_name)
            venue_name = concert[4] if len(concert) > 4 and concert[4] else 'Venue desconocido'
            table_widget.setItem(row, 1, QTableWidgetItem(venue_name))
            
            # Ciudad (índices 5: city_name, 6: city_state)
            city_parts = []
            if len(concert) > 5 and concert[5]:  # city_name
                city_parts.append(concert[5])
            if len(concert) > 6 and concert[6]:  # city_state
                city_parts.append(concert[6])
            city = ", ".join(city_parts) if city_parts else "Ciudad desconocida"
            table_widget.setItem(row, 2, QTableWidgetItem(city))
            
            # País (índice 7: country_name)
            country = concert[7] if len(concert) > 7 and concert[7] else 'País desconocido'
            table_widget.setItem(row, 3, QTableWidgetItem(country))
            
            # Tour (índice 9: tour)
            tour = concert[9] if len(concert) > 9 and concert[9] else ''
            table_widget.setItem(row, 4, QTableWidgetItem(tour))
            
            # Tracklist (índice 10: sets)
            sets_data = concert[10] if len(concert) > 10 and concert[10] else ''
            tracklist = self._format_setlist(sets_data)
            tracklist_item = QTableWidgetItem(tracklist)
            tracklist_item.setToolTip(tracklist)  # Tooltip para ver el tracklist completo
            table_widget.setItem(row, 5, tracklist_item)
            
            # URL (índice 8: url)
            url = concert[8] if len(concert) > 8 and concert[8] else ''
            if url:
                url_item = QTableWidgetItem("Ver en setlist.fm")
                url_item.setData(Qt.ItemDataRole.UserRole, url)  # Guardar URL en los datos del item
                url_item.setToolTip(url)
            else:
                url_item = QTableWidgetItem("")
            table_widget.setItem(row, 6, url_item)
        
        # Configurar el comportamiento de la tabla
        table_widget.setSortingEnabled(True)  # Habilitar ordenación
        table_widget.setAlternatingRowColors(True)  # Filas alternas con colores diferentes
        table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)  # Seleccionar filas completas
        
        # Ajustar el ancho de las columnas
        header = table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Fecha
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Venue
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Ciudad
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # País
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Tour
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Tracklist (expandir)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # URL
        
        # Conectar doble clic para abrir URLs
        table_widget.itemDoubleClicked.connect(self._handle_concert_item_double_click)




    def _format_setlist(self, sets_data):
        """Format the setlist data into a readable string."""
        if not sets_data:
            return "Sin setlist"
        
        try:
            # Si es string JSON, parsearlo
            if isinstance(sets_data, str):
                sets_json = json.loads(sets_data)
            else:
                sets_json = sets_data
                
            if not sets_json or not isinstance(sets_json, list):
                return "Sin setlist"
            
            # Extraer canciones de todos los sets
            all_songs = []
            for set_info in sets_json:
                if isinstance(set_info, dict) and 'song' in set_info:
                    songs = set_info['song']
                    if isinstance(songs, list):
                        for song in songs:
                            if isinstance(song, dict):
                                song_name = song.get('@name', 'Canción desconocida')
                                # Verificar si es un encore
                                if set_info.get('@encore') == '1':
                                    song_name = f"(Encore) {song_name}"
                                all_songs.append(song_name)
                            elif isinstance(song, str):
                                all_songs.append(song)
                    elif isinstance(songs, dict):
                        song_name = songs.get('@name', 'Canción desconocida')
                        if set_info.get('@encore') == '1':
                            song_name = f"(Encore) {song_name}"
                        all_songs.append(song_name)
            
            if all_songs:
                # Limitar a las primeras 3 canciones para la vista de tabla
                if len(all_songs) > 3:
                    display_songs = all_songs[:3]
                    return f"{' • '.join(display_songs)} ... (+{len(all_songs)-3} más)"
                else:
                    return ' • '.join(all_songs)
            else:
                return "Sin setlist"
                
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            # Si hay error parseando, intentar mostrar como texto plano
            if isinstance(sets_data, str) and len(sets_data) > 0:
                # Truncar si es muy largo
                if len(sets_data) > 100:
                    return sets_data[:100] + "..."
                return sets_data
            return "Error en setlist"



    def _show_full_setlist_dialog(self, concert_data):
        """Show full setlist in a dialog."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel
        from PyQt6.QtCore import Qt
        
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Setlist Completo")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Información del concierto
        concert_info = f"""
        <h3>{concert_data.get('eventDate', 'Fecha desconocida')} - {concert_data.get('venue_name', 'Venue desconocido')}</h3>
        <p><strong>Ubicación:</strong> {concert_data.get('city_name', '')}, {concert_data.get('country_name', '')}</p>
        {f"<p><strong>Tour:</strong> {concert_data.get('tour', '')}</p>" if concert_data.get('tour') else ""}
        """
        
        info_label = QLabel(concert_info)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info_label)
        
        # Setlist completo
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        full_setlist = self._format_full_setlist(concert_data.get('sets', ''))
        text_edit.setHtml(full_setlist)
        
        layout.addWidget(text_edit)
        
        # Botón cerrar
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec()


    def _format_full_setlist(self, sets_data):
        """Format the complete setlist data into HTML."""
        if not sets_data:
            return "<p>Sin setlist disponible</p>"
        
        try:
            if isinstance(sets_data, str):
                sets_json = json.loads(sets_data)
            else:
                sets_json = sets_data
                
            if not sets_json or not isinstance(sets_json, list):
                return "<p>Sin setlist disponible</p>"
            
            html_content = "<h4>Setlist:</h4>"
            
            for i, set_info in enumerate(sets_json):
                if isinstance(set_info, dict) and 'song' in set_info:
                    # Determinar el tipo de set
                    if set_info.get('@encore') == '1':
                        html_content += "<h5>🎵 Encore:</h5>"
                    elif i == 0:
                        html_content += "<h5>🎵 Set Principal:</h5>"
                    else:
                        html_content += f"<h5>🎵 Set {i + 1}:</h5>"
                    
                    html_content += "<ol>"
                    
                    songs = set_info['song']
                    if isinstance(songs, list):
                        for song in songs:
                            if isinstance(song, dict):
                                song_name = song.get('@name', 'Canción desconocida')
                                # Añadir información adicional si está disponible
                                if song.get('@tape') == '1':
                                    song_name += " (Playback)"
                                html_content += f"<li>{song_name}</li>"
                            elif isinstance(song, str):
                                html_content += f"<li>{song}</li>"
                    elif isinstance(songs, dict):
                        song_name = songs.get('@name', 'Canción desconocida')
                        if songs.get('@tape') == '1':
                            song_name += " (Playback)"
                        html_content += f"<li>{song_name}</li>"
                    
                    html_content += "</ol>"
            
            return html_content
            
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            # Si hay error, mostrar como texto plano
            if isinstance(sets_data, str) and len(sets_data) > 0:
                return f"<pre>{sets_data}</pre>"
            return "<p>Error procesando setlist</p>"



    def _handle_concert_item_double_click(self, item):
        """Handle double click on concert table items."""
        from PyQt6.QtCore import Qt
        import webbrowser
        
        # Si se hace doble clic en la columna URL (columna 6)
        if item.column() == 6:
            url = item.data(Qt.ItemDataRole.UserRole)
            if url:
                try:
                    webbrowser.open(url)
                except Exception as e:
                    print(f"Error abriendo URL: {e}")
        else:
            # Para otras columnas, mostrar información detallada del setlist
            row = item.row()
            table = item.tableWidget()
            tracklist_item = table.item(row, 5)  # Columna del tracklist
            if tracklist_item:
                # Aquí podrías mostrar un diálogo con el setlist completo
                full_tracklist = tracklist_item.toolTip()
                print(f"Setlist completo: {full_tracklist}")  # Por ahora solo imprimir


    def _update_feed_group(self, group_type, feeds):
        """Update a specific feed group with content."""
        # Encontrar el widget apropiado para este grupo
        if group_type == 'artistas':
            text_edit = self.parent.findChild(QTextEdit, "artistas_textEdit")
        elif group_type == 'albums':
            text_edit = self.parent.findChild(QTextEdit, "albums_textEdit")
        elif group_type == 'menciones':
            text_edit = self.parent.findChild(QTextEdit, "menciones_textEdit")
        elif group_type == 'libros':
            text_edit = self.parent.findChild(QTextEdit, "libros_textEdit")
        elif group_type == 'conciertos':
            # Para conciertos usar QTableWidget en lugar de QTextEdit
            table_widget = self.parent.findChild(QTableWidget, "conciertos_tableWidget")
            if table_widget:
                self._populate_concerts_table(table_widget, feeds)
            else:
                print("No se encontró conciertos_tableWidget")
            return
        elif group_type == 'instrumentos':
            text_edit = self.parent.findChild(QTextEdit, "instrumentos_textEdit")
        else:
            return
        
        if not text_edit:
            print(f"No se encontró widget para {group_type}")
            return
        
        # Clear existing content
        text_edit.clear()
        
        if not feeds:
            text_edit.setPlainText(f"No hay datos de {group_type} disponibles.")
            return
        
        # Construir contenido HTML (resto del código igual para otros tipos)
        html_content = ""
        
        if group_type == 'instrumentos':  # Formatear instrumentos
            for instrumento in feeds:
                equipment_name = instrumento['equipment_name'] if 'equipment_name' in instrumento.keys() and instrumento['equipment_name'] else "Instrumento desconocido"
                brand = instrumento['brand'] if 'brand' in instrumento.keys() and instrumento['brand'] else ""
                model = instrumento['model'] if 'model' in instrumento.keys() and instrumento['model'] else ""
                equipment_type = instrumento['equipment_type'] if 'equipment_type' in instrumento.keys() and instrumento['equipment_type'] else ""
                url = instrumento['equipment_url'] if 'equipment_url' in instrumento.keys() and instrumento['equipment_url'] else "#"
                
                # Información de precios si está disponible
                price_info = ""
                if 'average_price' in instrumento.keys() and instrumento['average_price']:
                    price_info = f"Precio promedio: ${instrumento['average_price']:.2f}"
                    if 'min_price' in instrumento.keys() and instrumento['min_price']:
                        price_info += f" (${instrumento['min_price']:.2f} - ${instrumento['max_price']:.2f})"
                
                # Información de reviews
                review_info = ""
                if 'review_score' in instrumento.keys() and instrumento['review_score']:
                    review_info = f"Rating: {instrumento['review_score']:.1f}/5"
                    if 'total_reviews' in instrumento.keys() and instrumento['total_reviews']:
                        review_info += f" ({instrumento['total_reviews']} reviews)"
                
                # Descripción detallada
                description = ""
                if 'detailed_description' in instrumento.keys() and instrumento['detailed_description']:
                    description = f"<div style='margin-top: 5px;'>{instrumento['detailed_description']}</div>"
                
                html_content += f"""
                <div style="margin-bottom: 15px; border-bottom: 1px solid #ccc; padding-bottom: 10px;">
                    <h3><a href="{url}" style="text-decoration:none;">{equipment_name}</a></h3>
                    <div style="font-size:small; color:#666;">
                        {f"Marca: {brand}" if brand else ""} 
                        {f" | Modelo: {model}" if model else ""} 
                        {f" | Tipo: {equipment_type}" if equipment_type else ""}
                    </div>
                    {f"<div style='font-size:small; color:#009900;'>{price_info}</div>" if price_info else ""}
                    {f"<div style='font-size:small; color:#ff6600;'>{review_info}</div>" if review_info else ""}
                    {description}
                </div>
                """
                
        elif group_type == 'libros':  # Formatear libros
            for libro in feeds:
                title = libro['book_title'] if 'book_title' in libro.keys() and libro['book_title'] else "Título desconocido"
                author = libro['book_author'] if 'book_author' in libro.keys() and libro['book_author'] else "Autor desconocido"
                genre = libro['genre'] if 'genre' in libro.keys() and libro['genre'] else ""
                updated_at = libro['updated_at'] if 'updated_at' in libro.keys() and libro['updated_at'] else ""
                content = libro['content'] if 'content' in libro.keys() and libro['content'] else ""
                page_count = libro['page_count'] if 'page_count' in libro.keys() and libro['page_count'] else 0
                char_count = libro['char_count'] if 'char_count' in libro.keys() and libro['char_count'] else 0
                
                html_content += f"""
                <div style="margin-bottom: 15px; border-bottom: 1px solid #ccc; padding-bottom: 10px;">
                    <h3>{title} - {author}</h3>
                    <div style="font-size:small; color:#666;">
                        Género: {genre} | Páginas: {page_count} | Caracteres: {char_count} | Actualizado: {updated_at}
                    </div>
                    <div style="margin-top: 5px;">{content}</div>
                </div>
                """
        else:  # Para feeds normales (artistas, albums, menciones)
            # Mantener el código existente para los otros tipos
            for feed in feeds:
                title = feed['post_title'] if 'post_title' in feed.keys() and feed['post_title'] else "Sin título"
                url = feed['post_url'] if 'post_url' in feed.keys() and feed['post_url'] else "#"
                content = feed['content'] if 'content' in feed.keys() and feed['content'] else "Sin contenido"
                post_date = feed['post_date'] if 'post_date' in feed.keys() and feed['post_date'] else ""
                feed_name = feed['feed_name'] if 'feed_name' in feed.keys() and feed['feed_name'] else "Fuente desconocida"
                
                domain = ""
                import re
                if url and url != "#":
                    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                    if match:
                        domain = match.group(1)
                
                html_content += f"""
                <div style="margin-bottom: 15px; border-bottom: 1px solid #ccc; padding-bottom: 10px;">
                    <h3><a href="{url}" style="text-decoration:none;">{title}</a> 
                    <span style="font-size:small;">({domain})</span></h3>
                    <div style="font-size:small; color:#666;">Fuente: {feed_name} | Fecha: {post_date}</div>
                    <div style="margin-top: 5px;">{content}</div>
                </div>
                """
        
        # Actualizar el texto con contenido formateado
        text_edit.setHtml(html_content)




    def _connect_feed_buttons(self):
        """Connect the feed navigation buttons if not already connected."""
        # Encontrar los botones
        artists_button = self.parent.findChild(QPushButton, "artists_pushButton")
        albums_button = self.parent.findChild(QPushButton, "albums_pushButton")
        menciones_button = self.parent.findChild(QPushButton, "menciones_pushButton")
        libros_button = self.parent.findChild(QPushButton, "libros_pushButton")
        conciertos_button = self.parent.findChild(QPushButton, "conciertos_pushButton")  # NUEVO
        instrumentos_button = self.parent.findChild(QPushButton, "instrumentos_pushButton")  # NUEVO
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget_feeds")
        
        if (artists_button and albums_button and menciones_button and libros_button and 
            conciertos_button and instrumentos_button and stack_widget):  # MODIFICADO
            # Verificar si ya están conectados
            if hasattr(self, '_feed_buttons_connected') and self._feed_buttons_connected:
                return
            
            # Conectar cada botón a su página correspondiente
            artists_button.clicked.connect(lambda: stack_widget.setCurrentIndex(0))
            albums_button.clicked.connect(lambda: stack_widget.setCurrentIndex(1))
            menciones_button.clicked.connect(lambda: stack_widget.setCurrentIndex(2))
            libros_button.clicked.connect(lambda: stack_widget.setCurrentIndex(3))
            conciertos_button.clicked.connect(lambda: stack_widget.setCurrentIndex(4))  # NUEVO
            instrumentos_button.clicked.connect(lambda: stack_widget.setCurrentIndex(5))  # NUEVO
            
            # Marcar como conectados para evitar múltiples conexiones
            self._feed_buttons_connected = True

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


    def load_artist_setlists(self, artist_id):
        """Cargar información de conciertos/setlists para el artista."""
        if not artist_id:
            return []
        
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, artist_name, setlist_id, eventDate, venue_name, city_name, 
                    city_state, country_name, url, tour, sets, last_updated
                FROM artists_setlistfm
                WHERE artist_id = ?
                ORDER BY eventDate DESC
            """, (artist_id,))
            
            return cursor.fetchall()
        except Exception as e:
            print(f"Error loading setlists: {e}")
            return []
        finally:
            conn.close()

    def load_artist_instruments(self, artist_id):
        """Cargar información de instrumentos del artista desde equipboard."""
        if not artist_id:
            return []
        
        conn = self.parent.db_manager._get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ei.id, ei.equipment_name, ei.equipment_url, ei.brand, 
                    ei.model, ei.equipment_type, ei.extraction_date,
                    ed.min_price, ed.average_price, ed.max_price, ed.price_tier,
                    ed.stores_available, ed.total_reviews, ed.review_score,
                    ed.detailed_description, ed.specifications
                FROM equipboard_instruments ei
                LEFT JOIN equipboard_details ed ON ei.equipment_id = ed.equipment_id
                WHERE ei.artist_id = ?
                ORDER BY ei.equipment_type, ei.equipment_name
            """, (artist_id,))
            
            return cursor.fetchall()
        except Exception as e:
            print(f"Error loading instruments: {e}")
            return []
        finally:
            conn.close()