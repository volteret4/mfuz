from PyQt6.QtCore import QThread, pyqtSignal
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import requests
import sqlite3

class ConcertSearchWorker(QThread):
    """Worker para buscar conciertos en segundo plano con controles de progreso"""
    
    log_message = pyqtSignal(str)
    concerts_found = pyqtSignal(list)
    search_finished = pyqtSignal()
    progress_update = pyqtSignal(int, int)  # actual, total
    
    def __init__(self, services, artists, country_code, db_path):
        """
        Inicializar worker
        
        Args:
            services (list): Lista de tuplas (nombre_servicio, objeto_servicio)
            artists (list): Lista de nombres de artistas
            country_code (str): Código de país
        """
        super().__init__()
        self.services = services
        self.artists = artists
        self.country_code = country_code
        self.db_path = db_path
        self.concerts = []
        self._running = True
        
        # Debug: verificar que services no está vacío
        print(f"Worker: Services received: {services}")
        print(f"Worker: Artists received: {artists}")
        print(f"Worker: Country code: {country_code}")
    
    def get_artist_image(self, artist_name, service_name=None, service=None):
        """
        Obtener imagen del artista según la jerarquía especificada:
        1. base de datos, tabla artists, columna img
        2. spotify api, y la guardaría en dicha columna
        3. base de datos, tabla albums, columna 'album_art_path'
        4. spotify api, obteniendo la caratula del album
        
        Args:
            artist_name (str): Nombre del artista
            service_name (str, optional): Nombre del servicio que se está utilizando
            service (object, optional): Objeto del servicio para consultas directas
            
        Returns:
            str: URL o ruta de la imagen
        """
        try:
            # Conectar a la base de datos
            db_conn = sqlite3.connect(self.db_path)
            cursor = db_conn.cursor()
            
            # Verificar si la columna img existe en la tabla artists
            cursor.execute("PRAGMA table_info(artists)")
            columns = cursor.fetchall()
            has_img_column = any(col[1] == 'img' for col in columns)
            
            # Si no existe, crearla
            if not has_img_column:
                self.log_message.emit("Creando columna 'img' en tabla 'artists'...")
                cursor.execute("ALTER TABLE artists ADD COLUMN img TEXT")
                db_conn.commit()
            
            # Paso 1: Buscar en la BD (tabla artists, columna img)
            cursor.execute("SELECT img FROM artists WHERE name = ?", (artist_name,))
            result = cursor.fetchone()
            
            if result and result[0]:
                self.log_message.emit(f"Imagen para {artist_name} encontrada en base de datos")
                db_conn.close()
                return result[0]
            
            # Paso 2: Buscar en Spotify API y actualizar BD
            spotify_service = None
            for srv_name, srv_obj in self.services:
                if srv_name == "spotify":
                    spotify_service = srv_obj
                    break
            
            if spotify_service:
                self.log_message.emit(f"Buscando imagen de {artist_name} en Spotify...")
                artist_data = spotify_service.search_artist(artist_name)
                
                if artist_data and 'images' in artist_data and artist_data['images']:
                    # Obtener la primera imagen de tamaño mediano o la primera disponible
                    img_url = None
                    for img in artist_data['images']:
                        if img.get('width', 0) > 200 and img.get('width', 0) < 500:
                            img_url = img.get('url')
                            break
                    
                    # Si no hay imagen de tamaño mediano, usar la primera
                    if not img_url and artist_data['images']:
                        img_url = artist_data['images'][0].get('url')
                    
                    if img_url:
                        # Actualizar BD
                        cursor.execute("UPDATE artists SET img = ? WHERE name = ?", (img_url, artist_name))
                        db_conn.commit()
                        self.log_message.emit(f"Imagen de {artist_name} actualizada en BD desde Spotify")
                        db_conn.close()
                        return img_url
            
            # Paso 3: Buscar en tabla albums
            cursor.execute("""
                SELECT album_art_path FROM albums 
                WHERE artist_id IN (SELECT id FROM artists WHERE name = ?)
                AND album_art_path IS NOT NULL
                LIMIT 1
            """, (artist_name,))
            result = cursor.fetchone()
            
            if result and result[0]:
                self.log_message.emit(f"Imagen para {artist_name} encontrada en álbumes")
                db_conn.close()
                return result[0]
            
            # Paso 4: Obtener carátula de álbum desde Spotify
            if spotify_service:
                self.log_message.emit(f"Buscando carátula de álbum para {artist_name} en Spotify...")
                
                # Obtener ID del artista en Spotify si está disponible
                artist_data = spotify_service.search_artist(artist_name)
                if artist_data and 'id' in artist_data:
                    spotify_id = artist_data['id']
                    
                    # Intentar acceder a los álbumes (Esto puede requerir ajustes en la clase SpotifyService)
                    # Esta parte depende de la implementación del método get_artist_albums en SpotifyService
                    try:
                        # Si el método existe y está disponible
                        albums = spotify_service.get_artist_albums(spotify_id, limit=1)
                        if albums and 'items' in albums and albums['items']:
                            album = albums['items'][0]
                            if 'images' in album and album['images']:
                                img_url = album['images'][0].get('url')
                                if img_url:
                                    # Actualizar BD si es posible
                                    cursor.execute("""
                                        UPDATE albums SET album_art_path = ?
                                        WHERE id IN (
                                            SELECT MIN(id) FROM albums
                                            WHERE artist_id IN (SELECT id FROM artists WHERE name = ?)
                                        )
                                    """, (img_url, artist_name))
                                    db_conn.commit()
                                    db_conn.close()
                                    return img_url
                    except AttributeError:
                        self.log_message.emit("Método get_artist_albums no disponible en SpotifyService")
                    except Exception as e:
                        self.log_message.emit(f"Error obteniendo álbumes: {str(e)}")
            
            db_conn.close()
            
            # Si llegamos aquí, no se encontró imagen
            return ""
            
        except Exception as e:
            self.log_message.emit(f"Error buscando imagen para {artist_name}: {str(e)}")
            return ""
    
    def run(self):
        """Realizar búsqueda en segundo plano"""
        total_artists = len(self.artists)
        total_services = len(self.services)
        
        # Si no hay servicios, finalizar
        if not self.services:
            self.log_message.emit("No hay servicios de API disponibles")
            self.search_finished.emit()
            return
            
        # Si no hay artistas, finalizar
        if not self.artists:
            self.log_message.emit("No hay artistas para buscar")
            self.search_finished.emit()
            return
        
        # Variables para seguimiento de progreso
        current_progress = 0
        total_operations = total_artists * total_services
        
        # Lista para acumular todos los conciertos
        all_concerts = []
        
        for i, artist in enumerate(self.artists):
            # Verificar si se ha solicitado detener
            if not self._running:
                self.log_message.emit("Búsqueda cancelada")
                break
                
            self.log_message.emit(f"Buscando conciertos para {artist} ({i+1}/{total_artists})")
            self.progress_update.emit(i+1, total_artists)
            
            # Resultados para este artista
            artist_concerts = []
            
            # Buscar en cada servicio
            for service_name, service in self.services:
                # Verificar si se ha solicitado detener
                if not self._running:
                    break
                    
                try:
                    # Añadir pequeña pausa para no saturar la API
                    time.sleep(0.2)
                    
                    # Buscar conciertos según el servicio
                    self.log_message.emit(f"Consultando {service_name} para {artist}...")
                    
                    # Llamar al método adecuado según el tipo de servicio
                    if service_name == "spotify":
                        results, message = service.get_artist_concerts_from_db_or_search(artist, self.db_path)
                    else:
                        results, message = service.search_concerts(artist, self.country_code)
                                        
                    # Activar logging detallado para Setlist.fm
                    if service_name == "setlistfm":
                        self.log_message.emit(f"=== DEBUGGING SETLIST.FM FOR {artist} ===")
                        self.log_message.emit(f"Results type: {type(results)}")
                        self.log_message.emit(f"Results count: {len(results) if isinstance(results, list) else 'N/A'}")
                        self.log_message.emit(f"Message: {message}")
                        if results and isinstance(results, list):
                            self.log_message.emit(f"First result keys: {list(results[0].keys()) if results else 'No results'}")

                    # Validar resultados
                    if not isinstance(results, list):
                        self.log_message.emit(f"Error: Resultados no válidos de {service_name} para {artist}")
                        results = []
                    
                    # Emitir mensaje de log
                    self.log_message.emit(message)
                    
                    # Buscar imagen del artista si no hay imagen definida en los resultados
                    artist_image = ""
                    
                    # Añadir la fuente si no está presente y asegurar campos necesarios
                    for concert in results:
                        if 'source' not in concert:
                            concert['source'] = service_name.capitalize()
                        
                        # Asegurar campos necesarios para identificar duplicados
                        if 'artist' not in concert or not concert.get('artist'):
                            concert['artist'] = artist
                        if 'date' not in concert or not concert.get('date'):
                            concert['date'] = '9999-99-99'  # Fecha por defecto
                        if 'venue' not in concert or not concert.get('venue'):
                            concert['venue'] = ''
                        if 'name' not in concert or not concert.get('name'):
                            concert['name'] = 'Evento sin nombre'
                        
                        # Asegurar que url e id existen
                        if 'url' not in concert:
                            concert['url'] = ''
                        if 'id' not in concert:
                            concert['id'] = ''
                            
                        # Verificar si el concierto ya tiene imagen, si no, buscarla
                        if ('image' not in concert or not concert.get('image')) and not artist_image:
                            artist_image = self.get_artist_image(artist, service_name, service)
                            
                        # Asignar imagen si se encontró y el concierto no tiene
                        if ('image' not in concert or not concert.get('image')) and artist_image:
                            concert['image'] = artist_image
                    
                    # Acumular resultados para este artista
                    artist_concerts.extend(results)
                    
                    # Informar sobre resultados de este servicio
                    self.log_message.emit(f"  - {service_name}: {len(results)} conciertos encontrados")
                    
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    self.log_message.emit(f"Error en {service_name} para {artist}: {str(e)}\n{tb}")
                
                # Actualizar progreso
                current_progress += 1
                self.progress_update.emit(current_progress, total_operations)
            
            # Añadir todos los conciertos de este artista a la lista global
            all_concerts.extend(artist_concerts)
        
        if self._running:
            # Ordenar conciertos por fecha
            try:
                all_concerts.sort(key=lambda x: x.get('date', '9999-99-99'))
            except Exception as e:
                self.log_message.emit(f"Error ordenando conciertos: {str(e)}")
            
            # Emitir resultados
            self.concerts_found.emit(all_concerts)
            
            self.log_message.emit(f"Búsqueda completada: {len(all_concerts)} conciertos encontrados en total")
        
        self.search_finished.emit()
    
    def stop(self):
        """Detener la búsqueda"""
        self._running = False