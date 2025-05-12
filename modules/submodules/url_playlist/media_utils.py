import os
import json
import subprocess
import time
import traceback
import socket
from pathlib import Path
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtGui import QIcon

from modules.submodules.url_playlist.playlist_manager import determine_source_from_url
from tools.player_manager import PlayerManager
# Función para reproducir a partir de un índice
def play_from_index(self, index):
    """Reproduce desde un índice específico de la playlist actual."""
    if not hasattr(self, 'current_playlist') or not self.current_playlist:
        self.log("No hay playlist actual para reproducir")
        return False
        
    if index < 0 or index >= len(self.current_playlist):
        self.log(f"Índice {index} fuera de rango (0-{len(self.current_playlist)-1})")
        return False
        
    # Obtener datos de la pista
    track_data = self.current_playlist[index]
    self.current_track_index = index
    
    # Priorizar file_path para archivos locales
    url = None
    if track_data.get('file_path') and os.path.exists(track_data['file_path']):
        url = track_data['file_path']
    else:
        url = track_data.get('url', '')
        
    if not url:
        self.log(f"No hay URL o archivo para reproducir la pista {index}")
        return False
        
    title = track_data.get('title', 'Desconocido')
    artist = track_data.get('artist', '')
    
    self.log(f"Reproduciendo: {artist} - {title} [{url}]")
    
    # Intentar reproducir usando la función del player_manager
    if hasattr(self, 'player_manager') and self.player_manager:
        result = self.player_manager.play_media(url, {"title": title, "artist": artist})
        if result:
            self.is_playing = True
            self.play_button.setIcon(QIcon(":/services/b_pause"))
            
            # Resaltar pista actual en la lista
            self.highlight_current_track()
            return True
        else:
            self.log(f"Error reproduciendo con player_manager: {url}")
            return False
    else:
        self.log("No hay player_manager disponible")
        return False



def play_single_url(self, url):
    """Reproduce una única URL o archivo local con MPV."""
    if not url:
        self.log("Error: URL/path vacío")
        return
    
    # Asegurarse de que la URL/path es un string
    if isinstance(url, dict):
        url = url.get('file_path', url.get('url', str(url)))
    url = str(url)
    
    self.log(f"Reproduciendo URL/path: {url}")
    
    # Verificar o crear directorio temporal para el socket
    if not self.mpv_temp_dir or not os.path.exists(self.mpv_temp_dir):
        try:
            import tempfile
            self.mpv_temp_dir = tempfile.mkdtemp(prefix="mpv_socket_")
            self.log(f"Directorio temporal creado o recreado: {self.mpv_temp_dir}")
        except Exception as e:
            self.log(f"Error al crear directorio temporal: {str(e)}")
            self.mpv_temp_dir = "/tmp"
    
    # Crear ruta para el socket
    socket_path = Path(self.mpv_temp_dir, "mpv_socket")
    self.mpv_socket = socket_path
    
    # Si existe un socket anterior, eliminarlo
    if os.path.exists(socket_path):
        try:
            os.remove(socket_path)
            self.log(f"Socket antiguo eliminado: {socket_path}")
        except Exception as e:
            self.log(f"Error al eliminar socket antiguo: {str(e)}")
    
    # Preparar argumentos para mpv (ventana independiente)
    mpv_args = [
        "--input-ipc-server=" + socket_path,  # Socket para controlar mpv
        "--ytdl=yes",                # Usar youtube-dl/yt-dlp para streaming
        "--ytdl-format=best",        # Mejor calidad disponible
        "--keep-open=yes",           # Mantener abierto al finalizar
    ]
    
    # Special handling for local files vs. stream URLs
    is_local_file = url.startswith(('/', '~', 'file:', 'C:', 'D:'))
    
    if is_local_file:
        self.log("Reproduciendo archivo local")
        # Make sure the file exists
        if not os.path.exists(os.path.expanduser(url.replace('file://', ''))):
            self.log(f"Advertencia: El archivo no existe: {url}")
    
    # Special handling for Bandcamp URLs
    elif "bandcamp.com" in url:
        # For Bandcamp, we might want to use specific options
        mpv_args.extend([
            "--ytdl-raw-options=yes-playlist=",  # Handle as single track even if it's an album
            "--force-window=yes",               # Force window creation
        ])
        self.log("Aplicando configuración especial para Bandcamp")
    
    # Add the URL
    mpv_args.append(url)
    
    # Registrar comando completo para depuración
    self.log(f"Comando MPV: mpv {' '.join(mpv_args)}")
    
    # Iniciar mpv para reproducir
    self.player_process = QProcess()
    self.player_process.readyReadStandardOutput.connect(self.handle_player_output)
    self.player_process.readyReadStandardError.connect(self.handle_player_error)
    self.player_process.finished.connect(self.handle_player_finished)
    
    try:
        self.player_process.start("mpv", mpv_args)
        success = self.player_process.waitForStarted(3000)  # Esperar 3 segundos máximo
        
        if success:
            self.is_playing = True
            self.play_button.setIcon(QIcon(":/services/b_pause"))
            self.log("Reproducción iniciada correctamente")
        else:
            self.log("Error al iniciar MPV: timeout")
            error = self.player_process.errorString()
            self.log(f"Error detallado: {error}")
                
    except Exception as e:
        self.log(f"Excepción al iniciar MPV: {str(e)}")

