"""
Módulo para solucionar problemas de visualización de botones en links_buttons_submodule.py

Este archivo debe colocarse junto con los otros submodules de fuzzy music module.
"""

from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QGroupBox
from PyQt6.QtGui import QIcon, QDesktopServices
from PyQt6.QtCore import QSize, QUrl
import traceback
import sys

class LinkButtonsFixer:
    """
    Clase para diagnosticar y solucionar problemas con LinkButtonsManager
    y sus contenedores de botones en MusicBrowser.
    """
    
    def __init__(self, music_browser):
        """
        Inicializar el fixer con referencia al MusicBrowser.
        
        Args:
            music_browser: Instancia de MusicBrowser
        """
        self.music_browser = music_browser
        self.debug_mode = True
        
    def fix_link_buttons(self):
        """
        Corrige los problemas de los botones de enlaces.
        
        Returns:
            bool: True si se corrigieron los problemas
        """
        if not self.music_browser:
            print("[FIXER] No hay una instancia válida de MusicBrowser.")
            return False
            
        try:
            print("[FIXER] Iniciando corrección de botones de enlaces...")
            
            # 1. Verificar y corregir las referencias a los grupos
            self._fix_group_references()
            
            # 2. Arreglar layouts si es necesario
            self._fix_group_layouts()
            
            # 3. Recrear el gestor de botones con las referencias correctas
            self._recreate_link_buttons_manager()
            
            # 4. Aplicar el parche al método de actualización de botones
            self._patch_update_buttons_method()
            
            # 5. Intenta forzar la visibilidad de grupos
            self._force_group_visibility()
            
            # 6. Aplicar parche al método extract_links
            self._patch_extract_links_method()
            
            print("[FIXER] Corrección completada.")
            return True
            
        except Exception as e:
            print(f"[FIXER] Error durante la corrección: {e}")
            traceback.print_exc()
            return False
            
    def _fix_group_references(self):
        """Verifica y corrige las referencias a los grupos de enlaces."""
        print("[FIXER] Verificando referencias a grupos de enlaces...")
        
        # Obtener referencias desde el UI
        if hasattr(self.music_browser, 'main_ui'):
            print("[FIXER] Buscando grupos en main_ui...")
            
            # Buscar los grupos por nombre
            artist_links_group = self.music_browser.main_ui.findChild(QGroupBox, "artist_links_group")
            album_links_group = self.music_browser.main_ui.findChild(QGroupBox, "album_links_group")
            
            # Actualizar referencias en music_browser
            if artist_links_group:
                print("[FIXER] Encontrado artist_links_group en UI.")
                self.music_browser.artist_links_group = artist_links_group
            else:
                print("[FIXER] ¡No se encontró artist_links_group! Buscando alternativas...")
                # Búsqueda alternativa por texto
                for group in self.music_browser.main_ui.findChildren(QGroupBox):
                    if "artist" in group.title().lower() and "link" in group.title().lower():
                        print(f"[FIXER] Encontrado grupo alternativo: {group.title()}")
                        self.music_browser.artist_links_group = group
                        break
            
            if album_links_group:
                print("[FIXER] Encontrado album_links_group en UI.")
                self.music_browser.album_links_group = album_links_group
            else:
                print("[FIXER] ¡No se encontró album_links_group! Buscando alternativas...")
                # Búsqueda alternativa por texto
                for group in self.music_browser.main_ui.findChildren(QGroupBox):
                    if "album" in group.title().lower() and "link" in group.title().lower():
                        print(f"[FIXER] Encontrado grupo alternativo: {group.title()}")
                        self.music_browser.album_links_group = group
                        break
        else:
            print("[FIXER] No se encontró main_ui en MusicBrowser.")
            
    def _fix_group_layouts(self):
        """Verifica y corrige los layouts de los grupos de enlaces."""
        print("[FIXER] Verificando layouts de grupos de enlaces...")
        
        # Verificar y corregir layout de artist_links_group
        if hasattr(self.music_browser, 'artist_links_group') and self.music_browser.artist_links_group:
            if not self.music_browser.artist_links_group.layout():
                print("[FIXER] Creando nuevo layout para artist_links_group")
                layout = QHBoxLayout(self.music_browser.artist_links_group)
                layout.setContentsMargins(5, 5, 5, 5)
                layout.setSpacing(5)
            else:
                print("[FIXER] artist_links_group ya tiene layout")
                # Limpiar layout existente
                layout = self.music_browser.artist_links_group.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
        # Verificar y corregir layout de album_links_group
        if hasattr(self.music_browser, 'album_links_group') and self.music_browser.album_links_group:
            if not self.music_browser.album_links_group.layout():
                print("[FIXER] Creando nuevo layout para album_links_group")
                layout = QHBoxLayout(self.music_browser.album_links_group)
                layout.setContentsMargins(5, 5, 5, 5)
                layout.setSpacing(5)
            else:
                print("[FIXER] album_links_group ya tiene layout")
                # Limpiar layout existente
                layout = self.music_browser.album_links_group.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
    def _recreate_link_buttons_manager(self):
        """Recrea el gestor de botones de enlaces con las referencias correctas."""
        from modules.submodules.fuzzy.links_buttons_submodule import LinkButtonsManager
        
        print("[FIXER] Recreando LinkButtonsManager...")
        
        if (hasattr(self.music_browser, 'artist_links_group') and self.music_browser.artist_links_group and
            hasattr(self.music_browser, 'album_links_group') and self.music_browser.album_links_group):
            
            # Actualizar el enlace
            self.music_browser.link_buttons = LinkButtonsManager(
                self.music_browser.artist_links_group,
                self.music_browser.album_links_group
            )
            
            # Actualizar también las referencias en las vistas
            if hasattr(self.music_browser, 'artist_view') and self.music_browser.artist_view:
                self.music_browser.artist_view.link_buttons = self.music_browser.link_buttons
                print("[FIXER] Actualizada referencia en artist_view")
                
            if hasattr(self.music_browser, 'album_view') and self.music_browser.album_view:
                self.music_browser.album_view.link_buttons = self.music_browser.link_buttons
                print("[FIXER] Actualizada referencia en album_view")
                
            if hasattr(self.music_browser, 'track_view') and self.music_browser.track_view:
                self.music_browser.track_view.link_buttons = self.music_browser.link_buttons
                print("[FIXER] Actualizada referencia en track_view")
                
            print("[FIXER] LinkButtonsManager recreado exitosamente")
        else:
            print("[FIXER] No se pudieron encontrar los grupos necesarios para LinkButtonsManager")
            
    def _patch_update_buttons_method(self):
        """Aplica un parche al método _update_buttons del LinkButtonsManager."""
        print("[FIXER] Aplicando parche a LinkButtonsManager._update_buttons...")
        
        if not hasattr(self.music_browser, 'link_buttons') or not self.music_browser.link_buttons:
            print("[FIXER] No hay LinkButtonsManager para parchear.")
            return
            
        # Definir la versión mejorada del método
        def patched_update_buttons(self_lbm, container, layout, links_dict, button_store, entity_type):
            """
            Versión mejorada de _update_buttons con mejor manejo de visibilidad.
            """
            import traceback
            
            print(f"[DEBUG] Actualizando botones para {entity_type}")
            
            if not links_dict:
                print(f"[DEBUG] No hay enlaces para mostrar en {entity_type}")
                container.hide()
                return False
            
            # Filtrar enlaces no válidos o especiales
            filtered_links = {}
            for service_name, url in links_dict.items():
                if not url or not isinstance(url, str) or not url.strip():
                    continue
                # Excluir campos que no son enlaces
                if service_name in ['s_updated', 'links_updated', 'last_updated']:
                    continue
                filtered_links[service_name] = url
                
            if not filtered_links:
                print(f"[DEBUG] No hay enlaces válidos para {entity_type} después de filtrar")
                container.hide()
                return False
                
            print(f"[DEBUG] Creando {len(filtered_links)} botones para {entity_type}")
            
            try:
                # Limpiar layout existente
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
                # Limpiar diccionario de botones
                button_store.clear()
                
                # Create buttons for each link
                for service_name, url in filtered_links.items():
                    try:
                        # Create button
                        button = self_lbm._create_service_button(service_name, url, entity_type)
                        
                        # Add to layout
                        layout.addWidget(button)
                        
                        # Store reference
                        button_store[service_name] = button
                        
                        print(f"[DEBUG] Botón creado para {service_name}: {url[:30]}...")
                    except Exception as btn_err:
                        print(f"[DEBUG] Error al crear botón para {service_name}: {btn_err}")
                        traceback.print_exc()
                
                # Add stretch at the end to push buttons to the left
                layout.addStretch()
                
                # Show container if buttons were added
                has_buttons = len(button_store) > 0
                
                # Forzar la visibilidad del contenedor y sus padres
                if has_buttons:
                    # Hacer visible el contenedor primero
                    container.setVisible(True)
                    
                    # Actualizar layout
                    layout.update()
                    
                    # Forzar visibilidad
                    container.show()
                    
                    # Asegurar que todos los padres son visibles
                    parent = container.parent()
                    while parent:
                        parent.setVisible(True)
                        parent.show()
                        parent = parent.parent()
                    
                    print(f"[DEBUG] Contenedor de {entity_type} visible con {len(button_store)} botones")
                    
                    # Forzar actualización de UI
                    container.update()
                    # Forzar procesamiento de eventos
                    from PyQt6.QtCore import QCoreApplication
                    QCoreApplication.processEvents()
                else:
                    container.hide()
                    print(f"[DEBUG] Contenedor de {entity_type} oculto - sin botones")
                
                return has_buttons
                
            except Exception as e:
                print(f"[DEBUG] Error en _update_buttons: {e}")
                traceback.print_exc()
                return False
                
        # Reemplazar el método original
        self.music_browser.link_buttons._update_buttons = patched_update_buttons.__get__(self.music_browser.link_buttons)
        print("[FIXER] Método _update_buttons parcheado exitosamente")
        
    def _force_group_visibility(self):
        """Fuerza la visibilidad de los grupos de enlaces."""
        print("[FIXER] Forzando visibilidad de grupos de enlaces...")
        
        # Mostrar artist_links_group
        if hasattr(self.music_browser, 'artist_links_group') and self.music_browser.artist_links_group:
            self.music_browser.artist_links_group.setVisible(True)
            self.music_browser.artist_links_group.show()
            
            # Mostrar todos los padres
            parent = self.music_browser.artist_links_group.parent()
            while parent:
                parent.setVisible(True)
                parent.show()
                parent = parent.parent()
        
        # Mostrar album_links_group
        if hasattr(self.music_browser, 'album_links_group') and self.music_browser.album_links_group:
            self.music_browser.album_links_group.setVisible(True)
            self.music_browser.album_links_group.show()
            
            # Mostrar todos los padres
            parent = self.music_browser.album_links_group.parent()
            while parent:
                parent.setVisible(True)
                parent.show()
                parent = parent.parent()
                
    def _patch_extract_links_method(self):
        """Aplica un parche al método extract_links de EntityView."""
        from modules.submodules.fuzzy.entity_view_submodule import EntityView
        
        print("[FIXER] Aplicando parche a EntityView.extract_links...")
        
        # Definir la versión mejorada del método
        def patched_extract_links(self_ev, entity_data, entity_type):
            """
            Versión mejorada del método extract_links con mejor detección de enlaces.
            """
            links = {}
            
            if not entity_data:
                print(f"[DEBUG] No hay datos para extraer enlaces - entity_type: {entity_type}")
                return links
                
            # Extract from dictionary
            if isinstance(entity_data, dict):
                for key, value in entity_data.items():
                    # Busca cualquier campo que contenga "url" o "link"
                    if ('url' in key.lower() or 'link' in key.lower()) and value and isinstance(value, str) and value.strip():
                        # Normaliza el nombre del servicio
                        service_name = key.replace('_url', '').replace('url', '').replace('_link', '').replace('link', '')
                        if service_name.startswith('_') or service_name.endswith('_'):
                            service_name = service_name.strip('_')
                        if service_name:
                            links[service_name] = value
                            print(f"[DEBUG] Enlace encontrado en diccionario: {service_name}: {value[:30]}...")
            
            # Extract from tuple/list (database query result)
            elif isinstance(entity_data, (list, tuple)):
                # Define índices conocidos para diferentes servicios
                url_indices = {}
                
                if entity_type == 'artist':
                    # Índices conocidos para artistas (con valores alternativos)
                    url_indices = {
                        'spotify': [9, 16, 'spotify'],
                        'youtube': [10, 17, 'youtube'],
                        'musicbrainz': [11, 18, 'musicbrainz'],
                        'discogs': [12, 19, 'discogs'],
                        'rateyourmusic': [13, 20, 'rateyourmusic'],
                        'wikipedia': [15, 26, 'wiki'],
                        'bandcamp': [19, 20, 'bandcamp'],
                        'lastfm': [22, 23, 'lastfm']
                    }
                elif entity_type == 'album':
                    # Índices conocidos para álbumes (con valores alternativos)
                    url_indices = {
                        'spotify': [9, 21, 'spotify'],
                        'youtube': [11, 22, 'youtube'],
                        'musicbrainz': [12, 23, 'musicbrainz'],
                        'discogs': [13, 24, 'discogs'],
                        'rateyourmusic': [14, 25, 'rateyourmusic'],
                        'wikipedia': [16, 28, 'wiki'],
                        'bandcamp': [22, 23, 'bandcamp'],
                        'lastfm': [26, 27, 'lastfm']
                    }
                    
                # Revisar todos los índices conocidos
                for service, info in url_indices.items():
                    idx1, idx2, keyword = info
                    # Probar el primer índice
                    if idx1 < len(entity_data) and entity_data[idx1] and isinstance(entity_data[idx1], str) and entity_data[idx1].strip():
                        links[service] = entity_data[idx1]
                        print(f"[DEBUG] Enlace de {entity_type} encontrado en índice {idx1}: {service}")
                    # Probar el segundo índice si el primero falló
                    elif idx2 < len(entity_data) and entity_data[idx2] and isinstance(entity_data[idx2], str) and entity_data[idx2].strip():
                        links[service] = entity_data[idx2]
                        print(f"[DEBUG] Enlace de {entity_type} encontrado en índice {idx2}: {service}")
                
                # Buscar enlaces en todos los elementos de la tupla
                for i, item in enumerate(entity_data):
                    if isinstance(item, str) and ('http://' in item or 'https://' in item):
                        # Intentar determinar el tipo de servicio por URL
                        for service in url_indices:
                            keyword = url_indices[service][2]
                            if keyword in item.lower():
                                links[service] = item
                                print(f"[DEBUG] Enlace encontrado en posición {i}: {service}: {item[:30]}...")
                                break
            
            # Si no se encontraron enlaces, imprimir mensaje
            if not links:
                print(f"[DEBUG] No se encontraron enlaces para {entity_type} en los datos proporcionados")
            else:
                print(f"[DEBUG] Enlaces encontrados: {len(links)}")
                
            return links
            
        # Reemplazar el método original
        EntityView.extract_links = patched_extract_links
        print("[FIXER] Método EntityView.extract_links parcheado exitosamente")
        
    @classmethod
    def add_fix_method_to_music_browser(cls, music_browser):
        """
        Añade el método fix_link_buttons al MusicBrowser para facilitar su uso.
        
        Args:
            music_browser: Instancia de MusicBrowser
        """
        def fix_link_buttons_method(self):
            """
            Corrige los problemas de visualización de los botones de enlaces.
            Este método se añade dinámicamente a MusicBrowser.
            """
            fixer = LinkButtonsFixer(self)
            return fixer.fix_link_buttons()
            
        setattr(music_browser, 'fix_link_buttons', fix_link_buttons_method.__get__(music_browser))
        
        
def apply_to_music_browser(music_browser):
    """
    Aplica todas las correcciones a una instancia de MusicBrowser.
    
    Args:
        music_browser: Instancia de MusicBrowser
        
    Returns:
        bool: True si se aplicaron las correcciones exitosamente
    """
    fixer = LinkButtonsFixer(music_browser)
    result = fixer.fix_link_buttons()
    
    # Añadir método fix_link_buttons a MusicBrowser
    LinkButtonsFixer.add_fix_method_to_music_browser(music_browser)
    
    return result


# Ejemplo de uso
if __name__ == "__main__":
    print("Este módulo debe importarse y aplicarse a una instancia de MusicBrowser.")
    print("Ejemplo de uso:")
    print("  from modules.submodules.fuzzy.links_buttons_fix import apply_to_music_browser")
    print("  apply_to_music_browser(self)  # donde 'self' es tu instancia de MusicBrowser")