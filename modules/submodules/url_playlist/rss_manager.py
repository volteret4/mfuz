from modules.submodules.url_playlist.playlist_manager import _determine_source_from_url
from PyQt6.QtWidgets import QPushButton, QMessageBox, QVBoxLayout, QTreeWidgetItem
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer
import subprocess
import os

from modules.submodules.url_playlist.playlist_manager import load_rss_playlists


def setup_rss_controls(self):
    """Configura controles adicionales para playlists RSS"""
    try:
        # Buscar el botón existente en la UI
        existing_button = self.findChild(QPushButton, 'mark_as_listened_button')
        
        if existing_button:
            # Si existe, simplemente conectar su señal
            existing_button.clicked.connect(lambda: mark_current_rss_as_listened(self))
            self.log("Botón 'mark_as_listened_button' encontrado en UI y conectado")
            
            # Guardar referencia para uso posterior
            self.mark_as_listened_button = existing_button
        
        # Aquí se elimina todo el código relacionado con el 'refresh_rss_button'
            
        self.log("Controles RSS configurados")
        return True
            
    except Exception as e:
        self.log(f"Error configurando controles RSS: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False

def load_rss_playlist_content(self, playlist_item, playlist_data):
    """Carga el contenido de una playlist RSS como hijos del item de la playlist"""
    try:
        # Limpiar cualquier contenido previo
        while playlist_item.childCount() > 0:
            playlist_item.removeChild(playlist_item.child(0))
            
        # Ruta de la playlist
        playlist_path = playlist_data['path']
        
        # Verificar archivo relacionado de títulos (txt con mismo nombre que la playlist)
        txt_path = os.path.splitext(playlist_path)[0] + '.txt'
        titles = []
        
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                titles = [line.strip() for line in f.readlines()]
        
        # Leer la playlist
        track_index = 0
        with open(playlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Obtener título si está disponible, de lo contrario usar URL
                    title = line
                    if track_index < len(titles) and titles[track_index]:
                        title = titles[track_index]
                    
                    # Crear item para la pista
                    track_item = QTreeWidgetItem(playlist_item)
                    track_item.setText(0, title)
                    track_item.setText(1, playlist_data['blog']) # Blog como "artista"
                    track_item.setText(2, "Track") # Tipo
                    
                    # Determinar fuente y establecer icono adecuado
                    source = _determine_source_from_url(self, line)
                    track_item.setIcon(0, self.get_source_icon(line, {'source': source}))
                    
                    # Almacenar datos para reproducción
                    track_data = {
                        'title': title,
                        'url': line,
                        'type': 'track',
                        'source': source,
                        'blog': playlist_data['blog'],
                        'playlist': playlist_data['name']
                    }
                    track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
                    
                    track_index += 1
        
        # Expandir el item de la playlist
        playlist_item.setExpanded(True)
        
        # Almacenar datos de la playlist actual para otras operaciones
        self.current_rss_playlist = playlist_data
        
        self.log(f"Cargada playlist RSS '{playlist_data['name']}' con {track_index} pistas")
        return True
    except Exception as e:
        self.log(f"Error cargando contenido de playlist RSS: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False


def mark_current_rss_as_listened(self):
    """Marca la playlist RSS actual como escuchada"""
    if not hasattr(self, 'current_rss_playlist') or not self.current_rss_playlist:
        QMessageBox.warning(self, "Advertencia", "No hay playlist RSS seleccionada")
        return
    
    # Confirmar con el usuario
    reply = QMessageBox.question(
        self,
        "Marcar como Escuchada",
        f"¿Deseas marcar la playlist '{self.current_rss_playlist['name']}' como escuchada?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes
    )
    
    if reply == QMessageBox.StandardButton.Yes:
        # Mover a escuchados
        success = self.move_rss_playlist_to_listened(self.current_rss_playlist)
        
        if success:
            # Limpiar el treeWidget
            self.treeWidget.clear()
            
            # Reseleccionar el primer ítem en el combobox
            self.playlist_rss_comboBox.setCurrentIndex(0)
            
            # Eliminar referencia a la playlist actual
            self.current_rss_playlist = None

# Función modificada para actualizar_playlists_rss
def actualizar_playlists_rss(self):
    """Lanza script para obtener nuevas playlists del servidor RSS en un hilo separado"""
    if not hasattr(self, 'script_path') or not hasattr(self, 'freshrss_url') or not hasattr(self, 'freshrss_username') or not hasattr(self, 'freshrss_auth_token') or not hasattr(self, 'rss_pending_dir'):
        self.log("Error: Faltan credenciales o rutas necesarias para actualizar RSS")
        QMessageBox.warning(self, "Error", "Faltan credenciales o rutas necesarias para actualizar RSS")
        return False
    
    self.log(f"Ejecutando script: {self.script_path}")
    
    # Crear un thread para ejecutar el script sin bloquear la interfaz
    import threading
    
    def run_script():
        try:
            # Emitir señal de inicio con mensaje
            self.process_started_signal.emit("Actualizando feeds RSS...")
            
            # Preparar comando
            cmd = [
                "python", 
                str(self.script_path), 
                "--url", str(self.freshrss_url), 
                "--username", str(self.freshrss_username), 
                "--auth-token", str(self.freshrss_auth_token), 
                "--output-dir", str(self.rss_pending_dir)
            ]
            
            self.log(f"Comando: {' '.join(cmd)}")
            
            # Ejecutar en proceso separado
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Variables para contar progreso
            success_count = 0
            total_count = 0
            line_count = 0
            
            # Leer salida línea por línea para actualizar progreso
            for line in process.stdout:
                line_count += 1
                self.log(f"Script: {line.strip()}")
                
                # Extraer información de progreso si está disponible
                if "Procesando feed:" in line:
                    # Actualizar progreso (estimado)
                    self.process_progress_signal.emit(min(25 + line_count, 90), f"Procesando feed: {line.split('Procesando feed:')[1].strip()}")
                elif "Obtenidos" in line and "posts nuevos" in line:
                    try:
                        # Intentar extraer números
                        parts = line.split("Obtenidos ")[1].split(" posts nuevos")[0]
                        num_posts = int(parts.strip())
                        total_count += num_posts
                        # Actualizar progreso
                        self.process_progress_signal.emit(min(50 + line_count, 90), f"Encontrados {total_count} posts")
                    except:
                        pass
                elif "Playlists creadas:" in line:
                    try:
                        # Intentar extraer número de playlists creadas
                        success_count = int(line.split("Playlists creadas:")[1].strip())
                        # Casi completado
                        self.process_progress_signal.emit(95, f"Creadas {success_count} playlists")
                    except:
                        pass
                
                # Actualizar progreso periódico si no hay info específica
                if line_count % 5 == 0:
                    # Progreso estimado basado en líneas procesadas
                    progress = min(10 + line_count * 2, 90)
                    self.process_progress_signal.emit(progress, "Procesando feeds...")
            
            # Leer errores
            stderr_output = process.stderr.read()
            if stderr_output:
                self.log(f"Error del script: {stderr_output}")
            
            # Esperar a que termine el proceso
            return_code = process.wait()
            
            if return_code == 0:
                self.process_finished_signal.emit("Actualización completada", success_count, total_count)
                
                # Actualizar UI en el hilo principal
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(self, "post_rss_update", Qt.ConnectionType.QueuedConnection)
            else:
                self.process_error_signal.emit(f"Error al ejecutar el script (código {return_code})")
        
        except Exception as e:
            self.log(f"Error al ejecutar el script: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            self.process_error_signal.emit(f"Error al ejecutar el script: {str(e)}")
    
    # Iniciar el hilo
    thread = threading.Thread(target=run_script)
    thread.daemon = True  # Para que el hilo termine si la aplicación se cierra
    thread.start()
    
    return True

# Método para ser llamado desde el hilo separado cuando finalice la actualización
def post_rss_update(self):
    """Acciones a realizar en el hilo principal después de actualizar RSS"""
    # Recargar las playlists RSS después de la actualización
    reload_rss_playlists(self)
    QMessageBox.information(self, "Éxito", "Feeds RSS actualizados correctamente")

def run_direct_command(self, cmd, args=None):
    """Ejecuta un comando directo y devuelve su salida."""
    if args is None:
        args = []
        
    try:
        result = subprocess.run([cmd] + args, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", f"Error: {str(e)}", -1




def reload_rss_playlists(self):
    """Recarga específicamente las playlists RSS"""
    try:
        self.log("Recargando playlists RSS manualmente...")
        result = load_rss_playlists(self)
        if result:
            self.log("Recarga de playlists RSS completada con éxito")
            
            # Actualizar el menú unificado también
            if hasattr(self, 'action_unified_playlist') and self.action_unified_playlist:
                update_unified_playlist_menu(self)
        else:
            self.log("ERROR: No se pudieron recargar las playlists RSS")
        
        # Force UI update
        if hasattr(self, 'playlist_rss_comboBox') and self.playlist_rss_comboBox:
            self.playlist_rss_comboBox.update()
        
        return result
    except Exception as e:
        self.log(f"Error recargando playlists RSS: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False


def update_unified_playlist_menu(self):
    """Update the hierarchical menu with playlists from all sources"""
    try:
        if not hasattr(self, 'playlist_menu') or not self.playlist_menu:
            self.log("Playlist menu not initialized")
            return False
            
        # Clear the current menu
        self.playlist_menu.clear()
        
        # Rebuild menu
        from modules.submodules.url_playlist.ui_helpers import setup_unified_playlist_menu
        setup_unified_playlist_menu(self)
        
        self.log("Unified playlist menu updated")
        return True
    except Exception as e:
        self.log(f"Error updating unified playlist menu: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False