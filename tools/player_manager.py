import os
import json
import subprocess
import time
import platform
import socket
from pathlib import Path
from PyQt6.QtCore import QProcess, QObject, pyqtSignal, QTimer
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import PROJECT_ROOT

class PlayerManager(QObject):
    """Manages different music players with a unified interface"""
    
    # Define signals
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_resumed = pyqtSignal()
    track_finished = pyqtSignal()
    playback_error = pyqtSignal(str)
    
    def __init__(self, config=None, parent=None, logger=None):
        self.parent = parent
        self._logger = logger or (lambda msg: print(f"[PlayerManager] {msg}"))
        super().__init__(parent)
        
        # Default settings
        self.current_player = None
        self.player_process = None
        self.is_playing = False
        self.socket_path = None
        self.config = config or {}
        
        # Try to load configuration if not provided
        if not self.config:
            self.load_config()
            
        # Set up the selected player based on configuration
        self.setup_player()
    
    def load_config(self):
        """Load player configuration from config file"""
        try:
            # Try to find the project root
            project_root = PROJECT_ROOT
            config_path = Path(project_root, "config", "config.yml")
            
            if os.path.exists(config_path):
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f)
                    
                # Extract player configuration
                if 'music_players' in full_config:
                    self.config = full_config['music_players']
                    self._logger(f"Loaded player configuration from {config_path}")
            else:
                self._logger(f"Config file not found at: {config_path}")
        except Exception as e:
            self._logger(f"Error loading player configuration: {e}")
    
    def _find_project_root(self):
        """Try to find the project root directory"""
        try:
            # First check if PROJECT_ROOT is defined globally
            import sys
            for path in sys.path:
                if os.path.exists(Path(path, "base_module.py")):
                    return path
            
            # Try to navigate up from current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            max_depth = 5
            
            for _ in range(max_depth):
                if os.path.exists(Path(current_dir, "base_module.py")):
                    return current_dir
                current_dir = os.path.dirname(current_dir)
                
            # Fallback to current directory
            return os.path.dirname(os.path.abspath(__file__))
        except Exception:
            return os.path.dirname(os.path.abspath(__file__))
    
    def setup_player(self):
        """Set up player based on configuration"""
        if not self.config:
            # Default to MPV player
            self.current_player = {
                'player_name': 'mpv',
                'player_path': self._find_player_path('mpv'),
                'player_temp_dir': os.path.expanduser('~/.config/mpv/_mpv_socket'),
                'args': '--input-ipc-server={socket_path} --no-terminal --really-quiet'
            }
            self._logger("Using default MPV player configuration")
            return
        
        # Try to get selected player for url_enlaces from config
        selected_player_name = self.config.get('selected_player', {}).get('url_enlaces', 'mpv')
        
        # Find matching player in installed_players
        installed_players = self.config.get('installed_players', {})
        
        for player_key, player_config in installed_players.items():
            if player_config.get('player_name') == selected_player_name:
                self.current_player = player_config
                self._logger(f"Using configured player: {selected_player_name}")
                return
        
        # If selected player not found, use first available
        if installed_players:
            first_player = list(installed_players.values())[0]
            self.current_player = first_player
            self._logger(f"Selected player not found, using first available: {first_player.get('player_name')}")
        else:
            # Fallback to mpv
            self.current_player = {
                'player_name': 'mpv',
                'player_path': self._find_player_path('mpv'),
                'player_temp_dir': os.path.expanduser('~/.config/mpv/_mpv_socket'),
                'args': '--input-ipc-server={socket_path}'
            }
            self._logger("No player configuration found, using default MPV")
    
    def _find_player_path(self, player_name):
        """Find path to player executable"""
        try:
            # Check if the player is in the PATH
            which_cmd = 'where' if platform.system() == 'Windows' else 'which'
            result = subprocess.run([which_cmd, player_name], capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            
            # Common locations by OS
            if platform.system() == 'Windows':
                common_paths = [
                    r"C:\Program Files\mpv\mpv.exe",
                    r"C:\Program Files (x86)\mpv\mpv.exe"
                ]
            else:  # Linux/Unix
                common_paths = [
                    "/usr/bin/mpv",
                    "/usr/local/bin/mpv"
                ]
                
            for path in common_paths:
                if os.path.exists(path):
                    return path
                    
            # Return just the name and let the OS resolve it
            return player_name
        except Exception as e:
            self._logger(f"Error finding player path: {e}")
            return player_name
    
    def play(self, url_or_path):
        """Play media from the given URL or path"""
        if not self.current_player:
            self.playback_error.emit("No player configured")
            return False
        
        # Stop any current playback
        self.stop()
        
        # Get player info
        player_path = self.current_player.get('player_path')
        if not player_path:
            self.playback_error.emit("Player path not configured")
            return False
        
        # Set up socket path for IPC if player supports it
        self.socket_path = None
        if self.current_player.get('player_temp_dir'):
            temp_dir = os.path.expanduser(self.current_player['player_temp_dir'])
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
            self.socket_path = Path(temp_dir, "player_socket")
            
            # Delete existing socket file if it exists
            if os.path.exists(self.socket_path):
                try:
                    os.remove(self.socket_path)
                except:
                    pass
        
        # Build command line arguments - ORDEN CORRECTO
        args = []
        
        # Primero añadir las opciones globales antes de la URL
        if self.current_player.get('args'):
            player_args = self.current_player['args']
            # Replace placeholder with actual socket path
            if self.socket_path:
                socket_path_str = str(self.socket_path)
                player_args = player_args.replace('{socket_path}', socket_path_str)
            
            # Separar argumentos y asegurar que --no-video esté al principio
            arg_list = player_args.split()
            
            # Reorganizar para poner --no-video al principio si existe
            no_video_args = []
            other_args = []
            
            for arg in arg_list:
                if arg.startswith('--no-video') or arg.startswith('--vid=no') or arg.startswith('--force-window=no'):
                    no_video_args.append(arg)
                else:
                    other_args.append(arg)
            
            # Construir lista final: opciones de video primero, luego el resto
            args = no_video_args + other_args
        
        # Add the URL or path DESPUÉS de todas las opciones
        args.append(url_or_path)
        
        # Start the player process
        self.player_process = QProcess()
        self.player_process.readyReadStandardOutput.connect(self.handle_output)
        self.player_process.readyReadStandardError.connect(self.handle_error)
        self.player_process.finished.connect(self.handle_finished)
        
        try:
            self._logger(f"Starting player: {player_path} {' '.join(args)}")
            self.player_process.start(player_path, args)
            
            # Wait for process to start
            if self.player_process.waitForStarted(3000):
                self.is_playing = True
                self.playback_started.emit()
                return True
            else:
                error = self.player_process.errorString()
                self.playback_error.emit(f"Failed to start player: {error}")
                return False
        except Exception as e:
            self.playback_error.emit(f"Error starting player: {str(e)}")
            return False
    
    def stop(self):
        """Stop the current playback"""
        if not self.player_process:
            return
            
        if self.player_process.state() == QProcess.ProcessState.Running:
            # Try to use socket for graceful exit if available
            if self.socket_path and os.path.exists(self.socket_path):
                self.send_command({"command": ["quit"]})
                
                # Give it a moment to quit nicely
                if not self.player_process.waitForFinished(1000):
                    self.player_process.terminate()
                    
                    if not self.player_process.waitForFinished(1000):
                        self.player_process.kill()
            else:
                # No socket, terminate directly
                self.player_process.terminate()
                if not self.player_process.waitForFinished(1000):
                    self.player_process.kill()
        
        self.is_playing = False
        self.playback_stopped.emit()
    
    def pause(self):
        """Pause the current playback"""
        if not self.is_playing:
            return
            
        success = self.send_command({"command": ["cycle", "pause"]})
        
        if success:
            self.is_playing = False
            self.playback_paused.emit()
    
    def resume(self):
        """Resume the paused playback"""
        if self.is_playing:
            return
            
        success = self.send_command({"command": ["cycle", "pause"]})
        
        if success:
            self.is_playing = True
            self.playback_resumed.emit()
    
    def toggle_pause(self):
        """Toggle between play and pause"""
        if self.is_playing:
            self.pause()
        else:
            self.resume()
    
    def seek(self, offset_seconds):
        """Seek forward or backward by the specified number of seconds"""
        self.send_command({"command": ["seek", str(offset_seconds)]})
    
    def set_volume(self, volume_percent):
        """Set volume to the specified percentage (0-100)"""
        if volume_percent < 0:
            volume_percent = 0
        elif volume_percent > 100:
            volume_percent = 100
            
        self.send_command({"command": ["set", "volume", str(volume_percent)]})
    
    def send_command(self, command):
        """Send a command to the player via socket if available"""
        if not self.socket_path or not os.path.exists(self.socket_path):
            return False
        
        try:
            import json
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            # Convertir a string en caso de que sea un objeto PosixPath
            socket_path_str = str(self.socket_path)
            sock.connect(socket_path_str)
            
            command_str = json.dumps(command) + "\n"
            sock.send(command_str.encode())
            sock.close()
            
            return True
        except Exception as e:
            self._logger(f"Error sending command: {e}")
            return False
    
    def handle_output(self):
        """Handle standard output from the player process with filtering"""
        if not self.player_process:
            return
            
        data = self.player_process.readAllStandardOutput()
        output = bytes(data).decode('utf-8', errors='replace').strip()
        
        if output:
            # Filter out verbose MPV messages we don't need
            filtered_lines = []
            for line in output.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Skip common verbose messages
                skip_patterns = [
                    'AV: ',  # Audio/Video sync info
                    'V: ',   # Video frame info
                    'A: ',   # Audio frame info
                    '[ffmpeg/',  # FFmpeg verbose output
                    '[lavf]',    # libavformat messages
                    '[ao/',      # Audio output messages
                    '[vo/',      # Video output messages
                    'Cache: ',   # Cache status
                    '(+',        # Frame timing info
                    'Dropped: ', # Dropped frames
                    'FPS: ',     # FPS info
                    '[statusline]', # Status line updates
                ]
                
                # Check if line should be skipped
                should_skip = any(pattern in line for pattern in skip_patterns)
                
                if not should_skip:
                    # Only log important messages
                    important_patterns = [
                        'Playing: ',
                        'File: ',
                        'Title: ',
                        'Artist: ',
                        'Album: ',
                        'Exiting',
                        'EOF reached',
                        'Finished playback',
                    ]
                    
                    if any(pattern in line for pattern in important_patterns):
                        filtered_lines.append(line)
            
            # Only log if we have important messages
            if filtered_lines:
                self._logger(f"Player: {'; '.join(filtered_lines)}")
    
    def handle_error(self):
        """Handle standard error from the player process with filtering"""
        if not self.player_process:
            return
            
        data = self.player_process.readAllStandardError()
        error = bytes(data).decode('utf-8', errors='replace').strip()
        
        if error:
            # Filter out non-critical error messages
            filtered_errors = []
            for line in error.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Skip verbose error patterns
                skip_error_patterns = [
                    '[ffmpeg/',
                    '[lavf]',
                    '[ao/',
                    '[vo/',
                    'deprecated',
                    'Using hardware',
                    'Selected audio codec',
                    'Selected video codec',
                    'Stream #',
                    'Duration: ',
                    'encoder         :',
                    'creation_time   :',
                ]
                
                should_skip = any(pattern in line for pattern in skip_error_patterns)
                
                if not should_skip:
                    # Only care about actual errors
                    if any(keyword in line.lower() for keyword in ['error', 'failed', 'cannot', 'unable']):
                        filtered_errors.append(line)
            
            # Only log and emit signals for real errors
            if filtered_errors:
                error_msg = '; '.join(filtered_errors)
                self._logger(f"Player error: {error_msg}")
                self.playback_error.emit(error_msg)
    
    def handle_finished(self, exit_code, exit_status):
        """Handle the player process finishing"""
        self.is_playing = False
        
        if exit_code != 0:
            self.playback_error.emit(f"Player exited with code {exit_code}")
        
        # Emit track finished signal
        self.track_finished.emit()


    def create_playlist(self, urls):
        """Crear una playlist de MPV con múltiples URLs"""
        if not urls or len(urls) == 0:
            self._logger("No hay URLs para crear una playlist")
            return False
            
        try:
            # Detener cualquier reproducción actual
            self.stop()
            
            # Iniciar con la primera URL
            success = self.play(urls[0])
            
            if not success:
                self._logger("No se pudo iniciar la reproducción de la playlist")
                return False
                
            # Añadir el resto de URLs a la playlist
            for url in urls[1:]:
                self.send_command({"command": ["loadfile", url, "append-play"]})
                
            self._logger(f"Playlist creada con {len(urls)} elementos")
            return True
        except Exception as e:
            self._logger(f"Error al crear playlist: {e}")
            self.playback_error.emit(f"Error al crear playlist: {str(e)}")
            return False

    def playlist_next(self):
        """Avanzar a la siguiente pista en la playlist"""
        success = self.send_command({"command": ["playlist-next", "force"]})
        if success:
            self._logger("Avanzando a la siguiente pista en la playlist")
            return True
        else:
            self._logger("No se pudo avanzar a la siguiente pista")
            return False
            
    def playlist_prev(self):
        """Retroceder a la pista anterior en la playlist"""
        success = self.send_command({"command": ["playlist-prev", "force"]})
        if success:
            self._logger("Retrocediendo a la pista anterior en la playlist")
            return True
        else:
            self._logger("No se pudo retroceder a la pista anterior")
            return False

    def seek_random_position(self, min_percent=10, max_percent=80):
        """Buscar una posición aleatoria en la canción actual"""
        if not self.is_playing:
            self._logger("No hay reproducción activa para buscar posición")
            return False
            
        try:
            # Generar un porcentaje aleatorio entre min_percent y max_percent
            random_percent = random.uniform(min_percent, max_percent)
            
            # Enviar comando para buscar a esa posición (porcentaje)
            success = self.send_command({"command": ["seek", str(random_percent), "absolute-percent"]})
            
            if success:
                self._logger(f"Posición establecida aleatoriamente al {random_percent:.1f}%")
                return True
            else:
                self._logger("No se pudo establecer la posición aleatoria")
                return False
        except Exception as e:
            self._logger(f"Error al buscar posición aleatoria: {e}")
            return False


    def create_temp_playlist_file(self, tracks):
        """Create a temporary playlist file for MPV"""
        try:
            import tempfile
            
            # Create a temporary playlist file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.m3u8', prefix='mpv_playlist_')
            
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                
                for track in tracks:
                    # Write track info
                    title = track.get('title', 'Unknown')
                    artist = track.get('artist', 'Unknown Artist')
                    duration = track.get('duration', -1)
                    
                    f.write(f"#EXTINF:{duration},{artist} - {title}\n")
                    
                    # Write the URL/path
                    url = track.get('file_path') or track.get('url', '')
                    if url:
                        f.write(f"{url}\n")
            
            self._logger(f"Created temporary playlist: {temp_path}")
            return temp_path
            
        except Exception as e:
            self._logger(f"Error creating playlist file: {e}")
            return None

    def play_playlist_detached(self, tracks):
        """Launch MPV as an independent process with the full playlist"""
        if not tracks:
            self._logger("No tracks to play")
            return False
        
        # Create temporary playlist file
        playlist_path = self.create_temp_playlist_file(tracks)
        if not playlist_path:
            return False
        
        try:
            # Get player path
            player_path = self.current_player.get('player_path', 'mpv')
            
            # Build arguments for independent playback
            args = [
                player_path,
                '--force-window=yes',           # Always show window
                '--keep-open=yes',              # Keep open after playlist ends
                '--loop-playlist=inf',          # Loop playlist infinitely
                '--shuffle=no',                 # Don't shuffle by default
                '--volume=70',                  # Set reasonable volume
                '--title=Music Player',         # Window title
                '--geometry=800x600',           # Window size
                '--ontop=no',                   # Don't stay on top
                '--no-terminal',                # Don't show terminal output
                '--really-quiet',               # Minimize output
                playlist_path                   # The playlist file
            ]
            
            # Launch as completely independent process - FIXED
            if platform.system() == 'Windows':
                # Windows method
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                )
            else:
                # Linux/Unix method - CORREGIDO
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,     # Start in new session
                    # Removido preexec_fn que causaba el error
                )
            
            # Don't store the process reference - let it be truly independent
            self._logger(f"Launched independent MPV with {len(tracks)} tracks (PID: {process.pid})")
            
            # Schedule cleanup of temp file after a delay
            QTimer.singleShot(10000, lambda: self._cleanup_temp_file(playlist_path))  # Aumentado a 10 segundos
            
            return True
            
        except Exception as e:
            self._logger(f"Error launching independent player: {e}")
            # Clean up temp file on error
            try:
                os.unlink(playlist_path)
            except:
                pass
            return False

    def _cleanup_temp_file(self, file_path):
        """Clean up temporary playlist file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                self._logger(f"Cleaned up temporary playlist file: {file_path}")
        except Exception as e:
            self._logger(f"Error cleaning up temp file: {e}")