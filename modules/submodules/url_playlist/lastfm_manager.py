import os
import json
import time
import threading
import urllib.parse
import requests
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QMetaObject
from PyQt6.QtWidgets import QMenu, QProgressDialog, QApplication, QMessageBox, QPushButton, QSlider, QSpinBox
from PyQt6.QtGui import QIcon

from modules.submodules.url_playlist.ui_helpers import get_service_priority
from modules.submodules.url_playlist.lastfm_db import (
    save_scrobbles_to_db,
    process_scrobbles,
    load_scrobbles_from_db,
    create_scrobbles_table,
    integrate_scrobbles_to_songs,
    fetch_links_for_scrobbles,
    extract_link_from_lastfm
)

# Asegurarse de que PROJECT_ROOT está disponible
try:
    from base_module import PROJECT_ROOT
except ImportError:
    import os
    PROJECT_ROOT = os.path.abspath(Path(os.path.dirname(__file__), "..", ".."))

def setup_lastfm_menu_items(self, menu):
    """Set up Last.fm menu items in any menu"""
    try:
        # Add "Sync Scrobbles" option
        sync_action = menu.addAction(QIcon(":/services/refresh"), "Sincronizar scrobbles")
        sync_action.triggered.connect(lambda: sync_lastfm_scrobbles_safe(self))
        
        # Add "Latest" submenu
        latest_menu = menu.addMenu(QIcon(":/services/lastfm"), "Últimos")
        
        # NUEVA LÍNEA: Añadir opción para últimas 24 horas
        last_24h = latest_menu.addAction("Últimas 24 horas")
        last_24h.triggered.connect(lambda checked=False, instance=self: 
            QTimer.singleShot(0, lambda: load_lastfm_scrobbles_period(instance, "24h")))
        
        last_week = latest_menu.addAction("Última semana")
        last_week.triggered.connect(lambda checked=False, instance=self:
            QTimer.singleShot(0, lambda: load_lastfm_scrobbles_period(instance, "week")))
        
        last_month = latest_menu.addAction("Último mes")
        last_month.triggered.connect(lambda checked=False, instance=self:
            QTimer.singleShot(0, lambda: load_lastfm_scrobbles_period(instance, "month")))
        
        last_year = latest_menu.addAction("Último año")
        last_year.triggered.connect(lambda checked=False, instance=self:
            QTimer.singleShot(0, lambda: load_lastfm_scrobbles_period(instance, "year")))
        
        # Menu separator
        menu.addSeparator()
        
        # Add "Months" submenu (will be populated dynamically later)
        months_menu = menu.addMenu(QIcon(":/services/calendar"), "Meses")
        
        # Add "Years" submenu (will be populated dynamically later)
        years_menu = menu.addMenu(QIcon(":/services/calendar"), "Años")
        
        # Return the menu references before trying to populate them
        menu_refs = {
            'months_menu': months_menu,
            'years_menu': years_menu
        }
        
        # Try to populate menus immediately if possible
        try:
            populate_scrobbles_time_menus(self)
        except Exception as e:
            self.log(f"Error pre-populating time menus: {e}")
            # We'll try to populate them later
        
        menu.addSeparator()
        
        # Add "Integrate Scrobbles" submenu
        integrate_menu = menu.addMenu(QIcon(":/services/database"), "Integrar scrobbles")
        
        # Add entry for each lastfm username we can find
        lastfm_usernames = get_lastfm_usernames(self)
        
        for user in lastfm_usernames:
            user_action = integrate_menu.addAction(f"Integrar scrobbles de {user}")
            # FIX: Capturar la variable user correctamente
            user_action.triggered.connect(lambda checked=False, u=user: integrate_scrobbles_to_songs(self, u))
        
        # Add "Fetch Links" submenu - AQUÍ ESTÁ EL FIX PRINCIPAL
        links_menu = menu.addMenu(QIcon(":/services/link"), "Obtener enlaces")
        
        for user in lastfm_usernames:
            link_action = links_menu.addAction(f"Obtener enlaces para {user}")
            # FIX: Usar parámetro por defecto para capturar la variable del bucle
            link_action.triggered.connect(lambda checked=False, u=user: fetch_links_for_scrobbles(self, u))
        
        return menu_refs
    except Exception as e:
        self.log(f"Error setting up Last.fm menu items: {str(e)}")
        return {}

def get_lastfm_cache_path(lastfm_username=None):
    """
    Get the path to the Last.fm scrobbles cache file.
    
    Args:
        lastfm_username: Optional Last.fm username to create user-specific cache files
        
    Returns:
        Path to the cache file
    """
    try:
        # Try to import PROJECT_ROOT from base module
        from base_module import PROJECT_ROOT
    except ImportError:
        # Use a fallback if not available
        PROJECT_ROOT = os.path.abspath(Path(os.path.dirname(__file__), "..", "..", ".."))
    
    cache_dir = Path(PROJECT_ROOT, ".content", "cache", "url_playlist")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Create user-specific cache file if username is provided
    if lastfm_username:
        return Path(cache_dir, f"scrobbles_{lastfm_username}.json")
    else:
        return Path(cache_dir, "lastfm_scrobbles.json")

def get_lastfm_usernames(self):
    """Get a list of Last.fm users from existing database tables"""
    try:
        if not hasattr(self, 'db_path') or not self.db_path:
            return [getattr(self, 'lastfm_username', 'paqueradejere')] if hasattr(self, 'lastfm_username') and self.lastfm_username else ['paqueradejere']
            
        import sqlite3
        import re
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get tables starting with "scrobbles_"
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'scrobbles_%'")
        tables = cursor.fetchall()
        
        conn.close()
        
        # Extract usernames from table names
        usernames = []
        for table in tables:
            match = re.match(r'scrobbles_(\w+)', table[0])
            if match:
                usernames.append(match.group(1))
        
        # Add current lastfm_usernameif set and not in the list
        if hasattr(self, 'lastfm_username') and self.lastfm_username and self.lastfm_username not in usernames:
            usernames.append(self.lastfm_username)
        
        # Add paqueradejere as fallback if no usernames found
        if not usernames:
            usernames.append('paqueradejere')
            
        # Remove duplicates while preserving order
        seen = set()
        unique_usernames = [u for u in usernames if not (u in seen or seen.add(u))]
        
        self.log(f"Found Last.fm users: {', '.join(unique_usernames)}")
        return unique_usernames
    except Exception as e:
        self.log(f"Error getting Last.fm users: {str(e)}")
        return [getattr(self, 'lastfm_username', 'paqueradejere')] if hasattr(self, 'lastfm_username') and self.lastfm_username else ['paqueradejere']



