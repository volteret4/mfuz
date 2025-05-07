import os
import re
import json
import time
import shutil
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem, QMessageBox
from PyQt6.QtGui import QIcon


# Asegurarse de que PROJECT_ROOT está disponible
try:
    from base_module import PROJECT_ROOT
except ImportError:
    import os
    PROJECT_ROOT = os.path.abspath(Path(os.path.dirname(__file__), "..", ".."))

def get_local_playlist_path(self):
    """Get the local playlist save path from configuration."""
    # Default path if not specified in config
    default_path = Path(PROJECT_ROOT, ".content", "playlists", "locales")
    
    try:
        # Try to read from config
        config_path = Path(PROJECT_ROOT, "config", "config.yml")
        if not os.path.exists(config_path):
            os.makedirs(os.path.dirname(default_path), exist_ok=True)
            return default_path
        
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Check global configuration first
        if 'global_theme_config' in config and 'local_playlist_path' in config['global_theme_config']:
            path = config['global_theme_config']['local_playlist_path']
            # Handle relative paths
            if not os.path.isabs(path):
                path = Path(PROJECT_ROOT, path)
            return path
        
        # Then check module configuration
        for module in config.get('modules', []):
            if module.get('name') in ['Url Playlists', 'URL Playlist', 'URL Player']:
                if 'args' in module and 'local_playlist_path' in module['args']:
                    path = module['args']['local_playlist_path']
                    # Handle relative paths
                    if not os.path.isabs(path):
                        path = Path(PROJECT_ROOT, path)
                    return path
        
        # Default if not found
        return default_path
    except Exception as e:
        print(f"Error reading local playlist path from config: {str(e)}")
        return default_path