def stop_playback(self):
    """Detiene cualquier reproducción en curso."""
    if self.player_process and self.player_process.state() == QProcess.ProcessState.Running:
        self.log("Deteniendo reproducción actual...")
        
        # Intentar terminar gracefully primero
        try:
            send_mpv_command(self, {"command": ["quit"]})
            
            # Esperar un poco para que mpv se cierre por sí mismo
            if not self.player_process.waitForFinished(1000):
                self.player_process.terminate()
                
                if not self.player_process.waitForFinished(1000):
                    self.player_process.kill()
                    self.log("Forzando cierre del reproductor")
        except Exception as e:
            self.log(f"Error al detener reproducción: {str(e)}")
            # Forzar terminación en caso de error
            self.player_process.kill()
        
        self.is_playing = False
        self.play_button.setIcon(QIcon(":/services/b_play"))
        self.log("Reproducción detenida")

def send_mpv_command(self, command):
    """Envía un comando a mpv a través del socket IPC."""
    if not self.mpv_socket or not os.path.exists(self.mpv_socket):
        self.log(f"No se puede enviar comando: socket no disponible")
        return False
    
    try:
        import socket
        import json
        
        self.log(f"Enviando comando: {json.dumps(command)}")
        
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.mpv_socket)
        
        command_str = json.dumps(command) + "\n"
        sock.send(command_str.encode())
        sock.close()
        
        return True
    except Exception as e:
        self.log(f"Error enviando comando a mpv: {str(e)}")
        return False

def toggle_play_pause(parent_instance):
    """Alterna entre reproducir y pausar."""
    if not parent_instance.is_playing:
        play_media(parent_instance)
        parent_instance.play_button.setIcon(QIcon(":/services/b_pause"))
    else:
        parent_instance.pause_media()
        parent_instance.play_button.setIcon(QIcon(":/services/b_play"))

def pause_media(parent_instance):
    """Pausa la reproducción actual."""
    if parent_instance.player_process and parent_instance.player_process.state() == QProcess.ProcessState.Running:
        success = send_mpv_command(parent_instance, {"command": ["cycle", "pause"]})
        
        if success:
            parent_instance.is_playing = False
            parent_instance.play_button.setIcon(QIcon(":/services/b_play"))
            parent_instance.log("Reproducción pausada")
        else:
            parent_instance.log("Error al pausar la reproducción")

def next_track(parent_instance):
    """Reproduce la siguiente pista."""
    if not parent_instance.current_playlist:
        return
    
    next_index = parent_instance.current_track_index + 1
    if next_index >= len(parent_instance.current_playlist):
        next_index = 0  # Volver al principio si estamos al final
    
    parent_instance.log(f"Cambiando a la siguiente pista (índice {next_index})")
    play_from_index(parent_instance, next_index)

