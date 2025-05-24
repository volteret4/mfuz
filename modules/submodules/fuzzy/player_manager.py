import os
import subprocess
import platform
import logging
from pathlib import Path
import traceback
import random
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import PROJECT_ROOT

class PlayerManager:
    """
    Gestiona interacciones con reproductores de música, 
    con un enfoque inicial en deadbeef para Linux.
    """
    
    def __init__(self, config=None):
        """
        Inicializa el gestor de reproductores con la configuración dada.
        
        Args:
            config: Dict con la configuración del reproductor desde config.yml
        """
        self.logger = logging.getLogger(__name__)
        self.system = platform.system()  # 'Linux', 'Windows', o 'Darwin'
        self.config = config or {}
        
        # Reproductor seleccionado y configuraciones
        self.selected_player = 'deadbeef'  # Predeterminado a deadbeef
        self.player_configs = {}
        
        # Cargar configuración
        self._load_config()
        
        # Imprimir configuración final para depuración
        print(f"PlayerManager inicializado:")
        print(f"Sistema operativo: {self.system}")
        print(f"Reproductor seleccionado: {self.selected_player}")
        print(f"Configuraciones de reproductores: {list(self.player_configs.keys())}")
    
    def _load_config(self):
        """Carga la configuración del reproductor desde el dict de config."""
        print("Cargando configuración del reproductor...")
        
        if not isinstance(self.config, dict):
            print(f"ADVERTENCIA: La configuración no es un diccionario: {type(self.config)}")
            self._create_default_configs()
            return
            
        # Obtener reproductor seleccionado para el módulo actual (fuzzy)
        player_config = self.config.get('music_players', {})
        
        if not player_config:
            print("ADVERTENCIA: No se encontró la sección 'music_players' en la configuración")
            print(f"Claves disponibles en config: {self.config.keys()}")
            self._create_default_configs()
            return
            
        print(f"Configuración music_players encontrada: {player_config}")
        
        # Obtener el reproductor seleccionado
        selected_players = player_config.get('selected_player', {})
        
        if not selected_players:
            print("ADVERTENCIA: No se encontró la sección 'selected_player'")
        else:
            self.selected_player = selected_players.get('fuzzy', 'deadbeef')
        
        print(f"Reproductor seleccionado: {self.selected_player}")
        
        # Cargar configuraciones de reproductores instalados
        installed_players = player_config.get('installed_players', {})
        
        if not installed_players:
            print("ADVERTENCIA: No se encontró la sección 'installed_players'")
            self._create_default_configs()
            return
            
        print(f"Se encontraron {len(installed_players)} configuraciones de reproductores")
        
        for player_key, player_data in installed_players.items():
            player_name = player_data.get('player_name')
            if player_name:
                self.player_configs[player_name] = player_data
                print(f"Configuración cargada para {player_name}: {player_data}")
        
        # Si deadbeef no está en las configuraciones, añadirlo
        if 'deadbeef' not in self.player_configs:
            print("ADVERTENCIA: No se encontró configuración para deadbeef, creando configuración predeterminada")
            self._create_default_configs()
            
    def _create_default_configs(self):
        """Crea configuraciones predeterminadas para los reproductores."""
        print("Creando configuraciones predeterminadas para reproductores")
        
        # deadbeef predeterminado
        self.player_configs['deadbeef'] = {
            'player_name': 'deadbeef',
            'player_path': '/usr/bin/deadbeef',
            'player_temp_dir': None,
            'args': ''
        }
        
        print(f"Configuraciones predeterminadas creadas: {list(self.player_configs.keys())}")


    def setup_player(self):
        """Set up player based on configuration"""
        if not self.config:
            # Default to MPV player
            self.current_player = {
                'player_name': 'mpv',
                'player_path': self._find_player_path('mpv'),
                'player_temp_dir': os.path.expanduser(f"{PROJECT_ROOT}/.content/mpv/_mpv_socket"),
                'args': '--input-ipc-server={socket_path} --no-video'
            }
            self._logger("Using default MPV player configuration")
            return
        
        # Try to get selected player for url_enlaces from config
        selected_player_name = self.config.get('selected_player', {}).get('url_enlaces', 'mpv_no_video')
        
        # Find matching player in installed_players
        installed_players = self.config.get('installed_players', {})
        
        for player_key, player_config in installed_players.items():
            if player_config.get('player_name') == selected_player_name:
                self.current_player = player_config
                self._logger(f"Using configured player: {selected_player_name}")
                return
        
        # If selected player not found, use mpv_no_video as fallback
        for player_key, player_config in installed_players.items():
            if player_config.get('player_name') == 'mpv_no_video':
                self.current_player = player_config
                self._logger(f"Selected player not found, using mpv_no_video")
                return
        
        # Final fallback to mpv with no-video
        self.current_player = {
            'player_name': 'mpv',
            'player_path': self._find_player_path('mpv'),
            'player_temp_dir': os.path.expanduser(f"{PROJECT_ROOT}/.content/mpv/_mpv_socket"),
            'args': '--input-ipc-server={socket_path} --no-video'
        }
        self._logger("No mpv_no_video configuration found, using default MPV with --no-video")

    def _get_player_path(self, player_name=None):
        """Obtiene la ruta al ejecutable del reproductor seleccionado."""
        player_name = player_name or self.selected_player
        
        if player_name in self.player_configs:
            path = self.player_configs[player_name].get('player_path')
            if path:
                print(f"Ruta de reproductor para {player_name}: {path}")
                return path
        
        # Rutas predeterminadas
        if self.system == 'Linux':
            default_paths = {
                'deadbeef': '/usr/bin/deadbeef'
            }
        else:
            default_paths = {}
            
        path = default_paths.get(player_name)
        print(f"Usando ruta predeterminada para {player_name}: {path}")
        return path
        
    def play(self, path=None):
        """
        Reproduce un archivo o reanuda la reproducción.
        
        Args:
            path: Ruta opcional a un archivo de medios para reproducir
        
        Returns:
            bool: True si el comando fue exitoso, False en caso contrario
        """
        print(f"Comando play llamado con ruta: {path}")
        
        if not path:
            # Reanudar reproducción
            print("No se proporcionó ruta, alternando play/pause")
            return self.play_pause()
        
        # Reproducir un archivo específico
        try:
            deadbeef_path = self._get_player_path('deadbeef')
            if not os.path.exists(deadbeef_path):
                print(f"ERROR: Ejecutable deadbeef no encontrado en {deadbeef_path}")
                return False
                
            print(f"Reproduciendo con deadbeef: {path}")
            
            # Asegurarse de que path existe
            if not os.path.exists(path):
                print(f"ERROR: El archivo o carpeta no existe: {path}")
                return False
                
            # Ejecutar el comando deadbeef con la ruta
            cmd = [deadbeef_path, path]
            print(f"Ejecutando comando: {' '.join(cmd)}")
            
            subprocess.Popen(cmd, start_new_session=True)
            print("deadbeef iniciado exitosamente")
            return True
        except Exception as e:
            print(f"Error al reproducir: {e}")
            traceback.print_exc()
            return False
    
    def play_artist(self, folder_paths):
        """
        Reproduce todos los álbumes de un artista.
        
        Args:
            folder_paths: Lista de rutas de carpetas de álbumes
        
        Returns:
            bool: True si el comando fue exitoso, False en caso contrario
        """
        print(f"Reproduciendo carpetas de artista: {folder_paths}")
        
        if not folder_paths:
            print("No se proporcionaron rutas de carpetas")
            return False
            
        try:
            deadbeef_path = self._get_player_path('deadbeef')
            if not os.path.exists(deadbeef_path):
                print(f"ERROR: Ejecutable deadbeef no encontrado en {deadbeef_path}")
                return False
                
            # Verificar que las carpetas existen
            valid_paths = []
            for path in folder_paths:
                if path and os.path.exists(path):
                    valid_paths.append(path)
                elif path:
                    print(f"ADVERTENCIA: La carpeta no existe: {path}")
                else:
                    print("ADVERTENCIA: Ruta de carpeta vacía")
            
            if not valid_paths:
                print("No hay carpetas válidas para reproducir")
                return False
                
            # Ejecutar el comando deadbeef con las rutas de carpetas
            cmd = [deadbeef_path] + valid_paths
            print(f"Ejecutando comando: {' '.join(cmd)}")
            
            subprocess.Popen(cmd, start_new_session=True)
            print("deadbeef iniciado exitosamente con carpetas de artista")
            return True
        except Exception as e:
            print(f"Error al reproducir carpetas de artista: {e}")
            traceback.print_exc()
            return False
    
    def play_pause(self):
        """Alterna entre reproducir y pausar."""
        print("Comando play/pause llamado")
        
        try:
            deadbeef_path = self._get_player_path('deadbeef')
            if not os.path.exists(deadbeef_path):
                print(f"ERROR: Ejecutable deadbeef no encontrado en {deadbeef_path}")
                return False
                
            # Ejecutar el comando deadbeef --toggle-pause
            cmd = [deadbeef_path, "--toggle-pause"]
            print(f"Ejecutando comando: {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True)
            print("Comando toggle-pause enviado exitosamente")
            return True
        except Exception as e:
            print(f"Error al alternar play/pause: {e}")
            traceback.print_exc()
            return False
    
    def add_to_queue(self, paths):
        """
        Añade archivos a la cola de reproducción.
        
        Args:
            paths: Ruta o lista de rutas a los archivos de medios para añadir
        
        Returns:
            bool: True si el comando fue exitoso, False en caso contrario
        """
        print(f"Añadiendo a la cola: {paths}")
        
        # Asegurar que paths es una lista
        if isinstance(paths, str):
            paths = [paths]
            
        if not paths:
            print("No se proporcionaron rutas para encolar")
            return False
            
        try:
            deadbeef_path = self._get_player_path('deadbeef')
            if not os.path.exists(deadbeef_path):
                print(f"ERROR: Ejecutable deadbeef no encontrado en {deadbeef_path}")
                return False
                
            # Verificar que los archivos existen
            valid_paths = []
            for path in paths:
                if path and os.path.exists(path):
                    valid_paths.append(path)
                elif path:
                    print(f"ADVERTENCIA: El archivo no existe: {path}")
                else:
                    print("ADVERTENCIA: Ruta de archivo vacía")
            
            if not valid_paths:
                print("No hay archivos válidos para encolar")
                return False
                
            # Ejecutar el comando deadbeef --queue con las rutas
            cmd = [deadbeef_path, "--queue"] + valid_paths
            print(f"Ejecutando comando: {' '.join(cmd)}")
            
            # Usar subprocess.run en lugar de call para mejor manejo de errores
            subprocess.run(cmd, check=True)
            print("Archivos encolados exitosamente")
            return True
        except Exception as e:
            print(f"Error al encolar archivos: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def next_track(self):
        """Salta a la siguiente pista."""
        print("Comando next track llamado")
        
        try:
            deadbeef_path = self._get_player_path('deadbeef')
            if not os.path.exists(deadbeef_path):
                print(f"ERROR: Ejecutable deadbeef no encontrado en {deadbeef_path}")
                return False
                
            # Ejecutar el comando deadbeef --next
            cmd = [deadbeef_path, "--next"]
            print(f"Ejecutando comando: {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True)
            print("Comando next enviado exitosamente")
            return True
        except Exception as e:
            print(f"Error al saltar a la siguiente pista: {e}")
            traceback.print_exc()
            return False
    
    def previous_track(self):
        """Vuelve a la pista anterior."""
        print("Comando previous track llamado")
        
        try:
            deadbeef_path = self._get_player_path('deadbeef')
            if not os.path.exists(deadbeef_path):
                print(f"ERROR: Ejecutable deadbeef no encontrado en {deadbeef_path}")
                return False
                
            # Ejecutar el comando deadbeef --prev
            cmd = [deadbeef_path, "--prev"]
            print(f"Ejecutando comando: {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True)
            print("Comando prev enviado exitosamente")
            return True
        except Exception as e:
            print(f"Error al volver a la pista anterior: {e}")
            traceback.print_exc()
            return False
    
    def get_now_playing(self):
        """
        Obtiene la ruta del archivo que se está reproduciendo actualmente.
        
        Returns:
            str: Ruta del archivo actualmente en reproducción o None si no hay ninguno
        """
        print("Obteniendo información de la reproducción actual")
        
        try:
            deadbeef_path = self._get_player_path('deadbeef')
            if not os.path.exists(deadbeef_path):
                print(f"ERROR: Ejecutable deadbeef no encontrado en {deadbeef_path}")
                return None
                
            # Ejecutar el comando deadbeef --nowplaying-tf "%path%"
            cmd = [deadbeef_path, "--nowplaying-tf", "%path%"]
            print(f"Ejecutando comando: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            path = result.stdout.strip()
            
            if path:
                print(f"Actualmente reproduciendo: {path}")
                return path
            else:
                print("No hay nada reproduciéndose actualmente")
                return None
        except Exception as e:
            print(f"Error al obtener la información de reproducción actual: {e}")
            traceback.print_exc()
            return None

    def stop(self):
        """Detiene la reproducción."""
        print("Comando stop llamado")
        
        try:
            deadbeef_path = self._get_player_path('deadbeef')
            if not os.path.exists(deadbeef_path):
                print(f"ERROR: Ejecutable deadbeef no encontrado en {deadbeef_path}")
                return False
                
            # Ejecutar el comando deadbeef --stop
            cmd = [deadbeef_path, "--stop"]
            print(f"Ejecutando comando: {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True)
            print("Comando stop enviado exitosamente")
            return True
        except Exception as e:
            print(f"Error al detener la reproducción: {e}")
            import traceback
            traceback.print_exc()
            return False


    def get_now_playing_search_query(self):
        """
        Obtiene información de la canción que está sonando y devuelve una cadena formateada
        para usar en una búsqueda combinada.
        
        Returns:
            str: Una cadena con formato 'a:artist&t:title' o None si no hay reproducción
        """
        print("Obteniendo información de reproducción para búsqueda")
        
        try:
            deadbeef_path = self._get_player_path('deadbeef')
            if not os.path.exists(deadbeef_path):
                print(f"ERROR: Ejecutable deadbeef no encontrado en {deadbeef_path}")
                return None
                
            # Ejecutar el comando deadbeef --nowplaying-tf "%artist%-%title%"
            cmd = [deadbeef_path, "--nowplaying-tf", "%artist%-%title%-%album%"]
            print(f"Ejecutando comando: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout.strip()
            
            if not output or "-" not in output:
                print("No hay información de reproducción disponible o formato inválido")
                return None
            
            # Dividir la salida en artista y título
            parts = output.split("-", 2)  # Dividir solo en la primera ocurrencia de "-"
            if len(parts) != 3:
                print(f"Formato inesperado en la salida: {output}")
                return None
                
            artist = parts[0].strip()
            title = parts[1].strip()
            album = parts[2].strip()
            
            if not artist or not title:
                print("Artista o título vacío")
                return None
                
            # Crear la cadena de búsqueda
            search_query = f"a:{artist}&b:{album}&t:{title}"
            print(f"Cadena de búsqueda generada: {search_query}")
            
            return search_query
        except Exception as e:
            print(f"Error al obtener información para búsqueda: {e}")
            import traceback
            traceback.print_exc()
            return None