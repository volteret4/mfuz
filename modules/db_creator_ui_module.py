import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QStackedWidget, QProgressBar,QTextEdit,
    QFileDialog, QMessageBox, QPlainTextEdit, QTabWidget
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QProcess, QSize
from PyQt6.QtGui import QIcon
from base_module import BaseModule, PROJECT_ROOT
import resources_rc

# Import submodules
from modules.submodules.db.db_music_path_module import DBMusicPathModule
from modules.submodules.db.lastfm_module import LastFMModule


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


class DBCreatorModule(BaseModule):
    """Módulo para crear y gestionar bases de datos de música."""
    
    def __init__(self, parent=None, **kwargs):
        # Initialize attributes before calling super().__init__
        self.current_index = 0
        self.total_steps = 6  # Total number of steps in the wizard
        self.submodules = []
        
        # Check if config file exists and is valid
        self.config_file = kwargs.get('config_file', '')
        
        # Validate and load config file
        if self.config_file:
            if not os.path.isabs(self.config_file):
                # Convert relative path to absolute
                self.config_file = os.path.join(PROJECT_ROOT, self.config_file)
                
            if not os.path.exists(self.config_file):
                # Create default config file if it doesn't exist
                self.create_default_config()
        else:
            # Default config file path
            self.config_file = os.path.join(PROJECT_ROOT, "config", "db_creator_config.json")
            if not os.path.exists(self.config_file):
                self.create_default_config()
                
        self.config_data = {}
        
        # Initialize submodules
        self.init_submodules()
        
        # IMPORTANTE: Llama a super().__init__ ANTES de llamar a cualquier método que use self.logger
        super().__init__(parent, **kwargs)
        
        # Cargar configuración después de super().__init__ para tener acceso a self.logger
        self.load_config(self.config_file)
   
    def create_default_config(self):
        """Create a default configuration file."""
        default_config = {
            "scripts_order": [
                "db_musica_path"
            ],
            "common": {
                "db_path": "",
                "lastfm_api_key": "",
                "lastfm_user": "",
                "spotify_client_id": "",
                "spotify_client_secret": ""
            },
            "db_musica_path": {
                "root_path": "",
                "force_update": False,
                "update_replay_gain": False,
                "update_schema": False,
                "update_bitrates": False,
                "quick_scan": False,
                "optimize": False
            }
        }
        
        # Ensure directory exists
        config_dir = os.path.dirname(self.config_file)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            
        # Write default config
        try:
            with open(self.config_file, 'w') as f:
                if self.config_file.endswith('.json'):
                    json.dump(default_config, f, indent=2)
                elif self.config_file.endswith(('.yml', '.yaml')):
                    import yaml
                    yaml.dump(default_config, f, default_flow_style=False)
                else:
                    # Default to JSON
                    json.dump(default_config, f, indent=2)
            
            self.logger.info(f"Created default configuration at {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Error creating default configuration: {str(e)}")
            
        # Use default config
        self.config_data = default_config

    def init_ui(self):
        """Initialize the user interface."""
        # Try to load from UI file first
        ui_file = Path(f"{PROJECT_ROOT}/ui/base_datos/db_creator_base.ui")

        required_widgets = [
            "stackedWidget", "progressBar", "anterior_button", "siguiente_button", "output_text"
        ]
        
        if self.load_ui_file(str(ui_file), required_widgets):
            # Asegurarse de que tenemos referencias a los widgets necesarios
            if not hasattr(self, 'stackedWidget') or not self.stackedWidget:
                self.stackedWidget = self.findChild(QStackedWidget, "stackedWidget")
            if not hasattr(self, 'anterior_button') or not self.anterior_button:
                self.anterior_button = self.findChild(QPushButton, "anterior_button")
            if not hasattr(self, 'siguiente_button') or not self.siguiente_button:
                self.siguiente_button = self.findChild(QPushButton, "siguiente_button")
            if not hasattr(self, 'progressBar') or not self.progressBar:
                self.progressBar = self.findChild(QProgressBar, "progressBar")
            if not hasattr(self, 'output_text') or not self.output_text:
                self.output_text = self.findChild(QTextEdit, "output_text")
            if not hasattr(self, 'scrollArea_output_text') or not self.scrollArea_output_text:
                self.scrollArea_output_text = self.findChild(QTextEdit, "scrollArea_output_text")

            # Verificación de widgets encontrados
            print(f"StackedWidget encontrado: {bool(self.stackedWidget)}")
            print(f"Botón anterior encontrado: {bool(self.anterior_button)}")
            print(f"Botón siguiente encontrado: {bool(self.siguiente_button)}")
            print(f"Output text encontrado: {bool(self.output_text)}")
                
            self.setup_connections()
        else:
            self._create_ui_manually()
        
        # IMPORTANTE: Asegurarse de que siempre empiece en la primera página (índice 0)
        self.current_index = 0
        self.stackedWidget.setCurrentIndex(0)
        
        # Debug del StackedWidget
        self.debug_stacked_widget()
        
        # Setup the progress bar
        self.progressBar.setRange(0, self.total_steps)
        self.progressBar.setValue(self.current_index + 1)
        
        # Show/hide navigation buttons based on current page
        self.update_navigation_buttons()
        
        # Initialize the first submodule (sin crear widgets duplicados)
        if self.submodules and self.stackedWidget.count() > 0:
            current_widget = self.stackedWidget.widget(0)
            self.submodules[0].setup_ui(current_widget)
                
    def load_config_to_submodules(self):
        """Carga la configuración a todos los submódulos."""
        if not self.submodules:
            return
            
        print("Cargando configuración en submódulos...")
        for i, submodule in enumerate(self.submodules):
            if hasattr(submodule, 'config'):
                # Actualizar la configuración del submódulo
                submodule.config = self.config_data
                print(f"Configuración actualizada para submódulo {i}: {type(submodule).__name__}")
                
                # Si el submódulo tiene un método load_config, llamarlo
                if hasattr(submodule, 'load_config'):
                    submodule.load_config(self.config_data)
                    print(f"Método load_config llamado para submódulo {i}")


    def debug_stacked_widget(self):
        """Método para diagnosticar problemas con el StackedWidget."""
        print(f"\n--- Diagnóstico del StackedWidget ---")
        print(f"Total de páginas: {self.stackedWidget.count()}")
        print(f"Página actual: {self.stackedWidget.currentIndex()}")
        print(f"Current_index: {self.current_index}")
        
        for i in range(self.stackedWidget.count()):
            widget = self.stackedWidget.widget(i)
            print(f"Página {i}: {widget.objectName() if widget else 'None'}")
            
        print(f"Total de submódulos: {len(self.submodules)}")
        print("--- Fin del diagnóstico ---\n")


    def _create_ui_manually(self):
        """Create UI manually if loading from file fails."""
        main_layout = QVBoxLayout(self)
        self.verticalLayout = main_layout
        
        # Create stacked widget
        self.stackedWidget = QStackedWidget()
        
        # Create first page (DB Path)
        db_path_page = QWidget()
        db_path_layout = QVBoxLayout(db_path_page)
        
        # Title
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        self.titulo_label = QLabel("Creación de la base de datos")
        title_layout.addWidget(self.titulo_label)
        db_path_layout.addWidget(title_widget)
        
        # Path selector
        path_widget = QWidget()
        path_layout = QHBoxLayout(path_widget)
        self.rutaSelector_label = QLabel("Introduce la ruta a tu música")
        self.rutaSelector_line = QLineEdit()
        self.rutaSelector_line.setMinimumHeight(30)
        browse_button = QPushButton()
        browse_button.setIcon(QIcon(":/services/folder"))
        browse_button.setIconSize(QSize(30, 30))
        path_layout.addWidget(self.rutaSelector_label)
        path_layout.addWidget(self.rutaSelector_line)
        path_layout.addWidget(browse_button)
        db_path_layout.addWidget(path_widget)
        
        # Table for music paths
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        self.rutasMusica_tabla = QTableWidget()
        self.rutasMusica_tabla.setColumnCount(3)
        self.rutasMusica_tabla.setHorizontalHeaderLabels(["Ruta", "Carpetas", "Archivos reconocidos"])
        table_layout.addWidget(self.rutasMusica_tabla)
        db_path_layout.addWidget(table_widget)
        
        # Add page to stacked widget
        self.stackedWidget.addWidget(db_path_page)
        
        # Add stacked widget to main layout
        main_layout.addWidget(self.stackedWidget)
        
        # Progress widget
        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        self.anterior_button = QPushButton()
        self.anterior_button.setIcon(QIcon(":/services/b_prev"))
        self.anterior_button.setIconSize(QSize(30, 30))
        self.progressBar = QProgressBar()
        self.progressBar.setMinimumHeight(30)
        self.siguiente_button = QPushButton()
        self.siguiente_button.setIcon(QIcon(":/services/b_ff"))
        self.siguiente_button.setIconSize(QSize(30, 30))
        progress_layout.addWidget(self.anterior_button)
        progress_layout.addWidget(self.progressBar)
        progress_layout.addWidget(self.siguiente_button)
        main_layout.addWidget(progress_widget)
        
    def setup_connections(self):
        """Setup signal connections."""
        # Navigation buttons
        self.anterior_button.clicked.connect(self.go_to_previous_page)
        self.siguiente_button.clicked.connect(self.go_to_next_page)

        # Verificación de las conexiones
        print(f"Botón anterior conectado: {bool(self.anterior_button.receivers(self.anterior_button.clicked))}")
        print(f"Botón siguiente conectado: {bool(self.siguiente_button.receivers(self.siguiente_button.clicked))}")

        # Añadir la conexión para ocultar/mostrar el log al hacer clic en la progressBar
        self.progressBar.mousePressEvent = self.toggle_log_visibility

        # File browser button (assuming it's the third pushbutton)
        file_browser_buttons = self.findChildren(QPushButton)
        for button in file_browser_buttons:
            if button.icon().availableSizes() and button != self.anterior_button and button != self.siguiente_button:
                button.clicked.connect(self.browse_for_folder)
                break
                
    def init_submodules(self):
        """Initialize submodules for each step of the database creation process."""
        # Asegurarse de que config_data está inicializado
        if not hasattr(self, 'config_data') or not self.config_data:
            self.config_data = {}
            
        # First module: DB Music Path
        music_path_module = DBMusicPathModule(self, config=self.config_data)
        self.submodules.append(music_path_module)
        
        # Second module: LastFM
        lastfm_module = LastFMModule(self, config=self.config_data)
        self.submodules.append(lastfm_module)
        
        # Cargar archivo de configuración si existe
        if hasattr(self, 'config_file') and self.config_file:
            success = self.load_config(self.config_file)
            if success:
                print(f"Configuración cargada correctamente desde {self.config_file}")
                # Actualizar configuración en submódulos
                self.load_config_to_submodules()
            else:
                print(f"Error al cargar configuración inicial desde {self.config_file}")
        
    def browse_for_folder(self):
        """Open a file dialog to select music folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de música", 
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.rutaSelector_line.setText(folder)
            # Update the current submodule with the new path
            if self.submodules and self.current_index < len(self.submodules):
                self.submodules[self.current_index].set_music_path(folder)


    def toggle_log_visibility(self, event):
        """Alterna la visibilidad del panel de log cuando se hace clic en la barra de progreso."""
        # Primero pasamos el evento al controlador original para mantener su funcionalidad
        QProgressBar.mousePressEvent(self.progressBar, event)
        
        # Luego alternamos la visibilidad del panel de log
        if hasattr(self, 'scrollArea_output_text') and self.scrollArea_output_text:
            if self.scrollArea_output_text.isVisible():
                self.scrollArea_output_text.hide()
            else:
                self.scrollArea_output_text.show()

    def go_to_next_page(self):
        """Navigate to the next page."""
        # Depuración
        print(f"Intentando ir a la siguiente página: actual={self.current_index}, total={self.stackedWidget.count()}")
        
        # Validar página actual
        if self.submodules and self.current_index < len(self.submodules):
            if hasattr(self.submodules[self.current_index], 'validate'):
                if not self.submodules[self.current_index].validate():
                    return
                    
            # Guardar la configuración actualizada
            if hasattr(self.submodules[self.current_index], 'update_config_from_ui'):
                self.config_data = self.submodules[self.current_index].update_config_from_ui()
                # Opcionalmente guardar en archivo
                self.save_config()
        
        # Verificar si podemos avanzar
        if self.current_index < min(self.total_steps - 1, self.stackedWidget.count() - 1):
            self.current_index += 1
            print(f"Cambiando a índice: {self.current_index}")
            self.stackedWidget.setCurrentIndex(self.current_index)
            
            # Configurar la UI para este submódulo si es necesario
            if self.current_index < len(self.submodules):
                current_widget = self.stackedWidget.widget(self.current_index)
                print(f"Configurando UI para la página {self.current_index}, widget: {current_widget.objectName()}")
                self.submodules[self.current_index].setup_ui(current_widget)
                    
            self.progressBar.setValue(self.current_index + 1)
            self.update_navigation_buttons()
        else:
            print(f"No se puede avanzar más: current_index={self.current_index}, stackedWidget.count()={self.stackedWidget.count()}")

    # Reemplazar el método go_to_previous_page en DBCreatorModule
    def go_to_previous_page(self):
        """Navigate to the previous page."""
        # Guardar los cambios de la página actual
        if self.submodules and self.current_index < len(self.submodules):
            if hasattr(self.submodules[self.current_index], 'update_config_from_ui'):
                self.config_data = self.submodules[self.current_index].update_config_from_ui()
                # Opcionalmente guardar en archivo
                self.save_config()
                
        if self.current_index > 0:
            self.current_index -= 1
            self.stackedWidget.setCurrentIndex(self.current_index)
            self.progressBar.setValue(self.current_index + 1)
            self.update_navigation_buttons()
            
    def update_navigation_buttons(self):
        """Update the state of navigation buttons based on current page."""
        self.anterior_button.setEnabled(self.current_index > 0)
        self.siguiente_button.setEnabled(self.current_index < self.total_steps - 1)
        
    def load_config(self, config_file):
        """Load configuration from a file."""
        try:
            # Asegurarse de que config_file sea una cadena de texto, no un objeto Path
            if isinstance(config_file, Path):
                config_file = str(config_file)
                    
            print(f"Intentando cargar configuración desde archivo: {config_file}")
            
            if not os.path.exists(config_file):
                print(f"ADVERTENCIA: El archivo de configuración {config_file} no existe")
                return False
                    
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Contenido del archivo leído, tamaño: {len(content)} bytes")
                
                if config_file.endswith('.json'):
                    self.config_data = json.loads(content)
                    print(f"JSON cargado correctamente. Claves principales: {list(self.config_data.keys())}")
                    
                    # Mostrar algunos valores clave para depuración
                    if 'db_musica_path' in self.config_data:
                        db_path_config = self.config_data['db_musica_path']
                        print(f"db_musica_path opciones: {list(db_path_config.keys())}")
                        for k, v in db_path_config.items():
                            if k in ['force_update', 'update_replay_gain', 'update_schema', 
                                    'optimize', 'update_bitrates', 'quick_scan']:
                                print(f"  {k} = {v}")
                elif config_file.endswith(('.yml', '.yaml')):
                    import yaml
                    self.config_data = yaml.safe_load(content)
                    print(f"YAML cargado correctamente. Claves principales: {list(self.config_data.keys())}")
                else:
                    print(f"ADVERTENCIA: Formato de archivo no soportado: {config_file}")
                    return False
                    
                # Actualizar configuración en submodules
                self.load_config_to_submodules()
                    
                return True
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error cargando archivo de configuración: {str(e)}")
            else:
                print(f"Error cargando archivo de configuración: {str(e)}")
                import traceback
                traceback.print_exc()
            return False
            
    def save_config(self, config_file=None):
        """Save current configuration to a file."""
        if not config_file:
            config_file = self.config_file
            
        if not config_file:
            self.logger.error("No config file specified")
            return False
            
        try:
            with open(config_file, 'w') as f:
                if config_file.endswith('.json'):
                    json.dump(self.config_data, f, indent=2)
                elif config_file.endswith(('.yml', '.yaml')):
                    import yaml
                    yaml.dump(self.config_data, f, default_flow_style=False)
                else:
                    self.logger.error(f"Unsupported config file format: {config_file}")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error saving config file: {str(e)}")
            return False
            
    def run_db_script(self, script_name, args=None):
        """Run a database script and capture its output."""
        if args is None:
            args = []
        
        # Convertir todos los argumentos a strings (para evitar problemas con objetos Path)
        args = [str(arg) for arg in args]
            
        # Primero buscar en la raíz del proyecto
        script_path = Path(PROJECT_ROOT, f"{script_name}.py")
            
        # Si no existe ahí, intentar buscar en el directorio db/
        if not os.path.exists(script_path):
            script_path = Path(PROJECT_ROOT, "db", f"{script_name}.py")
            
        if not os.path.exists(script_path):
            self.output_text.append(f"Error: Script {script_name} no encontrado en {PROJECT_ROOT} ni en {Path(PROJECT_ROOT, 'db')}")
            return False
            
        # Prepare command - Convertir script_path a string
        command = [sys.executable, str(script_path)] + args
        
        # Clear output area
        self.output_text.clear()
        self.output_text.append(f"Ejecutando: {' '.join(command)}\n")
        
        # Create and start capture thread
        self.capture_thread = OutputCaptureThread(command, cwd=str(PROJECT_ROOT))
        self.capture_thread.output_received.connect(self.handle_script_output)
        self.capture_thread.error_received.connect(self.handle_script_error)
        self.capture_thread.process_finished.connect(self.handle_script_finished)
        self.capture_thread.start()
        
        return True
        
    def handle_script_output(self, output):
        """Handle script standard output."""
        self.output_text.append(output)
        # Parse output and update UI as needed
        if self.submodules and self.current_index < len(self.submodules):
            self.submodules[self.current_index].parse_output(output)
            
    def handle_script_error(self, error):
        """Handle script error output."""
        self.output_text.append(f"<span style='color:red'>{error}</span>")
        
    def handle_script_finished(self, exit_code):
        """Handle script completion."""
        if exit_code == 0:
            self.output_text.append("\n<span style='color:green'>Script completado correctamente</span>")
        else:
            self.output_text.append(f"\n<span style='color:red'>Script terminado con código de error: {exit_code}</span>")
            
        # Notify current submodule
        if self.submodules and self.current_index < len(self.submodules):
            self.submodules[self.current_index].script_finished(exit_code)