def previous_track(parent_instance):
    """Reproduce la pista anterior."""
    if not parent_instance.current_playlist:
        return
    
    prev_index = parent_instance.current_track_index - 1
    if prev_index < 0:
        prev_index = len(parent_instance.current_playlist) - 1  # Ir al final si estamos al principio
    
    parent_instance.log(f"Cambiando a la pista anterior (índice {prev_index})")
    play_from_index(parent_instance, prev_index)

def play_rss_playlist(self, playlist_data):
    """Reproduce una playlist RSS completa"""
    try:
        playlist_path = playlist_data['path']
        if not os.path.exists(playlist_path):
            self.log(f"Error: No se encuentra la playlist en {playlist_path}")
            return False
            
        # Crear y ejecutar el hilo para la reproducción
        player_thread = threading.Thread(
            target=_play_playlist_in_thread,
            args=(self, playlist_path, playlist_data)
        )
        player_thread.daemon = True
        player_thread.start()
        
        return True
    except Exception as e:
        self.log(f"Error reproduciendo playlist RSS: {str(e)}")
        return False

def _play_playlist_in_thread(self, playlist_path, playlist_data=None):
    """Método que se ejecuta en un hilo para reproducir la playlist"""
    try:
        # Construir comando mpv
        cmd = ["mpv", "--player-operation-mode=pseudo-gui", "--force-window=yes", str(playlist_path)]
        
        # Ejecutar mpv
        process = subprocess.run(cmd)
        
        # Si terminó correctamente y es una playlist RSS, preguntar si marcar como escuchada
        if process.returncode == 0 and playlist_data and 'state' in playlist_data and playlist_data['state'] == 'pending':
            # Usar señales para comunicarse con el hilo principal
            # Esta parte requiere configurar señales específicas en tu clase
            self.ask_mark_as_listened_signal.emit(playlist_data)
    except Exception as e:
        # Usar una señal para mostrar error en el hilo principal
        self.show_error_signal.emit(f"Error reproduciendo playlist: {str(e)}")

def check_dependencies(self):
    """Verifica que las dependencias necesarias estén instaladas."""
    dependencies = ['mpv', 'yt-dlp']
    missing = []
    
    for dep in dependencies:
        try:
            result = subprocess.run(['which', dep], capture_output=True, text=True)
            if result.returncode != 0:
                missing.append(dep)
        except Exception:
            missing.append(dep)
    
    if missing:
        missing_deps = ', '.join(missing)
        error_msg = f"Faltan dependencias necesarias: {missing_deps}"
        self.log(error_msg)
        QMessageBox.critical(self, "Error de dependencias", 
                            f"Faltan dependencias necesarias para ejecutar este módulo: {missing_deps}\n\n"
                            f"Por favor, instálalas con tu gestor de paquetes.")
        return False
    
    return True


# In submodules/url_playlist/media_player.py

def play_media(parent_instance):
    """Reproduce la cola actual."""
    try:
        if not parent_instance.current_playlist:
            if parent_instance.listWidget.count() == 0:
                # Si no hay nada en la cola, intentar reproducir lo seleccionado en el árbol
                parent_instance.add_to_queue()
                if not parent_instance.current_playlist:
                    QMessageBox.information(parent_instance, "Información", "No hay elementos para reproducir")
                    return
            else:
                # Reconstruir la lista de reproducción desde la lista visual
                rebuild_playlist_from_listwidget(self)
        
        # Si ya está reproduciendo, simplemente enviar comando de pausa/play
        if parent_instance.player_process and parent_instance.player_process.state() == QProcess.ProcessState.Running:
            send_mpv_command(self, {"command": ["cycle", "pause"]})
            parent_instance.is_playing = True
            parent_instance.play_button.setIcon(QIcon(":/services/b_pause"))
            return
        
        # Si tenemos un índice actual válido, reproducir desde él
        if parent_instance.current_track_index >= 0 and parent_instance.current_track_index < len(parent_instance.current_playlist):
            play_from_index(self, self.current_track_index)
        else:
            # Si no, comenzar desde el principio
            play_from_index(parent_instance, 0)
    except Exception as e:
        parent_instance.log(f"Error in play_media: {str(e)}")
        import traceback
        parent_instance.log(traceback.format_exc())