def sync_lastfm_scrobbles_safe(self, show_dialogs=True):
    """Versión segura de sincronización de Last.fm que evita problemas de memoria"""
    try:
        # Verificar que no estamos ya sincronizando
        if hasattr(self, '_is_syncing') and self._is_syncing:
            self.log("Ya hay una sincronización en progreso, ignorando solicitud")
            return False
            
        # Marcar que estamos sincronizando
        self._is_syncing = True
            
        # Verificar credenciales básicas sin acceder a la UI
        if not hasattr(self, 'lastfm_api_key') or not self.lastfm_api_key:
            self.log("Error: Last.fm API key not configured")
            self._is_syncing = False
            return False
                
        if not hasattr(self, 'lastfm_username') or not self.lastfm_username:
            self.log("Error: Last.fm username not configured")
            self._is_syncing = False
            return False
        
        # Obtener timestamp más reciente de la base de datos
        try:
            import sqlite3
            import time
            
            # Obtener el timestamp más reciente
            db_timestamp = 0
            
            if hasattr(self, 'db_path') and os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Comprobar tabla de configuración
                config_table = f"lastfm_config_{self.lastfm_username}"
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{config_table}'")
                if cursor.fetchone():
                    cursor.execute(f"SELECT last_timestamp FROM {config_table} WHERE id = 1")
                    result = cursor.fetchone()
                    if result and result[0]:
                        db_timestamp = int(result[0])
                
                conn.close()
            
            # Añadir 1 al timestamp para evitar duplicados
            last_updated = db_timestamp + 1 if db_timestamp > 0 else 0
            current_time = int(time.time())
            
            self.log(f"Timestamp más reciente: {db_timestamp}, usando {last_updated}")
            
            # Petición única a Last.fm para minimizar problemas
            all_scrobbles = []
            
            # Crear parámetros básicos
            params = {
                'method': 'user.getrecenttracks',
                'user': self.lastfm_username,
                'api_key': self.lastfm_api_key,
                'format': 'json',
                'limit': 50  # Limitar a menos resultados para seguridad
            }
            
            # Añadir rango de tiempo si tenemos un timestamp anterior
            if last_updated > 0:
                params['from'] = last_updated
                params['to'] = current_time
            
            # Hacer la petición de forma segura
            import urllib.parse
            url = f"https://ws.audioscrobbler.com/2.0/?{urllib.parse.urlencode(params)}"
            self.log(f"Petición segura a Last.fm: {url}")
            
            import requests
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                self.log(f"Error en petición a Last.fm: {response.status_code}")
                self._is_syncing = False
                return False
            
            # Procesar respuesta
            data = response.json()
            
            if 'error' in data:
                self.log(f"Error de Last.fm API: {data.get('message', 'Unknown error')}")
                self._is_syncing = False
                return False
            
            # Verificar que hay resultados
            recenttracks = data.get('recenttracks', {})
            total_results = int(recenttracks.get('@attr', {}).get('total', '0'))
            
            if total_results == 0:
                self.log("No hay nuevos scrobbles para sincronizar")
                self._is_syncing = False
                return True
            
            # Procesar tracks de forma segura
            tracks = recenttracks.get('track', [])
            if not isinstance(tracks, list):
                tracks = [tracks]
            
            for track in tracks:
                # Omitir 'now playing'
                if '@attr' in track and track['@attr'].get('nowplaying') == 'true':
                    continue
                
                # Crear objeto de scrobble básico
                try:
                    timestamp = int(track.get('date', {}).get('uts', '0'))
                    
                    # Solo procesar si es más reciente que el último guardado
                    if timestamp > db_timestamp:
                        scrobble = {
                            'artist_name': track.get('artist', {}).get('#text', ''),
                            'artist_mbid': track.get('artist', {}).get('mbid', ''),
                            'name': track.get('name', ''),
                            'album_name': track.get('album', {}).get('#text', ''),
                            'album_mbid': track.get('album', {}).get('mbid', ''),
                            'timestamp': timestamp,
                            'fecha_scrobble': track.get('date', {}).get('#text', ''),
                            'lastfm_url': track.get('url', ''),
                            'reproducciones': 1,
                            'fecha_reproducciones': json.dumps([track.get('date', {}).get('#text', '')])
                        }
                        
                        # Campos alternativos
                        scrobble['artist'] = scrobble['artist_name']
                        scrobble['title'] = scrobble['name']
                        scrobble['album'] = scrobble['album_name']
                        
                        all_scrobbles.append(scrobble)
                except Exception as e:
                    self.log(f"Error procesando track: {e}")
                    continue
            
            # Guardar en la base de datos de forma segura
            if all_scrobbles:
                self.log(f"Guardando {len(all_scrobbles)} scrobbles nuevos")
                
                # Importar función para guardar pero sin usarla directamente
                # Esto es para evitar problemas con importaciones circulares
                try:
                    # Crear tablas primero
                    if hasattr(self, 'db_path') and os.path.exists(self.db_path):
                        conn = sqlite3.connect(self.db_path)
                        
                        # Crear tabla de scrobbles si no existe
                        table_name = f"scrobbles_{self.lastfm_username}"
                        cursor = conn.cursor()
                        
                        # Verificar si la tabla existe
                        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                        if not cursor.fetchone():
                            # Crear tabla
                            cursor.execute(f"""
                            CREATE TABLE IF NOT EXISTS {table_name} (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                song_id INTEGER,
                                track_name TEXT NOT NULL,
                                artist_name TEXT NOT NULL,
                                album_name TEXT,
                                artist_id INTEGER,
                                album_id INTEGER,
                                timestamp INTEGER NOT NULL,
                                scrobble_date TEXT NOT NULL,
                                lastfm_url TEXT,
                                fecha_adicion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                artist_mbid TEXT,
                                name TEXT NOT NULL,
                                album_mbid TEXT,
                                fecha_scrobble TEXT NOT NULL,
                                reproducciones INTEGER DEFAULT 1,
                                fecha_reproducciones TEXT,
                                youtube_url TEXT,
                                spotify_url TEXT,
                                bandcamp_url TEXT,
                                soundcloud_url TEXT
                            )
                            """)
                            
                            # Crear índices para búsqueda rápida
                            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name}(timestamp)")
                            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_artist ON {table_name}(artist_name)")
                            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_track ON {table_name}(track_name)")
                            
                            self.log(f"Tabla {table_name} creada")
                        
                        # Crear tabla de configuración si no existe
                        config_table = f"lastfm_config_{self.lastfm_username}"
                        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{config_table}'")
                        if not cursor.fetchone():
                            cursor.execute(f"""
                            CREATE TABLE IF NOT EXISTS {config_table} (
                                id INTEGER PRIMARY KEY,
                                lastfm_username TEXT,
                                last_timestamp INTEGER,
                                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                            """)
                            
                            # Insertar registro inicial
                            cursor.execute(f"""
                            INSERT INTO {config_table} (id, lastfm_username, last_timestamp, last_updated)
                            VALUES (1, ?, 0, CURRENT_TIMESTAMP)
                            """, (self.lastfm_username,))
                            
                            self.log(f"Tabla {config_table} creada")
                        
                        conn.commit()
                        
                        # Insertar scrobbles uno por uno de forma segura
                        for scrobble in all_scrobbles:
                            try:
                                # Verificar si ya existe (para evitar duplicados)
                                cursor.execute(f"""
                                SELECT id FROM {table_name}
                                WHERE artist_name = ? AND track_name = ? AND timestamp = ?
                                """, (scrobble['artist_name'], scrobble['name'], scrobble['timestamp']))
                                
                                if not cursor.fetchone():
                                    # Insertar nuevo scrobble
                                    cursor.execute(f"""
                                    INSERT INTO {table_name} (
                                        track_name, artist_name, album_name, 
                                        timestamp, scrobble_date, lastfm_url, 
                                        artist_mbid, name, album_mbid, 
                                        fecha_scrobble, reproducciones, fecha_reproducciones
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        scrobble['name'], scrobble['artist_name'], scrobble['album_name'],
                                        scrobble['timestamp'], scrobble['fecha_scrobble'], scrobble['lastfm_url'],
                                        scrobble['artist_mbid'], scrobble['name'], scrobble['album_mbid'],
                                        scrobble['fecha_scrobble'], 1, scrobble['fecha_reproducciones']
                                    ))
                            except Exception as e:
                                self.log(f"Error insertando scrobble: {e}")
                                continue
                        
                        # Actualizar timestamp más reciente
                        newest_timestamp = max([s['timestamp'] for s in all_scrobbles]) if all_scrobbles else 0
                        
                        if newest_timestamp > db_timestamp:
                            cursor.execute(f"""
                            UPDATE {config_table}
                            SET last_timestamp = ?, last_updated = CURRENT_TIMESTAMP
                            WHERE id = 1
                            """, (newest_timestamp,))
                            
                            self.log(f"Timestamp actualizado a {newest_timestamp}")
                        
                        conn.commit()
                        conn.close()
                        
                        self.log(f"Sincronización completada con éxito")
                        
                        # Programar actualización de menús para el hilo principal
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(500, lambda: self._update_lastfm_menus_after_sync())
                        
                        self._is_syncing = False
                        return True
                    else:
                        self.log("Error: No se puede acceder a la base de datos")
                        self._is_syncing = False
                        return False
                        
                except Exception as e:
                    self.log(f"Error guardando scrobbles: {e}")
                    import traceback
                    self.log(traceback.format_exc())
                    self._is_syncing = False
                    return False
            else:
                self.log("No hay nuevos scrobbles para guardar")
                self._is_syncing = False
                return True
                
        except Exception as e:
            self.log(f"Error en sincronización: {e}")
            import traceback
            self.log(traceback.format_exc())
            self._is_syncing = False
            return False
            
    except Exception as e:
        self.log(f"Error general en sincronización: {e}")
        import traceback
        self.log(traceback.format_exc())
        if hasattr(self, '_is_syncing'):
            self._is_syncing = False
        return False

def _update_lastfm_menus_after_sync(self):
    """Actualiza los menús de Last.fm después de una sincronización exitosa"""
    try:
        # Cargar años y meses de forma segura
        years_dict = load_years_months_from_db_direct(self)
        if years_dict:
            populate_scrobbles_time_menus(self, years_dict=years_dict)
            self.log("Menús de Last.fm actualizados después de sincronización")
    except Exception as e:
        self.log(f"Error actualizando menús después de sincronización: {e}")


def sync_lastfm_scrobbles(self, show_dialogs=True):
    """Synchronize Last.fm scrobbles and store them in a cache file and database"""
    try:
        # Check if we have valid configuration
        if not self.lastfm_api_key:
            self.log("Error: Last.fm API key not configured")
            if show_dialogs:
                from PyQt6.QtWidgets import QMessageBox
                from PyQt6.QtCore import QThread, QCoreApplication, QTimer
                
                # Verificar si estamos en el hilo principal
                if QThread.currentThread() == QCoreApplication.instance().thread():
                    QMessageBox.warning(self, "Error", "Last.fm API key not configured. Check settings.")
                else:
                    # Si no estamos en el hilo principal, programar para el hilo principal
                    QTimer.singleShot(0, lambda: QMessageBox.warning(self, "Error", "Last.fm API key not configured. Check settings."))
            return False
                
        if not self.lastfm_username:
            self.log("Error: Last.fm username not configured")
            if show_dialogs:
                from PyQt6.QtWidgets import QMessageBox
                from PyQt6.QtCore import QThread, QCoreApplication, QTimer
                
                # Verificar si estamos en el hilo principal
                if QThread.currentThread() == QCoreApplication.instance().thread():
                    QMessageBox.warning(self, "Error", "Last.fm username not configured. Check settings.")
                else:
                    # Si no estamos en el hilo principal, programar para el hilo principal
                    QTimer.singleShot(0, lambda: QMessageBox.warning(self, "Error", "Last.fm username not configured. Check settings."))
            return False
        
        # Show progress dialog if requested
        progress = None
        if show_dialogs:
            from PyQt6.QtWidgets import QProgressDialog
            from PyQt6.QtCore import Qt, QCoreApplication, QThread, QTimer
            
            # Función segura para crear el diálogo de progreso
            def create_progress_dialog():
                nonlocal progress
                progress = QProgressDialog("Syncing Last.fm scrobbles...", "Cancel", 0, 100, self)
                progress.setWindowTitle("Last.fm Sync")
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.show()
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
            
            # Asegurarse de estar en el hilo principal
            if QThread.currentThread() == QCoreApplication.instance().thread():
                create_progress_dialog()
            else:
                # Si no estamos en el hilo principal, programar para el hilo principal
                QTimer.singleShot(0, create_progress_dialog)
                # Esperar un poco para que se cree el diálogo
                import time
                time.sleep(0.2)
        
        # Determine cache file path - use user-specific path
        cache_file = get_lastfm_cache_path(self.lastfm_username)
        
        # Create necessary tables if they don't exist
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        create_scrobbles_table(conn, self.lastfm_username)
        conn.close()
        
        # Get the latest timestamp from the database - CRITICAL PART
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use the user-specific config table directly instead of the function
        config_table = f"lastfm_config_{self.lastfm_username}"
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{config_table}'")
        if cursor.fetchone():
            cursor.execute(f"SELECT last_timestamp FROM {config_table} WHERE id = 1")
            config_result = cursor.fetchone()
            if config_result and config_result[0]:
                db_timestamp = config_result[0]
                self.log(f"Found last_timestamp in config table: {db_timestamp}")
            else:
                db_timestamp = 0
        else:
            db_timestamp = 0
            
        conn.close()
        
        self.log(f"Latest timestamp from database: {db_timestamp}")
        
        # Check if we have existing data
        if db_timestamp > 0:
            # Add 1 to avoid duplicate scrobbles
            last_updated = db_timestamp + 1  
            self.log(f"Using timestamp from database: {last_updated}")
        else:
            # No existing data, do a full sync
            self.log("No existing scrobbles in database, will perform full sync")
            last_updated = 0
        
        # Update progress safely
        def update_progress(value, message=None):
            if progress and show_dialogs:
                # Verificar que estamos en el hilo principal
                from PyQt6.QtCore import QThread, QCoreApplication, QTimer
                if QThread.currentThread() == QCoreApplication.instance().thread():
                    progress.setValue(value)
                    if message:
                        progress.setLabelText(message)
                    from PyQt6.QtWidgets import QApplication
                    QApplication.processEvents()
                else:
                    # Si no estamos en el hilo principal, programar para el hilo principal
                    QTimer.singleShot(0, lambda: update_progress(value, message))
        
        # Update progress to 10%
        update_progress(10, "Iniciando sincronización...")
        
        # Prepare for API requests
        all_scrobbles = []
        page = 1
        total_pages = 1
        
        # Update progress to 20%
        update_progress(20, "Conectando con Last.fm...")
        
        # Track if we found any new scrobbles
        new_scrobbles_found = False
        
        # Get current time for the "to" parameter
        import time
        current_time = int(time.time())
        
        while page <= total_pages:
            if progress and show_dialogs and progress.wasCanceled():
                break
                
            # Request parameters with EXPLICIT from and to
            params = {
                'method': 'user.getrecenttracks',
                'user': self.lastfm_username,
                'api_key': self.lastfm_api_key,
                'format': 'json',
                'limit': 200,  # Maximum allowed by Last.fm
                'page': page
            }
            
            # Add from_timestamp if we have a previous update
            if last_updated > 0:
                params['from'] = last_updated  # Already added +1 above
                params['to'] = current_time
                self.log(f"Using time range: from={last_updated} to={current_time}")
            
            # Make the request
            try:
                url = f"https://ws.audioscrobbler.com/2.0/?{urllib.parse.urlencode(params)}"
                self.log(f"Making request to Last.fm API: {url}")
                response = requests.get(url)
                
                if response.status_code != 200:
                    self.log(f"Error: HTTP {response.status_code} from Last.fm API")
                    if page > 1:  # If we already got some pages, continue with what we have
                        break
                    else:
                        # Show error safely
                        if show_dialogs:
                            from PyQt6.QtWidgets import QMessageBox
                            from PyQt6.QtCore import QThread, QCoreApplication, QTimer
                            
                            error_msg = f"Last.fm API returned error: HTTP {response.status_code}"
                            
                            def show_error():
                                QMessageBox.warning(self, "Error", error_msg)
                            
                            # Verificar si estamos en el hilo principal
                            if QThread.currentThread() == QCoreApplication.instance().thread():
                                show_error()
                            else:
                                # Si no estamos en el hilo principal, programar para el hilo principal
                                QTimer.singleShot(0, show_error)
                        return False
                
                data = response.json()
                
                if 'error' in data:
                    self.log(f"Last.fm API error: {data.get('message', 'Unknown error')}")
                    if page > 1:  # If we already got some pages, continue with what we have
                        break
                    else:
                        # Show error safely
                        if show_dialogs:
                            from PyQt6.QtWidgets import QMessageBox
                            from PyQt6.QtCore import QThread, QCoreApplication, QTimer
                            
                            error_msg = f"Last.fm API error: {data.get('message', 'Unknown error')}"
                            
                            def show_error():
                                QMessageBox.warning(self, "Error", error_msg)
                            
                            # Verificar si estamos en el hilo principal
                            if QThread.currentThread() == QCoreApplication.instance().thread():
                                show_error()
                            else:
                                # Si no estamos en el hilo principal, programar para el hilo principal
                                QTimer.singleShot(0, show_error)
                        return False
                
                # Get total pages if first request
                if page == 1:
                    recenttracks = data.get('recenttracks', {})
                    attr = recenttracks.get('@attr', {})
                    total_pages = int(attr.get('totalPages', '1'))
                    total_results = int(attr.get('total', '0'))
                    
                    self.log(f"Found {total_results} scrobbles across {total_pages} pages")
                    
                    # If no new scrobbles were found, we can finish early
                    if total_results == 0:
                        self.log("No new scrobbles to synchronize")
                        update_progress(100, "No new scrobbles found")
                        
                        # Show completion message safely
                        if show_dialogs:
                            from PyQt6.QtWidgets import QMessageBox
                            from PyQt6.QtCore import QThread, QCoreApplication, QTimer
                            
                            completion_msg = f"No new scrobbles found for {self.lastfm_username} since last update."
                            
                            def show_completion():
                                QMessageBox.information(self, "Sync Complete", completion_msg)
                            
                            # Verificar si estamos en el hilo principal
                            if QThread.currentThread() == QCoreApplication.instance().thread():
                                show_completion()
                            else:
                                # Si no estamos en el hilo principal, programar para el hilo principal
                                QTimer.singleShot(0, show_completion)
                        return True
                    
                    # We found some new scrobbles
                    new_scrobbles_found = True
                
                # Process tracks
                tracks = data.get('recenttracks', {}).get('track', [])
                if not isinstance(tracks, list):
                    tracks = [tracks]  # Handle single track response
                
                for track in tracks:
                    # Skip 'now playing' tracks
                    if '@attr' in track and track['@attr'].get('nowplaying') == 'true':
                        continue
                        
                    # Create scrobble object matching the format
                    scrobble = {
                        'artist_name': track.get('artist', {}).get('#text', ''),
                        'artist_mbid': track.get('artist', {}).get('mbid', ''),
                        'name': track.get('name', ''),
                        'album_name': track.get('album', {}).get('#text', ''),
                        'album_mbid': track.get('album', {}).get('mbid', ''),
                        'timestamp': int(track.get('date', {}).get('uts', '0')),
                        'fecha_scrobble': track.get('date', {}).get('#text', ''),
                        'lastfm_url': track.get('url', ''),
                        'reproducciones': 1,
                        'fecha_reproducciones': json.dumps([track.get('date', {}).get('#text', '')])
                    }
                    
                    # Map to alternate field names
                    scrobble['artist'] = scrobble['artist_name']
                    scrobble['title'] = scrobble['name']
                    scrobble['album'] = scrobble['album_name']
                    
                    # Only add scrobbles that are after the last_updated timestamp
                    if scrobble['timestamp'] > last_updated:
                        all_scrobbles.append(scrobble)
                    else:
                        self.log(f"Skipping scrobble with older timestamp: {scrobble['timestamp']} <= {last_updated}")
                
                # Update progress
                progress_value = 20 + int(70 * (page / (total_pages or 1)))  # Avoid division by zero
                update_progress(progress_value, f"Procesando página {page} de {total_pages}...")
                
                # Next page
                page += 1
                
            except Exception as e:
                self.log(f"Error fetching scrobbles from Last.fm: {str(e)}")
                import traceback
                self.log(traceback.format_exc())
                break
        
        # Update progress to 90%
        update_progress(90, "Guardando scrobbles en la base de datos...")
        
        # Save directly to DB
        if all_scrobbles:
            self.log(f"Saving {len(all_scrobbles)} new scrobbles to database")
            
            # Save to DB - use the user-specific table
            saved_count = save_scrobbles_to_db(self, all_scrobbles, self.lastfm_username)
            self.log(f"Saved {saved_count} processed scrobbles to database")
            
            # Update the last_timestamp in the config table directly
            newest_timestamp = 0
            for scrobble in all_scrobbles:
                if scrobble['timestamp'] > newest_timestamp:
                    newest_timestamp = scrobble['timestamp']
            
            if newest_timestamp > db_timestamp:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(f"""
                UPDATE {config_table} 
                SET last_timestamp = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
                """, (newest_timestamp,))
                conn.commit()
                conn.close()
                self.log(f"Updated last_timestamp in config table to {newest_timestamp}")
            
            # Update cache if needed
            try:
                # Create directory if needed
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                
                # Load existing cache if available
                cache_data = {"last_updated": last_updated, "scrobbles": []}
                if os.path.exists(cache_file):
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cached_content = f.read()
                            if cached_content.strip():
                                cache_data = json.loads(cached_content)
                    except Exception as e:
                        self.log(f"Error loading cache: {e}, creating new cache")
                
                # Update with new max timestamp
                if newest_timestamp > 0:
                    cache_data['last_updated'] = max(newest_timestamp, cache_data.get('last_updated', 0))
                
                # Instead of merging, just keep the latest cache_data['scrobbles'] 
                # and append new scrobbles at the start
                # This keeps cache manageable by not growing indefinitely
                MAX_CACHE_SIZE = 1000  # Reasonable number to keep in cache
                
                # Add new scrobbles at the start of the list
                updated_scrobbles = all_scrobbles + cache_data.get('scrobbles', [])
                
                # Limit the size
                if len(updated_scrobbles) > MAX_CACHE_SIZE:
                    updated_scrobbles = updated_scrobbles[:MAX_CACHE_SIZE]
                
                cache_data['scrobbles'] = updated_scrobbles
                
                # Save updated cache
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2)
                    self.log(f"Updated cache with {len(all_scrobbles)} new scrobbles (total cache: {len(updated_scrobbles)})")
            except Exception as e:
                self.log(f"Error updating cache: {str(e)}")
                import traceback
                self.log(traceback.format_exc())

            try:
                # Obtener TODOS los años y meses de la base de datos actualizada
                table_name = f"scrobbles_{self.lastfm_username}"
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                years_dict = {}
                
                cursor.execute(f"""
                SELECT 
                    CAST(strftime('%Y', datetime(timestamp, 'unixepoch')) AS INTEGER) as year,
                    COUNT(*) as count
                FROM {table_name}
                WHERE timestamp > 0
                GROUP BY year
                ORDER BY year DESC
                """)
                
                years_results = cursor.fetchall()
                
                for year_row in years_results:
                    if not year_row[0]:
                        continue
                        
                    year = year_row[0]
                    count = year_row[1]
                    
                    if count > 0:
                        years_dict[year] = set()
                        
                        # Obtener meses para este año
                        cursor.execute(f"""
                        SELECT 
                            CAST(strftime('%m', datetime(timestamp, 'unixepoch')) AS INTEGER) as month,
                            COUNT(*) as count
                        FROM {table_name}
                        WHERE timestamp > 0 
                        AND strftime('%Y', datetime(timestamp, 'unixepoch')) = ?
                        GROUP BY month
                        ORDER BY month
                        """, (str(year),))
                        
                        months_results = cursor.fetchall()
                        
                        for month_row in months_results:
                            if not month_row[0]:
                                continue
                                
                            month = month_row[0]
                            month_count = month_row[1]
                            
                            if month_count > 0:
                                years_dict[year].add(month)
                
                conn.close()
                
                # Actualizar menús con TODOS los datos de forma segura
                if years_dict:
                    # Verificar si estamos en el hilo principal
                    from PyQt6.QtCore import QThread, QCoreApplication, QTimer
                    
                    if QThread.currentThread() == QCoreApplication.instance().thread():
                        # Estamos en el hilo principal, podemos actualizar directamente
                        populate_scrobbles_time_menus(self, years_dict=years_dict)
                        self.log(f"Menús actualizados con {len(years_dict)} años total después de sincronización")
                    else:
                        # No estamos en el hilo principal, programar para el hilo principal
                        self._pending_years_dict = years_dict
                        QTimer.singleShot(0, lambda: populate_scrobbles_time_menus(self, years_dict=self._pending_years_dict))
                        self.log(f"Programada actualización de menús con {len(years_dict)} años")
                    
            except Exception as e:
                self.log(f"Error actualizando menús después de sincronización: {str(e)}")
                import traceback
                self.log(traceback.format_exc())

            # Complete progress
            update_progress(100, f"Sincronización completada. Añadidos {saved_count} scrobbles.")
            
            # Show completion message safely
            if show_dialogs:
                from PyQt6.QtWidgets import QMessageBox
                from PyQt6.QtCore import QThread, QCoreApplication, QTimer
                
                completion_msg = f"Synchronized Last.fm scrobbles for {self.lastfm_username}.\n\n" + \
                                 f"Added {saved_count} new scrobbles."
                
                def show_completion():
                    QMessageBox.information(self, "Sync Complete", completion_msg)
                
                # Verificar si estamos en el hilo principal
                if QThread.currentThread() == QCoreApplication.instance().thread():
                    show_completion()
                else:
                    # Si no estamos en el hilo principal, programar para el hilo principal
                    QTimer.singleShot(0, show_completion)
            
            return True
        elif new_scrobbles_found:
            # We found tracks but couldn't process them
            update_progress(100, "Scrobbles encontrados pero no se pudieron procesar.")
            
            # Show warning safely
            if show_dialogs:
                from PyQt6.QtWidgets import QMessageBox
                from PyQt6.QtCore import QThread, QCoreApplication, QTimer
                
                warning_msg = f"Found scrobbles for {self.lastfm_username} but couldn't process them."
                
                def show_warning():
                    QMessageBox.warning(self, "Sync Issue", warning_msg)
                # Verificar si estamos en el hilo principal
                if QThread.currentThread() == QCoreApplication.instance().thread():
                    show_warning()
                else:
                    # Si no estamos en el hilo principal, programar para el hilo principal
                    QTimer.singleShot(0, show_warning)
            
            return False
        else:
            # No new scrobbles at all
            update_progress(100, "No hay nuevos scrobbles.")
            
            # Show info safely
            if show_dialogs:
                from PyQt6.QtWidgets import QMessageBox
                from PyQt6.QtCore import QThread, QCoreApplication, QTimer
                
                info_msg = f"No new scrobbles found for {self.lastfm_username} since last update."
                
                def show_info():
                    QMessageBox.information(self, "Sync Complete", info_msg)
                
                # Verificar si estamos en el hilo principal
                if QThread.currentThread() == QCoreApplication.instance().thread():
                    show_info()
                else:
                    # Si no estamos en el hilo principal, programar para el hilo principal
                    QTimer.singleShot(0, show_info)
            
            return True
    except Exception as e:
        self.log(f"Error synchronizing Last.fm scrobbles: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        
        # Show error safely
        if show_dialogs:
            from PyQt6.QtWidgets import QMessageBox
            from PyQt6.QtCore import QThread, QCoreApplication, QTimer
            
            error_msg = f"Error synchronizing Last.fm scrobbles: {str(e)}"
            
            def show_error():
                QMessageBox.warning(self, "Error", error_msg)
            
            # Verificar si estamos en el hilo principal
            if QThread.currentThread() == QCoreApplication.instance().thread():
                show_error()
            else:
                # Si no estamos en el hilo principal, programar para el hilo principal
                QTimer.singleShot(0, show_error)
        
        return False



# def extract_youtube_from_lastfm_soup(self, soup, lastfm_url):
#     """Extract YouTube URL from a Last.fm page soup with multiple strategies"""
#     try:
#         self.log("Searching for YouTube links in Last.fm page...")
        
#         # Strategy 1: Look for data-youtube-id and data-youtube-url attributes
#         youtube_elements = soup.find_all(attrs={'data-youtube-id': True})
#         for element in youtube_elements:
#             youtube_id = element.get('data-youtube-id')
#             if youtube_id:
#                 youtube_url = f"https://www.youtube.com/watch?v={youtube_id}"
#                 self.log(f"Found YouTube ID via data-youtube-id: {youtube_id}")
#                 return youtube_url
        
#         youtube_elements = soup.find_all(attrs={'data-youtube-url': True})
#         for element in youtube_elements:
#             youtube_url = element.get('data-youtube-url')
#             if youtube_url and ('youtube.com/watch' in youtube_url or 'youtu.be/' in youtube_url):
#                 self.log(f"Found YouTube URL via data-youtube-url: {youtube_url}")
#                 return youtube_url
        
#         # Strategy 2: Look for standard YouTube links in href attributes
#         for link in soup.find_all('a', href=True):
#             href = link['href']
#             if 'youtube.com/watch' in href or 'youtu.be/' in href:
#                 # Convert relative URLs to absolute
#                 if href.startswith('/'):
#                     href = urljoin('https://youtube.com', href)
#                 elif href.startswith('//'):
#                     href = 'https:' + href
                    
#                 self.log(f"Found YouTube URL via href: {href}")
#                 return href
        
#         # Strategy 3: Look for YouTube URLs in onclick attributes or JavaScript
#         onclick_elements = soup.find_all(attrs={'onclick': True})
#         for element in onclick_elements:
#             onclick = element.get('onclick', '')
#             youtube_match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', onclick)
#             if youtube_match:
#                 youtube_id = youtube_match.group(1)
#                 youtube_url = f"https://www.youtube.com/watch?v={youtube_id}"
#                 self.log(f"Found YouTube ID via onclick: {youtube_id}")
#                 return youtube_url
        
#         # Strategy 4: Search in script tags for YouTube references
#         script_tags = soup.find_all('script')
#         for script in script_tags:
#             if script.string:
#                 # Look for YouTube video IDs in JavaScript
#                 youtube_matches = re.findall(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', script.string)
#                 if youtube_matches:
#                     youtube_id = youtube_matches[0]  # Take the first match
#                     youtube_url = f"https://www.youtube.com/watch?v={youtube_id}"
#                     self.log(f"Found YouTube ID in script: {youtube_id}")
#                     return youtube_url
                    
#                 # Look for YouTube video IDs in a different format
#                 youtube_id_matches = re.findall(r'"([a-zA-Z0-9_-]{11})"', script.string)
#                 for potential_id in youtube_id_matches:
#                     # YouTube video IDs are typically 11 characters
#                     if len(potential_id) == 11 and re.match(r'^[a-zA-Z0-9_-]+$', potential_id):
#                         youtube_url = f"https://www.youtube.com/watch?v={potential_id}"
#                         self.log(f"Found potential YouTube ID in script: {potential_id}")
#                         return youtube_url
        
#         self.log("No YouTube links found in Last.fm page")
#         return None
        
#     except Exception as e:
#         self.log(f"Error extracting YouTube from soup: {str(e)}")
#         import traceback
#         self.log(traceback.format_exc())
#         return None

# def extract_spotify_from_lastfm_soup(self, soup, lastfm_url):
#     """Extract Spotify URL from a Last.fm page soup"""
#     try:
#         self.log("Searching for Spotify links in Last.fm page...")
        
#         # Strategy 1: Look for data-spotify-id or similar attributes
#         spotify_elements = soup.find_all(attrs={'data-spotify-id': True})
#         for element in spotify_elements:
#             spotify_id = element.get('data-spotify-id')
#             if spotify_id:
#                 spotify_url = f"https://open.spotify.com/track/{spotify_id}"
#                 self.log(f"Found Spotify ID via data-spotify-id: {spotify_id}")
#                 return spotify_url
        
#         # Strategy 2: Look for Spotify links in href attributes
#         for link in soup.find_all('a', href=True):
#             href = link['href']
#             if 'open.spotify.com' in href:
#                 self.log(f"Found Spotify URL via href: {href}")
#                 return href
        
#         # Strategy 3: Look in script tags for Spotify references
#         script_tags = soup.find_all('script')
#         for script in script_tags:
#             if script.string:
#                 spotify_matches = re.findall(r'open\.spotify\.com/track/([a-zA-Z0-9]+)', script.string)
#                 if spotify_matches:
#                     spotify_id = spotify_matches[0]
#                     spotify_url = f"https://open.spotify.com/track/{spotify_id}"
#                     self.log(f"Found Spotify ID in script: {spotify_id}")
#                     return spotify_url
        
#         self.log("No Spotify links found in Last.fm page")
#         return None
        
#     except Exception as e:
#         self.log(f"Error extracting Spotify from soup: {str(e)}")
#         return None

# def extract_bandcamp_from_lastfm_soup(self, soup, lastfm_url):
#     """Extract Bandcamp URL from a Last.fm page soup"""
#     try:
#         self.log("Searching for Bandcamp links in Last.fm page...")
        
#         # Look for Bandcamp links
#         for link in soup.find_all('a', href=True):
#             href = link['href']
#             if 'bandcamp.com' in href and '/track/' in href:
#                 self.log(f"Found Bandcamp URL via href: {href}")
#                 return href
        
#         self.log("No Bandcamp links found in Last.fm page")
#         return None
        
#     except Exception as e:
#         self.log(f"Error extracting Bandcamp from soup: {str(e)}")
#         return None

# def extract_soundcloud_from_lastfm_soup(self, soup, lastfm_url):
#     """Extract SoundCloud URL from a Last.fm page soup"""
#     try:
#         self.log("Searching for SoundCloud links in Last.fm page...")
        
#         # Look for SoundCloud links
#         for link in soup.find_all('a', href=True):
#             href = link['href']
#             if 'soundcloud.com' in href and not href.endswith('/soundcloud.com'):
#                 self.log(f"Found SoundCloud URL via href: {href}")
#                 return href
        
#         self.log("No SoundCloud links found in Last.fm page")
#         return None
        
#     except Exception as e:
#         self.log(f"Error extracting SoundCloud from soup: {str(e)}")
#         return None



def load_lastfm_scrobbles_period(self, period):
    """Load Last.fm scrobbles for a specific time period from database"""
    try:
        if not hasattr(self, 'lastfm_username') or not self.lastfm_username:
            self.log(f"Error: Last.fm username not configured")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "Last.fm username not configured. Please set in settings.")
            return False
        
        # Determine time range
        import time
        current_time = int(time.time())
        start_time = 0
        title = ""

        if period == "24h":  # NUEVA OPCIÓN
            start_time = current_time - (24 * 60 * 60)  # 24 horas
            title = "Últimas 24 horas"
        elif period == "week":
            start_time = current_time - (7 * 24 * 60 * 60)  # 7 days
            title = "Última semana"
        elif period == "month":
            start_time = current_time - (30 * 24 * 60 * 60)  # 30 days
            title = "Último mes"
        elif period == "year":
            start_time = current_time - (365 * 24 * 60 * 60)  # 365 days
            title = "Último año"
        
        # Ensure we have a non-zero limit for scrobbles
        scrobbles_limit = getattr(self, 'scrobbles_limit', 100)
        if not scrobbles_limit or scrobbles_limit <= 0:
            scrobbles_limit = 100
            self.log(f"Using default limit of 100 scrobbles")
        
        # Load scrobbles from database using corrected function
        from modules.submodules.url_playlist.lastfm_db import load_scrobbles_from_db
        scrobbles = load_scrobbles_from_db(
            self, 
            self.lastfm_username, 
            start_time=start_time,
            limit=scrobbles_limit
        )
        
        # If no scrobbles found, try alternate table names
        if not scrobbles:
            self.log(f"No scrobbles found for period {period} in main table, trying alternates")
            
            alternate_users = ["paqueradejere"]
            for alt_user in alternate_users:
                alt_scrobbles = load_scrobbles_from_db(
                    self, 
                    alt_user, 
                    start_time=start_time,
                    limit=scrobbles_limit
                )
                if alt_scrobbles:
                    scrobbles = alt_scrobbles
                    self.log(f"Found {len(scrobbles)} scrobbles in alternate table for {alt_user}")
                    break
        
        if not scrobbles:
            self.log(f"No scrobbles found for period {period}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "No Data", f"No scrobbles found for {title}. Try syncing first.")
            return False
        
        # Add a flag to indicate if this is 24h data (to show time in display)
        for scrobble in scrobbles:
            scrobble['show_time'] = (period == "24h")
        
        # Display in tree
        from modules.submodules.url_playlist.lastfm_db import display_scrobbles_in_tree
        display_scrobbles_in_tree(self, scrobbles, title)
        
        return True
    except Exception as e:
        self.log(f"Error loading scrobbles for period {period}: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False

def load_lastfm_scrobbles_month(self, year, month):
    """
    Load Last.fm scrobbles for a specific year and month from database with improved table joining.
    
    Args:
        self: The parent object with necessary attributes and methods
        year: Year to load
        month: Month to load
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        if not hasattr(self, 'lastfm_username') or not self.lastfm_username:
            self.log(f"Error: Last.fm username not configured")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "Last.fm username not configured. Please set in settings.")
            return False
        
        # Calculate start and end timestamps for the month
        import datetime
        if month == 12:
            end_year = year + 1
            end_month = 1
        else:
            end_year = year
            end_month = month + 1
            
        start = datetime.datetime(year, month, 1, 0, 0, 0).timestamp()
        end = datetime.datetime(end_year, end_month, 1, 0, 0, 0).timestamp()
        
        # Ensure scrobbles_limit is set
        if not hasattr(self, 'scrobbles_limit') or not self.scrobbles_limit:
            self.scrobbles_limit = 100
        
        # Load scrobbles from database using the improved function
        from modules.submodules.url_playlist.lastfm_db import load_scrobbles_from_db
        scrobbles = load_scrobbles_from_db(self, self.lastfm_username, start_time=start, end_time=end, limit=self.scrobbles_limit)
        
        # If no scrobbles found, try alternate table names
        if not scrobbles:
            self.log(f"No scrobbles found for {month}/{year} in main table, trying alternates")
            
            alternate_users = ["paqueradejere"]
            for alt_user in alternate_users:
                alt_scrobbles = load_scrobbles_from_db(self, alt_user, start_time=start, end_time=end, limit=self.scrobbles_limit)
                if alt_scrobbles:
                    scrobbles = alt_scrobbles
                    self.log(f"Found {len(scrobbles)} scrobbles in alternate table for {alt_user}")
                    break
        
        if not scrobbles:
            self.log(f"No scrobbles found for {month}/{year}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "No Data", f"No scrobbles found for {month}/{year}. Try syncing first.")
            return False
        
        # Get month name
        month_name = datetime.datetime(year, month, 1).strftime("%B")
        title = f"{month_name} {year}"
        
        # Display in tree using the improved display function
        from modules.submodules.url_playlist.lastfm_db import display_scrobbles_in_tree
        display_scrobbles_in_tree(self, scrobbles, title)
        
        return True
    except Exception as e:
        self.log(f"Error loading scrobbles for {month}/{year}: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False
def load_lastfm_scrobbles_year(self, year):
    """
    Load Last.fm scrobbles for a specific year from database with improved table joining.
    
    Args:
        self: The parent object with necessary attributes and methods
        year: Year to load
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        if not hasattr(self, 'lastfm_username') or not self.lastfm_username:
            self.log(f"Error: Last.fm username not configured")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "Last.fm username not configured. Please set in settings.")
            return False
        
        # Calculate start and end timestamps for the year
        import datetime
        start = datetime.datetime(year, 1, 1, 0, 0, 0).timestamp()
        end = datetime.datetime(year + 1, 1, 1, 0, 0, 0).timestamp()
        
        # Ensure scrobbles_limit is set
        if not hasattr(self, 'scrobbles_limit') or not self.scrobbles_limit:
            self.scrobbles_limit = 100
        
        # Load scrobbles from database using the improved function
        from modules.submodules.url_playlist.lastfm_db import load_scrobbles_from_db
        scrobbles = load_scrobbles_from_db(self, self.lastfm_username, start_time=start, end_time=end, limit=self.scrobbles_limit)
        
        # If no scrobbles found, try alternate table names
        if not scrobbles:
            self.log(f"No scrobbles found for year {year} in main table, trying alternates")
            
            alternate_users = ["paqueradejere"]
            for alt_user in alternate_users:
                alt_scrobbles = load_scrobbles_from_db(self, alt_user, start_time=start, end_time=end, limit=self.scrobbles_limit)
                if alt_scrobbles:
                    scrobbles = alt_scrobbles
                    self.log(f"Found {len(scrobbles)} scrobbles in alternate table for {alt_user}")
                    break
        
        if not scrobbles:
            self.log(f"No scrobbles found for year {year}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "No Data", f"No scrobbles found for year {year}. Try syncing first.")
            return False
        
        # Display in tree using the improved display function
        from modules.submodules.url_playlist.lastfm_db import display_scrobbles_in_tree
        display_scrobbles_in_tree(self, scrobbles, f"Año {year}")
        
        return True
    except Exception as e:
        self.log(f"Error loading scrobbles for year {year}: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False




def populate_scrobbles_time_menus(self, scrobbles=None, years_dict=None):
    """Populate the year and month menus based on available scrobbles in database"""
    try:
        # Verificar que estamos en el hilo principal
        from PyQt6.QtCore import QThread, QCoreApplication, QTimer
        
        if QThread.currentThread() != QCoreApplication.instance().thread():
            # Si no estamos en el hilo principal, guardar datos y programar
            self._pending_populate_data = (scrobbles, years_dict)
            QTimer.singleShot(0, lambda: self._safe_populate_menus())
            return True
            
        # Continuamos solo si estamos en el hilo principal
        
        # Gather menu references
        menus_to_update = []
        
        # Add main scrobbles button menus if they exist
        if hasattr(self, 'months_menu') and hasattr(self, 'years_menu'):
            if self.months_menu and self.years_menu:
                if self.months_menu.actions() and self.years_menu.actions() and not years_dict:
                    return True
        
        # Add unified button menus if they exist
        if hasattr(self, 'unified_months_menu') and hasattr(self, 'unified_years_menu'):
            menus_to_update.append({
                'months': self.unified_months_menu, 
                'years': self.unified_years_menu
            })
        
        if not menus_to_update:
            self.log("No menus found to update")
            return False
            
        # If years_dict is provided directly, use it
        if years_dict:
            self.log(f"Using provided years_dict with {len(years_dict)} years")
        # If no years_dict provided and no scrobbles, load from database
        elif not scrobbles:
            try:
                # First check database for available years and months
                import sqlite3
                from datetime import datetime
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                years_dict = {}
                
                # Try all possible table name variants for this user
                user = getattr(self, 'lastfm_username', 'paqueradejere')
                table_names = [
                    f"scrobbles_{user}",
                    "scrobbles_paqueradejere",
                    user
                ]
                
                table_found = False
                
                for table_name in table_names:
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                    
                    if cursor.fetchone():
                        table_found = True
                        self.log(f"Found scrobbles table: {table_name}")
                        
                        # Check schema for timestamp column
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = [row[1] for row in cursor.fetchall()]
                        
                        if 'timestamp' not in columns:
                            self.log(f"No timestamp column in {table_name}")
                            continue
                        
                        # Get distinct years with count - FIXED QUERY
                        try:
                            cursor.execute(f"""
                            SELECT strftime('%Y', datetime(timestamp, 'unixepoch', 'localtime')) as year, 
                                COUNT(*) as count
                            FROM {table_name}
                            WHERE timestamp > 0
                            GROUP BY year
                            ORDER BY year DESC
                            """)
                            
                            years_results = cursor.fetchall()
                            
                            self.log(f"Found {len(years_results)} years in {table_name}")
                            
                            for year_row in years_results:
                                try:
                                    year = int(year_row[0])
                                    
                                    # Check if we have any scrobbles for this year
                                    if year_row[1] > 0:
                                        years_dict[year] = set()
                                        
                                        # Get months for this year
                                        cursor.execute(f"""
                                        SELECT strftime('%m', datetime(timestamp, 'unixepoch', 'localtime')) as month,
                                            COUNT(*) as count
                                        FROM {table_name}
                                        WHERE timestamp > 0 
                                        AND strftime('%Y', datetime(timestamp, 'unixepoch', 'localtime')) = ?
                                        GROUP BY month
                                        ORDER BY month
                                        """, (str(year),))
                                        
                                        months_results = cursor.fetchall()
                                        
                                        for month_row in months_results:
                                            if month_row[1] > 0:
                                                try:
                                                    month = int(month_row[0])
                                                    years_dict[year].add(month)
                                                except (ValueError, TypeError) as e:
                                                    self.log(f"Error parsing month: {e}")
                                except (ValueError, TypeError) as e:
                                    self.log(f"Error parsing year: {e}")
                            
                            self.log(f"Found {len(years_dict)} years with data in {table_name}")
                            break  # Use the first valid table we find
                            
                        except sqlite3.Error as e:
                            self.log(f"Error querying {table_name}: {e}")
                            continue
                
                if not table_found:
                    self.log("No valid scrobbles table found")
                
                conn.close()
                
                if not years_dict:
                    self.log("No scrobble years/months found in database")
                    return False
                    
            except Exception as e:
                self.log(f"Error querying database for dates: {str(e)}")
                years_dict = {}
        
        # If we couldn't load from database and don't have scrobbles parameter, try cache
        if not years_dict and not scrobbles:
            try:
                # Try to load from cache
                cache_file = get_lastfm_cache_path(getattr(self, 'lastfm_username', None))
                if os.path.exists(cache_file):
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        
                    scrobbles = cache_data.get('scrobbles', [])
                    self.log(f"Loaded {len(scrobbles)} scrobbles from cache")
            except Exception as e:
                self.log(f"Error loading cache: {str(e)}")
                scrobbles = []
        
        # If we have scrobbles but no years_dict, extract years/months
        if scrobbles and not years_dict:
            years_dict = {}
            
            for scrobble in scrobbles:
                timestamp = scrobble.get('timestamp')
                if not timestamp:
                    continue
                    
                try:
                    timestamp = int(timestamp)
                    from datetime import datetime
                    date = datetime.fromtimestamp(timestamp)
                    year = date.year
                    month = date.month
                    
                    if year not in years_dict:
                        years_dict[year] = set()
                    
                    years_dict[year].add(month)
                except (ValueError, TypeError, OverflowError) as e:
                    self.log(f"Error processing timestamp {timestamp}: {str(e)}")
                    continue
        
        if not years_dict:
            self.log("No valid years/months found in scrobbles or database")
            return False
        
        self.log(f"Prepared years dictionary with {len(years_dict)} years")
        
        # Update each set of menus
        for menu_set in menus_to_update:
            months_menu = menu_set.get('months')
            years_menu = menu_set.get('years')
            
            if not months_menu or not years_menu:
                continue
                
            # Clear menus
            months_menu.clear()
            years_menu.clear()
            
            # Populate Years menu
            years = sorted(years_dict.keys(), reverse=True)
            for year in years:
                year_action = years_menu.addAction(str(year))
                # Use lambda with default value to capture the current value
                year_action.triggered.connect(lambda checked=False, y=year: load_lastfm_scrobbles_year(self, y))
            
            # Populate Months menu (years as submenus, months within each year)
            for year in years:
                year_menu = months_menu.addMenu(str(year))
                
                # Get months for this year and sort them
                months = sorted(years_dict[year])
                
                # Add month items
                for month in months:
                    # Use the current locale for month names
                    try:
                        import datetime
                        date_obj = datetime.datetime(2000, month, 1)
                        month_name = date_obj.strftime("%B")
                    except:
                        month_name = f"Month {month}"
                        
                    month_action = year_menu.addAction(month_name)
                    # Use lambda with default values to capture the current values
                    month_action.triggered.connect(lambda checked=False, y=year, m=month: load_lastfm_scrobbles_month(self, y, m))
        
                self.log(f"Populated scrobbles menus with {len(years)} years")
        return True
    except Exception as e:
        self.log(f"Error populating scrobbles time menus: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False

def _safe_populate_menus(self):
    """Versión segura para poblar menús en el hilo principal"""
    try:
        # Recuperar datos pendientes
        scrobbles, years_dict = getattr(self, '_pending_populate_data', (None, None))
        # Limpiar datos pendientes
        if hasattr(self, '_pending_populate_data'):
            del self._pending_populate_data
            
        # Llamar a la función original ahora que estamos en el hilo principal
        populate_scrobbles_time_menus(self, scrobbles, years_dict)
    except Exception as e:
        self.log(f"Error en _safe_populate_menus: {str(e)}")


def get_track_links_from_db(self, artist, title, album=None):
    """Get track links from the database"""
    try:
        # Use the get_detailed_info method foundation
        if not self.db_path or not os.path.exists(self.db_path):
            self.log(f"Database not found at: {self.db_path}")
            return None
        
        # Import the database query class
        from db.tools.consultar_items_db import MusicDatabaseQuery
        
        db = MusicDatabaseQuery(self.db_path)
        
        # Get track links
        if album:
            track_links = db.get_track_links(album, title)
        else:
            # Try to find without album
            # First get song info to find album
            song_info = db.get_song_info(title, artist)
            if song_info and song_info.get('album'):
                track_links = db.get_track_links(song_info['album'], title)
            else:
                # If we don't have album info, we can't get links this way
                track_links = None
        
        # If we didn't find links via track, try artist->album->track path
        if not track_links:
            # Get albums by artist
            artist_albums = db.get_artist_albums(artist)
            if artist_albums:
                for album_tuple in artist_albums:
                    album_name = album_tuple[0]
                    
                    # Get album info
                    album_info = db.get_album_info(album_name, artist)
                    
                    if album_info and 'songs' in album_info:
                        for song in album_info['songs']:
                            if song.get('title', '').lower() == title.lower():
                                # Found the track, get links
                                track_links = db.get_track_links(album_name, title)
                                if track_links:
                                    break
                    
                    if track_links:
                        break
        
        db.close()
        return track_links
        
    except Exception as e:
        self.log(f"Error getting track links from database: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return None


def setup_scrobbles_menu(self):
    """Configure the scrobbles menu for the Last.fm button"""
    try:
        # Find the scrobbles button
        self.scrobbles_button = self.findChild(QPushButton, 'scrobbles_menu')
        
        if not self.scrobbles_button:
            self.log("Error: Scrobbles button not found")
            return False
            
        # Create the menu
        self.scrobbles_menu = QMenu(self.scrobbles_button)
        
        # Set up Last.fm menu items
        menu_refs = setup_lastfm_menu_items(self, self.scrobbles_menu)
        
        # Store menu references
        self.months_menu = menu_refs.get('months_menu')
        self.years_menu = menu_refs.get('years_menu')
        
        # Set the menu for the button
        self.scrobbles_button.setMenu(self.scrobbles_menu)

        # Asegurarnos de que los menús se carguen inmediatamente
        def load_existing_data():
            try:
                # Verificar que estamos en el hilo principal
                from PyQt6.QtCore import QThread, QCoreApplication
                if QThread.currentThread() == QCoreApplication.instance().thread():
                    # Intentar cargar datos existentes directamente
                    force_load_scrobbles_data_from_db(self)
                    
                    # Como respaldo, intentar también llenar los menús directamente
                    if hasattr(self, 'db_path') and os.path.exists(self.db_path):
                        years_dict = load_years_months_from_db_direct(self)
                        if years_dict:
                            populate_scrobbles_time_menus(self, years_dict=years_dict)
                else:
                    # Si no estamos en el hilo principal, programar para el hilo principal
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, load_existing_data)
            except Exception as e:
                self.log(f"Error loading existing scrobbles data: {str(e)}")

        # Usar QTimer para asegurar que la UI esté lista
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, load_existing_data)  # Aumentar el delay a 500ms

        self.log("Scrobbles menu set up")
        return True
    except Exception as e:
        self.log(f"Error setting up scrobbles menu: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False


def load_years_months_from_db_direct(self):
    """
    Cargar directamente años y meses desde la base de datos sin usar hilos
    """
    try:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        years_dict = {}
        
        # Buscar todas las tablas de scrobbles
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'scrobbles_%' OR name = 'scrobbles')")
        all_tables = cursor.fetchall()
        scrobbles_tables = [row[0] for row in all_tables]
        
        self.log(f"Found tables: {', '.join(scrobbles_tables)}")
        
        # Priorizar la tabla del usuario actual
        user = getattr(self, 'lastfm_username', 'paqueradejere')
        user_table = f"scrobbles_{user}"
        
        if user_table in scrobbles_tables:
            table_name = user_table
        elif "scrobbles_paqueradejere" in scrobbles_tables:
            table_name = "scrobbles_paqueradejere"
        elif scrobbles_tables:
            table_name = scrobbles_tables[0]
        else:
            self.log("No scrobbles tables found")
            conn.close()
            return {}
        
        self.log(f"Using scrobbles table: {table_name}")
        
        # Verificar que tiene timestamp
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'timestamp' not in columns:
            self.log(f"Table {table_name} has no timestamp column")
            conn.close()
            return {}
        
        # Obtener años
        cursor.execute(f"""
        SELECT strftime('%Y', datetime(timestamp, 'unixepoch')) as year, COUNT(*) as count
        FROM {table_name}
        WHERE timestamp > 0
        GROUP BY year
        ORDER BY year DESC
        """)
        
        years_results = cursor.fetchall()
        
        for year_row in years_results:
            if not year_row[0]:
                continue
                
            try:
                year = int(year_row[0])
                count = year_row[1]
                
                if count > 0:
                    years_dict[year] = set()
                    
                    # Obtener meses para este año
                    cursor.execute(f"""
                    SELECT strftime('%m', datetime(timestamp, 'unixepoch')) as month, COUNT(*) as count
                    FROM {table_name}
                    WHERE timestamp > 0 
                    AND strftime('%Y', datetime(timestamp, 'unixepoch')) = ?
                    GROUP BY month
                    ORDER BY month
                    """, (str(year),))
                    
                    months_results = cursor.fetchall()
                    
                    for month_row in months_results:
                        if month_row[1] > 0:
                            try:
                                month = int(month_row[0])
                                years_dict[year].add(month)
                            except (ValueError, TypeError):
                                pass
            except (ValueError, TypeError):
                pass
        
        conn.close()
        
        self.log(f"Loaded {len(years_dict)} years with months from database")
        return years_dict
        
    except Exception as e:
        self.log(f"Error in load_years_months_from_db_direct: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return {}

def connect_lastfm_controls(self):
    """Connect Last.fm controls (slider and spinbox) bidirectionally"""
    try:
        # Find the controls
        scrobbles_slider = self.findChild(QSlider, 'scrobbles_slider')
        scrobbles_spinbox = self.findChild(QSpinBox, 'scrobblers_spinBox')
        
        if scrobbles_slider and scrobbles_spinbox:
            # Set proper ranges
            scrobbles_slider.setMinimum(25)
            scrobbles_slider.setMaximum(1000)
            scrobbles_spinbox.setMinimum(25)
            scrobbles_spinbox.setMaximum(1000)
            
            # Block signals during initial setup
            scrobbles_slider.blockSignals(True)
            scrobbles_spinbox.blockSignals(True)
            
            # Set initial values
            scrobbles_slider.setValue(self.scrobbles_limit)
            scrobbles_spinbox.setValue(self.scrobbles_limit)
            
            # Unblock signals
            scrobbles_slider.blockSignals(False)
            scrobbles_spinbox.blockSignals(False)
            
            # Connect bidirectionally
            scrobbles_slider.valueChanged.connect(scrobbles_spinbox.setValue)
            scrobbles_spinbox.valueChanged.connect(scrobbles_slider.setValue)
            
            # Also connect to save settings on change
            scrobbles_slider.valueChanged.connect(lambda value: self.set_scrobbles_limit(value))
            
            self.log("Connected Last.fm controls")
            return True
        else:
            self.log("Could not find scrobbles slider or spinbox")
            return False
    except Exception as e:
        self.log(f"Error connecting Last.fm controls: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False



def load_lastfm_cache_if_exists(self):
    """Versión optimizada para cargar caché de Last.fm con validación de tiempo"""
    try:
        # Si ya hemos cargado la caché recientemente, no lo hacemos de nuevo
        if hasattr(self, '_lastfm_cache_loaded_time'):
            import time
            if time.time() - self._lastfm_cache_loaded_time < 600:  # 10 minutos
                self.log("Cache de Last.fm ya cargada recientemente")
                return True
        
        # Intentar cargar desde DB primero (más eficiente)
        db_result = load_years_months_from_db(self)
        
        if db_result:
            self.log("Datos de Last.fm cargados desde base de datos")
            self._lastfm_cache_loaded_time = time.time()
            return True
        
        # Si falló la carga desde DB, intentar con caché
        self.lastfm_username = getattr(self, 'lastfm_username', None)
        cache_file = get_lastfm_cache_path(self.lastfm_username)
        
        if os.path.exists(cache_file):
            self.log(f"Encontrado archivo de caché de Last.fm: {cache_file}")
            
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    scrobbles = cache_data.get('scrobbles', [])
                    
                    if scrobbles:
                        self.log(f"Cargados {len(scrobbles)} scrobbles desde caché")
                        # Poblar menús
                        populate_scrobbles_time_menus(self, scrobbles)
                        self._lastfm_cache_loaded_time = time.time()
                        return True
            except Exception as e:
                self.log(f"Error loading Last.fm cache: {str(e)}")
        
        return False
    except Exception as e:
        self.log(f"Error checking Last.fm data: {str(e)}")
        return False



def get_latest_timestamp_from_db(self, table_name):
    """
    Get the latest timestamp from the database for the specified table.
    
    Args:
        table_name: Name of the table to query
        
    Returns:
        Latest timestamp or 0 if no records
    """
    try:
        if not hasattr(self, 'db_path') or not self.db_path:
            return 0
            
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            conn.close()
            return 0
        
        # Get the latest timestamp
        cursor.execute(f"SELECT MAX(timestamp) FROM {table_name}")
        result = cursor.fetchone()
        
        conn.close()
        
        if result and result[0]:
            self.log(f"Latest timestamp from database: {result[0]}")
            return result[0]
        
        return 0
    except Exception as e:
        self.log(f"Error getting latest timestamp: {str(e)}")
        return 0



def obtener_scrobbles_lastfm(lastfm_username, lastfm_api_key, desde_timestamp=0, limite=200):
    """
    Obtiene todos los scrobbles de Last.fm para un usuario.
    
    Args:
        lastfm_username: Nombre de usuario de Last.fm
        lastfm_api_key: API key de Last.fm
        desde_timestamp: Timestamp desde el que obtener scrobbles
        limite: Número máximo de scrobbles por página
        
    Returns:
        Lista de scrobbles obtenidos
    """
    todos_scrobbles = []
    pagina = 1
    total_paginas = 1
    
    # Mensaje inicial
    if desde_timestamp > 0:
        fecha = datetime.fromtimestamp(desde_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        self.log(f"Obteniendo scrobbles desde {fecha}")
    else:
        self.log("Obteniendo todos los scrobbles (esto puede tardar bastante)")
    
    while pagina <= total_paginas:
        self.log(f"Obteniendo página {pagina} de {total_paginas}...")
        
        params = {
            'method': 'user.getrecenttracks',
            'user': lastfm_username,
            'api_key': lastfm_api_key,
            'format': 'json',
            'limit': limite,
            'page': pagina,
            'from': desde_timestamp
        }
        
        try:
            response = obtener_con_reintentos('http://ws.audioscrobbler.com/2.0/', params)
            
            if not response or response.status_code != 200:
                error_msg = f"Error al obtener scrobbles: {response.status_code if response else 'Sin respuesta'}"
                self.log(error_msg)
                
                if pagina > 1:  # Si hemos obtenido algunas páginas, devolvemos lo que tenemos
                    break
                else:
                    return []
            
            data = response.json()
            
        except Exception as e:
            self.log(f"Error al procesar página {pagina}: {str(e)}")
            
            if pagina > 1:  # Si hemos obtenido algunas páginas, devolvemos lo que tenemos
                break
            else:
                return []
        
        # Comprobar si hay tracks
        if 'recenttracks' not in data or 'track' not in data['recenttracks']:
            break
        
        # Actualizar total_paginas
        total_paginas = int(data['recenttracks']['@attr']['totalPages'])
        
        # Añadir tracks a la lista
        tracks = data['recenttracks']['track']
        if not isinstance(tracks, list):
            tracks = [tracks]
        
        # Filtrar tracks que están siendo escuchados actualmente (no tienen date)
        filtrados = [track for track in tracks if 'date' in track]
        todos_scrobbles.extend(filtrados)
        
        # Reportar progreso
        self.log(f"Obtenidos {len(filtrados)} scrobbles en página {pagina}")
        
        pagina += 1
        # Pequeña pausa para no saturar la API
        time.sleep(0.25)
    
    self.log(f"Obtenidos {len(todos_scrobbles)} scrobbles en total")
    return todos_scrobbles


def obtener_con_reintentos(url, params, max_reintentos=3, tiempo_espera=1, timeout=10):
    """
    Realiza una petición HTTP con reintentos en caso de error.
    
    Args:
        url: URL a consultar
        params: Parámetros para la petición
        max_reintentos: Número máximo de reintentos
        tiempo_espera: Tiempo base de espera entre reintentos
        timeout: Tiempo máximo de espera para la petición
        
    Returns:
        Respuesta HTTP o None si fallan todos los intentos
    """
    for intento in range(max_reintentos):
        try:
            respuesta = requests.get(url, params=params, timeout=timeout)
            
            # Si hay límite de tasa, esperar y reintentar
            if respuesta.status_code == 429:  # Rate limit
                tiempo_espera_recomendado = int(respuesta.headers.get('Retry-After', tiempo_espera * 2))
                self.log(f"Límite de tasa alcanzado. Esperando {tiempo_espera_recomendado} segundos...")
                time.sleep(tiempo_espera_recomendado)
                continue
            
            return respuesta
            
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            self.log(f"Error en intento {intento+1}/{max_reintentos}: {e}")
            if intento < max_reintentos - 1:
                # Backoff exponencial
                tiempo_espera_actual = tiempo_espera * (2 ** intento)
                self.log(f"Reintentando en {tiempo_espera_actual} segundos...")
                time.sleep(tiempo_espera_actual)
    
    return None


def fetch_youtube_links(self, scrobbles, cache_file, table_name=None):
    """
    Fetch URLs for scrobbles in a background thread, checking database first
    and updating both the cache and the song_links table.
    
    Args:
        self: The parent instance with logger
        scrobbles: List of scrobbles to check
        cache_file: Path to the cache file to update
        table_name: Optional name of the scrobbles table
    """
    try:
        self.log(f"Starting link fetching for {len(scrobbles)} scrobbles")
        
        # Load the current cache
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
        except Exception as e:
            self.log(f"Error loading cache file for link updates: {str(e)}")
            return
        
        # Track scrobbles by a unique key for efficient updates
        all_scrobbles = cache_data.get('scrobbles', [])
        scrobbles_dict = {}
        for s in all_scrobbles:
            # Support both field naming conventions
            artist = s.get('artist', s.get('artist_name', ''))
            title = s.get('title', s.get('name', ''))
            timestamp = s.get('timestamp', 0)
            key = f"{artist}|{title}|{timestamp}"
            scrobbles_dict[key] = s
        
        # Get service priority from settings
        service_priority = get_service_priority(self) if hasattr(self, 'get_service_priority') else ['youtube', 'spotify', 'bandcamp', 'soundcloud']
        self.log(f"Service priority: {', '.join(service_priority)}")
        
        # Database connection 
        db_conn = None
        db_cursor = None
        
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            try:
                import sqlite3
                db_conn = sqlite3.connect(self.db_path)
                db_cursor = db_conn.cursor()
                self.log(f"Connected to database for updating links")
            except Exception as e:
                self.log(f"Error connecting to database: {str(e)}")
        
        # Process each scrobble
        processed_count = 0
        updated_count = 0
        
        for scrobble in scrobbles:
            # Get fields, handling both naming conventions
            artist = scrobble.get('artist', scrobble.get('artist_name', ''))
            title = scrobble.get('title', scrobble.get('name', ''))
            album = scrobble.get('album', scrobble.get('album_name', ''))
            timestamp = scrobble.get('timestamp', 0)
            
            # Skip if already has a URL for any service
            if any(scrobble.get(f'{service}_url') for service in service_priority):
                continue
                
            # Create a unique key
            key = f"{artist}|{title}|{timestamp}"
            
            # Try to get URL from database first
            links = get_track_links_from_db(self, artist, title, album)
            
            if links:
                # Check for each service in priority order
                for service in service_priority:
                    if service in links and links[service]:
                        # Update the scrobble
                        service_url_key = f'{service}_url'
                        scrobble[service_url_key] = links[service]
                        
                        if key in scrobbles_dict:
                            scrobbles_dict[key][service_url_key] = links[service]
                            updated_count += 1
                            
                            # Log successful link retrieval
                            self.log(f"Found {service} link for {artist} - {title} in database")
                            
                            # Update the scrobbles table if we have a connection and table name
                            if db_conn and db_cursor and table_name:
                                try:
                                    # Determine the track field name
                                    db_cursor.execute(f"PRAGMA table_info({table_name})")
                                    columns = [row[1] for row in db_cursor.fetchall()]
                                    track_field = 'track_name' if 'track_name' in columns else 'name'
                                    
                                    update_sql = f"""
                                    UPDATE {table_name} 
                                    SET {service_url_key} = ? 
                                    WHERE LOWER(artist_name) = LOWER(?) AND LOWER({track_field}) = LOWER(?) AND timestamp = ?
                                    """
                                    db_cursor.execute(update_sql, (
                                        links[service], 
                                        artist, 
                                        title, 
                                        timestamp
                                    ))
                                    db_conn.commit()
                                except Exception as e:
                                    self.log(f"Error updating link in scrobbles table: {str(e)}")
                            
                            # Once we have one service URL, we can skip to the next scrobble
                            break
            
            # If no links were found in the database, try fetching from Last.fm
            if not any(scrobble.get(f'{service}_url') for service in service_priority):
                try:
                    # Check if we have a Last.fm URL
                    lastfm_url = scrobble.get('url', scrobble.get('lastfm_url', ''))
                    if lastfm_url:
                        # Try to extract links from Last.fm page
                        for service in service_priority:
                            service_url = extract_link_from_lastfm(self, lastfm_url, service)
                            
                            if service_url:
                                # Update the scrobble and cache
                                service_url_key = f'{service}_url'
                                scrobble[service_url_key] = service_url
                                
                                if key in scrobbles_dict:
                                    scrobbles_dict[key][service_url_key] = service_url
                                    updated_count += 1
                                    
                                    # Log successful link retrieval
                                    self.log(f"Found {service} link for {artist} - {title} from Last.fm")
                                    
                                    # Update the scrobbles table if we have a connection and table name
                                    if db_conn and db_cursor and table_name:
                                        try:
                                            # Determine the track field name
                                            db_cursor.execute(f"PRAGMA table_info({table_name})")
                                            columns = [row[1] for row in db_cursor.fetchall()]
                                            track_field = 'track_name' if 'track_name' in columns else 'name'
                                            
                                            update_sql = f"""
                                            UPDATE {table_name} 
                                            SET {service_url_key} = ? 
                                            WHERE LOWER(artist_name) = LOWER(?) AND LOWER({track_field}) = LOWER(?) AND timestamp = ?
                                            """
                                            db_cursor.execute(update_sql, (
                                                service_url, 
                                                artist, 
                                                title, 
                                                timestamp
                                            ))
                                            db_conn.commit()
                                        except Exception as e:
                                            self.log(f"Error updating link in scrobbles table: {str(e)}")
                                    
                                    # Once we have one service URL, we can skip to the next service
                                    break
                except Exception as e:
                    self.log(f"Error fetching links for {artist} - {title}: {str(e)}")
            
            # If we have links and the database connection, update song_links table
            if db_conn and db_cursor and any(scrobble.get(f'{service}_url') for service in service_priority):
                try:
                    # First, find or create song record
                    db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='songs'")
                    if db_cursor.fetchone():
                        # Check if the song exists
                        db_cursor.execute("""
                        SELECT id FROM songs 
                        WHERE LOWER(artist) = LOWER(?) AND LOWER(title) = LOWER(?)
                        """, (artist, title))
                        song_result = db_cursor.fetchone()
                        
                        song_id = None
                        if song_result:
                            song_id = song_result[0]
                            self.log(f"Found song ID {song_id} for {artist} - {title}")
                        else:
                            # If the song doesn't exist, create it
                            try:
                                db_cursor.execute("""
                                INSERT INTO songs 
                                (title, album, artist, origen, reproducciones)
                                VALUES (?, ?, ?, 'scrobble', 1)
                                """, (title, album, artist))
                                song_id = db_cursor.lastrowid
                                self.log(f"Created new song ID {song_id} for {artist} - {title}")
                            except Exception as e:
                                self.log(f"Error creating song record: {e}")
                        
                        # If we have a song_id, update song_links
                        if song_id:
                            db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='song_links'")
                            if db_cursor.fetchone():
                                # Check if we have a links record for this song
                                db_cursor.execute("SELECT id FROM song_links WHERE song_id = ?", (song_id,))
                                link_result = db_cursor.fetchone()
                                
                                # Collect all service URLs from the scrobble
                                urls = {}
                                for service in service_priority:
                                    service_url_key = f'{service}_url'
                                    if service_url_key in scrobble and scrobble[service_url_key]:
                                        urls[service_url_key] = scrobble[service_url_key]
                                
                                if urls:
                                    if link_result:
                                        # Update existing links
                                        update_fields = []
                                        update_params = []
                                        
                                        for service_url_key, url in urls.items():
                                            update_fields.append(f"{service_url_key} = COALESCE(?, {service_url_key})")
                                            update_params.append(url)
                                        
                                        update_params.append(song_id)
                                        
                                        update_sql = f"""
                                        UPDATE song_links SET 
                                            {', '.join(update_fields)},
                                            links_updated = CURRENT_TIMESTAMP
                                        WHERE song_id = ?
                                        """
                                        db_cursor.execute(update_sql, update_params)
                                        db_conn.commit()
                                        self.log(f"Updated song_links for song ID {song_id}")
                                    else:
                                        # Insert new links record
                                        insert_cols = ['song_id', 'links_updated']
                                        insert_vals = ['?', 'CURRENT_TIMESTAMP']
                                        insert_params = [song_id]
                                        
                                        for service_url_key, url in urls.items():
                                            insert_cols.append(service_url_key)
                                            insert_vals.append('?')
                                            insert_params.append(url)
                                        
                                        insert_sql = f"""
                                        INSERT INTO song_links ({', '.join(insert_cols)})
                                        VALUES ({', '.join(insert_vals)})
                                        """
                                        db_cursor.execute(insert_sql, insert_params)
                                        db_conn.commit()
                                        self.log(f"Inserted song_links for song ID {song_id}")
                except Exception as e:
                    self.log(f"Error updating song_links table: {e}")
            
            # Update progress periodically
            processed_count += 1
            if processed_count % 20 == 0:
                self.log(f"Processed {processed_count}/{len(scrobbles)} scrobbles, found {updated_count} links")
                
                # Save intermediate results to cache
                try:
                    # Rebuild the scrobbles list from the dictionary
                    cache_data['scrobbles'] = list(scrobbles_dict.values())
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache_data, f, indent=2)
                except Exception as e:
                    self.log(f"Error saving intermediate link updates: {str(e)}")
        
        # Close database connection if open
        if db_conn:
            db_conn.close()
        
        # Final save to cache
        try:
            # Rebuild the scrobbles list from the dictionary
            cache_data['scrobbles'] = list(scrobbles_dict.values())
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
                
            self.log(f"Link fetching complete. Updated {updated_count} scrobbles.")
        except Exception as e:
            self.log(f"Error saving final link updates: {str(e)}")
    
    except Exception as e:
        self.log(f"Error in link fetching thread: {str(e)}")
        import traceback
        self.log(traceback.format_exc())


def force_load_scrobbles_data_from_db(self):
    """
    Carga forzada de datos de scrobbles directamente de la base de datos,
    independientemente de la sincronización.
    """
    try:
        if not hasattr(self, 'db_path') or not os.path.exists(self.db_path):
            self.log("Error: No database path configured or database file does not exist")
            return False

        # Buscar todas las tablas de scrobbles disponibles
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Primero intentar con la tabla del usuario actual
        years_dict = {}
        user_tables = []
        
        if hasattr(self, 'lastfm_username') and self.lastfm_username:
            user_tables.append(f"scrobbles_{self.lastfm_username}")
        
        # Añadir tabla de paqueradejere como fallback
        user_tables.append("scrobbles_paqueradejere")
        
        found_data = False
        for table_name in user_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                continue
                
            # Verificar que la tabla tiene timestamps
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            if 'timestamp' not in columns:
                continue
                
            try:
                # Obtener años únicos
                cursor.execute(f"""
                SELECT strftime('%Y', datetime(timestamp, 'unixepoch')) as year,
                       COUNT(*) as count
                FROM {table_name}
                WHERE timestamp > 0
                GROUP BY year
                ORDER BY year DESC
                """)
                
                years_results = cursor.fetchall()
                
                if years_results:
                    for year_row in years_results:
                        try:
                            year = int(year_row[0])
                            count = year_row[1]
                            
                            if count > 0:
                                if year not in years_dict:
                                    years_dict[year] = set()
                                
                                # Obtener meses para este año
                                cursor.execute(f"""
                                SELECT strftime('%m', datetime(timestamp, 'unixepoch')) as month,
                                       COUNT(*) as count
                                FROM {table_name}
                                WHERE timestamp > 0 
                                AND strftime('%Y', datetime(timestamp, 'unixepoch')) = ?
                                GROUP BY month
                                ORDER BY month
                                """, (str(year),))
                                
                                months_results = cursor.fetchall()
                                for month_row in months_results:
                                    if month_row[1] > 0:  # Solo añadir si hay scrobbles
                                        try:
                                            month = int(month_row[0])
                                            years_dict[year].add(month)
                                        except (ValueError, TypeError):
                                            continue
                                            
                            found_data = True
                        except (ValueError, TypeError):
                            continue
                            
                    if found_data:
                        break  # Si encontramos datos, no necesitamos buscar en más tablas
                        
            except sqlite3.Error as e:
                self.log(f"Error querying {table_name}: {e}")
                continue
        
        conn.close()
        
        if years_dict:
            # Actualizar los menús en el hilo principal
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: populate_scrobbles_time_menus(self, years_dict=years_dict))
            return True
            
        return False
        
    except Exception as e:
        self.log(f"Error loading scrobbles data: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False

def _execute_load_scrobbles_db_impl(self):
    """Execute database operations in a background thread"""
    try:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Buscar todas las tablas de scrobbles disponibles
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'scrobbles_%' OR name = 'scrobbles')")
        scrobbles_tables = [row[0] for row in cursor.fetchall()]
        
        self.log(f"Found scrobbles tables: {', '.join(scrobbles_tables)}")
        
        if not scrobbles_tables:
            self.log("No scrobbles tables found in database")
            conn.close()
            return False
        
        # Seleccionar la tabla preferida
        preferred_table = None
        
        # Primero buscar la tabla del usuario actual si está configurado
        if hasattr(self, 'lastfm_username') and self.lastfm_username:
            user_table = f"scrobbles_{self.lastfm_username}"
            if user_table in scrobbles_tables:
                preferred_table = user_table
                self.log(f"Using preferred table for current user: {preferred_table}")
        
        # Si no hay tabla para el usuario actual, intentar con paqueradejere
        if not preferred_table and "scrobbles_paqueradejere" in scrobbles_tables:
            preferred_table = "scrobbles_paqueradejere"
            self.log(f"Using fallback table: {preferred_table}")
        
        # Si no hay tabla específica, usar la primera disponible
        if not preferred_table and scrobbles_tables:
            preferred_table = scrobbles_tables[0]
            self.log(f"Using first available table: {preferred_table}")
        
        if not preferred_table:
            self.log("Could not find a suitable scrobbles table")
            conn.close()
            return False
        
        # Verificar que la tabla tenga timestamp
        cursor.execute(f"PRAGMA table_info({preferred_table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'timestamp' not in columns:
            self.log(f"Table {preferred_table} does not have timestamp column")
            conn.close()
            return False
        
        # Cargar datos de años directamente
        years_dict = {}
        
        cursor.execute(f"""
        SELECT 
            CAST(strftime('%Y', datetime(timestamp, 'unixepoch')) AS INTEGER) as year,
            COUNT(*) as count
        FROM {preferred_table}
        WHERE timestamp > 0
        GROUP BY year
        ORDER BY year DESC
        """)
        
        years_results = cursor.fetchall()
        self.log(f"Found {len(years_results)} years with data in {preferred_table}")
        
        for year_row in years_results:
            if not year_row[0]:
                continue
                
            year = year_row[0]
            count = year_row[1]
            
            if count > 0:
                years_dict[year] = set()
                
                # Obtener meses para este año
                cursor.execute(f"""
                SELECT 
                    CAST(strftime('%m', datetime(timestamp, 'unixepoch')) AS INTEGER) as month,
                    COUNT(*) as count
                FROM {preferred_table}
                WHERE timestamp > 0 
                AND strftime('%Y', datetime(timestamp, 'unixepoch')) = ?
                GROUP BY month
                ORDER BY month
                """, (str(year),))
                
                months_results = cursor.fetchall()
                
                for month_row in months_results:
                    if not month_row[0]:
                        continue
                        
                    month = month_row[0]
                    month_count = month_row[1]
                    
                    if month_count > 0:
                        years_dict[year].add(month)
        
        conn.close()
        
        # Si encontramos datos, poblar los menús en el hilo principal
        if years_dict:
            self.log(f"Loaded data for {len(years_dict)} years with {sum(len(months) for months in years_dict.values())} months total")
            
            # Store the data for access in the main thread
            self._pending_years_dict = years_dict
            
            # Schedule menu update in main thread using QTimer
            from PyQt6.QtCore import QTimer
            
            # Define a function to run in the main thread
            def update_menus_in_main_thread():
                from modules.submodules.url_playlist.lastfm_manager import populate_scrobbles_time_menus
                populate_scrobbles_time_menus(self, years_dict=self._pending_years_dict)
            
            # Schedule it to run in the main thread
            QTimer.singleShot(0, update_menus_in_main_thread)
            
            return True
        else:
            self.log("No year/month data found in database")
            return False
            
    except Exception as e:
        self.log(f"Error in _execute_load_scrobbles_db: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False


def _execute_load_scrobbles_db(self):
    """Execute database operations in a background thread"""
    try:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Buscar todas las tablas de scrobbles disponibles
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'scrobbles_%' OR name = 'scrobbles')")
        scrobbles_tables = [row[0] for row in cursor.fetchall()]
        
        self.log(f"Found scrobbles tables: {', '.join(scrobbles_tables)}")
        
        if not scrobbles_tables:
            self.log("No scrobbles tables found in database")
            conn.close()
            return False
        
        # Seleccionar la tabla preferida
        preferred_table = None
        
        # Primero buscar la tabla del usuario actual si está configurado
        if hasattr(self, 'lastfm_username') and self.lastfm_username:
            user_table = f"scrobbles_{self.lastfm_username}"
            if user_table in scrobbles_tables:
                preferred_table = user_table
                self.log(f"Using preferred table for current user: {preferred_table}")
        
        # Si no hay tabla para el usuario actual, intentar con paqueradejere
        if not preferred_table and "scrobbles_paqueradejere" in scrobbles_tables:
            preferred_table = "scrobbles_paqueradejere"
            self.log(f"Using fallback table: {preferred_table}")
        
        # Si no hay tabla específica, usar la primera disponible
        if not preferred_table and scrobbles_tables:
            preferred_table = scrobbles_tables[0]
            self.log(f"Using first available table: {preferred_table}")
        
        if not preferred_table:
            self.log("Could not find a suitable scrobbles table")
            conn.close()
            return False
        
        # Verificar que la tabla tenga timestamp
        cursor.execute(f"PRAGMA table_info({preferred_table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'timestamp' not in columns:
            self.log(f"Table {preferred_table} does not have timestamp column")
            conn.close()
            return False
        
        # Cargar datos de años directamente
        years_dict = {}
        
        cursor.execute(f"""
        SELECT 
            CAST(strftime('%Y', datetime(timestamp, 'unixepoch')) AS INTEGER) as year,
            COUNT(*) as count
        FROM {preferred_table}
        WHERE timestamp > 0
        GROUP BY year
        ORDER BY year DESC
        """)
        
        years_results = cursor.fetchall()
        self.log(f"Found {len(years_results)} years with data in {preferred_table}")
        
        for year_row in years_results:
            if not year_row[0]:
                continue
                
            year = year_row[0]
            count = year_row[1]
            
            if count > 0:
                years_dict[year] = set()
                
                # Obtener meses para este año
                cursor.execute(f"""
                SELECT 
                    CAST(strftime('%m', datetime(timestamp, 'unixepoch')) AS INTEGER) as month,
                    COUNT(*) as count
                FROM {preferred_table}
                WHERE timestamp > 0 
                AND strftime('%Y', datetime(timestamp, 'unixepoch')) = ?
                GROUP BY month
                ORDER BY month
                """, (str(year),))
                
                months_results = cursor.fetchall()
                
                for month_row in months_results:
                    if not month_row[0]:
                        continue
                        
                    month = month_row[0]
                    month_count = month_row[1]
                    
                    if month_count > 0:
                        years_dict[year].add(month)
        
        conn.close()
        
        # Si encontramos datos, poblar los menús en el hilo principal
        if years_dict:
            self.log(f"Loaded data for {len(years_dict)} years with {sum(len(months) for months in years_dict.values())} months total")
            
            # Store the data for access in the main thread
            self._pending_years_dict = years_dict
            
            # Schedule menu update in main thread using QTimer
            from PyQt6.QtCore import QTimer
            
            # Define a function to run in the main thread
            def update_menus_in_main_thread():
                
                populate_scrobbles_time_menus(self, years_dict=self._pending_years_dict)
            
            # Schedule it to run in the main thread
            QTimer.singleShot(0, update_menus_in_main_thread)
            
            return True
        else:
            self.log("No year/month data found in database")
            return False
            
    except Exception as e:
        self.log(f"Error in _execute_load_scrobbles_db: {str(e)}")
        import traceback
        self.log(traceback.format_exc())
        return False




def load_years_months_from_db(self):
    """
    Cargar directamente años y meses desde la base de datos y crear menús
    Supports execution from any thread
    """
    try:
        # Verificar que tenemos la conexión a la base de datos
        if not hasattr(self, 'db_path') or not self.db_path:
            self.log("Error: No hay configuración de base de datos")
            return False
            
        if not os.path.exists(self.db_path):
            self.log(f"Error: Archivo de base de datos no encontrado: {self.db_path}")
            return False
            
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Encontrar la tabla de scrobbles más adecuada
        scrobbles_table = None
        
        # Primero buscar tabla para el usuario actual
        if hasattr(self, 'lastfm_username') and self.lastfm_username:
            user_table = f"scrobbles_{self.lastfm_username}"
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{user_table}'")
            if cursor.fetchone():
                scrobbles_table = user_table
        
        # Si no hay tabla para el usuario actual, buscar tabla paqueradejere
        if not scrobbles_table:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scrobbles_paqueradejere'")
            if cursor.fetchone():
                scrobbles_table = "scrobbles_paqueradejere"
        
        # Si no se encontraron tablas específicas, buscar cualquier tabla de scrobbles
        if not scrobbles_table:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'scrobbles_%'")
            result = cursor.fetchone()
            if result:
                scrobbles_table = result[0]
        
        if not scrobbles_table:
            self.log("No se encontró tabla de scrobbles")
            conn.close()
            return False
            
        self.log(f"Usando tabla de scrobbles: {scrobbles_table}")
        
        # Obtener años en orden descendente
        cursor.execute(f"""
        SELECT DISTINCT strftime('%Y', datetime(timestamp, 'unixepoch')) as year 
        FROM {scrobbles_table} 
        WHERE timestamp > 0
        ORDER BY year DESC
        """)
        
        years_result = cursor.fetchall()
        years = [row[0] for row in years_result if row[0]]
        
        self.log(f"Años encontrados: {years}")
        
        if not years:
            self.log("No se encontraron años en la tabla")
            conn.close()
            return False
        
        # Ahora que tenemos los años, obtener los meses para cada año
        years_months = {}
        
        for year in years:
            cursor.execute(f"""
            SELECT DISTINCT strftime('%m', datetime(timestamp, 'unixepoch')) as month 
            FROM {scrobbles_table} 
            WHERE timestamp > 0 
              AND strftime('%Y', datetime(timestamp, 'unixepoch')) = ?
            ORDER BY month
            """, (year,))
            
            months_result = cursor.fetchall()
            months = [int(row[0]) for row in months_result if row[0]]
            
            if months:
                years_months[int(year)] = months
        
        conn.close()
        
        self.log(f"Datos cargados: {len(years_months)} años con meses")
        
        # Define a helper function to update the menus
        def update_lastfm_menus_with_data():
            """Helper function to update LastFM menus in the main thread"""
            try:
                # Create los menús
                if hasattr(self, 'months_menu') and hasattr(self, 'years_menu'):
                    # Limpiar menús existentes
                    self.months_menu.clear()
                    self.years_menu.clear()
                    
                    # Crear menú de años
                    for year in sorted(years_months.keys(), reverse=True):
                        year_action = self.years_menu.addAction(str(year))
                        from modules.submodules.url_playlist.lastfm_manager import load_lastfm_scrobbles_year
                        year_action.triggered.connect(lambda checked=False, y=year: load_lastfm_scrobbles_year(self, y))
                    
                    # Crear menú de meses
                    for year in sorted(years_months.keys(), reverse=True):
                        year_submenu = self.months_menu.addMenu(str(year))
                        
                        for month in sorted(years_months[year]):
                            import datetime
                            date_obj = datetime.datetime(2000, month, 1)
                            month_name = date_obj.strftime("%B")
                            
                            month_action = year_submenu.addAction(month_name)
                            from modules.submodules.url_playlist.lastfm_manager import load_lastfm_scrobbles_month
                            month_action.triggered.connect(lambda checked=False, y=year, m=month: load_lastfm_scrobbles_month(self, y, m))
                
                # Hacer lo mismo con el menu unificado si existe
                if hasattr(self, 'unified_months_menu') and hasattr(self, 'unified_years_menu'):
                    # Limpiar menús existentes
                    self.unified_months_menu.clear()
                    self.unified_years_menu.clear()
                    
                    # Crear menú de años
                    for year in sorted(years_months.keys(), reverse=True):
                        year_action = self.unified_years_menu.addAction(str(year))
                        from modules.submodules.url_playlist.lastfm_manager import load_lastfm_scrobbles_year
                        year_action.triggered.connect(lambda checked=False, y=year: load_lastfm_scrobbles_year(self, y))
                    
                    # Crear menú de meses
                    for year in sorted(years_months.keys(), reverse=True):
                        year_submenu = self.unified_months_menu.addMenu(str(year))
                        
                        for month in sorted(years_months[year]):
                            import datetime
                            date_obj = datetime.datetime(2000, month, 1)
                            month_name = date_obj.strftime("%B")
                            
                            month_action = year_submenu.addAction(month_name)
                            from modules.submodules.url_playlist.lastfm_manager import load_lastfm_scrobbles_month
                            month_action.triggered.connect(lambda checked=False, y=year, m=month: load_lastfm_scrobbles_month(self, y, m))
                
                self.log("Menús de años y meses creados correctamente")
            except Exception as e:
                self.log(f"Error updating LastFM menus: {e}")
                import traceback
                self.log(traceback.format_exc())
        
        # Check if we're in the main thread
        from PyQt6.QtCore import QThread, QTimer, QCoreApplication
        if QThread.currentThread() == QCoreApplication.instance().thread():
            # We're in the main thread, update menus directly
            update_lastfm_menus_with_data()
            return True
        else:
            # We're in a background thread, use QTimer to run in main thread
            # Store the data as an instance variable for access in the main thread
            self._pending_years_months = years_months
            
            # SOLUCIÓN: Usar movido a contexto de método para evitar captura de 'self'
            QMetaObject.invokeMethod(QCoreApplication.instance(), 
                                     lambda: update_lastfm_menus_with_data(),
                                     Qt.ConnectionType.QueuedConnection)
            return True
        
    except Exception as e:
        self.log(f"Error cargando años y meses: {e}")
        import traceback
        self.log(traceback.format_exc())
        return False

def _update_lastfm_menus(self, years_months):
    """Helper function to update LastFM menus in the main thread"""
    try:
        # Create los menús
        if hasattr(self, 'months_menu') and hasattr(self, 'years_menu'):
            # Limpiar menús existentes
            self.months_menu.clear()
            self.years_menu.clear()
            
            # Crear menú de años
            for year in sorted(years_months.keys(), reverse=True):
                year_action = self.years_menu.addAction(str(year))
                from modules.submodules.url_playlist.lastfm_manager import load_lastfm_scrobbles_year
                year_action.triggered.connect(lambda checked=False, y=year: load_lastfm_scrobbles_year(self, y))
            
            # Crear menú de meses
            for year in sorted(years_months.keys(), reverse=True):
                year_submenu = self.months_menu.addMenu(str(year))
                
                for month in sorted(years_months[year]):
                    import datetime
                    date_obj = datetime.datetime(2000, month, 1)
                    month_name = date_obj.strftime("%B")
                    
                    month_action = year_submenu.addAction(month_name)
                    from modules.submodules.url_playlist.lastfm_manager import load_lastfm_scrobbles_month
                    month_action.triggered.connect(lambda checked=False, y=year, m=month: load_lastfm_scrobbles_month(self, y, m))
        
        # Hacer lo mismo con el menu unificado si existe
        if hasattr(self, 'unified_months_menu') and hasattr(self, 'unified_years_menu'):
            # Limpiar menús existentes
            self.unified_months_menu.clear()
            self.unified_years_menu.clear()
            
            # Crear menú de años
            for year in sorted(years_months.keys(), reverse=True):
                year_action = self.unified_years_menu.addAction(str(year))
                from modules.submodules.url_playlist.lastfm_manager import load_lastfm_scrobbles_year
                year_action.triggered.connect(lambda checked=False, y=year: load_lastfm_scrobbles_year(self, y))
            
            # Crear menú de meses
            for year in sorted(years_months.keys(), reverse=True):
                year_submenu = self.unified_months_menu.addMenu(str(year))
                
                for month in sorted(years_months[year]):
                    import datetime
                    date_obj = datetime.datetime(2000, month, 1)
                    month_name = date_obj.strftime("%B")
                    
                    month_action = year_submenu.addAction(month_name)
                    from modules.submodules.url_playlist.lastfm_manager import load_lastfm_scrobbles_month
                    month_action.triggered.connect(lambda checked=False, y=year, m=month: load_lastfm_scrobbles_month(self, y, m))
        
        self.log("Menús de años y meses creados correctamente")
    except Exception as e:
        self.log(f"Error updating LastFM menus: {e}")
        import traceback
        self.log(traceback.format_exc())