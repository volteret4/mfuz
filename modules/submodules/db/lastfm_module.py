import os
import sys
import json
import sqlite3
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QCheckBox, QFileDialog, QMessageBox, QApplication, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QProcess
from PyQt6.QtGui import QIcon

# Asegurar que podemos importar desde el directorio raíz del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from base_module import PROJECT_ROOT

class OutputCaptureThread(QThread):
    """Thread for capturing and processing script output."""
    output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    process_finished = pyqtSignal(int)
    
    def __init__(self, command, cwd=None, env=None):
        super().__init__()
        self.command = command
        self.cwd = cwd
        self.env = env
        self.process = None
        self.stopped = False
        
    def run(self):
        try:
            env = os.environ.copy()
            if self.env:
                env.update(self.env)
            
            self.process = QProcess()
            if self.cwd:
                self.process.setWorkingDirectory(self.cwd)
            
            # Connect signals
            self.process.readyReadStandardOutput.connect(self._read_stdout)
            self.process.readyReadStandardError.connect(self._read_stderr)
            self.process.finished.connect(self._on_finished)
            
            # Start process
            self.process.start(self.command[0], self.command[1:])
            self.process.waitForFinished(-1)  # Wait until the process completes
            
        except Exception as e:
            self.error_received.emit(f"Error executing process: {str(e)}")
            self.process_finished.emit(1)
    
    def _read_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode('utf-8')
        self.output_received.emit(stdout)
    
    def _read_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode('utf-8')
        self.error_received.emit(stderr)
    
    def _on_finished(self, exit_code, exit_status):
        self.process_finished.emit(exit_code)
    
    def stop(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            self.process.waitForFinished(3000)  # Wait 3 seconds for termination
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.kill()  # Force kill if not terminated
        self.stopped = True

class LastFMModule:
    """Módulo para gestionar la obtención de datos de Last.fm."""
    
    def __init__(self, parent_module, config=None):
        """
        Inicializa el módulo de Last.fm.
        
        Args:
            parent_module: Módulo padre que contiene este submódulo
            config: Configuración cargada del archivo JSON
        """
        self.parent = parent_module
        self.config = config or {}
        self.ui_elements = {}
        self.capture_thread = None
        self.stats = {
            'scrobbles_totales': 0,
            'scrobbles_unicos': 0,
            'scrobbles_guardados': 0
        }
        self.logger = logging.getLogger(self.__class__.__name__)
        
        script_path = Path(PROJECT_ROOT, "db", "lastfm", "lastfm_escuchas.py")
        self.script_path = script_path

        # Cargar configuración específica para lastfm desde FLAC_config_database_creator.json si existe
        self.load_specific_config()


    def load_specific_config(self):
        """Carga configuración específica desde FLAC_config_database_creator.json si existe"""
        try:
            # Buscar en diferentes ubicaciones posibles
            possible_paths = [
                Path(PROJECT_ROOT, "config", "db_creator_config.json"),
                Path(PROJECT_ROOT, "config", "FLAC_config_database_creator.json"),
                Path(PROJECT_ROOT, "db", "FLAC_config_database_creator.json")
            ]
            
            config_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    self.logger.info(f"Encontrado archivo de configuración específico: {path}")
                    break
            
            if not config_path:
                self.logger.info("No se encontró archivo de configuración específico FLAC_config_database_creator.json")
                return
                    
            with open(config_path, 'r', encoding='utf-8') as f:
                specific_config = json.load(f)
                    
            # Extraer configuración relevante para lastfm
            # Actualizar common (claves comunes)
            if 'common' in specific_config:
                if 'common' not in self.config:
                    self.config['common'] = {}
                        
                for key, value in specific_config['common'].items():
                    if key.startswith('lastfm') or key in ['db_path']:
                        self.config['common'][key] = value
            
            # Actualizar secciones específicas
            for section in ['lastfm_escuchas', 'lastfm_info']:
                if section in specific_config:
                    self.config[section] = specific_config[section]
                        
            self.logger.info(f"Configuración específica cargada: {', '.join(self.config.keys())}")
                
        except Exception as e:
            self.logger.error(f"Error al cargar configuración específica: {e}")



    def setup_ui(self, container_widget):
        """
        Configura la interfaz de usuario con los elementos específicos de Last.fm.
        
        Args:
            container_widget: Widget contenedor donde se mostrarán los elementos
        """
        print(f"Configurando UI para LastFMModule en contenedor: {container_widget.objectName()}")
        
        # Almacenar referencias a los widgets importantes
        self._find_ui_elements(container_widget)
        
        # Inicializar labels de estadísticas si existen
        if self.ui_elements.get('scrobbles_totales_value'):
            self.ui_elements['scrobbles_totales_value'].setText("0")
        if self.ui_elements.get('scrobbles_unicos_value'):
            self.ui_elements['scrobbles_unicos_value'].setText("0")
        if self.ui_elements.get('scrobbles_guardados_value'):
            self.ui_elements['scrobbles_guardados_value'].setText("0")
        
        # Inicializar textos de botones
        if self.ui_elements.get('verificar_apikey_button'):
            self.ui_elements['verificar_apikey_button'].setText("Verificar API Key")
        if self.ui_elements.get('ejecutar_escuchas_button'):
            self.ui_elements['ejecutar_escuchas_button'].setText("Obtener Escuchas")
        if self.ui_elements.get('ejecutar_info_button'):
            self.ui_elements['ejecutar_info_button'].setText("Obtener Info")
        
        # Cargar configuración en la UI
        self._load_config_to_ui()
        
        # Conectar señales
        self._connect_signals()
        
        self.logger.info("Interfaz de Last.fm configurada correctamente")
        
    def _find_ui_elements(self, container):
        """Encuentra y almacena referencias a los elementos de la UI."""
        print("Buscando elementos UI para LastFMModule...")
        
        # Reiniciar diccionario de elementos
        self.ui_elements = {}
        
        # Recopilación de todos los widgets principales por tipo
        all_line_edits = container.findChildren(QLineEdit)
        all_checkboxes = container.findChildren(QCheckBox)
        all_buttons = container.findChildren(QPushButton)
        all_labels = container.findChildren(QLabel)
        
        # Campos de configuración básica por nombre exacto
        self.ui_elements['lastfm_user_line'] = container.findChild(QLineEdit, "lastfm_user_line")
        self.ui_elements['lastfm_apikey_line'] = container.findChild(QLineEdit, "lastfm_apikey_line")
        
        # Búsqueda por nombre parcial si no se encuentra por nombre exacto
        if not self.ui_elements['lastfm_user_line']:
            for line_edit in all_line_edits:
                obj_name = line_edit.objectName().lower()
                if 'lastfm' in obj_name and ('user' in obj_name or 'usuario' in obj_name):
                    self.ui_elements['lastfm_user_line'] = line_edit
                    print(f"✓ Encontrado lastfm_user_line por nombre parcial: {obj_name}")
                    break
                    
        if not self.ui_elements['lastfm_apikey_line']:
            for line_edit in all_line_edits:
                obj_name = line_edit.objectName().lower()
                if 'lastfm' in obj_name and ('api' in obj_name or 'key' in obj_name):
                    self.ui_elements['lastfm_apikey_line'] = line_edit
                    print(f"✓ Encontrado lastfm_apikey_line por nombre parcial: {obj_name}")
                    break
        
        # Buscar tabWidget si existe 
        self.lastfm_tab_widget = container.findChild(QTabWidget)
        if self.lastfm_tab_widget:
            print(f"✓ Encontrado tab widget: {self.lastfm_tab_widget.objectName()}")
            # Identificar pestañas por sus nombres
            if self.lastfm_tab_widget.count() >= 2:
                escuchas_tab = None
                info_tab = None
                
                for i in range(self.lastfm_tab_widget.count()):
                    tab_name = self.lastfm_tab_widget.tabText(i).lower()
                    if 'escuchas' in tab_name or 'scrobbles' in tab_name:
                        escuchas_tab = self.lastfm_tab_widget.widget(i)
                        print(f"✓ Pestaña de Escuchas identificada en índice {i}")
                    elif 'info' in tab_name:
                        info_tab = self.lastfm_tab_widget.widget(i)
                        print(f"✓ Pestaña de Info identificada en índice {i}")
                
                # Si identificamos las pestañas, buscar elementos dentro de ellas
                if escuchas_tab:
                    self._find_escuchas_elements(escuchas_tab)
                if info_tab:
                    self._find_info_elements(info_tab)
            
            # Almacenar en el elemento padre para acceso futuro
            if hasattr(self.parent, 'lastfm_tab_widget'):
                self.parent.lastfm_tab_widget = self.lastfm_tab_widget
        else:
            print("✗ No se encontró QTabWidget")
            # Si no hay tabs, buscar en todo el contenedor
            self._find_escuchas_elements(container)
            self._find_info_elements(container)
        
        # Botones de acción
        self.ui_elements['verificar_apikey_button'] = container.findChild(QPushButton, "verificar_apikey_button")
        self.ui_elements['ejecutar_escuchas_button'] = container.findChild(QPushButton, "ejecutar_escuchas_button")
        self.ui_elements['ejecutar_info_button'] = container.findChild(QPushButton, "ejecutar_info_button")
        
        # Buscar botones por texto si no se encuentran
        if not self.ui_elements['verificar_apikey_button']:
            for button in all_buttons:
                text = button.text().lower()
                if ('verif' in text and 'api' in text) or ('check' in text and 'api' in text):
                    self.ui_elements['verificar_apikey_button'] = button
                    print(f"✓ Encontrado verificar_apikey_button por texto: {button.text()}")
                    break
        
        if not self.ui_elements['ejecutar_escuchas_button']:
            for button in all_buttons:
                text = button.text().lower()
                if ('escucha' in text) or ('play' in text) or ('scrobble' in text):
                    self.ui_elements['ejecutar_escuchas_button'] = button
                    print(f"✓ Encontrado ejecutar_escuchas_button por texto: {button.text()}")
                    break
        
        if not self.ui_elements['ejecutar_info_button']:
            for button in all_buttons:
                text = button.text().lower()
                if 'info' in text or 'metadata' in text:
                    self.ui_elements['ejecutar_info_button'] = button
                    print(f"✓ Encontrado ejecutar_info_button por texto: {button.text()}")
                    break
        
        # Etiquetas de estadísticas
        self.ui_elements['scrobbles_totales_value'] = container.findChild(QLabel, "scrobbles_totales_value")
        self.ui_elements['scrobbles_unicos_value'] = container.findChild(QLabel, "scrobbles_unicos_value")
        self.ui_elements['scrobbles_guardados_value'] = container.findChild(QLabel, "scrobbles_guardados_value")
        
        # Buscar etiquetas por texto si no se encuentran
        if not self.ui_elements['scrobbles_totales_value']:
            for label in all_labels:
                if 'total' in label.text().lower() and 'scrobble' in label.text().lower():
                    self.ui_elements['scrobbles_totales_value'] = label
                    print(f"✓ Encontrado scrobbles_totales_value por texto: {label.text()}")
                    break
        
        if not self.ui_elements['scrobbles_unicos_value']:
            for label in all_labels:
                if ('unic' in label.text().lower() or 'unique' in label.text().lower()) and 'scrobble' in label.text().lower():
                    self.ui_elements['scrobbles_unicos_value'] = label
                    print(f"✓ Encontrado scrobbles_unicos_value por texto: {label.text()}")
                    break
        
        if not self.ui_elements['scrobbles_guardados_value']:
            for label in all_labels:
                if ('guard' in label.text().lower() or 'save' in label.text().lower()) and 'scrobble' in label.text().lower():
                    self.ui_elements['scrobbles_guardados_value'] = label
                    print(f"✓ Encontrado scrobbles_guardados_value por texto: {label.text()}")
                    break
                    
        # Reportar elementos encontrados
        found_count = sum(1 for element in self.ui_elements.values() if element is not None)
        print(f"Elementos encontrados: {found_count}/{len(self.ui_elements)}")
        missing_elements = [key for key, value in self.ui_elements.items() if value is None]
        if missing_elements:
            print(f"Elementos no encontrados: {', '.join(missing_elements)}")
        
    def _load_config_to_ui(self):
        """Carga la configuración del archivo JSON a la interfaz."""
        if not self.config:
            print("No hay configuración para cargar en LastFMModule")
            return
        
        print("Cargando configuración a UI en LastFMModule")
        
        # Configuración común
        common = self.config.get('common', {})
        if self.ui_elements.get('lastfm_user_line'):
            user = common.get('lastfm_user', '')
            # Verificar también lastfm_username como alternativa
            if not user and 'lastfm_username' in common:
                user = common.get('lastfm_username', '')
            print(f"Cargando usuario Last.fm: {user}")
            self.ui_elements['lastfm_user_line'].setText(user)
                    
        if self.ui_elements.get('lastfm_apikey_line'):
            api_key = common.get('lastfm_api_key', '')
            # Verificar también lastfm_apikey como alternativa
            if not api_key and 'lastfm_apikey' in common:
                api_key = common.get('lastfm_apikey', '')
            print(f"Cargando API key Last.fm: {api_key[:5]}..." if api_key else "No hay API key")
            self.ui_elements['lastfm_apikey_line'].setText(api_key)
                
        # Configuración de lastfm_escuchas
        escuchas_config = self.config.get('lastfm_escuchas', {})
        if self.ui_elements.get('force_update_check'):
            force_update = escuchas_config.get('force_update', False)
            print(f"Cargando force_update: {force_update}")
            self.ui_elements['force_update_check'].setChecked(force_update)
        
        if self.ui_elements.get('output_json_line'):
            output_json = escuchas_config.get('output_json', '')
            # Si es ruta relativa, convertirla a absoluta
            if output_json and not os.path.isabs(output_json):
                output_json = os.path.join(PROJECT_ROOT, output_json)
            print(f"Cargando output_json: {output_json}")
            self.ui_elements['output_json_line'].setText(output_json)
            
        if self.ui_elements.get('add_items_check'):
            add_items = escuchas_config.get('add_items', True)
            print(f"Cargando add_items: {add_items}")
            self.ui_elements['add_items_check'].setChecked(add_items)
            
        if self.ui_elements.get('complete_relationships_check'):
            complete_rel = escuchas_config.get('complete_relationships', True)
            print(f"Cargando complete_relationships: {complete_rel}")
            self.ui_elements['complete_relationships_check'].setChecked(complete_rel)
                
        # Configuración de lastfm_info
        info_config = self.config.get('lastfm_info', {})
        
        # Debug para identificar el problema
        print(f"Configuración lastfm_info: {info_config}")
        
        if self.ui_elements.get('info_force_update_check'):
            force_update = info_config.get('force_update', False)
            self.ui_elements['info_force_update_check'].setChecked(force_update)
            print(f"Cargando info_force_update: {force_update}")
            
        if self.ui_elements.get('info_output_json_line'):
            info_output_json = info_config.get('output_json', '')
            # Si no hay valor específico, intentar construir uno predeterminado
            if not info_output_json:
                info_output_json = os.path.join(PROJECT_ROOT, ".content", "cache", "db", "lastfm", "FLAC_info_lastfm.json")
                # Crear directorio si no existe
                os.makedirs(os.path.dirname(info_output_json), exist_ok=True)
                print(f"Usando ruta predeterminada para info_output_json: {info_output_json}")
                
            # Si es ruta relativa, convertirla a absoluta
            elif not os.path.isabs(info_output_json):
                info_output_json = str(Path(PROJECT_ROOT, info_output_json))
                
            self.ui_elements['info_output_json_line'].setText(info_output_json)
            print(f"Cargando info_output_json: {info_output_json}")
            
        if self.ui_elements.get('info_add_items_check'):
            add_items = info_config.get('add_items', True)
            self.ui_elements['info_add_items_check'].setChecked(add_items)
            print(f"Cargando info_add_items: {add_items}")
            
        if self.ui_elements.get('info_complete_relationships_check'):
            complete_rel = info_config.get('complete_relationships', True)
            self.ui_elements['info_complete_relationships_check'].setChecked(complete_rel)
            print(f"Cargando info_complete_relationships: {complete_rel}")


    def _connect_signals(self):
        """Conecta las señales de los elementos de la UI."""
        print("Conectando señales en LastFMModule...")
        
        # Botones de selección de archivos
        if self.ui_elements.get('output_json_button'):
            self.ui_elements['output_json_button'].clicked.connect(lambda: self._browse_for_json_file('output_json_line'))
            print("✓ Conectado output_json_button")
        if self.ui_elements.get('info_output_json_button'):
            self.ui_elements['info_output_json_button'].clicked.connect(lambda: self._browse_for_json_file('info_output_json_line'))
            print("✓ Conectado info_output_json_button")
                
        # Botones de acción
        if self.ui_elements.get('verificar_apikey_button'):
            self.ui_elements['verificar_apikey_button'].clicked.connect(self.verificar_apikey)
            print("✓ Conectado verificar_apikey_button")
        if self.ui_elements.get('ejecutar_escuchas_button'):
            self.ui_elements['ejecutar_escuchas_button'].clicked.connect(self.ejecutar_escuchas)
            print("✓ Conectado ejecutar_escuchas_button")
        if self.ui_elements.get('ejecutar_info_button'):
            self.ui_elements['ejecutar_info_button'].clicked.connect(self.ejecutar_info)
            print("✓ Conectado ejecutar_info_button")
            
    def _browse_for_json_file(self, target_line_edit):
        """
        Abre un diálogo para seleccionar o crear un archivo JSON.
        
        Args:
            target_line_edit: Nombre del QLineEdit donde se colocará la ruta seleccionada
        """
        if not self.ui_elements.get(target_line_edit):
            return
            
        # Obtener el directorio inicial desde el campo actual o usar .content/cache
        current_path = self.ui_elements[target_line_edit].text()
        if current_path:
            initial_dir = os.path.dirname(current_path)
        else:
            initial_dir = Path(PROJECT_ROOT, ".content", "cache")
            os.makedirs(initial_dir, exist_ok=True)
            
        # Abrir diálogo
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Seleccionar archivo JSON de salida",
            initial_dir, 
            "Archivos JSON (*.json)"
        )
        
        if file_path:
            # Asegurar extensión .json
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
                
            self.ui_elements[target_line_edit].setText(file_path)
            
    def update_config_from_ui(self):
        """Actualiza la configuración con los valores de la UI."""
        # Asegurar que existen las secciones necesarias
        if 'common' not in self.config:
            self.config['common'] = {}
        if 'lastfm_escuchas' not in self.config:
            self.config['lastfm_escuchas'] = {}
        if 'lastfm_info' not in self.config:
            self.config['lastfm_info'] = {}
                
        # Actualizar configuración común
        if self.ui_elements.get('lastfm_user_line'):
            user = self.ui_elements['lastfm_user_line'].text()
            self.config['common']['lastfm_user'] = user
            # También actualizar lastfm_username para compatibilidad
            self.config['common']['lastfm_username'] = user
                
        if self.ui_elements.get('lastfm_apikey_line'):
            api_key = self.ui_elements['lastfm_apikey_line'].text()
            self.config['common']['lastfm_api_key'] = api_key
            # También actualizar lastfm_apikey para compatibilidad
            self.config['common']['lastfm_apikey'] = api_key
                
        # Actualizar configuración de lastfm_escuchas
        if self.ui_elements.get('force_update_check'):
            self.config['lastfm_escuchas']['force_update'] = self.ui_elements['force_update_check'].isChecked()
        if self.ui_elements.get('output_json_line'):
            output_json = self.ui_elements['output_json_line'].text()
            # Convertir a ruta relativa si está dentro de PROJECT_ROOT
            if output_json.startswith(str(PROJECT_ROOT)):
                output_json = os.path.relpath(output_json, PROJECT_ROOT)
            self.config['lastfm_escuchas']['output_json'] = output_json
        if self.ui_elements.get('add_items_check'):
            self.config['lastfm_escuchas']['add_items'] = self.ui_elements['add_items_check'].isChecked()
        if self.ui_elements.get('complete_relationships_check'):
            self.config['lastfm_escuchas']['complete_relationships'] = self.ui_elements['complete_relationships_check'].isChecked()
                
        # Actualizar configuración de lastfm_info
        if self.ui_elements.get('info_force_update_check'):
            self.config['lastfm_info']['force_update'] = self.ui_elements['info_force_update_check'].isChecked()
        if self.ui_elements.get('info_output_json_line'):
            info_output_json = self.ui_elements['info_output_json_line'].text()
            # Convertir a ruta relativa si está dentro de PROJECT_ROOT
            if info_output_json.startswith(str(PROJECT_ROOT)):
                info_output_json = os.path.relpath(info_output_json, PROJECT_ROOT)
            self.config['lastfm_info']['output_json'] = info_output_json
        if self.ui_elements.get('info_add_items_check'):
            self.config['lastfm_info']['add_items'] = self.ui_elements['info_add_items_check'].isChecked()
        if self.ui_elements.get('info_complete_relationships_check'):
            self.config['lastfm_info']['complete_relationships'] = self.ui_elements['info_complete_relationships_check'].isChecked()
                
        # Asegurar que scripts_order existe
        if 'scripts_order' not in self.config:
            self.config['scripts_order'] = []
        
        # Obtener el script actual basado en la pestaña activa
        script_actual = self.get_script_name()
        
        # Filtrar scripts_order para eliminar scripts de Last.fm
        scripts_filtrados = [script for script in self.config['scripts_order'] 
                            if script != 'lastfm_escuchas' and script != 'lastfm_info']
        
        # Añadir solo el script actual
        scripts_filtrados.append(script_actual)
        self.config['scripts_order'] = scripts_filtrados
        
        return self.config


    def get_script_name(self):
        """
        Retorna el nombre del script correspondiente a la página actual.
        
        Returns:
            str: Nombre del script para añadir a scripts_order
        """
        # Obtener el índice de la pestaña activa
        current_tab = self.get_active_tab_index()
        
        if current_tab == 0:  # Pestaña de Escuchas
            return "lastfm_escuchas"
        elif current_tab == 1:  # Pestaña de Info
            return "lastfm_info"
        
        # Por defecto, devolver escuchas
        return "lastfm_escuchas"

    def validate(self):
        """
        Valida que los campos necesarios estén llenos.
        
        Returns:
            bool: True si todos los campos obligatorios están llenos, False en caso contrario
        """
        # Actualizar configuración primero
        self.update_config_from_ui()
        
        # Verificar campos obligatorios
        missing_fields = []
        
        if not self.config['common'].get('lastfm_user'):
            missing_fields.append("Usuario de Last.fm")
        if not self.config['common'].get('lastfm_api_key'):
            missing_fields.append("API Key de Last.fm")
        if not self.config.get('db_path') and not self.config['common'].get('db_path'):
            missing_fields.append("Ruta de la base de datos")
            
        if missing_fields:
            QMessageBox.warning(
                self.parent, 
                "Campos obligatorios", 
                f"Los siguientes campos son obligatorios:\n- {'\n- '.join(missing_fields)}"
            )
            return False
            
        return True
        
    def verificar_apikey(self):
        """Verifica si la API key de Last.fm es válida."""
        # Actualizar configuración primero
        self.update_config_from_ui()
        
        # Verificar que tenemos los datos necesarios
        api_key = self.config['common'].get('lastfm_api_key')
        if not api_key:
            QMessageBox.warning(self.parent, "Error", "Debe ingresar una API Key de Last.fm")
            return
            
        # Preparar comando para verificar API key
        script_path = Path(PROJECT_ROOT, "db", "lastfm", "lastfm_escuchas.py")
        if not os.path.exists(script_path):
            QMessageBox.warning(self.parent, "Error", f"Script no encontrado: {script_path}")
            return
            
        # Crear comando con solo los parámetros necesarios para verificar la API key
        command = [
            sys.executable, 
            script_path, 
            "--lastfm_api_key", api_key
        ]
        
        # Iniciar captura de salida
        if self.capture_thread and self.capture_thread.isRunning():
            self.capture_thread.stop()
            
        # Limpiar área de texto de salida
        if hasattr(self.parent, 'output_text'):
            self.parent.output_text.clear()
            self.parent.output_text.append(f"Verificando API Key de Last.fm...\n")
            
        # Crear y arrancar hilo de captura
        self.capture_thread = OutputCaptureThread(command, cwd=str(PROJECT_ROOT))
        self.capture_thread.output_received.connect(self.parse_output)
        self.capture_thread.error_received.connect(self.parse_error)
        self.capture_thread.process_finished.connect(self.verify_process_finished)
        self.capture_thread.start()
        
    def ejecutar_escuchas(self):
        """Ejecuta el script lastfm_escuchas.py con la configuración actual."""
        if not self.validate():
            return
            
        # Preparar comando
        script_path = Path(PROJECT_ROOT, "db", "lastfm", "lastfm_escuchas.py")
        if not os.path.exists(script_path):
            QMessageBox.warning(self.parent, "Error", f"Script no encontrado: {script_path}")
            return
            
        # Actualizar configuración primero
        self.update_config_from_ui()
            
        # Construir argumentos
        args = [
            "--lastfm_user", self.config['common']['lastfm_user'],
            "--lastfm_api_key", self.config['common']['lastfm_api_key']
        ]
        
        # Obtener el path de la base de datos
        db_path = self.config.get('db_path', self.config['common'].get('db_path'))
        if not db_path:
            QMessageBox.warning(self.parent, "Error", "No se ha especificado la ruta a la base de datos")
            return
            
        # Añadir path de base de datos a los argumentos
        args.extend(["--db_path", str(db_path)])  # Convertir a string
        
        # Argumentos opcionales
        if self.config['lastfm_escuchas'].get('force_update'):
            args.append("--force_update")
            
        if self.config['lastfm_escuchas'].get('output_json'):
            output_json = self.config['lastfm_escuchas']['output_json']
            # Si es ruta relativa, convertirla a absoluta
            if not os.path.isabs(output_json):
                output_json = str(Path(PROJECT_ROOT, output_json))  # Convertir a string
            args.extend(["--output_json", output_json])
            
        # Crear directorio para output_json si no existe
        if self.config['lastfm_escuchas'].get('output_json'):
            output_dir = os.path.dirname(output_json)
            os.makedirs(output_dir, exist_ok=True)
            
        # Iniciar ejecución
        self._ejecutar_script(self.script_path, args)

    # Modificación de ejecutar_info
    def ejecutar_info(self):
        """Ejecuta el script lastfm_info.py con la configuración actual."""
        if not self.validate():
            return
            
        # Preparar comando
        script_path = Path(PROJECT_ROOT, "db", "lastfm_info.py")
        if not os.path.exists(script_path):
            # Intentar buscar en otras ubicaciones comunes
            alt_paths = [
                Path(PROJECT_ROOT, "db", "lastfm", "lastfm_info.py"),
                Path(PROJECT_ROOT, "lastfm_info.py")
            ]
            
            found = False
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    script_path = alt_path
                    found = True
                    break
                    
            if not found:
                QMessageBox.warning(self.parent, "Error", f"Script no encontrado: lastfm_info.py")
                return
                
        # Actualizar configuración primero
        self.update_config_from_ui()
            
        # Construir argumentos
        args = [
            "--lastfm_api_key", self.config['common']['lastfm_api_key']
        ]
        
        # Obtener el path de la base de datos
        db_path = self.config.get('db_path', self.config['common'].get('db_path'))
        if not db_path:
            QMessageBox.warning(self.parent, "Error", "No se ha especificado la ruta a la base de datos")
            return
            
        # Añadir path de base de datos a los argumentos
        args.extend(["--db_path", str(db_path)])  # Convertir a string
        
        # Argumentos opcionales específicos para lastfm_info
        if self.config['lastfm_info'].get('cache_dir'):
            cache_dir = self.config['lastfm_info']['cache_dir']
            if not os.path.isabs(cache_dir):
                cache_dir = str(Path(PROJECT_ROOT, cache_dir))  # Convertir a string
            args.extend(["--cache_dir", cache_dir])
            os.makedirs(cache_dir, exist_ok=True)
        else:
            # Usar un directorio de caché por defecto
            cache_dir = str(Path(PROJECT_ROOT, ".content", "cache", "lastfm"))
            os.makedirs(cache_dir, exist_ok=True)
            args.extend(["--cache_dir", cache_dir])
            
        # Agregar límites si están definidos
        if self.config['lastfm_info'].get('limite_artistas'):
            args.extend(["--limite_artistas", str(self.config['lastfm_info']['limite_artistas'])])
        else:
            # Valor predeterminado
            args.extend(["--limite_artistas", "50"])
            
        if self.config['lastfm_info'].get('limite_albumes'):
            args.extend(["--limite_albumes", str(self.config['lastfm_info']['limite_albumes'])])
        else:
            # Valor predeterminado
            args.extend(["--limite_albumes", "50"])
            
        if self.config['lastfm_info'].get('limite_canciones'):
            args.extend(["--limite_canciones", str(self.config['lastfm_info']['limite_canciones'])])
        else:
            # Valor predeterminado
            args.extend(["--limite_canciones", "50"])
        
        # Iniciar ejecución con la ruta del script completa
        self._ejecutar_script(str(script_path), args)
        
    def _ejecutar_script(self, script_name, args):
        """
        Ejecuta un script Python con los argumentos especificados.
        
        Args:
            script_name: Nombre del script a ejecutar
            args: Lista de argumentos para el script
        """
        # Convertir todos los argumentos a strings para evitar problemas con objetos Path
        args = [str(arg) for arg in args]
        
        script_path = os.path.join(PROJECT_ROOT, "db", script_name)
        command = [sys.executable, str(script_path)] + args
        
        # Detener hilo anterior si está corriendo
        if self.capture_thread and self.capture_thread.isRunning():
            self.capture_thread.stop()
            
        # Limpiar área de texto de salida si existe
        if hasattr(self.parent, 'output_text'):
            output_text = self.parent.output_text
            command_str = f"Ejecutando: {' '.join(command)}\n"
            
            # Determinar el tipo de widget y usar el método apropiado
            if hasattr(output_text, 'append'):
                # QTextEdit
                output_text.clear()
                output_text.append(command_str)
            elif hasattr(output_text, 'appendPlainText'):
                # QPlainTextEdit
                output_text.clear()
                output_text.appendPlainText(command_str)
            elif hasattr(output_text, 'setText'):
                # QLabel u otro widget con setText
                output_text.setText(command_str)
            else:
                # Fallback: intentar imprimir
                print(command_str)
        else:
            print(f"Ejecutando: {' '.join(command)}")
            
        # Crear y arrancar hilo de captura
        self.capture_thread = OutputCaptureThread(command, cwd=str(PROJECT_ROOT))
        self.capture_thread.output_received.connect(self.parse_output)
        self.capture_thread.error_received.connect(self.parse_error)
        self.capture_thread.process_finished.connect(self.script_process_finished)
        self.capture_thread.start()
        
    def parse_output(self, output):
        """
        Procesa la salida del script en ejecución.
        
        Args:
            output: Texto de salida del script
        """
        # Imprimir en área de texto si existe
        if hasattr(self.parent, 'output_text'):
            output_text = self.parent.output_text
            
            # Determinar el tipo de widget y usar el método apropiado
            if hasattr(output_text, 'append'):
                # QTextEdit
                output_text.append(output)
            elif hasattr(output_text, 'appendPlainText'):
                # QPlainTextEdit
                output_text.appendPlainText(output)
            elif hasattr(output_text, 'setText'):
                # QLabel u otro widget con setText
                current_text = output_text.text()
                output_text.setText(current_text + output)
        else:
            print(output)
            
        # Actualizar estadísticas si contiene información relevante
        if "Obtenidos" in output and "scrobbles en total" in output:
            try:
                parts = output.strip().split()
                self.stats['scrobbles_totales'] = int(parts[1])
                self._update_stats_ui()
            except (ValueError, IndexError):
                pass
                
        if "Procesamiento completado:" in output:
            try:
                # Formato: "Procesamiento completado: X scrobbles agrupados en Y entradas únicas"
                parts = output.strip().split(":")
                if len(parts) > 1:
                    unique_part = parts[1].strip().split()
                    self.stats['scrobbles_unicos'] = int(unique_part[-3])
                    self._update_stats_ui()
            except (ValueError, IndexError):
                pass
                
        if "Guardados en base de datos:" in output:
            try:
                # Formato: "Guardados en base de datos: X nuevos, Y actualizados"
                parts = output.strip().split(":")
                if len(parts) > 1:
                    saved_part = parts[1].strip().split()
                    self.stats['scrobbles_guardados'] = int(saved_part[0]) + int(saved_part[-2])
                    self._update_stats_ui()
            except (ValueError, IndexError):
                pass

    def parse_error(self, error):
        """
        Procesa los errores del script en ejecución.
        
        Args:
            error: Texto de error del script
        """
        # Imprimir en área de texto con formato de error
        if hasattr(self.parent, 'output_text'):
            output_text = self.parent.output_text
            error_formatted = f"ERROR: {error}"
            
            # Determinar el tipo de widget y usar el método apropiado
            if hasattr(output_text, 'append'):
                # QTextEdit que acepta HTML
                if hasattr(output_text, 'setHtml') or hasattr(output_text, 'insertHtml'):
                    output_text.append(f"<span style='color:red'>{error}</span>")
                else:
                    output_text.append(error_formatted)
            elif hasattr(output_text, 'appendPlainText'):
                # QPlainTextEdit
                output_text.appendPlainText(error_formatted)
            elif hasattr(output_text, 'setText'):
                # QLabel u otro widget con setText
                current_text = output_text.text()
                output_text.setText(current_text + "\n" + error_formatted)
        else:
            print(f"ERROR: {error}")

    def verify_process_finished(self, exit_code):
        """
        Maneja la finalización del proceso de verificación de API key.
        
        Args:
            exit_code: Código de salida del proceso
        """
        # Verificar si la salida de texto contiene información sobre la validez de la API key
        if hasattr(self.parent, 'output_text'):
            output_text = self.parent.output_text.toPlainText().lower()
            
            if "api key inválida" in output_text or "error al verificar api key" in output_text:
                QMessageBox.critical(self.parent, "Error", "La API Key de Last.fm no es válida")
            elif "api key parece válida" in output_text:
                QMessageBox.information(self.parent, "Éxito", "La API Key de Last.fm es válida")
            else:
                if exit_code == 0:
                    QMessageBox.information(self.parent, "Éxito", "La verificación se completó sin errores")
                else:
                    QMessageBox.warning(self.parent, "Advertencia", "No se pudo determinar la validez de la API Key")
                
    def script_process_finished(self, exit_code):
        """
        Maneja la finalización del proceso de ejecución de script.
        
        Args:
            exit_code: Código de salida del proceso
        """
        # Preparar mensaje de finalización
        if exit_code == 0:
            message = "\nScript completado correctamente"
            if hasattr(self.parent, 'output_text'):
                output_text = self.parent.output_text
                
                # Determinar el tipo de widget y usar el método apropiado
                if hasattr(output_text, 'append'):
                    # QTextEdit que acepta HTML
                    if hasattr(output_text, 'setHtml') or hasattr(output_text, 'insertHtml'):
                        output_text.append(f"<span style='color:green'>{message}</span>")
                    else:
                        output_text.append(message)
                elif hasattr(output_text, 'appendPlainText'):
                    # QPlainTextEdit
                    output_text.appendPlainText(message)
                elif hasattr(output_text, 'setText'):
                    # QLabel u otro widget con setText
                    current_text = output_text.text()
                    output_text.setText(current_text + "\n" + message)
            else:
                print(message)
                    
            # Mostrar estadísticas finales
            mensaje_dialog = f"Proceso completado con éxito.\n\n"
            mensaje_dialog += f"Scrobbles totales: {self.stats['scrobbles_totales']}\n"
            mensaje_dialog += f"Scrobbles únicos: {self.stats['scrobbles_unicos']}\n"
            mensaje_dialog += f"Scrobbles guardados: {self.stats['scrobbles_guardados']}"
            
            QMessageBox.information(self.parent, "Éxito", mensaje_dialog)
        else:
            message = f"\nScript terminado con código de error: {exit_code}"
            if hasattr(self.parent, 'output_text'):
                output_text = self.parent.output_text
                
                # Determinar el tipo de widget y usar el método apropiado
                if hasattr(output_text, 'append'):
                    # QTextEdit que acepta HTML
                    if hasattr(output_text, 'setHtml') or hasattr(output_text, 'insertHtml'):
                        output_text.append(f"<span style='color:red'>{message}</span>")
                    else:
                        output_text.append(message)
                elif hasattr(output_text, 'appendPlainText'):
                    # QPlainTextEdit
                    output_text.appendPlainText(message)
                elif hasattr(output_text, 'setText'):
                    # QLabel u otro widget con setText
                    current_text = output_text.text()
                    output_text.setText(current_text + "\n" + message)
            else:
                print(message)
                
            QMessageBox.warning(self.parent, "Error", f"El script terminó con código de error: {exit_code}")
            
    def _update_stats_ui(self):
        """Actualiza los widgets de estadísticas con los valores actuales."""
        if self.ui_elements.get('scrobbles_totales_value'):
            self.ui_elements['scrobbles_totales_value'].setText(str(self.stats['scrobbles_totales']))
        if self.ui_elements.get('scrobbles_unicos_value'):
            self.ui_elements['scrobbles_unicos_value'].setText(str(self.stats['scrobbles_unicos']))
        if self.ui_elements.get('scrobbles_guardados_value'):
            self.ui_elements['scrobbles_guardados_value'].setText(str(self.stats['scrobbles_guardados']))
            
        # Forzar actualización inmediata de la UI
        QApplication.processEvents()

    def get_active_tab_index(self):
        """
        Obtiene el índice de la pestaña activa del TabWidget de Last.fm.
        
        Returns:
            int: Índice de la pestaña activa o 0 si no se puede determinar
        """
        # Primero usar la referencia almacenada en el constructor
        if hasattr(self, 'lastfm_tab_widget') and self.lastfm_tab_widget:
            return self.lastfm_tab_widget.currentIndex()
                
        # Si no está directamente, buscar entre los elementos hijos
        if hasattr(self.parent, 'findChild'):
            tab_widget = self.parent.findChild(QTabWidget)
            if tab_widget:
                return tab_widget.currentIndex()
        
        # Si no se encuentra, intentar buscar en los widgets del container
        for name, widget in self.ui_elements.items():
            if isinstance(widget, QTabWidget):
                return widget.currentIndex()
        
        # Por defecto, asumimos la primera pestaña
        return 0

    def load_config(self, config):
        """Carga configuración desde un diccionario."""
        self.config = config
        
        # Si la UI ya está inicializada, cargar los valores
        if self.ui_elements:
            self._load_config_to_ui()


    def _find_escuchas_elements(self, container):
        """Busca elementos específicos de la pestaña de Escuchas"""
        self.ui_elements['force_update_check'] = container.findChild(QCheckBox, "force_update_check")
        self.ui_elements['output_json_line'] = container.findChild(QLineEdit, "output_json_line")
        self.ui_elements['output_json_button'] = container.findChild(QPushButton, "output_json_button")
        self.ui_elements['add_items_check'] = container.findChild(QCheckBox, "add_items_check")
        self.ui_elements['complete_relationships_check'] = container.findChild(QCheckBox, "complete_relationships_check")
        
        # Buscar por texto o nombre parcial si no se encuentra por nombre exacto
        all_checkboxes = container.findChildren(QCheckBox)
        all_line_edits = container.findChildren(QLineEdit)
        all_buttons = container.findChildren(QPushButton)
        
        if not self.ui_elements['force_update_check']:
            for checkbox in all_checkboxes:
                text = checkbox.text().lower()
                obj_name = checkbox.objectName().lower()
                if ('force' in text or 'forzar' in text) and ('update' in text or 'actualiz' in text):
                    self.ui_elements['force_update_check'] = checkbox
                    print(f"✓ Encontrado force_update_check por texto: {checkbox.text()}")
                    break
                elif 'force' in obj_name and 'update' in obj_name:
                    self.ui_elements['force_update_check'] = checkbox
                    print(f"✓ Encontrado force_update_check por nombre parcial: {obj_name}")
                    break
        
        if not self.ui_elements['output_json_line']:
            for line_edit in all_line_edits:
                obj_name = line_edit.objectName().lower()
                if ('output' in obj_name or 'salida' in obj_name) and 'json' in obj_name:
                    self.ui_elements['output_json_line'] = line_edit
                    print(f"✓ Encontrado output_json_line por nombre parcial: {obj_name}")
                    break
        
        if not self.ui_elements['output_json_button']:
            # Buscar botón cerca del line edit
            if self.ui_elements['output_json_line']:
                for button in all_buttons:
                    if button.parentWidget() == self.ui_elements['output_json_line'].parentWidget():
                        self.ui_elements['output_json_button'] = button
                        print(f"✓ Encontrado output_json_button por parentesco")
                        break
        
        if not self.ui_elements['add_items_check']:
            for checkbox in all_checkboxes:
                text = checkbox.text().lower()
                obj_name = checkbox.objectName().lower()
                if ('add' in text or 'añadir' in text) and ('item' in text or 'element' in text):
                    self.ui_elements['add_items_check'] = checkbox
                    print(f"✓ Encontrado add_items_check por texto: {checkbox.text()}")
                    break
                elif ('add' in obj_name or 'añadir' in obj_name) and 'item' in obj_name:
                    self.ui_elements['add_items_check'] = checkbox
                    print(f"✓ Encontrado add_items_check por nombre parcial: {obj_name}")
                    break
        
        if not self.ui_elements['complete_relationships_check']:
            for checkbox in all_checkboxes:
                text = checkbox.text().lower()
                obj_name = checkbox.objectName().lower()
                if ('complet' in text or 'relation' in text) or ('complet' in obj_name and 'relation' in obj_name):
                    self.ui_elements['complete_relationships_check'] = checkbox
                    print(f"✓ Encontrado complete_relationships_check por texto/nombre: {checkbox.text()}")
                    break

    def _find_info_elements(self, container):
        """Busca elementos específicos de la pestaña de Info"""
        self.ui_elements['info_force_update_check'] = container.findChild(QCheckBox, "info_force_update_check")
        self.ui_elements['info_output_json_line'] = container.findChild(QLineEdit, "info_output_json_line")
        self.ui_elements['info_output_json_button'] = container.findChild(QPushButton, "info_output_json_button")
        self.ui_elements['info_add_items_check'] = container.findChild(QCheckBox, "info_add_items_check")
        self.ui_elements['info_complete_relationships_check'] = container.findChild(QCheckBox, "info_complete_relationships_check")
        
        # Buscar por texto o nombre parcial si no se encuentra por nombre exacto
        all_checkboxes = container.findChildren(QCheckBox)
        all_line_edits = container.findChildren(QLineEdit)
        all_buttons = container.findChildren(QPushButton)
        
        # Fuerza bruta: si hay pocos elementos, asignarlos directamente por orden
        if len(all_checkboxes) <= 3 and not any([
                self.ui_elements['info_force_update_check'],
                self.ui_elements['info_add_items_check'],
                self.ui_elements['info_complete_relationships_check']]):
            
            print("Pocos checkboxes encontrados, asignando por orden...")
            for i, checkbox in enumerate(all_checkboxes):
                if i == 0:
                    self.ui_elements['info_force_update_check'] = checkbox
                    print(f"✓ Asignado info_force_update_check por orden: {checkbox.text()}")
                elif i == 1:
                    self.ui_elements['info_add_items_check'] = checkbox
                    print(f"✓ Asignado info_add_items_check por orden: {checkbox.text()}")
                elif i == 2:
                    self.ui_elements['info_complete_relationships_check'] = checkbox
                    print(f"✓ Asignado info_complete_relationships_check por orden: {checkbox.text()}")
        
        if len(all_line_edits) == 1 and not self.ui_elements['info_output_json_line']:
            self.ui_elements['info_output_json_line'] = all_line_edits[0]
            print(f"✓ Asignado info_output_json_line por ser único: {all_line_edits[0].objectName()}")
        
        if len(all_buttons) == 1 and not self.ui_elements['info_output_json_button']:
            self.ui_elements['info_output_json_button'] = all_buttons[0]
            print(f"✓ Asignado info_output_json_button por ser único: {all_buttons[0].text()}")
        
        # Búsqueda por keywords si la asignación directa no funcionó
        if not self.ui_elements['info_force_update_check']:
            for checkbox in all_checkboxes:
                text = checkbox.text().lower()
                obj_name = checkbox.objectName().lower()
                if ('force' in text or 'forzar' in text) and ('update' in text or 'actualiz' in text):
                    self.ui_elements['info_force_update_check'] = checkbox
                    print(f"✓ Encontrado info_force_update_check por texto: {checkbox.text()}")
                    break
                elif 'force' in obj_name and 'update' in obj_name and 'info' in obj_name:
                    self.ui_elements['info_force_update_check'] = checkbox
                    print(f"✓ Encontrado info_force_update_check por nombre parcial: {obj_name}")
                    break
        
        if not self.ui_elements['info_output_json_line']:
            for line_edit in all_line_edits:
                obj_name = line_edit.objectName().lower()
                if (('output' in obj_name or 'salida' in obj_name) and 'json' in obj_name and 'info' in obj_name):
                    self.ui_elements['info_output_json_line'] = line_edit
                    print(f"✓ Encontrado info_output_json_line por nombre parcial: {obj_name}")
                    break
        
        if not self.ui_elements['info_output_json_button']:
            # Buscar botón cerca del line edit
            if self.ui_elements['info_output_json_line']:
                for button in all_buttons:
                    if button.parentWidget() == self.ui_elements['info_output_json_line'].parentWidget():
                        self.ui_elements['info_output_json_button'] = button
                        print(f"✓ Encontrado info_output_json_button por parentesco")
                        break