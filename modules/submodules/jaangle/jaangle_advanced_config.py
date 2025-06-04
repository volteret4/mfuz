"""
Submódulo para manejar la configuración avanzada de Jaangle
Incluye sistema de penalizaciones, premios y perfiles de jugador
"""

import json
import os
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox, QInputDialog
from PyQt6.QtCore import QObject, pyqtSignal


class JaangleAdvancedConfig(QObject):
    """
    Manejador de configuración avanzada para Jaangle
    """
    
    # Señales para notificar cambios
    config_changed = pyqtSignal()
    player_changed = pyqtSignal(str)  # Emite el nombre del jugador
    
    def __init__(self, parent=None, project_root=None):
        super().__init__(parent)
        self.parent_module = parent
        self.project_root = project_root or Path(__file__).parent.parent.parent
        
        # Directorio para configuraciones de jugadores
        self.players_dir = Path(self.project_root, "config", "jaangle", "players")
        os.makedirs(self.players_dir, exist_ok=True)
        
        # Configuración de penalizaciones/premios (en segundos)
        self.penalty_seconds = 3      # Penalización por fallar
        self.reward_seconds = 1       # Premio por acertar
        self.favorite_penalty = 10     # Multa por fallar favorita
        
        # Jugador actual
        self.current_player = None
        self.player_config = {}
        
    def get_penalty_seconds(self):
        """Obtiene los segundos de penalización por fallar."""
        return self.penalty_seconds
    
    def set_penalty_seconds(self, seconds):
        """Establece los segundos de penalización por fallar."""
        self.penalty_seconds = max(0, min(600, seconds))
        self.config_changed.emit()
    
    def get_reward_seconds(self):
        """Obtiene los segundos de premio por acertar."""
        return self.reward_seconds
    
    def set_reward_seconds(self, seconds):
        """Establece los segundos de premio por acertar."""
        self.reward_seconds = max(0, min(600, seconds))
        self.config_changed.emit()
    
    def get_favorite_penalty_seconds(self):
        """Obtiene los segundos de multa por fallar favorita."""
        return self.favorite_penalty
    
    def set_favorite_penalty_seconds(self, seconds):
        """Establece los segundos de multa por fallar favorita."""
        self.favorite_penalty = max(0, min(600, seconds))
        self.config_changed.emit()
    
    def calculate_time_adjustment(self, is_correct, is_favorite=False):
        """
        Calcula el ajuste de tiempo basado en la respuesta
        
        Args:
            is_correct (bool): Si la respuesta fue correcta
            is_favorite (bool): Si la canción es favorita
            
        Returns:
            int: Segundos a añadir (positivo) o quitar (negativo) del tiempo
        """
        if is_correct:
            return self.reward_seconds
        else:
            penalty = self.penalty_seconds
            if is_favorite:
                penalty += self.favorite_penalty
            return -penalty
    
    def is_song_favorite(self, song_id):
        """
        Verifica si una canción es favorita consultando la base de datos
        
        Args:
            song_id: ID de la canción
            
        Returns:
            bool: True si la canción es favorita
        """
        try:
            if not self.parent_module or not hasattr(self.parent_module, 'cursor'):
                return False
            
            cursor = self.parent_module.cursor
            cursor.execute("SELECT favorita FROM songs WHERE id = ?", (song_id,))
            result = cursor.fetchone()
            
            if result:
                return bool(result[0])
            return False
            
        except Exception as e:
            print(f"Error verificando si canción es favorita: {e}")
            return False
    
    def get_available_players(self):
        """
        Obtiene la lista de jugadores disponibles
        
        Returns:
            list: Lista de nombres de jugadores
        """
        try:
            players = []
            for file_path in self.players_dir.glob("*.json"):
                player_name = file_path.stem
                players.append(player_name)
            
            return sorted(players)
        except Exception as e:
            print(f"Error obteniendo jugadores: {e}")
            return []
    
    def create_new_player(self, player_name):
        """
        Crea un nuevo perfil de jugador
        
        Args:
            player_name (str): Nombre del jugador
            
        Returns:
            bool: True si se creó correctamente
        """
        try:
            if not player_name or not player_name.strip():
                return False
            
            player_name = player_name.strip()
            
            # Verificar si ya existe
            player_file = Path(self.players_dir, f"{player_name}.json")
            if player_file.exists():
                return False
            
            # Crear configuración por defecto
            default_config = {
                "player_name": player_name,
                "created_date": str(Path().absolute()),
                "hotkeys": {
                    "0": 49,  # Key_1
                    "1": 50,  # Key_2
                    "2": 51,  # Key_3
                    "3": 52,  # Key_4
                    "4": 53,  # Key_5
                    "5": 54,  # Key_6
                    "6": 55,  # Key_7
                    "7": 56,  # Key_8
                },
                "filters": {
                    "excluded_artists": [],
                    "excluded_albums": [],
                    "excluded_genres": [],
                    "excluded_folders": [],
                    "session_filters": None
                },
                "game_settings": {
                    "music_origin": "local",
                    "spotify_user": None,
                    "listenbrainz_user": None,
                    "quiz_duration_minutes": 5,
                    "song_duration_seconds": 30,
                    "pause_between_songs": 5,
                    "options_count": 4,
                    "min_song_duration": 60,
                    "start_from_beginning_chance": 0.3,
                    "avoid_last_seconds": 15
                },
                "advanced_settings": {
                    "penalty_seconds": 60,
                    "reward_seconds": 60,
                    "favorite_penalty": 60,
                    "min_font_size": 8,
                    "max_font_size": 16,
                    "show_album_art": True,
                    "show_progress_details": True,
                    "cache_size": 200,
                    "preload_songs": 5,
                    "auto_backup": False,
                    "enable_debug": False
                },
                "statistics": {
                    "games_played": 0,
                    "total_questions": 0,
                    "correct_answers": 0,
                    "accuracy": 0.0,
                    "total_time_played": 0,
                    "favorite_genre": None,
                    "last_played": None
                }
            }
            
            # Guardar archivo
            with open(player_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            print(f"Jugador '{player_name}' creado correctamente")
            return True
            
        except Exception as e:
            print(f"Error creando jugador: {e}")
            return False
    
    def load_player_config(self, player_name):
        """
        Carga la configuración de un jugador
        
        Args:
            player_name (str): Nombre del jugador
            
        Returns:
            bool: True si se cargó correctamente
        """
        try:
            if not player_name:
                return False
            
            player_file = Path(self.players_dir, f"{player_name}.json")
            if not player_file.exists():
                print(f"Archivo de jugador no encontrado: {player_file}")
                return False
            
            with open(player_file, 'r', encoding='utf-8') as f:
                self.player_config = json.load(f)
            
            self.current_player = player_name
            
            # Aplicar configuración al módulo padre
            self.apply_player_config_to_module()
            
            print(f"Configuración del jugador '{player_name}' cargada")
            # MODIFICADO: Solo emitir la señal, sin mostrar diálogo automáticamente
            self.player_changed.emit(player_name)
            return True
            
        except Exception as e:
            print(f"Error cargando configuración del jugador: {e}")
            return False
    
    def save_current_player_config(self):
        """
        Guarda la configuración actual del jugador
        
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            if not self.current_player:
                print("No hay jugador actual para guardar")
                return False
            
            # Actualizar configuración desde el módulo
            self.update_player_config_from_module()
            
            player_file = Path(self.players_dir, f"{self.current_player}.json")
            
            with open(player_file, 'w', encoding='utf-8') as f:
                json.dump(self.player_config, f, indent=2, ensure_ascii=False)
            
            print(f"Configuración del jugador '{self.current_player}' guardada")
            return True
            
        except Exception as e:
            print(f"Error guardando configuración del jugador: {e}")
            return False
    
    def apply_player_config_to_module(self):
        """Aplica la configuración del jugador al módulo principal."""
        try:
            if not self.player_config or not self.parent_module:
                return
            
            parent = self.parent_module
            
            # Aplicar hotkeys
            if "hotkeys" in self.player_config:
                from PyQt6.QtCore import Qt
                hotkeys = {}
                for option_str, key_value in self.player_config["hotkeys"].items():
                    option_index = int(option_str)
                    hotkeys[option_index] = Qt.Key(key_value)
                parent.option_hotkeys = hotkeys
            
            # Aplicar configuración de juego
            game_settings = self.player_config.get("game_settings", {})
            for key, value in game_settings.items():
                if hasattr(parent, key):
                    setattr(parent, key, value)
            
            # Aplicar configuración avanzada
            advanced_settings = self.player_config.get("advanced_settings", {})
            self.penalty_seconds = advanced_settings.get("penalty_seconds", 60)
            self.reward_seconds = advanced_settings.get("reward_seconds", 60)
            self.favorite_penalty = advanced_settings.get("favorite_penalty", 60)
            
            for key, value in advanced_settings.items():
                if hasattr(parent, key):
                    setattr(parent, key, value)
            
            # Aplicar filtros de sesión si existen
            filters = self.player_config.get("filters", {})
            if filters.get("session_filters"):
                parent.session_filters = filters["session_filters"]
            
            # Actualizar UI
            if hasattr(parent, 'update_ui_from_config'):
                parent.update_ui_from_config()
            
        except Exception as e:
            print(f"Error aplicando configuración del jugador: {e}")
    
    def update_player_config_from_module(self):
        """Actualiza la configuración del jugador desde el módulo principal."""
        try:
            if not self.player_config or not self.parent_module:
                return
            
            parent = self.parent_module
            
            # Actualizar hotkeys
            if hasattr(parent, 'option_hotkeys'):
                hotkeys = {}
                for option_index, qt_key in parent.option_hotkeys.items():
                    key_value = qt_key.value if hasattr(qt_key, 'value') else int(qt_key)
                    hotkeys[str(option_index)] = key_value
                self.player_config["hotkeys"] = hotkeys
            
            # Actualizar configuración de juego
            game_settings = self.player_config.get("game_settings", {})
            game_attributes = [
                "music_origin", "spotify_user", "listenbrainz_user",
                "quiz_duration_minutes", "song_duration_seconds", "pause_between_songs",
                "options_count", "min_song_duration", "start_from_beginning_chance",
                "avoid_last_seconds"
            ]
            
            for attr in game_attributes:
                if hasattr(parent, attr):
                    game_settings[attr] = getattr(parent, attr)
            
            # Actualizar configuración avanzada
            advanced_settings = self.player_config.get("advanced_settings", {})
            advanced_settings.update({
                "penalty_seconds": self.penalty_seconds,
                "reward_seconds": self.reward_seconds,
                "favorite_penalty": self.favorite_penalty
            })
            
            advanced_attributes = [
                "min_font_size", "max_font_size", "show_album_art", "show_progress_details",
                "cache_size", "preload_songs", "auto_backup", "enable_debug"
            ]
            
            for attr in advanced_attributes:
                if hasattr(parent, attr):
                    advanced_settings[attr] = getattr(parent, attr)
            
            # Actualizar filtros de sesión
            filters = self.player_config.get("filters", {})
            if hasattr(parent, 'session_filters'):
                filters["session_filters"] = parent.session_filters
            
        except Exception as e:
            print(f"Error actualizando configuración del jugador: {e}")
    
    def delete_player(self, player_name):
        """
        Elimina un perfil de jugador
        
        Args:
            player_name (str): Nombre del jugador a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            if not player_name:
                return False
            
            player_file = Path(self.players_dir, f"{player_name}.json")
            if not player_file.exists():
                return False
            
            player_file.unlink()
            
            # Si era el jugador actual, limpiar
            if self.current_player == player_name:
                self.current_player = None
                self.player_config = {}
            
            print(f"Jugador '{player_name}' eliminado")
            return True
            
        except Exception as e:
            print(f"Error eliminando jugador: {e}")
            return False
    
    def get_current_player(self):
        """Obtiene el nombre del jugador actual."""
        return self.current_player
    
    def get_player_statistics(self, player_name=None):
        """
        Obtiene las estadísticas de un jugador
        
        Args:
            player_name (str): Nombre del jugador (None para el actual)
            
        Returns:
            dict: Estadísticas del jugador
        """
        try:
            target_player = player_name or self.current_player
            if not target_player:
                return {}
            
            player_file = Path(self.players_dir, f"{target_player}.json")
            if not player_file.exists():
                return {}
            
            with open(player_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return config.get("statistics", {})
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def update_player_statistics(self, games_played=0, questions=0, correct=0, time_played=0):
        """
        Actualiza las estadísticas del jugador actual
        
        Args:
            games_played (int): Juegos jugados
            questions (int): Preguntas respondidas
            correct (int): Respuestas correctas
            time_played (int): Tiempo jugado en segundos
        """
        try:
            if not self.current_player or not self.player_config:
                return
            
            stats = self.player_config.get("statistics", {})
            
            # Actualizar estadísticas
            stats["games_played"] = stats.get("games_played", 0) + games_played
            stats["total_questions"] = stats.get("total_questions", 0) + questions
            stats["correct_answers"] = stats.get("correct_answers", 0) + correct
            stats["total_time_played"] = stats.get("total_time_played", 0) + time_played
            
            # Calcular precisión
            if stats["total_questions"] > 0:
                stats["accuracy"] = (stats["correct_answers"] / stats["total_questions"]) * 100
            
            # Actualizar última vez jugado
            from datetime import datetime
            stats["last_played"] = datetime.now().isoformat()
            
            self.player_config["statistics"] = stats
            
            # Guardar automáticamente
            self.save_current_player_config()
            
        except Exception as e:
            print(f"Error actualizando estadísticas: {e}")

