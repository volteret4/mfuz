"""
Módulo de diagnóstico y soluciones para los problemas de visualización
en Music Fuzzy Module.

Cómo usar:
1. Guarda este archivo como music_fuzzy_diagnostics.py en la carpeta de módulos
2. Importa y aplica las soluciones como se muestra en el código de ejemplo
"""

import traceback
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

class MusicFuzzyDiagnostic:
    """
    Clase de diagnóstico para Music Fuzzy Module.
    Proporciona herramientas para diagnosticar y corregir problemas.
    """
    
    def __init__(self, music_browser=None):
        """Inicializar con una instancia opcional de MusicBrowser."""
        self.music_browser = music_browser
        self.debug_mode = True
    
    def patch_modules(self):
        """
        Aplica los parches para corregir los problemas de visualización.
        
        Returns:
            bool: True si se aplicaron todos los parches con éxito
        """
        success = True
        
        try:
            print("[DIAGNOSTIC] Aplicando parches a módulos...")
            
            # 1. Parche a EntityView.extract_links
            self._patch_extract_links()
            
            # 2. Parche a LinkButtonsManager
            self._patch_link_buttons_manager()
            
            # 3. Parche a la visualización de Wikipedia y letras
            self._patch_content_display()
            
            # 4. Parche para mostrar mejores mensajes de debug
            self._enable_debug_messages()
            
            print("[DIAGNOSTIC] Parches aplicados con éxito")
            
        except Exception as e:
            print(f"[DIAGNOSTIC] Error al aplicar parches: {e}")
            traceback.print_exc()
            success = False
            
        return success
    
    def check_database_connection(self, db_path=None):
        """
        Verifica la conexión a la base de datos.
        
        Args:
            db_path: Ruta a la base de datos (si es None, usa la del MusicBrowser)
            
        Returns:
            dict: Resultados de la verificación
        """
        if not db_path and self.music_browser:
            db_path = getattr(self.music_browser, 'db_path', None)
            
        if not db_path:
            return {"success": False, "error": "No se proporcionó ruta a la base de datos"}
            
        try:
            import sqlite3
            
            if not os.path.exists(db_path):
                return {"success": False, "error": f"Archivo de base de datos no encontrado: {db_path}"}
                
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar tablas principales
            tables_check = {}
            for table in ["artists", "albums", "songs", "lyrics"]:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                tables_check[table] = bool(cursor.fetchone())
                
            # Verificar si hay datos
            data_check = {}
            if tables_check["artists"]:
                cursor.execute("SELECT COUNT(*) FROM artists")
                data_check["artists_count"] = cursor.fetchone()[0]
                
            if tables_check["albums"]:
                cursor.execute("SELECT COUNT(*) FROM albums")
                data_check["albums_count"] = cursor.fetchone()[0]
                
            if tables_check["songs"]:
                cursor.execute("SELECT COUNT(*) FROM songs")
                data_check["songs_count"] = cursor.fetchone()[0]
                
            if tables_check["lyrics"]:
                cursor.execute("SELECT COUNT(*) FROM lyrics")
                data_check["lyrics_count"] = cursor.fetchone()[0]
                
            # Verificar si hay contenido de Wikipedia
            wiki_check = {}
            if tables_check["artists"]:
                cursor.execute("SELECT COUNT(*) FROM artists WHERE wikipedia_content IS NOT NULL AND wikipedia_content != ''")
                wiki_check["artists_with_wiki"] = cursor.fetchone()[0]
                
            if tables_check["albums"]:
                cursor.execute("SELECT COUNT(*) FROM albums WHERE wikipedia_content IS NOT NULL AND wikipedia_content != ''")
                wiki_check["albums_with_wiki"] = cursor.fetchone()[0]
                
            # Verificar si hay enlaces
            links_check = {}
            if tables_check["artists"]:
                cursor.execute("SELECT COUNT(*) FROM artists WHERE spotify_url IS NOT NULL AND spotify_url != ''")
                links_check["artists_with_spotify"] = cursor.fetchone()[0]
                
            conn.close()
            
            return {
                "success": True,
                "tables": tables_check,
                "data": data_check,
                "wiki": wiki_check,
                "links": links_check
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_example_usage():
        """
        Devuelve un ejemplo de uso del módulo de diagnóstico.
        
        Returns:
            str: Código de ejemplo
        """
        return """
    # Ejemplo de uso del módulo de diagnóstico

    # 1. Importar el módulo
    from modules.submodules.fuzzy.music_fuzzy_diagnostics import MusicFuzzyDiagnostic

    # 2. Crear una instancia con la referencia a MusicBrowser
    diagnostic = MusicFuzzyDiagnostic(self)  # 'self' es la instancia de MusicBrowser

    # 3. Aplicar los parches para corregir problemas
    diagnostic.patch_modules()

    # 4. Verificar la conexión a la base de datos
    db_status = diagnostic.check_database_connection()
    print(f"Estado de la base de datos: {db_status}")

    # 5. Verificar los componentes de UI
    ui_status = diagnostic.check_ui_components()
    print(f"Estado de los componentes UI: {ui_status}")

    # 6. Usar el nuevo método de debug para el elemento seleccionado
    self.debug_current_item()  # Muestra información detallada del elemento actual

    # Nota: También puedes añadir este código a un botón o acción para diagnóstico:
    # custom_button2.clicked.connect(self.debug_current_item)
    """

    def check_ui_components(self):
        """
        Verifica los componentes de UI necesarios para mostrar enlaces e info.
        
        Returns:
            dict: Estado de los componentes
        """
        if not self.music_browser:
            return {"error": "No hay instancia de MusicBrowser para verificar"}
            
        try:
            result = {}
            
            # Verificar grupos de enlaces
            result["link_groups"] = {
                "artist_links_group": {
                    "exists": hasattr(self.music_browser, 'artist_links_group') and self.music_browser.artist_links_group is not None,
                    "visible": self.music_browser.artist_links_group.isVisible() if hasattr(self.music_browser, 'artist_links_group') and self.music_browser.artist_links_group else False
                },
                "album_links_group": {
                    "exists": hasattr(self.music_browser, 'album_links_group') and self.music_browser.album_links_group is not None,
                    "visible": self.music_browser.album_links_group.isVisible() if hasattr(self.music_browser, 'album_links_group') and self.music_browser.album_links_group else False
                }
            }
            
            # Verificar vistas de entidades
            result["entity_views"] = {
                "artist_view": {
                    "exists": hasattr(self.music_browser, 'artist_view') and self.music_browser.artist_view is not None,
                    "wiki_container": {
                        "exists": hasattr(self.music_browser.artist_view, 'wiki_container') if hasattr(self.music_browser, 'artist_view') else False,
                        "visible": self.music_browser.artist_view.wiki_container.isVisible() if hasattr(self.music_browser, 'artist_view') and hasattr(self.music_browser.artist_view, 'wiki_container') else False
                    }
                },
                "album_view": {
                    "exists": hasattr(self.music_browser, 'album_view') and self.music_browser.album_view is not None,
                    "wiki_container": {
                        "exists": hasattr(self.music_browser.album_view, 'wiki_container') if hasattr(self.music_browser, 'album_view') else False,
                        "visible": self.music_browser.album_view.wiki_container.isVisible() if hasattr(self.music_browser, 'album_view') and hasattr(self.music_browser.album_view, 'wiki_container') else False
                    }
                },
                "track_view": {
                    "exists": hasattr(self.music_browser, 'track_view') and self.music_browser.track_view is not None,
                    "lyrics_container": {
                        "exists": hasattr(self.music_browser.track_view, 'lyrics_container') if hasattr(self.music_browser, 'track_view') else False,
                        "visible": self.music_browser.track_view.lyrics_container.isVisible() if hasattr(self.music_browser, 'track_view') and hasattr(self.music_browser.track_view, 'lyrics_container') else False
                    },
                    "wiki_container": {
                        "exists": hasattr(self.music_browser.track_view, 'wiki_container') if hasattr(self.music_browser, 'track_view') else False,
                        "visible": self.music_browser.track_view.wiki_container.isVisible() if hasattr(self.music_browser, 'track_view') and hasattr(self.music_browser.track_view, 'wiki_container') else False
                    }
                }
            }
            
            # Verificar LinkButtonsManager
            result["link_buttons_manager"] = {
                "exists": hasattr(self.music_browser, 'link_buttons') and self.music_browser.link_buttons is not None
            }
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def _patch_extract_links(self):
        """Aplica el parche a EntityView.extract_links."""
        from modules.submodules.fuzzy.entity_view_submodule import EntityView
        
        # Implementación mejorada de extract_links
        def extract_links_improved(self, entity_data, entity_type):
            """Extrae enlaces de los datos de entidad."""
            links = {}
            
            if not entity_data:
                print(f"[DEBUG] No hay datos para extraer enlaces - entity_type: {entity_type}")
                return links
                
            # Extract from dictionary
            if isinstance(entity_data, dict):
                for key, value in entity_data.items():
                    # Busca cualquier campo que contenga "url" (no solo los que terminan en _url)
                    if ('url' in key.lower() or 'link' in key.lower()) and value and isinstance(value, str) and value.strip():
                        # Normaliza el nombre del servicio
                        service_name = key.replace('_url', '').replace('url', '').replace('_link', '').replace('link', '')
                        if service_name.startswith('_') or service_name.endswith('_'):
                            service_name = service_name.strip('_')
                        if service_name:
                            links[service_name] = value
                            if self.debug_mode:
                                print(f"[DEBUG] Enlace encontrado en diccionario: {service_name}: {value[:30]}...")
            
            # Extract from tuple/list (database query result)
            elif isinstance(entity_data, (list, tuple)):
                # Define índices flexibles para diferentes versiones de la BD
                if entity_type == 'artist':
                    # Intenta varias búsquedas posibles para URLs
                    url_indices = {
                        'spotify': [9, 16],  # Posibles índices para spotify_url
                        'youtube': [10, 17],
                        'musicbrainz': [11, 18],
                        'discogs': [12, 19],
                        'rateyourmusic': [13, 20],
                        'wikipedia': [15, 26],
                        'bandcamp': [19, 20],
                        'lastfm': [22, 23]
                    }
                    
                    # Busca en todos los posibles índices para cada servicio
                    for service, possible_indices in url_indices.items():
                        for idx in possible_indices:
                            if idx < len(entity_data) and entity_data[idx] and isinstance(entity_data[idx], str):
                                links[service] = entity_data[idx]
                                if self.debug_mode:
                                    print(f"[DEBUG] Enlace de artista encontrado en índice {idx}: {service}")
                                break  # Al encontrar uno válido, salir del bucle interno
                                
                elif entity_type == 'album':
                    url_indices = {
                        'spotify': [9, 21],
                        'youtube': [11, 22],
                        'musicbrainz': [12, 23],
                        'discogs': [13, 24],
                        'rateyourmusic': [14, 25],
                        'wikipedia': [16, 28],
                        'bandcamp': [22, 23],
                        'lastfm': [26, 27]
                    }
                    
                    for service, possible_indices in url_indices.items():
                        for idx in possible_indices:
                            if idx < len(entity_data) and entity_data[idx] and isinstance(entity_data[idx], str):
                                links[service] = entity_data[idx]
                                if self.debug_mode:
                                    print(f"[DEBUG] Enlace de álbum encontrado en índice {idx}: {service}")
                                break
                                
                # Buscar enlaces en todos los elementos de la tupla por nombre
                for i, item in enumerate(entity_data):
                    if isinstance(item, str) and ('http://' in item or 'https://' in item):
                        # Intenta determinar el tipo de servicio por URL
                        for service in ['spotify', 'youtube', 'lastfm', 'musicbrainz', 'discogs', 'bandcamp', 'wikipedia']:
                            if service in item.lower():
                                links[service] = item
                                if self.debug_mode:
                                    print(f"[DEBUG] Enlace encontrado en posición {i}: {service}: {item[:30]}...")
                                break
            
            # Si no se encontraron enlaces, imprimir mensaje
            if not links and self.debug_mode:
                print(f"[DEBUG] No se encontraron enlaces para {entity_type} en los datos proporcionados")
            elif self.debug_mode:
                print(f"[DEBUG] Enlaces encontrados: {len(links)}")
                
            return links
        
        # Reemplazar el método original
        EntityView.extract_links = extract_links_improved
        
        print("[PATCH] EntityView.extract_links mejorado aplicado")