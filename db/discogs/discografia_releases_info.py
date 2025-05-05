import os
import sys
import sqlite3
import requests
import json
import time
from datetime import datetime
from base_module import PROJECT_ROOT

class DiscogsUpdater:
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.db_path = self.config.get('db_path', os.path.join(PROJECT_ROOT, 'music.db'))
        self.discogs_token = self.config.get('discogs_token', '')
        self.delay_between_requests = self.config.get('delay_between_requests', 1.5)
        self.force_update = self.config.get('force_update', False)
        self.conn = None
        self.cursor = None
        
    def connect_db(self):
        """Establece conexión con la base de datos"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
    def close_db(self):
        """Cierra la conexión con la base de datos"""
        if self.conn:
            self.conn.close()
            
    def get_releases_to_update(self):
        """Obtiene los releases que necesitan ser actualizados"""
        query = """
        SELECT id, main_release, resource_url 
        FROM discogs_discography 
        WHERE (main_release IS NOT NULL OR resource_url IS NOT NULL)
        """
        
        if self.force_update == False:
            # Si no es actualización forzada, excluir registros que ya tienen uri_release
            query += " AND (uri_release IS NULL OR uri_release = '')"
        
        self.cursor.execute(query)
        return self.cursor.fetchall()
        
    def get_rate_limit_info(self, response_headers):
        """Extrae información de límites de tasa de las cabeceras de respuesta"""
        try:
            # Extraer información de cabeceras
            remaining = int(response_headers.get('X-Discogs-Ratelimit-Remaining', 0))
            total = int(response_headers.get('X-Discogs-Ratelimit', 60))
            reset_time = float(response_headers.get('X-Discogs-Ratelimit-Used', 0))
            
            return {
                'remaining': remaining,
                'total': total,
                'reset_time': reset_time
            }
        except (ValueError, TypeError) as e:
            print(f"Error al procesar cabeceras de rate limit: {e}")
            # Valores por defecto conservadores
            return {'remaining': 5, 'total': 60, 'reset_time': 0}

    def get_release_data(self, release_id=None, resource_url=None):
        """Obtiene los datos de un release desde la API de Discogs"""
        headers = {
            'User-Agent': 'MusicLibraryManager/1.0 +http://example.com',
            'Authorization': f'Discogs token={self.discogs_token}'
        }
        
        if resource_url:
            url = resource_url
        elif release_id:
            url = f"https://api.discogs.com/releases/{release_id}"
        else:
            return None
            
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Obtener información de rate limit
            rate_info = self.get_rate_limit_info(response.headers)
            
            # Guardar información para uso posterior
            self.last_rate_info = rate_info
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener datos de Discogs: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Código: {e.response.status_code}")
                
                # Si es error 429 (Too Many Requests), extraer tiempo de espera
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    print(f"Rate limit superado. Esperar {retry_after} segundos.")
                    time.sleep(retry_after + 5)  # Añadir 5 segundos por seguridad
                    # Intentar de nuevo después de esperar
                    return self.get_release_data(release_id, resource_url)
                    
                print(f"Respuesta: {e.response.text[:200]}...")
            return None

    def adaptive_delay(self, rate_info=None):
        """Calcula un delay adaptativo basado en los límites de tasa"""
        if not rate_info and hasattr(self, 'last_rate_info'):
            rate_info = self.last_rate_info
        
        if rate_info and 'remaining' in rate_info and 'total' in rate_info:
            # Si quedan pocas peticiones, aumentar el delay
            if rate_info['remaining'] < 10:
                delay = 5.0  # Delay largo cuando casi no quedan peticiones
            elif rate_info['remaining'] < 20:
                delay = 3.0  # Delay medio
            else:
                delay = 1.5  # Delay normal
                
            print(f"Rate limit: {rate_info['remaining']}/{rate_info['total']} peticiones restantes")
            return delay
        
        # Valor por defecto conservador
        return self.delay_between_requests

    def process_releases(self):
        """Procesa todos los releases pendientes de actualización"""
        releases = self.get_releases_to_update()
        total = len(releases)
        
        if total == 0:
            print("No hay releases para actualizar")
            return
            
        print(f"Se van a procesar {total} releases")
        
        # Para almacenar el último estado de límite de tasa
        self.last_rate_info = None
        success_count = 0
        error_count = 0
        
        for i, release in enumerate(releases):
            row_id = release['id']
            release_id = release['main_release']
            resource_url = release['resource_url']
            
            print(f"Procesando {i+1}/{total}: ID {row_id}, Release {release_id or 'desde URL'}")
            
            # Implementar reintento con backoff exponencial
            max_retries = 3
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                if retry_count > 0:
                    retry_delay = 5 * (2 ** (retry_count - 1))  # 5, 10, 20 segundos
                    print(f"  Reintento {retry_count}/{max_retries} después de {retry_delay} segundos...")
                    time.sleep(retry_delay)
                
                # Obtener datos de la API
                release_data = self.get_release_data(release_id, resource_url)
                
                if release_data:
                    success = self.update_release_data(row_id, release_data)
                    if success:
                        print(f"  ✓ Actualizado correctamente")
                        success_count += 1
                        break  # Salir del bucle de reintento
                    else:
                        print(f"  ✗ Error al actualizar la base de datos")
                        retry_count += 1
                else:
                    print(f"  ✗ No se pudieron obtener datos de la API")
                    retry_count += 1
            
            if not success:
                error_count += 1
                if error_count > 5:
                    print("Demasiados errores consecutivos. Pausando ejecución durante 2 minutos...")
                    time.sleep(120)
                    error_count = 0
            
            # Calcular delay adaptativo basado en límites de tasa
            delay = self.adaptive_delay()
            
            # Evitar sobrecargar la API
            if i < total - 1:  # No esperar después del último
                print(f"  Esperando {delay:.1f} segundos antes de la siguiente petición...")
                time.sleep(delay)
        
        print(f"Proceso completado. {success_count}/{total} actualizados correctamente.")
            
    def update_release_data(self, row_id, release_data):
        """Actualiza los datos del release en la base de datos"""
        if not release_data:
            return False
            
        # Prepara los datos para actualizar
        update_data = {
            'status': release_data.get('status'),
            'year': release_data.get('year'),
            'uri_release': release_data.get('uri'),
            'labels': json.dumps(release_data.get('labels', [])),
            'companies': json.dumps(release_data.get('companies', [])),
            'formats': json.dumps(release_data.get('formats', [])),
            'rating_count': release_data.get('rating', {}).get('count'),
            'rate_average': release_data.get('rating', {}).get('average'),
            'num_for_sale': release_data.get('num_for_sale'),
            'lowest_price': release_data.get('lowest_price'),
            'release_title': release_data.get('title'),
            'released': release_data.get('released'),
            'notes': release_data.get('notes'),
            'genres': json.dumps(release_data.get('genres', [])),
            'styles': json.dumps(release_data.get('styles', [])),
            'tracklist': json.dumps(release_data.get('tracklist', [])),
            'extraartists': json.dumps(release_data.get('extraartists', [])),
            'thumb': release_data.get('thumb'),
            'estimated_weight': release_data.get('estimated_weight'),
            'blocked_from_sale': release_data.get('blocked_from_sale'),
            'is_offensive': release_data.get('is_offensive'),
            'images': json.dumps(release_data.get('images', [])),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Construir la consulta SQL dinámica
        set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
        values = list(update_data.values())
        values.append(row_id)  # Para el WHERE id = ?
        
        query = f"UPDATE discogs_discography SET {set_clause} WHERE id = ?"
        
        try:
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error al actualizar la base de datos: {e}")
            self.conn.rollback()
            return False
            
    def add_columns_if_missing(self):
        """Añade las columnas necesarias si no existen en la tabla"""
        columns_to_add = [
            ('uri_release', 'TEXT'),
            ('labels', 'JSON'),
            ('companies', 'JSON'),
            ('formats', 'JSON'),
            ('rating_count', 'INTEGER'),
            ('rate_average', 'REAL'),
            ('num_for_sale', 'INTEGER'),
            ('lowest_price', 'REAL'),
            ('release_title', 'TEXT'),
            ('released', 'TEXT'),
            ('notes', 'TEXT'),
            ('genres', 'JSON'),
            ('styles', 'JSON'),
            ('tracklist', 'JSON'),
            ('extraartists', 'JSON'),
            ('estimated_weight', 'REAL'),
            ('blocked_from_sale', 'INTEGER'),
            ('is_offensive', 'INTEGER'),
            ('images', 'JSON')
        ]
        
        # Obtener columnas existentes
        self.cursor.execute("PRAGMA table_info(discogs_discography)")
        existing_columns = [row[1] for row in self.cursor.fetchall()]
        
        # Añadir columnas que faltan
        for column_name, column_type in columns_to_add:
            if column_name not in existing_columns:
                try:
                    self.cursor.execute(f"ALTER TABLE discogs_discography ADD COLUMN {column_name} {column_type}")
                    print(f"Columna {column_name} añadida con éxito")
                except sqlite3.Error as e:
                    print(f"Error al añadir columna {column_name}: {e}")
        
        self.conn.commit()
      
    def run(self):
        """Ejecuta el proceso completo"""
        try:
            print("Iniciando actualización de datos de Discogs...")
            self.connect_db()
            self.add_columns_if_missing()
            self.process_releases()
            print("Proceso completado")
        except Exception as e:
            print(f"Error durante la ejecución: {e}")
        finally:
            self.close_db()
            
def main(config=None):
    updater = DiscogsUpdater(config)
    updater.run()
    
if __name__ == "__main__":
    main()