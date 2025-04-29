import os
import json
import subprocess
import time
import platform
import socket
from pathlib import Path
from PyQt6.QtCore import QProcess, QObject, pyqtSignal, QTimer

class PlayerManager(QObject):
    """Manages different music players with a unified interface"""
    
    # Define signals
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_resumed = pyqtSignal()
    track_finished = pyqtSignal()
    playback_error = pyqtSignal(str)
    
    def __init__(self, config=None, parent=None):
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
            project_root = self._find_project_root()
            config_path = os.path.join(project_root, "config", "config.yml")
            
            if os.path.exists(config_path):
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f)
                    
                # Extract player configuration
                if 'music_players' in full_config:
                    self.config = full_config['music_players']
                    print(f"Loaded player configuration from {config_path}")
            else:
                print(f"Config file not found at: {config_path}")
        except Exception as e:
            print(f"Error loading player configuration: {e}")
    
    def _find_project_root(self):
        """Try to find the project root directory"""
        try:
            # First check if PROJECT_ROOT is defined globally
            import sys
            for path in sys.path:
                if os.path.exists(os.path.join(path, "base_module.py")):
                    return path
            
            # Try to navigate up from current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            max_depth = 5
            
            for _ in range(max_depth):
                if os.path.exists(os.path.join(current_dir, "base_module.py")):
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
                'args': '--input-ipc-server={socket_path}'
            }
            print("Using default MPV player configuration")
            return
        
        # Try to get selected player for url_enlaces from config
        selected_player_name = self.config.get('selected_player', {}).get('url_enlaces', 'mpv')
        
        # Find matching player in installed_players
        installed_players = self.config.get('installed_players', {})
        
        for player_key, player_config in installed_players.items():
            if player_config.get('player_name') == selected_player_name:
                self.current_player = player_config
                print(f"Using configured player: {selected_player_name}")
                return
        
        # If selected player not found, use first available
        if installed_players:
            first_player = list(installed_players.values())[0]
            self.current_player = first_player
            print(f"Selected player not found, using first available: {first_player.get('player_name')}")
        else:
            # Fallback to mpv
            self.current_player = {
                'player_name': 'mpv',
                'player_path': self._find_player_path('mpv'),
                'player_temp_dir': os.path.expanduser('~/.config/mpv/_mpv_socket'),
                'args': '--input-ipc-server={socket_path}'
            }
            print("No player configuration found, using default MPV")
    
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
            print(f"Error finding player path: {e}")
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
            os.makedirs(temp_dir, exist_ok=True)
            self.socket_path = os.path.join(temp_dir, "player_socket")
            
            # Delete existing socket file if it exists
            if os.path.exists(self.socket_path):
                try:
                    os.remove(self.socket_path)
                except:
                    pass
        
        # Build command line arguments
        args = []
        if self.current_player.get('args'):
            player_args = self.current_player['args']
            # Replace placeholder with actual socket path
            if self.socket_path:
                player_args = player_args.replace('{socket_path}', self.socket_path)
            args = player_args.split()
        
        # Add the URL or path
        args.append(url_or_path)
        
        # Start the player process
        self.player_process = QProcess()
        self.player_process.readyReadStandardOutput.connect(self.handle_output)
        self.player_process.readyReadStandardError.connect(self.handle_error)
        self.player_process.finished.connect(self.handle_finished)
        
        try:
            print(f"Starting player: {player_path} {' '.join(args)}")
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
            sock.connect(self.socket_path)
            
            command_str = json.dumps(command) + "\n"
            sock.send(command_str.encode())
            sock.close()
            
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
    
    def handle_output(self):
        """Handle standard output from the player process"""
        if not self.player_process:
            return
            
        data = self.player_process.readAllStandardOutput()
        output = bytes(data).decode('utf-8', errors='replace').strip()
        
        if output:
            print(f"Player output: {output}")
    
    def handle_error(self):
        """Handle standard error from the player process"""
        if not self.player_process:
            return
            
        data = self.player_process.readAllStandardError()
        error = bytes(data).decode('utf-8', errors='replace').strip()
        
        if error:
            print(f"Player error: {error}")
            # Only emit error signal for significant errors, not warnings
            if "error:" in error.lower() or "failed:" in error.lower():
                self.playback_error.emit(error)
    
    def handle_finished(self, exit_code, exit_status):
        """Handle the player process finishing"""
        self.is_playing = False
        
        if exit_code != 0:
            self.playback_error.emit(f"Player exited with code {exit_code}")
        
        # Emit track finished signal
        self.track_finished.emit()