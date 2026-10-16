import os
import sys
import json
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QTableWidget, QTableWidgetItem, QCheckBox, QComboBox,
                            QLineEdit, QLabel, QFileDialog, QMessageBox, QDialog,
                            QTextEdit, QDialogButtonBox, QHeaderView, QRadioButton,
                            QButtonGroup, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QProcess
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6 import uic
from base_module import BaseModule, PROJECT_ROOT
import traceback
from modules.submodules.db.script_descriptions import SCRIPT_DESCRIPTIONS

class ExecutionConfigDialog(QDialog):
    """Diálogo para configurar cómo ejecutar el db_creator"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.execution_mode = "normal"
        self.selected_session = ""
        self.selected_terminal = ""
        self.init_ui()
        self.detect_available_options()

    def init_ui(self):
        """Inicializar la interfaz del diálogo"""
        self.setWindowTitle("Configuración de Ejecución")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # Título
        title_label = QLabel("Selecciona cómo ejecutar el script:")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title_label)

        # Grupo de botones de radio
        self.button_group = QButtonGroup(self)

        # Opción Normal
        self.normal_radio = QRadioButton("Normal (En segundo plano)")
        self.normal_radio.setToolTip("Ejecutar en segundo plano, mostrando log en la UI")
        self.normal_radio.setChecked(True)
        self.button_group.addButton(self.normal_radio)
        layout.addWidget(self.normal_radio)

        # Opción tmux
        tmux_group = QGroupBox("tmux")
        tmux_layout = QVBoxLayout(tmux_group)

        self.tmux_radio = QRadioButton("Ejecutar en sesión tmux")
        self.tmux_radio.setToolTip("Adjuntar a una sesión tmux existente o crear nueva")
        self.button_group.addButton(self.tmux_radio)
        tmux_layout.addWidget(self.tmux_radio)

        self.tmux_combo = QComboBox()
        self.tmux_combo.setEnabled(False)
        tmux_layout.addWidget(self.tmux_combo)

        layout.addWidget(tmux_group)

        # Opción zellij
        zellij_group = QGroupBox("zellij")
        zellij_layout = QVBoxLayout(zellij_group)

        self.zellij_radio = QRadioButton("Ejecutar en sesión zellij")
        self.zellij_radio.setToolTip("Adjuntar a una sesión zellij existente o crear nueva")
        self.button_group.addButton(self.zellij_radio)
        zellij_layout.addWidget(self.zellij_radio)

        self.zellij_combo = QComboBox()
        self.zellij_combo.setEnabled(False)
        zellij_layout.addWidget(self.zellij_combo)

        layout.addWidget(zellij_group)

        # Opción terminal
        terminal_group = QGroupBox("Terminal")
        terminal_layout = QVBoxLayout(terminal_group)

        self.terminal_radio = QRadioButton("Ejecutar en terminal externo")
        self.terminal_radio.setToolTip("Abrir en una nueva ventana de terminal")
        self.button_group.addButton(self.terminal_radio)
        terminal_layout.addWidget(self.terminal_radio)

        self.terminal_combo = QComboBox()
        self.terminal_combo.setEnabled(False)
        terminal_layout.addWidget(self.terminal_combo)

        layout.addWidget(terminal_group)

        # Botones
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept_config)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # Conectar señales
        self.normal_radio.toggled.connect(self.on_mode_changed)
        self.tmux_radio.toggled.connect(self.on_mode_changed)
        self.zellij_radio.toggled.connect(self.on_mode_changed)
        self.terminal_radio.toggled.connect(self.on_mode_changed)

    def detect_available_options(self):
        """Detectar opciones disponibles en el sistema"""
        # Detectar sesiones tmux
        try:
            result = subprocess.run(['tmux', 'list-sessions'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                sessions = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        session_name = line.split(':')[0]
                        sessions.append(session_name)

                self.tmux_combo.addItem("Nueva sesión")
                self.tmux_combo.addItems(sessions)
            else:
                self.tmux_radio.setEnabled(False)
                self.tmux_combo.addItem("tmux no disponible")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.tmux_radio.setEnabled(False)
            self.tmux_combo.addItem("tmux no instalado")

        # Detectar sesiones zellij
        try:
            result = subprocess.run(['zellij', 'list-sessions'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                sessions = []
                for line in result.stdout.strip().split('\n'):
                    if line and not line.startswith('No active'):
                        # Zellij format puede variar, ajustar según necesidad
                        session_name = line.strip()
                        sessions.append(session_name)

                self.zellij_combo.addItem("Nueva sesión")
                if sessions:
                    self.zellij_combo.addItems(sessions)
            else:
                self.zellij_radio.setEnabled(False)
                self.zellij_combo.addItem("zellij no disponible")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.zellij_radio.setEnabled(False)
            self.zellij_combo.addItem("zellij no instalado")

        # Detectar terminales disponibles
        terminals = self.detect_terminals()
        if terminals:
            self.terminal_combo.addItems(terminals)
        else:
            self.terminal_radio.setEnabled(False)
            self.terminal_combo.addItem("No hay terminales disponibles")

    def detect_terminals(self):
        """Detectar terminales disponibles en el sistema"""
        # Lista común de terminales
        common_terminals = [
            ('gnome-terminal', 'GNOME Terminal'),
            ('konsole', 'Konsole'),
            ('xfce4-terminal', 'XFCE Terminal'),
            ('mate-terminal', 'MATE Terminal'),
            ('lxterminal', 'LXTerminal'),
            ('terminator', 'Terminator'),
            ('kitty', 'Kitty'),
            ('alacritty', 'Alacritty'),
            ('urxvt', 'URxvt'),
            ('xterm', 'XTerm'),
            ('tilix', 'Tilix'),
            ('st', 'Simple Terminal')
        ]

        available = []
        for cmd, name in common_terminals:
            try:
                subprocess.run(['which', cmd],
                             capture_output=True, check=True, timeout=2)
                available.append(f"{name} ({cmd})")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return available

    def on_mode_changed(self):
        """Manejar cambio en el modo de ejecución"""
        # Habilitar/deshabilitar combos según la selección
        self.tmux_combo.setEnabled(self.tmux_radio.isChecked() and self.tmux_radio.isEnabled())
        self.zellij_combo.setEnabled(self.zellij_radio.isChecked() and self.zellij_radio.isEnabled())
        self.terminal_combo.setEnabled(self.terminal_radio.isChecked() and self.terminal_radio.isEnabled())

    def accept_config(self):
        """Validar y aceptar configuración"""
        if self.normal_radio.isChecked():
            self.execution_mode = "normal"
        elif self.tmux_radio.isChecked():
            if not self.tmux_radio.isEnabled():
                QMessageBox.warning(self, "Error", "tmux no está disponible en el sistema")
                return
            self.execution_mode = "tmux"
            self.selected_session = self.tmux_combo.currentText()
        elif self.zellij_radio.isChecked():
            if not self.zellij_radio.isEnabled():
                QMessageBox.warning(self, "Error", "zellij no está disponible en el sistema")
                return
            self.execution_mode = "zellij"
            self.selected_session = self.zellij_combo.currentText()
        elif self.terminal_radio.isChecked():
            if not self.terminal_radio.isEnabled():
                QMessageBox.warning(self, "Error", "No hay terminales disponibles")
                return
            self.execution_mode = "terminal"
            self.selected_terminal = self.terminal_combo.currentText()

        self.accept()

    def get_execution_config(self):
        """Obtener configuración de ejecución"""
        return {
            'mode': self.execution_mode,
            'session': self.selected_session,
            'terminal': self.selected_terminal
        }

class ConfigEditorDialog(QDialog):
    """Diálogo para editar configuraciones JSON de scripts específicos"""

    def __init__(self, parent=None, script_name="", config_data=None):
        super().__init__(parent)
        self.script_name = script_name
        self.config_data = config_data or {}
        self.init_ui()
        self.load_config()

    def init_ui(self):
        """Inicializar la interfaz del diálogo"""
        self.setWindowTitle(f"Configuración de {self.script_name}")
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # Etiqueta explicativa
        info_label = QLabel(f"Editar configuración para el script: {self.script_name}")
        info_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(info_label)

        # Editor de texto
        self.text_editor = QTextEdit()
        self.text_editor.setFont(QFont("Courier", 10))
        layout.addWidget(self.text_editor)

        # Botones
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept_changes)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def load_config(self):
        """Cargar configuración en el editor"""
        try:
            config_text = json.dumps(self.config_data, indent=2, ensure_ascii=False)
            self.text_editor.setPlainText(config_text)
        except Exception as e:
            self.text_editor.setPlainText(f"Error cargando configuración: {e}")

    def accept_changes(self):
        """Validar y aceptar cambios"""
        try:
            # Validar JSON
            config_text = self.text_editor.toPlainText()
            parsed_config = json.loads(config_text)
            self.config_data = parsed_config
            self.accept()
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "Error JSON", f"JSON inválido: {e}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error validando configuración: {e}")

    def get_config(self):
        """Obtener configuración editada"""
        return self.config_data


class DbCreatorWorker(QThread):
    """Worker para ejecutar db_creator.py en segundo plano"""

    log_message = pyqtSignal(str)
    finished_signal = pyqtSignal(int)  # Exit code

    def __init__(self, config_file_path, execution_config=None):
        super().__init__()
        self.config_file_path = config_file_path
        self.execution_config = execution_config or {'mode': 'normal'}
        self.process = None

    def run(self):
        """Ejecutar db_creator.py según la configuración"""
        try:
            python_executable = sys.executable
            db_creator_path = PROJECT_ROOT / "db_creator.py"

            base_cmd = [python_executable, str(db_creator_path), "--config", str(self.config_file_path)]

            mode = self.execution_config.get('mode', 'normal')

            if mode == 'normal':
                self._execute_normal(base_cmd)
            elif mode == 'tmux':
                self._execute_tmux(base_cmd)
            elif mode == 'zellij':
                self._execute_zellij(base_cmd)
            elif mode == 'terminal':
                self._execute_terminal(base_cmd)
            else:
                self._execute_normal(base_cmd)

        except Exception as e:
            self.log_message.emit(f"Error ejecutando db_creator: {e}")
            self.finished_signal.emit(-1)

    def _execute_normal(self, cmd):
        """Ejecutar en modo normal (segundo plano con log en UI)"""
        self.log_message.emit(f"Ejecutando: {' '.join(cmd)}")

        # Usar subprocess con PIPE para capturar output
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=str(PROJECT_ROOT)
        )

        # Leer output línea por línea
        for line in iter(self.process.stdout.readline, ''):
            if line:
                self.log_message.emit(line.strip())

        # Esperar a que termine y obtener código de salida
        exit_code = self.process.wait()
        self.finished_signal.emit(exit_code)

    def _execute_tmux(self, cmd):
        """Ejecutar en sesión tmux"""
        session = self.execution_config.get('session', 'Nueva sesión')

        if session == 'Nueva sesión':
            session_name = 'db_creator_session'
            tmux_cmd = ['tmux', 'new-session', '-d', '-s', session_name]
            tmux_cmd.extend(['--'] + cmd)
        else:
            tmux_cmd = ['tmux', 'send-keys', '-t', session]
            tmux_cmd.extend([' '.join(cmd), 'Enter'])

        self.log_message.emit(f"Ejecutando en tmux: {' '.join(tmux_cmd)}")

        try:
            result = subprocess.run(tmux_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_message.emit(f"Script ejecutado en sesión tmux: {session}")
                self.finished_signal.emit(0)
            else:
                self.log_message.emit(f"Error ejecutando en tmux: {result.stderr}")
                self.finished_signal.emit(result.returncode)
        except subprocess.TimeoutExpired:
            self.log_message.emit("Timeout ejecutando en tmux")
            self.finished_signal.emit(-1)

    def _execute_zellij(self, cmd):
        """Ejecutar en sesión zellij"""
        session = self.execution_config.get('session', 'Nueva sesión')

        if session == 'Nueva sesión':
            session_name = 'db_creator_session'
            zellij_cmd = ['zellij', '--session', session_name, '--', 'bash', '-c', ' '.join(cmd)]
        else:
            # Para sesiones existentes, zellij maneja esto diferente
            zellij_cmd = ['zellij', 'attach', session, '--', 'bash', '-c', ' '.join(cmd)]

        self.log_message.emit(f"Ejecutando en zellij: {' '.join(zellij_cmd)}")

        try:
            result = subprocess.run(zellij_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_message.emit(f"Script ejecutado en sesión zellij: {session}")
                self.finished_signal.emit(0)
            else:
                self.log_message.emit(f"Error ejecutando en zellij: {result.stderr}")
                self.finished_signal.emit(result.returncode)
        except subprocess.TimeoutExpired:
            self.log_message.emit("Timeout ejecutando en zellij")
            self.finished_signal.emit(-1)

    def _execute_terminal(self, cmd):
        """Ejecutar en terminal externo"""
        terminal_info = self.execution_config.get('terminal', '')

        # Extraer el comando del terminal del formato "Name (command)"
        if '(' in terminal_info and ')' in terminal_info:
            terminal_cmd = terminal_info.split('(')[1].split(')')[0]
        else:
            terminal_cmd = 'xterm'  # fallback

        # Construir comando según el terminal
        if terminal_cmd in ['gnome-terminal', 'mate-terminal']:
            terminal_full_cmd = [terminal_cmd, '--', 'bash', '-c', f"{' '.join(cmd)}; read -p 'Presiona Enter para cerrar...'"]
        elif terminal_cmd == 'konsole':
            terminal_full_cmd = [terminal_cmd, '-e', 'bash', '-c', f"{' '.join(cmd)}; read -p 'Presiona Enter para cerrar...'"]
        elif terminal_cmd in ['xfce4-terminal', 'lxterminal']:
            terminal_full_cmd = [terminal_cmd, '-e', f"bash -c \"{' '.join(cmd)}; read -p 'Presiona Enter para cerrar...'\""]
        elif terminal_cmd in ['kitty', 'alacritty']:
            terminal_full_cmd = [terminal_cmd, '-e', 'bash', '-c', f"{' '.join(cmd)}; read -p 'Presiona Enter para cerrar...'"]
        else:
            # Fallback genérico
            terminal_full_cmd = [terminal_cmd, '-e', f"bash -c \"{' '.join(cmd)}; read -p 'Presiona Enter para cerrar...'\""]

        self.log_message.emit(f"Ejecutando en terminal: {' '.join(terminal_full_cmd)}")

        try:
            # Para terminales externos, no esperamos la salida
            subprocess.Popen(terminal_full_cmd, cwd=str(PROJECT_ROOT))
            self.log_message.emit(f"Script ejecutado en terminal externo: {terminal_cmd}")
            self.finished_signal.emit(0)
        except Exception as e:
            self.log_message.emit(f"Error ejecutando en terminal: {e}")
            self.finished_signal.emit(-1)

    def stop(self):
        """Detener la ejecución"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.log_message.emit("Proceso detenido por el usuario")


