from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLineEdit, QLabel, QMessageBox, QGroupBox,
    QScrollArea, QFrame, QApplication, QSizePolicy,
    QComboBox, QCheckBox, QInputDialog, QFileDialog
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import uic
import json
import yaml
from pathlib import Path
import copy
import sys
import os
import logging
import traceback

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule, THEMES, PROJECT_ROOT
from utils.config_utils import ConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigEditorModule(BaseModule):
    config_updated = pyqtSignal()
    module_theme_changed = pyqtSignal(str, str)  # Signal to change theme for a specific module

    def __init__(self, config_path: str, parent=None, theme='Tokyo Night', **kwargs):
        # Determinar si la ruta es relativa y convertirla a absoluta si es necesario
        if not os.path.isabs(config_path):
            config_path = os.path.join(PROJECT_ROOT, config_path)
            
        # Initialize config_data with new global configuration options
        self.config_data = {
            "temas": list(THEMES.keys()),  # Always use THEMES from base_module
            "tema_seleccionado": theme,
            "logging": ["true", "false"],
            "logging_state": "true",
            
            # New global configuration options
            "global_theme_config": {
                "enable_individual_themes": True,
                "shared_db_paths": {
                    # Example of how shared database paths might be configured
                    "music_database": "data/music.sqlite"
                }
            },
            
            "modules": [],
            "modulos_desactivados": []  # Add list for disabled modules
        }
        
        self.config_path = config_path
        self.fields = {}
        self.module_checkboxes = {}  # Store module checkboxes

        # Determinar el formato del archivo (YAML o JSON)
        self.config_format = Path(config_path).suffix.lower()
        if self.config_format not in ['.yaml', '.yml', '.json']:
            # Si no tiene extensión reconocible, asumimos YAML como predeterminado
            self.config_format = '.yaml'

        self.available_themes = kwargs.pop('temas', [])
        self.selected_theme = kwargs.pop('tema_seleccionado', theme)        
        
        super().__init__(parent, theme, **kwargs)
        self.load_config()
        
    def apply_theme(self, theme_name=None):
        super().apply_theme(theme_name)

    def load_config(self):
        """Load configuration from file using ConfigManager"""
        try:
            loaded_config = ConfigManager.read_config(self.config_path, self.config_data)
            
            # Overwrite themes with THEMES
            loaded_config["temas"] = list(THEMES.keys())
            
            # Validate selected theme
            if loaded_config["tema_seleccionado"] not in THEMES:
                loaded_config["tema_seleccionado"] = list(THEMES.keys())[0]
            
            # Ensure modulos_desactivados exists
            if "modulos_desactivados" not in loaded_config:
                loaded_config["modulos_desactivados"] = []
            
            self.config_data = loaded_config
            
            # Process all paths to make them relative to PROJECT_ROOT
            self.config_data = self.make_paths_relative(self.config_data)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error loading config from {self.config_path}: {str(e)}\nUsing default configuration."
            )
            self.save_all_config()
            QMessageBox.information(
                self,
                "Config Created",
                f"New config file created at {self.config_path}"
            )

    def make_paths_relative(self, config):
        """Convert all absolute paths to be relative to PROJECT_ROOT"""
        
        def process_path(path):
            if not isinstance(path, str):
                return path
                
            if os.path.isabs(path):
                try:
                    # Intentar convertir a ruta relativa
                    rel_path = os.path.relpath(path, PROJECT_ROOT)
                    return rel_path
                except ValueError:
                    # Ocurre si las rutas están en diferentes unidades en Windows
                    return path
            return path
        
        def process_item(item):
            if isinstance(item, dict):
                return {k: process_item(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [process_item(i) for i in item]
            elif isinstance(item, str) and (
                    os.path.isabs(item) or
                    '/home/' in item or
                    '\\' in item or
                    item.endswith('.py') or
                    item.endswith('.sqlite')
                ):
                # Parece una ruta absoluta
                return process_path(item)
            else:
                return item
        
        return process_item(config)

    def init_ui(self):
        """Initialize the UI using UI file or create it manually"""
        # Try to load UI file
        ui_file_path = os.path.join(PROJECT_ROOT, "ui", "config_editor.ui")
        if os.path.exists(ui_file_path):
            try:
                # Load UI from file
                uic.loadUi(ui_file_path, self)
                
                # Connect signals to slots
                self.save_all_button.clicked.connect(lambda: self.save_all_config(
                    self.enable_individual_themes.isChecked()
                ))
                self.reload_button.clicked.connect(self.reload_config)
                self.add_path_button.clicked.connect(self.add_shared_db_path)
                self.remove_path_button.clicked.connect(self.remove_shared_db_path)
                self.db_paths_dropdown.currentTextChanged.connect(self.update_db_path_input)
                self.browse_button.clicked.connect(self.browse_db_path)
                
                # Add theme field to global group
                theme_field = ConfigField("Global Theme", list(THEMES.keys()))
                theme_field.set_value(self.config_data["tema_seleccionado"])
                self.global_layout.insertWidget(0, theme_field)
                
                # Add logging field to global group
                logging_field = ConfigField("Logging", self.config_data["logging"])
                logging_field.set_value(self.config_data["logging_state"])
                self.global_layout.insertWidget(1, logging_field)
                
                # Add format selection field
                format_field = ConfigField("Config Format", ["yaml", "json"])
                format_field.set_value("yaml" if self.config_format in ['.yaml', '.yml'] else "json")
                self.global_layout.insertWidget(2, format_field)
                self.format_field = format_field
                
                # Set the checkbox state
                self.enable_individual_themes.setChecked(
                    self.config_data.get("global_theme_config", {}).get("enable_individual_themes", True)
                )
                
                # Add database paths to dropdown
                self.load_database_paths()
                
                # Create module groups and add them to their respective layout
                self.create_module_groups()
                
                return True
            except Exception as e:
                logger.error(f"Error loading UI file: {e}")
                logger.error(traceback.format_exc())
        
        # Fallback to manual UI creation
        self._fallback_init_ui()
        return False
    
    def _fallback_init_ui(self):
        """Manual UI creation if UI file loading fails"""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a container widget for all elements
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(10, 10, 10, 10)
        
        # Scrollable area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setWidget(container)
        
        main_layout.addWidget(scroll_area)
        
        # Group for global configurations
        global_group = QGroupBox("Global Configuration")
        global_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        global_layout = QVBoxLayout()
        global_group.setLayout(global_layout)

        # Global theme selection dropdown
        theme_field = ConfigField("Global Theme", list(THEMES.keys()))
        theme_field.set_value(self.config_data["tema_seleccionado"])
        global_layout.addWidget(theme_field)
        
        # Logging state dropdown
        logging_field = ConfigField("Logging", self.config_data["logging"])
        logging_field.set_value(self.config_data["logging_state"])
        global_layout.addWidget(logging_field)
        
        # Config format selection
        format_field = ConfigField("Config Format", ["yaml", "json"])
        format_field.set_value("yaml" if self.config_format in ['.yaml', '.yml'] else "json")
        global_layout.addWidget(format_field)
        self.format_field = format_field
        
        # New global theme configuration checkbox
        enable_individual_themes = QCheckBox("Enable Individual Module Themes")
        enable_individual_themes.setChecked(
            self.config_data.get("global_theme_config", {}).get("enable_individual_themes", True)
        )
        global_layout.addWidget(enable_individual_themes)
        self.enable_individual_themes = enable_individual_themes
        
        # Shared database paths configuration
        shared_db_group = QGroupBox("Shared Database Paths")
        shared_db_layout = QVBoxLayout()
        shared_db_group.setLayout(shared_db_layout)
        
        global_theme_config = self.config_data.get("global_theme_config", {})
        shared_db_paths = global_theme_config.get("shared_db_paths", {})
        
        # Dropdown for existing database paths
        db_path_layout = QHBoxLayout()
        db_path_label = QLabel("Database Path:")
        self.db_paths_dropdown = QComboBox()
        self.db_paths_dropdown.addItems(list(shared_db_paths.keys()))
        
        # Path input field
        self.db_path_input = QLineEdit()
        self.db_path_input.setPlaceholderText("Enter database path")
        
        # Browse button
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_db_path)
        
        # Buttons
        add_path_button = QPushButton("Add Path")
        remove_path_button = QPushButton("Remove Path")
        
        # Layout for dropdown and buttons
        db_path_layout.addWidget(db_path_label)
        db_path_layout.addWidget(self.db_paths_dropdown)
        db_path_layout.addWidget(self.db_path_input)
        db_path_layout.addWidget(browse_button)
        db_path_layout.addWidget(add_path_button)
        db_path_layout.addWidget(remove_path_button)
        
        shared_db_layout.addLayout(db_path_layout)
        
        # Connect buttons
        add_path_button.clicked.connect(self.add_shared_db_path)
        remove_path_button.clicked.connect(self.remove_shared_db_path)
        self.browse_button = browse_button
        self.add_path_button = add_path_button
        self.remove_path_button = remove_path_button
        
        # If there are existing paths, populate the input with the first one
        if shared_db_paths:
            first_key = list(shared_db_paths.keys())[0]
            self.db_path_input.setText(shared_db_paths[first_key])
        
        # Update input when dropdown selection changes
        self.db_paths_dropdown.currentTextChanged.connect(self.update_db_path_input)
        
        global_layout.addWidget(shared_db_group)
        
        container_layout.addWidget(global_group)
        
        # Create "Active Modules" group
        active_modules_group = QGroupBox("Active Modules")
        active_modules_group.setStyleSheet("QGroupBox { font-weight: bold; color: #4CAF50; }")
        active_modules_layout = QVBoxLayout()
        active_modules_group.setLayout(active_modules_layout)
        self.active_modules_layout = active_modules_layout
        
        # Create "Disabled Modules" group
        disabled_modules_group = QGroupBox("Disabled Modules")
        disabled_modules_group.setStyleSheet("QGroupBox { font-weight: bold; color: #F44336; }")
        disabled_modules_layout = QVBoxLayout()
        disabled_modules_group.setLayout(disabled_modules_layout)
        self.disabled_modules_layout = disabled_modules_layout
        
        # Flag to check if we need to show any modules section
        has_active_modules = False
        has_disabled_modules = False
        
        # Module configurations - Active modules
        if self.config_data["modules"]:
            has_active_modules = True
            # Create groups for each active module
            for module in self.config_data["modules"]:
                module_group = self.create_module_group(module, True)
                active_modules_layout.addWidget(module_group)
        
        # Disabled modules
        if "modulos_desactivados" in self.config_data and self.config_data["modulos_desactivados"]:
            has_disabled_modules = True
            # Create groups for each disabled module
            for module in self.config_data["modulos_desactivados"]:
                module_group = self.create_module_group(module, False)
                disabled_modules_layout.addWidget(module_group)
        
        # Only add the groups if they have modules
        if has_active_modules:
            container_layout.addWidget(active_modules_group)
        else:
            # If no active modules, show a message
            label = QLabel("No active modules configured.")
            active_modules_layout.addWidget(label)
            container_layout.addWidget(active_modules_group)
        
        if has_disabled_modules:
            container_layout.addWidget(disabled_modules_group)
        else:
            # If no disabled modules, show a message
            label = QLabel("No disabled modules configured.")
            disabled_modules_layout.addWidget(label)
            container_layout.addWidget(disabled_modules_group)
        
        # Button to save all changes
        save_all_button = QPushButton("Save All Changes")
        save_all_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        save_all_button.clicked.connect(lambda: self.save_all_config(
            enable_individual_themes.isChecked()
        ))
        container_layout.addWidget(save_all_button)
        self.save_all_button = save_all_button
        
        # Button to reload configuration from file
        reload_button = QPushButton("Reload Configuration")
        reload_button.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        reload_button.clicked.connect(self.reload_config)
        container_layout.addWidget(reload_button)
        self.reload_button = reload_button
        
        # Add flexible space at the end to align everything at the top
        container_layout.addStretch()
    
    def browse_db_path(self):
        """Open file dialog to select database file"""
        # Construir la ruta inicial basada en el valor actual
        current_path = self.db_path_input.text()
        if not current_path:
            # Si no hay ruta actual, usar PROJECT_ROOT como inicio
            initial_dir = str(PROJECT_ROOT)
        elif not os.path.isabs(current_path):
            # Si es una ruta relativa, convertirla a absoluta
            initial_dir = os.path.join(PROJECT_ROOT, os.path.dirname(current_path))
        else:
            # Si ya es absoluta, usar su directorio
            initial_dir = os.path.dirname(current_path)
        
        # Asegurar que el directorio inicial existe
        if not os.path.exists(initial_dir):
            initial_dir = str(PROJECT_ROOT)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Database File",
            initial_dir,
            "Database Files (*.sqlite *.db);;All Files (*)"
        )
        
        if file_path:
            # Convertir a ruta relativa si está dentro del PROJECT_ROOT
            try:
                rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                self.db_path_input.setText(rel_path)
            except ValueError:
                # Si no se puede convertir a relativa (p.ej., en diferentes unidades en Windows)
                self.db_path_input.setText(file_path)
    
    def load_database_paths(self):
        """Load database paths from config and populate dropdown"""
        global_theme_config = self.config_data.get("global_theme_config", {})
        shared_db_paths = global_theme_config.get("shared_db_paths", {})
        
        # Clear and add items to dropdown
        self.db_paths_dropdown.clear()
        self.db_paths_dropdown.addItems(list(shared_db_paths.keys()))
        
        # If there are paths, set the first one in the input
        if shared_db_paths:
            first_key = list(shared_db_paths.keys())[0]
            self.db_path_input.setText(shared_db_paths[first_key])
    
    def create_module_groups(self):
        """Create the module groups and add them to their respective layouts"""
        # Clear existing modules
        for i in reversed(range(self.active_modules_layout.count())):
            if self.active_modules_layout.itemAt(i).widget():
                self.active_modules_layout.itemAt(i).widget().deleteLater()
        
        for i in reversed(range(self.disabled_modules_layout.count())):
            if self.disabled_modules_layout.itemAt(i).widget():
                self.disabled_modules_layout.itemAt(i).widget().deleteLater()
        
        # Flag to check if any modules exist
        has_active_modules = False
        has_disabled_modules = False
        
        # Add active modules
        if self.config_data["modules"]:
            has_active_modules = True
            for module in self.config_data["modules"]:
                module_group = self.create_module_group(module, True)
                self.active_modules_layout.addWidget(module_group)
        
        # Add disabled modules
        if self.config_data.get("modulos_desactivados", []):
            has_disabled_modules = True
            for module in self.config_data["modulos_desactivados"]:
                module_group = self.create_module_group(module, False)
                self.disabled_modules_layout.addWidget(module_group)
        
        # If no modules, add placeholder labels
        if not has_active_modules:
            label = QLabel("No active modules configured.")
            self.active_modules_layout.addWidget(label)
        
        if not has_disabled_modules:
            label = QLabel("No disabled modules configured.")
            self.disabled_modules_layout.addWidget(label)

    def create_module_group(self, module, is_active):
        """Create a group for a module with enable/disable checkbox and ordering buttons"""
        module_name = module["name"]
        
        # Create the group
        group = QGroupBox()
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Apply different styles based on active status
        if is_active:
            group.setStyleSheet("QGroupBox { border: 1px solid #4CAF50; border-radius: 5px; margin-top: 10px; padding: 5px; }")
        else:
            group.setStyleSheet("QGroupBox { border: 1px solid #F44336; border-radius: 5px; margin-top: 10px; padding: 5px; }")
        
        group_layout = QVBoxLayout()
        
        # Create header with checkbox and ordering buttons
        header_layout = QHBoxLayout()
        
        # Enable/disable checkbox
        enable_checkbox = QCheckBox(module_name)
        enable_checkbox.setChecked(is_active)
        enable_checkbox.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(enable_checkbox)
        
        # Add spacer to push ordering buttons to the right
        header_layout.addStretch()
        
        # Add ordering buttons
        move_up_button = QPushButton("↑")
        move_up_button.setFixedWidth(30)
        move_up_button.setToolTip("Move module up")
        move_up_button.clicked.connect(lambda: self.move_module(module_name, "up"))
        
        move_down_button = QPushButton("↓")
        move_down_button.setFixedWidth(30)
        move_down_button.setToolTip("Move module down")
        move_down_button.clicked.connect(lambda: self.move_module(module_name, "down"))
        
        header_layout.addWidget(move_up_button)
        header_layout.addWidget(move_down_button)
        
        # Store the checkbox for later use
        self.module_checkboxes[module_name] = enable_checkbox
        
        group_layout.addLayout(header_layout)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        group_layout.addWidget(separator)
        
        # Fields specific to each module
        fields = {}
        
        # Add module-specific theme dropdown if individual themes are enabled
        if (self.config_data.get("global_theme_config", {}).get("enable_individual_themes", True) and 
            "temas" in module.get("args", {})):
            # Check if the module has its own themes or should use global themes
            module_themes = module["args"]["temas"]
            if not module_themes:  # If empty, use global themes
                module_themes = list(THEMES.keys())
                
            theme_dropdown = ConfigField(f"Theme", module_themes)
            current_theme = module["args"].get("tema_seleccionado", list(THEMES.keys())[0])
            
            # Make sure selected theme is in the list
            if current_theme not in module_themes:
                current_theme = module_themes[0] if module_themes else list(THEMES.keys())[0]
                
            theme_dropdown.set_value(current_theme)
            group_layout.addWidget(theme_dropdown)
            fields["theme_dropdown"] = theme_dropdown
        
        # Process module arguments
        for key, value in module.get("args", {}).items():
            # Skip 'temas' and 'tema_seleccionado' as they're handled separately
            if key in ["temas", "tema_seleccionado"]:
                continue
            
            if isinstance(value, dict):
                # Use NestedConfigGroup for nested structures
                nested_group = NestedConfigGroup(key, value)
                group_layout.addWidget(nested_group)
                fields[key] = nested_group
            else:
                # Use ConfigField for simple values
                field = ConfigField(key, value)
                group_layout.addWidget(field)
                fields[key] = field
        
        self.fields[module_name] = fields
        
        # Add buttons row
        buttons_layout = QHBoxLayout()
        
        # Save button for this module
        save_button = QPushButton(f"Save {module_name}")
        save_button.setStyleSheet("background-color: #4CAF50; color: white;")
        save_button.clicked.connect(lambda checked, m=module_name: self.save_module_config(m))
        buttons_layout.addWidget(save_button)
        
        # Reset button for this module
        reset_button = QPushButton("Reset")
        reset_button.setStyleSheet("background-color: #F44336; color: white;")
        reset_button.clicked.connect(lambda checked, m=module_name: self.reset_module_config(m))
        buttons_layout.addWidget(reset_button)
        
        group_layout.addLayout(buttons_layout)
        
        group.setLayout(group_layout)
        return group

    def update_db_path_input(self, current_key):
        """Update the path input when a new database is selected from dropdown"""
        global_theme_config = self.config_data.get("global_theme_config", {})
        shared_db_paths = global_theme_config.get("shared_db_paths", {})
        
        if current_key in shared_db_paths:
            self.db_path_input.setText(shared_db_paths[current_key])

    def add_shared_db_path(self):
        """Add a new shared database path"""
        path = self.db_path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "Invalid Input", "Please enter a database path.")
            return
        
        # Prompt for database key
        key, ok = QInputDialog.getText(self, "Database Key", "Enter a key for this database path:")
        if not ok or not key:
            return
        
        # Sanitize the key
        key = key.lower().replace(' ', '_')
        
        # Ensure global_theme_config exists
        if "global_theme_config" not in self.config_data:
            self.config_data["global_theme_config"] = {}
        
        if "shared_db_paths" not in self.config_data["global_theme_config"]:
            self.config_data["global_theme_config"]["shared_db_paths"] = {}
        
        # Check for existing key
        if key in self.config_data["global_theme_config"]["shared_db_paths"]:
            reply = QMessageBox.question(self, "Overwrite", 
                f"A path for '{key}' already exists. Do you want to replace it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.No:
                return
        
        # Add or update the path
        self.config_data["global_theme_config"]["shared_db_paths"][key] = path
        
        # Save the configuration to file
        try:
            format_choice = self.format_field.get_value() if hasattr(self, 'format_field') else "yaml"
            ConfigManager.write_config(self.config_path, self.config_data, format_choice)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save configuration: {str(e)}")
            return
        
        # Update dropdown
        self.db_paths_dropdown.blockSignals(True)
        self.db_paths_dropdown.clear()
        self.db_paths_dropdown.addItems(list(self.config_data["global_theme_config"]["shared_db_paths"].keys()))
        self.db_paths_dropdown.setCurrentText(key)
        self.db_paths_dropdown.blockSignals(False)
        
        # Update path input
        self.db_path_input.setText(path)
        
        # Emit config updated signal
        self.config_updated.emit()
        
        # Show success message
        QMessageBox.information(self, "Success", f"Database path '{key}' added successfully.")
    
    def remove_shared_db_path(self):
        """Remove selected shared database path"""
        current_key = self.db_paths_dropdown.currentText()
        if not current_key:
            QMessageBox.warning(self, "No Selection", "Please select a database path to remove.")
            return
        
        # Confirmation dialog using StandardButton
        respuesta = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            f"Are you sure you want to delete the database path '{current_key}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                # Ensure the path exists before trying to delete
                if "global_theme_config" in self.config_data and \
                "shared_db_paths" in self.config_data["global_theme_config"]:
                    
                    db_paths = self.config_data["global_theme_config"]["shared_db_paths"]
                    if current_key in db_paths:
                        del db_paths[current_key]
                    
                    # Save updated configuration to file
                    format_choice = self.format_field.get_value() if hasattr(self, 'format_field') else "yaml"
                    ConfigManager.write_config(self.config_path, self.config_data, format_choice)
                    
                    # Update dropdown
                    self.db_paths_dropdown.removeItem(self.db_paths_dropdown.currentIndex())
                    
                    # Clear input
                    self.db_path_input.clear()
                    
                    # Emit config updated signal
                    self.config_updated.emit()
                    
                    # Show success message
                    QMessageBox.information(self, "Success", f"Database path '{current_key}' removed.")
                else:
                    QMessageBox.warning(self, "Error", "Configuration structure is invalid.")
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not remove database path: {str(e)}")
    
    def move_module(self, module_name, direction):
        """Move a module up or down in its list"""
        # Find the module's current list and position
        module_index = -1
        module_list = None
        is_active = self.module_checkboxes[module_name].isChecked()
        
        if is_active:
            # Check in active modules
            for i, module in enumerate(self.config_data["modules"]):
                if module["name"] == module_name:
                    module_index = i
                    module_list = self.config_data["modules"]
                    break
        else:
            # Check in disabled modules
            for i, module in enumerate(self.config_data["modulos_desactivados"]):
                if module["name"] == module_name:
                    module_index = i
                    module_list = self.config_data["modulos_desactivados"]
                    break
        
        if module_list is None or module_index == -1:
            QMessageBox.warning(self, "Error", f"Cannot find module '{module_name}' in the configuration")
            return
        
        # Calculate new position
        new_index = -1
        if direction == "up" and module_index > 0:
            new_index = module_index - 1
        elif direction == "down" and module_index < len(module_list) - 1:
            new_index = module_index + 1
        
        if new_index == -1:
            # Module already at the top/bottom
            return
        
        # Move the module
        module = module_list.pop(module_index)
        module_list.insert(new_index, module)
        
        # Save the changes
        try:
            format_choice = self.format_field.get_value() if hasattr(self, 'format_field') else "yaml"
            ConfigManager.write_config(self.config_path, self.config_data, format_choice)
            
            # Notify user and emit signal
            QMessageBox.information(
                self, 
                "Module Reordered", 
                f"Module '{module_name}' has been moved {direction}."
            )
            
            # Emit config updated signal to trigger reload
            self.config_updated.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving configuration: {str(e)}")
    
    def reload_config(self):
        """Reload configuration from file and update UI"""
        try:
            self.load_config()
            
            # If using UI file
            if hasattr(self, 'container'):
                # Update enable individual themes checkbox
                self.enable_individual_themes.setChecked(
                    self.config_data.get("global_theme_config", {}).get("enable_individual_themes", True)
                )
                
                # Update database paths
                self.load_database_paths()
                
                # Recreate module groups
                self.create_module_groups()
                
                # Update theme fields if they exist
                for child in self.findChildren(ConfigField):
                    if child.label.text() == "Global Theme":
                        child.set_value(self.config_data["tema_seleccionado"])
                    elif child.label.text() == "Logging":
                        child.set_value(self.config_data["logging_state"])
                    elif child.label.text() == "Config Format":
                        format_value = "yaml" if self.config_format in ['.yaml', '.yml'] else "json"
                        child.set_value(format_value)
            else:
                # For manually created UI, recreate everything
                for i in reversed(range(self.layout().count())): 
                    widget = self.layout().itemAt(i).widget()
                    if widget is not None:
                        widget.deleteLater()
                
                # Reinitialize UI
                self.init_ui()
            
            QMessageBox.information(self, "Success", "Configuration reloaded successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error reloading configuration: {str(e)}")
    
    def reset_module_config(self, module_name):
        """Reset a module's configuration to the saved values"""
        try:
            # Reload the configuration from file
            loaded_config = ConfigManager.read_config(self.config_path, {})
            
            # Find the module
            module_found = False
            for module_list in [loaded_config["modules"], loaded_config.get("modulos_desactivados", [])]:
                for module in module_list:
                    if module["name"] == module_name:
                        module_found = True
                        # Reset checkbox
                        is_active = module in loaded_config["modules"]
                        self.module_checkboxes[module_name].setChecked(is_active)
                        
                        # Reset fields
                        if module_name in self.fields:
                            fields = self.fields[module_name]
                            
                            # Reset theme if present
                            if "theme_dropdown" in fields and "tema_seleccionado" in module.get("args", {}):
                                fields["theme_dropdown"].set_value(module["args"]["tema_seleccionado"])
                            
                            # Reset other fields
                            for key, field in fields.items():
                                if key != "theme_dropdown" and key in module.get("args", {}):
                                    field.set_value(module["args"][key])
                        
                        break
                if module_found:
                    break
            
            if not module_found:
                QMessageBox.warning(self, "Module Not Found", f"Could not find module '{module_name}' in configuration")
            else:
                QMessageBox.information(self, "Reset Complete", f"Module '{module_name}' settings have been reset")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error resetting module configuration: {str(e)}")
    
    def save_module_config(self, module_name: str):
        """Save configuration for a specific module"""
        try:
            # Find the module in either active or disabled modules
            is_active = self.module_checkboxes[module_name].isChecked()
            
            # Find where the module currently exists (active or disabled list)
            module_list = None
            module_index = -1
            
            # Look in active modules first
            for i, module in enumerate(self.config_data["modules"]):
                if module["name"] == module_name:
                    module_list = self.config_data["modules"]
                    module_index = i
                    break
            
            # If not found in active, look in disabled
            if module_index == -1:
                for i, module in enumerate(self.config_data["modulos_desactivados"]):
                    if module["name"] == module_name:
                        module_list = self.config_data["modulos_desactivados"]
                        module_index = i
                        break
            
            if module_list is None or module_index == -1:
                QMessageBox.critical(self, "Error", f"Module {module_name} not found in configuration")
                return
            
            # Create a deep copy of the module to modify
            module = copy.deepcopy(module_list[module_index])
            module_fields = self.fields[module_name]
            
            # Track if theme was changed
            theme_changed = False
            old_theme = None
            new_theme = None
            
            # Handle module theme change
            if "theme_dropdown" in module_fields and "args" in module and "tema_seleccionado" in module["args"]:
                old_theme = module["args"]["tema_seleccionado"]
                new_theme = module_fields["theme_dropdown"].get_value()
                
                if old_theme != new_theme:
                    theme_changed = True
                    module["args"]["tema_seleccionado"] = new_theme
                    
                    # Only emit signal if module is active and theme actually changed
                    if is_active and theme_changed:  
                        self.module_theme_changed.emit(module_name, new_theme)
            
            # Update other fields
            if "args" not in module:
                module["args"] = {}
                
            for key, field in module_fields.items():
                if key != "theme_dropdown":
                    module["args"][key] = field.get_value()
            
            # Remove from current list
            source_list = module_list
            source_list.pop(module_index)
            
            # Add to correct list based on checkbox
            dest_list = self.config_data["modules"] if is_active else self.config_data["modulos_desactivados"]
            dest_list.append(module)
            
            # Get format choice
            format_choice = self.format_field.get_value() if hasattr(self, 'format_field') else "yaml"
            
            # Convert any absolute paths to relative
            module = self.make_paths_relative(module)
            
            # Save to file using ConfigManager
            ConfigManager.write_config(self.config_path, self.config_data, format_choice)
            
            # Show success message based on what changed
            if source_list != dest_list:
                message = f"Module '{module_name}' has been {'enabled' if is_active else 'disabled'}."
                if theme_changed:
                    message += f"\nTheme changed from '{old_theme}' to '{new_theme}'."
            elif theme_changed:
                message = f"Theme for '{module_name}' changed from '{old_theme}' to '{new_theme}'."
            else:
                message = f"Configuration for {module_name} saved successfully."
            
            QMessageBox.information(self, "Success", message)
            
            # Emit config updated signal
            self.config_updated.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving config: {str(e)}")
            logging.error(f"Error saving module config: {str(e)}")
            logging.error(traceback.format_exc())
    
    def save_all_config(self, enable_individual_themes=True):
        """Save all configuration changes"""
        try:
            # Create a deep copy of the config to modify
            updated_config = copy.deepcopy(self.config_data)
            
            # Ensure global_theme_config exists
            if "global_theme_config" not in updated_config:
                updated_config["global_theme_config"] = {}
            
            # Update enable individual themes setting
            updated_config["global_theme_config"]["enable_individual_themes"] = enable_individual_themes
            
            # Ensure shared_db_paths exists
            if "shared_db_paths" not in updated_config["global_theme_config"]:
                updated_config["global_theme_config"]["shared_db_paths"] = {}
            
            # Add current path if not empty
            current_key = self.db_paths_dropdown.currentText()
            current_path = self.db_path_input.text().strip()
            if current_key and current_path:
                updated_config["global_theme_config"]["shared_db_paths"][current_key] = current_path
            
            # Update global theme
            theme_fields = [f for f in self.findChildren(ConfigField) if f.label.text() == "Global Theme"]
            if theme_fields:
                new_global_theme = theme_fields[0].get_value()
                updated_config["tema_seleccionado"] = new_global_theme
            
            # Update logging state
            logging_fields = [f for f in self.findChildren(ConfigField) if f.label.text() == "Logging"]
            if logging_fields:
                updated_config["logging_state"] = logging_fields[0].get_value()
            
            # Update config format choice
            format_fields = [f for f in self.findChildren(ConfigField) if f.label.text() == "Config Format"]
            format_choice = "yaml"  # Default to YAML
            if format_fields:
                format_choice = format_fields[0].get_value()
                # Actualizar la extensión del archivo de configuración si es necesario
                if format_choice == "yaml" and not self.config_path.endswith(('.yaml', '.yml')):
                    new_path = Path(self.config_path).with_suffix('.yaml')
                    self.config_path = str(new_path)
                elif format_choice == "json" and not self.config_path.endswith('.json'):
                    new_path = Path(self.config_path).with_suffix('.json')
                    self.config_path = str(new_path)
            
            # Initialize lists for modules
            updated_config["modules"] = []
            updated_config["modulos_desactivados"] = []
            
            # Track theme changes for active modules
            theme_changes = []
            
            # Process all module checkboxes to organize modules
            for module_name, checkbox in self.module_checkboxes.items():
                is_active = checkbox.isChecked()
                
                # Find the module in either list
                module = None
                for mod in self.config_data["modules"] + self.config_data.get("modulos_desactivados", []):
                    if mod["name"] == module_name:
                        # Create a deep copy to avoid modifying the original
                        module = copy.deepcopy(mod)
                        break
                
                if not module:
                    continue
                    
                # Update module settings if we have fields for it
                if module_name in self.fields:
                    module_fields = self.fields[module_name]
                    
                    # Check for theme change
                    old_theme = None
                    new_theme = None
                    
                    if "theme_dropdown" in module_fields and "args" in module:
                        old_theme = module["args"].get("tema_seleccionado")
                        new_theme = module_fields["theme_dropdown"].get_value()
                        
                        # Update theme
                        module["args"]["tema_seleccionado"] = new_theme
                        
                        # Track theme change for active modules
                        if is_active and old_theme != new_theme:
                            theme_changes.append((module_name, new_theme))
                    
                    # Update other fields
                    for key, field in module_fields.items():
                        if key != "theme_dropdown" and "args" in module:
                            module["args"][key] = field.get_value()
                
                # Add to the appropriate list
                if is_active:
                    updated_config["modules"].append(module)
                else:
                    updated_config["modulos_desactivados"].append(module)
            
            # Process absolute paths to make them relative if possible
            updated_config = self.make_paths_relative(updated_config)
            
            # Save file with updated configuration using ConfigManager
            if ConfigManager.write_config(self.config_path, updated_config, format_choice):
                # Update our local config data
                self.config_data = updated_config
                
                # Emit theme change signals
                for module_name, new_theme in theme_changes:
                    self.module_theme_changed.emit(module_name, new_theme)
                
                QMessageBox.information(self, "Success", f"All configurations saved successfully to {self.config_path}")
                self.config_updated.emit()
                
                return True  # Indicate successful save
            else:
                QMessageBox.critical(self, "Error", f"Failed to save configuration to {self.config_path}")
                return False
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving config: {str(e)}")
            logging.error(f"Error saving configuration: {str(e)}")
            logging.error(traceback.format_exc())
            return False