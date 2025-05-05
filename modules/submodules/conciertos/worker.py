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
    
    def __init__(self, services, artists, country_code):
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
        self.concerts = []
        self._running = True
    
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
                        results, message = service.get_artist_concerts(artist, self.country_code)
                    else:  # Ticketmaster y otros servicios
                        results, message = service.search_concerts(artist, self.country_code)
                    
                    # Activar logging detallado para Setlist.fm
                    if service_name == "setlistfm":
                        self.log_message.emit(f"=== DEBUGGING SETLIST.FM FOR {artist} ===")

                    # Validar resultados
                    if not isinstance(results, list):
                        self.log_message.emit(f"Error: Resultados no válidos de {service_name} para {artist}")
                        results = []
                    
                    # Emitir mensaje de log
                    self.log_message.emit(message)
                    
                    # Añadir la fuente si no está presente
                    for concert in results:
                        if 'source' not in concert:
                            concert['source'] = service_name.capitalize()
                    
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
            for concert in artist_concerts:
                # Verificar estructura de datos mínima
                if not isinstance(concert, dict):
                    continue
                    
                # Asegurar que tenga los campos mínimos
                if not concert.get('name') or not concert.get('artist'):
                    concert['artist'] = artist
                    if not concert.get('name'):
                        concert['name'] = 'Evento sin nombre'
                
                # Comprobar si ya existe un concierto similar
                duplicate = False
                for existing_concert in all_concerts:
                    # Considerar duplicado si coincide artista, fecha y lugar
                    if (existing_concert.get('artist') == concert.get('artist') and
                        existing_concert.get('date') == concert.get('date') and
                        existing_concert.get('venue') == concert.get('venue')):
                        duplicate = True
                        break
                
                # Si no es duplicado, añadir
                if not duplicate:
                    all_concerts.append(concert)
        
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