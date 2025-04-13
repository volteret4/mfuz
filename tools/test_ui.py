import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTabWidget, 
    QPushButton, QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QCheckBox, 
    QRadioButton, QListWidget, QTreeWidget, QTreeWidgetItem, QTableWidget, 
    QTableWidgetItem, QLabel, QGroupBox, QProgressBar, QSpinBox, QDoubleSpinBox,
    QDateEdit, QTimeEdit, QDateTimeEdit, QFrame, QSplitter, QMenu, QMenuBar,
    QStatusBar, QDialog, QDialogButtonBox, QFormLayout, QScrollBar, QHeaderView,
    QFileDialog
)
from PyQt6.QtGui import QShortcut, QKeySequence, QColor, QAction
from PyQt6.QtCore import Qt, QSize, QDate, QTime, QDateTime

# Archivo de configuración de temas
THEMES_FILE = "themes.json"

class ThemeTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.font_family = "Segoe UI"
        self.font_size = "12px"
        self.current_theme = "Tokyo Night"
        
        # Cargar temas
        self.load_themes()
        
        # Configurar UI
        self.init_ui()
        
        # Configurar atajos de teclado
        self.setup_shortcuts()
        
        # Aplicar tema inicial
        self.apply_theme()
        
    def load_themes(self):
        """Carga los temas desde el archivo JSON."""
        try:
            # Crear el archivo de temas si no existe
            if not os.path.exists(THEMES_FILE):
                self.create_default_themes()
            
            # Cargar temas
            with open(THEMES_FILE, 'r') as f:
                self.themes = json.load(f)
        except Exception as e:
            print(f"Error al cargar temas: {str(e)}")
            self.create_default_themes()
    
    def create_default_themes(self):
        """Crea un tema predeterminado si no existe el archivo de temas."""
        self.themes = {
            "Tokyo Night": {
                "bg": "#1a1b26",
                "fg": "#a9b1d6",
                "secondary_bg": "#24283b",
                "border": "#414868",
                "accent": "#7aa2f7",
                "selection": "#565f89",
                "button_hover": "#3b4261"
            },
            "Light": {
                "bg": "#ffffff",
                "fg": "#000000",
                "secondary_bg": "#f0f0f0",
                "border": "#d0d0d0",
                "accent": "#0078d7",
                "selection": "#b3d7ff",
                "button_hover": "#e5f1fb"
            }
        }
        
        # Guardar temas
        with open(THEMES_FILE, 'w') as f:
            json.dump(self.themes, f, indent=4)
    
    def init_ui(self):
        """Configura la interfaz de usuario."""
        self.setWindowTitle("Probador de Temas PyQt6")
        self.setMinimumSize(1000, 700)
        
        # Crear el widget central
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Crear menú
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        
        file_menu = QMenu("Archivo", self)
        file_menu.addAction("Cargar tema desde archivo", self.load_theme_file)
        file_menu.addAction("Guardar tema actual", self.save_theme_file)
        file_menu.addSeparator()
        file_menu.addAction("Salir", self.close)
        menubar.addMenu(file_menu)
        
        theme_menu = QMenu("Temas", self)
        
        # Añadir opciones de temas
        for theme_name in self.themes.keys():
            theme_action = QAction(theme_name, self)
            theme_action.triggered.connect(lambda checked, name=theme_name: self.change_theme(name))
            theme_menu.addAction(theme_action)
        
        menubar.addMenu(theme_menu)
        
        # Barra de estado
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Listo")
        
        # Botón para recargar temas
        reload_button = QPushButton("Recargar Temas (F5 / Ctrl+R)")
        reload_button.clicked.connect(self.reload_themes)
        main_layout.addWidget(reload_button)
        
        # Caja de edición de tema actual
        theme_edit_group = QGroupBox("Editar Tema Actual")
        theme_edit_layout = QVBoxLayout(theme_edit_group)
        
        self.theme_editor = QPlainTextEdit()
        self.update_theme_editor()
        theme_edit_layout.addWidget(self.theme_editor)
        
        edit_buttons_layout = QHBoxLayout()
        apply_button = QPushButton("Aplicar Cambios")
        apply_button.clicked.connect(self.apply_theme_changes)
        edit_buttons_layout.addWidget(apply_button)
        
        save_button = QPushButton("Guardar Cambios")
        save_button.clicked.connect(self.save_theme_changes)
        edit_buttons_layout.addWidget(save_button)
        
        theme_edit_layout.addLayout(edit_buttons_layout)
        
        main_layout.addWidget(theme_edit_group)
        
        # Tema actual
        self.theme_label = QLabel(f"Tema actual: {self.current_theme}")
        main_layout.addWidget(self.theme_label)
        
        # Tabs para organizar widgets
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Widgets básicos
        self.create_basic_widgets_tab()
        
        # Tab 2: Widgets de formulario
        self.create_form_widgets_tab()
        
        # Tab 3: Widgets de lista y tablas
        self.create_list_widgets_tab()
        
        # Tab 4: Widgets adicionales
        self.create_additional_widgets_tab()
        
        # Tab 5: Diálogos
        self.create_dialog_tab()
        
        # Centro de la ventana
        self.center_on_screen()
    
    def create_basic_widgets_tab(self):
        """Crea la pestaña de widgets básicos."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Etiquetas
        layout.addWidget(QLabel("Etiqueta (QLabel) normal"))
        
        # Botones
        buttons_group = QGroupBox("Botones (QPushButton)")
        buttons_layout = QHBoxLayout(buttons_group)
        
        normal_button = QPushButton("Botón Normal")
        buttons_layout.addWidget(normal_button)
        
        hover_button = QPushButton("Botón Hover\n(Pasa el ratón por encima)")
        buttons_layout.addWidget(hover_button)
        
        disabled_button = QPushButton("Botón Desactivado")
        disabled_button.setEnabled(False)
        buttons_layout.addWidget(disabled_button)
        
        layout.addWidget(buttons_group)
        
        # Campos de texto
        text_group = QGroupBox("Campos de Texto")
        text_layout = QVBoxLayout(text_group)
        
        # QLineEdit
        text_layout.addWidget(QLabel("QLineEdit:"))
        line_edit = QLineEdit()
        line_edit.setText("Texto de ejemplo en QLineEdit")
        text_layout.addWidget(line_edit)
        
        # QTextEdit
        text_layout.addWidget(QLabel("QTextEdit:"))
        text_edit = QTextEdit()
        text_edit.setText("Texto de ejemplo en QTextEdit.\nPuede contener múltiples líneas y formato.")
        text_layout.addWidget(text_edit)
        
        # QPlainTextEdit
        text_layout.addWidget(QLabel("QPlainTextEdit:"))
        plain_text = QPlainTextEdit()
        plain_text.setPlainText("Texto plano de ejemplo en QPlainTextEdit.\nSin formato.")
        text_layout.addWidget(plain_text)
        
        layout.addWidget(text_group)
        
        self.tabs.addTab(tab, "Widgets Básicos")
    
    def create_form_widgets_tab(self):
        """Crea la pestaña de widgets de formulario."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Combobox
        combo_group = QGroupBox("QComboBox")
        combo_layout = QVBoxLayout(combo_group)
        
        combo = QComboBox()
        combo.addItems(["Opción 1", "Opción 2", "Opción 3", "Opción 4"])
        combo_layout.addWidget(combo)
        
        layout.addWidget(combo_group)
        
        # Checkbox y RadioButton
        check_group = QGroupBox("QCheckBox y QRadioButton")
        check_layout = QVBoxLayout(check_group)
        
        # Checkboxes
        check_layout.addWidget(QLabel("QCheckBox:"))
        check1 = QCheckBox("Opción marcada")
        check1.setChecked(True)
        check_layout.addWidget(check1)
        
        check2 = QCheckBox("Opción sin marcar")
        check_layout.addWidget(check2)
        
        # RadioButtons
        check_layout.addWidget(QLabel("QRadioButton:"))
        radio1 = QRadioButton("Opción 1 (seleccionada)")
        radio1.setChecked(True)
        check_layout.addWidget(radio1)
        
        radio2 = QRadioButton("Opción 2")
        check_layout.addWidget(radio2)
        
        layout.addWidget(check_group)
        
        # Spinboxes
        spin_group = QGroupBox("QSpinBox, QDoubleSpinBox")
        spin_layout = QVBoxLayout(spin_group)
        
        spin_layout.addWidget(QLabel("QSpinBox:"))
        spin = QSpinBox()
        spin.setRange(0, 100)
        spin.setValue(50)
        spin_layout.addWidget(spin)
        
        spin_layout.addWidget(QLabel("QDoubleSpinBox:"))
        double_spin = QDoubleSpinBox()
        double_spin.setRange(0.0, 1.0)
        double_spin.setValue(0.5)
        double_spin.setSingleStep(0.1)
        spin_layout.addWidget(double_spin)
        
        layout.addWidget(spin_group)
        
        # Widgets de fecha y hora
        date_group = QGroupBox("QDateEdit, QTimeEdit, QDateTimeEdit")
        date_layout = QVBoxLayout(date_group)
        
        date_layout.addWidget(QLabel("QDateEdit:"))
        date_edit = QDateEdit()
        date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(date_edit)
        
        date_layout.addWidget(QLabel("QTimeEdit:"))
        time_edit = QTimeEdit()
        time_edit.setTime(QTime.currentTime())
        date_layout.addWidget(time_edit)
        
        date_layout.addWidget(QLabel("QDateTimeEdit:"))
        datetime_edit = QDateTimeEdit()
        datetime_edit.setDateTime(QDateTime.currentDateTime())
        date_layout.addWidget(datetime_edit)
        
        layout.addWidget(date_group)
        
        self.tabs.addTab(tab, "Widgets de Formulario")
    
    def create_list_widgets_tab(self):
        """Crea la pestaña de widgets de lista y tablas."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # QListWidget
        list_group = QGroupBox("QListWidget")
        list_layout = QVBoxLayout(list_group)
        
        list_widget = QListWidget()
        for i in range(10):
            list_widget.addItem(f"Elemento {i+1}")
        list_widget.setCurrentRow(0)
        list_layout.addWidget(list_widget)
        
        layout.addWidget(list_group)
        
        # QTreeWidget
        tree_group = QGroupBox("QTreeWidget")
        tree_layout = QVBoxLayout(tree_group)
        
        tree_widget = QTreeWidget()
        tree_widget.setHeaderLabels(["Columna 1", "Columna 2"])
        
        for i in range(5):
            parent = QTreeWidgetItem(tree_widget)
            parent.setText(0, f"Elemento padre {i+1}")
            parent.setText(1, f"Dato {i+1}")
            
            for j in range(3):
                child = QTreeWidgetItem()
                child.setText(0, f"Hijo {j+1}")
                child.setText(1, f"Dato hijo {j+1}")
                parent.addChild(child)
        
        tree_widget.expandAll()
        tree_layout.addWidget(tree_widget)
        
        layout.addWidget(tree_group)
        
        # QTableWidget
        table_group = QGroupBox("QTableWidget")
        table_layout = QVBoxLayout(table_group)
        
        table_widget = QTableWidget(5, 3)
        table_widget.setHorizontalHeaderLabels(["Columna 1", "Columna 2", "Columna 3"])
        
        for i in range(5):
            for j in range(3):
                item = QTableWidgetItem(f"Celda {i+1},{j+1}")
                table_widget.setItem(i, j, item)
        
        table_widget.setCurrentCell(0, 0)
        table_layout.addWidget(table_widget)
        
        layout.addWidget(table_group)
        
        self.tabs.addTab(tab, "Listas y Tablas")
    
    def create_additional_widgets_tab(self):
        """Crea la pestaña de widgets adicionales."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # QProgressBar
        progress_group = QGroupBox("QProgressBar")
        progress_layout = QVBoxLayout(progress_group)
        
        progress_bar = QProgressBar()
        progress_bar.setValue(70)
        progress_layout.addWidget(progress_bar)
        
        layout.addWidget(progress_group)
        
        # QFrame
        frame_group = QGroupBox("QFrame")
        frame_layout = QVBoxLayout(frame_group)
        
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.Box)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        frame.setLineWidth(2)
        frame.setMinimumHeight(50)
        frame_layout.addWidget(frame)
        
        layout.addWidget(frame_group)
        
        # QSplitter
        splitter_group = QGroupBox("QSplitter")
        splitter_layout = QVBoxLayout(splitter_group)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("Widget izquierdo"))
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(QLabel("Widget derecho"))
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        splitter_layout.addWidget(splitter)
        
        layout.addWidget(splitter_group)
        
        # QScrollBar
        scroll_group = QGroupBox("QScrollBar")
        scroll_layout = QVBoxLayout(scroll_group)
        
        scroll_layout.addWidget(QLabel("QScrollBar Horizontal:"))
        scroll_h = QScrollBar(Qt.Orientation.Horizontal)
        scroll_h.setRange(0, 100)
        scroll_h.setValue(50)
        scroll_layout.addWidget(scroll_h)
        
        scroll_layout.addWidget(QLabel("QScrollBar Vertical:"))
        scroll_v = QScrollBar(Qt.Orientation.Vertical)
        scroll_v.setRange(0, 100)
        scroll_v.setValue(50)
        scroll_v.setMinimumHeight(100)
        scroll_layout.addWidget(scroll_v)
        
        layout.addWidget(scroll_group)
        
        self.tabs.addTab(tab, "Widgets Adicionales")
    
    def create_dialog_tab(self):
        """Crea la pestaña de diálogos."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Botón para mostrar diálogo
        dialog_button = QPushButton("Mostrar Diálogo de Ejemplo")
        dialog_button.clicked.connect(self.show_dialog)
        layout.addWidget(dialog_button)
        
        # QMenu
        menu_group = QGroupBox("QMenu")
        menu_layout = QVBoxLayout(menu_group)
        
        menu_button = QPushButton("Mostrar Menú")
        menu_button.clicked.connect(lambda: self.show_menu(menu_button))
        menu_layout.addWidget(menu_button)
        
        layout.addWidget(menu_group)
        
        self.tabs.addTab(tab, "Diálogos y Menús")
    
    def show_dialog(self):
        """Muestra un diálogo de ejemplo."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Diálogo de Ejemplo")
        
        layout = QVBoxLayout(dialog)
        
        form_layout = QFormLayout()
        form_layout.addRow("Nombre:", QLineEdit())
        form_layout.addRow("Edad:", QSpinBox())
        
        layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec()
    
    def show_menu(self, button):
        """Muestra un menú contextual."""
        menu = QMenu(self)
        menu.addAction("Opción 1")
        menu.addAction("Opción 2")
        menu.addAction("Opción 3")
        menu.addSeparator()
        menu.addAction("Salir")
        
        # Posicionar el menú debajo del botón
        pos = button.mapToGlobal(button.rect().bottomLeft())
        menu.exec(pos)
    
    def setup_shortcuts(self):
        """Configura los atajos de teclado."""
        # F5 para recargar
        self.shortcut_f5 = QShortcut(QKeySequence("F5"), self)
        self.shortcut_f5.activated.connect(self.reload_themes)
        
        # Ctrl+R para recargar
        self.shortcut_ctrl_r = QShortcut(QKeySequence("Ctrl+R"), self)
        self.shortcut_ctrl_r.activated.connect(self.reload_themes)
        
        # Ctrl+S para guardar cambios
        self.shortcut_ctrl_s = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_ctrl_s.activated.connect(self.save_theme_changes)
        
        # Ctrl+A para aplicar cambios
        self.shortcut_ctrl_a = QShortcut(QKeySequence("Ctrl+A"), self)
        self.shortcut_ctrl_a.activated.connect(self.apply_theme_changes)
    
    def update_theme_editor(self):
        """Actualiza el editor de temas con el tema actual."""
        theme_json = json.dumps(self.themes[self.current_theme], indent=4)
        self.theme_editor.setPlainText(theme_json)
    
    def apply_theme_changes(self):
        """Aplica los cambios realizados en el editor de temas."""
        try:
            # Obtener el JSON del editor
            theme_json = self.theme_editor.toPlainText()
            theme_data = json.loads(theme_json)
            
            # Actualizar el tema actual
            self.themes[self.current_theme] = theme_data
            
            # Aplicar el tema
            self.apply_theme()
            
            self.statusBar.showMessage("Cambios aplicados correctamente", 3000)
        except json.JSONDecodeError as e:
            self.statusBar.showMessage(f"Error de formato JSON: {str(e)}", 5000)
        except Exception as e:
            self.statusBar.showMessage(f"Error al aplicar cambios: {str(e)}", 5000)
    
    def save_theme_changes(self):
        """Guarda los cambios realizados en el editor de temas."""
        try:
            # Primero aplicar los cambios
            self.apply_theme_changes()
            
            # Guardar en el archivo
            with open(THEMES_FILE, 'w') as f:
                json.dump(self.themes, f, indent=4)
            
            self.statusBar.showMessage("Cambios guardados correctamente", 3000)
        except Exception as e:
            self.statusBar.showMessage(f"Error al guardar cambios: {str(e)}", 5000)
    
    def load_theme_file(self):
        """Carga un tema desde un archivo."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Cargar Tema", "", "Archivos JSON (*.json)"
            )
            
            if file_path:
                with open(file_path, 'r') as f:
                    theme_data = json.load(f)
                
                # Verificar si es un tema individual o un conjunto de temas
                if isinstance(theme_data, dict) and all(isinstance(theme_data[key], dict) for key in theme_data):
                    # Es un conjunto de temas
                    self.themes.update(theme_data)
                    self.statusBar.showMessage(f"Temas cargados: {', '.join(theme_data.keys())}", 3000)
                else:
                    # Es un tema individual
                    theme_name, _ = os.path.splitext(os.path.basename(file_path))
                    self.themes[theme_name] = theme_data
                    self.change_theme(theme_name)
                    self.statusBar.showMessage(f"Tema cargado: {theme_name}", 3000)
                
                # Guardar los temas
                with open(THEMES_FILE, 'w') as f:
                    json.dump(self.themes, f, indent=4)
        except Exception as e:
            self.statusBar.showMessage(f"Error al cargar tema: {str(e)}", 5000)
    
    def save_theme_file(self):
        """Guarda el tema actual en un archivo separado."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Guardar Tema", f"{self.current_theme}.json", "Archivos JSON (*.json)"
            )
            
            if file_path:
                with open(file_path, 'w') as f:
                    json.dump(self.themes[self.current_theme], f, indent=4)
                
                self.statusBar.showMessage(f"Tema guardado en: {file_path}", 3000)
        except Exception as e:
            self.statusBar.showMessage(f"Error al guardar tema: {str(e)}", 5000)
    
    def reload_themes(self):
        """Recarga los temas desde el archivo y aplica el tema actual."""
        self.load_themes()
        self.update_theme_editor()
        self.apply_theme()
        self.statusBar.showMessage("Temas recargados correctamente", 3000)
    
    def change_theme(self, theme_name):
        """Cambia al tema especificado."""
        if theme_name in self.themes:
            self.current_theme = theme_name
            self.update_theme_editor()
            self.apply_theme()
            self.theme_label.setText(f"Tema actual: {self.current_theme}")
            self.statusBar.showMessage(f"Tema cambiado a {theme_name}", 3000)
    
    def apply_theme(self):
        """Aplica el tema actual a la aplicación."""
        theme = self.themes.get(self.current_theme, {})
        
        # Valores por defecto si no se encuentra el tema
        if not theme:
            theme = {
                "bg": "#ffffff",
                "fg": "#000000",
                "secondary_bg": "#f0f0f0",
                "border": "#d0d0d0",
                "accent": "#0078d7",
                "selection": "#b3d7ff",
                "button_hover": "#e5f1fb"
            }
        
        # Aplicar el tema
        self.setStyleSheet(f"""
            /* Base Styles */
            QWidget {{
                background-color: {theme['bg']};
                color: {theme['fg']};
                font-family: {self.font_family};
                font-size: {self.font_size};
            }}
            
            /* Main Window */
            QMainWindow {{
                background-color: {theme['bg']};
                border: 1px solid {theme['border']};
            }}
            
            /* Tabs */
            QTabWidget::pane {{
                border: 1px solid {theme['border']};
                background-color: {theme['bg']};
                border-radius: 3px;
            }}
            
            QTabBar::tab {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                padding: 5px 10px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {theme['bg']};
                border-bottom-color: {theme['bg']};
            }}
            
            QTabBar::tab:hover {{
                background-color: {theme['button_hover']};
            }}
            
            /* Forms and Inputs */
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                padding: 5px;
                border-radius: 3px;
            }}
            
            QComboBox {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                border-radius: 3px;
                padding: 5px;
                min-height: 25px;
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left: 1px solid {theme['border']};
            }}
            
            QComboBox::down-arrow {{
                border: none;
                background-color: {theme['accent']};
                width: 8px;
                height: 8px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                selection-background-color: {theme['selection']};
            }}
            
            /* Buttons */
            QPushButton {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                padding: 5px 10px;
                border-radius: 3px;
                min-height: 25px;
            }}
            
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
            
            QPushButton:pressed {{
                background-color: {theme['selection']};
            }}
            
            QPushButton:disabled {{
                background-color: {theme['secondary_bg']};
                color: rgba({int(theme['fg'].lstrip('#')[0:2], 16)}, 
                            {int(theme['fg'].lstrip('#')[2:4], 16)}, 
                            {int(theme['fg'].lstrip('#')[4:6], 16)}, 0.5);
            }}
            
            /* Lists and Tables */
            QListWidget, QTreeWidget, QTableWidget, QTableView, QTreeView, QListView {{
                background-color: {theme['secondary_bg']};
                alternate-background-color: {theme['bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                border-radius: 3px;
                padding: 5px;
            }}
            
            QListWidget::item, QTreeWidget::item, QTableWidget::item {{
                padding: 5px;
            }}
            
            QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected,
            QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {{
                background-color: {theme['selection']};
                color: {theme['fg']};
            }}
            
            QHeaderView::section {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                padding: 5px;
                border: 1px solid {theme['border']};
            }}
            
            /* Scroll Bars */
            QScrollBar:vertical {{
                background-color: {theme['bg']};
                width: 14px;
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {theme['border']};
                min-height: 20px;
                border-radius: 7px;
                margin: 2px;
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar:horizontal {{
                background-color: {theme['bg']};
                height: 14px;
                margin: 0px;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {theme['border']};
                min-width: 20px;
                border-radius: 7px;
                margin: 2px;
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            
            /* Checkboxes and Radio Buttons */
            QCheckBox, QRadioButton {{
                background-color: transparent;
                color: {theme['fg']};
                spacing: 5px;
            }}
            
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 15px;
                height: 15px;
                border: 1px solid {theme['border']};
            }}
            
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                background-color: {theme['accent']};
            }}
            
            QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {{
                background-color: {theme['secondary_bg']};
            }}
            
            /* Group Box */
            QGroupBox {{
                background-color: {theme['bg']};
                border: 1px solid {theme['border']};
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: {theme['fg']};
            }}
            
            /* Spinboxes */
            QSpinBox, QDoubleSpinBox {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                border-radius: 3px;
                padding: 2px 5px;
            }}
            
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                border-left: 1px solid {theme['border']};
                border-bottom: 1px solid {theme['border']};
                width: 16px;
            }}
            
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                border-left: 1px solid {theme['border']};
                width: 16px;
            }}
            
            /* Progress Bar */
            QProgressBar {{
                border: 1px solid {theme['border']};
                border-radius: 3px;
                background-color: {theme['secondary_bg']};
                text-align: center;
                padding: 1px;
            }}
            
            QProgressBar::chunk {{
                background-color: {theme['accent']};
                width: 10px;
            }}
            
            /* Menu */
            QMenuBar {{
                background-color: {theme['bg']};
                color: {theme['fg']};
                border-bottom: 1px solid {theme['border']};
            }}
            
            QMenuBar::item {{
                background-color: transparent;
                padding: 5px 10px;
            }}
            
            QMenuBar::item:selected {{
                background-color: {theme['selection']};
            }}
            
            QMenu {{
                background-color: {theme['bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
            }}
            
            QMenu::item {{
                padding: 5px 30px 5px 20px;
            }}
            
            QMenu::item:selected {{
                background-color: {theme['selection']};
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {theme['border']};
                margin: 5px 0;
            }}
            
            /* Slider */
            QSlider::groove:horizontal {{
                border: 1px solid {theme['border']};
                height: 8px;
                background-color: {theme['secondary_bg']};
                border-radius: 4px;
            }}
            
            QSlider::handle:horizontal {{
                background-color: {theme['accent']};
                border: 1px solid {theme['border']};
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }}
            
            /* Date Time Edits */
            QDateEdit, QTimeEdit, QDateTimeEdit {{
                background-color: {theme['secondary_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                border-radius: 3px;
                padding: 2px 5px;
            }}
            
            /* Frames */
            QFrame {{
                border: 1px solid {theme['border']};
                border-radius: 3px;
            }}
            
            /* Status Bar */
            QStatusBar {{
                background-color: {theme['bg']};
                color: {theme['fg']};
                border-top: 1px solid {theme['border']};
            }}
            
            /* Dialog */
            QDialog {{
                background-color: {theme['bg']};
                color: {theme['fg']};
            }}
            
            QDialogButtonBox {{
                button-layout: spread;
            }}
        """)
    
    def center_on_screen(self):
        """Centra la ventana en la pantalla."""
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
    
    def watch_file_changes(self):
        """Inicia un temporizador para comprobar si el archivo de temas ha sido modificado."""
        # Implementación futura: Usar QFileSystemWatcher
        pass

def main():
    app = QApplication(sys.argv)
    window = ThemeTester()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()