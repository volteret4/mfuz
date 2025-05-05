from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt



class ArtistSelectorDialog(QDialog):
    """Diálogo para seleccionar artistas de la base de datos"""
    
    def __init__(self, parent=None, db_connection=None):
        super().__init__(parent)
        self.parent = parent
        self.db_connection = db_connection
        self.selected_artists = []
        self.init_ui()
        self.load_artists()
    
    def init_ui(self):
        """Inicializar la interfaz del diálogo"""
        self.setWindowTitle("Seleccionar Artistas")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Campo de búsqueda
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Buscar artistas...")
        self.search_field.textChanged.connect(self.filter_artists)
        layout.addWidget(self.search_field)
        
        # Lista de artistas
        self.artists_list = QListWidget()
        layout.addWidget(self.artists_list)
        
        # Botones
        button_layout = QVBoxLayout()
        self.select_all_btn = QPushButton("Seleccionar Todos")
        self.select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("Deseleccionar Todos")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(self.deselect_all_btn)
        
        self.ok_btn = QPushButton("Aceptar")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_artists(self):
        """Cargar artistas desde la base de datos"""
        try:
            if not self.db_connection:
                self.artists_list.addItem("Error: No se puede conectar a la base de datos")
                return
            
            cursor = self.db_connection.cursor()
            
            # Consultar artistas ordenados por nombre
            cursor.execute("SELECT name FROM artists ORDER BY name")
            artists = cursor.fetchall()
            
            # Añadir a la lista con checkboxes
            for artist in artists:
                item = QListWidgetItem()
                item.setText(artist[0])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.artists_list.addItem(item)
            
            # Cargar artistas guardados previamente y marcarlos
            if hasattr(self.parent, 'saved_artists') and self.parent.saved_artists:
                saved = self.parent.saved_artists
                for i in range(self.artists_list.count()):
                    item = self.artists_list.item(i)
                    if item.text() in saved:
                        item.setCheckState(Qt.CheckState.Checked)
            
        except Exception as e:
            self.artists_list.addItem(f"Error cargando artistas: {str(e)}")
    
    def filter_artists(self, text):
        """Filtrar artistas por texto de búsqueda"""
        for i in range(self.artists_list.count()):
            item = self.artists_list.item(i)
            if text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def select_all(self):
        """Seleccionar todos los artistas visibles"""
        for i in range(self.artists_list.count()):
            item = self.artists_list.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)
    
    def deselect_all(self):
        """Deseleccionar todos los artistas"""
        for i in range(self.artists_list.count()):
            item = self.artists_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
    
    def get_selected_artists(self):
        """Obtener lista de artistas seleccionados"""
        selected = []
        for i in range(self.artists_list.count()):
            item = self.artists_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected