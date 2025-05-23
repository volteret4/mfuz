class ListenBrainzPlaylist:
    """
    Clase para manejar playlists de canciones en el ListenBrainzPlayer.
    Esta clase permite gestionar una lista de canciones para reproducción secuencial.
    """
    
    def __init__(self, player_manager=None, logger_func=None):
        self.player_manager = player_manager
        self.logger = logger_func or (lambda msg: print(f"[ListenBrainzPlaylist] {msg}"))
        self.urls = []
        self.current_index = -1
        self.is_playing = False
        self.repeat_mode = 'none'  # 'none', 'one', 'all'
        self.shuffle_mode = False
        self.playlist_name = "Playlist temporal"
    
    def set_player_manager(self, player_manager):
        """Establece el reproductor MPV a utilizar"""
        self.player_manager = player_manager
    
    def add(self, url, play_now=False):
        """
        Añade una URL a la playlist.
        
        Args:
            url: URL para añadir a la playlist
            play_now: Si True, comienza a reproducir inmediatamente esta URL
        
        Returns:
            Índice de la URL en la playlist
        """
        if not url:
            return -1
            
        # Añadir la URL a la lista
        self.urls.append(url)
        new_index = len(self.urls) - 1
        
        # Si es la primera URL o se pide reproducir ahora, iniciar la reproducción
        if play_now or len(self.urls) == 1:
            self.play_index(new_index)
        else:
            # Si ya estamos reproduciendo, añadir a la playlist de MPV
            if self.is_playing and self.player_manager:
                self.player_manager.send_command({
                    "command": ["loadfile", url, "append-play"]
                })
        
        return new_index
    
    def add_multiple(self, urls, play_first=False):
        """
        Añade múltiples URLs a la playlist.
        
        Args:
            urls: Lista de URLs para añadir
            play_first: Si True, comienza a reproducir la primera URL
        
        Returns:
            Número de URLs añadidas
        """
        if not urls:
            return 0
            
        # Añadir todas las URLs
        for i, url in enumerate(urls):
            if i == 0 and play_first:
                self.add(url, play_now=True)
            else:
                self.add(url, play_now=False)
        
        return len(urls)
    
    def clear(self):
        """Limpia la playlist y detiene la reproducción"""
        self.stop()
        self.urls = []
        self.current_index = -1
        self.is_playing = False
    
    def play_index(self, index):
        """
        Reproduce la URL en el índice especificado.
        
        Args:
            index: Índice de la URL a reproducir
            
        Returns:
            True si se inició la reproducción, False en caso contrario
        """
        if not self.player_manager or index < 0 or index >= len(self.urls):
            return False
            
        # Establecer el índice actual
        self.current_index = index
        url = self.urls[index]
        
        # Intentar reproducir con el reproductor
        success = self.player_manager.play(url)
        
        if success:
            self.is_playing = True
            self.logger(f"Reproduciendo URL en índice {index}: {url}")
            return True
        else:
            self.logger(f"Error al reproducir URL en índice {index}")
            return False
    
    def play(self):
        """
        Inicia o reanuda la reproducción de la playlist.
        
        Returns:
            True si se inició/reanudó la reproducción, False en caso contrario
        """
        if not self.player_manager:
            return False
            
        # Si no hay URLs, no hay nada que reproducir
        if not self.urls:
            return False
            
        # Si ya estamos reproduciendo, no hacer nada
        if self.is_playing:
            return True
            
        # Si tenemos un índice actual, reanudar desde ahí
        if self.current_index >= 0 and self.current_index < len(self.urls):
            return self.play_index(self.current_index)
            
        # Si no, comenzar desde el principio
        return self.play_index(0)
    
    def stop(self):
        """
        Detiene la reproducción.
        
        Returns:
            True si se detuvo correctamente, False en caso contrario
        """
        if not self.player_manager:
            return False
            
        if not self.is_playing:
            return True
            
        try:
            self.player_manager.stop()
            self.is_playing = False
            return True
        except Exception as e:
            self.logger(f"Error al detener reproducción: {e}")
            return False
    
    def next(self):
        """
        Avanza a la siguiente URL en la playlist.
        
        Returns:
            True si se avanzó correctamente, False en caso contrario
        """
        if not self.player_manager or not self.urls:
            return False
            
        # Calcular el siguiente índice según el modo de repetición
        next_index = self.current_index + 1
        
        if next_index >= len(self.urls):
            if self.repeat_mode == 'all':
                next_index = 0
            else:
                # Fin de la playlist
                return False
        
        # Reproducir la siguiente URL
        return self.play_index(next_index)
    
    def previous(self):
        """
        Retrocede a la URL anterior en la playlist.
        
        Returns:
            True si se retrocedió correctamente, False en caso contrario
        """
        if not self.player_manager or not self.urls:
            return False
            
        # Calcular el índice anterior
        prev_index = self.current_index - 1
        
        if prev_index < 0:
            if self.repeat_mode == 'all':
                prev_index = len(self.urls) - 1
            else:
                # Ya estamos en la primera URL
                return False
        
        # Reproducir la URL anterior
        return self.play_index(prev_index)
    
    def shuffle(self):
        """
        Activa/desactiva el modo aleatorio.
        
        Returns:
            El nuevo estado del modo aleatorio
        """
        if not self.urls:
            return False
            
        import random
        
        # Invertir el estado actual
        self.shuffle_mode = not self.shuffle_mode
        
        if self.shuffle_mode:
            # Guardar el índice actual
            current_url = self.urls[self.current_index] if self.current_index >= 0 else None
            
            # Mezclar las URLs
            random.shuffle(self.urls)
            
            # Actualizar el índice actual si estábamos reproduciendo algo
            if current_url:
                try:
                    self.current_index = self.urls.index(current_url)
                except ValueError:
                    self.current_index = 0
        
        return self.shuffle_mode
    
    def set_repeat_mode(self, mode):
        """
        Establece el modo de repetición.
        
        Args:
            mode: Modo de repetición ('none', 'one', 'all')
            
        Returns:
            El modo establecido
        """
        if mode in ['none', 'one', 'all']:
            self.repeat_mode = mode
        
        return self.repeat_mode
    
    def get_current_url(self):
        """
        Obtiene la URL actual en reproducción.
        
        Returns:
            URL actual o None si no hay reproducción
        """
        if self.current_index >= 0 and self.current_index < len(self.urls):
            return self.urls[self.current_index]
        return None
    
    def save_to_file(self, filename):
        """
        Guarda la playlist en un archivo.
        
        Args:
            filename: Ruta del archivo donde guardar
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            import json
            
            # Crear un diccionario con la información de la playlist
            playlist_data = {
                'name': self.playlist_name,
                'urls': self.urls,
                'repeat_mode': self.repeat_mode,
                'shuffle_mode': self.shuffle_mode
            }
            
            # Guardar en el archivo
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, indent=2)
                
            self.logger(f"Playlist guardada en: {filename}")
            return True
            
        except Exception as e:
            self.logger(f"Error al guardar playlist: {e}")
            return False
    
    def load_from_file(self, filename):
        """
        Carga una playlist desde un archivo.
        
        Args:
            filename: Ruta del archivo de donde cargar
            
        Returns:
            True si se cargó correctamente, False en caso contrario
        """
        try:
            import json
            
            # Leer el archivo
            with open(filename, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)
                
            # Verificar el formato
            if not isinstance(playlist_data, dict) or 'urls' not in playlist_data:
                self.logger("Formato de archivo de playlist inválido")
                return False
                
            # Cargar los datos
            self.urls = playlist_data.get('urls', [])
            self.playlist_name = playlist_data.get('name', "Playlist cargada")
            self.repeat_mode = playlist_data.get('repeat_mode', 'none')
            self.shuffle_mode = playlist_data.get('shuffle_mode', False)
            
            # Reiniciar el índice actual
            self.current_index = -1
            self.is_playing = False
            
            self.logger(f"Playlist cargada desde: {filename}")
            return True
            
        except Exception as e:
            self.logger(f"Error al cargar playlist: {e}")
            return False