def parse_pls_file(file_path):
    """Parse a PLS file and return a list of items"""
    try:
        items = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Extraer número de entradas
        num_entries = 0
        for line in lines:
            if line.lower().startswith('numberofentries='):
                try:
                    num_entries = int(line.split('=')[1].strip())
                    break
                except:
                    pass
        
        # Procesar cada entrada
        for i in range(1, num_entries + 1):
            item = {}
            
            # Buscar URL/archivo
            file_key = f"File{i}="
            title_key = f"Title{i}="
            
            url = None
            title = None
            
            for line in lines:
                if line.startswith(file_key):
                    url = line[len(file_key):].strip()
                elif line.startswith(title_key):
                    title = line[len(title_key):].strip()
            
            if url:
                # Extraer artista/título si es posible
                artist = ""
                
                if title and " - " in title:
                    parts = title.split(" - ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                
                item = {
                    'url': url,
                    'title': title or f"Track {i}",
                    'artist': artist,
                    'source': determine_source_from_url(url)
                }
                
                items.append(item)
        
        return items
            
    except Exception as e:
        print(f"Error parsing PLS file: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return []

def determine_source_from_url(url):
    """Determine the source (service) from a URL."""
    url_str = str(url).lower()
    if 'spotify.com' in url_str:
        return 'spotify'
    elif 'youtube.com' in url_str or 'youtu.be' in url_str:
        return 'youtube'
    elif 'soundcloud.com' in url_str:
        return 'soundcloud'
    elif 'bandcamp.com' in url_str:
        return 'bandcamp'
    elif url_str.startswith(('/', 'file:', '~', 'C:', 'D:')):
        return 'local'
    return 'unknown'

def load_local_playlists(self):
    """Carga las playlists locales desde el directorio configurado"""
    try:
        # Obtener la ruta de las playlists locales de la configuración
        local_playlist_path = get_local_playlist_path(self)
        self.log(f"Buscando playlists locales en: {local_playlist_path}")
        
        if not os.path.exists(local_playlist_path):
            os.makedirs(local_playlist_path, exist_ok=True)
            self.log(f"Creado directorio de playlists locales: {local_playlist_path}")
            return []
        
        # Imprimir todos los archivos en el directorio para debug
        all_files = os.listdir(local_playlist_path)
        self.log(f"Archivos en el directorio: {', '.join(all_files)}")
        
        # Obtener todos los archivos .json en el directorio
        json_files = [f for f in all_files if f.endswith('.json')]
        self.log(f"Encontrados {len(json_files)} archivos de playlist JSON")
        
        # Obtener archivos .pls también como respaldo
        pls_files = [f for f in all_files if f.endswith('.pls')]
        self.log(f"Encontrados {len(pls_files)} archivos de playlist PLS")
        
        # Cargar playlists desde archivos JSON
        playlists = []
        
        for filename in json_files:
            try:
                file_path = Path(local_playlist_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Imprimir contenido para debugear
                    #self.log(f"Contenido de {filename}: {content[:100]}...")
                    
                    playlist_data = json.loads(content)
                    
                # Validar los datos de la playlist
                if 'name' in playlist_data and 'items' in playlist_data:
                    playlists.append(playlist_data)
                    #self.log(f"Playlist cargada: {playlist_data['name']} ({len(playlist_data.get('items', []))} elementos)")
                else:
                    self.log(f"Archivo {filename} no tiene formato válido de playlist")
            except Exception as e:
                self.log(f"Error cargando playlist {filename}: {str(e)}")
        
        # Si no se cargaron playlists JSON, intentar con archivos .pls
        if not playlists and pls_files:
            for pls_file in pls_files:
                try:
                    playlist_name = os.path.splitext(pls_file)[0]
                    file_path = Path(local_playlist_path, pls_file)
                    
                    # Extraer datos de archivo .pls
                    items = parse_pls_file(file_path)
                    
                    if items:
                        playlist_data = {
                            'name': playlist_name,
                            'items': items,
                            'created': int(time.time()),
                            'modified': int(time.time())
                        }
                        playlists.append(playlist_data)
                        self.log(f"Playlist PLS cargada: {playlist_name} ({len(items)} elementos)")
                except Exception as e:
                    self.log(f"Error cargando playlist PLS {pls_file}: {str(e)}")
        
        return playlists
            
    except Exception as e:
        self.log(f"Error cargando playlists locales: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return []

def create_local_playlist(self, name):
    """Crea una nueva playlist local vacía"""
    if not name:
        self.log("Nombre de playlist vacío, no se creó")
        return
    
    try:
        # Asegurarse de que existe el directorio
        local_playlist_dir = get_local_playlist_path(self)
        os.makedirs(local_playlist_dir, exist_ok=True)
        
        # Crear una playlist vacía
        import re
        safe_name = re.sub(r'[^\w\-_\. ]', '_', name)
        
        playlist_data = {
            "name": name,
            "items": [],
            "created": int(time.time()),
            "modified": int(time.time())
        }
        
        # Guardar como JSON
        json_path = Path(local_playlist_dir, f"{safe_name}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(playlist_data, f, indent=2, ensure_ascii=False)
        
        # También crear un archivo PLS vacío
        pls_path = Path(local_playlist_dir, f"{safe_name}.pls")
        with open(pls_path, 'w', encoding='utf-8') as f:
            f.write("[playlist]\n")
            f.write("NumberOfEntries=0\n\n")
        
        # Actualizar estructura interna
        if not hasattr(self, 'playlists'):
            self.playlists = self.load_playlists()
        
        if 'local' not in self.playlists:
            self.playlists['local'] = []
        
        # Añadir nueva playlist
        self.playlists['local'].append(playlist_data)
        
        # Guardar y actualizar UI
        save_playlists(self)
        update_playlist_comboboxes(self)
        
        # Seleccionar la nueva playlist
        if hasattr(self, 'playlist_local_comboBox'):
            index = self.playlist_local_comboBox.findText(name)
            if index > 0:
                self.playlist_local_comboBox.setCurrentIndex(index)
        
        self.log(f"Playlist local '{name}' creada correctamente")
        display_local_playlist(self, playlist_data)
        
    except Exception as e:
        self.log(f"Error creando playlist local: {str(e)}")
        import traceback
        self.log(traceback.format_exc())

def load_rss_playlists(self):
    """Carga las playlists de blogs/RSS en el combobox correspondiente"""
    try:
        self.log(f"Directorio de playlists RSS: {self.rss_pending_dir}")
        
        # Verificar combobox
        if not hasattr(self, 'playlist_rss_comboBox') or self.playlist_rss_comboBox is None:
            self.playlist_rss_comboBox = self.findChild(QComboBox, 'playlist_rss_comboBox')
            if not self.playlist_rss_comboBox:
                self.log("ERROR: Combobox 'playlist_rss_comboBox' no disponible")
                return False
        
        # Completely rebuild the combobox from scratch
        self.playlist_rss_comboBox.blockSignals(True)
        self.playlist_rss_comboBox.clear()
        
        # Add default item
        self.playlist_rss_comboBox.addItem(QIcon(":/services/rss"), "Playlists RSS")
        
        # Verify directory
        if not os.path.exists(self.rss_pending_dir):
            os.makedirs(self.rss_pending_dir, exist_ok=True)
            self.playlist_rss_comboBox.blockSignals(False)
            return False
        
        # Gather all playlists first
        all_rss_playlists = []
        blog_playlists = {}  # Organize by blog
        
        # Scan all blogs and their playlists
        for blog in os.listdir(self.rss_pending_dir):
            blog_path = Path(self.rss_pending_dir, blog)
            if os.path.isdir(blog_path):
                blog_playlists[blog] = []
                
                # Find all .m3u files for this blog
                for file in os.listdir(blog_path):
                    if file.endswith('.m3u'):
                        abs_path = os.path.abspath(Path(blog_path, file))
                        
                        if os.path.exists(abs_path):
                            track_count = count_tracks_in_playlist(abs_path)
                            
                            # Create playlist data object
                            playlist_data = {
                                'name': file,
                                'path': abs_path,
                                'track_count': track_count,
                                'blog': blog,
                                'state': 'pending'
                            }
                            
                            blog_playlists[blog].append(playlist_data)
                            all_rss_playlists.append(playlist_data)
        
        # Update internal playlists structure
        if hasattr(self, 'playlists') and isinstance(self.playlists, dict):
            self.playlists['rss'] = all_rss_playlists
        
        # Now add them to the combobox blog by blog
        for blog_name in sorted(blog_playlists.keys()):
            playlists = blog_playlists[blog_name]
            if not playlists:
                continue
                
            # We'll use a custom data structure to identify blog headers
            self.playlist_rss_comboBox.addItem(f"--- {blog_name} ---")
            last_index = self.playlist_rss_comboBox.count() - 1
            # Mark this item as a header with no data
            self.playlist_rss_comboBox.setItemData(last_index, None, Qt.ItemDataRole.UserRole)
            
            # Add each playlist for this blog
            for playlist in sorted(playlists, key=lambda x: x['name']):
                display_text = f"{playlist['name']} ({playlist['track_count']} pistas)"
                
                # Add to combobox
                self.playlist_rss_comboBox.addItem(QIcon(":/services/rss"), display_text)
                last_index = self.playlist_rss_comboBox.count() - 1
                
                # CRITICAL: Create a completely independent copy to avoid reference issues
                playlist_copy = {
                    'name': playlist['name'],
                    'path': playlist['path'],
                    'track_count': playlist['track_count'],
                    'blog': playlist['blog'],
                    'state': playlist['state']
                }
                
                # Set data with explicit call and role
                self.playlist_rss_comboBox.setItemData(last_index, playlist_copy, Qt.ItemDataRole.UserRole)
                
                # Log to verify
                test_data = self.playlist_rss_comboBox.itemData(last_index, Qt.ItemDataRole.UserRole)
                if test_data is None:
                    self.log(f"ERROR: Failed to set data for item {last_index}")
                # else:
                #     self.log(f"Successfully set data for item {last_index}: {test_data['name']}")
        
        self.playlist_rss_comboBox.blockSignals(False)
        return True
        
    except Exception as e:
        self.log(f"ERROR en load_rss_playlists: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        if hasattr(self, 'playlist_rss_comboBox'):
            self.playlist_rss_comboBox.blockSignals(False)
        return False

def count_tracks_in_playlist(playlist_path):
    """Counts the number of tracks in an M3U playlist file"""
    try:
        # Verify path exists
        if not os.path.exists(playlist_path):
            print(f"ERROR: Cannot count tracks, playlist doesn't exist: {playlist_path}")
            return 0
            
        count = 0
        with open(playlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Skip empty lines and metadata/comments
                line = line.strip()
                if line and not line.startswith('#'):
                    count += 1
                    
        #print(f"Counted {count} tracks in {os.path.basename(playlist_path)}")
        return count
    except Exception as e:
        print(f"Error counting tracks in {playlist_path}: {str(e)}")
        return 0

def move_rss_playlist_to_listened(self, playlist_data):
    """Mueve una playlist RSS a la carpeta de escuchados"""
    try:
        # Verificar que tenemos datos válidos
        if not playlist_data or 'path' not in playlist_data or 'blog' not in playlist_data:
            self.log("Error: Datos de playlist incompletos")
            return False
            
        # Directorio de destino
        blog_listened_dir = Path(self.rss_listened_dir, playlist_data['blog'])
        os.makedirs(blog_listened_dir, exist_ok=True)
        
        # Rutas de origen
        playlist_path = playlist_data['path']
        txt_path = os.path.splitext(playlist_path)[0] + '.txt'
        
        # Verificar que existe el archivo de playlist
        if not os.path.exists(playlist_path):
            self.log(f"Error: No se encuentra la playlist en {playlist_path}")
            return False
        
        # Añadir timestamp al nombre
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        new_name = timestamp + os.path.basename(playlist_path)
        new_txt_name = timestamp + os.path.basename(txt_path) if os.path.exists(txt_path) else None
        
        # Rutas de destino
        dest_playlist = Path(blog_listened_dir, new_name)
        dest_txt = Path(blog_listened_dir, new_txt_name) if new_txt_name else None
        
        # Mover archivos
        shutil.move(playlist_path, dest_playlist)
        if os.path.exists(txt_path) and dest_txt:
            shutil.move(txt_path, dest_txt)
            
        self.log(f"Playlist movida a escuchados: {new_name}")
        
        # Recargar playlists
        self.load_rss_playlists()
        
        return True
    except Exception as e:
        self.log(f"Error moviendo playlist a escuchados: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False

def save_playlists(self, playlists=None):
    """Save playlists to the standard location"""
    try:
        if playlists is None:
            if hasattr(self, 'playlists') and isinstance(self.playlists, dict):
                playlists = self.playlists
            else:
                playlists = {'spotify': [], 'local': [], 'rss': []}
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.spotify_playlist_path), exist_ok=True)
        
        with open(self.spotify_playlist_path, 'w', encoding='utf-8') as f:
            json.dump(playlists, f, indent=2, ensure_ascii=False)
        self.log("Playlists saved successfully")
    except Exception as e:
        self.log(f"Error saving playlists: {str(e)}")


def on_guardar_playlist_clicked(self):
    """Handle save playlist button click"""
    # Use the correct combobox name from your UI file
    if not hasattr(self, 'guardar_playlist_comboBox'):
        self.log("ComboBox para guardar playlist no encontrado")
        return
        
    combo = self.guardar_playlist_comboBox
    selected = combo.currentText()
    print(f"selected!!! {selected}")
    if selected == "Spotify":
        self.save_to_spotify_playlist()
    elif selected == "Playlist local":
        self.save_current_playlist()  # Tu función existente
    elif selected == "Youtube":
        self.log("Guardado en Youtube no implementado aún")

def update_playlist_comboboxes(self):
    """Actualiza todos los comboboxes de playlists con los contenidos guardados"""
    try:
        # Asegurarse de que playlists es un diccionario
        if not hasattr(self, 'playlists') or not isinstance(self.playlists, dict):
            self.log("Inicializando estructura de playlists para comboboxes...")
            self.playlists = self.load_playlists()
            if not isinstance(self.playlists, dict):
                self.playlists = {'spotify': [], 'local': [], 'rss': []}
        
        # Actualizar combobox de playlists locales
        if hasattr(self, 'playlist_local_comboBox'):
            # Guardar selección actual
            current_selection = self.playlist_local_comboBox.currentText()
            
            # Limpiar el combobox
            self.playlist_local_comboBox.blockSignals(True)  # Evitar que se disparen eventos durante la actualización
            self.playlist_local_comboBox.clear()
            
            # Añadir placeholder como primera opción
            self.playlist_local_comboBox.addItem(QIcon(":/services/plslove"), "Playlists locales")
            
            # Añadir opción para crear nueva playlist
            self.playlist_local_comboBox.addItem(QIcon(":/services/plslove"), "Nueva Playlist Local")
            
            # Añadir todas las playlists locales
            local_playlists = self.playlists.get('local', [])
            
            # Si no hay playlists locales, intentar cargarlas de nuevo
            if not local_playlists:
                local_playlists = self.load_local_playlists()
                if local_playlists:
                    self.playlists['local'] = local_playlists
                    save_playlists(self, )
            
            # Ordenar playlists por nombre
            local_playlists = sorted(local_playlists, key=lambda x: x.get('name', '').lower())
            
            for playlist in local_playlists:
                playlist_name = playlist.get('name', 'Playlist sin nombre')
                self.playlist_local_comboBox.addItem(
                    QIcon(":/services/plslove"), 
                    playlist_name
                )
            
            # Registrar cuántas playlists se añadieron
            num_playlists = len(local_playlists)
            self.log(f"Combobox actualizado con {num_playlists} playlists locales")
            
            # Restaurar selección o seleccionar placeholder
            if current_selection and current_selection != "Playlists locales" and current_selection != "Nueva Playlist Local":
                index = self.playlist_local_comboBox.findText(current_selection)
                if index > 0:
                    self.playlist_local_comboBox.setCurrentIndex(index)
                else:
                    self.playlist_local_comboBox.setCurrentIndex(0)  # Seleccionar placeholder
            else:
                self.playlist_local_comboBox.setCurrentIndex(0)  # Seleccionar placeholder
            
            self.playlist_local_comboBox.blockSignals(False)  # Reactivar las señales
        
        
        
        # Actualizar combobox de Spotify
        if hasattr(self, 'playlist_spotify_comboBox'):
            self.playlist_spotify_comboBox.clear()
            self.playlist_spotify_comboBox.addItem(QIcon(":/services/b_plus_cross"), "Nueva Playlist Spotify")
            
            for playlist in self.playlists.get('spotify', []):
                self.playlist_spotify_comboBox.addItem(
                    QIcon(":/services/spotify"), 
                    playlist.get('name', 'Unnamed Playlist')
                )
        
        # Actualizar combobox de RSS
        if hasattr(self, 'playlist_rss_comboBox'):
            self.playlist_rss_comboBox.clear()
            
            for playlist in self.playlists.get('rss', []):
                self.playlist_rss_comboBox.addItem(
                    QIcon(":/services/rss"), 
                    playlist.get('name', 'Unnamed Blog')
                )
    
    except Exception as e:
        self.log(f"Error actualizando comboboxes de playlists: {str(e)}")
        import traceback
        self.log(traceback.format_exc())

def display_local_playlist(self, playlist):
    """Display a local playlist in the tree widget"""
    try:
        # Clear the tree widget
        self.treeWidget.clear()
        
        # Get playlist data
        if isinstance(playlist, str):
            # If we received a playlist name instead of a data structure
            playlist_name = playlist
            playlist = None
            for p in self.playlists.get('local', []):
                if p.get('name') == playlist_name:
                    playlist = p
                    break
            if not playlist:
                self.log(f"Local playlist '{playlist_name}' not found")
                return
        
        playlist_name = playlist.get('name', 'Unnamed Playlist')
        items = playlist.get('items', [])
        
        if not items:
            self.log(f"Playlist '{playlist_name}' is empty")
            return
        
        # Create a root item for the playlist
        root_item = QTreeWidgetItem(self.treeWidget)
        root_item.setText(0, playlist_name)
        root_item.setText(1, "Local")
        root_item.setText(2, "Playlist")
        
        # Format as bold
        font = root_item.font(0)
        font.setBold(True)
        root_item.setFont(0, font)
        root_item.setFont(1, font)
        
        # Add the playlist icon
        root_item.setIcon(0, QIcon(":/services/plslove"))
        
        # Store playlist data on the root item
        root_item.setData(0, Qt.ItemDataRole.UserRole, {
            'name': playlist_name,
            'type': 'playlist',
            'source': 'local'
        })
        
        # Add tracks as children
        for i, item in enumerate(items):
            title = item.get('title', 'Unknown Track')
            artist = item.get('artist', '')
            url = item.get('url', '')
            source = item.get('source', _determine_source_from_url(self, url))
            
            # Create track item
            track_item = QTreeWidgetItem(root_item)
            track_item.setText(0, title)
            track_item.setText(1, artist)
            track_item.setText(2, "Canción")
            
            if item.get('duration'):
                duration_str = self.format_duration(item.get('duration'))
                track_item.setText(4, duration_str)
            
            # Set track icon based on source
            source_icon = self.get_source_icon(url, {'source': source})
            track_item.setIcon(0, source_icon)
            
            # Store track data
            track_data = {
                'title': title,
                'artist': artist,
                'url': url,
                'source': source,
                'type': 'track',
                'from_database': False
            }
            track_item.setData(0, Qt.ItemDataRole.UserRole, track_data)
        
        # Expand the root item
        root_item.setExpanded(True)
        
        self.log(f"Loaded playlist '{playlist_name}' with {len(items)} tracks into tree view")
        
    except Exception as e:
        self.log(f"Error displaying local playlist: {str(e)}")
        import traceback
        self.log(traceback.format_exc())


def _determine_source_from_url(self, url):
    """Determine the source (service) from a URL."""
    url = str(url).lower()
    if 'spotify.com' in url:
        return 'spotify'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'soundcloud.com' in url:
        return 'soundcloud'
    elif 'bandcamp.com' in url:
        return 'bandcamp'
    elif url.startswith(('/', 'file:', '~', 'C:', 'D:')):
        return 'local'
    return 'unknown'