class DbCreatorUIModule(BaseModule):
    """Módulo para gestionar la configuración del db_creator"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Obtener configuración desde los argumentos del módulo
        self.module_config = kwargs.get('args', {})

        # Rutas de configuración
        self.config_dir = PROJECT_ROOT / "config" / "ui_db_creator"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Archivo temporal para la configuración que se está editando
        self.temp_config_file = self.config_dir / "temp_config_database_creator.json"

        # Configuración actual - usar la del config.yml o default
        default_config_path = str(PROJECT_ROOT / "config" / "config_database_creator.json")
        self.current_config_path = self.module_config.get('config_file', default_config_path)

        # Si la ruta es relativa, hacerla absoluta respecto a PROJECT_ROOT
        if not Path(self.current_config_path).is_absolute():
            self.current_config_path = str(PROJECT_ROOT / self.current_config_path)

        self.current_config = {}
        self.scripts_data = []

        # Worker para ejecutar db_creator
        self.worker = None

        # Configuración de ejecución
        self.execution_config = {'mode': 'normal'}

        # Cargar configuración inicial
        self.load_database_config()

        # Poblar tabla
        self.populate_scripts_table()

        # Conectar señales
        self.connect_signals()

        # Deshabilitar ordenamiento inicialmente para establecer orden por defecto
        self.tabla_scripts.setSortingEnabled(False)

        # Inicializar en la página de tabla (índice 0)
        self.stackedWidget.setCurrentIndex(0)

        # Agregar botones adicionales si no existen en el UI
        self.setup_additional_buttons()

    def init_ui(self):
        """Inicializar la UI desde el archivo .ui"""
        ui_file = Path(PROJECT_ROOT, "ui", "db_creator", "db_creator_module.ui")
        try:
            uic.loadUi(ui_file, self)
            return True
        except Exception as e:
            print(f"Error cargando UI: {e}")
            traceback.print_exc()
            return False

    def connect_signals(self):
        """Conectar señales de la UI"""
        # Botón editar archivo de configuración
        self.action_editar.clicked.connect(self.select_config_file)

        # Botón actualizar (ejecutar db_creator)
        self.action_update.clicked.connect(self.show_execution_dialog)

        # Combobox de perfiles
        self.perfil_combobox.currentTextChanged.connect(self.on_profile_changed)

        # Botón de configuración de ejecución (si existe)
        if hasattr(self, 'action_config_update'):
            self.action_config_update.clicked.connect(self.show_execution_dialog)

    def update_config_file_setting(self, new_config_path):
        """Actualizar la configuración del archivo en el config.yml del módulo"""
        # Esta función debería ser llamada por el sistema de módulos padre
        # para actualizar la configuración en el archivo config.yml
        # Por ahora, solo actualizamos internamente
        self.current_config_path = new_config_path
        if hasattr(self, 'parent_app') and hasattr(self.parent_app, 'update_module_config'):
            # Si existe un método en la app principal para actualizar configuración
            self.parent_app.update_module_config(self.__class__.__name__, 'config_file', new_config_path)

    def load_database_config(self):
        """Cargar configuración de la base de datos"""
        try:
            config_path = Path(self.current_config_path)
            if not config_path.exists():
                QMessageBox.warning(
                    self,
                    "Archivo no encontrado",
                    f"No se encuentra el archivo: {config_path}"
                )
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                self.current_config = json.load(f)

            # Actualizar UI
            self.config_file_line_edit.setText(str(config_path))

            # Extraer información de scripts
            self.extract_scripts_data()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error cargando configuración de base de datos: {e}"
            )

    def setup_additional_buttons(self):
        """Configurar botones adicionales que pueden no estar en el UI"""
        # Buscar el layout del widget_5 donde están los botones
        if hasattr(self, 'widget_5'):
            layout = self.widget_5.layout()
            if layout:
                # Agregar botón para configuración de ejecución si no existe
                if not hasattr(self, 'action_config_update'):
                    self.action_config_update = QPushButton("⚙️ Configurar Ejecución")
                    self.action_config_update.setToolTip("Configurar cómo ejecutar el script")
                    layout.insertWidget(0, self.action_config_update)
                    self.action_config_update.clicked.connect(self.show_execution_dialog)

                # Agregar botón para cambiar entre páginas si no existe
                if not hasattr(self, 'action_toggle_view'):
                    self.action_toggle_view = QPushButton("📋 Ver Tabla")
                    self.action_toggle_view.setToolTip("Cambiar entre tabla y log")
                    layout.insertWidget(1, self.action_toggle_view)
                    self.action_toggle_view.clicked.connect(self.toggle_view)

    def toggle_view(self):
        """Cambiar entre la vista de tabla y la vista de log"""
        current_index = self.stackedWidget.currentIndex()
        if current_index == 0:  # Tabla -> Log
            self.stackedWidget.setCurrentIndex(1)
            self.action_toggle_view.setText("📋 Ver Tabla")
            self.action_toggle_view.setToolTip("Volver a la vista de tabla")
        else:  # Log -> Tabla
            self.stackedWidget.setCurrentIndex(0)
            self.action_toggle_view.setText("📃 Ver Log")
            self.action_toggle_view.setToolTip("Ver log de ejecución")

    def extract_scripts_data(self):
        """Extraer datos de scripts desde la configuración"""
        self.scripts_data = []

        # Scripts en scripts_order
        scripts_order = self.current_config.get('scripts_order', [])

        # Todos los scripts disponibles en la configuración
        all_scripts = set()
        for key in self.current_config.keys():
            if key not in ['scripts_order', 'common']:
                all_scripts.add(key)

        # También agregar scripts que están en scripts_order pero no tienen configuración
        for script in scripts_order:
            all_scripts.add(script)

        # Crear orden por defecto: primero los que están en scripts_order en ese orden,
        # luego el resto ordenados alfabéticamente
        ordered_scripts = []

        # Añadir scripts en el orden de scripts_order
        for script in scripts_order:
            if script in all_scripts:
                ordered_scripts.append(script)
                all_scripts.remove(script)

        # Añadir el resto ordenados alfabéticamente
        ordered_scripts.extend(sorted(all_scripts))

        # Crear datos para cada script manteniendo el orden por defecto
        for index, script in enumerate(ordered_scripts):
            script_data = {
                'script': script,
                'basename': Path(script).name if '/' in script else script,
                'enabled': script in scripts_order,
                'config': self.current_config.get(script, {}),
                'path': script,
                'definition': self.get_script_definition(script),
                'default_order': index  # Añadir índice para mantener orden por defecto
            }
            self.scripts_data.append(script_data)

    def get_script_definition(self, script_name):
        """Obtener definición/descripción del script"""
        return SCRIPT_DESCRIPTIONS.get(script_name, 'Script personalizado')

    def populate_scripts_table(self):
        """Poblar la tabla de scripts"""
        # IMPORTANT: disable sorting BEFORE inserting items.
        # With sorting enabled, setItem() on the sort column triggers an immediate
        # re-sort, which moves QTableWidgetItems to new visual rows while
        # setCellWidget() widgets stay at their original positions — causing a
        # permanent widget/item mismatch.
        self.tabla_scripts.setSortingEnabled(False)
        self.tabla_scripts.setRowCount(len(self.scripts_data))
        self.tabla_scripts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        for row, script_data in enumerate(self.scripts_data):
            script_key = script_data['script']

            # Columna 0: checkbox (widget) + item for sort value
            # Lambdas capture script_key — stays correct even after sorting
            checkbox = QCheckBox()
            checkbox.setChecked(script_data['enabled'])
            checkbox.stateChanged.connect(
                lambda state, key=script_key: self.on_script_enabled_changed(key, state)
            )
            self.tabla_scripts.setCellWidget(row, 0, checkbox)

            uso_item = QTableWidgetItem()
            uso_item.setData(Qt.ItemDataRole.UserRole, script_data['default_order'])
            uso_item.setData(Qt.ItemDataRole.DisplayRole, 0 if script_data['enabled'] else 1)
            self.tabla_scripts.setItem(row, 0, uso_item)

            # Columna 1: nombre
            script_item = QTableWidgetItem(script_data['basename'])
            script_item.setData(Qt.ItemDataRole.UserRole, script_data['default_order'])
            script_item.setToolTip(script_data['definition'])
            self.tabla_scripts.setItem(row, 1, script_item)

            # Columna 2: descripción
            def_item = QTableWidgetItem(script_data['definition'])
            def_item.setData(Qt.ItemDataRole.UserRole, script_data['default_order'])
            def_item.setToolTip(script_data['definition'])
            self.tabla_scripts.setItem(row, 2, def_item)

            # Columna 3: botón ajustes (widget) + item for sort value
            settings_btn = QPushButton("🔧")
            settings_btn.setFlat(True)
            settings_btn.setToolTip(script_data['definition'])
            settings_btn.clicked.connect(
                lambda checked, key=script_key: self.configure_script(key)
            )
            self.tabla_scripts.setCellWidget(row, 3, settings_btn)

            ajustes_item = QTableWidgetItem()
            ajustes_item.setData(Qt.ItemDataRole.UserRole, script_data['default_order'])
            ajustes_item.setData(Qt.ItemDataRole.DisplayRole, script_data['default_order'])
            self.tabla_scripts.setItem(row, 3, ajustes_item)

            # Columna 4: path completo — fuente de verdad tras el sort
            path_item = QTableWidgetItem(script_data['path'])
            path_item.setData(Qt.ItemDataRole.UserRole, script_data['default_order'])
            self.tabla_scripts.setItem(row, 4, path_item)

        # Re-connect sort signal (avoid duplicates)
        try:
            self.tabla_scripts.horizontalHeader().sectionClicked.disconnect(self.on_header_clicked)
        except RuntimeError:
            pass
        self.tabla_scripts.horizontalHeader().sectionClicked.connect(self.on_header_clicked)

        # Enable sorting, apply default sort, then fix cell-widget positions
        self.tabla_scripts.setSortingEnabled(True)
        self.tabla_scripts.sortItems(1, Qt.SortOrder.AscendingOrder)
        self.restore_widgets_after_sort()

    def on_header_clicked(self, logical_index):
        """Manejar clic en encabezado para reordenar widgets"""
        # QTimer lets Qt finish reordering before we re-sync the cell widgets
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.restore_widgets_after_sort)

    def restore_widgets_after_sort(self):
        """Recrear cell-widgets tras ordenar, usando la columna path (col 4) como fuente de verdad.

        QTableWidgetItems se reordenan con sortItems(); los cell-widgets (setCellWidget) NO.
        Por eso los recreamos usando el script_key que está en col 4 (sí se mueve con la fila).
        """
        # Build a fast lookup: script_key -> script_data
        key_to_data = {sd['script']: sd for sd in self.scripts_data}

        try:
            for row in range(self.tabla_scripts.rowCount()):
                path_item = self.tabla_scripts.item(row, 4)
                if not path_item:
                    continue
                script_key = path_item.text()
                sd = key_to_data.get(script_key)
                if not sd:
                    continue

                # Checkbox
                checkbox = QCheckBox()
                checkbox.blockSignals(True)
                checkbox.setChecked(sd['enabled'])
                checkbox.blockSignals(False)
                checkbox.stateChanged.connect(
                    lambda state, key=script_key: self.on_script_enabled_changed(key, state)
                )
                self.tabla_scripts.setCellWidget(row, 0, checkbox)

                # Settings button
                settings_btn = QPushButton("🔧")
                settings_btn.setFlat(True)
                settings_btn.setToolTip(sd['definition'])
                settings_btn.clicked.connect(
                    lambda checked, key=script_key: self.configure_script(key)
                )
                self.tabla_scripts.setCellWidget(row, 3, settings_btn)

        except Exception as e:
            print(f"Error restaurando widgets después de ordenar: {e}")

    def on_script_enabled_changed(self, script_key, state):
        """Manejar cambio en el estado de habilitación de un script"""
        for sd in self.scripts_data:
            if sd['script'] == script_key:
                sd['enabled'] = (state == Qt.CheckState.Checked.value)
                break
        else:
            return

        self.update_temp_config()

        # Actualizar valor de ordenamiento en la columna "Uso" para la fila correcta
        for table_row in range(self.tabla_scripts.rowCount()):
            path_item = self.tabla_scripts.item(table_row, 4)
            if path_item and path_item.text() == script_key:
                uso_item = self.tabla_scripts.item(table_row, 0)
                if uso_item:
                    enabled = next((sd['enabled'] for sd in self.scripts_data if sd['script'] == script_key), False)
                    uso_item.setData(Qt.ItemDataRole.DisplayRole, 0 if enabled else 1)
                break

    def configure_script(self, script_key):
        """Configurar script específico"""
        sd = next((d for d in self.scripts_data if d['script'] == script_key), None)
        if not sd:
            return

        dialog = ConfigEditorDialog(self, sd['script'], sd['config'].copy())

        if dialog.exec() == QDialog.DialogCode.Accepted:
            sd['config'] = dialog.get_config()
            self.update_temp_config()
            QMessageBox.information(
                self,
                "Configuración actualizada",
                f"Configuración del script '{sd['script']}' actualizada correctamente."
            )

    def update_temp_config(self):
        """Actualizar archivo de configuración temporal"""
        try:
            # Crear nueva configuración
            new_config = self.current_config.copy()

            # Actualizar scripts_order con scripts habilitados
            enabled_scripts = [
                script_data['script']
                for script_data in self.scripts_data
                if script_data['enabled']
            ]
            new_config['scripts_order'] = enabled_scripts

            # Actualizar configuraciones individuales de scripts
            for script_data in self.scripts_data:
                if script_data['config']:
                    new_config[script_data['script']] = script_data['config']

            # Guardar archivo temporal
            with open(self.temp_config_file, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error actualizando configuración temporal: {e}")

    def select_config_file(self):
        """Seleccionar nuevo archivo de configuración"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de configuración",
            str(PROJECT_ROOT / "config"),
            "Archivos JSON (*.json);;Todos los archivos (*.*)"
        )

        if file_path:
            try:
                # Validar que el archivo es un JSON válido
                with open(file_path, 'r', encoding='utf-8') as f:
                    test_config = json.load(f)

                # Actualizar configuración
                self.current_config_path = file_path
                self.update_config_file_setting(file_path)
                self.load_database_config()
                self.tabla_scripts.setSortingEnabled(False)  # Deshabilitar durante actualización
                self.populate_scripts_table()

                QMessageBox.information(
                    self,
                    "Archivo cargado",
                    f"Archivo de configuración cargado: {Path(file_path).name}\n\n" +
                    "Nota: Para que este cambio persista, actualiza el archivo config.yml " +
                    "de la aplicación con la nueva ruta."
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error cargando archivo de configuración: {e}"
                )

    def show_execution_dialog(self):
        """Mostrar diálogo de configuración de ejecución"""
        dialog = ExecutionConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.execution_config = dialog.get_execution_config()
            self.execute_db_creator()

    def execute_db_creator(self):
        """Ejecutar db_creator.py con la configuración actual"""
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Proceso en curso", "Ya hay un proceso ejecutándose.")
            return

        # Actualizar configuración temporal
        self.update_temp_config()

        if not self.temp_config_file.exists():
            QMessageBox.warning(self, "Error", "No se pudo crear el archivo de configuración temporal.")
            return

        # Confirmar ejecución
        enabled_scripts = [s['script'] for s in self.scripts_data if s['enabled']]
        if not enabled_scripts:
            QMessageBox.warning(self, "Advertencia", "No hay scripts seleccionados para ejecutar.")
            return

        mode_text = {
            'normal': 'segundo plano',
            'tmux': f"sesión tmux ({self.execution_config.get('session', 'nueva')})",
            'zellij': f"sesión zellij ({self.execution_config.get('session', 'nueva')})",
            'terminal': f"terminal externo ({self.execution_config.get('terminal', 'desconocido')})"
        }

        current_mode = mode_text.get(self.execution_config.get('mode', 'normal'), 'segundo plano')

        reply = QMessageBox.question(
            self,
            "Confirmar ejecución",
            f"¿Ejecutar db_creator en {current_mode} con {len(enabled_scripts)} scripts seleccionados?\n\n" +
            "\n".join(enabled_scripts),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Si el modo es normal, cambiar a la página de log
        if self.execution_config.get('mode', 'normal') == 'normal':
            self.stackedWidget.setCurrentIndex(1)
            self.log_textEdit.clear()

        # Crear worker y ejecutar
        self.worker = DbCreatorWorker(str(self.temp_config_file), self.execution_config)
        self.worker.log_message.connect(self.log_message)
        self.worker.finished_signal.connect(self.on_db_creator_finished)

        # Solo cambiar botón para modo normal
        if self.execution_config.get('mode', 'normal') == 'normal':
            self.action_update.setText("Detener")
            self.action_update.clicked.disconnect()
            self.action_update.clicked.connect(self.stop_db_creator)

        self.worker.start()
        self.log_message("Iniciando ejecución de db_creator...")

    def stop_db_creator(self):
        """Detener ejecución de db_creator"""
        if self.worker:
            self.worker.stop()
            self.worker.wait(5000)  # Esperar máximo 5 segundos

    def on_db_creator_finished(self, exit_code):
        """Manejar finalización de db_creator"""
        # Solo restaurar botón si estamos en modo normal
        if self.execution_config.get('mode', 'normal') == 'normal':
            self.action_update.setText("Actualizar")
            self.action_update.clicked.disconnect()
            self.action_update.clicked.connect(self.show_execution_dialog)

        if exit_code == 0:
            self.log_message("✓ db_creator ejecutado correctamente")
            if self.execution_config.get('mode', 'normal') == 'normal':
                QMessageBox.information(self, "Completado", "db_creator ejecutado correctamente.")
        else:
            self.log_message(f"✗ db_creator terminó con código de error: {exit_code}")
            if self.execution_config.get('mode', 'normal') == 'normal':
                QMessageBox.warning(self, "Error", f"db_creator terminó con errores (código: {exit_code})")

        self.worker = None

    def log_message(self, message):
        """Mostrar mensaje en el log"""
        print(f"[DbCreatorUI] {message}")

        # Mostrar en el QTextEdit del log
        if hasattr(self, 'log_textEdit'):
            # Añadir timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"

            self.log_textEdit.append(formatted_message)

            # Auto-scroll al final
            cursor = self.log_textEdit.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_textEdit.setTextCursor(cursor)

        # Si BaseModule tiene un método de logging, usarlo también
        if hasattr(super(), 'log_message'):
            super().log_message(message)

    def on_profile_changed(self, profile_name):
        """Manejar cambio de perfil predefinido"""
        # Definir perfiles con scripts y sus configuraciones específicas
        profiles = {
            'Archivos': {
                'scripts': ['path/db_musica_path'],
                'configs': {}
            },
            'Spotify': {
                'scripts': ['path/db_musica_spotify'],
                'configs': {}
            },
            'Escuchas': {
                'scripts': ['lastfm_escuchas', 'listenbrainz/listens_listenbrainz'],
                'configs': {}
            },
            'Letras': {
                'scripts': ['letras/letras_genius_ovh'],
                'configs': {}
            },
            'Info Artistas': {
                'scripts': ['wiki/wikilinks_desde_mb'],
                'configs': {
                    'wiki/wikilinks_desde_mb': {'type': 'artists'}
                }
            },
            'Info Álbumes': {
                'scripts': ['wiki/wikilinks_desde_mb'],
                'configs': {
                    'wiki/wikilinks_desde_mb': {'type': 'albums'}
                }
            },
            'Enlaces Básicos': {
                'scripts': ['enlaces/redes_sociales', 'enlaces/enlaces_artista_album', 'enlaces/yt_song_links'],
                'configs': {}
            },
            'Enlaces Artistas- Álbumes': {
                'scripts': ['enlaces/redes_sociales', 'discogs/artists_info', 'rateyourmusic/rym_artists_links', 'rateyourmusic/rym_artists_info'],
                'configs': {}
            },
            'Enlaces Canciones': {
                'scripts': ['enlaces/enlaces_canciones', 'musicbrainz/mb_data_canciones', 'enlaces/spotify_preview_urls'],
                'configs': {}
            },
            'Discografías': {
                'scripts': ['discogs/discografia_masters', 'discogs/discografia_releases_info', 'musicbrainz/mb_discografia'],
                'configs': {}
            },
            'Sellos': {
                'scripts': ['musicbrainz/mb_sellos', 'wiki/wikilinks_desde_mb'],
                'configs': {
                    'wiki/wikilinks_desde_mb': {'type': 'labels'}
                }
            },
            'Feeds': {
                'scripts': ['posts/posts_fresh_rss', 'posts/review_scrapper', 'libros/epubs', 'posts/menciones'],
                'configs': {}
            },
            'Instrumentos': {
                'scripts': ['posts/equipboard_artists', 'posts/equipboard_instruments', 'posts/equipboard_details'],
                'configs': {}
            },
            'Conciertos': {
                'scripts': ['setlistfm/setlists'],
                'configs': {}
            },
            'Imágenes': {
                'scripts': ['img/portadas_artistas'],
                'configs': {}
            }
        }

        if profile_name not in profiles:
            return

        profile_data = profiles[profile_name]
        profile_scripts = profile_data['scripts']
        profile_configs = profile_data.get('configs', {})

        # Confirmar cambio
        config_info = ""
        if profile_configs:
            config_details = []
            for script, config in profile_configs.items():
                config_str = ", ".join([f"{k}={v}" for k, v in config.items()])
                config_details.append(f"  • {script}: {config_str}")
            config_info = f"\n\nConfiguraciones específicas:\n" + "\n".join(config_details)

        reply = QMessageBox.question(
            self,
            "Aplicar perfil",
            f"¿Aplicar el perfil '{profile_name}'?\n\n"
            f"Scripts que se habilitarán ({len(profile_scripts)}):\n" +
            "\n".join([f"  • {script}" for script in profile_scripts]) +
            config_info +
            "\n\nEsto modificará la selección actual de scripts y sus configuraciones.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Deshabilitar todos los scripts
        for script_data in self.scripts_data:
            script_data['enabled'] = False

        # Habilitar scripts del perfil y aplicar configuraciones específicas
        for script_data in self.scripts_data:
            if script_data['script'] in profile_scripts:
                script_data['enabled'] = True

                # Aplicar configuración específica si existe
                if script_data['script'] in profile_configs:
                    specific_config = profile_configs[script_data['script']]

                    # Mergear la configuración específica con la existente
                    # Esto preserva otras configuraciones y solo actualiza las especificadas
                    current_config = script_data['config'].copy()
                    current_config.update(specific_config)
                    script_data['config'] = current_config

        # Actualizar tabla
        self.tabla_scripts.setSortingEnabled(False)  # Deshabilitar durante actualización
        self.populate_scripts_table()
        self.update_temp_config()

        # Mensaje de confirmación con detalles
        applied_configs = []
        for script in profile_scripts:
            if script in profile_configs:
                config_str = ", ".join([f"{k}={v}" for k, v in profile_configs[script].items()])
                applied_configs.append(f"  • {script}: {config_str}")

        success_message = f"Perfil '{profile_name}' aplicado correctamente.\n\n"
        success_message += f"Scripts habilitados: {len(profile_scripts)}"

        if applied_configs:
            success_message += f"\n\nConfiguraciones aplicadas:\n" + "\n".join(applied_configs)

        QMessageBox.information(
            self,
            "Perfil aplicado",
            success_message
        )