def rebuild_playlist_from_listwidget(self):
    """Rebuilds the playlist from the ListWidget, preserving icons and source information."""
    try:
        self.current_playlist = []
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            text = item.text()
            url = item.data(Qt.ItemDataRole.UserRole)
            
            # Extract artist if present in the format "Artist - Title"
            artist = ""
            title = text
            if " - " in text:
                parts = text.split(" - ", 1)
                artist = parts[0]
                title = parts[1]
            
            # Determine source from URL if not available from icon
            
            source = determine_source_from_url(url)
            
            self.current_playlist.append({
                'title': title, 
                'artist': artist, 
                'url': url,
                'source': source,
                'entry_data': None  # No full data available in this case
            })
            
        self.log(f"Playlist rebuilt with {len(self.current_playlist)} items")
    except Exception as e:
        self.log(f"Error rebuilding playlist: {str(e)}")
        import traceback
        self.log(traceback.format_exc())


def add_to_queue(parent_instance):
    """Adds the selected item to the playback queue without changing tabs."""
    selected_items = parent_instance.treeWidget.selectedItems()
    if not selected_items:
        return
    
    for item in selected_items:
        # Get the item type
        item_type = item.text(2).split(' ')[0].lower()  # Extract the basic type
        
        # Si es un álbum, preguntar si el usuario quiere añadir todas las pistas
        if item_type == "álbum":
            if item.childCount() > 0:  # Album has tracks as children
                reply = QMessageBox.question(
                    parent_instance, 
                    "Agregar Álbum", 
                    f"¿Deseas agregar todo el álbum '{item.text(0)}' a la cola?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Add all child tracks
                    for i in range(item.childCount()):
                        child = item.child(i)
                        add_item_to_queue(parent_instance, child)
                    continue  # Skip adding the album itself
        
        # If it's a parent item with children (like artist or playlist)
        elif item.childCount() > 0:
            for i in range(item.childCount()):
                child = item.child(i)
                
                add_item_to_queue(parent_instance, child)
            continue  # Skip adding the parent itself
        
        # For individual tracks or other items without special handling
        add_item_to_queue(parent_instance, item)


def remove_from_queue(parent_instance):
    """Elimina el elemento seleccionado de la cola de reproducción."""
    selected_items = parent_instance.listWidget.selectedItems()
    if not selected_items:
        return
    
    for item in selected_items:
        row = parent_instance.listWidget.row(item)
        parent_instance.listWidget.takeItem(row)
        
        # Actualizar la lista interna
        if 0 <= row < len(parent_instance.current_playlist):
            parent_instance.current_playlist.pop(row)

def play_item(self, item):
    """Play a tree widget item directly"""
    try:
        from PyQt6.QtCore import Qt
        
        # Get item data
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            self.log("No item data to play")
            return
            
        # Extract required information
        url = None
        if isinstance(item_data, dict):
            # Try file_path first for local files
            url = item_data.get('file_path')
            
            # If no file_path, try service URLs in preferred order
            if not url:
                service_priority = ['youtube', 'spotify', 'bandcamp', 'soundcloud', 'local']
                for service in service_priority:
                    service_url = item_data.get(f'{service}_url')
                    if service_url:
                        url = service_url
                        break
                        
            # Last resort: generic URL
            if not url:
                url = item_data.get('url')
        else:
            # If item_data is not a dict, assume it's the URL
            url = str(item_data)
            
        if not url:
            self.log("No playable URL found")
            return
            
        # Add to queue first
        added = add_item_to_queue(self, item)
        
        if not added:
            self.log("Failed to add item to queue")
            return
            
        # Set as current and play
        self.current_track_index = len(self.current_playlist) - 1
        
        # Play using the PlayerManager
        if hasattr(self, 'player_manager'):
            self.player_manager.play(url)
        else:
            # Fallback to old play method
            from modules.submodules.url_playlist.media_utils import play_media
            play_media(self)
        
    except Exception as e:
        self.log(f"Error playing item: {str(e)}")
        import traceback
        self.log(traceback.format_exc())


def add_to_queue(self):
    """Añade el elemento seleccionado a la cola de reproducción."""
    if not hasattr(self, 'treeWidget') or not self.treeWidget:
        self.log("No hay un árbol de widgets para obtener la selección")
        return
    
    selected_items = self.treeWidget.selectedItems()
    if not selected_items:
        self.log("No hay elementos seleccionados para añadir")
        return
    
    # Procesar cada elemento seleccionado
    for item in selected_items:
        add_item_to_queue(self, item)
        
def add_item_to_queue(self, item):
    """Añade un elemento del árbol a la cola de reproducción."""
    from PyQt6.QtWidgets import QListWidgetItem
    from PyQt6.QtCore import Qt
    
    # Obtener datos del elemento
    item_data = item.data(0, Qt.ItemDataRole.UserRole)
    if not item_data:
        self.log("No hay datos en el elemento seleccionado")
        return
        
    # Verificar si es un tipo reproducible (canción/track)
    item_type = item_data.get('type', '').lower()
    if item_type not in ['track', 'song', 'canción']:
        self.log(f"Tipo '{item_type}' no es reproducible directamente")
        return
        
    # Extraer información necesaria
    title = item_data.get('title', 'Canción desconocida')
    artist = item_data.get('artist', 'Artista desconocido')
    source = item_data.get('source', 'unknown')
    
    # IMPORTANTE: Priorizar file_path para archivos locales
    url = None
    if item_data.get('file_path') and os.path.exists(item_data['file_path']):
        url = item_data['file_path']
    else:
        url = item_data.get('url', '')
        # Si no hay URL explícita, buscar según el source
        if not url and source != 'unknown':
            url_key = f"{source}_url"
            if url_key in item_data:
                url = item_data[url_key]
                
    if not url:
        self.log(f"No se encontró URL o file_path para reproducir '{title}'")
        return
        
    # Crear el texto de visualización
    display_text = f"{artist} - {title}" if artist else title
    
    # Crear el elemento de lista
    list_item = QListWidgetItem(display_text)
    list_item.setData(Qt.ItemDataRole.UserRole, url)
    
    # Establecer icono según la fuente
    if source == 'local_file' or (url and os.path.exists(url)):
        if hasattr(self, 'service_icons') and 'local' in self.service_icons:
            list_item.setIcon(self.service_icons['local'])
        elif hasattr(self, 'get_source_icon'):
            list_item.setIcon(self.get_source_icon(url, {'source': 'local'}))
    elif hasattr(self, 'service_icons') and source in self.service_icons:
        list_item.setIcon(self.service_icons[source])
    elif hasattr(self, 'get_source_icon'):
        list_item.setIcon(self.get_source_icon(url, item_data))
        
    # Añadir a la lista de reproducción
    self.listWidget.addItem(list_item)
    
    # Añadir a la lista interna de pistas
    if not hasattr(self, 'current_playlist'):
        self.current_playlist = []
        
    track_data = {
        'title': title,
        'artist': artist,
        'url': url,  # Esta URL puede ser file_path para archivos locales
        'file_path': item_data.get('file_path', ''),  # Preservar file_path
        'source': source,
        'type': item_type
    }
    
    # Copiar campos adicionales importantes
    for field in ['album', 'track_number', 'duration', 'origin']:
        if field in item_data:
            track_data[field] = item_data[field]
            
    self.current_playlist.append(track_data)
    self.log(f"Añadido a la cola: {display_text} [{source}]")