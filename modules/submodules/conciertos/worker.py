from PyQt6.QtCore import QThread, pyqtSignal
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import requests

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