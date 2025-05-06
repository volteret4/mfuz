import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt

class DBMusicPathModule:
    """Submódulo para gestionar la creación de base de datos con db_musica_path.py"""
    
    def __init__(self, parent=None, config=None):
        self.parent = parent
        self.config = config or {}
        self.music_path = ""
        self.db_path = ""
        self.config_file_path = ""
        self.supported_extensions = ['.mp3', '.flac', '.m4a']
        self.options = {
            'force_update': False,
            'update_replay_gain': False,
            'update_schema': False,
            'optimize': False,
            'update_bitrates': False,
            'quick_scan': False
        }
        
        # Referencia a los checkboxes para poder leer sus valores
        self.checkboxes = {}
        
        # Extract default values from config if available
        self._extract_config_values()
        
        # Obtener la ruta del archivo de configuración del padre
        if parent and hasattr(parent, 'config_file'):
            self.config_file_path = parent.config_file
        
    def load_config(self, config):
        """Carga configuración desde un diccionario."""
        self.config = config
        self._extract_config_values()
        # Actualizar la UI si ya está inicializada
        if hasattr(self, 'path_line'):
            self._load_config_to_ui()
        
    def _extract_config_values(self):
        """Extract values from config data."""
        if not self.config:
            print("No hay configuración disponible para DBMusicPathModule")
            return
            
        print("Extrayendo valores de configuración para DBMusicPathModule")
        print(f"Config keys: {list(self.config.keys())}")
        
        # Primero buscamos db_path en la sección common
        if 'common' in self.config:
            common_config = self.config['common']
            print(f"Common config keys: {list(common_config.keys())}")
            if 'db_path' in common_config:
                self.db_path = common_config['db_path']
                print(f"Ruta de base de datos extraída: {self.db_path}")
        
        # Luego buscamos la configuración específica de db_musica_path
        if 'db_musica_path' in self.config:
            module_config = self.config['db_musica_path']
            print(f"db_musica_path config keys: {list(module_config.keys())}")
            
            if 'root_path' in module_config:
                self.music_path = module_config['root_path']
                print(f"Ruta de música extraída: {self.music_path}")
            
            # Extract options - Mostrar valores explícitamente
            for key in self.options.keys():
                if key in module_config:
                    old_value = self.options[key]
                    new_value = module_config[key]
                    self.options[key] = new_value
                    print(f"Opción actualizada: {key} de {old_value} a {new_value}")
                else:
                    print(f"Opción no encontrada en config: {key}")
 


    def setup_ui(self, container):
        """Setup the UI elements for this module."""
        # Depuración detallada del contenedor
        print(f"Configurando UI para DBMusicPathModule en contenedor: {container.objectName()}")
        
        # Encontrar elementos por jerarquía
        print("Buscando elementos por jerarquía...")
        
        # Buscar QLineEdit para rutas
        self.path_line = container.findChild(QLineEdit, "rutaSelector_line")
        if self.path_line:
            print("✓ Encontrado rutaSelector_line")
        else:
            print("✗ No se encontró rutaSelector_line")
            # Intentar buscar cualquier QLineEdit
            all_line_edits = container.findChildren(QLineEdit)
            if all_line_edits:
                self.path_line = all_line_edits[0]
                print(f"  Usando primer QLineEdit disponible: {self.path_line.objectName()}")
        
        # Buscar QLineEdit para base de datos
        self.db_path_line = container.findChild(QLineEdit, "db_path_line")
        if self.db_path_line:
            print("✓ Encontrado db_path_line")
        else:
            print("✗ No se encontró db_path_line")
            # Intentar encontrar un segundo QLineEdit
            all_line_edits = container.findChildren(QLineEdit)
            if len(all_line_edits) > 1:
                self.db_path_line = all_line_edits[1]
                print(f"  Usando segundo QLineEdit disponible: {self.db_path_line.objectName()}")
        
        # Buscar botones
        browse_button = container.findChild(QPushButton, "music_browse")  # Botón de explorar carpeta
        db_browse_button = container.findChild(QPushButton, "db_browse_button")  # Botón de explorar BD
        self.run_button = container.findChild(QPushButton, "run_button")  # Botón de analizar
        self.create_db_button = container.findChild(QPushButton, "create_db_button")  # Botón de crear BD
        self.save_config_button = container.findChild(QPushButton, "save_config_button")  # Botón de guardar config
        
        # Buscar save_config_button por nombre alternativo
        if not self.save_config_button:
            self.save_config_button = container.findChild(QPushButton, "create_db_button_2")
        
        # Si no se encuentran, intentar buscar por orden
        all_buttons = container.findChildren(QPushButton)
        if all_buttons:
            if not browse_button and len(all_buttons) > 0:
                browse_button = all_buttons[0]
                print(f"  Usando primer QPushButton disponible: {browse_button.objectName()}")
            if not db_browse_button and len(all_buttons) > 1:
                db_browse_button = all_buttons[1]
                print(f"  Usando segundo QPushButton disponible: {db_browse_button.objectName()}")
            if not self.run_button and len(all_buttons) > 2:
                self.run_button = all_buttons[2]
                print(f"  Usando tercer QPushButton disponible: {self.run_button.objectName()}")
            if not self.create_db_button and len(all_buttons) > 3:
                self.create_db_button = all_buttons[3]
                print(f"  Usando cuarto QPushButton disponible: {self.create_db_button.objectName()}")
            if not self.save_config_button and len(all_buttons) > 4:
                self.save_config_button = all_buttons[4]
                print(f"  Usando quinto QPushButton disponible: {self.save_config_button.objectName()}")
        
        # Buscar groupbox de opciones y sus checkboxes
        options_group = container.findChild(QGroupBox, "opciones")
        if options_group:
            print(f"✓ Encontrado grupo de opciones: {options_group.objectName()}")
        else:
            # Intentar buscar cualquier QGroupBox
            all_group_boxes = container.findChildren(QGroupBox)
            if all_group_boxes:
                options_group = all_group_boxes[0]
                print(f"  Usando primer QGroupBox disponible: {options_group.objectName()}")
            else:
                print("✗ No se encontró ningún QGroupBox para opciones")
        
        # Buscar los checkboxes dentro del groupbox
        self.checkboxes = {}
        if options_group:
            print(f"Buscando checkboxes dentro de {options_group.objectName()}...")
            # Buscar por nombres específicos primero
            checkbox_names = {
                'force_update': ['checkbox_force_update', 'force_update_checkbox', 'force_update'],
                'update_replay_gain': ['checkbox_update_replay_gain', 'update_replay_gain_checkbox', 'update_replay_gain'],
                'update_schema': ['checkbox_update_schema', 'update_schema_checkbox', 'update_schema'],
                'optimize': ['checkbox_optimize', 'optimize_checkbox', 'optimize'],
                'update_bitrates': ['checkbox_update_bitrates', 'update_bitrates_checkbox', 'update_bitrates'],
                'quick_scan': ['checkbox_quick_scan', 'quick_scan_checkbox', 'quick_scan']
            }
            
            for option_key, names in checkbox_names.items():
                for name in names:
                    checkbox = options_group.findChild(QCheckBox, name)
                    if checkbox:
                        self.checkboxes[option_key] = checkbox
                        print(f"✓ Encontrado checkbox para {option_key}: {checkbox.objectName()}")
                        break
            
            # Si no encontramos por nombre, buscar por texto
            checkbox_texts = {
                'force_update': ['force update', 'forzar actualización'],
                'update_replay_gain': ['replaygain', 'replay gain'],
                'update_schema': ['esquema'],
                'optimize': ['optimizar', 'optimize'],
                'update_bitrates': ['bitrates', 'bitrate'],
                'quick_scan': ['escaneo rápido', 'quick scan', 'scan']
            }
            
            for option_key, text_options in checkbox_texts.items():
                if option_key not in self.checkboxes:
                    all_checkboxes = options_group.findChildren(QCheckBox)
                    for checkbox in all_checkboxes:
                        checkbox_text = checkbox.text().lower()
                        for text in text_options:
                            if text in checkbox_text:
                                self.checkboxes[option_key] = checkbox
                                print(f"✓ Encontrado checkbox para {option_key} por texto: '{checkbox.text()}'")
                                break
                        if option_key in self.checkboxes:
                            break
            
            # Si aún faltan checkboxes, asignar por orden
            if len(self.checkboxes) < len(self.options):
                all_checkboxes = options_group.findChildren(QCheckBox)
                missing_keys = [k for k in self.options.keys() if k not in self.checkboxes]
                
                for i, key in enumerate(missing_keys):
                    if i < len(all_checkboxes):
                        # Buscar un checkbox no utilizado
                        for checkbox in all_checkboxes:
                            if checkbox not in self.checkboxes.values():
                                self.checkboxes[key] = checkbox
                                print(f"  Asignando checkbox '{checkbox.text()}' a {key}")
                                break
        else:
            print("✗ No se encontró el grupo de opciones")
            # Intentar buscar checkboxes en el contenedor principal por texto
            checkbox_texts = {
                'force_update': ['force update', 'forzar actualización'],
                'update_replay_gain': ['replaygain', 'replay gain'],
                'update_schema': ['esquema'],
                'optimize': ['optimizar', 'optimize'],
                'update_bitrates': ['bitrates', 'bitrate'],
                'quick_scan': ['escaneo rápido', 'quick scan', 'scan']
            }
            
            all_checkboxes = container.findChildren(QCheckBox)
            for option_key, text_options in checkbox_texts.items():
                for checkbox in all_checkboxes:
                    checkbox_text = checkbox.text().lower()
                    for text in text_options:
                        if text in checkbox_text:
                            self.checkboxes[option_key] = checkbox
                            print(f"✓ Encontrado checkbox para {option_key} por texto: '{checkbox.text()}'")
                            break
                    if option_key in self.checkboxes:
                        break
        
        # Buscar labels para estadísticas
        self.stats_labels = {
            'folders': container.findChild(QLabel, "stats_folders_label"),
            'files': container.findChild(QLabel, "stats_files_label"),
            'size': container.findChild(QLabel, "stats_size_label")
        }
        
        # Si no se encuentran, intentar buscar por contenido de texto
        for key in self.stats_labels:
            if not self.stats_labels[key]:
                all_labels = container.findChildren(QLabel)
                for label in all_labels:
                    label_text = label.text().lower()
                    if key in label_text or key[:-1] in label_text:  # Intentar con "folder" y "file" también
                        self.stats_labels[key] = label
                        print(f"✓ Encontrado label para {key} por texto: '{label.text()}'")
                        break
        
        # Si aún faltan labels, intentar por orden
        if not all(self.stats_labels.values()):
            # Intentar encontrar qlabels que puedan servir como stats
            all_labels = container.findChildren(QLabel)
            valid_labels = [label for label in all_labels if not label.text().endswith(':')]
            if len(valid_labels) >= 3:
                for i, key in enumerate(['folders', 'files', 'size']):
                    if not self.stats_labels[key] and i < len(valid_labels):
                        self.stats_labels[key] = valid_labels[i]
                        print(f"  Asignando QLabel '{valid_labels[i].text()}' como {key}")
        
        # Verificar elementos mínimos encontrados
        elements_found = bool(self.path_line and self.db_path_line)
        print(f"¿Se encontraron elementos mínimos necesarios? {elements_found}")
        
        # Cargar configuración desde el padre
        if self.parent and hasattr(self.parent, 'config_data'):
            print("Actualizando configuración desde el padre")
            self.config = self.parent.config_data
            self._extract_config_values() 

        # Conectar señales
        if self.path_line:
            self.path_line.textChanged.connect(self.on_path_changed)
        if self.db_path_line:
            self.db_path_line.textChanged.connect(self.on_db_path_changed)
        if browse_button:
            browse_button.clicked.connect(self.browse_for_music_folder)
        if db_browse_button:
            db_browse_button.clicked.connect(self.browse_for_db_file)
        if self.run_button:
            self.run_button.clicked.connect(self.analyze_folder)
        if self.create_db_button:
            self.create_db_button.clicked.connect(self.create_database)
        if self.save_config_button:
            self.save_config_button.clicked.connect(self.save_config_to_file)
            
        # Conectar checkboxes
        for option_key, checkbox in self.checkboxes.items():
            checkbox.stateChanged.connect(
                lambda state, key=option_key: self.on_option_changed(key, state)
            )
            
        # Cargar valores de configuración a la UI
        self._load_config_to_ui()
        
    def set_music_path(self, path):
        """Set the music path."""
        self.music_path = path
        if hasattr(self, 'path_line'):
            self.path_line.setText(path)
        self.update_config()
        
    def on_path_changed(self, text):
        """Handle changes to the music path."""
        self.music_path = text
        self.update_ui_state()
        self.update_config()
        
    def on_db_path_changed(self, text):
        """Handle changes to the database path."""
        self.db_path = text
        self.update_ui_state()
        self.update_config()
        
    def on_option_changed(self, option_key, state):
        """Handle changes to options."""
        self.options[option_key] = state == Qt.CheckState.Checked
        self.update_config()
        
    def _format_option_name(self, option_key):
        """Format option key to a readable name."""
        # Replace underscores with spaces and capitalize
        return ' '.join(word.capitalize() for word in option_key.split('_'))
        
    def update_ui_state(self):
        """Update the UI state based on current values."""
        # Enable/disable run button based on path values
        has_valid_paths = bool(self.music_path and os.path.isdir(self.music_path))
        
        if hasattr(self, 'run_button') and self.run_button:
            self.run_button.setEnabled(has_valid_paths)
            
        # Enable create database button if we have a valid DB path
        has_valid_db_path = bool(self.db_path)
        if hasattr(self, 'create_db_button') and self.create_db_button:
            self.create_db_button.setEnabled(has_valid_paths and has_valid_db_path)
            
    def _load_config_to_ui(self):
        """Carga los valores de configuración a la UI."""
        print("\n=== Cargando configuración a UI en DBMusicPathModule ===")
        print(f"Music path: '{self.music_path}'")
        print(f"DB path: '{self.db_path}'")
        print(f"Options: {self.options}")
        
        # Cargar valores solo si los widgets existen
        if hasattr(self, 'path_line') and self.path_line:
            current_text = self.path_line.text()
            if current_text != self.music_path:
                print(f"Actualizando path_line de '{current_text}' a '{self.music_path}'")
                self.path_line.setText(self.music_path)
        else:
            print("ERROR: No se puede cargar music_path - widget path_line no encontrado")
        
        if hasattr(self, 'db_path_line') and self.db_path_line:
            current_text = self.db_path_line.text()
            if current_text != self.db_path:
                print(f"Actualizando db_path_line de '{current_text}' a '{self.db_path}'")
                self.db_path_line.setText(self.db_path)
        else:
            print("ERROR: No se puede cargar db_path - widget db_path_line no encontrado")
        
        # Cargar opciones a checkboxes - VERIFICANDO EXPLÍCITAMENTE CADA VALOR
        print("\nEstado de los checkboxes:")
        for key, value in self.options.items():
            print(f"Opción en configuración: {key} = {value}")
            
            if hasattr(self, 'checkboxes') and key in self.checkboxes and self.checkboxes[key]:
                try:
                    checkbox = self.checkboxes[key]
                    current_state = checkbox.isChecked()
                    print(f"  Estado actual del checkbox {key}: {current_state}, nuevo estado: {value}")
                    
                    if current_state != value:
                        # Usar directamente setChecked para evitar problemas
                        checkbox.setChecked(bool(value))
                        print(f"  ✓ Checkbox {key} actualizado a {value}")
                        
                        # Verificar que realmente cambió
                        if checkbox.isChecked() != value:
                            print(f"  ⚠ ADVERTENCIA: El checkbox {key} no se actualizó correctamente")
                except Exception as e:
                    print(f"  ⚠ ERROR al configurar checkbox {key}: {str(e)}")
            else:
                print(f"  ⚠ ERROR: No se puede configurar {key} - checkbox no encontrado")
        
        print("=== Fin de carga de configuración ===\n")

    def update_config(self):
        """Update the configuration with current values."""
        if not self.parent or not hasattr(self.parent, 'config_data'):
            print("No se puede actualizar la configuración: parent o config_data no disponible")
            return
                
        # Ensure sections exist
        if 'common' not in self.parent.config_data:
            self.parent.config_data['common'] = {}
        if 'db_musica_path' not in self.parent.config_data:
            self.parent.config_data['db_musica_path'] = {}
                
        # Update values
        self.parent.config_data['common']['db_path'] = self.db_path
        self.parent.config_data['db_musica_path']['root_path'] = self.music_path
            
        # Update options in both local and parent config
        for key, value in self.options.items():
            self.parent.config_data['db_musica_path'][key] = value
        
        # Actualizar configuración local también
        self.config = self.parent.config_data
        
        print("Configuración actualizada con éxito")
        
        # Si hay un método para guardar la configuración en el padre, usarlo
        if hasattr(self.parent, 'save_config') and self.config_file_path:
            try:
                self.parent.save_config(self.config_file_path)
                print(f"Configuración guardada en {self.config_file_path}")
            except Exception as e:
                print(f"Error al guardar configuración: {str(e)}")
            
    def validate(self):
        """Validate the current settings."""
        if not self.music_path or not os.path.isdir(self.music_path):
            QMessageBox.warning(
                self.parent, 
                "Carpeta inválida", 
                "Por favor selecciona una carpeta de música válida."
            )
            return False
            
        if not self.db_path:
            QMessageBox.warning(
                self.parent, 
                "Base de datos no especificada", 
                "Por favor especifica la ruta para el archivo de base de datos."
            )
            return False
            
        # Check if parent directory of db_path exists
        db_parent_dir = os.path.dirname(self.db_path)
        if db_parent_dir and not os.path.isdir(db_parent_dir):
            result = QMessageBox.question(
                self.parent,
                "Directorio no existe",
                f"El directorio para la base de datos no existe: {db_parent_dir}\n¿Deseas crearlo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if result == QMessageBox.StandardButton.Yes:
                try:
                    os.makedirs(db_parent_dir, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(
                        self.parent,
                        "Error",
                        f"No se pudo crear el directorio: {str(e)}"
                    )
                    return False
            else:
                return False
                
        return True
        
    def browse_for_music_folder(self):
        """Open a file dialog to select music folder."""
        folder = QFileDialog.getExistingDirectory(
            self.parent, 
            "Seleccionar carpeta de música", 
            self.music_path or str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.path_line.setText(folder)
            self.music_path = folder
            self.update_config()
            self.update_ui_state()
            
    def browse_for_db_file(self):
        """Open a file dialog to select or create database file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Seleccionar archivo de base de datos",
            self.db_path or str(Path.home()),
            "Archivos SQLite (*.sqlite *.db);;Todos los archivos (*)"
        )
        if file_path:
            self.db_path_line.setText(file_path)
            self.db_path = file_path
            self.update_config()
            self.update_ui_state()
            
    def analyze_folder(self):
        """Analyze the music folder and update statistics."""
        if not self.music_path or not os.path.isdir(self.music_path):
            QMessageBox.warning(
                self.parent, 
                "Carpeta inválida", 
                "Por favor selecciona una carpeta de música válida."
            )
            return
            
        # Disable UI during analysis
        self.run_button.setEnabled(False)
        self.run_button.setText("Analizando...")
        
        # Call scan function
        folder_count, file_count, total_size = self.scan_music_folder(self.music_path)
        
        # Update UI labels
        self.stats_labels['folders'].setText(str(folder_count))
        self.stats_labels['files'].setText(str(file_count))
        self.stats_labels['size'].setText(self.format_size(total_size))
        
        # Re-enable UI
        self.run_button.setText("Analizar Carpeta")
        self.run_button.setEnabled(True)
        
        # Enable create database button if we found audio files and have a valid DB path
        has_valid_db_path = bool(self.db_path)
        self.create_db_button.setEnabled(file_count > 0 and has_valid_db_path)
        
        if file_count == 0:
            QMessageBox.warning(
                self.parent, 
                "No se encontraron archivos", 
                f"No se encontraron archivos de audio soportados ({', '.join(self.supported_extensions)}) en la carpeta seleccionada."
            )
        else:
            QMessageBox.information(
                self.parent, 
                "Análisis completado", 
                f"Se encontraron {file_count} archivos de audio en {folder_count} carpetas."
            )
            
    def scan_music_folder(self, folder_path) -> Tuple[int, int, int]:
        """
        Scan music folder and return statistics.
        
        Returns:
            Tuple of (folder_count, file_count, total_size_in_bytes)
        """
        folder_count = 0
        file_count = 0
        total_size = 0
        
        for root, dirs, files in os.walk(folder_path):
            folder_count += 1
            
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in self.supported_extensions:
                    file_count += 1
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except:
                        pass  # Ignore errors getting file size
                        
        return folder_count, file_count, total_size
        
    def format_size(self, size_bytes):
        """Format size in bytes to human readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def save_config_to_file(self):
        """Guarda la configuración actual en el archivo de configuración."""
        # Actualizar config con valores actuales
        self.update_values_from_ui()
        
        if not self.config_file_path:
            # Ofrecer guardar en una nueva ubicación
            file_path, _ = QFileDialog.getSaveFileName(
                self.parent,
                "Guardar configuración como",
                str(Path.home()),
                "Archivos JSON (*.json);;Archivos YAML (*.yml *.yaml);;Todos los archivos (*)"
            )
            if not file_path:
                return
            self.config_file_path = file_path
        
        # Guardar archivo
        try:
            if hasattr(self.parent, 'save_config'):
                success = self.parent.save_config(self.config_file_path)
                if success:
                    QMessageBox.information(
                        self.parent,
                        "Configuración guardada",
                        f"La configuración ha sido guardada en {self.config_file_path}"
                    )
                    return
            
            # Fallback si el método del padre no existe o falló
            self.save_config_file_direct(self.config_file_path)
            
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Error",
                f"No se pudo guardar la configuración: {str(e)}"
            )
    
    def save_config_file_direct(self, config_file):
        """Guarda el archivo de configuración directamente."""
        try:
            with open(config_file, 'w') as f:
                if config_file.endswith('.json'):
                    json.dump(self.parent.config_data, f, indent=2)
                elif config_file.endswith(('.yml', '.yaml')):
                    import yaml
                    yaml.dump(self.parent.config_data, f, default_flow_style=False)
                else:
                    # Por defecto, usar JSON
                    json.dump(self.parent.config_data, f, indent=2)
                    
            QMessageBox.information(
                self.parent,
                "Configuración guardada",
                f"La configuración ha sido guardada en {config_file}"
            )
            return True
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Error",
                f"No se pudo guardar la configuración: {str(e)}"
            )
            return False
            
    def update_values_from_ui(self):
        """Actualiza los valores de configuración desde la UI."""
        # Obtener valores de campos de texto
        if hasattr(self, 'rutaSelector_line') and self.path_line:
            self.music_path = self.path_line.text()
            print(f"Valor actualizado de music_path: '{self.music_path}'")
        
        if hasattr(self, 'db_path_line') and self.db_path_line:
            self.db_path = self.db_path_line.text()
            print(f"Valor actualizado de db_path: '{self.db_path}'")
        
        # Obtener valores de checkboxes
        for key, checkbox in self.checkboxes.items():
            if checkbox:
                self.options[key] = checkbox.isChecked()
                print(f"Valor actualizado de {key}: {self.options[key]}")
        
        # Actualizar configuración
        self.update_config()
            
    def create_database(self):
        """Run the database creation script."""
        if not self.validate():
            return
            
        # Asegurarse de que la configuración esté actualizada con los valores de la UI
        self.update_values_from_ui()
            
        # Confirmar la operación
        message = "¿Estás seguro de que deseas crear/actualizar la base de datos con los siguientes parámetros?\n\n"
        message += f"- Carpeta de música: {self.music_path}\n"
        message += f"- Archivo de base de datos: {self.db_path}\n\n"
        message += "Opciones seleccionadas:\n"
        
        for key, value in self.options.items():
            if value:
                message += f"- {self._format_option_name(key)}\n"
                
        result = QMessageBox.question(
            self.parent,
            "Confirmar creación de base de datos",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        # Guardar configuración actual antes de ejecutar
        if self.config_file_path:
            try:
                if hasattr(self.parent, 'save_config'):
                    self.parent.save_config(self.config_file_path)
                else:
                    self.save_config_file_direct(self.config_file_path)
            except Exception as e:
                if hasattr(self.parent, 'output_text'):
                    self.parent.output_text.append(f"<span style='color:orange'>Advertencia: No se pudo guardar la configuración: {str(e)}</span>")
        
        # Ejecutar db_creator.py con el archivo de configuración actual
        args = []
        
        if self.config_file_path:
            args = ["--config", str(self.config_file_path)]  # Convertir a string
            
            # Log
            if hasattr(self.parent, 'output_text'):
                self.parent.output_text.append(f"Ejecutando db_creator.py con el archivo de configuración: {self.config_file_path}")
        else:
            # Si no hay archivo de configuración, crear uno temporal
            temp_config = {
                "scripts_order": ["db_musica_path"],
                "common": {
                    "db_path": str(self.db_path)  # Convertir a string
                },
                "db_musica_path": {
                    "root_path": str(self.music_path)  # Convertir a string
                }
            }
            
            # Agregar opciones
            for key, value in self.options.items():
                temp_config["db_musica_path"][key] = value
            
            # Log
            if hasattr(self.parent, 'output_text'):
                self.parent.output_text.append(f"Usando configuración temporal: {json.dumps(temp_config, indent=2)}")
                
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(temp_config, temp_file, indent=2)
                args = ["--config", temp_file.name]
        
        # Ejecutar el script
        if self.parent and hasattr(self.parent, 'run_db_script'):
            self.parent.run_db_script("db_creator", args)
            
    def parse_output(self, output):
        """Parse script output and update UI as needed."""
        # Extract folder count
        folder_match = re.search(r"Se encontraron (\d+) carpetas", output)
        if folder_match and hasattr(self, 'stats_labels'):
            folders_matched = folder_match.group(1)
            self.stats_labels['folders'].setText(f"{folders_matched} carpetas")
            
        # Extract file count
        file_match = re.search(r"Files processed: (\d+)", output)
        if file_match and hasattr(self, 'stats_labels'):
            files_matched = file_match.group(1)
            self.stats_labels['files'].setText(f"{files_matched} archivos")
            
        # Extract errors
        error_match = re.search(r"Files with errors: (\d+)", output)
        if error_match and self.parent and hasattr(self.parent, 'output_text'):
            error_count = int(error_match.group(1))
            if error_count > 0:
                self.parent.output_text.append(f"<span style='color:orange'>Atención: {error_count} archivos con errores</span>")
                
    def script_finished(self, exit_code):
        """Handle script completion."""
        if exit_code == 0:
            QMessageBox.information(
                self.parent,
                "Operación completada",
                "La base de datos ha sido creada/actualizada correctamente."
            )
            
            # Enable navigation to next step if applicable
            if self.parent and hasattr(self.parent, 'siguiente_boton'):
                self.parent.siguiente_boton.setEnabled(True)
        else:
            QMessageBox.warning(
                self.parent,
                "Error",
                f"Ha ocurrido un error durante la creación de la base de datos (código {exit_code}).\nRevisa el log para más detalles."
            )