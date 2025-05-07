from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os
from PyQt6.QtWidgets import QLabel, QGroupBox, QTextEdit, QPushButton, QStackedWidget, QWidget, QSizePolicy
from pathlib import Path


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
        # This is a placeholder - implement according to your image storage strategy
        # For example, you might look in a specific directory for an image file named after the artist
        base_path = Path(os.path.expanduser("~"), ".local", "share", "music_app", "images", "artists")
        
        # Check for various extensions
        for ext in ['jpg', 'jpeg', 'png']:
            path = Path(base_path, f"{artist_name}.{ext}")
            if os.path.exists(path):
                return path
        
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
            
            # Actualizar los tres grupos de feeds
            self._update_feed_group('artistas', artist_feeds)
            self._update_feed_group('albums', album_feeds)
            self._update_feed_group('menciones', mention_feeds)
            
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

    def _update_feed_group(self, group_type, feeds):
        """Update a specific feed group with content."""
        # Encontrar el grupo, texto y etiqueta apropiados
        group_box = None
        text_edit = None
        label = None
        
        if group_type == 'artistas':
            group_box = self.parent.findChild(QGroupBox, "groupBox_artists")
            text_edit = self.parent.findChild(QTextEdit, "artistas_textEdit")
            label = self.parent.findChild(QLabel, "artistas_label")
        elif group_type == 'albums':
            group_box = self.parent.findChild(QGroupBox, "groupBox_albums")
            text_edit = self.parent.findChild(QTextEdit, "albums_textEdit")
            label = self.parent.findChild(QLabel, "albums_label")
        elif group_type == 'menciones':
            group_box = self.parent.findChild(QGroupBox, "groupBox_menciones")
            text_edit = self.parent.findChild(QTextEdit, "menciones_textEdit")
            label = self.parent.findChild(QLabel, "menciones_label")
        
        if not group_box or not text_edit:
            print(f"No se pudieron encontrar los elementos UI para el tipo de grupo: {group_type}")
            return
        
        # Limpiar contenido existente
        text_edit.clear()
        
        # Si no se encontraron feeds, mostrar un mensaje
        if not feeds or len(feeds) == 0:
            text_edit.setHtml(f"<p>No hay feeds de {group_type} disponibles para este artista</p>")
            if label:
                label.setText(f"{group_type.capitalize()} (0)")
            group_box.setTitle(f"{group_type.capitalize()} (0)")
            return
        
        # Actualizar la etiqueta con el recuento
        if label:
            label.setText(f"{group_type.capitalize()} ({len(feeds)})")
        
        # Actualizar el título del group box
        group_box.setTitle(f"{group_type.capitalize()} ({len(feeds)})")
        
        # Construir el contenido HTML para los feeds
        html_content = ""
        
        for feed in feeds:
            title = feed['post_title'] if 'post_title' in feed.keys() and feed['post_title'] else "Sin título"
            url = feed['post_url'] if 'post_url' in feed.keys() and feed['post_url'] else "#"
            content = feed['content'] if 'content' in feed.keys() and feed['content'] else "Sin contenido"
            post_date = feed['post_date'] if 'post_date' in feed.keys() and feed['post_date'] else ""
            feed_name = feed['feed_name'] if 'feed_name' in feed.keys() and feed['feed_name'] else "Fuente desconocida"
            
            # Extraer dominio de la URL para mostrar
            domain = ""
            import re
            if url and url != "#":
                match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                if match:
                    domain = match.group(1)
            
            # Formatear la entrada del feed como HTML
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
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget_feeds")
        
        if artists_button and albums_button and menciones_button and stack_widget:
            # Verificar si ya están conectados
            if hasattr(self, '_feed_buttons_connected') and self._feed_buttons_connected:
                return
            
            # Conectar cada botón a su página correspondiente
            artists_button.clicked.connect(lambda: stack_widget.setCurrentIndex(0))
            albums_button.clicked.connect(lambda: stack_widget.setCurrentIndex(1))
            menciones_button.clicked.connect(lambda: stack_widget.setCurrentIndex(2))
            
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


