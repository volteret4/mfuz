from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QGridLayout, 
                           QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                           QLabel, QCheckBox, QGroupBox, QTableWidget, QTableWidgetItem,
                           QHeaderView, QComboBox, QSizePolicy, QSplitter, QWidget)
from PyQt6.QtCore import Qt, QSize, QSortFilterProxyModel, QRegularExpression
from PyQt6.QtGui import QColor, QBrush
import traceback

class FilterableTableWidget(QTableWidget):
    """Tabla filtrable con capacidad para filtrar por columnas específicas"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setSortingEnabled(True)
        
        # Configurar las cabeceras para permitir el filtrado
        self.horizontalHeader().setSectionsClickable(True)
        self.horizontalHeader().sectionClicked.connect(self.header_clicked)
        
        # Almacenar qué columna está actualmente en modo de filtrado
        self.filter_column = -1
        self.filter_value = ""
        
        # Crear widget de filtrado
        self.filter_input = QLineEdit(self)
        self.filter_input.setPlaceholderText("Filtrar...")
        self.filter_input.textChanged.connect(self.filter_table)
        self.filter_input.hide()
    
    def header_clicked(self, column):
        """Manejar clic en la cabecera para filtrar esa columna"""
        # Si hacemos clic en la misma columna, cancelar filtrado
        if self.filter_column == column:
            self.clear_filter()
            return
        
        # Configurar para filtrar por esta columna
        self.filter_column = column
        
        # Mostrar input de filtrado
        self.filter_input.setText("")
        self.filter_input.show()
        self.filter_input.setFocus()
        
        # Posicionar el filtro bajo la cabecera
        header_pos = self.horizontalHeader().sectionPosition(column)
        header_width = self.horizontalHeader().sectionSize(column)
        
        self.filter_input.move(header_pos, self.horizontalHeader().height())
        self.filter_input.resize(header_width, 25)
    
    def clear_filter(self):
        """Limpiar filtro actual"""
        self.filter_column = -1
        self.filter_value = ""
        self.filter_input.hide()
        
        # Mostrar todas las filas
        for row in range(self.rowCount()):
            self.setRowHidden(row, False)
    
    def filter_table(self, text):
        """Filtrar tabla por el texto ingresado"""
        self.filter_value = text.lower()
        
        # Si no hay columna seleccionada o texto, mostrar todo
        if self.filter_column == -1 or not self.filter_value:
            for row in range(self.rowCount()):
                self.setRowHidden(row, False)
            return
        
        # Recorrer todas las filas y ocultar las que no coincidan
        for row in range(self.rowCount()):
            item = self.item(row, self.filter_column)
            if item:
                if self.filter_value in item.text().lower():
                    self.setRowHidden(row, False)
                else:
                    self.setRowHidden(row, True)
            else:
                self.setRowHidden(row, True)


class ArtistSelectorDialog(QDialog):
    """Diálogo mejorado para seleccionar artistas de la base de datos con filtros avanzados"""
    
    def __init__(self, parent=None, db_connection=None):
        super().__init__(parent)
        self.parent = parent
        self.db_connection = db_connection
        self.selected_artists = []
        
        # Comprobar si existe la columna favorito
        self.has_favorito_column = self._check_column_exists('artists', 'favorito')
        
        # Obtener usuarios de spotify y lastfm si existen
        self.spotify_users = self._get_distinct_values('artists', 'origen', 'spotify_%')
        self.lastfm_users = self._get_distinct_values('artists', 'origen', 'scrobble_%')
        
        self.init_ui()
        self.load_artists()
    
    def _check_column_exists(self, table, column):
        """Comprobar si existe una columna en una tabla"""
        try:
            if not self.db_connection:
                return False
                
            cursor = self.db_connection.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            return any(col[1] == column for col in columns)
        except Exception:
            return False
    
    def _get_distinct_values(self, table, column, pattern):
        """Obtener valores distintos de una columna que coinciden con un patrón"""
        try:
            if not self.db_connection:
                return []
                
            cursor = self.db_connection.cursor()
            cursor.execute(f"SELECT DISTINCT {column} FROM {table} WHERE {column} LIKE ?", (pattern,))
            values = cursor.fetchall()
            
            return [value[0] for value in values]
        except Exception:
            return []
    
    def init_ui(self):
        """Inicializar la interfaz del diálogo"""
        self.setWindowTitle("Seleccionar Artistas de Muspy")
        self.setMinimumSize(900, 600)
        
        # Layout principal
        main_layout = QVBoxLayout()
        
        # Sección de búsqueda global
        search_layout = QHBoxLayout()
        search_label = QLabel("Buscar:")
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Buscar artistas...")
        self.search_field.textChanged.connect(self.filter_artists)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_field, 1)
        
        main_layout.addLayout(search_layout)
        
        # Crear un QSplitter para dividir filtros y tabla
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panel de filtros (lado izquierdo)
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        # Grupo de origen
        origin_group = QGroupBox("Filtrar por origen")
        origin_layout = QVBoxLayout()
        
        # Checkbox para origen local
        self.local_checkbox = QCheckBox("Local")
        self.local_checkbox.stateChanged.connect(self.filter_artists)
        origin_layout.addWidget(self.local_checkbox)
        
        # Checkboxes para usuarios de Spotify
        if self.spotify_users:
            spotify_group = QGroupBox("Spotify")
            spotify_layout = QVBoxLayout()
            self.spotify_checkboxes = []
            
            for user in self.spotify_users:
                # Extraer nombre de usuario del prefijo spotify_
                username = user.replace('spotify_', '')
                checkbox = QCheckBox(username)
                checkbox.setProperty("origin_value", user)
                checkbox.stateChanged.connect(self.filter_artists)
                spotify_layout.addWidget(checkbox)
                self.spotify_checkboxes.append(checkbox)
            
            spotify_group.setLayout(spotify_layout)
            origin_layout.addWidget(spotify_group)
        
        # Checkboxes para usuarios de LastFM
        if self.lastfm_users:
            lastfm_group = QGroupBox("LastFM")
            lastfm_layout = QVBoxLayout()
            self.lastfm_checkboxes = []
            
            for user in self.lastfm_users:
                # Extraer nombre de usuario del prefijo scrobble_
                username = user.replace('scrobble_', '')
                checkbox = QCheckBox(username)
                checkbox.setProperty("origin_value", user)
                checkbox.stateChanged.connect(self.filter_artists)
                lastfm_layout.addWidget(checkbox)
                self.lastfm_checkboxes.append(checkbox)
            
            lastfm_group.setLayout(lastfm_layout)
            origin_layout.addWidget(lastfm_group)
        
        # Checkbox para favoritos, si la columna existe
        if self.has_favorito_column:
            self.favorite_checkbox = QCheckBox("Favoritos")
            self.favorite_checkbox.stateChanged.connect(self.filter_artists)
            origin_layout.addWidget(self.favorite_checkbox)
        
        origin_group.setLayout(origin_layout)
        filter_layout.addWidget(origin_group)
        
        # Añadir un widget con stretch para empujar todo hacia arriba
        filter_layout.addStretch()
        
        # Añadir el widget de filtros al splitter
        splitter.addWidget(filter_widget)
        
        # Configurar la tabla de artistas (lado derecho)
        self.artists_table = FilterableTableWidget()
        self.artists_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.artists_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.artists_table.setAlternatingRowColors(True)
        
        # Configurar columnas
        self.artists_table.setColumnCount(7)  # 7 columnas
        self.artists_table.setHorizontalHeaderLabels([
            "Artista", "Género", "Tags", "Artistas Similares", 
            "Miembro de", "Alias", "Seleccionar"
        ])
        
        # Ajustar ancho de columnas
        self.artists_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Añadir la tabla al splitter
        splitter.addWidget(self.artists_table)
        
        # Ajustar proporción de tamaño inicial
        splitter.setSizes([250, 650])
        
        main_layout.addWidget(splitter)
        
        # Botones
        button_layout = QHBoxLayout()
        
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
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def load_artists(self):
        """Cargar artistas desde la base de datos en la tabla"""
        try:
            if not self.db_connection:
                self.artists_table.setRowCount(1)
                self.artists_table.setItem(0, 0, QTableWidgetItem("Error: No se puede conectar a la base de datos"))
                return
            
            cursor = self.db_connection.cursor()
            
            # Obtener la lista de columnas disponibles en la tabla artists
            cursor.execute("PRAGMA table_info(artists)")
            columns_info = cursor.fetchall()
            column_names = [col[1] for col in columns_info]
            
            # Debug: mostrar columnas disponibles
            print(f"Columnas disponibles en tabla artists: {column_names}")
            
            # Construir la consulta SQL con las columnas que existen
            query = "SELECT a.id, a.name as artist_name"
            
            # Añadir columnas si existen
            if 'tags' in column_names:
                query += ", a.tags"
            else:
                query += ", ''"  # Valor por defecto
                
            if 'similar_artists' in column_names:
                query += ", a.similar_artists"
            else:
                query += ", ''"
                
            if 'member_of' in column_names:
                query += ", a.member_of"
            else:
                query += ", ''"
                
            if 'aliases' in column_names:
                query += ", a.aliases"
            else:
                query += ", ''"
                
            if 'origen' in column_names:
                query += ", a.origen"
            else:
                query += ", 'local'"
                
            # Añadir columna favorito si existe
            if self.has_favorito_column:
                query += ", a.favorito"
            
            query += " FROM artists a ORDER BY a.name"
            
            print(f"Query: {query}")  # Debug
            
            cursor.execute(query)
            artists = cursor.fetchall()
            
            print(f"Artistas encontrados: {len(artists)}")  # Debug
            
            # Determinar índices de columnas para acceder a los resultados
            col_indices = {
                'id': 0,
                'artist_name': 1,
                'tags': 2,
                'similar_artists': 3,
                'member_of': 4,
                'aliases': 5,
                'origen': 6
            }
            
            if self.has_favorito_column:
                col_indices['favorito'] = 7
            
            # Configurar filas de la tabla
            self.artists_table.setRowCount(len(artists))
            
            # Llenar la tabla con los datos
            for row, artist in enumerate(artists):
                # Almacenar ID y origen como datos de la fila
                artist_id = artist[col_indices['id']]
                artist_origin = artist[col_indices['origen']]
                
                # Determinar si es favorito
                is_favorite = False
                if self.has_favorito_column:
                    is_favorite = bool(artist[col_indices['favorito']])
                
                # Añadir los datos a las columnas
                self.artists_table.setItem(row, 0, QTableWidgetItem(artist[col_indices['artist_name']]))
                
                # Para la columna de género, buscaremos en otro lugar ya que no existe en la tabla artists
                genre = ""
                try:
                    # Intentar obtener género del álbum más popular del artista
                    cursor.execute("""
                        SELECT genre FROM albums 
                        WHERE artist_id = ? AND genre IS NOT NULL
                        LIMIT 1
                    """, (artist_id,))
                    genre_result = cursor.fetchone()
                    if genre_result:
                        genre = genre_result[0]
                except Exception as e:
                    print(f"Error obteniendo género para artista {artist_id}: {e}")
                
                self.artists_table.setItem(row, 1, QTableWidgetItem(genre))
                
                # Tags (puede ser None)
                tags = artist[col_indices['tags']] or ""
                self.artists_table.setItem(row, 2, QTableWidgetItem(tags))
                
                # Artistas similares (puede ser None)
                similar = artist[col_indices['similar_artists']] or ""
                self.artists_table.setItem(row, 3, QTableWidgetItem(similar))
                
                # Miembro de (puede ser None)
                member_of = artist[col_indices['member_of']] or ""
                self.artists_table.setItem(row, 4, QTableWidgetItem(member_of))
                
                # Alias (puede ser None)
                aliases = artist[col_indices['aliases']] or ""
                self.artists_table.setItem(row, 5, QTableWidgetItem(aliases))
                
                # Añadir checkbox en la última columna
                checkbox = QTableWidgetItem()
                checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                checkbox.setCheckState(Qt.CheckState.Unchecked)
                self.artists_table.setItem(row, 6, checkbox)
                
                # Guardar datos adicionales en las celdas para filtrado
                for col in range(7):
                    item = self.artists_table.item(row, col)
                    if item:
                        item.setData(Qt.ItemDataRole.UserRole, {
                            'id': artist_id,
                            'origin': artist_origin,
                            'favorite': is_favorite
                        })
                
                # Si es favorito, resaltar fila
                if is_favorite:
                    for col in range(7):
                        item = self.artists_table.item(row, col)
                        if item:
                            item.setBackground(QBrush(QColor(255, 255, 200)))  # Amarillo claro
            
            # Cargar artistas guardados previamente y marcarlos
            if hasattr(self.parent, 'saved_artists') and self.parent.saved_artists:
                saved = self.parent.saved_artists
                for row in range(self.artists_table.rowCount()):
                    artist_name_item = self.artists_table.item(row, 0)
                    if artist_name_item and artist_name_item.text() in saved:
                        checkbox_item = self.artists_table.item(row, 6)
                        if checkbox_item:
                            checkbox_item.setCheckState(Qt.CheckState.Checked)
            
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error cargando artistas: {str(e)}\n{tb}")
            
            self.artists_table.setRowCount(1)
            self.artists_table.setItem(0, 0, QTableWidgetItem(f"Error cargando artistas: {str(e)}"))
    
    def filter_artists(self):
        """Filtrar artistas según los criterios seleccionados"""
        search_text = self.search_field.text().lower()
        
        # Recopilar orígenes seleccionados
        selected_origins = []
        
        if hasattr(self, 'local_checkbox') and self.local_checkbox.isChecked():
            selected_origins.append('local')
        
        if hasattr(self, 'spotify_checkboxes'):
            for checkbox in self.spotify_checkboxes:
                if checkbox.isChecked():
                    selected_origins.append(checkbox.property("origin_value"))
        
        if hasattr(self, 'lastfm_checkboxes'):
            for checkbox in self.lastfm_checkboxes:
                if checkbox.isChecked():
                    selected_origins.append(checkbox.property("origin_value"))
        
        show_only_favorites = hasattr(self, 'favorite_checkbox') and self.favorite_checkbox.isChecked()
        
        # Filtrar filas
        for row in range(self.artists_table.rowCount()):
            show_row = True
            
            # Verificar filtro de texto si existe
            if search_text:
                text_match = False
                for col in range(6):  # Revisar las primeras 6 columnas (todas menos el checkbox)
                    item = self.artists_table.item(row, col)
                    if item and search_text in item.text().lower():
                        text_match = True
                        break
                
                if not text_match:
                    show_row = False
            
            # Verificar filtro de origen si hay orígenes seleccionados
            if show_row and selected_origins:
                # Obtener el origen de los datos del primer item
                item = self.artists_table.item(row, 0)
                if item:
                    item_data = item.data(Qt.ItemDataRole.UserRole)
                    if item_data and 'origin' in item_data:
                        if item_data['origin'] not in selected_origins:
                            show_row = False
            
            # Verificar filtro de favoritos
            if show_row and show_only_favorites:
                item = self.artists_table.item(row, 0)
                if item:
                    item_data = item.data(Qt.ItemDataRole.UserRole)
                    if item_data and not item_data.get('favorite', False):
                        show_row = False
            
            # Aplicar visibilidad
            self.artists_table.setRowHidden(row, not show_row)
    
    def select_all(self):
        """Seleccionar todos los artistas visibles"""
        for row in range(self.artists_table.rowCount()):
            if not self.artists_table.isRowHidden(row):
                checkbox_item = self.artists_table.item(row, 6)
                if checkbox_item:
                    checkbox_item.setCheckState(Qt.CheckState.Checked)
    
    def deselect_all(self):
        """Deseleccionar todos los artistas"""
        for row in range(self.artists_table.rowCount()):
            checkbox_item = self.artists_table.item(row, 6)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Unchecked)
    
    def get_selected_artists(self):
        """Obtener lista de artistas seleccionados"""
        selected = []
        for row in range(self.artists_table.rowCount()):
            checkbox_item = self.artists_table.item(row, 6)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                artist_name_item = self.artists_table.item(row, 0)
                if artist_name_item:
                    selected.append(artist_name_item.text())
        return selected
    
    def accept(self):
        """Aceptar selección y cerrar diálogo"""
        self.selected_artists = self.get_selected_artists()
        super().accept()