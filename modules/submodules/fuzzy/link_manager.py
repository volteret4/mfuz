import webbrowser
from PyQt6.QtWidgets import QPushButton, QWidget
import subprocess

class LinkManager:
    """Manages external links for artists and albums."""
    
    def __init__(self, parent):
        self.parent = parent
        
        # No dependemos de la señal, conectamos los botones directamente
        # después de que la UI se inicialice completamente
        if self.parent.isVisible():
            # Si la UI ya está visible, conectamos inmediatamente
            self._connect_link_buttons()
        else:
            # Esperar al evento show para conectar los botones
            self.parent.showEvent = self._wrap_show_event(self.parent.showEvent)
    
    def _wrap_show_event(self, original_show_event):
        """Wrap the show event to connect buttons when the UI becomes visible."""
        def wrapped_show_event(event):
            # Llamar al evento original primero
            if original_show_event:
                original_show_event(event)
                
            # Conectar los botones después de que la UI sea visible
            self._connect_link_buttons()
            
        return wrapped_show_event
    
    def _connect_link_buttons(self):
        """Connect all link buttons to their handlers."""
        from PyQt6.QtWidgets import QPushButton, QWidget
        print("INICIANDO CONEXIÓN DE BOTONES DE ENLACES...")
        
        # Buscar los contenedores directamente
        artist_links_group = self.parent.findChild(QWidget, "artist_links_group")
        album_links_group = self.parent.findChild(QWidget, "album_links_group")
        
        if not artist_links_group:
            print("ERROR: No se encontró el grupo de enlaces de artistas")
        if not album_links_group:
            print("ERROR: No se encontró el grupo de enlaces de álbumes")
        
        if artist_links_group:
            # Almacenar referencia
            self.parent.artist_links_group = artist_links_group
            
            # Conectar botones
            for button in artist_links_group.findChildren(QPushButton):
                button_name = button.objectName()
                print(f"Conectando botón de artista: {button_name}")
                
                # Asegurarse de que no haya conexiones previas
                try:
                    button.clicked.disconnect()
                except:
                    pass
                
                # Conectar el botón a nuestra función simple
                button.clicked.connect(lambda *args, b=button: self._simple_open_url(b))
        
        if album_links_group:
            # Almacenar referencia
            self.parent.album_links_group = album_links_group
            
            # Conectar botones
            for button in album_links_group.findChildren(QPushButton):
                button_name = button.objectName()
                print(f"Conectando botón de álbum: {button_name}")
                
                # Asegurarse de que no haya conexiones previas
                try:
                    button.clicked.disconnect()
                except:
                    pass
                
                # Conectar el botón a nuestra función simple
                button.clicked.connect(lambda *args, b=button: self._simple_open_url(b))
    
        print("CONEXIÓN DE BOTONES COMPLETADA")
    
    def _simple_open_url(self, button):
        """Una función simple para abrir URLs que primero intenta con xdg-open en Linux."""
        try:
            url = button.property('url')
            button_name = button.objectName()
            
            print(f"BOTÓN PULSADO: {button_name}")
            print(f"ABRIENDO URL: {url}")
            
            if not url:
                print(f"ERROR: El botón {button_name} no tiene URL")
                return
            
            import platform
            system = platform.system()
            
            # Intentar primero con el método específico del sistema operativo
            try:
                if system == 'Linux':
                    # En Linux, usar xdg-open de forma no bloqueante
                    import subprocess
                    print(f"Intentando abrir con xdg-open: {url}")
                    subprocess.Popen(['xdg-open', url], 
                                start_new_session=True,
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
                    print(f"Comando xdg-open ejecutado para: {url}")
                    return
                elif system == 'Windows':
                    # En Windows, usar el comando start
                    import subprocess
                    print(f"Intentando abrir con start: {url}")
                    subprocess.Popen(f'start "" "{url}"', 
                                shell=True,
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
                    print(f"Comando start ejecutado para: {url}")
                    return
                elif system == 'Darwin':  # macOS
                    # En macOS, usar open
                    import subprocess
                    print(f"Intentando abrir con open: {url}")
                    subprocess.Popen(['open', url], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
                    print(f"Comando open ejecutado para: {url}")
                    return
            except Exception as e:
                print(f"Error con el método específico del sistema operativo: {e}")
            
            # Usar webbrowser como respaldo
            import webbrowser
            print(f"Usando webbrowser como respaldo para: {url}")
            webbrowser.open(url)
            print(f"URL abierta con webbrowser: {url}")
            
        except Exception as e:
            print(f"ERROR general al abrir URL: {e}")
            import traceback
            traceback.print_exc()


    def update_artist_links(self, artist):
        """Update artist link buttons based on available links."""
        # Hide all buttons first
        self.hide_artist_links()
        
        # Show buttons for available links
        self._show_link_if_available(artist, 'spotify_url', self.parent.spot_link_button)
        self._show_link_if_available(artist, 'youtube_url', self.parent.yt_link_button)
        self._show_link_if_available(artist, 'musicbrainz_url', self.parent.mb_link_button)
        self._show_link_if_available(artist, 'discogs_url', self.parent.discogs_link_button)
        self._show_link_if_available(artist, 'rateyourmusic_url', self.parent.rym_link_button)
        self._show_link_if_available(artist, 'wikipedia_url', self.parent.wiki_link_button)
        self._show_link_if_available(artist, 'bandcamp_url', self.parent.bc_link_button)
        self._show_link_if_available(artist, 'lastfm_url', self.parent.lastfm_link_button)
        
        # Links from artists_networks table
        self._show_link_if_available(artist, 'allmusic', self.parent.allmusic_link_button)
        self._show_link_if_available(artist, 'bandcamp', self.parent.bc_link_button)
        self._show_link_if_available(artist, 'boomkat', self.parent.boomkat_link_button)
        self._show_link_if_available(artist, 'facebook', self.parent.fb_link_button)
        self._show_link_if_available(artist, 'twitter', self.parent.twitter_link_button)
        self._show_link_if_available(artist, 'mastodon', self.parent.mastodon_link_button)
        self._show_link_if_available(artist, 'bluesky', self.parent.bluesky_link_button)
        self._show_link_if_available(artist, 'instagram', self.parent.ig_link_button)
        self._show_link_if_available(artist, 'spotify', self.parent.spot_link_button)
        self._show_link_if_available(artist, 'lastfm', self.parent.lastfm_link_button)
        self._show_link_if_available(artist, 'wikipedia', self.parent.wiki_link_button)
        self._show_link_if_available(artist, 'juno', self.parent.juno_link_button)
        self._show_link_if_available(artist, 'soundcloud', self.parent.soudcloud_link_button)
        self._show_link_if_available(artist, 'youtube', self.parent.yt_link_button)
        self._show_link_if_available(artist, 'imdb', self.parent.imdb_link_button)
        self._show_link_if_available(artist, 'progarchives', self.parent.prog_link_button)
        self._show_link_if_available(artist, 'setlist_fm', self.parent.setlist_link_button)
        self._show_link_if_available(artist, 'who_sampled', self.parent.whosampled_link_button)
        self._show_link_if_available(artist, 'vimeo', self.parent.vimeo_link_button)
        self._show_link_if_available(artist, 'resident_advisor', self.parent.ra_link_button)
        self._show_link_if_available(artist, 'rateyourmusic', self.parent.rym_link_button)
        self._show_link_if_available(artist, 'tumblr', self.parent.tumblr_link_button)
        self._show_link_if_available(artist, 'myspace', self.parent.myspace_link_button)
    
    def update_album_links(self, album):
        """Update album link buttons based on available links."""
        # Hide all buttons first
        self.hide_album_links()
        
        # Show buttons for available links
        self._show_link_if_available(album, 'spotify_url', self.parent.spot_album_link_button)
        self._show_link_if_available(album, 'youtube_url', self.parent.yt_album_link_button)
        self._show_link_if_available(album, 'musicbrainz_url', self.parent.mb_album_link_button)
        self._show_link_if_available(album, 'discogs_url', self.parent.discogs_album_link_button)
        self._show_link_if_available(album, 'rateyourmusic_url', self.parent.rym_album_link_button)
        self._show_link_if_available(album, 'wikipedia_url', self.parent.wiki_album_link_button)
        self._show_link_if_available(album, 'bandcamp_url', self.parent.bc_album_link_button)
        self._show_link_if_available(album, 'lastfm_url', self.parent.lastfm_album_link_button)
    
    def hide_all_links(self):
        """Hide all link buttons."""
        self.hide_artist_links()
        self.hide_album_links()
    
    def hide_artist_links(self):
        """Hide all artist link buttons."""
        for button in self.parent.artist_links_group.findChildren(QPushButton):
            button.setVisible(False)
    
    def hide_album_links(self):
        """Hide all album link buttons."""
        for button in self.parent.album_links_group.findChildren(QPushButton):
            button.setVisible(False)
    
    def _show_link_if_available(self, item, link_key, button):
        """Show a link button if the corresponding link is available."""
        if item and link_key in item and item[link_key]:
            url = item[link_key]
            print(f"Configurando botón {button.objectName()} con URL: {url}")
            
            # Hacer visible el botón
            button.setVisible(True)
            
            # Guardar la URL como propiedad
            button.setProperty('url', url)
            
            # Verificar que la propiedad se estableció correctamente
            stored_url = button.property('url')
            print(f"URL almacenada en el botón: {stored_url}")
            
            # También podemos añadir un tooltip para mostrar la URL cuando se pasa el mouse
            button.setToolTip(f"Abrir: {url}")
        else:
            button.setVisible(False)
            button.setProperty('url', "")  # Limpiar la propiedad
    
    def _open_artist_link(self, link_type):
        """Open the artist link in a web browser."""
        sender = self.parent.sender()
        if sender and sender.property('url'):
            url = sender.property('url')
            self._open_link(url)
    
    def _open_album_link(self, link_type):
        """Open the album link in a web browser."""
        sender = self.parent.sender()
        if sender and sender.property('url'):
            url = sender.property('url')
            self._open_link(url)


    def _open_link(self, button=None):
        """Open a link in the default browser using subprocess in non-blocking mode."""
        # Si no se proporciona botón, usar el remitente (sender)
        if button is None:
            button = self.parent.sender()
            
        url = button.property('url')
        print(f"Intentando abrir URL: {url}")
        
        if url:
            import subprocess
            import platform
            import os
            
            system = platform.system()
            print(f"Sistema operativo detectado: {system}")
            
            try:
                # Determinar el comando según el sistema operativo y ejecutar de forma no bloqueante
                if system == 'Linux':
                    print(f"Ejecutando xdg-open para URL: {url}")
                    subprocess.Popen(['xdg-open', url], 
                                start_new_session=True, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
                elif system == 'Windows':
                    print(f"Ejecutando start para URL: {url}")
                    # Usamos Popen con shell=True, que es necesario para 'start' en Windows
                    subprocess.Popen(f'start "" "{url}"', 
                                shell=True, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
                elif system == 'Darwin':
                    print(f"Ejecutando open para URL: {url}")
                    subprocess.Popen(['open', url], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
                else:
                    # Fallback para otros sistemas
                    import webbrowser
                    print(f"Sistema no detectado, usando webbrowser para: {url}")
                    webbrowser.open(url)
                    
                print(f"Comando ejecutado para abrir URL: {url}")
                
            except Exception as e:
                print(f"Error al abrir URL {url}: {e}")
                try:
                    # Último recurso: webbrowser
                    import webbrowser
                    webbrowser.open(url)
                    print(f"Usado webbrowser como fallback para: {url}")
                except Exception as e2:
                    print(f"Error final al abrir enlace: {e2}")
        else:
            print("No se encontró URL en el botón")


    def _open_link_direct(self, button):
        """Open a link directly using the provided button."""
        try:
            url = button.property('url')
            print(f"BOTÓN PULSADO: {button.objectName()}")
            print(f"Abriendo URL: {url}")
            
            if not url:
                print("ERROR: No se encontró URL en el botón")
                return
                
            import subprocess
            import platform
            
            system = platform.system()
            print(f"Sistema operativo: {system}")
            
            if system == 'Linux':
                print(f"Ejecutando: xdg-open {url}")
                # Usar Popen para no bloquear
                subprocess.Popen(['xdg-open', url], 
                            stderr=subprocess.PIPE, 
                            stdout=subprocess.PIPE, 
                            start_new_session=True)
                            
            elif system == 'Windows':
                print(f"Ejecutando: start {url}")
                subprocess.Popen(f'start "" "{url}"', 
                            shell=True, 
                            stderr=subprocess.PIPE, 
                            stdout=subprocess.PIPE)
                            
            elif system == 'Darwin':  # macOS
                print(f"Ejecutando: open {url}")
                subprocess.Popen(['open', url], 
                            stderr=subprocess.PIPE, 
                            stdout=subprocess.PIPE)
                            
            else:
                print(f"Sistema no reconocido, usando webbrowser")
                import webbrowser
                webbrowser.open(url)
                
            print(f"Comando ejecutado para URL: {url}")
        except Exception as e:
            print(f"ERROR abriendo enlace: {e}")
            import traceback
            traceback.print_exc()
            
            # Último intento con webbrowser
            try:
                import webbrowser
                webbrowser.open(url)
                print(f"Intentado abrir con webbrowser como último recurso")
            except Exception as e2:
                print(f"Error final al abrir enlace: {e2}")